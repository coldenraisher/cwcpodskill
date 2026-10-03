# CWC_PodClips - build history and lessons (moved out of SKILL.md 2026-10-02)

This is the LOG of how the skill was built on The Creative Lens Ep 24 (2026-10-01 / 10-02): the pilot versions, what
went wrong, and why each gate exists. It is history, not procedure - version names, frame counts and "not built yet"
remarks describe that day. The procedure is SKILL.md; the rules are SKILL.md + `carried_rules.md`.

## Lessons that became gates (read these; the rest is detail)
- **Wrong media by name** (C02 v1-v3 used Ep 21's JAKE.mp4): every clip is resolved by name AND file path; the source
  gate runs before anything is created; VERIFY re-reads every piece's path; the contact sheet shows every camera.
- **A trim on Whisper's word edges cut a word in half** (C02 v2, rejected): a written trim needs a real gap in the
  program audio at both ends (`cut._dip`), the cut moves into the gap, no gap = no trim.
- **Taps took 22-31 s**: one always-on listener (`tg_listen.py`), IPv4 kept-open connection, answer first.
- **A 2-frame beep / the wrong beep file**: ruling 35 (Power Bin `Short Censor Beep.wav`, 3 frames of the word through
  at each end, the word start read from the waveform).
- **Stills with closed eyes / off-camera eyes**: ruling 39 (pose + pupils + the white of the eye against the person's
  neutral face, the exact frame re-checked at full resolution, a face-crop sheet and an eyes close-up that are looked at).
- **AI thumbnails drew a real actor's likeness and franchise art**: every AI image is looked at and attested before it
  is recorded (`thumbs.py add --saw`).
- **A long close-up got one punch-in**: re-engagement splits every close-up over 10 s.
- **The Master-bin beep was not his beep**: Power Bins are invisible to scripting - a Power Bin asset is imported by
  its file path.
- **His limiter does not stop true peaks over 0 dBFS** on the A1 strip: masters are finished to -14 LUFS / -1 dBTP.

## Stage 2 build log (verbatim from SKILL.md v1.0)
BUILT (2026-10-01):
- **The template** `00 PodClips Template` in "TCL Show Edits" (ruling 27): EMPTY, 3840x2160, 30 fps, V1 Program; A1
  "Main Pod Audio" (stereo - Colden's compressor / noise reduction / EQ go HERE), A2 Music, A3 SFX, A4 Meme. Made by
  `r_template.py` as a duplicate of the empty UHD `00 Clips Template` (the only way to a UHD timeline without
  SetSettings). Every clip is a DUPLICATE of it; the builder adds camera / Tags / B-roll / Intro-Outro video tracks and
  the ISO audio tracks AFTER A4, so the processed track is always A1. One UHD template serves both outputs (ruling
  25): a 1080-only episode is rendered at 1920x1080 from it. Keep it empty; each project (Colden and Todd) needs its own.
- **`cut.py`** - sections, trims (quiet pauses checked against the program audio + written word-level trims), every
  splice hidden camera > b-roll > 1.25x punch, re-engagement punches, guest name tag, censor windows, the per-channel
  stinger and the Colden ending on the clip's clock. Gates in its docstring; `selftest_cut.py` (14 cases).
  Ep 24: t01-t04 plan clean (t01 11 trims / 6.5 s, one censor; t02 3 trims; t03 5; t04 0); t05 stops on a cut inside
  Nick's "I" at the end of its 4th part (cross-talk: needs a word-level range end).
- `rs.py` (Resolve from Bash, hard timeout, the shared lock file), `r_survey.py` (read-only project survey).
- **`eyes.py`** (YuNet eye landmarks -> the pan / tilt that keeps the eye line fixed at 1.25x; no face = the build
  refuses the punch), **`build.py` + `r_build.py`** (offline build plan -> create from the template, every camera
  under every shot, stinger, guest name tag from the PodCut's card, censor beep + A1 ducked, the Colden ending with the
  glitch transition, verify, rename `zz BUILDING` -> `Ep NN Cxx <Title> <CH> vN`, red DRAFT marker), **`r_render.py`**
  (Deliver job), **`tg_edit.py`** (preview with metadata, short caption, one tap = approve + channel, or Changes).
```
python3 $S/build.py "<WORK>" <id> [--channel cwc|tcl]        # a NEW version in Resolve (never replaces one)
python3 $S/rs.py 2400 $S/r_render.py PROJECT=.. NAME=.. OUT=.. CN=.. W=1280 H=720 LIMIT=2300   # preview render
python3 $S/tg_edit.py send "<WORK>" <id> --note "<what is still missing>"; python3 $S/tg_edit.py poll "<WORK>"
```
- **PILOT, Ep 24 t02** (`Ep 24 C02 Business Podcast Bubble CWC v1`, bin `Ep. 24 - 10-1/Clips`): 11,900 frames (6:36.7),
  67 pieces per track on 4 cameras, 17 punch-ins, name tag at 0:27, GTR_02 transition placed, VERIFY 0 problems. The
  720p preview has 11,900 frames; a contact sheet of 20 moments was looked at (cold open, stinger, tag, punches, glitch,
  end screen all correct). Sound through Colden's A1 strip: -16.9 LUFS integrated, TRUE PEAK +1.7 dBFS in the dialogue
  (the ending peaks at -2.7) - the chain needs a limiter before any loudness bump. Sent to Telegram 2026-10-01 22:49.
  The pilot has NO b-roll (said so in its caption).
- Resolve facts learned: `GetItemListInTrack` returns a transition as an item with no media pool item; a few mid-clip
  starts read back ONE source frame early (10 pieces of 536 on the pilot, same on a track's video and audio) - verify
  allows 1 frame, like the PodCut's own check; `AddTrack('audio', 'stereo')` after a template's tracks keeps A1's strip.
- **`tg_listen.py start`** - ONE always-on listener for every card of every episode (Colden 2026-10-01: "a very long
  delay from button push to actual send on telegram"). Detached (pid + log in ~/.config/cwc/), never stopped for a
  run; a tap is answered and the button re-labelled BEFORE any bookkeeping. `tg_themes.py poll` / `tg_edit.py poll`
  remain for a single foreground run; `start` refuses while one of them (or edit-clips' poller) runs. After a code
  change: `tg_listen.py stop` then `start`. RULE: never leave cards open without the listener running.
- **`master.py`** - `render` (only a version approved for that channel; frames must equal the plan) then `loud`: static
  gain to -14 LUFS (+-0.5) and a limiter only as far as needed for a true peak <= -1.0 dBTP, picture copied; tested on
  the pilot preview (-16.9 LUFS / +1.7 dBFS -> -14.2 / -1.2).
- 2026-10-01 22:57: Colden approved the pilot (t02 v1) for BOTH channels. `build.py --channel tcl --plan-only` gives
  the Creative Lens version's plan (same cut, The Creative Lens stinger); not built in Resolve yet.
- **B-roll** (ruling 33): `capture.py` (a real page at 1920x1080 @2x; consent declined, never a bot check worked
  around; LOOK at every capture), `broll.py` (`prep` = crop to the part that matters + pad to 16:9 with the page's own
  background; `render` = a full-frame clip with an eased push, made with ffmpeg - no Fusion in Resolve 21.1; a
  fingerprint in the file name), `edit/<id>/broll.json` ({src, origin, anchor {phrase, word}, seconds, move, why}).
  `build.py` REFUSES a build without it (or a waiver in Colden's words), snaps each edge onto a cut or 15 frames clear,
  and gates: not in the cold open / stinger, not over the name tag, not in the last 1.5 s, no two overlapping.
  Sources live in `<episode>/Clips/B-Roll/Source`, rendered clips in `<episode>/Clips/B-Roll`.
- **`review.py render|check`** - preview render, frame count against the plan, loudness whole and per section, and a
  contact sheet of every risky moment (first frame, both sides of each cold-open splice, stinger, name tag, the middle
  of every b-roll, the last second, the transition, the end screen). The sheet is LOOKED AT before `tg_edit.py send`.
- **t02 v2** (`Ep 24 C02 Business Podcast Bubble CWC v2`, 11,786 frames, 6:33): cold open 14.0 s (the aside "that is
  an issue that I haven't necessarily solved yet" trimmed from the cold open only, punch-in on the splice), b-roll at
  1:53 NVIDIA market-cap history, 2:56 Apple Podcasts charts, 5:06 WillCo Media channel page, 6:14 Colden's Shorts tab.
  Sound: -17.1 LUFS, true peak +1.0 dBFS in the body - with a limiter at -12 dB and +5 dB make-up the peak should be
  near -7, so the limiter Colden showed is probably NOT on the template the clip was duplicated from (the API cannot
  read a track's dynamics): asked him. Sent to Telegram 23:2x. v1 stays in the bin (never deleted before the lock).
- **v2 was REJECTED** (Colden: "hook is no good. the edit was course and cut mid word. go back to the v1 version"):
  the hook trim was cut on Whisper's word edges, which are off by up to 100 ms inside running speech. Now a WRITTEN
  trim is kept only when BOTH ends sit in a real gap of the program audio (`_dip` in cut.py: the quietest 60 ms within
  5 frames, 18 dB under the speech around it) and the cut moves to that gap; no gap = no trim. NOT yet proven by his
  ear - do not send him another trim inside a sentence without saying so. A cold open over 15 s that cannot be
  tightened cleanly needs a shorter hook line at the THEME stage, or `cold_open_waiver` (his words).
  **t02 v3** = the v1 cold open (17.8 s, waiver on file) + the four b-roll clips; 11,900 frames.
- **The A1 strip does reach the clips** (tested 2026-10-01 with two `zz TEST PodClips audio ...` duplicates of the
  template, one with added tracks: identical): the same 20 s of program go from -19.7 LUFS raw to -16.8 LUFS. But the
  peak stays at -0.8 dBFS with his limiter at -13 dB: fast transients pass the Dynamics limiter (0.71 ms attack, no
  look-ahead) or something after it in the strip adds level. His call; `master.py loud` holds the master at -1 dBTP.
- **WRONG MEDIA in v1-v3** (found by Colden: "weird shots of jake... wearing a black shirt instead of the white shirt
  he wore in todays episode"): the builder looked camera clips up BY NAME and the pool holds `JAKE.mp4` for Ep 21 too.
  Every Jake shot of v1, v2 and v3 was Ep 21's picture - and v1 had been approved with it. Now: the build plan carries
  the FILE PATH of every clip (cameras from the PodCut manifest, assets from the survey), `r_build.py` finds a clip by
  name AND path, VERIFY fails on any piece whose path is not the plan's, and `review.py` puts one frame of EVERY camera
  on the contact sheet. **t02 v4** is the first build with the right Jake. My contact sheets for v1-v3 never showed a
  Jake close-up - a check that does not look at every camera proves nothing about that camera.
- **THE SOURCE GATE** (Colden 2026-10-01: "There needs to be a quick gate check when you are assembling clips that the
  correct source files are being used every single time"). `build.py` runs it FIRST on every build, before anything is
  created: (offline) each camera file sits inside this episode's folder and is on disk; (`r_build.py STEP=sources`,
  read-only) every clip of the plan resolves to exactly ONE media-pool item with the plan's file path, and each
  camera's path is the one the locked PodCut itself uses. A mismatch = exit 1, nothing created. VERIFY then re-reads
  the path of every placed piece. Proven both ways on 2026-10-01: v4 passes; a plan pointed at Ep 21's JAKE.mp4 fails
  ("the locked PodCut uses ... Ep. 24 ..., the plan would use ... Ep. 21 ...").
- Word-level range edges: `"start_word"` / `"end_word"` on a body range (cross-talk at a range end).
- **Telegram speed** (ruling 34, second round: "from tap to button actually reading as accepted was 22 seconds"):
  every Bot API call goes over IPv4 on a kept-open connection (`tg_themes.api`); measured 0.13 s a call against a
  stall of the whole timeout on every second call with urllib. Action calls time out at 6 s and retry once; the long
  poll is 10 s (a stalled poll costs 20 s at most). The button is re-labelled first, then the spinner is answered.
  A second tap on a settled card answers "Already approved" and changes nothing.
- **Bookkeeping fixed in the final sweep**: a build takes its version number before `create` and keeps it when it
  fails; the plan freezes the cut (`shots`, `anchors`) and an `edit_sha` that ignores the stinger, so the second
  channel's build of the same edit is approved automatically (`approved_via`); `master.py render` takes the newest
  version of THAT channel approved for it; `tg_edit.py send` needs `review.py check` clean and `review.py ack`
  (the contact sheet was looked at; bound to the sheet's hash).
Lock + cleanup: `lock.py` (ruling 36, automatic after the last master). Packaging: Stage 3. Posting plan, uploads,
Studio: the aggregator (`references/aggregator_handoff.md`). Possible later speed-up (not needed for correctness):
pre-building the next clip while one is in review.
Never build in Resolve while Colden is working in it: a build makes its timeline current and appends to the CURRENT
timeline.
Open for the pilot: word-level range edges (`start_word` / `end_word`) for cross-talk at a range end (t05);
`pause` trims are conservative (-12 dB under speech) - tune by ear on the pilot; screen-share layouts (no Ep 24 theme
has one) stop and ask until built.

## Stage 3 facts noted during the Ep 24 run
Ep 24 facts learned: closed-mouth stills are rare in podcast footage - 12 samples per close-up shot find 1-10 per clip;
a centred face makes the overlay zoom 1.3x and move the face to the right third; the AI models drew a Marlon Brando
look-alike and Star Wars art for "Godfather vs Megalopolis" - regenerated with a faceless silhouette poster (LOOK at
every AI image before it goes to Colden). Ep 24's full episode exists twice per channel - the aggregator picks the
the 📱 one is the vertical stream (ruling 38) - Ep 24 links fGHOfGSB2T4 (CWC) and IKl0UEEIYaI (TCL).

## Status notes of the first run (verbatim from SKILL.md v1.0)
- 2026-10-01: Stage 1 built. `selftest.py`: 26 gate cases on a synthetic episode; `selftest_tg.py`: 12 cases of the
  approval flow against a FAKE Telegram (send, approve, kill -> runner-up, notes -> resend, manual review, decision log).
- **First real run, The Creative Lens Ep 24 (`Ep 24 PodCut v3 (L)`, 1:25:44), same day.** The show never reached the
  planned tech news; all 85 minutes are filmmaking, marketing and AI conversation. Five themes written, seven cold reads
  (t01 and t02 were revised after their first FAIL and read again). Result: 0 pass (scores 50-60 against a pass line of
  70) -> exit 2 -> `tg_themes.py flag`: the manual-review message + five HELD cards went to Telegram; `poll` is
  listening. What Colden approves there is a manual override (logged `approved-manual`, carried in `approved.json`).
  Scrape waiver on file: "Colden 2026-10-01: Proceed".
  Then rulings 19-22 (rules 2026-10-01b): reader recalibrated, guest-only name cards in the assembly, soft line 55,
  short cards. All five themes re-read (t03 and t05 once more after one blocking gap each): t01 60.0, t04 59.0, t05 58.1,
  t02 57.1 are SOFT passes with a PASS cold read; t03 is 53.3, under the soft line. **Colden approved all five on
  Telegram** (t03 and t05 by tapping the earlier held cards = manual override; both were tightened after his tap -
  `approved.json` says so). `approved.json` is Stage 2's input. Suggested channels: t02 and t04 for @ColdenRaisher,
  t01, t03, t05 for The Creative Lens - his decision at the edit.
- Manual review (built during this run): `flag` sends the summary (+ `episode_note` from themes.json) and ONE card per
  held theme that has a cold read (best first, 5 at most) with the reason it is held; Approve on a held card = his call.
- Facts learned: the Analytics API has no supported query for impressions / CTR on this channel (the metric name
  exists, every report shape is refused) - CTR must come from the Monday scrape; a script named `platform.py` shadows
  Python's own module and breaks the Google client (hence `evidence.py`); YouTube's `SUBSCRIBER` traffic label is the
  home / subscriptions feed, not subscribers only; `evidence.py` computes the channel median only for the 10 biggest
  results and a big outlet's median is low (THR: 500x) - read the outlier with the subscriber count next to it.
- What the channel data says (data/learnings.md, channel_summary.md): hardware news with a Colden hook did 4-8.6 K
  views and 35-48 % viewed; conversation / opinion / AI-ethics clips did 50-450 views unless a named person and news
  carried them (Matti Haapoja 33.6 K, Kane Parsons 4.3 K). The shortest clip (5:56) held best.
