"""plan.py <WORK> <short id>   ->  <WORK>/edit/<id>/build.vN.json   (the offline half of a build; build.py runs it)
cut.json (the edit) + faces.json (one fixed crop per person) + broll.json -> every item Resolve will place:
LAYOUTS (1080x1920, edit-shorts' measured transform maths, references in edit-shorts resolve.md):
  single   the PodCut shows one person -> that person's camera, full height, face-centred (one fixed crop per person)
  stack    the PodCut shows the wide -> 3 people: three 640 px panels, the TALKER in the centre, the others top / bottom
           in cast order; 2 people: Colden top, the other bottom (edit-shorts 2026-09-11)
  share    a screen share inside the short -> STOP AND ASK (not built yet; no Ep 24 short has one)
CAPTIONS  phrase pop <= 4 words / <= 22 chars, ALL CAPS, Colden's Text+ style (references/text_styles.json), placed by
          layout so faces stay clear, STEADY while b-roll covers the frame; a listener's 1-2 word backchannel is not
          captioned; swears are shown masked (S***) under their beep; spellings from the show file + the theme's `fix`.
HOOK      the theme's hook_text (1-2 lines) in his white box (Acumin), frames 0-75, 9-frame fade; the builder sizes it to
          940 px and checks it on a rendered frame.
TAG       guests only, white card with the YouTube avatar + handle, top-left of the guest's panel, ~3 s, after the hook.
B-ROLL    edit/<id>/broll.json (producer mode, real material first): every still is rendered FULL FRAME 1080x1920 with an
          eased move (broll.py); edges on a cut or >= 15 frames clear; never in the hook window or the last 1.5 s; never
          over the tag; every splice cut.py could not hide with a layout change must sit under a b-roll.
AUDIO     A1 "Main Pod Audio" = the PodCut's program mix, cut as given (the template's A1 carries Colden's strip); ISO
          audio on its own tracks, every clip DISABLED; censor = Power Bin beep pieces on SFX + A1 ducked -40 dB.
GATES (exit 1): a share layout; a missing face; b-roll not 1080x1920 / outside the rules; a needs-b-roll splice left
uncovered; no broll.json and no waiver in Colden's words; a camera file outside this episode's folder."""
import os, re, sys, json, bisect, subprocess, random
import common as C, themes as T, cut as K, faces as FA
TW, TH = 1080, 1920
HERE = os.path.dirname(os.path.abspath(__file__))

def fit(p, W, H):
    """INTENDED units (scale = px per source px, Pan = shift_x * 1080 / SW, Tilt = -shift_y * 1920 / SH). Resolve's own
    units depend on the TIMELINE's input-resolution-mismatch setting (measured 2026-10-02: `00 PodReels Template` is
    centerCrop = no pre-scale; edit-shorts measured scale-to-fill on 2026-09-22), so r_build.py divides by the base of
    the timeline it builds on - never assumed here."""
    return dict(p, sw=W, sh=H)
def single(f):
    W, H = f['w'], f['h']; z = TH / H; shift = -(f['cx'] - W / 2) * z; lim = (W * z - TW) / 2; shift = max(-lim, min(lim, shift))
    face_bottom = TH / 2 + (f['cy'] - H / 2 + f['fh'] / 2) * z
    return fit({'ZoomX': z, 'ZoomY': z, 'Pan': shift * TW / W, 'Tilt': 0.0, 'CroppingEnabled': False, 'CropLeft': 0.0, 'CropRight': 0.0}, W, H), face_bottom
def panel(f, k, ph):
    W, H = f['w'], f['h']; z = ph / H; vis = TW / z; left = max(0, min(W - vis, f['cx'] - vis / 2)); wc = left + vis / 2
    shift_x = -(wc - W / 2) * z; shift_y = (ph / 2 + ph * k) - TH / 2
    return fit({'ZoomX': z, 'ZoomY': z, 'Pan': shift_x * TW / W, 'Tilt': -shift_y * TH / H, 'CroppingEnabled': True, 'CropLeft': float(left), 'CropRight': float(W - left - vis), 'CropRetain': False}, W, H)

def flashes(brolls, cuts, edge):
    """2026-09-13: every b-roll edge sits ON a cut / another b-roll's edge, or >= `edge` frames clear of one - else the
    viewer sees a few-frame flash of the shot in between (s15 2026-10-02: a 1-frame flash between two stills)"""
    out = []
    for b in brolls:
        a0, a1 = b['rec'], b['rec'] + b['frames']; others = [x for x in brolls if x is not b]
        before = [a0 - c for c in cuts + [x['rec'] + x['frames'] for x in others] if c <= a0]; after = [c - a1 for c in cuts + [x['rec'] for x in others] if c >= a1]
        for side, d in (('starts', min(before, default=None)), ('ends', min(after, default=None))):
            if d is not None and 0 < d < edge: out.append(f'b-roll "{os.path.basename(b["src"])}" {side} {d} frames from a cut (a {d}-frame flash) - move its anchor or length')
    return out
def pieces(items, a, b):
    out = []
    for t0, t1, s0, s1, en, name in items:
        if t1 <= a: continue
        if t0 >= b: break
        pa, pb = max(a, t0), min(b, t1); out.append((pa, pb, name, s0 + (pa - t0)))
    return out

def mask(t): return re.sub(r"[A-Za-z]+", lambda m: m.group(0)[0] + '*' * (len(m.group(0)) - 1), t)

def make(work, tid):
    W = T.Work(work); ep = W.ep; th = W.theme(tid); E = K.cfg(); B = E['bands']
    cut = C.load(f'{W.work}/edit/{tid}/cut.json')
    if not cut: C.fail(f'no edit/{tid}/cut.json - run cut.py first')
    if cut['problems']: C.fail(f'cut.json has problems: {cut["problems"]}')
    if cut['themes_sha'] != C.sha_file(W.themes_path): C.fail('themes.json changed after cut.py - run cut.py again')
    fps = cut['fps']; F = (C.load(f'{W.work}/edit/faces.json') or {}).get('faces') or FA.run(W.work)
    tracks, dump = FA.pod(ep); man = C.load(f'{ep["podcut_cache"]}/manifest.json')
    hosts = W.S['hosts']; order = [p['name'] for p in ep['people'] if p['host']]; order = sorted(order, key=lambda n: hosts.index(n) if n in hosts else 9) + [p['name'] for p in ep['people'] if not p['host']]
    NP = len(order); PANEL = TH // NP if NP in (2, 3) else None
    if NP not in (2, 3): C.ask(f'{NP} people on camera - the stack layout covers 2 or 3; a 4-person short needs Colden\'s layout first')
    X = K.Ctx(W, audio=False)
    for sp in X.specials:
        if any(s['a'] < sp[1] and s['b'] > sp[0] for s in cut['shots']): C.ask('this short contains a screen share - the vertical share layout is not built yet (edit-shorts had: talker top, share middle, others bottom). Ask Colden before building it.')
    VT = order + ['Program', 'Tags', 'B-roll', 'Captions', 'Hook']; AT = E['audio']['tracks'] + order
    items = []; runs = []
    for s in cut['shots']:
        who, _ = X.floor(s['a'], s['b'])
        if s['cam'] == 'WIDE':
            if NP == 3:
                talker = who if who in order else (runs[-1]['talker'] if runs else order[0]); others = [p for p in order if p != talker]
                place = [(others[0], panel(F[others[0]], 0, PANEL)), (talker, panel(F[talker], 1, PANEL)), (others[1], panel(F[others[1]], 2, PANEL))]
                key = f'stack:{talker}'; cap_y, hook_y = B['stack3_caption'], B['stack3_hook']
            else:
                talker = who; place = [(order[0], panel(F[order[0]], 0, PANEL)), (order[1], panel(F[order[1]], 1, PANEL))]
                key = 'stack2'; cap_y, hook_y = B['stack2_caption'], B['stack2_hook']
        else:
            if s['cam'] not in F: C.fail(f'no face data for {s["cam"]}')
            props, fb = single(F[s['cam']]); talker = s['cam']
            if s.get('punch'): props = dict(props, ZoomX=props['ZoomX'] * E['punch'], ZoomY=props['ZoomY'] * E['punch'])
            place = [(s['cam'], props)]; key = f'single:{s["cam"]}'
            cap_y = max(B['single_caption_min'], min(B['single_caption_max'], fb + B['single_below_face'])); hook_y = min(cap_y + B['hook_below_caption'], B['hook_max'])
        a = s['rec']; b = s['rec'] + s['b'] - s['a']
        for p, props in place:
            for pa, pb, clip, sin in pieces(tracks[p], s['a'], s['b']):
                items.append({'kind': 'video', 'track': VT.index(p) + 1, 'clip': clip, 'src_in': sin, 'src_out': sin + (pb - pa), 'rec': a + pa - s['a'], 'enabled': True, 'props': props, 'layout': key})
        for pa, pb, clip, sin in pieces(tracks['Program'], s['a'], s['b']):
            items.append({'kind': 'audio', 'track': 1, 'clip': clip, 'src_in': sin, 'src_out': sin + (pb - pa), 'rec': a + pa - s['a'], 'enabled': True})
        for p in order:
            for pa, pb, clip, sin in pieces(tracks[p], s['a'], s['b']):
                items.append({'kind': 'audio', 'track': AT.index(p) + 1, 'clip': clip, 'src_in': sin, 'src_out': sin + (pb - pa), 'rec': a + pa - s['a'], 'enabled': False})
        if runs and runs[-1]['key'] == key and runs[-1]['b'] == a: runs[-1]['b'] = b
        else: runs.append({'key': key, 'a': a, 'b': b, 'cap_y': cap_y, 'hook_y': hook_y, 'visible': [p for p, _ in place], 'talker': talker})
    total = cut['frames']
    # ---- b-roll (producer mode; Colden 2026-09-23: ALWAYS full frame)
    spec = C.load(f'{W.work}/edit/{tid}/broll.json')
    if spec is None: C.fail(f'no edit/{tid}/broll.json - every short carries b-roll (3-4) or a waiver in Colden\'s words: {{"items": [{{"src": "<image>", "origin": "<url>", "anchor": {{"phrase": "P0000", "word": 0}}, "seconds": 4, "move": "zoom_in", "why": "..."}}]}}')
    if not spec.get('items') and len(str(spec.get('waiver', ''))) < 10: C.fail('broll.json has no items and no waiver')
    BR = E['broll']; cuts = sorted({it['rec'] for it in items if it['kind'] == 'video'} | {it['rec'] + it['src_out'] - it['src_in'] for it in items if it['kind'] == 'video'})
    def snap(f, forward):
        near = [c for c in cuts if 0 < abs(c - f) < BR['edge_frames']]
        return (max(near) if forward else min(near)) if near else f
    def to_rec(f):
        for s in cut['shots']:
            if s['a'] <= f < s['b']: return s['rec'] + f - s['a']
        return None
    brolls = []; import broll as BRL; moves = ['zoom_in', 'pan_left', 'zoom_out', 'pan_right', 'pan_up', 'pan_down']; random.Random(tid).shuffle(moves); last_move = None
    for n, it in enumerate(spec.get('items', [])):
        ph = W.by.get(it['anchor']['phrase'])
        if not ph or not os.path.exists(it['src']): C.fail(f'b-roll {it.get("src")}: missing file or phrase')
        f0 = X.F(ph['w'][it['anchor'].get('word', 0)][1]); r0 = to_rec(f0)
        if r0 is None: C.fail(f'b-roll "{os.path.basename(it["src"])}": its anchor word is not in this cut')
        r0 = snap(max(r0, BR['not_in_hook_frames']), False); r1 = snap(r0 + int(round(float(it.get('seconds', BR['default_s'])) * fps)), True)
        r1 = min(r1, total - int(BR['not_in_last_s'] * fps))
        nxt = next((c for c in cuts if c >= r1), None)              # that clamp can land just before a cut: back off to 15 frames clear
        if nxt is not None and 0 < nxt - r1 < BR['edge_frames']: r1 = nxt - BR['edge_frames']
        if r0 < BR['not_in_hook_frames']: C.fail(f'b-roll "{os.path.basename(it["src"])}" starts in the hook window')
        if (r1 - r0) / fps < BR['min_s']: C.fail(f'b-roll "{os.path.basename(it["src"])}" would run {(r1 - r0) / fps:.1f} s (min {BR["min_s"]} s) - move its anchor')
        for x in brolls:
            if r0 < x['rec'] + x['frames'] and r1 > x['rec']: C.fail(f'two b-rolls overlap at {C.clock(r0 / fps)}')
        mv = it.get('move') or next(m for m in moves if m != last_move); last_move = mv
        clip = BRL.render(it['src'], f'{ep["shorts_dir"]}/B-Roll', (r1 - r0) / fps, mv, int(round(fps)), it.get('focus'))
        gap = {'prev': next((r0 - c for c in reversed(cuts) if c <= r0), None), 'next': next((c - r1 for c in cuts if c >= r1), None)}
        brolls.append({'file': clip, 'src': it['src'], 'rec': r0, 'frames': r1 - r0, 'move': mv, 'origin': it.get('origin'), 'why': it.get('why'), 'at': C.clock(r0 / fps), 'cut_gap': gap})
    for x in flashes(brolls, cuts, BR['edge_frames']): C.fail(x)
    for nb in cut['needs_broll']:
        if not any(b['rec'] <= nb['rec'] < b['rec'] + b['frames'] for b in brolls): C.fail(f'the splice at {nb["at"]} has no layout change to hide it and no b-roll over it - place one there (never a jump cut)')
    # ---- guest name tag
    tags = []; TG = E['tag']; lt = C.load(f'{ep["snapshot"]}/lower_thirds.json') or {}
    for g in [p for p in ep['people'] if not p['host']]:
        info = (lt.get('guests') or {}).get(g['name']) or {}
        said = sum(1 for s in cut['shots'] for w in X.words_in(s['a'], s['b']) if w['who'] == g['name'])
        if said < 6: continue
        if not info.get('avatar') or not info.get('handle') or not os.path.exists(info['avatar']): C.ask(f'no YouTube avatar / handle on file for {g["name"]} (lower_thirds.json) - never guessed')
        for r in runs:
            a_ = max(r['a'], TG['not_before_frames']); n_ = min(r['b'] - a_, int(TG['seconds'] * fps))
            if g['name'] not in r['visible'] or n_ < 24 or any(b['rec'] < a_ + n_ and b['rec'] + b['frames'] > a_ for b in brolls): continue
            k = r['visible'].index(g['name']) if r['key'].startswith('stack') else 0; y = (PANEL * k if r['key'].startswith('stack') else 0) + 35
            png = f'{ep["shorts_dir"]}/Assets/nametag/{g["name"]}_62_{y}.png'
            if not os.path.exists(os.path.splitext(png)[0] + '.mov'):
                os.makedirs(os.path.dirname(png), exist_ok=True)
                subprocess.run([sys.executable, f'{HERE}/nametag.py', info.get('name') or g['name'], info['handle'], info['avatar'], '62', str(y), png, str(TG['scale'])], check=True, capture_output=True)
            tags.append({'who': g['name'], 'file': os.path.splitext(png)[0] + '.mov', 'rec': a_, 'frames': n_, 'fade': TG['fade_frames']}); break
    # ---- captions (after b-roll: steady under a cover)
    fix = {k.lower(): v for k, v in list(W.S.get('spellings', {}).items()) + list((th.get('fix') or {}).items())}
    words = []; main = {}
    for s in cut['shots']:                                          # each section's MAIN speaker (most words over the whole section, not per shot:
        for w in X.words_in(s['a'], s['b']):                         # s14 2026-10-02 - a stretched one-word 'yes' won a 1 s shot and 'Regenerate.' was dropped)
            if s['a'] <= (w['a'] + w['b']) // 2 < s['b']: main.setdefault(s['range'], {}); main[s['range']][w['who']] = main[s['range']].get(w['who'], 0) + 1
    main = {k: max(v, key=v.get) for k, v in main.items()}
    for s in cut['shots']:
        ws = X.words_in(s['a'], s['b']); talker = main.get(s['range']) or X.floor(s['a'], s['b'])[0]
        for w in ws:
            mid = (w['a'] + w['b']) // 2
            if not (s['a'] <= mid < s['b']): continue
            ph = W.by[w['pid']]
            if w['who'] != talker and ph['n'] <= E['captions']['drop_backchannel_max_words']: continue
            t = w['t'].strip(); low = re.sub(r"[^a-z']", '', t.lower())
            if low in fix: t = re.sub(r"[A-Za-z']+", fix[low], t, count=1)
            if K.is_swear(E, t): t = mask(t)
            words.append({'t': t, 'rec': s['rec'] + max(w['a'], s['a']) - s['a'], 'end': s['rec'] + min(w['b'], s['b']) - s['a']})
    if cut.get('quiet_tail'): words = [w for w in words if (w['rec'] + w['end']) // 2 < cut['quiet_tail']['rec']]      # the muted tail is never captioned (by the word's middle: Whisper starts words early)
    words.sort(key=lambda w: w['rec'])
    merges = [(m[0].split(), m[1]) for m in W.S.get('caption_merges', [])]; i = 0; mw = []      # "FX three" -> FX3
    while i < len(words):
        hit = next(((n, rep) for n, rep in merges if [re.sub(r"[^a-z0-9]", '', x['t'].lower()) for x in words[i:i + len(n)]] == n), None)
        if hit: n, rep = hit; tail = re.sub(r"^[^.,?!:;]*", '', words[i + len(n) - 1]['t']); mw.append(dict(words[i], t=rep + tail, end=words[i + len(n) - 1]['end'])); i += len(n)
        else: mw.append(words[i]); i += 1
    words = mw; MAXC = E['captions']['max_chars']; MAXW = E['captions']['max_words']
    sents = []; cur = []                                                       # a caption never runs across a sentence end
    for w in words:
        cur.append(w)
        if w['t'].rstrip().endswith(('.', '?', '!')): sents.append(cur); cur = []
    if cur: sents.append(cur)
    from PIL import ImageFont
    ff = os.path.expanduser(E['captions']['font_file'])
    if not os.path.exists(ff): C.fail(f'the caption font is not on disk: {ff} (line widths are measured with it)')
    FNT = ImageFont.truetype(ff, 100); NW = FNT.getlength('N')
    def width(t): return FNT.getlength(t) + (len(t) - 1) * 0.127 * NW          # his CharacterSpacing 1.127
    def fits(ws):
        t = ' '.join(x['t'] for x in ws); return len(ws) <= MAXW and len(t) <= MAXC and width(t.upper()) <= E['captions']['max_width100']
    def split(ws):
        """the fewest lines that fit (<= 4 words, <= 22 chars - one line at Colden's caption size), then the most even
        ones: no 'PART.' orphan; a comma is a preferred break"""
        n = len(ws); best = {0: (0, 0.0, [])}
        for i in range(1, n + 1):
            for j in range(max(0, i - MAXW), i):
                if j in best and fits(ws[j:i]):
                    k, cost, cuts = best[j]; ln = len(' '.join(x['t'] for x in ws[j:i]))
                    c = cost + (MAXC - ln) ** 2 - (40 if ws[i - 1]['t'].rstrip().endswith((',', ':', ';')) and i < n else 0)
                    cand = (k + 1, c, cuts + [(j, i)])
                    if i not in best or cand[:2] < best[i][:2]: best[i] = cand
        if n not in best: return [ws[k:k + 1] for k in range(n)]
        return [ws[j:i] for j, i in best[n][2]]
    phr = [p for se in sents for p in split(se)]
    caps = []
    for i, p in enumerate(phr):
        st = p[0]['rec']; en = phr[i + 1][0]['rec'] if i + 1 < len(phr) else min(total, p[-1]['end'] + 6)
        caps.append({'start': st, 'end': max(st + 1, en), 'text': ' '.join(x['t'] for x in p).upper().strip(' ,')})
    cover = [(b['rec'], b['rec'] + b['frames']) for b in brolls]
    edges = sorted({e for a, b in cover for e in (a, b)}); cruns = []
    for r in runs:
        cs = [r['a']] + [e for e in edges if r['a'] < e < r['b']] + [r['b']]
        for a, b in zip(cs, cs[1:]):
            span = next(((ca, cb) for ca, cb in cover if ca <= a and b <= cb), None)
            src = next(x for x in runs if x['a'] <= span[0] < x['b']) if span else r
            if cruns and cruns[-1]['cap_y'] == src['cap_y'] and cruns[-1]['b'] == a: cruns[-1]['b'] = b
            else: cruns.append({'a': a, 'b': b, 'cap_y': src['cap_y']})
    captions = []
    for r in cruns:
        keys = []
        for i, c in enumerate(caps):
            if c['start'] >= r['b'] or c['end'] <= r['a']: continue
            keys.append((max(c['start'], r['a']) - r['a'], c['text']))
            nxt = caps[i + 1] if i + 1 < len(caps) else None
            if nxt is None or nxt['start'] > c['end']: keys.append((min(c['end'], r['b']) - r['a'], ''))
        if not keys: continue
        if keys[0][0] > 0: keys.insert(0, (0, ''))
        captions.append({'rec': r['a'], 'frames': r['b'] - r['a'], 'y': 1 - r['cap_y'] / TH, 'cap_px': r['cap_y'], 'keys': keys})
    hook = {'lines': [x.upper() for x in th['hook_text']], 'rec': 0, 'frames': E['hook_frames'], 'fade_out': E['hook_fade_frames'], 'y': 1 - runs[0]['hook_y'] / TH, 'hook_px': runs[0]['hook_y'],
            'caption_px': next((c['cap_px'] for c in captions if c['rec'] < E['hook_frames']), None)}
    # ---- censor
    bp = E['beep']; beeps = []
    if cut['censor'] and not os.path.exists(bp['path']): C.fail(f'the censor beep {bp["path"]} is not on disk')
    for c in cut['censor']:
        f = c['rec']
        while f < c['rec'] + c['frames']: n_ = min(bp['piece_frames'], c['rec'] + c['frames'] - f); beeps.append({'rec': f, 'frames': n_}); f += n_
        r0, r1 = c['rec'], c['rec'] + c['frames']; new = []
        for x in items:
            if x['kind'] == 'audio' and x['track'] == 1 and x['rec'] < r1 and x['rec'] + x['src_out'] - x['src_in'] > r0:
                e = x['rec'] + x['src_out'] - x['src_in']
                for a, b, vol in ((x['rec'], max(x['rec'], r0), None), (max(x['rec'], r0), min(e, r1), E['censor']['duck_db']), (min(e, r1), e, None)):
                    if b > a: new.append(dict(x, rec=a, src_in=x['src_in'] + a - x['rec'], src_out=x['src_in'] + b - x['rec'], volume=vol))
            else: new.append(x)
        items = new
    # ---- quiet tail (edit.json quiet_tail_rule): the picture holds past the payoff, A1 muted - the next word is never heard
    qt = cut.get('quiet_tail')
    if qt:
        r0, r1 = qt['rec'], qt['rec'] + qt['frames']; new = []
        for x in items:
            if x['kind'] == 'audio' and x['track'] == 1 and x['rec'] < r1 and x['rec'] + x['src_out'] - x['src_in'] > r0:
                e = x['rec'] + x['src_out'] - x['src_in']
                for a, b, vol in ((x['rec'], max(x['rec'], r0), x.get('volume')), (max(x['rec'], r0), min(e, r1), -60.0), (min(e, r1), e, x.get('volume'))):
                    if b > a: new.append(dict(x, rec=a, src_in=x['src_in'] + a - x['rec'], src_out=x['src_in'] + b - x['rec'], volume=vol))
            else: new.append(x)
        items = new
    # ---- media by PATH (never a name alone - Colden 2026-10-01, the Ep 21 Jake under Ep 24)
    media = {os.path.basename(c['path']): c['path'] for c in man['cameras']}
    used = sorted({x['clip'] for x in items})
    miss = [u for u in used if u not in media]
    if miss: C.fail(f'no file path known for {miss}')
    for c in man['cameras']:
        if not c['path'].startswith(ep['dir'].rstrip('/') + '/'): C.fail(f'SOURCE GATE: {c["path"]} is not inside this episode\'s folder')
        if not os.path.exists(c['path']): C.fail(f'SOURCE GATE: {c["path"]} is not on disk (NAS mounted?)')
    if beeps: media[bp['clip']] = bp['path']
    vers = C.load(f'{W.work}/edit/{tid}/versions.json', []); v = 1 + max([x['v'] for x in vers] or [0])
    name = C.tl_name(f'Ep {ep["ep_no"]} {tid.upper()} {th["title"]} v{v}')
    P = {'short': tid, 'v': v, 'name': name, 'building': 'zz BUILDING ' + name, 'template': W.S['resolve']['template'], 'project': ep['project'], 'bin': ep['bin'], 'shorts_bin': W.S['resolve']['shorts_bin'],
         'pod': ep['cut'], 'fps': fps, 'frames': total, 'tracks': {'video': VT, 'audio': AT}, 'camera_tracks': order, 'media': media, 'sources_used': used,
         'items': sorted(items, key=lambda x: (x['kind'], x['track'], x['rec'])), 'quiet_tail': cut.get('quiet_tail'), 'runs': runs, 'captions': captions, 'hook': hook, 'tags': tags, 'broll': brolls, 'broll_waiver': spec.get('waiver'),
         'beeps': beeps, 'beep': bp['clip'], 'beep_db': bp['db'], 'censor': cut['censor'], 'transparent': f'{ep["shorts_dir"]}/Assets/transparent_1080x1920_120s.mov',
         'cut_sha': C.sha_text(json.dumps(cut['shots'], sort_keys=True)), 'made_at': C.now(), 'shots': cut['shots'], 'dest': th['dest'], 'title': th['title']}
    path = f'{W.work}/edit/{tid}/build.v{v}.json'; C.save(path, P); return P, path

if __name__ == '__main__':
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    if len(a) < 2: C.fail(__doc__)
    P, path = make(os.path.abspath(a[0]), a[1])
    print(f'{P["name"]}: {P["frames"]} frames, {sum(1 for x in P["items"] if x["kind"] == "video")} video + {sum(1 for x in P["items"] if x["kind"] == "audio")} audio pieces, {len(P["captions"])} caption runs, tags {len(P["tags"])}, b-roll {[b["at"] for b in P["broll"]]}, beeps {len(P["beeps"])}\n  {path}')
