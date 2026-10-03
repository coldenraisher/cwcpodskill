"""cover.py - the two covers of one APPROVED short (Colden 2026-10-02, ruling 10: "Send 1 AI and 1 that you make in
Resolve. Issue with clips right now picking bad still image from edit. Make sure you use the best face detection
available to pick a clean image. Should be smiling at camera or looking forward (Jake does not look directly at
camera) if a different emotion is better, make sure you confirm with visual check that image fits emotion before
sending me the final"). Files: WORK/edit/<id>/cover/ ; record: WORK/edit/<id>/cover.json.

  LOCKED FOR FINAL 2026-10-02 (round 2 - round 1 voided: "Can't keep failing the basic gates"); SKILL.md ruling 10 a-e.
  cover.py frames <WORK> <id> [--emotion smile|laughing|angry|confused|serious]
        the SHORTLIST: a short that posts to Create with Colden shows COLDEN (show file channels.face, as on his long-form
        thumbnails - Colden 2026-10-02), otherwise the people who SPEAK in it (never a 3-stack listener); their camera
        file inside the short's own pieces, 6 frames a second. Apple Vision + Core Image per frame (tools/face, the CWC_PodClips
        detector). GATES: both eyes open (blink classifier + >= 95 % of the person's usual eye height for a smile),
        pupils centred, head to the lens (Jake: his own forward pose), sharp; the smile classifier for smile / laughing;
        the MOUTH never caught on a word: lips together, or a smile >= 1.2x their usual mouth width (a word stays ~1.0x).
        Default smile - a full smile may narrow the eyes ("narrow eyes fine"); serious / angry / confused need them open.
        Silent frames rank above talking ones, always ("talking always ranks lower than an actual smile"; `still`
        refuses a talking tile while a silent one of the same person is on the sheet). A short with no smile in it ->
        the emotion that fits its theme (serious = lips together, eyes on the lens, a point being made; confused;
        angry; laughing).
        still_sheet.jpg: PURPLE tiles = THUMBNAIL picks, fullest smile first, teeth welcome ("default to full smile.
        That includes teeth") | TEAL tiles = AI REFERENCES, lips together ("a good still face or grin with no teeth,
        send that to higgsfield"). Nothing passes -> exit 2: the emotion that fits the theme, else ask Colden.
  cover.py still <WORK> <id> <n> <emotion> "<what you see>"
        the THUMBNAIL still: the 21 frames around #n at full resolution, the SAME gates, the nearest passing frame
        within 3 frames -> still_full.png, eyes_check.jpg, ref_face.png, crop_check.jpg (the short's single crop). LOOK.
  cover.py airef <WORK> <id> <n> "<what you see>"
        the HIGGSFIELD REFERENCE: a teal tile, the same person as the still, mouth <= 0.022 at full resolution ->
        ai_ref_full.png, ai_ref_face.png, ai_ref_check.jpg. LOOK.
  cover.py resolve <WORK> <id>        (RESOLVE - ask first: tg_review.py ask-resolve) the RESOLVE-MADE cover: a 1 s
        timeline `<short name> cover vN` from the approved plan - that camera frame in the short's single crop + the
        hook on the caption line, nothing else - frame 12 rendered as a 16-bit TIFF -> "1 resolve.png". GATES: it IS the
        confirmed frame (offset measured, rebuilt once), the blink classifier again, face + hook inside the centre 3:4.
  cover.py headline <WORK> <id> "<1-3 words>" [--zone top|bottom]   the headline Colden decided + the third it rests on (recorded; add sets it in the hook box)
  cover.py brief <WORK> <id>          the AI brief: nano_banana_pro at 9:16 from the no-teeth AI reference, COMPOSED FOR THE
        CENTRE 3:4 (face + headline in the middle three quarters of the height; Colden 2026-10-02: a short-form cover is
        9:16, never generated at 3:4); NO TEETH, <= 3 words, ONE idea; no mics / AirPods / logos / film art.
  cover.py add <WORK> <id> <9:16 file> --headline "<exact>" --model nano_banana_pro --job <job record .json> --saw "..." --prompt cover/prompt.json
        (the prompt = the JSON object sent to Higgsfield, Colden's Nano Banana Pro guide 2026-10-02 - references/nano_banana_prompt.md:
        ONE reference @Image1 scoped to identity with do_not_transfer (background, mic, desk, lighting), subject.expression
        "lips together, no teeth", text.mode render_exact_text with exact_copy = the headline and a placement in % of the
        height, the layout keeping face + text in the middle three quarters, must_avoid with the exclusion list, no
        placeholders, no vague quality words; the headline = a line of the gated hook / title or a WIN pattern)
        -> "2 ai.jpg". GATES: the job record was SUBMITTED as nano_banana_pro (Higgsfield's API reports that job back as
        nano_banana_2 - the same job, its page says Nano Banana Pro); the prompt says "lips together, no teeth" and never
        asks for teeth / a grin / laughing; 9:16; every face + headline line inside y 264-1656 (the IG / TikTok grid = the
        centre 3:4); the headline reads back (OCR); mouth <= 0.022 (an AI cover never shows teeth). Refused -> .rejected.
  cover.py pair <WORK> <id>           both covers side by side -> pair.jpg (the short's Telegram card)
GATES: covers only for an approved short; no still without a shortlist; no Resolve cover without a CONFIRMED still; no
AI brief without the AI reference; an AI cover only with --saw; both files 1080x1920."""
import os, re, sys, json, glob, shutil, subprocess, copy, statistics as st
from PIL import Image, ImageDraw, ImageFont
import common as C
HERE = os.path.dirname(os.path.abspath(__file__)); TOOLS = os.path.join(C.SK, 'tools'); TW, TH = 1080, 1920
EMOTIONS = ('smile', 'laughing', 'angry', 'confused', 'serious'); AT = 12; N = 30     # serious = lips together, eyes open to the lens, no smile asked: the fallback when a short has no smile in it (a solo talker making a point)          # the cover frame sits at frame 12 of a 30-frame timeline (hookfit measures frame rec+12)
RES_SHIFT = 1        # measured 2026-10-02 (s03 cover v1): a clip appended from source frame n shows ffmpeg's frame n+1 at its first frame - placed 1 earlier; the gate below then demands an EXACT match

def opt(flag, d=None): return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else d
def cdir(W, tid): d = f'{W}/edit/{tid}/cover'; os.makedirs(d, exist_ok=True); return d
def rec(W, tid): return C.load(f'{W}/edit/{tid}/cover.json', {}) or {}
def save(W, tid, r): C.save(f'{W}/edit/{tid}/cover.json', r)
def approved(W, tid):
    vs = C.load(f'{W}/edit/{tid}/versions.json', []) or []; v = next((x for x in reversed(vs) if x.get('status') == 'approved'), None)
    if not v: C.ask(f'{tid}: no approved version - covers are made only for a short Colden approved')
    return v, C.load(v['plan'])
def person(W, who):
    p = next((x for x in C.episode(W)['people'] if x['name'] == who), None)
    if not p: C.fail(f'{who!r} is not in this episode (people: {[x["name"] for x in C.episode(W)["people"]]})')
    return p
def single_props(W, who):
    import plan as PL
    F = (C.load(f'{W}/edit/faces.json') or {}).get('faces') or {}
    if who not in F: C.fail(f'no face position for {who} - run faces.py')
    return PL.single(F[who])[0]
def crop_single(im, props):
    """the short's own single crop of a camera frame (plan.single's intended units) -> 1080x1920"""
    W_, H_ = im.size; z = props['ZoomX'] * props['sw'] / W_; shift = props['Pan'] * props['sw'] / TW     # z: timeline px per image px; shift: timeline px
    cx = W_ / 2 - shift / z; vw, vh = TW / z, TH / z; cy = H_ / 2
    return im.crop((int(round(cx - vw / 2)), int(round(cy - vh / 2)), int(round(cx + vw / 2)), int(round(cy + vh / 2)))).resize((TW, TH), Image.LANCZOS)

# ---- the face gates (copied from CWC_PodClips thumbs.py, 2026-10-02 - the same detector, the same rules)
def faces(files):
    rows = []
    for k in range(0, len(files), 200):
        r = subprocess.run([f'{TOOLS}/face'] + files[k:k + 200], capture_output=True, text=True)
        if r.returncode != 0: C.fail(f'tools/face failed (exit {r.returncode}): {r.stderr[-200:]} - rebuild it: make -C {TOOLS}')
        for line in r.stdout.splitlines():
            try: j = json.loads(line)
            except Exception: continue
            if j.get('faces'): rows.append(j)
    return rows
def eye_height(f, j):
    """visible eye height / eye width per eye (pixels that are not the skin under the eye, tallest run per column, median)"""
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
            for v in cols[:, c]: cur = cur + 1 if v else 0; best = max(best, cur)
            runs.append(best)
        out.append(round(float(np.median(runs)) / w, 3))
    return out
# Colden 2026-10-02 round 2 ("re-examine your smile/face detect... you let a lot of bad stills through. These should be the
# best still image in the short"): squints, off-lens looks and mid-word faces passed at the round-1 tolerances
EYE_MIN = {'smile': 0.6, 'laughing': 0.6, 'angry': 0.9, 'confused': 0.9, 'serious': 0.95}       # share of the person's own usual open eye (pixel eye height):
EYE_OPEN_MIN = {'smile': 0.5, 'laughing': 0.5, 'angry': 0.75, 'confused': 0.75, 'serious': 0.75}  # a FULL smile narrows the eyes and that is fine (Colden 2026-10-02: "narrow eyes fine" - Nick's smiles
                                            # squint); a serious / angry / confused face needs them open. Vision's own eye-openness vs the person's median is the second
                                            # check: a half-shut 'laughing' frame read 0.38 (s05 Jake) while the pixel height said 0.82; the blink classifier refuses shut eyes always
GAZE_TOL, YAW_TOL, PITCH_TOL, Q_MIN, SPEAK_PAD = 0.10, 7, 10, 0.4, 5           # pupil offset, degrees, degrees, Vision capture quality, frames
MOUTH_MAX = 0.014                           # lips together (inner-lip gap / face height): closed smiles measure 0.005-0.0137; a mouth parted on a vowel 0.016-0.02 (looked parted on the s14 sheet)
SMILE_W = 1.2                               # an OPEN mouth on a real still = a smile that shows teeth (Colden 2026-10-02: "default to full smile. That includes teeth"):
                                            # the lips stretched to >= 1.2x the person's own usual width (s15 teeth smile 1.42x); a mouth open on a WORD
                                            # stays near 1.0x - but a shouted vowel reaches 1.26x (Nick s09 / s01), so the corners must also LIFT:
LIFT_MIN = 0.02                             # mouth-corner lift (face heights) at least 0.02 over the person's usual (Colden good smiles 0.031-0.045 vs usual
                                            # 0.006; Nick's word mouths -0.004..-0.010 vs usual -0.023), and the mouth flat (open / width <= 0.32: a vowel is tall)
SAFE = (240, 1680); SAFE_MARGIN = 24        # Colden 2026-10-02: the IG grid (and TikTok's) shows the CENTRE 3:4 of a 9:16 cover (y 240-1680 of 1920)
TEETH_MAX = 0.022                           # AI covers: mouth openness (inner-lip gap / face height); teeth measured 0.044-0.069, lips together 0.006-0.015 - Colden's LOCKED rule (2026-10-02), never loosened without him
def eyes_ok(r, base, y0=0.0, p0=0.0, emo='smile', eo_base=None, slack=0.0):
    """slack: the re-check of a frame already on the sheet (still / airef) allows 5 % on the two eye ratios - the near frames are
    resampled by a different path than the sheet's ffmpeg scale and the pixel eye height moves a few percent"""
    return bool(r.get('ci') and not r.get('l_closed') and not r.get('r_closed') and all(0 <= g and abs(g - 0.5) <= GAZE_TOL for g in r['gx']) and all(0.2 <= g <= 0.7 for g in r['gy'])
                and abs(r['yaw'] - y0) <= YAW_TOL and abs(r['pitch'] - p0) <= PITCH_TOL and min(r['eh']) >= (EYE_MIN[emo] - slack) * base and r.get('quality', 0) >= Q_MIN
                and (not eo_base or (r.get('eye_open') and min(r['eye_open']) >= (EYE_OPEN_MIN[emo] - slack) * eo_base)))
def mouth_ok(r, mw0, emo='smile', lift0=0.0, slack=0.0):
    """lips together, or a smile that shows teeth: wide (>= SMILE_W x the person's usual mouth width), corners lifted (>= LIFT_MIN
    over their usual) and flat - a mouth forming a word fails one of the three; serious / angry / confused = lips together.
    slack: the re-check of a sheet frame allows +0.006 on the lip gap (resampling noise on a bearded mouth: Nick 0.0137 -> 0.018)"""
    if r.get('open', 1) <= MOUTH_MAX + slack: return True
    return (emo in ('smile', 'laughing') and r.get('mouth_w', 0) >= SMILE_W * mw0 and r.get('smile', -1) >= lift0 + LIFT_MIN and r['open'] / max(1e-6, r['mouth_w']) <= 0.32)
def score(rows, mode, emo):
    good = [r for r in rows if r.get('yaw', 999) < 900 and r.get('quality', 0) >= Q_MIN and r.get('ci')]
    if not good: return []
    y0 = st.median(r['yaw'] for r in good) if mode == 'forward' else 0.0; p0 = st.median(r['pitch'] for r in good) if mode == 'forward' else 0.0
    for r in good:
        if 'eh' not in r: r['eh'] = eye_height(r['file'], r)
    opened = [min(r['eh']) for r in good if not r.get('l_closed') and not r.get('r_closed')]
    if not opened: return []
    base = st.median(opened); eo = [min(r['eye_open']) for r in good if r.get('eye_open')]; eo_base = st.median(eo) if eo else None
    return [dict(r, eye_dev=round(max(abs(g - 0.5) for g in r['gx']) + abs(r['yaw'] - y0) / 60, 3), eye_base=base, eo_base=eo_base, pose0=[y0, p0]) for r in good if eyes_ok(r, base, y0, p0, emo, eo_base)]

def mouth_base(W, p):
    """the person's USUAL mouth width (a word keeps it, a smile stretches it): the median over 40 frames spread across their
    whole camera file, smile-classified frames left out - cached per episode in edit/mouth_base.json (a short where the
    person smiles throughout, s15, has no neutral frame of its own to measure)"""
    cp = f'{W}/edit/mouth_base.json'; cache = C.load(cp, {}) or {}; who = p['name']
    if cache.get(who, {}).get('path') == p['path'] and 'lift' in cache[who]: return cache[who]['mouth_w'], cache[who]['lift']
    tmp = f'{W}/edit/_mouth_{who}'; shutil.rmtree(tmp, ignore_errors=True); os.makedirs(tmp)
    dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', p['path']], capture_output=True, text=True).stdout.strip() or 0)
    for k in range(40): subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{dur * (k + 0.5) / 40:.2f}', '-i', p['path'], '-frames:v', '1', '-vf', 'scale=1280:-2', '-q:v', '3', f'{tmp}/m{k:02d}.jpg'])
    rows = [r for r in faces(sorted(glob.glob(f'{tmp}/m*.jpg'))) if r.get('mouth_w')]; shutil.rmtree(tmp, ignore_errors=True)
    plain = [r for r in rows if not r.get('ci_smile')]; vals = plain if len(plain) >= 8 else rows
    if len(vals) < 8: C.fail(f'{who}: only {len(vals)} faces in 40 frames of {p["path"]} - cannot measure the usual mouth width')
    cache[who] = {'path': p['path'], 'mouth_w': round(st.median(r['mouth_w'] for r in vals), 4), 'lift': round(st.median(r['smile'] for r in vals), 4), 'n': len(vals), 'plain': len(plain), 'at': C.now()}
    C.save(cp, cache); return cache[who]['mouth_w'], cache[who]['lift']

def safe_zone(path, headline=None):
    """everything important inside the centre 3:4 (the IG / TikTok grid): every face (>= 8 % of the frame height) and
    every line of the headline, measured with Vision (facequality, ocr); the headline must read back complete -> problems"""
    out = []; lo, hi = SAFE[0] + SAFE_MARGIN, SAFE[1] - SAFE_MARGIN
    fq = json.loads(subprocess.run([f'{TOOLS}/facequality', path], capture_output=True, text=True).stdout.splitlines()[0]); k = TH / fq['h']
    for f in fq.get('faces', []):
        if f['h'] * k < 0.08 * TH: continue
        if f['y'] * k < lo or (f['y'] + f['h']) * k > hi: out.append(f'a face at y {f["y"] * k:.0f}-{(f["y"] + f["h"]) * k:.0f} is outside the centre 3:4 ({lo}-{hi})')
    if not [f for f in fq.get('faces', []) if f['h'] * k >= 0.08 * TH]: out.append('no main face found')
    if headline:
        o = json.loads(subprocess.run([f'{TOOLS}/ocr', path], capture_output=True, text=True).stdout.splitlines()[0]); k = TH / o['h']
        norm = lambda t: re.sub(r'[^A-Z0-9$>%]', '', t.upper()); want = norm(headline); got = ''
        for l in o['lines']:
            t = norm(l['text'])
            if len(t) >= 2 and t in want:
                got += t
                if l['y'] * k < lo or (l['y'] + l['h']) * k > hi: out.append(f'headline line "{l["text"]}" at y {l["y"] * k:.0f}-{(l["y"] + l["h"]) * k:.0f} is outside the centre 3:4 ({lo}-{hi})')
        if not all(w in got for w in re.findall(r'[A-Z0-9$%]+', headline.upper())): out.append(f'the headline does not read back as "{headline}" (OCR: {[l["text"] for l in o["lines"]][:6]})')
    return out

def cover_people(W, v, P, S, ep):
    """whose face the cover shows (Colden 2026-10-02): a short that posts to Create with Colden -> COLDEN (the show file's
    channels.face), as on his long-form thumbnails, even where the guest says the line; otherwise the people who SPEAK in the
    short (a listener in the 3-stack is never its face). He must be on screen in it, or ASK"""
    import postcopy as PC
    dest = v.get('destination') or (next((t for t in (C.load(f'{W}/themes.json') or {}).get('themes', []) if t['id'] == P.get('short', '').split('/')[0]), {}) or {}).get('dest')
    talkers = {r['key'].split(':', 1)[1] for r in P['runs'] if ':' in r['key']}
    if S['channels']['primary'] in PC.brands(dest):
        face = S['channels'].get('face') or C.fail('the show file has no channels.face')
        p = next((x for x in ep['people'] if x['name'] == face), None) or C.fail(f'{face} is not in this episode')
        if not [x for x in P['items'] if x['kind'] == 'video' and x['clip'] == os.path.basename(p['path']) and x['enabled'] and x['src_out'] - x['src_in'] >= 24]:
            C.ask(f'{P.get("short")}: posts to {S["channels"]["labels"][S["channels"]["primary"]]} but {face} is never on screen in it - his face is the rule there; tell Colden')
        return {face}
    return talkers

def frames(W, tid, emo='smile'):
    """the shortlist = the best stills IN THE SHORT (Colden 2026-10-02): every person who SPEAKS in it, their camera file inside
    the short's own pieces at 6 frames a second, the eyes / gaze / pose / quality gates, the smile classifier for a smile,
    the mouth either closed or a real (wide) smile - never a mouth forming a word; silent frames rank first. Two pools:
    the THUMBNAIL picks (teeth welcome) and the AI REFERENCES (lips together). Nothing passes -> ASK (never the rest of
    the episode: the still is from the short)"""
    import themes as T, cut as K
    v, P = approved(W, tid); ep = C.episode(W); S = C.show(ep['show']); cutj = C.load(f'{W}/edit/{tid}/cut.json'); X = K.Ctx(T.Work(W), audio=False)
    if emo not in EMOTIONS: C.fail(f'emotion one of {EMOTIONS}')
    d = cdir(W, tid); cand = f'{d}/cand'; shutil.rmtree(cand, ignore_errors=True); os.makedirs(cand); picked, ai_pool, n_files, n_faces = [], [], 0, 0
    def podcut(rec_f):
        sh = next((x for x in cutj['shots'] if x['rec'] <= rec_f < x['rec'] + x['b'] - x['a']), None)
        return sh['a'] + rec_f - sh['rec'] if sh else None
    people = cover_people(W, v, P, S, ep)
    for p in ep['people']:
        who = p['name']; clip = os.path.basename(p['path']); fps = p['fps']; mode = (S.get('gaze') or {}).get(who, 'camera')
        if who not in people: continue
        items = [x for x in P['items'] if x['kind'] == 'video' and x['clip'] == clip and x['enabled'] and x['src_out'] - x['src_in'] >= 24]
        files = []
        for k, x in enumerate(items):
            t0 = (x['src_in'] + 4) / fps; dur = (x['src_out'] - x['src_in'] - 8) / fps; tag = f'{who}{k:02d}'
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{t0:.3f}', '-t', f'{dur:.3f}', '-i', p['path'], '-vf', 'fps=6,scale=1280:-2', '-q:v', '3', f'{cand}/{tag}_%04d.jpg'], check=True)
            for f in sorted(glob.glob(f'{cand}/{tag}_*.jpg')):
                t = t0 + (int(f[-8:-4]) - 0.5) / 6; rec_f = x['rec'] + int(round(t * fps)) - x['src_in']; pf = podcut(rec_f)
                speaking = pf is None or any(w['who'] == who and w['a'] - SPEAK_PAD <= pf <= w['b'] + SPEAK_PAD for w in X.words_in(pf - 40, pf + 40))
                files.append((f, t, rec_f, speaking))
        if not files: continue
        n_files += len(files); meta = {f: (t, r, sp) for f, t, r, sp in files}; rows = faces([f for f, *_ in files]); n_faces += len(rows)
        for r in rows: r['t'], r['rec'], r['speaking'] = meta[r['file']]
        ok = score(rows, mode, emo)
        if emo in ('smile', 'laughing'): ok = [r for r in ok if r.get('ci_smile')]
        mw0, lift0 = mouth_base(W, p)                                                # this person's usual mouth width + corner lift (episode-wide, not this short's: s15 is all smile)
        for r in ok: r['mouth_base'] = mw0; r['lift_base'] = lift0
        ok = [r for r in ok if mouth_ok(r, mw0, emo, lift0)]
        def z(key): vals = [r[key] for r in rows]; m = st.median(vals); sd = (st.pstdev(vals) or 1e-6); return lambda r: (r[key] - m) / sd
        zs, zw, zo = z('smile'), z('mouth_w'), z('open'); ze = lambda r: min(r['eh']) / max(1e-6, r['eye_base'])
        keyf = {'smile': lambda r: -(min(zs(r), 3.0) + 0.5 * min(zw(r), 3.0)) + 3 * r['eye_dev'] - 3.0 * min(ze(r), 1.0) + 6.0 * max(0, ze(r) - 1.08) + abs(r['pitch'] - r['pose0'][1]) / 6 - 2 * r.get('quality', 0),
                'laughing': lambda r: -(zs(r) + zw(r) + zo(r)) + 3 * r['eye_dev'], 'angry': lambda r: (zs(r) + zw(r)) + 3 * r['eye_dev'],
                'confused': lambda r: -abs(r['roll']) / 10 + zs(r) + 3 * r['eye_dev'],
                'serious': lambda r: 3 * r['eye_dev'] - 3.0 * min(ze(r), 1.0) + abs(r['pitch'] - r['pose0'][1]) / 6 - 2 * r.get('quality', 0) + 10 * r.get('open', 0)}[emo]
        for r in ok: picked.append(dict(r, who=who, src=p['path'], fps=fps, mode=mode, key=keyf(r), pool='thumb'))
        # the AI REFERENCE pool (Colden 2026-10-02: "find a good still face or grin with no teeth, send that to higgsfield. But keep
        # the best full smiles for the real thumbnail"): the strict smile eye gates, lips together, a grin ranked first
        lips = [r for r in score(rows, mode, 'smile') if r.get('open', 1) <= MOUTH_MAX]
        for r in lips: r['mouth_base'] = mw0; r['lift_base'] = lift0
        ks = lambda r: -(min(zs(r), 3.0) + 0.5 * min(zw(r), 3.0)) + 3 * r['eye_dev'] - 2 * r.get('quality', 0)
        for r in lips: ai_pool.append(dict(r, who=who, src=p['path'], fps=fps, mode=mode, key=ks(r), pool='ai'))
    picked.sort(key=lambda r: (r['speaking'], r['key'])); ai_pool.sort(key=lambda r: (r['speaking'], r['key'])); short = []   # Colden 2026-10-02: "Talking always ranks lower than an actual smile" - every silent frame before every talking one
    def take(pool, cap):
        k = 0
        for r in pool:
            if k == cap: break
            if all(r['who'] != x['who'] or abs(r['t'] - x['t']) > 1.0 for x in short if x['pool'] == r['pool']) and r['file'] not in [x['file'] for x in short]: short.append(r); k += 1
    take(picked, 8)
    if not short: C.ask(f'{tid}: no frame in the short passes the gates for anyone who speaks in it as "{emo}" (eyes fully open, to the lens / Jake forward, the expression, never a mouth caught on a word, sharp) - run it again with the emotion that fits the theme (--emotion serious | confused | angry | laughing; serious = lips together, a point being made), else tell Colden')
    take(ai_pool, 4)
    if not any(x['pool'] == 'ai' or (x.get('open') or 1) <= MOUTH_MAX for x in short): print(f'  WARNING {tid}: no lips-together frame for the AI reference - `airef` will refuse every tile; try another emotion')
    sheet = Image.new('RGB', (1920, 1080), 'black'); dr = ImageDraw.Draw(sheet)
    try: fnt = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Bold.ttf', 30); sm = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Bold.ttf', 22)
    except Exception: fnt = sm = ImageFont.load_default()
    slot = {'thumb': 0, 'ai': 8}                                                   # rows 1-2: thumbnail picks (purple) | row 3: AI references (teal)
    for i, r in enumerate(short):
        im = Image.open(r['file']).convert('RGB'); cx, cy, sz = r['x'] + r['w'] / 2, r['y'] + r['h'] / 2, max(r['w'], r['h']) * 0.85
        im = im.crop((int(max(0, cx - sz * 1.33)), int(max(0, cy - sz)), int(min(im.width, cx + sz * 1.33)), int(min(im.height, cy + sz)))).resize((480, 360))
        j_ = slot[r['pool']]; slot[r['pool']] += 1; col = '#7C3AED' if r['pool'] == 'thumb' else '#0D9488'
        X_, Y_ = (j_ % 4) * 480, (j_ // 4) * 360; sheet.paste(im, (X_, Y_)); dr.rectangle([X_, Y_, X_ + 46, Y_ + 40], fill=col); dr.text((X_ + 8, Y_ + 4), str(i + 1), font=fnt, fill='white')
        dr.text((X_ + 56, Y_ + 10), f'{r["who"]} {r["rec"] / 30:.1f}s' + (' talking' if r['speaking'] else '') + (' · AI ref (lips)' if r['pool'] == 'ai' else (' · teeth' if r.get('open', 0) > TEETH_MAX else '')), font=sm, fill='white')
    sheet.save(f'{d}/still_sheet.jpg', quality=85)
    R = rec(W, tid); R.update({'short': tid, 'version': v['v'], 'emotion_wanted': emo, 'scope': 'short', 'rules': 'round 2 (2026-10-02)',
              'shortlist': [{'n': i + 1, 'who': r['who'], 'file': r['file'], 't': r['t'], 'rec': r['rec'], 'src': r['src'], 'fps': r['fps'], 'mode': r['mode'], 'yaw': r['yaw'], 'pitch': r['pitch'], 'gx': r['gx'],
                             'smile': r['smile'], 'eh': r['eh'], 'eye_base': r['eye_base'], 'pose0': r['pose0'], 'ci_smile': r.get('ci_smile'), 'quality': r.get('quality'), 'speaking': r['speaking'], 'open': r.get('open'), 'mouth_w': r.get('mouth_w'), 'mouth_base': r.get('mouth_base'), 'lift_base': r.get('lift_base'), 'eo_base': r.get('eo_base'), 'pool': r['pool']} for i, r in enumerate(short)],
              'stats': {'sampled': n_files, 'faces': n_faces, 'passed': len(picked), 'ai_ref_pool': len(ai_pool)}, 'still_confirmed': None, 'ai_ref': None}); save(W, tid, R)
    print(f'{tid}: {n_files} frames of the people who speak, {n_faces} faces, {len(picked)} pass for the thumbnail, {len(ai_pool)} lips-together for the AI reference\n'
          f'  LOOK: {d}/still_sheet.jpg   then: cover.py still <WORK> {tid} <n> <emotion> "<what you see>"  +  cover.py airef <WORK> {tid} <n> "<what you see>"')

def near_pick(W, tid, n, ok):
    """the frame-exact pick: the 21 camera frames around sheet entry #n, the nearest one (<= 3 frames) where ok(face row,
    shortlist entry) holds -> (entry, best row, camera frame number, offset from the sheet). The gates are judged on the
    SAME 1280-px scale the sheet was measured on (the pixel eye-height and Vision's numbers shift with resolution: Nick's
    serious tiles passed at 1280 and failed at 4K); the frame handed back is the full-resolution one"""
    d = cdir(W, tid); R = rec(W, tid); s = next((x for x in R.get('shortlist') or [] if x['n'] == int(n)), None)
    if not s: C.fail(f'no shortlist entry {n} (cover.py frames first)')
    fps = s['fps']; tmp = f'{d}/_near'; shutil.rmtree(tmp, ignore_errors=True); os.makedirs(tmp)
    f0 = max(0, int(round(s['t'] * fps)) - 10)                                   # 10 frames either side of the sheet's frame, frame-exact
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{(f0 - 0.5) / fps:.4f}', '-i', s['src'], '-frames:v', '21', f'{tmp}/n%02d.png'], check=True)   # half a frame early: the first frame out IS f0
    near = sorted(glob.glob(f'{tmp}/n*.png'))
    if len(near) != 21: C.fail(f'could not read the 21 frames around {s["t"]:.2f} s ({len(near)})')
    small = []
    for f in near: Image.open(f).convert('RGB').resize((1280, int(round(1280 * Image.open(f).height / Image.open(f).width))), Image.LANCZOS).save(f[:-4] + '_s.jpg', quality=93); small.append(f[:-4] + '_s.jpg')
    import numpy as np
    g = lambda f: np.asarray(Image.open(f).convert('L').resize((160, 90))).astype(float); ref = g(s['file']); dif = [float(np.mean(np.abs(g(f) - ref))) for f in near]; mid = int(np.argmin(dif))
    if min(dif) > 4.0: C.fail(f'the frame shown as #{n} cannot be found around {s["t"]:.2f} s (best difference {min(dif):.1f}) - run cover.py frames again')
    good = []
    for r in faces(small):
        r['eh'] = eye_height(r['file'], r)
        if ok(r, s): good.append(r)
    if not good: C.fail(f'none of the 21 frames around #{n} passes the gates - pick another number')
    best = min(good, key=lambda r: (abs(small.index(r['file']) - mid), -min(r['eh']))); k = small.index(best['file']); off = k - mid
    if abs(off) > 3: C.fail(f'the nearest frame that passes is {abs(off)} frames from the one on the sheet - not the picture you looked at; pick another number')
    src_frame = f0 + k; out = f'{d}/_pick.png'; shutil.copyfile(near[k], out); shutil.rmtree(tmp, ignore_errors=True)
    return s, dict(best, file=out), src_frame, off

def face_files(full, face_out, check_out):
    """the face crop (a Higgsfield reference) + the eyes check (face + both eyes, large) of one frame -> (face row, image)"""
    j = json.loads(subprocess.run([f'{TOOLS}/face', full], capture_output=True, text=True).stdout.splitlines()[0])
    im = Image.open(full).convert('RGB'); cx, cy, sz = j['x'] + j['w'] / 2, j['y'] + j['h'] / 2, max(j['w'], j['h']) * 1.6
    im.crop((int(max(0, cx - sz)), int(max(0, cy - sz)), int(min(im.width, cx + sz)), int(min(im.height, cy + sz)))).save(face_out)
    chk = Image.new('RGB', (960, 480), 'black'); chk.paste(im.crop((int(cx - j['w'] * 0.7), int(cy - j['h'] * 0.7), int(cx + j['w'] * 0.7), int(cy + j['h'] * 0.7))).resize((480, 480)), (0, 0))
    for k, e in enumerate(('le', 're')):
        x0, y0_, x1, y1 = j[e]; w = x1 - x0; chk.paste(im.crop((x0 - w // 4, y0_ - w // 2, x1 + w // 4, y1 + w // 2)).resize((480, 240)), (480, k * 240))
    chk.save(check_out, quality=90); return j, im

def still(W, tid, n, emotion, saw):
    """the THUMBNAIL still (the Resolve cover): the best full smile in the short, teeth welcome - or the emotion that fits the theme"""
    if emotion not in EMOTIONS: C.fail(f'emotion one of {EMOTIONS}')
    if len(saw) < 20: C.fail('say what you see: the eyes, the expression, why it fits the short')
    def ok(r, s):
        y0, p0 = s['pose0']
        return eyes_ok(r, s['eye_base'], y0, p0, emotion, s.get('eo_base'), slack=0.05) and (emotion not in ('smile', 'laughing') or r.get('ci_smile') or not s.get('ci_smile')) and mouth_ok(r, s.get('mouth_base', 0), emotion, s.get('lift_base', 0), slack=0.006)
    R0 = rec(W, tid); s0 = next((x for x in R0.get('shortlist') or [] if x['n'] == int(n)), None) or C.fail(f'no shortlist entry {n}')
    silent = [x['n'] for x in R0['shortlist'] if x['pool'] == 'thumb' and x['who'] == s0['who'] and not x.get('speaking')]
    if s0.get('speaking') and silent: C.fail(f'#{n} is a talking frame and silent frame(s) {silent} of {s0["who"]} are on the sheet - "talking always ranks lower than an actual smile" (Colden 2026-10-02): pick one of those, or say why not in a new shortlist')
    s, best, src_frame, off = near_pick(W, tid, n, ok); d = cdir(W, tid); R = rec(W, tid); base = s['eye_base']
    full = f'{d}/still_full.png'; os.replace(best['file'], full)
    R['speaker'] = s['who']
    j, im = face_files(full, f'{d}/ref_face.png', f'{d}/eyes_check.jpg')
    crop_single(im, single_props(W, R['speaker'])).save(f'{d}/crop_check.jpg', quality=90)
    if (R.get('ai_ref') or {}).get('who') not in (None, s['who']): R['ai_ref'] = None          # the AI reference must be the same person
    if emotion != 'smile' and (best.get('open') or 1) > MOUTH_MAX + 0.006: C.fail(f'a "{emotion}" still with a parted mouth ({best.get("open")}) - lips together, or pick another')
    R.update(still=full, src_frame=src_frame, still_confirmed={'n': int(n), 'emotion': emotion, 'wanted': R.get('emotion_wanted'), 'saw': saw, 'at': C.now(), 'offset_from_sheet': off,
             'eye_height': best['eh'], 'eye_base': base, 'blink_classifier': 'both eyes open', 'smile_classifier': bool(best.get('ci_smile')), 'mouth_open': best.get('open')}, ref_face=f'{d}/ref_face.png'); save(W, tid, R)
    print(f'{tid}: still {n} -> camera frame {src_frame} ({off:+d} from the sheet), eyes open, smile classifier {bool(best.get("ci_smile"))}, mouth {best.get("open")}\n  LOOK: {d}/eyes_check.jpg and {d}/crop_check.jpg')

def airef(W, tid, n, saw):
    """the HIGGSFIELD REFERENCE (Colden 2026-10-02): a good face or grin with NO TEETH from the short, the same person as the
    thumbnail still - the AI copies what it is shown, and a toothy reference loses the person's identity"""
    if len(saw) < 20: C.fail('say what you see: the eyes, the mouth (lips together), why it is a good likeness')
    R = rec(W, tid)
    if not R.get('still_confirmed'): C.fail(f'{tid}: confirm the thumbnail still first (cover.py still) - the AI reference is the same person')
    s0 = next((x for x in R['shortlist'] if x['n'] == int(n)), None) or C.fail(f'no shortlist entry {n}')
    if s0['who'] != R['speaker']: C.fail(f'#{n} is {s0["who"]}, the thumbnail is {R["speaker"]} - the AI cover shows the same person')
    if (s0.get('open') or 1) > MOUTH_MAX: C.fail(f'#{n} shows teeth / a parted mouth ({s0.get("open")} > {MOUTH_MAX}) - the AI reference is lips together (a teal AI-ref tile)')
    def ok(r, s):
        y0, p0 = s['pose0']
        return eyes_ok(r, s['eye_base'], y0, p0, 'smile', s.get('eo_base'), slack=0.05) and r.get('open', 1) <= MOUTH_MAX + 0.006
    s, best, src_frame, off = near_pick(W, tid, n, ok); d = cdir(W, tid)
    full = f'{d}/ai_ref_full.png'; os.replace(best['file'], full); j, im = face_files(full, f'{d}/ai_ref_face.png', f'{d}/ai_ref_check.jpg')   # ai_ref_face.png is the CHECK image only - never sent
    if (best.get('open') or 1) > MOUTH_MAX + 0.006: C.fail(f'the AI reference frame measures mouth {best.get("open")} > {MOUTH_MAX} - pick another')
    R = rec(W, tid); R['ai_ref'] = {'n': int(n), 'who': s['who'], 'full': full, 'face': f'{d}/ai_ref_face.png', 'src_frame': src_frame, 'offset_from_sheet': off, 'mouth_open': best.get('open'), 'saw': saw, 'at': C.now()}
    save(W, tid, R); print(f'{tid}: AI reference {n} -> camera frame {src_frame} ({off:+d}), mouth {j.get("open")} (lips together)\n  LOOK: {d}/ai_ref_check.jpg')

def resolve(W, tid):
    """build -> render -> check; the source offset between ffmpeg's and Resolve's frame numbers is NOT constant (measured
    2026-10-02: +1 and 0 on the same COLDEN.mp4, 0 on NICK.mp4), so a mismatch is measured and the cover rebuilt once"""
    R = rec(W, tid)
    if R.get('resolve_pending'): R.setdefault('resolve_attempts', []).append(dict(R.pop('resolve_pending'), matched_offset='unchecked')); save(W, tid, R)   # an earlier run's render: kept on record, rebuilt
    shift = RES_SHIFT
    for attempt in range(3):
        build_cover(W, tid, shift); off = check_cover(W, tid)
        if off == 0: return
        R = rec(W, tid); p_ = R.pop('resolve_pending'); R.setdefault('resolve_attempts', []).append(dict(p_, matched_offset=off)); save(W, tid, R)
        print(f'  {tid}: Resolve showed camera frame {off:+d} from the confirmed one - rebuilding with the source shifted {off:+d}'); shift += off
    C.fail(f'{tid}: the Resolve cover never landed on the confirmed frame')

def hook_single(P, who):
    """the cover is a SINGLE of the speaker: the hook goes where a single puts it (below the face, under the caption line),
    even when the short itself opens on a 3-stack (s05 2026-10-02: the stack's top hook landed on Jake's forehead)"""
    run = next((r for r in P['runs'] if r['key'] == f'single:{who}'), None) or next((r for r in P['runs'] if r['key'].startswith('single')), None)
    hy = run['cap_y'] if run else 1180                                   # a cover has no captions: the hook takes the caption line, just under the face
    return dict(P['hook'], rec=0, frames=N, fade_out=0, y=1 - hy / TH, hook_px=hy, caption_px=None)
def build_cover(W, tid, shift):
    import build as B
    v, P = approved(W, tid); R = rec(W, tid)
    if not R.get('still_confirmed') or R.get('version') != v['v']: C.fail(f'{tid}: no confirmed still for the approved version (cover.py frames -> LOOK -> cover.py still)')
    who = R['speaker']; p = person(W, who); clip = os.path.basename(p['path']); sf = R['src_frame']
    track = P['tracks']['video'].index(who) + 1; made = R.get('resolve_versions') or []; cv = 1 + max([int(re.search(r'cover\.v(\d+)\.json$', f).group(1)) for f in glob.glob(f'{W}/edit/{tid}/cover.v*.json')] or [0])   # every attempt writes its plan first: never reuse a name
    base = P['name'].rsplit(' v', 1)[0]; name = f'{base} cover v{cv}'
    Q = copy.deepcopy(P); Q.update(short=f'{tid}/cover', v=cv, name=name, building='zz BUILDING ' + name, frames=N, captions=[], tags=[], broll=[], beeps=[], censor=[], sources_used=[clip],
        items=[{'kind': 'video', 'track': track, 'clip': clip, 'src_in': sf - AT - shift, 'src_out': sf - AT - shift + N, 'rec': 0, 'enabled': True, 'props': single_props(W, who), 'layout': f'single:{who}'}],
        hook=hook_single(P, who), made_at=C.now(), cover_of=v['plan'], safe=[SAFE[0] + SAFE_MARGIN, SAFE[1] - SAFE_MARGIN])   # hookfit keeps the hook inside the IG / TikTok grid
    path = f'{W}/edit/{tid}/cover.v{cv}.json'; C.save(path, Q); kw = {'PROJECT': Q['project'], 'PLAN': path}
    r = B.rs('r_build.py', 120, STEP='sources', **kw)
    if r['problems']: C.fail(f'SOURCE GATE: {r["problems"]}')
    B.rs('r_build.py', 180, STEP='import', **kw); B.rs('r_build.py', 180, STEP='create', **kw)
    r = B.rs('r_build.py', 300, STEP='place', KIND='video', TRACK=track, **kw)
    if r['props_failed']: C.fail('Resolve refused the crop')
    B.rs('r_build.py', 240, STEP='hook', **kw); hf = B.rs('r_build.py', 300, STEP='hookfit', **kw)
    if not hf['inside_safe']: C.fail(f'the hook box is outside the centre-3:4 band {hf.get("safe")}: {hf}')
    r = B.rs('r_build.py', 240, STEP='verify', **kw)
    if r['problems']: C.fail(f'VERIFY: {r["problems"]} (the timeline keeps its zz BUILDING name)')
    d = cdir(W, tid); res = B.rs('r_render.py', 300, PROJECT=Q['project'], NAME=name, OUT=d, CN=f'resolve_cover_v{cv}', W=TW, H=TH, FRAME=AT, LIMIT=120)
    if not res.get('made'): C.fail(f'the cover frame did not render: {res}')
    R['resolve_pending'] = {'v': cv, 'timeline': name, 'plan': path, 'tif': res['made'], 'shift': shift, 'hook': {k: hf.get(k) for k in ('size', 'box', 'moved_down')}}; save(W, tid, R)

def check_cover(W, tid):
    """GATES on the rendered Resolve cover (re-runnable: `cover.py resolve` resumes here when a render is pending)"""
    import numpy as np
    R = rec(W, tid); pend = R.get('resolve_pending') or C.fail(f'{tid}: no rendered Resolve cover waiting for its check'); who = R['speaker']; p = person(W, who); sf = R['src_frame']; d = cdir(W, tid)
    out = f'{d}/1 resolve.png'; subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', pend['tif'], '-pix_fmt', 'rgb24', out], check=True)
    im = Image.open(out); assert im.size == (TW, TH), f'cover is {im.size}'
    box = (pend.get('hook') or {}).get('box'); top = int(min(box[2], 1000)) - 20 if box else 900          # box = [x0, x1, y0, y1] (measure_box.py): compare ABOVE the hook box
    g = lambda x: np.asarray(x.convert('L').crop((0, 0, TW, top)).resize((216, top // 5))).astype(float)
    tmp = f'{d}/_chk'; shutil.rmtree(tmp, ignore_errors=True); os.makedirs(tmp)                            # GATE: the rendered frame IS the confirmed one (+-1 by pixels)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{(sf - 2.5) / p["fps"]:.4f}', '-i', p['path'], '-frames:v', '5', f'{tmp}/c%d.png'], check=True)
    props = single_props(W, who); dif = [float(np.mean(np.abs(g(crop_single(Image.open(f'{tmp}/c{k}.png').convert('RGB'), props)) - g(im)))) for k in range(1, 6)]
    off = int(np.argmin(dif)) - 2; shutil.rmtree(tmp, ignore_errors=True)
    if off != 0 and dif[2] - min(dif) <= 0.4: off = 0                        # neighbouring frames look the same (a still face): the confirmed one is as good a match
    if off != 0: return off
    j = json.loads(subprocess.run([f'{TOOLS}/face', out], capture_output=True, text=True).stdout.splitlines()[0])
    if not j.get('ci') or j.get('l_closed') or j.get('r_closed'): C.fail(f'the rendered cover fails the blink classifier: {j}')
    v, P = approved(W, tid); sz = safe_zone(out, ' '.join(P['hook']['lines']))
    if sz: C.fail(f'{tid}: the Resolve cover breaks the centre-3:4 rule (IG / TikTok grid): {sz}')
    made = R.get('resolve_versions') or []; made.append(dict(pend, file=out, frame_offset=off, frame_diffs=[round(x, 1) for x in dif], at=C.now()))
    R['resolve_versions'] = made; R['resolve_cover'] = out; R.pop('resolve_pending', None); save(W, tid, R)
    print(f'{tid}: Resolve cover -> {out} (timeline {pend["timeline"]}, frame {off:+d}, differences {[round(x, 1) for x in dif]})\n  LOOK at it'); return 0

def brief(W, tid):
    v, P = approved(W, tid); R = rec(W, tid)
    if not R.get('still_confirmed'): C.fail(f'{tid}: no confirmed still - the AI cover shows the same person')
    if not (R.get('ai_ref') or {}).get('face'): C.fail(f'{tid}: no AI reference - cover.py airef <WORK> {tid} <n> "<what you see>" (a teal tile: lips together, never teeth)')
    th = next(t for t in C.load(f'{W}/themes.json')['themes'] if t['id'] == tid); ep = C.episode(W)
    b = {'short': tid, 'title': th['title'], 'hook_text': th.get('hook_text'), 'summary': th.get('summary'), 'speaker': R['speaker'], 'emotion': R['still_confirmed']['emotion'],
         'show': ep['show_name'], 'model': 'nano_banana_pro (Higgsfield reports a finished Pro job back as nano_banana_2 - that is the same job; the page says Nano Banana Pro)', 'resolution': '2k', 'aspect_ratio': '9:16',
         'image_reference': R['ai_ref']['full'],                             # ONE reference = the FULL-RESOLUTION camera frame, NEVER a crop (Colden 2026-10-02 23:35: "always use the full resolution shot from resolve. STOP DOING THAT [cropping]") - "@Image1" in the prompt; lips together, the generator never sees teeth
         'prompt_file': f'{cdir(W, tid)}/prompt.json', 'headline': R.get('headline') or 'NOT DECIDED - cover.py headline <WORK> <id> "<1-3 words>" first',
         'steps': ['1. READ data/shorts/packaging_brief.md "What Studio said" + the cover patterns; fill every <<placeholder>> in cover/prompt.json (the scene idea tied to THIS short: a concrete prop or place, never a plain face at a desk; keep the wardrobe line unless the scene needs a change) - SHOW COLDEN the filled JSON before generating',
                   '2. generate_image model nano_banana_pro, aspect_ratio 9:16, resolution 2k, medias = [the ONE reference ai_ref_full.png]; the prompt = the JSON object text itself (no fences, no prose)',
                   '3. save the generate_image submission + the jobs_wait result verbatim to cover/job_<n>.json; download the image; LOOK at it (likeness, lips together, headline spelled, nothing banned, nothing important in the top / bottom eighth)',
                   '4. cover.py add <WORK> <id> <9:16 file> --headline "<exact text>" --model nano_banana_pro --job cover/job_<n>.json --saw "..." --prompt cover/prompt.json'],
         'rules': ['the person from the references, recognisably himself, big in the 3:4 frame',
                   'NO TEETH - lips together (Colden 2026-10-02 hard rule: a toothy AI smile loses the person\'s identity); other expressions are fine without teeth',
                   'eyes open; to the lens (Jake: looking just past it, his own pose)', 'ONE visual idea that says what the short is about - never a plain face on a studio background',
                   'at most THREE words of headline, big bold type, spelled exactly, in the upper part of the CENTRE 3:4 band (y 264-1656 of 1920): below the top eighth of the frame, above the face; the face in the middle of the frame',
                   'the prompt says "lips together, no teeth" in those words (add refuses a prompt without them, or one asking for a grin / laugh)',
                   'the prompt refers to him as "@Image1" (one attached reference) scoped to IDENTITY ONLY, with do_not_transfer (the studio, the mic, the lighting); it never contains "3:4"',
                   'the headline = a line of the hook / title (gated words) or words carrying a WIN pattern of the brief; shorter is better (one giant word won the PYXIS test)',
                   'no microphones, AirPods, headphones, logos, film posters / film art, or real third parties'],
         'gates (cover.py add)': ['the file is 9:16', f'every face and every headline line inside y {SAFE[0] + SAFE_MARGIN}-{SAFE[1] - SAFE_MARGIN} of 1920 (the centre 3:4)',
                                  f'mouth openness <= {TEETH_MAX} (teeth measured 0.044+)', 'the headline reads back exactly (OCR)', 'the job record was submitted as nano_banana_pro with ONE reference', 'the prompt names @Image1, says lips together, no teeth, never 3:4']}
    S = C.show(ep['show']); gz = ((S.get('gaze') or {}).get(R['speaker']) or 'camera')
    gaze = 'direct eye contact with the viewer, looking into the lens' if gz == 'camera' else 'looking straight ahead, just past the lens (his own on-camera pose)'
    pt = f'{cdir(W, tid)}/prompt.json'
    if not R.get('headline'): C.fail(f'{tid}: no headline decided - cover.py headline <WORK> {tid} "<1-3 words>" (Colden decides; the hook box carries it)')
    if not os.path.exists(pt): C.save(pt, prompt_template(th, R, R['speaker'], gaze))          # a filled prompt is never overwritten by a re-run
    C.save(f'{cdir(W, tid)}/brief.json', b); print(json.dumps(b, indent=1, ensure_ascii=False)); print(f'\nPROMPT TEMPLATE: {pt} - fill the <<placeholders>>, show Colden, then send that JSON text as the prompt')

TEETH_WORDS = re.compile(r'\b(teeth|toothy|grin(ning)?|big smile|wide smile|broad smile|beaming|laughing|laugh)\b', re.I)
NO_TEETH = re.compile(r'\b(no|without|never|not showing|hide|hidden|closed[- ]lip|lips (together|closed)|mouth closed)\b', re.I)
VAGUE = re.compile(r'\b(masterpiece|viral|perfect|8k|ultra[- ]?detailed|ultra[- ]?realistic|award[- ]winning|best quality|trending|hyper[- ]?detailed)\b', re.I)
PLACEHOLDER = re.compile(r'<<[^>]*>>')
BANNED_PROPS = ('microphone', 'earbud', 'logo', 'poster', 'teeth', 'people')
MAX_HEAD_WORDS = 3                                                                  # the cover headline: 1-3 words, big
NAMES = ('Colden', 'Colton', 'Jake', 'Todd', 'Nick', 'Raisher', 'Williams')          # the people on the shows: never in a prompt, the subject is @Image1
def prompt_template(th, R, who, gaze, wardrobe='the same clothes as in @Image1', zone=None):
    zone = zone or R.get('headline_zone') or 'top'
    # `who` is only used for the gate below (his name must NOT appear in the prompt - Colden 2026-10-02 23:10: the model binds the reference by its tag, a name means nothing to it)
    """the JSON prompt for one AI cover (Colden's Nano Banana Pro guide, 2026-10-02): every locked rule pre-filled, the
    creative part left as <<placeholders>> Claude replaces (add refuses any left). The reference is scoped to IDENTITY
    ONLY with do_not_transfer - round-2 s15 copied the whole studio (LED panels, shelves, desk, lamp) because nothing
    told the model what @Image1 was NOT for."""
    return {
        'task': f'Create one finished vertical social cover image for a short film-industry podcast clip titled "{th["title"]}"; it is seen as a small tile in the Instagram and TikTok profile grids.',
        'format': {'aspect_ratio': '9:16', 'orientation': 'portrait'},
        'viewer_read': '<<what a stranger understands in ONE second from the picture alone - the claim of the reel as a picture, e.g. "nobody came to his film">>',
        'click_reason': '<<why they tap: the question the picture plants, e.g. "why is he alone in there?">>',
        'main_prompt': '<<ONE coherent sentence: @Image1 (the man is only ever called @Image1, never a name), what he does, the setting, the single visual idea that says what the short is about - concrete, tied to this short, never a plain face at a desk>>',
        'reference_images': [{'tag': '@Image1', 'upload_order': 1, 'role': 'the identity of the man in @Image1, and nothing else',
                              'authoritative_for': ['facial identity, facial structure and proportions, apparent age, hairline and hair, cap if worn, facial hair, skin tone'],
                              'preserve': ['recognisable facial structure, natural skin texture, the same apparent age'],
                              'allowed_changes': ['pose, expression within the rules below, lighting, background, wardrobe as specified below'],
                              'do_not_transfer': ['the studio background: the purple LED light panels, the gear shelves, the desk, the lamp, the blinds, the air conditioner', 'the microphone and its boom arm', 'any earbuds or headphones', 'the reference lighting', 'any text in the reference']}],
        'priority_order': ['preserve the recognisable likeness of @Image1', 'lips together, no teeth', 'the face large and close, the prop beside it', 'no text anywhere, no sign or board above the head', 'natural light and realistic colour'],
        'subject': {'source': '@Image1', 'count': 1, 'framing': 'tight chest-up portrait: the face fills about 40 percent of the frame width (the camera close enough that it does), the setting shown only around and behind the head and shoulders, never a wide shot' + (f'; the top of the head at about {pct(ZONES["top"][1]) + 2} percent of the frame height, the eyes at about {pct(ZONES["top"][1]) + 14} percent' if zone == 'top' else f'; the top of the head at about {pct(SAFE[0] + SAFE_MARGIN) + 4} percent of the frame height, the chin above {pct(ZONES["bottom"][0]) - 4} percent'),
                    'pose': '<<body orientation, head orientation, hands - observable>>',
                    'expression': R['still_confirmed']['emotion'] + ': lips together, no teeth, a closed-mouth expression with the corners of the mouth slightly raised, both eyes open',
                    'gaze': gaze, 'wardrobe': wardrobe},
        'composition': {'viewpoint': 'eye level; all left and right directions refer to the viewer',
                        'layout': 'everything that matters lives in the middle three quarters of the frame height (the top and bottom eighths are cropped off in the profile grid); ' + zone_text(zone)[1] + '; the prop right beside the face so face and prop read as one shape at tile size',
                        'visual_hierarchy': ['the face and <<the prop or action>>, together', 'the soft dark background', 'nothing else'],
                        'depth': '<<foreground, middle ground, background in one line>>',
                        'clear_space': ('the upper third' if zone == 'top' else 'the lower third') + ' of the picture: the same soft dark background as the rest of the scene, no object, no light source, no sign or board - the headline is placed there later',
                        'edge_clearance': 'keep every face, prop and letter at least 14 percent in from the top edge and 14 percent in from the bottom edge, and 6 percent in from the sides'},
        'text': {'mode': 'leave_space_for_later', 'exact_copy': '', 'placement': text_placement(zone),
                 'typography': '', 'color': '',
                 'rules': ['render NO text of any kind: no words, letters, numbers, captions, signs, logos, labels or watermarks anywhere in the image', 'the headline is added later in that third']},
        'environment': {'setting': '<<a specific place tied to the short, described in one line>>', 'detail_level': 'simple and uncluttered, soft out-of-focus shapes, no readable signs, no blank boards, no film art'},
        'camera': {'perspective': 'eye level, a natural portrait perspective like an 85 mm lens, no wide-angle distortion of the face', 'focus': 'the eyes sharp', 'depth_of_field': 'soft background separation without blurring the face, the prop or the text'},
        'lighting': {'key': '<<direction and softness of the main light - WARM or neutral, natural skin, never a cool / blue / pale light on the face>>', 'fill': 'gentle fill keeping detail in the shadows', 'separation': 'subtle rim or background separation', 'consistency': 'one light direction with believable shadows on the face, the prop and the background'},
        'color_palette': {'dominant': ['<<two or three main colours of the scene>>'], 'accent': ['<<one accent colour>>'], 'skin_and_materials': 'natural skin tone and texture, realistic materials'},
        'style': {'medium': 'photorealistic editorial photography', 'finish': 'clean natural detail, moderate contrast, mild retouching, restrained sharpening'},
        'quality_controls': {'must_include': ['one person: @Image1, recognisably the same man', 'lips together, no teeth visible', 'the face large, filling about 40 percent of the frame width', 'the face and the prop inside the middle three quarters of the frame height'],
                             'must_avoid': ['changed facial proportions or apparent age', 'teeth visible, an open mouth, a grin', 'plastic skin or heavy beauty retouching', 'a microphone, a boom arm, earbuds or headphones', 'logos, brand marks, film posters, film titles or film artwork', 'other people, extra faces, duplicates of the subject', 'any text, letters, numbers, captions, signs or watermarks anywhere', 'a blank sign, board, banner, panel, marquee board or empty rectangle anywhere, above the head most of all', 'a wide shot where the person is small', 'the reference studio copied: purple LED panels, gear shelves, desk and lamp', 'anything important in the top or bottom eighth of the frame', 'oversharpening halos, crushed shadows, excessive saturation']}}

def headline(W, tid, text, zone='top'):
    """record the cover headline Colden decided (1-3 words) - the template and add use it; never silently replaced"""
    words = re.findall(r"[A-Za-z0-9$>%']+", text or '')
    if not 1 <= len(words) <= MAX_HEAD_WORDS: C.fail(f'the headline is {len(words)} words - 1 to {MAX_HEAD_WORDS}')
    import pack_learn as PL
    th = next((t for t in (C.load(f'{W}/themes.json') or {}).get('themes', []) if t['id'] == tid), None); pr = PL.headline_ok(text, th)
    if pr: C.fail(pr[0])
    if zone not in ZONES: C.fail(f'--zone top|bottom (the third of the picture the headline rests on)')
    R = rec(W, tid); R['headline'] = text.strip(); R['headline_zone'] = zone; save(W, tid, R)
    pt = f'{cdir(W, tid)}/prompt.json'
    if os.path.exists(pt):
        P = C.load(pt); P['text']['exact_copy'] = ''; P['text']['placement'] = text_placement(zone); P['composition']['layout'] = zone_text(zone)[1]; C.save(pt, P)
    print(f'{tid}: headline "{text.strip()}" on the {zone} third recorded (the add step sets it in the hook box)')
ZONES = {'top': (SAFE[0] + SAFE_MARGIN, SAFE[0] + SAFE_MARGIN + (SAFE[1] - SAFE[0] - 2 * SAFE_MARGIN) // 3),
         'bottom': (SAFE[1] - SAFE_MARGIN - (SAFE[1] - SAFE[0] - 2 * SAFE_MARGIN) // 3, SAFE[1] - SAFE_MARGIN)}   # Colden 2026-10-02 23:40: "title should rest on the top 3rd or the bottom 3rd. composition should flow around that"
def pct(y): return int(round(100 * y / TH))
def zone_text(zone):
    a, b = ZONES[zone]
    if zone == 'top': return (f'the headline is added later across the upper third of the picture, from about {pct(a)} to {pct(b)} percent of the frame height; that area is only the soft dark out-of-focus background of the scene continuing naturally - nothing bright, no object, and NOT a sign, board, banner, panel, wall patch or blank rectangle of any kind; the top of the head sits just below it, at about {pct(b) + 2} percent',
                             f'the headline owns the upper third of the picture (about {pct(a)}-{pct(b)} percent of the frame height: calm dark background only); the face sits directly under it in the middle third, large; the prop beside or just below the face in the lower third; the bottom eighth of the frame is background only')
    return (f'the headline is added later across the lower third of the picture, from about {pct(a)} to {pct(b)} percent of the frame height; that area is only calm, dark, out-of-focus foreground or background with nothing in it - NOT a sign, board, banner, panel, table edge or blank rectangle of any kind; the chin and the prop stay above it',
            f'the headline owns the lower third of the picture (about {pct(a)}-{pct(b)} percent of the frame height: calm dark background only); the face sits above it in the middle third, large, with the top of the head at about {pct(SAFE[0] + SAFE_MARGIN) + 4} percent; the prop beside the face; the top eighth of the frame is background only')
def text_placement(zone='top'): return zone_text(zone)[0]
def _unused_text_placement(): return 'the headline is added later over the area from about 24 percent to 38 percent of the frame height, directly above the head: that area is simply the dark, out-of-focus background of the scene continuing naturally, with nothing bright or busy in it - NOT a sign, board, banner, panel, wall patch or blank rectangle of any kind (round-4 s15 drew a big grey box there)'

def prompt_text(prompt):
    """--prompt may be the JSON text or a path to it -> the text as sent"""
    if prompt and os.path.exists(prompt): return open(prompt).read()
    return prompt or ''
def prompt_problems(txt, headline, th=None):
    """every rule of the prompt schema, checked on the JSON object as sent -> problems (nothing is recorded when one fails)"""
    import pack_learn as PL
    p = []
    try: P = json.loads(txt)
    except Exception as e: return [f'the prompt is not one JSON object ({str(e)[:60]}) - the guide: paste the JSON object itself, no prose, no fences; cover.py brief writes cover/prompt.json to fill in']
    if not isinstance(P, dict): return ['the prompt must be a JSON object']
    for name in NAMES:
        if re.search(r'\b' + name + r'\b', txt, re.I): p.append(f'the prompt calls the subject "{name}" - the model does not know that name; the subject is referred to ONLY as @Image1 (Colden 2026-10-02: "you are not using the @Image1 tag")')
    for k in ('viewer_read', 'click_reason'):
        if len(str(P.get(k, ''))) < 15 or '<<' in str(P.get(k, '')): p.append(f'"{k}" missing - the picture must tell a stranger what the reel is about in one second and give them a reason to tap (Colden 2026-10-02: "its boring and random to me")')
    if PLACEHOLDER.search(txt): p.append(f'placeholders left in the prompt: {PLACEHOLDER.findall(txt)[:3]} - replace every <<...>> with the real line')
    if VAGUE.search(txt): p.append(f'vague quality words ("{VAGUE.search(txt).group(0)}") do nothing for the model - describe what is seen instead')
    refs = P.get('reference_images') or []
    if len(refs) != 1 or (refs[0].get('tag') if isinstance(refs[0], dict) else None) != '@Image1': p.append('reference_images must hold exactly ONE entry tagged "@Image1"')
    else:
        r = refs[0]; dnt = ' '.join(r.get('do_not_transfer') or []).lower()
        if 'identity' not in str(r.get('role', '')).lower(): p.append('reference_images[0].role must scope @Image1 to identity')
        if not all(k in dnt for k in ('background', 'microphone')): p.append('reference_images[0].do_not_transfer must name the reference background and the microphone (round-2 s15 copied the whole studio)')
    sub = P.get('subject') or {}; ex = str(sub.get('expression', ''))
    if 'lips together' not in ex.lower() or 'no teeth' not in ex.lower(): p.append('subject.expression must say "lips together, no teeth" (the hard rule for AI covers)')
    ex_ = re.sub(r'\b(no|without|never|not showing)\s+(teeth|a grin|grinning|laughing)\b', '', ex, flags=re.I)         # "no teeth" is the rule itself
    if TEETH_WORDS.search(ex_): p.append(f'subject.expression asks for "{TEETH_WORDS.search(ex_).group(0)}" - an AI cover never shows teeth')
    if str(sub.get('source', '')) != '@Image1': p.append('subject.source must be "@Image1"')
    t = P.get('text') or {}
    if t.get('mode') != 'leave_space_for_later': p.append('text.mode must be "leave_space_for_later" - the model put the headline in the top eighth three times (s15 rounds 2-3); the headline is set in the hook box by cover.py add (Colden\'s guide: exact type goes in the editor)')
    if str(t.get('exact_copy') or '').strip(): p.append('text.exact_copy must be empty in leave_space_for_later mode (no text is rendered by the model)')
    if not re.search(r'\d+\s?(%|percent)', str(t.get('placement', ''))): p.append('text.placement must give the reserved band as percentages of the frame height')
    if not any(re.search(r'\bno (text|words)\b', str(r), re.I) for r in t.get('rules') or []): p.append('text.rules must say the model renders NO text')
    if re.search(r'\bheadline [A-Z]{3,}', P.get('main_prompt', '')): p.append('main_prompt spells the headline out - the model renders no text; describe the empty band instead')
    comp = P.get('composition') or {}; ctext = ' '.join(str(v) for v in comp.values()).lower()
    if not re.search(r'\b(upper|lower) third\b', ctext): p.append('composition.layout must say which third of the picture the headline owns (upper or lower) and that the face sits in the middle third (Colden 2026-10-02: "title should rest on the top 3rd or the bottom 3rd. composition should flow around that")')
    if 'middle three quarters' not in ctext: p.append('composition must keep the face and the headline in "the middle three quarters" of the frame height (the centre 3:4 rule, never written as 3:4)')
    if not re.search(r'\d+\s?(%|percent)', str(comp.get('edge_clearance', ''))): p.append('composition.edge_clearance must give the margins as percentages')
    lk = str((P.get('lighting') or {}).get('key', ''))
    if re.search(r'\b(cool|blue|bluish|pale|cyan|teal|cold)\b', lk, re.I): p.append(f'lighting.key asks for a cool / blue / pale light ("{lk[:50]}") - the face comes out blue-grey and the likeness goes (round 6 s15); the key on the face is warm or neutral')
    qc = P.get('quality_controls') or {}; avoid = ' '.join(qc.get('must_avoid') or []).lower()
    if re.search(r'\b(empty|clean|blank|plain) (band|wall)\b', P.get('main_prompt', '') + ' ' + str((P.get('environment') or {}).get('setting', '')), re.I): p.append('main_prompt / environment ask for an "empty band" or "plain wall" - the model draws a blank board there (round-4 s15); let the background continue, say nothing about a band')
    if 'board' not in avoid and 'sign' not in avoid: p.append('quality_controls.must_avoid must name a blank sign / board / panel (the model fills reserved space with one)')
    miss = [w for w in BANNED_PROPS if w not in avoid]
    if miss: p.append(f'quality_controls.must_avoid must name {miss} (mic, earbuds, logos, posters, teeth, other people)')
    if str(P.get('format', {}).get('aspect_ratio', '9:16')) != '9:16': p.append('format.aspect_ratio can only be 9:16 (the canvas is the API parameter)')
    nw = len(re.findall(r"[A-Za-z0-9$>%']+", headline or ''))
    if nw > MAX_HEAD_WORDS: p.append(f'the headline "{headline}" is {nw} words - an AI cover carries at most {MAX_HEAD_WORDS} (Colden 2026-10-02 23:20: "the title is too long"; one giant word won the PYXIS test)')
    p += PL.headline_ok(headline, th)
    return p

def job_model(job_file):
    """the model ids in the saved Higgsfield job record (the generate_image submission + the jobs_wait result, verbatim).
    Colden 2026-10-02 22:20 (Higgsfield's own page for job b2aeba49: "Model  Nano Banana Pro"): the API's `model` field on a
    finished job is a BACKEND id - a Nano Banana Pro job reports `nano_banana_2`. The product is what was submitted: the
    record must carry a submission with model nano_banana_pro; `nano_banana_2` beside it is that same job. A record that
    never names nano_banana_pro (submitted as something else) is refused."""
    if not job_file or not os.path.exists(job_file): C.fail('--job <file>: the job record (the generate_image submission + the jobs_wait result, saved verbatim)')
    txt = open(job_file).read(); found = sorted({re.sub(r'[\- ]', '_', f.lower()) for f in re.findall(r'nano[_\- ]?banana[_\- ]?(?:pro|2_shots|2_lite|2|\d+(?:\.\d+)?)?', txt, re.I)})
    if not found: C.fail(f'--job {job_file}: no Nano Banana id in it - the cover must be submitted as nano_banana_pro (save the submission and the result as returned)')
    return found
def add(W, tid, img, model, saw, prompt, headline=None, job=None):
    """record an AI cover - every rule of round 2 is a GATE here (nothing is recorded when one fails)"""
    import numpy as np
    if not saw or len(saw) < 30: C.fail('--saw: what the image shows (likeness, text spelled, nothing banned) - the attestation it was looked at')
    if not headline: C.fail('--headline "<the exact headline>" - it must read back from the image')
    prompt = prompt_text(prompt)
    if not prompt or len(prompt) < 30: C.fail('--prompt cover/prompt.json (or the JSON text as sent) - it is checked against every prompt rule')
    R0 = rec(W, tid)
    if R0.get('headline') and R0['headline'].strip().upper() != headline.strip().upper(): C.fail(f'--headline {headline!r} is not the recorded decision {R0["headline"]!r} (cover.py headline to change it - never silently)')
    th = next((t for t in (C.load(f'{W}/themes.json') or {}).get('themes', []) if t['id'] == tid), None)
    pp = prompt_problems(prompt, headline, th)
    if pp: C.fail(f'{tid}: the prompt breaks the schema rules (references/nano_banana_prompt.md):\n  ' + '\n  '.join(pp))
    if TEETH_WORDS.search(prompt) and not NO_TEETH.search(prompt): C.fail(f'the prompt asks for teeth / a grin / laughing ("{TEETH_WORDS.search(prompt).group(0)}") - an AI cover never shows teeth (Colden 2026-10-02 hard rule); write "lips together, no teeth"')
    if 'no teeth' not in prompt.lower() and 'lips together' not in prompt.lower(): C.fail('the prompt must say "no teeth" / "lips together" (the hard rule for AI covers)')
    if '@image1' not in prompt.lower(): C.fail('the prompt must refer to the subject as "@Image1" (Colden 2026-10-02: that is how Higgsfield binds the reference)')
    if re.search(r'\b(3\s?:\s?4|4\s?:\s?3|three[- ]quarter|portrait format)\b', prompt, re.I): C.fail('the prompt must not describe the image as 3:4 (the canvas is the API parameter, 9:16; the centre 3:4 is a composition rule - say "middle three quarters of the height")')
    refs = re.findall(r'"reference_images"\s*:\s*\[([^\]]*)\]', open(job).read()) if job and os.path.exists(job) else []
    n_ref = max([len([x for x in r.split(',') if x.strip()]) for r in refs] or [0])
    if n_ref != 1: C.fail(f'the job record shows {n_ref} reference image(s) - attach exactly ONE (Colden 2026-10-02: two confuse the model)')
    jt = open(job).read() if job and os.path.exists(job) else ''
    if re.search(r'ai_ref_(chest|face|crop)', jt) or ('reference_file' in jt and 'ai_ref_full' not in jt): C.fail('the job record shows a CROPPED reference - the reference is ALWAYS the full-resolution frame ai_ref_full.png (Colden 2026-10-02 23:35: "always use the full resolution shot from resolve"); record "reference_file": "ai_ref_full.png" and resubmit with it')
    ran = job_model(job)
    if 'nano_banana_pro' not in ran or model != 'nano_banana_pro' or (set(ran) - {'nano_banana_pro', 'nano_banana_2'}): C.fail(f'the job record names {ran} (--model {model!r}) - the cover must be SUBMITTED as nano_banana_pro (Higgsfield reports that job back as nano_banana_2; anything else is another model): do not record it')
    d = cdir(W, tid); im = Image.open(img).convert('RGB'); w, h = im.size
    if abs(w / h - 9 / 16) > 0.02: C.fail(f'the cover is {w}x{h} - a short-form cover is GENERATED at 9:16 (Colden 2026-10-02: never 3:4), composed for the centre 3:4')
    s_ = max(TW / w, TH / h); im = im.resize((int(round(w * s_)), int(round(h * s_))), Image.LANCZOS); x0, y0 = (im.width - TW) // 2, (im.height - TH) // 2
    im = im.crop((x0, y0, x0 + TW, y0 + TH)); raw = f'{d}/2 ai_notext.png'; im.save(raw)
    o = json.loads(subprocess.run([f'{TOOLS}/ocr', raw], capture_output=True, text=True).stdout.splitlines()[0]) if os.path.exists(f'{TOOLS}/ocr') else {}
    stray = [l['text'] for l in o.get('lines', []) if len(re.sub(r'[^A-Za-z0-9]', '', l.get('text', ''))) >= 3]
    if stray: os.rename(raw, raw + '.rejected'); C.fail(f'{tid}: the model rendered text although none was asked for: {stray[:4]} - regenerate')
    out = f'{d}/2 ai.jpg'; hook_box(im, headline, raw, R0.get('headline_zone') or 'top').save(out, quality=92)
    probs = safe_zone(out, headline) + face_gates(raw)                             # the centre-3:4 rule + face size / skin colour, measured on the finished file
    m = json.loads(subprocess.run([f'{TOOLS}/mouth', out], capture_output=True, text=True).stdout.splitlines()[0])
    if m.get('open') is None: probs.append('no face for the teeth check')
    elif m['open'] > TEETH_MAX: probs.append(f'TEETH: mouth openness {m["open"]} > {TEETH_MAX} - an AI cover never shows teeth (Colden 2026-10-02 hard rule)')
    if probs: os.rename(out, out + '.rejected'); C.fail(f'{tid}: AI cover refused: {probs}')
    R = rec(W, tid); R['ai'] = {'file': out, 'source': img, 'model': model, 'job_ids': ran, 'job_file': job, 'saw': saw, 'prompt': json.loads(prompt), 'headline': headline, 'mouth_open': m['open'], 'at': C.now()}
    save(W, tid, R); print(f'{tid}: AI cover -> {out} (mouth {m["open"]}, face + headline inside the centre 3:4)')

FACE_MIN_W = 0.30; SKIN_BR_MAX = 0.80          # Vision face box over the frame width: round 6 s15 (2026-10-02) 20 % + skin b/r 1.07 = "looks nothing like me, why am I blue"; round 7 26 % = "looks nothing like me" too. Passing this gate does NOT mean a likeness - only Colden's look does
def face_gates(path):
    """the face on an AI cover is LARGE (identity needs pixels) and lit as skin (red over blue) - measured on the file"""
    import numpy as np
    j = json.loads(subprocess.run([f'{TOOLS}/face', path], capture_output=True, text=True).stdout.splitlines()[0]) if os.path.exists(f'{TOOLS}/face') else {}
    if j.get('w') is None: return ['no main face found']
    im = Image.open(path).convert('RGB'); w = im.width; out = []
    if j['w'] / w < FACE_MIN_W: out.append(f'the face is {100 * j["w"] / w:.0f} % of the frame width (min {100 * FACE_MIN_W:.0f} %) - too small to carry the likeness; the camera must come closer')
    x, y, fw, fh = j['x'], j['y'], j['w'], j['h']; patch = np.asarray(im.crop((x + fw // 4, y + fh // 3, x + 3 * fw // 4, y + 2 * fh // 3))).reshape(-1, 3).mean(0)
    if patch[0] <= 0 or patch[2] / patch[0] > SKIN_BR_MAX: out.append(f'the skin is not skin-coloured (rgb {patch.round(0).tolist()}, blue/red {patch[2] / max(patch[0], 1):.2f} > {SKIN_BR_MAX}) - a cool / blue key light on the face; light him warm or neutral')
    return out

HOOK_FONTS = [os.path.expanduser('~/Library/Fonts/Oswald-Bold.ttf'), '/Library/Fonts/Oswald-Bold.ttf', '/System/Library/Fonts/Supplemental/Arial Bold.ttf']
def hook_box(im, headline, raw, zone='top'):
    """the headline in the shorts' white hook box (black condensed capitals), inside the reserved band (y 24-38 %) and the
    centre 3:4, never over the face: measured on the finished file by safe_zone + OCR afterwards"""
    im = im.copy(); dr = ImageDraw.Draw(im); fp = next((f for f in HOOK_FONTS if os.path.exists(f)), None) or C.fail('no hook font on disk (Oswald-Bold.ttf)')
    lines = [l.strip() for l in headline.upper().split('\n') if l.strip()]; size = 190; pad_x, pad_y = 56, 28; maxw = 940
    while size > 80:
        fnt = ImageFont.truetype(fp, size); ws = [dr.textbbox((0, 0), l, font=fnt)[2] for l in lines]
        if max(ws) + 2 * pad_x <= maxw: break
        size -= 6
    lh = int(size * 1.08); bw = max(ws) + 2 * pad_x; bh = lh * len(lines) + 2 * pad_y
    j = json.loads(subprocess.run([f'{TOOLS}/face', raw], capture_output=True, text=True).stdout.splitlines()[0]) if os.path.exists(f'{TOOLS}/face') else {}
    a, b = ZONES[zone]; top = a + (b - a - bh) // 2                                                  # centred in the third the headline owns
    if j.get('y') is not None:
        fy0, fy1 = j['y'] - int(j['h'] * 0.35), j['y'] + j['h']                                        # the head (cap) above the face box, down to the chin
        if top < fy1 and top + bh > fy0:                                                               # the head reaches into the third: slide the box to the far edge of the third if it still fits clear of the head
            top = a if zone == 'top' else b - bh
            if top < fy1 and top + bh > fy0: raise SystemExit(f'GATE FAILED: the {zone} third holds the face (y {fy0}-{fy1}) - the model did not compose around the headline zone (face box {j}); regenerate')
    left = (TW - bw) // 2
    dr.rounded_rectangle([left, top, left + bw, top + bh], radius=18, fill='white')
    for k, l in enumerate(lines):
        tw = dr.textbbox((0, 0), l, font=fnt)[2]; dr.text((left + (bw - tw) // 2, top + pad_y + k * lh - int(size * 0.12)), l, font=fnt, fill='black')
    return im

def pair(W, tid):
    """both covers side by side with BIG numbered badges (the PodClips grid style) -> pair.jpg for the short's card"""
    R = rec(W, tid); a, b = R.get('resolve_cover'), (R.get('ai') or {}).get('file')
    if not (a and b and os.path.exists(a) and os.path.exists(b)): C.fail(f'{tid}: needs both covers (resolve: {a}, ai: {b})')
    sh = Image.new('RGB', (1100, 960), 'black'); dr = ImageDraw.Draw(sh)
    try: fnt = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Bold.ttf', 64); sm = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Bold.ttf', 30)
    except Exception: fnt = sm = ImageFont.load_default()
    for k, (f, lab) in enumerate(((a, 'from the short'), (b, 'AI'))):
        x = k * 560; sh.paste(Image.open(f).convert('RGB').resize((540, 960)), (x, 0))
        for yy in (SAFE[0] * 960 // TH, SAFE[1] * 960 // TH): dr.line([x, yy, x + 540, yy], fill='#FACC15', width=2)       # the IG / TikTok grid band (centre 3:4) - what the feed shows
        dr.text((x + 8, SAFE[0] * 960 // TH + 4), 'IG grid', font=sm, fill='#FACC15')
        dr.rectangle([x, 0, x + 96, 92], fill='#7C3AED'); dr.text((x + 30, 10), str(k + 1), font=fnt, fill='white')
        dr.rectangle([x + 96, 0, x + 96 + 22 + int(dr.textlength(lab, font=sm)), 52], fill='#7C3AED'); dr.text((x + 106, 10), lab, font=sm, fill='white')
    out = f'{cdir(W, tid)}/pair.jpg'; sh.save(out, quality=88)
    fc = Image.new('RGB', (560, 360), 'black')                                                   # the feed check (the guide: judge it at tile size): both covers as the 270x360 centre-3:4 tile the grid shows
    for k, f in enumerate((a, b)): fc.paste(Image.open(f).convert('RGB').crop((0, SAFE[0], TW, SAFE[1])).resize((270, 360)), (k * 290, 0))
    fcp = f'{cdir(W, tid)}/feed_check.jpg'; fc.save(fcp, quality=88); R['pair'] = out; R['feed_check'] = fcp; save(W, tid, R); print(out); print(f'{fcp}  <- LOOK at tile size: does the idea still read?')

if __name__ == '__main__':
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    for f in ('--emotion', '--model', '--saw', '--prompt', '--headline', '--job', '--zone'):
        if f in sys.argv and opt(f) in a: a.remove(opt(f))
    if len(a) < 3: C.fail(__doc__)
    cmd, W, tid = a[0], os.path.abspath(a[1]), a[2]
    if cmd == 'frames': frames(W, tid, opt('--emotion', 'smile'))
    elif cmd == 'still' and len(a) >= 6: still(W, tid, a[3], a[4], a[5])
    elif cmd == 'airef' and len(a) >= 5: airef(W, tid, a[3], a[4])
    elif cmd == 'resolve': resolve(W, tid)
    elif cmd == 'brief': brief(W, tid)
    elif cmd == 'headline' and len(a) >= 4: headline(W, tid, a[3], opt('--zone', 'top'))
    elif cmd == 'add' and len(a) >= 4: add(W, tid, a[3], opt('--model', '?'), opt('--saw'), opt('--prompt'), opt('--headline'), opt('--job'))
    elif cmd == 'pair': pair(W, tid)
    else: C.fail(__doc__)
