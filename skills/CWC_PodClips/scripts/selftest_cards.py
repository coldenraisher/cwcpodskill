"""selftest_cards.py - the EDIT and PACKAGE cards and the lock's readiness, against a FAKE Telegram on synthetic state
(no network, no Resolve). Run after any change to tg_edit.py, tg_pack.py, tg_listen.py, lock.py or common.update.
Exit 0 = OK."""
import os, sys, json, shutil, tempfile
tmp = tempfile.mkdtemp(prefix='podclips_cards_'); os.environ['CWC_ROOT'] = tmp
import common as C, tg_themes as G, tg_edit as E, tg_pack as K, package as PK, thumbs as TH, lock as L
calls = []; hook = [None]; mids = [500]
def fake_api(method, _http=None, **p):
    calls.append((method, p))
    if hook[0]: f = hook[0]; hook[0] = None; f()
    if method == 'sendMessage': mids[0] += 1; return {'message_id': mids[0]}
    return {}
def fake_multipart(method, fields, files): mids[0] += 1; calls.append((method, fields)); return {'message_id': mids[0]}
G.api = fake_api; G.chat = lambda: 42; E.multipart = fake_multipart
ok = True
def expect(name, cond):
    global ok; ok &= bool(cond); print(('PASS  ' if cond else 'FAIL  ') + name)
def work(show='creative-lens'):
    W = f'{tmp}/clips/{show}/Ep77'; os.makedirs(f'{W}/edit/t01', exist_ok=True); os.makedirs(f'{W}/package/t01', exist_ok=True); os.makedirs(f'{W}/review', exist_ok=True)
    C.save(f'{W}/episode.json', {'show': 'creative-lens', 'show_name': 'The Creative Lens', 'ep_key': 'Ep77', 'ep_no': 77})
    C.save(f'{W}/checked.json', {'episode': {'label': 'The Creative Lens Ep 77', 'ep_key': 'Ep77'}, 'themes': {'t01': {'title': 'A Title'}}})
    C.save(f'{W}/approved.json', {'approved': [{'id': 't01', 'title': 'A Title'}]})
    return W
def tap(data, mid, chat=42): return {'update_id': 1, 'callback_query': {'id': 'q', 'data': data, 'message': {'message_id': mid, 'chat': {'id': chat}}}}
def say(text, reply=None): return {'update_id': 2, 'message': {'chat': {'id': 42}, 'text': text, **({'reply_to_message': {'message_id': reply}} if reply else {})}}
def ver(W, v, ch='cwc', status='draft', **kw):
    vs = C.load(C.vpath(W, 't01'), []); vs.append(dict({'v': v, 'channel': ch, 'timeline': f'T {ch} v{v}', 'plan': f'{W}/edit/t01/build.{ch}.v{v}.json', 'edit_sha': kw.pop('sha', f'sha{v}'), 'status': status}, **kw)); C.save(C.vpath(W, 't01'), vs)
def item(W, key, mid, status='sent'): C.update(E.rpath(W), lambda s: s['items'].__setitem__(key, {'status': status, 'message_id': mid, 'notes': []}), {'items': {}})
answers = lambda: [p.get('text') for m, p in calls if m == 'answerCallbackQuery']

# ---------------- EDIT cards ----------------
W = work(); ver(W, 1); item(W, 't01|cwc|v1', 10)
W2 = work('colden-todd'); ver(W2, 1); item(W2, 't01|cwc|v1', 30)            # ANOTHER show, same episode key, same theme id
expect('a tap on another show\'s card (same Ep key) is not claimed', E.handle(W, tap('pe|Ep77|t01|cwc|v1|both', 30)) is False and E.rstate(W)['items']['t01|cwc|v1']['status'] == 'sent')
expect('Changes -> the next plain message is that version\'s note', E.handle(W, tap('pe|Ep77|t01|cwc|v1|chg', 10)) and E.handle(W, say('tighten the hook')) and E.rstate(W)['items']['t01|cwc|v1']['notes'][0]['text'] == 'tighten the hook' and E.rstate(W)['items']['t01|cwc|v1']['status'] == 'changes')
rows, missing, stale = L.ready(W)
expect('lock is NOT ready while a Changes note has no new version', any('Changes' in m for m in missing))
ver(W, 2); item(W, 't01|cwc|v2', 20); E.retire(W, 't01', 'cwc', 't01|cwc|v2', 'replaced by v2')
expect('sending v2 retires the v1 card: item superseded, the version row superseded, buttons stripped', E.rstate(W)['items']['t01|cwc|v1']['status'] == 'superseded' and not C.live(C.load(C.vpath(W, 't01'))[0]) and any(m == 'editMessageReplyMarkup' and p['message_id'] == 10 for m, p in calls))
calls.clear(); E.handle(W, tap('pe|Ep77|t01|cwc|v1|both', 10))
expect('a tap on the retired v1 card approves NOTHING (answered "replaced")', E.rstate(W)['items']['t01|cwc|v1']['status'] == 'superseded' and C.load(C.vpath(W, 't01'))[0].get('channels') is None and any('replaced' in (a or '') for a in answers()))
hook[0] = lambda: item(W, 't01|tcl|v9', 99)                                    # another card is SENT while this tap is being answered
E.handle(W, tap('pe|Ep77|t01|cwc|v2|both', 20)); st = E.rstate(W)['items']
expect('approve on the current card: version approved for both channels', st['t01|cwc|v2']['status'] == 'approved' and C.load(C.vpath(W, 't01'))[1]['channels'] == ['cwc', 'tcl'])
expect('a card sent WHILE the tap was being answered is not lost (state re-read under the lock)', 't01|tcl|v9' in st)
C.update(E.rpath(W), lambda s: s['items'].pop('t01|tcl|v9'))
calls.clear(); E.handle(W, tap('pe|Ep77|t01|cwc|v2|tcl', 20))
expect('a second tap on an approved card changes nothing', C.load(C.vpath(W, 't01'))[1]['channels'] == ['cwc', 'tcl'] and 'Already approved.' in answers())
# ---------------- the lock's readiness ----------------
rows, missing, stale = L.ready(W)
expect('approved for both, tcl not built -> not ready, says build the tcl version', any('--channel tcl' in m for m in missing))
m1 = f'{W}/edit/t01/master/a.mp4'; os.makedirs(os.path.dirname(m1)); open(m1, 'w').write('x')
C.set_version(W, 't01', 'cwc', 2, master={'file': m1}); ver(W, 1, 'tcl', 'approved', sha='sha2', channels=['tcl'], approved_via='cwc v2', master={'file': m1})
rows, missing, stale = L.ready(W)
expect('both channels built (same edit) with masters, the old Changes card retired -> READY', not missing and sorted(v['channel'] for _, v in rows) == ['cwc', 'tcl'])
ver(W, 3)                                                                       # a newer build after the approval, not yet reviewed
rows, missing, stale = L.ready(W)
expect('a newer draft build than the approved one -> NOT ready (it would be deleted by the cleanup)', any('newer build v3' in m for m in missing))
import next as N
C.save(f'{W}/themes.json', {'themes': []}); st = N.main(W)
expect('next.py names the newer draft\'s next step instead of calling the clip finished', st['stage'] == 2 and any(x.startswith('t01|cwc|v3') for x in st['next'] + st['waiting']))
C.save(f'{W}/review/state.json', {'themes': {'t01': {'status': 'sent', 'message_id': 1}}}); st = N.main(W)
expect('next.py: a revised theme that went back to him is listed as waiting, its edit holds', any('theme t01' in x for x in st['waiting']) and not any(x.startswith('t01') for x in st['next']))
os.remove(f'{W}/review/state.json')
E.supersede(W, 't01', 'cwc', 3, 'test build, not wanted'); rows, missing, stale = L.ready(W)
expect('tg_edit.py supersede retires it -> ready again', not missing and len(rows) == 2)
for ch, v in (('cwc', 2), ('tcl', 1)): C.set_version(W, 't01', ch, v, status='locked')
ver(W, 4, status='approved', channels=['cwc'], approved_at='2099-01-01', master={'file': m1})
rows, missing, stale = L.ready(W)
expect('a change AFTER the lock (v4 approved for cwc only): v4 is locked, the old locked cwc and tcl versions are stale', not missing and [(v['channel'], v['v']) for _, v in rows] == [('cwc', 4)] and sorted((v['channel'], v['v']) for _, v in stale) == [('cwc', 2), ('tcl', 1)])
# ---------------- drop ----------------
W3 = f'{tmp}/clips/creative-lens/Ep78'; shutil.copytree(W, W3); C.save(f'{W3}/episode.json', dict(C.load(f'{W3}/episode.json'), ep_key='Ep78'))
for x in C.load(C.vpath(W3, 't01')): C.set_version(W3, 't01', x['channel'], x['v'], status='draft' if C.live(x) else x['status'])
E.drop(W3, 't01', 'Colden: "skip this one"'); a3 = C.load(f'{W3}/approved.json')
expect('drop: the clip leaves approved.json (kept under dropped with his words), every version retired, lock has nothing waiting on it', not a3['approved'] and a3['dropped'][0]['words'] and not any(C.live(x) for x in C.load(C.vpath(W3, 't01'))) and L.ready(W3)[1] == [])

# ---------------- PACKAGE cards ----------------
PK.check_one = lambda W, tid, ch, final=False: []
d = f'{W}/package/t01/thumbs/cwc'; os.makedirs(d); files = []
for i in range(7): f = f'{d}/f{i}.png'; open(f, 'w').write(f'img{i}'); files.append(f)
C.save(f'{W}/package/t01/copy.cwc.json', {'titles': ['T one', 'T two', 'T three']})
C.save(f'{W}/package/t01/thumbs.cwc.json', {'options': files[:4], 'kinds': ['frame', 'hook', 'ai-1', 'ai-2'], 'grid': files[4]})
K.send(W, 't01', 'cwc'); c1 = K.item(W, 't01|cwc')['message_id']
hook[0] = lambda: C.update(K.rpath(W), lambda s: s['items'].__setitem__('t09|tcl', {'status': 'sent', 'message_id': 900}))
K.handle(W, tap('pk|Ep77|t01|cwc|t|1', c1)); K.handle(W, tap('pk|Ep77|t01|cwc|h|2', c1)); it = K.item(W, 't01|cwc')
expect('title 2 + thumb 3 -> picked; A written into the copy, the pick into the thumbs record', it['status'] == 'picked' and C.load(f'{W}/package/t01/copy.cwc.json')['A'] == 'T two' and TH.rec(W, 't01', 'cwc')['pick'] == 2)
expect('a package card sent while the tap was being answered is not lost', 't09|tcl' in K.rstate(W)['items'])
C.update(f'{W}/package/t01/copy.cwc.json', lambda c: c.update(B='B title', C='C title'))
C.update(TH.paths(W, 't01', 'cwc')[1], lambda r: r.update(abc={'A': files[2], 'B': files[5], 'C': files[6]}, abc_grid=files[4], ai={'C': {'file': files[6], 'for_title': 'another title'}}))
try: K.send_abc(W, 't01', 'cwc'); refused = False
except SystemExit: refused = True
expect('A/B/C card refused when thumbnail C was made for another title C', refused)
C.update(TH.paths(W, 't01', 'cwc')[1], lambda r: r['ai']['C'].update(for_title='C title'))
K.send_abc(W, 't01', 'cwc'); a1 = K.item(W, 't01|cwc')['abc_message_id']
K.handle(W, tap('pk|Ep77|t01|cwc|a|1', a1))
expect('Approve A/B/C on the current card -> approved, and package.py may build', K.item(W, 't01|cwc')['abc'] == 'approved' and K.approved(W, 't01', 'cwc')[0])
open(files[5], 'w').write('a different B')
expect('a thumbnail changed after the approval -> not approved any more (send-abc again)', not K.approved(W, 't01', 'cwc')[0])
open(files[5], 'w').write('img5'); K.handle(W, say('B looks off', reply=a1))
expect('a note after the A/B/C approval re-opens the set (build refuses)', K.item(W, 't01|cwc')['abc'] == 'notes' and not K.approved(W, 't01', 'cwc')[0])
K.send_abc(W, 't01', 'cwc'); a2 = K.item(W, 't01|cwc')['abc_message_id']; calls.clear(); K.handle(W, tap('pk|Ep77|t01|cwc|a|1', a1))
expect('a tap on the OLD A/B/C card approves nothing (answered "replaced")', K.item(W, 't01|cwc')['abc'] == 'sent' and any('replaced' in (a or '') for a in answers()))
K.handle(W, tap('pk|Ep77|t01|cwc|a|1', a2)); K.send(W, 't01', 'cwc'); it = K.item(W, 't01|cwc')
expect('re-sending card 1 voids the old pick, A / B / C and the A/B/C approval', it['status'] == 'sent' and not it.get('abc') and 'A' not in C.load(f'{W}/package/t01/copy.cwc.json') and TH.rec(W, 't01', 'cwc')['pick'] is None and not K.approved(W, 't01', 'cwc')[0])
# ---------------- whose notes? the last Notes / Changes tap wins ----------------
ver(W, 5); item(W, 't01|cwc|v5', 50)
K.handle(W, tap('pk|Ep77|t01|cwc|n|0', it['message_id'])); E.handle(W, tap('pe|Ep77|t01|cwc|v5|chg', 50))
took_pack = K.handle(W, say('make the b-roll longer')); took_edit = E.handle(W, say('make the b-roll longer'))
expect('Notes tapped on a package card, then Changes on an edit card: the message goes to the EDIT card only', not took_pack and took_edit and E.rstate(W)['items']['t01|cwc|v5']['notes'][-1]['text'] == 'make the b-roll longer')
shutil.rmtree(tmp); print('\nSELFTEST CARDS ' + ('OK' if ok else 'FAILED')); sys.exit(0 if ok else 1)
