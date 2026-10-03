"""Face track of every camera AND of the program, 2 samples per second on the BASE clock.
Two readers per speaker frame: YuNet (assets/yunet.onnx: box, 5 landmarks, crop) and Apple Vision + CoreImage through
tools/expr (lip / eye landmarks and the smile classifier - YuNet's mouth-corner ratio alone could not tell a laugh from a
sip of water: Ep 23 5:59, 2026-10-01).
usage: faces.py <CACHE> [--one <camera id>]    -> <CACHE>/faces_<id>.npz   (one process per camera)
Speakers (one face per sample - the best one):
  t        base seconds            score   detector confidence (nan = no face)
  x y w h  face box / frame size   mouth   mouth-corner distance / eye distance (smile width)
  openv    (mouth y - eye y) / face width (drops when the head tilts down)
  eyerel   (eye y - box top) / box height (rises when looking down)        thumb  16x16 grey face crop (identity match)
  smile    1 / 0 Apple's smile classifier (-1 = it found no face)        mw  mouth width / face width
  mo       inner-lip opening / mouth width (teeth = a laugh)   eyeo  eye opening / eye width   blink, q (capture quality)
  vx vy vw vh  Vision's face box / frame size
Program ('wide'): up to 8 faces per sample: boxes (n, 8, 4), scores (n, 8), thumbs (n, 8, 256).
What reads it: layout.py (which participant is on the program, at what size = which StreamYard layout), reactions.py
(smiles / laughs / nods of a listener; in frame, facing the camera) and the planner's "presentable" mask."""
import os, sys, json, time, subprocess
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

W, H, FPS, MAXF = 640, 360, 2.0, 8
XW, XH = 960, 540          # frame size fed to tools/expr (the smile classifier wants a face of ~130 px)
EXPR = f'{C.SK}/tools/expr'
VK = ('smile', 'mw', 'mo', 'lift', 'eye', 'blink', 'q', 'x', 'y', 'w', 'h')
cache = sys.argv[1]; m = C.manifest(cache)

def run(cam):
    import cv2
    det = cv2.FaceDetectorYN.create(f'{C.SK}/assets/yunet.onnx', '', (W, H), 0.6, 0.3, 5000)
    t0 = np.ceil(max(0.0, cam.get('off', 0.0)) * FPS) / FPS                    # first base sample this camera covers, on the 0.5 s grid
    s0 = C.src_time(cam, t0); n_max = int((m['duration'] - t0) * FPS)
    # Decode: software, multi-threaded (a 1080p StreamYard file runs ~50x real time; videotoolbox was 5x slower here and
    # contends across cameras). A camera file over 1080p (Colden's 4K, 150 Mbit/s) is read on its KEYFRAMES only when it
    # has one every <= 0.6 s (his has one every 0.5 s) - the fps filter then takes the keyframe nearest each sample.
    pre = ['-threads', '6']
    if cam.get('height', 0) > 1080:
        kf = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-skip_frame', 'nokey', '-show_entries', 'frame=pts_time', '-read_intervals', f"{cam['duration'] / 2:.0f}%+8",
                             '-of', 'csv=p=0', cam['path']], capture_output=True, text=True).stdout.replace(',', ' ').split()
        kf = [float(x) for x in kf]; gap = max([b - a for a, b in zip(kf, kf[1:])] or [9.0])
        if gap <= 0.6: pre = ['-skip_frame', 'nokey']
    wide = cam['role'] == 'wide'; DW, DH = (W, H) if wide else (XW, XH)
    cmd = ['ffmpeg', '-v', 'error'] + pre + ['-ss', f'{s0:.4f}', '-i', cam['path'], '-an',
           '-vf', f"fps={FPS * cam.get('rate', 1.0):.7f},scale={DW}:{DH}", '-frames:v', str(n_max), '-f', 'rawvideo', '-pix_fmt', 'bgr24' if wide else 'bgra', '-']
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE); rows = []; i = 0; started = time.time(); vis = []
    if not wide:
        import threading
        assert os.path.exists(EXPR), f'{EXPR} missing - run `make` in {C.SK}/tools'
        tool = subprocess.Popen([EXPR, str(XW), str(XH)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=False)
        rd = threading.Thread(target=lambda: vis.extend(json.loads(l) for l in tool.stdout), daemon=True); rd.start()
    bpp = 3 if wide else 4
    while True:
        b = proc.stdout.read(DW * DH * bpp)
        if len(b) < DW * DH * bpp: break
        if wide: img = np.frombuffer(b, np.uint8).reshape(H, W, 3)
        else:
            tool.stdin.write(b)
            img = cv2.resize(np.frombuffer(b, np.uint8).reshape(DH, DW, 4)[:, :, :3], (W, H), interpolation=cv2.INTER_AREA)
        _, f = det.detect(img); t = t0 + i / FPS; i += 1
        grey = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        def thumb(r):
            x, y, w, h = [int(round(v)) for v in r[:4]]; x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + w), min(H, y + h)
            if x1 - x0 < 6 or y1 - y0 < 6: return np.zeros(256, np.float32)
            return cv2.resize(grey[y0:y1, x0:x1], (16, 16), interpolation=cv2.INTER_AREA).astype(np.float32).ravel()
        faces = sorted(f, key=lambda r: -r[14])[:MAXF] if f is not None and len(f) else []
        if wide:
            bx = np.full((MAXF, 4), np.nan, np.float32); sc = np.full(MAXF, np.nan, np.float32); th = np.zeros((MAXF, 256), np.float32)
            for k, r in enumerate(faces): bx[k] = (r[0] / W, r[1] / H, r[2] / W, r[3] / H); sc[k] = r[14]; th[k] = thumb(r)
            rows.append((t, bx, sc, th)); continue
        if not faces: rows.append((t,) + (np.nan,) * 8 + (np.zeros(256, np.float32),)); continue
        r = max(faces, key=lambda r: r[2] * r[3] * r[14])                       # the person, not a face on a poster behind them
        x, y, w, h = r[:4]; re_, le, nose, rm, lm = r[4:14].reshape(5, 2); eye = float(np.linalg.norm(le - re_)) or 1.0
        eye_y = (le[1] + re_[1]) / 2; mouth_y = (lm[1] + rm[1]) / 2
        rows.append((t, float(r[14]), x / W, y / H, w / W, h / H, float(np.linalg.norm(lm - rm) / eye), float((mouth_y - eye_y) / (w or 1)), float((eye_y - y) / (h or 1)), thumb(r)))
    if not wide:
        tool.stdin.close(); tool.wait(); rd.join(timeout=60)
        assert len(vis) == len(rows), f"{cam['name']}: tools/expr answered {len(vis)} of {len(rows)} frames"
    proc.wait()
    assert rows, f"{cam['name']}: no frames decoded from {cam['path']}"
    if wide:
        np.savez_compressed(f"{cache}/faces_{cam['id']}.npz", t=np.array([r[0] for r in rows]), boxes=np.stack([r[1] for r in rows]), scores=np.stack([r[2] for r in rows]), thumbs=np.stack([r[3] for r in rows]).astype(np.uint8))
        print(f"{cam['name']}: {len(rows)} samples, {np.isfinite(np.stack([r[2] for r in rows])).sum(1).mean():.1f} faces per sample, {time.time() - started:.0f}s")
    else:
        a = np.array([r[:9] for r in rows], np.float64); keys = ('t', 'score', 'x', 'y', 'w', 'h', 'mouth', 'openv', 'eyerel')
        vz = {('v' + k if k in 'xywh' else ('eyeo' if k == 'eye' else k)): np.array([(v.get(k) if v.get('face') and v.get(k) is not None else np.nan) for v in vis], np.float64) for k in VK}
        np.savez_compressed(f"{cache}/faces_{cam['id']}.npz", thumb=np.stack([r[9] for r in rows]).astype(np.uint8), **{k: a[:, j] for j, k in enumerate(keys)}, **vz)
        print(f"{cam['name']}: {len(rows)} samples from {C.hms(t0)}, a face on {np.isfinite(a[:, 1]).mean() * 100:.0f} %, smiling on {(vz['smile'] == 1).mean() * 100:.0f} %, {time.time() - started:.0f}s")

if '--one' in sys.argv:
    run(next(c for c in m['cameras'] if c['id'] == sys.argv[sys.argv.index('--one') + 1])); sys.exit(0)
todo = [c for c in m['cameras'] if not os.path.exists(f"{cache}/faces_{c['id']}.npz")]
procs = [subprocess.Popen([sys.executable, os.path.abspath(__file__), cache, '--one', c['id']], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for c in todo]
bad = []
for c, p in zip(todo, procs):
    out, err = p.communicate(); print(out.strip())
    if p.returncode != 0: bad.append(f"{c['name']}: {err.strip()[-300:]}")
for c in m['cameras']:
    f = f"{cache}/faces_{c['id']}.npz"
    if not os.path.exists(f): continue
    d = np.load(f); n = len(d['t']); want = (m['duration'] - d['t'][0]) * FPS
    if n < 0.97 * want - 4:
        bad.append(f"{c['name']}: {n} samples, expected ~{want:.0f} - the decode stopped early"); os.replace(f, f + '.rejected')      # not left for the next step to use
    elif c['role'] == 'speaker' and np.isfinite(d['score']).mean() < 0.5:
        bad.append(f"{c['name']}: a face on only {np.isfinite(d['score']).mean() * 100:.0f} % of samples - is this camera pointed at them?")
    elif c['role'] == 'speaker':
        # the two face readers must agree all the way through: Apple Vision (expression) went blind after ~44 min of a
        # long run while YuNet still saw the face, and half the show had no reactions (2026-10-01, a leak in tools/expr)
        yu = np.isfinite(d['score']); vi = np.isfinite(d['vw']); B = int(300 * FPS)
        for i in range(0, n, B):
            if yu[i:i + B].mean() >= 0.5 and vi[i:i + B].mean() < 0.6 * yu[i:i + B].mean():
                bad.append(f"{c['name']}: from {C.hms(float(d['t'][i]))} the expression track sees a face on {vi[i:i + B].mean() * 100:.0f} % of samples, the detector on {yu[i:i + B].mean() * 100:.0f} % - tools/expr failed part-way"); os.replace(f, f + '.rejected'); break
if bad: C.die('; '.join(bad))
