"""Theme approval on Telegram (@VideoEditReview_bot) - Colden 2026-10-01: one message per theme, at most 5; a killed
theme is answered with the next runner-up; fewer than 3 strong themes = a flag for manual review instead.

  tg_themes.py send   <WORK> [--dry-run]          check.py must pass first (it is run again here). Sends a one-line header
                                                  and ONE short message per theme: a tag line (n/N, length, suggested
                                                  channel), the title, the 1-2 sentence summary, the hook quote, with
                                                  Approve / Kill / Notes  buttons. Themes already sent are skipped.
  THE TAPS are answered by the always-on listener (tg_listen.py - it must be running; `send` refuses otherwise):
                                                  Approve -> approved. Kill -> killed, check.py is run again and the next
                                                  runner-up that still fits the 10 % overlap rule is sent. Notes -> his
                                                  next message (or any reply to a theme message) is stored as that
                                                  theme's notes: revise themes.json, cold-read again, check.py, then
                                                  `resend`. When every theme is approved or killed and no runner-up is
                                                  left: <WORK>/approved.json + a closing message.
  (tg_themes.py poll is a single-episode foreground loop kept for the self-test; it refuses while the listener runs.)
  tg_themes.py resend <WORK> <id> [--dry-run]     a revised theme, next round
  tg_themes.py flag   <WORK> [--dry-run]          the manual-review message when fewer than 3 themes pass
  tg_themes.py say    <WORK> "<text>"              a plain message (what changed, why cards are being sent again)
  tg_themes.py status <WORK>
Every decision is appended to data/decisions.jsonl with the theme's attributes (learn.py reads it).
State: <WORK>/review/state.json; everything that happens: <WORK>/review/events.log (watch it).
GATES: nothing is sent that check.py does not deliver; a TRIAL work is labelled TRIAL in every message; taps from any
chat but Colden's are ignored; a tap counts only on the theme's CURRENT card (matched by message id - a re-sent
theme strips the old card's buttons, and another show's episode with the same Ep key never claims it); every state
change is made under the shared lock on fresh state (common.update), after the tap was answered."""
import os, re, sys, json, time, socket, threading, subprocess, http.client, urllib.request, urllib.parse
import common as C, check as CK

def token():
    t = os.environ.get('TG_BOT_TOKEN')
    if not t and os.path.exists(os.path.expanduser('~/.zshrc')):
        for line in open(os.path.expanduser('~/.zshrc')):
            if line.startswith('export TG_BOT_TOKEN='): t = line.split('=', 1)[1].strip().strip('\'"')
    if not t: C.ask('TG_BOT_TOKEN is missing (~/.zshrc)')
    return t
def chat():
    for p in ('~/.config/cwc/telegram.json', '~/.config/edit-shorts/telegram.json'):
        p = os.path.expanduser(p)
        if os.path.exists(p): return json.load(open(p))['chat_id']
    C.ask('no Telegram pairing (~/.config/cwc/telegram.json or the edit-shorts one)')
class _V4(http.client.HTTPSConnection):
    """Telegram over IPv4 only, on a connection that is KEPT OPEN. Measured 2026-10-01 on Colden's Mac: with urllib
    (a new connection per call, IPv6 or IPv4 as the resolver alternates) every second call sat for the whole timeout
    before it fell back - his Approve tap took 22-31 s to show. IPv4 + keep-alive: about 0.1 s a call."""
    def connect(self):
        ip = socket.getaddrinfo(self.host, self.port, socket.AF_INET, socket.SOCK_STREAM)[0][4][0]
        self.sock = self._context.wrap_socket(socket.create_connection((ip, self.port), self.timeout), server_hostname=self.host)
_conn = threading.local()
def api(method, _http=None, **params):
    """one Bot API call. Action calls: 6 s timeout, one retry on a fresh connection. getUpdates: its own connection."""
    kind = 'poll' if method == 'getUpdates' else 'act'; timeout = _http or (6 if kind == 'act' else 20)
    body = urllib.parse.urlencode({k: (json.dumps(v) if isinstance(v, (dict, list)) else v) for k, v in params.items()})
    for attempt in (1, 2):
        c = getattr(_conn, kind, None)
        try:
            if c is None: c = _V4('api.telegram.org', 443, timeout=timeout); setattr(_conn, kind, c)
            if c.sock is not None: c.sock.settimeout(timeout)
            c.request('POST', f'/bot{token()}/{method}', body=body, headers={'Content-Type': 'application/x-www-form-urlencoded', 'Connection': 'keep-alive'})
            r = json.loads(c.getresponse().read())
            if not r.get('ok'): raise RuntimeError(f'{method}: {r}')
            return r['result']
        except RuntimeError: raise
        except Exception:
            try: c.close()
            except Exception: pass
            setattr(_conn, kind, None)
            if attempt == 2 or kind == 'poll': raise

def both(*fns):
    """the tap's two visible answers, in order, on the kept connection (about 0.13 s each - measured; fresh threads
    would each pay a new TLS handshake, 0.5 s)"""
    for f in fns: f()

def spath(W): return f'{W}/review/state.json'
DEF = {'themes': {}, 'offset': None, 'header': False}
def state(W): return C.load(spath(W), dict(DEF, themes={}))
def put(W, fn):
    """change the state under the shared lock, on what is on disk NOW (never on a copy read before a network call)"""
    return C.update(spath(W), fn, dict(DEF, themes={}))
def strip(mid, text):
    try: api('editMessageReplyMarkup', chat_id=chat(), message_id=mid, reply_markup={'inline_keyboard': [[{'text': text, 'callback_data': 'noop'}]]})
    except Exception: pass
def event(W, line):
    os.makedirs(f'{W}/review', exist_ok=True)
    with open(f'{W}/review/events.log', 'a') as f: f.write(f'{C.now()} {line}\n')
    print(line, flush=True)
def decide(W, ck, tid, decision, notes=None, rnd=1):
    r = ck['themes'][tid]; os.makedirs(C.DATA, exist_ok=True)
    row = {'at': C.now(), 'show': ck['episode']['show'], 'ep': ck['episode']['ep_key'], 'trial': bool(ck.get('trial')), 'theme': tid, 'title': r['title'], 'decision': decision, 'notes': notes, 'round': rnd,
           'attrs': {'total': r['total'], 'scores': r['scores'], 'est_seconds': r['est_seconds'], 'midroll': r['midroll'], 'news': r['news'], 'speakers': r['speakers'],
                     'ranges': r['ranges'], 'nonlinear': r['nonlinear'], 'jumps': r['jumps'], 'has_share': bool(r['shares']), 'hook_who': r['hook']['who'], 'hook_seconds': r['hook']['seconds']}}
    with open(f'{C.DATA}/decisions.jsonl', 'a') as f: f.write(json.dumps(row, ensure_ascii=False) + '\n')

def text_for(ck, tid, pos, total, label='', held=False):
    """the card. Colden 2026-10-01: "telegram cards are WAY too long for review. I know what I talked about on my show.
    Give me 25% of what you sent me per theme. Title, description, hook. good enough to move or kill" -> one tag line,
    the title, the 1-2 sentence summary, the hook quote. Everything else (payoff, evidence, thumbnail, scores, cold
    read) stays in checked.json and themes.json. GATE: selftest_tg.py fails a card over 600 characters."""
    r = ck['themes'][tid]; trial = 'TRIAL · ' if ck.get('trial') else ''
    tag = [label or f'{pos}/{total}', C.mmss(r['est_seconds'])]
    if r.get('suggest'): tag.append('for ' + r['suggest']['label'])
    if held: tag.append('HELD')
    q = r['hook']['quote'].strip(); q = q if len(q) <= 220 else q[:217] + '...'
    return f'{trial}🎬 {" · ".join(tag)}\n{r["title"]}\n\n{r["summary"]}\n\nHOOK ({r["hook"]["who"]}): "{q}"'

def keyboard(ep_key, tid):
    return {'inline_keyboard': [[{'text': '✅ Approve', 'callback_data': f'pc|{ep_key}|ok|{tid}'}, {'text': '❌ Kill', 'callback_data': f'pc|{ep_key}|kill|{tid}'}, {'text': '✏️ Notes', 'callback_data': f'pc|{ep_key}|notes|{tid}'}]]}

def checked(W):
    code, ck = CK.run(W)
    if ck is None: C.fail('check.py has structural errors - nothing is sent')
    return code, ck

def send(W, dry, only=None, label=''):
    code, ck = checked(W)
    blocks = [b for b in ck['blocks'] if not (only and b == 'too_few')]      # a revised theme may go back while the set is short
    if blocks: C.fail(f'check.py is blocked by {blocks} - nothing is sent (see its message; fewer than 3 themes -> tg_themes.py flag)')
    st = state(W); ch = chat(); ep = ck['episode']; todo = [t for t in ck['deliver'] if (only and t == only) or (not only and t not in st['themes'])]
    if only and only not in ck['deliver']: C.fail(f'{only} is not deliverable: {[h["why"] for h in ck["held"] if h["id"] == only]}')
    if not st['header'] and not only:
        head = f'{"TRIAL · " if ck.get("trial") else ""}🎞 {ep["label"]}: {len(ck["deliver"])} clip themes' + (' (softened: fewer than 3 reached the strong line)' if ck.get('softened') else '') + '. Approve / Kill / Notes on each.'
        if dry: print(head + '\n' + '=' * 60)
        else: api('sendMessage', chat_id=ch, text=head); put(W, lambda s: s.update(header=True))
    for t in todo:
        old = state(W)['themes'].get(t, {}); pos = ck['deliver'].index(t) + 1; rnd = old.get('round', 0) + 1
        txt = text_for(ck, t, pos, len(ck['deliver']), label or (f'{pos}/{len(ck["deliver"])} · round {rnd}' if rnd > 1 else ''))
        if dry: print(txt + '\n[ ✅ Approve ] [ ❌ Kill ] [ ✏️ Notes ]\n' + '=' * 60); continue
        m = api('sendMessage', chat_id=ch, text=txt, reply_markup=keyboard(ep['ep_key'], t))
        if old.get('message_id'): strip(old['message_id'], f'Revised - see round {rnd} below')
        def mut(s, t=t, m=m, rnd=rnd):
            o = s['themes'].get(t, {})
            s['themes'][t] = {'status': 'sent', 'message_id': m['message_id'], 'old_message_ids': o.get('old_message_ids', []) + ([o['message_id']] if o.get('message_id') else []), 'round': rnd, 'sent_at': C.now(),
                              'text_sha': ck['themes'][t]['text_sha'], 'notes': o.get('notes', []), 'manual': False}
            if s.get('settled'): s['settled'] = None; s['reopened'] = True     # an open card again: approved.json is rewritten when it closes
        put(W, mut); event(W, f'SENT {t} round {rnd}: {ck["themes"][t]["title"]}')
    if not todo: print('nothing new to send')

def flag(W, dry):
    """fewer than 3 themes pass: the manual-review message, then ONE card per held theme (best first, 5 at most) so
    Colden can make the manual call he said he would - Approve on a held card is his override and is logged as such"""
    code, ck = checked(W); ep = ck['episode']; ok = [ck['themes'][t] for t in ck['deliver']]
    if 'too_few' not in ck['blocks']: C.fail('enough themes pass - use tg_themes.py send')
    if [b for b in ck['blocks'] if b != 'too_few']: C.fail(f'check.py is blocked by {ck["blocks"]} - nothing is sent')
    held = sorted([r for r in ck['themes'].values() if r['hold'] and r.get('cold') and r['id'] not in ck['deliver']], key=lambda r: -r['total'])[:5]
    trial = 'TRIAL - ' if ck.get('trial') else ''
    L = [f'{trial}⚠️ {ep["label"]}: only {len(ok)} theme(s) strong enough (minimum 3). Not padded.']
    if ck.get('episode_note'): L.append(ck['episode_note'][:300])
    L.append(f'{len(held)} held theme(s) follow. Approve = make it anyway.')
    txt = '\n'.join(L)[:4000]; st = state(W); ch = chat() if not dry else None
    if dry: print(txt + '\n' + '=' * 60)
    elif not st.get('flagged_at'):
        api('sendMessage', chat_id=ch, text=txt); put(W, lambda s: s.update(flagged_at=C.now(), header=True)); event(W, f'FLAG sent: {len(ok)} passing, {len(held)} held cards')
    for i, r in enumerate(ok + held):
        t = r['id']; is_held = r in held
        if t in state(W)['themes']: continue
        body = text_for(ck, t, i + 1, len(ok) + len(held), f'{i + 1}/{len(ok) + len(held)}', held=is_held)
        if dry: print(body + '\n[ ✅ Approve ] [ ❌ Kill ] [ ✏️ Notes ]\n' + '=' * 60); continue
        m = api('sendMessage', chat_id=ch, text=body, reply_markup=keyboard(ep['ep_key'], t))
        def mut(s, t=t, m=m, r=r, is_held=is_held):
            if s.get('settled'): s['settled'] = None; s['reopened'] = True
            s['themes'][t] = {'status': 'sent', 'message_id': m['message_id'], 'round': 1, 'sent_at': C.now(), 'text_sha': r['text_sha'], 'notes': [], 'manual': is_held}
        put(W, mut); event(W, f'SENT {"held " if is_held else ""}{t}: {r["title"]}')

def others_polling():
    r = subprocess.run(['pgrep', '-fl', 'tg_review.py|tg_themes.py|tg_edit.py|tg_listen.py'], capture_output=True, text=True).stdout.splitlines()
    return [l for l in r if str(os.getpid()) != l.split()[0] and re.search(r'[Pp]ython\S* \S*(tg_review|tg_themes|tg_edit)\.py poll|[Pp]ython\S* \S*tg_listen\.py', l)]

def finish(W, st, ck):
    open_ = [t for t, v in st['themes'].items() if v['status'] in ('sent', 'notes')]
    if open_: return False
    ap = [t for t in ck['deliver'] if st['themes'].get(t, {}).get('status') == 'approved'] + [t for t, v in st['themes'].items() if v['status'] == 'approved' and t not in ck['deliver']]
    old = C.load(f'{W}/approved.json') or {}
    C.save(f'{W}/approved.json', {'at': C.now(), 'episode': ck['episode'], 'trial': ck.get('trial'), 'approved': [{'id': t, 'title': ck['themes'][t]['title'], 'slug': ck['themes'][t]['slug'], 'text_sha': st['themes'][t]['text_sha'], 'manual_override': bool(st['themes'][t].get('manual')), 'held_for': ck['themes'][t]['hold'] if st['themes'][t].get('manual') else []} for t in ap if t not in {d['id'] for d in old.get('dropped', [])}],
                                  'killed': [t for t, v in st['themes'].items() if v['status'] == 'killed'], 'dropped': old.get('dropped', [])})
    api('sendMessage', chat_id=chat(), text=f'🔒 {ck["episode"]["label"]} themes settled: {len(ap)} approved.\n' + '\n'.join(f'  {i + 1}. {ck["themes"][t]["title"]}' for i, t in enumerate(ap)))
    event(W, f'DONE approved={ap}'); return True

def handle(W, u):
    """one Telegram update against this episode's THEME cards -> True when it was ours (tg_listen.py routes by this)"""
    st = state(W); ck = C.load(f'{W}/checked.json')
    if not ck or not st['themes']: return False
    ch = chat(); ep_key = ck['episode']['ep_key']; q = u.get('callback_query'); msg = u.get('message')
    if q:
        parts = q.get('data', '').split('|'); mid = (q.get('message') or {}).get('message_id')
        if (q.get('message') or {}).get('chat', {}).get('id') != ch or len(parts) != 4 or parts[0] != 'pc' or parts[1] != ep_key or parts[3] not in st['themes']: return False
        act, tid = parts[2], parts[3]; th = st['themes'][tid]; title = ck['themes'][tid]['title']
        if mid not in [th.get('message_id')] + th.get('old_message_ids', []): return False       # another show's episode with the same Ep key
        def ack(t):
            try: api('answerCallbackQuery', callback_query_id=q['id'], text=t)
            except Exception: pass
        if mid != th.get('message_id'): ack('This card was revised - use the newest one.'); strip(mid, 'Revised - see the newer card'); return True
        if th['status'] in ('approved', 'killed') and act in ('ok', 'kill'): ack(f'Already {th["status"]}.'); return True
        def mark(t):
            try: api('editMessageReplyMarkup', chat_id=ch, message_id=mid, reply_markup={'inline_keyboard': [[{'text': t, 'callback_data': 'noop'}]]})
            except Exception: pass
        if act == 'ok':                                   # the tap is answered and the button re-labelled BEFORE any bookkeeping
            both(lambda: mark('✅ Approved'), lambda: ack('Approved')); put(W, lambda s: s['themes'][tid].update(status='approved', decided_at=C.now())); C.clear_awaiting('theme', W, tid)
            decide(W, ck, tid, 'approved-manual' if th.get('manual') else 'approved', rnd=th['round']); event(W, f'APPROVED{" (manual override of a held theme)" if th.get("manual") else ""} {tid}: {title}')
        elif act == 'kill':
            both(lambda: mark('❌ Killed'), lambda: ack('Killed')); put(W, lambda s: s['themes'][tid].update(status='killed', decided_at=C.now())); C.clear_awaiting('theme', W, tid)
            decide(W, ck, tid, 'killed', rnd=th['round']); event(W, f'KILLED {tid}: {title}')
            code, ck2 = CK.run(W, fresh=False)              # not the 36 h data gate: the set was checked fresh when it was sent
            if ck2 is None: api('sendMessage', chat_id=ch, text='(I cannot offer a runner-up right now - the theme file needs a fix on my side.)'); event(W, 'RUNNER-UP blocked: structural errors (check.py prints them; the PodCut lock may have changed)')
            else:
                ck = ck2; now = state(W); new = [t for t in ck['deliver'] if t not in now['themes']]
                if new:
                    t = new[0]; m = api('sendMessage', chat_id=ch, text=text_for(ck, t, 0, 0, 'RUNNER-UP'), reply_markup=keyboard(ep_key, t))
                    put(W, lambda s: s['themes'].__setitem__(t, {'status': 'sent', 'message_id': m['message_id'], 'round': 1, 'sent_at': C.now(), 'text_sha': ck['themes'][t]['text_sha'], 'notes': [], 'replaces': tid})); event(W, f'SENT runner-up {t} for {tid}: {ck["themes"][t]["title"]}')
                elif not now.get('flagged_at'):
                    api('sendMessage', chat_id=ch, text=f'No runner-up passes the gates (score, cold read, 10 % overlap). {sum(1 for v in now["themes"].values() if v["status"] != "killed")} theme(s) stand.'); event(W, f'NO runner-up for {tid}')
        elif act == 'notes':
            ack('Type your notes'); C.set_awaiting('theme', W, tid); api('sendMessage', chat_id=ch, text=f'✏️ Notes for "{title[:60]}": send them as one message.'); event(W, f'NOTES requested {tid}')
        else: ack('')
        return True
    if msg and msg.get('chat', {}).get('id') == ch and msg.get('text'):
        rid = (msg.get('reply_to_message') or {}).get('message_id')
        tid = next((t for t, v in st['themes'].items() if rid in [v.get('message_id')] + v.get('old_message_ids', [])), None) if rid else C.awaiting('theme', W)   # a reply to another message is not ours
        if not tid or tid not in st['themes']: return False
        was = st['themes'][tid]['status']; rnd = st['themes'][tid]['round']
        def mut(s):
            th = s['themes'][tid]; th.setdefault('notes', []).append({'at': C.now(), 'text': msg['text']})
            if th['status'] == 'approved': th['notes'][-1]['after_approval'] = True      # a note on an approved theme is logged; it never un-approves it
            elif th['status'] != 'killed': th['status'] = 'notes'
        put(W, mut); C.clear_awaiting('theme', W, tid)
        if was == 'approved':
            decide(W, ck, tid, 'note-after-approval', notes=msg['text'], rnd=rnd); api('sendMessage', chat_id=ch, text=f'Noted for "{ck["themes"][tid]["title"][:50]}" (it stays approved).'); event(W, f'NOTE after approval {tid}: {msg["text"]}'); return True
        decide(W, ck, tid, 'notes' if was != 'killed' else 'kill-reason', notes=msg['text'], rnd=rnd)
        api('sendMessage', chat_id=ch, text=f'Noted for "{ck["themes"][tid]["title"][:50]}".' + (' I will revise it and send it again.' if was != 'killed' else '')); event(W, f'NOTES {tid}: {msg["text"]}')
        return True
    return False

def settle(W):
    """every theme approved or killed -> approved.json + the closing message, once. True when settled."""
    st = state(W); ck = C.load(f'{W}/checked.json')
    if not st['themes'] or st.get('settled') or not ck: return bool(st.get('settled'))
    if os.path.exists(f'{W}/approved.json') and not st.get('reopened') and not any(v['status'] in ('sent', 'notes') for v in st['themes'].values()):
        put(W, lambda s: s.update(settled=C.now())); return True          # settled by an earlier run: never announce twice, never rewrite approved.json
    if finish(W, st, ck):
        put(W, lambda s: s.update(settled=C.now(), reopened=None)); return True
    return False

def poll(W, max_seconds):
    """a single-episode foreground loop (the self-test's driver). In real runs the taps are answered by tg_listen.py."""
    oth = others_polling()
    if oth: C.ask(f'the always-on listener (or another poller) is running on this bot: {oth}. It answers the taps - do not poll.')
    st = state(W); t0 = time.time()
    if not st['themes']: C.fail('nothing was sent yet (tg_themes.py send)')
    event(W, f'POLL start ({sum(1 for v in st["themes"].values() if v["status"] == "sent")} open)')
    while True:
        if max_seconds and time.time() - t0 > max_seconds: event(W, 'POLL stop (max seconds)'); return 0
        st = state(W)
        try: ups = api('getUpdates', 20, **dict({'timeout': 10}, **({'offset': st['offset']} if st['offset'] else {})))
        except Exception as e: event(W, f'POLL network: {str(e)[:100]}'); time.sleep(5); continue
        for u in ups:
            put(W, lambda s: s.update(offset=u['update_id'] + 1))
            if not handle(W, u):
                d = (u.get('callback_query') or {}).get('data') or ((u.get('message') or {}).get('text') or '')[:200]; event(W, f'FOREIGN / unrouted update ignored: {d[:80]}')
            if settle(W): return 0

if __name__ == '__main__':
    a = [x for x in sys.argv[1:] if not x.startswith('--')]; dry = '--dry-run' in sys.argv
    if len(a) < 2: C.fail(__doc__)
    cmd, W = a[0], os.path.abspath(a[1])
    if cmd in ('send', 'resend', 'flag') and not dry: C.need_listener()
    if cmd == 'send': send(W, dry)
    elif cmd == 'resend': send(W, dry, only=a[2])
    elif cmd == 'say':
        if dry: print(a[2])
        else: api('sendMessage', chat_id=chat(), text=a[2][:4000]); event(W, f'SAID: {a[2][:200]}')
    elif cmd == 'flag': flag(W, dry)
    elif cmd == 'poll': sys.exit(poll(W, int(sys.argv[sys.argv.index('--max-seconds') + 1]) if '--max-seconds' in sys.argv else 0))
    elif cmd == 'status':
        st = state(W); print(json.dumps({t: {k: v[k] for k in ('status', 'round') if k in v} for t, v in st['themes'].items()}, indent=1), 'awaiting notes:', C.awaiting('theme', W))
    else: C.fail(__doc__)
