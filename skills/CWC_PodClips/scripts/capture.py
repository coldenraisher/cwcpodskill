"""capture.py <url> <out.png> [--anchor "text on the page"] [--wait 2.5] [--full]
A real web page as b-roll source for a 16:9 clip (producer mode: real material first). Desktop viewport 1920x1080 at
device scale 2 = a 3840x2160 PNG of what a viewer would see; with --anchor the page is scrolled so the first element
holding that text sits ~220 px from the top. Consent banners get the most privacy-preserving choice (decline / reject /
necessary only); nothing is submitted, typed or signed into. A page behind a bot check is never worked around: use
another real source. ALWAYS look at the PNG before using it (a 404, a consent wall or an empty page is not b-roll).
Writes <out>.json {url, anchor_found, title}."""
import sys, json, time, argparse
from playwright.sync_api import sync_playwright
ap = argparse.ArgumentParser(); ap.add_argument('url'); ap.add_argument('out'); ap.add_argument('--anchor'); ap.add_argument('--wait', type=float, default=2.5); ap.add_argument('--full', action='store_true'); A = ap.parse_args()
DECLINE = ['Reject all', 'Reject All', 'Decline', 'Decline all', 'Only necessary', 'Necessary only', 'Reject', 'No thanks', 'Not now']
with sync_playwright() as p:
    b = p.chromium.launch(); ctx = b.new_context(viewport={'width': 1920, 'height': 1080}, device_scale_factor=2, locale='en-US',
        user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36')
    pg = ctx.new_page()
    try: pg.goto(A.url, wait_until='networkidle', timeout=45000)
    except Exception: pg.goto(A.url, wait_until='load', timeout=60000)
    time.sleep(A.wait)
    for label in DECLINE:
        try:
            el = pg.get_by_role('button', name=label, exact=True)
            if el.count(): el.first.click(timeout=1500); time.sleep(0.8); break
        except Exception: pass
    found = False
    if A.anchor:
        loc = pg.get_by_text(A.anchor, exact=False)
        if loc.count():
            bb = loc.first.bounding_box()
            if bb: pg.evaluate(f'window.scrollTo(0, {max(0, int(bb["y"] + pg.evaluate("window.scrollY") - 220))})'); time.sleep(1.0); found = True
    pg.screenshot(path=A.out, full_page=A.full); title = pg.title(); b.close()
json.dump({'url': A.url, 'anchor': A.anchor, 'anchor_found': found, 'title': title}, open(A.out + '.json', 'w'))
print(json.dumps({'out': A.out, 'anchor_found': found, 'title': title}))
