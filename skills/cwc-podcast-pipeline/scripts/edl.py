#!/usr/bin/env python3
"""Edit stage for the CWC podcast pipeline: build an edit decision list (EDL)
from trims + skip segments + dead-air removal, then render the master.

Usage:
  edl.py concat <out.mp4> <part1> <part2> ...        join split camera files (stream copy)
  edl.py build  <episode_dir> --source PATH [--head T] [--tail T]
                [--skip START-END[:reason]]... [--silence-min SEC] [--pad SEC]
                [--noise DB] [--no-silence]
  edl.py render <episode_dir> [--lufs -14] [--tp -1] [--fast]

build writes _pipeline/02_edit/edl.json and edit_report.md and renders nothing,
so the cut list can be reviewed before spending time on an encode.
Head/tail/skips also come from episode.json ("edit" section); CLI flags win.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import tempfile
from pathlib import Path

from _common import (detect_silences, ffprobe, fmt_ts, load_json, merge_ranges, parse_ts,
                     render_segments, require_ffmpeg, save_json, select_expr, stage_dir,
                     subtract_ranges)


def cmd_concat(out: Path, parts: list[Path]) -> None:
    require_ffmpeg()
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        for p in parts:
            f.write(f"file '{p.resolve()}'\n")
        listfile = f.name
    res = subprocess.run(["ffmpeg", "-hide_banner", "-y", "-f", "concat", "-safe", "0", "-i", listfile,
                          "-c", "copy", str(out)], capture_output=True, text=True)
    Path(listfile).unlink(missing_ok=True)
    if res.returncode != 0:
        raise SystemExit(f"concat failed:\n{res.stderr[-2000:]}")
    print(f"joined {len(parts)} files -> {out} ({ffprobe(out).get('duration')}s)")


SKIP_RE = re.compile(r"^\s*([\d:.]+)\s*-\s*([\d:.]+)\s*(?::\s*(.*))?$")


def parse_skip(text: str) -> tuple[float, float, str]:
    """'00:10:00-00:12:30:sponsor read' -> (600.0, 750.0, 'sponsor read')."""
    m = SKIP_RE.match(text)
    if not m:
        raise SystemExit(f"Bad --skip value {text!r}; want START-END[:reason]")
    return parse_ts(m.group(1)), parse_ts(m.group(2)), (m.group(3) or "skip").strip()


def cmd_build(episode: Path, a: argparse.Namespace) -> None:
    cfg = load_json(episode / "episode.json", {})
    ecfg = cfg.get("edit", {})
    source = a.source if a.source.is_absolute() else (episode / a.source)
    probe = ffprobe(source)
    duration = probe.get("duration") or 0.0
    if not duration:
        raise SystemExit(f"Could not read duration of {source}")
    has_audio = bool(probe.get("audio"))

    head = parse_ts(a.head) if a.head else _cfg_ts(ecfg.get("head_trim"), 0.0)
    tail = parse_ts(a.tail) if a.tail else _cfg_ts(ecfg.get("tail_trim"), duration)

    removed: list[dict] = []
    if head > 0:
        removed.append({"src_start": 0.0, "src_end": head, "reason": "head trim"})
    if tail < duration:
        removed.append({"src_start": tail, "src_end": duration, "reason": "tail trim"})

    skips = [parse_skip(s) for s in a.skip]
    for s in ecfg.get("skip_segments", []):
        skips.append((parse_ts(s["start"]), parse_ts(s["end"]), s.get("reason") or "skip"))
    for sa, sb, why in skips:
        removed.append({"src_start": sa, "src_end": sb, "reason": f"skip: {why}"})

    silence_min = a.silence_min if a.silence_min is not None else ecfg.get("dead_air_min_sec", 2.0)
    pad = a.pad if a.pad is not None else ecfg.get("dead_air_keep_sec", 0.35)
    noise = a.noise if a.noise is not None else ecfg.get("silence_noise_db", -35)
    silences = []
    if has_audio and not a.no_silence and silence_min > 0:
        silences = detect_silences(source, noise_db=noise, min_dur=silence_min)
        for sa, sb in silences:
            # leave `pad` of the pause on each side so cuts breathe
            ca, cb = max(sa + pad, head), min(sb - pad, tail)  # ignore dead air already trimmed
            if cb - ca > 0.1:
                removed.append({"src_start": ca, "src_end": cb, "reason": "dead air"})

    ranges = merge_ranges([(r["src_start"], r["src_end"]) for r in removed])
    keep_ranges = subtract_ranges(0.0, duration, ranges)
    keep, cursor = [], 0.0
    for ka, kb in keep_ranges:
        keep.append({"src_start": round(ka, 3), "src_end": round(kb, 3),
                     "master_start": round(cursor, 3), "master_end": round(cursor + kb - ka, 3)})
        cursor += kb - ka

    edl = {
        "source": str(source.relative_to(episode)) if source.is_relative_to(episode) else str(source),
        "source_duration": duration,
        "has_audio": has_audio,
        "params": {"head": head, "tail": tail, "dead_air_min_sec": silence_min,
                   "dead_air_keep_sec": pad, "silence_noise_db": noise},
        "removed": sorted(removed, key=lambda r: r["src_start"]),
        "keep": keep,
        "master_duration": round(cursor, 3),
        "time_saved": round(duration - cursor, 3),
    }
    out_dir = stage_dir(episode, "edit")
    save_json(out_dir / "edl.json", edl)
    write_report(edl, out_dir / "edit_report.md")
    print(f"source {fmt_ts(duration)} -> master {fmt_ts(cursor)} "
          f"({len(keep)} segments, {len([r for r in removed if r['reason'] == 'dead air'])} dead-air cuts, "
          f"saved {edl['time_saved']:.0f}s)")
    print(f"wrote {out_dir / 'edl.json'} and edit_report.md")


def _cfg_ts(value, default: float) -> float:
    if value in (None, "", "auto", "none"):
        return default
    return parse_ts(value)


def write_report(edl: dict, path: Path) -> None:
    lines = [
        "# Edit report", "",
        f"- Source: `{edl['source']}` ({fmt_ts(edl['source_duration'])})",
        f"- Master: {fmt_ts(edl['master_duration'])} after removing {edl['time_saved']:.0f}s",
        f"- Segments kept: {len(edl['keep'])}", "",
        "## Removed (source timeline)", "",
        "| From | To | Length | Reason |", "|---|---|---|---|",
    ]
    for r in edl["removed"]:
        lines.append(f"| {fmt_ts(r['src_start'])} | {fmt_ts(r['src_end'])} | "
                     f"{r['src_end'] - r['src_start']:.1f}s | {r['reason']} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def measure_loudness(src: Path, keep: list[tuple[float, float]], lufs: float, tp: float) -> dict | None:
    """Pass 1 of two-pass loudnorm, measured on the kept audio only."""
    graph = f"[0:a]aselect='{select_expr(keep)}',asetpts=N/SR/TB,loudnorm=I={lufs}:TP={tp}:LRA=11:print_format=json"
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write(graph)
        script = f.name
    res = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(src), "-filter_complex_script",
                          script, "-f", "null", "-"], capture_output=True, text=True)
    Path(script).unlink(missing_ok=True)
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", res.stderr)
    return json.loads(m.group(0)) if m else None


def cmd_render(episode: Path, a: argparse.Namespace) -> None:
    out_dir = stage_dir(episode, "edit")
    edl = load_json(out_dir / "edl.json")
    if not edl:
        raise SystemExit("No edl.json yet. Run: edl.py build <episode_dir> --source ...")
    src = Path(edl["source"])
    src = src if src.is_absolute() else episode / src
    keep = [(k["src_start"], k["src_end"]) for k in edl["keep"]]
    loud = None
    if edl.get("has_audio", True):
        m = measure_loudness(src, keep, a.lufs, a.tp)
        loud = f"I={a.lufs}:TP={a.tp}:LRA=11"
        if m:
            loud += (f":measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
                     f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
            print(f"loudness: measured {m['input_i']} LUFS -> target {a.lufs} LUFS")
    out = out_dir / ("master_preview.mp4" if a.fast else "master.mp4")
    render_segments(src, keep, out, loudnorm=loud, has_audio=edl.get("has_audio", True),
                    crf=28 if a.fast else 18, preset="ultrafast" if a.fast else "medium")
    print(f"rendered {out} ({ffprobe(out).get('duration')}s)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("concat"); p.add_argument("out", type=Path); p.add_argument("parts", type=Path, nargs="+")
    p = sub.add_parser("build"); p.add_argument("episode", type=Path); p.add_argument("--source", type=Path, required=True)
    p.add_argument("--head"); p.add_argument("--tail"); p.add_argument("--skip", action="append", default=[])
    p.add_argument("--silence-min", type=float); p.add_argument("--pad", type=float)
    p.add_argument("--noise", type=float); p.add_argument("--no-silence", action="store_true")
    p = sub.add_parser("render"); p.add_argument("episode", type=Path)
    p.add_argument("--lufs", type=float, default=-14.0); p.add_argument("--tp", type=float, default=-1.0)
    p.add_argument("--fast", action="store_true", help="quick low-quality preview render")
    a = ap.parse_args()
    if a.cmd == "concat":
        cmd_concat(a.out, a.parts)
    elif a.cmd == "build":
        cmd_build(a.episode, a)
    elif a.cmd == "render":
        cmd_render(a.episode, a)


if __name__ == "__main__":
    main()
