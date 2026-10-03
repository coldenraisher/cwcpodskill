"""Build the cut in Resolve from <CACHE>/plan.json - one command, gated, stops at the first failed gate.
usage: build.py <CACHE>        (Resolve running; External scripting = Local; a locked episode needs unlock.py first)
       build.py <CACHE> --prefix "zz TEST Ep 24 PodCut" [--plan trial.json]    a TRIAL build under another name
 0 gates before Resolve is touched: the episode is not locked; intake / sync / points are clean; plan.json carries the
   CURRENT plan.py RULES stamp, no --set overrides, an empty sanity list, the cadence that is on file now, and is newer
   than everything it was made from; the plan's non-negotiables are re-checked here with LITERAL numbers (no shot under
   2 s, a different camera on both sides of every cut, every missing frame a recorded trim); guests have their card
 1 the show's project is opened (open_project.py; refused while a render runs; the open project is saved first)
 2 BASE: built when it does not exist yet (r_base.py), then dumped and checked against the MANIFEST sync, piece by
   piece (record frame and source in-point of every item on every track)
 3 the cut is built as 'zz BUILDING <name>': create -> place per track -> link -> lower thirds
 4 VERIFY on the dumped timeline (below). Pass: renamed to '<cut prefix> vN' (next free N; an existing timeline is never
   replaced). Fail: renamed 'zz FAILED ...' and left for inspection - a half-built or wrong timeline never carries a
   PodCut name that /edit-shorts or /edit-clips could pick up.
 5 the plan and lower-third list the cut was built from are frozen next to the checks ('<cut> (plan).json'); the cut is
   recorded in the manifest; with `auto_lock` in the show file lock.py runs
VERIFY: frames == plan; every camera track cut on the plan's boundaries; exactly ONE enabled video item per shot and it
is the planned camera, on the source frame the sync gives; the program (V1 / A1) on the plan's frame under every shot,
A1 enabled, every ISO audio clip disabled and on its picture's frame; every camera present (enabled or not) under every
shot it has media for; the lower thirds are the planned files at the planned frames over that guest's close-up.
Non-destructive: nothing on an existing timeline is deleted or trimmed; the base is never modified after it is built."""
import os, re, sys, json, time, glob, shutil, hashlib, argparse, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

ap = argparse.ArgumentParser(); ap.add_argument('cache'); ap.add_argument('--slice', type=int, default=300)
ap.add_argument('--prefix', default=None, help='TRIAL build under another name ("zz TEST Ep 24 PodCut")'); ap.add_argument('--plan', default=None, help='with --prefix only: a trial plan file')
A = ap.parse_args()
cache = A.cache; m = C.manifest(cache); R = dict(m['resolve']); F = m['fps']; trial = bool(A.prefix)
if trial: R['cut_prefix'] = A.prefix
assert not A.plan or trial, '--plan is for a trial build (--prefix) only'
# ---- 0 gates ----
if C.frozen(m) and not trial: C.die(f"this episode is LOCKED ({m['locked']['timeline']}). A locked cut is not rebuilt; a new version needs Colden's word: unlock.py <CACHE> --by \"<his words>\"")
if m.get('problems'): C.die(f"intake is not clean: {m['problems']}")
if m.get('sync_problems') or any('sync' not in c for c in C.speakers(m)): C.die(f"sync is not clean: {m.get('sync_problems') or 'a camera has no measured offset'}")
pts = C.load(f'{cache}/points.json') or {}
if not pts.get('confident'): C.die(f"points.json is not confident: {pts.get('notes')}")
RULES = re.search(r"^RULES = '([^']+)'", open(f'{C.SK}/scripts/plan.py').read(), re.M).group(1)
plan_file = A.plan or f'{cache}/plan.json'
plan = C.load(plan_file); assert plan, f'no {plan_file} - run plan.py (a plan that failed a gate leaves none)'
assert plan.get('rules') == RULES, f"the plan was made under rules {plan.get('rules')!r}, the skill is at {RULES!r} - re-run plan.py"
st = plan['stats']
if not trial:
    assert not st.get('overrides'), f"the plan was made with --set {st['overrides']}: a trial plan is not built as a version"
    assert not st.get('sanity'), f"the plan failed its sanity bands: {st['sanity']}"
    cad = json.load(open(f'{C.SK}/references/cadence.json')); cad.update(C.show(m['show']).get('cadence') or {}); cad['tail'] = cad['tail_frames'] / F      # the same derived value plan.py records
    assert st.get('cadence') == cad, 'references/cadence.json (or the show cadence) changed since the plan was made - re-run plan.py'
    deps = ['points.json', 'words.json', 'layout.json', 'reactions.json', 'present.npz', 'vad.json'] + [f'fillers_{c["id"]}.json' for c in C.speakers(m)]
    for dep in deps:
        assert os.path.exists(f'{cache}/{dep}'), f'{dep} missing'
        assert os.path.getmtime(plan_file) >= os.path.getmtime(f'{cache}/{dep}'), f'plan.json is older than {dep} - re-run plan.py'
segs = plan['segments']; cams = m['cameras']; tracks = [{'track': c['track'], 'id': c['id']} for c in cams]
# the non-negotiables once more, with literal numbers (plan.py asserts them with the cadence file's values)
rem = {(int(round(r['srcStart'] * F)), int(round(r['srcEnd'] * F))) for r in plan['removals']}; of = 0
for i, s in enumerate(segs):
    assert s['frames'] >= int(round(2.0 * F)), f"shot {i} is {s['frames'] / F:.2f} s - under 2 s"
    assert s['outFrame'] == of and s['frames'] == s['srcFrames'][1] - s['srcFrames'][0], f'shot {i}: the plan is not contiguous'; of += s['frames']
    assert s['camera'] in {c['id'] for c in cams}, f"shot {i}: unknown camera {s['camera']}"
    if i:
        p = segs[i - 1]; assert p['camera'] != s['camera'], f'shots {i - 1} / {i}: the same camera on both sides of a cut'
        gap = (p['srcFrames'][1], s['srcFrames'][0]); assert gap[0] == gap[1] or gap in rem, f'shots {i - 1} / {i}: {gap[1] - gap[0]} frames missing that are not a recorded trim'
assert of == st['out_frames'], 'plan frames do not add up'
assert R.get('project'), 'the show file names no Resolve project - ask Colden which project this show is cut in'
if C.show(m['show']).get('auto_lock') and not trial:      # this build ends in the lock: the look comes before Resolve is touched
    bad = C.ack_problem(m, cache)
    if bad: C.die(f'auto_lock is on and {bad}')
lt_file = f'{cache}/lower_thirds.json' if not trial else f'{cache}/lower_thirds.trial.json'
if subprocess.run([sys.executable, f'{C.SK}/scripts/lower_thirds.py', cache, '--plan', plan_file, '--out', lt_file]).returncode: sys.exit(2)       # guests need a name + handle on file (never guessed)
LT = json.load(open(lt_file)); assert LT['plan_out_frames'] == st['out_frames'], 'lower_thirds.json is from another plan'
TAG_TRACK = max(c['track'] for c in cams) + 1
plan_sha = hashlib.sha1(open(plan_file, 'rb').read()).hexdigest()
# ---- 1, 2 project + base ----
P = dict(PROJECT=R['project'])
print('1 project:', C.rs('open_project.py', 180, **P))
ls = C.rs('r_list.py', 240, **P); assert not ls['rendering'], 'a render is in progress - not editing timelines'
if R['base'] not in ls['timelines']:
    extra = [s['path'] for s in m.get('screens', [])] + ([m['intro']] if m.get('intro') else [])
    b = C.rs('r_base.py', 600, BIN=R['bin'], NAME=R['base'], CAMS=[{k: c.get(k) for k in ('id', 'role', 'name', 'path', 'track', 'off', 'rate', 'fps', 'duration')} for c in cams], EXTRA=extra, FPS=F, DUR=m['duration'], **P)
    print('2 base built:', {k: b[k] for k in ('frames', 'pieces')})
C.rs('r_dump.py', 120, NAME=R['base'], OUT=f'{cache}/base_dump.json', **P); base = json.load(open(f'{cache}/base_dump.json'))
for c in cams:      # the base must be the one THIS manifest's sync describes - every piece, record frame and source in-point
    it = base['tracks'].get(f"V{c['track']}", {}).get('items') or []; ia = base['tracks'].get(f"A{c['track']}", {}).get('items') or []
    assert it, f"{R['base']}: nothing on V{c['track']} ({c['name']})"
    assert [x[:4] for x in it] == [x[:4] for x in ia], f"{R['base']}: {c['name']}'s audio items do not sit under its picture"
    off, rate = c.get('off', 0.0), c.get('rate', 1.0)
    want = int(round(max(0.0, off) * F)); assert abs(it[0][0] - want) <= 1, f"{c['name']}: placed at frame {it[0][0]} on the base, sync says {want} - the base is from another sync; ask Colden before anything is rebuilt"
    for x in it:
        assert x[5] == os.path.basename(c['path']), f"{R['base']} V{c['track']} holds {x[5]!r}, the manifest says {os.path.basename(c['path'])!r}"
        src = (x[0] / F - off) * rate * c['fps']; assert abs(x[2] - src) <= 1.5, f"{c['name']}: the base item at frame {x[0]} starts on source frame {x[2]}, the sync says {src:.1f} - the base is from another sync"
    for p, q in zip(it, it[1:]): assert q[0] == p[1], f"{c['name']}: a hole in the base track at frame {p[1]}"
print(f"2 base ok: {R['base']} ({base['frames']} frames) matches the manifest sync")
# ---- 3 build under a working name ----
n = 1
while f"{R['cut_prefix']} v{n}" in ls['timelines']: n += 1
POD = f"{R['cut_prefix']} v{n}"; TMP = f'zz BUILDING {POD}'; assert TMP not in ls['timelines'], f'{TMP} exists - an earlier build died; look at it, then rename or remove it in Resolve by hand'
G = dict(PLAN=plan_file, BASE=R['base'], POD=TMP, BIN=R['bin'], TRACKS=tracks, **P)
print('3 create:', C.rs('r_apply.py', 300, STEP='create', **G))
for t in tracks:
    for kind in ('video', 'audio'):
        got = 0; skipped = 0; t0 = time.time()
        for a in range(0, len(segs), A.slice):
            r = C.rs('r_apply.py', 600, STEP='place', TRACK=t['track'], KIND=kind, SEG_SLICE=[a, a + A.slice], **G); got += r['placed']; skipped += r['n_skipped']
            assert r['placed'] == r['wanted'], f"V/A{t['track']} {kind}: placed {r['placed']} of {r['wanted']} in slice {a} - {TMP} is left as it is"
        print(f"  {kind[0].upper()}{t['track']} {got} items ({skipped} shots without media on this camera) {time.time() - t0:.0f}s")
for k in range(40):
    r = C.rs('r_apply.py', 300, STEP='link', LINK_BUDGET=120, **G)
    if r['link_done']: break
else: raise SystemExit('linking did not finish in 40 passes')
print('3 linked')
if LT['tags']:
    canvas = C.rs('open_project.py', 60, **P)['resolution']
    assert [int(x) for x in canvas] == LT['canvas'], f"lower thirds were rendered at {LT['canvas']}, the project timeline is {canvas} - set `canvas` in the show file and re-run"
    print('3 lower thirds:', C.rs('r_tags.py', 300, POD=TMP, BIN=R['bin'], TRACK=TAG_TRACK, TAGS=[{k: t[k] for k in ('file', 'outFrame', 'frames', 'who', 'where')} for t in LT['tags']], **P))
C.rs('r_dump.py', 180, NAME=TMP, OUT=f'{cache}/pod_dump.json', **P); pod = json.load(open(f'{cache}/pod_dump.json'))
# ---- 4 VERIFY ----
fail = []
if pod['frames'] != st['out_frames']: fail.append(f"timeline is {pod['frames']} frames, the plan {st['out_frames']}")
bounds = {(s['outFrame'], s['outFrame'] + s['frames']): s for s in segs}; cam_track = {c['id']: c['track'] for c in cams}; wide = next(c for c in cams if c['role'] == 'wide')
vid = {c['track']: {(i[0], i[1]): i for i in pod['tracks'][f"V{c['track']}"]['items']} for c in cams}
aud = {c['track']: {(i[0], i[1]): i for i in pod['tracks'][f"A{c['track']}"]['items']} for c in cams}
def expected_src(c, base_frame):
    """source frame of camera c at a base frame, from the MANIFEST sync (not from the base timeline)"""
    return (base_frame / F - c.get('off', 0.0)) * c.get('rate', 1.0) * c['fps']
def covered(c, s):
    its = base['tracks'][f"V{c['track']}"]['items']; return its[0][0] <= s['srcFrames'][0] and s['srcFrames'][1] <= its[-1][1]
if not pod['tracks']['A1']['enabled']: fail.append('the program audio track A1 is muted')
for tr in vid:
    stray = [k for k in list(vid[tr]) + list(aud[tr]) if k not in bounds]
    if stray: fail.append(f'track {tr}: {len(stray)} items not on a plan boundary, e.g. {stray[:3]}')
for (a, b), s in bounds.items():
    on = [tr for tr in vid if (a, b) in vid[tr] and vid[tr][(a, b)][4]]
    if on != [cam_track[s['camera']]]: fail.append(f"shot at out frame {a}: enabled video on tracks {on}, plan says V{cam_track[s['camera']]} ({s['name']})"); continue
    for c in cams:
        k = (a, b); tr = c['track']
        if k not in vid[tr] or k not in aud[tr]:
            if c['role'] == 'wide' or covered(c, s): fail.append(f"shot at out frame {a}: {c['name']} has media there but no clip on track {tr} (every camera stays under every shot)")
            continue
        exp = expected_src(c, s['srcFrames'][0]); tol = 1.5 if c['role'] == 'speaker' else 1.01
        if abs(vid[tr][k][2] - exp) > tol: fail.append(f"shot at out frame {a}: {c['name']} picture on source frame {vid[tr][k][2]}, the sync says {exp:.1f}")
        if abs(aud[tr][k][2] - vid[tr][k][2]) > 1: fail.append(f"shot at out frame {a}: {c['name']} sound is not on its picture's frame")
        if tr == 1 and not aud[tr][k][4]: fail.append(f'shot at out frame {a}: program audio disabled')
        if tr != 1 and aud[tr][k][4]: fail.append(f"shot at out frame {a}: {c['name']} ISO audio is enabled")
# lower thirds: exactly the planned files at the planned frames, each over a close-up of that guest
tag_items = pod['tracks'].get(f'V{TAG_TRACK}', {}).get('items') or []
got_tags = sorted((i[0], i[1] - i[0], i[5]) for i in tag_items); want_tags = sorted((t['outFrame'], t['frames'], os.path.basename(t['file'])) for t in LT['tags'])
if got_tags != want_tags: fail.append(f'lower thirds on V{TAG_TRACK}: {got_tags}, planned {want_tags}')
for t in LT['tags']:
    sh_ = bounds.get(tuple(t['shot']))
    if not sh_ or sh_['camera'] != t['camera'] or 'reaction' in sh_['reason']: fail.append(f"lower third for {t['who']} ({t['where']}) is not over a speaking close-up of {t['who']}")
for g in [c['name'] for c in cams if c['role'] == 'speaker' and not c.get('host')]:
    if {t['where'] for t in LT['tags'] if t['who'] == g} != {'beginning', 'end'}: fail.append(f'guest {g} does not have a lower third at the beginning AND the end')
# ---- 5 name, freeze, record ----
final = POD if not fail else f"zz FAILED {POD} {time.strftime('%H%M')}"
C.rs('r_rename.py', 120, OLD=TMP, NEW=final, **P)
rep = {'timeline': final, 'frames': pod['frames'], 'shots': len(segs), 'items': {k: len(v['items']) for k, v in pod['tracks'].items()}, 'fail': fail[:40], 'n_fail': len(fail), 'rules': RULES, 'plan_sha': plan_sha,
       'trial': trial, 'at': time.strftime('%Y-%m-%d %H:%M')}
C.save(f'{cache}/{final} (checks).json', rep); shutil.copyfile(plan_file, f'{cache}/{final} (plan).json'); shutil.copyfile(lt_file, f'{cache}/{final} (lower thirds).json')
print(f"4 verify: {len(segs)} shots, {pod['frames']} frames, {len(fail)} problems -> \"{final}\""); [print('   FAIL', x) for x in fail[:15]]
m = C.manifest(cache); m.setdefault('cuts', []).append({'timeline': final, 'at': rep['at'], 'rules': RULES, 'verified': not fail, 'trial': trial, 'plan_sha': plan_sha,
                                                         'stats': {k: st[k] for k in ('shots', 'out_duration', 'removed_sec', 'avg_shot', 'cuts_per_min', 'reactions_used')}})
if m.get('rebuild') and not trial: m['cuts'][-1]['rebuild_of_locked'] = m['rebuild']
C.save(f'{cache}/manifest.json', m)
if fail: sys.exit(1)
if C.show(m['show']).get('auto_lock') and not trial:
    sys.exit(subprocess.run([sys.executable, f'{C.SK}/scripts/lock.py', cache, '--pod', final, '--by', 'auto_lock (the show file says the skill is tuned)']).returncode)
print(f'\nbuilt and verified: "{final}" in bin "{R["bin"]}". Not locked: lock.py locks it on Colden\'s word (or auto_lock once he says the skill is tuned).')
