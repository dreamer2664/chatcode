"use strict";
/* VOICE V3 — the list store (t-20261011-d339)
 * Pure logic, node + browser. Persistence: any localStorage-shaped object;
 * without one the store stays in memory and says so (honest).
 */

function makeStore(storage, key) {
  key = key || "voice-todo-items";
  var persisted = !!(storage && typeof storage.getItem === "function");
  var seq = 0;
  var items = [];

  function load() {
    if (!persisted) return;
    try {
      var raw = storage.getItem(key);
      if (raw) {
        var doc = JSON.parse(raw);
        items = doc.items || [];
        seq = doc.seq || items.length;
      }
    } catch (e) { items = []; }  /* corrupt storage: start clean, never crash */
  }
  function save() {
    if (!persisted) return;
    try { storage.setItem(key, JSON.stringify({ seq: seq, items: items })); }
    catch (e) { /* full/blocked storage: keep the in-memory copy */ }
  }

  load();

  return {
    persisted: function () { return persisted; },
    all: function () { return items.slice(); },
    add: function (text, due, priority) {
      seq += 1;
      var it = { id: seq, text: text, due: due || null,
                 priority: priority || "normal", done: false };
      items.push(it);
      save();
      return it;
    },
    addMany: function (parsed) {
      var out = [];
      for (var i = 0; i < parsed.length; i++) {
        out.push(this.add(parsed[i].text, parsed[i].due, parsed[i].priority));
      }
      return out;
    },
    toggle: function (id) {
      for (var i = 0; i < items.length; i++) if (items[i].id === id) {
        items[i].done = !items[i].done; save(); return items[i];
      }
      return null;
    },
    edit: function (id, text) {
      for (var i = 0; i < items.length; i++) if (items[i].id === id) {
        items[i].text = text; save(); return items[i];
      }
      return null;
    },
    move: function (id, dir) {  /* dir -1 up, +1 down */
      for (var i = 0; i < items.length; i++) if (items[i].id === id) {
        var j = i + dir;
        if (j < 0 || j >= items.length) return items[i];
        var t = items[i]; items[i] = items[j]; items[j] = t;
        save(); return t;
      }
      return null;
    },
    remove: function (id) {
      for (var i = 0; i < items.length; i++) if (items[i].id === id) {
        save(); return items.splice(i, 1)[0];
      }
      return null;
    },
    clearDone: function () {
      items = items.filter(function (x) { return !x.done; });
      save();
      return items.length;
    },
  };
}

if (typeof module !== "undefined") module.exports = { makeStore: makeStore };
