"""Filler finder (um / uh / er) per speaker - the audio is searched directly because Whisper drops most fillers.
usage: fillers.py <CACHE> [--one speaker_2] [--repeats-only]   -> <CACHE>/fillers_<speaker>.json [{start, end, heard, kind}]
Candidates (as in AMIRA_podcut): (a) speech islands on the speaker's own stem, cut down to the part NO transcribed word
of theirs touches, (b) gaps >= 0.45 s between two of their words that carry energy - both only mid-sentence (a real
word of theirs within 1.5 s before AND after). Each one is re-decoded ALONE (prompt "Um. Uh. Hmm.").
A candidate is a filler ONLY when it decodes to a filler token (at most one other word beside it) AND sits inside that
speaker's own talk (a real word of theirs within 1.5 s). An um / uh Whisper transcribed as its own word is trusted. Nothing-decoded islands are NOT fillers here: on this show they are laughs, breaths and claps,
and laughs stay in. Back-channels ("mm", "mhm", "yeah") are words of a listener - never trimmed.
Word repeats are listed too (kind 'repeat', `clean` true / false - see find_repeats); --repeats-only redoes just those."""
import os, sys, re, json, subprocess
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

cache = sys.argv[1]; m = C.manifest(cache)
FILL = {'um', 'uh', 'uhm', 'umm', 'er', 'erm', 'ah', 'eh', 'uhh', 'hmm'}      # not counted as words of a sentence
TRIM = {'um', 'uh', 'uhm', 'umm', 'uhh', 'er', 'erm'}                       # what may be trimmed: "ah" / "eh" / "hmm" are also reactions ("Ah, I see") and stay
if '--one' in sys.argv:
    sid = sys.argv[sys.argv.index('--one') + 1]
    from faster_whisper import WhisperModel
    x = C.pcm(f'{cache}/{sid}.wav'); HOP = 160; n = len(x) // HOP
    db = 20 * np.log10(np.sqrt((x[:n * HOP].reshape(n, HOP) ** 2).mean(1)) + 1e-6)
    on = db > max(np.percentile(db, 20) + 12, -45)
    isl = []; st = None
    for i, v in enumerate(list(on) + [False]):
        if v and st is None: st = i
        if not v and st is not None:
            if isl and (st - isl[-1][1]) * 0.01 < 0.12: isl[-1][1] = i
            else: isl.append([st, i])
            st = None
    isl = [(a * 0.01, b * 0.01) for a, b in isl]
    words = sorted(json.load(open(f'{cache}/words.json'))[sid], key=lambda w: w['start'])
    real = [w for w in words if C.norm_word(w['text']) and C.norm_word(w['text']) not in FILL]
    starts = np.array([w['start'] for w in real]); ends = np.array([w['end'] for w in real])
    # ---- word repeats (Colden 2026-10-01: "If you can cleanly kill the repetitions, yes. If not, keep safe.") ----
    # A repeat = the same FUNCTION word twice in a row ("I I", "the the", "it's it's") - never an emphasis ("really
    # really", "love love", "no no"). It is CLEAN only when the speaker's own stem dips (>= 12 dB under their speech
    # level) both where the first take starts and just before the second take: then the cut lands in two breaths and
    # does not depend on Whisper's word edges (+-50 ms). The trim = dip to dip, i.e. the first take and the pause after
    # it. Anything else is listed with clean = false and left in.
    FUNC = {'i', 'the', 'a', 'an', 'to', 'and', 'it', "it's", 'that', "that's", 'we', 'you', 'they', 'he', 'she', 'is', 'in', 'of', 'on', 'for', 'but', 'so', 'if', 'my', 'this',
            'what', 'when', 'with', 'was', 'are', "i'm", "we're", "you're", "they're", "there's", 'there', 'because', 'or', 'as', 'at', 'be', 'have', 'like', 'just', 'which', 'then', 'from', 'our', 'your', 'his', 'her', 'their', 'do', 'can', 'will', 'would', 'how', 'where', 'who', 'not', "don't", "i've", "we've", "you've"}
    sp_db = float(np.median(db[on])) if on.any() else -30.0
    def dip(t0, t1):
        i0, i1 = max(0, int(t0 * 100)), min(len(db), int(t1 * 100))
        if i1 <= i0: return None
        k = i0 + int(np.argmin(db[i0:i1])); return (k * 0.01 + 0.005, float(db[k]))
    def find_repeats():
        out = []; toks = [(C.norm_word(w['text']), w) for w in words]; toks = [(t, w) for t, w in toks if t]; i = 0
        while i < len(toks) - 1:
            (t0, w0), (t1, w1) = toks[i], toks[i + 1]
            if t0 == t1 and w1['start'] - w0['end'] <= 1.2 and w1['start'] - w0['start'] >= 0.25:
                r = {'start': round(w0['start'], 2), 'end': round(w1['start'], 2), 'heard': f'{t0} | {t0}', 'kind': 'repeat', 'from': 'words', 'clean': False}
                if t0 in FUNC and not (i + 2 < len(toks) and toks[i + 2][0] == t0):       # three in a row is a rhythm, not a stumble
                    d0 = dip(w0['start'] - 0.12, w0['start'] + 0.04); d1 = dip(max(w0['end'], w1['start'] - 0.2), w1['start'] + 0.02)
                    if d0 and d1 and d0[1] <= sp_db - 12 and d1[1] <= sp_db - 12 and 0.2 <= d1[0] - d0[0] <= 1.6:
                        r.update({'start': round(d0[0], 3), 'end': round(d1[0], 3), 'clean': True})
                    else: r['why_not'] = 'no breath at both ends'
                else: r['why_not'] = 'not a function word (may be emphasis)' if t0 not in FUNC else 'said three times'
                out.append(r); i += 2; continue
            i += 1
        return out
    if '--repeats-only' in sys.argv:      # fast: no Whisper, keeps the fillers already found
        keep = [k for k in C.load(f'{cache}/fillers_{sid}.json', []) if k['kind'] != 'repeat'] + find_repeats(); keep.sort(key=lambda k: k['start'])
        C.save(f'{cache}/fillers_{sid}.json', keep)
        print(f"{sid}: {sum(k['kind'] == 'filler' for k in keep)} fillers kept, {sum(k['kind'] == 'repeat' for k in keep)} repeats, {sum(bool(k.get('clean')) for k in keep)} of them clean"); sys.exit(0)
    def own_talk(a, b, both=False):
        """a real word of this speaker within 1.5 s before / after (both = mid-sentence: before AND after)"""
        if not len(real): return False
        i = np.searchsorted(starts, a - 30); j = np.searchsorted(starts, b + 1.5)
        before = bool(np.any((ends[i:j] > a - 1.5) & (ends[i:j] <= a + 0.05))); after = bool(np.any((starts[i:j] >= b - 0.05) & (starts[i:j] < b + 1.5)))
        return (before and after) if both else (before or after)
    def uncovered(a, b):
        """the longest part of [a, b] that no REAL transcribed word of this speaker touches (a trim must never hold a word:
        an island half-covered by "So" used to be listed whole - audit 2026-10-01)"""
        i = np.searchsorted(starts, a - 30); j = np.searchsorted(starts, b); cuts = sorted((max(a, s_ - 0.02), min(b, e_ + 0.02)) for s_, e_ in zip(starts[i:j], ends[i:j]) if e_ > a and s_ < b)
        best = None; cur = a
        for s_, e_ in cuts + [(b, b)]:
            if s_ - cur > (best[1] - best[0] if best else 0): best = (cur, s_)
            cur = max(cur, e_)
        return best
    cand = {}
    for a, b in isl:
        if not (0.15 <= b - a <= 1.5 and own_talk(a, b, both=True)): continue
        u = uncovered(a, b)
        if u and u[1] - u[0] >= 0.15: cand[(round(u[0], 2), round(u[1], 2))] = 'island'
    for w1, w2 in zip(words, words[1:]):
        g0, g1 = w1['end'], w2['start']
        if g1 - g0 >= 0.45 and on[int(g0 * 100):int(g1 * 100)].mean() >= 0.3:
            idx = np.where(on[int(g0 * 100):int(g1 * 100)])[0]; a, b = g0 + idx[0] * 0.01, g0 + (idx[-1] + 1) * 0.01
            if 0.12 <= b - a <= 1.5 and own_talk(a, b, both=True): cand[(round(a, 2), round(b, 2))] = f'gap "{w1["text"].strip()}" | "{w2["text"].strip()}"'
    # a filler Whisper DID transcribe as its own word: trusted as is (re-decoded alone it comes back with its neighbour -
    # "So, um." - Ep 24 2:02, which the all-filler test below then threw away). Its range = the sound inside the word's
    # span (Whisper stretches an "um" over the pause after it).
    keep = []; taken = []
    for w in words:
        if C.norm_word(w['text']) in TRIM and w.get('p', 1) >= 0.4 and own_talk(w['start'], w['end']):
            i0, i1 = int(max(0, w['start'] - 0.05) * 100), int((w['end'] + 0.05) * 100); idx = np.where(on[i0:i1])[0]
            if not len(idx): continue
            a, b = (i0 + idx[0]) * 0.01, (i0 + idx[-1] + 1) * 0.01
            if 0.12 <= b - a <= 1.5: keep.append({'start': round(a, 2), 'end': round(b, 2), 'heard': w['text'].strip(), 'kind': 'filler', 'from': 'word'}); taken.append((a, b))
    model = WhisperModel('small.en', device='cpu', compute_type='int8', cpu_threads=4)
    for (a, b), kind in sorted(cand.items()):
        if any(a < tb + 0.1 and b > ta - 0.1 for ta, tb in taken): continue
        seg = x[int(max(0, a - 0.06) * 16000):int((b + 0.06) * 16000)]
        segs, _ = model.transcribe(seg, initial_prompt='Um. Uh. Hmm.', beam_size=3, condition_on_previous_text=False)
        txt = ' '.join(s.text for s in segs).strip(); toks = re.findall(r"[a-z']+", txt.lower())
        # an island no transcribed word covers: a filler when the decode holds a filler token and at most one other word
        # (Whisper pads a lone "um" with a guess); a decode of several real words is speech the transcript missed - kept
        if any(t in TRIM for t in toks) and sum(t not in TRIM for t in toks) <= 1 and len(toks) <= 3: keep.append({'start': a, 'end': b, 'heard': txt, 'kind': 'filler', 'from': kind})
    keep += find_repeats()
    keep.sort(key=lambda k: k['start']); C.save(f'{cache}/fillers_{sid}.json', keep)
    print(f"{sid}: {len(cand)} candidates -> {sum(k['kind'] == 'filler' for k in keep)} fillers, {sum(k['kind'] == 'repeat' for k in keep)} repeats ({sum(bool(k.get('clean')) for k in keep)} clean)"); sys.exit(0)
extra = ['--repeats-only'] if '--repeats-only' in sys.argv else []
procs = [(c, subprocess.Popen([sys.executable, os.path.abspath(__file__), cache, '--one', c['id']] + extra, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)) for c in C.speakers(m)]
for c, p in procs:
    out, err = p.communicate(); print(f"{c['name']:8s} {out.strip()}")
    assert p.returncode == 0, f"fillers failed for {c['name']}: {err[-300:]}"
