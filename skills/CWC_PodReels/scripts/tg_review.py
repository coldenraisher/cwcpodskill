"""The EDIT review on Telegram - one short version at a time (Colden 2026-10-02, Q9: one tap approves the cut AND picks
the destination; the copy + covers come later as ONE batch card).
  tg_review.py send <WORK> <id> [--note "<what is still missing>"] [--dry-run]
        the newest verified version's preview WITH its metadata (width / height / duration, streaming, a same-shape
        cover - Colden's global rule) and the buttons of the show's destinations + Changes. GATES: review.py check
        passed (decode gate included) and the contact sheet was LOOKED at (review.py ack, bound to its hash).
  tg_review.py ask-resolve <WORK> "<what will be built>"
        Resolve is Colden's working surface (a build switches the current timeline): a one-tap card Build now / Wait.
        Build only after "RESOLVE GO" lands in review/events.log.
Taps arrive through the CWC listener -> tg_router.py -> handle(). Approve -> versions.json `approved` + destination;
Changes -> his next message (or a reply to the video) is stored as that version's notes: fix, build the next version,
send again. Every decision -> data/shorts/decisions.jsonl. State: WORK/review/edits.json."""
import os, sys, json
import common as C, tg_api as TG
LAB = {'cwc': 'Create with Colden', 'tcl': 'The Creative Lens', 'both': 'both channels', 'todd': "Todd's channel (export only)"}
BTN = {'cwc': "✅ Create with Colden", 'tcl': '✅ Creative Lens', 'both': '✅ Both', 'todd': '✅ Todd only'}

def rpath(W): return f'{W}/review/edits.json'
def rstate(W): return C.load(rpath(W), {'items': {}, 'awaiting_notes': None, 'resolve': None})
def vpath(W, tid): return f'{W}/edit/{tid}/versions.json'
def set_v(W, tid, vn, **f):
    vs = C.load(vpath(W, tid), []); row = next(x for x in vs if x['v'] == vn); row.update(f); C.save(vpath(W, tid), vs); return row

def send(W, tid, note, dry):
    import review as R
    ep = C.episode(W); S = C.show(ep['show']); v = R.newest(W, tid); pc = v.get('preview_check') or {}; key = f'{tid}|v{v["v"]}'
    if not pc or pc.get('problems'): C.fail(f'{key}: review.py check has not passed ({pc.get("problems")})')
    if not v.get('looked') or v['looked'].get('sheet_sha') != C.sha_file(pc['sheet']): C.fail(f'{key}: the contact sheet has not been looked at - open {pc["sheet"]}, then review.py ack')
    th = next(t for t in C.load(f'{W}/themes.json')['themes'] if t['id'] == tid); k = C.epk(ep); dests = S['channels']['destinations']
    row = [{'text': BTN[d], 'callback_data': f'pr|{k}|e|{tid}|v{v["v"]}|{d}'} for d in dests]
    kb = {'inline_keyboard': [row[:2], row[2:] + [{'text': '✏️ Changes', 'callback_data': f'pr|{k}|e|{tid}|v{v["v"]}|chg'}]]}
    w, h, d = TG.probe(v['preview'])
    cap = f'📱 {ep["show_name"]} Ep {ep["ep_no"]} · {tid.upper()} v{v["v"]} · {d:.0f} s · suggested: {LAB.get(th["dest"], th["dest"])}\n{th["title"]}' + (f'\n{note}' if note else '')
    if dry: print(cap, [[b['text'] for b in r] for r in kb['inline_keyboard']], v['preview'], f'{w}x{h} {d:.1f}s'); return
    m, meta = TG.send_video(v['preview'], cap, kb)
    st = rstate(W); st['items'][key] = {'status': 'sent', 'message_id': m['message_id'], 'sent_at': C.now(), 'timeline': v['timeline'], 'notes': []}; C.save(rpath(W), st)
    set_v(W, tid, v['v'], sent_at=C.now()); C.event(W, f'SENT EDIT {key}: {v["timeline"]} ({meta[0]}x{meta[1]}, {meta[2]:.0f} s)')

def ask_resolve(W, what):
    k = C.epk(C.episode(W)); kb = {'inline_keyboard': [[{'text': '▶️ Build now', 'callback_data': f'pr|{k}|r|go'}, {'text': '⏸ Not now', 'callback_data': f'pr|{k}|r|wait'}]]}
    m = TG.api('sendMessage', chat_id=TG.chat(), text=f'🎛 Ready to build in Resolve: {what}\nIt switches the current timeline in TCL Show Edits for a few minutes. OK to take Resolve?', reply_markup=kb)
    st = rstate(W); st['resolve'] = {'status': 'asked', 'message_id': m['message_id'], 'what': what, 'at': C.now()}; C.save(rpath(W), st); C.event(W, f'ASKED RESOLVE: {what}')

def handle(W, u):
    st = rstate(W); ep = C.episode(W); k = C.epk(ep); q = u.get('callback_query'); msg = u.get('message'); ch = TG.chat()
    if q:
        p = (q.get('data') or '').split('|')
        if len(p) < 4 or p[0] != 'pr' or p[1] != k or (q.get('message') or {}).get('chat', {}).get('id') != ch: return False
        if p[2] == 'r' and st.get('resolve'):
            go = p[3] == 'go'; TG.relabel(st['resolve']['message_id'], '▶️ Building now' if go else '⏸ Waiting - tap again later'); TG.ack(q, 'Building' if go else 'OK, waiting')
            st['resolve'].update(status='go' if go else 'wait', answered_at=C.now()); C.save(rpath(W), st)
            if not go:                                      # a fresh card so he can say go later with one tap
                kb = {'inline_keyboard': [[{'text': '▶️ Build now', 'callback_data': f'pr|{k}|r|go'}]]}
                m = TG.api('sendMessage', chat_id=ch, text='Tap when Resolve is free:', reply_markup=kb); st = rstate(W); st['resolve']['message_id'] = m['message_id']; C.save(rpath(W), st)
            C.event(W, 'RESOLVE GO' if go else 'RESOLVE WAIT'); return True
        if p[2] != 'e' or len(p) != 6: return False
        key = f'{p[3]}|{p[4]}'; it = st['items'].get(key)
        if not it: return False
        act = p[5]; tid, vn = p[3], int(p[4][1:])
        if it['status'] == 'approved': TG.ack(q, 'Already approved.'); return True
        if act in LAB:
            TG.relabel(it['message_id'], f'✅ Approved for {LAB[act]}'); TG.ack(q, 'Approved')
            it.update(status='approved', destination=act, decided_at=C.now())
            if st.get('awaiting_notes') == key: st['awaiting_notes'] = None
            C.save(rpath(W), st); set_v(W, tid, vn, status='approved', destination=act, approved_at=C.now())
            C.decision(W, {'stage': 'edit', 'short': tid, 'version': vn, 'decision': f'approved:{act}'}); C.event(W, f'EDIT APPROVED {key} for {LAB[act]}')
        elif act == 'chg':
            TG.ack(q, 'Type your changes'); st['awaiting_notes'] = key; it['status'] = 'changes'; C.save(rpath(W), st)
            TG.say('✏️ What should change? One message.'); C.event(W, f'EDIT CHANGES requested {key}')
        else: TG.ack(q)
        return True
    if msg and msg.get('chat', {}).get('id') == ch and msg.get('text'):
        rid = (msg.get('reply_to_message') or {}).get('message_id')
        key = next((x for x, v in st['items'].items() if v.get('message_id') == rid), None) if rid else st.get('awaiting_notes')
        if not key: return False
        it = st['items'][key]; it.setdefault('notes', []).append({'at': C.now(), 'text': msg['text'], 'after_approval': it['status'] == 'approved'})
        if it['status'] != 'approved': it['status'] = 'changes'
        st['awaiting_notes'] = None; C.save(rpath(W), st)
        C.decision(W, {'stage': 'edit', 'short': key.split('|')[0], 'version': key.split('|')[1], 'decision': 'note-after-approval' if it['status'] == 'approved' else 'changes', 'notes': msg['text']})
        TG.say('Noted (it stays approved).' if it['status'] == 'approved' else 'Noted. I will fix it and send the next version.'); C.event(W, f'EDIT NOTES {key}: {msg["text"]}')
        return True
    return False

if __name__ == '__main__':
    a = [x for x in sys.argv[1:] if not x.startswith('--')]; dry = '--dry-run' in sys.argv
    note = sys.argv[sys.argv.index('--note') + 1] if '--note' in sys.argv else None
    if note in a: a.remove(note)
    if len(a) < 2: C.fail(__doc__)
    cmd, W = a[0], os.path.abspath(a[1])
    if cmd == 'send': send(W, a[2], note, dry)
    elif cmd == 'ask-resolve': ask_resolve(W, a[2])
    else: C.fail(__doc__)
