"""selftest_pack.py - the packaging gates on synthetic data (no network, no Telegram). Exit 0 = OK.
Run after any change to package.py / captions.py / the show file's packaging block."""
import os, sys, json, tempfile, shutil
tmp = tempfile.mkdtemp(prefix='podclips_packtest_'); os.environ['CWC_ROOT'] = tmp
import common as C, package as P
ok = True
def expect(name, cond):
    global ok; ok &= bool(cond); print(('PASS  ' if cond else 'FAIL  ') + name)
S = C.show('creative-lens')
expect('titles: an em dash is refused', any('dash' in x for x in P.title_problems(['Good Title Here Now', 'A Title — With Dash', 'Third Option Is Fine'], 'x')))
expect('titles: options whose first 5 words match are refused', any('first 5 words' in x for x in P.title_problems(['Why Every Business Needs A Podcast', 'Why every business needs a podcast now', 'Third'], 'x')))
expect('titles: over 100 characters is refused', any('100' in x for x in P.title_problems(['x' * 101], 'x')))
expect('titles: three good options pass', not P.title_problems(['Should Every Business Start a Podcast?', 'Starting a Podcast Now Is Like Buying Nvidia', 'Your Podcast Will Make Zero Unless'], 'x'))
tg = P.tags_for(S, 'cwc', ['business podcast', 'podcast marketing', 'video podcast', 'content strategy'])
L = P.tag_len(tg); expect(f'tags are filled from the stock set to 470-500 characters, counted as YouTube counts them ({L}; plain join {len(", ".join(tg))})', 470 <= L <= 500 and tg[0] == 'business podcast')
expect('the YouTube tag count adds a comma per separator and 2 quotes per tag with a space', P.tag_len(['a b', 'c']) == 3 + 1 + 1 + 2)
pl = P.playlists_for(S, 'cwc', 'AI ads are costing local businesses customers')
expect('playlists: the show clips playlist always, AI topics add the AI playlist, ids only', [x['title'] for x in pl] == ['The Creative Lens Show Clips', 'AI, Creativity & the Future of Art'] and all(x['id'].startswith('PL') for x in pl))
bad = ['Three red flags when you hire an editor', 'Viral Short vs Feature Film', 'How to resolve a fight on set', 'The fusion of film and TV']
expect('playlists: lower-case look-alikes (red flags, short vs feature, resolve a fight, fusion of) add NOTHING', all([x['title'] for x in P.playlists_for(S, 'cwc', t)] == ['The Creative Lens Show Clips'] for t in bad))
expect('playlists: real camera titles still match (RED, Sony vs Canon, DaVinci)', 'Camera News and Camera Drama!' in [x['title'] for x in P.playlists_for(S, 'cwc', 'RED cuts the price')] and 'Camera Tests and Showdowns' in [x['title'] for x in P.playlists_for(S, 'cwc', 'Sony FX3 vs Canon C50')] and 'Tips for DaVinci Resolve' in [x['title'] for x in P.playlists_for(S, 'cwc', 'A DaVinci tip')])
expect('playlists: The Creative Lens gets its own clips playlist', [x['title'] for x in P.playlists_for(S, 'tcl', 'anything')] == ['The Creative Lens Clips'])
# full episode: the phone-emoji title is the vertical stream and is never linked (Colden 2026-10-02)
W = f'{tmp}/clips/creative-lens/Ep99'; os.makedirs(W)
C.save(f'{W}/episode.json', {'show': 'creative-lens', 'ep_key': 'Ep99', 'ep_no': 99})
for ch, ids in (('cwc', ('AAA', 'BBB')), ('tcl', ('CCC', 'DDD'))):
    C.save(f'{C.DATA}/channels/{ch}/videos.json', {'videos': [{'id': ids[1], 'title': 'Big News | Ep. 99 \U0001F4F1', 'duration': 5000}, {'id': ids[0], 'title': 'Big News | Ep. 99', 'duration': 5000},
                                                              {'id': 'SHORT', 'title': 'Ep. 99 teaser', 'duration': 50}, {'id': 'OLD', 'title': 'Old | Ep. 9', 'duration': 5000}]})
fe = P.full_episode(W)
expect('full episode: the upload WITHOUT the phone emoji is linked, the vertical one skipped, shorts and other episodes ignored', fe['cwc']['id'] == 'AAA' and fe['tcl']['id'] == 'CCC' and fe['cwc']['skipped_vertical'] == ['BBB'])
C.save(f'{C.DATA}/channels/tcl/videos.json', {'videos': [{'id': 'DDD', 'title': 'Big News | Ep. 99 \U0001F4F1', 'duration': 5000}]})
fe = P.full_episode(W); expect('full episode: only a vertical upload -> stays open, never linked', fe['tcl']['id'] is None)
C.save(f'{C.DATA}/channels/tcl/videos.json', {'videos': [{'id': 'PRIV', 'title': 'Big News | Ep. 99', 'duration': 5000, 'privacy': 'private'}]})
fe = P.full_episode(W); expect('full episode: a PRIVATE / scheduled upload is not linked (stays open: "not public yet")', fe['tcl']['id'] is None and 'public' in fe['tcl']['why'])
C.save(f'{C.DATA}/channels/cwc/videos.json', {'videos': [{'id': 'TODD', 'title': 'Colden and Todd: Talking Shop | Ep. 99', 'duration': 5000, 'privacy': 'public'}]})
fe = P.full_episode(W); expect('full episode: another show\'s "Ep. 99" on the same channel is not linked', fe['cwc']['id'] is None)
shutil.rmtree(tmp); print('\nSELFTEST PACK ' + ('OK' if ok else 'FAILED')); sys.exit(0 if ok else 1)
