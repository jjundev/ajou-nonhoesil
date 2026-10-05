# 결선도 엔진 조각 — 주차 빌더 도우미.
# 단독으로 import 하지 않는다. `../render_breadboard.py` 가 조각들을 `_PARTS` 순서대로 자기
# 이름공간에서 실행한다 — 앞 조각의 이름(import·상수·함수)을 import 없이 그대로 쓴다.

def _tag(bb, x, y, text, col=(60, 60, 60, 255)):
    """보드 **밖** 꼬리표 — 꽂을 자리(`입력 A → b7`). 신호 이름은 `signal_tag()` 가 보드 안에 둔다.

    앞 꼬리표와 겹치면 겹치지 않을 때까지 아래로 내린다 — 같은 행에 입력이 둘이면(실험04
    C2 의 S1·D, 31행) 뒤 꼬리표가 앞 것을 정확히 덮어 한 입력의 자리가 사라졌다."""
    font, pad = bb.font_kr_sm, 2

    def box(y_):
        b = bb.draw.textbbox((x, y_), text, font=font)
        return (b[0] - pad, b[1] - pad, b[2] + pad, b[3] + pad)

    def hits(b):
        return any(not (b[2] <= o[0] or o[2] <= b[0] or b[3] <= o[1] or o[3] <= b[1])
                   for _, o in bb.margin_tag_boxes)

    while hits(box(y)):
        y += 1
    bb.draw_badge(x, y, text, (255, 255, 255, 235), col, font=font, pad=pad)
    bb.margin_tag_boxes.append((text, box(y)))


def _input_jumper(bb, c, row, name, target, marker=None, col=None, side='a'):
    """입력 한 줄: **그쪽 GND 레일 홀 → 같은 행 `col` 열**. GND(=0) 자리를 그린 것이다.

    `side` 는 입력이 들어가는 핀이 칩의 어느 쪽인가다 — `'a'`(핀 1~7, a~e 쪽) 또는
    `'f'`(핀 8~14, f~j 쪽). 레일은 그쪽에 붙은 GND 다: 좌 블록은 a 쪽이 바깥 174, f 쪽이
    중앙 468 이고 우 블록은 뒤집혀 a 쪽이 중앙 542, f 쪽이 바깥 836 이다(v1 기준. v2 는 가운데 레일이 하나라 좌 f 쪽과 우 a 쪽이 같은 레일이다). 열 기본값은
    a 쪽 `b`, f 쪽 `i`(핀 홀 e·f 옆 d·g 는 전원선 자리라 한 칸 띈다 — `connect_power`).
    2026-09-18 실험03 에서 네 칩이 게이트 1·2 만 써 왼쪽에 11리드가 몰렸다(R7) — 게이트를
    좌·우로 나누면 오른쪽 게이트의 입력이 이 분기를 쓴다.

    아래는 좌 바깥 레일(side='a', 좌 블록) 의 경우다 — 다른 세 레일의 배지·번호 원
    자리는 본문 주석에 있다.

    `col` 은 같은 스트립에 **두 번째 점퍼(갈래)** 를 꽂을 때 쓴다. 갈래를 옆 홀에
    꽂되 그 갈래가 입력선 위를 되짚어 나가면 밑동이 굵은 입력선 아래 깔려
    "굵은 선 중간에서 얇은 선이 솟는" 그림이 된다 (2026-09-08 지적). 그래서
    입력선은 a 열에서 멈추고 갈래는 b 열에서 **세로로** 빠져나가게 한다.

    이전 판은 보드 밖 x=95 허공에서 선을 끌어왔다. 브레드보드 그림에서 홀이
    아닌 데서 나오는 선은 꽂을 데가 없다 — 따라 그리는 사람이 왼쪽 끝을 어디에
    꽂아야 하는지 알 수 없었다. netlist 공통 규칙(입력은 +5V 나 GND 에 직접
    물린다)대로 레일 홀에서 출발시키고, 1 을 줄 때는 레일 쪽 끝만 빨간 VCC
    레일로 옮겨 꽂는다고 범례에 적는다.

    레일에 홀이 없는 행(8·14·20행 따위)이나 이웃 입력이 이미 쓴 홀은
    `free_rail_row()` 가 피해 준다 — 7행·8행에 나란히 들어가는 A·B 는 B 가
    9행 홀에서 비스듬히 들어간다. `connect_unused_inputs()` 와 같은 관례다.

    번호 원은 기본으로 **레일 왼쪽 x=130, 행 높이 그대로** 둔다. 선이 레일에서
    시작하니 그 자리는 비어 있고, 선과 같은 높이라 어느 줄 번호인지 바로 읽힌다.
    단 템플릿에 행 번호가 인쇄된 10·20·30행은 거기가 막혀 있으니 레일과 a열
    사이 여백 `(215, ±13)` 으로 피한다. 꼬리표에는 꽂을 자리(b10)를 그대로
    적는다 — 왼쪽 눈금이 10·20·30 뿐이라 이름만 있으면 홀을 세어야 한다.

    **이름은 보드 안에도 적는다** — 레일 쪽 끝 옆, 보드 좌 테두리와 좌 GND 레일
    사이 여백이다(`signal_tag()`). 2026-09 실험01 예보가 "입력 A·B·C 위치 표기가
    없다" 로 감점됐다(-1) — 이름이 보드 밖 꼬리표에만 있었고 학생은 판형 위만
    따라 그렸다. 레일과 a 열 사이 여백은 쓰지 않는다: 복합 회로의 Z 급전선(x=212)이
    10~25행을 세로로 지나고, 번호 원 `(215, ±13)` 도 거기 앉는다(2026-09-14 실측).
    """
    assert side in ('a', 'f'), f"side 는 'a' 또는 'f' 다: {side!r}"
    block = 'left' if c is bb.cols['left'] else 'right'
    if side == 'a':
        x_rail = c['gnd'] if block == 'left' else c['mid_gnd']
        col = col or 'b'
    else:
        x_rail = c['mid_gnd'] if block == 'left' else c['gnd']
        col = col or 'i'
    r_rail = bb.free_rail_row(row, x_rail)
    y_rail, y_row = bb.r_y(r_rail), bb.r_y(row)
    # 신호 이름 배지와 번호 원의 기본 자리 — 레일 바깥 여백. 좌 바깥 레일은 보드 좌 테두리~레일
    # 사이, 우 바깥 레일은 VCC 레일~보드 우 테두리 사이, 가운데 레일은 판형이 정한
    # `spec.mid_badge_x`(v1: 좌 중앙 VCC 484 ~ 우 중앙 GND 542 의 가운데, v2: 가운데 VCC ~ 우 a 열의
    # 가운데)다. 번호 원은 좌·우 바깥이면 보드 밖 같은 행, 가운데면 배지 위 18px 다 — 여백이
    # 52~58px 라 나란히 못 놓는다.
    s = bb.spec
    if x_rail == bb.cols['left']['gnd']:
        badge_x, default_marker = (s.board_left + x_rail) / 2, (130, 0)
    elif x_rail == bb.cols['right']['gnd']:
        badge_x, default_marker = (bb.cols['right']['vcc'] + s.board_right) / 2, (s.board_right + 24, 0)
    else:
        # 가운데 레일(v1 은 좌 중앙 468·우 중앙 542 둘, v2 는 하나)이 이 자리를 같이 쓴다 — 같은
        # 행에 입력 둘을 넣으면 배지와 번호 원이 서로 위에 겹친다(가운데 여백은 한 번에 입력 한
        # 행만 받는다). 배지 겹침은 가독성 테스트가 잡는다.
        badge_x = s.mid_badge_x
        default_marker = (badge_x, -18)
    mx, dy = marker or default_marker
    pin = {'marker_at': (mx, y_row + dy)} if marker else {'marker_near': (mx, y_row + dy)}
    p0, p1 = (x_rail, y_rail), (c[col], y_row)
    # 걷기 보드(`removal_board`)가 이 점퍼를 걷는 장이면 `step_wire` 는 유령선만 그리고
    # 곧장 돌아온다 — 점유표도 구간도 레일 접촉도 안 남긴다. 꽂혀 있지 않은 선이다.
    # `step_wire` 와 **같은 식**으로 판정한다(회색 유지선·번호 끔도 None 을 돌려주니
    # 반환값으로는 못 가른다).
    ghosted = bb.ghost is not None and (
        'sig', bb._endpoint(p0), bb._endpoint(p1)) in bb.ghost['wires']
    bb.step_wire([p0, p1], 'sig',
                 f'입력 {name} -> {target} · 1 이면 레일 쪽 끝을 +5V 레일로 옮겨요', **pin)
    if not ghosted:
        # 이 점퍼는 `kind='sig'` 로 그린다(넷 검사가 입력을 GND 와 한 넷으로 세면 안
        # 되니까) — 그래서 `step_wire` 가 `touch_rail` 을 안 부르고, 레일 연결성 검사가
        # 이 레일을 아예 안 본다. 중앙 GND 468·우 바깥 GND 836 에 매달린 입력이 접지된
        # 레일과 안 이어져 있어도 verify() 가 통과하던 자리라 여기서 직접 찍는다
        # (2026-09-20). 걷는 점퍼에는 찍지 않는다 — 안 꽂힌 선 때문에 브리지를 내놓으라
        # 하게 된다. `input_node` 도 마찬가지다: 세그먼트가 안 쌓여 직전 배선(엉뚱한
        # 것)의 끝을 가상 입력 노드로 바꾸려다 단언에 걸린다.
        bb.touch_rail('gnd', x_rail)
        bb.input_node(name, c[col], row)
    _tag(bb, 12, y_row - 8, f"입력 {name} → {'우 ' if block == 'right' else ''}{col}{row}",
         col=INPUT)
    # 신호 이름은 보드 안, 레일 쪽 끝 옆. 0/1 을 바꿀 때 옮겨 꽂는 바로 그 끝이다
    bb.signal_tag(name, badge_x, y_rail, col=INPUT, seg=len(bb._segments) - 1,
                  arrow='right' if c[col] > x_rail else 'left')
