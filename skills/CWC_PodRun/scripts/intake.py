"""intake.py "<episode folder>" [--show creative-lens] [--resolve-window "<Colden's words>"] [--start YYYY-MM-DD]
An episode folder on the NAS -> a RUN folder (run/<show>/<EpNN>/run.json) that knows where every skill of the pipeline
keeps this episode: CWC_PodCut's cache, CWC_PodClips' WORK, CWC_PodReels' WORK, the posting window.
Show + episode key are found exactly the way CWC_PodCut's intake.py finds them (its show files: nas_root, episode_pattern),
so every skill lands on the same <show>/<EpNN>.
  --resolve-window  the window Colden gave for unattended Resolve work ("Resolve is yours until 2am"). Without one the
                    sub-skills ask before every Resolve build / render (their own safety rule).
  --start           first posting day. Default: the day after the show date in the folder name ("Ep. 24 - 10:1" = Oct 1,
                    a Thursday -> Friday Oct 2); no date in the name -> the next Friday (Colden 2026-10-03: Friday -> Thursday).
exit 0 = run.json written (re-running keeps what is already recorded); 2 = ask (which show / folder missing)."""
import os, sys, argparse, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

ap = argparse.ArgumentParser(); ap.add_argument('episode'); ap.add_argument('--show'); ap.add_argument('--resolve-window'); ap.add_argument('--start')
A = ap.parse_args()
D = A.episode.rstrip('/')
if not os.path.isdir(D): C.ask(f'not a folder (is the NAS mounted?): {D}')
sh = next((s for s in C.shows() if s['id'] == A.show), None) if A.show else next((s for s in C.shows() if D.startswith(s['nas_root'])), None)
if not sh: C.ask(f'which show is {D}? pass --show ({", ".join(s["id"] for s in C.shows())})')
ep_key, ep_no = C.ep_key_for(sh, D)
R = C.run_dir(sh['id'], ep_key); os.makedirs(R, exist_ok=True)
r = C.load(f'{R}/run.json') or {'created': C.now(), 'stages': {}}

rule = C.rules(); today = dt.datetime.now(C.ET).date()
start = dt.date.fromisoformat(A.start) if A.start else (r.get('window') or {}).get('start')
if isinstance(start, str): start = dt.date.fromisoformat(start)
show_day = C.show_date(os.path.basename(D), today)
if not start and show_day:
    start = show_day + dt.timedelta(days=1)           # the day after the live show (Thursday show -> Friday)
if not start:                                         # no date in the folder name: the next Friday, today when it is Friday
    dow = C.DAYS.index(rule['window_start_dow']); start = today + dt.timedelta(days=(dow - today.weekday()) % 7)
if C.DAYS[start.weekday()] != rule['window_start_dow']:
    print(f'NOTE: the window starts on a {C.DAYS[start.weekday()]}, not a {rule["window_start_dow"]} (show day {show_day}) - tell Colden on the plan card')
end = start + dt.timedelta(days=rule['window_days'] - 1)

r.update(show=sh['id'], show_name=sh['name'], ep_key=ep_key, ep_no=ep_no, episode_dir=D, episode_name=os.path.basename(D),
         podcut_cache=f'{C.PODCUT_CACHE}/{sh["id"]}/{ep_key}', clips_work=f'{C.CLIPS}/{sh["id"]}/{ep_key}',
         reels_work=f'{C.REELS}/{sh["id"]}/{ep_key}', rules=C.RULES,
         show_date=show_day.isoformat() if show_day else None,
         window={'start': start.isoformat(), 'end': end.isoformat(), 'start_dow': C.DAYS[start.weekday()], 'end_dow': C.DAYS[end.weekday()]})
if A.resolve_window: r['resolve_window'] = {'words': A.resolve_window, 'at': C.now()}
C.save_run(R, r); C.event(R, f'INTAKE {sh["id"]} {ep_key} window {start} -> {end}')
print(f'RUN={R}\n{sh["name"]} {ep_key}: posting window {C.DAYS[start.weekday()]} {start} -> {C.DAYS[end.weekday()]} {end}')
print('Resolve window: ' + (r.get('resolve_window', {}).get('words') or 'none given - the sub-skills ask before each Resolve step'))
print(f'next: python3 {C.SK}/scripts/next.py "{R}"')
