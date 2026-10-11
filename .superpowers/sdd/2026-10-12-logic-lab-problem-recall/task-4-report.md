# Task 4 — 실험01 12문항 핵심 개념 보충

## 결과

기존 실험01 12문항에 recall 본문 및 우측 핵심 개념 요약을 추가했고 v2로 로컬 발행했어요. 저작·발행 조각, HTML/MD, manifest, 실제 검토 기록과 공통 발행 테스트를 갱신했어요. 기존 understand/start/solve/verify/pitfall/retry 및 기존 요약은 추가 부분 제거 후 원래 문자열과 12개 모두 정확히 같아요. 기존 q-deq disputed와 모든 경고를 보존했어요. 외부/메인 checkout에는 쓰지 않았어요.

## TDD와 검사

- 공통 test_recall_published를 6실험 인자로 추가하고 coverage에도 (6,14)를 추가했어요.
- 변경 전 test_recall_published[1-12]는 manifest version 1 != 2로 실제 실패했어요.
- 저작 후 새 stage explain-stage/check, 실제 검토 기록 후 최종 stage check, publish, published check 모두 통과했어요.
- 발행본 recall/coverage/answer-state 3개 테스트 통과.
- 실험01 발행본 375/1280 × light/dark 브라우저 회귀 4개 및 no-JS 회귀 1개 통과.
- git diff --check 통과.

## 실제 원문/내용 검토

전용 logic-lab-problem-explain 스킬 및 PDF 스킬을 읽고 적용했어요. 단답형 p1, 기출 문제 p1/정답 p1, 예상문제v1 p1–2, 강의노트 p2–9/13–15의 16개 PNG와 채점본 JPG를 실제 view_image로 판독했어요. 개별 ID별 단서·개념/기호·적용 조건/선택 이유·모든 소문항·원문 page·경고·요약 일치를 저작/발행 검증결과와 docs/verify에 기록했어요.

원문 그림의 q-deq는 B의 접속점과 C가 E의 입력인데 제공 빨간 답은 E=A·B예요. 그림 기반 E=BC 해석과 기존 충돌 경고를 유지했어요. 답안 상태나 원문을 바꾸지 않았어요. 저자가 3입력8조합, XOR4조합, switching32조합, De Morgan32조합, logicdiagram16조합과 CMOS 상보경로를 전수 재계산했어요. content=self_review; independent=not_run이에요.

## 실제 브라우저 검토

Chrome에서 12개 문항 각각 hash로 이동하여 375×900/1280×900 × light/dark의 48개 경우를 확인했어요. recall/summary 96개 실제 screenshot과 12개 contact sheet를 저장했고 모든 sheet 및 no-JS screenshot을 view_image로 읽었어요. 본문/요약 일치, 읽기/테마 대비 확인. pageerror/katex-error/깨진 그림/문서 가로 넘침은 모두0이에요. 수식/표 카드 overflow-x=auto, padding≥16px, border≥1px; understand margin/padding/border=24/24/1px예요.

모바일 목차/닫기 동작, 키보드 포커스/Enter 다음 이동, 실험설명과 분리된 읽음 namespace를 확인했어요. no-JS에서는 문항12·목차12·recall/solve/verify36개가 보였어요. 발행본 실제 긴 수식 카드(q-switching 2개/q-nand-xor 1개 × 양테마=6개)의 내부 scrollLeft 이동과 터치 후 hash 불변도 확인했어요. browser=pass, source_visual=pass예요.

## 보존과 백업

발행 전에 설명 밖 파일170개의 SHA-256과 original manifest baseline을 저장했어요. stage/발행본/backup 모두170개 해시 일치, 설명 밖 신규/삭제0. experiment/sources/topics/problems/checks/review_presentation_version/note_presentation_version이 전후 동일해요. backup original manifest도 baseline과 같아요.

최종 stage: tmp/review-pack/recall-01-c6e9685228ca4eb8bad4c34537371029

백업: 복습노트/실험01.backup-a390ed552fcf (이 isolated worktree 내부)

필수 JSON 증거: output/validation/problem-recall/baseline-01.json, browser-01.json, content-proof-01.json, preservation-01.json, touch-01.json. 큰 PNG/contact sheet는 output/validation/problem-recall/source-01 및 browser-01에 로컬 보존해요. 독립 검토는 미실시예요. 다른 실험의 아직 v1인 recall 테스트는 이 작업의 완료 대상이 아니에요.

## 자체 diff 검토/범위

공통 테스트 외 생성기/런타임/원문/은행/그림 변경은 없어요. 두 번의 초기 browser harness 오류(숨긴 요약 여러 개 selector, 모바일 닫기 버튼 selector)는 보조 검사에서 수정한 뒤 전체48회를 완료했어요. 제품 변경은 필요하지 않았어요. controller spec 수정과 output/validation/navigation은 staging에서 제외했어요.
