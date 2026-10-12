# Final whole-branch review

Reviewed base `f55658ba59f6ba01a582c817857f12e9492cc6f9` through head `91f0984947899c99802a99f7f86bd8fbcd669408` against the approved design and constraints. This review covered the whole branch, not only Task 10. Implementation review was read-only; this requested report is the only reviewer-authored file. No index, HEAD, branch, or implementation changes were made.

## Strengths

- The skill split has a clear boundary: the dedicated skill owns explanation authoring and review, while the existing pack still invokes it in the same run and retains four HTML/four MD outputs. Selection avoids backup folders and preserves the parent run's selection in full-pack use.
- The engine change is small and consistent across manifest validation, assembly, Markdown collection, stage preparation, checks, and publication. Explicit v1 remains supported; the stage default is v2, and new explanation review states reset to `not_run` without approving new content from previous checks.
- Existing source hash, owned-file, path, user collision, publication review, backup, and rollback protections remain connected. Tests exercise actual assembly/staging/publication behavior, including a v2 publication rename failure and retained user files.
- The new content distinguishes assumptions that learners commonly confuse: active-low versus output value, one-hot versus priority encoding, arithmetic carry/borrow versus Boolean operations, current magnitude in PMOS resistance, input/output voltage bounds, level-sensitive latches versus edge-triggered flip-flops, asynchronous control priority, and unknown initial state. Uncertainty labels and the 74HC143/148 identification limit remain explicit.
- Independently compared current files directly to the Git base, not just to an author-created baseline: all 86 included questions retain their old six sections; `problems`, `sources`, `topics`, and original `checks` are unchanged in all six published manifests; all 86 author/published fragments are byte-identical. Imported experiment 06's `explanations.E` read-only and confirmed all 14 generated strings match its authored fragments.

## Issues

### Critical — none

### Important — fix before merge

1. **[P2] Summary body validation loses hidden/title ancestor context.**
   - Location: `scripts/lab/review_pack/explanation_content.py:68-69`.
   - `_validate_v2` finds any descendant marked `data-summary="recall"`, then runs `_body_text` starting at that descendant. The exclusion state of ancestors below the summary container is therefore lost. A concept paragraph wrapped in `<div hidden>`, `<div aria-hidden="true">`, or a heading is accepted as substantive body. The hidden wrapper remains after the template exposes the outer summary, so learners can receive a summary without its required visible concept; heading-only content also bypasses the stated v2 contract.
   - Reproduced read-only with the existing `FRAGMENT_V2` and `SUMMARY` fixture: replace `SUMMARY` by each of `<div hidden>{SUMMARY}</div>`, `<div aria-hidden="true">{SUMMARY}</div>`, and `<h4>{SUMMARY}</h4>`, then call `validate_fragment(..., version=2)`. All three returned successfully.
   - Fix: validate the marked paragraph in its ancestor context, exempting only the intentional outer `div.sum[hidden]`. Preserve exclusions for nested headings, `layer-title`, hidden, and `aria-hidden=true` ancestors. Requiring the documented direct paragraph shape is also viable. Add focused regressions for ancestor exclusion and a positive normal outer-hidden summary case; preserve v1 behavior.

### Minor — recommended

1. **[P3] Explain how to update experiment 06's authoritative Python authoring source.**
   - Location: `.claude/skills/logic-lab-problem-explain/SKILL.md:24`.
   - The new skill directs all existing-pack edits to `docs/learning-pack-source/실험NN/problem-explanations/<id>.html`. Experiment 06 instead has an authoritative `explanations.py`/`recall.py` generator. The current branch has synchronized them correctly, but following the new skill later can change only the HTML and leave the generator stale, allowing a subsequent regeneration to discard the update.
   - Fix: document the experiment 06 exception: edit the Python authoring source, regenerate only the explanation fragments for staging, and verify agreement. Retain the prohibition on running the full `build_run.py` merely to refresh explanations. This is a future-maintenance gap, not a current artifact mismatch.

## Review coverage and evidence

- Read the design/constraints, all engine changes and their surrounding explanation/publish code, all skill changes, test changes, source 04/05 manifest changes, and experiment 06 Python integration. Reviewed all 86 new recall bodies/summaries (experiment 06 through its generator) for plausible scientific and pedagogical errors, and inspected selected full fragments for warning/body relationships.
- Inspected retained computation and preservation evidence, audit implementation/output, and the final related-test transcript: `538 passed, 2593 deselected`. Did not rerun that already-reported whole suite. The new targeted reproduction demonstrates an uncovered input shape despite that passing suite.
- Inspected retained mobile dark trace-summary and desktop light SR/JK screenshots. Used existing per-experiment source/browser records as evidence for the broader matrix; this review does not claim to have independently reopened every original PDF page or repeated the entire browser matrix.
- The direct base-comparison command completed successfully with counts `[12, 14, 15, 12, 19, 14]`, metadata preservation, six-section preservation, 86 source/published byte comparisons, and 14 experiment 06 generator comparisons.
- The controller has separately identified pending packaging cleanup: durable verification evidence currently tracked under `.superpowers/sdd` will move to `output/validation/problem-recall`, with links updated. That forthcoming relocation and any resulting commit are not covered by this head's verdict. The supplied working audit helper already uses `read_bytes` for fragment equality; the read-only comparison above confirms the actual byte claim independently.

## Recommendations

Resolve the summary ancestor-validation defect with focused contract tests, add the experiment 06 authoring exception, and validate relocated evidence links after the controller's packaging cleanup. No content backfill, UI redesign, dependency addition, or fresh whole scientific review is indicated by these findings.

## Declined to judge

None. No behavior was silently set aside as outside the plan/spec. The evidence limits above describe what was actually inspected rather than removing requirements.

## Assessment

**Ready to merge? With fixes.**

The branch substantially fulfills the intended skill separation, v1/v2 integration, and 86-question preservation/backfill contract. Fix the reproducible v2 summary-validation hole before merge; the generator authoring instruction is a small preventative documentation improvement. No critical issue or current source/published content mismatch was found.
