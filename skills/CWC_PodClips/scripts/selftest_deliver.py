"""selftest_deliver.py - the final delivery (ruling 43) on synthetic files in a temp folder (no NAS, no Telegram, no
real Trash). Exit 0 = OK. Run after any change to deliver.py."""
import os, sys, json, tempfile, types, io, contextlib
tmp = tempfile.mkdtemp(prefix='podclips_delivertest_'); os.environ['CWC_ROOT'] = tmp; os.environ['CWC_TRASH'] = f'{tmp}/Trash'
sys.modules['tg_themes'] = types.SimpleNamespace(api=lambda *a, **k: {}, chat=lambda: 42)     # no Telegram from a test
import common as C, deliver as D
ok = True
def expect(name, cond):
    global ok; ok &= bool(cond); print(('PASS  ' if cond else 'FAIL  ') + name)
def run(*a):
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()): return D.main(*a)
    except SystemExit as e: return e.code
W = f'{tmp}/clips/creative-lens/Ep88'; NAS = f'{tmp}/Volumes/Share/Ep 88'; os.makedirs(NAS); os.makedirs(f'{W}/edit/t01/master')
C.save(f'{W}/episode.json', {'show': 'creative-lens', 'show_name': 'The Creative Lens', 'ep_key': 'Ep88', 'ep_no': 88, 'dir': NAS})
def put(p, data): os.makedirs(os.path.dirname(p), exist_ok=True); open(p, 'wb').write(data); return p
clips = []
for ch, title in (('cwc', 'Should You Start a Podcast? Yes: Here Is Why'), ('tcl', 'Your Podcast Will Make Zero')):
    m = put(f'{W}/edit/t01/master/Ep 88 C01 X {ch.upper()} v1.mp4', f'video {ch}'.encode() * 1000)
    th = {x: put(f'{W}/package/t01/thumbs/{ch}/{x}.png', f'png {ch} {x}'.encode()) for x in 'ABC'}
    put(f'{W}/package/t01/thumbs/{ch}/still_sheet.jpg', b'sheet')
    srt = put(f'{W}/package/t01/Ep 88 C01 X {ch.upper()} v1 (L).srt', b'1\n00:00:00,000 --> 00:00:01,000\nhi\n')
    C.save(f'{W}/package/t01/thumbs.{ch}.json', {'abc': th}); C.save(f'{W}/package/t01/facts.{ch}.json', {'master': m, 'captions': srt})
    clips.append({'theme': 't01', 'channel': ch, 'v': 1, 'timeline': f'X {ch} (L)', 'master': m, 'captions': srt, 'thumbnails': th, 'titles': {'A': title, 'B': 'b', 'C': 'c'},
                  'push_order': 1, 'seconds': 300, 'description': 'd', 'tags': ['a'], 'pinned_comment': 'q?', 'chapters': [{'t': 0, 'text': 'x'}], 'playlists': [], 'flags': {}, 'needs': []})
C.save(f'{W}/lock.json', {'clips': [{'theme': 't01', 'channel': c['channel'], 'v': 1, 'timeline': c['timeline'], 'master': c['master']} for c in clips]})
C.save(f'{W}/edit/t01/versions.json', [{'v': 1, 'channel': c['channel'], 'status': 'locked', 'master': {'file': c['master']}} for c in clips])
C.save(f'{W}/delivery.json', {'version': 2, 'clips': clips, 'full_episode': {}, 'rules_for_the_plan': {}})
F = f'{NAS}/Final/Clips'
expect('a dry run copies and moves nothing', run(W, True) == 0 and not os.path.exists(F) and os.path.exists(clips[0]['master']))
expect('delivery runs', run(W, False) == 0)
expect('the master is named by title A, minus the characters SMB refuses (? :)', os.path.exists(f'{F}/Should You Start a Podcast Yes Here Is Why.mp4') and os.path.exists(f'{F}/Your Podcast Will Make Zero.mp4'))
expect('thumbnails A/B/C and the srt sit in their sub folders', all(os.path.exists(f'{F}/Thumbnails/Your Podcast Will Make Zero - {x}.png') for x in 'ABC') and os.path.exists(f'{F}/Captions/Your Podcast Will Make Zero.srt'))
expect('the Clips Dashboard is written into Final/Clips', os.path.exists(f'{F}/Ep 88 Clips Dashboard.html') and 'Copy' in open(f'{F}/Ep 88 Clips Dashboard.html').read())
dj = C.load(f'{W}/delivery.json'); lj = C.load(f'{W}/lock.json'); vj = C.load(f'{W}/edit/t01/versions.json'); tj = C.load(f'{W}/package/t01/thumbs.tcl.json')
expect('every record now points at the NAS copy (delivery, lock, versions, thumbs)', all(c['master'].startswith(F) for c in dj['clips'] + lj['clips']) and all(v['master']['file'].startswith(F) for v in vj) and all(p.startswith(F) for p in tj['abc'].values()))
expect('the local masters, thumbnail folders and srt files went to the Trash; the JSON records stayed', not os.path.exists(f'{W}/edit/t01/master') and not os.path.exists(f'{W}/package/t01/thumbs') and not any(f.endswith('.srt') for f in os.listdir(f'{W}/package/t01')) and os.path.exists(f'{W}/package/t01/thumbs.tcl.json') and os.listdir(os.environ['CWC_TRASH']))
expect('a second run is a no-op (nothing copied twice)', run(W, False) == 0 and C.load(f'{W}/delivered.json')['copied'] == 0)
new = put(f'{W}/edit/t01/master/Ep 88 C01 X TCL v2.mp4', b'fixed video' * 1000)            # a fix after delivery: the same title, another file
C.update(f'{W}/delivery.json', lambda d: d['clips'][1].update(master=new))
expect('a fix after delivery replaces the file: the old one goes to #recycle / Trash, the new one is verified in place', run(W, False) == 0 and open(f'{F}/Your Podcast Will Make Zero.mp4', 'rb').read() == b'fixed video' * 1000 and C.load(f'{W}/delivered.json')['recycled_on_nas'])
C.update(f'{W}/delivery.json', lambda d: d['clips'][1]['titles'].update(A='Should You Start a Podcast?? Yes: Here Is Why'))
expect('two uploads that would get the same file name are refused', run(W, False) == 1)
C.update(f'{W}/delivery.json', lambda d: d['clips'][1]['titles'].update(A='Your Podcast Will Make Zero'))
C.update(f'{W}/episode.json', lambda e: e.update(dir=f'{tmp}/Volumes/NotMounted/Ep 88'))
expect('NAS not mounted -> exit 2 (ask), nothing moved', run(W, False) == 2)
print('SELFTEST DELIVER OK' if ok else 'SELFTEST DELIVER FAILED'); sys.exit(0 if ok else 1)
