/* platformer — engine loop + rendering (task t-20261011-1ec9, epic t-20261011-a629).
   Interface contract: bus message #c5108692.
     units px + seconds, y grows DOWN
     state  = {scene: "title"|"play"|"won"|"lost", score, time}
     player = {x, y, w, h, vx, vy, onGround, jumpHeld, coyoteMs}
     input  = {left, right, jump, jumpPressed}
     level  = {platforms:[{x,y,w,h}], goal:{x,y,w,h}, hazards:[{x,y,w,h}]}
   step(state, player, level, input, dt) mutates in place; render(ctx, ...) is read-only.

   OWNERSHIP: the stepPhysics() section was implemented by t-20261011-d4e3
   (gravity/terminal velocity, accel + friction, coyote time, sub-stepped
   AABB collision). Level data, scene/score/restart rules belong to
   t-20261011-b220 (levels.js + the marked sections in this file). */
"use strict";
(function () {
  /* level data lives in levels.js — this file never defines a level.
     Scene/level/score/restart rules are t-20261011-b220's. */
  var LEVELS = (typeof module !== "undefined" && module.exports)
    ? require("./levels.js")
    : window.PLATFORMER_LEVELS;
  var LEVEL_1 = LEVELS.LEVEL_1;

  var STEP = 1 / 60;        // fixed simulation step (s)
  var MAX_STEPS = 5;        // catch-up cap per animation frame
  var MAX_FRAME = 0.25;     // clamp on frame delta (throttled tabs)

  /* ---- physics section (implemented by t-20261011-d4e3) ----
   Gravity + terminal velocity; horizontal acceleration with friction and
   reduced air control; jump has COYOTE TIME (100 ms grace after leaving the
   ground) — the one jump-feel mechanic this build ships. The epic needs >= 1;
   why a release-cut was deliberately NOT shipped is documented in README.md
   ("Physics") — it measurably breaks test-level.js's bot. Evidence: bus.
   AABB collision resolves per axis in substeps of <= 6 px so nothing can
   tunnel. Contract: bus #c5108692. RUN_V/JUMP_V/GRAV keep the stub's exact
   top speed and jump arc, which LEVEL_1 and test-level.js are measured
   against (~113 px jump height, ~170 px distance) — do not retune. */
  var GRAV = 1800;          // px/s^2
  var TERM_V = 900;         // px/s terminal fall speed
  var RUN_V = 240;          // px/s target run speed (stub's MOVE, unchanged)
  var ACCEL_GROUND = 1600;  // px/s^2 toward target while grounded
  var ACCEL_AIR = 800;      // px/s^2 toward target while airborne (reduced)
  var FRICTION = 2200;      // px/s^2 toward 0 when grounded with no input
  var JUMP_V = -640;        // px/s (negative = up)
  var COYOTE_MS = 100;      // ms of jump grace after leaving the ground
  var SUBSTEP_PX = 6;       // max px moved per collision pass (no tunnelling)

  function overlaps(ax, ay, aw, ah, b) {
    return ax < b.x + b.w && ax + aw > b.x && ay < b.y + b.h && ay + ah > b.y;
  }

  function collideX(player, level) {
    for (var i = 0; i < level.platforms.length; i++) {
      var p = level.platforms[i];
      if (overlaps(player.x, player.y, player.w, player.h, p)) {
        if (player.vx > 0) { player.x = p.x - player.w; }
        else if (player.vx < 0) { player.x = p.x + p.w; }
        player.vx = 0;                       // side-block
      }
    }
  }

  function collideY(player, level) {
    player.onGround = false;
    for (var i = 0; i < level.platforms.length; i++) {
      var p = level.platforms[i];
      if (overlaps(player.x, player.y, player.w, player.h, p)) {
        if (player.vy > 0) {                 // landing: snap on top
          player.y = p.y - player.h;
          player.vy = 0;
          player.onGround = true;
        } else if (player.vy < 0) {          // head-bump
          player.y = p.y + p.h;
          player.vy = 0;
        }
      }
    }
  }

  function approach(v, target, delta) {
    if (v < target) { v += delta; if (v > target) { v = target; } }
    else if (v > target) { v -= delta; if (v < target) { v = target; } }
    return v;
  }

  function stepPhysics(player, level, input, dt) {
    /* horizontal: accelerate toward the target speed, friction when idle */
    var target = 0;
    if (input.left)  { target -= RUN_V; }
    if (input.right) { target += RUN_V; }
    if (target === 0 && player.onGround) {
      player.vx = approach(player.vx, 0, FRICTION * dt);
    } else {
      player.vx = approach(player.vx, target,
                           (player.onGround ? ACCEL_GROUND : ACCEL_AIR) * dt);
    }

    /* coyote time: full while grounded, decays in the air */
    if (player.onGround) { player.coyoteMs = COYOTE_MS; }
    else { player.coyoteMs = Math.max(0, player.coyoteMs - dt * 1000); }

    /* jump: on the ground OR inside the coyote window after leaving it */
    if (input.jumpPressed && (player.onGround || player.coyoteMs > 0)) {
      player.vy = JUMP_V;
      player.onGround = false;
      player.coyoteMs = 0;
    }
    player.jumpHeld = input.jump;   /* bookkept for the contract shape */

    /* gravity + terminal velocity */
    player.vy += GRAV * dt;
    if (player.vy > TERM_V) { player.vy = TERM_V; }

    /* integrate in substeps of <= SUBSTEP_PX using LIVE velocities, so the
       step where a collision zeroes a velocity also stops further movement
       (precomputed moves would keep pushing into the floor after a snap) */
    var n = Math.max(1, Math.ceil(Math.max(Math.abs(player.vx), Math.abs(player.vy)) * dt / SUBSTEP_PX));
    var subDt = dt / n;
    for (var s = 0; s < n; s++) {
      player.x += player.vx * subDt;
      collideX(player, level);
      player.y += player.vy * subDt;
      collideY(player, level);
    }

    /* grounded probe: resting exactly on a platform top counts as grounded,
       so standing is stable (strict overlap alone flickers after the snap) */
    player.onGround = false;
    for (var g = 0; g < level.platforms.length; g++) {
      var gp = level.platforms[g];
      if (player.x < gp.x + gp.w && player.x + player.w > gp.x &&
          player.y + player.h >= gp.y && player.y + player.h <= gp.y + 0.01) {
        player.onGround = true;
      }
    }

    /* world safety net (same as the stub's) */
    if (player.x < 0) { player.x = 0; player.vx = 0; }
    if (player.x > 960 - player.w) { player.x = 960 - player.w; player.vx = 0; }
    if (player.y > 540 + 200) { player.y = 300; player.x = 40; player.vy = 0; }
  }
  /* ---- end physics section ---- */

  var SPAWN_X = 40, SPAWN_Y = 460;

  function createPlayer() {
    return { x: SPAWN_X, y: SPAWN_Y, w: 28, h: 36,
             vx: 0, vy: 0, onGround: false, jumpHeld: false, coyoteMs: 0 };
  }
  function resetPlayer(player) {
    player.x = SPAWN_X; player.y = SPAWN_Y;
    player.vx = 0; player.vy = 0; player.onGround = false;
    player.jumpHeld = false; player.coyoteMs = 0;
  }
  function createState() {
    /* collected: indices into level.pickups that this run has taken. The
       authored level object is never mutated, which is what makes restart
       trivially correct — there is nothing to un-take. */
    return { scene: "title", score: 0, time: 0, collected: [] };
  }
  /* Full reset, in place: every field a run can touch goes back to new-game
     values. Adding a field to createState() means adding it here too — the
     deterministic-restart test in test-level.js catches it if you forget. */
  function restart(state, player) {
    state.scene = "title";
    state.score = 0;
    state.time = 0;
    state.collected.length = 0;
    resetPlayer(player);
  }
  function createInput() {
    return { left: false, right: false, jump: false, jumpPressed: false, restart: false };
  }

  var PICKUP_POINTS = 10;   /* each pickup */
  var FINISH_BONUS = 50;    /* reaching the goal */

  /* one simulation tick: scene, level and score rules (t-20261011-b220). */
  function step(state, player, level, input, dt) {
    if (input.restart) {                 /* R, or the restart input, any scene */
      restart(state, player);
      input.restart = false;
      if (!input.jumpPressed) { input.jumpPressed = false; }
      return;
    }
    if (state.scene === "title") {
      if (input.jumpPressed) {
        state.scene = "play";
        state.time = 0;
        state.score = 0;
        state.collected.length = 0;
      }
    } else if (state.scene === "play") {
      state.time += dt;
      stepPhysics(player, level, input, dt);
      var i, pickups = level.pickups || [];
      for (i = 0; i < pickups.length; i += 1) {
        if (state.collected.indexOf(i) !== -1) { continue; }
        if (overlaps(player.x, player.y, player.w, player.h, pickups[i])) {
          state.collected.push(i);
          state.score += PICKUP_POINTS;
        }
      }
      for (i = 0; i < level.hazards.length; i += 1) {
        if (overlaps(player.x, player.y, player.w, player.h, level.hazards[i])) {
          state.scene = "lost";        /* the run ends; restart is one key */
          state.time = state.time;     /* keep the clock for the loss screen */
        }
      }
      /* win only if the goal is touched first — a hazard frame cannot win */
      if (state.scene === "play"
          && overlaps(player.x, player.y, player.w, player.h, level.goal)) {
        state.scene = "won";
        state.score += FINISH_BONUS;
      }
    } else { /* won | lost */
      if (input.jumpPressed) {
        restart(state, player);        /* back to title, nothing left behind */
      }
    }
    input.jumpPressed = false; /* edge-trigger: consumed each tick */
  }

  /* ---- rendering (read-only; colors hoisted to avoid per-frame churn) ---- */
  var C_BG = "#1d232c", C_PLATFORM = "#4a5568", C_PLAYER = "#e0b34a",
      C_GOAL = "#69b578", C_HAZARD = "#c05a5a", C_PICKUP = "#7fd1e0", C_TEXT = "#e8e6e1",
      C_TEXT_DIM = "#9aa5b1";

  function render(ctx, state, player, level) {
    var i, p;
    ctx.fillStyle = C_BG;
    ctx.fillRect(0, 0, 960, 540);

    ctx.fillStyle = C_PLATFORM;
    for (i = 0; i < level.platforms.length; i++) {
      p = level.platforms[i];
      ctx.fillRect(p.x, p.y, p.w, p.h);
    }
    ctx.fillStyle = C_HAZARD;
    for (i = 0; i < level.hazards.length; i++) {
      p = level.hazards[i];
      ctx.fillRect(p.x, p.y, p.w, p.h);
    }
    var pickups = level.pickups || [];
    for (i = 0; i < pickups.length; i += 1) {
      if (state.collected.indexOf(i) !== -1) { continue; }
      ctx.fillStyle = C_PICKUP;
      ctx.fillRect(pickups[i].x, pickups[i].y, pickups[i].w, pickups[i].h);
    }
    /* goal flag: pole + waving triangle */
    p = level.goal;
    ctx.fillStyle = C_GOAL;
    ctx.fillRect(p.x, p.y, 4, p.h);
    ctx.beginPath();
    ctx.moveTo(p.x + 4, p.y);
    ctx.lineTo(p.x + 4 + 18, p.y + 8);
    ctx.lineTo(p.x + 4, p.y + 16);
    ctx.closePath();
    ctx.fill();

    if (state.scene !== "title") {
      ctx.fillStyle = C_PLAYER;
      ctx.fillRect(player.x, player.y, player.w, player.h);
    }

    ctx.textAlign = "center";
    if (state.scene === "title") {
      ctx.fillStyle = C_TEXT;
      ctx.font = "bold 42px system-ui, sans-serif";
      ctx.fillText("PLATFORMER", 480, 240);
      ctx.font = "18px system-ui, sans-serif";
      ctx.fillStyle = C_TEXT_DIM;
      ctx.fillText("press enter or space to start", 480, 276);
    } else if (state.scene === "won") {
      ctx.fillStyle = C_GOAL;
      ctx.font = "bold 42px system-ui, sans-serif";
      ctx.fillText("YOU WIN", 480, 240);
      ctx.font = "18px system-ui, sans-serif";
      ctx.fillStyle = C_TEXT_DIM;
      ctx.fillText("score " + state.score + " in " + state.time.toFixed(1)
                   + "s — space or R to play again", 480, 276);
    } else if (state.scene === "lost") {
      ctx.fillStyle = C_HAZARD;
      ctx.font = "bold 42px system-ui, sans-serif";
      ctx.fillText("OUCH", 480, 240);
      ctx.font = "18px system-ui, sans-serif";
      ctx.fillStyle = C_TEXT_DIM;
      ctx.fillText("hit a hazard on the rooftops — space or R to try again", 480, 276);
    } else {
      ctx.textAlign = "left";
      ctx.font = "14px system-ui, sans-serif";
      ctx.fillStyle = C_TEXT_DIM;
      ctx.fillText("score " + state.score + " · " + state.time.toFixed(1) + "s · "
                   + state.collected.length + "/" + (level.pickups || []).length
                   + " pickups · R restarts", 12, 24);
    }
  }

  /* ---- frame driver ---- */
  function start() {
    var canvas = document.getElementById("game");
    var ctx = canvas.getContext("2d");
    var state = createState();
    var player = createPlayer();
    var level = LEVEL_1;
    var input = createInput();
    var accumulator = 0;
    var last = -1;

    var KEYMAP = { KeyR: "restart", ArrowLeft: "left", KeyA: "left",
                   ArrowRight: "right", KeyD: "right",
                   ArrowUp: "jump", KeyW: "jump", Space: "jump", Enter: "jump" };
    window.addEventListener("keydown", function (e) {
      var k = KEYMAP[e.code];
      if (!k) { return; }
      e.preventDefault();
      if (k === "restart") {
        if (!e.repeat) { input.restart = true; }
      } else if (k === "jump" && !e.repeat) {
        if (!input.jump) { input.jumpPressed = true; }
        input.jump = true;
      } else if (k !== "jump") {
        input[k] = true;
      }
    });
    window.addEventListener("keyup", function (e) {
      var k = KEYMAP[e.code];
      if (!k || k === "restart") { return; }
      if (k === "jump") { input.jump = false; }
      else { input[k] = false; }
    });

    function frame(now) {
      if (last < 0) { last = now; }
      var dt = (now - last) / 1000;
      last = now;
      if (dt > MAX_FRAME) { dt = MAX_FRAME; }
      accumulator += dt;
      var steps = 0;
      while (accumulator >= STEP && steps < MAX_STEPS) {
        step(state, player, level, input, STEP);
        accumulator -= STEP;
        steps += 1;
      }
      if (steps === MAX_STEPS) { accumulator = 0; } /* drop the backlog, stay stable */
      render(ctx, state, player, level);
      requestAnimationFrame(frame);
    }
    canvas.focus();
    requestAnimationFrame(frame);
  }

  var isNodeTest = (typeof module !== "undefined" && module.exports);
  if (!isNodeTest && typeof document !== "undefined") { start(); }
  if (isNodeTest) {
    module.exports = {
      STEP: STEP, MAX_STEPS: MAX_STEPS, MAX_FRAME: MAX_FRAME,
      LEVELS: LEVELS, LEVEL_1: LEVEL_1,
      PICKUP_POINTS: PICKUP_POINTS, FINISH_BONUS: FINISH_BONUS,
      createState: createState, createPlayer: createPlayer,
      resetPlayer: resetPlayer, restart: restart, createInput: createInput,
      step: step, stepPhysics: stepPhysics
    };
  }
})();
