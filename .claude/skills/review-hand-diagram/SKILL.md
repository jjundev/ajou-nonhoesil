---
name: review-hand-diagram
description: 학생이 배포본 브레드보드 판형 위에 손으로 따라 그린 결선도 PDF 를 승인된 참조 결선도와 대조해 쪽별 판정과 증거 크롭을 낸다. 사용자가 "손그림 검토해줘", "따라 그린 거 확인", "브래드보드 작도 확인", "이거 이대로 제출해도 돼?" 등을 요청하거나 /review-hand-diagram 을 호출할 때 사용한다. 홀 좌표가 아니라 넷으로 비교하므로 칩이 몇 행 밀려도 배선이 함께 옮겨져 있으면 통과시킨다.
---

# review-hand-diagram

손그림 결선도를 참조와 대조한다. **판단은 전부 코드가 한다** — 이 문서는
전사(轉寫)를 어떻게 적을지와 결과를 어떻게 낼지만 정한다.

## 왜 코드가 판단하는가

2026-09-08 회차에서 사람이 눈으로 대조하다 **LED 사슬 검사를 통째로 건너뛰었다.**
칩별 전원·미사용핀·신호선만 보고 통과시켰는데, 재검토에서 저항이 한 행 위에
꽂혀 LED 가 아예 안 켜지는 것이 나왔다. 절차서를 더 써서 막을 수 있는 종류가
아니다 — 절차는 이미 알고 있었고 그중 하나를 건너뛴 것이다.

그래서 검사를 `scripts/lab/hand_compare.py` 의 `_RULES` 목록에 넣었고,
`tests/test_hand_compare.py` 가 **`check_` 로 시작하는 함수가 전부 목록에
올라 있는지** 검사한다.

## 인자

`<N주차|실험N> <PDF 경로> [round<N>]`

- 번호 토큰이 없으면 한 줄로 되묻고 중단한다.
- `round<N>` 이 없으면 기존 `round*` 폴더 중 최대 번호 + 1 을 쓴다.
- 출력 폴더는 `<실험NN>/output/손그림검토/round<N>/` 이다.

## 실행 절차

### 1. 실험 번호를 폴더 이름으로 옮긴다

사용자는 "실험1", "2주차", "다음 실험" 으로 부르고 경로는 `<실험NN>/` 이다.
손으로 `실험1` 이라고 적지 않는다 — 0 을 안 채우면 `실험10` 이 `실험2` 앞에 선다.

```bash
python3 -c "
from scripts.lab import config
print(config.experiment_dir(<실험번호>))
"
```

주차로 불렸으면 `config.experiments_in_week(<N>)`, 날짜로 불렸으면
`config.next_experiments()` 를 쓴다. 리스트가 둘 이상이면 되묻고 중단한다.

폴더가 없으면 **거절하고** `init-lab-experiment` 를 안내한다. 만들어 주지 않는다.

### 2. 쪽마다 판형을 꺼내고 격자를 덮는다

```bash
python3 -c "
from scripts.lab import hand_grid
import sys
pdf = sys.argv[1]
out = sys.argv[2]
import fitz
n = len(fitz.open(pdf))
for i in range(n):
    b = hand_grid.board_image(pdf, i)
    cal = hand_grid.calibrate(b)
    page = hand_grid.render_page(pdf, i)
    hand_grid.overlay_grid(page, cal, f'{out}/격자/p{i+1}.png')
    print(i+1, b.md5[:8], round(cal.res_x,2), round(cal.res_y,2))
" <PDF> <출력폴더>
```

`GridError` 가 나면 그대로 알리고 중단한다. 판형이 다른 그림 위에 그렸거나
판형이 바뀐 것이다 — 추측으로 넘어가지 않는다.

### 3. 격자 그림을 보고 전사한다

`격자/p<N>.png` 를 읽고 `전사/p<N>.json` 을 쓴다. **이 단계만 사람(vision)이
한다.**

```json
{
  "page": 3,
  "circuit": "e1_nand",
  "title": "2-1 NAND Gate",
  "signed": false,
  "chips": [
    {"label": "74HC08", "block": "좌", "pin1_row": 7},
    {"label": "74HC00", "block": "좌", "pin1_row": 17}
  ],
  "wires": [
    {"color": "빨강", "from": "좌 g7", "to": "좌 중앙VCC레일7행"},
    {"color": "검정", "from": "좌 GND레일7행", "to": "좌 b7"}
  ],
  "leds": [{"tag": "L1", "anode": "좌 c14", "cathode": "좌 c15"}],
  "resistors": [{"tag": "L1", "top": "좌 d15", "bottom": "좌 d16"}],
  "bridges": [{"kind": "gnd", "from": "좌 GND레일29행", "to": "좌 중앙GND레일29행"}],
  "uncertain": []
}
```

전사 규칙:

- **끝점과 점만 홀로 읽는다.** 선이 지나가는 홀은 적지 않는다. 끝점이 아닌
  자리에 점이 찍혀 있으면 그 자리도 꽂힌 것으로 읽는다 — 출력끼리 맞물린
  결함이 그렇게 나타난다.
- 두 행 사이로 보이면 **3배로 확대해** 다시 본다.
  `hand_grid.crop_rows(page, cal, 시작행, 끝행, 경로, scale=3)`.
- 그래도 못 정하면 그 주소를 `uncertain` 에 올린다. 추측으로 채우지 않는다.
- 색은 보이는 대로 적되 **판정에 쓰지 않는다.** 색이 틀려도 끝점이 맞으면
  통과, 색이 맞아도 끝점이 틀리면 오류다.
- 회로 ID(`circuit`)는 제목과 칩 라벨로 고른다. `e1_and` · `e1_or` ·
  `e1_nand` · `e1_nor` · `e1_comb` 중 하나다.

### 4. 대조하고 판정문을 낸다

```bash
python3 -c "
from pathlib import Path
from scripts.lab import hand_compare as hc
from scripts.lab.hand_transcript import parse_transcript
import sys
out = Path(sys.argv[1]); rnd = int(sys.argv[2])
pages = []
for p in sorted((out/'전사').glob('p*.json')):
    hand = parse_transcript(p)
    ref = hc.reference_diagram(hand.circuit)
    pages.append((hand.page, hand.circuit, hc.compare(ref, hand), hand))
(out/'판정.md').write_text(hc.judgment_markdown(pages, rnd), encoding='utf-8')
for page, _c, fs, _h in pages:
    for f in fs:
        print(page, f)
" <출력폴더> <라운드번호>
```

### 5. 치명 결함마다 증거 크롭을 만들어 보낸다

결함의 `where` 에 행이 들어 있으면 그 행 앞뒤 5행을 잘라 `증거/` 에 넣고
`SendUserFile` 로 보낸다. 사용자가 직접 눈으로 확인할 수 있어야 한다.

### 6. 요약한다

판정문 총평(`제출 가능` / `수정 필요`)을 먼저 말하고, 쪽별로 고칠 선을
**손그림 좌표로** 적는다. 참조 좌표를 그대로 옮기지 않는다 — 칩이 밀려 있으면
참조 좌표가 다른 자리를 가리킨다.

## 검사 목록

| 코드 | 검사 | 등급 |
|---|---|---|
| H1 | 끝점이 실제 홀인가 (레일 빈 행, 63행 밖) | 치명 |
| H2 | 한 홀에 리드 둘 | 치명 |
| H3 | pin 14 는 VCC 에만, pin 7 은 GND 에만 닿는가 | 치명 |
| H4 | 참조가 접지한 미사용 입력이 손그림에서도 묶였는가 | 기능 |
| H5 | 참조가 개방한 미사용 출력에 무언가 물렸는가 | 치명 |
| H6 | 핀 서명 차이 (입력·단 간 연결·LED 도달) | 치명 |
| H7 | LED 사슬: 캐소드~저항 윗다리가 한 줄 · 아랫다리가 GND | 치명 |
| H8 | 레일 연속성: 브리지가 있는가 | 치명 |
| H9 | 브리지 행이 참조와 다름 | 표기 |
| H10 | 칩 pin 1 행이 참조와 다름 | 표기 |
| H11 | 제목이 회로와 불일치 | 표기 |
| H12 | 학번·이름·날짜 미기재 | 표기 |
| H13 | 전사 `uncertain` | 보류 |

**치명·기능이 0건이면 제출 가능이다.** 표기는 막지 않고 별도 줄로 알린다 —
학번 미기재로 제출을 막을지는 채점 관행이지 회로 문제가 아니다.

## 판정할 때 지키는 것

- **행이 밀린 것은 오류가 아니다.** 칩과 배선이 함께 옮겨져 있으면 그림은
  유효하다. H10 이 표기로만 알린다. 참조 좌표와 다르다는 이유로 치명을 매기지
  않는다.
- **참조 그림도 의심한다.** 참조가 `overlap_warnings` 에 올린 배선은 다른 선에
  깔려 잘 안 보이는 자리다. H6 메시지에 그 사실이 붙는다 — 놓친 쪽을 탓하기
  전에 원도를 본다. 2026-09-08 5쪽에서 빠진 `A → 74HC32 pin 1` 이 그런 선이었다.
- **한 결함을 두 번 보고하지 않는다.** 브리지 누락은 H8 만 낸다. 미사용핀은
  H4·H5 가 보고 H6 에서는 뺀다.

## 비-목표

- 결선도를 그리지 않는다. 참조는 `breadboard-diagram` 이 만든다.
- 손그림 선을 자동 벡터화하지 않는다. 검정이 신호선·칩 글자·저항을 겸해서
  색으로 갈리지 않는다.
- 다이오드 극성을 판정하지 않는다. 손그림이 점 하나라 판정 불가다.
- 명세·보고서를 검증하지 않는다. `review-lab-report` 가 한다.
