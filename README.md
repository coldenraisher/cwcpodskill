# CWC Podcast skills

The whole Create with Colden podcast pipeline in one repo: one episode folder on the NAS in, every clip, short and post
scheduled out. Four Claude Code skills, each enforcing its rules in code (exit 0 done, 2 = ask Colden, anything else =
a gate failed).

| Skill | Job | Ends with |
|---|---|---|
| [`CWC_PodCut`](skills/CWC_PodCut/SKILL.md) | raw NAS footage -> synced, camera-cut PodCut timeline in DaVinci Resolve | a LOCKED `Ep NN PodCut vN (L)` timeline |
| [`CWC_PodClips`](skills/CWC_PodClips/SKILL.md) | 3-5 long-form YouTube clips: themes -> Telegram approval -> Resolve edit -> masters -> packaging | `<episode>/Final/Clips/` + Clips Dashboard + `delivery.json` |
| [`CWC_PodReels`](skills/CWC_PodReels/SKILL.md) | 10 vertical shorts: themes -> Telegram approval -> Resolve edit -> masters -> covers + copy (being finished: delivery like PodClips) | finals + dashboard + `delivery.json` |
| [`CWC_PodRun`](skills/CWC_PodRun/SKILL.md) | **the aggregator**: runs the three above, asks for the posting window, reads everything with the Monday data, checks YouTube + Metricool calendars, one plan, one Telegram approval, uploads + schedules, then cleans Resolve and the disks | posts out + `<episode>/Final/<EpNN> Posting Plan.html` + clean drives |

```
episode folder (NAS)
   │
   ▼
/CWC_PodCut ── locked PodCut ──┬──► /CWC_PodClips ──► Final/Clips + dashboard ──┐
                               │     (Resolve baton, one Telegram listener)      ├──► /CWC_PodRun
                               └──► /CWC_PodReels ──► finals + dashboard ───────┘      1. ask Colden for the posting window
                                                                                        2. calendars (YouTube, Metricool) + Studio
                                                                                           viewer peaks + Monday data + holistic read
                                                                                        3. ONE plan -> Telegram "Schedule all"
                                                                                        4. YouTube API: every video + metadata
                                                                                           (private -> he flips, until the audit)
                                                                                        5. Metricool FB/IG/TikTok (20/month/brand,
                                                                                           IG collaborators), manual kits past it
                                                                                        6. cleanup: Resolve, local -> Trash, NAS delete
```

Weekly rhythm (Colden 2026-10-03): live show Thursday, run Thursday night, posts go out Friday through the following
Thursday by default - the window is always asked, never assumed.

## Install (Mac)
```
git clone https://github.com/coldenraisher/cwcpodskill ~/Code/cwcpodskill
~/Code/cwcpodskill/install.sh            # symlinks each skill into ~/.claude/skills (never replaces an existing folder)
```
Then follow the "next, once per machine" lines it prints (build the Apple Vision tools, register the Telegram plugins,
restart the listener, run the doctor and the self-tests). Prerequisites per skill are in each SKILL.md.

Run: in Claude Code, `/CWC_PodRun` and give it the episode folder, e.g.
`/Volumes/Current Projects/The Creative Lens Show/Ep. 25 - 10:8`.

## Where the copies came from
`skills/CWC_PodCut`, `skills/CWC_PodClips` and `skills/CWC_PodReels` are verbatim copies of their own repos (tracked files
only, `git archive`), taken 2026-10-03:

| Skill | Upstream | Commit |
|---|---|---|
| CWC_PodCut | github.com/coldenraisher/cwcpodcutskill | `f85c83b` (2026-10-02) |
| CWC_PodClips | github.com/coldenraisher/cwcpodclipsskill | `4772be6` (2026-10-03) |
| CWC_PodReels | github.com/coldenraisher/cwcpodreelsskill | `641b424` (2026-10-02) |

Until the move to local is done, pick ONE home per skill for edits (this repo or its own repo) so the copies do not
drift; refresh a copy with `git -C <upstream clone> archive HEAD | tar -x -C skills/<name>` and update the table.

`CWC_PodRun` lives only here. Its self-test: `python3 skills/CWC_PodRun/scripts/selftest.py` (71 gates on a synthetic
episode, fake NAS and Trash included; needs only Python 3.9+).
