"""Open the show's Resolve project (run via rs.py with PROJECT=<name>). The ONLY script that switches projects, and it
refuses while a render is running. The project that was open is saved first (nothing of Colden's is discarded).
result: {'project', 'was', 'switched', 'fps', 'timelines'}"""
was = project.GetName() if project else None
if was != PROJECT:
    assert not (project and project.IsRenderingInProgress()), f'{was!r} is rendering - not switching projects'
    if project: pm.SaveProject()
    p = pm.LoadProject(PROJECT); assert p, f'project {PROJECT!r} not found in the current Resolve database'
    project = p
result = {'project': project.GetName(), 'was': was, 'switched': was != PROJECT, 'fps': project.GetSetting('timelineFrameRate'),
          'resolution': [project.GetSetting('timelineResolutionWidth'), project.GetSetting('timelineResolutionHeight')], 'timelines': project.GetTimelineCount()}
