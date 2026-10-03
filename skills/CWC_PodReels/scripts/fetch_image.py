"""fetch_image.py - real b-roll stills with their origin recorded (producer mode: real material first; Colden asks
"was this found or generated?" - the answer is in the sidecar).
  fetch_image.py wiki "<Wikipedia page title>" <out.jpg>        the page's lead image (poster / photo) at full size
  fetch_image.py commons "File:<name>" <out.jpg>               a Wikimedia Commons file
  fetch_image.py search "<words>" [n]                          Commons file search -> titles, sizes, licences
  fetch_image.py screen "<url>" <out.png> [scroll_px]          the real page as a PHONE sees it, 1080x1920 (FETCH_DPR=4: 2160x3840 for a close-up crop) (headless Chrome,
                                                               540x960 CSS at 2x, iPhone UA, a throwaway profile - never
                                                               Colden's Chrome); a screen already shaped for a short
Writes <out>.json next to the image: {origin, page, license, author, width, height}. A file under 1000 px on its short
side is refused (it would be upscaled past 2.6x on a 1080x1920 cover crop). A screen that came back blank, a login
wall or a consent / robot check is not b-roll: LOOK at every capture (never click through a captcha)."""
import os, sys, json, tempfile, subprocess, urllib.parse, urllib.request
CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
PHONE_UA = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1'
UA = {'User-Agent': 'CWC_PodReels/1.0 (b-roll research for Create with Colden; colden@americanira.com)'}
def C_now(): import time; return time.strftime('%Y-%m-%d %H:%M')
def get(url):
    return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30))
def info(title):
    q = get('https://commons.wikimedia.org/w/api.php?' + urllib.parse.urlencode({'action': 'query', 'titles': title, 'prop': 'imageinfo', 'iiprop': 'url|size|extmetadata', 'format': 'json'}))
    p = next(iter(q['query']['pages'].values())); ii = (p.get('imageinfo') or [None])[0]
    if not ii: return None
    m = ii.get('extmetadata', {}); clean = lambda s: __import__('re').sub(r'<[^>]+>', '', s or '')[:120]
    return {'url': ii['url'], 'width': ii['width'], 'height': ii['height'], 'license': clean(m.get('LicenseShortName', {}).get('value')), 'author': clean(m.get('Artist', {}).get('value')), 'page': ii.get('descriptionurl')}
def save(meta, out, origin):
    if min(meta['width'], meta['height']) < 1000 and not os.environ.get('ALLOW_SMALL'): raise SystemExit(f'GATE: {meta["width"]}x{meta["height"]} is too small for a full-frame cover crop')
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    data = urllib.request.urlopen(urllib.request.Request(meta['url'], headers=UA), timeout=60).read()   # bytes first: a refused download leaves no empty file
    open(out, 'wb').write(data)
    json.dump(dict(meta, origin=origin), open(out + '.json', 'w'), indent=1); print(out, meta['width'], meta['height'], meta['license'], meta['author'])
if __name__ == '__main__':
    a = sys.argv[1:]
    if not a: print(__doc__); sys.exit(1)
    if a[0] == 'wiki':
        q = get('https://en.wikipedia.org/w/api.php?' + urllib.parse.urlencode({'action': 'query', 'titles': a[1], 'prop': 'pageimages', 'piprop': 'original|name', 'format': 'json', 'redirects': 1}))
        p = next(iter(q['query']['pages'].values()))
        if 'original' not in p: raise SystemExit(f'no lead image on "{a[1]}"')
        o = p['original']; meta = {'url': o['source'], 'width': o['width'], 'height': o['height'], 'license': 'see page (non-free images are used on Wikipedia under fair use)', 'author': '', 'page': f'https://en.wikipedia.org/wiki/{urllib.parse.quote(p["title"].replace(" ", "_"))}', 'file': p.get('pageimage')}
        c = info('File:' + p['pageimage']) if p.get('pageimage') else None
        if c: meta.update({k: c[k] for k in ('license', 'author')}, file_page=c['page'])
        save(meta, a[2], f'Wikipedia "{p["title"]}" lead image')
    elif a[0] == 'poster':                                # a film's infobox poster (non-free, hosted on en.wikipedia itself)
        q = get('https://en.wikipedia.org/w/api.php?' + urllib.parse.urlencode({'action': 'parse', 'page': a[1], 'prop': 'images', 'format': 'json', 'redirects': 1}))
        imgs = [i for i in q['parse']['images'] if i.lower().endswith(('.jpg', '.jpeg', '.png')) and 'poster' in i.lower() or 'theatrical' in i.lower()]
        imgs = imgs or [i for i in q['parse']['images'] if i.lower().endswith(('.jpg', '.jpeg', '.png'))]
        if not imgs: raise SystemExit(f'no poster on "{a[1]}"')
        r = get('https://en.wikipedia.org/w/api.php?' + urllib.parse.urlencode({'action': 'query', 'titles': 'File:' + imgs[0], 'prop': 'imageinfo', 'iiprop': 'url|size', 'format': 'json'}))
        ii = next(iter(r['query']['pages'].values()))['imageinfo'][0]
        os.environ['ALLOW_SMALL'] = '1'                   # posters on Wikipedia are low resolution by policy: fit_poster renders them
        save({'url': ii['url'], 'width': ii['width'], 'height': ii['height'], 'license': 'non-free poster (fair use, commentary)', 'author': '', 'page': f'https://en.wikipedia.org/wiki/{urllib.parse.quote(a[1].replace(" ", "_"))}', 'file': imgs[0]}, a[2], f'Wikipedia "{a[1]}" poster')
    elif a[0] == 'commons':
        meta = info(a[1]); assert meta, f'{a[1]} not found'; save(meta, a[2], f'Wikimedia Commons {a[1]}')
    elif a[0] == 'screen':
        url, out = a[1], os.path.abspath(a[2]); scroll = int(a[3]) if len(a) > 3 else 0; os.makedirs(os.path.dirname(out), exist_ok=True)
        prof = tempfile.mkdtemp(prefix='podreels_chrome_'); h = 960 + scroll // 2
        if os.path.exists(out): os.rename(out, out + '.old')
        # headless Chrome on macOS writes the screenshot and then does not quit: wait for the file, then end THIS process group
        pr = subprocess.Popen([CHROME, '--headless=new', f'--user-data-dir={prof}', '--disable-gpu', '--hide-scrollbars', '--no-first-run', f'--window-size=540,{h}',
                               f'--force-device-scale-factor={os.environ.get("FETCH_DPR", "2")}', f'--user-agent={PHONE_UA}', '--virtual-time-budget=10000', f'--screenshot={out}', url],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        import time, signal; t0 = time.time(); last = -1
        while time.time() - t0 < 90:
            time.sleep(1); sz = os.path.getsize(out) if os.path.exists(out) else -1
            if sz > 0 and sz == last: break
            last = sz
        try: os.killpg(pr.pid, signal.SIGTERM); pr.wait(10)
        except Exception: pass
        __import__('shutil').rmtree(prof, ignore_errors=True)   # the throwaway profile made just above
        if not os.path.exists(out): raise SystemExit(f'no screenshot of {url}')
        from PIL import Image
        im = Image.open(out); w, hh = im.size
        k = int(os.environ.get('FETCH_DPR', '2')) / 2
        if scroll: im.crop((0, hh - int(1920 * k), int(1080 * k), hh)).save(out); w, hh = int(1080 * k), int(1920 * k)   # the phone screen after scrolling down `scroll` px
        json.dump({'origin': f'screenshot of {url} as a phone shows it ({C_now()})', 'page': url, 'license': 'screen capture for commentary', 'author': '', 'width': w, 'height': hh}, open(out + '.json', 'w'), indent=1)
        print(out, w, hh)
    elif a[0] == 'search':
        q = get('https://commons.wikimedia.org/w/api.php?' + urllib.parse.urlencode({'action': 'query', 'list': 'search', 'srsearch': a[1] + ' filetype:bitmap', 'srnamespace': 6, 'srlimit': int(a[2]) if len(a) > 2 else 10, 'format': 'json'}))
        for r in q['query']['search']:
            m = info(r['title']) or {}; print(r['title'], m.get('width'), m.get('height'), m.get('license'))
    else: print(__doc__)
