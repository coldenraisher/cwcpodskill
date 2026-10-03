"""Resolve side: place the guest lower thirds on the cut (run via rs.py; globals POD, BIN, TRACK, TAGS).
  TAGS  [{file, outFrame, frames, who, where}] from lower_thirds.json;  TRACK = the first video track above the cameras
The track is added when missing and named 'Lower Thirds'; the .mov files are imported once into BIN/Lower Thirds.
Refuses when the track already holds clips (our own overlays are never re-placed over existing ones). ProRes 4444
files only - no Fusion titles, no handles held."""
tl = next((project.GetTimelineByIndex(i) for i in range(1, project.GetTimelineCount() + 1) if project.GetTimelineByIndex(i).GetName() == POD), None)
assert tl, f'no timeline {POD!r}'
project.SetCurrentTimeline(tl); ST = tl.GetStartFrame()
while tl.GetTrackCount('video') < TRACK: tl.AddTrack('video')
assert not (tl.GetItemListInTrack('video', TRACK) or []), f'V{TRACK} of {POD} already has clips - not placing lower thirds over them'
tl.SetTrackName('video', TRACK, 'Lower Thirds')
b = mp.GetRootFolder()
for part in (BIN + '/Lower Thirds').split('/'):
    b = next((x for x in b.GetSubFolderList() if x.GetName() == part), None) or mp.AddSubFolder(b, part); assert b, f'bin {part!r}'
have = {c.GetClipProperty('File Path'): c for c in b.GetClipList()}; mp.SetCurrentFolder(b)
for f in sorted({t['file'] for t in TAGS}):
    if f not in have:
        got = mp.ImportMedia([f]) or []; assert got, f'import failed: {f}'; have[f] = got[0]
made = []
for t in TAGS:
    cur = project.GetCurrentTimeline(); assert cur and cur.GetName() == POD, f'the current timeline is not {POD!r} any more - stopped'
    got = mp.AppendToTimeline([{'mediaPoolItem': have[t['file']], 'startFrame': 0, 'endFrame': t['frames'], 'mediaType': 1, 'trackIndex': TRACK, 'recordFrame': ST + t['outFrame']}]) or []
    assert got, f"lower third for {t['who']} ({t['where']}) was not placed"
    made.append([got[0].GetStart() - ST, got[0].GetDuration()])
pm.SaveProject(); result = {'track': TRACK, 'placed': made}
