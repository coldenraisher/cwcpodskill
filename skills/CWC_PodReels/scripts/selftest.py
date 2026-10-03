"""selftest.py [<WORK>]   every gate that protects Colden, run against known-bad input: each must REFUSE, and the known-good
input must pass. Offline except the geometry test (it reads the pilot preview on disk). Nothing is sent, built or posted;
scratch files live in a temp folder. Default WORK = The Creative Lens Ep 24 (the pilot). Exit 1 when any gate let a bad
input through."""
import os, sys, json, shutil, tempfile, subprocess
import common as C
HERE = os.path.dirname(os.path.abspath(__file__)); PY = sys.executable; ok = []; bad = []
def check(name, cond, detail=''):
    (ok if cond else bad).append(name); print(('  ok    ' if cond else '  FAIL  ') + name + (f' - {detail}' if detail and not cond else ''))
def run(*a, stdin=None): return subprocess.run([PY, *a], capture_output=True, text=True, input=stdin, cwd=HERE)

def main(W):
    T = tempfile.mkdtemp(prefix='podreels_selftest_')
    try:
        print('Telegram router')
        r = run('tg_router.py', 'handle', stdin=json.dumps({'update_id': 1, 'callback_query': {'id': 'x', 'data': 'pc|Ep24|ok|t01'}}))
        check('a foreign callback (PodClips) is not ours -> 3', r.returncode == 3, r.stderr[-200:])
        r = run('tg_router.py', 'handle', stdin=json.dumps({'update_id': 2, 'message': {'chat': {'id': 1}, 'text': 'hello'}}))
        check('a stray text message is not ours -> 3', r.returncode == 3, r.stderr[-200:])

        print('B-roll flash gate (plan.flashes)')
        import plan as PL
        check('a 1-frame gap between two stills is refused', len(PL.flashes([{'src': 'a', 'rec': 100, 'frames': 80}, {'src': 'b', 'rec': 181, 'frames': 60}], [50, 300], 15)) == 2)
        check('an edge 6 frames before a cut is refused', len(PL.flashes([{'src': 'a', 'rec': 100, 'frames': 94}], [50, 200], 15)) == 1)
        check('stills handing over exactly + edges on cuts pass', not PL.flashes([{'src': 'a', 'rec': 100, 'frames': 80}, {'src': 'b', 'rec': 180, 'frames': 120}], [100, 300], 15))

        print('Packaging from data (pack_learn.py: the brief + its gates)')
        import pack_learn as PL
        B = PL.current(); check('a packaging brief exists (shorts_data.py summary builds it)', bool(B.get('id')), 'pack_learn.py build')
        pid = [x['id'] for x in B.get('patterns', []) if x['kind'] == 'title'][:2]
        learned = [{'id': pid[0], 'how': 'the FX3 is named: the data says a named product holds viewers'}, {'id': pid[1], 'how': 'kept to the number and the name, no open ending'}]
        check('a named product, a number and an open ending are measured features', {'S-named', 'S-number', 'S-cliffhanger'} <= set(PL.feats('An FX3 Will Not Save A Bad Story...')), str(PL.feats('An FX3 Will Not Save A Bad Story...')))
        check('themes.json without "brief" is refused', bool(PL.brief_ok({'themes': []}, 'x')))
        check('a theme without "learned" is refused', any('learned' in x for x in PL.problems({'title': 'An FX3 Will Not Save A Bad Story'}, 's99', {'title': 'An FX3 Will Not Save A Bad Story'}, hook='AN FX3 WILL NOT')))
        win = [x['id'] for x in B.get('patterns', []) if x['kind'] == 'title' and x['status'] == 'WIN']; lose = [x['id'] for x in B.get('patterns', []) if x['kind'] == 'title' and x['status'] == 'LOSE']
        if win: check('a title with no WIN pattern is refused when the brief has one', any('WIN' in x for x in PL.problems({'learned': learned}, 's99', {'title': 'A Thought About Stories'}, hook='A THOUGHT')))
        if 'S-cliffhanger' in lose: check('a LOSE pattern (cliffhanger ...) without "explore" is refused', any('LOSE' in x for x in PL.problems({'learned': learned}, 's99', {'title': 'An FX3 Will Not Save A Bad Story...'})))
        check('the same title with "explore" passes the LOSE gate', not any('LOSE' in x for x in PL.problems({'learned': learned, 'explore': {'title': 'testing whether an open ending holds on TikTok'}}, 's99', {'title': 'An FX3 Will Not Save A Bad Story...'})))

        print('Copy gates (postcopy.py)')
        S = f'{T}/copywork'; os.makedirs(f'{S}/edit', exist_ok=True); shutil.copy(f'{W}/episode.json', S)
        good = {'brief': B.get('id'), 'shorts': {'s99': {'title': 't', 'brands': ['cwc', 'tcl'], 'caption': 'Your FX3 will not save a bad story. The script has to win.\n#sonyfx3 #filmmaking #screenwriting #indiefilm #thecreativelens',
                                   'first_comment': 'What held your last project back, the camera or the script?', 'yt_title': 'An FX3 Will Not Save A Bad Story', 'fb_title': 'An FX3 Will Not Save A Bad Story',
                                   'playlist': {'cwc': 'tcl_shorts', 'tcl': 'tcl_shorts'}, 'ig_collab': 'none', 'learned': learned}}}
        C.save(f'{S}/copy.json', good); check('good copy (brief read, learned, a named product) passes', run('postcopy.py', 'check', S).returncode == 0, run('postcopy.py', 'check', S).stdout[-300:])
        b = json.loads(json.dumps(good)); b.pop('brief'); C.save(f'{S}/copy.json', b); check('copy that does not name the current brief is refused', run('postcopy.py', 'check', S).returncode == 1)
        b = json.loads(json.dumps(good)); b['shorts']['s99']['learned'] = []; C.save(f'{S}/copy.json', b); check('copy without "learned" is refused', run('postcopy.py', 'check', S).returncode == 1)
        for what, patch in (('4 hashtags', {'caption': 'A line.\n#a #b #c #d'}), ('an em dash', {'yt_title': 'Gear — story'}), ('a link', {'caption': 'See www.x.com now.\n#a #b #c #d #e'}),
                            ('a comment that is not a question', {'first_comment': 'Great episode.'}), ('CTA filler', {'first_comment': 'Thoughts? Drop it below?'}),
                            ('no Facebook title on a CWC post', {'fb_title': ''}), ('an unknown playlist', {'playlist': {'cwc': 'nope', 'tcl': 'tcl_shorts'}}), ('a guest with no IG handle', {'ig_collab': 'ASK'})):
            b = json.loads(json.dumps(good)); b['shorts']['s99'].update(patch); C.save(f'{S}/copy.json', b)
            check(f'copy with {what} is refused', run('postcopy.py', 'check', S).returncode == 1)

        print('Batch card / covers (Colden 2026-10-02: the centre 3:4, the best still, no AI teeth, Nano Banana Pro)')
        C.save(f'{S}/copy.json', good); r = run('tg_batch.py', 'send', S, '--dry-run')
        check('the batch card refuses a short without both covers', r.returncode != 0 and 'covers missing' in r.stdout + r.stderr, (r.stdout + r.stderr)[-200:])
        os.makedirs(f'{S}/edit/s99', exist_ok=True); json.dump([{'v': 1, 'status': 'approved', 'plan': 'x'}], open(f'{S}/edit/s99/versions.json', 'w'))
        import cover as CV
        FX = f'{C.SK}/references/selftest'; top = f'{FX}/bad_headline_top.jpg'; teeth = f'{FX}/bad_teeth.jpg'
        sz = CV.safe_zone(top, 'STORY > GEAR'); check('a headline above the centre 3:4 (round-1 s03) is refused by safe_zone', any('outside the centre 3:4' in x for x in sz), str(sz))
        m = json.loads(subprocess.run([f'{C.SK}/tools/mouth', teeth], capture_output=True, text=True).stdout.splitlines()[0])
        check('the round-1 s14 AI cover shows teeth (mouth > TEETH_MAX)', (m.get('open') or 0) > CV.TEETH_MAX, str(m.get('open')))
        job_bad = f'{T}/job_bad.json'; json.dump({'submitted': {'id': 'j1', 'model': 'gpt_image_2_5', 'params': {'reference_images': ['a']}}, 'jobs_wait': {'model': 'gpt_image_2_5', 'status': 'completed'}}, open(job_bad, 'w'))
        job_ok = f'{T}/job_ok.json'; json.dump({'submitted': {'id': 'j2', 'model': 'nano_banana_pro', 'params': {'reference_images': ['a']}}, 'jobs_wait': {'model': 'nano_banana_2', 'status': 'completed'}}, open(job_ok, 'w'))
        job_two = f'{T}/job_two.json'; json.dump({'submitted': {'id': 'j3', 'model': 'nano_banana_pro', 'params': {'reference_images': ['a', 'b']}}, 'jobs_wait': {'model': 'nano_banana_2'}}, open(job_two, 'w'))
        check('a Pro job the API reports back as nano_banana_2 is Nano Banana Pro (its page says so)', set(CV.job_model(job_ok)) == {'nano_banana_pro', 'nano_banana_2'})
        saw = 'looked: Colden, headline spelled right, lips together, nothing banned in the frame'
        import re as _re; C.save(f'{S}/themes.json', {'themes': [{'id': 's99', 'title': 'Story Over Gear', 'hook_text': ['STORY > GEAR', '180 RULE']}]})
        PT = CV.prompt_template({'id': 's99', 'title': 'Story Over Gear', 'hook_text': ['STORY > GEAR']}, {'still_confirmed': {'emotion': 'smile'}}, 'Colden', 'into the lens')
        raw = json.dumps(PT, indent=1); prompt = _re.sub(r'<<[^>]*>>', 'a concrete line', raw)
        check('the prompt template with its placeholders is refused', any('placeholders' in x for x in CV.prompt_problems(raw, 'STORY > GEAR', PT and {'hook_text': ['STORY > GEAR'], 'title': 'x'})))
        check('the filled template passes every prompt rule', not CV.prompt_problems(prompt, 'STORY > GEAR', {'hook_text': ['STORY > GEAR'], 'title': 'x'}), str(CV.prompt_problems(prompt, 'STORY > GEAR', {'hook_text': ['STORY > GEAR'], 'title': 'x'})))
        check('the template never names the subject (only @Image1)', not any('@Image1' in x and 'calls the subject' in x for x in CV.prompt_problems(prompt, 'STORY > GEAR', {'hook_text': ['STORY > GEAR'], 'title': 'x'})) and 'Colden' not in prompt)
        check('a prompt that calls the subject by his name is refused', any('calls the subject "Colden"' in x for x in CV.prompt_problems(prompt.replace('@Image1 (the', 'Colden, @Image1 (the', 1).replace('"source": "@Image1"', '"source": "@Image1 (Colden)"'), 'STORY > GEAR', {'hook_text': ['STORY > GEAR'], 'title': 'x'})))
        check('a headline over 3 words is refused', any('at most 3' in x for x in CV.prompt_problems(prompt.replace('STORY > GEAR', 'STORY BEATS GEAR EVERY TIME'), 'STORY BEATS GEAR EVERY TIME', {'hook_text': ['STORY BEATS GEAR EVERY TIME'], 'title': 'x'})))
        P2 = json.loads(prompt); P2['viewer_read'] = ''; check('a prompt without the one-second viewer read is refused', any('viewer_read' in x for x in CV.prompt_problems(json.dumps(P2), 'STORY > GEAR', {'hook_text': ['STORY > GEAR'], 'title': 'x'})))
        _fg = CV.face_gates(f'{FX}/bad_small_blue.jpg'); check('round-6 s15 (face 20 % wide, blue skin) is refused by the face gates', any('too small' in x for x in _fg) and any('skin' in x for x in _fg), str(_fg))
        pf = f'{T}/prompt.json'; open(pf, 'w').write(prompt)
        job_crop = f'{T}/job_crop.json'; json.dump({'request': {'reference_file': 'ai_ref_chest.png'}, 'submitted': {'id': 'j4', 'model': 'nano_banana_pro', 'params': {'reference_images': ['a']}}, 'jobs_wait': {'model': 'nano_banana_2', 'status': 'completed'}}, open(job_crop, 'w'))
        C.save(f'{S}/edit/s99/cover.json', {'headline': 'STORY > GEAR'}); r = run('cover.py', 'add', S, 's99', top, '--headline', 'STORY > GEAR', '--model', 'nano_banana_pro', '--job', job_crop, '--saw', saw, '--prompt', pf)
        check('a job submitted with a CROPPED reference is refused (the reference is always the full-resolution frame)', r.returncode != 0 and 'full-resolution' in r.stdout + r.stderr, (r.stdout + r.stderr)[-200:])
        P2 = json.loads(prompt); P2['lighting']['key'] = 'cool pale screen light from the front'; check('a prompt asking for a cool / blue key on the face is refused', any('blue' in x for x in CV.prompt_problems(json.dumps(P2), 'STORY > GEAR', {'hook_text': ['STORY > GEAR'], 'title': 'x'})))
        check('a prose prompt (not the JSON object) is refused', any('JSON' in x for x in CV.prompt_problems('@Image1 at a desk, lips together, no teeth, headline STORY > GEAR', 'STORY > GEAR')))
        check('a headline that is not the hook / title words and carries no WIN pattern is refused', any('WIN pattern' in x for x in CV.prompt_problems(prompt.replace('STORY > GEAR', 'THINK FIRST'), 'THINK FIRST', {'hook_text': ['STORY > GEAR'], 'title': 'x'})))
        check('a headline made of a named film (a WIN pattern) passes even off the hook', not CV.prompt_problems(prompt.replace('STORY > GEAR', 'GODFATHER FIRST'), 'GODFATHER FIRST', {'hook_text': ['STORY > GEAR'], 'title': 'x'}))
        P2 = json.loads(prompt); P2['text']['mode'] = 'render_exact_text'; P2['text']['exact_copy'] = 'STORY > GEAR'; check('a prompt asking the model to render the headline is refused (leave_space_for_later; the hook box carries it)', any('leave_space_for_later' in x for x in CV.prompt_problems(json.dumps(P2), 'STORY > GEAR', {'hook_text': ['STORY > GEAR'], 'title': 'x'})))
        P2 = json.loads(prompt); P2['main_prompt'] += ' with the headline STORY FIRST above him'; check('a main_prompt that spells a headline out is refused', any('spells the headline' in x for x in CV.prompt_problems(json.dumps(P2), 'STORY > GEAR', {'hook_text': ['STORY > GEAR'], 'title': 'x'})))
        from PIL import Image as _I; _hb = CV.hook_box(_I.new('RGB', (1080, 1920), 'gray'), 'STORY > GEAR', f'{T}/none.png'); _sz = CV.safe_zone((_hb.save(f'{T}/hb.jpg', quality=90), f'{T}/hb.jpg')[1], 'STORY > GEAR')
        _hb2 = CV.hook_box(_I.new('RGB', (1080, 1920), 'gray'), 'STORY > GEAR', f'{T}/none.png', 'bottom'); _hb2.save(f'{T}/hb2.jpg', quality=90); _sz2 = CV.safe_zone(f'{T}/hb2.jpg', 'STORY > GEAR')
        check('the hook box on the bottom third lands inside the centre 3:4 too', not [x for x in _sz2 if 'headline' in x], str(_sz2))
        _code = None
        try: CV.hook_box(_I.open(f'{C.SK}/references/selftest/bad_teeth.jpg').convert('RGB'), 'STORY > GEAR', f'{C.SK}/references/selftest/bad_teeth.jpg', 'top')
        except SystemExit as _x: _code = str(_x)
        check('a face sitting in the headline third is refused (the picture must compose around the zone)', _code is not None and 'holds the face' in _code, str(_code)[:120])
        P2 = json.loads(prompt); P2['composition']['layout'] = 'everything in the middle three quarters; the face in the centre'; P2['composition']['clear_space'] = 'above the head'; check('a layout that does not name the headline third is refused', any('third' in x for x in CV.prompt_problems(json.dumps(P2), 'STORY > GEAR', {'hook_text': ['STORY > GEAR'], 'title': 'x'})))
        check('the hook box lands inside the centre 3:4 and reads back by OCR', not [x for x in _sz if 'headline' in x], str(_sz))
        P2 = json.loads(prompt); P2['reference_images'][0]['do_not_transfer'] = ['nothing']; check('a reference not scoped with do_not_transfer (background, mic) is refused', any('do_not_transfer' in x for x in CV.prompt_problems(json.dumps(P2), 'STORY > GEAR', {'hook_text': ['STORY > GEAR']})))
        P2 = json.loads(prompt); P2['reference_images'].append(dict(P2['reference_images'][0], tag='@Image2')); check('two reference entries in the JSON are refused', any('ONE' in x for x in CV.prompt_problems(json.dumps(P2), 'STORY > GEAR', {'hook_text': ['STORY > GEAR']})))
        P2 = json.loads(prompt); P2['subject']['expression'] = 'a big smile, lips together, no teeth'; check('an expression asking for a big smile is refused even beside "no teeth"', any('never shows teeth' in x for x in CV.prompt_problems(json.dumps(P2), 'STORY > GEAR', {'hook_text': ['STORY > GEAR']})))
        P2 = json.loads(prompt); P2['style']['finish'] = 'masterpiece, 8k'; check('vague quality words are refused', any('vague' in x for x in CV.prompt_problems(json.dumps(P2), 'STORY > GEAR', {'hook_text': ['STORY > GEAR']})))
        P2 = json.loads(prompt); P2['text']['placement'] = 'upper middle'; check('a text placement without a percentage is refused', any('percentage' in x for x in CV.prompt_problems(json.dumps(P2), 'STORY > GEAR', {'hook_text': ['STORY > GEAR']})))
        pf = f'{T}/prompt.json'; open(pf, 'w').write(prompt)
        C.save(f'{S}/edit/s99/cover.json', {'headline': 'STORY > GEAR'})
        r = run('cover.py', 'add', S, 's99', top, '--headline', 'GEAR WINS', '--model', 'nano_banana_pro', '--job', job_ok, '--saw', saw, '--prompt', pf)
        check('add refuses a headline that is not the recorded decision', r.returncode != 0 and 'recorded decision' in r.stdout + r.stderr, (r.stdout + r.stderr)[-200:])
        r = run('cover.py', 'add', S, 's99', top, '--headline', 'STORY > GEAR', '--model', 'nano_banana_pro', '--job', job_ok, '--saw', saw, '--prompt', '@Image1 at a desk, lips together, no teeth, headline STORY > GEAR')
        check('add refuses a prose prompt (--prompt takes the JSON file as sent)', r.returncode != 0 and 'JSON' in r.stdout + r.stderr, (r.stdout + r.stderr)[-200:])
        r = run('cover.py', 'add', S, 's99', top, '--headline', 'STORY > GEAR', '--model', 'nano_banana_pro', '--job', job_two, '--saw', saw, '--prompt', prompt)
        check('a job with TWO reference images is refused (one reference, @Image1)', r.returncode != 0 and 'ONE' in r.stdout + r.stderr, (r.stdout + r.stderr)[-200:])
        r = run('cover.py', 'add', S, 's99', top, '--headline', 'STORY > GEAR', '--model', 'nano_banana_pro', '--job', job_ok, '--saw', saw, '--prompt', prompt.replace('@Image1', 'Colden'))
        check('a prompt that does not name @Image1 is refused', r.returncode != 0 and '@Image1' in r.stdout + r.stderr, (r.stdout + r.stderr)[-200:])
        r = run('cover.py', 'add', S, 's99', top, '--headline', 'STORY > GEAR', '--model', 'nano_banana_pro', '--job', job_ok, '--saw', saw, '--prompt', prompt.replace('"orientation": "portrait"', '"orientation": "3:4 portrait"'))
        check('a prompt that calls the image 3:4 is refused', r.returncode != 0 and '3:4' in r.stdout + r.stderr, (r.stdout + r.stderr)[-200:])
        r = run('cover.py', 'add', S, 's99', top, '--headline', 'STORY > GEAR', '--model', 'nano_banana_pro', '--job', job_bad, '--saw', saw, '--prompt', prompt)
        check('an AI cover whose job was not submitted as nano_banana_pro is refused', r.returncode != 0 and 'nano_banana_pro' in r.stdout + r.stderr, (r.stdout + r.stderr)[-200:])
        r = run('cover.py', 'add', S, 's99', top, '--headline', 'STORY > GEAR', '--model', 'nano_banana_pro', '--job', job_ok, '--saw', saw, '--prompt', prompt.replace('lips together, no teeth, a closed-mouth', 'a big smile showing teeth, a wide'))
        check('a prompt asking for teeth / a grin is refused', r.returncode != 0 and 'teeth' in (r.stdout + r.stderr).lower(), (r.stdout + r.stderr)[-200:])
        from PIL import Image; sq = f'{T}/square.jpg'; Image.new('RGB', (1440, 1920), 'gray').save(sq)
        r = run('cover.py', 'add', S, 's99', sq, '--headline', 'STORY > GEAR', '--model', 'nano_banana_pro', '--job', job_ok, '--saw', saw, '--prompt', prompt)
        check('a cover generated at 3:4 is refused (short-form covers are 9:16)', r.returncode != 0 and '9:16' in r.stdout + r.stderr, (r.stdout + r.stderr)[-200:])
        r = run('cover.py', 'add', S, 's99', top, '--headline', 'STORY > GEAR', '--model', 'nano_banana_pro', '--job', job_ok, '--saw', saw, '--prompt', prompt)
        check('a cover on which the model rendered text (round-1 s03: a headline in the top eighth) is refused by add', r.returncode != 0 and 'rendered text' in r.stdout + r.stderr, (r.stdout + r.stderr)[-200:])
        C.save(f'{S}/edit/s99/cover.json', {'headline': '180 RULE'}); _t = _I.open(teeth).convert('RGB'); _cv = _I.new('RGB', (1080, 1920), 'black'); _cv.paste(_t.crop((0, 264, 1080, 1484)), (0, 700)); _cv.save(f'{T}/teeth_notext.jpg', quality=92)   # the s14 cover below its headline, moved down so the toothy face sits in the middle third (face at 411,428 in the original; text ends at y 264)
        r = run('cover.py', 'add', S, 's99', f'{T}/teeth_notext.jpg', '--headline', '180 RULE', '--model', 'nano_banana_pro', '--job', job_ok, '--saw', saw, '--prompt', prompt.replace('STORY > GEAR', '180 RULE'))
        check('a cover with a toothy smile is refused by add', r.returncode != 0 and 'TEETH' in r.stdout + r.stderr, (r.stdout + r.stderr)[-200:])
        check('a mouth forming a word (open, not wide) never passes as a still', not CV.mouth_ok({'open': 0.05, 'mouth_w': 0.33, 'smile': 0.03}, 0.32, 'smile', 0.0))
        check('a shouted vowel (wide but the corners down - Nick s09) never passes as a smile', not CV.mouth_ok({'open': 0.092, 'mouth_w': 0.353, 'smile': -0.0099}, 0.2795, 'smile', -0.0225))
        check('a full smile with teeth (wide, corners up, flat - s15) passes as a thumbnail still', CV.mouth_ok({'open': 0.09, 'mouth_w': 0.459, 'smile': 0.045}, 0.3228, 'smile', -0.0034))
        check('lips together pass for every emotion', CV.mouth_ok({'open': 0.009, 'mouth_w': 0.32, 'smile': 0.0}, 0.32, 'serious', 0.0))
        check('a wide mouth is not a "serious" still', not CV.mouth_ok({'open': 0.09, 'mouth_w': 0.459, 'smile': 0.045}, 0.32, 'serious', 0.0))
        row = {'ci': True, 'l_closed': False, 'r_closed': False, 'gx': [0.5, 0.5], 'gy': [0.4, 0.4], 'yaw': 0, 'pitch': 0, 'eh': [0.5, 0.5], 'quality': 0.7, 'eye_open': [0.2, 0.14]}
        check('half-shut eyes (Vision eye_open 0.38x the usual) are refused even when the pixel height passes', not CV.eyes_ok(row, 0.45, 0, 0, 'laughing', 0.37))
        check('open eyes pass', CV.eyes_ok(dict(row, eye_open=[0.36, 0.35]), 0.45, 0, 0, 'laughing', 0.37))
        narrow = dict(row, eh=[0.30, 0.29], eye_open=[0.22, 0.21])                                   # a full smile narrows the eyes (0.65x height, 0.57x Vision)
        check('narrowed eyes on a SMILE pass (Colden: "narrow eyes fine")', CV.eyes_ok(narrow, 0.45, 0, 0, 'smile', 0.37))
        check('the same narrowed eyes on a SERIOUS still are refused', not CV.eyes_ok(narrow, 0.45, 0, 0, 'serious', 0.37))
        ep = C.episode(W); Ssh = C.show(ep['show']); col = next(p for p in ep['people'] if p['name'] == 'Colden'); nick = next(p for p in ep['people'] if p['name'] == 'Nick')
        Pm = {'short': 's99', 'runs': [{'key': 'single:Nick'}, {'key': 'stack:Nick'}], 'items': [{'kind': 'video', 'clip': os.path.basename(col['path']), 'enabled': True, 'src_in': 0, 'src_out': 100}, {'kind': 'video', 'clip': os.path.basename(nick['path']), 'enabled': True, 'src_in': 0, 'src_out': 100}]}
        check('a short posting to Create with Colden takes COLDEN as its face even when Nick says the line', CV.cover_people(S, {'destination': 'both'}, Pm, Ssh, ep) == {'Colden'})
        check('a TCL-only short takes the people who speak in it', CV.cover_people(S, {'destination': 'tcl'}, Pm, Ssh, ep) == {'Nick'})
        code = None
        try: CV.cover_people(S, {'destination': 'cwc'}, dict(Pm, items=Pm['items'][1:]), Ssh, ep)
        except SystemExit as x: code = x.code
        check('a CWC short where Colden is never on screen -> ASK (exit 2)', code == 2, f'exit {code}')
        sl = {'shortlist': [{'n': 1, 'who': 'Colden', 'pool': 'thumb', 'speaking': True}, {'n': 2, 'who': 'Colden', 'pool': 'thumb', 'speaking': False}]}
        C.save(f'{S}/edit/s99/cover.json', sl); r = run('cover.py', 'still', S, 's99', '1', 'smile', 'a talking frame while a silent one is on the sheet')
        check('still refuses a talking tile while a silent one of the same person is on the sheet', r.returncode != 0 and 'ranks lower' in r.stdout + r.stderr, (r.stdout + r.stderr)[-200:])
        os.remove(f'{S}/edit/s99/cover.json')
        r = run('cover.py', 'resolve', S, 's99')
        check('a Resolve cover without a confirmed still is refused', r.returncode != 0 and 'confirmed still' in r.stdout + r.stderr, (r.stdout + r.stderr)[-200:])
        r = run('cover.py', 'brief', S, 's99'); check('an AI brief without the no-teeth reference is refused', r.returncode != 0)

        print('Preview geometry gate (review.geometry)')
        import review as R
        P3 = C.load(f'{W}/edit/s03/build.v3.json'); prev = f'{W}/edit/s03/preview/s03 v3 preview.mp4'
        if os.path.exists(prev): check('the approved pilot preview passes', not R.geometry(P3, prev)[1], str(R.geometry(P3, prev)[1]))
        cam = next(p['path'] for p in C.episode(W)['people'] if p['name'] == 'Colden'); lb = f'{T}/letterbox.mp4'
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', '5100', '-i', cam, '-t', '1', '-vf', 'scale=720:-2,pad=720:1280:0:(oh-ih)/2', '-an', lb], check=True)
        check('a letterboxed single is refused', any('letterboxed' in x for x in R.geometry({'fps': 30.0, 'runs': [{'key': 'single:Colden', 'a': 0, 'b': 30, 'visible': ['Colden']}], 'broll': []}, lb)[1]))

        print('Publishing (publish.py plan)')
        Pw = f'{T}/pubwork'; os.makedirs(f'{Pw}/review', exist_ok=True); [shutil.copy(f'{W}/{f}', Pw) for f in ('episode.json', 'checked.json', 'themes.json')]
        ids = C.load(f'{W}/checked.json')['deliver']; master = prev; cover = f'{W}/edit/s03/cover/2 ai.jpg'; cp = {'shorts': {}}
        for i, s in enumerate(ids):
            os.makedirs(f'{Pw}/edit/{s}', exist_ok=True); json.dump([{'v': 1, 'status': 'approved', 'master': {'file': master}}], open(f'{Pw}/edit/{s}/versions.json', 'w'))
            cp['shorts'][s] = {'title': s, 'brands': ['cwc', 'tcl'] if i % 2 else ['tcl'], 'status': 'approved', 'cover': cover, 'playlist': {}, 'ig_collab': 'none'}
        C.save(f'{Pw}/copy.json', cp)
        r = run('publish.py', 'plan', Pw); check('no month_counts.json -> refused (count the scheduled posts first)', r.returncode == 1, (r.stdout + r.stderr)[-200:])
        C.save(f'{Pw}/review/month_counts.json', {'tcl': {'2099-01': 0}})
        import publish as PB
        real = C.show
        def nocap(sid):
            S = real(sid); S['publishing']['month_cap'] = {k: v for k, v in (S['publishing'].get('month_cap') or {}).items() if k != 'cwc'}; return S
        C.show = nocap; code = None
        try: PB.plan(Pw)
        except SystemExit as e: code = e.code
        finally: C.show = real
        check('a brand without a month cap on file -> ASK (exit 2)', code == 2, f'exit {code}')
        cp['shorts'] = {k: dict(v, brands=['tcl']) for k, v in cp['shorts'].items()}; C.save(f'{Pw}/copy.json', cp)
        import datetime as dt
        d0 = dt.date.today() + dt.timedelta(days=7); d0 = d0.replace(day=min(d0.day, 20))           # the 7-day window stays inside one month
        C.save(f'{Pw}/review/month_counts.json', {'tcl': {d0.strftime('%Y-%m'): 15}})
        r = run('publish.py', 'plan', Pw, '--start', d0.isoformat())
        pl = C.load(f'{Pw}/review/publish_plan.json') or {}; n_tcl = sum(1 for p in pl.get('posts', []) if p['brand'] == 'tcl')
        check('TCL with 15 already scheduled gets <= 5 more, the rest on the CUT list (lowest ranked)', r.returncode == 0 and n_tcl <= 5 and len(pl.get('cut', [])) >= 5 and pl['cut'][0]['short'] == ids[-1], (r.stdout + r.stderr)[-300:])

        print('Lock')
        r = run('lock.py', W, '--dry-run'); check('lock refuses while shorts are not approved + mastered (exit 2)', r.returncode == 2 or 'dry run' in r.stdout, (r.stdout + r.stderr)[-200:])
    finally:
        shutil.rmtree(T, ignore_errors=True)                       # the temp folder this run made
    print(f'\n{len(ok)} gates hold, {len(bad)} failed' + (f': {bad}' if bad else ''))
    return 1 if bad else 0

if __name__ == '__main__':
    sys.exit(main(os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else C.work_dir('creative-lens', 'Ep24')))
