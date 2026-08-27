import unittest
import os
import json
import tempfile
import unicodedata
import fitz
from scripts.rename_reports import (
    clean_unicode,
    extract_date_from_text,
    extract_report_metadata,
    build_rename_plan,
    execute_renaming,
    save_audit_log,
    main
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
        # Filename fallback with valid 6-digit date
        self.assertEqual(extract_date_from_text("날짜 없음", "실험10 181130제출 결과보고서.pdf"), "181130")
        # Filename fallback with student ID (must not be parsed as date)
        self.assertEqual(extract_date_from_text("날짜 없음", "201423042_홍길동_예비.pdf"), None)
        self.assertEqual(extract_date_from_text("날짜 없음", "201823012_결과.pdf"), None)

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

    def test_execute_renaming_chain_swap(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            exp_dir = os.path.join(tmpdir, "실험5")
            os.makedirs(exp_dir)

            file_a = os.path.join(exp_dir, "file_a.pdf")
            file_b = os.path.join(exp_dir, "file_b.pdf")
            with open(file_a, "w") as f:
                f.write("content A")
            with open(file_b, "w") as f:
                f.write("content B")

            # Swap: file_a -> file_b, file_b -> file_c
            file_c = os.path.join(exp_dir, "file_c.pdf")
            plan = [
                {
                    "old_path": file_a,
                    "old_name": "file_a.pdf",
                    "new_path": file_b,
                    "new_name": "file_b.pdf",
                    "folder": "실험5",
                    "category": "예비보고서"
                },
                {
                    "old_path": file_b,
                    "old_name": "file_b.pdf",
                    "new_path": file_c,
                    "new_name": "file_c.pdf",
                    "folder": "실험5",
                    "category": "예비보고서"
                }
            ]

            res_dry = execute_renaming(plan, dry_run=True)
            self.assertEqual(res_dry["success"], 2)
            self.assertEqual(len(res_dry["errors"]), 0)

            res_actual = execute_renaming(plan, dry_run=False)
            self.assertEqual(res_actual["success"], 2)
            self.assertEqual(len(res_actual["errors"]), 0)

            with open(file_b, "r") as f:
                self.assertEqual(f.read(), "content A")
            with open(file_c, "r") as f:
                self.assertEqual(f.read(), "content B")

    def test_execute_renaming_defensive_target_collision(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            exp_dir = os.path.join(tmpdir, "실험4")
            os.makedirs(exp_dir)

            source_file = os.path.join(exp_dir, "source.pdf")
            unmanaged_target = os.path.join(exp_dir, "existing_other.pdf")
            with open(source_file, "w") as f:
                f.write("source content")
            with open(unmanaged_target, "w") as f:
                f.write("unmanaged content")

            plan = [{
                "old_path": source_file,
                "old_name": "source.pdf",
                "new_path": unmanaged_target,
                "new_name": "existing_other.pdf",
                "folder": "실험4",
                "category": "예비보고서"
            }]

            # Both dry run and actual run should detect collision defensively
            res_dry = execute_renaming(plan, dry_run=True)
            self.assertEqual(len(res_dry["errors"]), 1)
            self.assertIn("Target collision", res_dry["errors"][0][1])

            res_actual = execute_renaming(plan, dry_run=False)
            self.assertEqual(len(res_actual["errors"]), 1)
            self.assertIn("Target collision", res_actual["errors"][0][1])
            # Ensure target content wasn't overwritten
            with open(unmanaged_target, "r") as f:
                self.assertEqual(f.read(), "unmanaged content")

    def test_save_audit_log(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            audit_file = os.path.join(tmpdir, "audit", "renaming_audit.json")
            sample_plan = [{
                "old_path": "/tmp/a.pdf",
                "old_name": "a.pdf",
                "new_path": "/tmp/b.pdf",
                "new_name": "b.pdf",
                "folder": "실험1",
                "category": "예비보고서"
            }]
            exec_res = {"success": 1, "skipped": 0, "errors": []}
            saved_path = save_audit_log(sample_plan, audit_path=audit_file, execution_results=exec_res)
            self.assertTrue(os.path.exists(saved_path))

            with open(saved_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.assertEqual(data["total_files"], 1)
            self.assertEqual(data["renames"], 1)
            self.assertEqual(data["unchanged"], 0)
            self.assertEqual(data["plan"], sample_plan)
            self.assertEqual(data["execution"], exec_res)

    def test_cli_dry_run_and_apply(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = os.path.join(tmpdir, "예비보고서")
            exp_dir = os.path.join(base_dir, "실험2")
            os.makedirs(exp_dir)
            doc_path = os.path.join(exp_dir, "raw_report.pdf")
            doc = fitz.open()
            page = doc.new_page()
            page.insert_text((50, 50), "제출일: 2020.09.08")
            doc.save(doc_path)
            doc.close()

            audit_log_path = os.path.join(tmpdir, "audit.json")

            # CLI dry-run
            ret_dry = main([base_dir, "--dry-run", "--audit-log", audit_log_path])
            self.assertEqual(ret_dry, 0)
            self.assertTrue(os.path.exists(doc_path))
            self.assertTrue(os.path.exists(audit_log_path))

            # CLI apply
            ret_apply = main([base_dir, "--apply", "--audit-log", audit_log_path])
            self.assertEqual(ret_apply, 0)
            self.assertFalse(os.path.exists(doc_path))
            self.assertTrue(os.path.exists(os.path.join(exp_dir, "실험2 예비보고서 200908.pdf")))

if __name__ == "__main__":
    unittest.main()
