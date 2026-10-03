"""cal.py - what is ALREADY on the calendar, before anything is planned (Colden 2026-10-03: "you will need to check
youtube and metricool first to see what is already on the calendar"; 2026-09-15: "Always look at YouTube Studio to
schedule. This is a must!" - Metricool cannot see Studio-native schedules).

  cal.py youtube <RUN>
        both channels through the API: every scheduled upload + everything published in the last 21 days -> calendar/youtube.json
  cal.py metricool <RUN> <cwc|tcl> <file> --from YYYY-MM-DD --to YYYY-MM-DD
        Claude calls getScheduledPosts on THAT brand's connector (cwc = the claude.ai Metricool connector, blogId 5965295;
        tcl = metricool-tcl, blogId 6367106) from the 1st of the window's first month to the last day of its last month,
        timezone America/New_York, saves the answer verbatim to <file>, then this normalises it -> calendar/metricool_<brand>.json
        (--from / --to = the range that was asked; it must cover the window's months or the month count would be short)
  cal.py besttimes <RUN> <cwc|tcl> <file>
        getBestTimeToPostByNetwork socialNetwork=tiktok for that brand, the coming week, saved verbatim -> calendar/best_<brand>.json
        (the answer as it came on 2026-10-03: {"data": [{"dayOfWeek": 1-7, "bestTimesByHour": [{"hourOfDay", "value"}]}]}, dayOfWeek
        ISO = 1 Monday .. 7 Sunday; rows already flattened to {"dow": 0-6 with 0 = Monday, "hour", "value"} are read too)
  cal.py peaks <RUN> <cwc|tcl> <file>
        FRESH viewer peaks per channel (Colden 2026-10-03: "For clip timings it might be best to pull fresh data from
        YouTube before determining"): Claude in Chrome opens
        https://studio.youtube.com/channel/<channel id>/analytics/tab-build_audience/period-default, confirms the channel
        (CWC UC3fBnVhH68gXhGAnn8J9IcA / TCL UCPcaMEVrhEwy08fK01U-Niw - never the old gymnastics one), runs
        scripts/studio_viewers_online.js in the page and saves what it returns -> calendar/peaks_<brand>.json
        (a card with no data is recorded as such: that channel's clips fall back to 2 PM, flagged on the card)
  cal.py counts <RUN> <cwc|tcl> <YYYY-MM>=<n> (--evidence <screenshot.png> | --by "<Colden's words>")
        the posts already used in that month on that Metricool account. The 20-post limit starts over on the 1st
        (Colden 2026-10-03). The number comes from the Metricool calendar itself (his ruling): Claude in Chrome, the brand's
        planner in month view, a screenshot (saved as the evidence), every post that month counted - published and
        scheduled. Or Colden's own number. What getScheduledPosts lists for the month (on 2026-10-03 it listed a PUBLISHED
        post too, whatever its description says) and the posts this skill created are the FLOOR: a count below it is refused.
  cal.py show <RUN>

plan.py needs a confirmed count (<= 12 h old) for every month a Metricool post lands in, and refuses one that is below
the floor (the posts Metricool's own API lists for that month, the posts this skill created - data/metricool_ledger.jsonl)."""
import os, re, sys, json, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

def cal(R, name): return f'{R}/calendar/{name}'

def first(d, *keys):
    for k in keys:
        cur = d
        for part in k.split('.'):
            cur = cur.get(part) if isinstance(cur, dict) else None
        if cur not in (None, ''): return cur
    return None

def rows_of(raw):
    if isinstance(raw, list): return raw
    for k in ('data', 'posts', 'rows', 'result', 'items'):
        if isinstance(raw, dict) and isinstance(raw.get(k), list): return raw[k]
    C.fail('could not find the list of posts in that file - save the tool answer verbatim (a list, or {"data": [...]})')

def norm_post(p):
    when = first(p, 'publicationDate.dateTime', 'date', 'dateTime', 'publicationDate')
    if not when: return None
    tz = first(p, 'publicationDate.timezone') or 'America/New_York'
    d = dt.datetime.fromisoformat(str(when).replace('Z', '+00:00'))
    if not d.tzinfo: d = d.replace(tzinfo=C.ZoneInfo(tz))
    nets = [x.get('network') for x in (p.get('providers') or []) if isinstance(x, dict)] or p.get('networks') or []
    sts = {x.get('status') for x in (p.get('providers') or []) if isinstance(x, dict) and x.get('status')}
    return {'id': str(first(p, 'id', 'postId', 'uuid') or ''), 'at': d.astimezone(C.ET).isoformat(timespec='minutes'),
            'networks': nets, 'text': (p.get('text') or '')[:80], 'status': 'published' if sts == {'PUBLISHED'} else 'scheduled'}

def hours(text):
    """'7 PM, 8 PM' / '19:00, 20:00' / '7PM' -> [19, 20]"""
    out = []
    for tok in [t.strip() for t in text.split(',') if t.strip()]:
        m = re.match(r'(\d{1,2})(?::\d{2})?\s*([AaPp][Mm])?', tok)
        if not m: continue
        h = int(m.group(1)); ap = (m.group(2) or '').lower()
        if ap == 'pm' and h != 12: h += 12
        if ap == 'am' and h == 12: h = 0
        out.append(h % 24)
    return sorted(set(out))

def months_between(a, b):
    out, d = [], dt.date(a.year, a.month, 1)
    while d <= b: out.append(d.strftime('%Y-%m')); d = (d.replace(day=28) + dt.timedelta(days=4)).replace(day=1)
    return out

def ledger(brand):
    out = []
    p = f'{C.DATA}/metricool_ledger.jsonl'
    if os.path.exists(p):
        for line in open(p, encoding='utf-8'):
            try: x = json.loads(line)
            except ValueError: continue
            if x.get('brand') == brand: out.append(x)
    return out

def month_counts(R, brand):
    """{month: {"used": n | None, "source": "..", "floor": n}} for the months the window (+ spill) touches; None = not
    confirmed. floor = what is provably there: the posts Metricool's API lists for that month, the posts this skill created"""
    r = C.run(R); W = C.window(r); w0, w1 = dt.date.fromisoformat(W['start']), dt.date.fromisoformat(W['end'])
    given = (C.load(cal(R, f'counts_{brand}.json')) or {}); out = {}; stale = C.rules()['counts_staleness_hours']
    listed = (C.load(cal(R, f'metricool_{brand}.json')) or {}).get('posts', [])
    for mo in months_between(w0, w1 + dt.timedelta(days=C.rules()['spill_days_max'])):
        g = given.get(mo); mine = len({x['post_id'] for x in ledger(brand) if str(x.get('publish_at', ''))[:7] == mo})
        floor = max(mine, len([p for p in listed if p['at'][:7] == mo]))
        if not g or (dt.datetime.now(C.ET) - C.et(g['at'])).total_seconds() / 3600 > stale:
            out[mo] = {'used': None, 'floor': floor, 'source': 'not confirmed' if not g else f'confirmed {g["at"]} - older than {stale} h'}; continue
        src = f'Metricool calendar screenshot {os.path.basename(g["evidence"])}' if g.get('evidence') else f'Colden: {g["words"]}'
        out[mo] = {'used': g['n'], 'floor': floor, 'source': src}
    return out

def main():
    a = sys.argv[1:]
    if len(a) < 2: print(__doc__); sys.exit(1)
    cmd, R = a[0], a[1].rstrip('/'); r = C.run(R); os.makedirs(f'{R}/calendar', exist_ok=True)
    if cmd == 'youtube':
        import ytapi as Y
        out = {'at': C.now(), 'channels': {}}
        for b in ('cwc', 'tcl'):
            out['channels'][b] = Y.uploads(b); print(f'{b}: {len(out["channels"][b])} recent / scheduled uploads')
        C.save(cal(R, 'youtube.json'), out); C.event(R, 'CALENDAR youtube read')
    elif cmd == 'metricool':
        b, f = a[2], a[3]
        if '--from' not in a or '--to' not in a: C.fail('--from and --to (the range you asked Metricool for) are required')
        fr, to = a[a.index('--from') + 1], a[a.index('--to') + 1]
        W = C.window(r); w0, w1 = dt.date.fromisoformat(W['start']), dt.date.fromisoformat(W['end'])
        if dt.date.fromisoformat(fr) > w0.replace(day=1) or dt.date.fromisoformat(to) < w1:
            C.fail(f'asked {fr} -> {to}, but the window is {w0} -> {w1}: ask again from {w0.replace(day=1)} to at least the end of {w1:%B}')
        posts = [x for x in (norm_post(p) for p in rows_of(C.load(f))) if x]
        C.save(cal(R, f'metricool_{b}.json'), {'at': C.now(), 'brand': b, 'from': fr, 'to': to, 'posts': sorted(posts, key=lambda x: x['at'])})
        print(f'{b}: {len(posts)} scheduled Metricool posts {fr} -> {to}'); C.event(R, f'CALENDAR metricool {b} {len(posts)}')
    elif cmd == 'besttimes':
        b, f = a[2], a[3]; raw = C.load(f); rows = []
        for x in (raw[b] if isinstance(raw, dict) and isinstance(raw.get(b), list) else rows_of(raw)):
            if isinstance(x.get('bestTimesByHour'), list):         # Metricool verbatim: dayOfWeek ISO (1 = Monday .. 7 = Sunday), one row per hour inside
                for h in x['bestTimesByHour']: rows.append({'dow': (int(x['dayOfWeek']) - 1) % 7, 'hour': int(h['hourOfDay']), 'value': float(h.get('value') or 0)})
                continue
            dow, hour, val = x.get('dow'), x.get('hour'), x.get('value')   # already flat: dow 0-6, 0 = Monday (how CWC_PodReels stored them)
            if dow is None or hour is None: continue
            rows.append({'dow': int(dow) % 7, 'hour': int(hour), 'value': float(val or 0)})
        if not rows: C.fail('no best-time rows found - save the connector\'s answer verbatim ({"data": [{"dayOfWeek", "bestTimesByHour": [..]}]})')
        C.save(cal(R, f'best_{b}.json'), {'at': C.now(), 'network': 'tiktok', 'rows': rows}); print(f'{b}: {len(rows)} best-time cells')
    elif cmd == 'counts':
        b = a[2]; mo, n = a[3].split('=')
        ev = a[a.index('--evidence') + 1] if '--evidence' in a else None; by = a[a.index('--by') + 1] if '--by' in a else None
        if not ev and not by: C.fail('counts needs --evidence <Metricool calendar screenshot> or --by "<Colden\'s words>"')
        if ev and not os.path.exists(ev): C.fail(f'evidence file not found: {ev}')
        if ev:
            keep = cal(R, f'counts_{b}_{mo}{os.path.splitext(ev)[1]}'); import shutil; shutil.copy2(ev, keep); ev = keep
        g = C.load(cal(R, f'counts_{b}.json')) or {}; g[mo] = {'n': int(n), 'evidence': ev, 'words': by, 'at': C.now()}
        C.save(cal(R, f'counts_{b}.json'), g); print(f'{b} {mo}: {n} posts used ({"screenshot " + ev if ev else "Colden: " + by})')
    elif cmd == 'peaks':
        b, f = a[2], a[3]; raw = open(f, encoding='utf-8').read().strip()
        try: data = json.loads(raw)
        except ValueError: C.fail('save exactly what studio_viewers_online.js returned (a JSON string)')
        if isinstance(data, str):
            if data.startswith('CARD_NOT_FOUND'): C.fail(f'the Studio card did not load ({data}) - check the login and the channel, read again')
            data = json.loads(data)
        days = {}
        for line in data.get('days', []):
            name, _, rest = line.partition(':'); dow = [d.lower() for d in C.DAYS].index(name.strip()[:3].lower())
            most, _, some = rest.partition('|')
            days[str(dow)] = {'most': hours(most.replace('MOST', '')), 'some': hours(some.replace('SOME', ''))}
        out = {'at': C.now(), 'channel_id': C.brands()[b]['youtube']['channel_id'], 'subtitle': data.get('subtitle'), 'days': days,
               'no_data': not any(v['most'] for v in days.values())}
        C.save(cal(R, f'peaks_{b}.json'), out)
        print(f'{b}: ' + ('NO viewer data on the card - clips fall back to 2 PM' if out['no_data'] else ', '.join(f'{C.DAYS[int(k)]} {min(v["most"])}:00' for k, v in sorted(days.items()) if v['most'])))
    elif cmd == 'show':
        y = C.load(cal(R, 'youtube.json'))
        print('youtube.json: ' + ('missing' if not y else f'{C.hours_old(cal(R, "youtube.json")):.1f} h old'))
        for b in ('cwc', 'tcl'):
            for v in (y or {}).get('channels', {}).get(b, []):
                if v.get('publish_at'): print(f'  {b} SCHEDULED {v["publish_at"]} {v["kind"]:5} {v["title"]}')
            m = C.load(cal(R, f'metricool_{b}.json'))
            print(f'metricool {b}: ' + ('missing' if not m else f'{len(m["posts"])} scheduled, {C.hours_old(cal(R, f"metricool_{b}.json")):.1f} h old'))
            for mo, v in month_counts(R, b).items(): print(f'  {b} {mo}: {v["used"] if v["used"] is not None else "?"}/{C.brands()[b]["metricool"]["month_cap"]} used ({v["source"]})')
            pk = C.load(cal(R, f'peaks_{b}.json'))
            print(f'peaks {b}: ' + ('missing' if not pk else ('no data' if pk['no_data'] else f'{C.hours_old(cal(R, f"peaks_{b}.json")):.1f} h old')))
    else: print(__doc__); sys.exit(1)

if __name__ == '__main__': main()
