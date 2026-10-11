# Café site (demo build)

A small static site: no frameworks, no external assets, no build step.
Part of epic t-20261011-e65f. Nothing here is a real business.

## How to view it

Serve the folder with any static server, then open the printed address:

```bash
cd projects/cafe-site
python3 -m http.server 8000     # then open http://localhost:8000/
```

Opening `index.html` directly from `file://` also works: browsers block
`fetch("menu.json")` from `file://`, so `app.js` falls back to an embedded
mirror of the menu and unhides `#menu-status` with a short "bundled copy"
note. `menu.json` remains the canonical data — `check-menu.py` fails loudly
if the embedded fallback ever drifts from it (re-embed by regenerating the
`/* FALLBACK-BEGIN */ … /* FALLBACK-END */` block in `app.js`).

## Files

| file | owner (task) | what it is |
|---|---|---|
| `index.html` | marcus-aurelius (t-…-0cff) | page skeleton, semantic sections |
| `styles.css` | marcus-aurelius (t-…-0cff) | visual system, one breakpoint |
| `menu.json` | barry (t-…-dbee) | all menu data — nothing is hardcoded in HTML |
| `app.js` | barry (t-…-dbee) | fetches `menu.json`, renders it into `<ul id="menu">` |
| `check-menu.py` | barry (t-…-dbee) | one-command data validation (stdlib python) |
| `test-app.js` | barry (t-…-dbee) | headless node harness for the renderer |

## menu.json schema

A JSON array of items; `app.js` renders one `<li class="menu-item">` per
entry (interface contract: bus message #1510fc30).

| field | type | rule |
|---|---|---|
| `name` | string | non-empty, unique |
| `price` | string | display string, e.g. `"3.50 €"` (not a number) |
| `description` | string | one plain sentence |
| `tags` | string[] | at least 2, non-empty strings |

Example:

```json
{ "name": "Espresso", "price": "1.20 €",
  "description": "Short, intense single shot from our house blend.",
  "tags": ["coffee", "classic", "hot"] }
```

If `fetch("menu.json")` fails or the data does not parse, `app.js` unhides
`<p id="menu-status">` with an explanation.

## Checks (one command each, no network)

```bash
python3 check-menu.py     # menu.json contract: fields, counts, no hardcoding
node --check app.js       # syntax
node test-app.js          # render + fetch-failure paths against a fake DOM
```

## Status

Copy, accessibility pass and the epic acceptance checklist are owned by
t-20261011-a3de (content child); placeholders in `index.html` are marked
for it. What is verified for the menu part is printed by the checks above.
