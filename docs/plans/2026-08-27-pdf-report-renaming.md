# PDF 보고서 파일명 표준화 및 정렬 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `from_the_past/정리/예비보고서` 및 `from_the_past/정리/결과보고서` 하위 96개 PDF 문서의 첫 페이지 텍스트를 파싱하여 `실험2 예비보고서 200908.pdf` 형식으로 파일명을 일괄 표준화 및 정렬한다.

**Architecture:** `PyMuPDF (fitz)`를 기반으로 PDF 첫 페이지에서 제출일/실험일 및 문서 유형 메타데이터를 추출하고, 정규화된 네이밍 규칙 및 중복 충돌 방지 알고리즘(순번/파트 접미사 보존)을 통해 안전한 1:1 매핑 계획을 생성한 뒤 CLI를 통해 드라이런 검증 및 적용을 수행한다.

**Tech Stack:** Python 3, PyMuPDF (fitz), unicodedata (NFC), unittest

## Global Constraints

- 대상 디렉터리: `/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/예비보고서` 및 `.../결과보고서` 하위 폴더만 처리한다.
- 보존 디렉터리: `강의노트`, `논회 강의노트`, `나머지`, `퀴즈` 폴더는 절대 변경하지 않는다.
- 파일 포맷: `[실험N 또는 프로젝트] [보고서유형] [YYMMDD][추가식별자].pdf` 포맷을 준수한다. 날짜 미상 시 날짜를 생략한다.
- 충돌 방지: 동일 폴더 내 중복 파일명 생성 시 `_1`, `_2` 순번 또는 `_partN` / `_(수정)` 등 고유 접미사를 결합하여 덮어쓰기로 인한 데이터 유실을 0%로 보장한다.
- 유니코드: macOS NFD 자소 분리 방지를 위해 모든 파일명은 NFC(`unicodedata.normalize('NFC', ...)`)로 정규화한다.
- 안전성: 기본 실행 모드는 `--dry-run`이며, 1:1 매핑 검증 완료 후에만 `--apply`로 파일명을 변경한다.

---

### Task 1: 보고서 메타데이터 추출 및 네이밍 로직 모듈 개발

**Files:**
- Create: `scripts/rename_reports.py`
- Test: `tests/test_rename_reports.py`

**Interfaces:**
- Consumes: `fitz.Document`, PDF 파일 경로, 상위 카테고리명, 폴더명
- Produces: 
  - `extract_report_metadata(pdf_path: str, category: str, folder_name: str) -> dict`
  - `build_rename_plan(base_dirs: list[str]) -> list[dict]`
  - `execute_renaming(plan: list[dict], dry_run: bool = True) -> dict`

- [ ] **Step 1: Write the failing tests for metadata extraction and collision resolution**

```python
# tests/test_rename_reports.py
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

    def test_extract_date_formats(self):
        self.assertEqual(extract_date_from_text("제출일: 2020. 09. 08"), "200908")
        self.assertEqual(extract_date_from_text("제출일\n: 2018년10월19일금요일"), "181019")
        self.assertEqual(extract_date_from_text("제출일자 : 2016-03-14"), "160314")
        self.assertEqual(extract_date_from_text("실험제목: DAC / ADC\n2015.11.27"), "151127")
        self.assertEqual(extract_date_from_text("날짜 없는 텍스트"), None)

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

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests/test_rename_reports.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.rename_reports'` or missing functions.

- [ ] **Step 3: Implement `scripts/rename_reports.py`**

```python
# scripts/rename_reports.py
import os
import re
import unicodedata
from collections import defaultdict
import fitz

def clean_unicode(text: str) -> str:
    return unicodedata.normalize('NFC', text)

def extract_date_from_text(text: str, filename: str = "") -> str | None:
    text = clean_unicode(text)
    # 1. Explicit 제출일 / 제출일자 / 제출
    m = re.search(r"제출(?:일|일자)?\s*[:\s]*([0-9]{4}[.\-/년\s]+[0-9]{1,2}[.\-/월\s]+[0-9]{1,2})", text)
    if not m:
        m = re.search(r"제출\s*\n\s*:\s*([0-9]{4}[.\-/년\s]+[0-9]{1,2}[.\-/월\s]+[0-9]{1,2})", text)
    if not m:
        # General date YYYY.MM.DD or YYYY년 M월 D일 or YYYY-MM-DD
        m = re.search(r"(20[0-9]{2}[.\-/년\s]+[0-9]{1,2}[.\-/월\s]+[0-9]{1,2})", text)
    
    if m:
        raw = m.group(1)
        dm = re.search(r"(\d{4})[^\d]+(\d{1,2})[^\d]+(\d{1,2})", raw)
        if dm:
            y = dm.group(1)[2:]
            mo = dm.group(2).zfill(2)
            d = dm.group(3).zfill(2)
            return f"{y}{mo}{d}"
            
    # Fallback to filename if text has no date (e.g. 실험10 181130제출 결과보고서.pdf)
    if filename:
        fn_m = re.search(r"(?:16|17|18|19|20)(\d{4})", filename)
        if fn_m and len(fn_m.group(0)) == 6:
            return fn_m.group(0)

    return None

def extract_report_metadata(pdf_path: str, category: str, folder_name: str) -> dict:
    pdf_path = clean_unicode(pdf_path)
    folder_name = clean_unicode(folder_name)
    fname = clean_unicode(os.path.basename(pdf_path))
    
    text = ""
    try:
        doc = fitz.open(pdf_path)
        for p in range(min(2, len(doc))):
            text += "\n" + doc[p].get_text()
        doc.close()
    except Exception as e:
        print(f"Warning: Failed to read {pdf_path}: {e}")
        
    text = clean_unicode(text)
    date_str = extract_date_from_text(text, fname)

    # Sub-part / suffix in filename (e.g. part1, 예보1, 예보2, 수정)
    part_suffix = ""
    part_m = re.search(r"(part\d+|part_\d+|예보\d+|\(수정\)|\(\d+\.\d+수정\))", fname, re.IGNORECASE)
    if part_m:
        part_suffix = "_" + part_m.group(1).replace(" ", "")

    subject = folder_name
    doc_type = category
    if "설계계획서" in fname or "설계계획서" in text[:300]:
        doc_type = "설계계획서"
    elif "설계예비보고서" in fname or "설계예비" in text[:300]:
        doc_type = "설계예비보고서"
    elif "설계결과보고서" in fname or "설계결과보고서" in text[:300] or "설계보고서" in text[:300]:
        doc_type = "설계보고서"

    return {
        "old_name": fname,
        "old_path": pdf_path,
        "subject": subject,
        "doc_type": doc_type,
        "date_str": date_str,
        "part_suffix": part_suffix
    }

def build_rename_plan(base_dirs: list[str], category_hint: str = "") -> list[dict]:
    plan = []
    for bdir in base_dirs:
        bdir = clean_unicode(bdir)
        if not os.path.exists(bdir):
            continue
        cat = category_hint or os.path.basename(bdir)
        for folder in sorted(os.listdir(bdir)):
            fpath = os.path.join(bdir, folder)
            if not os.path.isdir(fpath):
                continue
            norm_folder = clean_unicode(folder)
            pdf_files = [f for f in sorted(os.listdir(fpath)) if f.lower().endswith(".pdf")]
            
            parsed_list = []
            name_counts = defaultdict(int)
            for f in pdf_files:
                full_pdf = os.path.join(fpath, f)
                parsed = extract_report_metadata(full_pdf, cat, norm_folder)
                parsed_list.append(parsed)
                
            for item in parsed_list:
                base_new = f"{item['subject']} {item['doc_type']}"
                if item["date_str"]:
                    base_new += f" {item['date_str']}"
                if item["part_suffix"]:
                    base_new += f"{item['part_suffix']}"
                
                name_counts[base_new] += 1
                item["tentative_name"] = base_new
                
            used = defaultdict(int)
            for item in parsed_list:
                t = item["tentative_name"]
                if name_counts[t] > 1:
                    used[t] += 1
                    final_new = f"{t}_{used[t]}.pdf"
                else:
                    final_new = f"{t}.pdf"
                
                new_path = os.path.join(fpath, final_new)
                plan.append({
                    "old_path": item["old_path"],
                    "old_name": item["old_name"],
                    "new_name": final_new,
                    "new_path": new_path,
                    "folder": norm_folder,
                    "category": cat
                })
    return plan

def execute_renaming(plan: list[dict], dry_run: bool = True) -> dict:
    results = {"success": 0, "skipped": 0, "errors": []}
    for op in plan:
        old_p = op["old_path"]
        new_p = op["new_path"]
        if old_p == new_p:
            results["skipped"] += 1
            continue
        if dry_run:
            results["success"] += 1
        else:
            try:
                os.rename(old_p, new_p)
                results["success"] += 1
            except Exception as e:
                results["errors"].append((old_p, str(e)))
    return results
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests/test_rename_reports.py`
Expected: `Ran 3 tests in ...s - OK`

- [ ] **Step 5: Commit**

```bash
git add scripts/rename_reports.py tests/test_rename_reports.py
git commit -m "feat: add PDF report metadata extraction and renaming logic"
```

---

### Task 2: CLI 실행 스크립트 및 전체 96개 파일 Dry-Run 사전 검증

**Files:**
- Modify: `scripts/rename_reports.py`
- Test: `tests/test_rename_reports.py`

**Interfaces:**
- Consumes: CLI 인자 (`--apply`, `--dry-run`, `--base-dirs`)
- Produces: CLI 출력 (표준화 변경 내역 테이블, 중복 0건 검증 메시지, 실행 결과 요약)

- [ ] **Step 1: Write test for CLI argument parsing and execution**

```python
# In tests/test_rename_reports.py
    def test_cli_dry_run_and_apply(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            exp_dir = os.path.join(tmpdir, "실험2")
            os.makedirs(exp_dir)
            doc_path = os.path.join(exp_dir, "raw_report.pdf")
            doc = fitz.open()
            page = doc.new_page()
            page.insert_text((50, 50), "제출일: 2020.09.08")
            doc.save(doc_path)
            doc.close()

            plan = build_rename_plan([tmpdir], category_hint="예비보고서")
            # Dry run: file remains untouched
            res_dry = execute_renaming(plan, dry_run=True)
            self.assertEqual(res_dry["success"], 1)
            self.assertTrue(os.path.exists(doc_path))

            # Apply: file renamed
            res_apply = execute_renaming(plan, dry_run=False)
            self.assertEqual(res_apply["success"], 1)
            self.assertFalse(os.path.exists(doc_path))
            self.assertTrue(os.path.exists(os.path.join(exp_dir, "실험2 예비보고서 200908.pdf")))
```

- [ ] **Step 2: Run test to verify it passes**

Run: `python3 -m unittest tests/test_rename_reports.py`
Expected: PASS

- [ ] **Step 3: Add main CLI entry point in `scripts/rename_reports.py`**

```python
# Add to scripts/rename_reports.py
import argparse

def main():
    parser = argparse.ArgumentParser(description="Rename PDF reports according to first-page metadata")
    parser.add_argument("--apply", action="store_true", help="Apply actual renames (default: dry-run)")
    args = parser.parse_args()

    default_base_dirs = [
        "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/예비보고서",
        "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/결과보고서"
    ]
    
    plan = build_rename_plan(default_base_dirs)
    print(f"=== Found {len(plan)} PDF files to process ===")
    for op in plan:
        status = "[UNCHANGED]" if op["old_path"] == op["new_path"] else "[RENAME]"
        print(f"{status} [{op['category']}/{op['folder']}] {op['old_name']} -> {op['new_name']}")

    if not args.apply:
        print("\n[DRY RUN] No files were modified. Run with --apply to execute renames.")
    else:
        res = execute_renaming(plan, dry_run=False)
        print(f"\n[APPLIED] Success: {res['success']}, Skipped: {res['skipped']}, Errors: {len(res['errors'])}")
        if res["errors"]:
            for path, err in res["errors"]:
                print(f"  Error on {path}: {err}")

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Execute Dry-run on actual repository files to inspect and verify all 96 mappings**

Run: `python3 scripts/rename_reports.py`
Expected: Output showing all 96 PDF mappings with zero collision errors.

- [ ] **Step 5: Commit**

```bash
git add scripts/rename_reports.py tests/test_rename_reports.py
git commit -m "feat: complete CLI runner with dry-run support"
```

---

### Task 3: 실전 적용(Apply) 및 결과 무결성 검증

**Files:**
- Execute: `scripts/rename_reports.py --apply`
- Verify: `from_the_past/정리/예비보고서` 및 `from_the_past/정리/결과보고서` 하위 전체 PDF 파일 상태

**Interfaces:**
- Consumes: 실제 파일시스템
- Produces: 96개 표준 파일명으로 변경된 PDF 파일들

- [ ] **Step 1: Execute actual renaming with `--apply`**

Run: `python3 scripts/rename_reports.py --apply`
Expected: `[APPLIED] Success: 96 (or unchanged), Skipped: 0, Errors: 0`

- [ ] **Step 2: Verify total file count, naming structure, and no remaining HWP or broken files**

Run command:
```bash
python3 -c '
import os
import unicodedata

base_dirs = [
    "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/예비보고서",
    "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/결과보고서"
]

total = 0
for bdir in base_dirs:
    for root, dirs, files in os.walk(bdir):
        for f in files:
            if f.lower().endswith(".pdf"):
                total += 1
                norm_f = unicodedata.normalize("NFC", f)
                assert unicodedata.is_normalized("NFC", norm_f)
                print(f"[{os.path.basename(root)}] {norm_f}")

print(f"\nTotal verified PDF files: {total}")
assert total == 96
'
```
Expected: `Total verified PDF files: 96` without any assertion failures.

- [ ] **Step 3: Run full unittest test suite**

Run: `python3 -m unittest tests/test_rename_reports.py`
Expected: All tests pass.

- [ ] **Step 4: Commit**

```bash
git add from_the_past/정리/
git commit -m "chore: standardize all PDF report filenames in 예비보고서 and 결과보고서"
```
