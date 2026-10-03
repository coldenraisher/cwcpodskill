"""eyes.py (library + `eyes.py <camera file> <frame> [<frame> ...]` to test): where the eyes are in a camera frame, so a
punch-in can pivot on them (Colden 2026-10-01, ruling 23: "1.25 punch always focused on the eyes").
YuNet (assets/yunet.onnx, OpenCV) gives both eye landmarks; the pivot is their midpoint, the median over the samples.
No face in any sample -> None: the builder then REFUSES the punch (a centre zoom is never a fallback)."""
import os, sys, subprocess, statistics
import common as C
_det = {}
def _detector(w, h):
    import cv2
    if (w, h) not in _det: _det[(w, h)] = cv2.FaceDetectorYN.create(f'{C.SK}/assets/yunet.onnx', '', (w, h), 0.6, 0.3, 50)
    return _det[(w, h)]
def frame(path, n, fps, out):
    r = subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{n / fps:.3f}', '-i', path, '-frames:v', '1', '-q:v', '3', out], capture_output=True)
    return os.path.exists(out)
def eye_point(path, frames, fps, cache_dir):
    """median eye midpoint (x, y) in SOURCE pixels over the sampled frames + the source size, or None"""
    import cv2
    os.makedirs(cache_dir, exist_ok=True); pts = []; size = None
    for n in frames:
        f = f'{cache_dir}/{os.path.basename(path)}_{int(n)}.jpg'
        if not os.path.exists(f) and not frame(path, n, fps, f): continue
        img = cv2.imread(f)
        if img is None: continue
        h, w = img.shape[:2]; size = (w, h); _, faces = _detector(w, h).detect(img)
        if faces is None or not len(faces): continue
        fc = max(faces, key=lambda r: r[2] * r[3]); pts.append(((fc[4] + fc[6]) / 2, (fc[5] + fc[7]) / 2, fc[3]))
    if not pts: return None
    return {'x': statistics.median(p[0] for p in pts), 'y': statistics.median(p[1] for p in pts), 'face_h': statistics.median(p[2] for p in pts), 'w': size[0], 'h': size[1], 'samples': len(pts)}
def punch_props(eye, Z, FW, FH):
    """Inspector values that keep the eye point where it was at zoom Z (timeline pixels; Tilt + = image up - measured in
    edit-clips on 2026-09-13/14 and checked again on the pilot's stills)"""
    ex, ey = eye['x'] * FW / eye['w'], eye['y'] * FH / eye['h']
    return {'ZoomX': Z, 'ZoomY': Z, 'Pan': round(-(Z - 1) * (ex - FW / 2), 1), 'Tilt': round((Z - 1) * (ey - FH / 2), 1)}
if __name__ == '__main__':
    print(eye_point(sys.argv[1], [int(x) for x in sys.argv[2:]], 30.0, '/tmp/eyes_test'))
