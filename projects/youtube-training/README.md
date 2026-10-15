# YouTube training — ten real five-minute films

**Director order, 2026-10-15:** set OUTPOST MARS aside; train the agents to make
videos for YouTube automation. Cut about 15 hard, substantial jobs. The outcome
must include **at least TEN good-quality, five-minute finished videos**.

The Director chose **agent-selected subjects** and **English narration with
English captions**. No genre has been imposed; the slate should teach varied
skills instead of producing ten near-identical template exports.

## The contract

- **15 substantive jobs:** four common production/training jobs, ten individual
  full-video productions, one independent screening and delivery capstone.
- **At least 10 distinct accepted MP4s, each 300–330 seconds.** Target five minutes;
  five minutes of credits, silence, loops or static filler does not qualify.
- **At least 50 minutes of finished content in total.** Scripts, samples, teasers,
  audio-only files, test fixtures and board cards marked done are not videos.
- Every production goes **research → script → storyboard → rough cut → external
  critique → revised final → two independent full-watch reviews → durable delivery**.
- No completion claim until the actual media downloads, decodes, passes technical
  QC and passes editorial review. Automated metrics are NOT artistic approval.

Read **[ACCEPTANCE.md](ACCEPTANCE.md)** before claiming anything, then
**[TRAINING.md](TRAINING.md)** and **[JOBS.md](JOBS.md)**. Machine-readable job links,
slot identities and dependencies are in `campaign.json`.

## Start without a briefing

```bash
# from chatcode, with your kit armed
python3 bin/chatcode --repo-dir . tasks list --status open --tags video-training
python3 bin/chatcode tasks claim <id> --hours 8
python3 bin/chatcode say "plan: <deliverable / evidence / own files>" --type claim --ref <id>
# branch agent/<you>/<id>; heartbeat at a real checkpoint; PR + evidence + ballots
```

**Topic freedom:** each production owner proposes the exact subject and audience
promise, checks the shared slate for collisions, and supplies sources. V01 records
the approved slate; other workers may propose a replacement if it is better and
still distinct. Choose teachable evergreen subjects rather than high-risk advice
or clickbait. Research and scripts can start before the common tooling merges;
the shared-job dependencies gate FINAL EXPORT, not thinking or drafting.

## Reuse what exists; fix its real limitations

- `../motion-studio/` already renders real Canvas → Chromium → FFmpeg clips.
  **Its current limits are 30 seconds / 900 frames per render.** V02 assembles
  bounded shots into a five-minute film with audio and captions; it must not just
  remove caps and hope a giant frame directory survives.
- `../greece/` contains a dossier, script, narration chunks, storyboard and SRT.
  Those are reusable process lessons, **not a delivered five-minute MP4**. An old
  done card or the two-second motion-studio sample does not count toward ten.
- Use existing trustworthy voice tooling where available. No password, paid quota,
  specific premium voice or Director's Windows PC is assumed. Lack of access is a
  blocker to report, never a reason to ship unintelligible speech or fake audio.

## Where work and final files live

| Thing | Place |
|---|---|
| Source code, render recipes and editable film projects | this project / existing motion-studio, per card ownership |
| Production slot work | `videos/YT01/` … `videos/YT10/` |
| Research and final evidence packs | **storagecode** `data/youtube-training/yt-training-s1/<YTxx>/` |
| Actual large MP4s, masters, thumbnails, subtitle files | **Releases on dreamer2664/storagecode**, immutable revision filenames |
| Canonical final asset URLs, SHA-256, technical QC and reviews | each delivery manifest in storagecode; its `data/youtube-training/INDEX.md` is the viewing index |
| Push ledger and shifts | **storagecode** `PUSHES.md` and `shifts/` — NOT the retired storage repo |

No MP4 or WAV piles in ordinary Git. A manifest with a nonexistent asset is not
complete. V15 must publish a simple viewing/download index so the Director can
open all ten final videos without running code. See storagecode/STORAGE_POLICY.md.

## Work order and ownership

V01–V04 can run in parallel. V05–V14 each own a different complete video and may
research immediately; they converge on the accepted shared tools. V15 is blocked
until all ten finals exist and then independently screens the slate. Dependency
IDs and the precise unblock rule are on the cards, not assumed from a title.

Do not wait passively for a dependency: continue work that does not need it, or
record a narrow blocker and take another available job. Estimates are planning
estimates, not a requirement to waste hours. A checkpoint must let a replacement
continue after you disappear.

## Explicit scope boundary

**Mars is PAUSED.** No world map, colonist simulation, PC lease, Mars entrance,
Mars pipeline or Windows bridge work is required for this campaign. Render on
available Linux/Windows hardware. These are upload-ready videos; actual YouTube
posting is a separate, recorded action under the existing approval policy. Do not
invent publication URLs, audience retention figures, copyright clearance or
monetisation guarantees.

Campaign closure belongs to the evidence: **ten accepted final MP4s or not done**.
