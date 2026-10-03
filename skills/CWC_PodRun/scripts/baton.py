"""baton.py take <owner> "<what>" | give <owner> | status       the RESOLVE BATON for the tandem run
CWC_PodClips and CWC_PodReels run at the same time on the same Resolve project. Their rs.py calls already queue on the
shared lock (~/.config/amira/resolve.lock), but that lock covers ONE call: a build or a render is many calls and makes
its timeline the current one, so the other skill's next call could land on the wrong timeline. The baton is held for a
whole Resolve SEQUENCE (build.py, review.py render, master.py render, cover.py resolve, lock.py) and given back after.
  take    exit 0 = yours (or already yours); 4 = another skill holds it (prints who / what / since) - do non-Resolve work
          and try again; a baton older than 3 h is reported as stale and is never taken over without Colden's words:
          take <owner> "<what>" --steal "<his words>"
  give    exit 0; refuses (1) when another owner holds it
The baton only orders the two skills; Colden's own use of Resolve is still asked about (their safety rule 1)."""
import os, sys, json, time, fcntl
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
F = f'{C.CFG}/resolve_baton.json'; STALE_H = 3

def locked(fn):
    os.makedirs(C.CFG, exist_ok=True)
    with open(f'{F}.lock', 'w') as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        return fn(C.load(F))

def main():
    a = sys.argv[1:]
    if not a or a[0] not in ('take', 'give', 'status'): print(__doc__); sys.exit(1)
    if a[0] == 'status':
        b = C.load(F); print(json.dumps(b, indent=1) if b else 'free'); return
    owner = a[1] if len(a) > 1 else C.fail('owner missing (CWC_PodClips | CWC_PodReels | CWC_PodCut)')
    if a[0] == 'take':
        what = a[2] if len(a) > 2 else ''; steal = a[a.index('--steal') + 1] if '--steal' in a else None
        def take(b):
            if b and b['owner'] != owner:
                age = (time.time() - b['t']) / 3600
                if not steal:
                    print(f'HELD by {b["owner"]} ({b["what"]}) since {b["at"]}' + (f' - STALE ({age:.1f} h): ask Colden before --steal' if age > STALE_H else ''))
                    return 4
                print(f'taken from {b["owner"]} on Colden\'s words: {steal}')
            C.save(F, {'owner': owner, 'what': what, 'at': C.now(), 't': time.time(), 'pid': os.getppid(), 'steal': steal})
            print(f'baton: {owner} ({what})'); return 0
        sys.exit(locked(take))
    def give(b):
        if b and b['owner'] != owner: print(f'not yours: {b["owner"]} holds it'); return 1
        if os.path.exists(F): os.remove(F)
        print('baton free'); return 0
    sys.exit(locked(give))

if __name__ == '__main__': main()
