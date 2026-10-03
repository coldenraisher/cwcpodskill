"""tg_plan.py send <RUN> | wrapup <RUN> | handle | install | selftest      the ONE approval of the posting plan, on Telegram
  send     the plan as one card (split over messages when long; the buttons sit on the last one):
           [Schedule all] [Changes]. Callback data "pa|<show+ep>|ok|<sha8>" / "pa|<show+ep>|chg|<sha8>" (64-byte limit).
  handle   (the listener plugin; stdin = one Telegram update) exit 0 = handled, 3 = not ours, 1 = error.
           Schedule all -> run.json plan_approval {sha, by, at} + "PLAN APPROVED". A tap on a card whose plan was rebuilt
           changes nothing (the sha no longer matches). Changes -> his next message (or a reply to the card) is stored as
           plan_notes_open -> change the inputs, plan.py build, send again.
  wrapup   the closing message: what posts when and where, what is still his (manual posts, Studio uploads, Studio checklist).
  install  add CWC_PodRun to ~/.config/cwc/listen_plugins.json (idempotent; CWC_PodClips' listener must be restarted)
  selftest a foreign callback must come back 3
Nothing is posted by this script. Approval binds the plan's sha: plan.py build makes a new sha, so any change = a new card."""
import os, sys, json, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
import tg

SHOW_CODE = {'creative-lens': 'cl', 'colden-todd': 'ct'}
NET = {'facebook': 'FB', 'instagram': 'IG', 'tiktok': 'TT'}

def key(r): return f'{SHOW_CODE.get(r["show"], r["show"][:2])}{r.get("ep_no") or r["ep_key"]}'

def card_text(r, P):
    B = C.brands(); w = P['window']; L = []
    route = 'I upload + schedule' if P['youtube_route'] == 'youtube_api' else 'you upload + schedule in Studio (list in Final/), I write every piece of metadata - audit pending'
    L.append(f'POSTING PLAN - {r["show_name"]} {r["ep_key"]}')
    L.append(f'{w["start_dow"]} {w["start"][5:]} -> {w["end_dow"]} {w["end"][5:]} (ET). YouTube: {route}.')
    caps = ' | '.join(f'{B[b]["label"]} {mo[5:]}/{mo[:4]}: {v["used_before"]} used + {v["planned_metricool"]} new = {v["used_before"] + v["planned_metricool"]}/{v["cap"]}'
                      for b, ms in P['counts'].items() for mo, v in ms.items() if v['planned_metricool'] or v['manual'] or v['used_before'])
    if caps: L.append(f'Metricool: {caps}')
    man = [i for i in P['items'] if i['route'] == 'manual']
    if man: L.append(f'Over the cap -> {len(man)} posts by hand (kit in Final/Manual Posts)')
    groups = {}
    for i in P['items']:
        groups.setdefault((i['publish_at'], i['brand'], i['ref'], i['product']), []).append(i)
    day = None
    for (at, b, ref, prod), its in sorted(groups.items()):
        t = dt.datetime.fromisoformat(at)
        if t.date() != day: day = t.date(); L.append(''); L.append(f'{C.DAYS[t.weekday()].upper()} {t:%m/%d}')
        lab = 'CWC' if b == 'cwc' else 'TCL'
        if prod == 'clip': what = 'Clip'
        else:
            soc = next((x for x in its if x['kind'] == 'social'), None)
            nets = '/'.join(NET[n] for n in soc['networks']) if soc else ''
            what = 'Short YT' + (f' + {nets}' if soc and soc['route'] == 'metricool' else f' + {nets} BY HAND' if soc else '')
        title = next((x['title'] for x in its if x['kind'] != 'social'), its[0]['title'])
        L.append(f' {t:%H:%M} {lab} {what}: {title[:60]}')
    if P['warnings']: L.append(''); L += [f'- {x}' for x in P['warnings'][:6]]
    return '\n'.join(L)

def chunks(text, n=3500):
    out, cur = [], ''
    for line in text.split('\n'):
        if len(cur) + len(line) + 1 > n: out.append(cur); cur = ''
        cur += line + '\n'
    return out + [cur] if cur.strip() else out

def send(R):
    r = C.run(R); P = C.load(f'{R}/plan.json') or C.fail('no plan.json - plan.py build first')
    if (r.get('plan_approval') or {}).get('sha') == P['sha']: C.fail('this plan is already approved')
    k = key(r); s8 = P['sha'][:8]; ids = []
    parts = chunks(card_text(r, P))
    for n, part in enumerate(parts):
        kb = [[{'text': 'Schedule all', 'callback_data': f'pa|{k}|ok|{s8}'}, {'text': 'Changes', 'callback_data': f'pa|{k}|chg|{s8}'}]] if n == len(parts) - 1 else None
        ids.append(tg.say(part, kb)['message_id'])
    r['plan_card'] = {'sha': P['sha'], 'message_ids': ids, 'chat_id': tg.chat(), 'at': C.now()}; r.pop('plan_notes_open', None); r.pop('plan_notes_awaiting', None)
    C.save_run(R, r); C.event(R, f'PLAN CARD SENT {P["sha"]} ({len(ids)} message(s))'); print(f'plan card sent ({len(ids)} message(s)); waiting for Schedule all / Changes')

def find_run(k):
    for R in C.runs():
        r = C.load(f'{R}/run.json') or {}
        if r.get('show') and key(r) == k: return R, r
    return None, None

def handle(u):
    q = u.get('callback_query')
    if q:
        data = str(q.get('data', ''))
        if not data.startswith('pa|'): return False
        if data == 'pa|noop': tg.ack(q); return True
        _, k, action, s8 = (data.split('|') + ['', '', ''])[:4]
        R, r = find_run(k)
        if not R: tg.ack(q, 'No run for this card any more'); return True
        P = C.load(f'{R}/plan.json') or {}
        if not P.get('sha', '').startswith(s8) or (r.get('plan_card') or {}).get('sha') != P.get('sha'):
            tg.ack(q, 'This plan was replaced - use the newest card'); return True
        msg = (q.get('message') or {}); mid, cid = msg.get('message_id'), (msg.get('chat') or {}).get('id')
        if action == 'ok':
            tg.ack(q, 'Approved - scheduling')
            r['plan_approval'] = {'sha': P['sha'], 'by': 'Colden (Telegram)', 'at': C.now(), 'rules': P.get('rules'), 'message_id': mid}
            r.pop('plan_notes_open', None); r.pop('plan_notes_awaiting', None); C.save_run(R, r)
            C.event(R, f'PLAN APPROVED {P["sha"]}')
            if mid: tg.relabel(cid, mid, 'Schedule all - APPROVED')
            tg.say(f'PLAN APPROVED - {r["ep_key"]}: {len(P["items"])} posts. Scheduling now; the wrap-up follows when it is done.')
        elif action == 'chg':
            tg.ack(q, 'Send your changes as a message')
            r['plan_notes_awaiting'] = mid; C.save_run(R, r); C.event(R, f'PLAN CHANGES requested {P["sha"]}')
            if mid: tg.relabel(cid, mid, 'Changes - send them as a message')
        else: tg.ack(q)
        return True
    m = u.get('message') or {}
    text = m.get('text')
    if not text or text.startswith('/'): return False
    reply = (m.get('reply_to_message') or {}).get('message_id')
    for R in C.runs():
        r = C.load(f'{R}/run.json') or {}
        card = (r.get('plan_card') or {}).get('message_ids', [])
        if (reply and reply in card) or (r.get('plan_notes_awaiting') and not reply):
            r['plan_notes_open'] = text; r.pop('plan_notes_awaiting', None); C.save_run(R, r); C.event(R, f'PLAN NOTES: {text[:300]}')
            tg.say('Got it - I will change the plan and send a new card.'); return True
    return False

def wrapup(R):
    r = C.run(R); P = C.load(f'{R}/plan.json'); log = C.load(f'{R}/publish_log.json', {}) or {}
    if (r.get('plan_approval') or {}).get('sha') != P['sha']: C.fail('the plan is not approved')
    by = {}
    for i in P['items']: by.setdefault(i['route'], []).append(i)
    L = [f'WRAP-UP - {r["show_name"]} {r["ep_key"]}']
    mc = [i for i in by.get('metricool', []) if i['id'] in log]; L.append(f'Metricool: {len(mc)}/{len(by.get("metricool", []))} scheduled')
    if by.get('youtube_api'): L.append(f'YouTube (API): {sum(1 for i in by["youtube_api"] if i["id"] in log)}/{len(by["youtube_api"])} uploaded + scheduled')
    if by.get('studio_manual'):
        done = sum(1 for i in by['studio_manual'] if (log.get(i['id']) or {}).get('route') == 'studio_manual')
        L.append(f'YouTube (you in Studio): metadata written on {done}/{len(by["studio_manual"])} - the rest after you upload them (Final/YouTube Upload List.md)')
    if by.get('manual'): L.append(f'By hand (over the Metricool cap): {len(by["manual"])} posts - Final/Manual Posts')
    L.append(f'Studio checklist (Test & Compare, end screens, pinned comments): publish/studio_checklist.md + the posting dashboard in Final/')
    tg.say('\n'.join(L)); r.setdefault('stages', {})['wrapup'] = {'at': C.now()}; C.save_run(R, r); C.event(R, 'WRAP-UP SENT')

def main():
    a = sys.argv[1:]; cmd = a[0] if a else ''
    if cmd == 'handle':
        u = json.loads(sys.stdin.read() or '{}')
        try: ok = handle(u)
        except SystemExit as x: print(f'handler exit {x.code}', file=sys.stderr); sys.exit(1)
        sys.exit(0 if ok else 3)
    elif cmd == 'send': send(a[1].rstrip('/'))
    elif cmd == 'wrapup': wrapup(a[1].rstrip('/'))
    elif cmd == 'install':
        p = f'{C.CFG}/listen_plugins.json'; cur = C.load(p, []) or []
        me = {'name': 'CWC_PodRun', 'cmd': [sys.executable, os.path.abspath(__file__), 'handle']}
        cur = [x for x in cur if x.get('name') != 'CWC_PodRun'] + [me]; C.save(p, cur); print(json.dumps(cur, indent=1))
        print('restart CWC_PodClips\' listener so it reads the new plugin list: tg_listen.py stop, then start')
    elif cmd == 'selftest':
        import subprocess
        res = subprocess.run([sys.executable, os.path.abspath(__file__), 'handle'], input=json.dumps({'update_id': 1, 'callback_query': {'id': 'x', 'data': 'pr|cl24|t|s01'}}), capture_output=True, text=True)
        assert res.returncode == 3, (res.returncode, res.stderr); print('foreign callback -> 3 ok')
    else: print(__doc__); sys.exit(1)

if __name__ == '__main__': main()
