"""doctor.py [<show id>] [--resolve]      is everything this skill needs in place? Run it before a run on a new machine,
after an OS / Resolve update, or when a script fails for a reason that is not about the episode.
Offline by default (no Telegram message, no Resolve call). `--resolve` adds READ-ONLY Resolve checks (the project of the
show's last episode must be open): the template, the fixed assets by name, the render preset, the glitch transition.
NOT checkable from here (check by hand): the Higgsfield connector (AI thumbnails), the glitch transition pack GTR_02 in
Resolve, Colden's compressor / NR / EQ on the template's A1.
Prints OK / MISSING per item with the fix. Exit 0 = all there; 2 = something is missing (ask / install - never work
around a missing piece)."""
import os, sys, json, glob, shutil, subprocess, importlib
import common as C
HERE = os.path.dirname(os.path.abspath(__file__)); bad = []
def ok(name, cond, fix=''):
    print(('  OK       ' if cond else '  MISSING  ') + name + ('' if cond else f'  ->  {fix}'))
    if not cond: bad.append(name)
    return cond

def main(show_id, resolve):
    print('python + packages')
    ok(f'python >= 3.9 ({sys.version.split()[0]})', sys.version_info >= (3, 9), 'the scripts use 3.9 syntax')
    for mod, pip, why in (('numpy', 'numpy', 'audio checks: trims, censor, master picture'), ('cv2', 'opencv-python', 'eyes.py (punch-in pivot)'), ('PIL', 'Pillow', 'b-roll, thumbnails'),
                          ('googleapiclient', 'google-api-python-client', 'channel data'), ('google.oauth2', 'google-auth', 'channel data'), ('playwright', 'playwright  (then: python3 -m playwright install chromium)', 'capture.py (b-roll pages)')):
        try: importlib.import_module(mod); good = True
        except Exception: good = False
        ok(f'{mod} ({why})', good, f'pip3 install {pip}')
    try:
        import cv2; ok('opencv FaceDetectorYN + assets/yunet.onnx', hasattr(cv2, 'FaceDetectorYN') and os.path.exists(f'{C.SK}/assets/yunet.onnx'), 'opencv-python >= 4.8; the model file ships with the skill')
    except Exception: pass
    print('programs')
    for exe, why in (('ffmpeg', 'every render check, captions, loudness'), ('ffprobe', 'same'), ('textutil', 'show notes (.docx)'), ('pdftotext', 'show notes (.pdf): brew install poppler')):
        ok(f'{exe} ({why})', bool(shutil.which(exe)), f'install {exe}')
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw: ok('playwright chromium (capture.py)', os.path.exists(pw.chromium.executable_path), 'python3 -m playwright install chromium')
    except Exception: pass
    ok('Google Chrome (hook overlay render; needs the internet for the Sora font)', os.path.exists('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'), 'install Chrome')
    for t in ('face', 'facequality'):
        p = f'{C.SK}/tools/{t}'; ok(f'tools/{t} (Apple Vision / Core Image)', os.path.exists(p) and os.access(p, os.X_OK), f'make -C {C.SK}/tools   (needs swiftc: xcode-select --install)')
    if os.path.exists(f'{C.SK}/tools/face'):
        r = subprocess.run([f'{C.SK}/tools/face', '/dev/null'], capture_output=True, text=True); ok('tools/face runs', r.returncode == 0, f'rebuild: make -C {C.SK}/tools')
    print('accounts + config')
    ok('TG_BOT_TOKEN (~/.zshrc or the environment) - the @VideoEditReview_bot token', bool(os.environ.get('TG_BOT_TOKEN')) or (os.path.exists(os.path.expanduser('~/.zshrc')) and any(l.startswith('export TG_BOT_TOKEN=') for l in open(os.path.expanduser('~/.zshrc')))), 'export TG_BOT_TOKEN=... in ~/.zshrc')
    ok('Telegram chat pairing', any(os.path.exists(os.path.expanduser(p)) for p in ('~/.config/cwc/telegram.json', '~/.config/edit-shorts/telegram.json')), '~/.config/cwc/telegram.json {"chat_id": ...}')
    ok('the Telegram listener is running', C.listener_alive(), 'tg_listen.py start   (cards cannot be sent without it)')
    for ch in ('cwc', 'tcl'): ok(f'YouTube OAuth token {ch}', os.path.exists(f'{C.YT_CFG}/{ch}.json'), 'made by edit-clips (yt_upload.py auth) - never an interactive sign-in from this skill; ask Colden')
    scr = next((p for p in C.SCRAPE if os.path.exists(p)), None); ok('the Monday Studio scrape file (channel_metrics.json)', bool(scr), 'see references/weekly_scrape.md (check.py asks for a waiver when it is stale)')
    ok('the daily trend scan folder', os.path.isdir(C.TREND), f'{C.TREND} (evidence.py trends reads final.json / candidates.json)')
    print('files + mounts')
    E = json.load(open(f'{C.SK}/references/edit.json')); ok(f'the censor beep ({os.path.basename(E["beep"]["path"])})', os.path.exists(E['beep']['path']), f'{E["beep"]["path"]} - the Power Bin beep (ruling 35); ask Colden')
    S = C.load(f'{C.SK}/shows/{show_id}.json')
    if not ok(f'show file shows/{show_id}.json', bool(S), 'a new show needs its file (channels, hosts, packaging) - ask Colden'): return
    ok(f'{S["name"]}: nothing left to ask before a first run', not S.get('first_run_ask'), f'answer with Colden: {S.get("first_run_ask")}')
    ok(f'{S["name"]}: packaging block', bool(S.get('packaging')), 'channels, handles, playlists, footer, thumbnail gaze - ask Colden, write it like creative-lens.json')
    caches = sorted(glob.glob(f'{C.PODCUT_CACHE}/{show_id}/*/manifest.json'), key=os.path.getmtime); m = C.load(caches[-1]) if caches else None      # the episode worked on last
    if ok(f'a CWC_PodCut cache for {show_id}', bool(m), f'{C.PODCUT_CACHE}/{show_id}/<EpNN>/manifest.json - run /CWC_PodCut first'):
        ok(f'the NAS episode folder is mounted ({m["dir"]})', os.path.isdir(m['dir']), 'mount the NAS share')
        vol = '/'.join(m['dir'].split('/')[:3]); ok(f'{vol}/#recycle (where lock.py moves NAS files)', os.path.isdir(f'{vol}/#recycle'), 'without it NAS scratch goes to ~/.Trash instead (slow copy) - enable the recycle bin on the share')
        L = m.get('locked') or {}
        ok(f'the PodCut of {os.path.basename(os.path.dirname(caches[-1]))} is LOCKED, no rebuild open', bool(L) and not m.get('rebuild'), 'finish and lock it in /CWC_PodCut - this skill runs only on a locked cut')
        if L: ok('the lock snapshot holds plan, words, pod_dump, lower_thirds, layout', all(os.path.exists(f'{L["snapshot"]}/{f}') for f in ('plan.json', 'words.json', 'pod_dump.json', 'lower_thirds.json', 'layout.json')), 'lock the PodCut again with the current CWC_PodCut')
    print('Resolve' + ('' if resolve else '  (skipped - add --resolve; read-only)'))
    if resolve and m:
        code = '''
names = ['CR Stinger INtro 5 s.mov', 'The Creative Lens Stinger.mov', 'CR End Screen .mov', 'Heavy Riff (1 ).mp3', 'CR Endscreen Glitch, whoosh, transition, hit.png.wav']
def find(f, n):
    for c in f.GetClipList():
        if c.GetName() == n: return True
    return any(find(s, n) for s in f.GetSubFolderList())
tl = {project.GetTimelineByIndex(i).GetName() for i in range(1, project.GetTimelineCount() + 1)}
presets = [(p.get('RenderPresetName') if isinstance(p, dict) else str(p)) for p in (project.GetRenderPresetList() or [])]
result = {'project': project.GetName(), 'template': '00 PodClips Template' in tl, 'assets': {n: find(mp.GetRootFolder(), n) for n in names}, 'preset': 'H.264 Master' in presets}
'''
        f = '/tmp/cwc_doctor_r.py'; open(f, 'w').write(code)
        out = subprocess.run([sys.executable, f'{HERE}/rs.py', '60', f, f'PROJECT={json.dumps((m.get("resolve") or {}).get("project"))}'], capture_output=True, text=True).stdout.strip().splitlines()
        r = json.loads(out[-1]) if out else {'error': 'no answer from Resolve'}
        if ok('Resolve answers with the episode project open', not r.get('error'), f'{r.get("error")} - open DaVinci Resolve Studio on the project (External scripting = Local)'):
            ok('`00 PodClips Template` (empty, UHD, A1 "Main Pod Audio" with Colden\'s strip)', r['template'], 'r_template.py once per project, then Colden puts his compressor / NR / EQ on A1')
            for n, v in r['assets'].items(): ok(f'media pool: {n}', v, 'import it into the Master bin (same name)')
            ok('render preset "H.264 Master"', r['preset'], 'create / import the preset in Deliver')
            print('  NOTE     the glitch transition GTR_02 ("Drag-N-Drop Glitch Transitions") cannot be listed by script - build.py verify fails without it')
    print('\n' + ('ALL THERE' if not bad else f'{len(bad)} MISSING: {bad}'))

if __name__ == '__main__':
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    main(a[0] if a else 'creative-lens', '--resolve' in sys.argv); sys.exit(2 if bad else 0)
