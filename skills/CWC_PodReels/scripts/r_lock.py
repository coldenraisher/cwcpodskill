"""Resolve side of lock.py (CWC_PodReels; copied from CWC_PodClips r_lock.py 2026-10-02) (run via rs.py; globals STEP, LOCK, DELETE, RELOCKED, BROLL_BIN, KEEP_BROLL, BACKUP_DIR).
  STEP='lock'     every timeline in LOCK ({name: final}) gets a green LOCKED marker (custom data cwc-podreels-lock), its
                  red DRAFT marker is removed, and it is renamed to its final '<name> (L)'. Removes nothing else.
  STEP='cleanup'  (Colden 2026-10-02: "clean up should be automatic. Anything that the timeline or final output does not
                  rely on can be trashed") every timeline in DELETE - only names this skill recorded (versions.json) or
                  its own 'zz BUILDING' names - is first EXPORTED as a .drt into BACKUP_DIR (a folder in
                  the Trash) and only then removed; b-roll clips in BROLL_BIN that no locked timeline uses leave the pool.
Gates: a timeline is removed only after its .drt exists and is not empty; a LOCKED timeline is never removed; the
current timeline is moved to a locked one first."""
import os, re
def tls():
    out = {}
    for i in range(1, project.GetTimelineCount() + 1):
        t = project.GetTimelineByIndex(i)
        if t: out[t.GetName()] = t
    return out
locked = lambda t: any(mk.get('name') == 'LOCKED' for mk in (t.GetMarkers() or {}).values())
out = {'step': STEP, 'problems': []}
if STEP == 'lock':
    T = tls(); out['locked'] = []
    for name, final in LOCK.items():
        t = T.get(name) or T.get(final)
        if not t: out['problems'].append(f'{name!r} is not in the project'); continue
        for _ in range(5):                                                    # the red DRAFT marker (exact custom data)
            if not t.DeleteMarkerByCustomData('cwc-podreels'): break
        if not locked(t): assert t.AddMarker(0, 'Green', 'LOCKED', 'CWC_PodReels: approved, mastered, locked', 1, 'cwc-podreels-lock'), f'LOCKED marker on {name!r}'
        if t.GetName() != final:
            assert final not in T, f'{final!r} already exists'
            assert t.SetName(final), f'rename {name!r}'
        out['locked'].append(t.GetName())
elif STEP == 'cleanup':
    T = tls(); keep = [t for t in T.values() if locked(t) and t.GetName().endswith(' (L)') and t.GetName() not in RELOCKED]
    assert keep, 'no locked timeline in the project - nothing is cleaned up around an unlocked set'
    cur = project.GetCurrentTimeline()
    if cur and cur.GetName() in DELETE: project.SetCurrentTimeline(keep[0])
    out.update({'removed': [], 'not_found': []})
    for n in DELETE:
        t = T.get(n)
        if not t: out['not_found'].append(n); continue
        if locked(t) and n not in RELOCKED: out['problems'].append(f'{n!r} carries a LOCKED marker - kept'); continue      # RELOCKED: replaced by a newer locked version (lock.py decides)
        os.makedirs(BACKUP_DIR, exist_ok=True); f = os.path.join(BACKUP_DIR, re.sub(r'[\\/:*?"<>|]', '-', n) + '.drt')
        ok = t.Export(f, resolve.EXPORT_DRT, resolve.EXPORT_NONE)
        if not (ok and os.path.exists(f) and os.path.getsize(f) > 0): out['problems'].append(f'could not back up {n!r} - NOT removed'); continue
        assert mp.DeleteTimelines([t]), f'DeleteTimelines failed for {n!r}'
        out['removed'].append(n)
    b = mp.GetRootFolder()
    for part in BROLL_BIN.split('/'):
        if part == b.GetName(): continue
        b = next((x for x in b.GetSubFolderList() if x.GetName() == part), None)
        if b is None: break
    out['broll_removed'] = []
    if b is not None:
        gone = [c for c in b.GetClipList() if c.GetClipProperty('File Path') not in KEEP_BROLL]
        if gone:
            names = [c.GetName() for c in gone]
            if mp.DeleteClips(gone): out['broll_removed'] = names
            else: out['problems'].append(f'could not remove unused b-roll clips {names}')
pm.SaveProject(); result = out
