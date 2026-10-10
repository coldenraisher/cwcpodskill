"""related.py plan|due|mark|status <RUN>      the RELATED VIDEO of every YouTube Short (Studio's "Related video" field)
Colden 2026-10-03: '"related video" should be the full livestream or strategically relinked to the longer clip once that
comes out on the channel. The job of this skill is to develop that strategy and implement it.'
THE STRATEGY (deterministic, from the locked cut):
  - a Short points at the long-form clip ON ITS OWN CHANNEL that shares the most footage with it (>= rules.json
    same_topic_overlap_sec on the locked cut): the viewer who finished the Short gets the longer version of the same
    conversation - but only once that clip is PUBLIC (a link never points at a scheduled / private video, the end-screen
    ruling of 2026-09-15 "Do not link to unpublished videos ever")
  - until then, and for a Short no clip on its channel shares, it points at the full livestream on that channel (the
    public "Ep. NN" upload WITHOUT the phone emoji - CWC_PodClips ruling 38; read from its delivery.json full_episode)
  - when the clip goes public, every Short of that channel already up is RE-LINKED to it (the clip's go-live event)
  - NO FULL EPISODE (Colden and Todd), Colden 2026-10-08 "option 1": until its clip is public a Short links the related
    topic video - its clip's own "Watch next" (CWC_PodClips delivery `related`), else publish/related_topics.json
The Data API has no field for it: Claude sets it in Studio (Chrome) and records it here.
  plan   <RUN>   -> publish/related.json: per Short the clip it maps to (with the measured overlap) and the full episode
  due    <RUN> [--alert [--hours H]]   every uploaded Short whose recorded link differs from what it should be NOW -> SET
                 lines; exit 3 while any is open, 0 when every uploaded Short links where it should. --alert: the job is
                 queued for the conducting session (~/.config/cwc/podrun_todo.jsonl); with --telegram (not the daemon) ONE
                 Telegram line per Short whose slot is within H hours (default 12) and still not set
  mark   <RUN> <item id> <videoId> "<what you saw in Studio>"
  block  <RUN> <brand> "<what Studio did>"     the picker cannot be used on that channel: its Shorts are listed, not alerted
  status <RUN>
2026-10-04: STUDIO KEEPS ITS OWN CHANNEL (avatar > Switch account), separate from youtube.com/channel_switcher. On the
wrong one the "Choose specific video" picker lists nothing (the "TCL picker loads nothing" of 10/3) and another channel's
edit page says "Oops, something went wrong". Switch Studio to the Short's channel first; `block` is for a real Studio
refusal only."""
import os, sys, json, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

def approved(R):
    r = C.run(R); P = C.load(f'{R}/plan.json') or C.fail('no plan.json')
    if (r.get('plan_approval') or {}).get('sha') != P['sha']: C.fail('the plan is not approved')
    return r, P

def build(R):
    import plan as PL
    r, P = approved(R); thr = C.rules()['same_topic_overlap_sec']
    cs, rs = PL.spans(r['clips_work']), PL.spans(r['reels_work'])
    full = (C.clips_delivery(r) or {}).get('full_episode') or {}
    for b, vid in ((r.get('full_episode') or {}).get('ids') or {}).items():      # the live Colden named (intake --full-episode, 2026-10-09)
        if not (full.get(b) or {}).get('id'): full = dict(full, **{b: {'id': vid, 'title': 'full episode (Colden: ' + r['full_episode']['words'][:60] + ')'}})
    clips = {(i['ref'], i['brand']): i for i in P['items'] if i['kind'] == 'yt_clip'}
    out = {'at': C.now(), 'rule': 'same-channel clip with the most shared footage once PUBLIC, else the full livestream on that channel',
           'full_episode': {b: {'id': (full.get(b) or {}).get('id'), 'title': (full.get(b) or {}).get('title')} for b in ('cwc', 'tcl')}, 'shorts': {}}
    topics = C.load(f'{R}/publish/related_topics.json') or {}         # Colden's ruling for a show with no full episode (below)
    rel_of = {x.get('theme'): x.get('related') for x in (C.clips_delivery(r) or {}).get('clips', []) if x.get('related')}
    for it in [i for i in P['items'] if i['kind'] == 'yt_short']:
        best = max(((PL.overlap(cs.get(c, []), rs.get(it['ref'], [])), c) for (c, b) in clips if b == it['brand']), default=(0, None))
        clip = clips[(best[1], it['brand'])] if best[1] and best[0] >= thr else None
        out['shorts'][it['id']] = {'brand': it['brand'], 'title': it['title'], 'publish_at': it['publish_at'],
                                    'clip_item': clip['id'] if clip else None, 'clip_title': clip['title'] if clip else None,
                                    'clip_public_at': clip['publish_at'] if clip else None, 'shared_seconds': round(best[0], 1) if clip else 0}
        if not out['full_episode'][it['brand']]['id']:
            # NO FULL EPISODE (Colden and Todd: "No full episode link. Find a related topic video and link to that in the
            # description instead"; 2026-10-08 for the Shorts' Related video: "option 1") - until its clip is public a
            # Short links the related topic video: its clip's own "Watch next" (CWC_PodClips delivery `related`), else
            # the one picked for it in publish/related_topics.json {item id or ref: {id, title, why}}
            t = rel_of.get(clip['ref']) if clip else None
            t = {'id': t['video_id'], 'title': t.get('title'), 'why': f'the "Watch next" of clip {clip["ref"]}'} if t else (topics.get(it['id']) or topics.get(it['ref']))
            if not (t or {}).get('id'): C.ask(f'{it["id"]} ({it["title"][:50]}): no full episode on {it["brand"]} and no related topic video - add it to publish/related_topics.json')
            out['shorts'][it['id']]['topic'] = {'id': t['id'], 'title': t.get('title'), 'why': t.get('why')}
    C.save(f'{R}/publish/related.json', out); return out

def target(R, rel, sid, log, now):
    s = rel['shorts'][sid]; full = rel['full_episode'][s['brand']]
    if s['clip_item'] and dt.datetime.fromisoformat(s['clip_public_at']) <= now and (log.get(s['clip_item']) or {}).get('video_id'):
        return log[s['clip_item']]['video_id'], f'clip "{s["clip_title"][:60]}" ({s["shared_seconds"]} s shared)'
    until = f' (until the clip goes public {s["clip_public_at"][5:16]})' if s['clip_item'] else ''
    if not full['id'] and s.get('topic'): return s['topic']['id'], f'related topic video "{(s["topic"].get("title") or "")[:50]}"' + until
    return full['id'], 'full livestream' + until

def due(R, alert=False, hours=12.0, telegram=False):
    r, P = approved(R); rel = C.load(f'{R}/publish/related.json') or build(R); log = C.load(f'{R}/publish_log.json', {}) or {}
    now = dt.datetime.now(C.ET); n = 0; blocked = rel.get('blocked') or {}
    for sid, s in rel['shorts'].items():
        e = log.get(sid) or {}
        if not e.get('video_id'): continue
        if s['brand'] in blocked: print(f'BLOCKED {sid} ({s["brand"]}: {blocked[s["brand"]]["why"][:80]}) - wants {target(R, rel, sid, log, now)[0]}'); continue
        vid, why = target(R, rel, sid, log, now)
        if (e.get('related') or {}).get('video_id') == vid: continue
        n += 1; url = f'https://studio.youtube.com/video/{e["video_id"]}/edit'
        print(f'SET {sid} {s["brand"]} short {e["video_id"]} -> related {vid} ({why}): {url}')
        if alert:
            import pin
            if pin.todo(R, 'related', sid, target=vid, url=url, brand=s['brand'], why=why, publish_at=s['publish_at']): C.event(R, f'RELATED QUEUED {sid} -> {vid}')
        if telegram and alert and dt.datetime.fromisoformat(s['publish_at']) <= now + dt.timedelta(hours=hours) and (e.get('related_alerted') or {}).get('target') != vid:
            pin.alert(R, f'RELATED VIDEO not set on {sid} ({s["brand"]}, live {s["publish_at"][5:16]} ET): Studio -> {url} -> Related video = {vid} ({why}); then related.py mark {sid} {vid} "<saw>"')
            log = C.load(f'{R}/publish_log.json', {}) or {}; log.setdefault(sid, {})['related_alerted'] = {'target': vid, 'at': C.now()}; C.save(f'{R}/publish_log.json', log)
    if not n: print('every uploaded Short links where it should')
    sys.exit(3 if n else 0)

def mark(R, sid, vid, saw):
    r, P = approved(R); log = C.load(f'{R}/publish_log.json', {}) or {}
    if not (log.get(sid) or {}).get('video_id'): C.fail(f'{sid} is not uploaded')
    if len(saw.strip()) < 15: C.fail('say what you saw in Studio (>= 15 characters)')
    log[sid]['related'] = {'video_id': vid, 'at': C.now(), 'saw': saw, 'history': ((log[sid].get('related') or {}).get('history') or []) + ([log[sid]['related']['video_id']] if log[sid].get('related') else [])}
    C.save(f'{R}/publish_log.json', log); C.event(R, f'RELATED {sid} -> {vid}'); print(f'{sid}: related video {vid} recorded')

def status(R):
    r, P = approved(R); rel = C.load(f'{R}/publish/related.json') or build(R); log = C.load(f'{R}/publish_log.json', {}) or {}
    for sid, s in sorted(rel['shorts'].items(), key=lambda x: x[1]['publish_at']):
        cur = ((log.get(sid) or {}).get('related') or {}).get('video_id')
        base = f'topic {s["topic"]["id"]}' if s.get('topic') else 'full livestream'
        plan = f'{base} -> clip {s["clip_item"]} from {s["clip_public_at"][5:16]} ({s["shared_seconds"]} s shared)' if s['clip_item'] else f'-> {base} only'
        print(f'{s["publish_at"][5:16]} {sid:12} {plan:58} now: {cur or "not set"}')

def main():
    a = sys.argv[1:]
    if len(a) < 2: print(__doc__); sys.exit(1)
    cmd, R = a[0], a[1].rstrip('/')
    if cmd == 'plan': out = build(R); print(json.dumps(out['full_episode'])); status(R)
    elif cmd == 'due': due(R, '--alert' in a, float(a[a.index('--hours') + 1]) if '--hours' in a else 12.0, '--telegram' in a)
    elif cmd == 'mark': mark(R, a[2], a[3], a[4] if len(a) > 4 else '')
    elif cmd == 'block':
        rel = C.load(f'{R}/publish/related.json') or build(R); rel.setdefault('blocked', {})[a[2]] = {'why': a[3] if len(a) > 3 else '', 'at': C.now()}
        C.save(f'{R}/publish/related.json', rel); C.event(R, f'RELATED BLOCKED {a[2]}'); print(f'{a[2]}: related video blocked - listed, not alerted')
    elif cmd == 'status': status(R)
    else: print(__doc__); sys.exit(1)

if __name__ == '__main__': main()
