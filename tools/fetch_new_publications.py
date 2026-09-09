#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Look for new publications on Crossref and add them to data/publications.json.

Queries Crossref for works authored by the names in AUTHORS, keeps anything whose
DOI is not already in the data file, formats it in the site's citation style, and
writes it back. Then tools/build_publications.py re-renders publications.html.

Nothing is overwritten: existing entries are never modified, only new DOIs are added.
New entries are marked "needs_review": true so you can spot them in the pull request.

Usage:
    python3 tools/fetch_new_publications.py            # write changes
    python3 tools/fetch_new_publications.py --dry-run  # report only
"""
import argparse
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "publications.json")

# --- configuration -----------------------------------------------------------
# Crossref is polite to requests that identify themselves. Use a real address.
MAILTO = "hshinedu@sogang.ac.kr"

# The author to match. Crossref spells names inconsistently, so we match on the
# normalised "given family" string against these variants.
AUTHOR_VARIANTS = [
    "hyo jeong shin",
    "hyojeong shin",
    "h j shin",
    "hyo j shin",
]

# Only consider works published on or after this date.
SINCE = "2022-01-01"

# Journals whose articles are written in Korean; used to tag entries as "korean".
KOREAN_CONTAINERS = [
    "korean educational research association",
    "journal of educational technology",
    "korean association for educational information and media",
    "korean association of computer education",
    "korean journal of general education",
    "korean journal of educational research",
    "journal of educational evaluation",
    "asian journal of education",
]

TYPE_MAP = {
    "journal-article": "journal",
    "book-chapter": "chapter",
    "proceedings-article": "proceedings",
    "posted-content": "review",
    "report": "report",
    "reference-entry": "chapter",
    "other": "journal",
}
# -----------------------------------------------------------------------------


def norm(s):
    return re.sub(r"[^a-z ]", "", (s or "").lower()).strip()


def crossref(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": "MindScale-site-updater/1.0 (mailto:%s)" % MAILTO,
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.load(r)


def fetch_candidates():
    """Return Crossref items plausibly authored by Dr. Shin."""
    seen, items = set(), []
    for variant in ("Hyo Jeong Shin", "Hyo J. Shin"):
        params = urllib.parse.urlencode({
            "query.author": variant,
            "filter": "from-pub-date:" + SINCE,
            "rows": "100",
            "select": "DOI,title,original-title,author,container-title,issued,volume,issue,page,type",
            "mailto": MAILTO,
        })
        try:
            data = crossref("https://api.crossref.org/works?" + params)
        except Exception as exc:              # network hiccup: fail soft
            print("warning: Crossref query failed for %r: %s" % (variant, exc), file=sys.stderr)
            continue
        for it in data.get("message", {}).get("items", []):
            doi = (it.get("DOI") or "").lower()
            if doi and doi not in seen:
                seen.add(doi)
                items.append(it)
        time.sleep(1)
    return items


def is_ours(item):
    for a in item.get("author", []) or []:
        full = norm("%s %s" % (a.get("given", ""), a.get("family", "")))
        if full in AUTHOR_VARIANTS:
            return True
    return False


def format_authors(item):
    """Render the author list in the site's style, wrapping Dr. Shin in <me>."""
    out = []
    authors = item.get("author", []) or []
    for a in authors:
        family = a.get("family", "").strip()
        given = a.get("given", "").strip()
        initials = " ".join(p[0].upper() + "." for p in re.split(r"[ \-]+", given) if p)
        name = "%s, %s" % (family, initials) if initials else family
        if norm("%s %s" % (given, family)) in AUTHOR_VARIANTS:
            name = "<me>%s</me>" % name
        out.append(name)
    if not out:
        return ""
    if len(out) == 1:
        return out[0]
    return ", ".join(out[:-1]) + ", &amp; " + out[-1]


def first(seq):
    return (seq or [""])[0] if isinstance(seq, list) else (seq or "")


def format_venue(item):
    container = first(item.get("container-title"))
    vol, issue, page = item.get("volume"), item.get("issue"), item.get("page")
    bits = [container] if container else []
    if vol:
        bits.append(("%s(%s)" % (vol, issue)) if issue else str(vol))
    if page:
        bits.append(page.replace("-", "&ndash;"))
    return ", ".join(b for b in bits if b)


def year_of(item):
    parts = (item.get("issued") or {}).get("date-parts") or [[None]]
    try:
        return int(parts[0][0])
    except (TypeError, ValueError, IndexError):
        return None


def to_entry(item):
    year = year_of(item)
    if not year:
        return None
    container = norm(first(item.get("container-title")))
    korean_title = first(item.get("original-title"))
    is_korean = any(k in container for k in KOREAN_CONTAINERS) or bool(korean_title)

    english_title = first(item.get("title")).strip()
    if is_korean and korean_title:
        title, title_en = korean_title.strip(), english_title
    else:
        title, title_en = english_title, ""

    return {
        "group": str(year),
        "year": year,
        "type": "korean" if is_korean else TYPE_MAP.get(item.get("type"), "journal"),
        "authors": format_authors(item),
        "title": title,
        "title_en": title_en,
        "venue": format_venue(item),
        "doi": "https://doi.org/" + item["DOI"],
        "note": "",
        "needs_review": True,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    with io.open(DATA, encoding="utf-8") as f:
        payload = json.load(f)
    pubs = payload["publications"]

    known = set()
    for p in pubs:
        doi = (p.get("doi") or "").lower()
        if doi:
            known.add(doi.rsplit("doi.org/", 1)[-1])
        known.add(norm(re.sub(r"<[^>]+>", "", p.get("title", ""))))
        if p.get("title_en"):
            known.add(norm(p["title_en"]))

    additions = []
    for item in fetch_candidates():
        if not is_ours(item):
            continue
        doi = item["DOI"].lower()
        title_key = norm(first(item.get("title")))
        if doi in known or (title_key and title_key in known):
            continue
        entry = to_entry(item)
        if entry:
            additions.append(entry)
            known.add(doi)
            if title_key:
                known.add(title_key)

    if not additions:
        print("No new publications found.")
        return 0

    print("Found %d new publication(s):" % len(additions))
    for a in additions:
        print("  - [%s] %s (%s)" % (a["year"], re.sub(r"<[^>]+>", "", a["title"])[:90], a["doi"]))

    if args.dry_run:
        return 0

    payload["publications"] = additions + pubs
    with io.open(DATA, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print("Wrote %s" % DATA)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
