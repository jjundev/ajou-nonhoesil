# 문제설명 표 너비·그룹 간격 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 실험01~06 문제설명 HTML 전체에 의미 기반 열 너비, 그룹 경계 여백, 보조 그룹 머리글을 적용하고 재생성·내용 보존·브라우저 검증을 완료한다.

**Architecture:** 열 역할과 표현 종류를 문항별 JSON으로 명시한다. 문제 원문과 풀이 조각을 수정하지 않고 문제설명 조립 단계에서 표를 장식하며, 대응 표는 공동 너비 프로필을 사용한다. 템플릿 CSS는 문제설명에만 적용하고, 기존 팩은 별도 stage에서 생성·검증한 뒤 백업과 함께 발행한다.

**Tech Stack:** Python 3, 기존 HTML parser, JSON, CSS, pytest, Playwright Chromium(channel='chrome'). 새 의존성 없음.

**Spec:** 이 문서의 [확정 설계](#확정-설계). 2026-10-15 채팅의 grill-yourself 설계 및 사용자 결정 #8=필요 너비, #9=그룹 머리글 추가를 함께 보존한다.

## Global Constraints

- 적용 대상은 실험01~06의 문제설명 HTML 전체. 현재 표 수는 각각 9/0/8/12/19/14개, 합계 62개이며 구현 시작 시 다시 확인한다.
- 짧은 신호표는 필요한 너비만 사용하고 왼쪽 정렬한다. 문장 비교표는 가용 너비를 쓴다.
- 기본 단일 신호 열은 3rem, 일반 셀 좌우 padding은 각각 0.5rem이다.
- 주요 경계는 양쪽에 각각 0.5rem, 보조 경계는 양쪽에 각각 0.25rem 추가한다.
- 신호표는 입력/중간 계산/출력 등 보조 그룹 머리글을 추가한다. 비교표에는 붙이지 않는다.
- 첫 열 min-width:6em을 문제설명의 관리 대상 표에서 해제한다.
- 신호명·열 순서·기존 머리글·값·빈칸·행 순서·원래 병합 셀·수식·링크를 보존한다.
- 비트열과 상태식은 내부 줄바꿈하지 않는다. 설명 문장은 줄바꿈한다. 글씨 축소와 열 숨김은 금지한다.
- 좁은 화면에서는 table-card 한 곳에서 가로 스크롤한다. 안쪽 table-wrap은 중복 스크롤하지 않는다.
- 문제와 완성 표는 명시적으로 연결한다. 열 구성이 다르면 별도 프로필이다.
- HTML/MD와 생성기·저작 지침·검사기를 함께 갱신한다. 다른 학습 HTML/PDF와 원문/문제은행은 바꾸지 않는다.
- 실행 방법은 계획 검토 시 선택한다. 커밋/푸시는 별도 요청 없이 실행하지 않는다. 아래 작업 단위는 선택적 커밋 경계다.

## Review Focus

1. 같은 이름 A/C가 서로 다른 역할인 표: 역할을 이름으로 추측하지 않으며 메타데이터가 기준이다(Task 1).
2. 빈 표와 상태식이 들어간 완성 표: 공동 프로필로 좌표를 맞추고 긴 상태식을 자르지 않는다(Task 1/3).
3. rowspan/colspan과 기존 그룹 머리글: 논리 열 수를 계산하고 지원 불가능한 충돌은 식별 가능한 오류로 중단한다(Task 1).
4. 기존 팩의 동봉 템플릿과 검사기의 재생성: 공용 소스만 바꾸고 끝내지 않으며 최종 발행 폴더에서 검사가 통과한다(Task 3).
5. 모바일의 이중 스크롤·스와이프 문항 전환: 카드 내부 스크롤만 작동하고 문항이 바뀌지 않는다(Task 2/3).

---

## 확정 설계

### 표현과 너비

역할은 index/control/input/intermediate/output/description, 표현 종류는 signal/bus/expression/text/connector/index로 나눈다. 역할과 표현 종류는 독립이다. 그룹 라벨은 JSON에 한국어로 명시한다. 열 재배열은 하지 않는다.

폭 계산은 빌드 시 결정하며 JS 비활성에서도 동일하게 보인다. schema에 열별 선택적 min_rem을 허용한다. 본문에서 비트열과 식의 가장 긴 값을 확인해 산정하고, 임의 픽셀 측정/신호명 추측은 하지 않는다. 문자 폭 근사는 Unicode East Asian Width W/F=2, 나머지=1로 계산하고, 한 단위에 0.65rem + 셀 기본 padding 합 1rem을 잡는다. bus/expression은 각각 하한 4rem/6rem을 적용한다. signal은 하한 3rem이며 나눌 수 없는 머리글 신호 토큰도 담아야 한다. 길이가 같은 bus는 같은 폭, signal은 같은 표 안에서 같은 폭을 쓴다. min_rem은 수식 등 문자 폭 근사만으로 부족한 경우 수동 보정에 쓴다.

text 열은 하한 12ch(구현상 7.8rem)와 선택적 min_rem을 확보한 뒤, text 열끼리 같은 비중으로 남는 공간을 배분한다. index는 signal의 하한, connector는 2rem 하한을 쓴다. 단위 rem은 최종 표 CSS에서 유지한다. 긴 설명어가 붙은 머리글은 저작한 개행 지점으로 줄바꿈하며 신호 토큰은 분리하지 않는다.

경계 padding은 열 내용 폭과 별도로 더해 colgroup 총너비에 포함한다. 이전 그룹 마지막 셀과 다음 그룹 첫 셀 모두에 적용한다. 주경계(input/control 집합↔intermediate↔output)는 총 1rem 추가, 보조경계(index↔신호, control↔input)는 총 0.5rem 추가다. 표에 명시된 경계가 우선하며 연속 열 그룹별로 보조 머리글을 만든다.

원래 머리글과 값은 유지하고 새 그룹 행은 생성 표시 행으로 식별한다. semantic snapshot 비교와 MD 내보내기는 이 표시 행만 제외하여 원문과 생성 내용의 경계를 보존한다. 기존 그룹 머리글과 중복되면 기존 것을 사용한다. 데이터 셀을 열 머리글로 바꾸지 않는다.

### 파일과 인터페이스

- 새 `scripts/lab/review_pack/table_layout.py`: schema 로딩·유효성 확인·공동 폭 계산·HTML 표 장식. 외부 I/O는 JSON 로딩뿐이다.
- 새 `docs/learning-pack-source/실험NN/problem-explanations/table-layout.json` 6개: 모든 표를 원문·풀이와 대조한 역할/그룹/표현/짝 정보. 실험02는 빈 tables 목록으로 명시한다.
- `TableLayoutError(ValueError)`: experiment/question/table key를 포함하는 메시지.
- `load_layouts(author_root: Path) -> dict | None`: `author_root/problem-explanations/table-layout.json`을 읽고 version=1을 검증한다. 없는 legacy 입력은 None이며 기존 장식 없이 동작한다.
- `layout_problem_tables(problem_id: str, parts: dict[str, str], layouts: dict | None) -> dict[str, str]`: parts 키는 original/conditions/ask/explanation, 각 부분의 table은 0부터 센다. 원문과 풀이를 한 번에 받아 공동 폭을 계산한다.
- JSON table 키는 `<question-id>/<part>/<ordinal>`. expected_headers는 원래 최하위 열 머리글 텍스트를 보존·검사한다. pair 키는 동일 schema 표에만 공통이다. columns는 role/kind/group/선택적 min_rem/header_breaks, boundaries는 left-column index와 major/minor다.
- JSON이 있으면 실제 모든 표를 정확히 한 번 포함해야 한다. 불일치·남는 entry·열 수/머리글 drift·pair schema 불일치는 오류다. 자동 역할 추론은 없다.
- `scripts/lab/review_pack/explanation_render.py`: parts를 조립하기 전에 위 함수를 호출한다. HTML 루트에 문제설명 스타일 범위 표식을 넣는다.
- `scripts/lab/review_pack/html2md.py`: 생성 그룹 행만 MD 변환에서 제외한다. 기존 그룹 행과 authored text는 보존한다.
- `scripts/lab/review_pack/explanation_stage.py`: 메타데이터를 `.pack/problem-explanations/`로 복사하고, 공용 템플릿의 문제설명 스타일을 동봉 템플릿에 동기화하는 명시적 옵션을 지원한다.
- `.agents/skills/logic-lab-review-pack/assets/note-template.html`: 범위 표식 하위 표에만 CSS 적용. `.claude/skills`가 동일 실체를 가리키는지 먼저 확인하여 중복 수정하지 않는다.
- `scripts/lab/review_pack/explanation_checks.py`: 재생성 검사에 JSON을 포함한다.
- `.agents/skills/logic-lab-review-pack/references/authoring.md`: schema·메타데이터 작성·좁은 화면 규칙을 기록한다.

## Task 1: 의미 메타데이터와 결정적 표 장식

**Files:**
- Create: `scripts/lab/review_pack/table_layout.py`
- Create: `tests/test_review_pack_table_layout.py`
- Modify: `scripts/lab/review_pack/explanation_render.py:36-80`
- Modify: `scripts/lab/review_pack/html2md.py`
- Modify: `tests/test_review_pack_explanation_render.py`

**Interfaces:**
- Consumes: 기존 parts HTML 및 author_root.
- Produces: 위 확정 설계의 load_layouts/layout_problem_tables/TableLayoutError. 표시 속성 `data-layout-table`, `data-layout-group-row`, `data-layout-kind`, `data-layout-boundary`와 colgroup 폭.

- [x] **Step 1: 실패 테스트 작성.** `test_explicit_roles_override_header_names`는 A가 input/output 어느 쪽도 될 수 있음을 검사. `test_paired_blank_and_state_tables_share_widths`는 짝 표의 col 폭이 같고 signal 하한 3rem, 양쪽의 가장 긴 식이 폭에 반영됨을 검사. `test_group_boundaries_do_not_add_data_columns`는 경계 여백 표식과 입력/출력 그룹 머리글이 있으며 원래 셀 수/내용은 같음을 검사.
- [x] **Step 2: 유효성·보존 실패 테스트 추가.** `test_layout_rejects_header_or_column_drift`, `test_layout_rejects_missing_extra_and_duplicate_entries`, `test_pair_rejects_different_schema`, `test_spanning_headers_preserved_or_explicitly_rejected`, `test_no_metadata_keeps_legacy_markup`, `test_md_omits_only_generated_group_row`, `test_second_render_is_identical`에 각 오류/보존 결과를 고정한다. 병합 셀 fixture는 유효한 colspan/rowspan과 충돌하는 group boundary를 각각 포함한다.
- [x] **Step 3: `.venv/bin/python -m pytest tests/test_review_pack_table_layout.py -q` 실행.** 새 모듈/인터페이스 부재로 실패하는지 확인한다.
- [x] **Step 4: 표 장식과 렌더러·MD 연결 구현.** 외부 라이브러리 없이 기존 parser로 논리 열 격자를 만들고, 본문 내용과 원래 span 속성을 보존한다. None schema 경로는 기존 테스트와 호환한다.
- [x] **Step 5: `.venv/bin/python -m pytest tests/test_review_pack_table_layout.py tests/test_review_pack_explanation_render.py tests/test_review_pack_explanation_content.py -q` 실행.** 모든 테스트가 통과해야 한다.
- [x] **Step 6: diff 검토 및 선택적 커밋 경계.** 요청받은 경우에만 해당 코드/테스트를 stage하여 `feat: define semantic table layouts for explanations`로 커밋한다.

## Task 2: 표 스타일과 화면 동작

**Files:**
- Modify: `.agents/skills/logic-lab-review-pack/assets/note-template.html:115-126`
- Create: `tests/test_review_pack_table_layout_browser.py`
- Modify: `.agents/skills/logic-lab-review-pack/references/authoring.md:54-58`

**Interfaces:**
- Consumes: Task 1의 colgroup 폭과 data-layout-* 표식.
- Produces: 문제설명에만 적용되는 CSS. table-card가 유일한 가로 스크롤 소유자이며 내용 너비 기준 표와 full-width 문장표를 지원한다.

- [x] **Step 1: 브라우저 실패 테스트 작성.** `test_signal_widths_and_major_minor_gaps`는 signal 폭 차이 <=1px, major 양쪽 padding 추가 각각 0.5rem, minor 각각 0.25rem을 검사한다. 경계 padding을 제외한 내용 폭을 비교한다. `test_compact_signal_and_full_width_text_tables`는 짧은 신호표가 카드 안쪽보다 좁고 비교표는 안쪽 폭과 1px 이내임을 검사한다.
- [x] **Step 2: 추가 실패 테스트 작성.** `test_long_bus_and_state_expression_not_clipped`, `test_one_scroll_owner_and_no_swipe_navigation`, `test_generated_and_existing_headers_accessible`, `test_note_styles_unchanged`, `test_layout_without_javascript`를 375/768/1280px, light/dark에서 실행한다. 스크롤 가능한 표에서 좌우 끝까지 이동해 마지막 열과 셀 값이 접근 가능한지도 검사한다.
- [x] **Step 3: `.venv/bin/python -m pytest tests/test_review_pack_table_layout_browser.py -q` 실행.** geometry/style assertion 실패를 확인한다.
- [x] **Step 4: 확정 설계의 CSS 구현과 저작 지침 갱신.** 기본 셀 padding, 별도 경계 padding, table-layout:fixed와 colgroup 폭을 함께 적용한다. 관리 대상 표에서 첫 열 6em 및 이중 overflow를 해제한다. 주요·보조 그룹 라벨을 원래 제목과 구분하고 scope/colspan으로 연결한다.
- [x] **Step 5: `.venv/bin/python -m pytest tests/test_review_pack_table_layout_browser.py tests/test_review_pack_explanation_browser.py -q` 실행.** 신규 fixture 및 기존 탐색/카드 테스트가 통과해야 한다.
- [x] **Step 6: diff 검토 및 선택적 커밋 경계.** 요청받은 경우에만 `feat: style grouped explanation tables`로 커밋한다.

## Task 3: 전체 팩 분류·재생성·발행 검증

**Files:**
- Create: `docs/learning-pack-source/실험01/problem-explanations/table-layout.json` ~ `실험06/.../table-layout.json`
- Modify: `scripts/lab/review_pack/explanation_stage.py:9-47`
- Modify: `scripts/lab/review_pack/__main__.py` (explain-stage의 `--sync-explanation-template` 옵션)
- Modify: `scripts/lab/review_pack/explanation_checks.py`
- Modify: `tests/test_review_pack_explanation_stage.py`
- Modify: `tests/test_review_pack_explanation_published.py`
- Modify: `tests/test_review_pack_table_layout_browser.py`
- Modify: `복습노트/실험01` ~ `실험06`의 문제설명 HTML/MD, `.pack` 내 메타데이터·동봉 템플릿·검증 기록·manifest
- Create: `docs/verification/2026-10-15-explanation-table-layout.md`

**Interfaces:**
- Consumes: Task 1의 schema/장식 및 Task 2의 스타일.
- Produces: `prepare_explanation_stage(folder: Path, author_root: Path, stage: Path, *, sync_explanation_template: bool = False) -> Path`. 기존 호출 호환. True이면 생성 전 공용 문제설명 CSS 블록만 동봉 템플릿에 반영하며 다른 스타일은 보존한다.

- [x] **Step 1: stage 실패 테스트 작성.** `test_stage_copies_layout_and_syncs_explanation_css`는 새 JSON의 generated_files 포함, source template 스타일 동기화, 최종 재생성 검사 일치를 검증한다. `test_stage_preserves_other_learning_artifacts`는 실험설명/기출문제/기출풀이 HTML·MD·PDF 바이트 동일을 검사한다. 메타데이터 수정 시 기존 published 검사 실패도 고정한다.
- [x] **Step 2: `.venv/bin/python -m pytest tests/test_review_pack_explanation_stage.py -q` 실행.** 새 옵션 미지원/JSON 미복사로 실패하는지 확인한 뒤 stage/CLI/검사기 연결을 구현하고 같은 명령으로 통과를 확인한다.
- [x] **Step 3: 모든 실제 표를 문항 원문·풀이와 대조해 JSON 작성.** original/conditions/ask/explanation별 순번과 머리글을 기록한다. 신호/버스/상태식/비교표를 분류하고 control/input/intermediate/output을 명시한다. 서로 다른 schema의 표는 연결하지 않는다. 62개 전체와 실험02의 빈 목록을 검사한다.
- [x] **Step 4: 발행 전 SHA256와 semantic snapshot 저장.** 원문·다른 HTML/MD/PDF와 각 문제설명의 원래 셀/머리글/span/문항 ID를 `tmp/review-pack/<고유ID>/`에 기록한다. 저작 소스와 `.pack` 조각이 다르면 먼저 원인을 확인하고 기존 본문을 덮어쓰지 않는다.
- [x] **Step 5: 각 실험을 신규 stage로 생성.** `.venv/bin/python -m scripts.lab.review_pack explain-stage --folder 복습노트/실험NN --author-root docs/learning-pack-source/실험NN/problem-explanations --stage tmp/review-pack/<고유ID>/실험NN --sync-explanation-template`. 각 stage에서 `check --folder <stage>`가 `OK (mechanical checks only)`인지 확인한다. 기존 stage 재사용 금지.
- [x] **Step 6: stage의 여섯 HTML 전체를 화면 검사.** 브라우저 테스트에 `--explanation-pack-root <stage-parent>` 옵션을 추가하고 `.venv/bin/python -m pytest tests/test_review_pack_table_layout_browser.py --explanation-pack-root tmp/review-pack/<고유ID> -q` 실행. 모든 문항을 활성화해 375/768/1280px × light/dark, 그룹 간격/짝 좌표/셀 잘림/스크롤/JS 오류/JS 비활성 결과를 기록한다. 대표 신호·버스·상태·비교표를 스크린샷으로 직접 검토한다.
- [x] **Step 7: 콘텐츠·원문 보존과 관련 회귀 확인.** semantic snapshot 동일, 비대상 파일 SHA256 동일을 검사하고 `.venv/bin/python -m pytest tests/test_review_pack_table_layout.py tests/test_review_pack_table_layout_browser.py tests/test_review_pack_explanation_render.py tests/test_review_pack_explanation_stage.py tests/test_review_pack_explanation_content.py -q`를 실행한다. 수행한 검토만 checks에 기록하며 독립 리뷰를 실행하지 않았다면 independent=pass로 새로 주장하지 않는다.
- [x] **Step 8: 검증한 stage만 백업과 함께 발행.** 기존 publish 절차로 각 실험을 교체한다. 문제지·해설지 HTML/PDF가 같으므로 PDF 재생성은 하지 않는다. 발행 후 여섯 `check --folder 복습노트/실험NN`, published/browser 테스트를 다시 실행한다. 실패하면 성공으로 보고하지 않고 검증한 백업으로 복원한다.
- [x] **Step 9: 검증 기록과 최종 diff 확인.** 문서에 62개 분류 결과, 화면 크기/테마, 보존 해시, 백업 경로, 실제 테스트 결과를 남긴다. `git diff --check` 통과 및 변경 범위 일치를 확인한다. 요청받은 경우에만 `feat: apply verified table layouts to explanation packs`로 커밋한다. 최종 답변에는 여섯 HTML과 검증 문서 링크를 제공한다.

## 자체 검토

- 설계의 역할/너비/경계/그룹 머리글/짝 표/모바일/전체 팩 갱신은 Task 1/2/3에 모두 배정했다.
- 인터페이스 이름과 JSON 경로는 렌더러·stage·재생성 검사에서 동일하다.
- 다섯 Review Focus는 각 task의 실패 테스트와 실제 팩 검사에 포함했다.
- 이전 테스트의 원문 substring 보존 assertion은 메타데이터 없는 legacy 경로에 유지하고 관리 대상 표는 semantic snapshot으로 검증한다.
- 템플릿 사본과 CSS 범위 표식을 함께 갱신하므로 실험설명을 재생성하지 않아도 다른 문서의 표시 계약을 보존한다.
- 실행 전 남은 선택은 Native/Subagent-driven 방식뿐이며 표 디자인 선택 #8/#9는 확정됐다.

## 실행 기록

Native로 구현. 선택적 커밋 단계는 사용자 요청이 없어 생략. 상세 결과와 기존 실패 2건은 `docs/verification/2026-10-15-explanation-table-layout.md`에 기록.
