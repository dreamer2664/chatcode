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

## Level and scenes (t-20261011-b220)

`levels.js` holds the real level (`LEVEL_1`, "Rooftops": 6 platforms, 3
hazards, 4 pickups, goal flag) and the format is documented under *Level
format* below. `game.js` owns the scene rules — title/play/won/lost, pickups
and score, the finish bonus, and `restart()`, which `R` triggers from any
scene. The level object is never mutated: a run's collected pickups live in
`state.collected`, so restarting needs nothing undone.

The physics inside `game.js` is still a working stub (gravity, move, one jump
mode, AABB collision) in the marked section owned by `t-20261011-d4e3`.

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
