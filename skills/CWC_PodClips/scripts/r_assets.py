"""Resolve side, READ-ONLY (run via rs.py; NAMES, POD, TEMPLATE): where the fixed assets are in the media pool, the
PodCut's camera clips per track, and whether the template is still empty."""
def find(f, name, path=''):
    for c in f.GetClipList():
        if c.GetName() == name: return c, path + f.GetName()
    for s in f.GetSubFolderList():
        r = find(s, name, path + f.GetName() + '/')
        if r: return r
root = mp.GetRootFolder(); out = {}
for n in NAMES:
    r = find(root, n)
    out[n] = None if not r else {'bin': r[1], 'fps': r[0].GetClipProperty('FPS'), 'frames': r[0].GetClipProperty('Frames'), 'res': r[0].GetClipProperty('Resolution'), 'path': r[0].GetClipProperty('File Path')}
tls = {project.GetTimelineByIndex(i).GetName(): project.GetTimelineByIndex(i) for i in range(1, project.GetTimelineCount() + 1)}
pod = tls.get(POD); cams = {}
if pod:
    for k in ('video', 'audio'):
        for i in range(1, pod.GetTrackCount(k) + 1):
            its = pod.GetItemListInTrack(k, i) or []; names = {}
            for it in its[:3] + its[-2:]:
                m = it.GetMediaPoolItem()
                if m: names[m.GetName()] = [m.GetClipProperty('FPS'), m.GetClipProperty('Resolution'), m.GetClipProperty('Frames')]
            first = its[0] if its else None
            cams[f'{k[0].upper()}{i}'] = {'name': pod.GetTrackName(k, i), 'items': len(its), 'clips': names, 'first': [first.GetStart() - pod.GetStartFrame(), first.GetDuration(), first.GetSourceStartFrame(), first.GetSourceEndFrame(), first.GetClipEnabled()] if first else None}
tp = tls.get(TEMPLATE); tinfo = None
if tp:
    tinfo = {'empty': all(not (tp.GetItemListInTrack(k, i) or []) for k in ('video', 'audio') for i in range(1, tp.GetTrackCount(k) + 1)),
             'video': [tp.GetTrackName('video', i) for i in range(1, tp.GetTrackCount('video') + 1)], 'audio': [tp.GetTrackName('audio', i) for i in range(1, tp.GetTrackCount('audio') + 1)]}
result = {'project': project.GetName(), 'current': project.GetCurrentTimeline().GetName(), 'assets': out, 'pod': {'start': pod.GetStartFrame() if pod else None, 'tracks': cams}, 'template': tinfo, 'rendering': project.IsRenderingInProgress()}
