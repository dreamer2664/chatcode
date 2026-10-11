"use strict";
/* offline shell: cache-first for the app's own files */
var SHELL = ["index.html", "parser.js", "export.js", "store.js", "app.js", "manifest.json"];
self.addEventListener("install", function (e) {
  e.waitUntil(caches.open("voice-todo-v1").then(function (c) { return c.addAll(SHELL); }));
});
self.addEventListener("fetch", function (e) {
  e.respondWith(caches.match(e.request).then(function (hit) {
    return hit || fetch(e.request).then(function (res) {
      var cp = res.clone();
      caches.open("voice-todo-v1").then(function (c) { c.put(e.request, cp); });
      return res;
    });
  }));
});
