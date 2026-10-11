/* café-site menu renderer — task t-20261011-dbee, interface contract bus #1510fc30.
   Fetches menu.json and fills <ul id="menu">; on any fetch/parse failure it
   unhides <p id="menu-status"> with a clear message (file:// blocks fetch). */
"use strict";
(function () {
  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) { node.className = className; }
    if (text !== undefined) { node.textContent = text; }
    return node;
  }

  function menuItemNode(item) {
    var li = el("li", "menu-item");
    var head = el("div", "menu-item-head");
    head.appendChild(el("span", "menu-item-name", item.name));
    head.appendChild(el("span", "menu-item-price", item.price));
    li.appendChild(head);
    li.appendChild(el("p", "menu-item-desc", item.description));
    var tags = el("ul", "menu-item-tags");
    item.tags.forEach(function (tag) {
      tags.appendChild(el("li", null, tag));
    });
    li.appendChild(tags);
    return li;
  }

  function renderMenu(items) {
    var list = document.getElementById("menu");
    if (!list) { return; }
    list.textContent = "";
    items.forEach(function (item) {
      list.appendChild(menuItemNode(item));
    });
  }

  function showStatus(message) {
    var status = document.getElementById("menu-status");
    if (!status) { return; }
    status.hidden = false;
    status.textContent = message;
  }

  function loadMenu() {
    return fetch("menu.json", { cache: "no-store" })
      .then(function (response) {
        if (!response.ok) { throw new Error("HTTP " + response.status); }
        return response.json();
      })
      .then(function (items) {
        renderMenu(items);
      })
      .catch(function () {
        showStatus("The menu could not be loaded from menu.json. If you opened " +
          "index.html directly (file://), your browser blocks the fetch; serve " +
          "the folder instead — see README.md, e.g. run " +
          "`python3 -m http.server 8000` inside projects/cafe-site/ and open " +
          "the printed address.");
      });
  }

  var isNodeTest = (typeof module !== "undefined" && module.exports);
  if (!isNodeTest) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", loadMenu);
    } else {
      loadMenu();
    }
  }
  if (isNodeTest) {
    module.exports = {
      menuItemNode: menuItemNode,
      renderMenu: renderMenu,
      showStatus: showStatus,
      loadMenu: loadMenu
    };
  }
})();
