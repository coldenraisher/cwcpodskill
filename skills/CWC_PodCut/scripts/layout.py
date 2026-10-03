"""What the PROGRAM is showing, twice a second: the normal talk layout, or something special (intro / outro graphic, a
screen share, a played video, a solo full-screen). No template per show: every speaker's face (from their own camera)
is looked up among the faces on the program at the same instant (16x16 crop correlation) and its size there is compared
with the size it normally has.
usage: layout.py <CACHE> [--sheet out.jpg]   (after faces.py)   -> <CACHE>/layout.json
  live     [a, b]   first and last second of talk layout = the show between the intro graphic and the outro graphic
  special  [[a, b], ...] inside live: the program carries something the cameras do not (share, video, graphic) ->
           the planner holds the program there and trims nothing
  offair   {speaker: [[a, b], ...]} that person is not on the program (not joined yet / left) -> never cut to them
  dense_text [[a, b], ...] parts of the special stretches where the program carries a page of text (tools/textcount)
Rules per sample (then a 2.5 s majority filter; a special stretch is >= 3 s, a talk gap between two of them >= 3 s):
  talk     = the people on the program are a usual cast, each at the size they usually have in that cast (+-22 %),
             and nobody who is talking on the show is missing from the picture
  special  = somebody is off their usual size (a share pushed them into a corner or made them the presenter), nobody
             is on the program at all (graphic / full-screen video), or a talker is not on the picture
Gates: a talk layout must exist (>= 20 % of the show) and special layouts must not exceed 60 % of the live show -
otherwise the detector did not understand this program (or the episode is unusual): ASK.
Known limits: 'usual size' = the most common size per cast, so an episode that spends MORE time in one share layout
than in the talk layout would be read inside out; a share in which StreamYard shows only some of the people is its own
cast and passes as talk unless a missing person is talking. The sheet is there to be LOOKED at."""
import os, sys, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

cache = sys.argv[1]; m = C.manifest(cache); FPS = 2.0
Wd = np.load(f'{cache}/faces_wide.npz'); T = Wd['t']; n = len(T)
pth = Wd['thumbs'].astype(np.float32); pok = np.isfinite(Wd['scores']); pw = Wd['boxes'][:, :, 2]
def unit(a):
    a = a - a.mean(-1, keepdims=True); return a / (np.linalg.norm(a, axis=-1, keepdims=True) + 1e-6)
pth = unit(pth)
spk = C.speakers(m); ids = [c['id'] for c in spk]; S_ = len(spk)
has = np.zeros((S_, n), bool); hit = np.zeros((S_, n), bool); sc = np.full((S_, n), np.nan)
for j, c in enumerate(spk):
    d = np.load(f"{cache}/faces_{c['id']}.npz"); i0 = int(round((d['t'][0] - T[0]) * FPS)); k = min(len(d['t']), n - i0)
    th = unit(d['thumb'][:k].astype(np.float32)); ok = np.isfinite(d['score'][:k]) & (d['score'][:k] >= 0.7)
    cc = np.einsum('ifd,id->if', pth[i0:i0 + k], th); cc[~pok[i0:i0 + k]] = -1          # (samples, program faces)
    best = cc.argmax(1); bc = cc.max(1); rows = np.arange(k); h_ = ok & (bc >= 0.5)
    has[j, i0:i0 + k] = ok; hit[j, i0:i0 + k] = h_
    sc[j, i0:i0 + k] = np.where(h_, pw[i0:i0 + k][rows, best] / np.maximum(d['w'][:k], 1e-6), np.nan)
# A CAST = who is on the program at one instant. Per cast that holds >= 2 % of the samples, each person's usual size
# while that cast is on = the talk layout for that cast (2-up before a guest joins, 3-up after). A share moves at least
# one person off that size - smaller in a corner, or BIGGER as the presenter (Ep 23: Jake 0.65 presenting vs 0.52).
key = (hit * (1 << np.arange(S_))[:, None]).sum(0); ref = {}; edges = np.linspace(np.log(0.08), np.log(2.5), 60)
for cast in np.unique(key):
    sel = key == cast
    if cast == 0 or sel.mean() < 0.02: continue
    r = {}
    for j in range(S_):
        if not (cast >> j) & 1: continue
        h, _ = np.histogram(np.log(sc[j, sel]), bins=edges); h2 = h[:-1] + h[1:]; b_ = int(h2.argmax()); r[j] = float(np.exp(edges[b_ + 1]))
    ref[int(cast)] = r
raw = np.zeros(n, bool)
for cast, r in ref.items():
    sel = key == cast; ok_ = sel.copy()
    for j, v in r.items(): ok_ &= np.abs(np.log(np.where(np.isfinite(sc[j]), sc[j], 1e-9) / v)) <= np.log(1.22)
    raw |= ok_
# someone who is TALKING on the show but is not on the program picture -> the program is showing something else
Wj = json.load(open(f'{cache}/words.json'))       # required: without the words a talker missing from the picture cannot be seen
for j, c in enumerate(spk):
    ws = np.array(sorted(w['start'] for w in Wj.get(c['id'], []) if C.norm_word(w['text'])))
    if not len(ws): continue
    near = (np.searchsorted(ws, T + 30) - np.searchsorted(ws, T - 30)) >= 8          # >= 8 words within +-30 s
    raw &= ~(near & has[j] & ~hit[j])
scale = {ids[j]: {str(cast): round(r[j], 3) for cast, r in ref.items() if j in r} for j in range(S_)}
state = {ids[j]: {'on': hit[j], 'has': has[j]} for j in range(S_)}
def majority(x, k=5):
    p = np.pad(x.astype(int), k // 2, mode='edge'); return np.convolve(p, np.ones(k), 'valid') > k / 2
talk = majority(raw)
def runs(mask):
    out = []; st = None
    for i, v in enumerate(list(mask) + [False]):
        if v and st is None: st = i
        if not v and st is not None: out.append([st, i]); st = None
    return out
def drop_short(mask, val, min_s):
    mask = mask.copy()
    for a, b in runs(mask == val):
        if (b - a) / FPS < min_s and a > 0 and b < len(mask): mask[a:b] = not val
    return mask
talk = drop_short(talk, True, 3.0); talk = drop_short(talk, False, 3.0)
tr = runs(talk)
if not tr or talk.mean() < 0.2: C.die(f'no talk layout found on the program (talk on {talk.mean() * 100:.0f} % of samples) - the layout detector does not understand this program')
tr_long = [r for r in tr if (r[1] - r[0]) / FPS >= 8.0]
live = [float(T[tr_long[0][0]]), float(T[min(n - 1, tr_long[-1][1] - 1)] + 1 / FPS)]
special = [[float(T[a]), float(T[min(n - 1, b - 1)] + 1 / FPS)] for a, b in runs(~talk) if T[a] >= live[0] and T[min(n - 1, b - 1)] < live[1]]
# off air: inside talk layout, a speaker's own camera shows a face but the program does not carry it, for >= 20 s
offair = {}
for c in spk:
    st_ = state[c['id']]; on = st_['on']; win = int(20 * FPS)
    dens = np.convolve(on.astype(float), np.ones(win) / win, 'same'); off = talk & (dens < 0.05)
    off = drop_short(off, True, 20.0); rr = []
    for a, b in runs(off):       # the density window blurs the edges by ~10 s: stretch each range out to the last / first sample the person really IS on the program
        while a > 0 and not on[a - 1]: a -= 1
        while b < n and not on[b]: b += 1
        rr.append([a, b])
    offair[c['id']] = [[float(T[a]), float(T[min(n - 1, b - 1)] + 1 / FPS)] for a, b in rr if T[min(n - 1, b - 1)] > live[0] and T[a] < live[1]]
# ---- how much TEXT is on the program during each special stretch (Colden 2026-10-01: "if high density text is on the
# screen share, do not cut away unless longer time frame +/- 8sec") - Apple Vision reads a frame every 2 s; the talk
# layout's own lettering (handles, logo, ON AIR) is the baseline; a sample with >= 100 characters more is a page of text
import subprocess
from concurrent.futures import ThreadPoolExecutor
TW, TH, STEP = 1280, 720, 2.0; TOOL = f'{C.SK}/tools/textcount'; assert os.path.exists(TOOL), f'{TOOL} missing - run `make -C {C.SK}/tools`'
prog = m['cameras'][0]['path']
def read_text(a, b):
    """[(t, chars)] every STEP s over [a, b)"""
    p1 = subprocess.Popen(['ffmpeg', '-v', 'error', '-ss', f'{a:.2f}', '-t', f'{max(0.1, b - a):.2f}', '-i', prog, '-an', '-vf', f'fps=1/{STEP},scale={TW}:{TH}', '-f', 'rawvideo', '-pix_fmt', 'bgra', '-'], stdout=subprocess.PIPE)
    o = subprocess.run([TOOL, str(TW), str(TH)], stdin=p1.stdout, capture_output=True, text=True).stdout; p1.wait()
    return [(a + STEP / 2 + STEP * r['n'], r['chars']) for r in (json.loads(l) for l in o.splitlines())]
talk_t = [float(T[i]) for i in np.where(talk)[0][::max(1, int(talk.sum() // 12))]][:12]
with ThreadPoolExecutor(6) as ex:
    basev = [c for r in ex.map(lambda t: read_text(t, t + STEP), talk_t) for _, c in r]
    samples = [x for r in ex.map(lambda ab: read_text(ab[0], ab[1]), special) for x in r]
baseline = int(np.median(basev)) if basev else 0; thr = baseline + 100
dense = []
for t_, c_ in sorted(samples):
    if c_ < thr: continue
    if dense and t_ - STEP / 2 <= dense[-1][1] + 0.01: dense[-1][1] = t_ + STEP / 2
    else: dense.append([t_ - STEP / 2, t_ + STEP / 2])
if special and not samples: C.die('the text reader returned nothing for the special stretches - tools/textcount or ffmpeg failed')
out = {'live': [round(x, 2) for x in live], 'special': [[round(a, 2), round(b, 2)] for a, b in special], 'offair': offair,
       'dense_text': [[round(a, 2), round(b, 2)] for a, b in dense], 'text': {'baseline_chars': baseline, 'dense_from': thr, 'samples': len(samples)},
       'talk_scale': scale, 'stats': {'talk_pct': round(float(talk.mean() * 100), 1), 'special_s': round(sum(b - a for a, b in special), 1), 'special_runs': len(special)}}
share = out['stats']['special_s'] / max(1.0, live[1] - live[0])
C.save(f'{cache}/layout.json', out)
if share > 0.6: C.die(f'{share * 100:.0f} % of the live show reads as screen share / special layout - either this episode really is, or the talk layout was taken for the share (the "usual size" of each person is the most common one); look at the sheet and tell Colden')
print(f"live {C.hms(live[0])} - {C.hms(live[1])}; {len(special)} special stretches, {out['stats']['special_s'] / 60:.1f} min; talk-layout face size per cast {scale}")
for a, b in special: print(f'  special {C.hms(a)} - {C.hms(b)}  ({b - a:.0f} s)' + (f'   text-heavy for {sum(max(0, min(b, y) - max(a, x)) for x, y in dense):.0f} s' if any(x < b and y > a for x, y in dense) else ''))
for c in spk:
    for a, b in offair[c['id']]: print(f"  {c['name']} off air {C.hms(a)} - {C.hms(b)}")
if '--sheet' in sys.argv:      # one frame from the middle of every special stretch + the first/last live frames: LOOK at it when tuning
    import subprocess, io
    from PIL import Image, ImageDraw, ImageFont
    pts = [(live[0], 'live starts'), (live[0] - 1.0, 'before live')] + [((a + b) / 2, f'special {b - a:.0f}s') for a, b in special] + [(live[1] - 0.5, 'live ends'), (live[1] + 1.0, 'after live')]
    pts = pts[:60]; cols = 6; w, h = 320, 180; sh = Image.new('RGB', (cols * w, ((len(pts) + cols - 1) // cols) * h)); f = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 14); dr = ImageDraw.Draw(sh)
    for i, (t, lab) in enumerate(pts):
        b = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{max(0, t):.2f}', '-i', m['cameras'][0]['path'], '-frames:v', '1', '-vf', f'scale={w}:{h}', '-f', 'image2pipe', '-vcodec', 'mjpeg', '-'], capture_output=True).stdout
        x, y = (i % cols) * w, (i // cols) * h
        if b: sh.paste(Image.open(io.BytesIO(b)).convert('RGB'), (x, y))
        dr.rectangle((x, y, x + 190, y + 18), fill=(0, 0, 0)); dr.text((x + 3, y + 2), f'{C.hms(t)} {lab}', fill=(255, 255, 0), font=f)
    sh.save(sys.argv[sys.argv.index('--sheet') + 1], quality=80)
