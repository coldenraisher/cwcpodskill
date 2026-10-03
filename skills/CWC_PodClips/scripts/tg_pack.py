"""The PACKAGE review on Telegram (@VideoEditReview_bot) - short cards (ruling 22), one per clip upload.
  tg_pack.py send <WORK> <id> <ch>        card 1: the 2x2 grid of thumbnail options 1-4 + the three title options;
                                          buttons  [Title 1][Title 2][Title 3] / [Thumb 1]..[Thumb 4] / [Notes]. When a
                                          title AND a thumbnail are picked the card closes ("Title 2 + thumb 3"): that
                                          is A. Then Claude writes titles B and C (package.py check) and thumbnails B
                                          and C (thumbs.py), and:
  tg_pack.py send-abc <WORK> <id> <ch>    card 2: A / B / C side by side with the three titles; [Approve A/B/C][Notes]
  tg_pack.py status <WORK>
The always-on listener (tg_listen.py) answers the taps: the tap is answered FIRST, then the state is re-read and
changed under the shared lock (common.update) - never the copy read before the network calls.
State: WORK/package/review.json. The pick is written into copy.<ch>.json ("A") and thumbs.<ch>.json ("pick").
GATES  a card goes out only while the listener runs; card 1 only with package.py check clean and 4 options on disk;
card 2 only with A/B/C passing the gates, 3 different thumbnail files, and thumbnail C made for the CURRENT title C.
A tap counts only on the item's CURRENT card (matched by message id): re-sending a card strips the old one's buttons,
and a tap on an old card answers "replaced" and changes nothing. Re-sending card 1 voids the old pick, B / C and any
A/B/C approval. A note after an approval re-opens the set (package.py build refuses until it is approved again)."""
import os, sys, json
import common as C, tg_themes as G, tg_edit as E, package as PK, thumbs as TH

def rpath(W): return f'{W}/package/review.json'
def rstate(W): return C.load(rpath(W), {'items': {}})
def label(W, tid, ch):
    ck = C.load(f'{W}/checked.json'); S = C.show(C.episode(W)['show']); return f'{ck["episode"]["label"]} · C{tid[1:]} · ' + S['channels']['labels'].get(ch, ch)
def kb_pick(ep, key, it):
    t = it.get('title_pick'); h = it.get('thumb_pick'); tid, ch = key.split('|')
    return {'inline_keyboard': [[{'text': ('✅ ' if t == i else '') + f'Title {i + 1}', 'callback_data': f'pk|{ep}|{tid}|{ch}|t|{i}'} for i in range(3)],
                                [{'text': ('✅ ' if h == i else '') + f'Thumb {i + 1}', 'callback_data': f'pk|{ep}|{tid}|{ch}|h|{i}'} for i in range(4)],
                                [{'text': '✏️ Notes', 'callback_data': f'pk|{ep}|{tid}|{ch}|n|0'}]]}
def strip(mid, text):
    """an old card keeps its picture and loses its buttons"""
    try: G.api('editMessageReplyMarkup', chat_id=G.chat(), message_id=mid, reply_markup={'inline_keyboard': [[{'text': text, 'callback_data': 'noop'}]]})
    except Exception: pass
def item(W, key): return rstate(W)['items'].get(key)

def send(W, tid, ch):
    ep = C.episode(W); key = f'{tid}|{ch}'; probs = PK.check_one(W, tid, ch)
    if probs: C.fail(f'{key}: package.py check is not clean: {probs}')
    R = TH.rec(W, tid, ch); g = R.get('grid')
    if not g or not os.path.exists(g) or len(R.get('options') or []) != 4 or not all(os.path.exists(f) for f in R['options']): C.fail(f'{key}: no 4-option grid (thumbs.py grid)')
    old = item(W, key) or {}
    cp = C.load(f'{W}/package/{tid}/copy.{ch}.json')
    cap = f'🎨 {label(W, tid, ch)}\n' + '\n'.join(f'{i + 1}. {t}' for i, t in enumerate(cp['titles'])) + '\nPick a title and a thumbnail.'
    m = E.multipart('sendPhoto', {'chat_id': G.chat(), 'caption': cap[:1000], 'reply_markup': json.dumps(kb_pick(ep['ep_key'], key, {}))}, [('photo', g)])
    for mid in (old.get('message_id'), old.get('abc_message_id')):
        if mid: strip(mid, 'Replaced by a newer card')
    def mut(st):
        o = st['items'].get(key, {}); olds = o.get('old_message_ids', []) + [x for x in (o.get('message_id'), o.get('abc_message_id')) if x]
        st['items'][key] = {'status': 'sent', 'message_id': m['message_id'], 'sent_at': C.now(), 'title_pick': None, 'thumb_pick': None, 'notes': o.get('notes', []), 'old_message_ids': olds, 'round': o.get('round', 0) + 1}
    C.update(rpath(W), mut, {'items': {}})
    if old:                                               # a new card 1 voids the earlier pick and everything built on it
        C.update(f'{W}/package/{tid}/copy.{ch}.json', lambda c: [c.pop(k, None) for k in ('A', 'B', 'C')] and None)
        def tm(r): r['pick'] = None; r['abc'] = {}; r.pop('abc_grid', None); (r.get('ai') or {}).pop('C', None)
        C.update(TH.paths(W, tid, ch)[1], tm, {})
    G.event(W, f'SENT PACKAGE {key}' + (' (again: earlier pick and A/B/C voided)' if old else ''))

def send_abc(W, tid, ch):
    ep = C.episode(W); key = f'{tid}|{ch}'; it = item(W, key) or {}
    if it.get('status') != 'picked': C.fail(f'{key}: no title + thumbnail pick yet (card 1: {it.get("status") or "not sent"})')
    probs = PK.check_one(W, tid, ch, final=True)
    if probs: C.fail(f'{key}: A/B/C copy not clean: {probs}')
    R = TH.rec(W, tid, ch); g = R.get('abc_grid'); abc = R.get('abc') or {}; cp = C.load(f'{W}/package/{tid}/copy.{ch}.json')
    if not g or not all(os.path.exists(abc.get(k, '')) for k in 'ABC'): C.fail(f'{key}: A/B/C thumbnails incomplete (thumbs.py abc)')
    if len({C.sha_file(abc[k]) for k in 'ABC'}) != 3: C.fail(f'{key}: two of the A/B/C thumbnails are the same picture')
    cfor = ((R.get('ai') or {}).get('C') or {}).get('for_title')
    if cfor != cp['C']: C.fail(f'{key}: thumbnail C was made for the title "{cfor}", title C is now "{cp["C"]}" - regenerate it (thumbs.py prompt --title, add ... C)')
    cap = f'🅰️🅱️©️ {label(W, tid, ch)} - the YouTube test set\nA: {cp["A"]}\nB: {cp["B"]}\nC: {cp["C"]}'
    kb = {'inline_keyboard': [[{'text': '✅ Approve A/B/C', 'callback_data': f'pk|{ep["ep_key"]}|{tid}|{ch}|a|1'}, {'text': '✏️ Notes', 'callback_data': f'pk|{ep["ep_key"]}|{tid}|{ch}|n|1'}]]}
    m = E.multipart('sendPhoto', {'chat_id': G.chat(), 'caption': cap[:1000], 'reply_markup': json.dumps(kb)}, [('photo', g)])
    if it.get('abc_message_id'): strip(it['abc_message_id'], 'Replaced by a newer A/B/C card')
    def mut(st):
        o = st['items'][key]
        if o.get('abc_message_id'): o.setdefault('old_message_ids', []).append(o['abc_message_id'])
        o.update(abc='sent', abc_message_id=m['message_id'], abc_sent_at=C.now(), abc_sha={k: C.sha_file(abc[k]) for k in 'ABC'}, abc_titles=[cp['A'], cp['B'], cp['C']])
    C.update(rpath(W), mut); G.event(W, f'SENT A/B/C {key}')

def approved(W, tid, ch):
    """is the A/B/C set of this upload approved AS IT IS NOW (same titles, same three files)? -> (bool, why)"""
    it = item(W, f'{tid}|{ch}') or {}
    if it.get('abc') != 'approved': return False, f'the A/B/C set is not approved on Telegram ({it.get("abc") or it.get("status") or "not sent"})'
    cp = C.load(f'{W}/package/{tid}/copy.{ch}.json') or {}; abc = (TH.rec(W, tid, ch).get('abc') or {})
    if it.get('abc_titles') and it['abc_titles'] != [cp.get('A'), cp.get('B'), cp.get('C')]: return False, 'a title changed after the A/B/C approval - send-abc again'
    if it.get('abc_sha') and any(not os.path.exists(abc.get(k, '')) or C.sha_file(abc[k]) != it['abc_sha'][k] for k in 'ABC'): return False, 'a thumbnail changed after the A/B/C approval - send-abc again'
    return True, ''

def handle(W, u):
    """one Telegram update against this episode's PACKAGE cards -> True when it was ours"""
    st = rstate(W)
    if not st['items']: return False
    ep = C.episode(W); ch_id = G.chat(); q = u.get('callback_query'); msg = u.get('message'); rp = rpath(W)
    if q:
        p = q.get('data', '').split('|'); mid = (q.get('message') or {}).get('message_id')
        if (q.get('message') or {}).get('chat', {}).get('id') != ch_id or len(p) != 6 or p[0] != 'pk' or p[1] != ep['ep_key']: return False
        tid, ch, act, i = p[2], p[3], p[4], int(p[5]); key = f'{tid}|{ch}'; it = st['items'].get(key)
        if not it or mid not in [it.get('message_id'), it.get('abc_message_id')] + it.get('old_message_ids', []): return False     # not this episode's card (another show can have the same Ep key)
        def ack(t):
            try: G.api('answerCallbackQuery', callback_query_id=q['id'], text=t)
            except Exception: pass
        def markup(kb):
            try: G.api('editMessageReplyMarkup', chat_id=ch_id, message_id=mid, reply_markup=kb)
            except Exception: pass
        on_abc = act == 'a' or (act == 'n' and i == 1)
        if mid != (it.get('abc_message_id') if on_abc else it.get('message_id')):
            ack('This card was replaced - use the newest one.'); strip(mid, 'Replaced by a newer card'); return True
        if act in ('t', 'h'):
            if it.get('status') == 'picked': ack('Already picked.'); return True
            def mut(s):
                o = s['items'][key]; o['title_pick' if act == 't' else 'thumb_pick'] = i
                if o.get('title_pick') is not None and o.get('thumb_pick') is not None: o.update(status='picked', picked_at=C.now())
            now = C.update(rp, mut)['items'][key]
            if now.get('status') == 'picked':
                G.both(lambda: markup({'inline_keyboard': [[{'text': f'✅ Title {now["title_pick"] + 1} + thumb {now["thumb_pick"] + 1} - B/C next', 'callback_data': 'noop'}]]}), lambda: ack('Picked'))
                cp = C.update(f'{W}/package/{tid}/copy.{ch}.json', lambda c: c.update(A=c['titles'][now['title_pick']]))
                R = C.update(TH.paths(W, tid, ch)[1], lambda r: r.update(pick=now['thumb_pick']), {})
                C.clear_awaiting('pack', W, key)
                E.decide(W, f'{tid}|{ch}|package', f'picked:title{now["title_pick"] + 1}:thumb{now["thumb_pick"] + 1}:{(R.get("kinds") or [None] * 4)[now["thumb_pick"]]}', stage='package')
                G.event(W, f'PACKAGE PICKED {key}: title {now["title_pick"] + 1} "{cp["A"]}", thumb {now["thumb_pick"] + 1} ({(R.get("kinds") or [None] * 4)[now["thumb_pick"]]})')
            else:
                G.both(lambda: markup(kb_pick(ep['ep_key'], key, now)), lambda: ack(('Title' if act == 't' else 'Thumbnail') + f' {i + 1} - now the ' + ('thumbnail' if act == 't' else 'title')))
        elif act == 'a':
            if it.get('abc') == 'approved': ack('Already approved.'); return True
            if it.get('abc') != 'sent': ack('This set is being revised - a new card follows.'); return True
            G.both(lambda: markup({'inline_keyboard': [[{'text': '✅ A/B/C approved', 'callback_data': 'noop'}]]}), lambda: ack('Approved'))
            C.update(rp, lambda s: s['items'][key].update(abc='approved', abc_at=C.now())); C.clear_awaiting('pack', W, key)
            E.decide(W, f'{tid}|{ch}|package', 'abc-approved', stage='package'); G.event(W, f'PACKAGE A/B/C APPROVED {key}')
        elif act == 'n':
            ack('Type your notes'); C.set_awaiting('pack', W, key); G.api('sendMessage', chat_id=ch_id, text='✏️ Notes for this package? One message.'); G.event(W, f'PACKAGE NOTES requested {key}')
        else: ack('')
        return True
    if msg and msg.get('chat', {}).get('id') == ch_id and msg.get('text'):
        rid = (msg.get('reply_to_message') or {}).get('message_id')
        if rid:
            key = next((k for k, v in st['items'].items() if rid in [v.get('message_id'), v.get('abc_message_id')] + v.get('old_message_ids', [])), None)
        else: key = C.awaiting('pack', W)
        if not key or key not in st['items']: return False
        def mut(s):
            o = s['items'][key]; o.setdefault('notes', []).append({'at': C.now(), 'text': msg['text']})
            if o.get('abc') in ('sent', 'approved'): o['abc'] = 'notes'            # the set is open again: build refuses until it is approved again
            elif o.get('status') == 'sent': o['status'] = 'notes'
        C.update(rp, mut); C.clear_awaiting('pack', W, key)
        E.decide(W, f'{key}|package', 'notes', msg['text'], stage='package'); G.api('sendMessage', chat_id=ch_id, text='Noted. I will fix the package and send it again.'); G.event(W, f'PACKAGE NOTES {key}: {msg["text"]}')
        return True
    return False

if __name__ == '__main__':
    a = sys.argv[1:]
    if len(a) < 2: C.fail(__doc__)
    W = os.path.abspath(a[1])
    if a[0] in ('send', 'send-abc'): C.need_listener(); (send if a[0] == 'send' else send_abc)(W, a[2], a[3])
    elif a[0] == 'status': print(json.dumps(rstate(W)['items'], indent=1))
    else: C.fail(__doc__)
