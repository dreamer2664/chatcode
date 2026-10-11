"use strict";
/* VOICE V2 parser test — every row of PHRASES.md must pass.
 * Run:  node tests/test_parser.js
 */
const fs = require("fs");
const path = require("path");
const { parse } = require("../parser.js");

const ANCHOR = new Date(2026, 9, 11, 9, 0); // Sunday, pinned by PHRASES.md

function rows() {
  const md = fs.readFileSync(path.join(__dirname, "..", "PHRASES.md"), "utf8");
  const out = [];
  for (const line of md.split("\n")) {
    const m = line.match(/^\|\s*([^|`]+?)\s*\|\s*`(\[.*\])`\s*\|$/);
    if (m && !/utterance/.test(m[1])) out.push({ u: m[1], want: JSON.parse(m[2]) });
  }
  return out;
}

function main() {
  const rs = rows();
  if (rs.length < 10) { console.log("FAIL: PHRASES.md table not parsed (" + rs.length + " rows)"); return 1; }
  let bad = 0;
  for (const r of rs) {
    const got = parse(r.u, ANCHOR);
    const a = JSON.stringify(got), b = JSON.stringify(r.want);
    if (a !== b) { bad++; console.log("FAIL:", r.u, "\n  want", b, "\n  got ", a); }
    else console.log("PASS:", r.u);
  }
  // robustness extras
  const empty = parse("   ", ANCHOR);
  if (empty.length !== 0) { console.log("FAIL: blank input", JSON.stringify(empty)); bad++; }
  const weird = parse("!!! @@ hmm", ANCHOR);
  if (!Array.isArray(weird)) { console.log("FAIL: junk input crashed"); bad++; }
  if (bad) { console.log(bad + " failure(s)"); return 1; }
  console.log("OK: all " + rs.length + " PHRASES rows pass (+2 robustness checks)");
  return 0;
}
process.exit(main());
