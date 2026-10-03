"""READ-ONLY: resolution-mismatch settings of named timelines (no switching)."""
T = {project.GetTimelineByIndex(i).GetName(): project.GetTimelineByIndex(i) for i in range(1, project.GetTimelineCount() + 1)}
keys = ['timelineInputResMismatchBehavior', 'timelineInputResMismatchUseCustomPreset', 'timelineOutputResMismatchBehavior', 'timelineOutputResMismatchUseCustomPreset', 'timelineResolutionWidth', 'timelineResolutionHeight']
result = {n: {k: T[n].GetSetting(k) for k in keys} for n in NAMES if n in T}
result['project'] = {k: project.GetSetting(k) for k in ('timelineInputResMismatchBehavior', 'timelineOutputResMismatchBehavior')}
