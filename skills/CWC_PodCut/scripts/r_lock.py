"""Resolve side: green LOCKED marker at frame 0 of NAME (globals NAME, NOTE, PREFIX). AddMarker's frame is RELATIVE to
the timeline start. Reports other versions of the same cut that already carry a LOCKED marker; removes nothing."""
tls = {project.GetTimelineByIndex(i).GetName(): project.GetTimelineByIndex(i) for i in range(1, project.GetTimelineCount() + 1)}
t = tls[NAME]; locked = lambda x: any(mk.get('name') == 'LOCKED' for mk in (x.GetMarkers() or {}).values())
others = [n for n, x in tls.items() if n.startswith(PREFIX) and n != NAME and locked(x)]
have = locked(t); ok = True if have else t.AddMarker(0, 'Green', 'LOCKED', NOTE, 1)
pm.SaveProject(); result = {'marker': bool(ok), 'already': have, 'other_locked_versions': others}
