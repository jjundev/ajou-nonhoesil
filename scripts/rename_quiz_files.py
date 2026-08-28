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
    "실험3/퀴즈3-1.pdf": "실험3/실험3 퀴즈 기출 2016-1.pdf",
    "실험3/실험3+-+정답.pdf": "실험3/실험3 퀴즈 기출_정답.pdf",
    "실험3/실험3퀴즈_문제.pdf": "실험3/실험3 퀴즈 기출_문제.pdf",
    "실험3/실험 3.pdf": "실험3/실험3 퀴즈 예상문제_v1.pdf",
    "실험3/실험 3 (2).pdf": "실험3/실험3 퀴즈 예상문제_v2.pdf",
    "실험3/실험 3 (3).pdf": "실험3/실험3 퀴즈 예상문제_v3.pdf",
    "실험3/실험3.pdf": "실험3/실험3 퀴즈 예상문제_v4.pdf",

    # 실험4
    "실험4/4.jpg": "실험4/실험4 퀴즈 기출_채점본.jpg",
    "실험4/퀴즈4.pdf": "실험4/실험4 퀴즈 기출 2016-1.pdf",
    "실험4/실험4+-+정답.pdf": "실험4/실험4 퀴즈 기출_정답.pdf",
    "실험4/실험 4_퀴즈.pdf": "실험4/실험4 퀴즈 해설.pdf",
    "실험4/실험 4.pdf": "실험4/실험4 퀴즈 예상문제_v1.pdf",
    "실험4/실험 4 (2).pdf": "실험4/실험4 퀴즈 예상문제_v2.pdf",
    "실험4/실험4_예상.pdf": "실험4/실험4 퀴즈 예상문제_v3.pdf",
    "실험4/실험4_예상 (2).pdf": "실험4/실험4 퀴즈 예상문제_v4.pdf",

    # 실험5
    "실험5/5.jpg": "실험5/실험5 퀴즈 기출_채점본.jpg",
    "실험5/퀴즈5.pdf": "실험5/실험5 퀴즈 기출 2016-2.pdf",
    "실험5/quiz_05.pdf": "실험5/실험5 퀴즈 기출_단답형.pdf",
    "실험5/실험5+-+정답.pdf": "실험5/실험5 퀴즈 기출_정답.pdf",
    "실험5/실험5퀴즈_문제.pdf": "실험5/실험5 퀴즈 기출_문제.pdf",
    "실험5/실험5퀴즈_답.pdf": "실험5/실험5 퀴즈 기출_풀이.pdf",
    "실험5/실험 5_퀴즈.pdf": "실험5/실험5 퀴즈 해설.pdf",
    "실험5/실험 5.pdf": "실험5/실험5 퀴즈 예상문제_v1.pdf",
    "실험5/실험 5 (2).pdf": "실험5/실험5 퀴즈 예상문제_v2.pdf",
    "실험5/실험5_예상.pdf": "실험5/실험5 퀴즈 예상문제_v3.pdf",
    "실험5/실험5_예상 (2).pdf": "실험5/실험5 퀴즈 예상문제_v4.pdf",

    # 실험6
    "실험6/퀴즈6.pdf": "실험6/실험6 퀴즈 기출 2017-1.pdf",
    "실험6/quiz_06.pdf": "실험6/실험6 퀴즈 기출_단답형.pdf",
    "실험6/실험 6_퀴즈.pdf": "실험6/실험6 퀴즈 해설.pdf",
    "실험6/실험 6.pdf": "실험6/실험6 퀴즈 예상문제_v1.pdf",
    "실험6/실험6.pdf": "실험6/실험6 퀴즈 예상문제_v2.pdf",
    "실험6/실험6_예상.pdf": "실험6/실험6 퀴즈 예상문제_v3.pdf",
    "실험6/실험6_예상 (2).pdf": "실험6/실험6 퀴즈 예상문제_v4.pdf",

    # 실험7
    "실험7/7.jpg": "실험7/실험7 퀴즈 기출_채점본.jpg",
    "실험7/퀴즈7.pdf": "실험7/실험7 퀴즈 기출 2016-1.pdf",
    "실험7/실험7_수정.pdf": "실험7/실험7 퀴즈 강의자료 2016-2 (20p).pdf",
    "실험7/quiz_07(1).pdf": "실험7/실험7 퀴즈 기출_단답형.pdf",
    "실험7/실험7+-+정답.pdf": "실험7/실험7 퀴즈 기출_정답.pdf",
    "실험7/실험7_문제.pdf": "실험7/실험7 퀴즈 기출_월요반_문제.pdf",
    "실험7/실험7_답.pdf": "실험7/실험7 퀴즈 기출_금요반_정답.pdf",
    "실험7/실험 7_퀴즈.pdf": "실험7/실험7 퀴즈 해설.pdf",
    "실험7/실험 7.pdf": "실험7/실험7 퀴즈 예상문제_v1.pdf",
    "실험7/실험7_예상.pdf": "실험7/실험7 퀴즈 예상문제_v2.pdf",
    "실험7/실험7_예상 (2).pdf": "실험7/실험7 퀴즈 예상문제_v3.pdf",
    "실험7/실험7_예상 !!!.pdf": "실험7/실험7 퀴즈 예상문제_v4.pdf",
    "실험7/실험7_예상 !!! (2).pdf": "실험7/실험7 퀴즈 예상문제_v5.pdf",

    # 실험8
    "실험8/8.jpg": "실험8/실험8 퀴즈 기출_채점본.jpg",
    "실험8/퀴즈8.pdf": "실험8/실험8 퀴즈 기출 2017-1.pdf",
    "실험8/퀴즈8-eng.pdf": "실험8/실험8 퀴즈 기출 2015-2_영문.pdf",
    "실험8/실험8++-+정답.pdf": "실험8/실험8 퀴즈 기출_정답.pdf",
    "실험8/실험8_Counter.pdf": "실험8/실험8 퀴즈 예상문제_카운터심화.pdf",
    "실험8/실험8 최종 - 답안 단순화.pdf": "실험8/실험8 퀴즈 예상문제_답안단순화_v1.pdf",
    "실험8/실험8 최종 - 답안 단순화!.pdf": "실험8/실험8 퀴즈 예상문제_답안단순화_v2.pdf",
    "실험8/실험8 정리중!!!!!!.pdf": "실험8/실험8 퀴즈 예상문제_정리본_v1.pdf",
    "실험8/실험8 정리중-수정.pdf": "실험8/실험8 퀴즈 예상문제_정리본_v2.pdf",
    "실험8/실험 8.pdf": "실험8/실험8 퀴즈 예상문제_v1.pdf",
    "실험8/실험8.pdf": "실험8/실험8 퀴즈 예상문제_v2.pdf",
    "실험8/실험8 (2).pdf": "실험8/실험8 퀴즈 예상문제_v3.pdf",
    "실험8/실험8 (3).pdf": "실험8/실험8 퀴즈 예상문제_v4.pdf",

    # 실험9
    "실험9/9.jpg": "실험9/실험9 퀴즈 기출_채점본_1.jpg",
    "실험9/실험9.jpg": "실험9/실험9 퀴즈 기출_채점본_2.jpg",
    "실험9/실험9 (2).jpg": "실험9/실험9 퀴즈 기출_채점본_3.jpg",
    "실험9/실험91.jpg": "실험9/실험9 퀴즈 예상문제_수기메모.jpg",
    "실험9/퀴즈9.pdf": "실험9/실험9 퀴즈 기출 2016-2.pdf",
    "실험9/quiz_09(1).pdf": "실험9/실험9 퀴즈 기출_단답형.pdf",
    "실험9/실험 9.pdf": "실험9/실험9 퀴즈 예상문제_v1.pdf",
    "실험9/실험9_예상.pdf": "실험9/실험9 퀴즈 예상문제_v2.pdf",
    "실험9/실험9_예상 (2).pdf": "실험9/실험9 퀴즈 예상문제_v3.pdf",
    "실험9/실험9_예상 (3).pdf": "실험9/실험9 퀴즈 예상문제_v4.pdf",

    # 실험10
    "실험10/퀴즈10.pdf": "실험10/실험10 퀴즈 기출 2016-2.pdf",
    "실험10/실험 10.pdf": "실험10/실험10 퀴즈 예상문제_v1.pdf",
    "실험10/실험10.pdf": "실험10/실험10 퀴즈 예상문제_v2.pdf",
    "실험10/실험10_예상.pdf": "실험10/실험10 퀴즈 예상문제_v3.pdf",
    "실험10/실험10_예상 (2).pdf": "실험10/실험10 퀴즈 예상문제_v4.pdf",
    "실험10/실험10_예상 (3).pdf": "실험10/실험10 퀴즈 예상문제_v5.pdf",

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
        backup_file = Path(backup_file).resolve()
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

    out_path.parent.mkdir(parents=True, exist_ok=True)
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

    if args.apply or args.generate_index:
        md_file = target_path / "RENAME_MAP.md"
        generate_rename_markdown_table(target_path, md_file)
        print(f"[+] Generated markdown map: {md_file}")

    if args.apply:
        print(f"\n[+] Successfully renamed {len(renames)} files!")


if __name__ == "__main__":
    main()
