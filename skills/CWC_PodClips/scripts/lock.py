"""lock.py <WORK> [--dry-run]      LOCK every approved clip of the episode, then CLEAN UP - automatically.
master.py runs it by itself when the last master of the episode is rendered (Colden 2026-10-02: "Locking and cleaning
should definitely be part of this skill" ... "clean up should be automatic. Anything that the timeline or final output
does not rely on can be trashed. For hard files, send to trash, i will manually delete from there in case of error").
READY when every theme in approved.json has, for EVERY channel it was approved for, an approved version of that channel
with its master on disk, and no edit preview is still waiting on Telegram.
LOCK     each of those timelines: green LOCKED marker, the red DRAFT marker removed, renamed '<name> (L)'; versions.json
         status 'locked'; WORK/lock.json lists timeline, master, frames and loudness of each.
CLEANUP  Resolve: every other timeline this skill made for the episode (versions.json: superseded, rejected, failed,
         never-approved; 'zz BUILDING' leftovers; the 'zz TEST PodClips' tests) is exported as a .drt into the Trash and
         removed; b-roll clips no locked timeline uses leave the pool.
         Files (moved, never deleted): local -> ~/.Trash/CWC_PodClips <show> <Ep> <time>/ ; on the NAS -> the share's
         '#recycle/CWC_PodClips/...' (like CWC_PodCut): preview renders + Telegram copies + contact sheets, the face
         frames of the punch-ins, the raw pre-loudness master renders, the audio tests, b-roll renders no locked timeline
         uses and the b-roll Source captures.
KEPT     the locked timelines and every media they use, the masters, the template, all plans / versions / decisions /
         theme records (small JSON: the record of what was made and why).
NOT READY (exit 2, nothing touched) while anything is half-way: a newer build than the approved one (draft, building),
an open card, a Changes note without a new version, a channel without its build or master.
A CHANGE AFTER THE LOCK = a new version (build, review, approve, master): this run then locks the new one, exports the
old locked timeline as .drt and removes it, trashes its master, and package.py must run again for that upload.
(The Resolve side of that replacement - r_lock.py RELOCKED - had not been exercised when v1.1 shipped: on its first
use render the last master with `master.py render ... --no-lock`, read `lock.py --dry-run`, and run lock.py with Colden present.)"""
import os, re, sys, json, time, shutil, subprocess
import common as C
HERE = os.path.dirname(os.path.abspath(__file__))
def rs(script, seconds, **kw):
    out = subprocess.run([sys.executable, f'{HERE}/rs.py', str(seconds), f'{HERE}/{script}'] + [f'{k}={json.dumps(v)}' for k, v in kw.items()], capture_output=True, text=True).stdout.strip().splitlines()
    r = json.loads(out[-1]) if out else {'error': 'no answer from Resolve'}
    if isinstance(r, dict) and r.get('error'): C.fail(f'Resolve ({script} {kw.get("STEP", "")}): {r["error"]}\n{r.get("trace", "")}')
    return r

def ready(W):
    """-> (rows to lock [(tid, row)], what is missing, stale locked rows [(tid, row)] a newer approval replaces).
    The NEWEST approval of a theme (a tap, not an automatic second-channel approval) decides its channels and its edit;
    every channel needs a version of THAT edit with a master; nothing newer may be half-way (a draft not yet reviewed,
    a build in progress, an open card, a Changes note not yet answered with a new version)."""
    ap = C.load(f'{W}/approved.json') or {}; rows = []; missing = []; stale = []
    items = (C.load(f'{W}/edit/review.json', {}) or {}).get('items', {})
    for a in ap.get('approved', []):
        tid = a['id']; vs = [v for v in C.load(C.vpath(W, tid), []) if C.live(v)]
        for k, it in items.items():
            if k.startswith(tid + '|') and it.get('status') in ('sent', 'changes'): missing.append(f'{k}: ' + ('his Changes note is not answered with a new version yet' if it['status'] == 'changes' else 'the card is still waiting on Telegram'))
        tapped = [v for v in vs if v.get('status') in ('approved', 'locked') and not v.get('approved_via')]
        if not tapped: missing.append(f'{tid}: no approved version'); continue
        latest = max(tapped, key=lambda v: (v.get('approved_at') or '', v['v'])); sha = latest.get('edit_sha'); good = []
        for ch in latest.get('channels') or []:
            chv = [v for v in vs if v['channel'] == ch]
            mine = [v for v in chv if v.get('status') in ('approved', 'locked') and ch in (v.get('channels') or []) and v.get('edit_sha') == sha]
            if not mine: missing.append(f'{tid} {ch}: approved for {ch} (on {latest["channel"]} v{latest["v"]}) but no build of that edit carries the {ch} stinger: build.py "<WORK>" {tid} --channel {ch}'); continue
            v = mine[-1]
            if chv[-1] is not v: missing.append(f'{tid} {ch}: a newer build v{chv[-1]["v"]} is "{chv[-1].get("status")}" - review and send it, or retire it (tg_edit.py supersede)'); continue
            if not (v.get('master') and os.path.exists(v['master']['file'])): missing.append(f'{tid} {ch} v{v["v"]}: no master (master.py render "<WORK>" {tid} {ch})'); continue
            good.append(v)
        rows += [(tid, v) for v in good]
        stale += [(tid, v) for v in vs if v.get('status') == 'locked' and v not in good]
    return rows, missing, stale

def to_trash(path, trash, rel):
    """move (never delete): NAS files to the share's #recycle, local files to ~/.Trash"""
    m = re.match(r'^(/Volumes/[^/]+)/', path); dest = None
    if m and os.path.isdir(f'{m.group(1)}/#recycle'): dest = f'{m.group(1)}/#recycle/CWC_PodClips/{os.path.basename(trash)}/{rel}'
    dest = dest or f'{trash}/{rel}'
    os.makedirs(os.path.dirname(dest), exist_ok=True); shutil.move(path, dest); return dest

def main(W, dry):
    ep = C.episode(W); rows, missing, stale = ready(W)
    if missing: C.ask('not every clip is ready to lock:\n  ' + '\n  '.join(missing))
    if not rows: C.fail('nothing approved to lock')
    plans = {(tid, v['channel'], v['v']): C.load(v['plan']) for tid, v in rows}; P0 = next(iter(plans.values()))
    LOCK = {v['timeline']: (v['timeline'] if v['timeline'].endswith(' (L)') else v['timeline'] + ' (L)') for tid, v in rows}
    keep_tl = set(LOCK) | set(LOCK.values())
    # ---- what goes ----
    delete = []
    for tid in sorted({t for t, _ in rows} | {d for d in os.listdir(f'{W}/edit') if re.fullmatch(r't\d+', d)}):
        for v in C.load(C.vpath(W, tid), []):
            for n in (v.get('timeline'), 'zz BUILDING ' + re.sub(r' \(L\)$', '', v.get('timeline') or '')):
                if n and n not in keep_tl and n not in delete: delete.append(n)
    keep_broll = sorted({b['file'] for P in plans.values() for b in P.get('broll', [])})
    keep_files = {os.path.realpath(v['master']['file']) for _, v in rows}; relock = sorted({v['timeline'] for _, v in stale})
    stamp = time.strftime('%Y%m%d-%H%M%S'); trash = os.path.expanduser(f'~/.Trash/CWC_PodClips {ep["show"]} {ep["ep_key"]} {stamp}')
    moves = []
    for d in sorted(os.listdir(f'{W}/edit')):
        p = f'{W}/edit/{d}'
        if d.startswith('_'): moves.append((p, f'edit/{d}')); continue           # _audiotest
        if not os.path.isdir(p): continue
        for sub in ('preview', 'eyes'):
            if os.path.isdir(f'{p}/{sub}'): moves.append((f'{p}/{sub}', f'edit/{d}/{sub}'))
        if os.path.isdir(f'{p}/master'):
            for f in sorted(os.listdir(f'{p}/master')):
                if os.path.realpath(f'{p}/master/{f}') not in keep_files and not f.startswith('.'): moves.append((f'{p}/master/{f}', f'edit/{d}/master/{f}'))
    bdirs = sorted({os.path.dirname(b) for b in keep_broll}) or [f'{ep["dir"]}/Clips/B-Roll']
    for bd in bdirs:
        if not os.path.isdir(bd): continue
        for f in sorted(os.listdir(bd)):
            p = f'{bd}/{f}'
            if f.startswith('.') or os.path.realpath(p) in {os.path.realpath(x) for x in keep_broll}: continue
            if os.path.isdir(p) and f != 'Source': continue
            moves.append((p, f'b-roll/{f}'))
    print(f'LOCK {len(LOCK)} timeline(s):'); [print(f'  {a} -> {b}') for a, b in LOCK.items()]
    print(f'REMOVE from Resolve (after a .drt backup) if present: {delete} + every "zz TEST PodClips ..." timeline')
    if relock: print(f'RE-LOCK: these LOCKED timelines are replaced by a newer approved version and are removed too (after the backup): {relock}')
    print(f'TRASH {len(moves)} file(s) / folder(s):'); [print(f'  {a}') for a, _ in moves]
    if dry: print('\ndry run - nothing was changed'); return 0
    # ---- lock ----
    r = rs('r_lock.py', 300, PROJECT=ep['project'], STEP='lock', LOCK=LOCK, DELETE=[], RELOCKED=[], BROLL_BIN='', KEEP_BROLL=[], BACKUP_DIR='')
    if r['problems']: C.fail(f'lock: {r["problems"]}')
    for tid, v in rows: C.set_version(W, tid, v['channel'], v['v'], status='locked', timeline=LOCK[v['timeline']], built_as=v.get('built_as') or v['timeline'], locked_at=v.get('locked_at') or C.now())
    for tid, v in stale: C.set_version(W, tid, v['channel'], v['v'], status='superseded: a newer version was approved and locked after the lock', was_locked_at=v.get('locked_at'))
    prev = (C.load(f'{W}/lock.json') or {}).get('cleanups', [])
    lock = {'at': C.now(), 'episode': ep['ep_key'], 'show': ep['show'], 'clips': [{'theme': tid, 'channel': v['channel'], 'v': v['v'], 'timeline': LOCK[v['timeline']], 'master': v['master']['file'],
            'frames': plans[(tid, v['channel'], v['v'])]['frames'], 'loudness': v['master']['loudness'].get('out'), 'res': v['master'].get('res')} for tid, v in rows]}
    lock['cleanups'] = prev; C.save(f'{W}/lock.json', lock)
    # ---- cleanup ----
    tl_names = rs('r_list_tl.py', 120, PROJECT=ep['project'])['timelines']
    delete += [n for n in tl_names if n.startswith('zz TEST PodClips') and n not in delete]
    r = rs('r_lock.py', 900, PROJECT=ep['project'], STEP='cleanup', LOCK={}, DELETE=[n for n in delete + relock if n in tl_names], RELOCKED=relock, BROLL_BIN=P0['clips_bin'] + '/B-Roll', KEEP_BROLL=keep_broll, BACKUP_DIR=f'{trash}/timelines')
    moved = []
    for a, rel in moves:
        if os.path.exists(a): moved.append([a, to_trash(a, trash, rel)])
    lock['cleaned'] = {'at': C.now(), 'timelines_removed': r['removed'], 'timeline_backups': f'{trash}/timelines', 'broll_pool_removed': r['broll_removed'], 'files_moved': moved, 'problems': r['problems']}
    if r['removed'] or moved: lock['cleanups'] = prev + [lock['cleaned']]                   # every cleanup stays on record (a re-run never wipes it)
    C.save(f'{W}/lock.json', lock)
    print(f'\nLOCKED {len(rows)}; removed {len(r["removed"])} timeline(s) (backups {trash}/timelines); {len(r["broll_removed"])} unused b-roll pool clip(s); {len(moved)} file(s) / folder(s) moved to the Trash')
    for p in r['problems']: print('  PROBLEM:', p)
    try:
        import tg_themes as G
        G.api('sendMessage', chat_id=G.chat(), text=f'🔒 {ep.get("show_name", ep["show"])} {ep["ep_key"]} clips locked: {len(rows)} masters.\n' + '\n'.join(f'  {c["timeline"]}' for c in lock['clips']) + f'\nCleanup: {len(r["removed"])} timelines + {len(moved)} files to the Trash.')
    except Exception as e: print('telegram note not sent:', str(e)[:100])
    return 1 if r['problems'] else 0

if __name__ == '__main__':
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    if not a: C.fail(__doc__)
    sys.exit(main(os.path.abspath(a[0]), '--dry-run' in sys.argv))
