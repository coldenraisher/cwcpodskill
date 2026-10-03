"""build.py <WORK> <theme id> [--channel cwc|tcl] [--plan-only]
One approved theme -> a clip timeline in Resolve, as a NEW VERSION (never replacing one):
  cut.py (the edit plan)  ->  eyes for every punched shot  ->  <WORK>/edit/<id>/build.<channel>.vN.json  ->  Resolve
  (r_build.py through rs.py: create from the EMPTY template, place every camera under every shot, stinger, name tag,
  censor, the Colden ending, verify, rename `zz BUILDING ...` -> `Ep NN Cxx <Title> <CH> vN`, red DRAFT marker).
The timeline keeps the PodCut structure: V1 Program + one track per camera, cut on the same boundaries, exactly ONE
enabled camera per piece (the others are there, disabled, so Colden can flip a shot); A1 "Main Pod Audio" = the program
mix through HIS Fairlight strip (ruling 27), ISO audio present and disabled after the Music / SFX / Meme tracks.
GATES: THE SOURCE GATE first, every time (Colden 2026-10-01): each clip resolves to ONE media-pool item with the plan's
file path, camera files sit inside this episode's folder and are the ones the locked PodCut uses - before anything is
created; and VERIFY re-reads the path of every placed piece. cut.py clean (exit 1 / 2 pass through); a punched shot with no face found is refused (never a centre zoom);
a missing asset or name-tag file stops the run; r_build's verify must report 0 problems or the timeline keeps its
`zz BUILDING` name and nothing is recorded. Never run while Colden is working in Resolve (it switches his timeline)."""
import os, re, sys, json, subprocess
import common as C, themes as T, cut as K, eyes as EY, broll as BR

HERE = os.path.dirname(os.path.abspath(__file__))
def rs(script, seconds, **kw):
    cmd = [sys.executable, f'{HERE}/rs.py', str(seconds), f'{HERE}/{script}'] + [f'{k}={json.dumps(v)}' for k, v in kw.items()]
    out = subprocess.run(cmd, capture_output=True, text=True).stdout.strip().splitlines()
    r = json.loads(out[-1]) if out else {'error': 'no answer from Resolve'}
    if isinstance(r, dict) and r.get('error'): C.fail(f'Resolve ({script} {kw.get("STEP", "")}): {r["error"]}\n{r.get("trace", "")}')
    return r

def pieces(items, a, b):
    """the PodCut items of one track that cover [a, b) -> [(piece_a, piece_b, clip, src_in)]"""
    out = []
    for t0, t1, s0, s1, en, name in items:
        if t1 <= a: continue
        if t0 >= b: break
        pa, pb = max(a, t0), min(b, t1); out.append((pa, pb, name, s0 + (pa - t0)))
    return out

def plan(work, tid, channel=None):
    W = T.Work(work); ep = W.ep; cut = K.build(work, tid, channel); K.report(cut)
    if cut['problems']: C.fail('the edit plan has problems - nothing is built')
    if cut['ask']: C.ask('; '.join(cut['ask']))
    if cut['stats'].get('pause_trims_without_audio_check'): C.fail(f'{cut["stats"]["pause_trims_without_audio_check"]} pause trim(s) could not be checked against the program audio (numpy / ffmpeg missing, or the program file is not on disk - NAS mounted?) - an unverified trim is never built')
    channel = cut['channel']; E = K.cfg(); fps = cut['fps']; snap = ep['snapshot']; dump = C.load(f'{snap}/pod_dump.json'); m = C.load(f'{ep["podcut_cache"]}/manifest.json')
    assets = C.load(f'{W.work}/edit/assets.json')
    if not assets: C.fail('no edit/assets.json - run the asset survey first (build.py does it when Resolve is reachable)')
    vt = {v['name']: (k, v['items']) for k, v in dump['tracks'].items() if k.startswith('V') and v['name'] != 'Lower Thirds'}
    at = {v['name']: (k, v['items']) for k, v in dump['tracks'].items() if k.startswith('A')}
    cams = [n for n in vt if n != 'Program']; cam_path = {c['name']: c['path'] for c in m['cameras'] if c['role'] == 'speaker'}
    tracks = {'video': ['Program'] + cams + ['Tags', 'B-roll', 'Intro-Outro'], 'audio': ['Main Pod Audio', 'Music', 'SFX', 'Meme'] + cams}
    top = max(int(c.get('height') or 0) for c in m['cameras']); out_res = [3840, 2160] if top >= 2160 else [1920, 1080]     # ruling 25
    FW, FH = 3840, 2160; items = []; Z = E['punch']; no_face = []
    for s in cut['shots']:
        track_of_cam = 'Program' if s['cam'] == 'WIDE' else s['cam']; props = None
        if s['punch']:
            src = pieces(vt[track_of_cam][1], s['a'], s['b']); n0 = src[0][3]; span = s['b'] - s['a']
            eye = EY.eye_point(cam_path[s['cam']], [n0 + int(q * span) for q in (0.2, 0.5, 0.8)], fps, f'{W.work}/edit/{tid}/eyes')
            if not eye: no_face.append(f'{s["cam"]} at {C.clock(s["rec"] / fps)}')
            else: props = {k: float(v) for k, v in EY.punch_props(eye, Z, FW, FH).items()}
        for ti, name in enumerate(tracks['video'][:1 + len(cams)]):
            for pa, pb, clip, sin in pieces(vt[name][1], s['a'], s['b']):
                on = name == track_of_cam
                items.append({'kind': 'video', 'track': ti + 1, 'clip': clip, 'src_in': sin, 'src_out': sin + (pb - pa), 'rec': s['rec'] + pa - s['a'], 'enabled': on, 'props': props if on else None})
        for pa, pb, clip, sin in pieces(at['Program'][1], s['a'], s['b']):
            items.append({'kind': 'audio', 'track': 1, 'clip': clip, 'src_in': sin, 'src_out': sin + (pb - pa), 'rec': s['rec'] + pa - s['a'], 'enabled': True})
        for ci, name in enumerate(cams):
            for pa, pb, clip, sin in pieces(at[name][1], s['a'], s['b']):
                items.append({'kind': 'audio', 'track': 5 + ci, 'clip': clip, 'src_in': sin, 'src_out': sin + (pb - pa), 'rec': s['rec'] + pa - s['a'], 'enabled': False})
    if no_face: C.fail(f'no face found for the punch-in on {no_face} - a punch never falls back to a centre zoom; look at edit/{tid}/eyes and fix the plan')
    for c in cut['censor']:                                   # duck the program under each beep: A1 is split at the window, nothing is removed
        r0, r1 = c['rec'], c['rec'] + c['frames']; new = []
        for x in items:
            if x['kind'] == 'audio' and x['track'] == 1 and x['rec'] < r1 and x['rec'] + x['src_out'] - x['src_in'] > r0:
                e = x['rec'] + x['src_out'] - x['src_in']
                for a, b, vol in ((x['rec'], max(x['rec'], r0), None), (max(x['rec'], r0), min(e, r1), -40.0), (min(e, r1), e, None)):
                    if b > a: new.append(dict(x, rec=a, src_in=x['src_in'] + a - x['rec'], src_out=x['src_in'] + b - x['rec'], volume=vol))
            else: new.append(x)
        items = new
    st = cut['stinger']; sa = assets['assets'].get(st['clip'])
    if not sa: C.fail(f'the stinger {st["clip"]!r} is not in the media pool')
    sfps = float(sa['fps']); stinger = {'clip': st['clip'], 'rec': st['rec'], 'fade_frames': st['fade_frames'], 'src_video_end': int(round((st['video_frames'] + st['fade_frames']) / fps * sfps)), 'src_audio_end': int(sa['frames'])}
    lt = C.load(f'{snap}/lower_thirds.json') or {}; tags = []
    for t in cut['tags']:
        f = ((lt.get('guests') or {}).get(t['who']) or {}).get('file')
        if not f or not os.path.exists(f): C.ask(f'no name-tag file for {t["who"]} ({f}) - the PodCut makes it from the guest\'s YouTube channel; it is missing')
        tags.append({'who': t['who'], 'file': f, 'rec': t['rec'], 'frames': min(t['frames'], int(round(E['tag']['seconds'] * fps))), 'fade_frames': t['fade_frames']})
    # ---- b-roll (ruling 33: part of every v1). edit/<id>/broll.json, written in producer mode: real material first.
    spec = C.load(f'{W.work}/edit/{tid}/broll.json')
    if spec is None: C.fail(f'no edit/{tid}/broll.json - a v1 carries b-roll (Colden 2026-10-01: "include b-roll into V1\'s moving forward"). Write it: {{"items": [{{"src": "<16:9 image>", "origin": "<url>", "anchor": {{"phrase": "P0000", "word": 0}}, "seconds": 5, "move": "push", "why": "...", "looked": "<what the capture shows>"}}]}}  (SKILL.md Stage 2 step 2)')
    if not spec.get('items') and len(str(spec.get('waiver', ''))) < 10: C.fail('broll.json has no items: add them, or "waiver": "<Colden\'s words>" for a clip that gets none')
    B = E['broll']; edge = B['edge_frames']; body = [s for s in cut['shots'] if s['kind'] == 'body']; cuts = sorted({s['rec'] for s in body} | {s['rec'] + s['b'] - s['a'] for s in body})
    def snap(f, forward):
        near = [c for c in cuts if abs(c - f) < edge]
        return (max(near) if forward else min(near)) if near else f
    brolls = []; ep_dir = ep['dir']; bdir = f'{ep_dir}/Clips/B-Roll'
    for it in spec.get('items', []):
        for k, n_ in (('origin', 8), ('why', 10), ('looked', 20)):       # producer mode is attested: where it is from, why here, what the capture SHOWS (you looked at it)
            if len(str(it.get(k, ''))) < n_: C.fail(f'b-roll {os.path.basename(str(it.get("src")))}: "{k}" is missing - every item needs "origin" (url / where from), "why" (what it explains here) and "looked" (what the capture shows: no 404 / consent wall / bot check, and that it agrees with what is said - numbers, names)')
        if not str(it.get('src', '')).lower().endswith(('.png', '.jpg', '.jpeg')): C.fail(f'b-roll {it.get("src")}: the source must be a still image (png / jpg) - video b-roll is not built; ask Colden')
        ph = W.by.get(it['anchor']['phrase'])
        if not ph: C.fail(f'b-roll {it.get("src")}: its anchor phrase {it["anchor"].get("phrase")} is not in this episode')
        if not os.path.exists(it['src']):
            went = [m[1] for cl in ((C.load(f'{W.work}/lock.json') or {}).get('cleanups') or []) for m in cl.get('files_moved', []) if os.path.basename(m[0]) == 'Source' or m[0] == it['src']]
            C.fail(f'b-roll source missing: {it["src"]}' + (f'\n  the lock cleanup moved the b-roll captures to the Trash - move the Source folder back first: {went[-1]}' if went else '\n  capture it again (capture.py -> LOOK -> broll.py prep)'))
        f0 = int(round(ph['w'][it['anchor'].get('word', 0)][1] * fps)); sh = next((s for s in body if s['a'] <= f0 < s['b']), None)
        if not sh: C.fail(f'b-roll "{os.path.basename(it["src"])}": its anchor word ({it["anchor"]}) is not in the body of this cut')
        r0 = snap(sh['rec'] + f0 - sh['a'], False); r1 = snap(r0 + int(round(it.get('seconds', B['default_s']) * fps)), True)
        if r1 - r0 < int(B['min_s'] * fps): C.fail(f'b-roll "{os.path.basename(it["src"])}" would run {(r1 - r0) / fps:.1f} s (minimum {B["min_s"]} s)')
        if r0 < cut['anchors']['body_start']: C.fail(f'b-roll "{os.path.basename(it["src"])}" starts in the cold open / stinger')
        if r1 > cut['anchors']['C'] - int(B['not_in_last_s'] * fps): C.fail(f'b-roll "{os.path.basename(it["src"])}" covers the last {B["not_in_last_s"]} s - the payoff shows the speaker')
        for t in cut['tags']:
            if r0 < t['rec'] + t['frames'] and r1 > t['rec']: C.fail(f'b-roll "{os.path.basename(it["src"])}" would cover the name tag at {C.clock(t["rec"] / fps)}')
        for x in brolls:
            if r0 < x['rec'] + x['frames'] and r1 > x['rec']: C.fail(f'two b-rolls overlap at {C.clock(r0 / fps)}')
        clip = BR.render(it['src'], bdir, (r1 - r0) / fps, it.get('move', 'push'), tuple(out_res), int(round(fps)))
        brolls.append({'file': clip, 'rec': r0, 'frames': r1 - r0, 'origin': it.get('origin'), 'why': it.get('why'), 'at': C.clock(r0 / fps)})
    k30 = fps / 30.0; last = cut['shots'][-1]; lc = 'Program' if last['cam'] == 'WIDE' else last['cam']
    tail = pieces(vt[lc][1], last['a'], last['b']); lp = list(tail[-1])          # the copy that carries the glitch transition: the last
    for q in tail[-2::-1]:                                                       # source-continuous second and a half of the last shot
        if lp[1] - lp[0] >= int(1.5 * fps) or q[2] != lp[2] or q[3] + (q[1] - q[0]) != lp[3]: break
        lp = [q[0], lp[1], q[2], q[3]]
    if lp[1] - lp[0] > int(1.5 * fps): cutf = lp[1] - int(1.5 * fps); lp = [cutf, lp[1], lp[2], lp[3] + cutf - lp[0]]
    if lp[1] - lp[0] < 8: C.fail(f'the last shot gives only {lp[1] - lp[0]} continuous frames for the ending transition - end the theme a little later or earlier')
    lprops = next((x['props'] for x in items if x['kind'] == 'video' and x['enabled'] and x['rec'] <= last['rec'] + lp[0] - last['a'] < x['rec'] + x['src_out'] - x['src_in']), None)
    outro = {'C': cut['anchors']['C'], 'last_shot': {'clip': lp[2], 'src_in': lp[3], 'src_out': lp[3] + lp[1] - lp[0], 'rec': last['rec'] + lp[0] - last['a'], 'props': lprops},
             'end_screen_clip': 'CR End Screen .mov', 'end_screen_src_in': 7, 'end_screen_frames': cut['outro']['end_screen_frames'],
             'music_clip': 'Heavy Riff (1 ).mp3', 'music_src_in': int(round(1724 * k30)), 'music_pre_frames': cut['anchors']['C'] - cut['outro']['music_rec'], 'music_fade_in_frames': int(round(170 * k30)),
             'music_db_before': E['outro']['music_db_before'], 'music_db_after': E['outro']['music_db_after'],
             'sfx_clip': 'CR Endscreen Glitch, whoosh, transition, hit.png.wav', 'sfx_frames': int(round(291 * k30)), 'sfx_hit_frame': cut['anchors']['C'] - cut['outro']['sfx_rec'], 'sfx_db': E['outro']['sfx_db'],
             'transition': E['outro']['transition'], 'transition_frames': int(round(E['outro']['transition_frames_30'] * k30))}
    for n in (outro['end_screen_clip'], outro['music_clip'], outro['sfx_clip']):
        if not assets['assets'].get(n): C.fail(f'{n!r} is not in the media pool')
    B = E['beep']; beeps = []                                # the Power Bin beep (Colden 2026-10-02), tiled over each censor window
    if cut['censor']:
        if not os.path.exists(B['path']): C.fail(f'the censor beep {B["path"]} is not on disk')
        bd = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', B['path']], capture_output=True, text=True).stdout.strip() or 0)
        piece = max(1, int(bd * fps))                         # whole frames the wav can fill at THIS frame rate (3 at 30 fps, 2 at 24)
        hit = (outro['C'] - outro['sfx_hit_frame'], outro['C'] - outro['sfx_hit_frame'] + outro['sfx_frames'])      # the ending hit sits on SFX too
    for c in cut['censor']:
        f = c['rec']
        while f < c['rec'] + c['frames']:
            n_ = min(piece, c['rec'] + c['frames'] - f); beeps.append({'rec': f, 'frames': n_, 'track': 'Meme' if f < hit[1] and f + n_ > hit[0] else 'SFX'}); f += n_
    vers = C.load(f'{W.work}/edit/{tid}/versions.json', []); v = 1 + max([x['v'] for x in vers if x['channel'] == channel] or [0])      # failed builds keep their number (their zz BUILDING timeline stays in the bin)
    th = next(t for t in W.themes()['themes'] if t['id'] == tid); title = re.sub(r'[^A-Za-z0-9 ]', '', th['slug'].replace('-', ' ')).title()
    name = f'Ep {ep["ep_no"]} C{tid[1:]} {title} {channel.upper()} v{v}'
    media = {os.path.basename(c['path']): c['path'] for c in m['cameras']}                       # camera clips: the episode's own files, by path
    for n_, a_ in assets['assets'].items():
        if a_: media[n_] = a_['path']
    if beeps: media[B['clip']] = B['path']                   # by its path: build.py imports it into Master when the pool lacks it
    used = {x['clip'] for x in items} | {stinger['clip'], outro['end_screen_clip'], outro['music_clip'], outro['sfx_clip'], outro['last_shot']['clip']} | ({B['clip']} if beeps else set())
    miss = [u for u in used if u not in media]
    if miss: C.fail(f'no file path known for {miss} - a clip is never looked up by name alone')
    for c in m['cameras']:                                     # SOURCE GATE, offline half: the episode's own files, on disk
        if not c['path'].startswith(ep['dir'].rstrip('/') + '/'): C.fail(f'SOURCE GATE: camera file {c["path"]} is not inside this episode\'s folder {ep["dir"]}')
        if not os.path.exists(c['path']): C.fail(f'SOURCE GATE: {c["path"]} is not on disk (NAS mounted?)')
    P = {'theme': tid, 'channel': channel, 'version': f'v{v}', 'media': media, 'pod': ep['cut'], 'sources_used': sorted(used), 'v': v, 'name': name, 'building': 'zz BUILDING ' + name, 'template': '00 PodClips Template', 'project': ep['project'], 'bin': ep['bin'],
         'clips_bin': f'Master/{ep["bin"]}/Clips', 'fps': fps, 'timeline_res': [FW, FH], 'output_res': out_res, 'frames': cut['frames'], 'tracks': tracks, 'camera_tracks': ['Program'] + cams,
         'items': sorted(items, key=lambda x: (x['kind'], x['track'], x['rec'])), 'stinger': stinger, 'tags': tags, 'broll': brolls, 'broll_waiver': spec.get('waiver'), 'censor': cut['censor'], 'beep': B['clip'], 'beep_db': B['db'], 'beeps': beeps, 'outro': outro,
         'written_trims': [{'section': t['section'], 'words': t['why'].split(': ', 1)[-1][:60]} for t in cut['trims'] if t.get('kept') and t['kind'] == 'written'],
         'soft_swears': cut.get('soft_swears_to_listen') or [], 'cold_open_waiver': th.get('cold_open_waiver') if cut['anchors']['hook_end'] / fps > E['cold_open_max'] else None,
         'cut_sha': C.sha_text(json.dumps(cut['shots'], sort_keys=True)), 'made_at': C.now(), 'shots': cut['shots'], 'anchors': cut['anchors'],
         'edit_sha': C.sha_text(json.dumps([[x['kind'], x['a'], x['b'], x['cam'], x['punch']] for x in cut['shots']] + [[b['file'], b['frames']] for b in brolls]))}     # the same edit whatever the channel's stinger
    path = f'{W.work}/edit/{tid}/build.{channel}.v{v}.json'; C.save(path, P); return P, path, cut

if __name__ == '__main__':
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    if len(a) < 2: C.fail(__doc__)
    ch = sys.argv[sys.argv.index('--channel') + 1] if '--channel' in sys.argv else None
    if ch in a: a.remove(ch)
    work, tid = os.path.abspath(a[0]), a[1]; ep = C.episode(work)
    if not os.path.exists(f'{work}/edit/assets.json'):
        names = ['CR Stinger INtro 5 s.mov', 'The Creative Lens Stinger.mov', 'CR End Screen .mov', 'Heavy Riff (1 ).mp3', 'CR Endscreen Glitch, whoosh, transition, hit.png.wav']
        C.save(f'{work}/edit/assets.json', rs('r_assets.py', 120, PROJECT=ep['project'], POD=ep['cut'], TEMPLATE='00 PodClips Template', NAMES=names))
    P, path, cut = plan(work, tid, ch)
    n = {k: sum(1 for x in P['items'] if x['kind'] == k) for k in ('video', 'audio')}
    print(f'\nbuild plan {P["name"]}: {n["video"]} video + {n["audio"]} audio pieces, {sum(1 for x in P["items"] if x.get("props"))} punched, b-roll {[b["at"] for b in P["broll"]]}, output {P["output_res"][0]}x{P["output_res"][1]}\n  {path}')
    if '--plan-only' in sys.argv: sys.exit(0)
    kw = {'PROJECT': P['project'], 'PLAN': path}
    def record(status, **more):
        vers = C.load(f'{work}/edit/{tid}/versions.json', []); row = next((x for x in vers if x['v'] == P['v'] and x['channel'] == P['channel']), None)
        if row is None: row = {'v': P['v'], 'channel': P['channel'], 'timeline': P['name'], 'plan': path, 'edit_sha': P['edit_sha']}; vers.append(row)
        row.update(dict(more, status=status)); C.save(f'{work}/edit/{tid}/versions.json', vers)
    if P.get('beeps'):
        r = rs('r_build.py', 120, STEP='import', **kw)
        if r.get('imported'): print(f'  imported into Master: {r["imported"]}')
    r = rs('r_build.py', 120, STEP='sources', **kw)
    if r['problems']:
        print('  SOURCE GATE FAILED - nothing was created:'); [print('   ', x) for x in r['problems']]; sys.exit(1)
    print('  SOURCE GATE ok: ' + '; '.join(f'{n} <- {v["bin"]}' + (f' (1 of {v["same_name_in_pool"]} clips with that name)' if v['same_name_in_pool'] > 1 else '') for n, v in r['sources'].items()))
    record('building', started_at=C.now())                 # from here the number is taken, whatever happens
    r = rs('r_build.py', 180, STEP='create', **kw); print('  create:', r['video'], r['audio'], r['res'], r['fps'])
    for k in ('video', 'audio'):
        for t in sorted({x['track'] for x in P['items'] if x['kind'] == k}):
            r = rs('r_build.py', 300, STEP='place', KIND=k, TRACK=t, **kw); print(f'  {k} {t}: placed {r["placed"]}, disabled {r["disabled"]}, punched {r["with_props"]}')
    r = rs('r_build.py', 180, STEP='extras', **kw); print('  extras:', {k: r.get(k) for k in ('stinger_video', 'stinger_audio', 'tags', 'broll', 'censor', 'transition', 'transition_error') if r.get(k) is not None})
    r = rs('r_build.py', 180, STEP='verify', **kw)
    if r['problems']:
        record('failed', problems=r['problems'], timeline='zz BUILDING ' + P['name'])
        print('  VERIFY FAILED - the timeline keeps its zz BUILDING name:'); [print('   ', p) for p in r['problems']]; sys.exit(1)
    if r.get('src_off_by_one'): print(f'  note: {len(r["src_off_by_one"])} piece(s) read back one source frame off (within the PodCut tolerance): {r["src_off_by_one"][:6]}')
    same = next((x for x in C.load(f'{work}/edit/{tid}/versions.json', []) if str(x.get('status', '')).startswith('approved') and P['channel'] in (x.get('channels') or []) and x.get('edit_sha') == P['edit_sha'] and x['channel'] != P['channel']), None)
    record('approved' if same else 'draft', frames=r['frames'], built_at=C.now(), src_off_by_one=len(r.get('src_off_by_one') or []),
           **({'channels': [P['channel']], 'approved_via': f'{same["channel"]} v{same["v"]} (the same edit, approved for this channel too)'} if same else {}))
    print(f'  VERIFIED: {P["name"]} - {r["frames"]} frames ({C.mmss(r["frames"] / P["fps"])}), {r["counts"]}' + (f' - approved via {same["channel"]} v{same["v"]}' if same else ''))
