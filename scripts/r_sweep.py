"""Resolve side of cleanup.py (run through rs.py only; globals STEP, BIN, DELETE_TL, DELETE_MEDIA, BACKUP_DIR, SOURCES).
  STEP='list'   READ-ONLY. Every timeline and pool clip under the episode bin (sub-bins too), the file of every clip, the
                files each timeline of the bin uses (every track item's media pool item -> File Path), and the files ANY
                timeline of the project uses.
  STEP='apply'  DELETE_TL: each timeline is exported as a .drt into BACKUP_DIR first and removed only when that file exists
                and is not empty; never a name ending "(L)" (locked) or starting "00 " (a template). DELETE_MEDIA: pool
                clips by File Path, refused when any timeline of the project still uses the file or it is in SOURCES.
NOT yet run against a real project (2026-10-03): the first apply runs with Colden present, after a list he has read."""
import os, re

def find_bin(folder, name):
    if folder.GetName() == name: return folder
    for f in folder.GetSubFolderList() or []:
        hit = find_bin(f, name)
        if hit: return hit
    return None

def walk(folder, path=''):
    p = f'{path}/{folder.GetName()}'
    for c in folder.GetClipList() or []: yield p, c
    for f in folder.GetSubFolderList() or []: yield from walk(f, p)

def used(tl):
    out = set()
    for kind in ('video', 'audio', 'subtitle'):
        for n in range(1, (tl.GetTrackCount(kind) or 0) + 1):
            for it in tl.GetItemListInTrack(kind, n) or []:
                mpi = it.GetMediaPoolItem()
                fp = mpi.GetClipProperty('File Path') if mpi else None
                if fp: out.add(fp)
    return out

b = find_bin(mp.GetRootFolder(), BIN)
assert b, f'bin {BIN!r} not found in project {project.GetName()!r}'
tls = {}
for i in range(1, project.GetTimelineCount() + 1):
    t = project.GetTimelineByIndex(i)
    if t: tls[t.GetName()] = t
items = list(walk(b))
in_bin = [(p, c) for p, c in items if c.GetClipProperty('Type') == 'Timeline']
used_any = set()
for t in tls.values(): used_any |= used(t)

if STEP == 'list':
    tl_rows = []
    for p, c in in_bin:
        name = c.GetName(); t = tls.get(name)
        tl_rows.append({'name': name, 'bin': p, 'locked': name.endswith('(L)'), 'template': name.startswith('00 '), 'uses': sorted(used(t)) if t else []})
    media = [{'name': c.GetName(), 'bin': p, 'path': c.GetClipProperty('File Path'), 'used': c.GetClipProperty('File Path') in used_any}
             for p, c in items if c.GetClipProperty('Type') != 'Timeline']
    result = {'project': project.GetName(), 'bin': BIN, 'timelines': tl_rows, 'media': media, 'used_any': sorted(used_any)}
elif STEP == 'apply':
    out = {'removed_timelines': [], 'removed_media': [], 'problems': []}
    names = {c.GetName() for _, c in in_bin}
    gone = [n for n in DELETE_TL if n in names and n in tls and not n.endswith('(L)') and not n.startswith('00 ')]
    cur = project.GetCurrentTimeline()
    if cur and cur.GetName() in gone:
        keep = [t for n, t in tls.items() if n not in gone]
        if keep: project.SetCurrentTimeline(keep[0])
    os.makedirs(BACKUP_DIR, exist_ok=True)
    for n in gone:
        f = os.path.join(BACKUP_DIR, re.sub(r'[\\/:*?"<>|]', '-', n) + '.drt')
        ok = tls[n].Export(f, resolve.EXPORT_DRT, resolve.EXPORT_NONE)
        if not ok or not os.path.exists(f) or os.path.getsize(f) == 0: out['problems'].append(f'no .drt backup for {n!r} - kept'); continue
        if mp.DeleteTimelines([tls[n]]): out['removed_timelines'].append(n)
        else: out['problems'].append(f'DeleteTimelines failed for {n!r}')
    used_any = set()
    for i in range(1, project.GetTimelineCount() + 1):
        t = project.GetTimelineByIndex(i)
        if t: used_any |= used(t)
    drop = [c for _, c in walk(b) if c.GetClipProperty('Type') != 'Timeline' and c.GetClipProperty('File Path') in set(DELETE_MEDIA)
            and c.GetClipProperty('File Path') not in used_any and c.GetClipProperty('File Path') not in set(SOURCES)]
    if drop:
        names = [c.GetClipProperty('File Path') for c in drop]
        if mp.DeleteClips(drop): out['removed_media'] = names
        else: out['problems'].append('DeleteClips failed')
    result = out
else:
    raise AssertionError(f'unknown STEP {STEP!r}')
