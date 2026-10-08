"""YouTube Data API helpers for CWC_PodRun (library; youtube.py and cal.py are the commands).
Tokens: ~/.config/edit-clips/youtube/<cwc|tcl>.json (made by edit-clips; scopes youtube, youtube.upload, youtube.force-ssl,
yt-analytics.readonly). A dead token is exit 2 - never an interactive sign-in from here.
Every client is checked against the brand's channel id first: the Google login defaults to an old gymnastics channel
(UCQtVffA1H-pHwi8boVru6kA) - a call on the wrong channel is a gate failure, not a warning.
Quota: one project-wide pool, shared with CWC_PodClips through data/quota.json ({"<Pacific day>": units}); every call
here spends from it first and stops (exit 2) before passing rules.json quota_daily_limit."""
import os, re, datetime as dt
import common as C

CATEGORY = {'film & animation': '1', 'autos & vehicles': '2', 'music': '10', 'pets & animals': '15', 'sports': '17',
            'travel & events': '19', 'gaming': '20', 'people & blogs': '22', 'comedy': '23', 'entertainment': '24',
            'news & politics': '25', 'howto & style': '26', 'education': '27', 'science & technology': '28',
            'nonprofits & activism': '29'}

def category_id(v):
    """'1', 'Film & Animation', Metricool's 'FILM_ANIMATION' or CWC_PodClips' {"id": "1", "name": ..} -> '1'.
    Never a default: the category is one per channel (Colden 2026-09-15 "Keep film"), references/brands.json"""
    if isinstance(v, dict): v = v.get('id') or v.get('name')
    if v is None: C.fail('no YouTube category on this item - one per channel, references/brands.json youtube.category_id')
    s = str(v).strip()
    if s.isdigit(): return s
    flat = lambda x: re.sub(r'[^a-z]', '', x.lower().replace(' and ', ''))
    hit = next((cid for name, cid in CATEGORY.items() if flat(name) == flat(s)), None)
    return hit or C.fail(f'unknown YouTube category {v!r}')

def iso_seconds(d):
    m = re.fullmatch(r'P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', d or '')
    if not m: return 0
    dd, h, mi, s = (int(x or 0) for x in m.groups()); return dd * 86400 + h * 3600 + mi * 60 + s

def utc_z(iso_et):
    return C.et(iso_et).astimezone(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z')

def norm_title(t):
    """compare a planned title with a Studio upload: case, punctuation, the file extension and a leading 'NN ' ignored"""
    t = re.sub(r'\.(mp4|mov)$', '', (t or '').strip(), flags=re.I)
    return re.sub(r'[^a-z0-9]+', ' ', t.lower()).strip()

# ------------------------------------------------------------------ quota (shared ledger with CWC_PodClips)
def pacific_day(): return (dt.datetime.utcnow() - dt.timedelta(hours=7)).date().isoformat()
COMMENT_LIMIT = 10000          # Google's own daily cap: the uploads plan to quota_daily_limit (9,500), pinned comments may use the rest

def spend(units, what, limit=None):
    p = f'{C.DATA}/quota.json'; day = pacific_day(); q = C.load(p, {}) or {}; used = q.get(day, 0)
    limit = limit or (COMMENT_LIMIT if units <= 50 else C.rules()['quota_daily_limit'])   # uploads + captions plan to 9,500; reads, comments, playlist adds may use Google's full 10,000
    if used + units > limit: C.ask(f'YouTube API quota: {used} units used today (Pacific), {what} needs {units} more, limit {limit}. Wait for midnight Pacific or ask Colden to raise it.')
    C.save(p, {day: used + units})
def cost(op): return C.rules()['quota_cost'][op]

# ------------------------------------------------------------------ client
_clients = {}
def service(brand):
    if brand in _clients: return _clients[brand]
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
    except ImportError: C.ask('google-api-python-client / google-auth are not installed (pip install google-api-python-client google-auth)')
    b = C.brands()[brand]['youtube']; tok = f'{C.YT_CFG}/{b["token"]}'
    if not os.path.exists(tok): C.ask(f'no YouTube token for {brand} at {tok} (edit-clips makes it)')
    cr = Credentials.from_authorized_user_file(tok)
    if not cr.valid:
        try: cr.refresh(Request())
        except Exception as x: C.ask(f'the {brand} YouTube token is dead ({type(x).__name__}) - Colden signs in again with edit-clips')
    yt = build('youtube', 'v3', credentials=cr, cache_discovery=False)
    spend(cost('videos.list'), 'channel check')
    me = yt.channels().list(part='id', mine=True).execute().get('items', [])
    got = me[0]['id'] if me else None
    if got != b['channel_id']: C.fail(f'the {brand} token is signed in to channel {got}, not {b["channel_id"]} ({C.brands()[brand]["label"]}) - stop, nothing was changed')
    _clients[brand] = yt; return yt

def uploads(brand, days_back=21):
    """recent + scheduled uploads of the brand's channel: [{id, title, privacy, publish_at, published_at, seconds, live, kind}]"""
    yt = service(brand); pl = 'UU' + C.brands()[brand]['youtube']['channel_id'][2:]
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days_back); ids, token = [], None
    while True:
        spend(cost('playlistItems.list'), 'uploads list')
        res = yt.playlistItems().list(part='contentDetails', playlistId=pl, maxResults=50, pageToken=token).execute()
        old = 0
        for it in res.get('items', []):
            ids.append(it['contentDetails']['videoId']); pub = it['contentDetails'].get('videoPublishedAt')
            if pub and dt.datetime.fromisoformat(pub.replace('Z', '+00:00')) < cutoff: old += 1
        token = res.get('nextPageToken')
        if not token or old == len(res.get('items', [])): break
    out = []
    for i in range(0, len(ids), 50):
        spend(cost('videos.list'), 'video details')
        for v in yt.videos().list(part='snippet,status,contentDetails,liveStreamingDetails', id=','.join(ids[i:i + 50])).execute().get('items', []):
            st, sn = v.get('status', {}), v.get('snippet', {}); secs = iso_seconds(v.get('contentDetails', {}).get('duration'))
            live = 'liveStreamingDetails' in v; lsd = v.get('liveStreamingDetails') or {}
            when = st.get('publishAt') or sn.get('publishedAt')
            if when and dt.datetime.fromisoformat(when.replace('Z', '+00:00')) < cutoff and not st.get('publishAt'): continue
            out.append({'id': v['id'], 'title': sn.get('title'), 'privacy': st.get('privacyStatus'), 'publish_at': st.get('publishAt'),
                        'published_at': sn.get('publishedAt'), 'start_at': lsd.get('scheduledStartTime') or lsd.get('actualStartTime'), 'seconds': secs, 'live': live,
                        'kind': 'live' if live else ('short' if 0 < secs <= 180 else 'long')})
    return out

def full_episode_url(brand, ep_no, videos=None):
    """the PUBLIC 'Ep. NN' upload WITHOUT the phone emoji (CWC_PodClips ruling 38: the emoji one is the vertical stream)"""
    vids = videos if videos is not None else uploads(brand, days_back=60)
    pat = re.compile(rf'\bEp\.?\s*{int(ep_no)}\b', re.I)
    hits = [v for v in vids if pat.search(v['title'] or '') and '\U0001F4F1' not in (v['title'] or '') and v['privacy'] == 'public' and v['kind'] != 'short']
    if len(hits) != 1: return None, f'{len(hits)} public "Ep. {ep_no}" uploads without the phone emoji on {brand}'
    return f'https://www.youtube.com/watch?v={hits[0]["id"]}', None

# ------------------------------------------------------------------ writes
def snippet(item):
    sn = {'title': item['title'][:100], 'description': item.get('description') or '', 'tags': item.get('tags') or [],
          'categoryId': category_id(item.get('category')), 'defaultLanguage': 'en', 'defaultAudioLanguage': 'en-US'}
    if len(sn['title']) < len(item['title']): C.fail(f'{item["id"]}: title over 100 characters')
    return sn

def media(path, mimetype=None, chunk=64 * 1024 * 1024):
    from googleapiclient.http import MediaFileUpload
    if not os.path.exists(path): C.ask(f'file missing (NAS mounted?): {path}')
    return MediaFileUpload(path, mimetype=mimetype, chunksize=chunk, resumable=True)

def remaining():
    day = pacific_day(); return C.rules()['quota_daily_limit'] - (C.load(f'{C.DATA}/quota.json', {}) or {}).get(day, 0)

def insert(brand, item, schedule, notify=True):
    """upload with the snippet + flags. schedule 'publishAt': private + publishAt = the approved slot (YouTube publishes
    it by itself); 'flip': private, no publishAt - Colden flips it to Scheduled at the dashboard's time.
    notify=False only for test cards: subscribers are not told when it goes public."""
    yt = service(brand); spend(cost('videos.insert'), f'upload {item["id"]}')
    st = {'privacyStatus': 'private', 'selfDeclaredMadeForKids': False, 'containsSyntheticMedia': False, 'embeddable': True}
    if schedule == 'publishAt': st['publishAt'] = utc_z(item['publish_at'])
    body = {'snippet': snippet(item), 'status': st}
    req = yt.videos().insert(part='snippet,status', body=body, notifySubscribers=notify, media_body=media(item['files']['video'], 'video/*'))
    res = None
    while res is None: _, res = req.next_chunk()
    return res['id']

def update_snippet(brand, video_id, item):
    yt = service(brand); spend(cost('videos.update'), f'metadata {item["id"]}')
    yt.videos().update(part='snippet', body={'id': video_id, 'snippet': snippet(item)}).execute()

def schedule(brand, video_id, publish_at_iso):
    """a video Colden uploaded himself: private + publishAt = the approved slot, made for kids No, synthetic No"""
    yt = service(brand); spend(cost('videos.update'), f'schedule {video_id}')
    st = {'privacyStatus': 'private', 'publishAt': utc_z(publish_at_iso), 'selfDeclaredMadeForKids': False, 'containsSyntheticMedia': False, 'embeddable': True}
    yt.videos().update(part='status', body={'id': video_id, 'status': st}).execute()

def update_flags(brand, video_id):
    """made for kids No, altered / synthetic content No - keeps the privacy + publishAt Colden set in Studio"""
    yt = service(brand); spend(cost('videos.list') + cost('videos.update'), 'flags')
    st = yt.videos().list(part='status', id=video_id).execute()['items'][0]['status']
    keep = {k: st[k] for k in ('privacyStatus', 'publishAt', 'embeddable', 'license', 'publicStatsViewable') if k in st}
    yt.videos().update(part='status', body={'id': video_id, 'status': dict(keep, selfDeclaredMadeForKids=False, containsSyntheticMedia=False)}).execute()

def set_thumbnail(brand, video_id, path):
    yt = service(brand); spend(cost('thumbnails.set'), 'thumbnail')
    yt.thumbnails().set(videoId=video_id, media_body=media(path, chunk=-1)).execute()

def add_captions(brand, video_id, path):
    yt = service(brand); spend(cost('captions.insert'), 'captions')
    yt.captions().insert(part='snippet', body={'snippet': {'videoId': video_id, 'language': 'en', 'name': 'English', 'isDraft': False}},
                         media_body=media(path, 'application/octet-stream', chunk=-1)).execute()

def add_to_playlist(brand, video_id, playlist_id):
    yt = service(brand); spend(cost('playlistItems.insert'), 'playlist')
    yt.playlistItems().insert(part='snippet', body={'snippet': {'playlistId': playlist_id, 'resourceId': {'kind': 'youtube#video', 'videoId': video_id}}}).execute()

def video_status(brand, video_id):
    yt = service(brand); spend(cost('videos.list'), 'status read')
    items = yt.videos().list(part='status,snippet', id=video_id).execute().get('items', [])
    return items[0] if items else None

def add_comment(brand, video_id, text):
    """a top-level comment as the channel itself (commentThreads.insert works before the audit - edit-clips yt_daily.py).
    The Data API cannot PIN a comment: that is done in Studio (pin.py prints what to pin)."""
    yt = service(brand); spend(cost('commentThreads.insert'), f'comment on {video_id}', limit=COMMENT_LIMIT)
    r = yt.commentThreads().insert(part='snippet', body={'snippet': {'videoId': video_id, 'topLevelComment': {'snippet': {'textOriginal': text}}}}).execute()
    return r['id']
