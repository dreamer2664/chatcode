# YT05 pitch — "How Video Compression Squeezes Reality"

- **Owner:** odysseus · card t-20261015-eee1 · claimed 2026-10-15
- **Genre slot:** how a system works · **Target:** 05:00–05:30, EN narration + captions
- **Status:** pitch → research (final export gated on accepted V02/V03)

## Subject and audience promise
Five minutes of this film at 1080p raw would be ~7.5 GB. The file the viewer
gets is ~60 MB. **Where did 99% of the picture go — and why does it still look
real?** The answer is H.264's four tricks: chop frames into blocks, remember the
past (I/P frames), point arrows at what moved (motion vectors), and blur the
details eyes forgive (DCT + quantization). Viewer: the curious streamer who has
burned a terabyte of video and never asked how. Promise (first 15s): "I'll show
you the arrows your TV hides — the ones that tell your screen how to skip most
of the work." Format: ORIGINAL demonstrations — I encode real test footage
myself with ffmpeg and visualize the hidden structure (official codecview
filter: motion arrows drawn live over my own frames; QP heat maps of my own
encodes). No borrowed explainer footage anywhere.

## Why this teaches its maker
A video about the compression that will carry my own nine other films. The
maker learns the physics of her own medium — and leaves receipts (encode logs,
raster dumps) that V02's tooling can reuse as honest fixtures.

## Failure risks
1. *Codec math freezes viewers* → one analogy per trick (gesture-level, verified
   against the ITU text), math kept to "the picture becomes a recipe".
2. *Demo artifacts could be faked* → every visual accompanied by its full
   ffmpeg command in the dossier; outputs re-derivable bit-for-bit.
3. *Patent/patent-pool scare segment* → deliberately OUT of scope; the film is
   mechanism, not law (stated on screen; saves 45 risky seconds).

## Acceptance anchors
≥20 purposeful shots incl. 3 treatments (live encode demo, original diagrams,
real camera footage of my own test scenes); claim ledger maps each mechanism
claim to the ITU H.264 (05/2003) freely-available edition or x264/ffmpeg docs.
