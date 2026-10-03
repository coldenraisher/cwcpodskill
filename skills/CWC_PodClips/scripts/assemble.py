"""assemble.py <WORK> [theme id ...]   ->  <WORK>/cold/<id>.txt  (+ prints its hash and estimated runtime)
The clip in PLAY order, as a stranger would get it. The cold-read reviewer is given exactly this text (coldread.py prompt assembles it again from themes.json, so the file can never be stale for the reader); Stage 2 reads the file when choosing b-roll - run assemble.py after every change of a theme."""
import os, sys
import common as C, themes as T
if __name__ == '__main__':
    if len(sys.argv) < 2: C.fail(__doc__)
    W = T.Work(sys.argv[1]); only = sys.argv[2:]; os.makedirs(f'{W.work}/cold', exist_ok=True)
    for th in W.themes()['themes']:
        if only and th['id'] not in only: continue
        try: txt = W.assemble(th); raw, est = W.runtime(th)
        except (KeyError, ValueError) as e: C.fail(f'{th.get("id")}: bad range ({e}) - run check.py for the full list')
        open(f'{W.work}/cold/{th["id"]}.txt', 'w').write(txt)
        print(f'{th["id"]}  {C.mmss(est)} est.  {len(txt.split())} words  sha {C.sha_text(txt)[:12]}  {W.work}/cold/{th["id"]}.txt')
