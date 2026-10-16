"""buffer.py payloads|record|status <RUN> - THIS RUN's Facebook / Instagram / TikTok through Colden's Buffer MCP
(run.json social_route, his words, not a rule change - Ep 26 2026-10-16: "can we use my MCP to schedule the first 4 out?
Buffer's limit is 10 at a time so the next round will need to be uploaded monday"). Buffer takes ONE channel per post, so a
reel = one Buffer post per network (Facebook reel, Instagram reel, TikTok).
  payloads <RUN> <batch> [--now ISO]   the approved plan's buffer items of that batch -> publish/buffer_payloads.json: per
                                       post the create_post arguments (channelId from references/brands.json "buffer").
                                       Claude fires each with create_post on the Buffer connector and records it BEFORE the next.
  record   <RUN> <item id> <network> <answer.json | ->   the connector's answer (post id) -> publish_log.json "<item>|<network>"
  status   <RUN>
GATES: the plan is the approved one (sha) and his social posting yes is on file (run.json social_route.<brand>.by); only
the brand's Buffer channels for facebook / instagram / tiktok, never YouTube; both media links present (metricool.py upload);
the slot >= now + 15 min; a post already in publish_log.json is never sent again; record refuses an answer without a post id.
Not carried by Buffer (said on the plan card): Instagram collaborators (added by hand in the app), a custom cover image, the
first comment (his free plan: "First comment requires a paid plan", 2026-10-16) - listed per post to add by hand."""
import os, sys, json, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
from metricool import approved_plan

def chans(b):
    bf = (C.brands().get(b) or {}).get('buffer') or C.fail(f'no Buffer channels on file for {b} (references/brands.json "buffer")')
    return bf

def payloads(R, batch, now=None):
    r, P = approved_plan(R); sr = (r.get('social_route') or {})
    log = C.load(f'{R}/publish_log.json', {}) or {}; links = C.load(f'{R}/publish/drive_links.json', {}) or {}
    now = C.et(now) if now else dt.datetime.now(C.ET); out, bad = [], []
    for it in P['items']:
        if it['kind'] != 'social' or it.get('route') != 'buffer' or it.get('buffer_batch') != batch: continue
        b = it['brand']; v = sr.get(b) or {}
        if v.get('route') != 'buffer' or not v.get('by'): bad.append(f'{it["id"]}: no Buffer route with his words for {b} in run.json'); continue
        ch = chans(b); ln = links.get(it['id']) or {}
        if not ln.get('video_direct'): bad.append(f'{it["id"]}: no public video link - metricool.py upload first'); continue
        t = dt.datetime.fromisoformat(it['publish_at'])
        if t < now + dt.timedelta(minutes=15): bad.append(f'{it["id"]}: {t:%a %H:%M} is too close or past - plan.py build again + a new approval'); continue
        for n in it['networks']:
            if n not in ('facebook', 'instagram', 'tiktok'): bad.append(f'{it["id"]}: network {n} never through Buffer'); continue
            key = f'{it["id"]}|{n}'
            if key in log: continue
            if not ch.get(n): bad.append(f'{key}: no Buffer {n} channel on file for {b}'); continue
            a = {'channelId': ch[n], 'schedulingType': 'automatic', 'mode': 'customScheduled', 'dueAt': t.isoformat(timespec='seconds'),
                 'text': it['text'], 'assets': [{'video': {'url': ln['video_direct'], 'metadata': {'title': it['title'][:90]}}}]}
            if n == 'facebook': a['metadata'] = {'facebook': {'type': 'reel'}}
            if n == 'instagram': a['metadata'] = {'instagram': {'type': 'reel', 'shouldShareToFeed': True}}
            if n == 'tiktok': a['metadata'] = {'tiktok': {'title': it['title'][:90]}}
            out.append({'key': key, 'id': it['id'], 'network': n, 'brand': b, 'args': a, 'ig_collabs': it.get('ig_collabs') if n == 'instagram' else [],
                        'first_comment_by_hand': it.get('first_comment') if n in ('facebook', 'instagram', 'tiktok') else None})      # Buffer's free plan refuses a first comment (2026-10-16: "First comment requires a paid plan")
    if bad: C.fail('Buffer payloads refused:\n  ' + '\n  '.join(bad))
    C.save(f'{R}/publish/buffer_payloads.json', out)
    for x in out: print(f'{x["key"]:28} {x["args"]["dueAt"]}' + (f'   (collaborators by hand: {x["ig_collabs"]})' if x['ig_collabs'] else ''))
    print(f'{len(out)} Buffer post(s) -> {R}/publish/buffer_payloads.json; fire each with create_post, then: buffer.py record "{R}" <item id> <network> <answer>')

def record(R, item_id, net, src):
    r, P = approved_plan(R); log = C.load(f'{R}/publish_log.json', {}) or {}; key = f'{item_id}|{net}'
    if key in log: C.fail(f'{key} is already recorded - never twice')
    it = next((i for i in P['items'] if i['id'] == item_id), None) or C.fail(f'{item_id}: not in the approved plan')
    ans = json.load(sys.stdin) if src == '-' else json.load(open(src))
    pid = (ans.get('post') or ans).get('id') if isinstance(ans, dict) else None
    if not pid: C.fail(f'{key}: the answer has no post id - not recorded: {str(ans)[:300]}')
    log[key] = {'route': 'buffer', 'brand': it['brand'], 'network': net, 'publish_at': it['publish_at'], 'post_id': pid,
                'status': (ans.get('post') or ans).get('status'), 'at': C.now()}
    C.save(f'{R}/publish_log.json', log); C.event(R, f'BUFFER {key} {it["publish_at"]} post {pid}'); print(f'recorded {key} -> Buffer post {pid}')

def status(R):
    r, P = approved_plan(R); log = C.load(f'{R}/publish_log.json', {}) or {}
    for it in P['items']:
        if it.get('route') != 'buffer': continue
        for n in it['networks']:
            k = f'{it["id"]}|{n}'; print(f'batch {it.get("buffer_batch")} {k:28} {it["publish_at"][:16]}  ' + (f'post {log[k]["post_id"]}' if k in log else 'open'))

if __name__ == '__main__':
    a = sys.argv[1:]
    if not a: C.fail(__doc__)
    if a[0] == 'payloads': payloads(a[1], int(a[2]), a[a.index('--now') + 1] if '--now' in a else None)
    elif a[0] == 'record': record(a[1], a[2], a[3], a[4])
    elif a[0] == 'status': status(a[1])
    else: C.fail(__doc__)
