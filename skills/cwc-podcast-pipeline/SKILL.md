---
name: cwc-podcast-pipeline
description: Run a Create with Colden podcast episode end to end, from one folder of raw recordings to edited, packaged and scheduled posts. Chains Colden's other CWC skills (clips-from-video, youtube-packaging, instagram-carousel) with transcription, editing, clip rendering, a review gate and Metricool scheduling. Use this whenever Colden points at an episode or podcast folder and says things like "process this episode", "run the podcast pipeline", "take this from raw to posted", "edit and post this", "do the whole episode", or asks to resume, continue or check the status of an episode run. Also use it whenever a folder contains `_pipeline/state.json`.
---

# CWC Podcast Pipeline

One episode folder in, a finished episode out: edited master, long clips, vertical shorts,
YouTube packaging, an Instagram carousel, and every post scheduled after Colden approves it.

This skill is the conductor. It does the mechanical work (scan, transcribe, cut, render,
schedule) with the bundled scripts and hands the creative work to Colden's existing skills.

## Ground rules

1. **The episode folder is the unit of work.** Raw files in it are read-only. Everything the
   pipeline writes goes under `<episode>/_pipeline/` (layout in `references/episode-config.md`).
2. **`_pipeline/state.json` is the source of truth.** Always start with
   `python3 scripts/pipeline.py status "<episode>"` and continue from `next`. Wrap every stage in
   `pipeline.py start` / `pipeline.py done` (or `fail` / `skip` with a `--note`) so a later session
   can resume exactly where this one stopped.
3. **Only two checkpoints with Colden:** the kickoff (stage `intake`) and the review (stage
   `review`). Between them, run without asking. Collect questions that come up mid-run (for example
   editorial-only brand mentions) and raise them at review instead.
4. **Nothing is posted without explicit approval at review.** `pipeline.py start publish` refuses
   to run until `pipeline.py approve "<episode>" review --by Colden` has been recorded, and record it
   only after Colden says so in chat. Approval for one episode never carries to another.
5. **Sub-skills run with their questions pre-answered** from `episode.json`. Pass the handoff
   block from `references/skill-handoffs.md` and tell the sub-skill not to ask again.
6. **Protect the context window.** A full-episode transcript is large. When the Agent tool is
   available, run `clips`, `package` and `social` in a subagent each: give it the handoff block,
   have it load the sub-skill, and have it return only output paths plus a 3-line summary.
7. **House writing rules for all copy:** no em dashes or en dashes, minimal emojis (default
   zero), no "0:00 Intro" chapters.

Scripts live in `scripts/` next to this file and need only Python 3.9+ and ffmpeg. Run them with
the episode folder path quoted, because episode folders usually contain spaces.

## Stage map

| # | Stage | Does | Uses | Main output in `_pipeline/` |
|---|---|---|---|---|
| 1 | intake | scan files, kickoff questions | `pipeline.py init` | `manifest.json`, `episode.json` |
| 2 | transcribe | raw-timeline transcript | `transcript.py` | `01_transcribe/transcript.*` |
| 3 | edit | trims, skips, dead air, loudness | `edl.py` | `02_edit/master.mp4`, `edl.json`, `transcript_master.*` |
| 4 | clips | pick long clips + shorts | **clips-from-video** | `03_clips/clip_plan.json` + dashboard |
| 5 | render | cut clips, 9:16 shorts, captions | `render_clips.py` | `04_render/renders.json` + mp4s |
| 6 | package | full-episode YouTube packaging | **youtube-packaging** | `05_package/packaging.json` + dashboard |
| 7 | social | Instagram carousel | **instagram-carousel** | `06_social/carousel.json` + slides |
| 8 | review | schedule + review page, **approval gate** | `publish_plan.py` | `07_review/publish_plan.json`, `review.html` |
| 9 | publish | host media, schedule posts | Metricool MCP | `08_publish/publish_log.json` |
| 10 | wrapup | catalog, trackers, cleanup | | updated `video-catalog.md` |

## Stages

### 1. intake (kickoff checkpoint)

1. `python3 scripts/pipeline.py init "<episode>"`. This creates `_pipeline/`, writes
   `manifest.json`, and creates `episode.json` from `assets/episode.template.json` if it is missing.
2. Read the printed summary. Check that the primary video guess is right, that split camera files
   are listed (they get joined in the edit stage), and whether a transcript already exists.
3. Infer what you can (guest names from file names or notes, episode number from the folder name)
   and write it into `episode.json`.
4. Ask the kickoff questions in **one** AskUserQuestion call, skipping any already set in
   `episode.json`. Put the intake summary (files, duration, primary video) in the question text so
   Colden can correct the source in the same answer:
   - Intro/outro/skip handling: *Auto-detect from transcript (Recommended)* / *I'll give timestamps*
     / *Conventions (first and last 30 to 60s)*
   - Thumbnail style: *Face + bold text* / *Clean minimal* / *Text-only* / *Mix per clip*
   - Caption tone: *Punchy + viral hooks* / *Professional* / *Conversational* / *Match each clip*
   - Posting: *Schedule on cadence (Recommended)* / *Metricool drafts only* / *Stop after review*
5. Save the answers to `episode.json` (`clips.*`, `publish.mode`), set `"kickoff_confirmed": true`,
   then mark intake done. If `kickoff_confirmed` is already true, skip the questions and say so.

### 2. transcribe

- If intake found a `.vtt`/`.srt`/transcript `.json` covering the whole recording, normalise it:
  `python3 scripts/transcript.py normalize "<file>" --out-dir "<episode>/_pipeline/01_transcribe"`
- Otherwise: `python3 scripts/transcript.py transcribe "<source video>" --out-dir ...`, which tries
  local faster-whisper, then the whisper CLI, then the watch-video skill's Whisper API path.
- With split camera files, transcribe the joined file from the edit stage so timestamps line up.
  In that case run `edl.py concat` first (see stage 3), then come back.

### 3. edit

Read `references/editing.md` for the decisions; the commands are:

1. Split camera files: `python3 scripts/edl.py concat "<episode>/_pipeline/02_edit/source_joined.mp4" <parts in order>`
2. Decide head and tail trims from the transcript (first real line after any pre-roll chatter,
   last line of the sign-off) unless Colden gave timestamps. Add any skip segments to `episode.json`.
3. `python3 scripts/edl.py build "<episode>" --source "<source>" --head HH:MM:SS --tail HH:MM:SS`
   writes `edl.json` and `edit_report.md` without rendering. Sanity-check the report: if dead-air cuts
   land in the middle of sentences, raise `--silence-min` or lower `--noise` and rebuild.
4. `python3 scripts/edl.py render "<episode>"` renders `master.mp4` with two-pass loudness
   normalisation to `edit.loudness_lufs` (default -14 LUFS, the YouTube target).
5. Remap the transcript onto the master timeline:
   `python3 scripts/transcript.py remap "<episode>/_pipeline/01_transcribe/transcript.segments.json" --edl "<episode>/_pipeline/02_edit/edl.json" --out-dir "<episode>/_pipeline/02_edit"`

Everything downstream uses `master.mp4` and `transcript_master.*`, never the raw files.

### 4. clips → clips-from-video

Invoke **clips-from-video** through the Skill tool, using whatever name the skills list shows
(for example `clips-from-video` or `anthropic-skills:clips-from-video`), with the clips handoff from
`references/skill-handoffs.md`. Two outputs are required: the usual dashboard and
`03_clips/clip_plan.json` (`{"clips": CLIPS, "shorts": SHORTS}`, same schema as the template).
Without `clip_plan.json` the render stage cannot run.

### 5. render

`python3 scripts/render_clips.py "<episode>"` cuts every clip and short from the master, applies the
`cuts` trims, crops shorts to 9:16, and burns in captions. Use `--fast` for quick previews and
`--only c1,s3` to re-render single items. Spot-check one short by extracting a frame and viewing it.

### 6. package → youtube-packaging

Invoke **youtube-packaging** with the package handoff. It normally needs a YouTube URL; the
handoff switches it to local mode (master + transcript + contact sheet). It must write
`05_package/packaging.json` in addition to its HTML dashboard. Its catalog-update step waits for
wrapup.

### 7. social → instagram-carousel

Invoke **instagram-carousel** with the social handoff, using the master transcript plus the
packaging hook as the "script". Then render the slides to PNG (Instagram needs images) and write
`06_social/carousel.json`.

### 8. review (approval checkpoint)

1. `python3 scripts/publish_plan.py "<episode>"` builds `publish_plan.json` (dates, weekdays, networks,
   titles, captions) and `review.html`.
2. Mark review done, present `review.html` (and the clip and packaging dashboards) to Colden, and
   list anything queued for a decision: editorial-only brand mentions, a missing thumbnail, clips
   you demoted.
3. Apply requested changes by editing the inputs (clip plan, packaging, `episode.json`) and re-running
   the affected stages, then rebuild the plan. Do not hand-edit `publish_plan.json` dates.
4. Only when Colden explicitly approves: `python3 scripts/pipeline.py approve "<episode>" review --by Colden`.

### 9. publish

Follow `references/publishing.md`. In short: confirm every item has public media (upload to the
configured host first), then for each plan item call Metricool `createScheduledPost` with
blogId `5965295` (or `draft: true` in drafts mode), and write each `plannerUrl` back into
`08_publish/publish_log.json` as you go so a crash never double-posts. Skip items already logged.
Finish with a manual checklist for what Metricool cannot set (playlist, end screen, pinned comment).

### 10. wrapup

Append the episode and each long clip to `video-catalog.md` (youtube-packaging step 13), confirm
brand tracker updates went through, delete scratch frames and `--fast` previews, mark the pipeline
complete, and give Colden a short summary: what posts when, where the files are, and anything left
for him.

## When something fails

Mark the stage `fail` with a note saying what broke, tell Colden in one or two lines, and stop.
Do not skip ahead past a failed stage, because every later stage depends on earlier outputs. To redo
a stage after changing its inputs, `pipeline.py reset "<episode>" <stage> --cascade` resets it and
every stage after it.

## Scaffold status

This is v0.1. Implemented and tested: intake, state and gates, transcript normalise and remap,
EDL build, master render with loudness, clip and short rendering with captions, publish plan and
review page. Still to build or decide (tracked in the repo README): multicam and separate-audio
sync, speaker-following reframe for shorts, branded captions, carousel PNG export, thumbnail image
generation, media hosting for Metricool, and an audio-only podcast feed.
