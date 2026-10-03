"""The EDIT review on Telegram (@VideoEditReview_bot) - one clip version at a time.

  tg_edit.py send <WORK> <id> [--channel cwc|tcl] [--note "<one short line>"] [--dry-run]
        the newest VERIFIED version's preview, shrunk under Telegram's 50 MB, sent WITH its metadata (Colden's global
        rule 2026-09-29: width, height, duration read from the file, supports_streaming, a cover of the same shape - a
        file that cannot be probed is not sent), a SHORT caption (ruling 22) and four buttons (ruling 28: one tap
        approves the edit AND picks the channel):  Colden's channel / Creative Lens / Both / Changes.
        The caption carries by itself what he must listen for: every written trim inside a sentence, every softened
        swear that is not beeped, a cold-open waiver. Sending vN RETIRES the open cards of older versions of the same
        clip and channel (buttons stripped, "replaced by vN").
  tg_edit.py supersede <WORK> <id> <cwc|tcl> <vN> "<why>"    retire a version that must not be approved (never by hand in the json)
  tg_edit.py drop <WORK> <id> "<Colden's words>"             he does not want this clip: out of approved.json, every card closed
The always-on listener (tg_listen.py) answers the taps (answer first, then the state under the shared lock):
Approve-for-a-channel -> the version is `approved` with its channel(s) in edit/<id>/versions.json (the master is
rendered AFTER this, never before). Changes -> his next message (or a reply to the video) is stored as that version's
notes: fix, build the next version, review, send.
State: <WORK>/edit/review.json. Log: <WORK>/review/events.log. Decisions: data/decisions.jsonl.
GATES: a card goes out only while the listener runs; only a version build.py verified, whose review.py check passed
and whose contact sheet was looked at (review.py ack, bound to the sheet's hash); a tap counts only on the version's
CURRENT card and only while that version is live (a superseded / rejected / dropped version answers "replaced");
taps from another chat, another episode or another show are not ours."""
import os, re, sys, json, time, uuid, subprocess, mimetypes, urllib.request
import common as C, tg_themes as G

def probe(path):
    r = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height:format=duration', '-of', 'json', path], capture_output=True, text=True)
    j = json.loads(r.stdout or '{}'); st = (j.get('streams') or [{}])[0]; d = float((j.get('format') or {}).get('duration') or 0)
    if not st.get('width') or not st.get('height') or d <= 0: C.fail(f'cannot probe {path} - not sent (never a guessed size)')
    return st['width'], st['height'], d

def shrink(src, out, limit_mb=45):
    w, h, d = probe(src); kbps = int(limit_mb * 8 * 1024 / d) - 96
    if os.path.getsize(src) <= limit_mb * 1024 * 1024 and src.endswith('.mp4'): return src
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', src, '-vf', "scale='min(1280,iw)':-2", '-c:v', 'libx264', '-preset', 'medium', '-b:v', f'{kbps}k', '-maxrate', f'{int(kbps * 1.3)}k', '-bufsize', f'{kbps * 2}k',
                    '-c:a', 'aac', '-b:a', '96k', '-movflags', '+faststart', out], check=True)
    assert os.path.getsize(out) <= 49 * 1024 * 1024, f'{out} is still over 49 MB'
    return out

def multipart(method, fields, files):
    b = uuid.uuid4().hex; body = b''
    for k, v in fields.items(): body += f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
    for field, fp in files:
        body += (f'--{b}\r\nContent-Disposition: form-data; name="{field}"; filename="{os.path.basename(fp)}"\r\nContent-Type: {mimetypes.guess_type(fp)[0] or "application/octet-stream"}\r\n\r\n').encode() + open(fp, 'rb').read() + b'\r\n'
    body += f'--{b}--\r\n'.encode()
    r = json.load(urllib.request.urlopen(urllib.request.Request(f'https://api.telegram.org/bot{G.token()}/{method}', data=body, headers={'Content-Type': f'multipart/form-data; boundary={b}'}), timeout=900))
    if not r.get('ok'): raise RuntimeError(str(r))
    return r['result']

def rpath(W): return f'{W}/edit/review.json'
def rstate(W): return C.load(rpath(W), {'items': {}})
def versions(W, tid): return C.load(f'{W}/edit/{tid}/versions.json', [])
def strip(mid, text):
    try: G.api('editMessageReplyMarkup', chat_id=G.chat(), message_id=mid, reply_markup={'inline_keyboard': [[{'text': text, 'callback_data': 'noop'}]]})
    except Exception: pass

def auto_note(W, tid, v):
    """what he must listen for, taken from the plan this version was built from (never left to memory)"""
    P = C.load(v['plan']) or {}; fps = P.get('fps') or 30; L = []
    for t in P.get('written_trims') or []: L.append(f'✂️ trim inside a sentence ({t["section"]}): {t["words"]} - listen')
    for w in P.get('soft_swears') or []: L.append(f'"{w["word"]}" at {w["at"]} not beeped')
    if P.get('cold_open_waiver'): L.append(f'cold open {P["anchors"]["hook_end"] / fps:.0f} s (your OK on file)')
    return L

def retire(W, tid, ch, keep_key, why):
    """close every OPEN card of older versions of this clip + channel"""
    for k, o in rstate(W)['items'].items():
        if k.startswith(f'{tid}|{ch}|') and k != keep_key and o.get('status') in ('sent', 'changes'):
            if o.get('message_id'): strip(o['message_id'], why)
            C.update(rpath(W), lambda s: s['items'][k].update(status='superseded', superseded_at=C.now(), superseded_why=why))
            vn = int(k.split('|')[2][1:]); row = next((x for x in versions(W, tid) if x['v'] == vn and x['channel'] == ch), None)
            if row and row.get('status') in ('draft', 'building'): C.set_version(W, tid, ch, vn, status=f'superseded: {why}')
            G.event(W, f'EDIT RETIRED {k}: {why}')

def send(W, tid, channel, note, dry):
    ep = C.episode(W); v = C.newest_built(W, tid, channel); key = f'{tid}|{v["channel"]}|v{v["v"]}'; pv = v.get('preview')
    if not pv or not os.path.exists(pv): C.fail(f'{key} has no preview render (review.py render)')
    pc = v.get('preview_check') or {}
    if not pc or pc.get('problems'): C.fail(f'{key}: review.py check has not passed ({pc.get("problems")})')
    if not dry and (not v.get('looked') or v['looked'].get('sheet_sha') != C.sha_file(pc['sheet'])): C.fail(f'{key}: the contact sheet has not been looked at - open {pc["sheet"]}, then: review.py ack <WORK> {tid} "<what you saw: every camera, b-roll, tag, ending>"')
    if note and len(note) > 200: C.fail(f'--note is {len(note)} characters - one short line (ruling 22: cards are short), 200 at most')
    small = shrink(pv, pv.rsplit('.', 1)[0] + ' (tg).mp4'); w, h, d = probe(small)
    cover = small.rsplit('.', 1)[0] + ' (cover).jpg'
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-ss', '2', '-i', small, '-frames:v', '1', '-vf', "scale='if(gt(iw,ih),320,-2)':'if(gt(iw,ih),-2,320)'", cover], check=True)
    ck = C.load(f'{W}/checked.json'); th = ck['themes'][tid]; lab = ck['episode']['label']; S = C.show(ep['show'])['channels']['labels']
    cap = '\n'.join([f'🎬 {lab} · C{tid[1:]} v{v["v"]} · {C.mmss(d)}', th['title']] + auto_note(W, tid, v) + ([note] if note else []))
    kb = {'inline_keyboard': [[{'text': f'✅ {S.get("cwc", "cwc")}', 'callback_data': f'pe|{ep["ep_key"]}|{key}|cwc'}, {'text': f'✅ {S.get("tcl", "tcl")}', 'callback_data': f'pe|{ep["ep_key"]}|{key}|tcl'}],
                              [{'text': '✅ Both', 'callback_data': f'pe|{ep["ep_key"]}|{key}|both'}, {'text': '✏️ Changes', 'callback_data': f'pe|{ep["ep_key"]}|{key}|chg'}]]}
    if dry: print(cap, '\n', [[b['text'] for b in row] for row in kb['inline_keyboard']], f'\n{small}  {w}x{h}  {d:.1f}s  {os.path.getsize(small) / 1e6:.1f} MB  cover {cover}'); return
    m = multipart('sendVideo', {'chat_id': G.chat(), 'caption': cap[:1000], 'width': w, 'height': h, 'duration': int(round(d)), 'supports_streaming': 'true', 'reply_markup': json.dumps(kb)}, [('video', small), ('thumbnail', cover)])
    old = rstate(W)['items'].get(key) or {}
    if old.get('message_id'): strip(old['message_id'], 'Sent again below')
    C.update(rpath(W), lambda s: s['items'].__setitem__(key, {'status': 'sent', 'message_id': m['message_id'], 'old_message_ids': old.get('old_message_ids', []) + ([old['message_id']] if old.get('message_id') else []),
                                                             'sent_at': C.now(), 'timeline': v['timeline'], 'notes': old.get('notes', [])}), {'items': {}})
    retire(W, tid, v['channel'], key, f'replaced by v{v["v"]}')
    G.event(W, f'SENT EDIT {key}: {v["timeline"]} ({w}x{h}, {d:.0f} s, {os.path.getsize(small) / 1e6:.1f} MB)')

def decide(W, key, decision, notes=None, stage='edit'):
    ep = C.episode(W); tid = key.split('|')[0]; ck = C.load(f'{W}/checked.json'); os.makedirs(C.DATA, exist_ok=True)
    with open(f'{C.DATA}/decisions.jsonl', 'a') as f:
        f.write(json.dumps({'at': C.now(), 'show': ep['show'], 'ep': ep['ep_key'], 'trial': bool(ep.get('trial')), 'stage': stage, 'theme': tid, 'version': key, 'title': ck['themes'][tid]['title'], 'decision': decision, 'notes': notes}, ensure_ascii=False) + '\n')

NAMES = {'cwc': "Colden's channel", 'tcl': 'The Creative Lens', 'both': 'both channels'}
def handle(W, u):
    """one Telegram update against this episode's EDIT previews -> True when it was ours"""
    st = rstate(W)
    if not st['items']: return False
    ep = C.episode(W); ch = G.chat(); q = u.get('callback_query'); msg = u.get('message'); rp = rpath(W)
    if q:
        p = q.get('data', '').split('|'); mid = (q.get('message') or {}).get('message_id')
        if (q.get('message') or {}).get('chat', {}).get('id') != ch or len(p) != 6 or p[0] != 'pe' or p[1] != ep['ep_key']: return False
        key = '|'.join(p[2:5]); act = p[5]; it = st['items'].get(key); tid, bch, vn = p[2], p[3], int(p[4][1:])
        if not it or mid not in [it.get('message_id')] + it.get('old_message_ids', []): return False       # another show's episode with the same key
        def ack(t):
            try: G.api('answerCallbackQuery', callback_query_id=q['id'], text=t)
            except Exception: pass
        row = next((x for x in versions(W, tid) if x['v'] == vn and x['channel'] == bch), None)
        if it['status'] == 'approved': ack('Already approved.'); return True
        if mid != it.get('message_id') or it['status'] not in ('sent', 'changes') or not row or not C.live(row) or row.get('status') not in ('draft',):
            ack('This version was replaced - use the newest card.'); strip(mid, 'Replaced by a newer version'); return True
        def mark(t):
            try: G.api('editMessageReplyMarkup', chat_id=ch, message_id=mid, reply_markup={'inline_keyboard': [[{'text': t, 'callback_data': 'noop'}]]})
            except Exception: pass
        if act in NAMES:                                  # answer first, bookkeeping after (under the lock, on fresh state)
            G.both(lambda: mark(f'✅ Approved for {NAMES[act]}'), lambda: ack('Approved'))
            chans = ['cwc', 'tcl'] if act == 'both' else [act]
            C.update(rp, lambda s: s['items'][key].update(status='approved', channels=chans, decided_at=C.now())); C.clear_awaiting('edit', W, key)
            C.set_version(W, tid, bch, vn, status='approved', channels=chans, approved_at=C.now()); decide(W, key, f'approved:{act}'); G.event(W, f'EDIT APPROVED {key} for {NAMES[act]}')
        elif act == 'chg':
            ack('Type your changes'); C.update(rp, lambda s: s['items'][key].update(status='changes')); C.set_awaiting('edit', W, key)
            G.api('sendMessage', chat_id=ch, text='✏️ What should change? One message.'); G.event(W, f'EDIT CHANGES requested {key}')
        else: ack('')
        return True
    if msg and msg.get('chat', {}).get('id') == ch and msg.get('text'):
        rid = (msg.get('reply_to_message') or {}).get('message_id')
        key = next((k for k, v in st['items'].items() if rid in [v.get('message_id')] + v.get('old_message_ids', [])), None) if rid else C.awaiting('edit', W)   # a reply to ANOTHER message is not ours
        if not key or key not in st['items']: return False
        if st['items'][key]['status'] == 'approved':      # a note on an approved version is logged, never un-approves it
            C.update(rp, lambda s: s['items'][key].setdefault('notes', []).append({'at': C.now(), 'text': msg['text'], 'after_approval': True})); C.clear_awaiting('edit', W, key)
            decide(W, key, 'note-after-approval', msg['text']); G.api('sendMessage', chat_id=ch, text='Noted (that version stays approved until a new one replaces it).'); G.event(W, f'EDIT NOTE after approval {key}: {msg["text"]}')
            return True
        def mut(s):
            o = s['items'][key]; o.setdefault('notes', []).append({'at': C.now(), 'text': msg['text']})
            if o['status'] in ('sent', 'changes'): o['status'] = 'changes'
        C.update(rp, mut); C.clear_awaiting('edit', W, key)
        decide(W, key, 'changes', msg['text']); G.api('sendMessage', chat_id=ch, text='Noted. I will fix it and send the next version.'); G.event(W, f'EDIT NOTES {key}: {msg["text"]}')
        return True
    return False

def supersede(W, tid, ch, vn, why):
    if len(why) < 8: C.fail('say why (a few words)')
    row = next((x for x in versions(W, tid) if x['v'] == vn and x['channel'] == ch), None)
    if not row: C.fail(f'{tid} {ch} v{vn} is not in versions.json')
    if row.get('status') == 'locked': C.fail(f'{tid} {ch} v{vn} is LOCKED - a change after the lock is a new version (build, review, approve, master); lock.py then replaces the locked one')
    key = f'{tid}|{ch}|v{vn}'; it = rstate(W)['items'].get(key)
    if it:
        if it.get('message_id'): strip(it['message_id'], f'Replaced: {why}'[:60])
        C.update(rpath(W), lambda s: s['items'][key].update(status='superseded', superseded_at=C.now(), superseded_why=why))
    C.set_version(W, tid, ch, vn, status=f'superseded: {why}', was=row.get('status')); G.event(W, f'EDIT SUPERSEDED {key}: {why}')

def drop(W, tid, words):
    if len(words) < 8: C.fail("quote Colden's words for dropping the clip")
    ap = C.load(f'{W}/approved.json') or {}
    if not any(a['id'] == tid for a in ap.get('approved', [])): C.fail(f'{tid} is not in approved.json')
    for v in versions(W, tid):
        if v.get('status') == 'locked': C.fail(f'{tid} has a LOCKED version ({v["timeline"]}) - dropping a delivered clip is Colden\'s explicit call: ask him what to do with the timeline and the master')
    for v in versions(W, tid):
        if C.live(v): supersede(W, tid, v['channel'], v['v'], f'dropped: {words}'[:120])
    def mut(a): e = next(x for x in a['approved'] if x['id'] == tid); a['approved'].remove(e); a.setdefault('dropped', []).append(dict(e, dropped_at=C.now(), words=words))
    C.update(f'{W}/approved.json', mut); decide(W, f'{tid}|-|-', 'dropped', words); G.event(W, f'CLIP DROPPED {tid}: {words}')

if __name__ == '__main__':
    a = [x for x in sys.argv[1:] if not x.startswith('--')]; dry = '--dry-run' in sys.argv
    def opt(n): return sys.argv[sys.argv.index(n) + 1] if n in sys.argv else None
    for o in ('--channel', '--note'):
        if opt(o) in a: a.remove(opt(o))
    if len(a) < 2: C.fail(__doc__)
    cmd, W = a[0], os.path.abspath(a[1])
    if cmd == 'send':
        if not dry: C.need_listener()
        send(W, a[2], opt('--channel'), opt('--note'), dry)
    elif cmd == 'supersede' and len(a) >= 6: supersede(W, a[2], a[3], int(a[4].lstrip('v')), a[5])
    elif cmd == 'drop' and len(a) >= 4: drop(W, a[2], a[3])
    else: C.fail(__doc__)
