"""coldread.py prompt <WORK> <id>            the exact brief for the reviewer (instructions + the assembled short)
   coldread.py record <WORK> <id> <file.json | '-'>
A SECOND reader who has seen nothing - not the episode, not the transcript, not the scores - reads the short in play
order as a stranger in the feed and says where they would swipe. Spawn a FRESH agent with the output of `prompt` as its
whole brief; record its JSON here. The verdict is bound to the hash of the assembled text (change one phrase id and
check.py asks for a new read). Gaps are BLOCKING (fail) or MINOR (do not). Honest limit: code cannot prove a separate
agent wrote the JSON - this is an attestation."""
import os, sys, json
import common as C, themes as T
KEYS = {'hook_clear': int, 'payoff_answers_hook': int, 'self_contained': int, 'missing_context': list, 'minor_gaps': list, 'slow_spots': list, 'would_swipe_at': str, 'verdict': str, 'one_line': str}
if __name__ == '__main__':
    if len(sys.argv) < 4: C.fail(__doc__)
    cmd, W, tid = sys.argv[1], T.Work(sys.argv[2]), sys.argv[3]; txt = W.assemble(W.theme(tid))
    if cmd == 'prompt': print(open(f'{C.SK}/references/coldread_prompt.md').read() + '\n' + '-' * 80 + '\n' + txt)
    elif cmd == 'record':
        raw = sys.stdin.read() if sys.argv[4] == '-' else open(sys.argv[4]).read()
        v = json.loads(raw[raw.index('{'):raw.rindex('}') + 1])
        for k, ty in KEYS.items():
            if not isinstance(v.get(k), ty): C.fail(f'the reviewer answer has no valid "{k}" ({ty.__name__})')
        for k in ('hook_clear', 'payoff_answers_hook', 'self_contained'):
            if not 0 <= v[k] <= 5: C.fail(f'{k} must be 0-5')
        if (v['hook_clear'] < 3 or v['payoff_answers_hook'] < 3 or v['self_contained'] < 3 or v['missing_context']) and v['verdict'] == 'PASS':
            v['verdict'] = 'FAIL'; v['verdict_note'] = 'set to FAIL by coldread.py: the answer breaks its own PASS conditions'
        v.update({'theme': tid, 'text_sha': C.sha_text(txt), 'recorded_at': C.now()})
        C.save(f'{W.work}/cold/{tid}.json', v)
        print(f'{tid}: {v["verdict"]}  hook {v["hook_clear"]}  payoff {v["payoff_answers_hook"]}  self-contained {v["self_contained"]}  swipe at: {v["would_swipe_at"][:60]}' + ''.join(f'\n   BLOCKING: {m}' for m in v['missing_context']))
    else: C.fail(__doc__)
