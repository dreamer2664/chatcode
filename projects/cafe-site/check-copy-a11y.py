#!/usr/bin/env python3
"""Copy + accessibility checks for projects/cafe-site (t-20261011-a3de).

Answers the parts of the café epic's acceptance checklist that can be verified
without a browser, with one command from anywhere:

    python3 projects/cafe-site/check-copy-a11y.py

Exit 0 = all checks pass. What it does NOT do is render pixels: layout at
360px/1440px is reasoned about statically (viewport meta, breakpoints, fixed
widths), and that limit is printed in the report rather than hidden.

Stdlib only. Reads the three files that need no server: index.html, styles.css,
menu.json.
"""
from __future__ import annotations

import argparse
import html.parser
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FAILS: list[str] = []
NOTES: list[str] = []


def check(cond: bool, ok: str, bad: str) -> None:
    print(("PASS  " if cond else "FAIL  ") + (ok if cond else bad))
    if not cond:
        FAILS.append(bad)


def note(text: str) -> None:
    print(f"      note: {text}")
    NOTES.append(text)


class Parser(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.stack: list[str] = []
        self.unbalanced: list[str] = []
        self.ids: set[str] = set()
        self.images: list[dict] = []          # every <svg> and <img>
        self.headings: list[str] = []
        self.labels: dict[str, str] = {}      # id -> labelledby target
        self.roles: dict[str, str] = {}
        self._in_svg = 0
        self._svg_has_title = False
        self._svg_attribs: dict = {}
        self._svg_id = None
        self._heading: str | None = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag not in ("meta", "link", "br", "img", "hr", "input", "path",
                       "circle", "line", "source", "use"):
            self.stack.append(tag)
        if a.get("id"):
            self.ids.add(a["id"])
            if a.get("role"):
                self.roles[a["id"]] = a["role"]
            if a.get("aria-labelledby"):
                self.labels[a["id"]] = a["aria-labelledby"]
        if tag == "svg":
            self._in_svg = 1
            self._svg_has_title = False
            self._svg_attribs = a
            self._svg_id = a.get("id")
        if tag == "title" and self._in_svg:
            self._svg_has_title = True
        if tag == "img":
            self.images.append({"tag": "img", "alt": a.get("alt"), "attrs": a})
        if tag in ("h1", "h2", "h3", "h4"):
            self._heading = tag
            self.headings.append(tag)

    def handle_endtag(self, tag):
        if tag == "svg":
            self._in_svg = 0
            self.images.append({"tag": "svg", "has_title": self._svg_has_title,
                                "attrs": self._svg_attribs, "id": self._svg_id})
        if tag in ("h1", "h2", "h3", "h4"):
            self._heading = None
        if self.stack and self.stack[-1] == tag:
            self.stack.pop()
        elif tag in self.stack:
            self.unbalanced.append(tag)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--menu", default=os.path.join(HERE, "menu.json"),
                    help="path to menu.json (defaults to the copy beside this script)")
    args = ap.parse_args()
    html_text = open(os.path.join(HERE, "index.html"), encoding="utf-8").read()
    css = open(os.path.join(HERE, "styles.css"), encoding="utf-8").read()
    menu = None
    if os.path.exists(args.menu):
        menu = json.load(open(args.menu, encoding="utf-8"))

    p = Parser()
    p.feed(html_text)

    print("── copy (t-a3de: real text, no placeholders) ──")
    check("Placeholder" not in html_text,
          "no 'Placeholder' strings remain",
          f"'Placeholder' still appears {html_text.count('Placeholder')}x")
    check("TODO(t-20261011-a3de)" not in html_text,
          "no outstanding content TODOs",
          "content TODOs remain")
    check(re.search(r"<h1[^>]*>Bricco</h1>", html_text) is not None,
          "café name is real copy ('Bricco')",
          "café name is not set")
    about_block = re.search(r'<section id="about".*?</section>', html_text, re.S).group(0)
    check(about_block.count("<p>") >= 3,
          "about section has three paragraphs",
          "about section has fewer than three paragraphs")
    check(re.search(r"Mon–Fri", html_text) is not None
          and re.search(r"Sun closed", html_text) is not None,
          "hours are real and include a closed day",
          "hours copy missing")
    check("invented address for a fictional café" in html_text,
          "address is explicitly labelled fictional",
          "address is not marked as fictional")

    print("\n── accessibility ──")
    check(len(p.headings) >= 1 and p.headings[0] == "h1",
          "document starts with an h1",
          "first heading is not an h1")
    order_ok = all(p.headings[i] <= p.headings[i + 1]
                   for i in range(len(p.headings) - 1))
    check(order_ok, f"heading levels never skip downward ({' > '.join(p.headings)})",
          f"heading order jumps: {p.headings}")
    check('id="cafe-name"' in html_text and 'id="menu-heading"' in html_text
          and 'id="about-heading"' in html_text and 'id="hours-heading"' in html_text,
          "every section is labelled by its own heading",
          "a section heading id is missing")
    check(all('aria-labelledby' in html_text.split(f'id="{sid}"')[1][:120]
              for sid in ("menu-section", "about", "hours-location")),
          "sections reference their heading via aria-labelledby",
          "aria-labelledby missing on a section")

    # every inline SVG image needs a programmatic name (the SVG equivalent of alt)
    svgs = [i for i in p.images if i["tag"] == "svg"]
    svg_named = all(s["has_title"] and s["attrs"].get("role") == "img" for s in svgs)
    check(svgs and svg_named,
          f"every inline SVG has role=img and a <title> ({len(svgs)} svg)",
          "an inline SVG lacks a <title> or role=img")
    imgs = [i for i in p.images if i["tag"] == "img"]
    check(all(i["alt"] is not None for i in imgs),
          f"every <img> has an alt attribute ({len(imgs)} img)",
          "an <img> has no alt")

    # live region for the menu load/error message
    check(p.roles.get("menu-status") == "status",
          "#menu-status is a polite live region (role=status)",
          "#menu-status is not a live region, so a load failure is silent to screen readers")

    # keyboard path
    check('class="skip-link"' in html_text and 'href="#menu-section"' in html_text,
          "skip link present and targets the menu",
          "no skip link")
    check(":focus-visible" in css and "outline:" in css,
          "visible focus styling for keyboard users",
          "no visible focus styling")
    check(".skip-link:focus" in css,
          "skip link becomes visible when focused",
          "skip link has no focus style")

    print("\n── contrast (WCAG AA, computed from the palette) ──")

    def lum(h):
        h = h.lstrip("#")
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
        f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4  # noqa: E731
        return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)

    def ratio(fg, bg):
        la, lb = lum(fg), lum(bg)
        hi, lo = max(la, lb), min(la, lb)
        return round((hi + 0.05) / (lo + 0.05), 2)

    palette = dict(re.findall(r"(--clr-[a-z0-9-]+):\s*(#[0-9a-fA-F]{3,6})", css))
    pairs = [
        ("body text", palette.get("--clr-ink"), palette.get("--clr-bg")),
        ("muted text", palette.get("--clr-ink-soft"), palette.get("--clr-bg")),
        ("accent text", palette.get("--clr-accent"), palette.get("--clr-bg")),
        ("text on accent", palette.get("--clr-accent-ink"), palette.get("--clr-accent")),
        ("tag text", palette.get("--clr-tag-ink"), palette.get("--clr-tag-bg")),
    ]
    worst = 99.0
    for name, fg, bg in pairs:
        if not (fg and bg):
            check(False, "", f"palette is missing a colour for {name}")
            continue
        r = ratio(fg, bg)
        worst = min(worst, r)
        check(r >= 4.5, f"{name}: {r}:1 ({fg} on {bg})", f"{name} is {r}:1, below 4.5:1")
    note(f"worst pair {worst}:1; AA needs 4.5:1 for body text, 3:1 for large text")

    print("\n── no external assets (epic rule) ──")
    refs = re.findall(r'(?:src|href)\s*=\s*"([^"]+)"', html_text)
    external = [u for u in refs if u.startswith(("http://", "https://", "//"))]
    check(not external, "no external URLs referenced in HTML", f"external refs: {external}")
    urls = re.findall(r"url\(\s*[\"']?([^)\"']+)", css)
    check(not urls, "no url() fetches in CSS", f"css urls: {urls}")
    check("@import" not in css, "no @import in CSS", "@import present")
    fonts = re.findall(r"--font-[a-z]+:\s*([^;]+);", css)
    generic = ("system-ui", "serif", "sans-serif", "monospace")
    check(fonts and all(any(g in f for g in generic) for f in fonts),
          f"font stacks end in generic families ({len(fonts)} declared)",
          "a font stack has no generic fallback")

    print("\n── usability at 360px / 1440px (static reasoning, not rendered) ──")
    check('name="viewport"' in html_text and "width=device-width" in html_text,
          "viewport meta present for small screens",
          "no viewport meta")
    bps = [b for b in re.findall(r"@media[^{]+", css) if "width" in b]
    check(len(bps) == 1 and "640px" in bps[0],
          f"one layout breakpoint at 640px ({bps[0].strip()})",
          f"unexpected layout breakpoints: {bps}")
    fixed = [int(n) for n in re.findall(r"(?:^|[;\s])width:\s*(\d+)px", css)]
    wide = [w for w in fixed if w > 360]
    check(not wide, f"no fixed width above 360px ({len(fixed)} fixed widths checked)",
          f"fixed widths wider than 360px: {wide}")
    check("max-width" in css, "containers use max-width (fluid)", "no max-width in CSS")
    note("pixel-level rendering at 360/1440 is NOT verified here: this sandbox has no "
         "browser. What is verified: fluid width, one breakpoint, no oversized fixed widths.")

    print("\n── menu is data-driven (shared with the menu child) ──")
    if menu is None:
        note(f"menu.json not found at {args.menu} — data-driven checks SKIPPED "
             "(they are covered by the menu child's own check-menu.py; pass "
             "--menu <path> to run them here too)")
    else:
        check(isinstance(menu, list) and len(menu) >= 8,
              f"menu.json holds {len(menu)} items",
              "menu.json is not a list of >= 8 items")
        hard = [i["name"] for i in menu if i["name"] in html_text]
        check(not hard, "no menu item name is hardcoded in index.html", f"hardcoded: {hard}")
    check("<ul id=\"menu\" class=\"menu-list\"></ul>" in re.sub(r"\s+", " ", html_text),
          "#menu is still empty in the HTML (filled by app.js)",
          "#menu is not empty in the HTML")

    print()
    if FAILS:
        print(f"{len(FAILS)} check(s) FAILED:")
        for f in FAILS:
            print(f"  - {f}")
        return 1
    print("ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
