"""plan.py build <RUN> [--now ISO] [--waive-scrape "<Colden's words>"]   |   plan.py show <RUN>
THE HOLISTIC POSTING PLAN: every finished product of the episode (CWC_PodClips' uploads, CWC_PodReels' shorts) placed
on ONE calendar for ONE approval, around what is already scheduled. Writes <RUN>/plan.json + plan.md; nothing is posted.
Placement (each rule's source is in references/rules.json):
  clips   YouTube only, around 2 PM ET; Colden's channel first: CWC clips spread over the window, news first, then
          push_order; one long-form per channel per day (what is already on YouTube counts); the same clip on TCL >= 48 h
          after its CWC slot, a TCL-only clip not before window start + 48 h; may spill <= 3 days past the window (flagged).
  shorts  one a day per brand in rank order (CWC_PodReels checked.json), extras as second posts on the best days >= 3 h
          apart, the hour from Metricool's best times (TikTok) for that brand and weekday; a short to both brands posts to
          TCL >= 1 h after CWC; never on a channel and day that has a clip of the same topic.
  input   <RUN>/holistic.json first: Claude's read of every product + the Monday data (overrides / holds with reasons).
  routes  YouTube (clips + Shorts) = the Data API: youtube_api after the audit, studio_manual before it (Colden uploads +
          schedules in Studio, the skill writes every piece of metadata). Facebook / Instagram / TikTok = ONE Metricool post
          per short per brand (identical text + media on every network - Colden 2026-10-03: "all 3 equal 1 as long as you
          don't make individual changes"), while the brand's month count is under its cap (20); after that = manual.
GATES (re-asserted on the finished plan - exit 1, or 2 = ask):
  both products delivered and current - the calendar fresh (<= 6 h) for both brands - the Monday scrape <= 8 days (2, or
  --waive-scrape) - every file on disk (2: NAS) - a clip master only on its stinger's channel - never the full episode -
  never YouTube through Metricool, networks from brands.json only - one long-form per channel per day - 48 h / 1 h rules -
  no same-topic short on a clip's day and channel - every slot >= now + min_lead - month caps - weekdays computed."""
import os, sys, json, math, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
import cal as CAL

H = dt.timedelta(hours=1)

def hm(d, hhmm): h, m = (int(x) for x in str(hhmm).split(':')); return dt.datetime.combine(d, dt.time(h, m), tzinfo=C.ET)
def et_date(iso): return dt.datetime.fromisoformat(str(iso).replace('Z', '+00:00')).astimezone(C.ET).date()
def et_dt(iso): return dt.datetime.fromisoformat(str(iso).replace('Z', '+00:00')).astimezone(C.ET)

# ------------------------------------------------------------------ inputs
def products(r):
    cw, rw = r['clips_work'], r['reels_work']; cd = C.clips_delivery(r); rd = C.reels_delivery(r)
    if not cd: C.fail('CWC_PodClips has not delivered (no delivery.json) - next.py says what is left')
    if C.mtime(f'{cw}/delivery.json') < C.mtime(f'{cw}/lock.json'): C.fail('CWC_PodClips delivery.json is older than its lock.json - package.py build again')
    if not rd: C.fail('CWC_PodReels has not delivered (no delivery.json) - its lock.py writes it')
    clips = []
    for c in cd.get('clips', []):
        ch = c['channel']
        if c.get('master_carries_stinger_of') and c['master_carries_stinger_of'] != ch: C.fail(f'{c["theme"]}: the {ch} upload carries the {c["master_carries_stinger_of"]} stinger')
        clips.append({'ref': c['theme'], 'brand': ch, 'title': c['titles']['A'], 'titles': c.get('titles'), 'thumbnails': c.get('thumbnails'),
                      'master': c['master'], 'thumb': c['thumbnails']['A'], 'captions': c.get('captions'), 'description': c.get('description', ''),
                      'tags': c.get('tags', []), 'playlists': c.get('playlists', []), 'category': c.get('category'), 'pinned': c.get('pinned_comment'),
                      'push_order': c.get('push_order', 99), 'news': c.get('news'), 'score': c.get('score'), 'needs': c.get('needs', []),
                      'ab_tests_plan': c.get('ab_tests_plan'), 'seconds': c.get('seconds')})
    rank = [x if isinstance(x, str) else x.get('id') for x in (C.load(f'{rw}/checked.json') or {}).get('deliver', [])]
    shorts, skipped = [], []
    for i, s in enumerate(rd.get('shorts', [])):
        bs = [b for b in (s.get('brands') or []) if b in ('cwc', 'tcl')]
        if not bs: skipped.append(f'{s["id"]} "{s["title"]}": destination {s.get("destination")} - not a CWC / TCL post (Todd = CWC_PodReels publish.py export)'); continue
        shorts.append({'ref': s['id'], 'title': s['title'], 'brands': bs, 'master': s['master'], 'cover': s.get('cover'), 'copy': s.get('copy') or {},
                       'rank': rank.index(s['id']) if s['id'] in rank else 100 + i})
    clips, shorts = holistic(r, clips, shorts, skipped)
    return clips, sorted(shorts, key=lambda s: s['rank']), skipped

def holistic(r, clips, shorts, skipped):
    """<RUN>/holistic.json - Claude's read of EVERY product of the episode together with the Monday scrape and the
    short-form data, written before the plan (Colden 2026-10-03: "take a thorough read through all the content
    holistically as well as utilizing the monday youtube and tiktok data to plan out the best cadence"):
      {"summary": "..", "overrides": [{"ref": "s04", "kind": "short", "rank": 1, "why": ".."},
                                      {"ref": "t03", "kind": "clip", "push_order": 1, "why": ".."}],
       "hold": [{"ref": "s06", "kind": "short", "why": ".."}], "notes": [".."]}
    GATES: it exists and is newer than both deliveries; every override / hold names a product that exists and carries a
    reason of >= 25 characters (the data point it rests on). A hold leaves the product out of THIS plan (on the card)."""
    R = C.run_dir(r['show'], r['ep_key']); p = f'{R}/holistic.json'; h = C.load(p)
    if not h: C.fail('holistic.json missing - read every product + the Monday scrape + data/shorts/summary.md first (SKILL.md step 5)')
    if C.mtime(p) < max(C.mtime(f'{r["clips_work"]}/delivery.json'), C.mtime(f'{r["reels_work"]}/delivery.json')): C.fail('holistic.json is older than a delivery - read again')
    if len(str(h.get('summary', ''))) < 40: C.fail('holistic.json: write the summary (what this episode has, what leads and why)')
    by = {('clip', c['ref']): [x for x in clips if x['ref'] == c['ref']] for c in clips}; by.update({('short', x['ref']): [x] for x in shorts})
    for o in list(h.get('overrides', [])) + list(h.get('hold', [])):
        if (o.get('kind'), o.get('ref')) not in by: C.fail(f'holistic.json names {o.get("kind")} {o.get("ref")} - not a delivered product')
        if len(str(o.get('why', ''))) < 25: C.fail(f'holistic.json {o["ref"]}: the reason must name the data it rests on (>= 25 characters)')
    for o in h.get('overrides', []):
        for x in by[(o['kind'], o['ref'])]:
            if o['kind'] == 'short' and 'rank' in o: x['rank'] = float(o['rank']) - 1.5      # rank is 1-based; lands just ahead of that place
            if o['kind'] == 'clip' and 'push_order' in o: x['push_order'] = float(o['push_order']) - 0.5
            x['override'] = o['why']
    held = {(o['kind'], o['ref']): o['why'] for o in h.get('hold', [])}
    for (k, ref), why in held.items(): skipped.append(f'HELD {k} {ref}: {why}')
    return [c for c in clips if ('clip', c['ref']) not in held], [x for x in shorts if ('short', x['ref']) not in held]

def spans(work):
    ph = {p['id']: (p['start'], p['end']) for p in (C.load(f'{work}/phrases.json', []) or [])}
    out = {}
    for t in (C.load(f'{work}/themes.json') or {}).get('themes', []):
        rngs = list(t.get('body') or []) + list(t.get('ranges') or []) + ([t['hook']] if isinstance(t.get('hook'), dict) and 'from' in t['hook'] else [])
        out[t['id']] = [(ph[x['from']][0], ph[x['to']][1]) for x in rngs if isinstance(x, dict) and x.get('from') in ph and x.get('to') in ph]
    return out

def overlap(a, b): return sum(max(0.0, min(x1, y1) - max(x0, y0)) for x0, x1 in a for y0, y1 in b)

def calendar(R, rule, now):
    yt = C.load(f'{R}/calendar/youtube.json')
    if not yt: C.fail('calendar/youtube.json missing - cal.py youtube first')
    if C.hours_old(f'{R}/calendar/youtube.json') > rule['youtube_calendar_staleness_hours']: C.fail('calendar/youtube.json is stale - cal.py youtube again')
    long_busy, yt_shorts, mc_times, best = {}, {}, {}, {}
    for b in ('cwc', 'tcl'):
        vids = yt['channels'].get(b, [])
        when = lambda v: v.get('start_at') or v.get('publish_at') or v.get('published_at')
        long_busy[b] = {et_date(when(v)): v['title'] for v in vids if v['kind'] in ('long', 'live') and when(v)}
        yt_shorts[b] = {}
        for v in vids:
            if v['kind'] == 'short' and when(v): yt_shorts[b].setdefault(et_date(when(v)), []).append(et_dt(when(v)))
        p = f'{R}/calendar/metricool_{b}.json'; m = C.load(p)
        if not m: C.fail(f'calendar/metricool_{b}.json missing - getScheduledPosts on the {b} connector -> cal.py metricool')
        if C.hours_old(p) > rule['metricool_staleness_hours']: C.fail(f'calendar/metricool_{b}.json is stale - read it again')
        mc_times[b] = {}
        for x in m['posts']: mc_times[b].setdefault(dt.datetime.fromisoformat(x['at']).date(), []).append(dt.datetime.fromisoformat(x['at']))
        best[b] = (C.load(f'{R}/calendar/best_{b}.json') or {}).get('rows', [])
    return long_busy, yt_shorts, mc_times, best

# ------------------------------------------------------------------ placement
class Planner:
    def __init__(s, r, R, rule, now):
        s.r, s.R, s.rule, s.now = r, R, rule, now
        s.earliest = now + dt.timedelta(minutes=rule['min_lead_minutes'])
        s.w0, s.w1 = dt.date.fromisoformat(r['window']['start']), dt.date.fromisoformat(r['window']['end'])
        s.days = [s.w0 + dt.timedelta(days=i) for i in range((s.w1 - s.w0).days + 1)]
        s.spill = [s.w1 + dt.timedelta(days=i + 1) for i in range(rule['spill_days_max'])]
        s.long_busy, s.yt_shorts, s.mc_times, s.best = calendar(R, rule, now)
        s.items, s.warn, s.long = [], [], {'cwc': {}, 'tcl': {}}
        s.short_at = {'cwc': {}, 'tcl': {}}

    def long_free(s, b, d): return d not in s.long_busy[b] and d not in s.long[b]

    def place_clips(s, clips):
        T = s.rule['clip_time_et']; slot = {}
        prim = sorted([c for c in clips if c['brand'] == 'cwc'], key=lambda c: (0 if c['news'] else 1, c['push_order']))
        n = len(prim); targets = [min(len(s.days) - 1, round(i * len(s.days) / n)) for i in range(n)]
        for k, c in enumerate(prim):
            t0 = 0 if c['news'] else targets[k]
            order = s.days[t0:] + s.days[:t0][::-1]
            d = next((d for d in order if s.long_free('cwc', d) and hm(d, T) >= s.earliest), None)
            if not d: C.ask(f'no free long-form day left on Create with Colden for {c["ref"]} "{c["title"]}" in the window (busy: {sorted(map(str, s.long_busy["cwc"]))})')
            s.long['cwc'][d] = c['ref']; slot[c['ref']] = hm(d, T); s.add_clip(c, hm(d, T))
        sec = sorted([c for c in clips if c['brand'] == 'tcl'], key=lambda c: (0 if c['news'] else 1, c['push_order']))
        delay = dt.timedelta(hours=s.rule['secondary_min_delay_hours'])
        for c in sec:
            floor = max(s.earliest, (slot[c['ref']] + delay) if c['ref'] in slot else hm(s.w0, '00:00') + delay)
            d = next((d for d in s.days + s.spill if s.long_free('tcl', d) and hm(d, T) >= floor), None)
            if not d: C.ask(f'{c["ref"]} on The Creative Lens: no free day within {s.rule["spill_days_max"]} days after the window with the 48 h delay')
            if d > s.w1: s.warn.append(f'{c["ref"]} TCL spills past the window to {C.DAYS[d.weekday()]} {d} (48 h after its CWC slot)')
            s.long['tcl'][d] = c['ref']; s.add_clip(c, hm(d, T))

    def add_clip(s, c, t):
        s.items.append({'id': f'clip-{c["ref"]}-{c["brand"]}', 'kind': 'yt_clip', 'product': 'clip', 'ref': c['ref'], 'brand': c['brand'],
                        'route': s.yt_route(), 'publish_at': t.isoformat(), 'title': c['title'], 'description': c['description'],
                        'tags': c['tags'], 'playlists': c['playlists'], 'category': c['category'], 'pinned_comment': c['pinned'],
                        'files': {'video': c['master'], 'thumb': c['thumb'], 'captions': c['captions']},
                        'ab': {'titles': c['titles'], 'thumbnails': c['thumbnails'], 'plan': c['ab_tests_plan']},
                        'news': bool(c['news']), 'push_order': c['push_order'], 'needs': c['needs']})

    def yt_route(s): return 'youtube_api' if s.rule['youtube_audit_passed'] else 'studio_manual'

    def hours(s, b, dow):
        rows = sorted([x for x in s.best[b] if x['dow'] == dow], key=lambda x: -x['value'])
        hs = [x['hour'] for x in rows]
        return hs + [h for h in s.rule['short_default_hours_et'] if h not in hs]

    def day_score(s, b, d): return max([x['value'] for x in s.best[b] if x['dow'] == d.weekday()] or [0.0])

    def taken(s, b, d): return s.short_at[b].get(d, []) + s.mc_times[b].get(d, []) + s.yt_shorts[b].get(d, [])

    def pick(s, b, d, floor):
        gap = s.rule['shorts_extra_gap_hours'] * 3600
        for h in s.hours(b, d.weekday()):
            t = hm(d, f'{h}:00')
            if t >= floor and all(abs((t - x).total_seconds()) >= gap for x in s.taken(b, d)): return t
        return None

    def clash(s, b, d, short, same_topic):
        return [ref for dd, ref in s.long[b].items() if dd == d and same_topic(ref, short['ref'])]

    def place_shorts(s, shorts, same_topic):
        cwc_at = {}
        for b in ('cwc', 'tcl'):
            for sh in [x for x in shorts if b in x['brands']]:
                floor = max(s.earliest, cwc_at[sh['ref']] + s.rule['short_secondary_lead_hours'] * H) if (b == 'tcl' and sh['ref'] in cwc_at) else s.earliest
                t = None
                for d in s.days:                                       # pass 1: an empty day, in order
                    if len(s.taken(b, d)) < s.rule['shorts_per_brand_per_day'] and not s.clash(b, d, sh, same_topic) and (t := s.pick(b, d, floor)): break
                if not t:                                              # pass 2: a second post on the best days, >= 3 h apart
                    for d in sorted(s.days, key=lambda d: -s.day_score(b, d)):
                        if len(s.taken(b, d)) < s.rule['shorts_per_brand_per_day'] + 1 and not s.clash(b, d, sh, same_topic) and (t := s.pick(b, d, floor)): break
                if not t: C.ask(f'no slot left for short {sh["ref"]} "{sh["title"]}" on {b} in the window - drop one or widen the window (his call)')
                s.short_at[b].setdefault(t.date(), []).append(t)
                if b == 'cwc': cwc_at[sh['ref']] = t
                cp = sh['copy']
                s.items.append({'id': f'yts-{sh["ref"]}-{b}', 'kind': 'yt_short', 'product': 'short', 'ref': sh['ref'], 'brand': b, 'route': s.yt_route(),
                                'publish_at': t.isoformat(), 'title': cp.get('yt_title') or sh['title'], 'description': cp.get('caption') or '',
                                'tags': [], 'playlists': [p for p in [s.short_playlist(b, cp.get('playlist'))] if p], 'category': None,
                                'files': {'video': sh['master'], 'thumb': sh['cover'], 'captions': None}, 'rank': sh['rank']})
                s.items.append({'id': f'mc-{sh["ref"]}-{b}', 'kind': 'social', 'product': 'short', 'ref': sh['ref'], 'brand': b, 'route': None,
                                'publish_at': t.isoformat(), 'title': sh['title'], 'text': cp.get('caption') or '', 'first_comment': cp.get('first_comment'),
                                'networks': list(C.brands()[b]['metricool']['networks']),
                                'fb_title': cp.get('fb_title') if b == 'cwc' else None, 'ig_collab': cp.get('ig_collab') if b == 'cwc' else None,
                                'files': {'video': sh['master'], 'thumb': sh['cover']}, 'rank': sh['rank']})

    def short_playlist(s, b, key):
        sh = C.load(f'{C.REELS_SK}/shows/{s.r["show"]}.json') or {}
        mc = ((sh.get('publishing') or {}).get('metricool') or {}).get(b) or {}
        key = key or mc.get('default_playlist')
        if not key: return None
        if str(key).startswith('PL'): return key
        hit = (mc.get('playlists') or {}).get(key)
        if not hit: s.warn.append(f'short playlist "{key}" is not on file for {b} - none set'); return None
        return hit['id']

    def caps(s):
        counts = {b: CAL.month_counts(s.R, b) for b in ('cwc', 'tcl')}; used = {b: {m: v['used'] for m, v in counts[b].items()} for b in counts}
        out = {b: {m: {'used_before': v['used'], 'source': v['source'], 'planned_metricool': 0, 'manual': 0, 'cap': C.brands()[b]['metricool']['month_cap']} for m, v in counts[b].items()} for b in counts}
        for it in sorted([i for i in s.items if i['kind'] == 'social'], key=lambda i: (i['brand'], i['rank'])):
            b, mo = it['brand'], it['publish_at'][:7]; cap = C.brands()[b]['metricool']['month_cap']
            u = used[b].setdefault(mo, 0); out[b].setdefault(mo, {'used_before': 0, 'source': 'no count', 'planned_metricool': 0, 'manual': 0, 'cap': cap})
            if u + 1 <= cap: it['route'] = 'metricool'; used[b][mo] = u + 1; out[b][mo]['planned_metricool'] += 1
            else: it['route'] = 'manual'; out[b][mo]['manual'] += 1
        return out

# ------------------------------------------------------------------ gates on the finished plan
def validate(P, items, same_topic):
    rule = P.rule; B = C.brands(); bad = []
    for it in items:
        t = dt.datetime.fromisoformat(it['publish_at'])
        if it['weekday'] != C.DAYS[t.weekday()]: bad.append(f'{it["id"]}: weekday {it["weekday"]} != {C.DAYS[t.weekday()]}')
        if t < P.earliest: bad.append(f'{it["id"]}: {t} is sooner than now + {rule["min_lead_minutes"]} min')
        if it['kind'] not in ('yt_clip', 'yt_short', 'social'): bad.append(f'{it["id"]}: kind {it["kind"]} (the full episode stays the live stream)')
        if it['kind'] == 'social':
            if 'youtube' in it['networks']: bad.append(f'{it["id"]}: YouTube through Metricool')
            if set(it['networks']) - set(B[it['brand']]['metricool']['networks']): bad.append(f'{it["id"]}: networks {it["networks"]} not all on {it["brand"]}')
            if it['route'] not in ('metricool', 'manual'): bad.append(f'{it["id"]}: route {it["route"]}')
            if not it['text']: bad.append(f'{it["id"]}: no caption')
        else:
            if it['route'] != P.yt_route(): bad.append(f'{it["id"]}: route {it["route"]}')
            for k in ('video', 'thumb') + (('captions',) if it['kind'] == 'yt_clip' else ()):
                f = (it['files'] or {}).get(k)
                if not f or not os.path.exists(f): bad.append(f'{it["id"]}: {k} file missing: {f}')
    for b in ('cwc', 'tcl'):
        days = {}
        for it in items:
            if it['kind'] == 'yt_clip' and it['brand'] == b: days.setdefault(it['publish_at'][:10], []).append(it['id'])
        for d, ids in days.items():
            if len(ids) > rule['long_form_per_channel_per_day']: bad.append(f'{b} {d}: {len(ids)} long-form ({ids})')
            if dt.date.fromisoformat(d) in P.long_busy[b]: bad.append(f'{b} {d}: already has "{P.long_busy[b][dt.date.fromisoformat(d)]}" on YouTube')
    at = {(i['ref'], i['brand'], i['kind']): dt.datetime.fromisoformat(i['publish_at']) for i in items}
    for (ref, b, k), t in at.items():
        if k == 'yt_clip' and b == 'tcl' and (ref, 'cwc', k) in at and t - at[(ref, 'cwc', k)] < dt.timedelta(hours=rule['secondary_min_delay_hours']): bad.append(f'clip {ref}: TCL < 48 h after CWC')
        if k == 'yt_short' and b == 'tcl' and (ref, 'cwc', k) in at and t - at[(ref, 'cwc', k)] < rule['short_secondary_lead_hours'] * H: bad.append(f'short {ref}: TCL < 1 h after CWC')
        if k == 'yt_short':
            for (r2, b2, k2), t2 in at.items():
                if k2 == 'yt_clip' and b2 == b and t2.date() == t.date() and same_topic(r2, ref): bad.append(f'short {ref} on {b} {t.date()} = the day of same-topic clip {r2}')
    for b, months in P.cap_table.items():
        for mo, v in months.items():
            if v['used_before'] + v['planned_metricool'] > v['cap']: bad.append(f'{b} {mo}: Metricool {v["used_before"]} + {v["planned_metricool"]} > cap {v["cap"]}')
    if bad: C.fail('the plan breaks its own rules:\n  ' + '\n  '.join(bad))

def quota(P, items):
    q = C.rules()['quota_cost']; per = {}
    for it in items:
        if it['kind'] == 'social': continue
        n = (q['videos.insert'] if it['route'] == 'youtube_api' else q['videos.update'] + q['videos.list']) + q['thumbnails.set'] + len(it.get('playlists') or []) * q['playlistItems.insert']
        if it['files'].get('captions'): n += q['captions.insert']
        per[it['id']] = n
    limit = C.rules()['quota_daily_limit']; nights, cur, day = [], 0, 0
    for it in sorted([i for i in items if i['id'] in per], key=lambda i: i['publish_at']):
        if cur + per[it['id']] > limit: day += 1; cur = 0
        cur += per[it['id']]; it['quota_night'] = day
        if it['route'] == 'youtube_api' and (P.now.date() + dt.timedelta(days=day)) >= dt.datetime.fromisoformat(it['publish_at']).date():
            C.ask(f'{it["id"]}: the API quota only reaches it on night {day + 1}, on or after its publish day - spread the plan or raise the quota')
    return {'units': sum(per.values()), 'nights': day + 1, 'limit': limit, 'per_item': per}

def md(plan):
    L = [f'# Posting plan {plan["show"]} {plan["ep_key"]}', '', f'Window {plan["window"]["start_dow"]} {plan["window"]["start"]} -> {plan["window"]["end_dow"]} {plan["window"]["end"]} (ET). YouTube route: {plan["youtube_route"]}. sha {plan["sha"]}', '']
    day = None
    for it in plan['items']:
        d = it['publish_at'][:10]
        if d != day: day = d; L += ['', f'## {it["weekday"]} {d}']
        what = {'yt_clip': 'YouTube clip', 'yt_short': 'YouTube Short', 'social': '+'.join(it.get('networks', []))}[it['kind']]
        L.append(f'- {it["publish_at"][11:16]} {C.brands()[it["brand"]]["label"]} | {what} | {it["route"]} | {it["title"]}')
    L += ['', '## Metricool month counts']
    for b, ms in plan['counts'].items():
        for mo, v in ms.items(): L.append(f'- {C.brands()[b]["label"]} {mo}: {v["used_before"]} used + {v["planned_metricool"]} planned / {v["cap"]}; {v["manual"]} manual ({v["source"]})')
    if plan['warnings']: L += ['', '## Notes'] + [f'- {w}' for w in plan['warnings']]
    if plan['skipped']: L += ['', '## Not in this plan'] + [f'- {w}' for w in plan['skipped']]
    return '\n'.join(L) + '\n'

def build(R, now=None, waive=None):
    r = C.run(R); rule = C.rules()
    now = C.et(now) if now else dt.datetime.now(C.ET)
    p, scr = C.scrape()
    if not scr: C.ask('channel_metrics.json (the Monday scrape) not found')
    age = (now.date() - dt.date.fromisoformat(str(scr.get('updated'))[:10])).days
    if age > rule['scrape_max_age_days'] and not waive: C.ask(f'the Monday scrape is {age} days old ({p}) - run it, or --waive-scrape "<Colden\'s words>"')
    clips, shorts, skipped = products(r)
    for c in clips + shorts:
        for f in (c['master'], c.get('thumb') or c.get('cover')):
            if f and not os.path.exists(f): C.ask(f'not on disk (NAS mounted?): {f}')
    cs, rs = spans(r['clips_work']), spans(r['reels_work'])
    thr = rule['same_topic_overlap_sec']
    def same_topic(clip_ref, short_ref): return overlap(cs.get(clip_ref, []), rs.get(short_ref, [])) >= thr
    P = Planner(r, R, rule, now)
    P.place_clips(clips); P.place_shorts(shorts, same_topic); P.cap_table = P.caps()
    items = sorted(P.items, key=lambda i: (i['publish_at'], i['id']))
    for it in items:
        t = dt.datetime.fromisoformat(it['publish_at']); it['weekday'] = C.DAYS[t.weekday()]
    validate(P, items, same_topic)
    qu = quota(P, items)
    if any(c['needs'] for c in clips): P.warn.append('clip descriptions still hold {FULL_EPISODE_URL}: youtube.py fills it from the public "Ep. NN" live (no phone emoji) before writing')
    if scr: P.warn.append(f'data: Monday scrape {scr.get("updated")}, best slots {(scr.get("audience") or {}).get("best_slots_et")}')
    plan = {'version': 1, 'rules': C.RULES, 'built_at': C.now(), 'now': now.isoformat(timespec='minutes'), 'show': r['show'], 'ep_key': r['ep_key'],
            'window': r['window'], 'youtube_route': P.yt_route(), 'items': items, 'counts': P.cap_table, 'quota': qu,
            'warnings': P.warn, 'skipped': skipped, 'scrape': {'path': p, 'updated': scr.get('updated'), 'waiver': waive}}
    plan['sha'] = C.sha({'items': items, 'rules': C.RULES})
    C.save(f'{R}/plan.json', plan); open(f'{R}/plan.md', 'w', encoding='utf-8').write(md(plan))
    r.setdefault('stages', {})['plan'] = {'sha': plan['sha'], 'at': plan['built_at']}; C.save_run(R, r); C.event(R, f'PLAN BUILT {plan["sha"]} {len(items)} items')
    return plan

def main():
    a = sys.argv[1:]
    if len(a) < 2 or a[0] not in ('build', 'show'): print(__doc__); sys.exit(1)
    R = a[1].rstrip('/')
    if a[0] == 'build':
        plan = build(R, a[a.index('--now') + 1] if '--now' in a else None, a[a.index('--waive-scrape') + 1] if '--waive-scrape' in a else None)
    else:
        plan = C.load(f'{R}/plan.json') or C.fail('no plan.json yet')
    print(md(plan))
    if a[0] == 'build': print(f'next: python3 {C.SK}/scripts/tg_plan.py send "{R}"')

if __name__ == '__main__': main()
