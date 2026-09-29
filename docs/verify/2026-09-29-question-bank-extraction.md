# 기출 문제은행 추출 도구 검증 — 2026-09-29

## 완료 범위

승인된 추출 계약·검증 CLI·새 세션 인계 문서를 Native로 구현했다. 브랜치는 `codex/logic-lab-review-pack`, 시작 커밋은 `0d56b13f3bfe04e0483e142eb6ad698695e91752`, 기능 및 리뷰 수정 커밋은 `780ec2b`부터 `7dbd43e`까지다.

- JSON Schema v1, 원문 등장과 고유 문항 분리, 제공 답안 및 후보/변형 관계 보존.
- 형식·참조·페이지 감사·판독 보류·답 노출 그림 검사.
- 확장자 제한 없는 자료 목록, 링크·경로 탈출 거부, 원문/자산 SHA256 검사.
- 읽기 전용 inventory/check CLI. 기계 검사와 기록된 시각 판독 상태를 구분.
- 별도 새 세션에서 실험4를 원자료부터 추출하는 절차와 요청문.

실제 기출 추출, 정답 독립 풀이, 문제은행 import, 학습팩 생성, Task 8, 원래 체크아웃 통합은 실행하지 않았다. 템플릿·기존 manifest 계약도 변경하지 않았다.

## 검증 결과

| 검사 | 결과 |
|---|---|
| 시작 시 기존 manifest/sources 테스트 | 22 passed |
| 최종 신규 테스트 | 66 passed (전체 관련 109개에 포함) |
| 신규 + 기존 review_pack 회귀 | 109 passed |
| 전체 저장소 최초 실행 | 20 failed, 2174 passed, 4 skipped, 1082 subtests passed |
| 리뷰 수정 후 전체 재실행 | 21 failed, 2177 passed, 4 skipped, 1082 subtests passed |
| 추가 schematic 실패 단독 재실행 | 1 passed |
| 실험4 inventory와 파일시스템 경로 집합 대조 | 11개 파일 일치; 실제 판독은 하지 않음 |
| 실제 subprocess CLI 실행 | UTF-8 JSON 및 종료 코드 확인, 빈 draft의 시각 상태 not_run 유지 |
| schema 키워드 및 문서 링크 | 지원 키워드만 사용, 로컬 링크 모두 존재 |
| 변경 파일 범위 | 원자료·기존 구현 파일의 diff 없음 |

회귀 명령:

```powershell
python -m pytest -n0 tests/test_review_pack_question_bank.py tests/test_review_pack_question_bank_sources.py tests/test_review_pack_question_bank_cli.py tests/test_review_pack_sources.py tests/test_review_pack_manifest.py tests/test_review_pack_render.py tests/test_review_pack_md.py tests/test_review_pack_checks.py tests/test_review_pack_publish.py -q
python -m pytest -q
```

## 독립 코드 리뷰

별도 fresh-context gpt-6-astra 리뷰어가 전체 이번 변경을 읽기 전용으로 검토했다. Critical 0, Important 1, Minor 0, 판단 보류 없음.

Important: enum 필드에 배열이 들어오면 오류를 반환한 후가 아니라 배열 분기로 들어가 KeyError('items')가 발생했다. API 3개 및 CLI 1개 회귀 테스트에서 실패를 확인한 뒤 enum 불일치 시 즉시 오류를 반환하도록 수정했다. 관련 109개 테스트가 통과했다. 코드 리뷰는 기출 내용 판독이나 정답 검증을 뜻하지 않는다.

## 전체 테스트의 미해결 실패

기존 config 관련 14건은 앞선 인계에서 알려진 기준선 실패다. 이번 전체 실행에서 추가로 확인한 6건은 아래와 같다. 해당 테스트 및 구현 파일은 시작 커밋과 동일함을 git diff로 확인했다. 새 기능에서 이 모듈들의 동작을 변경하지 않았다.

| 영역 | 건수 | 관찰한 원인 |
|---|---:|---|
| config | 14 | 경로 표현 및 교안 후보 우선순위 관련 기존 기대값 불일치 |
| figure_export | 1 | 테스트의 file URI → Windows 경로 변환으로 잘못된 경로 발생 |
| html2pdf | 2 | Unix shell 스텁을 Windows 실행 파일처럼 호출해 WinError 193 |
| merge_report | 2 | 열린 임시 파일 삭제/정리 관련 Windows 잠금 및 잔존 파일 |
| trace_guide | 1 | 실험4 PDF 15쪽 기대에 실제 16쪽 |
| schematic (두 번째 전체 실행만) | 1 | 병렬 merge_report 테스트가 보고서 PDF를 잠시 변경해 git status 비교 실패; 단독 실행은 통과 |

전체 최종 실행 실패 이름(하위 검사 n=1~10 포함):

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
SUBFAILED(n='9') tests/test_lab_config.py::TestManualCandidates::test_아카이브_후보가_열_개_다_실재한다@test_lab_config.py::TestManualCandidates
SUBFAILED(n='10') tests/test_lab_config.py::TestManualCandidates::test_아카이브_후보가_열_개_다_실재한다@test_lab_config.py::TestManualCandidates
FAILED tests/test_lab_config.py::TestManualCandidates::test_아카이브_후보에는_실험_기반_경로가_붙지_않는다@test_lab_config.py::TestManualCandidates
FAILED tests/test_lab_config.py::TestManualCandidates::test_주차_폴더_사본이_아카이브보다_먼저다@test_lab_config.py::TestManualCandidates
FAILED tests/test_lab_config.py::TestManualCandidates::test_파일_이름은_0_을_채우지_않는다@test_lab_config.py::TestManualCandidates
FAILED tests/test_lab_figure_export.py::CaptureCopy::test_dump_dom_은_원본이_아니라_사본을_연다@test_lab_figure_export.py::CaptureCopy
FAILED tests/test_lab_html2pdf.py::TestSuccessRule::test_clean_exit_without_a_file_still_fails@test_lab_html2pdf.py::TestSuccessRule
FAILED tests/test_lab_html2pdf.py::TestSuccessRule::test_nonzero_exit_and_stderr_noise_still_succeed@test_lab_html2pdf.py::TestSuccessRule
FAILED tests/test_merge_report.py::TestIntegration::test_merge_lab_report_clean_body_false_keeps_file@test_merge_report.py::TestIntegration
FAILED tests/test_lab_schematic.py::TestMainWithSpec::test_사본_옆에_PNG_를_두고_사본에만_적는다@test_lab_schematic.py::TestMainWithSpec
FAILED tests/test_merge_report.py::TestIntegration::test_merge_lab_report_with_explicit_body_cleans_by_default@test_merge_report.py::TestIntegration
FAILED tests/test_trace_guide.py::Pdf::test_실험04_는_층마다_한_쪽@test_trace_guide.py::Pdf
```

판단: 기존 config/PDF/보고서 실패의 수정은 승인된 추출 도구 범위 밖이므로 기존 코드를 보존했다. 따라서 전체 저장소 테스트가 통과했다고 주장할 수 없으며 통합 완료로 판정하지 않는다. 전체 로그와 진행 원장은 이 워크트리의 `.superpowers/sdd/2026-09-29-question-bank-extraction/`에 보존한다.

## 다음 세션

[실험4 새 세션 요청문](../../.claude/skills/logic-lab-review-pack/references/question-bank-extraction-session.md)을 새 세션에 전달한다. [문제은행 계약](../../.claude/skills/logic-lab-review-pack/references/question-bank.md)에 따라 JSON과 근거 그림을 추출한 뒤, 별도 import 작업으로 연결한다.

## 사용자 요청에 따른 추가 수정

후속 재점검에서 발견한 세 문제를 수정했다.

- readable이면서 uncertainties가 남은 문항은 모든 audit 상태에서 오류다. partial/unreadable 및 unresolved로 기록하면 complete_with_holds를 사용할 수 있다.
- JSON 로더는 최상위와 중첩 객체의 중복 키를 거부한다. 원문 조건이 마지막 값으로 덮여 사라지는 것을 방지한다.
- 수치 검사에서 큰 정수를 float로 변환하지 않는다. 범위를 벗어난 좌표는 JSON 경로를 포함한 검증 오류로 반환한다.

API·CLI 회귀 사례 10개 모두 수정 전 실패를 확인했고 수정 후 통과했다. CLI 실패에서도 입력 파일을 수정하지 않음을 확인했다. 신규와 기존 review_pack을 합친 관련 테스트는 **119 passed**다. 이 후속 수정에서는 전체 저장소 테스트를 재실행하지 않았으며, 위 전체 검사 21건 실패 기록은 이전 실행 결과로 유지한다. 실제 추출·import·Task 8·통합도 실행하지 않았다.
