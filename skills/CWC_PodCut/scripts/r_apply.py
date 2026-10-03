"""Resolve side: build the PodCut from plan.json (run via rs.py; globals PLAN, BASE, POD, BIN, TRACKS, STEP + per step).
  STEP='create'  duplicate BASE as POD into BIN and empty the camera tracks OF THE DUPLICATE (the base is never touched;
                 an existing POD is refused, never replaced)
  STEP='place'   TRACK=<n>, KIND='video'|'audio', SEG_SLICE=[a, b]: slice that camera per plan segment (rate-aware, from
                 the base's own items), place it at the segment's output frame; video = enabled only on the chosen
                 camera, audio = enabled on track 1 (program mix), every ISO clip disabled
  STEP='link'    link each V item to the A item under it (resumable: LINK_BUDGET seconds per call)
The PodCut structure Colden's other skills read: V1 program, V2.. one ISO per person, all tracks cut on the same
boundaries, exactly ONE enabled video item per segment."""
import json, math, time
def tls(): return {project.GetTimelineByIndex(i).GetName(): project.GetTimelineByIndex(i) for i in range(1, project.GetTimelineCount() + 1)}
segs = json.load(open(PLAN))['segments']; root = mp.GetRootFolder(); log = {'step': STEP}
base = tls()[BASE]; BST = base.GetStartFrame()
cam_of = {t['track']: t['id'] for t in TRACKS}
if STEP == 'create':
    assert POD not in tls(), f'{POD} exists - never replaced; build under a new version'
    b = root
    for part in BIN.split('/'): b = next((x for x in b.GetSubFolderList() if x.GetName() == part), None) or mp.AddSubFolder(b, part)
    mp.SetCurrentFolder(b); project.SetCurrentTimeline(base)
    pod = base.DuplicateTimeline(POD); assert pod, 'DuplicateTimeline failed'
    for c in root.GetClipList():                       # DuplicateTimeline ignores the current folder
        if c.GetClipProperty('Type') == 'Timeline' and c.GetName() == POD: mp.MoveClips([c], b)
    project.SetCurrentTimeline(pod)
    for t in TRACKS:
        for kind in ('video', 'audio'):
            old = pod.GetItemListInTrack(kind, t['track']) or []
            if old: pod.DeleteClips(old, False)
    log['created'] = POD
pod = tls()[POD]; project.SetCurrentTimeline(pod); PST = pod.GetStartFrame()
if STEP == 'place':
    src = []
    for it in base.GetItemListInTrack(KIND, TRACK) or []:
        mpi = it.GetMediaPoolItem()
        if mpi: src.append({'tlStart': it.GetStart(), 'tlEnd': it.GetEnd(), 'srcStart': it.GetSourceStartFrame(), 'srcEnd': it.GetSourceEndFrame(), 'mp': mpi, 'total': int(mpi.GetClipProperty('Frames') or 0)})
    TLF = float(pod.GetSetting('timelineFrameRate') or 30)
    for c in src: c['fps'] = float(c['mp'].GetClipProperty('FPS') or TLF)
    def plan_clip(a, b):
        """source in / out of the shot [a, b) on this track. The rate is the clip's frame rate over the timeline's - 1.0
        for a same-rate file. (The plugin's port derived it from the base item's source span over its timeline span; those
        two differ by a frame or two of noise on a same-rate clip, which read as a 'rate' and slid the picture up to 2
        frames by the end of an 87-minute show - found by VERIFY against the manifest, 2026-10-01.)"""
        for c in src:
            if c['tlStart'] <= a < c['tlEnd']:
                rate = 1.0 if abs(c['fps'] - TLF) < 0.01 else c['fps'] / TLF
                s = c['srcStart'] + int(math.floor((a - c['tlStart']) * rate + 0.5)); e = s + int(math.ceil((b - a) * rate))
                if c['total'] and e > c['total']: return None                 # the shot runs past the end of this camera's file: no clip (never a short or clamped one)
                return c['mp'], s, e
        return None
    use = segs[SEG_SLICE[0]:SEG_SLICE[1]]; infos = []; en = []; skipped = []
    for s in use:
        a, b = BST + s['srcFrames'][0], BST + s['srcFrames'][1]; pc = plan_clip(a, b)
        if not pc: skipped.append(s['outFrame']); continue          # this camera has no media there (it started late / stopped early)
        infos.append({'mediaPoolItem': pc[0], 'startFrame': pc[1], 'endFrame': pc[2], 'mediaType': 1 if KIND == 'video' else 2, 'trackIndex': TRACK, 'recordFrame': PST + s['outFrame']})
        en.append((s['camera'] == cam_of[TRACK]) if KIND == 'video' else (TRACK == 1))
    made = []
    for i in range(0, len(infos), 40):       # a batch returns nothing when ONE info is invalid: chunks of 40, then singly
        cur = project.GetCurrentTimeline()     # AppendToTimeline writes to the CURRENT timeline: if someone clicked another one mid-build, stop before a clip lands on it
        assert cur and cur.GetName() == POD, f'the current timeline is {cur.GetName() if cur else None!r}, not {POD!r} - somebody switched timelines during the build; stopped'
        got = mp.AppendToTimeline(infos[i:i + 40]) or []
        if len(got) != len(infos[i:i + 40]):
            for x in infos[i:i + 40]:
                if not any(g.GetStart() == x['recordFrame'] for g in got): got += (mp.AppendToTimeline([x]) or [])
        made += got
    by_rec = {x['recordFrame']: e for x, e in zip(infos, en)}; off = 0
    for it in made:
        if not by_rec.get(it.GetStart(), True): it.SetClipEnabled(False); off += 1
    log.update({'track': TRACK, 'kind': KIND, 'wanted': len(infos), 'placed': len(made), 'disabled': off, 'skipped': skipped[:20], 'n_skipped': len(skipped)})
if STEP == 'link':
    n = 0; t0 = time.time(); done = True
    for t in TRACKS:
        v = {it.GetStart(): it for it in pod.GetItemListInTrack('video', t['track']) or []}
        for a_it in pod.GetItemListInTrack('audio', t['track']) or []:
            v_it = v.get(a_it.GetStart())
            if not v_it: continue
            try:
                if a_it.GetLinkedItems(): continue
            except Exception: pass
            try: pod.SetClipsLinked([v_it, a_it], True); n += 1
            except Exception: pass
            if time.time() - t0 > LINK_BUDGET: done = False; break
        if not done: break
    log.update({'linked': n, 'link_done': done})
log['frames'] = pod.GetEndFrame() - pod.GetStartFrame()
pm.SaveProject(); result = log
