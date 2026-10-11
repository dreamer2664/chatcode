/* platformer — physics determinism harness (task t-20261011-d4e3).
   Acceptance: step the simulation 600 times with fixed input and print the
   final x/y; the numbers must be identical across runs.

   One command from projects/platformer/:   node physics_determinism.js
*/
"use strict";
var game = require("./game.js");

function run() {
  var state = game.createState();
  var player = game.createPlayer();
  var level = game.LEVEL_1;
  var input = game.createInput();
  state.scene = "play";

  for (var i = 0; i < 600; i++) {
    input.left = false; input.right = false; input.jumpPressed = false;

    /* scripted, deterministic input, kept clear of hazards:
       settle, run, friction-stop, full jump, run back into the left wall,
       jump again, stand. */
    if (i >= 5 && i < 30)   { input.right = true; }
    if (i === 51)           { input.jumpPressed = true; input.jump = true; }
    if (i === 91)           { input.jump = false; }
    if (i >= 141 && i < 181) { input.left = true; }
    if (i === 241)          { input.jumpPressed = true; input.jump = true; }
    if (i === 281)          { input.jump = false; }

    game.step(state, player, level, input, game.STEP);
  }
  console.log("after 600 fixed steps: x=" + player.x + " y=" + player.y +
              " vx=" + player.vx + " vy=" + player.vy +
              " onGround=" + player.onGround + " scene=" + state.scene);
}

run();
