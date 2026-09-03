# Task 4 Report: Local Installation and Live Verification

## 1. Overview

Task 4 performs the local deployment of the updated `ajou-bb` OpenCLI adapter, validates adapter registration, verifies end-to-end live downloading of announcement attachments from Blackboard Ultra, and documents the `--announcements` capability in the `ajou-bb` skill definition.

---

## 2. Execution Details

### Step 1: Local Installation and OpenCLI Validation

1. **Local Adapter Staging & Copy**:
   - Command:
     ```bash
     npm --prefix /Users/hyunjun_macbook_pro/Documents/Private/ajou/tools/ajou-bb-opencli run install:local
     ```
   - Result: Exit code 0
   - Output:
     ```text
     Installed 12 adapter file(s) to /Users/hyunjun_macbook_pro/.opencli/clis/ajou-bb
       common.js
       parser.js
       status.js
       courses.js
       stream.js
       calendar.js
       contents.js
       announcements.js
       assignments.js
       grades.js
       download.js
       analytics.js
     ```

2. **OpenCLI Adapter Registration Validation**:
   - Command:
     ```bash
     npm --prefix /Users/hyunjun_macbook_pro/Documents/Private/ajou/tools/ajou-bb-opencli run validate
     ```
   - Result: Exit code 0
   - Output:
     ```text
     opencli validate: PASS
     Checked 10 command(s)
     Errors: 0  Warnings: 0
     ```

---

### Step 2: Live End-to-End Verification

1. **Initial Download Execution**:
   - Target course: `_118697_1` (`논리회로실험`)
   - Destination: `./강의노트/논리회로실험`
   - Command:
     ```bash
     opencli ajou-bb download "_118697_1" --announcements --out ./강의노트/논리회로실험 -f yaml
     ```
   - Output:
     ```yaml
     - file_name: 2026-2_논리회로실험 운영계획 (26.09.01).pdf
       file_size: 97377
       destination_path: /Users/hyunjun_macbook_pro/Documents/Univ/논회실/강의노트/논리회로실험/2026-2_논리회로실험 운영계획 (26.09.01).pdf
       content_id: announcement__348318_1
       status: downloaded
     ```

2. **Idempotency & Re-run Verification**:
   - Re-ran the same command:
     ```bash
     opencli ajou-bb download "_118697_1" --announcements --out ./강의노트/논리회로실험 -f yaml
     ```
   - Output:
     ```yaml
     - file_name: 2026-2_논리회로실험 운영계획 (26.09.01).pdf
       file_size: 97377
       destination_path: /Users/hyunjun_macbook_pro/Documents/Univ/논회실/강의노트/논리회로실험/2026-2_논리회로실험 운영계획 (26.09.01).pdf
       content_id: announcement__348318_1
       status: skipped (already exists)
     ```

3. **File Integrity Verification**:
   - File location: `/Users/hyunjun_macbook_pro/Documents/Univ/논회실/강의노트/논리회로실험/2026-2_논리회로실험 운영계획 (26.09.01).pdf`
   - Size: 97,377 bytes (matches Blackboard Ultra metadata exactly)
   - Magic byte header: `%PDF-1.6%` (verified authentic binary PDF, not an HTML error or redirect shell)

---

### Step 3: Skill Documentation Update

Updated `/Users/hyunjun_macbook_pro/.gemini/config/skills/ajou-bb/SKILL.md`:
1. **Command Routing Reference Table**:
   - Added `--announcements` to the core options list for `download <과목>`.
   - Updated description to include announcement attachment downloading.
2. **Workflow 2 (Inspect-then-Act) Step 2 (Act - 다운로드 게이트)**:
   - Added:
     ```markdown
     * 공지사항 첨부파일 다운로드: `opencli ajou-bb download "<과목명>" --announcements --out ./강의노트/<과목명>/ -f yaml`
     ```

---

### Step 4: Staging Plan File

- Executed `git add docs/plans/2026-09-03-ajou-bb-announcement-attachments.md` in `/Users/hyunjun_macbook_pro/Documents/Univ/논회실`.

---

## 3. Summary of Results

| Step | Item | Status | Result / Details |
|---|---|---|---|
| Step 1 | `npm run install:local` | PASS | 12 adapter files staged atomically to `~/.opencli/clis/ajou-bb` |
| Step 1 | `npm run validate` | PASS | 10 commands checked, 0 errors, 0 warnings |
| Step 2 | Live Announcement Download | PASS | `2026-2_논리회로실험 운영계획 (26.09.01).pdf` (97,377 bytes) downloaded |
| Step 2 | Idempotency | PASS | Subsequent execution returned `skipped (already exists)` |
| Step 2 | Binary Integrity | PASS | Verified `%PDF-1.6%` magic header |
| Step 3 | SKILL.md update | PASS | Routing table and Workflow 2 updated |
| Step 4 | Git staging | PASS | `docs/plans/2026-09-03-ajou-bb-announcement-attachments.md` staged |
