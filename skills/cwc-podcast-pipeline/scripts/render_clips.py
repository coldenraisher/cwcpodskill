#!/usr/bin/env python3
"""Render the long clips and vertical shorts from clip_plan.json.

clip_plan.json is the clips-from-video output in its own schema:
    {"clips": [CLIP, ...], "shorts": [CLIP, ...]}
where each CLIP has id, title, timestamp ("HH:MM:SS → HH:MM:SS" on the MASTER
timeline), cuts ([{ts: "A – B", note}]), desc, thumb, score.

Usage:
  render_clips.py <episode_dir> [--only c1,s2] [--no-captions] [--words 4] [--fast]

Outputs to _pipeline/04_render/{clips,shorts}/ plus renders.json (the publish
stage reads that file).
"""
from __future__ import annotations

import argparse
import shutil
import tempfile
from pathlib import Path

from _common import (ffprobe, load_json, map_time, parse_range, render_segments, save_json, slugify,
                     stage_dir, subtract_ranges)
from transcript import load_any, write_srt

# TODO(brand): swap in CWC caption styling (Space Grotesk, lime #A3FF12 active word,
# karaoke-style word highlight via ASS) once the look is signed off.
CAPTION_STYLE = ("FontName=Arial,Fontsize=13,Bold=1,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
                 "BorderStyle=1,Outline=2,Shadow=0,Alignment=2,MarginV=70")


def clip_keep(clip: dict) -> list[tuple[float, float]]:
    start, end = parse_range(clip["timestamp"])
    cuts = []
    for c in clip.get("cuts") or []:
        try:
            cuts.append(parse_range(c["ts"]))
        except (KeyError, ValueError):
            continue  # free-text notes like "clean, no trims" have no range
    return subtract_ranges(start, end, cuts)


def word_chunks(segs: list[dict], max_words: int) -> list[dict]:
    """Split transcript segments into short caption chunks, timing words evenly."""
    out = []
    for s in segs:
        words = s["text"].split()
        if not words:
            continue
        per = (s["end"] - s["start"]) / len(words)
        for i in range(0, len(words), max_words):
            chunk = words[i:i + max_words]
            a = s["start"] + i * per
            out.append({"start": a, "end": a + len(chunk) * per, "text": " ".join(chunk)})
    return out


def captions_for(segs: list[dict], keep: list[tuple[float, float]], max_words: int) -> list[dict]:
    lo, hi = keep[0][0], keep[-1][1]
    window = [s for s in segs if s["end"] > lo and s["start"] < hi]
    out = []
    for c in word_chunks(window, max_words):
        a = map_time(c["start"], keep)
        if a is None:
            continue
        b = map_time(c["end"], keep)
        out.append({"start": a, "end": b if b is not None and b > a else a + 0.6, "text": c["text"]})
    return out


def vertical_filter(probe: dict) -> str:
    v = probe.get("video") or {}
    w, h = v.get("width") or 1920, v.get("height") or 1080
    if w * 16 <= h * 9:  # already 9:16 or taller
        return "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2"
    # TODO(reframe): center crop is a placeholder. For a two-person podcast this should
    # follow the active speaker (face detection per shot, or a speaker diarization map).
    return "crop=ih*9/16:ih:(iw-ih*9/16)/2:0,scale=1080:1920"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("episode", type=Path)
    ap.add_argument("--only", help="comma-separated clip ids to render")
    ap.add_argument("--no-captions", action="store_true")
    ap.add_argument("--words", type=int, default=4, help="max words per caption on shorts")
    ap.add_argument("--fast", action="store_true", help="quick low-quality preview renders")
    a = ap.parse_args()
    ep = a.episode

    plan = load_json(stage_dir(ep, "clips") / "clip_plan.json")
    if not plan:
        raise SystemExit("No _pipeline/03_clips/clip_plan.json. Run the clips stage first.")
    master = stage_dir(ep, "edit") / "master.mp4"
    if not master.exists():
        raise SystemExit(f"No master at {master}. Run the edit stage first.")
    seg_path = stage_dir(ep, "edit") / "transcript_master.segments.json"
    segs = load_any(seg_path) if seg_path.exists() else []
    probe = ffprobe(master)
    has_audio = bool(probe.get("audio"))
    only = set(a.only.split(",")) if a.only else None
    out_root = stage_dir(ep, "render")
    tmp = Path(tempfile.mkdtemp(prefix="cwc_caps_"))  # libass hates odd characters in paths
    renders = load_json(out_root / "renders.json", {"items": []})
    by_id = {r["id"]: r for r in renders["items"]}

    jobs = [("clip", c) for c in plan.get("clips", [])] + [("short", s) for s in plan.get("shorts", [])]
    for kind, clip in jobs:
        if only and clip["id"] not in only:
            continue
        keep = clip_keep(clip)
        name = f"{clip['id']}-{slugify(clip.get('title', ''))}.mp4"
        out = out_root / ("clips" if kind == "clip" else "shorts") / name
        out.parent.mkdir(parents=True, exist_ok=True)
        vf = None
        srt_out = None
        if kind == "short":
            vf = vertical_filter(probe)
            if segs:
                caps = captions_for(segs, keep, a.words)
                srt_out = out.with_suffix(".srt")
                write_srt(caps, srt_out)
                if caps and not a.no_captions:
                    shutil.copy(srt_out, tmp / "caps.srt")
                    vf += f",subtitles={tmp / 'caps.srt'}:force_style='{CAPTION_STYLE}'"
        print(f"rendering {kind} {clip['id']}: {clip.get('title', '')}")
        render_segments(master, keep, out, vfilter=vf, has_audio=has_audio,
                        loudnorm=None,  # master is already normalised
                        crf=28 if a.fast else 18, preset="ultrafast" if a.fast else "medium")
        by_id[clip["id"]] = {
            "id": clip["id"], "kind": kind, "title": clip.get("title"), "score": clip.get("score"),
            "path": str(out.relative_to(ep)), "captions_srt": str(srt_out.relative_to(ep)) if srt_out else None,
            "duration": ffprobe(out).get("duration"), "desc": clip.get("desc"), "thumb": clip.get("thumb"),
            "preview": a.fast,
        }
    shutil.rmtree(tmp, ignore_errors=True)
    renders["items"] = sorted(by_id.values(), key=lambda r: (r["kind"], r["id"]))
    save_json(out_root / "renders.json", renders)
    print(f"{len(renders['items'])} renders listed in {out_root / 'renders.json'}")


if __name__ == "__main__":
    main()
