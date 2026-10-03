"""baton.py open <RUN> | close | take <owner> "<what>" [--steal "<his words>"] | give <owner> | status
THE RESOLVE BATON: one skill in Resolve at a time during the tandem run (Colden 2026-10-03: "begin running /cwcpodclips
and cwcpodreels skills at the same time"). Their rs.py calls already queue on the shared lock
(~/.config/amira/resolve.lock), but that lock covers ONE call: a build or a render is many calls and makes its timeline
the current one, so the other skill's next call could land on the wrong timeline. The baton is held for a whole Resolve
SEQUENCE (build.py, review.py render, master.py render, cover.py resolve, lock.py) and given back after.
THE GATE IS IN CODE: rs.py of CWC_PodClips, CWC_PodReels and this skill reads ~/.config/cwc/resolve_baton.json before
every Resolve call and refuses (exit 4) unless its own skill holds the baton. No file = no tandem run = no check, so
each skill still runs alone exactly as before.
  open    the tandem run starts (PodCut locked, both workers about to start): the file exists from now on, nobody holds it
  take    exit 0 = yours (or already yours); 4 = another skill holds it (prints who / what / since) - do non-Resolve work
          and try again. A baton older than 3 h is reported as stale and is never taken over without Colden's words:
          take <owner> "<what>" --steal "<his words>"
  give    exit 0; refuses (1) when another owner holds it. In a tandem run the file stays (free); outside one it is removed
  close   the tandem run is over (both skills delivered): the file is removed. Refuses (1) while a skill holds the baton
The baton only orders the skills; Colden's own use of Resolve is still asked about (their safety rule 1)."""
import os, sys, json, time, fcntl
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
F = f'{C.CFG}/resolve_baton.json'; STALE_H = 3
OWNERS = ('CWC_PodClips', 'CWC_PodReels', 'CWC_PodRun')

def locked(fn):
    os.makedirs(C.CFG, exist_ok=True)
    with open(f'{F}.lock', 'w') as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        return fn(C.load(F))

def free(b): return {'tandem': b.get('tandem'), 'owner': None, 'what': None, 'at': C.now(), 't': time.time()}

def main():
    a = sys.argv[1:]
    if not a or a[0] not in ('open', 'close', 'take', 'give', 'status'): print(__doc__); sys.exit(1)
    if a[0] == 'status':
        b = C.load(F); print(json.dumps(b, indent=1) if b else 'no baton file (no tandem run: rs.py checks nothing)'); return
    if a[0] == 'open':
        R = a[1].rstrip('/') if len(a) > 1 else C.fail('open <RUN>')
        C.run(R)
        def op(b):
            b = dict(b or {'owner': None, 'what': None, 'at': C.now(), 't': time.time()}, tandem={'run': R, 'at': C.now()})
            C.save(F, b); print(f'tandem run open for {R}: every Resolve call of CWC_PodClips / CWC_PodReels / CWC_PodRun now needs the baton' + (f' (held by {b["owner"]})' if b.get('owner') else '')); return 0
        sys.exit(locked(op))
    if a[0] == 'close':
        def cl(b):
            if b and b.get('owner'): print(f'still held by {b["owner"]} ({b.get("what")}) since {b.get("at")} - give it back first'); return 1
            if os.path.exists(F): os.remove(F)
            print('tandem run closed: no baton file, rs.py checks nothing'); return 0
        sys.exit(locked(cl))
    owner = a[1] if len(a) > 1 else C.fail(f'owner missing ({" | ".join(OWNERS)})')
    if owner not in OWNERS: C.fail(f'owner must be one of {", ".join(OWNERS)} - rs.py compares this name')
    if a[0] == 'take':
        what = a[2] if len(a) > 2 and not a[2].startswith('--') else ''; steal = a[a.index('--steal') + 1] if '--steal' in a else None
        def take(b):
            b = b or {}
            if b.get('owner') and b['owner'] != owner:
                age = (time.time() - b['t']) / 3600
                if not steal:
                    print(f'HELD by {b["owner"]} ({b["what"]}) since {b["at"]}' + (f' - STALE ({age:.1f} h): ask Colden before --steal' if age > STALE_H else ''))
                    return 4
                print(f'taken from {b["owner"]} on Colden\'s words: {steal}')
            C.save(F, {'tandem': b.get('tandem'), 'owner': owner, 'what': what, 'at': C.now(), 't': time.time(), 'steal': steal})
            print(f'baton: {owner} ({what})'); return 0
        sys.exit(locked(take))
    def give(b):
        if b and b.get('owner') and b['owner'] != owner: print(f'not yours: {b["owner"]} holds it'); return 1
        if b and b.get('tandem'): C.save(F, free(b)); print('baton free (tandem run still open)')
        else:
            if os.path.exists(F): os.remove(F)
            print('baton free')
        return 0
    sys.exit(locked(give))

if __name__ == '__main__': main()
