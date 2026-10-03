# The theme rubric (proposed 2026-10-01; Colden the same day: "Approved")

Machine copy: `rubric.json` (check.py reads it). Change both together, then run `scripts/selftest.py`.

A theme is scored 0-5 on nine things. Each score needs a written reason; three of them need ids of real videos.

| Dimension | Weight | Floor | 5 looks like | 1 looks like | Evidence the gate checks |
|---|---|---|---|---|---|
| Hook | 3 | 3 | a verbatim hot take / claim a stranger stops for, 14.5 s at most (it is the cold open: 15 s in the edit, ruling 32), clear with zero context | needs the previous minute to make sense | the quote is in the transcript; capped by the cold reader |
| Payoff | 3 | 3 | a verdict, number or decision that answers the hook exactly | trails off / changes subject | the quote is the end of the last range; capped by the cold reader |
| Story | 3 | 3 | one through-line, a turn every 60-90 s, every range moves it forward | a topic, not a story | reason only (judgement) |
| Package | 3 | 3 | title + one thumbnail image are obvious and specific: product, person, price, conflict | a vague topic | a thumbnail idea must be written |
| Channel fit | 2 | - | same lane as videos that worked on the channel | a lane the data says to avoid | score 3+ cites ids from the channel data |
| Platform | 2 | - | recent videos on the topic at 2x+ their channel's median | nobody is over-performing on it | score 3+ cites ids from evidence.py; 4+ needs a 2x outlier |
| Timeliness | 2 | - | this week's news, a launch or rumor still unfolding | evergreen | score 4+ needs a dated source; ranks first |
| Self-contained | 2 | 3 | a stranger misses nothing | "like we said earlier" | capped by the cold reader |
| Footage | 1 | - | presentable cameras, the screen share exists as a file | a static shot, the thing discussed cannot be shown | screen shares in the clip are declared |

Total = sum(weight x score) / 105 x 100. **Pass line 70.** Floors: a theme under 3 on hook, payoff, story, package or
self-contained is held whatever its total.

Why these weights: CTR is decided by the package and the first seconds (hook); retention by the story and by whether
the ending pays the hook off. Those four carry 12 of the 21 weight points. The two data dimensions (channel, platform)
keep the selection honest about what has actually worked. Timeliness is a moderate weight in the score because it is
already a hard priority in the RANKING ("always gets priority"): a news theme that passes goes ahead of every evergreen
theme. Footage is last: a great story with an average picture still beats a pretty nothing.

Ranking and delivery: passing themes, news first, then by total. The best 5 that keep every clip's shared footage at
10 % or less are delivered; the next ones are runner-ups (sent one at a time when he kills a theme); fewer than 3 = the
manual-review flag.

What the first data says (Ep 23, `data/learnings.md`) - use it, do not worship it (8 clips):
- hardware news with a Colden hook: 4-8.6 K views, 35-48 % viewed. Opinion / AI-ethics talk: 100-350 views.
- the shortest clip (5:56, one "why would X do Y" question) held best; the 12-minute grab-bags held worst.
- "kept at 30 s" ran 0.45-0.70: the cold open + stinger is where a third to half of the viewers go.

## Soft line 55 (ruling 21, 2026-10-01)
"you can soften scoring and send the best themes. most will be for TCL but I would like something going on my channel."
When fewer than 3 themes reach 70, themes from 55 up are delivered too (best first, 5 at most), marked SOFT PASS; the
floors and the cold read still apply. Every card carries a suggested channel and the best theme for Colden's own
channel is always marked for it. Fewer than 3 even then = `tg_themes.py flag`, never padding.
