"""youtube.py upload|verify|checklist <RUN> [--id ITEM]      YouTube = the Data API only, every clip and Short
Colden 2026-10-03: "Skill uploads to YouTube and adds in all the metadata. I flip from private to scheduled based on the
dashboard. make sure monetization is always turned on." / "Everything gets uploaded to YouTube through the current API. I
will just do the manual switch from private to scheduled until API clears."
  upload    every approved YouTube item not yet up, in publish order: the video, title (A / the Short's title),
            description (the full-episode link filled in from the public "Ep. NN" live without the phone emoji), tags,
            category, made for kids No, altered content No, thumbnail (A / the cover), captions, playlists.
            Before the audit (plan youtube_schedule 'flip') it stays PRIVATE with no publishAt - Colden flips it to
            Scheduled at the time on the dashboard; after it ('publishAt') YouTube schedules it itself.
            Stops cleanly when the day's API quota cannot fit the next upload: run it again after midnight Pacific
            (the plan's upload_day says which day each one goes up).
  verify    reads every uploaded video back: private (flip due at ...), scheduled at the planned time, scheduled at
            another time, public -> publish/youtube_status.json (the dashboard shows it)
  checklist the Studio-only work per video -> publish/studio_checklist.md: MONETIZATION ON + the ad-suitability
            questions (the API cannot set or read monetization on a creator channel), Test & Compare with the approved
            A/B/C, the end screen, the pinned comment ~1 min after it goes live
GATES: the approved plan (sha + rules); the right channel on every call (ytapi); the shared quota; nothing uploaded twice
(publish_log.json is written after each video, before the next); a slot too close to upload = rebuild the plan."""
import os, sys, json, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

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

def main():
    a = sys.argv[1:]
    if len(a) < 2: print(__doc__); sys.exit(1)
    cmd, R = a[0], a[1].rstrip('/'); only = a[a.index('--id') + 1] if '--id' in a else None
    r, P = approved(R); log = C.load(f'{R}/publish_log.json', {}) or {}
    if cmd == 'upload':
        import ytapi as Y
        todo = [i for i in yt_items(P, only) if i['id'] not in log]
        for it in todo:
            if dt.datetime.fromisoformat(it['publish_at']) < dt.datetime.now(C.ET) + dt.timedelta(minutes=30): C.fail(f'{it["id"]}: its slot is too close to upload - rebuild the plan')
            if Y.remaining() < units(it):
                left = [i['id'] for i in todo if i['id'] not in log]
                print(f'API quota for today is used up: {len(left)} upload(s) left ({", ".join(left[:8])}) - run youtube.py upload again after midnight Pacific'); break
            vids = (C.load(f'{R}/calendar/youtube.json') or {}).get('channels', {}).get(it['brand'])
            item = dict(it, description=fill_episode_link(r, it, vids))
            vid = Y.insert(it['brand'], item, P['youtube_schedule'])
            log[it['id']] = {'route': 'youtube_api', 'video_id': vid, 'schedule': P['youtube_schedule'], 'publish_at': it['publish_at'], 'at': C.now(), 'done': ['video']}
            C.save(f'{R}/publish_log.json', log)                      # recorded before the extras: a crash never re-uploads
            if it['files'].get('thumb'): Y.set_thumbnail(it['brand'], vid, it['files']['thumb']); log[it['id']]['done'].append('thumbnail')
            if it['files'].get('captions'): Y.add_captions(it['brand'], vid, it['files']['captions']); log[it['id']]['done'].append('captions')
            for pl in it.get('playlists') or []: Y.add_to_playlist(it['brand'], vid, pl); log[it['id']]['done'].append(f'playlist {pl}')
            C.save(f'{R}/publish_log.json', log); C.event(R, f'YOUTUBE UPLOAD {it["id"]} {vid} ({P["youtube_schedule"]})')
            print(f'{it["id"]:18} {vid}  ' + (f'PRIVATE - flip to Scheduled {it["weekday"]} {it["publish_at"][:10]} {it["publish_at"][11:16]} ET' if P['youtube_schedule'] == 'flip' else f'scheduled {it["publish_at"][:16]} ET'))
        else:
            print('every YouTube item is uploaded' if not [i for i in yt_items(P) if i['id'] not in log] else '')
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
            out[it['id']] = {'state': state, 'video_id': e['video_id'], 'publish_at_youtube': pa, 'at': C.now()}
            print(f'{it["id"]:18} {state}')
        os.makedirs(f'{R}/publish', exist_ok=True); C.save(f'{R}/publish/youtube_status.json', out)
    elif cmd == 'checklist':
        L = [f'# Studio checklist - {r["show_name"]} {r["ep_key"]}', '', 'What the API cannot do. Claude in Chrome can work through it; tick as you go.', '']
        for it in yt_items(P):
            v = (log.get(it['id']) or {}).get('video_id'); ab = it.get('ab') or {}; t = ab.get('titles') or {}
            L += [f'## {it["weekday"]} {it["publish_at"][:10]} {it["publish_at"][11:16]} ET - {C.brands()[it["brand"]]["label"]} - {"Clip" if it["kind"] == "yt_clip" else "Short"} - {it["title"]}',
                  f'video: {"https://studio.youtube.com/video/" + v + "/edit" if v else "(not uploaded yet)"}']
            if P['youtube_schedule'] == 'flip': L.append(f'- [ ] Visibility: Private -> Schedule {it["weekday"]} {it["publish_at"][:10]} {it["publish_at"][11:16]} ET')
            L += ['- [ ] Monetization: ON (Monetization tab) + the ad-suitability questions answered']
            if it['kind'] == 'yt_clip':
                L += [f'- [ ] Test & Compare: A "{t.get("A")}" / B "{t.get("B")}" / C "{t.get("C")}" with thumbnails A / B / C from Final/Clips/Thumbnails',
                      '- [ ] End screen: import from the last long-form; slot 1 = the most relevant PUBLIC video, slot 2 = the full episode (never a scheduled / private one)',
                      f'- [ ] Pinned comment ~1 min after it goes live: "{it.get("pinned_comment") or ""}"']
            L.append('')
        os.makedirs(f'{R}/publish', exist_ok=True); open(f'{R}/publish/studio_checklist.md', 'w', encoding='utf-8').write('\n'.join(L) + '\n'); print(f'{R}/publish/studio_checklist.md')
    else: print(__doc__); sys.exit(1)

if __name__ == '__main__': main()
