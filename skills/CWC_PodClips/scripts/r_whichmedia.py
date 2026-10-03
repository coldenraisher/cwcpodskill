"""Resolve side, READ-ONLY: every media-pool clip with one of NAMES (bin + file path), and the file paths the camera
tracks of timeline NAME and of the PodCut POD really use."""
def walk(f, path=''):
    out = []
    for c in f.GetClipList():
        if c.GetName() in NAMES: out.append([c.GetName(), path + f.GetName(), c.GetClipProperty('File Path')])
    for s in f.GetSubFolderList(): out += walk(s, path + f.GetName() + '/')
    return out
tls = {project.GetTimelineByIndex(i).GetName(): project.GetTimelineByIndex(i) for i in range(1, project.GetTimelineCount() + 1)}
def used(tl, n):
    out = {}
    for i in range(1, n + 1):
        paths = {}
        for it in tl.GetItemListInTrack('video', i) or []:
            m = it.GetMediaPoolItem()
            if m: p = m.GetClipProperty('File Path'); paths[p] = paths.get(p, 0) + 1
        out[f'V{i} {tl.GetTrackName("video", i)}'] = paths
    return out
result = {'pool': walk(mp.GetRootFolder()), 'clip': used(tls[NAME], 4), 'podcut': used(tls[POD], 4)}
