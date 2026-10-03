"""Shared helpers for CWC_PodReels: paths, show files, the episode record, time mapping, hashing, exit codes.

Two clocks, both in seconds (the same as CWC_PodClips - the locked PodCut is the common source):
  BASE = seconds of the PROGRAM file (what CWC_PodCut times everything on; words.json is on it)
  CUT  = seconds on the locked PodCut timeline (what Colden sees in Resolve; every timecode this skill shows)
The locked plan (snapshot plan.json: segments srcStart/srcEnd -> outStart/outEnd) maps one to the other.

Exit codes of every script:  0 = done   2 = STOP AND ASK COLDEN (never work around)   anything else = a gate failed:
read the message and fix the cause. CWC_PodCut, CWC_PodClips, edit-shorts, the AMIRA skills are READ-ONLY from here."""
import os, re, sys, json, hashlib, bisect, datetime

SK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.environ.get('CWC_ROOT') or os.path.expanduser('~/Documents/Claude/Projects/Create with Colden/CWC Podcast')
PODCUT_CACHE = f'{ROOT}/work/cache'      # CWC_PodCut's cache: READ-ONLY
REELS = f'{ROOT}/reels'                  # this skill's work: reels/<show>/<EpNN>/
DATA = f'{ROOT}/data/shorts'             # short-form data, decisions, learnings (every episode)
YT_CFG = os.path.expanduser('~/.config/edit-clips/youtube')    # OAuth tokens made by edit-clips (cwc.json, tcl.json) - read + refresh only
SCRAPE = [os.path.expanduser('~/Documents/Claude/CreateWithColden/trend_research/channel_metrics.json'),
          os.path.expanduser('~/Documents/Claude/Projects/Create with Colden/trend_research/channel_metrics.json')]   # Monday Studio scrape
TREND = os.path.expanduser('~/Documents/Claude/CreateWithColden/trend_research')                                # daily trend scanner (read-only)
CFG = os.path.expanduser('~/.config/cwc')                     # shared with CWC_PodClips (Telegram pairing, listener)
RULES = '2026-10-02a'                    # bump when a gate changes: check.py refuses a checked.json of another version

def load(path, default=None):
    return json.load(open(path)) if path and os.path.exists(path) else default

def save(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + '.tmp'; json.dump(obj, open(tmp, 'w'), indent=1, ensure_ascii=False); os.replace(tmp, path)

def sha_text(s): return hashlib.sha1(s.encode('utf-8')).hexdigest()
def sha_file(p): return hashlib.sha1(open(p, 'rb').read()).hexdigest()
def now(): return datetime.datetime.now().astimezone().isoformat(timespec='seconds')
def age_hours(iso):
    return (datetime.datetime.now().astimezone() - datetime.datetime.fromisoformat(iso)).total_seconds() / 3600

def ask(msg):
    print(f'\nASK COLDEN (exit 2): {msg}', file=sys.stderr); sys.exit(2)
def fail(msg):
    print(f'\nGATE FAILED: {msg}', file=sys.stderr); sys.exit(1)

def show(show_id):
    p = f'{SK}/shows/{show_id}.json'
    if not os.path.exists(p): ask(f'no show file for "{show_id}" in {SK}/shows - a new show needs its channels, hosts and publishing from Colden first')
    return json.load(open(p))

def work_dir(show_id, ep_key): return f'{REELS}/{show_id}/{ep_key}'
def works():
    import glob
    return sorted(os.path.dirname(p) for p in glob.glob(f'{REELS}/*/*/episode.json'))
def episode(work):
    e = load(f'{work}/episode.json')
    if not e: fail(f'no episode.json in {work} - run intake.py first')
    return e

def hms(t):
    t = max(0.0, float(t)); h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f'{h}:{m:02d}:{s:04.1f}' if h else f'{m}:{s:04.1f}'
def mmss(t):
    t = int(round(max(0.0, float(t)))); return f'{t // 60}:{t % 60:02d}'
def clock(t):
    t = int(round(max(0.0, float(t)))); return f'{t // 3600}:{t % 3600 // 60:02d}:{t % 60:02d}' if t >= 3600 else f'{t // 60}:{t % 60:02d}'
def parse_tc(s):
    parts = [float(x) for x in str(s).strip().split(':')]; t = 0.0
    for p in parts: t = t * 60 + p
    return t

class CutMap:
    """BASE <-> CUT through the locked plan's segments"""
    def __init__(self, plan):
        self.seg = sorted(plan['segments'], key=lambda s: s['srcStart']); self.src = [s['srcStart'] for s in self.seg]
        self.out = [s['outStart'] for s in self.seg]; self.duration = max(s['outEnd'] for s in self.seg)
    def to_cut(self, t):
        i = bisect.bisect_right(self.src, t) - 1
        if i < 0: return None
        s = self.seg[i]
        return s['outStart'] + (t - s['srcStart']) if t <= s['srcEnd'] + 1e-6 else None
    def to_base(self, c):
        i = max(0, bisect.bisect_right(self.out, c) - 1); s = self.seg[i]
        return s['srcStart'] + min(c - s['outStart'], s['srcEnd'] - s['srcStart'])

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
    return union_len(a_spans) + union_len(b_spans) - union_len(list(a_spans) + list(b_spans))

# Colden's name as Whisper hears it (memory 2026-09-28): every search for him matches these
COLDEN_RE = r'\b(colden|colton|coldon|colten|kolden|cold in)\b'

TL_BAD = '?*/\\:"<>|'
def tl_name(t):
    """Resolve refuses these characters in a timeline name (DuplicateTimeline returns None); SMB refuses them in files"""
    return re.sub(r'\s+', ' ', ''.join(ch for ch in t if ch not in TL_BAD)).strip()

def event(W, line):
    os.makedirs(f'{W}/review', exist_ok=True)
    with open(f'{W}/review/events.log', 'a') as f: f.write(f'{now()} {line}\n')
    print(line, flush=True)

def decision(W, row):
    """every tap and note -> data/shorts/decisions.jsonl (learn.py reads it)"""
    os.makedirs(DATA, exist_ok=True); ep = episode(W)
    row = dict({'at': now(), 'show': ep['show'], 'ep': ep['ep_key'], 'trial': bool(ep.get('trial'))}, **row)
    with open(f'{DATA}/decisions.jsonl', 'a') as f: f.write(json.dumps(row, ensure_ascii=False) + '\n')

SHOW_CODE = {'creative-lens': 'cl', 'colden-todd': 'ct'}
def epk(ep):
    """the episode's short key inside Telegram callback data (64-byte limit): cl24 / ct07"""
    return SHOW_CODE.get(ep['show'], ep['show'][:2]) + str(ep.get('ep_no') or ep['ep_key'])
