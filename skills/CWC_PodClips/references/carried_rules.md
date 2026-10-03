# Rules carried over from edit-clips (inlined 2026-10-02 so this skill stands alone)

Colden 2026-10-01: "I believe all [edit-clips] rules should still stand", except what `stage2_rules_review.md` lists as
replaced (splice order, trims, resolution, versions, audio, one-tap review, Colden ending, hook replay, posting plan)
and what rulings 20, 35, 36, 37, 39 replaced later. These are the ones that still apply here, each with his words and
with where it is enforced. Never edit `~/.claude/skills/edit-clips`; this file is the copy that governs CWC_PodClips.

## The clip
- ONE main talking point; opens on the hook / hot take (cold open), ends by closing the loop (2026-09-13).
  -> Stage 1: hook, payoff, story scores + the cold read.
- **Never mid-thought, never mid-word** (2026-09-14: "this edit is rough"). A cut lands on a phrase end.
  -> ranges are phrase ids; `cut.py` "cut inside a word" gate; written trims need a real audio gap.
- **No text boxes, ever**: no chapter titles, no callouts, no correction cards on the picture (2026-09-13 / 09-14,
  "never include those white chapter titles"). Only lower thirds, b-roll and memes. Chapters live in the description.
  -> the builder has no text track; never add one.
- **No burned-in captions**; an SRT is uploaded with the video. -> `captions.py`.
- **Punch-ins pivot on the eyes** (2026-09-14). -> `eyes.py`; a punch with no face found fails the build.
- **Censor every swear**, every speaker; a played clip's own soundtrack is not beeped unless he asks (2026-09-14).
  Timing and the beep file: ruling 35. -> `cut.py` censor, `build.py` beeps, verify.
- **Softened profanity** (2026-09-13): the transcript softens swears ("great shit" -> "great hit"). Every word on
  `soft_swears_to_listen` (hit, duck, spit, ship, crap, freaking...) near an emphatic beat is LISTENED to; a real swear
  is corrected in `phrases.json` (and the clip re-planned so it is beeped), a clean word is left and named in the
  Telegram caption. -> `tg_edit.py send` puts every such word on the card automatically.

## Played clips and screen shares
- **Played clips stay IN** (2026-09-13: "Why did you cut out both clips and leave in the references? It's very
  confusing."). The test: if the clip makes no logical sense without the reference ("look at this", a video the hosts
  react to) it is IN, tightened but never removed while the reactions stay. Decorative / fully explained in words = may
  go. Colden has the full-resolution file of every played clip: ASK for it.
- Ruling 15: an integral screen share must be SHOWN full screen. The layout for that is NOT built: `cut.py` exits 2 on
  a theme with an integral share / a special layout inside its ranges until Colden rules the layout (`share_plan`).

## B-roll (producer mode, 2026-09-12 .. 09-13) - see SKILL.md Stage 2 step 2 for the procedure
- Real material first: article captures, product pages, channel pages, charts, his own footage (his footage beats
  everything - ask when the film IS the subject). Generated images only for generic scenes, never real people, never a
  stock-looking composite when the real thing exists.
- A capture that shows a 404, a consent wall or a bot check is not b-roll: LOOK at every capture. A page that blocks the
  capture is never worked around - use another real source or go without.
- What the b-roll SHOWS must agree with what is SAID at that moment (numbers, names, dates).
- 16:9: crop to the part that matters, pad with the page's own background, >= 8 % margin (the push never clips text).
- Not in the cold open / stinger, not over the name tag, not in the last 1.5 s, edges on a cut or >= 15 frames clear.
- Count: as many as there are references that need showing (a name, a product, a number) - typically 1-4 per clip.
- No text boxes means b-roll is the ONLY way to explain a name the viewer may not know.
- His own designed graphics dropped in the episode's Clips folder replace captured b-roll at that beat.

## Lower thirds
- Guests only (ruling 20 replaced "every speaker"). The card is the PodCut's own; handle = YouTube handle; no handle
  -> ASK, never guess.

## Thumbnails
- **RULE 1 (Colden 2026-10-02, outranks every rule below): the thumbnail is the hook.** "The thumbnail and the title are
  the only thing that engages a viewer to watch my show. the thumbnail needs to be visually diverse and explain what's
  to come in the video." Stop the scroll (one bold idea, readable at 320x180); show what the video is about (the
  topic object in the picture, a promise the video pays off); every option a different idea.
- 1920x1080 under 2 MB, else 1280x720. -> `thumbs.fit`.
- Anything on @ColdenRaisher features Colden - A, B and C alike (2026-09-14).
- Real still: ruling 39 (eyes to camera, confirmed smile by default). Teeth are fine on a real smile (the Ep 24 stills
  he approved show them).
- AI images: likeness from a clean EPISODE still + features spelled out; ONE visual idea; at most THREE words of huge
  text; no logos, no microphones, "REMOVE THE AIRPODS - bare ears" (2026-09-14); expression natural, "not so
  overexaggerated": for Colden a closed-lip grin, "ABSOLUTELY NO TEETH VISIBLE" (2026-09-14, his default for himself;
  applied to every speaker's AI image). Ruling 40 (2026-10-02): "do not allow smiling teeth for AI, usually bad result.
  Can have teeth for different expressions" -> a smile never shows teeth; angry / confused / laughing may. Open-mouth
  shock faces only when he asks.
- Product clips: the ACTUAL product from a reference photo (ask / look in the work folder first) + the brand's logo
  background when he asks; good news = a genuine happy smile.
- Never a real third party's likeness, real film / franchise art, or garbled text in a generated image (Ep 24: a
  Brando look-alike and Star Wars art were regenerated).
- Guests have consented to likeness use in thumbnails of their own episode (2026-09-12).
- A/B/C: A = his pick; B and C titles written AFTER the pick, new angles, the first 5 words of A / B / C all differ,
  never an option he did not pick; thumbnail B = still + hook overlay; C regenerated from title C with A's model.
- Hook overlay: Sora ExtraBold, white + ONE purple (#7C3AED) accent word, text on the side without the face; the
  headline is the hook distilled, not the title (2026-09-15, "those look awesome").

## Copy
- Voice: direct, high-signal, no hype, no em dashes.
- Claims: "Start with context from the script... If it's announced but not yet released we say that... Never make
  costly assumptions." (2026-09-15) -> `claims_checked` gate.
- Description: summary + full-episode link + handles + Chapters; the gear footer on @ColdenRaisher only.
- Pinned comment: an engagement question, two short sentences max, no links, never "drop it below / comment below /
  let me know".
- Tags as close to 500 characters as possible; category Film & Animation on both channels; paid promotion No; AI use No
  (the one case to check: a clip carrying a GENERATED realistic b-roll image).
- Approval = title + thumbnail only; description, tags and pinned comment are written to the rules without a card.

## What moved to the aggregator (ruling 37) - NOT this skill
Posting plan (CWC first, TCL >= 48 h later, one long-form per channel per day, news first, no premieres, ~2 PM ET),
reading Studio's scheduled queue, uploads, Test & Compare, end screens (public videos only), pinned comment timing,
7-day results. See `aggregator_handoff.md`.
