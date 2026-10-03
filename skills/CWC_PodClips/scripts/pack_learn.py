"""pack_learn.py - packaging that LEARNS from the weekly data (Colden 2026-10-02, ruling 44: "Can you make sure each
weeks packaging generation actually utilizes, and learns from, this data?").

  pack_learn.py build                 -> data/packaging_brief.json + data/packaging_brief.md  (package.py facts runs it)
  pack_learn.py features "<title>"    the measurable features of one title (what the gate sees)

INPUTS  (kept and merged week after week in data/packaging_history.json, so n grows) the Monday Studio scrape (trend_research/channel_metrics.json): per-video impressions + CTR + % viewed for both
        channels, Test & Compare results with the three titles + what each thumbnail showed, the scrape's own
        packaging fixes / working_now / avoid; the API pull (data/channels/*/videos.json: the FULL titles - the
        scrape shortens some); Colden's picks on the package cards (data/decisions.jsonl); and every upload this skill
        delivered (clips/*/*/delivery.json) once it is live - found by its title on its channel, linked in
        data/published.jsonl, then judged by its own CTR and its own A/B result against the hypotheses we wrote.
MEASURED  each title is reduced to features a script can see (question, opens with Why / How, a dollar figure, a
        number, conflict words, first person, product name first, review / vs wording, two-part, long, short,
        leak / rumor wording). Per feature: the CTR of videos WITH it vs WITHOUT it, each video against its own
        channel's median (so TCL's lower CTR does not drown the signal), plus every finished A/B test: does the
        winner carry the feature and the losers not? -> each pattern is WIN / LOSE / WEAK with its evidence and n.
        Thumbnail text (the words in quotes in the scrape's thumbnail lines) is measured the same way.
THE GATE  package.py check refuses copy that did not use the current brief: `brief` = the brief's id, `learned` = the
        patterns that shaped it (ids that exist, each with how), at least one title option with a WIN feature, any
        LOSE feature only as a declared test (`explore`), and for the final set a hypothesis per test title
        (`ab_tests_plan`) with B and C each differing from A in a measured feature - so every Test & Compare result
        teaches the next brief something.
Honest limit: 20-40 videos a week is a small sample - the brief prints n for every claim and marks thin evidence WEAK."""
import os, re, sys, json, glob, hashlib, statistics, datetime
import common as C

BRANDS = r'(DJI|Sony|Nikon|Canon|Blackmagic|Insta360|GoPro|Panasonic|Lumix|Fujifilm|Fuji|RED|Viltrox|7Artisans|Sigma|Tamron|DaVinci|Resolve|Xtra|XTRA|Higgsfield|Apple|iPhone|Adobe|Premiere|Osmo|PYXIS|Pyxis|ARRI|Atomos|Rode|RODE|Zhiyun|Hollyland|Aputure|Godox)'
CONFLICT = r'\b(drama|fire|lost|kill(ed|s)?|dead|dies|worst|caught|problem|flaws?|truth|brutal|garbage|never|wouldn.t|didn.t|war|sued|ban(ned)?|fcc|mistakes?|wrong|fail(ed|s)?|broke|stuck|lied|scam|quietly|dropped|exposed|backlash|hate)\b'
TITLE_FEATURES = [
    ('T-question', 'a question mark', lambda t: '?' in t),
    ('T-why-how', 'opens with Why / How', lambda t: bool(re.match(r"\s*['\"]?(why|how)\b", t, re.I))),
    ('T-money', 'a dollar figure or price', lambda t: bool(re.search(r'\$\s?\d|\bdollars?\b|\bprice[ds]?\b|\bcheap(er|est)?\b|\bfree\b|\bbudget\b|\bunder\s+\$', t, re.I))),     # not "6K": that is a resolution
    ('T-number', 'any number (incl. model numbers)', lambda t: bool(re.search(r'\d', t))),
    ('T-conflict', 'conflict / stakes words (drama, caught, truth, never, FCC, flaws ...)', lambda t: bool(re.search(CONFLICT, t, re.I))),
    ('T-first-person', 'first person (I / my)', lambda t: bool(re.search(r"\b(I|I'm|I've|My|my|me)\b", t))),
    ('T-brand-first', 'a brand / product name as the first word', lambda t: bool(re.match(r"\s*(the\s+)?" + BRANDS + r"\b", t, re.I))),
    ('T-review-vs', 'review / vs / specs / comparison wording', lambda t: bool(re.search(r'\b(review|vs\.?|versus|specs|comparison|compared)\b', t, re.I))),
    ('T-two-part', 'two parts (colon, or two sentences)', lambda t: bool(re.search(r':\s|[.?!]\s+\S', t.strip().rstrip('.?!')))),
    ('T-long', 'over 70 characters (cut off in the feed)', lambda t: len(t) > 70),
    ('T-short', '45 characters or less', lambda t: len(t) <= 45),
    ('T-leak-rumor', 'leak / rumor / delay / "finally" news wording', lambda t: bool(re.search(r'\b(leak(ed|s)?|rumou?rs?|delayed|finally|coming|confirmed|announced)\b', t, re.I))),
]
THUMB_FEATURES = [
    ('H-question', 'thumbnail text is a question', lambda t: '?' in t),
    ('H-money', 'thumbnail text has a dollar figure / number', lambda t: bool(re.search(r'\$|\d', t))),
    ('H-one-word', 'thumbnail text is ONE word', lambda t: len(t.split()) == 1),
    ('H-long-text', 'thumbnail text is 4+ words', lambda t: len(t.split()) >= 4),
]
WIN, LOSE = 1.15, 0.85                                   # CTR lift against the channel median that counts as a pattern
def feats(title, table=TITLE_FEATURES): return [fid for fid, _, f in table if f(title or '')]
def thumb_text(desc): return ' '.join(a or b for a, b in re.findall(r"'([^']+)'|\"([^\"]+)\"", desc or ''))

def jl(p): return [json.loads(l) for l in open(p)] if os.path.exists(p) else []
def videos():
    out = {}
    for ch in ('cwc', 'tcl'):
        for v in (C.load(f'{C.DATA}/channels/{ch}/videos.json') or {}).get('videos', []): out[v['id']] = dict(v, channel=ch)
    return out
def norm(t): return re.sub(r'[^a-z0-9]+', ' ', (t or '').lower()).strip()

def autolink(V):
    """every upload this skill delivered that is now on YouTube -> data/published.jsonl (found by its title A/B/C on its own channel)"""
    have = {p['video_id'] for p in jl(f'{C.DATA}/published.jsonl')}; n = 0
    for dp in sorted(glob.glob(f'{C.CLIPS}/*/*/delivery.json')):
        D = C.load(dp) or {}; W = os.path.dirname(dp); since = (D.get('delivered_at') or D.get('at') or '')[:10]
        for c in D.get('clips', []):
            names = {norm(t) for t in (c.get('titles') or {}).values()}
            hit = [v for v in V.values() if v['channel'] == c['channel'] and norm(v['title']) in names and (v.get('published') or '')[:10] >= since]
            if not hit or hit[0]['id'] in have: continue
            v = hit[0]; ck = C.load(f'{W}/checked.json') or {}; r = (ck.get('themes') or {}).get(c['theme'], {})
            row = {'at': C.now(), 'show': D.get('show'), 'ep': D.get('episode'), 'theme': c['theme'], 'channel': c['channel'], 'video_id': v['id'], 'title': r.get('title') or c['titles']['A'],
                   'how': 'auto: title match after delivery', 'package': {'titles': c.get('titles'), 'thumbnail_meta': c.get('thumbnail_meta'), 'ab_tests_plan': c.get('ab_tests_plan'), 'learned': c.get('learned'), 'brief': c.get('brief')},
                   'attrs': {k: r.get(k) for k in ('total', 'scores', 'est_seconds', 'news', 'ranges', 'nonlinear', 'speakers')} | {'hook_who': (r.get('hook') or {}).get('who')}}
            with open(f'{C.DATA}/published.jsonl', 'a') as f: f.write(json.dumps(row, ensure_ascii=False) + '\n')
            have.add(v['id']); n += 1
    return n

def lift(rows, fid, table):
    w = [r['rel'] for r in rows if fid in r['f']]; wo = [r['rel'] for r in rows if fid not in r['f']]
    if len(w) < 3 or len(wo) < 3: return None, len(w), len(wo)
    return round(statistics.median(w) / statistics.median(wo), 2), len(w), len(wo)

def build(quiet=False):
    import channel_data as CD
    sp, S = CD.scrape(); S = S or {}; V = videos(); linked = autolink(V)
    store = C.load(f'{C.DATA}/packaging_history.json', {}) or {}           # every week's rows and tests, kept: the scrape only covers 90 days and the sample grows each week
    for ch, pv in (('cwc', S.get('per_video') or []), ('tcl', (S.get('tcl') or {}).get('per_video') or [])):
        for r in pv:
            if r.get('video_id') and r.get('ctr_pct') is not None: store.setdefault('videos', {})[r['video_id']] = dict(r, channel=ch, seen=S.get('updated'))
    for t in (S.get('ab_tests') or []) + ((S.get('tcl') or {}).get('ab_tests') or []):
        if t.get('video_id') and (t.get('status') == 'done' or t['video_id'] not in store.get('tests', {})): store.setdefault('tests', {})[t['video_id']] = dict(t, seen=S.get('updated'))
    C.save(f'{C.DATA}/packaging_history.json', store)
    rows = []                                             # one per long-form video with a CTR: features of its FULL title, CTR against its channel's median
    allv = list((store.get('videos') or {}).values())
    for ch, pv in (('cwc', [r for r in allv if r['channel'] == 'cwc']), ('tcl', [r for r in allv if r['channel'] == 'tcl'])):
        good = [r for r in pv if r.get('ctr_pct') is not None and (r.get('impressions') or 0) >= 500 and r.get('verdict') != 'too early']
        if len(good) < 3: continue
        med = statistics.median(r['ctr_pct'] for r in good)
        for r in good:
            t = (V.get(r.get('video_id')) or {}).get('title') or r.get('title') or ''
            rows.append({'id': r.get('video_id'), 'ch': ch, 'title': t, 'ctr': r['ctr_pct'], 'rel': r['ctr_pct'] / med if med else 1, 'viewed': r.get('avg_pct_viewed'), 'f': feats(t)})
    tests = [t for t in (store.get('tests') or {}).values() if t.get('titles')]
    done = [t for t in tests if t.get('status') == 'done' and t.get('winner') in ('A', 'B', 'C')]
    def ab_score(fid, table, get):
        s = 0
        for t in done:
            win = get(t, t['winner']); lose = [get(t, k) for k in 'ABC' if k != t['winner'] and get(t, k)]
            if win is None or not lose: continue
            hw = fid in feats(win, table); hl = sum(fid in feats(x, table) for x in lose)
            if hw and hl == 0: s += 1
            elif not hw and hl == len(lose): s -= 1
        return s
    tget = lambda t, k: (t.get('titles') or {}).get(k)
    hget = lambda t, k: thumb_text((t.get('thumbs') or {}).get(k)) or None if 'title-only' not in str((t.get('thumbs') or {}).get(k, '')) else None
    pats = []
    for table, get, kind in ((TITLE_FEATURES, tget, 'title'), (THUMB_FEATURES, hget, 'thumbnail')):
        for fid, what, _ in table:
            lf, nw, nwo = lift(rows, fid, table) if kind == 'title' else (None, 0, 0)
            ab = ab_score(fid, table, get)
            st = 'WEAK'
            if lf is not None and nw >= 4 and lf >= WIN or ab >= 2: st = 'WIN'
            if lf is not None and nw >= 4 and lf <= LOSE or ab <= -2: st = 'LOSE' if st != 'WIN' else 'WEAK'
            ex = [r['title'] for r in sorted([r for r in rows if fid in r['f']], key=lambda r: -r['rel'])[:2]] if kind == 'title' else []
            pats.append({'id': fid, 'kind': kind, 'what': what, 'status': st, 'ctr_lift': lf, 'n_with': nw, 'n_without': nwo, 'ab_score': ab, 'examples': ex})
    lessons = []
    for t in done:
        k = t['winner']; sh = t.get('watch_time_share_pct') or {}
        lessons.append({'id': f'AB-{t["video_id"]}', 'winner_title': tget(t, k), 'loser_titles': [tget(t, x) for x in 'ABC' if x != k],
                        'winner_thumb': (t.get('thumbs') or {}).get(k), 'loser_thumbs': [(t.get('thumbs') or {}).get(x) for x in 'ABC' if x != k], 'share': sh.get(k),
                        'winner_has': feats(tget(t, k)), 'losers_have': sorted({f for x in 'ABC' if x != k for f in feats(tget(t, x))})})
    ties = [{'id': f'AB-{t["video_id"]}', 'titles': t['titles'], 'note': t.get('note', 'no winner: the difference did not matter')} for t in tests if t.get('status') == 'done' and t.get('winner') not in ('A', 'B', 'C')]
    picks = [d for d in jl(f'{C.DATA}/decisions.jsonl') if d.get('stage') == 'package' or str(d.get('decision', '')).startswith('picked:')]
    pk = {}
    for d in picks:
        x = str(d.get('decision', ''))
        if x.startswith('picked:'):
            k = x.split(':')[3] if x.count(':') >= 3 else {'thumb1': 'real still', 'thumb2': 'still + headline', 'thumb3': 'AI (GPT Image)', 'thumb4': 'AI (Nano Banana)'}.get(x.split(':')[2], x.split(':')[2]); pk[k] = pk.get(k, 0) + 1
    ours = []
    by_id = {r['id']: r for r in rows}; abs_ = {t['video_id']: t for t in tests}
    for p in jl(f'{C.DATA}/published.jsonl'):
        if not p.get('package'): continue
        r = by_id.get(p['video_id']); t = abs_.get(p['video_id'])
        ours.append({'video_id': p['video_id'], 'ep': p.get('ep'), 'channel': p['channel'], 'title_A': (p['package'].get('titles') or {}).get('A'), 'ctr': r and r['ctr'], 'ctr_vs_median': r and round(r['rel'], 2),
                     'ab': t and {'status': t.get('status'), 'winner': t.get('winner'), 'share': t.get('watch_time_share_pct')}, 'hypotheses': p['package'].get('ab_tests_plan'),
                     'verdict': None if not (t and t.get('winner') in ('A', 'B', 'C')) else f'{t["winner"]} won: ' + str((p['package'].get('ab_tests_plan') or {}).get(t['winner'], 'A (his pick) held'))})
    fixes = (S.get('insights') or {}).get('packaging_fixes') or []
    body = {'scrape': sp, 'scrape_updated': S.get('updated'), 'rows': len(rows), 'tests_done': len(done), 'patterns': pats, 'ab_lessons': lessons, 'ab_ties': ties,
            'colden_picks': pk, 'our_uploads': ours, 'scrape_fixes': fixes, 'working_now': S.get('working_now') or [], 'avoid': S.get('avoid') or []}
    bid = hashlib.sha1(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()[:10]
    B = dict(body, id=bid, built_at=C.now(), autolinked=linked); C.save(f'{C.DATA}/packaging_brief.json', B)
    open(f'{C.DATA}/packaging_brief.md', 'w').write(md(B))
    if not quiet: print(f'{C.DATA}/packaging_brief.md  (brief {bid}: {len(rows)} videos with CTR, {len(done)} finished A/B tests, scrape {S.get("updated")}; {linked} new upload(s) linked)')
    return B

def md(B):
    L = [f'# Packaging brief {B["id"]} - read before writing titles / thumbnails', f'Scrape {B["scrape_updated"]} - {B["rows"]} long-form videos with CTR (each against its own channel median), {B["tests_done"]} finished A/B tests. Put `"brief": "{B["id"]}"` in the copy.', '']
    for kind in ('title', 'thumbnail'):
        L.append(f'## {kind.capitalize()} patterns')
        for s in ('WIN', 'LOSE', 'WEAK'):
            for p in [p for p in B['patterns'] if p['kind'] == kind and p['status'] == s]:
                ev = (f'CTR x{p["ctr_lift"]} (n {p["n_with"]} vs {p["n_without"]}), ' if p['ctr_lift'] is not None else ('CTR: too few videos, ' if kind == 'title' else '')) + f'A/B {p["ab_score"]:+d} (finished tests where only the winner had it = +1, only the losers = -1)'
                L.append(f'- **{s}** `{p["id"]}` {p["what"]} - {ev}' + (f' - e.g. "{p["examples"][0]}"' if p['examples'] and s != 'WEAK' else ''))
        L.append('')
    L.append('## Finished A/B tests (what won, word for word)')
    for x in B['ab_lessons']: L.append(f'- `{x["id"]}` WON ({x["share"]} % watch time): "{x["winner_title"]}" / thumb {x["winner_thumb"]}  -  lost: ' + ' | '.join(f'"{t}"' for t in x['loser_titles']) + f'  -  thumbs lost: {x["loser_thumbs"]}')
    for x in B['ab_ties']: L.append(f'- `{x["id"]}` no winner: {list(x["titles"].values())} ({x["note"]})')
    L += ['', f'## Colden\'s picks on the package cards: {B["colden_picks"] or "none yet"}', '', '## Our delivered uploads, once live']
    L += [f'- {o["ep"]} {o["channel"]} "{o["title_A"]}": CTR {o["ctr"]} (x{o["ctr_vs_median"]} of median), A/B {o["ab"]}' + (f' -> {o["verdict"]}' if o['verdict'] else '') for o in B['our_uploads']] or ['- none live yet (published uploads are linked automatically by title)']
    L += ['', '## The scrape\'s own packaging calls'] + [f'- fix: "{f.get("title")}" -> "{f.get("suggested_title")}" ({f.get("why")})' for f in B['scrape_fixes']] + [f'- working: {x}' for x in B['working_now']] + [f'- avoid: {x}' for x in B['avoid']]
    L += ['', '## How to use it', '- Every title option should carry at least one WIN feature; a LOSE feature only as a declared test (`explore`).',
          '- B and C are EXPERIMENTS: each changes one measured thing against A (question vs statement, $ figure vs none, ...). Write the hypothesis in `ab_tests_plan` - the next brief reads the result.',
          '- `learned`: the 2+ pattern / A/B ids from this brief that shaped this copy, each with how.']
    return '\n'.join(L) + '\n'

def current():
    return C.load(f'{C.DATA}/packaging_brief.json') or {}

def problems(cp, final, where):
    """the packaging-learning gate for one copy file (package.py check_one calls it)"""
    p = []; B = current()
    if not B: return [f'{where}: no packaging brief - package.py facts builds it (pack_learn.py build)']
    if cp.get('brief') != B['id']: return [f'{where}: "brief" is {cp.get("brief")!r}, the current brief is "{B["id"]}" - READ data/packaging_brief.md (it changed or was never read), then set "brief": "{B["id"]}"']
    ids = {x['id'] for x in B['patterns']} | {x['id'] for x in B['ab_lessons']} | {x['id'] for x in B['ab_ties']}
    le = cp.get('learned') or []
    if len(le) < 2 or any(not isinstance(x, dict) or x.get('id') not in ids or len(str(x.get('how', ''))) < 15 for x in le):
        p.append(f'{where}: "learned" needs 2+ entries {{"id": <a pattern / A/B id from the brief>, "how": "<how this copy uses it>"}} - unknown ids: {[x.get("id") for x in le if isinstance(x, dict) and x.get("id") not in ids]}')
    win = {x['id'] for x in B['patterns'] if x['kind'] == 'title' and x['status'] == 'WIN'}; lose = {x['id'] for x in B['patterns'] if x['kind'] == 'title' and x['status'] == 'LOSE'}
    ts = cp.get('titles') or []; ex = cp.get('explore') or {}
    if win and ts and not any(set(feats(t)) & win for t in ts): p.append(f'{where}: none of the 3 title options carries a WIN pattern ({sorted(win)}) - the data says what clicks; use it')
    for i, t in enumerate(ts, 1):
        bad = sorted(set(feats(t)) & lose)
        if bad and len(str(ex.get(str(i), ''))) < 15: p.append(f'{where}: title {i} carries LOSE pattern(s) {bad} - change it, or declare it a test: "explore": {{"{i}": "<what it tests and why>"}}')
    if final:
        A = cp.get('A') or ''; plan = cp.get('ab_tests_plan') or {}
        for k in ('B', 'C'):
            if len(str(plan.get(k, ''))) < 15: p.append(f'{where}: "ab_tests_plan" needs "{k}": "<what {k} tests against A>" - an A/B test without a hypothesis teaches nothing')
            elif cp.get(k) and set(feats(cp[k])) == set(feats(A)): p.append(f'{where}: title {k} has the same measured features as A ({feats(A)}) - change one thing (question, $ figure, conflict, first person ...) so the test can tell what won')
    return p

if __name__ == '__main__':
    a = sys.argv[1:]
    if a[:1] == ['build']: build()
    elif a[:1] == ['features'] and len(a) > 1: print(feats(a[1]))
    else: C.fail(__doc__)
