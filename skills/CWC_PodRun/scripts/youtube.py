"""youtube.py find|apply|upload|checklist <RUN> [--id ITEM] [--with-flags]      YouTube = the Data API only
Colden 2026-10-03: "YouTube will solely be driven by the API and uploaded directly"; "working through the audit now.
until it passes I will manually schedule. you will upload all metadata". (An unaudited API project's uploads are locked
private, so before the audit the VIDEO goes up through Studio and everything else goes up through the API.)
  find      route studio_manual: Colden uploaded + scheduled the planned videos in Studio from Final/YouTube Upload List.md
            (kit.py). Finds each on its channel - title = the file name Studio gave it, or the planned title - and checks
            its schedule against the plan -> publish/youtube_found.json. Not uploaded yet = listed, not an error.
  apply     every found video not yet done: title (A / the Short's title), description (the full-episode link filled in
            from the public "Ep. NN" live without the phone emoji), tags, category, thumbnail (A / the cover), captions,
            playlists [--with-flags: made for kids No, altered content No - keeps his privacy + schedule] -> publish_log.json
  upload    route youtube_api - ONLY when rules.json youtube_audit_passed is true (his word): upload as private with
            publishAt = the approved slot, then everything apply writes -> publish_log.json
  checklist Studio-only work per video -> publish/studio_checklist.md: Test & Compare with the approved A/B/C, the end
            screen (slot 1 = most relevant PUBLIC video, slot 2 = the full episode), the pinned comment ~1 min after it
            goes live, paid promotion / AI flags read back
GATES: the approved plan (sha); the right channel on every call (ytapi); the shared quota; a found video must be private /
scheduled (a public video is never matched); his Studio time wins over the plan (a mismatch > 10 min is logged + shown);
nothing written twice (publish_log.json)."""
import os, sys, json, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

def approved(R):
    r = C.run(R); P = C.load(f'{R}/plan.json') or C.fail('no plan.json')
    if (r.get('plan_approval') or {}).get('sha') != P['sha']: C.fail('the plan is not approved - tg_plan.py send')
    return r, P

def yt_items(P, route, only=None):
    return [i for i in P['items'] if i['kind'] in ('yt_clip', 'yt_short') and i['route'] == route and (not only or i['id'] == only)]

def fill_episode_link(r, item, videos):
    import ytapi as Y
    d = item.get('description') or ''
    if '{FULL_EPISODE_URL}' not in d: return d
    url, why = Y.full_episode_url(item['brand'], r['ep_no'], videos)
    if not url: C.ask(f'{item["id"]}: the full-episode link cannot be filled - {why}. Is the live public? (or give the link)')
    return d.replace('{FULL_EPISODE_URL}', url)

def write_all(r, item, vid, videos, flags, snippet=True):
    import ytapi as Y
    b = item['brand']; it = dict(item, description=fill_episode_link(r, item, videos))
    if snippet: Y.update_snippet(b, vid, it)          # an API upload already carried the snippet
    if it['files'].get('thumb'): Y.set_thumbnail(b, vid, it['files']['thumb'])
    if it['files'].get('captions'): Y.add_captions(b, vid, it['files']['captions'])
    for pl in it.get('playlists') or []: Y.add_to_playlist(b, vid, pl)
    if flags: Y.update_flags(b, vid)

def main():
    a = sys.argv[1:]
    if len(a) < 2: print(__doc__); sys.exit(1)
    cmd, R = a[0], a[1].rstrip('/'); only = a[a.index('--id') + 1] if '--id' in a else None; flags = '--with-flags' in a
    r, P = approved(R); log = C.load(f'{R}/publish_log.json', {}) or {}; found_p = f'{R}/publish/youtube_found.json'
    if cmd in ('find', 'apply', 'upload'): import ytapi as Y
    if cmd == 'find':
        found = C.load(found_p, {}) or {}; items = [i for i in yt_items(P, 'studio_manual', only) if i['id'] not in log]
        for b in sorted({i['brand'] for i in items}):
            vids = Y.uploads(b, days_back=14)
            for it in [i for i in items if i['brand'] == b]:
                names = {Y.norm_title(it['title']), Y.norm_title(os.path.basename(it['files']['video']))}
                hits = [v for v in vids if Y.norm_title(v['title']) in names and (v['privacy'] != 'public' or v.get('publish_at'))]
                if len(hits) != 1: print(f'{it["id"]:18} not found yet ({len(hits)} matches) - upload "{os.path.basename(it["files"]["video"])}" to {C.brands()[b]["label"]} and schedule it {it["weekday"]} {it["publish_at"][:16]} ET'); continue
                v = hits[0]; diff = None
                if v.get('publish_at'): diff = round((dt.datetime.fromisoformat(v['publish_at'].replace('Z', '+00:00')) - dt.datetime.fromisoformat(it['publish_at'])).total_seconds() / 60)
                found[it['id']] = {'video_id': v['id'], 'privacy': v['privacy'], 'studio_publish_at': v.get('publish_at'), 'diff_min': diff, 'at': C.now()}
                note = '' if diff is not None and abs(diff) <= 10 else (' NOT SCHEDULED in Studio' if diff is None else f' schedule differs from the plan by {diff} min (his Studio time stands)')
                print(f'{it["id"]:18} found {v["id"]} ({v["privacy"]}){note}')
        C.save(found_p, found)
    elif cmd == 'apply':
        found = C.load(found_p, {}) or {}; cache = {}
        for it in yt_items(P, 'studio_manual', only):
            if it['id'] in log or it['id'] not in found: continue
            f = found[it['id']]; vids = cache.setdefault(it['brand'], (C.load(f'{R}/calendar/youtube.json') or {}).get('channels', {}).get(it['brand']))
            write_all(r, it, f['video_id'], vids, flags)
            log[it['id']] = {'route': 'studio_manual', 'video_id': f['video_id'], 'studio_publish_at': f.get('studio_publish_at'), 'plan_publish_at': it['publish_at'], 'diff_min': f.get('diff_min'), 'flags': flags, 'at': C.now()}
            C.save(f'{R}/publish_log.json', log); C.event(R, f'YOUTUBE METADATA {it["id"]} {f["video_id"]}'); print(f'{it["id"]:18} metadata written on {f["video_id"]}')
        left = [i['id'] for i in yt_items(P, 'studio_manual') if i['id'] not in log]
        print(f'{len(left)} YouTube item(s) still waiting on a Studio upload: {", ".join(left)}' if left else 'every studio_manual video has its metadata')
    elif cmd == 'upload':
        if not C.rules()['youtube_audit_passed']: C.fail('youtube_audit_passed is false in rules.json - until Colden says the audit passed, the route is studio_manual (find / apply)')
        for it in yt_items(P, 'youtube_api', only):
            if it['id'] in log: continue
            if dt.datetime.fromisoformat(it['publish_at']) < dt.datetime.now(C.ET) + dt.timedelta(minutes=30): C.fail(f'{it["id"]}: its slot is too close - rebuild the plan')
            vids = (C.load(f'{R}/calendar/youtube.json') or {}).get('channels', {}).get(it['brand'])
            it = dict(it, description=fill_episode_link(r, it, vids))
            vid = Y.insert(it['brand'], it); write_all(r, it, vid, vids, False, snippet=False)
            log[it['id']] = {'route': 'youtube_api', 'video_id': vid, 'publish_at': it['publish_at'], 'at': C.now()}
            C.save(f'{R}/publish_log.json', log); C.event(R, f'YOUTUBE UPLOAD {it["id"]} {vid}'); print(f'{it["id"]:18} uploaded {vid}, scheduled {it["publish_at"][:16]} ET')
    elif cmd == 'checklist':
        L = [f'# Studio checklist - {r["show_name"]} {r["ep_key"]}', '', 'Studio-only work the API cannot do. Tick as you go.', '']
        for it in [i for i in P['items'] if i['kind'] == 'yt_clip']:
            v = (log.get(it['id']) or {}).get('video_id'); ab = it.get('ab') or {}
            L += [f'## {it["weekday"]} {it["publish_at"][:16]} - {C.brands()[it["brand"]]["label"]} - {it["title"]}', f'video: {"https://studio.youtube.com/video/" + v + "/edit" if v else "(not on YouTube yet)"}',
                  f'- [ ] Test & Compare: A "{(ab.get("titles") or {}).get("A")}" / B "{(ab.get("titles") or {}).get("B")}" / C "{(ab.get("titles") or {}).get("C")}" with thumbnails A/B/C from Final/Clips/Thumbnails',
                  '- [ ] End screen: import from the last long-form; slot 1 = the most relevant PUBLIC video, slot 2 = the full episode (never a scheduled / private video)',
                  f'- [ ] Pinned comment ~1 min after it goes live: "{it.get("pinned_comment") or ""}"', '- [ ] Paid promotion No, altered / AI content No - read back', '']
        os.makedirs(f'{R}/publish', exist_ok=True); open(f'{R}/publish/studio_checklist.md', 'w', encoding='utf-8').write('\n'.join(L) + '\n'); print(f'{R}/publish/studio_checklist.md')
    else: print(__doc__); sys.exit(1)

if __name__ == '__main__': main()
