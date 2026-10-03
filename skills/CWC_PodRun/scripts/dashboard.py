"""dashboard.py <RUN>      the episode's POSTING DASHBOARD in the NAS episode folder: <episode>/Final/<EpNN> Posting Plan.html
One self-contained page (no external files): the approved calendar day by day, every post's channel, route and status
(scheduled in Metricool / metadata written / waiting on a Studio upload / manual kit), the Metricool month counts, links
to the Clips Dashboard, the YouTube upload list, the manual kits and the Studio checklist. Re-run it any time: it reads
plan.json + publish_log.json and rewrites the page."""
import os, sys, html, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

def status(it, log, found):
    e = log.get(it['id'])
    if it['route'] == 'metricool': return ('Scheduled in Metricool', 'ok', e.get('plannerUrl')) if e else ('To schedule', 'todo', None)
    if it['route'] == 'manual': return ('Manual kit ready', 'warn', None) if e else ('Manual - kit not built', 'todo', None)
    if it['route'] == 'youtube_api': return ('Uploaded + scheduled', 'ok', f'https://studio.youtube.com/video/{e["video_id"]}/edit') if e else ('To upload', 'todo', None)
    if e: return ('Metadata written', 'ok', f'https://studio.youtube.com/video/{e["video_id"]}/edit')
    if it['id'] in found: return ('Found in Studio - metadata next', 'warn', None)
    return ('Waiting on your Studio upload', 'todo', None)

def main():
    R = sys.argv[1].rstrip('/') if len(sys.argv) > 1 else C.fail('dashboard.py <RUN>')
    r = C.run(R); P = C.load(f'{R}/plan.json') or C.fail('no plan.json'); log = C.load(f'{R}/publish_log.json', {}) or {}
    found = C.load(f'{R}/publish/youtube_found.json', {}) or {}; B = C.brands(); e = html.escape
    final = f'{r["episode_dir"]}/Final'
    if not os.path.isdir(r['episode_dir']): C.ask(f'episode folder not reachable (NAS mounted?): {r["episode_dir"]}')
    os.makedirs(final, exist_ok=True)
    rel = lambda p: os.path.relpath(p, final) if p else ''
    approved = (r.get('plan_approval') or {}).get('sha') == P['sha']
    rows, day = [], None
    for it in P['items']:
        if it['publish_at'][:10] != day:
            day = it['publish_at'][:10]; rows.append(f'<tr class="day"><td colspan="5">{e(it["weekday"])} {e(day)}</td></tr>')
        kind = {'yt_clip': 'YouTube clip', 'yt_short': 'YouTube Short', 'social': ' + '.join({'tiktok': 'TikTok'}.get(n, n.capitalize()) for n in it.get('networks', []))}[it['kind']]
        st, cls, link = status(it, log, found)
        f = (it.get('files') or {}).get('video')
        rows.append(f'<tr><td class="t">{e(it["publish_at"][11:16])}</td><td>{e(B[it["brand"]]["label"])}<br><small>{e(kind)}</small></td>'
                    f'<td><b>{e(it["title"])}</b>' + (f'<br><small><a href="{e(rel(f))}">{e(os.path.basename(f))}</a></small>' if f else '') + '</td>'
                    f'<td><small>{e(it["route"])}</small></td><td><span class="{cls}">{e(st)}</span>' + (f'<br><small><a href="{e(link)}">open</a></small>' if link else '') + '</td></tr>')
    caps = ''.join(f'<li>{e(B[b]["label"])} {e(mo)}: {v["used_before"]} used + {v["planned_metricool"]} planned / {v["cap"]}, {v["manual"]} manual <small>({e(v["source"])})</small></li>'
                   for b, ms in P['counts'].items() for mo, v in ms.items())
    links = [(p, os.path.basename(p)) for p in sorted(glob.glob(f'{final}/Clips/*Dashboard*.html'))]
    for p in (f'{final}/YouTube Upload List.md', f'{final}/Manual Posts', f'{R}/publish/studio_checklist.md'):
        if os.path.exists(p): links.append((p, os.path.basename(p)))
    link_html = ' &middot; '.join(f'<a href="{e(rel(p) if p.startswith(final) else "file://" + p)}">{e(t)}</a>' for p, t in links)
    page = f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(r["ep_key"])} Posting Plan</title><style>
:root{{--bg:#0B0F14;--card:#111827;--fg:#E5E7EB;--mut:#9CA3AF;--acc:#7C3AED;--lime:#A3FF12;--warn:#F59E0B;--line:#1F2937}}
body{{margin:0;padding:24px 16px;background:var(--bg);color:var(--fg);font:15px/1.5 -apple-system,Inter,system-ui,sans-serif}}
h1{{font-size:22px;margin:0}} .sub{{color:var(--mut);margin:4px 0 16px}} a{{color:var(--lime)}}
table{{width:100%;border-collapse:collapse;background:var(--card)}} td{{padding:9px 10px;border-top:1px solid var(--line);vertical-align:top}}
tr.day td{{background:#0F172A;color:var(--lime);font-weight:600;letter-spacing:.04em}} td.t{{font-variant-numeric:tabular-nums;white-space:nowrap}}
small{{color:var(--mut)}} .ok{{color:var(--lime)}} .warn{{color:var(--warn)}} .todo{{color:#F87171}}
.box{{background:var(--card);border-left:4px solid var(--acc);padding:10px 14px;margin:16px 0}} ul{{margin:6px 0;padding-left:18px}}
</style></head><body>
<h1>{e(r["show_name"])} {e(r["ep_key"])} &middot; Posting Plan</h1>
<div class="sub">{e(P["window"]["start_dow"])} {e(P["window"]["start"])} &rarr; {e(P["window"]["end_dow"])} {e(P["window"]["end"])} (ET) &middot; plan {e(P["sha"])} &middot;
{"approved by " + e(r["plan_approval"]["by"]) + " " + e(r["plan_approval"]["at"]) if approved else "NOT APPROVED YET"} &middot; YouTube route: {e(P["youtube_route"])}</div>
<div class="box">{link_html or "no linked files yet"}</div>
<table>{"".join(rows)}</table>
<div class="box"><b>Metricool month counts</b><ul>{caps}</ul></div>
{"<div class='box'><b>Notes</b><ul>" + "".join(f"<li>{e(w)}</li>" for w in P["warnings"]) + "</ul></div>" if P["warnings"] else ""}
<div class="sub">Rebuilt {e(C.now())} by CWC_PodRun dashboard.py</div></body></html>"""
    out = f'{final}/{r["ep_key"]} Posting Plan.html'; open(out, 'w', encoding='utf-8').write(page); print(out)

if __name__ == '__main__': main()
