"""check.py <WORK>     ->  <WORK>/checked.json      Every rule of the theme stage as a gate; nothing reaches Telegram that
this script has not passed.
STRUCTURAL errors (exit 1 - fix themes.json, never work around):
  ids, ranges and word indices valid; no footage twice inside one short; the hook QUOTE is the first words of the first
  range; the payoff QUOTE is found word for word and the short ENDS on it (<= 1.5 s after); title <= 60 chars,
  hook_text 1-2 lines <= 24 chars, summary one sentence, no em / en dashes; all eight scores with a reason; evidence
  ids exist in data/shorts (channel_fit >= 3 needs them); timeliness >= 4 has a dated source; every claim has a status
  (+ source unless opinion); every screen share inside the short is declared; LENGTH 20-75 s (Colden 2026-10-02), over
  45 s needs a length_note; a destination the show allows; b-roll ideas (3-4) or a waiver; no on-air "Colden, edit
  that" line inside a range (Whisper writes him Colton - common.COLDEN_RE); PACKAGING FROM DATA (Colden 2026-10-02:
  "Data MUST drive the packaging"): themes.json names the current data/shorts/packaging_brief (it was read), every
  theme has "learned" (2+ brief pattern ids + how they shaped its title / hook_text), title or hook_text carries a WIN
  pattern when the brief has one, a LOSE pattern only as a declared "explore".
QUALITY (the theme is HELD with the reason): cold read missing / stale / FAIL; a floor dimension under 3; total under
  the soft line; more than 25 % of the short shared with a short ranked above it (no variants).
SET: strong (>= 70) first, news first among them, then total; when fewer than 10 are strong, SOFT themes (>= 55) fill up
  to 10 (marked); the next ones are runner-ups; fewer than 5 deliverable -> exit 2 + tg_cards.py flag.
DATA: shorts_data.py fresh (YouTube < 36 h, Metricool < 7 days) - exit 1 otherwise; the intake still matches the locked
  PodCut."""
import os, re, sys, datetime
import common as C, themes as T, shorts_data as SD, pack_learn as PL
DIMS = ['hook', 'payoff', 'retention', 'channel_fit', 'timeliness', 'self_contained', 'package', 'footage']
CLAIM = {'verified', 'announced', 'rumor', 'opinion', 'own-experience'}
FLAGGED = re.compile(C.COLDEN_RE + r".{0,60}\b(edit|cut|take)\b.{0,12}\b(that|this|it)\b|\bedit (that|this) out\b|\bcut (that|this) out\b|\bdon'?t (use|put) (that|this)\b", re.I)

def structural(W, th, ev_ids):
    E = []; tid = th.get('id', '?'); R = W.R
    def e(m): E.append(f'{tid}: {m}')
    for k in ('id', 'slug', 'title', 'hook_text', 'summary', 'hook', 'ranges', 'payoff', 'scores', 'dest'):  # payoff = {"quote"} (from / to optional, informative)
        if not th.get(k): e(f'missing "{k}"')
    if E: return E
    if not re.fullmatch(r's\d\d', th['id']): e('id must look like s01')
    if len(th['title']) > 60: e(f'title is {len(th["title"])} characters (60 max - it is the timeline and file name)')
    if any(ch in th['title'] for ch in C.TL_BAD): e(f'title has a character Resolve / the NAS refuses ({C.TL_BAD})')
    ht = th['hook_text']
    if not isinstance(ht, list) or not 1 <= len(ht) <= 2 or any(not isinstance(x, str) or not x.strip() or len(x) > 24 for x in ht): e('hook_text must be 1-2 lines of at most 24 characters')
    for k, v in (('title', th['title']), ('summary', th['summary']), ('hook_text', ' '.join(ht if isinstance(ht, list) else []))):
        if '—' in v or '–' in v: e(f'{k} has an em / en dash (brand voice: none)')
    if len(re.findall(r'[.?!](?:\s|$)', th['summary'].strip())) > 1 or len(th['summary']) > 220: e('summary must be ONE sentence, <= 220 characters')
    sps = []
    for i, r in enumerate(th['ranges']):
        try: sps.append(W.span(r))
        except KeyError as x: e(f'ranges[{i}]: phrase id {x} does not exist')
        except (ValueError, TypeError, IndexError) as x: e(f'ranges[{i}]: {x}')
    if E: return E
    for i, a in enumerate(sps):
        for b in sps[i + 1:]:
            if min(a[1], b[1]) - max(a[0], b[0]) > 0.05: e(f'two ranges use the same footage ({C.hms(max(a[0], b[0]))}-{C.hms(min(a[1], b[1]))})')
    by = W.by; opener = by[th['ranges'][0]['from']]['who']; closer = by[th['ranges'][-1]['to']]['who']
    q = C.norm(th['hook'].get('quote', '')); first = [t for t, _, _ in W.spoken(th['ranges'][0], opener)]
    if len(q) < 3: e('hook.quote must be the first words heard, verbatim (at least 3 words)')
    elif first[:len(q)] != q: e(f'hook.quote is not how the short OPENS. {opener} starts: "{" ".join(first[:16])}"')
    pq = th['payoff'].get('quote', ''); last = sps[-1]
    if len(C.norm(pq)) < 4: e('payoff.quote must be verbatim (at least 4 words)')
    else:
        qe = W.quote_end(th['ranges'][-1], closer, pq)
        if qe is None: e(f'payoff.quote is not in what {closer} says in the LAST range, word for word: "...{" ".join(t for t, _, _ in W.spoken(th["ranges"][-1], closer)[-30:])}"')
        elif last[1] - qe > 1.5: e(f'{last[1] - qe:.1f} s of talk follow the payoff - end the last range on it (end_word), the short ends cold')
    sc = th['scores']
    for d in DIMS:
        s = sc.get(d)
        if not isinstance(s, dict) or not isinstance(s.get('s'), int) or not 0 <= s['s'] <= 5: e(f'scores.{d}.s must be an integer 0-5'); continue
        if len(str(s.get('why', ''))) < 20: e(f'scores.{d}.why must say why (evidence, not an adjective)')
    if E: return E
    ev = sc['channel_fit'].get('evidence', [])
    if sc['channel_fit']['s'] >= 3 and not ev: e('scores.channel_fit is 3+ with no evidence ids (cite Short ids / TikTok / Instagram urls from data/shorts/summary.md)')
    for v in ev:
        if v not in ev_ids: e(f'scores.channel_fit.evidence "{v}" is not in data/shorts/catalog.json')
    nw = th.get('news') or {}
    if sc['timeliness']['s'] >= R['news_priority_at']:
        if not nw.get('event') or not str(nw.get('source_url', '')).startswith('http'): e('timeliness >= 4 needs news: {event, date, source_url}')
        try: datetime.date.fromisoformat(str(nw.get('date')))
        except ValueError: e('news.date must be YYYY-MM-DD')
    cl = th.get('claims')
    if not isinstance(cl, list) and not th.get('claims_note'): e('claims must be a list (or claims_note: why there are none)')
    for c in (cl or []):
        if c.get('status') not in CLAIM: e(f'claim "{str(c.get("claim"))[:50]}": status must be one of {sorted(CLAIM)}')
        elif c['status'] in ('verified', 'announced', 'rumor') and not str(c.get('source_url', '')).startswith('http'): e(f'claim "{str(c.get("claim"))[:50]}" is {c["status"]} with no source_url')
    for s in W.specials_in(th):
        d = next((x for x in th.get('shares', []) if s['start'] - 1 <= C.parse_tc(x.get('at', '-99')) <= s['end'] + 1), None)
        if not d or not d.get('what') or not isinstance(d.get('integral'), bool):
            e(f'a screen share at {C.hms(s["start"])}-{C.hms(s["end"])} is inside the short and not declared: shares: [{{"at": "{C.hms(s["start"])}", "what": "...", "integral": true|false}}]')
    raw, est, _ = W.runtime(th); L = R['length']
    if est < L['hard_min'] or est > L['hard_max']: e(f'estimated {est:.0f} s is outside {L["hard_min"]}-{L["hard_max"]} s (Colden 2026-10-02: hard limits)')
    elif est > L['payoff_by'] and len(str(th.get('length_note', ''))) < 20: e(f'estimated {est:.0f} s: the payoff lands after {L["payoff_by"]} s - length_note must say why the story needs it')
    if th['dest'] not in W.S['channels']['destinations']: e(f'dest must be one of {W.S["channels"]["destinations"]}')
    ideas = [i for i in (th.get('broll') or []) if isinstance(i, str) and len(i) > 8]
    if not ideas and len(str(th.get('broll_waiver', ''))) < 10: e('b-roll: 3-4 concrete ideas, or broll_waiver with the reason (Colden: b-roll is part of every short)')
    for i, r in enumerate(th['ranges']):
        t = W.text(r)
        if FLAGGED.search(t): e(f'ranges[{i}] contains an on-air edit request ("{FLAGGED.search(t).group(0)}") - never use it')
    E += PL.problems(th, tid, {'title': th['title']}, hook='\n'.join(ht))          # the packaging-learning gate (data drives the words)
    return E

def evaluate(W, th):
    R = W.R; raw, est, _ = W.runtime(th); hold = []; warn = []; sc = {d: th['scores'][d]['s'] for d in DIMS}
    txt = W.assemble(th); sha = C.sha_text(txt); cold = C.load(f'{W.work}/cold/{th["id"]}.json')
    if not cold: hold.append('no cold read yet (assemble.py -> a fresh agent -> coldread.py record)')
    elif cold['text_sha'] != sha: hold.append('the theme changed after its cold read - read it again'); cold = None
    else:
        for d, k in R['cold_read_caps'].items(): sc[d] = min(sc[d], cold[k])
        if cold['verdict'] != 'PASS': hold.append(f'cold read FAIL: missing {cold["missing_context"]}; would swipe at "{cold["would_swipe_at"][:80]}"')
    tot = round(100 * sum(R['dims'][d]['w'] * sc[d] for d in DIMS) / sum(5 * R['dims'][d]['w'] for d in DIMS), 1)
    for d in DIMS:
        fl = R['dims'][d].get('floor')
        if fl and sc[d] < fl: hold.append(f'{d} is {sc[d]} (floor {fl})')
    if tot < R['soft_pass']: hold.append(f'total {tot} is under the soft line {R["soft_pass"]}')
    sps = W.spans(th); by = W.by
    for i, r in enumerate(th['ranges']):
        fp, tp = by[r['from']], by[r['to']]
        if r.get('start_word') is None and re.match(r"(and|but|so|because|or|which|that)\b", fp['text'].lower()): warn.append(f'ranges[{i}] opens on a continuation word: "{fp["text"][:50]}"')
        if r.get('end_word') is None and not re.search(r'[.?!]["\')]?$', tp['text']): warn.append(f'ranges[{i}] ends on a pause, not a finished sentence: "...{tp["text"][-50:]}"')
    hp = by[th['ranges'][0]['from']]; pp = by[th['ranges'][-1]['to']]
    return {'id': th['id'], 'slug': th['slug'], 'title': th['title'], 'hook_text': th['hook_text'], 'summary': th['summary'], 'dest': th['dest'],
            'hook': {'who': hp['who'], 'tc': C.clock(sps[0][0]), 'quote': th['hook']['quote']}, 'payoff': {'who': pp['who'], 'quote': th['payoff']['quote']},
            'raw_seconds': round(raw, 1), 'est_seconds': round(est, 1), 'scores_author': {d: th['scores'][d]['s'] for d in DIMS}, 'scores': sc, 'total': tot,
            'tier': 'strong' if tot >= R['pass'] else 'soft', 'news': bool(th.get('news')) and sc['timeliness'] >= R['news_priority_at'], 'news_event': (th.get('news') or {}).get('event'),
            'speakers': W.shares(th), 'ranges': len(sps), 'nonlinear': any(sps[i + 1][0] < sps[i][1] for i in range(len(sps) - 1)),
            'jumps': sum(1 for i in range(len(sps) - 1) if abs(sps[i + 1][0] - sps[i][1]) > 1.5), 'shares': th.get('shares', []),
            'spans_cut': [[round(a, 2), round(b, 2)] for a, b in sps], 'cold': {k: cold.get(k) for k in ('verdict', 'hook_clear', 'payoff_answers_hook', 'self_contained', 'one_line', 'slow_spots', 'would_swipe_at', 'missing_context', 'minor_gaps')} if cold else None,
            'text_sha': sha, 'hold': hold, 'warnings': warn}

def choose(recs, R, fixed=(), approved=()):
    ok = [r for r in recs if not r['hold']]; pos = {r['id']: n for n, r in enumerate(ok)}
    allow_soft = sum(r['tier'] == 'strong' for r in ok) < R['deliver_max']
    rank = lambda r: (r['id'] not in fixed, r['tier'] != 'strong', not r['news'], -r['total'], pos[r['id']])
    chosen = []; runner = []; over = {}
    for r in sorted(ok, key=lambda r: (r['id'] not in approved,) + rank(r)):
        fit = True
        for c in chosen:
            ov = C.overlap_len(r['spans_cut'], c['spans_cut'])
            if ov / r['est_seconds'] > R['overlap_max'] or ov / c['est_seconds'] > R['overlap_max']:
                fit = False; over[r['id']] = f'shares {ov:.0f} s with {c["id"]} "{c["title"][:40]}" - a variant (limit {R["overlap_max"]:.0%})'; break
        if not fit: continue
        deliverable = r['id'] in fixed or r['tier'] == 'strong' or allow_soft
        (chosen if deliverable and len(chosen) < R['deliver_max'] else runner).append(r)
    chosen.sort(key=rank)
    return chosen, runner, over, allow_soft and any(r['tier'] == 'soft' for r in chosen)

def run(work, write=True, fresh=True):
    W = T.Work(work); R = W.R; ep = W.ep; TH = W.themes(); errors = []
    m = C.load(f'{ep["podcut_cache"]}/manifest.json') or {}; L = m.get('locked') or {}
    if not ep.get('trial'):
        if m.get('rebuild') or not L: errors.append('the PodCut is no longer locked - wait for the new lock and run intake.py again')
        elif not os.path.exists(f'{L["snapshot"]}/plan.json') or C.sha_file(f'{L["snapshot"]}/plan.json') != ep['plan_sha']: errors.append('the locked PodCut changed since intake - run intake.py again (phrase ids moved)')
    if ep.get('rules') != C.RULES: errors.append(f'intake was made with rules {ep.get("rules")}, the skill is at {C.RULES} - run intake.py again')
    if fresh: errors += [f'data: {p}' for p in SD.fresh()]
    errors += PL.brief_ok(TH, 'themes.json')                                     # the brief was read before the titles / hooks were written
    ev = SD.evidence_ids(); ids = [t.get('id') for t in TH.get('themes', [])]
    if len(set(ids)) != len(ids): errors.append('two themes share an id')
    if len(set(t.get('slug') for t in TH['themes'])) != len(ids): errors.append('two themes share a slug')
    for th in TH['themes']: errors += structural(W, th, ev)
    if errors:
        print('\n'.join('STRUCTURAL  ' + x for x in errors)); return 1, None
    recs = [evaluate(W, th) for th in TH['themes']]
    st = C.load(f'{W.work}/review/cards.json', {}); fixed = [k for k, v in st.get('themes', {}).items() if v.get('status') in ('sent', 'approved', 'notes')]
    for r in recs:
        if st.get('themes', {}).get(r['id'], {}).get('status') == 'killed': r['hold'].append('killed by Colden on Telegram')
    approved = [k for k, v in st.get('themes', {}).items() if v.get('status') == 'approved']
    chosen, runner, over, softened = choose(recs, R, fixed, approved)
    for r in recs:
        if r['id'] in over: r['hold'].append(over[r['id']])
    out = {'rules': C.RULES, 'rubric': R['version'], 'pass': R['pass'], 'checked_at': C.now(), 'themes_sha': C.sha_file(W.themes_path), 'trial': ep.get('trial'),
           'episode': dict({k: ep[k] for k in ('show', 'show_name', 'ep_key', 'cut', 'plan_sha')}, label=f'{ep["show_name"]} Ep {ep["ep_no"]}' if ep.get('ep_no') else f'{ep["show_name"]} {ep["ep_key"]}'),
           'episode_note': str(TH.get('episode_note', ''))[:500], 'softened': softened, 'deliver': [r['id'] for r in chosen], 'runner_ups': [r['id'] for r in runner],
           'held': [{'id': r['id'], 'title': r['title'], 'why': r['hold']} for r in recs if r['hold']], 'themes': {r['id']: r for r in recs}}
    print(f'{"TRIAL " if ep.get("trial") else ""}{ep["show_name"]} {ep["ep_key"]} - {len(recs)} themes: deliver {len(chosen)}, runner-ups {len(runner)}, held {len(out["held"])}')
    for tag, rs in (('DELIVER', chosen), ('RUNNER-UP', runner)):
        for r in rs: print(f'  {tag:9} {r["id"]} {r["total"]:5.1f} {r["tier"]:6} {r["dest"]:4} {"NEWS " if r["news"] else "     "}{r["est_seconds"]:4.0f}s  {r["title"]}' + ''.join(f'\n            warning: {w}' for w in r['warnings']))
    for h in out['held']: print(f'  HELD      {h["id"]} {h["title"][:50]} - ' + '; '.join(h['why']))
    code = 0
    if len(chosen) < R['deliver_min']:
        print(f'\nFLAG FOR MANUAL REVIEW (exit 2): only {len(chosen)} short(s) pass - fewer than {R["deliver_min"]}. Never pad. Run: tg_cards.py flag <WORK>'); code = 2; out['flag'] = True
    out['exit'] = code
    if write: C.save(f'{W.work}/checked.json', out)
    return code, out

if __name__ == '__main__':
    if len(sys.argv) < 2: C.fail(__doc__)
    code, _ = run(os.path.abspath(sys.argv[1])); sys.exit(code)
