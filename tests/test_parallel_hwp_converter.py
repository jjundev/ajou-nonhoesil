import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from scripts.parallel_hwp_converter import (
    discover_hwp_files,
    validate_pdf,
    resolve_output_pdf_path,
    AllinpdfConverter,
    parallel_convert_hwp,
)

class TestParallelHWPConverter(unittest.TestCase):
    def setUp(self):
        self.temp_dir = str(Path(tempfile.mkdtemp()).resolve())
        (Path(self.temp_dir) / "sub").mkdir()
        (Path(self.temp_dir) / "sub" / "doc1.hwp").write_text("dummy")
        (Path(self.temp_dir) / "sub" / "doc2.HWP").write_text("dummy")
        (Path(self.temp_dir) / "sub" / "doc3.hwpx").write_text("dummy")
        (Path(self.temp_dir) / "sub" / "ignore.txt").write_text("dummy")
        (Path(self.temp_dir) / "sub" / "~$locked.hwp").write_text("dummy")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_discover_files(self):
        files = discover_hwp_files(self.temp_dir)
        self.assertEqual(len(files), 3)
        self.assertTrue(all(f.lower().endswith((".hwp", ".hwpx")) for f in files))
        self.assertFalse(any(os.path.basename(f).startswith("~$") for f in files))

    def test_discover_single_file(self):
        single = os.path.join(self.temp_dir, "sub", "doc1.hwp")
        self.assertEqual(discover_hwp_files(single), [single])
        non_hwp = os.path.join(self.temp_dir, "sub", "ignore.txt")
        self.assertEqual(discover_hwp_files(non_hwp), [])

    def test_validate_pdf(self):
        valid_pdf = os.path.join(self.temp_dir, "valid.pdf")
        with open(valid_pdf, "wb") as f:
            f.write(b"%PDF-1.4\n" + b"A" * 150 + b"\n%%EOF")
        self.assertTrue(validate_pdf(valid_pdf))

        invalid_pdf = os.path.join(self.temp_dir, "invalid.pdf")
        with open(invalid_pdf, "wb") as f:
            f.write(b"NOT A PDF")
        self.assertFalse(validate_pdf(invalid_pdf))

        # Test non-existent file
        self.assertFalse(validate_pdf(os.path.join(self.temp_dir, "nonexistent.pdf")))

        # Test too small file
        small_pdf = os.path.join(self.temp_dir, "small.pdf")
        with open(small_pdf, "wb") as f:
            f.write(b"%PDF-")
        self.assertFalse(validate_pdf(small_pdf))

    def test_resolve_output_path(self):
        hwp = os.path.join(self.temp_dir, "test.hwp")
        pdf = resolve_output_pdf_path(hwp)
        self.assertEqual(pdf, os.path.join(self.temp_dir, "test.pdf"))

        sub_hwp = os.path.join(self.temp_dir, "sub", "doc1.hwp")
        # In-place with base_target
        pdf_inplace = resolve_output_pdf_path(sub_hwp, base_target=self.temp_dir)
        self.assertEqual(pdf_inplace, os.path.join(self.temp_dir, "sub", "doc1.pdf"))

        # Mirrored output dir
        out_dir = os.path.join(self.temp_dir, "out")
        pdf_mirrored = resolve_output_pdf_path(sub_hwp, base_target=self.temp_dir, output_dir=out_dir)
        self.assertEqual(pdf_mirrored, os.path.join(out_dir, "sub", "doc1.pdf"))

    def test_converter_init_port_and_user_data_dir(self):
        c = AllinpdfConverter(port=9225)
        self.assertEqual(c.port, 9225)
        self.assertTrue(os.path.basename(c.user_data_dir).startswith("chrome_allinpdf_"))
        self.assertIn("9225", c.user_data_dir)

    @patch.object(AllinpdfConverter, "convert_file", return_value=True)
    @patch.object(AllinpdfConverter, "start", return_value=None)
    @patch.object(AllinpdfConverter, "stop", return_value=None)
    def test_parallel_convert_hwp_mock(self, mock_stop, mock_start, mock_convert):
        files = [
            os.path.join(self.temp_dir, "sub", "doc1.hwp"),
            os.path.join(self.temp_dir, "sub", "doc2.HWP"),
        ]
        result = parallel_convert_hwp(files, max_workers=2, force=True, base_port=9300)
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["success"], 2)
        self.assertEqual(len(result["failed"]), 0)

if __name__ == "__main__":
    unittest.main()
