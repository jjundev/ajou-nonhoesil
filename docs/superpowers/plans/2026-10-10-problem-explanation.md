# 문제설명 HTML Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 실험01~05의 72문항 전체를 처음 풀어보는 학생에게 설명하는 HTML/MD를 만들고 이후 학습팩 생성에도 포함한다.

**Architecture:** 기존 note-template과 워크북 문제 payload를 재사용한다. 문항별 설명 조각을 새 계약으로 검증하고 HTML/MD로 조립한다. 기존 팩 갱신은 별도 stage에 설명만 추가하여 기존 자료를 바이트 단위로 보존하며 기존 publish로 발행한다.

**Tech Stack:** 기존 Python/pytest, 정적 HTML/CSS/JavaScript, 번들 Pretendard/KaTeX, Playwright Chromium(channel='chrome'). 새 런타임 의존성 없음.

**Spec:** `docs/superpowers/specs/2026-10-10-problem-explanation-design.md` — 실행자는 설계와 계획을 모두 읽는다.

## Global Constraints

- 실험01~05의 현재 문제지 전체: 각각 12·14·15·12·19문항, 총 72문항. 구현 시작 때 manifest와 문제지 PDF를 다시 대조한다.
- 문제지에 수록된 모든 문항·소문항을 설명한다. 번호·순서·문항 ID·조건을 유지한다.
- 출력: `복습노트/실험NN/실험NN_문제설명.html`과 `.md`.
- 기존 실험설명 템플릿 재사용. 글꼴·색·본문·목차·우측 요약·모바일·다크모드·이전/다음 동작을 동일하게 한다.
- 목차에는 현재 문서의 문항만 둔다. 자료 이동 영역·진행 합계를 추가하지 않는다.
- 풀이·정답을 본문에 모두 펼친다. 학습 잠금·자동 채점을 넣지 않는다.
- 새 문제, 문제 재정렬, 문제설명 PDF·영상은 이번 범위에서 제외한다.
- `disputed/unresolved`를 설명 작성만으로 `verified`로 바꾸지 않는다.
- 기존 HTML·MD·PDF·원문·문제은행·사용자 파일은 보존한다.
- 기존 검사 기록을 새 설명의 검증으로 재사용하지 않는다.
- 375px/1280px × light/dark에서 모든 문항을 확인한다. JS 비활성에서도 문항·목차·완성 풀이가 읽혀야 한다.
- 구현 시 격리가 필요하면 using-git-worktrees 스킬을 사용한다. 사용자 실행 방식 선택 전 구현/커밋을 시작하지 않는다. 커밋은 각 task의 정확한 파일만 stage한다. 다른 작업의 `2026-10-10-lab-equation-wrap-and-video-gates.md`는 포함하지 않는다.

## Review Focus

1. 누락된 설명·소문항·원문 표의 기입 행: 문항은 완전히 대응하고 원문 기입값을 유지해야 한다(Task 1, 4~8).
2. disputed/unresolved: 충돌·조건 부족을 설명하며 답안 상태와 원문을 바꾸지 않아야 한다(Task 2, 4~6).
3. 기존 파일·사용자 파일·불완전한 stage: 검증 실패 시 발행본을 보존하고 미등록 파일 충돌을 거절해야 한다(Task 3).
4. 같은 문항 ID의 읽음 저장·잘못된 hash·JS 비활성: 다른 문서의 체크와 섞이지 않고 내용을 읽을 수 있어야 한다(Task 2).
5. 긴 표/수식과 어두운 테마의 SVG: 모든 문항에서 문서 전체 가로 넘침·잘림·저대비 라벨 없이 읽을 수 있어야 한다(Task 2, 4~8).

---

## File Structure

| 경로 | 책임 |
|---|---|
| `scripts/lab/review_pack/explanation_content.py` (신규) | 버전 활성 시 문항/설명 조각 대응·경로·내용 구조 검증 |
| `scripts/lab/review_pack/explanation_render.py` (신규) | note-template 기반 설명 HTML/MD 조립·MD 출처 메타데이터 |
| `scripts/lab/review_pack/explanation_checks.py` (신규) | 발행 설명과 저장된 조각/payload의 재대조·검토 상태 검사 |
| `scripts/lab/review_pack/explanation_stage.py` (신규) | 기존 팩을 새 stage에 복사하고 설명을 추가하는 보존 경로 |
| `manifest.py`, `render.py`, `html2md.py`, `checks.py`, `publish.py`, `__main__.py` | 기존 파이프라인 통합; 아래 task에 지정한 최소 부분만 변경 |
| `tests/test_review_pack_explanation_{content,render,stage,browser,published}.py` (신규) | 계약·화면·보존·최종 전체 대응 검증 |
| `tests/fixtures/review_pack/explanations/` (신규) | 최소 정상/불확실성 설명 조각; 기존 fixture는 계속 사용 가능 |
| `docs/learning-pack-source/실험NN/problem-explanations/` (신규) | 72개 설명 HTML, 보조 `figures/*.svg`, `검증결과.md` |
| `복습노트/실험NN/자료/` | 설명 조각과 새 그림의 발행 복사; 기존 자원 보존 |
| `.claude/skills/logic-lab-review-pack/{SKILL.md,references/*.md}` | 향후 학습팩 설명 저작·조립·검증 규칙 |

## 공통 인터페이스 결정

- manifest schema_version=1 유지. 선택적 `problem_explanation_version=1` 도입. 활성 시 review_presentation_version=2 필수.
- included 문항의 `explanation_fragment='problem-explanations/<id>.html'` 필수. 다른 status 문항에는 설명을 요구하지 않는다.
- `explanation_checks`: 기존 checks와 같은 source_visual/content/independent/browser 네 값(pass/fail/not_run/self_review). 추가 시 모두 not_run으로 초기화. 발행에는 source_visual=pass, content=pass 또는 self_review, browser=pass 필요. independent는 실제 수행 상태만 기록.
- `output_names(experiment, *, review_presentation_version=None, problem_explanation_version=None) -> dict[str,str]`: 활성 시 explanation_html/explanation_md 두 키 추가. 미활성 결과는 기존과 동일.
- `Explanation` dataclass: `problem: dict`(문제지 payload의 단일 문항), `fragment: str`(추가 설명 HTML). 번호·ID·원문은 problem에서만 가져온다.
- `load_explanations(manifest: dict, question_data: dict, author_root: Path) -> list[Explanation]`: author_root는 저작 RUN 또는 발행본의 자료 폴더. question_data는 `read_workbook_payload(question_html)`의 결과. 잘못된 입력은 ValueError.
- `write_explanations(manifest: dict, question_data: dict, author_root: Path, folder: Path, assets: Path) -> dict[str,Path]`: 설명 HTML/MD와 조각을 folder에 작성하며 explanation_html/explanation_md 반환. 원본 워크북은 쓰지 않는다.
- `check_explanations(folder: Path, manifest: dict) -> list[str]`: 미활성은 []; 활성은 전체 대응·MD·자원·조각/본문 대조 오류 반환. 발행 검토 gate는 publish에서 별도로 적용한다.
- `prepare_explanation_stage(folder: Path, author_root: Path, stage: Path) -> Path`: 기존 generated_files에 등록된 소유 파일만 새 stage에 복사하고 설명 추가. 비소유 파일은 원래 폴더에 유지하여 publish가 보존한다. author_root는 실험별 저작 폴더이며 `<id>.html`, 선택적 figures/를 포함. 오류 시 입력 folder는 무변경; stage는 신규 경로여야 한다.

### Task 1: 설명 콘텐츠 계약

**Files:** Create `explanation_content.py`, `tests/test_review_pack_explanation_content.py`, `tests/fixtures/review_pack/explanations/q-mux-001.html`; Modify `manifest.py:33-38,40-133`.

**Interfaces:** Consumes 기존 manifest/문제지 payload. Produces 위 `Explanation`, `load_explanations`, 확장된 output_names.

- [ ] **Step 1: 실패 테스트 작성.** 최소 workbook payload helper `question_data(ids: list[str]) -> dict`를 테스트 파일 안에 정의한다. `test_optional_explanation_contract`는 미활성 fixture가 그대로 valid이며 활성 출력명이 `실험04_문제설명.html/.md`임을 단언한다. `test_included_only_and_payload_order`는 included ID·number 순서 그대로 반환하고 held 설명은 요구하지 않음을 단언한다.

```python
def test_optional_explanation_contract():
    assert validate_manifest(fixture()) == []
    old = output_names(4, review_presentation_version=2)
    assert 'explanation_html' not in old
    new = output_names(4, review_presentation_version=2, problem_explanation_version=1)
    assert new['explanation_html'] == '실험04_문제설명.html'
    assert new['explanation_md'] == '실험04_문제설명.md'
```
- [ ] **Step 2: 누락·위험 입력 테스트 작성.** `test_missing_duplicate_or_reordered_question_rejected`는 설명 파일 누락, payload 중복/순서 차이, HTML article 중복을 각각 ValueError로 단언한다. `test_unsafe_fragment_rejected`는 `../`, 절대 경로, symlink, script/onerror/javascript URL을 거절한다. `test_required_learning_sections`는 아래 여섯 설명 영역/요약 중 하나가 없거나 빈 경우 거절한다.
- [ ] **Step 3: 실패 확인.** `.venv/bin/python -m pytest tests/test_review_pack_explanation_content.py -q` → 새 계약 미구현으로 FAIL.
- [ ] **Step 4: 계약 구현.** 위 인터페이스를 구현한다. fragment에는 data-explanation 값 `understand,start,solve,verify,pitfall,retry`가 각각 하나씩 있어야 한다. eli5/formal/warn 레이어와 직계 sum[hidden] 필수; 원문·조건·구할 것은 렌더러가 추가하므로 조각에 복제하지 않는다. fragment는 article/h1을 포함하지 않는다. 검산 영역에 최종 답과 검산을 모두 쓰고 retry는 1~3개의 항목으로 제한한다. 미래 문항 수도 동적으로 지원한다.
- [ ] **Step 5: 통과 확인.** 위 테스트와 `tests/test_review_pack_manifest.py` → PASS.
- [ ] **Step 6: 커밋.** 위 task 파일만 `git add` 후 `git commit -m "feat: define problem explanation content contract"`.

### Task 2: 같은 화면의 HTML/MD 조립과 브라우저 계약

**Files:** Create `explanation_render.py`, `tests/test_review_pack_explanation_render.py`, `tests/test_review_pack_explanation_browser.py`; Modify `render.py:82-106`, `html2md.py:75-85,116-144`.

**Interfaces:** Consumes Task 1 `load_explanations`. Produces `write_explanations` 및 신규 build의 explanation_html/explanation_md paths.

- [ ] **Step 1: 실패 테스트 작성.** `test_shared_note_shell_and_complete_content`는 note-template CSS/런타임을 재사용하며 같은 article.topic/목차/summary를 갖고 모든 풀이가 details 없이 펼쳐짐을 단언한다. `test_original_prefilled_table_preserved`는 payload의 이미 채워진 행과 D7…D0 순서를 보존한다. `test_md_keeps_math_figures_anchors_and_sources`는 설명 본문·요약·정적 그림·문항 앵커·원문 출처가 MD에 있고 해당 링크가 유효함을 단언한다.
- [ ] **Step 2: 불확실성 테스트 작성.** `test_answer_status_warning_is_not_lost`는 disputed/unresolved 문항의 경고가 HTML/MD에 나타나고 입력 manifest 상태가 무변경임을 단언한다. 불확실성 경고를 설명 조각의 warn에 요구하며 누락 시 생성 실패로 처리한다.
- [ ] **Step 3: 실패 확인.** `.venv/bin/python -m pytest tests/test_review_pack_explanation_render.py -q` → FAIL.
- [ ] **Step 4: 렌더러 구현.** `write_explanations`는 기존 note-template의 placeholder/로컬 자원 치환을 재사용한다. 조립기는 `문제 N · 제목`, original/conditions/ask/figures를 표시하고 그 뒤 추가 설명을 둔다. 문서의 RANGE는 `logic-lab-NN-problem-explanation`; data-panels=note 유지. topics 링크는 본문 start 영역에서 실제 실험설명 앵커로 연결한다. 출처는 `export_document(..., note_metadata=문항별메타데이터)`로 MD에 추가하고 HTML에는 넣지 않는다. explanation 조각은 자료/에 보존하며 관련 그림은 자료/problem-explanations/figures/에 둔다. html2md의 HTML→MD 이름 변환에 문제설명을 추가한다. assemble은 워크북 생성 이후 이 함수를 호출한다. convert_pack은 활성 시 추가 MD 존재를 확인하되 기존 세 문서의 변환을 바꾸지 않는다.
- [ ] **Step 5: 브라우저 테스트 작성.** 임시 완성 fixture를 만들어 `test_explanation_navigation`를 375/1280 × light/dark로 실행한다. 목차 hash/aria-current, 이전/다음, 요약, 새로고침 읽음 유지, 모바일 drawer 닫기, 키보드 포커스를 단언한다. `test_read_state_isolated`는 같은 context에서 원래 실험설명을 읽어도 설명 문항 체크가 변하지 않음을 단언한다. `test_no_js_and_invalid_hash`는 JS 비활성에서 전체 본문/목차가 보이고 `#missing`, `#%`에서 JS 오류가 없음을 단언한다. 긴 표/수식/SVG fixture에서 pageerror·katex-error·깨진 이미지=0, scrollWidth<=innerWidth와 내부 표 스크롤을 검사한다. 브라우저는 기존 테스트처럼 channel='chrome' 사용.
- [ ] **Step 6: 통과 확인.** `.venv/bin/python -m pytest tests/test_review_pack_explanation_render.py tests/test_review_pack_explanation_browser.py tests/test_review_pack_render.py tests/test_review_pack_md.py -q` → PASS.
- [ ] **Step 7: 커밋.** 위 task 파일만 stage 후 `git commit -m "feat: render problem explanations with note layout"`.

### Task 3: 기존 팩의 보존 갱신과 발행 검사

**Files:** Create `explanation_checks.py`, `explanation_stage.py`, `tests/test_review_pack_explanation_stage.py`; Modify `checks.py:20-86`, `publish.py:13-42`, `__main__.py:15-70`.

**Interfaces:** Consumes Task 2 `write_explanations`. Produces `check_explanations`, `prepare_explanation_stage`, CLI `explain-stage --folder FOLDER --author-root AUTHOR --stage STAGE`.

- [ ] **Step 1: 실패 테스트 작성.** `test_stage_preserves_existing_bytes`는 fixture의 기존 소유 HTML/MD/PDF를 stage와 hash로 비교하여 manifest 외 무변경을 단언하고, 사용자메모는 원래 폴더에 남고 stage/generated_files에 없음을 단언한다. `test_failed_stage_never_mutates_source`는 누락 설명/깨진 그림에서 원래 폴더 무변경, 기존 stage 거절을 단언한다. `test_explanation_only_rerun_is_deterministic`는 같은 입력의 두 신규 stage에서 설명 결과가 같음을 단언한다.
- [ ] **Step 2: 발행 gate 테스트 작성.** `test_unreviewed_explanation_cannot_publish`는 기존 checks=pass여도 새 explanation_checks의 browser 또는 content가 not_run이면 발행 거절을 단언한다. `test_original_publish_guards_remain`는 원문 hash 변경·사용자 설명파일 충돌·symlink·교체 실패 시 발행 거절/복구를 단언한다. `test_check_detects_missing_or_modified_explanation`는 파일 누락/문항순서 변경/깨진 개념 링크/풀이 삭제를 검사 오류로 단언한다.
- [ ] **Step 3: 실패 확인.** `.venv/bin/python -m pytest tests/test_review_pack_explanation_stage.py -q` → FAIL.
- [ ] **Step 4: stage와 검사 구현.** question payload와 manifest를 먼저 대조하고 신규 stage에 generated_files의 소유 파일만 복사한다. 목록의 누락 파일·위험 경로·symlink는 복사 전 실패시킨다. 비소유 사용자 파일은 원래 folder에 유지한다. author-root `<id>.html`을 stage 자료/problem-explanations/로 복사하며 각 included explanation_fragment를 지정한다. 추가 그림은 별도 하위 폴더에 복사하고 기존 비소유 경로와의 충돌은 거절한다. 새 checks는 not_run 초기화. generated_files는 기존 소유 목록에 신규/기존 설명 소유 파일만 더하고 stage의 실제 파일 집합과 같게 한다(사용자 파일을 소유 파일로 편입하지 않는다). 기존 note-template snapshot을 그대로 사용한다. check_explanations는 저장 조각과 payload로 재조립한 본문/MD·순서·링크를 검증하며 render가 무단으로 파일을 고치지 않도록 비교용 임시 폴더를 사용한다. stage CLI 성공은 검증 통과 후 stage 경로 출력/exit 0; 실패는 FAIL/exit 1. 새 build에도 조각과 추가 자원, generated_files를 포함한다.
- [ ] **Step 5: 통과 확인.** `.venv/bin/python -m pytest tests/test_review_pack_explanation_stage.py tests/test_review_pack_checks.py tests/test_review_pack_publish.py tests/test_review_pack_workbook_flow.py -q` → PASS.
- [ ] **Step 6: 커밋.** 위 task 파일만 stage 후 `git commit -m "feat: stage and validate explanations without rewriting packs"`.

## Task 4~8 공통 저작·검증 절차

각 task는 실험 하나의 모든 문항을 독립적으로 완성한다. 설명 원고의 일반 문장에 구현 테스트를 추가하지 않는다. `tests/test_review_pack_explanation_published.py`의 공통 parametrized 검증으로 문항/소문항 coverage와 기술 계약을 검사하고, 내용 충분성과 회로 정확성은 별도 검토 기록으로 확인한다.

**Interfaces:** Consumes Task 3 stage CLI와 기존 `check`, `publish`. Produces 실험별 설명 HTML/MD·원고·추가 그림·검토 기록·업데이트된 manifest.

**공통 테스트 인터페이스:** `audit_experiment(number: int) -> dict`는 최종 manifest included 목록, 문제지 payload, 설명 articles를 읽어 `ids`, `numbers`, `counts`, `answer_status`, `subparts_complete`를 반환한다. 소문항 목록/대응은 실험별 `검증결과.md`의 고정 표 `문항 ID | 원문 소문항 | 설명 위치 | 첫 줄 | 검산 | 상태`에서 읽는다. 이 표는 실제 원문 대조 후 작성하며 기계 검증이 원문의 소문항 수를 보장한다고 주장하지 않는다.

```python
@pytest.mark.parametrize('number, expected', [(1, 12), (2, 14), (3, 15), (4, 12), (5, 19)])
def test_experiment_coverage(number, expected):
    result = audit_experiment(number)
    assert result['counts'] == (expected, expected, expected)
    # ids/number lists are ordered as manifest, workbook, explanation document.
    assert result['ids'][0] == result['ids'][1] == result['ids'][2]
    assert result['numbers'][0] == result['numbers'][1] == result['numbers'][2]
    assert result['subparts_complete'] is True
```

위 테스트는 Task 4에 실험01만 활성화하여 만들고 Task 5~8에서 해당 실험 param을 순차 추가한다. 후속 산출물 부재를 앞 task의 실패로 만들지 않는다. `numbers[0]`는 manifest included 순서에서 `1..N`으로 계산한다. `answer_status`는 원본 상태와 설명 문구의 대응을 검사하는 별도 `test_experiment_answer_states`로 검증한다.

**공통 명령:** 아래 NN을 task 번호의 실험값으로 치환한다. `.venv/bin/python -m scripts.lab.review_pack explain-stage --folder 복습노트/실험NN --author-root docs/learning-pack-source/실험NN/problem-explanations --stage tmp/review-pack/explain-NN-<고유실행ID>`; 성공은 stage 경로와 exit 0. stage 검사는 `check --folder STAGE` → `OK (mechanical checks only)`.

**발행 전 검토:** 원문 PDF를 렌더링해 표·회로를 확인하는 작업에는 pdf 스킬을 적용한다. 실제 문제지 PDF와 payload의 번호·주어진 표·그림을 비교한다. 계산/진리표/회로는 답안을 베끼지 않고 다시 도출한다. first line·검산·모든 소문항 위치를 표에 기록한다. stage의 모든 문항을 375/1280 × light/dark와 JS 비활성에서 확인한다. 풀이의 첫 적용/완성 결과를 브라우저에서 실제로 읽어 판단한다. 새 검토 결과를 stage의 explanation_checks에 기록하고 검증결과를 저작 폴더와 발행 자료/problem-explanations/에 보존한다. 실패는 원고 수정 후 새 stage 재검증; 기존 pack은 교체하지 않는다.

**공통 발행:** `.venv/bin/python -m scripts.lab.review_pack publish --root . --experiment N --stage STAGE` → 대상/backup JSON, exit 0. 발행 전후 manifest 외 기존 파일 hash 보존과 사용자 파일 소유권을 확인한다. 실제 independent reviewer가 없으면 independent는 self_review 또는 not_run으로 남긴다. 새 오류가 없는 한 기존 워크북을 rerender하지 않는다.

### Task 4: 실험01 — 12문항

**Files:** Create `docs/learning-pack-source/실험01/problem-explanations/<각 included ID>.html`, 선택적 `figures/*.svg`, `검증결과.md`, `tests/test_review_pack_explanation_published.py`; Create 발행 `복습노트/실험01/실험01_문제설명.html/.md`, `자료/problem-explanations/`; Modify 해당 `자료/manifest.json`.

- [ ] **Step 1: 실패 테스트.** `test_experiment_coverage(1)`에서 `counts == (12,12,12)`, ids/numbers 세 목록 동일, subparts_complete=True, q-deq 상태 disputed 유지 단언. 현재 설명 부재로 FAIL을 확인한다: `.venv/bin/python -m pytest tests/test_review_pack_explanation_published.py -k 'coverage and 1' -q`.
- [ ] **Step 2: 12문항 저작.** 게이트 진리표는 첫 행의 입력→각 게이트 판단→출력 칸, 식/회로는 중간 신호부터 최종 출력, CMOS는 도통 경로부터 출력 판정을 설명한다. q-deq는 제공/도출 답 충돌과 적용 조건을 명시한다. 공통 일곱 단계와 전체 소문항을 작성한다.
- [ ] **Step 3: stage와 원문·내용·브라우저 검토.** 위 공통 절차 수행; 12문항 coverage 표와 검토 상태를 기록한다.
- [ ] **Step 4: 발행과 통과 확인.** 공통 발행 후 위 coverage 테스트 및 `check --folder 복습노트/실험01` → PASS/OK. 기존 파일 hash 무변경을 확인한다.
- [ ] **Step 5: 커밋.** 위 task의 원고·그림·검토·발행 설명·manifest·공통 테스트만 stage 후 `git commit -m "docs: explain all experiment 01 problems"`.

### Task 5: 실험02 — 14문항

**Files:** 위 Task 4의 실험 경로를 실험02로 치환; Modify `tests/test_review_pack_explanation_published.py`의 실험02 기대값.

- [ ] **Step 1: 실패 테스트.** coverage(2)에서 counts=(14,14,14), 세 목록 동일, subparts_complete=True; q-region=disputed, q-delay-transition/q-transition/q-speed=unresolved 단언. 해당 실험 테스트만 실행하여 설명 부재 FAIL 확인.
- [ ] **Step 2: 14문항 저작.** 입력/출력 전압 기준, 파형의 기준선·시점·단위, 지연·전이·속도 계산의 첫 식을 설명한다. 필요한 수치/정의가 없는 문제는 어떤 값이 더 필요한지와 가능한 해석을 명시하며 가짜 측정값을 만들지 않는다.
- [ ] **Step 3: 공통 stage·검토 수행.** 모든 그래프 축·단위·threshold와 소문항을 원문 대조하고 14개 coverage 행 기록.
- [ ] **Step 4: 공통 발행·해당 coverage 테스트·팩 검사.** PASS/OK와 기존 파일 hash 무변경 확인.
- [ ] **Step 5: 해당 실험 파일만 커밋.** `git commit -m "docs: explain all experiment 02 problems"`.

### Task 6: 실험03 — 15문항

**Files:** Task 4 실험 경로를 실험03으로 치환; Modify 공통 published 테스트 실험03 기대값.

- [ ] **Step 1: 실패 테스트.** coverage(3)에서 counts=(15,15,15), 동일 순서/전체 소문항; q-fa-design/q-fs-roles=disputed, q-cs-roles-sub=unresolved 단언. 해당 실험 테스트로 FAIL 확인.
- [ ] **Step 2: 15문항 저작.** 각 입력·carry/borrow 역할, 첫 진리표 행, 합/차 식과 출력, 설계 중간 신호를 작은 상태 예제로 풀어 설명한다. 충돌 답안·역할 조건 부족을 명시한다.
- [ ] **Step 3: 공통 stage·검토 수행.** 합/차·carry/borrow를 독립 계산하고 모든 소문항 coverage 기록.
- [ ] **Step 4: 공통 발행·해당 coverage 테스트·팩 검사.** PASS/OK와 기존 파일 hash 무변경 확인.
- [ ] **Step 5: 해당 실험 파일만 커밋.** `git commit -m "docs: explain all experiment 03 problems"`.

### Task 7: 실험04 — 12문항

**Files:** Task 4 실험 경로를 실험04로 치환; Modify 공통 published 테스트 실험04 기대값.

- [ ] **Step 1: 실패 테스트.** coverage(4)에서 counts=(12,12,12), 동일 순서/전체 소문항; q-tri/q-demux4=disputed 단언. 해당 실험 테스트로 FAIL 확인.
- [ ] **Step 2: 12문항 저작.** 선택선→선택한 입력/출력→실제 값 순서와 enable/active-low 조건, tri-state의 Z와 0 차이, 회로 설계의 첫 줄을 설명한다. q-tri/q-demux4 충돌을 명시한다.
- [ ] **Step 3: 공통 stage·검토 수행.** 선택선 비트 순서·활성 극성·미선택 출력·Z 상태를 원문 및 독립 계산과 대조하고 coverage 기록.
- [ ] **Step 4: 공통 발행·해당 coverage 테스트·팩 검사.** PASS/OK와 기존 파일 hash 무변경 확인.
- [ ] **Step 5: 해당 실험 파일만 커밋.** `git commit -m "docs: explain all experiment 04 problems"`.

### Task 8: 실험05 — 19문항

**Files:** Task 4 실험 경로를 실험05로 치환; Modify 공통 published 테스트 실험05 기대값.

- [ ] **Step 1: 실패 테스트.** coverage(5)에서 counts=(19,19,19), 동일 순서/전체 소문항과 기존 상태 전부 유지 단언. 해당 실험 테스트로 FAIL 확인.
- [ ] **Step 2: 19문항 저작.** 3×8 디코더 001→1→D1→실제 표 칸을 설명하고 모든 행을 완성한다. 인코더 우선순위·active-low·BCD/Excess-3·설계 문제도 첫 입력 예부터 전체 소문항을 설명한다. 단순 인코더와 우선순위 인코더의 동시 입력 조건을 구분한다.
- [ ] **Step 3: 공통 stage·검토 수행.** D7…D0/A2…A0 순서·극성·enable·don't-care를 원문/식/표와 대조하고 coverage 기록.
- [ ] **Step 4: 공통 발행·해당 coverage 테스트·팩 검사.** PASS/OK와 기존 파일 hash 무변경 확인.
- [ ] **Step 5: 해당 실험 파일만 커밋.** `git commit -m "docs: explain all experiment 05 problems"`.

### Task 9: 향후 생성 규칙과 전체 완료 검증

**Files:** Modify `.claude/skills/logic-lab-review-pack/SKILL.md`, `references/authoring.md`, `format.md`, `verification.md`, `workbook.md`; Create `docs/verify/logic-lab-review-pack-problem-explanation.md`.

**Interfaces:** Consumes 모든 task의 코드·발행 팩. Produces 다음 학습팩도 같은 설명을 만드는 저작/검증 안내와 전체 검증 기록.

- [ ] **Step 1: 신규 build 회귀 테스트 확인.** Task 2의 통합 테스트에 `test_future_workbook_build_includes_explanations`를 추가하여 활성 manifest build의 네 HTML/네 MD와 1문항 설명을 단언한다. 미활성/legacy 테스트는 기존 결과와 같음을 확인한다. 실패하면 해당 생성 경로만 고친다.
- [ ] **Step 2: 스킬 문서 갱신.** 새 워크북에는 problem_explanation_version=1, 각 included explanation_fragment와 explanation_checks를 지정하도록 한다. 네 HTML/MD, 일곱 교육 단계, 같은 note-template, 본문 전체 펼침, 별도 읽음 범위, 모든 소문항·불확실성·첫 줄·완성·검산, 추가 자원 보존/발행 gate를 정확히 기록한다. 원문/워크북 계약은 유지한다.
- [ ] **Step 3: 전체 테스트.** `.venv/bin/python -m pytest tests/test_review_pack_*.py -q` → 모두 PASS. published 설명 브라우저 검증은 5실험×4화면 조건에서 모든 문항을 순회하며 오류/그림/수식/가로 넘침을 검사하도록 Task 2 브라우저 테스트에 추가한다. JS 비활성도 5실험 모두 확인한다. 기존 navigation/workbook 테스트도 통과해야 한다.
- [ ] **Step 4: 최종 팩 검사.** 실험01~05 각각 `.venv/bin/python -m scripts.lab.review_pack check --folder 복습노트/실험NN` → 모두 OK. 총 72문항 대응, 원문 소문항 감사, 기존 바이트 보존, 실제 independent 상태와 미해결 조건을 docs/verify 문서에 기록한다. 스크린샷은 output/validation/problem-explanations/에 저장하고 관련 기록에서 참조한다.
- [ ] **Step 5: 최종 커밋.** 해당 task의 코드 변경/테스트/스킬 문서/검증 문서만 stage 후 `git commit -m "docs: require and verify explanations in future lab packs"`. 최종 변경 목록을 확인하여 관련 없는 파일이 포함되지 않았음을 보고한다.

## Self-Review 결과

- 범위 대응: 계약 Task 1, 화면/MD Task 2, 보존/발행 Task 3, 전체 72문항 Task 4~8, 향후 생성/최종 검증 Task 9.
- Review Focus 1~5는 해당 task의 명명된 테스트·원문 감사·브라우저 검증으로 연결했다. 교육적 충분성은 기계 검사가 보장하지 않으므로 문항별 실제 검토를 분리했다.
- 함수명·인자·반환형과 버전 키를 공통 인터페이스에 고정했다. 기존 RUN 부재를 stage 경로로 해결하며 기존 자료를 재생성하지 않는다.
- 새 검토 gate는 기존 checks와 분리했다. 검사 성공과 독립 정답 검증을 혼동하지 않는다.
- 이번 작업은 설계/계획 작성만이다. 구현·테스트 실행·커밋·발행은 실행 방식 선택 후 진행한다.

## Execution Handoff

추천: Native. 같은 생성/발행 인터페이스를 사용하는 5개의 실험을 순차 저작하므로 문항과 화면 규칙의 일관성을 유지하기 쉽다. executing-plans로 직접 구현하고 마지막에 새 리뷰어가 전체 변경을 검토한다. Subagent-driven을 선택하면 각 task 구현·리뷰 후 전체 브랜치 리뷰를 수행한다. 실제 모델 선택은 사용자의 설정을 유지하며 임의 변경하지 않는다.
