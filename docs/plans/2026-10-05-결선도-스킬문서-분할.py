"""breadboard-diagram SKILL.md 를 본문 + 형제 문서 셋으로 나눈다 (일회성).

계획 `docs/plans/2026-10-05-결선도-스킬문서-분할-구현계획.md` 의 Task 1 이 돌린다. 분할 커밋과 함께
기록으로 남지만, 분할 뒤에는 작업 트리 SKILL.md 가 BASE 와 달라 첫 가드에서 멈춘다 — 다시 돌릴 도구가 아니다.

입력: git 의 BASE 커밋에 있는 SKILL.md. 작업 트리가 그것과 같아야 한다(뒤에 누가 고친 것을 덮지 않게).
출력: OUT 폴더에 SKILL.md · v1.md · 주차별.md · 연혁.md.
검사: 원본의 모든 문단이 네 파일 어딘가에 글자 그대로 있는지(제목 줄·EDIT 제외), 본문 크기,
      테스트가 고정한 구절이 본문에 남았는지, 형제 표지 구절이 본문에 없는지. 줄인 문단마다 본문에서
      빠진 backtick 토큰을 `[검토]` 로 찍는다 — 실패 조건이 아니라 사람이 읽을 목록이다.

    python docs/plans/2026-10-05-결선도-스킬문서-분할.py <저장소 루트> <출력 폴더> [BASE]
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(sys.argv[1])
OUT = Path(sys.argv[2])
BASE = sys.argv[3] if len(sys.argv) > 3 else 'f3de368'
SKILL_REL = '.claude/skills/breadboard-diagram/SKILL.md'
MAX_BYTES = 40000
P = '`.claude/skills/breadboard-diagram/'

src = subprocess.run(['git', 'show', f'{BASE}:{SKILL_REL}'], cwd=ROOT, capture_output=True,
                     check=True).stdout.decode('utf-8').replace('\r\n', '\n')
L = src.split('\n')
# 작업 트리가 BASE 와 다르면(누가 그 뒤에 SKILL.md 를 고쳤으면) 그 변경을 덮어쓰게 된다 — 멈춘다.
live = (ROOT / SKILL_REL).read_text(encoding='utf-8')
assert live == src, f'{SKILL_REL} 가 {BASE} 이후 바뀌었다 — 이 스크립트의 문단 표를 다시 맞춰야 한다'

# 문단 = 빈 줄로 갈린 덩어리. 시작 행 번호(1부터)로 부른다.
blocks = {}
start = None
for i, line in enumerate(L + [''], 1):
    if line.strip() and start is None:
        start = i
    elif not line.strip() and start is not None:
        blocks[start] = '\n'.join(L[start - 1:i - 1])
        start = None


def B(n, prefix):
    """시작 행 n 의 문단. 원본이 바뀌었으면 여기서 멈춘다."""
    assert n in blocks, f'{n} 행에서 시작하는 문단이 없다'
    assert blocks[n].lstrip().startswith(prefix), (n, blocks[n][:60])
    return blocks[n]


def dedent(text):
    return '\n'.join(l[2:] if l.startswith('  ') else l for l in text.split('\n'))


# ── 형제 문서로 그대로 옮기는 문단 ──────────────────────────────────────────
V1_BLOCKS = [(25, '**정본은'), (30, '> **2026-2 배포본'), (40, '**아래 값은 템플릿을'),
             (48, '- 캔버스 원본 크기'), (62, '> **레일에는 홀이'), (66, '> **좌우 블록은')]
WEEK_BLOCKS = [(149, '아래 ID 는'), (163, '**OR·NOR 은'), (177, '미사용 입력은 이 주차만'),
               (207, '회로 경계의 걷기 보드'), (214, '**밀집 — R7'), (219, '- **실험 4')]
HIST_BLOCKS = [  # (시작 행, 접두, 연혁.md 소제목)
    (261, '> 이전 판은', '그림 두 층 — 보드 위 라벨 박스 30개 (§4)'),
    (332, '근거: 2026-09-18', '걷기 보드 — 2026-09-18 실험03 실험실 (§4a)'),
    (523, '> 왜 이 검사가 없었나', 'R1 — 끝점이 홀 밖이었다 (2026-09-07)'),
    (602, '> R3 는 2026-09-08', 'R3 — 같은 넷이라도 (2026-09-08)'),
    (541, '> 왜 R5 가', 'R5 — 기하만으로는 그물이 되지 않는다 (2026-09-09)'),
    (546, '> 왜 R6 가', 'R6 — 최소 패치는 증상만 건드린다 (2026-09-10)'),
    (557, '> 왜 R7 이', 'R7 — 꽂을 수 있음과 꽂기 쉬움 (2026-09-18)'),
    (564, '> 왜 R8 이', 'R8 — 무조건 1·4 로 나눈 X자 (2026-09-20)'),
]

# ── 본문에서 줄이는 문단: (시작 행, 접두, 원래 절) → 새 글. 원문은 연혁.md 「줄이기 전 원문」으로 간다.
COMPRESS = {}

COMPRESS[(75, '- **고르기.**', '§2b v2 판형')] = """\
- **고르기.** 주차 `배치.py` 에 `BOARD = 'v2'` 를 두고 빌더마다
  `BreadboardRenderer(template_path, baseline=baseline, layer=layer, board=BOARD)` 로 넘긴다(기본값 `DEFAULT_BOARD`
  도 v2). v1 주차는 `BOARD = 'v1'` 이고, `BOARD` 가 없으면 `require_board()` 가 멈춘다(`config.BOARD_V2_FROM` = 5).
  `board=BOARD` 를 빠뜨리면 `build_all`·손그림 참조의 `check_board()` 와 체크리스트의 사이드카 `board` 대조가
  멈춘다. 체크리스트 빈 판형은 `배치.py` 가 없어도 실험 번호로 v2 를 깐다.
- **좌표는 `.claude/assets/breadboard_v2/geometry.json` 에서만 읽는다** — 숫자를 문서·코드에 베껴 적지 않는다.
  양식 PNG(1200×1600)는 **1배 고정**이고 렌더러가 해시를 `png_sha256` 과 맞댄다 — 판형을 다시 뽑으면 그 값을
  고치고 `hand_grid.detect_grid` 가 0px 로 맞는지 본다.
- **26열**: `좌 GND·VCC | 좌 a~e (골) f~j | 가운데 GND·VCC | 우 a~e (골) f~j | 우 GND·VCC`.
  63행, 레일 빈 행은 v1 과 같다(§2). 모든 레일은 왼쪽이 GND, 오른쪽이 VCC 다.
- **가운데 레일은 한 넷이다.** `cols['left']['mid_gnd']` 와 `cols['right']['mid_gnd']` 가 같은 x 라 좌 칩
  pin 14(가운데 VCC)와 우 LED 사슬 GND(가운데 GND)가 브리지 없이 한 레일이다. 주소는 접두어 없이
  `중앙GND레일9행` 꼴이다. 가운데끼리 `bridge_rails` 를 부르면 오류다.
- **전원 표준**: `connect_jacks()` 로 잭 → **좌 바깥 레일**, 거기서 `bridge_rails(L['gnd'], L['mid_gnd'], …)`·
  `bridge_rails(L['vcc'], L['mid_vcc'], …)` 두 가닥으로 가운데 레일에 넘긴다. **우 바깥 레일은 기본 배선에서
  쓰지 않는다**(그림에는 있다).
- 사이드카 JSON 에는 `"board": "v2"` 가 든다(키가 없으면 v1).
- 본보기: `tests/fixtures/board_v2/배치.py` 는 **판형·전원·입력 본보기**다 — 급전선을 손좌표로 찍은 연기
  시험이라 신호선은 따르지 않는다. 신호선·배치(`PLACE`·`LAYOUT`·`배치탐색.md`) 본보기는
  `tests/fixtures/board_v2_e4/배치.py` 다(§4a).
- **DIP-16 칩(74HC42 따위).** 칩 핀 수는 엔진의 칩 모델 표 `DIP_PINS`(이름 → 14/16)에서 온다 — 배치기는 표에
  없는 칩을 거절하고, 그리기는 모르는 이름을 14핀으로 본다. 16핀 칩은 8행이고 pin 16 → 가운데 VCC(행 k),
  pin 8 → GND(행 k+7)다. 이름 글자는 몸통 가운데 반 행 하나만 막는다 — 74HC42 는 a쪽 pin 1~7 이 전부 출력이라
  일곱 가닥이 몸통을 건너는데 건널 반 행이 핀마다 하나뿐이다. 그래서 a쪽 출력 → LED 선은 배선표에 **이름 상자에
  가까운 핀부터**(pin 4, 3, 2, 1, 5, 6, 7) 적는다 — 배선기 수리는 막힌 선 앞 한 가닥만 바꿔 보므로 위에서부터
  적으면 pin 4 가 막힌다. 본보기 `tests/fixtures/board_v2_e5/배치.py`(실험05 1-2 시험판).
- **Negative Logic LED.** 출력이 0 일 때 켜지는 회로(교안 "Output 을 Negative Logic 으로 구축")는
  `bb.led_chain(R['a'], top, 'Y0', desc, block='right', active_low=True)` 로 그린다 — 신호 우 a 윗행 →
  330Ω(b, 윗행~윗행+2) → LED(c, 캐소드 윗행+2 → 애노드 윗행+3) → a 윗행+3 에서 가운데 VCC 레일. 레일 점퍼
  행이 보통 사슬과 같아 배치기는 극성을 모른다. 보드 위 꼬리표는 신호 이름만 두고 보드 아래
  `bb.note('Y0~Y9 LED 는 출력 0 에서 켜진다(Negative Logic).')` 한 줄을 둔다(순서표 사슬 줄에는 엔진이
  `0 이면 켜짐` 을 넣는다). LED 순서는 R10 대로 **칩 핀 행 순서**다 — 진리표 순서와 다르면 핀 행 순서가
  이긴다(74HC42: Y0, Y1, Y2, Y3, Y4, Y5, Y9, Y6, Y8, Y7 — Y7·Y8·Y9 가 pin 9·10·11)."""

COMPRESS[(10, '## 1. 개요 및 목적', '§1 개요 및 목적')] = """\
## 1. 개요 및 목적
학부 논리회로실험 운영계획서 규정(손스케치 첨부, 미사용 핀 처리, 보호 저항)을 지키면서 학생이 태블릿이나 종이에
따라 그릴 수 있는 정답 결선도를 낸다. 엔진이 지키는 전기 규칙:
- VCC(14번) → +5V 적색 레일, GND(7번) → 0V 청색 레일. 브레드보드 물리(단자대 세로 절연, 같은 행 5홀 도통)를 따른다.
- **미사용 입력 핀**: 접지하지 않는다 — 2026-09-11 실험01 실측에서 결과에 영향이 없었고 접지선이 순서표의
  절반이었다. `mark_unused_inputs()` 로 개방 등록만 한다. 교안이 미사용 핀 처리를 명시한 주차(실험02 p9)만
  `connect_unused_inputs()` 로 그린다. **사용하는 게이트의 입력은 반드시 물린다.**
- **미사용 출력 핀**: 내부 소손 방지를 위해 **절대 접지 금지, 완전 개방(NC)**.
- **LED 및 330Ω 보호저항**: 실제 다리 위치와 저항 색띠(주-주-갈-금)를 갖춘 실물 그래픽으로 둔다."""

COMPRESS[(306, '**걷기 보드.**', '§4a 슬롯 · 기준선 · 단계')] = """\
**걷기 보드.** **걷기 그림 정책의 정본은 이 절이다.** **선을 뽑는 자리마다** 사슬에 **걷기 전용 보드 한 장**을
끼운다 — 회로가 바뀌는 경계도, 회로 **안**의 임시 프로브 급전선도 같다. 앞 상태가 전부 회색이고, 다음 보드에
없는 배선만 **빨간 점선 + 빨간 채움 원 번호**(걷기 ①②)다. 다음 보드에 없는 **LED 사슬**은 LED·저항을 빨갛게
칠하고 빨간 점선 상자로 두른다 — 번호는 그 사슬의 GND 선이 받고, 부품은 순서표에 번호 없는 줄로 나간다. 새 선도
순서표도 없다. `배치.py` 의 `BOARDS` 에 `removal_board((앞_빌더, stage), (다음_빌더, stage), 제목, 부제)` 로
넣는다 — 회로 안 걷기는 **같은 빌더의 인접 단계**를 물린다(`(build_e3_fa, 1), (build_e3_fa, 2)`). 앞 보드는
기준선 dict 의 `ghost` 키로 다시 그려진다(유령선은 `verify()` 가 안 본다). 걷기 보드의 `snapshot()` 이 다음 보드의 기준선이라 **단계 보드는
아무것도 걷지 않는다**(`tests/test_breadboard_boards.py::StageBudget` 이 실험01·02 를 뺀 모든 주차에 단언한다).
netlist 단계 표의 `<k>걷기` 행이 그 번호를 인용한다(`**걷기 ①·② 를 뽑는다**`). 주차 파일에 `build_` 래퍼를
두지 않는다 — `tests/_boards.py` 가 잡아 `steps > 0` 검사에 걸린다. 걷을 배선이 없는 전환에는 끼우지 않는다 —
`removal_board` 가 `ValueError` 로 거절한다. 걷기 보드는 앞 단계를 그대로 다시 그려 만들므로 주차 빌더는
`bb.ghost is not None` 이면 단계 노트를 건다(실물: `보고서/실험03/결선도/배치.py` 의 `_E3_STAGE_NOTE`). 학생에게
무엇을 뽑으라고 말하는 자리는 `removal_board(...)` 의 제목·부제다."""

COMPRESS[(348, '**관측은 비어 있는 LED', '§4a 슬롯 · 기준선 · 단계')] = """\
**관측은 비어 있는 LED 를 프로브로 쓴다.** 완성본에서 그 LED 가 맡는 출력이 아직 안 세워진 단계에는 급전선을
그 단계의 관측 노드 핀에 잠시 꽂고, 다음 단계 머리의 걷기 보드에서 뽑는다. 여분 LED 를 더하지 않는다(교안 부품
수와 손그림 제출본을 지킨다). 걷기 보드(`<k>걷기`)의 확인 칸은 "뽑은 선이 손에 있고 그 홀이 비어 있다" 이고,
걷기 행은 **관측 노드 포인터와 새 신호선 셈에서만** 면제다 — 단계 셀 문법, `이 단계에서` 주소쌍, `확인`의 양 끝
홀은 `lab-netlist-v2` 검사를 그대로 받는다. 관측 노드의 상류에 뜬 입력이 있으면 안 된다 — 임시 입력 점퍼로 0 을
문다. 마지막 단계 전까지는 `bb.partial = True` 이고, 마지막 단계는 완성 상태라 뜬 핀이 없어야 한다."""

COMPRESS[(385, '**주차 빌더를 쓸 때:**', '§4a 슬롯 · 기준선 · 단계')] = """\
**주차 빌더를 쓸 때:** 파일은 `보고서/실험NN/결선도/배치.py` 하나다. 머리에서
`from render_breadboard import BreadboardRenderer, _input_jumper` 로 엔진을 가져온다(엔진이 그 파일을 불러 주므로
경로를 따로 잡지 않는다). 빌더 시그니처는 `build_eN_x(output_path, template_path=None, stage=None, baseline=None)`
이고 끝에 `return bb` 를 둔다. 보드 사슬은 `BOARDS = [(파일명, 빌더, stage), …]`, 완성본은
`FINALS = [(파일명, 빌더), …]` 다 — 일괄 렌더 함수는 쓰지 않는다(엔진 `build_all` 이 한다). **걷기 보드는 셋째
자리가 `None` 이다** — `removal_board(...)` 클로저는 `stage` 를 받으면 거절하고(받으면 조용히 무시돼 엉뚱한 단계의
걷기 그림이 나간다), 회귀 단언 `test_단계_보드는_아무것도_걷지_않는다` 가 `stage is not None` 인 보드만 골라
검사한다. 단계 래퍼 `build_eN_x_sK` 는 `_eN_board(index, …)` 로 앞 보드를 임시 렌더해 기준선을 만든다(실물
`보고서/실험01/결선도/배치.py` 의 `_e1_*`). `<ID>`(`build_<ID>`)는 손그림 검토 전사 JSON 에 저장되므로 한 번 쓴
이름은 바꾸지 않는다."""

COMPRESS[(127, '**엔진과 주차 결선은', '§3 CLI 사용법')] = """\
**엔진과 주차 결선은 따로 산다**(`docs/plans/2026-09-15-결선도-엔진-주차분리-설계.md`). 스킬 폴더의
`render_breadboard.py` 는 엔진(보드·배선 도구·`verify()`)만 갖고 주차 이름을 모른다. 결선은 그 실험 폴더의
`결선도/배치.py` 에 쓴다(§4a 「주차 빌더를 쓸 때」). 엔진 **코드**를 고치게 되면 도구 변경이다 — 따로 커밋한다."""

COMPRESS[(133, '**보드만 PNG', '§3 CLI 사용법')] = """\
**보드만 PNG, 글자는 사이드카.** 뽑은 PNG 에는 **보드만** 있다 — 제목·주석·범례·결선 순서·계측표·걷기 목록은
PNG 옆 같은 이름의 `.json`(`breadboard-sidecar/v1`: `title`·`subtitle`·`kept`·`steps`·`removals`·`probes`)으로
나가고 체크리스트가 목록으로 싣는다(`scripts/lab/render.py` 의 `_board_text_html`). PNG 와 JSON 은 늘 쌍이다 —
체크리스트는 JSON 이 없으면 멈춘다. `note()` 문구는 학생 면에 나가지 않는다(저작 흔적이다). 실험실에서 손으로
할 일이면 netlist 의 `must-read` 절에 쓴다."""

COMPRESS[(237, '**보드 위 (손으로', '§4 그림을 두 층으로')] = """\
**보드 위 (손으로 옮겨 그릴 것)** — 배선, 칩과 핀 번호, LED·저항, 그리고 **신호 이름**. 입력 `A`·`B`·`C` 는
점퍼의 레일 쪽 끝 옆 여백에, 출력 `L1`·`L2`·`X`·`Y`·`Z` 는 LED 옆에 `signal_tag()` 가 찍는다(보드 밖에만 있으면
손그림에 안 옮겨진다 — 실험01 예보 −1). **입력 배지는 보라(`INPUT`) 바탕에 흰 화살촉과 흰 글자**이고
(`signal_tag(arrow=...)`, 보드 밖 꼬리표도 같은 보라) 화살촉은 점퍼선이 뻗는 쪽을 가리킨다 — `D0▶`·`◀E`. 화살촉은
글리프가 아니라 다각형이고 폭 `INPUT_TRI` 4.5 는 좌 바깥 여백에 `D0` 가 들어가는 상한이다. 입력 점퍼도 LED 도 없는
주차는 **계측 지점**이 이름을 갖는다 — `instrument(..., name='VIN')` 이 교안 회로도 이름(`VIN`·`VOUT`·`CH1`·`CH2`)을
그 스트립 끝 여백에 찍는다."""

COMPRESS[(268, '**모든 선은 홀에서', '§4 그림을 두 층으로')] = """\
**모든 선은 홀에서 홀로 간다.** 입력도 예외가 아니다 — `_input_jumper()` 가 **좌 GND 레일 홀 → 같은 행 b열**
로 그린다(0 자리. 1 은 레일 쪽 끝만 빨간 레일로 옮긴다 — 범례에 있다). 다른 블록으로 가는 갈래는 허공에서
분기하지 않고 **같은 스트립의 다른 홀(a열)에 꽂는 두 번째 점퍼**로 그린다 — 점퍼는 이어 붙일 수 없다.
꼬리표에는 꽂을 자리(`입력 A → b10`)를 적는다. 같은 행 꼬리표가 겹치면 `_tag()` 가 아래로 비키고 상자를
`margin_tag_boxes` 에 남긴다(`test_보드_밖_입력_꼬리표끼리_겹치지_않는다`)."""

COMPRESS[(369, '**게이트 좌우 배정.**', '§4a 슬롯 · 기준선 · 단계')] = """\
**게이트 좌우 배정.** DIP-14 쿼드 게이트는 게이트 1·2 가 핀 1~6(a~e 쪽), 3·4 가 핀 8~13(f~j 쪽)이고 hex
인버터는 1·2·3 이 a쪽, 4·5·6 이 f쪽이다. 배정 순서는 셋이다. ① **R7 에 걸리는 칩만 나눈다** — 한쪽 리드가
8 이하면 게이트 1·2 로 둔다. ② **게이트 자리는 신호가 오는 쪽이다.** 같은 블록 위/아래 칩에서 오면 그 출력
핀과 같은 쪽, 다른 블록에서 오면 그 블록을 향한 쪽(우 블록은 a쪽, 좌 블록은 f쪽), 레일 입력은 바깥 레일 쪽.
그래서 나눌 때는 게이트 4(핀 12,13→11 — 게이트 1 의 거울)나 hex 6(13→12)이 짝이 된다.
③ **나눈 칩 안의 사슬만** 칩 위/아래 행(pin1_row−1 또는 +7)으로 건넌다 — 칩 몸통 위는 지나지 않고(핀 번호를
가린다), **두 칩 사이에서는 건너지 않는다.** f~j 쪽 게이트의 입력은 `_input_jumper(..., side='f')` 로 그쪽
GND 레일에서 i 열로 넣는다. 결과는 `verify()` 가 잰다 — R7(칩 한쪽 리드 ≤ `SIDE_LEAD_MAX` 8)과 R8(같은 블록
두 칩 사이 배선은 쪽을 안 바꾼다). netlist 를 저작할 때 게이트 번호를 이렇게 적는 것이 먼저다
(`draft-lab-spec` SKILL 의 「결선도 절에 회로 메타를 단다」 절). v2 는 여기에 아래 R9·R10 규약이 더해진다."""

COMPRESS[(400, '**파일명 규칙.**', '§4a 슬롯 · 기준선 · 단계')] = """\
**파일명 규칙.** 완성본은 `실험NN_<소단원>_결선도_<회로명>.png`, 절차 그림은
`실험NN_<소단원>_결선도_<회로명>_<k>단계_<이름>.png`, 걷기 보드는 `단계` 대신 `걷기` 를 쓴
`…_<k>걷기_<이름>.png` 다. `<소단원>` 은 명세 항목 ID 의 `P` 뒤 토큰이다(`E1.P1-1` → `1-1`, `E1.P3` → `3`).
걷기의 `<k>` 는 **뒤따르는** 단계 번호이고(`_2걷기_LED1프로브.png` 는 2단계 머리의 걷기), 회로 경계의 걷기는
`1걷기` 에 **다음** 회로의 `<소단원>` 을 쓴다. `export-hand-diagram` 의 손그림 이름
`실험NN_<소단원>_손그림_<회로명>.png` 과 같은 틀이다. `실험NN` 을 빼지 않는다 — 소단원 번호는 주차마다
1부터 다시 시작해 한 학기 안에서 유일하지 않다."""

COMPRESS[(414, '**글꼴.**', '§4a 슬롯 · 기준선 · 단계')] = """\
**글꼴.** 한글 후보는 `REQUIRED_GLYPHS['kr']`(`⊕→·☐※`)을 **전부** 가진 것만 쓴다 — `font_path()` 가 후보마다
`_covers()` 로 확인하고 빠진 글꼴은 건너뛴다(맑은 고딕은 `⊕`·`☐` 가 없어 뒤로 돌렸다)."""

COMPRESS[(439, '**v2 읽기 규칙', '§4a 슬롯 · 기준선 · 단계')] = """\
**v2 읽기 규칙 (R11~R14, `spec.readability`).** 칩 넷이 한 블록에 서면 a~d / g~j 열이 끝점으로 차서, R1~R10 을
다 통과해도 **따라 그릴 수 없는** 그림이 나온다 — 번호 원이 끝점 홀을 덮고, 검정 선이 검정 홀 열 위를 지나
꽂힌 것인지 지나가는 것인지 안 보인다. v2 빌더는 그래서 이렇게 그린다."""

COMPRESS[(444, '- 신호선의 가로 구간은', '§4a 슬롯 · 기준선 · 단계')] = """\
- 신호선의 가로 구간은 **반 행**(두 행 사이, `r_y(row) ± row_pitch/2`)으로, 세로 구간은 **홀 열 사이**(열 x ± 12)나
  여백 차선으로 낸다. 끝점에는 반 행에서 반 칸 꺾어 들어간다 — 그러면 선이 닿은 홀은 전부 꽂는 홀이다(R12).
  LED 로 건너는 선도 가운데 레일 홀 위를 같은 행으로 지나지 않는다 — GND 레일에 꽂은 것으로 읽힌다.
- 번호 원은 `marker_at` 을 안 주면 엔진이 고른다(`_auto_marker`). 그려졌든 안 그려졌든 앞 번호들의 자리
  (`_marker_slots`)를 피하므로 완성본·따라 그리기 층·단계 그림에서 같은 자리다. 못 찾으면
  `[WARN] 번호 원 자동 자리 없음` — 그때는 `marker_at` 을 직접 주되 R11 대로 꽂힌 홀·다른 원·칩 몸통·남의 배선을
  피한다. 엔진 고정 부품은 `marker_near` 기본 자리에서 R11 에 걸릴 때만 비키고(`_settle_marker`), `route_plan`
  원은 다 깐 superset 판에서 다시 고른다(`_resettle_markers`).
- 양 끝이 칩의 같은 쪽인 선은 칩 몸통을 건너지 않는다(R13). 몸통을 건너는 것은 칩 안 a↔f 이어 가기와 a쪽
  출력 → LED 뿐이고, 그것도 **칩 이름 글자 위**는 지나지 않는다(R14) — 건너는 반 행은 pin 1~3 사이나 pin 5~7
  사이(칩 하나에 넷)와 칩 위아래 바깥이다. 막히면 `route_plan` 이 직전 몇 가닥 중 한 가닥만 다음 후보로 바꿔
  다시 깐다.
- **v2 주차의 신호선(`sig`·`mid`)은 손좌표로 찍지 않는다 — 반드시 엔진 `route_plan(build_fixed, chips, wires,
  board=BOARD)` 에 배선표만 주고 `draw_routed` 로 그린다**(선이 한 가닥뿐이어도, 본보기
  `tests/fixtures/board_v2_e4/배치.py`). 입력 점퍼(`_input_jumper`)·전원·레일 브리지·LED 사슬은 고정 빌더가
  그린다. `route_plan` 이 다루지 못하는 끝점(7-segment 등)이 나오면 그 선만 손으로 찍어 우회하지 말고
  `route_plan` 을 먼저 넓힌다. 비용은 `길이 + 40·꺾임 + 400·몸통횡단 + λ·밀도`(λ = 엔진 `DENSITY_WEIGHT`, 근거
  `docs/plans/2026-10-04-v2-배선기-밀도-설계.md`, 다시 재려면 `python -m scripts.lab.route_sweep`)이고 밀도 지표는
  `wire_metrics(bb)` 다. 최종 판정은 늘 엔진 `verify()` 다.
- **v2 주차의 칩 행·LED 윗행·브리지 행도 손으로 정하지 않는다 — 배치기가 고른다**(설계
  `docs/plans/2026-10-05-v2-배치기-설계.md`). 주차 `배치.py` 는 `PLACE`(`PlaceCircuit` 목록 — 칩→슬롯·모델·LED
  태그 위→아래·배선표(LED 끝은 태그 `('LED', 'L1')`)·`fixed(bb, stage, superset, layout)`·입력 핀)·`SLOTS`·`LAYOUT`
  을 두고, 빌더는 행 상수 대신 `LAYOUT` 을 읽는다(경로는 `place_paths(circuit, LAYOUT)`, 고정물을 그리기 전에
  `bb.marker_hints = place_marker_hints(circuit, LAYOUT)`). 배선표를 쓰거나 바꾸면
  `python -m scripts.lab.place_search <배치.py>` 로 같은 폴더 `배치탐색.md` 를 만들고, 고른 layout 을 `LAYOUT` 과
  netlist `kind: layout` 표에 옮겨 적는다. `PlaceEnforced` 가 지문·layout 을, `PlaceLayoutTable` 이 netlist 표와
  `LAYOUT` 을 맞댄다. 후보는 칩 사이 빈 행 3~6(`PLACE_GMIN`)이고 칩·LED·입력 핀 행은 레일 빈 행을 피한다. 고르는
  것은 기준 `LAYOUT` 보다 짧고 밀도가 기준 이하이며 단계 사슬 `verify()` 를 통과한 후보 중 최단 길이의
  ×`PLACE_LENGTH_SLACK`(1.02) 안에서 밀도가 가장 낮은 것이다(세부는 엔진 `place_plan` docstring). 이 ε 를 바꾸면
  지문이 바뀌어 모든 v2 주차를 다시 돌린다. `--jobs`(기본 min(8, 코어 수))로 병렬로 돌고 `--jobs 1` 과 답이 같다.
  칩은 `DIP_PINS` 표에 있는 것만 받는다(16핀 포함 — §2b)."""

COMPRESS[(338, '**단계.**', '§4a 슬롯 · 기준선 · 단계')] = """**단계.** 단계 하나는 **관측 노드 하나를 세운다**(그 단계 끝의 확인은 netlist `## 노드` 표의 노드 하나다). 그 단계에서
**새로 꽂는 신호선은 셋 이하**다(`STAGE_WIRE_BUDGET` — 주차 예외는 `stage_budget(board)`: 배치.py 의
`STAGE_WIRE_BUDGET` + `STAGE_WIRE_BUDGET_REASON`, 값은 게이트 입력 수 + 1. 실험04 = 5). 신호선은 `sig`·`mid` 배선이고,
전원·GND·레일 브리지·잭·LED 사슬 부품·칩 꽂기는 기반이라 세지 않는다 — 기반은 그 회로가 쓰는 슬롯 전부를 1단계에
꽂는다. `export()` 가 보드마다 `새 신호선 n · 걷는 선 m` 을 찍고 예산을 넘으면 `[WARN]` 을 낸다. 승인을 막는 것은
`tests/test_breadboard_boards.py` 의 `StageBudget` 이다(실험01·02 는 옛 규약 승인본이라 `LEGACY_BOARDS` 로 면제)."""

COMPRESS[(419, '**v2 배치 규약 (R9·R10).**', '§4a 슬롯 · 기준선 · 단계')] = """**v2 배치 규약 (R9·R10).** 칩은 **좌 블록에만**, 우 블록에는 **LED 사슬(LED + 330Ω)만** 둔다 — 칩끼리는 좌 블록
안에서 세로로 잇는다. LED 를 구동하는 게이트는 **f~j 쪽(pin 8~14)** 에 배정하고(핀이 정해진 MSI 칩은 예외 — §2b
DIP-16), 사슬은 **우 a 열**에서 받아 GND 를 가운데 레일로 내린다(우 f~j 에 두면 GND 가 쓰지 않는 우 바깥 레일로
간다). 건너는 선의 위아래 순서는 LED 순서와 같게 둔다. 좌 블록에 칩이 다 안 들어가는 주차는 규약에 예외를 두지
않고 면제 열쇠 방식(`docs/plans/2026-09-21-면제열쇠-설계.md`)으로 연다."""

COMPRESS[(570, '**빈 홀 고르기.**', '§5 물리 실현성 규칙')] = """**빈 홀 고르기.** 레일 끝점은 `snap_rail_row()` 가 아니라 `free_rail_row(row, *xs)` 로 고른다 — 홀이 있고
**비어 있는** 가장 가까운 행이다. 헬퍼 전부(`connect_power`, `connect_unused_inputs`, `bridge_rails`, `led_chain`,
`connect_jacks`, `_input_jumper`)가 이것을 쓰고, 먼저 그린 배선이 **지나간** 레일 홀(`_passed`)도 찬 것으로 본다.
단자대(a~j) 충돌은 `verify()` 가 잡되 피하는 것은 빌더 몫이다 — 같은 스트립의 옆 홀로 옮긴다."""

COMPRESS[(503, '| | 규칙 | 잡는 결함 |', '§5 물리 실현성 규칙')] = """| | 규칙 |
|---|---|
| R1 | 모든 배선 끝점은 실제 홀이다. 전원잭(`_jack_at` — v1 y<240, v2 y<보드 위 테두리)만 예외 |
| R2 | 한 홀에는 리드 하나 — 점퍼 끝·LED 다리·저항 다리·칩 핀 전부 |
| R3 | 배선 끝점·부품 다리 위를 다른 배선이 지나가지 않는다 — **같은 넷이라도** |
| R4 | 서로 다른 배선이 같은 축 위에 포개지지 않는다 (다른 색 8px, 같은 색 30px 초과 — 같은 스트립 두 번째 점퍼의 밑동은 봐주지만 그 끝점은 R3 가 잡는다) |
| R5 | 넷이 말이 된다 — ⓐ 같은 스트립 안에서 끝나는 점퍼가 없고 ⓑ +5V 와 GND 가 한 넷이 아니며 ⓒ 아무 데도 안 물린 칩 핀이 없다 (미사용 출력·개방 등록한 미사용 입력·계측 접점·`partial` 은 ⓒ 면제) |
| R6 | 배선이 **자기 스트립 안을 달리는 구간**이 없다 — 이웃한 꺾임점 둘이 같은 스트립이면 그 구간은 없는 것과 같다 (양 끝이 다 실제 홀일 때만) |
| R7 | 칩 한쪽(핀 행 7 × 자유 열 4 = a~d 또는 g~j)에 꽂힌 리드가 `SIDE_LEAD_MAX`(8) 이하다 — 끝점만 센다. `density_policy = 'legacy'` 는 실험01~03 승인본만 |
| R8 | 같은 블록의 서로 다른 두 칩 핀 스트립을 잇는 배선은 양 끝 쪽(a~d / g~j)이 같다. 같은 칩 안·다른 블록 사이·칩 행 밖(LED 사슬·레일·잭) 끝점은 안 본다 — 칩 행 안 a~d/g~j 의 LED 다리는 본다. `legacy` 가 함께 끈다 |
| R9 | 칩은 판형이 허용한 블록에만 둔다(`spec.chip_blocks`) — v2 는 좌 블록만, v1 은 두 블록 다 |
| R10 | LED 전용 블록(`spec.led_only_blocks`, v2 는 우)으로 건너는 선은 **칩 핀 스트립 → LED 사슬 신호 스트립**뿐이고, 건너는 선끼리 위아래 순서가 LED 순서와 같다. 레일↔레일 브리지는 안 본다. v1 은 안 돈다 |
| R11 | 번호 원이 꽂힌 홀·다른 번호 원·칩 몸통을 가리지 않고, 원 아래를 지나는 배선이 **많아야 하나**다. `spec.readability`(v2)만 |
| R12 | 신호선(`sig`·`mid`)은 끝점 말고 홀 위(단자대·레일)를 지나지 않는다. 전원·GND·브리지·잭 선과 입력 점퍼는 안 본다. `spec.readability`(v2)만 |
| R13 | 양 끝이 칩 기둥의 같은 쪽인 신호선은 그 칩 몸통 상자에 들어가지 않는다(가로 건너기도, e·f 사이 골 세로 타기도). 칩 안 a↔f 이어 가기·a쪽 출력 → LED 는 안 본다. `spec.readability`(v2)만 |
| R14 | 어떤 배선도(전원선 포함) 칩 이름 글자 상자(`chip_label_boxes` — 도장에 드는 `chips` 와 따로)를 지나지 않는다. `spec.readability`(v2)만 |"""

COMPRESS[(584, '**경고 모드.**', '§5 물리 실현성 규칙')] = """\
**경고 모드.** `bb.overlap_policy = 'warn'`(R4 만 경고로 낮춘다)은 새 빌더에 쓰지 않는다 —
`tests/test_breadboard_physical.py` 가 모든 빌더가 엄격 모드인지 본다. 꼭 필요하면 그 이유를 빌더 주석에 적는다."""

COMPRESS[(590, '**밑동 허용은 면허가', '§5 물리 실현성 규칙')] = """\
**밑동 허용은 면허가 아니다.** R4 가 같은 색 30px 이하를 봐주는 것은 같은 스트립 두 번째 점퍼의 밑동 때문이지만,
그 밑동은 **얇은 선이 굵은 선 중간(홀 아닌 여백)에서 솟는 그림**이 된다. 갈래는 옆 홀에서 **세로로** 뺀다 —
입력 점퍼가 b열에 끝나면 c열처럼 위가 빈 옆 홀에서 올린다(실물: 실험01 복합회로 A 갈래 `c7→a13`).
`_input_jumper(..., col='a')` 로 a열에서 멈추고 b열에서 갈래를 올리는 방식은 netlist 가 입력 홀을 고정하지 않은
주차에만 쓸 수 있다."""

COMPRESS[(642, '**레일 브리지를 빼먹지', '§6 새 회로 빌더를 쓸 때')] = """\
**레일 브리지를 빼먹지 않는다.** 레일쌍은 서로 **별개 스트립**이다 — +5V 를 한 레일에 넣고 칩 전원 핀을 다른
레일에 물리면 **그림은 완벽해 보이는데 전원이 안 간다**(눈으로는 안 잡히고 `verify()` 의 연결성 검사가 잡는다).
v2 는 좌 바깥 레일과 가운데 레일 두 쌍만 쓴다 — 브리지도 그 사이 두 가닥이다(§2b)."""

COMPRESS[(649, '**브리지는 끝점이 있는', '§6 새 회로 빌더를 쓸 때')] = """\
**브리지는 끝점이 있는 레일만 잇는다.** 아무것도 꽂히지 않는 레일 구간을 잇는 브리지는 손으로 따라 그릴 가닥만
늘린다. `verify()` 는 여분 브리지를 안 잡으므로(R1~R6 위반이 아니다) 빌더에서 그 레일에 끝점이 있는지 먼저 본다."""

COMPRESS[(161, '**따라 그리기 층.**', '§3 CLI 사용법')] = """**따라 그리기 층.** 손그림을 팀원에게 맡길 때는 완성본을 층으로 나눈 PDF 를 준다 — 절차는 `make-trace-guide`
스킬이다. `배치.py` 에 `LAYERS`(`{완성본 파일명: [(lo, hi, 이름), …]}`, 완성본 번호 1..N 을 빈틈없이)를 두고,
새 주차의 완성본 빌더는 처음부터 `layer=None` 을 받아 `BreadboardRenderer(..., layer=layer)` 로 넘긴다. 절차
그림(`BOARDS`)은 임시 급전선이 있어 따라 그리기에 쓰지 않는다."""

COMPRESS[(609, '주차마다 `보고서/실험NN', '§6 새 회로 빌더를 쓸 때')] = """주차마다 `배치.py` 에 빌더를 쓰고(§4a 「주차 빌더를 쓸 때」) `render_breadboard.py --experiment N` 으로 뽑는다.
엔진을 고치면 도구 변경이라 따로 커밋하고 지난 주차 도장 테스트를 본다 — 그리는 방식(색·범례·배치)만 바꿨다면
도장은 그대로이니 전 주차를 다시 뽑는다. **옛 함수(`draw_wire`, `draw_badge`)는 살아 있고 더 짧아서 무심코 쓰면
옛 방식으로 돌아간다** — `tests/test_breadboard_readability.py` 가 엔진과 주차 `배치.py` 를 읽어 센다."""

COMPRESS[(655, '## 7. 손스케치', '§7 손스케치 활용 가이드')] = """## 7. 손스케치 활용 가이드 (학생용)
학생은 PNG 를 필기 앱에 불투명도 40~50% 로 깔고 따라 그린다. 보드 위 **신호 이름 배지**(보라 화살촉 입력 배지는
방향까지)도 같은 자리에 옮겨 적고 — 이 표기가 없다고 감점된 적이 있다 —, 체크리스트 완성본 아래 결선 순서 목록을
한 줄씩 지워 가며, 여백에 작성일자·학번·성명을 자필로 적는다."""

# ── 원문을 남기지 않고 고치는 문단(사소한 갱신) ───────────────────────────────
EDIT = {
    (618, '새 주차 결선을 쓸 때 손댈 곳'): ('⑤ §3 「주차별 결선」 목록.',
                                          f'⑤ {P}주차별.md` 목록.'),
}

# ── 본문에 새로 넣는 글 ─────────────────────────────────────────────────────
V1_STUB = f"""## 2. 판형 v1 (`Breadboard.jpg`, 실험01~04 전용)

v1 좌표계(템플릿 998x1345·행·열·잭), 배포본으로 갈아끼우면 안 되는 이유, 좌우 블록 레일 뒤집힘은
{P}v1.md` 에 있다 — 실험01~04 그림을 다시 그리거나 고칠 때만 읽는다.

**레일에는 홀이 없는 행이 있다**(v1·v2 같다). 1·2·63행과 6행 주기의 빈 행(8·14·20·26·32…)에는 꽂을 데가 없고,
단자대(a~j)는 63행 전부 홀이 있다. `free_rail_row()` 가 레일 착지 행을 가까운 **빈** 실제 홀로 옮긴다."""

WEEK_STUB = f"""### 주차별 결선

실험01~04 의 회로 ID(`build_<ID>` 의 `<ID>` — 손그림 검토 `hand_compare.CIRCUITS` 의 회로 ID)·슬롯·걷기 보드
실물은 {P}주차별.md` 에 있다. 새 주차 목록도 그 파일에 덧붙인다 — 그 주차 결선 커밋에서 함께 고친다."""

HIST_POINTER = f"""규칙마다 그 규칙을 낳은 사건은 {P}연혁.md` 에 있다 — 규칙을 고치거나 없애기 전에 읽는다."""

HOWTO = f"""## 8. 이 문서에 쓰는 법

이 문서는 스킬을 부를 때마다 통째로 실린다. 그래서 **지금 지킬 규칙만** 쓴다. 본문 상한은
`tests/test_skill_docs.py` 의 `BREADBOARD_SKILL_MAX`({MAX_BYTES} 바이트)다.

- 규칙을 낳은 사건, 날짜 붙은 실험실 기록, "왜 이 검사가 없었나" → {P}연혁.md`
- 끝난 주차의 회로 ID·슬롯·걷기 보드 목록 → {P}주차별.md`
- v1 판형(실험01~04)에만 해당하는 것 → {P}v1.md`
- 본문 규칙에는 근거를 괄호 하나(실물 파일 하나 또는 연혁 항목 이름)로만 단다."""

# ── 조립 ─────────────────────────────────────────────────────────────────────
v1_set = {n for n, p in V1_BLOCKS}
week_set = {n for n, p in WEEK_BLOCKS}
hist_set = {n for n, p, t in HIST_BLOCKS}
comp = {n: (p, sec, new) for (n, p, sec), new in COMPRESS.items()}
edit = {n: (p, old, new) for (n, p), (old, new) in EDIT.items()}
for n, p in V1_BLOCKS + WEEK_BLOCKS:
    B(n, p)
for n, p, t in HIST_BLOCKS:
    B(n, p)
for n, (p, sec, new) in sorted(comp.items()):
    B(n, p)
B(23, '## 2. 브레드보드 물리 좌표계')
B(147, '### 주차별 결선')
B(159, '**완성본과 단계 그림을')
B(161, '**따라 그리기 층.**')
B(520, 'R11~R14 는 기하')

core = []
for n, text in blocks.items():
    if n == 23:
        core.append(V1_STUB)
    elif n == 147:
        core.append(WEEK_STUB)
    elif n == 159:
        core.append(dedent(text))
    elif n in v1_set or n in week_set or n in hist_set:
        continue
    elif n in comp:
        core.append(comp[n][2])
    elif n in edit:
        p, old, new = edit[n]
        assert old in text, (n, old)
        core.append(text.replace(old, new))
    else:
        core.append(text)
    if n == 520:
        core.append(HIST_POINTER)
core.append(HOWTO)
core_text = '\n\n'.join(core) + '\n'

v1_text = '\n\n'.join([
    '# v1 판형 (`Breadboard.jpg`) — 실험01~04 전용',
    f'{P}SKILL.md` §2 에서 옮긴 v1 좌표계다. 실험01~04 그림을 다시 그리거나 고칠 때만 읽는다. '
    'v2 주차(실험05~)는 이 파일을 읽지 않는다 — 좌표는 `.claude/assets/breadboard_v2/geometry.json` 에만 있다.',
] + [blocks[n] for n, p in V1_BLOCKS]) + '\n'

week_text = '\n\n'.join([
    '# 주차별 결선 (`보고서/실험NN/결선도/배치.py`)',
    f'{P}SKILL.md` §3 에서 옮긴 주차별 회로 목록이다. 지난 주차 그림을 다시 뽑거나 회로 ID 를 찾을 때만 '
    '읽는다. 새 주차 목록은 이 파일 끝에 덧붙이고 그 주차 결선 커밋에서 함께 고친다.',
] + [blocks[n] for n, p in WEEK_BLOCKS]) + '\n'

hist_parts = [
    '# 규칙 연혁 — 왜 이 규칙이 생겼나',
    f'{P}SKILL.md` 의 규칙을 낳은 사건이다. 규칙을 고치거나 없애기 전에 읽는다. 새 사건은 날짜와 함께 '
    '「사건」 절에 덧붙이고, 본문에는 규칙 문장만 쓴다.',
    '## 사건',
]
for n, p, t in HIST_BLOCKS:
    hist_parts += [f'### {t}', blocks[n]]
hist_parts += [
    '## 줄이기 전 원문 (2026-10-05)',
    '본문을 40KB 아래로 줄일 때 고쳐 쓴 문단의 원문이다. **갱신하지 않는다** — 지금 규칙은 본문이 정본이고, '
    '이 절과 본문이 다르면 본문을 따른다. 원문에만 있던 날짜·사건·실물 경로를 찾을 때 읽는다.',
]
for n, (p, sec, new) in sorted(comp.items()):
    body = '\n'.join(f'**원래 제목: {l.lstrip("#").strip()}**' if l.startswith('#') else l
                     for l in blocks[n].split('\n'))
    hist_parts += [f'### {sec} — 원래 {n}행', body]
hist_text = '\n\n'.join(hist_parts) + '\n'

OUT.mkdir(parents=True, exist_ok=True)
files = {'SKILL.md': core_text, 'v1.md': v1_text, '주차별.md': week_text, '연혁.md': hist_text}
for name, text in files.items():
    (OUT / name).write_text(text, encoding='utf-8', newline='\n')

# ── 검사 ─────────────────────────────────────────────────────────────────────
def norm(t):
    return '\n'.join(l.strip() for l in t.split('\n'))

union = norm('\n\n'.join(files.values()))
def body_of(t):
    return '\n'.join(l for l in t.split('\n') if not l.startswith('#'))


lost = [n for n, t in blocks.items()
        if n not in edit and body_of(t).strip() and norm(body_of(t)) not in union]
size = len(core_text.encode('utf-8'))
PINNED = ["BOARD = 'v2'", "board=BOARD", "| R9 |", "| R10 |", "breadboard_v2/geometry.json", "실험01~04 전용",
          "tests/fixtures/board_v2/배치.py", "| R11 |", "| R12 |", "| R13 |", "| R14 |", "spec.readability", "반 행",
          "n.c.", "2026-10-03-실험04-v2-시험판-결과.md", "place_search", "PLACE", "배치탐색.md", "PlaceEnforced",
          "PLACE_LENGTH_SLACK", "--jobs", "marker_near", "place_marker_hints", "DIP_PINS", "active_low=True",
          "Negative Logic", "pin 4, 3, 2, 1, 5, 6, 7", "tests/fixtures/board_v2_e5/배치.py",
          "Y0, Y1, Y2, Y3, Y4, Y5, Y9, Y6, Y8, Y7", "게이트 좌우 배정", "주차 빌더를 쓸 때", "## 4a."]
MARKERS = {'v1.md': 'y = 272.0 + (r-1) * 16.345', '주차별.md': '`e3_fa_s4`', '연혁.md': '검사를 통과시키려는 최소'}
missing = [s for s in PINNED if s not in core_text]
leaked = [f for f, m in MARKERS.items() if m in core_text or m not in files[f]]
pointers = [f for f in ('v1.md', '주차별.md', '연혁.md') if f'{P}{f}`' not in core_text]
for name, text in files.items():
    print(f'{name:10s} {len(text.encode("utf-8")):6d} B')
# 검토용: 줄인 문단마다 원문의 backtick 토큰 중 본문에서 사라진 것. 실패 조건이 아니다 — 사람이 보고
# "규칙이 아니라 사건·예시였다" 를 확인할 목록이다(원문은 연혁.md 에 있다).
for n, (p, sec, new) in sorted(comp.items()):
    gone = sorted({t for t in re.findall(r'`([^`\n]+)`', blocks[n]) if f'`{t}`' not in core_text})
    if gone:
        print(f'[검토] {n}행 ({sec}) 본문에서 빠진 토큰: {gone}')
print('lost blocks:', lost)
print('missing pinned:', missing)
print('marker leaks:', leaked)
print('missing pointers:', pointers)
ok = size <= MAX_BYTES and not (lost or missing or leaked or pointers)
print('OK' if ok else 'FAIL')
sys.exit(0 if ok else 1)
