"""Resolve side: dump a timeline's items to OUT (json). globals: NAME, OUT. Read-only."""
import json
tl = next((project.GetTimelineByIndex(i) for i in range(1, project.GetTimelineCount() + 1) if project.GetTimelineByIndex(i).GetName() == NAME), None)
assert tl, f'no timeline {NAME!r}'
ST = tl.GetStartFrame(); d = {'name': NAME, 'fps': float(tl.GetSetting('timelineFrameRate')), 'start': ST, 'frames': tl.GetEndFrame() - ST, 'tracks': {}, 'markers': tl.GetMarkers() or {}}
for kind in ('video', 'audio'):
    for i in range(1, tl.GetTrackCount(kind) + 1):
        rows = []
        for it in tl.GetItemListInTrack(kind, i) or []:
            mpi = it.GetMediaPoolItem()
            rows.append([it.GetStart() - ST, it.GetEnd() - ST, it.GetSourceStartFrame(), it.GetSourceEndFrame(), bool(it.GetClipEnabled()), mpi.GetName() if mpi else None])
        d['tracks'][f'{kind[0].upper()}{i}'] = {'name': tl.GetTrackName(kind, i), 'enabled': bool(tl.GetIsTrackEnabled(kind, i)), 'items': rows}
json.dump(d, open(OUT, 'w'))
result = {'name': NAME, 'frames': d['frames'], 'items': {k: len(v['items']) for k, v in d['tracks'].items()}, 'out': OUT}
