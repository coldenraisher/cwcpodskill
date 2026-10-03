"""Re-open a LOCKED episode for a new version - only on Colden's word.
usage: unlock.py <CACHE> --by "<Colden's words>"
Records `rebuild` in the manifest (who said it, when, which cut it replaces). From then on prep.py / plan.py /
build.py / lower_thirds.py run again on this episode; the locked cut and its frozen snapshot are not touched. When the
new cut is locked (lock.py), the old lock moves to `lock_history` and `rebuild` is cleared."""
import os, sys, time, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
ap = argparse.ArgumentParser(); ap.add_argument('cache'); ap.add_argument('--by', required=True); A = ap.parse_args()
m = C.manifest(A.cache); assert m.get('locked'), 'this episode is not locked - nothing to re-open'
assert len(A.by.split()) >= 2, "--by takes Colden's own words"
m['rebuild'] = {'by': A.by, 'at': time.strftime('%Y-%m-%d %H:%M'), 'of': m['locked']['timeline']}; C.save(f'{A.cache}/manifest.json', m)
print(f"re-opened: a new version of {m['locked']['timeline']} may be planned and built ({A.by}). The locked cut stays as it is until the new one is locked.")
