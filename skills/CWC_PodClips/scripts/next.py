"""next.py <WORK> [--json]      WHERE THE EPISODE STANDS and the NEXT STEP of every clip - run it first, run it often.
Reads only the state files (no Resolve, no Telegram, no network) and prints, in pipeline order, what is done, what is
waiting on Colden, and the exact command (or judgement step) that comes next. A fresh session starts here; the
aggregator can read `--json` ({stage, done, waiting_on_colden: [...], next: [...]}; stage "delivered" = finished).
Always exits 0 (it reports, it gates nothing); the state is in the output."""
import os, re, sys, json, glob
import common as C

def stage1(W, out):
    if not os.path.exists(f'{W}/episode.json'): out['next'].append('intake.py "<PodCut CACHE>"   (the episode has no WORK folder yet)'); return False
    if not os.path.exists(f'{W}/themes.json'): out['next'].append(f'Stage 1: channel_data.py pull; learn.py report; evidence.py trends; READ the whole transcript; write themes.json (SKILL.md "How to build the themes")'); return False
    st = C.load(f'{W}/review/state.json', {}) or {}
    if not os.path.exists(f'{W}/approved.json'):
        if not os.path.exists(f'{W}/checked.json'): out['next'].append('assemble.py + a cold read per theme (coldread.py prompt / record), then check.py'); return False
        th = st.get('themes') or {}
        if not th: out['next'].append('check.py (exit 0 -> tg_themes.py send; exit 2 too_few -> tg_themes.py flag)'); return False
        for t, v in th.items():
            if v['status'] == 'sent': out['waiting'].append(f'theme {t}: card on Telegram')
            elif v['status'] == 'notes': out['next'].append(f'theme {t}: his notes "{(v.get("notes") or [{}])[-1].get("text", "")[:80]}" -> revise themes.json, cold read again, check.py, tg_themes.py resend "<WORK>" {t}')
        return False
    ap = C.load(f'{W}/approved.json') or {}
    for t, v in (st.get('themes') or {}).items():          # a revised theme that went back to him (resend) is open again
        if v['status'] == 'sent': out['waiting'].append(f'theme {t}: revised card on Telegram (its edit waits for his answer)'); out['open_themes'].add(t)
        elif v['status'] == 'notes': out['next'].append(f'theme {t}: his notes "{(v.get("notes") or [{}])[-1].get("text", "")[:80]}" -> revise themes.json, assemble.py, cold read, check.py, tg_themes.py resend "<WORK>" {t}'); out['open_themes'].add(t)
    out['done'].append(f'themes: {len(ap.get("approved", []))} approved' + (f', {len(ap["dropped"])} dropped at the edit' if ap.get('dropped') else ''))
    ep = C.load(f'{W}/episode.json') or {}; m = C.load(f'{ep.get("podcut_cache")}/manifest.json') or {}; L = m.get('locked') or {}
    if m and (m.get('rebuild') or not L or (os.path.exists(f'{L.get("snapshot")}/plan.json') and C.sha_file(f'{L["snapshot"]}/plan.json') != ep.get('plan_sha'))):
        out['next'].append('THE PODCUT CHANGED since intake (re-opened or re-locked): STOP - clips already locked stay valid; anything not yet locked is built on the old cut. Ask Colden before going on (SKILL.md "When things change").')
    return True

def stage2(W, out):
    ap = C.load(f'{W}/approved.json'); ck = C.load(f'{W}/checked.json') or {}; rv = (C.load(f'{W}/edit/review.json', {}) or {}).get('items', {}); all_ok = True
    for a in ap.get('approved', []):
        tid = a['id']; sug = ((ck.get('themes', {}).get(tid) or {}).get('suggest') or {}).get('channel') or 'cwc'; vs = C.load(C.vpath(W, tid), []) or []
        live = [v for v in vs if not str(v.get('status', '')).startswith(('superseded', 'rejected'))]
        okv = [v for v in live if v.get('status') in ('approved', 'locked')]
        if tid in out['open_themes']: all_ok = False; continue
        newer = [chv[-1] for chv in ([v for v in live if v['channel'] == c] for c in sorted({v['channel'] for v in live})) if okv and chv[-1].get('status') not in ('approved', 'locked')]
        if newer:                                          # a new version after an approval / after the lock: it goes through the same review
            all_ok = False
            for v in newer: draft(W, tid, v, rv, out)
            continue
        if okv:
            chans = sorted({c for v in okv for c in (v.get('channels') or [])})
            for ch in chans:
                mine = [v for v in okv if v['channel'] == ch and ch in (v.get('channels') or [])]
                if not mine: out['next'].append(f'{tid}: approved for {ch} but not built with the {ch} stinger -> build.py "<WORK>" {tid} --channel {ch}   (same edit = approved automatically)'); all_ok = False
                elif not (mine[-1].get('master') and os.path.exists(mine[-1]['master']['file'])): out['next'].append(f'{tid} {ch}: master.py render "<WORK>" {tid} {ch}'); all_ok = False
            continue
        all_ok = False
        if not os.path.exists(f'{W}/edit/{tid}/broll.json'): out['next'].append(f'{tid}: cut.py "<WORK>" {tid} --channel {sug} (fix every PROBLEM), then b-roll: capture.py -> LOOK -> broll.py prep -> write edit/{tid}/broll.json (origin, why, looked)'); continue
        if not live: out['next'].append(f'{tid}: build.py "<WORK>" {tid} --channel {sug}   (ask first if Colden may be working in Resolve)'); continue
        draft(W, tid, live[-1], rv, out)
    return all_ok

def draft(W, tid, v, rv, out):
    """the next step of one not-yet-approved version"""
    key = f'{tid}|{v["channel"]}|v{v["v"]}'; it = rv.get(key)
    if v.get('status') in ('building', 'failed'): out['next'].append(f'{key}: the build is "{v.get("status")}" ({v.get("problems")}) -> fix the cause, build.py again (a new version)'); return
    if it and it.get('status') == 'sent': out['waiting'].append(f'{key}: edit preview on Telegram'); return
    if it and it.get('status') == 'changes':
        n = (it.get('notes') or [{}])[-1].get('text')
        out['next'].append(f'{key}: CHANGES "{n}" -> fix (themes.json trims / ranges, broll.json), build.py (next version), review, send' if n else f'{key}: he tapped Changes - waiting for his message'); return
    if not v.get('preview') or not os.path.exists(v['preview']): out['next'].append(f'{key}: review.py render "<WORK>" {tid} --channel {v["channel"]}'); return
    pc = v.get('preview_check') or {}
    if not pc or pc.get('problems'): out['next'].append(f'{key}: review.py check problems {pc.get("problems")} -> fix'); return
    if not v.get('looked') or v['looked'].get('sheet_sha') != (C.sha_file(pc['sheet']) if os.path.exists(pc.get('sheet', '')) else None): out['next'].append(f'{key}: LOOK at {pc.get("sheet")} (every camera = this episode, b-roll, tag, ending), then review.py ack "<WORK>" {tid} "<what you saw>" --channel {v["channel"]}'); return
    out['next'].append(f'{key}: tg_edit.py send "<WORK>" {tid} --channel {v["channel"]} --note "<what he should listen / look for>"')

def stage3(W, out):
    L = C.load(f'{W}/lock.json')
    if not L: out['next'].append('lock.py "<WORK>"   (master.py runs it by itself after the last master; --dry-run shows what it will do)'); return False
    out['done'].append(f'locked: {len(L["clips"])} timelines (L), cleanup {"done" if L.get("cleaned") else "NOT done"}')
    rv = (C.load(f'{W}/package/review.json', {}) or {}).get('items', {}); ok = True
    if not L.get('cleaned') or (L.get('cleaned') or {}).get('problems'): out['next'].append(f'the lock cleanup is not clean ({(L.get("cleaned") or {}).get("problems") or "it did not run"}): read the problems, fix the cause, lock.py "<WORK>" again (ask first if Colden may be in Resolve)'); ok = False
    for c in L['clips']:
        tid, ch = c['theme'], c['channel']; k = f'{tid}|{ch}'; d = f'{W}/package/{tid}'; it = rv.get(k, {})
        if os.path.exists(f'{d}/package.{ch}.json') and it.get('abc') == 'approved' and C.load(f'{d}/package.{ch}.json').get('timeline') == c['timeline']: continue
        ok = False
        if not os.path.exists(f'{d}/facts.{ch}.json') or C.load(f'{d}/facts.{ch}.json').get('timeline') != c['timeline']: out['next'].append(f'{k}: package.py facts "<WORK>"'); continue
        if not os.path.exists(f'{d}/copy.{ch}.json'): out['next'].append(f'{k}: write {d}/copy.{ch}.json (3 titles, summary, chapters, pinned, topic_tags, hook_headline, claims_checked), then package.py check'); continue
        T = C.load(f'{d}/thumbs.{ch}.json', {}) or {}
        if not T.get('still_confirmed'): out['next'].append(f'{k}: thumbs.py frames "<WORK>" {tid} {ch} --scope episode -> LOOK at still_sheet.jpg -> thumbs.py still ... -> LOOK at eyes_check.jpg'); continue
        if not (T.get('hooks') or {}).get('2 hook'): out['next'].append(f'{k}: thumbs.py hook "<WORK>" {tid} {ch}'); continue
        if not all((T.get('ai') or {}).get(s) for s in ('ai-1', 'ai-2')): out['next'].append(f'{k}: AI thumbnails (thumbs.py prompt -> Higgsfield gpt_image_2 + nano_banana_pro -> LOOK -> thumbs.py add ... ai-1 / ai-2)'); continue
        if not T.get('grid'): out['next'].append(f'{k}: thumbs.py grid "<WORK>" {tid} {ch}'); continue
        if not it: out['next'].append(f'{k}: package.py check, then tg_pack.py send "<WORK>" {tid} {ch}'); continue
        if it.get('notes') and it['notes'][-1].get('at', '') > (it.get('abc_sent_at') or it.get('sent_at') or ''): out['next'].append(f'{k}: his package notes "{it["notes"][-1]["text"][:80]}" -> fix, send again'); continue
        if it.get('status') == 'sent': out['waiting'].append(f'{k}: title + thumbnail pick on Telegram'); continue
        cp = C.load(f'{d}/copy.{ch}.json') or {}
        if it.get('abc') == 'sent': out['waiting'].append(f'{k}: A/B/C card on Telegram'); continue
        if it.get('abc') != 'approved':
            if not cp.get('B') or not cp.get('C'): out['next'].append(f'{k}: A = "{cp.get("A")}" -> write "B" and "C" (+ hook_headline_B) into copy.{ch}.json, package.py check'); continue
            if not all(os.path.exists((T.get('abc') or {}).get(x, '')) for x in 'ABC') or not T.get('abc_grid'): out['next'].append(f'{k}: thumbs.py abc (B) ; thumbnail C from title C with {T.get("c_model", "the model of A")} -> LOOK -> thumbs.py add ... C ; thumbs.py abc'); continue
            out['next'].append(f'{k}: LOOK at {T.get("abc_grid")}, then tg_pack.py send-abc "<WORK>" {tid} {ch}'); continue
        out['next'].append(f'{k}: package.py build "<WORK>"')
    D = C.load(f'{W}/delivery.json')
    newer = D and any((C.load(f'{W}/package/{c["theme"]}/facts.{c["channel"]}.json') or {}).get('made_at', '') > D.get('at', '') for c in L['clips'])
    if ok and D and D.get('version', 1) >= 2 and not newer and len(D.get('clips', [])) == len(L['clips']) and not (D.get('final_dir') and all(c['master'].startswith(D['final_dir'] + '/') and os.path.exists(c['master']) for c in D['clips'])):
        out['next'].append('deliver.py "<WORK>"   (the finished files are not in <episode>/Final/Clips on the NAS yet - mount the share if it is not)'); ok = False
    if ok and (not D or D.get('version', 1) < 2 or newer or len(D.get('clips', [])) != len(L['clips']) or any(x['timeline'] not in {c['timeline'] for c in L['clips']} for x in D['clips'])): out['next'].append('package.py build "<WORK>"   (delivery.json is missing or older than the lock)'); ok = False
    return ok

def main(W):
    out = {'work': W, 'done': [], 'waiting': [], 'next': [], 'stage': 1, 'open_themes': set()}
    if stage1(W, out):
        out['stage'] = 2
        if stage2(W, out):
            out['stage'] = 3
            if stage3(W, out): out['stage'] = 'delivered'; out['done'].append('delivered: Final/Clips on the NAS + the Clips Dashboard; delivery.json written - hand over to the aggregator (references/aggregator_handoff.md)')
    pid = os.path.expanduser('~/.config/cwc/tg_listen.pid'); alive = False
    try: os.kill(int(open(pid).read().strip()), 0); alive = True
    except Exception: pass
    if out['waiting'] and not alive: out['next'].insert(0, 'tg_listen.py start   (cards are open and the listener is NOT running)')
    out['listener'] = alive
    return out

if __name__ == '__main__':
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    if not a: print(__doc__); sys.exit(0)
    o = main(os.path.abspath(a[0]))
    if '--json' in sys.argv: print(json.dumps({'stage': o['stage'], 'done': o['done'], 'waiting_on_colden': o['waiting'], 'next': o['next'], 'listener_running': o['listener']}, indent=1))
    else:
        print(f'{os.path.basename(os.path.dirname(o["work"]))} {os.path.basename(o["work"])} - stage {o["stage"]}   (Telegram listener {"running" if o["listener"] else "NOT running"})')
        for x in o['done']: print('  done    ', x)
        for x in o['waiting']: print('  COLDEN  ', x)
        for x in o['next']: print('  NEXT    ', x)
    sys.exit(0)
