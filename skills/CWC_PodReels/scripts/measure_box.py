"""Find the white hook box in a rendered 1080x1920 frame: prints 'left right top bottom' in px, or 'none'.
usage: python3 measure_box.py <frame.jpg> <approx_center_y_px>"""
import sys, numpy as np
from PIL import Image
im=np.asarray(Image.open(sys.argv[1]).convert('RGB')).astype(int); cy=int(float(sys.argv[2]))
y0,y1=max(0,cy-260),min(im.shape[0],cy+260)
band=im[y0:y1]
white=(band.min(axis=2)>=246)
rows=[]
for r in range(white.shape[0]):
    xs=np.where(white[r])[0]
    if len(xs)<200: continue
    # longest contiguous run
    runs=np.split(xs,np.where(np.diff(xs)>1)[0]+1); run=max(runs,key=len)
    if len(run)>=200: rows.append((r,run[0],run[-1]))
if not rows: print('none'); sys.exit()
left=min(r[1] for r in rows); right=max(r[2] for r in rows); top=rows[0][0]+y0; bottom=rows[-1][0]+y0
print(left,right,top,bottom)
