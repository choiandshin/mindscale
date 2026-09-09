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
import html
import io
import json
import os
import re
import sys
import time
import tempfile
import unicodedata
import urllib.error
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
    """Keep Unicode letters and digits; ignore markup and punctuation."""
    s = html.unescape(re.sub(r"<[^>]+>", "", text(s)))
    s = unicodedata.normalize("NFKC", s).casefold()
    return " ".join("".join(c if c.isalnum() else " " for c in s).split())


def text(value):
    return value.strip() if isinstance(value, str) else ""


def doi_key(value):
    value = urllib.parse.unquote(text(value)).casefold()
    value = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", value)
    return value if re.fullmatch(r"10\.\d{4,9}/\S+", value) else ""


def author_matches(author):
    if not isinstance(author, dict):
        return False
    name = norm(text(author.get("given")) + " " + text(author.get("family")))
    return name.replace(" ", "") in {v.replace(" ", "") for v in AUTHOR_VARIANTS}


def crossref(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": "MindScale-site-updater/1.0 (mailto:%s)" % MAILTO,
        "Accept": "application/json",
    })
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as exc:
            if exc.code != 429 and exc.code < 500:
                raise
            if attempt == 2:
                raise
        except (urllib.error.URLError, TimeoutError):
            if attempt == 2:
                raise
        time.sleep(2 ** attempt)


def fetch_candidates():
    """Return Crossref items plausibly authored by Dr. Shin."""
    seen, items, failures = set(), [], []
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
            message = data.get("message") if isinstance(data, dict) else None
            records = message.get("items") if isinstance(message, dict) else None
            if not isinstance(records, list):
                raise ValueError("Crossref response has no items list")
        except Exception as exc:              # network hiccup: fail soft
            print("warning: Crossref query failed for %r: %s" % (variant, exc), file=sys.stderr)
            failures.append(variant)
            continue
        for it in records:
            if not isinstance(it, dict):
                continue
            doi = doi_key(it.get("DOI"))
            if doi and doi not in seen:
                seen.add(doi)
                items.append(it)
        time.sleep(1)
    if failures:
        raise RuntimeError("Incomplete Crossref check; no files changed. Try again later.")
    return items


def is_ours(item):
    authors = item.get("author")
    return isinstance(authors, list) and any(author_matches(a) for a in authors)


def format_authors(item):
    """Render the author list in the site's style, wrapping Dr. Shin in <me>."""
    out = []
    authors = item.get("author")
    authors = authors if isinstance(authors, list) else []
    for a in authors:
        if not isinstance(a, dict):
            continue
        family = text(a.get("family")) or text(a.get("name"))
        given = text(a.get("given"))
        if not family:
            continue
        initials = " ".join(p[0].upper() + "." for p in re.split(r"[ \-]+", given) if p)
        name = "%s, %s" % (family, initials) if initials else family
        name = html.escape(name)
        if author_matches(a):
            name = "<me>%s</me>" % name
        out.append(name)
    if not out:
        return ""
    if len(out) == 1:
        return out[0]
    return ", ".join(out[:-1]) + ", &amp; " + out[-1]


def first(seq):
    return text(seq[0]) if isinstance(seq, list) and seq else text(seq)


def format_venue(item):
    container = html.escape(first(item.get("container-title")))
    vol, issue, page = (html.escape(text(item.get(k))) for k in ("volume", "issue", "page"))
    bits = [container] if container else []
    if vol:
        bits.append(("%s(%s)" % (vol, issue)) if issue else str(vol))
    if page:
        bits.append(page.replace("-", "&ndash;"))
    return ", ".join(b for b in bits if b)


def year_of(item):
    issued = item.get("issued")
    parts = issued.get("date-parts") if isinstance(issued, dict) else None
    try:
        year = parts[0][0]
        return year if type(year) is int and 1000 <= year <= 9998 else None
    except (TypeError, ValueError, IndexError, KeyError):
        return None


def to_entry(item):
    year = year_of(item)
    doi = doi_key(item.get("DOI"))
    if not year or not doi:
        return None
    container = norm(first(item.get("container-title")))
    korean_title = first(item.get("original-title"))
    english_title = first(item.get("title"))
    is_korean = bool(re.search(r"[\uac00-\ud7a3]", korean_title + english_title))
    is_korean = is_korean or any(k in container for k in KOREAN_CONTAINERS)

    if not english_title:
        return None
    if is_korean and re.search(r"[\uac00-\ud7a3]", korean_title):
        title, title_en = korean_title.strip(), english_title
    else:
        title, title_en = english_title, ""

    return {
        "group": str(year),
        "year": year,
        "type": "korean" if is_korean else TYPE_MAP.get(text(item.get("type")), "journal"),
        "authors": format_authors(item),
        "title": html.escape(title),
        "title_en": html.escape(title_en),
        "venue": format_venue(item),
        "doi": "https://doi.org/" + doi,
        "note": "",
        "needs_review": True,
    }


def write_payload(payload):
    """Replace only after a complete JSON file has been flushed to disk."""
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=os.path.dirname(DATA),
                                         prefix=".publications-", delete=False) as f:
            tmp = f.name
            json.dump(payload, f, ensure_ascii=False, indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, DATA)
    finally:
        if tmp and os.path.exists(tmp):
            os.unlink(tmp)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    with io.open(DATA, encoding="utf-8") as f:
        payload = json.load(f)
    pubs = payload["publications"]

    known = set()
    for p in pubs:
        doi = doi_key(p.get("doi"))
        if doi:
            known.add(doi)
        known.add(norm(re.sub(r"<[^>]+>", "", p.get("title", ""))))
        if p.get("title_en"):
            known.add(norm(p["title_en"]))

    additions = []
    try:
        candidates = fetch_candidates()
    except RuntimeError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1
    for item in candidates:
        if not is_ours(item):
            continue
        doi = doi_key(item.get("DOI"))
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
    write_payload(payload)
    print("Wrote %s" % DATA)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
