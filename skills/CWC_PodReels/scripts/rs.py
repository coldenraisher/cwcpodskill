"""Run a Resolve script from Bash with a hard timeout (macOS has no `timeout`; an MCP call idles 30 min on a hang).
usage: python3 rs.py <seconds> <script.py> [NAME=<json> ...]   - the script sees `resolve`, `project`, `pm`, `mp` and
every NAME as a global; it sets `result`, which is printed as one JSON line (the LAST line of stdout).
Needs Resolve Preferences -> System -> General -> External scripting = Local.
ONE Resolve call at a time across every skill of Colden's: the exclusive flock on ~/.config/amira/resolve.lock is the
SAME file the AMIRA skills use (2026-09-29: Resolve 21.1 aborted when two sessions' calls overlapped), waited for up
to CWC_RESOLVE_WAIT s (default 20 min) BEFORE the timeout starts; the OS releases it on exit, even on a crash.
PROJECT=<name>: the call refuses to run on any other open project (it never switches projects by itself - see
open_project.py)."""
import sys, os, signal, json, fcntl, time
sys.path.append('/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Modules')
os.environ.setdefault('RESOLVE_SCRIPT_API', '/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting')
os.environ.setdefault('RESOLVE_SCRIPT_LIB', '/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/fusionscript.so')
_LOCK = os.path.expanduser('~/.config/amira/resolve.lock'); os.makedirs(os.path.dirname(_LOCK), exist_ok=True)
_lf = open(_LOCK, 'a+'); _t0 = time.time()
while True:
    try: fcntl.flock(_lf, fcntl.LOCK_EX | fcntl.LOCK_NB); break
    except BlockingIOError:
        if time.time() - _t0 > float(os.environ.get('CWC_RESOLVE_WAIT', 1200)):
            _lf.seek(0); print(json.dumps({'error': f'Resolve busy: resolve.lock held by {_lf.read().strip()!r}'}), flush=True); os._exit(4)
        time.sleep(1)
_lf.seek(0); _lf.truncate(); _lf.write(f"{os.getpid()} CWC_PodReels {os.path.basename(sys.argv[2])} {time.strftime('%H:%M:%S')}\n"); _lf.flush()
def _die(*a): print(json.dumps({'error': 'TIMEOUT'}), flush=True); os._exit(3)
signal.signal(signal.SIGALRM, _die); signal.alarm(int(sys.argv[1]))
import DaVinciResolveScript as dvr
resolve = dvr.scriptapp('Resolve')
if not resolve: print(json.dumps({'error': 'no Resolve connection (Resolve not running, or external scripting is not Local)'}), flush=True); os._exit(2)
pm = resolve.GetProjectManager(); project = pm.GetCurrentProject(); mp = project.GetMediaPool() if project else None
g = {'resolve': resolve, 'pm': pm, 'project': project, 'mp': mp, 'result': None}
for kv in sys.argv[3:]:
    k, v = kv.split('=', 1); g[k] = json.loads(v)
try:
    if g.get('PROJECT') and os.path.basename(sys.argv[2]) != 'open_project.py':
        assert project and project.GetName() == g['PROJECT'], f"Resolve has project {project.GetName() if project else None!r} open, this run needs {g['PROJECT']!r} (open_project.py)"
    exec(open(sys.argv[2], encoding='utf-8').read(), g); print(json.dumps(g.get('result'), default=str))
except BaseException as e:      # a failed script still leaves through os._exit: the interpreter teardown of fusionscript.so segfaults
    import traceback; print(json.dumps({'error': f'{type(e).__name__}: {e}', 'trace': traceback.format_exc()[-900:]})); sys.stdout.flush(); os._exit(1)
sys.stdout.flush(); sys.stderr.flush(); os._exit(0)
