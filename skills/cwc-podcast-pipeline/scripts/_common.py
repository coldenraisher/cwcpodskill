"""Shared helpers for the CWC podcast pipeline scripts.

Pure stdlib. Every script in this folder imports from here, so keep it free of
side effects at import time.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

PIPELINE_DIR = "_pipeline"

# Ordered stage list. The folder is where that stage writes its outputs
# (relative to <episode>/_pipeline/). None = writes to the _pipeline root.
STAGES: list[tuple[str, str | None]] = [
    ("intake", None),
    ("transcribe", "01_transcribe"),
    ("edit", "02_edit"),
    ("clips", "03_clips"),
    ("render", "04_render"),
    ("package", "05_package"),
    ("social", "06_social"),
    ("review", "07_review"),
    ("publish", "08_publish"),
    ("wrapup", None),
]
STAGE_NAMES = [s for s, _ in STAGES]
GATED_STAGES = {"review"}  # must be explicitly approved before the next stage can start

VIDEO_EXT = {".mp4", ".mov", ".mkv", ".m4v", ".webm", ".avi", ".mxf", ".mts"}
AUDIO_EXT = {".wav", ".mp3", ".m4a", ".aac", ".flac", ".aif", ".aiff", ".ogg"}
CAPTION_EXT = {".vtt", ".srt"}
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".heic"}
DOC_EXT = {".md", ".txt", ".docx", ".pdf", ".rtf"}
PROJECT_EXT = {".drp", ".prproj", ".fcpxml", ".xml", ".edl", ".otio"}


# --------------------------------------------------------------------------- paths

def pipeline_dir(episode: Path) -> Path:
    return episode / PIPELINE_DIR


def stage_dir(episode: Path, stage: str) -> Path:
    folder = dict(STAGES)[stage]
    return pipeline_dir(episode) / folder if folder else pipeline_dir(episode)


def load_json(path: Path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def slugify(text: str, max_len: int = 48) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:max_len].rstrip("-") or "untitled"


# --------------------------------------------------------------------------- time

_TS_RE = re.compile(r"^(?:(\d+):)?(\d{1,2}):(\d{1,2})(?:[.,](\d+))?$")


def parse_ts(value) -> float:
    """'HH:MM:SS(.mmm)', 'MM:SS', or a number of seconds -> float seconds."""
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    try:
        return float(text)
    except ValueError:
        pass
    m = _TS_RE.match(text)
    if not m:
        raise ValueError(f"Unrecognised timestamp: {value!r}")
    h, mnt, s, frac = m.groups()
    secs = int(h or 0) * 3600 + int(mnt) * 60 + int(s)
    if frac:
        secs += float("0." + frac)
    return float(secs)


def fmt_ts(seconds: float, millis: bool = False) -> str:
    seconds = max(0.0, seconds)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    if millis:
        return f"{h:02d}:{m:02d}:{s:06.3f}"
    return f"{h:02d}:{m:02d}:{int(s):02d}"


_RANGE_SPLIT = re.compile(r"\s*(?:→|->|–|—|-{1,2}>?|to)\s*")


def parse_range(text: str) -> tuple[float, float]:
    """'00:23:54 → 00:30:50' (also ->, –, —, -, 'to') -> (start, end) seconds."""
    parts = [p for p in _RANGE_SPLIT.split(str(text).strip()) if p]
    if len(parts) != 2:
        raise ValueError(f"Unrecognised range: {text!r}")
    start, end = parse_ts(parts[0]), parse_ts(parts[1])
    if end <= start:
        raise ValueError(f"Range ends before it starts: {text!r}")
    return start, end


# --------------------------------------------------------------------------- segments

def merge_ranges(ranges: list[tuple[float, float]]) -> list[tuple[float, float]]:
    out: list[tuple[float, float]] = []
    for a, b in sorted(r for r in ranges if r[1] > r[0]):
        if out and a <= out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], b))
        else:
            out.append((a, b))
    return out


def subtract_ranges(start: float, end: float, remove: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Return the parts of [start, end] not covered by `remove`."""
    keep: list[tuple[float, float]] = []
    cursor = start
    for a, b in merge_ranges(remove):
        if b <= cursor or a >= end:
            continue
        if a > cursor:
            keep.append((cursor, min(a, end)))
        cursor = max(cursor, b)
    if cursor < end:
        keep.append((cursor, end))
    return [(a, b) for a, b in keep if b - a > 0.05]


def map_time(t: float, keep: list[tuple[float, float]]) -> float | None:
    """Map a source timestamp onto the edited timeline. None if t was cut."""
    offset = 0.0
    for a, b in keep:
        if t < a:
            return None
        if t <= b:
            return offset + (t - a)
        offset += b - a
    return None


# --------------------------------------------------------------------------- ffmpeg

def require_ffmpeg() -> None:
    missing = [b for b in ("ffmpeg", "ffprobe") if not shutil.which(b)]
    if missing:
        raise SystemExit(f"Missing on PATH: {', '.join(missing)}. Install ffmpeg first.")


def ffprobe(path: Path) -> dict:
    """Small, stable summary of a media file. Empty dict if ffprobe fails."""
    if not shutil.which("ffprobe"):
        return {}
    cmd = [
        "ffprobe", "-v", "error", "-print_format", "json",
        "-show_entries",
        "format=duration,size,bit_rate:format_tags=creation_time:"
        "stream=index,codec_type,codec_name,width,height,r_frame_rate,channels,sample_rate",
        str(path),
    ]
    try:
        raw = json.loads(subprocess.run(cmd, capture_output=True, text=True, check=True).stdout)
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        return {}
    fmt = raw.get("format", {})
    info: dict = {
        "duration": round(float(fmt.get("duration", 0) or 0), 3),
        "size_bytes": int(fmt.get("size", 0) or 0),
        "creation_time": (fmt.get("tags") or {}).get("creation_time"),
        "video": None,
        "audio": [],
    }
    for st in raw.get("streams", []):
        if st.get("codec_type") == "video" and info["video"] is None:
            num, _, den = (st.get("r_frame_rate") or "0/1").partition("/")
            fps = round(float(num) / float(den or 1), 3) if float(den or 1) else 0
            info["video"] = {"codec": st.get("codec_name"), "width": st.get("width"),
                             "height": st.get("height"), "fps": fps}
        elif st.get("codec_type") == "audio":
            info["audio"].append({"codec": st.get("codec_name"), "channels": st.get("channels"),
                                  "sample_rate": st.get("sample_rate")})
    return info


def detect_silences(path: Path, noise_db: float = -30.0, min_dur: float = 1.5) -> list[tuple[float, float]]:
    """Run ffmpeg silencedetect and return [(start, end), ...] in seconds."""
    require_ffmpeg()
    cmd = ["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-vn",
           "-af", f"silencedetect=noise={noise_db}dB:d={min_dur}", "-f", "null", "-"]
    log = subprocess.run(cmd, capture_output=True, text=True).stderr
    starts = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", log)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", log)]
    duration = ffprobe(path).get("duration", 0.0)
    out = []
    for i, s in enumerate(starts):
        e = ends[i] if i < len(ends) else duration  # trailing silence runs to EOF
        out.append((max(0.0, s), e))
    return out


def select_expr(keep: list[tuple[float, float]]) -> str:
    return "+".join(f"between(t,{a:.3f},{b:.3f})" for a, b in keep)


def render_segments(src: Path, keep: list[tuple[float, float]], out: Path, *,
                    vfilter: str | None = None, loudnorm: str | None = None,
                    has_audio: bool = True, crf: int = 18, preset: str = "medium") -> None:
    """Render only the `keep` ranges of `src` into `out`, in one ffmpeg pass.

    Uses select/aselect so hundreds of segments stay a single filter graph.
    `vfilter` is appended to the video chain (e.g. a 9:16 crop + subtitles).
    `loudnorm` is a loudnorm filter argument string, e.g. "I=-14:TP=-1:LRA=11".
    """
    require_ffmpeg()
    if not keep:
        raise SystemExit("Nothing to render: keep list is empty.")
    out.parent.mkdir(parents=True, exist_ok=True)
    expr = select_expr(keep)
    vchain = f"[0:v]select='{expr}',setpts=N/FRAME_RATE/TB"
    if vfilter:
        vchain += f",{vfilter}"
    graph = [vchain + "[v]"]
    maps = ["-map", "[v]"]
    if has_audio:
        achain = f"[0:a]aselect='{expr}',asetpts=N/SR/TB"
        if loudnorm:
            achain += f",loudnorm={loudnorm}"
        graph.append(achain + "[a]")
        maps += ["-map", "[a]"]
    script = out.with_suffix(".filtergraph.txt")
    script.write_text(";\n".join(graph), encoding="utf-8")
    cmd = ["ffmpeg", "-hide_banner", "-y", "-i", str(src),
           "-filter_complex_script", str(script), *maps,
           "-c:v", "libx264", "-preset", preset, "-crf", str(crf), "-pix_fmt", "yuv420p"]
    if has_audio:
        cmd += ["-c:a", "aac", "-b:a", "192k", "-ar", "48000"]
    cmd += ["-movflags", "+faststart", str(out)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(f"ffmpeg failed rendering {out.name}:\n{result.stderr[-3000:]}")
    script.unlink(missing_ok=True)
