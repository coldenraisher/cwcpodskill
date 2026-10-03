"""evidence.py search <WORK> <theme-slug> "<query>" ["<query 2>" ...] [--days 90]
           evidence.py trends <WORK>
"Proven on the platform as a whole" (Colden 2026-10-01: agreed) = recent videos on the SAME topic that beat their own
channel's normal. Evidence, never a feeling: every platform score in themes.json must cite video ids this script found.

search   YouTube Data API search (videos published in the last --days, by view count and by relevance), then per video:
         views, age, views a day, the channel's subscribers and - for the 10 biggest - the channel's median views over
         its last 15 uploads -> outlier = views / that median (>= 2 is a real over-performer; under 1 is not evidence).
         Colden's own channels are left out. Saves <WORK>/platform/<slug>.json and prints the table.
         Cost: 100 quota units a query (+ ~25); the day's use is kept in data/quota.json and the run refuses past 6,000
         of the 10,000 daily default (uploads need the rest).
trends   <WORK>/trends.md: today's packages from the daily trend scanner (CreateWithColden/trend_research, read-only),
         with their dates - what is NEWS right now. A scan older than 3 days is marked STALE in the file.
vidIQ: Colden has the free tier, which has no API - it is not read here. If he sends a vidIQ screenshot it is his evidence."""
import os, sys, json, datetime, statistics
import common as C, channel_data as CD
LIMIT = 6000

def spend(n):
    day = (datetime.datetime.utcnow() - datetime.timedelta(hours=7)).date().isoformat()      # quota resets at midnight Pacific
    q = C.load(f'{C.DATA}/quota.json', {}); used = q.get(day, 0)
    if used + n > LIMIT: C.ask(f'YouTube API quota: {used} units used today by this skill, {n} more would pass the {LIMIT} limit. Wait for the reset (midnight Pacific) or have Colden raise the limit.')
    q = {day: used + n}; C.save(f'{C.DATA}/quota.json', q)

def search(work, slug, queries, days):
    yt, _ = CD.services('cwc'); own = {(C.load(f'{C.DATA}/channels/{c}/channel.json') or {}).get('id') for c in CD.CHANNELS}
    after = (datetime.datetime.utcnow() - datetime.timedelta(days=days)).strftime('%Y-%m-%dT00:00:00Z'); found = {}
    for q in queries:
        for order in ('viewCount', 'relevance'):
            spend(100)
            r = yt.search().list(part='snippet', q=q, type='video', order=order, publishedAfter=after, maxResults=25, relevanceLanguage='en').execute()
            for it in r.get('items', []):
                found.setdefault(it['id']['videoId'], {'queries': set()})['queries'].add(q)
    ids = list(found); vids = []
    for i in range(0, len(ids), 50):
        spend(1)
        for v in yt.videos().list(part='snippet,statistics,contentDetails', id=','.join(ids[i:i + 50])).execute()['items']:
            if v['snippet']['channelId'] in own: continue
            dur = CD.iso_dur(v['contentDetails'].get('duration'))
            if dur <= 180: continue                                              # long-form evidence only
            age = max(1.0, (datetime.datetime.now(datetime.timezone.utc) - datetime.datetime.fromisoformat(v['snippet']['publishedAt'].replace('Z', '+00:00'))).total_seconds() / 86400)
            views = int(v['statistics'].get('viewCount', 0))
            vids.append({'id': v['id'], 'url': f'https://youtu.be/{v["id"]}', 'title': v['snippet']['title'], 'channel': v['snippet']['channelTitle'], 'channel_id': v['snippet']['channelId'],
                         'published': v['snippet']['publishedAt'][:10], 'age_days': round(age, 1), 'duration': dur, 'views': views, 'views_per_day': round(views / age),
                         'queries': sorted(found[v['id']]['queries'])})
    chans = list({v['channel_id'] for v in vids}); subs = {}; uploads = {}
    for i in range(0, len(chans), 50):
        spend(1)
        for c in yt.channels().list(part='statistics,contentDetails', id=','.join(chans[i:i + 50])).execute()['items']:
            subs[c['id']] = int(c['statistics'].get('subscriberCount', 0)); uploads[c['id']] = c['contentDetails']['relatedPlaylists']['uploads']
    for v in vids: v['subs'] = subs.get(v['channel_id']); v['views_per_sub'] = round(v['views'] / v['subs'], 2) if v.get('subs') else None
    vids.sort(key=lambda v: -v['views']); med = {}
    for v in vids[:10]:
        cid = v['channel_id']
        if cid not in med and cid in uploads:
            try:
                spend(2)
                pl = yt.playlistItems().list(part='contentDetails', playlistId=uploads[cid], maxResults=16).execute()['items']
                st = yt.videos().list(part='statistics,contentDetails', id=','.join(p['contentDetails']['videoId'] for p in pl)).execute()['items']
                vv = [int(s['statistics'].get('viewCount', 0)) for s in st if s['id'] != v['id'] and CD.iso_dur(s['contentDetails'].get('duration')) > 180]
                med[cid] = statistics.median(vv) if len(vv) >= 4 else None
            except Exception: med[cid] = None
        m = med.get(cid); v['channel_median'] = m; v['outlier'] = round(v['views'] / m, 1) if m else None
    out = {'slug': slug, 'queries': queries, 'days': days, 'pulled_at': C.now(), 'n': len(vids),
           'outliers_2x': sum(1 for v in vids if (v.get('outlier') or 0) >= 2), 'best_outlier': max([v.get('outlier') or 0 for v in vids] or [0]),
           'views_top10': sum(v['views'] for v in vids[:10]), 'results': vids}
    C.save(f'{work}/platform/{slug}.json', out)
    print(f'{slug}: {len(vids)} long-form videos in {days} days for {queries}; >= 2x their channel: {out["outliers_2x"]}; best outlier {out["best_outlier"]}x')
    for v in vids[:12]: print(f'  {v["id"]} {v["views"]:>9,} views {v["age_days"]:>5.0f} d  {str(v.get("outlier") or "-"):>5}x  {(v.get("subs") or 0):>9,} subs  {v["channel"][:24]:24} {v["title"][:70]}')

def trends(work):
    L = ['# Trend scan (daily scanner, read-only) - what is news right now', '']; f = C.load(f'{C.TREND}/final.json'); c = C.load(f'{C.TREND}/candidates.json')
    if not f: L.append('NO final.json - the daily scanner has not run')
    else:
        scanned = (c or {}).get('scanned_at', ''); age = C.age_hours(scanned) / 24 if scanned else None
        L += [f'scan of {scanned[:16]}' + (f' - STALE ({age:.0f} days old)' if age and age > 3 else ''), '', '## News packages']
        for n in f.get('news_packages', []): L += [f'- **{n.get("headline")}** - {n.get("summary", "")} | why: {n.get("why_it_matters", "")} | sources: {json.dumps(n.get("sources") or n.get("urls") or n.get("url") or "")[:300]}']
        L += ['', '## Social / video outliers']
        for s in f.get('social_items', []): L += [f'- {s.get("title")} ({s.get("platform")}, {s.get("creator")}, {s.get("posted_at")}, {s.get("views")} views, {s.get("multiplier")}x) {s.get("url")} - {s.get("why_viral", "")[:300]}']
        L += ['', '## Headlines in the pool (title - source - published)']
        for n in (c or {}).get('news_candidates', []): L.append(f'- {n.get("title")} - {n.get("source")} - {str(n.get("published_at_iso"))[:10]} - {n.get("url")}')
    os.makedirs(work, exist_ok=True); open(f'{work}/trends.md', 'w').write('\n'.join(L) + '\n'); print(f'{work}/trends.md ({len(L)} lines)')

if __name__ == '__main__':
    a = sys.argv[1:]; days = 90
    if '--days' in a: i = a.index('--days'); days = int(a[i + 1]); del a[i:i + 2]
    if len(a) >= 4 and a[0] == 'search': search(os.path.abspath(a[1]), a[2], a[3:], days)
    elif len(a) == 2 and a[0] == 'trends': trends(os.path.abspath(a[1]))
    else: C.fail(__doc__)
