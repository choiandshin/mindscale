# Review brief

A static site for an academic research lab (MindScale, Sogang University). Plain HTML/CSS/JS,
no build step, served by GitHub Pages. Seven pages, one stylesheet, one small script, plus
three Python maintenance scripts and one GitHub Actions workflow.

The owner is a professor, not a developer. She edits this site herself, mostly through the
GitHub web editor. Optimise for **something she can still safely edit in six months**, not for
architectural elegance.

---

## What to review

Highest value first.

1. **Accessibility.** Colour contrast in both light and dark themes, visible focus states,
   heading order, landmark structure, `alt` text, the mobile nav's ARIA state, and whether
   the publication filter chips announce themselves correctly to a screen reader.
2. **The Python scripts** in `tools/`. `fetch_new_publications.py` talks to the Crossref API
   and mutates `data/publications.json`; it runs unattended every Monday. Look for unhandled
   edge cases: malformed Crossref records, missing fields, author-name variants that should
   match but don't, duplicate detection that could false-negative, and whether a partial
   failure can corrupt the JSON.
3. **The GitHub Actions workflow** (`.github/workflows/update-publications.yml`). Action
   version pinning, permission scope, failure modes when Crossref is down.
4. **Metadata and SEO.** Open Graph tags exist but are thin. Structured data (JSON-LD
   `Person` / `ScholarlyArticle`) would be a real improvement for an academic site — Google
   Scholar and institutional aggregators read it.
5. **Performance.** Image dimensions and formats, font loading strategy, anything
   render-blocking. The site is small; don't over-engineer this.
6. **HTML validity and CSS hygiene.** Unclosed tags, duplicate IDs, dead rules, specificity
   collisions.
7. **Safari.** The owner is on macOS; Safari is the likeliest browser for her and her
   colleagues.

---

## Hard constraints — breaking these breaks the site's maintenance

1. **`publications.html` is partly generated.** Everything between
   `<!-- PUBLICATIONS:START -->` and `<!-- PUBLICATIONS:END -->` is written by
   `tools/build_publications.py` from `data/publications.json`. Never hand-edit that region —
   it is overwritten on the next run. To change how publications render, change the renderer
   and re-run it.

2. **The header and footer are duplicated across all seven pages** inside
   `<!-- HEADER:START/END -->` and `<!-- FOOTER:START/END -->` markers. Edit them in
   `index.html` only, then run `python3 tools/sync_layout.py`. Do not delete the marker
   comments, and do not "fix" the duplication by introducing a template engine or JS
   injection — see constraint 3.

3. **No build step. No bundler, no npm, no framework.** The site must remain plain static
   files that GitHub Pages serves directly, editable one file at a time in a browser text box.
   Client-side rendering of content is specifically unwanted: the pages must be readable with
   JavaScript disabled and indexable as static HTML.

4. **Do not remove** `.nojekyll` or `.github/workflows/update-publications.yml`.

5. **Do not rewrite content.** Biographical claims, publication metadata, dates, affiliations
   and award names were verified against primary sources (Crossref, OECD/PISA materials, the
   university's own pages, a published interview). If something looks wrong, flag it in your
   report — do not silently correct it.

6. **Language.** The site is English-only by the owner's choice. The exceptions are
   deliberate: Korean-language paper titles, Korean patent titles as filed, and Korean names
   beside romanised ones. These carry `lang="ko"` and must keep it.

---

## Known open items — not bugs

- `contact.html` links to `cv.pdf`, which has not been added yet. Expected.
- The course descriptions in `teaching.html` are drafts awaiting the owner's review. The
  course *titles* are authoritative.
- `assets/img/office.jpg`, `portrait-studio.jpg` and `sogang-logo-white.png` are intentionally
  unused alternates.

---

## How to verify anything you change

```bash
# 1. all seven pages load
python3 -m http.server 8000    # then open http://localhost:8000

# 2. header/footer still identical across all seven pages
python3 tools/sync_layout.py --check
#    expected: "All 7 pages already in sync."

# 3. the generated publication list still matches the JSON
python3 tools/build_publications.py
#    expected: "publications.html already up to date (44 entries)"

# 4. the weekly updater still runs
python3 tools/fetch_new_publications.py --dry-run
#    expected: a list of new DOIs, or "No new publications found."
```

All four must pass before and after your changes.

---

## Deliverable

A written report of findings ranked by severity, and — for anything you actually change — a
diff small enough that the owner can read it. Prefer several small, separately reviewable
commits over one large refactor. If a fix requires violating a constraint above, describe the
trade-off and leave the decision to the owner rather than making it.
