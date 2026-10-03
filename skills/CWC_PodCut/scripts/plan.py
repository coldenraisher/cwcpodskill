"""CWC plan - the camera cut and the trims for one episode, any number of speakers. Every rule ends in an assert; a
failed assert = no plan (build.py refuses a plan without this file's RULES stamp).
usage: plan.py <CACHE> [--out plan.json] [--set key=value ...]      (cadence defaults: references/cadence.json)

How it decides (one pass, frame-exact, no patch-up passes): candidate trims (ums, uhs, dead air) are taken OUT of the
timeline; on what is left, every frame of every camera gets a score from the rules below, and a dynamic program picks
the sequence of shots with the best total - each shot between --min-shot and --max-shot, each cut costing a little so
the pace stays calm unless something earns a cut. A trim only survives when a cut to a DIFFERENT camera lands exactly on
it; a trim the best plan could not hide is put back (the um stays - never a jump cut).

Rules (Colden 2026-10-01 unless dated otherwise; AMIRA rules carried over where he said so):
 1 start / end from points.py: live greeting -> live sign-off; nothing outside survives.
 2 the person with the floor gets the close-up; a close-up needs REAL words (a "mm-hmm" / "yeah" never earns one).
 3 never hold a close-up on someone who is not talking while another person has the floor - except a reaction (5).
 4 two or more talking, or a quick back-and-forth too fast for 2 s shots: the wide. The wide starts 0.25 s before the
   words that caused it (the lead is built into every speaker's floor).
 5 reactions (reactions.py, expression-scored, automatic): a 2-4 s cutaway to a listener who is visibly reacting, from
   ONE person who keeps talking (never over a new talker's first words), at most one per `reaction_spacing` s, best
   first. Never to someone out of frame, turned away, coughing, sneezing or walking off (those never reach the plan),
   never while that listener is off air.
 6 shots: >= 2 s (shots under 4 s cost extra, so they stay the exception), <= 20 s per shot ("still allow the longer
   limit when speakers are really going"): a monologue gets relief (a reaction if there is one, else the wide) only
   near that limit. A cut is cheap at a sentence start or in a breath and dear inside a word.
 7 trims: an um / uh by the person talking (nobody else saying words), dead air >= 1 s (everyone silent AND the program
   quiet - laughter and played videos are not dead air), kept >= 10 frames clear of the last word (an um touching the
   word before it stays: "keep it safe"), and a CLEAN word repeat ("I I", "the the" with a breath at both ends -
   "If you can cleanly kill the repetitions, yes. If not, keep safe."). Hidden by a camera change or a reaction, or
   not made.
 8 special program layout (screen share, played video, graphic - layout.py): the program holds the picture and nothing
   is trimmed inside it (a trim would be a jump in the share). The only cutaway is an approved reaction of 2 s or less,
   and only once the share has been up 5 s - 8 s when it shows a page of text (Colden 2026-10-01).
 9 nobody is shown before they are on the program (layout.py off-air ranges).
"""
RULES = '2026-10-01d'
import os, sys, json, re, argparse, collections
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

ap = argparse.ArgumentParser(); ap.add_argument('cache'); ap.add_argument('--out', default=None); ap.add_argument('--set', action='append', default=[]); A = ap.parse_args()
cache = A.cache; m = C.manifest(cache); F = m['fps']
cad = json.load(open(f'{C.SK}/references/cadence.json')); cad.update(C.show(m['show']).get('cadence') or {})
for kv in A.set: k, v = kv.split('=', 1); cad[k] = json.loads(v)
cad['tail'] = cad['tail_frames'] / F          # "10 frames clear of the last word" at any frame rate
out_path = A.out or f'{cache}/plan.json'
# ---- gates before anything is planned ----
if C.frozen(m) and not A.out: C.die(f"this episode is LOCKED ({m['locked']['timeline']}): its plan is not re-made. A trial plan goes to --out <file>; a new cut needs Colden's word (unlock.py --by \"<his words>\").")
if m.get('problems'): C.die(f"intake is not clean: {m['problems']}")
if m.get('sync_problems') or any('sync' not in c for c in C.speakers(m)): C.die(f"sync is not clean: {m.get('sync_problems') or 'a camera has no measured offset'}")
if not A.out and os.path.exists(out_path): os.replace(out_path, f'{cache}/plan.prev.json')      # a run that dies below leaves NO plan.json for build.py to pick up
P = json.load(open(f'{cache}/points.json')); W = json.load(open(f'{cache}/words.json')); VAD = json.load(open(f'{cache}/vad.json'))['speakers']
if not P.get('confident'): C.die(f"points.json is not confident ({P.get('notes')}) - Colden rules on the start / end first")
LAY = json.load(open(f'{cache}/layout.json')); RX = json.load(open(f'{cache}/reactions.json'))
if not os.path.exists(f'{cache}/present.npz'): C.die('present.npz is missing (reactions.py writes it) - without it nobody could be kept off screen for being out of frame')
spk = [c['id'] for c in C.speakers(m)]; names = {c['id']: c['name'] for c in m['cameras']}; cams = ['wide'] + spk; NC = len(cams)
f0 = int(np.ceil(P['start'] * F - 1e-6)); f1 = int(np.floor(P['end'] * F + 1e-6)); NB = f1 - f0      # base frames [f0, f1)
def fr(t): return int(round(t * F)) - f0
def mask(iv, pad0=0.0, pad1=0.0):
    x = np.zeros(NB, bool)
    for a, b in iv:
        i, j = max(0, fr(a - pad0)), min(NB, fr(b + pad1))
        if j > i: x[i:j] = True
    return x

# ---- who has the floor (rule 2) ----
PURE = {'mm', 'hmm', 'mhm', 'mm-hmm', 'uh-huh', 'um', 'uh', 'uhm', 'ah', 'er', 'huh'}
BACK = PURE | {'yeah', 'right', 'okay', 'ok', 'yes', 'sure', 'wow', 'yep', 'oh', 'great', 'fantastic', 'absolutely', 'exactly', 'totally', 'nice', 'cool', 'true', 'no', 'well', 'so', 'and', 'but'}
def runs_of(sid, gap=0.8):
    """[start, end, n real (non-back-channel) words, seconds of them] - runs of this speaker's words (fillers excluded)"""
    out = []
    for w in sorted(W.get(sid, []), key=lambda w: w['start']):
        t = C.norm_word(w['text'])
        if not t or t in PURE: continue
        real = t not in BACK
        if out and w['start'] - out[-1][1] < gap: out[-1][1] = max(out[-1][1], w['end']); out[-1][2] += real; out[-1][3] += (w['end'] - w['start']) if real else 0
        else: out.append([w['start'], w['end'], int(real), (w['end'] - w['start']) if real else 0.0])
    return out
RUNS = {s: runs_of(s) for s in spk}
FLOOR = {s: [r for r in RUNS[s] if r[2] >= cad['floor_words'] or r[3] >= cad['floor_sec']] for s in spk}
Fm = {s: mask([(r[0], r[1]) for r in FLOOR[s]], cad['lead'], 0.15) for s in spk}
anyword = {s: mask([(w['start'], w['end']) for w in W.get(s, []) if C.norm_word(w['text'])], 0.05, 0.05) for s in spk}
ntalk = sum(Fm[s].astype(int) for s in spk)
def spoken(sid, a, b): return sum(max(0.0, min(b, w['end']) - max(a, w['start'])) for w in W.get(sid, []) if w['end'] > a and w['start'] < b)
# rule 3: frames where a close-up of k would be a hold on a non-talker
HOLD = {}
for k in spk:
    iv = [(r[0] - 0.1, r[1]) for j in spk if j != k for r in FLOOR[j] if r[1] - r[0] >= 1.0 and r[2] >= 2 and spoken(k, r[0], r[1]) < 0.3 * (r[1] - r[0])]
    HOLD[k] = mask(iv)
# ---- layout (rules 8, 9), presentable faces, reactions (rule 5) ----
special = mask(LAY['special'], 0.5, 0.5)
offair = {s: mask(LAY['offair'].get(s, [])) for s in spk}
pz = np.load(f'{cache}/present.npz'); idx = np.clip(np.round((np.arange(NB) + f0) / F * 2).astype(int) - int(round(pz['t0'] * 2)), 0, len(pz['t']) - 1)
present = {s: pz[s][idx] for s in spk}
# a camera has no picture before it started / after it stopped (Colden's own camera file starts and ends on its own)
camrow = {c['id']: c for c in C.speakers(m)}
nocover = {s: ~mask([(max(0.0, camrow[s]['off']) + 0.1, camrow[s]['off'] + camrow[s]['duration'] / camrow[s].get('rate', 1.0) - 0.3)]) for s in spk}
# the program picture is only usable while the talk layout is on it: before `on_air` it is the intro, from `off_air` the
# outro graphic; when the switch is a dissolve (no exact cut found) half a second of guard is kept
wide_block = np.zeros(NB, bool)
if 'on_air' in P:
    i_ = fr(P['on_air'] + (0.0 if P.get('on_air_exact') else 0.5)); j_ = fr(P['off_air'] - (0.0 if P.get('off_air_exact') else 0.5))
    wide_block[:max(0, i_)] = True; wide_block[max(0, j_):] = True
def steady_floor(r):
    """a reaction is a cutaway from ONE person who keeps talking: somebody else holds the floor for >= 70 % of the window
    and was already talking half a second before it. A window in which a new person starts (the guest's first answer,
    Ep 24 1:05) would hide the very person the audience needs to see."""
    i, j = max(0, fr(r['start'])), min(NB, fr(r['end']))
    if j - i < 2: return False
    for o in spk:
        if o != r['camera'] and Fm[o][i:j].mean() >= 0.7 and Fm[o][max(0, i - int(0.5 * F))]: return True
    return False
# ---- reactions over a screen share (Colden 2026-10-01: "if the screen share is longer than 5s and cutaway is 2s or
# less. that is the rule. if high density text is on the screen share, do not cut away unless longer time frame +/- 8sec")
# A cutaway from a special layout: the share has been on the program for >= 5 s (>= 8 s when it carried a page of text
# in the seconds before), and the cutaway is 2 s - never longer. Read this way: the viewer gets time with the share
# first, more time when there is text to read, and is only ever taken away from it briefly.
SPEC = [(a, b) for a, b in LAY['special']]; DENSE = LAY.get('dense_text', [])
def share_of(t0, t1): return next(((a, b) for a, b in SPEC if t0 < b + 0.5 and t1 > a - 0.5), None)
def share_lead(t): return cad['share_lead_text'] if any(x < t and y > t - cad['share_lead_text'] for x, y in DENSE) else cad['share_lead']
def share_fit(r):
    """None = not over a share (untouched); False = not allowed; else the reaction cut down to the 2 s that may be used"""
    sp_ = share_of(r['start'], r['end'])
    if not sp_: return None
    if sp_[1] - sp_[0] <= cad['share_min'] or r['start'] < sp_[0] + share_lead(r['start']) or r['start'] + cad['share_cutaway'] > sp_[1] + 0.5: return False
    return dict(r, end=round(r['start'] + cad['share_cutaway'], 2), over_share=True)
n_share_no = 0; _rx = []
for r in RX.get('picked', []) + RX.get('others', []):
    f_ = share_fit(r)
    if f_ is False: n_share_no += 1
    else: _rx.append(f_ or r)
offered = [r for r in _rx if r['start'] >= P['start'] + cad['min_shot'] and r['end'] <= P['end'] - cad['min_shot'] and not (offair[r['camera']] | nocover[r['camera']])[max(0, fr(r['start'])):fr(r['end'])].any()]
react = []; n_unsteady = 0
for r in sorted(offered, key=lambda r: -r.get('score', 0)):      # best first, one per reaction_spacing seconds
    if not steady_floor(r): n_unsteady += 1; continue
    if all(r['start'] >= q['end'] + cad['reaction_spacing'] or r['end'] <= q['start'] - cad['reaction_spacing'] for q in react): react.append(r)
react.sort(key=lambda r: r['start'])
RW = {s: np.zeros(NB, np.float32) for s in spk}      # per-frame reaction reward
for r in react:
    i, j = fr(r['start']), fr(r['end'])
    RW[r['camera']][i:j] = 1.0 + (cad['reaction_bonus'] + cad['reaction_score_bonus'] * min(1.0, r.get('score', 0.5))) / max(1e-6, r['end'] - r['start'])
# ---- candidate trims (rule 7), base seconds ----
x = C.pcm(f'{cache}/wide.wav', ss=f0 / F, t=NB / F); H = 160; nf = len(x) // H
db = 20 * np.log10(np.sqrt((x[:nf * H].reshape(nf, H) ** 2).mean(1)) + 1e-7); tt = f0 / F + np.arange(nf) * 0.01
in_speech = np.zeros(nf, bool)
for s in spk + ['wide']:
    for v in VAD[s]['segments']: in_speech[max(0, int((v['start'] - f0 / F) * 100)):max(0, int((v['end'] - f0 / F) * 100))] = True
for s in spk:
    for w in W.get(s, []):
        if C.norm_word(w['text']): in_speech[max(0, int((w['start'] - 0.05 - f0 / F) * 100)):max(0, int((w['end'] + 0.05 - f0 / F) * 100))] = True
speech_db = float(np.median(db[in_speech])) if in_speech.any() else -30.0
quiet = (~in_speech) & (db < speech_db - cad['quiet_db'])
removals = []    # [a, b, kind, who, value]
st = None
for i, q in enumerate(list(quiet) + [False]):
    if q and st is None: st = i
    if not q and st is not None:
        a, b = tt[st], tt[st] + (i - st) * 0.01; st = None
        if b - a >= cad['pause']:
            ra, rb = a + cad['tail'], b - cad['pause_lead']
            if rb - ra >= 0.2: removals.append([ra, rb, 'pause', None])
def others_saying(sid, a, b): return any(spoken(o, a, b) > 0 for o in spk if o != sid)
def last_word_end(sid, t): return max([w['end'] for w in W.get(sid, []) if w['end'] <= t + 0.02 and C.norm_word(w['text']) not in PURE] + [-1e9])
def next_word_start(sid, t): return min([w['start'] for w in W.get(sid, []) if w['start'] >= t - 0.02 and C.norm_word(w['text']) not in PURE] + [1e9])
kept_tail = []
for s in spk:
    for f_ in C.load(f'{cache}/fillers_{s}.json', []):
        if f_['kind'] == 'repeat':      # only the CLEAN ones (fillers.py: a breath at both ends), cut exactly dip to dip
            if cad['trim_repeats'] and f_.get('clean') and not others_saying(s, f_['start'], f_['end']): removals.append([f_['start'], f_['end'], 'repeat', s])
            continue
        a, b = f_['start'] - 0.04, f_['end'] + 0.04
        if others_saying(s, a, b): continue
        # WHOLE or not at all (Colden 2026-10-01: "keep it safe"): the trim must begin >= 10 frames after the last word AND
        # before the um, and end after the um AND before the next word. Otherwise half an "u-" would stay: left in.
        pw = last_word_end(s, f_['start']); nw = next_word_start(s, f_['end'])
        if pw + cad['tail'] > a or nw - 0.02 < f_['end']: kept_tail.append((round(f_['start'], 2), names[s])); continue
        b = min(b, nw - 0.02)
        if b - a >= 0.12: removals.append([a, b, f_['kind'], s])
removals = [r for r in removals if r[0] >= P['start'] + cad['min_shot'] and r[1] <= P['end'] - cad['min_shot']]
removals.sort(key=lambda r: r[0])
def said_between(a, b): return any(spoken(s, a, b) > 0 for s in spk)
mg = []
for r in removals:   # an um + the dead air after it = ONE trim (AMIRA rule 10)
    if mg and r[0] <= mg[-1][1]: mg[-1][1] = max(mg[-1][1], r[1]); mg[-1][2] = mg[-1][2] if mg[-1][2] == r[2] else f'{mg[-1][2]}+{r[2]}'; mg[-1][3] = mg[-1][3] or r[3]
    elif mg and r[0] - mg[-1][1] < cad['merge_gap'] and not said_between(mg[-1][1], r[0]) and quiet[max(0, int((mg[-1][1] - f0 / F) * 100)):max(1, int((r[0] - f0 / F) * 100))].mean() >= 0.9:      # what is bridged must itself be quiet (a laugh between two pauses is not dead air)
        mg[-1][1] = r[1]; mg[-1][2] = mg[-1][2] if mg[-1][2] == r[2] else f'{mg[-1][2]}+{r[2]}'; mg[-1][3] = mg[-1][3] or r[3]
    else: mg.append(list(r))
NONWORD = PURE | {'umm', 'uhh', 'erm', 'eh'}
def words_inside(a, b, kind, who):
    """seconds of REAL words (anyone's) inside [a, b] - a trim must hold none. A repeat is exempt for its own speaker
    (the first take of the repeated word is what goes)."""
    tot = 0.0
    for s_ in spk:
        if 'repeat' in kind and s_ == who: continue
        tot += sum(max(0.0, min(b, w_['end']) - max(a, w_['start'])) for w_ in W.get(s_, []) if w_['end'] > a and w_['start'] < b and C.norm_word(w_['text']) and C.norm_word(w_['text']) not in NONWORD)
    return tot
cand = []; word_safe = 0
for a, b, kind, who in mg:
    i, j = int(np.ceil(a * F - 1e-6)) - f0, int(np.floor(b * F + 1e-6)) - f0
    if j - i < 3 or i < 1 or j > NB - 1: continue
    if special[max(0, i - int(F)):j + int(F)].any(): continue           # rule 8
    if words_inside((f0 + i) / F, (f0 + j) / F, kind, who) > 0.06: word_safe += 1; continue      # never a word inside a trim
    val = (cad['v_pause'] + cad['v_pause_per_sec'] * (j - i) / F) if 'pause' in kind else (cad['v_filler'] if 'filler' in kind else cad['v_repeat'])
    cand.append({'i': i, 'j': j, 'kind': kind, 'who': who, 'v': float(val)})
# ---- the compressed axis: base frames with every candidate trim taken out ----
keep = np.ones(NB, bool)
for r in cand: keep[r['i']:r['j']] = False
o2b = np.where(keep)[0]; T = len(o2b)
seamV = np.zeros(T + 1, np.float64); seam_of = {}
for r in cand:
    q = int(keep[:r['i']].sum()); r['q'] = q; seamV[q] += r['v']; seam_of.setdefault(q, []).append(r)
SC = np.cumsum(seamV)
# ---- per-frame scores (rules 2-5, 8, 9) ----
R = np.zeros((NC, NB), np.float32); w = cad['w']
R[0] = np.where(special, w['wide_special'], np.where(ntalk >= 2, w['wide_overlap'], np.where(ntalk == 0, w['wide_silence'], w['wide_one'])))
R[0] = np.where(wide_block, w['hard'], R[0])
near = int(1.5 * F)
for ci, k in enumerate(spk, 1):
    soon = np.convolve(Fm[k].astype(np.float32), np.ones(2 * near + 1, np.float32), 'same') > 0     # k talks within 1.5 s either side
    r = np.where(Fm[k] & (ntalk == 1), w['single_floor'], np.where(Fm[k], w['single_overlap'], np.where(ntalk == 0, np.where(soon, w['single_silence_near'], w['single_silence_far']), w['single_other_talking'])))
    r = np.where(HOLD[k] & ~Fm[k], w['hard'], r)
    # ...and no close-up may sit more than `max_other_floor` on k while ONLY someone else has the floor, whatever kind of
    # run it is (HOLD above only covers runs of >= 1 s that k does not talk over): the middle of every longer stretch is
    # closed, so a shot can touch its first or last half-allowance but never cross it (Ep 23 5:46: 2.8 s on Erik).
    oth_ = np.zeros(NB, bool)
    for j_ in spk:
        if j_ != k: oth_ |= Fm[j_]
    lone_ = oth_ & ~Fm[k]; half_ = int(cad['max_other_floor'] * F / 2); d_ = np.diff(np.concatenate([[0], lone_.astype(np.int8), [0]]))
    for a_, b_ in zip(np.where(d_ == 1)[0], np.where(d_ == -1)[0]):
        if b_ - a_ > 2 * half_: r[a_ + half_:b_ - half_] = w['hard']
    r = np.where(special | offair[k], w['hard'], r)
    r = np.where(RW[k] > 0, RW[k], r)
    r = np.where(~present[k] | nocover[k], w['hard'], r)                                           # out of frame, or the camera has no picture there: never                                                             # an approved reaction is the one listener shot that is allowed - also over a share / played video
    R[ci] = r
cum = np.zeros((NC, T + 1), np.float64); cum[:, 1:] = np.cumsum(R[:, o2b].astype(np.float64) / F, axis=1)
spec_o = special[o2b]
# ---- where a cut is cheap or dear: at a sentence start / in a breath it is cheap, inside a word it is dear ----
inword = np.zeros(NB, bool); natural = np.zeros(NB, bool)
for sp_ in spk:
    ws = sorted((w_ for w_ in W.get(sp_, []) if C.norm_word(w_['text'])), key=lambda w_: w_['start'])
    for w_ in ws:
        if C.norm_word(w_['text']) not in PURE: inword[max(0, fr(w_['start'] + 0.03)):max(0, fr(w_['end'] - 0.03))] = True
    for p_, q_ in zip(ws, ws[1:]):
        if re.search(r'[.?!]$', p_['text'].strip()) and q_['start'] - p_['end'] >= 0.15: i_ = fr(q_['start'] - 0.1); natural[max(0, i_ - 2):max(0, i_ + 3)] = True
        elif q_['start'] - p_['end'] >= 0.35: i_ = fr(q_['start'] - 0.1); natural[max(0, i_ - 2):max(0, i_ + 3)] = True
natural &= ~inword
Kpos = np.full(T + 1, cad['cut_cost'], np.float64)
Kpos[:T] += np.where(inword[o2b], cad['cut_in_word'], 0.0) - np.where(natural[o2b], cad['cut_natural'], 0.0)
Kpos[seamV > 0] = cad['cut_cost'] - cad['cut_natural']          # a trim is a breath by construction
# ---- shot-length terms (rule 6) ----
minF, maxF = int(round(cad['min_shot'] * F)), int(round(cad['max_shot'] * F))
d = np.arange(maxF + 1) / F
gd = -cad['short_cost'] * np.maximum(0.0, cad['short_under'] - d) - cad['long_cost'] * np.maximum(0.0, d - cad['long_over']) ** 2
gwin = gd[maxF:minF - 1:-1].copy()                 # for s = t - maxF ... t - minF
NEG = -1e12
Aa = np.full((NC, T + 1), NEG); E = np.full((T + 1, NC), NEG); bp = np.zeros((T + 1, NC), np.int32); pc = np.full((T + 1, NC), -1, np.int8)
Aa[:, 0] = 0.0 - cum[:, 0] + SC[0]
SCprev = np.concatenate([[0.0], SC[:-1]])          # SC[t - 1]
for t in range(minF, T + 1):
    lo = max(0, t - maxF); hi = t - minF
    win = Aa[:, lo:hi + 1] + gwin[-(hi - lo + 1):]
    ix = win.argmax(1); best = win[np.arange(NC), ix]
    E[t] = cum[:, t] - SCprev[t] + best; bp[t] = lo + ix
    e = E[t]; o = np.argsort(e)[::-1]; b1, b2 = int(o[0]), int(o[1])
    B = np.where(np.arange(NC) == b1, e[b2], e[b1]) - Kpos[t]; pcv = np.where(np.arange(NC) == b1, b2, b1)
    if t < T and spec_o[t] and spec_o[t - 1] and e[0] - seamV[t] > B[0]: B[0] = e[0] - seamV[t]; pcv[0] = 0      # the wide carries on through a share (not a cut)
    pc[t] = pcv; Aa[:, t] = B - cum[:, t] + SC[t]
assert E[T].max() > NEG / 2, 'no feasible plan (the episode is shorter than one shot?)'
shots = []; t = T; c = int(E[T].argmax())
while True:
    s = int(bp[t][c]); shots.append([s, t, c])
    if s == 0: break
    c = int(pc[s][c]); t = s
shots.reverse()
ms = []
for s, t, c in shots:
    if ms and ms[-1][2] == c: ms[-1][1] = t
    else: ms.append([s, t, c])
# ---- back to base frames; a trim inside a shot was not hidden -> it goes back (the shot simply spans it) ----
applied, kept = [], []
bounds = {s for s, t, c in ms}
for r in cand: (applied if r['q'] in bounds and r['q'] not in (0, T) else kept).append(r)
segs = []; out_f = 0
for s, t, c in ms:
    a = int(o2b[s]); b = int(o2b[t - 1]) + 1; cam = cams[c]
    inside = RW[cam][a:b] > 0 if cam != 'wide' else np.zeros(1, bool)
    if cam == 'wide': reason = 'special' if special[a:b].mean() > 0.5 else ('overlap' if (ntalk[a:b] >= 2).mean() > 0.3 else 'wide')
    else: reason = 'reaction' if inside.mean() > 0.6 else 'speaker'
    if any(r['q'] == s for r in applied): reason += '+trim'
    segs.append({'srcFrames': [f0 + a, f0 + b], 'srcStart': round((f0 + a) / F, 4), 'srcEnd': round((f0 + b) / F, 4), 'camera': cam, 'name': names[cam], 'reason': reason,
                 'outFrame': out_f, 'frames': b - a, 'outStart': round(out_f / F, 4), 'outEnd': round((out_f + b - a) / F, 4), 'zoom': False}); out_f += b - a
# ---- GATES ----
assert segs[0]['srcFrames'][0] == f0 and segs[-1]['srcFrames'][1] == f1, 'the plan does not run from start to end'
for p_, q_ in zip(segs, segs[1:]):
    gap = q_['srcFrames'][0] - p_['srcFrames'][1]
    assert gap >= 0, f"shots overlap at {p_['srcEnd']}"
    assert p_['camera'] != q_['camera'], f"same camera on both sides of a cut at {C.hms(q_['srcStart'])} (a jump cut)"
    if gap: assert any(f0 + r['i'] == p_['srcFrames'][1] and f0 + r['j'] == q_['srcFrames'][0] for r in applied), f"frames missing at {C.hms(p_['srcEnd'])} that are not a planned trim"
short = [(C.hms(s_['outStart']), round(s_['frames'] / F, 2), s_['name']) for s_ in segs if s_['frames'] < minF]
assert not short, f'shots under {cad["min_shot"]} s: {short[:5]}'
for s_ in segs:
    a, b = s_['srcFrames'][0] - f0, s_['srcFrames'][1] - f0
    if s_['camera'] == 'wide': continue
    assert not (special[a:b] & ~(RW[s_['camera']][a:b] > 0)).any(), f"close-up of {s_['name']} at {C.hms(s_['srcStart'])} while the program is in a special layout (share / video) and it is not a reaction"
    sp_ = share_of(s_['srcStart'], s_['srcEnd']) if special[a:b].any() else None
    if sp_:      # the share rule, asserted on the shot itself
        assert 'reaction' in s_['reason'] and b - a <= int(round(cad['share_cutaway'] * F)) + 1, f"cutaway from the share at {C.hms(s_['srcStart'])} is {(b - a) / F:.1f} s - over a share a cutaway is {cad['share_cutaway']} s or less"
        assert sp_[1] - sp_[0] > cad['share_min'] and s_['srcStart'] >= sp_[0] + share_lead(s_['srcStart']) - 1.0 / F, f"cutaway at {C.hms(s_['srcStart'])}: the share had been up {s_['srcStart'] - sp_[0]:.1f} s, it needs {share_lead(s_['srcStart'])} s first"
        s_['reason'] = 'reaction+share'
    assert not offair[s_['camera']][a:b].any(), f"{s_['name']} shown at {C.hms(s_['srcStart'])} while off air"
    bad = HOLD[s_['camera']][a:b] & ~Fm[s_['camera']][a:b] & ~(RW[s_['camera']][a:b] > 0)
    assert not bad.any(), f"close-up held on {s_['name']} at {C.hms(s_['srcStart'] + float(np.argmax(bad)) / F)} while someone else has the floor"
    assert not nocover[s_['camera']][a:b].any(), f"{s_['name']} shown at {C.hms(s_['srcStart'])} where their camera file has no picture"
    assert (~present[s_['camera']][a:b]).mean() <= 0.25, f"{s_['name']} at {C.hms(s_['srcStart'])}: out of frame / out of place for {(~present[s_['camera']][a:b]).mean() * 100:.0f} % of the shot"
    if 'reaction' not in s_['reason']:
        nreal = sum(1 for w_ in W.get(s_['camera'], []) if s_['srcStart'] - cad['lead'] - 0.1 <= w_['start'] < s_['srcEnd'] and C.norm_word(w_['text']) and C.norm_word(w_['text']) not in BACK)
        assert nreal >= 2, f"close-up of {s_['name']} at {C.hms(s_['srcStart'])} holds {nreal} real word(s) of theirs - a close-up needs real words"
        oth = np.zeros(b - a, bool)
        for j_ in spk:
            if j_ != s_['camera']: oth |= Fm[j_][a:b]
        lone = oth & ~Fm[s_['camera']][a:b] & ~(RW[s_['camera']][a:b] > 0); run = best = 0
        for v_ in lone:
            run = run + 1 if v_ else 0; best = max(best, run)
        s_['_other_floor'] = best
        assert best <= cad['max_other_floor'] * F, f"close-up of {s_['name']} at {C.hms(s_['srcStart'])} stays on them for {best / F:.1f} s while only someone else has the floor"
    kept_in = sum(r['j'] - r['i'] for r in kept if a <= r['i'] and r['j'] <= b)
    assert b - a <= maxF + kept_in + 2, f"close-up of {s_['name']} at {C.hms(s_['srcStart'])} runs {(b - a) / F:.1f} s (limit {cad['max_shot']} s plus {kept_in / F:.1f} s of trims left inside it)"
for s_ in segs:
    a, b = s_['srcFrames'][0] - f0, s_['srcFrames'][1] - f0
    if s_['camera'] != 'wide': continue
    assert not wide_block[a:b].any(), f"the program picture at {C.hms(s_['srcStart'])} is the intro / outro graphic, not the talk layout"
    if not special[a:b].any():
        kept_in = sum(r['j'] - r['i'] for r in kept if a <= r['i'] and r['j'] <= b)
        assert b - a <= maxF + kept_in + 2, f"the wide at {C.hms(s_['srcStart'])} runs {(b - a) / F:.1f} s outside a share (limit {cad['max_shot']} s)"
for r in applied: assert words_inside((f0 + r['i']) / F, (f0 + r['j']) / F, r['kind'], r['who']) <= 0.06, f"a word sits inside the trim at {C.hms((f0 + r['i']) / F)}"
worst_other = max([s_.pop('_other_floor', 0) for s_ in segs] + [0]) / F
# ---- report ----
dur = [s_['frames'] / F for s_ in segs]; per = collections.Counter(); n_by = collections.Counter(s_['reason'].split('+')[0] for s_ in segs)
for s_ in segs: per[s_['name']] += s_['frames'] / F
def out_time(fb):
    for s_ in segs:
        if s_['srcFrames'][0] <= fb <= s_['srcFrames'][1]: return s_['outStart'] + (fb - s_['srcFrames'][0]) / F
rep = [{'kind': r['kind'], 'who': names.get(r['who']), 'srcStart': round((f0 + r['i']) / F, 3), 'srcEnd': round((f0 + r['j']) / F, 3), 'cut': round((r['j'] - r['i']) / F, 2), 'outTime': round(out_time(f0 + r['i']) or 0, 2)} for r in applied]
kc = collections.Counter(r['kind'] for r in kept); ac = collections.Counter(r['kind'] for r in applied)
stats = {'rules': RULES, 'shots': len(segs), 'out_frames': out_f, 'out_duration': round(out_f / F, 2), 'source_duration': round(NB / F, 2), 'removed_sec': round(sum(r['cut'] for r in rep), 1),
         'avg_shot': round(float(np.mean(dur)), 1), 'median_shot': round(float(np.median(dur)), 1), 'min_shot': round(min(dur), 2), 'max_shot': round(max(dur), 1), 'cuts_per_min': round((len(segs) - 1) / (out_f / F / 60), 1),
         'per_camera_pct': {k: round(100 * v / (out_f / F), 1) for k, v in per.items()}, 'by_reason': dict(n_by), 'trims_applied': dict(ac), 'trims_kept': dict(kc), 'ums_on_word_tail': len(kept_tail),
         'reactions_passed_gate': len(offered), 'reactions_refused_over_share': n_share_no, 'reactions_new_talker': n_unsteady, 'cutaways_over_share': sum('share' in s_['reason'] and 'reaction' in s_['reason'] for s_ in segs), 'reactions_offered': len(react), 'reactions_used': n_by.get('reaction', 0), 'shots_under_short': int(sum(x < cad['short_under'] for x in dur)), 'trims_dropped_for_a_word': word_safe, 'longest_other_floor_in_closeup': round(worst_other, 2), 'overrides': A.set, 'cadence': cad}
# ---- sanity bands: a plan outside them is not built without Colden (exit 2) - they catch a run that went wrong quietly ----
live_s = NB / F; spec_s = float(special.sum()) / F; talk_s = max(1.0, live_s - spec_s); odd = []
wide_talk = sum(s_['frames'] for s_ in segs if s_['camera'] == 'wide' and 'special' not in s_['reason']) / F
if not (cad['sane']['cuts_per_min'][0] <= stats['cuts_per_min'] <= cad['sane']['cuts_per_min'][1]) and spec_s < 0.3 * live_s: odd.append(f"{stats['cuts_per_min']} cuts a minute (usual {cad['sane']['cuts_per_min']})")
if wide_talk / talk_s > cad['sane']['wide_share']: odd.append(f'the wide holds {wide_talk / talk_s * 100:.0f} % of the talk time (limit {cad["sane"]["wide_share"] * 100:.0f} %)')
if stats['removed_sec'] > cad['sane']['removed_share'] * live_s: odd.append(f"{stats['removed_sec']} s trimmed = {stats['removed_sec'] / live_s * 100:.1f} % of the show (limit {cad['sane']['removed_share'] * 100:.0f} %)")
for k in spk:
    floor_s = float((Fm[k] & (ntalk == 1) & ~special).sum()) / F; cu_s = sum(s_['frames'] for s_ in segs if s_['camera'] == k and 'reaction' not in s_['reason']) / F
    if floor_s >= 120 and cu_s < cad['sane']['closeup_of_floor'] * floor_s: odd.append(f'{names[k]} has the floor for {floor_s / 60:.1f} min but only {cu_s / 60:.1f} min of close-up - camera out of place, off air, or mis-synced?')
stats['sanity'] = odd
out = out_path if not odd or A.out else f'{cache}/plan.rejected.json'
C.save(out, {'fps': F, 'start': f0 / F, 'end': f1 / F, 'rules': RULES, 'segments': segs, 'removals': rep, 'kept': [{'kind': r['kind'], 'who': names.get(r['who']), 'srcStart': round((f0 + r['i']) / F, 2), 'srcEnd': round((f0 + r['j']) / F, 2)} for r in kept], 'stats': stats})
print(json.dumps({k: v for k, v in stats.items() if k != 'cadence'}, indent=1)); print('->', out)
if odd: C.die('the plan passes its rules but looks WRONG: ' + '; '.join(odd) + ' - look, then tell Colden (saved as plan.rejected.json, not plan.json)')
