"""Clean up after a LOCK (Colden 2026-10-01: "add a clean up step. delete extra files/timelines and any tests created in
the resolve bin. Leave only the finished podcut timeline appended with \"(L)\" for locked. if there were any cache renders
for checks or files created that are no longer needed for next steps, move to trash.")
usage: cleanup.py <CACHE> [--dry-run]         (lock.py runs it as its last step)
RESOLVE  the locked cut is renamed '<cut> (L)'; the BASE, every earlier version and every 'zz TEST / zz BUILDING /
         zz FAILED' timeline of this episode is exported as a .drt into the Trash folder and removed from the project.
         Media in the bin (camera files, lower thirds, Shares) stays: the locked cut and the next skills use it.
FILES    to ~/.Trash/CWC_PodCut <episode> <time>/ : the review folder (preview renders, sheets - the two sheets that
         were looked at are copied into the lock snapshot first) and everything in the cache except manifest.json and
         the snapshot of the CURRENT lock (stems, face tracks, transcripts per speaker, dumps, trial plans, stale files,
         snapshots of earlier locks). On the NAS: superseded / unreferenced lower-third files go to the share's
         '#recycle' folder.
KEPT     <CACHE>/manifest.json and <CACHE>/locked/<cut>/ (plan, words, layout, reactions, lower thirds, points, checks,
         sheets) - what /edit-shorts, /edit-clips and the assembly skill read.
Nothing is hard-deleted: files are moved, timelines are backed up first. A later rebuild (unlock.py) re-runs prep
from the camera files.
Gates: the episode is locked and not re-opened; the snapshot holds plan.json; Resolve confirms the LOCKED marker."""
import os, re, sys, json, time, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
cache = sys.argv[1]; DRY = '--dry-run' in sys.argv; m = C.manifest(cache); R = m['resolve']
assert m.get('locked') and not m.get('rebuild'), 'cleanup runs on a locked episode only (and not while it is re-opened)'
L = m['locked']; snap = L['snapshot']; assert os.path.exists(f'{snap}/plan.json'), f'the lock snapshot {snap} has no plan.json'
keep = L.get('built_as') or L['timeline']; final = keep if keep.endswith(' (L)') else keep + ' (L)'
stamp = time.strftime('%Y%m%d-%H%M%S'); trash = os.path.expanduser(f"~/.Trash/CWC_PodCut {m['ep_key']} {stamp}")
# ---- Resolve ----
ls = C.rs('r_list.py', 240, PROJECT=R['project'])['timelines']
mine = {R['base']} | {c['timeline'] for c in m.get('cuts', [])} | {h['timeline'] for h in m.get('lock_history', [])}
mine |= {n for n in ls if re.match(r'^zz (TEST|BUILDING|FAILED) ', n) and R['cut_prefix'] in n} | {n for n in ls if re.fullmatch(re.escape(R['cut_prefix']) + r' v\d+( \(L\))?', n)}
delete = sorted(n for n in mine if n in ls and n not in (keep, final))
res = C.rs('r_cleanup.py', 900, PROJECT=R['project'], KEEP=keep, FINAL=final, DELETE=delete, BACKUP_DIR=f'{trash}/timelines', DRY=DRY)
print(f"Resolve: kept \"{res['kept']}\"; " + (f"would remove {res['would_remove']}" if DRY else f"removed {res['removed']} (backups: {trash}/timelines)"))
# ---- files ----
moves = []      # (from, to)
rev = f"{C.WORK}/review/{m['show']}/{m['ep_key']}"
if os.path.isdir(rev): moves.append((rev, f'{trash}/review'))
for f in sorted(os.listdir(cache)):
    p = f'{cache}/{f}'
    if f == 'manifest.json': continue
    if f == 'locked':
        for d in sorted(os.listdir(p)):
            if os.path.join(p, d) != snap: moves.append((os.path.join(p, d), f'{trash}/cache/locked/{d}'))
        continue
    moves.append((p, f'{trash}/cache/{f}'))
lt_dir = f"{m['dir']}/Lower Thirds"; nas_moves = []
if os.path.isdir(lt_dir):
    used = set()
    for g in json.load(open(f'{snap}/lower_thirds.json'))['guests'].values(): used |= {g['file'], g['png'], g['avatar'], os.path.splitext(g['avatar'])[0] + '.json'}
    vol = '/'.join(m['dir'].split('/')[:3]); rec = f"{vol}/#recycle"
    for f in sorted(os.listdir(lt_dir)):
        p = f'{lt_dir}/{f}'
        if p not in used and not f.startswith('.'): nas_moves.append((p, f"{rec}/CWC_PodCut/{m['ep_key']} {stamp}/{f}") if os.path.isdir(rec) else (p, None))
for a, b in moves: print(f"  {'would trash' if DRY else 'trash'}: {a}")
for a, b in nas_moves: print(f"  {'would recycle' if DRY else 'recycle'} (NAS): {a}" if b else f'  LEFT (the share has no #recycle folder): {a}')
if DRY: print('\ndry run - nothing was changed'); sys.exit(0)
if os.path.isdir(rev):      # the sheets that were looked at stay with the lock
    os.makedirs(f'{snap}/review', exist_ok=True)
    for f in ('layout.jpg', 'reactions_in_cut.jpg'):
        if os.path.exists(f'{rev}/{f}'): shutil.copyfile(f'{rev}/{f}', f'{snap}/review/{f}')
for a, b in moves + [x for x in nas_moves if x[1]]:
    os.makedirs(os.path.dirname(b), exist_ok=True); shutil.move(a, b)
m = C.manifest(cache); m['locked'].update({'timeline': final, 'built_as': keep})
m['cleaned'] = {'at': time.strftime('%Y-%m-%d %H:%M'), 'timelines_removed': res['removed'], 'trash': trash, 'files_moved': len(moves) + len([x for x in nas_moves if x[1]])}
for c in m.get('cuts', []):
    if c['timeline'] in res['removed']: c['removed_at_cleanup'] = True
C.save(f'{cache}/manifest.json', m)
print(f"\nclean: \"{final}\" is the only timeline of this episode left in bin \"{R['bin']}\"; {m['cleaned']['files_moved']} file(s) / folder(s) moved to the Trash ({trash}).")
