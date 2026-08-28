import os
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.organize_quiz import classify_quiz_filename, organize_quiz_directory


class TestQuizOrganizer(unittest.TestCase):
    def test_classify_single_digit_jpg(self):
        self.assertEqual(classify_quiz_filename("1.jpg"), "실험1")
        self.assertEqual(classify_quiz_filename("2.jpg"), "실험2")
        self.assertEqual(classify_quiz_filename("7.jpg"), "실험7")
        self.assertEqual(classify_quiz_filename("9.jpg"), "실험9")

    def test_classify_quiz_prefix(self):
        self.assertEqual(classify_quiz_filename("quiz_05.pdf"), "실험5")
        self.assertEqual(classify_quiz_filename("quiz_06.hwp"), "실험6")
        self.assertEqual(classify_quiz_filename("quiz_07(1).pdf"), "실험7")
        self.assertEqual(classify_quiz_filename("quiz_09(1).hwp"), "실험9")

    def test_classify_korean_quiz_prefix(self):
        self.assertEqual(classify_quiz_filename("퀴즈1.docx"), "실험1")
        self.assertEqual(classify_quiz_filename("퀴즈1_답.docx"), "실험1")
        self.assertEqual(classify_quiz_filename("퀴즈2_2017-1.docx"), "실험2")
        self.assertEqual(classify_quiz_filename("퀴즈3-1.docx"), "실험3")
        self.assertEqual(classify_quiz_filename("퀴즈8-eng.docx"), "실험8")
        self.assertEqual(classify_quiz_filename("퀴즈10.docx"), "실험10")

    def test_classify_experiment_names(self):
        self.assertEqual(classify_quiz_filename("실험 1 (2).doc"), "실험1")
        self.assertEqual(classify_quiz_filename("실험1+답.jpg"), "실험1")
        self.assertEqual(classify_quiz_filename("실험4_예상 (2).docx"), "실험4")
        self.assertEqual(classify_quiz_filename("실험5퀴즈_문제.docx"), "실험5")
        self.assertEqual(classify_quiz_filename("실험7_수정.pptx"), "실험7")
        self.assertEqual(classify_quiz_filename("실험8_Counter.docx"), "실험8")
        self.assertEqual(classify_quiz_filename("실험8 최종 - 답안 단순화!.docx"), "실험8")
        self.assertEqual(classify_quiz_filename("실험91.jpg"), "실험9")
        self.assertEqual(classify_quiz_filename("실험 10.pdf"), "실험10")

    def test_classify_others(self):
        self.assertEqual(classify_quiz_filename("논회실 퀴즈 소스.pdf"), "기타")
        self.assertEqual(classify_quiz_filename("이외 실험.pdf"), "기타")
        self.assertEqual(classify_quiz_filename("이외 실험2.pdf"), "기타")
        self.assertEqual(classify_quiz_filename("6,10은 미안해~.txt"), "기타")
        self.assertEqual(classify_quiz_filename("KakaoTalk_20151001_155445279.png"), "기타")
        self.assertEqual(classify_quiz_filename("KakaoTalk_20151001_160027915.jpg"), "기타")

    def test_organize_quiz_directory_in_tempdir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            sample_files = [
                "1.jpg",
                "퀴즈2.docx",
                "실험 3.pdf",
                "실험4+-+정답.pdf",
                "quiz_05.pdf",
                "실험 10.pdf",
                "이외 실험.pdf",
            ]
            for sf in sample_files:
                (tmppath / sf).write_text("dummy", encoding="utf-8")

            # Dry run test
            res_dry = organize_quiz_directory(tmppath, dry_run=True)
            self.assertEqual(len(res_dry["실험1"]), 1)
            # Files should still be in root during dry run
            self.assertTrue((tmppath / "1.jpg").exists())

            # Real run test
            res_real = organize_quiz_directory(tmppath, dry_run=False)
            self.assertTrue((tmppath / "실험1" / "1.jpg").exists())
            self.assertTrue((tmppath / "실험2" / "퀴즈2.docx").exists())
            self.assertTrue((tmppath / "실험3" / "실험 3.pdf").exists())
            self.assertTrue((tmppath / "실험4" / "실험4+-+정답.pdf").exists())
            self.assertTrue((tmppath / "실험5" / "quiz_05.pdf").exists())
            self.assertTrue((tmppath / "실험10" / "실험 10.pdf").exists())
            self.assertTrue((tmppath / "기타" / "이외 실험.pdf").exists())
            self.assertFalse((tmppath / "1.jpg").exists())


if __name__ == "__main__":
    unittest.main()
