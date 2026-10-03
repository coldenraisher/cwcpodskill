"""Colden.braw -> COLDEN.mp4 with Colden's LUT (2026-10-01: "If the file is Colden.BRAW, you will need to convert it
with my LUT"). Blackmagic RAW cannot be read by ffmpeg, so the conversion is a Resolve render:
  a one-clip timeline 'zz BRAW convert <name>' in bin '<episode>/BRAW convert', the LUT on node 1 of the clip, rendered
  with the preset named in --preset (default 'H.265 Master') at the clip's own size and rate into the Angles folder.
usage: braw_convert.py "<file.braw>" --project "TCL Show Edits" [--preset "H.265 Master"] [--lut <cube>]
Gates: the LUT file exists; SetLUT returned True; the rendered file exists, probes, and is within 0.5 s of the BRAW's
length. The .braw is then moved to '<folder>/_braw/' so intake sees ONE file for Colden (moved, never deleted).
STATUS 2026-10-01: written from the API docs, NOT yet run on a real BRAW - the first one is run with Colden present."""
import os, sys, json, time, argparse, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
LUT = '/Library/Application Support/Blackmagic Design/DaVinci Resolve/LUT/LUTs/Custom/BMPCC4k Studio_1.2001_09141038_C001.cube'
ap = argparse.ArgumentParser(); ap.add_argument('braw'); ap.add_argument('--project', required=True); ap.add_argument('--preset', default='H.265 Master'); ap.add_argument('--lut', default=LUT); A = ap.parse_args()
assert os.path.exists(A.braw), f'no file {A.braw}'; assert os.path.exists(A.lut), f'LUT not found: {A.lut}'
d = os.path.dirname(A.braw); name = os.path.splitext(os.path.basename(A.braw))[0].upper(); out = f'{d}/{name}.mp4'
assert not os.path.exists(out), f'{out} already exists - not overwriting'
print(C.rs('open_project.py', 180, PROJECT=A.project))
r = C.rs('r_braw.py', 300, PROJECT=A.project, BRAW=A.braw, LUT=A.lut, PRESET=A.preset, TARGET=d, NAME=name, STEP='start'); print(r)
while True:
    time.sleep(20); s = C.rs('r_braw.py', 60, PROJECT=A.project, STEP='wait', JOB=r['job'])
    print('  render', s.get('status'), s.get('pct'))
    if not s['rendering']: break
made = next((f for f in os.listdir(d) if f.startswith(name + '.') and f.lower().endswith(('.mp4', '.mov')) and not f.lower().endswith('.braw')), None)
assert made, f'the render left no {name}.mp4/.mov in {d}'
p = C.probe(f'{d}/{made}'); assert abs(p['duration'] - r['seconds']) < 0.5, f"rendered {p['duration']:.2f}s, the BRAW is {r['seconds']:.2f}s"
os.makedirs(f'{d}/_braw', exist_ok=True); shutil.move(A.braw, f'{d}/_braw/{os.path.basename(A.braw)}')
print(f"converted -> {d}/{made} ({p['width']}x{p['height']} {p['fps']:.3f} fps, {C.hms(p['duration'])}); the BRAW moved to {d}/_braw/")
