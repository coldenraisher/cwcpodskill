"""captions.py <WORK> <id> <cwc|tcl>      the YouTube caption file (SRT) of one LOCKED / approved clip version
-> WORK/package/<id>/<timeline>.srt  (+ .captions.json: counts, names to check, what was fixed / left out)
The words come from the transcript (phrases.json, CUT clock) and are placed on the CLIP's clock through the version's
frozen cut (build plan `shots`): a word plays where its middle falls inside a shot - words a trim removed never show,
the cold open and the body are both captioned, the stinger and the end screen are not. The version is the one in
lock.json (the locked clip); before the lock, the newest version approved for that channel.
CUES   built per speaker (so cross-talk never chops a sentence into one-word cues), one or two lines of <= 42
       characters, <= 6 s, broken at sentence ends, at pauses >= 0.6 s and at every splice; then put on one clock: a
       1-2 word back-channel ("yeah", "right") spoken UNDER another speaker's line is left out (counted in the json);
       no cue overlaps the next; a cue shorter than 0.5 s is merged into its neighbour.
WORDS  swears are written "[ __ ]" (YouTube's own mark; the picture beeps them). Names Whisper mishears are fixed from
       WORK/caption_fixes.json {"heard": "right"} - case-insensitive, whole words, also with 's / s, also several
       words ("higgs field": "Higgsfield"). Whisper's stray mid-sentence capitals are lowered ONLY for plain function
       words ("successful, We can" -> "we") and the words listed under "_lower" in caption_fixes.json; a name is
       never lowered.
LOOK   `look_at_names`: every capitalised mid-sentence word that is not a known person or a fix target, plus
       `case_varies`: words written lower-case here but capitalised elsewhere in the episode (a name Whisper lowered).
       Read both lists against the conversation; put real corrections into caption_fixes.json and run again.
Not burned in - an upload file only (no captions on the picture)."""
import os, re, sys, json
import common as C, cut as K

FUNC = set("""a an the and but or so nor yet if then than that this these those there here when where what which who whom whose why how because
while although though unless until since as like just well yeah yes no not okay ok oh uh um we you they he she it i'm i've i'll i'd we're we've we'll you're you've
you'll they're they've they'll he's she's it's that's there's what's let's to of in on at for with from by about into over under after before between through
is are was were be been being am do does did done have has had having can could would should will shall may might must my your our their his her its me us them
him all some any each every both either neither one two three many much more most other another such only also even still again very really too now""".split())
END = re.compile(r'[.?!]["\')]?$')
def core_of(t): return re.sub(r"^[^A-Za-z0-9']+|[^A-Za-z0-9']+$", '', t)

def srt_time(f, fps):
    ms = int(round(f / fps * 1000)); h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
    return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'

def words_on_clip(W, P):
    """-> [[rec_start, rec_end, text, who, pid, splice_before]] in play order"""
    fps = P['fps']; F = lambda t: int(round(float(t) * fps)); out = []
    ph = C.load(f'{W}/phrases.json'); ws = [(F(a), F(b), t, p['who'], p['id']) for p in ph for t, a, b in p['w']]
    ws.sort()
    for n, s in enumerate(P['shots']):
        spl = bool(s.get('splice')) or n == 0 or P['shots'][n - 1]['kind'] != s['kind']
        first = True
        for a, b, t, who, pid in ws:
            mid = (a + b) / 2
            if mid < s['a'] or mid >= s['b']: continue
            r0 = s['rec'] + max(a, s['a']) - s['a']; r1 = s['rec'] + min(b, s['b']) - s['a']
            out.append([r0, max(r0 + 1, r1), t, who, pid, spl and first]); first = False
    out.sort(key=lambda x: x[0])
    return out

def fix_words(words, fixes, E, lower=()):
    """swear masks, caption fixes (single words with 's / s, and multi-word keys), stray capitals on function words"""
    log = {'fixed': [], 'masked': 0, 'lowered': 0}
    multi = sorted([k for k in fixes if ' ' in k], key=lambda k: -len(k.split()))
    i = 0
    while i < len(words):                                 # multi-word keys first: "higgs field" -> "Higgsfield"
        for k in multi:
            toks = k.split(); seg = words[i:i + len(toks)]
            if len(seg) == len(toks) and all(s[3] == seg[0][3] for s in seg) and [core_of(s[2]).lower() for s in seg] == toks:
                tail = re.search(r"[^A-Za-z0-9']*$", seg[-1][2]).group(0); tail = tail[1:] if fixes[k].endswith('.') and tail.startswith('.') else tail; words[i][2] = fixes[k] + tail; words[i][1] = seg[-1][1]; del words[i + 1:i + len(toks)]; log['fixed'].append(k); break
        i += 1
    for w in words:
        c = core_of(w[2]); lc = c.lower()
        if not c: continue
        if K.is_swear(E, c): w[2] = w[2].replace(c, '[ __ ]', 1); log['masked'] += 1; continue
        for suf in ('', "'s", 's'):
            base = lc[:len(lc) - len(suf)] if suf and lc.endswith(suf) else (lc if not suf else None)
            if base and base in fixes and ' ' not in base: w[2] = w[2].replace(c, fixes[base] + suf, 1); log['fixed'].append(base); break
    for w in words:                                       # a section that opens mid-sentence still starts with a capital
        c = core_of(w[2])
        if w[5] and c[:1].islower(): w[2] = w[2].replace(c, c[0].upper() + c[1:], 1)
    for i, w in enumerate(words):
        c = core_of(w[2])
        if i and not w[5] and c[:1].isupper() and c[1:].islower() and (c.lower() in FUNC or c.lower() in lower) and words[i - 1][3] == w[3] and not END.search(words[i - 1][2]):
            w[2] = w[2].replace(c, c.lower(), 1); log['lowered'] += 1
    return log

def speaker_cues(ws, fps):
    """one speaker's words -> cues [start, end, text, who, n_words]"""
    L, MAXD, GAP = 42, int(6 * fps), int(0.6 * fps); out = []; cur = []
    def text(x): return ' '.join(w[2] for w in x)
    def flush():
        if cur: out.append([cur[0][0], cur[-1][1], text(cur), cur[0][3], len(cur)]); cur.clear()
    for w in ws:
        if cur and (w[5] or w[0] - cur[-1][1] >= GAP or len(text(cur + [w])) > 2 * L or w[1] - cur[0][0] > MAXD): flush()
        cur.append(w)
        if END.search(w[2]) and len(text(cur)) >= 20 or w[2].endswith(',') and len(text(cur)) >= 34: flush()
    flush(); return out

def cues(words, fps):
    """-> ([start, end, text], backchannels left out)"""
    L = 42; MIN = int(0.5 * fps); HOLD = int(0.3 * fps); allc = []
    for who in sorted({w[3] for w in words}): allc += speaker_cues([w for w in words if w[3] == who], fps)
    allc.sort(key=lambda c: (c[0], c[1])); keep = []; dropped = 0
    for c in allc:                                        # a 1-2 word back-channel under another speaker's line is not captioned
        if c[4] <= 2 and any(o is not c and o[3] != c[3] and o[4] > 2 and o[0] < c[1] and o[1] > c[0] for o in allc): dropped += 1; continue
        keep.append(c)
    out = []
    for c in keep:
        if out and c[0] < out[-1][1]: out[-1][1] = max(out[-1][0] + 1, c[0])       # never overlapping: the earlier cue yields
        out.append([c[0], c[1], c[2], c[3]])
    i = 0
    while i < len(out):                                   # a cue too short to read joins its neighbour (same speaker first)
        c = out[i]; nxt = out[i + 1] if i + 1 < len(out) else None; room = (nxt[0] if nxt else c[1] + HOLD) - c[0]
        if room < MIN and len(out) > 1:
            j = i + 1 if nxt and (i == 0 or nxt[3] == c[3] or out[i - 1][3] != c[3]) else i - 1
            if j > i: out[j][0] = c[0]; out[j][2] = c[2] + ' ' + out[j][2]
            else: out[j][1] = max(out[j][1], c[1]); out[j][2] = out[j][2] + ' ' + c[2]
            del out[i]; i = max(0, i - 1); continue
        c[1] = max(c[1], min(c[0] + MIN, nxt[0] if nxt else c[0] + MIN)); c[1] = min(c[1] + HOLD, nxt[0]) if nxt else c[1] + HOLD
        i += 1
    for c in out:                                         # two lines when long: break at the space nearest the middle
        if len(c[2]) > L and ' ' in c[2]:
            sp = [m.start() for m in re.finditer(' ', c[2])]; k = min(sp, key=lambda i: abs(i - len(c[2]) / 2)); c[2] = c[2][:k] + '\n' + c[2][k + 1:]
    return [[c[0], c[1], c[2]] for c in out], dropped

def version(W, tid, ch):
    L = C.load(f'{W}/lock.json') or {}; lc = next((c for c in L.get('clips', []) if c['theme'] == tid and c['channel'] == ch), None); vs = C.load(C.vpath(W, tid), [])
    if lc: v = next((x for x in vs if x['channel'] == ch and x['v'] == lc['v']), None)
    else: v = next((x for x in reversed(vs) if x['channel'] == ch and x.get('status') in ('approved', 'locked') and ch in (x.get('channels') or [])), None)
    if not v: C.fail(f'{tid} has no version approved for {ch}')
    return v

def build(W, tid, ch):
    v = version(W, tid, ch); P = C.load(v['plan']); fps = P['fps']; E = K.cfg(); ep = C.episode(W)
    raw = C.load(f'{W}/caption_fixes.json', {}) or {}; low = {x.lower() for x in raw.get('_lower', [])}       # "_lower": plain words Whisper capitalised mid-sentence ("to Create the")
    fixes = {k.lower().strip(): val for k, val in raw.items() if not k.startswith('_')}
    words = words_on_clip(W, P); log = fix_words(words, fixes, E, low)
    cs, dropped = cues(words, fps)
    bad = [c for c in cs if c[1] <= c[0]]
    if bad: C.fail(f'{tid} {ch}: {len(bad)} caption cue(s) with no duration - a bug in captions.py, not shipped')
    name = v['timeline']; out = f'{W}/package/{tid}'; os.makedirs(out, exist_ok=True)
    srt = '\n'.join(f'{i + 1}\n{srt_time(a, fps)} --> {srt_time(b, fps)}\n{t}\n' for i, (a, b, t) in enumerate(cs))
    open(f'{out}/{name}.srt', 'w').write(srt)
    known = set()
    for p in ep.get('people', []): known |= {x.lower() for x in (p['name'] + ' ' + str(p.get('full_name') or '')).split()}
    known |= {x.lower() for val in fixes.values() for x in val.split()}
    capital_somewhere = set()                             # words the EPISODE writes with a capital in mid-sentence
    for p in C.load(f'{W}/phrases.json'):
        for k, (t, _, _) in enumerate(p['w']):
            c = core_of(t)
            if k and re.match(r"^[A-Z][a-z]", c) and not END.search(p['w'][k - 1][0]): capital_somewhere.add(c.lower())
    caps = set(); varies = set()
    for i, w in enumerate(words):
        c = core_of(w[2])
        if not c or c == '[ __ ]' or c.lower() in FUNC or c.lower() in known or c.lower() in low or c in ("I", "I'm", "I've", "I'll", "I'd"): continue
        start = i == 0 or w[5] or words[i - 1][3] != w[3] or END.search(words[i - 1][2])
        if re.match(r"^[A-Z]", c) and not start: caps.add(c)
        elif c[:1].islower() and c.lower() in capital_somewhere: varies.add(c)
    look = sorted(caps); varies = sorted(varies)
    C.save(f'{out}/{name}.captions.json', {'timeline': name, 'version': f'{ch} v{v["v"]}', 'cues': len(cs), 'words': len(words), 'look_at_names': look, 'case_varies': varies, 'fixes': fixes, 'fixed': sorted(set(log['fixed'])),
                                           'masked_swears': log['masked'], 'function_words_lowered': log['lowered'], 'backchannels_left_out': dropped, 'shortest_cue_s': round(min((b - a) for a, b, _ in cs) / fps, 2) if cs else None, 'made_at': C.now()})
    return f'{out}/{name}.srt', len(cs), look

if __name__ == '__main__':
    a = sys.argv[1:]
    if len(a) < 3: C.fail(__doc__)
    W = os.path.abspath(a[0]); path, n, look = build(W, a[1], a[2]); j = C.load(path[:-4] + '.captions.json')
    print(f'{path}: {n} cues, shortest {j["shortest_cue_s"]} s, {j["backchannels_left_out"]} back-channels left out, {j["masked_swears"]} swear(s) masked')
    print(f'  capitalised words to check (names Whisper may mishear): {look}\n  lower-case here, capitalised elsewhere in the episode: {j["case_varies"]}')
