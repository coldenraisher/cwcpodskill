"""Intake: an episode folder on the NAS -> <CACHE>/manifest.json (who is which file). Nothing is guessed.
usage: intake.py "<episode folder>" [--show creative-lens] [--no-host Jake] [--wide program|build]
The folder (and its `Angles/` subfolder when there is one) may hold:
  program   WIDE.mp4 / Show.mp4 / Program.mp4, or the raw StreamYard recording (the file without -webcam-/-screen-/-video-)
  speakers  <NAME>.mp4 (COLDEN.mp4, JAKE.mp4, NICK.mp4 - the file name IS the person) or raw StreamYard "<title>-<Name>-webcam-...mp4"
  shares    SCREEN 1.mp4 ... / raw StreamYard "-screen-" and "-video-" files (kept for the share layout; not cut on)
  intro     00 INTRO *.mp4 (the teaser that plays before the live greeting; used to find where the show starts)
  Colden.braw -> exit 3: convert it first with braw_convert.py (Colden's LUT), then re-run.
exit 0 = manifest written; exit 2 = STOP AND ASK (a file nobody can place, no program, a host with no file, two files
for one person); exit 3 = a BRAW needs converting."""
import os, re, sys, json, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

ap = argparse.ArgumentParser(); ap.add_argument('episode'); ap.add_argument('--show', default=None)
ap.add_argument('--no-host', action='append', default=[], help='a host who is NOT in this episode (Colden said so) - otherwise a missing host stops the run')
ap.add_argument('--wide', default=None, help='colden-todd: "program" or "build" (Colden rules per episode)'); A = ap.parse_args()
D = A.episode.rstrip('/'); EP = os.path.basename(D)
assert os.path.isdir(D), f'not a folder: {D}'
sh = C.show(A.show) if A.show else next((s for s in C.shows() if D.startswith(s['nas_root'])), None)
if not sh: C.die(f'which show is {D}? pass --show (creative-lens | colden-todd)')
m0 = re.match(sh['episode_pattern'], EP) if sh.get('episode_pattern') else None
ep_no = m0.group(1) if m0 else None
ep_key = f'Ep{ep_no}' if ep_no else re.sub(r'[^A-Za-z0-9]+', '_', EP).strip('_')
ep_label = f'Ep {ep_no}' if ep_no else EP

files = []
for d in (D, os.path.join(D, 'Angles')):
    if os.path.isdir(d): files += [os.path.join(d, f) for f in sorted(os.listdir(d)) if not f.startswith('.') and os.path.isfile(os.path.join(d, f))]
problems, cams, screens, intro, program, braw = [], {}, [], None, [], []; named_program = set()
OTHER_VID = ('.mkv', '.webm', '.mts', '.m2ts', '.avi', '.mpg', '.mpeg', '.wmv', '.flv', '.ts', '.3gp')
alias = {a: h['name'] for h in sh['hosts'] for a in h['aliases'] + [h['name'].lower()]}
def person(raw):
    k = re.sub(r'[_\-]+', ' ', raw).strip().lower()
    return alias.get(k) or alias.get(k.replace(' ', '_')) or raw.replace('_', ' ').strip().title()
for p in files:
    f = os.path.basename(p); stem, ext = os.path.splitext(f); ext = ext.lower()
    if ext == '.braw': braw.append(p); continue
    if ext in OTHER_VID: problems.append(f'{f}: a {ext} video - this skill reads .mp4 / .mov / .m4v / .mxf; what is this file?'); continue
    if ext not in C.VID: continue
    sy = re.match(r'^(?P<title>.+)-(?P<name>[^-]+)-(?P<kind>webcam|screen|video)-(?P<h>\d+)h_(?P<m>\d+)m_(?P<s>\d+)s_(?P<ms>\d+)ms-StreamYard$', stem)
    if sy:
        at = int(sy['h']) * 3600 + int(sy['m']) * 60 + int(sy['s']) + int(sy['ms']) / 1000
        if sy['kind'] == 'webcam': cams.setdefault(person(sy['name']), []).append(p)
        else: screens.append({'path': p, 'kind': sy['kind'], 'by': person(sy['name']), 'filename_start': at})
    elif re.match(r'^(wide|show|program)$', stem.strip(), re.I): program.append(p); named_program.add(p)
    elif re.match(r'^screen\b', stem, re.I): screens.append({'path': p, 'kind': 'screen', 'by': None, 'filename_start': None})
    elif re.match(r'^00\s*intro', stem, re.I): intro = p
    elif os.path.dirname(p) == D and os.path.isdir(os.path.join(D, 'Angles')): problems.append(f'{f}: a video in the episode root that is not WIDE / 00 INTRO - what is it?')
    elif re.match(r'^[A-Za-z][A-Za-z .\']{1,30}$', stem.strip()): cams.setdefault(person(stem.strip()), []).append(p)
    else: program.append(p)      # an unnamed long file = the raw StreamYard recording (checked by length below)
if braw:
    print('BRAW found: ' + ', '.join(braw)); print('convert first:  python3 scripts/braw_convert.py "<file.braw>"   (Colden\'s LUT), then re-run intake'); sys.exit(3)
for n, ps in cams.items():
    if len(ps) > 1: problems.append(f'{n}: {len(ps)} files ({[os.path.basename(p) for p in ps]}) - one angle per person; which one?')
if len(program) > 1:
    iso = max((C.probe(ps[0])['duration'] for ps in cams.values()), default=0)
    long_ = [p for p in program if C.probe(p)['duration'] >= 0.6 * iso]
    if len(long_) == 1: program = long_
wide_mode = A.wide or (C.load(f"{C.cache_dir(sh['id'], ep_key)}/manifest.json") or {}).get('wide_ruled') or sh.get('wide', 'program')
if wide_mode == 'ask': problems.append('this show needs a ruling per episode: is the program feed usable as the wide (--wide program) or must a two-shot be built from the ISOs (--wide build)?')
if wide_mode == 'build': problems.append('--wide build is not written yet (a two-shot rendered from the ISOs) - tell Colden before going on')
if len(program) != 1: problems.append(f'expected exactly one program feed (WIDE.mp4), found {[os.path.basename(p) for p in program]}')
elif program[0] not in named_program:      # not called WIDE / Show / Program: it must at least be as long as the cameras
    iso = max((C.probe(ps[0])['duration'] for ps in cams.values()), default=0); d_ = C.probe(program[0])['duration']
    if not (0.9 * iso <= d_ <= 1.15 * iso): problems.append(f'{os.path.basename(program[0])} is taken for the program feed but is {C.hms(d_)} against cameras of {C.hms(iso)} - is it?')
greg = json.load(open(f'{C.SK}/references/guests.json')).get(sh['id'], {})
for n in cams:      # a file named like a person who is neither a host nor a guest on file: ask NOW (it may be "Final.mp4"), not after an hour of analysis
    if n not in [h['name'] for h in sh['hosts']] and not (greg.get(n, {}).get('name') and greg.get(n, {}).get('handle')):
        problems.append(f'{n}: not a host and not in references/guests.json - who is this? (a guest needs a full name and a YouTube handle on file, with where they came from; never guessed)')
for h in sh['hosts']:
    if h['name'] not in cams and h['name'] not in A.no_host: problems.append(f"host {h['name']} has no file (still copying? not in this episode? -> --no-host {h['name']})")
if len(cams) < 2: problems.append(f'{len(cams)} speaker file(s) - a multicam cut needs at least two')

hosts = [h['name'] for h in sh['hosts']]; guests = [n for n in cams if n not in hosts]
order = []
for slot in sh['track_order']:
    if slot == '<guests>': order += sorted(guests)
    else:
        n = next((h for h in hosts if h.lower() == slot), None)
        if n and n in cams: order.append(n)
cameras = []
if len(program) == 1:
    pr = C.probe(program[0]); cameras.append({'id': 'wide', 'role': 'wide', 'name': 'WIDE', 'path': program[0], 'track': 1, 'off': 0.0, 'rate': 1.0, **pr})
for k, n in enumerate(order, 1):
    p = cams[n][0]; pr = C.probe(p)
    cameras.append({'id': f'speaker_{k}', 'role': 'speaker', 'name': n, 'host': n in hosts, 'path': p, 'track': k + 1, **pr})
    if pr.get('vfr'): problems.append(f"{n}: {os.path.basename(p)} is variable frame rate ({pr['fps']:.3f} / {pr['avg_fps']:.3f}) - a camera file must be constant; re-export it")
for c in cameras: st = os.stat(c['path']); c['size'] = st.st_size; c['mtime'] = int(st.st_mtime)
pf = cameras[0]['fps'] if cameras and cameras[0]['role'] == 'wide' else 30.0; fps = int(round(pf))
if abs(pf - fps) > 0.01: problems.append(f'the program is {pf:.3f} fps - only whole frame rates (30, 25, 24, 60) have been run through this skill; tell Colden before going on')
for s in screens: s.update(C.probe(s['path']))
cache = C.cache_dir(sh['id'], ep_key)
res = sh['resolve']
man = {'show': sh['id'], 'episode': EP, 'ep_no': ep_no, 'ep_key': ep_key, 'dir': D, 'cache': cache, 'fps': fps,
       'duration': cameras[0]['duration'] if cameras else None, 'cameras': cameras, 'screens': screens, 'intro': intro,
       'resolve': {'project': res['project'], 'bin': re.sub(r'[\\/:*?"<>|]', '-', EP),      # Resolve's API refuses a bin named with ':' (2026-10-01: 'Ep. 24 - 10:1' -> 'Ep. 24 - 10-1')
                    'base': (res['base'].replace('<NN>', ep_no or '').replace('<episode>', EP)), 'cut_prefix': (res['cut'].replace('<NN>', ep_no or '').replace('<episode>', EP))},
       'wide_mode': wide_mode, 'wide_ruled': A.wide or (C.load(f"{C.cache_dir(sh['id'], ep_key)}/manifest.json") or {}).get('wide_ruled'), 'problems': problems}
prev = C.load(f'{cache}/manifest.json') or {}
for c in man['cameras']:                     # keep measured sync when the same file is still the camera
    old = next((o for o in prev.get('cameras', []) if o['path'] == c['path'] and 'sync' in o), None)
    if old and (old.get('size'), old.get('mtime')) in ((c['size'], c['mtime']), (None, None)): c.update({k: old[k] for k in ('off', 'rate', 'sync')})      # the SAME file (path, size, date): a replaced file is measured again
for k in ('locked', 'cuts', 'sync_problems', 'rebuild', 'lock_history', 'cleaned'):                  # what build.py / lock.py recorded survives a re-run of intake
    if k in prev: man[k] = prev[k]
C.save(f'{cache}/manifest.json', man)
print(f"{sh['name']} - {EP}  ->  {cache}/manifest.json")
for c in cameras: print(f"  V{c['track']} {c['id']:10s} {c['name']:8s} {os.path.basename(c['path'])}  {c['width']}x{c['height']} {c['fps']:.3f} fps{' VFR' if c.get('vfr') else ''} {C.hms(c['duration'])}")
for s in screens: print(f"  share   {s['kind']:6s} {os.path.basename(s['path'])}  {C.hms(s['duration'])}")
print(f'  intro   {os.path.basename(intro) if intro else "none"}')
print(f'CACHE={cache}')
if problems:
    print('\nSTOP AND ASK:'); [print('  - ' + p) for p in problems]; sys.exit(2)
