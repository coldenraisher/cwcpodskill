"""Telegram Bot API for CWC_PodReels (@VideoEditReview_bot, the same bot as CWC_PodClips).
NO POLLER HERE: CWC_PodClips' always-on tg_listen.py owns getUpdates and hands every update its own handlers decline to
our tg_router.py (plugin, ~/.config/cwc/listen_plugins.json). Two pollers on one bot steal each other's taps.
Every call goes over IPv4 on a kept-open connection (CWC_PodClips measured 22-31 s per tap with urllib's IPv6/IPv4
alternation, 0.1 s with this). Every VIDEO carries width / height / duration read with ffprobe, supports_streaming and a
same-shape cover <= 320 px (Colden's global rule 2026-09-29); a file that cannot be probed is never sent."""
import os, json, uuid, socket, mimetypes, subprocess, threading, http.client, urllib.parse
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
    C.ask('no Telegram pairing (~/.config/cwc/telegram.json or the edit-shorts one)')

class _V4(http.client.HTTPSConnection):
    def connect(self):
        ip = socket.getaddrinfo(self.host, self.port, socket.AF_INET, socket.SOCK_STREAM)[0][4][0]
        self.sock = self._context.wrap_socket(socket.create_connection((ip, self.port), self.timeout), server_hostname=self.host)
_conn = threading.local()

def api(method, **params):
    body = urllib.parse.urlencode({k: (json.dumps(v) if isinstance(v, (dict, list)) else v) for k, v in params.items()})
    for attempt in (1, 2):
        c = getattr(_conn, 'c', None)
        try:
            if c is None: c = _V4('api.telegram.org', 443, timeout=8); _conn.c = c
            c.request('POST', f'/bot{token()}/{method}', body=body, headers={'Content-Type': 'application/x-www-form-urlencoded', 'Connection': 'keep-alive'})
            r = json.loads(c.getresponse().read())
            if not r.get('ok'): raise RuntimeError(f'{method}: {r}')
            return r['result']
        except RuntimeError: raise
        except Exception:
            try: c.close()
            except Exception: pass
            _conn.c = None
            if attempt == 2: raise

def multipart(method, fields, files):
    import urllib.request
    b = uuid.uuid4().hex; body = b''
    for k, v in fields.items(): body += f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
    for field, fp in files:
        body += (f'--{b}\r\nContent-Disposition: form-data; name="{field}"; filename="{os.path.basename(fp)}"\r\nContent-Type: {mimetypes.guess_type(fp)[0] or "application/octet-stream"}\r\n\r\n').encode() + open(fp, 'rb').read() + b'\r\n'
    body += f'--{b}--\r\n'.encode()
    r = json.load(urllib.request.urlopen(urllib.request.Request(f'https://api.telegram.org/bot{token()}/{method}', data=body, headers={'Content-Type': f'multipart/form-data; boundary={b}'}), timeout=900))
    if not r.get('ok'): raise RuntimeError(str(r))
    return r['result']

def probe(path):
    r = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height:format=duration', '-of', 'json', path], capture_output=True, text=True)
    j = json.loads(r.stdout or '{}'); st = (j.get('streams') or [{}])[0]; d = float((j.get('format') or {}).get('duration') or 0)
    if not st.get('width') or not st.get('height') or d <= 0: C.fail(f'cannot probe {path} - not sent (never a guessed size)')
    return int(st['width']), int(st['height']), d

def shrink(src, limit_mb=45):
    w, h, d = probe(src)
    if os.path.getsize(src) <= limit_mb * 1024 * 1024 and src.endswith('.mp4'): return src
    out = src.rsplit('.', 1)[0] + ' (tg).mp4'; kbps = int(limit_mb * 8 * 1024 / d) - 96
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', src, '-c:v', 'libx264', '-preset', 'medium', '-b:v', f'{kbps}k', '-maxrate', f'{int(kbps * 1.3)}k', '-bufsize', f'{kbps * 2}k',
                    '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart', out], check=True)
    assert os.path.getsize(out) <= 49 * 1024 * 1024, f'{out} is still over 49 MB'
    return out

def send_video(path, caption, keyboard=None, cover_at=1.0):
    """sendVideo WITH metadata (global rule): width / height / duration from the file, supports_streaming, a cover of
    the same shape <= 320 px on the long side"""
    small = shrink(path); w, h, d = probe(small); cover = small.rsplit('.', 1)[0] + ' (cover).jpg'
    sc = "scale='if(gt(iw,ih),320,-2)':'if(gt(iw,ih),-2,320)'"
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-ss', f'{min(cover_at, max(0.0, d - 0.5)):.2f}', '-i', small, '-frames:v', '1', '-vf', sc, cover], check=True)
    f = {'chat_id': chat(), 'caption': caption[:1000], 'width': w, 'height': h, 'duration': int(round(d)), 'supports_streaming': 'true'}
    if keyboard: f['reply_markup'] = json.dumps(keyboard)
    return multipart('sendVideo', f, [('video', small), ('thumbnail', cover)]), (w, h, d, small)

def send_photo(path, caption, keyboard=None):
    f = {'chat_id': chat(), 'caption': caption[:1000]}
    if keyboard: f['reply_markup'] = json.dumps(keyboard)
    return multipart('sendPhoto', f, [('photo', path)])

def say(text): return api('sendMessage', chat_id=chat(), text=text[:4000])

def ack(q, text=''):
    try: api('answerCallbackQuery', callback_query_id=q['id'], text=text)
    except Exception: pass

def relabel(msg_id, text):
    try: api('editMessageReplyMarkup', chat_id=chat(), message_id=msg_id, reply_markup={'inline_keyboard': [[{'text': text, 'callback_data': 'noop'}]]})
    except Exception: pass
