"""READ-ONLY: the current timeline's name and, when it is the template, A1's voice-isolation state (the API reads it
on the CURRENT timeline only - never switched here)."""
tl = project.GetCurrentTimeline(); out = {'current': tl.GetName() if tl else None}
if tl and tl.GetName() == NAME:
    out['voice_isolation'] = {tl.GetTrackName('audio', i): tl.GetVoiceIsolationState(i) for i in range(1, tl.GetTrackCount('audio') + 1)}
    out['items'] = sum(len(tl.GetItemListInTrack(k, i) or []) for k in ('video', 'audio') for i in range(1, tl.GetTrackCount(k) + 1))
result = out
