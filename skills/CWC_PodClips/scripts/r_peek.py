"""Resolve side, READ-ONLY: the items of some tracks of one timeline (NAME, TRACKS=[["video", 7], ...]); optional POD + AT frames to compare a PodCut item's source start."""
tls = {project.GetTimelineByIndex(i).GetName(): project.GetTimelineByIndex(i) for i in range(1, project.GetTimelineCount() + 1)}
tl = tls[NAME]; ST = tl.GetStartFrame(); out = {}
for k, i in TRACKS:
    out[f'{k}{i}'] = [[it.GetName(), it.GetStart() - ST, it.GetDuration(), it.GetSourceStartFrame(), it.GetSourceEndFrame(), bool(it.GetClipEnabled()), (it.GetMediaPoolItem().GetName() if it.GetMediaPoolItem() else None)] for it in (tl.GetItemListInTrack(k, i) or [])][:LIMIT]
result = {'name': NAME, 'frames': tl.GetEndFrame() - ST, 'tracks': out}
if globals().get('POD'):
    pod = tls[POD]; PS = pod.GetStartFrame(); rows = []
    for k, i, f in AT:
        for it in pod.GetItemListInTrack(k, i) or []:
            if it.GetStart() - PS <= f < it.GetEnd() - PS: rows.append([k, i, f, it.GetStart() - PS, it.GetDuration(), it.GetSourceStartFrame(), it.GetSourceEndFrame()]); break
    result['pod'] = rows
