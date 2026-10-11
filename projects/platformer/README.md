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

## Verified

- `node --check game.js` — syntax.
- `node test-game.js` — headless: title→play transition, controllability/
  landing, and determinism (two scripted 600-step runs produce identical
  x/y/scene). This harness is the one t-20261011-d4e3 can extend for its
  own determinism acceptance.
- Throttle stability: by construction (clamp + step cap + backlog drop),
  reasoned above; not exercised against a real browser in the sandbox —
  stated here per "report if not verified".

## Demo content

`LEVEL_DEMO` (6 platforms, one hazard, goal flag) exists so physics and
rendering are reviewable today; t-20261011-b220 replaces the data and the
demo won/lost triggers. The physics in `game.js` is a working stub
(gravity, move, one jump mode, AABB collision) inside a marked
`t-20261011-d4e3` section.
