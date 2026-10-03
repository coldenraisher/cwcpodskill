"""Read a plan next to the transcript (tuning aid). usage: show_plan.py <CACHE> <from s> <to s> [plan.json]   (program seconds)"""
import sys, json, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
cache, a, b = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]); P = json.load(open(sys.argv[4] if len(sys.argv) > 4 else f'{cache}/plan.json'))
m = C.manifest(cache); W = json.load(open(f'{cache}/words.json')); nm = {c['id']: c['name'] for c in m['cameras']}
allw = sorted(({**w, 'sid': s} for s in W for w in W[s]), key=lambda w: w['start'])
prev_end = None
for s in P['segments']:
    if s['srcEnd'] < a or s['srcStart'] > b: continue
    if prev_end is not None and s['srcStart'] - prev_end > 0.01: print(f'        --- trim {s["srcStart"] - prev_end:.2f}s ---')
    prev_end = s['srcEnd']
    said = {}
    for w in allw:
        if s['srcStart'] <= (w['start'] + w['end']) / 2 < s['srcEnd']: said.setdefault(nm[w['sid']], []).append(w['text'].strip())
    txt = ' | '.join(f"{k}: {' '.join(v)[:90]}" for k, v in said.items())
    print(f"{C.hms(s['srcStart']):>9} {s['frames'] / P['fps']:5.1f}s  {s['name']:7s} {s['reason']:14s} {txt}")
