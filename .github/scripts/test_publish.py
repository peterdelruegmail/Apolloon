import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("publish", Path(__file__).with_name("publish_handbal_live.py"))
publish = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publish)


class FakeFTP:
    def __init__(self, corrupt=False):
        self.files = {"index.html": b"old index", "custom.css": b"keep me"}
        self.corrupt = corrupt
        self.renames = []
    def storbinary(self, command, source):
        self.files[command[5:]] = source.read()
    def retrbinary(self, command, writer):
        writer(b"corrupt" if self.corrupt else self.files[command[5:]])
    def rename(self, old, new):
        self.files[new] = self.files.pop(old)
        self.renames.append((old, new))


class PublishTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.before = os.getcwd()
        os.chdir(self.temp.name)
        self.root = Path(publish.PREFIX)
        self.root.mkdir(parents=True)
        (self.root / "api.php").write_bytes(b"<?php echo 'ok';")
    def tearDown(self):
        os.chdir(self.before)
        self.temp.cleanup()
    def test_manual_selection_and_traversal(self):
        self.assertEqual(publish.files_to_publish({}, "workflow_dispatch", "api.php,api.php"), [publish.PREFIX+"api.php"])
        for name in ["../secret.php", "/secret.php", "../../ranking/api.php", "LEESMIJ.txt"]:
            with self.assertRaises(ValueError):
                publish.files_to_publish({}, "workflow_dispatch", name)
    def test_changed_files_only(self):
        diff = (publish.PREFIX+"api.php\0"+publish.PREFIX+"LEESMIJ.txt\0ranking/api.php\0").encode()
        with patch.object(publish.subprocess, "check_output", return_value=diff) as call:
            self.assertEqual(publish.files_to_publish({"before":"abc"}, "push", "", "last-success"), [publish.PREFIX+"api.php"])
            self.assertIn("last-success", call.call_args.args[0])
            self.assertIn("--diff-filter=ACMRT", call.call_args.args[0])
    def test_upload_verifies_and_preserves_other_files(self):
        ftp = FakeFTP()
        publish.upload(ftp, [publish.PREFIX+"api.php"], "123")
        self.assertEqual(ftp.files["api.php"], (self.root/"api.php").read_bytes())
        self.assertEqual(ftp.files["custom.css"], b"keep me")
        self.assertTrue(ftp.renames[0][0].endswith(".php"))
        self.assertEqual(ftp.files["index.html"], b"old index")
    def test_corrupt_transfer_never_replaces_live_file(self):
        ftp = FakeFTP(corrupt=True)
        ftp.files["api.php"] = b"old"
        with self.assertRaises(ValueError):
            publish.upload(ftp, [publish.PREFIX+"api.php"], "123")
        self.assertEqual(ftp.files["api.php"], b"old")
        self.assertEqual(ftp.renames, [])
    def test_missing_password_does_not_connect(self):
        with patch.dict(os.environ, {"FTP_PASSWORD":""}), patch.object(publish.ftplib, "FTP") as ftp:
            with self.assertRaises(ValueError):
                publish.connect()
            ftp.assert_not_called()
    def test_wrong_directory_does_not_write(self):
        ftp = FakeFTP()
        ftp.connect = ftp.login = ftp.set_pasv = ftp.cwd = ftp.close = lambda *args, **kwargs: None
        with patch.dict(os.environ, {"FTP_PASSWORD":"test", "FTP_HOST":"example.test", "FTP_USERNAME":"test", "FTP_REMOTE_DIR":"Handbal-Live", "FTP_PROTOCOL":"ftp"}), patch.object(publish.ftplib, "FTP", return_value=ftp):
            with self.assertRaises(ValueError):
                publish.connect()
        self.assertEqual(ftp.renames, [])
    def test_html_validation(self):
        path = self.root/"index.html"
        path.write_text("<script>const value=1;</script>", encoding="utf-8")
        publish.validate([str(path)])
        path.write_text("<script>const = ;</script>", encoding="utf-8")
        with patch.object(publish.subprocess, "run", wraps=publish.subprocess.run) as run:
            with self.assertRaises(publish.subprocess.CalledProcessError):
                publish.validate([str(path)])


if __name__ == "__main__":
    unittest.main()
