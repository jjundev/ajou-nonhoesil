"""All 실험06 schematics and timing diagrams, drawn from scratch (not copies of the originals)."""
from figlib import *

CAPTION = '선이 만나는 곳의 점은 연결, 점 없는 교차는 연결되지 않아요'


def save(fig, path):
    Path(path).write_text(fig.svg(), encoding='utf-8')


def _pin(f, x, y, n, side='in'):
    if n is None:
        return
    if side == 'in':
        f.text(x - 6, y - 7, str(n), size=18, anchor='end', fill=GREY)
    else:
        f.text(x + 4, y - 10, str(n), size=18, anchor='start', fill=GREY)


def latch(title, kind='sr', names=None, pins=True, chips=True, desc='', w=900, cross_pins=None):
    """Gated latch drawn the same way as the 교안 schematics.

    kind: 'sr' (S, C, R → 4 NAND), 'd' (D, C → NOT + 4 NAND),
          'jk' (J, C, K → two 3-input NAND + two NAND with Q/Q′ fed back),
          'basic' (S, R → two cross-coupled NAND, no enable).
    names: input labels in drawing order, e.g. ('S', 'C', 'R').
    """
    names = names or dict(sr=('S', 'E', 'R'), d=('D', 'E'), jk=('J', 'E', 'K'), basic=('S', 'R'))[kind]
    h = 520 if kind == 'basic' else 570
    f = Fig(w, h, title, desc)
    # cross-coupled pair (G3 top → Q, G4 bottom → Q′)
    g3 = f.and_(520, 70, 2, bubble=True, H=100)
    g4 = f.and_(520, 350, 2, bubble=True, H=100)
    (x3a, y3a), (x3b, y3b) = g3['ins']
    (x4a, y4a), (x4b, y4b) = g4['ins']
    qx, qy = g3['out']
    nx, ny = g4['out']
    xend = w - 80
    f.line([(qx, qy), (xend, qy)])
    f.line([(nx, ny), (xend, ny)])
    f.text(xend + 12, qy + 8, 'Q', weight='bold')
    f.text(xend + 12, ny + 8, 'Q′', weight='bold')
    # Q → G4 top input, Q′ → G3 bottom input
    f.dot(650, qy)
    f.line([(650, qy), (650, 300), (470, 300), (470, y4a), (x4a, y4a)])
    f.dot(680, ny)
    f.line([(680, ny), (680, 240), (490, 240), (490, y3b), (x3b, y3b)])
    chip_cross = '74HC00'
    if chips:
        f.text(560, 196, chip_cross, size=18, anchor='middle', fill=GREY)
        f.text(560, 476, chip_cross, size=18, anchor='middle', fill=GREY)
    if pins:
        # 74HC00 pins of the cross pair: G3 in/in/out, G4 in/in/out
        cp = cross_pins or ((1, 2, 3, 4, 5, 6) if kind in ('jk', 'basic') else (9, 10, 8, 12, 13, 11))
        _pin(f, x3a, y3a, cp[0])
        _pin(f, x3b, y3b, cp[1])
        _pin(f, qx, qy, cp[2], 'out')
        _pin(f, x4a, y4a, cp[3])
        _pin(f, x4b, y4b, cp[4])
        _pin(f, nx, ny, cp[5], 'out')

    if kind == 'basic':
        s, r = names
        f.text(20, y3a + 8, s, weight='bold')
        f.line([(60, y3a), (x3a, y3a)])
        f.text(20, y4b + 8, r, weight='bold')
        f.line([(60, y4b), (x4b, y4b)])
        f.text(20, h - 18, CAPTION, size=18, fill=GREY)
        return f

    n = 3 if kind == 'jk' else 2
    H = 100 if n == 3 else 80
    g1 = f.and_(240, y3a - H / 2, n, bubble=True, H=H)
    g2 = f.and_(240, y4b - H / 2, n, bubble=True, H=H)
    f.line([g1['out'], (x3a, y3a)])
    f.line([g2['out'], (x4b, y4b)])
    gate_chip = '74HC10' if n == 3 else '74HC00'
    if chips:
        f.text(285, y3a + H / 2 + 26, gate_chip, size=18, anchor='middle', fill=GREY)
        f.text(285, y4b + H / 2 + 26, gate_chip, size=18, anchor='middle', fill=GREY)
    i1, i2 = g1['ins'], g2['ins']
    cy = 260
    c_name = names[1]
    f.text(20, cy + 8, c_name, weight='bold')
    f.line([(60, cy), (170, cy)])
    f.dot(170, cy)
    top_c, bot_c = i1[-1], i2[0]
    f.line([(170, top_c[1]), (170, bot_c[1])])
    f.line([(170, top_c[1]), top_c])
    f.line([(170, bot_c[1]), bot_c])
    if kind == 'sr':
        f.text(20, i1[0][1] + 8, names[0], weight='bold')
        f.line([(60, i1[0][1]), i1[0]])
        f.text(20, i2[1][1] + 8, names[2], weight='bold')
        f.line([(60, i2[1][1]), i2[1]])
        if pins:
            for (px, py), k in zip(i1 + i2, (1, 2, 4, 5)):
                _pin(f, px, py, k)
            _pin(f, *g1['out'], 3, 'out')
            _pin(f, *g2['out'], 6, 'out')
    elif kind == 'd':
        dy = i1[0][1]
        f.text(20, dy + 8, names[0], weight='bold')
        f.line([(60, dy), i1[0]])
        f.dot(110, dy)
        ry = i2[1][1]
        f.line([(110, dy), (110, ry), (132, ry)])
        nt = f.not_(132, ry - 22)
        f.line([nt['out'], i2[1]])
        if chips:
            f.text(155, ry + 50, '74HC04', size=18, anchor='middle', fill=GREY)
        if pins:
            for (px, py), k in zip(i1 + i2, (1, 2, 4, 5)):
                _pin(f, px, py, k)
            _pin(f, *g1['out'], 3, 'out')
            _pin(f, *g2['out'], 6, 'out')
            f.text(126, ry - 10, '1', size=18, anchor='end', fill=GREY)
            f.text(nt['out'][0] + 4, ry - 10, '2', size=18, fill=GREY)
    elif kind == 'jk':
        jy, ky = i1[1][1], i2[1][1]
        f.text(20, jy + 8, names[0], weight='bold')
        f.line([(60, jy), i1[1]])
        f.text(20, ky + 8, names[2], weight='bold')
        f.line([(60, ky), i2[1]])
        # Q′ → G1 top input (over the top), Q → G2 bottom input (under the bottom)
        f.dot(735, ny)
        f.line([(735, ny), (735, 25), (205, 25), (205, i1[0][1]), i1[0]])
        f.dot(760, qy)
        f.line([(760, qy), (760, 520), (205, 520), (205, i2[2][1]), i2[2]])
        if pins:
            for (px, py), k in zip(i1, (1, 2, 13)):
                _pin(f, px, py, k)
            for (px, py), k in zip(i2, (3, 4, 5)):
                _pin(f, px, py, k)
            _pin(f, *g1['out'], 12, 'out')
            _pin(f, *g2['out'], 6, 'out')
    f.text(20, h - 14, CAPTION, size=18, fill=GREY)
    return f


def not_loop(title):
    """Two NOT gates in a ring: the memory idea before NAND handles are added."""
    f = Fig(760, 380, title, 'NOT1의 출력 Q가 NOT2로, NOT2의 출력 Q′이 NOT1로 돌아가는 고리')
    n1 = f.not_(330, 72, H=56)
    n2 = f.not_(330, 232, H=56)
    (ax, ay), = n1['ins']
    (bx, by), = n2['ins']
    qx, qy = n1['out']
    nx, ny = n2['out']
    f.line([(qx, qy), (640, qy)])
    f.line([(nx, ny), (640, ny)])
    f.text(652, qy + 8, 'Q', weight='bold')
    f.text(652, ny + 8, 'Q′', weight='bold')
    # Q → NOT2 input, Q′ → NOT1 input
    f.dot(500, qy)
    f.line([(500, qy), (500, 200), (260, 200), (260, by), (bx, by)])
    f.dot(540, ny)
    f.line([(540, ny), (540, 165), (220, 165), (220, ay), (ax, ay)])
    f.text(353, 60, 'NOT1', size=18, anchor='middle', fill=GREY)
    f.text(353, 312, 'NOT2', size=18, anchor='middle', fill=GREY)
    f.text(580, qy - 12, '1', size=22, anchor='middle', fill=BLUE, weight='bold')
    f.text(580, ny - 12, '0', size=22, anchor='middle', fill=BLUE, weight='bold')
    f.text(20, 345, 'Q=1이면 NOT2가 0을, NOT1이 다시 1을 내서 그대로예요.', size=18, fill=BLUE)
    f.text(20, 372, CAPTION, size=18, fill=GREY)
    return f


def jk_latch(title, names=('J', 'E', 'K'), pins=True, desc=''):
    return latch(title, 'jk', names, pins=pins, desc=desc)


# ------------------------------------------------------------------ blocks
def ff_block(f, x, y, ins, outs, clk=None, clk_bubble=False, pr_clr=False, w=220, h=240):
    """Rectangle symbol. ins: list of (label, y_offset); clk: y_offset of the clock pin."""
    f.rect(x, y, w, h, fill='#fff', rx=4)
    for lab, dy in ins:
        f.line([(x - 70, y + dy), (x, y + dy)])
        f.text(x + 14, y + dy + 8, lab, weight='bold')
    if clk is not None:
        cy = y + clk
        f.path(f'M{x:g},{cy-14:g} L{x+20:g},{cy:g} L{x:g},{cy+14:g}', fill='none')
        if clk_bubble:
            f.circle(x - 7, cy, 7)
            f.line([(x - 70, cy), (x - 14, cy)])
        else:
            f.line([(x - 70, cy), (x, cy)])
        f.text(x + 26, cy + 8, 'CK', size=20, fill=GREY)
    for lab, dy in outs:
        f.line([(x + w, y + dy), (x + w + 70, y + dy)])
        f.text(x + w - 14, y + dy + 8, lab, anchor='end', weight='bold')
    return dict(l=x - 70, r=x + w + 70)


def tff_fig(title):
    f = Fig(760, 360, title, 'J와 K를 하나로 묶은 입력 T와 하강 엣지 클록을 받는 J-K 플립플롭')
    x, y = 330, 60
    ff_block(f, x, y, [('J', 50), ('K', 190)], [('Q', 50), ('Q′', 190)], clk=120, clk_bubble=True)
    f.text(40, y + 58, 'T', weight='bold', size=24)
    f.line([(70, y + 50), (x - 70, y + 50)])
    f.dot(190, y + 50)
    f.line([(190, y + 50), (190, y + 190), (x - 70, y + 190)])
    f.text(40, y + 128, 'CLK', weight='bold')
    f.line([(100, y + 120), (x - 70, y + 120)])
    f.text(x + 300, y + 58, 'Q', weight='bold')
    f.text(x + 300, y + 198, 'Q′', weight='bold')
    f.text(20, 340, 'CK 앞의 원은 하강 엣지(1→0)에서 동작한다는 표시예요. 점 없는 교차는 연결되지 않아요.', size=18, fill=GREY)
    return f


def hc76_fig(title):
    f = Fig(940, 640, title, '74HC76 16핀 DIP의 핀 배치. 5번이 VCC, 13번이 GND예요')
    bx, by, bw, bh = 330, 40, 280, 520
    f.rect(bx, by, bw, bh, fill='#fff', rx=6)
    f.path(f'M{bx+bw/2-30:g},{by:g} a30,30 0 0 0 60,0', fill='#fff')
    left = ['1CK', '1PR (SET)', '1CLR (RESET)', '1J', 'VCC', '2CK', '2PR (SET)', '2CLR (RESET)']
    right = ['1K', '1Q', '1Q′', 'GND', '2K', '2Q', '2Q′', '2J']
    for i in range(8):
        y = by + 50 + i * 60
        n_l, n_r = i + 1, 16 - i
        for side, n, lab in (('l', n_l, left[i]), ('r', n_r, right[i])):
            px = bx - 40 if side == 'l' else bx + bw
            f.rect(px, y - 16, 40, 32, fill='#fff', rx=2, sw=2)
            f.text(px + 20, y + 8, str(n), size=20, anchor='middle')
            power = lab in ('VCC', 'GND')
            col = RED if power else INK
            if side == 'l':
                f.text(px - 14, y + 8, lab, anchor='end', fill=col, weight='bold' if power else None)
            else:
                f.text(px + 54, y + 8, lab, anchor='start', fill=col, weight='bold' if power else None)
    f.text(bx + bw / 2, by + bh / 2 - 10, '74HC76', size=28, anchor='middle', weight='bold')
    f.text(bx + bw / 2, by + bh / 2 + 26, 'J-K F/F × 2', size=22, anchor='middle', fill=GREY)
    f.text(20, 600, 'VCC 5번, GND 13번: 흔한 배치(14핀 14·7번, 16핀 16·8번)와 달라요.', size=20, fill=RED)
    f.text(20, 628, 'PR(SET)·CLR(RESET)은 0일 때 동작해요(Active Low). 클록은 하강 엣지예요.', size=20, fill=GREY)
    return f


# ------------------------------------------------------------------ timing
class Timing:
    def __init__(self, f, x0, t_end, unit):
        self.f, self.x0, self.unit, self.t_end = f, x0, unit, t_end

    def x(self, t):
        return self.x0 + t * self.unit

    def wave(self, y, name, segs, color=INK, h=40, sub=None):
        """segs: list of (t0, t1, level) with level 0, 1 or None (정해지지 않음)."""
        f = self.f
        f.text(20, y - h / 2 + 8, name, weight='bold', fill=color)
        if sub:
            f.text(20, y - h / 2 + 34, sub, size=18, fill=GREY)
        prev = None
        for t0, t1, lv in segs:
            x0, x1 = self.x(t0), self.x(t1)
            if lv is None:
                f.raw(f'<rect x="{x0:g}" y="{y-h:g}" width="{x1-x0:g}" height="{h:g}" fill="#d9dee6" stroke="none"/>')
                f.text((x0 + x1) / 2, y - h / 2 + 7, '?', size=20, anchor='middle', fill=GREY)
            else:
                yy = y - h if lv else y
                if prev is not None and prev != lv:
                    f.line([(x0, y - h), (x0, y)], color=color)
                f.line([(x0, yy), (x1, yy)], color=color)
            prev = lv

    def mark(self, t, y0, y1, label=None):
        f = self.f
        f.line([(self.x(t), y0), (self.x(t), y1)], color=BLUE, width=2, dash='6 6')
        if label:
            f.text(self.x(t), y0 - 8, label, size=18, anchor='middle', fill=BLUE)


def level_edge_fig(title):
    f = Fig(940, 520, title, 'Enable·클록 C가 1인 동안 D를 따라가는 D 래치와, C가 0에서 1로 오르는 순간에만 D를 저장하는 D 플립플롭의 비교')
    T = Timing(f, 250, 16, 40)
    C = [(0, 2, 0), (2, 6, 1), (6, 10, 0), (10, 14, 1), (14, 16, 0)]
    D = [(0, 3, 0), (3, 5, 1), (5, 8, 0), (8, 12, 1), (12, 16, 0)]
    QL = [(0, 2, None), (2, 3, 0), (3, 5, 1), (5, 10, 0), (10, 12, 1), (12, 16, 0)]
    QF = [(0, 2, None), (2, 10, 0), (10, 16, 1)]
    for yy, name, segs, col, sub in [(110, 'C', C, INK, None), (210, 'D', D, INK, None),
                                     (330, 'Q', QL, BLUE, 'D 래치'), (450, 'Q', QF, GRN, 'D F/F (↑)')]:
        T.wave(yy, name, segs, col, sub=sub)
    for t in (2, 10):
        T.mark(t, 50, 460, '↑')
    f.text(T.x(2) + 8, 470, 'Q=D(0) 저장', size=18, fill=GRN)
    f.text(T.x(10) + 8, 470, 'Q=D(1) 저장', size=18, fill=GRN)
    for a, b in ((2, 6), (10, 14)):
        f.parts.insert(0, f'<rect x="{T.x(a):g}" y="280" width="{T.x(b)-T.x(a):g}" height="60" fill="{BLUEBG}"/>')
    f.text((T.x(2) + T.x(6)) / 2, 272, 'C=1: D를 따라가요', size=18, anchor='middle', fill=BLUE)
    f.text((T.x(6) + T.x(10)) / 2, 272, 'C=0: 유지', size=18, anchor='middle', fill=GREY)
    f.text(20, 505, '회색 ?는 아직 정해지지 않은 값이에요. 파란 점선은 C가 0→1로 오르는 순간이에요.', size=18, fill=GREY)
    return f


def memory_fig(title):
    f = Fig(940, 470, title, 'Enable이 1인 SR 래치에서 S를 잠깐 1로 했다가 내려도 Q가 1로 남고, R을 잠깐 1로 하면 Q가 0이 되는 모습')
    T = Timing(f, 250, 16, 40)
    E = [(0, 16, 1)]
    S = [(0, 3, 0), (3, 5, 1), (5, 16, 0)]
    R = [(0, 10, 0), (10, 12, 1), (12, 16, 0)]
    Q = [(0, 3, None), (3, 10, 1), (10, 16, 0)]
    for yy, name, segs, col in [(100, 'E', E, INK), (190, 'S', S, INK), (280, 'R', R, INK), (400, 'Q', Q, BLUE)]:
        T.wave(yy, name, segs, col)
    f.parts.insert(0, f'<rect x="{T.x(5):g}" y="350" width="{T.x(10)-T.x(5):g}" height="60" fill="{BLUEBG}"/>')
    f.text((T.x(5) + T.x(10)) / 2, 342, 'S=0, R=0 → 그대로 1', size=20, anchor='middle', fill=BLUE, weight='bold')
    f.text((T.x(12) + T.x(16)) / 2, 342, '그대로 0', size=20, anchor='middle', fill=BLUE, weight='bold')
    f.text(20, 455, '회색 ?는 전원을 켠 직후처럼 아직 정해지지 않은 값이에요.', size=18, fill=GREY)
    return f
