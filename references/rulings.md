# CWC_PodRun - Colden's rulings, verbatim, and the run history

Moved out of SKILL.md on 2026-10-09 so every session loads the recipe, not the history. This file is the SOURCE of every
rule in SKILL.md: read it when a rule is in question or a new ruling lands (add it here with his words and the date, then
change the gate and the one-line rule in SKILL.md).

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
11. **Colden uploads, the API packages (2026-10-08, Ep 25 kickoff).** "I will upload all YouTube videos to help with quota.
    You handle all the metadata and schedule" -> `intake.py --colden-uploads "<his words>"` (per run, never assumed): plan.py
    paces by metadata units (~150-550 a video, not ~1,700-2,150), the card tells him what to upload (private, not scheduled,
    the master's file name as the title), `youtube.py adopt` matches each upload and shows him the map, `adopt --apply` adds
    every piece of metadata + publishAt + the extras; `youtube.py upload` refuses. Same day: "Never double up 2 clips in one
    day. Doubling up shorts is fine" (rules.json shorts_per_channel_per_day 2, long_form_per_channel_per_day 1).
10. **The build review** (his four answers): this repo holds **CWC_PodRun only** (one skill, one repo, like the other
    three); CWC_PodReels' delivery is built by **its own session** - this skill only reads it
    (`references/podreels_handoff.md`); the Resolve baton is checked **inside** CWC_PodClips' and CWC_PodReels' `rs.py`.

12. **His own Short slots** (2026-10-09, Ep 25, when s18 had no CWC slot): "These are the top slots for the 6 CWC shorts:
    9/9 4:00 PM, 9/10 1:00 PM, ..." -> `holistic.json` `"short_slots": {"cwc": {"at": ["YYYY-MM-DDTHH:MM", ..], "by":
    "<his words>"}}`. Those slots replace the best-time search and the per-day cap for that brand; reels fill them in rank
    order, never on a same-topic clip day (`plan.py fixed_slots`). A reel that fits none = ASK.

13. **The plan card is two calendar graphics** (2026-10-09, Ep 25): "On telegram show as a calendar graphic. one for TCL,
    one graphic for CWC. too confusing as all that text." -> `plan_cal.py` renders `plan_cal_<brand>.png` (days as columns,
    CLIP red / SHORT blue, already-scheduled posts grey); `tg_plan.py send` sends both, then a short text with the buttons.
14. **Everything through Metricool** when he says so (2026-10-09: "Schedule all in Metricool and we will fix once we hit
    quota") -> `intake.py --metricool-all "<his words>"`: no manual kits, the cap gate is off for that run.
15. **The full-episode link by id** (2026-10-09: the Ep 25 live has no "Ep. 25" in its title; "Yes do NOT link to the one
    with 📱 emoji") -> `intake.py --full-episode <cwc id> <tcl id> "<his words>"`; youtube.py uses it before the title search.

16. **The go-live watch is code, not memory** (2026-10-09, Ep 25: s06 went live at 4 PM with no pinned comment and no
    related video - "why have these skills with rules if they keep getting missed and ignored?"). The moment the first
    YouTube item is scheduled, a recurring session cron (every <= 10 min) runs `pin.py due` + `related.py due` + the
    monetization check, and `pin.py arm` records it; `next.py` puts GO-LIVE WATCH NOT RUNNING first until it is armed.
    Related videos and monetization can be set BEFORE go-live (private is fine) - do them right after adopt --apply.

Carried rules (ruled in the skills that hand over to this one): clips ~2 PM ET when no viewer data; one long-form per
channel per day; news first then push_order; no short on top of the clip of the same topic; read Studio's scheduled queue
first ("This is a must!", 2026-09-15); each master only on its own channel; end screens link only public videos; the
full-episode link = the public "Ep. NN" upload WITHOUT the 📱; one reel a day per brand, extras on the best days >= 3 h
apart at the brand's best TikTok hour; Todd-only reels are exported, never posted; one YouTube category per channel
(Film & Animation on both - "Keep film", 2026-09-15).

## Where things stood on 2026-10-03 (history)
- **Proven on real data** (dry, temp root): intake on the Ep 24 NAS folder; the YouTube calendar read of both channels
  (API); Metricool's real answers parsed (scheduled posts, best times); the plan built from the real CWC_PodClips and
  CWC_PodReels deliveries - 7 clip uploads + 15 Short uploads + 15 Metricool posts, 40,250 quota units = 5 upload days.
- **Never run for real**: the tandem run with two background workers; the plan card on Telegram; an upload of a real
  video; a Metricool post through this skill; the Studio viewer-peak read and the month-count screenshot (Claude in
  Chrome); the cleanup (`r_sweep.py` has not touched a real project). The first of each happens with Colden reachable.
- **The YouTube route is settled: `publish_at_works`** - nothing to flip. Two tests on The Creative Lens, 2026-10-03:
  the flip test (Colden: "the flip worked. i switched to unlisted and saved. good. switched to public and tested on
  different browser. good. has not been tested on main channel but should be good to go"), then the publish test he
  asked for ("good lets run that test on the creative lens channel"): uploaded private with publishAt 10:07 ET, public
  by itself at 10:07. So API uploads from this project are NOT locked private, whatever edit-clips' notes of
  2026-09-15 say. Still to see: the first upload to Create with Colden. Both test cards stay up until he deletes them
  ("Leave it, I'll delete"); plan.py ignores them on the calendar.
- **Ep 24** (The Creative Lens) is the pilot, run started 2026-10-03: window Sat 10/3 -> Thu 10/8 (his words); calendars,
  Metricool best times, both channels' Studio viewer peaks (CWC read by switching Chrome's YouTube channel to Colden
  Raisher and back - his OK; TCL's card has no data, clips at 2 PM), October counts from the API in his words.
- **Handles on file** (references/collaborators.json, each with its source): Nick @willco_media, Erik @eriksutton_,
  Jake @jakedirectedthis, Todd @imtoddv (Colden 2026-10-03). A new guest who speaks in a reel = exit 2 until he gives it.
- **The dry plan with the real answers** (route + handles): builds clean; Ep 24 collaborators come out as Jake + Nick
  on s01, Jake on s05, Nick on s02 / s04 / s09 / s15, none on the four reels where only Colden has a real line.

## Open items (ask Colden)
- **Collaborators**: is @createwithcolden ever a collaborator on a TCL post where Colden speaks (today: never)? Is a
  phrase of 3+ words the right line for "speaks"? Instagram's collaborator limit (3 on file) unverified.
- **Month count**: on 2026-10-03 `getScheduledPosts` listed a PUBLISHED October post too. If it always does, the count
  could come from the API instead of a screenshot - his ruling (the screenshot) stands until he says otherwise.
- **Quota**: ~4-5 uploads a day at 10,000 units; an episode is ~40,000. `youtube.py upload` must run daily for ~5 days
  (each Pacific day from midnight PT): a scheduled daily run, or the quota increase that is in the audit request?
- **After publish**: pinned comment ~1 min after a video goes live, end-screen re-pointing as later clips go public,
  Test & Compare - today a checklist (`youtube.py checklist`), nothing fires by itself.
- **Monetization**: Studio's upload defaults (Monetization On) on both channels + Claude in Chrome checking each video.
- **Cleanup**: confirm every time (today), or automatic once trusted (like PodCut's auto_lock)? Where do Resolve's cache /
  proxy / optimized media live, so the sweep can include them?
- **Colden and Todd**: not set up in PodClips / PodReels yet (their `first_run_ask`).
- **CWC_PodClips rs.py** prints "no Resolve connection" without a flush (lost when piped); CWC_PodReels' copy has the fix.
  CWC_PodReels has no `next.py --json`: its cards do not show under WAITING ON COLDEN here.
- **Quota costs** in rules.json: check once against Google's quota calculator.

## 2026-10-09 (the audit's questions, his answers)
1. "Keep the model render" - the AI headline stays model-rendered. 2. "daemon should tell claude to pin with chrome MCP" ->
watch.py queues every pin / related job in ~/.config/cwc/podrun_todo.jsonl; the conductor session's Monitor wakes on it and
pins with the Chrome MCP; Telegram only after 15 min (pin) / inside 12 h of the slot (related). 4. Cold reads on Sonnet:
"yes" (no drawback to the final packaging: a cold read only judges a theme). 5. "Reels on 'Colden and Todd' will either go
to CWC or get killed"; clip thumbnail headlines "should be 2-5 words with a target of 3".

