"""Resolve side: build ONE short from a build plan (run via rs.py; globals PLAN, STEP [+ KIND, TRACK, I0, I1, SHOTS]).
  STEP='sources'  THE SOURCE GATE, read-only, first: every clip resolves to exactly ONE media-pool item with the plan's
                  FILE PATH, and each camera's path is the one the locked PodCut itself uses (Colden 2026-10-01: "a quick
                  gate check ... that the correct source files are being used every single time")
  STEP='import'   add-only, by path: the censor beep (Master), the transparent text clip (<bin>/Shorts/Assets), name-tag
                  clips (Shorts/Assets/nametag), b-roll clips (Shorts/B-Roll) - never replaces a pool clip
  STEP='create'   duplicate the EMPTY `00 PodReels Template` as `zz BUILDING <name>` into <bin>/Shorts, add + name the video
                  tracks (cameras, Program, Tags, B-roll, Captions, Hook) and the ISO audio tracks AFTER A4 (A1 keeps his strip)
  STEP='place'    KIND video|audio, TRACK n: every piece of that track (chunks of 40), Inspector transforms, enabled flags, duck
  STEP='captions' I0..I1 caption runs: Text+ on the transparent clip, keyframed per phrase, Colden's saved style
  STEP='hook'     the hook Text+ (white box) + name tags + b-roll + censor beeps
  STEP='hookfit'  render ONE frame of the hook, measure the white box, size it to 940 px, re-check: box top >= 50 px under
                  the caption line and bottom inside the safe zone (frames kept in edit/<id>/stills/)
  STEP='verify'   read everything back (FILE PATH of every camera piece, counts, frames, ISO audio disabled, A1 enabled);
                  0 problems -> rename to the final name + red DRAFT marker at frame 0
NON-DESTRUCTIVE: only the timeline this run created is written to; every append checks it is still the CURRENT timeline;
nothing is deleted. Fusion handles are created and dropped inside one call (Resolve 21.1 aborts on held handles)."""
import json, os, re, time, glob, subprocess, tempfile
P = json.load(open(PLAN, encoding='utf-8')); NAME = P['building']; FINAL = P['name']; WORK = os.path.dirname(os.path.dirname(os.path.dirname(PLAN)))
STY = json.load(open(os.path.expanduser('~/.claude/skills/CWC_PodReels/references/text_styles.json'), encoding='utf-8'))
def tls(): return {project.GetTimelineByIndex(i).GetName(): project.GetTimelineByIndex(i) for i in range(1, project.GetTimelineCount() + 1)}
def find_folder(f, name):
    if f.GetName() == name: return f
    for s in f.GetSubFolderList():
        r = find_folder(s, name)
        if r: return r
def sub(f, n): return next((x for x in f.GetSubFolderList() if x.GetName() == n), None) or mp.AddSubFolder(f, n)
root = mp.GetRootFolder(); log = {'step': STEP}
ep = find_folder(root, P['bin']); assert ep, f'episode bin {P["bin"]!r} not found'
shorts = sub(ep, P['shorts_bin']); assets = sub(shorts, 'Assets'); brbin = sub(shorts, 'B-Roll'); tagbin = sub(assets, 'nametag')
def by_path(f, path):
    r = [c for c in f.GetClipList() if c.GetClipProperty('File Path') == path]
    for s in f.GetSubFolderList(): r += by_path(s, path)
    return r
def current(tl):
    project.SetCurrentTimeline(tl)
    for _ in range(80):
        c = project.GetCurrentTimeline()
        if c and c.GetName() == tl.GetName(): return
        time.sleep(0.1)
    raise AssertionError(f'could not make {tl.GetName()!r} current')
def append(infos, label):
    made = []
    for i in range(0, len(infos), 40):
        cur = project.GetCurrentTimeline(); assert cur and cur.GetName() == NAME, f'the current timeline is {cur.GetName() if cur else None!r}, not {NAME!r} - somebody switched timelines during the build; stopped'
        chunk = infos[i:i + 40]; got = mp.AppendToTimeline(chunk) or []
        if len(got) != len(chunk):
            for x in chunk:
                if not any(g.GetStart() == x['recordFrame'] and g.GetTrackTypeAndIndex()[1] == x['trackIndex'] for g in got): got += (mp.AppendToTimeline([x]) or [])
        made += got
    assert len(made) == len(infos), f'{label}: placed {len(made)} of {len(infos)}'
    return made

if STEP == 'sources':
    def all_named(f, name, path=''):
        out = [[path + f.GetName(), c.GetClipProperty('File Path')] for c in f.GetClipList() if c.GetName() == name]
        for s in f.GetSubFolderList(): out += all_named(s, name, path + f.GetName() + '/')
        return out
    bad = []; rep = {}
    for name in P['sources_used']:
        want = P['media'].get(name); found = all_named(root, name); hit = [x for x in found if x[1] == want]
        rep[name] = {'path': want, 'bin': hit[0][0] if hit else None, 'same_name_in_pool': len(found)}
        if len(hit) != 1: bad.append(f'{name}: {len(hit)} media-pool clips have the path {want} ({len(found)} clips with that name: {found})')
    pod = tls().get(P['pod'])
    if not pod: bad.append(f'the PodCut {P["pod"]!r} is not in the project')
    else:
        for i in range(1, pod.GetTrackCount('video') + 1):
            n = pod.GetTrackName('video', i)
            if n not in P['camera_tracks'] + ['Program']: continue
            paths = sorted({it.GetMediaPoolItem().GetClipProperty('File Path') for it in (pod.GetItemListInTrack('video', i) or []) if it.GetMediaPoolItem()})
            want = sorted({P['media'][x['clip']] for x in P['items'] if x['kind'] == 'video' and P['tracks']['video'][x['track'] - 1] == n})
            if not set(want) <= set(paths): bad.append(f'camera {n}: the locked PodCut uses {paths}, the plan would use {want}')
    if not tls().get(P['template']): bad.append(f'the template {P["template"]!r} is missing (r_template.py)')
    result = {'step': 'sources', 'problems': bad, 'sources': rep}
elif STEP == 'import':
    log['imported'] = []
    def imp(folder, paths):
        need = [p for p in paths if not by_path(root, p)]
        if need:
            mp.SetCurrentFolder(folder); got = mp.ImportMedia(need) or []; assert len(got) == len(need), f'import failed: {need}'; log['imported'] += need
    if P.get('beeps'): imp(root, [P['media'][P['beep']]])
    imp(assets, [P['transparent']]); imp(tagbin, sorted({t['file'] for t in P['tags']})); imp(brbin, sorted({b['file'] for b in P['broll']}))
    mp.SetCurrentFolder(shorts); pm.SaveProject(); result = log
elif STEP == 'create':
    T = tls(); assert NAME not in T and FINAL not in T, f'{NAME} / {FINAL} exists - never replaced; build the next version'
    tpl = T.get(P['template']); assert tpl, f'template {P["template"]!r} is missing'
    for k in ('video', 'audio'):
        for i in range(1, tpl.GetTrackCount(k) + 1): assert not (tpl.GetItemListInTrack(k, i) or []), f'the template has clips on {k} {i} - it must stay empty'
    assert tpl.GetTrackName('audio', 1) == 'Main Pod Audio'
    current(tpl); tl = tpl.DuplicateTimeline(NAME); assert tl, 'DuplicateTimeline failed'
    def pool_tl(f):
        for c in f.GetClipList():
            if c.GetClipProperty('Type') == 'Timeline' and c.GetName() == NAME: return c, f
        for s in f.GetSubFolderList():
            r = pool_tl(s)
            if r: return r
    r = pool_tl(root)
    if r and r[1].GetName() != P['shorts_bin']: mp.MoveClips([r[0]], shorts)
    current(tl)
    while tl.GetTrackCount('video') < len(P['tracks']['video']): assert tl.AddTrack('video')
    for i, n in enumerate(P['tracks']['video']): tl.SetTrackName('video', i + 1, n)
    while tl.GetTrackCount('audio') < len(P['tracks']['audio']): assert tl.AddTrack('audio', 'stereo')
    for i, n in enumerate(P['tracks']['audio']): tl.SetTrackName('audio', i + 1, n)
    assert tl.GetTrackName('audio', 1) == 'Main Pod Audio' and (tl.GetSetting('timelineResolutionWidth'), tl.GetSetting('timelineResolutionHeight')) == ('1080', '1920')
    # Colden 2026-10-02: the template's A1 carries his strip - compressor / limiter, EQ (the API cannot read those) and
    # voice isolation at 60 % (it can, on the CURRENT timeline): a short whose A1 lost it was not made from his template
    vi = tl.GetVoiceIsolationState(1) or {}
    assert vi.get('isEnabled') and int(vi.get('amount') or 0) == 60, f'A1 "Main Pod Audio" voice isolation is {vi}, the template has it on at 60 - fix the TEMPLATE, never the short'
    log['voice_isolation'] = vi
    pm.SaveProject(); result = dict(log, created=NAME, video=[tl.GetTrackName('video', i) for i in range(1, tl.GetTrackCount('video') + 1)], audio=[tl.GetTrackName('audio', i) for i in range(1, tl.GetTrackCount('audio') + 1)])
else:
    tl = tls().get(NAME); assert tl, f'no timeline {NAME!r} (create first)'
    current(tl); ST = tl.GetStartFrame(); VT = {n: i + 1 for i, n in enumerate(P['tracks']['video'])}; AT = {n: i + 1 for i, n in enumerate(P['tracks']['audio'])}
    pool = {}
    def clip(name, path=None):
        path = path or P['media'].get(name); assert path, f'no file path for {name!r}'
        if path not in pool:
            hit = by_path(root, path); assert len(hit) >= 1, f'{path} is not in the media pool'; pool[path] = hit[0]
        return pool[path]
    def apply_style(tp, style):
        for k, v in style.items():
            if k.startswith('_'): continue
            if isinstance(v, dict) and '__table' in v:
                t = v['__table']; v = {1: t[0], 2: t[1], 3: t[2]} if len(t) == 3 else {1: t[0], 2: t[1]}
            try: tp.SetInput(k, v, 0)
            except Exception: pass
    def apply_gradient(tp, style):
        g = style.get('__gradient1')
        if not g: return
        stops = ''.join(f"\t\t\t\t\t\t\t[{i}] = {{ {c[0]}, {c[1]}, {c[2]}, {c[3] if len(c) > 3 else 1} }}{',' if i < len(g) - 1 else ''}\n" for i, c in enumerate(g))
        block = "\t\t\t\tShadingGradient1 = Input {\n\t\t\t\t\tValue = Gradient {\n\t\t\t\t\t\tColors = {\n" + stops + "\t\t\t\t\t\t}\n\t\t\t\t\t},\n\t\t\t\t},\n"
        path = os.path.join(tempfile.gettempdir(), 'cwc_podreels_tp.setting')
        if not tp.SaveSettings(path): return
        txt = open(path).read(); txt = re.sub(r"\t*ShadingGradient1 = Input \{.*?\n\t{4}\},\n", "", txt, flags=re.S)
        if 'Type1 = Input' in txt: txt = re.sub(r"(Type1 = Input \{ Value = )[^,]+(, \},\n)", r"\g<1>2\2", txt)
        else: txt = txt.replace("\t\t\t\tFont = Input", "\t\t\t\tType1 = Input { Value = 2, },\n\t\t\t\tFont = Input", 1)
        txt = txt.replace("Type1 = Input { Value = 2, },\n", "Type1 = Input { Value = 2, },\n" + block, 1); open(path, 'w').write(txt); tp.LoadSettings(path)
    def text_clip(track, rec, frames, style, center, keys=None, text=None, fades=None):
        made = append([{'mediaPoolItem': clip(None, P['transparent']), 'startFrame': 0, 'endFrame': frames, 'mediaType': 1, 'trackIndex': track, 'recordFrame': ST + rec}], 'text')
        ti = made[0]; comp = ti.AddFusionComp()
        if not comp: time.sleep(0.3); comp = ti.AddFusionComp()
        assert comp, 'AddFusionComp returned None (overlap, or a dialog is open in Resolve)'
        tp = comp.AddTool('TextPlus', -32768, -32768); apply_style(tp, style)
        tp.SetInput('GlobalIn', 0); tp.SetInput('GlobalOut', frames + 10); tp.SetInput('Center', {1: center[0], 2: center[1], 3: 0.0}, 0)
        if keys:
            tp.StyledText = comp.BezierSpline()
            for f, t in keys: tp.StyledText[f] = t
        else: tp.SetInput('StyledText', text, 0)
        comp.FindTool('MediaOut1').ConnectInput('Input', tp); apply_gradient(tp, style)
        if fades: ti.SetFades(fades)
        return ti
def resolve_units(props):
    """intended geometry -> Resolve's Zoom / Pan / Tilt on THIS timeline: a clip whose resolution differs from the timeline
    is first pre-scaled by the timeline's mismatch setting (centerCrop: not at all; scaleToFit: to fit; scaleToCrop: to
    fill), and Zoom / Pan / Tilt are relative to that (edit-shorts resolve.md, measured 2026-09-11 / 09-22)"""
    p = dict(props); sw, sh = p.pop('sw'), p.pop('sh'); tw, th = int(tl.GetSetting('timelineResolutionWidth')), int(tl.GetSetting('timelineResolutionHeight'))
    mode = tl.GetSetting('timelineInputResMismatchBehavior')
    base = {'centerCrop': 1.0, 'scaleToFit': min(tw / sw, th / sh), 'scaleToCrop': max(tw / sw, th / sh)}.get(mode)
    assert base, f'unknown input-resolution-mismatch setting {mode!r} on {NAME} - measure it before building'
    for k in ('ZoomX', 'ZoomY', 'Pan', 'Tilt'): p[k] = p[k] / base
    return p
if STEP == 'place':
    its = [x for x in P['items'] if x['kind'] == KIND and x['track'] == TRACK]
    assert not (tl.GetItemListInTrack(KIND, TRACK) or []), f'{KIND} {TRACK} already has clips'
    made = append([{'mediaPoolItem': clip(x['clip']), 'startFrame': x['src_in'], 'endFrame': x['src_out'], 'mediaType': 1 if KIND == 'video' else 2, 'trackIndex': TRACK, 'recordFrame': ST + x['rec']} for x in its], f'{KIND} {TRACK}')
    by = {m.GetStart() - ST: m for m in made}; off = 0; pr = 0; bad = []
    for x in its:
        m = by[x['rec']]
        if not x['enabled']: m.SetClipEnabled(False); off += 1
        if x.get('props'):
            if not m.SetProperties(dict(resolve_units(x['props']), ZoomGang=True)): bad.append(x['rec'])
            pr += 1
        if x.get('volume') is not None: m.SetProperty('AudioVolume', float(x['volume']))
    pm.SaveProject(); result = dict(log, kind=KIND, track=TRACK, placed=len(made), disabled=off, with_props=pr, props_failed=bad, mismatch=tl.GetSetting('timelineInputResMismatchBehavior'))
if STEP == 'captions':
    st = dict(STY['captions']); st['VerticalTopCenterBottom'] = 0.0; n = 0
    for c in P['captions'][I0:I1]: text_clip(VT['Captions'], c['rec'], c['frames'], st, (0.5, c['y']), keys=[(f, t) for f, t in c['keys']]); n += 1
    pm.SaveProject(); result = dict(log, captions=f'{I0}..{I0 + n} of {len(P["captions"])}')
if STEP == 'hook':
    h = P['hook']; text_clip(VT['Hook'], h['rec'], h['frames'], STY['hook'], (0.5, h['y']), text='\n'.join(h['lines']), fades={'FadeIn': 0, 'FadeOut': h['fade_out']})
    if P['tags']:
        made = append([{'mediaPoolItem': clip(None, t['file']), 'startFrame': 0, 'endFrame': t['frames'], 'mediaType': 1, 'trackIndex': VT['Tags'], 'recordFrame': ST + t['rec']} for t in P['tags']], 'tags')
        for m, t in zip(made, P['tags']): m.SetFades({'FadeIn': t['fade'], 'FadeOut': t['fade']})
        log['tags'] = [[m.GetName(), m.GetStart() - ST, m.GetDuration()] for m in made]
    if P['broll']:
        made = append([{'mediaPoolItem': clip(None, b['file']), 'startFrame': 0, 'endFrame': b['frames'], 'mediaType': 1, 'trackIndex': VT['B-roll'], 'recordFrame': ST + b['rec']} for b in P['broll']], 'b-roll')
        log['broll'] = [[m.GetName()[:40], m.GetStart() - ST, m.GetDuration()] for m in made]
    if P['beeps']:
        made = append([{'mediaPoolItem': clip(P['beep']), 'startFrame': 0, 'endFrame': b['frames'], 'mediaType': 2, 'trackIndex': AT['SFX'], 'recordFrame': ST + b['rec']} for b in P['beeps']], 'beeps')
        for m in made: m.SetProperty('AudioVolume', P['beep_db'])
        log['beeps'] = len(made)
    pm.SaveProject(); result = log
if STEP == 'hookfit':
    h = P['hook']; outdir = f'{WORK}/edit/{P["short"]}/stills'; os.makedirs(outdir, exist_ok=True)
    hk = [it for it in (tl.GetItemListInTrack('video', VT['Hook']) or []) if it.GetStart() - ST == h['rec']]; assert hk, 'no hook clip'
    tp = [t for t in hk[0].GetFusionCompByIndex(1).GetToolList(False).values() if t.ID == 'TextPlus'][0]
    def frame(tag):
        project.SetCurrentRenderFormatAndCodec('jpg', 'YUV420_8')
        project.SetRenderSettings({'SelectAllFrames': False, 'MarkIn': ST + h['rec'] + 12, 'MarkOut': ST + h['rec'] + 12, 'TargetDir': outdir, 'CustomName': tag, 'ExportVideo': True, 'ExportAudio': False, 'FormatWidth': 1080, 'FormatHeight': 1920})
        jid = project.AddRenderJob(); project.StartRendering([jid], isInteractiveMode=False); t0 = time.time()
        while project.IsRenderingInProgress() and time.time() - t0 < 60: time.sleep(0.25)
        project.DeleteRenderJob(jid); f = sorted(glob.glob(f'{outdir}/{tag}*'), key=os.path.getmtime)[-1]
        r = subprocess.run(['python3', os.path.expanduser('~/.claude/skills/CWC_PodReels/scripts/measure_box.py'), f, str(h['hook_px'])], capture_output=True, text=True).stdout.split()
        return (f, [int(v) for v in r]) if r and r[0] != 'none' else (f, None)
    size0 = float(tp.GetInput('Size', 0) or STY['hook'].get('Size', 0.1)); f, box = frame('hook_measure'); steps = []
    for _ in range(3):
        if not box: break
        w = box[1] - box[0]; steps.append({'size': round(size0, 4), 'box': box})
        if abs(w - 940) <= 12: break
        size0 = round(size0 * 940.0 / w, 4); tp.SetInput('Size', size0, 0); f, box = frame('hook_measure')
    cap = h.get('caption_px'); moved = 0; above = cap is not None and h['hook_px'] < cap      # a 3-stack opening puts the hook ABOVE the captions (edit-shorts bands)
    s_top, s_bot = P.get('safe') or [150, 1700]                                                  # a COVER plan sets the IG / TikTok grid band (264-1656); a short keeps the feed limits
    if box and cap is not None and not above and box[2] < cap + 50:
        shift = min(cap + 50 - box[2], max(0, s_bot - box[3])); cy = tp.GetInput('Center', 0); tp.SetInput('Center', {1: 0.5, 2: cy[2] - shift / 1920.0, 3: 0.0}, 0); moved = shift; f, box = frame('hook_measure')
    if box and (box[3] > s_bot or box[2] < s_top):                                               # outside the band: pull it back in (the gate below still reports the final box)
        shift = (s_bot - box[3]) if box[3] > s_bot else (s_top - box[2]); cy = tp.GetInput('Center', 0); tp.SetInput('Center', {1: 0.5, 2: cy[2] - shift / 1920.0, 3: 0.0}, 0); moved += shift; f, box = frame('hook_measure')
    tp = None; hk = None
    os.replace(f, f'{outdir}/hook_placement.jpg'); [os.remove(x) for x in glob.glob(f'{outdir}/hook_measure*')]
    pm.SaveProject(); result = dict(log, steps=steps, size=size0, box=box, caption_px=cap, moved_down=moved, clear=bool(box and (cap is None or (box[3] <= cap - 45 if above else box[2] >= cap + 45))), inside_safe=bool(box and box[3] <= s_bot and box[2] >= s_top), safe=[s_top, s_bot], hook_above_captions=above, frame=f'{outdir}/hook_placement.jpg')
if STEP == 'verify':
    bad = []; got = {}
    for kind, names in (('video', P['tracks']['video']), ('audio', P['tracks']['audio'])):
        for i, n in enumerate(names):
            rows = [[it.GetStart() - ST, it.GetDuration(), bool(it.GetClipEnabled()), (it.GetMediaPoolItem().GetClipProperty('File Path') if it.GetMediaPoolItem() else None), it.GetSourceStartFrame()] for it in tl.GetItemListInTrack(kind, i + 1) or []]
            got[f'{kind}:{i + 1}'] = rows
            want = sorted([x for x in P['items'] if x['kind'] == kind and x['track'] == i + 1], key=lambda x: x['rec'])
            if kind == 'video' and n in ('Tags', 'B-roll', 'Captions', 'Hook', 'Program') and not want or kind == 'audio' and n in ('Music', 'SFX', 'Meme'): continue
            if len(rows) != len(want): bad.append(f'{kind} {i + 1} {n}: {len(rows)} items, plan has {len(want)}'); continue
            for r, x in zip(rows, want):
                if r[3] != P['media'].get(x['clip']): bad.append(f'{kind} {i + 1} {n} at {x["rec"]}: WRONG MEDIA {r[3]} (plan {P["media"].get(x["clip"])})'); break
                if r[0] != x['rec'] or r[1] != x['src_out'] - x['src_in'] or r[2] != x['enabled'] or abs(r[4] - x['src_in']) > 1:
                    bad.append(f'{kind} {i + 1} {n} at {x["rec"]}: is {r[:3] + [r[4]]}, plan {[x["rec"], x["src_out"] - x["src_in"], x["enabled"], x["src_in"]]}')
                    if len(bad) > 12: break
    if not all(r[2] for r in got['audio:1']): bad.append('a program-audio clip on A1 is disabled')
    for i, n in enumerate(P['tracks']['audio']):
        if n in P['camera_tracks'] and any(r[2] for r in got[f'audio:{i + 1}']): bad.append(f'ISO audio on A{i + 1} {n} is enabled')
    frames = tl.GetEndFrame() - ST
    if frames != P['frames']: bad.append(f'timeline is {frames} frames, plan {P["frames"]}')
    if len(got[f'video:{VT["Captions"]}']) != len(P['captions']): bad.append(f'{len(got["video:%d" % VT["Captions"]])} caption clips, plan {len(P["captions"])}')
    if len(got[f'video:{VT["Hook"]}']) != 1: bad.append('the hook clip is missing')
    if sorted([r[0], r[1]] for r in got[f'video:{VT["B-roll"]}']) != sorted([b['rec'], b['frames']] for b in P['broll']): bad.append('b-roll on the timeline is not the plan')
    if len(got[f'video:{VT["Tags"]}']) != len(P['tags']): bad.append('name tag count')
    if sorted([r[0], r[1]] for r in got[f'audio:{AT["SFX"]}']) != sorted([b['rec'], b['frames']] for b in P['beeps']): bad.append('beeps on SFX are not the plan')
    log.update({'problems': bad, 'frames': frames, 'counts': {k: len(v) for k, v in got.items()}})
    if not bad:
        tl.AddMarker(0, 'Red', 'DRAFT', f'CWC_PodReels {P["short"]} v{P["v"]} - review on Telegram', 1, 'cwc-podreels')
        assert tl.SetName(FINAL), 'rename failed'; log['name'] = FINAL
    pm.SaveProject(); result = log
