/* café-site menu renderer — task t-20261011-dbee, interface contract bus #1510fc30.
   Fetches menu.json and fills <ul id="menu">; on any fetch/parse failure it
   unhides <p id="menu-status"> with a clear message (file:// blocks fetch). */
"use strict";
(function () {
  /* file:// fallback: a byte-for-byte mirror of menu.json, embedded so the
     menu still renders when the browser blocks fetch (browsers do on
     file://). menu.json stays canonical; check-menu.py FAILS if these drift. */
  var FALLBACK_MENU = /* FALLBACK-BEGIN */
  [
    {
      "name": "Espresso",
      "price": "1.20 €",
      "description": "Short, intense single shot from our house blend, roasted in small batches each week.",
      "tags": [
        "coffee",
        "classic",
        "hot"
      ]
    },
    {
      "name": "Cappuccino",
      "price": "1.80 €",
      "description": "Espresso under velvety steamed-milk foam; dusted with cocoa on request.",
      "tags": [
        "coffee",
        "breakfast",
        "hot"
      ]
    },
    {
      "name": "Caffè macchiato",
      "price": "1.30 €",
      "description": "Espresso stained with a spoonful of warm milk foam.",
      "tags": [
        "coffee",
        "hot"
      ]
    },
    {
      "name": "Caffè shakerato",
      "price": "3.00 €",
      "description": "Double espresso shaken over ice until frothy; served chilled in a coupe glass.",
      "tags": [
        "coffee",
        "cold",
        "summer"
      ]
    },
    {
      "name": "Cornetto alla crema",
      "price": "1.60 €",
      "description": "Butter cornetto filled with vanilla custard, baked in-house every morning.",
      "tags": [
        "breakfast",
        "sweet",
        "bakery"
      ]
    },
    {
      "name": "Maritozzo con panna",
      "price": "3.00 €",
      "description": "Soft Roman brioche bun split open and filled with fresh whipped cream.",
      "tags": [
        "sweet",
        "bakery",
        "local specialty"
      ]
    },
    {
      "name": "Spremuta d'arancia",
      "price": "3.50 €",
      "description": "Freshly squeezed orange juice, pressed to order and never from concentrate.",
      "tags": [
        "cold",
        "fresh",
        "vegan"
      ]
    },
    {
      "name": "Tramezzino tonno e carciofini",
      "price": "3.80 €",
      "description": "Soft-crustless sandwich with tuna and artichoke cream; made fresh daily.",
      "tags": [
        "savoury",
        "lunch"
      ]
    },
    {
      "name": "Tiramisù",
      "price": "4.50 €",
      "description": "Espresso-soaked savoiardi layered with mascarpone cream and dark cocoa.",
      "tags": [
        "sweet",
        "dessert",
        "classic"
      ]
    },
    {
      "name": "Ciambellina al vino",
      "price": "1.50 €",
      "description": "Traditional ring-shaped wine biscuit; light, crisp, and made for dipping.",
      "tags": [
        "sweet",
        "bakery",
        "vegan"
      ]
    }
  ]
  /* FALLBACK-END */;

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
        renderMenu(FALLBACK_MENU);
        showStatus("Showing the menu bundled with the site: the browser blocked " +
          "fetching menu.json (expected on file://). To serve the live data, " +
          "see README.md, e.g. run `python3 -m http.server 8000` inside " +
          "projects/cafe-site/ and open the printed address.");
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
