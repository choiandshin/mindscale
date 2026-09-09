# MindScale Lab website

Static site for the MindScale Lab, Sogang University. Plain HTML, one stylesheet,
one small script — no build step, no dependencies for the site itself.

```
index.html            Home
research.html         Research areas, AI Measurement Science, PISA, grants, patents, awards
people.html           Director, students, fellows, undergraduate researchers
publications.html     Filterable publication list  ← GENERATED, see below
news.html             Dated news archive
teaching.html         Programs, courses, workshops, professional service
contact.html          Contact details, prospective students

assets/css/style.css  All styling (design tokens in :root at the top)
assets/js/main.js     Mobile nav, active nav item, publication filters
assets/img/           photos — see "Images" below

data/publications.json          Source of truth for the publication list
tools/build_publications.py     Renders that JSON into publications.html
tools/fetch_new_publications.py Finds new work on Crossref and adds it to the JSON
tools/sync_layout.py            Copies the nav + footer from index.html to every page
.github/workflows/update-publications.yml   Runs the first two scripts weekly

.nojekyll             Tells GitHub Pages to serve files as-is
```

---

## Before you publish

1. **CV.** Drop your CV in the site root as `cv.pdf`. Until that file exists, the
   "Curriculum vitae (PDF)" link on the Contact page will 404. Nothing else is outstanding.

### Already settled

- **Academic title** — "Associate Professor" (부교수, from September 2026). Note that
  조교수 translates as *Assistant* Professor and 부교수 as *Associate* Professor; the site
  uses Associate throughout, on `people.html`.
- **Courses** — the real list is on `teaching.html`, five undergraduate and two graduate.
  The one-line descriptions are editable; the course titles are yours as given.
- **LinkedIn** — `https://www.linkedin.com/in/hyo-jeong-shin-42128932/`, in the footer of
  every page and on the Contact page.
- **Sogang logotype** — in the affiliation strip above the footer.

---

## Images

The Sogang logotype is already in place in the affiliation strip above the footer, at 28 px
tall (the wordmark is about 11.8:1, so it stays short). Logo use is administered by
발전홍보팀 (02-705-8052) — worth a note to them if this becomes an official departmental page.


| file | where it appears | source |
|---|---|---|
| `portrait.jpg` | homepage hero | office photo, 4:5 crop |
| `portrait-square.jpg` | People page, director card | your cropped headshot |
| `speaking.jpg` | homepage, AI Measurement Science band | lectern photo |
| `office.jpg` | not currently used — a wide 3:2 crop of the office photo, if you want a banner | office photo |
| `portrait-studio.jpg` | not currently used — the studio photo as a 4:5 portrait | studio photo |
| `sogang-logo.png` | affiliation strip above the footer | official Sogang logotype, dark on transparent |
| `sogang-logo-white.png` | not currently used — white version, for a dark background | same logotype, recoloured |

To swap the hero photo for the studio version, change the `src` in `index.html` from
`assets/img/portrait.jpg` to `assets/img/portrait-studio.jpg`.

Replacing a photo: keep the same file name and roughly the same aspect ratio (4:5 for the
portraits, 1:1 for the square, 3:2 for the wide ones) and nothing else needs to change.

---

## Keeping the nav and footer in sync

The header and footer are copied into all seven pages. Rather than editing seven files,
edit them **once in `index.html`** — inside the `<!-- HEADER:START -->` / `<!-- FOOTER:START -->`
marker comments — then run:

```bash
python3 tools/sync_layout.py
```

It copies both blocks into every other page and moves the `is-active` highlight to the
right nav link on each one. `python3 tools/sync_layout.py --check` reports pages that are
out of sync without changing anything.

---

## The weekly auto-update

Every Monday at 09:00 Korea time, GitHub runs `.github/workflows/update-publications.yml`:

1. `tools/fetch_new_publications.py` asks Crossref for works authored by "Hyo Jeong Shin"
   published since 2022, skips every DOI and title already in `data/publications.json`,
   and appends anything new — formatting authors, venue, and Korean titles in the site's style.
2. `tools/build_publications.py` re-renders the list inside `publications.html`.
3. If anything changed, a **pull request** is opened called "New publications found".

Nothing goes live until you merge that pull request. New entries carry
`"needs_review": true` in the JSON so you can see at a glance what the robot added.
Crossref metadata is good but not perfect — check the author list, page range, and
category, then delete the flag and merge. If an entry does not belong, delete it from
the JSON, run `python3 tools/build_publications.py`, and merge.

**One-time setup after the repo exists:** go to *Settings → Actions → General*, and under
*Workflow permissions* select **Read and write permissions** and tick **Allow GitHub
Actions to create and approve pull requests**. Without this the workflow can read but
cannot open the PR.

To test it immediately: *Actions → Update publications → Run workflow*.

To run it locally:

```bash
python3 tools/fetch_new_publications.py --dry-run   # just report
python3 tools/fetch_new_publications.py             # write to the JSON
python3 tools/build_publications.py                 # re-render the HTML
```

The script's settings — author name variants, cut-off date, list of Korean-language
journals — are constants at the top of `tools/fetch_new_publications.py`.

### Adding a publication by hand

Edit `data/publications.json` and run `python3 tools/build_publications.py`. Fields:

| field | meaning |
|---|---|
| `group` | heading it appears under — a year, or `Under review` |
| `year` | integer used for sorting (`9999` sorts to the top) |
| `type` | `journal`, `chapter`, `proceedings`, `report`, `korean`, `review` — drives the filter chips |
| `authors` | wrap your own name in `<me>…</me>` to bold it |
| `title` | for Korean-language work, the Korean title |
| `title_en` | English gloss, shown in italics beneath a Korean title |
| `venue` | journal, volume(issue), pages |
| `doi` | full URL; renders as a DOI link |
| `note` | optional badge, e.g. "Undergraduate capstone project" |

### Adding a news item

News lives directly in `news.html` and the homepage. Copy an existing
`<article class="news-item">` block in `news.html`, put it at the top, and copy the same
item into the three-card grid on `index.html` if it should appear on the homepage.

---

## Publishing to GitHub Pages

**Option A — user site at `https://<username>.github.io`**

1. Create a repository named exactly `<your-github-username>.github.io`.
2. Upload every file and folder from this directory into the repository root
   (*Add file → Upload files*; drag and drop works). Keep the folder structure —
   `.github/` and `.nojekyll` are hidden on macOS, so use the command line below if
   drag-and-drop skips them.
3. The site is live at `https://<your-github-username>.github.io` within a minute.

**Option B — project site (e.g. `https://<username>.github.io/mindscale`)**

Create a repository named `mindscale`, upload as above, then *Settings → Pages*,
source **Deploy from a branch**, branch `main`, folder `/ (root)`.

Command line — recommended, because it includes the hidden files:

```bash
cd mindscale
git init && git branch -M main
git add -A && git commit -m "MindScale Lab website"
git remote add origin https://github.com/<username>/<repo>.git
git push -u origin main
```

### Custom domain (optional)

1. Create a file `CNAME` in the site root containing only the domain, e.g. `mindscale.kr`.
2. At your registrar: `A` records for the apex domain → `185.199.108.153`,
   `185.199.109.153`, `185.199.110.153`, `185.199.111.153`; or a `CNAME` record for a
   subdomain (`www`, `lab`) → `<username>.github.io`.
3. *Settings → Pages*, enter the domain and tick **Enforce HTTPS** once the certificate
   is issued (up to an hour).

---

## Editing the rest of the site

**Colors and spacing.** All design tokens are in the `:root` block at the top of
`assets/css/style.css`. Changing `--teal-700` and `--navy-800` restyles the whole site.

**Navigation.** The nav bar and footer are copied into each HTML file. If you add or
rename a page, update the `<ul class="nav-links">` block in all seven files.

**Korean text.** Mark it with `lang="ko"` so it picks up the right font and line breaking,
e.g. `<span lang="ko">신효정</span>`.

## Testing locally

```bash
cd mindscale
python3 -m http.server 8000
# open http://localhost:8000
```
