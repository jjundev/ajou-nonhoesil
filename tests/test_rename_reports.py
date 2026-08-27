import unittest
import os
import tempfile
import unicodedata
import fitz
from scripts.rename_reports import (
    clean_unicode,
    extract_date_from_text,
    extract_report_metadata,
    build_rename_plan,
    execute_renaming
)

class TestRenameReports(unittest.TestCase):
    def test_clean_unicode(self):
        nfd_str = unicodedata.normalize('NFD', '프로젝트 예비보고서.pdf')
        nfc_str = clean_unicode(nfd_str)
        self.assertEqual(unicodedata.is_normalized('NFC', nfc_str), True)
        self.assertEqual(nfc_str, '프로젝트 예비보고서.pdf')

    def test_extract_date_formats(self):
        self.assertEqual(extract_date_from_text("제출일: 2020. 09. 08"), "200908")
        self.assertEqual(extract_date_from_text("제출일\n: 2018년10월19일금요일"), "181019")
        self.assertEqual(extract_date_from_text("제출일자 : 2016-03-14"), "160314")
        self.assertEqual(extract_date_from_text("실험제목: DAC / ADC\n2015.11.27"), "151127")
        self.assertEqual(extract_date_from_text("날짜 없는 텍스트"), None)
        # Filename fallback
        self.assertEqual(extract_date_from_text("날짜 없음", "실험10 181130제출 결과보고서.pdf"), "181130")

    def test_part_suffix_and_special_doc_types(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, "실험2_part1.pdf")
            doc = fitz.open()
            page = doc.new_page()
            page.insert_text((50, 50), "실험2 예비보고서\n제출일 : 2019.03.20")
            doc.save(pdf_path)
            doc.close()

            meta = extract_report_metadata(pdf_path, "예비보고서", "실험2")
            self.assertEqual(meta["part_suffix"], "_part1")
            self.assertEqual(meta["date_str"], "190320")
            self.assertEqual(meta["doc_type"], "예비보고서")

    def test_special_doc_type_detection(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, "설계계획서.pdf")
            doc = fitz.open()
            page = doc.new_page()
            page.insert_text((50, 50), "최종 프로젝트 설계계획서\n제출일자: 2021-12-01")
            doc.save(pdf_path)
            doc.close()

            meta = extract_report_metadata(pdf_path, "예비보고서", "프로젝트")
            self.assertEqual(meta["doc_type"], "설계계획서")
            self.assertEqual(meta["date_str"], "211201")

    def test_metadata_and_conflict_resolution(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            exp_dir = os.path.join(tmpdir, "실험1")
            os.makedirs(exp_dir)
            
            # Create 2 dummy PDFs with same submission date
            for name, date_text in [("docA.pdf", "제출일: 2020.09.08"), ("docB.pdf", "제출일: 2020.09.08")]:
                doc = fitz.open()
                page = doc.new_page()
                page.insert_text((50, 50), f"실험1 예비보고서\n{date_text}")
                doc.save(os.path.join(exp_dir, name))
                doc.close()

            plan = build_rename_plan([tmpdir], category_hint="예비보고서")
            self.assertEqual(len(plan), 2)
            new_names = sorted([op["new_name"] for op in plan])
            self.assertEqual(new_names, ["실험1 예비보고서 200908_1.pdf", "실험1 예비보고서 200908_2.pdf"])

    def test_execute_renaming_dry_run_and_actual(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            exp_dir = os.path.join(tmpdir, "실험3")
            os.makedirs(exp_dir)
            
            fpath = os.path.join(exp_dir, "old_file.pdf")
            doc = fitz.open()
            page = doc.new_page()
            page.insert_text((50, 50), "실험3 결과보고서\n제출일: 2017.05.10")
            doc.save(fpath)
            doc.close()

            plan = build_rename_plan([tmpdir], category_hint="결과보고서")
            self.assertEqual(len(plan), 1)
            self.assertEqual(plan[0]["new_name"], "실험3 결과보고서 170510.pdf")

            # Dry run test
            res_dry = execute_renaming(plan, dry_run=True)
            self.assertEqual(res_dry["success"], 1)
            self.assertTrue(os.path.exists(fpath))
            self.assertFalse(os.path.exists(plan[0]["new_path"]))

            # Actual run test
            res_actual = execute_renaming(plan, dry_run=False)
            self.assertEqual(res_actual["success"], 1)
            self.assertFalse(os.path.exists(fpath))
            self.assertTrue(os.path.exists(plan[0]["new_path"]))

if __name__ == "__main__":
    unittest.main()
