"""READ-ONLY survey of the open Resolve project for CWC_PodReels (run via rs.py): project, current timeline, the
templates, the episode bin's subfolders, render presets. Changes nothing (never switches the current timeline)."""
def walk(f, path='', depth=0, out=None):
    out = out if out is not None else []
    for s in f.GetSubFolderList():
        p = path + '/' + s.GetName(); out.append([p, len(s.GetClipList())])
        if depth < 3: walk(s, p, depth + 1, out)
    return out
tl = project.GetCurrentTimeline()
tls = [project.GetTimelineByIndex(i) for i in range(1, project.GetTimelineCount() + 1)]
info = {}
for t in tls:
    n = t.GetName()
    if n.startswith('00 ') or 'Template' in n:
        info[n] = {'res': [t.GetSetting('timelineResolutionWidth'), t.GetSetting('timelineResolutionHeight')], 'fps': t.GetSetting('timelineFrameRate'),
                   'v': [t.GetTrackName('video', i) for i in range(1, t.GetTrackCount('video') + 1)], 'a': [t.GetTrackName('audio', i) for i in range(1, t.GetTrackCount('audio') + 1)],
                   'items': sum(len(t.GetItemListInTrack(k, i) or []) for k in ('video', 'audio') for i in range(1, t.GetTrackCount(k) + 1))}
result = {'project': project.GetName(), 'current_timeline': tl.GetName() if tl else None, 'timelines': len(tls), 'templates': info,
          'ep24': [t.GetName() for t in tls if t.GetName().startswith('Ep 24')], 'bins': [b for b in walk(mp.GetRootFolder()) if 'Ep. 24' in b[0] or 'Shorts' in b[0] or b[0].count('/') == 1][:60],
          'presets': [p for p in (project.GetRenderPresetList() or [])], 'rendering': project.IsRenderingInProgress(), 'page': resolve.GetCurrentPage()}
