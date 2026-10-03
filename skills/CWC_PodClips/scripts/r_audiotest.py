"""Resolve side (run via rs.py; TEMPLATE, NAME, CLIP, SRC_IN, FRAMES, OUT): does the template's A1 strip reach a clip?
A duplicate of the template named `zz TEST ...` with ONE program-audio piece on A1 (and the same piece's picture on V1),
rendered small. The file's sound is then compared with the raw source outside Resolve. The test timeline is left in
place (nothing is deleted before the lock cleanup); the current timeline is restored."""
import time, glob, os
def tls(): return {project.GetTimelineByIndex(i).GetName(): project.GetTimelineByIndex(i) for i in range(1, project.GetTimelineCount() + 1)}
def find(f, name):
    for c in f.GetClipList():
        if c.GetName() == name: return c
    for s in f.GetSubFolderList():
        r = find(s, name)
        if r: return r
assert not project.IsRenderingInProgress(), 'a render is in progress'
T = tls(); assert NAME not in T, f'{NAME} exists'; tpl = T[TEMPLATE]; cur = project.GetCurrentTimeline().GetName()
project.SetCurrentTimeline(tpl); tl = tpl.DuplicateTimeline(NAME); assert tl
project.SetCurrentTimeline(tl)
for _ in range(80):
    if project.GetCurrentTimeline().GetName() == NAME: break
    time.sleep(0.1)
if ADD_TRACKS:
    for n in ('Jake', 'Nick', 'Colden'): assert tl.AddTrack('audio', 'stereo')
mpi = find(mp.GetRootFolder(), CLIP); ST = tl.GetStartFrame()
made = mp.AppendToTimeline([{'mediaPoolItem': mpi, 'startFrame': SRC_IN, 'endFrame': SRC_IN + FRAMES, 'mediaType': 2, 'trackIndex': 1, 'recordFrame': ST},
                            {'mediaPoolItem': mpi, 'startFrame': SRC_IN, 'endFrame': SRC_IN + FRAMES, 'mediaType': 1, 'trackIndex': 1, 'recordFrame': ST}]) or []
assert len(made) == 2, f'placed {len(made)}'
os.makedirs(OUT, exist_ok=True)
codecs = project.GetRenderCodecs('mp4') or {}; codec = next((v for v in codecs.values() if str(v).lower().replace('.', '') == 'h264'), None) or next(iter(codecs.values()), 'H264')
project.LoadRenderPreset('H.264 Master'); project.SetCurrentRenderFormatAndCodec('mp4', codec)
project.SetRenderSettings({'SelectAllFrames': True, 'TargetDir': OUT, 'CustomName': NAME, 'ExportVideo': True, 'ExportAudio': True, 'FormatWidth': 640, 'FormatHeight': 360})
jid = project.AddRenderJob(); t0 = time.time(); project.StartRendering([jid], isInteractiveMode=False)
while project.IsRenderingInProgress() and time.time() - t0 < 300: time.sleep(0.5)
st = project.GetRenderJobStatus(jid); project.DeleteRenderJob(jid)
made_f = sorted(glob.glob(os.path.join(OUT, glob.escape(NAME) + '.*')), key=os.path.getmtime)
if cur in tls(): project.SetCurrentTimeline(tls()[cur])
pm.SaveProject()
result = {'status': st, 'file': made_f[-1] if made_f else None, 'audio_tracks': [tl.GetTrackName('audio', i) for i in range(1, tl.GetTrackCount('audio') + 1)], 'restored': project.GetCurrentTimeline().GetName()}
