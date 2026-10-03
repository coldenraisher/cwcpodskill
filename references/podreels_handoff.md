# What CWC_PodRun reads from CWC_PodReels

Written 2026-10-03 from the real Ep 24 delivery (`reels/creative-lens/Ep24/delivery.json`, delivered 09:23 by
CWC_PodReels' own session - Colden: "PodReels session" builds its delivery, this skill only reads it). CWC_PodReels is
never changed from here. If its delivery changes shape, change `scripts/selftest.py`'s fixture FIRST, then `plan.py`.

## The finished signal
`<WORK>/delivery.json` with `"skill": "CWC_PodReels"`, `final_dir` and `delivered_at`. Its `lock.py` writes the file
(the masters are then still in `Shorts/Renders`); its `deliver.py` adds `final_dir`, `dashboard`, `delivered_at` once
every file is verified in `<episode>/Final/Reels`. Without both keys this skill reports "locked, not delivered" and
`plan.py` refuses.

## Per short (`shorts`, in rank order)
| Field | Used for |
|---|---|
| `id` | the product ref (`s03`), the key into themes.json |
| `title`, `yt_title` | the card / the YouTube Short's title |
| `brands` | `cwc`, `tcl` or both = where it posts. Empty (`destination: todd`) = exported only, listed, never posted |
| `master` | `Final/Reels/<yt title>.mp4` - uploaded to YouTube, sent to Metricool, copied into a manual kit |
| `cover` | `Final/Reels/Thumbnails/<yt title>.<ext>`, the cover he PICKED - YouTube thumbnail + Metricool cover |
| `copy.caption` | the Metricool text and the Short's description; its hashtags become the Short's tags |
| `copy.first_comment`, `copy.fb_title` | Metricool first comment; Facebook title (Create with Colden only) |
| `copy.playlist` | `{"cwc": "tcl_shorts", "tcl": "tcl_shorts"}` - per brand, a key of `shows/<show>.json` `publishing.metricool.<brand>.playlists` (or a `PL...` id) |
| `copy.ig_collab` | only compared ("none" = none): the collaborators come from who speaks (ruling 5); a disagreement is flagged |

## Also read from its WORK (records that stay on the Mac after delivery)
- `checked.json` `deliver` - the rank order.
- `themes.json` (`ranges` in phrase ids, `start_word` / `end_word`) + `phrases.json` (`who`, `w`, `start`, `end`) - who
  speaks in each reel (Instagram collaborators) and which reels share footage with a clip (same-topic days).
- `shows/<show>.json` in the skill: `publishing.metricool.<brand>.playlists` / `default_playlist`,
  `publishing.ig_collaborators`.

## Resolve
Its `scripts/rs.py` carries the baton check (2026-10-03, Colden's OK): while `~/.config/cwc/resolve_baton.json`
exists, every Resolve call exits 4 unless CWC_PodReels holds the baton (`baton.py take CWC_PodReels "<what>"`).
No file = no tandem run = nothing changes for a stand-alone run.

## Never from here
`publish.py`, `plan_card.py`, `tg_plan.py` of CWC_PodReels (its own posting steps, out of its flow since its ruling 11).

## Would help (ask its session)
A `next.py <WORK> --json` like CWC_PodClips' (`stage`, `waiting_on_colden`, `next`): this skill's `next.py` would then
show its open cards. Today the progress is read from `approved.json`, `edit/<id>/versions.json` and `copy.json`.
