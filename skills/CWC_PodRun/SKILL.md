---
name: CWC_PodRun
description: The CWC podcast aggregator - one episode folder on the NAS to every clip and reel posted and the disks cleaned. Runs /CWC_PodCut until the cut is locked, then /CWC_PodClips and /CWC_PodReels in tandem (shared Resolve baton, one Telegram listener), asks Colden for the posting window, reads every finished product with the Monday channel data, checks YouTube and both Metricool calendars, builds ONE posting plan for ONE Telegram approval, uploads every video to YouTube through the API (private until he flips it while the audit is pending), schedules Facebook / Instagram / TikTok through Metricool within each account's 20-post month with the right Instagram collaborators, makes manual kits past the cap, and ends by sweeping Resolve, the local drive and the NAS. Use when Colden says "pod run", "/CWC_PodRun", "run the episode", "process Ep NN", "take this episode to posting", or gives an episode folder of The Creative Lens / Colden and Todd and wants it done end to end; also to resume a run or ask where an episode stands.
---

# CWC_PodRun

**v0.2 (2026-10-03)** - built from Colden's flow and his answers of 2026-10-03 plus the hand-off contracts the three
pipeline skills define (`CWC_PodClips/references/aggregator_handoff.md`, CWC_PodReels' publishing cadence).
`selftest.py` proves 71 gates on a synthetic episode. NOT yet run on a real episode - the first run is the pilot.

## START HERE - every time
```
S=~/.claude/skills/CWC_PodRun/scripts
python3 $S/intake.py "<episode folder>" [--window YYYY-MM-DD YYYY-MM-DD --by "<his words>"] [--resolve-window "<his words>"]
python3 $S/next.py "<RUN>"            # where the whole pipeline stands + the next step (run it often)
```
RUN = `~/Documents/Claude/Projects/Create with Colden/CWC Podcast/run/<show>/<EpNN>/`.
Exit codes, as the whole pipeline: **0 done - 2 STOP AND ASK COLDEN - anything else a gate failed** (read it, fix the
cause, never work around it or re-run to get past it). Not covered by a rule: STOP AND ASK. **DO NOT ASSUME** (his words).

## Colden's rulings (2026-10-03) - the source of every rule
1. **The flow.** "1. I call this skill in a code project and give you an episode folder on my NAS. 2. you send that
   folder to /cwcpodcut... That skill ends with a locked podcut timeline. 3. Once you see a locked podcut timeline, begin
   running /cwcpodclips and cwcpodreels skills at the same time... Both end my dropping final versions and a dash board in
   the NAS root folder. 4. Once clips and reels are done processing, you will take a thorough read through all the content
   holistically as well as utilizing the monday youtube and tiktok data to plan out the best cadence for these new clips."
2. **Ask for the window.** "Default can be Fri-Thurs but I think it would be best to ask for a time span first then develop
   your cadence around that and the currently scheduled clips, rather than just assume and move on. this week, for
   instance, it will already be saturday/sunday before clips get posted." Calendar first: "check youtube and metricool first
   to see what is already on the calendar". Rhythm: live show Thursday, run Thursday night, posts Friday -> Thursday.
3. **YouTube = the API, every video.** "Skill uploads to YouTube and adds in all the metadata. I flip from private to
   scheduled based on the dashboard. make sure monetization is always turned on." / "Everything gets uploaded to YouTube
   through the current API. I will just do the manual switch from private to scheduled until API clears." Thumbnails sent
   through Metricool do not carry to YouTube Shorts - YouTube never goes through Metricool. rules.json
   `youtube_audit_passed: false` = upload private, no publishAt; flip it only on his word.
4. **48 h priority, only for the same product on both.** "TCL ONLY clips have no delay. The only delay is when TCL and CWC
   BOTH post the same reel. In THAT case, CWC post gets priority always then TCL can post any time after 48 hours." Same
   for shorts: "CWC always gets a 48 hr priority over TCL shorts if the same reel goes out on both."
5. **Instagram collaborators - meticulous.** "First, you will need to determine if a collaborator is even necessary. If
   only colden talks in a clip. no collab, if guest + colden talk then guest gets added as a collab. Jake and Todd can both
   be added as collabs as well if the speak in the reel. Each reel only gets ONE set of collaborators - meaning do NOT add
   a guest collaborator to CWC channels and then also on the TCL channel 48 hours later... Collabs get priority on
   Colden's channel if the reel plays on both. If the reel only plays on TCL, add collaborators there."
6. **Metricool.** FB / IG / TikTok only through Metricool; CWC and TCL each have their own account, 20 posts a month each,
   manual after that; TCL has no Facebook. One post to all three networks "equal 1 as long as you don't make individual
   changes". "The 20 limit starts over on the first day of each month"; the month count comes from "a chrome MCP
   screenshot of the metricool calendar" (the API lists only posts not yet published).
7. **Clip timing from fresh data.** "For clip timings it might be best to pull fresh data from YouTube before determining."
8. **Clean up last.** "just sweeping resolve and the disks for extra generations or files that were saved but not used in
   the final outputs... the last step needs to be to clean up everything possible. NAS gets hard delete. Local drive files
   get moved to the trash bin where I can delete."
9. The full episode "stays as the live stream" (never uploaded here). Reviews go through Telegram. Thumbnails: Higgsfield
   (inside PodClips / PodReels). Data: `channel_metrics.json`, updated every Monday. Mac; NAS root = the episode folder.
   PodReels "is still being finished. Assume a similar delivery to PodClips." The repo backs up all four skills.

Carried rules (ruled in the skills that hand over to this one): clips ~2 PM ET when no viewer data; one long-form per
channel per day; news first then push_order; no short on top of the clip of the same topic; read Studio's scheduled queue
first ("This is a must!", 2026-09-15); each master only on its own channel; end screens link only public videos; the
full-episode link = the public "Ep. NN" upload WITHOUT the 📱; one reel a day per brand, extras on the best days >= 3 h
apart at the brand's best TikTok hour; Todd-only reels are exported, never posted.

## SAFETY RULES
1. **Nothing is uploaded, scheduled or deleted before Colden's tap on the CURRENT card** (plan: "Schedule all"; cleanup:
   "Clean up") - each approval is bound to a sha; a rebuild needs a new card.
2. **The other three skills are read-only from here** - code and state files. This skill runs their scripts and reads
   their files; a change to one of them is that skill's job (ask Colden).
3. **Resolve is Colden's workspace.** The sub-skills ask before Resolve work unless intake recorded a `--resolve-window`
   in his words; in the tandem run the BATON (`baton.py`) is taken around every Resolve sequence. The cleanup sweep asks too.
4. **One Telegram listener** (CWC_PodClips' `tg_listen.py`); this skill is its plugin (`tg_plan.py install`). Never a poller.
5. **Never** touch a public video, send YouTube through Metricool, post the full episode, post Facebook for TCL, put
   collaborators on two posts of one reel, or delete a source, a final, a delivered file or anything a timeline uses.
6. **Every write is logged before the next one** (`publish_log.json`, `data/metricool_ledger.jsonl`, `cleanup/done.json`):
   a crash never double-posts, and a re-run skips what is done.

## THE RUN, in order (S = this skill's scripts, R = the RUN folder)
```
# 1 intake - at kickoff Colden is in the session: ask the posting window (AskUserQuestion: the proposal intake prints, or his span)
python3 $S/intake.py "<episode folder>" --window <start> <end> --by "<his words>" [--resolve-window ".."]
# 2 the cut: /CWC_PodCut (prep.py -> LOOK -> ack.py -> build.py; Creative Lens auto-locks)   -> next.py: "PodCut locked"
# 3 clips + reels in tandem (below)                                                            -> next.py: both "delivered"
# 4 the window again if it has started or he never gave one:  python3 $S/window.py ask "$R"   (Telegram: Use this / Change)
#   Change -> his message lands in run.json window_notes_open -> window.py set "$R" <start> <end> --by "<his words>"
# 5 the calendar + fresh data (the plan refuses anything stale)
python3 $S/cal.py youtube "$R"                                  # both channels: scheduled + last 21 days (API)
#   Metricool per brand ON ITS OWN CONNECTOR (cwc = claude.ai Metricool, blogId 5965295; tcl = metricool-tcl, 6367106):
#   getScheduledPosts from the 1st of the window's first month to the end of its last, America/New_York -> save ->
python3 $S/cal.py metricool "$R" <cwc|tcl> <file> --from YYYY-MM-01 --to YYYY-MM-DD
#   getBestTimeToPostByNetwork socialNetwork=tiktok, the coming week -> save ->  cal.py besttimes "$R" <cwc|tcl> <file>
#   Claude in Chrome, per brand: the Metricool planner in MONTH view for every month the window touches -> screenshot ->
#   count every post that month (published + scheduled) ->  cal.py counts "$R" <cwc|tcl> YYYY-MM=<n> --evidence <png>
#   Claude in Chrome, per channel: studio.youtube.com/channel/<id>/analytics/tab-build_audience/period-default (check the
#   channel - never the old gymnastics one) -> run scripts/studio_viewers_online.js -> save ->  cal.py peaks "$R" <cwc|tcl> <file>
python3 $S/cal.py show "$R"
# 6 the holistic read (judgement - below) -> R/holistic.json, then
python3 $S/plan.py build "$R"  ;  python3 $S/tg_plan.py send "$R"          # ONE card: Schedule all / Changes
#   Changes -> his message lands in run.json plan_notes_open -> change the INPUTS (holistic.json, window, counts) -> build -> send
# 7 after "PLAN APPROVED"
python3 $S/youtube.py upload "$R"        # every clip + Short, all metadata; private (flip) until the audit passes. Quota
#                                          paces it: re-run each day until "every YouTube item is uploaded" (plan upload_day)
python3 $S/metricool.py upload "$R"      # reel video + cover -> Drive direct links
python3 $S/metricool.py payloads "$R"    # per call: createScheduledPost(blogId, date, info) on ITS connector ->
python3 $S/metricool.py record "$R" <item id> <answer file>                 #   record it BEFORE the next call
python3 $S/kit.py "$R"                   # Final/Manual Posts/ for posts over the cap (collaborators on the right post)
python3 $S/youtube.py checklist "$R"     # monetization ON + ad suitability, the flip times, Test & Compare, end screens,
#                                          pinned comments - Claude in Chrome works through it in Studio where it can
python3 $S/youtube.py verify "$R"  ;  python3 $S/dashboard.py "$R"         # read back every video; <episode>/Final/<EpNN> Posting Plan.html
python3 $S/tg_plan.py wrapup "$R"
# 8 cleanup - the last step
python3 $S/cleanup.py scan "$R"  ;  python3 $S/cleanup.py card "$R"         # Resolve open on the project (or scan --no-resolve)
python3 $S/cleanup.py apply "$R"                                            # after his "Clean up" tap
```

## 3. The tandem run - CWC_PodClips + CWC_PodReels at the same time
Both start the moment the PodCut is locked, on the same locked cut. Run each as a **background agent** (Agent tool,
`run_in_background: true`) so their long Telegram waits overlap; the main session conducts. The brief for each:
```
You are the <CWC_PodClips | CWC_PodReels> worker of CWC_PodRun for <show> <EpNN>. PodCut CACHE = <podcut_cache>.
Load the skill with the Skill tool (<CWC_PodClips | CWC_PodReels>) and follow its SKILL.md exactly, from its START HERE.
Resolve: before EVERY Resolve sequence (build, preview render, master render, cover render, template, lock) run
  python3 ~/.claude/skills/CWC_PodRun/scripts/baton.py take <skill> "<what>"   - exit 4 = the other skill is in Resolve:
do non-Resolve work (data, themes, cold reads, b-roll research, covers, copy, packaging) and try again; give it back right
after:  baton.py give <skill>.  Resolve window from Colden: <his words | none: ask as your skill says>.
STOP when your skill has DELIVERED (finals + dashboard in the episode folder, delivery.json). Do NOT run any posting step
of your own (CWC_PodReels: publish.py plan / payloads / tg_plan) - CWC_PodRun plans and posts every product together.
When everything left is waiting on Colden (cards on Telegram), return a 5-line status: stage, what waits on him, what you
do on his next tap. Never claim a look you did not take; never work around a gate.
```
The main session watches both event logs with a Monitor (`tail -n 0 -F "<clips WORK>/review/events.log" "<reels
WORK>/review/events.log"`), resumes the matching worker when a tap lands (SendMessage: "Colden answered: <line> -
continue"), runs `next.py "$R"` after each report and answers the questions workers return. No Agent tool: interleave the
two skills in this session, the baton still taken around every Resolve sequence.

## 6. The holistic read -> `holistic.json` (ruling 1)
1. Every product as a whole: the clips (titles A/B/C, hooks, push order, news, channels) and the reels (titles, hooks,
   destinations, rank), and where they repeat each other (the planner also keeps same-topic products apart by measured
   overlap on the locked cut).
2. The Monday scrape: `working_now`, `avoid`, `insights`, `shorts.youtube` + `shorts.tiktok`, `audience.best_slots_et`,
   `trend_vs_last_week`, `tcl` - and data/shorts/summary.md.
3. What is already on the calendar (`cal.py show`) and the month counts.
4. Write `R/holistic.json`: `{"summary": "what this episode has and what leads, why", "overrides": [{"ref": "s04", "kind":
   "short", "rank": 1, "why": ".."}, {"ref": "t03", "kind": "clip", "push_order": 1, "why": ".."}], "hold": [{"ref": "s06",
   "kind": "short", "why": ".."}], "notes": [".."]}` - `rank` / `push_order` are 1-based places (an override lands just ahead
   of that place); every `why` names the data point it rests on (>= 25 characters, gated); a hold leaves a product out of
   this window and shows it on the card. No overrides is a valid read - say so in the summary.

## What the plan decides (plan.py; numbers in references/rules.json)
- **Window**: only the one Colden confirmed (window.py / intake --window); never one that started before today.
- **Clips** (YouTube): CWC spread over the window, news first then push_order; one long-form per channel per day including
  what is on YouTube already (lives count); time = 30 min before that weekday's viewer peak from Studio (fresh, <= 24 h;
  2 PM only for a channel with no data, flagged); the same clip on TCL any time >= 48 h after CWC (CWC slots for shared
  clips stay early enough), spill <= 3 days past the window flagged; TCL-only: no delay.
- **Reels**: per brand in rank order, one a day, then second posts on the best days >= 3 h apart at the brand's best TikTok
  hour; the same reel on TCL >= 48 h after CWC; TCL-only: no delay; never on a channel + day with a same-topic clip.
- **Collaborators** (Instagram): everyone who SPEAKS in the reel - a phrase of >= 3 words inside its ranges (CWC_PodReels
  phrases; a "yeah" is not speaking) - except Colden; one set per reel, on the CWC post when it plays on both, else on its
  one brand; handles from references/collaborators.json (+ PodReels' show file) - a speaker without one = ask.
- **Routes**: YouTube = `youtube_api` with schedule `flip` (private, his flip) or `publishAt` (after the audit); FB + IG +
  TikTok = ONE Metricool post per reel per brand while the confirmed month count is under 20, best-ranked first; over it =
  `manual`. TCL networks: Instagram + TikTok.
- **Quota**: units per upload (~1,700 a Short, ~2,100 a clip with captions) over Pacific days from tonight; each upload must
  land at least a day before its slot or the plan asks.

## Gates (selftest.py proves each - run it after ANY change)
| Rule | Gate |
|---|---|
| The window is his | plan.py exit 2 without a confirmed window or with one that has started; window.py set needs his words |
| Finished products only | plan.py: both delivery.json files (PodClips' newer than its lock.json; PodReels' in either shape) |
| The holistic read happened | holistic.json newer than both deliveries; every override / hold names a real product with a data reason |
| Calendar + fresh data | youtube.json + metricool_<brand>.json <= 6 h; peaks <= 24 h; month counts confirmed (screenshot or his words) <= 12 h; scrape <= 8 days (2, or --waive-scrape) |
| Files exist, right channel | exit 2 for a missing master / thumbnail (NAS); a clip master only on its stinger's channel; every API call checked against the brand's channel id |
| Never the full episode, YouTube in Metricool, FB on TCL | validate(); metricool.py payloads |
| One long-form a day, 48 h rules, same topic apart, lead time, caps, weekdays | validate() re-asserts each on the finished plan |
| Collaborators | from measured speakers; a missing handle = exit 2; one set per reel, never on TCL when the reel is on CWC (validate) |
| One approval each | plan + cleanup approvals bound to a sha; a tap on a replaced card changes nothing |
| Never twice, never a false "scheduled" | publish_log.json before each send; `record` refuses a connector error or a second record; uploads logged before their extras |
| Cleanup keeps what matters | only after every post is handled; keep set re-checked at apply; NAS media folders need a Resolve listing; other episodes' #recycle untouched |
| Resolve, one skill at a time | baton.py (4 while the other holds it; stale > 3 h only with his words) |
NOT gated (know it): the holistic read's judgement; whether YouTube shows an API thumbnail on a Short; monetization (the
API cannot set or read it on a creator channel - the checklist + Claude in Chrome); r_sweep.py has not run on a real
project; the baton is a convention in the worker briefs, not code inside the sub-skills.

## Definition of done - `next.py` reads the same files
- [ ] PodCut locked; CWC_PodClips and CWC_PodReels delivered (finals + dashboards in the episode folder, delivery.json)
- [ ] the window confirmed by Colden; calendar, peaks and month counts fresh; holistic.json written after both deliveries
- [ ] plan.py exit 0; the card sent; "Schedule all" on the current sha
- [ ] every YouTube item uploaded with its metadata (re-run daily until done); every `metricool` item recorded with its
      plannerUrl; every `manual` item has its kit
- [ ] the Studio checklist written (monetization ON on every video); verify + dashboard rebuilt; the wrap-up sent
- [ ] cleanup: scan -> card -> his tap -> apply; `cleanup/done.json` lists every NAS delete and every file in the Trash

## Files
`scripts/` common.py intake.py window.py next.py baton.py cal.py ytapi.py plan.py tg.py tg_plan.py metricool.py youtube.py
kit.py dashboard.py cleanup.py rs.py (copied from CWC_PodClips) r_sweep.py studio_viewers_online.js (copied from
youtube-packaging) selftest.py - `references/` rules.json brands.json collaborators.json.
RUN folder: run.json, events.log, calendar/, holistic.json, plan.json + plan.md, publish/ (drive_links, metricool_payloads,
youtube_status, studio_checklist.md), publish_log.json, cleanup/ (resolve.json, manifest.json, done.json).

## Open items (ask Colden)
- **Collaborators**: is @createwithcolden ever a collaborator on a TCL post where Colden speaks (today: never)? Jake's and
  Todd's Instagram handles. Is a phrase of 3+ words the right line for "speaks" (a "yeah" / "right" never counts)?
- **Monetization**: the API cannot turn it on. Studio's Upload defaults (Monetization On) on both channels + Claude in
  Chrome checking each video's Monetization tab and ad-suitability answers - OK? Is The Creative Lens monetized?
- **Before the audit**: YouTube may lock API uploads from an unaudited project as private so they cannot be switched in
  Studio - upload ONE test video first and try the flip.
- **Quota**: ~4-5 uploads a day at the default 10,000 units: a week of ~20 YouTube uploads takes ~4-5 days, so the upload
  re-runs daily. A scheduled daily run, or a quota increase in the same audit form?
- **Cleanup**: confirm every time (today), or automatic once trusted (like PodCut's auto_lock)? Where do Resolve's cache /
  proxy / optimized media live, so the sweep can include them? Raw camera files are always kept (they are the sources of
  the locked timelines) - right?
- **CWC_PodReels** (being finished): deliver like PodClips (`Final/Reels/` + dashboard + delivery.json, optionally a
  `next.py --json`); retire its own posting steps (publish.py plan / payloads / tg_plan still send YouTube through Metricool).
- **The baton in code**: taking it inside both skills' rs.py would make it a real gate rather than a brief.
- **Colden and Todd**: not set up in PodClips / PodReels yet (their `first_run_ask`).
- **Quota costs** in rules.json: check once against Google's quota calculator.
