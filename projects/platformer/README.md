# Platformer (demo build)

A small canvas platformer with no libraries and no network. Part of epic
t-20261011-a629. Engine slice (loop + input + render) by barry
(t-20261011-1ec9); physics refinement is t-20261011-d4e3's, level/score/
win-lose is t-20261011-b220's.

## How to play

Open `index.html` — from `file://` directly, no server needed (the game has
no fetches at all). Move with arrows or `A`/`D`, jump with `space` or `W`,
start/restart with `enter` or `space`.

## The loop contract (bus #c5108692)

- Fixed timestep: `STEP = 1/60 s`, accumulator pattern, at most
  `MAX_STEPS = 5` catch-up steps per animation frame.
- Frame delta is clamped to `MAX_FRAME = 0.25 s`. A throttled/backgrounded
  tab stops getting `requestAnimationFrame` callbacks; when it comes back,
  the clamp plus the step cap mean the simulation does at most ~5 steps and
  **drops the backlog** (`accumulator = 0` after the cap) instead of
  spiral-of-death fast-forwarding. Simulation stays stable; only wall-clock
  positioning is lost.
- `step(state, player, level, input, dt)` is the only place simulation
  happens. `render(ctx, ...)` is read-only.
- Edge inputs: `jumpPressed` is set on a fresh keydown and consumed at the
  end of every `step`, so one press = one jump regardless of frame rate.

## No per-frame garbage

State, player, input and level objects are created once and mutated in
place; the loop never allocates objects or arrays. Reported honestly: the
HUD does one string conversion per drawn frame (`state.time.toFixed(1)`),
which is inherent to `fillText`; everything else is churn-free.

## Physics (t-20261011-d4e3)

The section between `/* ---- physics section ... */` and
`/* ---- end physics section ---- */` in `game.js` is the full physics.

Jump feel — the epic requires at least one of coyote time or variable jump
height; this build ships **coyote time (100 ms)** and deliberately NOT a
release-cut:

- **Coyote time:** `player.coyoteMs` is topped up to 100 while grounded and
  decays in the air; a jump pressed within the window after walking off a
  ledge still fires. Verified by the behavior test.
- **Why no release-cut (variable jump height):** the bot in `test-level.js`
  releases the jump key one frame after takeoff (its trigger turns off as
  soon as the player leaves the ground), and `LEVEL_1` is measured against
  the full stub arc (~113 px high, ~170 px long). A release-cut shrinks that
  arc and the bot can no longer win. Measured, not assumed: with a 0.45
  cut implemented, `node test-level.js` fails
  ("the bot never reached the goal in 60s (scene=lost)"); without it, all
  checks pass and the bot wins in ~3.8s. Since the epic needs only one
  mechanic, coyote time is the one shipped.

Movement constants (px + seconds, y-down). `RUN_V`, `JUMP_V`, `GRAV`,
`TERM_V` are the stub's exact values on purpose — `LEVEL_1` and
`test-level.js` are measured against them, so do not retune:

| constant | value | meaning |
|---|---|---|
| `GRAV` | 1800 px/s² | gravity |
| `TERM_V` | 900 px/s | terminal fall speed |
| `RUN_V` | 240 px/s | target run speed (the stub's `MOVE`) |
| `ACCEL_GROUND` / `ACCEL_AIR` | 1600 / 800 px/s² | reduced air control |
| `FRICTION` | 2200 px/s² | decel toward 0 when grounded, no input |
| `JUMP_V` | −640 px/s | launch speed |
| `COYOTE_MS` | 100 | grace window after leaving ground |
| `SUBSTEP_PX` | 6 | max px moved per collision pass |

Collision: AABB resolved per axis — landing (snap on top, `onGround`),
head-bump (snap below, `vy = 0`), side-block (snap flush, `vx = 0`).

No tunnelling: each step integrates in substeps of at most `SUBSTEP_PX`
using live velocities (a collision that zeroes a velocity also stops the
remaining movement that step). Worst case is terminal velocity:
900 px/s × 1/60 s = 15 px per step → 3 substeps of 5 px, well under the
thinnest platform in `LEVEL_1` (the 16 px roofs), so a fast fall cannot
skip geometry. Verified by the behavior test.

Stable standing: after the snap, the box touches the platform exactly and
strict overlap flickers, so an end-of-step ground probe (resting within
0.01 px on a platform top) sets `onGround`. Position and grounded flag are
constant for 120+ consecutive idle steps — no jitter.

Frame-rate independence: physics is driven only by the fixed `STEP` through
`step()`; the accumulator/catch-up in the loop contract above is the only
clock. Physics never sees wall-clock time.

## Verified

- `node --check game.js` — syntax.
- `node test-game.js` — barry's engine harness: full story
  (title→play→lost→title) plus two byte-identical 600-step runs; green
  against this physics.
- `node test-level.js` — scott's level/score/restart suite incl. the
  winning bot; green against this physics (win ~3.8s vs 3.7s on the stub —
  the accel ramp, nothing else).
- `node physics_behavior_test.js` — t-d4e3's 7 checks, all PASS: stable
  standing, tuned jump arc (~113px), coyote jump after walking off the
  step, no tunnelling at terminal speed onto a 16 px roof, head-bump,
  side-block, friction-to-stop.
- `node physics_determinism.js` — the t-d4e3 acceptance harness: 600 fixed
  steps with scripted input, prints the final x/y. Run twice:

      after 600 fixed steps: x=0 y=484 vx=0 vy=0 onGround=true scene=play

  Byte-identical across runs (compared with `a=$(node ...); b=$(node ...); [ "$a" = "$b" ]`).
- Throttle stability: by construction (clamp + step cap + backlog drop),
  reasoned above; not exercised against a real browser in the sandbox —
  stated here per "report if not verified".

## Level and scenes (t-20261011-b220)

`levels.js` holds the real level (`LEVEL_1`, "Rooftops": 6 platforms, 3
hazards, 4 pickups, goal flag) and the format is documented under *Level
format* below. `game.js` owns the scene rules — title/play/won/lost, pickups
and score, the finish bonus, and `restart()`, which `R` triggers from any
scene. The level object is never mutated: a run's collected pickups live in
`state.collected`, so restarting needs nothing undone.

The physics inside `game.js` was implemented by `t-20261011-d4e3` in the
marked section — see *Physics* below.

## Level format (t-20261011-b220)

Levels are **data**, not code: `levels.js` exports them and `game.js` never
defines one. Adding a level means adding an object — no physics or scene change:

```js
{
  name:      "Rooftops",                       // for humans
  platforms: [{ x, y, w, h }],                 // solids: ground, steps, walls
  hazards:   [{ x, y, w, h }],                 // touching one loses the run
  pickups:   [{ x, y, w, h }],                 // 10 points each; optional
  goal:      { x, y, w, h }                    // touching it wins the run
}
```

Coordinates are pixels with the origin at the top-left and **y growing down**;
the view is 960×540. Every rect is `{x, y, w, h}` with `x`/`y` at the top-left
corner. A platform that reaches the ground (`y + h === 520`) is a wall you
cannot run through, which is how the climb in `LEVEL_1` is forced.

Rules of thumb the shipped level follows, measured against the physics:
a jump lifts the player about **113px** and carries them about **170px**, so
rises stay ≤ 80px and gaps ≤ 50px. Hazards are 32px wide, and each leaves at
least 16px of landing room past its far edge, because the last few pixels of
the jump arc are what actually pass over it. Score is 10 per pickup plus 50 for
finishing; `R` restarts from anywhere and resets everything.

`node test-level.js` plays the level with a bot (hold right; jump at hazards
and walls), and fails if the level cannot be won inside 60 seconds, if a loss
cannot be reached and recovered from, if two restarts differ, or if the
authored level object is mutated by play. Edit the data, run it, and it will
tell you whether the level is still playable.
