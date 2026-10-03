---
name: CWC_PodReels
description: Vertical shorts (YouTube Shorts / TikTok / Instagram Reels) from a LOCKED CWC PodCut - The Creative Lens, Colden and Todd, any later show under Colden's umbrella. Runs in tandem with /CWC_PodClips on the same locked cut. Stage 1 reads the whole cut, Colden's short-form data on every platform (YouTube Analytics + Metricool TikTok / Instagram) and the news, writes 10+ themes in phrase ids, gates them in code, has a fresh reader cold-read each one as a stranger in the feed, and sends the best 10 as short Telegram cards (Approve / Kill / Notes). Stage 2 builds each approved short in DaVinci Resolve from `00 PodReels Template` (his A1 strip): fixed face-centred singles and 3-stacks, hidden splices, his MOON GET! captions, white hook box, guest tag, full-frame real b-roll, censor beeps; preview + decode gate + contact sheet; one Telegram tap approves the cut AND picks the destination; master at -14 LUFS. Use when Colden says "pod reels", "/CWC_PodReels", "shorts for Ep NN", "cut the shorts", or when the CWC aggregator reaches the shorts step after a PodCut lock. Not for IRA Cafe (/AMIRA_podcast_reels), not long-form clips (/CWC_PodClips), not /edit-shorts (the older skill, left untouched).
---

# CWC_PodReels

**WHERE THINGS STAND (2026-10-02, evening) - read this first when resuming:**
- Pilot episode (ruling 13): The Creative Lens Ep 24 (`Ep 24 PodCut v3 (L)`, guest Nick Williams @willco_media). 10 themes
  approved; ALL 10 EDITS APPROVED AND MASTERED (`<episode>/Shorts/Renders/`): s03 s07 s14 s08 s04 -> both channels,
  s01 s02 s15 s09 s05 -> TCL. The covers + copy round 1 was VOIDED by Colden (headlines outside the IG grid, mid-word
  stills, AI teeth, nano_banana_2) -> ruling 10 a-e below; copy.json statuses are back to draft, no covers recorded.
- `selftest.py` = 51 gates hold (packaging-from-data, the centre 3:4, no AI teeth, the model the job reported, mouth /
  eye gates). Every stage is built and ran for real on Ep 24 except publishing + lock.
- NEXT, in order: (1) `pack_learn.py build` is done - REWRITE Ep 24's copy.json from data/shorts/packaging_brief.md
  (set "brief", per short "learned"; postcopy.py check refuses it until then). (2) Per short: cover.py frames (done for
  all 10, sheets on disk) -> LOOK -> still + airef -> resolve (RESOLVE GO needed again) -> brief -> Higgsfield at 3:4
  (STOP if the job reports anything but nano_banana_pro) -> outpaint -> add -> pair. (3) tg_batch send, one card at a
  time. (4) publish upload / Claude pulls best times + counts / publish plan / tg_plan send -> PLAN APPROVED -> payloads
  -> createScheduledPost per call -> record -> lock.py (dry-run first) -> learn.py.
- 2026-10-02 23:30: Colden's two asks done. (1) The packaging brief now folds in the Monday scrape's OWN ANALYSIS
  (insights patterns / actions / fixes, working_now, avoid, every Test & Compare with what each thumbnail showed ->
  C-* cover patterns) like CWC_PodClips, Studio-shortened titles match by prefix; copy.json re-stamped (brief 4bec51b4bb).
  (2) AI cover prompts are now the JSON schema of Colden's Nano Banana Pro guide (references/nano_banana_prompt.md):
  `cover.py brief` writes cover/prompt.json pre-filled, Claude fills the <<placeholders>>, SHOWS COLDEN, sends the JSON
  text; `add --prompt cover/prompt.json` parses it and gates every rule (one @Image1 scoped to identity with
  do_not_transfer, lips together / no teeth, exact_copy = headline, placement in %, middle three quarters, must_avoid
  list, no placeholders / vague words, the headline from the hook or a WIN pattern). selftest 68.
- 2026-10-02 23:15 (Colden's round-3 review of s15: "not anything like me", "the title is back at the top", "the title is too
  long", "GODFATHER FIRST, that's what was already decided", "you are not using the @Image1 tag"): the subject is referred
  to ONLY as @Image1 (any show name in a prompt is refused); the headline is a DECISION of 1-3 words recorded once with
  `cover.py headline` (add refuses another); the model renders NO text (text.mode leave_space_for_later, a clean band at
  24-38 % above the head) and `add` sets the headline in the shorts' white hook box (Oswald Bold on disk; the Resolve hook is
  Acumin), OCR + safe zone on the result, stray model text refused; the reference is ALWAYS the FULL-RESOLUTION frame
  (ai_ref_full.png, never a crop - Colden 23:35: "always use the full resolution shot from resolve. STOP DOING THAT";
  `add` refuses a job record naming a cropped reference); likeness is solved in the prompt (face >= 30 % of the width,
  warm / neutral key, identity-only reference scope) - face_gates measure size + skin colour on the result. s15 round 4
  passed every gate (2 ai.jpg, pair + feed_check) - waiting for Colden's verdict; then s03 s07 s14 s08 s04 s01 s02 s09 s05
  the same way, one at a time (cover.py headline -> brief -> fill prompt.json -> SHOW -> generate -> add -> pair).
- 2026-10-02 22:40 STATE: copy.json passes the data gate; ALL 10 stills + AI references CONFIRMED
  (cover.json per short: still_confirmed + ai_ref); Resolve covers NOT built (ask-resolve card sent 22:11, no GO yet);
  AI covers: 0 of 10 recorded - two s15 generations rejected by Colden (generic, weak prompt, wrong reference); the
  prompt must be SPECIFIC and written for Nano Banana Pro (subject lock from @Image1, scene, camera, lighting, typography
  with exact placement in % of frame height, layout band, exclusions). Next: s15 AI cover with the full-frame
  reference and a prompt Colden has seen, then the other 9; Resolve covers after RESOLVE GO; pair; tg_batch one at a time.
- Caps: Create with Colden and TCL Metricool = 20 posts / month each (show files month_cap).
- Telegram: CWC_PodClips' always-on listener runs our plugin; watch review/events.log with a Monitor (`tail -n 0 -F`).
- Ask before taking Resolve (it switches Colden's current timeline): `tg_review.py ask-resolve` -> "RESOLVE GO".

Third skill of the CWC pipeline: `/CWC_PodCut` (locked cut) -> `/CWC_PodClips` (long-form) + **`/CWC_PodReels`** (shorts,
in tandem) -> an aggregator (not built). Act as an expert short-form editor: retention first, a hook in the first 3
seconds, a payoff that lands it, end cold. Every rule below is a decision Colden made, and every rule has a GATE in code
(prose rules get skipped - [[skill-enforced-by-code]]). Not covered: STOP AND ASK. Exit codes: 0 done - 2 ASK COLDEN -
anything else a gate failed (read it, fix the cause, never work around it).
`/CWC_PodCut`, `/CWC_PodClips`, `/edit-shorts`, `/edit-clips`, the AMIRA skills, the trend scanner: READ-ONLY from here
(code is copied and adapted, never imported).

## Colden's rulings (2026-10-02, answers to my 13 questions)
The brief: "operate almost exactly how /edit-shorts already works but in its own contained skill specifically tuned to
the CWC podcast network shows... review /AMIRA_podcast_reels... Utilizing the data from posted short form content to
deliver optimized short form for the channels. This will also cover The creative lens show."
1. **10 shorts per episode**; "not all will go to both channels".
2. **Data drives selection** (reverses edit-shorts' Sep 4 "analytics are not the driver"): rubric like CWC_PodClips;
   retention first (YT % viewed + kept at 3 s, TikTok avg watch, IG 3-second rate), then views; subs reported.
   **AND THE PACKAGING** (2026-10-02 evening: "When it is titling and generating hooks, make sure it is actually
   utilizing the data we pulled from the analytics scrape like /CWC_PodClips is doing. Data MUST drive the packaging
   here"): `pack_learn.py build` turns the catalog + the Monday scrape + his decisions into data/shorts/
   packaging_brief.md (WIN / LOSE / WEAK patterns for titles, caption hooks, on-screen hooks and covers, with n, PLUS
   the scrape's own analysis: insights, actions, working_now, avoid, Test & Compare lessons with the thumbnails); check.py and
   postcopy.py REFUSE themes / copy that do not name the current brief, carry `learned` (2+ pattern ids + how), use a
   WIN pattern, or test a LOSE pattern without a declared `explore`.
3. **Theme cards first** (title + hook, Approve / Kill / Notes); only approved themes are built; kill -> runner-up.
4. Shorts **may reuse moments in the long-form clips**: "these are not the same and can reuse".
5. Length: hard **20-75 s**, aim 25-45 s, payoff before 45 s unless the story needs more (length_note).
6. Look = **edit-shorts exactly**: MOON GET! purple-gradient captions + his outline (references/text_styles.json), white
   hook box (Acumin), 3-stack / 2-stack layouts, same for both shows.
7. Splice hiding: **layout change > b-roll > punch-in** (punch only on a camera file >= 2160 px); **minimum shot 1 s**.
8. Audio: **template** `00 PodReels Template`, his strip on A1; clips are duplicates; master -14 LUFS / -1 dBTP; no music.
   2026-10-02 12:0x: "Podreels template effects (compressor/limiter, eq and voice isolation at 60%) now on the template
   timeline" -> r_build.py `create` REFUSES a short whose A1 voice isolation is not on at 60 (the part the API can read).
9. Telegram: **one tap per short approves AND picks the destination** (CWC / TCL / Both; Todd-only on Colden and Todd);
   covers + copy: **ONE CARD PER SHORT, one at a time** (2026-10-02: "The delivery system for thumbnails is very
   confusing. Go one at a time same way /CWC_PodClips does") - Cover 1 / Cover 2 approves that short's copy too.
10. Covers: **1 AI + 1 made in Resolve**. "Issue with clips right now picking bad still image from edit. Make sure you
    use the best face detection available to pick a clean image. Should be smiling at camera or looking forward (Jake
    does not look directly at camera) if a different emotion is better, make sure you confirm with visual check that
    image fits emotion before sending me the final." (show file `gaze`: Jake = forward.)
    **LOCKED FOR FINAL 2026-10-02 (round 1 voided: "Can't keep failing the basic gates") - every line is a cover.py gate:**
    a. **Centre 3:4.** "The main grid is a centered 3:4 vertical image ... TikTok does the same. You need to optimize
       these always for the center 3:4. Nothing important (face, props, text) can ever exist outside of that." Every
       face and headline line inside y 264-1656 of 1920 (band 240-1680, 24 px margin), measured by Vision on the
       finished file of BOTH covers (`safe_zone`); the headline reads back complete (OCR).
    b. **Thumbnail still = the best still IN THE SHORT.** "These should be the best still image in the short." Only
       people who SPEAK in it (a 3-stack listener is never its face), from their camera inside the short's own pieces.
       "Select the best smile or other emotion that fits the theme of the short. If no other emotion, default to full
       smile. That includes teeth." Never a mouth caught on a word (open mouth only as a smile >= 1.2x the person's
       usual mouth width, never while they speak); eyes fully open, to the lens (Jake forward), sharp.
    c. **AI reference = a separate no-teeth frame.** "Find a good still face or grin with no teeth, send that to
       higgsfield. But keep the best full smiles for the real thumbnail." `cover.py airef` (teal tiles): the same
       person, lips together (mouth <= 0.022), strict eye gates; the brief sends only these frames.
    d. **AI covers: NO TEETH.** "No teeth smile in AI gens, other expressions okay ... they completely lose the exact
       identity." Applies ONLY to AI. Gate: mouth openness <= 0.022 on the finished cover.
    e. **Nano Banana Pro** for every AI cover, **generated at 9:16** (Colden 2026-10-02 22:20: "Social media thumbnails
       must be 9:16 aspect ratio and ... needs to compose for 3:4 center safe zones" - never generated at 3:4 and
       outpainted; the safe zone is a composition rule inside the 9:16, not a canvas size) and COMPOSED for the centre
       3:4: face, props and headline in the middle three quarters of the height. Higgsfield's API reports a finished Pro
       job back as `nano_banana_2` - the same job (its page says Nano Banana Pro; Colden verified); the gate checks the
       job was SUBMITTED as nano_banana_pro and refuses any other model.
       **Prompt craft (Colden 2026-10-02 22:25, gated in `add`):** ONE reference image attached (two confuse the model);
       the subject is referred to as "@Image1" in the prompt; the prompt never states an aspect ratio or calls the image
       3:4 (the aspect is the API parameter: 9:16); it says "lips together, no teeth".
    **Rulings after the review (2026-10-02, late), gated in cover.py + selftest:**
    f. **A short that posts to Create with Colden shows COLDEN's face** ("For CWC use colden face"), as on his
       long-form thumbnails, even when the guest says the line (show file `channels.face`); he must be on screen in
       it, or ASK. A TCL-only (or Todd) short shows the people who speak in it.
    g. **Narrowed eyes on a full smile are fine** ("Yes narrow eyes fine" - Nick squints when he smiles): the smile /
       laughing eye gates drop to 0.6x height / 0.5x Vision openness (the blink classifier still refuses shut eyes);
       serious / angry / confused keep eyes open.
    h. **"Talking always ranks lower than an actual smile."** Silent frames rank above talking ones on the sheet, and
       `still` refuses a talking tile while a silent one of the same person is on it.
    i. `serious` (lips together, eyes on the lens, a point being made) is the fallback when a short has no smile in it
       - Ep 24 s01 s02 s09 s05 (Nick / Jake never smile in them).
11. Publishing: **Metricool**; "we can cut when needed to stay in limit" (TCL plan 20 posts / month; CWC hit its cap in Sep).
12. **Monday scrape**: add YouTube Shorts "stayed to watch vs swiped away" and TikTok Studio retention per short.
13. **Pilot = Creative Lens Ep 24.** The pilot is the COMPLETE recipe; his notes before the rest.

## Prerequisites
- A LOCKED CWC PodCut (`CWC Podcast/work/cache/<show>/<EpNN>/manifest.json` with `locked`; its snapshot holds plan.json,
  words.json, pod_dump.json, layout.json, lower_thirds.json). The NAS mounted (camera files, `<episode>/Shorts/`).
- python3.9 with faster_whisper, torch/torchaudio, cv2 (YuNet in assets/), PIL, numpy, google-api-python-client.
- YouTube OAuth tokens `~/.config/edit-clips/youtube/{cwc,tcl}.json` (read + refresh only).
- Metricool: two MCP connectors - CWC = claude.ai connector (UUID tools), blogId 5965295; TCL = `metricool-tcl`, 6367106.
- Telegram: `TG_BOT_TOKEN` (~/.zshrc), chat id `~/.config/cwc/telegram.json`; the CWC listener running with our plugin.
- Resolve 21.1, project "TCL Show Edits", `00 PodReels Template` present; External scripting = Local.
- tools/: `make` builds the Apple Vision helpers (face, facequality, mouth).

## Where things live
- Skill: `~/.claude/skills/CWC_PodReels` - private repo github.com/coldenraisher/cwcpodreelsskill. Commit + push every change.
- Work per episode: `Create with Colden/CWC Podcast/reels/<show>/<EpNN>/` = WORK: episode.json, phrases.json,
  transcript.txt, show_notes.txt, themes.json, cold/, checked.json, review/ (cards.json, edits.json, events.log),
  approved.json, edit/faces.json, edit/<id>/ (cut.json, broll.json, src/, build.vN.json, versions.json, stills/, preview/).
- Media on the NAS: `<episode>/Shorts/` - Assets/ (transparent clip, nametag/), B-Roll/ (rendered clips), Renders/ (masters).
- Resolve: `<episode bin>/Shorts` (short timelines), `Shorts/Assets`, `Shorts/B-Roll`; template at the project level.
- Shared data: `CWC Podcast/data/shorts/` - youtube_<ch>.json, metricool/<brand>_<network>.json, catalog.json,
  summary.md (what Claude reads before scoring), decisions.jsonl, learnings.md.
- Two clocks (as CWC_PodClips): BASE = program-file seconds (words.json); CUT = locked-timeline seconds (every timecode shown).

## Stage 1 - themes (built, proven on Ep 24)
```
S=~/.claude/skills/CWC_PodReels/scripts
python3 $S/intake.py "<PodCut CACHE>"            # locked cut -> WORK (phrases on the CUT clock, people + cameras, specials, notes)
python3 $S/shorts_data.py pull                   # YouTube Shorts both channels (~3 min) + join + summary
#  Metricool (MCP, Claude): getAnalyticsDataByMetrics per brand with EXACTLY `shorts_data.py metricool-fields tiktok|instagram`
#  -> save {"rows": [...]} to a file -> python3 $S/shorts_data.py metricool <cwc|tcl> <tiktok|instagram> <file>
python3 $S/shorts_data.py summary                # catalog (YouTube <-> TikTok <-> Instagram matched by caption + day) -> summary.md
#   + pack_learn.py build -> data/shorts/packaging_brief.md (title / hook / caption patterns measured on RETENTION, with n)
#  READ: data/shorts/summary.md AND packaging_brief.md -> WORK/transcript.txt (ALL of it) -> show_notes.txt; research
#  claims (web); write themes.json with "brief": <the brief id> and, per theme, "learned" (titles + hooks come FROM the
#  WIN patterns; a LOSE pattern only as a declared "explore")
python3 $S/assemble.py "<WORK>"                  # each theme in play order -> cold/<id>.txt
python3 $S/coldread.py prompt "<WORK>" <id> > cold/<id>_brief.txt   # ONE FRESH agent per theme reads ONLY its brief file
python3 $S/coldread.py record "<WORK>" <id> <answer.json>
python3 $S/check.py "<WORK>"                     # every gate -> checked.json (1 = fix themes.json, 2 = flag)
python3 $S/tg_cards.py send "<WORK>"             # header + one short card per delivered theme
```
Writing themes (themes.py docstring has the schema): `brief` = the current packaging brief id, per theme `learned` /
`explore`; ranges in PHRASE IDS (start_word / end_word for a word inside an edge phrase),
`hook.quote` = the first words heard (verbatim, the opener's own words - a listener's "yeah" is ignored),
`payoff.quote` = the last words, at the END of the last range (<= 1.5 s of talk after it), hook_text 1-2 lines <= 24
chars, title <= 60 chars with no `?*/\:"<>|` (it is the timeline + file name), 8 scores with reasons (channel_fit >= 3
cites ids from data/shorts/catalog.json), claims with status + source, b-roll ideas (3-4) or a waiver, dest suggestion,
optional `fix` ({"pot": "pod"}). Write more than 10 (the rest are runner-ups), list rejected ideas.
What the data said on Ep 24 (summary.md): named products / films / people + a number win on every platform (FX3/FX6
Sundance TT 2.1K, Blackmagic price cut IG 7.5K, OpenPocketCine IG 23.6K, Inception story IG 6.4K, "Rigs get bigger
gigs" TT 28K); abstract AI / creator-business opinion sits at 100-400; The Creative Lens is weak everywhere (TT avg
watch 7 s); Instagram on Create with Colden is the strongest platform for the podcast shorts.

### Rubric (references/rubric.json) and gates (check.py)
hook x3 (floor 3), payoff x3 (floor 3), retention x3 (floor 3), channel_fit x2, timeliness x2, self_contained x2 (floor
3), package x2, footage x1 -> /100. STRONG 70, SOFT 55 (fills up to 10 when fewer are strong). Cold-read caps hook /
payoff / self_contained. News first (timeliness >= 4 with a dated source). <= 25 % footage shared between two SHORTS (no
variants; reuse of long-form clip moments is allowed). Deliver 10, runner-ups next, fewer than 5 deliverable -> flag.
Structural gates (exit 1): ids / word indices, no footage twice, hook = how the short opens, payoff ends it, lengths
20-75 s (> 45 needs a length_note), title / hook_text / summary limits, no em dashes, evidence ids exist, news / claims
sourced, screen shares declared, destination allowed, b-roll ideas or waiver, no on-air "Colden, edit that" line
(COLDEN_RE matches colton / coldon / colten...), the packaging brief named + `learned` + a WIN pattern in title or
hook_text (pack_learn.problems). Data freshness: YouTube < 36 h, Metricool < 7 days.

## Telegram (shared bot @VideoEditReview_bot)
NO POLLER of our own: CWC_PodClips' always-on `tg_listen.py` hands every update its handlers decline to
`scripts/tg_router.py handle` (registered in `~/.config/cwc/listen_plugins.json`; hook added by the PodClips session,
commit ac7794b, 2026-10-02). Our callback data always starts `pr|<cl24>|<stage>|...` (t theme, e edit, r resolve, b batch,
p plan). Handlers answer the tap and re-label the button BEFORE bookkeeping (~1.3 s end to end, measured). Free text is
ours only when it replies to our message or answers an awaiting-notes state. Every decision -> data/shorts/decisions.jsonl.
- `tg_cards.py send|resend|flag|say|status` - theme cards; all settled -> approved.json + "THEMES SETTLED".
- `tg_review.py send <WORK> <id> [--note]` - the preview WITH metadata (global rule) + buttons of the show's destinations
  + Changes. `tg_review.py ask-resolve <WORK> "<what>"` - Build now / Not now -> "RESOLVE GO" / "RESOLVE WAIT".

## Stage 2 - edit, review, master (built through the pilot)
```
python3 $S/faces.py "<WORK>"                     # once per episode: one fixed face position per camera (24 samples, YuNet)
#  per short: write edit/<id>/broll.json (real stills: fetch_image.py wiki|poster|commons|search; LOOK at every crop)
python3 $S/build.py "<WORK>" <id> [--plan-only]  # cut.py -> plan.py -> Resolve (sources gate, import, create, place, captions, hook, hookfit, verify)
python3 $S/review.py render "<WORK>" <id>        # 720x1280 preview -> frames / loudness / DECODE GATE / contact sheet
python3 $S/review.py ack "<WORK>" <id> "<what you saw>"   # after LOOKING at the sheet and stills/hook_placement.jpg
python3 $S/tg_review.py send "<WORK>" <id> [--note "..."]
python3 $S/master.py render "<WORK>" <id>        # after the tap: 1080x1920 H.264 -> loudness finish -> <episode>/Shorts/Renders/NN Title.mp4
```
- **cut.py** (from CWC_PodClips cut.py): sections between words, never open / close on a listener, the last shot shows the
  talker, end hold <= 0.4 s through silence only; pause trims > 0.8 s only where the program is quiet and a layout change
  hides them; written trims only into a real audio gap; splices hidden by a layout change (PodCut camera change, or a
  bridge flipped single <-> 3-stack), else a punch on a >= 2160 px camera, else `needs_broll` (plan.py refuses unless a
  b-roll covers it); min shot 1 s; censor windows (3 frames through each end).
- **plan.py**: single = full-height face-centred crop of the person's camera (faces.json); 3-stack = 640 px panels,
  talker centred, others top / bottom in cast order; 2-stack = Colden top; a SCREEN SHARE in a short = ASK (not built).
  Captions: <= 4 words / <= 22 chars, never across a sentence end, balanced lines (no orphan word), listener backchannels
  (<= 2 words) not captioned, swears masked (S***), show `spellings` + `caption_merges` (FX three -> FX3) + theme `fix`,
  steady under b-roll. Hook 75 frames, 9-frame fade. Guest tag (YouTube avatar + handle from lower_thirds.json) in the
  guest's panel after the hook, under B-roll. B-roll: rendered FULL FRAME by broll.py (cover crop + smoothstep move,
  sub-pixel, fingerprint in the file name), on a cut or >= 15 frames clear, not in the hook window / last 1.5 s / over
  the tag, never two overlapping. Audio: A1 program pieces (duck -40 dB under beeps), ISO tracks with every clip disabled.
- **r_build.py** (rs.py, one step per call, shared lock file, no Fusion handles kept): SOURCE GATE first (every clip by
  name AND file path; the PodCut's own camera paths); template duplicate as `zz BUILDING ...` into <bin>/Shorts; geometry
  converted to Resolve units BY THE TIMELINE'S OWN mismatch setting; Text+ captions (keyframed StyledText + his gradient
  via SaveSettings/LoadSettings) and hook; hookfit renders a frame, sizes the box to 940 px, keeps its top >= 50 px under
  the caption line and its bottom <= 1700; verify reads back paths / counts / frames / ISO disabled -> rename + red DRAFT.
- **review.py**: frames = plan, one video + one audio stream, loudness, DECODE GATE (faster-whisper on the render: opens
  on the first word, no stray word at a splice, ends on the payoff word with picture after it), contact sheet (hook,
  every layout run, every b-roll, tag, splices, last 0.3 s) -> LOOK -> ack (bound to the sheet hash) -> send.
- **master.py**: approved version only; frames = plan; static gain + limiter to -14 LUFS (+-0.5) / <= -1 dBTP; picture copied.

### Resolve facts learned building the pilot (2026-10-02)
- `00 PodReels Template` (and edit-shorts' `00 Shorts Template` it was duplicated from) has input-resolution mismatch
  **centerCrop**: a 1920x1080 camera is NOT pre-scaled (v1 came out letterboxed). edit-shorts' 2026-09-22 note assumed
  scale-to-fill. r_build converts intended geometry with the TIMELINE's `timelineInputResMismatchBehavior` (centerCrop 1.0,
  scaleToFit min, scaleToCrop max) and refuses any other value. The PodCut timeline is scaleToFit (16:9).
- Duplicating a timeline is the only safe way to a vertical one (SetSettings on a fresh timeline deadlocks Resolve 21.1).
  `DeleteTrack` exists; the template was rebuilt to V1 + four STEREO audio tracks (the source's were per-person mono).
- `GetVoiceIsolationState(track)` reads only on the CURRENT timeline (r_peek.py reads it without switching).
- The pool holds two JAKE.mp4 (Ep 21 and Ep 24): the source gate resolves by path (found it again, 1 of 2).
- The plan file must be read as UTF-8 inside rs.py (a credit "Söderlund" broke the ASCII read).
- Build ~3 min for a 22 s short; preview render ~1 min; decode gate ~30 s.

## Stage 3 - covers, copy, batch, publishing, lock, learning (built 2026-10-02; selftest.py 51 gates)
```
# per APPROVED short (its master rendered):
python3 $S/cover.py frames "<WORK>" <id> [--emotion smile|laughing|angry|confused|serious]   # LOOK at cover/still_sheet.jpg:
#   the face = Colden on a CWC post, else the speakers; purple tiles (rows 1-2) = thumbnail picks, silent before talking,
#   fullest smile first, teeth OK, narrowed eyes OK on a smile | teal tiles (row 3) = AI references, lips together
#   nothing passes (exit 2) -> the emotion that fits the theme (serious = lips together, eyes on the lens, a point being
#   made; Ep 24: s02 and s05 had no smile in them), else ask Colden. First run per episode measures each person's usual
#   mouth width over their whole camera (edit/mouth_base.json)
python3 $S/cover.py still "<WORK>" <id> <n> <emotion> "<what you see>"   # the THUMBNAIL still - LOOK at eyes_check.jpg + crop_check.jpg
python3 $S/cover.py airef "<WORK>" <id> <n> "<what you see>"             # the HIGGSFIELD reference (teal, same person, no teeth) - LOOK at ai_ref_check.jpg
python3 $S/cover.py resolve "<WORK>" <id>        # (Resolve, after RESOLVE GO) the Resolve-made cover -> cover/1 resolve.png - LOOK
#   GATE: face + hook inside the centre 3:4 (safe_zone)
python3 $S/cover.py headline "<WORK>" <id> "<1-3 words>"   # Colden's decided headline (hook / title words or a WIN pattern) - recorded once
python3 $S/cover.py brief "<WORK>" <id>          # -> cover/prompt.json (the JSON prompt, rules pre-filled: fill the <<placeholders>> from the brief's
#   "What Studio said" + the short's idea, SHOW COLDEN, send the JSON text as the prompt) + Higgsfield: media_upload ai_ref_full.png (curl PUT, media_confirm),
#   generate_image model nano_banana_pro, aspect_ratio 9:16, 2k, ONE reference (ai_ref_full.png, the FULL frame - never a tight face crop) called "@Image1" in the
#   prompt, COMPOSED FOR THE CENTRE 3:4 (face + headline in the middle three quarters of the height, top / bottom eighths
#   background only - never the words "3:4" in the prompt), NO TEETH ("lips together, no teeth"), ONE idea, <= 3 words, no
#   mics / AirPods / logos / film art -> download -> LOOK. The API reports the finished Pro job as nano_banana_2: same job.
#   SAVE the submission + jobs_wait result verbatim -> cover/job_<n>.json
python3 $S/cover.py add "<WORK>" <id> <9x16 file> --headline "<exact words>" --model nano_banana_pro --job cover/job_<n>.json \
    --saw "<what you checked>" --prompt cover/prompt.json
#   GATES: the job record was submitted as nano_banana_pro with ONE reference image; the prompt is the JSON object
#   (references/nano_banana_prompt.md): one @Image1 scoped to identity + do_not_transfer (studio, mic), subject.expression
#   "lips together, no teeth" (no smile / grin word), text.mode render_exact_text + exact_copy = the headline + placement in
#   %, "the middle three quarters" + edge_clearance in %, must_avoid (mic, earbuds, logos, posters, teeth, people), no
#   <<placeholders>>, no vague quality words, never 3:4; the headline = hook / title words or a WIN pattern
#   (pack_learn.headline_ok); 9:16; face + headline inside the centre 3:4 (y 264-1656); headline reads back (OCR);
#   mouth <= 0.022 (no teeth). Refused -> the file is renamed .rejected
python3 $S/cover.py pair "<WORK>" <id>           # pair.jpg with the IG-grid band drawn on both covers + feed_check.jpg (both as the 270x360 grid tile) - LOOK
python3 $S/postcopy.py scaffold "<WORK>"         # then READ data/shorts/packaging_brief.md; write caption / first_comment / yt_title /
#   fb_title in WORK/copy.json, set "brief": <id> and per short "learned" (2+ pattern ids + how), "explore" for a tested LOSE pattern
python3 $S/postcopy.py check "<WORK>"
python3 $S/tg_batch.py send "<WORK>"             # ONE CARD PER SHORT, one at a time (Colden 2026-10-02, as PodClips): the cover pair + that
#   short's copy; his Cover 1 / 2 tap approves cover + copy and the next card follows by itself; all done -> "BATCH APPROVED".
#   Notes -> fix -> tg_batch.py send "<WORK>" <id> (the old card retires)
python3 $S/master.py render "<WORK>" <id>        # (done per short right after his edit tap)
python3 $S/publish.py upload "<WORK>"            # masters + picked covers -> Drive (direct links)
#   Claude, both connectors: getBestTimeToPostByNetwork tiktok -> review/best_times.json; getScheduledPosts for the window's
#   months -> review/busy_days.json + review/month_counts.json
python3 $S/publish.py plan "<WORK>" [--start YYYY-MM-DD]   # Fri-Thu, CWC first / TCL >= 1 h later, month cap -> CUT list
python3 $S/tg_plan.py send "<WORK>"              # calendar card(s) + Schedule all / Changes -> "PLAN APPROVED"
python3 $S/publish.py payloads "<WORK>"          # then createScheduledPost per call via ITS connector; publish.py record ... per post id
python3 $S/publish.py export "<WORK>"            # Todd-only shorts -> Renders/Todd (never Metricool)
python3 $S/lock.py "<WORK>" [--dry-run]          # lock + cleanup (Trash / #recycle) + delivery.json
python3 $S/learn.py snapshot | calibrate | report   # weekly: posted shorts at 48 h / 7 d, TikTok fwr calibration, learnings.md
python3 $S/selftest.py                           # every gate against known-bad input (run after any change) - 68 gates
```
- **Covers** (ruling 10 a-e, locked): the shortlist samples the CAMERA FILE of every person who SPEAKS in the short,
  inside its own pieces at 6 fps (no captions in the frame), CWC_PodClips' detector (tools/face: Core Image blink +
  smile classifiers, pupils, head pose - Jake 'forward'). Per frame: both eyes open to >= 95 % of that person's usual
  eye height for a smile (90 % angry / confused, 70 % laughing), pupils within 0.10 of centre, head within 7 deg yaw /
  10 deg pitch of their usual pose, Vision quality >= 0.4, the smile classifier for smile / laughing; MOUTH: lips
  together (<= 0.025), or - not while speaking (+-5 frames of their words) - a smile wide enough to show teeth (>= 1.2x
  their usual mouth width; a mouth on a word stays ~1.0x). Fullest smile first, silent frames before talking ones.
  The Resolve cover is a 1 s `<short> cover vN` timeline built by r_build.py from the approved plan (single crop + the
  short's hook on the caption line, nothing else), frame 12 rendered as a 16-bit TIFF; GATES: the render is the
  confirmed camera frame (offset measured, rebuilt once), the blink classifier again, the centre-3:4 safe zone.
  AI covers: Nano Banana Pro at 9:16 from ONE no-teeth FULL-RESOLUTION frame (never a crop; the subject is only ever
  "@Image1" - never a name), composed for the centre 3:4 with an empty band above the head; the model renders NO text, the 1-3 word headline
  Colden decided goes into the white hook box by `add`; NO TEETH; no mics / AirPods / logos / film art / real third parties.
- **Copy** (edit-shorts copy.md): caption 1-3 sentences, the hook first, then exactly 5 hashtags on their own line, no
  link; first_comment = one engagement question (no plug, no "drop it below"); yt_title <= 100; fb_title only for CWC;
  IG collaborator = the guest on the Create with Colden post only. Brand voice direct, no hype, no em dashes.
  FROM THE DATA (ruling 2): yt_title and the caption's first sentence carry a WIN pattern of the current packaging
  brief; `brief` + `learned` recorded; a LOSE pattern only as `explore` (postcopy.py check refuses otherwise).
- **Publishing**: nothing is created before "PLAN APPROVED"; youtubeData.playlistId is never sent (the connector drops
  it - Colden sets the playlist); TCL month_cap 20 (Metricool plan). Calendar card = plan_card.py.
- **Monday scrape** (ruling 12): `~/Documents/Claude/Scheduled/cwc-weekly-metrics/SKILL.md` STEP 1b writes
  channel_metrics.json `shorts` (YouTube "stayed to watch", avg % viewed; TikTok avg watch, watched full %, retention
  3 s / 50 %, For You) - summary.md shows it, learn.py calibrate uses it.
- **Preview geometry gate** (review.py): a single = one big centred face, eyes in the upper half; a stack = a face in
  every panel (catches v1's letterbox).

## Open items (ask Colden)
- (answered 2026-10-02: CWC posts show Colden; narrowed eyes fine on a smile; talking ranks below a smile - ruling 10 f-h)
- Film posters on Wikipedia are ~250 px (non-free policy) - too small for a full-frame cover crop. Ep 24 used free
  Commons photos instead (Coppola's Godfather casting notes, the Rocky statue, Timberline Lodge, a Pulp Fiction poster
  held at a screening) + `fetch_image.py screen` phone captures. Posters only if Colden supplies large files.
- Colden and Todd: Resolve project for that show, and its CWC cadence (show file `first_run_ask`).
- TikTok "full video watched rate" from Metricool reads 0.0001-0.002 - unit unverified; `learn.py calibrate` settles it after the first Monday scrape with the shorts block.
- Share layout (talker top, share middle, others bottom) for a short that contains a screen share - build when one comes.

## Files
scripts/ common.py intake.py shorts_data.py themes.py check.py assemble.py coldread.py tg_api.py tg_cards.py tg_router.py
tg_review.py tg_batch.py tg_plan.py faces.py cut.py plan.py broll.py nametag.py measure_box.py fetch_image.py build.py review.py
master.py cover.py postcopy.py pack_learn.py publish.py plan_card.py lock.py learn.py selftest.py rs.py r_template.py
r_build.py r_render.py r_lock.py r_list_tl.py r_survey.py r_peek.py r_settings.py open_project.py · references/ rubric.json
coldread_prompt.md edit.json text_styles.json nano_banana_prompt.md (the applied prompt rules) nano_banana_prompt_guide_colden.md
(Colden's full guide) selftest/ (the round-1 covers the gates must refuse) · shows/
creative-lens.json colden-todd.json · tools/ face facequality mouth ocr (+ .swift, Makefile) · assets/ yunet.onnx fonts/
