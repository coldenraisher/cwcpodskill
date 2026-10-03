"""cleanup.py scan|card|apply|status <RUN> [--no-resolve] [--by "<Colden's words>"]      THE LAST STEP of an episode
Colden 2026-10-03: "after all that there will need to be a clean up step as well. just sweeping resolve and the disks for
extra generations or files that were saved but not used in the final outputs. these projects have quickly become dozens of
gigs on my local drives and NAS. the last step needs to be to clean up everything possible. NAS gets hard delete. Local
drive files get moved to the trash bin where I can delete."
  scan   READ-ONLY: Resolve listing of the episode bin (rs.py r_sweep.py list; --no-resolve skips it) + both disks ->
         cleanup/manifest.json with every path, its size and why it goes:
           NAS    PERMANENT delete
           local  moved to ~/.Trash/CWC_PodRun <show> <EpNN> <time>/ (Colden empties the Trash)
           Resolve timelines exported as .drt into that Trash folder, then removed; unused pool clips removed
  card   the totals as ONE Telegram card: [Clean up] [Not now] (tg_plan.py's plugin records the tap)
  apply  ONLY the manifest Colden approved (its sha - the card, or --by "<his words>" in the session): Resolve first, then
         local -> Trash, then NAS hard delete. Every path is re-checked right before it goes: still there, still not in the
         keep set. -> cleanup/done.json
  status
KEEP (never a candidate, re-checked at apply): everything in <episode>/Final (finals, dashboards, manual kits); every file
path any delivery names (masters, covers, thumbnails, captions); the program / camera / screen-share / intro files
CWC_PodCut's manifest lists and the lock snapshot's lower thirds; every file a timeline of the project uses (Resolve
listing); every record (.json .jsonl .md .txt .srt .csv .log .drt); the PodCut lock snapshot; anything outside the episode
folder, the episode's WORK folders and this episode's #recycle/CWC_Pod* folders.
CANDIDATES: NAS - the generated folders of the episode (Clips/B-Roll and its Source, Shorts/B-Roll, Shorts/Assets,
Shorts/Renders, Lower Thirds) - only with a fresh Resolve listing, else kept and reported - every *.rejected file, and this
episode's folders in the share's #recycle/CWC_Pod*. Local - media and large files (> 1 MB) in the episode's WORK folders.
Resolve - timelines in the episode bin that are not locked "(L)" and not a template ("00 ..."), and pool clips no timeline
of the project uses (never a source file).
GATES: only when every planned post is handled (the YouTube uploads read the masters); apply = the approved manifest only;
the Resolve apply needs a listing <= 6 h old and Colden present the first time (r_sweep.py has not run on a real project)."""
import os, re, sys, json, glob, shutil, subprocess, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

RECORD = {'.json', '.jsonl', '.md', '.txt', '.srt', '.csv', '.log', '.drt'}
NAS_GEN = ['Clips/B-Roll', 'Shorts/B-Roll', 'Shorts/Assets', 'Shorts/Renders', 'Lower Thirds']
LOCAL_MIN = 1024 * 1024

def size(p):
    if os.path.isfile(p): return os.path.getsize(p)
    return sum(os.path.getsize(os.path.join(d, f)) for d, _, fs in os.walk(p) for f in fs if os.path.exists(os.path.join(d, f)))

def gb(n): return f'{n / 1024 ** 3:.2f} GB' if n >= 1024 ** 3 else f'{n / 1024 ** 2:.0f} MB'

SKIP_KEYS = {'cleanup', 'cleanups', 'cleaned', 'files_moved', 'trash', 'timeline_backups', 'backup_dir'}

def paths_in(obj, out):
    """every absolute path string in a JSON record - except the records of what a skill already threw away"""
    if isinstance(obj, str) and obj.startswith('/'): out.add(os.path.realpath(obj))
    elif isinstance(obj, dict): [paths_in(v, out) for k, v in obj.items() if k not in SKIP_KEYS]
    elif isinstance(obj, list): [paths_in(v, out) for v in obj]
    return out

def keep_set(r, listing):
    keep = set()
    for d in (C.clips_delivery(r), C.reels_delivery(r)): paths_in(d or {}, keep)
    m = C.podcut_manifest(r) or {}
    for c in m.get('cameras', []) + m.get('screens', []): keep.add(os.path.realpath(c['path']))
    if m.get('intro'): keep.add(os.path.realpath(m['intro']))
    snap = (m.get('locked') or {}).get('snapshot')
    if snap: paths_in(C.load(f'{snap}/lower_thirds.json') or {}, keep)
    for p in (listing or {}).get('used_any', []): keep.add(os.path.realpath(p))
    return keep, snap

def protected(p, r, keep, snap):
    rp = os.path.realpath(p); final = os.path.realpath(f'{r["episode_dir"]}/Final')
    if rp in keep or rp == final or rp.startswith(final + os.sep): return 'kept'
    if snap and (rp == os.path.realpath(snap) or rp.startswith(os.path.realpath(snap) + os.sep)): return 'lock snapshot'
    if os.path.isfile(p) and os.path.splitext(p)[1].lower() in RECORD: return 'record'
    if os.path.isdir(p) and any(os.path.realpath(k).startswith(rp + os.sep) for k in keep): return 'holds a kept file'
    return None

def recycle_dirs(r):
    """this episode's folders in the share's #recycle, as the three skills name them (2026-10-03 on the NAS:
    CWC_PodCut/Ep24 <stamp>, CWC_PodClips/CWC_PodClips creative-lens Ep24 <stamp>, CWC_PodReels/creative-lens Ep24 lock <stamp>).
    The share = the first folder above the episode that holds a #recycle. A folder named for another show is never taken."""
    d = os.path.dirname(r['episode_dir'].rstrip('/')); rec = None
    while d and d != os.path.dirname(d):
        if os.path.isdir(f'{d}/#recycle'): rec = f'{d}/#recycle'; break
        d = os.path.dirname(d)
    out = set(); others = [s['id'] for s in C.shows() if s['id'] != r['show']]
    for d in glob.glob(f'{glob.escape(rec)}/CWC_Pod*/*') if rec else []:
        name = os.path.basename(d)
        if re.search(rf'(^|[ _-]){re.escape(r["ep_key"])}([ _-]|$)', name) and not any(o in name for o in others): out.add(d)
    return sorted(out)

def resolve_list(R, r):
    m = C.podcut_manifest(r) or {}; res = m.get('resolve') or {}
    if not res.get('project') or not res.get('bin'): C.ask('the PodCut manifest has no Resolve project / bin - cannot sweep Resolve (or run scan --no-resolve)')
    out = subprocess.run([sys.executable, f'{C.SK}/scripts/rs.py', '300', f'{C.SK}/scripts/r_sweep.py', f'PROJECT={json.dumps(res["project"])}',
                          f'STEP={json.dumps("list")}', f'BIN={json.dumps(res["bin"])}', 'DELETE_TL=[]', 'DELETE_MEDIA=[]', 'BACKUP_DIR=""', 'SOURCES=[]'],
                         capture_output=True, text=True).stdout.strip().splitlines()
    ans = json.loads(out[-1]) if out else {'error': 'no answer from Resolve'}
    if isinstance(ans, dict) and ans.get('error'): C.ask(f'Resolve listing failed: {ans["error"]} (Resolve open on {res["project"]}? or scan --no-resolve)')
    ans['at'] = C.now(); C.save(f'{R}/cleanup/resolve.json', ans); return ans

def scan(R, no_resolve):
    r = C.run(R); P = C.load(f'{R}/plan.json'); log = C.load(f'{R}/publish_log.json', {}) or {}
    if not P or (r.get('plan_approval') or {}).get('sha') != P['sha']: C.fail('no approved plan - cleanup is the last step')
    open_items = [i['id'] for i in P['items'] if not C.handled(i, log)]
    if open_items: C.fail(f'{len(open_items)} planned post(s) not handled yet ({", ".join(open_items[:6])}) - the masters must stay until they are up')
    listing = None if no_resolve else resolve_list(R, r)
    keep, snap = keep_set(r, listing); nas, local, notes = [], [], []
    ep = r['episode_dir']
    for rel in NAS_GEN:
        root = f'{ep}/{rel}'
        if not os.path.isdir(root): continue
        if not listing: notes.append(f'kept {rel}: no Resolve listing, so "not used by a locked timeline" cannot be proven'); continue
        for d, _, fs in os.walk(root):
            for f in fs:
                p = os.path.join(d, f)
                if not f.startswith('.') and not protected(p, r, keep, snap): nas.append({'path': p, 'bytes': size(p), 'why': f'{rel}: not used by any timeline or final'})
    for p in glob.glob(f'{glob.escape(ep)}/**/*.rejected', recursive=True):
        if not protected(p, r, keep, snap) and not any(x['path'] == p for x in nas): nas.append({'path': p, 'bytes': size(p), 'why': 'rejected generation'})
    for d in recycle_dirs(r): nas.append({'path': d, 'bytes': size(d), 'why': 'already discarded by a pipeline skill (#recycle)'})
    for root in (r['podcut_cache'], r['clips_work'], r['reels_work'], R):
        for d, _, fs in os.walk(root) if os.path.isdir(root) else []:
            if os.path.realpath(d).startswith(os.path.realpath(f'{R}/cleanup')): continue
            for f in fs:
                p = os.path.join(d, f)
                if os.path.isfile(p) and os.path.getsize(p) >= LOCAL_MIN and not protected(p, r, keep, snap): local.append({'path': p, 'bytes': os.path.getsize(p), 'why': 'working file, not in any final'})
    rv = {'timelines': [], 'media': []}
    if listing:
        srcs = {os.path.realpath(c['path']) for c in (C.podcut_manifest(r) or {}).get('cameras', []) + (C.podcut_manifest(r) or {}).get('screens', [])}
        rv['timelines'] = [t['name'] for t in listing['timelines'] if not t['locked'] and not t['template']]
        rv['media'] = [m['path'] for m in listing['media'] if m.get('path') and not m['used'] and os.path.realpath(m['path']) not in srcs]
    man = {'at': C.now(), 'nas': nas, 'local': local, 'resolve': rv, 'notes': notes,
           'totals': {'nas_bytes': sum(x['bytes'] for x in nas), 'local_bytes': sum(x['bytes'] for x in local), 'nas_n': len(nas), 'local_n': len(local)}}
    man['sha'] = C.sha({k: man[k] for k in ('nas', 'local', 'resolve')})
    C.save(f'{R}/cleanup/manifest.json', man); C.event(R, f'CLEANUP SCAN {man["sha"]}')
    for x in nas: print(f'NAS DELETE  {gb(x["bytes"]):>9}  {x["path"]}  ({x["why"]})')
    for x in local: print(f'TO TRASH    {gb(x["bytes"]):>9}  {x["path"]}')
    for n in rv['timelines']: print(f'RESOLVE TL  {n}  (.drt backup first)')
    for p in rv['media']: print(f'RESOLVE POOL {p}')
    for n in notes: print(f'NOTE: {n}')
    t = man['totals']; print(f'\nNAS: {t["nas_n"]} items, {gb(t["nas_bytes"])} PERMANENT | local: {t["local_n"]} files, {gb(t["local_bytes"])} to the Trash | Resolve: {len(rv["timelines"])} timelines, {len(rv["media"])} pool clips  (sha {man["sha"]})')
    return man

def card(R):
    import tg, tg_plan
    r = C.run(R); man = C.load(f'{R}/cleanup/manifest.json') or C.fail('cleanup.py scan first'); t = man['totals']; rv = man['resolve']
    text = (f'CLEAN UP - {r["show_name"]} {r["ep_key"]}\nNAS: {t["nas_n"]} items, {gb(t["nas_bytes"])} - PERMANENT DELETE\n'
            f'Local: {t["local_n"]} files, {gb(t["local_bytes"])} -> Trash\nResolve: {len(rv["timelines"])} timelines (.drt backups in the Trash), {len(rv["media"])} unused pool clips\n'
            f'Kept: Final/, every delivered file, the camera files, everything a locked timeline uses. Full list: run/{r["show"]}/{r["ep_key"]}/cleanup/manifest.json'
            + (('\n' + '\n'.join('- ' + n for n in man['notes'])) if man['notes'] else ''))
    k = tg_plan.key(r); s8 = man['sha'][:8]
    m = tg.say(text, [[{'text': 'Clean up', 'callback_data': f'pa|{k}|cln|{s8}'}, {'text': 'Not now', 'callback_data': f'pa|{k}|clnno|{s8}'}]])
    r = C.run(R); r['cleanup_card'] = {'sha': man['sha'], 'message_id': m['message_id'], 'at': C.now()}; C.save_run(R, r); print(text)

def to_trash(p, trash, roots):
    rel = next((os.path.relpath(p, os.path.dirname(rt)) for rt in roots if os.path.realpath(p).startswith(os.path.realpath(rt))), os.path.basename(p))
    dest = os.path.join(trash, rel); os.makedirs(os.path.dirname(dest), exist_ok=True); shutil.move(p, dest); return dest

def apply(R, by=None):
    r = C.run(R); man = C.load(f'{R}/cleanup/manifest.json') or C.fail('cleanup.py scan first')
    ap = r.get('cleanup_approval') or {}
    if by:
        if len(by.strip()) < 3: C.fail('--by needs his words')
        ap = {'sha': man['sha'], 'by': by, 'at': C.now()}; r['cleanup_approval'] = ap; C.save_run(R, r)
    if ap.get('sha') != man['sha']: C.fail('this cleanup manifest is not approved - cleanup.py card (or --by "<his words>")')
    listing = C.load(f'{R}/cleanup/resolve.json')
    if man['resolve']['timelines'] or man['resolve']['media']:
        if not listing or C.hours_old(f'{R}/cleanup/resolve.json') > 6: C.fail('the Resolve listing is older than 6 h - scan again')
        listing = resolve_list(R, r)
    keep, snap = keep_set(r, listing)
    stamp = dt.datetime.now().strftime('%Y%m%d-%H%M%S'); trash = os.path.expanduser(f'~/.Trash/CWC_PodRun {r["show"]} {r["ep_key"]} {stamp}')
    done = {'at': C.now(), 'by': ap['by'], 'trash': trash, 'resolve': None, 'local': [], 'nas': [], 'skipped': []}
    if man['resolve']['timelines'] or man['resolve']['media']:
        m = C.podcut_manifest(r)['resolve']; srcs = [c['path'] for c in C.podcut_manifest(r).get('cameras', []) + C.podcut_manifest(r).get('screens', [])]
        out = subprocess.run([sys.executable, f'{C.SK}/scripts/rs.py', '900', f'{C.SK}/scripts/r_sweep.py', f'PROJECT={json.dumps(m["project"])}', f'STEP={json.dumps("apply")}',
                              f'BIN={json.dumps(m["bin"])}', f'DELETE_TL={json.dumps(man["resolve"]["timelines"])}', f'DELETE_MEDIA={json.dumps(man["resolve"]["media"])}',
                              f'BACKUP_DIR={json.dumps(trash + "/timelines")}', f'SOURCES={json.dumps(srcs)}'], capture_output=True, text=True).stdout.strip().splitlines()
        done['resolve'] = json.loads(out[-1]) if out else {'error': 'no answer from Resolve'}
        if done['resolve'].get('error'): C.save(f'{R}/cleanup/done.json', done); C.fail(f'Resolve sweep failed: {done["resolve"]["error"]} - disks untouched')
    roots = [r['podcut_cache'], r['clips_work'], r['reels_work'], R]
    for x in man['local']:
        p = x['path']
        if not os.path.exists(p) or protected(p, r, keep, snap): done['skipped'].append(p); continue
        done['local'].append([p, to_trash(p, trash, roots)])
    for x in man['nas']:
        p = x['path']
        if not os.path.exists(p) or protected(p, r, keep, snap): done['skipped'].append(p); continue
        shutil.rmtree(p) if os.path.isdir(p) else os.remove(p); done['nas'].append(p)
    C.save(f'{R}/cleanup/done.json', done); r = C.run(R); r.setdefault('stages', {})['cleanup'] = {'at': C.now(), 'sha': man['sha']}; C.save_run(R, r)
    C.event(R, f'CLEANUP APPLIED {man["sha"]}: NAS {len(done["nas"])} deleted, {len(done["local"])} to Trash, skipped {len(done["skipped"])}')
    print(f'NAS: {len(done["nas"])} deleted | local: {len(done["local"])} moved to {trash} | Resolve: {done["resolve"] or "nothing"} | skipped (changed since the scan): {len(done["skipped"])}')

def main():
    a = sys.argv[1:]
    if len(a) < 2: print(__doc__); sys.exit(1)
    cmd, R = a[0], a[1].rstrip('/')
    if cmd == 'scan': scan(R, '--no-resolve' in a)
    elif cmd == 'card': card(R)
    elif cmd == 'apply': apply(R, a[a.index('--by') + 1] if '--by' in a else None)
    elif cmd == 'status':
        d = C.load(f'{R}/cleanup/done.json'); m = C.load(f'{R}/cleanup/manifest.json')
        print(json.dumps({'manifest': m and {'sha': m['sha'], **m['totals']}, 'approval': C.run(R).get('cleanup_approval'), 'done': d and {k: (len(v) if isinstance(v, list) else v) for k, v in d.items()}}, indent=1))
    else: print(__doc__); sys.exit(1)

if __name__ == '__main__': main()
