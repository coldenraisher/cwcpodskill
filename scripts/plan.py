"""plan.py build <RUN> [--now ISO] [--waive-scrape "<Colden's words>"]   |   plan.py show <RUN>
THE HOLISTIC POSTING PLAN: every finished product of the episode (CWC_PodClips' uploads, CWC_PodReels' reels) placed on
ONE calendar for ONE approval, inside the window Colden gave, around what is already scheduled. Writes <RUN>/plan.json +
plan.md; nothing is posted. Each rule's source is in references/rules.json.
  window  the span Colden confirmed (window.py) - never assumed, never one that has already started
  input   <RUN>/holistic.json: Claude's read of every product + the Monday data (overrides / holds, each with its reason)
  clips   YouTube only. CWC spread over the window, news first then push_order, one long-form per channel per day (what is
          already on YouTube counts, lives too). Time = 30 min before that weekday's viewer peak from Studio, read fresh
          (cal.py peaks); 14:00 only for a channel Studio has no data for. The same clip on both: TCL any time >= 48 h after
          CWC (CWC slots for shared clips stay early enough for that). TCL-only: no delay.
  reels   one a day per brand in rank order, extras as second posts on the best days >= 3 h apart, at that brand's best
          TikTok hour (Metricool). The same reel on both: TCL >= 48 h after CWC. TCL-only: no delay. Never on a channel +
          day that has a clip of the same topic (measured overlap on the locked cut).
  collabs Instagram collaborators from WHO SPEAKS in the reel (CWC_PodReels phrases): everyone with a real line (a phrase
          of >= 3 words - a "yeah" is not a line) except Colden; ONE set per reel, on the CWC post when the reel plays on
          both, else on the one brand it plays on. A speaker with no handle on file = ask.
  routes  YouTube (clips + Shorts): uploaded through the API with every piece of metadata; before the audit they stay
          private and Colden flips each to Scheduled at the time on the dashboard; after it publishAt is set at upload.
          Which of the two: data/youtube_route.json (youtube.py flip-test / route) - not settled or locked = ask.
          The API quota paces uploads (a slot the quota cannot reach in time = ask). FB / IG / TikTok: ONE Metricool post
          per reel per brand (one caption, one video, every network of that brand) while the month count is under 20
          (resets on the 1st; the count is confirmed from the Metricool calendar, cal.py counts); over it = manual kit.
GATES (re-asserted on the finished plan - exit 1, or 2 = ask): confirmed window - both products delivered and current -
holistic read newer than both - calendar <= 6 h - viewer peaks <= 24 h - month counts confirmed <= 12 h - Monday scrape
<= 8 days (2, or --waive-scrape) - files on disk (2: NAS) - a clip master only on its stinger's channel - never the full
episode - never YouTube in Metricool, networks from brands.json - one long-form per channel per day - 48 h rules - same
topic apart - lead time - caps - one collaborator set per reel, never on TCL when the reel is on CWC - weekdays computed."""
import os, re, sys, json, subprocess, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
import cal as CAL

def yt_schedule():
    """how a YouTube item is scheduled - data/youtube_route.json (youtube.py flip-test / route), never assumed"""
    st = C.youtube_route().get('state')
    if st == 'audit_passed': return 'publishAt'
    if st == 'flip_works': return 'flip'
    if st == 'locked': C.ask('YouTube: API uploads from this project are locked private and cannot be switched to Scheduled (the flip test, data/youtube_route.json) - '
                             'nothing this skill uploads could go live. The route is Colden\'s call: wait for the audit, or upload in Studio.')
    C.ask('YouTube: the upload route is not settled yet - python3 scripts/youtube.py flip-test <cwc|tcl>, Colden tries the flip in Studio, '
          'then youtube.py route flip_works|locked --by "<his words>"' + (f' (a test video is up: {C.youtube_route()["test"]["url"]})' if st == 'test_uploaded' else ''))

def hm(d, hhmm): h, m = (int(x) for x in str(hhmm).split(':')); return dt.datetime.combine(d, dt.time(h, m), tzinfo=C.ET)
def et_date(iso): return dt.datetime.fromisoformat(str(iso).replace('Z', '+00:00')).astimezone(C.ET).date()
def et_dt(iso): return dt.datetime.fromisoformat(str(iso).replace('Z', '+00:00')).astimezone(C.ET)

# ------------------------------------------------------------------ products
def clips_in(r):
    cw = r['clips_work']; cd = C.clips_delivery(r)
    if not cd: C.fail('CWC_PodClips has not delivered (no delivery.json) - next.py says what is left')
    if C.mtime(f'{cw}/delivery.json') < C.mtime(f'{cw}/lock.json'): C.fail('CWC_PodClips delivery.json is older than its lock.json - package.py build again')
    out = []
    for c in cd.get('clips', []):
        ch = c['channel']
        if c.get('master_carries_stinger_of') and c['master_carries_stinger_of'] != ch: C.fail(f'{c["theme"]}: the {ch} upload carries the {c["master_carries_stinger_of"]} stinger')
        pls = [p.get('id') if isinstance(p, dict) else p for p in c.get('playlists', [])]      # delivery v2: [{"title", "id"}]
        cat = c['category'].get('id') if isinstance(c.get('category'), dict) else c.get('category')   # delivery v2: {"id", "name", "note"}
        if not all(pls) or not cat: C.fail(f'{c["theme"]} {ch}: a playlist without an id or no category in CWC_PodClips delivery.json')
        c = dict(c, playlists=pls, category=str(cat))
        out.append({'ref': c['theme'], 'brand': ch, 'title': c['titles']['A'], 'titles': c.get('titles'), 'thumbnails': c.get('thumbnails'),
                    'master': c['master'], 'thumb': c['thumbnails']['A'], 'captions': c.get('captions'), 'description': c.get('description', ''),
                    'tags': c.get('tags', []), 'playlists': c.get('playlists', []), 'category': c.get('category'), 'pinned': c.get('pinned_comment'),
                    'push_order': c.get('push_order', 99), 'news': c.get('news'), 'needs': c.get('needs', []), 'ab_tests_plan': c.get('ab_tests_plan')})
    return out

def reels_in(r, skipped):
    """CWC_PodReels' delivery.json as its lock.py + deliver.py write it (references/podreels_handoff.md): "shorts" = one
    entry per short with `brands`, the master and the PICKED cover in <episode>/Final/Reels, and its approved copy."""
    rw = r['reels_work']; rd = C.reels_delivery(r)
    if not rd: C.fail('CWC_PodReels has not delivered (delivery.json with final_dir + delivered_at) - next.py says what is left')
    rank = [x if isinstance(x, str) else x.get('id') for x in (C.load(f'{rw}/checked.json') or {}).get('deliver', [])]
    out = []
    for i, s in enumerate(rd.get('shorts') or []):
        sid = s.get('id'); bs = [b for b in (s.get('brands') or []) if b in ('cwc', 'tcl')]
        if not bs: skipped.append(f'reel {sid} "{s.get("title")}": destination {s.get("destination") or s.get("brands")} - not a CWC / TCL post (Todd = export only)'); continue
        cp = dict(s.get('copy') or {}); cp['yt_title'] = cp.get('yt_title') or s.get('yt_title') or s.get('title')
        if not cp.get('caption'): C.fail(f'reel {sid}: no caption in CWC_PodReels delivery.json - its cover + copy card is not approved')
        out.append({'ref': sid, 'title': s.get('title') or cp['yt_title'], 'brands': bs, 'copy': {b: cp for b in bs},
                    'files': {b: {'video': s.get('master'), 'thumb': s.get('cover')} for b in bs},
                    'rank': rank.index(sid) if sid in rank else 100 + i})
    return out

def holistic(R, r, clips, reels, skipped):
    """<RUN>/holistic.json - Claude's read of EVERY product together with the Monday scrape + short-form data (Colden
    2026-10-03: "take a thorough read through all the content holistically as well as utilizing the monday youtube and
    tiktok data to plan out the best cadence"):
      {"summary": "..", "overrides": [{"ref": "s04", "kind": "short", "rank": 1, "why": ".."},
                                      {"ref": "t03", "kind": "clip", "push_order": 1, "why": ".."}],
       "hold": [{"ref": "s06", "kind": "short", "why": ".."}], "notes": [".."]}
    GATES: newer than both deliveries; every override / hold names a delivered product with a >= 25-character reason."""
    p = f'{R}/holistic.json'; h = C.load(p)
    if not h: C.fail('holistic.json missing - read every product + the Monday scrape + data/shorts/summary.md first (SKILL.md step 6)')
    if C.mtime(p) < max(C.mtime(f'{r["clips_work"]}/delivery.json'), C.mtime(f'{r["reels_work"]}/delivery.json')): C.fail('holistic.json is older than a delivery - read again')
    if len(str(h.get('summary', ''))) < 40: C.fail('holistic.json: write the summary (what this episode has, what leads and why)')
    by = {}
    for c in clips: by.setdefault(('clip', c['ref']), []).append(c)
    for x in reels: by[('short', x['ref'])] = [x]
    for o in list(h.get('overrides', [])) + list(h.get('hold', [])):
        if (o.get('kind'), o.get('ref')) not in by: C.fail(f'holistic.json names {o.get("kind")} {o.get("ref")} - not a delivered product')
        if len(str(o.get('why', ''))) < 25: C.fail(f'holistic.json {o["ref"]}: the reason must name the data it rests on (>= 25 characters)')
    for o in h.get('overrides', []):
        for x in by[(o['kind'], o['ref'])]:
            if o['kind'] == 'short' and 'rank' in o: x['rank'] = float(o['rank']) - 1.5          # 1-based place; lands just ahead of it
            if o['kind'] == 'clip' and 'push_order' in o: x['push_order'] = float(o['push_order']) - 0.5
    held = {(o['kind'], o['ref']): o['why'] for o in h.get('hold', [])}
    for (k, ref), why in held.items(): skipped.append(f'HELD {k} {ref}: {why}')
    return [c for c in clips if ('clip', c['ref']) not in held], [x for x in reels if ('short', x['ref']) not in held]

# ------------------------------------------------------------------ the locked cut: topics + speakers
def theme_ranges(t): return [x for x in list(t.get('body') or []) + list(t.get('ranges') or []) if isinstance(x, dict) and x.get('from')]

def spans(work):
    ph = {p['id']: (p['start'], p['end']) for p in (C.load(f'{work}/phrases.json', []) or [])}
    out = {}
    for t in (C.load(f'{work}/themes.json') or {}).get('themes', []):
        rngs = theme_ranges(t) + ([t['hook']] if isinstance(t.get('hook'), dict) and 'from' in t['hook'] else [])
        out[t['id']] = [(ph[x['from']][0], ph[x['to']][1]) for x in rngs if x.get('from') in ph and x.get('to') in ph]
    return out

def overlap(a, b): return sum(max(0.0, min(x1, y1) - max(x0, y0)) for x0, x1 in a for y0, y1 in b)

def speakers(work, ref):
    """{who: longest line in words} inside the reel's ranges (start_word / end_word respected at the edges)"""
    phs = C.load(f'{work}/phrases.json', []) or []; idx = {p['id']: i for i, p in enumerate(phs)}
    th = next((t for t in (C.load(f'{work}/themes.json') or {}).get('themes', []) if t.get('id') == ref), None)
    if not th or not theme_ranges(th): C.ask(f'reel {ref}: no ranges in CWC_PodReels themes.json - cannot tell who speaks in it (collaborators are never guessed)')
    out = {}
    for rg in theme_ranges(th):
        a, b = idx.get(rg['from']), idx.get(rg['to'])
        if a is None or b is None: C.ask(f'reel {ref}: range {rg["from"]}..{rg["to"]} is not in phrases.json')
        for i in range(a, b + 1):
            p = phs[i]; who = p.get('who')
            if not who: C.ask(f'reel {ref}: phrase {p["id"]} has no speaker - cannot set collaborators')
            words = p.get('w') if isinstance(p.get('w'), list) else str(p.get('text', '')).split()
            lo = rg.get('start_word', 0) if i == a else 0; hi = rg.get('end_word', len(words) - 1) if i == b else len(words) - 1
            n = max(0, hi - lo + 1); out[who] = max(out.get(who, 0), n)
    return out

def handles(r):
    reg = {k.lower(): v for k, v in (C.load(f'{C.SK}/references/collaborators.json') or {}).get('people', {}).items()}
    sh = C.load(f'{C.REELS_SK}/shows/{r["show"]}.json') or {}
    for k, v in ((sh.get('publishing') or {}).get('ig_collaborators') or {}).items():
        if not k.endswith('note') and isinstance(v, str): reg.setdefault(k.lower(), {'ig': v, 'source': f'CWC_PodReels shows/{r["show"]}.json'})
    return reg

def collaborators(r, reel, rule):
    sp = speakers(r['reels_work'], reel['ref']); reg = handles(r)
    never = {n.lower() for n in (C.load(f'{C.SK}/references/collaborators.json') or {}).get('never', ['Colden'])}
    talkers = sorted(w for w, n in sp.items() if n >= rule['collab_min_words'] and w.lower() not in never)
    missing = [w for w in talkers if not (reg.get(w.lower()) or {}).get('ig')]
    if missing: C.ask(f'reel {reel["ref"]}: Instagram handle for {", ".join(missing)}? (they speak in it; handles are never guessed - add them to CWC_PodRun references/collaborators.json with the source)')
    hs = [reg[w.lower()]['ig'].lstrip('@') for w in talkers]
    if len(hs) > rule['ig_max_collaborators']: C.ask(f'reel {reel["ref"]}: {len(hs)} collaborators ({hs}) - over the Instagram limit on file ({rule["ig_max_collaborators"]}); which ones?')
    return talkers, hs, sp

# ------------------------------------------------------------------ calendar + data
def calendar(R, rule):
    yt = C.load(f'{R}/calendar/youtube.json')
    if not yt: C.fail('calendar/youtube.json missing - cal.py youtube first')
    if C.hours_old(f'{R}/calendar/youtube.json') > rule['youtube_calendar_staleness_hours']: C.fail('calendar/youtube.json is stale - cal.py youtube again')
    long_busy, yt_shorts, mc_times, best, peaks = {}, {}, {}, {}, {}
    when = lambda v: v.get('start_at') or v.get('publish_at') or v.get('published_at')
    for b in ('cwc', 'tcl'):
        vids = yt['channels'].get(b, [])
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
        peaks[b] = C.load(f'{R}/calendar/peaks_{b}.json')
    return long_busy, yt_shorts, mc_times, best, peaks

# ------------------------------------------------------------------ placement
class Planner:
    def __init__(s, r, R, rule, now, W):
        s.r, s.R, s.rule, s.now = r, R, rule, now
        s.earliest = now + dt.timedelta(minutes=rule['min_lead_minutes'])
        s.w0, s.w1 = dt.date.fromisoformat(W['start']), dt.date.fromisoformat(W['end'])
        s.days = [s.w0 + dt.timedelta(days=i) for i in range((s.w1 - s.w0).days + 1)]
        s.spill = [s.w1 + dt.timedelta(days=i + 1) for i in range(rule['spill_days_max'])]
        s.long_busy, s.yt_shorts, s.mc_times, s.best, s.peaks = calendar(R, rule)
        s.items, s.warn, s.long = [], [], {'cwc': {}, 'tcl': {}}
        s.short_at = {'cwc': {}, 'tcl': {}}; s.fallback_warned = set(); s.yt_schedule = yt_schedule()

    def schedule(s): return s.yt_schedule
    def long_free(s, b, d): return d not in s.long_busy[b] and d not in s.long[b]

    def clip_time(s, b, d):
        pk = s.peaks.get(b) or {}
        hrs = ((pk.get('days') or {}).get(str(d.weekday())) or {}).get('most') or []
        if hrs:
            t = hm(d, f'{min(hrs)}:00') - dt.timedelta(minutes=s.rule['clip_lead_minutes_before_peak'])
            return t.replace(minute=(t.minute // 15) * 15)
        if b not in s.fallback_warned:
            s.fallback_warned.add(b); s.warn.append(f'{C.brands()[b]["label"]}: Studio shows no viewer-peak data - clips at {s.rule["clip_fallback_time_et"]} (hand-off default)')
        return hm(d, s.rule['clip_fallback_time_et'])

    def place_clips(s, clips):
        slot = {}; twins = {c['ref'] for c in clips if c['brand'] == 'tcl'}
        prim = sorted([c for c in clips if c['brand'] == 'cwc'], key=lambda c: (0 if c['news'] else 1, c['push_order']))
        n = len(prim); room = s.rule['secondary_min_delay_hours'] // 24
        for k, c in enumerate(prim):
            last = len(s.days) - 1 - (room if c['ref'] in twins else 0)          # a shared clip leaves room for TCL + 48 h
            t0 = 0 if c['news'] else min(max(last, 0), round(k * len(s.days) / n))
            order = s.days[t0:max(last, 0) + 1] + s.days[:t0][::-1] + s.days[max(last, 0) + 1:]
            d = next((d for d in order if s.long_free('cwc', d) and s.clip_time('cwc', d) >= s.earliest), None)
            if not d: C.ask(f'no free long-form day left on Create with Colden for {c["ref"]} "{c["title"]}" in the window (already busy: {sorted(map(str, s.long_busy["cwc"]))})')
            t = s.clip_time('cwc', d); s.long['cwc'][d] = c['ref']; slot[c['ref']] = t; s.add_clip(c, t)
        delay = dt.timedelta(hours=s.rule['secondary_min_delay_hours'])
        for c in sorted([c for c in clips if c['brand'] == 'tcl'], key=lambda c: (0 if c['news'] else 1, c['push_order'])):
            floor = max(s.earliest, slot[c['ref']] + delay) if c['ref'] in slot else s.earliest      # TCL-only: no delay
            pool = s.days + (s.spill if c['ref'] in slot else [])
            d = next((d for d in pool if s.long_free('tcl', d) and s.clip_time('tcl', d) >= floor), None)
            if not d: C.ask(f'{c["ref"]} on The Creative Lens: no free day ' + ('within the spill days after the window with the 48 h delay' if c['ref'] in slot else 'in the window'))
            if d > s.w1: s.warn.append(f'clip {c["ref"]} on TCL spills past the window to {C.DAYS[d.weekday()]} {d} (48 h after its CWC slot)')
            t = s.clip_time('tcl', d); s.long['tcl'][d] = c['ref']; s.add_clip(c, t)

    def add_clip(s, c, t):
        s.items.append({'id': f'clip-{c["ref"]}-{c["brand"]}', 'kind': 'yt_clip', 'product': 'clip', 'ref': c['ref'], 'brand': c['brand'],
                        'route': 'youtube_api', 'schedule': s.schedule(), 'publish_at': t.isoformat(), 'title': c['title'], 'description': c['description'],
                        'tags': c['tags'], 'playlists': c['playlists'], 'category': c['category'], 'pinned_comment': c['pinned'],
                        'files': {'video': c['master'], 'thumb': c['thumb'], 'captions': c['captions']},
                        'ab': {'titles': c['titles'], 'thumbnails': c['thumbnails'], 'plan': c['ab_tests_plan']},
                        'news': bool(c['news']), 'push_order': c['push_order'], 'needs': c['needs']})

    def hours(s, b, dow):
        hs = [x['hour'] for x in sorted([x for x in s.best[b] if x['dow'] == dow], key=lambda x: -x['value'])]
        return hs + [h for h in s.rule['short_default_hours_et'] if h not in hs]
    def day_score(s, b, d): return max([x['value'] for x in s.best[b] if x['dow'] == d.weekday()] or [0.0])
    def taken(s, b, d): return s.short_at[b].get(d, []) + s.mc_times[b].get(d, []) + s.yt_shorts[b].get(d, [])
    def pick(s, b, d, floor):
        gap = s.rule['shorts_extra_gap_hours'] * 3600
        for h in s.hours(b, d.weekday()):
            t = hm(d, f'{h}:00')
            if t >= floor and all(abs((t - x).total_seconds()) >= gap for x in s.taken(b, d)): return t
        return None
    def clash(s, b, d, ref, same_topic): return any(dd == d and same_topic(cref, ref) for dd, cref in s.long[b].items())

    def place_reels(s, reels, same_topic, collabs):
        cwc_at = {}; delay = dt.timedelta(hours=s.rule['short_secondary_delay_hours']); room = s.rule['short_secondary_delay_hours'] // 24
        for b in ('cwc', 'tcl'):
            for x in [x for x in reels if b in x['brands']]:
                shared = 'cwc' in x['brands'] and 'tcl' in x['brands']
                floor = max(s.earliest, cwc_at[x['ref']] + delay) if (b == 'tcl' and shared) else s.earliest
                days = s.days + (s.spill if (b == 'tcl' and shared) else [])
                cut = max(1, len(s.days) - room) if (b == 'cwc' and shared) else len(days)   # a shared reel leaves room for TCL + 48 h
                early, late = days[:cut], days[cut:]
                t = None
                for d in early + late:                                  # pass 1: an empty day, in order
                    if len(s.taken(b, d)) < s.rule['shorts_per_brand_per_day'] and not s.clash(b, d, x['ref'], same_topic) and (t := s.pick(b, d, floor)): break
                if not t:                                               # pass 2: a second post on the best days, >= 3 h apart
                    for d in sorted(early, key=lambda d: -s.day_score(b, d)) + sorted(late, key=lambda d: -s.day_score(b, d)):
                        if len(s.taken(b, d)) < s.rule['shorts_per_brand_per_day'] + 1 and not s.clash(b, d, x['ref'], same_topic) and (t := s.pick(b, d, floor)): break
                if not t: C.ask(f'no slot left for reel {x["ref"]} "{x["title"]}" on {b} - drop one, hold one, or widen the window (his call)')
                if t.date() > s.w1: s.warn.append(f'reel {x["ref"]} on TCL spills past the window to {C.DAYS[t.weekday()]} {t.date()} (48 h after CWC)')
                s.short_at[b].setdefault(t.date(), []).append(t)
                if b == 'cwc': cwc_at[x['ref']] = t
                cp, f = x['copy'][b], x['files'][b]
                owner = 'cwc' if 'cwc' in x['brands'] else 'tcl'           # ONE collaborator set per reel, Colden's channel first
                names, hs, sp = collabs[x['ref']]
                s.items.append({'id': f'yts-{x["ref"]}-{b}', 'kind': 'yt_short', 'product': 'short', 'ref': x['ref'], 'brand': b, 'route': 'youtube_api',
                                'schedule': s.schedule(), 'publish_at': t.isoformat(), 'title': cp.get('yt_title') or x['title'], 'description': cp.get('caption') or '',
                                'tags': [t.lstrip('#') for t in re.findall(r'#\w+', cp.get('caption') or '')],      # the caption's hashtags, as CWC_PodReels publish.py did
                                'playlists': [p for p in [s.short_playlist(b, cp.get('playlist'))] if p], 'category': str(C.brands()[b]['youtube']['category_id']),
                                'files': {'video': f['video'], 'thumb': f['thumb'], 'captions': None}, 'rank': x['rank']})
                s.items.append({'id': f'mc-{x["ref"]}-{b}', 'kind': 'social', 'product': 'short', 'ref': x['ref'], 'brand': b, 'route': None,
                                'publish_at': t.isoformat(), 'title': x['title'], 'text': cp.get('caption') or '', 'first_comment': cp.get('first_comment'),
                                'networks': list(C.brands()[b]['metricool']['networks']), 'fb_title': cp.get('fb_title') if b == 'cwc' else None,
                                'ig_collabs': hs if b == owner else [], 'speakers': sp, 'collab_names': names if b == owner else [],
                                'files': {'video': f['video'], 'thumb': f['thumb']}, 'rank': x['rank']})
                old = (cp.get('ig_collab') or '').lstrip('@'); old = '' if old.lower() == 'none' else old      # CWC_PodReels writes "none" for no collaborator
                if b == owner and old and old not in hs: s.warn.append(f'reel {x["ref"]}: PodReels copy says collaborator @{old.lstrip("@")}, the speakers say {hs or "none"} - the speakers win; check it')

    def short_playlist(s, b, key):
        sh = C.load(f'{C.REELS_SK}/shows/{s.r["show"]}.json') or {}
        mc = ((sh.get('publishing') or {}).get('metricool') or {}).get(b) or {}
        if isinstance(key, dict): key = key.get(b)                      # CWC_PodReels copy: {"cwc": "tcl_shorts", "tcl": "tcl_shorts"} - one key per brand
        key = key or mc.get('default_playlist')
        if not key: return None
        if str(key).startswith('PL'): return key
        hit = (mc.get('playlists') or {}).get(key)
        if not hit: s.warn.append(f'Short playlist "{key}" is not on file for {b} - none set'); return None
        return hit['id']

    def caps(s):
        out, used = {}, {}
        for b in ('cwc', 'tcl'):
            out[b], used[b] = {}, {}
            for mo, v in CAL.month_counts(s.R, b).items():
                out[b][mo] = {'used_before': v['used'], 'source': v['source'], 'planned_metricool': 0, 'manual': 0, 'cap': C.brands()[b]['metricool']['month_cap']}
                used[b][mo] = v['used']
        for it in sorted([i for i in s.items if i['kind'] == 'social'], key=lambda i: (i['brand'], i['rank'])):
            b, mo = it['brand'], it['publish_at'][:7]
            fl = (CAL.month_counts(s.R, b).get(mo) or {}).get('floor', 0)
            if mo in used[b] and used[b][mo] is not None and out[b][mo]['used_before'] < fl:
                C.fail(f'{C.brands()[b]["label"]} {mo}: the confirmed Metricool count ({out[b][mo]["used_before"]}) is below the {fl} posts that are provably there (Metricool\'s own list / this skill\'s ledger) - count again')
            if mo not in used[b] or used[b][mo] is None: C.fail(f'no confirmed Metricool count for {C.brands()[b]["label"]} {mo} - Claude in Chrome: the Metricool calendar (month view) for that brand -> count -> cal.py counts "{s.R}" {b} {mo}=<n> --evidence <screenshot>')
            if used[b][mo] + 1 <= out[b][mo]['cap']: it['route'] = 'metricool'; used[b][mo] += 1; out[b][mo]['planned_metricool'] += 1
            else: it['route'] = 'manual'; out[b][mo]['manual'] += 1
        return out

# ------------------------------------------------------------------ gates on the finished plan
def validate(P, items, same_topic):
    rule = P.rule; B = C.brands(); bad = []
    for it in items:
        t = dt.datetime.fromisoformat(it['publish_at'])
        if it['weekday'] != C.DAYS[t.weekday()]: bad.append(f'{it["id"]}: weekday {it["weekday"]} != {C.DAYS[t.weekday()]}')
        if t < P.earliest: bad.append(f'{it["id"]}: {t} is sooner than now + {rule["min_lead_minutes"]} min')
        if t.date() < P.w0: bad.append(f'{it["id"]}: before the window')
        if it['kind'] not in ('yt_clip', 'yt_short', 'social'): bad.append(f'{it["id"]}: kind {it["kind"]} (the full episode stays the live stream)')
        if it['kind'] == 'social':
            if 'youtube' in it['networks']: bad.append(f'{it["id"]}: YouTube through Metricool')
            if set(it['networks']) - set(B[it['brand']]['metricool']['networks']): bad.append(f'{it["id"]}: networks {it["networks"]} not all on {it["brand"]}')
            if it['route'] not in ('metricool', 'manual'): bad.append(f'{it["id"]}: route {it["route"]}')
            if not it['text']: bad.append(f'{it["id"]}: no caption')
        else:
            if it['route'] != 'youtube_api' or it['schedule'] != P.schedule(): bad.append(f'{it["id"]}: route {it["route"]} / {it["schedule"]}')
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
        if b == 'tcl' and (ref, 'cwc', k) in at:
            need = rule['secondary_min_delay_hours'] if k == 'yt_clip' else rule['short_secondary_delay_hours']
            if t - at[(ref, 'cwc', k)] < dt.timedelta(hours=need): bad.append(f'{k} {ref}: TCL < {need} h after CWC')
        if k == 'yt_short':
            for (r2, b2, k2), t2 in at.items():
                if k2 == 'yt_clip' and b2 == b and t2.date() == t.date() and same_topic(r2, ref): bad.append(f'reel {ref} on {b} {t.date()} = the day of same-topic clip {r2}')
    for ref in {i['ref'] for i in items if i['kind'] == 'social'}:
        soc = [i for i in items if i['kind'] == 'social' and i['ref'] == ref]
        with_c = [i for i in soc if i['ig_collabs']]
        if len(with_c) > 1: bad.append(f'reel {ref}: collaborators on {len(with_c)} posts - one set per reel')
        if with_c and with_c[0]['brand'] == 'tcl' and any(i['brand'] == 'cwc' for i in soc): bad.append(f'reel {ref}: collaborators on TCL while the reel plays on CWC')
    for b, months in P.cap_table.items():
        for mo, v in months.items():
            if v['used_before'] is not None and v['used_before'] + v['planned_metricool'] > v['cap']: bad.append(f'{b} {mo}: Metricool {v["used_before"]} + {v["planned_metricool"]} > cap {v["cap"]}')
    if bad: C.fail('the plan breaks its own rules:\n  ' + '\n  '.join(bad))

def quota(P, items):
    """API units per YouTube item, laid over Pacific days from today: an upload lands on the first day with room, and
    must land at least a day before its slot (Colden flips / YouTube schedules it)."""
    q = C.rules()['quota_cost']; limit = C.rules()['quota_daily_limit']
    today = (P.now.astimezone(dt.timezone.utc) - dt.timedelta(hours=7)).date()        # the quota day = Pacific (as ytapi.pacific_day)
    used_today = (C.load(f'{C.DATA}/quota.json', {}) or {}).get(today.isoformat(), 0)
    per, day, cur = {}, 0, used_today
    for it in sorted([i for i in items if i['kind'] != 'social'], key=lambda i: i['publish_at']):
        n = q['videos.insert'] + q['thumbnails.set'] + len(it.get('playlists') or []) * q['playlistItems.insert'] + (q['captions.insert'] if it['files'].get('captions') else 0)
        per[it['id']] = n
        if cur + n > limit: day += 1; cur = 0
        cur += n; it['upload_day'] = (today + dt.timedelta(days=day)).isoformat()
        if dt.date.fromisoformat(it['upload_day']) >= dt.datetime.fromisoformat(it['publish_at']).date():
            C.ask(f'{it["id"]}: the API quota ({limit}/day, ~{n} units an upload) only reaches it on {it["upload_day"]}, not before its slot {it["publish_at"][:16]} - '
                  'fewer YouTube posts early in the window, a later window, or a quota increase (his call)')
    return {'units': sum(per.values()), 'upload_days': day + 1, 'limit': limit, 'used_today_before': used_today, 'per_item': per}

def md(plan):
    L = [f'# Posting plan {plan["show"]} {plan["ep_key"]}', '', f'Window {plan["window"]["start_dow"]} {plan["window"]["start"]} -> {plan["window"]["end_dow"]} {plan["window"]["end"]} (ET, confirmed by {plan["window"].get("confirmed_by")}). YouTube: {"publishAt at upload" if plan["youtube_schedule"] == "publishAt" else "uploaded private, Colden flips to Scheduled"}. sha {plan["sha"]}', '']
    day = None
    for it in plan['items']:
        d = it['publish_at'][:10]
        if d != day: day = d; L += ['', f'## {it["weekday"]} {d}']
        what = {'yt_clip': 'YouTube clip', 'yt_short': 'YouTube Short', 'social': '+'.join(it.get('networks', []))}[it['kind']]
        extra = f' | collab {", ".join("@" + h for h in it["ig_collabs"])}' if it.get('ig_collabs') else ''
        extra += f' | upload {it["upload_day"]}' if it.get('upload_day') else ''
        L.append(f'- {it["publish_at"][11:16]} {C.brands()[it["brand"]]["label"]} | {what} | {it["route"]} | {it["title"]}{extra}')
    L += ['', '## Metricool month counts']
    for b, ms in plan['counts'].items():
        for mo, v in ms.items(): L.append(f'- {C.brands()[b]["label"]} {mo}: {v["used_before"]} used + {v["planned_metricool"]} planned / {v["cap"]}; {v["manual"]} manual ({v["source"]})')
    L += ['', f'## YouTube API quota: {plan["quota"]["units"]} units over {plan["quota"]["upload_days"]} day(s) at {plan["quota"]["limit"]}/day']
    if plan['warnings']: L += ['', '## Notes'] + [f'- {w}' for w in plan['warnings']]
    if plan['skipped']: L += ['', '## Not in this plan'] + [f'- {w}' for w in plan['skipped']]
    return '\n'.join(L) + '\n'

def build(R, now=None, waive=None):
    r = C.run(R); rule = C.rules()
    now = C.et(now) if now else dt.datetime.now(C.ET)
    yt_schedule()                                                       # the YouTube route is settled before anything is planned (exit 2 = ask)
    W = C.window(r, confirmed=True)
    if not W: C.ask('the posting window is not confirmed - window.py ask (Colden 2026-10-03: ask for a time span first, never assume)')
    if W['start'] < now.date().isoformat(): C.ask(f'the confirmed window starts {W["start"]}, before today - ask again (window.py ask)')
    p, scr = C.scrape()
    if not scr: C.ask('channel_metrics.json (the Monday scrape) not found')
    age = (now.date() - dt.date.fromisoformat(str(scr.get('updated'))[:10])).days
    if age > rule['scrape_max_age_days'] and not waive: C.ask(f'the Monday scrape is {age} days old ({p}) - run it, or --waive-scrape "<Colden\'s words>"')
    skipped = []
    clips, reels = holistic(R, r, clips_in(r), reels_in(r, skipped), skipped)
    reels = sorted(reels, key=lambda x: x['rank'])                       # placement order = rank (after the holistic read)
    for c in clips:
        for f in (c['master'], c['thumb']):
            if f and not os.path.exists(f): C.ask(f'not on disk (NAS mounted?): {f}')
    for x in reels:
        for f in [v for fs in x['files'].values() for v in fs.values()]:
            if f and not os.path.exists(f): C.ask(f'not on disk (NAS mounted?): {f}')
    for b in {c['brand'] for c in clips}:
        pk = f'{R}/calendar/peaks_{b}.json'
        if not os.path.exists(pk) or C.hours_old(pk) > rule['peaks_staleness_hours']:
            C.fail(f'fresh viewer peaks for {b} missing - Claude in Chrome on Studio ({C.brands()[b]["youtube"]["channel_id"]}) -> cal.py peaks "{R}" {b} <file>')
    cs, rs = spans(r['clips_work']), spans(r['reels_work']); thr = rule['same_topic_overlap_sec']
    def same_topic(clip_ref, reel_ref): return overlap(cs.get(clip_ref, []), rs.get(reel_ref, [])) >= thr
    collabs = {x['ref']: collaborators(r, x, rule) for x in reels}
    P = Planner(r, R, rule, now, W)
    P.place_clips(clips); P.place_reels(reels, same_topic, collabs); P.cap_table = P.caps()
    items = sorted(P.items, key=lambda i: (i['publish_at'], i['id']))
    for it in items: it['weekday'] = C.DAYS[dt.datetime.fromisoformat(it['publish_at']).weekday()]
    validate(P, items, same_topic)
    qu = quota(P, items)
    if any(c['needs'] for c in clips): P.warn.append('clip descriptions still hold {FULL_EPISODE_URL}: youtube.py fills it from the public "Ep. NN" live (no phone emoji) before upload')
    P.warn.append(f'data: Monday scrape {scr.get("updated")}; viewer peaks read {", ".join(b for b in ("cwc", "tcl") if P.peaks.get(b))}')
    plan = {'version': 2, 'rules': C.RULES, 'built_at': C.now(), 'now': now.isoformat(timespec='minutes'), 'show': r['show'], 'ep_key': r['ep_key'],
            'window': W, 'youtube_schedule': P.schedule(), 'items': items, 'counts': P.cap_table, 'quota': qu,
            'warnings': P.warn, 'skipped': skipped, 'scrape': {'path': p, 'updated': scr.get('updated'), 'waiver': waive}}
    plan['sha'] = C.sha({'items': items, 'rules': C.RULES, 'window': W})
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
