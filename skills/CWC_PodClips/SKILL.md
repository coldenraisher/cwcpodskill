---
name: CWC_PodClips
description: Long-form YouTube clips from a LOCKED CWC PodCut (The Creative Lens, Colden and Todd, any later show under Colden's umbrella) - generation, editing and delivery of the 3-5 strongest stand-alone clips of an episode. Stage 1 reads the whole locked cut, the show notes, Colden's channel data and the platform, builds clip THEMES (verbatim hook, story, payoff - parts of the podcast may be mixed), gates them in code, has a second reader cold-read each one, and sends at most 5 short cards to Telegram for approval. Stage 2 plans each approved clip (trims, hidden splices, 1.25x eye-pivot punch-ins, b-roll, guest name tag, Power Bin censor beep), builds it in DaVinci Resolve from the audio template, checks a preview and sends it to Telegram where one tap approves and picks the channel; masters at -14 LUFS, then an automatic lock + cleanup. Stage 3 packages every upload (captions, A/B/C titles + thumbnails with confirmed eyes-to-camera smiling stills, description, chapters, tags, playlists) and writes delivery.json for the aggregator, which owns the posting plan, uploads and Studio work. Use when Colden says "pod clips", "/CWC_PodClips", "clip themes for Ep NN", "clips from the podcast", "build the clips", or when the CWC aggregator skill reaches the clips step after a PodCut lock. Not for IRA Cafe, not for shorts (/CWC_PodReels, /edit-shorts), and not /edit-clips (the older clip skill, left untouched).
---

# CWC_PodClips

**v1.1 (2026-10-02)** - complete and proven end to end on The Creative Lens Ep 24 (5 themes -> 5 clips -> 7 uploads ->
`delivery.json`), then hardened by a final review pass (two independent reviews: code and instructions).

## START HERE - every time
```
S=~/.claude/skills/CWC_PodClips/scripts
python3 $S/next.py "<WORK>"        # where the episode stands + the exact next step of every clip (no WORK yet -> intake.py)
python3 $S/doctor.py <show> [--resolve]   # first run on a machine / after an update / on an odd failure: is everything in place?
python3 $S/tg_listen.py status     # the Telegram listener must be running before any card goes out (start it if not)
```
WORK = `~/Documents/Claude/Projects/Create with Colden/CWC Podcast/clips/<show>/<EpNN>/`.
Second skill of the CWC pipeline: `/CWC_PodCut` (locked cut) -> **`/CWC_PodClips`** (+ `/CWC_PodReels` for shorts, in
tandem) -> an aggregator skill (not built) that plans, posts and reports. This skill's only job: the highest-quality
long-form clips. You act as an expert YouTube video producer: every clip is a stand-alone, dynamic story with a
strong hook, real substance and a payoff that answers the hook - built for click-through and retention.

Every rule here is a decision Colden made (quoted, dated) and every rule has a GATE - a script that enforces it -
because prose rules get skipped. Not covered by a rule: STOP AND ASK. Never guess, never pad.
**Exit codes: 0 done - 2 STOP AND ASK COLDEN - anything else a gate failed**: read the message and fix the cause; never
work around a gate, never re-run to get past it, never hand-edit a state file to make it pass. (`rs.py` also uses 2 =
Resolve not reachable, 3 = timeout, 4 = another Resolve call is running; `next.py` always exits 0 - it only reports.
A mistyped command prints the usage and exits 1.)

## SAFETY RULES - before you touch anything
1. **Resolve is Colden's workspace.** Never build, render a preview or render a master while he may be working in it:
   a build AND a render make their timeline the current one. Ask him first ("is Resolve free?") unless he just said so.
   Running unattended (the aggregator): only in a window he has given.
2. **Never destructive in Resolve.** A fix is always a NEW version (`build.py`); nothing is deleted or trimmed on a
   timeline by hand. The only removals are `lock.py`'s, after a `.drt` backup of each timeline into the Trash.
   Resolve is driven only through this skill's `rs.py` scripts - not the Resolve MCP tools, never Fusion handles.
3. **The last `master.py render` of an episode locks and cleans up by itself** (ruling 36): timelines renamed "(L)",
   every other clip timeline of the episode removed (backups in the Trash), previews / raw masters / scratch trashed.
   To SEE the list before it happens: render the last master with `master.py render ... --no-lock`, read
   `lock.py "<WORK>" --dry-run`, then `lock.py "<WORK>"`. (Before the last master the dry run only says what is missing.)
4. **One listener per Telegram bot.** `tg_listen.py` answers every tap of every episode (and of CWC_PodReels through its
   plugin file). Never start a second poller; every `send` refuses to run while the listener is down.
5. **State files are written by scripts only** (`review/state.json`, `edit/review.json`, `package/review.json`,
   `versions.json`, `approved.json`, `lock.json`): the detached listener writes them too. To retire a version use
   `tg_edit.py supersede`; to drop a clip `tg_edit.py drop`. What you DO write by hand: `themes.json`, `broll.json`,
   `copy.<ch>.json` (the listener adds `"A"` to it at his pick - re-read before editing), `caption_fixes.json`.
6. **Other skills are read-only from here**: `/CWC_PodCut`, `/CWC_PodReels`, `/edit-clips`, `/edit-shorts`, `/podcut`,
   the AMIRA skills, the trend scanner. (`channel_data.py` refreshes the YouTube tokens edit-clips made - that is all.)
7. **Telegram videos always carry metadata** (Colden 2026-09-29): width, height, duration from the file, streaming on,
   a cover of the same shape - `tg_edit.py send` does it; never send a video any other way.
8. **Real sources only, honestly taken**: a page that shows a bot check, a consent wall or a 404 is not b-roll and is
   never worked around; a generated image never shows a real third party or real film / brand art.
9. **Never leave a card open with the listener down, and never claim a look you did not take**: `review.py ack`,
   `thumbs.py still`, `thumbs.py add --saw` and the b-roll `looked` field are attestations - open the picture first.

## Colden's rulings (2026-10-01 and 10-02) - the source of every rule
Read them once per session. A later ruling beats an earlier one where marked.
The brief: "develop 3-5 long form clips out of the entire podcast... Using the data that is collected each week on the
ColdenRaisher YouTube, make decisions to produce only the strongest segments that have proven success both on my youtube
channel and the platform as a whole. The main goal... highly engaging content with a high CTR and very high retention
throughout the segment. Each segment must be crafted as its own stand alone, dynamic story. Use the full context and
understanding of the transcript... research the topics... These themes do not need to be completely linear from the
podcast... if a theme can mix two different parts of the podcast together in the edit to tell a compelling story, do
it. The theme must have a very strong hook that sets up what the theme is about. It must have 5-10 minutes of interesting
dialogue and it must resolve with a strong payoff from the hook at the beginning. if you find more than 5 themes...
select only the very best 5 and hold the rest. if there are less than 3 strong, youtube forward themes, stop and flag
for manual review and more information in telegram... Summarize each with a draft title for youtube, and 1-2 sentences
describing the overall topic of the theme. Send all themes via telegram for approval."

His answers to my 18 questions:
1. A NEW skill for this format, "to be used in a larger aggregator skill that can run once per episode". Focus: "solely
   on the generation, editing and delivery of the highest quality clips".
2. "all of the Colden show umbrellas, Creative Lens and Colden and Todd including any other shows that may follow".
3. Clips go to @ColdenRaisher AND The Creative Lens. "The priority will still be on Colden's main channel with a minimum
   48 hr delay for TCL clips. not all clips will be pushed to Colden's main channel. This will be reviewed and determined
   at the edit level via telegram." (Stage 2 - nothing about channels is asked at the theme stage.)
4. "The aggregator skill will run this after the completion of a locked podcut."
5. "the channel metrics JSON should run each monday. If there are more specific data points needed. Tell me what to add
   to that scrape" -> `references/weekly_scrape.md`.
6. "Yes pull as much as possible to improve hit rate" (YouTube Analytics API).
7. Platform proof = recent videos on the topic that beat their own channel's normal. vidIQ: free tier only (no API).
8. Length: "no hard rule. The target is still an 8 minute video with mid-roll ad but if it is a shorter segment, fine. Do
   not add filler or garbage just to make it 8 minutes. Also, if the segment runs long and it concludes much stronger at
   the 10-15 minute mark, fine. The goal should always be a compelling story and retention. The cold open, stinger and
   end screen will all count towards the 8 minute target".
9. Held themes: "you can log them. only deliver 5 to me on telegram. if I veto or kill one, then you can suggest a runner up."
10. The rubric: mine to propose -> `references/rubric.json` + `rubric.md`. Colden 2026-10-01: "Approved".
11. Shared footage between clips: "keep overlap minimal... never more than 10%" ("a huge frustration to audience when
    they click on a 'new' video, but see older, reused segments").
12. Show notes: saved "in the main folder... each time", read every run - but "show notes will not always be followed...
    Highest level of context will come from the transcript."
13. "time sensitive, new releases/rumors, newsworthy always gets priority".
14. A theme where Colden barely speaks: acceptable, "likely only for TCL but I will approve manually".
15. "I will also be adding in all screen recordings so you can cut to full screen with speaker in lower third or create
    new layouts for optimal viewing. If the clip is integral to the theme and discussed in the clip, it needs to be shown."
16. Telegram: "one per theme to keep things clean", @VideoEditReview_bot.
17. ONE draft title per theme, "a place holder and a file name" - "another pass at titles and metadata once the full edit
    has been completed".
18. (REPLACED by ruling 22.) Each theme message also carried the payoff quote, the runtime and one line of evidence.
After the first real run (Ep 24, same day):
19. Cold reader: "yes you may change" - gaps are sorted BLOCKING / MINOR, only a blocking gap fails a clip.
20. Name tags: "Only guest gets name tag. Colden/Jake no. Colden/Todd no. When todd is a guest on TCL, yes for todd."
21. No-news episodes: "you can soften scoring and send the best themes. most will be for TCL but I would like something
    going on my channel." -> `soft_pass` 55 in rubric.json, used only when fewer than 3 themes reach 70; every card
    carries a suggested channel and at least one theme is suggested for his own channel.
22. Cards: "telegram cards are WAY too long for review. I know what I talked about on my show. Give me 25% of what you
    sent me per theme. Title, description, hook. good enough to move or kill". (This replaces answer 18.)
Stage 2 rulings (same day; the whole review with his words: `references/stage2_rules_review.md`): "I believe all
[edit-clips] rules should still stand" except:
23. Splices: camera change > b-roll > a 1.25x punch-in "always focused on the eyes"; never a jump cut.
24. "trim in clips to smooth as much as possible"; swears are never cut, they get the censor beep + ducking.
25. Output = the highest camera resolution (a 4K camera -> UHD; all 1080 -> 1080).
26. Versions are kept until locked; when every clip is locked, "clean up everything you can" (made automatic by ruling 36).
27. Audio like AMIRA: ONE template timeline he puts compressor / noise reduction / EQ on; clips are duplicates of it;
    nothing else until the end; a loudness bump before the final render only if still needed.
28. One tap approves the edit and picks the channel; masters render after it.
29. "use the colden ending on all". 30. The hook plays again in context. 31. Default 7-day posting plan, one approval
(MOVED to the aggregator by ruling 37 - nothing in this skill plans or posts).
After the pilot (same night): 32. "Hook running 17s... could easily condense to 12-15s" -> the cold open is 15 s at
most, tightened by a written trim scoped to the hook and hidden by a punch-in (the body still plays the line in full).
33. "you should include b-roll into V1's moving forward. That way I can give all notes at the same time."
34. Telegram must answer at once ("a very long delay from button push to actual send") -> `tg_listen.py`.
35. The censor (2026-10-02): the beep is the Power Bin's `Short Censor Beep.wav` ("Censors are missing the censor beep
    from power bin"; Power Bins are not reachable by script, so the build imports the file into Master by its path), and
    "let the first 3 frames of the waveform/word through. Then beep/duck. Then end the beep duck 3 frames before the end"
    -> `edit.json` censor: the word's start from the waveform, a word too short for 3 + 3 + 3 gets one 3-frame beep
    centred on it (C01 "bitch" = 4 frames: b, beep, ch).
36. Lock + cleanup belong to this skill and run AUTOMATICALLY (2026-10-02: "clean up should be automatic. Anything that
    the timeline or final output does not rely on can be trashed. For hard files, send to trash, i will manually delete
    from there in case of error") -> `lock.py`, run by `master.py` when the last master of the episode lands: every
    approved timeline renamed "(L)" with a green LOCKED marker; every other timeline of the episode exported as .drt into
    ~/.Trash and removed; previews, face frames, raw masters, audio tests, unused b-roll renders and the b-roll Source
    captures moved to ~/.Trash or the NAS share's #recycle. Kept: locked timelines + their media, masters, all JSON records.
37. Packaging is part of this skill; the posting plan, uploads and Studio work belong to the aggregator (2026-10-02:
    "Good add that packaging to this skill and build. List out what the aggregator should be responsible for after")
    -> Stage 3 below, the hand-off in `references/aggregator_handoff.md`.
38. Full-episode link (2026-10-02): every live goes up twice per channel; "one titles ends with a 📱 this denotes the
    mobile/vertical stream. Do not use this one to link to. Use the one without the 📱 emoji." -> `package.full_episode`
    (the "Ep. NN" upload without the emoji; exactly one per channel or it stays open); `selftest_pack.py` proves it.
39. Thumbnail stills (2026-10-02: "the still you are selecting for the "real thumbnail" have all been terrible...
    Real thumbnail must have eyes at the camera (or looking straight forward because Jake does not look straight to
    camera) and default should be smiling emotion with smile confirmed. If other emotion is the main focus and you can
    find a confirmed still, use, if not, default to smiling. Other emotions- angry, confused, laughing") ->
    `tools/face` (Apple Vision head pose + pupil position in each eye; Core Image's blink and smile classifiers), `thumbs.py frames`
    (gaze gate: Colden 'camera' = yaw / pitch ~0, Jake 'forward' = his own usual pose; pupils centred; smile measured
    against the person's own neutral face; the whole episode camera is scanned once per person and cached), a face-crop
    sheet that is LOOKED at, and `thumbs.py still <n> <emotion> "<what you see>"` - no hook / B thumbnail without it.
    Same day, on a B thumbnail with shut eyes: "this should have failed for jake. no eyes" -> the blink classifier is
    a hard gate on the shortlist AND on the exact full-resolution frame (Vision's eye outline alone reads a shut eye as open).
    Ep 24: C04 wanted "angry" - none confirmed (talking mouths only) -> smile.
Answers of 2026-10-02 (after the final pass):
40. AI thumbnails: "keep rules. do not allow smiling teeth for AI, usually bad result. Can have teeth for different
    expressions" -> `thumbs.py prompt`: a smile = closed-lip grin, NO teeth; angry / confused / laughing may show teeth.
    Real stills keep their teeth (ruling 39).
41. Short swears: "centered beep seems to be working perfectly. allowing the first and last sounds of the word through
    adds to the comedy of the censor. cutting it out completely does not." -> ruling 35 stands as built: 3 frames of
    the word through at each end, a word too short for that = one 3-frame beep centred on it. Never bleep the whole word.
42. Loudness: "keep the gain on the masters so peaking is below 0 db" -> his A1 strip stays as it is; `master.py`
    finishes every master at -14 LUFS with true peaks <= -1 dBTP (a preview may still peak over 0 - only the master counts).
43. Delivery: "the final renders are still living on disk not NAS... In NAS under the episode folder, final files should
    be in sub folder "Final" then sub folder "Clips". Each final with locked A YouTube title as the file name. And
    dashboard built for clips." ... "I think it should be the final steps here" -> `deliver.py`, run by `package.py
    build`: `<episode>/Final/Clips/<title A>.mp4` + Thumbnails/ + Captions/ + `Ep NN Clips Dashboard.html`, every copy
    verified, every record repointed to the NAS, the Mac copies to the Trash. The aggregator starts from Final/Clips.
    Same day: "Edits are fine to stay on local HD until locked. Faster transfers and a fail safe with trashcan" ->
    previews, versions and masters are made on the Mac; nothing goes to Final/Clips before the lock + package approval.
44. Packaging learns (2026-10-02): "Can you make sure each weeks packaging generation actually utilizes, and learns
    from, this data?" -> `pack_learn.py`: the Monday scrape (per-video CTR both channels, Test & Compare results), the
    API pull, his package picks and our own live uploads become `data/packaging_brief.md` (patterns WIN / LOSE / WEAK
    with n, the A/B tests word for word). `package.py check` refuses copy that did not use the current brief, and every
    B / C must be an experiment with a written hypothesis, so each A/B result teaches the next brief.
45. (RETIRED by 47) AI thumbnails from Colden's JSON template (2026-10-02): "This template will work for both" (GPT Image 2 + Nano Banana
    Pro); the person is only "@Image1" ("the tag...as i told you... is @Image1"); the reference is a clean full frame
    ("USE THE FULL IMAGE FROM RESOLVE", "Do not use distorted or mid word images. ever"); wardrobe from the episode
    stills ("not just a black t every time"); default expression "believable expression tied to the topic"; a podcast
    mic "is certainly allowed as a prop". -> thumb_prompt.py + selftest_prompt.py.
46. **RULE 1 - the thumbnail is the hook** (2026-10-02): "The thumbnail and the title are the only thing that engages a
    viewer to watch my show. the thumbnail needs to be visually diverse and explain what's to come in the video ...
    make it rule 1 when creating these thumbnails" -> Stage 3 step 3; gated in thumb_prompt.rule1 + thumbs.py add --reads.
47. Prose prompts + new models (2026-10-03): "I would like to return to the prose style prompt from before.
    /CWC_PodReels just did exhaustive tests and came up with a perfect prompt system. copy their system into the 16:9
    format. for the two models ... 1. GPT Image 2.5 sunburst 16:9, quality high, resolution 1k 2. Grok Imagine 2.0
    quality medium, resolution 1k, 16:9" -> thumb_prompt.py (prose builder + gate), selftest_prompt.py. Their tests:
    the JSON prompts drifted the likeness (0.14-0.23), the ~950-character prose kept it (0.85-0.91).
"Build all your hardening suggestions": data before selection (freshness gate), evidence-bound themes, the cold read,
the package scored, length follows the story, decisions logged and tied to results. All six are below.

## Prerequisites (`doctor.py` checks them - except the Higgsfield connector, the glitch pack and Colden's A1 strip)
| What | Detail |
|---|---|
| A LOCKED CWC PodCut | `<CWC Podcast>/work/cache/<show>/<EpNN>/manifest.json` with `locked`, no open `rebuild`; the lock snapshot holds `plan.json`, `words.json`, `pod_dump.json` (the edit builds from it), `lower_thirds.json`, `layout.json` |
| The show file | `shows/<show>.json` with a `packaging` block and an empty `first_run_ask` (a new show stops at intake until Colden has answered it - Colden and Todd is NOT set up yet) |
| NAS | the episode folder mounted (`/Volumes/Current Projects/...`; show notes, cameras, b-roll); `#recycle` on the share |
| Python 3.9+ | numpy, opencv-python (FaceDetectorYN), Pillow, playwright (+ chromium), google-api-python-client, google-auth |
| Programs | ffmpeg / ffprobe, textutil, pdftotext, Google Chrome (hook overlay; Sora font from Google Fonts), `tools/face` + `tools/facequality` (`make -C tools`, needs swiftc) |
| Resolve | Studio 21.1 running on the episode's project (External scripting = Local; `rs.py` never switches projects - CWC_PodCut's `open_project.py` does); `00 PodClips Template` in that project (once per project: `python3 $S/rs.py 120 $S/r_template.py 'PROJECT="<project name>"' 'NAME="00 PodClips Template"' 'SOURCE="00 Clips Template"'` - it copies edit-clips' empty UHD template, which must exist; then Colden puts his compressor / NR / EQ on A1 - ask him, never guess the strip); in the media pool by name: `CR Stinger INtro 5 s.mov`, `The Creative Lens Stinger.mov`, `CR End Screen .mov`, `Heavy Riff (1 ).mp3`, `CR Endscreen Glitch, whoosh, transition, hit.png.wav`; render preset `H.264 Master`; the "Drag-N-Drop Glitch Transitions" pack (GTR_02) |
| Censor beep | `~/Documents/Video FX, LUTS, Etc/SFX/Short Censor Beep.wav` (the Power Bin beep, ruling 35) |
| Telegram | `TG_BOT_TOKEN` (~/.zshrc, the @VideoEditReview_bot token), chat id in `~/.config/cwc/telegram.json` or the edit-shorts pairing; `tg_listen.py` running |
| YouTube | OAuth tokens `~/.config/edit-clips/youtube/{cwc,tcl}.json` (made by edit-clips; a dead token is exit 2, never an interactive sign-in from here) |
| Data | the Monday Studio scrape `.../Create with Colden/trend_research/channel_metrics.json` (stale -> `check.py` asks for a waiver in his words); the daily trend scan `~/Documents/Claude/CreateWithColden/trend_research` |
| AI thumbnails | the Higgsfield connector (`gpt_image_2`, `nano_banana_pro`) |

## Where things live
- WORK = `Create with Colden/CWC Podcast/clips/<show>/<EpNN>/`:
  `episode.json phrases.json transcript.txt show_notes.txt trends.md platform/ themes.json cold/ checked.json waivers.json`
  `review/ (state.json, events.log)  approved.json`
  `edit/<id>/ (cut.<ch>.json, broll.json, build.<ch>.vN.json, versions.json, preview/, master/)  edit/review.json  lock.json`
  `package/<id>/ (facts.<ch>.json, copy.<ch>.json, thumbs.<ch>.json, thumbs/<ch>/, *.srt, package.<ch>.json)  package/review.json`
  `caption_fixes.json  delivery.json`
- Shared data: `Create with Colden/CWC Podcast/data/` (channels/<ch>/videos.json + channel.json, channel_summary.md,
  decisions.jsonl, published.jsonl, learnings.md, quota.json, awaiting_notes.json).
- Everything that happens on Telegram: `WORK/review/events.log` (watch it: `tail -F`); the listener's own log:
  `~/.config/cwc/tg_listen.log`.
- Two clocks: BASE = seconds of the program file (PodCut's clock); CUT = seconds on the locked timeline (every
  timecode this skill shows). A clip has its own clock (0 = the first frame of the cold open).
- B-roll files: `<episode>/Clips/B-Roll/Source` (captures) and `<episode>/Clips/B-Roll` (rendered clips) on the NAS.

## THE RUN, in order (S = the scripts folder, W = WORK)
```
# ---------- Stage 1: themes ----------
python3 $S/intake.py "<PodCut CACHE>"            # locked cut -> W: transcript in phrases, show notes, screen shares
python3 $S/channel_data.py pull                  # both channels through the API (~3 min)
python3 $S/learn.py report                       # his past approvals / kills / notes + what published clips did -> channel_summary.md
python3 $S/evidence.py trends "$W"               # today's news from the daily trend scan
#  READ: data/channel_summary.md -> W/transcript.txt (ALL of it) -> W/show_notes.txt -> W/trends.md. List the candidate stories. Research each.
python3 $S/evidence.py search "$W" <slug> "<query>" ["<query>"]     # platform proof per candidate topic (BEFORE scoring it)
#  write W/themes.json (shape: Stage 1 step 6)
python3 $S/assemble.py "$W"                      # each theme in play order -> W/cold/<id>.txt
python3 $S/coldread.py prompt "$W" <id>          # the brief for a FRESH agent (save it as W/cold/<id>.prompt.txt)
python3 $S/coldread.py record "$W" <id> <answer.json | ->    # the agent's JSON, from a file or stdin
python3 $S/check.py "$W"                         # every gate -> checked.json (1 = fix themes.json, 2 = ask / flag)
python3 $S/tg_themes.py send "$W"                # --dry-run prints the cards.  check.py exit 2 "too_few" -> tg_themes.py flag "$W" instead
#  his taps -> W/review/events.log ; Notes -> revise, assemble.py, cold read, check.py, tg_themes.py resend "$W" <id> ; all settled -> approved.json
# ---------- Stage 2: per approved theme ----------
python3 $S/cut.py "$W" <id> [--channel cwc|tcl]  # the edit plan (default channel = the card's suggestion); fix every PROBLEM
#  b-roll: capture.py <url> "<episode>/Clips/B-Roll/Source/<name>.png" [--anchor "text"] -> LOOK -> broll.py prep -> write W/edit/<id>/broll.json
python3 $S/build.py "$W" <id> [--channel ..]     # a NEW version in Resolve (source gate -> create -> place -> verify)
python3 $S/review.py render "$W" <id> [--channel ..]    # 720p preview + checks + contact sheet  -> LOOK at the sheet
python3 $S/review.py ack "$W" <id> "<what you saw>" [--channel ..]
python3 $S/tg_edit.py send "$W" <id> [--channel ..] [--note "<one short line>"]
#  his tap: Approve (channel / Both) or Changes -> fix, build.py (vN+1), review, ack, send (the old card retires itself)
python3 $S/build.py "$W" <id> --channel <other>  # when he approved a channel the card was NOT built for (Both, or only the other one): same edit, that channel's stinger, approved by itself
python3 $S/master.py render "$W" <id> <cwc|tcl> [--no-lock]   # per approved channel; the LAST one of the episode locks + cleans up
# ---------- Stage 3: per locked upload (clip x channel) ----------
python3 $S/channel_data.py pull                  # today's: the full episode must be public to be linked
python3 $S/package.py facts "$W"                 # masters, chapter points, captions, handles, full-episode link + the packaging brief
#  READ data/packaging_brief.md (ruling 44) before writing any title or thumbnail idea
#  write W/caption_fixes.json from the "names to check" lists, run facts again; write W/package/<id>/copy.<ch>.json
python3 $S/package.py check "$W"
python3 $S/thumbs.py frames "$W" <id> <ch> --scope episode    # -> LOOK at still_sheet.jpg
python3 $S/thumbs.py still "$W" <id> <ch> <n> smile "<what you see>"    # -> LOOK at eyes_check.jpg
python3 $S/thumbs.py hook "$W" <id> <ch>         # option 2
#  RULE 1: the thumbnail is the hook - stops the scroll, shows what the video is about, every option a different idea
python3 $S/thumbs.py airef "$W" <id> <ch> ; python3 $S/thumbs.py wardrobe "$W" <id> <ch>   # clean reference + episode wardrobe, LOOK, record
python3 $S/thumbs.py prompt "$W" <id> <ch> <ai-1|ai-2|C> --promise ".." --object ".." --scene ".." --expression ".."   # -> check-prompt -> generate as printed
python3 $S/thumbs.py add "$W" <id> <ch> <image> <slot> --model <m> --gen-id <job> --reported-model <m> --saw ".." --reads ".."
python3 $S/thumbs.py grid "$W" <id> <ch> ; python3 $S/tg_pack.py send "$W" <id> <ch>
#  his pick (events.log "PACKAGE PICKED") -> write "B", "C", "hook_headline_B" into the copy ; package.py check
python3 $S/thumbs.py abc "$W" <id> <ch>          # B ; then C: prompt --title "<C>" -> generate with A's model -> LOOK -> add ... C ; abc again
python3 $S/tg_pack.py send-abc "$W" <id> <ch>    # LOOK at abc_grid.jpg first
python3 $S/package.py build "$W"                 # package.<ch>.json per upload + W/delivery.json ; scratch to the Trash ;
#                                                  then deliver.py: Final/Clips on the NAS + the dashboard, the Mac cleaned (ruling 43)
python3 $S/learn.py report                       # close the loop for the next episode
```
One clip does not wait for another: plan / build / review the next clip while a card is with Colden - but never send a
second preview of the SAME clip before he answered the first, and keep cards in a sensible order (best clip first).

## Stage 1 - themes
The commands are in THE RUN above; this is the judgement and the rules.
### How to build the themes (the judgement part - do all of it)
1. **Know what works before reading the episode.** `channel_summary.md`: which topics, lengths and hook types got views,
   7-day views, % viewed, "kept at 30 s", subs; where clips lose people (steepest drop); the search terms that find
   the channel; the scrape's working-now / avoid lists; `learnings.md` (his past approvals, kills and notes).
2. **Read the whole transcript**, not a search of it. Mark every candidate story: a claim or question worth a title,
   the stretch that develops it, the line that resolves it. A theme may join parts that are far apart (he asked for
   it) - but never so that an answer lands against a question it was not answering, and never by re-using footage a
   stronger clip already uses (10 % rule).
3. **Show notes are context, not truth** ("the guest talked for an hour away from the show notes").
4. **Research every candidate** (web search): what actually happened, dates, prices, whether it is released, announced
   or a rumor ("announced is not released" - edit-clips 2026-09-15). Every claim the title, summary or hook leans on
   goes in `claims` with its status and `source_url`. News / new releases / rumors get `news` with date + source and a
   timeliness score of 4-5: they rank ahead of everything else.
5. **Platform proof**: `evidence.py search` with the queries a viewer would type; cite the ids of videos that beat
   their channel's median. Platform 3 = you cite videos the search found; 4-5 needs one that did at least 2x its
   channel's normal; nothing found = 2 or less, said plainly.
6. **Write `themes.json`** in PHRASE IDS - `{"themes": [ ... ], "rejected": [{"idea": "..", "why": ".."}], "episode_note": ".."}`,
   one theme (every field name as the gates read it):
   ```
   {"id": "t01", "slug": "business-podcast-bubble", "title": "..", "summary": "1-2 sentences, <= 330 characters",
    "hook": {"from": "P0412", "to": "P0413", "quote": "<verbatim>"},
    "body": [{"from": "P0380", "to": "P0455", "why": "setup"}, {"from": "P0610", "to": "P0672", "why": "the turn", "start_word": 3}],
    "payoff": {"from": "P0668", "to": "P0672", "quote": "<verbatim, inside the LAST body range>"},
    "thumbnail": "one concrete image: who, what, the words on it", "evidence_line": "the data reason, one line",
    "scores": {"hook": {"s": 4, "why": "at least 20 characters of reason"}, "payoff": {..}, "story": {..}, "package": {..},
               "channel_fit": {"s": 3, "why": "..", "evidence": ["<video id from data/channels>"]},
               "platform": {"s": 3, "why": "..", "evidence": ["<video id evidence.py found>"]},
               "timeliness": {..}, "self_contained": {..}, "footage": {..}},
    "news": {"time_sensitive": true, "event": "..", "date": "2026-09-30", "source_url": "https://.."},
    "claims": [{"claim": "..", "status": "verified|announced|rumor|opinion|own-experience", "source_url": "https://.."}],
    "shares": [{"at": "0:41:10", "what": "..", "integral": true}], "length_note": "why the story needs this length (outside 5-10 min)"}
   ```
   (`news` only for news; no claims at all -> `"claims": [], "claims_note": "why"`. Edit-stage fields sit on the SAME
   theme object: `trims`, `cold_open_waiver`, `share_plan` - Stage 2.) In words:
   id `t01`.., slug, title (ONE placeholder, <= 100 chars, no em dash, nothing the clip does not support), summary (1-2
   sentences), hook {from, to, quote} (verbatim, <= 14.5 s - it is the cold open, ruling 32), body [{from, to, why}] in PLAY order, payoff
   {from, to, quote} (verbatim, the end of the last range), thumbnail (one concrete image idea), evidence_line (one
   line for Telegram: the data reason this will work), scores (nine dimensions, each {s, why, evidence?}), news, claims
   (or claims_note), shares (every screen share inside the clip: at, what, integral), length_note (outside 5-10 min).
   Write EVERY candidate you would defend (more than 5 is right: the rest become runner-ups); list rejected ideas with
   one line each under `rejected` so the log shows what was considered.
7. **Cold read every theme**: `assemble.py`, then for each id spawn a fresh agent (Agent tool, no other context)
   whose WHOLE brief is the output of `coldread.py prompt` (it sees only what a stranger on YouTube would: the title
   and the clip in play order). Save its JSON answer to a file and `coldread.py record "$W" <id> <file>` (or `-` and
   pipe it in). A FAIL names what a stranger is missing: fix the ranges (add the setup,
   drop the dangling reference) and read again - never argue with the reader, never edit its JSON.
8. `check.py` until it exits 0 (or 2: ask / flag). Then `tg_themes.py send`.

### The rubric (`references/rubric.json`, explained in `references/rubric.md`)
Nine scores 0-5, weighted: hook x3, payoff x3, story x3, package x3 (title + thumbnail idea = CTR), channel_fit x2,
platform x2, timeliness x2, self_contained x2, footage x1 -> a total out of 100. STRONG line 70; hook, payoff, story,
package and self_contained each need at least 3. The cold-read reviewer's numbers CAP the author's hook, payoff and
self_contained. Ranking: strong first, news first (timeliness >= 4 with a dated source), then total. Best 5 delivered,
next ones are runner-ups, the rest held with the reason.
SOFT line 55 (ruling 21): when fewer than 3 themes are strong, themes from 55 up are delivered too (floors and cold
read still apply). Each theme gets a suggested channel: Colden's own when he carries it (his share of the words + 20
for the hook + 20 for the payoff >= 60), else The Creative Lens; the best one for his channel is always marked so.
Fewer than 3 deliverable even then = flag, never pad.

### Gates (check.py; `selftest.py` proves each one fires - run it after any change to check.py / themes.py / the rubric)
| Rule | Gate |
|---|---|
| Runs only on a locked PodCut | `intake.py` exit 2 without a lock or with an open rebuild (`--trial "<why>"` = a labelled test on the last snapshot); `check.py` exit 1 when the lock changed after intake |
| Show notes read each run | `intake.py` exit 2 when the main folder has none (`--no-notes "<his words>"`) |
| Data before selection | `check.py` exit 1 when a channel pull is older than 36 h; exit 2 when the Monday scrape's last good run is older than 8 days (`--waive scrape_stale "<his words>"`) |
| Hook and payoff are real lines | quotes must be found word for word in their phrases (>= 5 words); hook <= 14.5 s (`cold_open_waiver` = his words); payoff at the end of the last range |
| Never cut mid-word / mid-thought | ranges are phrase ids (a phrase = a sentence, or speech up to a pause); cross-talk and continuation-word openings are printed as warnings to fix |
| No footage twice in a clip; <= 10 % shared between clips | structural error inside a clip; between clips the lower-ranked one is held |
| Scores are evidence, not adjectives | every score has a reason; channel_fit >= 3 cites ids from the channel data; platform >= 3 cites ids evidence.py found, >= 4 needs a 2x outlier; timeliness >= 4 needs a dated source |
| Claims verified | every claim has a status; verified / announced / rumor need a source url |
| Integral screen shares are shown | every special layout >= 5 s inside the clip must be declared (what, integral or not); the cold reader is told when the viewer is NOT shown it |
| Length follows the story | estimate = hook + stinger + ranges - dead air over 0.8 s + end screen; outside 5-10 min needs a length_note; under 3 / over 15 is held; mid-roll reported at >= 8:00 |
| Stand-alone | cold read PASS, bound to the hash of the assembled clip (any change voids it) |
| 5 at most, 3 at least | `check.py` delivers <= 5; < 3 = exit 2 + `tg_themes.py flag` |
| One message per theme; kill -> runner-up | `tg_themes.py` (sends only what check.py delivers; re-runs check.py after a kill and sends the next theme that still fits) |
| One message per theme, flow correct | `selftest_tg.py` (run after any change to tg_themes.py) |
| Decisions are logged | every tap and note -> `data/decisions.jsonl`; `learn.py report` -> `learnings.md`, read at step 1 next time |
NOT gated (know it): the scores themselves are judgement (the evidence behind them is checked, the number is not);
"an answer against the wrong question" is caught only by the cold read; whether a separate agent really did the cold
read is an attestation; Whisper's words are the transcript (a mis-heard name passes the quote gate - read names twice).

### Telegram (theme cards)
`tg_listen.py status` first (running, or `start`). `tg_themes.py send` -> a one-line header, then one SHORT message per
theme (ruling 22): a tag line (n/N, length, suggested channel), the title, the 1-2 sentence summary, the hook quote.
Buttons: Approve / Kill / Notes. Payoff, evidence, thumbnail idea, scores and the cold read stay in `checked.json` /
`themes.json` - never on the card.
`flag` (fewer than 3 deliverable): one short line why, then the same short card per held theme (marked HELD);
Approve on a held card is his manual override.
The listener answers every tap at once (watch `W/review/events.log`): Approve -> approved. Kill -> the next runner-up
that still passes is sent (or "no runner-up passes"). Notes -> his next message, or any reply to a theme message, is
stored on that theme (status `notes`): revise `themes.json`, `assemble.py`, cold read again, `check.py`, `tg_themes.py resend "$W" <id>`
(the old card's buttons are removed; a tap on an old card changes nothing). When every theme is approved or killed:
`W/approved.json` + a closing message. That file is Stage 2's input - and binds each theme's text: a later change of
hook / ranges / payoff needs his approval again.
There is no polling command to run: `tg_themes.py poll` exists only for the self-test.

## Stage 2 - edit, review, masters, lock
Rules: rulings 19-39 + `references/carried_rules.md` (the edit-clips rules that still stand, inlined). Settings:
`references/edit.json`. How it was built and why each gate exists: `references/history.md`.
What a clip is on the timeline: cold open (the hook line, <= 15 s) -> the channel's stinger -> body (the ranges in
play order; the hook plays again in context, ruling 30) -> the Colden ending (glitch transition + CR end screen, on
every channel, ruling 29). Every clip is a duplicate of `00 PodClips Template`: A1 "Main Pod Audio" carries Colden's
Fairlight strip (ruling 27); cameras sit under every shot (the wrong angle can be swapped by hand later); output =
the highest camera resolution (ruling 25).

### 1. `cut.py` - the edit plan. Fix every PROBLEM; exit 2 = ask.
| cut.py says | what to do |
|---|---|
| the cold open runs N s (limit 15) | a written trim scoped to the hook: `"trims": [{"phrase": "P0123", "words": [i, j], "in": "hook", "why": ".."}]` on that theme in themes.json (`words` = first and last index removed, inclusive) - kept only where the program audio has a real gap at both ends; else a shorter hook line (a changed hook = back to Colden, see "When things change"); else `cold_open_waiver` = his words (ask) |
| the join into part N cannot be hidden | move that range's edge by a phrase, or `start_word` / `end_word`, so the two sides sit on different cameras or leave a shot long enough to split |
| cut inside a word (X) | cross-talk at a range edge: `"end_word": k` / `"start_word": k` on that body range |
| shot ... is N s | a sliver under 2 s (1 s at an edge): move the range edge; never force it |
| written trim ... was NOT made (no clean gap in the audio / cannot be hidden) / not applied / nothing was trimmed | take that trim out or fix its phrase id; choose other words only where you can HEAR a pause on both sides - never try indexes just to get past the gate. If the trim was Colden's own note and cannot be made clean, tell him so on the next card (`--note`) |
| the hook line is trimmed out of the body (ruling 30) | scope the trim `"in": "hook"` |
| ASK: guest has no close-up of 6 s for the name tag | exit 2 - ask Colden |
| exit 2: ranges changed after his approval | the STORY changed: assemble, cold read, check.py, `tg_themes.py resend` |
| exit 2: a screen share / played clip inside the ranges | the full-screen share layout is not built (ruling 15, "played clips stay in"): ask Colden how to show it and for the full-resolution file; record `share_plan` on the theme |
- `start_word` / `end_word` / trim `words` / the b-roll `anchor.word` are INDEXES into a phrase's words. List them:
  `python3 -c "import json,sys;[print(i,w[0]) for i,w in enumerate(next(p for p in json.load(open(sys.argv[1]+'/phrases.json')) if p['id']==sys.argv[2])['w'])]" "$W" P0123`
  (`start_word` = the first word kept, `end_word` = the last word kept).
- What `cut.py` decides by itself: pause trims (over 0.8 s, checked against the program audio), every splice hidden by a
  camera change, else a 1.25x punch-in on the eyes (never a jump cut, ruling 23); a punch toggle every <= 10 s on a long
  close-up; the guest's name tag once, on the first 6 s close-up of the body; a censor window on every swear (3 frames
  of the word through at each end, ruling 35; the word start from the waveform; overlapping swears = one window).
- `listen (possible softened swear): "hit" at 2:07` - LISTEN to each. A real swear the transcript softened: in
  `phrases.json` change ONLY that word inside the phrase's `w` list (`w[i][0]`; never `text` - that would void his
  approval and the cold read) and plan again: it is then beeped and masked in the captions. This is the one hand edit
  of phrases.json; a new `intake.py` run would lose it. A clean word: leave it - `tg_edit.py send` names it on the
  card by itself.
- `--no-audio` is for the self-test only (it skips the audio checks). `build.py` plans again by itself, with audio,
  and refuses when the program audio cannot be read (NAS not mounted).

### 2. B-roll - producer mode (ruling 33: in every v1) -> `W/edit/<id>/broll.json`
Read the clip (`W/cold/<id>.txt`) and list every NAME, PRODUCT, NUMBER or PLACE a stranger would want to see - b-roll is
the only way to explain a name (no text boxes). Typically 1-4 per clip, 3-6 s each. Research each (web search) so that
what is shown is true and agrees with what is said at that moment (a chart whose number contradicts the line is worse
than none). Sources, best first: Colden's own footage / graphics (ask when the film IS the subject) -> the real page
(article, product page, channel page, chart, Wikipedia) -> a generated image only for a generic scene, never a real
person, never when the real thing exists.
```
python3 $S/capture.py "<url>" "<episode>/Clips/B-Roll/Source/<name>.png" [--anchor "text on the page"] [--wait <seconds, default 2.5>] [--full]
#  LOOK at the PNG (Read it): the real content? no consent wall / 404 / "Access Denied" / bot check? If blocked: another real source, or none.
python3 $S/broll.py prep "<episode>/Clips/B-Roll/Source/<name>.png" "<episode>/Clips/B-Roll/Source/<name> 16x9.png" --box x0,y0,x1,y1   # fractions of the capture: the part that matters, padded to 16:9
```
```
{"items": [{"src": "<.../Source/<name> 16x9.png>", "origin": "<url>", "anchor": {"phrase": "P0499", "word": 10},
            "seconds": 5, "move": "push", "why": "<what it explains at this line>",
            "looked": "<what the capture shows - and that it agrees with what is said>"}]}
```
`move`: push (default), pull, pan_left, pan_right, fit_blur (a picture that is not 16:9). Stills only (png / jpg).
A clip that truly needs none: `{"items": [], "waiver": "<Colden's words>"}` - ask him. `build.py` snaps each edge onto
a cut or 15 frames clear and refuses b-roll in the cold open / stinger, over the name tag, in the last 1.5 s,
overlapping another, or shorter than 3 s.

### 3. `build.py` -> 4. `review.py render` -> LOOK -> `review.py ack`
`build.py` always makes a NEW version (`Ep NN Cxx <Title> <CH> vN`, red DRAFT marker); a failed one keeps its
`zz BUILDING` name and its number. `review.py render` renders 720p, checks the frame count, the loudness, the CENSOR
(under each beep the voice must be >= 12 dB down and the tone present - measured, not assumed) and writes the contact
sheet. LOOK at `<preview> sheet.jpg` (Read it) and check, then say it in the ack (>= 30 characters):
- every camera frame shows THIS episode (wardrobe, set) - one frame of every camera is on the sheet for this reason;
- punched shots keep the eyes in frame; the first frame is not a blink;
- every b-roll shows the intended region, legible, full frame;
- the name tag: right guest, spelling, handle; the stinger is this channel's; the glitch transition and the end screen
  are there; no black frame.

### 5. `tg_edit.py send` - the review card
One short caption (ruling 22). The card names by itself every written trim inside a sentence, every softened swear left
unbeeped, a cold-open waiver. `--note` (<= 200 characters) is for one more thing he must know (an assumption in the
b-roll, a line you are unsure about) - not for a description of the clip.
His tap: **Colden's channel / Creative Lens / Both** = approved for those channels; **Changes** = his next message is
the note (events.log `EDIT NOTES`).

### 6. Changes -> the next version
Read his note. Fix the cause where it lives (themes.json: trims, word edges, waiver; broll.json; a rule -> new ruling +
gate + test). `cut.py` -> `build.py` (vN+1) -> render -> LOOK -> ack -> send. Sending vN+1 retires the vN card by
itself (buttons stripped, status superseded). A version that must not be used and was never sent:
`tg_edit.py supersede "$W" <id> <ch> <vN> "<why>"`. He does not want the clip at all:
`tg_edit.py drop "$W" <id> "<his words>"` (before the lock; once a version is locked the script refuses - ask him what
to do with the timeline and the master).

### 7. Both channels, masters, lock
- Approved for a channel the card was not built for (Both, or only the other one - a master carries its channel's
  stinger): `build.py "$W" <id> --channel <that one>` makes the same edit with that stinger; it is approved by its edit
  signature and gets no card. Its picture is checked by `master.py` (below).
- `master.py render "$W" <id> <ch>` (after the tap, never before - ruling 28): renders at the output resolution,
  finishes the loudness (-14 LUFS +-0.5, true peak <= -1 dBTP; picture untouched), and compares the master's stinger and
  end screen with the source files (the right channel's stinger, the ending in place) - a mismatch fails.
- When the last master of the episode exists, `master.py` runs `lock.py`: every approved timeline -> "(L)" + green
  LOCKED marker; everything else of the episode -> .drt backup + removed; previews, raw masters, scratch -> Trash /
  NAS `#recycle`. `lock.py` refuses (exit 2, nothing touched) while anything is half-way: a newer build than the
  approved one, an open card, a Changes note without a new version, a channel without its build or master.

### Gates of Stage 2 (each proven by `selftest_cut.py`, `selftest_cards.py` or measured on Ep 24)
| Rule | Gate |
|---|---|
| Only an approved theme, as approved | `cut.py` exit 2 when the id is not in approved.json or the assembled text changed after his approval |
| Cold open <= 15 s (ruling 32) | `check.py` (hook phrases <= 14.5 s) at the theme stage; `cut.py` PROBLEM; `cold_open_waiver` = his words |
| Never mid-word; trims only in a real gap | `cut.py` "cut inside a word"; a written trim needs an audio gap at both ends (`_dip`), reported when not applied |
| Never a jump cut (ruling 23) | every splice hidden by camera or a 1.25x punch on the eyes; an unhidden splice is a PROBLEM; no face = no punch (build fails) |
| Screen shares / played clips shown (ruling 15) | `cut.py` exit 2 until `share_plan` records his answer |
| Swears beeped, never cut (rulings 24, 35) | trim over a swear fails; censor windows from the waveform; `review.py` measures the duck and the tone |
| B-roll in every v1, real and looked at (ruling 33) | `build.py` fails without broll.json; each item needs `origin`, `why`, `looked`; placement gates |
| The right source files (2026-10-01) | SOURCE GATE before anything is created (every clip by name AND path, cameras = the locked PodCut's); VERIFY re-reads every piece's path; every camera on the sheet |
| Nothing destructive | a build never replaces a timeline; verify-or-keep `zz BUILDING` |
| The preview was checked and looked at | `tg_edit.py send` needs `review.py check` clean + `ack` bound to the sheet's hash; only the newest VERIFIED version is reviewed or sent |
| A tap means what he saw | a tap counts only on a version's CURRENT card while that version is live; a new version retires older cards |
| Masters only after approval; right stinger; -14 LUFS | `master.py`: approved-for-this-channel only, frames = plan, loudness finish, stinger + end screen compared with the sources |
| Lock only when everything is finished | `lock.py ready()` (above); .drt backup before every removal |
NOT gated (know it): whether the b-roll is the BEST choice; whether a softened word was really listened to; the look at
the sheet is an attestation; `--note` content; true peaks over 0 dBFS on his A1 strip are measured and stored, the
master is limited to -1 dBTP (open item with Colden); the Sora font falls back silently when offline.

## Stage 3 - packaging (per locked upload = clip x channel)
Rules: `references/carried_rules.md` ("Thumbnails", "Copy"), rulings 37-39, the show file's `packaging` block.
The posting plan, uploads and Studio work are NOT here (ruling 37) - `references/aggregator_handoff.md`.

### 1. Facts, captions, names
`channel_data.py pull` (today), then `package.py facts`. It prints, per upload: the chapter points (0:00 = the cold
open, then the first word of each body range), who is heard in the clip, and the caption check lists. The full-episode
link is the PUBLIC "Ep. NN" upload without the phone emoji (ruling 38); not public yet -> the description keeps
`{FULL_EPISODE_URL}` and `needs` says so: pull and run `facts` again once it is live, or leave it to the aggregator.
Captions: read the printed `names to check` and `case varies` lists against the conversation (who / which product is meant). Put real
corrections in `W/caption_fixes.json` - `{"Krieger": "Cregger", "higgs field": "Higgsfield", "_lower": ["Create"]}`
(single words also fix `'s` / plural; several words allowed; `_lower` = plain words Whisper capitalised mid-sentence) -
and run `facts` again. A caption file is not done until both lists are explained.

### 2. `copy.<ch>.json` - the words (one file per upload; a clip on both channels gets two, written for each audience)
FIRST read `data/packaging_brief.md` (`package.py facts` rebuilt it from this week's data - ruling 44): which title
patterns WIN / LOSE on these channels (each against its own channel's median CTR, with n), the finished A/B tests word
for word with their thumbnails, his picks, how our own live uploads did and which A/B hypothesis won, and the scrape's
own packaging calls. `pack_learn.py features "<title>"` shows what the gate measures in a title.
```
{"titles": ["..", "..", ".."], "summary": "1-4 sentences", "chapters": [{"part": "hook", "text": ".."}, {"part": 0, "text": ".."}],
 "pinned": "one engagement question", "topic_tags": [".."], "hook_headline": "2-4 WORDS", "hook_accent": "WORD",
 "thumb_emotion": "smile", "claims_checked": [{"claim": "..", "status": "verified", "source": "https://.. or P0123"}],
 "brief": "<the brief id>", "learned": [{"id": "T-money", "how": "title 1 leads with the price cut"}, {"id": "AB-DnLuxJxJDUc", "how": ".."}],
 "explore": {"3": "only when a title carries a LOSE pattern on purpose: what it tests"}}
```
- **brief / learned**: the current brief's id, and 2+ pattern or A/B ids from it that shaped THIS copy, each with how.
- At least one of the three title options carries a WIN pattern (when the brief has one). A LOSE pattern only as a
  declared test in `explore`. WEAK = not enough evidence either way: judgement, but say in `learned` what you lean on.
- The thumbnail idea and the AI prompt use the thumbnail lessons too (`thumbs.py prompt` prints the A/B thumbnail winners).
- **Titles**: three genuinely different angles (a question, a claim, a curiosity gap; the first 5 words of each must differ), the hook in the first ~45
  characters (the feed cuts there), search words from `channel_summary.md`, <= 100 characters, no em dash, no "|",
  nothing the clip does not deliver; "announced" is not "released" (a claim of release needs a verified source).
- **Summary**: who says what and why it matters, in his voice - direct, no hype, no hashtags, no dashes.
- **Chapters**: `part` = "hook" (always the first, 0:00) or the index of a body range (from the facts' chapter points); at least 3, each >= 10 s
  (leave a short part out), text <= 60 characters. They exist only in the description - never on the picture.
- **Pinned**: one question that invites an answer (2 sentences at most); no link, no "comment below / let me know / subscribe".
- **Topic tags**: what a viewer would type, <= 30 characters each, the most specific first; the show's stock tags fill
  the rest to 470-500 characters counted the way YouTube counts.
- **hook_headline**: the hook distilled into 2-4 words for the overlay (not the title; 32 characters at most; letters,
  digits and ' $ % & . , - ? ! only); `hook_accent` = the one word
  in purple. 4 words -> also `ai_headline` (<= 3 words) for the AI images.
- **thumb_emotion**: smile (default) | laughing | angry | confused - only when that emotion is the clip's point; if no
  still clearly shows it, confirm a smile (ruling 39).
- **claims_checked**: what the titles and the summary assert, each with a status (verified / announced / rumor /
  opinion / quote / own-experience) and a source (a url, or the phrase id where it is said).
`package.py check` until "copy OK".

### 3. Thumbnails - RULE 1 first, then four options (confirmed still, still + headline, two AI)
**RULE 1 - THE THUMBNAIL IS THE HOOK** (Colden 2026-10-02: "The thumbnail and the title are the only thing that
engages a viewer to watch my show. the thumbnail needs to be visually diverse and explain what's to come in the video."
He calls it rule 1 - it outranks every other thumbnail rule; everything else only serves it):
1. **Stop the scroll.** One bold idea, strong contrast, an action - read in under a second at 320x180.
2. **Say what the video is about.** The topic object is IN the picture (a podcast clip shows podcast mics, a camera
   clip the camera) and the image makes a promise the video pays off. A generic face + chart + text says nothing.
3. **Be visually different.** The two AI options are two different concepts - never one idea on two models; thumbnail
   C is a new idea for title C; no clip of the episode repeats another clip's idea. Same clip on its other channel may
   share it. Use the brief (packaging_brief.md): what won A/B tests on the channel.
Before any AI prompt write the click promise (what the viewer wonders, what the video answers) and the topic object;
after it, LOOK at the 320x180 copy and say what a stranger understands from it (`--reads`). Gated in thumb_prompt.py:
promise must be about THIS video (shares words with its titles / summary / hook), the object must be in main_prompt,
a concept that repeats another option or clip is refused, `add` needs `--reads`.

**The real still (options 1 + 2)**
- `thumbs.py frames ... --scope episode` scans the speaker's whole camera (cached per person). Who: @ColdenRaisher =
  always Colden; otherwise the clip's main speaker. LOOK at `still_sheet.jpg`: 12 face crops that passed the eyes gate
  (blink classifier: both eyes open; pupils centred; to camera - Jake: straight ahead; no squint) ranked for the
  emotion. Choose one where the eyes are clearly visible and the expression fits; use a different still per upload.
- `thumbs.py still ... <n> smile "<what you see, >= 20 characters>"` re-checks that exact frame at full resolution and writes
  `eyes_check.jpg` - LOOK at it (face + both eyes, large). Refused = pick another number, never force it.
- `thumbs.py hook` = option 2: the headline (2-4 words that say what the video is about - Rule 1.2) over the still.

**The two AI options (ruling 47: the PROSE recipe from CWC_PodReels' tests, thumb_prompt.py)**
- Models (Colden 2026-10-03): **ai-1 = GPT Image 2.5 `gpt_image_2_5`, variant sunburst, quality high, 1k, 16:9**;
  **ai-2 = Grok Imagine 2.0 `grok_image_2_0`, quality medium, 1k, 16:9**. Both: ONE reference, role `image_references`.
  Thumbnail C = the model of A (GPT Image 2.5 when A is not AI). check-prompt prints the exact params - use them as printed.
- `thumbs.py airef "$W" <id> <ch>` -> LOOK at `airef_sheet.jpg`: CLEAN reference frames only - full camera frames
  (never the master, never a crop), eyes open to the lens, LIPS TOGETHER, sharp. Pick the frame whose expression fits the
  idea - the model copies the reference's expression more than the prompt's. `thumbs.py airef ... <n> --saw ".."`.
- `thumbs.py wardrobe` -> LOOK at the sheet -> `--saw "<exactly what they wear>"`.
- For EACH AI option a different concept (Rule 1.3): `thumbs.py prompt "$W" <id> <ch> <ai-1|ai-2> --promise "<click
  promise>" --object "<topic object>" --scene "<one concrete idea: where, what is held or done with the object, the
  light>" --expression "<what the face does; a smile = lips closed>" [--side right|left]`. The builder writes the prose
  (~950 characters, fixed order: format, "the man in @Image1 ... keep his real face exactly as it is", the episode
  wardrobe, the scene, the expression + eyes into the lens, face large on one side, the headline in quotes in big bold
  white condensed capitals with a black outline on the other side, bottom-right clear, a short fixed tail). Never edit
  the text by hand - change the inputs and rebuild. Write scene and expression as what IS there: "no / not / without"
  in them is refused (naming a thing invites it). The second concept may carry its own headline: copy `ai_headline_2`.
- `thumbs.py check-prompt` -> generate exactly as printed -> LOOK at the image AND its 320x180 copy -> `thumbs.py add
  ... --model <m> --gen-id <job> --reported-model <what jobs_wait reports> --saw ".." --reads ".."`. REJECT and
  regenerate when Rule 1 fails, the likeness is off, the text is misspelled or carries extra punctuation, teeth show on
  a smile, earbuds or the own boom mic appear (a prop mic is allowed), or a real third party / logo appears.
- `thumbs.py grid` -> `tg_pack.py send`: he picks one title and one thumbnail = A.

### 4. A/B/C (YouTube Test & Compare) after his pick
The listener has written `"A"` (his title) into `copy.<ch>.json` and the pick into `thumbs.<ch>.json`: READ the copy
file again and ADD to it - never rewrite it from what you had before the pick. Add `"B"` and `"C"` - new angles on the same clip, the first 5 words of A / B / C all different,
never one of the options he passed over - and `"hook_headline_B"` (+ `hook_accent_B`), the headline of thumbnail B.
B and C are EXPERIMENTS (ruling 44): each changes one measured feature against A (a question, a $ figure, first
person, conflict ...; `pack_learn.py features` shows them) - `"ab_tests_plan": {"B": "what B tests against A", "C": ".."}`.
The test then answers a question the next brief can use; a B with A's exact features is refused.
`package.py check`. `thumbs.py abc` builds B (the confirmed still + that headline). C: a NEW idea for title C (Rule 1.3):
copy `ai_headline_C` (2-5 words), `thumbs.py prompt ... C --promise .. --object ..`, fill, check-prompt, generate with the
model that made A (`gpt_image_2` when A is not AI), LOOK, `thumbs.py add ... C --model .. --saw .. --reads ..`,
`thumbs.py abc` again -> LOOK at `abc_grid.jpg` (three different pictures, three different ideas) ->
`tg_pack.py send-abc`. His Approve closes the upload. Notes -> fix and send the card again (the old one retires).

### 5. `package.py build` -> `delivery.json` -> `deliver.py` (the last step of the skill)
Per upload `package.<ch>.json` (master, captions, A/B/C titles and thumbnails with their kind and model, description
with chapters and the footer on @ColdenRaisher only, tags, playlists, category, flags, pinned comment, claims, push
order) and, when every locked upload is complete, `W/delivery.json`. The packaging scratch (face scans, candidates)
goes to the Trash. `needs` lists what is still open (the full-episode link) - tell Colden in one line.
Then, by itself, `deliver.py` (ruling 43) - `--dry-run` prints the plan:
- `<episode>/Final/Clips/<title A>.mp4` per upload (title A exactly, minus `\ / : * ? " < > |`; a clip on both channels =
  two files, each named by its own title A), `Thumbnails/<title A> - A|B|C.<ext>`, `Captions/<title A>.srt`, and
  `Ep NN Clips Dashboard.html` (episode tab: push order, channels, full-episode links, posting rules; one tab per upload:
  the video, A/B/C titles + thumbnails, description, tags, pinned comment, chapters, Studio settings - copy buttons).
- Every copy is verified (size + SHA-256) before anything else moves. Then every record (versions, lock, facts, thumbs,
  package, delivery) points at the NAS copy, and the Mac copies go to the Trash (masters, the thumbnail work folders,
  the .srt files). The small JSON / text records stay in WORK. `W/delivered.json` keeps what went where.
- NAS not mounted = exit 2 (ask him to mount it; nothing moved). Two uploads with the same title A = exit 1 (one title
  A must change, through the package card). A fix after delivery: `package.py build` again - the replaced NAS file
  goes to the share's `#recycle`, the new one is copied and verified.
- The aggregator reads `W/delivery.json`: its paths are the NAS files.

### Gates of Stage 3 (`selftest_pack.py`, `selftest_cards.py`)
| Rule | Gate |
|---|---|
| Only locked clips are packaged; a show needs its packaging block | `package.py` exit 2 without lock.json / without `packaging` |
| Titles, summary, chapters, pinned, tags, claims | `package.py check` (docstring lists every limit; tags counted as YouTube counts them) |
| Full-episode link: public, this show, not the vertical copy (ruling 38) | `package.full_episode`; otherwise left open in `needs` |
| Captions are readable and true | per-speaker cues, no overlap, no cue under 0.5 s, swears masked; the name lists are a LOOK |
| Real still: eyes + smile (ruling 39) | `thumbs.eyes_ok` on the shortlist AND on the exact full-resolution frame; the frame used is matched to the frame on the sheet by its pixels; no hook / B without a confirmed still |
| RULE 1: the thumbnail is the hook | click promise about THIS video + topic object in the scene + no repeated concept (thumb_prompt.rule1); `add --reads` = what a stranger gets at 320x180 |
| AI images come from the prose recipe, a clean reference, the right model, and were looked at | `thumbs.py airef` (full camera frame, lips together) -> `prompt` / `check-prompt` (ruling 47 gates: unedited builder text, ONE reference, @Image1 only, exact headline, topic object in the scene, no negations in scene / expression) -> `add` (checked prompt unchanged, slot model, job id, `--saw`); C is bound to the title C it was made for |
| A, B, C are three pictures; B has its own headline | `tg_pack.py send-abc` / `package.py build` (file hashes; `hook_headline_B` required and different) |
| Packaging learns from the weekly data (ruling 44) | `package.py check` -> `pack_learn.problems`: current brief id, 2+ learned ids that exist, a WIN pattern among the options, LOSE only as a declared test, B / C each with a hypothesis and a measured change against A; live uploads linked by title and judged by their own CTR + A/B result (`selftest_learn.py`) |
| His approval covers what is delivered | a tap counts only on the current card; a re-sent card 1 voids the pick and A/B/C; a note or any changed title / file after the approval re-opens it; `package.py build` requires the approval of the set AS IT IS NOW |
| The package belongs to the current lock | `package.py build`: facts' timeline and master = lock.json's; master and SRT on disk |
NOT gated: the dashboard's look (open it once per episode);
whether a title is GOOD; whether the AI image is on brand; the "aim for 70 characters / hook in the first 45"
advice; whether Colden is the subject of an AI image on his channel (your look); the AI-use flag is always "No" - if a
clip carries a GENERATED realistic b-roll image, tell Colden.

## When things change
- **Notes on a theme card** -> revise themes.json, `assemble.py`, cold read, `check.py`, `tg_themes.py resend "$W" <id>`.
- **Kill on a theme card** -> the listener sends the next runner-up that still passes; nothing to do.
- **You need to change an approved theme's hook / ranges / payoff** (a cut cannot be made clean, a share cannot be
  shown) -> that is a new story: same loop as Notes; `cut.py` refuses (exit 2) until his approval of the revised card.
  Trims, word edges and waivers are edit decisions and need no card.
- **Changes on an edit card** -> Stage 2 step 6.
- **He does not want a clip any more** -> `tg_edit.py drop "$W" <id> "<his words>"` (before the lock; after it, ask).
- **A change AFTER the lock** (he watches a master and wants a fix) -> first move the b-roll captures back: the
  cleanup sent `<episode>/Clips/B-Roll/Source` to the Trash / `#recycle` (`lock.json` -> `cleanups[..].files_moved` has
  both paths; `build.py` prints the place when a source is missing). Then a new version: `build.py`, review, ack, send,
  his approval, `master.py render ... --no-lock`, `lock.py --dry-run` (read it), `lock.py`. It locks the new one, exports the old locked timeline as .drt and
  removes it, trashes the old master. Then `package.py facts` + `build` again for that upload (captions and chapter
  times moved; the copy and the A/B/C approval stand unless the content changed - then send the cards again).
  The Resolve side of replacing a locked timeline had not run when v1.1 shipped: the first time, do it with Colden present.
- **The PodCut is re-opened or re-locked after clips exist** (`next.py` says so) -> STOP and ask. Clips already locked
  and mastered stay valid (they are finished files). Anything not locked was planned on the old cut: phrase ids move
  on a new intake, so themes, cold reads, trims and b-roll anchors must be redone on the new lock - Colden decides
  whether that is worth it.
- **A new show (Colden and Todd)** -> `intake.py` stops (exit 2) with the questions in the show file's
  `first_run_ask`. Answer them with Colden, write the answers into the show file (channels, playlists, footer,
  handles, gaze, assets, the project's template), empty the list. Its frame rate differs (24 fps): the first build is
  a pilot - look at the censor timing, the stinger and the ending with him before trusting the defaults.
- **A rule changes** -> quote Colden in "Colden's rulings", change the gate, add a self-test case, run all self-tests,
  restart the listener if a Telegram script changed (`tg_listen.py stop`, `start`), commit + push.

## Definition of done - every line is checkable (`next.py` reads the same files)
**Stage 1**
- [ ] `intake.py` exit 0 on the locked cut (not a trial): the transcript covers the cut, show notes read
- [ ] `channel_data.py pull` today; no stale data (or his waiver, in his words)
- [ ] every theme: verbatim hook (<= 14.5 s) + payoff, evidence ids that exist, claims with sources, shares declared
- [ ] every delivered theme: cold read PASS on the current text
- [ ] `check.py` exit 0 (3-5 delivered, <= 10 % shared footage) - or exit 2 and the manual-review flag sent
- [ ] cards sent with the listener running; `approved.json` exists
**Stage 2, per clip**
- [ ] `cut.<ch>.json`: no problems, nothing to ask
- [ ] `broll.json`: items with origin, why, looked - or his waiver
- [ ] the newest version VERIFIED; `preview_check.problems` empty (frames, censor); the sheet looked at and acked
- [ ] the card approved with its channel(s); no older card open
- [ ] every approved channel: a build with its stinger and a master (-14 LUFS +-0.5, <= -1 dBTP, frames = plan, picture check)
**Stage 2, episode**
- [ ] `lock.json` lists every clip of approved.json on every channel he tapped (`versions.json` `channels`); `cleaned.problems` empty
**Stage 3, per upload**
- [ ] facts made for the locked timeline; caption name lists explained; `package.py check` clean
- [ ] still confirmed (eyes_check looked at); four options; his pick; B and C written; three different thumbnails
- [ ] copy carries the current `brief`, 2+ `learned`, a WIN pattern in the options, `ab_tests_plan` for B and C
- [ ] A/B/C approved on the current card; `package.<ch>.json` written
**The run**
- [ ] `delivery.json` = every locked upload; `needs` empty or told to Colden
- [ ] `deliver.py` done: every master, A/B/C thumbnail and .srt in `<episode>/Final/Clips` (verified), the Clips Dashboard
      there, `delivery.json` points at them, nothing large left in WORK (`delivered.json` `large_files_left_on_mac` empty)
- [ ] `learn.py report` run after the last decision; no card open; one closing line to Colden on what is delivered and what is still open

## Files
`scripts/` common.py - Stage 1: intake.py channel_data.py evidence.py themes.py assemble.py coldread.py check.py
tg_themes.py learn.py - Stage 2: cut.py eyes.py capture.py broll.py build.py review.py tg_edit.py master.py lock.py -
Stage 3: captions.py package.py pack_learn.py thumbs.py tg_pack.py deliver.py - always: next.py doctor.py tg_listen.py -
Resolve side (run through rs.py only): rs.py r_build.py r_render.py r_lock.py r_list_tl.py r_template.py r_assets.py
r_survey.py r_peek.py r_whichmedia.py (read-only diagnostics, like r_assets.py and r_list_tl.py) r_audiotest.py (makes a
`zz TEST PodClips` timeline and renders it - safety rule 1 applies) -
self-tests: selftest.py (themes gates) selftest_tg.py (theme cards) selftest_cut.py (edit planner) selftest_cards.py
(edit + package cards, lock readiness) selftest_pack.py (packaging gates) selftest_deliver.py (Final/Clips delivery) selftest_learn.py (packaging learns from the data) selftest_face.py (the eyes gate on real Ep 24 frames in
`tests/faces/`, checked by eye): run ALL after any change.
`references/` rubric.json rubric.md coldread_prompt.md weekly_scrape.md edit.json carried_rules.md
stage2_rules_review.md aggregator_handoff.md history.md - `shows/*.json` - `assets/yunet.onnx` - `tools/` face.swift
facequality.swift Makefile (+ the built binaries).
Repo: github.com/coldenraisher/cwcpodclipsskill (private; Colden 2026-10-01: "Yes push to GitHub"). Commit + push every change.

## Open items (ask Colden)
- **Monday scrape**: stale since 2026-09-21; Colden runs it by hand 2026-10-02. The task
  (`~/Documents/Claude/Scheduled/cwc-weekly-metrics/SKILL.md`) now has YouTube Shorts + TikTok (STEP 1b, CWC_PodReels)
  and this skill's long-form block (STEP 1c, his "Yes" 2026-10-02: per-video impressions + CTR for both channels, A/B
  winners, 28-day reach). After the first run, check `channel_data.py pull` reports "CTR rows from the scrape" > 0.
- **Colden and Todd**: not set up (see "When things change"); `doctor.py colden-todd` lists what is missing.
- **Screen-share / played-clip layout** (ruling 15): not built; `cut.py` stops and asks. The first episode with tech
  news on screen will need it.
- **Re-lock in Resolve** (a change after the lock): the code path exists and is covered offline; its Resolve side has
  not run yet.
