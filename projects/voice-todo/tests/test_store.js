"use strict";
/* VOICE V3 store tests. Run: node tests/test_store.js */
const assert = require("assert");
const { makeStore } = require("../store.js");
const { parse } = require("../parser.js");

function fakeStorage() {
  const m = new Map();
  return {
    getItem: (k) => (m.has(k) ? m.get(k) : null),
    setItem: (k, v) => m.set(k, String(v)),
    removeItem: (k) => m.delete(k),
    _map: m,
  };
}

let fails = 0;
function check(name, fn) {
  try { fn(); console.log("PASS", name); }
  catch (e) { fails++; console.log("FAIL", name, "-", e.message); }
}

check("add/toggle/edit/move/remove/clearDone", () => {
  const s = makeStore(fakeStorage());
  assert.strictEqual(s.persisted(), true);
  const a = s.add("buy milk", null, "normal");
  const b = s.add("call mom", "2026-10-12T17:00", "high");
  const c = s.add("water plants", null, "low");
  assert.strictEqual(s.all().length, 3);
  assert.strictEqual(s.toggle(a.id).done, true);
  assert.strictEqual(s.toggle(a.id).done, false);
  assert.strictEqual(s.edit(b.id, "call mom back").text, "call mom back");
  s.move(c.id, -1);
  assert.deepStrictEqual(s.all().map((x) => x.text),
    ["buy milk", "water plants", "call mom back"]);
  s.move(c.id, -1);
  assert.deepStrictEqual(s.all().map((x) => x.text),
    ["water plants", "buy milk", "call mom back"]);
  s.move(c.id, 1);           // already last: no-op
  assert.strictEqual(s.all()[2].text, "call mom back");
  s.toggle(a.id);
  assert.strictEqual(s.clearDone(), 2);
  s.remove(c.id);
  assert.strictEqual(s.all().length, 1);
});

check("persistence round-trip survives a reload", () => {
  const st = fakeStorage();
  let s = makeStore(st);
  s.add("pay rent", "2026-10-16", "normal");
  s.add("read chapter 3", null, "low");
  s = makeStore(st);  // "reload"
  const texts = s.all().map((x) => x.text);
  assert.deepStrictEqual(texts, ["pay rent", "read chapter 3"]);
  assert.strictEqual(s.all()[0].due, "2026-10-16");
});

check("no storage: in-memory and honest about it", () => {
  const s = makeStore(null);
  assert.strictEqual(s.persisted(), false);
  s.add("x", null, "normal");
  assert.strictEqual(s.all().length, 1);
});

check("corrupt storage: starts clean, never crashes", () => {
  const st = fakeStorage();
  st.setItem("voice-todo-items", "{not json!!");
  const s = makeStore(st);
  assert.deepStrictEqual(s.all(), []);
  s.add("fresh", null, "normal");
  assert.strictEqual(s.all().length, 1);
});

check("addMany from the parser keeps due + priority", () => {
  const s = makeStore(fakeStorage());
  const parsed = parse("buy milk and call mom tomorrow at five",
    new Date(2026, 9, 11, 9, 0));
  s.addMany(parsed);
  const all = s.all();
  assert.strictEqual(all.length, 2);
  assert.strictEqual(all[1].due, "2026-10-12T17:00");
  assert.strictEqual(all[1].priority, "normal");
});

if (fails) { console.log(fails + " failure(s)"); process.exit(1); }
console.log("OK: all store checks passed");
