# 독립 기출 문제은행 v1

문제은행은 원자료의 전사와 증거를 보존한다. 학습팩 `manifest.json`은 설명·개념 링크·독립 풀이·HTML 조각을 담는 별도 계약이다. import-bank로 새 저작 RUN을 만든 뒤 설명·독립 풀이를 저작하고 build한다.

형식 정본은 [question-bank.schema.json](question-bank.schema.json), 의미 규칙은 [설계](../../../../docs/superpowers/specs/2026-09-29-question-bank-extraction-design.md)와 [검증기](../../../../scripts/lab/review_pack/question_bank.py)다. [최소 fixture](../../../../tests/fixtures/review_pack/question_bank/minimal.json)는 문항이 없는 형식 예제이며 실제 기출이 아니다.

## 명령과 저장

저장소 루트에서 실행한다. 두 명령은 파일을 쓰거나 상태를 변경하지 않는다.

```powershell
python -m scripts.lab.review_pack.question_bank_cli inventory --root . --experiment 4
python -m scripts.lab.review_pack.question_bank_cli check --root . --bank 문제은행/실험04/question-bank.json
```

- inventory 출력: `experiment`, `sources`. 대상 퀴즈 폴더의 모든 파일을 재귀 목록화한다. 미지원 확장자도 `other`로 남긴다. 없는/빈 폴더, 링크, 접근 오류는 실패다.
- inventory는 판독 전 자료 목록이다. `processing=pending`, PDF `unit_count=null`을 반환한다. 은행에 넣을 때 실제 페이지 수와 감사 결과를 기록한다. 페이지 수를 확인하지 못했으면 `held`와 이유를 기록한다.
- check 출력: `mechanical_check`, `audit_status`, `recorded_source_visual`, `counts`. counts는 sources/occurrences/unique_questions/past/predicted/unknown/unreadable/partial/candidate_relations/unresolved다.
- 성공 종료 코드 0, 자료·JSON·검사 오류 1(stderr의 FAIL), 명령 사용 오류 2. JSON 출력은 UTF-8이다.
- `mechanical_check=pass`는 기록된 원문 판독 상태의 진실성이나 정답을 보증하지 않는다. 검사기는 `audit.checks`를 자동 갱신하지 않는다.

작업은 `tmp/question-bank/실험04-<고유실행ID>/`에서 한다. 감사 완료 후 `문제은행/실험04/`에 `question-bank.json`, `assets/`, `검증결과.md`를 저장한다. 기존 폴더는 자동으로 덮어쓰지 않는다.

## 공통 규칙

최상위 키는 schema=`logic-lab-question-bank`, schema_version=1, bank_id, experiment(정수 1~10), sources, assets, occurrences, questions, relations, audit. 선언되지 않은 키는 거부한다. HTML fragment/topics/derived_answer/answer_status는 사용하지 않는다.

같은 JSON 객체 안의 중복 키는 값이 같더라도 거부한다. 중첩된 문제 본문에도 적용하며 마지막 값으로 원문 조건을 덮어쓰지 않는다.

ID는 영문자로 시작하고 영문·숫자·하이픈·밑줄만 허용한다. source/asset/occurrence/question/block/subpart 전체에서 유일하다. 재정렬과 전사 교정은 기존 ID를 유지하고 실질적 문제 조건 변경은 새 ID와 variant_of로 남긴다. ID를 배열 위치나 문제 텍스트 해시에서 재발급하지 않는다.

source.path는 저장소 상대, asset.path는 은행 폴더 상대 `assets/` 아래 POSIX 경로다. 절대 경로, 역슬래시, `..`, `.` 경로 요소, 빈 요소, 드라이브/스트림 구분자 및 링크를 허용하지 않는다. 파일의 SHA256을 소문자 64자리로 기록한다. 검증은 원문과 그림 모두의 파일 존재·경로·해시를 확인한다.

## 객체별 계약

모든 선언된 필드를 기록한다. 값이 없는 nullable 필드는 누락 대신 `null`을 쓴다.

### Location

`source_id`, `pdf_page`, `printed_page`, `locator`, `bbox`, `image_size`.

- PDF의 pdf_page는 실제 PDF 페이지를 1부터 센 정수이며 unit_count 이하다. 비PDF는 null이다. 인쇄 쪽수 printed_page는 별도 문자열 또는 null이다.
- locator는 비어 있지 않은 위치 설명이다. DOCX는 문단·표·셀, 이미지는 전체 이미지 등을 기록한다.
- bbox는 좌상단 기준 `[x0,y0,x1,y1]`, `0<=x0<x1<=1`, `0<=y0<y1<=1`. bbox가 있으면 기준 이미지의 `[너비,높이]` 양의 정수 image_size가 필요하다.
- 기준 이미지는 PDF 전체 페이지 렌더, 원본 이미지, 또는 DOCX locator가 식별하는 렌더 페이지다. 부분 크롭을 좌표 기준으로 쓰지 않는다.

### sources

`id`, `path`, `sha256`, `format`, `filename_metadata`, `observed_metadata`, `conflicts`, `processing`, `reason`, `unit_kind`, `unit_count`.

format은 pdf/docx/doc/image/text/other. 각 metadata는 `{year,term}`이며 값은 문자열 또는 null. 파일명과 원문 헤더를 각각 기록한다. 값이 다르면 conflicts에 `{field,filename_value,observed_value,location}`을 남긴다. 파일명만으로 기출 여부나 연도를 확정하지 않는다.

processing은 pending/complete/held. complete는 감사 단위 모두를 확인했다는 뜻이며 모든 문항을 읽었다는 뜻은 아니다. held는 reason과 audit.unresolved에 이유를 남긴다. PDF는 unit_kind=page와 페이지 수, 이미지는 image/1, 나머지는 document/1이다. PDF 페이지 수를 확인하지 못했으면 unit_count=null, processing=held로 기록한다.

### assets

`id`, `path`, `sha256`, `location`, `role`, `answer_exposure`.

role은 problem/answer/mixed, answer_exposure는 none/present/unknown. problem은 none만 허용한다. 정답 표시가 있는 이미지는 mixed 또는 answer로 보존한다. 답을 지우거나 회로를 새로 그린 뒤 원문 증거라고 표시하지 않는다. 새 교육용 그림은 후속 학습팩 저작 단계의 자산이다.

### occurrences 및 blocks

Occurrence는 원자료에 등장하는 각각의 문제·답안·해설이다. 필드는 `id`, `role`, `location`, `original_number`, `blocks`, `reading`, `uncertainties`다. role은 question/answer/explanation/mixed, reading은 readable/partial/unreadable. 원문 번호는 문자열 또는 null이다.

Block은 `id`, `type`, `text`, `tex`, `cells`, `asset_id`다. 배열 순서를 원문 순서로 유지한다.

| type | 필요한 값 | 나머지 |
|---|---|---|
| text | 비어 있지 않은 text | tex/cells/asset_id=null |
| math | 비어 있지 않은 tex, text에 설명/전사 | cells/asset_id=null |
| table | 비어 있지 않은 직사각형 문자열 cells | tex/asset_id=null |
| figure | 존재하는 asset_id, text에 그림 설명 | tex/cells=null |

partial/unreadable은 uncertainties가 필요하다. 각 항목은 `{block_id,symbol,candidates,reason,location}`이다. block_id는 해당 occurrence 안의 block 또는 null, candidates는 가능한 해석의 문자열 배열이다. 판독 불가 문제는 blocks가 비어 있어도 원문 위치와 이유를 보존한다. 해당 occurrence를 audit.unresolved에도 기록한다. 오버바·엣지·X/Z·활성 극성을 추측해 채우지 않는다.

uncertainties가 남아 있으면 readable을 사용할 수 없다. partial/unreadable과 unresolved로 보류를 기록한다. 원문 대조로 의문을 해결한 뒤 uncertainties를 비우고 관련 unresolved를 정리해야 readable 및 complete로 전환할 수 있다.

### questions 및 제공 답안

Question은 확인된 고유 문제 묶음이다. 필드는 `id`, `occurrence_ids`, `representative_occurrence_id`, `kind`, `classification_reason`, `evidence`, `subparts`, `answers`다.

occurrence_ids에는 question/mixed 등장만 넣으며 대표 ID도 그 안에 있어야 한다. 각 question/mixed 등장은 정확히 한 question에 속한다. kind는 past/predicted/unknown. 분류 이유와 원문 Location 배열 evidence를 반드시 남긴다. 추출 시 예상문제를 버리지 않으며, 학습팩에서 개념 공백에 따라 선별한다.

subparts 항목은 `{id,label,occurrence_id,block_ids}`. 해당 question의 occurrence와 그 block만 참조한다. 공통 지문·그림은 부모 question을 통해 참조하고 복제하지 않는다.

answers 항목은 `{occurrence_id,target_id,status,reason}`. occurrence는 answer/explanation/mixed, target은 해당 question 또는 소문항이다. status는 confirmed/candidate이고 **confirmed는 연결 확인이며 정답 확인이 아니다**. 서로 다른 제공 답안은 모두 남긴다. 아직 연결하지 못한 답안은 audit.unresolved에 이유를 남긴다.

### relations

각 항목은 `{from_id,to_id,type,reason,evidence}`.

- duplicate_candidate/variant_of: 서로 다른 question 사이의 무방향 관계. 같은 타입·같은 쌍을 중복 기록하지 않는다.
- answer_candidate: 답안/해설/mixed occurrence에서 question 또는 subpart로 향하는 후보 연결.
- 확정 중복은 관계 대신 한 question의 occurrence_ids에 묶는다. 문구만 비슷하거나 회로·극성·조건이 다른 문제는 자동 병합하지 않는다.

### audit

`status`, `checks`, `units`, `unresolved`.

checks는 `{structure:not_run/pass/fail, source_visual:not_run/partial/pass}`다. 구조 검사 결과와 실제로 수행한 시각 판독 범위를 직접 기록한다.

units 항목은 `{source_id,index,outcome,occurrence_ids,reason}`. PDF는 각 페이지, 비PDF는 문서/이미지 전체의 index=1을 감사한다. outcome은 questions/reference/blank/held. questions는 문제·답안·해설 등장 ID가 필요하고 reference/blank에는 등장 ID가 없다. held는 이유와 source를 대상으로 한 unresolved 항목이 필요하다. 페이지 수 미확인 PDF는 index=1의 held 항목으로 파일 전체를 표시한다.

여러 페이지에 걸친 문제는 각 페이지 units에 같은 occurrence를 연결한다. 대표 location 페이지에는 그 occurrence가 반드시 포함되어야 한다. 추가 페이지의 블록은 근거 자산으로 출처를 보존한다.

unresolved 항목은 `{target_id,reason}`이며 실제 source/asset/occurrence/question/block/subpart를 가리킨다. 집계는 CLI가 계산하므로 중복 저장하지 않는다.

| status | 의미와 조건 |
|---|---|
| draft | 진행 중. pending 자료와 미작성 감사 단위를 허용하나 잘못된 참조·형식은 허용하지 않음 |
| complete | 모든 자료·단위 감사, pending/held·미해결·부분 판독 없음, source_visual=pass |
| complete_with_holds | 모든 감사 시도 종료, pending 없음, 각 보류의 이유 기록, unresolved 최소 1개, source_visual=partial/pass |

완료 상태에는 sources가 필요하다. complete source는 draft에서도 모든 단위 감사가 필요하다. 판독 보류는 정직하게 남길 수 있으나 오류가 있는 JSON이나 draft를 최종 은행으로 발행하지 않는다.

## 학습팩 import

```powershell
python -m scripts.lab.review_pack import-bank --root . --bank 문제은행/실험04/question-bank.json --run tmp/review-pack/실험04-import-01
```

complete/complete_with_holds만 가져오며 기존 RUN은 덮어쓰지 않는다. draft·해시 불일치·입력과 겹치는 출력 경로는 거절한다.
RUN에는 바이트 동일 evidence/question-bank.json, 선언 자산 전체, authoring-index.json, 원문과_저작안내.md, 유효한 초기 manifest와 빈 저작 디렉터리를 만든다.
초기 checks는 모두 not_run이며 모든 문제는 held/독립 풀이 없음으로 시작한다. confirmed는 답안 연결 상태 그대로 보존한다.

authoring-index의 question별 원문 등장·소문항·답안·관계·보류·허용 자산은 고정이다. authoring_status(pending/reading_hold/ready/not_selected/held)와 selection_reason만 수정한다. ready는 검증 완료가 아니다.
모든 고유 문항을 manifest에 남기고 미수록·보류 이유를 기록한다. 새로운 practice는 별도 ID로 추가한다.
부분 판독 문항은 은행에서 해결 후 다시 import하며, 제공 답안에 대한 의문만 있는 readable 문항은 독립 풀이와 불일치를 공개하며 저작할 수 있다.

build는 로컬 증거와 원래 은행·원자료를 대조한다. check는 현재 폴더의 snapshot·asset·인덱스·문항 연결을 검사한다. publish는 현재 저장소의 원래 입력도 다시 검사한다.
원래 은행을 바꾼 경우 metadata.sha256만 수정해 과거 저작을 재사용하지 말고 새 import 후 변경된 문항을 재검토한다.
안전한 원문 그림은 role=problem/exposure=none이다. present/unknown 이미지의 문제 화면 사용은 파일명을 바꿔도 해시 검사로 거절된다. 원문·답안 증거는 details.original/solution에서 확인한다.
새 교육용 그림은 원문 증거가 아니며 후속 내용 검토 대상이다. 실제 HTML/MD 저작과 브라우저 검증은 import 다음 단계다.
