"""build.py <WORK> <short id> [--plan-only]
One APPROVED short -> a NEW version of its timeline in Resolve (never replacing one):
  cut.py (the edit) -> plan.py (layouts, captions, hook, tag, b-roll, censor) -> r_build.py through rs.py, one step per
  call: sources (THE SOURCE GATE, first, read-only) -> import -> create (from `00 PodReels Template`) -> every video and
  audio track -> captions -> hook / tag / b-roll / beeps -> hookfit (the hook box measured on a rendered frame) -> verify
  (every piece's FILE PATH, frames, counts; 0 problems -> final name + red DRAFT marker).
Records edit/<id>/versions.json (building -> draft | failed). A failed build keeps its `zz BUILDING` name; nothing is
deleted. GATES: cut.py clean; plan.py clean; the source gate; hookfit must report the box clear of the captions and
inside the safe zone; verify 0 problems. NEVER run while Colden is working in Resolve: a build switches the current
timeline (ask first - `tg_review.py ask-resolve` sends him a one-tap Build now / Wait card)."""
import os, sys, json, subprocess
import common as C, cut as K, plan as PL
HERE = os.path.dirname(os.path.abspath(__file__))

def rs(script, seconds, **kw):
    cmd = [sys.executable, f'{HERE}/rs.py', str(seconds), f'{HERE}/{script}'] + [f'{k}={json.dumps(v)}' for k, v in kw.items()]
    out = subprocess.run(cmd, capture_output=True, text=True).stdout.strip().splitlines()
    r = json.loads(out[-1]) if out else {'error': 'no answer from Resolve'}
    if isinstance(r, dict) and r.get('error'): C.fail(f'Resolve ({script} {kw.get("STEP", "")}): {r["error"]}\n{r.get("trace", "")}')
    return r

def record(work, tid, P, path, status, **more):
    vers = C.load(f'{work}/edit/{tid}/versions.json', []); row = next((x for x in vers if x['v'] == P['v']), None)
    if row is None: row = {'v': P['v'], 'timeline': P['name'], 'plan': path}; vers.append(row)
    row.update(dict(more, status=status)); C.save(f'{work}/edit/{tid}/versions.json', vers); return row

def transparent(path):
    if os.path.exists(path): return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'color=c=black@0.0:s=1080x1920:r=30:d=120,format=yuva444p10le', '-c:v', 'prores_ks', '-profile:v', '4444', '-pix_fmt', 'yuva444p10le', path], check=True)

def run(work, tid, plan_only=False):
    cut = K.build(work, tid); K.report(cut)
    if cut['problems']: C.fail('the edit plan has problems - nothing is built')
    P, path = PL.make(work, tid); transparent(P['transparent'])
    n = {k: sum(1 for x in P['items'] if x['kind'] == k) for k in ('video', 'audio')}
    print(f'\nbuild plan {P["name"]}: {n["video"]} video + {n["audio"]} audio pieces, {len(P["captions"])} caption runs, tag {[t["who"] for t in P["tags"]]}, b-roll {[b["at"] for b in P["broll"]]}, beeps {len(P["beeps"])}\n  {path}')
    if plan_only: return P
    kw = {'PROJECT': P['project'], 'PLAN': path}
    r = rs('r_build.py', 120, STEP='sources', **kw)
    if r['problems']: print('SOURCE GATE FAILED - nothing was created:'); [print('  ', x) for x in r['problems']]; sys.exit(1)
    print('  SOURCE GATE ok: ' + '; '.join(f'{k} <- {v["bin"]}' + (f' (1 of {v["same_name_in_pool"]} with that name)' if v['same_name_in_pool'] > 1 else '') for k, v in r['sources'].items()))
    r = rs('r_build.py', 180, STEP='import', **kw); print('  import:', r.get('imported'))
    record(work, tid, P, path, 'building', started_at=C.now())
    r = rs('r_build.py', 180, STEP='create', **kw); print('  create:', r['video'], r['audio'])
    for k in ('video', 'audio'):
        for t in sorted({x['track'] for x in P['items'] if x['kind'] == k}):
            r = rs('r_build.py', 300, STEP='place', KIND=k, TRACK=t, **kw); print(f'  {k} {t}: {r["placed"]} placed, {r["disabled"]} disabled, {r["with_props"]} with transforms' + (f', PROPS FAILED {r["props_failed"]}' if r['props_failed'] else ''))
            if r['props_failed']: record(work, tid, P, path, 'failed', problems=[f'transforms failed on {k} {t}']); C.fail('Resolve refused some transforms')
    for i in range(0, len(P['captions']), 6):
        r = rs('r_build.py', 240, STEP='captions', I0=i, I1=i + 6, **kw); print('  captions', r['captions'])
    r = rs('r_build.py', 240, STEP='hook', **kw); print('  hook + extras:', {k: r.get(k) for k in ('tags', 'broll', 'beeps') if r.get(k)})
    r = rs('r_build.py', 300, STEP='hookfit', **kw); print(f'  hookfit: size {r["size"]}, box {r["box"]}, caption line {r["caption_px"]}, moved {r["moved_down"]} px, clear {r["clear"]}, safe {r["inside_safe"]}  LOOK: {r["frame"]}')
    if not (r['clear'] and r['inside_safe']): record(work, tid, P, path, 'failed', problems=['hook box placement']); C.fail(f'the hook box is not clear of the captions / inside the safe zone: {r}')
    hook = r
    r = rs('r_build.py', 240, STEP='verify', **kw)
    if r['problems']:
        record(work, tid, P, path, 'failed', problems=r['problems'], timeline=P['building']); print('  VERIFY FAILED - the timeline keeps its zz BUILDING name:'); [print('   ', p) for p in r['problems']]; sys.exit(1)
    record(work, tid, P, path, 'draft', frames=r['frames'], built_at=C.now(), hook=hook)
    print(f'  VERIFIED: {P["name"]} - {r["frames"]} frames ({r["frames"] / P["fps"]:.1f} s)'); return P

if __name__ == '__main__':
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    if len(a) < 2: C.fail(__doc__)
    run(os.path.abspath(a[0]), a[1], '--plan-only' in sys.argv)
