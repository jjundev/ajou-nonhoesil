# 결선도 엔진 조각 — 주차 빌더 도우미.
# 단독으로 import 하지 않는다. `../render_breadboard.py` 가 조각들을 `_PARTS` 순서대로 자기
# 이름공간에서 실행한다 — 앞 조각의 이름(import·상수·함수)을 import 없이 그대로 쓴다.

def _tag(bb, x, y, text, col=(60, 60, 60, 255)):
    """보드 **밖** 꼬리표 — 꽂을 자리(`입력 A → b7`). 앞 꼬리표와 겹치면 아래로 내린다(실험04
    같은 행 입력 둘이 서로 덮었다). 신호 이름은 `signal_tag()` 가 보드 안에 둔다."""
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
    """입력 한 줄: **그쪽 GND 레일 홀 → 같은 행 `col` 열** — GND(=0) 자리. 1 을 줄 때는 레일 쪽 끝만
    +5V 레일로 옮긴다(입력을 허공에서 끌어오면 꽂을 데가 없다).

    `side` 는 입력 핀이 칩의 어느 쪽인가 — `'a'`(핀 1~7) 또는 `'f'`(핀 8~14). 레일은 그쪽 GND 다.
    열 기본값은 a 쪽 `b`, f 쪽 `i` — d·g 는 전원선 자리(`connect_power`). `col` 은 같은 스트립의
    두 번째 점퍼(갈래)용이다 — 갈래가 입력선 위를 되짚으면 굵은 선 아래 깔린다(2026-09-08).
    빈 레일 행·이웃이 쓴 홀은 `free_rail_row()` 가 피한다.

    신호 이름은 보드 안 레일 쪽 끝 옆에도 적는다(`signal_tag()`) — 2026-09 실험01 예보가 입력 위치
    표기 없음으로 감점됐다. 번호 원·배지 기본 자리는 본문 주석에 있다.
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
    # 배지·번호 원 기본 자리 — 레일 바깥 여백(가운데 레일은 `spec.mid_badge_x`). 번호 원은 좌·우
    # 바깥이면 보드 밖 같은 행, 가운데면 배지 위 18px — 여백이 좁아 나란히 못 놓는다.
    s = bb.spec
    y_mark = y_row
    if x_rail == bb.cols['left']['gnd']:
        badge_x, default_marker = (s.board_left + x_rail) / 2, (130, 0)
    elif x_rail == bb.cols['right']['gnd']:
        badge_x, default_marker = (bb.cols['right']['vcc'] + s.board_right) / 2, (s.board_right + 24, 0)
    else:
        # 가운데 레일들이 이 자리를 같이 쓴다 — 같은 행 입력 둘은 겹친다(가독성 시험이 잡는다)
        badge_x = s.mid_badge_x
        default_marker = (badge_x, -18)
        if s.readability:
            # 배지는 레일 착지 행(`y_rail`)에 붙는다 — 핀 행이 레일 빈 행이면 착지가 한 행 밀려 핀 행 기준
            # 원이 제 배지를 덮었다(2026-10-05 실험05 C2 `D1`). v1 은 도장을 지키려고 핀 행 그대로
            y_mark = y_rail
    mx, dy = marker or default_marker
    y0 = y_row if marker else y_mark
    pin = {'marker_at': (mx, y0 + dy)} if marker else {'marker_near': (mx, y0 + dy)}
    p0, p1 = (x_rail, y_rail), (c[col], y_row)
    # 걷기 보드가 이 점퍼를 걷으면 `step_wire` 는 유령선만 그린다 — 꽂혀 있지 않은 선이다.
    # `step_wire` 와 같은 식으로 판정한다(반환값은 회색 유지선도 None 이라 못 가른다).
    ghosted = bb.ghost is not None and (
        'sig', bb._endpoint(p0), bb._endpoint(p1)) in bb.ghost['wires']
    arrow = 'right' if c[col] > x_rail else 'left'
    # v2 는 번호 원 자리를 고르기 전에 제 배지 자리를 잡아 둔다 — 배지를 원 뒤에 그려 `_settle_marker` 가
    # 몰랐고, 가운데 레일에 배지가 한 행씩 쌓이면 원이 곧 그려질 제 배지 위에 앉았다(2026-10-05 실험05 C1 `Bit1`)
    held = (name, bb._signal_tag_geom(name, badge_x, y_rail, arrow=arrow)[0], None)
    if s.readability:
        bb.tag_boxes.append(held)
    bb.step_wire([p0, p1], 'sig',
                 f'입력 {name} -> {target} · 1 이면 레일 쪽 끝을 +5V 레일로 옮겨요', **pin)
    if s.readability:
        bb.tag_boxes.remove(held)
    if not ghosted:
        # `kind='sig'` 라 `step_wire` 가 `touch_rail` 을 안 부른다 — 레일 연결성 검사가 이 레일을
        # 보도록 직접 찍는다(2026-09-20). 걷는 점퍼는 안 꽂힌 선이라 찍지도, 입력 노드도 안 둔다.
        bb.touch_rail('gnd', x_rail)
        bb.input_node(name, c[col], row)
    _tag(bb, 12, y_row - 8, f"입력 {name} → {'우 ' if block == 'right' else ''}{col}{row}",
         col=INPUT)
    # 신호 이름은 레일 쪽 끝 옆 — 0/1 을 바꿀 때 옮겨 꽂는 끝이다
    bb.signal_tag(name, badge_x, y_rail, col=INPUT, seg=len(bb._segments) - 1, arrow=arrow)
