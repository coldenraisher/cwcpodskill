"""assemble.py <WORK> [theme id ...]   ->  <WORK>/cold/<id>.txt   the short in play order, as a stranger gets it (the ONLY
thing the cold reader sees) + its estimated length."""
import os, sys
import common as C, themes as T
if __name__ == '__main__':
    if len(sys.argv) < 2: C.fail(__doc__)
    W = T.Work(sys.argv[1]); only = sys.argv[2:]; os.makedirs(f'{W.work}/cold', exist_ok=True)
    for th in W.themes()['themes']:
        if only and th['id'] not in only: continue
        try: txt = W.assemble(th); raw, est, _ = W.runtime(th)
        except (KeyError, ValueError, IndexError) as e: C.fail(f'{th.get("id")}: bad range ({e}) - run check.py for the full list')
        open(f'{W.work}/cold/{th["id"]}.txt', 'w').write(txt)
        print(f'{th["id"]}  {est:4.0f} s est.  {len(txt.split())} words  sha {C.sha_text(txt)[:12]}  {th["title"]}')
