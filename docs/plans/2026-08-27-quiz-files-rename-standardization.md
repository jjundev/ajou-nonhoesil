# 퀴즈 디렉토리 파일명 표준화 및 구조화 계획 (Quiz Files Rename Standardization Plan)

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `from_the_past/정리/퀴즈/` 하위 97개 파일(PDF 82개, 이미지 14개, 텍스트 1개)의 파일명을 `결과보고서`/`예비보고서`와 일관된 `실험{N} 퀴즈 {유형}_{상세/학기}.{ext}` 패턴으로 표준화하고, 롤백 지원 스크립트 및 `RENAME_MAP.md` 대조 문서를 생성한다.

**Architecture:** 
- `scripts/rename_quiz_files.py`에 97개 파일의 1:1 전단사(bijective) 매핑 테이블을 내장.
- `--dry-run`, `--apply`, `--rollback`, `--generate-index` 명령 지원 및 백업 파일(`.system_generated/quiz_rename_backup.json`) 자동 관리.
- TDD 기반 단위 테스트(`tests/test_quiz_renamer.py`)로 양방향 롤백 무결성을 검증한 후 실제 변경을 적용.

**Tech Stack:** Python 3 (standard library: `os`, `json`, `pathlib`, `unittest`)

## Global Constraints

- 대상 디렉토리: `/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/퀴즈`
- 대상 파일 수: 총 97개 (PDF 82개, 이미지 14개, 텍스트 1개)
- 명명 형식: `실험{N} 퀴즈 {유형}_{상세/학기}.{ext}`
- 안전성: 1:1 유일성(중복 대상명 없음), 백업 JSON 기반 완전 롤백 기능 제공, 대조표(`RENAME_MAP.md`) 생성

---

### Task 1: 퀴즈 파일명 변경/롤백/인덱스 생성 모듈 및 단위 테스트 작성 (TDD)

**Files:**
- Create: `scripts/rename_quiz_files.py`
- Create: `tests/test_quiz_renamer.py`

**Interfaces:**
- Consumes: Standard Python libraries (`os`, `json`, `pathlib`, `unittest`)
- Produces:
  - `QUIZ_RENAME_MAP: dict[str, str]` (97개 상대경로 매핑 딕셔너리)
  - `rename_quiz_files(base_dir: str | Path, dry_run: bool = False, backup_file: Optional[Path] = None) -> dict[str, str]`
  - `rollback_quiz_files(backup_file: str | Path) -> int`
  - `generate_rename_markdown_table(base_dir: str | Path, output_file: str | Path) -> None`

- [x] **Step 1: Write the failing unit tests**

Create `tests/test_quiz_renamer.py`:

```python
import json
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
```

- [x] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests/test_quiz_renamer.py`
Expected: FAIL (ModuleNotFoundError: No module named 'scripts.rename_quiz_files')

- [x] **Step 3: Implement `scripts/rename_quiz_files.py`**

Create `scripts/rename_quiz_files.py` containing complete `QUIZ_RENAME_MAP` and operations:

```python
#!/usr/bin/env python3
"""
Quiz files renaming and rollback utility.
Standardizes 97 quiz files into unified naming convention.
"""

import argparse
import json
import os
from pathlib import Path
from typing import Dict, Optional

QUIZ_RENAME_MAP: Dict[str, str] = {
    # 실험1
    "실험1/1.jpg": "실험1/실험1 퀴즈 기출_채점본.jpg",
    "실험1/실험1+답.jpg": "실험1/실험1 퀴즈 풀이_수기메모.jpg",
    "실험1/실험 1 (2).pdf": "실험1/실험1 퀴즈 예상문제_v1.pdf",
    "실험1/실험 1.pdf": "실험1/실험1 퀴즈 예상문제_v2.pdf",
    "실험1/실험1.pdf": "실험1/실험1 퀴즈 예상문제_v3.pdf",
    "실험1/퀴즈1.pdf": "실험1/실험1 퀴즈 기출_단답형.pdf",
    "실험1/퀴즈1_문제.pdf": "실험1/실험1 퀴즈 기출_문제.pdf",
    "실험1/퀴즈1_답.pdf": "실험1/실험1 퀴즈 기출_정답.pdf",

    # 실험2
    "실험2/2.jpg": "실험2/실험2 퀴즈 기출_채점본.jpg",
    "실험2/퀴즈2.pdf": "실험2/실험2 퀴즈 기출 2016-1.pdf",
    "실험2/퀴즈2_2017-1.pdf": "실험2/실험2 퀴즈 기출 2017-1.pdf",
    "실험2/실험2.pdf": "실험2/실험2 퀴즈 예상문제_v1.pdf",
    "실험2/실험 2.pdf": "실험2/실험2 퀴즈 예상문제_v2.pdf",
    "실험2/실험 2 (2).pdf": "실험2/실험2 퀴즈 예상문제_v3.pdf",
    "실험2/실험2 (2).pdf": "실험2/실험2 퀴즈 예상문제_v4.pdf",

    # 실험3
    "실험3/3.jpg": "실험3/실험3 퀴즈 기출_채점본.jpg",
    "실험3/퀴즈3-1.pdf": "실험3 퀴즈 기출 2016-1.pdf",
    "실험3/실험3+-+정답.pdf": "실험3 퀴즈 기출_정답.pdf",
    "실험3/실험3퀴즈_문제.pdf": "실험3 퀴즈 기출_문제.pdf",
    "실험3/실험 3.pdf": "실험3 퀴즈 예상문제_v1.pdf",
    "실험3/실험 3 (2).pdf": "실험3 퀴즈 예상문제_v2.pdf",
    "실험3/실험 3 (3).pdf": "실험3 퀴즈 예상문제_v3.pdf",
    "실험3/실험3.pdf": "실험3 퀴즈 예상문제_v4.pdf",

    # 실험4
    "실험4/4.jpg": "실험4/실험4 퀴즈 기출_채점본.jpg",
    "실험4/퀴즈4.pdf": "실험4 퀴즈 기출 2016-1.pdf",
    "실험4/실험4+-+정답.pdf": "실험4 퀴즈 기출_정답.pdf",
    "실험4/실험 4_퀴즈.pdf": "실험4 퀴즈 해설.pdf",
    "실험4/실험 4.pdf": "실험4 퀴즈 예상문제_v1.pdf",
    "실험4/실험 4 (2).pdf": "실험4 퀴즈 예상문제_v2.pdf",
    "실험4/실험4_예상.pdf": "실험4 퀴즈 예상문제_v3.pdf",
    "실험4/실험4_예상 (2).pdf": "실험4 퀴즈 예상문제_v4.pdf",

    # 실험5
    "실험5/5.jpg": "실험5/실험5 퀴즈 기출_채점본.jpg",
    "실험5/퀴즈5.pdf": "실험5 퀴즈 기출 2016-2.pdf",
    "실험5/quiz_05.pdf": "실험5 퀴즈 기출_단답형.pdf",
    "실험5/실험5+-+정답.pdf": "실험5 퀴즈 기출_정답.pdf",
    "실험5/실험5퀴즈_문제.pdf": "실험5 퀴즈 기출_문제.pdf",
    "실험5/실험5퀴즈_답.pdf": "실험5 퀴즈 기출_풀이.pdf",
    "실험5/실험 5_퀴즈.pdf": "실험5 퀴즈 해설.pdf",
    "실험5/실험 5.pdf": "실험5 퀴즈 예상문제_v1.pdf",
    "실험5/실험 5 (2).pdf": "실험5 퀴즈 예상문제_v2.pdf",
    "실험5/실험5_예상.pdf": "실험5 퀴즈 예상문제_v3.pdf",
    "실험5/실험5_예상 (2).pdf": "실험5 퀴즈 예상문제_v4.pdf",

    # 실험6
    "실험6/퀴즈6.pdf": "실험6 퀴즈 기출 2017-1.pdf",
    "실험6/quiz_06.pdf": "실험6 퀴즈 기출_단답형.pdf",
    "실험6/실험 6_퀴즈.pdf": "실험6 퀴즈 해설.pdf",
    "실험6/실험 6.pdf": "실험6 퀴즈 예상문제_v1.pdf",
    "실험6/실험6.pdf": "실험6 퀴즈 예상문제_v2.pdf",
    "실험6/실험6_예상.pdf": "실험6 퀴즈 예상문제_v3.pdf",
    "실험6/실험6_예상 (2).pdf": "실험6 퀴즈 예상문제_v4.pdf",

    # 실험7
    "실험7/7.jpg": "실험7/실험7 퀴즈 기출_채점본.jpg",
    "실험7/퀴즈7.pdf": "실험7 퀴즈 기출 2016-1.pdf",
    "실험7/실험7_수정.pdf": "실험7 퀴즈 강의자료 2016-2 (20p).pdf",
    "실험7/quiz_07(1).pdf": "실험7 퀴즈 기출_단답형.pdf",
    "실험7/실험7+-+정답.pdf": "실험7 퀴즈 기출_정답.pdf",
    "실험7/실험7_문제.pdf": "실험7 퀴즈 기출_월요반_문제.pdf",
    "실험7/실험7_답.pdf": "실험7 퀴즈 기출_금요반_정답.pdf",
    "실험7/실험 7_퀴즈.pdf": "실험7 퀴즈 해설.pdf",
    "실험7/실험 7.pdf": "실험7 퀴즈 예상문제_v1.pdf",
    "실험7/실험7_예상.pdf": "실험7 퀴즈 예상문제_v2.pdf",
    "실험7/실험7_예상 (2).pdf": "실험7 퀴즈 예상문제_v3.pdf",
    "실험7/실험7_예상 !!!.pdf": "실험7 퀴즈 예상문제_v4.pdf",
    "실험7/실험7_예상 !!! (2).pdf": "실험7 퀴즈 예상문제_v5.pdf",

    # 실험8
    "실험8/8.jpg": "실험8/실험8 퀴즈 기출_채점본.jpg",
    "실험8/퀴즈8.pdf": "실험8 퀴즈 기출 2017-1.pdf",
    "실험8/퀴즈8-eng.pdf": "실험8 퀴즈 기출 2015-2_영문.pdf",
    "실험8/실험8++-+정답.pdf": "실험8 퀴즈 기출_정답.pdf",
    "실험8/실험8_Counter.pdf": "실험8 퀴즈 예상문제_카운터심화.pdf",
    "실험8/실험8 최종 - 답안 단순화.pdf": "실험8 퀴즈 예상문제_답안단순화_v1.pdf",
    "실험8/실험8 최종 - 답안 단순화!.pdf": "실험8 퀴즈 예상문제_답안단순화_v2.pdf",
    "실험8/실험8 정리중!!!!!!.pdf": "실험8 퀴즈 예상문제_정리본_v1.pdf",
    "실험8/실험8 정리중-수정.pdf": "실험8 퀴즈 예상문제_정리본_v2.pdf",
    "실험8/실험 8.pdf": "실험8 퀴즈 예상문제_v1.pdf",
    "실험8/실험8.pdf": "실험8 퀴즈 예상문제_v2.pdf",
    "실험8/실험8 (2).pdf": "실험8 퀴즈 예상문제_v3.pdf",
    "실험8/실험8 (3).pdf": "실험8 퀴즈 예상문제_v4.pdf",

    # 실험9
    "실험9/9.jpg": "실험9/실험9 퀴즈 기출_채점본_1.jpg",
    "실험9/실험9.jpg": "실험9 퀴즈 기출_채점본_2.jpg",
    "실험9/실험9 (2).jpg": "실험9 퀴즈 기출_채점본_3.jpg",
    "실험9/실험91.jpg": "실험9 퀴즈 예상문제_수기메모.jpg",
    "실험9/퀴즈9.pdf": "실험9 퀴즈 기출 2016-2.pdf",
    "실험9/quiz_09(1).pdf": "실험9 퀴즈 기출_단답형.pdf",
    "실험9/실험 9.pdf": "실험9 퀴즈 예상문제_v1.pdf",
    "실험9/실험9_예상.pdf": "실험9 퀴즈 예상문제_v2.pdf",
    "실험9/실험9_예상 (2).pdf": "실험9 퀴즈 예상문제_v3.pdf",
    "실험9/실험9_예상 (3).pdf": "실험9 퀴즈 예상문제_v4.pdf",

    # 실험10
    "실험10/퀴즈10.pdf": "실험10 퀴즈 기출 2016-2.pdf",
    "실험10/실험 10.pdf": "실험10 퀴즈 예상문제_v1.pdf",
    "실험10/실험10.pdf": "실험10 퀴즈 예상문제_v2.pdf",
    "실험10/실험10_예상.pdf": "실험10 퀴즈 예상문제_v3.pdf",
    "실험10/실험10_예상 (2).pdf": "실험10 퀴즈 예상문제_v4.pdf",
    "실험10/실험10_예상 (3).pdf": "실험10 퀴즈 예상문제_v5.pdf",

    # 기타
    "기타/논회실 퀴즈 소스.pdf": "기타/논회실 퀴즈 종합 족보 (40p).pdf",
    "기타/이외 실험.pdf": "기타/논회실 퀴즈 종합 기출단답 1 (8p).pdf",
    "기타/이외 실험2.pdf": "기타/논회실 퀴즈 종합 기출단답 2 (7p).pdf",
    "기타/6,10은 미안해~.txt": "기타/기출채점본 실험6,10 누락 안내.txt",
    "기타/KakaoTalk_20151001_155445279.png": "기타/디코더 vs 디멀티플렉서 개념비교.png",
    "기타/KakaoTalk_20151001_160027915.jpg": "기타/디코더 vs 멀티플렉서 vs 디멀티플렉서 동작비교.jpg",
}


def rename_quiz_files(
    base_dir: str | Path,
    dry_run: bool = False,
    backup_file: Optional[Path] = None,
) -> Dict[str, str]:
    base_path = Path(base_dir).resolve()
    performed_renames: Dict[str, str] = {}

    for old_rel, new_rel in QUIZ_RENAME_MAP.items():
        src = base_path / old_rel
        dst = base_path / new_rel
        if src.exists() and src != dst:
            performed_renames[str(src)] = str(dst)
            if not dry_run:
                dst.parent.mkdir(parents=True, exist_ok=True)
                os.rename(src, dst)

    if not dry_run and backup_file and performed_renames:
        backup_file.parent.mkdir(parents=True, exist_ok=True)
        with open(backup_file, "w", encoding="utf-8") as f:
            json.dump(performed_renames, f, ensure_ascii=False, indent=2)

    return performed_renames


def rollback_quiz_files(backup_file: str | Path) -> int:
    backup_path = Path(backup_file).resolve()
    if not backup_path.exists():
        raise FileNotFoundError(f"Backup file not found: {backup_path}")

    with open(backup_path, "r", encoding="utf-8") as f:
        renames: Dict[str, str] = json.load(f)

    restored = 0
    for old_path_str, new_path_str in renames.items():
        src = Path(new_path_str)
        dst = Path(old_path_str)
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            os.rename(src, dst)
            restored += 1

    return restored


def generate_rename_markdown_table(base_dir: str | Path, output_file: str | Path):
    base_path = Path(base_dir).resolve()
    out_path = Path(output_file).resolve()

    folders = [f"실험{i}" for i in range(1, 11)] + ["기타"]
    lines = ["# 퀴즈 파일명 변경 대조표 (RENAME MAP)\n"]
    lines.append("| 번호 | 기존 파일명 | 변경된 표준 파일명 |")
    lines.append("| :--- | :--- | :--- |")

    idx = 1
    for folder in folders:
        folder_items = [
            (k, v) for k, v in QUIZ_RENAME_MAP.items() if k.startswith(folder + "/")
        ]
        if folder_items:
            lines.append(f"\n### {folder}")
            lines.append("| 번호 | 기존 파일명 | 변경된 표준 파일명 |")
            lines.append("| :--- | :--- | :--- |")
            for old_k, new_v in sorted(folder_items):
                old_name = Path(old_k).name
                new_name = Path(new_v).name
                lines.append(f"| {idx} | `{old_name}` | **`{new_name}`** |")
                idx += 1

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Standardize Quiz Filenames")
    parser.add_argument(
        "--target-dir",
        default="from_the_past/정리/퀴즈",
        help="Target quiz directory",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply renames (default is dry-run)",
    )
    parser.add_argument(
        "--rollback",
        action="store_true",
        help="Rollback renames using backup JSON",
    )
    parser.add_argument(
        "--backup-file",
        default="from_the_past/정리/퀴즈/.system_generated/quiz_rename_backup.json",
        help="Path to backup JSON file",
    )
    parser.add_argument(
        "--generate-index",
        action="store_true",
        help="Generate RENAME_MAP.md index file",
    )
    args = parser.parse_args()

    target_path = Path(args.target_dir)
    backup_path = Path(args.backup_file)

    if args.rollback:
        restored = rollback_quiz_files(backup_path)
        print(f"[+] Successfully rolled back {restored} files.")
        return

    dry_run = not args.apply
    if dry_run:
        print("[*] Running in DRY-RUN mode. Use --apply to execute changes.\n")

    renames = rename_quiz_files(
        target_path, dry_run=dry_run, backup_file=backup_path
    )
    print(f"[*] Found {len(renames)} files to rename.")
    for src, dst in renames.items():
        print(f"  {Path(src).name} -> {Path(dst).name}")

    if args.apply:
        print(f"\n[+] Successfully renamed {len(renames)} files!")
        md_file = target_path / "RENAME_MAP.md"
        generate_rename_markdown_table(target_path, md_file)
        print(f"[+] Generated markdown map: {md_file}")


if __name__ == "__main__":
    main()
```

- [x] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests/test_quiz_renamer.py`
Expected: PASS (all tests pass)

---

### Task 2: Dry Run 검증, 실제 파일명 변경 실행 및 `RENAME_MAP.md` 생성

**Files:**
- Execute: `scripts/rename_quiz_files.py`
- Modify: `from_the_past/정리/퀴즈/` (97 files renamed)
- Create: `from_the_past/정리/퀴즈/RENAME_MAP.md`
- Create: `from_the_past/정리/퀴즈/.system_generated/quiz_rename_backup.json`

**Interfaces:**
- Consumes: `from_the_past/정리/퀴즈/` (97 old names)
- Produces: `from_the_past/정리/퀴즈/` (97 standardized names) + `RENAME_MAP.md`

- [x] **Step 1: Run Dry-run on `from_the_past/정리/퀴즈`**

Run: `python3 scripts/rename_quiz_files.py`
Expected: Lists all 97 planned renames without modifying files.

- [x] **Step 2: Execute actual renaming with `--apply`**

Run: `python3 scripts/rename_quiz_files.py --apply`
Expected: Successfully renames all 97 files and generates `RENAME_MAP.md` and backup JSON.

- [x] **Step 3: Validate file counts and structure**

Run: `python3 -c "import os; from pathlib import Path; p=Path('from_the_past/정리/퀴즈'); files=[f for f in p.rglob('*') if f.is_file() and not any(part.startswith('.') for part in f.parts) and f.name != 'RENAME_MAP.md']; print(f'Total files in 퀴즈: {len(files)}'); assert len(files) == 97, f'Expected 97, got {len(files)}'; print('Verification PASSED!')"`
Expected: Total files in 퀴즈: 97, Verification PASSED!

- [x] **Step 4: Run full test suite**

Run: `python3 -m unittest discover -s tests`
Expected: All tests pass.

- [x] **Step 5: Commit changes**

```bash
git add scripts/rename_quiz_files.py tests/test_quiz_renamer.py docs/plans/2026-08-27-quiz-files-rename-standardization.md
git commit -m "feat: standardize quiz filenames across all experiments with rollback and markdown map"
```

---

## Verification Plan

### Automated Tests
- Renamer unit tests:
  ```bash
  python3 -m unittest tests/test_quiz_renamer.py
  ```
- Full test suite:
  ```bash
  python3 -m unittest discover -s tests
  ```

### Manual & File Integrity Verification
- Verify 97 standardized files exist:
  ```bash
  python3 -c "import os; from pathlib import Path; p=Path('from_the_past/정리/퀴즈'); files=[f for f in p.rglob('*') if f.is_file() and not f.name.startswith('.') and f.name != 'RENAME_MAP.md']; print(len(files))"
  ```
- Verify `RENAME_MAP.md` content:
  ```bash
  head -n 30 from_the_past/정리/퀴즈/RENAME_MAP.md
  ```
