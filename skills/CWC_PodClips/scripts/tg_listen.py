"""tg_listen.py start | stop | status | run
ONE always-on listener for the review bot (Colden 2026-10-01: "a very long delay from button push to actual send on
telegram"). What caused the delay: the listener was a 2-hour job that was stopped whenever the skill was being changed,
so taps waited in Telegram's queue (5 theme approvals sat for minutes on Ep 24), and a tap was answered only after the
bookkeeping. Now:
  - `start` launches the listener DETACHED (it survives this session; pid + log in ~/.config/cwc/); it serves EVERY
    episode under clips/ - theme cards (tg_themes.handle), edit previews (tg_edit.handle) and package cards (tg_pack.handle) - and never exits by itself;
  - a tap is answered (the spinner stops, the button is re-labelled) BEFORE anything is written;
  - updates this skill does not claim go to PLUGINS (~/.config/cwc/listen_plugins.json - CWC_PodReels, 2026-10-02),
    each as its own process, exit 0 handled / 3 not mine;
  - Telegram long-polling returns the instant a tap arrives, so there is no polling interval to wait for;
  - every call goes over IPv4 on a kept-open connection (tg_themes.api): the 22-31 s Colden measured on 2026-10-01
    was a new connection per call stalling for its whole timeout on every second call.
Code changes need `stop` + `start` (a few seconds; taps in between are kept by Telegram and handled on start).
One consumer per bot: `start` refuses while any other poller of this bot runs (tg_themes / tg_edit poll, edit-clips'
tg_review poll)."""
import os, sys, json, time, glob, signal, subprocess
import common as C, tg_themes as G, tg_edit as E, tg_pack as PKG
CFG = os.path.expanduser('~/.config/cwc'); PID = f'{CFG}/tg_listen.pid'; LOG = f'{CFG}/tg_listen.log'; OFF = f'{CFG}/tg_listen.offset'
def works(): return sorted(os.path.dirname(p) for p in glob.glob(f'{C.CLIPS}/*/*/episode.json'))
def alive():
    try:
        pid = int(open(PID).read().strip()); os.kill(pid, 0); return pid
    except Exception: return None
def offset():
    cands = []
    if os.path.exists(OFF): cands.append(int(open(OFF).read().strip() or 0))
    for W in works():
        for f in (G.spath(W), E.rpath(W), PKG.rpath(W)):
            o = (C.load(f) or {}).get('offset')
            if o: cands.append(int(o))
    return max(cands) if cands else None
PLUGINS = f'{CFG}/listen_plugins.json'
def plugins(u, log):
    """updates none of this skill's handlers claimed go to the plugins listed in ~/.config/cwc/listen_plugins.json
    ([{"name": .., "cmd": [..]}]; no file = no plugins) - one bot, one listener (two pollers steal each other's taps).
    Each plugin gets the update as JSON on stdin and runs as its OWN process (skills share module names like common.py):
    exit 0 = handled (the plugin answered its own callback), 3 = not mine (next plugin), anything else = logged."""
    for pl in (C.load(PLUGINS, []) or []):
        try:
            r = subprocess.run(pl['cmd'], input=json.dumps(u), capture_output=True, text=True, timeout=10)      # a hung plugin holds every tap: 10 s at most
            if r.returncode == 0: return f'plugin {pl.get("name")}'
            if r.returncode != 3: log(f'plugin {pl.get("name")} exit {r.returncode}: {(r.stderr or "")[-300:]}')
        except Exception as x: log(f'plugin {pl.get("name")}: {type(x).__name__}: {str(x)[:200]}')
    return None

def run():
    os.makedirs(CFG, exist_ok=True); open(PID, 'w').write(str(os.getpid())); off = offset()
    def log(m):
        with open(LOG, 'a') as f: f.write(f'{C.now()} {m}\n')
    log(f'listen start, offset {off}, episodes {[os.path.basename(w) for w in works()]}')
    while True:
        try: ups = G.api('getUpdates', 20, **dict({'timeout': 10}, **({'offset': off} if off else {})))       # a stalled long poll costs 20 s at most, not 45
        except Exception as e: log(f'network: {str(e)[:120]}'); time.sleep(3); continue
        for u in ups:
            off = u['update_id'] + 1; open(OFF, 'w').write(str(off)); t0 = time.time(); done = None
            for W in works():
                for mod in (E, PKG, G):
                    try:
                        if mod.handle(W, u): done = f'{mod.__name__} {os.path.basename(W)}'; break
                    except SystemExit as x: log(f'handler stopped ({mod.__name__}): exit {x.code}')
                    except Exception as x: log(f'handler error ({mod.__name__}): {type(x).__name__}: {str(x)[:200]}')
                if done: break
            if done:
                for W in works():
                    try: G.settle(W)
                    except BaseException as x: log(f'settle: {x}')
            q = u.get('callback_query')
            if not done and q and q.get('data') == 'noop':      # a tap on a closed card's label: quiet, nobody's business
                try: G.api('answerCallbackQuery', callback_query_id=q['id'])
                except Exception: pass
                done = 'noop'
            if not done: done = plugins(u, log)                 # other skills on the same bot (CWC_PodReels: callback data "pr|...")
            if not done and q:
                try: G.api('answerCallbackQuery', callback_query_id=q['id'], text='That card is no longer open.')
                except Exception: pass
            log(f'{"handled by " + done if done else "unrouted"} in {time.time() - t0:.2f} s: {(q or {}).get("data") or ((u.get("message") or {}).get("text") or "")[:60]}')
if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    if cmd == 'run': run()
    elif cmd == 'start':
        if alive(): print(f'already running (pid {alive()})'); sys.exit(0)
        oth = G.others_polling()
        if oth: C.ask(f'another poller is running on this bot: {oth}')
        os.makedirs(CFG, exist_ok=True)
        p = subprocess.Popen([sys.executable, os.path.abspath(__file__), 'run'], stdout=open(LOG, 'a'), stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, start_new_session=True, cwd=os.path.dirname(os.path.abspath(__file__)))
        time.sleep(1.5)
        if not alive(): C.fail(f'listener did not stay up - see {LOG}')
        print(f'listener started, pid {p.pid}, log {LOG}')
    elif cmd == 'stop':
        pid = alive()
        if pid: os.kill(pid, signal.SIGTERM); print(f'stopped {pid}')
        else: print('not running')
    elif cmd == 'status':
        print(f'running, pid {alive()}' if alive() else 'NOT running'); print(''.join(open(LOG).readlines()[-6:]) if os.path.exists(LOG) else '')
    else: C.fail(__doc__)
