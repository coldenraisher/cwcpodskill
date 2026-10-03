"""deliver.py <WORK> [--dry-run]      the FINAL step of the skill: the finished uploads go to the NAS, the Mac is cleaned.
Colden 2026-10-02 (ruling 43): "the final renders are still living on disk not NAS... In NAS under the episode folder,
final files should be in sub folder "Final" then sub folder "Clips". Each final with locked A YouTube title as the file
name. And dashboard built for clips." ... "I think it should be the final steps here".
`package.py build` runs it by itself once delivery.json is complete; run it by hand after a fix, or with --dry-run to
read what it will do.

  <episode>/Final/Clips/<title A>.mp4                         the master of every upload (a clip on both channels = two
                                                             files, each named by ITS channel's title A)
  <episode>/Final/Clips/Thumbnails/<title A> - A|B|C.<ext>     the approved Test & Compare thumbnails
  <episode>/Final/Clips/Captions/<title A>.srt                 the caption file
  <episode>/Final/Clips/Ep NN Clips Dashboard.html             everything needed to post, with copy buttons
File names: title A exactly, minus the characters the NAS (SMB) refuses: \\ / : * ? " < > |  (like AMIRA's Final files).
GATES  NAS mounted (exit 2 otherwise); delivery.json complete and current (package.py build); no two uploads with the same
       file name; every copy is verified (size + SHA-256) before anything is repointed or moved; a file already there
       with other content (a fix after delivery) goes to the share's #recycle first, never overwritten in place; files of
       an earlier delivery that are no longer part of it go to #recycle too.
THEN   every record that pointed at a local file (versions.json, lock.json, facts / thumbs / package json, delivery.json)
       is repointed to the NAS copy, and the local copies go to ~/.Trash (masters, the thumbnail folders with every
       option / sheet / reference, the .srt files) - Colden empties the Trash himself. KEPT on the Mac: the small JSON /
       text records (the decision log, the learning loop, next.py and a fix after the lock read them).
Telegram: one line when it is done."""
import os, re, sys, json, time, shutil, hashlib, base64, io, html
import common as C
BAD = re.compile(r'[\\/:*?"<>|]')
TRASH = os.environ.get('CWC_TRASH') or os.path.expanduser('~/.Trash')        # the self-test points this elsewhere

def fname(title):
    n = re.sub(r'\s+', ' ', BAD.sub('', title)).strip().rstrip('.').strip()
    if not n: C.fail(f'title "{title}" has no usable characters for a file name')
    return n

def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(8 << 20), b''): h.update(b)
    return h.hexdigest()

def same(a, b): return os.path.exists(a) and os.path.exists(b) and os.path.getsize(a) == os.path.getsize(b) and sha(a) == sha(b)

def recycle(path, stamp):
    """NAS file -> the share's #recycle (the NAS has no Trash); never deleted"""
    m = re.match(r'^(/Volumes/[^/]+)/', path)
    base = f'{m.group(1)}/#recycle/CWC_PodClips/deliver {stamp}' if m and os.path.isdir(f'{m.group(1)}/#recycle') else f'{TRASH}/CWC_PodClips deliver {stamp}'
    dest = f'{base}/{os.path.basename(path)}'; os.makedirs(base, exist_ok=True); shutil.move(path, dest); return dest

def copy(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True); tmp = dst + '.partial'
    shutil.copyfile(src, tmp)
    if os.path.getsize(tmp) != os.path.getsize(src) or sha(tmp) != sha(src): os.remove(tmp); C.fail(f'the copy of {src} to the NAS does not match the original - nothing was moved; check the share and run again')
    os.replace(tmp, dst)

def swap(o, mp):
    if isinstance(o, str): return mp.get(o, o)
    if isinstance(o, list): return [swap(x, mp) for x in o]
    if isinstance(o, dict): return {k: swap(v, mp) for k, v in o.items()}
    return o

def plan(W):
    D = C.load(f'{W}/delivery.json'); L = C.load(f'{W}/lock.json'); ep = C.episode(W)
    if not D or D.get('version', 1) < 2: C.fail('no delivery.json version 2 - package.py build first')
    if not L or sorted((c['theme'], c['channel']) for c in L['clips']) != sorted((c['theme'], c['channel']) for c in D['clips']): C.fail('delivery.json does not cover the uploads of lock.json - package.py build again')
    if not os.path.isdir(ep['dir']): C.ask(f'the NAS episode folder is not reachable: {ep["dir"]} - mount the share, then run deliver.py again')
    final = f'{ep["dir"]}/Final/Clips'; names = {}; jobs = []
    for c in D['clips']:
        n = fname(c['titles']['A']); k = f'{c["theme"]} {c["channel"]}'
        if n.lower() in names: C.fail(f'{k} and {names[n.lower()]} would both be "{n}.mp4" - give one of them another title A (package cards) and build again')
        names[n.lower()] = k
        jobs.append((c, 'master', c['master'], f'{final}/{n}.mp4'))
        for x in 'ABC': jobs.append((c, f'thumbnail {x}', c['thumbnails'][x], f'{final}/Thumbnails/{n} - {x}{os.path.splitext(c["thumbnails"][x])[1].lower()}'))
        jobs.append((c, 'captions', c['captions'], f'{final}/Captions/{n}.srt'))
    for c, what, src, dst in jobs:
        if not os.path.exists(src): C.fail(f'{c["theme"]} {c["channel"]}: the {what} is not on disk ({src}) - package.py build again (a moved file is restored from the Trash, never re-made by guess)')
    return D, ep, final, jobs

def main(W, dry):
    D, ep, final, jobs = plan(W); prev = C.load(f'{W}/delivered.json') or {}
    keep = {dst for _, _, _, dst in jobs}; dash = f'{final}/Ep {ep.get("ep_no") or ep["ep_key"]} Clips Dashboard.html'
    old = [f for f in prev.get('files', []) if f not in keep and f != dash and os.path.exists(f)]
    print(f'DELIVER to {final}:')
    for c, what, src, dst in jobs: print(f'  {c["theme"]} {c["channel"]} {what:12s} -> {os.path.relpath(dst, final)}' + ('   (already there)' if os.path.realpath(src) == os.path.realpath(dst) else ''))
    if old: print(f'  no longer part of the delivery -> #recycle: {[os.path.basename(f) for f in old]}')
    if dry: print('\ndry run - nothing was copied or moved'); return 0
    stamp = time.strftime('%Y%m%d-%H%M%S'); mp = {}; recycled = []
    for c, what, src, dst in jobs:                          # 1. copy + verify (nothing local is touched yet)
        if os.path.realpath(src) == os.path.realpath(dst): continue
        if os.path.exists(dst) and not same(src, dst): recycled.append(recycle(dst, stamp))
        if not os.path.exists(dst): copy(src, dst)
        mp[src] = dst
    for f in old: recycled.append(recycle(f, stamp))
    # 2. repoint every record (same content, new place: the approval hashes stay valid)
    recs = [f'{W}/delivery.json', f'{W}/lock.json'] + [f'{W}/edit/{d}/versions.json' for d in os.listdir(f'{W}/edit') if os.path.exists(f'{W}/edit/{d}/versions.json')]
    for c in D['clips']:
        d = f'{W}/package/{c["theme"]}'; recs += [f'{d}/facts.{c["channel"]}.json', f'{d}/thumbs.{c["channel"]}.json', f'{d}/package.{c["channel"]}.json']
    if mp:
        for r in recs:
            if os.path.exists(r): C.update(r, lambda o: o.update(swap(dict(o), mp)) if isinstance(o, dict) else o.__setitem__(slice(None), swap(list(o), mp)))
    D = C.load(f'{W}/delivery.json')
    # 3. the dashboard
    os.makedirs(final, exist_ok=True); open(dash, 'w').write(dashboard(D, ep, final))
    D.update(final_dir=final, dashboard=dash, delivered_at=C.now()); C.save(f'{W}/delivery.json', D)
    # 4. the Mac: what was copied, the thumbnail work folders, the srt files -> ~/.Trash (kept: the JSON / text records)
    trash = f'{TRASH}/CWC_PodClips {ep["show"]} {ep["ep_key"]} delivered {stamp}'; moved = []
    local = [s for s in mp if s.startswith(W + '/')]
    local += [f'{W}/package/{t}/thumbs' for t in sorted({c['theme'] for c in D['clips']})]
    local += [f'{W}/edit/{t}/master' for t in sorted({c['theme'] for c in D['clips']})]
    local = [p for p in dict.fromkeys(local) if not any(p != q and p.startswith(q + '/') for q in local)]     # a file inside a folder that moves anyway
    for p in local:
        if os.path.exists(p) and not os.path.realpath(p).startswith(os.path.realpath(final)):
            dest = f'{trash}/{os.path.relpath(p, W)}'
            while os.path.exists(dest): dest += ' (2)'
            os.makedirs(os.path.dirname(dest), exist_ok=True); shutil.move(p, dest); moved.append([p, dest])
    big = [os.path.relpath(os.path.join(r, f), W) for r, _, fs in os.walk(W) for f in fs if os.path.getsize(os.path.join(r, f)) > 5e6]
    rec = {'at': C.now(), 'final_dir': final, 'dashboard': dash, 'files': sorted(keep), 'copied': len(mp), 'recycled_on_nas': recycled,
           'local_to_trash': moved, 'trash': trash if moved else None, 'large_files_left_on_mac': big,
           'history': prev.get('history', []) + ([{k: prev[k] for k in ('at', 'copied', 'recycled_on_nas') if k in prev}] if prev else [])}
    C.save(f'{W}/delivered.json', rec)
    print(f'\nDELIVERED {len(D["clips"])} uploads to {final} ({len(mp)} file(s) copied and verified); dashboard: {os.path.basename(dash)}')
    print(f'Mac: {len(moved)} item(s) moved to {trash}' if moved else 'Mac: nothing left to move')
    if recycled: print(f'NAS #recycle: {len(recycled)} replaced / retired file(s)')
    if big: print(f'NOTE large files still in WORK: {big}')
    if not mp and not recycled: return 0                    # a re-run that only rebuilt the dashboard: no new message
    try:
        import tg_themes as G
        G.api('sendMessage', chat_id=G.chat(), text=f'📦 {ep.get("show_name", ep["show"])} {ep["ep_key"]} clips delivered: {len(D["clips"])} files in Final/Clips + {os.path.basename(dash)}.' + (f'\nLocal copies are in the Trash.' if moved else ''))
    except Exception as e: print('telegram note not sent:', str(e)[:100])
    return 0

# ---------------------------------------------------------------- the dashboard
CH = {'cwc': '@ColdenRaisher', 'tcl': 'The Creative Lens'}
def esc(s): return html.escape(str(s if s is not None else ''))
def when(iso):
    try: import datetime; return datetime.datetime.fromisoformat(iso).strftime('%b %-d, %Y %-I:%M %p')
    except Exception: return iso or ''
def eplabel(ep): return f'Ep {ep["ep_no"]}' if ep.get('ep_no') else ep['ep_key']
def img64(p):
    try:
        from PIL import Image
        im = Image.open(p).convert('RGB'); im.thumbnail((640, 360)); b = io.BytesIO(); im.save(b, 'JPEG', quality=82); return base64.b64encode(b.getvalue()).decode()
    except Exception: return ''
def field(label, text, cid, mono=False):
    return (f'<div class="field"><div class="fh"><span>{esc(label)}</span><button class="cp" data-c="{cid}">Copy</button></div>'
            f'<pre id="{cid}" class="{"mono" if mono else ""}">{esc(text)}</pre></div>')

def dashboard(D, ep, final):
    rel = lambda p: esc(os.path.relpath(p, final))
    tabs = ['<button class="tab" data-t="ep">Episode</button>']; panels = []
    rows = ''.join(f'<tr><td>{c["push_order"]}</td><td>{esc(CH.get(c["channel"], c["channel"]))}</td><td><a href="{rel(c["master"])}">{esc(c["titles"]["A"])}</a></td><td>{C.mmss(c["seconds"])}</td><td>{"yes" if c.get("news") else ""}</td></tr>' for c in D['clips'])
    R = D.get('rules_for_the_plan') or {}
    fe = ''.join(f'<li>{esc(CH.get(k, k))}: ' + (f'<a href="{esc(v["url"])}">{esc(v["url"])}</a> {esc(v.get("title"))}' if v.get('url') else f'not public yet - {esc(v.get("why"))}') + '</li>' for k, v in (D.get('full_episode') or {}).items())
    needs = [f'{c["theme"]} {c["channel"]}: {", ".join(c["needs"])}' for c in D['clips'] if c.get('needs')]
    panels.append(f'''<section class="panel" id="p-ep"><h2>{esc(ep.get("show_name"))} {esc(eplabel(ep))} - {len(D["clips"])} clip uploads</h2>
<p class="meta">Locked {esc(when(D.get("lock_at")))} &middot; delivered {esc(when(D.get("delivered_at") or C.now()))} &middot; files in this folder</p>
<table><tr><th>Push</th><th>Channel</th><th>Title A (file)</th><th>Length</th><th>News</th></tr>{rows}</table>
<h3>Full episode</h3><ul>{fe}</ul>
<h3>Posting rules (the aggregator plans; one approval)</h3><ul>
<li>{esc(CH.get(R.get("primary_channel_first"), R.get("primary_channel_first")))} first; the other channel at least {esc(R.get("secondary_min_delay_hours"))} h later</li>
<li>News first, then push order; one long-form per channel per day; clips around {esc(R.get("clips_around"))}; no premieres</li>
<li>Each master only on its own channel (the stinger is the channel's); end screens link public videos only</li></ul>
{"<h3>Still open</h3><ul>" + "".join(f"<li>{esc(x)}</li>" for x in needs) + "</ul>" if needs else ""}</section>''')
    for i, c in enumerate(D['clips']):
        k = f'u{i}'; tabs.append(f'<button class="tab" data-t="{k}">{c["push_order"]}. C{esc(c["theme"][1:])} {esc(c["channel"].upper())}</button>')
        th = ''.join(f'<figure><img src="data:image/jpeg;base64,{img64(c["thumbnails"][x])}" alt="thumbnail {x}"><figcaption><b>{x}</b> {esc((c.get("thumbnail_meta") or {}).get(x, {}).get("kind"))} &middot; <a href="{rel(c["thumbnails"][x])}">file</a></figcaption></figure>' for x in 'ABC')
        tit = ''.join(field(f'Title {x}' + (' (upload title)' if x == 'A' else ' (Test & Compare)'), c['titles'][x], f'{k}t{x}') for x in 'ABC')
        chap = '\n'.join(f'{C.stamp(x["t"])} {x["text"]}' for x in c['chapters'])
        pl = ', '.join(f'{p["title"]}' for p in c['playlists']) or 'none'
        fl = c.get('flags') or {}
        claims = ''.join(f'<li><b>{esc(x.get("status"))}</b> {esc(x.get("claim"))} <span class="src">{esc(x.get("source"))}</span></li>' for x in c.get('claims_checked') or [])
        lo = c.get('loudness') or {}
        panels.append(f'''<section class="panel" id="p-{k}"><h2>{esc(c["titles"]["A"])}</h2>
<p class="meta"><span class="badge {esc(c["channel"])}">{esc(CH.get(c["channel"], c["channel"]))}</span> push {c["push_order"]} &middot; {C.mmss(c["seconds"])}{" &middot; mid-roll possible" if c.get("midroll_possible") else ""}
&middot; {esc("x".join(map(str, c.get("resolution") or [])))} &middot; {esc(lo.get("lufs"))} LUFS, peak {esc(lo.get("true_peak"))} dBTP
&middot; <a href="{rel(c["master"])}">video file</a> &middot; <a href="{rel(c["captions"])}">captions (.srt)</a></p>
<div class="thumbs">{th}</div>{tit}
{field("Description (chapters included)", c["description"], k + "d")}
{field(f"Tags ({c.get('tags_youtube_count')} / 500 as YouTube counts)", ", ".join(c["tags"]), k + "g", True)}
{field("Pinned comment (post ~1 minute after it goes live)", c["pinned_comment"], k + "p")}
<div class="cols"><div><h3>Chapters</h3><pre class="mono">{esc(chap)}</pre></div>
<div><h3>Studio settings</h3><ul class="set"><li>Playlists: {esc(pl)}</li><li>Category: {esc((c.get("category") or {}).get("name"))}</li>
<li>Paid promotion: {"Yes" if fl.get("paid_promotion") else "No"}</li><li>Altered or synthetic content: {"Yes" if fl.get("altered_or_synthetic") else "No"}</li>
<li>Made for kids: {"Yes" if fl.get("made_for_kids") else "No"}</li><li>Language: {esc(fl.get("language"))}</li><li>Premiere: {"Yes" if fl.get("premiere") else "No"}</li>
<li>Test &amp; Compare: titles + thumbnails A / B / C</li><li>End screen: most relevant PUBLIC video + the full episode</li></ul></div></div>
<details><summary>Claims checked ({len(c.get("claims_checked") or [])})</summary><ul>{claims}</ul></details>
<details><summary>Hook</summary><p>"{esc(c.get("hook_quote"))}"</p></details></section>''')
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(eplabel(ep))} Clips Dashboard</title><style>
:root{{--bg:#f6f5f2;--card:#fff;--ink:#1d1d1f;--muted:#6b6b70;--line:#e2e0da;--acc:#7c3aed;--cwc:#c2410c;--tcl:#0f766e}}
@media (prefers-color-scheme:dark){{:root{{--bg:#141416;--card:#1e1e22;--ink:#ececef;--muted:#a0a0a8;--line:#33333a;--acc:#a78bfa;--cwc:#fb923c;--tcl:#2dd4bf}}}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 -apple-system,system-ui,sans-serif}}
header{{padding:20px 16px 8px;max-width:1100px;margin:auto}} h1{{margin:0;font-size:22px}} header p{{margin:4px 0 0;color:var(--muted)}}
nav{{display:flex;gap:8px;flex-wrap:wrap;padding:8px 16px;max-width:1100px;margin:auto;position:sticky;top:0;background:var(--bg);z-index:2}}
.tab{{border:1px solid var(--line);background:transparent;color:var(--ink);border-radius:20px;padding:6px 14px;font-weight:600;cursor:pointer}} .tab.on{{background:var(--acc);border-color:var(--acc);color:#fff}}
main{{max-width:1100px;margin:auto;padding:0 16px 40px}} .panel{{display:none;background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px}} .panel.on{{display:block}}
h2{{margin:0 0 6px;font-size:20px}} h3{{font-size:15px;margin:18px 0 6px}} .meta{{color:var(--muted);margin:0 0 14px}} a{{color:var(--acc)}}
.badge{{color:#fff;border-radius:10px;padding:1px 8px;font-weight:600;background:var(--muted)}} .badge.cwc{{background:var(--cwc)}} .badge.tcl{{background:var(--tcl)}}
.thumbs{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:14px}} figure{{margin:0}} figure img{{width:100%;border-radius:8px;display:block}} figcaption{{font-size:13px;color:var(--muted);margin-top:4px}}
.field{{border:1px solid var(--line);border-radius:10px;margin:10px 0;overflow:hidden}} .fh{{display:flex;justify-content:space-between;align-items:center;padding:6px 10px;background:var(--bg);font-weight:600;font-size:13px}}
.cp{{border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:8px;padding:3px 12px;cursor:pointer}} .cp.ok{{background:var(--acc);color:#fff;border-color:var(--acc)}}
pre{{margin:0;padding:10px;white-space:pre-wrap;word-break:break-word;font:inherit}} .mono{{font-family:ui-monospace,Menlo,monospace;font-size:13px}}
.cols{{display:grid;grid-template-columns:1fr 1fr;gap:16px}} .set{{margin:0;padding-left:18px}} .src{{color:var(--muted);font-size:13px;word-break:break-all}}
table{{border-collapse:collapse;width:100%}} td,th{{border-bottom:1px solid var(--line);padding:6px 8px;text-align:left;vertical-align:top}} details{{margin-top:12px}}
@media (max-width:700px){{.thumbs,.cols{{grid-template-columns:1fr}} th:nth-child(5),td:nth-child(5){{display:none}}}}
</style></head><body><header><h1>{esc(ep.get("show_name"))} {esc(eplabel(ep))} - Clips</h1><p>Every upload's master, A/B/C titles and thumbnails, description, tags and settings. Copy buttons on every field.</p></header>
<nav>{"".join(tabs)}</nav><main>{"".join(panels)}</main><script>
const tabs=document.querySelectorAll('.tab');function show(t){{tabs.forEach(b=>b.classList.toggle('on',b.dataset.t===t));document.querySelectorAll('.panel').forEach(p=>p.classList.toggle('on',p.id==='p-'+t));try{{localStorage.setItem('cwc-clips-tab',t)}}catch(e){{}}}}
tabs.forEach(b=>b.onclick=()=>show(b.dataset.t));let s=null;try{{s=localStorage.getItem('cwc-clips-tab')}}catch(e){{}}show(s&&document.querySelector('.tab[data-t="'+s+'"]')?s:'ep');
document.querySelectorAll('.cp').forEach(b=>b.onclick=async()=>{{const t=document.getElementById(b.dataset.c).innerText;try{{await navigator.clipboard.writeText(t)}}catch(e){{const a=document.createElement('textarea');a.value=t;document.body.appendChild(a);a.select();document.execCommand('copy');a.remove()}}b.textContent='Copied';b.classList.add('ok');setTimeout(()=>{{b.textContent='Copy';b.classList.remove('ok')}},1400)}});
</script></body></html>'''

if __name__ == '__main__':
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    if not a: C.fail(__doc__)
    sys.exit(main(os.path.abspath(a[0]), '--dry-run' in sys.argv))
