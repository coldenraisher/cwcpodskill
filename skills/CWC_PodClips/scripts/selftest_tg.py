"""selftest_tg.py - the Telegram approval flow with a FAKE Telegram (nothing is sent, no network): send -> approve ->
kill -> runner-up -> notes -> resend -> approve -> approved.json. Run after any change to tg_themes.py. Exit 0 = OK."""
import os, sys, json, copy, shutil, tempfile, io, contextlib
tmp = tempfile.mkdtemp(prefix='podclips_tgtest_'); os.environ['CWC_ROOT'] = tmp
import common as C, themes as T, check as CK, tg_themes as G
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'selftest.py')).read()
exec(src[src.index("W = f'{tmp}/clips"):src.index('ok = True')])          # the synthetic episode + theme() + cold() + run()
base = [theme(i + 1, 1 + i * 130, 120 + i * 130) for i in range(6)]
sent = []; queue = []; uid = [100]
def fake_api(method, _http=30, **p):
    if method == 'sendMessage': sent.append(p); return {'message_id': 1000 + len(sent)}
    if method == 'getUpdates':
        if not queue: raise SystemExit('script ran out of updates before the poll finished')
        x = queue.pop(0); return [x() if callable(x) else x]
    return {}
G.api = fake_api; G.chat = lambda: 42; G.others_polling = lambda: []
def tap(act, tid, mid=None, chat=42):
    def make():                                           # resolved when it is delivered: the tap is on the theme's CURRENT card
        uid[0] += 1; return {'update_id': uid[0], 'callback_query': {'id': 'x', 'data': f'pc|EpTEST|{act}|{tid}', 'message': {'message_id': mid or G.state(W)['themes'].get(tid, {}).get('message_id'), 'chat': {'id': chat}}}}
    return make
def say(text, chat=42): uid[0] += 1; return {'update_id': uid[0], 'message': {'chat': {'id': chat}, 'text': text}}
ok = True
def expect(name, cond):
    global ok; ok &= bool(cond); print(('PASS  ' if cond else 'FAIL  ') + name)
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    run(copy.deepcopy(base)); G.send(W, dry=False)
st = G.state(W); expect('send: a header + 5 theme messages, the runner-up is NOT sent', len(sent) == 6 and set(st['themes']) == {'t01', 't02', 't03', 't04', 't05'})
expect('each card is short (title, summary, hook; under 600 characters) with three buttons', all('HOOK' in m['text'] and 'Theme' in m['text'] and len(m['text']) < 600 and 'PAYOFF' not in m['text'] and len(m['reply_markup']['inline_keyboard'][0]) == 3 for m in sent[1:]) and len(sent[0]['text']) < 250)
queue += [tap('ok', 't01'), {'update_id': 7, 'callback_query': {'id': 'y', 'data': 'ok:03', 'message': {'message_id': 1, 'chat': {'id': 42}}}}, tap('ok', 't02', chat=999), tap('ok', 't02', mid=99999),
          tap('kill', 't02'), say('too close to last week\'s video'), tap('notes', 't03'), say('open on the price, not the specs'), tap('ok', 't04'), tap('ok', 't05'), tap('ok', 't06')]
with contextlib.redirect_stdout(buf):
    try: G.poll(W, 0)
    except SystemExit as e: stop = str(e)
st = G.state(W)
expect('approve -> approved', st['themes']['t01']['status'] == 'approved')
log = open(f'{W}/review/events.log').read()
expect('a tap from another skill, another chat, or on a card that is not this episode\'s (unknown message id) is ignored', st['themes']['t02']['status'] == 'killed' and log.count('FOREIGN') >= 3)
expect('kill -> killed, the runner-up t06 is sent', st['themes']['t02']['status'] == 'killed' and st['themes'].get('t06', {}).get('replaces') == 't02')
expect('notes -> stored on the theme, status notes, the set stays open (no approved.json)', st['themes']['t03']['status'] == 'notes' and st['themes']['t03']['notes'][0]['text'].startswith('open on the price') and not os.path.exists(f'{W}/approved.json'))
with contextlib.redirect_stdout(buf): G.send(W, dry=False, only='t03')
expect('resend -> round 2', G.state(W)['themes']['t03']['round'] == 2 and G.state(W)['themes']['t03']['status'] == 'sent')
old_mid = [m for m in G.state(W)['themes']['t03']['old_message_ids']][0]
queue += [tap('ok', 't03', mid=old_mid), say('thinking about it'), tap('ok', 't03')]
with contextlib.redirect_stdout(buf): rc = G.poll(W, 0)
expect('a tap on the OLD card of a revised theme changes nothing (answered "revised"); only the new card approves', 'APPROVED t03' in open(f'{W}/review/events.log').read().split('SENT t03 round 2')[1] and G.state(W)['themes']['t03']['old_message_ids'] == [old_mid])
ap = C.load(f'{W}/approved.json')
expect('all settled -> approved.json with 5 approved (t02 killed), poll exits 0', rc == 0 and ap and [a['id'] for a in ap['approved']] == ['t01', 't03', 't04', 't05', 't06'] and ap['killed'] == ['t02'])
dec = [json.loads(l) for l in open(f'{tmp}/data/decisions.jsonl')]
expect('every decision is logged with the theme attributes', {d['decision'] for d in dec} >= {'approved', 'killed', 'notes'} and all('total' in d['attrs'] for d in dec))
# ---- manual review: fewer than 3 pass -> flag + one card per held theme; Approve on a held card = Colden's override
shutil.rmtree(f'{W}/review'); os.remove(f'{W}/approved.json'); del sent[:]; del queue[:]
weak = copy.deepcopy(base)
for x in weak[:5]: x['scores']['story']['s'] = 2
with contextlib.redirect_stdout(buf):
    run(weak)
    try: G.send(W, dry=False); sent_anyway = True
    except SystemExit: sent_anyway = False
    G.flag(W, dry=False)
st = G.state(W)
expect('fewer than 3 pass: send refuses, flag sends the summary + the passing theme + the held cards (5 at most)', not sent_anyway and len(sent) == 1 + 1 + 5 and 'minimum 3' in sent[0]['text'] and sum('HELD' in m['text'] for m in sent[1:]) == 5 and all(len(m['text']) < 600 for m in sent))
held_ids = [t for t, v in st['themes'].items() if v.get('manual')]
queue += [tap('ok', 't06'), tap('ok', held_ids[0])] + [tap('kill', t) for t in held_ids[1:]]
with contextlib.redirect_stdout(buf): rc = G.poll(W, 0)
ap = C.load(f'{W}/approved.json'); dec = [json.loads(l) for l in open(f'{tmp}/data/decisions.jsonl')]
expect('Approve on a held card is logged as his manual override and carried into approved.json with the hold reasons', rc == 0 and [a['manual_override'] for a in ap['approved']] == [False, True] and ap['approved'][1]['held_for'] and any(d['decision'] == 'approved-manual' for d in dec))
expect('no runner-up message is sent in manual review', not any('runner-up' in m.get('text', '').lower() for m in sent[7:]))
shutil.rmtree(tmp); print('\nSELFTEST TG ' + ('OK' if ok else 'FAILED')); sys.exit(0 if ok else 1)
