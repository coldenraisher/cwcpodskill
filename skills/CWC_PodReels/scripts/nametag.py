"""Guest name tag as a transparent 1080x1920 PNG (Colden's spec 2026-09-11): white rounded card, drop shadow, circular
profile photo, name bold on top, handle smaller/lighter below, black text.
usage: python3 nametag_render.py "<Name>" "<handle>" <avatar.png> <left_px> <top_px> <out.png> [scale=0.885]"""
import sys, subprocess, base64, os, tempfile
name, handle, avatar, left, top, out = sys.argv[1:7]
scale = float(sys.argv[7]) if len(sys.argv) > 7 else 0.885   # Colden scaled the card to 0.885 in Fusion on 2026-09-11; that is the template size
FONTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets', 'fonts')
def face(fam, file, weight):
    p = os.path.join(FONTS, file)
    if not os.path.exists(p): return ''
    b = base64.b64encode(open(p, 'rb').read()).decode()
    return f"@font-face{{font-family:'{fam}';font-weight:{weight};src:url(data:font/woff2;base64,{b}) format('woff2')}}"
av = 'data:image/png;base64,' + base64.b64encode(open(avatar, 'rb').read()).decode()
css_fonts = face('SG', 'SpaceGrotesk-700.woff2', 700) + face('IN', 'Inter-500.woff2', 500) + face('IN', 'Inter-600.woff2', 600)
html = f"""<!doctype html><html><head><meta charset="utf-8"><style>{css_fonts}
html,body{{margin:0;width:1080px;height:1920px;background:transparent;overflow:hidden}}
.tag{{position:absolute;left:{left}px;top:{top}px;transform:scale({scale});transform-origin:top left;display:flex;align-items:center;gap:22px;background:#fff;border-radius:26px;padding:14px 32px 14px 14px;box-shadow:0 14px 34px rgba(0,0,0,.38),0 3px 8px rgba(0,0,0,.25)}}
.av{{width:92px;height:92px;border-radius:50%;object-fit:cover;display:block}}
.name{{font-family:'SG','Space Grotesk',Inter,-apple-system,sans-serif;font-weight:700;font-size:36px;line-height:1.05;color:#111;letter-spacing:-.01em}}
.handle{{font-family:'IN',Inter,-apple-system,sans-serif;font-weight:500;font-size:25px;line-height:1.1;color:#333;margin-top:6px}}
</style></head><body><div class="tag"><img class="av" src="{av}"><div><div class="name">{name}</div><div class="handle">{handle}</div></div></div></body></html>"""
tmp = tempfile.mktemp(suffix='.html'); open(tmp, 'w').write(html)
subprocess.run(["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "--headless=new", "--disable-gpu", "--hide-scrollbars", "--window-size=1080,1920",
                "--default-background-color=00000000", "--force-device-scale-factor=1", f"--screenshot={out}", "file://" + tmp], capture_output=True, timeout=60)
os.remove(tmp)
# Resolve appends stills at a fixed 150 frames whatever endFrame says, so also write a 5 s ProRes 4444 (alpha) clip that trims freely
mov = os.path.splitext(out)[0] + '.mov'
subprocess.run(['ffmpeg','-v','error','-y','-loop','1','-framerate','30','-i',out,'-t','5','-c:v','prores_ks','-profile:v','4444','-pix_fmt','yuva444p10le','-an',mov],check=True)
print(out, mov)
