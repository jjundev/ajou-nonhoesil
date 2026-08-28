import argparse
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Union


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
    source_dir: Union[str, Path], dry_run: bool = False
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
