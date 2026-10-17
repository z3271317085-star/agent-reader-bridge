import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'vendor')]
import pymupdf
from bridge import PaperBridge


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=ROOT / 'tmp')
        self.pdf = Path(self.tmp.name) / 'paper.pdf'
        doc = pymupdf.open()
        for text in ['First page: alpha evidence.', 'Second page: beta findings.']:
            page = doc.new_page()
            page.insert_text((72, 72), text)
        doc.save(self.pdf)
        doc.close()
        self.current = {'document_id': 'local:A', 'title': 'Paper A', 'path': str(self.pdf),
                        'page': 2, 'page_label': '1', 'selection': {'text': 'beta', 'pages': [2]}}
        self.bridge = PaperBridge(lambda: self.current)

    def tearDown(self):
        self.tmp.cleanup()

    def test_snapshot_keeps_original_paper_after_switch(self):
        snap = self.bridge.capture()
        self.current = {'document_id': 'local:B', 'path': 'missing.pdf', 'page': 1}
        self.assertIn('beta', self.bridge.read_pages(snap['snapshot_id'], 2, 2)['pages'][0]['text'])
        self.assertNotIn('path', snap)

    def test_page_bounds_rejected(self):
        snap = self.bridge.capture()['snapshot_id']
        for first, last in [(0, 1), (2, 1), (1, 3), (True, 2)]:
            with self.assertRaises(ValueError):
                self.bridge.read_pages(snap, first, last)

    def test_file_change_rejected(self):
        snap = self.bridge.capture()['snapshot_id']
        with self.pdf.open('ab') as out:
            out.write(b'\nchanged')
        with self.assertRaisesRegex(ValueError, 'changed'):
            self.bridge.read_pages(snap, 1, 1)

    def test_unknown_snapshot_rejected(self):
        with self.assertRaises(ValueError):
            self.bridge.read_pages('unknown', 1, 1)

    def test_search_includes_page_and_bounded_results(self):
        snap = self.bridge.capture()['snapshot_id']
        result = self.bridge.search(snap, 'beta', 5)
        self.assertEqual(result['matches'][0]['page'], 2)
        with self.assertRaises(ValueError):
            self.bridge.search(snap, '', 5)

    def test_page_image_is_png(self):
        snap = self.bridge.capture()['snapshot_id']
        self.assertTrue(self.bridge.page_image(snap, 1).startswith(b'\x89PNG'))

    def test_missing_context_never_reuses_previous(self):
        self.bridge.capture()
        self.current = {'error': 'no_active_reader'}
        with self.assertRaisesRegex(ValueError, 'no_active_reader'):
            self.bridge.capture()

    def test_snapshot_capacity(self):
        bridge = PaperBridge(lambda: self.current, capacity=2)
        first = bridge.capture()['snapshot_id']
        bridge.capture()
        bridge.capture()
        with self.assertRaises(ValueError):
            bridge.read_pages(first, 1, 1)

    def test_expired_snapshot_rejected(self):
        bridge = PaperBridge(lambda: self.current, ttl=-1)
        sid = bridge.capture()['snapshot_id']
        with self.assertRaises(ValueError):
            bridge.read_pages(sid, 1, 1)


if __name__ == '__main__':
    unittest.main()
