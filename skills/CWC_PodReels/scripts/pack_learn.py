"""pack_learn.py - packaging that LEARNS from the short-form data (Colden 2026-10-02: "When it is titling and generating
hooks, make sure it is actually utilizing the data we pulled from the analytics scrape like /CWC_PodClips is doing.
Data MUST drive the packaging here"). The PodReels twin of CWC_PodClips' pack_learn.py, measured on SHORTS.

  pack_learn.py build                 -> data/shorts/packaging_brief.json + packaging_brief.md  (shorts_data.py summary runs it)
  pack_learn.py features "<text>"     the measurable features of one title / hook / caption (what the gates see)

INPUTS   data/shorts/catalog.json (shorts_data.py join: every YouTube Short of both channels with lifetime avg % viewed +
         kept at 3 s, every TikTok post with avg watch time, every Instagram reel with its 3-second view rate), the
         Monday Studio scrape's `shorts` block (YouTube stayed-to-watch / avg % viewed, TikTok watched-full %,
         retention at 3 s) matched by title (a title Studio shortened, with or without "...", matches by prefix), the scrape's
         OWN ANALYSIS (insights.patterns / actions / packaging_fixes, working_now, avoid, every Test & Compare result
         with what each thumbnail showed - the same blocks /CWC_PodClips folds in; Colden 2026-10-02: "like
         /CWC_PodClips is doing"), Colden's theme decisions (data/shorts/decisions.jsonl: approved vs
         killed hook_text + title), and our own published shorts once learn.py snapshot has their numbers.
MEASURED each title / caption is reduced to features a script can see (a question, a number, a $ figure, a named
         brand / product / film, conflict words, "you", a quote, a cliffhanger "...", length). RETENTION FIRST
         (ruling 2): per platform each short's retention metric is divided by its brand's median on that platform
         (YouTube avg % viewed, TikTok avg watch / length, Instagram 3-s rate; the scrape's stayed-to-watch when it
         has it), the row's `rel` = the median of those; views the same way as `vrel`. Per feature: the median rel
         WITH it vs WITHOUT it (n >= 4 each side) -> WIN (x1.15+) / LOSE (x0.85-) / WEAK, with examples and n.
         On-screen HOOK features are measured on our own shorts (themes.json of every episode: approved vs killed
         by Colden, then their published numbers) - thin until a few episodes are out, and marked WEAK until then.
         COVER (thumbnail) features are measured on the scrape's finished A/B tests: what the winning thumbnail
         showed vs the losers (a face, one giant word, a question, a number) -> C-* patterns; cover.py add refuses
         a cover headline that carries no WIN pattern and is not a line of the short's (already gated) hook / title.
THE GATES  check.py (themes): themes.json carries "brief": <this brief's id> (the brief was READ), every theme
         "learned": 2+ pattern ids with how they shaped its title / hook_text, title or hook_text carries a WIN
         feature when the brief has one, a LOSE feature only as a declared "explore". postcopy.py (copy): the same
         on copy.json ("brief", per short "learned"; yt_title + the caption's first sentence).
Honest limit: n is printed on every claim; the brief never hides a thin sample."""
import os, re, sys, json, glob, hashlib, statistics, datetime
import common as C

BRANDS = (r'(DJI|Sony|FX3|FX6|FX30|A7|Nikon|Canon|Blackmagic|BMPCC|Pyxis|PYXIS|Insta360|GoPro|Panasonic|Lumix|Fujifilm|Fuji|RED|Komodo|Viltrox|Sigma|Tamron|'
          r'DaVinci|Resolve|Premiere|Adobe|Apple|iPhone|Osmo|Pocket|ARRI|Alexa|Atomos|Rode|RODE|Zhiyun|Aputure|Godox|Netflix|Nvidia|OpenPocketCine|'
          r'Nolan|Spielberg|Coppola|Tarantino|Scorsese|Kubrick|Godfather|Rocky|Shining|Pulp Fiction|Inception|Oppenheimer|Megalopolis|Odyssey|Sundance|Hollywood|Instagram|TikTok|YouTube|Veo|Sora|Runway|ChatGPT)')
CONFLICT = (r'\b(worst|never|wouldn.t|didn.t|won.t|can.t|stop|quit|dead|dies|kill(ed|s)?|lost|lie[sd]?|wrong|fail(ed|s)?|broke|broken|trash|crappy|'
            r'garbage|sucks?|hate|mistakes?|problem|truth|brutal|scam|quietly|dropped|exposed|backlash|caught|fired|banned|over|nobody|no one)\b')
FEATURES = [
    ('S-question', 'a question', lambda t: '?' in t),
    ('S-number', 'a number', lambda t: bool(re.search(r'\d', t))),
    ('S-money', 'a $ figure / price', lambda t: bool(re.search(r'\$\s?\d|\b\d+\s?(k|K|m|M|million|grand)\b|\bprice\b|\bcheap(er)?\b|\bfree\b|\bbudget\b', t))),
    ('S-named', 'a named brand / product / film / person', lambda t: bool(re.search(r'\b' + BRANDS + r'\b', t))),
    ('S-conflict', 'conflict / stakes words (worst, never, trash, quit, wrong ...)', lambda t: bool(re.search(CONFLICT, t, re.I))),
    ('S-you', 'talks to the viewer (you / your)', lambda t: bool(re.search(r"\b(you|your|you're|yours)\b", t, re.I))),
    ('S-first-person', 'first person (I / my / we)', lambda t: bool(re.search(r"\b(I|I'm|I've|my|me|we|we're|our)\b", t))),
    ('S-quote', 'a quoted line', lambda t: bool(re.search(r'["“].+["”]', t))),
    ('S-cliffhanger', 'ends open (... or an unfinished clause)', lambda t: t.rstrip().endswith(('...', '…'))),
    ('S-vs', 'A vs B / comparison wording', lambda t: bool(re.search(r'\b(vs\.?|versus|beats?|better than|instead of)\b', t, re.I))),
    ('S-news', 'news wording (leak, rumor, dropped, announced, price cut, finally)', lambda t: bool(re.search(r'\b(leak(ed|s)?|rumou?rs?|announced|confirmed|finally|price cut|just dropped|launch(ed|es)?|new)\b', t, re.I))),
    ('S-short', '45 characters or less', lambda t: len(t.strip()) <= 45),
    ('S-long', 'over 70 characters (cut off in the feed)', lambda t: len(t.strip()) > 70),
]
HOOK_FEATURES = [('H-' + f[0][2:], 'on-screen hook: ' + f[1], f[2]) for f in FEATURES if f[0] not in ('S-short', 'S-long')] + [
    ('H-one-line', 'on-screen hook on ONE line', lambda t: '\n' not in t.strip()),
    ('H-two-lines', 'on-screen hook on two lines', lambda t: '\n' in t.strip()),
]
COVER_FEATURES = [          # measured on the scrape's A/B thumbnail descriptions ("face + camera + giant 'WHY?'") and on our cover headlines
    ('C-face', 'a face on the cover', lambda t: bool(re.search(r'\bface\b', t, re.I))),
    ('C-one-word', 'ONE giant word', lambda t: len(thumb_words(t).split()) == 1),
    ('C-question', 'the cover text is a question', lambda t: '?' in thumb_words(t)),
    ('C-number', 'a number / $ on the cover', lambda t: bool(re.search(r'\$|\d', thumb_words(t)))),
    ('C-named', 'a named brand / product / film on the cover', lambda t: bool(re.search(r'\b' + BRANDS + r'\b', thumb_words(t)))),
    ('C-long-text', '4+ words on the cover', lambda t: len(thumb_words(t).split()) >= 4),
]
def thumb_words(desc):
    """the words a thumbnail shows: the quoted parts of a scrape description, or the whole text when nothing is quoted (our own headline)"""
    q = ' '.join(a or b for a, b in re.findall(r"'([^']+)'|\"([^\"]+)\"", desc or ''))
    return q if q else ('' if re.search(r'\b(face|camera|studio|text|same as)\b', desc or '', re.I) else (desc or ''))
WIN, LOSE, N_MIN, VIEWS_MIN, DAYS = 1.15, 0.85, 4, 100, 180      # a short under 100 views has a noisy % viewed; the window = shorts_data's deep window
def feats(text, table=FEATURES): return [fid for fid, _, f in table if f(text or '')]
def norm(t): return re.sub(r'[^a-z0-9]+', ' ', (t or '').lower()).strip()
def jl(p): return [json.loads(l) for l in open(p)] if os.path.exists(p) else []
def first_sentence(t):
    t = re.sub(r'#\w+', '', t or '').strip(); m = re.split(r'(?<=[.!?])\s+', t, 1); return m[0].strip() if m else t

def scrape_file():
    """the newest Monday Studio scrape that exists (channel_metrics.json) -> (path, dict)"""
    for p in C.SCRAPE:
        d = C.load(p)
        if d: return p, d
    return None, {}
def scrape_rows():
    p, d = scrape_file(); return (p, d['shorts']) if d.get('shorts') else (None, {})
def studio():
    """what the weekly scrape SAID (its analysis, not its rows): patterns, actions, packaging fixes, working_now, avoid,
    every Test & Compare of both channels - read whole, shown whole in the brief"""
    p, d = scrape_file(); ins = d.get('insights') or {}
    tests = [dict(t, channel='cwc') for t in d.get('ab_tests') or []] + [dict(t, channel='tcl') for t in (d.get('tcl') or {}).get('ab_tests') or []]
    return {'path': p, 'updated': d.get('updated'), 'patterns': ins.get('patterns') or [], 'actions': ins.get('actions') or [], 'fixes': ins.get('packaging_fixes') or [],
            'working_now': d.get('working_now') or [], 'avoid': d.get('avoid') or [], 'ab_tests': [t for t in tests if t.get('titles')]}
def sc_lookup(rows_, who_key, text_key):
    """scrape rows by (account, first 40 chars of the normalised text); a title the scrape shortened with '...' matches by prefix"""
    tab = [(r.get(who_key), norm(re.sub(r'\.\.\.$', '', r.get(text_key) or '')), str(r.get(text_key) or '').endswith('...'), r) for r in rows_]
    def get(who, text):
        nk = norm(text)
        for w, sk, trunc, r in tab:
            if w != who or not sk: continue
            if sk[:40] == nk[:40] or ((trunc or len(sk) < len(nk)) and len(sk) >= 18 and nk.startswith(sk)): return r    # Studio shortens titles, with or without "..."; 18+ chars of prefix is a title, not a stem
        return {}
    return get

def rows():
    """one row per short per platform: {brand, platform, text, kind, f, rel, vrel, metrics} - rel = retention vs the brand's
    platform median, vrel = views vs the brand's platform median"""
    cat = (C.load(f'{C.DATA}/catalog.json') or {}).get('shorts') or []; sp, sc = scrape_rows()
    yt_sc = sc_lookup(sc.get('youtube', []), 'channel', 'title'); tt_sc = sc_lookup(sc.get('tiktok', []), 'account', 'caption')
    raw = []; cut = (datetime.date.today() - datetime.timedelta(days=DAYS)).isoformat()
    for r in cat:
        if (r.get('published') or '') < cut: continue
        b = r['brand']; dur = r.get('duration')
        y = r.get('youtube') or {}; lf = y.get('life') or {}; rt = y.get('retention') or {}
        if lf.get('averageViewPercentage') is not None and (lf.get('views') or 0) >= VIEWS_MIN:
            s = yt_sc(b, r['title'])
            raw.append({'brand': b, 'platform': 'youtube', 'id': y.get('id'), 'text': r['title'], 'kind': 'title', 'published': r['published'],
                        'm': {'pct_viewed': lf['averageViewPercentage'], 'kept_3s': rt.get('kept_3s'), 'stayed': s.get('stayed_to_watch_pct')}, 'views': lf.get('views')})
        t = r.get('tiktok') or {}
        if t.get('avg_watch_s') is not None and (t.get('views') or 0) >= VIEWS_MIN:
            s = tt_sc(b, t.get('text')); d = dur or t.get('duration') or s.get('length_s')
            raw.append({'brand': b, 'platform': 'tiktok', 'id': t.get('url'), 'text': first_sentence(t.get('text')), 'kind': 'caption', 'published': r['published'],
                        'm': {'watch_share': (t['avg_watch_s'] / d) if d else None, 'avg_watch_s': t['avg_watch_s'] if not d else None, 'watched_full': s.get('watched_full_pct'), 'kept_3s': s.get('retention_3s_pct')}, 'views': t.get('views')})
        g = r.get('instagram') or {}
        if g.get('view_rate_3s') is not None and (g.get('views') or 0) >= VIEWS_MIN:
            raw.append({'brand': b, 'platform': 'instagram', 'id': g.get('url'), 'text': first_sentence(g.get('text')), 'kind': 'caption', 'published': r['published'],
                        'm': {'rate_3s': g['view_rate_3s'], 'avg_watch_s': g.get('avg_watch_s')}, 'views': g.get('views')})
    out = []
    for b in {x['brand'] for x in raw}:
        for pf in ('youtube', 'tiktok', 'instagram'):
            grp = [x for x in raw if x['brand'] == b and x['platform'] == pf]
            if len(grp) < N_MIN: continue
            meds = {}
            for k in set(k for x in grp for k in x['m']):
                v = [x['m'][k] for x in grp if x['m'].get(k)]; meds[k] = statistics.median(v) if len(v) >= N_MIN else None
            vm = statistics.median([x['views'] for x in grp if x['views']]) or 1
            for x in grp:
                rels = [x['m'][k] / meds[k] for k in x['m'] if x['m'].get(k) and meds.get(k)]
                if not rels: continue
                out.append(dict(x, rel=round(statistics.median(rels), 3), vrel=round((x['views'] or 0) / vm, 3), f=feats(x['text'])))
    return out

def lift(rs, fid):
    w = [r['rel'] for r in rs if fid in r['f']]; wo = [r['rel'] for r in rs if fid not in r['f']]
    if len(w) < N_MIN or len(wo) < N_MIN: return None, len(w), len(wo), None
    vw = [r['vrel'] for r in rs if fid in r['f']]; vwo = [r['vrel'] for r in rs if fid not in r['f']]
    return round(statistics.median(w) / statistics.median(wo), 2), len(w), len(wo), round(statistics.median(vw) / (statistics.median(vwo) or 1), 2)

def our_hooks():
    """every theme this skill wrote, with Colden's decision and (once posted) its numbers -> hook rows"""
    dec = {}
    for d in jl(f'{C.DATA}/decisions.jsonl'):
        if d.get('stage') == 'theme' and d.get('decision') in ('approved', 'killed') and not d.get('trial'): dec[(d['show'], d['ep'], d['theme'])] = d['decision']
    snaps = jl(f'{C.DATA}/published_snapshots.jsonl'); out = []
    for W in C.works():
        ep = C.episode(W)
        if ep.get('trial'): continue
        for th in (C.load(f'{W}/themes.json') or {}).get('themes', []):
            k = (ep['show'], ep['ep_key'], th['id']); d = dec.get(k)
            if not d: continue
            mine = [s for s in snaps if (s['ep'], s['short']) == (ep['ep_key'], th['id']) and s.get('yt_pct_viewed')]
            out.append({'ep': ep['ep_key'], 'short': th['id'], 'hook': '\n'.join(th.get('hook_text') or []), 'title': th.get('title'), 'decision': d,
                        'f': feats('\n'.join(th.get('hook_text') or []), HOOK_FEATURES), 'yt_pct_viewed': max((s['yt_pct_viewed'] for s in mine), default=None)})
    return out

def build(quiet=False):
    rs = rows(); hooks = our_hooks(); pats = []
    for fid, what, _ in FEATURES:
        lf, nw, nwo, vl = lift(rs, fid)
        per = {}
        for pf in ('youtube', 'tiktok', 'instagram'):
            l2, a, b_, v2 = lift([r for r in rs if r['platform'] == pf], fid)
            if l2 is not None: per[pf] = {'lift': l2, 'n': a, 'views_lift': v2}
        st = 'WEAK'
        if lf is not None and lf >= WIN: st = 'WIN'
        elif lf is not None and lf <= LOSE: st = 'LOSE'
        ex = [r['text'] for r in sorted([r for r in rs if fid in r['f']], key=lambda r: -r['rel'])[:2]]
        pats.append({'id': fid, 'kind': 'title', 'what': what, 'status': st, 'retention_lift': lf, 'views_lift': vl, 'n_with': nw, 'n_without': nwo, 'per_platform': per, 'examples': ex})
    ap = [h for h in hooks if h['decision'] == 'approved']; ki = [h for h in hooks if h['decision'] == 'killed']
    for fid, what, _ in HOOK_FEATURES:
        a = sum(fid in h['f'] for h in ap); k = sum(fid in h['f'] for h in ki); posted = [h for h in hooks if h.get('yt_pct_viewed') is not None]
        st = 'WEAK'; lf = None
        if len(posted) >= 2 * N_MIN:
            w = [h['yt_pct_viewed'] for h in posted if fid in h['f']]; wo = [h['yt_pct_viewed'] for h in posted if fid not in h['f']]
            if len(w) >= N_MIN and len(wo) >= N_MIN:
                lf = round(statistics.median(w) / statistics.median(wo), 2); st = 'WIN' if lf >= WIN else 'LOSE' if lf <= LOSE else 'WEAK'
        pats.append({'id': fid, 'kind': 'hook', 'what': what, 'status': st, 'retention_lift': lf, 'approved_with': a, 'killed_with': k, 'n_posted': len(posted),
                     'examples': [h['hook'].replace('\n', ' / ') for h in ap if fid in h['f']][:2]})
    ST = studio(); done = [t for t in ST['ab_tests'] if t.get('status') == 'done' and t.get('winner') in ('A', 'B', 'C') and t.get('thumbs')]
    for fid, what, f in COVER_FEATURES:
        ab = 0; ex = []
        for t in done:
            k = t['winner']; th_ = t['thumbs'] or {}
            same = lambda d: th_.get((re.search(r'same as ([ABC])', d or '', re.I) or [None, ''])[1], d) if re.search(r'same as [ABC]', d or '', re.I) else d   # "same as A: ..." -> A's thumbnail
            w = same(th_.get(k) or ''); ls = [same(th_.get(x) or '') for x in 'ABC' if x != k]
            ls = [x for x in ls if x and x != w]                                                       # a loser with the same thumbnail as the winner says nothing about the thumbnail
            if not w or not ls: continue
            hw = f(w); hl = sum(bool(f(x)) for x in ls)
            if hw and hl == 0: ab += 1; ex.append(w)
            elif not hw and hl == len(ls): ab -= 1
        st_ = 'WIN' if ab >= 2 else 'LOSE' if ab <= -2 else 'WEAK'
        pats.append({'id': fid, 'kind': 'cover', 'what': what, 'status': st_, 'ab_score': ab, 'n_tests': len(done), 'examples': ex[:2]})
    lessons = [{'id': f'AB-{t.get("video_id")}', 'channel': t['channel'], 'winner_title': t['titles'].get(t['winner']), 'loser_titles': [t['titles'].get(x) for x in 'ABC' if x != t['winner']],
                'winner_thumb': (t.get('thumbs') or {}).get(t['winner']), 'loser_thumbs': [(t.get('thumbs') or {}).get(x) for x in 'ABC' if x != t['winner']],
                'share': (t.get('watch_time_share_pct') or {}).get(t['winner'])} for t in ST['ab_tests'] if t.get('status') == 'done' and t.get('winner') in ('A', 'B', 'C')]
    sp, sc = scrape_rows(); best = sorted(rs, key=lambda r: -r['rel'])[:12]; worst = sorted(rs, key=lambda r: r['rel'])[:6]
    body = {'studio': {k: ST[k] for k in ('path', 'updated', 'patterns', 'actions', 'fixes', 'working_now', 'avoid')}, 'ab_lessons': lessons, 'ab_running': sum(1 for t in ST['ab_tests'] if t.get('status') != 'done'),
            'catalog_rows': len(rs), 'by_platform': {pf: sum(1 for r in rs if r['platform'] == pf) for pf in ('youtube', 'tiktok', 'instagram')}, 'scrape': sp, 'scrape_updated': sc.get('updated'),
            'patterns': pats, 'our_hooks': len(hooks), 'best': [{'brand': r['brand'], 'platform': r['platform'], 'text': r['text'], 'rel': r['rel'], 'vrel': r['vrel'], 'f': r['f']} for r in best],
            'worst': [{'brand': r['brand'], 'platform': r['platform'], 'text': r['text'], 'rel': r['rel'], 'f': r['f']} for r in worst],
            'catalog_made': (C.load(f'{C.DATA}/catalog.json') or {}).get('made_at')}
    bid = hashlib.sha1(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()[:10]
    B = dict(body, id=bid, built_at=C.now()); C.save(f'{C.DATA}/packaging_brief.json', B); open(f'{C.DATA}/packaging_brief.md', 'w').write(md(B))
    if not quiet: print(f'{C.DATA}/packaging_brief.md  (brief {bid}: {len(rs)} short-platform rows {B["by_platform"]}, {len(hooks)} of our hooks, scrape {sc.get("updated")})')
    return B

def md(B):
    L = [f'# Shorts packaging brief {B["id"]} - read before writing titles, on-screen hooks and captions',
         f'{B["catalog_rows"]} short-platform rows {B["by_platform"]} - the last {DAYS} days, {VIEWS_MIN}+ views, each short against its brand\'s median on that platform, RETENTION first, views second; scrape {B["scrape_updated"]}. Put `"brief": "{B["id"]}"` at the top of themes.json and copy.json.', '']
    for kind, lab in (('title', 'Title / caption-hook patterns (YouTube titles, TikTok + Instagram caption first sentences)'), ('hook', 'On-screen hook patterns (our own shorts: Colden\'s approvals / kills, then their numbers)'),
                      ('cover', 'Cover (thumbnail) patterns - what the winning thumbnail showed in the finished Test & Compare runs (cover.py add gates the headline on these + the title WINs)')):
        L.append(f'## {lab}')
        for s in ('WIN', 'LOSE', 'WEAK'):
            for p in [p for p in B['patterns'] if p['kind'] == kind and p['status'] == s]:
                if kind == 'title':
                    ev = f'retention x{p["retention_lift"]}, views x{p["views_lift"]} (n {p["n_with"]} vs {p["n_without"]})' if p['retention_lift'] is not None else f'too few shorts (n {p["n_with"]} vs {p["n_without"]})'
                    if p['per_platform']: ev += ' - ' + ', '.join(f'{k} x{v["lift"]} (n {v["n"]})' for k, v in p['per_platform'].items())
                elif kind == 'cover':
                    ev = f'A/B {p["ab_score"]:+d} over {p["n_tests"]} finished tests (only the winner had it = +1, only the losers = -1)'
                else:
                    ev = f'approved {p["approved_with"]}, killed {p["killed_with"]}' + (f', posted retention x{p["retention_lift"]} (n {p["n_posted"]})' if p['retention_lift'] is not None else f', {p["n_posted"]} posted (need {2 * N_MIN} for a lift)')
                L.append(f'- **{s}** `{p["id"]}` {p["what"]} - {ev}' + (f' - e.g. "{p["examples"][0]}"' if p['examples'] and s != 'WEAK' else ''))
        L.append('')
    L += ['## The 12 best-retained shorts (relative to their brand + platform)'] + [f'- {b["brand"]} {b["platform"]} x{b["rel"]} (views x{b["vrel"]}): "{b["text"]}"  {b["f"]}' for b in B['best']]
    L += ['', '## The 6 worst'] + [f'- {b["brand"]} {b["platform"]} x{b["rel"]}: "{b["text"]}"  {b["f"]}' for b in B['worst']]
    ST = B.get('studio') or {}
    L += ['', f'## What Studio said this week (the Monday scrape {ST.get("updated")}, its own analysis - read it, it covers Shorts + TikTok too)']
    L += [f'- pattern: {x}' for x in ST.get('patterns', [])] + [f'- action: {x}' for x in ST.get('actions', [])] + [f'- working now: {x}' for x in ST.get('working_now', [])] + [f'- avoid: {x}' for x in ST.get('avoid', [])]
    L += [f'- long-form fix: "{f.get("title")}" -> "{f.get("suggested_title")}" ({f.get("why")})' for f in ST.get('fixes', [])]
    L += ['', f'## Test & Compare lessons ({len(B.get("ab_lessons") or [])} finished, {B.get("ab_running", 0)} running) - the winning title AND what its thumbnail showed']
    L += [f'- {l["channel"]} {l["id"]} won with {l["share"]} % watch time: "{l["winner_title"]}" [{l["winner_thumb"]}] over ' + ' / '.join(f'"{t}" [{h}]' for t, h in zip(l['loser_titles'], l['loser_thumbs'])) for l in B.get('ab_lessons') or []] or ['- none finished yet']
    L += ['', '## How to use it',
          '- Every theme\'s title AND on-screen hook: write them FROM the WIN patterns above (a named thing, a number, a conflict ... whatever the data says); a LOSE pattern only as a declared test (`explore`).',
          '- `learned` on every theme and every copy record: 2+ pattern ids from this brief with how they shaped the words.',
          '- yt_title and the caption\'s first sentence are the title for TikTok / Instagram viewers: the same rules.',
          '- The AI cover headline: a line of the short\'s hook / title (already gated), or words that carry a WIN title or cover pattern; the scene idea follows "What Studio said" (gear + money + a named thing, not abstract talk).',
          '- n is small on some lines; a WEAK line is not a finding. The brief grows with every pull and every posted short.']
    return '\n'.join(L) + '\n'

def current(): return C.load(f'{C.DATA}/packaging_brief.json') or {}

def problems(obj, where, texts, hook=None):
    """the gate shared by check.py and postcopy.py: obj = the record carrying "learned" / "explore"; texts = the title-like
    strings it wrote (title, yt_title, caption hook); hook = the on-screen hook text (themes only) -> problems"""
    p = []; B = current()
    if not B: return [f'{where}: no shorts packaging brief - pack_learn.py build (shorts_data.py summary runs it)']
    ids = {x['id'] for x in B['patterns']}; le = obj.get('learned') or []
    if len(le) < 2 or any(not isinstance(x, dict) or x.get('id') not in ids or len(str(x.get('how', ''))) < 15 for x in le):
        p.append(f'{where}: "learned" needs 2+ entries {{"id": <a pattern id from data/shorts/packaging_brief.md>, "how": "<how it shaped these words>"}} - unknown ids: {[x.get("id") for x in le if isinstance(x, dict) and x.get("id") not in ids]}')
    win = {x['id'] for x in B['patterns'] if x['kind'] == 'title' and x['status'] == 'WIN'}; lose = {x['id'] for x in B['patterns'] if x['kind'] == 'title' and x['status'] == 'LOSE'}
    hwin = {x['id'] for x in B['patterns'] if x['kind'] == 'hook' and x['status'] == 'WIN'}; hlose = {x['id'] for x in B['patterns'] if x['kind'] == 'hook' and x['status'] == 'LOSE'}
    ex = obj.get('explore') or {}
    have = set()
    for k, t in texts.items():
        if not t: continue
        f = set(feats(t)); have |= f & win
        bad = sorted(f & lose)
        if bad and len(str(ex.get(k, ''))) < 15: p.append(f'{where}: {k} carries LOSE pattern(s) {bad} - change it, or declare the test: "explore": {{"{k}": "<what it tests and why>"}}')
    if hook is not None:
        f = set(feats(hook, HOOK_FEATURES)); have |= {'H' + x[1:] for x in f & {'H' + w[1:] for w in win}} | (f & hwin)
        bad = sorted(f & hlose)
        if bad and len(str(ex.get('hook_text', ''))) < 15: p.append(f'{where}: hook_text carries LOSE pattern(s) {bad} - change it, or declare the test: "explore": {{"hook_text": "..."}}')
    if win and not have: p.append(f'{where}: none of {list(texts)}{" / hook_text" if hook is not None else ""} carries a WIN pattern ({sorted(win)}) - the data says what holds viewers; use it')
    return p

def headline_ok(headline, th=None, where='cover'):
    """the gate on an AI cover's headline (cover.py add): it is a line of the short's gated hook_text / title (same words), or it
    carries a WIN title pattern or a WIN cover pattern of the current brief -> problems"""
    B = current()
    if not B: return [f'{where}: no shorts packaging brief - pack_learn.py build']
    hw = lambda t: set(re.findall(r"[a-z0-9$>%']+", (t or '').lower()))
    words = hw(headline)
    if not words: return [f'{where}: empty headline']
    allowed = set()
    for line in (th or {}).get('hook_text') or []: allowed |= hw(line)
    allowed |= hw((th or {}).get('title'))
    if th and words <= allowed: return []
    win = {x['id'] for x in B['patterns'] if x['kind'] == 'title' and x['status'] == 'WIN'}; cwin = {x['id'] for x in B['patterns'] if x['kind'] == 'cover' and x['status'] == 'WIN'}
    fs = set(feats(headline)) | set(feats(headline.title())) | set(feats(headline, COVER_FEATURES))      # headlines are UPPER CASE; the brand list is cased like titles
    if fs & win or fs & cwin: return []
    return [f'{where}: the headline "{headline}" is not made of the short\'s hook / title words and carries no WIN pattern ({sorted(win | cwin)}) - the data drives the cover words too (Colden 2026-10-02)']

def brief_ok(obj, where):
    """the record (themes.json / copy.json) names the CURRENT brief - the brief was read"""
    B = current()
    if not B: return [f'{where}: no shorts packaging brief - pack_learn.py build']
    if obj.get('brief') != B['id']: return [f'{where}: "brief" is {obj.get("brief")!r}, the current brief is "{B["id"]}" - READ {C.DATA}/packaging_brief.md (it changed or was never read), then set "brief": "{B["id"]}"']
    return []

if __name__ == '__main__':
    a = sys.argv[1:]
    if a and a[0] == 'build': build()
    elif len(a) >= 2 and a[0] == 'features': print(feats(a[1]), feats(a[1], HOOK_FEATURES))
    else: C.fail(__doc__)
