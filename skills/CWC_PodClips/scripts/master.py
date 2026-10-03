"""master.py loud <in.mp4> <out.mp4>              the loudness finish on a rendered file (picture copied, never re-encoded)
   master.py render <WORK> <id> <cwc|tcl> [--no-lock]
                                               (after the edit is APPROVED on Telegram) the master of that channel's newest
                                               approved version at the build plan's output resolution, then `loud`.
                                               The LAST master of the episode runs lock.py by itself; `--no-lock` renders it
                                               without locking, so `lock.py <WORK> --dry-run` can be read first (use it for a
                                               change after the lock, or whenever the cleanup list should be seen before it runs)
Ruling 27: "If it still needs loudness bump, add it at the end before final render" - Colden's Fairlight strip on A1 is
the mix; this only measures the finished file and corrects it when it is off: target -14 LUFS integrated (+-0.5), true
peak <= -1.0 dBTP, like AMIRA_Pod_Build. A static gain, then a limiter only as far as the peaks need it - no dynamic
loudness normalisation (it made the volume fluctuate on the shorts, 2026-09-12).
GATES: the result is measured again and must be inside both limits; frame count and video stream identical to the input;
`render` refuses a version that is not approved, and refuses when the approved channel list does not include it."""
import os, re, sys, json, subprocess
import common as C
TARGET, TOL, PEAK = -14.0, 0.5, -1.0
def measure(path):
    r = subprocess.run(['ffmpeg', '-nostats', '-i', path, '-vn', '-af', 'ebur128=peak=true', '-f', 'null', '-'], capture_output=True, text=True).stderr
    s = r[r.rfind('Summary'):]; i = re.search(r'I:\s+(-?[\d.]+) LUFS', s); p = re.search(r'Peak:\s+(-?[\d.]+) dBFS', s)
    if not i or not p: C.fail(f'cannot measure the loudness of {path}')
    return float(i.group(1)), float(p.group(1))
def frames(path):
    r = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=nb_frames', '-of', 'csv=p=0', path], capture_output=True, text=True).stdout.strip()
    return int(r) if r.isdigit() else None
def loud(src, out):
    I, P = measure(src); log = {'in': {'lufs': I, 'true_peak': P}}
    if abs(I - TARGET) <= TOL and P <= PEAK:
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', src, '-c', 'copy', '-movflags', '+faststart', out], check=True); log['action'] = 'none needed'
    else:
        gain = TARGET - I; limit = PEAK - 0.5
        for attempt in range(4):
            af = f'volume={gain:.2f}dB,alimiter=limit={10 ** (limit / 20):.4f}:level=disabled:attack=3:release=60'
            subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', src, '-map', '0:v:0', '-map', '0:a:0', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '320k', '-af', af, '-movflags', '+faststart', out], check=True)
            I2, P2 = measure(out); log.setdefault('passes', []).append({'gain_db': round(gain, 2), 'limit_db': round(limit, 2), 'lufs': I2, 'true_peak': P2})
            if abs(I2 - TARGET) <= TOL and P2 <= PEAK: break
            gain += TARGET - I2
            if P2 > PEAK: limit -= (P2 - PEAK) + 0.2
        log['action'] = f'gain {gain:+.1f} dB' + (' + limiter' if P + gain > PEAK else '')
    I2, P2 = measure(out); log['out'] = {'lufs': I2, 'true_peak': P2}
    if abs(I2 - TARGET) > TOL or P2 > PEAK: C.fail(f'loudness finish did not land: {I2} LUFS, true peak {P2} dBFS ({log})')
    if frames(src) != frames(out): C.fail(f'frame count changed: {frames(src)} -> {frames(out)}')
    return log
def picture(final, P):
    """the master carries THIS channel's stinger and the end screen: frames of the master are compared with the same
    moments of the source files (64x36 grey, mean absolute difference; the right file is under 10, the other channel's
    stinger is over 70 - measured on Ep 24). The second channel's build is approved by its edit signature and never
    gets a review card: this is its picture check."""
    import numpy as np
    def fr(path, t):
        r = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{t:.3f}', '-i', path, '-frames:v', '1', '-vf', 'scale=64:36,format=gray', '-f', 'rawvideo', '-'], capture_output=True).stdout
        return np.frombuffer(r, np.uint8).astype(float) if len(r) == 64 * 36 else None
    fps = P['fps']; st = P['stinger']; o = P['outro']; out = {}; probs = []
    for name, src, t_m, t_s in [('stinger', P['media'].get(st['clip']), st['rec'] / fps, 0.0), ('end screen', P['media'].get(o['end_screen_clip']), o['C'] / fps, o['end_screen_src_in'] / 30.0)]:
        if not src or not os.path.exists(src): probs.append(f'{name}: the source file {src} is not on disk - cannot check the picture'); continue
        ds = []
        for dt in ((1.0, 2.5) if name == 'stinger' else (2.0, 6.0)):
            a, b = fr(final, t_m + dt), fr(src, t_s + dt)
            ds.append(None if a is None or b is None else round(float(np.mean(np.abs(a - b))), 1))
        out[name] = ds
        if any(d is None or d > 20 for d in ds): probs.append(f'{name}: the master does not show {os.path.basename(src)} where the plan puts it (difference {ds}, 20 at most) - wrong stinger / ending or a shifted timeline')
    return out, probs

if __name__ == '__main__':
    if len(sys.argv) >= 4 and sys.argv[1] == 'loud': print(json.dumps(loud(sys.argv[2], sys.argv[3]), indent=1))
    elif len(sys.argv) >= 5 and sys.argv[1] == 'render':
        W, tid, ch = os.path.abspath(sys.argv[2]), sys.argv[3], sys.argv[4]; vs = C.load(f'{W}/edit/{tid}/versions.json', [])
        mine = [v for v in vs if v['channel'] == ch and str(v.get('status', '')) == 'approved' and ch in (v.get('channels') or [])]
        if not mine:
            other = [v for v in vs if str(v.get('status', '')) == 'approved' and ch in (v.get('channels') or [])]
            if other: C.fail(f'{tid} is approved for {ch} (on {other[-1]["channel"]} v{other[-1]["v"]}) but no timeline with the {ch} stinger exists yet: build.py <WORK> {tid} --channel {ch}')
            C.ask(f'{tid} has no version approved for {ch} - the master is rendered only after Colden\'s tap')
        v = mine[-1]
        P = C.load(v['plan']); ep = C.episode(W); out_dir = f'{W}/edit/{tid}/master'; cn = f'{v["timeline"]} raw'
        r = subprocess.run([sys.executable, f'{os.path.dirname(os.path.abspath(__file__))}/rs.py', '3400', f'{os.path.dirname(os.path.abspath(__file__))}/r_render.py', f'PROJECT={json.dumps(ep["project"])}', f'NAME={json.dumps(v["timeline"])}',
                            f'OUT={json.dumps(out_dir)}', f'CN={json.dumps(cn)}', f'W={P["output_res"][0]}', f'H={P["output_res"][1]}', 'LIMIT=3300'], capture_output=True, text=True).stdout.strip().splitlines()
        res = json.loads(r[-1]) if r else {'error': 'no answer'}
        if res.get('error') or not res.get('made'): C.fail(f'render: {res}')
        if frames(res['made']) != P['frames']: C.fail(f'the render has {frames(res["made"])} frames, the plan {P["frames"]}')
        final = f'{out_dir}/{v["timeline"]}.mp4'; log = loud(res['made'], final); pic, pp = picture(final, P)
        if pp: C.fail(f'{tid} {ch}: ' + '; '.join(pp))
        log['picture'] = pic; v = C.set_version(W, tid, v['channel'], v['v'], master={'file': final, 'loudness': log, 'res': P['output_res'], 'at': C.now()})      # re-read: a tap may have landed during the render
        print(json.dumps(v['master'], indent=1))
        import lock as L                                   # the last master of the episode locks and cleans up by itself (Colden 2026-10-02)
        rows, missing, _ = L.ready(W)
        if rows and not missing and '--no-lock' in sys.argv: print(f'\nevery approved clip is mastered; --no-lock: NOT locked. Next: lock.py "{W}" --dry-run (read what it will remove), then lock.py "{W}"'); sys.exit(0)
        if rows and not missing: print('\nevery approved clip is mastered - lock + cleanup:'); sys.exit(L.main(W, False))
        print(f'\nnot locked yet: {missing}')
    else: C.fail(__doc__)
