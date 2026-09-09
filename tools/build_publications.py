#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render data/publications.json into the publication list inside publications.html.

The generated block is written between the two marker comments:

    <!-- PUBLICATIONS:START -->  ...generated...  <!-- PUBLICATIONS:END -->

Everything outside the markers is hand-edited and left untouched.

Usage:  python3 tools/build_publications.py
"""
import io
import argparse
import html
from html.parser import HTMLParser
import json
import os
import sys
import re
import tempfile
from urllib.parse import urlsplit

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


class CitationHTML(HTMLParser):
    """Keep the citation's small formatting vocabulary; never execute markup."""
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.parts = []

    def handle_starttag(self, tag, attrs):
        allowed = {"me": '<span class="me">', "em": "<em>", "strong": "<strong>"}
        self.parts.append(allowed.get(tag, html.escape(self.get_starttag_text())))

    def handle_endtag(self, tag):
        self.parts.append({"me": "</span>", "em": "</em>", "strong": "</strong>"}.get(
            tag, html.escape("</%s>" % tag)))

    def handle_data(self, data):
        self.parts.append(html.escape(data, quote=False))

    def handle_entityref(self, name):
        self.parts.append("&%s;" % name)

    def handle_charref(self, name):
        self.parts.append("&#%s;" % name)


def citation(value):
    parser = CitationHTML()
    parser.feed(value)
    parser.close()
    return "".join(parser.parts)


def plain(value):
    return html.unescape(re.sub(r"<[^>]+>", "", value))


def scholarly_data(pubs):
    articles = []
    for p in pubs:
        if p["type"] not in ("journal", "korean", "proceedings") or p["group"] == "Under review":
            continue
        article = {"@type": "ScholarlyArticle", "name": plain(p["title"]),
                   "datePublished": str(p["year"]),
                   "inLanguage": "ko" if p["type"] == "korean" else "en"}
        if p.get("doi"):
            article["url"] = p["doi"]
            article["identifier"] = p["doi"]
        if p.get("title_en"):
            article["alternateName"] = plain(p["title_en"])
        articles.append(article)
    # Escape '<' so external metadata cannot terminate this script element.
    return json.dumps({"@context": "https://schema.org", "@graph": articles},
                      ensure_ascii=False).replace("<", "\\u003c")


def sort_key(p):
    """Under review first, then newest year first, preserving file order within a year."""
    return (0 if p["group"] == "Under review" else 1, -int(p.get("year", 0)))


def render(pubs):
    pubs = sorted(pubs, key=sort_key)
    out, current = [], None
    for p in pubs:
        if p["group"] != current:
            current = p["group"]
            out.append('        <h2 class="pub-year">%s</h2>' % html.escape(current))

        authors = citation(p["authors"])
        if p["type"] not in TYPE_LABEL:
            raise ValueError("Unknown publication type: %s" % p["type"])

        title_attr = ' lang="ko"' if p["type"] == "korean" else ""
        bits = ['        <div class="pub" data-type="%s">' % p["type"],
                '          <span class="pub-title"%s>%s</span>' % (title_attr, citation(p["title"]))]
        if p.get("title_en"):
            bits.append('          <span class="pub-title-en">%s</span>' % citation(p["title_en"]))
        bits.append('          <span class="pub-authors">%s</span>' % authors)
        if p.get("venue"):
            bits.append('          <span class="pub-venue">%s</span>' % citation(p["venue"]))

        links = []
        if p.get("doi"):
            if urlsplit(p["doi"]).scheme not in ("https", "http") or not urlsplit(p["doi"]).netloc:
                raise ValueError("Publication link must be an absolute HTTP(S) URL")
            label = "Springer" if "link.springer.com" in p["doi"] else "DOI"
            links.append('<a href="%s" rel="noopener">%s</a>' % (html.escape(p["doi"], quote=True), label))
        if p.get("note"):
            links.append('<span class="tag">%s</span>' % citation(p["note"]))
        if links:
            bits.append('          <div class="pub-links">%s</div>' % "".join(links))
        bits.append("        </div>")
        out.append("\n".join(bits))
    out.append('        <script type="application/ld+json">%s</script>' % scholarly_data(pubs))
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="report drift without writing")
    args = ap.parse_args()
    with io.open(DATA, encoding="utf-8") as f:
        pubs = json.load(f)["publications"]

    with io.open(PAGE, encoding="utf-8") as f:
        html = f.read()

    if html.count(START) != 1 or html.count(END) != 1 or html.index(START) > html.index(END):
        sys.exit("Expected one ordered pair of publication markers")

    head, rest = html.split(START, 1)
    _, tail = rest.split(END, 1)
    new = head + START + "\n" + render(pubs) + "\n        " + END + tail

    if new == html:
        print("publications.html already up to date (%d entries)" % len(pubs))
        return 0

    if args.check:
        print("publications.html is out of date; run python3 tools/build_publications.py")
        return 1

    tmp = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=ROOT, delete=False) as f:
            tmp = f.name
            f.write(new)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, PAGE)
    finally:
        if tmp and os.path.exists(tmp):
            os.unlink(tmp)
    print("publications.html rebuilt with %d entries" % len(pubs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
