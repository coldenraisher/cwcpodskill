"""thumb_prompt.py - the AI thumbnail brief as a PLAIN PROSE prompt (ruling 47, Colden 2026-10-03: "I would like to return
to the prose style prompt from before. /CWC_PodReels just did exhaustive tests and came up with a perfect prompt system.
copy their system into the 16:9 format. for the two models"). The JSON template (ruling 45) is retired: its 5,700-7,000
character prompts, mostly prohibitions, drifted the likeness ("nothing like me", SFace 0.14-0.23); the ~950-character
prose recipe kept it (0.85-0.91) - CWC_PodReels' tests, memory ai-cover-recipe-v2.
thumbs.py routes these commands here:

  thumbs.py airef <WORK> <id> <ch> [<n> --saw ".."]      the ONE reference: a clean full camera frame (eyes open to the lens,
        lips together, never the master, never a crop). Pick it for the EMOTION the thumbnail needs - the model copies
        the reference's expression more than the prompt's.
  thumbs.py wardrobe <WORK> <id> <ch> [--saw ".."]       what the person wears in THIS episode (looked at on the stills)
  thumbs.py prompt <WORK> <id> <ch> <ai-1|ai-2|C> --promise ".." --object ".." --scene ".." --expression ".."
        [--side right|left] [--noun man|woman|person]
        builds the prose prompt in a fixed order: format -> who (@Image1 only, keep the real face, the episode wardrobe)
        -> the SCENE (one concrete idea with the topic object, where, what is held, the light) -> the EXPRESSION + eyes
        into the lens -> framing (face large on one side) -> the exact HEADLINE in big bold white condensed capitals with
        a black outline on the other side, upper half -> bottom-right kept clear -> a short fixed tail.
  thumbs.py check-prompt <WORK> <id> <ch> <slot>      THE GATE, then prints the exact Higgsfield call
  thumbs.py add <WORK> <id> <ch> <image> <slot> --model <m> --gen-id <job> --reported-model <m> --saw ".." --reads ".."

MODELS (Colden 2026-10-03: "completely change our generations to: 1. GPT Image 2.5 sunburst 16:9, quality high,
        resolution 1k 2. Grok Imagine 2.0 quality medium, resolution 1k, 16:9"):
        ai-1 = gpt_image_2_5 {variant sunburst, quality high, resolution 1k, 16:9}; ai-2 = grok_image_2_0 {quality
        medium, resolution 1k, 16:9}; both ONE reference, role image_references. C = the model of A (ai-1's when A is not AI).
THE GATE: the prompt is the builder's text, unchanged; 600-1400 characters, no JSON; the person only as @Image1 (no
        name, no @handle); ONE reference = the confirmed clean full frame; the exact approved headline (ai-1 / ai-2 <= 3
        words, C 2-5); the topic object in the scene; the scene and expression written as what IS there - no "no / not /
        without" in them (naming a thing invites it - CWC_PodReels' finding); a smile = closed lips, no teeth (ruling 40);
        Rule 1 (promise about THIS video, no repeated concept)."""
import os, re, sys, json, glob, shutil, subprocess, hashlib
from PIL import Image, ImageDraw, ImageFont
import common as C

RULE1 = """RULE 1 (Colden 2026-10-02): THE THUMBNAIL IS THE HOOK. "The thumbnail and the title are the only thing that engages a
viewer to watch my show. the thumbnail needs to be visually diverse and explain what's to come in the video."
  1. STOP THE SCROLL - one bold idea, strong contrast, read in under a second at 320x180.
  2. SAY WHAT THE VIDEO IS ABOUT - the topic object is IN the picture; the click promise is what the video pays off.
  3. BE VISUALLY DIFFERENT - the two AI options are two different concepts (never one idea on two models), thumbnail C
     is a new idea for title C, and no clip of the episode repeats another clip's idea.
  Everything else (likeness, wardrobe, margins, text) only serves these three."""
PARAMS = {'gpt_image_2_5': {'model': 'gpt_image_2_5', 'variant': 'sunburst', 'quality': 'high', 'resolution': '1k', 'aspect_ratio': '16:9'},
          'grok_image_2_0': {'model': 'grok_image_2_0', 'quality': 'medium', 'resolution': '1k', 'aspect_ratio': '16:9'}}
MODEL = {'ai-1': 'gpt_image_2_5', 'ai-2': 'grok_image_2_0'}
ROLE = 'image_references'
PRON = {'man': ('his', 'He'), 'woman': ('her', 'She'), 'person': ('their', 'They')}
NEG = re.compile(r"\b(no|not|without|never|don'?t|avoid)\b", re.I)
def sha(s): return hashlib.sha1(s.encode() if isinstance(s, str) else s).hexdigest()

def frame_size(src):
    r = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of', 'csv=p=0', src], capture_output=True, text=True).stdout.strip().split(',')
    return [int(r[0]), int(r[1])] if len(r) == 2 and r[0].isdigit() else None
def full_frame_problem(meta):
    """@Image1 must be the uncropped episode frame at the camera's resolution"""
    f = (meta.get('files') or [None])[0]
    if not f or not os.path.exists(f): return '@Image1 file is missing'
    w, h = Image.open(f).size
    if os.path.basename(f) == 'ref_face.png' or abs(w / h - 16 / 9) > 0.02: return f'@Image1 is a crop ({w}x{h}) - attach the FULL frame from the episode (Colden: "USE THE FULL IMAGE FROM RESOLVE")'
    if (meta.get('mouth_open') or 1) > MOUTH_MAX: return f'@Image1 mouth {meta.get("mouth_open")} - not lips together (a mid-word frame); use a confirmed clean reference (thumbs.py airef)'
    if meta.get('full_frame') and [w, h] != meta['full_frame']: return f'@Image1 is {w}x{h}, the camera frame is {meta["full_frame"][0]}x{meta["full_frame"][1]} - attach the full-resolution frame'
    return None
MOUTH_MAX = 0.022                                   # lips together (CWC_PodReels' measured line): never a mouth caught on a word

def airef_candidates(W, who):
    """CLEAN STATIC reference frames of `who` in this episode: full camera frames (never the master - punch-ins distort),
    eyes open to the lens, lips together. Source 1: the AI references CWC_PodReels confirmed for this episode (read-only);
    source 2: this skill's episode scan of the camera file (thumbs.py frames --scope episode)."""
    ep = C.episode(W); out = []
    for f in sorted(glob.glob(f'{C.ROOT}/reels/{ep["show"]}/{ep["ep_key"]}/edit/s*/cover.json')):
        a = (C.load(f) or {}).get('ai_ref') or {}
        if a.get('who') == who and a.get('full') and os.path.exists(a['full']) and (a.get('mouth_open') or 1) <= MOUTH_MAX:
            out.append({'file': a['full'], 'mouth_open': a['mouth_open'], 'from': f'CWC_PodReels {os.path.basename(os.path.dirname(f))}: {a.get("saw", "")}'})
    rows = (C.load(f'{W}/package/_faces/{who}/rows.json') or {}).get('rows') or []
    import thumbs as T
    ok = [r for r in T.score(rows, 'camera') if r.get('open', 1) <= MOUTH_MAX] if rows else []
    for r in sorted(ok, key=lambda r: (r.get('open', 1), -r.get('quality', 0)))[:6]:
        out.append({'file': None, 't': r['t'], 'src': (C.load(f'{W}/package/_faces/{who}/rows.json') or {}).get('src'), 'mouth_open': r.get('open'), 'from': f'episode scan t={r["t"]:.1f}s'})
    return out

def airef(W, tid, ch, n=None, saw=None):
    """thumbs.py airef <WORK> <id> <ch> [<n> --saw "..."]: the AI reference (@Image1). Colden 2026-10-02: "We already used
    Apples Face API to find clean faces. not mid word. not distorted ... Find the best one and use that. Do not use
    distorted or mid word images. ever." """
    import thumbs as T
    R = T.rec(W, tid, ch); who = R.get('speaker')
    if not who: C.fail(f'{tid} {ch}: run thumbs.py frames first (who is the face of this upload)')
    if ch == 'cwc' and who != 'Colden': C.fail('@ColdenRaisher thumbnails feature Colden')
    cands = airef_candidates(W, who); d, _ = T.paths(W, tid, ch)
    if not cands: C.fail(f'no clean reference of {who} yet: thumbs.py frames "<WORK>" {tid} {ch} --scope episode (scans the camera file), then airef again')
    if n is None:
        tiles = []; f = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Bold.ttf', 26)
        for i, c in enumerate(cands, 1):
            if not c['file']:
                c['file'] = f'{d}/_airef_{i}.png'; subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{c["t"]:.3f}', '-i', c['src'], '-frames:v', '1', c['file']], check=True)
            im = Image.open(c['file']).convert('RGB'); w, h = im.size; t = im.crop((int(w * .25), 0, int(w * .75), int(h * .75))).resize((480, 405))
            dr = ImageDraw.Draw(t); dr.rectangle([0, 0, 480, 36], fill='black'); dr.text((6, 4), f'{i}  mouth {c["mouth_open"]:.4f}', font=f, fill='white'); tiles.append(t)
        g = Image.new('RGB', (480 * min(4, len(tiles)), 405 * ((len(tiles) + 3) // 4)), 'black')
        for i, t in enumerate(tiles): g.paste(t, ((i % 4) * 480, (i // 4) * 405))
        g.save(f'{d}/airef_sheet.jpg', quality=88); C.save(f'{d}/airef_candidates.json', cands)
        print(f'{tid} {ch}: {len(cands)} clean reference frame(s) of {who} (full camera frames, eyes to the lens, lips together)\n  LOOK: {d}/airef_sheet.jpg  then: thumbs.py airef "<WORK>" {tid} {ch} <n> --saw "<eyes, mouth, sharpness, likeness>"'); return
    cands = C.load(f'{d}/airef_candidates.json') or []
    if not 1 <= int(n) <= len(cands): C.fail('pick a number from airef_sheet.jpg (run airef without a number first)')
    if not saw or len(saw) < 20: C.fail('--saw: what you see - eyes open to the lens, lips together, sharp, a good likeness')
    c = cands[int(n) - 1]; full = f'{d}/ai_ref_full.png'; shutil.copyfile(c['file'], full)
    def mut(r): r['ai_ref'] = {'file': full, 'who': who, 'mouth_open': c['mouth_open'], 'from': c['from'], 'saw': saw, 'at': C.now()}
    C.update(T.paths(W, tid, ch)[1], mut, {}); print(f'{tid} {ch}: AI reference = #{n} ({c["from"][:60]}) -> {full}')

def wardrobe_path(W, who): d = f'{W}/package/_wardrobe'; os.makedirs(d, exist_ok=True); return f'{d}/{who}.json'

def wardrobe(W, tid, ch, saw=None):
    import thumbs as T
    R = T.rec(W, tid, ch); who = R.get('speaker'); sc = R.get('still_confirmed')
    if not who or not sc or not R.get('still') or not os.path.exists(R['still']): C.fail(f'{tid} {ch}: no confirmed still yet (thumbs.py frames -> still) - the wardrobe sheet starts from it')
    p = wardrobe_path(W, who); d = os.path.dirname(p); sheet = f'{d}/{who} sheet.jpg'; rec = C.load(p, {}) or {}
    if saw is None:
        m = C.load(f'{C.episode(W)["podcut_cache"]}/manifest.json'); cam = next((x for x in m['cameras'] if x.get('name') == who), None)
        if not cam: C.fail(f'no camera named {who} in the PodCut manifest')
        dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', cam['path']], capture_output=True, text=True).stdout.strip() or 0)
        tiles = [Image.open(R['still']).convert('RGB')]
        for k, f in enumerate((0.2, 0.5, 0.8)):
            out = f'{d}/_{who}_{k}.png'; subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{dur * f:.1f}', '-i', cam['path'], '-frames:v', '1', out], check=True); tiles.append(Image.open(out).convert('RGB')); os.remove(out)
        g = Image.new('RGB', (1920, 1080), 'black'); dr = ImageDraw.Draw(g)
        try: fnt = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Bold.ttf', 30)
        except Exception: fnt = ImageFont.load_default()
        for i, (im, lab) in enumerate(zip(tiles, ['the confirmed still (@Image1)', 'episode 20 %', 'episode 50 %', 'episode 80 %'])):
            im = im.resize((960, 540)); X, Y = (i % 2) * 960, (i // 2) * 540; g.paste(im, (X, Y)); dr.rectangle([X, Y, X + 520, Y + 42], fill='black'); dr.text((X + 8, Y + 5), f'{who}: {lab}', font=fnt, fill='white')
        g.save(sheet, quality=88); C.save(p, dict(rec, sheet=sheet, sheet_sha=C.sha_file(sheet), made_at=C.now()))
        print(f'{who}: LOOK at {sheet} - what does {who} wear in THIS episode (garments, colors, cap, glasses; logos to leave out)?\n  then: thumbs.py wardrobe "<WORK>" {tid} {ch} --saw "<exactly that>"'); return
    if len(saw) < 25: C.fail('--saw: describe the wardrobe exactly (garments, colors, cap / glasses; at least 25 characters)')
    if not rec.get('sheet') or not os.path.exists(rec['sheet']) or C.sha_file(rec['sheet']) != rec.get('sheet_sha'): C.fail(f'make and LOOK at the wardrobe sheet first: thumbs.py wardrobe "<WORK>" {tid} {ch}')
    C.save(p, dict(rec, text=saw.strip(), looked_at=C.now())); print(f'{who}: wardrobe recorded for this episode: {saw.strip()}')

def headline(cp, slot):
    if slot == 'C':
        h = (cp.get('ai_headline_C') or '').strip(); lim = (2, 5)
        if not h: C.fail('thumbnail C needs "ai_headline_C" in the copy: 2-5 words from title C (Colden: "3 is still the best. 2-5 could add variants which may work well on a feed")')
    elif slot == 'ai-2' and cp.get('ai_headline_2'): h = cp['ai_headline_2'].strip(); lim = (1, 3)      # a second concept may carry its own headline (Rule 1.3)
    else: h = (cp.get('ai_headline') or cp.get('hook_headline') or '').strip(); lim = (1, 3)
    return h, lim

def model_for(R, slot):
    if slot in MODEL: return MODEL[slot]
    k = (R.get('kinds') or [None] * 4)[R['pick']] if R.get('pick') is not None else None
    m = (R.get('ai') or {}).get(k, {}).get('model') if k in ('ai-1', 'ai-2') else None
    return m if m in PARAMS else 'gpt_image_2_5'

def build_text(noun, wardrobe_txt, scene, expression, side, head, obj):
    his, he = PRON[noun]; other = 'left' if side == 'right' else 'right'
    ward = re.sub(r'\s*\([^)]*\)', '', wardrobe_txt).strip().rstrip('.')
    mic = '' if re.search(r'\bmic', obj + ' ' + scene, re.I) else 'no microphone, '      # a prop mic named in the scene is not forbidden in the same breath
    return (f'Horizontal 16:9 YouTube thumbnail, photorealistic. The {noun} is the {noun} in @Image1 (the attached photo): keep {his} real face '
            f'exactly as it is, same features, same age, same hair and facial hair, and {his} {ward}. {scene.strip().rstrip(".")}. '
            f'{expression.strip().rstrip(".")}, eyes straight into the lens. {he} is large in the frame on the {side} third, head and shoulders, '
            f'{his} face big and clear. The headline sits on the {other} side in the upper half, never at the top edge, in big bold white condensed '
            f'capital letters with a thick black outline reading exactly "{head}" (only these words, no added punctuation). Keep the bottom-right corner free of the headline and {his} face. '
            f'No other text anywhere, no logos, {mic}no earbuds, no other people.')

def prompt(W, tid, ch, slot, products=(), promise=None, obj=None, scene=None, expression=None, side='right', noun='man'):
    # Colden 2026-10-02: "What am i clicking on? Why should I watch this video?" - the creative brief comes BEFORE the prompt
    if not promise or len(promise) < 25: C.fail('--promise "<the click promise: what question the viewer has and what the video answers>" (at least 25 characters)')
    if not obj or len(obj) < 3: C.fail('--object "<the topic object that must be IN the picture - what makes the topic readable at 320x180>"')
    if not scene or len(scene) < 60: C.fail('--scene "<one concrete idea: where the person is, what they hold or do with the topic object, the light>" (at least 60 characters)')
    if not expression or len(expression) < 15: C.fail('--expression "<what the face does, tied to the topic; a smile = lips closed, no teeth>"')
    if side not in ('left', 'right') or noun not in PRON: C.fail('--side left|right, --noun man|woman|person')
    if products: C.fail('ONE reference only (two confuse the model - CWC_PodReels): describe a product in the scene in words')
    import thumbs as T
    if slot not in ('ai-1', 'ai-2', 'C'): C.fail('slot: ai-1 | ai-2 | C')
    R = T.rec(W, tid, ch); who = R.get('speaker'); cp = C.load(f'{W}/package/{tid}/copy.{ch}.json') or {}
    ar = R.get('ai_ref') or {}
    if not ar.get('file') or not os.path.exists(ar['file']) or ar.get('who') != who: C.fail(f'{tid} {ch}: no confirmed AI reference - thumbs.py airef (a clean full camera frame: eyes open, lips together, never a master frame or a crop)')
    if ch == 'cwc' and who != 'Colden': C.fail('@ColdenRaisher thumbnails feature Colden')
    wr = C.load(wardrobe_path(W, who), {}) or {}
    if not wr.get('text'): C.fail(f'{who}\'s wardrobe for this episode is not recorded - thumbs.py wardrobe "<WORK>" {tid} {ch} (make the sheet, LOOK, then --saw)')
    if slot == 'C' and not cp.get('C'): C.fail('thumbnail C is made FROM title C - write "C" into the copy first')
    head, lim = headline(cp, slot); head = head.upper()
    text = build_text(noun, wr['text'], scene, expression, side, head, obj)
    import thumbs as T; d, _ = T.paths(W, tid, ch); f = f'{d}/ai_prompt.{slot}.txt'; open(f, 'w').write(text)
    m = C.load(f'{(C.load(f"{W}/episode.json") or {}).get("podcut_cache")}/manifest.json') or {}; cam = next((x for x in m.get('cameras', []) if x.get('name') == who), {}); src = cam.get('path')
    full_wh = frame_size(src) if src and os.path.exists(src) else None
    C.save(f'{d}/ai_prompt.{slot}.refs.json', {'files': [ar['file']], 'full_frame': full_wh, 'source': src, 'mouth_open': ar.get('mouth_open'), 'who': who, 'promise': promise, 'object': obj,
                                               'scene': scene, 'expression': expression, 'side': side, 'noun': noun, 'headline': head, 'limits': lim, 'wardrobe': wr['text'], 'model': model_for(R, slot), 'text_sha': sha(text)})
    B = C.load(f'{C.DATA}/packaging_brief.json') or {}
    print(RULE1 + '\n')
    print(f'{tid} {ch} {slot}: {f} ({len(text)} characters)\n  READ it once as the model will, then: thumbs.py check-prompt "<WORK>" {tid} {ch} {slot}')
    if B.get('ab_lessons'): print('  thumbnails that WON A/B tests on the channel:\n' + '\n'.join(f'    won: {x["winner_thumb"]}  |  lost: {x["loser_thumbs"]}' for x in B['ab_lessons'][-5:]))

def problems(text, meta, who_expected=None):
    """the prose gate on one prompt -> list of problems (empty = OK)"""
    p = []
    if sha(text) != meta.get('text_sha'): p.append('the prompt text was edited by hand - change --scene / --expression and run thumbs.py prompt again')
    if not 600 <= len(text) <= 1400: p.append(f'{len(text)} characters - the recipe that keeps the likeness is ~950 (600-1400)')
    if '{' in text or '}' in text: p.append('no JSON - plain prose only (ruling 47)')
    if '@Image1' not in text or len(meta.get('files') or []) != 1: p.append('ONE reference, called @Image1')
    for h in re.findall(r'@(?!Image1\b)[A-Za-z0-9_]+', text): p.append(f'"@{h}" is not the attached image - the person is only @Image1')
    if who_expected and re.search(r'\b' + re.escape(who_expected) + r'\b', text): p.append(f'names "{who_expected}" - the model does not know names; the person is @Image1')
    if who_expected and meta.get('who') and meta['who'] != who_expected: p.append(f'@Image1 was made from {meta["who"]}\'s frame, the upload\'s speaker is {who_expected}')
    if f'reading exactly "{meta["headline"]}"' not in text: p.append(f'the exact headline "{meta["headline"]}" is missing')
    nw = len(meta['headline'].split()); lo, hi = meta['limits']
    if not lo <= nw <= hi: p.append(f'the headline has {nw} words - {lo}-{hi} for this slot')
    ob = re.findall(r'[a-z]{4,}', str(meta.get('object', '')).lower())
    if ob and not any(w in str(meta.get('scene', '')).lower() for w in ob): p.append(f'the scene does not show the topic object "{meta.get("object")}" (Rule 1.2)')
    for k in ('scene', 'expression'):
        if NEG.search(str(meta.get(k, ''))) and not (k == 'expression' and re.search(r'no teeth', meta.get(k, ''), re.I) and not NEG.search(re.sub(r'no teeth', '', meta[k], flags=re.I))):
            p.append(f'--{k} says what is NOT there ("{NEG.search(meta[k]).group(0)}") - write only what IS there; naming a thing invites it')
    ex = str(meta.get('expression', ''))
    if re.search(r'smil|grin|smirk', ex, re.I) and not re.search(r'lips (closed|together|pressed)|closed[- ]lip|no teeth', ex, re.I): p.append('a smile must say lips closed / no teeth (ruling 40)')
    if re.search(r'(showing|visible|bared) teeth|teeth (showing|visible)', re.sub(r'no teeth( visible)?', '', ex, flags=re.I), re.I) and re.search(r'smil|grin|smirk', ex, re.I): p.append('a smile never shows teeth in an AI thumbnail (ruling 40)')
    if len(str(meta.get('promise', ''))) < 25: p.append('no click promise recorded (thumbs.py prompt --promise)')
    return p

def check(W, tid, ch, slot):
    import thumbs as T
    d, _ = T.paths(W, tid, ch); f = f'{d}/ai_prompt.{slot}.txt'; meta = C.load(f'{d}/ai_prompt.{slot}.refs.json')
    if not meta or not os.path.exists(f): C.fail(f'no prompt for {slot}: thumbs.py prompt "<WORK>" {tid} {ch} {slot}')
    text = open(f).read(); R = T.rec(W, tid, ch)
    probs = problems(text, meta, R.get('speaker')); fp = full_frame_problem(meta)
    if fp: probs.append(fp)
    probs += rule1(W, tid, ch, slot, meta)
    for x in probs: print('  PROBLEM:', x)
    if probs: C.fail(f'{len(probs)} problem(s) in {f}')
    m = meta['model']; params = dict(PARAMS[m], count=1)
    def mut(r): r.setdefault('prompts', {})[slot] = {'file': f, 'sha': sha(text), 'model': m, 'params': params, 'checked_at': C.now()}
    C.update(T.paths(W, tid, ch)[1], mut, {})
    print(f'PROMPT OK ({slot}). Generate in Higgsfield, exactly:\n  params {json.dumps(params)}\n  medias: ONE reference, role "{ROLE}": {meta["files"][0]}\n  prompt:\n{text}')
    print(f'  then LOOK at the image AND its 320x180 copy: thumbs.py add "<WORK>" {tid} {ch} <file> {slot} --model {m} --gen-id <job id> --reported-model <what jobs_wait reports> --saw ".." --reads ".."')

STOP = set('the and with that this from into over have what they their them your will been about would which there while'.split())
def words(t): return {w for w in re.findall(r"[a-z]{4,}", str(t).lower()) if w not in STOP}
def sim(a, b):
    a, b = words(a), words(b); return len(a & b) / max(1, len(a | b))
def rule1(W, tid, ch, slot, meta):
    """RULE 1, parts 2 and 3: the promise is about THIS video; the concept is not a repeat"""
    p = []; cp = C.load(f'{W}/package/{tid}/copy.{ch}.json') or {}; F = C.load(f'{W}/package/{tid}/facts.{ch}.json') or {}
    video = ' '.join([str(x) for x in (cp.get('titles') or [])] + [str(cp.get(k, '')) for k in ('A', 'B', 'C', 'summary')] + [str(F.get(k, '')) for k in ('title_placeholder', 'summary_placeholder', 'hook_quote', 'payoff_quote')])
    if not words(meta.get('promise', '')) & words(video): p.append('RULE 1.2: the click promise shares nothing with this video\'s titles / summary / hook - say what THIS video pays off')
    mine = (str(meta.get('object', '')).lower(), str(meta.get('scene', '')))
    for g in glob.glob(f'{W}/package/*/thumbs/*/ai_prompt.*.refs.json'):
        oslot = os.path.basename(g).split('.')[1]; otid = g.split('/package/')[1].split('/')[0]; och = os.path.basename(os.path.dirname(g))
        if (otid, och, oslot) == (tid, ch, slot) or (otid == tid and och != ch): continue           # the same clip on its other channel may share the idea
        o = C.load(g) or {}; of = g.replace('.refs.json', '.txt'); R2 = C.load(f'{W}/package/{otid}/thumbs.{och}.json') or {}
        if oslot not in (R2.get('prompts') or {}) or not os.path.exists(of): continue                 # only ideas that were actually checked
        same_obj = str(o.get('object', '')).lower() == mine[0]; s = sim(mine[1], o.get('scene', ''))
        if (same_obj and s >= 0.35) or s >= 0.5:
            where = f'{oslot} of this upload' if otid == tid else f'{otid} {och} {oslot}'
            p.append(f'RULE 1.3: this concept repeats {where} (same object "{o.get("object")}", {int(s * 100)} % the same scene) - make a visually different idea')
    return p

def gate_add(W, tid, ch, slot, model, gen_id, reported=None):
    """thumbs.py add calls this: the image must come from the checked prompt of this slot, with the slot's model + params"""
    import thumbs as T
    R = T.rec(W, tid, ch); pr = (R.get('prompts') or {}).get(slot)
    if not pr: C.fail(f'{slot}: no checked prompt - thumbs.py prompt / check-prompt first (ruling 47: the prose recipe)')
    if not os.path.exists(pr['file']) or sha(open(pr['file']).read()) != pr['sha']: C.fail(f'{slot}: the prompt changed after check-prompt - run check-prompt again')
    want = pr['model']
    if model != want: C.fail(f'{slot} must be generated with {want} (ai-1 = GPT Image 2.5 sunburst high 1k, ai-2 = Grok Imagine 2.0 medium 1k, C = the model of A) - got {model}')
    if not gen_id or len(gen_id) < 6: C.fail('--gen-id <the Higgsfield job / generation id>: the record of which generation this is')
    if not reported: C.fail('--reported-model <the model the finished job reports (jobs_wait)> - every add records both')
    if reported != model: print(f'  WARNING: requested {model}, the finished job reports {reported} - recorded; tell Colden if it is not the same model (job {gen_id})')
    return dict(pr, reported=reported)

if __name__ == '__main__':
    C.fail(__doc__)
