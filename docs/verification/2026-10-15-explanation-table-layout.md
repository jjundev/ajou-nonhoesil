# 2026-10-15 문제설명 표 배치 적용·검증

실험01~06 문제설명 HTML 전체에 명시적 열 역할에 따른 너비와 입력/중간 계산/출력 그룹 구분을 적용했다. 짧은 표는 필요한 너비만 왼쪽에 배치하며, 문장 비교표는 가용 폭을 쓴다. 실험설명·기출문제·기출풀이 HTML/MD/PDF와 원문은 보존한다.

| 실험 | 표 수 | 문항 수 |
|---|---:|---:|
| 01 | 9 | 12 |
| 02 | 0 | 14 |
| 03 | 8 | 15 |
| 04 | 12 | 12 |
| 05 | 19 | 19 |
| 06 | 14 | 14 |
| 합계 | 62 | 86 |

## 적용 규칙

- 열의 역할(index/control/input/intermediate/output/description)과 표현(signal/bus/expression/text/connector/index)을 문항별 JSON에 명시했다. A/C 등의 이름으로 입력·출력을 추측하지 않는다.
- 단일 신호 열은 같은 표에서 같은 내용 폭, 최소 3rem이다. 기본 좌우 여백은 각각 0.5rem이다. 경계 여백은 내용 폭과 따로 계산한다.
- 주 경계는 양쪽 셀에 각각 0.5rem, 보조 경계는 각각 0.25rem을 추가한다. 원래 열의 순서는 유지한다.
- 비트열·상태식은 줄바꿈하지 않는다. 문장은 열별 최소 너비를 확보한 다음 남는 공간을 같은 비중으로 나눠 갖는다. 수동 min_rem 보정도 유지한다.
- 같은 열 구성을 가진 빈 표·완성 표는 같은 pair로 연결했다. 비트 길이와 최장 내용까지 공동으로 계산한다. 열 구성이 다른 표는 연결하지 않았다.
- 신호표에 보조 그룹 머리글을 추가했다. scope/colspan과 실제 colgroup 범위를 일치시켰다. 문장 비교표에는 그룹 행을 추가하지 않았다.
- 글자 축소·열 숨김·간격용 빈 열을 쓰지 않았다. 모바일 가로 스크롤은 table-card 한 곳이 담당한다. 계산은 빌드 시 수행하며 JS 비활성에서도 표를 읽을 수 있다.

## 구현과 재생성

`table_layout.py`는 메타데이터 누락/중복/남는 표, 머리글·열 개수 변경, 짝 schema 불일치, 경계를 가로지르는 병합 셀을 오류로 처리한다. JSON 없는 legacy 호출은 원래 HTML을 유지한다. 생성 그룹 행만 Markdown에서 제외한다.

`explain-stage --sync-explanation-template`은 명시된 문제설명 CSS 블록을 동봉 템플릿에 동기화한다. 이 CSS는 문제설명 루트 표식 아래에서만 작동한다. 최종 팩은 `.pack/problem-explanations/table-layout.json`으로 재생성 검사를 재현할 수 있다.

실험06은 Python `explanations.E`에서 풀이 조각을 생성하던 구조였다. 14개 결과가 기존 발행 조각과 바이트 단위로 같은지 확인한 후 표준 저작 폴더에도 저장했다. 생성기와 정적 조각의 일치 테스트를 추가했으며, 앞으로 RUN을 만들 때도 JSON을 복사한다. 두 표현의 유지 비용은 이 일치 검사로 감시한다.

## 검증 결과

- 신규 인터페이스 부재, CSS geometry, stage 옵션 부재가 실제로 실패하는 것을 확인한 후 구현했다.
- 독립 코드 리뷰는 짝 비트열 너비와 문장 열 min_rem의 두 예외를 재현했다. 각각 RED→GREEN 회귀 테스트로 수정했다.
- 그룹 머리글의 실제 열 그룹도 일치하도록 수정하고 구조 회귀 테스트를 통과했다.
- 관련 테스트: **130 passed**. 단위·콘텐츠·렌더러·stage·생성기 일치·전체 표 브라우저 검사 포함.
- 전체 표 브라우저 검사: 375/768/1280px × light/dark, 6개 팩의 모든 문항을 활성화했다. 신호 내용 폭 차이 1px 이하, 경계 padding, 짝 표 좌표, 줄바꿈 금지 값 잘림 없음, 페이지 넘침 없음, 카드 끝까지 스크롤, 스와이프 시 문항 유지, JS 오류·깨진 그림·수식 오류 없음을 확인했다.
- 6개 팩의 JS 비활성 상태를 검사했다. 별도 fixture에서는 3개 폭·2개 테마·JS 활성/비활성 조합을 확인했다.
- 신호·버스·상태식·문장 비교표 대표 4개의 스크린샷을 직접 검토했다.
- 원래 62개 표의 행 순서, 셀 종류/머리글/값/빈칸/colspan/rowspan을 생성 그룹 행만 제외하고 비교했다. **동일**.
- 86개 문항의 교육용 텍스트, 문항 ID, 링크, 그림 경로, 수식, 풀이 구역 순서를 비교했다. **동일**.
- 원문·문제은행 및 비대상 HTML/MD/PDF **521개 파일의 SHA256 동일**. Markdown 내용은 생성 그룹 행을 제외하므로 그대로 유지됐다. PDF 재생성은 수행하지 않았다.
- 최종 전체 테스트와 원래 작업 폴더 검사는 아래 실행 결과로 보완한다.

## 판단과 검증 범위

- 사용자 요청에 따라 커밋·푸시 없이 작업 diff로 전달한다. 격리 worktree에서 구현·검사한 뒤 원래 작업 폴더의 변경 여부를 검사하여 적용한다. 커밋 이력 대신 현재 diff를 검토해야 한다.
- 실험06의 Python 생성 결과와 정적 조각을 함께 보존한다. 생성기 일치 검사 실패 시 두 표현의 불일치를 해결해야 한다.
- 실제 스크린리더의 음성 안내는 시험하지 않았다. scope/colspan/colgroup의 DOM 구조를 검사했다. 브라우저/보조공학 조합에 따른 안내 차이는 남을 수 있다.
- 62개 전체는 자동 geometry·내용 검사, 직접 시각 검토는 대표 4개를 사용했다. 개별 표의 미세한 미관 판단까지 독립 리뷰가 보증하는 것은 아니다.
- 이번 검토는 기존 정답의 새로운 학술 심사가 아니다. explanation_checks의 content=self_review, browser=pass, source_visual=pass(기존 원문 및 교육 내용 보존 비교), independent=not_run으로 기록한다. 독립 코드 리뷰를 독립 정답 검토로 기록하지 않는다.

## 최종 전체 테스트

`.venv/bin/python -m pytest -q`: **3299 passed, 2 failed, 9 skipped**, 1248 subtests passed(117.05초).

남은 두 실패는 이번 변경 전 원래 작업 폴더에서 별도로 재현했다(같은 두 실패, 10 passed, 21 subtests passed). 해당 HTML/결선도 코드는 변경하지 않았다.

1. `tests/test_review_pack_work_table.py::test_published_payloads_obey_the_rule_and_match_the_source`: 기존 `PUBLISHED` 기대값에 실험06 문항이 없어 실제 work-table 표식과 다르다.
2. `tests/test_breadboard_diagram_cli.py::BreadboardCli::test_완성본끼리_빌더를_공유하지_않는다`의 실험06 subtest: `_finals()`가 f-string AST `JoinedStr`에 `.value`를 사용해 AttributeError가 난다.

초기 전체 검사에서 발견한 이번 변경의 동봉 템플릿 위치 불일치는 수정했다. 발행 백업이 학습팩 검색 glob에 걸리는 문제는 백업을 별도 보관 경로로 옮겨 해결했다. 최종 전체 검사에는 이 실패가 없다.

## 결과·증거 위치

- 원래 작업 폴더: `복습노트/실험01` ~ `복습노트/실험06`.
- 기존 파일 백업: `tmp/review-pack/table-layout-20261015-delivery/backups/실험NN`.
- 해시·표 셀 baseline, 테스트 전체 로그: `tmp/review-pack/table-layout-20261015-delivery/`.
- 시각 검토: [신호표](explanation-table-layout-20261015/signal.png), [비트열](explanation-table-layout-20261015/bus.png), [상태식](explanation-table-layout-20261015/state.png), [모바일 비교표](explanation-table-layout-20261015/comparison.png).
- 원래 작업 폴더에 반영한 뒤 여섯 pack check와 관련 회귀·브라우저 검사를 다시 수행한다. 커밋·푸시는 수행하지 않는다.

## 원래 작업 폴더 반영 후 확인

- 실험01~06 각각 `check_pack`: **OK (mechanical checks only)**.
- `.venv/bin/python -m pytest tests/test_review_pack_explanation_*.py tests/test_review_pack_table_layout*.py tests/test_review_pack_template_scrollbar.py -q -n 4`: **214 passed (31.50초)**.
- 최종 HTML의 62개 표 semantic snapshot과 비대상 파일 521개의 SHA256를 다시 대조: **동일**.
- `git diff --check`: 통과.
- 여섯 기존 폴더를 `tmp/review-pack/table-layout-20261015-delivery/backups/`에 보존했다. 코드/문서 변경 전 파일은 같은 실행 폴더의 `source-backup/`에 보존했다.
- 요청 범위의 코드·메타데이터·HTML·검증 자료만 작업 diff로 남겼다. 커밋·푸시는 수행하지 않았다.
