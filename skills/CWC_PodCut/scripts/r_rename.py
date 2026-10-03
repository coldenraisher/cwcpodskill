"""Resolve side: rename a timeline (globals OLD, NEW). Refuses when NEW exists. Nothing else is touched."""
tls = {project.GetTimelineByIndex(i).GetName(): project.GetTimelineByIndex(i) for i in range(1, project.GetTimelineCount() + 1)}
assert OLD in tls, f'no timeline {OLD!r}'; assert NEW not in tls, f'{NEW!r} already exists - not renaming over it'
ok = tls[OLD].SetName(NEW); assert ok and tls[OLD].GetName() == NEW, f'SetName failed ({OLD!r} -> {NEW!r})'
pm.SaveProject(); result = {'renamed': NEW}
