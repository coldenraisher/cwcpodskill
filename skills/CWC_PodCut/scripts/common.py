"""Shared helpers for CWC_PodCut: paths, show files, the episode manifest, ffmpeg/ffprobe wrappers, time mapping.
Everything in this skill is timed in BASE seconds = seconds of the PROGRAM file (the StreamYard feed on V1). A camera's
source time for base time t is  src = (t - off) * rate  (manifest: cameras[*].off / .rate, measured by sync.py)."""
import os, re, sys, json, subprocess

SK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.environ.get('CWC_WORK') or os.path.expanduser('~/Documents/Claude/Projects/Create with Colden/CWC Podcast/work')
VID = ('.mp4', '.mov', '.m4v', '.mxf')
AE_PY = os.path.expanduser('~/Documents/Claude/AutoEditor/python')      # AutoEditor's venv + analysis scripts (read-only)
# Version of each prep step's CODE. Bump a number when that step's output would change: prep.py then re-runs it and
# everything that reads it, on every episode, instead of trusting an old file.
ALGO = {'sync': 3, 'stems': 2, 'words': 2, 'faces': 3, 'fillers': 4, 'layout': 4, 'points': 2, 'reactions': 6}

def show(show_id):
    return json.load(open(f'{SK}/shows/{show_id}.json'))

def shows():
    return [json.load(open(f'{SK}/shows/{f}')) for f in sorted(os.listdir(f'{SK}/shows')) if f.endswith('.json')]

def cache_dir(show_id, ep_key):
    d = f'{WORK}/cache/{show_id}/{ep_key}'; os.makedirs(d, exist_ok=True); return d

def load(path, default=None):
    return json.load(open(path)) if os.path.exists(path) else default

def save(path, obj):
    tmp = path + '.tmp'; json.dump(obj, open(tmp, 'w'), indent=1); os.replace(tmp, path)

def manifest(cache):
    m = load(f'{cache}/manifest.json'); assert m, f'no manifest in {cache} - run intake.py first'; return m

def probe(path):
    """{'duration', 'fps', 'avg_fps', 'width', 'height', 'audio_channels', 'vfr'} - never guessed: a file that cannot be probed stops the run"""
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration:stream=codec_type,codec_name,width,height,r_frame_rate,avg_frame_rate,channels',
                        '-of', 'json', path], capture_output=True, text=True)
    assert r.returncode == 0 and r.stdout.strip(), f'ffprobe failed on {path}: {r.stderr.strip()[:200]}'
    j = json.loads(r.stdout); v = next((s for s in j['streams'] if s['codec_type'] == 'video'), None); a = next((s for s in j['streams'] if s['codec_type'] == 'audio'), None)
    def fr(x):
        n, d = (x or '0/1').split('/'); return float(n) / float(d) if float(d) else 0.0
    out = {'duration': float(j['format']['duration']), 'audio_channels': int(a['channels']) if a else 0}
    if v:
        out.update({'fps': fr(v['r_frame_rate']), 'avg_fps': fr(v['avg_frame_rate']), 'width': v['width'], 'height': v['height'], 'vcodec': v['codec_name']})
        out['vfr'] = abs(out['fps'] - out['avg_fps']) > 0.002
    return out

def pcm(path, ss=None, t=None, sr=16000, af=None):
    """mono float32 audio of a file (or a window of it), on the file's own clock: sample 0 = container time `ss` (or 0).
    A decode from the top pads the audio stream's start offset (StreamYard files start their audio up to 40 ms after
    their video; without the pad every sample would sit that much early - Ep 24 COLDEN.mp4, 2026-10-01)."""
    import numpy as np
    cmd = ['ffmpeg', '-v', 'error']
    if ss is not None: cmd += ['-ss', f'{ss:.3f}']
    if t is not None: cmd += ['-t', f'{t:.3f}']
    filt = ([af] if af else []) + (['aresample=async=1:first_pts=0'] if ss is None else [])
    cmd += ['-i', path, '-vn', '-ac', '1', '-ar', str(sr)] + (['-af', ','.join(filt)] if filt else []) + ['-f', 's16le', '-']
    raw = subprocess.run(cmd, capture_output=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768

def src_time(cam, t):
    """source seconds of camera `cam` (a manifest cameras row) at base second t"""
    return (t - cam['off']) * cam.get('rate', 1.0)

def base_time(cam, s):
    return s / cam.get('rate', 1.0) + cam['off']

def sid_of(m, name):
    return next(c['id'] for c in m['cameras'] if c['name'].lower() == name.lower())

def speakers(m):
    return [c for c in m['cameras'] if c['role'] == 'speaker']

def norm_word(t):
    return re.sub(r"[^a-z'\-]", '', t.lower())

def hms(t):
    t = max(0.0, t); return f'{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}' if t >= 3600 else f'{int(t // 60)}:{t % 60:05.2f}'

def frozen(m):
    """a LOCKED episode that Colden has not re-opened (unlock.py): nothing re-plans, rebuilds or re-tags it"""
    return bool(m.get('locked')) and not m.get('rebuild')

def ack_problem(m, cache):
    """None when the review sheets on disk now are the ones ack.py recorded as looked at, else what is wrong. Required
    for every lock, auto_lock included: auto_lock replaces Colden's word, never the look at the sheets."""
    import hashlib
    ack = load(f'{cache}/ack.json'); rev = f"{WORK}/review/{m['show']}/{m['ep_key']}"
    if not ack: return 'the review sheets were not looked at: open layout.jpg and reactions_in_cut.jpg, then  ack.py <CACHE> "<what you saw>"'
    for f, h in ack['sheets'].items():
        now = hashlib.sha1(open(f'{rev}/{f}', 'rb').read()).hexdigest() if os.path.exists(f'{rev}/{f}') else None
        if now != h: return f'{f} changed since it was looked at ({ack["at"]}) - look again, then ack.py'
    return None

def die(msg, code=2):
    """exit 2 = STOP AND ASK COLDEN (never guess)"""
    print(f'STOP: {msg}'); sys.exit(code)

def rs(script, seconds=120, **g):
    """run a Resolve-side script through rs.py (hard timeout, shared Resolve lock); returns its `result`, raises on error"""
    cmd = [sys.executable, f'{SK}/scripts/rs.py', str(seconds), f'{SK}/scripts/{script}'] + [f'{k}={json.dumps(v)}' for k, v in g.items()]
    r = subprocess.run(cmd, capture_output=True, text=True, env=dict(os.environ, PYTHONUTF8='1'))
    line = (r.stdout.strip().splitlines() or ['null'])[-1]
    try: res = json.loads(line)
    except Exception: raise SystemExit(f'{script}: unreadable answer from Resolve: {r.stdout[-300:]} {r.stderr[-300:]}')
    if isinstance(res, dict) and res.get('error'):
        import glob, time
        recent = [f for f in glob.glob(os.path.expanduser('~/Library/Logs/DiagnosticReports/*Resolve*')) if time.time() - os.path.getmtime(f) < 900]
        alive = subprocess.run(['pgrep', '-f', 'DaVinci Resolve.app/Contents/MacOS/Resolve'], capture_output=True, text=True).stdout.strip()
        hint = ''
        if res['error'] == 'TIMEOUT': hint = ('\nResolve is NOT running any more' if not alive else (f'\na fresh crash report exists: {recent[0]}' if recent else '\nResolve is alive but did not answer in time (busy, a dialog open, or Colden is working in it) - try again'))
        raise SystemExit(f"{script}: {res['error']}\n{res.get('trace', '')}{hint}")
    return res
