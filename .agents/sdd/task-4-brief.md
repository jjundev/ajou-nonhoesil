### Task 4: Local Installation and Live Verification

**Files:**
- Modify: `~/.opencli/clis/ajou-bb/*` (via atomic `npm run install:local`)
- Modify: `/Users/hyunjun_macbook_pro/.gemini/config/skills/ajou-bb/SKILL.md` (document `--announcements` option)

**Interfaces:**
- Consumes: Built adapter files in `adapter/ajou-bb/`
- Produces: Production deployment in `~/.opencli/clis/ajou-bb/` and verified CLI command `opencli ajou-bb download <course> --announcements`

- [x] **Step 1: Run `npm run install:local` and `validate`**

```bash
npm --prefix /Users/hyunjun_macbook_pro/Documents/Private/ajou/tools/ajou-bb-opencli run install:local
npm --prefix /Users/hyunjun_macbook_pro/Documents/Private/ajou/tools/ajou-bb-opencli run validate
```
Expected:
- `Installed 12 adapter file(s) to ~/.opencli/clis/ajou-bb`
- `validate` passes with 0 errors.

- [x] **Step 2: Live end-to-end verification**

Run live query download for `논리회로실험` announcement attachment:
```bash
opencli ajou-bb download "_118697_1" --announcements --out ./강의노트/논리회로실험 -f yaml
```
Expected:
- Successfully discovers and downloads `2026-2_논리회로실험 운영계획 (26.09.01).pdf`
- Status: `downloaded` or `skipped (already exists)`
- File is non-dummy and verified.

- [x] **Step 3: Update `SKILL.md` to document announcement downloads**

Update `/Users/hyunjun_macbook_pro/.gemini/config/skills/ajou-bb/SKILL.md`:
Document `--announcements` option in Command Routing Reference table and Workflow 2.

- [x] **Step 4: Commit documentation updates**

```bash
git add docs/plans/2026-09-03-ajou-bb-announcement-attachments.md
```
