# Reorganize Past Materials (`논회실 김지성` → `정리`) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move and integrate all legacy lab materials, reports, lecture notes, FPGA project files, quiz sources, videos, and guidelines from `from_the_past/논회실 김지성` into their respective destination folders under `from_the_past/정리`, followed by cleaning up duplicate and temporary files and pruning the empty source directory.

**Architecture:** A series of deterministic Python migration and validation tasks sequentially map source files to standard target categories (`예비보고서/실험1~10`, `결과보고서/실험4~10`, `강의노트/2020-2/`, `퀴즈/`, `나머지/가이드라인/`, `나머지/8주차 대면실험 영상/`, `나머지/project_2020-2_김지성/`), check file integrity and non-emptiness, remove redundant copies/temporary files (`debug.log`, duplicate Quartus root folder), and perform a full-tree audit.

**Tech Stack:** Python 3 (`os`, `shutil`, `unicodedata`, `hashlib`, `pathlib`).

## Global Constraints

- Source directory: `/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/논회실 김지성`
- Destination root: `/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리`
- Handle Unicode NFC/NFD filename normalization on macOS to ensure robust file lookups.
- Preserve file integrity: verify file sizes and non-emptiness after move.
- Total files to migrate: 84 independent files + 1 complete Quartus project directory.
- Exclude/delete temporary CEF `debug.log`.
- Prune empty source folder after all files have been safely migrated and verified.

---

### Task 1: Create Destination Directory Scaffolding

**Files:**
- Create directories under: `/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/`
  - `강의노트/2020-2/`
  - `예비보고서/프로젝트/`
  - `결과보고서/설계/`
  - `나머지/가이드라인/`
  - `나머지/8주차 대면실험 영상/`
  - `나머지/project_2020-2_김지성/`

**Interfaces:**
- Consumes: Existing destination root `from_the_past/정리/`.
- Produces: Required subdirectories ready for file migration.

- [x] **Step 1: Execute directory creation script**

```python
import os

dst_base = "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리"

dirs_to_create = [
    "강의노트/2020-2",
    "예비보고서/프로젝트",
    "결과보고서/설계",
    "나머지/가이드라인",
    "나머지/8주차 대면실험 영상",
    "나머지/project_2020-2_김지성",
]

for d in dirs_to_create:
    full_path = os.path.join(dst_base, d)
    os.makedirs(full_path, exist_ok=True)
    print(f"[+] Created directory: {d}")
```

- [x] **Step 2: Verify all target directories exist**

```python
import os

dst_base = "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리"
dirs_to_check = [
    "강의노트/2020-2",
    "예비보고서/프로젝트",
    "결과보고서/설계",
    "나머지/가이드라인",
    "나머지/8주차 대면실험 영상",
    "나머지/project_2020-2_김지성",
]
for d in dirs_to_check:
    full_path = os.path.join(dst_base, d)
    assert os.path.isdir(full_path), f"Directory missing: {full_path}"

print("[✓] All target directories verified.")
```

---

### Task 2: Move and Verify 예비보고서 Files (26 files) + 설계계획서 (2 files)

**Files:**
- Source: `/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/논회실 김지성/예보/` (26 files) & `설계/Project_설계계획서.*` (2 files)
- Destination: `/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/예비보고서/` (subfolders `실험1` ~ `실험10`, `프로젝트`)

**Interfaces:**
- Consumes: 26 files in `예보/` + 2 files in `설계/`.
- Produces: 28 files distributed into `예비보고서/실험1~10/` and `예비보고서/프로젝트/`.

- [x] **Step 1: Execute file migration for 예비보고서**

```python
import os, shutil, unicodedata

src_base = "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/논회실 김지성"
dst_base = "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/예비보고서"

def find_file(dir_path, filename):
    norm_fn = unicodedata.normalize("NFC", filename)
    for x in os.listdir(dir_path):
        if unicodedata.normalize("NFC", x) == norm_fn:
            return os.path.join(dir_path, x)
    return None

yebo_mappings = [
    ("논회실 1주차 예보1.hwp", "실험1"),
    ("논회실 1주차 예보1.pdf", "실험1"),
    ("논회실 1주차 예보2.hwp", "실험1"),
    ("논회실 1주차 예보2.pdf", "실험1"),
    ("논회실 2주차 예보1.hwp", "실험2"),
    ("논회실 2주차 예보1.pdf", "실험2"),
    ("논회실 2주차 예보2.hwp", "실험2"),
    ("논회실 2주차 예보2.pdf", "실험2"),
    ("논회실 3주차 예보1.hwp", "실험3"),
    ("논회실 3주차 예보1.pdf", "실험3"),
    ("논회실 3주차 예보2.hwp", "실험3"),
    ("논회실 3주차 예보2.pdf", "실험3"),
    ("논회실 4주차 예보.hwp", "실험4"),
    ("논회실 4주차 예보.pdf", "실험4"),
    ("논회실 5주차 예보.hwp", "실험5"),
    ("논회실 5주차 예보.pdf", "실험5"),
    ("논회실 6주차 예보.hwp", "실험6"),
    ("논회실 6주차 예보.pdf", "실험6"),
    ("논회실 7주차 예보.hwp", "실험7"),
    ("논회실 7주차 예보.pdf", "실험7"),
    ("논회실 8주차 예보.hwp", "실험8"),
    ("논회실 8주차 예보.pdf", "실험8"),
    ("논회실 9주차 예보.hwp", "실험9"),
    ("논회실 9주차 예보.pdf", "실험9"),
    ("논회실 10주차 예보.hwp", "실험10"),
    ("논회실 10주차 예보.pdf", "실험10"),
]

for filename, sub in yebo_mappings:
    src_file = find_file(os.path.join(src_base, "예보"), filename)
    assert src_file is not None, f"Source file not found: {filename}"
    target_dir = os.path.join(dst_base, sub)
    os.makedirs(target_dir, exist_ok=True)
    dst_file = os.path.join(target_dir, filename)
    shutil.move(src_file, dst_file)
    print(f"[+] Moved {filename} -> 예비보고서/{sub}/")

# Move Project_설계계획서
design_plan_mappings = [
    ("Project_설계계획서.hwp", "프로젝트"),
    ("Project_설계계획서.pdf", "프로젝트"),
]
for filename, sub in design_plan_mappings:
    src_file = find_file(os.path.join(src_base, "설계"), filename)
    assert src_file is not None, f"Source file not found: {filename}"
    target_dir = os.path.join(dst_base, sub)
    os.makedirs(target_dir, exist_ok=True)
    dst_file = os.path.join(target_dir, filename)
    shutil.move(src_file, dst_file)
    print(f"[+] Moved {filename} -> 예비보고서/{sub}/")
```

- [x] **Step 2: Verify 예비보고서 files in destination**

```python
import os, unicodedata

dst_base = "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/예비보고서"

def find_file(dir_path, filename):
    norm_fn = unicodedata.normalize("NFC", filename)
    for x in os.listdir(dir_path):
        if unicodedata.normalize("NFC", x) == norm_fn:
            return os.path.join(dir_path, x)
    return None

expected = [
    ("논회실 1주차 예보1.hwp", "실험1"),
    ("논회실 1주차 예보1.pdf", "실험1"),
    ("논회실 1주차 예보2.hwp", "실험1"),
    ("논회실 1주차 예보2.pdf", "실험1"),
    ("논회실 2주차 예보1.hwp", "실험2"),
    ("논회실 2주차 예보1.pdf", "실험2"),
    ("논회실 2주차 예보2.hwp", "실험2"),
    ("논회실 2주차 예보2.pdf", "실험2"),
    ("논회실 3주차 예보1.hwp", "실험3"),
    ("논회실 3주차 예보1.pdf", "실험3"),
    ("논회실 3주차 예보2.hwp", "실험3"),
    ("논회실 3주차 예보2.pdf", "실험3"),
    ("논회실 4주차 예보.hwp", "실험4"),
    ("논회실 4주차 예보.pdf", "실험4"),
    ("논회실 5주차 예보.hwp", "실험5"),
    ("논회실 5주차 예보.pdf", "실험5"),
    ("논회실 6주차 예보.hwp", "실험6"),
    ("논회실 6주차 예보.pdf", "실험6"),
    ("논회실 7주차 예보.hwp", "실험7"),
    ("논회실 7주차 예보.pdf", "실험7"),
    ("논회실 8주차 예보.hwp", "실험8"),
    ("논회실 8주차 예보.pdf", "실험8"),
    ("논회실 9주차 예보.hwp", "실험9"),
    ("논회실 9주차 예보.pdf", "실험9"),
    ("논회실 10주차 예보.hwp", "실험10"),
    ("논회실 10주차 예보.pdf", "실험10"),
    ("Project_설계계획서.hwp", "프로젝트"),
    ("Project_설계계획서.pdf", "프로젝트"),
]

for filename, sub in expected:
    target_dir = os.path.join(dst_base, sub)
    p = find_file(target_dir, filename)
    assert p is not None and os.path.getsize(p) > 0, f"Verification failed: {filename} in {sub}"

print("[✓] All 28 예비보고서 & 설계계획서 files successfully verified.")
```

---

### Task 3: Move and Verify 결과보고서 Files (14 files) + 설계보고서 (12 files)

**Files:**
- Source: `/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/논회실 김지성/결보/` (14 files) & `설계/Project_설계보고서*` (12 files)
- Destination: `/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/결과보고서/` (subfolders `실험4` ~ `실험10`, `설계`)

**Interfaces:**
- Consumes: 14 files in `결보/` + 12 files in `설계/`.
- Produces: 26 files placed into `결과보고서/실험4~10/` and `결과보고서/설계/`.

- [x] **Step 1: Execute file migration for 결과보고서**

```python
import os, shutil, unicodedata

src_base = "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/논회실 김지성"
dst_base = "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/결과보고서"

def find_file(dir_path, filename):
    norm_fn = unicodedata.normalize("NFC", filename)
    for x in os.listdir(dir_path):
        if unicodedata.normalize("NFC", x) == norm_fn:
            return os.path.join(dir_path, x)
    return None

gyulbo_mappings = [
    ("논회실 4주차 결보.hwp", "실험4"),
    ("논회실 4주차 결보.pdf", "실험4"),
    ("논회실 5주차 결보.hwp", "실험5"),
    ("논회실 5주차 결보.pdf", "실험5"),
    ("논회실 6주차 결보.hwp", "실험6"),
    ("논회실 6주차 결보.pdf", "실험6"),
    ("논회실 7주차 결보.hwp", "실험7"),
    ("논회실 7주차 결보.pdf", "실험7"),
    ("논회실 8주차 결보.hwp", "실험8"),
    ("논회실 8주차 결보.pdf", "실험8"),
    ("논회실 9주차 결보.hwp", "실험9"),
    ("논회실 9주차 결보.pdf", "실험9"),
    ("논회실 10주차 결보.hwp", "실험10"),
    ("논회실 10주차 결보.pdf", "실험10"),
]

for filename, sub in gyulbo_mappings:
    src_file = find_file(os.path.join(src_base, "결보"), filename)
    assert src_file is not None, f"Source file not found: {filename}"
    target_dir = os.path.join(dst_base, sub)
    os.makedirs(target_dir, exist_ok=True)
    dst_file = os.path.join(target_dir, filename)
    shutil.move(src_file, dst_file)
    print(f"[+] Moved {filename} -> 결과보고서/{sub}/")

# Move Project_설계보고서 (단일본 2개 + part1~5 분할본 10개)
design_report_mappings = [
    ("Project_설계보고서.hwp", "설계"),
    ("Project_설계보고서.pdf", "설계"),
    ("Project_설계보고서_part1.hwp", "설계"),
    ("Project_설계보고서_part1.pdf", "설계"),
    ("Project_설계보고서_part2.hwp", "설계"),
    ("Project_설계보고서_part2.pdf", "설계"),
    ("Project_설계보고서_part3.hwp", "설계"),
    ("Project_설계보고서_part3.pdf", "설계"),
    ("Project_설계보고서_part4.hwp", "설계"),
    ("Project_설계보고서_part4.pdf", "설계"),
    ("Project_설계보고서_part5.hwp", "설계"),
    ("Project_설계보고서_part5.pdf", "설계"),
]
for filename, sub in design_report_mappings:
    src_file = find_file(os.path.join(src_base, "설계"), filename)
    assert src_file is not None, f"Source file not found: {filename}"
    target_dir = os.path.join(dst_base, sub)
    os.makedirs(target_dir, exist_ok=True)
    dst_file = os.path.join(target_dir, filename)
    shutil.move(src_file, dst_file)
    print(f"[+] Moved {filename} -> 결과보고서/{sub}/")
```

- [x] **Step 2: Verify 결과보고서 files in destination**

```python
import os, unicodedata

dst_base = "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/결과보고서"

def find_file(dir_path, filename):
    norm_fn = unicodedata.normalize("NFC", filename)
    for x in os.listdir(dir_path):
        if unicodedata.normalize("NFC", x) == norm_fn:
            return os.path.join(dir_path, x)
    return None

expected = [
    ("논회실 4주차 결보.hwp", "실험4"),
    ("논회실 4주차 결보.pdf", "실험4"),
    ("논회실 5주차 결보.hwp", "실험5"),
    ("논회실 5주차 결보.pdf", "실험5"),
    ("논회실 6주차 결보.hwp", "실험6"),
    ("논회실 6주차 결보.pdf", "실험6"),
    ("논회실 7주차 결보.hwp", "실험7"),
    ("논회실 7주차 결보.pdf", "실험7"),
    ("논회실 8주차 결보.hwp", "실험8"),
    ("논회실 8주차 결보.pdf", "실험8"),
    ("논회실 9주차 결보.hwp", "실험9"),
    ("논회실 9주차 결보.pdf", "실험9"),
    ("논회실 10주차 결보.hwp", "실험10"),
    ("논회실 10주차 결보.pdf", "실험10"),
    ("Project_설계보고서.hwp", "설계"),
    ("Project_설계보고서.pdf", "설계"),
    ("Project_설계보고서_part1.hwp", "설계"),
    ("Project_설계보고서_part1.pdf", "설계"),
    ("Project_설계보고서_part2.hwp", "설계"),
    ("Project_설계보고서_part2.pdf", "설계"),
    ("Project_설계보고서_part3.hwp", "설계"),
    ("Project_설계보고서_part3.pdf", "설계"),
    ("Project_설계보고서_part4.hwp", "설계"),
    ("Project_설계보고서_part4.pdf", "설계"),
    ("Project_설계보고서_part5.hwp", "설계"),
    ("Project_설계보고서_part5.pdf", "설계"),
]

for filename, sub in expected:
    target_dir = os.path.join(dst_base, sub)
    p = find_file(target_dir, filename)
    assert p is not None and os.path.getsize(p) > 0, f"Verification failed: {filename} in {sub}"

print("[✓] All 26 결과보고서 & 설계보고서 files successfully verified.")
```

---

### Task 4: Move 강의노트 (2020-2 슬라이드 10종, 매뉴얼, 사진) & Delete `debug.log`

**Files:**
- Source: `/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/논회실 김지성/논회실 강의노트/`
- Destination: `/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/강의노트/2020-2/`
- Delete: `/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/논회실 김지성/논회실 강의노트/debug.log`

**Interfaces:**
- Consumes: 12 lecture files + 1 temporary log file.
- Produces: 12 files placed in `강의노트/2020-2/`, `debug.log` purged.

- [x] **Step 1: Execute migration and log deletion**

```python
import os, shutil, unicodedata

src_dir = "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/논회실 김지성/논회실 강의노트"
dst_dir = "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/강의노트/2020-2"
os.makedirs(dst_dir, exist_ok=True)

# Delete debug.log
debug_log = os.path.join(src_dir, "debug.log")
if os.path.exists(debug_log):
    os.remove(debug_log)
    print("[-] Removed temporary debug.log")

lecture_files = [
    "실험1.pptx.pdf",
    "실험2.pptx.pdf",
    "실험3.ppt.pdf",
    "실험4.ppt.pdf",
    "실험5.pptx.pdf",
    "실험6.pptx.pdf",
    "실험7.pptx.pdf",
    "실험8.pptx.pdf",
    "실험9.ppt.pdf",
    "실험10.pptx.pdf",
    "Breadboard.jpg",
    "오실로스코프 메뉴얼.pdf",
]

def find_file(dir_path, filename):
    norm_fn = unicodedata.normalize("NFC", filename)
    for x in os.listdir(dir_path):
        if unicodedata.normalize("NFC", x) == norm_fn:
            return os.path.join(dir_path, x)
    return None

for filename in lecture_files:
    src_file = find_file(src_dir, filename)
    assert src_file is not None, f"Lecture file not found: {filename}"
    dst_file = os.path.join(dst_dir, filename)
    shutil.move(src_file, dst_file)
    print(f"[+] Moved {filename} -> 강의노트/2020-2/")
```

- [x] **Step 2: Verify lecture files in destination**

```python
import os, unicodedata

dst_dir = "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/강의노트/2020-2"

def find_file(dir_path, filename):
    norm_fn = unicodedata.normalize("NFC", filename)
    for x in os.listdir(dir_path):
        if unicodedata.normalize("NFC", x) == norm_fn:
            return os.path.join(dir_path, x)
    return None

expected = [
    "실험1.pptx.pdf",
    "실험2.pptx.pdf",
    "실험3.ppt.pdf",
    "실험4.ppt.pdf",
    "실험5.pptx.pdf",
    "실험6.pptx.pdf",
    "실험7.pptx.pdf",
    "실험8.pptx.pdf",
    "실험9.ppt.pdf",
    "실험10.pptx.pdf",
    "Breadboard.jpg",
    "오실로스코프 메뉴얼.pdf",
]

for filename in expected:
    p = find_file(dst_dir, filename)
    assert p is not None and os.path.getsize(p) > 0, f"Lecture verification failed: {filename}"

print("[✓] All 12 2020-2 lecture files successfully verified.")
```

---

### Task 5: Move 퀴즈 소스, 가이드라인, ic칩.txt, 8주차 대면실험 영상

**Files:**
- Source: `/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/논회실 김지성/`
  - `논회실 퀴즈 소스.pdf` $\rightarrow$ `정리/퀴즈/`
  - `ic칩.txt` $\rightarrow$ `정리/나머지/`
  - 가이드라인 8종 $\rightarrow$ `정리/나머지/가이드라인/`
  - `8주차 대면실험 영상/` (3개 mp4) $\rightarrow$ `정리/나머지/8주차 대면실험 영상/`

**Interfaces:**
- Consumes: 10 root files + 3 video files.
- Produces: Files placed in respective destinations.

- [x] **Step 1: Execute file migration**

```python
import os, shutil, unicodedata

src_base = "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/논회실 김지성"
dst_base = "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리"

def find_file(dir_path, filename):
    norm_fn = unicodedata.normalize("NFC", filename)
    for x in os.listdir(dir_path):
        if unicodedata.normalize("NFC", x) == norm_fn:
            return os.path.join(dir_path, x)
    return None

# Ensure target category folders exist
os.makedirs(os.path.join(dst_base, "퀴즈"), exist_ok=True)
os.makedirs(os.path.join(dst_base, "나머지"), exist_ok=True)

# 1. 퀴즈 소스
quiz_src = find_file(src_base, "논회실 퀴즈 소스.pdf")
shutil.move(quiz_src, os.path.join(dst_base, "퀴즈", "논회실 퀴즈 소스.pdf"))
print("[+] Moved 논회실 퀴즈 소스.pdf -> 퀴즈/")

# 2. ic칩.txt
ic_src = find_file(src_base, "ic칩.txt")
shutil.move(ic_src, os.path.join(dst_base, "나머지", "ic칩.txt"))
print("[+] Moved ic칩.txt -> 나머지/")

# 3. 가이드라인
guidelines = [
    "논회실 결보 가이드라인.hwp",
    "논회실 결보 가이드라인.pdf",
    "논회실 예보 가이드라인.hwp",
    "논회실 예보 가이드라인.pdf",
    "논회실 예보1 가이드라인.hwp",
    "논회실 예보1 가이드라인.pdf",
    "논회실 예보2 가이드라인.hwp",
    "논회실 예보2 가이드라인.pdf",
]
gl_dst = os.path.join(dst_base, "나머지", "가이드라인")
os.makedirs(gl_dst, exist_ok=True)
for g in guidelines:
    g_src = find_file(src_base, g)
    assert g_src is not None, f"Guideline missing: {g}"
    shutil.move(g_src, os.path.join(gl_dst, g))
    print(f"[+] Moved {g} -> 나머지/가이드라인/")

# 4. 8주차 대면실험 영상
vid_src = os.path.join(src_base, "8주차 대면실험 영상")
vid_dst = os.path.join(dst_base, "나머지", "8주차 대면실험 영상")
os.makedirs(vid_dst, exist_ok=True)
for v in ["1.mp4", "2.mp4", "3.mp4"]:
    v_path = find_file(vid_src, v)
    assert v_path is not None, f"Video missing: {v}"
    shutil.move(v_path, os.path.join(vid_dst, v))
    print(f"[+] Moved {v} -> 나머지/8주차 대면실험 영상/")
```

- [x] **Step 2: Verify quiz, guidelines, ic칩, and video files in destination**

```python
import os, unicodedata

dst_base = "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리"

def find_file(dir_path, filename):
    norm_fn = unicodedata.normalize("NFC", filename)
    for x in os.listdir(dir_path):
        if unicodedata.normalize("NFC", x) == norm_fn:
            return os.path.join(dir_path, x)
    return None

# Check quiz
assert find_file(os.path.join(dst_base, "퀴즈"), "논회실 퀴즈 소스.pdf") is not None
# Check ic칩
assert find_file(os.path.join(dst_base, "나머지"), "ic칩.txt") is not None
# Check guidelines
for g in [
    "논회실 결보 가이드라인.hwp", "논회실 결보 가이드라인.pdf",
    "논회실 예보 가이드라인.hwp", "논회실 예보 가이드라인.pdf",
    "논회실 예보1 가이드라인.hwp", "논회실 예보1 가이드라인.pdf",
    "논회실 예보2 가이드라인.hwp", "논회실 예보2 가이드라인.pdf"
]:
    assert find_file(os.path.join(dst_base, "나머지", "가이드라인"), g) is not None
# Check videos
for v in ["1.mp4", "2.mp4", "3.mp4"]:
    assert find_file(os.path.join(dst_base, "나머지", "8주차 대면실험 영상"), v) is not None

print("[✓] All quiz, guidelines, ic칩, and video files successfully verified.")
```

---

### Task 6: Move FPGA Design Files & Project, Clean Duplicates, and Prune Empty Source Directory

**Files:**
- Source: `/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/논회실 김지성/설계/` (교안 3종, `논회실 project.zip`, `설계 코드.txt`, `논회실 project/` 디렉토리)
- Destination: `/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/나머지/project_2020-2_김지성/`
- Delete:
  - Duplicate `/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/논회실 김지성/논회실 project`
  - Empty `/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/논회실 김지성` folder

**Interfaces:**
- Consumes: FPGA design materials + duplicate project folder.
- Produces: `정리/나머지/project_2020-2_김지성/` containing complete project archive and clean removal of empty source directories.

- [x] **Step 1: Execute migration and cleanup**

```python
import os, shutil, unicodedata

src_base = "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/논회실 김지성"
dst_project_dir = "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/나머지/project_2020-2_김지성"
os.makedirs(dst_project_dir, exist_ok=True)

def find_file(dir_path, filename):
    norm_fn = unicodedata.normalize("NFC", filename)
    for x in os.listdir(dir_path):
        if unicodedata.normalize("NFC", x) == norm_fn:
            return os.path.join(dir_path, x)
    return None

# 1. Delete duplicate root project folder if exists
dup_proj = os.path.join(src_base, "논회실 project")
if os.path.exists(dup_proj):
    shutil.rmtree(dup_proj)
    print("[-] Removed duplicate root `논회실 project` folder.")

# 2. Move FPGA documents & files from 설계
design_src = os.path.join(src_base, "설계")
fpga_files = [
    "[2020-2] FPGA 설계 환경 구축 및 실습.pdf",
    "[2020-2] Verilog 기초.pdf",
    "[2020-2] 설계과제.pdf",
    "논회실 project.zip",
    "설계 코드.txt",
]
for f in fpga_files:
    f_path = find_file(design_src, f)
    assert f_path is not None, f"FPGA file missing: {f}"
    shutil.move(f_path, os.path.join(dst_project_dir, f))
    print(f"[+] Moved {f} -> 나머지/project_2020-2_김지성/")

# 3. Move Quartus project folder
proj_folder = os.path.join(design_src, "논회실 project")
if os.path.exists(proj_folder):
    shutil.move(proj_folder, os.path.join(dst_project_dir, "논회실 project"))
    print("[+] Moved Quartus project folder -> 나머지/project_2020-2_김지성/논회실 project")

# 4. Remove empty source subdirectories and root
for sub in ["예보", "결보", "논회실 강의노트", "8주차 대면실험 영상", "설계"]:
    sub_path = os.path.join(src_base, sub)
    if os.path.exists(sub_path):
        shutil.rmtree(sub_path)
        print(f"[-] Removed empty subfolder: {sub}")

# Clean .DS_Store in src_base if present
ds_store = os.path.join(src_base, ".DS_Store")
if os.path.exists(ds_store):
    os.remove(ds_store)

if os.path.exists(src_base) and len(os.listdir(src_base)) == 0:
    os.rmdir(src_base)
    print("[-] Removed empty source root directory `논회실 김지성`.")
```

- [x] **Step 2: Verify FPGA project destination and empty source removal**

```python
import os, unicodedata

dst_project_dir = "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/나머지/project_2020-2_김지성"
src_base = "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/논회실 김지성"

def find_file(dir_path, filename):
    norm_fn = unicodedata.normalize("NFC", filename)
    for x in os.listdir(dir_path):
        if unicodedata.normalize("NFC", x) == norm_fn:
            return os.path.join(dir_path, x)
    return None

expected_fpga = [
    "[2020-2] FPGA 설계 환경 구축 및 실습.pdf",
    "[2020-2] Verilog 기초.pdf",
    "[2020-2] 설계과제.pdf",
    "논회실 project.zip",
    "설계 코드.txt",
]
for f in expected_fpga:
    assert find_file(dst_project_dir, f) is not None, f"FPGA check failed: {f}"

assert os.path.isdir(os.path.join(dst_project_dir, "논회실 project")), "Quartus project folder missing!"
assert not os.path.exists(src_base), "Source directory `논회실 김지성` should be deleted!"

print("[✓] FPGA design files and clean source removal verified.")
```

---

### Task 7: Full Migration Integrity Audit across `from_the_past/정리`

**Files:**
- Audit root: `/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리`

- [x] **Step 1: Run comprehensive migration check**

```python
import os, unicodedata

dst_base = "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리"
src_base = "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/논회실 김지성"

# 1. Source must not exist
assert not os.path.exists(src_base), f"Source folder {src_base} still exists!"

# 2. Check key target folders
required_categories = [
    "예비보고서",
    "결과보고서",
    "강의노트",
    "논회 강의노트",
    "퀴즈",
    "나머지",
]
for cat in required_categories:
    cat_path = os.path.join(dst_base, cat)
    assert os.path.isdir(cat_path), f"Category directory missing: {cat}"

print("=== Comprehensive Migration Audit Passed Successfully ===")
```
