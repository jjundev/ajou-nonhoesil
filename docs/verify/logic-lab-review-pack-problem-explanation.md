# 문제설명 HTML 검증 — 2026-10-10

실험설명을 한 번 읽은 학생이 첫 문제풀이를 시작하도록 실험01~05의 모든 72문항을 설명했다. 현재 문제지의 번호·ID·순서·입력 조건·소문항을 유지했다. 문제설명 HTML/MD는 기존 note-template과 로컬 자원을 재사용한다. 풀이·정답은 본문에 펼쳐 있고, 우측 요약과 읽음 저장은 실험설명과 분리된다.

## 실제 확인 결과

| 실험 | 문항 | 화면 조건별 전체 문항 검사 | 보존한 기존 파일(manifest 제외) |
|---|---:|---:|---:|
| 01 | 12 | 48 | 170 |
| 02 | 14 | 56 | 184 |
| 03 | 15 | 60 | 162 |
| 04 | 12 | 48 | 166 |
| 05 | 19 | 76 | 172 |
| 합계 | 72 | 288 | 854 |

- 375px/1280px × light/dark에서 모든 문항을 실제 Chrome으로 확인했다. pageerror·깨진 그림·KaTeX 오류·문서 전체 가로 넘침은 0이다. 표·수식은 본문 안에서 필요시 스크롤된다.
- 5개 문서 모두 JavaScript 비활성에서 전체 문제·목차·완성 풀이를 읽을 수 있다. fixture와 발행본 테스트에서 현재 목차/이전·다음/요약/모바일 drawer·잘못된 hash·읽음 저장 분리와 유지도 확인했다.
- 기존 문제지 PDF 전체 72쪽을 렌더링하여 표의 기입 행, 회로와 출력/입력 열 순서, 각 문항 요구를 payload와 대조했다. 소문항·첫 줄·검산 표는 각 `자료/problem-explanations/검증결과.md`에 있다.
- 기존 설명·문제·풀이·PDF·자료 854개는 구현 시작 commit `2dca1db`와 발행 전 snapshot 둘 모두에 대해 바이트가 같다. 변경한 기존 파일은 각 팩 manifest뿐이다. 원문·문제은행·보고서 파일은 수정하지 않았다.
- 55개 완성 진리표 행을 별도 계산으로 대조했다. NAND XOR/3입력 NAND/NOR·드모르간·Switching 식·가산기/감산기 산술 항등식·MUX/DMUX 선택·NAND 인코더 one-hot·Excess-3 보수 짝은 입력 조합을 전수 계산했다. 서술형 설명의 과도한 일반화도 보완했다.
- 실험03의 IC 지정 회로에는 이미 A/B/S/Co와 IC 이름이 표시된 완성 SVG가 있어, 중복 추가 그림을 제거했다. 원래 회로 그림은 보존했다.

## 명령과 결과

```sh
.venv/bin/python -m pytest -n0 tests/test_review_pack_*.py -q
# 433 passed in 64.26s

.venv/bin/python -m scripts.lab.review_pack check --folder 복습노트/실험01
# 실험01~05 모두 OK (mechanical checks only)

git diff --check
# 오류 없음
```

생성 계약·위험 경로·문항 누락/중복/순서/번호·불확실성 표시·출처 MD·기존 파일 보존·미검토 발행 거절·신규 build의 네 HTML/MD·브라우저 검증을 포함한다. pytest-xdist/playwright/pymupdf/pypdf는 격리 `.venv`의 테스트 도구이며 런타임 의존성을 추가하지 않았다.

## 판단과 제한

내용 검토는 저자가 수행하여 `content=self_review`로 기록했다. 별도 reviewer가 전체 코드를 검토하더라도 72문항의 독립 블라인드 풀이를 완료한 것은 아니므로 각 팩의 `independent=not_run`을 유지한다. 기존 disputed/unresolved 답안 상태를 바꾸지 않았다. 실험05의 우선순위 방향·칩명 불일치도 원문 조건/해석에 남겼다.

실험02 netlist 원문 해시가 CRLF 기준이었다. 현재 LF 바이트를 CRLF로 변환한 해시가 이전 값과 정확히 일치했으므로 내용 동일을 확인했고 manifest의 원문 해시만 현재 파일 값으로 갱신했다. 원문 파일과 기존 문서의 바이트는 그대로다.

publish의 sibling 백업을 기존 테스트가 active pack으로 읽어 두 테스트가 실패했다. 이번에 생성한 백업 5개를 삭제하지 않고 `tmp/explanation-audit/backups/`로 이동하여 구분했다. 검증 이후 변경이 있는 항목은 해당 검사를 다시 수행했다.

## 증거 위치

- `output/validation/problem-explanations/expNN-browser.json`: 실제 문항/화면 조합.
- `output/validation/problem-explanations/expNN-preservation.json`, `final-preservation.json`: 전후 파일 hash와 원래 commit.
- `output/validation/problem-explanations/*-teaching.png`: 풀이·회로·파형·첫 줄 화면.
- `docs/learning-pack-source/실험NN/problem-explanations/`: 재현 가능한 저작 원고와 내용 대조표.

## 별도 최종 코드 리뷰

새 리뷰어가 읽기 전용으로 신규 모듈·발행·rerender·목차 갱신 연동과 실험별 설명 16개를 표본 검토했다. 표본에서 명백한 논리식·계산 오류를 발견하지 않았으며, 다음 P2 두 건을 보고했다.

1. 조립 문서의 중복 ID가 문항 목차 이동을 방해할 수 있음: 조립 시와 검사 시 전체 ID 중복을 거절하도록 수정했다.
2. 기출풀이 문항 앵커는 워크북 payload에서 동적으로 생성되어 정적 앵커 검사로는 오판함: 문제지·풀이 문서 앵커를 payload ID로 검증하도록 수정했다.

두 건 각각 실패 재현 테스트를 실행하여 실제 실패를 확인한 뒤 수정하여 통과했다. 독립 블라인드 풀이를 실시한 것은 아니므로 각 팩의 independent 상태는 not_run을 유지한다. 리뷰에서 판단을 보류한 항목과 미해결 minor는 없다.

최종 수정 후 전체 스위트: 433 passed in 64.26s. 5개 최종 팩 검사와 git diff --check도 통과했다.

## 단락 간격 수정 (2026-10-10)

`문제 읽기` 뒤에 오는 `.layer.eli5`에 첫 단락용 간격 제거 규칙이 적용되어 제목 위 간격이 0px이었다. 생성본의 375px/1280px × light/dark 회귀 검사에서 실제 간격 0px로 네 조건 모두 실패하는 것을 확인했다. 공통 note-template에 `.layer + .layer.eli5` 규칙을 추가해 위 여백 24px, 안쪽 여백 24px, 구분선 1px를 적용했다. 실험01~05의 저장 템플릿과 문제설명을 재생성하고, upstream provenance를 유지한 채 local_adjustments에 수정본 해시를 기록했다. 기존 실험설명/문제지/풀이/MD 내용은 변경하지 않았다.

생성본 검사와 모든 72문항 × 네 화면 조건(288개)의 간격 검사를 자동화했다. 간격이 다시 사라지거나 구분선이 제거되면 실패한다. 검증 스킬 지침에도 같은 기준을 추가했다. 실제 실험설명의 첫 eli5 단락은 기존 여백 0px를 유지하는지 함께 확인한다. 첨부 이미지 문항(실험04 q-decoder)의 수정 화면은 `output/validation/problem-explanations/section-spacing-dark.png`에 보존했다.

최종 검증: `check_pack` 다섯 팩 통과. 생성본 네 화면 조건과 발행본 288개 간격 검사 통과. `pytest -n4 -q` 전체 실행은 2883 passed, 1206 subtests passed, 9 skipped, 1 failed(70.11s). 유일한 실패는 변경하지 않은 `tests/test_merge_report.py::TestIntegration::test_merge_lab_report_warns_when_body_cannot_be_removed`이며 단독 실행에서도 실패한다. 보고서 병합의 삭제 실패 경고 테스트이고 이번 HTML/CSS 변경과 무관하다. 22 warnings는 기존 Pillow deprecated API 경고 등이다. 검증 중 새 회귀 테스트의 실험설명 예제에 eli5 요소가 없었던 테스트 오류를 발견하여 실제 발행 실험설명으로 간격 보존을 검사하도록 수정했다. 최종 실행에서 문제설명 관련 실패는 없다. 기존 발행 HTML/MD/PDF 65개는 HEAD와 바이트 동일함을 확인했다. `git diff --check` 통과.

## 수식 카드 수정 (2026-10-10)

첨부 문항 `q-ha-design-eq`의 식 `S = x′y + xy′, C = xy (1)`이 일반 문단으로 표시되는 것을 확인했다. `equation_cards.py`에서 HTML 위치를 기록해 독립 수식 문단만 카드로 감싼다. 원래 문단의 텍스트·태그·LaTeX·식 번호를 그대로 보존하고, 설명 문장과 이미 만든 수식 카드는 건드리지 않는다. 문제 읽기와 저작 설명 모두 렌더링 시 적용하여 향후 생성에도 반영한다. 다섯 팩의 독립 수식 32개(14/2/2/7/7)를 분리했다. 배경·1px 테두리·16px 안쪽 여백·내부 가로 스크롤을 공통 템플릿에 추가하고 저장 템플릿 및 local_adjustments 해시를 동기화했다.

일반식/블록 LaTeX/독립 inline LaTeX가 문제와 풀이 모두 카드가 되는지 RED(세 조건 카드 수 0)→GREEN을 확인했다. 원래 문장·기존 카드가 보존되는 검사도 통과했다. 모바일 긴 수식의 터치 제스처가 다음 문제로 넘기는 문제를 추가로 재현하여(두 theme 모두 hash 변경) 카드 내부는 페이지 넘기기에서 제외했고 두 조건 모두 통과했다. 전체 문항 화면 검사에서 카드 테두리·배경·여백·스크롤 스타일을 검사한다. 기존 간격 회귀 검사도 유지한다.

다섯 팩 check_pack 통과. 기존 발행 HTML/MD/PDF 65개는 HEAD와 바이트 동일하다. 원문 PDF와 문제지의 수식은 변경하지 않았다. 첨부 문항의 dark 1280px 및 light 375px 화면을 `output/validation/problem-explanations/equation-card-*.png`에 보존하고 시각 확인했다. 저작 및 검증 지침에 독립 수식 문단과 카드/스크롤 기준을 추가했다.

최종 전체 실행 `pytest -n4 -q`: 2889 passed, 1206 subtests passed, 9 skipped, 1 failed(60.34s). 유일한 실패는 앞서 독립 재현한 기존 `TestIntegration::test_merge_lab_report_warns_when_body_cannot_be_removed`이며 수식/간격/브라우저 관련 검사는 모두 통과했다. `git diff --check` 통과.

## main 통합 검증 (2026-10-10)

간격·수식 카드 수정 커밋 `b3fabfd`를 포함하여 main의 도입 설명 개선(403b649)과 통합했다. 다섯 manifest 충돌은 서로 다른 저작 정보는 각각 유지하고, generated_files는 양쪽의 추가와 기존 항목 삭제를 반영하여 해결했다. 현재 main의 기존 학습자료 844개(의도적으로 갱신한 manifest/저장 템플릿/provenance 제외)는 바이트 그대로 보존했다. 통합 상태에서 다섯 팩 check_pack 통과.

통합 전체 테스트: 2903 passed, 1206 subtests passed, 9 skipped, 1 failed(79.23s). 실패는 앞서 공개한 기존 `tests/test_merge_report.py::TestIntegration::test_merge_lab_report_warns_when_body_cannot_be_removed` 한 건이며, 문제설명·간격·수식 카드·도입 설명 검사는 통과했다. 사용자가 해당 실패가 보고된 상태에서 커밋 및 main 병합을 요청하여, 이를 기록하고 로컬 통합했다. 원격 push는 하지 않는다.

## 표 카드 수정 (2026-10-10)

문제설명의 일반 표가 본문에 붙어 보이는 요청에 따라 `table-card`를 추가했다. `table_cards.py`는 표 HTML 전체의 위치를 기록하여 바깥에 카드만 추가하며, 머리·주어진 값·빈칸·rowspan/colspan 및 기존 table-wrap/work-table은 변경하지 않는다. 이미 작성한 카드는 중첩하지 않는다. 문제 읽기와 저작 설명 모두 적용되어 다섯 팩의 표 48개(9/0/8/12/19)를 카드로 분리했다. 수식 카드와 같은 배경·테두리·여백 및 내부 가로 스크롤을 사용한다. 표 카드는 터치 문제 넘김에서 제외한다. 저작/검증 스킬 지침에도 기준을 반영했다.

생성본의 문제/풀이 표 카드와 기존 카드 보존 검사를 추가하고 카드 수 0으로 실패하는 것을 확인한 뒤 구현하여 통과했다. 375px/1280px × light/dark에서 넓은 표의 내부 스크롤·빈칸 보존·문서 가로 넘침·터치 문제 넘김 방지 검사를 추가했고 통과했다. 모든 발행 문항에서 표가 카드 안에 있는지와 카드 스타일을 검사한다. 기존 식/간격 검사는 유지한다.

다섯 팩 check_pack 통과. 기존 발행 HTML/MD/PDF 65개는 HEAD와 바이트 동일함을 확인했다. 첨부 문항 `q-prio-onehot`의 dark 1280px 및 light 375px 화면은 `output/validation/problem-explanations/table-card-*.png`로 보존했다.

최종 전체 테스트: 2909 passed, 1206 subtests passed, 9 skipped, 1 failed(85.78s). 실패는 기존 `TestIntegration::test_merge_lab_report_warns_when_body_cannot_be_removed` 한 건이며 표/수식/간격/브라우저 관련 검사는 모두 통과했다. `git diff --check` 통과.
