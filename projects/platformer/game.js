/* platformer — engine loop + rendering (task t-20261011-1ec9, epic t-20261011-a629).
   Interface contract: bus message #c5108692.
     units px + seconds, y grows DOWN
     state  = {scene: "title"|"play"|"won"|"lost", score, time}
     player = {x, y, w, h, vx, vy, onGround, jumpHeld, coyoteMs}
     input  = {left, right, jump, jumpPressed}
     level  = {platforms:[{x,y,w,h}], goal:{x,y,w,h}, hazards:[{x,y,w,h}]}
   step(state, player, level, input, dt) mutates in place; render(ctx, ...) is read-only.

   OWNERSHIP: the stepPhysics() section is a working STUB so the game plays
   today — t-20261011-d4e3 owns gravity/jump/collision refinement. The demo
   level and won/lost triggers belong to t-20261011-b220. */
"use strict";
(function () {
  var STEP = 1 / 60;        // fixed simulation step (s)
  var MAX_STEPS = 5;        // catch-up cap per animation frame
  var MAX_FRAME = 0.25;     // clamp on frame delta (throttled tabs)

  /* ---- physics section (STUB — owned by t-20261011-d4e3) ---- */
  var GRAV = 1800;          // px/s^2
  var MOVE = 240;           // px/s
  var JUMP_V = -640;        // px/s (negative = up)
  var TERM_V = 900;         // terminal fall speed

  function overlaps(ax, ay, aw, ah, b) {
    return ax < b.x + b.w && ax + aw > b.x && ay < b.y + b.h && ay + ah > b.y;
  }

  function collideX(player, level) {
    for (var i = 0; i < level.platforms.length; i++) {
      var p = level.platforms[i];
      if (overlaps(player.x, player.y, player.w, player.h, p)) {
        player.x = (player.vx > 0) ? p.x - player.w : p.x + p.w;
        player.vx = 0;
      }
    }
  }

  function collideY(player, level) {
    player.onGround = false;
    for (var i = 0; i < level.platforms.length; i++) {
      var p = level.platforms[i];
      if (overlaps(player.x, player.y, player.w, player.h, p)) {
        if (player.vy > 0) {
          player.y = p.y - player.h;
          player.onGround = true;
        } else if (player.vy < 0) {
          player.y = p.y + p.h;
        }
        player.vy = 0;
      }
    }
  }

  function stepPhysics(player, level, input, dt) {
    player.vx = 0;
    if (input.left)  { player.vx = -MOVE; }
    if (input.right) { player.vx += MOVE; }

    if (input.jumpPressed && player.onGround) {
      player.vy = JUMP_V;
    }
    player.jumpHeld = input.jump;

    player.vy += GRAV * dt;
    if (player.vy > TERM_V) { player.vy = TERM_V; }

    player.x += player.vx * dt;
    collideX(player, level);
    player.y += player.vy * dt;
    collideY(player, level);

    if (player.x < 0) { player.x = 0; }
    if (player.x > 960 - player.w) { player.x = 960 - player.w; }
    if (player.y > 540 + 200) { player.y = 300; player.x = 40; player.vy = 0; }
  }
  /* ---- end physics section ---- */

  /* demo level: real data is t-20261011-b220's; format is final (contract). */
  var LEVEL_DEMO = {
    platforms: [
      { x: 0,   y: 520, w: 960, h: 40 },
      { x: 120, y: 440, w: 140, h: 18 },
      { x: 320, y: 380, w: 120, h: 18 },
      { x: 500, y: 320, w: 120, h: 18 },
      { x: 680, y: 260, w: 120, h: 18 },
      { x: 820, y: 190, w: 120, h: 18 }
    ],
    goal:    { x: 862, y: 130, w: 22, h: 60 },
    hazards: [ { x: 560, y: 502, w: 60, h: 18 } ]
  };

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
  function createState() { return { scene: "title", score: 0, time: 0 }; }
  function createInput() { return { left: false, right: false, jump: false, jumpPressed: false }; }

  /* one simulation tick; scene transitions here are DEMO versions —
     full win/lose/restart rules belong to t-20261011-b220. */
  function step(state, player, level, input, dt) {
    if (state.scene === "title") {
      if (input.jumpPressed) {
        state.scene = "play";
        state.time = 0; state.score = 0;
      }
    } else if (state.scene === "play") {
      state.time += dt;
      stepPhysics(player, level, input, dt);
      var i;
      for (i = 0; i < level.hazards.length; i++) {
        if (overlaps(player.x, player.y, player.w, player.h, level.hazards[i])) {
          state.scene = "lost";
        }
      }
      if (overlaps(player.x, player.y, player.w, player.h, level.goal)) {
        state.scene = "won";
        state.score += 1;
      }
    } else { /* won | lost */
      if (input.jumpPressed) {
        resetPlayer(player);
        state.scene = "title";
      }
    }
    input.jumpPressed = false; /* edge-trigger: consumed each tick */
  }

  /* ---- rendering (read-only; colors hoisted to avoid per-frame churn) ---- */
  var C_BG = "#1d232c", C_PLATFORM = "#4a5568", C_PLAYER = "#e0b34a",
      C_GOAL = "#69b578", C_HAZARD = "#c05a5a", C_TEXT = "#e8e6e1",
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
      ctx.fillText("space to return to title", 480, 276);
    } else if (state.scene === "lost") {
      ctx.fillStyle = C_HAZARD;
      ctx.font = "bold 42px system-ui, sans-serif";
      ctx.fillText("OUCH", 480, 240);
      ctx.font = "18px system-ui, sans-serif";
      ctx.fillStyle = C_TEXT_DIM;
      ctx.fillText("space to return to title", 480, 276);
    } else {
      ctx.textAlign = "left";
      ctx.font = "14px system-ui, sans-serif";
      ctx.fillStyle = C_TEXT_DIM;
      ctx.fillText("score " + state.score + " · " + state.time.toFixed(1) + "s", 12, 24);
    }
  }

  /* ---- frame driver ---- */
  function start() {
    var canvas = document.getElementById("game");
    var ctx = canvas.getContext("2d");
    var state = createState();
    var player = createPlayer();
    var level = LEVEL_DEMO;
    var input = createInput();
    var accumulator = 0;
    var last = -1;

    var KEYMAP = { ArrowLeft: "left", KeyA: "left",
                   ArrowRight: "right", KeyD: "right",
                   ArrowUp: "jump", KeyW: "jump", Space: "jump", Enter: "jump" };
    window.addEventListener("keydown", function (e) {
      var k = KEYMAP[e.code];
      if (!k) { return; }
      e.preventDefault();
      if (k === "jump" && !e.repeat) {
        if (!input.jump) { input.jumpPressed = true; }
        input.jump = true;
      } else if (k !== "jump") {
        input[k] = true;
      }
    });
    window.addEventListener("keyup", function (e) {
      var k = KEYMAP[e.code];
      if (!k) { return; }
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
      LEVEL_DEMO: LEVEL_DEMO,
      createState: createState, createPlayer: createPlayer,
      resetPlayer: resetPlayer, createInput: createInput,
      step: step, stepPhysics: stepPhysics
    };
  }
})();
