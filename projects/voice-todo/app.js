"use strict";
/* VOICE V3 — app wiring (t-20261011-d339)
 * List UI on top of store.js + parser.js + export.js.
 * Speech entry uses V1's hook when present (window.voiceTodoTranscribe);
 * otherwise a textarea (honest fallback until V1 lands).
 */
(function () {
  var store = makeStore(typeof localStorage !== "undefined" ? localStorage : null);
  var listEl = document.getElementById("list");
  var noteEl = document.getElementById("note");
  var speechBtn = document.getElementById("speak");
  var ta = document.getElementById("typed");

  function render() {
    listEl.innerHTML = "";
    var its = store.all();
    if (!its.length) {
      listEl.textContent = "Nothing yet. Say or type something.";
    }
    its.forEach(function (it) {
      var li = document.createElement("li");
      li.className = it.done ? "done" : it.priority;
      var chk = document.createElement("input");
      chk.type = "checkbox"; chk.checked = it.done;
      chk.onchange = function () { store.toggle(it.id); render(); };
      var span = document.createElement("span");
      span.className = "txt";
      span.textContent = it.text + (it.due ? "  [" + it.due + "]" : "");
      span.ondblclick = function () {
        var v = prompt("Edit item:", it.text);
        if (v !== null && v.trim()) { store.edit(it.id, v.trim()); render(); }
      };
      var up = btn("↑", function () { store.move(it.id, -1); render(); });
      var dn = btn("↓", function () { store.move(it.id, 1); render(); });
      var del = btn("×", function () { store.remove(it.id); render(); });
      li.appendChild(chk); li.appendChild(span);
      li.appendChild(up); li.appendChild(dn); li.appendChild(del);
      listEl.appendChild(li);
    });
    noteEl.textContent = store.persisted()
      ? its.length + " item(s), saved on this device."
      : its.length + " item(s) in memory only - this browser offers no storage.";
  }
  function btn(label, fn) {
    var b = document.createElement("button");
    b.type = "button"; b.textContent = label; b.onclick = fn;
    return b;
  }

  function ingest(text) {
    var parsed = parse(text, new Date());
    if (!parsed.length) { noteEl.textContent = "Could not find an item in that."; return; }
    store.addMany(parsed);
    render();
  }

  document.getElementById("add").onclick = function () {
    if (ta.value.trim()) { ingest(ta.value); ta.value = ""; }
  };

  if (typeof window.voiceTodoTranscribe === "function") {
    speechBtn.onclick = function () {
      speechBtn.disabled = true;
      window.voiceTodoTranscribe(function (text, how) {
        speechBtn.disabled = false;
        if (text) ingest(text);
        noteEl.textContent = "transcribed " + (how || "") + ".";
      });
    };
  } else {
    speechBtn.disabled = true;
    speechBtn.title = "speech arrives with V1";
  }

  document.getElementById("copy").onclick = function () {
    share(store.all()).then(function (r) {
      noteEl.textContent = "copied via " + r.method + ".";
    });
  };
  document.getElementById("ics").onclick = function () {
    var ics = toICS(store.all(), new Date());
    var a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([ics], { type: "text/calendar" }));
    a.download = "voice-todo.ics";
    a.click();
  };
  document.getElementById("clear").onclick = function () {
    store.clearDone(); render();
  };

  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("sw.js").catch(function () {});
  }
  render();
})();
