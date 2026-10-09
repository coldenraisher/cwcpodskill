"""Telegram Bot API for CWC_PodRun - the same bot as CWC_PodClips / CWC_PodReels (@VideoEditReview_bot).
NO POLLER HERE: CWC_PodClips' always-on tg_listen.py owns getUpdates and hands every update its own handlers decline to
the plugins in ~/.config/cwc/listen_plugins.json (ours: tg_plan.py handle). Two pollers on one bot steal each other's taps.
Calls go over IPv4 on a kept-open connection (CWC_PodClips measured 22-31 s a tap with urllib's IPv6/IPv4 alternation).
CWC_TG_DRY=1 records calls in $CWC_TG_DRY_LOG instead of sending (selftest)."""
import os, json, socket, threading, http.client
import common as C

def token():
    t = os.environ.get('TG_BOT_TOKEN')
    if not t and os.path.exists(os.path.expanduser('~/.zshrc')):
        for line in open(os.path.expanduser('~/.zshrc')):
            if line.startswith('export TG_BOT_TOKEN='): t = line.split('=', 1)[1].strip().strip('\'"')
    if not t: C.ask('TG_BOT_TOKEN is missing (~/.zshrc)')
    return t

def chat():
    for p in (f'{C.CFG}/telegram.json', '~/.config/edit-shorts/telegram.json'):
        p = os.path.expanduser(p)
        if os.path.exists(p): return json.load(open(p))['chat_id']
    C.ask('no Telegram pairing (~/.config/cwc/telegram.json)')

class _V4(http.client.HTTPSConnection):
    def connect(self):
        ip = socket.getaddrinfo(self.host, self.port, socket.AF_INET, socket.SOCK_STREAM)[0][4][0]
        self.sock = self._context.wrap_socket(socket.create_connection((ip, self.port), self.timeout), server_hostname=self.host)
_conn = threading.local()

def api(method, **params):
    if os.environ.get('CWC_TG_DRY'):
        log, n = os.environ.get('CWC_TG_DRY_LOG'), 1
        if log:
            with open(log, 'a') as f: f.write(json.dumps({'method': method, **params}) + '\n')
            n = sum(1 for _ in open(log))
        return {'message_id': 1000 + n}
    body = json.dumps(params).encode()
    for attempt in (1, 2):
        try:
            c = getattr(_conn, 'c', None) or _V4('api.telegram.org', timeout=30); _conn.c = c
            c.request('POST', f'/bot{token()}/{method}', body, {'Content-Type': 'application/json'})
            res = json.loads(c.getresponse().read())
            break
        except (OSError, http.client.HTTPException):
            _conn.c = None
            if attempt == 2: raise
    if not res.get('ok'): C.fail(f'Telegram {method}: {res.get("description")}')
    return res['result']

def say(text, keyboard=None):
    p = {'chat_id': chat(), 'text': text[:4000], 'disable_web_page_preview': True}
    if keyboard: p['reply_markup'] = {'inline_keyboard': keyboard}
    return api('sendMessage', **p)

def photo(path, caption=''):
    """send an image (multipart, so curl) - the plan's calendar graphics"""
    if os.environ.get('CWC_TG_DRY'): return api('sendPhoto', photo=path, caption=caption)
    import subprocess
    out = subprocess.run(['curl', '-s', '-4', '-F', f'chat_id={chat()}', '-F', f'caption={caption[:1000]}', '-F', f'photo=@{path}',
                          f'https://api.telegram.org/bot{token()}/sendPhoto'], capture_output=True, text=True, timeout=120).stdout
    res = json.loads(out or '{}')
    if not res.get('ok'): C.fail(f'Telegram sendPhoto: {res.get("description")}')
    return res['result']

def ack(q, text=''): return api('answerCallbackQuery', callback_query_id=q['id'], text=text[:190])

def relabel(chat_id, msg_id, label):
    return api('editMessageReplyMarkup', chat_id=chat_id, message_id=msg_id, reply_markup={'inline_keyboard': [[{'text': label, 'callback_data': 'pa|noop'}]]})
