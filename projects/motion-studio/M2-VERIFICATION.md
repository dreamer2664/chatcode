# M2 — independent render-receipt verification

Task `t-20261013-c435` · Achilles infrastructure lane · stacked on M1 PR #57.

M2 adds a read-only CLI auditor. It does not re-render or infer taste; it
recomputes the accepted-frame and rejected-attempt bytes/pixel metrics and
checks their consistency with recorded evidence.

```bash
node engine/verify.mjs renders/my-film --decode --source-root .
# Exit 0 PASS, 1 FAIL, 2 bad CLI usage; JSON verdict on stdout.
node engine/verify.mjs renders/my-film --require-semantic
# Correctly FAILS if no semantic provider was supplied.
```

## Checks

- Completed status, real chronological timestamps, valid config, exact frame
  budget, no error state, every expected PNG and no extra frame PNG.
- Unique ordered frame IDs and exact `frame/fps` timestamps.
- Bounded revision sequences, no retry after a passed attempt, valid scores,
  honest semantic-provider status, explicit intentional-hold declarations.
- Recompute all final-frame SHA-256 hashes and structural metrics from actual
  pixels, not the JSON headline. Rerun the same mandatory structural gate.
- Retain rejected-attempt PNGs in `attempts/`; verify their hashes and pixel
  metrics too, so reported structural improvement is independently auditable.
- Exact iteration/improvement totals. A retry is not automatically a gain.
- MP4 SHA-256; optional real FFmpeg decode validates output frame count,
  dimensions and duration (2 ms tolerance, appropriate for this CFR encoder).
- Optional source-root comparison checks recorded engine and loaded module/
  asset fingerprints. Local module bytes are frozen on first load; the initial
  scene uses the same snapshot as its declared hash. Engine fingerprints are
  captured at engine import, not from a file edited afterward.

**Legacy support:** M1's single-pass receipts remain verifiable; their missing
engine/import fingerprints are labelled *legacy scene-only*. Older improved
runs without rejected-attempt artifacts cannot fully verify that history and
are refused. M2 records those artifacts and the hold declaration explicitly.
The auditor cannot reconstruct a file that was never retained.

**Limits:** this establishes bundle self-consistency, not authenticity. It is
not a cryptographic signature; someone who can rewrite all bytes, hashes and
JSON can create another self-consistent bundle. Semantic scores are checked
for threshold/metadata consistency, not independently assessed by this CLI.
Fonts/system libraries are not included in module hashes. This does not prove
spring physics, musical beat alignment, artistic 8/10 quality, human review,
or reproducibility on a different browser/font environment.

## Preflight for this stacked PR

The unchanged repository `tools/preflight-pr.sh` compares against main using
a two-dot diff. It exits 1 here, listing the newer board files for Leonidas's
`t-0bd4` and this `t-c435` as absent from the old M1 base. This is recorded,
**not hidden or reported as a standard-tool pass**.

[Stack-aware evidence](evidence/m2-stack-preflight.json) verifies the actual
PR base `agent/achilles/t-20261013-df96`: every change is within this project,
no deletion exists in that diff, and `git merge-tree --write-tree` produces a
clean simulated main merge preserving **both task blobs byte-identically**.
No tool, board file or other agent's artifact was edited to force a pass.
Pericles is asked to decide the stacked-branch preflight policy before merge.

## Evidence

- [31/31 tests PASS](evidence/m2-tests.txt): original 15 tests plus independent
  verification/adversarial cases, including altered PNG/video, missing/extra
  frames, duplicate IDs, wrong timestamps, fake artistic approval/metrics,
  forged improvement totals, artifact traversal, source drift, retained
  rejected-attempt auditing, explicit held frames, real decode and source
  verification.
- [Fresh 48-frame M2 audit PASS](evidence/m2-audit.json): 960×540, 24 FPS,
  2 seconds, all hashes/pixel metrics verified, four source fingerprints match,
  all 48 decoded video frames counted. Semantic provider **not provided**.
- [Fresh M2 manifest](evidence/m2-manifest.json).
- [Latest-engine browser smoke](evidence/m2-browser-smoke.json): real UI export
  of 48 frames independently re-audited with decoder and all four source
  fingerprints; zero page errors/mobile overflow; arbitrary scene submission
  correctly rejected with HTTP 400.
- [M1 legacy 48-frame audit PASS](evidence/m2-legacy-audit.json), explicitly
  scene-only source coverage, not upgraded to full fingerprints.
- [M1 → M2 output identity](evidence/m2-output-identity.json): all 48 PNG hashes
  and the MP4 hash are identical to the committed [sample](evidence/sample.mp4).
  M2 changes evidence/verification, not the calibration film.

The generated `renders/` directory remains ignored; reproduce a complete
frame bundle with the renderer before auditing it. The committed sample is a
review artifact, not the full 48-PNG render directory. Absolute directory
names inside captured audit JSON describe this run and are not hash identity.

No Leonidas-owned physics/audio/semantic modules were changed. The v1 contract
was confirmed by Leonidas in DM `3ff46d92`, with his interface lock `9943becb`.
His quality-lane M2 is **a different task**, `t-20261013-0bd4` (PR #58); this
infrastructure-verifier M2 is `t-20261013-c435`. Achilles reviewed #58 at
`9c1941b` (21/21 tests passed), requested changes with a reproducible score-range
bug and beat-insensitive grading control, and did not manufacture approval.
The review is recorded in GitHub comment `6149760019` and bus `ca6903ec`.
