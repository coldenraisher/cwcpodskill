"""Resolve side (run via rs.py; NAME, OUT, CN, W, H [, PRESET]): one Deliver job of a whole timeline -> OUT/CN.mp4.
The AMIRA recipe (proven 2026-09-30): no page switch, no Quick Export; refuses while another render runs; the job is
removed from the queue afterwards. Nothing on the timeline is touched."""
import time, glob, os
if project.IsRenderingInProgress(): result = {'error': 'a render is already in progress in Resolve'}
else:
    tl = next((project.GetTimelineByIndex(i) for i in range(1, project.GetTimelineCount() + 1) if project.GetTimelineByIndex(i).GetName() == NAME), None)
    assert tl, f'timeline {NAME!r} not found'
    project.SetCurrentTimeline(tl)
    for _ in range(80):
        if project.GetCurrentTimeline().GetName() == NAME: break
        time.sleep(0.1)
    os.makedirs(OUT, exist_ok=True)
    for old in glob.glob(os.path.join(OUT, glob.escape(CN) + '.*')): os.rename(old, old + '.old')
    codecs = project.GetRenderCodecs('mp4') or {}
    codec = next((v for v in codecs.values() if str(v).lower().replace('.', '') == 'h264'), None) or next(iter(codecs.values()), 'H264')
    preset = globals().get('PRESET') or 'H.264 Master'
    assert any((x.get('RenderPresetName') if isinstance(x, dict) else str(x)) == preset for x in (project.GetRenderPresetList() or [])), f'the render preset {preset!r} is not in this Resolve - nothing rendered (a silent fallback would render with whatever was loaded last)'
    project.LoadRenderPreset(preset); project.SetCurrentRenderFormatAndCodec('mp4', codec)
    ok = project.SetRenderSettings({'SelectAllFrames': True, 'TargetDir': OUT, 'CustomName': CN, 'ExportVideo': True, 'ExportAudio': True, 'FormatWidth': W, 'FormatHeight': H})
    jid = project.AddRenderJob(); t0 = time.time(); project.StartRendering([jid], isInteractiveMode=False)
    while project.IsRenderingInProgress() and time.time() - t0 < LIMIT: time.sleep(1)
    st = project.GetRenderJobStatus(jid) or {}; project.DeleteRenderJob(jid)
    made = sorted([f for f in glob.glob(os.path.join(OUT, glob.escape(CN) + '.*')) if not f.endswith('.old')], key=os.path.getmtime)
    result = {'status': st, 'settings_ok': ok, 'codec': codec, 'made': made[-1] if made else None, 'secs': round(time.time() - t0)}
