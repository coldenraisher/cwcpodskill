"""Everything before Resolve, one command. A step is SKIPPED only when its recorded fingerprint still matches what it
would be made from now; otherwise its old outputs are moved aside and it runs again. A failed gate stops the run and
records nothing, so the same gate fires again next time (it cannot be walked past by re-running).
usage: prep.py "<episode folder>" [--show creative-lens] [--no-host Jake] [--wide program|build] [--from <step>]
steps: intake -> sync -> stems (+VAD) -> words + faces (in parallel) -> fillers -> layout -> points -> reactions -> plan
       -> the sheet of the reactions that are in the cut
exit 0 = <CACHE>/plan.json is ready for build.py; exit 2 = STOP AND ASK Colden (the step prints what it needs);
exit 3 = a BRAW must be converted first (braw_convert.py); any other non-zero = a gate failed: read it, do not work
around it. A LOCKED episode is not re-run at all. Review sheets land in <work>/review/<show>/<episode>/.
Fingerprints (<CACHE>/state.json): every camera's path + size + date + who it is + its track, the measured offsets, the
version of each step's code (common.ALGO) and the fingerprints of the steps it reads. So a replaced camera file, a guest
added (which renumbers the speakers), a re-sync or a changed algorithm re-runs exactly what depends on it.
Steps run by hand on the CACHE are not recorded: prep.py will run them again."""
import os, sys, glob, json, time, hashlib, subprocess, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
ap = argparse.ArgumentParser(); ap.add_argument('episode'); ap.add_argument('--show', default=None); ap.add_argument('--no-host', action='append', default=[])
ap.add_argument('--wide', default=None); ap.add_argument('--from', dest='frm', default=None); A = ap.parse_args()
S = f'{C.SK}/scripts'; py = sys.executable
ia = [A.episode] + (['--show', A.show] if A.show else []) + [x for h in A.no_host for x in ('--no-host', h)] + (['--wide', A.wide] if A.wide else [])
r = subprocess.run([py, f'{S}/intake.py'] + ia, capture_output=True, text=True); print(r.stdout, r.stderr[-800:] if r.returncode not in (0, 2, 3) else '')
if r.returncode: sys.exit(r.returncode)
cache = next(l.split('=', 1)[1] for l in r.stdout.splitlines() if l.startswith('CACHE=')); m = C.manifest(cache)
if C.frozen(m):
    print(f"\nLOCKED: {m['locked']['timeline']} ({m['locked']['at']}, {m['locked']['by']}). Nothing is re-run on a locked episode (unlock.py --by \"<Colden's words>\" re-opens it)."); sys.exit(0)
rev = f"{C.WORK}/review/{m['show']}/{m['ep_key']}"; os.makedirs(rev, exist_ok=True)
ORDER = ['sync', 'stems', 'words', 'faces', 'fillers', 'layout', 'points', 'reactions']
DEPS = {'sync': [], 'stems': ['sync'], 'words': ['stems'], 'faces': ['sync'], 'fillers': ['words'], 'layout': ['faces', 'words'], 'points': ['layout', 'words'], 'reactions': ['faces', 'words']}
OUT = {'sync': [], 'stems': ['*.wav', 'stems.json', 'vad.json', 'audio_reactions.json', 'vad_input.json', 'reactions_input.json'], 'words': ['words.json', 'words_speaker_*.json'],
       'faces': ['faces_*.npz'], 'fillers': ['fillers_*.json'], 'layout': ['layout.json'], 'points': ['points.json'], 'reactions': ['reactions.json', 'present.npz']}
ARGS = {'layout': ['--sheet', f'{rev}/layout.jpg'], 'reactions': ['--sheet', f'{rev}/reactions_passed.jpg']}
state = C.load(f'{cache}/state.json', {})
def fp(step):
    """what this step is made from, right now"""
    mm = C.manifest(cache); cams = [[c['id'], c['name'], c['track'], c['path'], c.get('size'), c.get('mtime')] for c in mm['cameras']]
    offs = [[c['id'], c.get('off'), c.get('rate')] for c in mm['cameras']]
    own = {'sync': cams, 'stems': offs, 'faces': [cams, offs]}.get(step, [])
    return hashlib.sha1(json.dumps([C.ALGO[step], own, [state.get(d, {}).get('hash') for d in DEPS[step]]], sort_keys=True).encode()).hexdigest()[:16]
def have(step):
    return all(glob.glob(f'{cache}/{pat}') for pat in OUT[step]) if step != 'sync' else (all('sync' in c for c in C.speakers(C.manifest(cache))) and not C.manifest(cache).get('sync_problems'))
def fresh(step): return state.get(step, {}).get('hash') == fp(step) and have(step) and not forced.get(step)
def aside(step):
    old = [f for pat in OUT[step] for f in glob.glob(f'{cache}/{pat}')]
    if not old: return
    d = f"{cache}/_stale/{time.strftime('%Y%m%d-%H%M%S')}"; os.makedirs(d, exist_ok=True)
    for f in old: os.replace(f, f'{d}/{os.path.basename(f)}')
    print(f'   ({step}: {len(old)} stale file(s) moved to {d})')
def start(step):
    aside(step); print(f'\n== {step}', flush=True); return (step, time.time(), subprocess.Popen([py, f'{S}/{step}.py', cache] + ARGS.get(step, [])))
def finish(job):
    step, t0, p = job; rc = p.wait(); print(f'   ({step}: {time.time() - t0:.0f}s, exit {rc})', flush=True)
    if rc:
        state.pop(step, None); C.save(f'{cache}/state.json', state); sys.exit(rc)
    state[step] = {'hash': fp(step), 'at': time.strftime('%Y-%m-%d %H:%M')}; C.save(f'{cache}/state.json', state)
forced = {s: True for s in (ORDER[ORDER.index(A.frm):] if A.frm else [])}
for step in ('sync', 'stems'):
    if not fresh(step): finish(start(step)); forced.pop(step, None)
jobs = [start(s) for s in ('faces', 'words') if not fresh(s)]        # the two long ones, side by side
for j in sorted(jobs, key=lambda j: j[0] != 'words'): finish(j); forced.pop(j[0], None)
for step in ('fillers', 'layout', 'points', 'reactions'):
    if not fresh(step): finish(start(step)); forced.pop(step, None)
for name, args in (('plan', [cache]), ('reaction_sheet', [cache, f'{rev}/reactions_in_cut.jpg'])):
    print(f'\n== {name}', flush=True); rc = subprocess.run([py, f'{S}/{name}.py'] + args).returncode
    if rc: sys.exit(rc)
print(f'\nready: {cache}/plan.json\nLOOK at: {rev}/layout.jpg and {rev}/reactions_in_cut.jpg, then record it:  python3 {S}/ack.py "{cache}" "<what you saw>"\nnext: python3 {S}/build.py "{cache}"')
