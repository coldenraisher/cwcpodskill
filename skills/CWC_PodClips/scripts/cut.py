"""cut.py <WORK> <theme id> [--channel cwc|tcl] [--no-audio]     ->  <WORK>/edit/<id>/cut.<channel>.json  (+ the report)
The EDIT PLAN of one approved theme, computed before Resolve is touched. Frames are frames of the locked PodCut
timeline (0 = its first frame); `rec` is the frame on the clip's own timeline.

  cold open (the hook) -> stinger (per channel) -> body ranges in play order -> the Colden ending (ruling 29)

What it decides, and the rule behind each (references/edit.json, references/stage2_rules_review.md):
  SECTIONS   each range opens a little before its first word and closes a little after its last, never inside a word of
             the person talking; never opens or closes on a listener's reaction shot.
  TRIMS      (ruling 24: "trim in clips to smooth as much as possible") pauses over 0.8 s where the PROGRAM is quiet
             (laughter and played video are not dead air) are cut to 0.5 s; plus the trims written in themes.json
             (`trims: [{"phrase": "P1266", "words": [0, 2], "why": "false start"}]`). A trim is KEPT only when its splice
             can be hidden and every shot around it stays >= 2 s; otherwise it is put back ("keep safe"). A WRITTEN trim
             also needs a real gap in the program audio at both ends (Whisper's word edges are not good enough to cut
             inside running speech): no gap, no trim.
             A swear is never inside a trim: it is beeped (ruling 24).
  HIDING     (ruling 23) every splice, in this order: a camera change (the PodCut's own, or the shot after / before the
             splice flipped between the speaker's close-up and the wide - a long shot only for its first 3 s), b-roll
             over it (edit stage), a 1.25x punch-in toggled on the close-up. NEVER a jump cut.
  PUNCH-INS  1.25x, pivot on the eyes (eyes.py fills the pan / tilt). A close-up longer than 10 s is also split at a
             word boundary and punched (the standing edit-clips re-engagement rule, at the new size).
  NAME TAG   guests only (ruling 20): once, on the guest's first close-up of the body that is >= 6 s.
  CENSOR     every swear among the kept words -> beep + duck window on the clip's clock.
GATES (exit 1): a cold open over 15 s (tighten it with a written trim scoped "in": "hook" - hidden there by a punch-in
first, so the cold open stays on the talker); a splice left unhidden; a shot under 2 s inside a section (1 s at its edges); a cut inside a word of
the person talking; a swear inside a trim; the hook's line missing from the body when its range contains it (ruling 30).
exit 2 (ask Colden): a guest who speaks in the body with no close-up long enough for the name tag."""
import math, os, re, sys, copy, json, bisect, subprocess
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
        self.guests = {p['name']: p for p in ep.get('people', []) if not p.get('host')}; self.audio = audio
        m = C.load(f'{ep["podcut_cache"]}/manifest.json') or {}; self.program = next((c['path'] for c in m.get('cameras', []) if c.get('role') == 'wide'), None)
    def F(self, t): return int(round(float(t) * self.fps))
    def n(self, key): return int(round(self.E[key] * self.fps))
    def words_in(self, a, b): return [w for w in self.words[bisect.bisect_left(self.w_a, a - 400):] if w['a'] < b and w['b'] > a] if b > a else []
    def floor(self, a, b):
        tot = {}
        for w in self.words_in(a, b): tot[w['who']] = tot.get(w['who'], 0) + (min(b, w['b']) - max(a, w['a']))
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
        """the frame between two words nearest `target` inside [lo, hi] (a shot is only ever split there), or None"""
        ws = self.words_in(lo - 30, hi + 30); best = None; end = None
        for w in ws:
            if end is not None and w['a'] >= end:
                f = (end + w['a']) // 2
                if lo <= f <= hi and (best is None or abs(f - target) < abs(best - target)): best = f
            end = w['b'] if end is None else max(end, w['b'])
        return best
    def quiet(self, a, b):
        """is the PROGRAM quiet between cut frames a and b? (speech level = the 3 s before a). None = could not measure."""
        if not self.audio or not self.program or not os.path.exists(self.program): return None
        try:
            import numpy as np
            t0 = self.cm.to_base(max(0, a - 90) / self.fps); dur = (b - a + 90) / self.fps + 0.2
            raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{t0:.3f}', '-t', f'{dur:.3f}', '-i', self.program, '-vn', '-ac', '1', '-ar', '8000', '-f', 's16le', '-'], capture_output=True, timeout=60).stdout
            x = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
            if len(x) < 8000: return None
            win = 400; r = np.sqrt(np.convolve(x * x, np.ones(win) / win, 'valid') + 1e-12); pre = int(min(a, 90) / self.fps * 8000)
            speech = float(np.median(r[:max(win, pre)])); gap = r[pre + 400:pre + int((b - a) / self.fps * 8000) - 400]
            if len(gap) < 200: return None
            return bool(20 * np.log10(float(np.percentile(gap, 95)) / max(speech, 1e-6)) < -12.0)
        except Exception: return None

def _dip(X, f):
    """a WRITTEN trim cuts inside running speech, where Whisper's word edges are off by up to 100 ms (the Ep 24 pilot v2
    cut a word in half: Colden 2026-10-01, "the edit was course and cut mid word"). So each end of such a trim must sit
    in a real gap of the program audio: within +-5 frames of the planned frame, the quietest 60 ms must be at least 18 dB
    under the speech around it. -> the frame of that gap, None when there is none (the trim is refused), 'unverified'
    when the audio cannot be read (only acceptable in a self-test)."""
    if not X.audio: return 'unverified'
    if not X.program or not os.path.exists(X.program): return None
    try:
        import numpy as np
        t0 = X.cm.to_base(max(0, f - 60) / X.fps); raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{t0:.3f}', '-t', '4.0', '-i', X.program, '-vn', '-ac', '1', '-ar', '8000', '-f', 's16le', '-'], capture_output=True, timeout=60).stdout
        x = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
        if len(x) < 16000: return None
        win = 480; r = np.sqrt(np.convolve(x * x, np.ones(win) / win, 'same') + 1e-12); speech = float(np.percentile(r, 75)); c = int(min(f, 60) / X.fps * 8000)
        lo, hi = max(win, c - int(5 / X.fps * 8000)), min(len(r) - win, c + int(5 / X.fps * 8000)); k = lo + int(np.argmin(r[lo:hi]))
        if 20 * np.log10(float(r[k]) / max(speech, 1e-6)) > -18.0: return None
        return f + int(round((k - c) / 8000 * X.fps))
    except Exception: return None

def onset(X, f):
    """the frame where the word near cut frame f really starts in the PROGRAM waveform: the first frame >= 12 dB over the
    quietest frame within onset_search frames before Whisper's start. None = no clear start (keep Whisper's)."""
    if not X.audio or not X.program or not os.path.exists(X.program): return None
    try:
        import numpy as np
        k = X.E['censor']['onset_search']; t0 = X.cm.to_base(max(0, f - k - 1) / X.fps); n = 2 * k + 3
        raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{t0:.3f}', '-t', f'{n / X.fps:.3f}', '-i', X.program, '-vn', '-ac', '1', '-ar', '48000', '-f', 'f32le', '-'], capture_output=True, timeout=60).stdout
        x = np.frombuffer(raw, np.float32); fr = int(48000 / X.fps)
        lv = [20 * np.log10(np.sqrt(np.mean(x[i:i + fr] ** 2)) + 1e-9) for i in range(0, len(x) - fr + 1, fr)]
        if len(lv) < n - 1: return None
        q = int(np.argmin(lv[:k + 2]))                    # the gap before the word (frames f-k-1 .. f)
        up = next((j for j in range(q + 1, len(lv)) if lv[j] >= lv[q] + 12.0), None)
        return None if up is None else f - k - 1 + up
    except Exception: return None

SWEAR = None
def is_swear(E, t):
    w = re.sub(r"[^a-z]", '', t.lower())                 # exact short words, or a stem anywhere in the word (fuckin, bullshit, horseshit, clusterfuck)
    return w not in E.get('swear_not', []) and (w in E['swears'] or any(x in w for x in E.get('swear_stems', [])))

def section(X, r, by):
    """a theme range -> [a, b) in PodCut frames, opened / closed between words"""
    fp, tp = by[r['from']], by[r['to']]; a0, b0 = X.F(fp['start']), X.F(tp['end']); lead, tail = X.n('lead'), X.n('tail')
    if r.get('start_word') is not None: a0 = X.F(fp['w'][r['start_word']][1])        # a range may open / close on a WORD inside its edge phrase
    if r.get('end_word') is not None: b0 = X.F(tp['w'][r['end_word']][2])            # (cross-talk at a range end: stop on the talker's last clean word)
    prev = max([w['b'] for w in X.words_in(a0 - lead - 60, a0) if w['b'] <= a0 + 1 and (w['pid'] != fp['id'] or r.get('start_word') is not None)] or [a0 - lead])
    nxt = min([w['a'] for w in X.words_in(b0, b0 + tail + 60) if w['a'] >= b0 - 1 and (w['pid'] != tp['id'] or r.get('end_word') is not None)] or [b0 + tail])
    return max(a0 - lead, (prev + a0) // 2 if prev > a0 - lead else a0 - lead), min(b0 + tail, (b0 + nxt) // 2 if nxt < b0 + tail else b0 + tail)

def merge(sh):
    out = []
    for s in sh:
        if out and out[-1]['b'] == s['a'] and out[-1]['cam'] == s['cam'] and out[-1]['punch'] == s['punch'] and not s.get('splice'): out[-1]['b'] = s['b']
        else: out.append(s)
    return out

def tidy(X, sh, frag):
    """a sliver of a PodCut shot left at the edge of a piece takes the camera of the shot it touches"""
    sh = merge(sh); changed = True
    while changed and len(sh) > 1:
        changed = False
        for i, s in enumerate(sh):
            if s['b'] - s['a'] >= frag: continue
            left = i > 0 and sh[i - 1]['b'] == s['a'] and not s.get('splice'); right = i + 1 < len(sh) and sh[i + 1]['a'] == s['b'] and not sh[i + 1].get('splice')
            if left or right:
                s['cam'] = sh[i - 1]['cam'] if left else sh[i + 1]['cam']; s['punch'] = sh[i - 1]['punch'] if left else sh[i + 1]['punch']; sh = merge(sh); changed = True; break
    return sh

def no_listener_edges(X, sh):
    """a section never opens or closes on a listener: the reaction shot at its edge becomes the talker's close-up"""
    for idx in (0, -1):
        s = sh[idx]
        if s['reason'] == 'reaction':
            who, n = X.floor(s['a'], s['b']); s['cam'] = who if who and n >= 2 else 'WIDE'; s['reason'] = 'speaker' if s['cam'] != 'WIDE' else 'wide'
    return merge(sh)

def hidden(A, B): return A['cam'] != B['cam'] or (A['punch'] != B['punch'] and A['cam'] != 'WIDE') or bool(B.get('broll'))

def problems(X, sh):
    out = []; ms, fr = X.n('min_shot'), X.n('edge_fragment')
    for i, s in enumerate(sh):
        first_or_last = i == 0 or i == len(sh) - 1 or s.get('section_edge') or (i + 1 < len(sh) and sh[i + 1].get('section_edge'))
        if s['b'] - s['a'] < (fr if first_or_last else ms): out.append(f'shot {C.clock(s["a"] / X.fps)} is {(s["b"] - s["a"]) / X.fps:.1f} s')
        if s.get('splice') and i > 0 and not hidden(sh[i - 1], s): out.append(f'splice at {C.clock(s["a"] / X.fps)} is not hidden')
        if s['punch'] and s['cam'] == 'WIDE': out.append('a punch-in on the wide')
    return out

def alt_cam(X, cam, a, b):
    if cam != 'WIDE': return 'WIDE'
    who, n = X.floor(a, b); return who if who and n >= 2 else None

def hide(X, sh, i, base=None, punch_first=False):
    """splice between sh[i-1] and sh[i]: try the rule-23 order, return (new list, method) for the first that leaves the
    whole list without problems, else (None, why)"""
    A, B = sh[i - 1], sh[i]; before = set(problems(X, sh)) if base is None else base; mine = f'splice at {C.clock(B["a"] / X.fps)} is not hidden'
    def good(trial):
        now = set(problems(X, trial)); return mine not in now and not (now - before)
    if hidden(A, B) and good(sh): return sh, 'camera (PodCut cut)'
    def punch():
        if B['cam'] == 'WIDE': return None
        t = copy.deepcopy(sh); t[i]['punch'] = not t[i - 1]['punch']
        return (t, 'punch-in 1.25x' if t[i]['punch'] else 'punch-out (back to 1.0x)') if good(t) else None
    if punch_first:                                    # the cold open stays on the talker: a punch-in, not a cut to the wide
        r = punch()
        if r: return r
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
            head = dict(S, b=cutp); rest = dict(S, a=cutp); rest.pop('splice', None) if side == 'after' else None
            flip = head if side == 'after' else rest
            alt = alt_cam(X, S['cam'], flip['a'], flip['b'])
            if not alt: continue
            flip['cam'] = alt; flip['punch'] = False
            if side == 'before': rest.pop('splice', None); head_keep = head
            k = i if side == 'after' else i - 1; t[k:k + 1] = [head, rest]
        t2 = []
        for s in t:                                    # merge across PodCut cuts only (never across a splice)
            if t2 and t2[-1]['b'] == s['a'] and t2[-1]['cam'] == s['cam'] and t2[-1]['punch'] == s['punch'] and not s.get('splice'): t2[-1]['b'] = s['b']
            else: t2.append(s)
        if good(t2): return t2, f'camera ({"wide" if alt == "WIDE" else alt + " close-up"} {side} the splice)'
    r = punch()
    if r: return r
    return None, 'no camera change, b-roll or punch can hide it'

def apply_trim(X, sh, t0, t1):
    """remove [t0, t1) from a shot list -> (list, index of the first shot after the splice) or (None, why)"""
    left = [dict(s, b=min(s['b'], t0)) for s in sh if s['a'] < t0]; right = [dict(s, a=max(s['a'], t1)) for s in sh if s['b'] > t1]
    if not left or not right: return None, 'at the edge of a section'
    if any(x.get('splice') and t0 < x['a'] <= t1 for x in sh): return None, 'runs into another splice'
    right[0] = dict(right[0], splice={'type': 'trim', 'removed': t1 - t0}); right[0].pop('section_edge', None)
    frag = X.n('edge_fragment')
    # slivers next to the splice join their neighbour on the far side
    if left[-1]['b'] - left[-1]['a'] < frag and len(left) > 1 and left[-2]['b'] == left[-1]['a'] and not left[-1].get('splice'): left[-2]['b'] = left[-1]['b']; left.pop()
    if right[0]['b'] - right[0]['a'] < frag and len(right) > 1 and right[1]['a'] == right[0]['b'] and not right[1].get('splice'):
        right[1] = dict(right[1], a=right[0]['a'], splice=right[0]['splice']); right.pop(0)
    return left + right, len(left)

def trims_for(X, th, a, b, by, kind='body', skipped=None):
    """candidate trims inside [a, b): written ones (themes.json) and quiet pauses. -> [(t0, t1, why, kind)]
    A written trim that does not fit (bad word indices) is reported in `skipped`, never dropped silently."""
    E = X.E; out = []; pad = X.n('word_pad')
    for tr in th.get('trims', []):
        if tr.get('in', 'both') not in ('both', kind): continue        # a trim can be for the cold open only: the body plays the line in full (ruling 30)
        if tr['phrase'] not in by:
            if skipped is not None: skipped.add(f'written trim in {tr["phrase"]}: no such phrase')
            continue
        p = by[tr['phrase']]; ws = [w for w in X.words if w['pid'] == p['id']]; i, j = tr['words']
        if not (0 <= i <= j < len(ws)):
            if skipped is not None: skipped.add(f'written trim in {p["id"]} words {i}-{j}: the phrase has {len(ws)} words')
            continue
        if ws[i]['a'] < a or ws[j]['b'] > b: continue                  # another section's trim (a trim no section took is reported in build())
        if skipped is not None: X.seen_trims.add((tr['phrase'], i, j, kind))
        prev = ws[i - 1]['b'] if i > 0 else max([w['b'] for w in X.words_in(ws[i]['a'] - 90, ws[i]['a']) if w['b'] <= ws[i]['a']] or [ws[i]['a'] - pad])
        nxt = ws[j + 1]['a'] if j + 1 < len(ws) else min([w['a'] for w in X.words_in(ws[j]['b'], ws[j]['b'] + 90) if w['a'] >= ws[j]['b']] or [ws[j]['b'] + pad])
        gone = [w for w in X.words_in(prev + pad, nxt - pad) if w['a'] < nxt - pad and w['b'] > prev + pad]          # EVERY speaker's words in the cut window
        if any(is_swear(E, w['t']) for w in gone): C.fail(f'{th["id"]}: the trim in {p["id"]} words {i}-{j} removes a swear ("{" ".join(w["t"] for w in gone)}") - ruling 24: beep it, never cut it')
        out.append((prev + pad, nxt - pad, tr.get('why', 'written trim') + f': "{" ".join(w["t"] for w in ws[i:j + 1])}"' + (f' (also cuts {", ".join(w["who"] + ": " + w["t"] for w in gone if w["pid"] != p["id"])})' if any(w['pid'] != p['id'] for w in gone) else ''), 'written'))
    ws = sorted(X.words_in(a, b), key=lambda w: w['a']); end = None; over = X.n('pause_over')
    for w in ws:
        if end is not None and w['a'] - end > over:
            t0, t1 = end + X.n('pause_keep_before'), w['a'] - X.n('pause_keep_after')
            if not any(s0 < t1 and s1 > t0 for s0, s1 in X.specials) and not any(o[0] < t1 and o[1] > t0 for o in out): out.append((t0, t1, f'pause of {(w["a"] - end) / X.fps:.1f} s', 'pause'))
        end = w['b'] if end is None else max(end, w['b'])
    for o in out:
        if o[3] == 'written' and not (o[1] - o[0] >= X.n('trim_min') and a < o[0] and o[1] < b) and skipped is not None: skipped.add(f'written trim {o[2]}: only {(o[1] - o[0]) / X.fps:.2f} s would be removed (minimum {X.E["trim_min"]} s) or it touches the section edge - not applied')
    return sorted([o for o in out if o[1] - o[0] >= X.n('trim_min') and a < o[0] and o[1] < b])

def plan_list(X, th, ranges, by, log, kind):
    """sections -> one shot list in play order with every join and every accepted trim hidden"""
    sh = []; bounds = []
    for k, r in enumerate(ranges):
        a, b = section(X, r, by)
        cont = bool(bounds) and 0 <= a - bounds[-1][1] < X.n('pause_over') or bool(bounds) and bounds[-1][0] < a <= bounds[-1][1] < b
        if cont: a = bounds[-1][1]                        # two ranges that touch in the show are one continuous piece: no splice
        bounds.append((a, b)); part = tidy(X, X.shots(a, b), X.n('edge_fragment') if kind == 'body' else int(1.5 * X.n('min_shot')))
        if not cont: part = no_listener_edges(X, part)
        for s in part: s['kind'] = kind; s['range'] = k
        if sh and not cont: part[0]['splice'] = {'type': 'join', 'removed': None}
        if not cont: part[0]['section_edge'] = True
        sh += part
    sh = merge(sh)
    while True:                                          # joins first: a join that cannot be hidden is a gate, not a choice
        i = next((n for n, x in enumerate(sh) if x.get('splice') and x['splice']['type'] == 'join' and 'hide' not in x['splice']), None)
        if i is None: break
        rng = sh[i]['range']; new, how = hide(X, sh, i)
        if new is None:
            sh[i]['splice']['hide'] = 'UNHIDDEN'
            log['problems'].append(f'the join into part {rng + 1} at {C.clock(sh[i]["a"] / X.fps)} cannot be hidden ({how}): move the range edge by a phrase (or start_word / end_word) so the two sides sit on different cameras or leave a shot long enough to split')
        else:
            sh = new; next(x for x in sh if x.get('splice') and x['splice']['type'] == 'join' and x['range'] == rng)['splice']['hide'] = how
    for k, r in enumerate(ranges):
        a, b = bounds[k]
        for t0, t1, why, tk in trims_for(X, th, a, b, by, kind, log.setdefault('skipped', set())):
            rec = {'at': C.clock(t0 / X.fps), 'seconds': round((t1 - t0) / X.fps, 2), 'why': why, 'kind': tk, 'section': kind, 'range': k}
            if tk == 'written':
                d0, d1 = _dip(X, t0), _dip(X, t1)
                if d0 is None or d1 is None:
                    rec.update(kept=False, reason='no clean gap in the audio at the cut - it would land inside a word (a trim inside running speech is refused, never forced)'); log['trims'].append(rec); continue
                if d0 != 'unverified':
                    t0, t1 = d0, d1; rec.update(audio_checked=True, at=C.clock(t0 / X.fps), seconds=round((t1 - t0) / X.fps, 2))      # the cut moved into the real gap
                    if t1 - t0 < X.n('trim_min'):
                        rec.update(kept=False, reason='after moving both cuts into the audio gaps, less than trim_min is left'); log['trims'].append(rec); continue
            if tk == 'pause':
                q = X.quiet(t0, t1)
                if q is False: rec.update(kept=False, reason='the program is not quiet there (laughter / a played clip is not dead air)'); log['trims'].append(rec); continue
                rec['audio_checked'] = q is True
            idx = [n for n, s in enumerate(sh) if s['a'] < b and s['b'] > a and s['range'] in (k, k - 1, k + 1)]
            if not idx: continue
            lo, hi = idx[0], idx[-1] + 1; sub, at = apply_trim(X, copy.deepcopy(sh[lo:hi]), t0, t1)
            if sub is None: rec.update(kept=False, reason=at); log['trims'].append(rec); continue
            for s in sub: s.setdefault('kind', kind); s.setdefault('range', k)
            trial = sh[:lo] + sub + sh[hi:]; new, how = hide(X, trial, lo + at, base=set(problems(X, sh)), punch_first=(kind == 'hook'))     # judged against the list BEFORE the trim: a trim may not leave a short shot behind
            if new is None: rec.update(kept=False, reason=how)
            else:
                sh = new; rec.update(kept=True, hide=how)
                for s in sh:
                    if s.get('splice') and s['splice']['type'] == 'trim' and 'hide' not in s['splice']: s['splice'].update(hide=how, audio_gap=bool(rec.get('audio_checked')) and tk == 'written')
            log['trims'].append(rec)
    return sh

def reengage(X, sh, log):
    over, side = X.n('reengage_over'), X.n('reengage_side'); i = 0; before = set(problems(X, sh))
    while i < len(sh):
        s = sh[i]
        if s['cam'] != 'WIDE' and s['b'] - s['a'] > over:
            L = s['b'] - s['a']; cutp = X.boundary(s['a'] + L // math.ceil(L / over), s['a'] + side, s['b'] - side)      # equal pieces <= `over`, punch alternating
            if cutp is not None:
                t = copy.deepcopy(sh); second = dict(t[i], a=cutp, punch=not t[i]['punch'], reengage=True); second.pop('splice', None); second.pop('section_edge', None); t[i]['b'] = cutp; t.insert(i + 1, second)
                if not (set(problems(X, t)) - before): sh = t; log['reengage'] += 1; i += 1; continue      # the second piece is looked at again: a 40 s close-up gets 3 changes, not 1
        i += 1
    return sh

def build(work, tid, channel=None, audio=True, write=True):
    W = T.Work(work); X = Ctx(W, audio); E = X.E; th = next((t for t in W.themes()['themes'] if t['id'] == tid), None)
    if not th: C.fail(f'no theme {tid}')
    ap = C.load(f'{W.work}/approved.json') or {}; ok = {a['id']: a for a in ap.get('approved', [])}
    if tid not in ok and not W.ep.get('trial'): C.ask(f'{tid} is not in approved.json - only a theme Colden approved is edited')
    if tid in ok and ok[tid].get('text_sha'):             # ... and only AS he approved it: trims / word edges / waivers are edit decisions, new ranges are not
        cur = C.sha_text(W.assemble(th))
        if cur not in (ok[tid]['text_sha'], ok[tid].get('current_text_sha')): C.ask(f'{tid}: the hook / ranges / payoff of this theme changed after Colden approved it. A changed story goes back to him: assemble.py, cold read, check.py, tg_themes.py resend "<WORK>" {tid} (his approval updates approved.json). Trims, start_word / end_word and waivers do not need this.')
    sp = W.specials_in(th); integral = [x for x in th.get('shares', []) if x.get('integral')]
    if (sp or integral) and len(str(th.get('share_plan', ''))) < 10:                      # ruling 15 + "played clips stay in": the layout for it is not built
        C.ask(f'{tid} has a screen share / played clip inside its ranges ({[(C.clock(x["start"]), str(x["overlap"]) + " s") for x in sp] or integral}). Ruling 15: an integral share must be SHOWN full screen (speaker in the lower third), and a played clip stays in - that layout is not built yet. Ask Colden how this clip should show it (and for the full-resolution file); record his answer as `share_plan` on the theme. Until then the clip is not built.')
    ck = C.load(f'{W.work}/checked.json') or {}; channel = channel or ((ck.get('themes', {}).get(tid) or {}).get('suggest') or {}).get('channel') or W.S['channels']['primary']
    by = W.by; log = {'trims': [], 'problems': [], 'reengage': 0}; X.seen_trims = set()
    hook = plan_list(X, th, [th['hook']], by, log, 'hook'); body = reengage(X, plan_list(X, th, th['body'], by, log, 'body'), log)
    for name, sh in (('cold open', hook), ('body', body)): log['problems'] += [f'{name}: {p}' for p in problems(X, sh)]
    hook_s = sum(s['b'] - s['a'] for s in hook) / X.fps
    if hook_s > E['cold_open_max'] and len(str(th.get('cold_open_waiver', ''))) < 10: log['problems'].append(f'the cold open runs {hook_s:.1f} s (limit {E["cold_open_max"]:.0f} s - Colden 2026-10-01: "could easily condense to 12-15s"): tighten it with a trim written for the hook ("in": "hook") - it is kept only where the audio has a real gap - or pick a shorter hook line; `cold_open_waiver` (his words) when he prefers the long one')
    # the clip's own clock
    st = E['stinger'][channel]; rec = 0; shots = []
    for s in hook: shots.append(dict(s, rec=rec)); rec += s['b'] - s['a']
    H = rec; body0 = H + X.F(st['anim_end_s']); rec = body0
    for s in body: shots.append(dict(s, rec=rec)); rec += s['b'] - s['a']
    Cf = rec; total = Cf + X.F(E['outro']['end_screen_s'])
    def to_rec(f, kind='body'):
        for s in shots:
            if s['kind'] == kind and s['a'] <= f < s['b']: return s['rec'] + f - s['a']
        return None
    # cuts inside a word of the person talking (gate) / of someone else (reported)
    inside = []; cross = 0
    for n, s in enumerate(shots):
        edges = []; gap = lambda x: bool((x.get('splice') or {}).get('audio_gap'))      # a written trim's cut the AUDIO check put in a real gap: Whisper's edges are wrong there, not the cut
        if n == 0 or s.get('splice') or s.get('section_edge') or shots[n - 1]['kind'] != s['kind']:
            if not gap(s): edges.append(s['a'])
        if n == len(shots) - 1 or shots[n + 1].get('splice') or shots[n + 1].get('section_edge') or shots[n + 1]['kind'] != s['kind']:
            if not (n + 1 < len(shots) and gap(shots[n + 1])): edges.append(s['b'])
        for f in edges:
            who, _ = X.floor(f - 60, f + 60)
            for w in X.words_in(f - 1, f + 1):
                if w['a'] + 2 < f < w['b'] - 2:
                    if w['who'] == who: inside.append(f'{C.clock(f / X.fps)} cuts "{w["t"]}" ({w["who"]})')
                    else: cross += 1
    real_inside = sorted(set(inside))
    # the hook stays in the body (ruling 30)
    hs = X.F(by[th['hook']['from']]['start']); he = X.F(by[th['hook']['to']]['end'])
    in_body = any(X.F(by[r['from']]['start']) <= hs and he <= X.F(by[r['to']]['end']) for r in th['body'])
    if in_body:
        missing = [w['t'] for w in X.words_in(hs, he) if w['pid'] in (th['hook']['from'], th['hook']['to']) and to_rec((w['a'] + w['b']) // 2) is None]
        if missing: log['problems'].append(f'ruling 30: the hook line is trimmed out of the body ({" ".join(missing)[:60]})')
    # name tag: guests only, first body close-up long enough
    tags = []; tg = E['tag']
    for g, info in X.guests.items():
        said = sum(1 for s in shots if s['kind'] == 'body' for w in X.words_in(s['a'], s['b']) if w['who'] == g)
        if said < 20: continue
        need = X.F(tg['min_shot']); cand = [s for s in shots if s['kind'] == 'body' and s['cam'] == g and s['b'] - s['a'] >= need and s['rec'] >= body0 + X.F(st['audio_end_s'] - st['anim_end_s'])]
        if not cand: log.setdefault('ask', []).append(f'{g} speaks in the body but has no close-up of {tg["min_shot"]:.0f} s for the name tag'); continue
        s = cand[0]; tags.append({'who': g, 'name': info.get('full_name') or g, 'handle': info.get('handle'), 'rec': s['rec'] + tg['clear_frames'], 'frames': X.F(tg['seconds']), 'fade_frames': tg['fade_frames'], 'punched': s['punch']})
    # censor
    censor = []; soft = []; pieces = {}
    for s in shots:                                       # a word may straddle a shot edge (PodCut cut to a listener mid-word): every piece of it counts
        for w in X.words_in(s['a'], s['b']):
            if w['b'] <= s['a'] or w['a'] >= s['b']: continue
            tok = re.sub(r"[^a-z]", '', w['t'].lower())
            r0, r1 = s['rec'] + max(w['a'], s['a']) - s['a'], s['rec'] + min(w['b'], s['b']) - s['a']
            if is_swear(E, w['t']): pieces.setdefault((w['a'], w['b'], w['who'], w['t'], s['kind']), []).append([r0, r1])
            elif tok in E['soft_swears_check'] and w['a'] >= s['a']: soft.append({'word': w['t'], 'who': w['who'], 'at': C.clock(r0 / X.fps)})
    for (wa, wb, who, t, kind), ps in sorted(pieces.items(), key=lambda kv: min(p[0] for p in kv[1])):
        ps.sort(); runs = [list(ps[0])]
        for p in ps[1:]:
            if p[0] - runs[-1][1] <= 1: runs[-1][1] = max(runs[-1][1], p[1])
            else: runs.append(list(p))                   # a trim splice inside the word: beep each heard piece
        CE = E['censor']; o = onset(X, wa); used = o is not None and abs(o - wa) <= CE['onset_search']; shift = (o - wa) if used else 0
        for r0, r1 in runs:                               # Colden 2026-10-02: 3 frames of the word through, beep + duck, end 3 frames before its end
            if r0 == runs[0][0]: r0, r1 = r0 + shift, r1 + shift          # the word's real start (waveform), its length from Whisper
            a_, b_ = r0 + CE['through_start'], r1 - CE['through_end']
            if b_ - a_ < CE['min_beep']: a_ = r0 + max(0, (r1 - r0 - CE['min_beep'] + 1) // 2); b_ = a_ + CE['min_beep']; short = True
            else: short = False
            censor.append({'word': t, 'who': who, 'rec': a_, 'frames': b_ - a_, 'section': kind, 'word_rec': [r0, r1], 'onset_from_audio': used, 'short_word': short})
    censor.sort(key=lambda c: c['rec']); merged = []
    for c in censor:                                      # two people swearing at once: ONE window (one beep, one duck), never two fighting
        if merged and c['section'] == merged[-1]['section'] and c['rec'] <= merged[-1]['rec'] + merged[-1]['frames']:
            m = merged[-1]; end = max(m['rec'] + m['frames'], c['rec'] + c['frames']); m['frames'] = end - m['rec']; m['word'] += ' + ' + c['word']; m['who'] += ' + ' + c['who']
        else: merged.append(c)
    censor = merged
    if real_inside: log['problems'] += [f'cut inside a word: {x}' for x in real_inside]
    log['problems'] += sorted(log.get('skipped') or [])
    for tr in th.get('trims', []):                         # a written trim that no section took (wrong phrase id for this clip) is never silent
        kinds = ('hook', 'body') if tr.get('in', 'both') == 'both' else (tr['in'],)
        if tr['phrase'] in by and not any((tr['phrase'], tr['words'][0], tr['words'][1], k) in X.seen_trims for k in kinds) and not any(tr['phrase'] in x for x in log['problems']):
            log['problems'].append(f'written trim in {tr["phrase"]} words {tr["words"]}: that phrase is not inside the {" / ".join(kinds)} of this clip - nothing was trimmed')
    for t in log['trims']:                                 # ... and one that was refused (no audio gap, cannot be hidden) is never silent either
        if t['kind'] == 'written' and not t.get('kept'): log['problems'].append(f'written trim "{t["why"]}" at {t["at"]} ({t["section"]}) was NOT made: {t.get("reason")} - take it out of themes.json, or choose words with a real pause on both sides (never try indexes just to get past this)')
    splices = [dict(s['splice'], at=C.clock(s['rec'] / X.fps), section=s['kind']) for s in shots if s.get('splice')]
    kept = [t for t in log['trims'] if t.get('kept')]; wide = sum(s['b'] - s['a'] for s in shots if s['cam'] == 'WIDE')
    out = {'theme': tid, 'title': th['title'], 'channel': channel, 'fps': X.fps, 'rules': E['version'], 'made_at': C.now(), 'themes_sha': C.sha_file(W.themes_path), 'plan_sha': W.ep['plan_sha'],
           'podcut': W.ep['cut'], 'project': W.ep['project'], 'frames': total, 'seconds': round(total / X.fps, 2),
           'anchors': {'hook_end': H, 'body_start': body0, 'C': Cf, 'end': total},
           'stinger': dict(st, rec=H, video_frames=X.F(st['anim_end_s']), audio_frames=X.F(st['audio_end_s'])),
           'outro': dict(E['outro'], C=Cf, music_rec=Cf - X.F(E['outro']['music_pre_s']), sfx_rec=Cf - X.F(E['outro']['sfx_pre_s']), end_screen_frames=X.F(E['outro']['end_screen_s'])),
           'shots': [{k: s[k] for k in ('kind', 'range', 'a', 'b', 'rec', 'cam', 'punch', 'reason') if k in s} | ({'splice': s['splice']} if s.get('splice') else {}) | ({'reengage': True} if s.get('reengage') else {}) for s in shots],
           'tags': tags, 'censor': censor, 'soft_swears_to_listen': soft, 'trims': log['trims'], 'splices': splices,
           'stats': {'shots': len(shots), 'avg_shot_s': round(sum(s['b'] - s['a'] for s in shots) / len(shots) / X.fps, 1), 'wide_pct': round(100 * wide / max(1, sum(s['b'] - s['a'] for s in shots))),
                     'trims_kept': len(kept), 'trimmed_s': round(sum(t['seconds'] for t in kept), 1), 'trims_put_back': len(log['trims']) - len(kept),
                     'pause_trims_without_audio_check': sum(1 for t in kept if t['kind'] == 'pause' and not t.get('audio_checked')),
                     'splices': len(splices), 'hidden_by': {}, 'punched_shots': sum(1 for s in shots if s['punch']), 'reengage_punches': log['reengage'], 'cuts_in_others_words': cross},
           'problems': log['problems'], 'ask': log.get('ask', [])}
    for sp in splices: out['stats']['hidden_by'][sp.get('hide', 'UNHIDDEN').split(' (')[0]] = out['stats']['hidden_by'].get(sp.get('hide', 'UNHIDDEN').split(' (')[0], 0) + 1
    if write:
        C.save(f'{W.work}/edit/{tid}/cut.{channel}.json', out)
    return out

def report(o):
    s = o['stats']; print(f'{o["theme"]} [{o["channel"]}] {o["title"]}\n  {C.mmss(o["seconds"])} = cold open {o["anchors"]["hook_end"] / o["fps"]:.1f} s + stinger + body {(o["anchors"]["C"] - o["anchors"]["body_start"]) / o["fps"]:.0f} s + ending {o["outro"]["end_screen_s"]:.1f} s')
    print(f'  {s["shots"]} shots, avg {s["avg_shot_s"]} s, wide {s["wide_pct"]} %; trims kept {s["trims_kept"]} ({s["trimmed_s"]} s), put back {s["trims_put_back"]}; splices {s["splices"]} hidden by {s["hidden_by"]}; punched shots {s["punched_shots"]} ({s["reengage_punches"]} re-engagement)')
    for t in o['tags']: print(f'  name tag: {t["name"]} {t["handle"] or ""} at {C.clock(t["rec"] / o["fps"])}')
    for c in o['censor']: print(f'  censor: "{c["word"]}" ({c["who"]}) at {C.clock(c["rec"] / o["fps"])}')
    for c in o['soft_swears_to_listen']: print(f'  listen (possible softened swear): "{c["word"]}" at {c["at"]}')
    if s['pause_trims_without_audio_check']: print(f'  NOT VERIFIED: {s["pause_trims_without_audio_check"]} pause trim(s) were accepted without the program-audio check (--no-audio or the NAS file is missing)')
    for p in o['problems']: print(f'  PROBLEM: {p}')
    for p in o['ask']: print(f'  ASK: {p}')

if __name__ == '__main__':
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    if len(a) < 2: C.fail(__doc__)
    ch = sys.argv[sys.argv.index('--channel') + 1] if '--channel' in sys.argv else None
    if ch in a: a.remove(ch)
    o = build(os.path.abspath(a[0]), a[1], ch, audio='--no-audio' not in sys.argv); report(o)
    sys.exit(1 if o['problems'] else 2 if o['ask'] else 0)
