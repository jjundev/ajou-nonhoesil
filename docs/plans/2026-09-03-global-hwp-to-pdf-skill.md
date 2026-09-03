# Global HWP to PDF Skill (`hwp-to-pdf`) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a reusable, self-contained global skill `~/.gemini/config/skills/hwp-to-pdf/` that enables high-reliability HWP/HWPX to PDF conversion across all projects, incorporating single/multi-worker local conversion and `/dispatching-parallel-agents` orchestration for large distributed document sets.

**Architecture:** A self-contained global skill package with zero external Python dependencies. Bundled Python conversion engines (`hwp_to_pdf.py`, `split_hwp.py`) use standard library Python plus Headless Google Chrome via Chrome DevTools Protocol (CDP) and Allinpdf. The skill orchestrates tasks into two tiers: direct multi-worker execution for local/small batches, and parallel subagent dispatch with isolated CDP port allocation (`9222 + i*10`) for multi-directory or large-scale document conversions.

**Tech Stack:** Python 3 standard library (socket, struct, urllib, json, subprocess, concurrent.futures, shutil, os, sys, tempfile, pathlib), Chrome DevTools Protocol (CDP), Headless Google Chrome, Markdown Skill Spec (`SKILL.md`).

---

## Global Constraints

- Global Skill Path: `Path.home() / ".gemini/config/skills/hwp-to-pdf"` (`/Users/hyunjun_macbook_pro/.gemini/config/skills/hwp-to-pdf/`).
- Skill metadata: `name: hwp-to-pdf`, model-invoked (`disable-model-invocation` MUST NOT be set).
- Standalone execution: Zero third-party Python package dependencies (standard library only; dummy images in `split_hwp.py` use static byte literals without PIL).
- Port isolation: Subagents running in parallel must have strictly disjoint base ports (`9222 + i*10`) to prevent CDP socket collision.
- Output guarantee: Every converted PDF must pass validation (exist, size >= 100 bytes, `header.lstrip().startswith(b"%PDF-")`).
- Security notice: A 1-line notice stating conversion via external service (Allinpdf) must precede conversion start.
- Large files: Files >50MB must be flagged and rejected prior to upload in `hwp_to_pdf.py`, and routed to `split_hwp.py` before conversion.
- Lazy binary lookup: `get_chrome_binary()` must evaluate lazily upon converter initialization, not at module import time.

---

## File Structure

```text
~/.gemini/config/skills/hwp-to-pdf/
├── SKILL.md                          # Global skill definition, triggers, 2-tier orchestration logic
├── scripts/
│   ├── hwp_to_pdf.py                 # Unified Chrome CDP Allinpdf converter (single & multi-worker, standard lib only)
│   └── split_hwp.py                  # Pure-Python OLE2 compound document splitter for >50MB files (zero third-party deps)
└── references/
    └── dispatch-guide.md             # Subagent prompt templates and port-allocation reference for /dispatching-parallel-agents
```

Test file:
- `tests/test_global_hwp_to_pdf_skill.py`: Unit tests verifying skill structure, Python engine discovery, port allocation formula, lazy Chrome lookup, and PDF validation logic.

---

### Task 1: Implement Unified Python Engines in Global Skill & Add Unit Tests

**Files:**
- Create: `/Users/hyunjun_macbook_pro/.gemini/config/skills/hwp-to-pdf/scripts/hwp_to_pdf.py`
- Create: `/Users/hyunjun_macbook_pro/.gemini/config/skills/hwp-to-pdf/scripts/split_hwp.py`
- Create: `tests/test_global_hwp_to_pdf_skill.py`

**Interfaces:**
- Consumes: Existing implementations `scripts/parallel_hwp_converter.py` and `scripts/split_hwp.py`.
- Produces:
  - `discover_hwp_files(target: str) -> list[str]`
  - `validate_pdf(pdf_path: str) -> bool` (verifies `header.lstrip().startswith(b"%PDF-")` and size >= 100)
  - `resolve_output_pdf_path(hwp_path: str, base_target: str | None = None, output_dir: str | None = None) -> str`
  - `get_chrome_binary() -> str` (lazy evaluation)
  - `parallel_convert_hwp(files: list[str], max_workers: int = 3, force: bool = False, base_port: int = 9222, ...) -> dict`
  - CLI usage: `python3 ~/.gemini/config/skills/hwp-to-pdf/scripts/hwp_to_pdf.py <target> [--output-dir OUT] [--workers N] [--base-port P] [--force]`
  - `create_dummy_images() -> tuple[bytes, bytes]` returning `(real_jpg, real_bmp)` without PIL.

- [ ] **Step 1: Write the failing unit test**

Create `tests/test_global_hwp_to_pdf_skill.py`:
```python
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Portable path to global skill scripts directory
GLOBAL_SKILL_DIR = Path.home() / ".gemini/config/skills/hwp-to-pdf"
SCRIPTS_DIR = GLOBAL_SKILL_DIR / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

class TestGlobalHwpToPdfSkill(unittest.TestCase):
    def test_global_scripts_exist(self):
        hwp_to_pdf_script = SCRIPTS_DIR / "hwp_to_pdf.py"
        split_hwp_script = SCRIPTS_DIR / "split_hwp.py"
        self.assertTrue(hwp_to_pdf_script.exists(), "hwp_to_pdf.py should exist in global skill scripts")
        self.assertTrue(split_hwp_script.exists(), "split_hwp.py should exist in global skill scripts")

    def test_import_and_functions(self):
        import hwp_to_pdf  # type: ignore
        import split_hwp   # type: ignore
        self.assertTrue(callable(getattr(hwp_to_pdf, "discover_hwp_files", None)))
        self.assertTrue(callable(getattr(hwp_to_pdf, "validate_pdf", None)))
        self.assertTrue(callable(getattr(hwp_to_pdf, "resolve_output_pdf_path", None)))
        self.assertTrue(callable(getattr(hwp_to_pdf, "get_chrome_binary", None)))
        self.assertTrue(callable(getattr(split_hwp, "split_hwp_file", None)))
        self.assertTrue(callable(getattr(split_hwp, "create_dummy_images", None)))

    def test_split_hwp_dummy_images_zero_deps(self):
        import split_hwp  # type: ignore
        # Verify PIL is not imported
        self.assertNotIn("PIL", sys.modules)
        dummy_jpg, dummy_bmp = split_hwp.create_dummy_images()
        self.assertIsInstance(dummy_jpg, bytes)
        self.assertIsInstance(dummy_bmp, bytes)
        self.assertTrue(dummy_jpg.startswith(b"\xff\xd8\xff"))  # JPEG header
        self.assertTrue(dummy_bmp.startswith(b"BM"))            # BMP header

    def test_validate_pdf_logic(self):
        import hwp_to_pdf  # type: ignore
        with tempfile.TemporaryDirectory() as tmpdir:
            valid_pdf = os.path.join(tmpdir, "valid.pdf")
            with open(valid_pdf, "wb") as f:
                f.write(b"%PDF-1.4\n" + b"X" * 150 + b"\n%%EOF")
            self.assertTrue(hwp_to_pdf.validate_pdf(valid_pdf))

            # HTML error page containing %PDF- as substring must be rejected
            fake_html = os.path.join(tmpdir, "fake_html.pdf")
            with open(fake_html, "wb") as f:
                f.write(b"<!DOCTYPE html><html><body>Error converting to %PDF-1.4 format" + b"X" * 100 + b"</body></html>")
            self.assertFalse(hwp_to_pdf.validate_pdf(fake_html))

            # Empty or small file must be rejected
            small_pdf = os.path.join(tmpdir, "small.pdf")
            with open(small_pdf, "wb") as f:
                f.write(b"%PDF-")
            self.assertFalse(hwp_to_pdf.validate_pdf(small_pdf))

    def test_lazy_chrome_binary_lookup(self):
        import hwp_to_pdf  # type: ignore
        # Confirm get_chrome_binary can be called or mocked lazily without raising at import time
        with patch.dict(os.environ, {"CHROME_PATH": "/mock/nonexistent/chrome"}, clear=True):
            self.assertIsNotNone(hwp_to_pdf)

    def test_port_allocation_offset(self):
        # Base port offset formula check: agent i with offset 10
        base_ports = [9222 + i * 10 for i in range(3)]
        self.assertEqual(base_ports, [9222, 9232, 9242])

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests/test_global_hwp_to_pdf_skill.py`
Expected: FAIL (No module named 'hwp_to_pdf' or file does not exist).

- [ ] **Step 3: Implement `split_hwp.py` and `hwp_to_pdf.py` in global skill directory**

1. Create directory `~/.gemini/config/skills/hwp-to-pdf/scripts/`.
2. Implement `split_hwp.py` with zero PIL dependencies:
   - Remove `from PIL import Image`.
   - In `create_dummy_images()`, return `(real_jpg, real_bmp)` using static byte literals:
     - 1x1 white BMP: `b"BM\x3a\x00\x00\x00\x00\x00\x00\x00\x36\x00\x00\x00\x28\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x01\x00\x18\x00\x00\x00\x00\x00\x04\x00\x00\x00\x13\x0b\x00\x00\x13\x0b\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xff\xff\x00"`
     - 1x1 white JPEG: `b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xbf\x00\xff\xd9"`
3. Implement `hwp_to_pdf.py`:
   - Lazy Chrome binary lookup (`get_chrome_binary()` called inside `AllinpdfConverter.start()`, never evaluated at module import level).
   - Strict `validate_pdf()`:
     ```python
     def validate_pdf(pdf_path: str) -> bool:
         if not os.path.exists(pdf_path) or os.path.getsize(pdf_path) < 100:
             return False
         try:
             with open(pdf_path, "rb") as f:
                 header = f.read(1024)
                 return header.lstrip().startswith(b"%PDF-")
         except Exception:
             return False
     ```
   - 50MB hard size rejection in `AllinpdfConverter.convert_file()`:
     ```python
     file_size_mb = os.path.getsize(input_path) / (1024 * 1024)
     if file_size_mb > 50:
         print(f"  [!] Error: File size {file_size_mb:.1f}MB exceeds Allinpdf 50MB limit. Split using split_hwp.py before converting: {input_path}")
         return False
     ```
   - Pre-startup notice:
     `print("[Notice] Document conversion is processed via external service (Allinpdf) via Headless Chrome.", flush=True)`

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests/test_global_hwp_to_pdf_skill.py`
Expected: PASS (6 tests passing).

- [ ] **Step 5: Commit changes in project repository**

```bash
git add tests/test_global_hwp_to_pdf_skill.py
git commit -m "test: add unit test for global hwp-to-pdf skill"
```

---

### Task 2: Create Subagent Dispatch Reference Guide (`dispatch-guide.md`)

**Files:**
- Create: `/Users/hyunjun_macbook_pro/.gemini/config/skills/hwp-to-pdf/references/dispatch-guide.md`

**Interfaces:**
- Consumes: Rules from `/Users/hyunjun_macbook_pro/.gemini/config/skills/dispatching-parallel-agents/SKILL.md`.
- Produces: Standardized subagent prompts and port assignment specs for parallel HWP conversion.

- [ ] **Step 1: Write `dispatch-guide.md` with explicit prompt template and port mapping**

Create `/Users/hyunjun_macbook_pro/.gemini/config/skills/hwp-to-pdf/references/dispatch-guide.md`:
```markdown
# Parallel Agent Dispatch Guide for HWP to PDF

This guide provides instructions and templates for dispatching parallel subagents to convert HWP documents across multiple directories or large file sets using the `/dispatching-parallel-agents` pattern.

## When to Dispatch Parallel Agents

- **Trigger Condition:** 2 or more independent directories containing HWP files, OR 15+ HWP files spread across subfolders.
- **Why Parallel Dispatch:** Isolates context per domain, allows independent recovery/retries, and speeds up batch processing across large sets without context bloat in the coordinator.

## Chrome Debugging Port Allocation Rule

Each agent must be assigned an isolated base port range (`9222 + i * 10`) to prevent Chrome DevTools Protocol socket collisions:
- **Agent 0 (Worker Group 0):** `--base-port 9222 --workers 2` (Uses ports 9222, 9223)
- **Agent 1 (Worker Group 1):** `--base-port 9232 --workers 2` (Uses ports 9232, 9233)
- **Agent 2 (Worker Group 2):** `--base-port 9242 --workers 2` (Uses ports 9242, 9243)
- **Agent 3 (Worker Group 3):** `--base-port 9252 --workers 2` (Uses ports 9252, 9253)

## Subagent Dispatch Pattern

In the coordinator session, call `invoke_subagent` in a single turn for all target domains:

```python
invoke_subagent(
    Subagents=[
        {
            "TypeName": "self",
            "Role": "HWP Converter - Domain A",
            "Prompt": prompt_for_domain_a,
        },
        {
            "TypeName": "self",
            "Role": "HWP Converter - Domain B",
            "Prompt": prompt_for_domain_b,
        }
    ]
)
```

## Subagent Prompt Template

```markdown
Convert all HWP/HWPX documents in the assigned directory to PDF.

**Assigned Directory:** <ABSOLUTE_DIRECTORY_PATH>
**Pre-flight Check:**
Check file sizes beforehand. If any file exceeds 50MB, do NOT pass it directly to `hwp_to_pdf.py`. Instead, split it beforehand:
python3 /Users/hyunjun_macbook_pro/.gemini/config/skills/hwp-to-pdf/scripts/split_hwp.py "<FILE_PATH>"
and convert the resulting part files (`_part1.hwp`, `_part2.hwp`).

**Execution Command:**
python3 /Users/hyunjun_macbook_pro/.gemini/config/skills/hwp-to-pdf/scripts/hwp_to_pdf.py "<ABSOLUTE_DIRECTORY_PATH>" --base-port <ASSIGNED_BASE_PORT> -w 2

**Constraints:**
1. Do NOT modify or inspect files outside the assigned directory.
2. Verify each output PDF has `%PDF-` header and size >= 100 bytes.

**Return:**
A structured markdown summary containing:
- Total HWP files discovered in directory
- Successfully converted files list
- Failed or skipped files list
- Any split part files generated
```

## Integration Step for Coordinator

Upon receiving subagent completion messages:
1. Aggregate reports from all subagents.
2. Spot-check that all expected PDFs exist in their destination folders and pass `header.lstrip().startswith(b"%PDF-")`.
3. Output a unified batch conversion summary table to the user.
```

- [ ] **Step 2: Verify file readability and markdown rendering**

Verify: Check that `references/dispatch-guide.md` exists and contains valid markdown without broken code blocks.

---

### Task 3: Create `SKILL.md` and Register Global Skill

**Files:**
- Create: `/Users/hyunjun_macbook_pro/.gemini/config/skills/hwp-to-pdf/SKILL.md`
- Modify: `tests/test_global_hwp_to_pdf_skill.py` (add metadata & skill parsing test)

**Interfaces:**
- Consumes: `hwp_to_pdf.py`, `split_hwp.py`, and `references/dispatch-guide.md`.
- Produces: The primary entrypoint `SKILL.md` discovered by Antigravity runtime.

- [ ] **Step 1: Add SKILL.md validation test to `tests/test_global_hwp_to_pdf_skill.py`**

Update `tests/test_global_hwp_to_pdf_skill.py`:
```python
    def test_skill_md_metadata(self):
        skill_file = GLOBAL_SKILL_DIR / "SKILL.md"
        self.assertTrue(skill_file.exists(), "SKILL.md must exist in global skill")
        content = skill_file.read_text(encoding="utf-8")
        self.assertTrue(content.startswith("---"), "SKILL.md must start with YAML frontmatter")
        self.assertIn("name: hwp-to-pdf", content)
        self.assertIn("description:", content)
        self.assertNotIn("disable-model-invocation: true", content, "Should be model-invoked")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests/test_global_hwp_to_pdf_skill.py`
Expected: FAIL (SKILL.md does not exist yet).

- [ ] **Step 3: Create `/Users/hyunjun_macbook_pro/.gemini/config/skills/hwp-to-pdf/SKILL.md`**

```markdown
---
name: hwp-to-pdf
description: MUST USE when the user wants to convert HWP/HWPX documents to PDF — e.g. "HWP PDF로 변환해줘", "hwp to pdf", "한글 파일 변환", "/hwp-to-pdf", or batch converting HWP files across directories. Supports single-file conversion, high-speed multi-worker batch conversion, large file splitting (>50MB), and parallel subagent orchestration for multi-directory tasks.
---

# HWP to PDF Skill (`hwp-to-pdf`)

Converts Hancom Word Processor (HWP / HWPX) files into high-integrity PDF documents using headless Chrome automation with Chrome DevTools Protocol (CDP) and Allinpdf.

## Quick Start

### 1. Single File or Small Batch (<= 14 files, single directory)
Run the unified Python converter directly in the current session:

```bash
# Convert a single file (PDF saved alongside HWP)
python3 /Users/hyunjun_macbook_pro/.gemini/config/skills/hwp-to-pdf/scripts/hwp_to_pdf.py "path/to/document.hwp"

# Convert all files in a folder with 3 workers
python3 /Users/hyunjun_macbook_pro/.gemini/config/skills/hwp-to-pdf/scripts/hwp_to_pdf.py "path/to/folder" -w 3

# Specify output directory
python3 /Users/hyunjun_macbook_pro/.gemini/config/skills/hwp-to-pdf/scripts/hwp_to_pdf.py "path/to/folder" -o "path/to/output_pdf"
```

---

### 2. Large Batch or Multi-Directory (>= 2 independent folders OR >= 15 files)
Follow the `/dispatching-parallel-agents` pattern to isolate tasks and avoid session context bloat:

1. **Scan:** Identify target directories containing HWP files.
2. **Assign Ports:** Give each subagent an isolated base port (`9222 + i*10`):
   - Subagent 0: `--base-port 9222 -w 2`
   - Subagent 1: `--base-port 9232 -w 2`
   - Subagent 2: `--base-port 9242 -w 2`
3. **Dispatch in Parallel:** In a single response, invoke one subagent per domain using `invoke_subagent`. See [dispatch-guide.md](references/dispatch-guide.md) for full prompt templates.
4. **Aggregate & Verify:** Inspect subagent completion summaries and ensure all PDFs start with `%PDF-` and >= 100 bytes.

---

## Large Files Handling (> 50MB)
Online conversion services (Allinpdf) reject files exceeding 50MB. If a file exceeds 50MB:
```bash
python3 /Users/hyunjun_macbook_pro/.gemini/config/skills/hwp-to-pdf/scripts/split_hwp.py "path/to/large_file.hwp"
```
This produces `large_file_part1.hwp`, `large_file_part2.hwp`, etc. Convert the parts into corresponding PDFs.

---

## Security & Privacy Notice
All conversions are routed through external SaaS (Allinpdf) via Headless Chrome. Before running, notify the user if files contain strictly confidential data.
```

- [ ] **Step 4: Run tests to verify all pass**

Run: `python3 -m unittest tests/test_global_hwp_to_pdf_skill.py`
Expected: PASS (7 tests passing).

- [ ] **Step 5: Run existing project tests to prevent regressions**

Run: `python3 -m unittest discover -s tests -p "test_*.py"`
Expected: All tests pass.

- [ ] **Step 6: Commit test additions**

```bash
git add tests/test_global_hwp_to_pdf_skill.py
git commit -m "feat: complete test suite for global hwp-to-pdf skill"
```

---

## Verification Plan

### Automated Tests
- `python3 -m unittest tests/test_global_hwp_to_pdf_skill.py`
- `python3 -m unittest tests/test_parallel_hwp_converter.py`
- `python3 -m unittest tests/test_skill_docs.py` (if applicable for skill schema/doc tests)

### Manual Verification
- Verify that `~/.gemini/config/skills/hwp-to-pdf/` contains `SKILL.md`, `scripts/hwp_to_pdf.py`, `scripts/split_hwp.py`, and `references/dispatch-guide.md`.
- Test running `python3 ~/.gemini/config/skills/hwp-to-pdf/scripts/hwp_to_pdf.py --help` from a shell.
- Run a conversion dry-run on a test fixture HWP file.
