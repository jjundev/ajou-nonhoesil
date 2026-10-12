# Task10 final regression and evidence

Scope: final tests/evidence and controller-authorized source-build contract corrections; no published document regeneration or explanation content edits. Controller spec change remains unstaged. Whole-branch independent review belongs to controller after this task gate.

## Corrections

- Controller authorized source04/05 manifest contract completion after real build failures: four explanation_checks remain allnot_run, canonical fragment paths point to all12/19existing included manuscripts. JSON structural comparison after removing only these added fields equals HEAD exactly. Published manifests and documents unchanged. Navigation current-pack discovery now enumerates six canonical folders with existing-file assertions.
- Original failingcases corrected:4 passed; new source05 fullbuild test first failed for preexisting archived import evidence omission, then missing authoring guide; isolated fixture now materializes exact published evidence and guide, modeling existing import-bank preparation. Checksum guards remain enabled. Actual fullbuild generates allfourHTML/fourMD,19recallsections and check_pack==[]. Final narrow test1passed5.98s.

- Browser v1 pages fixture retained; generated v2 tests use setup_v2. Published article and no-JS coverage expanded to all six packs. Current summary uses the single visible `.sum:not([hidden])` because the actual template moves every authored sum into the right panel. Its text is compared with the matching authored article summary, not merely checked nonempty.
- Added recall equation/table HTML-card and Markdown regression; existing published section coverage now includes recall.
- Windows motivation snapshot uses as_posix, matching generated canonical paths. Experiment06 expected work-table IDs were checked in actual published payload: q-rs-latch, q-dff-table, q-jkff-short, q-p-76-trace.
- Focused run found backup directory discovery regression: 1 failed,124 passed in273.89s. Active published test now enumerates exactly six canonical folders and asserts all twelve question/review HTMLs exist; saved backups are outside current-pack discovery. Corrected work-table suite:20 passed in5.43s.
- Exact netlist -text rule added without content/hash changes; git check-attr text is unset. Committed/current SHA256=333048b95d08190aafbc871d2bd0cdc3c98c8ed6edf58566b1f50f61b2ca857f. git diff --numstat source returned no content diff; status-only M remains from checkout/index stat and is preserved for controller cache refresh, without staging source.
- Review8: actual browser-05 JSON has76 cases,19 no-JS articles,57 visible recall/solve/verify blocks. Historical48/12 console message was inaccurate; final totals derive from JSON. Harness print now derives counts if reused; historical output is not rewritten.
- Review9: calculation-06 adds actual eight J,K,Q→Qnext and four T,Q→Qnext tuples plus expected/current source digests. Original pass labels/path list retained as historical evidence.

## Final preservation and sources

Fresh task-10-audit.py also directly validates/loads original source04/05 v2 manuscripts (12/19) independently of imported-bank fixture. It checks check_pack for six packs, version2, seven unchanged metadata groups, every baseline non-explanation SHA, no unexpected additions, all source SHAs, exact HEAD/current netlist bytes, matching backups, all86 author/published fragment bytes, and all six old sections versus baseline backups.

| Experiment | Included | Preserved non-explanation files | Source digest entries | Baseline-matching backup |
|---|---:|---:|---:|---|
| 01 | 12 | 170 | 11 | 복습노트/실험01.backup-a390ed552fcf |
| 02 | 14 | 184 | 12 | 복습노트/실험02.backup-34107408ed7b |
| 03 | 15 | 162 | 10 | 복습노트/실험03.backup-88dfe79d5eb4 |
| 04 | 12 | 166 | 13 | 복습노트/실험04.backup-6d0f6ed1cc30 |
| 05 | 19 | 172 | 19 | 복습노트/실험05.backup-f026b24748e2 |
| 06 | 14 | 204 | 14 | 복습노트/실험06.backup-d015c7a4243a |

Output: `6 packs, 86 explanations, all non-explanation files preserved`; original-six-section counts12/14/15/12/19/14. Machine detail: output/validation/problem-recall/final-audit.json.

## Content/source evidence scope

Read the per-experiment verification records and existing computation/source/browser evidence. Recompared actual risky recall text with stored source images: exp02 source-02/00.png confirms input ramp but output request and1.5/3.5V boundaries; exp03 manual p7 shows D and Bo separate from input Bi; exp04 v2-3.png explicitly gives active-low nOE and High-Z; exp05 source-05/02-2.png says74HC143 and A0/A1/A2/GS/EO roles while manual p10 labels74HC148 and active-low inputs/outputs; exp06 manual-11.png specifies Falling Edge and active-low asynchronous SET/RESET priority. Existing conflict/unresolved warnings and all old solve/verify content are structurally unchanged. These targeted fresh readings plus retained per-pack reviews do not claim a fresh visual rereading of every source page.

All86 authored/published fragments and all86 old six sections compared, not just record-row presence. Existing content records cover all86; scientific review evidence is the per-pack records/computations and independent task reviews reported by controller. No new content approval flags were written.

## Browser evidence

Existing actual browser JSON case totals:48/56/60/48/76/56=344 article/condition visits. Experiment06 results derive56 from four14-ID lists. Existing screenshots/source renderings are reused as historical evidence. New final pytest browser regressions visit all86 published articles at375/1280×light/dark plus generatedv2 fixture, and no-JS checks all six packs; Final required related suite:538 passed,2593 deselected in310.25s, exit0; all final browser cases included. This is fresh DOM/browser regression, not a fresh visual screenshot-review assertion.

## Baseline diagnosis

Controller baseline had17 failed,448 passed,2593 deselected. Nine stage failures were Windows canonical-path fixture failures corrected inTask2; six motivation failures were the snapshot path issue corrected here; work-table experiment06 expectation/discovery corrected here; original workbook-browser timeout rechecked unchanged:4 passed,5 deselected in13.17s (baseline-browser-recheck.txt). No timeout policy/assertion suppression added.

## Commands and observed output

- `python .superpowers/sdd/2026-10-12-logic-lab-problem-recall/task-10-audit.py`: initial standalone import failed (repo path absent); fixed script sys.path to repo root; subsequent audit passed.
- `python -m pytest tests/test_review_pack_explanation_browser.py tests/test_review_pack_explanation_render.py tests/test_review_pack_motivation_refresh.py tests/test_review_pack_work_table.py -n0 -q`:124 passed,1 failed; backup-discovery cause and correction above.
- `python -m pytest tests/test_review_pack_work_table.py -n0 -q`:20 passed in5.43s.
- `python -m pytest tests/test_review_pack_explanation_render.py tests/test_review_pack_explanation_published.py -n0 -q`:32 passed in4.83s.
- Full requested initial related suite output retained in task-10-related-initial.txt; corrected final output retained in task-10-related-tests.txt. Original run:4 failed,533 passed,2593 deselected in343.13s. Failures were navigation backup-folder discovery, earlier-collected work-table backupglob, and two viewport cases rejected before browser launch because source04 v2 manifest lacked required fragment/check metadata. Both source04 and05 validate_manifest also revealed incomplete activation. Corrected final run:538 passed,2593 deselected in310.25s (0:05:10), exit0.

Dedicated skill: `.claude/skills/logic-lab-problem-explain/SKILL.md`; existing review-pack skill remains the full four-HTML/four-MD workflow entry.

## Final explanation links

| Experiment | HTML | Markdown |
|---|---|---|
| 01 | [HTML](C:/Users/Hyunjun/.codex/worktrees/logic-lab-problem-recall/논회실/복습노트/실험01/실험01_문제설명.html) | [MD](C:/Users/Hyunjun/.codex/worktrees/logic-lab-problem-recall/논회실/복습노트/실험01/실험01_문제설명.md) |
| 02 | [HTML](C:/Users/Hyunjun/.codex/worktrees/logic-lab-problem-recall/논회실/복습노트/실험02/실험02_문제설명.html) | [MD](C:/Users/Hyunjun/.codex/worktrees/logic-lab-problem-recall/논회실/복습노트/실험02/실험02_문제설명.md) |
| 03 | [HTML](C:/Users/Hyunjun/.codex/worktrees/logic-lab-problem-recall/논회실/복습노트/실험03/실험03_문제설명.html) | [MD](C:/Users/Hyunjun/.codex/worktrees/logic-lab-problem-recall/논회실/복습노트/실험03/실험03_문제설명.md) |
| 04 | [HTML](C:/Users/Hyunjun/.codex/worktrees/logic-lab-problem-recall/논회실/복습노트/실험04/실험04_문제설명.html) | [MD](C:/Users/Hyunjun/.codex/worktrees/logic-lab-problem-recall/논회실/복습노트/실험04/실험04_문제설명.md) |
| 05 | [HTML](C:/Users/Hyunjun/.codex/worktrees/logic-lab-problem-recall/논회실/복습노트/실험05/실험05_문제설명.html) | [MD](C:/Users/Hyunjun/.codex/worktrees/logic-lab-problem-recall/논회실/복습노트/실험05/실험05_문제설명.md) |
| 06 | [HTML](C:/Users/Hyunjun/.codex/worktrees/logic-lab-problem-recall/논회실/복습노트/실험06/실험06_문제설명.html) | [MD](C:/Users/Hyunjun/.codex/worktrees/logic-lab-problem-recall/논회실/복습노트/실험06/실험06_문제설명.md) |

## Limitations and self-review

Known disputed/unresolved states remain;74HC143 identity is explicitly unresolved and GS/EO detail is not falsely sourced to the provided148 function table. No held/duplicate/other_experiment content promoted. No unrelated hardware/video/report suite run. No fresh all-page visual review claimed. No reviewer spawned; controller whole-branch review pending. All exact authorized test/audit/report/attribute/source-manifest files are included in the task commit; controller spec and other untracked historical artifacts remain untouched.

Self-review: active-summary selector matches template relocation, fixture remains v1, all six active folder coverage preserved, source checks enabled, exact netlist bytes preserved, final facts derived from actual JSON/output, failed runs disclosed.

## Final task gate

`python -m pytest tests -k review_pack -n 0 -q`:538 passed,2593 deselected in310.25s (0:05:10), exit0. `git diff --check`:exit0. Task10 gate passes; controller task/whole-branch independent reviews remain pending. No further broad rerun needed absent new changes or review concerns.

Raw pytest traceback trailing whitespace was trimmed for git diff --check; every output line, failure and count remains. First cached diff check detected those formatting-only spaces and harness EOF blank; corrected before commit.

## Retained complete initial related output

```text
........................................................................ [ 13%]
........................................................................ [ 26%]
........................................................................ [ 40%]
........................................................................ [ 53%]
.................................................F...................... [ 67%]
........................................................................ [ 80%]
.....................................F......FF.......................... [ 93%]
.................................                                        [100%]
================================== FAILURES ===================================
______________ test_all_published_notes_have_separate_navigation ______________

    def test_all_published_notes_have_separate_navigation():
        from scripts.lab.review_pack.html2md import Parser
        from scripts.lab.review_pack.navigation import check_navigation
        for folder in sorted(PACKS.glob('실험*')):
            path = folder/(folder.name+'_실험설명.html')
>           parser = Parser(); parser.feed(path.read_text())
                                           ^^^^^^^^^^^^^^^^

tests\test_review_pack_navigation_upgrade.py:97:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
..\..\..\..\AppData\Local\Programs\Python\Python314\Lib\pathlib\__init__.py:787: in read_text
    with self.open(mode='r', encoding=encoding, errors=errors, newline=newline) as f:
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

self = WindowsPath('복습노트/실험01.backup-a390ed552fcf/실험01.backup-a390ed552fcf_실험설명.html')
mode = 'r', buffering = -1, encoding = 'locale', errors = None, newline = None

    def open(self, mode='r', buffering=-1, encoding=None,
             errors=None, newline=None):
        """
        Open the file pointed to by this path and return a file object, as
        the built-in open() function does.
        """
        if "b" not in mode:
            encoding = io.text_encoding(encoding)
>       return io.open(self, mode, buffering, encoding, errors, newline)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       FileNotFoundError: [Errno 2] No such file or directory: '복습노트\\실험01.backup-a390ed552fcf\\실험01.backup-a390ed552fcf_실험설명.html'

..\..\..\..\AppData\Local\Programs\Python\Python314\Lib\pathlib\__init__.py:771: FileNotFoundError
_________ test_published_payloads_obey_the_rule_and_match_the_source __________

    def test_published_payloads_obey_the_rule_and_match_the_source():
        from scripts.lab.review_pack.workbook_render import read_workbook_payload
        # Publish backups preserve earlier packs but are not current published folders.
        packs = [Path('복습노트')/f'실험{n:02d}'/f'실험{n:02d}_{kind}.html'
                 for n in range(1,7) for kind in ('기출문제','기출풀이')]
        assert all(path.is_file() for path in packs)
        for path in packs:
            data = read_workbook_payload(path)
            marked = set()
            for p in data['problems']:
                for key in FIELDS:
>                   check_work_tables(p['html'][key], p['id'])
E                   AssertionError: 복습노트\실험01.backup-a390ed552fcf\실험01_기출문제.html: 표지 달린 문항이 기대와 다르다
E                   assert {'q-tt3-4row'..., 'q-xor2-tt'} == set()
E
E                     Extra items in the left set:
E                     'q-tt3-4row'
E                     'q-xor2-tt'
E                     'q-tt3-8row'
E                     Use -v to get more diff

tests\test_review_pack_work_table.py:120: AssertionError
_________ test_real_workbook_decode_ready_and_no_overflow[viewport0] __________

tmp_path = WindowsPath('C:/Users/Hyunjun/AppData/Local/Temp/pytest-of-Hyunjun/pytest-482/test_real_workbook_decode_read0')
viewport = {'width': 1280, 'height': 900}

    @pytest.mark.parametrize('viewport',[{'width':1280,'height':900},{'width':375,'height':812}])
    def test_real_workbook_decode_ready_and_no_overflow(tmp_path,viewport):
        pw = pytest.importorskip('playwright.sync_api')
        run = Path('docs/learning-pack-source/실험04')
        m = json.loads((run/'manifest.json').read_text(encoding='utf-8'))
>       paths = assemble(m,run,tmp_path/'stage',Path('.claude/skills/logic-lab-review-pack/assets'))
                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

tests\test_review_pack_workbook_browser.py:12:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

manifest = {'schema_version': 1, 'experiment': 4, 'title': 'Multiplexer & Demultiplexer — 경로를 고르는 회로를 배워요', 'edition_status': 'current', ...}
run = WindowsPath('docs/learning-pack-source/실험04')
out = WindowsPath('C:/Users/Hyunjun/AppData/Local/Temp/pytest-of-Hyunjun/pytest-482/test_real_workbook_decode_read0/stage')
assets = WindowsPath('.claude/skills/logic-lab-review-pack/assets')

    def assemble(manifest,run,out,assets):
        errors=validate_manifest(manifest)
>       if errors: raise ValueError('\n'.join(errors))
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       ValueError: invalid explanation check: source_visual
E       invalid explanation check: content
E       invalid explanation check: independent
E       invalid explanation check: browser
E       q-mux2: missing/canonical explanation_fragment required
E       q-mux4: missing/canonical explanation_fragment required
E       q-demux2: missing/canonical explanation_fragment required
E       q-design4: missing/canonical explanation_fragment required
E       q-decoder: missing/canonical explanation_fragment required
E       q-tri: missing/canonical explanation_fragment required
E       q-muxdef: missing/canonical explanation_fragment required
E       q-demuxdef: missing/canonical explanation_fragment required
E       q-difference: missing/canonical explanation_fragment required
E       q-demux4: missing/canonical explanation_fragment required
E       q-mux2-graded: missing/canonical explanation_fragment required
E       q-active-general: missing/canonical explanation_fragment required

scripts\lab\review_pack\render.py:26: ValueError
_________ test_real_workbook_decode_ready_and_no_overflow[viewport1] __________

tmp_path = WindowsPath('C:/Users/Hyunjun/AppData/Local/Temp/pytest-of-Hyunjun/pytest-482/test_real_workbook_decode_read1')
viewport = {'width': 375, 'height': 812}

    @pytest.mark.parametrize('viewport',[{'width':1280,'height':900},{'width':375,'height':812}])
    def test_real_workbook_decode_ready_and_no_overflow(tmp_path,viewport):
        pw = pytest.importorskip('playwright.sync_api')
        run = Path('docs/learning-pack-source/실험04')
        m = json.loads((run/'manifest.json').read_text(encoding='utf-8'))
>       paths = assemble(m,run,tmp_path/'stage',Path('.claude/skills/logic-lab-review-pack/assets'))
                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

tests\test_review_pack_workbook_browser.py:12:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

manifest = {'schema_version': 1, 'experiment': 4, 'title': 'Multiplexer & Demultiplexer — 경로를 고르는 회로를 배워요', 'edition_status': 'current', ...}
run = WindowsPath('docs/learning-pack-source/실험04')
out = WindowsPath('C:/Users/Hyunjun/AppData/Local/Temp/pytest-of-Hyunjun/pytest-482/test_real_workbook_decode_read1/stage')
assets = WindowsPath('.claude/skills/logic-lab-review-pack/assets')

    def assemble(manifest,run,out,assets):
        errors=validate_manifest(manifest)
>       if errors: raise ValueError('\n'.join(errors))
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       ValueError: invalid explanation check: source_visual
E       invalid explanation check: content
E       invalid explanation check: independent
E       invalid explanation check: browser
E       q-mux2: missing/canonical explanation_fragment required
E       q-mux4: missing/canonical explanation_fragment required
E       q-demux2: missing/canonical explanation_fragment required
E       q-design4: missing/canonical explanation_fragment required
E       q-decoder: missing/canonical explanation_fragment required
E       q-tri: missing/canonical explanation_fragment required
E       q-muxdef: missing/canonical explanation_fragment required
E       q-demuxdef: missing/canonical explanation_fragment required
E       q-difference: missing/canonical explanation_fragment required
E       q-demux4: missing/canonical explanation_fragment required
E       q-mux2-graded: missing/canonical explanation_fragment required
E       q-active-general: missing/canonical explanation_fragment required

scripts\lab\review_pack\render.py:26: ValueError
=========================== short test summary info ===========================
FAILED tests/test_review_pack_navigation_upgrade.py::test_all_published_notes_have_separate_navigation
FAILED tests/test_review_pack_work_table.py::test_published_payloads_obey_the_rule_and_match_the_source
FAILED tests/test_review_pack_workbook_browser.py::test_real_workbook_decode_ready_and_no_overflow[viewport0]
FAILED tests/test_review_pack_workbook_browser.py::test_real_workbook_decode_ready_and_no_overflow[viewport1]
4 failed, 533 passed, 2593 deselected in 343.13s (0:05:43)
```

## Retained complete final related output

```text
........................................................................ [ 13%]
........................................................................ [ 26%]
........................................................................ [ 40%]
........................................................................ [ 53%]
........................................................................ [ 66%]
........................................................................ [ 80%]
........................................................................ [ 93%]
..................................                                       [100%]
538 passed, 2593 deselected in 310.25s (0:05:10)
```

## Retained final audit output

```text
6 packs, 86 explanations, all non-explanation files preserved
[('01', 170, 11, ['복습노트/실험01.backup-a390ed552fcf']), ('02', 184, 12, ['복습노트/실험02.backup-34107408ed7b']), ('03', 162, 10, ['복습노트/실험03.backup-88dfe79d5eb4']), ('04', 166, 13, ['복습노트/실험04.backup-6d0f6ed1cc30']), ('05', 172, 19, ['복습노트/실험05.backup-f026b24748e2']), ('06', 204, 14, ['복습노트/실험06.backup-d015c7a4243a'])]
netlist committed/current SHA: 333048b95d08190aafbc871d2bd0cdc3c98c8ed6edf58566b1f50f61b2ca857f
86 authored/published fragments exact; original six sections identical: [12, 14, 15, 12, 19, 14]
Original source04/05 manifest and v2 fragments validate/load: [{'experiment': 4, 'validation': 'pass', 'loaded': 12, 'checks': {'source_visual': 'not_run', 'content': 'not_run', 'independent': 'not_run', 'browser': 'not_run'}}, {'experiment': 5, 'validation': 'pass', 'loaded': 19, 'checks': {'source_visual': 'not_run', 'content': 'not_run', 'independent': 'not_run', 'browser': 'not_run'}}]
```
