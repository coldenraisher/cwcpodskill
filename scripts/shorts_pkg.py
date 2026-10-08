"""shorts_pkg.py build|apply|status <RUN> [--id ITEM]      the YouTube PACKAGE of every Short + paid promotion "No" on every upload
Colden 2026-10-03, on the first Short that went up: "you also forgot to click "no" on paid promotion" / "You left over 400
char tags open. This should be optimized for as close to 500 as possible." / "Usually we add the shorts to several fitting
playlists" / "the reels skill is supposed to read the captions and provide you a clean and correct subtitles track to help
with search and visibility ... Search and correct subtitles are critical."
CWC_PodReels hands over a caption, a first comment, a title and ONE playlist key per short - not a YouTube package. This
builds the rest, with CWC_PodClips' rules (its show file packaging block):
  tags       the short's topic tags (publish/shorts_topics.json, written per short: what a viewer would type) + the stock
             set, filled to 470-500 characters COUNTED AS YOUTUBE COUNTS (CWC_PodClips package.tag_len); gate: >= 470
  playlists  every playlist named for the short in shorts_topics.json + the brand's Shorts playlist; ids from the show files
  subtitles  an .srt from the captions CWC_PodReels BURNED INTO the approved version (its build plan: the show's spellings
             and caption merges already applied - "PANAVISION", "FX3"), sentence case restored from the short's own title,
             caption and the show glossary; never YouTube's auto-captions
  paid promotion "No" (paidProductPlacementDetails.hasPaidProductPlacement false) on EVERY YouTube upload, clips too
  build  -> publish/shorts_package.json + publish/srt/<item>.srt     apply -> the uploaded videos get what they lack
GATES: tags 470-500; every playlist name resolves to an id; an srt with every cue inside the short and no empty text;
each step recorded in publish_log.json before the next."""
import os, re, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

LIMIT = 9850                    # leaves Google's 10,000 room for the day's pinned comments (ytapi.COMMENT_LIMIT)

def tag_len(tags): return sum(len(t) for t in tags) + max(0, len(tags) - 1) + 2 * sum(1 for t in tags if ' ' in t)

SHOW = 'creative-lens'           # set from the run by build / apply / status (C&T 10-6: it read The Creative Lens for every show)
def show(name): return C.load(f'{C.SKILLS}/{name}/shows/{SHOW}.json') or {}
def for_run(R):
    global SHOW; SHOW = C.run(R).get('show') or 'creative-lens'

def playlist_ids(brand):
    out = {}
    for k, v in (((show('CWC_PodReels').get('publishing') or {}).get('metricool') or {}).get(brand, {}).get('playlists') or {}).items(): out[v['title']] = v['id']
    for n, i in ((show('CWC_PodClips').get('packaging') or {}).get('playlists', {}).get(brand, {}).get('ids') or {}).items(): out.setdefault(n, i)
    return out

ALWAYS = ['YouTube', 'AI', 'Hollywood', 'Instagram', 'TikTok', 'Facebook', 'Google', 'Netflix', 'Nvidia', 'Christopher', 'Nolan', 'Scorsese', 'Coppola', 'Godfather', 'Megalopolis', 'Odyssey', 'Rocky', 'Shining', 'Pulp', 'Fiction']   # names Whisper and the captions lower-case
STOP = set('film films movie movies a an and are as at be but by for from has have he her his i if in into is it its me my no not of on or our she so that the their them then there these they this to us was we were what when where which who will with you your'.split())

def casing(prose, names):
    """proper nouns only: words capitalised INSIDE a sentence of the short's own caption (never at its start - a title or a
    sentence start is no evidence), letter+digit models (FX3), and the show's glossary / spellings / host names"""
    m = {}
    for sent in re.split(r'(?<=[.!?])\s+', prose):
        ws = re.findall(r"[A-Za-z0-9][A-Za-z0-9'$\-]*", sent)
        for n, w in enumerate(ws):
            w = w.strip("-'")
            if not w or w.lower() in STOP: continue
            if (n > 0 and w[0].isupper()) or (any(c.isdigit() for c in w) and any(c.isalpha() for c in w)): m.setdefault(w.lower(), w)
    for w in re.findall(r"[A-Za-z0-9][A-Za-z0-9'$\-]*", names):
        if w.lower() not in STOP and w != w.lower(): m.setdefault(w.lower(), w)
    return m

def sentence_case(text, cmap, start):
    out, cap = [], start
    for tok in text.split():
        core = re.sub(r"^[^A-Za-z0-9$]+|[^A-Za-z0-9']+$", '', tok); low = tok.lower()
        if core and core.lower() in cmap: low = low.replace(core.lower(), cmap[core.lower()], 1)
        elif core.lower() == 'i' or core.lower().startswith("i'"): low = low.replace(core.lower(), 'I' + core.lower()[1:], 1)
        if cap: low = re.sub(r'[A-Za-z]', lambda x: x.group(0).upper(), low, count=1)
        out.append(low); cap = bool(re.search(r'[.!?]["\']?$', tok))
    return ' '.join(out), cap

def srt_for(r, sid, copy, title):
    W = r['reels_work']; vs = C.load(f'{W}/edit/{sid}/versions.json', []) or []
    v = next((x for x in reversed(vs) if x.get('status') in ('approved', 'locked')), None) or C.fail(f'{sid}: no approved version in CWC_PodReels')
    p = C.load(f'{W}/edit/{sid}/build.v{v["v"]}.json') or C.fail(f'{sid}: build.v{v["v"]}.json missing')
    fps = float(p.get('fps') or 30); end_all = int(p.get('frames') or 0)
    sh = show('CWC_PodReels')
    names = ' '.join([' '.join(sh.get('glossary') or []), ' '.join(str(x) for x in (sh.get('spellings') or {}).values()),
                      ' '.join(h.get('name', '') if isinstance(h, dict) else str(h) for h in sh.get('hosts') or [])])
    th = next((t for t in (C.load(f'{W}/themes.json') or {}).get('themes', []) if t.get('id') == sid), {}) or {}
    prose = ' '.join([copy.get('caption') or '', th.get('summary') or '', ' '.join(c.get('claim', '') for c in th.get('claims') or [])])
    names += ' ' + ' '.join((C.load(f'{C.SKILLS}/CWC_PodCut/shows/{r["show"]}.json') or {}).get('glossary') or []) + ' ' + ' '.join(ALWAYS)
    cmap = casing(re.sub(r'#\w+', ' ', prose), names)
    keys = []
    for run in p.get('captions') or []:
        for off, text in run['keys']: keys.append((run['rec'] + off, text.strip()))
        keys.append((run['rec'] + run['frames'], None))
    cues, cur = [], None
    for f, text in sorted(keys, key=lambda k: k[0]):
        if cur and (text is None or text != cur[1]): cur[2] = f; cues.append(cur); cur = None
        if text and (not cues or cues[-1][1] != text or cues[-1][2] < f): cur = [f, text, None] if not cur else cur
    if cur: cur[2] = end_all or cur[0] + int(fps); cues.append(cur)
    merged = []
    for a, t, b in cues:
        if merged and merged[-1][1] == t and merged[-1][2] >= a - 1: merged[-1][2] = b
        elif b > a: merged.append([a, t, b])
    if not merged: C.fail(f'{sid}: no caption cues in the approved build plan')
    ts = lambda f: f'{int(f / fps // 3600):02d}:{int(f / fps % 3600 // 60):02d}:{int(f / fps % 60):02d},{int(round(f / fps % 1 * 1000)) % 1000:03d}'
    L, cap = [], True
    for n, (a, t, b) in enumerate(merged, 1):
        if end_all and b > end_all: C.fail(f'{sid}: a cue runs past the end of the short')
        text, cap = sentence_case(t, cmap, cap)
        L += [str(n), f'{ts(a)} --> {ts(b)}', text, '']
    os.makedirs(f'{C.RUNS}/{r["show"]}/{r["ep_key"]}/publish/srt', exist_ok=True)
    out = f'{C.RUNS}/{r["show"]}/{r["ep_key"]}/publish/srt/{sid}.srt'; open(out, 'w', encoding='utf-8').write('\n'.join(L)); return out, len(merged)

def build(R):
    for_run(R)
    r = C.run(R); P = C.load(f'{R}/plan.json'); topics = C.load(f'{R}/publish/shorts_topics.json') or C.fail('publish/shorts_topics.json missing: per short {"tags": [what a viewer types], "playlists": {"cwc": [names], "tcl": [names]}}')
    stock = ((show('CWC_PodClips').get('packaging') or {}).get('tags') or {}).get('stock') or []
    d = C.reels_delivery(r) or C.fail('CWC_PodReels has not delivered'); by = {s['id']: s for s in d['shorts']}
    pkg = {}; bad = []
    for it in [i for i in P['items'] if i['kind'] == 'yt_short']:
        t = topics.get(it['ref']) or C.fail(f'{it["ref"]}: no topic tags in shorts_topics.json')
        tags, seen = [], set()
        for x in list(t['tags']) + stock:
            x = x.strip()
            if x and x.lower() not in seen and len(x) <= 30 and tag_len(tags + [x]) <= 500: tags.append(x); seen.add(x.lower())
        n = tag_len(tags)
        if n < 470: bad.append(f'{it["id"]}: tags only {n}/500 - add topic tags')
        ids = playlist_ids(it['brand']); names = list(dict.fromkeys((t.get('playlists') or {}).get(it['brand'], [])))
        miss = [x for x in names if x not in ids]
        if miss: bad.append(f'{it["id"]}: playlist(s) {miss} not on file for {it["brand"]}')
        pl = list(dict.fromkeys(list(it.get('playlists') or []) + [ids[x] for x in names if x in ids]))
        srt, ncue = srt_for(r, it['ref'], by[it['ref']].get('copy') or {}, by[it['ref']].get('yt_title') or it['title'])
        pkg[it['id']] = {'tags': tags, 'tags_youtube_count': n, 'playlists': pl, 'playlist_names': names, 'captions': srt, 'cues': ncue}
    if bad: C.fail('shorts package:\n  ' + '\n  '.join(bad))
    C.save(f'{R}/publish/shorts_package.json', pkg); return pkg

def apply(R, only=None):
    for_run(R)
    import ytapi as Y
    r = C.run(R); P = C.load(f'{R}/plan.json'); pkg = C.load(f'{R}/publish/shorts_package.json') or build(R); log = C.load(f'{R}/publish_log.json', {}) or {}
    for it in [i for i in P['items'] if i['kind'] in ('yt_clip', 'yt_short') and (not only or i['id'] == only)]:
        e = log.get(it['id']) or {}
        if not e.get('video_id'): continue
        vid, b, done = e['video_id'], it['brand'], e.setdefault('repack', [])
        yt = Y.service(b); k = pkg.get(it['id'])
        if 'paid_promotion_no' not in done or (k and 'tags' not in done):
            Y.spend(Y.cost('videos.list'), 'read before update', limit=LIMIT)
            cur = yt.videos().list(part='snippet', id=vid).execute()['items'][0]['snippet']
            body = {'id': vid, 'paidProductPlacementDetails': {'hasPaidProductPlacement': False}}; parts = ['paidProductPlacementDetails']
            if k and 'tags' not in done:
                body['snippet'] = {f: cur[f] for f in ('title', 'description', 'categoryId', 'defaultLanguage', 'defaultAudioLanguage') if f in cur}; body['snippet']['tags'] = k['tags']; parts.append('snippet')
            Y.spend(Y.cost('videos.update'), f'repack {it["id"]}', limit=LIMIT)
            yt.videos().update(part=','.join(parts), body=body).execute()
            done += ['paid_promotion_no'] + (['tags'] if 'snippet' in parts else []); C.save(f'{R}/publish_log.json', log)
        if k:
            for pl in k['playlists']:
                if f'playlist {pl}' in e['done'] or f'playlist {pl}' in done: continue
                Y.spend(Y.cost('playlistItems.insert'), 'playlist', limit=LIMIT)
                yt.playlistItems().insert(part='snippet', body={'snippet': {'playlistId': pl, 'resourceId': {'kind': 'youtube#video', 'videoId': vid}}}).execute()
                done.append(f'playlist {pl}'); C.save(f'{R}/publish_log.json', log)
            if 'captions' not in done and 'captions' not in e['done']:
                from googleapiclient.http import MediaFileUpload
                Y.spend(Y.cost('captions.insert'), 'captions', limit=LIMIT)
                yt.captions().insert(part='snippet', body={'snippet': {'videoId': vid, 'language': 'en', 'name': 'English', 'isDraft': False}},
                                     media_body=MediaFileUpload(k['captions'], mimetype='application/octet-stream')).execute()
                done.append('captions'); C.save(f'{R}/publish_log.json', log)
        C.event(R, f'REPACK {it["id"]}: {done}'); print(f'{it["id"]:14} {vid}: {", ".join(done)}')

def status(R):
    for_run(R)
    P = C.load(f'{R}/plan.json'); pkg = C.load(f'{R}/publish/shorts_package.json') or {}; log = C.load(f'{R}/publish_log.json', {}) or {}
    for it in [i for i in P['items'] if i['kind'] in ('yt_clip', 'yt_short')]:
        k = pkg.get(it['id']) or {}; e = log.get(it['id']) or {}
        print(f'{it["id"]:14} ' + (f'tags {k.get("tags_youtube_count")}/500, {len(k.get("playlists", []))} playlists, {k.get("cues")} cues | ' if k else '') + f'applied: {e.get("repack") or "-"}')

def main():
    a = sys.argv[1:]
    if len(a) < 2: print(__doc__); sys.exit(1)
    cmd, R = a[0], a[1].rstrip('/'); only = a[a.index('--id') + 1] if '--id' in a else None
    if cmd == 'build':
        pkg = build(R)
        for k, v in pkg.items(): print(f'{k:14} tags {v["tags_youtube_count"]}/500 ({len(v["tags"])}), playlists {v["playlist_names"]}, {v["cues"]} subtitle cues')
    elif cmd == 'apply': apply(R, only)
    elif cmd == 'status': status(R)
    else: print(__doc__); sys.exit(1)

if __name__ == '__main__': main()
