"""postcopy.py - the posting copy of every approved short: the six fields Metricool publishes (edit-shorts references/copy.md,
Colden 2026-09-13), one record per short in WORK/copy.json.
  postcopy.py scaffold <WORK>     the mechanical part, from the approved edit: destination (his tap), the brands it posts to,
                              playlist per brand (show default), ig_collab (the guest's Instagram when the guest speaks -
                              Create with Colden post only). Re-run is safe: written text is kept.
  -> Claude writes, per short: caption, first_comment, yt_title, fb_title (rules below), then:
  postcopy.py check <WORK>        THE GATES (exit 1 on any): caption = 1-3 sentences, the hook in the first four words, then
                              exactly 5 hashtags on their own last line, no link, <= 2200 chars; first_comment = an
                              engagement QUESTION (ends with "?"), <= 2 sentences, never a plug / link / "full episode",
                              no CTA filler ("drop it below", "comment below", "let me know"); yt_title <= 100 chars
                              (TikTok gets its first 90), fb_title only when Create with Colden posts it; no em dashes
                              anywhere; playlist slugs exist on that channel; claims only from the short itself;
                              PACKAGING FROM DATA (Colden 2026-10-02): copy.json names the current data/shorts/
                              packaging_brief ("brief"), each short has "learned" (2+ brief pattern ids + how), yt_title
                              or the caption's first sentence carries a WIN pattern, a LOSE pattern only as "explore".
  postcopy.py show <WORK>         every short's copy, for reading and for the batch card
Brand voice (cwc and tcl): direct, high-signal, no hype, no em dashes. Hashtags: the topic first (the named camera /
film / person), then the craft (#filmmaking #cinematography ...), then the show (#thecreativelens) - 5 total."""
import os, re, sys, json
import common as C, pack_learn as PL
FILLER = ('drop it below', 'comment below', 'let me know', 'full episode', 'link in bio', 'watch the full', 'subscribe')
def path(W): return f'{W}/copy.json'
def approved_shorts(W):
    out = []
    for th in C.load(f'{W}/themes.json')['themes']:
        vs = C.load(f'{W}/edit/{th["id"]}/versions.json', []) or []; v = next((x for x in reversed(vs) if x.get('status') == 'approved'), None)
        if v: out.append((th, v))
    return out
def brands(dest): return {'cwc': ['cwc'], 'tcl': ['tcl'], 'both': ['cwc', 'tcl'], 'todd': []}.get(dest, [])

def scaffold(W):
    ep = C.episode(W); S = C.show(ep['show']); pub = S['publishing']; mc = pub['metricool']; collabs = {k.lower(): v for k, v in pub.get('ig_collaborators', {}).items() if not k.endswith('note')}
    cp = C.load(path(W), {'shorts': {}}) or {'shorts': {}}
    for th, v in approved_shorts(W):
        P = C.load(v['plan']); dest = v.get('destination') or th.get('dest'); bs = brands(dest)
        guest = next((t['who'] for t in P.get('tags', [])), None)
        cur = cp['shorts'].get(th['id'], {})
        cp['shorts'][th['id']] = {'title': th['title'], 'hook_text': th.get('hook_text'), 'version': v['v'], 'destination': dest, 'brands': bs,
            'caption': cur.get('caption', ''), 'first_comment': cur.get('first_comment', ''), 'yt_title': cur.get('yt_title', ''), 'fb_title': cur.get('fb_title', '') if 'cwc' in bs else '',
            'playlist': cur.get('playlist') or {b: mc[b].get('default_playlist', 'tcl_shorts') for b in bs},
            'ig_collab': cur.get('ig_collab') or (collabs.get(guest.lower(), 'ASK') if guest and 'cwc' in pub.get('ig_collab_brands', ['cwc']) and 'cwc' in bs else 'none'),
            'status': cur.get('status', 'draft'), 'learned': cur.get('learned', []), 'explore': cur.get('explore', {})}
    cp.setdefault('brief', PL.current().get('id') if cur_brief_read(cp) else None); C.save(path(W), cp); todo = [k for k, c in cp['shorts'].items() if not (c['caption'] and c['first_comment'] and c['yt_title'])]
    print(f'{path(W)}: {len(cp["shorts"])} approved shorts | still need copy: {", ".join(todo) or "none"}')

def cur_brief_read(cp): return cp.get('brief') == PL.current().get('id')        # scaffold never claims the brief was read: Claude sets "brief" after reading it
def sentences(t): return [s for s in re.split(r'(?<=[.!?])\s+', t.strip()) if s]
def check(W):
    ep = C.episode(W); S = C.show(ep['show']); mc = S['publishing']['metricool']; cp = C.load(path(W)) or C.fail('no copy.json - postcopy.py scaffold first'); bad = []
    bad += PL.brief_ok(cp, 'copy.json')
    for sid, c in cp['shorts'].items():
        e = lambda m: bad.append(f'{sid}: {m}')
        if not c['brands']: continue                                   # Todd-only: exported, never posted
        bad += PL.problems(c, sid, {'yt_title': c.get('yt_title', ''), 'caption_hook': PL.first_sentence(c.get('caption', ''))})
        for k in ('caption', 'first_comment', 'yt_title'):
            if not c.get(k): e(f'{k} is empty')
        for k in ('caption', 'first_comment', 'yt_title', 'fb_title'):
            if '—' in (c.get(k) or '') or '–' in (c.get(k) or ''): e(f'{k} has an em / en dash')
        cap = c.get('caption', ''); lines = [l for l in cap.strip().split('\n') if l.strip()]
        if lines:
            tags = re.findall(r'#\w+', lines[-1]); body = '\n'.join(lines[:-1])
            if len(tags) != 5 or re.sub(r'#\w+|\s', '', lines[-1]): e(f'caption: the last line must be exactly 5 hashtags and nothing else ({lines[-1]!r})')
            if '#' in body: e('caption: hashtags only on the last line')
            if not 1 <= len(sentences(body)) <= 3: e(f'caption: 1-3 sentences, has {len(sentences(body))}')
            if re.search(r'https?://|www\.|\.com\b', cap, re.I): e('caption has a link')
            if len(cap) > 2200: e(f'caption is {len(cap)} chars (2200 max)')
        fc = c.get('first_comment', '')
        if fc:
            if not fc.rstrip().endswith('?'): e('first_comment must end on the question')
            if len(sentences(fc)) > 2: e('first_comment: two sentences max')
            if any(f in fc.lower() for f in FILLER) or re.search(r'https?://|www\.', fc): e(f'first_comment has a plug / link / filler: {fc!r}')
        if len(c.get('yt_title', '')) > 100: e(f'yt_title is {len(c["yt_title"])} chars (100 max)')
        if c.get('fb_title') and 'cwc' not in c['brands']: e('fb_title on a short Create with Colden does not post (TCL has no Facebook page)')
        if 'cwc' in c['brands'] and not c.get('fb_title'): e('fb_title is empty (Create with Colden posts to Facebook)')
        for b, slug in (c.get('playlist') or {}).items():
            if slug not in mc[b]['playlists']: e(f'playlist {slug!r} does not exist on {b}')
        if c.get('ig_collab') == 'ASK': e('the guest speaks but has no Instagram handle in the show file (ig_collaborators) - ask Colden')
    if bad: print('COPY GATES FAILED:'); [print('  ', b) for b in bad]; sys.exit(1)
    print(f'copy OK: {sum(1 for c in cp["shorts"].values() if c["brands"])} shorts')

def show(W):
    cp = C.load(path(W)) or C.fail('no copy.json')
    for sid, c in cp['shorts'].items():
        print(f'\n== {sid.upper()} {c["title"]}  -> {", ".join(c["brands"]) or "Todd only (export)"}\nYT: {c["yt_title"]}' + (f'\nFB: {c["fb_title"]}' if c.get('fb_title') else '') +
              f'\n{c["caption"]}\n1st comment: {c["first_comment"]}\nplaylist: {c["playlist"]}  ig collab: {c["ig_collab"]}')

if __name__ == '__main__':
    a = sys.argv[1:]
    if len(a) < 2: C.fail(__doc__)
    W = os.path.abspath(a[1]); {'scaffold': scaffold, 'check': check, 'show': show}.get(a[0], lambda W: C.fail(__doc__))(W)
