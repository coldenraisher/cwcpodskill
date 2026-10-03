"""Resolve side (run via rs.py; PROJECT, NAME, SOURCE): make the ONE empty template every clip is a duplicate of
(Colden 2026-10-01, ruling 27: "create one template timeline that I can add the compressor, noise reduction and EQ on").
A DUPLICATE of the empty UHD `00 Clips Template` (edit-clips' own, never modified) - duplicating is the only way to get
a UHD timeline without Timeline.SetSettings, which deadlocks Resolve 21.1 on a fresh timeline. The copy keeps V1 and four
stereo audio tracks: A1 "Main Pod Audio" (the program mix - HIS Fairlight strip goes here), A2 Music, A3 SFX, A4 Meme.
The builder adds the camera, Tags, B-roll and Intro-Outro video tracks and the ISO audio tracks (after A4) per episode,
so the processed track is always A1. Refuses an existing NAME; touches no other timeline; restores the current timeline."""
import time
def tls(): return {project.GetTimelineByIndex(i).GetName(): project.GetTimelineByIndex(i) for i in range(1, project.GetTimelineCount() + 1)}
T = tls(); assert NAME not in T, f'{NAME} already exists - never replaced'
src = T.get(SOURCE); assert src, f'{SOURCE} not found'
for k in ('video', 'audio'):
    for i in range(1, src.GetTrackCount(k) + 1): assert not (src.GetItemListInTrack(k, i) or []), f'{SOURCE} is not empty ({k} {i})'
cur = project.GetCurrentTimeline(); cur_name = cur.GetName() if cur else None
project.SetCurrentTimeline(src); new = src.DuplicateTimeline(NAME); assert new, 'DuplicateTimeline failed'
project.SetCurrentTimeline(new)
for _ in range(50):
    if project.GetCurrentTimeline().GetName() == NAME: break
    time.sleep(0.1)
assert project.GetCurrentTimeline().GetName() == NAME
log = {'deleted': []}
for i in range(new.GetTrackCount('video'), 1, -1): log['deleted'].append(['video', i, new.GetTrackName('video', i), bool(new.DeleteTrack('video', i))])
for i in range(new.GetTrackCount('audio'), 1, -1): log['deleted'].append(['audio', i, new.GetTrackName('audio', i), bool(new.DeleteTrack('audio', i))])
assert new.GetTrackSubType('audio', 1) == 'stereo', 'A1 of the source is not stereo'
new.SetTrackName('video', 1, 'Program'); new.SetTrackName('audio', 1, 'Main Pod Audio')
for n in ('Music', 'SFX', 'Meme'):                       # the source's own were mono (found 2026-10-01): made fresh as stereo
    assert new.AddTrack('audio', 'stereo'); new.SetTrackName('audio', new.GetTrackCount('audio'), n)
if cur_name and cur_name in tls(): project.SetCurrentTimeline(tls()[cur_name])
pm.SaveProject()
result = dict(log, name=NAME, w=new.GetSetting('timelineResolutionWidth'), h=new.GetSetting('timelineResolutionHeight'), fps=new.GetSetting('timelineFrameRate'),
              video=[new.GetTrackName('video', i) for i in range(1, new.GetTrackCount('video') + 1)],
              audio=[[new.GetTrackName('audio', i), new.GetTrackSubType('audio', i)] for i in range(1, new.GetTrackCount('audio') + 1)],
              current_restored=project.GetCurrentTimeline().GetName())
