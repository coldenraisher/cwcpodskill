"""window.py propose|ask|set|show <RUN>      THE POSTING WINDOW is Colden's call, asked before any cadence is built
Colden 2026-10-03: "Default can be Fri-Thurs but I think it would be best to ask for a time span first then develop your
cadence around that and the currently scheduled clips, rather than just assume and move on. this week, for instance, it
will already be saturday/sunday before clips get posted."
  propose <RUN>   print the default to put to him: the day after the show (tomorrow when that has passed) -> the next
                  Thursday, plus what is already scheduled in that span when the calendar has been read
  ask     <RUN>   the same as a Telegram card: [Use this] [Change] (handled by tg_plan.py's plugin). Change -> his next
                  message lands in run.json window_notes_open: read it, then `set` with his words
  set     <RUN> YYYY-MM-DD YYYY-MM-DD --by "<his words>"      record the window he gave (in the session or on Telegram)
  show    <RUN>
GATE (plan.py): no plan without a window he confirmed, and never one that starts before today."""
import os, sys, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

def proposal(r):
    today = dt.datetime.now(C.ET).date(); sd = dt.date.fromisoformat(r['show_date']) if r.get('show_date') else None
    return C.propose_window(sd, today)

def busy_lines(R, start, end):
    out = []
    y = C.load(f'{R}/calendar/youtube.json') or {}
    for b, vids in (y.get('channels') or {}).items():
        for v in vids:
            when = v.get('publish_at') or v.get('start_at')
            if when:
                d = dt.datetime.fromisoformat(when.replace('Z', '+00:00')).astimezone(C.ET)
                if start <= d.date() <= end: out.append(f'{C.DAYS[d.weekday()]} {d:%m/%d %H:%M} {b.upper()} YouTube: {v["title"][:50]}')
    for b in ('cwc', 'tcl'):
        for p in (C.load(f'{R}/calendar/metricool_{b}.json') or {}).get('posts', []):
            d = dt.datetime.fromisoformat(p['at'])
            if start <= d.date() <= end: out.append(f'{C.DAYS[d.weekday()]} {d:%m/%d %H:%M} {b.upper()} Metricool: {p["text"][:40]}')
    return sorted(out)

def main():
    a = sys.argv[1:]
    if len(a) < 2: print(__doc__); sys.exit(1)
    cmd, R = a[0], a[1].rstrip('/'); r = C.run(R)
    if cmd in ('propose', 'ask'):
        s, e = proposal(r); busy = busy_lines(R, s, e)
        text = (f'Posting window for {r["show_name"]} {r["ep_key"]}?\nProposed: {C.DAYS[s.weekday()]} {s:%m/%d} -> {C.DAYS[e.weekday()]} {e:%m/%d} (ET)\n'
                + ('Already scheduled in that span:\n' + '\n'.join(busy[:15]) if busy else '(calendar not read yet)' if not os.path.exists(f'{R}/calendar/youtube.json') else 'Nothing scheduled in that span yet.'))
        r['window_proposed'] = C.window_dict(s, e, at=C.now()); C.save_run(R, r)
        if cmd == 'propose': print(text); return
        import tg, tg_plan
        k = tg_plan.key(r); span = f'{s:%Y%m%d}-{e:%Y%m%d}'
        m = tg.say(text, [[{'text': 'Use this', 'callback_data': f'pa|{k}|wok|{span}'}, {'text': 'Change', 'callback_data': f'pa|{k}|wchg|{span}'}]])
        r = C.run(R); r['window_card'] = {'message_id': m['message_id'], 'span': span, 'at': C.now()}; r.pop('window_notes_open', None); C.save_run(R, r)
        C.event(R, f'WINDOW CARD {span}'); print(text + '\n-> sent on Telegram')
    elif cmd == 'set':
        if len(a) < 4 or '--by' not in a: C.fail('set <RUN> YYYY-MM-DD YYYY-MM-DD --by "<his words>"')
        s, e, by = dt.date.fromisoformat(a[2]), dt.date.fromisoformat(a[3]), a[a.index('--by') + 1]
        if e < s: C.fail('the window ends before it starts')
        if len(by.strip()) < 3: C.fail('--by needs his words')
        r['window'] = C.window_dict(s, e, confirmed_by=by, confirmed_at=C.now()); r.pop('window_notes_open', None); C.save_run(R, r)
        C.event(R, f'WINDOW SET {s} -> {e} ({by})'); print(f'window: {C.DAYS[s.weekday()]} {s} -> {C.DAYS[e.weekday()]} {e} ({by})')
    elif cmd == 'show':
        w = r.get('window') or {}
        print(f'window: {w.get("start_dow")} {w.get("start")} -> {w.get("end_dow")} {w.get("end")}  ' + (f'confirmed by {w["confirmed_by"]} at {w["confirmed_at"]}' if w.get('confirmed_by') else 'NOT CONFIRMED - window.py ask'))
        if r.get('window_notes_open'): print(f'his answer to read: "{r["window_notes_open"]}" -> window.py set ... --by "<his words>"')
    else: print(__doc__); sys.exit(1)

if __name__ == '__main__': main()
