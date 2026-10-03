"""cut.py <WORK> <short id> [--no-audio]   ->  <WORK>/edit/<id>/cut.json  (+ the report)
The EDIT PLAN of one approved short, before Resolve is touched. Frames are frames of the locked PodCut timeline
(0 = its first frame); `rec` is the frame on the short's own timeline (0 = the first frame of the short).
Ported from CWC_PodClips cut.py (the same footage, the same gates) with the shorts rulings (references/edit.json):
  SECTIONS  each range opens a little before its first word and closes a little after its last, never inside a word of
            the person talking; never opens or closes on a listener's reaction shot; the LAST shot shows the talker
            (the payoff), and the short ends cold: <= 0.4 s of picture after the last word, through silence only.
  TRIMS     pauses over 0.8 s where the PROGRAM is quiet are cut to 0.5 s; written trims (themes.json `trims`) only where
            the audio has a real gap at both ends (Whisper's edges are not cut points - Colden 2026-10-01). A trim is kept
            only when its splice can be hidden and every shot stays >= 1 s; otherwise it is put back.
  HIDING    (Colden 2026-10-02, Q7) every splice: a LAYOUT change (the PodCut's own camera change, or the shot next to the
            splice flipped between the talker's single and the 3-stack), then b-roll over it (plan.py places one there or
            fails), then a 1.25x punch-in - ONLY on a camera file of 2160 px or more. NEVER a jump cut.
  CENSOR    every swear among the kept words -> beep + duck window (3 frames through at each end; short word = one 3-frame beep).
GATES (exit 1): a shot under 1 s (0.5 s at a section edge); a cut inside a word of the person talking; a swear inside a
trim; a written trim that does not fit. Splices no layout change or punch can hide are reported as `needs_broll`."""
import os, re, sys, copy, json, bisect, subprocess
import common as C, themes as T

def cfg(): return C.load(f'{C.SK}/references/edit.json')

class Ctx:
    def __init__(self, W, audio=True):
        self.W = W; ep = W.ep; self.E = cfg(); plan = C.load(f'{ep["snapshot"]}/plan.json'); self.fps = float(plan['fps']); self.cm = C.CutMap(plan)
        self.segs = [{'a': s['outFrame'], 'b': s['outFrame'] + s['frames'], 'cam': s['name'], 'reason': s['reason'].split('+')[0]} for s in sorted(plan['segments'], key=lambda s: s['outFrame'])]
        self.seg_a = [s['a'] for s in self.segs]; self.words = []
        for p in W.ph:
            for i, (t, a, b) in enumerate(p['w']): self.words.append({'who': p['who'], 't': t, 'a': self.F(a), 'b': max(self.F(a) + 1, self.F(b)), 'pid': p['id'], 'i': i})
        self.words.sort(key=lambda w: (w['a'], w['b'])); self.w_a = [w['a'] for w in self.words]
        self.specials = [(self.F(s['start']), self.F(s['end'])) for s in ep['specials']]
        self.big = {p['name'] for p in ep['people'] if (p.get('h') or 0) >= self.E['punch_min_source_height']}
        self.audio = audio; self.program = (ep.get('wide') or {}).get('path')
    def F(self, t): return int(round(float(t) * self.fps))
    def n(self, key): return int(round(self.E[key] * self.fps))
    def words_in(self, a, b): return [w for w in self.words[bisect.bisect_left(self.w_a, a - 400):] if w['a'] < b and w['b'] > a] if b > a else []
    def floor(self, a, b):
        tot = {}
        for w in self.words_in(a, b): tot[w['who']] = tot.get(w['who'], 0) + min(12, min(b, w['b']) - max(a, w['a']))     # a word counts <= 0.4 s: Whisper stretches words over silence (s14: Nick's 'yes' = 38 frames)
        if not tot: return None, 0
        who = max(tot, key=tot.get); return who, sum(1 for w in self.words_in(a, b) if w['who'] == who)
    def shots(self, a, b):
        out = []; i = max(0, bisect.bisect_right(self.seg_a, a) - 1)
        while i < len(self.segs) and self.segs[i]['a'] < b:
            s = self.segs[i]
            if s['b'] > a: out.append({'a': max(a, s['a']), 'b': min(b, s['b']), 'cam': s['cam'], 'reason': s['reason'], 'punch': False})
            i += 1
        return out
    def boundary(self, target, lo, hi):
        ws = self.words_in(lo - 30, hi + 30); best = None; end = None
        for w in ws:
            if end is not None and w['a'] >= end:
                f = (end + w['a']) // 2
                if lo <= f <= hi and (best is None or abs(f - target) < abs(best - target)): best = f
            end = w['b'] if end is None else max(end, w['b'])
        return best
    def pcm(self, f0, frames, rate=8000):
        import numpy as np
        t0 = self.cm.to_base(max(0, f0) / self.fps)
        raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{t0:.3f}', '-t', f'{frames / self.fps:.3f}', '-i', self.program, '-vn', '-ac', '1', '-ar', str(rate), '-f', 's16le', '-'], capture_output=True, timeout=60).stdout
        return np.frombuffer(raw, np.int16).astype('float32') / 32768
    def quiet(self, a, b):
        if not self.audio or not self.program or not os.path.exists(self.program): return None
        try:
            import numpy as np
            x = self.pcm(max(0, a - 90), b - a + 96)
            if len(x) < 8000: return None
            win = 400; r = np.sqrt(np.convolve(x * x, np.ones(win) / win, 'valid') + 1e-12); pre = int(min(a, 90) / self.fps * 8000)
            speech = float(np.median(r[:max(win, pre)])); gap = r[pre + 400:pre + int((b - a) / self.fps * 8000) - 400]
            if len(gap) < 200: return None
            return bool(20 * np.log10(float(np.percentile(gap, 95)) / max(speech, 1e-6)) < -12.0)
        except Exception: return None
    def silent_after(self, f, frames):
        """how many of the `frames` frames after cut frame f stay quiet (the end hold runs only through silence)"""
        if not self.audio or not self.program or not os.path.exists(self.program): return 0
        try:
            import numpy as np
            x = self.pcm(f - 30, frames + 30, rate=24000); fr = 24000 / self.fps; lv = [20 * np.log10(np.sqrt(np.mean(x[int(i * fr):int((i + 1) * fr)] ** 2)) + 1e-9) for i in range(int(len(x) / fr))]
            if len(lv) < 31: return 0
            speech = float(np.percentile(lv[:30], 80)); n = 0
            for v in lv[30:]:
                if v > speech - 18: break
                n += 1
            return n
        except Exception: return 0

def _dip(X, f):
    """a WRITTEN trim's cut must sit in a real gap of the program audio (CWC_PodClips cut.py: the quietest 60 ms within
    +-5 frames, 18 dB under the speech around it) -> the frame of that gap, None when there is none"""
    if not X.audio: return 'unverified'
    if not X.program or not os.path.exists(X.program): return None
    try:
        import numpy as np
        x = X.pcm(max(0, f - 60), 120)
        if len(x) < 16000: return None
        win = 480; r = np.sqrt(np.convolve(x * x, np.ones(win) / win, 'same') + 1e-12); speech = float(np.percentile(r, 75)); c = int(min(f, 60) / X.fps * 8000)
        lo, hi = max(win, c - int(5 / X.fps * 8000)), min(len(r) - win, c + int(5 / X.fps * 8000)); k = lo + int(np.argmin(r[lo:hi]))
        if 20 * np.log10(float(r[k]) / max(speech, 1e-6)) > -18.0: return None
        return f + int(round((k - c) / 8000 * X.fps))
    except Exception: return None

def onset(X, f):
    """the frame where the word near f really starts in the PROGRAM waveform (12 dB over the quietest frame before it)"""
    if not X.audio or not X.program or not os.path.exists(X.program): return None
    try:
        import numpy as np
        k = X.E['censor']['onset_search']; n = 2 * k + 3; x = X.pcm(f - k - 1, n, 48000); fr = int(48000 / X.fps)
        lv = [20 * np.log10(np.sqrt(np.mean(x[i:i + fr] ** 2)) + 1e-9) for i in range(0, len(x) - fr + 1, fr)]
        if len(lv) < n - 1: return None
        q = int(np.argmin(lv[:k + 2])); up = next((j for j in range(q + 1, len(lv)) if lv[j] >= lv[q] + 12.0), None)
        return None if up is None else f - k - 1 + up
    except Exception: return None

def is_swear(E, t):
    w = re.sub(r"[^a-z]", '', t.lower()); return w in E['swears'] or any(w.startswith(x) for x in E.get('swear_stems', []))

def section(X, r, by):
    fp, tp = by[r['from']], by[r['to']]; a0, b0 = X.F(fp['start']), X.F(tp['end']); lead, tail = X.n('lead'), X.n('tail')
    if r.get('start_word') is not None: a0 = X.F(fp['w'][r['start_word']][1])
    if r.get('end_word') is not None: b0 = X.F(tp['w'][r['end_word']][2])
    prev = max([w['b'] for w in X.words_in(a0 - lead - 60, a0) if w['b'] <= a0 + 1 and (w['pid'] != fp['id'] or r.get('start_word') is not None) and w['who'] == fp['who']] or [a0 - lead])
    nxt = min([w['a'] for w in X.words_in(b0, b0 + tail + 60) if w['a'] >= b0 - 1 and (w['pid'] != tp['id'] or r.get('end_word') is not None) and w['who'] == tp['who']] or [b0 + tail])
    return max(a0 - lead, (prev + a0) // 2 if prev > a0 - lead else a0 - lead), min(b0 + tail, (b0 + nxt) // 2 if nxt < b0 + tail else b0 + tail)

def levels(X, f0, n):
    """program audio level (dBFS) of each frame f0 .. f0+n-1"""
    import numpy as np
    x = X.pcm(f0, n, rate=24000); fr = 24000 / X.fps                     # FULL band: an 's' lives above 4 kHz (s07 v4: 'clips' lost its s at 8 kHz)
    return [float(20 * np.log10(np.sqrt(np.mean(x[int(i * fr):int((i + 1) * fr)] ** 2)) + 1e-9)) if len(x[int(i * fr):int((i + 1) * fr)]) else -99.0 for i in range(n)]
def snap(X, r, by, a, b):
    """Colden 2026-10-02 (s07 v2: "Cuts are often cutting off pieces of words there were 3-4 premature cuts"): Whisper's
    word edges are not cut points (2026-10-01). Each section edge moves to the QUIETEST frame of the program audio between
    its word and the neighbouring one: the start to the latest frame within 3 dB of the minimum before the first word's
    onset, the end to the first frame within 3 dB of the minimum after the last word. -> (a, b, notes)"""
    if not X.audio or not X.program or not os.path.exists(X.program): return a, b, []
    fp, tp = by[r['from']], by[r['to']]
    a0 = X.F(fp['w'][r['start_word']][1]) if r.get('start_word') is not None else X.F(fp['start'])
    b0 = X.F(tp['w'][r['end_word']][2]) if r.get('end_word') is not None else X.F(tp['end'])
    prev = max([w['b'] for w in X.words_in(a0 - 60, a0) if w['b'] <= a0 + 1 and not (w['pid'] == fp['id'] and w['a'] >= a0 - 1)] or [a0 - 15])
    nw = [w for w in X.words_in(b0, b0 + 60) if w['a'] >= b0 - 1 and not (w['pid'] == tp['id'] and w['b'] <= b0 + 1)]
    nxt = min([w['a'] for w in nw] or [b0 + 15]); nmid = min([(w['a'] + w['b']) // 2 for w in nw] or [b0 + 15])
    notes = []
    lo = max(prev - 1, a0 - 30); hi = a0 + 8                             # Whisper starts words early AND late (s05 'Again,' = 28 frames late): back to the previous word / 1 s, 8 frames past its start
    if hi > lo:
        lv = levels(X, lo, hi - lo + 1); im = min(range(len(lv)), key=lambda i: (lv[i], -i)); m = lv[im]
        on = next((i for i in range(im + 1, len(lv)) if lv[i] > m + 20), None)                 # the real onset of the first word: 20 dB over the quietest frame
        a = lo + (max(im, on - 2) if on is not None else max([i for i, v in enumerate(lv[:a0 + 2 - lo]) if v <= m + 3] or [im]))
        if m > -40: notes.append({'edge': 'start', 'frame': a, 'db': round(m, 1), 'why': 'no pause before the first word - the open sits in sound'})
    lo = b0 - 2; hi = min(max(nmid, b0 + 1), b0 + 12)                 # Whisper starts the next word early (s07 'clips'/'That's'), but never past its middle (s07 'found.'/'You')
    if hi > lo:
        lv = levels(X, lo, hi - lo + 1); m = min(lv); q = [i for i, v in enumerate(lv) if v <= m + 6]
        run = q[-1]
        while run - 1 in q: run -= 1                                     # the START of the LAST quiet run: the word (and its 's') is over, the next one not begun
        b = lo + run + 1
        if m > -40: notes.append({'edge': 'end', 'frame': b, 'db': round(m, 1), 'why': 'no pause after the last word - the end sits in sound'})
    X.next_word_after = nxt
    return a, max(b, a + 1), notes

def merge(sh):
    out = []
    for s in sh:
        if out and out[-1]['b'] == s['a'] and out[-1]['cam'] == s['cam'] and out[-1]['punch'] == s['punch'] and not s.get('splice'): out[-1]['b'] = s['b']
        else: out.append(s)
    return out

def tidy(X, sh, frag):
    sh = merge(sh); changed = True
    while changed and len(sh) > 1:
        changed = False
        for i, s in enumerate(sh):
            if s['b'] - s['a'] >= frag: continue
            left = i > 0 and sh[i - 1]['b'] == s['a'] and not s.get('splice'); right = i + 1 < len(sh) and sh[i + 1]['a'] == s['b'] and not sh[i + 1].get('splice')
            if left or right:
                s['cam'] = sh[i - 1]['cam'] if left else sh[i + 1]['cam']; s['punch'] = sh[i - 1]['punch'] if left else sh[i + 1]['punch']; sh = merge(sh); changed = True; break
    return sh

def no_listener_edges(X, sh, last=False, payoff_who=None):
    """a section never opens or closes on a listener; the short's very last shot shows the talker (the payoff) - the
    PAYOFF's speaker, not a word count (s14 2026-10-02: Whisper stretched Nick's 'yes' over 38 frames and the count gave
    him the last shot under Colden's 'Regenerate.')"""
    for idx in (0, -1):
        s = sh[idx]
        who, n = X.floor(s['a'], s['b'])
        if idx == -1 and last and payoff_who: who, n = payoff_who, max(n, 1)
        if s['reason'] == 'reaction' or (idx == -1 and last and s['cam'] not in ('WIDE', who) and who and n >= 1):
            s['cam'] = who if who and n >= 1 else 'WIDE'; s['reason'] = 'speaker' if s['cam'] != 'WIDE' else 'wide'
    return merge(sh)

def hidden(A, B): return A['cam'] != B['cam'] or (A['punch'] != B['punch'] and A['cam'] != 'WIDE') or bool(B.get('broll'))

def problems(X, sh):
    out = []; ms, fr = X.n('min_shot'), X.n('edge_fragment')
    for i, s in enumerate(sh):
        edge = i == 0 or i == len(sh) - 1 or s.get('section_edge') or (i + 1 < len(sh) and sh[i + 1].get('section_edge'))
        if s['b'] - s['a'] < (fr if edge else ms): out.append(f'shot {C.clock(s["a"] / X.fps)} is {(s["b"] - s["a"]) / X.fps:.1f} s')
        if s['punch'] and (s['cam'] == 'WIDE' or s['cam'] not in X.big): out.append(f'a punch-in on {s["cam"]} (only cameras of 2160 px or more are punched)')
    return out

def unhidden(sh): return [s for i, s in enumerate(sh) if s.get('splice') and i > 0 and not hidden(sh[i - 1], s)]

def alt_cam(X, cam, a, b):
    if cam != 'WIDE': return 'WIDE'
    who, n = X.floor(a, b); return who if who and n >= 2 else None

def hide(X, sh, i, base=None):
    """splice between sh[i-1] and sh[i]: a layout change first (the PodCut's own, or a bridge flipped single <-> stack),
    a punch-in only on a big camera -> (list, method), or (list unchanged, 'needs b-roll')"""
    A, B = sh[i - 1], sh[i]; before = set(problems(X, sh)) if base is None else base
    def good(trial): return not (set(problems(X, trial)) - before)
    if hidden(A, B) and good(sh): return sh, 'layout (PodCut camera change)'
    br, bmax, ms = X.n('bridge'), X.n('bridge_max'), X.n('min_shot')
    for side in ('after', 'before'):
        t = copy.deepcopy(sh); S = t[i] if side == 'after' else t[i - 1]; L = S['b'] - S['a']
        if L < ms: continue
        if L <= bmax:
            alt = alt_cam(X, S['cam'], S['a'], S['b'])
            if not alt: continue
            S['cam'] = alt; S['punch'] = False
        else:
            cutp = X.boundary(S['a'] + br if side == 'after' else S['b'] - br, S['a'] + ms, S['b'] - ms)
            if cutp is None: continue
            head = dict(S, b=cutp); rest = dict(S, a=cutp); flip = head if side == 'after' else rest
            if side == 'after': rest.pop('splice', None)
            else: rest.pop('splice', None); rest.pop('section_edge', None)
            alt = alt_cam(X, S['cam'], flip['a'], flip['b'])
            if not alt: continue
            flip['cam'] = alt; flip['punch'] = False
            k = i if side == 'after' else i - 1; t[k:k + 1] = [head, rest]
        t2 = []
        for s in t:
            if t2 and t2[-1]['b'] == s['a'] and t2[-1]['cam'] == s['cam'] and t2[-1]['punch'] == s['punch'] and not s.get('splice'): t2[-1]['b'] = s['b']
            else: t2.append(s)
        if good(t2) and not any(s.get('splice') and s['a'] == B['a'] and not hidden(t2[j - 1], s) for j, s in enumerate(t2) if j): return t2, f'layout ({"3-stack" if alt == "WIDE" else alt + " single"} {side} the splice)'
    if B['cam'] in X.big:
        t = copy.deepcopy(sh); t[i]['punch'] = not t[i - 1]['punch']
        if good(t): return t, 'punch-in 1.25x'
    return sh, 'needs b-roll'

def apply_trim(X, sh, t0, t1):
    left = [dict(s, b=min(s['b'], t0)) for s in sh if s['a'] < t0]; right = [dict(s, a=max(s['a'], t1)) for s in sh if s['b'] > t1]
    if not left or not right: return None, 'at the edge of a section'
    if any(x.get('splice') and t0 < x['a'] <= t1 for x in sh): return None, 'runs into another splice'
    right[0] = dict(right[0], splice={'type': 'trim', 'removed': t1 - t0}); right[0].pop('section_edge', None)
    frag = X.n('edge_fragment')
    if left[-1]['b'] - left[-1]['a'] < frag and len(left) > 1 and left[-2]['b'] == left[-1]['a'] and not left[-1].get('splice'): left[-2]['b'] = left[-1]['b']; left.pop()
    if right[0]['b'] - right[0]['a'] < frag and len(right) > 1 and right[1]['a'] == right[0]['b'] and not right[1].get('splice'):
        right[1] = dict(right[1], a=right[0]['a'], splice=right[0]['splice']); right.pop(0)
    return left + right, len(left)

def trims_for(X, th, a, b, by, skipped):
    E = X.E; out = []; pad = X.n('word_pad')
    for tr in th.get('trims', []):
        if tr['phrase'] not in by: skipped.add(f'written trim in {tr["phrase"]}: no such phrase'); continue
        p = by[tr['phrase']]; ws = [w for w in X.words if w['pid'] == p['id']]; i, j = tr['words']
        if not (0 <= i <= j < len(ws)): skipped.add(f'written trim in {p["id"]} words {i}-{j}: the phrase has {len(ws)} words'); continue
        if ws[i]['a'] < a or ws[j]['b'] > b: continue
        prev = ws[i - 1]['b'] if i > 0 else ws[i]['a'] - pad; nxt = ws[j + 1]['a'] if j + 1 < len(ws) else ws[j]['b'] + pad
        gone = [w for w in X.words_in(prev + pad, nxt - pad) if w['a'] < nxt - pad and w['b'] > prev + pad]
        if any(is_swear(E, w['t']) for w in gone): C.fail(f'{th["id"]}: the trim in {p["id"]} removes a swear - beep it, never cut it')
        out.append((prev + pad, nxt - pad, tr.get('why', 'written trim') + f': "{" ".join(w["t"] for w in ws[i:j + 1])}"', 'written'))
    ws = sorted(X.words_in(a, b), key=lambda w: w['a']); end = None; over = X.n('pause_over')
    for w in ws:
        if end is not None and w['a'] - end > over:
            t0, t1 = end + X.n('pause_keep_before'), w['a'] - X.n('pause_keep_after')
            if not any(s0 < t1 and s1 > t0 for s0, s1 in X.specials) and not any(o[0] < t1 and o[1] > t0 for o in out): out.append((t0, t1, f'pause of {(w["a"] - end) / X.fps:.1f} s', 'pause'))
        end = w['b'] if end is None else max(end, w['b'])
    return sorted([o for o in out if o[1] - o[0] >= X.n('trim_min') and a < o[0] and o[1] < b])

def build(work, tid, audio=True, write=True):
    W = T.Work(work); X = Ctx(W, audio); E = X.E; th = W.theme(tid); by = W.by; ep = W.ep
    ap = C.load(f'{W.work}/approved.json') or {}
    if tid not in [a['id'] for a in ap.get('approved', [])] and not ep.get('trial') and not os.environ.get('PODREELS_PILOT_PREVIEW'): C.ask(f'{tid} is not approved on Telegram - only an approved short is edited')
    log = {'trims': [], 'problems': [], 'skipped': set()}; sh = []; bounds = []
    for k, r in enumerate(th['ranges']):
        a, b = section(X, r, by); a, b, en = snap(X, r, by, a, b); log.setdefault('edges', []).extend(dict(e, range=k) for e in en)
        if k == len(th['ranges']) - 1:                     # end cold on the payoff: a short hold through silence only
            b0 = b; hold = min(X.n('end_hold'), X.silent_after(b, X.n('end_hold')))
            nxt = min([w['a'] for w in X.words_in(b, b + 60) if w['a'] >= b] + [getattr(X, 'next_word_after', 10 ** 9)] or [b + hold + 1]); b = max(b0, min(b + hold, nxt - 1))
            qt = int(E.get('quiet_tail_frames', 0))
            if qt and b - b0 < qt:                          # the next word starts inside the hold: hold the picture, mute A1 from here
                log['quiet_tail'] = {'a': b, 'b': b0 + qt}; b = b0 + qt
        cont = bool(bounds) and 0 <= a - bounds[-1][1] < X.n('pause_over')
        if cont: a = bounds[-1][1]
        bounds.append((a, b)); part = tidy(X, X.shots(a, b), X.n('edge_fragment'))
        pw = by[r['to']]['who'] if k == len(th['ranges']) - 1 else None
        if not cont: part = no_listener_edges(X, part, last=(k == len(th['ranges']) - 1), payoff_who=pw)
        elif k == len(th['ranges']) - 1: part = no_listener_edges(X, part, last=True, payoff_who=pw)
        for s in part: s['range'] = k
        if sh and not cont: part[0]['splice'] = {'type': 'join', 'removed': None}
        if not cont: part[0]['section_edge'] = True
        sh += part
    sh = merge(sh)
    while True:
        i = next((n for n, x in enumerate(sh) if x.get('splice') and x['splice']['type'] == 'join' and 'hide' not in x['splice']), None)
        if i is None: break
        rng = sh[i]['range']; new, how = hide(X, sh, i)
        sh = new; s = next(x for x in sh if x.get('splice') and x['splice']['type'] == 'join' and x['range'] == rng and 'hide' not in x['splice']); s['splice']['hide'] = how
    for k, r in enumerate(th['ranges']):
        a, b = bounds[k]
        for t0, t1, why, tk in trims_for(X, th, a, b, by, log['skipped']):
            rec = {'at': C.clock(t0 / X.fps), 'seconds': round((t1 - t0) / X.fps, 2), 'why': why, 'kind': tk, 'range': k}
            if tk == 'written':
                d0, d1 = _dip(X, t0), _dip(X, t1)
                if d0 is None or d1 is None: rec.update(kept=False, reason='no clean gap in the audio at the cut'); log['trims'].append(rec); continue
                if d0 != 'unverified': t0, t1 = d0, d1; rec['audio_checked'] = True
            if tk == 'pause':
                q = X.quiet(t0, t1)
                if q is False: rec.update(kept=False, reason='the program is not quiet there'); log['trims'].append(rec); continue
                rec['audio_checked'] = q is True
            idx = [n for n, s in enumerate(sh) if s['a'] < b and s['b'] > a and s['range'] == k]
            if not idx: continue
            lo, hi = idx[0], idx[-1] + 1; sub, at = apply_trim(X, copy.deepcopy(sh[lo:hi]), t0, t1)
            if sub is None: rec.update(kept=False, reason=at); log['trims'].append(rec); continue
            for s in sub: s.setdefault('range', k)
            trial = sh[:lo] + sub + sh[hi:]; new, how = hide(X, trial, lo + at, base=set(problems(X, sh)))
            if how == 'needs b-roll': rec.update(kept=False, reason='only b-roll could hide it - a pause stays (b-roll is placed for the story, not to rescue a pause)')
            else:
                sh = new; rec.update(kept=True, hide=how)
                for s in sh:
                    if s.get('splice') and s['splice']['type'] == 'trim' and 'hide' not in s['splice']: s['splice'].update(hide=how, audio_gap=bool(rec.get('audio_checked')) and tk == 'written')
            log['trims'].append(rec)
    log['problems'] += problems(X, sh)
    rec = 0; shots = []
    for s in sh: shots.append(dict(s, rec=rec)); rec += s['b'] - s['a']
    total = rec
    inside = []
    for n, s in enumerate(shots):
        edges = []
        if n == 0 or s.get('splice') or s.get('section_edge'):
            if not (s.get('splice') or {}).get('audio_gap'): edges.append(s['a'])
        if n == len(shots) - 1 or shots[n + 1].get('splice') or shots[n + 1].get('section_edge'):
            if not (n + 1 < len(shots) and (shots[n + 1].get('splice') or {}).get('audio_gap')): edges.append(s['b'])
        if n == len(shots) - 1 and log.get('quiet_tail') and s['b'] in edges: edges.remove(s['b'])     # the last edge sits in the MUTED tail (A1 -60 dB): no word is heard cut
        for f in edges:
            who, _ = X.floor(f - 60, f + 60)
            for w in X.words_in(f - 1, f + 1):
                if w['a'] + 2 < f < w['b'] - 2 and w['who'] == who and not (X.audio and X.program and max(levels(X, f - 1, 2)) <= -38):   # Whisper stretches words over silence (s09 'because' = 67 frames): a cut in real silence cuts nothing
                    inside.append(f'{C.clock(f / X.fps)} cuts "{w["t"]}" ({w["who"]})')
    log['problems'] += [f'cut inside a word: {x}' for x in sorted(set(inside))] + sorted(log['skipped'])
    censor = []; pieces = {}
    for s in shots:
        for w in X.words_in(s['a'], s['b']):
            if w['b'] <= s['a'] or w['a'] >= s['b'] or not is_swear(E, w['t']): continue
            pieces.setdefault((w['a'], w['b'], w['who'], w['t']), []).append([s['rec'] + max(w['a'], s['a']) - s['a'], s['rec'] + min(w['b'], s['b']) - s['a']])
    CE = E['censor']
    for (wa, wb, who, t), ps in sorted(pieces.items(), key=lambda kv: min(p[0] for p in kv[1])):
        ps.sort(); r0, r1 = ps[0][0], ps[-1][1]; o = onset(X, wa); shift = (o - wa) if o is not None and abs(o - wa) <= CE['onset_search'] else 0
        r0, r1 = r0 + shift, r1 + shift; a_, b_ = r0 + CE['through_start'], r1 - CE['through_end']; short = b_ - a_ < CE['min_beep']
        if short: a_ = r0 + max(0, (r1 - r0 - CE['min_beep'] + 1) // 2); b_ = a_ + CE['min_beep']
        censor.append({'word': t, 'who': who, 'rec': a_, 'frames': b_ - a_, 'word_rec': [r0, r1], 'onset_from_audio': o is not None, 'short_word': short})
    splices = [dict(s['splice'], at=C.clock(s['rec'] / X.fps), rec=s['rec']) for s in shots if s.get('splice')]
    qt = None
    if log.get('quiet_tail'):                              # rec frames of the muted picture hold at the very end
        q = log['quiet_tail']; s_ = next((s for s in shots if s['a'] <= q['a'] < s['b']), shots[-1]); r = s_['rec'] + min(q['a'], s_['b']) - s_['a']
        qt = {'rec': r, 'frames': total - r, 'why': 'the next word starts inside the end hold'}
    out = {'short': tid, 'title': th['title'], 'fps': X.fps, 'rules': E['version'], 'made_at': C.now(), 'themes_sha': C.sha_file(W.themes_path), 'plan_sha': ep['plan_sha'],
           'podcut': ep['cut'], 'frames': total, 'seconds': round(total / X.fps, 2),
           'shots': [{k: s[k] for k in ('range', 'a', 'b', 'rec', 'cam', 'punch', 'reason') if k in s} | ({'splice': s['splice']} if s.get('splice') else {}) for s in shots],
           'needs_broll': [{'rec': s['rec'], 'at': C.clock(s['rec'] / X.fps)} for s in shots if s.get('splice') and s['splice'].get('hide') == 'needs b-roll'],
           'censor': censor, 'quiet_tail': qt, 'tight_edges': log.get('edges', []), 'trims': log['trims'], 'splices': splices,
           'stats': {'shots': len(shots), 'avg_shot_s': round(total / len(shots) / X.fps, 1), 'stack_pct': round(100 * sum(s['b'] - s['a'] for s in shots if s['cam'] == 'WIDE') / max(1, total)),
                     'trims_kept': sum(1 for t in log['trims'] if t.get('kept')), 'trimmed_s': round(sum(t['seconds'] for t in log['trims'] if t.get('kept')), 1), 'splices': len(splices)},
           'problems': log['problems']}
    if write: C.save(f'{W.work}/edit/{tid}/cut.json', out)
    return out

def report(o):
    s = o['stats']; print(f'{o["short"]} {o["title"]}: {o["seconds"]:.1f} s, {s["shots"]} shots (avg {s["avg_shot_s"]} s, 3-stack {s["stack_pct"]} %), trims kept {s["trims_kept"]} ({s["trimmed_s"]} s), splices {s["splices"]}')
    for sp in o['splices']: print(f'  splice {sp["type"]} at {sp["at"]}: {sp.get("hide")}')
    for c in o['censor']: print(f'  censor "{c["word"]}" ({c["who"]}) at {C.clock(c["rec"] / o["fps"])}')
    for e in o.get('tight_edges', []): print(f'  TIGHT EDGE (range {e["range"]}, {e["edge"]}): {e["why"]} ({e["db"]} dB) - the decode gate will judge it')
    for p in o['problems']: print(f'  PROBLEM: {p}')

if __name__ == '__main__':
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    if len(a) < 2: C.fail(__doc__)
    o = build(os.path.abspath(a[0]), a[1], audio='--no-audio' not in sys.argv); report(o); sys.exit(1 if o['problems'] else 0)
