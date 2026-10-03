"""tg_router.py handle   (stdin = one Telegram update as JSON)  -> exit 0 handled, 3 not mine, 1 error
The CWC_PodReels plugin of CWC_PodClips' always-on listener (tg_listen.py, ~/.config/cwc/listen_plugins.json; hook
added 2026-10-02, ac7794b): every update its own handlers decline is piped here. Callback data of this skill always
starts "pr|<show+ep>|<stage>|..." (64-byte limit): t = theme card, e = edit preview, b = covers + copy batch,
p = posting plan. A text message is ours only when it replies to one of our messages or answers an awaiting-notes
state. Each handler answers its own callback query BEFORE writing anything.
  tg_router.py install    write ~/.config/cwc/listen_plugins.json (idempotent)
  tg_router.py selftest   a fake foreign update must come back 3"""
import os, sys, json, importlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
MODULES = ['tg_cards', 'tg_review', 'tg_batch', 'tg_plan']

def handle(u):
    q = u.get('callback_query')
    if q and not str(q.get('data', '')).startswith('pr|'): return False
    for W in C.works():
        for name in MODULES:
            try: mod = importlib.import_module(name)
            except ModuleNotFoundError: continue
            if mod.handle(W, u): return True
    return False

if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    if cmd == 'handle':
        u = json.loads(sys.stdin.read() or '{}')
        try: ok = handle(u)
        except SystemExit as x: print(f'handler exit {x.code}', file=sys.stderr); sys.exit(1)
        sys.exit(0 if ok else 3)
    elif cmd == 'install':
        p = f'{C.CFG}/listen_plugins.json'; cur = C.load(p, []) or []
        me = {'name': 'CWC_PodReels', 'cmd': [sys.executable, os.path.abspath(__file__), 'handle']}
        cur = [x for x in cur if x.get('name') != 'CWC_PodReels'] + [me]; C.save(p, cur); print(json.dumps(cur, indent=1))
    elif cmd == 'selftest':
        import subprocess
        r = subprocess.run([sys.executable, os.path.abspath(__file__), 'handle'], input=json.dumps({'update_id': 1, 'callback_query': {'id': 'x', 'data': 'pc|Ep24|ok|t01'}}), capture_output=True, text=True)
        assert r.returncode == 3, (r.returncode, r.stderr); print('foreign callback -> 3 ok')
    else: print(__doc__)
