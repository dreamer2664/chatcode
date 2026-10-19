# Fieldnotes — Motion Design Studio / M1

Achilles's infrastructure prototype, assigned by Pericles in DM `016e85fb`.
Task: `t-20261013-df96`. Leonidas owns the spring/beat/perceptual-quality lane.

**What works:** trusted scene code paints deterministic Canvas frames in
headless Chromium; Node captures each lossless PNG, grades measurable structural
checks, retries a finite number of times, and FFmpeg encodes actual H.264 MP4.
A responsive studio UI previews, seeks, renders, cancels, downloads and exposes
quality manifests. No cloud service, model API, or external page assets.

**What is NOT claimed:** no perceptual 8/10 guarantee, reference-video
transcription, spring physics enforcement, musical beat analysis, or complete
semantic self-critique. Both supplied TikTok links return HTTP 403 in this
runtime. Uploading the videos/transcripts would unblock reference analysis.
The original vector calibration scene is not the final artistic deliverable.

## Run (Node 20+, Linux x64 prototype)

```bash
cd projects/motion-studio
npm ci
npx playwright install --with-deps chromium
npm test
npm start                    # binds 0.0.0.0:8787, accepts preview hosts
# PORT=9000 npm start        # optional
npm run render -- --out renders/my-film --duration 4 --fps 24
```

System dependencies may require root/sudo. The setup downloads Chromium.
Node dependencies and browser/system packages do not persist with workspace
snapshots; reinstall them in a fresh runtime. The lockfile is committed.
The pinned Linux x64 FFmpeg npm binary supplies a prototype encoder; set
`FFMPEG_PATH=/absolute/path/to/ffmpeg` to prefer a maintained system build.
This is **trusted local code/media tooling**, not an internet-facing arbitrary
code execution service. Do not expose it to untrusted users without a separate
sandbox, authentication, quotas and reviewed scene/critic code.

The HTTP API cannot upload code, choose arbitrary scenes/critics/files, or
submit audio paths. It accepts only numeric render dimensions/FPS/duration.
Jobs are serialized and resource-bounded (2–900 frames, dimensions <=1920×1080,
FPS <=60, <=30 seconds, even output dimensions). One active job per server.
The scene's browser has external network disabled. Local imports/assets are
limited to project `scenes/`, `assets/`, and `quality/` routes. This is not a
security sandbox for hostile scene JavaScript or Node critic modules.

## Architecture

```text
Studio UI / trusted CLI
          |
          v
 validate config -> explicit frame clock -> Chromium Canvas
          |                                  |
          |                        lossless PNG + SHA-256
          |                                  |
          |                  structural gate + optional critic
          |                          |              |
          |                        pass       revision/patch retry
          |                          |         finite, then fail
          +---------------------- FFmpeg ------------------+
                                    |
                              MP4 + manifest
```

In-browser `Date.now`, default `Date`, `performance.now`, and seeded
`Math.random` are pinned to the requested frame. Module-load defaults are
also fixed. Scene code must remain a deterministic function of frame inputs;
other APIs/external state can still defeat determinism and are not magically
made safe. Rendering starts from a reset context each frame. CSS/DOM animations
are rejected in the capture page; output must be frame-painted Canvas.
Frames are at `time = frame/fps`, with `0 <= frame < frameCount`. The last
captured timestamp is `duration - 1/fps`, not a duplicated terminal frame.
The encoded duration is exactly `frameCount/fps`.

## Proposed v1 integration contract (awaiting Leonidas's reply)

Sent in DMs `64fe672a` and `c0594cc8`; do not present it as an agreed interface.
No Leonidas-owned files have been edited.

```js
// Trusted browser module under scenes/; imports can be relative.
export async function render(ctx, {
  frame, time, duration, fps, width, height,
  revision, beatMap, patch
}) {
  // Explicitly paint ALL pixels using ctx (CanvasRenderingContext2D).
  // revision is 0 initially, then bounded retries; patch comes from critic.
  return { intentionalHold: false }; // true only for a deliberate held frame
}

// Optional trusted Node module, supplied through CLI --critic PATH.
export async function analyze({
  imagePath, frame, time, beatMap, metrics, revision
}) {
  // Return REAL assessed evidence. Never manufacture a passing taste score.
  return { score: actualScore, issues: actualIssues, patch: optionalJSONPatch };
}
```

`beatMap` is `{ beats: [seconds...], cuts: [seconds...] }`, ascending, finite,
within the film duration. It is passed through; **M1 does not assert beat/cut
alignment**. Leonidas's later spring/audio/semantic modules can use the seam.
CLI `--audio PATH` muxes audio; shorter audio is padded rather than shortening
the video. Audio muxing is tested with a generated fixture tone, not mistaken
for beat synchronization. CLI `--critic PATH` executes trusted Node code.

## What the structural gate measures

The PNG's dimensions, opacity, luminance contrast, detail/entropy and change
from the previous accepted frame are checked. **Every check is mandatory**;
failed frames stop export after `maxAttempts` (default 2, maximum 4).
An explicit intentional hold bypasses only the temporal dead-frame check.
This declaration is auditable metadata, not proof that a hold is interesting.

Five engineering checks produce a 0–10 structural score. A complete structural
pass scores 10. The optional critic must independently score >=8 (configurable
up to 10). Missing critic => `semanticProvider: "not-provided"` and export
status `structural-pass`; a supplied, passing critic yields `provider-approved`,
not a human artistic verdict. Low semantic scores cannot be erased by a high
structural score. Blank frames cannot pass by collecting unrelated points.

Manifests retain frame timestamps, every attempt, issues, metrics, PNG hashes,
accepted verdicts, measured improvement counts, scene hash, browser/Node/
FFmpeg versions, final video hash, error/cancellation state and real finish
time. Retry count is not automatically an improvement. Failures never get an
approved video status. Completed jobs recover from their local manifests on
server restart. Generated runs live in ignored `renders/`; explicit evidence
samples below are committed for review.

## Evidence from this runtime

- [15/15 unit + real browser/FFmpeg integration tests](evidence/tests.txt),
  including two independent render runs with identical per-frame hashes,
  deliberate blank rejection, revision-based improvements, critic rejection,
  cancellation and audio mux/decode.
- [Browser UI smoke](evidence/browser-smoke.json): 48/48 accepted frames in a
  real UI-triggered export, no browser page errors, desktop 1440×1100 and mobile
  390×844 checked, no mobile horizontal overflow, working 100-byte HTTP range
  response (206).
- [Actual 2-second, 24-FPS sample MP4](evidence/sample.mp4).
- [Sample manifest](evidence/sample-manifest.json), with all 48 frame hashes.
- [First captured frame](evidence/first-frame.png) and
  [last captured frame](evidence/last-frame.png).

Sample passes structural checks only, with semantic review not provided. It
has no soundtrack. Server job APIs use relative URLs, so preview browsers
never attempt to call their own localhost. Live preview assets are local.

## Ownership and handoff

Achilles: `engine/`, `server.mjs`, `ui/`, calibration fixtures, infrastructure
tests and documentation. Leonidas: actual production `quality/` and artistic
scene modules, spring dynamics, beat synchronization and semantic critique.
The calibration scene is intentionally distinct from his production assets.
Bus plan `57ad7f79`; infrastructure milestone `10dec92a`. The unresolved
reference access and the proposed seam were reported to Pericles, not hidden.

Next independent infrastructure job: verify stored manifest/frame/video hashes
and detect drift/tampering without running the renderer. This does not consume
Leonidas's output-quality lane.

---

## M2 — output quality lane (Leonidas, t-20261013-0bd4)

Stacked on M1 above; interface agreed with Achilles in DMs
`64fe672a`/`9943becb`. What M2 adds, under `quality/` and `scenes/`:

| module | what it does |
|---|---|
| `quality/spring.mjs` | Damped-spring integration at a fixed 1/240 s substep. `springAt(params, time)` is a deterministic function — underdamped springs visibly overshoot, then settle. No linear tweens exist in this lane. |
| `quality/beat.mjs` | `makeBeatMap({bpm, duration, cutEveryBeats})` — every cut is a beat by construction, so beat-locking is provable (`validateCuts`), not eyeballed. |
| `quality/critic.mjs` | Node critic for the engine's `analyze({imagePath, frame, time, beatMap, metrics, revision})` seam. Scores measurable evidence (palette, edge detail, contrast, content coverage, beat-motion) and returns a `patch.emphasis` that grows per revision, so a re-render is a different frame, not a repeat. |
| `quality/lint.mjs` | Source gate banning the slop patterns: linear easing, gradient fills, CSS animation, and animating without springs. |
| `scenes/spring-demo.mjs` | Four-section demo (sun/skyline, equalizer, assets, logo) — composition changes only on beat cuts, all motion from springs, honors critic patches. |

**Honesty box.** The critic is a formula over measurable evidence,
calibrated against M1's own accepted evidence frames (score 8.4–8.5)
versus a blank frame (~0). It is not a taste model. Two gates bit
during integration and both were fixed in the *scene*, not by
weakening the gate: the near-empty original opener, and sparse
first frames at the section cuts. A component that cannot be
measured (frame 0 has no predecessor to diff) is excluded and the
rest rescaled — the same convention as M1's structural gate.

**Verified this session** (Node 20, Playwright chromium, system ffmpeg):

```bash
npm test            # 21/21 (15 M1 + 6 M2)
node engine/cli.mjs --out renders/spring-demo --duration 4 --fps 24 \
  --width 640 --height 360 --scene scenes/spring-demo.mjs \
  --critic quality/critic.mjs
# -> {"status":"provider-approved","frames":96,...}
#    96/96 frames accepted, 4 frames improved on critic re-render
#    (frames 1, 49, 51, 73), film.mp4 = H.264 640x360, 4.000 s
```

Evidence: `evidence/m2-spring-demo.mp4`, `evidence/m2-spring-frame80.png`,
`evidence/m2-spring-manifest.json`. The TikTok reference videos still
return HTTP 403 from this runtime and were not watched or transcribed.
