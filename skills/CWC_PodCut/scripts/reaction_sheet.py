"""The reactions that are IN THE CUT, three frames each (start / middle / end) - the sheet to LOOK at.
usage: reaction_sheet.py <CACHE> <out.jpg> [--plan plan.json]
(reactions.py's own sheet shows what passed its gate; the planner then picks, spaces and drops some - audit 2026-10-01:
the sheet looked at must be the reactions the cut really uses.)"""
import os, sys, json, subprocess, io
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
from PIL import Image, ImageDraw, ImageFont
cache, out = sys.argv[1], sys.argv[2]; m = C.manifest(cache); P = json.load(open(sys.argv[sys.argv.index('--plan') + 1] if '--plan' in sys.argv else f'{cache}/plan.json'))
cam = {c['id']: c for c in m['cameras']}; shots = [s for s in P['segments'] if s['reason'].startswith('reaction')]
if not shots: print('no reaction shots in the plan'); sys.exit(0)
w, h, th, cols = 240, 135, 20, 2
sh = Image.new('RGB', (cols * (3 * w + 6), ((len(shots) + cols - 1) // cols) * (h + th)), (18, 18, 18)); f = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 13); dr = ImageDraw.Draw(sh)
for i, s in enumerate(shots):
    x0 = (i % cols) * (3 * w + 6); y0 = (i // cols) * (h + th)
    for k, fr_ in enumerate((0.1, 0.5, 0.9)):
        t = s['srcStart'] + (s['srcEnd'] - s['srcStart']) * fr_
        b = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f"{C.src_time(cam[s['camera']], t):.3f}", '-i', cam[s['camera']]['path'], '-frames:v', '1', '-vf', f'scale={w}:{h}', '-f', 'image2pipe', '-vcodec', 'mjpeg', '-'], capture_output=True).stdout
        if b: sh.paste(Image.open(io.BytesIO(b)).convert('RGB'), (x0 + k * w, y0 + th))
    dr.text((x0 + 4, y0 + 3), f"cut {C.hms(s['outStart'])}  (program {C.hms(s['srcStart'])})  {s['frames'] / P['fps']:.1f}s  {s['name']}", fill=(255, 255, 255), font=f)
sh.save(out, quality=82); print(f'{len(shots)} reaction shots -> {out}')
