# 퀴즈 디렉토리 하위 실험별 폴더 분류 계획 (Quiz Folder Categorization Plan)

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `from_the_past/정리/퀴즈/` 하위의 113개 퀴즈 관련 파일들을 `실험1` ~ `실험10` 및 `기타` 폴더로 안전하고 정확하게 자동 분류한다.

**Architecture:** 정규표현식 및 파일명 패턴 기반의 분류 엔진(`classify_quiz_filename`)을 순수 함수로 구현하고, 안전한 이동 및 dry-run을 지원하는 `organize_quiz_directory` 함수를 작성한다. 단위 테스트(`tests/test_quiz_organizer.py`)로 모든 파일명 케이스와 임시 디렉토리 이동 로직을 검증한 뒤 실제 퀴즈 폴더를 분류한다.

**Tech Stack:** Python 3 (standard library: `os`, `re`, `shutil`, `pathlib`, `unittest`)

## Global Constraints

- 대상 디렉토리: `/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/퀴즈`
- 하위 생성 폴더 규격: 기존 `결과보고서`, `예비보고서`와 일관되게 `실험1`, `실험2`, ..., `실험10`, `기타` (공백 없는 형태)
- 데이터 손실 금지: 113개 모든 파일의 존재 확인 및 누락/덮어쓰기 방지
- 독립적 검증 가능: `--dry-run` 및 사전 테스트 지원

---

### Task 1: 퀴즈 분류 모듈 및 단위 테스트 작성 (TDD)

**Files:**
- Create: `scripts/organize_quiz.py`
- Create: `tests/test_quiz_organizer.py`

**Interfaces:**
- Consumes: Standard Python libraries (`os`, `re`, `shutil`, `pathlib`, `unittest`)
- Produces:
  - `classify_quiz_filename(filename: str) -> str`
  - `organize_quiz_directory(source_dir: Path | str, dry_run: bool = False) -> dict[str, list[str]]`

- [x] **Step 1: Write the failing unit tests for quiz categorization**

Create `tests/test_quiz_organizer.py` with comprehensive test cases:

```python
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
```

- [x] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests/test_quiz_organizer.py`
Expected: FAIL (ModuleNotFoundError: No module named 'scripts.organize_quiz')

- [x] **Step 3: Implement `scripts/organize_quiz.py`**

Create `scripts/organize_quiz.py`:

```python
import argparse
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Dict, List


def classify_quiz_filename(filename: str) -> str:
    """
    Classifies a quiz file into '실험1' ~ '실험10' or '기타'.
    """
    # Rule 1: Single digit jpg (1.jpg ~ 9.jpg)
    m_single = re.match(r"^([1-9])\.jpg$", filename, re.IGNORECASE)
    if m_single:
        return f"실험{m_single.group(1)}"

    # Rule 2: quiz_05, quiz_06, quiz_07(1), quiz_09(1)
    m_quiz_num = re.match(r"^quiz_0?([0-9]+)", filename, re.IGNORECASE)
    if m_quiz_num:
        num = int(m_quiz_num.group(1))
        if 1 <= num <= 10:
            return f"실험{num}"

    # Rule 3: 퀴즈1, 퀴즈10, 퀴즈3-1, 퀴즈8-eng
    m_quiz_ko = re.match(r"^퀴즈\s*([0-9]+)", filename)
    if m_quiz_ko:
        num = int(m_quiz_ko.group(1))
        if 1 <= num <= 10:
            return f"실험{num}"

    # Rule 4: 실험 1, 실험10, 실험91.jpg (실험9), etc.
    m_exp = re.match(r"^실험\s*([0-9]+)", filename)
    if m_exp:
        num = int(m_exp.group(1))
        if num == 91:
            return "실험9"
        elif 1 <= num <= 10:
            return f"실험{num}"

    return "기타"


def organize_quiz_directory(
    source_dir: str | Path, dry_run: bool = False
) -> Dict[str, List[str]]:
    """
    Organizes files in source_dir into subdirectories: 실험1 ~ 실험10, 기타.
    Only processes files directly located in source_dir.
    """
    source_path = Path(source_dir).resolve()
    if not source_path.exists() or not source_path.is_dir():
        raise ValueError(f"Directory not found: {source_path}")

    # Prepare categories
    categories = [f"실험{i}" for i in range(1, 11)] + ["기타"]
    results: Dict[str, List[str]] = {cat: [] for cat in categories}

    files = [
        f
        for f in os.listdir(source_path)
        if not f.startswith(".") and (source_path / f).is_file()
    ]

    for fname in sorted(files):
        cat = classify_quiz_filename(fname)
        results[cat].append(fname)

    if not dry_run:
        # Create directories
        for cat in categories:
            (source_path / cat).mkdir(exist_ok=True)

        # Move files
        for cat, flist in results.items():
            dest_dir = source_path / cat
            for fname in flist:
                src_file = source_path / fname
                dest_file = dest_dir / fname
                shutil.move(str(src_file), str(dest_file))

    return results


def main():
    parser = argparse.ArgumentParser(description="Organize quiz files by experiment.")
    parser.add_argument(
        "--target-dir",
        default="from_the_past/정리/퀴즈",
        help="Target quiz directory to organize",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate categorization without moving files",
    )
    args = parser.parse_args()

    target_path = Path(args.target_dir)
    print(f"[*] Processing directory: {target_path}")
    print(f"[*] Dry run mode: {args.dry_run}")

    summary = organize_quiz_directory(target_path, dry_run=args.dry_run)

    total_files = sum(len(v) for v in summary.values())
    print(f"\n[+] Categorization Summary ({total_files} files):")
    for cat, flist in summary.items():
        print(f"  - {cat} ({len(flist)} files):")
        for f in flist:
            print(f"      • {f}")

    if args.dry_run:
        print("\n[!] Dry run complete. No files were moved.")
    else:
        print("\n[+] Successfully organized all files!")


if __name__ == "__main__":
    main()
```

- [x] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests/test_quiz_organizer.py`
Expected: PASS (all tests pass)

---

### Task 2: 실제 디렉토리 Dry Run 및 최종 파일 이동 실행

**Files:**
- Execute: `scripts/organize_quiz.py`
- Modify: `from_the_past/정리/퀴즈/` (Directory structure)

**Interfaces:**
- Consumes: `from_the_past/정리/퀴즈/` (113 files)
- Produces:
  - `from_the_past/정리/퀴즈/실험1/` (8 files)
  - `from_the_past/정리/퀴즈/실험2/` (9 files)
  - `from_the_past/정리/퀴즈/실험3/` (13 files)
  - `from_the_past/정리/퀴즈/실험4/` (9 files)
  - `from_the_past/정리/퀴즈/실험5/` (13 files)
  - `from_the_past/정리/퀴즈/실험6/` (9 files)
  - `from_the_past/정리/퀴즈/실험7/` (14 files)
  - `from_the_past/정리/퀴즈/실험8/` (13 files)
  - `from_the_past/정리/퀴즈/실험9/` (12 files)
  - `from_the_past/정리/퀴즈/실험10/` (7 files)
  - `from_the_past/정리/퀴즈/기타/` (6 files)

- [x] **Step 1: Execute dry run on actual directory**

Run: `python3 scripts/organize_quiz.py --dry-run`
Expected: Outputs exactly 113 categorized files without error.

- [x] **Step 2: Execute actual organization**

Run: `python3 scripts/organize_quiz.py`
Expected: Creates `실험1`~`실험10` and `기타`, moves all 113 files into their respective folders.

- [x] **Step 3: Verify directory contents after move**

Run: `python3 -c "import os; p='from_the_past/정리/퀴즈'; print('Root files:', [f for f in os.listdir(p) if os.path.isfile(os.path.join(p, f)) and not f.startswith('.')]); print('Subdirs:', sorted([d for d in os.listdir(p) if os.path.isdir(os.path.join(p, d))])); print('Total files in subdirs:', sum(len(files) for _, _, files in os.walk(p)))"`
Expected: Root files: `[]`, Subdirs: `['기타', '실험1', '실험10', '실험2', '실험3', '실험4', '실험5', '실험6', '실험7', '실험8', '실험9']`, Total files: 113.

- [x] **Step 4: Commit changes**

```bash
git add scripts/organize_quiz.py tests/test_quiz_organizer.py docs/plans/2026-08-27-quiz-folder-categorization.md
git commit -m "feat: organize quiz folder into per-experiment subdirectories"
```

---

## Verification Plan

### Automated Tests
- Unit test runner:
  `python3 -m unittest tests/test_quiz_organizer.py`
- Full repository test suite:
  `python3 -m unittest discover tests`

### Manual / Structural Verification
- Check that all 113 files are preserved without any missing or duplicated files:
  `python3 -c "import os; print(sum(len(f) for _, _, f in os.walk('from_the_past/정리/퀴즈')))"`
- Check folder naming and hierarchy matches `결과보고서` and `예비보고서` (`실험1`~`실험10`, `기타`).
