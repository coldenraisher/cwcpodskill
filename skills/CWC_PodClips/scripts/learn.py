"""learn.py report                         -> data/learnings.md (read before scoring; channel_data.py summary appends it)
   learn.py link <WORK> <theme id> <cwc|tcl> <videoId>     tie a published clip to its theme (the edit / publish stage)
   learn.py seed-ep23                       one-off: the 8 Ep 23 clips edit-clips published (read-only) as history
The loop (Colden 2026-10-01: "Build all your hardening suggestions"):
  data/decisions.jsonl   every Approve / Kill / Notes on Telegram with the theme's attributes  (tg_themes.py writes it)
  data/published.jsonl   theme -> video id                                                     (link / seed-ep23)
  report joins both with data/channels/*/videos.json (views, 7-day views, % viewed, kept at 30 s, subs) so the next
  episode's scoring starts from what Colden approved and what the audience watched - not from a hunch."""
import os, sys, json, statistics
import common as C
def jl(p): return [json.loads(l) for l in open(p)] if os.path.exists(p) else []
def videos():
    out = {}
    for ch in ('cwc', 'tcl'):
        for v in (C.load(f'{C.DATA}/channels/{ch}/videos.json') or {}).get('videos', []): out[v['id']] = dict(v, channel=ch)
    return out
def report():
    dec = [d for d in jl(f'{C.DATA}/decisions.jsonl') if not d.get('trial')]; pub = jl(f'{C.DATA}/published.jsonl'); V = videos(); L = ['### Theme decisions (Telegram)']
    final = {}
    for d in dec:
        if d['decision'] in ('approved', 'approved-manual', 'killed'): final[(d['show'], d['ep'], d['theme'])] = d
    if not final: L.append('none yet')
    else:
        ap = [d for d in final.values() if d['decision'].startswith('approved')]; ki = [d for d in final.values() if d['decision'] == 'killed']
        L.append(f'{len(ap)} approved, {len(ki)} killed over {len({(d["show"], d["ep"]) for d in final.values()})} episode(s).')
        def avg(rows, f):
            x = [f(r) for r in rows if f(r) is not None]; return round(statistics.mean(x), 1) if x else 'n/a'
        for name, f in (('score', lambda d: d['attrs']['total']), ('minutes', lambda d: d['attrs']['est_seconds'] / 60), ('parts', lambda d: d['attrs']['ranges']), ('news share', lambda d: 100.0 * d['attrs']['news'])):
            L.append(f'- {name}: approved {avg(ap, f)} vs killed {avg(ki, f)}')
        for d in ap:
            if d['decision'] == 'approved-manual': L.append(f'- MANUAL OVERRIDE {d["ep"]} "{d["title"]}" (scored {d["attrs"]["total"]}, held by the gates, approved by Colden)')
        for d in ki: L.append(f'- KILLED {d["ep"]} "{d["title"]}" ({d["attrs"]["total"]})' + ''.join(f' - reason: {n["notes"]}' for n in dec if n['decision'] == 'kill-reason' and n['theme'] == d['theme'] and n['ep'] == d['ep']))
        for n in dec:
            if n['decision'] == 'notes': L.append(f'- NOTES {n["ep"]} "{n["title"]}": {n["notes"]}')
    ed = [d for d in dec if d.get('stage') in ('edit', 'package')]
    if ed:
        L += ['', '### What he said at the edit and the package (read before planning cuts, b-roll, titles and thumbnails)']
        for d in ed:
            if d['decision'] in ('changes', 'notes', 'note-after-approval', 'dropped') and d.get('notes'): L.append(f'- {d["stage"].upper()} {d["ep"]} {d.get("version", "")} "{d["title"][:50]}": {d["notes"]}')
        picks = [d['decision'] for d in ed if d['decision'].startswith('picked:')]
        if picks:
            kinds = {}
            for x in picks:
                k = x.split(':')[3] if x.count(':') >= 3 else 'thumb ' + x.split(':')[2][-1]; kinds[k] = kinds.get(k, 0) + 1
            L.append(f'- thumbnail picks so far (frame = real still, hook = still + overlay, ai-1 = GPT Image, ai-2 = Nano Banana): {kinds}; title option picked: ' + str({n: sum(1 for x in picks if x.split(":")[1] == f"title{n}") for n in (1, 2, 3)}))
        ch = {}
        for d in ed:
            if d['decision'].startswith('approved:'): ch[d['decision'].split(':')[1]] = ch.get(d['decision'].split(':')[1], 0) + 1
        if ch: L.append(f'- channel he chose at the edit: {ch}')
    L += ['', '### Published clips and what they did', '| ep | channel | title | len | views | 7d | % viewed | kept 30 s | subs | score | hook by | parts |', '|---|---|---|---|---|---|---|---|---|---|---|---|']
    for p in pub:
        v = V.get(p['video_id'])
        if not v: L.append(f'| {p["ep"]} | {p["channel"]} | {p.get("title", "")[:60]} | not in the channel data (private / removed / pull again) |||||||||'); continue
        lf = v.get('life', {}); a = p.get('attrs', {})
        L.append(f'| {p["ep"]} | {p["channel"]} | {v["title"][:60]} | {C.mmss(v["duration"])} | {lf.get("views", "")} | {v.get("first7", {}).get("views", "")} | {round(lf.get("averageViewPercentage", 0), 1)} | {v.get("retention", {}).get("kept_30s", "")} | {lf.get("subscribersGained", "")} | {a.get("total", "")} | {a.get("hook_who", "")} | {a.get("ranges", "")} |')
    if not pub: L.append('| none linked yet |||||||||||')
    open(f'{C.DATA}/learnings.md', 'w').write('\n'.join(L) + '\n'); print(f'{C.DATA}/learnings.md: {len(final)} decisions, {len(pub)} published clips')
if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    if cmd == 'report':
        report()
        import pack_learn as PL; PL.build()                # links uploads that went live + the packaging brief (ruling 44)
        import channel_data as CD; CD.summary()            # channel_summary.md carries the learnings: rewrite it NOW, or the next read sees the old ones
    elif cmd == 'link':
        W, tid, ch, vid = os.path.abspath(sys.argv[2]), sys.argv[3], sys.argv[4], sys.argv[5]; ck = C.load(f'{W}/checked.json'); r = ck['themes'][tid]
        row = {'at': C.now(), 'show': ck['episode']['show'], 'ep': ck['episode']['ep_key'], 'theme': tid, 'channel': ch, 'video_id': vid, 'title': r['title'],
               'attrs': {'total': r['total'], 'scores': r['scores'], 'est_seconds': r['est_seconds'], 'news': r['news'], 'ranges': r['ranges'], 'nonlinear': r['nonlinear'], 'hook_who': r['hook']['who'], 'speakers': r['speakers']}}
        if any(p['video_id'] == vid for p in jl(f'{C.DATA}/published.jsonl')): C.fail(f'{vid} is already linked')
        with open(f'{C.DATA}/published.jsonl', 'a') as f: f.write(json.dumps(row, ensure_ascii=False) + '\n')
        print('linked', vid)
    elif cmd == 'seed-ep23':
        src = os.path.expanduser('~/Documents/Claude/Projects/Create with Colden/Creative Lens Ep 23/clips-work'); up = C.load(f'{src}/review/uploads.json'); th = {f'{c["n"]:02d}': c for c in C.load(f'{src}/themes.json')['clips']}
        have = {p['video_id'] for p in jl(f'{C.DATA}/published.jsonl')}; n = 0; os.makedirs(C.DATA, exist_ok=True)
        with open(f'{C.DATA}/published.jsonl', 'a') as f:
            for key, rec in up.items():
                if key.startswith('_') or not rec.get('videoId') or rec['videoId'] in have: continue
                nn, ch = key.split('/'); c = th.get(nn, {})
                f.write(json.dumps({'at': C.now(), 'show': 'creative-lens', 'ep': 'Ep23', 'theme': f'edit-clips {nn}', 'channel': ch, 'video_id': rec['videoId'], 'title': c.get('title'),
                                    'attrs': {'hook_who': (c.get('hook') or {}).get('who'), 'ranges': len(c.get('beats', [])), 'source': 'edit-clips Ep 23 (made before this skill; no rubric score)'}}, ensure_ascii=False) + '\n'); n += 1
        print(f'seeded {n} Ep 23 clips'); report()
    else: C.fail(__doc__)
