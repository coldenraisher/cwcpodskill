"""selftest_prompt.py - AI thumbnails: the prose recipe (ruling 47), GPT Image 2.5 sunburst + Grok Imagine 2.0, the clean
reference, Rule 1 - on synthetic data: no Higgsfield call, no real files. Exit 0 = OK. Run after any change to
thumb_prompt.py or thumbs.py add."""
import os, sys, json, tempfile, io, contextlib
tmp = tempfile.mkdtemp(prefix='podclips_prompttest_'); os.environ['CWC_ROOT'] = tmp
import common as C, thumbs as T, thumb_prompt as TP
from PIL import Image
ok = True
def expect(name, cond):
    global ok; ok &= bool(cond); print(('PASS  ' if cond else 'FAIL  ') + name)
def dies(f, *a, **k):
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()): f(*a, **k)
    except SystemExit as e: return e.code
    return 0
W = f'{tmp}/clips/creative-lens/Ep77'; d, _ = T.paths(W, 't01', 'cwc')
full = f'{d}/ai_ref_full.png'; Image.new('RGB', (1920, 1080), 'gray').save(full); crop = f'{d}/ref_face.png'; Image.new('RGB', (400, 400), 'gray').save(crop)
T.save(W, 't01', 'cwc', {'speaker': 'Colden', 'still': full, 'still_confirmed': {'n': 1}, 'pick': 2, 'kinds': ['frame', 'hook', 'ai-1', 'ai-2'], 'ai': {'ai-1': {'model': 'gpt_image_2_5'}},
                         'ai_ref': {'file': full, 'who': 'Colden', 'mouth_open': 0.01}})
C.save(f'{W}/package/t01/copy.cwc.json', {'titles': ['Should Every Business Start a Podcast in 2026?', 'b', 'c'], 'summary': 'Is a business podcast still worth it?', 'hook_headline': 'TOO LATE?',
                                          'ai_headline': 'EVERYONE HAS ONE', 'ai_headline_2': 'TOO LATE?', 'C': 'Your Business Podcast Will Make Zero', 'ai_headline_C': 'ZERO AFTER 100 EPISODES'})
wr = 'plain black baseball cap worn forward, fitted black crew-neck T-shirt (white AirPods in the footage are left out)'
C.save(TP.wardrobe_path(W, 'Colden'), {'text': wr})
PROM = 'Every business is told to start a podcast - is it still worth it when everyone has one?'
SCENE = 'He stands in his purple-lit creator studio holding up one podcast microphone, and behind him hundreds of identical podcast microphones on desk stands fill the room in receding rows'
EXPR = 'A knowing look, one eyebrow raised, lips closed in a slight smile'
def mk(slot='ai-1', **k):
    a = dict(promise=PROM, obj='podcast microphones', scene=SCENE, expression=EXPR); a.update(k)
    return dies(TP.prompt, W, 't01', 'cwc', slot, (), a['promise'], a['obj'], a['scene'], a['expression'])
def cur(slot='ai-1'): return open(f'{d}/ai_prompt.{slot}.txt').read(), C.load(f'{d}/ai_prompt.{slot}.refs.json')
expect('the prompt needs a promise, an object, a scene and an expression', dies(TP.prompt, W, 't01', 'cwc', 'ai-1') == 1 and mk() == 0)
text, meta = cur()
expect('ai-1 = GPT Image 2.5 sunburst, quality high, 1k, 16:9; ai-2 = Grok Imagine 2.0, medium, 1k, 16:9',
       meta['model'] == 'gpt_image_2_5' and TP.PARAMS['gpt_image_2_5'] == {'model': 'gpt_image_2_5', 'variant': 'sunburst', 'quality': 'high', 'resolution': '1k', 'aspect_ratio': '16:9'}
       and TP.MODEL['ai-2'] == 'grok_image_2_0' and TP.PARAMS['grok_image_2_0'] == {'model': 'grok_image_2_0', 'quality': 'medium', 'resolution': '1k', 'aspect_ratio': '16:9'})
expect('the prompt is plain prose (~950 characters), no JSON, the person only as @Image1, the exact headline', 600 <= len(text) <= 1400 and '{' not in text and 'the man in @Image1' in text and 'Colden' not in text and 'reading exactly "EVERYONE HAS ONE"' in text)
expect('the wardrobe is the episode one, its (AirPods) aside stripped - naming them invites them', 'plain black baseball cap' in text and 'AirPods' not in text)
expect('a podcast mic as the topic object drops the "no microphone" tail (a prop mic is allowed)', 'no microphone' not in text and 'no earbuds' in text)
expect('the prose prompt passes the gate', TP.problems(text, meta, 'Colden') == [])
expect('a hand-edited prompt is refused (change the inputs, rebuild)', any('edited by hand' in x for x in TP.problems(text + ' Extra.', meta, 'Colden')))
mk(scene=SCENE + ', no other people and no logos')
expect('a scene that says what is NOT there is refused ("naming a thing invites it")', any('NOT there' in x for x in TP.problems(*cur(), 'Colden')))
mk(expression='A warm smile at the viewer')
expect('a smile without closed lips is refused (ruling 40)', any('ruling 40' in x for x in TP.problems(*cur(), 'Colden')))
mk(scene='He stands in his purple-lit creator studio, arms crossed, warm light from the left side of the room, calm and still')
expect('a scene without the topic object is refused (Rule 1.2)', any('topic object' in x for x in TP.problems(*cur(), 'Colden')))
expect('a crop or a mid-word frame as the reference is refused', 'crop' in (TP.full_frame_problem(dict(meta, files=[crop])) or '') and 'mid-word' in (TP.full_frame_problem(dict(meta, mouth_open=0.05)) or ''))
expect('products as a second reference are refused (ONE reference)', dies(TP.prompt, W, 't01', 'cwc', 'ai-1', (crop,), PROM, 'podcast microphones', SCENE, EXPR) == 1)
mk(); expect('check-prompt passes and records the slot params', dies(TP.check, W, 't01', 'cwc', 'ai-1') == 0 and T.rec(W, 't01', 'cwc')['prompts']['ai-1']['params']['variant'] == 'sunburst')
mk('ai-2'); expect('RULE 1.3: ai-2 with the same concept as ai-1 is refused', dies(TP.check, W, 't01', 'cwc', 'ai-2') == 1)
mk('ai-2', obj='stock chart', scene='He points at a giant glowing stock chart of podcast launches that has already peaked and is crashing behind him in his purple-lit studio')
expect('RULE 1.3: a different concept for ai-2 passes, with its own headline and Grok', dies(TP.check, W, 't01', 'cwc', 'ai-2') == 0 and 'reading exactly "TOO LATE?"' in cur('ai-2')[0] and cur('ai-2')[1]['model'] == 'grok_image_2_0')
mk('C', obj='zero dollar sign', scene='He holds a huge cardboard sign with a giant zero dollar sign painted on it next to a stack of one hundred podcast episode cassettes in his purple-lit studio')
mc = cur('C')[1]
expect('thumbnail C: ai_headline_C (2-5 words) and the model of A (GPT Image 2.5 here)', mc['headline'] == 'ZERO AFTER 100 EPISODES' and mc['limits'] == [2, 5] and mc['model'] == 'gpt_image_2_5')
C.update(f'{d}/ai_prompt.ai-2.refs.json', lambda m: m.update(promise='Learn how to bake sourdough bread at home tonight.'))
expect('RULE 1.2: a click promise not about this video is refused', dies(TP.check, W, 't01', 'cwc', 'ai-2') == 1)
gen = f'{tmp}/gen.png'; Image.new('RGB', (1376, 768), 'gray').save(gen)
SAW = 'the man from @Image1 holding a podcast mic in his studio full of mics, EVERYONE HAS ONE spelled right'; READS = 'a podcast-mic crowd: a video about podcasts being everywhere'
expect('add refuses ai-1 made with another model', dies(T.add, W, 't01', 'cwc', gen, 'ai-1', 'grok_image_2_0', None, SAW, 'job123456', 'grok_image_2_0', READS) == 1)
expect('add refuses an image without the job id or the 320x180 read', dies(T.add, W, 't01', 'cwc', gen, 'ai-1', 'gpt_image_2_5', None, SAW, None, 'gpt_image_2_5', READS) == 1 and dies(T.add, W, 't01', 'cwc', gen, 'ai-1', 'gpt_image_2_5', None, SAW, 'job123456', 'gpt_image_2_5', None) == 1)
expect('add records GPT Image 2.5 with its job id and the 320x180 preview', dies(T.add, W, 't01', 'cwc', gen, 'ai-1', 'gpt_image_2_5', None, SAW, 'job123456', 'gpt_image_2_5', READS) == 0
       and T.rec(W, 't01', 'cwc')['ai']['ai-1']['gen_id'] == 'job123456' and os.path.exists(f'{d}/3 ai-1 320.jpg'))
open(f'{d}/ai_prompt.ai-1.txt', 'a').write(' Edited.')
expect('a prompt changed after check-prompt voids the next add', dies(T.add, W, 't01', 'cwc', gen, 'ai-1', 'gpt_image_2_5', None, SAW, 'job123456', 'gpt_image_2_5', READS) == 1)
print('SELFTEST PROMPT OK' if ok else 'SELFTEST PROMPT FAILED'); sys.exit(0 if ok else 1)
