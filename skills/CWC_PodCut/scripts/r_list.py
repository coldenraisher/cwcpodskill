"""Resolve side: timeline names + whether a render is running. Read-only."""
result = {'project': project.GetName(), 'rendering': bool(project.IsRenderingInProgress()), 'timelines': [t.GetName() for t in (project.GetTimelineByIndex(i) for i in range(1, project.GetTimelineCount() + 1)) if t]}
