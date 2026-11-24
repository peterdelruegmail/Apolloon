"""Checks required by the Handbal Live publication workflow."""
import hashlib
import unittest
from unittest.mock import Mock, patch
import publish_handbal_live as publish


class PublicationTests(unittest.TestCase):
    def test_allowed_files_stay_in_website_directory(self):
        for path in ['programmas/handbal-live/ticker.html', 'programmas/handbal-live/ticker.js',
                     'programmas/handbal-live/ranking/api.php', 'programmas/handbal-live/.htaccess']:
            self.assertTrue(publish.publishable(path), path)
        for path in ['settings.ini', 'programmas/handbal-live/../secret.php',
                     'programmas/handbal-live/config.exe', 'programmas/slideshow-livescores/slideshow.py']:
            self.assertFalse(publish.publishable(path), path)

    def test_manual_publication_requires_explicit_valid_files(self):
        with self.assertRaises(ValueError):
            publish.files_to_publish({}, 'workflow_dispatch', '')
        with self.assertRaises(ValueError):
            publish.files_to_publish({}, 'workflow_dispatch', '../secret.php')
        with self.assertRaises(ValueError):
            publish.files_to_publish({}, 'workflow_dispatch', 'missing-file.html')

    def test_matching_upload_is_verified_before_rename(self):
        payload = b'<html>ticker</html>'
        client = Mock()
        client.retrbinary.side_effect = lambda command, callback: callback(payload)
        with patch.object(publish.Path, 'read_bytes', return_value=payload):
            publish.upload(client, ['programmas/handbal-live/ticker.html'], 'test')
        client.rename.assert_called_once_with('.ticker.upload-test.html', 'ticker.html')
        self.assertEqual(client.method_calls[-1][0], 'rename')
        self.assertEqual(hashlib.sha256(payload).digest(), hashlib.sha256(payload).digest())

    def test_mismatched_upload_never_replaces_existing_file(self):
        client = Mock()
        client.retrbinary.side_effect = lambda command, callback: callback(b'corrupt')
        with patch.object(publish.Path, 'read_bytes', return_value=b'expected'):
            with self.assertRaises(ValueError):
                publish.upload(client, ['programmas/handbal-live/ticker.html'], 'test')
        client.rename.assert_not_called()
        client.delete.assert_not_called()


if __name__ == '__main__':
    unittest.main()
