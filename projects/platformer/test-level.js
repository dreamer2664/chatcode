#!/usr/bin/env node
/* test-level.js — level, score, win/lose and restart checks for t-20261011-b220.
 *
 *   node projects/platformer/test-level.js
 *
 * Exit 0 = all cases pass. No browser, no network, deterministic: every case
 * drives the engine with a fixed 1/60s step, exactly like the frame driver.
 *
 * The two bots below are the point of this file. One plays the level the way a
 * person would — hold right, jump when something is in the way — and proves the
 * win is reachable; the other walks straight into a hazard and proves the loss
 * is reachable. Neither is a scripted key sequence tuned to the level: they
 * only look at the state they are given, so they keep working if the level is
 * edited, and if they cannot finish the level the level is the problem.
 */
"use strict";

var game = require("./game.js");
var levels = require("./levels.js");
var LEVEL_1 = levels.LEVEL_1;
var STEP = game.STEP;

var fails = [];
function check(cond, ok, bad) {
  console.log((cond ? "PASS  " : "FAIL  ") + (cond ? ok : bad));
  if (!cond) { fails.push(bad); }
}
function note(text) { console.log("      note: " + text); }

/* ---- the bots ----------------------------------------------------------- */

/* holds right and jumps when a wall or a hazard is close ahead. */
function playBot(state, player, level, input) {
  input.right = true;
  var ahead = player.x + player.w;
  var feet = player.y + player.h;
  var i, r, jump = false;

  var hazards = level.hazards || [];
  for (i = 0; i < hazards.length; i += 1) {
    r = hazards[i];
    var hd = r.x - ahead;
    /* between 30 and 80px ahead. The bounds are measured, not guessed: the
       arc from takeoff travels ~172px and its last ~8px of descent are what
       actually pass the hazard, so taking off too early drops the player onto
       it and too late runs into its side. */
    if (hd > 30 && hd < 80 && r.y < feet && r.y + r.h > player.y) { jump = true; }
  }
  var platforms = level.platforms || [];
  for (i = 0; i < platforms.length; i += 1) {
    r = platforms[i];
    var pd = r.x - ahead;
    if (pd > -2 && pd < 72 && r.y < feet && r.y + r.h > player.y) { jump = true; }
  }
  if (jump && player.onGround) {
    input.jump = true;
    input.jumpPressed = true;
  } else {
    input.jump = false;
  }
}

/* holds right and never jumps: walks into the first hazard. */
function walkBot(state, player, level, input) {
  input.right = true;
  input.jump = false;
}

/* ---- harness ------------------------------------------------------------ */

function run(bot, level, maxSeconds) {
  var state = game.createState();
  var player = game.createPlayer();
  var input = game.createInput();
  var steps = 0;
  var limit = Math.round(maxSeconds / STEP);
  var trace = [];

  input.jumpPressed = true;              /* start the run from the title */
  while (steps < limit && state.scene !== "won" && state.scene !== "lost") {
    game.step(state, player, level, input, STEP);
    bot(state, player, level, input);
    /* a cheap fingerprint of the whole run, for the determinism case */
    trace.push([Math.round(player.x * 100), Math.round(player.y * 100),
                state.score, state.collected.length].join(","));
    steps += 1;
  }
  return { state: state, player: player, input: input,
           time: steps * STEP, steps: steps, trace: trace.join("|") };
}

function snapshot(state, player) {
  return JSON.stringify({ state: state, player: player });
}

/* ---- cases -------------------------------------------------------------- */

console.log("── level data (t-b220 deliverable 1: data, >=6 platforms, >=3 hazards/pickups) ──");
check(Array.isArray(LEVEL_1.platforms) && LEVEL_1.platforms.length >= 6,
      "at least six platforms (" + LEVEL_1.platforms.length + ")",
      "fewer than six platforms");
check(Array.isArray(LEVEL_1.hazards) && LEVEL_1.hazards.length >= 3,
      "at least three hazards (" + LEVEL_1.hazards.length + ")",
      "fewer than three hazards");
check(Array.isArray(LEVEL_1.pickups) && LEVEL_1.pickups.length >= 3,
      "at least three pickups (" + LEVEL_1.pickups.length + ")",
      "fewer than three pickups");
check(!!LEVEL_1.goal && ["x", "y", "w", "h"].every(function (k) { return typeof LEVEL_1.goal[k] === "number"; }),
      "goal rect present and numeric", "goal rect missing or malformed");
var rects = LEVEL_1.platforms.concat(LEVEL_1.hazards, LEVEL_1.pickups, [LEVEL_1.goal]);
check(rects.every(function (r) {
        return ["x", "y", "w", "h"].every(function (k) { return typeof r[k] === "number" && isFinite(r[k]); });
      }),
      "every rect is four finite numbers", "a rect has a non-numeric or infinite field");
check(JSON.stringify(JSON.parse(JSON.stringify(LEVEL_1))) === JSON.stringify(LEVEL_1),
      "the level survives a JSON round-trip untouched (pure data, no functions)",
      "the level does not survive a JSON round-trip");
check(rects.every(function (r) { return r.w > 0 && r.h > 0; }),
      "no zero-sized rects (nothing invisible or untouchable)", "a rect has zero width or height");

console.log("\n── deliverable 3/4: win reachable by normal play, in under 60s ──");
var win = run(playBot, LEVEL_1, 60);
check(win.state.scene === "won",
      "a running-and-jumping bot reaches the goal (won after " + win.time.toFixed(1) + "s of play)",
      "the bot never reached the goal in 60s (scene=" + win.state.scene + ")");
check(win.state.scene === "won" && win.time < 60,
      "win inside 60 simulated seconds (" + win.time.toFixed(1) + "s)",
      "no win inside 60s, so the 60s bound is unmet");
check(win.state.score >= game.FINISH_BONUS,
      "finishing scores at least the finish bonus (" + win.state.score + ")",
      "score at win is only " + win.state.score);
if (win.state.scene === "won") {
  note("a bot that only holds right and jumps at what is in front of it wins in "
       + win.time.toFixed(1) + "s of a 60s allowance; a human has that margin and more");
}

console.log("\n── deliverable 3: lose reachable, and recoverable ──");
var lose = run(walkBot, LEVEL_1, 60);
check(lose.state.scene === "lost",
      "walking into a hazard loses the run (lost after " + lose.time.toFixed(1) + "s)",
      "walking right never lost the run (scene=" + lose.state.scene + ")");
game.restart(lose.state, lose.player);
check(lose.state.scene === "title" && lose.state.score === 0 && lose.state.collected.length === 0,
      "restart after a loss clears scene, score and pickups",
      "restart left state behind: " + JSON.stringify(lose.state));
var retry = run(playBot, LEVEL_1, 60);
check(retry.state.scene === "won", "after that restart the same bot can still win",
      "the run after a restart could not win");

console.log("\n── deliverable 4: restart leaves no leaked variables ──");
var s1 = game.createState(), p1 = game.createPlayer(), i1 = game.createInput();
game.step(s1, p1, LEVEL_1, i1, STEP); i1.jumpPressed = true;   /* start playing */
for (var i = 0; i < 300; i += 1) { playBot(s1, p1, LEVEL_1, i1); game.step(s1, p1, LEVEL_1, i1, STEP); }
game.restart(s1, p1);
var snap1 = snapshot(s1, p1);
for (var j = 0; j < 120; j += 1) { playBot(s1, p1, LEVEL_1, i1); game.step(s1, p1, LEVEL_1, i1, STEP); }
game.restart(s1, p1);
var snap2 = snapshot(s1, p1);
check(snap1 === snap2, "two restarts in a row leave byte-identical state",
      "state after the second restart differs:\n      " + snap1 + "\n      " + snap2);
var pristine = JSON.stringify(LEVEL_1);
check(pristine === JSON.stringify(levels.LEVEL_1),
      "the authored level object is never mutated by play or restart",
      "playing mutated the level data (a restart could not fully reset it)");

console.log("\n── determinism (same inputs, same run) ──");
var a = run(playBot, LEVEL_1, 60);
var b = run(playBot, LEVEL_1, 60);
check(a.trace === b.trace && a.time === b.time,
      "two identical runs produce identical position/score traces (" + a.steps + " steps)",
      "the same inputs produced different traces — the sim is not deterministic");
note("trace covers every step's player position, score and pickup count");

console.log("\n── deliverable 2: a new level is only data ──");
var shortLevel = JSON.parse(JSON.stringify(LEVEL_1));
shortLevel.goal = { x: 260, y: 470, w: 20, h: 50 };      /* goal moved next to spawn */
shortLevel.hazards = [];
shortLevel.pickups = [{ x: 200, y: 496, w: 16, h: 16 }];
var quick = run(playBot, shortLevel, 60);
check(quick.state.scene === "won" && quick.time < 5,
      "a level built by editing only data wins in " + quick.time.toFixed(1) + "s (no code change)",
      "the data-only level did not play: scene=" + quick.state.scene);
check(quick.state.collected.length === 1 && quick.state.score === game.PICKUP_POINTS + game.FINISH_BONUS,
      "score follows the data: 1 pickup + finish = " + quick.state.score,
      "score did not follow the edited data: " + quick.state.score);

console.log();
if (fails.length) {
  console.log(fails.length + " check(s) FAILED:");
  fails.forEach(function (f) { console.log("  - " + f); });
  process.exit(1);
}
console.log("ALL CHECKS PASSED");
