"""Shared helpers for CWC_PodRun (the aggregator): paths, the run state, the other skills' state files (READ-ONLY),
exits, time. Everything here is stdlib; youtube.py imports the Google client lazily.
Exit codes as the rest of the pipeline: 0 done - 2 STOP AND ASK COLDEN - anything else a gate failed."""
import os, re, sys, json, time, hashlib, datetime as dt
from zoneinfo import ZoneInfo

SK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.environ.get('CWC_ROOT') or os.path.expanduser('~/Documents/Claude/Projects/Create with Colden/CWC Podcast')
SKILLS = os.environ.get('CWC_SKILLS') or os.path.expanduser('~/.claude/skills')
PODCUT_SK, CLIPS_SK, REELS_SK = (f'{SKILLS}/CWC_PodCut', f'{SKILLS}/CWC_PodClips', f'{SKILLS}/CWC_PodReels')
PODCUT_CACHE = f'{ROOT}/work/cache'     # CWC_PodCut's cache: READ-ONLY
CLIPS = f'{ROOT}/clips'                 # CWC_PodClips WORK: READ-ONLY
REELS = f'{ROOT}/reels'                 # CWC_PodReels WORK: READ-ONLY
RUNS = f'{ROOT}/run'                    # this skill's work: run/<show>/<EpNN>/
DATA = f'{ROOT}/data'                   # shared with CWC_PodClips (quota.json lives here)
CFG = os.path.expanduser('~/.config/cwc')            # Telegram pairing + listener plugins (shared)
YT_CFG = os.path.expanduser('~/.config/edit-clips/youtube')   # OAuth tokens cwc.json / tcl.json (read + refresh)
SCRAPE = [os.environ['CWC_SCRAPE']] if os.environ.get('CWC_SCRAPE') else [os.path.expanduser('~/Documents/Claude/Projects/Create with Colden/trend_research/channel_metrics.json'),
          os.path.expanduser('~/Documents/Claude/CreateWithColden/trend_research/channel_metrics.json')]   # Monday scrape (both homes)
ET = ZoneInfo('America/New_York')
RULES = '2026-10-03a'                   # bump when a gate changes: plan.py refuses an approval made under other rules

# ------------------------------------------------------------------ exits
def fail(msg): print(f'GATE: {msg}', file=sys.stderr); sys.exit(1)
def ask(msg): print(f'ASK COLDEN: {msg}', file=sys.stderr); sys.exit(2)

# ------------------------------------------------------------------ files
def load(p, default=None):
    try:
        with open(p, encoding='utf-8') as f: return json.load(f)
    except FileNotFoundError: return default
def save(p, data):
    os.makedirs(os.path.dirname(p), exist_ok=True); tmp = f'{p}.tmp'
    with open(tmp, 'w', encoding='utf-8') as f: json.dump(data, f, indent=1, ensure_ascii=False); f.write('\n')
    os.replace(tmp, p)
def sha(obj): return hashlib.sha1(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12]
def mtime(p): return os.path.getmtime(p) if os.path.exists(p) else 0
def rules(): return load(f'{SK}/references/rules.json')
def brands(): return load(f'{SK}/references/brands.json')

# ------------------------------------------------------------------ time
def now(): return dt.datetime.now(ET).isoformat(timespec='seconds')
def et(iso): d = dt.datetime.fromisoformat(iso); return d if d.tzinfo else d.replace(tzinfo=ET)
def hours_old(p): return (time.time() - mtime(p)) / 3600 if os.path.exists(p) else 1e9
DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

# ------------------------------------------------------------------ shows + runs
def shows():
    d = f'{PODCUT_SK}/shows'
    if not os.path.isdir(d): ask(f'CWC_PodCut is not installed at {PODCUT_SK} (its show files say which show a NAS folder is)')
    return [load(f'{d}/{f}') for f in sorted(os.listdir(d)) if f.endswith('.json')]
def ep_key_for(show, folder):
    """the same key CWC_PodCut's intake.py makes: Ep<NN> from the show's episode_pattern, else the folder name"""
    name = os.path.basename(folder.rstrip('/'))
    m = re.match(show['episode_pattern'], name) if show.get('episode_pattern') else None
    return (f'Ep{m.group(1)}', m.group(1)) if m else (re.sub(r'[^A-Za-z0-9]+', '_', name).strip('_'), None)
def show_date(folder_name, today):
    """'Ep. 24 - 10:1' -> 2026-10-01 (month:day at the end of the folder name; ':' may have become '-' or '/')"""
    m = re.search(r'(\d{1,2})[:/._-](\d{1,2})\s*$', folder_name)
    if not m: return None
    try: d = dt.date(today.year, int(m.group(1)), int(m.group(2)))
    except ValueError: return None
    return d.replace(year=d.year - 1) if d > today + dt.timedelta(days=7) else d
def run_dir(show_id, ep_key): return f'{RUNS}/{show_id}/{ep_key}'
def run(R):
    r = load(f'{R}/run.json')
    if not r: fail(f'{R} is not a run folder (no run.json) - intake.py "<episode folder>" first')
    return r
def save_run(R, r): save(f'{R}/run.json', r)
def event(R, line):
    with open(f'{R}/events.log', 'a', encoding='utf-8') as f: f.write(f'{now()} {line}\n')
def runs():
    out = []
    for show in (os.listdir(RUNS) if os.path.isdir(RUNS) else []):
        for ep in os.listdir(f'{RUNS}/{show}'):
            if os.path.exists(f'{RUNS}/{show}/{ep}/run.json'): out.append(f'{RUNS}/{show}/{ep}')
    return out

# ------------------------------------------------------------------ the other skills' state (read-only)
def podcut_manifest(r): return load(f'{r["podcut_cache"]}/manifest.json')
def clips_delivery(r): return load(f'{r["clips_work"]}/delivery.json')
def reels_delivery(r): return load(f'{r["reels_work"]}/delivery.json')
def scrape():
    """the Monday Studio scrape, the newer of its two homes"""
    best = None
    for p in SCRAPE:
        d = load(p)
        if d and (not best or str(d.get('updated', '')) > str(best[1].get('updated', ''))): best = (p, d)
    return best or (None, None)
