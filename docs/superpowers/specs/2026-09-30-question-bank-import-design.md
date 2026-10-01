# 문제은행 → 학습팩 import 연결 설계

## 승인과 작업 범위

2026-09-30 사용자가 대화에서 제시한 import 연결 설계에 “진행해”로 동의했다. 이 문서는 그 설계를 파일·인터페이스·검증 기준으로 구체화한다. 구현 방식은 기존 Native를 유지한다. 구현 시작 전 이 명세의 검토가 필요하다.

실험4 추출은 완료되어 있다. 입력은 문제은행/실험04/question-bank.json과 assets/이다. 최신 기준 커밋은 a6d937e이고 기존 워크트리 C:/Users/Hyunjun/.codex/worktrees/logic-lab-review-pack/논회실, 브랜치 codex/logic-lab-review-pack에서 진행한다.

이번 결과물은 import 명령과 기존 build/check/publish 연결이다. 설명·독립 풀이 저작, 실제 학습팩 발행, Task 8, 원래 체크아웃 통합은 이번 범위에 포함하지 않는다. 기존 tmp/review-pack-work/experiment04는 입력으로 사용하지 않는다.

## 목적

완료된 문제은행을 다시 추출하거나 제공 답안을 정답으로 가정하지 않고, 출처·모든 원문 등장·후보 답안·보류 정보를 가진 학습팩 저작 시작점으로 가져온다. 문제은행은 추출 계약, manifest는 교육 내용 저작 계약으로 유지한다.

흐름은 import-bank → 설명·독립 풀이·개념 연결 저작 → 기존 build/check → 내용·브라우저 검토 → publish다.

## 공통 제약

- Python 표준 라이브러리만 사용한다.
- 기존 실험4 문제은행·원문 자료·원문 자산은 수정하지 않는다.
- 문항 ID와 분류를 임의로 변경하거나 variant_of 문항을 자동 병합하지 않는다.
- 제공 답안의 confirmed/candidate는 연결 상태이며 정답 검증 상태가 아니다.
- 추출 검사 결과를 학습팩 content/independent/browser의 pass로 복사하지 않는다.
- 생명과학 note-template.html/review-template.html과 기존 출력 네 파일을 유지한다.
- 답 노출 present/unknown 자산을 답 없는 문제 본문에 자동 삽입하지 않는다.
- 기존 run/stage/최종 팩을 import에서 덮어쓰지 않는다.
- 문제은행 JSON의 정확한 바이트와 SHA256을 보존한다.
- JSON에 없는 풀이·개념·문제 조건을 import가 생성하지 않는다.

## 명령

저장소 루트에서 다음 명령을 제공한다.

```powershell
python -m scripts.lab.review_pack import-bank --root . --bank 문제은행/실험04/question-bank.json --run tmp/review-pack/실험04-import-01
```

bank는 저장소 내부 파일, run은 새 저작 디렉터리다. run이 존재하거나 입력 은행 폴더와 겹치면 실패한다. 심볼릭 링크·저장소 밖 입력·경로 탈출은 기존 question_bank_sources의 엄격한 경로 검사를 따른다.

초기 검사 실패 시 run을 생성하지 않는다. 구조 계약, 원문/자산 파일 해시를 검사한 뒤 입력 상태가 complete 또는 complete_with_holds인 경우만 import한다. draft는 거절한다. complete_with_holds의 보류는 그대로 가져오고 오류로 일괄 거절하지 않는다.

## import 산출물

run 아래에 다음을 생성한다.

| 경로 | 용도 |
|---|---|
| manifest.json | 기존 학습팩 형식의 유효한 저작 초안 |
| evidence/question-bank.json | 입력 은행 JSON의 바이트 동일 사본 |
| evidence/assets/ | 은행이 선언한 모든 원문 자산의 해시 동일 사본 |
| authoring-index.json | 고유 문항별 저작 입력·상태·허용 자산 목록 |
| 원문과_저작안내.md | 분류·출처·보류·답안 연결의 탐색 안내 |
| sections/ | 설명 저작 위치. 초기에는 비어 있음 |
| problems/ | 문제·풀이 저작 위치. 초기에는 비어 있음 |
| figures/ | 새 교육용 그림·검토한 문제 자산을 배치할 위치 |

원문 원자료 자체는 복제하지 않는다. 그 경로·해시는 은행 사본에 보존하고 publish에서 저장소 원자료와 대조한다. 자산은 은행의 assets 상대 경로를 evidence 아래에서 동일하게 유지한다.

모든 선언 자산을 증거로 복사하지만, 카드 본문에 배치할 수 있는 목록은 role=problem 및 answer_exposure=none인 자산만 제공한다. 답이 노출된 원문은 원문 정보/풀이의 증거로 사람이 명시적으로 사용하거나 새로운 교육용 그림을 작성한다. unknown 자산의 노출 상태를 import에서 재판정하지 않는다.

## 저작 manifest 계약

schema_version=1은 유지한다. legacy manifest는 bank_import가 없어도 기존 동작을 유지한다.

은행을 가져온 manifest에는 다음 bank_import를 기록한다.

```json
{
  "bank_id": "bank-exp04",
  "schema_version": 1,
  "source_path": "문제은행/실험04/question-bank.json",
  "sha256": "<입력 JSON의 소문자 SHA256 64자리>",
  "snapshot_path": "evidence/question-bank.json",
  "index_path": "authoring-index.json"
}
```

이 블록은 선언된 키만 허용한다. 은행 실험 번호와 manifest 실험 번호가 일치해야 한다. 경로 검사는 단순 문자열 검사 대신 기존 은행의 엄격한 상대 경로 규칙을 재사용한다.

초기 title은 “실험4 문제은행 저작”, edition_status=unknown이다. 현재 교안은 이후 sources 명령으로 찾아 추가하고 판본을 확정한다. 문제은행을 만들었다는 이유만으로 현재 학기 교안 기준이라고 표시하지 않는다.

sources는 은행 source ID·경로·해시를 그대로 유지하고 학습팩 kind=quiz, edition=unknown으로 매핑한다. 파일명·실측 메타데이터·충돌 등 원래 정보는 evidence/question-bank.json에 온전히 보존한다.

topics=[]로 시작한다. 은행의 각 question마다 정확히 하나의 problems 행을 만들고 id를 그대로 사용한다. sources는 모든 occurrence_ids의 location에서 가져오며 source_id/pdf_page/printed_page/locator/bbox/image_size 및 original_number를 보존한다. 중복 위치를 임의로 줄이지 않는다.

각 problems 행에 bank_question_id를 추가해 은행과 연결한다. 기존 새 practice 문항은 이 필드 없이 저작할 수 있다. 수입된 문제는 bank_question_id와 id가 같아야 한다.

수입 문제의 초기 값:

- kind: 은행 past/predicted/unknown 그대로.
- status=held, reason=“설명·개념 연결·독립 풀이 저작 대기”를 기본으로 한다.
- 원문 불확실성·빈 항목 등은 기본 이유에 보류 이유도 덧붙인다.
- topics=[], scope=unknown, duplicate_of=null.
- given_answer=null, derived_answer=null, answer_status=unresolved.
- fragment는 아직 선언하지 않는다. 기존 held 계약은 fragment를 요구하지 않는다.

모든 제공 답안은 은행과 authoring-index에서 보존한다. scalar given_answer를 자동으로 한 답안으로 채우지 않는다. 이후 작성자는 제공 답안들을 대조한 다음 독립 풀이 및 필요한 요약을 작성한다.

checks의 source_visual/content/independent/browser는 모두 not_run으로 시작한다. 원문을 추출 세션에서 판독했다는 기록은 은행 사본에 남지만, 학습팩 검토 완료로 해석하지 않는다.

## authoring-index 계약 v1

최상위 키: schema=logic-lab-bank-import, schema_version=1, bank_id, bank_sha256, experiment, questions.

각 질문 레코드:

- question_id, kind, representative_occurrence_id, occurrence_ids, subparts.
- provided_answers: 원래 answers 배열 전체(confirmed/candidate/reason/target 유지).
- relations: 해당 문항/소문항/관련 답안 등장과 연결된 relations 전체.
- unresolved: 관련 question/occurrence/block/subpart/source/asset를 대상으로 한 audit.unresolved 전체.
- representative_reading, safe_problem_asset_ids, evidence_only_asset_ids.
- authoring_status=pending, selection_reason. 원문 partial/unreadable이면 reading_hold로 시작한다.

완료된 은행의 15개 항목은 전부 인덱스에 남긴다. 예상문제나 미확인 문항의 수록 여부는 저작 단계에서 이유를 기록하며, 빈 항목을 완성된 예상문제로 집계하지 않는다.

인덱스의 추출 정보는 은행으로부터 파생한 고정 정보다. 저작 상태·선별 이유만 수정 가능하다. 검사 시 고정 필드는 은행을 기준으로 다시 계산해 대조한다.

## 생성·검사·저장 연결

build는 bank_import가 있으면 은행 사본/인덱스/연결 문항을 검증하고 evidence와 authoring-index를 stage로 복사한다. root를 받은 build는 source_path의 현재 은행 바이트 해시와 원자료 해시도 대조한다. 변경됐으면 관련 입력을 다시 import하도록 오류를 보고한다.

check_pack는 root 없이도 은행 사본의 해시·ID·버전·실험 번호·선언 자산 해시·인덱스 고정 정보·문항 참조를 확인한다. 원래 은행과 원자료의 현재 상태 대조는 root가 주어진 build/publish에서 수행한다.

기존 은행의 모든 고유 질문은 manifest에 정확히 한 번 남아야 한다. 수록하지 않거나 보류한 이유도 행에 기록한다. 과거/예상/미확인 분류 변경, 문항 누락, 다른 은행 문항 ID 연결은 거절한다.

included로 바꾼 문제는 기존 topic·fragment·answer_status 계약을 충족해야 한다. 대표 원문 reading이 partial/unreadable인 문제는 은행에서 판독을 해결하기 전 included로 바꾸지 못한다. readable 문제에 연결된 제공 답안 보류는 독립 풀이 후 disputed/unresolved로 공개할 수 있다.

문제 fragment의 div.problem 안에서 evidence/assets 또는 그와 바이트가 같은 figures 자산을 사용하면 은행 asset ID의 role/exposure와 대조한다. 안전 목록에 없는 원문 자산을 문제 영역에 넣으면 거절한다. 파일 복사로 노출 검사를 우회하지 못하도록 SHA256으로도 대조한다.

새로 작성한 교육용 그림은 원문 자산으로 표시하지 않고 별도 figures에 둔다. 자동 검사는 의미상 답 노출 판정을 대신하지 않으므로 새 그림은 내용·브라우저 검토 대상이다.

render는 은행 수입 행의 상세 제공 답안·후보 연결·불확실성에 접근할 수 있도록 원문과_저작안내.md 링크를 붙인다. 여러 provided answer를 scalar 값 하나로 축소하지 않는다. 학생에게 표시할 독립 풀이와 원문 제공 답안은 명확히 구분한다.

publish는 check_pack에 더해 현재 원래 은행 및 원자료/증거 해시를 확인하고 기존 검증·백업·rollback 조건을 유지한다. 증거와 인덱스는 generated_files에 포함해 다음 갱신에도 관리한다.

## 파일 책임

- scripts/lab/review_pack/bank_import.py: import, 저작 인덱스 생성·검증, 증거 사본 검증.
- scripts/lab/review_pack/__main__.py: import-bank 명령과 build 연계.
- scripts/lab/review_pack/manifest.py: optional bank_import 및 bank_question_id의 형식·연결 계약.
- scripts/lab/review_pack/checks.py: pack의 증거 검증·문제 영역 자산 노출 검사.
- scripts/lab/review_pack/publish.py: 원래 은행·증거 대조.
- scripts/lab/review_pack/render.py: 증거/저작 안내 보존 및 탐색 링크.
- .claude/skills/logic-lab-review-pack/SKILL.md와 references/question-bank.md, format.md, verification.md: 실제 명령과 경계.
- tests/test_review_pack_bank_import.py, tests/test_review_pack_bank_import_flow.py: 계약 및 연결 행동 검증.
- docs/verify/2026-09-30-question-bank-import.md: 실제 은행 import 수용 검증.

## 검증과 수용 기준

계약 fixture에서 source/asset bytes를 만들고 전체 경로를 실행한다. missing/changed 자산·원문·은행, 잘못된 버전/실험 번호, 기존 출력 경로, 누락/변경된 문항, 여러 제공 답안과 후보 관계, 부분 판독, 답 노출 present/unknown를 검증한다.

문항 순서만 바뀌어도 ID는 유지되어야 한다. 다른 의미의 변형 문항은 자동 병합하지 않아야 한다. 원래 은행 bytes/hash는 snapshot과 일치하고 테스트 전후 입력은 변경되지 않아야 한다.

legacy manifest의 기존 build/check/publish 회귀를 유지한다. 실제 은행으로 새 tmp 폴더에 import를 실행해 15개 행·93개 occurrence·34개 자산·38개 제공 답안 연결·20개 미해결 기록이 증거에 유지되는지 확인한다. 이 수치는 실험4 수용 예이며 구현에 하드코딩하지 않는다.

전수 기출은 저작 대상으로 보존하되 자동 풀이하지 않는다. import 성공을 학습팩 완료나 정답 검증 완료라고 보고하지 않는다. 실제 학습 HTML을 저작하거나 발행하지 않는다.

## 코드 기반 확인

현재 CLI는 sources/build/check/publish이며 import가 없다. manifest는 scalar given_answer와 topics/fragment를 요구하는 별도 계약이다. question_bank.load_question_bank는 중복 키를 거절하고 check_question_bank_files는 원자료·자산을 읽기 전용으로 검사한다.

실제 은행은 complete_with_holds이며 기계 검사 pass다. 대표 판독은 q-empty-six만 partial이고 나머지는 readable이지만, 일부 원문 그림은 role=mixed/answer 및 exposure=present라서 문제 본문으로 자동 삽입할 수 없다. 추출의 audit.checks.source_visual은 partial이며 독립 정답 풀이 검토는 하지 않았다.
