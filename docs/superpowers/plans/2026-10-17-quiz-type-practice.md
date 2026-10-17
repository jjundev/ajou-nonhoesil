# Quiz Type Practice Implementation Plan

> 2026-10-17 사용자 후속 지정으로 아래 일반 보드 생성 계획을 변경한다. 퀴즈 작도는 모든 실험에서 `강의노트/공지사항/Breadboard.pdf` v1 양식을 페이지 전체·원본 종횡비로 보존한다. v1 JPG 및 v2 geometry로 대체하지 않는다. 원본 PDF 300dpi 배경만 SVG 래스터 금지의 예외로 허용하고, 완성 배선은 PDF에서 확인한 홀 위치에 얹는다. 기존 팩과 보고서 결선도는 소급 변경하지 않는다.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 복습팩을 새로 생성하거나 전체 갱신할 때 해당 실험에 근거한 T/F 4·빈칸 3·작도 1·서술형 2의 자체 출제 연습을 추가한다.

**Architecture:** 에이전트의 기존 저작 절차에 10문항 출제를 추가하고, Python은 정책·문항·그림 계약과 산출물 일치를 검증한다. 선택적 정책 버전으로 새 제목과 보드 배치 패치를 구분해 기존 팩의 검사·재렌더 결과를 유지한다. 새 CLI·문제은행·자동 채점기는 만들지 않는다.

**Tech Stack:** Python, pytest(`python -m pytest -n0`), 기존 HTML Parser, JSON/SVG/PNG, 기존 Pillow·PyMuPDF, Playwright/Chrome, `scripts.lab.workbook_pdf`.

**Spec:** [확정 설계](../specs/2026-10-17-quiz-type-practice-design.md). 사용자 확정일: 2026-10-17. 구현 전 두 문서를 읽는다.

## Global Constraints

- 실험당 10문항: T/F 4·빈칸 3·작도 1·서술형 2.
- 앞으로 생성하거나 전체 갱신하는 팩부터 적용.
- `schema_version=1`, `review_presentation_version=2`, `problem_explanation_version=2` 유지.
- 새 전체 저작에만 선택적 `quiz_practice_version=1`을 기록한다. 기존 파일의 읽기·검사·부분 수정만으로 자동 삽입하지 않는다.
- 원본 워크북 템플릿과 provenance hash를 유지하고, 새 렌더 패치는 정책 버전이 있는 payload에만 적용한다.
- 기존 파일명과 문항별 링크는 유지한다. 은행 원문·고정 필드·기출·사용자 파일을 보존한다.
- 이 기능의 구현·검증 중에는 실제 `복습노트/실험01`~`실험06`을 변경하지 않는다. 시연과 발행 테스트는 임시 루트에서 수행한다.
- 새 패키지·서비스·네트워크 호출을 요구하지 않는다. PowerShell과 현재 Python/pytest·Chrome·PDF 도구를 사용한다.
- 새 유형의 근거·정답 검토가 부족하면 보류하고 발행을 차단한다. 구조 검사를 내용 정확성의 증명으로 보고하지 않는다.
- 문항 내용은 에이전트가 저작한다. Python에 정해진 문제 문장·정답을 담아 자동으로 10개를 복제하지 않는다.

## Review Focus

1. 정책 없는 기존 팩·비정책 연습문제: 새 수량을 요구하거나 기존 렌더 바이트를 바꾸지 않는다. Task 1·3·5에서 고정한다.
2. 총 10개지만 유형이 틀리거나 held/미검토 문항을 섞은 입력: 올바른 포함 문항만 세고 부족 유형을 알린다. Task 1에서 고정한다.
3. 회로도·빈 보드로 위장한 해설 그림, 다른 문항 그림, 빈 칩 명세: build와 발행본 check가 모두 거절한다. Task 2에서 고정한다.
4. 긴 핀 명세·큰 보드·빈 조건·여러 표가 있는 작도 문제: 가독성을 유지하고 넘치면 실패로 드러낸다. Task 3에서 고정한다.
5. 기존 팩 재렌더·문제설명만 갱신·반복 전체 build: 새 문제를 누적 추가하지 않고 기존 파일을 보호한다. Task 5에서 고정한다.

---

## 파일 구조와 현재 연결 지점

Git 정본은 `.claude/skills/logic-lab-review-pack/`이다. `.agents/skills/logic-lab-review-pack`은 Git mode `120000`의 링크이며 Windows에서 읽히는 경로도 같은 정본을 가리킨다. 두 벌의 스킬을 만들거나 링크를 일반 폴더로 교체하지 않는다.

| 파일 | 책임 |
|---|---|
| 새 `scripts/lab/review_pack/quiz_practice.py` | 정책 상수·manifest 분류/수량 검증; 렌더러나 파일 IO 의존 없음 |
| 새 `scripts/lab/review_pack/quiz_practice_content.py` | 네 유형의 저작 HTML·해설·그림의 구조 검사 |
| 기존 `manifest.py` | 선택적 정책 검사 연결 |
| 기존 `workbook_content.py`, `workbook_checks.py` | 새 표시·meta 생성 및 RUN/발행본에서 같은 검사 적용 |
| 기존 `workbook_render.py` | 정책 전용 패치 선택; 기존 기본 패치 결과 보존 |
| 새 `quiz_practice_patches.py` | 보드를 중앙으로 옮기고 해설의 빈 보드를 제거하는 CSS/JS 패치 상수 |
| 기존 `checks.py` | 문제설명 없는 기존 워크북도 워크북 검사에 도달하도록 연결 보완 |
| 기존 스킬 `SKILL.md`·references, 새 `references/quiz-practice.md` | 실제 출제·근거 확인·검산·전체/부분 갱신 경계 |
| 새 `tests/_quiz_practice_fixture.py`와 `test_review_pack_quiz_*.py` | 임시 입력·합성 그림과 검증; 실제 복습노트 수정 없음 |

확인한 연결: `manifest.py:108` 문항 검사, `workbook_content.py:75` 저작 로드와 `:126` projection, `workbook_checks.py:13` 발행본 검사, `workbook_render.py:182` 채울 표 이동 패치, `workbook_rerender.py:13` payload 재렌더, `explanation_checks.py:23` 워크북 검사 호출, `workbook_pdf.py:109` PDF 내보내기. 줄 번호는 현재 기준이므로 실행 시 함수명으로 다시 찾는다.

### Task 1: 10문항 정책과 기존 manifest 호환

**Files:** Create `scripts/lab/review_pack/quiz_practice.py`, `tests/_quiz_practice_fixture.py`, `tests/test_review_pack_quiz_policy.py`; Modify `scripts/lab/review_pack/manifest.py:42-145`.

**Interfaces:**
- Consumes: `manifest.validate_manifest(data)`의 기존 검증 후 구조적으로 유효한 collections. 새 모듈은 manifest를 import하지 않는다.
- Produces: `QUIZ_COUNTS = {'true_false': 4, 'fill_blank': 3, 'breadboard': 1, 'short_answer': 2}`; `QUIZ_LABELS = {'true_false':'T/F','fill_blank':'빈칸','breadboard':'브레드보드 작도','short_answer':'짧은 서술형'}`; `validate_quiz_practice(manifest: dict) -> list[str]`.
- Test helper: `quiz_manifest() -> dict`는 기존 `tests.test_review_pack_manifest.fixture()`를 복사해 기존 1문항을 유지하고, 정책·워크북 v2·문제설명 v2와 10개의 새 문항을 붙인다. 각 새 ID는 `q-qp-e04-tf-01` 등으로 안정적이며 sources는 기존 `s1`의 PDF 1쪽, topics는 `t-mux`, scope는 current, 답은 검토된 합성값이다. 모든 included 문항에 workbook/explanation 정규 경로와 두 checks 블록을 지정한다. T/F 답은 T 2개·F 2개이다.

- [ ] **Step 1: 정책 테스트 작성.** 아래 검사를 구현하고 입력이 변경되지 않았는지도 비교한다.

```python
def test_policy_counts_and_legacy():
    assert QUIZ_COUNTS == {'true_false': 4, 'fill_blank': 3, 'breadboard': 1, 'short_answer': 2}
    assert validate_manifest(quiz_manifest()) == []
    assert validate_manifest(fixture()) == []

@pytest.mark.parametrize('version', [True, '1', 0, 2, None])
def test_invalid_policy_version(version):
    m = quiz_manifest(); m['quiz_practice_version'] = version
    assert any('quiz_practice_version' in e for e in validate_manifest(m))

def test_wrong_mix_does_not_pass_with_total_ten():
    m = quiz_manifest()
    p = next(p for p in m['problems'] if p.get('question_type') == 'breadboard')
    p['question_type'] = 'short_answer'
    errors = validate_manifest(m)
    assert any('breadboard' in e for e in errors)
    assert any('short_answer' in e for e in errors)
```

같은 파일에 `test_held_does_not_fill_quota`(reason 있는 held로 변경 시 부족), `test_unverified_or_unsourced_practice_is_rejected`(answer_status unresolved/disputed, sources=[], topics=[], scope=supplement, given_answer non-null, bank_question_id 추가 각각 오류), `test_unversioned_type_and_unknown_type_rejected`, `test_versions_and_practice_order`(워크북/문제설명 v2 필요, 새 유형은 기존 included 문항 뒤)를 추가한다. T/F derived_answer는 정확히 `T` 또는 `F`이며, 다른 유형의 정답은 비어 있지 않아야 한다. 잘못된 list/row 입력은 예외 대신 기존 validation 오류를 반환해야 한다.

- [ ] **Step 2: 실패 확인.** `python -m pytest -n0 tests/test_review_pack_quiz_policy.py -q` → 새 모듈/상수 부재로 FAIL.
- [ ] **Step 3: 정책 검사 구현.** 위 signature대로 구현하고 `validate_manifest`의 기존 collections 검증 뒤 호출한다. type(version)는 int여야 한다. 정책 없으면 question_type 없는 기존 입력은 그대로 통과; question_type만 있으면 버전 누락 오류. 정책 있으면 included 중 question_type 있는 practice만 세어 각 수량이 정확히 일치해야 한다. 기존 일반 practice와 held 후보는 할당량에 넣지 않는다. 정책 대상은 given_answer=null, verified, current, 출처와 토픽 있음, bank_question_id 없음. 반환 오류에는 문항 ID 또는 부족 유형/기대 수를 넣는다.
- [ ] **Step 4: 검증.** `python -m pytest -n0 tests/test_review_pack_quiz_policy.py tests/test_review_pack_manifest.py tests/test_review_pack_workbook_contract.py tests/test_review_pack_bank_import.py -q` → 모두 PASS.
- [ ] **Step 5: 커밋.** 위 네 파일만 `git add` 후 `git commit -m "feat: validate quiz practice policy"`.

### Task 2: 저작물·해설 검증과 동일한 문제/해설 표시

**Files:** Create `scripts/lab/review_pack/quiz_practice_content.py`, `tests/test_review_pack_quiz_content.py`; Modify `workbook_content.py:75-141`, `workbook_checks.py:13-76`, `tests/_quiz_practice_fixture.py`. 경로는 모두 `scripts/lab/review_pack/` 또는 `tests/` 아래다.

**Interfaces:**
- Consumes: Task 1 상수와 정책 통과 manifest; 현재 registry 필드 계약·`check_authored_html` 유지.
- Produces: `check_quiz_question(problem: dict, html: dict[str, str], problem_figures: list[dict], solution: dict | None, registry: dict[str, dict]) -> list[str]`. question_type 없으면 빈 오류 목록. figures의 src는 RUN의 `figures/..` 또는 발행본의 `.pack/figures/..`를 기존 `strip_data`로 정규화한다. solution=None은 문제 영역만 검사한다.
- Produces in workbook_content: `workbook_meta(manifest: dict, mode: str, total: int) -> dict`, `workbook_section(manifest: dict, problem: dict) -> str`; 생성기와 검사기가 공동 사용한다. 기존 meta/section은 현재 바이트와 동일하게 반환한다. 새 meta에만 `quiz_practice_version: 1`을 추가한다. 새 section은 기존 실험·검토 상태 뒤에 ` · 퀴즈 유형 연습 — 자체 출제 · <QUIZ_LABELS[type]>`를 붙인다.
- Test helper: `create_quiz_run(tmp_path: Path) -> tuple[dict, Path]`는 `quiz_manifest()`와 기존 workbook fixture를 사용해 11문항 RUN을 만든다. 새 10문항의 JSON과 문항별 내용에 맞는 v2 설명 조각(7개 layer+sum)을 만든다. 합성 작도 그림 3개(회로·빈 보드·완성 보드)는 모두 문항별 SVG/PNG·registry를 작성한다. 새 문항 해설 steps에만 `QUIZ_SOLUTION_ONLY_SENTINEL`을 넣어 문제 PDF 비노출 검사에 사용한다. fixture의 그림 검토 상태는 not_run이며 내용은 실험 근거로 주장하지 않는다.

- [ ] **Step 1: 콘텐츠 테스트 작성.** `test_projection_contains_ten_typed_practice_without_answers`에서 q/a 전체 ID 순서 동일, 새 문항 10개, q에 solution/notes 없음, a에 solution 있음, meta의 정책 값과 정확한 문서 제목을 단언한다. `test_legacy_projection_unchanged`는 기존 fixture의 meta·section에 정책 값/문구가 없음을 단언한다. `test_quiz_fragment_contract`는 아래 계약의 항목을 하나씩 제거/변조했을 때 ID 포함 오류가 생김을 parameterize한다.

| 유형 | 기계적으로 확인할 계약 | 내용 검토로 확인할 것 |
|---|---|---|
| 공통 | solution에 비어 있지 않은 steps와 answer | 노트만으로 풀 수 있음, 정답·힌트의 정확성 |
| T/F | 최종 answer 텍스트가 derived_answer(T/F)와 동일; 단계 label `판정 근거`, `문장 확인` | 한 주장, F의 바른 문장, T의 조건 |
| 빈칸 | 단계 label `빈칸별 근거` | 각 빈칸과 답의 대응·허용 표현 |
| 서술형 | 단계 label `채점 핵심`, `허용 표현` | 모범 답의 기능·원리·인과와 채점 요소 |
| 작도 | 조건에 완성된 `table.chip-spec`(머리 `핀/이름/역할`, 비어 있지 않은 데이터행), 정확히 한 `div.work-board > img`; problem_figures에 별도의 회로도; 해설 단계 `연결 기준`, `완성 결선도` 및 solution/present 등록 그림 | 회로와 명세 일치, 전원·GND·미사용 핀, 넷 동등성 |

`test_board_asset_mutations_rejected`는 solution/present를 빈 보드로 지정, 타 문항 그림, 누락 등록, src URL 인코딩, 중복 work-board, 빈 칩 명세 각각을 검사한다. 해결 그림의 alt·파일명 변경으로 role 검사를 우회할 수 없어야 한다. `test_published_check_uses_same_contract`는 stage의 q/a payload 양쪽에 같은 변조를 넣고 MD도 재생성해 단순 양쪽 비교만으로 통과하지 않는 것을 확인한다.

- [ ] **Step 2: 실패 확인.** `python -m pytest -n0 tests/test_review_pack_quiz_content.py -q` → 새 인터페이스 부재/미검출로 FAIL.
- [ ] **Step 3: 콘텐츠 검사 구현.** 위 인터페이스대로 기존 Parser를 사용한다. 칩 명세는 `<div class="table-wrap"><table class="chip-spec">…</table></div>`, 빈 보드는 conditions 안 `<div class="work-board"><img src="figures/questions/...png" alt="작도용 빈 브레드보드"></div>`로 고정한다. 빈 보드는 problem_figures에 다시 등록해 중복 표시하지 않는다. 기존 자산 검사·문제 HTML 검사 뒤 새 검사를 호출하며 HTML substring만으로 role을 판정하지 않는다. 검사 오류는 RUN load에서 ValueError, 발행본 check에서 list[str]로 전달한다.
- [ ] **Step 4: projection 연결.** `build_workbook_data`에서 `workbook_meta`/`workbook_section`을 사용한다. 제목은 설계의 두 문자열로 고정한다. workbook_checks는 meta 전체·section 전체를 두 helper로 대조한다. strict ENTRY_KEYS/AUTHOR_KEYS에는 필드를 추가하지 않으며 question_type은 manifest에만 둔다. MD는 기존 payload 작성기로 새 title·section·본문·해설을 그대로 보존한다.
- [ ] **Step 5: 검증.** `python -m pytest -n0 tests/test_review_pack_quiz_policy.py tests/test_review_pack_quiz_content.py tests/test_review_pack_workbook_content.py tests/test_review_pack_workbook_flow.py tests/test_review_pack_workbook_md.py tests/test_review_pack_workbook_figures.py -q` → 모두 PASS.
- [ ] **Step 6: 커밋.** 이 task의 생성/수정 파일만 stage 후 `git commit -m "feat: validate and project quiz practice content"`.

### Task 3: 새 정책에서만 빈 보드를 중앙 풀이 공간에 배치

**Files:** Create `scripts/lab/review_pack/quiz_practice_patches.py`, `tests/test_review_pack_quiz_render.py`, `tests/test_review_pack_quiz_browser.py`, `tests/fixtures/review_pack/quiz-legacy-render-sha256.json`; Modify `scripts/lab/review_pack/workbook_render.py:182-246`.

**Interfaces:**
- Consumes: Task 2 meta.quiz_practice_version, work-board 마크업·등록 그림.
- Produces: `apply_quiz_patches(text: str, template_name: str) -> str`; 고유 anchor가 없거나 두 개면 ValueError. `apply_local_patches(text, name, *, quiz_practice: bool = False)`로 확장하며 기본값은 기존 동작 그대로다. `render_workbook_html(data, assets)`의 외부 signature는 유지한다.

- [ ] **Step 1: 렌더 실패 테스트 작성.** 기존 fixture payload의 두 mode 렌더 결과 SHA-256을 **구현 전 baseline 파일** `tests/fixtures/review_pack/quiz-legacy-render-sha256.json`에 기록하고 `test_unversioned_render_matches_baseline`으로 고정한다. 새 정책 payload는 문제지의 `.page-center` 안에 work-board 1개, 패널에는 0개여야 한다. 해설의 payload 원문은 같되 DOM에는 빈 보드가 없고 완성 그림만 보인다. 새 patch의 누락/중복 anchor를 `test_quiz_patch_anchor_fail_closed`로 검사한다.
- [ ] **Step 2: 실패 확인.** `python -m pytest -n0 tests/test_review_pack_quiz_render.py -q` → 정책 배치 패치 부재로 FAIL; baseline 검사는 구현 전 PASS여야 한다.
- [ ] **Step 3: 조건부 패치 구현.** render_workbook_html은 version이 정확한 int 1일 때만 새 패치를 적용하고 지원하지 않는 명시적 값은 거절한다. 기존 LOCAL_PATCHES/TEMPLATE_PATCHES의 기본 출력은 바꾸지 않는다. 문제지는 `.work-table` 이동과 공존하게 빈 보드를 별도 `.work-board-block`으로 중앙의 `.work` 앞에 이동한다. 빈 조건 owner만 제거한다. 해설은 `.work-board`만 제거하고 핀 명세·문제 조건을 남긴다. 보드 CSS는 width 100mm, height auto, img display block, margin 0 auto; 풀이 공간과 겹치지 않게 기존 center fit/clip 검사에 포함한다. 그림을 최소 너비 90mm 아래로 축소해 넘침을 숨기지 않는다.
- [ ] **Step 4: 브라우저 테스트 추가.** `test_quiz_board_print_geometry`를 1280×900/375×812와 print media로 실행해 ready=true, overflow='', 문항 ID/Hint 링크 일치, 이미지 complete/naturalWidth>0, 수식·콘솔 오류 0, offline reload를 단언한다. CSS 변환 전 폭인 img.offsetWidth를 mm로 환산해 90mm 이상, 중앙의 너비/높이 안에 있음을 확인한다. `test_oversized_board_or_pin_spec_reports_overflow`는 고정 보드 아래에 긴 핀 표/조건을 넣어 overflow에 문항 ID가 생기는 것을 검사한다. 표 두 개·빈 조건·일반 비작도 문항도 넣어 기존 배치와 공존함을 확인한다. 브라우저 미설치/skip는 검증 미실행으로 기록한다.
- [ ] **Step 5: 검증.** `python -m pytest -n0 tests/test_review_pack_quiz_render.py tests/test_review_pack_quiz_browser.py tests/test_review_pack_workbook_render.py tests/test_workbook_clip_gate.py tests/test_review_pack_workbook_browser.py -q` → 모두 PASS, 필수 브라우저 항목 skip 0. snapshot 원본/provenance의 git diff는 없어야 한다.
- [ ] **Step 6: 커밋.** 새 baseline 포함 task 파일만 stage 후 `git commit -m "feat: place quiz drawing boards in workbook area"`.

### Task 4: 생성 스킬에 실제 출제·검산 절차 연결

**Files:** Modify `.claude/skills/logic-lab-review-pack/SKILL.md:55-101,125-135`, `references/format.md`, `references/authoring.md`, `references/workbook.md`, `references/verification.md`; Create 같은 스킬의 `references/quiz-practice.md`, `tests/test_review_pack_quiz_skill.py`.

**Interfaces:**
- Consumes: Task 1 정책·ID, Task 2 문항/해설 마크업, Task 3 정책 패치와 보드 크기. `.agents` 링크로 노출되는 같은 정본을 편집한다.
- Produces: 새 전체 저작에서 기출 선별 뒤 항상 quiz-practice.md를 읽고 새 10문항을 저작하도록 하는 절차. 기존 문제설명 전용 스킬은 모든 included 문항을 이미 처리하므로 새로운 출제 단계나 정책 주입을 추가하지 않는다.

- [ ] **Step 1: 규칙 계약 테스트 작성.** `test_full_authoring_requires_quiz_reference`는 SKILL.md가 새 참조를 연결하며 파일이 존재함을 확인한다. `test_documented_policy_matches_code`는 quiz-practice.md의 JSON 예를 파싱해 버전·유형별 수량을 QUIZ_COUNTS와 대조한다. `test_partial_workflows_do_not_author_quizzes`는 참조의 명시적 부분 갱신 제외 목록을 확인한다. 산문 전체를 문자열 일치로 테스트하지 않는다.
- [ ] **Step 2: 실패 확인.** `python -m pytest -n0 tests/test_review_pack_quiz_skill.py -q` → 참조/계약 예 부재로 FAIL.
- [ ] **Step 3: 문서 수정.** reference에 다음 순서의 실행 지침과 네 유형의 짧은 작성 예를 넣는다: 교안·칩 자료 확인 → 기존 기출과 학습목표 표 작성 → 기존 자체 문항 ID 재사용/조건 변경 시 새 ID → 네 유형 10문항 작성 → 독립 계산·반례·답 범위 검토 → 작도 그림과 연결표 작성 → 모든 included 문제설명 저작 → build/check/검토/publish/PDF. 기존 ‘개념 공백만 보충’ 규칙은 은행 예상문제 선별에 유지하고, 새 practice에는 유형 연습 목적의 개념 반복을 명시적으로 허용한다.
- [ ] **Step 4: 출처·실패·보드 규칙 명시.** 2026-10-17 유형 관찰과 학습용 수량을 구분한다. ambiguous `sw 인버터`는 교안에서 뜻을 먼저 확인한다. T/F 두 참·두 거짓은 저작 기본값이고 기계 검증으로 진위를 주장하지 않는다. 빈칸 답 순서·허용 표현, 서술형 모범 답·채점 핵심, 작도 전원·극성·미사용 핀·동등한 넷의 인정 기준을 설명한다. 보드 생성은 기존 geometry와 engine verify()/nets()로 좌표·넷을 검토하고 같은 좌표의 SVG+300dpi PNG를 새 자산으로 등록한다. 래스터 SVG 삽입 금지, source_refs/derivation/review_notes 필수, 시각 확인 전 review_status=pass 금지. 부족하면 held와 사유, quota 미달이면 완료/발행 금지로 기록한다.
- [ ] **Step 5: 검증.** `python -m pytest -n0 tests/test_review_pack_quiz_skill.py tests/test_review_pack_work_table.py tests/test_review_pack_workbook_contract.py -q` → PASS. 수동으로 다섯 references와 SKILL의 전체/부분 갱신·기출 보존·검토 상태 규칙이 충돌하지 않는지 읽는다.
- [ ] **Step 6: 커밋.** 이 task의 스킬 정본과 테스트만 stage 후 `git commit -m "docs: require quiz type practice in full review packs"`.

### Task 5: 임시 팩에서 전체 흐름·기존 팩 보호·PDF 검증

**Files:** Create `tests/test_review_pack_quiz_flow.py`, `tests/test_review_pack_quiz_pdf.py`; Modify `scripts/lab/review_pack/checks.py:25-93`와 필요하면 `tests/_quiz_practice_fixture.py`의 임시 입력 보조 함수만. 실제 복습노트·기존 실험 원고는 수정하지 않는다.

**Interfaces:**
- Consumes: `create_quiz_run`, `assemble(manifest,run,out,assets)`, `convert_pack`, `check_pack(folder)`, `rerender_workbook(folder)`, `publish(stage,dest,root)`, `workbook_pdf.export(note_dir,kind,out_dir)` 기존 signature 그대로.
- Produces: 정책 팩의 4 HTML/4 MD와 두 PDF를 임시 폴더에서 검증하는 회귀 테스트. checks.py는 workbook이면서 문제설명 버전이 없는 구형 팩에도 check_workbook_pack을 호출한다. 문제설명 있는 팩은 기존 explanation_checks 내부 호출을 재사용해 중복 검사를 피한다.

- [ ] **Step 1: 통합 실패 테스트 작성.** `test_workbook_check_runs_without_explanation`은 기존 비정책 workbook fixture의 q/a payload 양쪽에 같은 조건 변조를 넣고 MD를 다시 써도 check_pack이 잡는 것을 단언한다. `test_policy_pack_build_has_all_eleven_ids`는 기존 1문항+새 10문항이 문제·해설·문제설명 HTML/MD에 같은 순서로 있고 check_pack=[]임을 확인한다. `test_quota_failure_blocks_build_and_publish`는 1개를 held로 바꾸고 build/publish가 실패하며 기존 dest의 hash가 같음을 확인한다.
- [ ] **Step 2: 실패 확인.** `python -m pytest -n0 tests/test_review_pack_quiz_flow.py -q` → 비정책 workbook의 검사 누락 테스트가 FAIL. 다른 새 통합 테스트는 이미 통과할 수 있다.
- [ ] **Step 3: 검사 경로 보완과 보존 테스트 구현.** checks.py에 위 단일 연결을 추가한다. `test_repeated_build_and_rerender_do_not_accumulate`는 같은 RUN을 두 새 stage에 build해 ID와 산출물 hash가 같고, 한 stage를 두 번 rerender해 두 번째에도 hash가 같음을 검사한다. `test_explanation_only_keeps_workbook_and_pdf_bytes`는 구형·정책 팩 각각 설명 stage를 만들어 q/a HTML·MD·PDF와 원본 폴더의 hash가 같음을 검사한다. 원래 설명 stage는 설명 관련 파일만 바꾸는 계약을 유지한다. bank import는 기존 테스트로 고정 필드 보존을 재확인한다.
- [ ] **Step 4: 임시 publish/PDF 테스트 작성.** test root 아래 source 파일과 실제 sha256을 맞추고, 테스트용 검토 상태와 그림 상태를 설정해 임시 `복습노트/실험04`에 publish한다. 이 값은 테스트 fixture이며 실제 검토 증거로 보고하지 않는다. export는 그 임시 note_dir에 직접 호출한다. `test_quiz_pdf_counts_and_content`는 두 PDF 생성, 문제 PDF 정확히 11쪽·해설 11쪽 이상, A4 가로, check_pdf_content=[]을 단언한다. PyMuPDF로 각 문제 쪽의 제목/자체 출제 표시를 검사하고 작도 쪽에 빈 보드 그림이 한 번 인쇄되며 문제 PDF에 해설 전용 sentinel이 없고 해설에는 있음을 확인한다. 테스트 생성물은 tmp_path 안에만 둔다.
- [ ] **Step 5: 자동 검증.** `python -m pytest -n0 tests/test_review_pack_quiz_policy.py tests/test_review_pack_quiz_content.py tests/test_review_pack_quiz_render.py tests/test_review_pack_quiz_browser.py tests/test_review_pack_quiz_skill.py tests/test_review_pack_quiz_flow.py tests/test_review_pack_quiz_pdf.py tests/test_review_pack_checks.py tests/test_review_pack_publish.py tests/test_review_pack_explanation_stage.py tests/test_review_pack_bank_provenance.py tests/test_workbook_pdf.py -q` → 모두 PASS, 필수 Chrome/PDF 테스트 skip 0. 이어 아래 PowerShell 명령으로 기존 workbook 회귀를 실행해 모두 PASS인지 확인한다. 실제 동작을 확인하지 못한 검증은 not_run으로 남긴다.

```powershell
$workbookTests = (Get-ChildItem tests/test_review_pack_workbook_*.py).FullName
python -m pytest -n0 @workbookTests -q
```
- [ ] **Step 6: 시각·내용 확인.** 임시 시연 팩의 T/F·빈칸·서술형 대표 각 1문항과 작도 문항의 문제·해설 PDF를 PNG로 렌더해 확인한다. 빈 보드에 손으로 IC·배선을 그릴 공간, 핀 번호·레일·배선의 가독성, 해설 그림·최종 답의 잘림을 확인한다. 합성 fixture는 레이아웃 증거일 뿐 실제 새 출제 능력의 증명이 아니다. 스킬 절차의 내용 확인은 별도 임시 RUN에 현재 교안으로 10문항을 저작해 유형별 근거·정답·T/F 2:2·대체 표현·넷을 검토하고 결과를 RUN/검증결과.md에 남긴다. 이 RUN을 실제 복습노트에 publish하지 않는다.
- [ ] **Step 7: 최종 보존 확인·커밋.** `git diff --check`; `git diff --name-only -- 복습노트 보고서 문제은행 docs/learning-pack-source .claude/skills/logic-lab-review-pack/assets/workbook` 결과는 비어 있어야 한다. 검증결과는 임시 RUN에 남기고 최종 보고에는 실행한 테스트·skip·미해결을 구분한다. 이 task 파일만 stage 후 `git commit -m "test: verify quiz practice pack lifecycle"`.

## 자기 검토와 실행 인계

정책/수량/근거/실패는 Task 1·2, 문제·해설·MD 표시는 Task 2, 작도 공간/호환 패치는 Task 3, 실제 저작 행동은 Task 4, 전체 산출물/반복/부분 갱신/PDF/기존 보호는 Task 5가 담당한다. Review Focus의 다섯 항목은 해당 task의 명시된 테스트에 연결했다. 테스트 helper와 함수명은 위 Interfaces를 정본으로 사용하며 별도 LLM 출제 API나 신규 자동 채점 모듈은 없다.

이 계획은 실행 명령이 아니다. 계획을 검토받고 실행 방식을 선택받은 뒤 구현한다. 권장 방식은 **Native**: 다섯 작업이 같은 manifest·projection·렌더 계약에 순서대로 의존하므로 한 구현자가 이어서 구현하고 마지막에 독립 리뷰를 받는 방식이 적합하다. 실행 시 `using-git-worktrees`로 현재 첨부 상태와 저장소를 확인하고 필요한 격리를 정하며, 변경 파일만 커밋한다.
