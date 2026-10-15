# YT05 research dossier — "How Video Compression Squeezes Reality"

Verified 2026-10-15 (UTC). Link checks done live.

## Primary / authoritative
1. **ITU-T H.264 (05/2003), first published edition — FREELY AVAILABLE**
   https://www.itu.int/rec/T-REC-H.264-200305-S/en — "Access: Freely
   available items", English PDF (~1.8 MB). The genuine standard text:
   macroblocks, prediction, transform, quantization, entropy coding.
   The edition is superseded, but its core mechanisms are exactly what the
   film explains (stated in the film to stay honest).
2. **ITU-T H.264.2 reference software (02/16, in force)** — freely available
   https://www.itu.int/rec/T-REC-H.264.2-201602-I/en — cited only if the
   "reference encoder" aside survives the edit.
3. **FFmpeg Filters documentation (official)** — §codecview:
   https://ffmpeg.org/ffmpeg-filters.html#codecview — the exact filter set my
   demos use: `ffplay/ffmpeg -flags2 +export_mvs … -vf codecview=mv=pf+bf+bb`
   renders motion vectors; `codecview=qp` visualizes quantization parameters
   via chroma planes. Demo scripts will live in dossier/demos/ with receipts.
4. **x264 source (GPL)** — https://code.videolan.org/videolan/x264 — for the
   real encoder implementation color (rate control, presets). Cited as the
   implementation actually used on camera.

## Claim sketch → claims.md at script time
- raw 1080p30 ≈ 1.49 Gbps (1920·1080·3·8·30) → arithmetic shown on screen, footnote
  to the standard's level table (H.264, level limits).
- "I-frames carry whole pictures; P-frames point at the past" → H.264 (1).
- "Motion vectors shift blocks from the previous picture" → H.264 (1) + live
  export_mvs capture (3).
- "Quantization tosses detail below the eye's threshold" → H.264 + QP heat map demo (3).
