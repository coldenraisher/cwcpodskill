"""Resolve side, READ-ONLY: the names of every timeline in the project."""
result = {'timelines': [project.GetTimelineByIndex(i).GetName() for i in range(1, project.GetTimelineCount() + 1) if project.GetTimelineByIndex(i)]}
