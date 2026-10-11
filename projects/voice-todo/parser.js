"use strict";
/* VOICE V2 — utterance -> items (t-20261011-f697)
 * Plain JS, no dependencies: runs in node (tests) and in the browser app.
 * parse(utterance, now) -> [{text, due, priority}]
 *   due: "YYYY-MM-DD" or "YYYY-MM-DDTHH:MM" or null
 *   priority: "high" | "normal" | "low"
 * Deterministic for a given `now`; PHRASES.md pins now = 2026-10-11T09:00.
 */

var DOW = { sunday: 0, monday: 1, tuesday: 2, wednesday: 3, thursday: 4,
            friday: 5, saturday: 6 };
var WORD_NUM = { one: 1, two: 2, three: 3, four: 4, five: 5, six: 6, seven: 7,
                 eight: 8, nine: 9, ten: 10, eleven: 11, twelve: 12 };
var VERBS = ["buy", "call", "get", "take", "email", "send", "pay", "water",
             "pick", "book", "schedule", "check", "flip", "fix", "write",
             "read", "upload", "download", "test", "review", "update",
             "clean", "cook", "order", "ask", "tell", "visit", "bring"];

function pad(n) { return (n < 10 ? "0" : "") + n; }
function fmtDate(d) { return d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate()); }
function fmtDT(d) { return fmtDate(d) + "T" + pad(d.getHours()) + ":" + pad(d.getMinutes()); }
function addDays(d, n) { var x = new Date(d); x.setDate(x.getDate() + n); return x; }

function nextDow(now, dow, strictly) {
  var diff = (dow - now.getDay() + 7) % 7;
  if (strictly && diff === 0) diff = 7;
  if (!strictly && diff === 0) diff = 0;
  return addDays(now, diff);
}

function hourFromWords(tok) {
  if (WORD_NUM[tok]) return WORD_NUM[tok];
  return null;
}

/* extract one date/time expression; returns {due, rest} or null */
function extractWhen(seg, now) {
  var m, d = null, t = null, cut = [];

  m = seg.match(/\b(in|within)\s+(\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\s+(hour|hours|minute|minutes|day|days|week|weeks)\b/i);
  if (m) {
    var n = WORD_NUM[m[2].toLowerCase()] || parseInt(m[2], 10);
    d = new Date(now);
    if (/hour/.test(m[3])) d.setHours(d.getHours() + n);
    else if (/minute/.test(m[3])) d.setMinutes(d.getMinutes() + n);
    else if (/week/.test(m[3])) d = addDays(now, 7 * n);
    else d = addDays(now, n);
    cut.push(m[0]);
    return { due: fmtDT(d), cut: cut };
  }

  var dm = seg.match(/\bat\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b/i);
  var wm = !dm ? seg.match(/\bat\s+(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\s*(am|pm)?\b/i) : null;
  if (dm || wm) {
    var h = dm ? parseInt(dm[1], 10) : WORD_NUM[wm[1].toLowerCase()];
    var min = dm && dm[2] ? parseInt(dm[2], 10) : 0;
    var ap = (dm ? dm[3] : wm[2]) || null;
    if (ap) { ap = ap.toLowerCase(); if (ap === "pm" && h < 12) h += 12; if (ap === "am" && h === 12) h = 0; }
    else if (h < 7) h += 12; /* bare small numbers read as afternoon: "at five" */
    t = { h: h, m: min };
    cut.push(dm ? dm[0] : wm[0]);
  }

  var dayRe = /\b(today|tonight|this evening|tomorrow|yesterday|next week|this weekend|on\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)|next\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)|by\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday|tomorrow|friday))\b/i;
  m = seg.match(dayRe);
  if (m) {
    var tok = m[0].toLowerCase();
    if (tok === "today") d = new Date(now);
    else if (tok === "tomorrow" || tok === "by tomorrow") d = addDays(now, 1);
    else if (tok === "yesterday") d = addDays(now, -1);
    else if (tok === "tonight" || tok === "this evening") { d = new Date(now); t = t || { h: 18, m: 0 }; }
    else if (tok === "next week") d = addDays(now, 7);
    else if (tok === "this weekend") d = nextDow(now, 6, false) || addDays(now, 6);
    else {
      var mm = tok.match(/(?:on|next|by)\s+(\w+)/);
      if (mm && DOW[mm[1]] !== undefined) d = nextDow(now, DOW[mm[1]], tok.indexOf("next") === 0);
    }
    cut.push(m[0]);
  }

  if (!d && !t) return null;
  var base = d || new Date(now);
  if (t) { base = new Date(base); base.setHours(t.h, t.m, 0, 0); return { due: fmtDT(base), cut: cut }; }
  return { due: fmtDate(base), cut: cut };
}

function stripFiller(s) {
  s = s.replace(/\b(um|uh|erm|hey|okay|ok|so|please|just|and then|listen)\b[,:]*/gi, " ");
  s = s.replace(/^\s*(please|don'?t forget to|remember to|remind me to|i need to|i have to|can you|could you|make sure to|make sure i|add|put)\s+/i, "");
  return s.replace(/\s+/g, " ").trim();
}

function splitClauses(s) {
  return s.split(/\s+and\s+|\s+then\s+|\s+also\s+|\s+plus\s+|,\s*/i)
          .map(function (x) { return x.trim(); })
          .filter(function (x) { return x.length > 0; });
}

function hasVerb(s) {
  var w = s.toLowerCase().split(/\W+/);
  for (var i = 0; i < w.length; i++) if (VERBS.indexOf(w[i]) >= 0) return w[i];
  return null;
}

function parse(utterance, now) {
  now = now || new Date();
  var segs = splitClauses(stripFiller(String(utterance)));
  var items = [];
  var prevVerb = null;
  for (var i = 0; i < segs.length; i++) {
    var seg = segs[i];
    var priority = "normal";
    var pm = seg.match(/\b(urgent|asap|as soon as possible|important|high priority)\b/i);
    if (pm) { priority = "high"; seg = seg.replace(pm[0], " "); }
    var lm = seg.match(/\b(no rush|whenever|sometime|eventually|low priority)\b/i);
    if (lm) { priority = "low"; seg = seg.replace(lm[0], " "); }

    var when = extractWhen(seg, now);
    var due = null;
    if (when) {
      due = when.due;
      for (var c = 0; c < when.cut.length; c++) seg = seg.replace(when.cut[c], " ");
    } else {
      seg = seg.replace(/\s+\bon\b\s+/i, " ");  /* "no rush on updating..." */
    }

    seg = stripFiller(seg);
    var v = hasVerb(seg);
    if (!v && prevVerb && seg.split(/\s+/).length <= 3 && seg) {
      seg = prevVerb + " " + seg;  /* list shorthand: "buy eggs, bread" */
      v = prevVerb;
    }
    if (v) prevVerb = v;
    if (!seg) continue;
    items.push({ text: seg.replace(/\s+/g, " ").trim(), due: due, priority: priority });
  }
  return items;
}

if (typeof module !== "undefined") module.exports = { parse: parse };
if (typeof require !== "undefined" && require.main === module) {
  var line = process.argv[2] || "buy milk and call mom tomorrow at five";
  console.log(JSON.stringify(parse(line, new Date(2026, 9, 11, 9, 0)), null, 1));
}
