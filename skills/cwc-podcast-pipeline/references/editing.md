# Edit stage

Goal: one clean, loudness-normalised `master.mp4` that is the full episode as it will be published,
plus an `edl.json` that records every cut so all later timestamps can be traced back to the raw files.

## What v0.1 handles

The edit stage assumes the raw folder holds **one program feed**: a single video with good mixed
audio (a switched ATEM recording, or a Riverside, StreamYard or OBS export). It can be split across
several camera files, which get joined first.

| Raw situation | v0.1 behaviour |
|---|---|
| One video with audio | used directly |
| Camera split into chunks (C0001, C0002 / GX01xxxx, GX02xxxx) | `edl.py concat` joins them (stream copy) |
| Several cameras + separate audio recorder | **not yet**: stop and tell Colden; pick the best single feed if he wants to continue |
| Audio only | works; master is audio in an mp4 with no video, shorts are skipped |

Before joining chunks, check that each part's duration and creation time line up (in
`manifest.json`). A missing chunk shows up as a gap in the creation times.

## Decisions Claude makes

**Head trim.** Find the first line that is actually the show (the greeting or cold open) and trim to
about 0.5 s before it. Pre-roll chatter, "are we rolling", countdowns and mic checks all go.

**Tail trim.** End about 1 s after the last sign-off line ("see you next week", "peace"). Post-roll
chatter goes.

**Skip segments.** Anything Colden flagged at kickoff, plus obvious restarts ("let me say that
again"). Restarts need judgement: cut from the start of the flubbed take to the start of the clean
retake. Record each as `{"start", "end", "reason"}` in `episode.json` → `edit.skip_segments` so the
reason shows up in `edit_report.md`.

**Dead air.** Silences of at least `dead_air_min_sec` (default 2.0 s) below `silence_noise_db`
(default -35 dB) are shortened, keeping `dead_air_keep_sec` (default 0.35 s) on each side. These
defaults are deliberately conservative. On a static two-shot every cut is a visible jump, so this
removes real dead air, not natural pauses. If Colden wants a tighter cut, lower the minimum to about
1.2 s.

How to check the result: read `edit_report.md`. If many dead-air cuts are under 2.5 s and fall
between sentences, the threshold is fine. If cuts land on soft-spoken words, the noise floor is too
high: move `--noise` down to -40 and rebuild.

**Loudness.** Two-pass EBU R128 to `loudness_lufs` (default -14 LUFS integrated, -1 dBTP), which is
YouTube's playback target. An audio-only podcast feed would want -16 LUFS. That export is a TODO.

## Output files (`_pipeline/02_edit/`)

| File | What |
|---|---|
| `source_joined.mp4` | only when camera chunks were joined |
| `edl.json` | source path, params, `removed[]` with reasons, `keep[]` with source and master times |
| `edit_report.md` | human-readable cut list |
| `master.mp4` | H.264 CRF 18 + AAC 192k, faststart |
| `master_preview.mp4` | from `edl.py render --fast`; delete at wrapup |
| `transcript_master.*` | transcript remapped onto the master timeline |

## Roadmap for this stage

- Multicam: sync cameras and the recorder by audio cross-correlation, then cut to the active
  speaker using a diarized transcript.
- Intro/outro bumpers: `paths.intro_bumper` / `paths.outro_bumper` concatenated around the master,
  with transcript times shifted by the intro length.
- Resolve handoff: export `edl.json` as CMX 3600 EDL or FCPXML so Colden can open the cut in
  DaVinci Resolve and finish it by hand when an episode needs it.
- Filler-word removal ("um", "uh") from word-level timestamps. This needs a transcription engine
  that returns word timings.
