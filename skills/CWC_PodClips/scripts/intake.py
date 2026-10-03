"""intake.py "<PodCut CACHE dir>" [--trial "<why>"] [--no-notes "<Colden's words>"]
The hand-off from CWC_PodCut: reads the LOCKED cut's snapshot (plan.json, words.json, layout.json, lower_thirds.json)
and writes this skill's work folder  clips/<show>/<EpNN>/ :
  episode.json     what was read (show, cut, project, bin, people, plan hash, specials, screen files, show notes)
  phrases.json     every sentence / phrase on the CUT clock, in time order, with an id (P0001...) - the unit themes are
                   written in, so a range can never start or end inside a word or a thought (+ its words `w`:
                   [text, start, end], the unit of the edit's trims)
  transcript.txt   the same, readable:  P0123 12:34.5 Nick: ...   (+ lines where the program shows a screen share)
  show_notes.txt   the show notes found in the episode's main folder (context only - the transcript is the truth)
Nothing in CWC_PodCut's cache is written. GATES: the episode is locked and not re-opened (exit 2 otherwise; --trial
reads the last lock snapshot for a test and marks the work TRIAL); the snapshot holds plan + words; every speaker has
words; show notes exist in the main folder (exit 2 - Colden saves them each time - unless --no-notes "<his words>")."""
import os, re, sys, glob, subprocess
import common as C

def flag(name):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else None

def phrases_of(words, who, cm, fix):
    """one speaker's words (BASE clock) -> phrases on the CUT clock. A phrase ends on sentence punctuation, on a pause
    of >= 0.6 s, where the plan removed something between two words, or - for a run-on - at its longest pause once it
    passes 25 s."""
    out = []; cur = []
    def flush():
        if cur: out.append(list(cur)); cur.clear()
    prev = None
    for w in words:
        mid = (w['start'] + w['end']) / 2; c0 = cm.to_cut(mid)
        if c0 is None: continue                                  # removed by the PodCut (um / dead air / repeat) or outside it
        cs = cm.to_cut(w['start']); ce = cm.to_cut(w['end'])
        cs = c0 - (mid - w['start']) if cs is None else cs; ce = c0 + (w['end'] - mid) if ce is None else ce
        t = w['text'].strip()
        if not t: continue
        low = re.sub(r"[^a-z']", '', t.lower())
        if low in fix: t = re.sub(r"[A-Za-z']+", fix[low], t, count=1)
        item = {'t': t, 'cs': round(cs, 3), 'ce': round(ce, 3), 'bs': w['start'], 'be': w['end'], 'p': w.get('p', 1.0)}
        if prev is not None and (item['bs'] - prev['be'] >= 0.6 or abs((item['cs'] - prev['ce']) - (item['bs'] - prev['be'])) > 0.05): flush()
        cur.append(item); prev = item
        if re.search(r'[.?!]["\')]?$', t): flush()
    flush()
    final = []
    for ph in out:                                                # split run-ons at their longest pause
        stack = [ph]
        while stack:
            p = stack.pop()
            if p[-1]['ce'] - p[0]['cs'] > 25 and len(p) > 8:
                k = max(range(4, len(p) - 3), key=lambda i: p[i]['cs'] - p[i - 1]['ce'])
                stack.append(p[k:]); stack.append(p[:k])
            else: final.append(p)
    return [{'who': who, 'start': p[0]['cs'], 'end': p[-1]['ce'], 'b0': round(p[0]['bs'], 3), 'b1': round(p[-1]['be'], 3),
             'text': ' '.join(x['t'] for x in p), 'n': len(p), 'p_min': round(min(x['p'] for x in p), 2),
             'w': [[x['t'], x['cs'], x['ce']] for x in p]} for p in final]            # the words, for word-level trims in the edit

def notes_text(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in ('.txt', '.md'): return open(path, errors='replace').read()
    if ext in ('.docx', '.doc', '.rtf', '.rtfd', '.odt', '.html'):
        r = subprocess.run(['textutil', '-convert', 'txt', '-stdout', path], capture_output=True, text=True); return r.stdout if r.returncode == 0 else None
    if ext == '.pdf':
        r = subprocess.run(['pdftotext', '-layout', path, '-'], capture_output=True, text=True); return r.stdout if r.returncode == 0 else None
    return None

if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    for f in ('--trial', '--no-notes'):
        v = flag(f)
        if v in args: args.remove(v)
    if not args: C.fail(__doc__)
    cache = os.path.abspath(args[0]); m = C.load(f'{cache}/manifest.json')
    if not m: C.fail(f'no manifest.json in {cache} - that is not a CWC_PodCut cache')
    trial = flag('--trial'); L = m.get('locked')
    if not L: C.ask(f'{m.get("ep_key")} has no locked PodCut. This skill runs only after the lock (Colden 2026-10-01).')
    if m.get('rebuild') and not trial:
        C.ask(f'{m["ep_key"]} was re-opened for a new version ("{m["rebuild"].get("by")}") and is not locked again yet. '
              f'Wait for the new lock, or run with --trial "<why>" to test on the last locked snapshot ({L["timeline"]}).')
    snap = L['snapshot']
    for f in ('plan.json', 'words.json', 'pod_dump.json'):          # pod_dump: the PodCut's timeline items - the EDIT builds every piece from it
        if not os.path.exists(f'{snap}/{f}'): C.fail(f'the lock snapshot {snap} has no {f}' + (' - lock the PodCut again with the current CWC_PodCut (its lock writes it)' if f == 'pod_dump.json' else ''))
    S = C.show(m['show'])
    if S.get('first_run_ask') and not trial:
        C.ask(f'{S["name"]} has never been run through this skill - these must be answered by Colden first (then written into shows/{S["id"]}.json and `first_run_ask` emptied):\n  - ' + '\n  - '.join(S['first_run_ask']))
    if not S.get('packaging') and not trial: C.ask(f'shows/{S["id"]}.json has no `packaging` block (channels, handles, playlists, footer, thumbnail rules) - ask Colden, write it like shows/creative-lens.json')
    S = S; plan = C.load(f'{snap}/plan.json'); words = C.load(f'{snap}/words.json'); cm = C.CutMap(plan)
    fix = {k.lower(): v for k, v in S.get('spellings', {}).items()}
    people = [{'id': c['id'], 'name': c['name'], 'host': bool(c.get('host'))} for c in m['cameras'] if c['role'] == 'speaker']
    lt = C.load(f'{snap}/lower_thirds.json', {}) or {}
    for p in people:
        g = (lt.get('guests') or {}).get(p['name'])
        if g: p.update({'full_name': g.get('name'), 'handle': g.get('handle')})
    ph = []
    for p in people:
        w = words.get(p['id'])
        if not w: C.fail(f'no words for {p["name"]} ({p["id"]}) in the lock snapshot')
        ph += phrases_of(w, p['name'], cm, fix)
    ph.sort(key=lambda x: (x['start'], x['end']))
    for i, x in enumerate(ph): x['id'] = f'P{i + 1:04d}'
    if len(ph) < 50: C.fail(f'only {len(ph)} phrases - the transcript does not cover the cut')
    covered = C.union_len([[x['start'], x['end']] for x in ph]) / cm.duration
    if covered < 0.5: C.fail(f'words cover only {covered:.0%} of the cut - transcript or plan mismatch')

    lay = C.load(f'{snap}/layout.json', {}) or {}; specials = []
    for a, b in lay.get('special', []):
        ca = next((cm.to_cut(t) for t in (a, a + 0.5, a + 1, a + 2) if cm.to_cut(t) is not None), None)
        cb = next((cm.to_cut(t) for t in (b, b - 0.5, b - 1, b - 2) if cm.to_cut(t) is not None), None)
        if ca is not None and cb is not None and cb - ca >= 5.0: specials.append({'start': round(ca, 2), 'end': round(cb, 2), 'base': [a, b]})
    ep_dir = m['dir']; screens = [s['path'] for s in m.get('screens', [])]
    if os.path.isdir(ep_dir):
        for f in sorted(glob.glob(f'{ep_dir}/**/*', recursive=True)):
            if re.search(r'screen|share', os.path.basename(f), re.I) and f.lower().endswith(('.mp4', '.mov', '.mkv')) and f not in screens: screens.append(f)

    work = C.work_dir(m['show'], m['ep_key']); os.makedirs(work, exist_ok=True)
    notes = []; no_notes = flag('--no-notes')
    if os.path.isdir(ep_dir):
        for f in sorted(os.listdir(ep_dir)):
            if f.startswith('.') or not f.lower().endswith(('.txt', '.md', '.docx', '.doc', '.rtf', '.pdf', '.odt', '.pages')): continue
            t = notes_text(f'{ep_dir}/{f}')
            if t is None: C.ask(f'cannot read "{f}" in {ep_dir} (a .pages file? export it as .docx or .pdf)')
            notes.append({'file': f'{ep_dir}/{f}', 'chars': len(t)}); open(f'{work}/show_notes.txt', 'a' if len(notes) > 1 else 'w').write(f'===== {f} =====\n{t.strip()}\n\n')
    elif not no_notes: C.ask(f'the episode folder {ep_dir} is not mounted - mount the NAS (show notes and screen recordings live there)')
    if not notes and not no_notes:
        C.ask(f'no show notes (.docx / .pdf / .txt / .md) in the main folder {ep_dir}. Colden saves them there each time; '
              f'if this episode has none, re-run with --no-notes "<his words>".')

    ep = {'show': m['show'], 'show_name': S['name'], 'ep_key': m['ep_key'], 'ep_no': m.get('ep_no'), 'episode': m.get('episode'), 'dir': ep_dir,
          'podcut_cache': cache, 'snapshot': snap, 'cut': L['timeline'], 'project': L.get('project'), 'bin': L.get('bin'), 'locked_by': L.get('by'),
          'plan_sha': C.sha_file(f'{snap}/plan.json'), 'fps': plan.get('fps'), 'duration': round(cm.duration, 2), 'people': people,
          'specials': specials, 'screens': screens, 'notes': notes, 'no_notes': no_notes, 'trial': trial, 'intake_at': C.now(), 'rules': C.RULES,
          'phrases': len(ph)}
    C.save(f'{work}/episode.json', ep); C.save(f'{work}/phrases.json', ph)
    lines = [f'# {S["name"]} {m["ep_key"]} - {L["timeline"]} - {C.hms(cm.duration)} - timecodes are the locked PodCut timeline',
             f'# people: ' + ', '.join(f'{p["name"]}{" (host)" if p["host"] else " (guest" + (": " + p["full_name"] + " " + (p.get("handle") or "") if p.get("full_name") else "") + ")"}' for p in people)]
    marks = sorted([(s['start'], f'--- SCREEN SHARE / SPECIAL PROGRAM LAYOUT ON from {C.hms(s["start"])} to {C.hms(s["end"])} ({s["end"] - s["start"]:.0f} s) ---') for s in specials])
    for x in ph:
        while marks and marks[0][0] <= x['start']: lines.append(marks.pop(0)[1])
        lines.append(f'{x["id"]} {C.hms(x["start"])} {x["who"]}: {x["text"]}')
    open(f'{work}/transcript.txt', 'w').write('\n'.join(lines) + '\n')
    share = {p['name']: round(100 * sum(x['n'] for x in ph if x['who'] == p['name']) / sum(x['n'] for x in ph)) for p in people}
    print(f'{"TRIAL " if trial else ""}intake {m["show"]} {m["ep_key"]}: {L["timeline"]} ({C.hms(cm.duration)}), {len(ph)} phrases, words cover {covered:.0%} of the cut')
    print(f'  words by speaker: {share}   specials >= 5 s: {len(specials)}   screen files: {len(screens)}   show notes: {[os.path.basename(n["file"]) for n in notes] or "NONE (--no-notes)"}')
    print(f'  work: {work}')
