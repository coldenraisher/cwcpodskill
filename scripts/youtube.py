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
            audit_passed --by "<his words>" the audit cleared: publishAt is set at upload, nothing to flip
            (no state: prints the current answer)
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

STATES = ('flip_works', 'locked', 'audit_passed')
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
    url, why = Y.full_episode_url(item['brand'], r['ep_no'], videos)
    if not url: C.ask(f'{item["id"]}: the full-episode link cannot be filled - {why}. Is the live public? (or give the link)')
    return d.replace('{FULL_EPISODE_URL}', url)

def units(it):
    q = C.rules()['quota_cost']
    return q['videos.insert'] + q['thumbnails.set'] + len(it.get('playlists') or []) * q['playlistItems.insert'] + (q['captions.insert'] if it['files'].get('captions') else 0)

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
    vid = Y.insert(brand, item, 'flip'); v = Y.video_status(brand, vid) or {}
    st = v.get('status') or {}
    C.save(ROUTE, {'state': 'test_uploaded', 'test': {'brand': brand, 'video_id': vid, 'url': f'https://studio.youtube.com/video/{vid}/edit', 'at': C.now(),
                                                      'privacy': st.get('privacyStatus'), 'upload_status': st.get('uploadStatus')}})
    print(f'test video up on {C.brands()[brand]["label"]}: {vid} (privacy {st.get("privacyStatus")}, {st.get("uploadStatus")})\n'
          f'Studio: https://studio.youtube.com/video/{vid}/edit -> Visibility: can it be changed to Scheduled, or does it say locked?\n'
          f'then: youtube.py route flip_works|locked --by "<what Colden said / saw>"   (the test video can be deleted afterwards)')

def route(a):
    cur = C.youtube_route()
    if not a:
        print(json.dumps(cur, indent=1) if cur else 'not tested yet - youtube.py flip-test <cwc|tcl>'); return
    if a[0] not in STATES or '--by' not in a: C.fail(f'route <{"|".join(STATES)}> --by "<Colden\'s words, or what Studio showed>"')
    by = a[a.index('--by') + 1]
    if len(by.strip()) < 8: C.fail('--by needs his words (or what Studio showed)')
    C.save(ROUTE, dict(cur, state=a[0], by=by, at=C.now(), history=(cur.get('history') or []) + ([{k: cur[k] for k in ('state', 'by', 'at') if k in cur}] if cur.get('state') else [])))
    print(f'YouTube route: {a[0]} ({by})')

def main():
    a = sys.argv[1:]
    if not a: print(__doc__); sys.exit(1)
    if a[0] == 'flip-test': return flip_test(a[1] if len(a) > 1 else '')
    if a[0] == 'route': return route(a[1:])
    if len(a) < 2: print(__doc__); sys.exit(1)
    cmd, R = a[0], a[1].rstrip('/'); only = a[a.index('--id') + 1] if '--id' in a else None
    r, P = approved(R); log = C.load(f'{R}/publish_log.json', {}) or {}
    if cmd == 'upload':
        import ytapi as Y
        if P['youtube_schedule'] != {'audit_passed': 'publishAt', 'flip_works': 'flip'}.get(C.youtube_route().get('state')):
            C.fail(f'the plan was built for YouTube schedule "{P["youtube_schedule"]}", the route on file is now "{C.youtube_route().get("state")}" - rebuild the plan (a new approval)')
        for it in [i for i in yt_items(P, only) if not C.handled(i, log)]:
            if it['id'] not in log:
                if dt.datetime.fromisoformat(it['publish_at']) < dt.datetime.now(C.ET) + dt.timedelta(minutes=30): C.fail(f'{it["id"]}: its slot is too close to upload - rebuild the plan')
                if Y.remaining() < units(it):
                    left = [i['id'] for i in yt_items(P, only) if i['id'] not in log]
                    print(f'API quota for today is used up: {len(left)} upload(s) left ({", ".join(left[:8])}) - run youtube.py upload again after midnight Pacific'); break
                vids = (C.load(f'{R}/calendar/youtube.json') or {}).get('channels', {}).get(it['brand'])
                item = dict(it, description=fill_episode_link(r, it, vids))
                vid = Y.insert(it['brand'], item, P['youtube_schedule'])
                log[it['id']] = {'route': 'youtube_api', 'video_id': vid, 'schedule': P['youtube_schedule'], 'publish_at': it['publish_at'], 'at': C.now(), 'done': ['video']}
                C.save(f'{R}/publish_log.json', log)                  # recorded before the extras: a crash never re-uploads
                C.event(R, f'YOUTUBE UPLOAD {it["id"]} {vid} ({P["youtube_schedule"]})')
                print(f'{it["id"]:18} {vid}  ' + (f'PRIVATE - flip to Scheduled {it["weekday"]} {it["publish_at"][:10]} {it["publish_at"][11:16]} ET' if P['youtube_schedule'] == 'flip' else f'scheduled {it["publish_at"][:16]} ET'))
            extras(Y, R, it, log)
        else:
            left = [i['id'] for i in yt_items(P) if not C.handled(i, log)]
            print('every YouTube item is uploaded with its thumbnail, captions and playlists' if not left else f'{len(left)} left: {", ".join(left[:8])}')
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
                L += [f'- [ ] Test & Compare: A "{t.get("A")}" / B "{t.get("B")}" / C "{t.get("C")}" with thumbnails A / B / C from Final/Clips/Thumbnails',
                      '- [ ] End screen: import from the last long-form; slot 1 = the most relevant PUBLIC video, slot 2 = the full episode (never a scheduled / private one)',
                      f'- [ ] Pinned comment ~1 min after it goes live: "{it.get("pinned_comment") or ""}"']
            L.append('')
        os.makedirs(f'{R}/publish', exist_ok=True); open(f'{R}/publish/studio_checklist.md', 'w', encoding='utf-8').write('\n'.join(L) + '\n'); print(f'{R}/publish/studio_checklist.md')
    else: print(__doc__); sys.exit(1)

if __name__ == '__main__': main()
