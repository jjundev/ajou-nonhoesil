# 논리회로 기출 문제은행 추출 설계

상태: 2026-09-29 사용자가 grill-yourself의 추천안을 모두 수락했다. #1 추출 계약·절차 우선, #2 실험4부터 시작은 confirmed by default. 구현 방식은 앞서 확정한 Native를 유지한다. 이 문서는 승인된 대화 설계를 보존하며 구현 완료를 뜻하지 않는다.

## 목적과 경계

별도 새 세션에서 원자료를 직접 읽어 출처·문제 조건·그림·제공 답안·중복 관계를 보존하는 문제은행을 만든다. 학습팩 import, 설명·풀이 저작, HTML/MD 생성, Task 8, 브라우저 검증, 원래 체크아웃 통합은 별도 작업이다. 이번 구현 계획은 계약·검증 도구·추출 인계 절차를 제공한다. 실제 실험4 추출은 도구 구현 후 새 세션에서 수행한다.

기존 manifest는 topics/fragment/derived_answer 등을 담는 학습팩 저작 계약이다. 문제은행을 manifest라고 부르거나 build에 직접 넣지 않는다. 기존 생명과학 템플릿 및 네 학습 파일 출력 결정은 유지한다.

## 공통 제약

- 기존 워크트리 C:/Users/Hyunjun/.codex/worktrees/logic-lab-review-pack/논회실 및 브랜치 codex/logic-lab-review-pack을 사용한다.
- Python 런타임은 표준 라이브러리만 사용한다. PDF 시각 판독 도구는 기존 검증 환경과 pdf 스킬을 사용한다.
- 원자료·보고서·측정 기록·결선도·기존 학습팩은 수정하지 않는다.
- tmp/review-pack-work/experiment04의 임시 분석은 추출 근거로 사용하지 않는다.
- 첫 실제 추출은 실험4 전체 자료이며, 기출·예상·해설·이미지·원본 문서를 모두 감사한다.
- 문제은행 JSON에는 HTML 조각·독립 풀이·정답 검증 완료 상태를 넣지 않는다.
- 파일 경로는 기준 디렉터리 상대 POSIX 경로이며 Windows와 macOS에서 사용할 수 있어야 한다.
- 형식 검사 통과, 원문 시각 판독 완료, 독립 풀이 검증을 서로 대신하지 않는다.
- 새 세션 생성이나 Task 8 실행을 자동으로 시작하지 않는다.

## 산출물과 인터페이스

실제 추출 산출물은 문제은행/실험04/question-bank.json, assets/, 검증결과.md. 작업 중에는 tmp/question-bank/실험04-<고유실행ID>를 사용한다. 기존 산출물이 있으면 덮어쓰지 않고 새로운 작업 디렉터리에서 차이를 검토한다.

최상위 키: schema="logic-lab-question-bank", schema_version=1, bank_id, experiment(정수 1~10), sources, assets, occurrences, questions, relations, audit. 모든 레코드는 스키마에서 선언한 필드만 허용한다. 알 수 없는 버전과 필드 오타는 오류다.

ID는 [A-Za-z][A-Za-z0-9_-]*. bank_id를 제외한 source/asset/occurrence/question/block/subpart ID는 은행 안에서 전역 유일하다. 기존 은행을 다시 추출할 때 ID를 유지한다. 순서와 전사 교정은 새 ID 사유가 아니다. 실질적 문제 조건 변경은 새 문항 및 variant_of 관계로 남긴다.

### 원문 위치 Location

source_id, pdf_page(int|null), printed_page(str|null), locator(str), bbox([number,number,number,number]|null), image_size([positive int,positive int]|null).

PDF는 pdf_page>=1, 해당 source의 unit_count 이하이며 locator에 위치 설명을 쓴다. 비PDF는 pdf_page=null이며 locator가 필수다. bbox는 좌상단 기준 [x0,y0,x1,y1], 0<=x0<x1<=1, 0<=y0<y1<=1. bbox가 있으면 image_size가 필수다. PDF의 경우 해당 페이지의 전체 렌더 이미지가 기준이고 비PDF 이미지는 원본, DOCX는 locator로 식별한 렌더 페이지가 기준이다. 부분 크롭 이미지를 좌표 기준으로 쓰지 않는다.

### Sources

id, path(저장소 상대), sha256, format(pdf/docx/doc/image/text/other), filename_metadata({year,term}: str|null), observed_metadata({year,term}: str|null), conflicts([{field,filename_value,observed_value,location}]), processing(pending/complete/held), reason(str), unit_kind(page/document/image), unit_count(int|null).

연도·학기는 파일명과 원문 판독값을 따로 보존한다. 값이 모두 있고 다르면 conflicts에 해당 필드와 양쪽 값·근거 위치가 있어야 한다. complete는 모든 단위를 감사했음을 뜻하며 모든 문항 판독 성공을 뜻하지 않는다. held는 미지원·암호화·읽기 실패 등의 이유와 미해결 항목을 필요로 한다. PDF 페이지 수를 모르면 unit_count=null, processing=held. 이미지와 문서 단위는 unit_count=1. DOCX는 문서 전체 감사에 더해 occurrence.locator로 문단/표/셀을 식별한다.

### Assets

id, path(은행 폴더 상대, assets/ 아래), sha256, location, role(problem/answer/mixed), answer_exposure(none/present/unknown). 원문 판독 근거만 저장한다. role=problem이면 answer_exposure=none이어야 한다. 답이 표시된 원문을 지우거나 다시 그려 문제 증거로 바꾸지 않는다.

### Occurrences와 Blocks

Occurrence: id, role(question/answer/explanation/mixed), location, original_number(str|null), blocks, reading(readable/partial/unreadable), uncertainties([{block_id:str|null,symbol:str,candidates:[str],reason:str,location}]). partial/unreadable은 최소 하나의 uncertainty가 필요하다. 문항 본문이 없더라도 원문 위치와 판독 불가 이유를 남긴다.

Block: id, type(text/math/table/figure), text(str), tex(str|null), cells([[str]]|null), asset_id(str|null). 모든 필드를 명시한다. text는 원문 전사 또는 그림 설명이다. math는 tex 필수, table은 cells 필수이며 행 길이가 같아야 하고, figure는 asset_id 필수. 다른 형식에서 해당 필드는 null. 그림은 원문 대조 없이 텍스트나 LaTeX만으로 대체하지 않는다. blocks 배열 순서가 원문 순서다.

### Questions와 제공 답안

Question: id, occurrence_ids([question/mixed occurrence ID], 비어 있지 않음), representative_occurrence_id, kind(past/predicted/unknown), classification_reason(str), evidence([Location]), subparts([{id,label,occurrence_id,block_ids}]), answers([{occurrence_id,target_id,status(confirmed/candidate),reason}]).

대표 occurrence는 해당 occurrence_ids에 속한다. 같은 문제라고 확인한 등장만 한 question으로 묶는다. 한 question/mixed occurrence는 정확히 한 question에 소속된다. 기출·예상 분류는 파일 제목만으로 확정하지 않으며 근거 위치를 남긴다. question의 소문항은 해당 question의 occurrence와 그 안의 block을 참조한다. 공통 지문·그림은 부모 question의 전체 occurrence로 접근하므로 소문항에 복사하지 않는다.

답안 occurrence는 answer/explanation/mixed 역할이어야 하고 target_id는 해당 question 또는 그 소문항이어야 한다. confirmed는 연결이 확인되었다는 뜻이며 정답이라는 뜻이 아니다. 여러 제공 답안을 모두 보존한다. 연결되지 않은 answer/explanation occurrence는 audit.unresolved에 이유를 남긴다. derived_answer/answer_status/fragment/topics는 이 계약에 없다.

### Relations

{from_id,to_id,type,reason,evidence:[Location]}. duplicate_candidate와 variant_of는 서로 다른 question을 연결하며 무방향 관계다(동일 쌍 중복 금지). answer_candidate는 answer/explanation/mixed occurrence에서 question/소문항으로 향한다. 확정 중복은 관계 대신 한 question의 occurrence_ids로 표현한다. 조건·회로·극성 차이가 있는 유사 문제를 자동 병합하지 않는다.

### Audit

status(draft/complete/complete_with_holds), checks({structure:not_run/pass/fail,source_visual:not_run/partial/pass}), units([{source_id,index:int,outcome(questions/reference/blank/held),occurrence_ids:[str],reason:str}]), unresolved([{target_id,reason}]). 집계는 별도 중복 저장하지 않고 검증 도구가 계산한다.

PDF는 페이지마다 1..unit_count, 비PDF는 문서/이미지 단위 1개의 units가 필요하다. 등장 레코드가 여러 페이지를 잇는 경우 추가 페이지의 units에도 같은 occurrence ID를 연결하고 블록별 근거 자산으로 대응시킨다. 대표 location의 페이지에는 반드시 해당 occurrence가 있어야 한다. held 단위는 reason과 unresolved가 필요하다. draft는 미완성 감사를 허용하나 참조·형식 오류는 허용하지 않는다. complete는 pending/held 단위, 미해결, partial/unreadable occurrence가 없고 source_visual=pass여야 한다. complete_with_holds는 모든 자료의 감사 시도는 끝났지만 이유가 기록된 미해결이 남은 상태다. 두 완료 상태는 sources가 비어 있으면 허용하지 않는다. partial/unreadable occurrence와 held source는 각각 unresolved에 이유를 남긴다. 미지원 source의 페이지 수를 모르면 index=1의 held 단위로 파일 전체를 표시한다.

## 검증과 추출 절차

목록화는 대상 퀴즈 폴더의 모든 파일을 재귀 탐색하며 확장자로 누락시키지 않는다. 경로 밖 링크는 오류다. 없는/빈 폴더도 자료 없음으로 명시한다. inventory는 판독·분류·source_visual 판정을 하지 않는다. 원문 해시와 전사한 근거 이미지를 보존한다.

원문 등장 전사 → 고유 문항 묶기 → 답안 연결 → 미해결 감사 순서. OCR/텍스트 추출은 탐색 보조이며 회로·오버바·클록 엣지·표는 시각 대조한다. X/Z·출력 극성·IC 명칭을 추측해 교정하지 않는다. 종합본의 예상문제는 문항 단위로 분류한다.

검증기는 데이터를 수정하지 않고 JSON 경로를 포함한 오류 목록을 반환한다. 구조 오류, 잘못된 참조, 경로 탈출, 누락 자산, 원문/자산 해시 불일치는 실패한다. 정직하게 기록된 판독 보류는 입력 오류가 아니다. CLI는 기계 검사의 결과와 기록된 판독 상태를 따로 출력한다.

## 후속 import 경계

별도 후속 계획에서 bank ID/version/JSON SHA256을 기록하고 문항 ID·원문 위치·모든 제공 답안을 저작 입력으로 전달한다. 예상문제 선별, 개념 매핑, 독립 풀이, HTML 조각 생성 후에 학습팩 manifest를 작성한다. 문제은행 checks를 학습팩 content/independent/browser=pass로 복사하지 않는다.

## 확인된 코드 근거

- scripts/lab/review_pack/manifest.py:63~75 — 학습팩은 kind/status/topics/fragment와 답안 상태를 요구한다.
- scripts/lab/review_pack/sources.py:61 — 기존 목록기는 .doc를 제외한다. 새 목록 함수는 별도로 제공한다.
- scripts/lab/review_pack/__main__.py:16 — 기존 명령은 sources/build/check/publish이며 import는 없다.
- requirements-dev.txt — scripts/lab 런타임은 표준 라이브러리만 사용한다.
- docs/superpowers/plans/2026-09-29-logic-lab-review-pack.md:478 — Task 8 중단 및 새 세션 추출 요구.
