"""Where the cut starts and ends (Colden 2026-10-01: "Cut from live greeting to live sign off. Cut out intro graphic and
ending graphic").    usage: points.py <CACHE>   (after layout.py + words.py)   -> <CACHE>/points.json    exit 2 = ASK
  start = 0.3 s before the first word spoken once the talk layout is on the program (the intro graphic / teaser before
          it is cut; banter recorded on the ISOs while the intro plays is head, not show)
  end   = 10 frames after the voice stops on the last word spoken before the outro graphic takes the program (the
          10-frame tail is what the assembly skill dissolves on), never past the graphic
The layout switch is found to the frame with ffmpeg's scene detector within 0.6 s of layout.py's half-second estimate
(a dissolve has no cut: the estimate stands, `on_air_exact` false, and plan.py keeps the program picture out of the
first and last half second of the cut).
Confidence: the greeting and the sign-off are looked for in the transcript (show file `greeting` / `signoff`); when
one is missing the run goes on and SAYS so; it stops only when the live window itself is implausible (starts after
10 min, ends more than 10 min before the file does, or covers under half of the program)."""
import os, re, sys, json, subprocess
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

cache = sys.argv[1]; m = C.manifest(cache); sh = C.show(m['show']); FPS = m['fps']
lay = json.load(open(f'{cache}/layout.json')); W = json.load(open(f'{cache}/words.json')); live0, live1 = lay['live']
prog = m['cameras'][0]['path']
def scene_cuts(a, b):
    r = subprocess.run(['ffmpeg', '-v', 'info', '-ss', f'{max(0, a):.3f}', '-t', f'{b - a:.3f}', '-copyts', '-i', prog, '-an', '-vf', "select='gt(scene,0.2)',showinfo", '-f', 'null', '-'], capture_output=True, text=True)
    return [float(x) for x in re.findall(r'pts_time:([\d.]+)', r.stderr)]
# layout.py samples twice a second, so live0 / live1 are right to +-0.5 s. A hard cut within 0.6 s of them is the exact
# frame; anything farther is a cut INSIDE the intro teaser (Ep 24: one 1.9 s early), and a dissolve has no cut at all -
# then the half-second estimate stands and the guard below keeps the program picture out of the first / last half second.
c0 = [t for t in scene_cuts(live0 - 1.0, live0 + 1.0) if abs(t - live0) <= 0.6]; c1 = [t for t in scene_cuts(live1 - 1.0, live1 + 1.0) if abs(t - live1) <= 0.6]
on_air = min(c0, key=lambda t: abs(t - live0)) if c0 else live0          # the talk layout is on the program from here
off_air = min(c1, key=lambda t: abs(t - live1)) if c1 else live1 - 0.5   # the outro graphic takes the program here (no cut found: half a second early, to be safe)
names = {c['id']: c['name'] for c in C.speakers(m)}
FILL = {'um', 'uh', 'uhm', 'hmm', 'mm', 'mhm', 'ah', 'er'}
allw = sorted(({**w, 'sid': sid} for sid in W for w in W[sid] if C.norm_word(w['text']) and C.norm_word(w['text']) not in FILL), key=lambda w: w['start'])
out = {'confident': True, 'notes': [], 'on_air': round(on_air, 3), 'off_air': round(off_air, 3), 'on_air_exact': bool(c0), 'off_air_exact': bool(c1)}
first = next((w for w in allw if w['start'] >= on_air), None); last = next((w for w in reversed(allw) if w['end'] <= off_air + 0.15), None)
if not first or not last or last['end'] <= first['start']: C.die('no words between the intro and the outro graphic')
out['start'] = round(max(on_air, first['start'] - 0.3), 3)       # never before the talk layout is on the program
def voice_stop(sid, t, cap=0.6):
    """where that speaker's voice actually stops after word end t: the first 0.1 s of their stem under -50 dB"""
    a = max(0, t - 0.05); x = C.pcm(f'{cache}/{sid}.wav', ss=a, t=cap + 0.5); B = 320
    db = [20 * np.log10(np.sqrt((x[i:i + B] ** 2).mean()) + 1e-9) for i in range(0, len(x) - B + 1, B)]
    for k in range(len(db) - 5):
        if all(v < -50 for v in db[k:k + 5]): return min(t + cap, a + k * 0.02)
    return t + cap
stop = voice_stop(last['sid'], last['end']); out['voice_stop'] = round(stop, 3)
out['end'] = round(min(stop + 10 / FPS, off_air - 1 / FPS), 3)
if out['end'] < stop: out['notes'].append(f"the outro graphic lands {stop - out['end']:.2f}s before the last voice stops - the last word is clipped by the stream itself")
def said(a, b): return ' '.join(w['text'].strip() for w in allw if a <= w['start'] < b)
out['opener_line'] = said(first['start'], first['start'] + 8)[:160]; out['opener_by'] = names[first['sid']]
out['last_line'] = said(last['end'] - 8, last['end'] + 0.01)[-160:]; out['last_by'] = names[last['sid']]
hosts = {c['id'] for c in C.speakers(m) if c.get('host')}
open_txt = ' '.join(C.norm_word(w['text']) for w in allw if out['start'] <= w['start'] < out['start'] + 25)
close_txt = ' '.join(C.norm_word(w['text']) for w in allw if out['end'] - 75 <= w['start'] < out['end'] and w['sid'] in hosts)
out['greeting_found'] = bool(re.search(sh['greeting'], open_txt)); out['signoff_found'] = bool(re.search(sh['signoff'], close_txt))
if not out['greeting_found']: out['notes'].append(f'no greeting phrase in the first 25 s ("{out["opener_line"][:80]}") - start set on the layout switch; check it')
if not out['signoff_found']: out['notes'].append(f'no sign-off phrase in the last 75 s ("{out["last_line"][-80:]}") - end set on the outro graphic; check it')
D = m['duration']
if out['start'] > 600 or D - out['end'] > 600 or out['end'] - out['start'] < 0.5 * D:
    out['confident'] = False; out['notes'].append(f"live window {C.hms(out['start'])} - {C.hms(out['end'])} of a {C.hms(D)} program is implausible")
C.save(f'{cache}/points.json', out)
print(f"start {C.hms(out['start'])}  ({out['opener_by']}: \"{out['opener_line'][:70]}\")\nend   {C.hms(out['end'])}  ({out['last_by']}: \"...{out['last_line'][-70:]}\")")
for n in out['notes']: print('  note:', n)
sys.exit(0 if out['confident'] else 2)
