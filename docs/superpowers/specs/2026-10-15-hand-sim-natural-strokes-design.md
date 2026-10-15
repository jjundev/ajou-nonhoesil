# 손그림모사 배선을 자연스러운 벡터 펜 선으로 (2026-10-15)

## Intent
make-hand-sim 이 긋는 배선을 팀원이 덧칠하지 않고 그대로 써도 될 만큼 자연스럽게 만든다 — 팀원은
칩·LED·저항·이름만 그린다. 선은 지금보다 얇게, 원하면 덧칠할 수 있게. 실험06 에서 팀원이 손그림모사
2·3쪽 배선을 전부 덧칠한 원인 셋 — 안티앨리어싱 없는 래스터(계단현상), 사인 셋 합의 규칙적 출렁임,
가닥마다 ×0.7~1.3 의 제각각 굵기 — 이 모두 사라지고, 실험06 손그림모사를 다시 뽑아 태블릿에서
확대해도 펜 잉크처럼 매끈하면 끝이다.
Classification: bounded — 이미 있는 `hand=` 경로(엔진 `step_wire` 손그림 분기, `hand_sim.make_handout_pdf`)를 고친다.

## Behavior when done
- `실험NN_손그림모사.pdf` 의 쪽은 **빈 판형 PDF 쪽 그대로**(v2) 이고 배선은 그 위의 **PDF 벡터 선**이다.
  태블릿에서 얼마나 확대해도 매끈하다.
- 선은 쪽 전체가 한 굵기(0.9pt ≈ 2.0 논리 px)다. 긴 선은 한 번 살짝 휘고(최대 2.5 논리 px ≈ 홀 간격의
  13%) 미세한 떨림만 있다. 끝점·모서리는 홀·경로점 그대로다.
- 부품그리기 안내판은 같은 획을 회색으로, 안티앨리어싱해 그린다. 두 PDF 의 선 모양이 같다.
- 손그림모사 쪽의 판형 이미지가 빈 판형 원본과 같아 `review-hand-diagram` 격자 보정이 그대로 통과한다.
- 손그림 모드에서 배선 밖 그림이 판에 남으면(`instrument()` 프로브 등) 생성기가 이유를 대고 멈춘다.
- `hand` 없는 렌더(완성본·단계·따라그리기)는 픽셀 하나 바뀌지 않는다.

## Not in this round
- 필압 굵기 변화 — 윤곽 다각형 계산이 필요하다. 일정 굵기 볼펜이 태블릿 기본 펜과 같다.
- 팀원 손그림 학습 — 원인 셋이 모두 규칙으로 풀린다.
- 이미 제출된 실험06 2·3쪽(옛 래스터 배포본) 격자 보정 — 별도 `hand_grid` 작업.
- 부품그리기 안내판 벡터화 — HTML 로 줄여 싣는 그림이라 AA 래스터로 충분하다.
- `instrument()` 프로브 손그림화 — 쓰는 주차가 없다. 가드가 막는다.

## Approaches
| Option | Approach | Pro | Con | Chosen |
|---|---|---|---|---|
| A | 엔진 래스터에서 선마다 patch ×4 초과표본 후 축소·합성 | 변경 작음 | 309dpi 래스터라 확대 시 흐림 — 펜 잉크와 재질 차이 남음. 판형 이미지가 원본과 달라 검토 보정 문제 남음 | — |
| B | 엔진은 획 목록만 기록. 손그림모사 PDF 는 빈 판형 쪽 + 벡터 획, PNG·안내판 래스터는 같은 획을 MuPDF 로 AA | 배율 무관 매끈, 그리는 코드 하나, 판형 md5 원본 동일 | 획 기록·좌표 변환·가드 추가 | ✔ |
| C | 캔버스 전체 고배율 후 축소 | 단순 | 모든 렌더 변화(픽셀 불변 깨짐), 메모리·시간 큼 | — |

## Implementation spec
1. **획 모델 `engine/base.py`** — `_hand_noise`·`_hand_width` 삭제, 상수 `HAND_WIDTH = 2.0`,
   `HAND_DOT_R = 2.4`. `_hand_polyline(points, rng)`: 구간마다 **수직 방향만** 오프셋, 모서리·양 끝 고정,
   3 논리 px 간격. 오프셋 = 휨 `A·sin(π·t^k)` (A = ±U(0.4,1.0)·min(0.012·L, 2.5), k = U(0.75,1.35),
   L < 15 이면 휨 0) + 떨림(8px 간격 무작위 값 코사인 보간, ±0.25, 양 끝 6px 램프).
   `_hand_dot(p, rng)`: 반지름 HAND_DOT_R 축마다 ±10%, 중심 고정. `draw_strokes(page, strokes, to_pt, k)`:
   pymupdf Shape, 둥근 끝·이음, 점은 채운 타원. `strokes_layer(strokes, size, scale)`: 논리 크기 빈 쪽에
   그려 `alpha=True` 래스터 → PIL RGBA(MuPDF 표본은 premultiplied — `'RGBa'` 로 읽어 변환).
2. **엔진 `engine/renderer.py`** — `self.hand_strokes`. `step_wire` hand 분기와 `connect_unused_inputs`
   는 긋지 않고 획 기록. `export` 는 hand 면 `im + ghost + hand_layer + overlay` 로 합성(`self.hand_layer` 보관).
3. **생성기 `scripts/lab/hand_sim.py`** — `render_final` 이 손그림모사 bb 도 돌려준다.
   `make_handout_pdf(spec, bbs, out)`: overlay 가 비지 않으면 `ValueError`; v2 는 빈 판형 PDF 쪽을
   `insert_pdf` 로 복사, v1 은 템플릿 그림을 판 자리에 꽉 채움; `to_pt(x, y) = (slot.x0 + x·slot.width/W,
   slot.y0 + y·slot.height/H)`, 굵기도 같은 배율.
4. **시험 `tests/test_breadboard_hand.py`** — 모델 단위시험 교체, AA·premultiply·overlay 비움·md5·벡터 끝점·
   격자 보정·안내판 획 일치. hand 없는 `build_all` 픽셀 sha256 불변.
5. **문서 `.claude/skills/make-hand-sim/SKILL.md`** — 표·절차 4·정한 규칙·넓힐 때 손볼 곳 갱신.

## Decisions
### Confident
| # | Decision | Answer | Rationale |
|---|---|---|---|
| 0 | 접근 | B | 위 표 |
| 1 | 래스터 AA | 같은 획을 MuPDF 알파 래스터화 | patch ×4 는 긴 대각선 bbox 에서 수백 MB; 한 코드여야 두 PDF 선이 같다 |
| 2 | 획 레이어 위치 | overlay 아래 별도 레이어 | 가드를 overlay 비움으로 걸 수 있다 (renderer.py:46) |
| 3 | 손그림모사 바탕 | 빈 판형 PDF 쪽 그대로 | hand_grid.board_image 는 가장 큰 이미지를 판형으로 본다 (hand_grid.py:98) |
| 4 | 노이즈 | 구간별 활 하나 + 미세 떨림, 수직만 | 옛 모델: 축별 사인 셋, 파장 40~160 / 행 간격 19 |
| 5 | 굵기 | 쪽 전체 상수 | 옛 ×0.7~1.3 로 나란한 D·E 선 굵기 약 2배 차 |
| 6 | 끝점·모서리 | 고정 | 검토가 끝점 홀로 판정 |
| 7 | 미사용 입력선 | 같은 획 | 옛 곧은 draw.line (renderer.py:1073) |
| 8 | 배선 밖 그림 잔존 | 이유 대고 멈춤 | 스킬 규칙 |
| 9 | hand 없는 렌더 | 불변 | 픽셀 불변 절차 |
### Needs you (모두 확인됨)
| # | Decision | Answer |
|---|---|---|
| 10 | 선 굵기 | 0.9pt (2.0 논리 px) [confirmed] |
| 11 | 휨 세기 | 은은하게, 최대 2.5 논리 px [confirmed] |
| 12 | 실험06 재생성 | 다시 뽑아 커밋 [confirmed] |
