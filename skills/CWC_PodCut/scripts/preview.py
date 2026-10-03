"""A watchable preview of the PLAN, made with ffmpeg straight from the camera files - no Resolve. For looking at the
cut before (or without) building it, and for the Telegram sample.
usage: preview.py <CACHE> [--from <cut s>] [--to <cut s>] [--out file.mp4] [--height 360] [--plan plan.json]
Picture = the planned camera of every shot at its synced source time; sound = the program mix (what A1 will play).
Gates: the file's length is within 2 frames per 100 shots of the plan range, and it has one video + one audio stream."""
import os, sys, json, argparse, subprocess, tempfile, shutil
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
ap = argparse.ArgumentParser(); ap.add_argument('cache'); ap.add_argument('--from', dest='a', type=float, default=0.0); ap.add_argument('--to', dest='b', type=float, default=None)
ap.add_argument('--out', default=None); ap.add_argument('--height', type=int, default=360); ap.add_argument('--plan', default=None); A = ap.parse_args()
cache = A.cache; m = C.manifest(cache); P = json.load(open(A.plan or f'{cache}/plan.json')); F = P['fps']
cam = {c['id']: c for c in m['cameras']}; wide = cam['wide']; b = A.b if A.b is not None else P['segments'][-1]['outEnd']
parts = []
for s in P['segments']:
    o0, o1 = max(A.a, s['outStart']), min(b, s['outEnd'])
    if o1 - o0 < 1 / F: continue
    t0 = s['srcStart'] + (o0 - s['outStart']); parts.append((t0, o1 - o0, s['camera']))
tmp = tempfile.mkdtemp(prefix='cwc_prev_'); H = A.height; Wd = H * 16 // 9
def enc(i):
    t0, d, c = parts[i]; f = f'{tmp}/{i:05d}.ts'
    r = subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{C.src_time(cam[c], t0):.4f}', '-t', f'{d + 0.5:.4f}', '-i', cam[c]['path'], '-an',
                        '-vf', f'fps={F},scale={Wd}:{H}', '-frames:v', str(int(round(d * F))), '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '27', '-pix_fmt', 'yuv420p', '-f', 'mpegts', f], capture_output=True, text=True)
    assert r.returncode == 0 and os.path.exists(f), f'shot {i} ({c} at {t0:.2f}): {r.stderr[-200:]}'
    return f
with ThreadPoolExecutor(6) as ex: files = list(ex.map(enc, range(len(parts))))
lst = f'{tmp}/list.txt'; open(lst, 'w').write(''.join(f"file '{f}'\n" for f in files))
# sound: the program mix, cut sample-exactly on the same ranges (encoding the audio per shot padded every piece to a
# whole AAC frame: 27 ms of drift per cut)
import numpy as np, wave
SR = 48000; lo = min(p[0] for p in parts); hi = max(p[0] + p[1] for p in parts); x = C.pcm(wide['path'], ss=lo, t=hi - lo + 1.0, sr=SR)
y = np.concatenate([x[int(round((t0 - lo) * SR)):int(round((t0 - lo) * SR)) + int(round(int(round(d * F)) / F * SR))] for t0, d, c in parts])
wv = wave.open(f'{tmp}/a.wav', 'wb'); wv.setnchannels(1); wv.setsampwidth(2); wv.setframerate(SR); wv.writeframes((np.clip(y, -1, 1) * 32767).astype('<i2').tobytes()); wv.close()
out = A.out or f'{cache}/preview_{int(A.a)}_{int(b)}.mp4'
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst, '-i', f'{tmp}/a.wav', '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '96k', '-movflags', '+faststart', out], check=True)
shutil.rmtree(tmp); pr = C.probe(out); want = sum(int(round(p[1] * F)) / F for p in parts)
assert abs(pr['duration'] - want) <= max(0.2, 2 / F * len(parts) / 100 + 0.1), f"preview is {pr['duration']:.2f}s, the plan range {want:.2f}s"
assert pr.get('width') and pr['audio_channels'], 'preview lacks a stream'
print(f"{out}: {len(parts)} shots, {C.hms(pr['duration'])}, {pr['width']}x{pr['height']}, {os.path.getsize(out) / 1e6:.1f} MB")
