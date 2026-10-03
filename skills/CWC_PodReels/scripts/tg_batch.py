"""tg_batch.py - covers + copy on Telegram, ONE CARD PER SHORT, one at a time (Colden 2026-10-02: "The delivery system for
thumbnails is very confusing. Go one at a time same way /CWC_PodClips does" - the single batch card is retired).
  tg_batch.py send <WORK> [<id>]
        the card of <id>, or of the next short still waiting: ONE photo (cover.py pair: cover 1 = the frame from the short
        with its hook, made in Resolve | cover 2 = the AI cover, big numbered badges) + that short's copy in the caption
        (YouTube title, caption + hashtags, pinned comment, IG collaborator) and the buttons [Cover 1] [Cover 2] [Notes].
        GATES: both covers on disk, the copy passes postcopy.py check.
  tg_batch.py status <WORK>
Taps (CWC listener -> tg_router.py): Cover 1 / 2 = this short's cover AND copy approved (copy.json status approved +
cover) -> the card closes ("✅ Cover 2 - S01 done") and the NEXT short's card is sent by the handler itself; after the
last one "BATCH APPROVED" lands in events.log. Notes -> his next message (or a reply to the card) is stored as that
short's notes ("PACKAGE NOTES s01: ...") -> fix, `tg_batch.py send <WORK> s01` again (the old card retires). A tap on a
retired card changes nothing. Every decision -> data/shorts/decisions.jsonl. State: WORK/review/batch.json."""
import os, sys, json, subprocess
import common as C, tg_api as TG
HERE = os.path.dirname(os.path.abspath(__file__)); LAB = {'cwc': 'Create with Colden', 'tcl': 'The Creative Lens'}
def bpath(W): return f'{W}/review/batch.json'
def bstate(W):
    st = C.load(bpath(W), {}) or {}
    if st.get('mode') != 'per_short':                               # the retired single batch card (2026-10-02): keep its id to strip it
        st = {'mode': 'per_short', 'items': {}, 'retired_batch_message_id': st.get('message_id')}
    return st
def order(W):
    cp = (C.load(f'{W}/copy.json') or {}).get('shorts', {}); rank = (C.load(f'{W}/checked.json') or {}).get('deliver', [])
    return [s for s in rank + [x for x in cp if x not in rank] if s in cp and cp[s].get('brands')]

def send(W, sid=None):
    st = bstate(W)
    if st.get('retired_batch_message_id'): TG.relabel(st.pop('retired_batch_message_id'), 'Replaced: one card per short follows')
    todo = [s for s in order(W) if st['items'].get(s, {}).get('status') != 'approved']
    sid = sid or next((s for s in todo if st['items'].get(s, {}).get('status') != 'sent'), None)
    if not sid: print('every short is decided'); C.save(bpath(W), st); return None
    r = subprocess.run([sys.executable, f'{HERE}/postcopy.py', 'check', W], capture_output=True, text=True)
    if r.returncode != 0: C.fail(f'the copy does not pass its gates:\n{r.stdout}')
    cv = C.load(f'{W}/edit/{sid}/cover.json', {}) or {}; c = C.load(f'{W}/copy.json')['shorts'][sid]
    if not (cv.get('resolve_cover') and (cv.get('ai') or {}).get('file') and cv.get('pair') and os.path.exists(cv['pair'])): C.fail(f'{sid}: covers missing (cover.py resolve + add + pair)')
    ep = C.episode(W); k = C.epk(ep); n, tot = order(W).index(sid) + 1, len(order(W))
    cap = (f'🎨 {ep["show_name"]} Ep {ep["ep_no"]} · {sid.upper()} ({n}/{tot}) → {" + ".join(LAB[b] for b in c["brands"])}\n'
           f'YT: {c["yt_title"]}\n\n{c["caption"]}\n\n💬 {c["first_comment"]}' + (f'\n🤝 IG collab: @{c["ig_collab"]}' if c.get('ig_collab') not in (None, 'none') else '') +
           '\n\nPick the cover - it approves the copy too.')
    kb = {'inline_keyboard': [[{'text': 'Cover 1', 'callback_data': f'pr|{k}|b|{sid}|1'}, {'text': 'Cover 2', 'callback_data': f'pr|{k}|b|{sid}|2'}],
                              [{'text': '✏️ Notes', 'callback_data': f'pr|{k}|b|{sid}|n'}]]}
    old = st['items'].get(sid, {})
    m = TG.send_photo(cv['pair'], cap, kb)
    if old.get('message_id'): TG.relabel(old['message_id'], 'Replaced by a newer card')
    st = bstate(W); st['items'][sid] = {'status': 'sent', 'message_id': m['message_id'], 'sent_at': C.now(), 'notes': old.get('notes', []), 'old_message_ids': old.get('old_message_ids', []) + ([old['message_id']] if old.get('message_id') else [])}
    C.save(bpath(W), st); C.event(W, f'SENT PACKAGE {sid} ({n}/{tot})'); return sid

def handle(W, u):
    st = C.load(bpath(W), {}) or {}
    if st.get('mode') != 'per_short' or not st.get('items'): return False
    k = C.epk(C.episode(W)); q = u.get('callback_query'); msg = u.get('message'); ch = TG.chat()
    if q:
        p = (q.get('data') or '').split('|'); mid = (q.get('message') or {}).get('message_id')
        if len(p) != 5 or p[0] != 'pr' or p[1] != k or p[2] != 'b' or (q.get('message') or {}).get('chat', {}).get('id') != ch: return False
        sid, act = p[3], p[4]; it = st['items'].get(sid)
        if not it: return False
        if mid != it.get('message_id'): TG.ack(q, 'This card was replaced - use the newest one.'); TG.relabel(mid, 'Replaced by a newer card'); return True
        if it['status'] == 'approved': TG.ack(q, 'Already approved.'); return True
        if act in ('1', '2'):
            n = int(act); TG.relabel(mid, f'✅ Cover {n} - {sid.upper()} done'); TG.ack(q, f'Cover {n}')
            cv = C.load(f'{W}/edit/{sid}/cover.json', {}); cp = C.load(f'{W}/copy.json')
            cp['shorts'][sid].update(status='approved', cover=cv['resolve_cover'] if n == 1 else cv['ai']['file'], cover_kind='resolve' if n == 1 else 'ai'); C.save(f'{W}/copy.json', cp)
            st = C.load(bpath(W)); st['items'][sid].update(status='approved', pick=n, decided_at=C.now()); st['awaiting_notes'] = None; C.save(bpath(W), st)
            C.decision(W, {'stage': 'batch', 'short': sid, 'decision': f'cover:{n}'}); C.event(W, f'PACKAGE PICKED {sid}: cover {n} ({"resolve" if n == 1 else "ai"})')
            if all(st['items'].get(s, {}).get('status') == 'approved' for s in order(W)):
                C.event(W, 'BATCH APPROVED'); TG.say('✅ Covers + copy approved for every short. The posting calendar comes next.')
            else:
                try: send(W)                                        # one at a time: the next short's card right away
                except SystemExit as e: TG.say(f'⚠️ The next card could not be sent ({e}) - I will fix it.'); C.event(W, f'NEXT PACKAGE FAILED: {e}')
            return True
        if act == 'n':
            TG.ack(q, 'Type your notes'); st['awaiting_notes'] = sid; it['status'] = 'changes'; C.save(bpath(W), st)
            TG.say(f'✏️ What should change on {sid.upper()} (cover or copy)? One message.'); C.event(W, f'PACKAGE NOTES requested {sid}'); return True
        TG.ack(q); return True
    if msg and msg.get('chat', {}).get('id') == ch and msg.get('text'):
        rid = (msg.get('reply_to_message') or {}).get('message_id')
        sid = next((s for s, v in st['items'].items() if rid and rid in [v.get('message_id')] + v.get('old_message_ids', [])), None) or st.get('awaiting_notes')
        if not sid or sid not in st['items']: return False
        st['items'][sid].setdefault('notes', []).append({'at': C.now(), 'text': msg['text']}); st['items'][sid]['status'] = 'changes'; st['awaiting_notes'] = None; C.save(bpath(W), st)
        C.decision(W, {'stage': 'batch', 'short': sid, 'decision': 'notes', 'notes': msg['text']}); TG.say(f'Noted for {sid.upper()}. I will fix it and send its card again.'); C.event(W, f'PACKAGE NOTES {sid}: {msg["text"]}')
        return True
    return False

def status(W):
    st = bstate(W)
    for s in order(W): it = st['items'].get(s, {}); print(s, it.get('status', 'waiting'), f'cover {it.get("pick")}' if it.get('pick') else '', it.get('notes', [])[-1:] if it.get('notes') else '')

if __name__ == '__main__':
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    if len(a) < 2: C.fail(__doc__)
    W = os.path.abspath(a[1])
    if a[0] == 'send': send(W, a[2] if len(a) > 2 else None)
    elif a[0] == 'status': status(W)
    else: C.fail(__doc__)
