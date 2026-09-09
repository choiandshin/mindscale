#!/usr/bin/env python3
"""Check local links, landmarks, IDs and generated data without dependencies."""
from collections import Counter
from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
PAGES = ('index', 'research', 'people', 'publications', 'news', 'teaching', 'contact')
VOID = set('area base br col embed hr img input link meta param source track wbr'.split())
SVG_VOID = {'path', 'rect', 'circle', 'stop', 'line', 'polyline', 'ellipse'}


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids, self.tags, self.links, self.errors, self.stack = [], Counter(), [], [], []
        self.schema = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.tags[tag] += 1
        if 'id' in attrs:
            self.ids.append(attrs['id'])
        if tag == 'img' and ('alt' not in attrs or not attrs.get('width') or not attrs.get('height')):
            self.errors.append('Image requires alt, width and height: ' + str(attrs.get('src')))
        if tag == 'html' and attrs.get('lang') != 'en':
            self.errors.append('Page language must remain en')
        for key in ('href', 'src'):
            if attrs.get(key):
                self.links.append(attrs[key])
        if tag == 'script' and attrs.get('type') == 'application/ld+json':
            self.schema = ''
        if tag not in VOID:
            self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_data(self, data):
        if self.schema is not None:
            self.schema += data

    def handle_endtag(self, tag):
        if tag == 'script' and self.schema is not None:
            try:
                json.loads(self.schema)
            except ValueError:
                self.errors.append('Invalid JSON-LD')
            self.schema = None
        if tag in VOID:
            return
        if not self.stack or self.stack[-1] != tag:
            self.errors.append('Mismatched closing tag: ' + tag)
        else:
            self.stack.pop()


def main():
    parsed, errors, warnings = {}, [], []
    for name in PAGES:
        path = ROOT / (name + '.html')
        page = Page()
        page.feed(path.read_text(encoding='utf-8'))
        page.close()
        parsed[path.name] = page
        if page.stack:
            page.errors.append('Unclosed tags: ' + ', '.join(page.stack))
        if len(page.ids) != len(set(page.ids)):
            page.errors.append('Duplicate IDs')
        for tag in ('h1', 'main', 'header', 'footer'):
            if page.tags[tag] != 1:
                page.errors.append('Expected exactly one ' + tag)
        errors.extend(path.name + ': ' + error for error in page.errors)
    for name, page in parsed.items():
        for link in page.links:
            url = urlsplit(link)
            if url.scheme or url.netloc:
                continue
            target = unquote(url.path) or name
            if target == 'cv.pdf' and not (ROOT / target).exists():
                warnings.append('contact.html: cv.pdf is still awaiting the owner (known open item)')
                continue
            if not (ROOT / target).is_file():
                errors.append(name + ': missing local file ' + target)
            if url.fragment and target in parsed and unquote(url.fragment) not in parsed[target].ids:
                errors.append(name + ': missing fragment ' + link)
    for warning in sorted(set(warnings)):
        print('WARNING:', warning)
    for error in errors:
        print('ERROR:', error)
    if not errors:
        print('All 7 pages passed local HTML, links, landmarks, images and JSON-LD checks.')
    return bool(errors)


if __name__ == '__main__':
    raise SystemExit(main())
