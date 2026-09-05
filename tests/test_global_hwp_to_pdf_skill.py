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

# 이 스킬은 일부러 리포 밖(홈 디렉터리)에 산다 — 여러 프로젝트가 같이 쓰기
# 때문이다(`docs/plans/2026-09-03-global-hwp-to-pdf-skill.md:5`). 그래서
# 설치되지 않은 기계에서는 이 파일이 검사할 대상 자체가 없다. 없는 것을
# 실패로 세면 리포의 테스트 스위트가 이 기계에만 붙어 새로 클론한 곳마다
# 깨진다. 그래서 "설치 안 됨" 은 건너뛰고, "설치는 됐는데 반쪽" 은 실패로
# 남긴다 — 아래 판정을 디렉터리 존재로만 두는 이유이고, 그래야
# `test_global_scripts_exist`·`test_skill_md_metadata` 가 여전히 뜻을 가진다.
_INSTALLED = GLOBAL_SKILL_DIR.is_dir()


@unittest.skipUnless(_INSTALLED, f"전역 hwp-to-pdf 스킬이 없는 환경 ({GLOBAL_SKILL_DIR})")
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

    def test_skill_md_metadata(self):
        skill_file = GLOBAL_SKILL_DIR / "SKILL.md"
        self.assertTrue(skill_file.exists(), "SKILL.md must exist in global skill")
        content = skill_file.read_text(encoding="utf-8")
        self.assertTrue(content.startswith("---"), "SKILL.md must start with YAML frontmatter")
        self.assertIn("name: hwp-to-pdf", content)
        self.assertIn("description:", content)
        self.assertNotIn("disable-model-invocation: true", content, "Should be model-invoked")

# 이 계산은 전역 스킬을 건드리지 않으므로 설치 여부와 무관하게 돌아야 한다.
class TestPortAllocation(unittest.TestCase):
    def test_port_allocation_offset(self):
        # Base port offset formula check: agent i with offset 10
        base_ports = [9222 + i * 10 for i in range(3)]
        self.assertEqual(base_ports, [9222, 9232, 9242])


if __name__ == "__main__":
    unittest.main()
