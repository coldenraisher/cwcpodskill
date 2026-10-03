"""lock.py <WORK> [--dry-run]      LOCK every approved short of the episode, CLEAN UP, write delivery.json - automatically
(ported from CWC_PodClips lock.py; Colden 2026-10-02 for the pipeline: "clean up should be automatic. Anything that the
timeline or final output does not rely on can be trashed. For hard files, send to trash, i will manually delete from
there in case of error").
READY when every theme in approved.json has an APPROVED edit with its master on disk, no edit card is still waiting on
Telegram (sent / changes), and the covers + copy batch is approved (copy.json: every posting short approved + cover).
LOCK     each approved short timeline: green LOCKED marker (custom data cwc-podreels-lock), the red DRAFT marker removed,
         renamed '<name> (L)'; the short's newest Resolve-made cover timeline likewise (the cover may be re-rendered);
         versions.json status 'locked'.
CLEANUP  Resolve: every other timeline this skill made for the episode (superseded / failed / never-approved versions,
         'zz BUILDING' leftovers, older cover versions) is exported as a .drt into the Trash, then removed; b-roll clips
         in <bin>/Shorts/B-Roll that no locked short uses leave the pool. Files (moved, never deleted; NAS files to the
         share's #recycle/CWC_PodReels/, local files to ~/.Trash/CWC_PodReels <show> <Ep> <time>/): preview renders and
         their frames / sheets, the raw pre-loudness master renders, cover candidate frames and unused AI raws, b-roll
         renders no locked short uses.
KEPT     the locked timelines and their media, Renders/ (masters), the picked covers, every plan / version / decision /
         theme / copy record.
DELIVERY WORK/delivery.json for the aggregator: per short its title, destination + brands, master, cover, copy fields,
         Metricool post ids (review/publish.json) and the locked timeline.
NOT READY -> exit 2, nothing touched."""
import os, re, sys, json, time, shutil, subprocess
import common as C
HERE = os.path.dirname(os.path.abspath(__file__))
def rs(script, seconds, **kw):
    out = subprocess.run([sys.executable, f'{HERE}/rs.py', str(seconds), f'{HERE}/{script}'] + [f'{k}={json.dumps(v)}' for k, v in kw.items()], capture_output=True, text=True).stdout.strip().splitlines()
    r = json.loads(out[-1]) if out else {'error': 'no answer from Resolve'}
    if isinstance(r, dict) and r.get('error'): C.fail(f'Resolve ({script} {kw.get("STEP", "")}): {r["error"]}')
    return r
def ready(W):
    ap = (C.load(f'{W}/approved.json') or {}).get('approved', []); items = (C.load(f'{W}/review/edits.json') or {}).get('items', {}); cp = (C.load(f'{W}/copy.json') or {}).get('shorts', {})
    rows, missing = [], []
    for a in ap:
        tid = a['id']; vs = C.load(f'{W}/edit/{tid}/versions.json', []) or []
        for k, it in items.items():
            if k.startswith(tid + '|') and it.get('status') in ('sent', 'changes'): missing.append(f'{k}: ' + ('his Changes note has no new version yet' if it['status'] == 'changes' else 'the edit card is still waiting on Telegram'))
        v = next((x for x in reversed(vs) if x.get('status') in ('approved', 'locked')), None)
        if not v: missing.append(f'{tid}: no approved edit'); continue
        if vs and vs[-1] is not v and not str(vs[-1].get('status', '')).startswith(('superseded', 'failed')): missing.append(f'{tid}: a newer build v{vs[-1]["v"]} is "{vs[-1].get("status")}"')
        if not (v.get('master') and os.path.exists(v['master']['file'])): missing.append(f'{tid} v{v["v"]}: no master (master.py render)'); continue
        c = cp.get(tid)
        if v.get('destination') != 'todd' and not (c and c.get('status') == 'approved' and c.get('cover')): missing.append(f'{tid}: covers + copy not approved on the batch card')
        rows.append((tid, v))
    return rows, missing
def to_trash(path, trash, rel):
    m = re.match(r'^(/Volumes/[^/]+)/', path); dest = None
    if m and os.path.isdir(f'{m.group(1)}/#recycle'): dest = f'{m.group(1)}/#recycle/CWC_PodReels/{os.path.basename(trash)}/{rel}'
    dest = dest or f'{trash}/{rel}'; os.makedirs(os.path.dirname(dest), exist_ok=True); shutil.move(path, dest); return dest
def main(W, dry):
    ep = C.episode(W); rows, missing = ready(W)
    if missing: C.ask('not every short is ready to lock:\n  ' + '\n  '.join(missing))
    if not rows: C.fail('nothing approved to lock')
    LOCK = {}; plans = {}
    for tid, v in rows:
        LOCK[v['timeline']] = v['timeline'] if v['timeline'].endswith(' (L)') else v['timeline'] + ' (L)'; plans[tid] = C.load(v['plan'])
        cv = (C.load(f'{W}/edit/{tid}/cover.json') or {}).get('resolve_versions') or []
        if cv: n = cv[-1]['timeline']; LOCK[n] = n if n.endswith(' (L)') else n + ' (L)'
    keep_tl = set(LOCK) | set(LOCK.values()); delete = []
    for d in sorted(x for x in os.listdir(f'{W}/edit') if re.fullmatch(r's\d+', x)):
        names = [v.get('timeline') for v in C.load(f'{W}/edit/{d}/versions.json', []) or []] + [c['timeline'] for c in (C.load(f'{W}/edit/{d}/cover.json') or {}).get('resolve_versions') or []]
        for n in names:
            for x in (n, 'zz BUILDING ' + re.sub(r' \(L\)$', '', n or '')):
                if x and x not in keep_tl and x not in delete: delete.append(x)
    keep_broll = sorted({b['file'] for P in plans.values() for b in P.get('broll', [])})
    cp = (C.load(f'{W}/copy.json') or {}).get('shorts', {}); keep_files = {os.path.realpath(v['master']['file']) for _, v in rows} | {os.path.realpath(c['cover']) for c in cp.values() if c.get('cover')}
    stamp = time.strftime('%Y%m%d-%H%M%S'); trash = os.path.expanduser(f'~/.Trash/CWC_PodReels {ep["show"]} {ep["ep_key"]} {stamp}'); moves = []
    for d in sorted(x for x in os.listdir(f'{W}/edit') if re.fullmatch(r's\d+', x)):
        p = f'{W}/edit/{d}'
        for sub in ('preview', 'master', 'cover/cand', 'cover/_near', 'cover/_chk'):
            if os.path.isdir(f'{p}/{sub}'): moves.append((f'{p}/{sub}', f'edit/{d}/{sub}'))
        for f in sorted(os.listdir(f'{p}/cover')) if os.path.isdir(f'{p}/cover') else []:
            if re.match(r'ai_raw_\d+\.png$|resolve_cover_v\d+.*\.tif(\.old)?$', f) and os.path.realpath(f'{p}/cover/{f}') not in keep_files: moves.append((f'{p}/cover/{f}', f'edit/{d}/cover/{f}'))
    bd = f'{ep["shorts_dir"]}/B-Roll'
    if os.path.isdir(bd):
        kb = {os.path.realpath(x) for x in keep_broll}
        for f in sorted(os.listdir(bd)):
            if not f.startswith('.') and os.path.realpath(f'{bd}/{f}') not in kb: moves.append((f'{bd}/{f}', f'b-roll/{f}'))
    print(f'LOCK {len(LOCK)} timeline(s):'); [print(f'  {a} -> {b}') for a, b in LOCK.items()]
    print(f'REMOVE from Resolve (after a .drt backup) if present: {delete}'); print(f'TRASH {len(moves)} file(s) / folder(s):'); [print(f'  {a}') for a, _ in moves]
    if dry: print('\ndry run - nothing was changed'); return 0
    r = rs('r_lock.py', 300, PROJECT=ep['project'], STEP='lock', LOCK=LOCK, DELETE=[], RELOCKED=[], BROLL_BIN='', KEEP_BROLL=[], BACKUP_DIR='')
    if r['problems']: C.fail(f'lock: {r["problems"]}')
    for tid, v in rows:
        vs = C.load(f'{W}/edit/{tid}/versions.json'); row = next(x for x in vs if x['v'] == v['v']); row.update(status='locked', timeline=LOCK[v['timeline']], built_as=row.get('built_as') or v['timeline'], locked_at=row.get('locked_at') or C.now()); C.save(f'{W}/edit/{tid}/versions.json', vs)
    tl = rs('r_list_tl.py', 120, PROJECT=ep['project'])['timelines']; P0 = next(iter(plans.values()))
    r = rs('r_lock.py', 900, PROJECT=ep['project'], STEP='cleanup', LOCK={}, DELETE=[n for n in delete if n in tl], RELOCKED=[], BROLL_BIN=f'{P0["bin"]}/{P0["shorts_bin"]}/B-Roll', KEEP_BROLL=keep_broll, BACKUP_DIR=f'{trash}/timelines')
    moved = [[a, to_trash(a, trash, rel)] for a, rel in moves if os.path.exists(a)]
    pubs = C.load(f'{W}/review/publish.json', {}) or {}
    delivery = {'at': C.now(), 'skill': 'CWC_PodReels', 'episode': ep['ep_key'], 'show': ep['show'], 'shorts': [
        {'id': tid, 'title': plans[tid]['title'], 'destination': v.get('destination'), 'brands': (cp.get(tid) or {}).get('brands', []), 'timeline': LOCK[v['timeline']], 'master': v['master']['file'],
         'frames': plans[tid]['frames'], 'loudness': (v['master'].get('loudness') or {}).get('out'), 'cover': (cp.get(tid) or {}).get('cover'), 'cover_kind': (cp.get(tid) or {}).get('cover_kind'),
         'copy': {k: (cp.get(tid) or {}).get(k) for k in ('caption', 'first_comment', 'yt_title', 'fb_title', 'playlist', 'ig_collab')}, 'metricool_posts': pubs.get('posts', {}).get(tid, {})} for tid, v in rows],
        'cleanup': {'timelines_removed': r['removed'], 'timeline_backups': f'{trash}/timelines', 'broll_pool_removed': r['broll_removed'], 'files_moved': moved, 'problems': r['problems']}}
    C.save(f'{W}/delivery.json', delivery); C.event(W, f'LOCKED {len(rows)} shorts; removed {len(r["removed"])} timelines; moved {len(moved)} files to the Trash')
    print(f'\nLOCKED {len(rows)}; removed {len(r["removed"])} timeline(s) (backups {trash}/timelines); {len(r["broll_removed"])} unused b-roll pool clip(s); {len(moved)} moved to the Trash -> delivery.json')
    for p in r['problems']: print('  PROBLEM:', p)
    try:
        import tg_api as TG
        TG.say(f'🔒 {ep["show_name"]} {ep["ep_key"]} shorts locked: {len(rows)} masters.\nCleanup: {len(r["removed"])} timelines + {len(moved)} files to the Trash (restorable).')
    except Exception as e: print('telegram note not sent:', str(e)[:100])
    return 1 if r['problems'] else 0
if __name__ == '__main__':
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    if not a: C.fail(__doc__)
    sys.exit(main(os.path.abspath(a[0]), '--dry-run' in sys.argv))
