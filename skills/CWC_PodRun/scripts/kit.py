"""kit.py <RUN>      the hand-made part of an approved plan, laid out in the episode folder on the NAS
  YouTube, route studio_manual (until the API audit passes): <episode>/Final/YouTube Upload List.md - in publish order,
          the file to drag into Studio, the channel, and the exact date + time to schedule. Upload it under its own file
          name: youtube.py find matches on it, then apply writes the title, description, tags, thumbnail, captions, playlists.
  Social posts over the Metricool cap (route manual): <episode>/Final/Manual Posts/<YYYY-MM-DD HHMM> <Brand> <title>/
          with the video, the cover and post.txt (networks, time ET, the caption - the same on every network, the first
          comment, the IG collaborator). Logged as 'manual_kit' in publish_log.json: handled once the kit is in place.
Copies are checked by size; a file already there with the same size is left alone. NAS not mounted = exit 2."""
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
    yt = [i for i in P['items'] if i['route'] == 'studio_manual']
    if yt:
        L = [f'# YouTube upload list - {r["show_name"]} {r["ep_key"]}', '', 'Until the API audit passes: upload each file in Studio UNDER ITS OWN FILE NAME and schedule it at the time below.',
             'Then tell Claude "uploaded" - youtube.py find + apply write the title, description, tags, thumbnail, captions and playlists.', '',
             '| When (ET) | Channel | Kind | File | Final title |', '|---|---|---|---|---|']
        for i in yt: L.append(f'| {i["weekday"]} {i["publish_at"][:10]} {i["publish_at"][11:16]} | {B[i["brand"]]["label"]} | {"Clip" if i["kind"] == "yt_clip" else "Short"} | {i["files"]["video"]} | {i["title"]} |')
        open(f'{final}/YouTube Upload List.md', 'w', encoding='utf-8').write('\n'.join(L) + '\n'); print(f'{final}/YouTube Upload List.md ({len(yt)} videos)')
    man = [i for i in P['items'] if i['route'] == 'manual']
    for i in man:
        d = f'{final}/Manual Posts/{i["publish_at"][:10]} {i["publish_at"][11:13]}{i["publish_at"][14:16]} {B[i["brand"]]["label"]} {safe(i["title"])}'
        os.makedirs(d, exist_ok=True)
        copy(i['files']['video'], f'{d}/{os.path.basename(i["files"]["video"])}')
        if i['files'].get('thumb'): copy(i['files']['thumb'], f'{d}/cover{os.path.splitext(i["files"]["thumb"])[1]}')
        nets = ', '.join({'tiktok': 'TikTok'}.get(n, n.capitalize()) for n in i['networks'])
        txt = [f'POST BY HAND - over the {B[i["brand"]]["label"]} Metricool cap ({B[i["brand"]]["metricool"]["month_cap"]}/month)', f'When: {i["weekday"]} {i["publish_at"][:10]} {i["publish_at"][11:16]} ET',
               f'Account: {B[i["brand"]]["label"]}  Networks: {nets}', '', 'Caption (same on every network):', i['text'], '', f'First comment: {i.get("first_comment") or "-"}']
        if i.get('ig_collab'): txt.append(f'Instagram collaborator: @{i["ig_collab"]}')
        if i.get('fb_title'): txt.append(f'Facebook title: {i["fb_title"]}')
        open(f'{d}/post.txt', 'w', encoding='utf-8').write('\n'.join(txt) + '\n')
        log.setdefault(i['id'], {'route': 'manual_kit', 'kit': d, 'publish_at': i['publish_at'], 'at': C.now()})
    C.save(f'{R}/publish_log.json', log)
    if man: print(f'{len(man)} manual post kit(s) in {final}/Manual Posts'); C.event(R, f'KIT {len(man)} manual posts, {len(yt)} studio uploads listed')

if __name__ == '__main__': main()
