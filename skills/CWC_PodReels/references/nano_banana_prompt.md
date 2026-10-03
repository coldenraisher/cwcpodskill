# Nano Banana Pro prompts for AI covers (Colden's guide, applied 2026-10-02)

The full guide Colden supplied is `nano_banana_prompt_guide_colden.md` (read it once). This file is what THIS skill
takes from it, and every line here is a gate in `cover.py add` (`prompt_problems`). `cover.py brief` writes
`edit/<id>/cover/prompt.json` with every locked rule pre-filled; Claude replaces the `<<placeholders>>`, SHOWS COLDEN
the filled JSON, sends that JSON text as the prompt (no fences, no prose), then `add ... --prompt cover/prompt.json`.

## What is applied
- **The prompt is one JSON object** (task, format, main_prompt, reference_images, priority_order, subject, composition,
  text, environment, camera, lighting, color_palette, style, quality_controls). `add` parses it; prose is refused.
- **Reference authority.** ONE reference, `@Image1` (Colden's rule), scoped to IDENTITY ONLY: `authoritative_for`
  face / age / hair / cap / facial hair / skin; `do_not_transfer` the studio background (purple LED panels, shelves,
  desk, lamp), the microphone + boom arm, earbuds, the reference lighting, any text. Round-2 s15 copied the whole
  studio because nothing said what @Image1 was NOT for.
- **Observable expression**: "lips together, no teeth, corners slightly raised, both eyes open" in
  `subject.expression`; a smile / grin / laugh word there is refused even beside "no teeth".
- **Exact text**: `text.mode` = `render_exact_text`, `exact_copy` = the headline (with `\n` for a second line) and
  it must equal `--headline` (the OCR gate reads it back); `placement` in PERCENT of the frame height; "render only
  this headline, nothing else written".
- **Layout for the centre 3:4 without saying 3:4**: "the middle three quarters of the frame height", the top and
  bottom eighths background only; `edge_clearance` in percent (14 % top and bottom, 6 % sides). Never "3:4",
  "portrait format", "three-quarter".
- **Visual hierarchy**: first the face + the prop, second the headline, third a quiet background; ONE idea tied to
  the short (`main_prompt` is one coherent sentence; never a plain face at a desk).
- **Camera + lighting**: eye level, natural portrait perspective (85 mm), no wide-angle distortion (it changes the
  face = identity loss); soft key, gentle fill, one light direction, natural skin texture, moderate contrast.
- **must_avoid** carries the exclusion list: teeth / open mouth / grin, mic / boom / earbuds / headphones, logos /
  posters / film art, other people / duplicates, extra text, misspelled headline, the studio copied, anything
  important in the top / bottom eighth, plastic skin, halos / crushed shadows / saturation.
- **No vague quality words** (masterpiece, viral, perfect, 8k, ultra-detailed ...): refused.
- **Data drives the headline**: a line of the short's gated hook / title, or words carrying a WIN title / cover
  pattern of the current packaging brief (`pack_learn.headline_ok`); shorter is better (one giant word won the PYXIS
  Test & Compare). The scene idea follows "What Studio said this week" in the brief.
- **Feed check**: `cover.py pair` also writes `feed_check.jpg`, both covers as the 270x360 tile the profile grid shows.

## Not taken from the guide
- 16:9 defaults, the YouTube duration-overlay corner, the multi-reference product sections (one reference by rule).
- The black T-shirt default: the wardrobe line defaults to "the same clothes as in @Image1" (change it only when the
  scene needs it).
- Model / resolution / aspect ratio are API parameters (`nano_banana_pro`, `2k`, `9:16`), never prompt text that
  decides anything; `format.aspect_ratio` in the JSON is descriptive and may only say 9:16.
