"""intake.py "<episode folder>" [--show creative-lens] [--resolve-window "<Colden's words>"]
          [--window YYYY-MM-DD YYYY-MM-DD --by "<Colden's words>"] [--post-ok "<Colden's words>"]
An episode folder on the NAS -> a RUN folder (run/<show>/<EpNN>/run.json) that knows where every skill of the pipeline
keeps this episode: CWC_PodCut's cache, CWC_PodClips' WORK, CWC_PodReels' WORK, the show date, the posting window.
Show + episode key are found exactly the way CWC_PodCut's intake.py finds them (its show files: nas_root, episode_pattern),
so every skill lands on the same <show>/<EpNN>. The show date comes from the folder name ("Ep. 24 - 10:1" = Oct 1).
  --resolve-window  the window Colden gave for unattended Resolve work ("Resolve is yours until 2am"). Without one the
                    sub-skills ask before every Resolve build / render (their own safety rule).
  --window          the posting span Colden gave. THE FIRST QUESTION OF EVERY RUN (Colden 2026-10-03: "You should alway
                    start this skill by asking a time window for these posts, then you develop your cadence from there"):
                    without a confirmed window intake writes run.json with a PROPOSAL and exits 2 - ask him, then run
                    intake again with --window ... --by "<his words>" (or window.py set).
  --colden-uploads  his words when HE uploads every clip + Short in Studio and the API only adds the metadata + publish time
                    (Colden 2026-10-08: "I will upload all YouTube videos to help with quota. You handle all the metadata
                    and schedule"): plan.py paces by metadata units, youtube.py adopt matches his uploads, youtube.py upload refuses.
  --post-ok         his posting yes, asked IN CHAT in the same breath as the window, while he is at the computer (Colden
                    2026-10-03: "we will keep confirmation here. As long as it runs at the beginning of this skill while
                    i am still at this computer. cannot ask hours after we run the skill"). The question: "When you tap
                    Schedule all on the plan card, may I post everything on it - including the YouTube uploads on later
                    days - without asking you here again?" His yes -> his Telegram tap is the go; youtube.py upload and
                    metricool.py payloads refuse without it (common.post_ok). Never asked later in the run.
exit 0 = run.json written with his window and his posting yes (re-running keeps what is already recorded); 2 = ask (the
window / the posting yes / which show / folder missing)."""
import os, sys, argparse, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

ap = argparse.ArgumentParser(); ap.add_argument('episode'); ap.add_argument('--show'); ap.add_argument('--resolve-window')
ap.add_argument('--window', nargs=2, metavar=('START', 'END')); ap.add_argument('--by'); ap.add_argument('--post-ok'); ap.add_argument('--colden-uploads'); ap.add_argument('--metricool-all'); ap.add_argument('--full-episode', nargs=3, metavar=('CWC_ID', 'TCL_ID', 'WORDS'))
A = ap.parse_args()
D = A.episode.rstrip('/')
if not os.path.isdir(D): C.ask(f'not a folder (is the NAS mounted?): {D}')
sh = next((s for s in C.shows() if s['id'] == A.show), None) if A.show else next((s for s in C.shows() if D.startswith(s['nas_root'])), None)
if not sh: C.ask(f'which show is {D}? pass --show ({", ".join(s["id"] for s in C.shows())})')
ep_key, ep_no = C.ep_key_for(sh, D)
R = C.run_dir(sh['id'], ep_key); os.makedirs(R, exist_ok=True)
r = C.load(f'{R}/run.json') or {'created': C.now(), 'stages': {}}

today = dt.datetime.now(C.ET).date()
show_day = C.show_date(os.path.basename(D), today)
r.update(show=sh['id'], show_name=sh['name'], ep_key=ep_key, ep_no=ep_no, episode_dir=D, episode_name=os.path.basename(D),
         podcut_cache=f'{C.PODCUT_CACHE}/{sh["id"]}/{ep_key}', clips_work=f'{C.CLIPS}/{sh["id"]}/{ep_key}',
         reels_work=f'{C.REELS}/{sh["id"]}/{ep_key}', rules=C.RULES, show_date=show_day.isoformat() if show_day else None)
ps, pe = C.propose_window(show_day, today); r['window_proposed'] = C.window_dict(ps, pe, at=C.now())
if A.window:
    if not A.by: C.fail('--window needs --by "<Colden\'s words>"')
    s, e = (dt.date.fromisoformat(x) for x in A.window)
    if e < s: C.fail('the window ends before it starts')
    r['window'] = C.window_dict(s, e, confirmed_by=A.by, confirmed_at=C.now())
if A.resolve_window: r['resolve_window'] = {'words': A.resolve_window, 'at': C.now()}
if A.metricool_all:
    if len(A.metricool_all.strip()) < 10: C.fail('--metricool-all needs his words')
    r['metricool_all'] = {'words': A.metricool_all.strip(), 'at': C.now()}        # every reel through Metricool, no manual kits (common.metricool_all)
if A.full_episode:
    ids = dict(zip(('cwc', 'tcl'), A.full_episode[:2]))
    if len(A.full_episode[2].strip()) < 2: C.fail('--full-episode needs his words')
    r['full_episode'] = {'ids': {b: v for b, v in ids.items() if v and v != '-'}, 'words': A.full_episode[2].strip(), 'at': C.now()}
if A.colden_uploads:
    if len(A.colden_uploads.strip()) < 2: C.fail('--colden-uploads needs his words')
    r['colden_uploads'] = {'words': A.colden_uploads.strip(), 'at': C.now()}      # he uploads every YouTube video himself; the API adds the metadata (common.colden_uploads)
if A.post_ok is not None:
    if len(A.post_ok.strip()) < 2: C.fail('--post-ok needs his words')
    r['post_ok'] = {'words': A.post_ok.strip(), 'at': C.now()}
C.save_run(R, r); C.event(R, f'INTAKE {sh["id"]} {ep_key} show {show_day}')
print(f'RUN={R}\n{sh["name"]} {ep_key}, show date {show_day or "not in the folder name"}')
w = r.get('window')
print(f'posting window: {w["start_dow"]} {w["start"]} -> {w["end_dow"]} {w["end"]} (confirmed: {w["confirmed_by"]})' if w and w.get('confirmed_by')
      else f'posting window NOT confirmed - proposal {C.DAYS[ps.weekday()]} {ps} -> {C.DAYS[pe.weekday()]} {pe}: ask Colden (window.py)')
print('Resolve window: ' + (r.get('resolve_window', {}).get('words') or 'none given - the sub-skills ask before each Resolve step'))
print('posting yes: ' + ((r.get('post_ok') or {}).get('words') or 'NOT given - ask it now, with the window'))
print('YouTube uploads: ' + (f'COLDEN uploads every video himself, the API adds the metadata ("{C.colden_uploads(r)}")' if C.colden_uploads(r) else 'the API uploads every video (youtube.py upload)'))
need = []
if not (w and w.get('confirmed_by')):
    need.append(f'the posting window (proposal {C.DAYS[ps.weekday()]} {ps} -> {C.DAYS[pe.weekday()]} {pe}) -> --window YYYY-MM-DD YYYY-MM-DD --by "<his words>"')
if not (r.get('post_ok') or {}).get('words'):
    need.append('the posting yes: "When you tap Schedule all on the plan card, may I post everything on it - including the YouTube '
                'uploads on later days - without asking you here again?" -> --post-ok "<his words>"')
if need:
    C.ask(f'{sh["name"]} {ep_key} - ask Colden NOW, in chat, while he is at the computer (never hours later): '
          + ' AND '.join(need) + f'; then intake.py "{D}" with those flags')
print(f'next: python3 {C.SK}/scripts/next.py "{R}"')
