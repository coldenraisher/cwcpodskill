"""Library for the theme files (no command line): spans, runtime, the play-order assembly.

themes.json (written by Claude, checked by check.py) - a theme points at PHRASE IDS of phrases.json, never at seconds,
so a range cannot start or end inside a word or a thought:
  hook     {"from": "P0412", "to": "P0413", "quote": "<verbatim words of those phrases>"}       the cold open
  body     [{"from": "P0380", "to": "P0455", "why": "setup"}, ...]                              in PLAY order
  payoff   {"from": "P0890", "to": "P0893", "quote": "<verbatim>"}                              inside the LAST body range
A range plays everything every speaker says from the start of `from` to the end of `to` on the locked cut."""
import os, re
import common as C

def rubric(): return C.load(f'{C.SK}/references/rubric.json')

class Work:
    def __init__(self, work):
        self.work = os.path.abspath(work); self.ep = C.episode(self.work); self.S = C.show(self.ep['show'])
        self.ph = C.load(f'{self.work}/phrases.json'); self.by = {p['id']: p for p in self.ph}
        self.themes_path = f'{self.work}/themes.json'; self.R = rubric()
    def themes(self):
        t = C.load(self.themes_path)
        if not t: C.fail(f'no themes.json in {self.work}')
        return t
    def span(self, r):
        """{'from','to'} -> [start, end] on the cut clock, or raises KeyError / ValueError"""
        a = self.by[r['from']]; b = self.by[r['to']]
        if b['end'] <= a['start']: raise ValueError(f'{r["from"]}..{r["to"]} runs backwards')
        return [a['start'], b['end']]
    def base_span(self, r): return [self.by[r['from']]['b0'], self.by[r['to']]['b1']]
    def inside(self, sp):
        return [p for p in self.ph if sp[0] - 1e-6 <= (p['start'] + p['end']) / 2 <= sp[1] + 1e-6]
    def text(self, r): return ' '.join(p['text'] for p in self.inside(self.span(r)))
    def dead_air(self, sp):
        """seconds the edit will tighten inside a span: stretches over 0.8 s where nobody says a word are cut to 0.5 s
        (not inside a screen share / played video: that is picture, not dead air)"""
        cfg = self.R['dead_air']; cut = 0.0; end = sp[0]
        for p in sorted(self.inside(sp), key=lambda p: p['start']):
            gap = p['start'] - end
            if gap > cfg['over'] and not any(s['start'] < p['start'] and s['end'] > end for s in self.ep['specials']): cut += gap - cfg['keep']
            end = max(end, p['end'])
        return cut
    def runtime(self, th):
        """(raw seconds of the ranges, estimated seconds of the finished clip incl. cold open + stinger + end screen)"""
        fx = self.S['fixed_seconds']; body = [self.span(r) for r in th['body']]; hook = self.span(th['hook'])
        raw = sum(b - a for a, b in body); est = (hook[1] - hook[0]) + fx['stinger'] + raw - sum(self.dead_air(s) for s in body) + fx['end_screen']
        return raw, est
    def spans(self, th):
        """every second of the cut this clip uses (body + hook), for the overlap rule"""
        return [self.span(r) for r in th['body']] + [self.span(th['hook'])]
    def shares(self, th):
        tot = {}
        for sp in [self.span(r) for r in th['body']]:
            for p in self.inside(sp): tot[p['who']] = tot.get(p['who'], 0) + p['n']
        n = sum(tot.values()) or 1; return {k: round(100 * v / n) for k, v in sorted(tot.items(), key=lambda kv: -kv[1])}
    def specials_in(self, th):
        out = []
        for s in self.ep['specials']:
            ov = sum(max(0.0, min(b, s['end']) - max(a, s['start'])) for a, b in [self.span(r) for r in th['body']])
            if ov >= 5.0: out.append(dict(s, overlap=round(ov, 1)))
        return out
    def assemble(self, th):
        """the clip as a viewer gets it: title, cold open, body in play order with the jumps marked. No timecodes, no
        phrase ids, no scores - the cold-read reviewer sees only what a stranger on YouTube would see."""
        L = [f'TITLE: {th["title"]}', '', '[COLD OPEN - the first thing the viewer hears]']
        guests = {p['name']: p for p in self.ep.get('people', []) if not p.get('host')}; carded = set()
        def say(sp, cards=True):
            out = []; who = None; seen = set()
            for p in sorted(self.inside(sp), key=lambda p: (p['start'], p['end'])):
                for k, s in enumerate(self.ep['specials']):
                    if k not in seen and s['start'] <= p['end'] and p['start'] <= s['end']:
                        seen.add(k); d = next((x for x in th.get('shares', []) if s['start'] - 1 <= C.parse_tc(x['at']) <= s['end'] + 1), None)
                        out.append(f'[ON SCREEN: {d["what"]}]' if d and d.get('integral') else '[the hosts look at something on their screen that the viewer is NOT shown]'); who = None
                if cards and p['who'] in guests and p['who'] not in carded and p['n'] >= 3:      # only a GUEST gets a name tag (Colden 2026-10-01)
                    g = guests[p['who']]; carded.add(p['who']); out.append(f'[NAME CARD: {g.get("full_name") or g["name"]}{(", " + g["handle"]) if g.get("handle") else ""}]'); who = None
                if p['who'] == who: out[-1] += ' ' + p['text']
                else: out.append(f'{p["who"]}: {p["text"]}'); who = p['who']
            return out
        L += say(self.span(th['hook']), cards=False) + ['', '[INTRO STINGER - 5 seconds of branding, no words]', '']
        prev_end = None
        for i, r in enumerate(th['body']):
            sp = self.span(r)
            if prev_end is not None and abs(sp[0] - prev_end) > 2.0: L += ['', f'[EDIT - the video jumps to another part of the conversation]', '']
            L += say(sp); prev_end = sp[1]
        L += ['', '[END SCREEN - music, no more talking]']
        return '\n'.join(L) + '\n'
