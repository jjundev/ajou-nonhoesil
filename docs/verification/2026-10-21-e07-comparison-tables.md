# 실험07 관측·기록표 한 행 비교

## 결과와 범위

Native managed 작업 공간을 재사용한 `codex/e07-comparison-tables`에서 구현했다.
V1~V12와 T1~T3을 입력·조작/예상/실제 결과 한 행 비교로 바꿨다.
V1~V6은 프로브 핀·예상 논리값, V7~V12와 T1~T3은 예상 켜짐·소등을 표시한다.
실제 결과는 일치 ✓, 불일치 실제값, 미확인 공란이다. 초기 실측값을 생성하지 않았다.
T1 입력은 시간순 101100이며 BIT1→BIT6 예상 상태는
100000 → 010000 → 101000 → 110100 → 011010 → 001101이다.
T2·T3의 PR 활성·해제·시프트 순서를 유지했다.
회로·보드 자산·준비6·기능12·걷기11은 바꾸지 않았다. PDF는34쪽을 유지한다.
다른 실험의 산출물은 재생성하지 않았다.

## 구현과 호환성

- 명세의 선택 `comparison: led`와 outputs로 예상 논리값을 선언한다.
- 선택한 비교 스텝표만 실제 결과 칸을 만든다. 원래 stepped의 빈 실측 칸은 유지한다.
- v3 절차의 선택 layout:inline만 한 표로 만든다. 생략 시 기존 split이다.
- 두 산출물은 사이드카 LED 번호·극성을 같이 읽는다. 유지·반전·미정·관측 안 함을 소등과 구별한다.
- 비어 있는 이전 기록은 변경 전 명세에서 파생한 previous_template과 대조해 이행했다.
  헤더/행/셀 구조·고정 입력이 달라지거나 실제 기록이 있으면 보존한다. force는 사용하지 않았다.

## 검증

테스트 최초 실패를 확인한 뒤 구현했다. 기본 기능9개 RED→GREEN, E07 저작2개 RED→GREEN.
독립 리뷰 이후 추가행/셀구조 보호와 기록 비트순서 안내도 RED→GREEN으로 검증했다.
수정 후 관련 테스트52개와30subtests가 통과했다.

실제 HTML에는 비교표15개, 비어 있는 실제 결과126칸이 있다. 기록 T1~T3의25행도
실제 결과가 공란이며 명세/결선/HTML/이미지 검증 오류는0이다.
PDF34쪽의 폭은 모두209.9mm다. Poppler로 V1(9쪽), V6(19쪽), V12(31쪽),
T1~T3(33쪽)을 렌더해 표와 필기 공간을 확인했다. T1은 폭1200px 확대도 확인했다.
클리핑·겹침은 없으며 단계의 전체 그림·표가 기존처럼 하나의 가변 높이 페이지에 있다.
실물 통전 동작을 검증한 것은 아니다.

## 독립 리뷰와 판단

fresh-context reviewer가 Critical0, Important1, Minor1을 보고했다.
추가 관측행이 이전 템플릿 범위를 벗어나 실측 보호를 빠져나가는 Important는 구조 대조로 고쳤다.
기록.md의 BIT순서 안내 누락은 물리 LED순서와 달라 실제값 오기입을 유발하므로 Important로
재분류해 같은 수정 패스에서 보완했다. 미해결 리뷰 지적은 없다.
이전 조립 작업의 기록 파일 바이트 고정 검사는 이번 승인된 기록 형식 변경으로 만료됐다.
보드 스냅샷·경로·넷의 기존 비교는 유지했다.

## 기존 전체 테스트 실패

실험05의 저장된 사이드카 바이트 차이와 실험06의 복습팩 표 개수 문제는 기존 main에서도
확인된 실패이며 이번 변경에 포함하지 않았다. 실패 식별자는 다음과 같다.

- tests/test_breadboard_boards.py::CommittedPngs_e05::test_결선도_폴더가_코드와_같다
- tests/test_review_pack_explanation_published.py::test_experiment_coverage[6-14]
- tests/test_review_pack_explanation_published.py::test_recall_published[6-14]
- tests/test_review_pack_table_layout_browser.py::test_all_managed_tables[light-375-6]
- tests/test_review_pack_table_layout_browser.py::test_all_managed_tables[light-768-6]
- tests/test_review_pack_table_layout_browser.py::test_all_managed_tables[light-1280-6]
- tests/test_review_pack_table_layout_browser.py::test_all_managed_tables[dark-375-6]
- tests/test_review_pack_table_layout_browser.py::test_all_managed_tables[dark-768-6]
- tests/test_review_pack_table_layout_browser.py::test_all_managed_tables[dark-1280-6]
- tests/test_review_pack_table_layout_browser.py::test_published_managed_without_javascript[6]

## 최종 전체 검사

`.venv/bin/python -m pytest tests -q`: 3612passed / 10기존실패 / 9skipped /
1324subtests / 52warnings, 128.64초. 실패ID는 직전 main 검증의10개와 집합이 같다.
테스트가 갱신한 범위 밖 navigation PNG2개는 복원했다. git diff --check 통과.
작업은 Native feature 브랜치에 보관하며 main 병합·원격 push는 하지 않았다.
