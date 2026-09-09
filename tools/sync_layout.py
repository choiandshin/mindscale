#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Copy the shared header and footer from index.html into every other page.

index.html is the master. Everything between

    <!-- HEADER:START -->  ...  <!-- HEADER:END -->
    <!-- FOOTER:START -->  ...  <!-- FOOTER:END -->

is copied verbatim into the matching block in the other pages, except that the
"is-active" marker on the nav is moved to whichever page is being written.

Edit the nav or footer once in index.html, run this, and all seven pages agree.

Usage:  python3 tools/sync_layout.py
        python3 tools/sync_layout.py --check    # report differences, change nothing
"""
import argparse
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MASTER = "index.html"
BLOCKS = ("HEADER", "FOOTER")


def pages():
    return sorted(f for f in os.listdir(ROOT) if f.endswith(".html"))


def read(name):
    with io.open(os.path.join(ROOT, name), encoding="utf-8") as f:
        return f.read()


def write(name, text):
    with io.open(os.path.join(ROOT, name), "w", encoding="utf-8") as f:
        f.write(text)


def extract(html, block, filename):
    start, end = "<!-- %s:START -->" % block, "<!-- %s:END -->" % block
    if html.count(start) != 1 or html.count(end) != 1 or html.index(start) > html.index(end):
        sys.exit("%s: expected one ordered pair of %s markers" % (filename, block))
    return html.split(start, 1)[1].split(end, 1)[0]


def replace(html, block, body):
    start, end = "<!-- %s:START -->" % block, "<!-- %s:END -->" % block
    head, rest = html.split(start, 1)
    _, tail = rest.split(end, 1)
    return head + start + body + end + tail


def retarget_nav(header, page):
    """Move class="is-active" / aria-current to this page's nav link."""
    header = header.replace(' class="is-active" aria-current="page"', "")
    return re.sub(
        r'(<a href="%s")' % re.escape(page),
        r'\1 class="is-active" aria-current="page"',
        header,
        count=1,
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="report differences without writing")
    args = ap.parse_args()

    master = read(MASTER)
    parts = {b: extract(master, b, MASTER) for b in BLOCKS}
    # Validate every page before changing any, including in --check mode.
    for page in pages():
        for block in BLOCKS:
            extract(read(page), block, page)

    changed = []
    for page in pages():
        html = original = read(page)
        for block in BLOCKS:
            body = parts[block]
            if block == "HEADER":
                body = retarget_nav(body, page)
            html = replace(html, block, body)
        if html != original:
            changed.append(page)
            if not args.check:
                write(page, html)

    if not changed:
        print("All %d pages already in sync." % len(pages()))
        return 0
    if args.check:
        print("Out of sync: " + ", ".join(changed))
        return 1
    print("Synced header and footer into: " + ", ".join(changed))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
