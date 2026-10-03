#!/usr/bin/env python3
"""Transcript utilities for the CWC podcast pipeline.

All transcripts are normalised to one shape, segments.json:
    [{"start": 12.34, "end": 15.0, "text": "..."}, ...]
plus a flat transcript.txt of "[HH:MM:SS] text" lines (what clips-from-video wants).

Usage:
  transcript.py normalize  <in.vtt|.srt|.json> --out-dir DIR
  transcript.py transcribe <media> --out-dir DIR [--backend groq|openai]
  transcript.py remap      <segments.json> --edl edl.json --out-dir DIR
  transcript.py srt        <segments.json> --start T --end T --out FILE.srt   (cues for one clip range)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from _common import fmt_ts, load_json, map_time, parse_ts, save_json

CUE_RE = re.compile(r"(\d{1,2}:\d{2}:\d{2}[.,]\d{3}|\d{2}:\d{2}[.,]\d{3})\s+-->\s+"
                    r"(\d{1,2}:\d{2}:\d{2}[.,]\d{3}|\d{2}:\d{2}[.,]\d{3})")
TAG_RE = re.compile(r"<[^>]+>")


# --------------------------------------------------------------------------- parse

def parse_cues(path: Path) -> list[dict]:
    """Parse .vtt or .srt into segments, stripping inline tags and rolling duplicates."""
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    segs: list[dict] = []
    i = 0
    while i < len(lines):
        m = CUE_RE.search(lines[i])
        if not m:
            i += 1
            continue
        start, end = parse_ts(m.group(1)), parse_ts(m.group(2))
        i += 1
        text_lines = []
        while i < len(lines) and lines[i].strip():
            t = TAG_RE.sub("", lines[i]).strip()
            if t:
                text_lines.append(t)
            i += 1
        text = " ".join(text_lines).strip()
        if text:
            segs.append({"start": round(start, 3), "end": round(end, 3), "text": text})
    return dedupe(segs)


def dedupe(segs: list[dict]) -> list[dict]:
    """Collapse YouTube-style rolling captions: identical repeats, and cues that
    only restate the previous cue's text before adding new words."""
    out: list[dict] = []
    for s in segs:
        if out:
            prev = out[-1]
            if s["text"] == prev["text"]:
                prev["end"] = s["end"]
                continue
            if s["text"].startswith(prev["text"]) and s["start"] - prev["start"] < 10:
                tail = s["text"][len(prev["text"]):].strip()
                if tail:
                    out.append({"start": s["start"], "end": s["end"], "text": tail})
                else:
                    prev["end"] = s["end"]
                continue
        out.append(dict(s))
    return out


def load_any(path: Path) -> list[dict]:
    ext = path.suffix.lower()
    if ext in (".vtt", ".srt"):
        return parse_cues(path)
    if ext == ".json":
        data = load_json(path)
        if isinstance(data, dict):  # whisper verbose_json or watch-video output
            data = data.get("segments", [])
        return [{"start": float(s["start"]), "end": float(s["end"]), "text": str(s["text"]).strip()}
                for s in data if str(s.get("text", "")).strip()]
    raise SystemExit(f"Unsupported transcript format: {path.name} (want .vtt, .srt or .json)")


# --------------------------------------------------------------------------- write

def write_outputs(segs: list[dict], out_dir: Path, stem: str = "transcript") -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    save_json(out_dir / f"{stem}.segments.json", segs)
    (out_dir / f"{stem}.txt").write_text(
        "\n".join(f"[{fmt_ts(s['start'])}] {s['text']}" for s in segs) + "\n", encoding="utf-8")
    write_vtt(segs, out_dir / f"{stem}.vtt")
    print(f"{len(segs)} segments -> {out_dir}/{stem}.{{segments.json,txt,vtt}}")


def write_vtt(segs: list[dict], path: Path) -> None:
    body = ["WEBVTT", ""]
    for s in segs:
        body += [f"{fmt_ts(s['start'], True)} --> {fmt_ts(s['end'], True)}", s["text"], ""]
    path.write_text("\n".join(body), encoding="utf-8")


def write_srt(segs: list[dict], path: Path) -> None:
    body = []
    for n, s in enumerate(segs, 1):
        a, b = fmt_ts(s["start"], True).replace(".", ","), fmt_ts(s["end"], True).replace(".", ",")
        body += [str(n), f"{a} --> {b}", s["text"], ""]
    path.write_text("\n".join(body), encoding="utf-8")


# --------------------------------------------------------------------------- remap

def remap(segs: list[dict], keep: list[tuple[float, float]]) -> list[dict]:
    """Move segments from the raw timeline onto the edited (master) timeline.
    Segments whose start was cut are dropped; ends that were cut are clamped."""
    out = []
    for s in segs:
        a = map_time(s["start"], keep)
        if a is None:
            continue
        b = map_time(s["end"], keep)
        if b is None or b < a:
            b = a + min(s["end"] - s["start"], 4.0)
        out.append({"start": round(a, 3), "end": round(b, 3), "text": s["text"]})
    return out


# --------------------------------------------------------------------------- transcribe

def find_watch_video_whisper() -> Path | None:
    """Locate the installed watch-video skill's whisper.py (Groq/OpenAI Whisper API)."""
    roots = [Path.home() / ".claude", Path("/mnt/skills"), Path("/sessions")]
    for root in roots:
        if root.exists():
            for p in root.glob("**/watch-video/scripts/whisper.py"):
                return p
    return None


def transcribe(media: Path, out_dir: Path, backend: str | None) -> list[dict]:
    """Best-effort chain: local faster-whisper -> local whisper CLI -> watch-video's Whisper API."""
    out_dir.mkdir(parents=True, exist_ok=True)

    try:  # 1. faster-whisper (local, free, accurate)
        from faster_whisper import WhisperModel  # type: ignore
        model = WhisperModel(os.environ.get("CWC_WHISPER_MODEL", "medium.en"), compute_type="auto")
        segments, _ = model.transcribe(str(media), vad_filter=True)
        return [{"start": round(s.start, 3), "end": round(s.end, 3), "text": s.text.strip()} for s in segments]
    except ImportError:
        pass

    import shutil
    if shutil.which("whisper"):  # 2. openai-whisper CLI
        subprocess.run(["whisper", str(media), "--model", os.environ.get("CWC_WHISPER_MODEL", "medium.en"),
                        "--output_format", "vtt", "--output_dir", str(out_dir)], check=True)
        return parse_cues(out_dir / f"{media.stem}.vtt")

    script = find_watch_video_whisper()  # 3. Whisper API via the watch-video skill
    if script:
        # TODO: the APIs cap uploads at 25 MB. watch-video sends mono mp3, which is roughly
        # 0.5 MB/min, so episodes over ~45 min need chunking (split on silences, offset, merge).
        cmd = [sys.executable, str(script), str(media), str(out_dir / "audio.mp3")]
        if backend:
            cmd += ["--backend", backend]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            return json.loads(res.stdout)["segments"]
        raise SystemExit(f"watch-video whisper failed:\n{res.stderr[-2000:]}")

    raise SystemExit(
        "No transcription engine available. Options: drop a .vtt/.srt export (Riverside, Descript, "
        "Premiere) into the episode folder; `pip install faster-whisper`; or add GROQ_API_KEY / "
        "OPENAI_API_KEY to ~/.config/watch/.env for the watch-video skill's Whisper path.")


# --------------------------------------------------------------------------- cli

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("normalize"); p.add_argument("src", type=Path); p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--stem", default="transcript")
    p = sub.add_parser("transcribe"); p.add_argument("media", type=Path); p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--backend", choices=["groq", "openai"])
    p = sub.add_parser("remap"); p.add_argument("segments", type=Path); p.add_argument("--edl", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, required=True); p.add_argument("--stem", default="transcript_master")
    p = sub.add_parser("srt"); p.add_argument("segments", type=Path)
    p.add_argument("--start", required=True); p.add_argument("--end", required=True)
    p.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()

    if a.cmd == "normalize":
        write_outputs(load_any(a.src), a.out_dir, a.stem)
    elif a.cmd == "transcribe":
        write_outputs(transcribe(a.media, a.out_dir, a.backend), a.out_dir)
    elif a.cmd == "remap":
        edl = load_json(a.edl)
        keep = [(k["src_start"], k["src_end"]) for k in edl["keep"]]
        write_outputs(remap(load_any(a.segments), keep), a.out_dir, a.stem)
    elif a.cmd == "srt":
        start, end = parse_ts(a.start), parse_ts(a.end)
        segs = [{"start": max(0, s["start"] - start), "end": min(end, s["end"]) - start, "text": s["text"]}
                for s in load_any(a.segments) if s["end"] > start and s["start"] < end]
        write_srt(segs, a.out)
        print(f"{len(segs)} cues -> {a.out}")


if __name__ == "__main__":
    main()
