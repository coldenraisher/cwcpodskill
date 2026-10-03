# Stage 2 - the edit-clips rules against this build (review of 2026-10-01)

Colden 2026-10-01: "I believe all rules should still stand. Review these rules and surface any that don't make sense in
this build." Sources read: edit-clips SKILL.md + references (clips, end_screen, broll, thumbnails, scheduling, copy, qc,
resolve), the saved rulings (played clips, no chapter titles, draft quality, scheduling, Studio package, packaging,
never-destructive, Fusion crash, no jump cuts / keep words), CWC_PodCut SKILL.md, and this skill's rulings 1-22.
Everything NOT listed below carries over unchanged. Nothing here is decided until he rules; his answers go under each
item and become gates in the same change.

## A. Already overruled by a newer ruling of his (the newer one is applied; listed so he can object)
A1. Lower thirds "on every speaker, including Colden and Jake" (edit-clips 2026-09-13) -> guests only (ruling 20).
A2. "Both clips: TCL 1 day after CWC when HOT, else 2" -> TCL at least 48 h after CWC, always (answer 3).
A3. Themes start from the pre-show clip goals, HTML game plan as checkpoint -> transcript + data, short Telegram cards.
A4. Length 5-15 min -> no hard rule, 8-minute target, never padded (answer 8).
A5. Long Telegram copy cards -> the short-card rule (ruling 22) is applied to every Stage 2 message too.

## B. Rules that contradict each other or do not fit this build (need his ruling)
B1. HIDING A SPLICE. Three rules disagree: edit-clips = camera change > b-roll > a visible jump cut as last resort
    (logged), plus a 1.15x eye-pivot punch-in on any single over 10 s; AMIRA (2026-09-28) = "needs to be a camera change
    or a 1.35x punch in. Do not jump cut"; CWC_PodCut (2026-10-01) = "NO JUMP CUTS, NO PUNCH-INS". Clips are spliced far
    more than a PodCut (t05 joins five pieces).
B2. WORD-LEVEL TRIMS. edit-clips tightens pauses over 0.8 s and removes fillers; the PodCut rule keeps every word and
    trims only where a camera change hides it. The approved themes still contain stumbles and asides ("is one is it
    worth", "Eric, we love you, man", "fuck, there's two parts") that only a trim inside a shot can remove.
B3. UHD. "Final delivery is UHD; PodCut, stinger and end screen are UHD" was true for Ep 23 (Colden on a 4K camera).
    Ep 24 is 1920x1080 on every camera: a UHD master is an upscale (4x the render and upload, no added detail; the one
    real gain is YouTube's better codec for 4K uploads). Any punch-in or full-screen share on it is softer still.
B4. NEVER DESTRUCTIVE vs the edit-clips builder. Its `create` renames an existing timeline to `~old` and `cleanup`
    deletes it, and a re-cut moves masters to `_superseded`. The 2026-09-25 rule forbids deletes; the only exception he
    gave is the PodCut lock cleanup.
B5. AUDIO. edit-clips: "exactly what the PodCut has, no processing". AMIRA's finals are rendered at -14 LUFS. The CWC
    PodCut does no loudness step (it was left to an assembly skill that does not exist).
B6. PRE-BUILD EVERYTHING vs CHANNEL AT THE EDIT. edit-clips pre-renders the master while the previous clip is in
    review; the stinger differs per channel and he now decides the channel at the edit review.
B7. TCL OUTRO. Only the Create with Colden outro is measured (Heavy Riff, glitch hit, CR End Screen 11:20). The Creative
    Lens has its own stinger on file and an `End Screen.mov` that was never measured. Three of the five Ep 24 themes are
    suggested for The Creative Lens.
B8. THE HOOK PLAYS TWICE. The cold open is lifted from the body, so the same line is heard again in context. The cold
    reader named that replay as a weak stretch in four of the five themes.
B9. CADENCE "ask every run". The aggregator is meant to run once per episode without stopping.

## C. Fit, but the wording was written for another case (I apply the obvious reading unless he says otherwise)
C1. End-screen timings are frame counts at 30 fps (C-313, 350 frames...). Colden and Todd is 24 fps: converted by time.
C2. "Guest tag at the beginning and end" (PodCut) vs "at first appearance, ~4 s" (edit-clips): in a clip, once, at the
    guest's first close-up of the BODY (not in the cold open), 5 s, same card as the PodCut, re-rendered at the clip's
    resolution, photo from the guest's YouTube channel.
C3. B-roll count "3-4 per short" is a shorts number; for clips the count follows the references that need showing
    (the cold reader's list: Matti Haapoja, Curry Barker, Megalopolis). No text boxes means b-roll is the ONLY way to
    explain a name.
C4. "AI use = No" in Studio stays the default; a clip that carries a GENERATED realistic b-roll image is the one case
    to check before ticking it.
C5. Stock tags name Ep 23's guest (Erik Sutton, OpenPocketCine): guest tags come from the episode, not the show file.
C6. The edit-clips Resolve code runs through the MCP and holds Fusion handles; Stage 2 drives Resolve the CWC_PodCut
    way (Bash runner, timeout, the shared lock file, one short call per Fusion touch). Rules unchanged, code not reused.
C7. Colden and Todd clips: which second channel (The Creative Lens, or Todd's as in the shorts workflow) is asked on
    that show's first run.

## His rulings on section B (Colden 2026-10-01) - each becomes a gate when Stage 2 is built
B1 -> "your recommendation. 1.25 punch always focused on the eyes." = camera change > b-roll > 1.25x eye-pivot punch-in;
      NEVER a jump cut. Every punch-in in a clip is 1.25x and pivots on the eyes.
B2 -> "yes trim in clips to smooth as much as possible. do not cut out the swearing but censor it like we did in
      edit-clips with the censor beep and ducking." = word-level trims are allowed in clips (only where B1 hides them);
      a swear is never trimmed out, it is beeped and the program audio ducked.
B3 -> "default to highest resolution possible. If there is a 4k camera, that is the default output. if all cameras are
      1080. 1080 is output."
B4 -> "correct. keep versions until locked. once all locked, clean up everything you can" = versioned timelines, nothing
      deleted before the lock; when EVERY clip of the episode is locked, the PodCut-style cleanup (backups first).
B5 -> "similar to how we did with /AMIRA_Pod_Build. I need you to create one template timeline that I can add the
      compressor, noise reduction and EQ on, then leave everything else as is until the very end. If it still needs
      loudness bump, add it at the end before final render." = ONE empty template timeline; he puts his Fairlight strip
      on its program-audio track; every clip is a DUPLICATE of it; no other audio processing; loudness measured at the
      end and corrected only if needed (AMIRA: -14 LUFS, true peak <= -1 dBTP).
B6 -> "your recommendation" = one tap on the review card approves AND picks the channel (Colden / Creative Lens / Both);
      the master is rendered after that tap, never before.
B7 -> "use the colden ending on all" = the measured CR outro (Heavy Riff, glitch hit, CR End Screen 11:20) on every
      clip, whatever the channel. (The STINGER is still per channel.)
B8 -> "yes, playing it again in context is very standard. keep it in.." = the hook line stays in the body.
B9 -> "yes set default strongest posting over 7 days and then i approve" = no cadence question; a default plan over the
      7 days after the show, strongest first, sent for one approval.
