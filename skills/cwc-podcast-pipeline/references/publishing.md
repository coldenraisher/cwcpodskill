# Publish stage

Runs only after `pipeline.py approve "<episode>" review --by Colden`. Executes
`_pipeline/07_review/publish_plan.json` exactly as approved. If something needs changing, go back to
review, rebuild the plan and get approval again. Do not improvise at publish time.

## Metricool account

- Brand: **Create with Colden**, blogId `5965295`, timezone `America/New_York`
- Connected: YouTube (`UC3fBnVhH68gXhGAnn8J9IcA`), TikTok (`createwithcolden`),
  Instagram (`createwithcolden`), Facebook page, Twitch
- Re-check with `getBrandSettings` if a call fails with an account or network error.

## Step 1: host the media

Metricool only takes **public URLs** (or Google Drive / Dropbox links, which it imports itself
when Drive is linked in Metricool). Local files cannot be sent directly.

`publish.media_host` in `episode.json` picks how this works. **Not decided yet, ask Colden the
first time:**

- `google_drive`: upload to a Drive folder linked to Metricool and use the share links.
- `episode_folder_drive`: the episode folder already syncs to Drive; look up each file's link.
- Anything else he already uses (Dropbox, Frame.io, an S3 bucket).

Write each URL into the plan item's `media_url` (and `thumbnail_url` when there is a thumbnail).
Full episodes are large, so check the host and Metricool upload limits on the first run and record
them here.

## Step 2: schedule each item

For each item in `publish_plan.json` whose id is not already in `08_publish/publish_log.json`:

`createScheduledPost(blogId, date, info)` with `date` = `publish_at` + offset, and `info` built
like this:

| Plan asset | providers | networkData |
|---|---|---|
| full_episode | `youtube` | `youtubeData: {title, type: "video", privacy, tags, category, madeForKids: false}` |
| long_clip | `youtube` | same as full_episode |
| short | `youtube`, `tiktok`, `instagram`, `facebook` | `youtubeData: {title, type: "short", madeForKids: false}`, `tiktokData: {}`, `instagramData: {type: "REEL", showReelOnFeed: true}`, `facebookData: {type: "REEL"}` |
| carousel | `instagram` | `instagramData: {type: "POST"}` with every slide URL in `media` |

Common `info` fields: `text` (description or caption), `media: [media_url]`,
`publicationDate: {dateTime: publish_at, timezone}`, `autoPublish: true`, `draft` = true only when
`publish.mode` is `drafts`, `videoThumbnailUrl` when a thumbnail exists, and `firstCommentText`
for the pinned-comment text when the network supports it.

Notes:
- The YouTube description and the TikTok/Instagram caption are often different. When they are,
  schedule a short as two posts (YouTube alone, then TikTok + Instagram + Facebook) rather than
  forcing one caption on every network.
- Never schedule in the past. If a planned time has already passed (for example review took a
  day), stop and rebuild the plan rather than shifting times silently.
- On any error, log it, stop, and report it verbatim. Do not retry with altered text.

## Step 3: log as you go

After **each** successful call, append to `08_publish/publish_log.json` right away:

```json
{"id": "s1", "asset": "short", "networks": ["youtube", "tiktok", "instagram", "facebook"],
 "publish_at": "2026-10-08T12:00:00", "plannerUrl": "...", "scheduled_at": "<now>", "mode": "schedule"}
```

This makes the stage safe to resume: items already in the log are skipped.

## Step 4: manual checklist

Metricool cannot set these. List them for Colden at the end, filled in from `packaging.json`:

- Add the full episode to playlist **{playlist.name}** (create it with the given description if new)
- End screen → **{end_screen}**
- Pin the comment: "{pinned_comment}" (Metricool's first comment is not pinned)
- Upload the thumbnail by hand if `videoThumbnailUrl` was not applied (unverified channel)
- Anything from `brand_flags` still marked `needs_decision`

## Not covered yet

- Audio-only podcast feed (Spotify, Apple) via the podcast host's API or RSS
- YouTube direct upload as a fallback when a file is too big for Metricool (Studio in Chrome)
- Twitch: connected, but nothing is planned for it
