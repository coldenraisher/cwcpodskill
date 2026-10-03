"""Guest lower thirds (Colden 2026-10-01: "extra guests should get a name handle at the beginning and end both in full
podcut and then later on in clips"). Hosts get none here.
usage: lower_thirds.py <CACHE> [--replace] [--plan <file> --out <file>] [--locked-ok "<Colden's words>"]     (after plan.py)     -> <CACHE>/lower_thirds.json     exit 2 = ASK COLDEN
Look = the card his clips already use (edit-clips nametag): white rounded card, drop shadow, round photo, name bold,
@YouTube handle under it, bottom-left. Rendered once per guest per episode at the timeline size into
`<episode folder>/Lower Thirds/lt_<name>.png` + `.mov` (ProRes 4444 with alpha, 5 s, 8-frame fade in and out - ProRes
only, no Fusion). Name and handle come from references/guests.json and are NEVER guessed: a guest without an entry
stops the run. The PHOTO IS THE GUEST'S YOUTUBE CHANNEL PICTURE (Colden 2026-10-01: "Images on lower thirds need to
be pulled from their youtube"): fetched from the channel page of the handle (the page must answer to that same handle),
unless the registry names an `avatar` file Colden supplied. No picture -> exit 2, never a frame grab in its place.
--replace: when a guest's card changed (new photo / name / handle) and a cut already carries the old file, the media-pool
clip is pointed at the new file (r_replace.py) - the timeline items stay where they are; the old files move to
`Lower Thirds/_superseded/` (moved, not deleted).
Placement: over the guest's FIRST and LAST close-up that can hold it - a 'speaker' shot (not a reaction, never the
wide) of >= 6 s - starting 15 frames into the shot and ending >= 15 frames before its end.
Gates: both placements exist for every guest; each lies inside ONE close-up of that guest, 15 frames clear of its cuts."""
import os, re, sys, json, subprocess, tempfile, base64
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

cache = sys.argv[1]; m = C.manifest(cache); sh = C.show(m['show'])
def opt(name, default=None): return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default
plan_path = opt('--plan', f'{cache}/plan.json'); out_path = opt('--out', f'{cache}/lower_thirds.json')
if C.frozen(m) and out_path == f'{cache}/lower_thirds.json' and not opt('--locked-ok'):
    C.die(f"this episode is LOCKED ({m['locked']['timeline']}): its lower thirds are not re-made or swapped without Colden's word (--locked-ok \"<his words>\")")
P = json.load(open(plan_path)); F = P['fps']
CW, CH = sh.get('canvas', [1920, 1080]); LEN = int(round(5 * F)); EDGE = 15; FADE = 8
reg = json.load(open(f'{C.SK}/references/guests.json')).get(m['show'], {})
guests = [c for c in C.speakers(m) if not c.get('host')]; missing = [c['name'] for c in guests if not (reg.get(c['name'], {}).get('name') and reg.get(c['name'], {}).get('handle'))]
if missing: C.die(f"no name / YouTube handle on file for guest(s) {missing} - ask Colden, then add them to references/guests.json (never guess a name or a handle)")
out_dir = f"{m['dir']}/Lower Thirds"; os.makedirs(out_dir, exist_ok=True); tags = []; made = {}
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36'
def avatar_from_youtube(handle, dst):
    """the channel picture of @handle -> dst (.jpg, 400 px). Returns {'channel', 'image'} or raises SystemExit(2)."""
    from PIL import Image
    assert handle.startswith('@'), f'not a YouTube handle: {handle!r}'
    html = subprocess.run(['curl', '-sL', '--max-time', '40', '-A', UA, '-H', 'Accept-Language: en-US,en;q=0.9', f'https://www.youtube.com/{handle}'], capture_output=True).stdout.decode('utf-8', 'ignore')
    van = re.search(r'"vanityChannelUrl":"[^"]*/(@[^"/]+)"', html); img = re.search(r'<meta property="og:image" content="([^"]+)"', html); can = re.search(r'<link rel="canonical" href="([^"]+)"', html)
    if not (van and img) or van.group(1).lower() != handle.lower():
        C.die(f"could not get the YouTube channel picture for {handle} (page answered {van.group(1) if van else 'no channel'}) - check the handle with Colden, or have him supply the image (`avatar` in references/guests.json)")
    url = re.sub(r'=s\d+-', '=s400-', img.group(1))
    subprocess.run(['curl', '-sL', '--max-time', '40', '-A', UA, url, '-o', dst], check=True)
    try:
        im = Image.open(dst); im.load(); assert min(im.size) >= 150
    except Exception: C.die(f'the picture fetched for {handle} is not a usable image ({url})')
    return {'channel': can.group(1) if can else None, 'image': url}
def render(name, handle, avatar, png):
    av = ('data:image/jpeg;base64,' if avatar.lower().endswith(('.jpg', '.jpeg')) else 'data:image/png;base64,') + base64.b64encode(open(avatar, 'rb').read()).decode()
    k = CW / 3840 * 2.2                                    # the clips' card is scale 2.2 on a 3840 canvas, left 182 / top 1722
    esc = lambda s: s.replace('&', '&amp;').replace('<', '&lt;')
    html = f"""<!doctype html><html><head><meta charset="utf-8"><style>
html,body{{margin:0;width:{CW}px;height:{CH}px;background:transparent;overflow:hidden}}
.tag{{position:absolute;left:{round(182 * CW / 3840)}px;top:{round(1722 * CH / 2160)}px;transform:scale({k:.4f});transform-origin:top left;display:flex;align-items:center;gap:22px;background:#fff;border-radius:26px;padding:14px 32px 14px 14px;box-shadow:0 14px 34px rgba(0,0,0,.38),0 3px 8px rgba(0,0,0,.25)}}
.av{{width:92px;height:92px;border-radius:50%;object-fit:cover;display:block}}
.name{{font-family:'Space Grotesk',Inter,-apple-system,sans-serif;font-weight:700;font-size:36px;line-height:1.05;color:#111;letter-spacing:-.01em;white-space:nowrap}}
.handle{{font-family:Inter,-apple-system,sans-serif;font-weight:500;font-size:25px;line-height:1.1;color:#333;margin-top:6px;white-space:nowrap}}
</style></head><body><div class="tag"><img class="av" src="{av}"><div><div class="name">{esc(name)}</div><div class="handle">{esc(handle)}</div></div></div></body></html>"""
    tmp = tempfile.mktemp(suffix='.html'); open(tmp, 'w').write(html)
    subprocess.run(['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '--headless=new', '--disable-gpu', '--hide-scrollbars', f'--window-size={CW},{CH}',
                    '--default-background-color=00000000', '--force-device-scale-factor=1', f'--screenshot={png}', 'file://' + tmp], capture_output=True, timeout=90)
    os.remove(tmp); assert os.path.exists(png), 'Chrome did not write the card'
    mov = os.path.splitext(png)[0] + '.mov'; secs = LEN / F
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-loop', '1', '-framerate', str(F), '-i', png, '-t', f'{secs:.4f}', '-vf', f'format=rgba,fade=t=in:st=0:d={FADE / F:.4f}:alpha=1,fade=t=out:st={secs - FADE / F:.4f}:d={FADE / F:.4f}:alpha=1',
                    '-c:v', 'prores_ks', '-profile:v', '4444', '-pix_fmt', 'yuva444p10le', '-an', mov], check=True)
    pr = C.probe(mov); assert (pr['width'], pr['height']) == (CW, CH) and abs(pr['duration'] - secs) < 0.05, f'{mov}: wrong size or length'
    return mov
problems = []; prev = C.load(out_path, {'guests': {}}); swaps = []
import hashlib
for c in guests:
    g = reg[c['name']]; slug = re.sub(r'[^a-z0-9]+', '', c['name'].lower()); av = g.get('avatar'); src = {'supplied': av} if av else None
    if not av:
        av = f'{out_dir}/avatar_{slug}_youtube.jpg'; meta = f'{out_dir}/avatar_{slug}_youtube.json'
        if not (os.path.exists(av) and os.path.exists(meta) and json.load(open(meta)).get('handle') == g['handle']):
            got = avatar_from_youtube(g['handle'], av); C.save(meta, {'handle': g['handle'], **got})
        src = json.load(open(meta))
    assert os.path.exists(av), f"{c['name']}: avatar file {av} not found"
    stamp = hashlib.sha1(f"{g['name']}|{g['handle']}|{CW}x{CH}|{LEN}|".encode() + open(av, 'rb').read()).hexdigest()[:6]
    png = f'{out_dir}/lt_{slug}_{stamp}.png'; mov = os.path.splitext(png)[0] + '.mov'
    if not (os.path.exists(png) and os.path.exists(mov)): render(g['name'], g['handle'], av, png)
    made[c['name']] = {'file': mov, 'png': png, 'avatar': av, 'avatar_source': src, 'name': g['name'], 'handle': g['handle']}
    old = (prev.get('guests') or {}).get(c['name'], {}).get('file')
    if old and old != mov: swaps.append((c['name'], old, mov, (prev['guests'][c['name']].get('png'), prev['guests'][c['name']].get('avatar'))))
    hold = [s for s in P['segments'] if s['camera'] == c['id'] and s['reason'].split('+')[0] == 'speaker' and s['frames'] >= LEN + 2 * EDGE]
    if not hold: problems.append(f"{c['name']}: no close-up of >= {(LEN + 2 * EDGE) / F:.0f} s to hold the lower third"); continue
    picks = [('beginning', hold[0])] + ([('end', hold[-1])] if hold[-1] is not hold[0] else [])
    if len(picks) < 2: problems.append(f"{c['name']}: only one close-up can hold the lower third - no separate one for the end")
    for where, s in picks:
        tags.append({'who': c['name'], 'camera': c['id'], 'where': where, 'file': made[c['name']]['file'], 'outFrame': s['outFrame'] + EDGE, 'frames': LEN, 'shot': [s['outFrame'], s['outFrame'] + s['frames']]})
for t in tags:      # gate
    assert t['shot'][0] + EDGE <= t['outFrame'] and t['outFrame'] + t['frames'] <= t['shot'][1] - EDGE, f"lower third for {t['who']} ({t['where']}) does not sit inside its close-up"
C.save(out_path, {'canvas': [CW, CH], 'fps': F, 'guests': made, 'tags': tags, 'plan_out_frames': P['stats']['out_frames'], 'problems': problems})
for t in tags: print(f"  {t['who']:8s} {t['where']:9s} at {C.hms(t['outFrame'] / F)} of the cut, {t['frames'] / F:.0f} s  ({os.path.basename(t['file'])})")
if not guests: print('  no guests in this episode - no lower thirds')
for who, old, new, extra in swaps:
    if '--replace' not in sys.argv: print(f"  NOTE {who}: the card changed ({os.path.basename(old)} -> {os.path.basename(new)}); cuts already built still show the old one - re-run with --replace"); continue
    assert m['resolve'].get('project'), 'no Resolve project in the manifest - cannot replace a clip in "whatever is open"'
    r = C.rs('r_replace.py', 180, PROJECT=m['resolve']['project'], BIN=m['resolve']['bin'] + '/Lower Thirds', OLD=old, NEW=new); print(f'  {who}: replaced in Resolve {r}')
    sup = f'{out_dir}/_superseded'; os.makedirs(sup, exist_ok=True)
    for f in [old] + [x for x in extra if x and x != made[who]['avatar']] + [os.path.splitext(old)[0] + '.txt']:
        if f and os.path.exists(f) and os.path.dirname(f) == out_dir: os.replace(f, f'{sup}/{os.path.basename(f)}')
if problems: C.die('; '.join(problems))
