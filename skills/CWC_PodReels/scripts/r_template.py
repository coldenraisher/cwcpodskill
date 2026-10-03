"""Resolve side (run via rs.py; PROJECT, NAME, SOURCE): make the ONE vertical template every short is a duplicate of
(Colden 2026-10-02, Q8: "use template" - the AMIRA / CWC_PodClips pattern: he puts his Fairlight strip on its A1 once,
every short inherits it). A DUPLICATE of edit-shorts' empty 1080x1920 `00 Shorts Template` (never modified): duplicating
is the only safe way to a vertical timeline - Timeline.SetSettings on a fresh timeline deadlocks Resolve 21.1.
The copy keeps V1 only and FOUR STEREO audio tracks: A1 "Main Pod Audio" (the program mix - HIS strip goes here), A2
Music, A3 SFX, A4 Meme (the source's per-person tracks are removed from the COPY; the builder adds the camera, Tags,
B-roll, Captions and Hook video tracks and the ISO audio tracks after A4, so the processed track is always A1).
Refuses an existing NAME; touches no other timeline; restores the current timeline."""
import time
def tls(): return {project.GetTimelineByIndex(i).GetName(): project.GetTimelineByIndex(i) for i in range(1, project.GetTimelineCount() + 1)}
T = tls(); assert NAME not in T, f'{NAME} already exists - never replaced'
src = T.get(SOURCE); assert src, f'{SOURCE} not found'
assert (src.GetSetting('timelineResolutionWidth'), src.GetSetting('timelineResolutionHeight')) == ('1080', '1920'), 'the source is not 1080x1920'
cur = project.GetCurrentTimeline(); cur_name = cur.GetName() if cur else None
project.SetCurrentTimeline(src); new = src.DuplicateTimeline(NAME); assert new, 'DuplicateTimeline failed'
project.SetCurrentTimeline(new)
for _ in range(50):
    if project.GetCurrentTimeline().GetName() == NAME: break
    time.sleep(0.1)
assert project.GetCurrentTimeline().GetName() == NAME
log = {'cleared': [], 'deleted': []}
for k in ('video', 'audio'):
    for i in range(1, new.GetTrackCount(k) + 1):
        its = new.GetItemListInTrack(k, i) or []
        if its: log['cleared'].append([k, i, [x.GetName() for x in its]]); new.DeleteClips(its, False)
time.sleep(0.3)
for i in range(new.GetTrackCount('video'), 1, -1): log['deleted'].append(['video', i, new.GetTrackName('video', i), bool(new.DeleteTrack('video', i))])
n0 = new.GetTrackCount('audio')
for nm in ('Main Pod Audio', 'Music', 'SFX', 'Meme'):
    assert new.AddTrack('audio', 'stereo'); new.SetTrackName('audio', new.GetTrackCount('audio'), nm)
for i in range(n0, 0, -1): log['deleted'].append(['audio', i, new.GetTrackName('audio', i), bool(new.DeleteTrack('audio', i))])
new.SetTrackName('video', 1, 'Program')
aud = [[new.GetTrackName('audio', i), new.GetTrackSubType('audio', i)] for i in range(1, new.GetTrackCount('audio') + 1)]
assert aud == [['Main Pod Audio', 'stereo'], ['Music', 'stereo'], ['SFX', 'stereo'], ['Meme', 'stereo']], aud
if cur_name and cur_name in tls(): project.SetCurrentTimeline(tls()[cur_name])
pm.SaveProject()
result = dict(log, name=NAME, w=new.GetSetting('timelineResolutionWidth'), h=new.GetSetting('timelineResolutionHeight'), fps=new.GetSetting('timelineFrameRate'),
              video=[new.GetTrackName('video', i) for i in range(1, new.GetTrackCount('video') + 1)], audio=aud,
              current_restored=project.GetCurrentTimeline().GetName() if project.GetCurrentTimeline() else None)
