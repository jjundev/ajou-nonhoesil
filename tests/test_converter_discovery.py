# tests/test_converter_discovery.py
import os
import tempfile
import unittest
from pathlib import Path

from scripts.convert_hwp_to_pdf import discover_hwp_files, resolve_output_pdf_path, validate_pdf

class TestConverterDiscovery(unittest.TestCase):
    def setUp(self):
        self.temp_dir = str(Path(tempfile.mkdtemp()).resolve())
        (Path(self.temp_dir) / "sub1").mkdir()
        (Path(self.temp_dir) / "sub1" / "doc1.hwp").write_text("dummy")
        (Path(self.temp_dir) / "sub1" / "doc2.HWP").write_text("dummy")
        (Path(self.temp_dir) / "sub2").mkdir()
        (Path(self.temp_dir) / "sub2" / "doc3.hwpx").write_text("dummy")
        (Path(self.temp_dir) / "ignore.txt").write_text("dummy")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_discover_hwp_files(self):
        files = discover_hwp_files(self.temp_dir)
        self.assertEqual(len(files), 3)
        stems = {Path(f).stem for f in files}
        self.assertEqual(stems, {"doc1", "doc2", "doc3"})

    def test_discover_single_hwp_file(self):
        single_hwp = os.path.join(self.temp_dir, "sub1", "doc1.hwp")
        files = discover_hwp_files(single_hwp)
        self.assertEqual(files, [single_hwp])

    def test_discover_single_non_hwp_file(self):
        non_hwp = os.path.join(self.temp_dir, "ignore.txt")
        files = discover_hwp_files(non_hwp)
        self.assertEqual(files, [])

    def test_discover_ignores_lock_files(self):
        lock_file = Path(self.temp_dir) / "sub1" / "~$locked.hwp"
        lock_file.write_text("lock")
        files = discover_hwp_files(self.temp_dir)
        self.assertNotIn(str(lock_file), files)

    def test_resolve_output_pdf_path_inplace(self):
        hwp = os.path.join(self.temp_dir, "sub1", "doc1.hwp")
        pdf = resolve_output_pdf_path(hwp, self.temp_dir, output_dir=None)
        expected = os.path.join(self.temp_dir, "sub1", "doc1.pdf")
        self.assertEqual(pdf, expected)

    def test_resolve_output_pdf_path_mirrored(self):
        out_root = os.path.join(self.temp_dir, "out")
        hwp = os.path.join(self.temp_dir, "sub1", "doc1.hwp")
        pdf = resolve_output_pdf_path(hwp, self.temp_dir, output_dir=out_root)
        expected = os.path.join(out_root, "sub1", "doc1.pdf")
        self.assertEqual(pdf, expected)

    def test_resolve_output_pdf_path_single_file_target(self):
        out_root = os.path.join(self.temp_dir, "out")
        hwp = os.path.join(self.temp_dir, "sub1", "doc1.hwp")
        pdf = resolve_output_pdf_path(hwp, hwp, output_dir=out_root)
        expected = os.path.join(out_root, "doc1.pdf")
        self.assertEqual(pdf, expected)

    def test_validate_pdf(self):
        valid_pdf = os.path.join(self.temp_dir, "valid.pdf")
        with open(valid_pdf, "wb") as f:
            f.write(b"%PDF-1.4\n" + b"x" * 150 + b"\n%%EOF")
        self.assertTrue(validate_pdf(valid_pdf))

        invalid_pdf = os.path.join(self.temp_dir, "invalid.pdf")
        with open(invalid_pdf, "wb") as f:
            f.write(b"NOT A PDF")
        self.assertFalse(validate_pdf(invalid_pdf))

        # Test non-existent file
        self.assertFalse(validate_pdf(os.path.join(self.temp_dir, "non_existent.pdf")))

        # Test empty/small file
        small_pdf = os.path.join(self.temp_dir, "small.pdf")
        with open(small_pdf, "wb") as f:
            f.write(b"%PDF-1.4")
        self.assertFalse(validate_pdf(small_pdf))

if __name__ == "__main__":
    unittest.main()
