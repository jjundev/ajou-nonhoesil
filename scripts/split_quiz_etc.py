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
