#!/usr/bin/env python3
"""
DOC/DOCX/PPTX to PDF batch converter using Headless LibreOffice.
Inherits the robust architecture, discovery, validation, and batch processing
patterns from convert_hwp_to_pdf.py with fast offline local conversion.
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import List, Optional, Tuple

SOFFICE_CANDIDATES = [
    "/Applications/LibreOffice.app/Contents/MacOS/soffice",
    shutil.which("soffice"),
    shutil.which("libreoffice"),
]


def get_soffice_binary() -> str:
    for cand in SOFFICE_CANDIDATES:
        if cand and os.path.exists(cand) and os.access(cand, os.X_OK):
            return cand
    raise FileNotFoundError(
        "LibreOffice binary (soffice) not found. Please ensure LibreOffice is installed."
    )


def discover_doc_files(
    target: str | Path,
    extensions: Tuple[str, ...] = (".docx", ".doc", ".pptx"),
) -> List[str]:
    """
    Recursively finds all supported document files, ignoring temporary/lock files (~$*) and hidden files.
    """
    target_path = Path(target).resolve()
    if target_path.is_file():
        if target_path.suffix.lower() in extensions and not target_path.name.startswith("~$") and not target_path.name.startswith("."):
            return [str(target_path)]
        return []

    doc_files = []
    for root, _, files in os.walk(target_path):
        for f in files:
            if not f.startswith("~$") and not f.startswith("."):
                ext = Path(f).suffix.lower()
                if ext in extensions:
                    doc_files.append(os.path.join(root, f))
    return sorted(doc_files)


def resolve_output_pdf_path(
    doc_path: str | Path,
    base_target: str | Path,
    output_dir: Optional[str | Path] = None,
) -> str:
    """
    Resolves target PDF path in-place alongside doc or mirrored into output_dir.
    """
    doc_p = Path(doc_path).resolve()
    pdf_filename = doc_p.stem + ".pdf"

    if output_dir is None:
        return str(doc_p.parent / pdf_filename)

    base_p = Path(base_target).resolve()
    if base_p.is_file():
        return str(Path(output_dir).resolve() / pdf_filename)

    rel_parent = doc_p.parent.relative_to(base_p)
    return str(Path(output_dir).resolve() / rel_parent / pdf_filename)


def validate_pdf(pdf_path: str | Path) -> bool:
    """
    Validates PDF existence, size (> 100 bytes), and %PDF- magic header.
    """
    p = Path(pdf_path)
    if not p.exists() or p.stat().st_size < 100:
        return False
    try:
        with open(p, "rb") as f:
            header = f.read(1024)
            return b"%PDF-" in header
    except Exception:
        return False


def convert_doc_to_pdf(
    doc_path: str | Path,
    output_pdf_path: str | Path,
    timeout_sec: int = 60,
) -> bool:
    """
    Converts a single document file to PDF using isolated LibreOffice headless process.
    """
    abs_doc = os.path.abspath(doc_path)
    abs_out = os.path.abspath(output_pdf_path)
    out_dir = os.path.dirname(abs_out)
    os.makedirs(out_dir, exist_ok=True)

    try:
        soffice_bin = get_soffice_binary()
    except FileNotFoundError as e:
        print(f"  [-] Error: {e}", flush=True)
        return False

    with tempfile.TemporaryDirectory(prefix="libreoffice_conv_") as tmpdir:
        user_profile = f"file://{tmpdir}/profile"
        cmd = [
            soffice_bin,
            f"-env:UserInstallation={user_profile}",
            "--headless",
            "--convert-to",
            "pdf",
            abs_doc,
            "--outdir",
            tmpdir,
        ]

        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
            )
            # Find generated PDF in tmpdir
            generated_pdfs = list(Path(tmpdir).glob("*.pdf"))
            if not generated_pdfs:
                return False

            gen_pdf = generated_pdfs[0]
            shutil.move(str(gen_pdf), abs_out)
            return validate_pdf(abs_out)
        except Exception as e:
            print(f"  [-] Exception during conversion: {e}", flush=True)
            return False


def batch_convert_docs(
    target: str,
    output_dir: Optional[str] = None,
    force: bool = False,
    timeout_sec: int = 60,
) -> Tuple[int, int, List[Tuple[str, str]]]:
    """
    Performs batch conversion with skip detection, reporting, and error tracking.
    """
    target_path = os.path.abspath(target)
    if not os.path.exists(target_path):
        raise FileNotFoundError(f"Target path does not exist: {target_path}")

    doc_files = discover_doc_files(target_path)
    if not doc_files:
        print(f"No document files found in {target_path}", flush=True)
        return 0, 0, []

    print(f"Found {len(doc_files)} document files in {target_path}", flush=True)
    print(
        f"Output mode: {'Mirrored to ' + str(output_dir) if output_dir else 'In-place (alongside original document)'}",
        flush=True,
    )

    success_cnt = 0
    skipped_cnt = 0
    failed_files = []

    for idx, doc_file in enumerate(doc_files, 1):
        out_pdf = resolve_output_pdf_path(doc_file, target_path, output_dir)
        rel_doc = (
            os.path.relpath(doc_file, target_path)
            if os.path.isdir(target_path)
            else os.path.basename(doc_file)
        )
        file_sz_kb = os.path.getsize(doc_file) / 1024

        if not force and validate_pdf(out_pdf):
            print(f"[{idx}/{len(doc_files)}] [SKIPPED - Already converted] {rel_doc}")
            skipped_cnt += 1
            success_cnt += 1
            continue

        print(f"[{idx}/{len(doc_files)}] Converting: {rel_doc} ({file_sz_kb:.1f} KB)...", flush=True)
        success = convert_doc_to_pdf(doc_file, out_pdf, timeout_sec=timeout_sec)

        if success:
            file_sz_pdf = os.path.getsize(out_pdf) / 1024
            print(f"  [+] Saved & Validated: {os.path.basename(out_pdf)} ({file_sz_pdf:.1f} KB)", flush=True)
            success_cnt += 1
        else:
            failed_files.append((doc_file, out_pdf))
            print(f"  [!] Failed to convert {rel_doc}", flush=True)

    print("\n" + "=" * 50)
    print("Batch Conversion Finished!")
    print(
        f"Total: {len(doc_files)} | Converted: {success_cnt - skipped_cnt} | Skipped: {skipped_cnt} | Failed: {len(failed_files)}"
    )
    if failed_files:
        print(f"\nFailed files ({len(failed_files)}):")
        for src, dst in failed_files:
            print(f" - {src}")

    return success_cnt, skipped_cnt, failed_files


def main():
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except Exception:
        pass

    parser = argparse.ArgumentParser(
        description="Batch convert DOC/DOCX/PPTX files to PDF via Headless LibreOffice"
    )
    parser.add_argument(
        "target",
        nargs="?",
        default="from_the_past/정리/퀴즈",
        help="Target document file or directory (default: from_the_past/정리/퀴즈)",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        default=None,
        help="Optional output directory (default: in-place next to original files)",
    )
    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Force overwrite existing PDF files",
    )
    parser.add_argument(
        "--timeout",
        "-t",
        type=int,
        default=60,
        help="Conversion timeout per file in seconds (default: 60)",
    )
    args = parser.parse_args()

    batch_convert_docs(
        target=args.target,
        output_dir=args.output_dir,
        force=args.force,
        timeout_sec=args.timeout,
    )


if __name__ == "__main__":
    main()
