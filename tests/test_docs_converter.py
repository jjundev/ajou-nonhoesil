# tests/test_docs_converter.py
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.convert_docs_to_pdf import (
    discover_doc_files,
    resolve_output_pdf_path,
    validate_pdf,
    convert_doc_to_pdf,
)


class TestDocsConverter(unittest.TestCase):
    def setUp(self):
        self.temp_dir = str(Path(tempfile.mkdtemp()).resolve())
        (Path(self.temp_dir) / "sub1").mkdir()
        (Path(self.temp_dir) / "sub1" / "doc1.docx").write_text("dummy")
        (Path(self.temp_dir) / "sub1" / "doc2.doc").write_text("dummy")
        (Path(self.temp_dir) / "sub2").mkdir()
        (Path(self.temp_dir) / "sub2" / "slide.pptx").write_text("dummy")
        (Path(self.temp_dir) / "ignore.txt").write_text("dummy")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_discover_doc_files(self):
        files = discover_doc_files(self.temp_dir)
        self.assertEqual(len(files), 3)
        stems = {Path(f).stem for f in files}
        self.assertEqual(stems, {"doc1", "doc2", "slide"})

    def test_discover_single_doc_file(self):
        single_doc = os.path.join(self.temp_dir, "sub1", "doc1.docx")
        files = discover_doc_files(single_doc)
        self.assertEqual(files, [single_doc])

    def test_discover_single_non_doc_file(self):
        non_doc = os.path.join(self.temp_dir, "ignore.txt")
        files = discover_doc_files(non_doc)
        self.assertEqual(files, [])

    def test_discover_ignores_lock_files(self):
        lock_file = Path(self.temp_dir) / "sub1" / "~$locked.docx"
        lock_file.write_text("lock")
        files = discover_doc_files(self.temp_dir)
        self.assertNotIn(str(lock_file), files)

    def test_resolve_output_pdf_path_inplace(self):
        doc = os.path.join(self.temp_dir, "sub1", "doc1.docx")
        pdf = resolve_output_pdf_path(doc, self.temp_dir, output_dir=None)
        expected = os.path.join(self.temp_dir, "sub1", "doc1.pdf")
        self.assertEqual(pdf, expected)

    def test_resolve_output_pdf_path_mirrored(self):
        out_root = os.path.join(self.temp_dir, "out")
        doc = os.path.join(self.temp_dir, "sub1", "doc1.docx")
        pdf = resolve_output_pdf_path(doc, self.temp_dir, output_dir=out_root)
        expected = os.path.join(out_root, "sub1", "doc1.pdf")
        self.assertEqual(pdf, expected)

    def test_resolve_output_pdf_path_single_file_target(self):
        out_root = os.path.join(self.temp_dir, "out")
        doc = os.path.join(self.temp_dir, "sub1", "doc1.docx")
        pdf = resolve_output_pdf_path(doc, doc, output_dir=out_root)
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
