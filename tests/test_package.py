"""Mirror Zotero 10's mandatory manifest fields, not just generic ZIP validity."""
import json
import unittest
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]


class PackageTests(unittest.TestCase):
    def test_zotero10_required_install_fields(self):
        manifest = json.loads((ROOT / 'plugin/manifest.json').read_text(encoding='utf-8'))
        zotero = manifest['applications']['zotero']
        for key in ['id', 'update_url', 'strict_max_version']:
            self.assertTrue(zotero.get(key), f'Zotero 10 rejects manifests without {key}')
        update = urlparse(zotero['update_url'])
        self.assertEqual(update.scheme, 'https', 'Zotero rejects insecure update metadata')
        self.assertEqual(update.hostname, '127.0.0.1')
        self.assertEqual(update.path, '/agent-reader-bridge/updates.json')


if __name__ == '__main__':
    unittest.main()
