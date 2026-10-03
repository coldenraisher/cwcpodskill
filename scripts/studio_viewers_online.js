// Copied from the youtube-packaging skill (scripts/studio_viewers_online.js, 2026-06-23) for CWC_PodRun cal.py peaks.
// Navigate to https://studio.youtube.com/channel/<CHANNEL ID>/analytics/tab-build_audience/period-default first:
//   Create with Colden UC3fBnVhH68gXhGAnn8J9IcA, The Creative Lens UCPcaMEVrhEwy08fK01U-Niw. Save the returned string to a file.
// Paste into the Chrome MCP javascript_tool AFTER navigating to:
//   https://studio.youtube.com/channel/UC3fBnVhH68gXhGAnn8J9IcA/analytics/tab-build_audience/period-default
// Confirm you are on the Create with Colden channel (not the old gymnastics channel)
// and logged in. Returns each weekday's peak ("MOST") and quiet ("SOME") hours in
// Colden's local time (ET), last 28 days. The data lives in per-day aria-labels.
await (async () => {
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  await sleep(3000);
  const card = document.querySelector('yta-audience-online-card');
  if (!card) return 'CARD_NOT_FOUND (check login + correct channel + that the Audience tab loaded)';
  const subtitle = (card.querySelector('yta-title-subtitle-header')?.innerText || '').replace(/\s+/g, ' ').trim();
  const days = [...card.querySelectorAll('[aria-label]')]
    .map(e => e.getAttribute('aria-label'))
    .filter(a => /day/i.test(a) && /viewers are on YouTube/i.test(a));
  const out = days.map(a => {
    const lines = a.split('\n').map(s => s.trim());
    const day = lines[0]; const most = []; const some = [];
    for (let i = 1; i < lines.length; i++) {
      if (/Most of your viewers/i.test(lines[i])) most.push(lines[i - 1]);
      else if (/Some of your viewers/i.test(lines[i])) some.push(lines[i - 1]);
    }
    return day + ': MOST ' + most.join(', ') + ' | SOME ' + some.join(', ');
  });
  return JSON.stringify({ subtitle, days: out });
})();
