# Organize Converted PDFs into Report Directories Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Copy and organize all 65 converted PDF files from `from_the_past/pdf 모음` into their matching destination folders under `from_the_past/정리/예비보고서` (36 files), `from_the_past/정리/결과보고서` (21 files), and `from_the_past/정리/퀴즈` (8 files).

**Architecture:** A lightweight Python distribution script reads the 1:1 mapped HWP layout in `from_the_past/정리`, copies each corresponding `.pdf` from `from_the_past/pdf 모음` to its exact corresponding directory (e.g. `예비보고서/실험1/`, `결과보고서/실험10/`), verifies file sizes and non-emptiness, and outputs a complete distribution summary.

**Tech Stack:** Python 3 standard library (`os`, `shutil`, `pathlib`).

## Global Constraints

- Source files are strictly read from `/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/pdf 모음`.
- Destination root is `/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리`.
- Preserve existing files in destination directories without unintentional overwrites; verified copy with hash or size check.
- Target categories:
  - `예비보고서` (36 files)
  - `결과보고서` (21 files)
  - `퀴즈` (8 files)

---

### Task 1: Copy and Place 예비보고서 PDFs (36 files)

**Files:**
- Source: `/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/pdf 모음/*.pdf`
- Destination: `/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/예비보고서/` (and subdirectories `실험1` ~ `실험10`)

**Interfaces:**
- Consumes: 36 PDF files corresponding to 예비보고서 HWP files.
- Produces: 36 PDF files placed in matching `예비보고서/실험X/` folders.

- [ ] **Step 1: Execute copy for 예비보고서 files**
```python
import os, shutil

src_dir = '/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/pdf 모음'
dst_base = '/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/예비보고서'

mappings = [
    ('논리회로실험 설계예비보고서.pdf', ''),
    ('프로젝트예비1주차.pdf', ''),
    ('실험1 180914제출 예비보고서.pdf', '실험1'),
    ('예비1.pdf', '실험1'),
    ('실험2 180921제출 예비보고서.pdf', '실험2'),
    ('실험2 예비.pdf', '실험2'),
    ('예비2.pdf', '실험2'),
    ('실험3 180928제출 예비보고서.pdf', '실험3'),
    ('실험3 예비.pdf', '실험3'),
    ('예비3.pdf', '실험3'),
    ('실험4 181005제출 예비보고서.pdf', '실험4'),
    ('실험4 예비.pdf', '실험4'),
    ('실험4 예비보고서.pdf', '실험4'),
    ('예비4.pdf', '실험4'),
    ('실험5 181012제출 예비보고서.pdf', '실험5'),
    ('실험5 예비.pdf', '실험5'),
    ('예비5.pdf', '실험5'),
    ('실험6 181019제출 예비보고서.pdf', '실험6'),
    ('실험6 예비.pdf', '실험6'),
    ('실험6 예비보고서.pdf', '실험6'),
    ('예비6.pdf', '실험6'),
    ('실험7 181102제출 예비보고서.pdf', '실험7'),
    ('실험7 예비.pdf', '실험7'),
    ('실험7 예비보고서.pdf', '실험7'),
    ('예비7.pdf', '실험7'),
    ('실험8 181109제출 예비보고서.pdf', '실험8'),
    ('실험8 예비.pdf', '실험8'),
    ('실험8 예비보고서.pdf', '실험8'),
    ('예비8.pdf', '실험8'),
    ('실험9 181116제출 예비보고서.pdf', '실험9'),
    ('실험9 예비.pdf', '실험9'),
    ('실험9 예비보고서.pdf', '실험9'),
    ('예비9.pdf', '실험9'),
    ('실험10 181123제출 예비보고서.pdf', '실험10'),
    ('실험10 예비.pdf', '실험10'),
    ('예비보고서 10.pdf', '실험10'),
]

for filename, sub in mappings:
    src = os.path.join(src_dir, filename)
    target_dir = os.path.join(dst_base, sub)
    os.makedirs(target_dir, exist_ok=True)
    dst = os.path.join(target_dir, filename)
    shutil.copy2(src, dst)
    assert os.path.exists(dst) and os.path.getsize(dst) > 0
```

- [ ] **Step 2: Verify 예비보고서 copy**
Check that all 36 files exist in `from_the_past/정리/예비보고서` and have valid non-zero file sizes matching the source.

---

### Task 2: Copy and Place 결과보고서 PDFs (21 files)

**Files:**
- Source: `/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/pdf 모음/*.pdf`
- Destination: `/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/결과보고서/` (and subdirectories `실험2` ~ `실험10`)

**Interfaces:**
- Consumes: 21 PDF files corresponding to 결과보고서 HWP files.
- Produces: 21 PDF files placed in matching `결과보고서/실험X/` folders.

- [ ] **Step 1: Execute copy for 결과보고서 files**
```python
import os, shutil

src_dir = '/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/pdf 모음'
dst_base = '/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/결과보고서'

mappings = [
    ('논리회로실험 설계결과보고서.pdf', ''),
    ('실험2 180928제출 결과보고서.pdf', '실험2'),
    ('실험2 결과.pdf', '실험2'),
    ('실험2 결과보고서(9.29수정).pdf', '실험2'),
    ('실험3 181005제출 결과보고서.pdf', '실험3'),
    ('실험3 결과.pdf', '실험3'),
    ('실험4 181012제출 결과보고서.pdf', '실험4'),
    ('실험4 결과.pdf', '실험4'),
    ('실험5 181019제출 결과보고서.pdf', '실험5'),
    ('실험5 결과.pdf', '실험5'),
    ('실험6 181102제출 결과보고서.pdf', '실험6'),
    ('실험6 결과.pdf', '실험6'),
    ('실험7 181109제출 결과보고서.pdf', '실험7'),
    ('실험7 결과.pdf', '실험7'),
    ('실험8 181116제출 결과보고서.pdf', '실험8'),
    ('실험8 결과.pdf', '실험8'),
    ('실험9 181123제출 결과보고서.pdf', '실험9'),
    ('실험9 결과.pdf', '실험9'),
    ('(결과)10. DAC_ADC.pdf', '실험10'),
    ('실험10 181130제출 결과보고서.pdf', '실험10'),
    ('실험10 결과.pdf', '실험10'),
]

for filename, sub in mappings:
    src = os.path.join(src_dir, filename)
    target_dir = os.path.join(dst_base, sub)
    os.makedirs(target_dir, exist_ok=True)
    dst = os.path.join(target_dir, filename)
    shutil.copy2(src, dst)
    assert os.path.exists(dst) and os.path.getsize(dst) > 0
```

- [ ] **Step 2: Verify 결과보고서 copy**
Check that all 21 files exist in `from_the_past/정리/결과보고서` and have valid non-zero file sizes matching the source.

---

### Task 3: Copy and Place 퀴즈 PDFs (8 files)

**Files:**
- Source: `/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/pdf 모음/*.pdf`
- Destination: `/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/퀴즈/`

**Interfaces:**
- Consumes: 8 PDF files corresponding to 퀴즈 HWP files.
- Produces: 8 PDF files placed in `from_the_past/정리/퀴즈/`.

- [ ] **Step 1: Execute copy for 퀴즈 files**
```python
import os, shutil

src_dir = '/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/pdf 모음'
dst_base = '/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/퀴즈'

mappings = [
    'quiz_05.pdf',
    'quiz_06.pdf',
    'quiz_07(1).pdf',
    'quiz_09(1).pdf',
    '실험 3 (2).pdf',
    '실험 3 (3).pdf',
    '실험 3.pdf',
    '실험3.pdf',
]

for filename in mappings:
    src = os.path.join(src_dir, filename)
    dst = os.path.join(dst_base, filename)
    shutil.copy2(src, dst)
    assert os.path.exists(dst) and os.path.getsize(dst) > 0
```

- [ ] **Step 2: Verify 퀴즈 copy**
Check that all 8 files exist in `from_the_past/정리/퀴즈` and have valid non-zero file sizes matching the source.

---

### Task 4: Complete Distribution Integrity Verification

**Files:**
- Audit: `/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리`

- [ ] **Step 1: Run total count and file-size audit across all categories**
Run Python audit script ensuring all 65 converted PDFs in `from_the_past/pdf 모음` exist in their target category directory with 100% integrity.
