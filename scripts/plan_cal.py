"""plan_cal.py <RUN> [brand]      the posting plan as a CALENDAR GRAPHIC, one image per channel (PNG in <RUN>/plan_cal_<brand>.png)
Colden 2026-10-09, Ep 25 plan card: "On telegram show as a calendar graphic. one for TCL, one graphic for CWC. too confusing
as all that text." Each day is a column (5 per row); this plan's posts are colour cards (CLIP red, SHORT blue) with the time,
the title, where it goes (YT / FB / IG / TT, by hand) and the collaborators; what was ALREADY on the calendar (YouTube +
Metricool) shows as grey lines so the doubling up is visible. tg_plan.py send sends both images before the buttons."""
import os, sys, textwrap, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
from PIL import Image, ImageDraw, ImageFont

FONT = '/System/Library/Fonts/HelveticaNeue.ttc'
COLS, CW, PAD = 5, 400, 14
INK, MUTED, BG, LINE = (20, 20, 24), (125, 125, 135), (247, 247, 249), (222, 222, 228)
KIND = {'clip': ((214, 48, 49), 'CLIP'), 'short': ((9, 132, 227), 'SHORT')}
NET = {'facebook': 'FB', 'instagram': 'IG', 'tiktok': 'TT'}

def f(size, bold=False):
    try: return ImageFont.truetype(FONT, size, index=1 if bold else 0)
    except OSError: return ImageFont.load_default()

def et(iso): return dt.datetime.fromisoformat(str(iso).replace('Z', '+00:00')).astimezone(C.ET)

def entries(R, P, b):
    """this plan's posts for brand b, one entry per product slot (the YouTube item + its Metricool post together)"""
    g = {}
    for i in P['items']:
        if i['brand'] == b: g.setdefault((i['publish_at'], i['ref'], i['product']), []).append(i)
    out = []
    for (at, ref, prod), its in sorted(g.items()):
        soc = next((x for x in its if x['kind'] == 'social'), None)
        title = next((x['title'] for x in its if x['kind'] != 'social'), its[0]['title'])
        where = ['YT']
        if soc: where.append('/'.join(NET[n] for n in soc['networks']) + ('' if soc['route'] == 'metricool' else ' BY HAND'))
        collab = ' '.join('@' + h for h in (soc or {}).get('ig_collabs') or [])
        out.append({'t': et(at), 'kind': prod, 'title': title, 'where': ' + '.join(where), 'collab': collab, 'ref': ref})
    return out

def existing(R, b):
    """what is already scheduled / published on that brand's calendar (grey)"""
    out = []
    yt = C.load(f'{R}/calendar/youtube.json') or {}
    for v in (yt.get('channels') or {}).get(b, []):
        w = v.get('start_at') or v.get('publish_at') or v.get('published_at')
        if w: out.append({'t': et(w), 'label': ('LIVE' if v['kind'] == 'live' else 'YT clip' if v['kind'] == 'long' else 'YT Short'), 'title': v.get('title') or ''})
    for x in (C.load(f'{R}/calendar/metricool_{b}.json') or {}).get('posts', []):
        out.append({'t': et(x['at']) if 'T' in str(x['at']) else et(x['at'] + 'T00:00'), 'label': 'Metricool', 'title': x.get('title') or x.get('text') or ''})
    return out

def wrap(d, text, font, width):
    words, lines, cur = str(text).split(), [], ''
    for w in words:
        t = (cur + ' ' + w).strip()
        if d.textlength(t, font=font) <= width: cur = t
        else: lines.append(cur); cur = w
    return lines + ([cur] if cur else [])

def render(R, P, b):
    B = C.brands(); mine = entries(R, P, b)
    w0 = dt.date.fromisoformat(P['window']['start'])
    last = max([e['t'].date() for e in mine] + [dt.date.fromisoformat(P['window']['end'])])
    days = [w0 + dt.timedelta(days=i) for i in range((last - w0).days + 1)]
    old = [e for e in existing(R, b) if w0 <= e['t'].date() <= last]
    probe = ImageDraw.Draw(Image.new('RGB', (10, 10)))
    ft, fb, fs, fh, fx = f(19), f(21, True), f(16), f(26, True), f(15)
    # lay out every column first to know the row heights
    cols = {}
    for d in days:
        blocks = []
        for e in [x for x in old if x['t'].date() == d]:
            ln = wrap(probe, f'{e["t"]:%-I:%M%p} {e["label"]}: {e["title"]}', fx, CW - 2 * PAD - 16)[:2]
            blocks.append(('old', e, ln, 8 + 19 * len(ln)))
        for e in [x for x in mine if x['t'].date() == d]:
            ln = wrap(probe, e['title'], ft, CW - 2 * PAD - 40)[:4]
            h = 40 + 25 * len(ln) + 24 + (22 if e['collab'] else 0) + 10
            blocks.append(('new', e, ln, h))
        cols[d] = sorted(blocks, key=lambda bk: (bk[1]['t'], bk[0] == 'new'))      # one timeline: grey and new by time
    rows = [days[i:i + COLS] for i in range(0, len(days), COLS)]
    rh = [56 + max([sum(bk[3] + 10 for bk in cols[d]) for d in row] + [60]) + 10 for row in rows]
    W, top = COLS * CW + PAD, 96
    img = Image.new('RGB', (W, top + sum(rh) + 50), BG); d = ImageDraw.Draw(img)
    n_clip = sum(1 for e in mine if e['kind'] == 'clip'); n_short = len(mine) - n_clip
    d.text((PAD + 6, 18), f'{B[b]["label"]}  -  {P.get("show_name") or ""} {P.get("ep_key") or ""} posting plan', font=f(32, True), fill=INK)
    d.text((PAD + 6, 60), f'{n_clip} clips + {n_short} Shorts/reels (colour) - grey = already on the calendar - times ET - window {P["window"]["start"][5:]} to {P["window"]["end"][5:]}', font=fs, fill=MUTED)
    y = top
    for row, h in zip(rows, rh):
        for k, day in enumerate(row):
            x = PAD + k * CW
            out_of_window = day > dt.date.fromisoformat(P['window']['end'])
            d.rounded_rectangle((x, y, x + CW - PAD, y + h - 10), 12, fill=(255, 255, 255), outline=LINE, width=2)
            d.text((x + PAD, y + 12), f'{C.DAYS[day.weekday()].upper()} {day:%-m/%-d}' + ('  (after window)' if out_of_window else ''), font=fh if not out_of_window else fb, fill=INK if not out_of_window else MUTED)
            yy = y + 56
            for kind, e, ln, bh in cols[day]:
                if kind == 'old':
                    for i, l in enumerate(ln): d.text((x + PAD + 4, yy + 4 + 19 * i), l, font=fx, fill=MUTED)
                else:
                    col, lab = KIND[e['kind']]
                    d.rounded_rectangle((x + PAD, yy, x + CW - 2 * PAD, yy + bh), 10, fill=tuple(int(c * .12 + 255 * .88) for c in col), outline=col, width=2)
                    d.rounded_rectangle((x + PAD + 10, yy + 9, x + PAD + 10 + d.textlength(lab, font=fs) + 16, yy + 33), 6, fill=col)
                    d.text((x + PAD + 18, yy + 11), lab, font=fs, fill=(255, 255, 255))
                    d.text((x + PAD + 26 + d.textlength(lab, font=fs) + 12, yy + 8), f'{e["t"]:%-I:%M %p}', font=fb, fill=INK)
                    for i, l in enumerate(ln): d.text((x + PAD + 12, yy + 40 + 25 * i), l, font=ft, fill=INK)
                    yl = yy + 40 + 25 * len(ln) + 2
                    d.text((x + PAD + 12, yl), e['where'], font=fs, fill=col)
                    if e['collab']: d.text((x + PAD + 12, yl + 22), 'collab ' + e['collab'], font=fs, fill=MUTED)
                yy += bh + 10
        y += h
    p = f'{R}/plan_cal_{b}.png'; img.save(p); return p

def render_all(R):
    P = C.load(f'{R}/plan.json') or C.fail('no plan.json - plan.py build first')
    r = C.run(R); P = dict(P, show_name=r.get('show_name'), ep_key=r.get('ep_key'))
    return [render(R, P, b) for b in ('cwc', 'tcl') if any(i['brand'] == b for i in P['items'])]

if __name__ == '__main__':
    if len(sys.argv) < 2: print(__doc__); sys.exit(1)
    for p in render_all(sys.argv[1]): print(p)
