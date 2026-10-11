"use strict";
/* VOICE V4 — export and share (t-20261011-b984)
 * Plain JS, no dependencies. Works in node (tests) and the browser app.
 *   toText(items)      -> readable checklist text
 *   toICS(items, now)  -> RFC 5545 calendar for the dated items
 *   share(items)       -> navigator.share -> clipboard -> {method, text}
 * items: [{text, due, priority}] as produced by parser.js
 * due:   "YYYY-MM-DD" (all-day) or "YYYY-MM-DDTHH:MM" (timed, floating local)
 */

function esc(s) {
  return String(s).replace(/\\/g, "\\\\").replace(/;/g, "\\;")
                  .replace(/,/g, "\\,").replace(/\n/g, "\\n");
}

function icsStamp(d) {
  function p(n) { return (n < 10 ? "0" : "") + n; }
  return d.getFullYear() + p(d.getMonth() + 1) + p(d.getDate()) + "T" +
         p(d.getHours()) + p(d.getMinutes()) + "00";
}

/* deterministic UID: djb2 over text+due (stable across exports/devices) */
function uid(item) {
  var s = item.text + "|" + (item.due || "");
  var h = 5381;
  for (var i = 0; i < s.length; i++) h = ((h << 5) + h + s.charCodeAt(i)) >>> 0;
  return h.toString(16) + "@voice-todo";
}

function toText(items) {
  return items.map(function (it) {
    var bits = ["- " + it.text];
    if (it.due) bits.push("[" + it.due + "]");
    if (it.priority === "high") bits.push("[!]");
    if (it.priority === "low") bits.push("[~]");
    return bits.join(" ");
  }).join("\n");
}

function toICS(items, now) {
  now = now || new Date();
  var L = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//chatcode//voice-todo//EN",
           "CALSCALE:GREGORIAN"];
  items.forEach(function (it) {
    if (!it.due) return;
    L.push("BEGIN:VEVENT", "UID:" + uid(it), "SUMMARY:" + esc(it.text),
           "DTSTAMP:" + icsStamp(now));
    if (/T/.test(it.due)) {
      var dt = new Date(it.due);
      var end = new Date(dt.getTime() + 3600000);
      L.push("DTSTART:" + icsStamp(dt), "DTEND:" + icsStamp(end));
    } else {
      L.push("DTSTART;VALUE=DATE:" + it.due.replace(/-/g, ""),
             "DTEND;VALUE=DATE:" + icsStamp(new Date(new Date(it.due).getTime() + 86400000)).slice(0, 8));
    }
    L.push("PRIORITY:" + (it.priority === "high" ? 1 : it.priority === "low" ? 9 : 5),
           "END:VEVENT");
  });
  L.push("END:VCALENDAR");
  return L.join("\r\n") + "\r\n";
}

/* honest fallback chain: share sheet -> clipboard -> hand the text back */
function share(items, nav, doc) {
  var text = toText(items);
  nav = nav || (typeof navigator !== "undefined" ? navigator : null);
  if (nav && nav.share) {
    return nav.share({ text: text }).then(function () {
      return { method: "share-sheet", text: text };
    }).catch(function () { return clipboardThenText(text, nav); });
  }
  return Promise.resolve(clipboardThenText(text, nav));
}

function clipboardThenText(text, nav) {
  if (nav && nav.clipboard && nav.clipboard.writeText) {
    return nav.clipboard.writeText(text).then(function () {
      return { method: "clipboard", text: text };
    }).catch(function () { return { method: "text", text: text }; });
  }
  return { method: "text", text: text };
}

if (typeof module !== "undefined") {
  module.exports = { toText: toText, toICS: toICS, share: share, uid: uid };
}
