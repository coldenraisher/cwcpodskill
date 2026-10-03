"""tg_plan.py - the posting plan on Telegram (ruling 11; memory: "never create Metricool posts without Colden's go").
  tg_plan.py send <WORK> [--dry-run]
        one calendar card per brand (plan_card.py; Create with Colden first), the CUT list on it, and under the last
        card the buttons [Schedule all] [Changes]. GATE: review/publish_plan.json exists and every planned short is
        uploaded (publish.py upload).
Taps (CWC listener -> tg_router.py): Schedule all -> review/plan_state.json approved + "PLAN APPROVED" in events.log;
only THEN does Claude run publish.py payloads and fire createScheduledPost per call through the right connector, then
publish.py record. Changes -> his next message -> "PLAN NOTES" -> re-plan, send again."""
import os, sys, json
import common as C, tg_api as TG
def spath(W): return f'{W}/review/plan_state.json'
def send(W, dry):
    import plan_card as PC
    pl = C.load(f'{W}/review/publish_plan.json') or C.fail('publish.py plan first'); st = C.load(f'{W}/review/publish.json', {}) or {}
    miss = [f'{p["short"]} {p["brand"]}' for p in pl['posts'] if not (st.get('links', {}).get(p['short'], {}).get(p['brand']))]
    if miss: C.fail(f'not uploaded yet: {miss} (publish.py upload)')
    ep = C.episode(W); k = C.epk(ep); brands = [b for b in ('cwc', 'tcl') if any(p['brand'] == b for p in pl['posts'])]
    cards = [(b, PC.render(W, b)) for b in brands]
    kb = {'inline_keyboard': [[{'text': '✅ Schedule all', 'callback_data': f'pr|{k}|p|ok'}, {'text': '✏️ Changes', 'callback_data': f'pr|{k}|p|chg'}]]}
    cut = '\n'.join(f'✂️ {x["short"].upper()} not on {x["brand"].upper()}: {x["why"]}' for x in pl.get('cut', []))
    if dry: print([c for _, c in cards], cut, kb); return
    mid = None
    for i, (b, png) in enumerate(cards):
        last = i == len(cards) - 1; cap = f'📅 {ep["show_name"]} Ep {ep["ep_no"]} - {b.upper()} plan' + (f'\n{cut}\nSchedule all = these posts go to Metricool now.' if last else '')
        m = TG.send_photo(png, cap, kb if last else None); mid = m['message_id']
    C.save(spath(W), {'status': 'sent', 'message_id': mid, 'sent_at': C.now(), 'plan_made_at': pl['made_at']}); C.event(W, f'SENT PLAN: {len(pl["posts"])} posts, cut {len(pl.get("cut", []))}')
def handle(W, u):
    st = C.load(spath(W), {}) or {}
    if not st: return False
    k = C.epk(C.episode(W)); q = u.get('callback_query'); msg = u.get('message'); ch = TG.chat()
    if q:
        p = (q.get('data') or '').split('|')
        if len(p) < 4 or p[0] != 'pr' or p[1] != k or p[2] != 'p' or (q.get('message') or {}).get('chat', {}).get('id') != ch: return False
        if st['status'] == 'approved': TG.ack(q, 'Already approved.'); return True
        if p[3] == 'ok':
            TG.relabel(st['message_id'], '✅ Scheduling now'); TG.ack(q, 'Scheduling')
            st.update(status='approved', approved_at=C.now()); C.save(spath(W), st); C.decision(W, {'stage': 'plan', 'decision': 'approved'}); C.event(W, 'PLAN APPROVED'); return True
        if p[3] == 'chg':
            TG.ack(q, 'Type your changes'); st['awaiting_notes'] = True; C.save(spath(W), st); TG.say('✏️ What should change in the plan? One message.'); C.event(W, 'PLAN CHANGES requested'); return True
        TG.ack(q); return True
    if msg and msg.get('chat', {}).get('id') == ch and msg.get('text'):
        rid = (msg.get('reply_to_message') or {}).get('message_id')
        if not (st.get('awaiting_notes') or (rid and rid == st.get('message_id'))): return False
        st.setdefault('notes', []).append({'at': C.now(), 'text': msg['text']}); st.update(awaiting_notes=False, status='changes'); C.save(spath(W), st)
        C.decision(W, {'stage': 'plan', 'decision': 'notes', 'notes': msg['text']}); TG.say('Noted. I will re-plan and send it again.'); C.event(W, f'PLAN NOTES: {msg["text"]}'); return True
    return False
if __name__ == '__main__':
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    if len(a) < 2 or a[0] != 'send': C.fail(__doc__)
    send(os.path.abspath(a[1]), '--dry-run' in sys.argv)
