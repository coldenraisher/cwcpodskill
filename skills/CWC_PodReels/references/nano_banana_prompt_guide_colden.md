# JSON Image Prompt Guide for Nano Banana Pro in Higgsfield

Use this guide to write structured image prompts for Nano Banana Pro in Higgsfield. It builds on the recurring sections in Colden's earlier JSON prompts: references, identity, product fidelity, composition, text, lighting, color, and quality controls. The method is generic; the thumbnail defaults adapt it to @ColdenRaisher.

JSON is a way to organize the visual brief. The schema below is a custom authoring template, not a documented Higgsfield API request or a guarantee of a perfect result. Higgsfield publishes examples of JSON prompts, but choose the model, aspect ratio, and resolution in the interface. Typing a model name or resolution into the prompt does not establish those settings. The practical recommendations below are an original workflow adapted from Colden's prompt history; platform facts are sourced at the end.

## Step 1 Define the image purpose

Write one sentence explaining what the image must communicate and who will see it. For a thumbnail, identify the video's real topic and the curiosity the image should create. Use the title or content brief to decide the visual idea before adding style. Example: “Show a creator questioning whether this camera deserves an upgrade.” Avoid a claim such as “best camera ever” unless the video actually supports it.

## Step 2 Choose generation or editing

State whether you are creating a new composition from references, editing a supplied base image, or replacing one element. For an edit, identify the base with its actual tag, list the permitted changes, and describe what should remain stable. A text instruction to preserve an area is a request; it does not guarantee unchanged pixels. Use a local editing mask when the tool exposes one and the change is confined to one region.

## Step 3 Prepare and tag every reference

Upload only references that contribute useful information. Prefer a clear face photograph for identity, an accurate product photograph for gear, and a separate layout or style image when needed. Avoid references that contradict the desired age, product model, or composition. A simple layout sketch can clarify complicated placement.

Assign tags by the actual uploaded order. Use the exact spelling `@Image1` for the first image, `@Image2` for the second, and continue sequentially. Keep a tag map and check the attached image thumbnails before generating. If the interface shows a different ordering or assigns reference chips, reconcile the prompt with that ordering. The tags are the requested naming convention; writing a tag alone does not attach an image. Do not use `@ColdenRaisher` as a substitute for an image reference.

| Uploaded image | Prompt tag | Example role |
| --- | --- | --- |
| First image | `@Image1` | Person identity |
| Second image | `@Image2` | Product design |
| Third image | `@Image3` | Pose or composition |
| Fourth image | `@Image4` | Environment or style |

These roles are examples, not fixed rules. If the product is uploaded first, `@Image1` controls the product. Put every tag in the reference list and use it again wherever that reference controls a subject, object, background, or edit. Never mention an unattached reference.

## Step 4 Assign reference authority

For each image, specify its role, the details it controls, the details to preserve, the changes allowed, and the details that should not transfer. This keeps an identity image from also deciding the background or wardrobe. Prefer a narrow role such as “@Image3 controls pose only” over “copy @Image3.”

Example: “Use @Image1 for the person's identity only. Preserve facial proportions, apparent age, hairline, hairstyle, facial hair, and skin tone. Change the pose and lighting as directed. Exclude the microphone and original background.” For multiple views of the same person, say explicitly that they show one person. For multiple products, keep their tags and design rules separate.

Resolve conflicting references by feature: “@Image1 controls identity; @Image2 controls wardrobe; @Image3 controls pose. The identity in @Image3 must not replace the person from @Image1.” A priority list expresses intended importance but does not function as a numeric reference weight.

## Step 5 Write a coherent scene sentence

Use `main_prompt` to describe the image as a whole: subject, action, setting, and visual idea. Write natural sentences inside JSON strings. The fields below add detail. Avoid repeating every instruction in a second complete prompt or packing strings with vague quality terms such as “masterpiece,” “viral,” or “perfect.”

## Step 6 Define subjects and products

Specify the count, framing, body orientation, head direction, gaze, expression, and wardrobe. Use observable directions: “one eyebrow slightly raised and mouth relaxed” is more actionable than “high-CTR reaction.” State whether hands are visible, and describe a grip or gesture if it matters. Distinguish the viewer's right from the subject's right.

For gear, name the correct product when known and attach its reference tag. Preserve visible silhouette, proportions, lens, screens, buttons, materials, and source branding. Choose a view supported by the references. A model asked to show an unseen back panel may invent it. Do not add unverified specifications to the picture, and do not merge features from competing products. When requested, a conceptual oversized foreground product should remain recognizably the same product.

## Step 7 Plan composition and hierarchy

Define the viewpoint, position, approximate scale, depth, and overlap of the major elements. Give a first visual read, a second, and a third. Example: “Camera in the lower-left foreground, person on the right third, short headline upper-left, quiet studio behind.” Reserve text space early.

Percentages are approximate placement guidance, not guaranteed pixel coordinates. For a 16:9 thumbnail, a starting recommendation is roughly 6–8 percent clearance around essential faces, product details, and text. Keep the bottom-right clear of essential content because the duration overlay can cover it. This is a practical design margin, not an official universal YouTube safe zone. Preview at roughly 320 by 180 pixels, and check that the main idea still reads.

## Step 8 Decide the text mode

Choose exactly one mode: `render_exact_text`, `leave_space_for_later`, or `none`. For rendered text, supply final copy, spelling, punctuation, capitalization, intended line breaks, placement, font category, weight, color, and size relationships. A starting recommendation for a thumbnail is two to five words, adjusted for the topic.

Use a JSON newline escape such as `"exact_copy": "WORTH\nIT?"` for two lines. Do not put an unescaped line break inside a JSON string. Treat a requested font and hex color as visual targets that still need review. When typography must match an exact brand asset, add the final text in a design editor.

If text will be added later, leave `exact_copy` empty and reserve a clear region. If no text is wanted, set it empty and request no added text. Separate generated headline copy from authentic product labels. “No added text except source product branding” avoids accidentally removing a label you wanted preserved. Do not include candidate headlines, alternatives, or instructional bracket text in a production prompt.

## Step 9 Describe photography and lighting

Specify the view, perspective, focus targets, and background separation. Use lens language when it communicates a meaningful effect, such as a natural portrait perspective or a deliberately exaggerated foreground. Avoid combining incompatible directions such as a strongly distorted close-up face and an unchanged facial perspective.

Describe light direction, softness, facial exposure, fill, background brightness, and any rim light. Match shadows and reflections across people and products. If both the face and gear must read clearly, ask for both to remain legible rather than requesting extremely shallow focus. Do not rely on a camera brand name alone to create realism.

## Step 10 Set color and finish

Choose a small palette, a specific medium, and the intended finish. Separate headline contrast from photographic contrast: readable white text does not require crushed shadows or unnatural skin. For Colden's default photographic thumbnails, use realistic color, soft flattering light, natural skin texture, moderate contrast, mild retouching, and restrained sharpening. Use a stylized treatment only when the concept calls for it.

## Step 11 Add focused quality controls

List the essential visible outcomes and the errors most likely for this image. Keep the list short and relevant: changed facial identity, fused products, extra objects, additional text, misspelled headline, plastic skin, or oversharpening halos. Prefer a positive instruction such as “one clearly separated camera with source-accurate controls” alongside a specific exclusion.

Treat `must_avoid` or `negative_prompt` as descriptive instructions in the prompt. Do not assume either key invokes a separate negative-prompt engine. Do not invent `CFG`, sampler, seed, reference weight, identity strength, or strictness values as operative controls. Use an actual interface control only when it exists and its behavior is documented.

## Step 12 Validate and iterate

Validate the JSON, then check the visual logic. Use double quotes, unique keys, valid commas, escaped quote marks, and arrays for lists. Remove comments, trailing commas, placeholders, unused references, contradictory instructions, and competing layout variants. Remove optional sections that do not apply instead of filling them with meaningless values.

In Higgsfield, select Nano Banana Pro, choose the appropriate generation or reference mode, attach the images in the mapped order, and set the available aspect ratio and resolution controls. Paste the JSON object into the prompt field without Markdown fences, a prose preamble, or the reusable writer instructions from this guide. Generate, then review likeness, product geometry, headline, layout, color, and anatomy. Adjust one problem at a time. If you switch to editing a result, rebuild the reference map for the new upload set.

## Generic JSON skeleton

This is a teaching skeleton. Replace every bracketed value, remove unused sections, add only uploaded references, and keep text mode consistent before using it in Higgsfield.

```json
{
  "task": "Create one finished image for [purpose and audience].",
  "format": {
    "aspect_ratio": "[16:9, 1:1, 9:16, or another supported ratio]",
    "orientation": "[landscape, square, or portrait]"
  },
  "main_prompt": "[One coherent sentence describing the subject, action, setting, and visual idea.]",
  "reference_images": [
    {
      "tag": "@Image1",
      "upload_order": 1,
      "role": "[Identity, product, pose, environment, style, layout, or base image]",
      "authoritative_for": [
        "[Specific features this image controls]"
      ],
      "preserve": [
        "[Features that must remain recognizable or accurate]"
      ],
      "allowed_changes": [
        "[Explicit changes permitted for this reference]"
      ],
      "do_not_transfer": [
        "[Background, accessories, text, identity, or other irrelevant features]"
      ]
    },
    {
      "tag": "@Image2",
      "upload_order": 2,
      "role": "[Role of the second uploaded image]",
      "authoritative_for": [
        "[Specific features controlled by @Image2]"
      ],
      "preserve": [
        "[Required details]"
      ],
      "allowed_changes": [
        "[Permitted changes]"
      ],
      "do_not_transfer": [
        "[Features to exclude]"
      ]
    }
  ],
  "priority_order": [
    "[Highest priority]",
    "[Second priority]",
    "[Third priority]"
  ],
  "subject": {
    "source": "@Image1",
    "count": 1,
    "framing": "[Close-up, chest-up, waist-up, full-body, or object framing]",
    "pose": "[Body orientation, head orientation, and hand position]",
    "expression": "[Observable facial expression, if applicable]",
    "gaze": "[Where the subject looks, if applicable]",
    "wardrobe": "[Preserve or explicitly replace wardrobe]"
  },
  "products": [
    {
      "source": "@Image2",
      "count": 1,
      "placement": "[Position and approximate size]",
      "orientation": "[Visible side and angle]",
      "accuracy_rules": [
        "[Design, proportions, controls, material, branding, or labels to preserve]"
      ]
    }
  ],
  "composition": {
    "viewpoint": "[Viewer-relative placement and camera viewpoint]",
    "layout": "[Describe where each subject, product, and text area sits]",
    "visual_hierarchy": [
      "[First visual read]",
      "[Second visual read]",
      "[Third visual read]"
    ],
    "depth": "[Foreground, middle ground, and background relationships]",
    "clear_space": "[Area reserved for text or other design needs]",
    "edge_clearance": "[Practical margin and overlay clearance]"
  },
  "text": {
    "mode": "[render_exact_text, leave_space_for_later, or none]",
    "exact_copy": "[Final text with \\n for an intended line break, or empty string]",
    "placement": "[Location, or empty string]",
    "typography": "[Font category, weight, line arrangement, and size relationship]",
    "color": "[Text color and contrast treatment]",
    "rules": [
      "[Text-specific requirements consistent with the selected mode]"
    ]
  },
  "environment": {
    "setting": "[Specific background or location]",
    "detail_level": "[Amount and kind of visible background detail]",
    "reference_source": "[Reference tag if used; otherwise omit this field]"
  },
  "camera": {
    "perspective": "[Natural perspective or a deliberate photographic effect]",
    "focus": "[Elements that must remain sharp]",
    "depth_of_field": "[Amount of separation; preserve important details]"
  },
  "lighting": {
    "key": "[Direction, softness, and brightness]",
    "fill": "[Shadow treatment]",
    "separation": "[Optional rim light or background separation]",
    "consistency": "[How lighting and shadows connect all scene elements]"
  },
  "color_palette": {
    "dominant": [
      "[Main colors]"
    ],
    "accent": [
      "[Accent colors]"
    ],
    "skin_and_materials": "[Natural color and material requirements]"
  },
  "style": {
    "medium": "[Photography, illustration, 3D, or another medium]",
    "finish": "[Specific visual treatment]"
  },
  "quality_controls": {
    "must_include": [
      "[Essential visible requirements]"
    ],
    "must_avoid": [
      "[Specific likely errors relevant to this scene]"
    ]
  }
}
```

## Colden thumbnail defaults

Use these defaults only when the video brief does not specify something else. Preserve recognizable likeness from the supplied reference, including facial structure, apparent age, hair, and skin tone. Use a plain fitted black T-shirt when no wardrobe is specified. Use a believable expression tied to the topic. Remove microphones, boom arms, or earbuds when the brief calls for their removal, and identify those changes explicitly.

Start with 16:9, a clear face or product silhouette, a simple background, and one visual idea. Favor accurate gear and a short honest hook aligned with the title. Use soft flattering light, realistic color, natural skin, mild retouching, and restrained sharpening. Keep the essential content within practical margins and away from the duration overlay. These defaults do not require every thumbnail to use the same left-right layout.

## Filled thumbnail example

This illustrates the structure with two references: a Colden photograph and a camera photograph. The headline is an example, not a claim about a particular video. Replace it with the actual content-aligned hook.

```json
{
  "task": "Create one photorealistic YouTube thumbnail for @ColdenRaisher.",
  "format": {
    "aspect_ratio": "16:9",
    "orientation": "landscape"
  },
  "main_prompt": "Show Colden reacting with thoughtful skepticism to the camera from @Image2, with Colden on the right, the camera in the lower-left foreground, and a short headline above it.",
  "reference_images": [
    {
      "tag": "@Image1",
      "upload_order": 1,
      "role": "Colden's identity",
      "authoritative_for": [
        "Facial identity, apparent age, hairstyle, hairline, facial hair, and skin tone"
      ],
      "preserve": [
        "Recognizable facial structure and natural skin texture"
      ],
      "allowed_changes": [
        "Pose, expression, lighting, background, and wardrobe as specified below"
      ],
      "do_not_transfer": [
        "Microphone, boom arm, earbuds, reference background, or existing text"
      ]
    },
    {
      "tag": "@Image2",
      "upload_order": 2,
      "role": "Authoritative camera product reference",
      "authoritative_for": [
        "Camera body and visible product details"
      ],
      "preserve": [
        "Silhouette, proportions, lens shape, control placement, materials, and visible source branding"
      ],
      "allowed_changes": [
        "Placement, scene lighting, and modest perspective adjustment consistent with visible source geometry"
      ],
      "do_not_transfer": [
        "Reference background, unrelated accessories, or photographic borders"
      ]
    }
  ],
  "priority_order": [
    "Preserve Colden's recognizable likeness",
    "Preserve the camera's source design",
    "Keep the headline and visual idea readable at small size",
    "Use natural lighting and realistic color"
  ],
  "subject": {
    "source": "@Image1",
    "count": 1,
    "framing": "Chest-up on the right third",
    "pose": "Torso turned slightly toward the camera product; head turned toward the viewer; hands outside the crop",
    "expression": "One eyebrow slightly raised, relaxed mouth, subtle skeptical expression",
    "gaze": "Direct eye contact with the viewer",
    "wardrobe": "Plain fitted black T-shirt"
  },
  "products": [
    {
      "source": "@Image2",
      "count": 1,
      "placement": "Lower-left foreground, approximately one-third of the frame width",
      "orientation": "Use the visible three-quarter angle from @Image2",
      "accuracy_rules": [
        "Keep the camera visually separate from Colden",
        "Do not combine its design with another model",
        "Preserve the visible source branding without inventing additional labels"
      ]
    }
  ],
  "composition": {
    "viewpoint": "All left and right directions refer to the viewer",
    "layout": "Colden on the right; camera below the headline on the left; no overlap between the face, camera silhouette, and headline",
    "visual_hierarchy": [
      "Camera and skeptical reaction",
      "Headline",
      "Quiet studio background"
    ],
    "depth": "Camera in the foreground, Colden in the middle ground, unobtrusive studio background behind",
    "clear_space": "Upper-left area for the headline",
    "edge_clearance": "Keep essential elements about 7 percent from the outer edges; leave the bottom-right area free of essential content"
  },
  "text": {
    "mode": "render_exact_text",
    "exact_copy": "WORTH\nIT?",
    "placement": "Upper-left, on two lines",
    "typography": "Large bold condensed sans-serif capitals; IT? slightly larger than WORTH",
    "color": "White with a restrained dark outline or shadow",
    "rules": [
      "Render only the headline and branding visible in @Image2",
      "Preserve exact spelling and punctuation",
      "Keep the headline clear of Colden's face and the camera"
    ]
  },
  "environment": {
    "setting": "A simple, darker creator studio",
    "detail_level": "Soft, unobtrusive background shapes; no identifiable extra gear"
  },
  "camera": {
    "perspective": "Eye-level view with natural facial proportions",
    "focus": "Colden's eyes and the camera product both clearly legible",
    "depth_of_field": "Soft background separation without blurring either focal element"
  },
  "lighting": {
    "key": "Large soft frontal key, slightly above eye level, with bright natural facial exposure",
    "fill": "Gentle fill retaining detail in the shadows",
    "separation": "Subtle neutral separation from the background",
    "consistency": "Match the key-light direction and believable shadows on Colden and the camera"
  },
  "color_palette": {
    "dominant": [
      "Deep neutral charcoal",
      "Natural skin tones",
      "Source camera colors"
    ],
    "accent": [
      "Restrained white headline"
    ],
    "skin_and_materials": "Neutral skin tone and realistic product materials"
  },
  "style": {
    "medium": "Photorealistic editorial photography",
    "finish": "Clean natural detail, moderate contrast, mild retouching, restrained sharpening"
  },
  "quality_controls": {
    "must_include": [
      "One recognizable Colden",
      "One accurate camera from @Image2",
      "Exact two-line headline",
      "Clear face and product silhouettes"
    ],
    "must_avoid": [
      "Changed facial proportions or age",
      "Plastic skin or heavy beauty retouching",
      "Fused or invented camera parts",
      "Extra people or camera duplicates",
      "Additional headline text",
      "Oversharpening halos, crushed shadows, or excessive saturation"
    ]
  }
}
```

## Reusable instructions for a prompt writing AI

Copy the following instructions into the AI that will write your prompts. Supply the image brief and references afterward. Paste only its final JSON image prompt into Higgsfield.

```text
Act as an expert generative image prompt writer for Nano Banana Pro in Higgsfield.ai. Use my existing JSON prompt, when supplied, as the base. Preserve correct creative decisions and improve clarity, reference authority, visual hierarchy, and consistency.

First identify the purpose, audience, visual idea, creation or editing mode, aspect ratio, subjects, products, reference roles, permitted changes, text mode, lighting, and style. Inspect supplied references when available. Ask only for missing details that materially affect identity, product accuracy, exact text, or the central concept. Otherwise use sensible stated defaults during planning. Do not pretend to have inspected an unavailable image.

Map every uploaded reference by its actual order: @Image1, @Image2, @Image3, and so on. Do not invent references or use the channel handle as an image tag. For each reference, state its role, authoritative features, preservation requirements, allowed changes, and excluded transfers. Repeat its exact tag in the sections it controls. Resolve reference conflicts by feature.

Write one coherent main scene sentence, then organize details using task, format, main_prompt, reference_images, priority_order, subject, products, composition, text, environment, camera, lighting, color_palette, style, and quality_controls. Add a base-image edit scope if editing. Remove sections that do not apply. This is a descriptive prompt schema, not a Higgsfield API request.

Specify counts, observable poses, gaze, expression, viewer-relative placement, approximate scale, depth, overlap, and focus. Preserve source identity and source product design. Avoid inventing unseen product details, features, labels, or unsupported factual claims.

Choose one text mode: render_exact_text, leave_space_for_later, or none. For rendered text, use final exact wording and specify typography, placement, color, and line breaks. Separate headline rules from authentic source product labels. Do not place candidate hooks or alternatives in the final prompt.

For @ColdenRaisher thumbnails, default to 16:9, recognizable likeness, a fitted black T-shirt when unspecified, soft flattering light, natural skin texture, realistic color, moderate contrast, mild retouching, and restrained sharpening. Use a short honest hook aligned with the video. Keep essential elements away from edges and the bottom-right duration overlay. Follow explicit brief instructions over these defaults.

Use natural-language instructions inside valid JSON. Treat priorities and exclusions as descriptive directions, not executable controls. Do not invent seed, CFG, sampler, reference weight, identity strength, or quality numbers. Model, resolution, and available aspect-ratio controls belong in Higgsfield's interface.

Before returning the prompt, check JSON syntax, tag consistency, attached-reference count, identity and product authority, visual feasibility, exact text, and conflicting instructions. Remove placeholders, redundant wording, and unused fields. Return one valid JSON object only, with no Markdown fences, commentary, or multiple variants, unless I specifically request explanation or alternatives.
```

## Quick review

- Every attached image has the correct sequential `@ImageN` tag and an explicit role.
- Identity, product, pose, and style references do not overwrite each other's authority.
- The main idea is clear, and layout, scale, and depth agree.
- Text mode, final copy, and source-label rules agree.
- Lighting, focus, skin tone, and materials are coherent.
- No unsupported features, misleading claims, placeholders, or invented controls remain.
- JSON parses, and the result is checked at full size and thumbnail size.

## Platform facts and sources

Checked October 2, 2026. Higgsfield's help center describes Nano Banana Pro generation, reference-role assignment, up to 14 references, and 1K drafting followed by 2K or 4K output. Available controls should be checked in the current interface. Its expert-use-case article demonstrates JSON as prompt content. Google's guidance covers explicit visual direction and reference roles, and notes that small text, complex blending, and character consistency can still need correction.

- [Higgsfield Nano Banana help center](https://higgsfield.ai/creator-hub/help-center/ai-models/how-do-i-use-nano-banana)
- [Higgsfield JSON prompt example](https://higgsfield.ai/blog/Nano-Banana-Pro-Expert-Use-Cases)
- [Google Nano Banana Pro prompting tips](https://blog.google/products-and-platforms/products/gemini/prompting-tips-nano-banana-pro/)
- [Google image generation documentation](https://ai.google.dev/gemini-api/docs/image-generation)

The `@Image1` naming convention follows Colden's requested workflow. The retrieved documentation supports assigning each reference a role; it does not establish a universal custom JSON schema or guaranteed uppercase-tag parser. Verify the actual uploaded reference order and any reference chips in the current Higgsfield interface.

