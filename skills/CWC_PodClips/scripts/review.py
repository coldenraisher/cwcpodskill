"""review.py render <WORK> <id> [--channel cwc|tcl]     preview render (720p) of the newest version, then `check`
   review.py check  <WORK> <id> [--channel cwc|tcl]     the checks on an existing preview file
   review.py ack    <WORK> <id> "<what you saw>" [--channel cwc|tcl]     after LOOKING at the contact sheet (bound to the sheet's hash; an
                                                       attestation, like CWC_PodCut's ack.py - tg_edit.py send needs it)
What must be true before a preview goes to Telegram (gates, exit 1):
  - the render has exactly the plan's frame count, one video and one audio stream;
  - the sound: integrated loudness and true peak, whole clip and per section (cold open, stinger, body, ending) are
    measured and stored; a true peak over 0 dBFS is REPORTED loudly (Colden's A1 strip decides the mix; the loudness
    finish in master.py brings the master to -14 LUFS / -1 dBTP);
  - a contact sheet is made of every moment that can go wrong: the first frame, each side of every splice in the cold
    open, the stinger, one frame of EVERY camera (another episode's file under a shot shows here), the name tag, the middle of every b-roll, the first trims, the last second, the glitch
    transition, the end screen. LOOK AT IT before sending (edit/<id>/preview/<name> sheet.jpg) - a check no script does.
Then: tg_edit.py send. The preview path and the numbers are stored on the version in edit/<id>/versions.json."""
import os, re, sys, json, subprocess
import common as C, master as M
HERE = os.path.dirname(os.path.abspath(__file__))
def duck(f, rec, frames, fps):
    """inside a censor window vs the half second on each side: how far the VOICE (150-4000 Hz without the beep's 850-1150
    Hz) drops, and how far the beep's band rises over the voice left inside"""
    try:
        import numpy as np
        pad = int(0.5 * fps); t0 = max(0, rec - pad) / fps; n = frames + 2 * pad
        x = np.frombuffer(subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{t0:.4f}', '-t', f'{n / fps:.4f}', '-i', f, '-vn', '-ac', '1', '-ar', '48000', '-f', 'f32le', '-'], capture_output=True).stdout, np.float32)
        fr = int(48000 / fps); voice = []; tone = []
        for i in range(0, len(x) - fr + 1, fr):
            sp = np.abs(np.fft.rfft(x[i:i + fr] * np.hanning(fr))) ** 2; fq = np.fft.rfftfreq(fr, 1 / 48000)
            voice.append(10 * np.log10(sp[(fq > 150) & (fq < 4000) & ((fq < 850) | (fq > 1150))].sum() / fr + 1e-12)); tone.append(10 * np.log10(sp[(fq >= 850) & (fq <= 1150)].sum() / fr + 1e-12))
        k0 = min(rec, pad); inside = voice[k0:k0 + frames]; outside = voice[:max(0, k0 - 1)] + voice[k0 + frames + 1:]
        loud = sorted(outside)[len(outside) // 2:]                  # the louder half around it = speech, not the pauses
        return {'voice_drop_db': round(float(np.mean(loud) - np.max(inside[1:] or inside)), 1), 'tone_over_db': round(float(np.median(tone[k0:k0 + frames]) - np.median(inside)), 1)}
    except Exception as e: return {'voice_drop_db': None, 'tone_over_db': None, 'error': str(e)[:80]}
def check(W, tid, ch):
    v = C.newest_built(W, tid, ch); P = C.load(v['plan']); f = v.get('preview')
    if not f or not os.path.exists(f): C.fail('no preview file - review.py render first')
    pr = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'stream=codec_type,nb_frames:format=duration', '-of', 'json', f], capture_output=True, text=True).stdout)
    vst = [s for s in pr['streams'] if s['codec_type'] == 'video']; ast = [s for s in pr['streams'] if s['codec_type'] == 'audio']; probs = []
    if len(vst) != 1 or len(ast) != 1: probs.append(f'streams: {len(vst)} video, {len(ast)} audio')
    if vst and int(vst[0].get('nb_frames') or 0) != P['frames']: probs.append(f'the render has {vst[0].get("nb_frames")} frames, the plan {P["frames"]}')
    fps = P['fps']; cut = {'shots': P.get('shots') or [], 'anchors': P.get('anchors')}; A = P.get('anchors')      # the cut this version was BUILT from, frozen in its plan
    I, TP = M.measure(f); sound = {'integrated_lufs': I, 'true_peak_dbfs': TP, 'sections': {}}
    if A:
        for name, a, b in (('cold open', 0, A['hook_end']), ('stinger', A['hook_end'], A['body_start'] + int(4 * fps)), ('body', A['body_start'] + int(4 * fps), A['C'] - int(11 * fps)), ('ending', A['C'], A['end'])):
            r = subprocess.run(['ffmpeg', '-nostats', '-ss', f'{a / fps:.2f}', '-to', f'{b / fps:.2f}', '-i', f, '-vn', '-af', 'ebur128=peak=true', '-f', 'null', '-'], capture_output=True, text=True).stderr
            s = r[r.rfind('Summary'):]; i = re.search(r'I:\s+(-?[\d.]+) LUFS', s); p = re.search(r'Peak:\s+(-?[\d.]+) dBFS', s)
            if i and p: sound['sections'][name] = [float(i.group(1)), float(p.group(1))]
    for c in P.get('censor') or []:                       # THE CENSOR, measured (the API cannot be trusted to have ducked): under the beep the voice is gone and the tone is there
        d = duck(f, c['rec'], c['frames'], fps); sound.setdefault('censor', []).append(dict(d, word=c['word'], at=C.clock(c['rec'] / fps)))
        if d['voice_drop_db'] is None or d['voice_drop_db'] < 12: probs.append(f'censor "{c["word"]}" at {C.clock(c["rec"] / fps)}: the voice under the beep is only {d["voice_drop_db"]} dB down (>= 12 wanted) - the program was NOT ducked')
        if d['tone_over_db'] is None or d['tone_over_db'] < 6: probs.append(f'censor "{c["word"]}" at {C.clock(c["rec"] / fps)}: no beep tone heard over the window ({d["tone_over_db"]} dB)')
    times = [0.4]
    shots = (cut or {}).get('shots', [])
    for s in shots:
        if s.get('splice') and (s['kind'] == 'hook' or len(times) < 14): times += [max(0, s['rec'] / fps - 0.2), s['rec'] / fps + 0.3]
    for cam in sorted({s['cam'] for s in shots}):                     # one frame of EVERY camera: wrong media (another episode's file) shows here
        long = max((s for s in shots if s['cam'] == cam and s['kind'] == 'body'), key=lambda s: s['b'] - s['a'], default=None)
        if long: times.append((long['rec'] + (long['b'] - long['a']) // 2) / fps)
    times += [(P['stinger']['rec'] + 60) / fps] + [(t['rec'] + 60) / fps for t in P['tags']] + [(b['rec'] + b['frames'] // 2) / fps for b in P.get('broll', [])]
    times += [(P['outro']['C'] - 30) / fps, (P['outro']['C'] - 1) / fps, (P['outro']['C'] + 90) / fps]
    times = sorted(set(round(t, 2) for t in times))[:36]; d = os.path.splitext(f)[0] + ' frames'; os.makedirs(d, exist_ok=True)
    for n, t in enumerate(times): subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{t}', '-i', f, '-frames:v', '1', '-vf', 'scale=480:-1', f'{d}/{n + 1:02d}.jpg'])
    cols = 6; rows = (len(times) + cols - 1) // cols; sheet = os.path.splitext(f)[0] + ' sheet.jpg'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-framerate', '1', '-start_number', '1', '-i', f'{d}/%02d.jpg', '-vf', f'tile={cols}x{rows}:padding=4', '-frames:v', '1', sheet])
    v = C.set_version(W, tid, v['channel'], v['v'], preview_check={'frames': int(vst[0].get('nb_frames') or 0) if vst else None, 'sound': sound, 'sheet': sheet, 'sheet_times': times, 'problems': probs, 'at': C.now()})
    print(f'{v["timeline"]}: {v["preview_check"]["frames"]} frames (plan {P["frames"]}); {I} LUFS, true peak {TP} dBFS; sections {sound["sections"]}')
    if TP > 0: print(f'  LOUD PEAKS: true peak {TP} dBFS is over 0 - tell Colden (his A1 strip); master.py limits the master to -1 dBTP')
    print(f'  LOOK AT: {sheet}\n  frames at (s): {times}')
    for p in probs: print('  PROBLEM:', p)
    return 1 if probs else 0
if __name__ == '__main__':
    a = [x for x in sys.argv[1:] if not x.startswith('--')]; ch = sys.argv[sys.argv.index('--channel') + 1] if '--channel' in sys.argv else None
    if ch in a: a.remove(ch)
    if len(a) < 3: C.fail(__doc__)
    cmd, W, tid = a[0], os.path.abspath(a[1]), a[2]
    if cmd == 'render':
        v = C.newest_built(W, tid, ch); ep = C.episode(W); out = f'{W}/edit/{tid}/preview'; cn = f'{tid} {v["channel"]} v{v["v"]} preview'
        r = subprocess.run([sys.executable, f'{HERE}/rs.py', '2400', f'{HERE}/r_render.py', f'PROJECT={json.dumps(ep["project"])}', f'NAME={json.dumps(v["timeline"])}', f'OUT={json.dumps(out)}', f'CN={json.dumps(cn)}', 'W=1280', 'H=720', 'LIMIT=2300'], capture_output=True, text=True).stdout.strip().splitlines()
        res = json.loads(r[-1]) if r else {'error': 'no answer'}
        if res.get('error') or not res.get('made'): C.fail(f'render: {res}')
        C.set_version(W, tid, v['channel'], v['v'], preview=res['made']); sys.exit(check(W, tid, v['channel']))
    elif cmd == 'check': sys.exit(check(W, tid, ch))
    elif cmd == 'ack':
        v = C.newest_built(W, tid, ch); pc = v.get('preview_check') or {}
        if not pc.get('sheet') or not os.path.exists(pc['sheet']): C.fail('no contact sheet - review.py check first')
        if len(a) < 4 or len(a[3]) < 30: C.fail('say what you saw on the sheet (every camera, each b-roll, the name tag, the ending) - at least a sentence')
        C.set_version(W, tid, v['channel'], v['v'], looked={'sheet_sha': C.sha_file(pc['sheet']), 'saw': a[3], 'at': C.now()}); print('recorded')
    else: C.fail(__doc__)
