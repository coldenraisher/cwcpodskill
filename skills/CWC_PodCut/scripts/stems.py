"""Stems in BASE time, then speech detection - no Resolve render needed.
usage: stems.py <CACHE>     (after sync.py)
  <CACHE>/speaker_<k>.wav  each speaker's own audio, 16 kHz mono, shifted (and rate-corrected) onto the program's clock,
                           exactly as long as the program;  <CACHE>/wide.wav = the program mix
  <CACHE>/vad.json         Silero VAD per stem (AutoEditor's analyze_vad.py, its venv - read-only reuse)
  <CACHE>/audio_reactions.json   AutoEditor's audio reaction score per speaker at 10 Hz (laughs / bursts while others talk)
Gate: every stem within 0.1 s of the program's length, and each speaker's stem correlates with the program (the sync
is re-proved on the stems across the show)."""
import os, sys, json, subprocess, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

cache = sys.argv[1]; m = C.manifest(cache); DUR = m['duration']
assert not m.get('sync_problems'), f"sync is not clean: {m['sync_problems']}"
assert not m.get('problems'), f"intake is not clean: {m['problems']}"
import wave
def write_wav(path, x):
    w = wave.open(path, 'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(x.astype('<i2').tobytes()); w.close()
SR = 16000; N = int(round(DUR * SR))
for cam in m['cameras']:
    out = f"{cache}/{cam['id']}.wav"
    if os.path.exists(out) and abs(C.probe(out)['duration'] - DUR) < 0.1 and C.load(f'{cache}/stems.json', {}).get(cam['id']) == [cam.get('off', 0.0), cam.get('rate', 1.0), 2]: continue
    assert cam['role'] == 'wide' or 'sync' in cam, f"{cam['name']} is not synced - run sync.py"
    print(f"stem {cam['id']} ({cam['name']}) ...")
    # the camera's audio, resampled sample by sample onto the program's clock: base t -> source (t - off) * rate. Done in
    # numpy because ffmpeg's asetrate only takes whole Hz (20 ppm steps) and StreamYard ISOs drift by ~8 ppm.
    s0 = max(0.0, C.src_time(cam, 0.0)); x = (C.pcm(cam['path'], ss=s0 if s0 > 0 else None, sr=SR) * 32768.0).astype(np.float32)
    y = np.zeros(N, np.float32); CH = SR * 120
    for i in range(0, N, CH):
        t = np.arange(i, min(N, i + CH), dtype=np.float64) / SR; pos = (C.src_time(cam, t) - s0) * SR
        i0 = np.floor(pos).astype(np.int64); fr = (pos - i0).astype(np.float32); ok = (i0 >= 0) & (i0 < len(x) - 1); j = np.clip(i0, 0, len(x) - 2)
        y[i:i + len(t)] = np.where(ok, x[j] * (1 - fr) + x[j + 1] * fr, 0.0)
    write_wav(out, np.clip(y, -32768, 32767)); del x, y
    st = C.load(f'{cache}/stems.json', {}); st[cam['id']] = [cam.get('off', 0.0), cam.get('rate', 1.0), 2]; C.save(f'{cache}/stems.json', st)
# proof: each speaker stem lines up with the program across the show (+-0.5 s search, must peak within 40 ms of zero)
for cam in C.speakers(m):
    lags = []
    for t in np.linspace(0.15, 0.85, 9) * DUR:
        a = np.abs(C.pcm(f'{cache}/wide.wav', ss=t, t=45)); b = C.pcm(f"{cache}/{cam['id']}.wav", ss=t, t=45)
        fr = np.sqrt((b[:len(b) // 320 * 320].reshape(-1, 320) ** 2).mean(1)); top = np.percentile(fr, 99)
        if top < 2e-3 or (fr > 0.16 * top).mean() < 0.10: continue
        b = np.abs(b); a -= a.mean(); b -= b.mean(); n = SR // 2; L = 2 * len(a)
        c = np.fft.irfft(np.fft.rfft(a, L) * np.conj(np.fft.rfft(b, L)), L); c = np.concatenate([c[-n:], c[:n + 1]])
        if c.max() / (np.sqrt((a ** 2).sum() * (b ** 2).sum()) + 1e-9) < 0.15: continue      # others talk over this stretch: no clean peak
        lags.append((int(np.argmax(c)) - n) / SR)
    assert len(lags) >= 2, f"{cam['name']}: only {len(lags)} place(s) with a clean peak to prove the stem on"
    worst = max(abs(x) for x in lags); print(f"  {cam['name']:8s} stem vs program: {len(lags)} checks, worst {worst * 1000:.0f} ms")
    assert worst <= 0.04, f"{cam['name']}: stem is {worst * 1000:.0f} ms off the program - sync is wrong"
cams = m['cameras']
json.dump({'speakers': [{'id': c['id'], 'label': c['name'], 'path': f"{cache}/{c['id']}.wav"} for c in cams], 'out': f'{cache}/vad.json'}, open(f'{cache}/vad_input.json', 'w'), indent=1)
json.dump({'vad_path': f'{cache}/vad.json', 'out': f'{cache}/audio_reactions.json'}, open(f'{cache}/reactions_input.json', 'w'), indent=1)
PY = f'{C.AE_PY}/.venv/bin/python'; assert os.path.exists(PY), f'AutoEditor python venv missing: run {os.path.dirname(C.AE_PY)}/scripts/setup-python.sh'
for what in ('vad', 'reactions'):
    made = f"{cache}/{'vad' if what == 'vad' else 'audio_reactions'}.json"
    if os.path.exists(made) and all(os.path.getmtime(made) > os.path.getmtime(f"{cache}/{c['id']}.wav") for c in cams): continue      # newer than EVERY stem
    print(f'{what} ...'); r = subprocess.run([PY, f'{C.AE_PY}/analyze_{what}.py', '--input', f'{cache}/{what}_input.json'], capture_output=True, text=True)
    last = [json.loads(l) for l in r.stdout.splitlines() if l.startswith('{') and '"progress"' not in l][-1:]
    assert last and last[0].get('type') == 'done', f'{what} failed: {r.stdout[-300:]} {r.stderr[-300:]}'
v = json.load(open(f'{cache}/vad.json'))['speakers']
for c in cams: print(f"  {c['name']:8s} speech {sum(s['end'] - s['start'] for s in v[c['id']]['segments']) / 60:5.1f} min in {len(v[c['id']]['segments'])} runs")
