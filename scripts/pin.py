"""pin.py due|mark|status|alert <RUN>      PINNED COMMENTS at go-live, monetization records, Telegram alerts
Colden 2026-10-03: "You will also need to manage pinned comments at the exact time of posting. make sure this thread stays
active and send a telegram message if there is an error with uploading or pinned comments ASAP" / monetization: "it needs to
be turned on and then clicked that no harmful or violative content is being shared (you can always agree to that)" -
"monetization step only applies to @coldenraisher channel" (The Creative Lens is not in the Partner Program).
  due    <RUN>   every uploaded YouTube item whose publish time has passed (>= 45 s) and has no comment yet: reads the
                 video back - public = the comment goes up through the API as the channel (commentThreads.insert;
                 clips: the package's pinned comment, Shorts: the reel's first comment, the same question Metricool posts
                 on IG / TikTok / FB), recorded in publish_log.json BEFORE anything else. The API cannot pin: every
                 comment that is up and not pinned yet is printed as a PIN line - Claude pins it ON YOUTUBE (Chrome, the
                 Short / watch page's comments, with youtube.com switched to that channel; Studio's comment menu has no
                 Pin - 2026-10-03), then `mark ... pinned`. Not public yet: WAIT (retry in a few minutes); still not public 15 min after its
                 time: ALERT. exit 0 nothing left to post now, 3 = WAIT lines, 1 = an error (already sent to Telegram)
  mark   <RUN> <item id> pinned|monetization|abtest|endscreen "<what you saw>"     what was done by hand in Studio
         (abtest = Test & Compare "Title and thumbnail" with the plan's A/B/C pairs - Colden 2026-09-15 + 2026-10-06
         "Why are there no A/B tests"; endscreen = his master imported, targets re-pointed; both clips only)
  status <RUN>   every YouTube item: uploaded, comment, pinned, monetization
  alert  <RUN> "<text>"   one Telegram message to Colden (for an error found outside these scripts, e.g. a refused command)
GATES: the approved plan; a comment is never posted twice (publish_log before the next call); a video that is not public
gets no comment; every error goes to Telegram at once."""
import os, sys, json, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

GRACE_S, LATE_MIN = 45, 15

def approved(R):
    r = C.run(R); P = C.load(f'{R}/plan.json') or C.fail('no plan.json')
    if (r.get('plan_approval') or {}).get('sha') != P['sha']: C.fail('the plan is not approved')
    return r, P

def alert(R, text):
    r = C.load(f'{R}/run.json') or {}
    msg = f'⚠️ CWC_PodRun {r.get("show_name", "")} {r.get("ep_key", "")}: {text}'[:3900]
    try:
        import tg; tg.say(msg); C.event(R, f'ALERT SENT {text[:200]}')
    except BaseException as x: C.event(R, f'ALERT NOT SENT ({type(x).__name__}) {text[:200]}'); print(f'TELEGRAM FAILED: {x}', file=sys.stderr)
    print(f'ALERT: {text}', file=sys.stderr)

def comment_text(r, it):
    if it['kind'] == 'yt_clip': return (it.get('pinned_comment') or '').strip()
    d = C.reels_delivery(r) or {}
    s = next((s for s in d.get('shorts', []) if s.get('id') == it['ref']), None) or {}
    return ((s.get('copy') or {}).get('first_comment') or '').strip()

def due(R):
    import ytapi as Y
    r, P = approved(R); log = C.load(f'{R}/publish_log.json', {}) or {}; now = dt.datetime.now(C.ET); waits, errors = [], []
    for it in [i for i in P['items'] if i['kind'] in ('yt_clip', 'yt_short')]:
        e = log.get(it['id']); at = dt.datetime.fromisoformat(it['publish_at'])
        if now < at + dt.timedelta(seconds=GRACE_S): continue
        if not e or not e.get('video_id'):
            if now > at + dt.timedelta(minutes=LATE_MIN) and not (e or {}).get('late_alerted'):
                errors.append(f'{it["id"]} "{it["title"][:60]}" was due {it["publish_at"][:16]} ET and is NOT on YouTube (upload missing)')
                log.setdefault(it['id'], {}); log[it['id']]['late_alerted'] = C.now(); C.save(f'{R}/publish_log.json', log)
            continue
        if (e.get('comment') or {}).get('id'): continue
        text = comment_text(r, it)
        if not text: errors.append(f'{it["id"]}: no comment text in the plan / delivery'); continue
        try:
            v = Y.video_status(it['brand'], e['video_id'])
        except SystemExit: raise
        except Exception as x: errors.append(f'{it["id"]}: could not read the video back ({type(x).__name__}: {str(x)[:150]})'); continue
        st = (v or {}).get('status') or {}
        if st.get('privacyStatus') != 'public':
            if now > at + dt.timedelta(minutes=LATE_MIN): errors.append(f'{it["id"]} https://youtu.be/{e["video_id"]} is still {st.get("privacyStatus")} {round((now - at).total_seconds() / 60)} min after its publish time (publishAt {st.get("publishAt")})')
            else: waits.append(it['id']); print(f'WAIT {it["id"]}: {st.get("privacyStatus")} - publishes {it["publish_at"][11:16]} ET')
            continue
        try:
            cid = Y.add_comment(it['brand'], e['video_id'], text)
        except SystemExit: raise
        except Exception as x: errors.append(f'{it["id"]} https://youtu.be/{e["video_id"]}: the comment was refused ({type(x).__name__}: {str(x)[:200]}) - post + pin it by hand: "{text}"'); continue
        log = C.load(f'{R}/publish_log.json', {}) or {}
        log[it['id']]['comment'] = {'id': cid, 'at': C.now(), 'text': text, 'pinned': False}; C.save(f'{R}/publish_log.json', log)
        C.event(R, f'COMMENT {it["id"]} {cid}'); print(f'posted {it["id"]}: comment {cid}')
    log = C.load(f'{R}/publish_log.json', {}) or {}
    for it in [i for i in P['items'] if i['kind'] in ('yt_clip', 'yt_short')]:
        c = (log.get(it['id']) or {}).get('comment') or {}
        if c.get('id') and not c.get('pinned'):
            v = log[it['id']]['video_id']; url = f'https://www.youtube.com/shorts/{v}' if it['kind'] == 'yt_short' else f'https://www.youtube.com/watch?v={v}'
            print(f'PIN {it["id"]} {it["brand"]} video {v} comment {c["id"]}: {url} (channel switched to {it["brand"]}) | "{c["text"][:70]}"')
    for x in errors: alert(R, x)
    sys.exit(1 if errors else 3 if waits else 0)

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
    else: C.fail('mark <RUN> <item id> pinned|monetization|abtest|endscreen "<what you saw>"')
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
    if cmd == 'due': due(R)
    elif cmd == 'mark': mark(R, a[2], a[3], a[4] if len(a) > 4 else '')
    elif cmd == 'status': status(R)
    elif cmd == 'alert': alert(R, ' '.join(a[2:]) or C.fail('alert <RUN> "<text>"'))
    else: print(__doc__); sys.exit(1)

if __name__ == '__main__': main()
