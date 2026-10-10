"""pin.py due|mark|status|alert <RUN>      PINNED COMMENTS at go-live, monetization records, Telegram alerts
Colden 2026-10-03: "You will also need to manage pinned comments at the exact time of posting. make sure this thread stays
active and send a telegram message if there is an error with uploading or pinned comments ASAP" / monetization: "it needs to
be turned on and then clicked that no harmful or violative content is being shared (you can always agree to that)" -
"monetization step only applies to @coldenraisher channel" (The Creative Lens is not in the Partner Program).
  due    <RUN> [--alert-pins]   every uploaded YouTube item whose publish time has passed (>= 45 s) and has no comment yet: reads the
                 video back - public = the comment goes up through the API as the channel (commentThreads.insert;
                 clips: the package's pinned comment, Shorts: the reel's first comment, the same question Metricool posts
                 on IG / TikTok / FB), recorded in publish_log.json BEFORE anything else. The API cannot pin: every
                 comment that is up and not pinned yet is printed as a PIN line - Claude pins it ON YOUTUBE (Chrome, the
                 Short / watch page's comments, with youtube.com switched to that channel; Studio's comment menu has no
                 Pin - 2026-10-03), then `mark ... pinned`. Not public yet: WAIT (retry in a few minutes); still not public 15 min after its
                 time: ALERT. exit 0 nothing left to post now, 3 = WAIT lines, 1 = an error (already sent to Telegram).
                 --alert-pins (watch.py runs it so): every PIN goes to the TODO QUEUE ~/.config/cwc/podrun_todo.jsonl at once -
                 the conductor session keeps a Monitor on that file and pins with the Chrome MCP (Colden 2026-10-09: "daemon
                 should tell claude to pin with chrome MCP"). --telegram (NOT used by the daemon - Colden 2026-10-10: "This bot
                 was supposed to be for review only"): a pin still open PIN_GRACE_MIN after the comment goes to him ONCE.
  mark   <RUN> <item id> pinned|monetization|abtest|endscreen|cover "<what you saw>"     what was done by hand in Studio
         (cover = the thumbnail set in Studio after the API refused it: clears the problem, the item completes on the next pass)
         (abtest = Test & Compare "Title and thumbnail" with the plan's A/B/C pairs - Colden 2026-09-15 + 2026-10-06
         "Why are there no A/B tests"; endscreen = his master imported, targets re-pointed; both clips only)
  status <RUN>   every YouTube item: uploaded, comment, pinned, monetization
  arm    <RUN> "<job>"   records that the GO-LIVE WATCH runs (a recurring session cron, every <= 10 min: pin.py due +
                 related.py due + monetization). Colden 2026-10-09, after s06 went live with no pinned comment and no related
                 video: "why have these skills with rules if they keep getting missed". next.py blocks without it.
  alert  <RUN> "<text>"   one Telegram message to Colden - an EMERGENCY only (a post that will go out wrong or not at all;
                 Colden 2026-10-10: "If there is an emergency, send it in telegram. If it's just routine keep it quiet")
GATES: the approved plan; a comment is never posted twice (publish_log before the next call); a video that is not public
gets no comment; every error goes to Telegram at once."""
import os, sys, json, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

GRACE_S, LATE_MIN, PIN_GRACE_MIN = 45, 15, 15
TODO = f'{C.CFG}/podrun_todo.jsonl'          # one line per browser job for the live session: {"type": "pin"|"related", "run", "item", "url", ...}

def todo(R, kind, item, **more):
    """append ONE job line for the conductor session (its Monitor wakes on it) - never twice for the same job key"""
    key = f'{kind}|{os.path.relpath(R, C.RUNS)}|{item}|{more.get("target", "")}'
    if os.path.exists(TODO) and any(key == (json.loads(l) if l.strip() else {}).get('key') for l in open(TODO, encoding='utf-8') if l.strip()): return False
    os.makedirs(C.CFG, exist_ok=True)
    with open(TODO, 'a', encoding='utf-8') as f: f.write(json.dumps({'key': key, 'type': kind, 'run': R, 'item': item, 'at': C.now(), **more}, ensure_ascii=False) + '\n')
    return True

def approved(R):
    r = C.run(R); P = C.load(f'{R}/plan.json') or C.fail('no plan.json')
    if (r.get('plan_approval') or {}).get('sha') != P['sha']: C.fail('the plan is not approved')
    return r, P

def alert(R, text, emergency=False):
    """Colden 2026-10-10: "If there is an emergency, send it in telegram. If it's just routine keep it quiet." The bot is for
    review cards; an automatic line reaches him ONLY when emergency=True - a post that will go out wrong or not at all, a
    video that did not publish, the YouTube connection itself broken (watch.py emergencies() decides). Everything else is
    written to the run's events.log as QUIET and shown by next.py / watch.py status."""
    if not emergency:
        C.event(R, f'QUIET {text[:300]}'); print(f'NOTE (not sent - routine): {text}', file=sys.stderr); return
    r = C.load(f'{R}/run.json') or {}
    msg = f'🚨 {r.get("show_name", "")} {r.get("ep_key", "")}: {text}'[:3900]
    try:
        import tg; tg.say(msg); C.event(R, f'ALERT SENT {text[:200]}')
    except BaseException as x: C.event(R, f'ALERT NOT SENT ({type(x).__name__}) {text[:200]}'); print(f'TELEGRAM FAILED: {x}', file=sys.stderr)
    print(f'ALERT: {text}', file=sys.stderr)

def comment_text(r, it):
    if it['kind'] == 'yt_clip': return (it.get('pinned_comment') or '').strip()
    d = C.reels_delivery(r) or {}
    s = next((s for s in d.get('shorts', []) if s.get('id') == it['ref']), None) or {}
    return ((s.get('copy') or {}).get('first_comment') or '').strip()

def due(R, alert_pins=False, telegram=False):
    import ytapi as Y
    if Y.quota_exhausted(): print(f'YouTube API quota is used up until {Y.quota_exhausted()} - nothing read or posted this pass'); sys.exit(3)
    r, P = approved(R); log = C.load(f'{R}/publish_log.json', {}) or {}; now = dt.datetime.now(C.ET); waits, errors = [], []
    for it in [i for i in P['items'] if i['kind'] in ('yt_clip', 'yt_short')]:
        e = log.get(it['id']); at = dt.datetime.fromisoformat(it['publish_at'])
        if now < at + dt.timedelta(seconds=GRACE_S): continue
        if not e or not e.get('video_id'):
            if now > at + dt.timedelta(minutes=LATE_MIN) and not (e or {}).get('late_alerted'):
                errors.append((f'"{it["title"][:70]}" ({C.brands()[it["brand"]]["label"]}) was due {it["publish_at"][11:16]} ET {it["publish_at"][5:10]} and is NOT on YouTube', True))
                log.setdefault(it['id'], {}); log[it['id']]['late_alerted'] = C.now(); C.save(f'{R}/publish_log.json', log)
            continue
        if (e.get('comment') or {}).get('id'): continue
        text = comment_text(r, it)
        if not text: errors.append((f'{it["id"]}: no comment text in the plan / delivery', False)); continue
        try:
            v = Y.video_status(it['brand'], e['video_id'])
        except SystemExit: raise
        except Exception as x: errors.append((f'{it["id"]}: could not read the video back ({type(x).__name__}: {str(x)[:150]})', False)); continue
        st = (v or {}).get('status') or {}
        if st.get('privacyStatus') != 'public':
            if now > at + dt.timedelta(minutes=LATE_MIN) and not e.get('notpublic_alerted'):
                errors.append((f'"{it["title"][:70]}" ({C.brands()[it["brand"]]["label"]}) did NOT go public: still {st.get("privacyStatus")} {round((now - at).total_seconds() / 60)} min after {it["publish_at"][11:16]} ET - Studio: https://studio.youtube.com/video/{e["video_id"]}/edit', True))
                log = C.load(f'{R}/publish_log.json', {}) or {}; log[it['id']]['notpublic_alerted'] = C.now(); C.save(f'{R}/publish_log.json', log)
            else: waits.append(it['id']); print(f'WAIT {it["id"]}: {st.get("privacyStatus")} - publishes {it["publish_at"][11:16]} ET')
            continue
        try:
            cid = Y.add_comment(it['brand'], e['video_id'], text)
        except SystemExit: raise
        except Exception as x: errors.append((f'{it["id"]} https://youtu.be/{e["video_id"]}: the comment was refused ({type(x).__name__}: {str(x)[:200]}) - post + pin it by hand: "{text}"', False)); continue
        log = C.load(f'{R}/publish_log.json', {}) or {}
        log[it['id']]['comment'] = {'id': cid, 'at': C.now(), 'text': text, 'pinned': False}; C.save(f'{R}/publish_log.json', log)
        C.event(R, f'COMMENT {it["id"]} {cid}'); print(f'posted {it["id"]}: comment {cid}')
    log = C.load(f'{R}/publish_log.json', {}) or {}
    for it in [i for i in P['items'] if i['kind'] in ('yt_clip', 'yt_short')]:
        c = (log.get(it['id']) or {}).get('comment') or {}
        if c.get('id') and not c.get('pinned'):
            v = log[it['id']]['video_id']; url = f'https://www.youtube.com/shorts/{v}' if it['kind'] == 'yt_short' else f'https://www.youtube.com/watch?v={v}'
            print(f'PIN {it["id"]} {it["brand"]} video {v} comment {c["id"]}: {url} (channel switched to {it["brand"]}) | "{c["text"][:70]}"')
            if alert_pins:
                mon = ' + Monetization ON (Earn tab)' if it['brand'] == 'cwc' else ''
                if todo(R, 'pin', it['id'], url=url, brand=it['brand'], comment_id=c['id'], text=c['text'], monetization=it['brand'] == 'cwc'):
                    C.event(R, f'PIN QUEUED {it["id"]} -> {TODO}')
                if telegram and not c.get('pin_alerted') and C.hours_old_iso(c.get('at')) * 60 >= PIN_GRACE_MIN:        # the fallback line to Colden, only when asked for (--telegram): the bot is for review
                    alert(R, f'LIVE {it["id"]} ({C.brands()[it["brand"]]["label"]}): the comment is up {round(C.hours_old_iso(c.get("at")) * 60)} min and not pinned - PIN it as the channel: {url} | "{c["text"][:120]}"{mon}; then pin.py mark {it["id"]} pinned "<saw>"', emergency=True)
                    log = C.load(f'{R}/publish_log.json', {}) or {}; log[it['id']]['comment']['pin_alerted'] = C.now(); C.save(f'{R}/publish_log.json', log)
    for x, em in errors: alert(R, x, emergency=em)
    sys.exit(1 if any(em for _, em in errors) else 3 if waits or errors else 0)

def mark(R, iid, what, saw):
    r, P = approved(R); log = C.load(f'{R}/publish_log.json', {}) or {}
    if iid not in log or not log[iid].get('video_id'): C.fail(f'{iid} is not uploaded')
    if len(saw.strip()) < 15: C.fail('say what you saw in Studio (>= 15 characters)')
    if what == 'pinned':
        if not (log[iid].get('comment') or {}).get('id'): C.fail(f'{iid} has no comment yet - pin.py due')
        log[iid]['comment'].update(pinned=True, pinned_at=C.now(), saw=saw)
    elif what == 'monetization':
        it = next(i for i in P['items'] if i['id'] == iid)
        if it['brand'] != 'cwc': C.fail('monetization is only for @ColdenRaisher (Colden 2026-10-03) - The Creative Lens is not in the Partner Program')
        log[iid]['monetization'] = {'at': C.now(), 'saw': saw}
    elif what in ('abtest', 'endscreen'):
        it = next(i for i in P['items'] if i['id'] == iid)
        if it['kind'] != 'yt_clip': C.fail(f'{what} is for long-form clips only')
        log[iid][what] = {'at': C.now(), 'saw': saw}
    elif what == 'cover':                                               # the thumbnail set in Studio by hand after the API refused it
        e = log[iid]; e.setdefault('done', [])
        if 'thumbnail' not in e['done']: e['done'].append('thumbnail')
        (e.get('problems') or {}).pop('thumbnail', None); e['cover_by_hand'] = {'at': C.now(), 'saw': saw}
        if not e.get('problems'): e['complete'] = True
    else: C.fail('mark <RUN> <item id> pinned|monetization|abtest|endscreen|cover "<what you saw>"')
    C.save(f'{R}/publish_log.json', log); C.event(R, f'MARK {iid} {what}: {saw[:120]}'); print(f'{iid}: {what} recorded')

def status(R):
    r, P = approved(R); log = C.load(f'{R}/publish_log.json', {}) or {}
    for it in [i for i in P['items'] if i['kind'] in ('yt_clip', 'yt_short')]:
        e = log.get(it['id']) or {}; c = e.get('comment') or {}
        mon = '' if it['brand'] != 'cwc' else (' monetization OK' if e.get('monetization') else ' monetization TODO')
        clip = '' if it['kind'] != 'yt_clip' else (' A/B/C OK' if e.get('abtest') else ' A/B/C TODO') + (' endscreen OK' if e.get('endscreen') else ' endscreen TODO')
        print(f'{it["publish_at"][5:16]} {it["id"]:14} ' + (f'{e["video_id"]} ' if e.get('video_id') else f'not uploaded (day {it.get("upload_day")}) ')
              + ('comment pinned' if c.get('pinned') else 'comment up, PIN TODO' if c.get('id') else 'no comment') + mon + clip)

def main():
    a = sys.argv[1:]
    if len(a) < 2: print(__doc__); sys.exit(1)
    cmd, R = a[0], a[1].rstrip('/')
    if cmd == 'due': due(R, '--alert-pins' in a, '--telegram' in a)
    elif cmd == 'mark': mark(R, a[2], a[3], a[4] if len(a) > 4 else '')
    elif cmd == 'status': status(R)
    elif cmd == 'arm':                                                  # the go-live watch is running (a session cron) - next.py refuses to call the run done without it
        if len(a) < 3 or len(a[2].strip()) < 4: C.fail('arm <RUN> "<cron job id + what it runs>"')
        r = C.run(R); r['golive_watch'] = {'job': a[2].strip(), 'at': C.now()}; C.save_run(R, r); print('go-live watch recorded:', a[2].strip())
    elif cmd == 'alert': alert(R, ' '.join(a[2:]) or C.fail('alert <RUN> "<text>"'), emergency=True)      # a session's deliberate line: EMERGENCIES ONLY (Colden 2026-10-10)
    else: print(__doc__); sys.exit(1)

if __name__ == '__main__': main()
