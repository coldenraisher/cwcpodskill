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
  cal.py counts <RUN> <cwc|tcl> <YYYY-MM>=<n> ["<Colden's words>"]
        Colden's own number of Metricool posts used in a month (Metricool shows it). Wins over the computed count.
  cal.py show <RUN>

Month counts (the 20-post cap per Metricool account): getScheduledPosts returns only posts NOT yet published, so the
count is: posts this skill created in that month (data/metricool_ledger.jsonl) + scheduled posts it did not create
(same post id never counted twice), unless Colden gave the number (counts). The plan card shows the count for him to
confirm - a manual post in Metricool that already went out is the one thing the skill cannot see."""
import os, sys, json, datetime as dt
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
    return {'id': str(first(p, 'id', 'postId', 'uuid') or ''), 'at': d.astimezone(C.ET).isoformat(timespec='minutes'),
            'networks': nets, 'text': (p.get('text') or '')[:80]}

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
    """{month: {"used": n, "source": ".."}} for the window's months"""
    r = C.run(R); w0, w1 = dt.date.fromisoformat(r['window']['start']), dt.date.fromisoformat(r['window']['end'])
    mc = C.load(cal(R, f'metricool_{brand}.json')) or {'posts': []}; given = (C.load(cal(R, f'counts_{brand}.json')) or {})
    out = {}
    for mo in months_between(w0, w1 + dt.timedelta(days=C.rules()['spill_days_max'])):
        if mo in given: out[mo] = {'used': given[mo]['n'], 'source': f'Colden: {given[mo]["words"]}'}; continue
        ids = {x['post_id'] for x in ledger(brand) if str(x.get('publish_at', ''))[:7] == mo}
        sched = {p['id'] or p['at'] for p in mc['posts'] if p['at'][:7] == mo}
        out[mo] = {'used': len(ids | sched), 'source': f'{len(ids)} created by CWC_PodRun + {len(sched - ids)} other scheduled (published posts made outside the skill are not visible)'}
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
        w0, w1 = dt.date.fromisoformat(r['window']['start']), dt.date.fromisoformat(r['window']['end'])
        if dt.date.fromisoformat(fr) > w0.replace(day=1) or dt.date.fromisoformat(to) < w1:
            C.fail(f'asked {fr} -> {to}, but the window is {w0} -> {w1}: ask again from {w0.replace(day=1)} to at least the end of {w1:%B}')
        posts = [x for x in (norm_post(p) for p in rows_of(C.load(f))) if x]
        C.save(cal(R, f'metricool_{b}.json'), {'at': C.now(), 'brand': b, 'from': fr, 'to': to, 'posts': sorted(posts, key=lambda x: x['at'])})
        print(f'{b}: {len(posts)} scheduled Metricool posts {fr} -> {to}'); C.event(R, f'CALENDAR metricool {b} {len(posts)}')
    elif cmd == 'besttimes':
        b, f = a[2], a[3]; raw = C.load(f); rows = []
        for x in (raw[b] if isinstance(raw, dict) and isinstance(raw.get(b), list) else rows_of(raw)):
            dow = first(x, 'dow', 'dayOfWeek', 'day', 'weekday'); hour = first(x, 'hour', 'hourOfDay'); val = first(x, 'value', 'score', 'count')
            if dow is None or hour is None: continue
            if isinstance(dow, str) and not dow.isdigit(): dow = [d.lower() for d in C.DAYS].index(dow[:3].lower())
            rows.append({'dow': int(dow) % 7, 'hour': int(hour), 'value': float(val or 0)})
        if not rows: C.fail('no {dow, hour, value} rows found - write the file as [{"dow": 0-6 (0 = Monday), "hour": 0-23, "value": n}, ...]')
        C.save(cal(R, f'best_{b}.json'), {'at': C.now(), 'network': 'tiktok', 'rows': rows}); print(f'{b}: {len(rows)} best-time cells')
    elif cmd == 'counts':
        b = a[2]; mo, n = a[3].split('='); words = a[4] if len(a) > 4 else C.fail('his words are required: counts <RUN> <brand> YYYY-MM=n "<what Colden said>"')
        g = C.load(cal(R, f'counts_{b}.json')) or {}; g[mo] = {'n': int(n), 'words': words, 'at': C.now()}; C.save(cal(R, f'counts_{b}.json'), g); print(f'{b} {mo}: {n} used (Colden)')
    elif cmd == 'show':
        y = C.load(cal(R, 'youtube.json'))
        print('youtube.json: ' + ('missing' if not y else f'{C.hours_old(cal(R, "youtube.json")):.1f} h old'))
        for b in ('cwc', 'tcl'):
            for v in (y or {}).get('channels', {}).get(b, []):
                if v.get('publish_at'): print(f'  {b} SCHEDULED {v["publish_at"]} {v["kind"]:5} {v["title"]}')
            m = C.load(cal(R, f'metricool_{b}.json'))
            print(f'metricool {b}: ' + ('missing' if not m else f'{len(m["posts"])} scheduled, {C.hours_old(cal(R, f"metricool_{b}.json")):.1f} h old'))
            for mo, v in month_counts(R, b).items(): print(f'  {b} {mo}: {v["used"]}/{C.brands()[b]["metricool"]["month_cap"]} used ({v["source"]})')
    else: print(__doc__); sys.exit(1)

if __name__ == '__main__': main()
