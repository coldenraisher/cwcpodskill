"""next.py <RUN> [--json]      WHERE THE EPISODE STANDS across the whole pipeline and the NEXT STEP - run it first, run it often.
Reads state files only (CWC_PodCut's manifest, CWC_PodClips' `next.py --json`, CWC_PodReels' WORK files, this run's
files); no Resolve, no Telegram, no network. Always exits 0 - it reports, it gates nothing.
--json: {"stage", "done": [..], "waiting_on_colden": [..], "next": [..], "products": {...}}
stage: podcut -> tandem (clips + reels) -> window -> calendar -> plan -> approval -> publish -> wrapup -> cleanup -> done"""
import os, sys, json, glob, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

def podcut(r, out):
    m = C.podcut_manifest(r); S = C.PODCUT_SK
    if not m:
        out['next'].append(f'/CWC_PodCut: python3 {S}/scripts/prep.py "{r["episode_dir"]}"  (exit 2 = ask Colden, 3 = convert the BRAW first) -> LOOK at the two sheets -> ack.py -> build.py')
        return False
    L = m.get('locked') or {}
    if m.get('rebuild'): out['next'].append(f'PodCut re-opened by unlock.py ({m["rebuild"]}) - finish the new version in /CWC_PodCut; clips / reels wait'); return False
    if not L:
        cuts = [c.get('timeline') for c in m.get('cuts', [])]
        out['next'].append(f'/CWC_PodCut in progress (cache {r["podcut_cache"]}; cuts so far: {cuts or "none"}) - continue prep / ack / build; Creative Lens auto-locks after VERIFY')
        return False
    out['done'].append(f'PodCut locked: "{L.get("timeline")}" at {L.get("at")} ({L.get("by")})')
    out['products']['podcut'] = {'timeline': L.get('timeline'), 'snapshot': L.get('snapshot'), 'at': L.get('at')}
    return True

def clips(r, out):
    W = r['clips_work']
    if not os.path.exists(f'{W}/episode.json'):
        out['next'].append(f'/CWC_PodClips: python3 {C.CLIPS_SK}/scripts/intake.py "{r["podcut_cache"]}"  (Stage 1 starts there)'); return False
    try:
        res = subprocess.run([sys.executable, f'{C.CLIPS_SK}/scripts/next.py', W, '--json'], capture_output=True, text=True, timeout=60)
        st = json.loads(res.stdout or '{}')
    except Exception as x:
        out['next'].append(f'CWC_PodClips next.py could not be read ({type(x).__name__}) - run it by hand: python3 {C.CLIPS_SK}/scripts/next.py "{W}"'); return False
    for w in st.get('waiting_on_colden', []): out['waiting'].append(f'clips: {w}')
    if st.get('stage') == 'delivered':
        d = C.clips_delivery(r) or {}
        out['done'].append(f'clips delivered: {len(d.get("clips", []))} uploads in {r["episode_dir"]}/Final/Clips')
        out['products']['clips'] = {'uploads': len(d.get('clips', [])), 'needs': sorted({n for c in d.get('clips', []) for n in c.get('needs', [])})}
        return True
    for n in st.get('next', [])[:6]: out['next'].append(f'clips: {n}')
    out['products']['clips'] = {'stage': st.get('stage')}
    return False

def reels(r, out):
    W = r['reels_work']
    if not os.path.exists(f'{W}/episode.json'):
        out['next'].append(f'/CWC_PodReels: python3 {C.REELS_SK}/scripts/intake.py "{r["podcut_cache"]}"  (Stage 1 starts there)'); return False
    if os.path.exists(f'{C.REELS_SK}/scripts/next.py'):              # PodReels with a PodClips-like next.py --json (being finished 2026-10-03)
        try:
            st = json.loads(subprocess.run([sys.executable, f'{C.REELS_SK}/scripts/next.py', W, '--json'], capture_output=True, text=True, timeout=60).stdout or '{}')
        except Exception: st = {}
        for w in st.get('waiting_on_colden', []): out['waiting'].append(f'reels: {w}')
        if st and st.get('stage') != 'delivered':
            for n in st.get('next', [])[:6]: out['next'].append(f'reels: {n}')
            out['products']['reels'] = {'stage': st.get('stage')}; return False
    d = C.reels_delivery(r)
    if d and C.mtime(f'{W}/delivery.json') >= max([C.mtime(p) for p in glob.glob(f'{W}/edit/*/versions.json')] or [0]):
        rows = d.get('reels') or d.get('shorts') or d.get('uploads') or []
        out['done'].append(f'reels delivered: {len(rows)} entries' + (f' in {d["final_dir"]}' if d.get('final_dir') else ''))
        out['products']['reels'] = {'entries': len(rows)}
        return True
    ap = (C.load(f'{W}/approved.json') or {}).get('approved', [])
    if not ap:
        out['next'].append('reels Stage 1: themes -> cold reads -> check.py -> tg_cards.py send (approved.json appears when every card is settled)'); return False
    edits = {a['id']: next((v for v in reversed(C.load(f'{W}/edit/{a["id"]}/versions.json', []) or []) if v.get('status') in ('approved', 'locked')), None) for a in ap}
    mastered = [k for k, v in edits.items() if v and (v.get('master') or {}).get('file')]
    cp = (C.load(f'{W}/copy.json') or {}).get('shorts', {})
    batch = [k for k, c in cp.items() if c.get('status') == 'approved' and c.get('cover')]
    out['products']['reels'] = {'approved_themes': len(ap), 'edits_approved': sum(1 for v in edits.values() if v), 'mastered': len(mastered), 'covers_copy_approved': len(batch)}
    if len(mastered) < len(ap): out['next'].append(f'reels Stage 2: {len(mastered)}/{len(ap)} shorts approved + mastered (build -> review -> tg_review send -> master)')
    elif len(batch) < len(mastered): out['next'].append(f'reels Stage 3: covers + copy approved for {len(batch)}/{len(mastered)} (cover.py ... -> postcopy.py -> tg_batch.py send)')
    else: out['next'].append(f'reels: lock + deliver (finals + dashboard on the NAS, delivery.json). Do NOT run its own posting steps (publish.py plan / payloads / tg_plan): CWC_PodRun plans and posts every product.')
    return False

def ours(r, R, out):
    pl = C.load(f'{R}/plan.json'); ap = (r.get('plan_approval') or {})
    w = C.window(r, confirmed=True)
    if not w or w['start'] < C.now()[:10]:
        out['stage'] = 'window'
        if r.get('window_notes_open'): out['next'].append(f'his window answer: "{r["window_notes_open"]}" -> window.py set "{R}" START END --by "<his words>"')
        elif (r.get('window_card') or {}).get('at') and not w: out['waiting'].append('posting-window card on Telegram (Use this / Change)')
        else: out['next'].append(f'ask Colden for the posting window: python3 {C.SK}/scripts/window.py ask "{R}"  (or in the session; then window.py set ... --by "<his words>")' + (' - the confirmed one has already started' if w else ''))
        return
    cal = [f'{R}/calendar/youtube.json'] + [f'{R}/calendar/metricool_{b}.json' for b in ('cwc', 'tcl')]
    if not pl:
        missing = [os.path.basename(p) for p in cal if not os.path.exists(p)]
        if missing: out['stage'] = 'calendar'; out['next'].append(f'calendar: {", ".join(missing)} missing - SKILL.md step 4 (cal.py youtube; Metricool getScheduledPosts per brand -> cal.py metricool; best times -> cal.py besttimes)')
        else: out['stage'] = 'plan'; out['next'].append(f'python3 {C.SK}/scripts/plan.py build "{R}"  then  tg_plan.py send "{R}"')
        return
    if ap.get('sha') != pl.get('sha'):
        out['stage'] = 'approval'
        if r.get('plan_card', {}).get('sha') == pl.get('sha') and not r.get('plan_notes_open'): out['waiting'].append('posting plan card on Telegram (Schedule all / Changes)')
        elif r.get('plan_notes_open'): out['next'].append(f'his plan notes: "{r["plan_notes_open"][:120]}" -> change the inputs, plan.py build, tg_plan.py send')
        else: out['next'].append(f'python3 {C.SK}/scripts/tg_plan.py send "{R}"')
        return
    out['done'].append(f'plan approved by {ap.get("by")} at {ap.get("at")} ({len(pl["items"])} posts)')
    log = C.load(f'{R}/publish_log.json', {}) or {}
    todo = [i for i in pl['items'] if i['id'] not in log]
    if todo:
        out['stage'] = 'publish'
        by = {}
        for i in todo: by.setdefault(i['route'], []).append(i['id'])
        for route, ids in by.items(): out['next'].append(f'publish {route}: {len(ids)} left ({", ".join(ids[:6])}{"..." if len(ids) > 6 else ""}) - SKILL.md step 7')
        return
    out['done'].append(f'every planned post handled ({len(log)})')
    if not r.get('stages', {}).get('wrapup'):
        out['stage'] = 'wrapup'; out['next'].append(f'python3 {C.SK}/scripts/dashboard.py "{R}"  then youtube.py checklist + tg_plan.py wrapup (SKILL.md step 7)')
        return
    if not r.get('stages', {}).get('cleanup'):
        out['stage'] = 'cleanup'
        if (r.get('cleanup_card') or {}).get('sha') and (r.get('cleanup_approval') or {}).get('sha') != r['cleanup_card']['sha']: out['waiting'].append('cleanup card on Telegram (Clean up / Not now)')
        elif (r.get('cleanup_approval') or {}).get('sha'): out['next'].append(f'python3 {C.SK}/scripts/cleanup.py apply "{R}"')
        else: out['next'].append(f'python3 {C.SK}/scripts/cleanup.py scan "{R}"  then  cleanup.py card "{R}" (SKILL.md step 8)')
        return
    out['stage'] = 'done'

def main():
    R = sys.argv[1].rstrip('/'); as_json = '--json' in sys.argv
    r = C.run(R); out = {'stage': 'podcut', 'done': [], 'waiting': [], 'next': [], 'products': {}}
    if podcut(r, out):
        out['stage'] = 'tandem'
        a = clips(r, out); b = reels(r, out)
        if a and b: ours(r, R, out)
    res = {'stage': out['stage'], 'done': out['done'], 'waiting_on_colden': out['waiting'], 'next': out['next'], 'products': out['products']}
    if as_json: print(json.dumps(res, indent=1, ensure_ascii=False)); return
    w = C.window(r); conf = 'confirmed' if C.window(r, True) else 'PROPOSED, not confirmed'
    print(f'{r["show_name"]} {r["ep_key"]} - stage: {res["stage"]}   (window {w["start_dow"]} {w["start"]} -> {w["end_dow"]} {w["end"]}, {conf})')
    for k, label in (('done', 'DONE'), ('waiting_on_colden', 'WAITING ON COLDEN'), ('next', 'NEXT')):
        for line in res[k]: print(f'  {label}: {line}')

if __name__ == '__main__': main()
