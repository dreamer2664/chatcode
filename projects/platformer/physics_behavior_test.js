/* platformer — physics behavior checks (task t-20261011-d4e3).
   Runs the real stepPhysics through game.step() against LEVEL_1 and asserts
   the task's acceptance items. One command from projects/platformer/:

       node physics_behavior_test.js
*/
"use strict";
var game = require("./game.js");
var failures = [];

function check(name, cond, detail) {
  if (cond) { console.log("PASS  " + name); }
  else { console.log("FAIL  " + name + (detail ? " — " + detail : "")); failures.push(name); }
}

function setup() {
  var state = game.createState();
  state.scene = "play";
  var player = game.createPlayer();
  var level = JSON.parse(JSON.stringify(game.LEVEL_1));
  return { state: state, player: player, level: level, input: game.createInput() };
}

function oneStep(env, mutate) {
  env.input.left = false; env.input.right = false; env.input.jumpPressed = false;
  if (mutate) { mutate(env.input); }
  game.step(env.state, env.player, env.level, env.input, game.STEP);
}

function steps(env, n, mutate) {
  for (var i = 0; i < n; i++) { oneStep(env, mutate); }
}

/* LEVEL_1 landmarks (levels.js): ground {0,520,960,40}; step {430,448,100,72};
   blocker column {530,380,140,140}; roof 1 {700,330,110,16};
   ground hazards at x=200 and x=380; chimney {820,300,24,60}. */

/* 1. Standing on the ground is stable: no position jitter, stays grounded. */
(function () {
  var env = setup();
  env.player.x = 60; env.player.y = 100;              /* falls onto ground */
  steps(env, 60);
  var yRef = env.player.y;
  var grounded = env.player.onGround === true;
  var stable = true;
  for (var i = 0; i < 120; i++) {
    oneStep(env);
    if (env.player.y !== yRef || !env.player.onGround) { stable = false; break; }
  }
  check("standing is stable (y constant + grounded for 120 consecutive steps)",
        grounded && stable, "yRef=" + yRef + " onGround=" + env.player.onGround);
})();

/* 2. Jump arc keeps the tuned height (~113px: JUMP_V^2 / (2*GRAV)). */
(function () {
  var env = setup();
  env.player.x = 60; env.player.y = 100;
  steps(env, 60);                                     /* settle on ground */
  var groundY = env.player.y;
  var minY = groundY;
  for (var i = 0; i < 100; i++) {
    oneStep(env, function (inp) {
      if (i === 0) { inp.jumpPressed = true; inp.jump = true; }
    });
    if (env.player.y < minY) { minY = env.player.y; }
  }
  var rise = groundY - minY;
  check("jump arc height is the tuned ~113px (measured " + rise.toFixed(1) + "px)",
        rise > 100 && rise < 125, "rise=" + rise);
})();

/* 3. Coyote time: a jump fired shortly AFTER walking off a ledge still works. */
(function () {
  var env = setup();
  env.player.x = 450; env.player.y = 448 - 36;        /* on the step */
  steps(env, 5);                                      /* grounded, coyote charged */
  var fellAt = -1;
  for (var i = 0; i < 30 && fellAt < 0; i++) {
    oneStep(env, function (inp) { inp.left = true; });
    if (!env.player.onGround) { fellAt = i; }
  }
  var inAir = fellAt >= 0;
  oneStep(env, function (inp) { inp.left = true; });  /* ~17 ms into the window */
  var coyoteLeft = env.player.coyoteMs;
  var vyBefore = env.player.vy;
  oneStep(env, function (inp) { inp.left = true; inp.jumpPressed = true; inp.jump = true; });
  check("coyote: jump fires after walking off the step (within 100 ms window)",
        inAir && coyoteLeft > 0 && vyBefore >= 0 && env.player.vy < 0,
        "fellAt=" + fellAt + " coyoteMs=" + coyoteLeft.toFixed(0) +
        " vy " + vyBefore + " -> " + env.player.vy);
})();

/* 4. No tunnelling: a terminal-speed fall onto the 16 px roof lands ON it. */
(function () {
  var env = setup();
  env.player.x = 740; env.player.y = -800;            /* long fall onto roof 1 */
  var roof = env.level.platforms[3];                  /* {x:700,y:330,w:110,h:16} */
  var passedThrough = false;
  for (var i = 0; i < 600; i++) {
    var yPrev = env.player.y;
    oneStep(env);
    if (yPrev + env.player.h <= roof.y && env.player.y > roof.y) { passedThrough = true; }
  }
  var landed = env.player.onGround === true &&
               Math.abs(env.player.y - (roof.y - env.player.h)) < 0.001;
  check("no tunnelling: terminal-speed fall lands on the 16 px roof",
        !passedThrough && landed,
        "y=" + env.player.y + " expected=" + (roof.y - env.player.h) +
        " onGround=" + env.player.onGround + " passedThrough=" + passedThrough);
})();

/* 5. Head-bump: rising into a roof from below stops the ascent. */
(function () {
  var env = setup();
  var roof = env.level.platforms[3];                  /* {x:700,y:330,w:110,h:16} */
  env.player.x = roof.x + 50;
  env.player.y = roof.y + roof.h + 2;                 /* just under it */
  env.player.vy = -800;                               /* hard upward */
  steps(env, 5);
  check("head-bump stops ascent below the roof",
        env.player.y >= roof.y + roof.h - 0.001,
        "y=" + env.player.y + " roofBottom=" + (roof.y + roof.h) + " vy=" + env.player.vy);
})();

/* 6. Side-block: running into the blocker column stops flush against it. */
(function () {
  var env = setup();
  env.player.x = 460; env.player.y = 100;             /* falls onto the step */
  steps(env, 60);                                     /* settle on the step */
  steps(env, 60, function (inp) { inp.right = true; });
  var column = env.level.platforms[2];                /* {x:530,y:380,w:140,h:140} */
  var flush = Math.abs(env.player.x - (column.x - env.player.w)) < 0.001;
  check("side-block: player stops flush against the column, vx zeroed",
        flush && env.player.vx === 0 && env.player.onGround,
        "x=" + env.player.x + " expected=" + (column.x - env.player.w) +
        " vx=" + env.player.vx);
})();

/* 7. Friction: releasing the run input on the ground decelerates to a stop. */
(function () {
  var env = setup();
  env.player.x = 60; env.player.y = 100;
  steps(env, 60);                                     /* settle on ground */
  steps(env, 20, function (inp) { inp.right = true; });  /* reaches full 240 */
  var fullSpeed = env.player.vx;
  var xAtRelease = env.player.x;
  steps(env, 30);                                     /* no input: friction */
  check("friction: run then release decelerates to exactly 0",
        fullSpeed === 240 && env.player.vx === 0 && env.player.x > xAtRelease,
        "fullSpeed=" + fullSpeed + " vxAfter=" + env.player.vx);
})();

if (failures.length) {
  console.log(failures.length + " behavior check(s) FAILED");
  process.exit(1);
}
console.log("all behavior checks passed");
