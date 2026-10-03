"""selftest_learn.py - ruling 44 (packaging learns from the weekly data) on synthetic data: no network, no real files.
Exit 0 = OK. Run after any change to pack_learn.py or to the copy gate in package.py."""
import os, sys, json, tempfile
tmp = tempfile.mkdtemp(prefix='podclips_learntest_'); os.environ['CWC_ROOT'] = tmp
import common as C, pack_learn as PL
SCR = f'{tmp}/channel_metrics.json'; C.SCRAPE[:] = [SCR]
ok = True
def expect(name, cond):
    global ok; ok &= bool(cond); print(('PASS  ' if cond else 'FAIL  ') + name)
money = [f'Camera {c} Now Costs ${p} Less' for c, p in zip('ABCDE', (300, 400, 500, 600, 700))]
review = [f'Camera {c} Review Today' for c in 'FGHIJ']
rows = [{'video_id': f'm{i}', 'title': t, 'ctr_pct': 8.0, 'impressions': 5000, 'avg_pct_viewed': 30} for i, t in enumerate(money)] + \
       [{'video_id': f'r{i}', 'title': t, 'ctr_pct': 4.0, 'impressions': 5000, 'avg_pct_viewed': 30} for i, t in enumerate(review)]
tests = [{'video_id': 'ab1', 'status': 'done', 'winner': 'C', 'titles': {'A': 'Sony Made It Cheaper', 'B': 'The Sony Is Cheaper Now', 'C': 'Why Did Sony Cut the Price?'},
          'thumbs': {'A': "face + 'IT IS CHEAPER'", 'B': "face + 'PRICE CUT NOW HERE'", 'C': "face + 'WHY?'"}},
         {'video_id': 'ab2', 'status': 'done', 'winner': 'B', 'titles': {'A': 'Nikon Fixed the ZR', 'B': 'Why Nikon Fixed the ZR?', 'C': 'Nikon ZR Firmware Is Out'}}]
C.save(SCR, {'updated': '2026-10-05', 'per_video': rows, 'ab_tests': tests})
B = PL.build(quiet=True); P = {p['id']: p for p in B['patterns']}
expect('a dollar figure that clicks 2x the median is a WIN, with its n', P['T-money']['status'] == 'WIN' and P['T-money']['n_with'] == 5)
expect('review wording that clicks at half the median is a LOSE', P['T-review-vs']['status'] == 'LOSE')
expect('two A/B wins for a question title make it a WIN even without CTR rows', P['T-question']['status'] == 'WIN' and P['T-question']['ab_score'] == 2)
expect('a "6K" camera resolution is not money', 'T-money' not in PL.feats('Blackmagic PYXIS 6K Review'))
expect('thumbnail text is measured from the A/B lines (one word "WHY?" won)', P['H-one-word']['ab_score'] >= 1)
C.save(SCR, {'updated': '2026-10-12', 'per_video': rows[:2], 'ab_tests': []})              # next week the 90-day window dropped most rows
B2 = PL.build(quiet=True)
expect('the evidence is kept week to week (rows and tests that left the scrape still count)', B2['rows'] == 10 and B2['tests_done'] == 2)
# ---- the gate on a copy file
cp = {'titles': ['Camera X Now Costs $200 Less', 'Why Is Camera X So Good?', 'Camera X Is Great'], 'learned': [{'id': 'T-money', 'how': 'title 1 leads with the price cut'}, {'id': 'AB-ab1', 'how': 'title 2 copies the Why ... ? winner'}]}
expect('copy without the brief id is refused (the brief must be read)', any('"brief"' in x for x in PL.problems(cp, False, 'x')))
cp['brief'] = B2['id']; expect('copy with the brief id, 2 learned ids and a WIN title passes', PL.problems(cp, False, 'x') == [])
bad = dict(cp, learned=[{'id': 'T-made-up', 'how': 'invented pattern here'}])
expect('learned ids that are not in the brief are refused', any('learned' in x for x in PL.problems(bad, False, 'x')))
nowin = dict(cp, titles=['Camera X Is Great', 'Camera X Is Good', 'Camera X Is Fine'])
expect('three options without a WIN pattern are refused', any('WIN pattern' in x for x in PL.problems(nowin, False, 'x')))
rev = dict(cp, titles=['Camera X Review Today', 'Why Is Camera X So Good?', 'Camera X Now Costs $200 Less'])
expect('a LOSE pattern needs a declared test', any('LOSE' in x for x in PL.problems(rev, False, 'x')) and not PL.problems(dict(rev, explore={'1': 'testing review wording on a new format'}), False, 'x'))
fin = dict(cp, A='Camera X Now Costs $200 Less', B='Camera Y Now Costs $300 Less', C='Why Is Camera X So Good?')
expect('final set without a hypothesis per test title is refused', any('ab_tests_plan' in x for x in PL.problems(fin, True, 'x')))
fin['ab_tests_plan'] = {'B': 'same shape as A: no change, a bad test', 'C': 'question + Why against the price statement'}
expect('a test title with the same measured features as A is refused (the test could not teach anything)', any('title B has the same measured features' in x for x in PL.problems(fin, True, 'x')))
fin['B'] = 'I Bought Camera X After the $200 Cut'; fin['ab_tests_plan']['B'] = 'first person + price against the plain price statement'
expect('a final set where B and C each change something, with hypotheses, passes', PL.problems(fin, True, 'x') == [])
# ---- the loop closes: a delivered upload goes live, is linked by its title, and its A/B result is read against our hypothesis
W = f'{C.CLIPS}/creative-lens/Ep99'; os.makedirs(W)
C.save(f'{W}/delivery.json', {'show': 'creative-lens', 'episode': 'Ep99', 'delivered_at': '2026-10-06T10:00:00-04:00', 'clips': [{'theme': 't01', 'channel': 'cwc', 'titles': {'A': fin['A'], 'B': fin['B'], 'C': fin['C']},
        'ab_tests_plan': fin['ab_tests_plan'], 'learned': fin['learned'], 'brief': fin['brief']}]})
C.save(f'{C.DATA}/channels/cwc/videos.json', {'videos': [{'id': 'NEW1', 'title': fin['B'], 'published': '2026-10-08T14:00:00Z'}, {'id': 'OLD1', 'title': fin['A'], 'published': '2026-01-01T00:00:00Z'}]})
C.save(SCR, {'updated': '2026-10-19', 'per_video': [{'video_id': 'NEW1', 'title': fin['B'], 'ctr_pct': 9.0, 'impressions': 4000}], 'ab_tests': [{'video_id': 'NEW1', 'status': 'done', 'winner': 'B', 'titles': {'A': fin['A'], 'B': fin['B'], 'C': fin['C']}}]})
B3 = PL.build(quiet=True); pub = [json.loads(l) for l in open(f'{C.DATA}/published.jsonl')]
expect('the live upload is linked by its title (the A/B winner may be what YouTube shows), not an older same-title video', len(pub) == 1 and pub[0]['video_id'] == 'NEW1' and pub[0]['package']['ab_tests_plan'])
o = B3['our_uploads'][0] if B3['our_uploads'] else {}
expect('its own A/B result is read against the hypothesis we wrote', o.get('verdict', '').startswith('B won: first person + price'))
expect('a second build does not link it twice', PL.build(quiet=True) and sum(1 for _ in open(f'{C.DATA}/published.jsonl')) == 1)
print('SELFTEST LEARN OK' if ok else 'SELFTEST LEARN FAILED'); sys.exit(0 if ok else 1)
