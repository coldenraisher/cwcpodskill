# What CWC_PodClips hands over, and what the aggregator owns (Colden 2026-10-02)

Colden 2026-10-02: packaging belongs to this skill ("Good add that packaging to this skill and build"); the holistic
posting plan belongs to the aggregator, which sees every finished product of the episode at once.

## CWC_PodClips delivers (per episode): `WORK/delivery.json` (version 2)
**Where the files are** (ruling 43, 2026-10-02): `<episode>/Final/Clips/` on the NAS - `<title A>.mp4` per upload,
`Thumbnails/<title A> - A|B|C.<ext>`, `Captions/<title A>.srt`, and `Ep NN Clips Dashboard.html` (everything needed to
post, with copy buttons). Every path in `delivery.json` points there (`final_dir`, `dashboard`); nothing of the
delivery is left on the Mac. The aggregator STARTS from these files - it never re-renders or renames them.
**The finished signal**: `python3 scripts/next.py "<WORK>" --json` -> `"stage": "delivered"` (anything else: `next` lists
what is left, `waiting_on_colden` what sits on Telegram). A `delivery.json` older than `lock.json` is stale - `next.py` says so.
Top level: `version` 2, `show`, `episode`, `podcut`, `lock_at`, `episode_published`, `full_episode` (per channel: the
PUBLIC "Ep. NN" upload without the phone emoji - ruling 38 - or empty when it was not public yet),
`rules_for_the_plan` (below), `results_loop`, `clips`.
One entry in `clips` per UPLOAD (a clip approved for both channels = two entries), sorted by `push_order`:
- `theme`, `channel`, `version`, `timeline` (the locked "(L)" timeline), `package_file`
- `master` (the loudness-finished file) + `master_carries_stinger_of` (a master may ONLY go to that channel),
  `resolution`, `loudness` (measured), `seconds`, `midroll_possible` (>= 8:00)
- `captions` (.srt on the clip's own clock, swears masked, names fixed)
- `titles` {A, B, C} - A = Colden's pick, B / C written after it (YouTube Test & Compare set)
- `thumbnails` {A, B, C} (1920x1080 under 2 MB) + `thumbnail_meta` (kind of each: still / hook / ai, the model, the
  headline) - A/B/C were approved by Colden as a set; never swap one
- `description` (summary, the full-episode line, handles, Chapters from 0:00, the gear footer on @ColdenRaisher only),
  `chapters`, `tags` (+ `tags_youtube_count`, 470-500 as YouTube counts), `playlists` (ids), `category`,
  `flags` (paid promotion No, AI use No, not for kids, English US, monetization on, no premiere), `pinned_comment`
- `claims_checked`, `hook_quote`, `slug`
- how hard and how fast to push: `push_order` (1 = first; news first, then score), `news` (set ONLY when the theme is
  time-sensitive, with its date and source - else null), `timeliness`, `score`, `suggested_channel`,
  `manual_override` (Colden approved a held theme himself), `both_channels`
- `ab_tests_plan` {B, C} (what each test title tests against A) + `title_features` + `brief` / `learned`: set up
  Test & Compare with exactly these A/B/C - the result is how the next brief learns (ruling 44)
- `needs`: what is still open - `FULL_EPISODE_URL` when the description still holds `{FULL_EPISODE_URL}`
`rules_for_the_plan`: primary channel first, the secondary channel at least `secondary_min_delay_hours` (48) later,
news first then `push_order`, a 7-day default window after the show, one long-form per channel per day, clips around
2 PM ET, no premieres, no short on top of the clip of the same topic, read Studio's scheduled queue first, end screens
link only public videos, each master only on its own channel, ONE plan for ONE approval.

## The aggregator is responsible for
1. **Running the pipeline** once per episode: PodCut -> lock -> CWC_PodClips -> shorts -> anything else, in order, and
   knowing when each product is finished (`next.py --json` stage "delivered" = files in Final/Clips + dashboard).
2. **Reading every finished product together**: the full episode (both channels), the long-form clips, the shorts,
   plus what is ALREADY scheduled or recently posted on both channels (read YouTube Studio's Scheduled queue - Colden
   2026-09-15: "Always look at YouTube Studio to schedule. This is a must!" - Metricool cannot see Studio-native
   schedules).
3. **The full-episode link**: CWC_PodClips fills it already (ruling 38: the "Ep. NN" upload WITHOUT the 📱 emoji - the
   📱 one is the vertical stream). The aggregator only fills `{FULL_EPISODE_URL}` where `needs` still lists it (the
   episode was not public yet when the clips were packaged).
4. **The holistic posting plan** (one approval, Colden 2026-10-01 ruling 31 moves here): slots for every clip upload,
   short and episode across both channels - news / time-sensitive first, CWC before TCL (>= 48 h), one long-form per
   channel per day, clips around ~2 PM ET (quote times in ET), no premieres, shorts not on top of the clip of the same
   topic; sent as ONE plan for one approval (calendar artifact or Telegram card), never posts before the go.
5. **Uploading** each master on the approved slot: YouTube Data API (`publishAt`, private until the audit clears ->
   Studio upload) or Studio via the browser; then title A, description, tags, category, playlists, captions file,
   thumbnail A, flags.
6. **Studio-only work** before each publish time: Test & Compare with the A/B/C titles + thumbnails; end screen
   (import from the last long-form video; slot 1 = the most relevant PUBLIC video, slot 2 = the full episode; never a
   scheduled / private video - re-point it once the next clip is public); paid promotion No, AI use No; the read-back
   checklist per video with its link.
7. **After publish**: the pinned comment ~1 minute after going live (as the owning channel), end-screen re-pointing as
   later clips go public, and the RESULTS LOOP - for every published upload run
   (automatic since ruling 44: `learn.py report` / `package.py facts` find a live upload by its title A/B/C on its channel;
   `python3 scripts/learn.py link "<WORK>" <theme id> <cwc|tcl> <videoId>` only when the title was changed by hand) (it writes `CWC Podcast/data/published.jsonl`;
   never write that file by hand). Views, 7-day views, % viewed and subs then arrive through `channel_data.py pull`;
   the A/B winner goes into the Monday scrape (`references/weekly_scrape.md`).
8. **Cross-product rules**: no two products of the same topic on one channel on one day; where a show's clips may go is the show
   file's `channels` block (Colden and Todd: still to be asked - its `first_run_ask`); Telegram as the single approval surface (one listener per bot - CWC_PodClips' `tg_listen.py`).
9. **The episode wrap-up message** on Telegram: what posts when, where, and what is still waiting on Colden.
10. **When something changes after delivery**: a clip re-locked after a fix (a new master, a new `delivery.json`) -
    replace only that upload, re-read `needs`; a PodCut re-opened after clips exist - stop and ask Colden
    (`next.py` reports it).
11. **Resolve windows**: this skill builds and renders in Resolve only when Colden is not working in it. An unattended
    run needs a window he has given; otherwise stop before `build.py` / `review.py render` / `master.py render` and ask.
