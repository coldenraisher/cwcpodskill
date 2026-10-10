"""watch.py start | stop | status | run | pass [--once] | install      THE GO-LIVE WATCH, as a detached daemon (not a session cron)
Colden 2026-10-09, after s06 went live with no pinned comment and no related video: "why have these skills with rules if
they keep getting missed and ignored?" The watch used to be a cron inside a Claude session: it died with the session, with
the usage limit (Ep 24: "LATE (session restarted, crons lost)", "wake-ups did nothing after Wed 10:33 - usage limits"), and
every wake-up cost a model turn on a huge context. This daemon runs the same scripts on its own, with no model at all:
  every minute, for every run with an APPROVED plan and the posting yes on file, until its cleanup is done:
    pin.py due --alert-pins      the comment goes up through the API at go-live; the PIN job is queued at once in
                                 ~/.config/cwc/podrun_todo.jsonl for the conductor session (a Monitor on that file; it pins
                                 with the Chrome MCP - Colden 2026-10-09)
    related.py due --alert       a Short whose Related video is not set -> the same queue
  TELEGRAM = EMERGENCIES ONLY (Colden 2026-10-10: "If there is an emergency, send it in telegram. If it's just routine keep
  it quiet"). emergencies() decides, once per item and cause: a YouTube post <= 3 h from its slot that is not ready (not
  uploaded, not packaged, thumbnail refused - with the reason and the fix), a video that did not go public, a due video
  not on YouTube, this daemon failing 5 passes in a row. Everything else (matches, quota used up with nothing at risk,
  pins / related videos waiting, a stopped step with time to spare) is QUIET in events.log, next.py and watch.py status.
  every 5 minutes (run.json colden_uploads): youtube.py adopt + adopt --apply   his Studio uploads get their metadata,
                                 publishAt, thumbnail, captions, playlists as soon as they are processed (logged; next.py
                                 shows them); only an AMBIGUOUS match (two uploads with one name) is asked, once
  Google's quotaExceeded: the day is marked exhausted (ytapi.quota_exhausted) and every pass skips the API until midnight
                                 Pacific - silently
  once a day after 03:10 ET (API uploads): youtube.py upload --alert           the next quota day's uploads
  any script error -> ONE Telegram alert per distinct message per 6 h; a heartbeat in ~/.config/cwc/podrun_watch.json
  (next.py reads it: GO-LIVE WATCH RUNNING / NOT RUNNING)
What still needs a browser (Chrome): the PIN itself, the Related video field, monetization, Test & Compare, end screens -
the Data API has none of them. The daemon makes sure the comment is UP on time and that someone is TOLD, at once.
  start    detached (survives the session; pid + log in ~/.config/cwc/)      stop      status
  pass     one pass over every run now (what the loop does), --once = exit after it
  install  write a LaunchAgent plist so the daemon (and the Telegram listener) come back after a reboot - prints the
           launchctl command, loads nothing by itself
GATES: every action runs through the existing scripts and their gates (approved sha, post_ok, quota, publish_log before
the next call) - the daemon adds no path of its own to YouTube or Telegram."""
import os, re, sys, json, time, signal, subprocess, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

PID = f'{C.CFG}/podrun_watch.pid'; LOG = f'{C.CFG}/podrun_watch.log'; HEART = f'{C.CFG}/podrun_watch.json'
EVERY, ADOPT_EVERY, ALERT_REPEAT_H = 60, 300, 24
_state = {'alerted': {}, 'adopted_at': {}, 'uploaded_day': {}}

def log(m):
    os.makedirs(C.CFG, exist_ok=True)
    with open(LOG, 'a', encoding='utf-8') as f: f.write(f'{C.now()} {m}\n')

def alive():
    try:
        pid = int(open(PID).read().strip()); os.kill(pid, 0); return pid
    except Exception: return None

def heartbeat():
    try: return C.load(HEART) or {}
    except Exception: return {}

def running(max_age_min=15):
    """True when the daemon is alive AND its last pass is recent (next.py's gate)"""
    h = heartbeat()
    return bool(alive()) and C.hours_old_iso(h.get('at')) * 60 <= max_age_min

NOISE = ('Warning', 'warnings.warn', 'LibreSSL', 'past its end of life', 'best-effort basis')
def clean_err(err):
    """the script's own last GATE / ASK line - never Python warnings, never Google's HTML / JSON (2026-10-10: Colden got both)"""
    lines = [l for l in (err or '').splitlines() if l.strip() and not any(n in l for n in NOISE)]
    own = [l for l in lines if l.startswith(('GATE:', 'ASK COLDEN:'))]
    t = (own or lines or [''])[-1]; t = re.sub(r'<[^>]+>', '', t); t = re.sub(r'Details: .*$', '', t)
    return t[:240]
def script(R, *a, timeout=900):
    p = subprocess.run([sys.executable, f'{C.SK}/scripts/{a[0]}', *a[1:]], capture_output=True, text=True, timeout=timeout)
    return p.returncode, (p.stdout or '').strip(), clean_err(p.stderr)

def alert_once(R, key, text, emergency=False):
    """a routine stop is logged once per day per cause (QUIET in events.log); an emergency goes to Telegram once per cause"""
    k = f'{R}|{key}'; last = _state['alerted'].get(k, 0)
    if time.time() - last < ALERT_REPEAT_H * 3600: return
    _state['alerted'][k] = time.time()
    import pin; pin.alert(R, text, emergency=emergency)

EMERGENCY_H = 3            # a YouTube item not ready this close to its slot will go out wrong or not at all
_last_error = {}           # run -> the last stop message of a step this daemon saw (the WHY of an emergency)
_crashes = {}              # run -> consecutive crashed passes

def emergencies(R, r, P, now):
    """Colden 2026-10-10: "If there is an emergency, send it in telegram. If it's just routine keep it quiet."
    An EMERGENCY = a post that will go out wrong or not at all and still can be saved by him:
      - a YouTube clip / Short whose slot is <= EMERGENCY_H away (or passed < 1 h ago) and that is not up AND complete
        (not uploaded by him, not packaged - quota, a gate, a dead token -, or its thumbnail refused)
      - (pin.py) a video still private 15 min after its slot; one due 15 min ago that is not on YouTube at all
      - this daemon crashing on the run 5 passes in a row (nothing is being watched)
    One Telegram line per item and cause, recorded in publish_log (`emergency`) so a restart never repeats it.
    Routine, never sent: matches, packaging done, quota used up with nothing at risk, a pin / related video waiting
    (the conducting session does it), a refused cover with time to fix it."""
    import ytapi as Y
    log = C.load(f'{R}/publish_log.json', {}) or {}; blocked = Y.quota_exhausted(); sent = []
    for it in [i for i in P['items'] if i['kind'] in ('yt_clip', 'yt_short')]:
        if C.handled(it, log): continue
        at = dt.datetime.fromisoformat(it['publish_at']); left = (at - now).total_seconds() / 3600
        if left > EMERGENCY_H or left < -1: continue
        e = log.get(it['id']) or {}
        if (e.get('emergency') or {}).get('at'): continue
        label = f'"{it["title"][:70]}" ({C.brands()[it["brand"]]["label"]}, {"clip" if it["kind"] == "yt_clip" else "Short"}) goes live {it["publish_at"][11:16]} ET'
        if not e.get('video_id'):
            why = ('is NOT uploaded yet - upload it in Studio now (private, not scheduled, title = the file name ' + os.path.basename(it['files']['video']) + ')'
                   if C.colden_uploads(r) else 'is NOT uploaded yet')
        elif (e.get('problems') or {}).get('thumbnail'): why = f'is up WITHOUT its thumbnail (YouTube refused it) - set it in Studio: https://studio.youtube.com/video/{e["video_id"]}/edit'
        else: why = f'is uploaded but NOT packaged (no title / description / publish time yet) - Studio: https://studio.youtube.com/video/{e["video_id"]}/edit'
        if blocked: why += f'. The YouTube API quota is used up until {dt.datetime.fromisoformat(blocked).astimezone(C.ET):%H:%M} ET, so I cannot finish it in time - set it in Studio by hand, or tell me to move the slot'
        elif _last_error.get(R): why += f'. Last error: {_last_error[R]}'
        if left < 0: label = label.replace('goes live', 'was due')
        import pin; pin.alert(R, f'{label} and {why}', emergency=True)
        log = C.load(f'{R}/publish_log.json', {}) or {}; log.setdefault(it['id'], {})['emergency'] = {'at': C.now(), 'why': why[:200]}; C.save(f'{R}/publish_log.json', log)
        sent.append(it['id'])
    return sent

def active_runs():
    out = []
    for R in C.runs():
        r = C.load(f'{R}/run.json') or {}; P = C.load(f'{R}/plan.json')
        if not P or (r.get('plan_approval') or {}).get('sha') != P.get('sha'): continue
        if not (r.get('post_ok') or {}).get('words'): continue
        if (r.get('stages') or {}).get('cleanup'): continue
        out.append((R, r, P))
    return out

def yt_open(R, P):
    log_ = C.load(f'{R}/publish_log.json', {}) or {}
    return [i for i in P['items'] if i['kind'] in ('yt_clip', 'yt_short') and not C.handled(i, log_)]

def one_pass(now=None):
    now = now or dt.datetime.now(C.ET); seen = {}
    for R, r, P in active_runs():
        name = os.path.relpath(R, C.RUNS); rec = {'at': C.now()}
        try:
            import ytapi as Y
            opn = yt_open(R, P); blocked = Y.quota_exhausted()
            if blocked: rec['quota'] = f'exhausted until {blocked}'                       # expected, not an error: nothing is read or written until the reset, nobody is messaged
            if opn and not blocked:
                if C.colden_uploads(r):
                    if time.time() - _state['adopted_at'].get(R, 0) >= ADOPT_EVERY:
                        _state['adopted_at'][R] = time.time()
                        rc, out, err = script(R, 'youtube.py', 'adopt', R)
                        if rc == 0:
                            for l in out.splitlines():                      # "x: N match(es) for ..." - only N > 1 is a question (0 = not uploaded yet)
                                m = re.search(r':\s+(\d+) match\(es\)', l)
                                if m and int(m.group(1)) > 1: alert_once(R, 'adopt:' + l[:60], f'Two private uploads carry the name of {l.split(":")[0].strip()} - which one is it? (youtube.py adopt lists them)')
                            rc2, out2, err2 = script(R, 'youtube.py', 'adopt', R, '--apply')     # the matches are logged + shown by next.py, never messaged (2026-10-10: 14 lines at 3 AM)
                            if rc2 in (1, 2) and err2: _last_error[R] = err2; alert_once(R, 'apply:' + err2[:80], f'Packaging your uploads stopped: {err2}')
                            rec['adopt'] = (out2 or out)[-200:]
                        elif rc in (1, 2) and err: _last_error[R] = err; alert_once(R, 'adopt-err:' + err[:80], f'Matching your uploads stopped: {err}')
                else:
                    day = (now.astimezone(dt.timezone.utc) - dt.timedelta(hours=7)).date().isoformat()      # the quota day (Pacific)
                    if _state['uploaded_day'].get(R) != day and now.hour * 60 + now.minute >= 3 * 60 + 10:
                        _state['uploaded_day'][R] = day
                        rc, out, err = script(R, 'youtube.py', 'upload', R, '--alert', timeout=3600)
                        rec['upload'] = (out or err)[-200:]
            rc, out, err = script(R, 'pin.py', 'due', R, '--alert-pins')
            rec['pin'] = {'rc': rc, 'out': out[-300:]}
            if rc not in (0, 1, 2, 3) and err: alert_once(R, 'pin:' + err[:80], f'The go-live comment step stopped: {err}')
            rc, out, err = script(R, 'related.py', 'due', R, '--alert')
            rec['related'] = {'rc': rc, 'out': out[-300:]}
            if rc not in (0, 2, 3) and err: alert_once(R, 'related:' + err[:80], f'The related-video check stopped: {err}')
            rec['emergencies'] = emergencies(R, r, P, now)
            _crashes[R] = 0
        except subprocess.TimeoutExpired as x: log(f'{name}: {os.path.basename(str(x.cmd[1]))} timed out'); rec['error'] = 'timeout'
        except Exception as x: log(f'{name}: {type(x).__name__}: {x}'); rec['error'] = f'{type(x).__name__}: {str(x)[:200]}'
        if rec.get('error'):
            _crashes[R] = _crashes.get(R, 0) + 1
            if _crashes[R] == 5: alert_once(R, 'crashing', f'The go-live watch has failed 5 passes in a row on this run - nothing is being watched: {rec["error"]}', emergency=True)
        seen[name] = rec
    C.save(HEART, {'pid': os.getpid(), 'at': C.now(), 'runs': seen})
    return seen

def run():
    os.makedirs(C.CFG, exist_ok=True); open(PID, 'w').write(str(os.getpid()))
    log(f'watch start pid {os.getpid()}')
    while True:
        t0 = time.time()
        try: seen = one_pass(); log('pass: ' + ', '.join(f'{k} pin {v.get("pin", {}).get("rc")} rel {v.get("related", {}).get("rc")}' + (' ERR ' + v['error'] if v.get('error') else '') for k, v in seen.items()) if seen else 'pass: no active run')
        except Exception as x: log(f'pass crashed: {type(x).__name__}: {x}')
        time.sleep(max(5, EVERY - (time.time() - t0)))

PLIST = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
 <key>Label</key><string>{label}</string>
 <key>ProgramArguments</key><array><string>{py}</string><string>{script}</string><string>run</string></array>
 <key>WorkingDirectory</key><string>{cwd}</string>
 <key>EnvironmentVariables</key><dict><key>PATH</key><string>/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin</string>{env}</dict>
 <key>RunAtLoad</key><true/><key>KeepAlive</key><true/><key>ThrottleInterval</key><integer>30</integer>
 <key>StandardOutPath</key><string>{log}</string><key>StandardErrorPath</key><string>{log}</string>
</dict></plist>
"""

def install():
    import tg
    la = os.path.expanduser('~/Library/LaunchAgents'); os.makedirs(la, exist_ok=True)
    env = f'<key>TG_BOT_TOKEN</key><string>{tg.token()}</string>'
    jobs = [('com.coldenraisher.cwc-podrun-watch', os.path.abspath(__file__), LOG),
            ('com.coldenraisher.cwc-telegram-listener', f'{C.CLIPS_SK}/scripts/tg_listen.py', f'{C.CFG}/tg_listen.log')]
    for label, script_, lg in jobs:
        p = f'{la}/{label}.plist'
        open(p, 'w').write(PLIST.format(label=label, py=sys.executable, script=script_, cwd=os.path.dirname(script_), env=env, log=lg))
        print(f'wrote {p}')
    print('NOT loaded. FIRST: System Settings > Privacy & Security > Full Disk Access > add the Python the agents run\n'
          f'  ({sys.executable} -> its Python.app in .../Python3.framework/Versions/3.9/Resources/): a launchd process gets no\n'
          '  ~/Documents access otherwise (2026-10-10: the first pass died with Operation not permitted, the listener saw no episodes).\n'
          'THEN, to make both survive reboots (stop the hand-started copies first: watch.py stop; tg_listen.py stop):\n'
          + '\n'.join(f'  launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/{l}.plist' for l, _, _ in jobs))

def main():
    a = sys.argv[1:]; cmd = a[0] if a else ''
    if cmd == 'run': run()
    elif cmd == 'pass':
        seen = one_pass(); print(json.dumps(seen, indent=1, ensure_ascii=False)[:4000] if seen else 'no active run (approved plan + posting yes, cleanup not done)')
    elif cmd == 'start':
        if alive(): print(f'already running (pid {alive()})'); return
        if subprocess.run(['launchctl', 'list', 'com.coldenraisher.cwc-podrun-watch'], capture_output=True).returncode == 0:
            C.fail('the watch is a LaunchAgent (2026-10-10): launchctl kickstart -k gui/$(id -u)/com.coldenraisher.cwc-podrun-watch - never a hand-started second copy')
        os.makedirs(C.CFG, exist_ok=True)
        p = subprocess.Popen([sys.executable, os.path.abspath(__file__), 'run'], stdout=open(LOG, 'a'), stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, start_new_session=True, cwd=os.path.dirname(os.path.abspath(__file__)))
        time.sleep(2)
        if not alive(): C.fail(f'the watch did not stay up - see {LOG}')
        print(f'go-live watch started, pid {p.pid}, log {LOG}')
    elif cmd == 'stop':
        pid = alive()
        if pid: os.kill(pid, signal.SIGTERM); print(f'stopped {pid}')
        else: print('not running')
        if os.path.exists(PID): os.remove(PID)
    elif cmd == 'status':
        h = heartbeat(); pid = alive()
        print(f'{"RUNNING" if running() else "NOT RUNNING"}: pid {pid}, last pass {h.get("at")} ({C.hours_old_iso(h.get("at")) * 60:.0f} min ago)' if pid else 'NOT RUNNING (watch.py start)')
        for k, v in (h.get('runs') or {}).items(): print(f'  {k}: pin rc {v.get("pin", {}).get("rc")} | related rc {v.get("related", {}).get("rc")}' + (f' | {v["error"]}' if v.get('error') else ''))
        import pin
        if os.path.exists(pin.TODO):
            rows = [json.loads(l) for l in open(pin.TODO, encoding='utf-8') if l.strip()][-8:]
            print(f'queue {pin.TODO} (last {len(rows)}): ' + '; '.join(f'{r["type"]} {r["item"]} {r.get("url", "")}' for r in rows))
        if os.path.exists(LOG): print(''.join(open(LOG, encoding='utf-8').readlines()[-5:]))
    elif cmd == 'install': install()
    else: print(__doc__); sys.exit(1)

if __name__ == '__main__': main()
