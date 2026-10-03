"""Resolve side, READ-ONLY (run via rs.py): the open project, its timelines (resolution, fps, tracks) and bins."""
def info(tl):
    return {'name': tl.GetName(), 'w': tl.GetSetting('timelineResolutionWidth'), 'h': tl.GetSetting('timelineResolutionHeight'), 'fps': tl.GetSetting('timelineFrameRate'),
            'v': tl.GetTrackCount('video'), 'a': tl.GetTrackCount('audio'), 'start': tl.GetStartFrame(), 'end': tl.GetEndFrame(),
            'vnames': [tl.GetTrackName('video', i) for i in range(1, tl.GetTrackCount('video') + 1)], 'anames': [tl.GetTrackName('audio', i) for i in range(1, tl.GetTrackCount('audio') + 1)],
            'items': {f'V{i}': len(tl.GetItemListInTrack('video', i) or []) for i in range(1, tl.GetTrackCount('video') + 1)}}
tls = [project.GetTimelineByIndex(i) for i in range(1, project.GetTimelineCount() + 1)]
want = [t for t in tls if any(k in t.GetName() for k in FILTER)] if FILTER else tls
def walk(f, path=''):
    out = [path + f.GetName()]
    for s in f.GetSubFolderList(): out += walk(s, path + f.GetName() + '/')
    return out
result = {'project': project.GetName(), 'n_timelines': len(tls), 'current': project.GetCurrentTimeline().GetName() if project.GetCurrentTimeline() else None,
          'rendering': project.IsRenderingInProgress(), 'timelines': [info(t) for t in want], 'bins': walk(mp.GetRootFolder())[:80],
          'project_res': [project.GetSetting('timelineResolutionWidth'), project.GetSetting('timelineResolutionHeight'), project.GetSetting('timelineFrameRate')]}
