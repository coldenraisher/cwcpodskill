"""shorts_data.py - what has worked in Colden's SHORT-FORM, on every platform (Colden 2026-10-02: data drives selection,
retention first, then views; subs reported).

  pull [cwc|tcl|all]        YouTube Data + Analytics API (edit-clips' OAuth tokens, read + refresh only): every Short of
                            both channels -> data/shorts/youtube_<ch>.json: id, title, description, published, duration,
                            lifetime views / engaged views / avg view duration / avg % viewed / subs / likes / comments /
                            shares; for the last 180 days also the first 7 days, the retention curve (kept at 3 s / 50 %
                            / end), traffic sources (Shorts feed vs search vs ...).
  metricool <brand> <network> <rows.json> [--from YYYY-MM-DD]
                            stores what Claude pulled through the Metricool MCP (getAnalyticsDataByMetrics; it is not
                            callable from Python) -> data/shorts/metricool/<brand>_<network>.json. The rows MUST be
                            requested with exactly the field list printed by `metricool-fields <network>` (row order).
  metricool-fields <network>   the field ids to request (tiktok | instagram)
  join                      one catalog row per short across YouTube / TikTok / Instagram (matched by the caption Metricool
                            posted everywhere + the day) -> data/shorts/catalog.json
  summary                   data/shorts/summary.md - the tables Claude reads before scoring (cite ids from it)
  fresh                     exit 0 when YouTube pulls are < 36 h old and the Metricool rows < 7 days; exit 1 otherwise
GATE: a pull that fails writes nothing (the old file keeps its old date, so `fresh` fails)."""
import os, re, sys, json, datetime, statistics
import common as C
SCOPES = ['https://www.googleapis.com/auth/youtube', 'https://www.googleapis.com/auth/youtube.upload', 'https://www.googleapis.com/auth/youtube.force-ssl', 'https://www.googleapis.com/auth/yt-analytics.readonly']
CHANNELS = {'cwc': 'Create with Colden (@ColdenRaisher)', 'tcl': 'The Creative Lens (@TheCreativeLensShow)'}
M_LIFE = 'views,engagedViews,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,subscribersGained,likes,comments,shares'
FRESH_H = 36; METRICOOL_DAYS = 7; DEEP_DAYS = 180
FIELDS = {   # Metricool Data Studio ids, in the order the rows come back
    'tiktok': [('TKPO02', 'posted'), ('TKPO03', 'url'), ('TKPO05', 'text'), ('TKPO06', 'duration'), ('TKPO07', 'views'), ('TKPO08', 'likes'),
               ('TKPO09', 'comments'), ('TKPO10', 'shares'), ('TKPO11', 'reach'), ('TKPO13', 'full_watch_rate'), ('TKPO14', 'total_time_s'),
               ('TKPO15', 'avg_watch_s'), ('TKPO16', 'src_for_you'), ('TKPO17', 'src_follow'), ('TKPO20', 'src_profile'), ('TKPO21', 'src_search')],
    'instagram': [('IGRE02', 'posted'), ('IGRE06', 'url'), ('IGRE03', 'text'), ('IGRE23', 'views'), ('IGRE11', 'reach'), ('IGRE24', 'avg_watch_s'),
                  ('IGRE27', 'avg_pct_viewed'), ('IGRE28', 'view_rate_3s'), ('IGRE10', 'likes'), ('IGRE07', 'comments'), ('IGRE21', 'shares'), ('IGRE12', 'saved')],
}
BLOG = {'cwc': '5965295', 'tcl': '6367106'}

def creds(ch):
    import warnings; warnings.simplefilter('ignore')
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    tok = f'{C.YT_CFG}/{ch}.json'
    if not os.path.exists(tok): C.ask(f'no YouTube token for "{ch}" ({tok}). Colden signs in once: python3 ~/.claude/skills/edit-clips/scripts/yt_upload.py auth {ch}')
    c = Credentials.from_authorized_user_file(tok, SCOPES)
    if not c.valid:
        if c.expired and c.refresh_token: c.refresh(Request()); open(tok, 'w').write(c.to_json())
        else: C.ask(f'the YouTube token for "{ch}" cannot be refreshed - Colden signs in again (edit-clips yt_upload.py auth {ch})')
    return c

def services(ch):
    import warnings; warnings.simplefilter('ignore')
    from googleapiclient.discovery import build
    c = creds(ch); return build('youtube', 'v3', credentials=c, cache_discovery=False), build('youtubeAnalytics', 'v2', credentials=c, cache_discovery=False)

def iso_dur(s):
    m = re.match(r'P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', s or ''); d, h, mi, se = [int(x or 0) for x in m.groups()]
    return d * 86400 + h * 3600 + mi * 60 + se

def rows(ya, start, end, **kw):
    r = ya.reports().query(ids='channel==MINE', startDate=start, endDate=end, **kw).execute()
    names = [h['name'] for h in r['columnHeaders']]; return [dict(zip(names, row)) for row in r.get('rows', [])]

def curve_facts(curve, dur):
    """a Short's curve (ratio -> audienceWatchRatio; it can start over 1.0 because Shorts loop): kept at 3 s, at half, at
    the end, and the steepest drop after the first 3 s"""
    if not curve or not dur: return {}
    def at(r):
        r = min(max(r, curve[0][0]), curve[-1][0])
        for (a, va), (b, vb) in zip(curve, curve[1:]):
            if a <= r <= b: return va + (vb - va) * (r - a) / (b - a) if b > a else va
        return curve[-1][1]
    out = {'kept_3s': round(at(3.0 / dur), 3), 'kept_50': round(at(.5), 3), 'kept_end': round(at(0.98), 3)}
    best = None
    for i in range(len(curve) - 5):
        if curve[i][0] * dur < 3.0 or curve[i + 5][0] > 0.95: continue
        d = curve[i][1] - curve[i + 5][1]
        if best is None or d > best[0]: best = (d, curve[i][0])
    if best: out['steepest_drop'] = {'at_sec': round(best[1] * dur, 1), 'lost': round(best[0], 3)}
    return out

def pull(ch):
    yt, ya = services(ch); today = datetime.date.today()
    me = yt.channels().list(part='snippet,contentDetails,statistics', mine=True).execute()['items'][0]
    ids = []; tok = None
    while True:
        r = yt.playlistItems().list(part='contentDetails', playlistId=me['contentDetails']['relatedPlaylists']['uploads'], maxResults=50, pageToken=tok).execute()
        ids += [i['contentDetails']['videoId'] for i in r['items']]; tok = r.get('nextPageToken')
        if not tok: break
    vids = {}
    for i in range(0, len(ids), 50):
        for v in yt.videos().list(part='snippet,contentDetails,statistics,liveStreamingDetails,status', id=','.join(ids[i:i + 50])).execute()['items']:
            dur = iso_dur(v['contentDetails'].get('duration'))
            if v.get('liveStreamingDetails') or dur > 180: continue
            vids[v['id']] = {'id': v['id'], 'title': v['snippet']['title'], 'description': v['snippet'].get('description', '')[:600], 'published': v['snippet']['publishedAt'],
                             'duration': dur, 'privacy': v['status'].get('privacyStatus'), 'public_views': int(v['statistics'].get('viewCount', 0))}
    start0 = me['snippet']['publishedAt'][:10]; end = today.isoformat(); allids = list(vids)
    for i in range(0, len(allids), 200):
        for row in rows(ya, start0, end, metrics='views', dimensions='video,creatorContentType', filters='video==' + ','.join(allids[i:i + 200]), maxResults=200):
            v = vids.get(row['video'])
            if v: v['yt_kind'] = row['creatorContentType']
        for row in rows(ya, start0, end, metrics=M_LIFE, dimensions='video', filters='video==' + ','.join(allids[i:i + 200]), maxResults=200):
            v = vids.get(row.pop('video'))
            if v: v['life'] = row
    vids = {k: v for k, v in vids.items() if v.get('yt_kind', 'shorts') == 'shorts'}
    cutoff = (today - datetime.timedelta(days=DEEP_DAYS)).isoformat(); deep = [v for v in vids.values() if v['privacy'] == 'public' and v['published'][:10] >= cutoff]
    for v in deep:
        p0 = v['published'][:10]; f = f'video=={v["id"]}'; d7 = min(today, datetime.date.fromisoformat(p0) + datetime.timedelta(days=7)).isoformat()
        try:
            r7 = rows(ya, p0, d7, metrics=M_LIFE, filters=f); v['first7'] = r7[0] if r7 else {}
            cv = rows(ya, p0, end, metrics='audienceWatchRatio', dimensions='elapsedVideoTimeRatio', filters=f)
            v['curve'] = [[c['elapsedVideoTimeRatio'], round(c['audienceWatchRatio'], 4)] for c in cv]; v['retention'] = curve_facts(v['curve'], v['duration'])
            v['traffic'] = {t['insightTrafficSourceType']: t['views'] for t in rows(ya, p0, end, metrics='views', dimensions='insightTrafficSourceType', filters=f, sort='-views')}
        except Exception as e: v['deep_error'] = str(e)[:160]
    out = {'channel': ch, 'name': me['snippet']['title'], 'subs': int(me['statistics'].get('subscriberCount', 0)), 'pulled_at': C.now(), 'n': len(vids),
           'shorts': sorted(vids.values(), key=lambda v: v['published'], reverse=True)}
    C.save(f'{C.DATA}/youtube_{ch}.json', out)
    print(f'{ch}: {len(vids)} Shorts, deep stats on {len(deep)} ({sum(1 for v in deep if v.get("deep_error"))} errors)')

def num(x):
    try: return float(x)
    except (TypeError, ValueError): return None

def metricool(brand, network, path, since=None):
    if brand not in BLOG or network not in FIELDS: C.fail(f'brand one of {list(BLOG)}, network one of {list(FIELDS)}')
    raw = C.load(path); rws = raw.get('rows') if isinstance(raw, dict) else raw
    if not isinstance(rws, list): C.fail(f'{path}: expected {{"rows": [...]}} as getAnalyticsDataByMetrics returns it')
    names = [n for _, n in FIELDS[network]]; out = []
    for r in rws:
        if len(r) != len(names): C.fail(f'a row has {len(r)} values, the field list has {len(names)} - request exactly: {",".join(i for i, _ in FIELDS[network])}')
        d = dict(zip(names, r))
        for k, v in d.items():
            if k not in ('posted', 'url', 'text'): d[k] = num(v)
        out.append(d)
    C.save(f'{C.DATA}/metricool/{brand}_{network}.json', {'brand': brand, 'network': network, 'blogId': BLOG[brand], 'pulled_at': C.now(), 'since': since,
                                                          'fields': [i for i, _ in FIELDS[network]], 'rows': out})
    print(f'{brand} {network}: {len(out)} posts stored')

def key(text):
    w = C.norm(re.sub(r'#\w+', ' ', text or ''))
    return ' '.join(w[:8])

def day(s):
    s = str(s or '')
    if re.fullmatch(r'\d{8}(\d{6})?', s): return datetime.date(int(s[:4]), int(s[4:6]), int(s[6:8]))
    try: return datetime.date.fromisoformat(s[:10])
    except ValueError: return None

def join():
    """one row per short: YouTube (both channels) and the Metricool posts of the same text within 2 days"""
    cat = []; mc = {}
    for b in BLOG:
        for n in FIELDS:
            d = C.load(f'{C.DATA}/metricool/{b}_{n}.json')
            if d: mc[(b, n)] = d['rows']
    used = set()
    for ch in CHANNELS:
        y = C.load(f'{C.DATA}/youtube_{ch}.json') or {}
        for v in y.get('shorts', []):
            r = {'brand': ch, 'title': v['title'], 'published': v['published'][:10], 'duration': v['duration'], 'youtube': {'id': v['id'], **{k: v.get(k) for k in ('life', 'first7', 'retention', 'traffic')}}}
            k = key(v.get('description')) or key(v['title']); d0 = day(v['published'])
            for (b, n), rws in mc.items():
                if b != ch: continue
                hit = next((x for x in rws if (b, n, x['url']) not in used and key(x['text']) == k and d0 and day(x['posted']) and abs((day(x['posted']) - d0).days) <= 2), None)
                if hit: used.add((b, n, hit['url'])); r[n] = hit
            cat.append(r)
    rest = []                                            # Metricool posts with no YouTube twin: TikTok + Instagram of the same text join
    for (b, n), rws in mc.items():
        for x in rws:
            if (b, n, x['url']) in used: continue
            k = key(x['text']); d0 = day(x['posted'])
            twin = next((r for r in rest if r['brand'] == b and n not in r and r['_k'] == k and d0 and r['_d'] and abs((r['_d'] - d0).days) <= 2), None)
            if twin: twin[n] = x; twin['duration'] = twin.get('duration') or x.get('duration')
            else: rest.append({'brand': b, 'title': (x['text'] or '')[:90], 'published': str(d0 or ''), 'duration': x.get('duration'), n: x, 'no_youtube': True, '_k': k, '_d': d0})
    for r in rest: r.pop('_k'); r.pop('_d'); cat.append(r)
    cat.sort(key=lambda r: r['published'], reverse=True)
    C.save(f'{C.DATA}/catalog.json', {'made_at': C.now(), 'n': len(cat), 'shorts': cat}); print(f'catalog: {len(cat)} shorts')
    return cat

def fresh():
    probs = []
    for ch in CHANNELS:
        d = C.load(f'{C.DATA}/youtube_{ch}.json')
        if not d: probs.append(f'YouTube {ch}: never pulled (shorts_data.py pull)')
        elif C.age_hours(d['pulled_at']) > FRESH_H: probs.append(f'YouTube {ch}: pulled {C.age_hours(d["pulled_at"]):.0f} h ago (limit {FRESH_H} h)')
    for b in BLOG:
        for n in FIELDS:
            d = C.load(f'{C.DATA}/metricool/{b}_{n}.json')
            if not d: probs.append(f'Metricool {b} {n}: never pulled (getAnalyticsDataByMetrics -> shorts_data.py metricool)')
            elif C.age_hours(d['pulled_at']) > METRICOOL_DAYS * 24: probs.append(f'Metricool {b} {n}: {C.age_hours(d["pulled_at"]) / 24:.0f} days old (limit {METRICOOL_DAYS})')
    return probs

def summary():
    cat = (C.load(f'{C.DATA}/catalog.json') or {}).get('shorts') or join()
    L = ['# Short-form data - what has worked (read before scoring; cite the ids in the first column as evidence)', '',
         'Goal (Colden 2026-10-02): RETENTION first (YouTube avg % viewed + kept at 3 s, TikTok avg watch time, Instagram 3-second view rate), then views; subs reported.',
         'fwr = TikTok full-video-watched rate as Metricool reports it (unit unverified - compare between shorts only).', '']
    for ch in CHANNELS:
        rs = [r for r in cat if r['brand'] == ch and r['published'] >= (datetime.date.today() - datetime.timedelta(days=150)).isoformat()]
        if not rs: continue
        L += [f'## {CHANNELS[ch]} - {len(rs)} shorts in 150 days', '',
              '| evidence id | posted | len | title | YT views | YT % viewed | YT kept 3s | YT subs | TT views | TT avg s | TT fwr | TT FYP | IG views | IG avg s | IG 3s rate |',
              '|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|']
        for r in rs:
            y = r.get('youtube') or {}; lf = y.get('life') or {}; rt = y.get('retention') or {}; t = r.get('tiktok') or {}; g = r.get('instagram') or {}
            eid = y.get('id') or (t.get('url') or g.get('url') or '')
            f = lambda v, d=0: '' if v is None else (f'{v:.{d}f}' if isinstance(v, float) else str(v))
            L.append(f'| {eid} | {r["published"]} | {r.get("duration") or ""} | {r["title"][:60]} | {f(lf.get("views"))} | {f(lf.get("averageViewPercentage"), 1)} | {f(rt.get("kept_3s"), 2)} | {f(lf.get("subscribersGained"))} | '
                     f'{f(t.get("views"))} | {f(t.get("avg_watch_s"), 1)} | {f(t.get("full_watch_rate"), 4)} | {f(t.get("src_for_you"), 2)} | {f(g.get("views"))} | {f(g.get("avg_watch_s"), 1)} | {f(g.get("view_rate_3s"), 2)} |')
        L.append('')
        def med(vals):
            vals = [v for v in vals if v is not None]; return round(statistics.median(vals), 2) if vals else None
        L += [f'medians ({ch}): YT views {med([((r.get("youtube") or {}).get("life") or {}).get("views") for r in rs if r.get("youtube")])}, '
              f'YT % viewed {med([((r.get("youtube") or {}).get("life") or {}).get("averageViewPercentage") for r in rs if r.get("youtube")])}, '
              f'TT views {med([(r.get("tiktok") or {}).get("views") for r in rs])}, TT avg watch {med([(r.get("tiktok") or {}).get("avg_watch_s") for r in rs])} s, '
              f'IG views {med([(r.get("instagram") or {}).get("views") for r in rs])}, IG 3 s rate {med([(r.get("instagram") or {}).get("view_rate_3s") for r in rs])}', '']
    lp = f'{C.DATA}/learnings.md'
    if os.path.exists(lp): L += ['## Learnings (learn.py report: past approvals, kills, notes, and what posted shorts did)', '', open(lp).read()]
    for p in C.SCRAPE:
        d = C.load(p)
        if d and d.get('shorts'):
            L += [f'## Monday Studio scrape - shorts block ({p}, updated {d.get("updated")})', '', '```', json.dumps(d['shorts'], indent=0)[:6000], '```', '']; break
    C.save(f'{C.DATA}/_summary_marker.json', {'at': C.now()})
    open(f'{C.DATA}/summary.md', 'w').write('\n'.join(L) + '\n'); print(f'{C.DATA}/summary.md')
    import pack_learn as PL; PL.build()                                       # the packaging brief from the same catalog (titles / hooks / captions come FROM it)

def evidence_ids():
    """every id a theme may cite: YouTube Short ids + TikTok / Instagram post urls"""
    ids = set()
    for r in (C.load(f'{C.DATA}/catalog.json') or {}).get('shorts', []):
        if r.get('youtube'): ids.add(r['youtube']['id'])
        for n in ('tiktok', 'instagram'):
            if r.get(n) and r[n].get('url'): ids.add(r[n]['url'])
    return ids

if __name__ == '__main__':
    a = sys.argv[1:]; cmd = a[0] if a else ''
    if cmd == 'pull':
        for ch in (CHANNELS if len(a) < 2 or a[1] == 'all' else [a[1]]): pull(ch)
        join(); summary()
    elif cmd == 'metricool':
        if len(a) < 4: C.fail(__doc__)
        metricool(a[1], a[2], a[3], a[a.index('--from') + 1] if '--from' in a else None)
    elif cmd == 'metricool-fields': print(json.dumps([i for i, _ in FIELDS[a[1]]]))
    elif cmd == 'join': join()
    elif cmd == 'summary': join(); summary()
    elif cmd == 'fresh':
        p = fresh(); [print('STALE', x) for x in p]; sys.exit(1 if p else 0)
    else: print(__doc__)
