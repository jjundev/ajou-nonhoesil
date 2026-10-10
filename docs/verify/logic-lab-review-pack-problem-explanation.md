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
