"""Offline regression tests for unattended updates and generated HTML."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import urllib.error

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import fetch_new_publications as fetch
import build_publications as build

RECORD = {'DOI': '10.1234/Example', 'title': ['A valid title'],
          'author': [{'given': 'Hyo-Jeong', 'family': 'Shin'}],
          'issued': {'date-parts': [[2026, 1]]}, 'type': 'journal-article'}


class PublicationTests(unittest.TestCase):
    def test_name_variants_and_unrelated_names(self):
        for given in ('Hyo-Jeong', 'Hyo Jeong', 'Hyojeong', 'H. J.', 'Hyo J.'):
            self.assertTrue(fetch.author_matches({'given': given, 'family': 'Shin'}))
        self.assertFalse(fetch.author_matches({'given': 'Hyo Jin', 'family': 'Shin'}))
        self.assertFalse(fetch.is_ours({'author': [None, 'bad', {}]}))
        self.assertFalse(fetch.is_ours({'author': {'family': 'Shin'}}))

    def test_doi_and_unicode_title_duplicates(self):
        for doi in ('10.1234/ABC', ' DOI:10.1234/abc ', 'https://dx.doi.org/10.1234/AbC',
                    'https://doi.org/10.1234%2Fabc'):
            self.assertEqual(fetch.doi_key(doi), '10.1234/abc')
        self.assertEqual(fetch.norm('A &amp; B: large&ndash;scale'), fetch.norm('A & B large-scale'))
        self.assertNotEqual(fetch.norm('교육 연구 1'), fetch.norm('교육 연구 2'))
        self.assertNotEqual(fetch.norm('교육 연구'), '')
        self.assertEqual(fetch.doi_key('javascript:alert(1)'), '')

    def test_malformed_optional_fields(self):
        for key, value in [('issued', None), ('issued', []), ('issued', {'date-parts': [[]]}),
                           ('issued', {'date-parts': [[True]]}), ('title', []),
                           ('title', [None]), ('DOI', None)]:
            item = copy.deepcopy(RECORD)
            item[key] = value
            self.assertIsNone(fetch.to_entry(item))
        item = dict(RECORD, volume=4, issue=[], page=12, type={})
        self.assertIsNotNone(fetch.to_entry(item))

    def test_korean_is_detected_without_mislabeling_other_languages(self):
        self.assertEqual(fetch.to_entry(dict(RECORD, title=['교육 연구']))['type'], 'korean')
        self.assertEqual(fetch.to_entry(dict(RECORD, **{'original-title': ['Étude']}))['type'], 'journal')

    def test_external_markup_is_not_executed(self):
        item = dict(RECORD, title=['<img src=x onerror=alert(1)>'],
                    **{'container-title': ['<script>alert(1)</script>']})
        entry = fetch.to_entry(item)
        rendered = build.render([entry])
        self.assertNotIn('<img ', rendered)
        self.assertNotIn('<script>alert', rendered)
        self.assertIn('&lt;img', rendered)
        self.assertEqual(build.citation('<me>Shin</me> &amp; <em>Study</em>'),
                         '<span class="me">Shin</span> &amp; <em>Study</em>')
        entry['doi'] = 'javascript:alert(1)'
        with self.assertRaises(ValueError):
            build.render([entry])

    def test_partial_or_malformed_crossref_response_fails(self):
        good = {'message': {'items': [None, {}, RECORD]}}
        for failure in (OSError('offline'), {'message': None}, {'message': {'items': None}}):
            with patch.object(fetch, 'crossref', side_effect=[good, failure]), patch.object(fetch.time, 'sleep'):
                with self.assertRaises(RuntimeError):
                    fetch.fetch_candidates()
        with patch.object(fetch, 'crossref', return_value=good), patch.object(fetch.time, 'sleep'):
            self.assertEqual(len(fetch.fetch_candidates()), 1)

    def test_network_failure_is_nonzero_and_preserves_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'publications.json'
            original = '{"publications": []}\n'
            path.write_text(original)
            with patch.object(fetch, 'DATA', str(path)), patch.object(sys, 'argv', ['fetch', '--dry-run']), \
                 patch.object(fetch, 'fetch_candidates', side_effect=RuntimeError('offline')):
                self.assertEqual(fetch.main(), 1)
            self.assertEqual(path.read_text(), original)

    def test_interrupted_atomic_write_preserves_original(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'publications.json'
            path.write_text('{"publications": []}\n')
            original = path.read_bytes()
            with patch.object(fetch, 'DATA', str(path)), patch.object(fetch.os, 'replace', side_effect=OSError('disk error')):
                with self.assertRaises(OSError):
                    fetch.write_payload({'publications': [fetch.to_entry(RECORD)]})
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(len(list(Path(directory).iterdir())), 1)
            with patch.object(fetch, 'DATA', str(path)):
                fetch.write_payload({'publications': []})
            self.assertEqual(json.loads(path.read_text()), {'publications': []})

    def test_retries_are_bounded(self):
        with patch.object(fetch.urllib.request, 'urlopen', side_effect=urllib.error.URLError('offline')) as request, \
             patch.object(fetch.time, 'sleep'):
            with self.assertRaises(urllib.error.URLError):
                fetch.crossref('https://api.crossref.org/works')
            self.assertEqual(request.call_count, 3)

    def test_structured_data_does_not_claim_unpublished_dates(self):
        review = dict(fetch.to_entry(RECORD), type='review', group='Under review', year=9999)
        data = json.loads(build.scholarly_data([review]))
        self.assertEqual(data['@graph'], [])


if __name__ == '__main__':
    unittest.main()
