#!/usr/bin/env python3
"""Episode intake + pipeline state for the CWC podcast pipeline.

Usage:
  pipeline.py init     <episode_dir>                 scan raw files, write manifest, create _pipeline/
  pipeline.py status   <episode_dir> [--json]        show every stage's status
  pipeline.py next     <episode_dir>                 print the next stage to run
  pipeline.py start    <episode_dir> <stage>         mark a stage in progress (checks prerequisites)
  pipeline.py done     <episode_dir> <stage> [--output PATH ...] [--note TEXT]
  pipeline.py fail     <episode_dir> <stage> --note TEXT
  pipeline.py skip     <episode_dir> <stage> --note TEXT
  pipeline.py approve  <episode_dir> <stage> --by NAME [--note TEXT]
  pipeline.py reset    <episode_dir> <stage> [--cascade]

The episode folder is the unit of work. Raw files anywhere in it (outside
_pipeline/) are treated as read-only source material.
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

from _common import (AUDIO_EXT, CAPTION_EXT, DOC_EXT, GATED_STAGES, IMAGE_EXT, PIPELINE_DIR,
                     PROJECT_EXT, STAGE_NAMES, STAGES, VIDEO_EXT, ffprobe, load_json,
                     pipeline_dir, save_json, stage_dir)

SKILL_ROOT = Path(__file__).resolve().parent.parent
CONFIG_TEMPLATE = SKILL_ROOT / "assets" / "episode.template.json"


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


# --------------------------------------------------------------------------- intake

def classify(path: Path) -> str:
    ext = path.suffix.lower()
    name = path.stem.lower()
    if ext in VIDEO_EXT:
        return "video"
    if ext in AUDIO_EXT:
        return "audio"
    if ext in CAPTION_EXT:
        return "transcript"
    if ext == ".txt" and re.search(r"transcript|caption|subtit", name):
        return "transcript"
    if ext == ".json" and re.search(r"transcript", name):
        return "transcript"
    if ext in IMAGE_EXT:
        if re.search(r"headshot|guest|portrait", name):
            return "image:guest"
        if re.search(r"thumb", name):
            return "image:thumbnail"
        if re.search(r"logo", name):
            return "image:logo"
        return "image"
    if ext in PROJECT_EXT:
        return "project"
    if ext in DOC_EXT:
        return "doc"
    return "other"


def scan(episode: Path) -> list[dict]:
    files = []
    for p in sorted(episode.rglob("*")):
        rel = p.relative_to(episode)
        if not p.is_file() or rel.parts[0] == PIPELINE_DIR or any(part.startswith(".") for part in rel.parts):
            continue
        if p.name == "episode.json":
            continue
        kind = classify(p)
        entry = {"path": str(rel), "kind": kind, "size_bytes": p.stat().st_size}
        if kind in ("video", "audio"):
            entry["probe"] = ffprobe(p)
        files.append(entry)
    return files


def camera_chunk_groups(files: list[dict]) -> list[list[str]]:
    """Group camera files that were split mid-recording (C0001.MP4, C0002.MP4 / GX010123, GX020123).

    Heuristic only: same folder + same alpha prefix + consecutive numbers. The
    edit stage should confirm by checking that durations/creation times line up.
    """
    groups: dict[tuple[str, str], list[tuple[int, str]]] = {}
    for f in files:
        if f["kind"] != "video":
            continue
        p = Path(f["path"])
        m = re.match(r"^([A-Za-z_\- ]*?)(\d{2,})$", p.stem)
        if m:
            groups.setdefault((str(p.parent), m.group(1)), []).append((int(m.group(2)), f["path"]))
    out = []
    for items in groups.values():
        items.sort()
        run = [items[0]]
        for n, path in items[1:]:
            if n == run[-1][0] + 1:
                run.append((n, path))
            else:
                if len(run) > 1:
                    out.append([x[1] for x in run])
                run = [(n, path)]
        if len(run) > 1:
            out.append([x[1] for x in run])
    return out


def pick_primary(files: list[dict]) -> str | None:
    """Longest video that has an audio track; falls back to the longest video."""
    vids = [f for f in files if f["kind"] == "video" and f.get("probe")]
    if not vids:
        return None
    with_audio = [f for f in vids if f["probe"].get("audio")]
    pool = with_audio or vids
    return max(pool, key=lambda f: f["probe"].get("duration", 0))["path"]


def guess_episode_number(name: str) -> int | None:
    m = re.search(r"(?:ep(?:isode)?|#)\s*[-_ ]?(\d{1,4})", name, re.I)
    return int(m.group(1)) if m else None


def cmd_init(episode: Path) -> None:
    if not episode.is_dir():
        raise SystemExit(f"Not a folder: {episode}")
    pdir = pipeline_dir(episode)
    for stage, _ in STAGES:
        stage_dir(episode, stage).mkdir(parents=True, exist_ok=True)

    files = scan(episode)
    manifest = {
        "episode_dir": str(episode.resolve()),
        "scanned_at": now(),
        "files": files,
        "primary_video": pick_primary(files),
        "camera_chunk_groups": camera_chunk_groups(files),
        "existing_transcripts": [f["path"] for f in files if f["kind"] == "transcript"],
        "counts": {},
    }
    for f in files:
        manifest["counts"][f["kind"]] = manifest["counts"].get(f["kind"], 0) + 1
    save_json(pdir / "manifest.json", manifest)

    cfg_path = episode / "episode.json"
    if not cfg_path.exists():
        cfg = load_json(CONFIG_TEMPLATE, {})
        cfg["episode_number"] = cfg.get("episode_number") or guess_episode_number(episode.name)
        cfg["folder_name"] = episode.name
        primary = next((f for f in files if f["path"] == manifest["primary_video"]), None)
        created = (primary or {}).get("probe", {}).get("creation_time")
        if created and not cfg.get("recorded_date"):
            cfg["recorded_date"] = created[:10]
        save_json(cfg_path, cfg)

    state_path = pdir / "state.json"
    state = load_json(state_path)
    if state is None:
        state = {"created_at": now(), "stages": {s: {"status": "pending"} for s in STAGE_NAMES}, "log": []}
    for s in STAGE_NAMES:  # forward-compatible if stages are added later
        state["stages"].setdefault(s, {"status": "pending"})
    state["log"].append({"at": now(), "event": "init", "files": len(files)})
    save_json(state_path, state)

    print_intake_summary(manifest, cfg_path)


def print_intake_summary(manifest: dict, cfg_path: Path) -> None:
    print(f"Scanned {len(manifest['files'])} files: " +
          ", ".join(f"{k}={v}" for k, v in sorted(manifest["counts"].items())))
    for f in manifest["files"]:
        if f["kind"] in ("video", "audio"):
            pr = f.get("probe") or {}
            v = pr.get("video") or {}
            res = f" {v.get('width')}x{v.get('height')}@{v.get('fps')}" if v else ""
            print(f"  [{f['kind']}] {f['path']}  {pr.get('duration', '?')}s{res}  audio_tracks={len(pr.get('audio', []))}")
    print(f"Primary video guess: {manifest['primary_video']}")
    if manifest["camera_chunk_groups"]:
        print("Split camera files to concatenate first:")
        for g in manifest["camera_chunk_groups"]:
            print("  " + " + ".join(g))
    if manifest["existing_transcripts"]:
        print("Existing transcripts: " + ", ".join(manifest["existing_transcripts"]))
    print(f"Episode config: {cfg_path}")


# --------------------------------------------------------------------------- state

def load_state(episode: Path) -> dict:
    state = load_json(pipeline_dir(episode) / "state.json")
    if state is None:
        raise SystemExit(f"No pipeline state in {episode}. Run: pipeline.py init \"{episode}\"")
    return state


def write_state(episode: Path, state: dict) -> None:
    save_json(pipeline_dir(episode) / "state.json", state)


def check_stage(stage: str) -> None:
    if stage not in STAGE_NAMES:
        raise SystemExit(f"Unknown stage {stage!r}. Stages: {', '.join(STAGE_NAMES)}")


def next_stage(state: dict) -> str | None:
    for s in STAGE_NAMES:
        st = state["stages"][s]
        if st["status"] in ("done", "skipped"):
            if s in GATED_STAGES and st["status"] == "done" and not st.get("approved_by"):
                return s  # gate not yet passed
            continue
        return s
    return None


def cmd_start(episode: Path, stage: str) -> None:
    state = load_state(episode)
    idx = STAGE_NAMES.index(stage)
    for prev in STAGE_NAMES[:idx]:
        st = state["stages"][prev]
        if st["status"] not in ("done", "skipped"):
            raise SystemExit(f"Cannot start {stage}: {prev} is {st['status']}.")
        if prev in GATED_STAGES and not st.get("approved_by"):
            raise SystemExit(f"Cannot start {stage}: {prev} has not been approved. "
                             f"Get explicit approval, then run: pipeline.py approve ... {prev} --by NAME")
    state["stages"][stage].update(status="in_progress", started_at=now())
    state["log"].append({"at": now(), "event": "start", "stage": stage})
    write_state(episode, state)
    print(f"{stage}: in_progress  (outputs -> {stage_dir(episode, stage)})")


def cmd_finish(episode: Path, stage: str, status: str, outputs: list[str], note: str | None) -> None:
    state = load_state(episode)
    entry = state["stages"][stage]
    entry.update(status=status, finished_at=now())
    if outputs:
        entry["outputs"] = outputs
    if note:
        entry["note"] = note
    state["log"].append({"at": now(), "event": status, "stage": stage, "note": note})
    write_state(episode, state)
    print(f"{stage}: {status}")


def cmd_approve(episode: Path, stage: str, by: str, note: str | None) -> None:
    state = load_state(episode)
    entry = state["stages"][stage]
    if entry["status"] != "done":
        raise SystemExit(f"{stage} is {entry['status']}; finish it before approving.")
    entry.update(approved_by=by, approved_at=now())
    if note:
        entry["approval_note"] = note
    state["log"].append({"at": now(), "event": "approve", "stage": stage, "by": by})
    write_state(episode, state)
    print(f"{stage}: approved by {by}")


def cmd_reset(episode: Path, stage: str, cascade: bool) -> None:
    state = load_state(episode)
    targets = STAGE_NAMES[STAGE_NAMES.index(stage):] if cascade else [stage]
    for s in targets:
        state["stages"][s] = {"status": "pending"}
    state["log"].append({"at": now(), "event": "reset", "stages": targets})
    write_state(episode, state)
    print("reset: " + ", ".join(targets))
    if not cascade:
        later = [s for s in STAGE_NAMES[STAGE_NAMES.index(stage) + 1:] if state["stages"][s]["status"] == "done"]
        if later:
            print("warning: these later stages were built from the old output and may be stale: " + ", ".join(later))


def cmd_status(episode: Path, as_json: bool) -> None:
    state = load_state(episode)
    if as_json:
        import json
        print(json.dumps(state["stages"], indent=2))
        return
    width = max(len(s) for s in STAGE_NAMES)
    for s in STAGE_NAMES:
        st = state["stages"][s]
        extra = ""
        if s in GATED_STAGES and st["status"] == "done":
            extra = f"  approved by {st['approved_by']}" if st.get("approved_by") else "  AWAITING APPROVAL"
        if st.get("note"):
            extra += f"  ({st['note']})"
        print(f"{s:<{width}}  {st['status']}{extra}")
    print(f"next: {next_stage(state) or 'nothing, pipeline complete'}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("init", "status", "next"):
        p = sub.add_parser(name)
        p.add_argument("episode", type=Path)
        if name == "status":
            p.add_argument("--json", action="store_true")
    for name in ("start", "done", "fail", "skip", "approve", "reset"):
        p = sub.add_parser(name)
        p.add_argument("episode", type=Path)
        p.add_argument("stage")
        p.add_argument("--note")
        if name == "done":
            p.add_argument("--output", action="append", default=[])
        if name == "approve":
            p.add_argument("--by", required=True)
        if name == "reset":
            p.add_argument("--cascade", action="store_true")
    a = ap.parse_args()
    episode = a.episode.expanduser()
    if getattr(a, "stage", None):
        check_stage(a.stage)

    if a.cmd == "init":
        cmd_init(episode)
    elif a.cmd == "status":
        cmd_status(episode, a.json)
    elif a.cmd == "next":
        print(next_stage(load_state(episode)) or "")
    elif a.cmd == "start":
        cmd_start(episode, a.stage)
    elif a.cmd == "done":
        cmd_finish(episode, a.stage, "done", a.output, a.note)
    elif a.cmd in ("fail", "skip"):
        if not a.note:
            raise SystemExit(f"{a.cmd} needs --note explaining why")
        cmd_finish(episode, a.stage, "failed" if a.cmd == "fail" else "skipped", [], a.note)
    elif a.cmd == "approve":
        cmd_approve(episode, a.stage, a.by, a.note)
    elif a.cmd == "reset":
        cmd_reset(episode, a.stage, a.cascade)


if __name__ == "__main__":
    sys.exit(main())
