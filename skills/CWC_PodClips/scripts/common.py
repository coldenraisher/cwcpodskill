"""Shared helpers for CWC_PodClips: paths, show files, the episode record, time mapping, hashing, exit codes.

Two clocks, both in seconds:
  BASE = seconds of the PROGRAM file (what CWC_PodCut times everything on; words.json is on it)
  CUT  = seconds on the locked PodCut timeline (what Colden sees in Resolve; what every timecode in this skill shows)
The locked plan (snapshot plan.json: segments srcStart/srcEnd -> outStart/outEnd) maps one to the other.

Exit codes of every script:  0 = done   2 = STOP AND ASK COLDEN (never work around)   anything else = a gate failed:
read the message and fix the cause."""
import os, re, sys, json, copy, fcntl, hashlib, bisect, datetime, contextlib

SK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.environ.get('CWC_ROOT') or os.path.expanduser('~/Documents/Claude/Projects/Create with Colden/CWC Podcast')
PODCUT_CACHE = f'{ROOT}/work/cache'      # CWC_PodCut's cache: READ-ONLY from this skill
CLIPS = f'{ROOT}/clips'                  # this skill's work: clips/<show>/<EpNN>/
DATA = f'{ROOT}/data'                    # channel data, decisions, learnings (shared by every episode)
YT_CFG = os.path.expanduser('~/.config/edit-clips/youtube')    # OAuth tokens made by edit-clips (cwc.json, tcl.json)
SCRAPE = [os.path.expanduser('~/Documents/Claude/Projects/Create with Colden/trend_research/channel_metrics.json'),
          os.path.expanduser('~/Documents/Claude/CreateWithColden/trend_research/channel_metrics.json')]   # weekly Studio scrape (Mondays)
TREND = os.path.expanduser('~/Documents/Claude/CreateWithColden/trend_research')                          # daily trend scanner (read-only)
RULES = '2026-10-01b'                    # bump when a gate changes: check.py refuses a checked.json of another version

def load(path, default=None):
    return json.load(open(path)) if os.path.exists(path) else default

def save(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f'{path}.{os.getpid()}.tmp'                               # per process: two writers never share a temp file
    with open(tmp, 'w') as f: json.dump(obj, f, indent=1, ensure_ascii=False)
    os.replace(tmp, path)

_depth = [0, None]
@contextlib.contextmanager
def locked():
    """ONE lock for every read-modify-write of a state file (review/state.json, edit/review.json, package/review.json,
    versions.json, copy / thumbs records): the detached listener and the CLI scripts write the same files, and a
    handler that saved the copy it read before its network calls erased what the other side wrote meanwhile (bug
    sweep 2026-10-02). Re-entrant inside one process."""
    if _depth[0] == 0:
        d = os.path.expanduser('~/.config/cwc'); os.makedirs(d, exist_ok=True); _depth[1] = open(f'{d}/state.lock', 'w'); fcntl.flock(_depth[1], fcntl.LOCK_EX)
    _depth[0] += 1
    try: yield
    finally:
        _depth[0] -= 1
        if _depth[0] == 0: fcntl.flock(_depth[1], fcntl.LOCK_UN); _depth[1].close(); _depth[1] = None
def update(path, fn, default=None):
    """read -> fn(obj) mutates it IN PLACE (its return value is ignored) -> save, all under the lock, with NO network
    call inside. The rule for every handler: answer Telegram first, then update()."""
    with locked():
        obj = load(path, copy.deepcopy(default)); fn(obj); save(path, obj); return obj

# ---- whose notes is the next plain message? ONE pointer for the whole bot: the last Notes / Changes tap wins ----
def _aw(): return f'{DATA}/awaiting_notes.json'
def set_awaiting(kind, work, key): save(_aw(), {'kind': kind, 'work': os.path.abspath(work), 'key': key, 'at': now()})
def awaiting(kind, work):
    a = load(_aw())
    return a['key'] if a and a.get('kind') == kind and a.get('work') == os.path.abspath(work) else None
def clear_awaiting(kind=None, work=None, key=None):
    a = load(_aw())
    if a and (kind is None or (a.get('kind') == kind and a.get('work') == os.path.abspath(work) and (key is None or a.get('key') == key))): save(_aw(), None)
def listener_alive():
    try: os.kill(int(open(os.path.expanduser('~/.config/cwc/tg_listen.pid')).read().strip()), 0); return True
    except Exception: return False
def need_listener():
    """a card is never sent while nobody is listening (ruling 34): its buttons would spin until a session notices"""
    if not listener_alive(): fail('the Telegram listener is not running - start it first: tg_listen.py start')

def sha_text(s): return hashlib.sha1(s.encode('utf-8')).hexdigest()
def sha_file(p): return hashlib.sha1(open(p, 'rb').read()).hexdigest()
def now(): return datetime.datetime.now().astimezone().isoformat(timespec='seconds')
def age_hours(iso):
    return (datetime.datetime.now().astimezone() - datetime.datetime.fromisoformat(iso)).total_seconds() / 3600

def ask(msg):
    print(f'\nASK COLDEN (exit 2): {msg}', file=sys.stderr); sys.exit(2)
def fail(msg):
    print(f'\nGATE FAILED: {msg}', file=sys.stderr); sys.exit(1)

BUILT = ('draft', 'approved')                                    # a version build.py VERIFIED (not 'building' / 'failed' / 'superseded')
def vpath(work, tid): return f'{work}/edit/{tid}/versions.json'
def newest_built(work, tid, ch=None):
    """the newest VERIFIED version of a theme (of one channel) - a failed or unfinished build is never reviewed or sent"""
    mine = [v for v in load(vpath(work, tid), []) if (not ch or v['channel'] == ch) and not str(v.get('status', '')).startswith('superseded')]
    if not mine: fail(f'no built version of {tid}' + (f' for {ch}' if ch else '') + ' - build.py first')
    if mine[-1].get('status') not in BUILT:             # never fall back to an older version: the newest one is what he is waiting for
        fail(f'{tid} {mine[-1]["channel"]} v{mine[-1]["v"]} is "{mine[-1].get("status")}", not verified - fix and build again (an unverified build is never reviewed or sent)')
    return mine[-1]
def set_version(work, tid, ch, vn, **fields):
    """update ONE row of versions.json, read right before the write: the always-on listener writes approvals into the
    same file while a render or a check runs for minutes - holding the list across that would undo his tap"""
    with locked():
        vs = load(vpath(work, tid), []); row = next((x for x in vs if x['v'] == vn and x['channel'] == ch), None)
        if row is None: fail(f'{tid} {ch} v{vn} is not in versions.json')
        row.update(fields); save(vpath(work, tid), vs); return row
DEAD = ('superseded', 'rejected', 'failed', 'dropped')           # a version nobody may approve, review, master or lock any more
def live(v): return not str(v.get('status', '')).startswith(DEAD)

def show(show_id):
    p = f'{SK}/shows/{show_id}.json'
    if not os.path.exists(p): ask(f'no show file for "{show_id}" in {SK}/shows - a new show needs its channels, hosts and assets from Colden first')
    return json.load(open(p))

def work_dir(show_id, ep_key): return f'{CLIPS}/{show_id}/{ep_key}'
def episode(work):
    e = load(f'{work}/episode.json')
    if not e: fail(f'no episode.json in {work} - run intake.py first')
    return e

def hms(t):
    t = max(0.0, float(t)); h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f'{h}:{m:02d}:{s:04.1f}' if h else f'{m}:{s:04.1f}'
def mmss(t):
    t = int(round(max(0.0, float(t)))); return f'{t // 60}:{t % 60:02d}'
def stamp(t):
    """a YouTube chapter timestamp: FLOORED (a chapter must not start after its first word)"""
    t = int(max(0.0, float(t))); return f'{t // 3600}:{t % 3600 // 60:02d}:{t % 60:02d}' if t >= 3600 else f'{t // 60}:{t % 60:02d}'
def clock(t):
    """m:ss, or h:mm:ss past the hour - the timecode Colden reads on the timeline"""
    t = int(round(max(0.0, float(t)))); return f'{t // 3600}:{t % 3600 // 60:02d}:{t % 60:02d}' if t >= 3600 else f'{t // 60}:{t % 60:02d}'
def parse_tc(s):
    """'1:02:03.5' / '12:34' / '75.2' -> seconds"""
    parts = [float(x) for x in str(s).strip().split(':')]; t = 0.0
    for p in parts: t = t * 60 + p
    return t

class CutMap:
    """BASE <-> CUT through the locked plan's segments"""
    def __init__(self, plan):
        self.seg = sorted(plan['segments'], key=lambda s: s['srcStart']); self.src = [s['srcStart'] for s in self.seg]
        self.out = [s['outStart'] for s in self.seg]; self.duration = max(s['outEnd'] for s in self.seg)
    def to_cut(self, t):
        """cut second of base second t, or None when the plan removed it / it is outside the cut"""
        i = bisect.bisect_right(self.src, t) - 1
        if i < 0: return None
        s = self.seg[i]
        return s['outStart'] + (t - s['srcStart']) if t <= s['srcEnd'] + 1e-6 else None
    def to_base(self, c):
        i = max(0, bisect.bisect_right(self.out, c) - 1); s = self.seg[i]
        return s['srcStart'] + min(c - s['outStart'], s['srcEnd'] - s['srcStart'])
    def camera_at(self, c):
        i = max(0, bisect.bisect_right(self.out, c) - 1); return self.seg[i].get('name')

def norm(s):
    """for quote matching: lower-case words only (punctuation, case and spacing never decide a match)"""
    return re.sub(r"[^a-z0-9' ]", ' ', s.lower().replace('’', "'")).split()

def contains_seq(hay, needle):
    n = len(needle)
    return n > 0 and any(hay[i:i + n] == needle for i in range(len(hay) - n + 1))

def union_len(spans):
    tot = 0.0; end = None
    for a, b in sorted(spans):
        if end is None or a > end: tot += b - a; end = b
        elif b > end: tot += b - end; end = b
    return tot

def overlap_len(a_spans, b_spans):
    """seconds of a_spans also covered by b_spans (both lists of [start, end])"""
    return union_len(a_spans) + union_len(b_spans) - union_len(list(a_spans) + list(b_spans))
