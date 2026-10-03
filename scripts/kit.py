"""kit.py <RUN>      the posts that go out BY HAND: social posts over a brand's Metricool cap (20 a month, resets on the 1st)
<episode>/Final/Manual Posts/<YYYY-MM-DD HHMM> <Brand> <title>/ with the video, the cover and post.txt: networks, time
ET, the caption (the same on every network), the first comment, the Instagram collaborators (the reel's ONE set, only on
the post that carries it), the Facebook title. Logged as 'manual_kit' in publish_log.json - handled once the kit is in
place. Copies are checked by size; a file already there with the same size is left alone. NAS not mounted = exit 2.
(YouTube is never manual: youtube.py uploads every video.)"""
import os, sys, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

BAD = '\\/:*?"<>|'
def safe(s): return ''.join('-' if ch in BAD else ch for ch in s).strip()[:90]

def copy(src, dst):
    if not src or not os.path.exists(src): C.ask(f'not on disk (NAS mounted?): {src}')
    if os.path.exists(dst) and os.path.getsize(dst) == os.path.getsize(src): return
    shutil.copy2(src, dst)
    if os.path.getsize(dst) != os.path.getsize(src): C.fail(f'copy did not verify: {dst}')

def main():
    R = sys.argv[1].rstrip('/') if len(sys.argv) > 1 else C.fail('kit.py <RUN>')
    r = C.run(R); P = C.load(f'{R}/plan.json') or C.fail('no plan.json')
    if (r.get('plan_approval') or {}).get('sha') != P['sha']: C.fail('the plan is not approved')
    final = f'{r["episode_dir"]}/Final'
    if not os.path.isdir(r['episode_dir']): C.ask(f'episode folder not reachable (NAS mounted?): {r["episode_dir"]}')
    os.makedirs(final, exist_ok=True); B = C.brands(); log = C.load(f'{R}/publish_log.json', {}) or {}
    man = [i for i in P['items'] if i['route'] == 'manual']
    for i in man:
        d = f'{final}/Manual Posts/{i["publish_at"][:10]} {i["publish_at"][11:13]}{i["publish_at"][14:16]} {B[i["brand"]]["label"]} {safe(i["title"])}'
        os.makedirs(d, exist_ok=True)
        copy(i['files']['video'], f'{d}/{os.path.basename(i["files"]["video"])}')
        if i['files'].get('thumb'): copy(i['files']['thumb'], f'{d}/cover{os.path.splitext(i["files"]["thumb"])[1]}')
        nets = ', '.join({'tiktok': 'TikTok'}.get(n, n.capitalize()) for n in i['networks'])
        txt = [f'POST BY HAND - over the {B[i["brand"]]["label"]} Metricool cap ({B[i["brand"]]["metricool"]["month_cap"]}/month)', f'When: {i["weekday"]} {i["publish_at"][:10]} {i["publish_at"][11:16]} ET',
               f'Account: {B[i["brand"]]["label"]}  Networks: {nets}', '', 'Caption (same on every network):', i['text'], '', f'First comment: {i.get("first_comment") or "-"}']
        txt.append('Instagram collaborators: ' + (' '.join('@' + h for h in i['ig_collabs']) if i.get('ig_collabs') else 'none on this post' + (' (the reel\'s collaborators are on its Create with Colden post)' if i['brand'] == 'tcl' and i.get('speakers') else '')))
        if i.get('fb_title'): txt.append(f'Facebook title: {i["fb_title"]}')
        open(f'{d}/post.txt', 'w', encoding='utf-8').write('\n'.join(txt) + '\n')
        log.setdefault(i['id'], {'route': 'manual_kit', 'kit': d, 'publish_at': i['publish_at'], 'at': C.now()})
    C.save(f'{R}/publish_log.json', log)
    print(f'{len(man)} manual post kit(s) in {final}/Manual Posts' if man else 'no manual posts in this plan')
    if man: C.event(R, f'KIT {len(man)} manual posts')

if __name__ == '__main__': main()
