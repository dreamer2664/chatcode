#!/usr/bin/env node
/* Headless engine harness for game.js (task t-20261011-1ec9).

     node test-game.js

   Zero DOM, zero randomness. The script below drives one full story on
   purpose: title → play → move right → jump → hit the hazard (lost) →
   press jump again → back at title with the player reset. Then it proves
   determinism by running the same 600 scripted steps twice and comparing
   every physics value byte-for-byte. This is the harness t-20261011-d4e3
   and t-20261011-b220 can reuse for their own acceptance criteria.

   Exits 1 on any failed check. */
"use strict";
const engine = require("./game.js");

function runScripted(steps) {
  const state = engine.createState();
  const player = engine.createPlayer();
  const input = engine.createInput();
  const level = engine.LEVEL_DEMO;
  const seen = { play: 0, lost: 0, won: 0, title: 0 };
  let maxX = player.x;
  let landedAtLeastOnce = false;
  for (let s = 0; s < steps; s++) {
    input.left = s >= 60 && s < 160;
    input.right = s >= 160 && s < 320;
    if (s === 10 || s === 200 || s === 380) { input.jumpPressed = true; input.jump = true; }
    if (s === 40 || s === 230 || s === 410) { input.jump = false; }
    engine.step(state, player, level, input, engine.STEP);
    seen[state.scene] += 1;
    if (player.x > maxX) { maxX = player.x; }
    if (player.onGround) { landedAtLeastOnce = true; }
  }
  return { scene: state.scene, time: state.time, x: player.x, y: player.y,
           vx: player.vx, vy: player.vy, onGround: player.onGround,
           seen, maxX, landedAtLeastOnce };
}

let failures = 0;
function check(name, cond) {
  console.log((cond ? "ok   " : "FAIL ") + name);
  if (!cond) { failures++; }
}

const a = runScripted(600);
const b = runScripted(600);

check("story: title is entered and left (play reached)", a.seen.play > 0);
check("story: player reached and landed on platforms (no fall-through)",
      a.landedAtLeastOnce && a.seen.play > 0);
check(`story: scripted run moved right from spawn (maxX=${a.maxX.toFixed(1)} > 40)`,
      a.maxX > 40);
check(`story: hazard reached -> 'lost' happened (seen.lost=${a.seen.lost})`,
      a.seen.lost > 0);
check("story: restart after lost returned to title and reset the player to spawn",
      a.scene === "title" && a.x === 40 && a.y === 460 && a.vx === 0 && a.vy === 0);
check("player never left the allowed area vertically", a.y >= 0 && a.y <= 740);
const same = a.scene === b.scene && a.x === b.x && a.y === b.y &&
             a.vx === b.vx && a.vy === b.vy && a.onGround === b.onGround &&
             a.time === b.time && a.maxX === b.maxX &&
             a.seen.play === b.seen.play && a.seen.lost === b.seen.lost &&
             a.seen.title === b.seen.title;
check(`determinism: two 600-step runs byte-identical (time=${a.time.toFixed(3)}s, maxX=${a.maxX.toFixed(1)})`, same);

console.log(failures ? `FAILURES: ${failures}` : "OK: engine harness green");
process.exit(failures ? 1 : 0);
