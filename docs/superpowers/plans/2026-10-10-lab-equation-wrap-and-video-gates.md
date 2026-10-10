# 논리식 줄바꿈·넘침 게이트·풀이영상 입력 게이트 보강 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 실험05 해설지의 어긋난 논리식 줄바꿈을 고치고 같은 경로의 잘림·넘침을 게이트로 막은 뒤, 풀이영상 스킬의 미해결 7건(라벨·종료 상태, 표 행 순서, SVG 동결, 왼쪽 패널 연출, 오류 문구, 테스트 빈틈, git 범위)을 닫는다.

**Architecture:** 복습팩 템플릿 스냅샷은 해시 고정이므로 `scripts/lab/review_pack/workbook_render.py` 의 패치로만 고친다(렌더러 → 재렌더 순). 풀이영상 스킬은 `sources.py`·`video.py`·`annotations.py`·`writing_camera.py` 를 각각 한 가지씩 고치고, 실제 팩과 합성 팩 양쪽으로 테스트한다.

**Tech Stack:** Python 3(.venv — PyMuPDF, unittest/pytest), playwright + Chrome, KaTeX(템플릿 내장), git.

**Spec:** 이 문서의 「확정 결정」 절. 2026-10-10 대화(`/grill-yourself 수정 방향을 정하자`)에서 확정했다. 근거 조사는 같은 대화의 "미해결 8건" 표.

## Global Constraints

- 템플릿 스냅샷 `.claude/skills/logic-lab-review-pack/assets/workbook/{problem,answer}.html` 은 `provenance.json` 의 sha256 에 고정돼 있다. **직접 수정하지 않는다.** 고침은 `workbook_render.py` 의 `LOCAL_PATCHES` 로만 하고, anchor 가 정확히 한 번이 아니면 `apply_local_patches` 가 `ValueError` 를 낸다(이 동작을 유지한다).
- `splitRelations`·`breakEquations` 구간은 두 템플릿에서 바이트까지 같다(2026-10-10 확인). 패치는 두 템플릿에 모두 맞아야 한다.
- 작업은 git worktree 에서 한다. 공유 작업 트리(main)에 다른 세션의 미커밋 수정이 있다: `.claude/skills/logic-lab-review-pack/SKILL.md`, `.../assets/{note,review}-template.html`, `.../references/verification.md`, `scripts/lab/review_pack/{render,checks}.py`, `scripts/lab/standalone_note.py`, `.claude/skills/export-standalone-note/SKILL.md`, `tests/test_standalone_note.py`, `복습노트/실험01/실험01_실험설명.html`. **이 파일들은 건드리지 않는다.** 복습팩 문서는 `references/workbook.md` 에 쓴다.
- 풀이영상 스킬 파일을 바꾸면 `upstream.json.local_changes` 에 이유 한 줄을 적는다(없으면 `test_upstream_manifest_accounts_for_every_file` 가 깨진다). 이미 항목이 있으면 이유 문구를 갱신한다.
- 유료 호출 금지: `prepare`·`extract`·`check` 만 쓴다. `tts` 는 Task 11 에서 사용자 승인 뒤에만.
- 테스트 명령(저장소 루트, worktree 의 `.venv` 는 main 의 `.venv` 심볼릭 링크):
  - 복습팩: `.venv/bin/python -m pytest tests/test_review_pack_workbook_browser.py tests/test_review_pack_workbook_render.py tests/test_workbook_equations.py tests/test_workbook_clip_gate.py tests/test_review_pack_layout.py -q` — **skip 은 통과가 아니다.** playwright·Chrome 이 없어 skip 되면 멈추고 보고한다.
  - 영상 스킬: `.venv/bin/python -m unittest discover -s .claude/skills/logic-lab-solution-video/tests`
- 응답·문서·커밋 메시지는 한국어, 코드 식별자·경로만 원문. 커밋 메시지 끝에 `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.
- 확정 결정에서 **뺀 것**: #10 의 "확대 뷰를 쪽 안으로 클램프". 기존 `test_table_edges_and_infeasible_readability`(tests/test_focus.py)가 "쪽 가장자리 region 도 여백 180px 를 우선한다"고 못박고 있어 클램프하면 기존 계약이 깨진다. 규칙 완화만 한다.

## 확정 결정

| # | 결정 | 값 |
|---|---|---|
| 1 | 줄바꿈 원인 | `splitRelations` 가 쉼표를 보지 않고 모든 최상위 `=` 에서 자름 → 식 목록 `O_0=…,\ O_1=…` 의 꼬리표가 앞 줄에 남음 |
| 2 | 줄바꿈 수정 | 최상위 쉼표로 식 목록을 먼저 나눈 뒤 식마다 `aligned` 행. 조각마다 최상위 `=` 가 있을 때만 나눔 |
| 3 | 영향 | 실험05 해설지 7쪽(기출4·7·12, 예상문제8, 출처 미확인11·14·17). 실험01~04 워크북 md 에 같은 패턴 없음 |
| 4 | 넘침 게이트 | 맞춤이 끝난 뒤 한 번 훑어 잘린 식·넘친 표·넘친 풀이 단계를 `data-overflow` 로 알림 |
| 5 | 재렌더 범위 | ~~실험05 만~~ → **실험01~05 HTML 전부**. `test_review_pack_layout.py::test_published_pack_passes_checks` 가 게시 HTML 을 렌더 결과와 바이트 비교하므로 템플릿 패치가 바뀌면 식이 안 바뀐 실험01~04 도 HTML 을 다시 써야 한다(2026-10-10 Task 1 리뷰에서 확인). 01~04 는 HTML 만 바뀌고 md·PDF 는 바뀌지 않는다(격리 사본에서 확인). |
| 6 | 표 행 순서 | `find_tables` 행렬 비교를 기존 글자 multiset 위에 추가 |
| 7 | 탈락 항목 | `label` 부여. 전부 탈락이면 `status:'failed'`·종료 코드 1 |
| 8 | SVG | `figure_svg_refs` 로 동결, 없으면 `figure_svg_missing` 경고 |
| 9 | 왼쪽 패널 | "region must be above work_bbox" 제거, "overlaps work_bbox" 만 둠 |
| 10 | layers git | `layers/` 의 svg·png 무시·추적 해제, json 만 추적 |
| 11 | 기출12 영상 | PDF 수정 뒤 재제작. 유료 호출이 필요해 보이면 실행 전 보고 |

## Review Focus

1. **함수 인자 쉼표** `f(a,b)=…` — 쪼개지지 않고 기존처럼 한 식으로 남아야 한다(Task 1).
2. **목록 중 한 조각만 관계 기호가 없는 식** — 통째로 두고 기존 동작을 유지해야 한다(Task 1).
3. **실제 팩 5개에서 넘침 훑기 오탐** — 게시본 5개 모두 `data-overflow` 가 비어야 한다. 걸리면 조용히 완화하지 말고 쪽 id 와 함께 보고한다(Task 2).
4. **표 감지 오탐·표 없는 쪽** — 짝이 없으면 건너뛰고, 실제 팩 전 문항이 통과해야 한다(Task 6).
5. **범위 선택(`실험04-05`)에서 탈락 항목 라벨** — `실험04 기출1` 처럼 실험 접두어가 붙어야 한다(Task 5).

---

### Task 0: 격리 작업 트리

**Files:** 없음(환경 준비)

- [ ] **Step 1: worktree 만들기**

```bash
git worktree add .claude/worktrees/lab-equation-gates -b fix/lab-equation-gates main
ln -s ../../../.venv .claude/worktrees/lab-equation-gates/.venv
```

Expected: `git worktree list` 에 새 경로가 보인다. 이후 모든 작업과 명령은 이 경로에서 한다.

- [ ] **Step 2: 기준선 확인**

Run: `.venv/bin/python -m unittest discover -s .claude/skills/logic-lab-solution-video/tests 2>&1 | tail -3`
Expected: `OK` (브라우저 테스트가 환경 때문에 실패하면 기준선으로 기록해 두고 이후 비교한다).

---

### Task 1: 논리식 식 목록 줄바꿈 (렌더러 패치)

**Files:**
- Modify: `scripts/lab/review_pack/workbook_render.py` (`LOCAL_PATCHES` 에 항목 추가)
- Create: `tests/test_workbook_equations.py`
- Modify: `.claude/skills/logic-lab-review-pack/references/workbook.md` (식 줄바꿈 규칙 한 문단)

**Interfaces:**
- Produces: 템플릿 JS 전역 `splitEquationList(tex: string): string[] | null`. 최상위(`{}`·`\left…\right`·`()`·`[]` 깊이 0) 쉼표에서 나누고, 다음 조각 머리의 `\ `·`\quad`·`\qquad`·`\,`·공백을 지운다. 조각이 2개 이상이고 **모든 조각에** `splitRelations(조각)` 이 있을 때만 배열을 돌려주고 아니면 `null`.
- Produces: 바뀐 `equationTex(tex, parts, prefix)` — `splitEquationList(tex)` 가 배열이면 조각마다 `splitRelations` 결과로 행을 만든다(첫 행 `lhs &= rhs`, 같은 조각의 이어지는 관계는 `&= rhs`), 전체를 한 `\begin{aligned}…\end{aligned}` 로 ` \\ ` 이어 붙인다. `prefix` 는 맨 첫 행 앞에만. 배열이 아니면 기존 동작.
- Produces: 패치 상수 `EQUATION_OLD`, `EQUATION_NEW` (anchor = 스냅샷의 `function equationTex(...) { ... }` 7줄 전체).

- [ ] **Step 1: 실패하는 테스트 작성** — `tests/test_workbook_equations.py`

실제 식 세 개를 상수로 둔다(모두 `복습노트/실험05/실험05_기출풀이.md` 에서 가져온다).

```python
OUTPUT = r"O_0=\overline{I_1}\,\overline{I_0},\ O_1=\overline{I_1}I_0,\ O_2=I_1\overline{I_0},\ O_3=I_1I_0"   # 기출4
BITS = r"\mathrm{Bit3}=SW5,\ \mathrm{Bit2}=SW1+SW2+SW3+SW4,\ \mathrm{Bit1}=SW0+SW3+SW4,\ \mathrm{Bit0}=SW0+SW2+SW4"  # 기출7
DEMUX = r"Y_0=\overline{S_1}\,\overline{S_0}D,\ Y_1=\overline{S_1}S_0D,\ Y_2=S_1\overline{S_0}D,\ Y_3=S_1S_0D"  # 기출12
```

`tests/test_review_pack_workbook_browser.py::_synthetic_pack` 로 문제 1개짜리 페이지를 렌더하고 `page.goto` 후 `data-ready` 를 기다린 다음 `page.evaluate("h => breakEquations(h)", html)` 로 순수 함수를 호출하는 fixture `breaker` 를 둔다. 테스트 이름과 단언:

- `test_patch_applies_to_both_templates` (브라우저 없음): `problem.html`·`answer.html` 각각 `apply_local_patches(read_text, name)` 결과에 `'splitEquationList'` 가 있다.
- `test_comma_list_becomes_one_aligned_row_per_equation[OUTPUT|BITS|DEMUX]`: 결과가 `\begin{aligned}` 하나이고 `re.findall(r'(\\mathrm\{Bit\d\}|[OY]_\d) &amp;= ', out)` 가 식 순서(`O_0..O_3` / `Bit3..Bit0` / `Y_0..Y_3`)와 같고, `out.count(r' \\ ') == 3`, 최상위 쉼표 없음(`,\ ` 가 aligned 안에 없음).
- `test_function_arguments_are_not_split`: `$$f(a,b)=\overline{x_1}\,\overline{x_2}\,\overline{x_3}\,\overline{x_4}\,\overline{x_5}$$` → 결과에 `f(a,b) &amp;=` 가 있고 `' \\ '` 가 없다.
- `test_list_with_a_relationless_piece_is_kept_whole`: `$$x_1=a+b+c+d+e+f+g+h,\ \text{단,}\ y=z+z+z+z$$` 조각 하나(`\text{단,}`)에 관계 기호가 없으므로 쉼표 분할이 일어나지 않는다(`out.count(r'\begin{aligned}') <= 1` 이고 `\text{단,}` 가 한 행 안에 그대로).
- `test_short_list_stays_inline`: `$O_0=a,\ O_1=b$` (40자 이하) → 입력과 같다.
- `test_single_chain_keeps_old_rows`: `$$A=B+C+D+E+F+G+H+I+J+K=L+M+N+O+P+Q+R+S+T+U$$` → 행 2개, 둘째 행이 `&amp;= ` 로 시작.

- [ ] **Step 2: 실패 확인**

Run: `.venv/bin/python -m pytest tests/test_workbook_equations.py -q`
Expected: `splitEquationList` 가 없어 FAIL (첫 테스트) 및 aligned 행 단언 FAIL.

- [ ] **Step 3: `workbook_render.py` 에 패치 추가**

`EQUATION_OLD` 는 답안 템플릿 `equationTex` 함수 본문과 바이트까지 같게 복사한다(`sed -n '/^function equationTex/,/^}/p' .claude/skills/logic-lab-review-pack/assets/workbook/answer.html`). `EQUATION_NEW` 는 위 Interfaces 의 동작을 JS 로 쓴 `splitEquationList` + 새 `equationTex`. `LOCAL_PATCHES` 끝에 `(EQUATION_OLD, EQUATION_NEW)` 를 더한다. 기존 주석 스타일대로 패치 위에 "왜"(쉼표 목록이 `=` 마다 잘려 꼬리표가 앞 줄에 남던 문제, 2026-10-10 기출4·12)를 적는다.

- [ ] **Step 4: 테스트 통과 확인**

Run: `.venv/bin/python -m pytest tests/test_workbook_equations.py tests/test_review_pack_workbook_render.py -q`
Expected: 모두 PASS (스냅샷 해시·anchor 유일성 테스트 포함).

- [ ] **Step 5: 문서 한 문단** — `references/workbook.md` 의 식 설명 근처에 "여러 식이 쉼표로 이어진 긴 `$$…$$` 는 식마다 한 줄(`aligned`)로 나뉘고, 각 식의 관계 기호는 그 줄 안에서만 이어진다. 조각마다 최상위 `=` 가 있을 때만 나눈다"를 적는다.

- [ ] **Step 6: 커밋**

```bash
git add scripts/lab/review_pack/workbook_render.py tests/test_workbook_equations.py .claude/skills/logic-lab-review-pack/references/workbook.md
git commit -m "fix(복습팩): 쉼표로 이어진 논리식을 식마다 한 줄로 나눈다"
```

---

### Task 2: 잘림·넘침 훑기 게이트

**Files:**
- Modify: `scripts/lab/review_pack/workbook_render.py` (`LOCAL_PATCHES` 에 두 항목)
- Create: `tests/test_workbook_clip_gate.py`
- Modify: `.claude/skills/logic-lab-review-pack/references/workbook.md`

**Interfaces:**
- Produces: 템플릿 JS 전역 `hasClippedContent(page: Element): boolean` — 해당 `.page--problem` 안에서 하나라도 참이면 true.
  - `.katex-display` 의 첫 자식 `getBoundingClientRect().right` 가 그 display 의 `right + 1` 보다 크다(70% 축소 한계 뒤에도 넘침).
  - `.table-wrap` 의 `scrollWidth > clientWidth + 1`.
  - `.sol-flow` 안의 **모든** `.sol-step` 의 `bottom`/`right` 가 flow 의 `bottom + 1`/`right + 1` 보다 크다(기존 `fits()` 는 마지막 단계만 봤다).
- Produces: 패치 anchor 두 개 — `async function main() {` (앞에 helper 삽입), `    document.body.dataset.overflow = overflow.join(',');` (앞에 훑기 삽입: `.page--problem` 마다 이미 `overflow` 에 없고 `hasClippedContent(page)` 이면 `overflow.push(page.id)`). 두 anchor 는 두 템플릿에서 각각 정확히 한 번이다.

- [ ] **Step 1: 실패하는 테스트 작성** — `tests/test_workbook_clip_gate.py`

- `test_unfittable_display_formula_is_reported` (answers 모드 합성 팩): `solution.steps[0].html = '<p>$$' + '+'.join(f'a_{{{i}}}' for i in range(90)) + '$$</p>'` → 렌더 후 `body[data-overflow]` 가 해당 문항 id 를 포함한다.
- `test_every_solution_step_is_checked` (page.evaluate 로 합성 DOM): `.page--problem > .sol-flow(높이 100px) > .sol-step×3` 에서 **첫째** 단계가 flow 밖으로 나가면 `hasClippedContent` 가 true, 셋 모두 안이면 false.
- `test_wide_table_scroll_is_reported`: `.table-wrap` 안 table 폭을 wrap 보다 크게 둔 합성 DOM → true.
- `test_published_packs_report_no_clipped_content[실험01..실험05]` (parametrize): 각 팩의 `실험NN_기출문제.html`·`실험NN_기출풀이.html` 에서 `read_workbook_payload` 로 payload 를 읽고, `render_workbook_html(data, 복습노트/실험NN/자료/assets)` 결과를 `tmp_path` 에 쓰고(`assets/vendor` 는 `_synthetic_pack` 처럼 복사) 열어 `body[data-overflow] == ''` 를 단언한다.

- [ ] **Step 2: 실패 확인**

Run: `.venv/bin/python -m pytest tests/test_workbook_clip_gate.py -q`
Expected: 앞의 세 테스트 FAIL(`hasClippedContent` 미정의). 게시본 5개 테스트는 지금 코드로도 돌 수 있다 — **결과를 기록한다.**

- [ ] **Step 3: 패치 구현** — 위 Interfaces 대로 `workbook_render.py` 에 상수와 `LOCAL_PATCHES` 항목을 더한다. 훑기는 기존 맞춤 루프가 끝난 뒤(`overflow.join` 직전)에만 돌아 맞춤 도중의 일시적 넘침을 보고하지 않는다.

- [ ] **Step 4: 게시본 5개 결과 판정**

Run: `.venv/bin/python -m pytest tests/test_workbook_clip_gate.py -q`
Expected: 모두 PASS. **게시본 테스트가 실패하면 멈춘다** — 걸린 쪽 id 와 어느 검사(식/표/단계)에 걸렸는지를 사용자에게 보고하고, 오탐인지 실제 결함인지 가린 뒤 진행한다. 임계값을 조용히 완화하지 않는다.

- [ ] **Step 5: 문서** — `references/workbook.md` 에 "맞춤이 끝난 뒤 잘린 식·넘친 표·넘친 풀이 단계가 남으면 `data-overflow` 에 해당 쪽 id 가 오른다"를 한 줄 적는다.

- [ ] **Step 6: 커밋**

```bash
git add scripts/lab/review_pack/workbook_render.py tests/test_workbook_clip_gate.py .claude/skills/logic-lab-review-pack/references/workbook.md
git commit -m "feat(복습팩): 맞춤 뒤 잘린 식·넘친 표·넘친 풀이 단계를 data-overflow 로 알린다"
```

---

### Task 3: 실험01~05 재렌더와 영상 스킬의 실제 팩 값 맞추기

**Files:**
- Modify (생성물): `복습노트/실험05/실험05_기출풀이.{html,md,pdf}`, `실험05_기출문제.{html,md,pdf}`; `복습노트/실험01~04/실험NN_기출{문제,풀이}.html` (템플릿 스크립트 변경만 — md·PDF 는 되돌린다)
- Modify: `tests/test_workbook_equations.py` (실제 팩 테스트 추가)
- Modify (필요한 만큼): `.claude/skills/logic-lab-solution-video/tests/*` 의 실제 팩 의존 값

**Interfaces:**
- Consumes: Task 1·2 의 패치된 `render_workbook_html`.

- [ ] **Step 1: 실패하는 테스트 추가** — `test_published_experiment05_has_no_top_level_commas_in_display_math`: `복습노트/실험05/실험05_기출풀이.html` 을 playwright 로 열어 `.katex-display annotation[encoding="application/x-tex"]` 텍스트마다 중괄호 깊이 0 쉼표가 없고, `O_0 &= ` 를 가진 식이 하나 있다.

Run: `.venv/bin/python -m pytest tests/test_workbook_equations.py -k published -q`
Expected: FAIL (게시본이 옛 렌더).

- [ ] **Step 2: 재렌더·PDF 재생성**

```bash
for n in 01 02 03 04 05; do .venv/bin/python -m scripts.lab.review_pack rerender --folder 복습노트/실험$n; done
.venv/bin/python -m scripts.lab.workbook_pdf 실험05
```

Expected: 첫 명령 오류 목록이 비어 있고, 둘째 명령이 `실험05_기출문제.pdf (… 19쪽)`, `실험05_기출풀이.pdf (… 21쪽)` 를 낸다. `실패:` 가 나오면 멈추고 보고한다.

- [ ] **Step 3: 시각 확인** — 기출4·7·12·예상문제8·출처 미확인11·14·17 해설지 쪽을 PNG 로 렌더해(`pymupdf`, 2배) 논리식이 `O_0 = …` / `O_1 = …` 처럼 식마다 한 줄이고 `=` 로 시작하는 고아 줄이 없는지 눈으로 본다.

- [ ] **Step 3b: 실험01~04 는 HTML 만 남긴다** — `git status` 로 실험01~04 에서 HTML 외 변경(md·PDF)이 있으면 `git checkout --` 로 되돌리고, HTML diff 가 `splitEquationList` 추가(Task 2 이후에는 `hasClippedContent` 포함)뿐인지 확인한다. 그 외 변경이 있으면 멈추고 보고한다. 그 뒤 `test_review_pack_layout.py` 가 통과해야 한다.

- [ ] **Step 4: 커밋할 PDF 가려내기** — 각 PDF 를 `git show HEAD:<경로>` 와 비교해 쪽 수와 텍스트 해시가 같으면 `git checkout -- <그 PDF>` 로 되돌린다(타임스탬프만 다른 재생성 PDF 는 커밋하지 않는다). HTML·MD 는 패치된 스크립트 때문에 항상 바뀐다.

- [ ] **Step 5: 영상 스킬 기준선 맞추기**

Run: `.venv/bin/python -m unittest discover -s .claude/skills/logic-lab-solution-video/tests 2>&1 | tail -30`
Expected: PASS. 실제 팩 값(쪽 좌표·글리프 수)에 묶인 테스트만 실패할 수 있다 — 실패마다 새 값이 PDF 변경에서 온 것인지 확인하고 그 값만 고친다. 의미가 다른 실패는 고치지 말고 보고한다. 바꾼 테스트 파일은 `upstream.json.local_changes` 이유를 갱신한다.

- [ ] **Step 6: 커밋**

```bash
git add 복습노트/실험05 tests/test_workbook_equations.py .claude/skills/logic-lab-solution-video
git commit -m "fix(실험05): 식 목록 줄바꿈을 고쳐 문제지·해설지를 다시 렌더한다"
```

---

### Task 4: 합성 팩과 테스트 빈틈 (NFD 파일 이름, 라벨 재계산 성공 경로)

**Files:**
- Modify: `.claude/skills/logic-lab-solution-video/tests/fixtures.py`
- Modify: `.claude/skills/logic-lab-solution-video/tests/test_sources_lab.py`
- Modify: `.claude/skills/logic-lab-solution-video/upstream.json` (두 파일 이유)

**Interfaces:**
- Produces (`tests/fixtures.py`): `synthetic_pack(repo: Path, name: str, problems: list[dict], table: list[list[str]] | None = None, answer_table: list[list[str]] | None = None) -> Path`
  - `problems` 항목은 `dict(id, kind, title)`(kind ∈ `past|predicted|unknown|practice`). `repo/복습노트/<name>/자료/manifest.json`(`{'problems':[{id,kind,title,status:'included'}]}`)과 `<name>_기출문제.pdf`·`<name>_기출풀이.pdf`(A4 가로 841.9×595.3, 문항마다 한 쪽)를 쓴다.
  - 쪽 머리: 배지 `KINDS[kind]+n` 을 (30,40), 제목을 (150,40) 에 `fontname='korea'` 로 쓴다. `table` 이 있으면 문제지 쪽에 (300,200) 기준 칸 폭 60·높이 24 의 격자 표, `answer_table` 이 있으면 해설지 쪽 (34,200) 에 같은 모양으로 그린다(칸 글자는 `fontsize=10`).
  - 문항 순서가 바뀐 manifest 로 같은 함수를 다시 부르면 PDF 도 그 순서로 다시 쓴다.

- [ ] **Step 1: 실패하는 테스트 작성** — `test_sources_lab.py`

```python
def test_nfd_file_names(self):
    # 실험05 를 모든 파일 이름이 NFD 인 사본으로 만든다(폴더 이름만 NFD 이던 기존 테스트의 빈틈).
    # 사본 이름이 실제로 NFD 로 남지 않는 파일시스템이면 self.skipTest.
    # 단언: discover(repo,'실험05',None,[]) 의 문항 ID 순서와 figure_refs 개수·md_snapshot 유무가 원본과 같다.
def test_labels_are_recomputed_when_pack_is_rebuilt(self):
    # synthetic_pack(repo,'실험06',[q-a,q-b]) → labels ['기출1','기출2'], 실패 없음.
    # 순서를 바꿔 synthetic_pack 를 다시 부르면 failures==[] 이고 첫 문항 id 가 q-b 이며,
    # selector '기출1' 로 고르면 q-b 가 나온다(성공 경로).
```

- [ ] **Step 2: 실패 확인**

Run: `.venv/bin/python -m unittest discover -s .claude/skills/logic-lab-solution-video/tests -p test_sources_lab.py -v`
Expected: `synthetic_pack` 미정의로 ERROR. (NFD 테스트는 fixture 없이도 돌지만 새 코드와 함께 확인.)

- [ ] **Step 3: `synthetic_pack` 구현** — 위 Interfaces 대로.

- [ ] **Step 4: 통과 확인**

Run: 같은 명령.
Expected: PASS. `test_nfd_file_names` 가 NFC/NFD 구분 때문에 실패하면 `sources.py` 의 `_norm` 누락이라는 뜻이므로 그 지점을 고치고(테스트가 먼저) 이유를 `upstream.json` 에 적는다.

- [ ] **Step 5: 커밋**

```bash
git add .claude/skills/logic-lab-solution-video
git commit -m "test(solution-video): 합성 팩 fixture 와 NFD 파일 이름·라벨 재계산 성공 경로 테스트"
```

---

### Task 5: 탈락 항목 라벨과 전부 탈락 상태

**Files:**
- Modify: `.claude/skills/logic-lab-solution-video/scripts/solution_video/sources.py` (`discover` 의 `fail`)
- Modify: `.claude/skills/logic-lab-solution-video/scripts/video.py` (`prepare_batch` 실패 항목, `main`)
- Modify: `.claude/skills/logic-lab-solution-video/tests/test_cli.py`
- Modify: `.claude/skills/logic-lab-solution-video/upstream.json`

**Interfaces:**
- Produces: `discover` 의 실패 레코드 키 `label: str | None` (문항 탈락이면 manifest 순서로 센 표시 라벨, 실험 단위 실패면 `None`).
- Produces: `video.summarize_batch(batch: Path) -> dict` = `{'prepared': int, 'failed': int}` (`batch.json` 항목의 `status` 로 센다: `failed` 이외는 prepared).
- Produces: 실패 항목 `{'id','run','filename','status':'failed','reason'}` 에 `label` 추가, `filename = <표시라벨> — 풀이.mp4`(범위 선택이면 `실험04 기출1` 형식, 성공 항목과 같은 규칙). 라벨이 없으면 기존처럼 `<id> — 풀이.mp4`.
- Produces: `prepare` 결과 `{'status','batch','prepared','failed','paid_requests'}`. `prepared == 0 and failed > 0` 이면 `status:'failed'`(종료 코드 1), 아니면 `author-required`.

- [ ] **Step 1: 실패하는 테스트 작성** — `test_cli.py`

- `test_prepare_labels_and_paths` 에 추가: `items['q-demux-from-dec']['label'] == '출처 미확인11'`, `['filename'] == '출처 미확인11 — 풀이.mp4'`.
- `test_prepare_all_failed_experiment` 에 추가: `cli.main(...)` 반환값 `== 1`, 결과 `status == 'failed'`, `prepared == 0`, 모든 항목에 `label` 이 있고, batch 폴더와 `paid_requests == 0` 은 그대로.
- `test_prepare_partial_failure_exits_zero`: `기출4,q-demux-from-dec` 선택(하나 탈락) → 반환값 0, `prepared == 1`, `failed == 1`.
- `test_range_prefix_on_failed_label`: `prepare 실험04-05` 에서 탈락 항목 라벨이 `실험05 출처 미확인11` 처럼 접두어를 가진다(sandbox_repo 에 `defective_pack` 로 실험05 쪽을 결함으로 만들어 쓴다).

- [ ] **Step 2: 실패 확인**

Run: `.venv/bin/python -m unittest discover -s .claude/skills/logic-lab-solution-video/tests -p test_cli.py -v`
Expected: 새 단언 FAIL(`KeyError: 'label'`, 반환값 0).

- [ ] **Step 3: 구현** — `discover` 에서 `labels = {(name, pid): label}` 을 팩을 읽을 때 채우고 `fail()` 이 레코드에 `label` 을 넣는다. `prepare_batch` 의 실패 항목에 `label`·`filename` 을 넣고, `main` 이 `summarize_batch` 로 상태를 정한다. 전부 탈락 결과에는 `reason: 'all problems failed the input gate; see batch.json'` 을 더한다.

- [ ] **Step 4: 통과 확인** — 같은 명령 + `test_sources_lab.py`. Expected: PASS.

- [ ] **Step 5: 커밋**

```bash
git add .claude/skills/logic-lab-solution-video
git commit -m "feat(solution-video): 탈락 항목에 라벨을 남기고 전부 탈락하면 failed 로 끝낸다"
```

---

### Task 6: 표 행·열 순서 대조

**Files:**
- Modify: `.claude/skills/logic-lab-solution-video/scripts/solution_video/sources.py`
- Modify: `.claude/skills/logic-lab-solution-video/tests/test_sources_lab.py`
- Modify: `.claude/skills/logic-lab-solution-video/references/pdf-and-coverage.md` (조건 대조 문장), `upstream.json`

**Interfaces:**
- Produces: `_table_mismatch(problem_ref: dict, answer_ref: dict) -> str | None` — 두 쪽의 `page.find_tables()` 결과를 `extract()` 한 행렬(셀은 NFC 변환 후 공백 제거, `None` → `''`)로 비교한다. 문제지 표마다 해설지에 **같은 (행, 열) 모양**의 표가 있으면 그중 하나와 셀이 한 칸도 다르지 않아야 한다. 모양이 같은 표가 없으면 건너뛴다. 불일치면 `'table <i> row <r>'` 형식의 설명을 돌려주고 일치·건너뜀이면 `None`.
- `validate_pairs` 는 기존 글자 multiset 대조 뒤에 `_table_mismatch` 를 부르고, 값이 있으면 `InputError('table rows differ: ' + problem_id + ' ' + 설명)`.

- [ ] **Step 1: 실패하는 테스트 작성** — `test_sources_lab.py` (Task 4 의 `synthetic_pack` 사용)

- `test_table_row_swap_is_rejected`: `table=[['A','B'],['0','1'],['1','0']]`, `answer_table=[['A','B'],['1','0'],['0','1']]` → `discover(..., failures)` 의 사유에 `table rows differ` 가 있고 문항이 반환되지 않는다.
- `test_identical_tables_pass`: 같은 표 → 실패 없음.
- `test_answer_without_table_is_skipped`: `answer_table=None` 이면 표 때문에 실패하지 않는다(글자 multiset 은 이미 `조건 differ` 로 막으므로 문제지 표 글자를 패널 글자로 옮겨 쓰는 구성으로 만든다).
- `test_real_packs_have_no_table_false_positive`: 실험01~05 를 `failures` 목록과 함께 `discover` 했을 때 어떤 사유에도 `table rows differ` 가 없다.

- [ ] **Step 2: 실패 확인**

Run: `.venv/bin/python -m unittest discover -s .claude/skills/logic-lab-solution-video/tests -p test_sources_lab.py -v`
Expected: 행 바뀜 테스트 FAIL(글자 multiset 은 통과해 버린다).

- [ ] **Step 3: 구현** — 위 Interfaces 대로. `find_tables` 가 예외를 내면 그 쪽은 건너뛴다(검사가 입력 게이트를 새로 막지 않도록).

- [ ] **Step 4: 통과 확인** — 같은 명령. Expected: PASS. 실제 팩 테스트가 실패하면 규칙을 완화하지 말고 어느 문항·표인지 보고한다.

- [ ] **Step 5: 문서 한 문장** — `pdf-and-coverage.md` 의 조건 대조 설명에 "표는 행·열 순서까지 같아야 하며 모양이 같은 해설지 표가 없으면 건너뛴다"를 더한다.

- [ ] **Step 6: 커밋**

```bash
git add .claude/skills/logic-lab-solution-video
git commit -m "feat(solution-video): 조건 대조가 표의 행·열 순서까지 본다"
```

---

### Task 7: 그림 SVG 동결

**Files:**
- Modify: `.claude/skills/logic-lab-solution-video/scripts/solution_video/sources.py` (`discover`, `freeze_sources`)
- Modify: `.claude/skills/logic-lab-solution-video/scripts/solution_video/contracts.py` (`PagePair`)
- Modify: `.claude/skills/logic-lab-solution-video/scripts/video.py` (런 폴더로 복사)
- Modify: `.claude/skills/logic-lab-solution-video/tests/test_sources_lab.py`, `upstream.json`

**Interfaces:**
- Produces: `PagePair` 에 `figure_svg_refs: list[str]`(그 문항 `figures/solutions/<id>-solution-NN.svg` 절대 경로), `figure_svg_missing: list[str]`(짝 SVG 가 없는 PNG 이름). 둘 다 읽을 때 `.get(..., [])` 로 받아 옛 `pair.json` 과 호환한다.
- 동결 위치는 PNG 와 같은 `source/snapshots/figures/<sha>/<이름>.svg`, 출처는 `inputs.json` 의 `files` 에 남는다. SVG 는 픽셀 대조에 쓰지 않는다(근거 보존용).

- [ ] **Step 1: 실패하는 테스트 작성** — `test_sources_lab.py`

- `test_svg_refs_are_exact_per_problem`: `discover(REPO,'실험05',['q-dec2x4-design'])[0]` 의 `[Path(f).name for f in figure_svg_refs] == ['q-dec2x4-design-solution-01.svg']` 이고 `figure_svg_missing == []`.
- `test_svg_is_frozen_with_provenance`: `freeze_sources` 뒤 `(run/frozen[0]['figure_svg_refs'][0]).is_file()` 이고 `inputs.json['files']` 에 그 상대 경로 키가 있다.
- `test_missing_svg_warns_without_failing`: 실험05 사본에서 그 문항 SVG 를 지우면 문항은 여전히 반환되고 `figure_svg_missing == ['q-dec2x4-design-solution-01.png']`.
- `test_prepare_copies_svg_into_run` (`test_cli.py`): `prepare` 뒤 런 폴더에서 `pair['figure_svg_refs']` 파일이 모두 있다.

- [ ] **Step 2: 실패 확인** — Expected: `KeyError: 'figure_svg_refs'` 로 FAIL.

- [ ] **Step 3: 구현** — `discover` 가 PNG 와 같은 정규식으로 `.svg` 도 모으고, PNG 마다 같은 stem 의 SVG 가 없으면 `figure_svg_missing` 에 PNG 이름을 넣는다. `freeze_sources` 가 PNG 와 같은 `freeze(f, True)` 로 동결한다. `video.py` 의 런 복사 루프가 두 목록을 함께 복사한다. `export_page` 인자(`figure_refs`)는 PNG 만 그대로 넘긴다.

- [ ] **Step 4: 통과 확인**

Run: `.venv/bin/python -m unittest discover -s .claude/skills/logic-lab-solution-video/tests -p 'test_sources_lab.py' -v && .venv/bin/python -m unittest discover -s .claude/skills/logic-lab-solution-video/tests -p 'test_cli.py' -v`
Expected: PASS.

- [ ] **Step 5: 커밋**

```bash
git add .claude/skills/logic-lab-solution-video
git commit -m "feat(solution-video): 그림 의미의 근거인 SVG 를 PNG 와 함께 동결한다"
```

---

### Task 8: 왼쪽 패널 자료를 확대·주석 대상으로

**Files:**
- Modify: `.claude/skills/logic-lab-solution-video/scripts/solution_video/annotations.py` (`_validate` 의 region 검사)
- Modify: `.claude/skills/logic-lab-solution-video/tests/test_annotations.py`, `tests/test_focus.py`
- Modify: `.claude/skills/logic-lab-solution-video/references/pdf-and-coverage.md`, `upstream.json` (`tests/test_annotations.py`·`tests/test_focus.py` 항목 추가)

**Interfaces:**
- 변경: region 은 `work_bbox` 와 **겹치지 않으면** 쪽 어디든 된다(`check_box` 의 "overlaps work_bbox" 만 남기고 `r['bbox'][3] > work_bbox[1]` 이면 실패하던 "region must be above work_bbox" 를 지운다). `focus.py` 는 바꾸지 않는다.

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_annotations.py` (fixture 쪽 400×300, `work_bbox=[100,100,300,240]`):
- `test_region_beside_work_area_is_accepted`: `regions=[dict(id='circuit', bbox=[10,40,90,200])]`(왼쪽, 아래 끝 200 > work 위 100) → `validate_teaching` 이 예외 없이 `regions[0]['bbox']` 를 돌려준다.
- `test_region_overlapping_work_area_is_still_rejected`: `bbox=[80,40,150,200]` → `InputError` 메시지에 `overlaps work_bbox`.

`tests/test_focus.py`:
- `test_left_panel_region_view_keeps_margins`: 위 왼쪽 region 으로 `compile_focus_keys` → 뷰가 region 을 포함하고 `(b[0]-v[0])*scale >= 179`, `(b[1]-v[1])*scale >= 199` (기존 여백 계약과 같은 단언 형태).

- [ ] **Step 2: 실패 확인**

Run: `.venv/bin/python -m unittest discover -s .claude/skills/logic-lab-solution-video/tests -p 'test_annotations.py' -v`
Expected: 첫 테스트 FAIL (`region must be above work_bbox`).

- [ ] **Step 3: 구현** — `annotations.py` 의 해당 두 줄(검사)을 지운다. 이유(왼쪽 조건 패널은 중앙 풀이 칸 옆이라 "위" 규칙이 상류 레이아웃 전제였다)를 주석 한 줄로 남긴다.

- [ ] **Step 4: 통과 확인**

Run: `.venv/bin/python -m unittest discover -s .claude/skills/logic-lab-solution-video/tests -p 'test_annotations.py' -v && .venv/bin/python -m unittest discover -s .claude/skills/logic-lab-solution-video/tests -p 'test_focus.py' -v`
Expected: PASS (기존 `test_table_edges_and_infeasible_readability` 포함).

- [ ] **Step 5: 문서** — `pdf-and-coverage.md` 의 region 설명 "work_bbox보다 위에 있어야 한다" 를 "work_bbox 와 겹치지 않아야 한다. 왼쪽 조건 패널의 표·문장도 대상이 되지만 패널 전체가 아니라 필요한 표·문장 단위로 잡는다(패널 전체를 잡으면 배율이 쪽 전체 아래로 내려가 읽기 어렵다)" 로 바꾼다.

- [ ] **Step 6: 커밋**

```bash
git add .claude/skills/logic-lab-solution-video
git commit -m "feat(solution-video): 확대·주석 region 을 work_bbox 와 겹치지 않으면 어디든 허용한다"
```

---

### Task 9: 그림 묶음 오류 문구

**Files:**
- Modify: `.claude/skills/logic-lab-solution-video/scripts/solution_video/writing_camera.py` (`build_writing_camera_keys` 끝의 `InputError`)
- Modify: `.claude/skills/logic-lab-solution-video/tests/test_figure_unit.py`, `tests/test_writing_camera.py` 확인, `upstream.json`

**Interfaces:**
- 변경: 후보가 없을 때 묶음에 figure 도형이 있으면 `InputError('figure chunk cannot fit even at the full-page view; crop or split the figure: <chunk_id>')`, 글자만이면 기존 `'writing chunk cannot fit at 26px; author smaller chunks: <chunk_id>'` 를 그대로 낸다.

- [ ] **Step 1: 실패하는 테스트** — `test_oversized_figure_rejected` 의 정규식을 `r'figure chunk cannot fit.*chunk1'` 로 바꾼다. `tests/test_writing_camera.py` 35행 근처의 기존 글자 묶음 테스트가 여전히 `'chunk'` 로 통과하는지 확인하고, 그 단언에 `'author smaller chunks'` 를 더해 글자 문구가 유지됨을 못박는다.

- [ ] **Step 2: 실패 확인**

Run: `.venv/bin/python -m unittest discover -s .claude/skills/logic-lab-solution-video/tests -p 'test_figure_unit.py' -v`
Expected: `test_oversized_figure_rejected` FAIL.

- [ ] **Step 3: 구현** — 분기 한 줄. 이미 있는 `any(p['kind']=='shape' and p['id'] in figures for p in pieces)` 조건을 변수로 빼서 재사용한다.

- [ ] **Step 4: 통과 확인** — `test_figure_unit.py`, `test_writing_camera.py`. Expected: PASS.

- [ ] **Step 5: 커밋**

```bash
git add .claude/skills/logic-lab-solution-video
git commit -m "fix(solution-video): 안 들어가는 그림 묶음의 오류 문구가 그림에 맞게 나오게 한다"
```

---

### Task 10: layers/ git 정책과 스킬 문서

**Files:**
- Modify: `.gitignore`
- Modify: `.claude/skills/logic-lab-solution-video/SKILL.md` (49행 근처), `references/verification.md`
- Modify: `docs/superpowers/specs/2026-10-09-logic-lab-solution-video-design.md` (결정 #11 한 줄), `upstream.json`
- 추적 해제: `문제풀이영상/**/실행/**/layers/{original,candidate,animated}.svg`, `native.png` (현재 8개)

**Interfaces:**
- `.gitignore` 에 `문제풀이영상/**/실행/**/layers/*.svg`, `문제풀이영상/**/실행/**/layers/*.png` 를 기존 `renders/`·`verification/` 줄 옆에 더한다. `layers/*.json` 은 계속 추적한다.

- [ ] **Step 1: 현재 상태 기록**

Run: `git ls-files -z 문제풀이영상 | tr '\0' '\n' | grep '/layers/' | grep -v '\.json$' | wc -l`
Expected: `8`.

- [ ] **Step 2: `.gitignore` 수정과 추적 해제**

```bash
git ls-files -z -- 문제풀이영상 \
  | python3 -c "import sys; [print(p, end='\0') for p in sys.stdin.read().split('\0') if '/layers/' in p and not p.endswith('.json')]" \
  | xargs -0 git rm --cached --quiet --
```

Expected: Step 1 의 grep 이 `0`. 디스크의 파일은 남아 있다(`ls` 로 확인).

- [ ] **Step 3: 무시 확인**

Run: `git check-ignore -v "<추적 해제한 layers/original.svg 경로 하나>"`
Expected: 새 `.gitignore` 줄이 매치된다. `layers/layers.json` 은 매치되지 않는다.

- [ ] **Step 4: 문서**
  - `SKILL.md` 49행: "`layers/*.json`" 은 그대로 두고 "`layers/` 의 svg·png 는 동결 PDF 에서 `extract` 로 다시 만들 수 있어 무시한다. 새 clone 에서 이어 작업하면 `extract` 부터 다시 돌린다(비용 0)" 를 한 줄 더한다.
  - `references/verification.md`: 새 clone 의 `resume-set` 이 `layers` 단계부터 무효를 돌려줄 수 있음을 한 줄로.
  - 설계 문서 결정 #11: "`layers/*.json`" 문구는 맞다 — 뒤에 "(svg·png 는 무시)" 만 붙인다.

- [ ] **Step 5: 풀이영상 스킬 전체 테스트**

Run: `.venv/bin/python -m unittest discover -s .claude/skills/logic-lab-solution-video/tests 2>&1 | tail -3`
Expected: `OK` (Task 0 기준선과 같거나 더 낫다).

- [ ] **Step 6: 커밋**

```bash
git add .gitignore .claude/skills/logic-lab-solution-video docs/superpowers/specs/2026-10-09-logic-lab-solution-video-design.md
git commit -m "chore(solution-video): layers 의 svg·png 를 추적에서 빼고 문서를 맞춘다"
```

---

### Task 11: 기출12 영상 재제작 (실행 절차 — 코드 변경 없음)

**Files:** `문제풀이영상/실험05/` (새 run 과 MP4)

**Interfaces:**
- Consumes: Task 3 의 새 `실험05_기출문제.pdf`·`실험05_기출풀이.pdf`, Task 5 의 `prepare` 결과 형식.

- [ ] **Step 1: 준비(비용 0)**

```bash
.venv/bin/python .claude/skills/logic-lab-solution-video/scripts/video.py prepare 실험05 --repo "$PWD" --problems 기출12
```

Expected: `status: author-required`, `prepared: 1`, `paid_requests: 0`. 탈락이면 사유를 보고하고 멈춘다.

- [ ] **Step 2: 저작** — `SKILL.md` 의 흐름(PDF·MD 대조 → `source/map.json` → `extract` → manifest·coverage·circuit-review → `check`)을 따른다. 이전 run 의 `map.json`·`manifest.json` 을 출발점으로 쓰되 새 PDF 의 글리프 ID 로 다시 대조한다(논리식 줄 구성이 바뀌었다).

- [ ] **Step 3: 유료 호출 전 점검 — 사용자 확인 지점**

Run: `.venv/bin/python .claude/skills/logic-lab-solution-video/scripts/video.py check --run <새 run>`
Expected: `paid_requests: 0`. 음성 캐시(`assets/voice/`)와 대본이 이전 run 과 같아 `tts` 가 캐시를 맞추면 비용 0 이지만, **대본이 바뀌어 새 합성이 필요하면 여기서 멈추고** 건수·예산을 사용자에게 보고한 뒤 승인을 받는다.

- [ ] **Step 4: 나머지 단계** — `tts` → `assemble` → `render` → `captions` → `verify` → `publish-set`. `verify` 가 `complete=false/live_audio=unverified` 이면 게시하지 않는다.

- [ ] **Step 5: 사용자 청취 요청** — 음성 검토는 실제 청취가 필요하다. 최종 MP4 경로를 알리고 청취·논리식 발음 확인을 요청한다(`audio-review.json` 은 사용자 확인 뒤에만 `live-listened` 로 작성). 이전 MP4 는 `이전버전/` 으로 간다.

- [ ] **Step 6: 커밋** — 사용자 승인 뒤: `git add 문제풀이영상/실험05` 후 `git commit -m "feat(실험05): 수정된 PDF 로 기출12 풀이영상을 다시 만든다"`.

---

## Self-Review 기록

- **Spec coverage:** 결정 1~3 → Task 1·3, 4 → Task 2, 5 → Task 3, 6 → Task 6, 7 → Task 5, 8 → Task 7, 9 → Task 8, 10 → Task 10, 11 → Task 11. 미해결 8건 중 테스트 빈틈(NFD·라벨 성공 경로)은 Task 4, 오류 문구는 Task 9.
- **의도적 이탈:** 결정 #10 의 클램프 제외(Global Constraints 에 근거 기록).
- **타입 일관성:** `synthetic_pack`(Task 4) 은 Task 6 이 쓴다. `figure_svg_refs`(Task 7) 는 `PagePair`·`discover`·`freeze_sources`·`video.py` 에서 같은 이름이다. `label` 키(Task 5)는 `fail()`·실패 항목·`summarize_batch` 에서 같다.
- **순서:** Task 3 의 재렌더가 영상 스킬의 실제 팩 값을 바꾸므로 Task 4 이후는 Task 3 뒤에 한다.
