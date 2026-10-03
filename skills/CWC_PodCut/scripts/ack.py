"""Record that the review sheets of THIS plan were looked at: lock.py refuses a cut whose sheets were not, auto_lock
included, and with auto_lock on build.py will not start without it. usage: ack.py <CACHE> "<what you saw - at least a sentence>"
The note is kept with the hashes of layout.jpg and reactions_in_cut.jpg: a re-made sheet needs a new look.
This is the one gate that is an attestation, not a measurement - it exists so the look cannot be skipped silently."""
import os, sys, json, time, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
cache, note = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else ''); m = C.manifest(cache)
assert len(note.split()) >= 6, 'say what you saw on the sheets (a sentence, not "ok")'
rev = f"{C.WORK}/review/{m['show']}/{m['ep_key']}"; h = {}
for f in ('layout.jpg', 'reactions_in_cut.jpg'):
    p = f'{rev}/{f}'
    if f == 'reactions_in_cut.jpg' and not os.path.exists(p) and not any(s['reason'].startswith('reaction') for s in json.load(open(f'{cache}/plan.json'))['segments']): h[f] = None; continue
    assert os.path.exists(p), f'{p} does not exist - run prep.py'
    h[f] = hashlib.sha1(open(p, 'rb').read()).hexdigest()
C.save(f'{cache}/ack.json', {'sheets': h, 'note': note, 'at': time.strftime('%Y-%m-%d %H:%M')}); print('recorded:', h)
