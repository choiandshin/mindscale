#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render data/publications.json into the publication list inside publications.html.

The generated block is written between the two marker comments:

    <!-- PUBLICATIONS:START -->  ...generated...  <!-- PUBLICATIONS:END -->

Everything outside the markers is hand-edited and left untouched.

Usage:  python3 tools/build_publications.py
"""
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "publications.json")
PAGE = os.path.join(ROOT, "publications.html")

START = "<!-- PUBLICATIONS:START -->"
END = "<!-- PUBLICATIONS:END -->"

TYPE_LABEL = {
    "journal": "Journal article",
    "chapter": "Book chapter",
    "proceedings": "Conference paper",
    "report": "Technical report",
    "korean": "Korean-language",
    "review": "Under review",
}


def sort_key(p):
    """Under review first, then newest year first, preserving file order within a year."""
    return (0 if p["group"] == "Under review" else 1, -int(p.get("year", 0)))


def render(pubs):
    pubs = sorted(pubs, key=sort_key)
    out, current = [], None
    for p in pubs:
        if p["group"] != current:
            current = p["group"]
            out.append('        <h2 class="pub-year">%s</h2>' % current)

        authors = p["authors"].replace("<me>", '<span class="me">').replace("</me>", "</span>")

        title_attr = ' lang="ko"' if p["type"] == "korean" else ""
        bits = ['        <div class="pub" data-type="%s">' % p["type"],
                '          <span class="pub-title"%s>%s</span>' % (title_attr, p["title"])]
        if p.get("title_en"):
            bits.append('          <span class="pub-title-en">%s</span>' % p["title_en"])
        bits.append('          <span class="pub-authors">%s</span>' % authors)
        if p.get("venue"):
            bits.append('          <span class="pub-venue">%s</span>' % p["venue"])

        links = []
        if p.get("doi"):
            label = "Springer" if "link.springer.com" in p["doi"] else "DOI"
            links.append('<a href="%s" rel="noopener">%s</a>' % (p["doi"], label))
        if p.get("note"):
            links.append('<span class="tag">%s</span>' % p["note"])
        if links:
            bits.append('          <div class="pub-links">%s</div>' % "".join(links))
        bits.append("        </div>")
        out.append("\n".join(bits))
    return "\n".join(out)


def main():
    with io.open(DATA, encoding="utf-8") as f:
        pubs = json.load(f)["publications"]

    with io.open(PAGE, encoding="utf-8") as f:
        html = f.read()

    if START not in html or END not in html:
        sys.exit("markers not found in publications.html")

    head, rest = html.split(START, 1)
    _, tail = rest.split(END, 1)
    new = head + START + "\n" + render(pubs) + "\n        " + END + tail

    if new == html:
        print("publications.html already up to date (%d entries)" % len(pubs))
        return 0

    with io.open(PAGE, "w", encoding="utf-8") as f:
        f.write(new)
    print("publications.html rebuilt with %d entries" % len(pubs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
