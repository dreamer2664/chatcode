# GREECE — narration (G4, t-20261011-a99a)

Synthetic voice, generated during the build from the G2 script (voice
auditioned and selected for narration use; not cloned from any person).
This is disclosed in the video description and the channel about section:
"Narration: synthetic voice."

**Join order:** part01 → part06, in this order, one act boundary per part
(part02/03 split Act II; join parts, then align to acts via
`subtitles.srt`). Parts were generated from the cleaned script text; cue
timing in the .srt was computed at 140 wpm and must be hand-aligned to
the real audio at edit time (the .srt ships as the alignment scaffold, not
as final cues).

**Quality notes (honest):** mono 44.1 kHz-class output; numbers and names
spoken in full ("four hundred eighty", "Ga-u-ga-mela" risk zones — listen
for Aegospotami, Mardonius, Alcibiades and re-generate any that land
wrong); long sentences read flat at times; no breath marks. Normalize to
-14 LUFS at edit; duck music under the voice per the G3 mood notes.

**Regeneration recipe:** script.md → strip `[source]` tags → split at act
boundaries → pack into <=1400-char sentence-aligned chunks → synthesize
with the registered narration voice. Any fix re-runs only the affected
part; the exception list lives here.
