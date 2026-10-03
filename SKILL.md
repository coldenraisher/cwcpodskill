---
name: CWC_PodRun
description: The CWC podcast aggregator - one episode folder on the NAS to every clip and reel posted and the disks cleaned. Runs /CWC_PodCut until the cut is locked, then /CWC_PodClips and /CWC_PodReels in tandem (one skill in Resolve at a time, enforced in each skill's rs.py; one Telegram listener), asks Colden for the posting window, reads every finished product with the Monday channel data, checks YouTube and both Metricool calendars, builds ONE posting plan for ONE Telegram approval, uploads every clip and Short to YouTube through the API with all its metadata (the route while the audit is pending is settled by a one-time flip test), schedules Facebook / Instagram / TikTok through Metricool within each account's 20-post month with the right Instagram collaborators, makes manual kits past the cap, and ends by sweeping Resolve, the local drive and the NAS. Use when Colden says "pod run", "/CWC_PodRun", "run the episode", "process Ep NN", "take this episode to posting", or gives an episode folder of The Creative Lens and wants it done end to end (Colden and Todd once /CWC_PodClips and /CWC_PodReels are set up for it); also to resume a run or ask where an episode stands.
---

# CWC_PodRun

**v0.3 (2026-10-03)** - the cloud scaffold (v0.2) reviewed against the LOCAL skills and the real Ep 24 records, fixed
and re-tested. `selftest.py` proves 88 gates on fixtures copied from the real records. A dry plan was built on the real
Ep 24 deliveries in a temp folder (nothing posted). NOT yet run for real - Ep 24 is the pilot (see "Where things stand").

## START HERE - every time
```
S=~/.claude/skills/CWC_PodRun/scripts
python3 $S/intake.py "<episode folder>" [--window YYYY-MM-DD YYYY-MM-DD --by "<his words>"] [--resolve-window "<his words>"]
python3 $S/next.py "<RUN>"            # where the whole pipeline stands + the next step (run it often)
python3 $S/youtube.py route           # how videos reach YouTube right now (flip test / audit) - plan.py needs it settled
```
RUN = `~/Documents/Claude/Projects/Create with Colden/CWC Podcast/run/<show>/<EpNN>/`.
Exit codes, as the whole pipeline: **0 done - 2 STOP AND ASK COLDEN - anything else a gate failed** (read it, fix the
cause, never work around it or re-run to get past it). Not covered by a rule: STOP AND ASK. **DO NOT ASSUME** (his words).

## Where things stand (2026-10-03) - read before the first real run
- **Proven on real data** (dry, temp root): intake on the Ep 24 NAS folder; the YouTube calendar read of both channels
  (API); Metricool's real answers parsed (scheduled posts, best times); the plan built from the real CWC_PodClips and
  CWC_PodReels deliveries - 7 clip uploads + 15 Short uploads + 15 Metricool posts, 40,250 quota units = 5 upload days.
- **Never run for real**: the tandem run with two background workers; the plan card on Telegram; an upload of a real
  video; a Metricool post through this skill; the Studio viewer-peak read and the month-count screenshot (Claude in
  Chrome); the cleanup (`r_sweep.py` has not touched a real project). The first of each happens with Colden reachable.
- **The YouTube route is open.** A private test video is up on The Creative Lens (`youtube.py route` shows it). Colden
  tries the flip to Scheduled in Studio, then `youtube.py route flip_works|locked --by "<his words>"`. Until then
  `plan.py` stops (exit 2). edit-clips' notes of 2026-09-15 say such uploads are LOCKED private - expect that it may be.
- **Ep 24** (The Creative Lens): PodCut locked, CWC_PodClips delivered (Final/Clips), CWC_PodReels delivered
  2026-10-03 (Final/Reels). No RUN folder exists yet: the pilot starts at intake and goes straight to the window.
- **Handles missing**: Jake and Todd have no Instagram handle on file; Jake speaks in Ep 24 reels s01 and s05, so the
  plan stops there (exit 2) until Colden gives it.

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
   through Metricool do not carry to YouTube Shorts - YouTube never goes through Metricool. Asked whether the audit had
   cleared: **"Not yet: test one"** -> `youtube.py flip-test`, the answer in `data/youtube_route.json`.
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
   screenshot of the metricool calendar".
7. **Clip timing from fresh data.** "For clip timings it might be best to pull fresh data from YouTube before determining."
8. **Clean up last.** "just sweeping resolve and the disks for extra generations or files that were saved but not used in
   the final outputs... the last step needs to be to clean up everything possible. NAS gets hard delete. Local drive files
   get moved to the trash bin where I can delete."
9. The full episode "stays as the live stream" (never uploaded here). Reviews go through Telegram. Thumbnails: Higgsfield
   (inside PodClips / PodReels). Data: `channel_metrics.json`, updated every Monday. Mac; NAS root = the episode folder.
10. **The build review** (his four answers): this repo holds **CWC_PodRun only** (one skill, one repo, like the other
    three); CWC_PodReels' delivery is built by **its own session** - this skill only reads it
    (`references/podreels_handoff.md`); the Resolve baton is checked **inside** CWC_PodClips' and CWC_PodReels' `rs.py`.

Carried rules (ruled in the skills that hand over to this one): clips ~2 PM ET when no viewer data; one long-form per
channel per day; news first then push_order; no short on top of the clip of the same topic; read Studio's scheduled queue
first ("This is a must!", 2026-09-15); each master only on its own channel; end screens link only public videos; the
full-episode link = the public "Ep. NN" upload WITHOUT the 📱; one reel a day per brand, extras on the best days >= 3 h
apart at the brand's best TikTok hour; Todd-only reels are exported, never posted; one YouTube category per channel
(Film & Animation on both - "Keep film", 2026-09-15).

## SAFETY RULES
1. **Nothing is uploaded, scheduled or deleted before Colden's tap on the CURRENT card** (plan: "Schedule all"; cleanup:
   "Clean up") - each approval is bound to a sha; a rebuild needs a new card. (The one exception he chose himself: the
   single private test video of `youtube.py flip-test`.)
2. **The other three skills are read-only from here** - code and state files. This skill runs their scripts and reads
   their files; a change to one of them is that skill's job (ask Colden). The baton check in their `rs.py` is the one
   change he approved (ruling 10).
3. **Resolve is Colden's workspace.** The sub-skills ask before Resolve work unless intake recorded a `--resolve-window`
   in his words; in the tandem run the BATON (`baton.py`) is taken around every Resolve sequence. The cleanup sweep asks too.
4. **One Telegram listener** (CWC_PodClips' `tg_listen.py`); this skill is its plugin (`tg_plan.py install`, then
   restart the listener). Never a poller.
5. **Never** touch a public video, send YouTube through Metricool, post the full episode, post Facebook for TCL, put
   collaborators on two posts of one reel, guess an Instagram handle, or delete a source, a final, a delivered file or
   anything a timeline uses.
6. **Every write is logged before the next one** (`publish_log.json`, `data/metricool_ledger.jsonl`, `cleanup/done.json`):
   a crash never double-posts, and a re-run finishes what is missing.
7. **The self-test never touches the real Resolve, Telegram, YouTube or Metricool**; never run `baton.py open / take`
   by hand outside a tandem run - the file makes every other skill's Resolve call stop.

## THE RUN, in order (S = this skill's scripts, R = the RUN folder)
```
# 0 once, not per episode: how do videos reach YouTube?   python3 $S/youtube.py route
#   not settled -> youtube.py flip-test <cwc|tcl> (ONE private 8 s test video) -> Colden tries the flip in Studio ->
#   youtube.py route flip_works|locked|audit_passed --by "<his words>"
# 1 intake - at kickoff Colden is in the session: ask the posting window (AskUserQuestion: the proposal intake prints, or his span)
python3 $S/intake.py "<episode folder>" --window <start> <end> --by "<his words>" [--resolve-window ".."]
# 2 the cut: /CWC_PodCut (prep.py -> LOOK -> ack.py -> build.py; Creative Lens auto-locks)   -> next.py: "PodCut locked"
# 3 clips + reels in tandem (below): baton.py open "$R" first                                  -> next.py: both "delivered"
python3 $S/baton.py close                                       # the tandem run is over
# 4 the window again if it has started or he never gave one:  python3 $S/window.py ask "$R"   (Telegram: Use this / Change)
#   Change -> his message lands in run.json window_notes_open -> window.py set "$R" <start> <end> --by "<his words>"
# 5 the calendar + fresh data (the plan refuses anything stale)
python3 $S/cal.py youtube "$R"                                  # both channels: scheduled + last 21 days (API)
#   Metricool per brand ON ITS OWN CONNECTOR (cwc = the claude.ai Metricool connector, 5965295; tcl = metricool-tcl, 6367106):
#   getScheduledPosts(brandId, fromDate = the 1st of the window's first month, toDate = the end of its last month,
#   timezone America/New_York) -> save the answer verbatim ->
python3 $S/cal.py metricool "$R" <cwc|tcl> <file> --from YYYY-MM-01 --to YYYY-MM-DD
#   getBestTimeToPostByNetwork(brandId, socialNetwork "tiktok", the coming week) -> save verbatim -> cal.py besttimes "$R" <cwc|tcl> <file>
#   Claude in Chrome, per brand: the Metricool planner in MONTH view for every month the window touches -> screenshot ->
#   count every post that month (published + scheduled) ->  cal.py counts "$R" <cwc|tcl> YYYY-MM=<n> --evidence <png>
#   Claude in Chrome, per channel: studio.youtube.com/channel/<id>/analytics/tab-build_audience/period-default (check the
#   channel - never the old gymnastics one) -> run scripts/studio_viewers_online.js -> save ->  cal.py peaks "$R" <cwc|tcl> <file>
python3 $S/cal.py show "$R"
# 6 the holistic read (judgement - below) -> R/holistic.json, then
python3 $S/plan.py build "$R"  ;  python3 $S/tg_plan.py send "$R"          # ONE card: Schedule all / Changes
#   Changes -> his message lands in run.json plan_notes_open -> change the INPUTS (holistic.json, window, counts) -> build -> send
# 7 after "PLAN APPROVED"
python3 $S/youtube.py upload "$R"        # every clip + Short with all its metadata, then thumbnail / captions / playlists;
#                                          a re-run finishes what is missing. Quota paces it: run it again each day until
#                                          "every YouTube item is uploaded" (the plan's upload_day says which day)
python3 $S/metricool.py upload "$R"      # reel video + cover -> Drive direct links
python3 $S/metricool.py payloads "$R"    # per call: createScheduledPost(blogId, date, info) on ITS connector ->
python3 $S/metricool.py record "$R" <item id> <answer file>                 #   record it BEFORE the next call
python3 $S/kit.py "$R"                   # Final/Manual Posts/ for posts over the cap (collaborators on the right post)
python3 $S/youtube.py checklist "$R"     # monetization ON + ad suitability, the flip times, Test & Compare, end screens,
#                                          pinned comments, a Short cover the API refused - Claude in Chrome works through it
python3 $S/youtube.py verify "$R"  ;  python3 $S/dashboard.py "$R"         # read back every video; <episode>/Final/<EpNN> Posting Plan.html
python3 $S/tg_plan.py wrapup "$R"
# 8 cleanup - the last step. FIRST REAL RUN: with Colden present, read the scan with him before the card.
python3 $S/cleanup.py scan "$R"  ;  python3 $S/cleanup.py card "$R"         # Resolve open on the project (or scan --no-resolve)
python3 $S/cleanup.py apply "$R"                                            # after his "Clean up" tap
```

## 3. The tandem run - CWC_PodClips + CWC_PodReels at the same time
Both start the moment the PodCut is locked, on the same locked cut. First `python3 $S/baton.py open "$R"`: from then on
`rs.py` of CWC_PodClips, CWC_PodReels and this skill refuses every Resolve call (exit 4) of a skill that does not hold
the baton - the gate is code, not this paragraph. Run each skill as a **background agent** (Agent tool,
`run_in_background: true`) so their long Telegram waits overlap; the main session conducts. The brief for each:
```
You are the <CWC_PodClips | CWC_PodReels> worker of CWC_PodRun for <show> <EpNN>. PodCut CACHE = <podcut_cache>.
Load the skill with the Skill tool (<CWC_PodClips | CWC_PodReels>) and follow its SKILL.md exactly, from its START HERE.
Resolve: a tandem run is open - your rs.py refuses every call unless you hold the baton. Before EVERY Resolve sequence
(build, preview render, master render, cover render, template, lock):
  python3 ~/.claude/skills/CWC_PodRun/scripts/baton.py take <skill> "<what>"   - exit 4 = the other skill is in Resolve:
do non-Resolve work (data, themes, cold reads, b-roll research, covers, copy, packaging) and try again; give it back right
after:  baton.py give <skill>.  Resolve window from Colden: <his words | none: ask as your skill says>.
STOP when your skill has DELIVERED (finals + dashboard in the episode's Final folder, delivery.json). Do NOT run any
posting step (CWC_PodReels: publish.py / plan_card.py / tg_plan.py) - CWC_PodRun plans and posts every product together.
When everything left is waiting on Colden (cards on Telegram), return a 5-line status: stage, what waits on him, what you
do on his next tap. Never claim a look you did not take; never work around a gate.
```
The main session watches both event logs with a Monitor (`tail -n 0 -F "<clips WORK>/review/events.log" "<reels
WORK>/review/events.log"`), resumes the matching worker when a tap lands (SendMessage: "Colden answered: <line> -
continue"), runs `next.py "$R"` after each report and answers the questions workers return. No Agent tool: interleave the
two skills in this session, the baton still taken around every Resolve sequence. Both delivered: `baton.py close`.
A baton older than 3 h is reported as stale and is only taken over with Colden's words (`take ... --steal "<words>"`).

## 6. The holistic read -> `holistic.json` (ruling 1)
1. Every product as a whole: the clips (titles A/B/C, hooks, push order, news, channels) and the reels (titles, hooks,
   destinations, rank), and where they repeat each other (the planner also keeps same-topic products apart by measured
   overlap on the locked cut). The two dashboards in `<episode>/Final/Clips` and `Final/Reels` show everything.
2. The Monday scrape: `working_now`, `avoid`, `insights`, `shorts`, `audience.best_slots_et`, `trend_vs_last_week`,
   `tcl` - and `data/shorts/summary.md`.
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
  A reel = a YouTube Short (API: its `yt_title`, the caption as description, the caption's hashtags as tags, the
  channel's category, the brand's playlist from CWC_PodReels' show file, the picked cover) + ONE Metricool post.
- **Collaborators** (Instagram): everyone who SPEAKS in the reel - a phrase of >= 3 words inside its ranges (CWC_PodReels
  phrases; a "yeah" is not speaking) - except Colden; one set per reel, on the CWC post when it plays on both, else on its
  one brand; handles from references/collaborators.json (+ PodReels' show file) - a speaker without one = ask. The
  `ig_collab` in PodReels' copy is only compared: a disagreement is flagged, the speakers win.
- **Routes**: YouTube = `youtube_api` with schedule `flip` (private, his flip) or `publishAt` (after the audit), from
  `data/youtube_route.json`; FB + IG + TikTok = ONE Metricool post per reel per brand while the confirmed month count is
  under 20, best-ranked first; over it = `manual`. TCL networks: Instagram + TikTok.
- **Quota**: units per upload (~1,700 a Short, ~2,150 a clip with captions) over Pacific days from tonight; each upload must
  land at least a day before its slot or the plan asks.

## Gates (selftest.py proves each - run it after ANY change)
| Rule | Gate |
|---|---|
| The window is his | plan.py exit 2 without a confirmed window or with one that has started; window.py set needs his words |
| The YouTube route is settled, never assumed | plan.py exit 2 until `youtube.py route` says flip_works or audit_passed; `locked` = exit 2 (his call); upload refuses a plan built for another route |
| Finished products only | plan.py: PodClips' delivery.json newer than its lock.json; PodReels' delivery.json with `final_dir` + `delivered_at` (locked is not delivered) |
| The real record shapes | clip category / playlists read from PodClips' v2 objects; Shorts: per-brand playlist key, the channel's category, never a default one |
| The holistic read happened | holistic.json newer than both deliveries; every override / hold names a real product with a data reason |
| Calendar + fresh data | youtube.json + metricool_<brand>.json <= 6 h; peaks <= 24 h; month counts confirmed (screenshot or his words) <= 12 h and never below what Metricool's own API lists; scrape <= 8 days (2, or --waive-scrape) |
| Files exist, right channel | exit 2 for a missing master / thumbnail (NAS); a clip master only on its stinger's channel; every API call checked against the brand's channel id |
| Never the full episode, YouTube in Metricool, FB on TCL | validate(); metricool.py payloads |
| One long-form a day, 48 h rules, same topic apart, lead time, caps, weekdays | validate() re-asserts each on the finished plan |
| Collaborators | from measured speakers; a missing handle = exit 2; one set per reel, never on TCL when the reel is on CWC (validate) |
| One approval each | plan + cleanup approvals bound to a sha; a tap on a replaced card changes nothing |
| Never twice, never half-done, never a false "scheduled" | publish_log.json before each send; a video is handled only with its thumbnail / captions / playlists (`complete`); `record` refuses a connector error or a second record |
| Cleanup keeps what matters | only after every post is handled; keep set re-checked at apply; NAS media folders need a Resolve listing; another episode's or another show's #recycle folder untouched |
| Resolve, one skill at a time | `rs.py` of CWC_PodClips / CWC_PodReels / CWC_PodRun: exit 4 unless its skill holds the baton while a baton file exists; baton.py (4 while the other holds it; stale > 3 h only with his words) |
NOT gated (know it): the holistic read's judgement; whether YouTube shows an API thumbnail on a Short (a refusal is
recorded and put on the checklist); monetization (the API cannot set or read it on a creator channel - the checklist +
Claude in Chrome); the Studio peak read and the month-count screenshot are a look, the numbers typed from it are not
checked; r_sweep.py has not run on a real project; a worker that never calls a Resolve script is not stopped by the baton.

## Definition of done - `next.py` reads the same files
- [ ] PodCut locked; CWC_PodClips and CWC_PodReels delivered (finals + dashboards in `<episode>/Final`, delivery.json); `baton.py close`
- [ ] the YouTube route settled; the window confirmed by Colden; calendar, peaks and month counts fresh; holistic.json written after both deliveries
- [ ] plan.py exit 0; the card sent; "Schedule all" on the current sha
- [ ] every YouTube item uploaded AND complete (re-run daily until done); every `metricool` item recorded with its
      plannerUrl; every `manual` item has its kit
- [ ] the Studio checklist written (monetization ON on every video); verify + dashboard rebuilt; the wrap-up sent
- [ ] cleanup: scan -> card -> his tap -> apply; `cleanup/done.json` lists every NAS delete and every file in the Trash

## Files
`scripts/` common.py intake.py window.py next.py baton.py cal.py ytapi.py plan.py tg.py tg_plan.py metricool.py youtube.py
kit.py dashboard.py cleanup.py rs.py (copied from CWC_PodClips, + the baton check) r_sweep.py studio_viewers_online.js
(copied from youtube-packaging) selftest.py - `references/` rules.json brands.json collaborators.json podreels_handoff.md.
RUN folder: run.json, events.log, calendar/, holistic.json, plan.json + plan.md, publish/ (drive_links, metricool_payloads,
youtube_status, studio_checklist.md), publish_log.json, cleanup/ (resolve.json, manifest.json, done.json).
Shared: `<CWC Podcast>/data/` youtube_route.json, quota.json (one pool with CWC_PodClips), metricool_ledger.jsonl;
`~/.config/cwc/` resolve_baton.json (only during a tandem run), listen_plugins.json.
Repo: github.com/coldenraisher/cwcpodskill (private, this skill only, branch `main`). Commit + push every change.
The other three skills live in their own repos (cwcpodcutskill, cwcpodclipsskill, cwcpodreelsskill).

## Open items (ask Colden)
- **The flip test**: can the private test video be switched to Scheduled in Studio? `locked` means the route itself must
  be re-decided (wait for the audit, or upload in Studio and let the API add the metadata - not built).
- **Handles**: Jake's and Todd's Instagram. Is @createwithcolden ever a collaborator on a TCL post where Colden speaks
  (today: never)? Is a phrase of 3+ words the right line for "speaks"? Instagram's collaborator limit (3 on file) unverified.
- **Month count**: on 2026-10-03 `getScheduledPosts` listed a PUBLISHED October post too. If it always does, the count
  could come from the API instead of a screenshot - his ruling (the screenshot) stands until he says otherwise.
- **Quota**: ~4-5 uploads a day at 10,000 units; an episode is ~40,000. `youtube.py upload` must run daily for ~5 days:
  a scheduled daily run, or the quota increase that is in the audit request?
- **After publish**: pinned comment ~1 min after a video goes live, end-screen re-pointing as later clips go public,
  Test & Compare - today a checklist (`youtube.py checklist`), nothing fires by itself.
- **Monetization**: Studio's upload defaults (Monetization On) on both channels + Claude in Chrome checking each video.
- **Cleanup**: confirm every time (today), or automatic once trusted (like PodCut's auto_lock)? Where do Resolve's cache /
  proxy / optimized media live, so the sweep can include them?
- **Colden and Todd**: not set up in PodClips / PodReels yet (their `first_run_ask`).
- **CWC_PodClips rs.py** prints "no Resolve connection" without a flush (lost when piped); CWC_PodReels' copy has the fix.
  CWC_PodReels has no `next.py --json`: its cards do not show under WAITING ON COLDEN here.
- **Quota costs** in rules.json: check once against Google's quota calculator.
