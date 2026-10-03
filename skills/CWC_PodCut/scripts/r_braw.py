"""Resolve side of braw_convert.py. STEP='start': import BRAW, one-clip timeline, LUT on node 1, queue + start the
render (globals BRAW, LUT, PRESET, TARGET, NAME). STEP='wait': render status (global JOB)."""
import os
if STEP == 'start':
    assert not project.IsRenderingInProgress(), 'a render is in progress'
    root = mp.GetRootFolder(); b = next((x for x in root.GetSubFolderList() if x.GetName() == 'BRAW convert'), None) or mp.AddSubFolder(root, 'BRAW convert')
    mp.SetCurrentFolder(b); clip = (mp.ImportMedia([BRAW]) or [None])[0]; assert clip, f'import failed: {BRAW}'
    tname = f'zz BRAW convert {NAME} {os.path.basename(os.path.dirname(TARGET))}'
    tl = mp.CreateTimelineFromClips(tname, [clip]); assert tl, 'CreateTimelineFromClips failed (a timeline of that name exists?)'
    project.SetCurrentTimeline(tl); it = tl.GetItemListInTrack('video', 1)[0]
    assert it.SetLUT(1, LUT), f'SetLUT failed for {LUT}'
    assert project.LoadRenderPreset(PRESET), f'render preset {PRESET!r} not found'
    fps = float(clip.GetClipProperty('FPS')); frames = int(clip.GetClipProperty('Frames'))
    project.SetRenderSettings({'SelectAllFrames': True, 'TargetDir': TARGET, 'CustomName': NAME, 'UniqueFilenameStyle': 0})
    job = project.AddRenderJob(); assert job, 'AddRenderJob failed'; project.StartRendering([job], isInteractiveMode=False)
    result = {'job': job, 'timeline': tname, 'seconds': frames / fps, 'fps': fps, 'resolution': clip.GetClipProperty('Resolution')}
else:
    st = project.GetRenderJobStatus(JOB) or {}
    result = {'rendering': bool(project.IsRenderingInProgress()), 'status': st.get('JobStatus'), 'pct': st.get('CompletionPercentage')}
