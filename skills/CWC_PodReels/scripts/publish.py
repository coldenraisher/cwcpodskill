"""publish.py - the approved, mastered shorts -> Google Drive -> a Metricool plan Colden approves on Telegram -> posts.
Ported from edit-shorts publish.py (Colden 2026-09-13 rules) with ruling 11 (2026-10-02): "use metricool and we can cut
when needed to stay in limit". Metricool is reachable only as MCP connectors, so this script does the deterministic
half and Claude fires the calls (CWC = the claude.ai connector, blogId 5965295; TCL = `metricool-tcl`, 6367106).

  publish.py upload <WORK>     master (<shorts_dir>/Renders/NN Title.mp4) + the PICKED cover -> rclone gdrive:Shorts
                               Upload/<Colden|TCL>/ per brand; direct links -> review/publish.json. Needs the batch card
                               approved (copy.json status approved + cover).
  publish.py plan <WORK> [--start YYYY-MM-DD]
        BEFORE it, Claude writes from the connectors (per brand): review/best_times.json from getBestTimeToPostByNetwork
        socialNetwork=tiktok ({brand: [{"dow": 0-6, "hour": H, "value": V}]}), review/busy_days.json + review/month_counts.json
        from getScheduledPosts over the window's months ({brand: [dates]}, {brand: {"YYYY-MM": n}}).
        Creative Lens cadence (show file publishing.cadence): edit Thursday, post Friday -> Thursday, one a day per brand,
        extras as second posts on the busiest days >= 3 h apart; a short going to both posts to Create with Colden FIRST,
        The Creative Lens >= 1 h later. MONTH CAP (publishing.month_cap, TCL 20): posts already scheduled that month +
        this plan over the cap -> the lowest-ranked shorts of that brand (checked.json deliver order) go on a CUT list
        (they still post on the other brand when they go to both). A brand with no cap on file -> ASK (exit 2).
        -> review/publish_plan.json + one calendar card per brand (plan_card.py) for tg_plan.py.
  publish.py payloads <WORK>   plan + links + copy -> review/publish_payloads.json: one createScheduledPost per (short,
                               brand). youtubeData.playlistId is never sent (the connector drops it - his click).
  publish.py record <WORK> <id> <brand> <post_id>   after the connector created the post
  publish.py export <WORK>     Todd-only shorts (Colden and Todd): master + cover + copy -> Renders/Todd/, never Metricool
  publish.py status <WORK>
GATES: nothing is planned without the batch approval; nothing is created without "PLAN APPROVED" (tg_plan.py) - and
Claude, not this script, creates the posts."""
import os, re, sys, json, shutil, subprocess, datetime as dt
from zoneinfo import ZoneInfo
import common as C
BR = {'cwc': 'Create with Colden', 'tcl': 'The Creative Lens'}; LEAD_HOURS = 1; MIN_GAP_H = 3
def ppath(W): return f'{W}/review/publish.json'
def pstate(W): return C.load(ppath(W), {'links': {}, 'posts': {}}) or {'links': {}, 'posts': {}}
def pub(W): return C.show(C.episode(W)['show'])['publishing']
def ready(W):
    """[(id, copy row, master file)] approved on the batch card, in the episode's rank order"""
    cp = (C.load(f'{W}/copy.json') or {}).get('shorts', {}); order = (C.load(f'{W}/checked.json') or {}).get('deliver', []) + list(cp)
    out = []
    for sid in dict.fromkeys(order):
        c = cp.get(sid)
        if not c or c.get('status') != 'approved' or not c.get('cover'): continue
        v = next((x for x in C.load(f'{W}/edit/{sid}/versions.json', []) if x.get('status') == 'approved'), None)
        m = (v or {}).get('master', {}).get('file')
        if not m or not os.path.exists(m): C.fail(f'{sid}: no master render (master.py render)')
        out.append((sid, c, m))
    return out
def rclone(*a):
    r = subprocess.run(['rclone', *a], capture_output=True, text=True)
    if r.returncode: C.fail(f'rclone {a[0]} failed: {r.stderr.strip()[-300:]}')
    return r.stdout.strip()

def upload(W):
    g = pub(W)['gdrive']; st = pstate(W); todo = ready(W)
    if not todo: C.fail('nothing approved on the batch card yet')
    for sid, c, m in todo:
        for b in c['brands']:
            have = st['links'].get(sid, {}).get(b, {})
            if have.get('size') == os.path.getsize(m) and have.get('cover_src') == c['cover']: print(sid, b, 'already uploaded'); continue
            dest = f'{g["remote"]}:{g["folder_name"]}/{g["subfolders"][b]}'; base = os.path.splitext(os.path.basename(m))[0]; links = {}
            for kind, f, name in (('video', m, os.path.basename(m)), ('thumb', c['cover'], f'{base} cover{os.path.splitext(c["cover"])[1]}')):
                rclone('copyto', f, f'{dest}/{name}', '--drive-chunk-size', '64M'); url = rclone('link', f'{dest}/{name}')
                fid = re.search(r'id=([\w-]+)', url) or re.search(r'/d/([\w-]+)', url)
                links[kind] = url; links[kind + '_direct'] = f'https://drive.google.com/uc?export=download&id={fid.group(1)}' if fid else url
            links.update(size=os.path.getsize(m), cover_src=c['cover'], at=C.now()); st['links'].setdefault(sid, {})[b] = links; C.save(ppath(W), st); print(sid, b, '->', links['video'])

def best_hour(bt, b, dow, fallback, used=()):
    rows = sorted([r for r in bt.get(b, []) if int(r['dow']) == dow], key=lambda r: -float(r.get('value', 0)))
    hours = [int(r['hour']) for r in rows] + [h for h in fallback if h not in [int(r['hour']) for r in rows]]
    return next((h for h in hours if h not in used), hours[0] if hours else 12)
def day_score(bt, b, dow): return max([float(r.get('value', 0)) for r in bt.get(b, []) if int(r['dow']) == dow] or [0.0])
def plan(W, start=None):
    P_ = pub(W); mc = P_['metricool']; tz = mc['cwc'].get('timezone', 'America/New_York'); caps = P_.get('month_cap') or {}
    if not P_.get('cadence'): C.ask('no cadence for this show (publishing.cadence) - ask Colden how often its shorts post')
    bt = C.load(f'{W}/review/best_times.json', {}) or {}; busy = C.load(f'{W}/review/busy_days.json', {}) or {}; counts = C.load(f'{W}/review/month_counts.json')
    if counts is None: C.fail('review/month_counts.json is missing - count the scheduled posts per brand and month first (getScheduledPosts)')
    todo = ready(W)
    if not todo: C.fail('nothing approved on the batch card yet')
    t = dt.date.today(); start_d = dt.date.fromisoformat(start) if start else t + dt.timedelta(days=(4 - t.weekday()) % 7 or 7)   # the coming Friday
    days = [start_d + dt.timedelta(days=i) for i in range(7)]; posts = []; cut = []
    for b in ('cwc', 'tcl'):
        sids = [sid for sid, c, _ in todo if b in c['brands']]
        if not sids: continue
        if not isinstance(caps.get(b), (int, type(None))) or b not in caps: C.ask(f'no monthly post cap on file for {BR[b]} (publishing.month_cap) - ask Colden what the Metricool plan allows')
        cap = caps[b]
        if cap is not None:                                          # ruling 11: cut the lowest-ranked to stay inside the plan
            while sids:
                per_month = {}
                for i, sid in enumerate(sids): m = days[min(i, 6)].strftime('%Y-%m'); per_month[m] = per_month.get(m, 0) + 1
                over = [m for m, n in per_month.items() if n + int((counts.get(b) or {}).get(m, 0)) > cap]
                if not over: break
                cut.append({'short': sids[-1], 'brand': b, 'why': f'{BR[b]} month cap {cap}: {over[0]} already has {int((counts.get(b) or {}).get(over[0], 0))} scheduled'}); sids = sids[:-1]
        free = [d for d in days if d.isoformat() not in set(busy.get(b, []))] or days
        extra = max(0, len(sids) - len(free)); doubles = set(sorted(free, key=lambda d: -day_score(bt, b, d.weekday()))[:extra]); used = {d: 0 for d in free}
        fallback = mc[b].get('default_hours') or [12, 17, 9]
        for sid in sids:
            lo = free[0]; cw = next((p for p in posts if p['short'] == sid and p['brand'] == 'cwc'), None)
            if cw: lo = dt.date.fromisoformat(cw['date'])
            d = next((x for x in free if x >= lo and used[x] < (2 if x in doubles else 1)), None) or max([x for x in free if x >= lo] or free[-1:], key=lambda x: day_score(bt, b, x.weekday()))
            same = [p['hour'] for p in posts if p['brand'] == b and p['date'] == d.isoformat()]
            block = set(h for s in same for h in range(s - MIN_GAP_H + 1, s + MIN_GAP_H))
            if cw and cw['date'] == d.isoformat(): block |= set(range(0, cw['hour'] + LEAD_HOURS))     # Create with Colden first, TCL >= 1 h later
            h = best_hour(bt, b, d.weekday(), fallback, block)
            if h in block:                                           # no legal hour that day -> the next free day
                d = next((x for x in free if x > d), d + dt.timedelta(days=1)); h = best_hour(bt, b, d.weekday(), fallback)
            used[d] = used.get(d, 0) + 1; posts.append({'short': sid, 'brand': b, 'date': d.isoformat(), 'hour': h})
    for p in posts:
        if p['brand'] == 'tcl':
            c = next((q for q in posts if q['short'] == p['short'] and q['brand'] == 'cwc'), None)
            if c: assert (p['date'], p['hour']) >= (c['date'], c['hour'] + LEAD_HOURS) or p['date'] > c['date'], f'{p} before {c}'
    cps = {sid: c for sid, c, _ in todo}
    for p in posts:
        c = cps[p['short']]; p.update(title=c['title'], when=dt.datetime(*map(int, p['date'].split('-')), p['hour'], 0, tzinfo=ZoneInfo(tz)).isoformat(), timezone=tz,
                                      playlist=(c.get('playlist') or {}).get(p['brand']), ig_collab=c.get('ig_collab', 'none') if p['brand'] in P_.get('ig_collab_brands', ['cwc']) else 'none', cover=c['cover'])
    posts.sort(key=lambda p: (p['date'], p['hour'], p['brand']))
    out = {'made_at': C.now(), 'start': start_d.isoformat(), 'posts': posts, 'cut': cut, 'month_counts': counts, 'caps': caps, 'best_times_used': bool(bt)}
    C.save(f'{W}/review/publish_plan.json', out)
    print(f'plan from {start_d} ({"best hours from TikTok" if bt else "show default hours"}):\n| Short | Brand | Day | Time | IG collab |\n|---|---|---|---|---|')
    for p in posts: print(f'| {p["short"].upper()} {p["title"]} | {BR[p["brand"]]} | {dt.date.fromisoformat(p["date"]).strftime("%a %b %-d")} | {p["hour"]:02d}:00 | {p["ig_collab"]} |')
    for x in cut: print(f'CUT {x["short"].upper()} from {BR[x["brand"]]}: {x["why"]}')
    import plan_card as PC
    for b in sorted({p['brand'] for p in posts}): print('card:', PC.render(W, b))

def payloads(W):
    pl = C.load(f'{W}/review/publish_plan.json') or C.fail('publish.py plan first'); st = pstate(W); mc = pub(W)['metricool']; cps = (C.load(f'{W}/copy.json') or {})['shorts']; calls = []
    collabs = {k.lower(): v for k, v in pub(W).get('ig_collaborators', {}).items() if not k.endswith('note')}
    for p in pl['posts']:
        sid, b = p['short'], p['brand']; c = cps[sid]; L = st['links'].get(sid, {}).get(b)
        if not L: C.fail(f'{sid} {b}: not uploaded (publish.py upload)')
        nets = mc[b]['networks']
        info = {'autoPublish': True, 'draft': False, 'text': c['caption'], 'firstCommentText': c['first_comment'], 'media': [L['video_direct']], 'videoThumbnailUrl': L['thumb_direct'], 'mediaAltText': [],
                'providers': [{'network': n} for n in nets], 'publicationDate': {'dateTime': p['when'][:19], 'timezone': p['timezone']}, 'shortener': False, 'smartLinkData': {'ids': []}, 'descendants': [], 'hasNotReadNotes': False}
        if 'youtube' in nets: info['youtubeData'] = {'title': c['yt_title'], 'type': 'short', 'privacy': 'public', 'category': 'FILM_ANIMATION', 'madeForKids': False, 'tags': [t.lstrip('#') for t in re.findall(r'#\w+', c['caption'])]}
        if 'facebook' in nets: info['facebookData'] = {'type': 'REEL', 'title': c.get('fb_title') or c['yt_title']}
        if 'instagram' in nets:
            ig = {'type': 'REEL', 'showReelOnFeed': True}; h = (p.get('ig_collab') or 'none').lstrip('@'); h = collabs.get(h.lower(), h)
            if h.lower() not in ('none', ''): ig['collaborators'] = [{'username': h, 'deleted': False}]
            info['instagramData'] = ig
        if 'tiktok' in nets: info['tiktokData'] = {'title': c['yt_title'][:90], 'privacyOption': 'PUBLIC_TO_EVERYONE'}
        calls.append({'short': sid, 'brand': b, 'connector': mc[b]['mcp'], 'playlist_manual': p.get('playlist'), 'args': {'blogId': str(mc[b]['blogId']), 'date': p['when'], 'info': info}})
    C.save(f'{W}/review/publish_payloads.json', {'made_at': C.now(), 'calls': calls}); print(len(calls), 'createScheduledPost calls -> review/publish_payloads.json')
    for k in calls: print(f' {k["short"]} {k["brand"]} {k["args"]["date"]} blogId {k["args"]["blogId"]} via {k["connector"][:30]}')

def record(W, sid, b, pid):
    st = pstate(W); st['posts'].setdefault(sid, {})[b] = {'id': pid, 'at': C.now()}; C.save(ppath(W), st)
    C.decision(W, {'stage': 'publish', 'short': sid, 'brand': b, 'decision': f'scheduled:{pid}'}); C.event(W, f'POSTED {sid} {b} id {pid}'); print('recorded')

def export(W):
    cp = (C.load(f'{W}/copy.json') or {}).get('shorts', {}); ep = C.episode(W); d = f'{ep["shorts_dir"]}/Renders/Todd'; n = 0
    for sid, c in cp.items():
        if c.get('destination') != 'todd': continue
        v = next(x for x in C.load(f'{W}/edit/{sid}/versions.json', []) if x.get('status') == 'approved'); m = v['master']['file']; os.makedirs(d, exist_ok=True)
        shutil.copy2(m, d); cover = c.get('cover')
        if cover: shutil.copy2(cover, f'{d}/{os.path.splitext(os.path.basename(m))[0]} cover{os.path.splitext(cover)[1]}')
        with open(f'{d}/README.txt', 'a') as fh: fh.write(f'\n{os.path.basename(m)}\nTitle: {c.get("yt_title")}\n{c.get("caption")}\nPinned comment: {c.get("first_comment")}\n')
        n += 1
    print(f'{n} Todd-only shorts -> {d}')

def status(W):
    st = pstate(W); pl = C.load(f'{W}/review/publish_plan.json') or {}
    for sid, c, m in ready(W): print(f'{sid}: {c["brands"]} uploaded {sorted(st["links"].get(sid, {}))} posted {st["posts"].get(sid, {})}')
    for x in pl.get('cut', []): print('cut:', x)

if __name__ == '__main__':
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    if len(a) < 2: C.fail(__doc__)
    W = os.path.abspath(a[1]); cmd = a[0]
    if cmd == 'upload': upload(W)
    elif cmd == 'plan': plan(W, sys.argv[sys.argv.index('--start') + 1] if '--start' in sys.argv else None)
    elif cmd == 'payloads': payloads(W)
    elif cmd == 'record' and len(a) >= 5: record(W, a[2], a[3], a[4])
    elif cmd == 'export': export(W)
    elif cmd == 'status': status(W)
    else: C.fail(__doc__)
