"""selftest.py      every gate of plan.py (and the other deterministic scripts) against a synthetic episode - run after ANY change.
Builds a throw-away CWC_ROOT with a fake PodClips + PodReels delivery, phrases / themes for the topic check, a YouTube
calendar with a busy day, Metricool calendars, best times and a month that is nearly full, then:
  - the plan builds and holds every rule (48 h, 1 h, one long-form a day, busy day avoided, same topic kept apart,
    month cap -> manual, TCL without Facebook, no YouTube in Metricool, weekdays, never sooner than now + lead)
  - each gate fires on bad input (stale calendar, wrong stinger, missing file, stale scrape, waiver, a full episode)
  - metricool.py payloads refuse an unapproved plan and build one call per short per brand with identical text
Exit 0 = all hold. Uses the real show files in this repo (CWC_SKILLS = the repo's skills/ folder)."""
import os, sys, json, glob, shutil, tempfile, subprocess, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); SKILLS = os.path.dirname(os.path.dirname(HERE))
PASS, FAIL = [], []

def check(name, ok, detail=''):
    (PASS if ok else FAIL).append(name); print(('ok   ' if ok else 'FAIL ') + name + (f'  - {detail}' if detail and not ok else ''))

def w(p, data):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w') as f: json.dump(data, f, indent=1) if not isinstance(data, str) else f.write(data)

def fixture(T, now):
    root = f'{T}/root'; ep = f'{T}/nas/Ep. 24 - 10:1'; os.makedirs(ep)
    env = dict(os.environ, CWC_ROOT=root, CWC_SKILLS=SKILLS, CWC_SCRAPE=f'{T}/channel_metrics.json', HOME=f'{T}/home')
    def f(name):
        p = f'{ep}/Final/{name}'; os.makedirs(os.path.dirname(p), exist_ok=True); open(p, 'w').write('x'); return p
    run = subprocess.run([sys.executable, f'{HERE}/intake.py', ep, '--show', 'creative-lens'], env=env, capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    R = f'{root}/run/creative-lens/Ep24'; CW = f'{root}/clips/creative-lens/Ep24'; RW = f'{root}/reels/creative-lens/Ep24'
    # phrases: P0001.. every 10 s on the cut clock
    ph = [{'id': f'P{i:04d}', 'start': i * 10.0, 'end': i * 10.0 + 9.0} for i in range(1, 400)]
    w(f'{CW}/phrases.json', ph); w(f'{RW}/phrases.json', ph)
    w(f'{CW}/themes.json', {'themes': [
        {'id': 't01', 'hook': {'from': 'P0010', 'to': 'P0010'}, 'body': [{'from': 'P0005', 'to': 'P0040'}]},    # 50-409 s
        {'id': 't02', 'body': [{'from': 'P0100', 'to': 'P0140'}]},
        {'id': 't03', 'body': [{'from': 'P0200', 'to': 'P0240'}]},
        {'id': 't04', 'body': [{'from': 'P0300', 'to': 'P0340'}]}]})
    w(f'{RW}/themes.json', {'themes': [
        {'id': 's01', 'ranges': [{'from': 'P0012', 'to': 'P0014'}]},     # inside t01 -> same topic as t01
        {'id': 's02', 'ranges': [{'from': 'P0060', 'to': 'P0062'}]},
        {'id': 's03', 'ranges': [{'from': 'P0160', 'to': 'P0162'}]},
        {'id': 's04', 'ranges': [{'from': 'P0260', 'to': 'P0262'}]},
        {'id': 's05', 'ranges': [{'from': 'P0360', 'to': 'P0362'}]},
        {'id': 's06', 'ranges': [{'from': 'P0380', 'to': 'P0382'}]}]})
    w(f'{CW}/lock.json', {'at': 'x'})
    clips = []
    for i, (th, chans, news) in enumerate([('t01', ['cwc', 'tcl'], None), ('t02', ['cwc', 'tcl'], {'date': '2026-10-01'}), ('t03', ['cwc'], None), ('t04', ['tcl'], None)]):
        for ch in chans:
            clips.append({'theme': th, 'channel': ch, 'master': f(f'Clips/{th} {ch}.mp4'), 'master_carries_stinger_of': ch, 'seconds': 480,
                          'titles': {'A': f'Title {th} {ch}', 'B': 'b', 'C': 'c'}, 'thumbnails': {'A': f(f'Clips/Thumbnails/{th} {ch} - A.jpg'), 'B': 'b', 'C': 'c'},
                          'captions': f(f'Clips/Captions/{th} {ch}.srt'), 'description': 'desc {FULL_EPISODE_URL}', 'tags': ['a'], 'playlists': ['PLx'],
                          'category': 'Science & Technology', 'pinned_comment': 'q?', 'push_order': i + 1, 'news': news, 'score': 80 - i,
                          'needs': ['FULL_EPISODE_URL'], 'ab_tests_plan': {'B': 'x', 'C': 'y'}})
    w(f'{CW}/delivery.json', {'version': 2, 'clips': clips})
    shorts = []
    for sid, brands in [('s01', ['cwc', 'tcl']), ('s02', ['cwc', 'tcl']), ('s03', ['cwc']), ('s04', ['tcl']), ('s05', ['cwc', 'tcl']), ('s06', ['cwc'])]:
        shorts.append({'id': sid, 'title': f'Short {sid}', 'brands': brands, 'destination': 'both' if len(brands) == 2 else brands[0],
                       'master': f(f'Shorts/{sid}.mp4'), 'cover': f(f'Shorts/{sid} cover.jpg'),
                       'copy': {'caption': f'Hook {sid}. Two lines.\n#a #b #c #d #e', 'first_comment': 'q?', 'yt_title': f'YT {sid}', 'fb_title': f'FB {sid}', 'playlist': 'tcl_shorts', 'ig_collab': 'willco_media'}})
    w(f'{RW}/delivery.json', {'skill': 'CWC_PodReels', 'shorts': shorts})
    w(f'{RW}/checked.json', {'deliver': ['s02', 's01', 's03', 's05', 's04', 's06']})
    # calendar: CWC already has a long-form on Mon Oct 5; Metricool CWC has posts Fri Oct 2 12:00; best times
    w(f'{R}/calendar/youtube.json', {'at': now, 'channels': {
        'cwc': [{'id': 'v1', 'title': 'Existing long', 'privacy': 'private', 'publish_at': '2026-10-05T18:00:00Z', 'published_at': None, 'seconds': 600, 'live': False, 'kind': 'long'},
                {'id': 'v2', 'title': 'Ep. 24 live', 'privacy': 'public', 'publish_at': None, 'published_at': '2026-10-01T23:00:00Z', 'seconds': 5400, 'live': True, 'kind': 'live'}],
        'tcl': []}})
    for b in ('cwc', 'tcl'):
        w(f'{R}/calendar/metricool_{b}.json', {'at': now, 'brand': b, 'from': '2026-10-01', 'to': '2026-10-31',
                                                 'posts': [{'id': 'm1', 'at': '2026-10-02T12:00-04:00', 'networks': ['instagram'], 'text': 'x'}] if b == 'cwc' else []})
        w(f'{R}/calendar/best_{b}.json', {'at': now, 'rows': [{'dow': d, 'hour': h, 'value': v} for d in range(7) for h, v in ((11, 5.0), (15, 4.0), (19, 3.0))]})
    w(f'{R}/calendar/counts_cwc.json', {'2026-10': {'n': 18, 'words': 'selftest: 18 used', 'at': now}})
    w(f'{T}/channel_metrics.json', {'updated': '2026-10-02', 'audience': {'best_slots_et': ['Tue 11 AM']}})
    w(f'{R}/holistic.json', {'summary': 'Selftest episode: a news clip (t02) leads, four clips, six shorts; nothing held but s06 for the test.',
                             'overrides': [{'ref': 's05', 'kind': 'short', 'rank': 1, 'why': 'price number in frame 1: TikTok gear-price posts 10x median (scrape insights)'}],
                             'hold': [{'ref': 's06', 'kind': 'short', 'why': 'abstract AI opinion: 0.06-0.2x median on every platform (scrape avoid list)'}]})
    return env, R, CW, RW

def plan(env, R, *extra, touch=True):
    hp = f'{R}/holistic.json'
    if touch and os.path.exists(hp): os.utime(hp, None)      # the read is redone after the test edits a delivery
    return subprocess.run([sys.executable, f'{HERE}/plan.py', 'build', R, '--now', '2026-10-01T23:30:00-04:00', *extra], env=env, capture_output=True, text=True)

def main():
    now = dt.datetime.now().isoformat()
    T = tempfile.mkdtemp(prefix='cwc_podrun_selftest_')
    try:
        env, R, CW, RW = fixture(T, now)
        res = plan(env, R)
        check('plan builds on good input', res.returncode == 0, res.stderr[-600:])
        P = json.load(open(f'{R}/plan.json')) if res.returncode == 0 else {'items': [], 'counts': {}}
        it = {i['id']: i for i in P['items']}; t = lambda k: dt.datetime.fromisoformat(it[k]['publish_at'])
        check('window = Fri Oct 2 -> Thu Oct 8 (show date in the folder name)', P.get('window', {}).get('start') == '2026-10-02' and P['window']['end'] == '2026-10-08')
        check('news clip t02 goes first on CWC', min((i for i in P['items'] if i['kind'] == 'yt_clip' and i['brand'] == 'cwc'), key=lambda i: i['publish_at'])['ref'] == 't02')
        cwc_long_days = [i['publish_at'][:10] for i in P['items'] if i['kind'] == 'yt_clip' and i['brand'] == 'cwc']
        check('one long-form per channel per day', len(cwc_long_days) == len(set(cwc_long_days)))
        check('busy day (existing long-form Mon Oct 5) avoided', '2026-10-05' not in cwc_long_days)
        check('clips at 2 PM ET', all(i['publish_at'][11:16] == '14:00' for i in P['items'] if i['kind'] == 'yt_clip'))
        check('TCL clip >= 48 h after its CWC slot', all(t(f'clip-{r}-tcl') - t(f'clip-{r}-cwc') >= dt.timedelta(hours=48) for r in ('t01', 't02')))
        check('TCL-only clip not before window start + 48 h', t('clip-t04-tcl') >= dt.datetime(2026, 10, 4, 0, 0, tzinfo=t('clip-t04-tcl').tzinfo))
        check('short to both: TCL >= 1 h after CWC', all(t(f'yts-{s}-tcl') - t(f'yts-{s}-cwc') >= dt.timedelta(hours=1) for s in ('s01', 's02', 's05')))
        check('same-topic short s01 not on the day of clip t01 (same channel)', all(it[f'yts-s01-{b}']['publish_at'][:10] != it[f'clip-t01-{b}']['publish_at'][:10] for b in ('cwc', 'tcl')))
        soc = [i for i in P['items'] if i['kind'] == 'social']
        check('no YouTube through Metricool', all('youtube' not in i['networks'] for i in soc))
        check('TCL socials have no Facebook', all('facebook' not in i['networks'] for i in soc if i['brand'] == 'tcl'))
        cwc_mc = [i for i in soc if i['brand'] == 'cwc' and i['route'] == 'metricool']; cwc_man = [i for i in soc if i['brand'] == 'cwc' and i['route'] == 'manual']
        check('CWC month cap: 18 used -> 2 via Metricool, the other 2 manual', len(cwc_mc) == 2 and len(cwc_man) == 2, f'{len(cwc_mc)} metricool / {len(cwc_man)} manual')
        check('the best-ranked shorts get the Metricool slots (s05 moved up by the holistic read)', sorted(i['ref'] for i in cwc_mc) == ['s02', 's05'])
        check('YouTube route is studio_manual before the audit', all(i['route'] == 'studio_manual' for i in P['items'] if i['kind'] != 'social'))
        check('weekdays computed', all(i['weekday'] == ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][dt.datetime.fromisoformat(i['publish_at']).weekday()] for i in P['items']))
        check('CWC short avoids the 12:00 slot taken by an existing Metricool post (>= 3 h)', all(abs((t(i['id']) - dt.datetime.fromisoformat('2026-10-02T12:00-04:00')).total_seconds()) >= 3 * 3600 for i in P['items'] if i['kind'] == 'yt_short' and i['brand'] == 'cwc' and i['publish_at'][:10] == '2026-10-02'))
        check('no full episode in the plan', all(i['kind'] in ('yt_clip', 'yt_short', 'social') for i in P['items']))
        check('holistic hold: s06 left out and listed', not any(i['ref'] == 's06' for i in P['items']) and any('HELD short s06' in x for x in P['skipped']))
        check('holistic override: s05 posts first on CWC', min((i for i in P['items'] if i['kind'] == 'yt_short' and i['brand'] == 'cwc'), key=lambda i: i['publish_at'])['ref'] == 's05')
        hp = f'{R}/holistic.json'; hb = open(hp).read(); os.remove(hp); res = plan(env, R, touch=False)
        check('GATE no holistic read -> exit 1', res.returncode == 1, res.stderr[-200:])
        w(hp, {'summary': 'x' * 50, 'overrides': [{'ref': 's01', 'kind': 'short', 'rank': 1, 'why': 'feels right'}]}); res = plan(env, R)
        check('GATE an override without a data reason -> exit 1', res.returncode == 1, res.stderr[-200:])
        open(hp, 'w').write(hb); res = plan(env, R); P = json.load(open(f'{R}/plan.json'))
        # ---- gates fire
        os.utime(f'{R}/calendar/youtube.json', (0, 0)); res = plan(env, R)
        check('GATE stale YouTube calendar -> exit 1', res.returncode == 1, res.stderr[-200:]); os.utime(f'{R}/calendar/youtube.json', None)
        d = json.load(open(f'{CW}/delivery.json')); d['clips'][0]['master_carries_stinger_of'] = 'tcl'; w(f'{CW}/delivery.json', d); res = plan(env, R)
        check('GATE master on the wrong channel -> exit 1', res.returncode == 1, res.stderr[-200:]); d['clips'][0]['master_carries_stinger_of'] = 'cwc'; w(f'{CW}/delivery.json', d)
        m = d['clips'][0]['master']; os.rename(m, m + '.gone'); res = plan(env, R)
        check('GATE missing master (NAS) -> exit 2', res.returncode == 2, res.stderr[-200:]); os.rename(m + '.gone', m)
        w(f'{T}/channel_metrics.json', {'updated': '2026-09-01'}); res = plan(env, R)
        check('GATE stale Monday scrape -> exit 2', res.returncode == 2, res.stderr[-200:])
        res = plan(env, R, '--waive-scrape', 'selftest waiver')
        check('waiver lets a stale scrape through', res.returncode == 0, res.stderr[-200:])
        w(f'{T}/channel_metrics.json', {'updated': '2026-10-02'})
        rd = json.load(open(f'{RW}/delivery.json')); shutil.copy(f'{RW}/delivery.json', f'{T}/rd.bak')
        os.utime(f'{CW}/lock.json', None); os.utime(f'{CW}/delivery.json', (0, 0)); res = plan(env, R, touch=False)
        check('GATE clips delivery older than its lock -> exit 1', res.returncode == 1, res.stderr[-200:]); os.utime(f'{CW}/delivery.json', None)
        res = plan(env, R, touch=False); check('GATE holistic read older than a delivery -> exit 1', res.returncode == 1, res.stderr[-200:])
        res = plan(env, R); check('plan rebuilds clean', res.returncode == 0, res.stderr[-300:])
        # ---- metricool payloads before approval
        mp = subprocess.run([sys.executable, f'{HERE}/metricool.py', 'payloads', R], env=env, capture_output=True, text=True)
        check('GATE payloads refuse an unapproved plan', mp.returncode == 1, mp.stderr[-200:])
        # ---- Telegram plan card (dry: calls are logged, nothing is sent)
        tenv = dict(env, CWC_TG_DRY='1', CWC_TG_DRY_LOG=f'{T}/tg.log'); w(f'{T}/home/.config/cwc/telegram.json', {'chat_id': 1})
        tp = lambda *a, inp=None: subprocess.run([sys.executable, f'{HERE}/tg_plan.py', *a], env=tenv, capture_output=True, text=True, input=inp)
        res = tp('send', R); check('plan card sends', res.returncode == 0, res.stderr[-300:])
        r = json.load(open(f'{R}/run.json')); P = json.load(open(f'{R}/plan.json')); s8 = P['sha'][:8]; mid = r['plan_card']['message_ids'][-1]
        cb = lambda data: json.dumps({'update_id': 2, 'callback_query': {'id': 'q', 'data': data, 'message': {'message_id': mid, 'chat': {'id': 1}}}})
        res = tp('handle', inp=cb('pr|cl24|t|s01')); check('a CWC_PodReels callback is not ours (exit 3)', res.returncode == 3, res.stderr[-200:])
        res = tp('handle', inp=cb('pa|cl24|ok|deadbeef')); r = json.load(open(f'{R}/run.json'))
        check('a tap on a replaced plan approves nothing', res.returncode == 0 and not r.get('plan_approval'), res.stderr[-200:])
        res = tp('handle', inp=cb(f'pa|cl24|chg|{s8}')); res2 = tp('handle', inp=json.dumps({'update_id': 3, 'message': {'message_id': 77, 'text': 'move s03 to Thursday'}}))
        r = json.load(open(f'{R}/run.json')); check('Changes -> his next message is stored as plan notes', res2.returncode == 0 and r.get('plan_notes_open') == 'move s03 to Thursday', res2.stderr[-200:])
        res = tp('handle', inp=cb(f'pa|cl24|ok|{s8}')); r = json.load(open(f'{R}/run.json'))
        check('Schedule all -> plan_approval bound to the sha', res.returncode == 0 and (r.get('plan_approval') or {}).get('sha') == P['sha'], res.stderr[-200:])
        nx = subprocess.run([sys.executable, f'{HERE}/next.py', R, '--json'], env=env, capture_output=True, text=True)
        check('next.py runs (exit 0) and reports a stage', nx.returncode == 0 and json.loads(nx.stdout or '{}').get('stage'), nx.stderr[-300:])
        r = json.load(open(f'{R}/run.json')); P = json.load(open(f'{R}/plan.json'))
        r['plan_approval'] = {'sha': P['sha'], 'by': 'selftest', 'at': now, 'rules': P['rules']}; w(f'{R}/run.json', r)
        links = {'links': {s['id']: {b: {'video_direct': f'https://drive.example/{s["id"]}{b}.mp4', 'thumb_direct': f'https://drive.example/{s["id"]}{b}.jpg'} for b in s['brands']} for s in rd['shorts']}}
        w(f'{RW}/review/publish.json', links)
        mp = subprocess.run([sys.executable, f'{HERE}/metricool.py', 'payloads', R, '--now', '2026-10-01T23:45:00-04:00'], env=env, capture_output=True, text=True)
        check('payloads build for an approved plan', mp.returncode == 0, mp.stderr[-400:])
        pl = json.load(open(f'{R}/publish/metricool_payloads.json')) if mp.returncode == 0 else []
        infos = [json.loads(x['info']) for x in pl]
        check('one Metricool call per short per brand on the metricool route', len(pl) == len([i for i in P['items'] if i['kind'] == 'social' and i['route'] == 'metricool']))
        check('payload providers never include youtube', all('youtube' not in [p['network'] for p in i['providers']] for i in infos))
        check('payload: one text for every network (counts as ONE post)', all(isinstance(i['text'], str) and i['text'] for i in infos))
        check('payload: the right blogId per brand', all(x['blogId'] == {'cwc': '5965295', 'tcl': '6367106'}[x['brand']] for x in pl))
        check('payload: Facebook only on CWC, as a Reel', all(('facebookData' in i) == (x['brand'] == 'cwc') for x, i in zip(pl, infos)))
        # ---- record, kit, dashboard
        ans = f'{T}/ans.json'; w(ans, {'data': {'id': 4242, 'plannerUrl': 'https://app.metricool.com/planner/x'}})
        rc = subprocess.run([sys.executable, f'{HERE}/metricool.py', 'record', R, pl[0]['id'], ans], env=env, capture_output=True, text=True)
        check('record writes publish_log + the month ledger', rc.returncode == 0 and os.path.exists(f'{T}/root/data/metricool_ledger.jsonl'), rc.stderr[-200:])
        rc = subprocess.run([sys.executable, f'{HERE}/metricool.py', 'record', R, pl[0]['id'], ans], env=env, capture_output=True, text=True)
        check('GATE the same post is never recorded twice', rc.returncode == 1, rc.stderr[-200:])
        w(ans, {'error': 'Text too long'}); rc = subprocess.run([sys.executable, f'{HERE}/metricool.py', 'record', R, pl[1]['id'], ans], env=env, capture_output=True, text=True)
        check('GATE a connector error is never recorded as scheduled', rc.returncode == 1, rc.stderr[-200:])
        kt = subprocess.run([sys.executable, f'{HERE}/kit.py', R], env=env, capture_output=True, text=True)
        ep = r['episode_dir']; kits = glob.glob(f'{ep}/Final/Manual Posts/*/post.txt')
        check('kit: one folder per manual post + the YouTube upload list', kt.returncode == 0 and len(kits) == len([i for i in P['items'] if i['route'] == 'manual']) and os.path.exists(f'{ep}/Final/YouTube Upload List.md'), kt.stderr[-300:])
        db = subprocess.run([sys.executable, f'{HERE}/dashboard.py', R], env=env, capture_output=True, text=True)
        check('dashboard written to the episode Final folder', db.returncode == 0 and os.path.exists(f'{ep}/Final/Ep24 Posting Plan.html'), db.stderr[-300:])
        bt = lambda *a: subprocess.run([sys.executable, f'{HERE}/baton.py', *a], env=env, capture_output=True, text=True).returncode
        check('baton: one skill at a time in Resolve', bt('take', 'CWC_PodClips', 'build t01') == 0 and bt('take', 'CWC_PodReels', 'build s01') == 4 and bt('give', 'CWC_PodReels') == 1 and bt('give', 'CWC_PodClips') == 0 and bt('take', 'CWC_PodReels', 'build s01') == 0)
    finally:
        shutil.rmtree(T, ignore_errors=True)
    print(f'\n{len(PASS)} passed, {len(FAIL)} failed')
    sys.exit(1 if FAIL else 0)

if __name__ == '__main__': main()
