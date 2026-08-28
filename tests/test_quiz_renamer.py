import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.rename_quiz_files import (
    QUIZ_RENAME_MAP,
    rename_quiz_files,
    rollback_quiz_files,
    generate_rename_markdown_table,
)


class TestQuizRenamer(unittest.TestCase):
    def test_mapping_integrity(self):
        # 97 total items
        self.assertEqual(len(QUIZ_RENAME_MAP), 97)
        # All target filenames must be unique
        targets = list(QUIZ_RENAME_MAP.values())
        self.assertEqual(len(targets), len(set(targets)))

    def test_rename_and_rollback_in_tempdir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            backup_json = tmppath / "backup.json"

            # Create sample files from mapping
            sample_keys = [
                "실험1/1.jpg",
                "실험1/퀴즈1.pdf",
                "실험7/실험7_수정.pdf",
                "기타/논회실 퀴즈 소스.pdf",
            ]
            for k in sample_keys:
                src = tmppath / k
                src.parent.mkdir(parents=True, exist_ok=True)
                src.write_text("content", encoding="utf-8")

            # 1. Dry run
            renamed_dry = rename_quiz_files(tmppath, dry_run=True)
            self.assertEqual(len(renamed_dry), len(sample_keys))
            self.assertTrue((tmppath / "실험1/1.jpg").exists())

            # 2. Apply
            renamed_real = rename_quiz_files(
                tmppath, dry_run=False, backup_file=backup_json
            )
            self.assertEqual(len(renamed_real), len(sample_keys))
            self.assertTrue((tmppath / "실험1/실험1 퀴즈 기출_채점본.jpg").exists())
            self.assertTrue((tmppath / "실험1/실험1 퀴즈 기출_단답형.pdf").exists())
            self.assertTrue((tmppath / "실험7/실험7 퀴즈 강의자료 2016-2 (20p).pdf").exists())
            self.assertTrue((tmppath / "기타/논회실 퀴즈 종합 족보 (40p).pdf").exists())
            self.assertFalse((tmppath / "실험1/1.jpg").exists())

            # 3. Generate Markdown table
            md_path = tmppath / "RENAME_MAP.md"
            generate_rename_markdown_table(tmppath, md_path)
            self.assertTrue(md_path.exists())
            md_content = md_path.read_text(encoding="utf-8")
            self.assertIn("실험1 퀴즈 기출_채점본.jpg", md_content)

            # 4. Rollback
            restored_count = rollback_quiz_files(backup_json)
            self.assertEqual(restored_count, len(sample_keys))
            self.assertTrue((tmppath / "실험1/1.jpg").exists())
            self.assertTrue((tmppath / "실험1/퀴즈1.pdf").exists())
            self.assertFalse((tmppath / "실험1/실험1 퀴즈 기출_채점본.jpg").exists())


if __name__ == "__main__":
    unittest.main()
