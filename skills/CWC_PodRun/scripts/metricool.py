"""metricool.py upload|payloads|record|status <RUN>      Facebook / Instagram / TikTok through Metricool (never YouTube)
  upload   <RUN>  the shorts' masters + picked covers -> Google Drive direct links, through CWC_PodReels' own
                  `publish.py upload` (rclone remote + folders from its show file; it refuses before the covers + copy batch
                  is approved). Links land in <REELS WORK>/review/publish.json - Metricool copies the media at scheduling.
  payloads <RUN> [--now ISO]
                  the APPROVED plan's metricool items -> <RUN>/publish/metricool_payloads.json: one createScheduledPost per
                  short per brand with ALL of that brand's networks in ONE post, ONE text, ONE video (Colden 2026-10-03:
                  "all 3 equal 1 as long as you don't make individual changes to the posts"). Claude fires each one through
                  its brand's connector (cwc = the claude.ai Metricool connector, tcl = metricool-tcl) and records the answer.
  record   <RUN> <item id> <answer.json | ->
                  the connector's answer -> publish_log.json (plannerUrl, post id) + data/metricool_ledger.jsonl (the month count)
  status   <RUN>
GATES: the plan is the approved one (sha) - never a youtube provider - networks only from brands.json (TCL: no Facebook) -
both media links present - the slot is still >= now + 15 min (else: plan.py build + a new approval, never a silent shift) -
an item already in publish_log.json is never sent again."""
import os, sys, json, subprocess, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

def approved_plan(R):
    r = C.run(R); P = C.load(f'{R}/plan.json') or C.fail('no plan.json')
    ap = r.get('plan_approval') or {}
    if ap.get('sha') != P['sha']: C.fail(f'plan {P["sha"]} is not approved (approved: {ap.get("sha")}) - tg_plan.py send, wait for "Schedule all"')
    if P.get('rules') != C.RULES: C.fail(f'the plan was built under rules {P.get("rules")}, the skill is on {C.RULES} - rebuild it')
    return r, P

def find(obj, key):
    if isinstance(obj, dict):
        if key in obj: return obj[key]
        for v in obj.values():
            x = find(v, key)
            if x is not None: return x
    if isinstance(obj, list):
        for v in obj:
            x = find(v, key)
            if x is not None: return x
    return None

def payloads(R, now=None):
    r, P = approved_plan(R); B = C.brands(); log = C.load(f'{R}/publish_log.json', {}) or {}
    links = (C.load(f'{r["reels_work"]}/review/publish.json') or {}).get('links', {})
    now = C.et(now) if now else dt.datetime.now(C.ET); out, bad = [], []
    for it in P['items']:
        if it['kind'] != 'social' or it['route'] != 'metricool' or it['id'] in log: continue
        b = it['brand']; mc = B[b]['metricool']; nets = it['networks']
        if 'youtube' in nets: bad.append(f'{it["id"]}: youtube in a Metricool post'); continue
        if set(nets) - set(mc['networks']): bad.append(f'{it["id"]}: {nets} not all connected on {b}'); continue
        ln = (links.get(it['ref']) or {}).get(b) or {}
        if not ln.get('video_direct') or not ln.get('thumb_direct'): bad.append(f'{it["id"]}: no Drive links - metricool.py upload first'); continue
        t = dt.datetime.fromisoformat(it['publish_at'])
        if t < now + dt.timedelta(minutes=15): bad.append(f'{it["id"]}: {t:%a %H:%M} is too close or past - plan.py build again + a new approval'); continue
        info = {'autoPublish': True, 'draft': False, 'descendants': [], 'hasNotReadNotes': False, 'shortener': False, 'smartLinkData': {'ids': []},
                'text': it['text'], 'firstCommentText': it.get('first_comment') or '', 'media': [ln['video_direct']], 'mediaAltText': [],
                'videoThumbnailUrl': ln['thumb_direct'], 'providers': [{'network': n} for n in nets],
                'publicationDate': {'dateTime': t.strftime('%Y-%m-%dT%H:%M:%S'), 'timezone': mc['timezone']}}
        if 'instagram' in nets:
            info['instagramData'] = {'type': 'REEL', 'showReelOnFeed': True, 'collaborators': [{'username': it['ig_collab'], 'deleted': False}] if it.get('ig_collab') else []}
        if 'tiktok' in nets: info['tiktokData'] = {}
        if 'facebook' in nets: info['facebookData'] = {'type': 'REEL', **({'title': it['fb_title']} if it.get('fb_title') else {})}
        out.append({'id': it['id'], 'brand': b, 'connector': mc['connector'], 'blogId': mc['blogId'], 'date': t.isoformat(timespec='seconds'),
                    'info': json.dumps(info, ensure_ascii=False), 'title': it['title']})
    if bad: C.fail('payloads refused:\n  ' + '\n  '.join(bad))
    C.save(f'{R}/publish/metricool_payloads.json', out)
    for x in out: print(f'{x["id"]:18} {x["brand"]} blogId {x["blogId"]} {x["date"]}  via {x["connector"]}')
    print(f'{len(out)} call(s) -> {R}/publish/metricool_payloads.json\nFire each with createScheduledPost(blogId, date, info) on ITS connector, then: metricool.py record "{R}" <id> <answer file>')

def record(R, item_id, src):
    r, P = approved_plan(R); it = next((i for i in P['items'] if i['id'] == item_id), None) or C.fail(f'{item_id} is not in the plan')
    ans = json.load(sys.stdin) if src == '-' else C.load(src)
    if ans is None: C.fail('empty answer')
    if find(ans, 'error') or find(ans, 'errors'): C.fail(f'the connector answered with an error - nothing recorded: {json.dumps(ans)[:300]}')
    log = C.load(f'{R}/publish_log.json', {}) or {}
    if item_id in log: C.fail(f'{item_id} is already recorded ({log[item_id].get("plannerUrl")})')
    pid = str(find(ans, 'id') or find(ans, 'postId') or ''); url = find(ans, 'plannerUrl')
    log[item_id] = {'route': 'metricool', 'brand': it['brand'], 'publish_at': it['publish_at'], 'post_id': pid, 'plannerUrl': url, 'at': C.now()}
    C.save(f'{R}/publish_log.json', log); os.makedirs(C.DATA, exist_ok=True)
    with open(f'{C.DATA}/metricool_ledger.jsonl', 'a', encoding='utf-8') as f:
        f.write(json.dumps({'brand': it['brand'], 'post_id': pid or url, 'publish_at': it['publish_at'], 'run': R, 'item': item_id, 'at': C.now()}) + '\n')
    C.event(R, f'METRICOOL {item_id} {it["brand"]} {it["publish_at"]} {url}'); print(f'{item_id}: recorded {url}')

def main():
    a = sys.argv[1:]
    if len(a) < 2: print(__doc__); sys.exit(1)
    cmd, R = a[0], a[1].rstrip('/')
    if cmd == 'upload':
        r, P = approved_plan(R)
        sys.exit(subprocess.run([sys.executable, f'{C.REELS_SK}/scripts/publish.py', 'upload', r['reels_work']]).returncode)
    elif cmd == 'payloads': payloads(R, a[a.index('--now') + 1] if '--now' in a else None)
    elif cmd == 'record': record(R, a[2], a[3] if len(a) > 3 else C.fail('record <RUN> <item id> <answer file | ->'))
    elif cmd == 'status':
        r, P = approved_plan(R); log = C.load(f'{R}/publish_log.json', {}) or {}
        for it in P['items']:
            if it['kind'] == 'social': print(f'{it["id"]:18} {it["route"]:9} {it["publish_at"][:16]}  ' + (log[it['id']].get('plannerUrl') or 'recorded' if it['id'] in log else 'open'))
    else: print(__doc__); sys.exit(1)

if __name__ == '__main__': main()
