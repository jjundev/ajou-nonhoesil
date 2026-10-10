# 회로 사용 동기 도입부 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 기존 실험01~05와 향후 실험설명에서 회로가 필요한 이유를 초반에 설명한다.

**Architecture:** 기존 `t-start` 안에 동기를 저작하고 공통 저작 규칙에 반영한다. 실험04·05의 생성 코드와 보존 fragment를 동기화한다. 실험01~03의 저작 원본 부재와 기존 본문 보존을 고려해 5개 발행본의 복사 stage에서 도입부만 갱신하고 기존 MD 변환기·검사기·publish를 재사용한다. 새 manifest 스키마나 런타임 기능은 추가하지 않는다.

**Tech Stack:** Python 3, pathlib, 기존 HTMLParser/MD 변환기, pytest, 기존 학습팩 CLI, 브라우저.

**Spec:** [2026-10-10-circuit-motivation-design.md](../specs/2026-10-10-circuit-motivation-design.md)

## Global Constraints

- 적용 대상은 `복습노트/실험01~05/`의 실험설명 HTML·MD와 해당 저작 원본, 앞으로 사용할 저작·검증 규칙이다.
- 설명 순서: 해결할 문제 → 회로가 필요한 이유 → 작은 입력·출력 예 → 이번 실험과 연결.
- 새 동기 설명은 약 2~4개 짧은 문단, 다정한 ‘~해요’체로 쓴다. 정의·성립 조건·인과는 줄이지 않는다.
- 첫 토픽 ID `t-start`를 유지하고 제목은 `왜 이 회로를 쓰는지 먼저 알아봐요`로 통일한다.
- 이해를 위한 상황은 `이해를 위한 예시`로 표시하고 교안의 실제 수행 조건과 구분한다. 교안 밖 설명은 `보충`으로 표시한다.
- `t-start` 이외 토픽의 본문·IDs, 읽음 저장 키, 기출문제·풀이·문제은행·그림·원문 증거를 보존한다.
- HTML과 MD는 같은 내용으로 만들고 출처는 manifest 기반으로 MD에 생성한다.
- 보고서·원자료·영상·새 위젯·화면 디자인 변경은 범위 밖이다.
- 계획 작성 턴에서는 문서만 저장했고, 이후 사용자의 직접 구현 승인으로 실행했다. 관련 없는 기존 변경을 보존하고 검증한 작업만 커밋한다. push는 포함하지 않는다.

## Review Focus

1. 실험01~03 저작 원본 부재: 현재 발행본의 비도입 본문과 기출 자료가 바뀌지 않아야 한다(Task 2 보존 테스트).
2. 실험04·05 생성 코드 재실행: 새 도입 문장과 제목이 옛 값으로 돌아가지 않아야 한다(Task 2 저작 원본 동기화 테스트).
3. 활성 Low·one-hot·수행 제외 항목: 이상 모델의 예를 실제 칩·수행 조건으로 오해하지 않아야 한다(Task 2 내용 검산).
4. HTML/MD/요약/목차: 새 내용과 제목이 일치하고 기존 hash·읽음 키가 유지되어야 한다(Task 2 stage 비교와 Task 3 브라우저 검증).
5. 원자료·사용자 파일 충돌·묵은 검증 상태: 현재 해시나 보존 조건 실패 시 발행을 중단하고 기존 팩을 유지해야 한다(Task 3 기존 publish 테스트와 실제 stage 사전검사).

---

## 파일 구조

| 파일 | 책임 |
|---|---|
| `.claude/skills/logic-lab-review-pack/SKILL.md` | 앞으로 만드는 노트에 동기 도입 요구 |
| `.claude/skills/logic-lab-review-pack/references/authoring.md` | 네 단계·분량·예시/보충 경계 |
| `.claude/skills/logic-lab-review-pack/references/verification.md` | 동기·입출력 예·실험 연결 검토 |
| `docs/learning-pack-source/실험01/sections/t-start.html` 및 `실험02`, `실험03` 동일 경로 (신규) | 복원·개선한 첫 토픽 fragment 보존 |
| `docs/learning-pack-source/실험04/refresh_note.py`, `실험05/sections.py` | 재생성 가능한 본문·제목 |
| `docs/learning-pack-source/실험04/sections/t-start.html`, `실험05/sections/t-start.html`, 각 `manifest.json` | 갱신한 저작 내용·제목·근거 |
| `docs/learning-pack-source/refresh_motivation.py` (신규) | 기존 팩을 새 stage에 복사하고 도입부만 갱신하는 작업용 CLI |
| `tests/test_review_pack_motivation_refresh.py` (신규) | 도입부 교체 범위와 기존 자료 보존, 원본 동기화 |
| `복습노트/실험NN/실험NN_실험설명.html`, `.md`, `자료/manifest.json` (NN=01~05) | 검증 후 발행할 결과 |
| `docs/verify/logic-lab-review-pack-motivation.md` (신규) | 실제 확인한 대상·명령·검산·브라우저 결과 |

### Task 1: 앞으로 사용할 동기 저작·검토 규칙 확정

**Files:** Modify: 위 표의 `SKILL.md`, `references/authoring.md`, `references/verification.md`.

**Interfaces:** Consumes: Spec의 내용·보존 계약. Produces: 이후 저작자가 따르는 네 단계의 도입부 계약. 새 Python API는 없다.

- [x] **Step 1: 규칙의 모호함을 확인한다.** 현재 ‘동기’ 한 단어와 정의 위주의 도입부를 대조하고, 정의만 적은 문장은 새 계약을 만족하지 않는다는 반례를 검토 기록에 적는다. 문장 복사 여부를 검사하는 테스트는 만들지 않는다.
- [x] **Step 2: 규칙을 갱신한다.** 첫 토픽 제목·2~4개 문단·네 단계·예시/보충 표시·실험 연결을 명시한다. 이미 있는 layer 순서와 요약·출처 계약을 유지한다. 부품 핀을 외우는 이유나 ‘시험에 나와요’만으로 동기를 대신하지 않게 한다.
- [x] **Step 3: 규칙의 판정 가능성을 확인한다.** Spec의 실험04 예시가 네 단계에 대응하는지, 실험02의 AC 제외와 실험05의 극성 경고를 유지할 수 있는지 읽어 확인한다.
- [x] **Step 4: 세 규칙 파일만 stage하여 커밋한다.** `git diff --check` 후 `docs: require circuit motivation in lab note introductions`. 이후 실행 선택에서 커밋을 제외하라는 사용자 지시가 있으면 그 지시를 따른다.

### Task 2: 5개 도입부 저작과 보존 가능한 stage 갱신

**Files:** Create/Modify: 위 표의 `docs/learning-pack-source/` 파일과 `tests/test_review_pack_motivation_refresh.py`.

**Interfaces:**
- Consumes: 발행본 `자료/manifest.json`, 첫 토픽 fragment, 기존 `html2md.export_document(path, export=True, note_metadata=None)`, `note_metadata.topic_metadata(manifest)`.
- Produces: 작업용 함수 `prepare_stage(pack: Path, fragment: Path, stage: Path) -> Path` in `docs/learning-pack-source/refresh_motivation.py`. 반환값은 새 stage 경로. 존재하는 stage, 첫 토픽 ID 불일치, 중복/누락 `t-start`는 `ValueError`; 원본 pack은 수정하지 않는다.
- CLI: `python docs/learning-pack-source/refresh_motivation.py --root . --stage-root tmp/motivation-<고유ID>`. 01~05를 고정 대상으로 하고 stage-root가 이미 존재하면 중단한다. 각 stage는 `<stage-root>/실험NN`이다.

- [x] **Step 1: 의미 있는 실패 테스트를 작성한다.** `test_stage_preserves_everything_except_intro`는 임시 pack에서 기출 HTML·MD·evidence·비도입 article의 바이트와 storage KEY를 비교한다. `test_source_pack_is_untouched`는 작업 전후 원본 파일 바이트가 같음을 검증한다. `test_unsupported_intro_aborts`는 0개/2개 `article#t-start`와 존재하는 stage에 대해 ValueError를 확인한다. `test_html_md_title_and_id_agree`는 새 제목과 도입 내용이 HTML/MD에 있고 `t-start`가 한 번씩 존재하며 다른 토픽 ID가 그대로임을 확인한다.
- [x] **Step 2: RED를 확인한다.** `python -m pytest -o addopts='' tests/test_review_pack_motivation_refresh.py -q` → 신규 함수가 없어 실패해야 한다.
- [x] **Step 3: 도입부 5개를 저작한다.** 현재 교안과 첫 토픽을 읽는다. 01~03은 현재 HTML의 첫 article에서 h3를 제외한 fragment를 복원한다. 04·05는 보존 원본과 현재 발행본 차이를 먼저 확인하고 현재 내용을 기준으로 수정한다. Spec의 실험별 강조점을 2~4개 문단에 넣고, 기존 범위·주의 문단을 보존하며 sum에 필요성을 반영한다. 새 SVG는 만들지 않는다.
- [x] **Step 4: 재생성 원본을 동기화한다.** 04 `refresh_note.py`의 `text['t-start']`와 `titles[0]`, 05 `sections.py`의 `S['t-start']`와 `TOPICS` 첫 제목을 함께 수정한다. 각 저작 manifest의 첫 제목·필요한 `md_notes`를 갱신하고 기존 source ID·극성·판본 근거를 보존한다. 04 author()는 사본에서 실행하고 첫 fragment/title을 비교한다. 05는 sections 모듈의 S/TOPICS와 보존 fragment를 비교하는 `test_authoring_sources_keep_new_intro`를 추가한다. 전체 build_run은 문제은행 재저작 부작용이 있으므로 실행하지 않는다.
- [x] **Step 5: stage 준비 함수를 구현한다.** HTMLParser 위치 기반으로 첫 article의 정확한 범위만 교체한다(중첩 태그를 단순 정규식으로 자르지 않는다). 목차의 `#t-start` 링크 텍스트만 같은 제목으로 바꾸고 manifest 첫 제목·근거를 동기화한다. MD는 note에만 `export_document`와 `topic_metadata`로 재생성한다. 기출 MD를 재생성하지 않는다. 복사 stage의 checks를 모두 `not_run`으로 초기화하고 generated_files를 실제 stage 파일 목록으로 갱신한다. 원본 전체 해시를 재확인해 읽는 사이 변경이 생기면 중단한다.
- [x] **Step 6: GREEN과 내용 검산을 확인한다.** Step 2 명령과 `tests/test_review_pack_note_metadata.py`, `tests/test_review_pack_navigation.py`를 실행한다. 별도로 01 AND 조건, 02 히스테리시스(증가·감소 문턱의 순서와 사이 구간의 상태 유지), 03 `1+1=10`의 합/올림, 04 `I0=0,I1=1`에서 S별 출력, 05 one-hot 인코더의 유효 조건과 활성 High 예/실제 IC 극성 구분을 검토 문서에 남긴다. 숫자 문턱·측정값은 새로 만들지 않는다.
- [x] **Step 7: 검증한 저작 원본·작업용 CLI·테스트만 커밋한다.** 비도입 fragment 변화가 없는지 `git diff`로 확인하고 `feat: add circuit motivation to lab note sources`.

### Task 3: 검증한 5개 팩 발행

**Files:** Modify: 위 표의 5개 발행본. Create: `docs/verify/logic-lab-review-pack-motivation.md`.

**Interfaces:** Consumes: Task 2의 prepare_stage와 CLI. Produces: 기존 CLI로 검사·발행된 5개 팩과 실제 검증 기록. `scripts/lab/review_pack/publish.py`는 변경하지 않는다.

- [x] **Step 1: 사전검사와 보존 기준을 수집한다.** 각 현재 팩에 `python -m scripts.lab.review_pack check --folder 복습노트/실험NN`을 실행한다. 5개 전체 파일 목록·sha256·비도입 article·storage KEY·출처 해시를 RUN에 저장한다. `python -m pytest -o addopts='' tests/test_review_pack_publish.py -q`로 source hash/사용자 파일 충돌/검증 상태 거부의 기존 보호를 확인한다. 실패가 있으면 원인을 설명하고 기존 팩을 교체하지 않는다.
- [x] **Step 2: 새 stage 5개를 만든다.** Task 2 CLI를 새 고유 stage-root로 실행한다. 도입부 HTML/MD·manifest 외 자료의 해시가 기준과 같은지 확인한다. 새 검증 기록 파일을 추가할 때 generated_files도 실제 목록과 맞춘다.
- [x] **Step 3: 브라우저와 내용 검증을 수행한다.** 5개 모두 375px/1280px, 밝은/어두운 테마에서 첫 토픽·목차 제목·우측 요약·이전/다음·hash 직접 이동·읽음 상태를 확인한다. 깨진 이미지/수식 오류/잘린 본문은 0이어야 한다. 새 도입부의 예시가 본문 조건과 충돌하지 않는지 확인한다. 실제 확인한 결과로 checks를 갱신하며, 독립 검토를 하지 않았다면 independent는 `not_run` 또는 `self_review`로 남긴다.
- [x] **Step 4: 최종 stage를 검사한다.** 각 stage에 `python -m scripts.lab.review_pack check --folder <stage-root>/실험NN` → `OK (mechanical checks only)`. `python -m pytest -o addopts='' tests -k review_pack -q` → 실패 0; 환경/기존 실패가 있으면 그 범위와 발행 영향 판단을 기록한다. 검토 후 내용을 고쳤다면 관련 내용·화면 검증을 다시 한다.
- [x] **Step 5: 기존 publish로 발행한다.** 각 NN에 `python -m scripts.lab.review_pack publish --root . --stage <stage-root>/실험NN --experiment N`. 기본 backup 경로를 기록한다. 모두 stage 검증을 마친 다음 발행하며 중간 실패 시 이미 교체된 팩을 해당 backup에서 복구해 혼합 상태를 남기지 않는다. 사용자 파일 충돌·원자료 변경은 보호 검사를 우회하지 않는다.
- [x] **Step 6: 발행본과 최종 stage를 비교한다.** 생성 파일은 stage와 byte-identical이어야 한다. 원래 사용자 추가 파일은 유지되어야 한다. 각 발행본 check를 다시 실행하고 검증 문서에 실제 명령·결과·검산·백업·미해결 사항을 기록한다.
- [x] **Step 7: 최종 diff를 확인하고 요청 범위만 커밋한다.** `git diff --check`와 `git status --short` 후 수정한 5개 실험설명 HTML·MD·manifest, 새 검증 기록만 명시적으로 stage한다. backup·tmp·기존 unrelated 계획 파일은 제외한다. 커밋 메시지: `docs: publish motivated introductions for lab notes 01-05`.

## 계획 자체 검토

- 범위/첫 토픽/새 요약/문체/출처 경계: Task 1과 Task 2.
- 원본 동기화/현재 발행본 보존/HTML·MD 일치: Task 2.
- 입출력 예/수행 제외/극성/one-hot 조건: Task 2 Step 6, Task 3 Step 3.
- 5개 팩 브라우저·출처 해시·백업·검증 기록: Task 3.
- 새 런타임 API나 schema 변경은 없고 작업용 API는 prepare_stage 하나다. Review Focus 다섯 항목마다 위 검증을 배정했다. 문장의 고정 문자열 테스트 대신 자료 보존과 재생성 회귀를 검사한다.

## 실행 인계

권장 방식은 Native: 저작 규칙·5개 도입부·보존 검증의 연결이 단순하고 새 런타임 기능이 없으므로 같은 세션에서 직접 실행하는 편이 효율적이다. Subagent-driven을 선택하면 과업별 구현·독립 리뷰 절차를 사용한다. 선택과 계획 검토를 받은 뒤 실행 스킬을 읽고 구현한다. 모델 지정은 사용자가 별도로 요청하지 않은 한 상속하며 임의로 변경하지 않는다.
