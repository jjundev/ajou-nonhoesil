"""교안·기출 회로를 직접 그린 벡터 원고와 300dpi 워크북 그림."""
from figlib import Fig, render_png, sha, BLUE, BLUEBG, GREY, INK, RED, GRN
from pathlib import Path
import json, base64, re, sys
REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / '.claude/skills/breadboard-diagram/scripts'))

from scripts.lab.review_pack.note_schematic import SchematicSymbols, write_note_schematics

ORANGE = '#b45309'


class NoteFig(SchematicSymbols, Fig):
    pass


def resistor_label(f, x, y, label, anchor='middle'):
    parts = re.fullmatch(r'(R)([0-9]+|f|L)(.*)', label)
    if parts:
        f.label(x, y, parts[1], sub=parts[2], suffix=parts[3], size=24, anchor=anchor)
    elif label == '2ⁿ⁻¹R':
        f.label(x, y, '2', super_='n−1', suffix='R', size=24, anchor=anchor)
    else:
        f.label(x, y, label, size=24, anchor=anchor)


# ---- 작은 부품 --------------------------------------------------------------
def res_h(f, x1, x2, y, label=None, dy=-16, color=INK):
    m = (x1 + x2) / 2
    a, b = m - 30, m + 30
    f.line([(x1, y), (a, y)], color=color)
    f.path(f'M{a:g},{y:g} l5,-10 l10,20 l10,-20 l10,20 l10,-20 l10,20 l5,-10', fill='none', stroke=color)
    f.line([(b, y), (x2, y)], color=color)
    if label and isinstance(f, NoteFig):
        resistor_label(f, m, y - 30, label)
    elif label:
        f.text(m, y + dy, label, size=18, anchor='middle', fill=color)


def res_v(f, x, y1, y2, label=None, dx=16, color=INK, anchor='start'):
    m = (y1 + y2) / 2
    a, b = m - 30, m + 30
    if isinstance(f, NoteFig):
        step = min(10, (y2 - y1) / 8)
        a, b = m - 3 * step, m + 3 * step
        points = [(x + (10 if i % 2 else -10), a + (i + 0.5) * step) for i in range(6)]
        f.line([(x, a), *points, (x, b)], color=color)
    else:
        f.line([(x, y1), (x, a)], color=color)
        f.path(f'M{x:g},{a:g} l-10,5 l20,10 l-20,10 l20,10 l-20,10 l20,10 l-10,5', fill='none', stroke=color)
    if isinstance(f, NoteFig):
        f.line([(x, y1), (x, a)], color=color)
    f.line([(x, b), (x, y2)], color=color)
    if label and isinstance(f, NoteFig):
        for i, text in enumerate(label.split('\n')):
            x_label = x + max(dx, 32) if anchor == 'start' else x + min(dx, -32)
            resistor_label(f, x_label, m + 8 + i * 28, text, anchor)
    elif label:
        lines = label.split('\n')
        for i, t in enumerate(lines):
            f.text(x + dx, m - 10 * (len(lines) - 1) + 20 * i + 6, t, size=18, anchor=anchor, fill=color)


def gnd(f, x, y):
    f.line([(x, y), (x, y + 10)])
    f.line([(x - 15, y + 10), (x + 15, y + 10)])
    f.line([(x - 9, y + 17), (x + 9, y + 17)])
    f.line([(x - 3, y + 24), (x + 3, y + 24)])


def term(f, x, y, name, side='left', color=INK, size=22, *, node=None):
    if isinstance(f, NoteFig):
        palette = 'red' if color == RED else 'blue'
        f.junction(x, y, node=node, color=palette)
        offsets = {'left': (-25, 8, 'end'), 'right': (25, 8, 'start'), 'top': (0, -35, 'middle')}
        dx, dy, anchor = offsets[side]
        signal = re.fullmatch(r'([VD])(in|out|o|ref|n|[0-9]+)', name)
        if signal:
            f.label(x + dx, y + dy, signal[1], sub=signal[2], anchor=anchor, node=node, color=palette)
        else:
            f.label(x + dx, y + dy, name, anchor=anchor, node=node, color=palette)
        return
    f.circle(x, y, 6, stroke=color)
    if side == 'left':
        f.text(x - 12, y + 7, name, size=size, anchor='end', fill=color, weight='bold')
    elif side == 'right':
        f.text(x + 12, y + 7, name, size=size, fill=color, weight='bold')
    else:
        f.text(x, y - 14, name, size=size, anchor='middle', fill=color, weight='bold')


def opamp(f, x, y, W=140, H=160, label=None, minus_top=True, pins=None):
    """삼각형 왼쪽 변 x, 가운데 y. 반환: 위 입력·아래 입력·출력·위/아래 변 가운데."""
    f.path(f'M{x:g},{y-H/2:g} L{x:g},{y+H/2:g} L{x+W:g},{y:g} Z', fill=BLUEBG, stroke=BLUE)
    top, bot = (x, y - H / 4), (x, y + H / 4)
    offset = 20 if isinstance(f, NoteFig) else 14
    f.text(x + offset, top[1] + 9, '−' if minus_top else '+', size=28, fill=INK, weight='bold')
    f.text(x + offset, bot[1] + 9, '+' if minus_top else '−', size=28, fill=INK, weight='bold')
    if label:
        f.text(x + W * 0.42, y + 8, label, size=18, anchor='middle', fill=GREY)
    out = (x + W, y)
    mid = x + W / 2
    if pins:
        a, b, o = pins[:3]
        dy = 19 if isinstance(f, NoteFig) else 8
        f.text(x - 8, top[1] - dy, a, size=18, anchor='end', fill=GREY)
        f.text(x - 8, bot[1] - dy, b, size=18, anchor='end', fill=GREY)
        f.text(out[0] + 8, out[1] - (dy + 2), o, size=18, fill=GREY)
    return dict(top=top, bot=bot, out=out, up=(mid, y - H / 4), down=(mid, y + H / 4))


# ---- 실험설명 그림 ----------------------------------------------------------
def opamp_inv():
    f = NoteFig(793, 346, '반전 증폭기',
                '입력은 R1을 거쳐 반전 입력에 연결되고, Rf가 출력을 반전 입력으로 되돌린다. 비반전 입력은 접지한다.')
    o = opamp(f, 405, 203, label='Op-Amp')
    iy, oy = o['top'][1], o['out'][1]
    term(f, 98, iy, 'Vin', node='vin')
    res_h(f, 98, 310, iy, 'R1')
    f.line([(310, iy), o['top']])
    f.junction(328, iy, node='minus', color='red')
    f.label(305, iy + 47, 'V', sub='−', suffix=' ≈ 0 V',
            anchor='end', node='minus', color='red')
    f.line([(328, iy), (328, 83), (410, 83)])
    res_h(f, 410, 585, 83, 'Rf')
    f.line([(585, 83), (620, 83), (620, oy)])
    f.junction(620, oy, node='out')
    f.line([o['out'], (699, oy)])
    term(f, 699, oy, 'Vout', 'right', node='out')
    f.line([o['bot'], (340, o['bot'][1]), (340, 299)])
    gnd(f, 340, 299)
    return f


def summing(n=4, title='네 입력 반전 가산증폭기', node_label=True, *, note=False):
    H = 110 + 70 * (n - 1) + 270
    f = (NoteFig if note else Fig)(875 if note else 900, H - 50 if note else H, title, f'V1~V{n}이 R1~R{n}을 지나 반전 입력의 한 점에서 만나요. Rf 귀환, 비반전 입력 접지.')
    ys = [110 + 70 * i for i in range(n)]
    bus = 360
    for i, yy in enumerate(ys):
        term(f, 80, yy, f'V{i+1}')
        res_h(f, 80 if note else 86, bus, yy, f'R{i+1}')
        if note:
            f.junction(bus, yy, node='summing', color='red')
        else:
            f.dot(bus, yy)
    yc = ys[-1] + 60
    o = opamp(f, 470, yc + 40, label='Op-amp')
    f.line([(bus, ys[0]), (bus, o['top'][1]), o['top']])
    feedback_y = 74 if note else 50
    f.line([(bus, ys[0]), (bus, feedback_y), (480, feedback_y)])
    res_h(f, 480, 640, feedback_y, 'Rf', dy=-14)
    f.line([(640, feedback_y), (680, feedback_y), (680, o['out'][1])])
    if note:
        f.junction(680, o['out'][1], node='out')
    else:
        f.dot(680, o['out'][1])
    f.line([o['out'], (766 if note else 760, o['out'][1])])
    term(f, 766, o['out'][1], 'Vo', 'right', node='out' if note else None)
    f.line([o['bot'], (430, o['bot'][1]), (430, o['bot'][1] + 30)])
    gnd(f, 430, o['bot'][1] + 30)
    if node_label and note:
        f.label(bus - 23, o['top'][1] + 7, 'V', sub='−', suffix=' ≈ 0 V',
                anchor='end', node='summing', color='red')
    elif node_label:
        f.text(bus - 12, o['top'][1] - 12, '≈ 0V', size=20, anchor='end', fill=RED)
    return f


def network(given=False, *, note=False):
    f = (NoteFig if note else Fig)(1300, 505 if note else 560, 'Weighted resistor와 Ladder type resistor', '왼쪽 가중 저항, 오른쪽 R-2R 래더')
    # 가중 저항
    xs = [90, 210, 330, 450]
    names = ['D1', 'D2', 'D3', 'Dn']
    labs = ['R', '2R', '4R', '2ⁿ⁻¹R']
    for x, n_, lab in zip(xs, names, labs):
        term(f, x, 70, n_, 'top')
        res_v(f, x, 70 if note else 76, 260, lab)
        if not note or x != xs[0]:
            f.dot(x, 260)
    f.text(390, 112, '…', size=28, anchor='middle')
    f.line([(xs[0], 260), (xs[-1], 260)])
    f.dot(270, 260)
    res_v(f, 270, 260, 420, 'RL ≫ R')
    gnd(f, 270, 420)
    if not given:
        f.line([(450, 260), (505, 260)])
        term(f, 505, 260, 'Vo', 'right')
    if note:
        f.label(270, 488, '가중 저항', anchor='middle')
    else:
        f.text(270, 520, 'Weighted resistor', size=22, anchor='middle', weight='bold')
    # 래더
    xs2 = [760, 900, 1040, 1180]
    names2 = ['Dn', 'D3', 'D2', 'D1']
    for x, n_ in zip(xs2, names2):
        term(f, x, 70, n_, 'top')
        res_v(f, x, 70 if note else 76, 300, '2R')
        f.dot(x, 300)
    res_h(f, 620, 760, 300, '2R')
    for a, b in zip(xs2, xs2[1:]):
        res_h(f, a, b, 300, 'R')
    f.line([(620, 300), (620, 400)])
    gnd(f, 620, 400)
    f.text(830, 112, '…', size=28, anchor='middle')
    if not given:
        f.line([(1180, 300), (1225, 300)])
        term(f, 1225, 300, 'Vo', 'right')
    if note:
        f.label(900, 480, 'R–2R 래더', anchor='middle')
    else:
        f.text(900, 520, 'Ladder type resistor', size=22, anchor='middle', weight='bold')
    return f


def oc():
    f = NoteFig(970, 325, '7404, 7405와 1.5kΩ 풀업',
                '7405의 출력, 1.5kΩ 풀업, 가중 저항이 한 접점에서 만난다.')
    y = 210
    term(f, 167, y, 'Q (7490)', node='bit')
    a = f.not_(185, y - 22)
    f.line([(167, y), a['ins'][0]])
    b = f.not_(369, y - 22)
    f.line([a['out'], b['ins'][0]])
    f.label(208, y + 54, '7404', anchor='middle')
    f.label(392, y + 54, '7405', anchor='middle')
    f.label(392, y + 85, '오픈 컬렉터', size=22, anchor='middle')
    f.line([b['out'], (606, y)])
    f.junction(563, y, node='pulled', color='red')
    f.label(533, y - 34, 'V', sub='bit', anchor='end', node='pulled', color='red')
    res_v(f, 563, 81, y, '1.5 kΩ')
    f.junction(563, 81)
    f.label(563, 58, '+5 V', anchor='middle')
    res_h(f, 606, 786, y, '가중 저항')
    f.line([(786, y), (815, y)])
    term(f, 815, y, '가산점으로', 'right')
    return f


def dac(title='DAC 회로 (교안 회로도를 다시 그림)', pin7=None):
    f = Fig(1560, 860, title, '7490 → 7404 → 7405(풀업 1.5k) → 가중 저항 → LM741 반전 가산증폭기, V+는 +15V 분배기')
    rows = [180, 280, 380, 480]
    bx0, bx1 = 160, 320
    f.rect(bx0, 120, bx1 - bx0, 420, fill='#fff', rx=4)
    f.text((bx0 + bx1) / 2, 520, 'U1 7490', size=20, anchor='middle', fill=GREY)
    # 왼쪽 핀
    lp = [(180, '14', 'CLKA'), (230, '1', 'CLKB'), (300, '2', 'R01'), (340, '3', 'R02'), (380, '6', 'R91'), (420, '7', 'R92')]
    for yy, num, name in lp:
        f.line([(bx0 - 30, yy), (bx0, yy)])
        f.text(bx0 + 8, yy + 7, name, size=18)
        f.text(bx0 - 6, yy - 6, num, size=18, anchor='end', fill=GREY)
    term(f, 50, 180, 'clk', 'top', color=RED)
    f.line([(56, 180), (bx0 - 30, 180)])
    # R 핀 접지
    f.line([(bx0 - 30, 300), (80, 300), (80, 460)])
    for yy in (340, 380, 420):
        f.line([(bx0 - 30, yy), (80, yy)])
        f.dot(80, yy)
    gnd(f, 80, 460)
    # 오른쪽 핀
    rp = [('12', 'QA'), ('9', 'QB'), ('8', 'QC'), ('11', 'QD')]
    for yy, (num, name) in zip(rows, rp):
        f.text(bx1 - 8, yy + 7, name, size=18, anchor='end')
        f.text(bx1 + 6, yy - 8, num, size=18, fill=GREY)
    # QA → CLKB
    f.dot(350, rows[0])
    f.line([(350, rows[0]), (350, 90), (105, 90), (105, 230), (bx0 - 30, 230)])
    # 인버터 두 개씩
    pinpairs = [('1', '2'), ('3', '4'), ('5', '6'), ('9', '8')]
    for yy, (pi, po) in zip(rows, pinpairs):
        a = f.not_(420, yy - 22)
        f.line([(bx1, yy), a['ins'][0]])
        b = f.not_(560, yy - 22)
        f.line([a['out'], b['ins'][0]])
        f.text(412, yy - 10, pi, size=18, anchor='end', fill=GREY)
        f.text(a['out'][0] + 2, yy - 12, po, size=18, fill=GREY)
        f.text(552, yy - 10, pi, size=18, anchor='end', fill=GREY)
        f.text(b['out'][0] + 2, yy - 12, po, size=18, fill=GREY)
        f.line([b['out'], (960, yy)])
    f.text(445, 545, '7404 (U2)', size=18, anchor='middle', fill=GREY)
    f.text(585, 545, '7405 (U3)', size=18, anchor='middle', fill=GREY)
    # 풀업
    px = [700, 770, 840, 910]
    f.line([(px[0], 60), (px[-1], 60)])
    f.line([(805, 60), (805, 44)])
    f.text(805, 36, '+5V', size=20, anchor='middle', weight='bold', fill=RED)
    for i, (x, yy) in enumerate(zip(px, rows)):
        res_v(f, x, 60, 150, f'R{i+1}\n1.5k', dx=13)
        f.line([(x, 150), (x, yy)])
        f.dot(x, yy)
    # 가중 저항
    wv = ['22.6k', '10.5k', '4.5k', '1.5k']
    for i, (yy, v) in enumerate(zip(rows, wv)):
        res_h(f, 960, 1120, yy, f'R{i+5} {v}')
    f.text(1200, rows[0] + 7, 'LSB', size=20, fill=GREY)
    f.text(1200, rows[-1] + 7, 'MSB', size=20, fill=GREY)
    bus = 1160
    for yy in rows:
        f.line([(1120, yy), (bus, yy)])
        f.dot(bus, yy)
    # LM741
    o = opamp(f, 1220, 690, W=140, H=160, label='LM741', pins=('2', '3', '6'))
    f.line([(bus, rows[0]), (bus, o['top'][1]), o['top']])
    f.dot(bus, 580)
    f.line([(bus, 580), (1250, 580)])
    res_h(f, 1250, 1390, 580, 'R12 4.5k (Rf)')
    f.line([(1390, 580), (1420, 580), (1420, o['out'][1])])
    f.dot(1420, o['out'][1])
    f.line([o['out'], (1460, o['out'][1])])
    f.text(1466, o['out'][1] - 40, 'DAC OUTPUT', size=20, anchor='middle', fill=RED, weight='bold')
    f.circle(1466, o['out'][1], 6, stroke=RED)
    f.line([o['up'], (o['up'][0], 615)])
    f.text(o['up'][0] + 8, 625, '4', size=18, fill=GREY)
    f.text(o['up'][0], 606, 'GND', size=18, anchor='middle')
    f.line([o['down'], (o['down'][0], 770)])
    f.circle(o['down'][0], 776, 6)
    f.text(o['down'][0] + 10, 760, '7 (라벨 없음)' if pin7 is None else '7', size=18, fill=GREY)
    if pin7:
        f.text(o['down'][0], 806, pin7, size=20, anchor='middle', weight='bold', fill=RED)
    f.text(1210, o['out'][1] + 120, 'U4', size=18, anchor='middle', fill=GREY)
    # 분배기
    dx = 1000
    f.text(dx, 600, '+15V', size=20, anchor='middle', weight='bold', fill=RED)
    f.line([(dx, 608), (dx, 615)])
    res_v(f, dx, 615, 680, 'R10 1k', dx=-16, anchor='end')
    res_v(f, dx, 680, 760, 'R9 330', dx=-16, anchor='end')
    f.path(f'M{dx+40},{o["bot"][1]} l-22,0', fill='none')
    f.path(f'M{dx+18},{o["bot"][1]-7} l-10,7 l10,7 z', fill=INK)
    f.line([(dx + 40, o['bot'][1]), o['bot']])
    res_v(f, dx, 760, 810, None)
    f.text(dx - 16, 800, 'R11 1k', size=18, anchor='end')
    gnd(f, dx, 810)
    return f


def note_dac():
    f = NoteFig(1490, 978, '7490과 LM741로 만든 4비트 가중 저항 DAC',
                'QA가 최하위 비트, QD가 최상위 비트다. 가중 저항 네 개와 귀환 저항은 LM741의 반전 입력에 모인다.')
    rows = (216, 324, 432, 540)
    f.rect(170, 167, 146, 444, rx=5)
    f.label(244, 593, '7490 U1', anchor='middle')
    f.line([(60, 216), (170, 216)])
    term(f, 60, 216, 'CLK', 'top', RED, node='clock')
    f.label(154, 195, '14', anchor='end', size=22)
    f.label(192, 225, 'CLKA', size=22)
    f.label(192, 278, 'CLKB', size=22)
    f.label(154, 251, '1', anchor='end', size=22, node='qa')
    f.line([(360, 216), (360, 124), (108, 124), (108, 269), (170, 269)])
    f.crossing(108, 216)
    f.junction(360, 216, node='qa')
    for name, sub, pin, yy in (('R', '01', 2, 365), ('R', '02', 3, 418),
                                ('R', '91', 6, 471), ('R', '92', 7, 524)):
        f.line([(100, yy), (170, yy)])
        if yy != 365:
            f.junction(100, yy)
        f.label(151, yy - 18, str(pin), anchor='end', size=22)
        f.label(191, yy + 8, name, sub=sub, size=22)
    f.line([(100, 365), (100, 555)])
    gnd(f, 100, 555)

    pullups = (757, 859, 961, 1063)
    f.line([(757, 68), (1063, 68)])
    f.line([(757, 68), (757, 53)])
    f.junction(757, 53, node='pullup', color='red')
    f.label(757, 29, '+5 V', anchor='middle', node='pullup', color='red')
    bus = 1284
    for i, (yy, bit, qa_pin, gate_pins, pull, weight) in enumerate(zip(
        rows, 'ABCD', (12, 9, 8, 11), ((1, 2), (3, 4), (5, 6), (9, 8)),
        pullups, ('22.6 kΩ', '10.5 kΩ', '4.5 kΩ', '1.5 kΩ'),
    )):
        node = f'q{bit.lower()}'
        f.label(292, yy + 8, 'Q', sub=bit, anchor='end', size=24, node=node)
        f.label(335, yy - 19, str(qa_pin), anchor='middle', size=21, node=node)
        gates = (f.not_(444, yy - 22), f.not_(602, yy - 22))
        f.line([(316, yy), gates[0]['ins'][0]])
        f.line([gates[0]['out'], gates[1]['ins'][0]])
        f.line([gates[1]['out'], (1110, yy)])
        for gate, label in zip(gates, ('7404', '7405')):
            gx = gate['ins'][0][0]
            f.label(gx - 19, yy - 20, str(gate_pins[0]), anchor='end', size=20)
            f.label(gate['out'][0] + 9, yy - 20, str(gate_pins[1]), size=20)
            f.label(gx + 19, yy + 53, label, size=23, anchor='middle')

        res_v(f, pull, 68, 168)
        if i in (1, 2):
            f.junction(pull, 68, node='pullup', color='red')
        f.label(pull + 25, 110, 'R', sub=str(i + 1), size=21)
        f.label(pull + 25, 142, '1.5 kΩ', size=20)
        f.line([(pull, 168), (pull, yy)])
        f.junction(pull, yy)
        res_h(f, 1110, bus, yy, f'R{i+5}  {weight}')
        f.junction(bus, yy, node='summing', color='red')
        if i in (0, 3):
            f.label(1311, yy + 8, 'LSB' if i == 0 else 'MSB', size=22)

    # The four vertical pull-up leads cross earlier bit rows without joining them.
    for i, pull in enumerate(pullups):
        for yy in rows[:i]:
            f.crossing(pull, yy)

    # Route the summing bus below the bit rows, to the inverting pin and Rf.
    o = opamp(f, 1050, 778, W=152, H=160, label='LM741', pins=('2', '3', '6'))
    f.line([(bus, rows[0]), (bus, 606), (995, 606), (995, o['top'][1]), o['top']])
    f.junction(bus, 606, node='summing', color='red')
    f.label(bus + 24, 646, 'V', sub='−', node='summing', color='red')
    f.line([(bus, 606), (1372, 606)])
    res_v(f, 1372, 606, o['out'][1])
    f.label(1402, 681, 'R', sub='f')
    f.label(1402, 714, '4.5 kΩ', size=22)
    f.line([o['out'], (1436, o['out'][1])])
    f.junction(1372, o['out'][1], node='out')
    f.junction(1436, o['out'][1], node='out')
    f.label(1436, o['out'][1] + 45, 'DAC OUT', anchor='end', node='out')
    supply = o['up'][0]
    f.line([o['up'], (supply, 681)])
    f.label(supply + 33, 704, '4', size=22)
    for y, span in ((681, 15), (674, 9), (667, 3)):
        f.line([(supply - span, y), (supply + span, y)])
    f.line([o['down'], (supply, 895)])
    f.junction(supply, 895)
    f.label(supply + 23, 901, '7', size=22)

    # A 330Ω potentiometer sets the reference between the two 1kΩ resistors.
    x = 802
    term(f, x, 622, '+15 V', 'top', RED)
    res_v(f, x, 622, 742, 'R10  1 kΩ', anchor='end')
    res_v(f, x, 742, 894, 'R9  330 Ω', anchor='end')
    res_v(f, x, 894, 930, 'R11  1 kΩ', anchor='end')
    gnd(f, x, 930)
    y = o['bot'][1]
    f.path(f'M{x},{y:g} l26,-7 v14 z', fill=INK)
    f.line([(x + 26, y), o['bot']])
    f.label(x + 77, y - 35, 'V', sub='ref', node='reference')
    return f


def stair(rf_compare=False):
    if rf_compare:
        f = Fig(1100, 420, 'Rf 4.5k와 2.7k의 계단 높이 비교', '왼쪽 Rf 4.5kΩ, 오른쪽 Rf 2.7kΩ: 한 단의 높이가 0.6배')
        for k, (x0, h, lab) in enumerate([(70, 26, 'Rf = 4.5kΩ: 한 단 h'), (600, 26 * 0.6, 'Rf = 2.7kΩ: 한 단 0.6h')]):
            f.line([(x0, 50), (x0, 330), (x0 + 440, 330)], color=GREY, width=2)
            pts = []
            for n in range(10):
                yy = 70 + n * h
                pts += [(x0 + 20 + n * 40, yy), (x0 + 60 + n * 40, yy)]
            f.line(pts, color=BLUE, width=4)
            for n in range(9):
                f.line([(x0 + 60 + n * 40, 70 + n * h), (x0 + 60 + n * 40, 70 + (n + 1) * h)], color=BLUE, width=2, dash='4 4')
            f.text(x0 + 220, 380, lab, size=22, anchor='middle', weight='bold')
            f.text(x0 + 220, 410, '카운트 0 → 9', size=18, anchor='middle', fill=GREY)
        return f
    f = Fig(1000, 400, '내림차순 계단 파형', '카운트 0~9 동안 한 단씩 내려가고 9 다음 0에서 맨 위로')
    x0, y0, h, w = 80, 70, 24, 40
    f.line([(x0, 40), (x0, 330), (x0 + 870, 330)], color=GREY, width=2)
    f.text(x0 - 10, 40, '출력', size=20, anchor='end', fill=GREY)
    f.text(x0 + 870, 360, '시간 →', size=20, anchor='end', fill=GREY)
    pts = []
    for per in range(2):
        for n in range(10):
            xx = x0 + 10 + per * 400 + n * w
            yy = y0 + n * h
            pts += [(xx, yy), (xx + w, yy)]
    f.line(pts, color=BLUE, width=4)
    for n in range(10):
        f.text(x0 + 30 + n * w, y0 + n * h - 10, str(n), size=18, anchor='middle', fill=INK)
    f.text(x0 + 410, y0 + 9 * h + 40, '9 → 0: 맨 위로', size=20, anchor='middle', fill=RED, weight='bold')
    return f


def comparator(*, note=False):
    f = (NoteFig if note else Fig)(900, 420, '실험 2 비교기 (교안 p22를 다시 그림)', 'DAC OUTPUT → 2번(−), R13 가운데 단자 → 3번(+), 7번 +15V, 4번 GND')
    o = opamp(f, 470, 220, W=150, H=150, label='LM741 (U5)', pins=('2', '3', '6'))
    if note:
        term(f, 105, o['top'][1], 'DAC OUT', 'top', RED, node='in')
        f.line([(105, o['top'][1]), o['top']])
    else:
        f.circle(90, o['top'][1], 6, stroke=RED)
        f.text(90, o['top'][1] - 16, 'DAC OUTPUT', size=20, anchor='start', fill=RED, weight='bold')
        f.line([(96, o['top'][1]), o['top']])
    x = 230
    if note:
        term(f, x, 211, '+15 V', 'left', RED)
        res_v(f, x, 211, 362, 'R13  330 Ω', anchor='end')
        gnd(f, x, 362)
        f.path(f'M{x},{o["bot"][1]} l26,-7 v14 z', fill=INK)
        f.line([(x + 26, o['bot'][1]), o['bot']])
        f.label(310, o['bot'][1] - 35, 'V', sub='ref')
    else:
        f.text(x - 12, 212, '+15V', size=20, anchor='end', weight='bold', fill=RED)
        f.circle(x, 205, 5, stroke=RED)
        res_v(f, x, 210, 320, 'R13\n330Ω', dx=-16, anchor='end')
        gnd(f, x, 320)
        f.path(f'M{x+16},{o["bot"][1]} l12,-7 l0,14 z', fill=INK)
        f.line([(x + 28, o['bot'][1]), o['bot']])
    f.line([o['up'], (o['up'][0], 90)])
    if note:
        f.line([o['down'], (o['down'][0], 330)])
        x_ground = o['up'][0]
        for y, span in ((90, 15), (83, 9), (76, 3)):
            f.line([(x_ground - span, y), (x_ground + span, y)])
        f.label(x_ground + 21, 124, '4', size=22)
        f.label(x_ground + 21, 312, '7', size=22)
        f.junction(x_ground, 330, node='supply', color='red')
        f.label(x_ground, 369, '+15 V', anchor='middle', node='supply', color='red')
    else:
        f.text(o['up'][0] + 8, 120, '4', size=18, fill=GREY)
        f.text(o['up'][0], 80, '0 (GND)', size=18, anchor='middle')
        f.line([o['down'], (o['down'][0], 330)])
        f.text(o['down'][0] + 8, 310, '7', size=18, fill=GREY)
        f.text(o['down'][0], 356, '+15V', size=20, anchor='middle', weight='bold', fill=RED)
    f.line([o['out'], (780, o['out'][1])])
    if note:
        term(f, 780, o['out'][1], 'OUT', 'right', node='out')
    else:
        f.text(790, o['out'][1] + 7, 'OUTPUT', size=20, fill=RED, weight='bold')
    return f


def flash():
    f = NoteFig(945, 595, '2비트 Flash ADC',
                '저항 사다리의 세 기준은 비교기의 반전 입력, Vin은 비반전 입력에 연결한다.')
    x, vin_x = 143, 310
    rows = (63, 185, 304, 423, 545)
    term(f, x, rows[0], 'Vref', 'top', RED, node='ref')
    for a, b in zip(rows, rows[1:]):
        res_v(f, x, a, b, 'R', anchor='end')
    gnd(f, x, rows[-1])
    term(f, 245, 524, 'Vin', node='vin')
    f.line([(245, 524), (vin_x, 524), (vin_x, rows[1] - 24)])
    for i, yy in enumerate(rows[1:4]):
        o = opamp(f, 417, yy, W=115, H=96, minus_top=False)
        threshold = f'threshold{i}'
        f.junction(x, yy, node=threshold, color='red')
        f.line([(x, yy), (375, yy), (375, o['bot'][1]), o['bot']])
        f.crossing(vin_x, yy)
        f.label(283, yy - 35, f'{3-i}/4 V', sub='ref', anchor='end',
                node=threshold, color='red')
        f.line([(vin_x, o['top'][1]), o['top']])
        if i:
            f.junction(vin_x, o['top'][1], node='vin')
        f.line([o['out'], (681, yy)])
        f.label(603, yy - 34, 'C', sub=str(3-i), anchor='middle')
    f.rect(681, 150, 126, 307, fill=BLUEBG, rx=5)
    f.label(744, 313, '인코더', anchor='middle')
    for yy, bit in ((250, '1'), (361, '0')):
        f.line([(807, yy), (868, yy)])
        f.junction(868, yy, node=f'b{bit}')
        f.label(892, yy + 8, 'B', sub=bit, node=f'b{bit}')
    return f


def draw_note_schematics(output_dir: Path) -> tuple[Path, ...]:
    return write_note_schematics(output_dir, {
        'opamp-inv': opamp_inv(), 'summing': summing(note=True), 'network': network(note=True),
        'oc': oc(), 'dac-block': note_dac(), 'comparator': comparator(note=True), 'flash': flash(),
    })


def counter_given(title='7490을 0~9 카운터로 연결한 회로'):
    f = Fig(860, 560, title, '7490: clk→14, 12→1, 2·3·6·7→GND, 5 VCC, 10 GND, QA~QD 측정점')
    bx0, bx1 = 300, 500
    f.rect(bx0, 90, bx1 - bx0, 340, fill='#fff', rx=4)
    f.text(400, 470, '7490', size=22, anchor='middle', fill=GREY)
    f.text(400, 530, '전원: 5번 +5V, 10번 GND', size=20, anchor='middle', fill=GREY)
    lp = [(130, '14', 'CLKA'), (180, '1', 'CLKB'), (250, '2', 'R01'), (290, '3', 'R02'), (330, '6', 'R91'), (370, '7', 'R92')]
    for yy, num, name in lp:
        f.line([(bx0 - 40, yy), (bx0, yy)])
        f.text(bx0 + 8, yy + 7, name, size=20)
        f.text(bx0 - 6, yy - 6, num, size=18, anchor='end', fill=GREY)
    term(f, 120, 130, 'CLK', 'left', color=RED)
    f.line([(126, 130), (bx0 - 40, 130)])
    f.line([(bx0 - 40, 250), (200, 250), (200, 410)])
    for yy in (290, 330, 370):
        f.line([(bx0 - 40, yy), (200, yy)])
        f.dot(200, yy)
    gnd(f, 200, 410)
    rp = [(130, '12', 'QA'), (190, '9', 'QB'), (250, '8', 'QC'), (310, '11', 'QD')]
    for yy, num, name in rp:
        f.text(bx1 - 8, yy + 7, name, size=20, anchor='end')
        f.text(bx1 + 6, yy - 8, num, size=18, fill=GREY)
        f.line([(bx1, yy), (680, yy)])
        term(f, 686, yy, name, 'right', color=BLUE)
    f.dot(540, 130)
    f.line([(540, 130), (540, 60), (240, 60), (240, 180), (bx0 - 40, 180)])
    return f


# ---- 등록 -------------------------------------------------------------------
REVIEW_NOTE = '2026-11-16 PNG를 원문·교안 회로와 대조했어요. 7490 핀 번호, 7404·7405 핀 쌍, 풀업·가중 저항 값, LM741 핀(2·3·4·6·7), 분배기 R10·R9·R11, 비교기 입력 방향, 문제 그림의 답 비노출을 확인했어요.'


def build(run, m):
    F = run / 'figures'
    (F / 'questions').mkdir(parents=True, exist_ok=True)
    (F / 'solutions').mkdir(exist_ok=True)
    reg = []

    def register(fid, pid, role, f, ww=120, ids=(), how='원문의 핀·신호·연결을 읽어 직접 다시 그린 벡터 그림이에요. 문제 그림과 풀이 그림을 나눴어요.'):
        sub = 'questions' if role == 'problem' else 'solutions'
        stem = F / sub / fid
        stem.with_suffix('.svg').write_text(f.svg(physical=(ww, ww * f.h / f.w)), encoding='utf8')
        render_png(stem.with_suffix('.svg'), stem.with_suffix('.png'), ww)
        q = next(x for x in m['problems'] if x['id'] == pid)
        reg.append(dict(id=fid, question_id=pid, role=role, svg=f'figures/{sub}/{fid}.svg', png=f'figures/{sub}/{fid}.png', svg_sha256=sha(stem.with_suffix('.svg')), png_sha256=sha(stem.with_suffix('.png')), w_mm=ww, h_mm=ww * f.h / f.w, source_asset_ids=list(ids), source_refs=q['sources'][:1], derivation=how, answer_exposure='none' if role == 'problem' else 'present', review_status='pass', review_notes=REVIEW_NOTE))

    (F / 'stair.svg').write_text(stair().svg(), encoding='utf8')
    draw_note_schematics(F)

    register('summing-given', 'q-summing-amp', 'problem', summing(3, '반전 가산증폭기', node_label=False), 120, ['a-s01-p1-q2'])
    register('network-given', 'q-resistor-network', 'problem', network(True), 160, ['a-s01-p1-q4'])
    register('dac-given', 'q-dac-operation', 'problem', dac('D/A converter 회로', pin7='+15V'), 175, ['a-s04-p1-q3'])
    register('dac-given-2', 'q-counter-7490', 'problem', dac('D/A converter 회로', pin7='+15V'), 175, ['a-s04-p1-q4'])
    register('dac-given-3', 'q-rf-output', 'problem', dac('D/A converter 회로', pin7='+15V'), 175, ['a-s04-p2-q7'])
    register('stair-rf', 'q-rf-output', 'solution', stair(True), 140)
    register('comparator-given', 'q-comparator', 'problem', comparator(), 130, ['a-s04-p2-q8'])

    pid = 'q-qp-e10-board-01'
    register('counter-given', pid, 'problem', counter_given(), 70)
    board(F, reg, pid)
    (F / 'redraw-manifest.json').write_text(json.dumps(dict(schema_version=1, figures=reg), ensure_ascii=False, indent=2))


def board(F, reg, pid):
    from render_breadboard import BreadboardRenderer, _input_jumper
    from scripts.lab.review_pack.breadboard_template import template_png
    b = BreadboardRenderer(board='v1')
    c = b.cols['left']
    y = b.r_y
    b.draw_chip('7490', 10)
    b.connect_jacks()
    b.bridge_rails(c['vcc'], c['mid_vcc'], 35, kind='vcc')
    b.bridge_rails(c['gnd'], c['mid_gnd'], 37, kind='gnd')
    b.connect_power(10)
    b.instrument(c['i'], 10, 'CLK', '7490 CLKA input from generator')
    # R01·R02·R91·R92 (2·3·6·7 → 행 11·12·15·16) 을 바깥 GND 레일로
    for pin, row in ((2, 11), (3, 12), (6, 15), (7, 16)):
        r = b.free_rail_row(row, c['gnd'])
        b.step_wire([(c['c'], y(row)), (c['gnd'], y(r))], 'gnd', f'7490 pin {pin} -> GND 레일')
    b.mark_unused_outputs([4, 13], 10, chip='7490')
    # QA(12번, 행12 f쪽) → CLKB(1번, 행10 a쪽): 칩 위쪽(행 8)으로 돌아가요
    b.step_wire([(c['j'], y(12)), (c['j'], y(8)), (c['a'], y(8)), (c['a'], y(10))], 'sig', 'QA pin12 to CLKB pin1')
    for name, row in (('QA', 12), ('QD', 13), ('QB', 15), ('QC', 16)):
        b.instrument(c['h'], row, name, f'7490 {name} output')
    b.verify()
    nets = []
    for n in b.nets():
        pins = {int(t.rsplit(' ', 1)[1]) for t in n['labels'] if ' pin ' in t and t.rsplit(' ', 1)[1].isdigit()}
        if pins:
            nets.append(pins)
    print('board nets', nets)
    assert any({12, 1} <= s for s in nets), nets
    assert any({10, 2, 3, 6, 7} <= s for s in nets), nets
    assert any(5 in s for s in nets) and not any({5, 10} <= s for s in nets), nets
    png, w, h = template_png()
    head = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}"><title>v1 PDF 7490 BCD counter board</title>'
    bg = f'<image x="0" y="0" width="{w}" height="{h}" href="data:image/png;base64,{base64.b64encode(png).decode()}"/>'
    # 실험08 팩에서 잰 v1 배포 PDF 열 중심(엔진 x → PDF x)과 행 대응이에요(실험09와 같아요).
    xs = [(174, 394), (190, 433), (239, 563), (256, 606), (272, 649), (288, 692), (305, 734), (354, 862), (370, 904), (386, 948), (403, 990), (419, 1033), (468, 1161), (484, 1201)]

    def mx(x):
        for (a, u), (z, v) in zip(xs, xs[1:]):
            if a <= x <= z:
                return u + (x - a) * (v - u) / (z - a)
        a, u = xs[0] if x < 174 else xs[-1]
        return u + (x - a) * 2.606

    def my(yv):
        return 711.8 + (yv - 272) * (3352 - 711.8) / (62 * 16.345)

    parts = []
    l, r = mx(312), mx(347)
    t, bot = my(y(10) - 10), my(y(16) + 10)
    parts.append(f'<rect x="{l}" y="{t}" width="{r-l}" height="{bot-t}" fill="#e5e7eb" stroke="#111" stroke-width="6"/><path d="M{(l+r)/2-20},{t} a20,20 0 0 0 40,0" fill="none" stroke="#111" stroke-width="6"/>')
    for pin in range(1, 15):
        row = 10 + pin - 1 if pin <= 7 else 10 + 14 - pin
        xx = mx(305 if pin <= 7 else 354)
        yy = my(y(row))
        edge = l if pin <= 7 else r
        parts.append(f'<path d="M{xx},{yy} H{edge}" stroke="#111" stroke-width="7"/><text x="{xx-45 if pin<=7 else xx+10}" y="{yy-8}" font-size="30">{pin}</text>')
    parts.append(f'<text x="{(l+r)/2}" y="{(t+bot)/2}" font-size="34" text-anchor="middle" transform="rotate(-90 {(l+r)/2} {(t+bot)/2})">7490</text>')
    mapped = []
    for k, pts, desc in b._segments:
        out = [(1083 if b._jack_at(x, yv) == 'red' else 1936, 400) if b._jack_at(x, yv) else (mx(x), my(yv)) for x, yv in pts]
        coords = ' '.join(f'{x:.1f},{yv:.1f}' for x, yv in out)
        color = {'vcc': '#dc2626', 'gnd': '#1665ca', 'sig': '#16814e', 'mid': '#b06a00'}[k]
        parts.append(f'<polyline points="{coords}" fill="none" stroke="white" stroke-width="13"/><polyline points="{coords}" fill="none" stroke="{color}" stroke-width="7"/>')
        for xx, yy in [out[0], out[-1]]:
            parts.append(f'<circle cx="{xx}" cy="{yy}" r="8" fill="{color}"/>')
        mapped.append(dict(kind=k, description=desc, pdf_points=out))
    for name, row, col in (('CLK ← 발생기', 10, 'i'), ('QA', 12, 'h'), ('QD', 13, 'h'), ('QB', 15, 'h'), ('QC', 16, 'h')):
        cx, cy = mx(c[col]), my(y(row))
        parts.append(f'<circle cx="{cx}" cy="{cy}" r="13" fill="none" stroke="#7c3aed" stroke-width="6"/>')
        parts.append(f'<text x="{mx(419)+30}" y="{cy-8}" font-size="30" fill="#7c3aed" font-weight="bold">{name}</text>')
    for suffix, role, body in (('blank', 'problem', ''), ('complete', 'solution', ''.join(parts))):
        sub = 'questions' if role == 'problem' else 'solutions'
        stem = F / sub / ('counter-' + suffix)
        stem.with_suffix('.svg').write_text(head + bg + body + '</svg>', encoding='utf8')
        if suffix == 'blank':
            stem.with_suffix('.png').write_bytes(png)
        else:
            render_png(stem.with_suffix('.svg'), stem.with_suffix('.png'), 100)
        reg.append(dict(id='counter-' + suffix, question_id=pid, role=role, svg=f'figures/{sub}/counter-{suffix}.svg', png=f'figures/{sub}/counter-{suffix}.png', svg_sha256=sha(stem.with_suffix('.svg')), png_sha256=sha(stem.with_suffix('.png')), w_mm=100, h_mm=100 * h / w, source_asset_ids=[], source_refs=[dict(source_id='s-board', pdf_page=1, printed_page=None)], derivation='v1 배포 강의노트/공지사항/Breadboard.pdf sha256=' + sha(REPO / '강의노트/공지사항/Breadboard.pdf') + ' 300dpi 전체 페이지. PDF 열 중심 394,433,563,606,649,692,734,862,904,948,990,1033,1161,1201; 행1=711.8 행63=3352(실험08 팩에서 잰 값). 엔진 JPG 좌표를 개별 선형 대응. verify 와 넷 대조.', answer_exposure='none' if role == 'problem' else 'present', review_status='pass', review_notes='2026-11-16 확대 렌더로 배선 끝점이 홀에 놓이고 5번 +5V, 10번 GND, 2·3·6·7번 GND, 12→1 연결, 14번 CLK와 QA~QD 측정점 표시(보라 원)인지 확인했어요. CLK는 발생기 신호라 레일에 잇지 않았어요.'))
    (F / 'quiz-board-mapping.json').write_text(json.dumps(dict(columns=xs, y_first=711.8, y_last=3352, segments=mapped, nets=[sorted(n) for n in nets]), ensure_ascii=False, indent=2))
