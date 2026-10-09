"""selftest.py      every gate of CWC_PodRun against a synthetic episode - run after ANY change. Exit 0 = all hold.
Builds a throw-away CWC_ROOT (fake HOME, fake NAS folder, fake #recycle) with a PodClips + PodReels delivery, phrases with
speakers, a YouTube calendar with a busy day, Metricool calendars, best times, Studio viewer peaks, Chrome-confirmed month
counts and a holistic read, then checks the plan, every gate, the Telegram cards (dry: logged, never sent), Metricool
payloads, the manual kits, the dashboard, the baton (and its check inside each skill's rs.py, against a stub Resolve
module - the real Resolve is never contacted) and the cleanup (scan -> card -> apply on the fake disks).
THE FIXTURES COPY THE REAL RECORDS (Ep 24, 2026-10-03): CWC_PodClips delivery.json v2 (category and playlists are objects),
CWC_PodReels delivery.json as its lock.py + deliver.py write it (per-brand playlist keys, ig_collab "none"). When either
skill changes its delivery, change the fixture FIRST - a self-test on invented shapes proves nothing (v0.2 passed 71 gates
and failed on the first real file).
Uses the real show files of the sibling skills (~/.claude/skills, or CWC_SKILLS). Needs only Python 3.9+; nothing is
sent, uploaded or deleted outside the temp folder."""
import os, sys, json, glob, shutil, tempfile, subprocess, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); SKILLS = os.environ.get('CWC_SKILLS') or os.path.dirname(os.path.dirname(HERE))
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
    res = subprocess.run([sys.executable, f'{HERE}/intake.py', ep, '--show', 'creative-lens', '--window', '2026-10-02', '2026-10-08', '--by', 'selftest: Fri to Thu', '--post-ok', 'selftest: yes, post it on the tap'], env=env, capture_output=True, text=True)
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
                          'captions': f(f'Clips/Captions/{th} {ch}.srt'), 'description': 'desc {FULL_EPISODE_URL}', 'tags': ['a'], 'playlists': [{'title': 'The Creative Lens Clips', 'id': 'PLx'}],
                          'category': {'id': '1', 'name': 'Film & Animation', 'note': 'Colden 2026-09-15: "Keep film"'}, 'pinned_comment': 'q?', 'push_order': i + 1, 'news': news, 'needs': ['FULL_EPISODE_URL'], 'ab_tests_plan': {'B': 'x', 'C': 'y'}})
    w(f'{CW}/delivery.json', {'version': 2, 'clips': clips})
    for d in ('creative-lens Ep24 lock 20261003-092106', 'colden-todd Ep24 lock 20261003-100000'):       # the names CWC_PodReels gives its #recycle folders
        os.makedirs(f'{T}/#recycle/CWC_PodReels/{d}', exist_ok=True); open(f'{T}/#recycle/CWC_PodReels/{d}/prev.mp4', 'wb').write(b'x' * 2048)
    shorts = [{'id': sid, 'title': f'Short {sid}', 'yt_title': f'YT {sid}', 'destination': 'both' if len(bs) == 2 else (bs[0] if bs else 'todd'), 'brands': bs, 'timeline': f'Ep 24 {sid} (L)', 'cover_timeline': None,
               'master': f(f'Reels/YT {sid}.mp4'), 'frames': 900, 'seconds': 30.0, 'loudness': {'lufs': -14.2, 'true_peak': -1.3}, 'cover': f(f'Reels/Thumbnails/YT {sid}.jpg'), 'cover_kind': 'ai', 'cover_headline': 'X', 'cover_sha': 'x',
               'copy': {'caption': f'Hook {sid}.\n#filmmaking #podcast #c #d #e', 'first_comment': 'q?', 'yt_title': f'YT {sid}', 'fb_title': f'FB {sid}' if 'cwc' in bs else '', 'playlist': {b: 'tcl_shorts' for b in bs},
                        'ig_collab': 'willco_media' if sid == 's02' else 'none', 'hook_text': ['HOOK']}}
              for sid, bs in [('s01', ['cwc', 'tcl']), ('s02', ['cwc', 'tcl']), ('s03', ['cwc']), ('s04', ['tcl']), ('s05', ['cwc', 'tcl']), ('s06', ['cwc']), ('s07', [])]]
    w(f'{RW}/delivery.json', {'at': 'x', 'locked_at': 'x', 'skill': 'CWC_PodReels', 'episode': 'Ep24', 'show': 'creative-lens', 'shorts': shorts,
                              'cleanup': {'timelines_removed': [], 'nas_recycled': [[f'{ep}/Shorts/B-Roll/x.png', f'{T}/#recycle/CWC_PodReels/creative-lens Ep24 lock 20261003-092106/prev.mp4']], 'problems': []},
                              'final_dir': f'{ep}/Final/Reels', 'dashboard': f'{ep}/Final/Reels/Ep 24 Reels Dashboard.html', 'delivered_at': 'x'})
    w(f'{root}/data/youtube_route.json', {'state': 'flip_works', 'by': 'selftest: the flip works', 'at': 'x'})
    w(f'{RW}/checked.json', {'deliver': ['s02', 's01', 's03', 's05', 's04', 's06']})
    w(f'{R}/calendar/youtube.json', {'at': 'x', 'channels': {
        'cwc': [{'id': 'v1', 'title': 'Existing long', 'privacy': 'private', 'publish_at': '2026-10-05T18:00:00Z', 'seconds': 600, 'live': False, 'kind': 'long'},
                {'id': 'v2', 'title': 'Ep. 24 live', 'privacy': 'public', 'published_at': '2026-10-01T23:00:00Z', 'seconds': 5400, 'live': True, 'kind': 'live'}], 'tcl': []}})
    for b in ('cwc', 'tcl'):
        w(f'{R}/calendar/metricool_{b}.json', {'at': 'x', 'brand': b, 'from': '2026-10-01', 'to': '2026-10-31',
                                                 'posts': [{'id': 'm1', 'at': '2026-10-02T12:00-04:00', 'networks': ['instagram'], 'text': 'x'}] if b == 'cwc' else []})
        w(f'{T}/best_raw.json', {'data': [{'dayOfWeek': d, 'bestTimesByHour': [{'hourOfDay': h, 'value': v + (100 if (d, h) == (7, 9) else 0)} for h, v in ((9, 1), (11, 5), (15, 4), (19, 3))]} for d in (7, 1, 2, 3, 4, 5, 6)]})
        res = subprocess.run([sys.executable, f'{HERE}/cal.py', 'besttimes', R, b, f'{T}/best_raw.json'], env=env, capture_output=True, text=True); assert res.returncode == 0, res.stderr   # the connector's answer, verbatim
    w(f'{R}/calendar/peaks_cwc.json', {'at': 'x', 'days': {str(d): {'most': [13, 14], 'some': [12]} for d in range(7)}, 'no_data': False})
    w(f'{R}/calendar/peaks_tcl.json', {'at': 'x', 'days': {str(d): {'most': [], 'some': []} for d in range(7)}, 'no_data': True})
    w(f'{T}/shot.png', 'png')
    for b, n in (('cwc', 18), ('tcl', 0)):
        res = subprocess.run([sys.executable, f'{HERE}/cal.py', 'counts', R, b, f'2026-10={n}', '--evidence', f'{T}/shot.png'], env=env, capture_output=True, text=True); assert res.returncode == 0, res.stderr
    w(f'{T}/channel_metrics.json', {'updated': '2026-10-02', 'audience': {'best_slots_et': ['Tue 11 AM']}})
    w(f'{R}/holistic.json', {'summary': 'Selftest episode: a news clip (t02) leads, four clips, six reels; s06 held for the test.',
                             'overrides': [{'ref': 's05', 'kind': 'short', 'rank': 1, 'why': 'price number in frame 1: TikTok gear-price posts 10x median (scrape insights)'}],
                             'hold': [{'ref': 's06', 'kind': 'short', 'why': 'abstract AI opinion: 0.06-0.2x median on every platform (scrape avoid list)'}],
                             'notes': ['selftest note for the card']})
    y = json.load(open(f'{R}/calendar/youtube.json')); y['channels']['tcl'].append({'id': 'TESTCARD', 'title': 'API upload test - safe to delete', 'privacy': 'public', 'published_at': '2026-10-02T14:00:00Z', 'seconds': 8, 'live': False, 'kind': 'short'})
    w(f'{R}/calendar/youtube.json', y); w(f'{root}/data/youtube_route.json', {'state': 'flip_works', 'by': 'selftest: the flip works', 'at': 'x', 'test': {'video_id': 'TESTCARD'}})
    return env, R, CW, RW, ep

C_DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
def run(env, *a, inp=None): return subprocess.run([sys.executable, *a], env=env, capture_output=True, text=True, input=inp)
def plan(env, R, *extra, touch=True):
    if touch and os.path.exists(f'{R}/holistic.json'): os.utime(f'{R}/holistic.json', None)
    return run(env, f'{HERE}/plan.py', 'build', R, '--now', NOW, *extra)

def main():
    T = tempfile.mkdtemp(prefix='cwc_podrun_selftest_')
    try:
        env, R, CW, RW, ep = fixture(T)
        os.makedirs(f'{T}/nas/Ep. 25 - 10:8', exist_ok=True)
        res = subprocess.run([sys.executable, f'{HERE}/intake.py', f'{T}/nas/Ep. 25 - 10:8', '--show', 'creative-lens'], env=env, capture_output=True, text=True)
        check('GATE the posting window is the first question: intake without it -> exit 2, the run exists with a proposal only',
              res.returncode == 2 and 'window' in res.stderr and not json.load(open(f'{T}/root/run/creative-lens/Ep25/run.json')).get('window'), res.stderr[-200:])
        res = subprocess.run([sys.executable, f'{HERE}/intake.py', f'{T}/nas/Ep. 25 - 10:8', '--show', 'creative-lens', '--window', '2026-10-09', '2026-10-15', '--by', 'selftest'], env=env, capture_output=True, text=True)
        check('GATE the posting yes is asked at kickoff with the window: a window alone -> exit 2, asks the yes',
              res.returncode == 2 and 'posting yes' in res.stderr and 'window (' not in res.stderr, res.stderr[-300:])
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
        check('TCL-only reel: no delay (Fri) - the skill\'s own test card on that day is not a post', it['yts-s04-tcl']['publish_at'][:10] == '2026-10-02')
        check('the holistic read\'s notes lead the card notes', P['warnings'][0] == 'read: selftest note for the card', str(P['warnings'][:2]))
        check('same-topic reel s01 not on the day of clip t01', all(it[f'yts-s01-{b}']['publish_at'][:10] != it[f'clip-t01-{b}']['publish_at'][:10] for b in ('cwc', 'tcl')))
        # collaborators
        soc = {i['id']: i for i in P['items'] if i['kind'] == 'social'}
        check('collab: Colden + guest -> the guest, on the CWC post only', soc['mc-s01-cwc']['ig_collabs'] == ['willco_media'] and soc['mc-s01-tcl']['ig_collabs'] == [])
        check('collab: only Colden (+ a 2-word "yeah" from Jake) -> none', soc['mc-s02-cwc']['ig_collabs'] == [] and soc['mc-s02-tcl']['ig_collabs'] == [])
        check('collab: PodReels copy disagreeing with the speakers is flagged', any('reel s02' in x and 'speakers win' in x for x in P['warnings']))
        check('collab: TCL-only reel -> collaborators on TCL', soc['mc-s04-tcl']['ig_collabs'] == ['willco_media'])
        check('collab: "none" in the PodReels copy is no collaborator (no false flag)', not any('@none' in x for x in P['warnings']))
        check('collab: one set per reel', all(sum(1 for i in soc.values() if i['ref'] == r and i['ig_collabs']) <= 1 for r in {i['ref'] for i in soc.values()}))
        # one quota pool (2026-10-07): another run's approved, not-yet-uploaded videos are counted, in go-live order
        O = f'{T}/root/run/creative-lens/Ep99'; os.makedirs(O, exist_ok=True)
        w(f'{O}/plan.json', {'sha': 'x1', 'items': [{'id': 'yts-a', 'route': 'youtube_api', 'publish_at': '2026-10-03T10:00:00-04:00'},
                                                   {'id': 'yts-b', 'route': 'youtube_api', 'publish_at': '2026-10-04T10:00:00-04:00'},
                                                   {'id': 'mc-a', 'route': 'metricool', 'publish_at': '2026-10-03T10:00:00-04:00'}],
                             'quota': {'per_item': {'yts-a': 1700, 'yts-b': 1700}}})
        w(f'{O}/publish_log.json', {'yts-a': {'video_id': 'v1'}})
        w(f'{O}/run.json', {'plan_approval': {'sha': 'x1'}})
        res = run(env, '-c', f'import sys, json; sys.path.insert(0, {HERE!r}); import plan; print(json.dumps(plan.other_runs_owed({R!r})))')
        owed = json.loads(res.stdout or 'null') if res.returncode == 0 else None
        check('quota: another approved run\'s not-yet-uploaded YouTube video is counted (uploaded one + Metricool post are not)',
              owed and owed[1] == [['yts-b', 1700, '2026-10-04T10:00:00-04:00']], res.stdout[-300:] + res.stderr[-300:])
        w(f'{O}/run.json', {'plan_approval': {'sha': 'old'}})
        res = run(env, '-c', f'import sys, json; sys.path.insert(0, {HERE!r}); import plan; print(json.dumps(plan.other_runs_owed({R!r})))')
        check('quota: a run whose current plan is not approved owes nothing', res.returncode == 0 and json.loads(res.stdout)[1] == [], res.stderr[-300:])
        shutil.rmtree(O)
        # the real delivery shapes
        check('clip category + playlists read from the v2 objects', it['clip-t01-cwc']['category'] == '1' and it['clip-t01-cwc']['playlists'] == ['PLx'])
        check('Short: the channel\'s category (Film & Animation), tags from the caption, the brand\'s own TCL Shorts playlist',
              all(i['category'] == '1' and i['tags'][:2] == ['filmmaking', 'podcast'] for i in P['items'] if i['kind'] == 'yt_short')
              and it['yts-s01-cwc']['playlists'] == ['PLwTk-C92V3R-hJiEy5tOwzV6OG3aFcGmk'] and it['yts-s01-tcl']['playlists'] == ['PLEovtEg4gZSQcf6yQ9Gdqf_y-mSB5Q3EN'], str(it['yts-s01-cwc']['playlists']))
        check('a Todd-only reel is listed, never posted', not any(i['ref'] == 's07' for i in P['items']) and any('s07' in x for x in P['skipped']))
        bt_ = {(x['dow'], x['hour']): x['value'] for x in json.load(open(f'{R}/calendar/best_cwc.json'))['rows']}
        check('Metricool best times read verbatim: dayOfWeek 7 = Sunday, 1 = Monday', bt_.get((6, 9)) == 101 and bt_.get((0, 9)) == 1 and len(bt_) == 28, str(sorted(bt_.items())[:3]))
        check('reels land on the best TikTok hour of their day (Sunday 09:00 here, else 11:00)', all(i['publish_at'][11:13] == ('09' if i['weekday'] == 'Sun' else '11') for i in P['items'] if i['kind'] == 'yt_short' and i['brand'] == 'tcl'), str([(i['weekday'], i['publish_at'][11:16]) for i in P['items'] if i['kind'] == 'yt_short']))
        # routes + caps
        check('no YouTube through Metricool; TCL has no Facebook', all('youtube' not in i['networks'] for i in soc.values()) and all('facebook' not in i['networks'] for i in soc.values() if i['brand'] == 'tcl'))
        mc = [i for i in soc.values() if i['brand'] == 'cwc' and i['route'] == 'metricool']; man = [i for i in soc.values() if i['brand'] == 'cwc' and i['route'] == 'manual']
        check('CWC cap: 18 used (Chrome count) -> 2 via Metricool, the rest manual', len(mc) == 2 and len(man) == 2, f'{len(mc)}/{len(man)}')
        check('the best-ranked reels get the Metricool slots (s05 moved up by the holistic read)', sorted(i['ref'] for i in mc) == ['s02', 's05'])
        check('every YouTube item uploads through the API, private until flipped', all(i['route'] == 'youtube_api' and i['schedule'] == 'flip' for i in P['items'] if i['kind'] != 'social'))
        check('every YouTube upload can be up before its slot', all(i['upload_day'] <= i['publish_at'][:10] for i in P['items'] if i['kind'] != 'social'))
        check('holistic override: s05 is the first CWC reel', min((i for i in P['items'] if i['kind'] == 'yt_short' and i['brand'] == 'cwc'), key=lambda i: i['publish_at'])['ref'] == 's05')
        check('reels placed in rank order on CWC (s05, s02, then s01 / s03)', [i['ref'] for i in sorted((i for i in P['items'] if i['kind'] == 'yt_short' and i['brand'] == 'cwc'), key=lambda i: i['publish_at'])][:2] == ['s05', 's02'])
        check('holistic hold: s06 out and listed', not any(i['ref'] == 's06' for i in P['items']) and any('HELD short s06' in x for x in P['skipped']))
        check('weekdays computed', all(i['weekday'] == ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][dt.datetime.fromisoformat(i['publish_at']).weekday()] for i in P['items']))
        # ---- gates fire
        r0 = json.load(open(f'{R}/run.json')); r1 = dict(r0); r1.pop('window'); w(f'{R}/run.json', r1); res = plan(env, R)
        check('GATE no confirmed window -> exit 2 (ask)', res.returncode == 2, res.stderr[-200:]); w(f'{R}/run.json', r0)
        os.rename(f'{R}/calendar/counts_cwc.json', f'{T}/c.bak'); res = plan(env, R)
        check('GATE no confirmed Metricool count -> exit 1', res.returncode == 1, res.stderr[-200:]); os.rename(f'{T}/c.bak', f'{R}/calendar/counts_cwc.json')
        res = subprocess.run([sys.executable, f'{HERE}/cal.py', 'counts', R, 'cwc', '2026-10=0', '--by', 'selftest: a wrong count'], env=env, capture_output=True, text=True); res = plan(env, R)
        check('GATE a Metricool count below what its own API lists -> exit 1', res.returncode == 1 and 'provably' in res.stderr, res.stderr[-200:])
        subprocess.run([sys.executable, f'{HERE}/cal.py', 'counts', R, 'cwc', '2026-10=18', '--evidence', f'{T}/shot.png'], env=env, capture_output=True, text=True)
        os.utime(f'{R}/calendar/peaks_cwc.json', (0, 0)); res = plan(env, R)
        check('GATE stale viewer peaks -> exit 1', res.returncode == 1, res.stderr[-200:]); os.utime(f'{R}/calendar/peaks_cwc.json', None)
        os.utime(f'{R}/calendar/youtube.json', (0, 0)); res = plan(env, R)
        check('GATE stale YouTube calendar -> exit 1', res.returncode == 1, res.stderr[-200:]); os.utime(f'{R}/calendar/youtube.json', None)
        ph = json.load(open(f'{RW}/phrases.json')); ph[60]['w'] = [['x', 0, 0]] * 4; w(f'{RW}/phrases.json', ph); res = plan(env, R)
        sj = {i['id']: i for i in json.load(open(f'{R}/plan.json'))['items'] if i['kind'] == 'social'}
        check('collab: a host with a real line (Jake, 4 words) is a collaborator, his handle from collaborators.json, on the CWC post only',
              res.returncode == 0 and sj['mc-s02-cwc']['ig_collabs'] == ['jakedirectedthis'] and sj['mc-s02-tcl']['ig_collabs'] == [], res.stderr[-200:])
        ph[60]['who'] = 'Zed'; w(f'{RW}/phrases.json', ph); res = plan(env, R)
        check('GATE a speaker with no handle on file -> exit 2 (never guessed)', res.returncode == 2 and 'Zed' in res.stderr, res.stderr[-200:])
        ph[60]['who'] = 'Jake'; ph[60]['w'] = [['x', 0, 0]] * 2; w(f'{RW}/phrases.json', ph)
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
        rd = json.load(open(f'{RW}/delivery.json')); r2 = dict(rd); r2.pop('delivered_at'); w(f'{RW}/delivery.json', r2); res = plan(env, R)
        check('GATE reels locked but not delivered to Final/Reels -> exit 1', res.returncode == 1 and 'not delivered' in res.stderr, res.stderr[-200:]); w(f'{RW}/delivery.json', rd)
        yr = f'{T}/root/data/youtube_route.json'; os.rename(yr, yr + '.bak'); res = plan(env, R)
        check('GATE the YouTube route is not tested -> exit 2 (ask)', res.returncode == 2 and 'flip-test' in res.stderr, res.stderr[-200:])
        w(yr, {'state': 'test_uploaded', 'test': {'url': 'https://studio.youtube.com/video/x/edit'}}); res = plan(env, R)
        check('GATE a test video is up but nobody tried the flip -> exit 2', res.returncode == 2, res.stderr[-200:])
        w(yr, {'state': 'locked', 'by': 'selftest'}); res = plan(env, R)
        check('GATE API uploads locked private -> exit 2, nothing planned', res.returncode == 2 and 'locked' in res.stderr, res.stderr[-200:])
        w(yr, {'state': 'audit_passed', 'by': 'selftest'}); res = plan(env, R)
        check('after the audit: publishAt at upload', res.returncode == 0 and all(i['schedule'] == 'publishAt' for i in json.load(open(f'{R}/plan.json'))['items'] if i['kind'] != 'social'), res.stderr[-200:])
        os.remove(yr); os.rename(yr + '.bak', yr)
        os.utime(f'{R}/holistic.json', None); res = run(env, f'{HERE}/plan.py', 'build', R, '--now', '2026-10-02T09:00:00-04:00')
        Pd = json.load(open(f'{R}/plan.json')) if res.returncode == 0 else {'items': []}
        check('a window that starts today: same-day posts, never sooner than now + 90 min', res.returncode == 0 and any(i['publish_at'][:10] == '2026-10-02' and i['kind'] != 'social' for i in Pd['items'])
              and all(i['publish_at'] >= '2026-10-02T10:30' for i in Pd['items']), res.stderr[-300:])
        res = run(env, f'{HERE}/plan.py', 'build', R, '--now', '2026-10-04T09:00:00-04:00')
        Pd = json.load(open(f'{R}/plan.json')) if res.returncode == 0 else {'items': [], 'warnings': []}
        check('a window that has started is planned from today on, and says so', res.returncode == 0 and all(i['publish_at'][:10] >= '2026-10-04' for i in Pd['items']) and any('window started' in x for x in Pd['warnings']), res.stderr[-300:])
        res = run(env, f'{HERE}/plan.py', 'build', R, '--now', '2026-10-09T09:00:00-04:00', '--waive-scrape', 'selftest'); check('GATE a window that has ended -> exit 2 (ask again)', res.returncode == 2 and 'ended' in res.stderr, res.stderr[-200:])
        res = plan(env, R); check('plan rebuilds clean', res.returncode == 0, res.stderr[-300:])
        # ---- Colden uploads (2026-10-08, Ep 25): HE uploads every video in Studio, the API only adds the metadata - paced by metadata units; youtube.py upload refuses
        r0 = json.load(open(f'{R}/run.json')); r1 = dict(r0, colden_uploads={'words': 'selftest: I will upload all YouTube videos', 'at': NOW}); w(f'{R}/run.json', r1); res = plan(env, R)
        Pq = json.load(open(f'{R}/plan.json')) if res.returncode == 0 else {'quota': {'per_item': {}}, 'items': [], 'sha': '', 'rules': ''}
        ins = json.load(open(f'{HERE}/../references/rules.json'))['quota_cost']['videos.insert']
        check('Colden uploads: the plan paces by metadata units only (no videos.insert) and says so', res.returncode == 0 and Pq['quota'].get('colden_uploads') and Pq['quota']['per_item']
              and all(0 < n < ins for n in Pq['quota']['per_item'].values()) and 'COLDEN uploads' in open(f'{R}/plan.md').read(), res.stderr[-300:] + str(Pq['quota'].get('per_item')))
        r1['plan_approval'] = {'sha': Pq['sha'], 'by': 'selftest', 'at': NOW, 'rules': Pq['rules']}; w(f'{R}/run.json', r1)
        res = run(env, f'{HERE}/youtube.py', 'upload', R)
        check('GATE Colden uploads: youtube.py upload refuses (adopt is the way), the API never inserts', res.returncode == 1 and 'adopt' in res.stderr, res.stderr[-300:])
        w(f'{R}/run.json', r0); res = plan(env, R); check('plan rebuilds clean without the flag (API uploads again)', res.returncode == 0 and not json.load(open(f'{R}/plan.json'))['quota'].get('colden_uploads'), res.stderr[-300:])
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
        # ---- reslot (2026-10-08: wake-ups died with the session; YouTube slots move, Metricool never; shorts may double up, clips never)
        keep = {f: open(f'{R}/{f}').read() for f in ('plan.json', 'run.json', 'plan.md')}
        yts = [i for i in P['items'] if i['kind'] == 'yt_short' and i['brand'] == 'cwc']; ytc = [i for i in P['items'] if i['kind'] == 'yt_clip' and i['brand'] == 'cwc']
        soc = next(i for i in P['items'] if i['kind'] == 'social')
        rs_ = lambda *mv: run(env, f'{HERE}/plan.py', 'reslot', R, *mv, '--by', 'selftest: good', '--now', NOW)
        res = rs_(f'{soc["id"]}=2026-10-06T21:00'); check('reslot: a Metricool post never moves (it is already at Metricool)', res.returncode == 1 and 'Metricool' in res.stderr, res.stderr[-200:])
        res = rs_(f'{yts[0]["id"]}={NOW[:16]}'); check('reslot: a slot sooner than now + min lead is refused', res.returncode == 1 and 'sooner' in res.stderr, res.stderr[-200:])
        if len(ytc) > 1:
            res = rs_(f'{ytc[0]["id"]}={ytc[1]["publish_at"][:10]}T20:00'); check('reslot: never two clips on one channel on one day', res.returncode == 1 and 'yt_clip' in res.stderr, res.stderr[-300:])
        days = sorted({i['publish_at'][:10] for i in P['items']}); free = [d for d in days if d > NOW[:10] and not any(i['brand'] == 'cwc' and i['kind'] in ('yt_short', 'yt_clip') and i['publish_at'][:10] == d for i in P['items'])]
        D = (free or [P['window']['end']])[-1]; mv = yts[-1]
        res = rs_(f'{mv["id"]}={D}T20:15'); P2 = json.load(open(f'{R}/plan.json')); r2 = json.load(open(f'{R}/run.json')); m2 = next(i for i in P2['items'] if i['id'] == mv['id'])
        check('reslot: a Short moves, the sha is new and his words are the approval, Metricool posts untouched',
              res.returncode == 0 and P2['sha'] != P['sha'] and r2['plan_approval']['sha'] == P2['sha'] and 'selftest: good' in r2['plan_approval']['by']
              and m2['publish_at'].startswith(f'{D}T20:15') and m2['weekday'] == C_DAYS[dt.date.fromisoformat(D).weekday()] and m2['moved']['from'] == mv['publish_at']
              and [i for i in P2['items'] if i['kind'] == 'social'] == [i for i in P['items'] if i['kind'] == 'social'], res.stderr[-400:])
        others = [i for i in yts if i['id'] != mv['id']][:2]
        res = rs_(*[f'{o["id"]}={D}T{h}' for o, h in zip(others, ('20:30', '20:45'))]); check('reslot: a third Short on one channel on one day is refused (two may double up)', res.returncode == 1 and ('Shorts' in res.stderr or 'yt_short' in res.stderr), res.stderr[-300:])
        r3 = json.load(open(f'{R}/run.json')); r3['plan_approval']['sha'] = 'deadbeef0000'; w(f'{R}/run.json', r3)
        res = rs_(f'{mv["id"]}={D}T21:00'); check('reslot: an unapproved plan is never moved', res.returncode == 1 and 'APPROVED' in res.stderr, res.stderr[-200:])
        # ---- adopt (his own Studio uploads): exactly one private match by file name (+ length), never a guess; never a second copy
        for f, txt in keep.items(): open(f'{R}/{f}', 'w').write(txt)
        vi = [i for i in P['items'] if i['kind'] in ('yt_clip', 'yt_short')][:3]
        fake = [{'id': 'VID_A', 'title': os.path.splitext(os.path.basename(vi[0]['files']['video']))[0].upper(), 'privacy': 'private', 'seconds': 0, 'brand': vi[0]['brand']},
                {'id': 'VID_B1', 'title': os.path.basename(vi[1]['files']['video']), 'privacy': 'private', 'seconds': 0, 'brand': vi[1]['brand']},
                {'id': 'VID_B2', 'title': os.path.basename(vi[1]['files']['video']), 'privacy': 'private', 'seconds': 0, 'brand': vi[1]['brand']},
                {'id': 'VID_C', 'title': os.path.basename(vi[2]['files']['video']), 'privacy': 'private', 'seconds': 999, 'brand': vi[2]['brand']}]
        code = (f'import sys, json; sys.path.insert(0, {HERE!r}); import youtube as Yt; F = {json.dumps(fake)!r}; F = json.loads(F)\n'
                f'Yt.by_hand = lambda b, cache=None: [v for v in F if v["brand"] == b]\nYt.seconds = lambda p: 30.0\nYt.adopt({R!r})')
        res = run(env, '-c', code); M = json.load(open(f'{R}/publish/adopt_map.json')).get('map', {}) if res.returncode == 0 else {}
        check('adopt: one private upload with the file\'s name (case/punctuation ignored) is matched', M.get(vi[0]['id'], {}).get('video_id') == 'VID_A', res.stdout[-300:] + res.stderr[-300:])
        check('adopt: two uploads with the same name -> listed, never guessed', vi[1]['id'] not in M and 'NOT MATCHED' in res.stdout, res.stdout[-300:])
        check('adopt: the right name but the wrong length -> not matched', vi[2]['id'] not in M, res.stdout[-300:])
        code = (f'import sys, json; sys.path.insert(0, {HERE!r}); import youtube as Yt; M = json.load(open({R + "/publish/adopt_map.json"!r})); M["sha"] = "old"; json.dump(M, open({R + "/publish/adopt_map.json"!r}, "w"))\n'
                f'Yt.adopt({R!r}, apply=True)')
        res = run(env, '-c', code); check('adopt --apply: a map made for another plan is refused', res.returncode == 1 and 'run adopt again' in res.stderr, res.stderr[-200:])
        src = open(f'{HERE}/youtube.py').read()
        check('GATE never a second copy: every API insert first checks the channel for his own upload of that file',
              src.index('dup = [v[\'id\'] for v in by_hand(') < src.index("vid = Y.insert(it['brand'], item, P['youtube_schedule'])"))
        nx = run(env, f'{HERE}/next.py', R, '--json'); check('next.py runs (exit 0) and reports a stage', nx.returncode == 0 and json.loads(nx.stdout or '{}').get('stage'), nx.stderr[-300:])
        r0 = json.load(open(f'{R}/run.json')); r1 = dict(r0); r1.pop('post_ok'); w(f'{R}/run.json', r1)
        yu = run(env, f'{HERE}/youtube.py', 'upload', R); mq = run(env, f'{HERE}/metricool.py', 'payloads', R, '--now', '2026-10-01T23:45:00-04:00')
        check('GATE no posting yes from kickoff -> the tap alone posts nothing (YouTube upload + Metricool payloads refuse)',
              yu.returncode == 1 and 'kickoff' in yu.stderr and mq.returncode == 1 and 'kickoff' in mq.stderr, yu.stderr[-200:] + mq.stderr[-200:])
        w(f'{R}/run.json', r0)
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
        # ---- the go-live pieces (2026-10-09): a thumbnail YouTube can take, a refused one that blocks + alerts, the related-video gate, the watch daemon
        code = (f'import sys, os; sys.path.insert(0, {HERE!r}); import ytapi as Y; from PIL import Image\n'
                f'p = {T!r} + "/big.png"; Image.frombytes("RGB", (1080, 1920), os.urandom(1080 * 1920 * 3)).save(p)\n'
                f'f = Y.thumb_file(p); print(os.path.getsize(p), f, os.path.getsize(f))')
        import site; res = run(dict(env, PYTHONPATH=site.getusersitepackages()), '-c', code); parts = (res.stdout.strip().splitlines() or [''])[-1].split()      # PIL lives in the real user site, the fake HOME hides it
        check('thumbnail: a cover over 2 MB (a 1080x1920 PNG) is re-encoded to a JPEG under 2 MB before thumbnails.set (C&T 10-6: 5 Shorts refused)',
              res.returncode == 0 and len(parts) == 3 and int(parts[0]) > 2_000_000 and parts[1].endswith('.jpg') and int(parts[2]) <= 2_000_000, res.stdout[-200:] + res.stderr[-300:])
        sh = next(i for i in P['items'] if i['kind'] == 'yt_short'); lg = json.load(open(f'{R}/publish_log.json'))
        lg[sh['id']] = {'route': 'youtube_api', 'video_id': 'VSHORT', 'schedule': 'flip', 'publish_at': sh['publish_at'], 'done': ['video']}; w(f'{R}/publish_log.json', lg)
        code = (f'import sys, json; sys.path.insert(0, {HERE!r}); import youtube as Yt\n'
                f'class Y:\n    def set_thumbnail(self, *a): raise RuntimeError("MediaUploadSizeError: Media larger than: 2097152")\n'
                f'    def add_captions(self, *a): pass\n    def add_to_playlist(self, *a): pass\n'
                f'log = json.load(open({R + "/publish_log.json"!r})); it = json.loads({json.dumps(sh)!r})\nYt.extras(Y(), {R!r}, it, log)')
        res = run(tenv, '-c', code); lg = json.load(open(f'{R}/publish_log.json')); e = lg.get(sh['id']) or {}
        check('GATE a thumbnail YouTube refuses leaves the item NOT complete, records the problem and alerts Colden once (never silent)',
              res.returncode == 0 and not e.get('complete') and 'MediaUploadSize' in (e.get('problems') or {}).get('thumbnail', '') and 'refused the thumbnail' in open(f'{T}/tg.log').read(), res.stderr[-300:])
        res = run(env, f'{HERE}/pin.py', 'mark', R, sh['id'], 'cover', 'selftest: set the cover in Studio by hand'); e = json.load(open(f'{R}/publish_log.json'))[sh['id']]
        check('pin.py mark cover: a cover set in Studio clears the problem and completes the item', res.returncode == 0 and e.get('complete') and 'thumbnail' in e['done'] and not e.get('problems'), res.stderr[-200:])
        dj = json.load(open(f'{CW}/delivery.json')); dj['full_episode'] = {'cwc': {'id': 'FULLCWC', 'title': 'Ep. 24 live'}, 'tcl': {'id': 'FULLTCL', 'title': 'Ep. 24 live'}}; w(f'{CW}/delivery.json', dj)
        rd = run(env, f'{HERE}/related.py', 'due', R)
        check('GATE related.py due exits 3 while an uploaded Short has no Related video recorded', rd.returncode == 3 and f'SET {sh["id"]}' in rd.stdout, rd.stdout[-200:] + rd.stderr[-300:])
        rd = run(tenv, f'{HERE}/related.py', 'due', R, '--alert', '--hours', '999999'); rd2 = run(tenv, f'{HERE}/related.py', 'due', R, '--alert', '--hours', '999999')
        check('related --alert: ONE Telegram line for a Short near its slot, never twice', rd.returncode == 3 and open(f'{T}/tg.log').read().count('RELATED VIDEO not set') == 1 and rd2.returncode == 3, rd.stderr[-300:])
        want = 'FULLCWC' if sh['brand'] == 'cwc' else 'FULLTCL'
        rm = run(env, f'{HERE}/related.py', 'mark', R, sh['id'], want, 'selftest: set in Studio, saved'); rd = run(env, f'{HERE}/related.py', 'due', R)
        check('related.py mark + due -> exit 0 once every uploaded Short links where it should', rm.returncode == 0 and rd.returncode == 0, rm.stderr[-200:] + rd.stdout[-200:])
        code = (f'import sys, json; sys.path.insert(0, {HERE!r}); import next as N, common as C; r = C.run({R!r}); r["window"]["end"] = "2099-01-01"; out = {{"stage": "x", "done": [], "waiting": [], "next": [], "products": {{}}}}\n'
                f'N.ours(r, {R!r}, out); print(json.dumps(out["next"]))')
        res = run(env, '-c', code); nxt = json.loads(res.stdout or '[]') if res.returncode == 0 else []
        check('next.py: no watch daemon -> GO-LIVE WATCH NOT RUNNING is the first next step; a Short without its related video is listed',
              bool(nxt) and nxt[0].startswith('GO-LIVE WATCH NOT RUNNING') and not any('RELATED video not set' in x for x in nxt), res.stdout[-300:] + res.stderr[-300:])
        code = (f'import sys, os, json; sys.path.insert(0, {HERE!r}); import watch as WT, common as C\n'
                f'a = WT.running(); n = len(WT.active_runs()); os.makedirs(C.CFG, exist_ok=True); open(WT.PID, "w").write(str(os.getpid())); C.save(WT.HEART, {{"pid": os.getpid(), "at": C.now(), "runs": {{}}}})\n'
                f'print(a, n, WT.running())')
        res = run(env, '-c', code); check('watch: not running without a live pid + fresh heartbeat; this approved run is active; running once both exist', res.stdout.split() == ['False', '1', 'True'], res.stdout + res.stderr[-300:])
        for pth in (f'{T}/home/.config/cwc/podrun_watch.pid', f'{T}/home/.config/cwc/podrun_watch.json'):
            if os.path.exists(pth): os.remove(pth)
        # ---- kits, checklist, dashboard, baton
        kt = run(env, f'{HERE}/kit.py', R); kits = glob.glob(f'{glob.escape(ep)}/Final/Manual Posts/*/post.txt')
        check('kit: one folder per manual post, collaborators line present', kt.returncode == 0 and len(kits) == len([i for i in P['items'] if i['route'] == 'manual']) and all('Instagram collaborators' in open(k).read() for k in kits), kt.stderr[-300:])
        ck = run(env, f'{HERE}/youtube.py', 'checklist', R); body = open(f'{R}/publish/studio_checklist.md').read() if ck.returncode == 0 else ''
        check('Studio checklist: monetization ON + the flip time on every video', body.count('Monetization: ON') == len([i for i in P['items'] if i['kind'] != 'social']) and 'Private -> Schedule' in body, ck.stderr[-200:])
        db = run(env, f'{HERE}/dashboard.py', R); check('dashboard written to the episode Final folder', db.returncode == 0 and os.path.exists(f'{ep}/Final/Ep24 Posting Plan.html'), db.stderr[-300:])
        bt = lambda *a: run(env, f'{HERE}/baton.py', *a).returncode; BF = f'{T}/home/.config/cwc/resolve_baton.json'
        w(f'{T}/stub/DaVinciResolveScript.py', 'def scriptapp(name): return None\n')          # rs.py imports THIS, never the real Resolve
        renv = dict(env, PYTHONPATH=f'{T}/stub')
        rs = lambda skill: subprocess.run([sys.executable, f'{SKILLS}/{skill}/scripts/rs.py', '5', os.devnull], env=renv, capture_output=True, text=True).returncode
        subs = [k for k in ('CWC_PodClips', 'CWC_PodReels') if os.path.exists(f'{SKILLS}/{k}/scripts/rs.py')]
        check('baton: no tandem run -> no file, every rs.py passes the check (2 = the stub answers "no Resolve")', not os.path.exists(BF) and all(rs(k) == 2 for k in subs + ['CWC_PodRun']))
        check('baton: tandem open, nobody holds it -> every rs.py refuses (4)', bt('open', R) == 0 and all(rs(k) == 4 for k in subs + ['CWC_PodRun']))
        check('baton: one skill at a time', bt('take', 'CWC_PodClips', 'build t01') == 0 and bt('take', 'CWC_PodReels', 'build s01') == 4 and bt('give', 'CWC_PodReels') == 1 and bt('close') == 1)
        check('baton: the holder passes its rs.py, the other skill is refused', len(subs) == 2 and rs('CWC_PodClips') == 2 and rs('CWC_PodReels') == 4 and rs('CWC_PodRun') == 4, str(subs))
        check('baton: give keeps the tandem open (free), close removes the file', bt('give', 'CWC_PodClips') == 0 and json.load(open(BF)).get('owner') is None and bt('close') == 0 and not os.path.exists(BF))
        # ---- cleanup
        sc = run(env, f'{HERE}/cleanup.py', 'scan', R, '--no-resolve'); check('GATE cleanup refuses while posts are still open', sc.returncode == 1, sc.stderr[-200:])
        log = json.load(open(f'{R}/publish_log.json'))
        for i in P['items']: log.setdefault(i['id'], {'route': 'selftest', 'video_id': 'v', 'done': ['video']})
        w(f'{R}/publish_log.json', log); sc = run(env, f'{HERE}/cleanup.py', 'scan', R, '--no-resolve')
        check('GATE a video that is up without its thumbnail / captions / playlists is not handled yet', sc.returncode == 1, sc.stderr[-200:])
        for i in P['items']: log[i['id']]['complete'] = True
        w(f'{R}/publish_log.json', log)
        os.makedirs(f'{ep}/Clips/B-Roll', exist_ok=True); open(f'{ep}/Clips/B-Roll/unused.png', 'w').write('x')
        os.makedirs(f'{ep}/Shorts/Renders', exist_ok=True); open(f'{ep}/Shorts/Renders/s09 old.mp4.rejected', 'w').write('x')
        os.makedirs(f'{T}/#recycle/CWC_PodCut/Ep24 20261001-2140', exist_ok=True); open(f'{T}/#recycle/CWC_PodCut/Ep24 20261001-2140/lt.mov', 'wb').write(b'x' * 4096)
        os.makedirs(f'{T}/#recycle/CWC_PodCut/Ep23 20260920-1000', exist_ok=True)
        os.makedirs(f'{RW}/edit/s01/preview', exist_ok=True); open(f'{RW}/edit/s01/preview/p.mp4', 'wb').write(b'x' * 2 * 1024 * 1024); open(f'{RW}/edit/s01/big.json', 'wb').write(b'x' * 2 * 1024 * 1024)
        sc = run(env, f'{HERE}/cleanup.py', 'scan', R, '--no-resolve'); man = json.load(open(f'{R}/cleanup/manifest.json')) if sc.returncode == 0 else {'nas': [], 'local': [], 'notes': [], 'sha': ''}
        nas = [x['path'] for x in man['nas']]; loc = [x['path'] for x in man['local']]
        check('cleanup scan runs once every post is handled', sc.returncode == 0, sc.stderr[-300:])
        check('NAS: rejected generation + this episode\'s #recycle folders are candidates', any(p.endswith('.rejected') for p in nas) and any('CWC_PodCut/Ep24 ' in p for p in nas) and any('CWC_PodReels/creative-lens Ep24 lock' in p for p in nas), str(nas))
        check('NAS: another episode\'s and another show\'s #recycle folders are never candidates', not any('Ep23' in p or 'colden-todd' in p for p in nas))
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
              and os.path.isdir(f'{T}/#recycle/CWC_PodCut/Ep23 20260920-1000') and os.path.isdir(f'{T}/#recycle/CWC_PodReels/colden-todd Ep24 lock 20261003-100000') and os.path.exists(f'{ep}/Clips/B-Roll/unused.png'))
    finally:
        shutil.rmtree(T, ignore_errors=True)
        print(f'\n{len(PASS)} passed, {len(FAIL)} failed')
    sys.exit(1 if FAIL else 0)

if __name__ == '__main__': main()
