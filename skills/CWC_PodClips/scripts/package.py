"""package.py - the YouTube package of every LOCKED clip version (ruling 37: packaging is this skill's; the posting plan,
uploads and Studio work are the aggregator's). Rules: references/carried_rules.md + the show file's `packaging` block;
every rule is a gate here.

  package.py facts <WORK>                     per locked clip x channel -> WORK/package/<id>/facts.<ch>.json : the master,
                                              its length, the captions (captions.py), the CHAPTER POINTS on the clip clock
                                              (0:00 = the cold open, then the first word of each part of the story), who
                                              speaks in the clip (handles), the claims of the theme, the full-episode link.
                                              The full episode must be PUBLIC to be linked: when it is not found and the
                                              channel pull is older than 36 h, facts stops and asks for a fresh pull.
  (Claude writes WORK/package/<id>/copy.<ch>.json - the words; SKILL.md Stage 3 says how:)
      {"titles": [3 options], "summary": "1-4 sentences", "chapters": [{"part": "hook"|0|1|.., "text": ".."}],
       "pinned": "an engagement question", "topic_tags": [".."], "hook_headline": "2-4 WORDS", "hook_accent": "WORD",
       "ai_headline": "<= 3 WORDS" (only when hook_headline has 4), "thumb_emotion": "smile|laughing|angry|confused",
       "claims_checked": [{"claim": "..", "status": "verified|announced|rumor|opinion|quote|own-experience", "source": "url or Pnnnn"}],
       "brief": "<id of data/packaging_brief.md>", "learned": [{"id": "T-..|H-..|AB-..", "how": ".."}, ..2+], "explore": {"<1-3>": "why a LOSE pattern is tested"}}
      (ruling 44: pack_learn.py - the weekly data turned into patterns; package.py facts rebuilds it)
      after his pick on Telegram (tg_pack.py writes "A") the same file gets "B", "C" (titles written AFTER the pick)
      and "hook_headline_B" (+ "hook_accent_B"): thumbnail B is the confirmed still with THAT headline, and
      "ab_tests_plan": {"B": "what B tests against A", "C": ".."} - each test title changes one measured feature.
  package.py check <WORK> [<id> <ch>]         every gate (exit 1 = fix the copy)
  package.py build <WORK>                     -> WORK/package/<id>/package.<ch>.json (the finished fields) and, when
                                              every locked upload is complete, WORK/delivery.json (the aggregator's
                                              input); then the packaging scratch (face scans, candidates) goes to the Trash,
                                              and deliver.py moves every upload to <episode>/Final/Clips on the NAS (ruling 43).
GATES  titles: 3 distinct options, <= 100 characters, no em / en dash, no "|", the first 5 words of each differ; B / C:
       first 5 words differ from A and from each other, never an option he did not pick. Summary 1-4 sentences, no
       hashtag, no dash. Chapters: >= 3, the first at 0:00, each >= 10 s, in order, before the end screen, text <= 60
       chars. Pinned: a question, <= 2 sentences, no link, no CTA filler. Tags: 470-500 characters COUNTED AS YOUTUBE
       COUNTS (commas + 2 quotes for every tag with a space), topic tags first, each <= 30 chars, then the show's stock
       set fills up. Claims: >= 1, each with a status and a source; "released / out now / launched" in the copy needs a
       VERIFIED claim. hook_headline 2-4 words; hook_headline_B (final) present and different. Footer only where the
       show file has one for the channel. Playlists only with known ids. build: the facts belong to the CURRENT lock
       (timeline + master), the master and the SRT are on disk, the A/B/C set is approved on Telegram AS IT IS NOW
       (same three titles, same three files), the three thumbnails differ."""
import os, re, sys, json, glob, time, shutil, datetime
import common as C, captions as CAP, pack_learn as PL

def show(W):
    S = C.show(C.episode(W)['show'])
    if not S.get('packaging'): C.ask(f'the show file shows/{S["id"]}.json has no `packaging` block (channels, handles, footer, tags, playlists, thumbnail rules): this show has never been packaged - ask Colden for its channel(s), playlists and footer first')
    return S
def locked(W):
    L = C.load(f'{W}/lock.json')
    if not L: C.ask('the episode is not locked yet (lock.py) - only locked clips are packaged')
    return L['clips']

def full_episode(W):
    """the full episode's upload on each channel, from the channel data (videos.json): a PUBLIC live / long upload whose
    title carries "Ep. NN" of this episode, published at most 60 days before the clips' intake, and not another show's
    (packaging.full_episode.exclude_title). Colden 2026-10-02: the title ending in the phone emoji is the MOBILE /
    vertical stream - never link to it; use the one without it. Exactly one candidate per channel, else that channel
    stays open (`{FULL_EPISODE_URL}` + needs). -> WORK/package/full_episode.json"""
    ep = C.episode(W); S = show(W); cfg = S['packaging'].get('full_episode') or {}; n = str(ep.get('ep_no') or re.sub(r'\D', '', ep['ep_key'])).lstrip('0'); out = {}
    t_in = datetime.datetime.fromisoformat(ep['intake_at']) if ep.get('intake_at') else None
    for ch in S['packaging']['channels']:
        vs = (C.load(f'{C.DATA}/channels/{ch}/videos.json') or {}).get('videos', [])
        hit = []
        for v in vs:
            t = v.get('title', '')
            if not re.search(rf'\bEp\.?\s*0*{n}\b', t, re.I) or int(v.get('duration') or 0) < 1200: continue
            if any(x.lower() in t.lower() for x in cfg.get('exclude_title', [])): continue
            if cfg.get('require_title') and not any(x.lower() in t.lower() for x in cfg['require_title']): continue
            if t_in and v.get('published'):
                age = (t_in - datetime.datetime.fromisoformat(v['published'].replace('Z', '+00:00'))).days
                if not -30 <= age <= 60: continue
            hit.append(v)
        main = [v for v in hit if '\U0001F4F1' not in v['title']]; pub = [v for v in main if v.get('privacy', 'public') == 'public']
        if len(pub) == 1 and len(main) == 1: out[ch] = {'id': pub[0]['id'], 'url': f'https://youtu.be/{pub[0]["id"]}', 'title': pub[0]['title'], 'published': pub[0].get('published'), 'privacy': 'public', 'skipped_vertical': [v['id'] for v in hit if v not in main]}
        else: out[ch] = {'id': None, 'candidates': [[v['id'], v.get('privacy'), v['title']] for v in hit],
                         'why': 'no upload found' if not main else 'the upload is not public yet' if len(main) == 1 else f'{len(main)} non-vertical uploads match - ask Colden'}
    C.save(f'{W}/package/full_episode.json', out); return out

def chapter_points(W, th, P):
    """0:00 = the cold open; then the first WORD of every body range, through the version's frozen shots (a range that
    touches the previous one shares its shot: the point is still its own first word)"""
    fps = P['fps']; by = {p['id']: p for p in C.load(f'{W}/phrases.json')}; F = lambda t: int(round(float(t) * fps))
    parts = [{'part': 'hook', 't': 0.0, 'what': 'cold open: ' + th['hook']['quote'][:80]}]; body = [s for s in P['shots'] if s['kind'] == 'body']
    for k, r in enumerate(th['body']):
        f = F(by[r['from']]['w'][r.get('start_word') or 0][1])
        s = next((s for s in body if s['a'] <= f < s['b']), None) or next((s for s in body if s.get('range', -1) >= k and s['a'] >= f), None)
        if s: parts.append({'part': k, 't': round((s['rec'] + max(0, f - s['a'])) / fps, 2), 'what': r.get('why', '')})
    return parts

def facts(W):
    ep = C.episode(W); S = show(W); PK = S['packaging']; th = {t['id']: t for t in C.load(f'{W}/themes.json')['themes']}
    people = ep.get('people', []); out = []; full = full_episode(W)
    PL.build()                                             # ruling 44: the packaging brief from this week's data - READ it before writing the copy
    if any(not f.get('id') for f in full.values()):       # an open link on OLD data is not a finding: the episode may be public by now
        import channel_data as CD; fresh_ok, why, _ = CD.fresh(quiet=True)
        if not fresh_ok: C.fail(f'the full episode is not found as a public upload, and the channel data is old ({why}): channel_data.py pull, then package.py facts again')
    for ch, f in full.items(): print(f'full episode on {ch}: ' + (f'{f["url"]} "{f["title"]}" (vertical copy skipped: {f["skipped_vertical"]})' if f.get('id') else f'OPEN - {f["why"]} {f.get("candidates")}'))
    for c in locked(W):
        tid, ch = c['theme'], c['channel']; v = next(x for x in C.load(C.vpath(W, tid), []) if x['channel'] == ch and x['v'] == c['v']); P = C.load(v['plan']); fps = P['fps']
        parts = chapter_points(W, th[tid], P)
        srt, ncues, look = CAP.build(W, tid, ch); cj = C.load(srt[:-4] + '.captions.json')
        said = {}
        for w in CAP.words_on_clip(W, P): said[w[3]] = said.get(w[3], 0) + 1
        hand = [{'name': p.get('full_name') or PK.get('names', {}).get(p['name']) or p['name'], 'handle': p.get('handle') or PK['handles'].get(p['name']), 'guest': not p['host'], 'words': said.get(p['name'], 0)}
                for p in people if said.get(p['name'], 0) >= 5]                         # only who is actually heard in this clip
        F = {'theme': tid, 'channel': ch, 'version': c['v'], 'timeline': c['timeline'], 'master': c['master'], 'seconds': round(P['frames'] / fps, 2), 'end_screen_at': round(P['outro']['C'] / fps, 2),
             'title_placeholder': th[tid]['title'], 'summary_placeholder': th[tid].get('summary'), 'hook_quote': th[tid]['hook']['quote'], 'payoff_quote': th[tid]['payoff'].get('quote'),
             'chapter_points': parts, 'captions': srt, 'caption_cues': ncues, 'caption_names_to_check': look, 'caption_case_varies': cj.get('case_varies'), 'handles': hand,
             'claims': th[tid].get('claims') or [], 'claims_note': th[tid].get('claims_note'), 'news': th[tid].get('news'),
             'timeliness': ((th[tid].get('scores') or {}).get('timeliness') or {}).get('s'), 'thumbnail_idea': th[tid].get('thumbnail'),
             'footer': bool(PK['footer'].get(ch)), 'full_episode': full.get(ch), 'made_at': C.now()}
        C.save(f'{W}/package/{tid}/facts.{ch}.json', F); out.append(F)
        print(f'{tid} {ch}: {C.mmss(F["seconds"])}, chapter points {[(p["part"], C.stamp(p["t"])) for p in parts]}, captions {ncues} cues, heard: {[h["name"] for h in hand]}' + (f'\n   names to check: {look}' if look else '') + (f'\n   case varies: {cj.get("case_varies")}' if cj.get('case_varies') else ''))
    return out

DASH = re.compile('[—–|]'); CTA = re.compile(r'drop it below|comment below|let me know|link in|full episode on|smash|subscribe', re.I)
HEAD = re.compile(r"[A-Z0-9'$%&.,\- ?!]{2,32}")
def first5(t): return ' '.join(re.sub(r"[^a-z0-9' ]", '', t.lower()).split()[:5])
def title_problems(ts, label):
    p = []
    for t in ts:
        if not t or not t.strip(): p.append(f'{label}: an empty title'); continue
        if len(t) > 100: p.append(f'{label}: "{t[:40]}.." is {len(t)} characters (YouTube max 100)')
        if DASH.search(t): p.append(f'{label}: "{t[:40]}.." has an em / en dash or "|" (house style: none)')
    f = [first5(t) for t in ts if t]
    if len(set(f)) != len(f): p.append(f'{label}: the first 5 words must differ between options ({f})')
    return p

def tag_len(tags):
    """how YouTube counts the 500: every tag, a comma between tags, and 2 quotation marks for each tag with a space"""
    return sum(len(t) for t in tags) + max(0, len(tags) - 1) + 2 * sum(1 for t in tags if ' ' in t)
def tags_for(S, ch, topic):
    PK = S['packaging']['tags']; out = []; seen = set()
    for t in [x.strip() for x in topic] + PK['stock']:
        if t and t.lower() not in seen and len(t) <= 30 and tag_len(out + [t]) <= PK['max_chars']: out.append(t); seen.add(t.lower())
    return out

def playlists_for(S, ch, text):
    """the show's clips playlist always + every tailored playlist whose pattern is in the TITLE or SUMMARY. Patterns are
    matched as written (case-sensitive: "RED" the camera, not "red flags"; "Resolve" the app, not "resolve a fight")."""
    PL = S['packaging']['playlists'][ch]; names = list(PL['always'])
    for rx, pls in PL.get('map', {}).items():
        if re.search(rx, text): names += [n for n in pls if n not in names]
    return [{'title': n, 'id': PL['ids'][n]} for n in names if n in PL['ids']]

def description(S, ch, cp, F):
    PK = S['packaging']; fe = F.get('full_episode') or {}
    L = [cp['summary'].strip(), '', PK['full_episode_line'][ch].replace('{FULL_EPISODE_URL}', fe.get('url') or '{FULL_EPISODE_URL}'), '']
    for h in F['handles']:
        if h.get('handle'): L.append(f'{h["name"]}: https://www.youtube.com/{h["handle"]}')
    if PK.get('show_line'): L.append(PK['show_line'])
    L += ['', 'Chapters']
    pts = {p['part']: p['t'] for p in F['chapter_points']}
    for c in cp['chapters']: L.append(f'{C.stamp(pts[c["part"]])} {c["text"]}')
    if PK['footer'].get(ch): L += ['', PK['footer'][ch]]
    return '\n'.join(L)

def check_one(W, tid, ch, final=False):
    S = show(W); F = C.load(f'{W}/package/{tid}/facts.{ch}.json'); cp = C.load(f'{W}/package/{tid}/copy.{ch}.json'); p = []
    if not F: return [f'{tid} {ch}: no facts (package.py facts)']
    if not cp: return [f'{tid} {ch}: no copy.{ch}.json written yet']
    ts = cp.get('titles') or []
    if len(ts) != 3: p.append(f'{tid} {ch}: {len(ts)} title options (3 wanted)')
    p += title_problems(ts, f'{tid} {ch} options')
    if final or cp.get('B') or cp.get('C'):
        A = cp.get('A'); abc = [A, cp.get('B'), cp.get('C')]
        if not A: p.append(f'{tid} {ch}: no title A (his pick)')
        p += title_problems(abc, f'{tid} {ch} A/B/C')
        for k in ('B', 'C'):
            if cp.get(k) and cp[k] in [t for t in ts if t != A]: p.append(f'{tid} {ch}: {k} reuses an option he did not pick')
        hb = (cp.get('hook_headline_B') or '').strip()
        if not hb or not HEAD.fullmatch(hb.upper()) or not 2 <= len(hb.split()) <= 4: p.append(f'{tid} {ch}: hook_headline_B (2-4 words, from title B) is missing or not usable (2-4 words, 32 characters at most, only letters, digits and \' $ % & . , - ? !) - thumbnail B is the still with THAT headline')
        elif hb.upper() == (cp.get('hook_headline') or '').upper(): p.append(f'{tid} {ch}: hook_headline_B equals hook_headline - thumbnail B would repeat option 2')
    p += PL.problems(cp, bool(final or cp.get('B') or cp.get('C')), f'{tid} {ch}')       # ruling 44: the copy uses (and the A/B test feeds) the weekly data
    sm = cp.get('summary', '')
    n_sent = len([s for s in re.split(r'(?<=[.?!])\s+', sm.strip()) if s])
    if not 1 <= n_sent <= 4: p.append(f'{tid} {ch}: summary has {n_sent} sentences (1-4)')
    if '#' in sm or DASH.search(sm): p.append(f'{tid} {ch}: summary has a hashtag or a dash')
    pts = {x['part']: x['t'] for x in F['chapter_points']}; chs = cp.get('chapters') or []
    times = []
    for c in chs:
        if c.get('part') not in pts: p.append(f'{tid} {ch}: chapter part {c.get("part")!r} is not a chapter point ({list(pts)}: "hook" or the index of a body range)'); continue
        times.append(pts[c['part']])
        if not c.get('text') or len(c['text']) > 60 or DASH.search(c['text']): p.append(f'{tid} {ch}: chapter text "{c.get("text")}" (1-60 chars, no dash)')
    if len(chs) < 3: p.append(f'{tid} {ch}: {len(chs)} chapters (YouTube needs >= 3)')
    if times and times[0] != 0: p.append(f'{tid} {ch}: the first chapter must be at 0:00 (part "hook")')
    if times != sorted(times): p.append(f'{tid} {ch}: chapters out of order')
    for a, b in zip(times, times[1:] + [F['end_screen_at']]):
        if int(b) - int(a) < 10: p.append(f'{tid} {ch}: the chapter at {C.stamp(a)} is {int(b) - int(a)} s (YouTube needs >= 10 s) - leave that part out of the chapter list')
    pin = cp.get('pinned', '')
    if not pin or '?' not in pin or 'http' in pin or CTA.search(pin) or len([s for s in re.split(r'(?<=[.?!])\s+', pin.strip()) if s]) > 2: p.append(f'{tid} {ch}: pinned comment must be a question, <= 2 sentences, no link, no CTA filler ("{pin[:60]}")')
    topic = cp.get('topic_tags') or []; tg = tags_for(S, ch, topic); L = tag_len(tg); T = S['packaging']['tags']
    if not topic: p.append(f'{tid} {ch}: no topic tags')
    for t in topic:
        if len(t.strip()) > 30: p.append(f'{tid} {ch}: topic tag "{t}" is over 30 characters (it would be left out)')
    if not T['min_chars'] <= L <= T['max_chars']: p.append(f'{tid} {ch}: tags count {L} characters the way YouTube counts them ({T["min_chars"]}-{T["max_chars"]}) - add topic tags')
    cl = cp.get('claims_checked') or []
    if not cl: p.append(f'{tid} {ch}: claims_checked is empty (what do the title and summary assert, and how do we know)')
    for c in cl:
        if c.get('status') not in ('verified', 'announced', 'rumor', 'opinion', 'quote', 'own-experience') or not c.get('source'): p.append(f'{tid} {ch}: claim "{str(c.get("claim"))[:40]}" needs a status (verified / announced / rumor / opinion / quote / own-experience) and a source (url or phrase id)')
    txt = ' '.join(ts + [sm] + [x for x in (cp.get('A'), cp.get('B'), cp.get('C')) if x])
    if re.search(r'\b(released|out now|launched|now available|ships)\b', txt, re.I) and not any(c.get('status') == 'verified' for c in cl): p.append(f'{tid} {ch}: the copy says released / out now - needs a VERIFIED claim (announced is not released)')
    hh = (cp.get('hook_headline') or '').strip()
    if not HEAD.fullmatch(hh.upper()) or not 2 <= len(hh.split()) <= 4: p.append(f'{tid} {ch}: hook_headline must be 2-4 words, 32 characters at most, only letters, digits and \' $ % & . , - ? ! - the overlay of thumbnail option 2')
    if len(hh.split()) > 3 and not 1 <= len((cp.get('ai_headline') or '').split()) <= 3: p.append(f'{tid} {ch}: hook_headline has 4 words - add "ai_headline" (at most 3 words) for the AI thumbnails')
    if cp.get('thumb_emotion', 'smile') not in ('smile', 'laughing', 'angry', 'confused'): p.append(f'{tid} {ch}: thumb_emotion must be smile / laughing / angry / confused')
    return p

def thumb_meta(R):
    """what each of A / B / C is (for the aggregator: the AI disclosure question, re-creating the test)"""
    k = (R.get('kinds') or [None] * 4)[R['pick']] if R.get('pick') is not None else None; ai = R.get('ai') or {}
    return {'A': {'kind': k, 'model': (ai.get(k) or {}).get('model') if k in ('ai-1', 'ai-2') else None},
            'B': {'kind': 'still + hook overlay', 'model': None}, 'C': {'kind': 'ai', 'model': (ai.get('C') or {}).get('model'), 'for_title': (ai.get('C') or {}).get('for_title')}}

def build(W):
    import tg_pack as TP
    S = show(W); allp = []; done = []; L = C.load(f'{W}/lock.json'); ep = C.episode(W); ck = C.load(f'{W}/checked.json'); ap = {a['id']: a for a in (C.load(f'{W}/approved.json') or {}).get('approved', [])}
    for c in locked(W):
        tid, ch = c['theme'], c['channel']; p = check_one(W, tid, ch, final=True)
        F = C.load(f'{W}/package/{tid}/facts.{ch}.json') or {}; cp = C.load(f'{W}/package/{tid}/copy.{ch}.json') or {}; R = C.load(f'{W}/package/{tid}/thumbs.{ch}.json') or {}
        if F and (F.get('timeline') != c['timeline'] or F.get('master') != c['master']): p.append(f'{tid} {ch}: the facts were made for "{F.get("timeline")}", the lock now holds "{c["timeline"]}" - run package.py facts again (captions and chapter times changed)')
        for f, what in ((c['master'], 'master'), (F.get('captions', ''), 'captions (.srt)')):
            if not os.path.exists(f): p.append(f'{tid} {ch}: the {what} file is not on disk: {f}')
        okk, why = TP.approved(W, tid, ch)
        if not okk: p.append(f'{tid} {ch}: {why}')
        abc = R.get('abc') or {}
        for k in 'ABC':
            if not os.path.exists(abc.get(k, '')): p.append(f'{tid} {ch}: thumbnail {k} missing')
        if all(os.path.exists(abc.get(k, '')) for k in 'ABC') and len({C.sha_file(abc[k]) for k in 'ABC'}) != 3: p.append(f'{tid} {ch}: two of the A/B/C thumbnails are the same picture')
        if p: allp += p; continue
        desc = description(S, ch, cp, F); t = ck['themes'].get(tid, {}); news = F.get('news') if (F.get('news') or {}).get('time_sensitive') else None
        pk = {'theme': tid, 'channel': ch, 'version': c['v'], 'timeline': c['timeline'], 'master': c['master'], 'master_carries_stinger_of': ch, 'resolution': c.get('res'), 'loudness': c.get('loudness'),
              'captions': F['captions'], 'caption_names_to_check': F.get('caption_names_to_check'), 'seconds': F['seconds'], 'midroll_possible': F['seconds'] >= 480,
              'slug': t.get('slug'), 'hook_quote': F.get('hook_quote'), 'titles': {'A': cp['A'], 'B': cp['B'], 'C': cp['C']}, 'thumbnails': {k: abc[k] for k in 'ABC'}, 'thumbnail_meta': thumb_meta(R),
              'description': desc, 'tags': tags_for(S, ch, cp['topic_tags']), 'playlists': playlists_for(S, ch, cp['A'] + ' ' + cp['summary']), 'category': S['packaging']['category'], 'flags': S['packaging']['flags'],
              'pinned_comment': cp['pinned'], 'chapters': [{'t': {x['part']: x['t'] for x in F['chapter_points']}[x['part']], 'text': x['text']} for x in cp['chapters']],
              'claims_checked': cp['claims_checked'], 'news': news, 'timeliness': F.get('timeliness'), 'score': t.get('total'), 'manual_override': bool((ap.get(tid) or {}).get('manual_override')),
              'suggested_channel': (t.get('suggest') or {}).get('channel'), 'full_episode': F.get('full_episode'), 'needs': ['FULL_EPISODE_URL'] if '{FULL_EPISODE_URL}' in desc else [], 'built_at': C.now()}
        pk['tags_youtube_count'] = tag_len(pk['tags'])
        pk.update(brief=cp.get('brief'), learned=cp.get('learned'), explore=cp.get('explore') or {}, ab_tests_plan=cp.get('ab_tests_plan'),
                  title_features={k: PL.feats(pk['titles'][k]) for k in 'ABC'})     # what each test title changes: the next brief reads the winner against it
        C.save(f'{W}/package/{tid}/package.{ch}.json', pk); done.append(pk)
    for x in allp: print('  PROBLEM:', x)
    if allp: return 1
    order = sorted({p['theme'] for p in done}, key=lambda t: (not next(p for p in done if p['theme'] == t)['news'], -(next(p for p in done if p['theme'] == t)['score'] or 0)))
    for p in done: p['push_order'] = order.index(p['theme']) + 1; p['both_channels'] = sum(1 for x in done if x['theme'] == p['theme']) > 1; p['package_file'] = f'{W}/package/{p["theme"]}/package.{p["channel"]}.json'; C.save(p['package_file'], p)
    full = C.load(f'{W}/package/full_episode.json', {}) or {}
    D = {'kind': 'cwc_podclips_delivery', 'version': 2, 'at': C.now(), 'lock_at': L.get('at'), 'show': ep['show'], 'show_name': ep['show_name'], 'episode': ep['ep_key'], 'podcut': ep['cut'],
         'episode_published': next((f.get('published') for f in full.values() if f.get('published')), None), 'full_episode': full,
         'rules_for_the_plan': {'primary_channel_first': S['channels']['primary'], 'secondary_min_delay_hours': S['channels']['secondary_min_delay_hours'], 'news_first_then_push_order': True,
                                'default_window_days_after_the_show': 7, 'one_long_form_per_channel_per_day': True, 'clips_around': '2 PM ET', 'no_premieres': True, 'no_short_on_top_of_the_same_topic_clip': True,
                                'read_studio_scheduled_queue_first': True, 'end_screens_link_public_only': True, 'each_master_only_on_its_own_channel': 'the stinger is the channel\'s',
                                'one_plan_one_approval': True, 'source': 'Colden 2026-09-15 / 2026-10-01 / 2026-10-02 - references/aggregator_handoff.md'},
         'results_loop': 'after publish: learn.py link <WORK> <theme> <cwc|tcl> <videoId>  (ties the decision log to the video for the next episode\'s learnings)',
         'clips': sorted(done, key=lambda p: (p['push_order'], p['channel']))}
    C.save(f'{W}/delivery.json', D); print(f'delivery.json: {len(D["clips"])} clip uploads ready for the aggregator (push order: {order})')
    clean_scratch(W)
    import deliver                                         # ruling 43: the final step - Final/Clips on the NAS, the Mac cleaned
    return deliver.main(W, False)

def clean_scratch(W):
    """ruling 36 for the packaging stage: what the delivered package does not rely on goes to the Trash (never deleted)"""
    trash = os.path.expanduser(f'~/.Trash/CWC_PodClips {C.episode(W)["show"]} {C.episode(W)["ep_key"]} package {time.strftime("%Y%m%d-%H%M%S")}'); n = 0
    for d in [f'{W}/package/_faces'] + glob.glob(f'{W}/package/*/thumbs/*/cand') + glob.glob(f'{W}/package/*/thumbs/*/_near') + glob.glob(f'{W}/package/*/thumbs/*/_hook'):
        if os.path.isdir(d): dest = f'{trash}/{os.path.relpath(d, W)}'; os.makedirs(os.path.dirname(dest), exist_ok=True); shutil.move(d, dest); n += 1
    if n: print(f'packaging scratch: {n} folder(s) moved to {trash}')

if __name__ == '__main__':
    a = sys.argv[1:]
    if len(a) < 2: C.fail(__doc__)
    cmd, W = a[0], os.path.abspath(a[1])
    if cmd == 'facts': facts(W)
    elif cmd == 'check':
        items = [(a[2], a[3])] if len(a) >= 4 else [(c['theme'], c['channel']) for c in locked(W)]
        probs = [x for tid, ch in items for x in check_one(W, tid, ch)]
        for x in probs: print('  PROBLEM:', x)
        print('copy OK' if not probs else f'{len(probs)} problem(s)'); sys.exit(1 if probs else 0)
    elif cmd == 'build': sys.exit(build(W))
    else: C.fail(__doc__)
