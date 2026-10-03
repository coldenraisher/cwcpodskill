"""Theme cards on Telegram (Colden 2026-10-02 Q3: "A" - title + hook, Approve / Kill; build only what he approves).
  tg_cards.py send   <WORK> [--dry-run]      check.py is run again; a one-line header + ONE short card per delivered theme
                                              (tag line, title, on-screen hook, the opening line) with Approve / Kill / Notes
  tg_cards.py resend <WORK> <id> [--dry-run] a revised theme (after notes), next round
  tg_cards.py flag   <WORK> [--dry-run]      fewer than 5 deliverable: the manual-review line + the held cards (Approve = his override)
  tg_cards.py say    <WORK> "<text>"
  tg_cards.py status <WORK>
Taps arrive through CWC_PodClips' listener -> tg_router.py -> handle() here. Kill -> the next runner-up that still
passes; Notes -> his next message (or a reply to the card) is stored on the theme; when every card is approved or
killed: WORK/approved.json + a closing message + "THEMES SETTLED" in WORK/review/events.log (watch it).
Every decision -> data/shorts/decisions.jsonl. State: WORK/review/cards.json."""
import os, sys, json
import common as C, check as CK, tg_api as TG

def spath(W): return f'{W}/review/cards.json'
def state(W): return C.load(spath(W), {'themes': {}, 'awaiting_notes': None, 'header': False})
LAB = {'cwc': 'Create with Colden', 'tcl': 'The Creative Lens', 'both': 'both channels', 'todd': "Todd's channel"}

def text_for(ck, tid, label, held=False):
    r = ck['themes'][tid]; trial = 'TRIAL · ' if ck.get('trial') else ''
    tag = [label, f'{r["est_seconds"]:.0f} s', 'for ' + LAB.get(r['dest'], r['dest'])] + (['SOFT'] if r['tier'] == 'soft' else []) + (['NEWS'] if r['news'] else []) + (['HELD'] if held else [])
    q = r['hook']['quote'].strip(); q = q if len(q) <= 160 else q[:157] + '...'
    return f'{trial}📱 {" · ".join(tag)}\n{r["title"]}\n\nON SCREEN: {" / ".join(r["hook_text"])}\nOPENS ({r["hook"]["who"]}): "{q}"'

def keyboard(ep, tid):
    k = C.epk(ep)
    return {'inline_keyboard': [[{'text': '✅ Approve', 'callback_data': f'pr|{k}|t|ok|{tid}'}, {'text': '❌ Kill', 'callback_data': f'pr|{k}|t|kill|{tid}'}, {'text': '✏️ Notes', 'callback_data': f'pr|{k}|t|notes|{tid}'}]]}

def decide(W, ck, tid, decision, notes=None, rnd=1):
    r = ck['themes'][tid]
    C.decision(W, {'stage': 'theme', 'theme': tid, 'title': r['title'], 'decision': decision, 'notes': notes, 'round': rnd,
                   'attrs': {k: r[k] for k in ('total', 'scores', 'est_seconds', 'news', 'speakers', 'ranges', 'jumps', 'dest', 'tier')} | {'hook_who': r['hook']['who']}})

def checked(W):
    code, ck = CK.run(W)
    if ck is None: C.fail('check.py has structural errors - nothing is sent')
    return code, ck

def send(W, dry, only=None):
    code, ck = checked(W)
    if code and not only: C.fail('check.py exit 2: fewer than 5 deliverable - use tg_cards.py flag')
    ep = C.episode(W); st = state(W); todo = [t for t in ck['deliver'] if (only and t == only) or (not only and t not in st['themes'])]
    if only and only not in ck['deliver']: C.fail(f'{only} is not deliverable: {[h["why"] for h in ck["held"] if h["id"] == only]}')
    if not st['header'] and not only:
        head = f'{"TRIAL · " if ck.get("trial") else ""}📱 {ck["episode"]["label"]}: {len(ck["deliver"])} shorts' + (' (softened: fewer than 10 reached the strong line)' if ck.get('softened') else '') + '. Approve / Kill / Notes on each.'
        if dry: print(head + '\n' + '=' * 60)
        else: TG.say(head); st = state(W); st['header'] = True; C.save(spath(W), st)
    for t in todo:
        pos = ck['deliver'].index(t) + 1; rnd = st['themes'].get(t, {}).get('round', 0) + 1
        txt = text_for(ck, t, f'{pos}/{len(ck["deliver"])}' + (f' · round {rnd}' if rnd > 1 else ''))
        if dry: print(txt + '\n[ ✅ Approve ] [ ❌ Kill ] [ ✏️ Notes ]\n' + '=' * 60); continue
        m = TG.api('sendMessage', chat_id=TG.chat(), text=txt, reply_markup=keyboard(ep, t))
        st = state(W); st['themes'][t] = {'status': 'sent', 'message_id': m['message_id'], 'round': rnd, 'sent_at': C.now(), 'text_sha': ck['themes'][t]['text_sha'], 'notes': st['themes'].get(t, {}).get('notes', []), 'manual': False}
        st['settled'] = None; C.save(spath(W), st); C.event(W, f'SENT THEME {t} round {rnd}: {ck["themes"][t]["title"]}')
    if not todo: print('nothing new to send')

def flag(W, dry):
    code, ck = CK.run(W)
    if ck is None: C.fail('check.py has structural errors')
    if not ck.get('flag'): C.fail('enough themes pass - use tg_cards.py send')
    ep = C.episode(W); ok = list(ck['deliver']); held = sorted([r for r in ck['themes'].values() if r['hold'] and r.get('cold') and r['id'] not in ok], key=lambda r: -r['total'])[:10 - len(ok)]
    txt = f'{"TRIAL · " if ck.get("trial") else ""}⚠️ {ck["episode"]["label"]}: only {len(ok)} short(s) strong enough (minimum 5). Not padded.' + (f'\n{ck["episode_note"][:300]}' if ck.get('episode_note') else '') + f'\n{len(held)} held theme(s) follow. Approve = make it anyway.'
    st = state(W)
    if dry: print(txt + '\n' + '=' * 60)
    elif not st.get('flagged_at'): TG.say(txt); st = state(W); st['flagged_at'] = C.now(); st['header'] = True; C.save(spath(W), st); C.event(W, f'FLAG sent: {len(ok)} passing, {len(held)} held')
    all_ = [(t, False) for t in ok] + [(r['id'], True) for r in held]
    for i, (t, is_held) in enumerate(all_):
        if t in state(W)['themes']: continue
        body = text_for(ck, t, f'{i + 1}/{len(all_)}', held=is_held)
        if dry: print(body + '\n' + '=' * 60); continue
        m = TG.api('sendMessage', chat_id=TG.chat(), text=body, reply_markup=keyboard(ep, t))
        st = state(W); st['themes'][t] = {'status': 'sent', 'message_id': m['message_id'], 'round': 1, 'sent_at': C.now(), 'text_sha': ck['themes'][t]['text_sha'], 'notes': [], 'manual': is_held}
        st['settled'] = None; C.save(spath(W), st); C.event(W, f'SENT {"held " if is_held else ""}THEME {t}: {ck["themes"][t]["title"]}')

def settle(W):
    st = state(W); ck = C.load(f'{W}/checked.json')
    if not st['themes'] or st.get('settled') or any(v['status'] in ('sent', 'notes') for v in st['themes'].values()): return False
    ap = [t for t in ck['deliver'] if st['themes'].get(t, {}).get('status') == 'approved'] + [t for t, v in st['themes'].items() if v['status'] == 'approved' and t not in ck['deliver']]
    C.save(f'{W}/approved.json', {'at': C.now(), 'episode': ck['episode'], 'trial': ck.get('trial'),
                                  'approved': [{'id': t, 'title': ck['themes'][t]['title'], 'slug': ck['themes'][t]['slug'], 'dest': ck['themes'][t]['dest'], 'text_sha': st['themes'][t]['text_sha'], 'manual_override': bool(st['themes'][t].get('manual'))} for t in ap],
                                  'killed': [t for t, v in st['themes'].items() if v['status'] == 'killed']})
    TG.say(f'🔒 {ck["episode"]["label"]} shorts settled: {len(ap)} approved. Building them now; the pilot comes first.')
    st = state(W); st['settled'] = C.now(); C.save(spath(W), st); C.event(W, f'THEMES SETTLED approved={ap}'); return True

def handle(W, u):
    st = state(W); ck = C.load(f'{W}/checked.json')
    if not ck or not st['themes']: return False
    ep = C.episode(W); q = u.get('callback_query'); msg = u.get('message'); ch = TG.chat()
    if q:
        p = (q.get('data') or '').split('|')
        if len(p) != 5 or p[0] != 'pr' or p[1] != C.epk(ep) or p[2] != 't' or p[4] not in st['themes'] or (q.get('message') or {}).get('chat', {}).get('id') != ch: return False
        act, tid = p[3], p[4]; th = st['themes'][tid]; title = ck['themes'][tid]['title']
        if th['status'] in ('approved', 'killed') and act in ('ok', 'kill'): TG.ack(q, f'Already {th["status"]}.'); return True
        if act == 'ok':                                    # answer first, bookkeeping after
            TG.relabel(th['message_id'], '✅ Approved'); TG.ack(q, 'Approved')
            th.update({'status': 'approved', 'decided_at': C.now()})
            if st.get('awaiting_notes') == tid: st['awaiting_notes'] = None
            C.save(spath(W), st); decide(W, ck, tid, 'approved-manual' if th.get('manual') else 'approved', rnd=th['round']); C.event(W, f'APPROVED THEME {tid}: {title}')
        elif act == 'kill':
            TG.relabel(th['message_id'], '❌ Killed'); TG.ack(q, 'Killed')
            th.update({'status': 'killed', 'decided_at': C.now()})
            if st.get('awaiting_notes') == tid: st['awaiting_notes'] = None
            C.save(spath(W), st); decide(W, ck, tid, 'killed', rnd=th['round']); C.event(W, f'KILLED THEME {tid}: {title}')
            code, ck2 = CK.run(W, fresh=False)
            new = [t for t in (ck2 or {}).get('deliver', []) if t not in state(W)['themes']] if ck2 else []
            if new:
                t = new[0]; m = TG.api('sendMessage', chat_id=ch, text=text_for(ck2, t, 'RUNNER-UP'), reply_markup=keyboard(ep, t))
                st = state(W); st['themes'][t] = {'status': 'sent', 'message_id': m['message_id'], 'round': 1, 'sent_at': C.now(), 'text_sha': ck2['themes'][t]['text_sha'], 'notes': [], 'replaces': tid}; C.save(spath(W), st)
                C.event(W, f'SENT RUNNER-UP {t} for {tid}: {ck2["themes"][t]["title"]}')
            else: TG.say('No runner-up passes the gates.'); C.event(W, f'NO RUNNER-UP for {tid}')
        elif act == 'notes':
            TG.ack(q, 'Type your notes'); st['awaiting_notes'] = tid; C.save(spath(W), st); TG.say(f'✏️ Notes for "{title[:60]}": one message.'); C.event(W, f'NOTES requested THEME {tid}')
        else: TG.ack(q)
        settle(W); return True
    if msg and msg.get('chat', {}).get('id') == ch and msg.get('text'):
        rid = (msg.get('reply_to_message') or {}).get('message_id')
        tid = next((t for t, v in st['themes'].items() if v.get('message_id') == rid), None) if rid else st.get('awaiting_notes')
        if not tid: return False
        th = st['themes'][tid]; th.setdefault('notes', []).append({'at': C.now(), 'text': msg['text']})
        if th['status'] == 'approved':
            th['notes'][-1]['after_approval'] = True; st['awaiting_notes'] = None; C.save(spath(W), st); decide(W, ck, tid, 'note-after-approval', notes=msg['text'], rnd=th['round'])
            TG.say(f'Noted for "{ck["themes"][tid]["title"][:50]}" (it stays approved).'); C.event(W, f'NOTE after approval THEME {tid}: {msg["text"]}'); return True
        if th['status'] != 'killed': th['status'] = 'notes'
        st['awaiting_notes'] = None; C.save(spath(W), st); decide(W, ck, tid, 'notes' if th['status'] == 'notes' else 'kill-reason', notes=msg['text'], rnd=th['round'])
        TG.say(f'Noted for "{ck["themes"][tid]["title"][:50]}".' + (' I will revise it and send it again.' if th['status'] == 'notes' else '')); C.event(W, f'NOTES THEME {tid}: {msg["text"]}')
        return True
    return False

if __name__ == '__main__':
    a = [x for x in sys.argv[1:] if not x.startswith('--')]; dry = '--dry-run' in sys.argv
    if len(a) < 2: C.fail(__doc__)
    cmd, W = a[0], os.path.abspath(a[1])
    if cmd == 'send': send(W, dry)
    elif cmd == 'resend': send(W, dry, only=a[2])
    elif cmd == 'flag': flag(W, dry)
    elif cmd == 'say': (print(a[2]) if dry else (TG.say(a[2]), C.event(W, f'SAID: {a[2][:200]}')))
    elif cmd == 'status': st = state(W); print(json.dumps({t: {k: v[k] for k in ('status', 'round')} for t, v in st['themes'].items()}, indent=1), 'awaiting notes:', st.get('awaiting_notes'))
    else: C.fail(__doc__)
