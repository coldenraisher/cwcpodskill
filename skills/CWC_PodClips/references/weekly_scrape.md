# What to add to the Monday scrape (`channel_metrics.json`) - Colden 2026-10-01: "Tell me what to add to that scrape"

Why: the YouTube Analytics API gives this skill views, watch time, % viewed, retention curves, traffic sources and
search terms for every video (`channel_data.py`), but it has NO supported query for thumbnail impressions or
click-through rate on this channel (tested 2026-10-01: the metric name is known, every report shape is refused), and
no A/B test results. Those live only in Studio. CTR is half of this skill's goal, so the scrape is its only source.

Add these keys to `channel_metrics.json` (keep everything it already writes):

1. `per_video` - one row per long-form video published in the last 90 days, plus the 10 best of all time.
   Fastest source: Studio -> Analytics -> Advanced mode -> Content tab -> Export current view (CSV), or read the table.
   ```json
   "per_video": [
     {"video_id": "DnLuxJxJDUc", "title": "...", "as_of": "2026-10-05",
      "impressions": 123456, "ctr_pct": 6.4,
      "impressions_first_7d": 80000, "ctr_first_7d_pct": 7.1,
      "ctr_browse_pct": 5.9, "ctr_suggested_pct": 4.2, "ctr_search_pct": 9.8}
   ]
   ```
   `video_id`, `impressions`, `ctr_pct`, `as_of` are the ones this skill needs; the rest are welcome when the page shows them.
   `channel_data.py` merges the rows by `video_id` (already wired: field `ctr` on each video).
2. `ab_tests` - Test & compare results for every video that has one:
   ```json
   "ab_tests": [{"video_id": "...", "status": "done|running", "winner": "A|B|C|none",
                 "watch_time_share_pct": {"A": 41.2, "B": 33.0, "C": 25.8},
                 "titles": {"A": "...", "B": "...", "C": "..."}, "as_of": "2026-10-05"}]
   ```
3. `channel_reach_28d`: `{"impressions": n, "ctr_pct": x, "as_of": "..."}` (the number the file has been missing
   since 2026-09-07).
4. The same three blocks for The Creative Lens channel under `"tcl": {...}` (clips post there too, 48 h later).
5. Reliability: `updated` must only move when private Studio data was really read (it already works this way - keep
   it). When a run is blocked (signed out, tab blank), send a Telegram line the same day so it is fixed before the
   next episode: this skill stops and asks when the last good run is older than 8 days.
6. Write the file where it is today: `~/Documents/Claude/Projects/Create with Colden/trend_research/channel_metrics.json`
   (this skill also looks in `~/Documents/Claude/CreateWithColden/trend_research/` and takes the newer `updated`).

Not needed from the scrape (the API covers it): views, watch time, average view duration, % viewed, retention
curves, subscribers gained, traffic sources, search terms, first-7-day numbers.
