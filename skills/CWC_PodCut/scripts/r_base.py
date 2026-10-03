"""Resolve side: build the synced BASE timeline (run via rs.py; globals: BIN, NAME, CAMS, EXTRA, FPS, DUR).
  BIN   media-pool bin path ('Ep. 24 - 10:1'), created when missing; every camera file is imported into it once
  NAME  'Ep 24 BASE' - refused when it exists (a timeline is never replaced)
  CAMS  manifest cameras: [{id, role, name, path, track, off, rate, fps, duration}]   track 1 = the program
  EXTRA other files to import into BIN/Shares (screen recordings, the intro) - imported, not placed
Layout (the PodCut structure edit-shorts / edit-clips read): V1/A1 program at 0, V<k>/A<k> one camera per person,
placed at round(off * fps). A1 (program mix) is the sound; every ISO audio CLIP is disabled, its track left enabled.
A camera whose clock drifts more than a frame over the show (manifest rate != 1) is laid as adjacent pieces, each
re-anchored - the track still tiles the whole span (non-destructive: nothing is trimmed away, a piece is not "the part
we keep"). result: {'placed': {track: [[tlStart, tlEnd, srcStart, srcEnd], ...]}, ...}"""
import os, math
tls = {project.GetTimelineByIndex(i).GetName(): project.GetTimelineByIndex(i) for i in range(1, project.GetTimelineCount() + 1)}
assert NAME not in tls, f'{NAME} already exists - not replacing it'
pfps = float(project.GetSetting('timelineFrameRate')); assert abs(pfps - FPS) < 0.01, f'project timeline rate {pfps} != program {FPS}: the base cannot be built in this project without Colden'
root = mp.GetRootFolder()
def sub(f, n): return next((x for x in f.GetSubFolderList() if x.GetName() == n), None) or mp.AddSubFolder(f, n)
b = root
for part in BIN.split('/'):
    b = sub(b, part); assert b, f'could not create bin {part!r} (Resolve refuses some characters, e.g. a colon)'
def by_path(folder): return {c.GetClipProperty('File Path'): c for c in folder.GetClipList() if c.GetClipProperty('File Path')}
have = by_path(b); mp.SetCurrentFolder(b)
for c in CAMS:
    if c['path'] not in have:
        got = mp.ImportMedia([c['path']]) or []; assert got, f"import failed: {c['path']}"
        have[c['path']] = got[0]
if EXTRA:
    sb = sub(b, 'Shares'); hv = by_path(sb); mp.SetCurrentFolder(sb)
    todo = [p for p in EXTRA if p not in hv]
    if todo: mp.ImportMedia(todo)
mp.SetCurrentFolder(b)
tl = mp.CreateEmptyTimeline(NAME); assert tl, 'CreateEmptyTimeline failed'
project.SetCurrentTimeline(tl); ST = tl.GetStartFrame(); ntr = max(c['track'] for c in CAMS)
while tl.GetTrackCount('video') < ntr: tl.AddTrack('video')
while tl.GetTrackCount('audio') < ntr: tl.AddTrack('audio', 'stereo')
END = int(round(DUR * FPS)); log = {'fps': pfps, 'start': ST, 'frames': END, 'placed': {}, 'pieces': {}}
for c in sorted(CAMS, key=lambda c: c['track']):
    clip = have[c['path']]; tr = c['track']; label = 'Program' if c['role'] == 'wide' else c['name']
    tl.SetTrackName('video', tr, label); tl.SetTrackName('audio', tr, label)
    cf = float(clip.GetClipProperty('FPS') or c['fps']); total = int(clip.GetClipProperty('Frames') or 0)
    off, rate = c.get('off', 0.0), c.get('rate', 1.0)
    b0 = max(0.0, off); b1 = min(DUR, c['duration'] / rate + off)                       # base seconds this camera covers
    drift = abs(rate - 1.0) * (b1 - b0) * FPS; n = 1 if drift <= 1.0 else int(math.ceil(drift)) + 1
    rec = int(round(b0 * FPS)); last = int(round(b1 * FPS)); made_v = []; made_a = []
    for k in range(n):
        r1 = last if k == n - 1 else int(round((b0 + (b1 - b0) * (k + 1) / n) * FPS))
        s0 = int(round((rec / FPS - off) * rate * cf)); s1 = min(total, s0 + int(round((r1 - rec) / FPS * rate * cf)))   # source frames, the clip's own rate
        if s1 <= s0: break
        for mt, bag in ((1, made_v), (2, made_a)):
            got = mp.AppendToTimeline([{'mediaPoolItem': clip, 'startFrame': s0, 'endFrame': s1, 'mediaType': mt, 'trackIndex': tr, 'recordFrame': ST + rec}]) or []
            assert got, f"{c['name']}: AppendToTimeline failed (track {tr}, piece {k}, record {rec})"
            bag.append(got[0])
        rec = made_v[-1].GetEnd() - ST                                                   # the next piece starts where this one really ended
    if tr != 1:
        for it in made_a: it.SetClipEnabled(False)
    log['placed'][f'V{tr}'] = [[it.GetStart() - ST, it.GetEnd() - ST, it.GetSourceStartFrame(), it.GetSourceEndFrame()] for it in made_v]
    log['pieces'][c['name']] = n
pm.SaveProject(); result = log
