---
name: CWC_PodRun
description: The CWC podcast aggregator - one episode folder on the NAS to every clip, short and post scheduled. Runs /CWC_PodCut until the cut is locked, then /CWC_PodClips and /CWC_PodReels in tandem (shared Resolve baton, one Telegram listener), then reads every finished product together with the Monday channel data, checks YouTube and both Metricool calendars, builds ONE Friday-to-Thursday posting plan for ONE Telegram approval, and posts it - YouTube through the Data API (Studio upload + API metadata until the audit passes), Facebook / Instagram / TikTok through Metricool within each account's 20-post month, manual kits after that - and ends with the posting dashboard in the episode folder. Use when Colden says "pod run", "/CWC_PodRun", "run the episode", "process Ep NN", "take this episode to posting", or gives an episode folder of The Creative Lens / Colden and Todd and wants it done end to end; also to resume a run or ask where an episode stands.
---

# CWC_PodRun

**v0.1 (2026-10-03)** - built in one session from Colden's flow of 2026-10-03 and the hand-off contracts the three
pipeline skills already define (`CWC_PodClips/references/aggregator_handoff.md`, CWC_PodReels' publishing cadence).
`selftest.py` proves 49 gates on a synthetic episode. NOT yet run on a real episode - the first run (Ep 25) is the pilot.

## START HERE - every time
```
S=~/.claude/skills/CWC_PodRun/scripts
python3 $S/intake.py "<episode folder>" [--resolve-window "<Colden's words>"]   # once per episode -> RUN
python3 $S/next.py "<RUN>"            # where the whole pipeline stands + the next step (run it often)
```
RUN = `~/Documents/Claude/Projects/Create with Colden/CWC Podcast/run/<show>/<EpNN>/`.
Exit codes, as the whole pipeline: **0 done - 2 STOP AND ASK COLDEN - anything else a gate failed** (read it, fix the
cause, never work around it or re-run to get past it). Not covered by a rule: STOP AND ASK. Never guess.

## Colden's rulings (2026-10-03) - the source of every rule
1. **The flow.** "1. I call this skill in a code project and give you an episode folder on my NAS. 2. you send that
   folder to /cwcpodcut to sync those clips into a multicam and cut the podcast into a final multicam output. That skill
   ends with a locked podcut timeline. 3. Once you see a locked podcut timeline, begin running /cwcpodclips and
   cwcpodreels skills at the same time... Both end my dropping final versions and a dash board in the NAS root folder.
   4. Once clips and reels are done processing, you will take a thorough read through all the content holistically as
   well as utilizing the monday youtube and tiktok data to plan out the best cadence for these new clips."
2. **Calendar first, weekly rhythm.** "you will need to check youtube and metricool first to see what is already on the
   calendar when deciding on your cadence. generally speaking we will have at least one show per week so the goal will be
   - live show thursday, skill run thursday night with posting going out Friday to the following thursday and then repeat."
3. **Metricool.** "social media posts will need to go out through metricool. Create with Colden and The Creative Lens both
   have their own metricool accounts for posting. both are limited to 20 posts a month. If we exceed that, we will need to
   post manually after that 20 has been hit. Metricool will be used to Facebook, Instagram and TikTok (TCL does not have a
   facebook at the moment)." One post to FB + IG + TikTok: "all 3 equal 1 as long as you don't make individual changes to
   the posts."
4. **YouTube = the API.** "YouTube will solely be driven by the API and uploaded directly to youtube as thumbnails given to
   metricool do not actually transfer over to youtube shorts." Audit: "working through the audit now. until it passes I
   will manually schedule. you will upload all metadata." -> rules.json `youtube_audit_passed: false` = route
   `studio_manual`; flip it only on his word.
5. **The full episode** "stays as the live stream" - this skill never uploads it.
6. **Reviews** "are being sent through telegram" (the shared @VideoEditReview_bot). **Thumbnails**: Higgsfield MCP (inside
   PodClips / PodReels). **Data**: `channel_metrics.json`, "a local file that is updated every monday". Mac; the NAS root
   for an episode = the episode folder.
7. **The repo.** "you can move copies of them into this repo. eventually this will be built to live locally with a back
   up here in this repo." -> github.com/coldenraisher/cwcpodskill holds all four skills (`install.sh`).

Carried rules (already ruled in the skills that hand over to this one - not re-asked):
- CWC_PodClips aggregator_handoff (2026-10-02): primary channel first, TCL >= 48 h later; news first, then push_order;
  one long-form per channel per day; clips ~2 PM ET; no premieres; no short on top of the clip of the same topic; no two
  products of the same topic on one channel on one day; read Studio's scheduled queue first ("Always look at YouTube
  Studio to schedule. This is a must!", 2026-09-15); each master only on its own channel; end screens link only public
  videos; ONE plan for ONE approval; the full-episode link = the public "Ep. NN" upload WITHOUT the 📱.
- CWC_PodReels cadence: one short a day per brand, extras as second posts on the best days >= 3 h apart; a short to both
  posts to CWC first, TCL >= 1 h later; best hours = Metricool best times (TikTok) per brand; Todd-only shorts are
  exported, never posted; IG collaborator = the guest on the CWC post only.

## SAFETY RULES
1. **Nothing is posted, uploaded or scheduled before "Schedule all" on the CURRENT plan card.** Approval is bound to the
   plan's sha; any rebuild needs a new card. `metricool.py`, `youtube.py` and `kit.py` refuse otherwise.
2. **The other three skills are read-only from here** - their code AND their state files. This skill runs their scripts
   and reads their files; it never edits them. A change to one of them is that skill's job (ask Colden).
3. **Resolve is Colden's workspace.** The sub-skills ask before Resolve work unless intake recorded a `--resolve-window`
   in his words. In the tandem run, the Resolve BATON (`baton.py`) is taken before every Resolve sequence and given back
   right after - two skills never drive Resolve at once.
4. **One Telegram listener** (CWC_PodClips' `tg_listen.py`); this skill is a plugin of it (`tg_plan.py install`). Never
   start a poller.
5. **Never touch a public video** that is not the planned one; never send YouTube through Metricool; never post the full
   episode; never a Facebook post for The Creative Lens.
6. **Every write is logged before the next one** (`publish_log.json`, `data/metricool_ledger.jsonl`) so a crash never
   double-posts: an item in the log is never sent again.

## THE RUN, in order (S = this skill's scripts, R = the RUN folder)
```
# 1 ---------- intake
python3 $S/intake.py "<episode folder>" [--resolve-window ".."]      # show + EpNN exactly as CWC_PodCut finds them; window = the day after the show date in the folder name -> +6 days
# 2 ---------- the cut
/CWC_PodCut  (its own SKILL.md: prep.py -> LOOK -> ack.py -> build.py; Creative Lens auto-locks)   ->  next.py says "PodCut locked"
# 3 ---------- clips + reels in tandem (below)  ->  next.py: "clips delivered" AND "reels delivered"
# 4 ---------- the calendar (fresh: <= 6 h when the plan is built)
python3 $S/cal.py youtube "$R"                                        # both channels: scheduled + last 21 days (API)
#   Metricool, per brand ON ITS OWN CONNECTOR (cwc = claude.ai Metricool, blogId 5965295; tcl = metricool-tcl, 6367106):
#   getScheduledPosts from the 1st of the window's first month to the end of its last month, America/New_York -> save verbatim ->
python3 $S/cal.py metricool "$R" <cwc|tcl> <file> --from YYYY-MM-01 --to YYYY-MM-DD
#   getBestTimeToPostByNetwork socialNetwork=tiktok, the coming week -> save ->  cal.py besttimes "$R" <cwc|tcl> <file>
python3 $S/cal.py show "$R"                                           # month counts: say them to Colden if anything looks off;
#   his number wins:  cal.py counts "$R" <brand> YYYY-MM=<n> "<his words>"
# 5 ---------- the holistic read (judgement - do all of it), then the plan
#   READ: CWC_PodClips WORK/delivery.json + Final/Clips dashboard, CWC_PodReels WORK/delivery.json + copy.json, the Monday
#   scrape (working_now, avoid, insights, shorts, tiktok), data/shorts/summary.md, data/channel_summary.md -> write R/holistic.json
python3 $S/plan.py build "$R"                                         # -> plan.json + plan.md (every rule re-asserted)
python3 $S/tg_plan.py send "$R"                                       # ONE card: Schedule all / Changes
#   Changes -> his message lands in run.json plan_notes_open -> change the INPUTS (holistic.json, cal.py counts, a re-read) -> build -> send
# 6 ---------- after "PLAN APPROVED"
python3 $S/metricool.py upload "$R"                                   # shorts + covers -> Drive direct links (CWC_PodReels publish.py upload)
python3 $S/metricool.py payloads "$R"                                 # then per call: createScheduledPost(blogId, date, info) on ITS connector ->
python3 $S/metricool.py record "$R" <item id> <answer file>          #   save the answer, record it BEFORE the next call
python3 $S/kit.py "$R"                                                # Final/YouTube Upload List.md + Final/Manual Posts/ (over the cap)
#   YouTube, before the audit: Colden uploads + schedules from the list (file names unchanged) ->
python3 $S/youtube.py find "$R"   ;   python3 $S/youtube.py apply "$R"      # find his uploads, write ALL the metadata
#   after the audit (rules.json youtube_audit_passed true, his word):  youtube.py upload "$R"
python3 $S/youtube.py checklist "$R"                                  # Studio-only work: Test & Compare, end screens, pinned comments
# 7 ---------- wrap-up
python3 $S/dashboard.py "$R"                                          # <episode>/Final/<EpNN> Posting Plan.html (re-run as uploads land)
python3 $S/tg_plan.py wrapup "$R"
```

## 3. The tandem run - CWC_PodClips + CWC_PodReels at the same time
Both start the moment the PodCut is locked (`next.py`), on the same locked cut. Run each as a **background agent** (Agent
tool, `run_in_background: true`) so their long Telegram waits overlap; the main session conducts.

The brief for each agent (fill the <> parts; one agent per skill):
```
You are the <CWC_PodClips | CWC_PodReels> worker of CWC_PodRun for <show> <EpNN>. PodCut CACHE = <podcut_cache>.
Load the skill with the Skill tool (<CWC_PodClips | CWC_PodReels>) and follow its SKILL.md exactly, from its START HERE.
Resolve: before EVERY Resolve sequence (build.py, review.py render, master.py render, cover.py resolve, r_template,
lock.py) run  python3 ~/.claude/skills/CWC_PodRun/scripts/baton.py take <skill> "<what>"  - exit 4 = the other skill
is in Resolve: do non-Resolve work (data, themes, cold reads, b-roll research, covers, copy, packaging) and try again;
give it back right after:  baton.py give <skill>.  Resolve window from Colden: <his words | none: ask as your skill says>.
<PodReels only:> STOP at lock.py (it writes delivery.json). Do NOT run publish.py plan / payloads / tg_plan.py - CWC_PodRun
plans and posts every product together.
<PodClips only:> STOP after package.py build -> deliver.py (Final/Clips + the dashboard).
When everything left is waiting on Colden (cards on Telegram), return a 5-line status: stage, what waits on him, what you
do on his next tap. Never claim a look you did not take; never work around a gate.
```
The main session then: watches both event logs with a Monitor (`tail -n 0 -F "<clips WORK>/review/events.log"
"<reels WORK>/review/events.log"`), and when a tap lands resumes that worker (SendMessage: "Colden answered: <line> -
continue"); runs `next.py "$R"` after each report; answers questions the workers return. When both say delivered, go to 4.
No Agent tool (another client): interleave the two skills in this session, each skill's `next` steps in turn, the baton
still taken around every Resolve sequence.

## 5. The holistic read -> `holistic.json` (Colden ruling 1: "a thorough read through all the content holistically")
Do all of it before the plan:
1. Every product as a whole: the clips (titles A/B/C, hooks, push order, news, which channel), the shorts (titles, hooks,
   destinations, rank), and where they repeat each other (the planner also keeps same-topic products apart by measured
   overlap on the locked cut).
2. The Monday scrape: `working_now`, `avoid`, `insights.patterns / actions`, `shorts.youtube` + `shorts.tiktok`,
   `audience.best_slots_et`, `trend_vs_last_week`, `tcl`. Ep 24 lessons as an example of what to look for: gear + money
   topics carry clips; TikTok winners show a price or outrage in frame 1; AI / career talk sits at 0.06-0.2x.
3. What is already on the calendar (cal.py show) and the month counts.
4. Write `R/holistic.json`:
   `{"summary": "what this episode has and what leads, why", "overrides": [{"ref": "s04", "kind": "short", "rank": 1, "why": ".."},
   {"ref": "t03", "kind": "clip", "push_order": 1, "why": ".."}], "hold": [{"ref": "s06", "kind": "short", "why": ".."}], "notes": [".."]}`
   - `rank` / `push_order` are 1-based places; an override moves a product just ahead of that place.
   - Every `why` names the data point it rests on (>= 25 characters, gated). A hold leaves a product out of this week's
     plan and puts it on the card - never a silent drop.
   - No overrides is a valid read: the skills already ranked by the same data. Say so in the summary.

## 6. What the plan decides (plan.py; numbers in references/rules.json)
- **Window**: the day after the live show (the date in the folder name, "Ep. 24 - 10:1" -> Fri Oct 2) through the
  following Thursday. No slot sooner than 90 min after the build (a card that waits too long is rebuilt, never shifted).
- **Clips** (YouTube): CWC first, spread over the window, news first then push_order, 2 PM ET; one long-form per
  channel per day including what is already on YouTube (lives count); the same clip on TCL >= 48 h after CWC; a TCL-only
  clip not before window start + 48 h (my reading - Open items); spill up to 3 days past the window, flagged.
- **Shorts**: per brand in rank order, one a day, then second posts on the best days >= 3 h apart, at that brand's best
  TikTok hour; TCL >= 1 h after CWC for a short on both; never on a channel + day with a same-topic clip.
- **Routes**: YouTube clip / Short -> `studio_manual` (before the audit) or `youtube_api`; FB + IG + TikTok -> ONE Metricool
  post per short per brand (one caption, one video, every network of that brand) while the month count is under 20,
  best-ranked shorts first; over the cap -> `manual` (kit). TCL networks: Instagram + TikTok.
- **Quota**: the YouTube units per item are summed against the shared daily pool (data/quota.json with CWC_PodClips);
  after the audit, uploads that do not fit tonight move to the next night, and a slot the quota cannot reach in time asks.

## Gates (selftest.py proves each - run it after ANY change)
| Rule | Gate |
|---|---|
| Runs on finished products only | plan.py: both delivery.json files, the clips one newer than its lock.json |
| The holistic read happened | plan.py: holistic.json newer than both deliveries; every override / hold names a real product with a data reason |
| Calendar first | plan.py: youtube.json + metricool_<brand>.json <= 6 h old; cal.py metricool refuses a range that misses the window's months |
| Data before planning | plan.py: the Monday scrape <= 8 days old (exit 2; `--waive-scrape "<his words>"`) |
| Files exist | plan.py exit 2 (NAS) for any master / thumbnail; validate() for captions |
| Right channel | a clip master only on its stinger's channel; every API call checked against the brand's channel id first (ytapi) |
| Never the full episode, never YouTube in Metricool, no FB on TCL | validate(); metricool.py payloads |
| One long-form per channel per day, 48 h, 1 h, same topic apart, lead time, caps, weekdays | validate() re-asserts every one on the finished plan |
| One approval, bound to the plan | tg_plan.py: approval = sha; a tap on a replaced card changes nothing; publish scripts refuse any other sha or rules version |
| Never twice, never a false "scheduled" | publish_log.json checked before every send; `record` refuses a connector error and a second record |
| Resolve, one skill at a time | baton.py (take = 4 while the other holds it; stale > 3 h only with his words) |
NOT gated (know it): the holistic read's judgement; Metricool posts published outside the skill earlier in the month
(the card shows the count for Colden to confirm); whether YouTube shows an API thumbnail on a Short; the baton is a
convention in the worker briefs (the sub-skills' own code does not take it).

## Definition of done - `next.py` reads the same files
- [ ] PodCut locked; CWC_PodClips `next.py --json` stage `delivered`; CWC_PodReels `delivery.json` (lock.py) current
- [ ] calendar read within 6 h of the plan; month counts said to Colden when unsure
- [ ] holistic.json written after both deliveries; plan.py exit 0; the card sent; "Schedule all" on the current sha
- [ ] every `metricool` item recorded with its plannerUrl; every `manual` item has its kit in Final/Manual Posts
- [ ] every YouTube item: uploaded + scheduled (API) or found in Studio + metadata written; the Studio checklist written
- [ ] `<episode>/Final/<EpNN> Posting Plan.html` rebuilt after the last write; the wrap-up sent on Telegram

## Files
`scripts/` common.py intake.py next.py baton.py cal.py ytapi.py plan.py tg.py tg_plan.py metricool.py youtube.py kit.py
dashboard.py selftest.py - `references/` rules.json brands.json.
RUN folder: run.json (paths, window, plan_card, plan_approval, notes), events.log, calendar/, holistic.json, plan.json,
plan.md, publish/ (metricool_payloads.json, youtube_found.json, studio_checklist.md), publish_log.json.
Shared: data/quota.json (with CWC_PodClips), data/metricool_ledger.jsonl, ~/.config/cwc/resolve_baton.json.

## Open items (ask Colden)
- **TCL-only clips**: "minimum 48 hr delay for TCL clips" - built as "not before window start + 48 h" when the clip is
  not on CWC at all. Right?
- **Before the audit**, every YouTube clip AND Short is a Studio upload by hand (Ep 24 scale: ~7 clip uploads + up to 20
  Short uploads a week). Keep it that way, or Shorts through Metricool's YouTube until the audit (no custom cover)?
- **Metricool month**: counted by publish month; Metricool's API shows only posts not yet published, so earlier posts made
  outside this skill are invisible - the card shows the count; is Metricool's counter per publish month or per creation?
- **API thumbnails on Shorts**: does `thumbnails.set` show on a Short? Check on the first run.
- **`youtube.py apply --with-flags`** (made for kids / altered content through videos.update) is untested on an
  unaudited project - off by default; Studio's upload flow asks both anyway.
- **CWC_PodReels**: (a) its `publish.py plan / payloads / tg_plan.py` are superseded by this skill and still send YouTube
  through Metricool - retire or mark them in that skill; (b) "both end by dropping final versions and a dashboard in the
  NAS root folder": PodReels keeps masters in `<episode>/Shorts/Renders/` and has no dashboard - a `deliver.py` like
  PodClips' (Final/Reels + dashboard) would match.
- **The baton in code**: taking it inside both skills' rs.py would make it a real gate rather than a brief.
- **Colden and Todd**: not set up in PodClips / PodReels yet (their `first_run_ask`).
- **Clip time**: 2 PM ET from the hand-off; the scrape's best slots read Tue 11 AM / Thu 12 PM - move clips to the data?
- **Quota costs** in rules.json: check once against Google's quota calculator.
