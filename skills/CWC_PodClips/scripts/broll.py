"""broll.py prep <capture.png> <out 16x9.png> [--box x0,y0,x1,y1]   crop a capture to the part that matters (fractions of
                                              the picture) and pad it to 16:9 with the page's own background, >= 8 % margin
   broll.py render <src image> <out dir> <seconds> <move> [--res 3840x2160]   -> prints the clip path (build.py calls this)
A b-roll still as a full-frame 16:9 clip with an eased move, made with ffmpeg (no Fusion: Resolve 21.1 aborts on Fusion
handles held by a script - 2026-09-23; this is the AMIRA reels recipe at 16:9). Moves: push (1.00 -> 1.06), pull,
pan_left, pan_right (a 1.08 cover), fit_blur (an image that is not 16:9: whole picture at 88 % height over a blurred,
darkened cover of itself, slow push). Cosine ease in and out; the move is computed at 2x and scaled down so it does
not step. H.264 CRF 14, 30 fps, no audio. The file name carries a fingerprint of source + move + length: a re-render
is a NEW file, never an overwrite of a clip Resolve has linked."""
import os, sys, hashlib, subprocess
from PIL import Image
def render(src, out_dir, dur, move, res=(3840, 2160), fps=30):
    W, H = res; w, h = Image.open(src).size; n = max(1, int(round(dur * fps)))
    fp = hashlib.sha1(open(src, 'rb').read() + f'{move}{dur}{W}x{H}'.encode()).hexdigest()[:8]
    out = os.path.join(out_dir, f'{os.path.splitext(os.path.basename(src))[0]} {move} {dur:g}s {fp}.mp4'); os.makedirs(out_dir, exist_ok=True)
    if os.path.exists(out): return out
    E = f"(1-cos(PI*on/{n}))/2"
    if move == 'fit_blur' or abs(w / h - W / H) > 0.12 and move in ('push', 'pull'):
        s0 = min(0.88 * H / h, 0.94 * W / w); fw, fh = int(w * s0) // 2 * 2, int(h * s0) // 2 * 2
        fc = (f"[0:v]split=2[a][b];[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},gblur=sigma=50,eq=brightness=-0.12[bg];"
              f"[b]scale={fw * 2}:{fh * 2},zoompan=z='1+0.05*{E}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={fw}x{fh}:fps={fps}[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2")
        cmd = ['ffmpeg', '-y', '-v', 'error', '-loop', '1', '-framerate', str(fps), '-i', src, '-filter_complex', fc]
    else:
        k = 1.08 if move.startswith('pan') else 1.0; s = max(W / w, H / h) * k; W2, H2 = int(w * s * 2) // 2 * 2, int(h * s * 2) // 2 * 2
        if move in ('push', 'pull'):
            z = f"1+0.06*{E}" if move == 'push' else f"1.06-0.06*{E}"
            vf = f"scale={W2}:{H2},crop={2 * W}:{2 * H},zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={W}x{H}:fps={fps}"
        else:
            T = f"(1-cos(PI*t/{dur}))/2"; x = f"{W2 - 2 * W}*(1-{T})" if move == 'pan_left' else f"{W2 - 2 * W}*{T}"
            vf = f"scale={W2}:{H2},crop={2 * W}:{2 * H}:'{x}':{(H2 - 2 * H) // 2},scale={W}:{H}"
        cmd = ['ffmpeg', '-y', '-v', 'error', '-loop', '1', '-framerate', str(fps), '-i', src, '-vf', vf]
    subprocess.run(cmd + ['-t', f'{dur}', '-r', str(fps), '-c:v', 'libx264', '-preset', 'medium', '-crf', '14', '-pix_fmt', 'yuv420p', '-an', out], check=True)
    return out
def prep(src, out, box=None, margin=0.08, res=(3840, 2160)):
    """crop a capture to the part that matters (box = x0, y0, x1, y1 as fractions) and pad it to 16:9 with the page's own
    background colour, >= 8 % margin on every side, so the eased push never clips text (edit-clips broll.md, 16:9 clips)"""
    im = Image.open(src).convert('RGB'); w, h = im.size
    if box: im = im.crop((int(box[0] * w), int(box[1] * h), int(box[2] * w), int(box[3] * h)))
    bg = im.getpixel((2, 2)); W, H = res; s = min(W * (1 - 2 * margin) / im.width, H * (1 - 2 * margin) / im.height)
    im2 = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS); canvas = Image.new('RGB', (W, H), bg)
    canvas.paste(im2, ((W - im2.width) // 2, (H - im2.height) // 2)); canvas.save(out); return out
if __name__ == '__main__':
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    if len(a) >= 3 and a[0] == 'prep':                     # broll.py prep <capture.png> <out 16x9.png> [--box x0,y0,x1,y1  (fractions of the capture)]
        box = tuple(float(x) for x in sys.argv[sys.argv.index('--box') + 1].split(',')) if '--box' in sys.argv else None
        prep(a[1], a[2], box); print(a[2]); sys.exit(0)
    if len(a) < 5 or a[0] != 'render': print(__doc__); sys.exit(1)
    res = tuple(int(x) for x in sys.argv[sys.argv.index('--res') + 1].split('x')) if '--res' in sys.argv else (3840, 2160)
    print(render(a[1], a[2], float(a[3]), a[4], res))
