"""selftest.py - every gate of check.py on a synthetic episode (no Resolve, no network, no Telegram, nothing of a real
episode touched: it runs in a temp folder through CWC_ROOT). Run after ANY change to check.py / themes.py / rubric.json.
Exit 0 = every gate fired exactly when it should."""
import os, sys, json, copy, shutil, tempfile
tmp = tempfile.mkdtemp(prefix='podclips_selftest_'); os.environ['CWC_ROOT'] = tmp
import common as C, themes as T, check as CK, coldread
W = f'{tmp}/clips/creative-lens/EpTEST'; os.makedirs(f'{W}/cold'); os.makedirs(f'{W}/platform')
who = ['Colden', 'Jake', 'Nick']; ph = []
for i in range(900):
    ph.append({'id': f'P{i + 1:04d}', 'who': who[i % 3], 'start': i * 4.0, 'end': i * 4.0 + 3.6, 'b0': 60 + i * 4.0, 'b1': 60 + i * 4.0 + 3.6, 'text': f'Sentence number {i + 1} is about the camera topic today.', 'n': 9, 'p_min': 0.9})
C.save(f'{W}/phrases.json', ph)
C.save(f'{W}/episode.json', {'show': 'creative-lens', 'show_name': 'The Creative Lens', 'ep_key': 'EpTEST', 'ep_no': 'TEST', 'cut': 'TEST (L)', 'plan_sha': 'x', 'podcut_cache': tmp, 'trial': 'selftest', 'rules': C.RULES,
                             'specials': [{'start': 3300.0, 'end': 3340.0, 'base': [3360, 3400]}], 'people': [{'name': 'Colden', 'host': True}, {'name': 'Jake', 'host': True}, {'name': 'Nick', 'host': False, 'full_name': 'Nick Williams', 'handle': '@WillCoMedia'}], 'duration': 3600})
for ch in ('cwc', 'tcl'): C.save(f'{tmp}/data/channels/{ch}/videos.json', {'pulled_at': C.now(), 'videos': [{'id': 'OWNVIDEO001'}]})
C.save(f'{W}/platform/a.json', {'results': [{'id': 'PLAT2X', 'outlier': 3.0}, {'id': 'PLATFLAT', 'outlier': 0.8}]})
C.save(f'{W}/waivers.json', {'scrape_stale': {'by': 'selftest', 'at': C.now()}})
def P(i): return f'P{i:04d}'
def theme(n, a, b, **kw):
    """a clip of phrases a..b (4 s each)"""
    sc = {d: {'s': 4, 'why': 'a reason long enough to count as one'} for d in CK.DIMS}
    sc['channel_fit']['evidence'] = ['OWNVIDEO001']; sc['platform'] = {'s': 3, 'why': 'a reason long enough to count as one', 'evidence': ['PLATFLAT']}; sc['timeliness']['s'] = 2
    t = {'id': f't{n:02d}', 'slug': f'theme-{n}', 'title': f'Theme {n} title', 'summary': 'One sentence about it. And a second one.', 'thumbnail': 'Colden holding the camera, text: WHY?',
         'evidence_line': 'matches OWNVIDEO001', 'hook': {'from': P(a + 3), 'to': P(a + 4), 'quote': f'Sentence number {a + 3} is about the camera topic today'},
         'body': [{'from': P(a), 'to': P(b), 'why': 'all'}], 'payoff': {'from': P(b), 'to': P(b), 'quote': f'Sentence number {b} is about the camera topic'},
         'scores': sc, 'news': {'time_sensitive': False}, 'claims': [], 'claims_note': 'synthetic'}
    t.update(kw); return t
def cold(Wk, t, **kw):
    v = {'hook_clear': 5, 'payoff_answers_hook': 5, 'self_contained': 5, 'missing_context': [], 'minor_gaps': ['a host is not introduced'], 'weak_stretches': [], 'title_delivered': True, 'would_leave_at': 'nowhere', 'verdict': 'PASS', 'one_line': 'x'}
    v.update(kw); v.update({'theme': t['id'], 'text_sha': C.sha_text(Wk.assemble(t)), 'recorded_at': C.now()}); C.save(f'{W}/cold/{t["id"]}.json', v)
def run(themes, colds=True, cold_kw=None):
    C.save(f'{W}/themes.json', {'themes': themes}); Wk = T.Work(W)
    if colds:
        for t in themes:
            try: cold(Wk, t, **((cold_kw or {}).get(t['id'], {})))
            except Exception: pass
    return CK.run(W, write=False)
ok = True
def expect(name, cond):
    global ok; ok &= bool(cond); print(('PASS  ' if cond else 'FAIL  ') + name)
# 120 phrases = 8:00 of ranges (+ hook + stinger + end screen)
base = [theme(i + 1, 1 + i * 130, 120 + i * 130) for i in range(6)]
def quiet(*a, **k):
    sys.stdout = open(os.devnull, 'w')
    try: return run(*a, **k)
    finally: sys.stdout = sys.__stdout__
code, out = quiet(copy.deepcopy(base))
expect('6 clean themes -> exit 0, 5 delivered, 1 runner-up', code == 0 and len(out['deliver']) == 5 and len(out['runner_ups']) == 1)
t = copy.deepcopy(base); t[0]['hook']['quote'] = 'Words that were never said in the show'
expect('a hook quote that is not in the transcript -> structural exit 1', quiet(t)[0] == 1)
t = copy.deepcopy(base); t[0]['payoff'] = {'from': P(50), 'to': P(50), 'quote': 'Sentence number 50 is about the camera topic'}
expect('payoff far from the end of the last range -> structural', quiet(t)[0] == 1)
t = copy.deepcopy(base); t[0]['body'] = [{'from': P(1), 'to': P(80)}, {'from': P(60), 'to': P(120)}]
expect('the same footage twice inside one clip -> structural', quiet(t)[0] == 1)
t = copy.deepcopy(base); t[0]['scores']['timeliness']['s'] = 5
expect('timeliness 5 without a dated news source -> structural', quiet(t)[0] == 1)
t = copy.deepcopy(base); t[0]['scores']['channel_fit']['evidence'] = ['NOTAVIDEO']
expect('channel evidence id that is not in the channel data -> structural', quiet(t)[0] == 1)
t = copy.deepcopy(base); t[0]['summary'] = 'One. Two. Three sentences here.'
expect('a 3-sentence summary -> structural', quiet(t)[0] == 1)
t = copy.deepcopy(base); t[0]['title'] = 'A title — with an em dash'
expect('an em dash in the title -> structural', quiet(t)[0] == 1)
t = copy.deepcopy(base); t[3] = theme(4, 775, 894)
expect('a screen share inside the clip that is not declared -> structural', quiet(t)[0] == 1)
t[3]['shares'] = [{'at': '55:00', 'what': 'the DJI product page', 'integral': True}]
expect('...declared -> passes', quiet(t)[0] == 0)
t = copy.deepcopy(base); t[0] = theme(1, 1, 60)
expect('a 4:20 clip without a length_note -> structural', quiet(t)[0] == 1)
t[0]['length_note'] = 'the segment ends on its answer at four minutes; more would be filler'
expect('...with a length_note -> passes (short is fine, never padded)', quiet(t)[0] == 0)
t = copy.deepcopy(base); t[0] = theme(1, 1, 30, length_note='a reason that is long enough to be read')
c, o = quiet(t); expect('a 2:20 clip -> held (under 3 min)', 't01' not in o['deliver'] and any('3-15' in w for h in o['held'] if h['id'] == 't01' for w in h['why']))
t = copy.deepcopy(base); t[1] = theme(2, 100, 219)                     # shares phrases 100-120 (84 s of ~8:20) with t01
c, o = quiet(t); expect('two clips sharing more than 10 % -> the lower-ranked one is held', len([x for x in ('t01', 't02') if x in o['deliver']]) == 1)
t = copy.deepcopy(base); t[1] = theme(2, 116, 235)                     # shares 5 phrases (20 s = 4 %)
c, o = quiet(t); expect('two clips sharing 4 % -> both delivered', 't01' in o['deliver'] and 't02' in o['deliver'])
[os.remove(f'{W}/cold/{f}') for f in os.listdir(f'{W}/cold')]
c, o = quiet(copy.deepcopy(base), colds=False); expect('no cold read -> nothing delivered, flagged (exit 2)', c == 2 and not o['deliver'] and 'too_few' in o['blocks'])
t = copy.deepcopy(base); quiet(t); t[0]['body'][0]['to'] = P(119); t[0]['payoff'] = {'from': P(119), 'to': P(119), 'quote': 'Sentence number 119 is about the camera topic'}
C.save(f'{W}/themes.json', {'themes': t}); sys.stdout = open(os.devnull, 'w'); c, o = CK.run(W, write=False); sys.stdout = sys.__stdout__
expect('a theme edited after its cold read -> held until it is read again', any('changed after its cold read' in w for h in o['held'] if h['id'] == 't01' for w in h['why']))
c, o = quiet(copy.deepcopy(base), cold_kw={'t02': {'verdict': 'FAIL', 'missing_context': ['who is "he"?'], 'self_contained': 2}})
expect('cold read FAIL -> held', 't02' not in o['deliver'])
c, o = quiet(copy.deepcopy(base), cold_kw={'t03': {'hook_clear': 3, 'payoff_answers_hook': 3, 'self_contained': 3}})
expect('the reviewer caps the author\'s hook / payoff / self-contained scores', o['themes']['t03']['scores']['hook'] == 3 and o['themes']['t03']['total'] < o['themes']['t01']['total'])
t = copy.deepcopy(base); t[2]['scores']['platform'] = {'s': 5, 'why': 'a reason long enough to count as one', 'evidence': ['PLATFLAT']}
c, o = quiet(t); expect('platform 5 citing only a 0.8x video -> held', 't03' not in o['deliver'])
t[2]['scores']['platform']['evidence'] = ['PLAT2X']; c, o = quiet(t); expect('...citing a 3x outlier -> delivered', 't03' in o['deliver'])
t = copy.deepcopy(base); t[5]['scores']['timeliness']['s'] = 5; t[5]['news'] = {'time_sensitive': True, 'event': 'launch', 'date': '2026-09-30', 'source_url': 'https://example.com'}
for d in ('story', 'package'): t[5]['scores'][d]['s'] = 3
c, o = quiet(t); expect('a news theme ranks first even with a lower total', o['deliver'][0] == 't06')
t = copy.deepcopy(base)
for x in t[:4]: x['scores']['story']['s'] = 2
c, o = quiet(t); expect('only 2 themes pass -> exit 2, flagged, not padded', c == 2 and len(o['deliver']) == 2 and o.get('flag'))
# ---- soft pass (Colden 2026-10-01: "soften scoring and send the best themes ... something going on my channel")
def soften(t):
    for d in ('channel_fit', 'platform', 'timeliness'): t['scores'][d] = {'s': 1, 'why': 'a reason long enough to count as one'}
    return t
t = copy.deepcopy(base); [soften(x) for x in t[2:]]                    # 2 strong (74.3), 4 soft (62.9)
c, o = quiet(t); expect('2 strong + 4 soft -> softened: 5 delivered, strong ones first, exit 0', c == 0 and o['softened'] and o['deliver'][:2] == ['t01', 't02'] and len(o['deliver']) == 5 and len(o['runner_ups']) == 1)
t = copy.deepcopy(base); [soften(x) for x in t[3:]]                    # 3 strong, 3 soft
c, o = quiet(t); expect('3 strong + 3 soft -> NOT softened: only the 3 strong are delivered, soft ones wait as runner-ups', c == 0 and not o['softened'] and o['deliver'] == ['t01', 't02', 't03'] and len(o['runner_ups']) == 3)
t = copy.deepcopy(base); [soften(x) for x in t]
for x in t[:4]: x['scores']['package']['s'] = 2; x['scores']['footage']['s'] = 1
c, o = quiet(t); expect('under the soft line or under a floor -> still held; fewer than 3 left -> flag', c == 2 and len(o['deliver']) == 2 and 'too_few' in o['blocks'])
c, o = quiet(copy.deepcopy(base)); sug = [o['themes'][i]['suggest']['channel'] for i in o['deliver']]
expect('every delivered theme carries a suggested channel and at least one is Colden\'s own', len(sug) == 5 and 'cwc' in sug)
txt = T.Work(W).assemble(base[0])
expect('only the GUEST gets a name card in the assembled clip (hosts never)', txt.count('[NAME CARD: Nick Williams, @WillCoMedia]') == 1 and 'NAME CARD: Colden' not in txt and 'NAME CARD: Jake' not in txt)
C.save(f'{W}/review/state.json', {'themes': {'t01': {'status': 'killed'}, 't02': {'status': 'sent'}, 't03': {'status': 'sent'}, 't04': {'status': 'sent'}, 't05': {'status': 'sent'}}})
c, o = quiet(copy.deepcopy(base)); expect('Colden kills t01 -> the runner-up t06 is promoted, t01 never returns', 't06' in o['deliver'] and 't01' not in o['deliver'] and len(o['deliver']) == 5)
os.remove(f'{W}/review/state.json'); os.remove(f'{W}/waivers.json'); c, o = quiet(copy.deepcopy(base))
expect('stale Monday scrape without a waiver -> exit 2 (ask), blocked', c == 2 and 'scrape_stale' in o['blocks']) if o['scrape_stale'] else print('SKIP  scrape is fresh today - the stale-scrape gate was not exercised')
C.save(f'{tmp}/data/channels/cwc/videos.json', {'pulled_at': '2026-01-01T00:00:00+00:00', 'videos': [{'id': 'OWNVIDEO001'}]})
expect('channel data older than 36 h -> exit 1', quiet(copy.deepcopy(base))[0] == 1)
shutil.rmtree(tmp); print('\nSELFTEST ' + ('OK' if ok else 'FAILED')); sys.exit(0 if ok else 1)
