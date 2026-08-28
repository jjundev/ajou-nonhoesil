import tempfile
import unittest
from pathlib import Path
import fitz

from scripts.split_quiz_etc import (
    split_comprehensive_quiz_pdf,
    split_short_answer_quiz_pdf,
    distribute_comparison_images,
    execute_full_quiz_integration,
)


class TestSplitQuizEtc(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.tmppath = Path(self.tmpdir.name)
        self.quiz_dir = self.tmppath / "퀴즈"
        self.etc_dir = self.quiz_dir / "기타"
        self.etc_dir.mkdir(parents=True)

        for i in range(1, 11):
            (self.quiz_dir / f"실험{i}").mkdir(parents=True)

        # Create dummy 40-page PDF
        doc_40 = fitz.open()
        for i in range(40):
            page = doc_40.new_page()
            page.insert_text((50, 50), f"Page {i+1} Content")
        doc_40.save(self.etc_dir / "논회실 퀴즈 종합 족보 (40p).pdf")
        doc_40.close()

        # Create dummy 7-page PDF
        doc_7 = fitz.open()
        for i in range(7):
            page = doc_7.new_page()
            page.insert_text((50, 50), f"Short Answer Page {i+1}")
        doc_7.save(self.etc_dir / "논회실 퀴즈 종합 기출단답 2 (7p).pdf")
        doc_7.close()

        # Create dummy images and text
        (self.etc_dir / "디코더 vs 디멀티플렉서 개념비교.png").write_bytes(b"\x89PNG\r\n\x1a\n")
        (self.etc_dir / "디코더 vs 멀티플렉서 vs 디멀티플렉서 동작비교.jpg").write_bytes(b"\xff\xd8\xff")
        (self.etc_dir / "기출채점본 실험6,10 누락 안내.txt").write_text("안내", encoding="utf-8")

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_split_comprehensive_pdf(self):
        pdf_path = self.etc_dir / "논회실 퀴즈 종합 족보 (40p).pdf"
        splits = split_comprehensive_quiz_pdf(pdf_path, self.quiz_dir)
        self.assertEqual(len(splits), 10)
        # Check 실험1 has 3 pages
        doc1 = fitz.open(splits["실험1"])
        self.assertEqual(len(doc1), 3)
        doc1.close()
        # Check 실험8 has 8 pages
        doc8 = fitz.open(splits["실험8"])
        self.assertEqual(len(doc8), 8)
        doc8.close()

    def test_split_short_answer_pdf(self):
        pdf_path = self.etc_dir / "논회실 퀴즈 종합 기출단답 2 (7p).pdf"
        splits = split_short_answer_quiz_pdf(pdf_path, self.quiz_dir)
        self.assertEqual(len(splits), 6)
        for exp, p in splits.items():
            doc = fitz.open(p)
            self.assertEqual(len(doc), 1)
            doc.close()

    def test_distribute_images(self):
        copied = distribute_comparison_images(self.etc_dir, self.quiz_dir)
        self.assertEqual(len(copied), 4)  # 2 images * 2 folders (실험4, 실험5)
        self.assertTrue((self.quiz_dir / "실험4" / "실험4 퀴즈 개념_디코더vs디멀티플렉서_비교.png").exists())
        self.assertTrue((self.quiz_dir / "실험5" / "실험5 퀴즈 개념_Mux_Demux_Decoder_동작비교.jpg").exists())

    def test_execute_full_quiz_integration(self):
        result = execute_full_quiz_integration(self.quiz_dir)
        self.assertFalse(self.etc_dir.exists())  # 기타 folder cleaned up
        for i in range(1, 11):
            exp_folder = self.quiz_dir / f"실험{i}"
            split_40_files = list(exp_folder.glob("*종합_기출문제*"))
            self.assertEqual(len(split_40_files), 1)


if __name__ == "__main__":
    unittest.main()
