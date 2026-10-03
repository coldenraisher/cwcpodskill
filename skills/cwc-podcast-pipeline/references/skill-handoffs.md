# Sub-skill handoffs

Each CWC skill was written to be run on its own, with its own questions, inputs and output
locations. These handoffs adapt them to the pipeline. Paste the block (with the placeholders filled)
as the sub-skill's input, or as the subagent prompt when running it in a subagent.

General rules for every handoff:

- Answers already given at kickoff live in `episode.json`. Tell the sub-skill they are final and
  that it must not ask Colden again. If a sub-skill genuinely cannot proceed, it returns the question
  to the conductor, which queues it for the review checkpoint.
- Outputs go in the stage folder named below, not in the sub-skill's default location. If the
  sub-skill insists on its default path, let it write there, then copy the files into the stage folder.
- Each sub-skill must also write a small JSON file for the next stage. The HTML dashboards are for
  Colden; the JSON is for the pipeline.
- The sub-skill's own "deliver" step (sharing a link, summarising) is skipped. The conductor
  delivers everything together at review.

If a sub-skill is not installed, mark the stage `fail` with a note naming the missing skill.

---

## clips-from-video → stage `clips`

```
Run the clips-from-video skill for a CWC podcast episode, as one stage of cwc-podcast-pipeline.

Inputs (already edited; use these, not raw files):
- Transcript: <episode>/_pipeline/02_edit/transcript_master.vtt   (also .txt in [HH:MM:SS] form)
- Video:      <episode>/_pipeline/02_edit/master.mp4
- Episode:    <episode>/episode.json (guests, working title, notes)

Phase 1 answers are final, do not ask again:
- Brand: {brand}
- Skip handling: {clips.skip_detection}. The edit already removed pre-roll and the tail, so only
  skip intro/outro bits that remain in the master.
- Thumbnail style: {clips.thumbnail_style}
- Tone: {clips.tone}. House rules: no em or en dashes, minimal emojis, no "0:00 Intro" chapter.

Limits: up to {clips.max_long_clips} long clips and {clips.max_shorts} shorts; cut anything below
{clips.min_score}.

All timestamps must be on the master timeline (the files above).

Write to <episode>/_pipeline/03_clips/:
1. clips_dashboard.html (from the skill's template, as usual)
2. clip_plan.json = {"clips": CLIPS, "shorts": SHORTS}, the exact arrays you put in the
   dashboard. Put each internal trim in `cuts` as {"ts": "HH:MM:SS – HH:MM:SS", "note": ...};
   say "no trims" in a note without a ts when a clip is clean.
3. Thumbnail candidate frames you picked, as c1_*.jpg etc.

Skip Phase 9 (delivery). Return: paths written + one line per clip (id, score, title).
```

Phase 2 (cleaning the VTT) is mostly a no-op here because `transcript.py` already normalised it.
Phase 2.5 (ffmpeg inspection) and the frame checks still apply and are worth doing.

---

## youtube-packaging → stage `package`

```
Run the youtube-packaging skill for the FULL episode of a CWC podcast, in LOCAL MODE, as one stage
of cwc-podcast-pipeline. The video is not on YouTube yet, so there is no URL.

Replace step 1 (watch the video) with:
a. Metadata: duration from `ffprobe <episode>/_pipeline/02_edit/master.mp4`; title idea, guests
   and notes from <episode>/episode.json. No YouTube page to read.
b. Transcript: <episode>/_pipeline/02_edit/transcript_master.txt (timestamps match the master,
   so chapters can come straight from it).
c. Frames: build the contact sheet from the local master instead of yt-dlp:
   ffmpeg -y -i "<master>" -vf "fps=1/<interval>,scale=360:-1,drawtext=text='%{eif\:t\:d}s':x=6:y=6:fontsize=20:fontcolor=yellow:box=1:boxcolor=black@0.6,tile=4x6:margin=4:padding=4" -frames:v 1 contact.jpg
   Pick <interval> as duration/24 so the sheet covers the whole episode, then Read it.

Steps 2 to 9 run as normal (duration bucket, 3 titles, description, chapters, tags, thumbnail JSON,
pinned comment, category/playlist/end screen).

Step 10 (go-live time): use the live Studio chart via Chrome if it is available. If not, call
Metricool getBestTimeToPostByNetwork (network youtube, brandId 5965295, timezone America/New_York)
for the coming week and note which source you used.

Step 11 (brand flags): push significant gear mentions to the trackers as the skill says. Do NOT
ask about editorial-only mentions; list them in packaging.json under brand_flags with
"needs_decision": true and the conductor raises them at review.

Step 13 (catalog): skip for now. Wrapup appends the entry once the publish date and link exist.

Write to <episode>/_pipeline/05_package/:
1. packaging-<slug>.html (the skill's dashboard)
2. packaging.json:
   {"titles": {"A": "", "B": "", "C": ""}, "chosen_title": "C",
    "description": "full description including CHAPTERS block and footer",
    "chapters": [{"ts": "0:00", "title": ""}], "tags": [],
    "thumbnail_prompt": {...}, "thumbnail_path": null,
    "pinned_comment": "", "category": "SCIENCE_TECHNOLOGY",
    "playlist": {"name": "", "existing": true, "description": null},
    "end_screen": "", "related_video": {"title": "", "url": ""},
    "go_live": {"day": "Wed", "time": "HH:MM", "source": "studio|metricool"},
    "brand_flags": [{"brand": "", "kind": "significant|editorial", "pushed": true, "needs_decision": false}]}
   `category` uses Metricool's enum names (SCIENCE_TECHNOLOGY, PEOPLE_BLOGS, EDUCATION, ...).

Return: paths written + the three titles.
```

Open question: whether long clips also get the full packaging treatment. For now they use the
title, description and thumbnail concept from `clip_plan.json`.

---

## instagram-carousel → stage `social`

```
Run the instagram-carousel skill for brand {brand}, as one stage of cwc-podcast-pipeline.

"Script": <episode>/_pipeline/02_edit/transcript_master.txt. The packaging hook and chosen title
are in <episode>/_pipeline/05_package/packaging.json; use the hook to pick Slide 1.

Path overrides: the skill's built-in /sessions/... paths belong to an old session. Use
episode.json paths instead:
- brand memory file: paths.brand_memory_file (or search the mounted folders for brand-colden-raisher.md)
- backgrounds folder + image-index.md: paths.carousel_backgrounds_dir
- headshot / logo: paths.headshot, paths.logo
If one is missing, build the slide without it and add a note to carousel.json instead of asking.

Write to <episode>/_pipeline/06_social/:
1. carousel-<brand>-<slug>-<date>.html (the skill's output)
2. slide-1.png ... slide-7.png at 1080x1440 (screenshot each slide; see below)
3. carousel.json: {"html": "_pipeline/06_social/<file>.html",
   "slides": ["_pipeline/06_social/slide-1.png", ...],
   "caption": "Instagram caption: hook line, 2 to 3 sentences, CTA, 5 to 8 hashtags",
   "notes": []}

Return: paths written + one line per slide (number, role, headline).
```

PNG export (still a TODO script): load the HTML in Playwright (Chromium is usually preinstalled;
otherwise use the built-in or Chrome browser skills), set the viewport to the slide's full size
(1080x1440), step through slides with the right-arrow key, and screenshot each one.
