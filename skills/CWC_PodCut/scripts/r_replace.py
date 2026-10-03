"""Resolve side: point a media-pool clip at a new file (globals BIN, OLD, NEW). Every timeline item made from the clip
follows; nothing on any timeline is moved, deleted or trimmed. Refuses when the new file's length differs."""
b = mp.GetRootFolder()
for part in BIN.split('/'):
    b = next((x for x in b.GetSubFolderList() if x.GetName() == part), None); assert b, f'bin {part!r} not found'
clip = next((c for c in b.GetClipList() if c.GetClipProperty('File Path') == OLD), None)
if not clip:
    assert any(c.GetClipProperty('File Path') == NEW for c in b.GetClipList()), f'neither {OLD} nor {NEW} is in bin {BIN}'
    result = {'replaced': False, 'already': True}
else:
    frames = clip.GetClipProperty('Frames'); ok = clip.ReplaceClip(NEW); assert ok, 'ReplaceClip failed'
    assert clip.GetClipProperty('Frames') == frames, f"length changed: {frames} -> {clip.GetClipProperty('Frames')}"
    pm.SaveProject(); result = {'replaced': True, 'now': clip.GetClipProperty('File Path'), 'name': clip.GetName()}
