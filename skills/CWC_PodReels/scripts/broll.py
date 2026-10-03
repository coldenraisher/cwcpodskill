"""broll.py - b-roll for shorts: ALWAYS full frame (Colden 2026-09-23: "B roll needs to ALWAYS be full frame"), never a
still on a card, never letterboxed, nothing baked in Fusion (Resolve 21.1 crashes on held Fusion handles).
  render(src, out_dir, seconds, move, fps, focus=None) -> a 1080x1920 H.264 clip: the still cover-cropped to 9:16 and moved
      with an eased (smoothstep) zoom or pan, rendered frame by frame with sub-pixel sampling (no zoompan jitter). The file
      name carries a fingerprint of everything that made it: a re-render is a new file, never an overwrite of a clip
      Resolve has linked (AMIRA reels 2026-09-29: an overwritten clip played as Media Offline).
  focus = [fx, fy] (0..1 of the image) keeps the hero in frame; default the centre.
  python3 broll.py <image> <seconds> <move> [fx fy]   renders a test clip next to the image
GATES: the result is 1080x1920 at the asked frame count; an image that needs more than 2.6x upscaling to cover the
frame is refused (find a bigger source)."""
import os, sys, json, hashlib, subprocess
from PIL import Image, ImageOps
TW, TH = 1080, 1920
MOVES = ('zoom_in', 'zoom_out', 'pan_left', 'pan_right', 'pan_up', 'pan_down', 'static')

def render(src, out_dir, seconds, move, fps=30, focus=None):
    if move not in MOVES: raise SystemExit(f'move must be one of {MOVES}')
    raw = Image.open(src); rot = raw.getexif().get(0x0112, 1)
    im = ImageOps.exif_transpose(raw).convert('RGB'); iw, ih = im.size; base = max(TW / iw, TH / ih)   # stand a phone photo upright (EXIF orientation; 2026-10-02 an empty-cinema still rendered sideways)
    if base > 2.6: raise SystemExit(f'GATE: {os.path.basename(src)} is {iw}x{ih} - it would be upscaled {base:.1f}x to fill 1080x1920. Find a bigger source.')
    n = max(2, int(round(seconds * fps))); fx, fy = (focus or [0.5, 0.5])
    key = hashlib.sha1(open(src, 'rb').read() + json.dumps([n, move, fps, fx, fy] + ([f'upright{rot}'] if rot != 1 else [])).encode()).hexdigest()[:8]
    os.makedirs(out_dir, exist_ok=True); out = f'{out_dir}/{os.path.splitext(os.path.basename(src))[0]} {move} {key}.mp4'
    if os.path.exists(out): return out
    zoom = {'zoom_in': (1.0, 1.10), 'zoom_out': (1.10, 1.0)}.get(move, (1.08, 1.08))
    def box(s, cx, cy):
        w, h = TW / (base * s), TH / (base * s); cx = min(max(cx, w / 2), iw - w / 2); cy = min(max(cy, h / 2), ih - h / 2)
        return (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
    cx0, cy0 = fx * iw, fy * ih; w8, h8 = TW / (base * 1.08), TH / (base * 1.08)
    px = min(0.06 * iw, max(0.0, (iw - w8) / 2)); py = min(0.05 * ih, max(0.0, (ih - h8) / 2))
    path = {'pan_left': ((cx0 + px, cy0), (cx0 - px, cy0)), 'pan_right': ((cx0 - px, cy0), (cx0 + px, cy0)),
            'pan_up': ((cx0, cy0 + py), (cx0, cy0 - py)), 'pan_down': ((cx0, cy0 - py), (cx0, cy0 + py))}.get(move, ((cx0, cy0), (cx0, cy0)))
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{TW}x{TH}', '-r', str(fps), '-i', '-',
                          '-c:v', 'libx264', '-preset', 'slow', '-crf', '14', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', out], stdin=subprocess.PIPE)
    for i in range(n):
        t = i / (n - 1); e = t * t * (3 - 2 * t)
        s = zoom[0] + (zoom[1] - zoom[0]) * e; cx = path[0][0] + (path[1][0] - path[0][0]) * e; cy = path[0][1] + (path[1][1] - path[0][1]) * e
        p.stdin.write(im.transform((TW, TH), Image.EXTENT, box(s, cx, cy), Image.BICUBIC).tobytes())
    p.stdin.close(); p.wait()
    pr = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-count_frames', '-show_entries', 'stream=width,height,nb_read_frames', '-of', 'json', out], capture_output=True, text=True).stdout)['streams'][0]
    if (pr['width'], pr['height'], int(pr['nb_read_frames'])) != (TW, TH, n): os.remove(out); raise SystemExit(f'GATE: b-roll render is {pr}, wanted {TW}x{TH} x {n}')
    return out

if __name__ == '__main__':
    a = sys.argv[1:]
    if len(a) < 3: print(__doc__); sys.exit(1)
    print(render(a[0], os.path.dirname(os.path.abspath(a[0])), float(a[1]), a[2], 30, [float(a[3]), float(a[4])] if len(a) > 4 else None))
