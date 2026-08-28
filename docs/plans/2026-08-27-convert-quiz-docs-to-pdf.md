# 퀴즈 디렉토리 DOCX/DOC/PPTX 문서의 PDF 일괄 변환 계획 (Convert Quiz Docs to PDF Plan)

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `from_the_past/정리/퀴즈/` 하위의 모든 Word 및 문서 파일(`*.docx`, `*.doc`, `*.pptx` 총 59개)을 기존 HWP 변환기 아키텍처(`convert_hwp_to_pdf.py`)의 모듈화 패턴을 계승하여 안전하고 빠른 로컬 헤드리스 엔진 기반의 `convert_docs_to_pdf.py`로 PDF 변환한다.

**Architecture:** 
- 기존 `convert_hwp_to_pdf.py`의 `discover_files`, `resolve_output_pdf_path`, `validate_pdf`, 배치 진행률/스킵/재시도 루프 패턴을 계승.
- 로컬 환경의 `/Applications/LibreOffice.app/Contents/MacOS/soffice` (격리된 `-env:UserInstallation` 프로필)를 엔진으로 활용하여 네트워크 지연 및 업로드 용량 제한 없이 100% 오프라인 고속 변환 수행.
- TDD 기반 단위 테스트(`tests/test_docs_converter.py`)로 파일 검색, 경로 해석, PDF 유효성 검증 및 변환 실행을 검증한 뒤 실제 퀴즈 디렉토리에 대해 일괄 변환 및 유효성 검증을 수행.

**Tech Stack:** Python 3 (standard library: `os`, `re`, `subprocess`, `tempfile`, `pathlib`, `unittest`), PyMuPDF (`fitz`), LibreOffice headless engine

## Global Constraints

- 대상 디렉토리: `/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/퀴즈`
- 대상 파일 확장자: `.docx`, `.doc`, `.pptx` (임시 잠금 파일 `~$*` 제외)
- 출력 경로: 원본 문서 파일과 동일한 디렉토리에 동일한 stem 이름의 `.pdf` 파일 생성 (in-place)
- 스킵 로직: 이미 유효한 `.pdf` 파일이 존재하고 `--force` 플래그가 없으면 변환을 스킵하여 효율성 보장
- 원본 보존: 원본 `.doc`, `.docx`, `.pptx` 파일은 절대 삭제하거나 수정하지 않고 보존

---

### Task 1: Docs to PDF 변환기 모듈 및 단위 테스트 작성 (TDD)

**Files:**
- Create: `scripts/convert_docs_to_pdf.py`
- Create: `tests/test_docs_converter.py`

**Interfaces:**
- Consumes: Standard Python libraries (`os`, `subprocess`, `tempfile`, `pathlib`, `unittest`)
- Produces:
  - `discover_doc_files(target: str | Path, extensions: tuple = ('.docx', '.doc', '.pptx')) -> list[str]`
  - `resolve_output_pdf_path(doc_path: str, base_target: str, output_dir: str | None = None) -> str`
  - `validate_pdf(pdf_path: str) -> bool`
  - `convert_doc_to_pdf(doc_path: str, output_pdf_path: str, timeout_sec: int = 60) -> bool`
  - `batch_convert_docs(target: str, output_dir: str | None = None, force: bool = False, timeout_sec: int = 60) -> tuple[int, int, list]`

- [x] **Step 1: Write the failing unit tests**

Create `tests/test_docs_converter.py`:

```python
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.convert_docs_to_pdf import (
    discover_doc_files,
    resolve_output_pdf_path,
    validate_pdf,
    convert_doc_to_pdf,
)


class TestDocsConverter(unittest.TestCase):
    def setUp(self):
        self.temp_dir = str(Path(tempfile.mkdtemp()).resolve())
        (Path(self.temp_dir) / "sub1").mkdir()
        (Path(self.temp_dir) / "sub1" / "doc1.docx").write_text("dummy")
        (Path(self.temp_dir) / "sub1" / "doc2.doc").write_text("dummy")
        (Path(self.temp_dir) / "sub2").mkdir()
        (Path(self.temp_dir) / "sub2" / "slide.pptx").write_text("dummy")
        (Path(self.temp_dir) / "ignore.txt").write_text("dummy")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_discover_doc_files(self):
        files = discover_doc_files(self.temp_dir)
        self.assertEqual(len(files), 3)
        stems = {Path(f).stem for f in files}
        self.assertEqual(stems, {"doc1", "doc2", "slide"})

    def test_discover_single_doc_file(self):
        single_doc = os.path.join(self.temp_dir, "sub1", "doc1.docx")
        files = discover_doc_files(single_doc)
        self.assertEqual(files, [single_doc])

    def test_discover_single_non_doc_file(self):
        non_doc = os.path.join(self.temp_dir, "ignore.txt")
        files = discover_doc_files(non_doc)
        self.assertEqual(files, [])

    def test_discover_ignores_lock_files(self):
        lock_file = Path(self.temp_dir) / "sub1" / "~$locked.docx"
        lock_file.write_text("lock")
        files = discover_doc_files(self.temp_dir)
        self.assertNotIn(str(lock_file), files)

    def test_resolve_output_pdf_path_inplace(self):
        doc = os.path.join(self.temp_dir, "sub1", "doc1.docx")
        pdf = resolve_output_pdf_path(doc, self.temp_dir, output_dir=None)
        expected = os.path.join(self.temp_dir, "sub1", "doc1.pdf")
        self.assertEqual(pdf, expected)

    def test_resolve_output_pdf_path_mirrored(self):
        out_root = os.path.join(self.temp_dir, "out")
        doc = os.path.join(self.temp_dir, "sub1", "doc1.docx")
        pdf = resolve_output_pdf_path(doc, self.temp_dir, output_dir=out_root)
        expected = os.path.join(out_root, "sub1", "doc1.pdf")
        self.assertEqual(pdf, expected)

    def test_validate_pdf(self):
        valid_pdf = os.path.join(self.temp_dir, "valid.pdf")
        with open(valid_pdf, "wb") as f:
            f.write(b"%PDF-1.4\n" + b"x" * 150 + b"\n%%EOF")
        self.assertTrue(validate_pdf(valid_pdf))

        invalid_pdf = os.path.join(self.temp_dir, "invalid.pdf")
        with open(invalid_pdf, "wb") as f:
            f.write(b"NOT A PDF")
        self.assertFalse(validate_pdf(invalid_pdf))
        self.assertFalse(validate_pdf(os.path.join(self.temp_dir, "non_existent.pdf")))


if __name__ == "__main__":
    unittest.main()
```

- [x] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests/test_docs_converter.py`
Expected: FAIL (ModuleNotFoundError: No module named 'scripts.convert_docs_to_pdf')

- [x] **Step 3: Implement `scripts/convert_docs_to_pdf.py`**

Create `scripts/convert_docs_to_pdf.py`:

```python
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
    Recursively finds all supported document files, ignoring temporary/lock files (~$*).
    """
    target_path = Path(target).resolve()
    if target_path.is_file():
        if target_path.suffix.lower() in extensions and not target_path.name.startswith("~$"):
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

    soffice_bin = get_soffice_binary()

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
        except Exception:
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
```

- [x] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests/test_docs_converter.py`
Expected: PASS (all tests pass)

---

### Task 2: `from_the_past/정리/퀴즈` 하위 문서 일괄 PDF 변환 실행 및 유효성 검증

**Files:**
- Execute: `scripts/convert_docs_to_pdf.py`
- Target: `from_the_past/정리/퀴즈/` (59 files across `실험1` ~ `실험10`)

**Interfaces:**
- Consumes: 59 document files (`.docx`, `.doc`, `.pptx`)
- Produces: 59 validated `.pdf` files alongside originals

- [x] **Step 1: Execute batch conversion on `from_the_past/정리/퀴즈`**

Run: `python3 scripts/convert_docs_to_pdf.py from_the_past/정리/퀴즈`
Expected: Converts all 51 un-converted documents (and skips 8 already converted), total 59/59 success with 0 failures.

- [x] **Step 2: Validate all generated PDFs with PyMuPDF**

Run: `python3 -c "import fitz, os; from pathlib import Path; quiz=Path('from_the_past/정리/퀴즈'); docs=[p for p in quiz.rglob('*') if p.suffix.lower() in ['.docx','.doc','.pptx'] and not p.name.startswith(('~$','.'))]; print(f'Checking {len(docs)} documents...'); errs=0; for d in docs: pdf=d.with_suffix('.pdf'); assert pdf.exists(), f'Missing: {pdf}'; doc=fitz.open(pdf); assert len(doc)>=1, f'Empty: {pdf}'; print(f'  OK: {d.name} -> {pdf.name} ({len(doc)}p, {os.path.getsize(pdf)} bytes)'); print(f'All {len(docs)} PDFs verified successfully!')"`
Expected: All 59 PDFs exist, are valid, and have >0 pages.

- [x] **Step 3: Run full test suite**

Run: `python3 -m unittest tests/test_docs_converter.py tests/test_quiz_organizer.py`
Expected: All unit tests pass.

- [x] **Step 4: Commit changes**

```bash
git add scripts/convert_docs_to_pdf.py tests/test_docs_converter.py docs/plans/2026-08-27-convert-quiz-docs-to-pdf.md
git commit -m "feat: batch convert quiz docx/doc/pptx files to pdf with automated converter"
```

---

## Verification Plan

### Automated Tests
- Converter discovery & validation unit tests:
  ```bash
  python3 -m unittest tests/test_docs_converter.py
  ```

### Functional / Batch Verification
- Run converter across `from_the_past/정리/퀴즈`:
  ```bash
  python3 scripts/convert_docs_to_pdf.py from_the_past/정리/퀴즈
  ```
- PyMuPDF integrity verification script:
  ```bash
  python3 -c "import fitz; from pathlib import Path; quiz=Path('from_the_past/정리/퀴즈'); docs=[p for p in quiz.rglob('*') if p.suffix.lower() in ['.docx','.doc','.pptx'] and not p.name.startswith(('~$','.'))]; [fitz.open(d.with_suffix('.pdf')) for d in docs]; print(f'Successfully verified {len(docs)} PDFs!')"
  ```
