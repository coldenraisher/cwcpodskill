"""youtube.py upload|verify|checklist <RUN> [--id ITEM]   |   youtube.py flip-test <cwc|tcl>   |   youtube.py route [<state> --by "<words>"]
YouTube = the Data API only, every clip and Short (Colden 2026-10-03: "Skill uploads to YouTube and adds in all the
metadata. I flip from private to scheduled based on the dashboard. make sure monetization is always turned on." /
"Everything gets uploaded to YouTube through the current API. I will just do the manual switch from private to scheduled
until API clears.")
  flip-test THE ROUTE TEST, once (Colden 2026-10-03: "Not yet: test one"). YouTube locks uploads from an API project that
            has not passed its audit to private (edit-clips references/youtube_api.md, 2026-09-15); whether Colden can
            still switch such a video to Scheduled in Studio decides the whole route. Uploads ONE 8-second test card,
            private, to that channel and records it in data/youtube_route.json. Then, in Studio: can the visibility be
            changed? ->
  route     flip_works --by "<his words>"   uploads go up private, he flips each to Scheduled at the dashboard's time
            locked     --by "<his words>"   they cannot be switched: plan.py stops and asks (the route must be re-decided)
            publish_at_works --by ".."      the publish-test fired: publishAt is set at upload, nothing to flip
            audit_passed --by "<his words>" the audit cleared: the same, publishAt at upload
            (no state: prints the current answer)
  publish-test <cwc|tcl> <HH:MM>   ONE 8-second test card uploaded private WITH a publish time today (ET), subscribers
            not notified: does YouTube publish it by itself? (Colden 2026-10-03: "good lets run that test")
  publish-check                    reads it back after that time: public = it fired -> route publish_at_works
  upload    every approved YouTube item, in publish order: the video, title (A / the Short's title), description (the
            full-episode link filled in from the public "Ep. NN" live without the phone emoji), tags, category, made for
            kids No, altered content No; then thumbnail (A / the cover), captions, playlists - each recorded as it lands,
            so a re-run finishes what is missing and never uploads a video twice. A Short whose cover the API refuses is
            recorded and put on the Studio checklist (custom Shorts covers by API are unproven on his channels).
            Stops cleanly when the day's API quota cannot fit the next upload: run it again after midnight Pacific
            (the plan's upload_day says which day each one goes up).
  verify    reads every uploaded video back: private (flip due at ...), scheduled at the planned time, scheduled at
            another time, public -> publish/youtube_status.json (the dashboard shows it)
  checklist the Studio-only work per video -> publish/studio_checklist.md: MONETIZATION ON + the ad-suitability
            questions (the API cannot set or read monetization on a creator channel), Test & Compare with the approved
            A/B/C, the end screen, the pinned comment ~1 min after it goes live
GATES: the approved plan (sha + rules); the right channel on every call (ytapi); the shared quota; nothing uploaded twice
(publish_log.json is written after each video and after each extra); a slot too close to upload = rebuild the plan."""
import os, sys, json, subprocess, tempfile, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

STATES = ('flip_works', 'locked', 'publish_at_works', 'audit_passed')
ROUTE = f'{C.DATA}/youtube_route.json'

def approved(R):
    r = C.run(R); P = C.load(f'{R}/plan.json') or C.fail('no plan.json')
    if (r.get('plan_approval') or {}).get('sha') != P['sha']: C.fail('the plan is not approved - tg_plan.py send')
    if P.get('rules') != C.RULES: C.fail(f'the plan was built under rules {P.get("rules")}, the skill is on {C.RULES} - rebuild it')
    return r, P

def yt_items(P, only=None): return [i for i in P['items'] if i['kind'] in ('yt_clip', 'yt_short') and (not only or i['id'] == only)]

def fill_episode_link(r, item, videos):
    import ytapi as Y
    d = item.get('description') or ''
    if '{FULL_EPISODE_URL}' not in d: return d
    fe = ((r.get('full_episode') or {}).get('ids') or {}).get(item['brand'])      # the live Colden named (title without "Ep. NN")
    url, why = (f'https://www.youtube.com/watch?v={fe}', None) if fe else Y.full_episode_url(item['brand'], r['ep_no'], videos)
    if not url: C.ask(f'{item["id"]}: the full-episode link cannot be filled - {why}. Is the live public? (or give the link)')
    return d.replace('{FULL_EPISODE_URL}', url)

def units(it, pkg=None):
    q = C.rules()['quota_cost']; k = (pkg or {}).get(it['id']) or {}
    n = q['videos.insert'] + q['thumbnails.set'] + len(it.get('playlists') or []) * q['playlistItems.insert'] + (q['captions.insert'] if it['files'].get('captions') else 0)
    return n + q['videos.list'] + q['videos.update'] + len(set(k.get('playlists') or []) - set(it.get('playlists') or [])) * q['playlistItems.insert'] + (q['captions.insert'] if k.get('captions') else 0)   # shorts_pkg.apply: paid promotion No, tags, playlists, subtitles

def extras(Y, R, it, log):
    """thumbnail, captions, playlists of an uploaded video: each one once, recorded as it lands"""
    e = log[it['id']]; vid = e['video_id']; steps = []
    if it['files'].get('thumb'): steps.append(('thumbnail', lambda: Y.set_thumbnail(it['brand'], vid, it['files']['thumb'])))
    if it['files'].get('captions'): steps.append(('captions', lambda: Y.add_captions(it['brand'], vid, it['files']['captions'])))
    for pl in it.get('playlists') or []: steps.append((f'playlist {pl}', lambda pl=pl: Y.add_to_playlist(it['brand'], vid, pl)))
    for name, fn in steps:
        if name in e['done']: continue
        try: fn()
        except SystemExit: raise                                     # quota / file missing: already said why; a re-run continues here
        except Exception as x:
            if name == 'thumbnail' and it['kind'] == 'yt_short':     # unproven on his channels: never blocks the run, lands on the Studio checklist
                e.setdefault('problems', {})[name] = f'{type(x).__name__}: {str(x)[:200]}'; C.save(f'{R}/publish_log.json', log)
                print(f'{it["id"]}: YouTube refused the Short cover through the API - set it in Studio (checklist)'); continue
            C.fail(f'{it["id"]}: {name} failed ({type(x).__name__}: {str(x)[:200]}) - the video is up ({vid}); fix the cause and run upload again, it continues here')
        e['done'].append(name); (e.get('problems') or {}).pop(name, None); C.save(f'{R}/publish_log.json', log)
    e['complete'] = True; C.save(f'{R}/publish_log.json', log)

def flip_test(brand):
    import ytapi as Y
    if brand not in ('cwc', 'tcl'): C.fail('flip-test <cwc|tcl>')
    cur = C.youtube_route()
    if cur.get('state') == 'test_uploaded': C.fail(f'a test video is already up ({cur["test"]["url"]}) - check it in Studio, then: youtube.py route flip_works|locked --by "<what Colden said / saw>"')
    f = os.path.join(tempfile.mkdtemp(prefix='cwc_fliptest_'), 'API upload test.mp4')
    res = subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'testsrc2=size=1280x720:rate=30', '-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo',
                          '-t', '8', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-shortest', f], capture_output=True, text=True)
    if res.returncode or not os.path.exists(f): C.fail(f'ffmpeg could not make the test clip: {res.stderr[-200:]}')
    item = {'id': 'flip-test', 'title': 'API upload test - safe to delete', 'description': 'A private 8-second test card uploaded by CWC_PodRun to learn whether a video uploaded through the API can be switched to Scheduled in Studio. Safe to delete.',
            'tags': [], 'category': C.brands()[brand]['youtube']['category_id'], 'files': {'video': f}}
    vid = Y.insert(brand, item, 'flip', notify=False); v = Y.video_status(brand, vid) or {}
    st = v.get('status') or {}
    C.save(ROUTE, {'state': 'test_uploaded', 'test': {'brand': brand, 'video_id': vid, 'url': f'https://studio.youtube.com/video/{vid}/edit', 'at': C.now(),
                                                      'privacy': st.get('privacyStatus'), 'upload_status': st.get('uploadStatus')}})
    print(f'test video up on {C.brands()[brand]["label"]}: {vid} (privacy {st.get("privacyStatus")}, {st.get("uploadStatus")})\n'
          f'Studio: https://studio.youtube.com/video/{vid}/edit -> Visibility: can it be changed to Scheduled, or does it say locked?\n'
          f'then: youtube.py route flip_works|locked --by "<what Colden said / saw>"   (the test video can be deleted afterwards)')

def test_clip(name):
    f = os.path.join(tempfile.mkdtemp(prefix='cwc_yttest_'), name)
    res = subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'testsrc2=size=1280x720:rate=30', '-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo',
                          '-t', '8', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-shortest', f], capture_output=True, text=True)
    if res.returncode or not os.path.exists(f): C.fail(f'ffmpeg could not make the test clip: {res.stderr[-200:]}')
    return f

def publish_test(brand, hhmm):
    import ytapi as Y
    if brand not in ('cwc', 'tcl'): C.fail('publish-test <cwc|tcl> <HH:MM>')
    h, m = (int(x) for x in hhmm.split(':')); when = dt.datetime.now(C.ET).replace(hour=h, minute=m, second=0, microsecond=0)
    if when < dt.datetime.now(C.ET) + dt.timedelta(minutes=4): C.fail(f'{hhmm} ET is less than 4 minutes away - the upload has to finish processing first; give a later time')
    item = {'id': 'publish-test', 'title': 'API schedule test - safe to delete', 'description': 'A private 8-second test card uploaded by CWC_PodRun with a publish time, to learn whether YouTube publishes it by itself. Safe to delete.',
            'tags': [], 'category': C.brands()[brand]['youtube']['category_id'], 'publish_at': when.isoformat(timespec='seconds'), 'files': {'video': test_clip('API schedule test.mp4')}}
    vid = Y.insert(brand, item, 'publishAt', notify=False)
    cur = C.youtube_route(); cur['publish_test'] = {'brand': brand, 'video_id': vid, 'publish_at': item['publish_at'], 'uploaded_at': C.now(), 'url': f'https://studio.youtube.com/video/{vid}/edit'}
    C.save(ROUTE, cur); print(f'test video {vid} on {C.brands()[brand]["label"]}: private, publishes {item["publish_at"][11:16]} ET -> youtube.py publish-check after that')

def publish_check():
    import ytapi as Y
    cur = C.youtube_route(); t = cur.get('publish_test') or C.fail('no publish test on file - youtube.py publish-test <cwc|tcl> <HH:MM>')
    v = Y.video_status(t['brand'], t['video_id'])
    if not v: C.fail(f'the test video {t["video_id"]} is gone')
    st = v['status']; due = C.et(t['publish_at']); now = dt.datetime.now(C.ET)
    t.update(checked_at=C.now(), privacy=st.get('privacyStatus'), publish_at_youtube=st.get('publishAt')); C.save(ROUTE, cur)
    if st.get('privacyStatus') == 'public': print(f'FIRED: the test video is public ({C.now()}, due {t["publish_at"][11:16]}) -> youtube.py route publish_at_works --by "<what happened + his words>"')
    elif now < due: print(f'not due yet ({t["publish_at"][11:16]} ET): still {st.get("privacyStatus")}, publishAt {st.get("publishAt")}')
    else: print(f'NOT FIRED {round((now - due).total_seconds() / 60)} min after its time: still {st.get("privacyStatus")} (publishAt {st.get("publishAt")}) - check again in a few minutes; if it stays private the route stays flip_works')

def route(a):
    cur = C.youtube_route()
    if not a:
        print(json.dumps(cur, indent=1) if cur else 'not tested yet - youtube.py flip-test <cwc|tcl>'); return
    if a[0] not in STATES or '--by' not in a: C.fail(f'route <{"|".join(STATES)}> --by "<Colden\'s words, or what Studio showed>"')
    by = a[a.index('--by') + 1]
    if len(by.strip()) < 8: C.fail('--by needs his words (or what Studio showed)')
    C.save(ROUTE, dict(cur, state=a[0], by=by, at=C.now(), history=(cur.get('history') or []) + ([{k: cur[k] for k in ('state', 'by', 'at') if k in cur}] if cur.get('state') else [])))
    print(f'YouTube route: {a[0]} ({by})')

ALERT, missed = False, []

def main():
    global ALERT
    a = sys.argv[1:]
    if not a: print(__doc__); sys.exit(1)
    ALERT = '--alert' in a
    if ALERT and a[0] == 'upload':                                           # the daily run: every failure goes to Telegram at once
        a.remove('--alert'); sys.argv = [sys.argv[0]] + a
        try: return run(a)
        except SystemExit as x:
            if x.code not in (0, None) and not missed:
                import pin; pin.alert(a[1].rstrip('/'), f'YouTube upload run stopped (exit {x.code}) - see the session; nothing after it went up')
            raise
        except Exception as x:
            import pin; pin.alert(a[1].rstrip('/'), f'YouTube upload run crashed: {type(x).__name__}: {str(x)[:300]}'); raise
    return run(a)

def by_hand(brand, cache={}):
    """private, unscheduled videos on the channel - what Colden uploaded himself in Studio (one API read per brand per run)"""
    import ytapi as Y
    if brand not in cache: cache[brand] = [v for v in Y.uploads(brand, days_back=3) if v['privacy'] == 'private' and not v.get('publish_at')]
    return cache[brand]

def seconds(path):
    out = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path], capture_output=True, text=True).stdout.strip()
    return float(out) if out else None

def adopt(R, apply=False, only=None):
    """videos Colden uploaded HIMSELF in Studio take the place of the API upload. Colden 2026-10-08: "why don't i upload
    the videos to youtube so you dont hit an api limit and you add in the metadata?" - videos.insert is 1,600 of a
    Short's ~1,700 units, so a day's quota sets up ~15 videos instead of ~5.
      adopt <RUN>          match each approved YouTube item not yet up to ONE private, unscheduled video on its brand's
                           channel: same title as the master's file name (norm_title) and, once YouTube reports it,
                           the same length (+-2 s). Prints + saves publish/adopt_map.json. Ambiguous / missing = listed,
                           never guessed.
      adopt <RUN> --apply  the saved map, in go-live order: title / description / tags / category, private + publishAt,
                           then exactly what an API upload gets (thumbnail, captions, playlists, shorts_pkg). Stops when
                           the day's quota would run out; a re-run continues where it stopped."""
    import ytapi as Y
    r, P = approved(R); log = C.load(f'{R}/publish_log.json', {}) or {}; mp = f'{R}/publish/adopt_map.json'
    if not apply:
        taken = {e.get('video_id') for e in log.values() if e.get('video_id')}; out, miss = {}, []
        want = [i for i in yt_items(P, only) if not (log.get(i['id']) or {}).get('video_id')]
        for it in want:
            name = Y.norm_title(os.path.basename(it['files']['video'])); secs = seconds(it['files']['video'])
            c = [v for v in by_hand(it['brand']) if Y.norm_title(v['title']) == name and v['id'] not in taken]
            c = [v for v in c if not v.get('seconds') or secs is None or abs(v['seconds'] - secs) <= 2]
            if len(c) == 1:
                out[it['id']] = {'video_id': c[0]['id'], 'brand': it['brand'], 'file': os.path.basename(it['files']['video']), 'yt_title': c[0]['title'],
                                 'yt_seconds': c[0].get('seconds'), 'file_seconds': round(secs or 0, 2), 'publish_at': it['publish_at']}
                taken.add(c[0]['id'])
            else: miss.append(f'{it["id"]}: {len(c)} match(es) for "{os.path.basename(it["files"]["video"])}" on {it["brand"]}')
        C.save(mp, {'at': C.now(), 'sha': P['sha'], 'map': out})
        for k, v in sorted(out.items(), key=lambda kv: kv[1]['publish_at']):
            print(f'{v["publish_at"][5:16]}  {k:16} {v["video_id"]}  {v["yt_seconds"] or "?":>5}s/{v["file_seconds"]:>6}s  {v["file"][:64]}')
        if miss: print('NOT MATCHED:\n  ' + '\n  '.join(miss))
        print(f'{len(out)} matched -> {mp}' + ('' if miss else '; nothing missing')); return
    M = C.load(mp) or C.fail('no adopt_map.json - run youtube.py adopt <RUN> first (and show Colden the mapping)')
    if M['sha'] != P['sha']: C.fail(f'the map was made for plan {M["sha"]}, the approved plan is {P["sha"]} - run adopt again')
    C.post_ok(r, 'YouTube metadata on his uploads')
    import shorts_pkg
    pkg = C.load(f'{R}/publish/shorts_package.json') or shorts_pkg.build(R)
    items = {i['id']: i for i in yt_items(P, only)}; insert = C.rules()['quota_cost']['videos.insert']
    for iid, m in sorted(M['map'].items(), key=lambda kv: items[kv[0]]['publish_at'] if kv[0] in items else ''):
        it = items.get(iid)
        if not it or C.handled(it, log): continue
        if dt.datetime.fromisoformat(it['publish_at']) < dt.datetime.now(C.ET) + dt.timedelta(minutes=C.rules()['upload_lead_minutes']):
            print(f'{iid}: its slot {it["publish_at"][5:16]} is too close - reslot it first (plan.py reslot)'); continue
        e = log.get(iid)
        if not e:
            if Y.remaining() < units(it, pkg) - insert:
                print(f'API quota for today is used up - adopt --apply again after midnight Pacific ({iid} next)'); break
            st = Y.video_status(it['brand'], m['video_id']) or {}
            if (st.get('status') or {}).get('privacyStatus') != 'private' or (st.get('status') or {}).get('publishAt'):
                C.fail(f'{iid}: {m["video_id"]} is no longer a private, unscheduled video - did Colden change it in Studio? Ask before touching it')
            vids = (C.load(f'{R}/calendar/youtube.json') or {}).get('channels', {}).get(it['brand'])
            Y.update_snippet(it['brand'], m['video_id'], dict(it, description=fill_episode_link(r, it, vids)))
            Y.schedule(it['brand'], m['video_id'], it['publish_at'])
            e = log[iid] = {'route': 'youtube_api', 'video_id': m['video_id'], 'schedule': 'publishAt', 'publish_at': it['publish_at'], 'at': C.now(),
                            'done': ['video', 'metadata', 'schedule'], 'adopted': {'by': 'Colden in Studio', 'file': m['file']}}
            C.save(f'{R}/publish_log.json', log); C.event(R, f'YOUTUBE ADOPT {iid} {m["video_id"]} (his upload; publishAt {it["publish_at"][:16]})')
            print(f'{iid:18} {m["video_id"]}  scheduled {it["publish_at"][:16]} ET')
        extras(Y, R, it, log)
        shorts_pkg.apply(R, iid); log = C.load(f'{R}/publish_log.json', {}) or {}
    left = [i for i in yt_items(P) if not C.handled(i, C.load(f'{R}/publish_log.json', {}) or {})]
    print('every YouTube item is up with its metadata' if not left else f'{len(left)} left: {", ".join(i["id"] for i in left[:10])}')

def run(a):
    if a[0] == 'flip-test': return flip_test(a[1] if len(a) > 1 else '')
    if a[0] == 'route': return route(a[1:])
    if a[0] == 'publish-test': return publish_test(a[1] if len(a) > 1 else '', a[2] if len(a) > 2 else C.fail('publish-test <cwc|tcl> <HH:MM>'))
    if a[0] == 'publish-check': return publish_check()
    if len(a) < 2: print(__doc__); sys.exit(1)
    cmd, R = a[0], a[1].rstrip('/'); only = a[a.index('--id') + 1] if '--id' in a else None
    if cmd == 'adopt': return adopt(R, '--apply' in a, only)
    r, P = approved(R); log = C.load(f'{R}/publish_log.json', {}) or {}
    if cmd == 'upload':
        C.post_ok(r, 'YouTube upload')
        if C.colden_uploads(r): C.fail(f'Colden uploads every video himself this run (run.json colden_uploads: "{C.colden_uploads(r)[:70]}") - '
                                       f'youtube.py adopt "{R}" matches his Studio uploads (show him the map), adopt --apply adds the metadata + publish time; the API never inserts a video here')
        import ytapi as Y
        if P['youtube_schedule'] != {'audit_passed': 'publishAt', 'publish_at_works': 'publishAt', 'flip_works': 'flip'}.get(C.youtube_route().get('state')):
            C.fail(f'the plan was built for YouTube schedule "{P["youtube_schedule"]}", the route on file is now "{C.youtube_route().get("state")}" - rebuild the plan (a new approval)')
        up = lambda i: bool((log.get(i['id']) or {}).get('video_id'))
        import shorts_pkg
        pkg = C.load(f'{R}/publish/shorts_package.json') or shorts_pkg.build(R)
        for it in [i for i in yt_items(P, only) if not C.handled(i, log)]:
            if not up(it):
                if dt.datetime.fromisoformat(it['publish_at']) < dt.datetime.now(C.ET) + dt.timedelta(minutes=30):
                    if ALERT: missed.append(f'{it["id"]} "{it["title"][:50]}" ({it["publish_at"][:16]} ET) is too close or past to upload - NOT uploaded'); continue
                    C.fail(f'{it["id"]}: its slot is too close to upload - rebuild the plan')
                import plan as PL                                      # one quota pool: another approved run's uploads that go live
                ahead = sum(n for oid, n, at in PL.other_runs_owed(R)[1]          # SOONER keep their room (2026-10-07, C&T 10-6 + Ep 24)
                            if dt.datetime.fromisoformat(at) < dt.datetime.fromisoformat(it['publish_at']))
                if ahead and Y.remaining() - units(it, pkg) < ahead:
                    print(f'{it["id"]}: deferred - {ahead} units stay free for another run\'s uploads that go live sooner'); continue
                if Y.remaining() < units(it, pkg):
                    left = [i['id'] for i in yt_items(P, only) if not up(i)]
                    print(f'API quota for today is used up: {len(left)} upload(s) left ({", ".join(left[:8])}) - run youtube.py upload again after midnight Pacific'); break
                vids = (C.load(f'{R}/calendar/youtube.json') or {}).get('channels', {}).get(it['brand'])
                item = dict(it, description=fill_episode_link(r, it, vids))
                dup = [v['id'] for v in by_hand(it['brand']) if Y.norm_title(v['title']) == Y.norm_title(os.path.basename(it['files']['video']))]
                if dup: C.fail(f'{it["id"]}: "{os.path.basename(it["files"]["video"])}" is already on the channel as a private upload ({", ".join(dup)}) - Colden uploaded it himself: youtube.py adopt "{R}", never a second copy')
                vid = Y.insert(it['brand'], item, P['youtube_schedule'])
                log[it['id']] = {**(log.get(it['id']) or {}), 'route': 'youtube_api', 'video_id': vid, 'schedule': P['youtube_schedule'], 'publish_at': it['publish_at'], 'at': C.now(), 'done': ['video']}
                C.save(f'{R}/publish_log.json', log)                  # recorded before the extras: a crash never re-uploads
                C.event(R, f'YOUTUBE UPLOAD {it["id"]} {vid} ({P["youtube_schedule"]})')
                print(f'{it["id"]:18} {vid}  ' + (f'PRIVATE - flip to Scheduled {it["weekday"]} {it["publish_at"][:10]} {it["publish_at"][11:16]} ET' if P['youtube_schedule'] == 'flip' else f'scheduled {it["publish_at"][:16]} ET'))
            extras(Y, R, it, log)
            shorts_pkg.apply(R, it['id']); log = C.load(f'{R}/publish_log.json', {}) or {}     # the package Colden asked for 2026-10-03 (paid promotion No, ~500 tags, playlists, clean subtitles)
        else:
            left = [i['id'] for i in yt_items(P) if not C.handled(i, log)]
            print('every YouTube item is uploaded with its thumbnail, captions and playlists' if not left else f'{len(left)} left: {", ".join(left[:8])}')
        if ALERT:                                                            # anything that can no longer be up in time for its slot = an error now
            log = C.load(f'{R}/publish_log.json', {}) or {}; now = dt.datetime.now(dt.timezone.utc)
            reset = (now - dt.timedelta(hours=7)).replace(hour=0, minute=0, second=0, microsecond=0) + dt.timedelta(days=1, hours=7)    # next midnight Pacific (PDT)
            late = [i['id'] for i in yt_items(P, only) if not C.handled(i, log) and dt.datetime.fromisoformat(i['publish_at']) < reset + dt.timedelta(minutes=C.rules()['upload_lead_minutes'])
                    and not any(m.startswith(i['id'] + ' ') for m in missed)]
            if late: missed.append(f'{len(late)} upload(s) cannot be complete before their slot with today\'s quota: {", ".join(late)} - an error above, or quota')
            if missed:
                import pin; [pin.alert(R, m) for m in missed]; sys.exit(1)
    elif cmd == 'verify':
        import ytapi as Y
        out = {}
        for it in yt_items(P, only):
            e = log.get(it['id'])
            if not e: out[it['id']] = {'state': 'not uploaded'}; continue
            v = Y.video_status(it['brand'], e['video_id'])
            if not v: out[it['id']] = {'state': 'missing on YouTube', 'video_id': e['video_id']}; continue
            st = v['status']; pa = st.get('publishAt')
            if st.get('privacyStatus') == 'public': state = 'public'
            elif pa:
                diff = round((dt.datetime.fromisoformat(pa.replace('Z', '+00:00')) - dt.datetime.fromisoformat(it['publish_at'])).total_seconds() / 60)
                state = 'scheduled' if abs(diff) <= 5 else f'scheduled {diff:+d} min off the plan'
            else: state = 'private - flip due'
            out[it['id']] = {'state': state, 'video_id': e['video_id'], 'publish_at_youtube': pa, 'at': C.now(), 'extras_open': not e.get('complete'), 'problems': e.get('problems') or {}}
            print(f'{it["id"]:18} {state}' + ('  (extras not finished - youtube.py upload again)' if not e.get('complete') else ''))
        os.makedirs(f'{R}/publish', exist_ok=True); C.save(f'{R}/publish/youtube_status.json', out)
    elif cmd == 'checklist':
        L = [f'# Studio checklist - {r["show_name"]} {r["ep_key"]}', '', 'What the API cannot do. Claude in Chrome can work through it; tick as you go.', '']
        for it in yt_items(P):
            e = log.get(it['id']) or {}; v = e.get('video_id'); ab = it.get('ab') or {}; t = ab.get('titles') or {}
            L += [f'## {it["weekday"]} {it["publish_at"][:10]} {it["publish_at"][11:16]} ET - {C.brands()[it["brand"]]["label"]} - {"Clip" if it["kind"] == "yt_clip" else "Short"} - {it["title"]}',
                  f'video: {"https://studio.youtube.com/video/" + v + "/edit" if v else "(not uploaded yet)"}']
            if P['youtube_schedule'] == 'flip': L.append(f'- [ ] Visibility: Private -> Schedule {it["weekday"]} {it["publish_at"][:10]} {it["publish_at"][11:16]} ET')
            L += ['- [ ] Monetization: ON (Monetization tab) + the ad-suitability questions answered']
            if (e.get('problems') or {}).get('thumbnail'): L.append(f'- [ ] Cover: the API refused it - set {os.path.basename(it["files"]["thumb"])} in Studio by hand')
            if it['kind'] == 'yt_clip':
                L += [f'- [ ] Test & Compare: A "{t.get("A")}" / B "{t.get("B")}" / C "{t.get("C")}" with thumbnails A / B / C from Final/Clips/{"CWC" if it["brand"] == "cwc" else "TCL"}/Thumbnails',
                      '- [ ] End screen: import from the last long-form; slot 1 = the most relevant PUBLIC video, slot 2 = the full episode (never a scheduled / private one)',
                      f'- [ ] Pinned comment ~1 min after it goes live: "{it.get("pinned_comment") or ""}"']
            L.append('')
        os.makedirs(f'{R}/publish', exist_ok=True); open(f'{R}/publish/studio_checklist.md', 'w', encoding='utf-8').write('\n'.join(L) + '\n'); print(f'{R}/publish/studio_checklist.md')
    else: print(__doc__); sys.exit(1)

if __name__ == '__main__': main()
