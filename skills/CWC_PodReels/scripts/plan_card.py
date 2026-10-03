"""plan_card.py <WORK> cwc|tcl [out.png] - one brand's posting plan as a calendar card for Telegram (edit-shorts
plan_card.py, Colden 2026-09-13: the text list was "very difficult to read"). Calendar weeks Mon..Sun, each post = its
PICKED cover + the short number + the time; the month-cap CUT list (ruling 11) printed under the calendar."""
import os, sys, datetime as dt
from PIL import Image, ImageDraw, ImageFont
import common as C
BR = {'cwc': 'Create with Colden', 'tcl': 'The Creative Lens'}
BG, CARD, INK, MUTED, ACCENT, ACCENT2, RED = (16, 17, 20), (28, 30, 36), (245, 245, 247), (150, 154, 165), (255, 196, 0), (98, 220, 140), (240, 90, 90)
def font(size, bold=False):
    for p in (['/System/Library/Fonts/Supplemental/Arial Bold.ttf', '/Library/Fonts/Arial Bold.ttf'] if bold else ['/System/Library/Fonts/Supplemental/Arial.ttf', '/Library/Fonts/Arial.ttf']):
        if os.path.exists(p): return ImageFont.truetype(p, size)
    return ImageFont.load_default()
def render(W, brand, out=None):
    pl = C.load(f'{W}/review/publish_plan.json') or C.fail('publish.py plan first')
    posts = [p for p in pl['posts'] if p['brand'] == brand]
    if not posts: C.fail(f'no posts for {brand}')
    cut = [x for x in pl.get('cut', []) if x['brand'] == brand]
    d0, d1 = dt.date.fromisoformat(posts[0]['date']), dt.date.fromisoformat(posts[-1]['date']); monday = d0 - dt.timedelta(days=d0.weekday()); weeks = (d1 - monday).days // 7 + 1
    byday = {}
    for p in posts: byday.setdefault(p['date'], []).append(p)
    perday = max(len(v) for v in byday.values()); COLS, CW, PAD, TOP = 7, 150, 30, 230; RH = 70 + perday * 248 + 10
    W_, H_ = PAD * 2 + COLS * CW, TOP + weeks * RH + 90 + 40 * len(cut)
    im = Image.new('RGB', (W_, H_), BG); dr = ImageDraw.Draw(im)
    dr.text((PAD, 36), BR[brand], font=font(54, True), fill=INK)
    cap = (pl.get('caps') or {}).get(brand); sub = f'{len(posts)} posts · {d0.strftime("%b %-d")} - {d1.strftime("%b %-d")}' + (f' · cap {cap}/month' if cap else '')
    dr.text((PAD, 104), sub, font=font(30), fill=MUTED)
    for c, name in enumerate(['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']): dr.text((PAD + c * CW + CW / 2, 175), name, font=font(26, True), fill=MUTED, anchor='mm')
    for w in range(weeks):
        for c in range(COLS):
            day = monday + dt.timedelta(days=w * 7 + c); x = PAD + c * CW; y = TOP + w * RH; inr = d0 <= day <= d1
            dr.rounded_rectangle((x + 4, y, x + CW - 4, y + RH - 12), 16, fill=CARD if inr else (22, 23, 27))
            dr.text((x + 16, y + 12), str(day.day), font=font(34, True), fill=INK if inr else (70, 72, 80))
            items = byday.get(day.isoformat(), [])
            if not items:
                if inr: dr.text((x + CW / 2, y + RH / 2), '-', font=font(30), fill=(60, 62, 70), anchor='mm')
                continue
            ty = y + 58
            for p in items[:2]:
                th = Image.open(p['cover']).convert('RGB') if p.get('cover') and os.path.exists(p['cover']) else Image.new('RGB', (108, 192), (60, 60, 70))
                th.thumbnail((CW - 40, 196)); im.paste(th, (int(x + CW / 2 - th.width / 2), ty))
                dr.rounded_rectangle((x + 14, ty + 6, x + 70, ty + 40), 8, fill=ACCENT); dr.text((x + 42, ty + 23), p['short'].upper(), font=font(20, True), fill=(20, 20, 20), anchor='mm')
                h = p['hour']; dr.text((x + CW / 2, ty + th.height + 24), f'{(h - 1) % 12 + 1} {"PM" if h >= 12 else "AM"}', font=font(30, True), fill=INK, anchor='mm')
                if p.get('ig_collab') not in (None, 'none'):
                    dr.ellipse((x + CW - 46, ty + 8, x + CW - 18, ty + 36), fill=ACCENT2); dr.text((x + CW - 32, ty + 22), 'G', font=font(20, True), fill=(10, 30, 15), anchor='mm')
                ty += th.height + 52
    y = TOP + weeks * RH + 10
    for x in cut: dr.text((PAD, y), f'CUT {x["short"].upper()}: {x["why"]}', font=font(24, True), fill=RED); y += 40
    dr.ellipse((PAD, H_ - 62, PAD + 26, H_ - 36), fill=ACCENT2); dr.text((PAD + 36, H_ - 49), 'guest invited as IG collaborator (Create with Colden only)', font=font(24), fill=MUTED, anchor='lm')
    out = out or f'{W}/review/plan_{brand}.png'; im.save(out); return out
if __name__ == '__main__':
    if len(sys.argv) < 3: C.fail(__doc__)
    print(render(os.path.abspath(sys.argv[1]), sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None))
