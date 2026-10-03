"""selftest_cut.py - the edit planner's rules on a synthetic episode (no Resolve, no NAS, no network). Exit 0 = OK.
Run after any change to cut.py or references/edit.json."""
import os, sys, json, copy, shutil, tempfile, io, contextlib
tmp = tempfile.mkdtemp(prefix='podclips_cuttest_'); os.environ['CWC_ROOT'] = tmp
import common as C, themes as T, cut as K
W = f'{tmp}/clips/creative-lens/EpTEST'; snap = f'{tmp}/snap'; os.makedirs(W); os.makedirs(snap); FPS = 30
# 10 minutes: blocks of 12 s per speaker (Colden host, Nick guest, Jake host), each block = one close-up, 3 sentences of
# 8 words; a 2.0 s silence before the 2nd sentence of block 3; the word "bullshit" in block 5, "fuckin" in block 6; a 40 s close-up in block 7
ph = []; segs = []; t = 0.0; who = ['Colden', 'Nick', 'Jake']; n = 0; LONG = 7
def sentence(speaker, t0, words):
    global n; n += 1; w = []; x = t0
    for k in words: w.append([k, round(x, 3), round(x + 0.40, 3)]); x += 0.45
    w[-1][0] += '.'; ph.append({'id': f'P{n:04d}', 'who': speaker, 'start': t0, 'end': w[-1][2], 'b0': t0, 'b1': w[-1][2], 'text': ' '.join(k[0] for k in w), 'n': len(w), 'p_min': 0.9, 'w': w}); return x
for blk in range(50):
    sp = who[blk % 3]; b0 = t
    for sidx in range(3):
        words = ['word'] * 8
        if blk == 5 and sidx == 1: words[3] = 'bullshit'
        if blk == 6 and sidx == 1: words[3] = 'fuckin'
        if blk == 3 and sidx == 1: t += 2.0
        t = sentence(sp, t, words) + 0.3
    if blk == 7:
        for _ in range(LONG): t = sentence(sp, t, ['long'] * 8) + 0.3
    segs.append({'srcFrames': [0, 0], 'srcStart': b0, 'srcEnd': t, 'camera': sp, 'name': sp, 'reason': 'speaker', 'outFrame': int(round(b0 * FPS)), 'frames': int(round(t * FPS)) - int(round(b0 * FPS)), 'outStart': b0, 'outEnd': t, 'zoom': False})
C.save(f'{snap}/plan.json', {'fps': FPS, 'segments': segs}); C.save(f'{W}/phrases.json', ph)
C.save(f'{W}/episode.json', {'show': 'creative-lens', 'show_name': 'The Creative Lens', 'ep_key': 'EpTEST', 'ep_no': 'TEST', 'cut': 'TEST (L)', 'project': 'x', 'plan_sha': 'x', 'podcut_cache': tmp, 'snapshot': snap, 'trial': 'selftest', 'rules': C.RULES, 'specials': [],
                             'people': [{'name': 'Colden', 'host': True}, {'name': 'Jake', 'host': True}, {'name': 'Nick', 'host': False, 'full_name': 'Nick Williams', 'handle': '@WillCoMedia'}], 'duration': t})
def P(blk, s): return f'P{blk * 3 + s + 1 + (LONG if blk > 7 else 0):04d}'
def theme(body, hook=(0, 0), **kw):
    th = {'id': 't01', 'slug': 'x', 'title': 'T', 'hook': {'from': P(*hook), 'to': P(*hook), 'quote': 'x'}, 'body': [{'from': P(*a), 'to': P(*b)} for a, b in body], 'payoff': {}}; th.update(kw)
    C.save(f'{W}/themes.json', {'themes': [th]}); return th
def run(**kw):
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()): return K.build(W, 't01', 'cwc', audio=False, write=False)
ok = True
def expect(name, cond):
    global ok; ok &= bool(cond); print(('PASS  ' if cond else 'FAIL  ') + name)
E = K.cfg()
theme([((0, 0), (9, 2))]); o = run()
expect('one continuous range: no problems, every shot >= 2 s (1 s at the edges)', not o['problems'] and all(s['b'] - s['a'] >= 30 for s in o['shots']))
tr = [t for t in o['trims'] if t['kind'] == 'pause']
expect('the 2.35 s silence is trimmed to 0.5 s and its splice is hidden - never a jump cut', len(tr) == 1 and tr[0]['kept'] and abs(tr[0]['seconds'] - (2.35 - 0.5)) < 0.1 and o['splices'] and all(sp.get('hide') and sp['hide'] != 'UNHIDDEN' for sp in o['splices']))
def cams_differ(o):
    sh = o['shots']; return all(sh[i - 1]['cam'] != s['cam'] or sh[i - 1]['punch'] != s['punch'] for i, s in enumerate(sh) if s.get('splice'))
expect('on both sides of every splice the camera or the punch state differs', cams_differ(o))
expect('a punch-in is only ever on a close-up and the size is 1.25', E['punch'] == 1.25 and all(s['cam'] != 'WIDE' for s in o['shots'] if s['punch']))
expect('the 40 s close-up is split at word boundaries into pieces of 10 s at most, the punch alternating (re-engagement)', o['stats']['reengage_punches'] >= 3 and all(s['b'] - s['a'] <= E['reengage_over'] * FPS for s in o['shots'] if s['kind'] == 'body' and s['cam'] != 'WIDE'))
expect('every swear is kept and gets a censor window, inflected forms too (fuckin)', sorted(c['word'] for c in o['censor']) == ['bullshit', 'fuckin'])
expect('a beep lets 3 frames of the word through at each end (Colden 2026-10-02)', all(12 - 6 - 1 <= c['frames'] <= 12 - 6 + 1 and c['rec'] - c['word_rec'][0] == 3 for c in o['censor']))
expect('name tag: the guest only, once, on his first close-up of the body', [t['who'] for t in o['tags']] == ['Nick'] and o['tags'][0]['handle'] == '@WillCoMedia')
theme([((0, 0), (0, 2)), ((3, 0), (3, 2)), ((6, 0), (9, 2))]); o = run()      # three parts, all starting on a Colden close-up
j = [sp for sp in o['splices'] if sp['type'] == 'join']
expect('joining two parts that sit on the same camera: hidden by a camera change (wide) or a punch, not left as a jump cut', len(j) == 2 and all(sp['hide'] != 'UNHIDDEN' for sp in j) and cams_differ(o) and not o['problems'])
theme([((0, 0), (1, 2)), ((2, 0), (3, 2))]); o = run()
expect('two ranges that touch in the show are one continuous piece (no splice at all between them)', not [sp for sp in o['splices'] if sp['type'] == 'join'])
theme([((4, 0), (6, 2))], trims=[{'phrase': P(5, 1), 'words': [2, 4], 'why': 'test'}])
try:
    run(); died = False
except SystemExit: died = True
expect('a written trim that would remove a swear is refused (beep it, never cut it)', died)
theme([((4, 0), (6, 2))], trims=[{'phrase': P(4, 1), 'words': [0, 2], 'why': 'false start'}]); o = run()
w = [t for t in o['trims'] if t['kind'] == 'written']
expect('a written word-level trim is applied only with a hidden splice, else put back', len(w) == 1 and (w[0]['kept'] and cams_differ(o) or not w[0]['kept']) and not o['problems'])
theme([((0, 0), (9, 2))]); o = run()
expect('no trim leaves a shot under 2 s behind (it is put back instead)', all(s['b'] - s['a'] >= 60 for i, s in enumerate(o['shots'][1:-1])) or bool(o['problems']) is False and all(s['b'] - s['a'] >= 30 for s in o['shots']))
theme([((0, 0), (9, 2))], hook=(2, 1)); o = run()
expect('the hook plays as the cold open AND again in the body (ruling 30); the stinger sits between them', o['anchors']['body_start'] == o['anchors']['hook_end'] + round(E['stinger']['cwc']['anim_end_s'] * FPS) and not o['problems'])
expect('the Colden ending closes every clip: 11.67 s after the last word', o['frames'] - o['anchors']['C'] == round(E['outro']['end_screen_s'] * FPS))
expect('swear list: a stem anywhere in the word is caught (horseshit, clusterfuck, bitchy), look-alikes are not (shiitake), plain words are not', all(K.is_swear(E, w) for w in ('horseshit', 'clusterfuck', 'Bitchy', 'fuckin')) and not any(K.is_swear(E, w) for w in ('shiitake', 'shift', 'assess', 'class')))
theme([((4, 0), (6, 2))], trims=[{'phrase': P(20, 1), 'words': [0, 2], 'why': 'typo: a phrase outside this clip'}]); o = run()
expect('a written trim whose phrase is not in the clip is REPORTED (never silently dropped)', any('nothing was trimmed' in x for x in o['problems']))
keep_dip = K._dip; K._dip = lambda X, f: None                                # the audio has no gap at the cut
theme([((4, 0), (6, 2))], trims=[{'phrase': P(4, 1), 'words': [0, 2], 'why': 'false start'}]); o = run(); K._dip = keep_dip
expect('a written trim the audio refuses is a PROBLEM (never a silent "put back")', any('was NOT made' in x and 'false start' in x for x in o['problems']))
C.save(f'{W}/approved.json', {'approved': [{'id': 't01', 'text_sha': 'not-the-current-text'}]}); ep0 = C.load(f'{W}/episode.json'); C.save(f'{W}/episode.json', dict(ep0, trial=None)); theme([((0, 0), (9, 2))])
try: run(); asked = None
except SystemExit as x: asked = x.code
expect('a theme whose ranges changed after his approval is not edited (exit 2: resend it)', asked == 2)
C.save(f'{W}/approved.json', {'approved': [{'id': 't01'}]}); C.save(f'{W}/episode.json', dict(ep0, trial=None, specials=[{'start': 20.0, 'end': 40.0}]))
try: run(); asked = None
except SystemExit as x: asked = x.code
expect('a screen share / played clip inside the ranges stops the edit (exit 2: ask Colden) until `share_plan` records his answer', asked == 2)
theme([((0, 0), (9, 2))], share_plan='Colden 2026-10-02: test - keep the program feed'); o = run()
expect('... and with share_plan the clip plans', o['frames'] > 0)
C.save(f'{W}/episode.json', ep0); os.remove(f'{W}/approved.json')
# two people swearing at the same moment: one window
ph2 = C.load(f'{W}/phrases.json'); bw = next(w for p in ph2 for w in p['w'] if w[0] == 'bullshit'); src = next(p for p in ph2 if any(w[0] == 'bullshit' for w in p['w']))
ph2.append({'id': 'P9999', 'who': 'Jake' if src['who'] != 'Jake' else 'Nick', 'start': bw[1] + 0.1, 'end': bw[2] + 0.2, 'b0': bw[1] + 0.1, 'b1': bw[2] + 0.2, 'text': 'shit', 'n': 1, 'p_min': 0.9, 'w': [['shit', bw[1] + 0.1, bw[2] + 0.2]]})
C.save(f'{W}/phrases.json', sorted(ph2, key=lambda p: p['start'])); theme([((0, 0), (9, 2))]); o = run(); cz = [c for c in o['censor'] if 'bullshit' in c['word']]
expect('two swears that overlap in time become ONE censor window (one beep, one duck)', len(cz) == 1 and 'shit' in cz[0]['word'].split(' + ')[-1] and not any(a['rec'] < b['rec'] + b['frames'] and b['rec'] < a['rec'] + a['frames'] for i, a in enumerate(o['censor']) for b in o['censor'][i + 1:]))
C.save(f'{W}/phrases.json', [p for p in ph2 if p['id'] != 'P9999'])
# a PodCut camera cut INSIDE the swear (a reaction cut-in mid-word): the word must still be beeped
bw = next(w for p in ph for w in p['w'] if w[0] == 'bullshit'); mid = (bw[1] + bw[2]) / 2
k = next(i for i, g in enumerate(segs) if g['srcStart'] <= mid < g['srcEnd']); g = segs[k]
a = dict(g, srcEnd=mid, outEnd=mid, frames=int(round(mid * FPS)) - g['outFrame']); b = dict(g, srcStart=mid, outStart=mid, outFrame=int(round(mid * FPS)), frames=g['outFrame'] + g['frames'] - int(round(mid * FPS)), camera='Jake', name='Jake', reason='reaction')
C.save(f'{snap}/plan.json', {'fps': FPS, 'segments': segs[:k] + [a, b] + segs[k + 1:]}); theme([((0, 0), (9, 2))]); o = run()
expect('a swear that straddles a camera cut is still beeped, as one window', len([c for c in o['censor'] if c['word'] == 'bullshit']) == 1)
shutil.rmtree(tmp); print('\nSELFTEST CUT ' + ('OK' if ok else 'FAILED')); sys.exit(0 if ok else 1)
