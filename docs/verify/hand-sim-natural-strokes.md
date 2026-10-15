# 손그림모사 벡터 출력과 안내판 쪽 넘침 검증

검증일: 2026-10-15. 브랜치: `hand-sim-natural-strokes`.

## 구현

- 계획 Task 1·2의 획 모델과 MuPDF 안티앨리어싱 레이어를 그대로 사용한다.
- `render_final`이 손그림모사 renderer도 반환한다. PDF 생성기는 v2 빈 판형 PDF의 첫 쪽을
  복사하고 같은 획 목록을 벡터로 얹는다. v1은 기존 템플릿 이미지 위에 벡터를 얹는다.
- 손그림모사 renderer의 overlay에 배선 밖 그림이 남으면 생성하지 않고 이유를 보고한다.
- 안내판 그림 높이 상한을 230mm에서 220mm로 줄였다. 쪽 크기, 표 글자 크기, 표 행은 유지했다.
- 재생성 결과를 비교하는 스킬 절차에 쪽 크기와 `get_drawings()`를 포함했다. 판형 이미지만 같다고
  배선 변경을 버리지 않도록 한다.

## 넘침 원인과 재현

기존 실험05 BCD 안내판은 Windows의 현재 글꼴 환경에서 그림·범례·25행 부품표의 총 높이가
1509.73px였다. 인쇄 가능 높이는 `(420-12-12)mm = 1496.69px`여서 마지막 `Bit3` 행이 다음 쪽으로
밀렸다. 기존 테스트는 2쪽 대신 3쪽, 쪽별 그림 `[1, 0, 1]`로 실패했다.

220mm 상한을 적용한 총 높이는 1471.94px이다. 진단 출력은 2쪽, 그림 `[1, 1]`이며 `Bit3`와 그 자리
`레일 쪽 끝 중앙GND레일7행 옆`이 첫 쪽에 들어간다. 기존 PDF 쪽 수 회귀 테스트에 마지막 행 확인도 추가했다.

## 시험

- 구현 전: `HandSimScript` 7 failed, 12 passed. 추가한 벡터·판형·격자·overlay 시험 5개와
  기존 실험05 쪽 넘침 시험 2개가 실패했다.
- 구현 후: `python -m pytest tests/test_breadboard_hand.py -q` → **54 passed**, 69.13초.
- 전체 시험: `python -m pytest -q` → **3233 passed, 11 failed, 7 skipped,
  1248 subtests passed**, 282.57초. 전체 통과 상태는 아니다. 아래 11개는 이번 수정 전 커밋
  `d21ac5c`에서 필요한 원본 파일 821개를 별도 스냅샷으로 추출하여 동일하게 재현했다.
- 실패한 범위만 직렬 분리 실행: 현재와 수정 전 스냅샷 모두 **11 failed, 2 passed,
  5 subtests passed**. 이번 변경과 무관한 기존 실패로 구분하며 이 작업에서 수정하지 않는다.
- 앞선 Task 2의 일반 렌더 픽셀 비교는 63장 모두 불변이었다. 이후 변경은 손그림모사 생성기·시험·문서뿐이며
  일반 렌더 엔진과 주차별 빌더는 수정하지 않았다.

### 수정 전부터 존재한 전체 시험 실패

- `test_review_pack_work_table.py::test_published_payloads_obey_the_rule_and_match_the_source`:
  실험06 발행본의 표 표시 문항 4개가 기대 집합과 다르다.
- `test_review_pack_explanation_stage.py`의 다음 9개:
  Windows fixture의 `str(relative_path)`가 역슬래시를 만들어 manifest의 안전한 경로 계약과 충돌한다.
  같은 경로 표현 차이로 보존 비교도 실패한다.
  - `test_stage_preserves_existing_bytes`
  - `test_explanation_only_rerun_is_deterministic`
  - `test_check_detects_missing_or_modified_explanation[delete]`
  - `test_check_detects_missing_or_modified_explanation[body]`
  - `test_check_detects_missing_or_modified_explanation[link]`
  - `test_unreviewed_explanation_cannot_publish`
  - `test_original_publish_guards_remain`
  - `test_duplicate_html_id_cannot_break_question_navigation`
  - `test_workbook_question_and_review_anchors_are_valid`
- `test_breadboard_diagram_cli.py::BreadboardCli::test_완성본끼리_빌더를_공유하지_않는다`의 실험06 subtest:
  `_finals`가 파일명의 f-string AST(`JoinedStr`)를 일반 상수처럼 `.value`로 읽는다.

## 실험06 재생성

기존 PDF 두 개를 먼저 별도 보관한 후 `python -m scripts.lab.hand_sim --experiment 6`을 실행했다.

| 검사 | SR | D | JK |
|---|---:|---:|---:|
| 손그림모사 벡터 배선 수 | 18 | 21 | 15 |
| 배선 굵기(pt) | 0.9317 | 0.9317 | 0.9317 |
| 원본 판형 이미지 md5 일치 | 예 | 예 | 예 |
| 격자 보정 잔차 x/y(px) | 0/0 | 0/0 | 0/0 |
| PDF 쪽 텍스트 길이 | 0 | 0 | 0 |
| 안내판 부품표 행 수 | 8 | 8 | 10 |

두 PDF 모두 3쪽이고 쪽마다 이미지가 하나다. 손그림모사는 66,273,385바이트에서 211,447바이트로
줄었다. 안내판은 726,518바이트이며 모든 표가 쪽 안에서 끝난다.

전체 6쪽을 90dpi로 렌더하고 손그림모사의 입력 배선 부근 3곳을 600dpi로 확대해 확인했다.
손그림모사는 부품·입력 배지가 비어 있고 입력 점퍼선은 남아 있다. 안내판 배선은 회색이며 색 부품과
표가 표시된다. 확대 배선은 일정한 굵기이고 가장자리가 매끈하다.

## 독립 검토

별도 리뷰어가 전체 변경과 출력물을 읽기 전용으로 검토했다. Critical/Important/Minor 지적은 없었다.
실험06 모든 벡터 꼭짓점과 획 목록의 좌표 차이는 0.000046pt 미만이며, 누락된 획이 없었다.
손그림모사와 안내판의 획 좌표·굵기·도트가 같고, 안내판 부품표의 모든 셀 내용이 PDF에 있음을 확인했다.
