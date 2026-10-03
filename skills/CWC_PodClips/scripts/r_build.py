"""Resolve side: build ONE clip timeline from a build plan (run via rs.py; globals PLAN, STEP [+ TRACK, KIND]).
  STEP='sources'  THE SOURCE GATE, read-only, first: every clip the plan uses resolves to exactly ONE media-pool item with
                  the plan's FILE PATH, and each camera's path is the one the locked PodCut itself uses
  STEP='import'   (only when the plan has censor beeps) the beep file into the Master bin when NO pool clip has its path -
                  an add, never a replace (Colden 2026-10-02: the Power Bin beep; Power Bins are not reachable by script)
  STEP='create'   duplicate the EMPTY template as the plan's `building` name (zz BUILDING ...) into <episode bin>/Clips,
                  add and name the video tracks (cameras, Tags, B-roll, Intro-Outro) and the ISO audio tracks AFTER the
                  template's four, so A1 "Main Pod Audio" keeps Colden's Fairlight strip. Refuses existing names.
  STEP='place'    KIND video|audio, TRACK n: every piece of that track (chunks of 40), enabled flags, punch properties
  STEP='extras'   stinger (video + audio), guest name tags, b-roll clips (video only, full frame, on B-roll), censor beeps, the Colden ending (last shot copy + glitch
                  transition + end screen, music in two parts, the hit)
  STEP='verify'   read everything back against the plan (every piece's FILE PATH included); on 0 problems rename to the final name and drop a red DRAFT marker
NON-DESTRUCTIVE: only the timeline this run created is written to; every append asserts it is still the CURRENT timeline
(a click on another timeline mid-build stops the run); nothing is ever deleted. No Fusion handles are held."""
import json, time
P = json.load(open(PLAN)); NAME = P['building']; FINAL = P['name']
def tls(): return {project.GetTimelineByIndex(i).GetName(): project.GetTimelineByIndex(i) for i in range(1, project.GetTimelineCount() + 1)}
def find(f, name):
    for c in f.GetClipList():
        if c.GetName() == name: return c
    for s in f.GetSubFolderList():
        r = find(s, name)
        if r: return r
def folder(path):
    b = mp.GetRootFolder()
    for part in path.split('/'):
        if part == b.GetName(): continue
        b = next((x for x in b.GetSubFolderList() if x.GetName() == part), None) or mp.AddSubFolder(b, part); assert b, f'bin {part!r}'
    return b
def find_folder(f, name):
    if f.GetName() == name: return f
    for s in f.GetSubFolderList():
        r = find_folder(s, name)
        if r: return r
root = mp.GetRootFolder(); log = {'step': STEP}
def current(tl):
    project.SetCurrentTimeline(tl)
    for _ in range(80):
        c = project.GetCurrentTimeline()
        if c and c.GetName() == tl.GetName(): return
        time.sleep(0.1)
    raise AssertionError(f'could not make {tl.GetName()!r} the current timeline')
def append(infos, label):
    made = []
    for i in range(0, len(infos), 40):
        cur = project.GetCurrentTimeline(); assert cur and cur.GetName() == NAME, f'the current timeline is {cur.GetName() if cur else None!r}, not {NAME!r} - somebody switched timelines during the build; stopped'
        got = mp.AppendToTimeline(infos[i:i + 40]) or []
        if len(got) != len(infos[i:i + 40]):
            for x in infos[i:i + 40]:
                if not any(g.GetStart() == x['recordFrame'] and g.GetTrackTypeAndIndex()[1] == x['trackIndex'] for g in got): got += (mp.AppendToTimeline([x]) or [])
        made += got
    assert len(made) == len(infos), f'{label}: placed {len(made)} of {len(infos)}'
    return made
if STEP == 'sources':
    # THE SOURCE GATE (Colden 2026-10-01: "a quick gate check when you are assembling clips that the correct source
    # files are being used every single time"). Read-only, runs before anything is created.
    def all_named(f, name, path=''):
        out = [[path + f.GetName(), c.GetClipProperty('File Path')] for c in f.GetClipList() if c.GetName() == name]
        for sub in f.GetSubFolderList(): out += all_named(sub, name, path + f.GetName() + '/')
        return out
    bad = []; rep = {}
    for name in P['sources_used']:
        want = P['media'].get(name); found = all_named(root, name); hit = [x for x in found if x[1] == want]
        rep[name] = {'path': want, 'bin': hit[0][0] if hit else None, 'same_name_in_pool': len(found)}
        if not want: bad.append(f'{name}: the plan has no file path')
        elif len(hit) != 1: bad.append(f'{name}: {len(hit)} media-pool clips have the path {want} (there are {len(found)} clips with that name: {found})')
    pod = tls().get(P['pod'])
    if not pod: bad.append(f'the PodCut timeline {P["pod"]!r} is not in the project')
    else:
        for i in range(1, pod.GetTrackCount('video') + 1):
            n = pod.GetTrackName('video', i)
            if n not in P['camera_tracks']: continue
            paths = sorted({it.GetMediaPoolItem().GetClipProperty('File Path') for it in (pod.GetItemListInTrack('video', i) or []) if it.GetMediaPoolItem()})
            want = sorted({P['media'][x['clip']] for x in P['items'] if x['kind'] == 'video' and x['track'] == P['tracks']['video'].index(n) + 1})
            if not set(want) <= set(paths): bad.append(f'camera {n}: the locked PodCut uses {paths}, the plan would use {want}')      # a subset: a camera split in two files, or unused in this clip, is fine
    result = {'step': 'sources', 'problems': bad, 'sources': rep}
elif STEP == 'create':
    T = tls(); assert NAME not in T and FINAL not in T, f'{NAME} / {FINAL} exists - never replaced; build the next version'
    tpl = T.get(P['template']); assert tpl, f'template {P["template"]!r} is missing'
    for k in ('video', 'audio'):
        for i in range(1, tpl.GetTrackCount(k) + 1): assert not (tpl.GetItemListInTrack(k, i) or []), f'the template has clips on {k} {i} - it must stay empty'
    assert tpl.GetTrackName('audio', 1) == 'Main Pod Audio', 'A1 of the template is not "Main Pod Audio"'
    ep = find_folder(root, P['bin']); assert ep, f'episode bin {P["bin"]!r} not found'
    dest = next((x for x in ep.GetSubFolderList() if x.GetName() == 'Clips'), None) or mp.AddSubFolder(ep, 'Clips'); assert dest
    current(tpl); tl = tpl.DuplicateTimeline(NAME); assert tl, 'DuplicateTimeline failed'
    def pool_tl(f):
        for c in f.GetClipList():
            if c.GetClipProperty('Type') == 'Timeline' and c.GetName() == NAME: return c, f
        for s in f.GetSubFolderList():
            r = pool_tl(s)
            if r: return r
    r = pool_tl(root)
    if r and r[1].GetName() != 'Clips': mp.MoveClips([r[0]], dest)
    current(tl)
    for n in P['tracks']['video'][tl.GetTrackCount('video'):]: assert tl.AddTrack('video')
    for i, n in enumerate(P['tracks']['video']): tl.SetTrackName('video', i + 1, n)
    for n in P['tracks']['audio'][tl.GetTrackCount('audio'):]: assert tl.AddTrack('audio', 'stereo')
    for i, n in enumerate(P['tracks']['audio']): tl.SetTrackName('audio', i + 1, n)
    assert tl.GetTrackName('audio', 1) == 'Main Pod Audio'
    log.update({'created': NAME, 'video': [tl.GetTrackName('video', i) for i in range(1, tl.GetTrackCount('video') + 1)], 'audio': [tl.GetTrackName('audio', i) for i in range(1, tl.GetTrackCount('audio') + 1)],
                'res': [tl.GetSetting('timelineResolutionWidth'), tl.GetSetting('timelineResolutionHeight')], 'fps': tl.GetSetting('timelineFrameRate'), 'start': tl.GetStartFrame()})
if STEP == 'import':
    def by_path(f, path):
        r = [c for c in f.GetClipList() if c.GetClipProperty('File Path') == path]
        for sub in f.GetSubFolderList(): r += by_path(sub, path)
        return r
    log['imported'] = []
    for fpath in [P['media'][P['beep']]] if P.get('beeps') else []:
        if not by_path(root, fpath):
            mp.SetCurrentFolder(root); got = mp.ImportMedia([fpath]) or []; assert got, f'import failed: {fpath}'; log['imported'].append(fpath)
if STEP not in ('sources', 'create', 'import'):
    tl = tls().get(NAME); assert tl, f'no timeline {NAME!r} (create first)'
    current(tl); ST = tl.GetStartFrame()
    VT = {n: i + 1 for i, n in enumerate(P['tracks']['video'])}; AT = {n: i + 1 for i, n in enumerate(P['tracks']['audio'])}
    pool = {}
    def find_path(f, name, path):
        for c in f.GetClipList():
            if c.GetName() == name and c.GetClipProperty('File Path') == path: return c
        for sub in f.GetSubFolderList():
            r = find_path(sub, name, path)
            if r: return r
    def clip(name):
        """a media-pool clip by name AND file path - never by name alone: the pool holds a JAKE.mp4 for more than one
        episode, and the first build put Ep 21's Jake under Ep 24's shots (Colden 2026-10-01: "wearing a black shirt
        instead of the white shirt he wore in todays episode")"""
        if name not in pool:
            want = P['media'].get(name); assert want, f'the plan has no file path for {name!r}'
            pool[name] = find_path(root, name, want); assert pool[name], f'{name!r} with path {want} is not in the media pool'
        return pool[name]
if STEP == 'place':
    its = [x for x in P['items'] if x['kind'] == KIND and x['track'] == TRACK]
    assert not (tl.GetItemListInTrack(KIND, TRACK) or []), f'{KIND} {TRACK} already has clips'
    made = append([{'mediaPoolItem': clip(x['clip']), 'startFrame': x['src_in'], 'endFrame': x['src_out'], 'mediaType': 1 if KIND == 'video' else 2, 'trackIndex': TRACK, 'recordFrame': ST + x['rec']} for x in its], f'{KIND} {TRACK}')
    by = {m.GetStart() - ST: m for m in made}; off = 0; props = 0
    for x in its:
        m = by[x['rec']]
        if not x['enabled']: m.SetClipEnabled(False); off += 1
        if x.get('props'): m.SetProperties(dict(x['props'], ZoomGang=True)); props += 1
        if x.get('volume') is not None: m.SetProperty('AudioVolume', float(x['volume']))
    log.update({'kind': KIND, 'track': TRACK, 'placed': len(made), 'disabled': off, 'with_props': props})
if STEP == 'extras':
    s = P['stinger']; sc = clip(s['clip'])
    made = append([{'mediaPoolItem': sc, 'startFrame': 0, 'endFrame': s['src_video_end'], 'mediaType': 1, 'trackIndex': VT['Intro-Outro'], 'recordFrame': ST + s['rec']},
                   {'mediaPoolItem': sc, 'startFrame': 0, 'endFrame': s['src_audio_end'], 'mediaType': 2, 'trackIndex': AT['Music'], 'recordFrame': ST + s['rec']}], 'stinger')
    for m in made:
        if m.GetTrackTypeAndIndex()[0] == 'video': m.SetFades({'FadeIn': 0, 'FadeOut': s['fade_frames']}); log['stinger_video'] = [m.GetStart() - ST, m.GetDuration()]
        else: log['stinger_audio'] = [m.GetStart() - ST, m.GetDuration()]
    if P['tags']:
        assets = folder(P['clips_bin'] + '/Assets'); have = {c.GetClipProperty('File Path'): c for c in assets.GetClipList()}; mp.SetCurrentFolder(assets)
        for t in P['tags']:
            if t['file'] not in have:
                got = mp.ImportMedia([t['file']]) or []; assert got, f'import failed: {t["file"]}'; have[t['file']] = got[0]
        made = append([{'mediaPoolItem': have[t['file']], 'startFrame': 0, 'endFrame': t['frames'], 'mediaType': 1, 'trackIndex': VT['Tags'], 'recordFrame': ST + t['rec']} for t in P['tags']], 'tags')
        for m in made: m.SetFades({'FadeIn': P['tags'][0]['fade_frames'], 'FadeOut': P['tags'][0]['fade_frames']})
        log['tags'] = [[m.GetName(), m.GetStart() - ST, m.GetDuration()] for m in made]
    if P.get('broll'):
        bb = folder(P['clips_bin'] + '/B-Roll'); have = {c.GetClipProperty('File Path'): c for c in bb.GetClipList()}; mp.SetCurrentFolder(bb)
        for x in P['broll']:
            if x['file'] not in have:
                got = mp.ImportMedia([x['file']]) or []; assert got, f'import failed: {x["file"]}'; have[x['file']] = got[0]
        made = append([{'mediaPoolItem': have[x['file']], 'startFrame': 0, 'endFrame': x['frames'], 'mediaType': 1, 'trackIndex': VT['B-roll'], 'recordFrame': ST + x['rec']} for x in P['broll']], 'b-roll')
        log['broll'] = [[m.GetName()[:40], m.GetStart() - ST, m.GetDuration()] for m in made]
    if P.get('beeps'):                                    # the Power Bin beep, copies back to back over each window, no fades (a fade would gap the tone)
        beep = clip(P['beep'])
        made = append([{'mediaPoolItem': beep, 'startFrame': 0, 'endFrame': x['frames'], 'mediaType': 2, 'trackIndex': AT[x.get('track', 'SFX')], 'recordFrame': ST + x['rec']} for x in P['beeps']], 'censor')      # 'Meme' only where the ending hit already sits on SFX
        for m in made: m.SetProperty('AudioVolume', P.get('beep_db', -10.0))
        log['censor'] = [[m.GetStart() - ST, m.GetDuration()] for m in made]
    o = P['outro']; Cf = o['C']; ls = o['last_shot']; mus = clip(o['music_clip']); sfx = clip(o['sfx_clip']); es = clip(o['end_screen_clip'])
    infos = [{'mediaPoolItem': clip(ls['clip']), 'startFrame': ls['src_in'], 'endFrame': ls['src_out'], 'mediaType': 1, 'trackIndex': VT['Intro-Outro'], 'recordFrame': ST + ls['rec']},
             {'mediaPoolItem': es, 'startFrame': o['end_screen_src_in'], 'endFrame': o['end_screen_src_in'] + o['end_screen_frames'], 'mediaType': 1, 'trackIndex': VT['Intro-Outro'], 'recordFrame': ST + Cf},
             {'mediaPoolItem': mus, 'startFrame': o['music_src_in'], 'endFrame': o['music_src_in'] + o['music_pre_frames'], 'mediaType': 2, 'trackIndex': AT['Music'], 'recordFrame': ST + Cf - o['music_pre_frames']},
             {'mediaPoolItem': mus, 'startFrame': o['music_src_in'] + o['music_pre_frames'], 'endFrame': o['music_src_in'] + o['music_pre_frames'] + o['end_screen_frames'], 'mediaType': 2, 'trackIndex': AT['Music'], 'recordFrame': ST + Cf},
             {'mediaPoolItem': sfx, 'startFrame': 0, 'endFrame': o['sfx_frames'], 'mediaType': 2, 'trackIndex': AT['SFX'], 'recordFrame': ST + Cf - o['sfx_hit_frame']}]
    made = append(infos, 'ending'); vid = sorted([m for m in made if m.GetTrackTypeAndIndex()[0] == 'video'], key=lambda m: m.GetStart()); aud = [m for m in made if m.GetTrackTypeAndIndex()[0] == 'audio']
    if ls.get('props'): vid[0].SetProperties(dict(ls['props'], ZoomGang=True))
    tr = None
    try: tr = vid[0].AddTransition({'type': o['transition'], 'category': 'fusion', 'position': 'end', 'alignment': 'center', 'duration': o['transition_frames']})
    except Exception as e: log['transition_error'] = str(e)[:200]
    log['transition'] = bool(tr)
    m2 = sorted([m for m in aud if m.GetTrackTypeAndIndex()[1] == AT['Music']], key=lambda m: m.GetStart())
    m2[0].SetProperty('AudioVolume', o['music_db_before']); m2[0].SetFades({'FadeIn': o['music_fade_in_frames'], 'FadeOut': 0}); m2[1].SetProperty('AudioVolume', o['music_db_after'])
    for m in aud:
        if m.GetTrackTypeAndIndex()[1] == AT['SFX']: m.SetProperty('AudioVolume', o['sfx_db'])
    log['ending'] = [[m.GetName(), list(m.GetTrackTypeAndIndex()), m.GetStart() - ST, m.GetDuration()] for m in made]
if STEP == 'verify':
    bad = []; got = {}; off1 = []
    for kind, names in (('video', P['tracks']['video']), ('audio', P['tracks']['audio'])):
        for i, n in enumerate(names):
            rows = [[it.GetStart() - ST, it.GetDuration(), bool(it.GetClipEnabled()), (it.GetMediaPoolItem().GetName() if it.GetMediaPoolItem() else None), it.GetSourceStartFrame(), (it.GetMediaPoolItem().GetClipProperty('File Path') if it.GetMediaPoolItem() else None)] for it in tl.GetItemListInTrack(kind, i + 1) or []]
            got[f'{kind}:{i + 1}'] = rows
            want = sorted([x for x in P['items'] if x['kind'] == kind and x['track'] == i + 1], key=lambda x: x['rec'])
            if kind == 'video' and n in ('Tags', 'B-roll', 'Intro-Outro') or kind == 'audio' and n in ('Music', 'SFX', 'Meme'): continue
            if len(rows) != len(want): bad.append(f'{kind} {i + 1} {n}: {len(rows)} items, plan has {len(want)}'); continue
            wrong = sorted({r[5] for r, x in zip(rows, want) if r[5] != P['media'].get(x['clip'])})
            if wrong: bad.append(f'{kind} {i + 1} {n}: WRONG MEDIA - uses {wrong}, the plan says {sorted({P["media"].get(x["clip"]) for x in want})}')
            for r, x in zip(rows, want):
                if r[4] != x['src_in'] and abs(r[4] - x['src_in']) <= 1: off1.append([kind, i + 1, x['rec'], r[4] - x['src_in']])     # Resolve reads some mid-clip starts back one frame off (the PodCut's own check allows 1.5)
                if r[0] != x['rec'] or r[1] != x['src_out'] - x['src_in'] or r[2] != x['enabled'] or r[3] != x['clip'] or abs(r[4] - x['src_in']) > 1:
                    bad.append(f'{kind} {i + 1} {n} at {x["rec"]}: is {r}, plan {[x["rec"], x["src_out"] - x["src_in"], x["enabled"], x["clip"], x["src_in"]]}')
                    if len(bad) > 12: break
    cams = [i + 1 for i, n in enumerate(P['tracks']['video']) if n in P['camera_tracks']]
    on = {}
    for c in cams:
        for r in got[f'video:{c}']:
            if r[2]: on[r[0]] = on.get(r[0], 0) + 1
    recs = sorted({r[0] for c in cams for r in got[f'video:{c}']})
    multi = [r for r in recs if on.get(r, 0) != 1]
    if multi: bad.append(f'{len(multi)} pieces do not have exactly ONE enabled camera (first at {multi[0]})')
    if not all(r[2] for r in got['audio:1']): bad.append('a program-audio clip on A1 is disabled')
    for i, n in enumerate(P['tracks']['audio']):
        if n in P['camera_tracks'] and any(r[2] for r in got[f'audio:{i + 1}']): bad.append(f'ISO audio on A{i + 1} {n} is enabled')
    frames = tl.GetEndFrame() - ST
    if frames != P['frames']: bad.append(f'timeline is {frames} frames, plan {P["frames"]}')
    io = [r for r in got[f'video:{VT["Intro-Outro"]}'] if r[3]]; trans = [r for r in got[f'video:{VT["Intro-Outro"]}'] if not r[3]]
    if len(io) != 3: bad.append(f'Intro-Outro has {len(io)} clips, wanted 3 (stinger, last shot, end screen)')
    if len(trans) != 1: bad.append(f'the ending transition is missing ({len(trans)} found) - is the Drag-N-Drop Glitch Transitions pack installed?')
    if io and (io[-1][0] != P['outro']['C'] or io[-1][1] != P['outro']['end_screen_frames']): bad.append(f'end screen is at {io[-1][0]} for {io[-1][1]} frames, plan {P["outro"]["C"]} / {P["outro"]["end_screen_frames"]}')
    if len(got[f'video:{VT["Tags"]}']) != len(P['tags']): bad.append('name tag count')
    br = got[f'video:{VT["B-roll"]}']; want_br = sorted([[x['rec'], x['frames']] for x in P.get('broll', [])])
    if sorted([[r[0], r[1]] for r in br]) != want_br: bad.append(f'b-roll on the timeline {sorted([[r[0], r[1]] for r in br])} is not the plan {want_br}')
    nm = len(got['audio:%d' % AT['Music']])
    if nm != 3: bad.append(f'Music has {nm} clips, wanted 3 (stinger audio, riff before C, riff after C)')
    ns = len(got['audio:%d' % AT['SFX']])
    want_sfx = 1 + len([x for x in P.get('beeps') or [] if x.get('track', 'SFX') == 'SFX'])
    if ns != want_sfx: bad.append(f'SFX has {ns} clips, wanted {want_sfx} (the hit + the beep pieces)')
    sfx_rows = got['audio:%d' % AT['SFX']] + got['audio:%d' % AT['Meme']]; bp = sorted([r[0], r[1]] for r in sfx_rows if r[3] == P.get('beep')); wb = sorted([x['rec'], x['frames']] for x in P.get('beeps') or [])
    if bp != wb: bad.append(f'beeps on SFX {bp} are not the plan {wb}')
    if any(r[5] != P['media'].get(P.get('beep')) for r in sfx_rows if r[3] == P.get('beep')): bad.append(f'beep: WRONG MEDIA - not {P["media"].get(P.get("beep"))}')
    log.update({'problems': bad, 'frames': frames, 'counts': {k: len(v) for k, v in got.items()}, 'src_off_by_one': off1})
    if not bad:
        tl.AddMarker(0, 'Red', 'DRAFT', f'CWC_PodClips {P["theme"]} {P["version"]} - not approved', 1, 'cwc-podclips')
        assert tl.SetName(FINAL), 'rename failed'; log['name'] = FINAL
if STEP != 'sources':
    pm.SaveProject(); result = log
