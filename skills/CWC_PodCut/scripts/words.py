"""Word timings per speaker stem (faster-whisper small.en, one process per speaker) - BASE seconds.
usage: words.py <CACHE> [--one speaker_2]   -> <CACHE>/words.json  {speaker_id: [{start, end, text, p}]}
The prompt keeps fillers in the transcript ("Um, uh, ...") and carries the show glossary (names Whisper misspells:
Colden comes out "Colton" / "Kolden" - every scan for his name must match those too).
Gate: every speaker's last word is within the program, and the words cover that speaker's VAD speech (>= 60 %): a
transcript that stops early (more than 20 s of that speaker's speech after its last word) stops the run and leaves
no words.json behind."""
import os, sys, json, time, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

cache = sys.argv[1]; m = C.manifest(cache); sh = C.show(m['show'])
if '--one' in sys.argv:
    sid = sys.argv[sys.argv.index('--one') + 1]
    from faster_whisper import WhisperModel
    model = WhisperModel('small.en', device='cpu', compute_type='int8', cpu_threads=4); t0 = time.time()
    prompt = 'Um, uh, hmm, so, um, you know, uh, like, I mean. ' + ', '.join(sh.get('glossary', [])) + '.'
    segs, _ = model.transcribe(f'{cache}/{sid}.wav', word_timestamps=True, vad_filter=True, condition_on_previous_text=False, initial_prompt=prompt)
    out = [{'start': round(w.start, 2), 'end': round(w.end, 2), 'text': w.word, 'p': round(w.probability, 2)} for s in segs for w in (s.words or [])]
    C.save(f'{cache}/words_{sid}.json', out); print(sid, len(out), 'words', f'{time.time() - t0:.0f}s'); sys.exit(0)
todo = [c for c in C.speakers(m) if not (os.path.exists(f"{cache}/words_{c['id']}.json") and os.path.getmtime(f"{cache}/words_{c['id']}.json") > os.path.getmtime(f"{cache}/{c['id']}.wav"))]
procs = [subprocess.Popen([sys.executable, os.path.abspath(__file__), cache, '--one', c['id']], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True) for c in todo]
for p in procs:
    print(p.communicate()[0].strip()); assert p.returncode == 0, 'whisper failed'
W = {c['id']: json.load(open(f"{cache}/words_{c['id']}.json")) for c in C.speakers(m)}
vad = json.load(open(f'{cache}/vad.json'))['speakers']; bad = []
for c in C.speakers(m):
    w = W[c['id']]; sp = vad[c['id']]['segments']; speech = sum(s['end'] - s['start'] for s in sp)
    if not w: bad.append(f"{c['name']}: no words"); continue
    cov = sum(min(s['end'], x['end'] + 0.3) - max(s['start'], x['start'] - 0.3) > 0 for s in sp for x in [next((x for x in w if x['end'] > s['start'] - 0.3 and x['start'] < s['end'] + 0.3), None)] if x) / max(1, len(sp))
    print(f"  {c['name']:8s} {len(w)} words, last at {C.hms(w[-1]['end'])}, {cov * 100:.0f} % of {len(sp)} speech runs have words")
    late = sp[-1]['end'] - w[-1]['end'] if sp else 0.0
    if cov < 0.6 or w[-1]['end'] > m['duration'] + 1: bad.append(f"{c['name']}: words cover {cov * 100:.0f} % of speech runs / last word {w[-1]['end']:.0f}s")
    elif late > 120 and sum(s_['end'] - s_['start'] for s_ in sp if s_['start'] > w[-1]['end']) > 20: bad.append(f"{c['name']}: the transcript stops at {C.hms(w[-1]['end'])} but they keep talking for {late:.0f} s more - Whisper gave up early")
if bad:      # a transcript that failed its gate is NOT left where the next step would pick it up
    if os.path.exists(f'{cache}/words.json'): os.replace(f'{cache}/words.json', f'{cache}/words.rejected.json')
    C.die('; '.join(bad))
C.save(f'{cache}/words.json', W)
