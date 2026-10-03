"""Resolve side (run via rs.py; NAME, OUT, CN, W, H [, PRESET] [, FRAME]): one Deliver job of a whole timeline -> OUT/CN.mp4;
with FRAME=n: that ONE timeline frame as a 16-bit TIFF -> OUT/CN*.tif (a cover; Resolve's PNG stills came out posterized
in edit-shorts, 2026-09-12).
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
    os.makedirs(OUT, exist_ok=True); pat = os.path.join(OUT, glob.escape(CN) + ('*.tif' if globals().get('FRAME') is not None else '.*'))   # a still gets a frame number in its name
    for old in glob.glob(pat): os.rename(old, old + '.old')
    if globals().get('FRAME') is not None:
        codecs = project.GetRenderCodecs('tif') or {}
        codec = next((v for v in codecs.values() if '16' in str(v)), None) or next(iter(codecs.values()), 'RGB16LZW')
        project.SetCurrentRenderFormatAndCodec('tif', codec); st0 = tl.GetStartFrame()
        ok = project.SetRenderSettings({'SelectAllFrames': False, 'MarkIn': st0 + FRAME, 'MarkOut': st0 + FRAME, 'TargetDir': OUT, 'CustomName': CN, 'ExportVideo': True, 'ExportAudio': False, 'FormatWidth': W, 'FormatHeight': H})
    else:
        codecs = project.GetRenderCodecs('mp4') or {}
        codec = next((v for v in codecs.values() if str(v).lower().replace('.', '') == 'h264'), None) or next(iter(codecs.values()), 'H264')
        project.LoadRenderPreset(globals().get('PRESET') or 'H.264 Master'); project.SetCurrentRenderFormatAndCodec('mp4', codec)
        ok = project.SetRenderSettings({'SelectAllFrames': True, 'TargetDir': OUT, 'CustomName': CN, 'ExportVideo': True, 'ExportAudio': True, 'FormatWidth': W, 'FormatHeight': H})
    jid = project.AddRenderJob(); t0 = time.time(); project.StartRendering([jid], isInteractiveMode=False)
    while project.IsRenderingInProgress() and time.time() - t0 < LIMIT: time.sleep(1)
    st = project.GetRenderJobStatus(jid) or {}; project.DeleteRenderJob(jid)
    made = sorted([f for f in glob.glob(pat) if not f.endswith('.old')], key=os.path.getmtime)
    result = {'status': st, 'settings_ok': ok, 'codec': codec, 'made': made[-1] if made else None, 'secs': round(time.time() - t0)}
