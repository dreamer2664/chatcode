#!/usr/bin/env node
/* Headless harness for app.js (task t-20261011-dbee).
   Stubs a minimal DOM, then proves both contract paths with zero network:

     node test-app.js

   Case 1: renderMenu() appends one <li class="menu-item"> per menu.json
           entry, with the contract structure (menu-item-head > name+price,
           menu-item-desc, menu-item-tags > li per tag), text from data.
   Case 2: a failing fetch unhides #menu-status with an actionable message
           and leaves #menu's existing content untouched.

   Exits 1 on any failed check. */
"use strict";
const fs = require("fs");
const path = require("path");

function fakeNode(tag) {
  return {
    tag, className: "", textContent: "", hidden: false, children: [],
    appendChild(child) { this.children.push(child); return child; }
  };
}
const menuEl = fakeNode("ul");
const statusEl = fakeNode("p");
statusEl.hidden = true;
const byId = { "menu": menuEl, "menu-status": statusEl };

global.document = {
  createElement: fakeNode,
  getElementById: (id) => byId[id] || null,
  readyState: "loading",
  addEventListener() {}
};

const app = require(path.join(__dirname, "app.js"));
const items = JSON.parse(fs.readFileSync(path.join(__dirname, "menu.json"), "utf8"));

let failures = 0;
function check(name, cond) {
  console.log((cond ? "ok   " : "FAIL ") + name);
  if (!cond) { failures++; }
}

app.renderMenu(items);
check(`renders one <li> per menu.json entry (${items.length})`,
      menuEl.children.length === items.length);
const first = menuEl.children[0];
check("item root is li.menu-item", first.className === "menu-item");
const head = first.children[0];
check("head is div.menu-item-head with name+price spans",
      head.className === "menu-item-head" &&
      head.children[0].className === "menu-item-name" &&
      head.children[1].className === "menu-item-price");
check("name and price text come from menu.json",
      head.children[0].textContent === items[0].name &&
      head.children[1].textContent === items[0].price);
const desc = first.children[1];
check("description is p.menu-item-desc from data",
      desc.className === "menu-item-desc" && desc.textContent === items[0].description);
const tags = first.children[2];
check("tags are ul.menu-item-tags with one <li> per tag (>= 2)",
      tags.className === "menu-item-tags" &&
      tags.children.length === items[0].tags.length &&
      tags.children[0].textContent === items[0].tags[0]);

global.fetch = () => Promise.reject(new TypeError("Failed to fetch"));
app.loadMenu().then(() => {
  check("fetch failure unhides #menu-status with a message",
        statusEl.hidden === false && statusEl.textContent.length > 0);
  check("status message is actionable (mentions menu.json + how to serve)",
        /menu\.json/.test(statusEl.textContent) && /http\.server/.test(statusEl.textContent));
  check("menu content survives the failure path",
        menuEl.children.length === items.length);
  console.log(failures ? `FAILURES: ${failures}` : "OK: render + failure paths verified");
  process.exit(failures ? 1 : 0);
});
