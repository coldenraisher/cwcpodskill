"""master.py render <WORK> <id>        (after the edit is APPROVED on Telegram) the 1080x1920 H.264 master of the approved
                                     version, then the loudness finish -> <shorts_dir>/Renders/<NN Title>.mp4
   master.py loud <in.mp4> <out.mp4>   the finish alone
Colden 2026-10-02 (Q8): his template strip is the mix; this only measures the finished file and corrects it: -14 LUFS
integrated (+-0.5), true peak <= -1.0 dBTP - a static gain, then a limiter only as far as the peaks need it (no dynamic
normalisation: it made the volume fluctuate on the shorts, 2026-09-12). Picture copied, never re-encoded.
GATES: only an approved version; frame count = plan; the result lands inside both limits; picture stream identical."""
import os, re, sys, json, shutil, subprocess
import common as C
HERE = os.path.dirname(os.path.abspath(__file__)); TARGET, TOL, PEAK = -14.0, 0.5, -1.0
def measure(path):
    r = subprocess.run(['ffmpeg', '-nostats', '-i', path, '-vn', '-af', 'ebur128=peak=true', '-f', 'null', '-'], capture_output=True, text=True).stderr
    s = r[r.rfind('Summary'):]; i = re.search(r'I:\s+(-?[\d.]+) LUFS', s); p = re.search(r'Peak:\s+(-?[\d.]+) dBFS', s)
    if not i or not p: C.fail(f'cannot measure the loudness of {path}')
    return float(i.group(1)), float(p.group(1))
def frames(path):
    r = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-count_frames', '-show_entries', 'stream=nb_read_frames', '-of', 'csv=p=0', path], capture_output=True, text=True).stdout.strip()
    return int(r) if r.isdigit() else None
def loud(src, out):
    I, P = measure(src); log = {'in': {'lufs': I, 'true_peak': P}}; gain = TARGET - I; limit = PEAK - 0.5
    if abs(I - TARGET) <= TOL and P <= PEAK:
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', src, '-c', 'copy', '-movflags', '+faststart', out], check=True); log['action'] = 'none needed'
    else:
        for _ in range(4):
            af = f'volume={gain:.2f}dB,alimiter=limit={10 ** (limit / 20):.4f}:level=disabled:attack=3:release=60'
            subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', src, '-map', '0:v:0', '-map', '0:a:0', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '320k', '-af', af, '-movflags', '+faststart', out], check=True)
            I2, P2 = measure(out); log.setdefault('passes', []).append({'gain_db': round(gain, 2), 'limit_db': round(limit, 2), 'lufs': I2, 'true_peak': P2})
            if abs(I2 - TARGET) <= TOL and P2 <= PEAK: break
            gain += TARGET - I2
            if P2 > PEAK: limit -= (P2 - PEAK) + 0.2
        log['action'] = f'gain {gain:+.1f} dB + limiter at {limit:.1f} dB'
    I2, P2 = measure(out); log['out'] = {'lufs': I2, 'true_peak': P2}
    if abs(I2 - TARGET) > TOL or P2 > PEAK: C.fail(f'loudness finish did not land: {I2} LUFS, true peak {P2} ({log})')
    if frames(src) != frames(out): C.fail(f'frame count changed: {frames(src)} -> {frames(out)}')
    return log
if __name__ == '__main__':
    a = sys.argv[1:]
    if len(a) >= 3 and a[0] == 'loud': print(json.dumps(loud(a[1], a[2]), indent=1))
    elif len(a) >= 3 and a[0] == 'render':
        W, tid = os.path.abspath(a[1]), a[2]; ep = C.episode(W); vs = C.load(f'{W}/edit/{tid}/versions.json', [])
        v = next((x for x in reversed(vs) if x.get('status') == 'approved'), None)
        if not v: C.ask(f'{tid} has no approved version - the master is rendered only after Colden\'s tap')
        P = C.load(v['plan']); raw_dir = f'{W}/edit/{tid}/master'; cn = f'{v["timeline"]} raw'
        r = subprocess.run([sys.executable, f'{HERE}/rs.py', '1800', f'{HERE}/r_render.py', f'PROJECT={json.dumps(ep["project"])}', f'NAME={json.dumps(v["timeline"])}', f'OUT={json.dumps(raw_dir)}',
                            f'CN={json.dumps(cn)}', 'W=1080', 'H=1920', 'LIMIT=1700'], capture_output=True, text=True).stdout.strip().splitlines()
        res = json.loads(r[-1]) if r else {'error': 'no answer'}
        if res.get('error') or not res.get('made'): C.fail(f'render: {res}')
        if frames(res['made']) != P['frames']: C.fail(f'the render has {frames(res["made"])} frames, the plan {P["frames"]}')
        nn = int(tid[1:]); final = f'{ep["shorts_dir"]}/Renders/{nn:02d} {C.tl_name(P["title"])}.mp4'; os.makedirs(os.path.dirname(final), exist_ok=True)
        log = loud(res['made'], final)
        vs = C.load(f'{W}/edit/{tid}/versions.json', []); row = next(x for x in vs if x['v'] == v['v']); row['master'] = {'file': final, 'loudness': log, 'at': C.now()}; C.save(f'{W}/edit/{tid}/versions.json', vs)
        print(json.dumps(row['master'], indent=1))
    else: print(__doc__)
