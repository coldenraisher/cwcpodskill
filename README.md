# CWC_PodRun

The aggregator of the Create with Colden podcast pipeline: one episode folder on the NAS in, every clip, short and post
scheduled out, the disks cleaned. A Claude Code skill that enforces its rules in code (exit 0 done, 2 = ask Colden,
anything else = a gate failed). The instructions are in [SKILL.md](SKILL.md).

```
episode folder (NAS)
   │
   ▼
/CWC_PodCut ── locked PodCut ──┬──► /CWC_PodClips ──► Final/Clips + dashboard ──┐
                               │     (one skill in Resolve at a time)            ├──► /CWC_PodRun
                               └──► /CWC_PodReels ──► Final/Reels + dashboard ──┘      posting window (asked) -> calendars +
                                                                                        fresh data -> ONE plan -> Telegram
                                                                                        "Schedule all" -> YouTube API +
                                                                                        Metricool -> cleanup
```

This repo holds CWC_PodRun only (Colden 2026-10-03). The three skills it runs live in their own repos and are installed
as their own folders in `~/.claude/skills`:

| Skill | Repo |
|---|---|
| CWC_PodCut | github.com/coldenraisher/cwcpodcutskill |
| CWC_PodClips | github.com/coldenraisher/cwcpodclipsskill |
| CWC_PodReels | github.com/coldenraisher/cwcpodreelsskill |

## Install (Mac)
```
git clone https://github.com/coldenraisher/cwcpodskill ~/.claude/skills/CWC_PodRun
python3 ~/.claude/skills/CWC_PodRun/scripts/selftest.py            # every gate, on fixtures copied from real records
python3 ~/.claude/skills/CWC_PodRun/scripts/tg_plan.py install     # the plan-card plugin of CWC_PodClips' Telegram listener
python3 ~/.claude/skills/CWC_PodClips/scripts/tg_listen.py stop; python3 ~/.claude/skills/CWC_PodClips/scripts/tg_listen.py start
```
Run: in Claude Code, `/CWC_PodRun` with the episode folder, e.g.
`/Volumes/Current Projects/The Creative Lens Show/Ep. 25 - 10:8`.
