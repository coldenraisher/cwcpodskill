"""Library for the shorts theme file (no command line): spans, runtime, the play-order assembly.

themes.json (written by Claude, checked by check.py) points at PHRASE IDS of phrases.json, never at seconds:
  {"brief": "<id of data/shorts/packaging_brief.md - READ it first: titles and hooks come FROM its WIN patterns>",
   "themes": [{
    "id": "s01", "slug": "dji-app-nobody-asked-for", "title": "One Guy Built The App DJI Wouldn't",   (<= 60 chars; the timeline / file name)
    "hook_text": ["ONE GUY BUILT", "THE APP DJI WOULDN'T"],   on-screen hook, 1-2 lines, <= 24 characters each
    "summary": "one sentence: what the short is",
    "hook": {"quote": "<the first words heard, verbatim>"},           must open the FIRST range
    "ranges": [{"from": "P0412", "to": "P0418", "why": "the claim"}, {"from": "P0890", "to": "P0893", "end_word": 6, "why": "payoff"}],
              PLAY order; a range may open / close on a word inside its edge phrase (start_word / end_word = index in phrase.w)
    "payoff": {"from": "P0893", "to": "P0893", "quote": "<verbatim>"},  the end of the LAST range (the short ends cold on it)
    "scores": {dim: {"s": 0-5, "why": "...", "evidence": [ids]}},  the eight dims of references/rubric.json
    "news": {...} | null, "claims": [...] | "claims_note": "...", "shares": [{"at": "12:34", "what": "...", "integral": true}],
    "broll": ["3-4 concrete b-roll ideas"] | "broll_waiver": "<why none>",
    "dest": "cwc" | "tcl" | "both" | "todd",   the SUGGESTED destination (Colden picks on the edit card)
    "cover": {"emotion": "smile", "who": "Colden"},   optional
    "trims": [{"phrase": "P0414", "words": [0, 2], "why": "false start"}],   optional, audio-gap gated in the edit
    "length_note": "why it needs > 45 s"   (only when the estimate is over 45 s)
    "learned": [{"id": "S-named", "how": "the FX3 is named in the title and the hook"}, ...2+],   brief pattern ids that shaped title / hook_text
    "explore": {"title": "why a LOSE pattern is tested here"}   (only when title / hook_text carries a LOSE pattern)
  }], "rejected": [{"idea": "...", "why": "..."}], "episode_note": "..."}"""
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
    def theme(self, tid):
        th = next((t for t in self.themes()['themes'] if t['id'] == tid), None)
        if not th: C.fail(f'no theme {tid}')
        return th
    def span(self, r):
        """{'from','to', start_word?, end_word?} -> [start, end] on the cut clock (raises KeyError / ValueError / IndexError)"""
        a = self.by[r['from']]; b = self.by[r['to']]
        s = a['w'][r['start_word']][1] if r.get('start_word') is not None else a['start']
        e = b['w'][r['end_word']][2] if r.get('end_word') is not None else b['end']
        if e <= s: raise ValueError(f'{r["from"]}..{r["to"]} runs backwards')
        return [s, e]
    def words(self, sp):
        """every word of every speaker inside a span, in time order: (who, text, start, end, phrase id)"""
        out = []
        for p in self.ph:
            if p['end'] < sp[0] - 0.01 or p['start'] > sp[1] + 0.01: continue
            for t, a, b in p['w']:
                if sp[0] - 0.01 <= (a + b) / 2 <= sp[1] + 0.01: out.append((p['who'], t, a, b, p['id']))
        return sorted(out, key=lambda x: x[2])
    def text(self, r): return ' '.join(w[1] for w in self.words(self.span(r)))
    def spoken(self, r, who):
        """the words ONE speaker says inside a range, as (token, word start, word end) - quotes are matched on these, so a
        listener's 'yeah' inside the line never breaks a verbatim quote"""
        out = []
        for w in self.words(self.span(r)):
            if w[0] == who: out += [(t, w[2], w[3]) for t in C.norm(w[1])]
        return out
    def quote_end(self, r, who, quote):
        """end time of the LAST verbatim occurrence of `quote` in what `who` says inside range r, or None"""
        tk = self.spoken(r, who); q = C.norm(quote); n = len(q); hit = None
        for i in range(len(tk) - n + 1):
            if [x[0] for x in tk[i:i + n]] == q: hit = tk[i + n - 1][2]
        return hit
    def dead_air(self, sp):
        cfg = self.R['dead_air']; cut = 0.0; end = sp[0]
        for w in self.words(sp):
            gap = w[2] - end
            if gap > cfg['over'] and not any(s['start'] < w[2] and s['end'] > end for s in self.ep['specials']): cut += gap - cfg['keep']
            end = max(end, w[3])
        return cut
    def runtime(self, th):
        """(raw seconds of the ranges, estimated seconds of the finished short, seconds into the short where the payoff ends)"""
        sps = [self.span(r) for r in th['ranges']]; raw = sum(b - a for a, b in sps)
        est = raw - sum(self.dead_air(s) for s in sps)
        return raw, est, est
    def spans(self, th): return [self.span(r) for r in th['ranges']]
    def shares(self, th):
        tot = {}
        for sp in self.spans(th):
            for w in self.words(sp): tot[w[0]] = tot.get(w[0], 0) + 1
        n = sum(tot.values()) or 1; return {k: round(100 * v / n) for k, v in sorted(tot.items(), key=lambda kv: -kv[1])}
    def specials_in(self, th):
        out = []
        for s in self.ep['specials']:
            ov = sum(max(0.0, min(b, s['end']) - max(a, s['start'])) for a, b in self.spans(th))
            if ov >= 2.0: out.append(dict(s, overlap=round(ov, 1)))
        return out
    def assemble(self, th):
        """the short as a viewer gets it - no timecodes, ids or scores: the on-screen hook, then each PHRASE in play order
        (a listener's 'yeah' over the talker is its own short line, never splitting the talker's sentence)"""
        L = [f'[ON-SCREEN TEXT for the first 2.5 seconds: "{" / ".join(th.get("hook_text") or [])}"]', '']
        guests = {p['name']: p for p in self.ep.get('people', []) if not p.get('host')}; carded = set(); prev_end = None; who = None
        for r in th['ranges']:
            sp = self.span(r)
            if prev_end is not None and abs(sp[0] - prev_end) > 1.5: L += ['', '[EDIT - the video jumps to another moment of the conversation]', '']; who = None
            seen = set()
            for p in sorted(self.ph, key=lambda p: (p['start'], p['end'])):
                ws = [w for w in p['w'] if sp[0] - 0.01 <= (w[1] + w[2]) / 2 <= sp[1] + 0.01]
                if not ws: continue
                for n, s in enumerate(self.ep['specials']):
                    if n not in seen and s['start'] <= ws[-1][2] and ws[0][1] <= s['end']:
                        seen.add(n); d = next((x for x in th.get('shares', []) if s['start'] - 1 <= C.parse_tc(x.get('at', '-99')) <= s['end'] + 1), None)
                        L.append(f'[ON SCREEN: {d["what"]}]' if d and d.get('integral') else '[the hosts look at something on their screen that the viewer is NOT shown]'); who = None
                if p['who'] in guests and p['who'] not in carded and len(ws) >= 3:
                    g = guests[p['who']]; carded.add(p['who']); L.append(f'[NAME CARD: {g.get("full_name") or g["name"]}{(", " + g["handle"]) if g.get("handle") else ""}]'); who = None
                t = ' '.join(w[0] for w in ws)
                if p['who'] == who: L[-1] += ' ' + t
                else: L.append(f'{p["who"]}: {t}'); who = p['who']
            prev_end = sp[1]
        L += ['', '[THE SHORT ENDS HERE]']
        return '\n'.join(L) + '\n'
