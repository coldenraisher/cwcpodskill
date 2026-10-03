"""Resolve side of cleanup.py (globals KEEP, FINAL, DELETE, BACKUP_DIR, DRY).
Leaves ONE timeline of this episode: the locked cut, renamed FINAL ('<cut> (L)'). Every other timeline named in DELETE
(the base, earlier versions, trial / failed builds - only names this skill recorded or its own 'zz ...' names) is first
EXPORTED as a .drt into BACKUP_DIR (a folder in the Trash) and only then removed from the project - a removed timeline can
be brought back with File > Import > Timeline from that file. Gates: the kept timeline carries the green LOCKED marker;
a timeline is removed only after its .drt exists and is not empty; the kept one is never in DELETE."""
import os, re
tls = {}
for i in range(1, project.GetTimelineCount() + 1):
    t = project.GetTimelineByIndex(i)
    if t: tls[t.GetName()] = t
keep = tls.get(KEEP) or tls.get(FINAL); assert keep, f'neither {KEEP!r} nor {FINAL!r} is in the project'
assert any(mk.get('name') == 'LOCKED' for mk in (keep.GetMarkers() or {}).values()), f'{keep.GetName()} carries no LOCKED marker - nothing is cleaned up around an unlocked cut'
assert KEEP not in DELETE and FINAL not in DELETE, 'the locked cut is in the delete list'
out = {'kept': None, 'removed': [], 'not_found': [], 'would_remove': [], 'backups': BACKUP_DIR}
project.SetCurrentTimeline(keep)
for n in DELETE:
    t = tls.get(n)
    if not t: out['not_found'].append(n); continue
    if DRY: out['would_remove'].append(n); continue
    os.makedirs(BACKUP_DIR, exist_ok=True); f = os.path.join(BACKUP_DIR, re.sub(r'[\\/:*?"<>|]', '-', n) + '.drt')
    ok = t.Export(f, resolve.EXPORT_DRT, resolve.EXPORT_NONE)
    assert ok and os.path.exists(f) and os.path.getsize(f) > 0, f'could not back up {n!r} to {f} - it is NOT removed'
    assert mp.DeleteTimelines([t]), f'DeleteTimelines failed for {n!r}'
    out['removed'].append(n)
if not DRY and keep.GetName() != FINAL:
    assert FINAL not in tls, f'{FINAL!r} already exists'
    assert keep.SetName(FINAL), f'could not rename {keep.GetName()!r}'
out['kept'] = keep.GetName()
if not DRY: pm.SaveProject()
result = out
