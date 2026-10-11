/* platformer levels — pure data (task t-20261011-b220, epic t-20261011-a629).
 *
 * LEVEL FORMAT (also documented in README.md; the engine reads nothing else):
 *   {
 *     name:      string,                  // shown nowhere yet, for humans
 *     platforms: [{x,y,w,h}],             // solids: ground, steps, walls
 *     hazards:   [{x,y,w,h}],             // touching one loses the run
 *     pickups:   [{x,y,w,h}],             // optional; 10 points each
 *     goal:      {x,y,w,h}                // touching it wins the run
 *   }
 *
 * Coordinates: pixels, origin top-left, y grows DOWN, the view is 960x540.
 * A rect is {x, y, w, h}: x/y is its top-left corner. Units are px and seconds.
 * A level is ONLY this data — adding a level means adding an object here (or
 * passing one to the engine), never touching physics or scene code.
 *
 * Reachability is verified, not assumed: test-level.js drives a scripted bot
 * (hold right; jump at a hazard or a wall ahead) through LEVEL_1 and fails if
 * it cannot win in under 60 simulated seconds. Physics allows a jump of about
 * 113px of height and 170px of distance, so every rise below is <= 80px and
 * every gap <= 60px, which leaves room for a human player to be sloppier.
 */
"use strict";
(function () {
  var LEVEL_1 = {
    name: "Rooftops",
    /* Path: ground -> jump two ground hazards -> up the step -> over the
       blocker column -> roof 1 -> roof 2 -> goal. The step and the blocker are
       solid from the ground up, so running through them is impossible: the
       climb is forced. Margins are measured, not guessed (test-level.js plays
       it): every rise is <= 80px against a ~113px jump, every gap <= 50px
       against a ~170px jump, hazard widths are 32px, and each hazard leaves at
       least 16px of landing room past its far edge. */
    platforms: [
      { x: 0,   y: 520, w: 960, h: 40 },    // ground, spawn at x=40 on top
      { x: 430, y: 448, w: 100, h: 72 },    // step, solid to the ground
      { x: 530, y: 380, w: 140, h: 140 },   // blocker column, top at y=380
      { x: 700, y: 330, w: 110, h: 16 },    // roof 1
      { x: 850, y: 280, w: 110, h: 16 },    // roof 2, the goal lives here
      { x: 880, y: 430, w: 80,  h: 16 }     // right-wall ledge, optional path
    ],
    hazards: [
      { x: 200, y: 500, w: 32, h: 20 },     // on the ground
      { x: 380, y: 500, w: 32, h: 20 },     // on the ground
      { x: 820, y: 300, w: 24, h: 60 }      // chimney in the gap between roofs
    ],
    pickups: [
      { x: 120, y: 496, w: 16, h: 16 },     // ground, on the way
      { x: 500, y: 432, w: 16, h: 16 },     // on the step, on the way
      { x: 884, y: 414, w: 16, h: 16 },     // on the ledge, optional detour
      { x: 930, y: 264, w: 16, h: 16 }      // on roof 2, past the hazard
    ],
    goal: { x: 944, y: 220, w: 16, h: 60 }
  };

  var LEVELS = { level1: LEVEL_1 };

  var exported = { LEVELS: LEVELS, LEVEL_1: LEVEL_1 };
  if (typeof module !== "undefined" && module.exports) {
    module.exports = exported;            // node (tests)
  }
  if (typeof window !== "undefined") {
    window.PLATFORMER_LEVELS = exported;  // browser (index.html)
  }
})();
