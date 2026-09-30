# 문제은행 import 연결 검증 기록

2026-09-30. 작업 브랜치 codex/logic-lab-review-pack, 구현 시작 dca96fa, 기능 구현 4d76f42.

## 검증 결과

- 관련 baseline: 119 passed.
- 최종 관련 회귀: 207 passed. 새 import·연결 행동 테스트 88개.
- 전체 저장소: 20 failed, 2276 passed, 4 skipped, 1082 subtests passed. 전체 통과가 아니다.
- 스킬 형식 검사와 git diff --check 통과.
- 새 원자료·추출 JSON·템플릿 변경 없음. 기존 워크트리를 유지했다.

전체 실패는 이전 [추출 도구 검증](2026-09-29-question-bank-extraction.md)에 기록된 config/figure_export/html2pdf/merge_report/trace_guide 영역이다. 이번 코드 범위에서 해당 구현·테스트를 수정하지 않았다. 이전 병렬 실행에서 보였던 schematic 경합은 이번 실행에서는 발생하지 않았다.

## 실제 실험4 import

명령:

```powershell
python -m scripts.lab.review_pack.question_bank_cli check --root . --bank 문제은행/실험04/question-bank.json
python -m scripts.lab.review_pack import-bank --root . --bank 문제은행/실험04/question-bank.json --run tmp/review-pack/실험04-import-20260930-cli
```

API 수용 경로: tmp/review-pack/실험04-import-20260930. 실제 CLI 수용 경로: tmp/review-pack/실험04-import-20260930-cli. 실제 입력은 완료된 문제은행이며 이전 임시 저작을 재사용하지 않았다.

| 항목 | 결과 |
|---|---:|
| 고유 질문 행 | 15 |
| 원문 등장 | 93 |
| 원문 자산 | 34 |
| 제공 답안 연결 | 38 |
| 연결 confirmed/candidate | 30 / 8 |
| 추출 보류 기록 | 20 |
| 바이트 변경 없는 입력 파일 | 46 |

은행 SHA256: `f264d0d777be8cbbb02dc340c06da539b3a53dc3454355fe1239c780154b020c`.
snapshot bytes는 원래 JSON과 같고, 원자료 11개·자산 34개·은행 1개의 해시가 전후 동일하다.
모든 15개 문항은 held, 독립 풀이 없음으로 시작한다. q-empty-six는 reading_hold다. 모든 학습팩 checks는 not_run이다.
confirmed 30은 답안 연결 확인일 뿐 정답 검증이 아니다. 원문 판독·출처·답안 보류를 import가 해결하지 않았다.

## 구현된 동작

- 새로운 run만 생성. draft·구조/해시 오류·입력과 겹치는 출력·기존 run을 거절한다.
- snapshot·선언 자산 전체·인덱스·원문 안내를 보존한다.
- 원문 등장·소문항·복수 답안·후보 관계·판독 보류·변형 관계를 유지한다.
- 파일명 변경에도 답 노출 present/unknown 원문을 문제·힌트·카드 본문에서 차단하고 원문/풀이 details에서는 허용한다.
- build/check/publish에서 증거·문항 연결을 확인하며 build/publish는 현재 원래 입력도 대조한다.
- legacy 팩의 기존 테스트를 유지했다. 기존 사용자 메모 보존과 rollback 테스트도 통과했다.

## 전체 실행의 실패 목록

```text
FAILED tests/test_lab_config.py::ExperimentBaseTest::test_기반이_두_입구_전부에_적용된다@test_lab_config.py::ExperimentBaseTest
SUBFAILED(n='1') tests/test_lab_config.py::TestManualCandidates::test_아카이브_후보가_열_개_다_실재한다@test_lab_config.py::TestManualCandidates
SUBFAILED(n='2') tests/test_lab_config.py::TestManualCandidates::test_아카이브_후보가_열_개_다_실재한다@test_lab_config.py::TestManualCandidates
SUBFAILED(n='3') tests/test_lab_config.py::TestManualCandidates::test_아카이브_후보가_열_개_다_실재한다@test_lab_config.py::TestManualCandidates
SUBFAILED(n='4') tests/test_lab_config.py::TestManualCandidates::test_아카이브_후보가_열_개_다_실재한다@test_lab_config.py::TestManualCandidates
SUBFAILED(n='5') tests/test_lab_config.py::TestManualCandidates::test_아카이브_후보가_열_개_다_실재한다@test_lab_config.py::TestManualCandidates
SUBFAILED(n='6') tests/test_lab_config.py::TestManualCandidates::test_아카이브_후보가_열_개_다_실재한다@test_lab_config.py::TestManualCandidates
SUBFAILED(n='7') tests/test_lab_config.py::TestManualCandidates::test_아카이브_후보가_열_개_다_실재한다@test_lab_config.py::TestManualCandidates
SUBFAILED(n='8') tests/test_lab_config.py::TestManualCandidates::test_아카이브_후보가_열_개_다_실재한다@test_lab_config.py::TestManualCandidates
FAILED tests/test_lab_figure_export.py::CaptureCopy::test_dump_dom_은_원본이_아니라_사본을_연다@test_lab_figure_export.py::CaptureCopy
SUBFAILED(n='9') tests/test_lab_config.py::TestManualCandidates::test_아카이브_후보가_열_개_다_실재한다@test_lab_config.py::TestManualCandidates
SUBFAILED(n='10') tests/test_lab_config.py::TestManualCandidates::test_아카이브_후보가_열_개_다_실재한다@test_lab_config.py::TestManualCandidates
FAILED tests/test_lab_config.py::TestManualCandidates::test_아카이브_후보에는_실험_기반_경로가_붙지_않는다@test_lab_config.py::TestManualCandidates
FAILED tests/test_lab_config.py::TestManualCandidates::test_주차_폴더_사본이_아카이브보다_먼저다@test_lab_config.py::TestManualCandidates
FAILED tests/test_lab_config.py::TestManualCandidates::test_파일_이름은_0_을_채우지_않는다@test_lab_config.py::TestManualCandidates
FAILED tests/test_lab_html2pdf.py::TestSuccessRule::test_clean_exit_without_a_file_still_fails@test_lab_html2pdf.py::TestSuccessRule
FAILED tests/test_lab_html2pdf.py::TestSuccessRule::test_nonzero_exit_and_stderr_noise_still_succeed@test_lab_html2pdf.py::TestSuccessRule
FAILED tests/test_merge_report.py::TestIntegration::test_merge_lab_report_clean_body_false_keeps_file@test_merge_report.py::TestIntegration
FAILED tests/test_merge_report.py::TestIntegration::test_merge_lab_report_with_explicit_body_cleans_by_default@test_merge_report.py::TestIntegration
FAILED tests/test_trace_guide.py::Pdf::test_실험04_는_층마다_한_쪽@test_trace_guide.py::Pdf
```

전체 로그는 .superpowers/sdd/2026-09-30-question-bank-import/full-suite-final.txt에 있다.

## 실행 중 판단

PowerShell/Python으로 진행 원장·brief를 관리했다. 이 Windows 환경에서 Bash helper 대신 동일한 테스트·커밋 기록을 보존하기 위한 선택이며, 비용은 수동 bookkeeping이다.

## 최종 독립 리뷰

별도 fresh-context gpt-6-astra 리뷰에서 Important 2건, Critical/Minor/판단 보류 0건을 받았다. 두 노출 검사 누락을 다음과 같이 수정했다.

- srcset 후보와 스타일 블록의 이미지 URL을 검사한다. 스타일은 부모 DOM 밖에도 적용되므로 문서 전체에서 검사한다.
- 항상 보이는 summary와 초기 open details는 닫힌 증거 영역으로 취급하지 않는다.

자체 API·실제 build 경로의 재현 11개가 수정 전에 실패했고, 수정 후 통과했다. 해당 검증 파일 39개와 관련 회귀 207개가 통과했다. 수정 후 전체 재실행도 20개 기존 영역 실패이며 새로운 실패는 없었다. 두 번째 리뷰어/재리뷰는 요청하지 않았다. 코드는 f8a3b94에서 수정됐다.

추가 구현 판단: CSS @import/image-set은 완전한 CSS 의존성 해석기를 추가하는 대신 지원하지 않는 은행 카드 문법으로 거절한다. 영향은 작성자가 직접 로컬 이미지 URL을 사용해야 한다는 것이다.

## 다음 단계와 경계

실험4 설명·개념 매핑·독립 풀이 저작, 실제 학습팩 HTML/MD 생성, 내용·브라우저 검증, Task 8, 원래 체크아웃 통합·merge·push는 수행하지 않았다.
다음 저작은 import된 manifest/index와 함께 저장된 은행 증거를 입력으로 진행한다. 원래 은행을 수정해야 할 경우 재import하고 영향을 받는 저작을 재검토한다.
