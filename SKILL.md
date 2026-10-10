---
name: CWC_PodRun
description: The CWC podcast aggregator - one episode folder on the NAS to every clip and reel posted and the disks cleaned. Runs /CWC_PodCut until the cut is locked, then /CWC_PodClips and /CWC_PodReels in tandem (one skill in Resolve at a time, enforced in each skill's rs.py; one Telegram listener), asks Colden for the posting window, reads every finished product with the Monday channel data, checks YouTube and both Metricool calendars, builds ONE posting plan for ONE Telegram approval, puts every clip and Short on YouTube with all its metadata (the API uploads, or Colden uploads and the API packages), schedules Facebook / Instagram / TikTok through Metricool within each account's 20-post month with the right Instagram collaborators, runs a detached go-live watch (comments at go-live, pin / related-video / cover alerts), and ends by sweeping Resolve, the local drive and the NAS. Use when Colden says "pod run", "/CWC_PodRun", "run the episode", "process Ep NN", "take this episode to posting", or gives an episode folder of The Creative Lens or Colden and Todd and wants it done end to end; also to resume a run or ask where an episode stands.
---

# CWC_PodRun

**v0.4 (2026-10-09)** - after Ep 24, Colden & Todd 10-6 and Ep 25 ran for real. Every rule is a decision Colden made; his
words, dated, are in `references/rulings.md` (read it when a rule is in question - never from memory). Every rule a
machine can measure is a GATE in code; `selftest.py` proves 120 of them. Exit codes everywhere: **0 done - 2 STOP AND
ASK COLDEN - anything else a gate failed** (read it, fix the cause, never work around it or re-run to get past it).
Not covered by a rule: STOP AND ASK. **DO NOT ASSUME** (his words).

## START HERE - every time
```
S=~/.claude/skills/CWC_PodRun/scripts
python3 $S/next.py "<RUN>"            # where the whole pipeline stands + the next step (run it often; exits 0, gates nothing)
python3 $S/watch.py status            # the go-live watch daemon (must be RUNNING from the first upload to the cleanup)
python3 $S/youtube.py route           # how videos reach YouTube (settled: publish_at_works - publishAt at upload)
```
RUN = `~/Documents/Claude/Projects/Create with Colden/CWC Podcast/run/<show>/<EpNN>/`. New episode: step 1 below.
Resume: `next.py` + the RUN's `STATE.md` (write it before any long wait or /compact: stage, what waits on him, next command).

## The rules (one line each; the words behind each one: references/rulings.md, numbered the same)
1. Flow: PodCut locked -> clips + reels in tandem -> the holistic read with the Monday data -> ONE plan -> ONE tap -> post -> clean up.
2. The posting window is ASKED at kickoff (default proposal Fri -> Thu), and the calendar is read before any cadence.
3. YouTube = the Data API for every clip and Short, all metadata included; never through Metricool. Monetization ON (@ColdenRaisher).
4. 48 h priority only when the SAME product goes on both: CWC first, TCL >= 48 h later. TCL-only: no delay. Clips and reels alike.
5. Instagram collaborators = who SPEAKS in the reel (a phrase of >= 3 words), Colden excluded; ONE set per reel, on the CWC post when it plays on both.
6. FB / IG / TikTok only through Metricool; CWC and TCL have their own accounts, 20 posts a month each (resets on the 1st, counted from the Metricool calendar), manual kits past the cap unless he says "all through Metricool" (ruling 14); TCL has no Facebook.
7. Clip times from FRESH data: 30 min before that weekday's Studio viewer peak (<= 24 h old); 2 PM only for a channel with no data, flagged.
8. Cleanup is the last step: NAS hard delete, local files to the Trash, Resolve timelines exported as .drt first - on his "Clean up" tap.
9. The full episode stays the live stream (never uploaded here); reviews on Telegram; data = the Monday scrape (`channel_metrics.json`).
10. This repo holds CWC_PodRun only; CWC_PodReels' delivery is built by its own session; the Resolve baton is checked inside each skill's `rs.py`.
11. Colden may upload every YouTube video himself (`intake.py --colden-uploads "<his words>"`, per run): the API then only packages + schedules (`youtube.py adopt`); `youtube.py upload` refuses. Never two clips on one channel on one day; two Shorts a day is fine.
12. His own Short slots (`holistic.json short_slots`) replace the best-time search for that brand; reels fill them in rank order, never on a same-topic clip day.
13. The plan card = two calendar graphics (CWC, TCL) + a short text with the buttons.
15. The full-episode link by id (`intake.py --full-episode <cwc id> <tcl id> "<his words>"`), never the one with the phone emoji.
16. The go-live watch is CODE, not memory: `watch.py` (a detached daemon) posts the comment at go-live and QUEUES every browser job (PIN, Related video) in `~/.config/cwc/podrun_todo.jsonl` for the conducting session, which keeps a Monitor on that file and does the job with the Chrome MCP (2026-10-09: "daemon should tell claude to pin with chrome MCP"); Telegram gets the line only as a fallback (a pin still open 15 min after the comment, a related video < 12 h from its slot). `next.py` puts GO-LIVE WATCH NOT RUNNING first until it runs. Related videos and monetization are set BEFORE go-live (private is fine), right after adopt --apply.
17. (2026-10-09) The model renders the AI headline (never typeset by code); cold reads run on Sonnet; a Colden and Todd reel goes to CWC or is killed; clip thumbnail headlines are 2-5 words, 3 the target.
Carried from the sub-skills: one long-form per channel per day (lives count); news first then push_order; no short on a channel + day with a same-topic clip (>= 5 s shared on the locked cut); read Studio's scheduled queue first; each master only on its own channel; end screens and related videos link only PUBLIC videos; a reel with no CWC / TCL destination is listed, never posted; one YouTube category per channel (Film & Animation).

## SAFETY RULES
1. **Nothing is uploaded, scheduled or deleted before Colden's tap on the CURRENT card** (plan: "Schedule all"; cleanup: "Clean up"); each approval is bound to a sha; a rebuild needs a new card. **And the tap posts only with his posting yes from KICKOFF on file** (`run.json post_ok`): asked in chat with the window while he is at the computer, never hours later; `youtube.py upload / adopt --apply` and `metricool.py payloads` refuse without it. A refused post is alerted on Telegram with the exact command - never worked around.
2. **The other three skills are read-only from here** - this skill runs their scripts and reads their files; a change to one of them is that skill's job.
3. **Resolve is Colden's workspace**: the sub-skills ask before Resolve work unless intake recorded a `--resolve-window`; in the tandem run the BATON (`baton.py`) is taken around every Resolve sequence; the cleanup sweep asks too.
4. **One Telegram listener** (CWC_PodClips' `tg_listen.py`); this skill is its plugin (`tg_plan.py install`, then restart the listener). Never a second poller.
5. **Never** touch a public video, send YouTube through Metricool, post the full episode, post Facebook for TCL, put collaborators on two posts of one reel, guess an Instagram handle, or delete a source, a final, a delivered file or anything a timeline uses.
6. **Every write is logged before the next one** (`publish_log.json`, `data/metricool_ledger.jsonl`, `cleanup/done.json`): a crash never double-posts; a re-run finishes what is missing.
7. **The self-test never touches the real Resolve, Telegram, YouTube or Metricool**; never run `baton.py open / take` by hand outside a tandem run.

## THE RUN, in order (S = this skill's scripts, R = the RUN folder)
```
# 1 kickoff - Colden is in the session: ask the posting window (the proposal intake prints, or his span) AND in the same
#   breath the posting yes ("When you tap Schedule all on the plan card, may I post everything on it - including the
#   YouTube uploads on later days - without asking you here again?"), whether he uploads the YouTube videos himself,
#   and the Resolve window. ONE question, all four parts.
python3 $S/intake.py "<episode folder>" --window <start> <end> --by "<his words>" --post-ok "<his words>" [--resolve-window ".."] [--colden-uploads ".."] [--metricool-all ".."] [--full-episode <cwc id> <tcl id> ".."]
# 2 the cut: /CWC_PodCut (prep.py -> LOOK -> ack.py -> build.py; auto-lock)                    -> next.py: "PodCut locked"
# 3 clips + reels in tandem (section below): baton.py open "$R" first                        -> next.py: both "delivered"
python3 $S/baton.py close
# 4 the window again only if it has started or he never gave one:  window.py ask "$R"   (Telegram: Use this / Change)
# 5 the calendar + fresh data (the plan refuses anything stale)
python3 $S/cal.py youtube "$R"                                  # both channels: scheduled + last 21 days (API)
#   Metricool per brand ON ITS OWN CONNECTOR (cwc = the claude.ai Metricool connector, 5965295; tcl = metricool-tcl, 6367106):
#   getScheduledPosts(brandId, fromDate = the 1st of the window's first month, toDate = the end of its last month, timezone
#   America/New_York) -> save the answer verbatim -> cal.py metricool "$R" <cwc|tcl> <file> --from YYYY-MM-01 --to YYYY-MM-DD
#   getBestTimeToPostByNetwork(brandId, "tiktok", the coming week) -> save verbatim -> cal.py besttimes "$R" <cwc|tcl> <file>
#   Claude in Chrome, per brand: the Metricool planner in MONTH view for every month the window touches -> screenshot ->
#   count every post that month (published + scheduled) -> cal.py counts "$R" <cwc|tcl> YYYY-MM=<n> --evidence <png>
#   Claude in Chrome, per channel: studio.youtube.com/channel/<id>/analytics/tab-build_audience/period-default (check the
#   channel - never the old gymnastics one) -> run scripts/studio_viewers_online.js -> save -> cal.py peaks "$R" <cwc|tcl> <file>
python3 $S/cal.py show "$R"
# 6 the holistic read (below) -> R/holistic.json, then
python3 $S/plan.py build "$R"  ;  python3 $S/tg_plan.py send "$R"          # ONE card: Schedule all / Changes
#   Changes -> his message lands in run.json plan_notes_open -> change the INPUTS (holistic.json, window, counts) -> build -> send
# 7 after "PLAN APPROVED" - the same minute:
python3 $S/watch.py start                # THE GO-LIVE WATCH (daemon): adopts his uploads / uploads on quota days, posts the
#                                          comment at go-live, alerts PIN / related / refused cover / monetization. Stays up to the cleanup.
python3 $S/metricool.py upload "$R"      # reel video + cover -> Drive direct links
python3 $S/metricool.py payloads "$R"    # per call: createScheduledPost(blogId, date, info) on ITS connector ->
python3 $S/metricool.py record "$R" <item id> <answer file>                 #   record it BEFORE the next call
python3 $S/kit.py "$R"                   # Final/Manual Posts/ for posts over the cap (none with --metricool-all)
#   YouTube: run.json colden_uploads -> HE uploads (private, not scheduled, title = the file name); the watch runs
#   youtube.py adopt + adopt --apply every 5 min (metadata, publishAt, thumbnail, captions, playlists, shorts_pkg) and
#   tells him each match on Telegram. Otherwise the watch runs youtube.py upload --alert after 03:10 ET each quota day.
#   By hand / Chrome, as soon as a video is up (next.py lists each one): related.py due -> Studio -> related.py mark;
#   monetization ON (@ColdenRaisher) -> pin.py mark ... monetization; clips: Test & Compare + end screen -> pin.py mark.
#   At go-live the watch posts the comment and QUEUES the pin: keep  tail -n 0 -F ~/.config/cwc/podrun_todo.jsonl  as a Monitor in this
#   session -> a "pin" line = Chrome MCP: youtube.com as that channel -> the comment's menu -> Pin -> pin.py mark ... pinned;
#   a "related" line = Studio's Related video -> related.py mark. Telegram gets the line only if nobody did it (15 min / 12 h).
python3 $S/youtube.py checklist "$R"  ;  python3 $S/youtube.py verify "$R"  ;  python3 $S/dashboard.py "$R"
python3 $S/tg_plan.py wrapup "$R"
# 8 cleanup - the last step, after every post is handled and live.
python3 $S/cleanup.py scan "$R"  ;  python3 $S/cleanup.py card "$R"         # Resolve open on the project (or scan --no-resolve)
python3 $S/cleanup.py apply "$R"                                            # after his "Clean up" tap; then watch.py keeps going for other runs
```

## 3. The tandem run - CWC_PodClips + CWC_PodReels at the same time
Both start the moment the PodCut is locked, on the same locked cut. First `python3 $S/baton.py open "$R"`: from then on
`rs.py` of CWC_PodClips, CWC_PodReels and this skill refuses every Resolve call (exit 4) of a skill that does not hold
the baton. Run each skill as a **background agent** (Agent tool, `run_in_background: true`).
**ONE WORKER PER SKILL PER STAGE, never one worker for the whole skill** (2026-10-09: four workers carried ~500k-token
contexts across ~4,000 turns = ~2 billion context tokens on one episode). A worker STOPS when its stage's cards are out
or its stage is delivered, writes the skill's STATE, and returns a 5-line status; the main session spawns a FRESH worker
for the next stage on the next tap. Workers use the model the session runs on unless Colden names a cheaper one for
Stage 1 cold reads. The brief for each:
```
You are the <CWC_PodClips | CWC_PodReels> worker of CWC_PodRun for <show> <EpNN>, STAGE <n> only. PodCut CACHE = <podcut_cache>.
Load the skill with the Skill tool (<CWC_PodClips | CWC_PodReels>) and follow its SKILL.md from its START HERE, for this stage.
Resolve: a tandem run is open - your rs.py refuses every call unless you hold the baton. Before EVERY Resolve sequence
(build, preview render, master render, cover render, template, lock):
  python3 ~/.claude/skills/CWC_PodRun/scripts/baton.py take <skill> "<what>"   - exit 4 = the other skill is in Resolve:
do non-Resolve work (data, themes, cold reads, b-roll research, covers, copy, packaging) and try again; give it back right
after:  baton.py give <skill>.  Resolve window from Colden: <his words | none: ask as your skill says>.
STOP when this stage's cards are all out, or the stage is delivered (finals + dashboard in the episode's Final folder,
delivery.json). Do NOT run any posting step. Never read an image twice; read a contact sheet, not single frames, when the
skill offers one. Return a 5-line status: stage, what waits on Colden, the exact next command. Never claim a look you did
not take; never work around a gate.
```
The main session watches both event logs with ONE Monitor filtered to the actionable lines only (`tail -n 0 -F "<clips
WORK>/review/events.log" "<reels WORK>/review/events.log" | grep --line-buffered -E "APPROVED|KILLED|NOTES|CHANGES|DELIVERED|FAILED"`),
spawns the next stage's worker when a tap lands, runs `next.py "$R"` after each report and answers the questions workers
return. Both delivered: `baton.py close`. A baton older than 3 h is stale and only taken over with Colden's words.

## 6. The holistic read -> `holistic.json`
1. Every product as a whole: the clips (titles A/B/C, hooks, push order, news, channels) and the reels (titles, hooks,
   destinations, rank), where they repeat each other. The two dashboards in `<episode>/Final/Clips` and `Final/Reels`.
2. The Monday scrape: `working_now`, `avoid`, `insights`, `shorts`, `audience.best_slots_et`, `trend_vs_last_week`, `tcl` - and `data/shorts/summary.md`.
3. What is already on the calendar (`cal.py show`) and the month counts.
4. Write `R/holistic.json`: `{"summary": "..", "overrides": [{"ref": "s04", "kind": "short", "rank": 1, "why": ".."}, {"ref": "t03", "kind": "clip",
   "push_order": 1, "why": ".."}], "hold": [{"ref": "s06", "kind": "short", "why": ".."}], "notes": [".."], "short_slots": {"cwc": {"at": [..], "by": "<his words>"}}}`
   - `rank` / `push_order` are 1-based places; every `why` names the data point (>= 25 characters, gated); a hold leaves a
   product out of this window. No overrides is a valid read - say so in the summary.

## What the plan decides (plan.py; numbers in references/rules.json)
- **Window**: only the one Colden confirmed; never one that started before today.
- **Clips** (YouTube): CWC spread over the window, news first then push_order; one long-form per channel per day including
  what is on YouTube already; time = 30 min before that weekday's viewer peak; the same clip on TCL >= 48 h after CWC,
  spill <= 3 days past the window flagged; TCL-only: no delay.
- **Reels**: per brand in rank order (or his slots), one a day, then second posts on the best days >= 3 h apart at the
  brand's best TikTok hour; TCL >= 48 h after CWC for a shared reel; never on a channel + day with a same-topic clip.
  A reel = a YouTube Short (its `yt_title`, the caption as description, the caption's hashtags as tags, the channel's
  category, the brand's playlist, the picked cover) + ONE Metricool post (every network of that brand in one post).
- **Collaborators**: from measured speakers; handles from references/collaborators.json (+ PodReels' show file); a speaker without one = ask.
- **Routes**: YouTube `youtube_api` with `publishAt`; Metricool while the confirmed month count is under 20 (or --metricool-all), else `manual`.
- **Quota**: units per item (adopt ~150-550, upload ~1,700-2,150) over Pacific days from today, shared with other approved runs in go-live order; each item must be ready `upload_lead_minutes` before its slot or the plan asks.

## Gates (selftest.py proves each - run it after ANY change)
| Rule | Gate |
|---|---|
| The window is his; the posting yes from kickoff | plan.py exit 2 without a confirmed window or one that started; upload / adopt --apply / payloads refuse without post_ok |
| The YouTube route is settled | plan.py exit 2 until `youtube.py route` is settled; upload refuses a plan built for another route |
| Finished products only; the real record shapes | PodClips' delivery.json newer than its lock.json; PodReels' delivery.json with `final_dir` + `delivered_at`; categories / playlists from the v2 objects, never a default |
| The holistic read happened | holistic.json newer than both deliveries; every override / hold names a real product with a data reason |
| Calendar + fresh data | youtube.json + metricool_<brand>.json <= 6 h; peaks <= 24 h; month counts confirmed <= 12 h and never below what Metricool lists; scrape <= 8 days (2, or --waive-scrape) |
| Files exist, right channel | exit 2 for a missing master / thumbnail; a clip master only on its stinger's channel; every API call checked against the brand's channel id |
| Never the full episode, YouTube in Metricool, FB on TCL; one long-form a day; 48 h; same topic apart; lead time; caps; weekdays | validate() on the finished plan; metricool.py payloads |
| Collaborators | from measured speakers; a missing handle = exit 2; one set per reel, never on TCL when the reel is on CWC |
| One approval each | plan + cleanup approvals bound to a sha; a tap on a replaced card changes nothing |
| Never twice, never half-done, never a false "scheduled" | publish_log.json before each send; a video is handled only with its thumbnail / captions / playlists (`complete`); `record` refuses a connector error or a second record |
| A thumbnail YouTube can take; a refused one is never silent | ytapi.thumb_file re-encodes any cover over 2 MB to a JPEG under it; a refusal keeps the item incomplete, alerts Colden once, and clears only with the file fixed or `pin.py mark ... cover` |
| Metadata only on a processed upload | adopt --apply skips a video whose uploadStatus is not `processed` |
| Never a second copy; never a guess | upload checks the channel for his own upload of the file first; adopt matches exactly one private video by name + length, lists the rest |
| The comment at go-live; PIN / related told at once | watch.py daemon (heartbeat <= 15 min) = the gate next.py checks; pin.py due posts once (publish_log first), `--alert-pins` one Telegram line per PIN; related.py due exit 3 while a Short links wrong, `--alert` one line per Short within 12 h of its slot |
| Cleanup keeps what matters | only after every post is handled; keep set re-checked at apply; NAS media folders need a Resolve listing; another episode's #recycle folder untouched |
| Resolve, one skill at a time | `rs.py` of each skill: exit 4 unless its skill holds the baton while a baton file exists; stale > 3 h only with his words |
NOT gated (know it): the holistic read's judgement; monetization, the PIN, the Related video field, Test & Compare and end
screens are browser work (the API has no field) - the watch only makes sure you are told; the Studio peak read and the
month-count screenshot are a look, the numbers typed from it are not checked; a worker that never calls a Resolve script
is not stopped by the baton.

## Definition of done - `next.py` reads the same files
- [ ] PodCut locked; CWC_PodClips and CWC_PodReels delivered (finals + dashboards in `<episode>/Final`, delivery.json); `baton.py close`
- [ ] the window confirmed; calendar, peaks and month counts fresh; holistic.json written after both deliveries
- [ ] plan.py exit 0; the card sent; "Schedule all" on the current sha; `watch.py status` RUNNING
- [ ] every YouTube item up AND complete; every `metricool` item recorded with its plannerUrl; every `manual` item has its kit
- [ ] every uploaded Short has its Related video recorded; every live video its pinned comment; every CWC video monetization; every clip its A/B/C + end screen (`pin.py status`)
- [ ] the Studio checklist written; verify + dashboard rebuilt; the wrap-up sent
- [ ] cleanup: scan -> card -> his tap -> apply; `cleanup/done.json` lists every NAS delete and every file in the Trash

## Files
`scripts/` common.py intake.py window.py next.py baton.py cal.py ytapi.py plan.py plan_cal.py tg.py tg_plan.py metricool.py
youtube.py shorts_pkg.py kit.py dashboard.py cleanup.py pin.py related.py watch.py rs.py r_sweep.py studio_viewers_online.js
selftest.py - `references/` rules.json brands.json collaborators.json podreels_handoff.md rulings.md (his words + history).
RUN folder: run.json, events.log, STATE.md, calendar/, holistic.json, plan.json + plan.md, plan_cal_<brand>.png, publish/
(drive_links, metricool_payloads, adopt_map, shorts_package, srt/, related.json, youtube_status, studio_checklist.md),
publish_log.json, cleanup/. Shared: `<CWC Podcast>/data/` youtube_route.json, quota.json (one pool with CWC_PodClips),
thumbs/ (re-encoded covers), metricool_ledger.jsonl; `~/.config/cwc/` resolve_baton.json (tandem runs only),
listen_plugins.json, podrun_watch.{pid,json,log}. Both the watch and the Telegram listener run as LaunchAgents since 2026-10-10 (com.coldenraisher.cwc-podrun-watch,
com.coldenraisher.cwc-telegram-listener: KeepAlive, back after a reboot or a crash) - never start either by hand (a second
poller steals taps); after a code change: launchctl kickstart -k gui/$(id -u)/<label>. `watch.py install` rewrites the plists.
Repo: github.com/coldenraisher/cwcpodskill (private, branch `main`). Commit + push every change. The other three skills
live in their own repos (cwcpodcutskill, cwcpodclipsskill, cwcpodreelsskill).

## Open items (ask Colden) - the long list with history: references/rulings.md
- The PIN itself needs a browser (no API): today Claude in Chrome or Colden from the Telegram line. A Playwright pin on a
  logged-in Chrome profile would make it automatic - his call.
- Collaborators: @createwithcolden on a TCL post where Colden speaks (today: never); Instagram's collaborator limit (3 on file) unverified.
- Month count from the API instead of a screenshot (getScheduledPosts listed a published post on 2026-10-03) - his ruling (the screenshot) stands.
- Cleanup: confirm every time (today), or automatic once trusted? Where Resolve's cache / proxy / optimized media live.
