"use strict";
/* VOICE V4 export tests. Run: node tests/test_export.js */
const assert = require("assert");
const { toText, toICS, share, uid } = require("../export.js");
const { parse } = require("../parser.js");

const NOW = new Date(2026, 9, 11, 9, 0);
const items = [
  { text: "buy milk", due: null, priority: "normal" },
  { text: "call mom", due: "2026-10-12T17:00", priority: "high" },
  { text: "pay rent", due: "2026-10-16", priority: "normal" },
  { text: "Meeting, with; tricky\\chars", due: "2026-10-13", priority: "low" },
];

let fails = 0;
function check(name, fn) {
  try { fn(); console.log("PASS", name); }
  catch (e) { fails++; console.log("FAIL", name, "-", e.message); }
}

check("toText renders checklist with due + priority marks", () => {
  const t = toText(items);
  assert(t.includes("- buy milk\n"), "plain item");
  assert(t.includes("- call mom [2026-10-12T17:00] [!]"), "timed + high");
  assert(t.includes("[~]"), "low mark");
});

check("toICS: one VEVENT per dated item, none for undated", () => {
  const ics = toICS(items, NOW);
  assert.strictEqual((ics.match(/BEGIN:VEVENT/g) || []).length, 3);
  assert(ics.startsWith("BEGIN:VCALENDAR\r\n"), "CRLF + header");
  assert(ics.trimEnd().endsWith("END:VCALENDAR"), "footer");
});

check("toICS: timed vs all-day forms", () => {
  const ics = toICS(items, NOW);
  assert(ics.includes("DTSTART:20261012T170000"), "timed start");
  assert(ics.includes("DTEND:20261012T180000"), "timed end +1h");
  assert(ics.includes("DTSTART;VALUE=DATE:20261016"), "all-day start");
  assert(ics.includes("DTEND;VALUE=DATE:20261017"), "all-day end next day");
});

check("toICS: RFC5545 escaping", () => {
  const ics = toICS(items, NOW);
  assert(ics.includes("SUMMARY:Meeting\\, with\\; tricky\\\\chars"), "escapes , ; \\");
});

check("toICS: priorities map 1/5/9", () => {
  const ics = toICS(items, NOW);
  assert(ics.includes("PRIORITY:1") && ics.includes("PRIORITY:5") && ics.includes("PRIORITY:9"));
});

check("toICS + uid deterministic", () => {
  assert.strictEqual(toICS(items, NOW), toICS(items, NOW));
  assert.strictEqual(uid(items[1]), uid(items[1]));
  assert.notStrictEqual(uid(items[1]), uid(items[2]));
});

(async () => {
  // no nav at all -> text
  let r = await share(items, null);
  check("share falls to text without browser APIs", () => assert.strictEqual(r.method, "text"));
  // clipboard present
  let copied = null;
  r = await share(items, { clipboard: { writeText: (t) => { copied = t; return Promise.resolve(); } } });
  check("share uses clipboard when available", () => {
    assert.strictEqual(r.method, "clipboard");
    assert.strictEqual(copied, toText(items));
  });
  // share sheet rejects -> clipboard
  r = await share(items, {
    share: () => Promise.reject(new Error("user cancelled")),
    clipboard: { writeText: () => Promise.resolve() },
  });
  check("share falls back from rejected share sheet", () => assert.strictEqual(r.method, "clipboard"));

  check("parser integration: parsed due lands in ICS", () => {
    const parsed = parse("buy milk and call mom tomorrow at five", NOW);
    const ics = toICS(parsed, NOW);
    assert(ics.includes("DTSTART:20261012T170000"), "JOBS example due in calendar");
    assert.strictEqual((ics.match(/BEGIN:VEVENT/g) || []).length, 1);
  });

  if (fails) { console.log(fails + " failure(s)"); process.exit(1); }
  console.log("OK: all export checks passed");
  process.exit(0);
})();
