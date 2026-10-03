---
name: CWC_PodCut
description: The base cut for Colden's own podcasts (The Creative Lens, Colden and Todd) - raw footage on the NAS to a camera-cut PodCut timeline in DaVinci Resolve. Finds who is which file, syncs every camera to the program feed by audio, transcribes each speaker, cuts from the live greeting to the live sign-off, switches camera on who is speaking and who is visibly reacting, trims ums / uhs / dead air only where a camera change hides them, holds the program during screen shares, builds and verifies the timeline. Use when Colden says "CWC podcut", "/CWC_PodCut", "cut the new episode", "podcut Ep NN", or drops a new episode folder for The Creative Lens / Colden and Todd. Not for IRA Cafe (that is /AMIRA_podcut).
---

# CWC_PodCut

First skill of the CWC pipeline (the AMIRA pipeline's twin): `CWC_PodCut` -> assembly (not built) -> `/edit-clips`,
`/edit-shorts` (built; they read the PodCut this skill makes) -> a main build skill (not built).
Built 2026-10-01 from Colden's eight rulings of that day. Every rule is a decision Colden made, and every rule has a
GATE - a script that enforces it or an assert that stops the run - because prose rules get skipped.
If a situation is not covered: STOP AND ASK. Never guess. Exit code 2 from a script = ask Colden; any other non-zero
exit = a gate failed (an assert): read the message and fix the cause - never work around it, never re-run to get past it.

What is a GATE here and what is not (audited 2026-10-01, see "Audit" at the end): an ASSERT or exit-2 in code is a
gate. A weight in the planner is a preference. Where a rule below is only a preference it says so.

`/AMIRA_podcut`, `/podcut`, `/edit-shorts`, `/edit-clips` and AutoEditor are read-only from here: never modify them.

## Colden's rulings (2026-10-01)
1. Covers The Creative Lens AND Colden and Todd. Ep 24 is the first full run.
2. His angle is the 4K camera file when he could record it, else the StreamYard webcam file. `Colden.braw` is
   converted first with his LUT (`braw_convert.py`).
3. "Cut from live greeting to live sign off. Cut out intro graphic and ending graphic. Cut out um's uh's and dead air as
   best as possible. AMIRA rule applies, prioritize cutting to a different camera or reaction. We can allow down to 2s
   cuts here as it is a faster paced show. Still allow the longer limit intact when speakers are really going."
4. "AMIRA cadence rules are good. Keep those but... cutting can be a bit faster at your suggestion."
5. "Automatic processing of reactions. This is a more expressive show so you will see more laughing, smiling etc. To get
   us closer to a one shot edit, try to avoid walking away from the camera, coughing, sneezing, going out of frame."
6. Screen shares: the program (wide) is the default. Full-screen share layouts are open - see Open items.
7. Audio: the program mix on A1; ISO audio clips present but disabled (what /edit-shorts and /edit-clips expect).
8. "This should be automatically approved as lock once the skill is tuned correctly." Until Colden says it is tuned,
   **2026-10-02: "lock skill" - the skill is tuned.** The Creative Lens show file has `"auto_lock": true`: build.py
   locks (and cleans up) a cut that passed VERIFY without waiting for his word. The look at the two review sheets
   (ack.py) is still required - build.py will not start without it. Colden and Todd stays `false` until its first
   episode (never run yet) has been locked on his word.

After the Ep 24 pilot (same day): "pace feels good I would keep"; ums that touch the word before them: "keep it safe"
(left in); word repeats: "If you can cleanly kill the repetitions, yes. If not, keep safe."; guests: "extra guests
should get a name handle at the beginning and end both in full podcut and then later on in clips"; "Images on lower
thirds need to be pulled from their youtube".
After the audit: "Yes Rebuild" (v3); cutaways over a screen share: "if the screen share is longer than 5s and cutaway is
2s or less. that is the rule. if high density text is on the screen share, do not cut away unless longer time frame +/-
8sec"; and "add a clean up step. delete extra files/timelines and any tests created in the resolve bin. Leave only the
finished podcut timeline appended with \"(L)\" for locked. if there were any cache renders for checks or files created
that are no longer needed for next steps, move to trash."

## Prerequisites
- DaVinci Resolve 21.1 running, Preferences -> System -> General -> External scripting = Local.
- python3 with `faster-whisper`, `opencv-python` (cv2 >= 5), `numpy`, `Pillow`; `ffmpeg` / `ffprobe`; `assets/yunet.onnx`.
- `tools/expr` and `tools/textcount` built (`make -C tools`, needs the Xcode command-line tools: Apple Vision +
  CoreImage - the smile classifier and the text reader).
- Google Chrome (renders the lower-third card) and network access to youtube.com (the guest's channel picture).
- AutoEditor's python venv (`~/Documents/Claude/AutoEditor/python/.venv`) for Silero VAD and the audio reaction score.
- The NAS mounted (`/Volumes/Current Projects`, `/Volumes/Colden and Todd`).

## Inputs
Episode folder, e.g. `/Volumes/Current Projects/The Creative Lens Show/Ep. 24 - 10:1/` (files may sit in `Angles/`):
- `WIDE.mp4` (or `Show.mp4`, or the raw StreamYard recording) - the program. Picture of the wide, the sound of the cut,
  and the clock everything is timed on (BASE seconds = seconds of this file).
- `<NAME>.mp4` per person (`COLDEN.mp4`, `JAKE.mp4`, `NICK.mp4`) or raw StreamYard `...-<Name>-webcam-...mp4`. The file
  name IS the person; hosts come from the show file, everyone else is a guest.
- `SCREEN n.mp4` / StreamYard `-screen-` / `-video-` files - imported into `<bin>/Shares`, not cut on (yet).
- `00 INTRO *.mp4` - imported, not placed (the intro is cut out; the assembly skill will bring it back).
Show files: `shows/creative-lens.json`, `shows/colden-todd.json` (hosts + Whisper spellings of their names, track
order, greeting / sign-off phrases, glossary, Resolve project, optional cadence overrides, `auto_lock`).
Work: `~/Documents/Claude/Projects/Create with Colden/CWC Podcast/work/` - `cache/<show>/<EpNN>/` (CACHE: manifest.json,
stems, words, faces, layout, points, reactions, plan, dumps, checks) and `review/<show>/<EpNN>/` (sheets to LOOK at).

## Non-negotiables (each with its gate)
1. **NON-DESTRUCTIVE.** Nothing on an existing timeline is deleted or trimmed away. The base is built once and never
   edited; every cut is a new `vN` timeline; an existing name is refused, never replaced. Every track of the cut tiles
   the whole cut on the same boundaries (the picture that is not chosen is a disabled clip, not a missing one). (One
   honest exception: `r_apply.py` empties the camera tracks of the fresh DUPLICATE it has just made of the base, before
   filling them.) A cut is built as `zz BUILDING ...` and only gets its PodCut name after VERIFY; a failed one is
   renamed `zz FAILED ...` and left. GATE: `r_base.py` / `r_apply.py` / `r_rename.py` refuse existing names; `r_apply.py`
   stops if the current timeline is not the one being built; `build.py` VERIFY (stray items, every camera under every
   shot it has media for).
1b. **A LOCKED episode is frozen.** `prep.py`, `plan.py`, `build.py` and `lower_thirds.py` refuse to touch it; a new
   version needs Colden's words (`unlock.py <CACHE> --by "<words>"`), and when it is locked the lock MOVES to it (the
   old one goes to `lock_history`). The plan a cut was built from is frozen beside its checks and copied into
   `<CACHE>/locked/<cut>/` at lock; the hand-off points there. GATE: those refusals; `lock.py` checks the frozen plan's
   hash against the checks and the timeline's length in Resolve.
1c. **Clean up at the lock** (Colden 2026-10-01). The last step of `lock.py` is `cleanup.py`: the locked cut is renamed
   `<cut> (L)`; the BASE, earlier versions and every `zz TEST / zz BUILDING / zz FAILED` timeline of the episode are
   removed from the project; the review folder and every working file in the cache go to the Trash; superseded
   lower-third files go to the NAS share's `#recycle`. This is the ONE place the skill removes timelines, and it is
   never a hard delete: each timeline is exported as a .drt into the Trash folder first and only removed once that file
   exists (File > Import > Timeline brings it back); files are moved, not deleted. Kept: manifest.json and the lock
   snapshot. Media in the bin stays. GATE: `cleanup.py` runs only on a locked, not re-opened episode; `r_cleanup.py`
   requires the green LOCKED marker on the kept timeline, never removes a name the skill did not make, and asserts each
   backup before each removal. `cleanup.py --dry-run` lists everything first.
2. **Synced by measurement.** Every camera is placed by its measured audio offset to the program (`sync.py`: coarse
   search over the whole program, up to 28 fine windows, drift fit). File-name offsets are never used. A camera whose
   clock drifts more than a frame is laid as adjacent re-anchored pieces. GATE: the coarse windows settle on ONE offset (>= 2 agree, no rival group),
   >= 4 fine windows on one drift line, >= 70 % of the strong ones (this person clearly talking) within 40 ms of it, residual <= 25 ms - a camera that fails is left with NO
   offset; `stems.py` re-proves each stem against the program (<= 40 ms, >= 2 places); `build.py` checks every base item
   AND every clip of the cut (every camera, under every shot) against the MANIFEST sync, within 1.5 frames.
   Accuracy to expect: an ISO sits on a whole frame of the base, so +-0.5 frame, plus up to ~1 frame inside a re-anchored
   piece. The StreamYard audio start offset (up to 40 ms) is handled in the measurement; whether Resolve applies it to
   the ISO SOUND is untested - that sound is disabled, the picture does not depend on it.
3. **Live greeting -> live sign-off.** GATE: `layout.py` finds where the talk layout is on the program (the intro and
   outro graphics are not it), `points.py` sets start 0.3 s before the first word after that - never before the talk
   layout is on - and end 10 frames after the last voice stops before the outro graphic; it stops (exit 2, and
   `plan.py` / `build.py` refuse `confident: false`) when the window is implausible. A missing greeting / sign-off
   PHRASE is only reported. `plan.py` asserts the program picture is never used before `on_air` / after `off_air`
   (half a second of guard when the switch is a dissolve).
4. **The person with the floor gets the close-up; a close-up needs real words** (a "mm-hmm" / "yeah" never earns one).
   GATE: `plan.py` asserts every non-reaction close-up holds >= 2 real words of that person.
5. **Never hold a close-up on someone who is not talking** while another person has the floor - except an approved
   reaction. GATE: `plan.py` forbids it for any floor run of >= 1 s (>= 2 real words) and asserts no close-up stays
   more than 1.5 s on someone while ONLY another person has the floor (Ep 24 worst case: 0.17 s).
6. **Overlap and quick back-and-forth go to the wide**, starting 0.25 s before the words that caused it. This one is a
   PREFERENCE (a planner weight), bounded by gate 5 - there is no assert of its own.
7. **Shots >= 2 s, <= 20 s.** Shots under 4 s cost extra so they stay the exception; a close-up starts to cost after
   10 s, so a monologue gets relief (a reaction if there is one, else the wide) between ~12 and 20 s; cuts are cheap at
   a sentence start or in a breath and dear inside a word. GATE: `plan.py` asserts >= 2 s and <= 20 s (plus the length
   of any trim that had to stay inside the shot; a screen share holds the program for its whole length); `build.py`
   re-asserts the 2 s with a literal number and refuses a plan made with `--set` overrides or another cadence file.
8. **Trims only where seamless. NO JUMP CUTS, NO PUNCH-INS.** An um / uh by the person talking (nobody else saying
   words) and dead air >= 1 s (everyone silent AND the program quiet: laughter and played videos are not dead air) are
   removed only when a cut to a DIFFERENT camera lands exactly on them. An um is trimmed WHOLE or not at all: it must
   start >= 10 frames after the last word and end before the next one ("keep it safe"), else it stays. Words are never
   removed (the one exception is the first take of a clean repeat, 8b). GATE: `fillers.py` (a candidate is cut down to
   the part no transcribed word touches, must DECODE as um / uh / er mid-sentence; "ah" / "hmm" are reactions and stay)
   -> `plan.py` (a trim that would hold > 0.06 s of anyone's real word is dropped, and asserted again after planning;
   an unhidden trim is put back; assert: different camera on both sides of every cut, every missing frame is a planned
   trim; two trims are only merged across a gap that is itself quiet).
8b. **Word repeats only when clean.** "I I", "the the", "it's it's": a FUNCTION word said twice (never an emphasis like
   "really really"), with a breath (>= 12 dB under that speaker's level) both where the first take starts and just
   before the second - the trim runs breath to breath. Anything else stays. GATE: `fillers.py` marks `clean`,
   `plan.py` trims only those, and only when a camera change hides it.
8c. **Guest lower thirds at the beginning and the end.** Every guest (not the hosts): the card his clips use (white,
   round photo, name, @YouTube handle, bottom-left), 5 s with an 8-frame fade, over the guest's FIRST and LAST close-up
   of >= 6 s, 15 frames clear of the cuts, never over the wide or a reaction. Name and handle come from
   `references/guests.json` and are never guessed: a guest without an entry stops the run (ASK). **The photo is pulled
   from the guest's YouTube channel** (Colden 2026-10-01: "Images on lower thirds need to be pulled from their youtube"):
   the channel picture of that handle, the page checked to answer to the same handle; no picture = stop and ask, never
   a frame grab in its place (an `avatar` file in the registry is only for one Colden supplies). ProRes 4444 files in
   `<episode folder>/Lower Thirds/`, on the track above the cameras. GATE: `lower_thirds.py` (exit 2) -> `r_tags.py`
   (refuses a track that already has clips) -> `build.py` VERIFY (both tags per guest, each over that guest's close-up).
9. **Reactions are scored on expression, never audio alone, and they are automatic.** A listener whom Apple's smile
   classifier sees smiling for >= 1 s; re-read at 10 fps and kept when >= 60 % of the 2-4 s window smiles, the face stays
   in frame at its usual place and size, the eyes are not down / closed, and there is no jolt (sneeze / cough / reach).
   Scored on smile share, mouth width against their own median and a laugh on their mic; under 0.40 is dropped. In the
   cut: only from ONE person who keeps talking (never over a new talker's first words), best first, at most one per
   15 s (`reaction_spacing`). NOT tested, despite the yaw the tool reports: "turned away" as such (a turned head usually
   fails the smile / place tests). GATE: `reactions.py` (each rejection reason is counted) -> `plan.py`; the sheet to
   LOOK at is `reactions_in_cut.jpg` - the reactions the plan really uses.
10. **Nobody is shown who is not presentable, not on air, or where their camera has no picture.** GATE: `reactions.py`
    writes the per-person presentable mask (in frame, usual place and size) and stops when anyone is under 85 % (a
    camera moved mid-show); `layout.py` the off-air ranges (to the sample the person appears); `plan.py` forbids and
    asserts all three (a close-up may be at most 25 % unpresentable).
11. **Special program layouts hold the program.** Screen share, played video, graphic: the wide carries the picture and
    nothing is trimmed inside. The only cutaway is an approved reaction, under Colden's rule (2026-10-01): the share is
    longer than 5 s and has been on the program >= 5 s when the cutaway starts - >= 8 s when it carried a page of text
    in the seconds before - and the cutaway is 2 s, never longer. "A page of text" = Apple Vision reads >= 100 characters
    more on the program than the talk layout's own lettering (`tools/textcount`, a sample every 2 s; calibrated on Ep 23:
    articles / forum posts 258-783 characters, videos / photos / channel pages 102-149, talk layout ~100).
    HOW I READ "+/- 8sec": with text on the share, the viewer gets about 8 s with it before any cutaway. Say if he meant
    something else. GATE: `layout.py` (`dense_text`; stops when > 60 % of the show reads as special) -> `plan.py` cuts
    every reaction over a share down to 2 s, refuses the ones that come too early, and asserts all three numbers on the
    final shots.
12. **Audio = the program mix, untouched.** A1 enabled on every shot and on the program's own frame; every ISO audio
    clip disabled and on its picture's frame. No gain, no processing (nothing in this skill sets any; clip gain is not
    read back). GATE: `build.py` VERIFY.
13. **Resolve is driven from Bash** (`rs.py`, hard timeout, one call at a time on the lock file the AMIRA skills use:
    `~/.config/amira/resolve.lock`). Never hold Fusion comp / tool handles. A call that times out: `common.rs` says whether
    Resolve is gone, left a fresh crash report, or is alive but busy (Colden working in it - try again).
    The project is only ever switched by `open_project.py` (refused while a render runs; the open project is saved first).
14. **Stop and ask** for anything not covered.

## Pipeline
```
python3 scripts/prep.py "<episode folder>"          # everything before Resolve; exit 2 = ASK, 3 = BRAW first
#   LOOK at review/<show>/<EpNN>/layout.jpg and reactions_in_cut.jpg, then:
python3 scripts/ack.py "<CACHE>" "<what you saw on the two sheets>"
python3 scripts/build.py "<CACHE>"                   # Resolve: project, base, cut vN, VERIFY (non-zero = a gate failed);
#   with auto_lock (Creative Lens) it ends in lock.py + cleanup.py: '<cut> (L)' is the one timeline left, working files
#   go to the Trash. Without auto_lock (Colden and Todd until its first lock), on his word:
python3 scripts/lock.py "<CACHE>" --pod "<cut>" --by "<Colden's words>"
python3 scripts/unlock.py "<CACHE>" --by "<Colden's words>"                 # ONLY to make a new version of a locked episode
```
`prep.py` keeps a fingerprint per step in `<CACHE>/state.json` (camera files by path + size + date + person + track, the
measured offsets, each step's code version `common.ALGO`, the steps it reads). A step is skipped only when its
fingerprint still matches; otherwise its old outputs are moved to `<CACHE>/_stale/` and it runs again. A step that fails
records nothing, so its gate fires again on the next run. Steps, in order:
1. `intake.py` - who is which file -> manifest.json. Stops on: no program, a host without a file (`--no-host <Name>`
   only when Colden says that host is out), two files for one person, an unexplained video (any type), a person who is
   neither a host nor in references/guests.json, a variable-frame-rate camera, a program that is not a whole frame
   rate, a BRAW (exit 3). A camera file that changed (size / date) loses its sync and is measured again.
2. `sync.py` - offsets and drift per camera.
3. `stems.py` - each speaker's audio resampled onto the program clock (16 kHz), Silero VAD, AutoEditor's audio
   reaction score. No Resolve stem render.
4. `words.py` (one Whisper process per speaker) in parallel with `faces.py` (one process per camera, 2 samples / s:
   YuNet face box + 16x16 crop, and through `tools/expr` Apple Vision's lip / eye landmarks and smile classifier).
5. `fillers.py` - ums / uhs and word repeats per speaker.
6. `layout.py --sheet` - talk layout vs special, live window, off-air ranges -> `layout.jpg`.
7. `points.py` - start / end.
8. `reactions.py --sheet` - reactions that pass the gate + the presentable mask (`reactions_passed.jpg`).
9. `plan.py` - the cut (see its docstring for the rules and how the optimizer scores them), its asserts, and the sanity
   bands (cuts a minute, share of the wide, share trimmed, each person's close-up time against their floor time): a plan
   outside them is saved as `plan.rejected.json` and the run stops with exit 2.
10. `reaction_sheet.py` - `reactions_in_cut.jpg`: the reactions the plan really uses.
`show_plan.py <CACHE> <from> <to>` reads the plan next to the transcript; `preview.py <CACHE> --from --to` renders a
watchable preview of any stretch straight from the camera files (no Resolve; no lower thirds).
`build.py`: see its docstring - gates, base (built once, checked against the manifest sync), the cut built as
`zz BUILDING ...`, lower thirds (`lower_thirds.py` -> `r_tags.py`), VERIFY, rename, the plan frozen beside the checks.
A trial: `plan.py <CACHE> --out trial.json [--set k=v]` then `build.py <CACHE> --prefix "zz TEST ..." --plan trial.json`.
`lock.py`: its docstring lists the gates; it freezes everything into `<CACHE>/locked/<cut>/`, runs `cleanup.py` and
prints the hand-off (the timeline is then called `<cut> (L)`). After a cleanup the cache holds only the manifest and
the snapshot: a later new version (unlock.py) runs prep again from the camera files.

## Per-episode questions (the ONLY things Colden is asked)
- A file intake cannot place, or a host with no file.
- A new guest's full name and YouTube handle (unless Colden said / showed them on the stream: then write the entry in
  references/guests.json WITH its source).
- A camera that will not sync, or a live window that is implausible.
- For Colden and Todd: whether the program feed is usable as the wide (`--wide program`) - building a two-shot from
  the ISOs is not written yet.
Everything else is automatic. Report what was done with numbers.

## Definition of done
Every line is something a script checks; the last three scripts refuse to go on without the ones before.
- [ ] prep.py exit 0 from a clean state.json: intake clean; every camera synced and its stem proven; transcripts cover
      the speech to the end; faces on every camera; points confident
- [ ] plan.py exit 0: every assert in its GATES block, no word inside a trim, sanity bands empty
- [ ] ack.py: layout.jpg and reactions_in_cut.jpg were looked at (hashes recorded) - always, auto_lock too
- [ ] build.py exit 0: gates 0 (no overrides, current rules + cadence, literal 2 s), base == manifest sync, VERIFY 0
      problems, the cut carries its real name (not zz BUILDING / zz FAILED)
- [ ] every guest has a lower third at the beginning and at the end, over their own speaking close-up, name + handle on
      file with a source, photo from their YouTube channel
- [ ] lock.py exit 0 (auto_lock, or Colden's word where it is off): frozen plan == checked plan, timeline length unchanged, snapshot
      written, hand-off printed
- [ ] cleanup.py exit 0: '<cut> (L)' is the only timeline of the episode in the bin; every removed timeline has its
      .drt in the Trash folder; the cache holds manifest.json + the snapshot

## Files
scripts/ common.py intake.py sync.py stems.py words.py faces.py fillers.py layout.py points.py reactions.py plan.py
lower_thirds.py reaction_sheet.py prep.py ack.py show_plan.py preview.py build.py lock.py unlock.py cleanup.py
braw_convert.py · Resolve side: rs.py open_project.py r_base.py r_apply.py r_tags.py r_rename.py r_replace.py r_dump.py
r_list.py r_lock.py r_cleanup.py r_braw.py · tools/expr.swift, tools/textcount.swift (`make -C tools`) ·
shows/*.json · references/cadence.json, guests.json · assets/yunet.onnx
Repo: github.com/coldenraisher/cwcpodcutskill (private). Commit + push every change.

## Status
- **2026-10-02: skill locked as tuned** (Colden: "lock skill") - auto_lock on for The Creative Lens; every test
  timeline, cache and scratch file of the build is gone (Ep 23 / Ep 22 test caches and review sheets to
  `~/.Trash/CWC_PodCut test data 20261002-113222/`).
- 2026-10-01 pilot, **Ep 24 (Nick Williams, 87.5 min program, 3 StreamYard cameras)**: sync Jake +1.533 s (40 ms drift,
  3 re-anchored pieces) / Nick +1.507 / Colden +1.581, stems proven within 11 ms; live window 0:57.22 - 1:27:21.22;
  5 special stretches (3 real shares, 2 false ones of 3-4 s where Colden leaned out of frame).
  History: v1 (pilot; "pace feels good"), v2 (clean repeats + guest lower thirds; locked "V2 good. locked."), then the
  audit found v2's flaws - Jake's and Colden's close-ups up to ~2 frames late by the last third, 6 um trims overlapping
  a word, and no reactions after 44 min (tools/expr went blind part-way).
  **`Ep 24 PodCut v3 (L)` is the LOCKED cut** (Colden: "Yes Rebuild", then "Lock v3"; rules 2026-10-01d; full prep
  from an empty state): 576 shots, avg 8.9 s, 6.7 cuts a minute; 26 ums + 24 dead-air gaps + 10 clean repeats trimmed
  (39.8 s), 51 ums left in for safety; 84 reactions across the whole show; no cutaway over a share (2 refused by the
  share rule); Nick Williams @WillCoMedia lower thirds at the start and end; VERIFY 0 problems against the manifest
  sync. First real run of the cleanup at lock: it is the only timeline of the episode in bin "Ep. 24 - 10-1" (project
  "TCL Show Edits"); `Ep 24 BASE`, v1, v2 and the two zz TEST timelines were exported as .drt to
  `~/.Trash/CWC_PodCut Ep24 20261001-214043/timelines/` and removed; 58 working files / folders (1.7 GB) went to the same
  Trash folder; the cache holds manifest.json + `locked/Ep 24 PodCut v3/` (plan, words, layout, reactions, lower thirds,
  points, checks, the two sheets).
- Regression on **Ep 23 (Erik, 105 min, Colden on a 4K 29.97 camera file that starts 37 s after the stream)**: sync
  matches Colden's hand-synced "Episode 23" timeline within a frame on all three cameras (Jake 1.633 / 1.633 s, Erik
  1.692 / 1.700, Colden 37.30 / 37.31); live window matches his in / out; all 11 screen shares found, no false ones.
  Full prep from an empty state under the hardened rules (55 min, the 4K file included): every gate passed; plan 420
  shots, 47 reactions (2 of them 2 s cutaways over a share, 3 refused by the share rule), 23 dead-air gaps + 12 ums + 12
  clean repeats trimmed, 42 ums left in for safety; 38 % of the show is screen share (held on the program), 24 min of it
  text-heavy. Not built in Resolve; its test data went to the Trash on 2026-10-02 (a new regression run = prep.py on
  the NAS folder from an empty cache, ~55 min). That run caught two of my own new gates being wrong for a camera's own mic (coarse
  and fine sync) and one rule the planner could still break (2.8 s on a non-talker) - all three fixed.
- Timing of a run (Ep 24): sync 20 s, stems + VAD 2.5 min, words 12 min and faces 6 min in parallel, fillers 9 min,
  layout / points / reactions 2 min, plan 12 s, build 3 min. A 4K camera file adds ~15 min to faces.
- Resolve facts learned: the API refuses a ':' in a bin name (intake swaps it for '-'); a call can time out while Colden
  is working in Resolve - the process is alive, try again (common.rs says which it is); building a cut makes it the
  current timeline in his window; a base item's source span and timeline span differ by a frame or two on a same-rate
  clip - never derive a rate from them (r_apply.py uses the clip's frame rate).

## Audit 2026-10-01 (Colden: "Any issues, hallucinations, assumptions or bugs... any other gates?")
My own read plus an independent reviewer (38 findings; the planner's dynamic program itself checked out). What was
wrong, and what now stops it:
- **Gates could be walked past by re-running** (outputs were written before the gate, steps were skipped when a file
  existed) -> prep.py records a fingerprint only on success; failed transcripts / face tracks are moved aside; a failed
  sync leaves no offset; plan.py / build.py refuse unclean intake, sync or points.
- **Stale caches** (a replaced camera file, a guest added -> speakers renumbered, a re-sync) -> fingerprints by file
  size + date + person + track + offsets + code version; stale outputs are moved to `_stale/`.
- **VERIFY compared the cut with the base instead of the measured sync** -> every base item and every clip of the cut
  is checked against the manifest. First run of that check found a real 2-frame slide (rate derived from noisy item
  spans) - fixed in r_apply.py.
- **plan.json could be overwritten after a lock; a failed plan left the old one** -> locked episodes are refused, a
  plan run removes the old file first, the built plan is frozen with the cut.
- **"Words are never removed" was not enforced** -> fillers are cut down to what no word touches, ums are whole-or-none,
  merges need quiet between, and plan.py drops and asserts any trim holding a word.
- **Rules that were only weights** (close-up needs words, never hold on a non-talker under 1 s runs, presentable, max
  shot) -> asserts; rule 6 is now labelled a preference.
- **SKILL.md said things the code did not do** (reaction threshold "1.12x median", "one per 20 s", "turned away",
  "loud burst with no smile", "plan.py asserts presentable", "under 3.5 s") -> rewritten from the code.
- **A camera that ends before the show, or was moved mid-show** -> planned around (coverage) / stops the run (85 %).
- **The intro could flash at the head of the cut** (`on_air` picked a cut inside the teaser) -> exact cut only within
  0.6 s, start never before the talk layout, program picture blocked outside it.
- **Half-built timelines carried a PodCut name; a click on another timeline mid-build would place clips there** ->
  `zz BUILDING` / `zz FAILED` names; the build stops if the current timeline changes.
- **The sheet looked at was not the reactions in the cut; "looked at" and "on his word" were prose** ->
  `reactions_in_cut.jpg`, `ack.py`, `build.py --lock` removed.
- New run-level gates: plan sanity bands, share of special layout <= 60 %, unknown people asked at intake, whole frame
  rates only, no trial plan (`--set`) can become a version.
- **Half the show had no reactions** (found by LOOKING at the new in-cut sheet: the last reaction sat at 43 min). The
  Swift helper kept every frame's Vision objects alive and went blind after ~5,300 frames; YuNet still saw the face, so
  nothing failed -> one autoreleasepool per frame; faces.py compares the two readers in 5-minute blocks, reactions.py
  refuses an expression track that covers less of the show than the detector does.
- **A reaction that opens on a hand at the face** (Jake rubbing his nose, then laughing) -> the window opens on a
  SUSTAINED smile and never over low capture-quality frames; a face that stays under 75 % quality is rejected.
- **A gate of mine that was wrong**: the cadence comparison in build.py (a derived value), the coarse / fine sync tests
  (too strict for a camera's own mic), the first covered-face test (rejected 260 good reactions) - each found by
  running the whole thing, not by reading it.
Still NOT gated (know this when a run looks odd): the layout detector's "usual size" assumption (see layout.py); the
screen-share / talk decision is only as good as the face match; Whisper's word edges (+-50-100 ms) under every trim and
cut cost; the fonts of the lower-third card; clip gain is never read back; ack.py is an attestation, not a measurement.

## Open items (ask Colden / next sessions)
- **Lower thirds in clips**: `/edit-clips` makes its own (UHD, every speaker); it is not modified from here. The guest's
  name / handle / photo are in the lock hand-off and the frozen `lower_thirds.json` for it to use.
- **Screen-share layout** (his question 6): today the program holds the picture for the whole share (Ep 23: one of
  9.6 min). Proposed, not built: share full screen with the active speaker in a corner box, on tracks ABOVE the PodCut
  structure so /edit-shorts and /edit-clips still read it; needs a screen recording that carries the share (Ep 24's
  `SCREEN 1.mp4` is black except its first and last seconds) and his pick of the box.
- **Colden's camera file can be LOG** (Ep 23's Colden.MP4 is flat / grey straight from the file): whether the cut should
  carry his LUT on that track is his call; `braw_convert.py` is written from the API docs and NOT yet run on a real BRAW.
- **Colden and Todd**: show file written, not run. Needs: the Resolve project name, a ruling per episode on the wide
  (`--wide build`, a two-shot from the ISOs, is not written), and its 29.97 fps material stops at intake until that
  path has been run once with him.
- **fillers.py is the slow step** (one Whisper re-decode per candidate, ~9 min): a smaller model is untested.
- **Reactions**: tuned by eye on Ep 23 / Ep 24 sheets; no ruling yet on frequency (<= 1 per 15 s) or length (2-4 s).
  Nick smokes a pipe on camera - a reaction with the pipe at his mouth passed; say if that is unwanted.
- **No final render / loudness** here: that is the assembly skill's job (not built), as is bringing the intro back.
- No Telegram from this skill (the unused `tg.py` was removed 2026-10-02); a future sender follows his metadata rule
  (width / height / duration from ffprobe, supports_streaming, a cover).
