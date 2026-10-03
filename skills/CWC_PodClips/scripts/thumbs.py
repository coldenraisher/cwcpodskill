"""thumbs.py - the thumbnails of one locked clip upload (rules: references/carried_rules.md "Thumbnails", ruling 39,
the show file's packaging.thumbnail). Files: WORK/package/<id>/thumbs/<ch>/ ; record: WORK/package/<id>/thumbs.<ch>.json
{speaker, gaze_mode, shortlist, still_confirmed, frame, hooks, ai {ai-1, ai-2, C}, options [4 files], kinds, pick,
abc {A, B, C}, c_model}.

  thumbs.py frames <WORK> <id> <ch> [--scope clip|episode]
        the SHORTLIST for the real still (ruling 39). Who: @ColdenRaisher = always Colden; else the clip's main
        speaker. Where: `clip` = his close-ups in the master (no b-roll / name tag / stinger / ending), 4 frames a
        second; `episode` = his whole camera file, 1 frame a second (same day, same wardrobe; scanned once per person
        and cached) - the normal choice (SKILL.md Stage 3): a clip rarely holds a confirmed smile to camera. Apple Vision (tools/face) per frame: head pose, where each
        pupil sits in its eye, mouth, smile, capture quality; Core Image's BLINK classifier per eye and SMILE classifier.
        GATES per frame (thumbs.eyes_ok): both eyes open by the blink classifier (Vision's eye outline stays "open" on
        a shut eye - C03 v1 shipped closed eyes); both pupils centred; eyes to camera ("camera": head yaw / pitch near
        0) or straight ahead ("forward": the person's own usual pose - packaging.thumbnail.gaze, Jake); no squint (the
        visible eye >= 85 % of the person's usual height - 60 % for "laughing"); a clear face. For smile / laughing only frames the smile
        classifier accepts; ranked for the wanted emotion (copy `thumb_emotion`, default smile) against the person's
        own neutral face.
        -> still_sheet.jpg: 12 face crops, numbered. LOOK at it.
  thumbs.py still <WORK> <id> <ch> <n> <smile|laughing|angry|confused> "<what you see: eyes, expression>"
        the CONFIRMED still: the frame is taken at full resolution, the SAME gates run on that exact frame (the 10
        frames either side are searched when it fails - a blink sits one frame away), -> "1 frame.png", ref_face.png and
        eyes_check.jpg (the face + both eyes, large). LOOK at eyes_check.jpg. If the wanted emotion has no confirmed
        still, confirm a smile (ruling 39: "if not, default to smiling") - the record says so.
  thumbs.py hook <WORK> <id> <ch> ["WORDS"] [--accent W] [--out name]
        option 2: the headline (copy hook_headline) over the confirmed still - Sora 800, white + ONE purple accent word,
        text on the side without the face (a centred face is moved to the right third). Refuses without a confirmed still.
  thumbs.py wardrobe <WORK> <id> <ch> [--saw "<what they wear>"]   the episode wardrobe sheet -> LOOK -> record (ruling 45)
  thumbs.py airef <WORK> <id> <ch> [<n> --saw ".."]  the ONE clean reference frame (thumb_prompt.py)
  thumbs.py prompt <WORK> <id> <ch> <ai-1|ai-2|C> --promise .. --object .. --scene .. --expression .. [--side] [--noun]
        the AI brief as the PROSE recipe (ruling 47)
  thumbs.py check-prompt <WORK> <id> <ch> <slot>      the gate + the exact Higgsfield call (thumb_prompt.py)
        ai-1 = GPT Image 2.5 sunburst high 1k, ai-2 = Grok Imagine 2.0 medium 1k, C = the model of A; a smile = closed-lip, NO teeth (ruling 40);
        otherwise a believable expression tied to the topic (ruling 45).
  thumbs.py add <WORK> <id> <ch> <image> <ai-1|ai-2|C> --model <m> --gen-id <job id> --reported-model <m> --saw "<what the image shows>"
        fit an AI image to 1920x1080 under 2 MB and record it. --saw is the attestation that it was LOOKED at: the
        right person's likeness, no real third party / film art / logo, the text spelled right, no teeth on a smile, no mics or
        AirPods. C is bound to the title C it was made for (a changed title C voids it).
  thumbs.py grid <WORK> <id> <ch>       options 1-4 (still, hook, ai-1, ai-2) -> grid.jpg for the Telegram card
  thumbs.py abc <WORK> <id> <ch>        after his pick: A = the pick; B = the confirmed still + the overlay with
                                        copy hook_headline_B; C = added with `add ... C` (from title C, with A's model;
                                        gpt_image_2 when A is not AI). Run it again after C -> abc_grid.jpg
GATES every file 16:9 at 1920x1080 (or 1280x720 when 1920 is over 2 MB) and under 2 MB; no hook / B without a confirmed
still; an AI image is recorded only with --saw; A, B and C must be three different pictures (tg_pack / package)."""
import os, re, sys, json, glob, shutil, subprocess, base64, time
from PIL import Image, ImageDraw, ImageFont
import common as C
HERE = os.path.dirname(os.path.abspath(__file__)); TOOLS = os.path.join(os.path.dirname(HERE), 'tools')
def opt(flag, d=None): return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else d
def paths(W, tid, ch):
    d = f'{W}/package/{tid}/thumbs/{ch}'; os.makedirs(d, exist_ok=True); return d, f'{W}/package/{tid}/thumbs.{ch}.json'
def rec(W, tid, ch): return C.load(paths(W, tid, ch)[1], {}) or {}
def save(W, tid, ch, r): C.save(paths(W, tid, ch)[1], r)
def version(W, tid, ch):
    L = C.load(f'{W}/lock.json'); c = next(x for x in L['clips'] if x['theme'] == tid and x['channel'] == ch)
    v = next(x for x in C.load(C.vpath(W, tid), []) if x['channel'] == ch and x['v'] == c['v']); return c, C.load(v['plan'])

def fit(src, out):
    """-> a 1920x1080 file under 2 MB (else 1280x720), cover-cropped to 16:9"""
    im = Image.open(src).convert('RGB'); w, h = im.size; t = 16 / 9
    if abs(w / h - t) > 0.01:
        if w / h > t: nw = int(h * t); im = im.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
        else: nh = int(w / t); im = im.crop((0, (h - nh) // 2, w, (h - nh) // 2 + nh))
    big = im.resize((1920, 1080), Image.LANCZOS); big.save(out, optimize=True) if out.endswith('.png') else big.save(out, quality=92)
    if os.path.getsize(out) > 2_000_000:
        big.save(out[:-4] + '.jpg', quality=90);
        if out.endswith('.png'): os.remove(out); out = out[:-4] + '.jpg'
    if os.path.getsize(out) > 2_000_000: im.resize((1280, 720), Image.LANCZOS).save(out, quality=90)
    assert os.path.getsize(out) <= 2_000_000, f'{out} is over 2 MB'
    return out

def speaker(W, tid, ch, P):
    if ch == 'cwc': return C.show(C.episode(W)['show'])['packaging']['thumbnail']['cwc_face']
    tot = {}
    for s in P['shots']:
        if s['kind'] == 'body' and s['cam'] != 'WIDE': tot[s['cam']] = tot.get(s['cam'], 0) + s['b'] - s['a']
    return max(tot, key=tot.get)

EMOTIONS = ('smile', 'laughing', 'angry', 'confused')
def faces(files):
    """tools/face over files (200 at a time) -> rows with a face; a crashed batch is an error, never a silent gap"""
    rows = []
    for k in range(0, len(files), 200):
        r = subprocess.run([f'{TOOLS}/face'] + files[k:k + 200], capture_output=True, text=True)
        if r.returncode != 0: C.fail(f'tools/face failed on frames {k}-{k + 200} (exit {r.returncode}): {r.stderr[-200:]} - rebuild it: make -C {TOOLS}')
        for line in r.stdout.splitlines():
            try: j = json.loads(line)
            except Exception: continue
            if j.get('faces'): rows.append(j)
    return rows
def eye_height(f, j):
    """visible eye height / eye width per eye, independent of brightness: pixels that are NOT the skin just under the
    eye (iris, pupil, white, lashes) in the middle half of the eye, tallest run per column, median over columns.
    Judged against the person's own median (a squint is well under it). It cannot tell a lowered lid in deep shadow
    from an open eye - that is what the blink classifier (tools/face: l_closed / r_closed) and the pose gate are for."""
    import numpy as np
    im = np.asarray(Image.open(f).convert('RGB')).astype(float); out = []
    for e in ('le', 're'):
        if not j.get(e): out.append(0.0); continue
        x0, y0, x1, y1 = j[e]; w = x1 - x0
        if w < 10: out.append(0.0); continue
        cy = (y0 + y1) // 2; top, bot = max(0, cy - int(0.38 * w)), cy + int(0.38 * w)
        box = im[top:bot, x0:x1]; skin = im[bot + int(0.12 * w):bot + int(0.42 * w), x0:x1].reshape(-1, 3)
        if box.size == 0 or skin.size == 0: out.append(0.0); continue
        sk = np.median(skin, 0); m = np.sqrt(((box - sk) ** 2).sum(2)) / (np.linalg.norm(sk) + 1e-6) > 0.20; cols = m[:, int(0.25 * w):int(0.75 * w)]; runs = []
        for c in range(cols.shape[1]):
            best = cur = 0
            for v in cols[:, c]:
                cur = cur + 1 if v else 0; best = max(best, cur)
            runs.append(best)
        out.append(round(float(np.median(runs)) / w, 3))
    return out
EYE_MIN = {'smile': 0.85, 'angry': 0.85, 'confused': 0.85, 'laughing': 0.6}     # share of the person's usual visible eye height: a smile keeps the eyes VISIBLE; a laugh may squint
def eyes_ok(r, base, mode, y0=0.0, p0=0.0, emo='smile'):
    """THE EYES GATE (ruling 39 + Colden 2026-10-02 "this should have failed for jake. no eyes"): Apple's blink
    classifier says both eyes are open; both pupils sit in the middle of the eye; the head faces the camera ("camera")
    or the person's usual direction ("forward"); the visible eye is not a squint."""
    return bool(r.get('ci') and not r.get('l_closed') and not r.get('r_closed') and all(0 <= g and abs(g - 0.5) <= 0.12 for g in r['gx']) and all(0.2 <= g <= 0.7 for g in r['gy'])
                and abs(r['yaw'] - y0) <= 9 and abs(r['pitch'] - p0) <= 12 and min(r['eh']) >= EYE_MIN[emo] * base)
def score(rows, mode, emo='smile'):
    """rows that pass the eyes gate -> each with eye_base / pose0 (what the person's NORMAL looks like in this footage)"""
    import statistics as st
    good = [r for r in rows if r.get('yaw', 999) < 900 and r.get('quality', 0) >= 0.3 and r.get('ci')]
    if not good: return []
    y0 = st.median(r['yaw'] for r in good) if mode == 'forward' else 0.0; p0 = st.median(r['pitch'] for r in good) if mode == 'forward' else 0.0
    for r in good:
        if 'eh' not in r: r['eh'] = eye_height(r['file'], r)
    opened = [min(r['eh']) for r in good if not r.get('l_closed') and not r.get('r_closed')]
    if not opened: return []
    base = st.median(opened)
    return [dict(r, eye_dev=round(max(abs(g - 0.5) for g in r['gx']) + abs(r['yaw'] - y0) / 60, 3), eye_base=base, pose0=[y0, p0]) for r in good if eyes_ok(r, base, mode, y0, p0, emo)]

def frames(W, tid, ch, scope='clip'):
    """the SHORTLIST for the real thumbnail still (Colden 2026-10-02): eyes to camera (Jake: straight ahead), default
    emotion SMILING, confirmed by a person looking - `thumbs.py still` records the confirmation. scope 'clip' samples the
    speaker's close-ups in the master every 6 frames; 'episode' samples the speaker's camera file over the whole episode
    every 1 s (same day, same wardrobe) when the clip has no confirmed still."""
    c, P = version(W, tid, ch); fps = P['fps']; who = speaker(W, tid, ch, P); d, _ = paths(W, tid, ch); cand = f'{d}/cand'; shutil.rmtree(cand, ignore_errors=True); os.makedirs(cand)
    TH_ = C.show(C.episode(W)['show'])['packaging']['thumbnail']; mode = (TH_.get('gaze') or {}).get(who, 'camera')
    cp = C.load(f'{W}/package/{tid}/copy.{ch}.json') or {}; emo = cp.get('thumb_emotion', 'smile'); assert emo in EMOTIONS, f'thumb_emotion must be one of {EMOTIONS}'
    if scope == 'clip':
        busy = [(b['rec'] - 15, b['rec'] + b['frames'] + 15) for b in P.get('broll', [])] + [(t['rec'] - 15, t['rec'] + t['frames'] + 15) for t in P.get('tags', [])] + [(P['stinger']['rec'], P['anchors']['body_start'] + 15), (P['outro']['C'] - 30, P['frames'])]
        wins = [(s['rec'] / fps, (s['rec'] + s['b'] - s['a']) / fps) for s in P['shots'] if s['cam'] == who and s['b'] - s['a'] >= 30]
        src, rate = c['master'], 4
        keep = lambda t: any(a + 0.2 <= t <= b - 0.2 for a, b in wins) and not any(a <= t * fps < b for a, b in busy)
    else:
        m = C.load(f'{C.episode(W)["podcut_cache"]}/manifest.json'); cam = next(x for x in m['cameras'] if x.get('name') == who); src, rate = cam['path'], 1
        keep = lambda t: True; shutil.rmtree(cand, ignore_errors=True); cand = f'{W}/package/_faces/{who}'          # one scan per person per episode, shared by their uploads
        cache = f'{cand}/rows.json'
        if os.path.exists(cache) and C.load(cache).get('src') == src and all('ci' in r for r in C.load(cache)['rows'][:5]): rows = C.load(cache)['rows']; files = [r['file'] for r in rows]; cached = True
        else: cached = False; shutil.rmtree(cand, ignore_errors=True); os.makedirs(cand)
    if scope == 'clip' or not cached:
      subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', src, '-vf', f'fps={rate},scale=1280:-2', '-q:v', '3', f'{cand}/f%05d.jpg'], check=True)
      files = []
      for f in sorted(glob.glob(f'{cand}/f*.jpg')):
        t = (int(os.path.basename(f)[1:6]) - 0.5) / rate          # ffmpeg's fps filter takes the frame at the MIDDLE of each interval (measured: +0.5 / rate)
        if keep(t): files.append((f, t))
        else: os.remove(f)
      if not files: C.fail(f'{tid} {ch}: no frame of {who} to look at')
      tmap = dict(files); files = [f for f, _ in files]; rows = faces(files)
      for j in rows: j['t'] = tmap.get(j['file'])
      if scope == 'episode': C.save(f'{cand}/rows.json', {'src': src, 'rows': rows})
    for r in rows: r['t'] = (int(os.path.basename(r['file'])[1:6]) - 0.5) / rate      # also for a cached scan
    if not rows: C.fail(f'{tid} {ch}: no face of {who} found in {len(files)} frames ({scope}) - try --scope episode, or ask Colden for a photo')
    ok = score(rows, mode, emo)
    if scope == 'episode': C.save(f'{cand}/rows.json', {'src': src, 'rows': rows})          # with the eye heights: the next upload of this person is instant
    if emo in ('smile', 'laughing'):                           # "smile confirmed": Apple's smile classifier first, the look at the sheet second
        smiling = [r for r in ok if r.get('ci_smile')]
        if smiling: ok = smiling
        else: print(f'  NOTE: no frame with open eyes AND a detected smile - the sheet shows the best of what exists; say so to Colden')
    import statistics as st                                   # each person's own neutral face is the baseline (a smile is relative)
    def z(k): vals = [r[k] for r in rows]; m = st.median(vals); sd = (st.pstdev(vals) or 1e-6); return lambda r: (r[k] - m) / sd
    zs, zw, zo = z('smile'), z('mouth_w'), z('open')
    ze = lambda r: min(r['eh']) / max(1e-6, r['eye_base'])            # how open the eyes are vs the person's usual
    key = {'smile': lambda r: -(min(zs(r), 1.5) + 0.5 * min(zw(r), 1.5) - 0.5 * max(0, zo(r))) + 3 * r['eye_dev'] - 3.0 * min(ze(r), 1.0) + 6.0 * max(0, ze(r) - 1.08) + abs(r['pitch'] - r['pose0'][1]) / 6,      # a clear smile, not the widest laugh; open eyes count as much as the smile; a "taller than usual" eye is a lowered lid in shadow (looking down), not a wider eye
           'laughing': lambda r: -(zs(r) + zw(r) + zo(r)) + 3 * r['eye_dev'],
           'angry': lambda r: (zs(r) + zw(r)) + 3 * r['eye_dev'],
           'confused': lambda r: -abs(r['roll']) / 10 + zs(r) + 3 * r['eye_dev']}[emo]
    ok.sort(key=key); short = []
    for r in ok:                                              # spread: never two picks within 2 s of each other
        if all(abs(r['t'] - x['t']) > 2 for x in short): short.append(r)
        if len(short) == 12: break
    sheet = Image.new('RGB', (1920, 1080), 'black'); dr = ImageDraw.Draw(sheet)
    try: fnt = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Bold.ttf', 30)
    except Exception: fnt = ImageFont.load_default()
    for i, r in enumerate(short):                             # FACE crops, big enough to judge the expression and the eyes
        im = Image.open(r['file']).convert('RGB'); cx, cy, sz = r['x'] + r['w'] / 2, r['y'] + r['h'] / 2, max(r['w'], r['h']) * 0.85
        im = im.crop((int(max(0, cx - sz * 1.33)), int(max(0, cy - sz)), int(min(im.width, cx + sz * 1.33)), int(min(im.height, cy + sz)))).resize((480, 360))
        X, Y = (i % 4) * 480, (i // 4) * 360; sheet.paste(im, (X, Y)); dr.rectangle([X, Y, X + 46, Y + 40], fill='#7C3AED'); dr.text((X + 8, Y + 4), str(i + 1), font=fnt, fill='white')
    sheet.save(f'{d}/still_sheet.jpg', quality=85)
    R = rec(W, tid, ch); R.update({'speaker': who, 'gaze_mode': mode, 'emotion_wanted': emo, 'shortlist': [{'n': i + 1, 'file': r['file'], 't': r['t'], 'src': src, 'yaw': r['yaw'], 'pitch': r['pitch'], 'gx': r['gx'], 'smile': r['smile'], 'open': r['open'], 'eh': r['eh'], 'eye_base': r['eye_base'], 'pose0': r['pose0'], 'ci_smile': r.get('ci_smile')} for i, r in enumerate(short)],
              'shortlist_scope': scope, 'shortlist_stats': {'sampled': len(files), 'faces': len(rows), 'eyes_ok': len(ok)}, 'still_confirmed': None})
    save(W, tid, ch, R)
    print(f'{tid} {ch}: {who} ({mode}), want {emo}: {len(files)} frames ({scope}), {len(rows)} faces, {len(ok)} with eyes {"to camera" if mode == "camera" else "straight ahead"}\n  LOOK: {d}/still_sheet.jpg   then: thumbs.py still <WORK> {tid} {ch} <n> <emotion> "<what you see>"' + ('' if short else f'\n  NOTHING passed - run with --scope episode'))

def still(W, tid, ch, n, emotion, saw):
    """record the CONFIRMED still (a person looked at the sheet): the frame at full resolution -> '1 frame.png' + ref_face"""
    assert emotion in EMOTIONS, f'emotion one of {EMOTIONS}'
    if len(saw) < 20: C.fail('say what you see: eyes, expression')
    d, _ = paths(W, tid, ch); R = rec(W, tid, ch); s = next((x for x in R.get('shortlist') or [] if x['n'] == int(n)), None)
    if not s: C.fail(f'no shortlist entry {n} (thumbs.py frames)')
    if not s.get('eye_base'): C.fail(f'{tid} {ch}: this shortlist was made by an older thumbs.py (no eye baseline) - run thumbs.py frames again')
    tmp = f'{d}/_near'; shutil.rmtree(tmp, ignore_errors=True); os.makedirs(tmp)
    num, den = (subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=r_frame_rate', '-of', 'csv=p=0', s['src']], capture_output=True, text=True).stdout.strip() or '30/1').split('/'); sfps = float(num) / float(den or 1)
    t0 = max(0.0, s['t'] - 10 / sfps); mid = int(round((s['t'] - t0) * sfps))                      # 10 frames either side of the sheet's frame, at the SOURCE's frame rate
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{t0:.3f}', '-i', s['src'], '-frames:v', '21', f'{tmp}/n%02d.png'], check=True)
    near = sorted(glob.glob(f'{tmp}/n*.png')); rows = faces(near)
    if os.path.exists(s['file']):                             # THE FRAME USED IS THE FRAME LOOKED AT: find the sheet's frame among these by its pixels
        import numpy as np
        g = lambda f: np.asarray(Image.open(f).convert('L').resize((160, 90))).astype(float); ref = g(s['file']); dif = [float(np.mean(np.abs(g(f) - ref))) for f in near]
        mid = int(np.argmin(dif))
        if min(dif) > 4.0: C.fail(f'{tid} {ch}: the frame shown as #{n} on the sheet cannot be found in the source around {s["t"]:.2f} s (best difference {min(dif):.1f}) - a timing fault; run thumbs.py frames again')
    mode = R.get('gaze_mode', 'camera'); base = s['eye_base']; y0, p0 = s.get('pose0') or [0.0, 0.0]
    good = []
    for r in rows:                                            # the SAME gates on the full-resolution frame that will be used
        r['eh'] = eye_height(r['file'], r)
        if eyes_ok(r, base, mode, y0, p0, emotion) and (emotion not in ('smile', 'laughing') or r.get('ci_smile') or not s.get('ci_smile')): good.append(r)
    if not good: C.fail(f'{tid} {ch}: none of the 21 frames around shortlist {n} passes eyes + gaze at full resolution - pick another number')
    best = min(good, key=lambda r: (abs(near.index(r['file']) - mid), -min(r['eh'])))
    if abs(near.index(best['file']) - mid) > 3: C.fail(f'{tid} {ch}: the nearest frame that passes the eyes gate is {abs(near.index(best["file"]) - mid)} frames from the one on the sheet - not the picture you looked at; pick another number')
    full = f'{d}/still_full.png'; shutil.copyfile(best['file'], full); shutil.rmtree(tmp, ignore_errors=True)
    out = fit(full, f'{d}/1 frame.png'); j = json.loads(subprocess.run([f'{TOOLS}/face', full], capture_output=True, text=True).stdout.splitlines()[0])
    im = Image.open(full).convert('RGB'); cx, cy, sz = j['x'] + j['w'] / 2, j['y'] + j['h'] / 2, max(j['w'], j['h']) * 1.6
    im.crop((int(max(0, cx - sz)), int(max(0, cy - sz)), int(min(im.width, cx + sz)), int(min(im.height, cy + sz)))).save(f'{d}/ref_face.png')
    chk = Image.new('RGB', (960, 480), 'black'); chk.paste(im.crop((int(cx - j['w'] * 0.7), int(cy - j['h'] * 0.7), int(cx + j['w'] * 0.7), int(cy + j['h'] * 0.7))).resize((480, 480)), (0, 0))
    for k, e in enumerate(('le', 're')):
        x0, y0, x1, y1 = j[e]; w = x1 - x0; chk.paste(im.crop((x0 - w // 4, y0 - w // 2, x1 + w // 4, y1 + w // 2)).resize((480, 240)), (480, k * 240))
    chk.save(f'{d}/eyes_check.jpg', quality=90)
    want = R.get('emotion_wanted', 'smile')
    R.update({'still': full, 'frame': {'file': out, 't': s['t'], 'src': s['src']}, 'ref_face': f'{d}/ref_face.png',
              'still_confirmed': {'n': int(n), 'emotion': emotion, 'wanted': want, 'saw': saw, 'at': C.now(), 'fallback_to_smile': emotion == 'smile' and want != 'smile'}})
    R['still_confirmed'].update(eye_height=best['eh'], eye_base=base, blink_classifier='both eyes open', smile_classifier=bool(best.get('ci_smile'))); save(W, tid, ch, R)
    print(f'{tid} {ch}: still {n} -> frame {near.index(best["file"]) - mid:+d} from the sheet time, eyes open (blink classifier), eye height {best["eh"]} (usual {base:.2f}), smile classifier {bool(best.get("ci_smile"))} -> {out}\n  LOOK at {d}/eyes_check.jpg before building on it')

def hook(W, tid, ch, head=None, accent=None, still=None, out_name='2 hook'):
    d, _ = paths(W, tid, ch); R = rec(W, tid, ch); cp = C.load(f'{W}/package/{tid}/copy.{ch}.json') or {}
    head = head or cp.get('hook_headline'); accent = accent or cp.get('hook_accent'); still = still or R.get('still')
    assert head and still and os.path.exists(still), 'needs a headline (copy hook_headline) and a still (thumbs.py frames)'
    if not R.get('still_confirmed'): C.fail(f'{tid} {ch}: the still is not confirmed (thumbs.py frames -> LOOK -> thumbs.py still) - Colden 2026-10-02: eyes to camera, smile confirmed')
    side = 'right'; d0, _ = paths(W, tid, ch)
    try:
        j = json.loads(subprocess.run([f'{TOOLS}/facequality', still], capture_output=True, text=True).stdout.splitlines()[0]); f = max(j['faces'], key=lambda f: f['w'] * f['h'])
        fx = (f['x'] + f['w'] / 2) / j['w']; side = 'left' if fx > 0.5 else 'right'
        if 0.3 < fx < 0.7:                                  # a centred face: zoom 1.3x and put it on the right third, text on the left (never over the face)
            im = Image.open(still).convert('RGB'); cw, chh = int(im.width / 1.3), int(im.height / 1.3); cx = fx * im.width
            x0 = int(min(max(0, cx - 0.68 * cw), im.width - cw)); y0 = int(min(max(0, (f['y'] + f['h'] / 2) - 0.45 * chh), im.height - chh))
            im.crop((x0, y0, x0 + cw, y0 + chh)).resize((im.width, im.height), Image.LANCZOS).save(f'{d0}/_still_shifted.png'); still = f'{d0}/_still_shifted.png'; side = 'left'
    except Exception as e: C.fail(f'{tid} {ch}: no face found on the confirmed still ({e}) - the headline could land on the face; confirm another still')
    b64 = base64.b64encode(open(still, 'rb').read()).decode(); words = head.upper().split()
    html_words = ' '.join(f'<em>{w}</em>' if accent and w.strip(',.?!') == accent.upper().strip(',.?!') else w for w in words)
    size = 168 if len(head) <= 14 else (150 if len(head) <= 24 else 128); acc = '#7C3AED'
    page = f'''<!doctype html><html><head><meta charset="utf-8"><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Sora:wght@800&display=swap">
<style>html,body{{margin:0;width:1920px;height:1080px;overflow:hidden;background:#0B0F14}}
.frame{{position:relative;width:1920px;height:1080px;background:url(data:image/png;base64,{b64}) center/cover no-repeat}}
.grad{{position:absolute;inset:0;background:linear-gradient(to {'right' if side == 'left' else 'left'}, rgba(11,15,20,.88) 0%, rgba(11,15,20,.55) 34%, rgba(11,15,20,0) 62%)}}
.bottom{{position:absolute;inset:0;background:linear-gradient(to top, rgba(11,15,20,.72) 0%, rgba(11,15,20,0) 45%)}}
.block{{position:absolute;bottom:96px;{side}:96px;max-width:1040px;display:flex;flex-direction:column;gap:22px;align-items:flex-start}}
.rule{{width:132px;height:10px;background:{acc};border-radius:2px}}
h1{{margin:0;font-family:"Sora","Barlow","Arial Black",sans-serif;font-weight:800;font-size:{size}px;line-height:.94;letter-spacing:-.015em;color:#fff;text-transform:uppercase;text-shadow:0 6px 28px rgba(0,0,0,.55),0 2px 4px rgba(0,0,0,.6);text-wrap:balance}}
h1 em{{font-style:normal;color:{acc}}}</style></head><body><div class="frame"><div class="grad"></div><div class="bottom"></div><div class="block"><div class="rule"></div><h1>{html_words}</h1></div></div></body></html>'''
    tmp = f'{d}/_hook'; shutil.rmtree(tmp, ignore_errors=True); os.makedirs(tmp); open(f'{tmp}/hook.html', 'w').write(page); shot = f'{tmp}/hook.png'
    CH = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
    p = subprocess.Popen([CH, '--headless=new', '--disable-gpu', '--hide-scrollbars', '--no-first-run', f'--user-data-dir={tmp}/prof', '--window-size=1920,1080', '--force-device-scale-factor=1', '--virtual-time-budget=6000', f'--screenshot={shot}', 'file://' + f'{tmp}/hook.html'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(60):
        if os.path.exists(shot) and os.path.getsize(shot) > 0: break
        time.sleep(1)
    p.kill(); assert os.path.exists(shot), 'Chrome made no screenshot'
    out = fit(shot, f'{d}/{out_name}.png'); shutil.rmtree(tmp, ignore_errors=True)
    R = rec(W, tid, ch); R.setdefault('hooks', {})[out_name] = {'file': out, 'headline': head, 'accent': accent, 'side': side, 'still': still}; save(W, tid, ch, R)
    print(f'{tid} {ch}: hook "{head}" ({side}) -> {out}'); return out

def add(W, tid, ch, img, slot, model=None, pfile=None, saw=None, gen_id=None, reported=None, reads=None):
    if not reads or len(reads) < 25: C.fail('--reads "<what a stranger understands from the 320x180 version: what stops the scroll and what the video is about>" - RULE 1 (thumb_prompt.RULE1)')
    if slot not in ('ai-1', 'ai-2', 'C'): C.fail('slot: ai-1 | ai-2 | C')
    import thumb_prompt as TP; pr = TP.gate_add(W, tid, ch, slot, model, gen_id, reported); pfile = pr['file']      # ruling 45: only from the checked JSON template, with the slot's model
    if not saw or len(saw) < 30: C.fail('--saw "<what the image shows>": LOOK at the image first - the right person\'s likeness, no real third party / film art / logo, the text spelled right, no teeth on a smile (ruling 40), no microphones or AirPods (Ep 24: a Brando look-alike, Star Wars art, a "1220" stamp and bared teeth all had to be regenerated)')
    cp = C.load(f'{W}/package/{tid}/copy.{ch}.json') or {}
    if slot == 'C' and not cp.get('C'): C.fail('thumbnail C is made FROM title C - write "C" into the copy first')
    d, _ = paths(W, tid, ch); name = {'ai-1': '3 ai-1', 'ai-2': '4 ai-2', 'C': 'C'}[slot]; out = fit(img, f'{d}/{name}.png')
    entry = {'reads_at_320': reads, 'file': out, 'model': model, 'reported_model': pr.get('reported'), 'model_mismatch': pr.get('reported') != model, 'gen_id': gen_id, 'prompt': open(pfile).read() if pfile and os.path.exists(pfile) else None, 'prompt_sha': pr['sha'], 'source': img, 'saw': saw, 'at': C.now(), 'for_title': cp.get('C') if slot == 'C' else None}
    small = f'{d}/{name} 320.jpg'; Image.open(out).convert('RGB').resize((320, 180), Image.LANCZOS).save(small, quality=90)      # the guide's small-size check
    def mut(R):
        R.setdefault('ai', {})[slot] = entry
        if slot == 'C': R.setdefault('abc', {})['C'] = out
    C.update(paths(W, tid, ch)[1], mut, {}); print(f'{tid} {ch}: {slot} -> {out} ({os.path.getsize(out) / 1e6:.2f} MB)\n  LOOK at the small one too ({small}): does the idea and the headline read at 320x180?')

def label(im, txt):
    d = ImageDraw.Draw(im)
    try: f = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Bold.ttf', 34)
    except Exception: f = ImageFont.load_default()
    d.rectangle([0, im.height - 52, 52, im.height], fill='#7C3AED'); d.text((14, im.height - 47), txt, font=f, fill='white')      # small, bottom-left: never over the headline

def grid(W, tid, ch):
    d, _ = paths(W, tid, ch); R = rec(W, tid, ch)
    opts = [R.get('frame', {}).get('file'), (R.get('hooks') or {}).get('2 hook', {}).get('file'), (R.get('ai') or {}).get('ai-1', {}).get('file'), (R.get('ai') or {}).get('ai-2', {}).get('file')]
    miss = [i + 1 for i, f in enumerate(opts) if not f or not os.path.exists(f)]
    if miss: C.fail(f'{tid} {ch}: thumbnail option(s) {miss} missing (frames / hook / add ai-1 ai-2)')
    g = Image.new('RGB', (1920, 1080), 'black')
    for i, f in enumerate(opts):
        im = Image.open(f).convert('RGB').resize((960, 540)); label(im, str(i + 1)); g.paste(im, ((i % 2) * 960, (i // 2) * 540))
    g.save(f'{d}/grid.jpg', quality=88); R.update({'options': opts, 'kinds': ['frame', 'hook', 'ai-1', 'ai-2'], 'grid': f'{d}/grid.jpg'}); save(W, tid, ch, R); print(f'{tid} {ch}: grid -> {d}/grid.jpg'); return f'{d}/grid.jpg'

def abc(W, tid, ch):
    d, _ = paths(W, tid, ch); R = rec(W, tid, ch); cp = C.load(f'{W}/package/{tid}/copy.{ch}.json') or {}
    if R.get('pick') is None: C.fail(f'{tid} {ch}: no thumbnail picked yet')
    if not cp.get('B') or not cp.get('C'): C.fail(f'{tid} {ch}: titles B and C are not written yet (copy.{ch}.json)')
    A = R['options'][R['pick']]; ab = R.setdefault('abc', {}); ab['A'] = A
    head_b = cp.get('hook_headline_B')
    if not head_b or head_b.upper() == (cp.get('hook_headline') or '').upper(): C.fail(f'{tid} {ch}: write "hook_headline_B" (2-4 words from title B, different from hook_headline) into the copy - thumbnail B is the still with THAT headline')
    if R['kinds'][R['pick']] == 'hook':                    # A is already the overlay: B = the overlay on another still, headline from title B
        ab['B'] = hook(W, tid, ch, head_b, cp.get('hook_accent_B') or None, R.get('still'), 'B')      # the confirmed still, headline from title B
    else: ab['B'] = hook(W, tid, ch, head_b, cp.get('hook_accent_B') or cp.get('hook_accent'), R.get('still'), 'B')
    R = rec(W, tid, ch); R['abc'] = dict(R.get('abc', {}), A=A, B=ab['B'])
    R['c_model'] = (R.get('ai') or {}).get({'ai-1': 'ai-1', 'ai-2': 'ai-2'}.get(R['kinds'][R['pick']], ''), {}).get('model') or 'gpt_image_2'; save(W, tid, ch, R)
    if not R['abc'].get('C'): print(f'{tid} {ch}: A + B ready; C: write "ai_headline_C" (2-5 words) into the copy, thumbs.py prompt "<WORK>" {tid} {ch} C -> fill -> check-prompt -> generate with {R["c_model"]} -> thumbs.py add ... C'); return
    g = Image.new('RGB', (1920, 360), 'black')
    for i, k in enumerate('ABC'):
        im = Image.open(R['abc'][k]).convert('RGB').resize((640, 360)); label(im, k); g.paste(im, (i * 640, 0))
    g.save(f'{d}/abc_grid.jpg', quality=88); R['abc_grid'] = f'{d}/abc_grid.jpg'; save(W, tid, ch, R); print(f'{tid} {ch}: A/B/C -> {d}/abc_grid.jpg')

if __name__ == '__main__':
    vals = [sys.argv[i + 1] for i, x in enumerate(sys.argv[:-1]) if x in ('--accent', '--out', '--title', '--model', '--prompt-file', '--scope', '--saw', '--gen-id', '--product', '--reported-model', '--promise', '--object', '--reads', '--scene', '--expression', '--side', '--noun')]
    a = [x for x in sys.argv[1:] if not x.startswith('--') and x not in vals]
    if len(a) < 4: C.fail(__doc__)
    cmd, W, tid, ch = a[0], os.path.abspath(a[1]), a[2], a[3]
    if cmd == 'frames': frames(W, tid, ch, opt('--scope', 'clip'))
    elif cmd == 'still': still(W, tid, ch, a[4], a[5], a[6] if len(a) > 6 else '')
    elif cmd == 'hook': hook(W, tid, ch, a[4] if len(a) > 4 else None, opt('--accent'), None, opt('--out', '2 hook'))
    elif cmd in ('prompt', 'check-prompt', 'wardrobe', 'airef'):
        import thumb_prompt as TP
        if cmd == 'wardrobe': TP.wardrobe(W, tid, ch, opt('--saw'))
        elif cmd == 'airef': TP.airef(W, tid, ch, a[4] if len(a) > 4 else None, opt('--saw'))
        elif len(a) < 5: C.fail('slot: ai-1 | ai-2 | C')
        elif cmd == 'prompt': TP.prompt(W, tid, ch, a[4], [sys.argv[i + 1] for i, x in enumerate(sys.argv[:-1]) if x == '--product'], opt('--promise'), opt('--object'), opt('--scene'), opt('--expression'), opt('--side', 'right'), opt('--noun', 'man'))
        else: TP.check(W, tid, ch, a[4])
    elif cmd == 'add': add(W, tid, ch, a[4], a[5], opt('--model'), None, opt('--saw'), opt('--gen-id'), opt('--reported-model'), opt('--reads'))
    elif cmd == 'grid': grid(W, tid, ch)
    elif cmd == 'abc': abc(W, tid, ch)
    else: C.fail(__doc__)
