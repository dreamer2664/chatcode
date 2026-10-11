# Café site — acceptance evidence (t-20261011-a3de)

Owner of this log: **scott**. Scope of the child task: real copy, an
accessibility pass, and the run-through of the parent epic's acceptance
checklist (`t-20261011-e65f`).

Everything below was run on this branch, which is `main` + this child's copy
and a11y changes. Commands are copy-pasteable from the repo root. Outputs are
verbatim.

> **Status of the epic: NOT ready to close yet.** One acceptance item cannot be
> verified until the menu child lands (#10), and one is a real product gap that
> needs a decision by the menu child's owner — item 1 below. Per the task, that
> is reported as not verified rather than passed.

---

## How to view the site

```bash
cd projects/cafe-site
python3 -m http.server 8000        # then open http://localhost:8000/
```

Opening `index.html` by double-click works for the page itself (HTML and CSS
are local), but the **menu will not appear** — see item 1. Serving the folder
is the supported way to see the site complete.

---

## The parent epic's checklist, item by item

### 1. Opens offline from `file://` with zero network requests

**Split verdict — this is the one item that is not simply "pass".**

*Zero network requests: PASS (verified).* No external resources are referenced
anywhere in the two shipped files:

```console
$ python3 projects/cafe-site/check-copy-a11y.py | sed -n '/no external assets/,/font stacks/p'
── no external assets (epic rule) ──
PASS  no external URLs referenced in HTML
PASS  no url() fetches in CSS
PASS  no @import in CSS
PASS  font stacks end in generic families (2 declared)
```

*Menu visible from `file://`: PASS (verified, since this document was first
written).* Originally this was the one failing item: `app.js` rendered the menu
via `fetch("menu.json")`, which browsers refuse on the `file://` scheme, and I
filed `t-20261011-7a7e` rather than patching the menu child's file (R8). The
menu child then landed the fix in PR #19 (`a21a147`): `app.js` now embeds a
mirror of `menu.json` between explicit markers and renders it when the fetch
fails, so a double-clicked page shows the real menu — and `check-menu.py`
fails loudly if that mirror ever drifts from `menu.json`.

I verified this myself in the review of #19, independently of the child's own
checker: I parsed the marker block, confirmed 10/10 items object-identical to
`menu.json`, then perturbed one price inside the mirror and re-ran
`check-menu.py` — exit 1, "app.js FALLBACK_MENU differs from menu.json". No
browser exists in my sandbox either, so the same caveat applies as everywhere
in this file: this is the code path plus a red/green drift test, not a
screenshot. `t-20261011-7a7e` closed on that merge.

### 2. Every menu item comes from `menu.json`, none hardcoded in HTML

**PASS** — verified twice, by the menu child's own check and by mine against
his data:

```console
$ python3 projects/cafe-site/check-menu.py            # menu child's check (from #10)
OK: 10 items, all with name/price/description/tags, >=2 tags each, prices as display strings, none hardcoded in index.html

$ python3 projects/cafe-site/check-copy-a11y.py --menu /path/to/menu.json | tail -4
PASS  menu.json holds 10 items
PASS  no menu item name is hardcoded in index.html
PASS  #menu is still empty in the HTML (filled by app.js)
```

### 3. Usable at 360px and 1440px

**PASS (static evidence only — see the caveat).**

```console
$ python3 projects/cafe-site/check-copy-a11y.py | sed -n '/360px/,/pixel-level/p'
── usability at 360px / 1440px (static reasoning, not rendered) ──
PASS  viewport meta present for small screens
PASS  one layout breakpoint at 640px (@media (max-width: 640px))
PASS  no fixed width above 360px (0 fixed widths checked)
PASS  containers use max-width (fluid)
```

The layout is a single fluid column with `max-width: 60rem` (960px at default
type size) and one breakpoint at 640px, so 360px is the tight case and 1440px
is the comfortable case; there is no fixed-width element that could force
horizontal scrolling at either end.

**Caveat, stated rather than hidden:** this sandbox has no browser, so the
pixels were **not** looked at. What is verified is the CSS properties that
decide the outcome. A human opening the page at both widths is the real
confirmation.

### 4. Keyboard-navigable with visible focus

**PASS.**

```console
$ python3 projects/cafe-site/check-copy-a11y.py | sed -n '/accessibility/,/^$/p'
── accessibility ──
PASS  document starts with an h1
PASS  heading levels never skip downward (h1 > h2 > h2 > h2)
PASS  every section is labelled by its own heading
PASS  sections reference their heading via aria-labelledby
PASS  every inline SVG has role=img and a <title> (1 svg)
PASS  every <img> has an alt attribute (0 img)
PASS  #menu-status is a polite live region (role=status)
PASS  skip link present and targets the menu
PASS  visible focus styling for keyboard users
PASS  skip link becomes visible when focused
```

Added by this child: a **skip link** ("Skip to the menu", hidden until focused,
`solid` 3px accent outline via the existing `:focus-visible` rule), and
`role="status"` on `#menu-status` so a screen reader is told when the menu
fails to load instead of the failure being silent. Both are in files this child
owns the change for; the menu child's DOM contract (ids, element shapes) is
unchanged — `#menu` is still empty in the HTML, `#menu-status` still starts
hidden.

Honest limit: **menu items are the only future interactive content and they do
not exist yet in this branch** (they arrive with #10), so keyboard navigation
of the rendered list cannot be walked end-to-end here. The page's own keyboard
path — skip link, focus visibility, heading structure — is verified.

### 5. No external fonts/images/scripts

**PASS.** Same evidence as item 1: no `http://`, `https://` or `//` references
in HTML, no `url()` and no `@import` in CSS, every font stack ends in a generic
family (`system-ui`, `Georgia`), and the only image is an inline `<svg>` whose
steam-and-cup artwork is drawn in the document itself.

### 6. README says how to view it

**PASS pending #10.** `projects/cafe-site/README.md` arrives with the menu
child's PR #10, which is not merged yet; on this branch there is no README to
check, so this item is **not verified here**. The menu child's README was
reviewed and does carry viewing instructions (I reviewed #10 and checked that
it explains serving the folder and the `file://` limitation). The "How to view"
section at the top of this file covers the same ground in the meantime.

---

## Accessibility detail worth recording

Contrast was recomputed from the palette rather than trusted from the comment
in `styles.css`:

```console
$ python3 projects/cafe-site/check-copy-a11y.py | sed -n '/contrast/,/worst pair/p'
PASS  body text: 14.61:1 (#2b211a on #faf6f0)
PASS  muted text: 7.34:1 (#5c4f44 on #faf6f0)
PASS  accent text: 7.56:1 (#8a3324 on #faf6f0)
PASS  text on accent: 8.14:1 (#ffffff on #8a3324)
PASS  tag text: 8.69:1 (#4a3b2c on #efe6d8)
      note: worst pair 7.34:1; AA needs 4.5:1 for body text, 3:1 for large text
```

`prefers-reduced-motion: reduce` is respected in `styles.css`; the skip link's
own transition, if any is added later, must keep that in mind.

## Copy

Real copy replaced every placeholder (`grep -c Placeholder index.html` → 0):
the café is **Bricco**, a fictional coffee house, with an invented address
explicitly labelled as invented, real opening hours including a closed day, and
five short paragraphs of voice. The footer states plainly that nothing here is
a real business — the epic's "no real business involved" rule.

---

## Follow-ups (not fixed here, on purpose)

1. **`file://` menu rendering — RESOLVED.** Filed as `t-20261011-7a7e` and
   fixed by the menu child in PR #19 (`a21a147`) with the embedded-mirror
   option (the first alternative above: keeps the epic's literal criterion).
   Closed with the merge; the verification is recorded in item 1 above.
2. **Merge order — RESOLVED.** The stale PR #10 was closed rather than merged;
   the menu work landed as PR #19 as five pure additions, and this document's
   PR was rebased onto `main` *after* that merge, so nothing here can revert
   the menu child's files and nothing of mine is reverted by them.
