"""check.py <WORK> [--waive scrape_stale "<Colden's words>"]     ->  <WORK>/checked.json
Every rule of the theme stage as a gate. Nothing reaches Telegram that this script has not passed.

STRUCTURAL errors (exit 1 - fix themes.json, never work around):
  ids and ranges valid, no footage used twice inside one clip; the hook and payoff QUOTES are found word for word in
  their phrases; the payoff sits at the end of the last range; the hook is <= 14.5 s (rubric hook_max_seconds; `cold_open_waiver` = his words); title / summary / thumbnail idea
  present (summary 1-2 sentences, no em dashes); all nine scores with a reason; evidence ids exist in the channel data /
  the platform searches; a timeliness score >= 4 has a dated source; every claim has a status (+ source unless opinion);
  every screen share inside the clip is declared (what it is, integral or not); length outside 5-10 min has a length_note.
QUALITY (the theme is HELD with the reason, not an error):
  cold read missing / stale / FAIL (a BLOCKING gap, a score under 3, title not delivered); total under the SOFT line; a floor dimension under 3; a platform score >= 4 without
  a 2x outlier; estimated length under 3 or over 15 min; more than 10 % of the clip shared with clips ranked above it.
SET: STRONG themes (>= pass line) ranked news-first then by total; when fewer than 3 are strong, SOFT themes (soft line
  up) are delivered too, marked as such, each with a suggested channel (at least one for Colden's own); the best 5 are delivered, the next ones are runner-ups (offered one at a time when
  Colden kills a theme); fewer than 3 deliverable -> exit 2: flag for manual review (tg_themes.py flag).
DATA: channel pulls younger than 36 h (exit 1: channel_data.py pull); the Monday scrape's last good run <= 8 days
  (exit 2 unless waived with Colden's words); the intake still matches the locked PodCut (exit 1: intake.py)."""
import os, re, sys, glob, datetime
import common as C, themes as T, channel_data as CD
DIMS = ['hook', 'payoff', 'story', 'package', 'channel_fit', 'platform', 'timeliness', 'self_contained', 'footage']
CLAIM = {'verified', 'announced', 'rumor', 'opinion', 'own-experience'}

def structural(W, th, own_ids, plat):
    """-> list of errors for one theme"""
    E = []; tid = th.get('id', '?'); R = W.R
    def e(m): E.append(f'{tid}: {m}')
    for k in ('id', 'slug', 'title', 'summary', 'hook', 'body', 'payoff', 'thumbnail', 'scores', 'evidence_line'):
        if not th.get(k): e(f'missing "{k}"')
    if E: return E
    if not re.fullmatch(r't\d\d', th['id']): e('id must look like t01')
    if len(th['title']) > 100: e(f'title is {len(th["title"])} characters (YouTube allows 100)')
    for k in ('title', 'summary', 'evidence_line', 'thumbnail'):
        if '—' in th[k] or '–' in th[k]: e(f'{k} has an em / en dash (brand voice: none)')
    n_sent = len(re.findall(r'[.?!](?:\s|$)', th['summary'].strip()))
    if not 1 <= n_sent <= 2 or len(th['summary']) > 330: e(f'summary must be 1-2 sentences, <= 330 characters (it has {n_sent} sentences, {len(th["summary"])} characters)')
    if len(th['thumbnail']) < 15: e('thumbnail idea is too thin to judge (one concrete image: who, what, the words on it)')
    spans = []
    for name, r in [('hook', th['hook'])] + [(f'body[{i}]', r) for i, r in enumerate(th['body'])] + [('payoff', th['payoff'])]:
        try: sp = W.span(r)
        except KeyError as x: e(f'{name}: phrase id {x} does not exist'); continue
        except (ValueError, TypeError) as x: e(f'{name}: {x}'); continue
        if name.startswith('body'): spans.append(sp)
    if E: return E
    for i, a in enumerate(spans):
        for b in spans[i + 1:]:
            if min(a[1], b[1]) - max(a[0], b[0]) > 0.05: e(f'two body ranges use the same footage ({C.hms(max(a[0], b[0]))}-{C.hms(min(a[1], b[1]))})')
    for name in ('hook', 'payoff'):
        q = C.norm(th[name].get('quote', '')); txt = C.norm(W.text(th[name]))
        if len(q) < 5: e(f'{name}.quote must be the verbatim line (at least 5 words)')
        elif not C.contains_seq(txt, q): e(f'{name}.quote is NOT in {th[name]["from"]}..{th[name]["to"]} word for word. Those phrases say: "{W.text(th[name])[:200]}"')
    hs = W.span(th['hook'])
    if hs[1] - hs[0] > R['hook_max_seconds'] and len(str(th.get('cold_open_waiver', ''))) < 10: e(f'hook runs {hs[1] - hs[0]:.1f} s (limit {R["hook_max_seconds"]} s: the cold open is 15 s at most - ruling 32). Pick a shorter hook line; `cold_open_waiver` (Colden\'s words) only when he wants the long one')
    ps = W.span(th['payoff']); last = spans[-1]
    if not (last[0] - 0.01 <= ps[0] and ps[1] <= last[1] + 0.01): e('payoff is not inside the LAST body range - the clip must end on it')
    elif last[1] - ps[1] > 20: e(f'{last[1] - ps[1]:.0f} s of talk follow the payoff - end the last range on the payoff (a short button line after it is fine, 20 s is not)')
    sc = th['scores']
    for d in DIMS:
        s = sc.get(d)
        if not isinstance(s, dict) or not isinstance(s.get('s'), int) or not 0 <= s['s'] <= 5: e(f'scores.{d}.s must be an integer 0-5'); continue
        if len(str(s.get('why', ''))) < 20: e(f'scores.{d}.why must say why (evidence, not an adjective)')
    if E: return E
    for d, pool, label in (('channel_fit', own_ids, 'data/channels/*/videos.json'), ('platform', plat, f'{W.work}/platform/*.json')):
        ev = sc[d].get('evidence', [])
        if sc[d]['s'] >= 3 and not ev: e(f'scores.{d} is {sc[d]["s"]} with no evidence ids (a score of 3+ cites videos from {label})')
        for v in ev:
            if v not in pool: e(f'scores.{d}.evidence "{v}" is not a video id in {label}')
    nw = th.get('news') or {}
    if sc['timeliness']['s'] >= R['news_priority_at']:
        if not nw.get('time_sensitive') or not nw.get('source_url') or not nw.get('event'): e('timeliness >= 4 needs news: {time_sensitive: true, event, date, source_url}')
        try: datetime.date.fromisoformat(str(nw.get('date')))
        except ValueError: e('news.date must be YYYY-MM-DD (the date of the release / announcement / rumor)')
    cl = th.get('claims')
    if not isinstance(cl, list): e('claims must be a list (every factual claim the title, summary or hook leans on)')
    elif not cl and not th.get('claims_note'): e('claims is empty: add the claims, or claims_note saying why there are none (pure opinion / experience)')
    else:
        for c in cl:
            if c.get('status') not in CLAIM: e(f'claim "{str(c.get("claim"))[:50]}": status must be one of {sorted(CLAIM)}')
            elif c['status'] in ('verified', 'announced', 'rumor') and not str(c.get('source_url', '')).startswith('http'): e(f'claim "{str(c.get("claim"))[:50]}" is {c["status"]} with no source_url')
    for s in W.specials_in(th):
        d = next((x for x in th.get('shares', []) if s['start'] - 1 <= C.parse_tc(x.get('at', '-99')) <= s['end'] + 1), None)
        if not d or not d.get('what') or not isinstance(d.get('integral'), bool):
            e(f'a screen share / special layout at {C.hms(s["start"])}-{C.hms(s["end"])} is inside the clip and not declared: shares: [{{"at": "{C.hms(s["start"])}", "what": "...", "integral": true|false}}]')
    raw, est = W.runtime(th); L = R['length']
    if (est < L['note_below'] or est > L['note_above']) and len(str(th.get('length_note', ''))) < 20: e(f'estimated {C.mmss(est)} is outside 5-10 min: length_note must say why the story needs this length')
    return E

def evaluate(W, th, own_ids, plat_rows):
    """-> the record of one structurally valid theme: numbers, effective scores, hold reasons, warnings"""
    R = W.R; raw, est = W.runtime(th); hold = []; warn = []; sc = {d: th['scores'][d]['s'] for d in DIMS}
    txt = W.assemble(th); sha = C.sha_text(txt); cold = C.load(f'{W.work}/cold/{th["id"]}.json')
    if not cold: hold.append('no cold read yet (assemble.py -> a fresh agent -> coldread.py record)')
    elif cold['text_sha'] != sha: hold.append('the theme changed after its cold read - read it again'); cold = None
    else:
        for d, k in R['cold_read_caps'].items(): sc[d] = min(sc[d], cold[k])
        if cold['verdict'] != 'PASS': hold.append(f'cold read FAIL: missing {cold["missing_context"]}; would leave at "{cold["would_leave_at"][:80]}"')
    tot = round(100 * sum(R['dims'][d]['w'] * sc[d] for d in DIMS) / sum(5 * R['dims'][d]['w'] for d in DIMS), 1)
    for d in DIMS:
        fl = R['dims'][d].get('floor')
        if fl and sc[d] < fl: hold.append(f'{d} is {sc[d]} (floor {fl})')
    soft = R.get('soft_pass', R['pass']); tier = 'strong' if tot >= R['pass'] else 'soft'
    if tot < soft: hold.append(f'total {tot} is under the soft line {soft} (strong line {R["pass"]})')
    if sc['platform'] >= 4 and not any((plat_rows.get(v) or {}).get('outlier') and plat_rows[v]['outlier'] >= 2 for v in th['scores']['platform'].get('evidence', [])):
        hold.append('platform is scored 4+ but no cited video is at 2x its channel median')
    L = R['length']
    if est < L['ask_below'] or est > L['ask_above']: hold.append(f'estimated {C.mmss(est)} is outside 3-15 min')
    spans = [W.span(r) for r in th['body']]
    for i, r in enumerate(th['body']):
        a, b = spans[i]; fp = W.by[r['from']]; tp = W.by[r['to']]
        for p in W.ph:
            if p['who'] != fp['who'] and p['start'] < a - 0.4 and p['end'] > a + 0.4: warn.append(f'body[{i}] opens while {p["who"]} is mid-sentence ({p["id"]})')
            if p['who'] != tp['who'] and p['start'] < b - 0.4 and p['end'] > b + 0.4: warn.append(f'body[{i}] closes while {p["who"]} is mid-sentence ({p["id"]})')
        if re.match(r"(and|but|so|because|or|which|that)\b", fp['text'].lower()): warn.append(f'body[{i}] opens on a continuation word: "{fp["text"][:50]}"')
        if not re.search(r'[.?!]["\')]?$', tp['text']): warn.append(f'body[{i}] ends on a pause, not a finished sentence: "...{tp["text"][-50:]}"')
    hp = W.by[th['hook']['from']]; pp = W.by[th['payoff']['to']]; face = W.S['channels'].get('face'); sh = W.shares(th)
    cwc_fit = sh.get(face, 0) + (20 if hp['who'] == face else 0) + (20 if pp['who'] == face else 0)
    nonlinear = any(spans[i + 1][0] < spans[i][1] for i in range(len(spans) - 1))
    return {'id': th['id'], 'slug': th['slug'], 'title': th['title'], 'summary': th['summary'], 'thumbnail': th['thumbnail'], 'evidence_line': th['evidence_line'],
            'hook': {'who': hp['who'], 'tc': C.clock(hp['start']), 'seconds': round(W.span(th['hook'])[1] - W.span(th['hook'])[0], 1), 'quote': th['hook']['quote']},
            'payoff': {'who': pp['who'], 'tc': C.clock(W.by[th['payoff']['from']]['start']), 'quote': th['payoff']['quote']},
            'raw_seconds': round(raw, 1), 'est_seconds': round(est, 1), 'midroll': est >= R['length']['target'], 'length_note': th.get('length_note'),
            'scores_author': {d: th['scores'][d]['s'] for d in DIMS}, 'scores': sc, 'total': tot, 'tier': tier, 'cwc_fit': cwc_fit, 'news': bool((th.get('news') or {}).get('time_sensitive')) and sc['timeliness'] >= R['news_priority_at'],
            'news_event': (th.get('news') or {}).get('event'), 'speakers': W.shares(th), 'ranges': len(spans), 'nonlinear': nonlinear, 'jumps': sum(1 for i in range(len(spans) - 1) if abs(spans[i + 1][0] - spans[i][1]) > 2),
            'shares': th.get('shares', []), 'spans_cut': [[round(a, 2), round(b, 2)] for a, b in W.spans(th)], 'spans_base': [W.base_span(r) for r in th['body']] + [W.base_span(th['hook'])],
            'cold': {k: cold.get(k) for k in ('verdict', 'hook_clear', 'payoff_answers_hook', 'self_contained', 'one_line', 'weak_stretches', 'would_leave_at', 'missing_context', 'minor_gaps')} if cold else None,
            'text_sha': sha, 'hold': hold, 'warnings': warn}

def choose(recs, R, fixed=(), approved=()):
    """rank and take the best that keep every clip's shared footage <= 10 %.
    STRONG themes (>= pass) first, news first among them, then by total. SOFT themes (soft_pass..pass) are delivered
    only when fewer than deliver_min strong ones exist (Colden 2026-10-01: "soften scoring and send the best themes");
    otherwise they wait as runner-ups. `fixed` = ids already on Telegram: they stay, the rest is fitted around them;
    `approved` ones come first of all, so a REVISED theme that now overlaps an approved clip is the one held."""
    ok = [r for r in recs if not r['hold']]; allow_soft = sum(r['tier'] == 'strong' for r in ok) < R['deliver_min']
    pos = {r['id']: n for n, r in enumerate(ok)}; rank = lambda r: (r['id'] not in fixed, r['tier'] != 'strong', not r['news'], -r['total'], pos[r['id']])
    ranked = sorted(ok, key=lambda r: (r['id'] not in approved,) + rank(r))      # approved first for the overlap test only
    chosen = []; runner = []; over = {}
    for r in ranked:
        fit = True
        for c in chosen:
            ov = C.overlap_len(r['spans_cut'], c['spans_cut'])
            if ov / r['est_seconds'] > R['overlap_max'] or ov / c['est_seconds'] > R['overlap_max']:
                fit = False; over[r['id']] = f'shares {ov:.0f} s with {c["id"]} "{c["title"][:40]}" (limit {R["overlap_max"]:.0%} of either clip)'; break
        if fit and r['id'] not in fixed:
            tot_ov = C.overlap_len(r['spans_cut'], [s for c in chosen for s in c['spans_cut']])
            if tot_ov / r['est_seconds'] > R['overlap_max']: fit = False; over[r['id']] = f'shares {tot_ov:.0f} s with the clips ranked above it (limit {R["overlap_max"]:.0%})'
        if not fit: continue
        deliverable = r['id'] in fixed or r['tier'] == 'strong' or allow_soft
        (chosen if deliverable and len(chosen) < R['deliver_max'] else runner).append(r)
    chosen.sort(key=rank)                                  # the delivered order stays the ranking
    return chosen, runner, over, allow_soft and any(r['tier'] == 'soft' for r in chosen)

def run(work, write=True, fresh=True):
    W = T.Work(work); R = W.R; ep = W.ep; TH = W.themes(); errors = []
    m = C.load(f'{ep["podcut_cache"]}/manifest.json') or {}; L = m.get('locked') or {}
    if not ep.get('trial'):
        if m.get('rebuild') or not L: errors.append('the PodCut is no longer locked - wait for the new lock and run intake.py again')
        elif not os.path.exists(f'{L["snapshot"]}/plan.json') or C.sha_file(f'{L["snapshot"]}/plan.json') != ep['plan_sha']: errors.append('the locked PodCut changed since intake - run intake.py again (phrase ids moved)')
    if ep.get('rules') != C.RULES: errors.append(f'intake was made with rules {ep.get("rules")}, the skill is at {C.RULES} - run intake.py again')
    ok, probs, stale = CD.fresh()
    if fresh: errors += [f'channel data: {p} - run channel_data.py pull' for p in probs]      # fresh=False: a runner-up after a kill (the set was checked fresh when it was sent)
    waivers = C.load(f'{W.work}/waivers.json', {})
    own = set(); plat = {}
    for ch in CD.CHANNELS: own |= {v['id'] for v in (C.load(f'{C.DATA}/channels/{ch}/videos.json') or {}).get('videos', [])}
    for f in glob.glob(f'{W.work}/platform/*.json'):
        for v in C.load(f).get('results', []): plat[v['id']] = v
    ids = [t.get('id') for t in TH.get('themes', [])]
    if len(set(ids)) != len(ids): errors.append('two themes share an id')
    if len(set(t.get('slug') for t in TH['themes'])) != len(ids): errors.append('two themes share a slug')
    for th in TH['themes']: errors += structural(W, th, own, plat)
    if errors:
        print('\n'.join('STRUCTURAL  ' + x for x in errors)); return 1, None
    recs = [evaluate(W, th, own, plat) for th in TH['themes']]
    state = C.load(f'{W.work}/review/state.json', {}); fixed = [k for k, v in state.get('themes', {}).items() if v.get('status') in ('sent', 'approved', 'notes')]
    killed = [k for k, v in state.get('themes', {}).items() if v.get('status') == 'killed']
    for r in recs:
        if r['id'] in killed: r['hold'].append('killed by Colden on Telegram')
    approved = [k for k, v in state.get('themes', {}).items() if v.get('status') == 'approved']
    chosen, runner, over, softened = choose(recs, R, fixed, approved)
    for r in recs:
        if r['id'] in over: r['hold'].append(over[r['id']])
    lab = W.S['channels'].get('labels', {}); face = W.S['channels'].get('face'); at = R.get('cwc_suggest_at', 60)
    best = max(chosen, key=lambda r: r['cwc_fit'])['id'] if chosen else None       # at least one for Colden's own channel
    for r in recs:
        own = r['cwc_fit'] >= at or r['id'] == best
        r['suggest'] = {'channel': 'cwc' if own else 'tcl', 'label': lab.get('cwc' if own else 'tcl'),
                        'why': f'{face} has ' + ' and '.join(x for x in (('the hook' if r['hook']['who'] == face else ''), ('the payoff' if r['payoff']['who'] == face else '')) if x) + f'{", " if r["hook"]["who"] == face or r["payoff"]["who"] == face else ""}{r["speakers"].get(face, 0)} % of the words'
                               + ('' if r['cwc_fit'] >= at else ' - the best of this set for his channel' if own else '')}
    out = {'rules': C.RULES, 'rubric': R['version'], 'pass': R['pass'], 'checked_at': C.now(), 'themes_sha': C.sha_file(W.themes_path), 'trial': ep.get('trial'),
           'episode': dict({k: ep[k] for k in ('show', 'show_name', 'ep_key', 'cut', 'plan_sha')}, label=f'{ep["show_name"]} Ep {ep["ep_no"]}' if ep.get('ep_no') else f'{ep["show_name"]} {ep["ep_key"]}'), 'scrape_stale': stale, 'waivers': waivers,
           'episode_note': str(TH.get('episode_note', ''))[:500], 'softened': softened, 'soft_pass': R.get('soft_pass'), 'deliver': [r['id'] for r in chosen], 'runner_ups': [r['id'] for r in runner], 'held': [{'id': r['id'], 'title': r['title'], 'why': r['hold']} for r in recs if r['hold']],
           'themes': {r['id']: r for r in recs}}
    print(f'{"TRIAL " if ep.get("trial") else ""}{ep["show_name"]} {ep["ep_key"]} - {len(recs)} themes checked: deliver {len(chosen)}, runner-ups {len(runner)}, held {len(out["held"])}')
    for tag, rs in (('DELIVER', chosen), ('RUNNER-UP', runner)):
        for r in rs: print(f'  {tag:9} {r["id"]} {r["total"]:5.1f} {r["tier"]:6} {r["suggest"]["channel"]} {"NEWS " if r["news"] else "     "}{C.mmss(r["est_seconds"])}{" mid-roll" if r["midroll"] else "         "}  {r["title"]}' + ''.join(f'\n            warning: {w}' for w in r['warnings']))
    for h in out['held']: print(f'  HELD      {h["id"]} {h["title"][:60]} - ' + '; '.join(h['why']))
    code = 0; out['blocks'] = []
    if stale and 'scrape_stale' not in waivers:
        out['blocks'].append('scrape_stale')
        print(f'\nASK COLDEN (exit 2): the Monday Studio scrape is stale - {stale}. The API numbers are fresh, CTR / reach are not. Proceed without it? -> check.py <WORK> --waive scrape_stale "<his words>"'); code = 2
    if len(chosen) < R['deliver_min']:
        print(f'\nFLAG FOR MANUAL REVIEW (exit 2): only {len(chosen)} theme(s) pass - fewer than {R["deliver_min"]}. Do not pad. Run: tg_themes.py flag <WORK>'); code = 2; out['flag'] = True; out['blocks'].append('too_few')
    out['exit'] = code
    if write: C.save(f'{W.work}/checked.json', out)
    return code, out

if __name__ == '__main__':
    if len(sys.argv) < 2: C.fail(__doc__)
    work = os.path.abspath(sys.argv[1])
    if '--waive' in sys.argv:
        i = sys.argv.index('--waive'); key, words = sys.argv[i + 1], sys.argv[i + 2]
        if key != 'scrape_stale' or len(words) < 3: C.fail('only scrape_stale can be waived, with Colden\'s own words')
        w = C.load(f'{work}/waivers.json', {}); w[key] = {'by': words, 'at': C.now()}; C.save(f'{work}/waivers.json', w)
    code, _ = run(work); sys.exit(code)
