# SDD ledger — plan: docs/superpowers/plans/2026-10-01-hand-diagram-crop.md
Pre-flight: Task 1 load_crop_plan/crop_box/pixel_box matches Task 2. Task 3 uses public CLI only.
Ruling: Implement in native isolated worktree; preserve original workspace changes. No commits/push per approved plan.
Ruling: Use this durable validation ledger rather than commit-driven SDD helpers because approved plan excludes commits.

Task 1: complete; 5 geometry/plan tests passed.
Task 2: code and skill updated; fresh validation pending.
Task 2: complete; 143 hand-related tests passed after review fixes.
Review: P1 subset filename overwrite and P2 multi-experiment report loss reproduced RED then GREEN.
Ruling: resolve names from the complete source PDF before selecting pages, preserving full/subset identity.
Full suite: 1607 tests, 1 failure, 5 skipped. test_lab_config.TestManualCandidates.test_파일_이름은_0_을_채우지_않는다 also fails on untouched primary checkout (103-test config run).
Fresh round01: baseline lower edge loss fixed; independent comparison running.
Ambiguity round01: FAIL; agent missed identical synthetic question mark on page 2. Preserve outputs and refine per-page inventory.
Fresh round02: both actual pages saved; manifest fixed. ambiguity round02: both pages pending, no final PNG, expected behavior PASS.
Delivery: original project code/skill/tests updated only after target files verified unchanged from worktree base. Primary 143 tests PASS.
Ruling: synthetic pending test requires no real user decision; reaching candidates/question is its passing condition.
Ruling: integration tests isolated into tests/test_hand_crop_export.py instead of growing round8-dependent test class.
Task 3: complete; round02 independent image comparison PASS for both actual pages, ambiguity round02 PASS. Manifest 17 hashes unchanged. Main workspace 143 related tests PASS; original unrelated config failure documented.
