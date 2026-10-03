"""channel_data.py pull [cwc|tcl|all]   |   channel_data.py summary   |   channel_data.py fresh
What has worked on Colden's own channels, pulled from the YouTube Data + Analytics APIs with the OAuth tokens edit-clips
made (~/.config/edit-clips/youtube/{cwc,tcl}.json; read + refresh only, never an interactive sign-in from here).

pull     data/channels/<ch>/videos.json   every upload: id, title, published, duration, kind (long / short / live),
                                          lifetime views, engaged views, minutes, average view duration, average %
                                          viewed, subs gained, likes, comments, shares
                                          + for long-form of the last 365 days and every podcast clip: the first 7 days,
                                          the retention curve (100 points) and what it says (kept at 30 s, at 25 / 50 /
                                          75 %, the steepest drop), traffic sources, subscribed vs not
                                          + ctr / impressions per video when the Monday Studio scrape carries them
                                          (the API has NO supported query for impressions or CTR - tested 2026-10-01)
         data/channels/<ch>/channel.json  28-day totals, traffic sources, the search terms that found the channel (90 d)
summary  data/channel_summary.md          the tables Claude reads before scoring a theme
fresh    exit 0 when both pulls are younger than 36 h and the Monday scrape's last GOOD run is 8 days old or less;
         exit 1 = pull again; exit 2 = the scrape is stale (ask Colden, or check.py --waive scrape_stale "<his words>")
GATE: a pull that fails writes nothing (the old file keeps its old date, so `fresh` fails)."""
import os, re, sys, json, datetime
import common as C
SCOPES = ['https://www.googleapis.com/auth/youtube', 'https://www.googleapis.com/auth/youtube.upload', 'https://www.googleapis.com/auth/youtube.force-ssl', 'https://www.googleapis.com/auth/yt-analytics.readonly']
CHANNELS = {'cwc': 'Create with Colden (@ColdenRaisher)', 'tcl': 'The Creative Lens'}
M_LIFE = 'views,engagedViews,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,subscribersGained,likes,comments,shares'
FRESH_H = 36; SCRAPE_DAYS = 8

def creds(ch):
    import warnings; warnings.simplefilter('ignore')
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    tok = f'{C.YT_CFG}/{ch}.json'
    if not os.path.exists(tok): C.ask(f'no YouTube token for "{ch}" ({tok}). Colden signs in once: python3 ~/.claude/skills/edit-clips/scripts/yt_upload.py auth {ch}')
    c = Credentials.from_authorized_user_file(tok, SCOPES)
    if not c.valid:
        if c.expired and c.refresh_token:
            c.refresh(Request()); open(tok, 'w').write(c.to_json())
        else: C.ask(f'the YouTube token for "{ch}" cannot be refreshed. Colden signs in again: python3 ~/.claude/skills/edit-clips/scripts/yt_upload.py auth {ch}')
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
    """curve = [[ratio, audienceWatchRatio], ...]: what share is still watching at 30 s / 25 / 50 / 75 %, and the
    steepest 5-point drop after the first 10 % (where a clip loses people once it has them)"""
    if not curve or not dur: return {}
    def at(r):
        r = min(max(r, curve[0][0]), curve[-1][0])
        for (a, va), (b, vb) in zip(curve, curve[1:]):
            if a <= r <= b: return va + (vb - va) * (r - a) / (b - a) if b > a else va
        return curve[-1][1]
    out = {'kept_30s': round(at(30.0 / dur), 3), 'kept_25': round(at(.25), 3), 'kept_50': round(at(.5), 3), 'kept_75': round(at(.75), 3), 'kept_end': round(curve[-1][1], 3)}
    best = None
    for i in range(len(curve) - 5):
        if curve[i][0] < 0.10 or curve[i + 5][0] > 0.92: continue             # not the hook, not the end screen
        d = curve[i][1] - curve[i + 5][1]
        if best is None or d > best[0]: best = (d, curve[i][0])
    if best: out['steepest_drop'] = {'at_sec': round(best[1] * dur), 'lost': round(best[0], 3)}
    return out

def scrape():
    """the weekly Studio scrape (channel_metrics.json): the newest copy that exists"""
    best = None
    for p in C.SCRAPE:
        d = C.load(p)
        if d and (best is None or str(d.get('updated', '')) > str(best[1].get('updated', ''))): best = (p, d)
    return best or (None, None)

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
            vids[v['id']] = {'id': v['id'], 'title': v['snippet']['title'], 'published': v['snippet']['publishedAt'], 'duration': dur,
                             'privacy': v['status'].get('privacyStatus'), 'tags': v['snippet'].get('tags', [])[:30],
                             'kind': 'live' if v.get('liveStreamingDetails') else ('short' if dur <= 180 else 'long'),
                             'public_views': int(v['statistics'].get('viewCount', 0))}
    S = C.load(f'{C.SK}/shows/creative-lens.json'); clip_ids = set()
    for sf in sorted(os.listdir(f'{C.SK}/shows')):
        for pl in (C.load(f'{C.SK}/shows/{sf}') or {}).get('clip_playlists', {}).get(ch, []):
            tok = None
            while True:
                try: r = yt.playlistItems().list(part='contentDetails', playlistId=pl, maxResults=50, pageToken=tok).execute()
                except Exception as e: print(f'  playlist {pl}: {str(e)[:120]}'); break
                clip_ids |= {i['contentDetails']['videoId'] for i in r['items']}; tok = r.get('nextPageToken')
                if not tok: break
    start0 = me['snippet']['publishedAt'][:10]; end = today.isoformat(); allids = list(vids)
    for i in range(0, len(allids), 200):                                     # lifetime numbers, 200 ids a query
        for row in rows(ya, start0, end, metrics=M_LIFE, dimensions='video', filters='video==' + ','.join(allids[i:i + 200]), maxResults=200):
            v = vids.get(row.pop('video'))
            if v: v['life'] = row
    try:                                                                     # YouTube's own long / short / live label
        for i in range(0, len(allids), 200):
            for row in rows(ya, start0, end, metrics='views', dimensions='video,creatorContentType', filters='video==' + ','.join(allids[i:i + 200]), maxResults=200):
                v = vids.get(row['video']); k = {'shorts': 'short', 'videoOnDemand': 'long', 'liveStream': 'live'}.get(row['creatorContentType'])
                if v and k and row['views'] >= 0.5 * (v.get('life') or {}).get('views', 0): v['kind'] = k
    except Exception as e: print(f'  creatorContentType per video not available ({str(e)[:80]}) - kind stays duration-based')
    cutoff = (today - datetime.timedelta(days=365)).isoformat()
    deep = [v for v in vids.values() if v['privacy'] == 'public' and (v['id'] in clip_ids or (v['kind'] == 'long' and v['published'][:10] >= cutoff))]
    for v in deep:
        v['podcast_clip'] = v['id'] in clip_ids; p0 = v['published'][:10]; f = f'video=={v["id"]}'
        d7 = min(today, datetime.date.fromisoformat(p0) + datetime.timedelta(days=7)).isoformat()
        try:
            r7 = rows(ya, p0, d7, metrics=M_LIFE, filters=f); v['first7'] = r7[0] if r7 else {}
            cv = rows(ya, p0, end, metrics='audienceWatchRatio,relativeRetentionPerformance', dimensions='elapsedVideoTimeRatio', filters=f)
            v['curve'] = [[c['elapsedVideoTimeRatio'], round(c['audienceWatchRatio'], 4)] for c in cv]
            v['vs_similar'] = round(sum(c['relativeRetentionPerformance'] for c in cv) / len(cv), 3) if cv else None
            v['retention'] = curve_facts(v['curve'], v['duration'])
            v['traffic'] = {t['insightTrafficSourceType']: t['views'] for t in rows(ya, p0, end, metrics='views', dimensions='insightTrafficSourceType', filters=f, sort='-views')}
            v['by_sub'] = {t['subscribedStatus']: {'views': t['views'], 'pct_viewed': round(t['averageViewPercentage'], 1)} for t in rows(ya, p0, end, metrics='views,averageViewPercentage', dimensions='subscribedStatus', filters=f)}
        except Exception as e: v['deep_error'] = str(e)[:160]
    sp, sd = scrape(); n_ctr = 0
    for row in ((sd or {}).get('per_video', []) if ch == 'cwc' else ((sd or {}).get('tcl') or {}).get('per_video', [])):       # schema: references/weekly_scrape.md (TCL rows under "tcl")
        v = vids.get(row.get('video_id'))
        if v and row.get('ctr_pct') is not None:
            v['ctr'] = {'pct': row['ctr_pct'], 'impressions': row.get('impressions'), 'as_of': row.get('as_of') or sd.get('updated'), 'source': 'weekly Studio scrape'}; n_ctr += 1
    s28 = (today - datetime.timedelta(days=28)).isoformat(); s90 = (today - datetime.timedelta(days=90)).isoformat()
    chan = {'channel': ch, 'name': me['snippet']['title'], 'id': me['id'], 'subs': int(me['statistics'].get('subscriberCount', 0)), 'pulled_at': C.now(),
            'totals_28d': (rows(ya, s28, end, metrics='views,estimatedMinutesWatched,averageViewDuration,subscribersGained') or [{}])[0],
            'traffic_28d': {t['insightTrafficSourceType']: t['views'] for t in rows(ya, s28, end, metrics='views', dimensions='insightTrafficSourceType', sort='-views')},
            'search_terms_90d': [[t['insightTrafficSourceDetail'], t['views']] for t in rows(ya, s90, end, metrics='views', dimensions='insightTrafficSourceDetail', filters='insightTrafficSourceType==YT_SEARCH', sort='-views', maxResults=25)]}
    out = f'{C.DATA}/channels/{ch}'
    C.save(f'{out}/videos.json', {'channel': ch, 'pulled_at': chan['pulled_at'], 'n': len(vids), 'ctr_rows_from_scrape': n_ctr, 'videos': sorted(vids.values(), key=lambda v: v['published'], reverse=True)})
    C.save(f'{out}/channel.json', chan)
    print(f'{ch}: {len(vids)} uploads ({sum(v["kind"] == "long" for v in vids.values())} long, {sum(v["kind"] == "short" for v in vids.values())} short, {sum(v["kind"] == "live" for v in vids.values())} live); '
          f'deep stats on {len(deep)} ({sum(1 for v in deep if v.get("deep_error"))} errors); podcast clips {len(clip_ids & set(vids))}; CTR rows from the scrape: {n_ctr}')

def fresh(quiet=False):
    """-> (ok, problems, scrape_stale)"""
    probs = []
    for ch in CHANNELS:
        d = C.load(f'{C.DATA}/channels/{ch}/videos.json')
        if not d: probs.append(f'{ch}: never pulled')
        elif C.age_hours(d['pulled_at']) > FRESH_H: probs.append(f'{ch}: pulled {C.age_hours(d["pulled_at"]):.0f} h ago (limit {FRESH_H} h)')
    sp, sd = scrape(); stale = None
    if not sd: stale = 'no channel_metrics.json found'
    else:
        age = (datetime.date.today() - datetime.date.fromisoformat(str(sd['updated'])[:10])).days
        if age > SCRAPE_DAYS: stale = f'last GOOD run {sd["updated"]} ({age} days ago, limit {SCRAPE_DAYS}); last attempt {sd.get("last_attempt")}: {(sd.get("last_run_status") or {}).get("status")}'
    return (not probs), probs, stale

def summary():
    L = ['# Channel data - what has worked (read this before scoring channel_fit; cite video ids as evidence)', '']
    for ch, label in CHANNELS.items():
        d = C.load(f'{C.DATA}/channels/{ch}/videos.json'); c = C.load(f'{C.DATA}/channels/{ch}/channel.json')
        if not d: L.append(f'## {label}: NOT PULLED'); continue
        L += [f'## {label} - {c["subs"]} subs - pulled {d["pulled_at"]}', f'28 days: {c["totals_28d"]}', f'traffic 28 d: {c["traffic_28d"]}',
              'search terms that found the channel (90 d): ' + ', '.join(f'{t} ({n})' for t, n in c['search_terms_90d']), '']
        longs = [v for v in d['videos'] if v.get('curve') is not None or v.get('podcast_clip')]
        L += ['| id | published | len | title | clip | views | 7d views | avg % viewed | kept 30 s | kept 50 % | steepest drop | subs | top source | CTR |', '|---|---|---|---|---|---|---|---|---|---|---|---|---|---|']
        for v in longs[:70]:
            lf = v.get('life', {}); r = v.get('retention', {}); tr = v.get('traffic', {}); top = max(tr, key=tr.get) if tr else ''
            sd = r.get('steepest_drop'); ctr = v.get('ctr')
            L.append(f'| {v["id"]} | {v["published"][:10]} | {C.mmss(v["duration"])} | {v["title"][:70]} | {"clip" if v.get("podcast_clip") else ""} | {lf.get("views", "")} | {v.get("first7", {}).get("views", "")} | '
                     f'{round(lf["averageViewPercentage"], 1) if "averageViewPercentage" in lf else ""} | {r.get("kept_30s", "")} | {r.get("kept_50", "")} | {(str(sd["lost"]) + " @ " + C.mmss(sd["at_sec"])) if sd else ""} | {lf.get("subscribersGained", "")} | {top} | {(str(ctr["pct"]) + "%") if ctr else "n/a"} |')
        L.append('')
    sp, sd = scrape()
    if sd:
        L += [f'## Weekly Studio scrape ({sp}) - last good run {sd.get("updated")}, last attempt {sd.get("last_attempt")}: {(sd.get("last_run_status") or {}).get("status")}', '',
              'working now:'] + [f'- {x}' for x in sd.get('working_now', [])] + ['', 'avoid:'] + [f'- {x}' for x in sd.get('avoid', [])] + ['', f'targets: {json.dumps(sd.get("targets_status", {}))[:1500]}', '']
    lp = f'{C.DATA}/learnings.md'
    if os.path.exists(lp): L += ['## Learnings from past theme decisions and published clips (learn.py report)', '', open(lp).read()]
    open(f'{C.DATA}/channel_summary.md', 'w').write('\n'.join(L) + '\n'); print(f'{C.DATA}/channel_summary.md')

if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    if cmd == 'pull':
        for ch in (CHANNELS if (len(sys.argv) < 3 or sys.argv[2] == 'all') else [sys.argv[2]]): pull(ch)
        summary()
    elif cmd == 'summary': summary()
    elif cmd == 'fresh':
        ok, probs, stale = fresh()
        for p in probs: print('STALE', p)
        if stale: print('SCRAPE STALE', stale)
        sys.exit(1 if not ok else (2 if stale else 0))
    else: C.fail(__doc__)
