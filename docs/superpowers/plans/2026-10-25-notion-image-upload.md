# 논회실 Notion 이미지 자동 업로드 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 예비·결과보고서의 로컬 이미지를 Notion 본문에 자동 삽입하고, 실제 위치·캡션·파일 내용 검증과 중단 후 복구까지 보장한다.

**Architecture:** 기존 전체 Markdown 변환을 유지하면서 로컬 이미지 등장마다 고유 표식 문단을 넣는다. 업로드한 이미지를 표식 바로 뒤에 삽입하고 확인 후 표식을 삭제한다. 파일 계획·검증은 `notion_images.py`, 진행 기록·재개·완료 처리는 `notion_sync.py`로 분리하고 기존 `notion.py`에 HTTP 원시 기능을 추가한다.

**Tech Stack:** Python, urllib.request, dataclasses, hashlib, json, unittest.mock, pytest. HTTP·일반 실행은 표준 라이브러리만 사용한다. 원격 이미지가 재인코딩된 경우의 픽셀 비교에는 이미 개발 의존성에 있는 Pillow를 선택적으로 사용한다.

**Spec:** 이 문서의 §승인 설계. 2026-10-25 채팅에서 승인한 grill-yourself 설계를 실행에 필요한 인터페이스와 검증 절차로 구체화했다. 계획 작성 단계에서는 구현·원격 쓰기를 실행하지 않는다.

## Global Constraints

- “기존 노션 페이지와 사용자가 편집한 내용은 보존합니다.” 새 작업이 만든 페이지의 작업 소유 표식·이미지만 변경한다.
- “원본 파일은 수정하지 않습니다.” 상대경로는 보고서 파일의 폴더 기준으로 해석한다.
- “토큰과 서명 URL은 기록하지 않습니다.” 인증은 `NOTION_TOKEN`에서만 읽고, 이미지 다운로드 요청에 Notion Bearer 헤더를 전달하지 않는다.
- API 버전 `2026-03-11`. 삽입은 `position={"type":"after_block","after_block":{"id": marker_id}}`를 사용한다. paragraph→image 타입 변경을 가정하지 않는다.
- PNG/JPEG, 본문 최상위 독립 이미지 줄을 지원한다. 코드 펜스 속 문법은 무시하고, 표 셀·목록·인용·HTML·인라인 로컬 이미지는 쓰기 전에 명시적으로 거절한다. 외부 HTTPS 이미지는 유지한다.
- single_part 상한은 20 MiB 이하. 워크스페이스의 더 낮은 제한으로 API가 거절하면 파일명·크기·API 오류를 보고하며 완료 처리하지 않는다. 자동 압축하지 않는다.
- 원격 상태가 불명확하면 쓰기를 무조건 재시도하지 않는다. 완료 이력과 baseline은 이미지·본문 검증을 모두 통과한 뒤에만 확정한다.
- 실험07 이상 경로는 `config.artifact_path`; 기존 레코드의 `history_source`, `notion.history_path`, 문서 제목·버전 규칙을 유지한다.
- 라이브 검증은 시험 전용 페이지와 로컬 작업 폴더를 사용하고 실제 보고서 `output/notion.json`에는 쓰지 않는다. 기존 페이지를 수정·삭제하지 않고 시험 페이지도 자동 삭제하지 않는다.

## Review Focus

1. 공백·한글·괄호·퍼센트 인코딩·이스케이프가 있는 경로와 코드 속 가짜 이미지: 올바른 파일만 읽거나 명확히 거절해야 한다. Task 1 테스트.
2. 같은 파일·같은 캡션의 연속 등장, 문서 첫·끝 이미지: 개별 등장과 정확한 본문 경계를 구분해야 한다. Task 3 테스트.
3. 쓰기는 성공했으나 응답이 유실되거나 로컬 저장 전에 종료: 원격 파일 내용으로 확인하고 중복 없이 재개해야 한다. Task 4, 6 테스트.
4. 재개 전에 원본 이미지·보고서·원격 본문이 변경되거나 같은 종류 업로드가 동시 실행됨: 자동 변경을 중단해야 한다. Task 4 테스트.
5. 블록이 100개를 넘거나 다운로드 URL이 만료되고 파일이 재인코딩됨: 페이지네이션·URL 재조회·픽셀 비교를 수행하고 검증 불능을 성공으로 처리하지 않아야 한다. Task 2, 3 테스트.

## 승인 설계

- 자동화 대상은 예비·결과보고서의 본문 이미지이며 PDF 내보내기·페이지 레이아웃은 범위 밖이다. 이전 페이지의 소급 보정도 하지 않는다.
- `![설명](../결선도/그림.png)`에서 설명을 정확한 일반 텍스트 캡션으로 사용한다. 빈 캡션도 원본 그대로 유지한다. Markdown title 속성은 지원하지 않고 사전 오류로 낸다.
- 이미지 등장별 목록을 만들고 작업 ID+등장 번호 표식으로 치환한다. 표식은 반드시 독립 문단 하나로 보존되어야 한다.
- 새 페이지 생성 → 표식/부모/형제 경계 발견 → 이미지 업로드 → uploaded 확인 → 표식 뒤 삽입 → 삽입 검증 → 표식 삭제 → 전체 이미지/본문 검증 → baseline·완료 이력 순서다.
- 위치는 같은 절인지가 아니라 원격 부모와 앞뒤 비이미지 본문 블록 사이의 정확한 이미지 구간·등장 순서로 판단한다. 동일 캡션은 식별자가 아니다.
- 내용은 바이트 SHA-256을 우선 비교하고 다르면 Pillow로 크기와 EXIF 방향을 반영한 RGBA 픽셀을 비교한다. 의존성이 없거나 픽셀도 다르면 검증 실패다. 픽셀 비교 통과가 파일 바이트 동일성을 의미하지 않도록 결과 종류를 기록한다.
- 중간 페이지는 미완료 작업으로 남는다. 업로드 ID·블록 ID·페이지 ID·해시·캡션·경계·상태만 진행 기록에 저장한다. 원격 조회 응답 전체를 저장하지 않는다.
- 사용자가 편집한 이후의 pull은 기존 baseline diff를 유지한다. 업로드 당시 위치 검증을 후속 사용자 편집을 금지하는 규칙으로 사용하지 않는다.

## 파일 구조와 인터페이스

- Modify `scripts/lab/notion.py`: 인증 HTTP, multipart 파일 전송, children 페이지네이션, 새 페이지 생성·기존 작업 소유 표식 삭제 원시 기능. 기존 공개 함수 호환 유지.
- Create `scripts/lab/notion_images.py`: 이미지 문법 파싱·불변 계획·본문 경계·이미지 내용 비교. 이력 관리 금지.
- Create `scripts/lab/notion_sync.py`: 계획 실행, 원자적 journal, 동시 실행 잠금, 재개, baseline·완료 이력 확정, CLI.
- Modify `scripts/lab/validate.py`: 수동 첨부 info를 파일 사전 검사로 교체. 기존 `Finding`과 본문 검사 재사용.
- Modify `.claude/skills/sync-report-to-notion/SKILL.md`: 자동 삽입·검증·복구 명령. `.agents/skills/sync-report-to-notion`은 링크이므로 별도 복사 금지.
- Modify `.claude/과목정보.md`: 노션 업로드 안내에 자동 이미지 포함 설명. 비밀 값은 변경하지 않는다.
- Modify `scripts/lab/contact_sheet.py`: 수동 노션 첨부를 전제로 한 설명만 현재 동작에 맞춘다.
- Tests: 기존 `tests/test_lab_notion.py`, `tests/test_lab_validate.py`, 신규 `tests/test_lab_notion_images.py`, `tests/test_lab_notion_sync.py`, `tests/test_notion_image_skill.py`, `tests/test_notion_image_live.py`.
- Create `scripts/verify_notion_images.py`: 명시적으로 실행하는 라이브 시험·장애 주입 도구. 기본 테스트에서는 원격 쓰기 없음.
- Create `docs/verify/2026-10-25-notion-image-upload.md`: 실행 시각·코드 커밋·시험 페이지 URL·판정·복구 증거. 실제 실행일이 달라지면 날짜도 바꾼다.

### Task 1: 이미지 입력 계획과 사전 검사

**Files:** Create `scripts/lab/notion_images.py`, `tests/test_lab_notion_images.py`; Modify `scripts/lab/validate.py:1540`, `tests/test_lab_validate.py`.

**Interfaces:**
- `ImageOccurrence` frozen dataclass: `index:int`(0부터), `line:int`(1부터), `path:Path`, `caption:str`, `sha256:str`, `content_type:str`, `marker:str`.
- `ImagePlan` frozen dataclass: `operation_id:str`, `source:Path`, `source_sha256:str`, `markdown:str`(표식 치환 본문), `images:tuple[ImageOccurrence,...]`.
- `plan_images(source:Path, *, operation_id:str, body:str|None=None)->ImagePlan`. 원본 전체 해시와 전송 본문을 구분한다. frontmatter는 기존 parser로 제거하며 제목 제거는 상위 호출자가 처리한다.
- `check_notion_markdown(md_path)->list[Finding]` 호환 유지. 계획의 경로/형식 오류를 error Finding으로 변환한다.

- [ ] **Step 1: 실패 테스트 작성.** `test_plan_relative_path_and_caption`은 한글·공백·괄호 파일로 `assert plan.images[0].path == image.resolve()`, `assert plan.images[0].caption == '결선도 (정상)'`, `assert source.read_bytes() == before`를 검증한다. `test_duplicate_occurrences`는 같은 파일 두 번에 `assert len(plan.images)==2`, `assert markers[0]!=markers[1]`를 검증한다. `test_fenced_example_is_not_uploaded`은 백틱/물결 펜스의 가짜 경로가 오류를 만들지 않고 이미지 목록도 비어 있음을 검증한다. `test_reject_unsupported_or_missing_image`는 표·목록·인라인·HTML·title 속성·깨진 문법·없는 파일·잘못된 파일 시그니처·20 MiB 초과에 `pytest.raises(notion.NotionError)`를 검증한다. 퍼센트 인코딩과 escaped 괄호를 해석하고 지원하지 않는 문법은 원격 쓰기 전 거절하는 사례를 추가한다. 외부 HTTPS 이미지 보존과 빈 캡션도 검증한다.
- [ ] **Step 2:** `.venv/bin/python -m pytest -n0 tests/test_lab_notion_images.py -q` → 신규 함수 부재로 FAIL 확인.
- [ ] **Step 3:** 위 dataclass·파서를 구현한다. 정규식 하나로 모든 Markdown을 추측하지 말고 코드 펜스와 escaped/balanced 괄호를 구분한다. PNG/JPEG의 실제 시그니처를 확인한다. validate의 기존 표·본문 검사는 유지하고 자동 첨부 사전 검사를 연결한다.
- [ ] **Step 4:** `.venv/bin/python -m pytest -n0 tests/test_lab_notion_images.py tests/test_lab_validate.py -q` → PASS. 기존 손수 첨부 info 테스트는 새 명세로 수정하되, 이전 baseline의 빈 그림 검출 테스트는 유지한다.
- [ ] **Step 5:** 변경된 네 파일만 stage하고 `git commit -m 'feat: plan local images for Notion report uploads'`.

### Task 2: Notion 파일·블록 API와 표식 실측 관문

**Files:** Modify `scripts/lab/notion.py`, `tests/test_lab_notion.py`; Create `scripts/verify_notion_images.py`(처음에는 probe 명령만).

**Interfaces:**
- `create_file_upload(path:Path, token:str)->dict`, `send_file_upload(upload_id:str, path:Path, token:str)->dict`, `retrieve_file_upload(upload_id:str, token:str)->dict`.
- `list_children(block_id:str, token:str)->list[dict]`(모든 cursor 처리), `append_after(parent_id:str, after_id:str, blocks:list[dict], token:str)->list[dict]`, `archive_block(block_id:str, token:str)->None`.
- `read_block_tree(page_id:str, token:str)->list[dict]`: 조회 응답에만 `_children`을 붙인 트리 반환. 서명 URL은 메모리에서만 유지.
- `python -m scripts.verify_notion_images probe --work-dir <absolute-path>`: config의 부모 아래 시험 페이지 생성; Markdown 표·수식·한글 표식 두 개·연속 표식·처음/끝 표식을 실측한다.

- [ ] **Step 1: 실패 테스트 작성.** `test_upload_multipart_file_field`는 multipart에 `name="file"`과 실제 바이너리·정확한 MIME·버전 헤더가 있음을 검증한다. `test_append_uses_position_after_block`은 `assert payload['position']=={'type':'after_block','after_block':{'id':'MARKER'}}`를 검증한다. `test_list_children_all_pages`는 `has_more=True`인 응답 뒤 next_cursor가 요청되고 양쪽 결과가 모두 반환됨을 검증한다. `test_non_uploaded_status_rejected`와 만료 업로드 조회, HTTP 오류의 토큰 비노출 테스트를 추가한다.
- [ ] **Step 2:** `.venv/bin/python -m pytest -n0 tests/test_lab_notion.py -q` → 새 원시 기능 테스트 FAIL 확인.
- [ ] **Step 3:** 위 원시 기능과 probe를 구현한다. 이미지 캡션 rich_text는 문자열을 1900자 단위로 나누고 읽을 때 합친다. list_children은 빈 cursor 반복을 오류 처리한다. 자동 쓰기 재시도는 추가하지 않는다. probe는 페이지 ID와 각 쓰기 예정 작업을 먼저 로컬 기록한다.
- [ ] **Step 4:** `.venv/bin/python -m pytest -n0 tests/test_lab_notion.py -q` → PASS.
- [ ] **Step 5: 실제 관문 실행.** `NOTION_TOKEN`은 존재 여부만 확인한다. `/tmp/notion-image-probe-<uuid>`에 작업 폴더를 만들고 `.venv/bin/python -m scripts.verify_notion_images probe --work-dir <path>` 실행. 표식이 독립 문단 한 개씩 되고 같은 부모에서 삽입·삭제 후 순서와 한글 캡션이 보존되는지 확인한다. 삽입한 원격 이미지 바이트도 원본과 비교한다. 페이지 URL·ID·각 판정을 비밀 없이 기록한다. 실패하면 Task 3 이후 실전 경로 구현을 강행하지 않고 실패 근거를 보고하며 설계를 재검토한다.
- [ ] **Step 6:** 원시 기능·테스트·probe만 stage하고 `git commit -m 'feat: add Notion file upload and positioned block APIs'`.

### Task 3: 본문 위치·캡션·원본 내용 검증

**Files:** Modify `scripts/lab/notion_images.py`, `tests/test_lab_notion_images.py`.

**Interfaces:**
- `ImagePlacement` dataclass: `index:int`, `marker_id:str`, `parent_id:str`, `before_id:str|None`, `after_id:str|None`, `block_id:str|None`. before/after는 연속 이미지 구간 바깥의 비표식 본문 경계이며 None은 문서 경계다.
- `locate_markers(plan:ImagePlan, tree:list[dict])->list[ImagePlacement]`: 고유한 독립 문단 일치만 허용. 누락·중복·다른 구조면 오류.
- `verify_placements(plan:ImagePlan, placements:list[ImagePlacement], tree:list[dict], *, markers_allowed:bool=False)->list[Finding]`: 모든 등장·블록 타입·부모·경계·순서·캡션·표식 잔존 검사. 외부 링크 이미지는 계획된 로컬 이미지 ID와 혼동하지 않는다.
- `verify_image_content(local_path:Path, url:str)->dict`: `{'ok':bool,'comparison':'sha256'|'pixels','source_sha256':str,'remote_sha256':str}`. URL은 반환/저장하지 않는다. 다운로드 오류 시 상위 계층이 원격 블록을 재조회하고 새 URL로 한 번 더 검증한다.

- [ ] **Step 1: 실패 테스트 작성.** `test_image_in_wrong_section_fails_with_correct_count`는 개수·캡션이 맞아도 잘못된 경계면 error임을 검증한다. `test_same_caption_adjacent_first_last_images`는 첫·끝·인접 등장 4개가 모두 유일하게 매핑됨을 검증한다. `test_caption_rich_text_join_exact`는 분할된 한글 캡션은 통과하고 끝 공백 변경은 실패함을 검증한다. `test_marker_missing_duplicate_or_merged_fails`, `test_swapped_or_missing_image_fails`, `test_external_image_not_counted_as_local`을 추가한다. `test_download_no_auth_header`, `test_reencoded_image_uses_pixels`, `test_changed_pixel_fails`, `test_missing_pillow_does_not_pass`를 추가한다.
- [ ] **Step 2:** `.venv/bin/python -m pytest -n0 tests/test_lab_notion_images.py -q` → 신규 검증 테스트 FAIL 확인.
- [ ] **Step 3:** 인터페이스대로 구현한다. 연속 표식은 하나의 이미지 구간으로 묶어 양쪽 비이미지 경계와 구간 내 순서를 검증한다. 삽입 전 기록한 비소유 블록의 순서·본문 내용 fingerprint도 유지해 다른 문단 변경을 감지한다. 서명 URL은 오류 문자열에서도 제거한다.
- [ ] **Step 4:** `.venv/bin/python -m pytest -n0 tests/test_lab_notion_images.py -q` → PASS.
- [ ] **Step 5:** 두 파일만 stage하고 `git commit -m 'feat: verify Notion image placement captions and content'`.

### Task 4: 진행 기록·재개·완료 확정

**Files:** Create `scripts/lab/notion_sync.py`, `tests/test_lab_notion_sync.py`; 필요 시 Modify `scripts/lab/notion.py`의 이력 쓰기를 원자적으로 변경하되 공개 시그니처 유지.

**Interfaces:**
- `sync_report(source:Path, parent_id:str, token:str, *, kind:str, title:str, work_dir:Path, output_dir:Path)->dict`.
- `resume_report(journal_path:Path, token:str)->dict`. 두 함수 반환은 `{'operation_id':str,'page_id':str,'url':str,'version':int,'status':'complete','baseline':str,'image_count':int}`. 실패 시 `NotionError`에 journal 경로와 현재 상태만 전달한다.
- CLI: `python -m scripts.lab.notion_sync push --source <path> --kind <예비보고서|결과보고서>` 및 `resume --journal <path>`. 일반 push는 config에서 부모·제목을 읽고 `<output>/.notion-sync/<operation_id>/journal.json`을 사용한다.
- journal schema `notion-image-sync/v1`: source/body/image hashes, operation/version/page IDs, planned intent와 완료한 단계, 표식·이미지·경계·비소유 블록 fingerprint. 원자적 temp→os.replace 저장. 정규화된 output 경로+kind로 exclusive lock; 동시 작업 거절, stale lock은 살아 있는 소유 프로세스를 확인해 명시적 resume 때만 인수한다.

- [ ] **Step 1: 실패 테스트 작성.** `test_sync_finalizes_only_after_all_checks`는 위치/내용 실패 시 `assert not notion.load_records(output)` 및 `assert not baseline.exists()`를 검증한다. `test_resume_after_successful_insert_lost_response`는 서버에 반영된 image 응답을 끊고 재개 후 `assert remote_image_count == planned_count`, `assert create_page_calls == 1`를 검증한다. `test_resume_after_marker_archive`, `test_resume_baseline_failure`, `test_resume_record_written_before_journal`, `test_source_or_remote_edit_conflict`, `test_concurrent_kind_rejected`를 추가한다. 페이지 생성 응답 유실은 임시 제목의 작업 ID로 부모 children 전체를 조회해 유일한 페이지와 본문 표식을 확인하며, 0개/복수개면 새 페이지를 만들지 않는 테스트를 작성한다. 업로드/send 응답 유실과 만료 upload ID 재생성도 검증한다.
- [ ] **Step 2:** `.venv/bin/python -m pytest -n0 tests/test_lab_notion_sync.py -q` → 신규 함수 부재로 FAIL 확인.
- [ ] **Step 3:** state machine을 구현한다: `planned → page_created → markers_located → inserting → verified → baseline_written → record_written → complete`. 작업 버전은 잠금 아래 예약하고 미완료 작업이 있으면 같은 kind 새 작업을 거절한다. 임시 페이지 제목은 `<title> v<N> [sync:<operation_id>]`, 마지막에 정상 제목으로 바꾸며 이 단계도 journal에 기록한다. 원격 삽입 결과가 file 형태여서 upload ID가 사라질 수 있으므로, 표식과 경계 사이의 후보를 캡션+파일 내용으로 대조해 유일할 때만 복구한다. 없는 후보는 재삽입 가능하나 모호하면 중단한다. 아직 첨부하지 않은 만료 upload만 새로 만들고 이미 첨부된 블록은 유지한다. baseline 저장 후 기존 완료 레코드의 page_id를 검사해 중복 append를 방지한다. 이력 파일 쓰기도 원자적으로 한다.
- [ ] **Step 4:** `.venv/bin/python -m pytest -n0 tests/test_lab_notion.py tests/test_lab_notion_images.py tests/test_lab_notion_sync.py tests/test_lab_validate.py -q` → PASS. 기존 레코드·history_source·이미지 없는 보고서·서명 제거 동작 회귀도 포함한다.
- [ ] **Step 5:** Task 4 대상 파일만 stage하고 `git commit -m 'feat: resume and finalize verified Notion report uploads'`.

### Task 5: 스킬의 실행·되읽기·복구 안내 연결

**Files:** Modify `.claude/skills/sync-report-to-notion/SKILL.md`, `.claude/과목정보.md`, `scripts/lab/contact_sheet.py`; Create `tests/test_notion_image_skill.py`.

**Interfaces:** Task 4의 push/resume CLI를 스킬의 유일한 업로드 진입점으로 사용한다. 기존 `pull_markdown`, `check_pulled_images`, baseline diff는 유지한다.

- [ ] **Step 1: 실패 테스트 작성.** `test_skill_uses_verified_push_and_resume`는 스킬에 `scripts.lab.notion_sync push`, `resume --journal`, 이미지 위치·캡션 검증 및 성공 전 baseline 금지 안내가 있음을 검증한다. `test_no_mandatory_manual_attachment_instruction`은 자동 첨부 금지/항상 직접 넣기 문구가 제거됐음을 검증한다. `test_legacy_pull_still_checks_missing_images`는 기존 페이지의 빈 그림 검사를 보존했음을 검증한다. `.agents`와 `.claude` 경로가 같은 실제 파일을 가리키는 것도 확인한다.
- [ ] **Step 2:** `.venv/bin/python -m pytest -n0 tests/test_notion_image_skill.py -q` → FAIL 확인.
- [ ] **Step 3:** 절대 규칙 3, push 2·4·4b·5·6, pull 8b, 비목표를 새 동작으로 통일한다. 수동 append_record/baseline 예시는 새 CLI로 대체한다. 완료 보고는 URL·버전·이미지 수·위치/캡션/내용 판정·본문 왕복 검사 결과를 포함한다. 후속 pull에서 사용자가 바꾼 그림을 업로드 시점의 고정 배치로 되돌리지 않는다. 과목정보와 contact_sheet의 오래된 설명도 고친다.
- [ ] **Step 4:** `.venv/bin/python -m pytest -n0 tests/test_notion_image_skill.py tests/test_skill_docs.py tests/test_lab_notion.py tests/test_lab_notion_sync.py -q` → PASS.
- [ ] **Step 5:** 해당 파일만 stage하고 `git commit -m 'docs: route lab report sync through verified image uploads'`.

### Task 6: 실제 Notion 시험 페이지와 실패 복구 인수 검증

**Files:** Extend `scripts/verify_notion_images.py`; Create `tests/test_notion_image_live.py`, `docs/verify/2026-10-25-notion-image-upload.md`.

**Interfaces:**
- `python -m scripts.verify_notion_images acceptance --work-dir <absolute-path>`: 시험용 source/output과 PNG/JPEG fixtures 생성, 실제 config 부모 아래 전용 페이지 사용. 실제 보고서 이력은 변경하지 않는다.
- 라이브 도구 내부 HTTP wrapper가 실제 서버 성공 응답을 받은 뒤 호출자에게 `URLError`를 던져 응답 유실을 주입한다. production sync에 공개 failpoint 옵션은 넣지 않는다. 별도 worker 프로세스는 지정 journal 상태 도달 후 종료해 crash도 재현한다.
- `tests/test_notion_image_live.py`는 `NOTION_IMAGE_LIVE=1`과 `NOTION_IMAGE_LIVE_WORKDIR`가 명시됐을 때만 실행한다. 평소에는 `pytest.skip`한다. pytest-xdist 병렬 실행 금지(`-n0`).

- [ ] **Step 1: 실패 테스트 작성.** 먼저 fake transport로 `test_harness_drops_response_after_remote_success`를 작성해 remote write 1회 후 예외가 발생함을 검증한다. 라이브 acceptance 테스트는 결과 JSON에 `happy_path`, `insert_response_lost`, `archive_response_lost`, `process_crash`, `baseline_failure`, `wrong_location_detected`, `caption_mismatch_detected`, `content_mismatch_detected`, `page_create_response_lost`, `no_duplicate_pages_or_images`, `no_secret_persistence`가 모두 `pass`인지 assert한다. 기록 부재를 pass로 취급하지 않는다.
- [ ] **Step 2:** 라이브 환경변수 없이 harness unit test를 실행해 신규 로직 부재 FAIL 확인; 라이브 케이스는 SKIP여야 한다.
- [ ] **Step 3:** 시험 도구를 구현한다. 첫·끝·연속 이미지, 같은 파일/캡션 반복, 서로 다른 PNG/JPEG, 한글 긴 캡션, 표·수식, 100개 초과 블록을 포함한다. 정상 실행·별도 장애 시나리오를 각각 작업 ID로 구분한다. 위치/캡션/내용 오류는 시험 소유 이미지에만 주입하고 검증 실패를 확인한 뒤 원래 상태로 복구·재검증한다. 업로드 만료는 실제 한 시간 대기 대신 unit test로 검증하며 라이브 실측이라고 표시하지 않는다. 만료 다운로드 URL도 unit test로 검증한다.
- [ ] **Step 4:** 단위 회귀 실행: `.venv/bin/python -m pytest -n0 tests/test_lab_notion.py tests/test_lab_notion_images.py tests/test_lab_notion_sync.py tests/test_lab_validate.py tests/test_notion_image_skill.py tests/test_notion_image_live.py -q` → unit PASS, live SKIP.
- [ ] **Step 5: 라이브 인수 실행.** 새 `/tmp/notion-image-acceptance-<uuid>`에서 `NOTION_IMAGE_LIVE=1 NOTION_IMAGE_LIVE_WORKDIR=<path> .venv/bin/python -m pytest -n0 tests/test_notion_image_live.py -q` → 라이브 PASS. 장애별 resume 전후 같은 page_id/version·예정 이미지 개수·caption·경계·baseline 하나·완료 레코드 하나를 확인한다. page-create 응답 유실은 유일한 작업 페이지를 재발견하고 두 번째 페이지를 생성하지 않아야 한다. 권한/인증 실패는 원인과 미검증 항목을 기록하고 실제 검증 완료로 주장하지 않는다.
- [ ] **Step 6: 증거 문서 작성.** 실제 실행 일시(KST), 커밋, 실행 명령, 페이지 URL·ID, 시나리오별 기대/실측/판정, 이미지 hash·block ID·본문 경계·caption 검증 결과, 복구 전후 개수와 동일 page_id를 기록한다. 토큰·서명 URL·raw API response는 저장하지 않는다. 시험 페이지는 검증 완료/실패 제목과 URL을 남겨 사용자가 확인할 수 있게 한다. 일반 보고서 이력이 바뀌지 않았음도 확인한다.
- [ ] **Step 7: 자체 대조.** 모든 승인 설계 요구를 Task 1~6에 대응시키고 `git diff --check` 및 `git diff --stat`로 범위 확인. 병합/push를 진행한다면 저장소 지침대로 `.venv/bin/python -m pytest tests/ -q` 전체 테스트를 실행하고, 실패는 이번 변경과의 관련성·기존 실패 여부를 구분한다. 네트워크 라이브 테스트는 명시적 환경변수 없이는 다시 실행되지 않아야 한다.
- [ ] **Step 8:** 시험 도구·테스트·비밀 제거 증거만 stage하고 `git commit -m 'test: verify live Notion image placement and recovery'`.

## 실행 순서와 완료 기준

Task 1 → Task 2(실제 표식 관문) → Task 3 → Task 4 → Task 5 → Task 6 순서다. 각 task의 FAIL→PASS는 실제 출력으로 확인한다. 기능 테스트 통과만으로 라이브 검증 통과를 대신하지 않는다.

완료는 다음 다섯 조건을 모두 만족한 때다: (1) 스킬이 새 CLI를 사용함, (2) 단위 회귀 통과, (3) 실제 시험 페이지에서 이미지 내용·정확한 위치·캡션 통과, (4) 응답 유실과 프로세스 중단 후 중복 없이 복구, (5) 검증 URL·결과·제한이 증거 문서에 남음. 계획 실행은 사용자 검토와 실행 방식 선택 후 시작한다.

## 계획 자체 검토

- 설계 대응: 입력/경로/원본 보존 Task 1; API/표식 실측 Task 2; 위치/캡션/내용 Task 3; 진행 기록/복구/이력/baseline Task 4; 스킬과 pull 호환 Task 5; 실제 원격 인수 Task 6.
- 인터페이스: ImagePlan→ImagePlacement→sync_report/resume_report→CLI로 연결되며 기존 push_markdown/append_record/pull_markdown 호출 호환을 유지한다.
- Review Focus 다섯 항목에 각각 소유 task와 검증 사례가 있다. 만료 upload·서명 URL은 unit test이며 라이브 결과와 구분한다.
- 미검증 전제: 표식 문단 보존은 Task 2 라이브 관문에서 확인한다. 승인 없이 대체 Markdown converter를 구축하는 것으로 범위를 넓히지 않는다.
