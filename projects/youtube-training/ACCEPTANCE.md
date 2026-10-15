# Acceptance — what counts as one of the ten

**Binding for every production card and V15. No manager may substitute a script,
placeholder, teaser, test fixture or a self-awarded quality score for a film.**

## 1. The real media

- Ten distinct subjects and audience promises, reserved in the slate. Each video
  is newly assembled for this campaign, not an old sample renamed ten ways.
- **300.0–330.0 seconds each**; target 05:00. At least **3,000 seconds** total across
  the ten accepted films. At most 10 seconds combined for branded intro/outro.
  No padding with silence, loops, repeated paragraphs or an unchanging end card.
- 1920×1080, 16:9, H.264/yuv420p MP4, constant 24/25/30 FPS; AAC audio at 48 kHz,
  at least 160 kb/s. Full-file decode must succeed, not just the first frame.
- Actual, intelligible **English narration** and synchronized **English SRT and
  VTT**, plus a plain transcript. Roughly 650–800 spoken words is a planning aid;
  the actual timed performance determines length. Do not stretch bad audio to fit.
- Integrated loudness target **−16 LUFS ±1.5**, true peak **≤ −1 dBTP**. Dialogue
  remains clear on a phone speaker. Music is optional, licensed and subordinate;
  sustained silence, clipped speech and accidental dropouts are hard failures.
- Captions: normally ≤2 lines and ≤42 characters/line; target ≤17 characters/sec,
  hard cap 20 unless a reviewer explicitly approves a recorded exception. Verify
  spoken alignment by listening; target ≤250 ms offset at checked cues.

## 2. Research, rights and truthful storytelling

- A specific intended viewer, a useful promise and an opening that earns interest
  in the first 15 seconds without deception. A coherent ending answers the promise.
- At least **three credible sources**, including one primary or authoritative
  source where applicable. A claim ledger maps every material factual claim to
  its source and the script/film timestamp. Mark uncertainty, do not fabricate it.
- Source links and a rights/provenance ledger for **every external image, clip,
  music track, sound effect and voice**. Record license, attribution, source URL,
  access date and permitted use. "Found on Google" is not permission. Tool output
  is labeled as synthetic where relevant; no imitated real-person voice.
- Titles and thumbnails accurately describe the film. No invented experiment,
  fake live data, fabricated browser recording or borrowed creator footage.

## 3. Actual visual craft

- A timecoded shot list covers the full film. Aim for **at least 20 purposeful
  shots/segments** and at least three relevant visual treatments (for example:
  demonstration, explanatory diagram, sourced image, chart, original animation).
  A lower count is acceptable only with a reasoned independent editorial verdict;
  arbitrary cuts are not quality. Real-time demonstrations may legitimately hold.
- Visuals explain the spoken ideas rather than decorate an unrelated monologue.
  Use hierarchy, composition, readable text, continuity, intentional transitions,
  deliberate motion and a paced sound mix. All must remain readable on a phone.
- No black/frozen frames, missing assets, cropped captions, broken charts or
  accidental stillness. Intentional holds/fades require timecoded explanations,
  not a global exception that defeats the check.
- Every video must make a rough cut, receive concrete non-owner notes, and submit
  a revised final with a before/after log. The same reusable engine is welcome;
  ten near-identical films differing only in text are not.

## 4. Quality is reviewed, not inferred from FFmpeg

Two **distinct non-owner reviewers** watch the **entire exact final MP4**, with
sound, and bind their reviews to its SHA-256. Neither may be the production owner;
no forged ballots, blind acceptances or owner-authored substitute reviews.

Each review contains:
- reviewer identity; final SHA-256; watched duration; full-watch attestation;
- at least five useful timestamped observations; corrections and their resolution;
- phone/readability and speaker/headphone checks;
- this rubric (score plus concrete reasons, not an automatic formula):

| Dimension | Points |
|---|---:|
| Research, accuracy and sourcing | 20 |
| Story, clarity and audience value | 20 |
| Narration and sound | 15 |
| Visual craft and explanatory usefulness | 20 |
| Editing and pacing | 15 |
| Packaging, captions and accessibility | 10 |
| **Total** | **100** |

**Each reviewer must score ≥80/100, with ≥70% in every dimension**, and report no
unresolved critical/major defect. A rights, accuracy, unintelligibility or missing
media failure cannot be averaged away. Rework until both reviews pass. A changed
final hash invalidates old approvals: re-review that exact new file.

## 5. The delivery pack — retrievable, not just described

For each YT01–YT10, archive the small evidence under:
`storagecode/data/youtube-training/yt-training-s1/<YTxx>/`.

Required:
1. `delivery.json`: slot/task/owner/title/topic/language, exact source commit,
   recipe/version, full duration, final media URLs + byte counts + SHA-256s,
   download verification, checks and reviewer identities/hash bindings.
2. Final MP4; narration/master audio; SRT; VTT; transcript; **1280×720** final
   thumbnail and editable project; title/description/chapters/credits text.
   Large binary files belong to **storagecode Releases**, not normal Git.
3. Sources/claims and rights ledgers; complete storyboard; rough-cut review;
   revision/change log; measured ffprobe, full-decode, audio and caption QC.
4. Two complete final-review records and the ordinary non-owner board ballots.
5. A render/run receipt with commands, environment/tool versions, render time,
   source and artifact hashes, recoverable paths and any honest exceptions.

Use immutable revision names. Do not delete or silently replace an approved
asset. The Director must be able to click a link and download/watch the final
MP4; a dead, private-without-access, local-only or placeholder link fails delivery.

## 6. Campaign closure (V15)

V15 independently downloads all ten final assets, re-hashes them, full-decodes
them, verifies durations total at least 50 minutes, checks all exact-hash approvals,
and watches the entire slate for duplication, factual/rights problems and craft.
It publishes the viewing index with ten working final-video links, subtitles and
thumbnails. Rejected films go back to their production owner; V15 stays blocked
until the ten-film minimum is genuinely met. **A green test suite is necessary
for tooling; it is never proof that ten good videos already exist.**
