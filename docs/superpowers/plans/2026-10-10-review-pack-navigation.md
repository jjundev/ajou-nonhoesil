# 복습노트 목차 분리 Implementation Plan

> **후속 결정:** 자료 이동 영역과 이 페이지 목차 소제목·진행 합계·막대·실험 이해 섹션 링크를 제거한다. 목차 아래에 정적 토픽 목록만 두고 JS는 기존 링크와 화면을 연결한다. 아래 완료 체크리스트는 최초 구현 이력이며, 현재 규칙은 갱신된 Spec을 따른다. 생성기·검사기·템플릿·기존 HTML·스킬 문서에 내부 목차만 남긴다.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 기존 학습 HTML 전체를 점검해 자료 이동과 내부 목차의 혼합을 수정하고 생성기·검사기·스킬 문서에 같은 계약을 반영한다.

**Architecture:** 공통 생성기는 자료 이동 링크와 내부 섹션 링크를 각각 출력한다. 기존 실험설명은 탐색 부분만 변경하는 일괄 갱신기로 본문을 보존하며, 검사기가 혼합 구조의 재생성을 차단한다. 워크북은 별도 렌더러라는 경계를 유지한다.

**Tech Stack:** Python, 기존 HTML Parser, pytest, HTML/CSS/JavaScript, 기존 로컬 Chrome 브라우저 검증 도구.

**Spec:** `docs/superpowers/specs/2026-10-10-review-pack-navigation-design.md`

## Global Constraints

- 자료 이동은 별도 `<nav class="pack-nav" aria-label="자료 이동">`, 내부 목차는 `<nav class="toc" aria-label="이 페이지 목차">`로 구현한다.
- 표시 순서: `자료 이동` → 구분선 → `이 페이지 목차` → 진행 숫자/막대 → 섹션 → 12px 들여쓴 토픽 목록.
- 현재 자료 링크는 `aria-current="page"`; 현재 토픽의 기존 `aria-current="true"` 계약은 유지한다.
- 토픽/문항 ID·순서·본문·원문 증거·payload·저장 키를 보존한다.
- 생명과학 등 다른 저장소의 upstream 템플릿을 수정하지 않는다.
- 전체 사전 검사와 백업 후 적용한다. 알 수 없는 구조는 쓰기 전에 실패한다. 두 번째 실행은 추가 변경이 없다.
- 실험01~05의 15개 학습 HTML을 전부 조사한다. 해당 패널이 없는 워크북에는 새 패널을 추가하지 않는다.
- 실행 방법은 사용자 선택 이후 확정한다. 커밋은 별도 요청이 있을 때 해당 작업만 정확히 stage한다.

## Review Focus

1. 자료 종류가 2개인 legacy 팩: 존재하지 않는 기출문제 링크를 만들지 않는다(Task 1).
2. JavaScript 꺼짐·잘못된 section hash: 자료 링크를 유지하고 잘못된 그룹을 만들지 않는다(Task 1).
3. 반복 갱신·예상하지 못한 HTML: 중복 삽입이나 부분 쓰기 없이 실패하거나 무변경으로 끝난다(Task 2).
4. standalone 내보내기: `aria-current` 등 속성이 추가된 링크도 상대경로를 남기지 않는다(Task 3).
5. 좁은 패널·긴 제목·읽음 상태 복구: 375px에서 제목과 체크가 잘리지 않고 저장된 상태와 현재 토픽을 구별한다(Task 4).

---

## 파일 구조

| 파일 | 책임 |
|---|---|
| `scripts/lab/review_pack/navigation.py` (신규) | 두 nav의 HTML 생성과 구조 검사 |
| `scripts/lab/review_pack/render.py:81` | navigation helper 사용과 템플릿 슬롯 공급 |
| `scripts/lab/review_pack/checks.py:33` | note/legacy review에 navigation 계약 검사 연결 |
| `.claude/skills/logic-lab-review-pack/assets/note-template.html` | 실제 패널·스타일·토픽 그룹 생성·drawer 동작 |
| `.claude/skills/logic-lab-review-pack/assets/review-template.html` | legacy review의 같은 탐색 계약 |
| `scripts/lab/review_pack/navigation_upgrade.py` (신규) | 백업·사전 검사·기존 HTML 탐색 부분만 갱신하는 CLI |
| `scripts/lab/standalone_note.py:88` | 새 속성이 있는 sibling 자료 링크의 standalone 처리 |
| `복습노트/실험01`~`실험05` | 기존 학습 HTML과 동봉 note/review 템플릿 갱신 |
| `.claude/skills/logic-lab-review-pack/SKILL.md:73` | 저작·조립·검증·갱신의 단일 규칙 |
| `.claude/skills/logic-lab-review-pack/references/verification.md` | 탐색 검증 항목 |
| `.claude/skills/export-standalone-note/SKILL.md` | 갱신 후 standalone 재출력 안내 |
| `docs/verify/logic-lab-review-pack-navigation.md` (신규) | 실제 처리 목록과 검증 증거 |

### Task 1: 생성기와 패널의 탐색 구조를 분리하고 검사 계약을 추가한다

**Files:** 위 navigation.py, render.py, checks.py, note/review 템플릿; `tests/test_review_pack_render.py`, `tests/test_review_pack_checks.py`; 신규 `tests/test_review_pack_navigation.py`.

**Interfaces:**
- Consumes: `output_names(experiment, review_presentation_version=...)`가 반환하는 파일명 dict; 기존 `assemble(manifest, run, out, assets)`와 Parser의 `Node` 트리.
- Produces: `render_navigation(names: dict[str, str], kind: str) -> dict[str, str]`는 `PACK_NAV`와 `TOC` 문자열을 반환한다. kind는 `note`/`review`; TOC에는 `#learning` 하나만 출력한다.
- Produces: `check_navigation(root: Node, expected_page: str) -> list[str]`는 구조가 유효하면 `[]`, 아니면 설명이 있는 오류 목록을 반환한다. 미래 생성 및 일괄 갱신 모두 같은 검사 함수를 쓴다.

- [x] **Step 1: 생성 회귀 테스트를 추가한다.** `test_navigation_separates_documents_from_sections`는 `.pack-nav`의 문서 링크, `.toc`의 `#learning`, 현재 페이지 `aria-current=page` 하나를 검증한다. `test_legacy_navigation_omits_question_page`는 legacy의 문서 링크가 2개임을 검증한다. 기존 `test_toc_supplies_section_for_template_generated_topic_links`도 유지한다.
- [x] **Step 2: 실패를 확인한다.** `python3 -m pytest tests/test_review_pack_render.py tests/test_review_pack_navigation.py -q` → 새 nav가 없어 FAIL.
- [x] **Step 3: render_navigation과 템플릿 슬롯을 구현한다.** 기존 혼합 TOC 생성을 helper로 교체한다. 템플릿에 PACK_NAV 슬롯과 별도 제목·구분선·진행 위치를 적용한다. 링크 텍스트/파일명은 기존 output_names를 따른다.
- [x] **Step 4: CSS·JS를 갱신한다.** 섹션 목록 12px 들여쓰기, 현재 문서 스타일, 두 nav 클릭 시 drawer 닫기, `#` 링크만 section으로 해석하는 guard를 적용한다. JS 없이 링크가 존재하도록 두 nav는 정적 HTML로 출력한다. 인쇄 규칙은 기존 panel 숨김을 따른다.
- [x] **Step 5: 검사 실패 테스트를 추가한다.** `test_navigation_rejects_document_link_in_toc`, `test_navigation_rejects_missing_current_page`, `test_navigation_rejects_duplicate_current_pages`는 각각 오류 목록이 비어 있지 않음을 검증한다. `test_navigation_accepts_local_section_and_page_links`는 `[]`를 검증한다.
- [x] **Step 6: check_navigation을 구현·연결한다.** check_pack의 note 및 legacy review Parser 트리에 호출한다. 별도 workbook HTML에는 이 패널 검사를 적용하지 않는다.
- [x] **Step 7: 테스트를 실행한다.** `python3 -m pytest tests/test_review_pack_render.py tests/test_review_pack_navigation.py tests/test_review_pack_checks.py -q` → 전부 PASS. 브라우저에서 JavaScript 비활성 상태의 두 nav 링크와 없는 section hash의 비오작동을 Task 4에서 확인한다.
- [x] **Step 8: 변경 목록을 검토한다.** 요청 시 커밋 범위는 이 Task의 생성기·검사기·템플릿·테스트만이다.

### Task 2: 기존 HTML을 보존하며 탐색 부분만 일괄 갱신한다

**Files:** 신규 navigation_upgrade.py, `tests/test_review_pack_navigation_upgrade.py`; 기존 `복습노트/실험NN/실험NN_실험설명.html` 및 `자료/assets/{note,review}-template.html`(NN=01~05).

**Interfaces:**
- Consumes: Task 1의 render_navigation/check_navigation과 공통 템플릿.
- Produces: `upgrade_navigation_html(text: str, *, names: dict[str, str], kind: str) -> str`는 기존 탐색 마크업·관련 CSS/JS만 변경한다. 새 구조이면 원문 그대로 반환; 지원하지 않는 구조는 ValueError.
- Produces: `upgrade_packs(folders: list[Path], *, apply: bool = False, backup_root: Path | None = None) -> list[Path]`는 변경 대상 경로 목록을 반환한다. apply=False는 쓰지 않는다. apply=True는 모든 대상 사전 검사 후 백업과 교체를 수행한다.
- CLI: `python3 -m scripts.lab.review_pack.navigation_upgrade --all`(dry-run), `--all --apply --backup-dir <path>`(적용). 탐색 범위는 저장소 `복습노트/실험*/`이다.

- [x] **Step 1: 갱신 테스트를 추가한다.** 최소 old note/legacy review fixture를 사용한다. `test_upgrade_preserves_main_and_ids`는 `<main>` 블록의 원본 문자열, 토픽 IDs, 저장 키가 전후 동일함을 검증한다. `test_upgrade_is_idempotent`는 두 번째 반환 문자열이 첫 번째와 동일함을 검증한다.
- [x] **Step 2: 실패를 확인한다.** `python3 -m pytest tests/test_review_pack_navigation_upgrade.py -q` → 신규 함수가 없어 FAIL.
- [x] **Step 3: upgrade_navigation_html을 구현한다.** 정확한 기존 panel/탐색 CSS/탐색 JS 앵커만 교체한다. 앵커가 없거나 두 개 이상이면 ValueError. `<main>`과 관련 없는 JS·스타일·head 자원을 재작성하지 않는다. 신규 구조를 먼저 감지해 무변경 반환한다.
- [x] **Step 4: 배치 안전성 테스트를 추가한다.** `test_dry_run_writes_nothing`, `test_unknown_page_aborts_batch_before_writes`, `test_apply_creates_backup`, `test_workbook_payload_unchanged`, `test_all_five_published_notes_have_new_navigation`를 작성한다. 마지막 테스트는 현재 5개 노트를 대상으로 하므로 실제 반영 전 실패해야 한다.
- [x] **Step 5: upgrade_packs와 CLI를 구현한다.** 대상 15개 학습 HTML을 분류·보고하고 패널 있는 파일만 변경한다. 동봉 템플릿은 Task 1의 로컬 공통 템플릿으로 동기화한다. 기존 generated_files 파일명 집합이 바뀌지 않음을 확인한다. 개별 파일 교체는 임시 파일을 이용하고 실패 시 백업 복원 경로를 보고한다.
- [x] **Step 6: 일괄 dry-run을 실행한다.** 위 CLI로 5개 실험설명과 템플릿이 변경 대상으로 나오는지, workbook 10개가 검사 대상으로 분류되는지 확인한다. 같은 결함을 가진 추가 저장소 HTML/standalone을 발견하면 처리 목록에 넣는다.
- [x] **Step 7: 백업 후 적용한다.** `python3 -m scripts.lab.review_pack.navigation_upgrade --all --apply --backup-dir output/backups/navigation-2026-10-10`을 실행한다. 백업과 바뀐 파일 목록이 일치해야 한다.
- [x] **Step 8: 테스트와 반복 실행을 확인한다.** `python3 -m pytest tests/test_review_pack_navigation_upgrade.py -q` → PASS. CLI 재실행 → 변경 대상 0. 원본 main/payload와 동봉 템플릿 동기화를 확인한다.
- [x] **Step 9: 변경 목록을 검토한다.** 요청 시 커밋 범위는 갱신기·테스트·관련 학습 산출물이며 백업은 포함하지 않는다.

### Task 3: standalone 호환성과 스킬 문서에 재발 방지 계약을 반영한다

**Files:** standalone_note.py, `tests/test_standalone_note.py`, logic-lab-review-pack/SKILL.md와 references/verification.md, export-standalone-note/SKILL.md.

**Interfaces:**
- Consumes: Task 1의 새 자료 링크와 Task 2의 navigation_upgrade CLI.
- Produces: 기존 `standalone_note.build(note_dir, kind) -> str`와 `leftovers(html) -> list[str]`의 인터페이스를 유지한다. sibling 문서 링크는 속성과 무관하게 비링크 표시로 전환하고 내부 hash 링크는 보존한다.

- [x] **Step 1: standalone 회귀 테스트를 추가한다.** `test_sibling_links_with_current_page_attributes`는 앞/뒤에 aria-current/class가 있는 sibling 링크도 제거되고 `leftovers(html)==[]`임을 검증한다. `test_standalone_keeps_topic_hash_links`는 `#t-start` 링크가 남음을 검증한다.
- [x] **Step 2: 실패를 확인한다.** `python3 -m pytest tests/test_standalone_note.py -q` → 속성이 추가된 sibling 링크가 남아 FAIL.
- [x] **Step 3: sibling 링크 변환을 갱신한다.** 정확히 같은 실험의 HTML 링크만 변환한다. 새 page-current와 topic-current 표시 및 CSS 의존성을 확인하고 클릭할 수 없는 span을 현재 문서 탐색 링크처럼 오인하지 않게 한다.
- [x] **Step 4: 테스트를 실행한다.** `python3 -m pytest tests/test_standalone_note.py -q` → PASS. 실제 실험01~05에서 임시 디렉터리로 내보내고 leftovers가 모두 0임을 확인한다. 기존 내보낸 파일이 발견되면 백업 후 재출력한다.
- [x] **Step 5: 스킬 저작 규칙을 갱신한다.** 자료 링크는 pack-nav, 내부 섹션/토픽은 toc, 현재 페이지 표시, 진행 집계 범위, 12px 들여쓰기와 모바일 두 nav 동작을 명시한다. `실험설명은 생명과학 원본 유지` 문구는 upstream 보존과 논회실 로컬 탐색 개선을 구분하도록 고친다.
- [x] **Step 6: 스킬 갱신 절차를 고친다.** workbook-only rerender 안내를 명확하게 한정하고 navigation 변경에는 Task 2 CLI의 dry-run/백업/apply 명령을 안내한다. standalone 스킬에 갱신된 원본으로 다시 내보내는 순서를 적는다.
- [x] **Step 7: 검증 문서를 갱신한다.** verification.md에 두 nav 경계, 현재 페이지 하나, 토픽 체크/저장 상태, JS 비활성, 모바일 닫기, 인쇄, 반복 갱신 검증을 추가한다. 기존 규칙과 충돌하는 문장이 없는지 문서 diff를 읽는다.
- [x] **Step 8: 변경 목록을 검토한다.** 요청 시 커밋 범위는 standalone·테스트·관련 스킬 문서만이다.

### Task 4: 전체 산출물과 브라우저 동작을 검증하고 증거를 남긴다

**Files:** 신규 `docs/verify/logic-lab-review-pack-navigation.md`; 필요한 기존 navigation tests; 테스트용 출력은 `output/validation/navigation/`.

**Interfaces:**
- Consumes: Tasks 1~3의 변경된 5개 팩, 백업 목록, 검사 함수와 업그레이드 CLI.
- Produces: 실제 확인한 파일·행동·한계를 적은 검증 기록. 내용 독립 검토 상태는 이번 탐색 변경만으로 갱신하지 않는다.

- [x] **Step 1: 관련 테스트를 실행한다.** `python3 -m pytest tests/test_review_pack_render.py tests/test_review_pack_navigation.py tests/test_review_pack_navigation_upgrade.py tests/test_review_pack_checks.py tests/test_standalone_note.py -q` → 전부 PASS.
- [x] **Step 2: 5개 팩 검사를 실행한다.** 각 NN=01~05에 대해 `python3 -m scripts.lab.review_pack check --folder 복습노트/실험NN` → 오류 없음. 실패하면 navigation 원인과 기존 원인을 구분해 기록하고 관련 원인을 해결한다.
- [x] **Step 3: 실제 UI를 확인한다.** 5개 실험설명 모두 375px/1280px, 밝은/어두운 테마에서 검사한다. 각 자료 이동과 토픽 선택, 이전/다음, hash 직접 열기·뒤로가기, 요약·위젯, drawer 닫기·키보드 포커스를 조작한다. 제목/체크 잘림 및 가로 넘침 0, 깨진 이미지·수식·콘솔 오류 0이어야 한다.
- [x] **Step 4: Review Focus의 브라우저 조건을 확인한다.** 실험03의 긴 제목/읽음 체크를 대표 화면으로 삼아 저장 상태를 복구하고 현재 토픽 강조와 비교한다. JS 비활성에서도 두 nav가 남는지, 없는 section hash가 잘못된 목록을 만들지 않는지 확인한다. legacy 2링크 fixture도 브라우저에서 확인한다.
- [x] **Step 5: 나머지 HTML을 확인한다.** 워크북 10개의 payload가 백업과 같고 기존 페이지 레이아웃이 정상인지 확인한다. 프린트 미리보기에서 탐색 패널이 숨겨지는지 확인한다. 스냅샷 해시 고정 파일은 수정되지 않아야 한다.
- [x] **Step 6: 처리 결과를 기록한다.** 문서에 15개 학습 HTML별 수정/검사 결과, 동봉 템플릿, 추가 standalone 유무, 백업 경로, 테스트 결과, 화면 증거, 반복 실행 무변경 결과와 미해결을 적는다.
- [x] **Step 7: 최종 diff를 검토한다.** 본문·IDs·원문 증거·문항 payload·저장 키의 변경이 없는지 확인하고 사용자에게 변경/검증 결과를 보고한다. 커밋 요청이 있으면 이번 범위만 stage한다.

## 계획 자체 검토

- 설계의 표시·동작은 Task 1, 기존 전체 갱신과 보존은 Task 2, standalone/스킬 재발 방지는 Task 3, 완료 증거는 Task 4로 대응한다.
- Review Focus의 다섯 조건에 각각 테스트 또는 실제 브라우저 확인 단계를 배정했다.
- render_navigation/check_navigation/upgrade_navigation_html/upgrade_packs의 이름·입출력을 작업 간 동일하게 사용한다.
- 현재 workbook-only rerender를 사용해 실험설명을 수정할 수 있다고 가정하지 않는다.
- 이 파일 작성 시점에는 구현·테스트 실행·기존 HTML 수정이 수행되지 않았다.

## 실행 결과

2026-10-10 직접 구현 완료. 상세 증거는 `docs/verify/logic-lab-review-pack-navigation.md`. 전체 테스트 2801 passed / 9 skipped; 추가 legacy 브라우저 검사 포함 별도 5 passed. 커밋 없이 변경을 작업 트리에 남겼다.

최종 후속 구현: 목차 아래 정적 토픽 목록만 표시하도록 갱신했고, 관련 53개/전체 2802개 테스트와 별도 리뷰를 통과했다. 사용자 요청에 따라 이번 작업만 커밋·push한다.
