"""intake.py "<episode folder>" [--show creative-lens] [--resolve-window "<Colden's words>"]
          [--window YYYY-MM-DD YYYY-MM-DD --by "<Colden's words>"]
An episode folder on the NAS -> a RUN folder (run/<show>/<EpNN>/run.json) that knows where every skill of the pipeline
keeps this episode: CWC_PodCut's cache, CWC_PodClips' WORK, CWC_PodReels' WORK, the show date, the posting window.
Show + episode key are found exactly the way CWC_PodCut's intake.py finds them (its show files: nas_root, episode_pattern),
so every skill lands on the same <show>/<EpNN>. The show date comes from the folder name ("Ep. 24 - 10:1" = Oct 1).
  --resolve-window  the window Colden gave for unattended Resolve work ("Resolve is yours until 2am"). Without one the
                    sub-skills ask before every Resolve build / render (their own safety rule).
  --window          the posting span Colden gave at kickoff (ruling: ask first, never assume - window.py). Without it the
                    run only holds a PROPOSAL; plan.py will not build until he confirms one.
exit 0 = run.json written (re-running keeps what is already recorded); 2 = ask (which show / folder missing)."""
import os, sys, argparse, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

ap = argparse.ArgumentParser(); ap.add_argument('episode'); ap.add_argument('--show'); ap.add_argument('--resolve-window')
ap.add_argument('--window', nargs=2, metavar=('START', 'END')); ap.add_argument('--by')
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
C.save_run(R, r); C.event(R, f'INTAKE {sh["id"]} {ep_key} show {show_day}')
print(f'RUN={R}\n{sh["name"]} {ep_key}, show date {show_day or "not in the folder name"}')
w = r.get('window')
print(f'posting window: {w["start_dow"]} {w["start"]} -> {w["end_dow"]} {w["end"]} (confirmed: {w["confirmed_by"]})' if w and w.get('confirmed_by')
      else f'posting window NOT confirmed - proposal {C.DAYS[ps.weekday()]} {ps} -> {C.DAYS[pe.weekday()]} {pe}: ask Colden (window.py)')
print('Resolve window: ' + (r.get('resolve_window', {}).get('words') or 'none given - the sub-skills ask before each Resolve step'))
print(f'next: python3 {C.SK}/scripts/next.py "{R}"')
