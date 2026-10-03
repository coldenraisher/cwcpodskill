"""LOCK a verified cut: green LOCKED marker at frame 0, `locked` in the manifest, a frozen copy of everything the cut was
built from, and the hand-off block for the next skills.
usage: lock.py <CACHE> --pod "Ep 24 PodCut v1" --by "<Colden's words>" [--no-cleanup]       (auto_lock passes its own --by)
Last step: cleanup.py - the cut becomes '<cut> (L)', every other timeline of the episode is backed up and removed,
working files go to the Trash.
Gates (all must hold - a cut is never locked on a hunch):
  - the cut's '(checks).json' from build.py exists with ZERO failures, is not a trial build, and its plan hash equals
    the frozen '<cut> (plan).json' build.py wrote
  - the manifest is clean (no intake / sync problems) and the timeline in Resolve still has the plan's length
  - the review sheets were looked at (ack.py) and are the ones on disk now - ALWAYS: `auto_lock` (on since Colden
    declared the skill tuned, 2026-10-02) replaces only his word
  - no other version of this episode is locked (a second lock needs the first one's --rebuild-locked record)
Frozen in <CACHE>/locked/<cut>/: plan, lower thirds, points, layout, reactions, words, dumps, checks. The hand-off
points THERE - a later re-plan of the cache cannot change what the locked cut is described by."""
import os, sys, json, time, shutil, hashlib, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
ap = argparse.ArgumentParser(); ap.add_argument('cache'); ap.add_argument('--pod', required=True); ap.add_argument('--by', required=True); ap.add_argument('--no-cleanup', action='store_true'); A = ap.parse_args()
cache = A.cache; m = C.manifest(cache); R = m['resolve']; sh = C.show(m['show'])
rep = C.load(f'{cache}/{A.pod} (checks).json'); assert rep, f'no checks for {A.pod} - build it with build.py'
assert not rep['n_fail'], f"{A.pod} failed VERIFY ({rep['n_fail']} problems) - not locking"
assert not rep.get('trial'), f'{A.pod} is a trial build - not locking'
pf = f'{cache}/{A.pod} (plan).json'; assert os.path.exists(pf), f'{pf} missing - the cut was built before plans were frozen; ask Colden'
assert hashlib.sha1(open(pf, 'rb').read()).hexdigest() == rep['plan_sha'], 'the frozen plan is not the one the checks were made on'
plan = json.load(open(pf))
assert not m.get('problems') and not m.get('sync_problems'), f"the manifest is not clean: {m.get('problems')} {m.get('sync_problems')}"
if m.get('locked') and A.pod not in (m['locked']['timeline'], m['locked'].get('built_as')):
    cut = next((c for c in m.get('cuts', []) if c['timeline'] == A.pod), {})
    assert m.get('rebuild') and cut.get('rebuild_of_locked'), f"{m['locked']['timeline']} is already locked and {A.pod} was not built after an unlock.py on Colden's word"
bad = C.ack_problem(m, cache); assert not bad, bad      # auto_lock too: it replaces Colden's word, never the look
d = C.rs('r_dump.py', 180, PROJECT=R['project'], NAME=A.pod, OUT=f'{cache}/pod_dump.json')
assert d['frames'] == plan['stats']['out_frames'], f"{A.pod} is {d['frames']} frames in Resolve now, the plan it was verified on is {plan['stats']['out_frames']} - it was edited after the build"
at = time.strftime('%Y-%m-%d %H:%M')
res = C.rs('r_lock.py', 120, PROJECT=R['project'], NAME=A.pod, PREFIX=R['cut_prefix'] + ' v', NOTE=f'Locked {at} ({A.by}). CWC_PodCut rules {rep["rules"]}. Do not rebuild.')
assert res['marker'], f'marker failed: {res}'
if res['other_locked_versions']: print(f"NOTE: other versions still carry a LOCKED marker: {res['other_locked_versions']} - tell Colden; nothing is removed")
snap = f'{cache}/locked/{A.pod}'; os.makedirs(snap, exist_ok=True)
shutil.copyfile(pf, f'{snap}/plan.json'); shutil.copyfile(f'{cache}/{A.pod} (checks).json', f'{snap}/checks.json')
lt = f'{cache}/{A.pod} (lower thirds).json'; shutil.copyfile(lt if os.path.exists(lt) else f'{cache}/lower_thirds.json', f'{snap}/lower_thirds.json')
for f in ('points.json', 'layout.json', 'reactions.json', 'words.json', 'pod_dump.json', 'base_dump.json', 'ack.json'):
    if os.path.exists(f'{cache}/{f}'): shutil.copyfile(f'{cache}/{f}', f'{snap}/{f}')
if m.get('locked') and A.pod not in (m['locked']['timeline'], m['locked'].get('built_as')): m.setdefault('lock_history', []).append(dict(m['locked'], replaced_by=A.pod, reopened=m.get('rebuild')))
m.pop('rebuild', None)
m['locked'] = {'timeline': A.pod, 'at': at, 'by': A.by, 'bin': R['bin'], 'project': R['project'], 'cache': cache, 'snapshot': snap, 'plan': f'{snap}/plan.json', 'rules': rep['rules']}
C.save(f'{cache}/manifest.json', m)
if '--no-cleanup' not in sys.argv:      # the last step of a lock (Colden 2026-10-01): one timeline left, named '(L)', working files to the Trash
    import subprocess
    rc = subprocess.run([sys.executable, f'{C.SK}/scripts/cleanup.py', cache]).returncode
    assert rc == 0, 'the cut IS locked, but cleanup.py failed - read its message; nothing was half-removed without a backup'
    m = C.manifest(cache)
L = json.load(open(f'{snap}/lower_thirds.json'))
lt_txt = 'Guests (lower thirds on the track above the cameras, beginning + end): ' + ('; '.join(f"{g['name']} {g['handle']} (photo {g['avatar']})" for g in L['guests'].values()) or 'none')
final = m['locked']['timeline']
print(f"""LOCKED "{final}" (project {R['project']}, bin {R['bin']}), green marker at frame 0.
== hand-off (for /edit-shorts, /edit-clips and the assembly skill)
Timeline "{final}": V1 program, {', '.join(f"V{c['track']} {c['name']}" for c in m['cameras'] if c['role'] == 'speaker')}; one enabled video item per shot; A1 program mix enabled, ISO audio clips disabled.
{lt_txt}
Frozen with the lock in {snap}: plan.json (shots: srcStart/srcEnd = program seconds, outStart/outEnd = cut seconds), words.json (program seconds), layout.json, reactions.json, lower_thirds.json. Use THESE, not the working files in the cache.""")
