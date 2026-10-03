"""Sync every speaker file to the program feed by audio. Measured, never read from a file name.
usage: sync.py <CACHE>            -> manifest cameras[*].off / .rate / .sync      exit 2 = a camera could not be synced (ASK)
  base seconds t (= program time)  ->  source seconds of the camera = (t - off) * rate
1. COARSE: up to twelve 90 s windows of the camera are searched over the WHOLE program (20 ms envelope, FFT correlation) - a
   camera file recorded on its own (Colden's 4K) starts minutes before the stream, a StreamYard ISO within a second.
2. FINE: up to 28 windows of 60 s across the show, +-2 s around the coarse lag at 16 kHz, speech-gated.
3. DRIFT: a line through the fine lags. StreamYard ISOs come out flat (rate 1). A separate recorder drifts; when the
   drift over the show exceeds one frame the fitted rate is kept and build_base re-anchors the clip in pieces.
Gates: >= 2 coarse windows agree within 0.25 s and no second group of >= 2 agrees on another offset; >= 4 fine windows on one drift line; of the
STRONG windows (correlation >= 0.25: this person clearly talking) >= 70 % within 40 ms of it (a file with a break fails here); residual of those <= 25 ms. A camera that fails is left
with NO offset in the manifest, and `sync_problems` stays there until a clean run - plan.py and build.py refuse on it."""
import os, sys, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

cache = sys.argv[1]; m = C.manifest(cache)
wide = next(c for c in m['cameras'] if c['role'] == 'wide'); DUR = wide['duration']; FPS = m['fps']
ENV_SR = 8000; HOP = 160            # 20 ms envelope
def envelope(x):
    n = len(x) // HOP; e = np.abs(x[:n * HOP]).reshape(n, HOP).mean(1); return e - e.mean()
print('program envelope ...'); P = envelope(C.pcm(wide['path'], sr=ENV_SR))
def speechy(x, hop):
    """the window holds this person's voice: >= 10 % of its 20 ms frames within 16 dB of the loud ones, and not silence"""
    fr = np.sqrt((x[:len(x) // hop * hop].reshape(-1, hop) ** 2).mean(1)); top = np.percentile(fr, 99)
    return top > 2e-3 and (fr > 0.16 * top).mean() >= 0.10
def coarse(cam):
    """[(off, score)] - base time of camera-source second 0, from 90 s windows searched over the whole program"""
    hits = []
    for frac in np.linspace(0.06, 0.94, 12):
        s = cam['duration'] * frac; x = C.pcm(cam['path'], ss=s, t=90, sr=ENV_SR)
        if len(x) < ENV_SR * 30: continue
        if not speechy(x, HOP): continue   # silent, or this person barely talks here
        e = envelope(x); L = len(P) + len(e)
        c = np.fft.irfft(np.fft.rfft(P, L) * np.conj(np.fft.rfft(e, L)), L)       # c[k] = sum P[i + k] e[i]; true lags lie in [-len(e), len(P)]
        k = int(np.argmax(c)); k = k - L if k > len(P) else k
        hits.append((k * HOP / ENV_SR - s, float(c.max() / (np.percentile(c, 99.9) + 1e-9))))    # off = base - src; score = peak over the 99.9th percentile
    return hits
def fine(cam, off0):
    """[(base t, off)] from 60 s windows, +-2 s around off0"""
    out = []; SR = 16000; n = 2 * SR
    for t in np.linspace(90, DUR - 150, 28):
        s = t - off0
        if s < 5 or s + 60 > cam['duration'] - 5: continue
        a = np.abs(C.pcm(wide['path'], ss=t, t=60, sr=SR)); b = C.pcm(cam['path'], ss=s, t=60, sr=SR)
        if len(b) < SR * 50 or len(a) < SR * 50: continue
        if not speechy(b, 320): continue     # speech-gated: this person talks in < 10 % of the window
        b = np.abs(b); a = a - a.mean(); b = b - b.mean(); L = 2 * max(len(a), len(b))
        c = np.fft.irfft(np.fft.rfft(a, L) * np.conj(np.fft.rfft(b, L)), L); c = np.concatenate([c[-n:], c[:n + 1]])
        sc = float(c.max() / (np.sqrt((a ** 2).sum() * (b ** 2).sum()) + 1e-9))
        if sc > 0.15: out.append((float(t), off0 + (int(np.argmax(c)) - n) / SR, sc))
    return out
bad = []
for cam in C.speakers(m):
    for k in ('off', 'rate', 'sync'): cam.pop(k, None)        # a camera that fails below is left UNSYNCED (no stale numbers for a later step to pick up)
    hits = coarse(cam)
    if not hits: bad.append(f"{cam['name']}: no audio to sync on"); continue
    groups = [[g for g in hits if abs(g[0] - h[0]) <= 0.25] for h in hits]; agree = max(groups, key=lambda g: (len(g), sum(x[1] for x in g)))
    # One offset must stand out. Windows where this person is not the one talking land on random lags (a camera's own mic
    # hears the room: Ep 23, 3 of 8 agree, 5 scattered) - those never agree with EACH OTHER. A second cluster of two or
    # more is a different thing: the file has a break and holds two offsets.
    rest = [h for h in hits if h not in agree]; rival = max([len([g for g in rest if abs(g[0] - h[0]) <= 0.25]) for h in rest] + [0])
    if len(agree) < 2 or rival >= 2: bad.append(f"{cam['name']}: coarse windows do not settle on one offset ({len(agree)} agree, a second group of {rival}) {[(round(float(o), 2), round(s, 2)) for o, s in hits]} - a break in the file?"); continue
    off0 = float(np.median([h[0] for h in agree])); f = fine(cam, off0)
    if len(f) < 4: bad.append(f"{cam['name']}: only {len(f)} confident fine windows (does this person talk? is the audio theirs?)"); continue
    t = np.array([x[0] for x in f]); o = np.array([x[1] for x in f]); sc = np.array([x[2] for x in f])
    # Robust fit: a window where this person is not the one talking lands anywhere within +-2 s (Ep 23's camera mic: a
    # window 1.76 s off, score 0.22) and one of those tilts a least-squares line until GOOD windows look wrong. So: first
    # keep what sits within 80 ms of the median offset, fit the drift line on those, then keep what is within 40 ms of it.
    keep = np.abs(o - np.median(o)) <= 0.08
    if keep.sum() < 4: bad.append(f"{cam['name']}: only {int(keep.sum())} of {len(f)} fine windows agree on an offset"); continue
    slope, icpt = np.polyfit(t[keep], o[keep], 1); keep = np.abs(o - (slope * t + icpt)) <= 0.04
    if keep.sum() < 4: bad.append(f"{cam['name']}: only {int(keep.sum())} of {len(f)} fine windows fit one drift line"); continue
    slope, icpt = np.polyfit(t[keep], o[keep], 1); res = (o - (slope * t + icpt))[keep]
    strong = sc >= 0.25                      # windows that clearly carry this person's voice: THESE must agree
    drift = slope * DUR
    if abs(drift) <= 1.0 / FPS:      # flat: one offset for the whole show
        rate = 1.0; off = float(np.median(o[keep])); res = (o - off)[keep]
    else:                            # off(t) = icpt + slope t  ->  src = t - off(t) = (1 - slope) t - icpt  = (t - off) * rate
        rate = 1.0 - slope; off = icpt / rate
    rms = float(np.sqrt((res ** 2).mean()))
    if strong.sum() < 3 or keep[strong].mean() < 0.7: bad.append(f"{cam['name']}: {int((~keep[strong]).sum())} of {int(strong.sum())} strong fine windows sit more than 40 ms off the fit - the offset jumps somewhere in the file; look before building"); continue
    if rms > 0.025: bad.append(f"{cam['name']}: sync residual {rms * 1000:.0f} ms > 25 ms - the offset wanders; look before building"); continue
    cam.update({'off': round(off, 4), 'rate': round(rate, 7)})
    cam.update({'sync': {'windows': len(f), 'used': int(keep.sum()), 'residual_ms': round(rms * 1000, 1), 'drift_ms_over_show': round(drift * 1000, 1), 'coarse': round(off0, 2),
                         'head_s': round(max(0.0, -off), 2), 'covers': [round(max(0.0, off), 2), round(min(DUR, C.base_time(cam, cam['duration'])), 2)]}})
    print(f"{cam['name']:8s} off {off:+9.3f} s  rate {rate:.7f}  ({len(f)} windows, residual {rms * 1000:.0f} ms, drift {drift * 1000:+.0f} ms over the show)")
m['sync_problems'] = bad; C.save(f'{cache}/manifest.json', m)
if bad:
    print('\nSTOP AND ASK:'); [print('  - ' + b) for b in bad]; sys.exit(2)
