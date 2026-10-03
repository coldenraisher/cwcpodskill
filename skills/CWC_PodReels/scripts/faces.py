"""faces.py <WORK>   ->  <WORK>/edit/faces.json      one fixed face position per camera for the whole episode
Edit-shorts' rule (Colden 2026-09-10): the camera stays in ONE position per person for the whole short - never a
reframe per cut (the face jumping at every cut makes jump cuts far more noticeable). So each speaker camera is sampled
where the locked PodCut shows that person on their own close-up (24 moments spread over the episode), YuNet finds the
largest face, and the MEDIAN centre / size / eye line is that person's crop anchor. Gates: every camera needs >= 8 face
hits (else exit 1 - LOOK at the frames in edit/faces/), the spread of the centre must stay inside a quarter of the frame."""
import os, sys, json, bisect, statistics, subprocess
import common as C

def pod(ep):
    """the locked PodCut's tracks by name -> list of [rec_a, rec_b, src_a, src_b, enabled, clip] (frames, timeline 0)"""
    d = C.load(f'{ep["snapshot"]}/pod_dump.json'); return {v['name']: v['items'] for k, v in d['tracks'].items()}, d

def src_frame(items, f):
    """source frame of the item covering cut frame f, or None"""
    st = [it[0] for it in items]; i = bisect.bisect_right(st, f) - 1
    if i < 0: return None
    a, b, s0 = items[i][0], items[i][1], items[i][2]
    return s0 + (f - a) if f < b else None

def detector(w, h):
    import cv2
    return cv2.FaceDetectorYN.create(f'{C.SK}/assets/yunet.onnx', '', (w, h), 0.6, 0.3, 50)

def run(W):
    ep = C.episode(W); plan = C.load(f'{ep["snapshot"]}/plan.json'); tracks, _ = pod(ep); out = {}; d = f'{W}/edit/faces'; os.makedirs(d, exist_ok=True)
    import cv2
    for p in ep['people']:
        segs = [s for s in plan['segments'] if s.get('name') == p['name'] and s['frames'] >= 45]
        if not segs: C.fail(f'{p["name"]} never has a close-up in the PodCut - cannot place their crop')
        pick = [segs[int(i * (len(segs) - 1) / 23)] for i in range(24)] if len(segs) > 24 else segs
        items = tracks.get(p['name']); assert items, f'no PodCut track named {p["name"]}'
        hits = []; det = None
        for s in pick:
            f = s['outFrame'] + s['frames'] // 2; sf = src_frame(items, f)
            if sf is None: continue
            img = f'{d}/{p["name"]}_{f}.jpg'
            if not os.path.exists(img): subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{sf / p["fps"]:.3f}', '-i', p['path'], '-frames:v', '1', '-q:v', '3', img])
            im = cv2.imread(img)
            if im is None: continue
            h, w = im.shape[:2]; det = det or detector(w, h); det.setInputSize((w, h)); _, fs = det.detect(im)
            if fs is None or not len(fs): continue
            fc = max(fs, key=lambda r: r[2] * r[3])
            hits.append({'f': f, 'cx': float(fc[0] + fc[2] / 2), 'cy': float(fc[1] + fc[3] / 2), 'fw': float(fc[2]), 'fh': float(fc[3]), 'eye_y': float((fc[5] + fc[7]) / 2), 'img': os.path.basename(img)})
        if len(hits) < 8: C.fail(f'{p["name"]}: only {len(hits)} face hits in {len(pick)} samples - LOOK at {d}')
        med = lambda k: statistics.median(x[k] for x in hits)
        spread = statistics.pstdev([x['cx'] for x in hits])
        if spread > p['w'] / 4: C.fail(f'{p["name"]}: the face moves a lot ({spread:.0f} px spread) - one fixed crop would lose it; LOOK at {d}')
        out[p['name']] = {'path': p['path'], 'w': p['w'], 'h': p['h'], 'cx': med('cx'), 'cy': med('cy'), 'fw': med('fw'), 'fh': med('fh'), 'eye_y': med('eye_y'), 'spread_px': round(spread, 1), 'hits': len(hits), 'samples': hits}
        print(f'{p["name"]:7} {p["w"]}x{p["h"]}  face centre ({med("cx"):.0f}, {med("cy"):.0f})  size {med("fw"):.0f}x{med("fh"):.0f}  spread {spread:.0f} px  {len(hits)}/{len(pick)} hits')
    C.save(f'{W}/edit/faces.json', {'made_at': C.now(), 'faces': out}); return out

if __name__ == '__main__':
    if len(sys.argv) < 2: C.fail(__doc__)
    run(os.path.abspath(sys.argv[1]))
