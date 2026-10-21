# 순차 관측 절차 구현 검증 (2026-10-21)

후속 실험07 v3 적용·실제 배치 결과는 [실험07 검증 기록](2026-10-21-e07-v3-placement.md)에 있다. 아래 내용은 공통 도구 구현 시점의 범위와 결과다.

B안 범위: v3의 저작한 확인 절차를 구조·의미 검증하고 단계 안에 인쇄한다. 회로 상태를 시뮬레이션하거나 실측 기록을 채우지 않는다.

## 환경과 기준선

격리 작업 공간: `/Users/hyunjun_macbook_pro/.codex/worktrees/sequential-observations/논회실`, 시작 HEAD `2966b1b`.
기존 Python venv를 사용했다. 첫 runtime 변경 전에 실험01·03·05·06을 같은 환경/경로에서 `parse_spec → parse_netlist → render_checklist`, `derive_record`로 저장했다. 대상은 기존 승인 자료이며 파일은 수정하지 않았다.

기준선 관련 테스트: **335 passed, 322 subtests passed**. 구현 후 네 실험의 HTML과 record 문자열이 모두 **바이트 동일**하다. SHA-256:

- `1.html`: `c22e2b2dd4193459fed94eb3f1bb8788b6d81aebdc985c6c9c8ae1c54855a1fb`
- `1.record`: `41469361e89b0e8ed60e6faa7d5237e7d48b906919ef14d1ab2e1783aff4d0e7`
- `3.html`: `db89161955a4d97b46bf2b0b5eb8805601f034126198a43c01d1cbc235be30b9`
- `3.record`: `4e24e11e6f8868c88a6f6bbc1c92ae8b45969f66446c4a5fb50a74bb7a2d8a99`
- `5.html`: `7f28c2212824529f87a31824893a41f050bda5496e808d79cef471263def8b71`
- `5.record`: `bdb2b87fb49a5322992f0b74741fe23e6abd8afb87e83a29ab1de42a3dd3e135`
- `6.html`: `8730cab580ebcdb380222ad5f35f1a94039ac7b13b025f432b8a8d482def9c48`
- `6.record`: `fea23c780e87fe5e845f9956167efa1f73e08cce0bef4876806dfae7ff808359`

## 수행한 검사

- parser RED→GREEN: v3 미지원으로 실패 후 86 passed, 14 subtests passed.
- observations RED→GREEN: 모듈 부재로 수집 실패 후 45 passed.
- validation RED→GREEN: 순차 노드·참조·출처·위치 검사 11개 실패 후 관련 21 passed.
- 단계/걷기/물리 배선/기존 검증 회귀: 606 passed, 52 subtests passed.
- render RED→GREEN: 절차 인쇄·LED·observed 계산 관련 8개 실패 후 244 passed, 308 subtests passed.
- 종단 통합: 4 passed. 이미 구현된 기능에 대한 종단 테스트여서 첫 실행부터 통과했으며 이를 RED라고 기록하지 않았다.
- 기록 보호: 동일 명세에서 절차 출력 전후 derive_record 동일, 채워진 write_record 거절 후 해시 동일.

## 논리 및 시각 확인

JK fixture의 CLR=0 초기화는 Q/Qbar=0/1, J=K=0 하강은 유지, J=K=1 하강은 반전으로 손검토했다. 6비트 fixture는 공통 CLR 초기화 후 첫 입력 1의 하강에서 100000, 다음 입력 0의 하강에서 010000이다. 상승·데이터 준비 행도 모두 유지한다. 이는 도구의 상태 계산 결과가 아니라 교안 동작으로 저작한 표본을 검토한 것이다. 실제 실험07 승인본을 대체하지 않는다.

시각 QA 임시 폴더: `/tmp/lab-observations-qa-20261021/`.
`render._stage_html → fit_pages → html_to_pdf`로 LED 1개(JK) 및 출력 6개 프로토콜을 격리해 인쇄했다. 전체 `render_checklist` 연결은 종단 테스트로 확인했다. Chrome headless 화면 캡처와 Poppler PDF PNG를 직접 열어 핀·조작·출처·유도 표시·에지·LED 번호/극성·확인 칸·마지막 행을 확인했다. 페이지 높이는 각각 415.37mm / 624.81mm로 조절됐으며 두 표의 순서가 보존되고 잘림이 없었다. 각 절차는 한 쪽에 들어가므로 강제 페이지 분할은 발생하지 않았다. CSS는 표 헤더 반복을 선언한다.

원래 fixture에는 보드/단계 그림/입력 위치가 없고, 해당 경고를 숨기지 않았다. 화면 검사용 LED 목록은 합성 데이터다. R7~R10 실물 배치, 실험07 결선도 PNG, 실제 장비 동작은 검증하지 않았다.

## 스킬 검증

수정 전 별도 에이전트 압박 테스트: 기존 draft는 순차 Q에도 기록 진리표 입력의 식을 요구해 v3 observed 경로를 안내하지 못했고, prep은 NetlistError를 회로메타 누락으로 단정했다. 승인본·작성된 기록 보호 규칙은 기존에도 있었다. 수정 후 같은 에이전트가 네 상황을 재검토해 observed/절차 라우팅, 실측 분리, 승인본/기록 보호, NetlistError 원인 단정 제거를 확인했다. 기존 expression 계산 안내와 v3 예외의 범위가 모호하다는 후속 지적은 표제와 별도 v3 항목으로 명확히 했다.

## 최종 회귀 및 리뷰

아래 fresh 리뷰 및 최종 전체 테스트 결과를 참조한다.

기존 실패 재현: 원본 작업 공간의 동일 HEAD에서 `pytest -n0 tests/test_breadboard_boards.py::CommittedPngs_e05::test_결선도_폴더가_코드와_같다 -q`도 실패했다. PNG 도장 이후 사이드카 JSON 12개 바이트 대조가 실패하며, 승인 자료를 재생성해 감추지 않았다.

## Fresh 전체 변경 리뷰 및 수정

별도 gpt-6-astra 리뷰어가 새 파일까지 읽기 전용으로 검토했다. Critical 없음. Important 3건(이전 LED의 이름 충돌, 설명 없는 참조의 닫는 백틱 손실, 깨진 PDF 예외 누출)을 수용했다. 미사용 expression의 미완성 문법을 통과시키는 Minor 1건은 검증 계약에 영향을 주므로 Important로 올려 함께 처리했다. 보류한 경미 지적은 없다.

재현 테스트에서 5개 실패(미완성 식은 2개 매개변수)를 확인한 뒤 한 수정 패스로 처리했다. `feeds_by_circuit`는 v3에서 물리 급전 핀을 보존하고 현재 회로 이름으로 변환한다. 같은 이름/다른 핀은 관측 안 함, 다른 이름/같은 핀은 같은 관측점이다. v2 이름 기반 경로는 유지한다. 원시 확인 셀을 보존해 정상 참조를 읽고, PyPdfError는 warn으로 보고하며, expression은 값 추론과 별개로 문법을 검사한다.

새 parser 테스트의 `stage['node']`를 기존 외부 Node 의존성 탐지 정규식이 오인한 전체 테스트 실패도 확인했다. 동일한 동작 검증을 `stage.get('node')`로 작성해 오탐을 피했다. 도구 의존성 설정이나 제품 동작은 바꾸지 않았다.

수정 후 관련 **407 passed, 322 subtests passed**. 실험01·03·05·06의 HTML/record **8개 모두 기준선 바이트 동일**을 다시 확인했다. 전체 테스트 최종 결과는 아래에 기록한다.

## 작업 중 판단과 한계

- 격리된 관리 작업 공간을 사용하고 원본 checkout을 보존했다. 수정은 첨부 작업 공간에 있으며 커밋/푸시/병합하지 않았다. 원본에 적용하려면 별도 통합이 필요하다.
- 문서 내용 문자열을 검색하는 테스트 대신 전체 Markdown 예제를 실제 파싱·의미 검증했다. 스킬 지시 판단은 수정 전/후 별도 에이전트 압박 테스트로 보완했다. 일반 산문 정확성은 자동 증명이 아니다.
- LED 핀 조회는 기존 전체 노드 조회를 유지하고, 리뷰에서 발견된 회로 간 정체성만 물리 핀 기반 새 경로로 보강했다. v2 렌더/기록 계약은 유지한다.
- 승인된 실험05 자산·실험06 학습팩·기존 breadboard 스킬을 바꿔 이번 구현의 테스트 숫자를 맞추지 않았다. 이들 기존 실패 때문에 전체 green을 주장할 수 없다.
- 단계만 격리한 화면/PDF QA와 전체 체크리스트 종단 테스트를 함께 사용했다. 실제 보드가 포함된 실험07 전체 PDF 시각 QA는 후속 작업이다.
- 저작 기대값의 논리·초기화 정확성은 교안과 손검토의 영역이다. 이번 도구는 이를 계산하거나 증명하지 않는다.
- 실제 실험07 배치/그림/승인본 적용은 이번 범위 밖이다. 실험07 산출물에 v3 절차를 적용하는 작업이 남는다.
- 리뷰에서 secondary observe 핀/예상은 전체 observe 목록을 인쇄함을 확인했으므로 별도 누락 수정은 하지 않았다. 해당 노드를 다시 계산 표로 인쇄하지 않는다.

## 확인된 기존 전역 실패

원본 checkout에서 다음 11개를 모두 재현했다. 이번 작업에서 관련 원본 파일은 수정하지 않았다.

- `tests/test_breadboard_boards.py::CommittedPngs_e05::test_결선도_폴더가_코드와_같다`: 저장된 사이드카 JSON 12개가 생성 결과와 다름.
- `tests/test_review_pack_explanation_published.py::test_experiment_coverage[6-14]`, `::test_recall_published[6-14]`: 기대 개수 14와 실제 24 불일치.
- `tests/test_review_pack_table_layout_browser.py::test_all_managed_tables[light-375-6]`, `[light-768-6]`, `[light-1280-6]`, `[dark-375-6]`, `[dark-768-6]`, `[dark-1280-6]`, `::test_published_managed_without_javascript[6]`: 기대 표 14와 실제 16 불일치.
- `tests/test_skill_docs.py::BreadboardSkillSize::test_본문이_상한_안이다`: 기존 스킬 40390B가 40000B 상한을 넘음.

브라우저 회귀 테스트가 쓰는 validation 화면 이미지 두 개는 실행 후 HEAD 바이트로 복원한다. 승인 보고서·복습노트·기록·배치.py 변경은 없다.

## 최종 결과

- 최종 전체 명령: `.venv/bin/python -m pytest -q`.
- **3546 passed, 11 failed, 9 skipped, 1252 subtests passed** (136.83초). 실패 11개는 위에서 원본 재현한 항목과 정확히 같으며, 이번 변경으로 남은 새 실패는 없다. 전체 green은 아니다.
- 새 기능/문서/스키마 집중 검사: **74 passed**. 기존 파서·계산·LED·렌더까지 포함한 관련 검사: **407 passed, 322 subtests passed**.
- 마지막 코드로 두 PDF를 다시 만들고 Poppler PNG를 직접 열어 잘림이 없음을 재확인했다. 794px에서 긴 입력명 `SERIAL_DATA_FROM_EXTERNAL_SIGNAL_GENERATOR_AND_MANUAL_SWITCH`로 Chrome 화면도 확인했다. 넘치는 셀 0개, 입력·결과 각각 8행 순서 보존.
- `git diff --check` 통과. 테스트가 쓴 navigation PNG 두 개는 HEAD 바이트로 복원했다. `보고서/`, `복습노트/`, `output/`의 tracked diff는 없다. 원본 checkout 상태도 시작과 같다.
- 브랜치 `codex/sequential-observations`, 커밋/푸시/원본 병합 없음. 원본 실험07 명세/netlist 적용 및 실물 배치는 후속 작업이다.
