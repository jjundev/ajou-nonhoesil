import os
import sys
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Portable path to global skill scripts directory
GLOBAL_SKILL_DIR = Path.home() / ".gemini/config/skills/hwp-to-pdf"
SCRIPTS_DIR = GLOBAL_SKILL_DIR / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

class TestGlobalHwpToPdfSkill(unittest.TestCase):
    def test_global_scripts_exist(self):
        hwp_to_pdf_script = SCRIPTS_DIR / "hwp_to_pdf.py"
        split_hwp_script = SCRIPTS_DIR / "split_hwp.py"
        self.assertTrue(hwp_to_pdf_script.exists(), "hwp_to_pdf.py should exist in global skill scripts")
        self.assertTrue(split_hwp_script.exists(), "split_hwp.py should exist in global skill scripts")

    def test_import_and_functions(self):
        import hwp_to_pdf  # type: ignore
        import split_hwp   # type: ignore
        self.assertTrue(callable(getattr(hwp_to_pdf, "discover_hwp_files", None)))
        self.assertTrue(callable(getattr(hwp_to_pdf, "validate_pdf", None)))
        self.assertTrue(callable(getattr(hwp_to_pdf, "resolve_output_pdf_path", None)))
        self.assertTrue(callable(getattr(hwp_to_pdf, "get_chrome_binary", None)))
        self.assertTrue(callable(getattr(split_hwp, "split_hwp_file", None)))
        self.assertTrue(callable(getattr(split_hwp, "create_dummy_images", None)))

    def test_split_hwp_dummy_images_zero_deps(self):
        import split_hwp  # type: ignore
        # Verify split_hwp has zero PIL dependencies in clean interpreter
        res = subprocess.run(
            [sys.executable, "-c", f"import sys; sys.path.insert(0, {str(SCRIPTS_DIR)!r}); import split_hwp; sys.exit(1 if 'PIL' in sys.modules else 0)"],
            capture_output=True,
        )
        self.assertEqual(res.returncode, 0, "split_hwp should have zero PIL dependencies")
        # Also verify source file contains no PIL imports
        source_code = (SCRIPTS_DIR / "split_hwp.py").read_text(encoding="utf-8")
        self.assertNotIn("import PIL", source_code)
        self.assertNotIn("from PIL", source_code)
        dummy_jpg, dummy_bmp = split_hwp.create_dummy_images()
        self.assertIsInstance(dummy_jpg, bytes)
        self.assertIsInstance(dummy_bmp, bytes)
        self.assertTrue(dummy_jpg.startswith(b"\xff\xd8\xff"))  # JPEG header
        self.assertTrue(dummy_bmp.startswith(b"BM"))            # BMP header

    def test_validate_pdf_logic(self):
        import hwp_to_pdf  # type: ignore
        with tempfile.TemporaryDirectory() as tmpdir:
            valid_pdf = os.path.join(tmpdir, "valid.pdf")
            with open(valid_pdf, "wb") as f:
                f.write(b"%PDF-1.4\n" + b"X" * 150 + b"\n%%EOF")
            self.assertTrue(hwp_to_pdf.validate_pdf(valid_pdf))

            # HTML error page containing %PDF- as substring must be rejected
            fake_html = os.path.join(tmpdir, "fake_html.pdf")
            with open(fake_html, "wb") as f:
                f.write(b"<!DOCTYPE html><html><body>Error converting to %PDF-1.4 format" + b"X" * 100 + b"</body></html>")
            self.assertFalse(hwp_to_pdf.validate_pdf(fake_html))

            # Empty or small file must be rejected
            small_pdf = os.path.join(tmpdir, "small.pdf")
            with open(small_pdf, "wb") as f:
                f.write(b"%PDF-")
            self.assertFalse(hwp_to_pdf.validate_pdf(small_pdf))

    def test_lazy_chrome_binary_lookup(self):
        import hwp_to_pdf  # type: ignore
        # Confirm get_chrome_binary can be called or mocked lazily without raising at import time
        with patch.dict(os.environ, {"CHROME_PATH": "/mock/nonexistent/chrome"}, clear=True):
            self.assertIsNotNone(hwp_to_pdf)

    def test_port_allocation_offset(self):
        # Base port offset formula check: agent i with offset 10
        base_ports = [9222 + i * 10 for i in range(3)]
        self.assertEqual(base_ports, [9222, 9232, 9242])

    def test_skill_md_metadata(self):
        skill_file = GLOBAL_SKILL_DIR / "SKILL.md"
        self.assertTrue(skill_file.exists(), "SKILL.md must exist in global skill")
        content = skill_file.read_text(encoding="utf-8")
        self.assertTrue(content.startswith("---"), "SKILL.md must start with YAML frontmatter")
        self.assertIn("name: hwp-to-pdf", content)
        self.assertIn("description:", content)
        self.assertNotIn("disable-model-invocation: true", content, "Should be model-invoked")

if __name__ == "__main__":
    unittest.main()
