"""selftest.py      every gate of CWC_PodRun against a synthetic episode - run after ANY change. Exit 0 = all hold.
Builds a throw-away CWC_ROOT (fake HOME, fake NAS folder, fake #recycle) with a PodClips + PodReels delivery, phrases with
speakers, a YouTube calendar with a busy day, Metricool calendars, best times, Studio viewer peaks, Chrome-confirmed month
counts and a holistic read, then checks the plan, every gate, the Telegram cards (dry: logged, never sent), Metricool
payloads, the manual kits, the dashboard, the baton and the cleanup (scan -> card -> apply on the fake disks).
Uses the real show files in this repo (CWC_SKILLS = the repo's skills/ folder). Needs only Python 3.9+."""
import os, sys, json, glob, shutil, tempfile, subprocess, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); SKILLS = os.path.dirname(os.path.dirname(HERE))
PASS, FAIL = [], []
NOW = '2026-10-01T23:30:00-04:00'

def check(name, ok, detail=''):
    (PASS if ok else FAIL).append(name); print(('ok   ' if ok else 'FAIL ') + name + (f'  - {detail}' if detail and not ok else ''))

def w(p, data):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w') as f: f.write(data) if isinstance(data, str) else json.dump(data, f, indent=1)

SPEAK = {13: ('Nick', 6), 61: ('Jake', 2), 161: ('Nick', 4), 261: ('Nick', 5), 361: ('Nick', 5)}     # phrase index -> (who, words)

def fixture(T):
    root = f'{T}/root'; ep = f'{T}/nas/Ep. 24 - 10:1'; os.makedirs(ep)
    env = dict(os.environ, CWC_ROOT=root, CWC_SKILLS=SKILLS, CWC_SCRAPE=f'{T}/channel_metrics.json', HOME=f'{T}/home')
    def f(name, kb=1):
        p = f'{ep}/Final/{name}'; os.makedirs(os.path.dirname(p), exist_ok=True); open(p, 'wb').write(b'x' * 1024 * kb); return p
    res = subprocess.run([sys.executable, f'{HERE}/intake.py', ep, '--show', 'creative-lens', '--window', '2026-10-02', '2026-10-08', '--by', 'selftest: Fri to Thu'], env=env, capture_output=True, text=True)
    assert res.returncode == 0, res.stderr
    R = f'{root}/run/creative-lens/Ep24'; CW = f'{root}/clips/creative-lens/Ep24'; RW = f'{root}/reels/creative-lens/Ep24'
    ph = []
    for i in range(1, 400):
        who, n = SPEAK.get(i, ('Colden', 5))
        ph.append({'id': f'P{i:04d}', 'who': who, 'start': i * 10.0, 'end': i * 10.0 + 9.0, 'w': [[f'w{k}', 0, 0] for k in range(n)]})
    w(f'{CW}/phrases.json', ph); w(f'{RW}/phrases.json', ph)
    w(f'{CW}/themes.json', {'themes': [
        {'id': 't01', 'hook': {'from': 'P0010', 'to': 'P0010'}, 'body': [{'from': 'P0005', 'to': 'P0040'}]},
        {'id': 't02', 'body': [{'from': 'P0100', 'to': 'P0140'}]}, {'id': 't03', 'body': [{'from': 'P0200', 'to': 'P0240'}]},
        {'id': 't04', 'body': [{'from': 'P0300', 'to': 'P0340'}]}]})
    w(f'{RW}/themes.json', {'themes': [{'id': sid, 'ranges': [{'from': f'P{a:04d}', 'to': f'P{a + 2:04d}'}]} for sid, a in
                                       (('s01', 12), ('s02', 60), ('s03', 160), ('s04', 260), ('s05', 360), ('s06', 380))]})
    w(f'{CW}/lock.json', {'at': 'x'})
    clips = []
    for i, (th, chans, news) in enumerate([('t01', ['cwc', 'tcl'], None), ('t02', ['cwc', 'tcl'], {'date': '2026-10-01'}), ('t03', ['cwc'], None), ('t04', ['tcl'], None)]):
        for ch in chans:
            clips.append({'theme': th, 'channel': ch, 'master': f(f'Clips/{th} {ch}.mp4'), 'master_carries_stinger_of': ch,
                          'titles': {'A': f'Title {th} {ch}', 'B': 'b', 'C': 'c'}, 'thumbnails': {'A': f(f'Clips/Thumbnails/{th} {ch} - A.jpg'), 'B': 'b', 'C': 'c'},
                          'captions': f(f'Clips/Captions/{th} {ch}.srt'), 'description': 'desc {FULL_EPISODE_URL}', 'tags': ['a'], 'playlists': ['PLx'],
                          'category': 'Science & Technology', 'pinned_comment': 'q?', 'push_order': i + 1, 'news': news, 'needs': ['FULL_EPISODE_URL'], 'ab_tests_plan': {'B': 'x', 'C': 'y'}})
    w(f'{CW}/delivery.json', {'version': 2, 'clips': clips})
    os.makedirs(f'{T}/#recycle/CWC_PodReels/old', exist_ok=True); open(f'{T}/#recycle/CWC_PodReels/old/prev.mp4', 'wb').write(b'x' * 2048)
    shorts = [{'id': sid, 'title': f'Short {sid}', 'brands': bs, 'destination': 'both' if len(bs) == 2 else bs[0], 'master': f(f'Reels/{sid}.mp4'), 'cover': f(f'Reels/{sid} cover.jpg'),
               'copy': {'caption': f'Hook {sid}.\n#a #b #c #d #e', 'first_comment': 'q?', 'yt_title': f'YT {sid}', 'fb_title': f'FB {sid}', 'playlist': 'tcl_shorts', 'ig_collab': 'willco_media' if sid == 's02' else None}}
              for sid, bs in [('s01', ['cwc', 'tcl']), ('s02', ['cwc', 'tcl']), ('s03', ['cwc']), ('s04', ['tcl']), ('s05', ['cwc', 'tcl']), ('s06', ['cwc'])]]
    w(f'{RW}/delivery.json', {'skill': 'CWC_PodReels', 'shorts': shorts, 'cleanup': {'files_moved': [[f'{ep}/Shorts/x.mp4', f'{T}/#recycle/CWC_PodReels/old/prev.mp4']]}})
    w(f'{RW}/checked.json', {'deliver': ['s02', 's01', 's03', 's05', 's04', 's06']})
    w(f'{R}/calendar/youtube.json', {'at': 'x', 'channels': {
        'cwc': [{'id': 'v1', 'title': 'Existing long', 'privacy': 'private', 'publish_at': '2026-10-05T18:00:00Z', 'seconds': 600, 'live': False, 'kind': 'long'},
                {'id': 'v2', 'title': 'Ep. 24 live', 'privacy': 'public', 'published_at': '2026-10-01T23:00:00Z', 'seconds': 5400, 'live': True, 'kind': 'live'}], 'tcl': []}})
    for b in ('cwc', 'tcl'):
        w(f'{R}/calendar/metricool_{b}.json', {'at': 'x', 'brand': b, 'from': '2026-10-01', 'to': '2026-10-31',
                                                 'posts': [{'id': 'm1', 'at': '2026-10-02T12:00-04:00', 'networks': ['instagram'], 'text': 'x'}] if b == 'cwc' else []})
        w(f'{R}/calendar/best_{b}.json', {'at': 'x', 'rows': [{'dow': d, 'hour': h, 'value': v} for d in range(7) for h, v in ((11, 5.0), (15, 4.0), (19, 3.0))]})
    w(f'{R}/calendar/peaks_cwc.json', {'at': 'x', 'days': {str(d): {'most': [13, 14], 'some': [12]} for d in range(7)}, 'no_data': False})
    w(f'{R}/calendar/peaks_tcl.json', {'at': 'x', 'days': {str(d): {'most': [], 'some': []} for d in range(7)}, 'no_data': True})
    w(f'{T}/shot.png', 'png')
    for b, n in (('cwc', 18), ('tcl', 0)):
        res = subprocess.run([sys.executable, f'{HERE}/cal.py', 'counts', R, b, f'2026-10={n}', '--evidence', f'{T}/shot.png'], env=env, capture_output=True, text=True); assert res.returncode == 0, res.stderr
    w(f'{T}/channel_metrics.json', {'updated': '2026-10-02', 'audience': {'best_slots_et': ['Tue 11 AM']}})
    w(f'{R}/holistic.json', {'summary': 'Selftest episode: a news clip (t02) leads, four clips, six reels; s06 held for the test.',
                             'overrides': [{'ref': 's05', 'kind': 'short', 'rank': 1, 'why': 'price number in frame 1: TikTok gear-price posts 10x median (scrape insights)'}],
                             'hold': [{'ref': 's06', 'kind': 'short', 'why': 'abstract AI opinion: 0.06-0.2x median on every platform (scrape avoid list)'}]})
    return env, R, CW, RW, ep

def run(env, *a, inp=None): return subprocess.run([sys.executable, *a], env=env, capture_output=True, text=True, input=inp)
def plan(env, R, *extra, touch=True):
    if touch and os.path.exists(f'{R}/holistic.json'): os.utime(f'{R}/holistic.json', None)
    return run(env, f'{HERE}/plan.py', 'build', R, '--now', NOW, *extra)

def main():
    T = tempfile.mkdtemp(prefix='cwc_podrun_selftest_')
    try:
        env, R, CW, RW, ep = fixture(T)
        res = plan(env, R); check('plan builds on good input', res.returncode == 0, res.stderr[-700:])
        if res.returncode: return
        P = json.load(open(f'{R}/plan.json'))
        it = {i['id']: i for i in P['items']}; t = lambda k: dt.datetime.fromisoformat(it[k]['publish_at'])
        # window + timing
        check('the window is the one Colden confirmed', P['window']['start'] == '2026-10-02' and P['window'].get('confirmed_by', '').startswith('selftest'))
        check('news clip t02 goes first on CWC', min((i for i in P['items'] if i['kind'] == 'yt_clip' and i['brand'] == 'cwc'), key=lambda i: i['publish_at'])['ref'] == 't02')
        check('CWC clips 30 min before the Studio viewer peak (13:00 -> 12:30)', all(i['publish_at'][11:16] == '12:30' for i in P['items'] if i['kind'] == 'yt_clip' and i['brand'] == 'cwc'))
        check('TCL without peak data -> 14:00 fallback, flagged', all(i['publish_at'][11:16] == '14:00' for i in P['items'] if i['kind'] == 'yt_clip' and i['brand'] == 'tcl') and any('no viewer-peak data' in x for x in P['warnings']))
        cwc_long = [i['publish_at'][:10] for i in P['items'] if i['kind'] == 'yt_clip' and i['brand'] == 'cwc']
        check('one long-form per channel per day', len(cwc_long) == len(set(cwc_long)))
        check('busy day (existing long-form Mon Oct 5) avoided', '2026-10-05' not in cwc_long)
        # delays
        check('the same clip on both: TCL >= 48 h after CWC', all(t(f'clip-{r}-tcl') - t(f'clip-{r}-cwc') >= dt.timedelta(hours=48) for r in ('t01', 't02')))
        check('TCL-only clip: no delay (Fri, the window start)', it['clip-t04-tcl']['publish_at'][:10] == '2026-10-02')
        check('the same reel on both: TCL >= 48 h after CWC', all(t(f'yts-{s}-tcl') - t(f'yts-{s}-cwc') >= dt.timedelta(hours=48) for s in ('s01', 's02', 's05')))
        check('TCL-only reel: no delay (Fri)', it['yts-s04-tcl']['publish_at'][:10] == '2026-10-02')
        check('same-topic reel s01 not on the day of clip t01', all(it[f'yts-s01-{b}']['publish_at'][:10] != it[f'clip-t01-{b}']['publish_at'][:10] for b in ('cwc', 'tcl')))
        # collaborators
        soc = {i['id']: i for i in P['items'] if i['kind'] == 'social'}
        check('collab: Colden + guest -> the guest, on the CWC post only', soc['mc-s01-cwc']['ig_collabs'] == ['willco_media'] and soc['mc-s01-tcl']['ig_collabs'] == [])
        check('collab: only Colden (+ a 2-word "yeah" from Jake) -> none', soc['mc-s02-cwc']['ig_collabs'] == [] and soc['mc-s02-tcl']['ig_collabs'] == [])
        check('collab: PodReels copy disagreeing with the speakers is flagged', any('reel s02' in x and 'speakers win' in x for x in P['warnings']))
        check('collab: TCL-only reel -> collaborators on TCL', soc['mc-s04-tcl']['ig_collabs'] == ['willco_media'])
        check('collab: one set per reel', all(sum(1 for i in soc.values() if i['ref'] == r and i['ig_collabs']) <= 1 for r in {i['ref'] for i in soc.values()}))
        # routes + caps
        check('no YouTube through Metricool; TCL has no Facebook', all('youtube' not in i['networks'] for i in soc.values()) and all('facebook' not in i['networks'] for i in soc.values() if i['brand'] == 'tcl'))
        mc = [i for i in soc.values() if i['brand'] == 'cwc' and i['route'] == 'metricool']; man = [i for i in soc.values() if i['brand'] == 'cwc' and i['route'] == 'manual']
        check('CWC cap: 18 used (Chrome count) -> 2 via Metricool, the rest manual', len(mc) == 2 and len(man) == 2, f'{len(mc)}/{len(man)}')
        check('the best-ranked reels get the Metricool slots (s05 moved up by the holistic read)', sorted(i['ref'] for i in mc) == ['s02', 's05'])
        check('every YouTube item uploads through the API, private until flipped', all(i['route'] == 'youtube_api' and i['schedule'] == 'flip' for i in P['items'] if i['kind'] != 'social'))
        check('every YouTube upload lands at least a day before its slot', all(i['upload_day'] < i['publish_at'][:10] for i in P['items'] if i['kind'] != 'social'))
        check('holistic override: s05 is the first CWC reel', min((i for i in P['items'] if i['kind'] == 'yt_short' and i['brand'] == 'cwc'), key=lambda i: i['publish_at'])['ref'] == 's05')
        check('reels placed in rank order on CWC (s05, s02, then s01 / s03)', [i['ref'] for i in sorted((i for i in P['items'] if i['kind'] == 'yt_short' and i['brand'] == 'cwc'), key=lambda i: i['publish_at'])][:2] == ['s05', 's02'])
        check('holistic hold: s06 out and listed', not any(i['ref'] == 's06' for i in P['items']) and any('HELD short s06' in x for x in P['skipped']))
        check('weekdays computed', all(i['weekday'] == ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][dt.datetime.fromisoformat(i['publish_at']).weekday()] for i in P['items']))
        # ---- gates fire
        r0 = json.load(open(f'{R}/run.json')); r1 = dict(r0); r1.pop('window'); w(f'{R}/run.json', r1); res = plan(env, R)
        check('GATE no confirmed window -> exit 2 (ask)', res.returncode == 2, res.stderr[-200:]); w(f'{R}/run.json', r0)
        os.rename(f'{R}/calendar/counts_cwc.json', f'{T}/c.bak'); res = plan(env, R)
        check('GATE no confirmed Metricool count -> exit 1', res.returncode == 1, res.stderr[-200:]); os.rename(f'{T}/c.bak', f'{R}/calendar/counts_cwc.json')
        os.utime(f'{R}/calendar/peaks_cwc.json', (0, 0)); res = plan(env, R)
        check('GATE stale viewer peaks -> exit 1', res.returncode == 1, res.stderr[-200:]); os.utime(f'{R}/calendar/peaks_cwc.json', None)
        os.utime(f'{R}/calendar/youtube.json', (0, 0)); res = plan(env, R)
        check('GATE stale YouTube calendar -> exit 1', res.returncode == 1, res.stderr[-200:]); os.utime(f'{R}/calendar/youtube.json', None)
        ph = json.load(open(f'{RW}/phrases.json')); ph[60]['w'] = [['x', 0, 0]] * 4; w(f'{RW}/phrases.json', ph); res = plan(env, R)
        check('GATE Jake speaks, no handle on file -> exit 2 (never guessed)', res.returncode == 2 and 'Jake' in res.stderr, res.stderr[-200:])
        ph[60]['w'] = [['x', 0, 0]] * 2; w(f'{RW}/phrases.json', ph)
        d = json.load(open(f'{CW}/delivery.json')); d['clips'][0]['master_carries_stinger_of'] = 'tcl'; w(f'{CW}/delivery.json', d); res = plan(env, R)
        check('GATE master on the wrong channel -> exit 1', res.returncode == 1, res.stderr[-200:]); d['clips'][0]['master_carries_stinger_of'] = 'cwc'; w(f'{CW}/delivery.json', d)
        m = d['clips'][0]['master']; os.rename(m, m + '.gone'); res = plan(env, R)
        check('GATE missing master (NAS) -> exit 2', res.returncode == 2, res.stderr[-200:]); os.rename(m + '.gone', m)
        w(f'{T}/channel_metrics.json', {'updated': '2026-09-01'}); res = plan(env, R)
        check('GATE stale Monday scrape -> exit 2', res.returncode == 2, res.stderr[-200:])
        res = plan(env, R, '--waive-scrape', 'selftest waiver'); check('a waiver lets a stale scrape through', res.returncode == 0, res.stderr[-200:])
        w(f'{T}/channel_metrics.json', {'updated': '2026-10-02'})
        hb = open(f'{R}/holistic.json').read(); os.remove(f'{R}/holistic.json'); res = plan(env, R, touch=False)
        check('GATE no holistic read -> exit 1', res.returncode == 1, res.stderr[-200:])
        w(f'{R}/holistic.json', {'summary': 'x' * 50, 'overrides': [{'ref': 's01', 'kind': 'short', 'rank': 1, 'why': 'feels right'}]}); res = plan(env, R)
        check('GATE an override without a data reason -> exit 1', res.returncode == 1, res.stderr[-200:])
        w(f'{R}/holistic.json', hb); os.utime(f'{CW}/lock.json', None); os.utime(f'{CW}/delivery.json', (0, 0)); res = plan(env, R)
        check('GATE clips delivery older than its lock -> exit 1', res.returncode == 1, res.stderr[-200:]); os.utime(f'{CW}/delivery.json', None)
        res = plan(env, R, touch=False); check('GATE holistic read older than a delivery -> exit 1', res.returncode == 1, res.stderr[-200:])
        res = plan(env, R); check('plan rebuilds clean', res.returncode == 0, res.stderr[-300:])
        # ---- Telegram (dry)
        tenv = dict(env, CWC_TG_DRY='1', CWC_TG_DRY_LOG=f'{T}/tg.log'); w(f'{T}/home/.config/cwc/telegram.json', {'chat_id': 1})
        tp = lambda *a, inp=None: run(tenv, f'{HERE}/tg_plan.py', *a, inp=inp)
        cb = lambda data, mid: json.dumps({'update_id': 2, 'callback_query': {'id': 'q', 'data': data, 'message': {'message_id': mid, 'chat': {'id': 1}}}})
        res = run(tenv, f'{HERE}/window.py', 'ask', R); r = json.load(open(f'{R}/run.json')); span = (r.get('window_card') or {}).get('span')
        check('window card sends with the proposal', res.returncode == 0 and span, res.stderr[-200:])
        res = tp('handle', inp=cb(f'pa|cl24|wchg|{span}', r['window_card']['message_id'])); res2 = tp('handle', inp=json.dumps({'update_id': 3, 'message': {'message_id': 70, 'text': 'Sun 10/4 to Fri 10/9'}}))
        r = json.load(open(f'{R}/run.json')); check('window Change -> his message is stored for Claude to read', r.get('window_notes_open') == 'Sun 10/4 to Fri 10/9', res2.stderr[-200:])
        res = run(env, f'{HERE}/window.py', 'set', R, '2026-10-02', '2026-10-08', '--by', 'selftest: keep Fri to Thu'); check('window.py set records his words', res.returncode == 0, res.stderr[-200:])
        res = plan(env, R); P = json.load(open(f'{R}/plan.json'))
        res = tp('send', R); check('plan card sends', res.returncode == 0, res.stderr[-300:])
        card = open(f'{T}/tg.log').read(); check('the card shows collaborators and the flip instruction', 'collab @willco_media' in card and 'flip' in card)
        r = json.load(open(f'{R}/run.json')); s8 = P['sha'][:8]; mid = r['plan_card']['message_ids'][-1]
        res = tp('handle', inp=cb('pr|cl24|t|s01', mid)); check('a CWC_PodReels callback is not ours (exit 3)', res.returncode == 3)
        res = tp('handle', inp=cb('pa|cl24|ok|deadbeef', mid)); r = json.load(open(f'{R}/run.json'))
        check('a tap on a replaced plan approves nothing', res.returncode == 0 and not r.get('plan_approval'))
        res = tp('handle', inp=cb(f'pa|cl24|ok|{s8}', mid)); r = json.load(open(f'{R}/run.json'))
        check('Schedule all -> plan_approval bound to the sha', (r.get('plan_approval') or {}).get('sha') == P['sha'], res.stderr[-200:])
        nx = run(env, f'{HERE}/next.py', R, '--json'); check('next.py runs (exit 0) and reports a stage', nx.returncode == 0 and json.loads(nx.stdout or '{}').get('stage'), nx.stderr[-300:])
        # ---- Metricool
        links = {i['id']: {'video_direct': f'https://drive.example/{i["id"]}.mp4', 'thumb_direct': f'https://drive.example/{i["id"]}.jpg', 'size': 1} for i in P['items'] if i['kind'] == 'social'}
        w(f'{R}/publish/drive_links.json', links)
        mp = run(env, f'{HERE}/metricool.py', 'payloads', R, '--now', '2026-10-01T23:45:00-04:00'); check('payloads build for the approved plan', mp.returncode == 0, mp.stderr[-400:])
        pl = json.load(open(f'{R}/publish/metricool_payloads.json')) if mp.returncode == 0 else []; infos = [json.loads(x['info']) for x in pl]
        check('one Metricool call per reel per brand, one text, never youtube, right blogId', len(pl) == len([i for i in P['items'] if i['kind'] == 'social' and i['route'] == 'metricool'])
              and all('youtube' not in [p['network'] for p in i['providers']] and i['text'] for i in infos) and all(x['blogId'] == {'cwc': '5965295', 'tcl': '6367106'}[x['brand']] for x in pl))
        coll = {x['id']: [c['username'] for c in i.get('instagramData', {}).get('collaborators', [])] for x, i in zip(pl, infos)}
        check('payload collaborators = the plan\'s set', all(coll[x['id']] == next(i for i in P['items'] if i['id'] == x['id'])['ig_collabs'] for x in pl))
        ans = f'{T}/ans.json'; w(ans, {'data': {'id': 4242, 'plannerUrl': 'https://app.metricool.com/planner/x'}})
        rc = run(env, f'{HERE}/metricool.py', 'record', R, pl[0]['id'], ans); check('record writes publish_log + the ledger', rc.returncode == 0 and os.path.exists(f'{T}/root/data/metricool_ledger.jsonl'), rc.stderr[-200:])
        rc = run(env, f'{HERE}/metricool.py', 'record', R, pl[0]['id'], ans); check('GATE the same post is never recorded twice', rc.returncode == 1)
        w(ans, {'error': 'Text too long'}); rc = run(env, f'{HERE}/metricool.py', 'record', R, pl[1]['id'], ans); check('GATE a connector error is never recorded', rc.returncode == 1)
        for x in pl[1:]: w(ans, {'data': {'id': x['id'], 'plannerUrl': 'u'}}); run(env, f'{HERE}/metricool.py', 'record', R, x['id'], ans)
        # ---- kits, checklist, dashboard, baton
        kt = run(env, f'{HERE}/kit.py', R); kits = glob.glob(f'{glob.escape(ep)}/Final/Manual Posts/*/post.txt')
        check('kit: one folder per manual post, collaborators line present', kt.returncode == 0 and len(kits) == len([i for i in P['items'] if i['route'] == 'manual']) and all('Instagram collaborators' in open(k).read() for k in kits), kt.stderr[-300:])
        ck = run(env, f'{HERE}/youtube.py', 'checklist', R); body = open(f'{R}/publish/studio_checklist.md').read() if ck.returncode == 0 else ''
        check('Studio checklist: monetization ON + the flip time on every video', body.count('Monetization: ON') == len([i for i in P['items'] if i['kind'] != 'social']) and 'Private -> Schedule' in body, ck.stderr[-200:])
        db = run(env, f'{HERE}/dashboard.py', R); check('dashboard written to the episode Final folder', db.returncode == 0 and os.path.exists(f'{ep}/Final/Ep24 Posting Plan.html'), db.stderr[-300:])
        bt = lambda *a: run(env, f'{HERE}/baton.py', *a).returncode
        check('baton: one skill at a time in Resolve', bt('take', 'CWC_PodClips', 'build t01') == 0 and bt('take', 'CWC_PodReels', 'build s01') == 4 and bt('give', 'CWC_PodReels') == 1 and bt('give', 'CWC_PodClips') == 0)
        # ---- cleanup
        sc = run(env, f'{HERE}/cleanup.py', 'scan', R, '--no-resolve'); check('GATE cleanup refuses while posts are still open', sc.returncode == 1, sc.stderr[-200:])
        log = json.load(open(f'{R}/publish_log.json'))
        for i in P['items']: log.setdefault(i['id'], {'route': 'selftest'})
        w(f'{R}/publish_log.json', log)
        os.makedirs(f'{ep}/Clips/B-Roll', exist_ok=True); open(f'{ep}/Clips/B-Roll/unused.png', 'w').write('x')
        os.makedirs(f'{ep}/Shorts/Renders', exist_ok=True); open(f'{ep}/Shorts/Renders/s09 old.mp4.rejected', 'w').write('x')
        os.makedirs(f'{T}/#recycle/CWC_PodCut/Ep24 20261001-2140', exist_ok=True); open(f'{T}/#recycle/CWC_PodCut/Ep24 20261001-2140/lt.mov', 'wb').write(b'x' * 4096)
        os.makedirs(f'{T}/#recycle/CWC_PodCut/Ep23 20260920-1000', exist_ok=True)
        os.makedirs(f'{RW}/edit/s01/preview', exist_ok=True); open(f'{RW}/edit/s01/preview/p.mp4', 'wb').write(b'x' * 2 * 1024 * 1024); open(f'{RW}/edit/s01/big.json', 'wb').write(b'x' * 2 * 1024 * 1024)
        sc = run(env, f'{HERE}/cleanup.py', 'scan', R, '--no-resolve'); man = json.load(open(f'{R}/cleanup/manifest.json')) if sc.returncode == 0 else {'nas': [], 'local': [], 'notes': [], 'sha': ''}
        nas = [x['path'] for x in man['nas']]; loc = [x['path'] for x in man['local']]
        check('cleanup scan runs once every post is handled', sc.returncode == 0, sc.stderr[-300:])
        check('NAS: rejected generation + this episode\'s #recycle folders are candidates', any(p.endswith('.rejected') for p in nas) and any('CWC_PodCut/Ep24 ' in p for p in nas) and any(p.endswith('prev.mp4') for p in nas), str(nas))
        check('NAS: another episode\'s #recycle folder is never a candidate', not any('Ep23' in p for p in nas))
        check('NAS: no Resolve listing -> b-roll kept and reported', not any('B-Roll' in p for p in nas) and any('B-Roll' in n for n in man['notes']))
        check('Final/ and every delivered file are kept', not any('/Final/' in p for p in nas + loc))
        check('local: a preview render goes to the Trash; a big JSON record stays', any(p.endswith('p.mp4') for p in loc) and not any(p.endswith('big.json') for p in loc))
        ap = run(env, f'{HERE}/cleanup.py', 'apply', R); check('GATE cleanup apply refuses an unapproved manifest', ap.returncode == 1)
        run(tenv, f'{HERE}/cleanup.py', 'card', R); r = json.load(open(f'{R}/run.json'))
        res = tp('handle', inp=cb(f'pa|cl24|cln|{man["sha"][:8]}', r['cleanup_card']['message_id'])); r = json.load(open(f'{R}/run.json'))
        check('Clean up tap -> approval bound to the manifest', (r.get('cleanup_approval') or {}).get('sha') == man.get('sha'), res.stderr[-200:])
        ap = run(env, f'{HERE}/cleanup.py', 'apply', R)
        check('apply: NAS candidates hard-deleted', ap.returncode == 0 and not os.path.exists(f'{T}/#recycle/CWC_PodCut/Ep24 20261001-2140') and not os.path.exists(f'{ep}/Shorts/Renders/s09 old.mp4.rejected'), ap.stderr[-300:])
        check('apply: local files moved to the Trash, not deleted', not os.path.exists(f'{RW}/edit/s01/preview/p.mp4') and bool(glob.glob(f'{T}/home/.Trash/CWC_PodRun*/**/p.mp4', recursive=True)))
        check('apply: masters, records, b-roll without a listing and the other episode untouched', os.path.exists(d['clips'][0]['master']) and os.path.exists(f'{RW}/edit/s01/big.json')
              and os.path.isdir(f'{T}/#recycle/CWC_PodCut/Ep23 20260920-1000') and os.path.exists(f'{ep}/Clips/B-Roll/unused.png'))
    finally:
        shutil.rmtree(T, ignore_errors=True)
        print(f'\n{len(PASS)} passed, {len(FAIL)} failed')
    sys.exit(1 if FAIL else 0)

if __name__ == '__main__': main()
