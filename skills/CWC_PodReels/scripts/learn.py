"""learn.py - the loop that makes the next episode's picks better (ruling 2: data drives selection).
  learn.py snapshot      every PUBLISHED short of every episode (review/publish.json posts + the plan's dates) matched to
                         its catalog row (shorts_data.py join: YouTube + TikTok + Instagram by title / caption + day) ->
                         one row per short per run in data/shorts/published_snapshots.jsonl {age_h, YT views, % viewed,
                         kept 3 s, subs, TT views, avg watch, IG views, 3 s rate}. Run after `shorts_data.py pull` +
                         the Metricool pulls (the Monday run does both) - the report reads the snapshot nearest 48 h and 7 d.
  learn.py calibrate     TikTok "full video watched" as Metricool reports it (0.0001-0.002 - unit unknown) against the
                         Monday Studio scrape's watched_full_pct for the same videos (caption + day) -> data/shorts/
                         calibration.json {tiktok_fwr_factor, n}. summary.md then shows fwr in Studio's own percent.
  learn.py report        data/shorts/learnings.md (summary.md carries it, read before scoring): theme approvals vs
                         kills (score, length, news, who hooks), every note he wrote at the edit / batch / plan, which
                         covers he picks (Resolve vs AI), where he sends shorts, and a table of published shorts at 48 h
                         and 7 d next to the score they had."""
import os, sys, json, statistics, datetime as dt
import common as C, shorts_data as SD
def jl(p): return [json.loads(l) for l in open(p)] if os.path.exists(p) else []
SNAP = f'{C.DATA}/published_snapshots.jsonl'
def published():
    """[(work, short id, brand, posted date, yt_title, caption, ep_key)] for every short this skill scheduled"""
    out = []
    for W in C.works():
        ps = (C.load(f'{W}/review/publish.json') or {}).get('posts', {}); plan = {(p['short'], p['brand']): p for p in (C.load(f'{W}/review/publish_plan.json') or {}).get('posts', [])}
        cp = (C.load(f'{W}/copy.json') or {}).get('shorts', {}); ep = C.episode(W)
        for sid, bs in ps.items():
            for b in bs:
                p = plan.get((sid, b))
                if p: out.append((W, sid, b, p['date'], (cp.get(sid) or {}).get('yt_title', ''), (cp.get(sid) or {}).get('caption', ''), ep['ep_key']))
    return out
def match(cat, brand, date, title, caption):
    d0 = dt.date.fromisoformat(date); kt, kc = SD.key(title), SD.key(caption)
    for r in cat:
        if r['brand'] != brand or abs((dt.date.fromisoformat(r['published'][:10]) - d0).days) > 1: continue
        if SD.key(r['title']) in (kt, kc) or (kc and SD.key(r['title'])[:30] == kc[:30]): return r
    return None
def snapshot():
    cat = (C.load(f'{C.DATA}/catalog.json') or {}).get('shorts') or SD.join(); n = 0; now = dt.datetime.now().astimezone()
    with open(SNAP, 'a') as f:
        for W, sid, b, date, t, cap, epk in published():
            r = match(cat, b, date, t, cap)
            if not r: print(f'{epk} {sid} {b}: not in the catalog yet (pull again after it posts)'); continue
            y = r.get('youtube') or {}; lf = y.get('life') or {}; tt = r.get('tiktok') or {}; ig = r.get('instagram') or {}
            row = {'at': C.now(), 'ep': epk, 'short': sid, 'brand': b, 'posted': date, 'age_h': round((now - dt.datetime.fromisoformat(date + 'T12:00:00').astimezone()).total_seconds() / 3600, 1),
                   'yt_views': lf.get('views'), 'yt_pct_viewed': lf.get('averageViewPercentage'), 'yt_kept_3s': (y.get('retention') or {}).get('kept_3s'), 'yt_subs': lf.get('subscribersGained'),
                   'tt_views': tt.get('views'), 'tt_avg_s': tt.get('avg_watch_s'), 'tt_fwr': tt.get('full_watch_rate'), 'ig_views': ig.get('views'), 'ig_3s': ig.get('view_rate_3s')}
            f.write(json.dumps(row) + '\n'); n += 1
    print(f'{n} snapshot rows -> {SNAP}')
def calibrate():
    cat = (C.load(f'{C.DATA}/catalog.json') or {}).get('shorts') or []; sc = next((C.load(p) for p in C.SCRAPE if (C.load(p) or {}).get('shorts')), None)
    if not sc: C.fail('no Monday scrape with a "shorts" block yet (channel_metrics.json)')
    ratios = []
    for t in sc['shorts'].get('tiktok', []):
        if t.get('watched_full_pct') is None: continue
        r = match(cat, t.get('account', 'cwc'), t['posted'], t.get('caption', ''), t.get('caption', ''))
        m = ((r or {}).get('tiktok') or {}).get('full_watch_rate')
        if m: ratios.append(float(t['watched_full_pct']) / float(m))
    if len(ratios) < 3: C.fail(f'only {len(ratios)} TikTok videos match between Studio and Metricool - need 3')
    out = {'tiktok_fwr_factor': round(statistics.median(ratios), 2), 'n': len(ratios), 'spread': [round(min(ratios), 2), round(max(ratios), 2)], 'at': C.now()}
    C.save(f'{C.DATA}/calibration.json', out); print(out)
def report():
    dec = [d for d in jl(f'{C.DATA}/decisions.jsonl') if not d.get('trial')]; L = ['### Theme decisions (Telegram)']
    final = {}
    for d in dec:
        if d.get('stage') == 'theme' and d['decision'] in ('approved', 'killed'): final[(d['show'], d['ep'], d['theme'])] = d
    ap = [d for d in final.values() if d['decision'] == 'approved']; ki = [d for d in final.values() if d['decision'] == 'killed']
    def avg(rows, f):
        x = [f(r) for r in rows if (r.get('attrs') or {}) and f(r) is not None]; return round(statistics.mean(x), 1) if x else 'n/a'
    L.append(f'{len(ap)} approved, {len(ki)} killed over {len({(d["show"], d["ep"]) for d in final.values()})} episode(s).' if final else 'none yet')
    for name, f in (('score', lambda d: d['attrs'].get('total')), ('seconds', lambda d: d['attrs'].get('est_seconds')), ('news share %', lambda d: 100.0 * bool(d['attrs'].get('news')))):
        if final: L.append(f'- {name}: approved {avg(ap, f)} vs killed {avg(ki, f)}')
    for d in ki: L.append(f'- KILLED {d["ep"]} "{d["title"]}" ({(d.get("attrs") or {}).get("total")})' + (f' - {d["notes"]}' if d.get('notes') else ''))
    for d in dec:
        if d.get('stage') == 'theme' and d['decision'] == 'notes': L.append(f'- THEME NOTES {d["ep"]} "{d.get("title")}": {d.get("notes")}')
    L += ['', '### What he said after the theme stage (read before cutting, b-roll, covers, copy, plans)']
    for d in dec:
        if d.get('stage') in ('edit', 'batch', 'plan') and d.get('notes'): L.append(f'- {d["stage"].upper()} {d.get("ep", "")} {d.get("short", "")} {d.get("version", "")}: {d["notes"]}')
    dests = {}; covers = {}
    for d in dec:
        if d.get('stage') == 'edit' and str(d['decision']).startswith('approved:'): k = d['decision'].split(':')[1]; dests[k] = dests.get(k, 0) + 1
        if d.get('stage') == 'batch' and str(d['decision']).startswith('cover:'): k = {'1': 'Resolve still', '2': 'AI'}[d['decision'].split(':')[1]]; covers[k] = covers.get(k, 0) + 1
    if dests: L.append(f'- where he sent approved shorts: {dests}')
    if covers: L.append(f'- covers he picked: {covers}')
    cal = C.load(f'{C.DATA}/calibration.json')
    if cal: L.append(f'- TikTok full-watch calibration: Studio % = Metricool fwr x {cal["tiktok_fwr_factor"]} (n={cal["n"]})')
    snaps = jl(SNAP); L += ['', '### Published shorts at 48 h and 7 d', '| ep | short | brand | score | at | YT views | YT % viewed | TT views | TT avg s | IG views | IG 3s |', '|---|---|---|---|---|---|---|---|---|---|---|']
    scores = {(d['ep'], d['theme']): (d.get('attrs') or {}).get('total') for d in ap}
    for k in sorted({(s['ep'], s['short'], s['brand']) for s in snaps}):
        mine = [s for s in snaps if (s['ep'], s['short'], s['brand']) == k]
        for target in (48, 168):
            s = min(mine, key=lambda s: abs(s['age_h'] - target))
            if abs(s['age_h'] - target) > target * 0.5: continue
            L.append(f'| {k[0]} | {k[1]} | {k[2]} | {scores.get((k[0], k[1]), "")} | {target // 24 if target > 48 else 2} d | {s["yt_views"]} | {s["yt_pct_viewed"]} | {s["tt_views"]} | {s["tt_avg_s"]} | {s["ig_views"]} | {s["ig_3s"]} |')
    if not snaps: L.append('| none yet (learn.py snapshot after the first posts go live) ||||||||||')
    open(f'{C.DATA}/learnings.md', 'w').write('\n'.join(L) + '\n'); print(f'{C.DATA}/learnings.md: {len(final)} theme decisions, {len(snaps)} snapshot rows')
if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    if cmd == 'snapshot': snapshot()
    elif cmd == 'calibrate': calibrate()
    elif cmd == 'report': report(); SD.summary()
    else: C.fail(__doc__)
