#!/usr/bin/env python3
"""Build the posting schedule and the review page for the approval gate.

Usage:
  publish_plan.py <episode_dir> [--start YYYY-MM-DD]

Reads   episode.json, 04_render/renders.json, 05_package/packaging.json,
        06_social/carousel.json (all optional except renders)
Writes  07_review/publish_plan.json   (the publish stage executes exactly this)
        07_review/review.html         (what Colden looks at before approving)

Weekdays are always computed from dates here, never written by hand.
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import os
from pathlib import Path

from _common import load_json, save_json, stage_dir

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def next_weekday(on_or_after: dt.date, day: str) -> dt.date:
    delta = (DAYS.index(day) - on_or_after.weekday()) % 7
    return on_or_after + dt.timedelta(days=delta)


def slots(after: dt.date, days: list[str], count: int) -> list[dt.date]:
    """The next `count` dates strictly after `after` that fall on `days`."""
    out, d = [], after + dt.timedelta(days=1)
    while len(out) < count:
        if DAYS[d.weekday()] in days:
            out.append(d)
        d += dt.timedelta(days=1)
    return out


def at(day: dt.date, hhmm: str) -> str:
    h, m = (int(x) for x in hhmm.split(":"))
    return dt.datetime.combine(day, dt.time(h, m)).isoformat(timespec="seconds")


def build_plan(ep: Path, start: dt.date) -> dict:
    cfg = load_json(ep / "episode.json", {})
    pub = cfg.get("publish", {})
    cad = pub.get("cadence", {})
    tz = pub.get("timezone", "America/New_York")
    renders = load_json(stage_dir(ep, "render") / "renders.json", {"items": []})["items"]
    pkg = load_json(stage_dir(ep, "package") / "packaging.json", {})
    car = load_json(stage_dir(ep, "social") / "carousel.json")

    go_live = (pkg.get("go_live") or {})
    long_day = go_live.get("day") or cad.get("long_form_day", "Wed")
    long_time = go_live.get("time") or cad.get("long_form_time", "12:00")
    ep_day = next_weekday(start, long_day)
    items = []

    titles = pkg.get("titles") or {}
    items.append({
        "id": "full", "asset": "full_episode", "path": "_pipeline/02_edit/master.mp4",
        "networks": pub.get("full_episode", {}).get("networks", ["youtube"]),
        "publish_at": at(ep_day, long_time), "timezone": tz,
        "title": titles.get(pkg.get("chosen_title", "C")) or cfg.get("working_title") or "TODO title",
        "text": pkg.get("description") or "TODO: description from packaging stage",
        "tags": pkg.get("tags", []),
        "youtube": {"type": "video", "privacy": pub.get("full_episode", {}).get("privacy", "public"),
                    "category": pkg.get("category") or pub.get("full_episode", {}).get("category"),
                    "made_for_kids": pub.get("made_for_kids", False)},
        "thumbnail_path": pkg.get("thumbnail_path"), "first_comment": pkg.get("pinned_comment"),
    })

    clips = sorted([r for r in renders if r["kind"] == "clip"], key=lambda r: -(r.get("score") or 0))
    for r, day in zip(clips, slots(ep_day, cad.get("long_clip_days", ["Tue", "Fri"]), len(clips))):
        items.append({
            "id": r["id"], "asset": "long_clip", "path": r["path"],
            "networks": pub.get("long_clips", {}).get("networks", ["youtube"]),
            "publish_at": at(day, long_time), "timezone": tz, "title": r.get("title"),
            "text": r.get("desc") or "", "tags": pkg.get("tags", [])[:10],
            "youtube": {"type": "video", "privacy": "public", "category": pkg.get("category"),
                        "made_for_kids": pub.get("made_for_kids", False)},
            "thumbnail_path": None,
        })

    shorts = sorted([r for r in renders if r["kind"] == "short"], key=lambda r: -(r.get("score") or 0))
    for r, day in zip(shorts, slots(ep_day, cad.get("shorts_days", ["Mon", "Thu", "Sat"]), len(shorts))):
        items.append({
            "id": r["id"], "asset": "short", "path": r["path"],
            "networks": pub.get("shorts", {}).get("networks", ["youtube", "tiktok", "instagram", "facebook"]),
            "publish_at": at(day, cad.get("shorts_time", "12:00")), "timezone": tz,
            "title": r.get("title"), "text": r.get("desc") or "",
            "youtube": {"type": "short", "privacy": "public", "made_for_kids": pub.get("made_for_kids", False)},
        })

    if car:
        day = ep_day + dt.timedelta(days=int(cad.get("carousel_offset_days", 2)))
        items.append({
            "id": "carousel", "asset": "carousel", "path": car.get("html"),
            "images": car.get("slides", []), "networks": pub.get("carousel", {}).get("networks", ["instagram"]),
            "publish_at": at(day, cad.get("carousel_time", "12:00")), "timezone": tz,
            "title": None, "text": car.get("caption") or "TODO caption",
        })

    for it in items:
        it["weekday"] = DAYS[dt.datetime.fromisoformat(it["publish_at"]).weekday()]
        it.setdefault("media_url", None)  # filled by the publish stage after hosting
        it["status"] = "planned"
        it["metricool"] = None
    return {"mode": pub.get("mode", "schedule"), "metricool_blog_id": pub.get("metricool_blog_id"),
            "timezone": tz, "items": sorted(items, key=lambda i: i["publish_at"])}


def render_review(ep: Path, plan: dict, out: Path) -> None:
    rel = lambda p: os.path.relpath(ep / p, out.parent) if p else ""
    esc = lambda s: html.escape(str(s or ""))
    rows = []
    for it in plan["items"]:
        media = ""
        if it.get("path", "").endswith(".mp4"):
            media = f'<video src="{esc(rel(it["path"]))}" controls preload="metadata"></video>'
        elif it.get("path"):
            media = f'<a href="{esc(rel(it["path"]))}">open</a>'
        rows.append(f"""<tr>
  <td><b>{esc(it['weekday'])}</b><br>{esc(it['publish_at'].replace('T', ' ')[:16])}</td>
  <td>{esc(it['asset'].replace('_', ' '))}<br><small>{esc(', '.join(it['networks']))}</small></td>
  <td class="m">{media}</td>
  <td><b>{esc(it.get('title'))}</b><pre>{esc(it.get('text'))}</pre></td></tr>""")
    edit_report = stage_dir(ep, "edit") / "edit_report.md"
    pkg_html = sorted(stage_dir(ep, "package").glob("packaging-*.html"))
    clips_html = sorted(stage_dir(ep, "clips").glob("clips_dashboard*.html"))
    links = [(edit_report, "Edit report")] + [(p, "Packaging dashboard") for p in pkg_html] + \
            [(p, "Clip plan dashboard") for p in clips_html]
    link_html = " · ".join(f'<a href="{esc(os.path.relpath(p, out.parent))}">{esc(t)}</a>'
                           for p, t in links if p.exists())
    out.write_text(f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Episode Review</title>
<style>
:root{{--bg:#0B0F14;--card:#111827;--fg:#E5E7EB;--mut:#9CA3AF;--acc:#7C3AED;--lime:#A3FF12}}
body{{margin:0;padding:24px 16px;background:var(--bg);color:var(--fg);font:15px/1.5 Inter,system-ui,sans-serif}}
h1{{margin:0 0 4px;font-size:22px}} .sub{{color:var(--mut);margin-bottom:16px}} a{{color:var(--lime)}}
table{{width:100%;border-collapse:collapse;background:var(--card)}}
td{{border-top:1px solid #1f2937;padding:10px;vertical-align:top}}
td.m video{{width:220px;max-height:240px;background:#000;border-radius:6px}}
pre{{white-space:pre-wrap;font:13px/1.45 Inter,system-ui,sans-serif;color:var(--mut);max-height:160px;overflow:auto;margin:6px 0 0}}
.gate{{border-left:4px solid var(--acc);background:var(--card);padding:12px 14px;margin:16px 0}}
@media (max-width:700px){{td.m video{{width:140px}}}}
</style></head><body>
<h1>Episode review: {len(plan['items'])} posts planned</h1>
<div class="sub">Mode: {esc(plan['mode'])} · timezone {esc(plan['timezone'])} · {link_html}</div>
<div class="gate">Nothing is posted until you approve in chat. Reply with changes (drop a clip, move a date,
swap a title) or say "approved" to schedule everything below.</div>
<table>{''.join(rows)}</table></body></html>
""", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("episode", type=Path)
    ap.add_argument("--start", help="earliest date for the full episode (default: target_publish_date or tomorrow)")
    a = ap.parse_args()
    cfg = load_json(a.episode / "episode.json", {})
    start_s = a.start or cfg.get("target_publish_date")
    start = dt.date.fromisoformat(start_s) if start_s else dt.date.today() + dt.timedelta(days=1)
    plan = build_plan(a.episode, start)
    out_dir = stage_dir(a.episode, "review")
    save_json(out_dir / "publish_plan.json", plan)
    render_review(a.episode, plan, out_dir / "review.html")
    for it in plan["items"]:
        print(f"{it['weekday']} {it['publish_at'][:16]}  {it['asset']:<12} {', '.join(it['networks']):<35} {it.get('title') or ''}")
    print(f"wrote {out_dir / 'publish_plan.json'} and review.html")


if __name__ == "__main__":
    main()
