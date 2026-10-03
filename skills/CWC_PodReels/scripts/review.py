"""review.py render <WORK> <id>        preview render (720x1280) of the newest VERIFIED version, then `check`
   review.py check  <WORK> <id>        the checks on the existing preview
   review.py ack    <WORK> <id> "<what you saw>"   after LOOKING at the contact sheet (bound to its hash)
Before a preview goes to Telegram (gates, exit 1):
  - the render has exactly the plan's frame count, one video + one audio stream;
  - DECODE GATE (AMIRA reels' rule, Colden 2026-09-29 "never truncate a word, always finish sentences, nothing stray"):
    the render's own audio is re-transcribed (faster-whisper small.en); the short must open on the hook's first words,
    every section must open on its first word with no stray word at the splice, and the last word heard must be the
    payoff's last word - with picture after it (no dead stop);
  - loudness measured (the master's finish brings it to -14 LUFS / -1 dBTP) - a true peak over 0 is reported;
  - a contact sheet of every moment that can go wrong: the hook frame, every layout run, every camera, every b-roll,
    the name tag, the last second. LOOK at it (`ack`) - a check no script does;
  - FACE / GEOMETRY GATE (v1 of the pilot came out letterboxed and only a look caught it): one frame of every layout run,
    away from b-roll, through tools/facequality - a single shows ONE big face (>= 20 % of the frame height), centred
    across (20-80 %), eyes in the upper half; a stack shows a face inside EVERY panel.
Then: tg_review.py send."""
import os, re, sys, json, difflib, subprocess
import common as C
HERE = os.path.dirname(os.path.abspath(__file__))
def vpath(W, tid): return f'{W}/edit/{tid}/versions.json'
def newest(W, tid):
    vs = [v for v in C.load(vpath(W, tid), []) if not str(v.get('status', '')).startswith('superseded')]
    if not vs: C.fail(f'no built version of {tid} - build.py first')
    if vs[-1]['status'] not in ('draft', 'approved'): C.fail(f'{tid} v{vs[-1]["v"]} is "{vs[-1]["status"]}", not verified - fix and build again')
    return vs[-1]
def set_v(W, tid, vn, **f):
    vs = C.load(vpath(W, tid), []); row = next(x for x in vs if x['v'] == vn); row.update(f); C.save(vpath(W, tid), vs); return row
def measure(path):
    r = subprocess.run(['ffmpeg', '-nostats', '-i', path, '-vn', '-af', 'ebur128=peak=true', '-f', 'null', '-'], capture_output=True, text=True).stderr
    s = r[r.rfind('Summary'):]; i = re.search(r'I:\s+(-?[\d.]+) LUFS', s); p = re.search(r'Peak:\s+(-?[\d.]+) dBFS', s)
    return (float(i.group(1)) if i else None), (float(p.group(1)) if p else None)
NORM = lambda t: re.sub(C.COLDEN_RE, 'colden', re.sub(r'[^a-z0-9 ]', '', t.lower())).replace(' ', '')     # Whisper spells Colden 'Colton' (2026-09-28)
def same(a, b):
    a, b = NORM(a), NORM(b)
    return bool(a and b) and (a == b or a.startswith(b) or b.startswith(a) or difflib.SequenceMatcher(None, a, b).ratio() >= 0.75)
def sections(W, P):
    """the plan's pieces as the viewer hears them: (rec start, first word of the talker, last word before the next piece)"""
    import themes as T, cut as K
    WK = T.Work(W); X = K.Ctx(WK, audio=False); out = []
    for i, s in enumerate(P['shots']):
        if i and not s.get('splice'): continue
        nxt = next((x for x in P['shots'][i + 1:] if x.get('splice')), None); end_b = nxt['a'] if nxt else P['shots'][-1]['b']
        seg_shots = [x for x in P['shots'][i:] if x['rec'] < (nxt['rec'] if nxt else 10 ** 9)]
        qt = (P.get('quiet_tail') or {}).get('rec', 10 ** 9)               # words inside the muted tail are not heard
        ws = [w for x in seg_shots for w in X.words_in(x['a'], x['b']) if x['a'] <= (w['a'] + w['b']) // 2 < x['b'] and x['rec'] + (w['a'] + w['b']) // 2 - x['a'] < qt]       # by the word's middle: Whisper starts words early
        who, _ = X.floor(s['a'], seg_shots[-1]['b']); tw = [w for w in ws if w['who'] == who] or ws
        out.append({'rec': s['rec'] / P['fps'], 'first': tw[0]['t'], 'firsts': [w['t'] for w in tw[:3]], 'last': tw[-1]['t']})
    return out
def decode(W, P, path):
    from faster_whisper import WhisperModel
    m = WhisperModel('small.en', device='cpu', compute_type='int8'); segs, _ = m.transcribe(path, word_timestamps=True, language='en', vad_filter=False)
    ws = [(w.start, w.end, w.word.strip()) for s in segs for w in s.words]; secs = sections(W, P); fails = []; dur = P['frames'] / P['fps']
    for i, p in enumerate(secs):
        b = p['rec']; after = [w for w in ws if b - 0.4 <= w[0] <= b + 1.2]; j = next((k for k, w in enumerate(after) if same(w[2], p['first'])), None)
        if j is None:                                   # a quick short first word ('you know' at s05's open) Whisper drops on the render: the next expected words must be heard
            fs = p.get('firsts') or []
            for n in (1, 2):
                if len(fs) > n and all(len(NORM(x)) <= 4 for x in fs[:n]):
                    j = next((k for k, w in enumerate(after[:2]) if same(w[2], fs[n])), None)
                    if j is not None: break
        if j is None: fails.append(f'at {b:.2f} s: did not hear the opening word {p["first"]!r} (heard {[w[2] for w in after[:3]]})')
        elif i == 0 and j > 0 and any(w[0] < after[j][0] - 0.05 for w in after[:j]): fails.append(f'start: stray word(s) {[w[2] for w in after[:j]]} before the opening word {p["first"]!r} (the open is not on a real pause)')
        if i:
            prev = secs[i - 1]['last']; before = [w for w in ws if b - 1.5 <= w[0] and w[1] <= b + 0.05]
            k = max((q for q, w in enumerate(before) if same(w[2], prev)), default=None)
            t_close = before[k][1] if k is not None else b - 0.4; t_open = after[j][0] if j is not None else b + 0.05
            stray = [w[2] for w in ws if w[0] >= t_close - 0.01 and w[1] <= t_open + 0.01 and not same(w[2], prev) and not same(w[2], p['first'])]
            if stray: fails.append(f'splice at {b:.2f} s: stray word(s) {stray} between {prev!r} and {p["first"]!r}')
    last = secs[-1]['last']
    if not ws or not same(ws[-1][2], last): fails.append(f'end: the last word heard is {ws[-1][2] if ws else None!r}, expected {last!r}')
    elif ws[-1][1] > dur - 0.05: fails.append(f'end: the last word runs to the final frame ({ws[-1][1]:.2f} of {dur:.2f} s)')
    return {'ok': not fails, 'fails': fails, 'heard_start': ' '.join(w[2] for w in ws[:8]), 'heard_end': ' '.join(w[2] for w in ws[-8:]), 'sections': secs}
def geometry(P, f, W=None):
    """one frame per layout run (clear of b-roll) -> the faces the layout promises are where it promises them. A single's
    face must be >= 65 % of that person's OWN expected size (faces.json; Nick's camera is framed wider - 2026-10-02 s02),
    else >= 20 % of the frame (a letterbox shrinks it to about half or less)"""
    F = ((C.load(f'{W}/edit/faces.json') or {}).get('faces') or {}) if W else {}
    fps = P['fps']; d = os.path.splitext(f)[0] + ' geometry'; os.makedirs(d, exist_ok=True); out = []; probs = []
    cover = [(b['rec'] - 3, b['rec'] + b['frames'] + 3) for b in P['broll']]
    for i, r in enumerate(P['runs']):
        free = [x for x in range(r['a'] + 6, r['b'] - 6, 3) if not any(a <= x < b for a, b in cover)]
        if not free: continue
        x = free[len(free) // 2]; img = f'{d}/run{i:02d}.jpg'
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{x / fps:.3f}', '-i', f, '-frames:v', '1', '-q:v', '2', img], check=True)
        j = json.loads((subprocess.run([f'{C.SK}/tools/facequality', img], capture_output=True, text=True).stdout.splitlines() or ['{}'])[0] or '{}')
        W_, H_ = j.get('w', 1), j.get('h', 1); fs = j.get('faces') or []; row = {'run': r['key'], 'at': round(x / fps, 2), 'faces': len(fs)}
        if r['key'].startswith('single'):
            big = max(fs, key=lambda q: q['w'] * q['h'], default=None)
            if not big: probs.append(f'{r["key"]} at {x / fps:.1f} s: no face found')
            else:
                fh, cx, cy = big['h'] / H_, (big['x'] + big['w'] / 2) / W_, (big['y'] + big['h'] * 0.4) / H_; row.update(face_h=round(fh, 2), cx=round(cx, 2), eye_y=round(cy, 2))
                who = r['key'].split(':', 1)[1] if ':' in r['key'] else None; exp = F[who]['fh'] / F[who]['h'] if who in F else None
                if (exp and fh < 0.65 * exp) or (not exp and fh < 0.20): probs.append(f'{r["key"]} at {x / fps:.1f} s: the face is only {fh:.0%} of the frame height' + (f' (expected ~{exp:.0%})' if exp else '') + ' - letterboxed / wrong zoom?')
                if not 0.2 <= cx <= 0.8: probs.append(f'{r["key"]} at {x / fps:.1f} s: the face is off-centre ({cx:.0%} across)')
                if cy > 0.5: probs.append(f'{r["key"]} at {x / fps:.1f} s: the eyes sit at {cy:.0%} down the frame')
        else:
            n = len(r['visible']); ph = H_ / n
            for k, who in enumerate(r['visible']):
                if not any(k * ph <= q['y'] + q['h'] / 2 < (k + 1) * ph and q['h'] >= 0.12 * ph for q in fs): probs.append(f'{r["key"]} at {x / fps:.1f} s: no face in panel {k + 1} ({who})')
        out.append(row)
    return out, probs
def splice_sound(P, f):
    """Colden 2026-10-02 (s07 v2): "Cuts are often cutting off pieces of words". The RENDER's own audio on both sides of
    every splice: a splice where the frame before AND the frame after are both loud (> -30 dBFS) cuts through sound."""
    import numpy as np
    out = []; fps = P['fps']
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', f, '-vn', '-ac', '1', '-ar', '24000', '-f', 's16le', '-'], capture_output=True).stdout
    x = np.frombuffer(raw, np.int16).astype(float) / 32768; fr = 24000 / fps
    db = lambda k: float(20 * np.log10(np.sqrt(np.mean(x[int(k * fr):int((k + 1) * fr)] ** 2)) + 1e-9)) if 0 <= k and int((k + 1) * fr) <= len(x) else -99.0
    for s in P['shots']:
        if s.get('splice') and s['rec'] > 0:
            r = s['rec']; before, after = db(r - 1), db(r)
            if before > -30 and after > -30: out.append(f'splice at {r / fps:.2f} s: {before:.0f} dB before, {after:.0f} dB after - a word is clipped')
    return out
def check(W, tid):
    v = newest(W, tid); P = C.load(v['plan']); f = v.get('preview')
    if not f or not os.path.exists(f): C.fail('no preview file - review.py render first')
    pr = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-count_frames', '-show_entries', 'stream=codec_type,nb_read_frames,width,height', '-of', 'json', f], capture_output=True, text=True).stdout)
    vst = [s for s in pr['streams'] if s['codec_type'] == 'video']; ast = [s for s in pr['streams'] if s['codec_type'] == 'audio']; probs = []
    if len(vst) != 1 or len(ast) != 1: probs.append(f'streams: {len(vst)} video, {len(ast)} audio')
    if vst and int(vst[0].get('nb_read_frames') or 0) != P['frames']: probs.append(f'the render has {vst[0].get("nb_read_frames")} frames, the plan {P["frames"]}')
    I, TP = measure(f); dec = decode(W, P, f)
    if not dec['ok']: probs += [f'DECODE: {x}' for x in dec['fails']]
    geo, gp = geometry(P, f, W); probs += [f'GEOMETRY: {x}' for x in gp]
    cuts = splice_sound(P, f); probs += [f'CUT THROUGH SOUND: {x}' for x in cuts]
    fps = P['fps']; times = [0.4]
    for r in P['runs']: times.append((r['a'] + r['b']) / 2 / fps)
    for b in P['broll']: times.append((b['rec'] + b['frames'] // 2) / fps)
    for t in P['tags']: times.append((t['rec'] + 30) / fps)
    for s in P['shots']:
        if s.get('splice'): times += [max(0, s['rec'] / fps - 0.2), s['rec'] / fps + 0.25]
    times.append(P['frames'] / fps - 0.3); times = sorted(set(round(t, 2) for t in times))[:30]
    d = os.path.splitext(f)[0] + ' frames'; os.makedirs(d, exist_ok=True)
    for x in os.listdir(d): os.remove(f'{d}/{x}')
    for n, t in enumerate(times): subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{t}', '-i', f, '-frames:v', '1', '-vf', 'scale=270:-1', f'{d}/{n + 1:02d}.jpg'])
    cols = 6; rows = (len(times) + cols - 1) // cols; sheet = os.path.splitext(f)[0] + ' sheet.jpg'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-framerate', '1', '-start_number', '1', '-i', f'{d}/%02d.jpg', '-vf', f'tile={cols}x{rows}:padding=4', '-frames:v', '1', sheet])
    set_v(W, tid, v['v'], preview_check={'frames': int(vst[0].get('nb_read_frames') or 0) if vst else None, 'lufs': I, 'true_peak': TP, 'decode': dec, 'geometry': geo, 'sheet': sheet, 'sheet_times': times, 'problems': probs, 'at': C.now()})
    print(f'{v["timeline"]}: {P["frames"]} frames planned; {I} LUFS, true peak {TP} dBFS\n  heard start: {dec["heard_start"]}\n  heard end:   {dec["heard_end"]}\n  LOOK AT: {sheet}\n  frames at (s): {times}')
    if TP is not None and TP > 0: print(f'  LOUD PEAKS: true peak {TP} dBFS (the master finish limits to -1 dBTP)')
    for p in probs: print('  PROBLEM:', p)
    return 1 if probs else 0
if __name__ == '__main__':
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    if len(a) < 3: C.fail(__doc__)
    cmd, W, tid = a[0], os.path.abspath(a[1]), a[2]
    if cmd == 'render':
        v = newest(W, tid); ep = C.episode(W); out = f'{W}/edit/{tid}/preview'; cn = f'{tid} v{v["v"]} preview'
        r = subprocess.run([sys.executable, f'{HERE}/rs.py', '1200', f'{HERE}/r_render.py', f'PROJECT={json.dumps(ep["project"])}', f'NAME={json.dumps(v["timeline"])}', f'OUT={json.dumps(out)}', f'CN={json.dumps(cn)}', 'W=720', 'H=1280', 'LIMIT=1100'], capture_output=True, text=True).stdout.strip().splitlines()
        res = json.loads(r[-1]) if r else {'error': 'no answer'}
        if res.get('error') or not res.get('made'): C.fail(f'render: {res}')
        set_v(W, tid, v['v'], preview=res['made']); sys.exit(check(W, tid))
    elif cmd == 'check': sys.exit(check(W, tid))
    elif cmd == 'ack':
        v = newest(W, tid); pc = v.get('preview_check') or {}
        if not pc.get('sheet') or not os.path.exists(pc['sheet']): C.fail('no contact sheet - review.py check first')
        if len(a) < 4 or len(a[3]) < 30: C.fail('say what you saw on the sheet (hook, every layout, b-roll, tag, ending) - at least a sentence')
        set_v(W, tid, v['v'], looked={'sheet_sha': C.sha_file(pc['sheet']), 'saw': a[3], 'at': C.now()}); print('recorded')
    else: C.fail(__doc__)
