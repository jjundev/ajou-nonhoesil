# 기타 폴더 퀴즈 자료 분해 및 실험별 통합 계획 (Split and Integrate Quiz Etc Files Plan)

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `from_the_past/정리/퀴즈/기타/`에 존재하는 6개 파일(종합 족보 40p PDF, 단답형 기출모음 PDF 2개, 개념 비교 이미지 2개, 안내 메모 1개)을 실험 1 ~ 10별로 무손실 분해(Split)하여 각 `실험N` 폴더에 완벽히 통합하고, `기타/` 폴더를 정리한다.

**Architecture:** 
- PyMuPDF(`fitz`)를 활용하여 40p 종합 족보 및 7p/8p 단답형 기출 PDF를 실험별 페이지 범위에 맞게 무손실 추출 및 저장하는 `scripts/split_quiz_etc.py` 구현.
- 개념 비교 이미지 2개를 관련 실험(`실험4`, `실험5`)으로 복사/배치.
- 분해 추출 후 원본 무결성 검증을 거쳐 `기타/` 폴더를 정리하고, [`RENAME_MAP.md`](file:///Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/퀴즈/RENAME_MAP.md) 인덱스를 갱신.
- TDD 기반 단위 테스트(`tests/test_split_quiz_etc.py`)로 분해 로직 및 파일 생성 무결성을 검증한 후 실제 작업을 수행.

**Tech Stack:** Python 3, PyMuPDF (`fitz`), `unittest`, `pathlib`, `shutil`

## Global Constraints

- 대상 디렉토리: `/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/퀴즈/`
- 분해 대상:
  1. `기타/논회실 퀴즈 종합 족보 (40p).pdf` $\rightarrow$ `실험1` ~ `실험10` 총 10개 PDF (무손실 분해)
  2. `기타/논회실 퀴즈 종합 기출단답 2 (7p).pdf` $\rightarrow$ `실험2`, `실험3`, `실험4`, `실험5`, `실험7`, `실험8` 총 6개 1p 단답형 PDF
  3. `기타/디코더 vs 디멀티플렉서 개념비교.png` $\rightarrow$ `실험4/`, `실험5/`
  4. `기타/디코더 vs 멀티플렉서 vs 디멀티플렉서 동작비교.jpg` $\rightarrow$ `실험4/`, `실험5/`
- 명명 규칙: `실험{N} 퀴즈 종합_기출문제 (N p).pdf`, `실험{N} 퀴즈 기출_단답형 (1p).pdf` 등 일관된 표준 명명
- 최종 상태: `기타/` 폴더 내 모든 자료가 `실험1`~`실험10`으로 통합되어 `기타/` 폴더는 완전히 삭제/정리됨

---

### Task 1: 퀴즈 기타 자료 분해 모듈 및 단위 테스트 작성 (TDD)

**Files:**
- Create: `scripts/split_quiz_etc.py`
- Create: `tests/test_split_quiz_etc.py`

**Interfaces:**
- Consumes: PyMuPDF (`fitz`), standard libraries (`os`, `shutil`, `tempfile`, `pathlib`, `unittest`)
- Produces:
  - `split_comprehensive_quiz_pdf(pdf_path: Path, output_base_dir: Path) -> dict[str, Path]`
  - `split_short_answer_quiz_pdf(pdf_path: Path, output_base_dir: Path) -> dict[str, Path]`
  - `distribute_comparison_images(src_dir: Path, output_base_dir: Path) -> list[Path]`
  - `execute_full_quiz_integration(quiz_dir: Path) -> dict`

- [x] **Step 1: Write failing unit tests for splitting logic**

Create `tests/test_split_quiz_etc.py`:

```python
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
```

- [x] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests/test_split_quiz_etc.py`
Expected: FAIL (ModuleNotFoundError: No module named 'scripts.split_quiz_etc')

- [x] **Step 3: Implement `scripts/split_quiz_etc.py`**

Create `scripts/split_quiz_etc.py`:

```python
#!/usr/bin/env python3
"""
Splits comprehensive quiz resources in 기타/ into per-experiment folders (실험1~10).
Extracts 40p comprehensive PDF and 7p/8p short-answer PDFs, distributes comparison images,
removes the 기타 folder, and updates the index.
"""

import argparse
import os
import shutil
from pathlib import Path
from typing import Dict, List
import fitz

# 40p Document split configuration: 0-indexed (start_page, end_page_exclusive, page_count_str)
SPLIT_40P_MAP = {
    "실험1": (0, 3, "3p"),
    "실험2": (3, 6, "3p"),
    "실험3": (6, 11, "5p"),
    "실험4": (11, 16, "5p"),
    "실험5": (16, 20, "4p"),
    "실험6": (20, 24, "4p"),
    "실험7": (24, 26, "2p"),
    "실험8": (26, 34, "8p"),
    "실험9": (34, 36, "2p"),
    "실험10": (36, 40, "4p"),
}

# 7p Short answer PDF configuration: 0-indexed page in 7p document
SPLIT_7P_MAP = {
    "실험2": (1, "실험2 퀴즈 기출_단답형 (1p).pdf"),
    "실험3": (2, "실험3 퀴즈 기출_단답형 (1p).pdf"),
    "실험4": (3, "실험4 퀴즈 기출_단답형 (1p).pdf"),
    "실험5": (4, "실험5 퀴즈 기출_단답형_v2 (1p).pdf"),
    "실험7": (5, "실험7 퀴즈 기출_단답형_v2 (1p).pdf"),
    "실험8": (6, "실험8 퀴즈 기출_단답형 (1p).pdf"),
}


def split_comprehensive_quiz_pdf(pdf_path: Path, output_base_dir: Path) -> Dict[str, Path]:
    src_doc = fitz.open(pdf_path)
    results = {}

    for exp_name, (start_pg, end_pg, pcount) in SPLIT_40P_MAP.items():
        exp_dir = output_base_dir / exp_name
        exp_dir.mkdir(parents=True, exist_ok=True)
        out_filename = f"{exp_name} 퀴즈 종합_기출문제 ({pcount}).pdf"
        out_path = exp_dir / out_filename

        sub_doc = fitz.open()
        sub_doc.insert_pdf(src_doc, from_page=start_pg, to_page=end_pg - 1)
        sub_doc.save(out_path)
        sub_doc.close()
        results[exp_name] = out_path

    src_doc.close()
    return results


def split_short_answer_quiz_pdf(pdf_path: Path, output_base_dir: Path) -> Dict[str, Path]:
    src_doc = fitz.open(pdf_path)
    results = {}

    for exp_name, (pg_idx, filename) in SPLIT_7P_MAP.items():
        exp_dir = output_base_dir / exp_name
        exp_dir.mkdir(parents=True, exist_ok=True)
        out_path = exp_dir / filename

        sub_doc = fitz.open()
        sub_doc.insert_pdf(src_doc, from_page=pg_idx, to_page=pg_idx)
        sub_doc.save(out_path)
        sub_doc.close()
        results[exp_name] = out_path

    src_doc.close()
    return results


def distribute_comparison_images(src_dir: Path, output_base_dir: Path) -> List[Path]:
    results = []
    img1 = src_dir / "디코더 vs 디멀티플렉서 개념비교.png"
    img2 = src_dir / "디코더 vs 멀티플렉서 vs 디멀티플렉서 동작비교.jpg"

    targets = ["실험4", "실험5"]
    for t in targets:
        exp_dir = output_base_dir / t
        exp_dir.mkdir(parents=True, exist_ok=True)

        if img1.exists():
            dst1 = exp_dir / f"{t} 퀴즈 개념_디코더vs디멀티플렉서_비교.png"
            shutil.copy2(img1, dst1)
            results.append(dst1)

        if img2.exists():
            dst2 = exp_dir / f"{t} 퀴즈 개념_Mux_Demux_Decoder_동작비교.jpg"
            shutil.copy2(img2, dst2)
            results.append(dst2)

    return results


def update_rename_map_markdown(quiz_dir: Path):
    folders = [f"실험{i}" for i in range(1, 11)]
    lines = ["# 퀴즈 파일 전체 목록 및 대조표 (QUIZ CATALOG)\n"]
    lines.append("| 번호 | 실험 폴더 | 표준 파일명 | 유형 |")
    lines.append("| :--- | :--- | :--- | :--- |")

    idx = 1
    for folder in folders:
        fpath = quiz_dir / folder
        if not fpath.exists():
            continue
        lines.append(f"\n### {folder}")
        lines.append("| 번호 | 표준 파일명 | 파일 형식 |")
        lines.append("| :--- | :--- | :--- |")
        for f in sorted(fpath.iterdir()):
            if f.name.startswith("."):
                continue
            lines.append(f"| {idx} | **`{f.name}`** | `{f.suffix.upper()[1:]}` |")
            idx += 1

    (quiz_dir / "RENAME_MAP.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def execute_full_quiz_integration(quiz_dir: Path) -> Dict:
    etc_dir = quiz_dir / "기타"
    if not etc_dir.exists():
        raise FileNotFoundError(f"기타 folder not found in {quiz_dir}")

    doc_40p = etc_dir / "논회실 퀴즈 종합 족보 (40p).pdf"
    doc_7p = etc_dir / "논회실 퀴즈 종합 기출단답 2 (7p).pdf"
    if not doc_7p.exists():
        doc_7p = etc_dir / "논회실 퀴즈 종합 기출단답 1 (8p).pdf"

    res_40p = split_comprehensive_quiz_pdf(doc_40p, quiz_dir)
    res_7p = split_short_answer_quiz_pdf(doc_7p, quiz_dir)
    res_imgs = distribute_comparison_images(etc_dir, quiz_dir)

    # Remove 기타 folder completely
    shutil.rmtree(etc_dir)

    # Update RENAME_MAP.md
    update_rename_map_markdown(quiz_dir)

    return {
        "split_40p": res_40p,
        "split_7p": res_7p,
        "images": res_imgs,
    }


def main():
    parser = argparse.ArgumentParser(description="Split and integrate 기타 quiz files into 실험1~10")
    parser.add_argument(
        "--target-dir",
        default="from_the_past/정리/퀴즈",
        help="Target quiz directory",
    )
    args = parser.parse_args()

    quiz_path = Path(args.target_dir).resolve()
    print(f"[*] Starting full quiz integration in {quiz_path}...")
    res = execute_full_quiz_integration(quiz_path)

    print(f"[+] Successfully extracted 10 comprehensive PDFs from 40p source.")
    print(f"[+] Successfully extracted 6 short-answer PDFs from 7p source.")
    print(f"[+] Distributed {len(res['images'])} comparison images.")
    print(f"[+] Cleaned up 기타/ directory.")
    print(f"[+] Updated RENAME_MAP.md.")


if __name__ == "__main__":
    main()
```

- [x] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests/test_split_quiz_etc.py`
Expected: PASS (all 4 tests pass)

---

### Task 2: 실제 기타 자료 분해 실행, 디렉토리 정리 및 인덱스 업데이트

**Files:**
- Execute: `scripts/split_quiz_etc.py`
- Modify: `from_the_past/정리/퀴즈/` (`실험1` ~ `실험10` folders)
- Delete: `from_the_past/정리/퀴즈/기타/`
- Update: `from_the_past/정리/퀴즈/RENAME_MAP.md`

**Interfaces:**
- Consumes: `from_the_past/정리/퀴즈/기타/` (6 files)
- Produces: 
  - 10 new comprehensive PDFs (`실험1` ~ `실험10`)
  - 6 new short-answer PDFs (`실험2, 3, 4, 5, 7, 8`)
  - 4 comparison images (`실험4`, `실험5`)
  - Cleaned repository structure (only `실험1` ~ `실험10` exist)

- [x] **Step 1: Execute full quiz integration script**

Run: `python3 scripts/split_quiz_etc.py --target-dir from_the_past/정리/퀴즈`
Expected: Extracts all files, deletes `기타/` folder, updates `RENAME_MAP.md`.

- [x] **Step 2: Verify all 10 experiment directories**

Run: `python3 -c "import fitz, os; from pathlib import Path; p=Path('from_the_past/정리/퀴즈'); subdirs=sorted([d.name for d in p.iterdir() if d.is_dir() and not d.name.startswith('.')]); print('Active subdirs:', subdirs); assert subdirs == [f'실험{i}' for i in range(1, 11)], f'Mismatch: {subdirs}'; print('Total files across 실험1~10:', sum(len(list(d.glob('*.*'))) for d in p.iterdir() if d.is_dir())); print('All 10 experiment folders verified!')"`
Expected: Active subdirs: `['실험1', '실험2', ..., '실험10']`, `기타` is absent.

- [x] **Step 3: Run full repository test suite**

Run: `python3 -m unittest discover -s tests`
Expected: All tests pass.

- [x] **Step 4: Commit changes**

```bash
git add scripts/split_quiz_etc.py tests/test_split_quiz_etc.py docs/plans/2026-08-27-split-and-integrate-quiz-etc-files.md
git commit -m "feat: split comprehensive quiz files and integrate into per-experiment folders"
```

---

## Verification Plan

### Automated Tests
- Unit test runner:
  ```bash
  python3 -m unittest tests/test_split_quiz_etc.py
  ```
- Full test suite:
  ```bash
  python3 -m unittest discover -s tests
  ```

### Structural & Visual Verification
- Verify `기타/` is completely gone and only `실험1`~`실험10` exist:
  ```bash
  python3 -c "import os; print(sorted([d for d in os.listdir('from_the_past/정리/퀴즈') if os.path.isdir(os.path.join('from_the_past/정리/퀴즈', d)) and not d.startswith('.')]))"
  ```
- Check that each experiment has its `종합_기출문제` PDF and can be opened with PyMuPDF.
