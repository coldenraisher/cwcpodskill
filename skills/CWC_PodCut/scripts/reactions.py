"""Reactions - automatic, expression-scored (Colden 2026-10-01: "automatic processing of reactions. this is a more
expressive show so you will see more laughing, smiling etc... avoid walking away from the camera, coughing, sneezing,
going out of frame"). Audio alone never earns a cutaway (AMIRA: the cut to a blank face "was a bad call").
usage: reactions.py <CACHE> [--sheet out.jpg]   (after faces.py, words.py)
  -> <CACHE>/reactions.json  {'picked': [{camera, name, start, end, score, why}], 'rejected': {reason: n}, ...}
  -> <CACHE>/present.npz     per speaker, twice a second: is this person PRESENTABLE (in frame, at their usual size
                             and place) - the planner will not put a close-up on anyone who is not
A candidate = a LISTENER (no real words of their own) while someone else has the floor, whom Apple's smile classifier
(tools/expr) sees smiling for >= 1 s. It is then re-read at 10 fps and kept only when, for the whole 2-4 s window:
  smiling       the classifier says so on >= 60 % of the frames (a sip of water, a hand at the mouth, a yawn do not)
  in frame      a face on >= 90 % of frames, box centre within 0.10 (across) / 0.12 (up-down) of their usual spot,
                size 0.75-1.35 x usual
  eyes up       eye opening not under ~half their usual on more than 30 % of frames (a bowed head / a phone / notes
                read as closed eyes)
  no jolt       the face does not jump (a sneeze / cough / reach = the box travelling fast) and does not wander
  uncovered     Apple's face-capture quality is under 75 % of their usual on at most 12 % of the frames (a hand at the
                nose, a glass, a blur stay low; a laugh dips for a frame or two), and the window never opens on such frames
Kept ones are scored (how much of the window smiles, how wide the mouth is against their own median, a laugh on their
mic) and dropped under --min-score. ALL of them go to the planner ('picked' + 'others'), which does the spacing itself
(cadence `reaction_spacing`); 'picked' (thinned to one per --spacing s) is what the review sheet shows."""
import os, sys, json, argparse, subprocess, io
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

ap = argparse.ArgumentParser(); ap.add_argument('cache'); ap.add_argument('--sheet', default=None)
ap.add_argument('--min-score', type=float, default=0.40); ap.add_argument('--spacing', type=float, default=20.0)
ap.add_argument('--min', type=float, default=2.0); ap.add_argument('--max', type=float, default=4.0); A = ap.parse_args()
cache = A.cache; m = C.manifest(cache); W = json.load(open(f'{cache}/words.json')); VAD = json.load(open(f'{cache}/vad.json'))['speakers']
spk = C.speakers(m); DUR = m['duration']; FPS = 2.0
PURE = {'mm', 'hmm', 'mhm', 'mm-hmm', 'uh-huh', 'um', 'uh', 'uhm', 'ah', 'er', 'huh', 'oh', 'wow', 'yeah', 'ha', 'haha'}
def word_iv(sid, real_only=True):
    return [(w['start'], w['end']) for w in W.get(sid, []) if C.norm_word(w['text']) and (not real_only or C.norm_word(w['text']) not in PURE)]
def mask_on(t, iv, pad=0.0):
    x = np.zeros(len(t), bool)
    for a, b in iv: x |= (t >= a - pad) & (t <= b + pad)
    return x
def frac(iv, a, b): return sum(max(0.0, min(b, e) - max(a, s)) for s, e in iv if e > a and s < b) / max(1e-6, b - a)
AR = C.load(f'{cache}/audio_reactions.json', {'speakers': {}}); HZ = AR.get('rate_hz', 10)
def laugh(sid, a, b):
    sc = (AR['speakers'].get(sid) or {}).get('score') or []; x = sc[int(a * HZ):int(b * HZ)]
    return float(max(x)) if x else 0.0
base = {}; present = {}
for c in spk:
    d = dict(np.load(f"{cache}/faces_{c['id']}.npz")); t = d['t']; ok = np.isfinite(d['score']) & (d['score'] >= 0.7)
    assert 'smile' in d, f"{c['name']}: faces file has no expression track - re-run faces.py (tools/expr)"
    talking = mask_on(t, word_iv(c['id']), 0.3); listen = ok & ~talking & np.isfinite(d['vw'])
    assert listen.sum() >= 40, f"{c['name']}: under 20 s of listening face - is this the right camera?"
    cx = d['x'] + d['w'] / 2; cy = d['y'] + d['h'] / 2
    med = {'w': float(np.median(d['w'][listen])), 'cx': float(np.median(cx[listen])), 'cy': float(np.median(cy[listen])),
           'vw': float(np.median(d['vw'][listen])), 'vcx': float(np.median((d['vx'] + d['vw'] / 2)[listen])), 'vcy': float(np.median((d['vy'] + d['vh'] / 2)[listen])),
           'mw': float(np.nanmedian(d['mw'][listen])), 'eyeo': float(np.nanmedian(d['eyeo'][listen])), 'q': float(np.nanmedian(d['q'][listen])), 'smile_rate': float((d['smile'][listen] == 1).mean())}
    pres = ok & (np.abs(cx - med['cx']) <= 0.12) & (np.abs(cy - med['cy']) <= 0.12) & (d['w'] >= 0.7 * med['w']) & (d['w'] <= 1.45 * med['w'])
    k5 = np.convolve(np.pad(pres.astype(int), 2, mode='edge'), np.ones(5), 'valid')
    present[c['id']] = (pres | (k5 >= 4))            # one missed detection in 2.5 s is not "out of frame"
    base[c['id']] = {'d': d, 'med': med, 'ok': ok, 'talking': talking}
    print(f"{c['name']:8s} face on {ok.mean() * 100:.0f} %, presentable {present[c['id']].mean() * 100:.0f} %, smiling on {med['smile_rate'] * 100:.0f} % of listening samples")
t0 = min(base[c['id']]['d']['t'][0] for c in spk); n_all = int(round((DUR - t0) * FPS)) + 1; grid = t0 + np.arange(n_all) / FPS
pz = {'t': grid, 't0': np.array(t0)}
for c in spk:
    d = base[c['id']]['d']; x = np.zeros(n_all, bool); i0 = int(round((d['t'][0] - t0) * FPS)); x[i0:i0 + len(d['t'])] = present[c['id']][:n_all - i0]; pz[c['id']] = x
np.savez_compressed(f'{cache}/present.npz', **pz)
# reactions must be findable across the WHOLE show: an expression track that covers only part of it is a broken track
for c in spk:
    d_ = base[c['id']]['d']; cover = float(np.isfinite(d_['vw']).mean()); seen = float(np.isfinite(d_['score']).mean())
    if cover < 0.8 * seen: C.die(f"{c['name']}: the expression track covers {cover * 100:.0f} % of the show, the face detector {seen * 100:.0f} % - re-run faces.py (tools/expr failed part-way)")
low = [f"{c['name']} {present[c['id']].mean() * 100:.0f} %" for c in spk if present[c['id']].mean() < 0.85]
if low: C.die(f"presentable under 85 % of the show for {low} - 'presentable' = at their USUAL place and size, so a camera that was moved or re-framed mid-show reads as out of place from then on and that person would vanish from the cut. Look at the camera, then tell Colden.")

XW, XH = 960, 540
def dense(cam, a, b, fps=10.0):
    """the window re-read at 10 fps through tools/expr: (times, rows)"""
    p1 = subprocess.Popen(['ffmpeg', '-v', 'error', '-ss', f'{C.src_time(cam, a):.3f}', '-t', f'{b - a:.3f}', '-i', cam['path'], '-an', '-vf', f'fps={fps},scale={XW}:{XH}', '-f', 'rawvideo', '-pix_fmt', 'bgra', '-'], stdout=subprocess.PIPE)
    out = subprocess.run([f'{C.SK}/tools/expr', str(XW), str(XH)], stdin=p1.stdout, capture_output=True, text=True).stdout; p1.wait()
    rows = [json.loads(l) for l in out.splitlines()]
    return a + np.arange(len(rows)) / fps, rows

todo = []; rejected = {}
def reject(why): rejected[why] = rejected.get(why, 0) + 1
for c in spk:
    sid = c['id']; b_ = base[sid]; d = b_['d']; t = d['t']
    others = [(s, e) for o in spk if o['id'] != sid for s, e in word_iv(o['id'])]; own = word_iv(sid)
    hot = b_['ok'] & ~b_['talking'] & present[sid] & (d['smile'] == 1)
    i = 0
    while i < len(hot) - 1:
        if not (hot[i] and hot[i + 1]): i += 1; continue
        j = i
        while j < len(hot) and hot[j]: j += 1
        a0, b0 = t[i] - 0.5, t[j - 1] + 0.5; i = j
        if frac(others, a0, min(b0, a0 + A.max)) < 0.4: reject('nobody else talking (not a listener shot)'); continue
        if frac(own, a0, min(b0, a0 + A.max)) > 0.15: reject('they are talking themselves'); continue
        todo.append((c, a0, b0))
def judge(job):
    c, a0, b0 = job; sid = c['id']; med = base[sid]['med']
    td, rows = dense(c, a0 - 0.5, min(b0, a0 + A.max) + 0.8)
    if len(rows) < 15: return 'could not read the frames'
    sm = np.array([r.get('smile') == 1 and bool(r.get('face')) for r in rows])
    if sm.sum() < 5: return 'the smile does not hold'
    # the window opens where the smile is SUSTAINED (3 frames in a row), not on a lone frame the classifier fires on while a
    # hand is still at the face (Ep 24 cut 1:23:47: one smile frame, then 1.2 s of Jake rubbing his nose, then the laugh)
    run3 = sm[:-2] & sm[1:-1] & sm[2:]
    if not run3.any(): return 'the smile does not hold'
    k0 = int(np.argmax(run3)); k1 = len(sm) - 1 - int(np.argmax(sm[::-1]))
    # ...and it does not reach back over frames where the face is partly covered (capture quality under 75 % of their usual)
    lowq = np.array([not r.get('face') or r.get('q') is None or r['q'] < 0.75 * med['q'] for r in rows]); i0 = max(0, k0 - 3)
    while lowq[i0:k0].any(): i0 += int(np.where(lowq[i0:k0])[0].max()) + 1
    ta = float(td[i0]); tb = float(td[k1]) + 0.2; tb = min(ta + A.max, max(tb, ta + A.min))
    inw = (td >= ta) & (td <= tb); R = [r for r, k in zip(rows, inw) if k]
    if len(R) < 0.8 * (tb - ta) * 10: return 'could not read the frames'       # the window runs past what was read
    face = np.array([bool(r.get('face')) for r in R])
    if face.mean() < 0.9: return 'face leaves the frame / is covered'
    g = lambda k: np.array([r[k] for r in R if r.get('face') and r.get(k) is not None], float)
    cx = g('x') + g('w') / 2; cy = g('y') + g('h') / 2; w_ = g('w')
    if (np.abs(cx - med['vcx']) > 0.10).any() or (np.abs(cy - med['vcy']) > 0.12).any() or (w_ < 0.75 * med['vw']).any() or (w_ > 1.35 * med['vw']).any(): return 'out of their usual place / size (leaning out, walking off)'
    step = np.hypot(np.diff(cx), np.diff(cy) * 9 / 16) / max(1e-6, med['vw'])       # movement per 0.1 s in face widths
    if len(step) and (step.max() > 0.22 or np.hypot(cx.max() - cx.min(), (cy.max() - cy.min()) * 9 / 16) / med['vw'] > 0.6): return 'a jolt (sneeze / cough / reach) or too much movement'
    smf = float(np.mean([r.get('smile') == 1 for r in R]))
    if smf < 0.6: return 'the smile does not hold'
    if lowq[inw].mean() > 0.12: return 'face partly covered or blurred (a hand, a glass, a fast move)'      # a frame or two dips on any laugh; a covered face stays low
    eye = g('eye')
    if len(eye) and (np.median(eye) < 0.5 * med['eyeo'] or (eye < 0.55 * med['eyeo']).mean() > 0.3): return 'eyes down / closed'
    if frac([(s, e) for o in spk if o['id'] != sid for s, e in word_iv(o['id'])], ta, tb) < 0.3: return 'nobody else talking (not a listener shot)'
    if frac(word_iv(sid), ta, tb) > 0.2: return 'they are talking themselves'
    mw = g('mw'); wide_ = float(np.percentile(mw, 80) / med['mw']) if len(mw) else 1.0; lg = laugh(sid, ta, tb); mo = g('mo')
    # the classifier's word counts for less on someone it calls smiling half the time anyway (Ep 23: Erik, 49 % of his
    # listening samples); a mouth wider than their own median and a laugh on their mic are the evidence that carries
    score = 0.35 * smf * (1.0 - 0.6 * min(1.0, med['smile_rate'])) + 0.4 * min(1.0, max(0.0, (wide_ - 1.0) / 0.25)) + 0.25 * min(1.0, lg)
    return {'camera': sid, 'name': c['name'], 'start': round(ta, 2), 'end': round(tb, 2), 'score': round(float(score), 3), 'smile_frac': round(smf, 2), 'mouth_x': round(wide_, 2), 'laugh': round(lg, 2),
            'why': f"smiling {smf * 100:.0f} % of {tb - ta:.1f}s, mouth {wide_:.2f}x" + (', laughing' if lg > 0.6 else '')}
from concurrent.futures import ThreadPoolExecutor
with ThreadPoolExecutor(8) as ex: res = list(ex.map(judge, todo))
cands = []
for r in res:
    if isinstance(r, str): reject(r)
    elif r['score'] < A.min_score: reject(f'weak (score under {A.min_score})')
    else: cands.append(r)
cands.sort(key=lambda r: -r['score']); picked = []
for r in cands:
    if all(r['start'] >= p['end'] + A.spacing or r['end'] <= p['start'] - A.spacing for p in picked): picked.append(r)
picked.sort(key=lambda r: r['start'])
C.save(f'{cache}/reactions.json', {'picked': picked, 'others': [r for r in cands if r not in picked], 'passed': len(cands), 'rejected': rejected, 'spacing': A.spacing,
                                   'baseline': {c['name']: {k: round(v, 4) for k, v in base[c['id']]['med'].items()} for c in spk}, 'min_score': A.min_score})
print(f"{len(cands)} reactions passed the gate, {len(picked)} kept at >= {A.spacing:.0f} s apart ({len(picked) / (DUR / 60):.1f} per min); rejected: {rejected}")
by = {}
for r in picked: by[r['name']] = by.get(r['name'], 0) + 1
print('  per person:', by)
if A.sheet and picked:      # LOOK at this when tuning: 3 frames per reaction (start / middle / end)
    from PIL import Image, ImageDraw, ImageFont
    show = picked if len(picked) <= 40 else [picked[int(i)] for i in np.linspace(0, len(picked) - 1, 40)]
    w, h, th = 240, 135, 20; sh = Image.new('RGB', (2 * (3 * w + 6), ((len(show) + 1) // 2) * (h + th)), (18, 18, 18)); f = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 13); dr = ImageDraw.Draw(sh)
    cam = {c['id']: c for c in spk}
    for i, r in enumerate(show):
        x0 = (i % 2) * (3 * w + 6); y0 = (i // 2) * (h + th)
        for k, fr_ in enumerate((0.15, 0.5, 0.85)):
            t = r['start'] + (r['end'] - r['start']) * fr_
            b = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f"{C.src_time(cam[r['camera']], t):.3f}", '-i', cam[r['camera']]['path'], '-frames:v', '1', '-vf', f'scale={w}:{h}', '-f', 'image2pipe', '-vcodec', 'mjpeg', '-'], capture_output=True).stdout
            if b: sh.paste(Image.open(io.BytesIO(b)).convert('RGB'), (x0 + k * w, y0 + th))
        dr.text((x0 + 4, y0 + 3), f"{C.hms(r['start'])} {r['end'] - r['start']:.1f}s {r['name']} score {r['score']:.2f}  {r['why']}", fill=(255, 255, 255), font=f)
    sh.save(A.sheet, quality=82); print('sheet ->', A.sheet)
