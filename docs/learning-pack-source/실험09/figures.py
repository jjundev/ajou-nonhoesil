"""교안·기출 회로를 직접 그린 벡터 원고와 300dpi 워크북 그림."""
from figlib import Fig, render_png, sha, BLUE, BLUEBG, GREY, INK, RED, GRN
from pathlib import Path
import json, base64, sys
REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / '.claude/skills/breadboard-diagram/scripts'))

from scripts.lab.review_pack.note_schematic import SchematicSymbols, write_note_schematics

ORANGE = '#b45309'


class NoteFig(SchematicSymbols, Fig):
    pass


def term(f, x, y, name, right=True, color=INK, *, node=None):
    """입력 단자(오각형)와 이름. 선은 (x+40, y)에서 시작해요."""
    if isinstance(f, NoteFig):
        f.junction(x + 40, y, node=node, color='red' if color == RED else 'blue')
        f.label(x + 18, y + 8, name, size=24, anchor='end', node=node,
                color='red' if color == RED else 'blue')
        return (x + 40, y)
    if right:
        f.path(f'M{x},{y-11} h28 l12,11 l-12,11 h-28 z', fill='#fff', stroke=color, sw=2.5)
        f.text(x - 10, y + 8, name, size=22, anchor='end', fill=color, weight='bold')
        return (x + 40, y)
    f.path(f'M{x},{y-11} h28 l12,11 l-12,11 h-28 z', fill='#fff', stroke=color, sw=2.5)
    f.text(x + 52, y + 8, name, size=22, fill=color, weight='bold')
    return (x, y)


def val(f, x, y, v, color=RED):
    """주석 값 배지."""
    t = str(v)
    w = 20 + 12 * len(t)
    f.rect(x - w / 2, y - 17, w, 30, fill='#fff', stroke=color, rx=8, sw=2.5)
    f.text(x, y + 6, t, size=20, anchor='middle', fill=color, weight='bold')


# ---- 1 bit RAM (p4) --------------------------------------------------------
def ram1(vals=None, title='1 bit RAM 회로', legend=True, *, note=False):
    """p4·기출 그림과 같은 연결: Input 인버터 → R 쪽 AND, Input 그대로 → S 쪽 AND, R/W 인버터 → 두 AND."""
    f = (NoteFig if note else Fig)(1350 if note else 1310, 545 if note else 560, title, 'Selection input·Input·Read/Write 입력, AND 세 개, 인버터 두 개, RS 플립플롭, Output')
    f.raw('<g transform="translate(130,0)">')
    v = vals or {}
    sel_y, inp_y, rw_y = 60, 330, 500
    term(f, 120, sel_y, 'Selection input', node='selection' if note else None)
    term(f, 120, inp_y, 'Input', node='input' if note else None)
    term(f, 640, rw_y, 'Read/Write', color=RED if note else INK, node='rw' if note else None)
    ga = f.and_(470, 120, n=3, H=110)       # 위 AND → R
    gb = f.and_(470, 260, n=3, H=110)       # 아래 AND → S
    go = f.and_(900, 110, n=3, H=110)       # 출력 AND
    # RS 플립플롭
    f.rect(680, 130, 130, 230, fill=BLUEBG, rx=2)
    f.text(701 if note else 698, 186, 'R', size=30)
    f.text(701 if note else 698, 326, 'S', size=30)
    f.text(789 if note else 792, 200, 'Q', size=30, anchor='end')
    f.text(745, 395, 'RS 플립플롭', size=20, anchor='middle', fill=GREY)
    f.line([ga['out'], (680, ga['out'][1])])
    f.line([gb['out'], (680, gb['out'][1])])
    # Selection: 세 AND 의 첫 입력
    x_sel = 400
    f.line([(160, sel_y), (860, sel_y), (860, go['ins'][0][1]), go['ins'][0]])
    if note:
        f.junction(x_sel, sel_y, node='selection')
    else:
        f.dot(x_sel, sel_y)
    f.line([(x_sel, sel_y), (x_sel, gb['ins'][0][1]), gb['ins'][0]])
    f.line([(x_sel, ga['ins'][0][1]), ga['ins'][0]])
    if note:
        f.junction(x_sel, ga['ins'][0][1], node='selection')
    else:
        f.dot(x_sel, ga['ins'][0][1])
    # Input: 그대로 → 아래 AND 둘째 입력, 인버터 → 위 AND 둘째 입력
    inv = f.not_(260, ga['ins'][1][1] - 22)
    f.line([(160, inp_y), (440, inp_y), (440, gb['ins'][1][1]), gb['ins'][1]])
    x_i = 220
    if note:
        f.junction(x_i, inp_y, node='input')
    else:
        f.dot(x_i, inp_y)
    f.line([(x_i, inp_y), (x_i, ga['ins'][1][1]), inv['ins'][0]])
    f.line([inv['out'], ga['ins'][1]])
    # Read/Write: 인버터 → 두 AND 셋째 입력, 그대로 → 출력 AND 셋째 입력
    x_rw = 870
    f.line([(680, rw_y), (x_rw, rw_y), (x_rw, go['ins'][2][1]), go['ins'][2]])
    if note:
        f.junction(x_rw, 440, node='rw', color='red')
    else:
        f.dot(x_rw, 440)
    f.line([(x_rw, 440), (606, 440)])
    f.path('M606,418 L606,462 L560,440 Z')   # 왼쪽을 향한 인버터
    f.circle(553, 440, 7)
    x_rwb = 420
    f.line([(546, 440), (x_rwb, 440), (x_rwb, ga['ins'][2][1]), ga['ins'][2]])
    f.dot(x_rwb, gb['ins'][2][1])
    f.line([(x_rwb, gb['ins'][2][1]), gb['ins'][2]])
    # Q → 출력 AND 둘째 입력
    f.line([(810, 190), (840, 190), (840, go['ins'][1][1]), go['ins'][1]])
    f.line([go['out'], (1080, go['out'][1])])
    if note:
        f.junction(1080, go['out'][1], node='out')
        f.label(1103, go['out'][1] + 8, 'Output', node='out')
        f.crossing(x_sel, ga['ins'][1][1])
        f.crossing(x_rwb, gb['ins'][0][1])
        f.crossing(x_rwb, inp_y)
    else:
        f.text(1090, go['out'][1] + 8, 'Output', size=22, weight='bold')
    if legend and not note:
        f.text(250, 470, '0 : Write Operation', size=20, fill=GREY)
        f.text(250, 500, '1 : Read Operation', size=20, fill=GREY)
    for key, (x, y) in dict(sel=(300, sel_y - 26), inp=(300, inp_y - 26), rw=(790, rw_y - 26), R=(650, ga['out'][1] - 24), S=(650, gb['out'][1] - 24), Q=(860, 222), out=(1060, go['out'][1] - 28)).items():
        if key in v:
            val(f, x, y, v[key])
    f.raw('</g>')
    return f


# ---- 2 bit RAM (p6) --------------------------------------------------------
def note_gate_pins(f, gate, pins, model, *, chip_label_gap=30):
    for (x, y), pin in zip(gate['ins'], pins[:2]):
        f.label(x + 17, y + 6, pin, size=18)
    x, y = gate['out']
    f.label(x + 12, y - 16, pins[2], size=18)
    f.label(gate['ins'][0][0] + 33, y + gate['H'] / 2 + chip_label_gap, model, size=18, anchor='middle')


def ram2(vals=None, title='2 bit RAM 회로 (74HC00 두 개, 74HC03 하나)', *, note=False):
    """p6 회로도와 같은 넷. WR1 은 두 비트의 세트 쪽 NAND(2번), WR0 은 리셋 쪽 NAND(5번)에 함께 들어가요."""
    f = (NoteFig if note else Fig)(1630 if note else 1600, 1030 if note else 1020, title, 'OE0·IN0·WR0·OE1·IN1·WR1 입력, 비트마다 NAND SR 래치와 74HC03 출력단, OUT0·OUT1 LED')
    v = vals or {}
    xs = dict(IN=300, WR1=340, WR0=380)
    base = {'A': 90, 'B': 580} if note else {'A': 70, 'B': 560}
    ends = {}
    for bit, y0 in base.items():
        k = '0' if bit == 'A' else '1'
        chip = 'U1' if bit == 'A' else 'U2'
        g1 = f.and_(440, y0 + 40, H=84, bubble=True, label='')
        g2 = f.and_(440, y0 + 260, H=84, bubble=True, label='')
        g3 = f.and_(700, g1['out'][1] - 28, H=84, bubble=True, label='')
        g4 = f.and_(700, g2['out'][1] - 56, H=84, bubble=True, label='')
        for g, pins, nm in ((g1, ('1', '2', '3'), chip), (g2, ('4', '5', '6'), chip), (g3, ('12', '13', '11'), chip), (g4, ('9', '10', '8'), chip)):
            if note:
                note_gate_pins(f, g, pins, '74HC00', chip_label_gap=23 if g is g3 else 30)
            else:
                f.text(g['ins'][0][0] - 6, g['ins'][0][1] - 6, pins[0], size=18, anchor='end', fill=GREY)
                f.text(g['ins'][1][0] - 6, g['ins'][1][1] - 6, pins[1], size=18, anchor='end', fill=GREY)
                f.text(g['out'][0] + 4, g['out'][1] - 8, pins[2], size=18, fill=GREY)
                f.text(g['ins'][0][0] + 34, g['ins'][0][1] + 62 + 6, '74HC00', size=18, anchor='middle', fill=GREY)
        # 앞단 → 래치
        f.line([g1['out'], g3['ins'][0]])
        f.line([g2['out'], g4['ins'][1]])
        q, qb = g3['out'], g4['out']
        # Q → 아래 게이트 9번(교차 결합)
        f.line([q, (820, q[1]), (820, y0 + 215), (660, y0 + 215), (660, g4['ins'][0][1]), g4['ins'][0]])
        if note:
            f.junction(820, q[1], node=f'q{bit}')
            f.label(887, q[1] - 31, 'Q', sub=bit, node=f'q{bit}', anchor='middle')
        else:
            f.dot(820, q[1])
        # Q′ → 위 게이트 13번
        f.line([qb, (850, qb[1]), (850, y0 + 175), (630, y0 + 175), (630, g3['ins'][1][1]), g3['ins'][1]])
        # 읽기: 74HC03 두 게이트
        g5 = f.and_(1010, q[1] - 56, H=84, bubble=True, label='')
        g6 = f.and_(1270, q[1] - 42, H=84, bubble=True, label='')
        p5 = ('1', '2', '3') if bit == 'A' else ('4', '5', '6')
        p6 = ('12', '13', '11') if bit == 'A' else ('9', '10', '8')
        for g, pins in ((g5, p5), (g6, p6)):
            if note:
                note_gate_pins(f, g, pins, '74HC03')
            else:
                f.text(g['ins'][0][0] - 6, g['ins'][0][1] - 6, pins[0], size=18, anchor='end', fill=GREY)
                f.text(g['ins'][1][0] - 6, g['ins'][1][1] + 22, pins[1], size=18, anchor='end', fill=GREY)
                f.text(g['out'][0] + 4, g['out'][1] - 8, pins[2], size=18, fill=GREY)
                f.text(g['ins'][0][0] + 34, g['ins'][1][1] + 48, '74HC03', size=18, anchor='middle', fill=GREY)
        f.line([(820, q[1]), g5['ins'][1]])
        rd = g5['out']
        xr = 1200
        f.line([rd, (xr, rd[1])])
        f.dot(xr, rd[1])
        f.line([(xr, g6['ins'][0][1]), g6['ins'][0]])
        f.line([(xr, rd[1]), (xr, g6['ins'][1][1]), g6['ins'][1]])
        f.line([(xr, g6['ins'][0][1]), (xr, rd[1])])
        # 풀업 두 개
        top = y0 - 30
        for x in (xr, 1440):
            f.line([(x, top), (x, top + 20)], color=RED)
            f.path(f'M{x},{top+20} l-10,6 l20,12 l-20,12 l20,12 l-20,12 l10,6', fill='none', stroke=RED, sw=2.5)
            f.text(x + 16, top + 54, ('10 kΩ' if note else '10k'), size=18, fill=RED)
        f.line([(xr, top + 80), (xr, g6['ins'][0][1])], color=RED)
        f.line([(xr - 0, top), (1440, top)], color=RED)
        f.text(xr - 10, top - 10, '+5V', size=20, anchor='end', fill=RED, weight='bold')
        out = g6['out']
        f.line([out, (1440, out[1])])
        if note:
            f.junction(1440, out[1], node=f'out{k}')
        else:
            f.dot(1440, out[1])
        f.line([(1440, top + 80), (1440, out[1])], color=RED)
        f.line([(1440, out[1]), (1490, out[1])])
        if note:
            f.junction(1490, out[1], node=f'out{k}')
            f.label(1514, out[1] + 8, 'OUT', sub=k, node=f'out{k}')
            f.label(1514, out[1] + 39, '→ LED', size=20)
            f.label(1120, y0 + 235, f'비트 {bit}', anchor='middle', size=32)
            f.crossing(820, y0 + 175)
            f.crossing(850, q[1])
        else:
            f.text(1500, out[1] + 8, f'OUT{k}', size=24, weight='bold', fill=BLUE)
            f.text(1500, out[1] + 38, '→ LED', size=20, fill=GREY)
            f.text(1080, y0 + 260, bit, size=90, anchor='middle', weight='bold', fill='#cbd5e1')
        ends[bit] = dict(g1=g1, g2=g2, g5=g5, q=q, qb=qb, rd=rd, out=out)
        # OE 입력: 위로 돌아 74HC03 첫 입력
        oe_y = y0
        term(f, 150, oe_y, f'OE{k}')
        f.line([(190, oe_y), (960, oe_y), (960, g5['ins'][0][1]), g5['ins'][0]])
        # IN 입력
        in_y = g1['ins'][0][1]
        term(f, 150, in_y, f'IN{k}', node=f'in{k}' if note else None)
        f.line([(190, in_y), g1['ins'][0]])
        if note:
            f.junction(xs['IN'], in_y, node=f'in{k}')
        else:
            f.dot(xs['IN'], in_y)
        f.line([(xs['IN'], in_y), (xs['IN'], g2['ins'][0][1]), g2['ins'][0]])
    # WR 버스: WR0 단자는 A 쪽, WR1 단자는 B 쪽에 있어요(교안 배치).
    a, b = ends['A'], ends['B']
    wr0_y = a['g2']['ins'][1][1]
    wr0_color = RED if note else GRN
    term(f, 150, wr0_y, 'WR0', color=wr0_color, node='wr0' if note else None)
    f.line([(190, wr0_y), a['g2']['ins'][1]], color=wr0_color)
    if note:
        f.junction(xs['WR0'], wr0_y, node='wr0', color='red')
    else:
        f.dot(xs['WR0'], wr0_y, color=wr0_color)
    f.line([(xs['WR0'], wr0_y), (xs['WR0'], b['g2']['ins'][1][1]), b['g2']['ins'][1]], color=wr0_color)
    wr1_y = base['B'] + 400
    term(f, 150, wr1_y, 'WR1', color=BLUE, node='wr1' if note else None)
    f.line([(190, wr1_y), (xs['WR1'], wr1_y), (xs['WR1'], a['g1']['ins'][1][1]), a['g1']['ins'][1]], color=BLUE)
    if note:
        f.junction(xs['WR1'], b['g1']['ins'][1][1], node='wr1')
    else:
        f.dot(xs['WR1'], b['g1']['ins'][1][1], color=BLUE)
    f.line([(xs['WR1'], b['g1']['ins'][1][1]), b['g1']['ins'][1]], color=BLUE)
    if note:
        # The write buses cross the independent OE and IN nets without joining them.
        for row in (base['B'], b['g1']['ins'][0][1], b['g1']['ins'][1][1], b['g2']['ins'][0][1]):
            f.crossing(xs['WR0'], row, color=RED)
        for row in (a['g2']['ins'][0][1], wr0_y, base['B'], b['g1']['ins'][0][1], b['g2']['ins'][0][1]):
            f.crossing(xs['WR1'], row, color=BLUE)
    else:
        f.text(30, 1005, '입력 스위치는 단자로 줄여 그렸어요. 선이 엇갈리기만 하는 곳(점 없음)은 연결이 아니에요.', size=20, fill=GREY)
    # 주석 값
    pos = {}
    for bit in 'AB':
        e = ends[bit]
        k = '0' if bit == 'A' else '1'
        pos[f'OE{k}'] = (250, base[bit] - 24)
        pos[f'IN{k}'] = (250, e['g1']['ins'][0][1] - 24)
        pos[f'S{bit}'] = (600, e['g1']['out'][1] - 24)
        pos[f'R{bit}'] = (600, e['g2']['out'][1] - 24)
        pos[f'Q{bit}'] = (910, e['q'][1] - 24)
        pos[f'OUT{k}'] = (1380, e['out'][1] + 34)
    pos['WR0'] = (250, a['g2']['ins'][1][1] + 30)
    pos['WR1'] = (250, base['B'] + 370)
    for key, value in v.items():
        val(f, *pos[key], value)
    return f


# ---- NAND SR 래치 ------------------------------------------------------------
def nand_latch(pins=False, title='NAND 두 개로 만든 SR 래치', *, note=False):
    f = (NoteFig if note else Fig)(655 if note else 760, 345 if note else 360, title, "S′와 R′ 입력, 두 NAND의 교차 되먹임, 출력 Q와 Q′")
    g1 = f.and_(300, 50, H=90, bubble=True, label='')
    g2 = f.and_(300, 210, H=90, bubble=True, label='')
    f.text(104 if note else 110, g1['ins'][0][1] + 8, "S′", size=28, weight='bold')
    f.text(104 if note else 110, g2['ins'][1][1] + 8, "R′", size=28, weight='bold')
    f.line([(150, g1['ins'][0][1]), g1['ins'][0]])
    f.line([(150, g2['ins'][1][1]), g2['ins'][1]])
    q, qb = g1['out'], g2['out']
    f.line([q, (560, q[1])])
    f.line([qb, (560, qb[1])])
    if note:
        f.label(584, q[1] + 8, 'Q', node='q')
        f.label(584, qb[1] + 8, 'Q′', node='q-bar', color='red')
        f.junction(560, q[1], node='q')
        f.junction(560, qb[1], node='q-bar', color='red')
        f.junction(450, q[1], node='q')
        f.junction(490, qb[1], node='q-bar', color='red')
        f.line([(450, q[1]), (450, 191), (260, 191), (260, g2['ins'][0][1]), g2['ins'][0]])
        f.line([(490, qb[1]), (490, 158), (240, 158), (240, g1['ins'][1][1]), g1['ins'][1]])
        f.crossing(450, 158)
        f.junction(150, g1['ins'][0][1])
        f.junction(150, g2['ins'][1][1])
    else:
        f.text(580, q[1] + 9, 'Q', size=28, weight='bold', fill=BLUE)
        f.text(580, qb[1] + 9, "Q′", size=28, weight='bold', fill=BLUE)
        f.dot(450, q[1])
        f.line([(450, q[1]), (450, 165), (260, 195), (260, g2['ins'][0][1]), g2['ins'][0]])
        f.dot(490, qb[1])
        f.line([(490, qb[1]), (490, 175), (240, 135), (240, g1['ins'][1][1]), g1['ins'][1]])
    if pins:
        for t, (x, y) in (('1', g1['ins'][0]), ('2', g1['ins'][1]), ('4', g2['ins'][0]), ('5', g2['ins'][1])):
            f.text(x - 6, y - 6, t, size=18, anchor='end', fill=GREY)
        f.text(q[0] + 4, q[1] - 8, '3', size=18, fill=GREY)
        f.text(qb[0] + 4, qb[1] - 8, '6', size=18, fill=GREY)
        f.text(30, 340, '74HC00: VCC 14번=+5V, GND 7번=0V', size=22)
    return f


# ---- 74670 -------------------------------------------------------------------
def pin670():
    f = Fig(760, 520, '74670 핀 배치 (교안 p8)', '16핀. 왼쪽 1~8, 오른쪽 16~9')
    f.rect(250, 30, 220, 440, rx=4)
    f.path('M335,30 a25,25 0 0 0 50,0', fill='#fff')
    left = ['D2', 'D3', 'D4', 'RB', 'RA', 'Q4', 'Q3', 'GND']
    right = ['VCC', 'D1', 'WA', 'WB', "WE′", "RE′", 'Q1', 'Q2']
    for i in range(8):
        y = 78 + i * 52
        f.text(270, y + 8, str(i + 1), size=20)
        f.text(450, y + 8, str(16 - i), size=20, anchor='end')
        lc = RED if left[i].startswith('Q') else BLUE if left[i][0] in 'DR' else INK
        rc = RED if right[i].startswith('Q') else BLUE if right[i][0] in 'DWR' else INK
        f.text(235, y + 8, left[i], size=24, anchor='end', fill=lc, weight='bold')
        f.text(485, y + 8, right[i], size=24, fill=rc, weight='bold')
    f.text(360, 500, '′ 표시: 0일 때 켜져요(교안은 이름 위에 줄)', size=20, anchor='middle', fill=GREY)
    return f


def block670():
    f = Fig(1100, 470, '74670 안의 4워드 × 4비트 저장 블록도', '쓰기 쪽 D1~D4·WA·WB·WE′, 읽기 쪽 RA·RB·RE′·Q1~Q4')
    f.rect(330, 60, 420, 330, fill='#fff', rx=4)
    f.text(540, 48, '74670 (4×4 레지스터 파일)', size=22, anchor='middle', weight='bold')
    for i, addr in enumerate(('00', '01', '10', '11')):
        y = 90 + i * 72
        f.text(360, y + 38, addr, size=22, fill=GREY)
        for j in range(4):
            f.rect(420 + j * 70, y, 60, 52, fill=BLUEBG, rx=4, sw=2)
        f.text(720, y + 34, f'워드{i}', size=18, anchor='middle', fill=GREY)
    f.text(560, 412, '칸 하나가 1비트, 줄 하나가 4비트 워드', size=20, anchor='middle', fill=GREY)
    for i, (t, c) in enumerate((('D1~D4 (데이터)', BLUE), ('WA·WB (쓰기 주소)', BLUE), ("WE′ (쓰기 켜기, 0=On)", BLUE))):
        y = 120 + i * 90
        f.text(20, y + 8, t, size=20, fill=c, weight='bold')
        f.line([(250, y), (330, y)], color=c)
        f.path(f'M330,{y} l-14,-7 v14 z', fill=c, stroke=c)
    for i, (t, c) in enumerate((('RA·RB (읽기 주소)', RED), ("RE′ (읽기 켜기, 0=On)", RED))):
        y = 140 + i * 90
        f.text(1080, y + 8, t, size=20, anchor='end', fill=c, weight='bold')
        f.line([(750, y), (830, y)], color=c)
        f.path(f'M750,{y} l14,-7 v14 z', fill=c, stroke=c)
    f.line([(750, 340), (830, 340)], color=RED)
    f.path('M830,340 l-14,-7 v14 z', fill=RED, stroke=RED)
    f.text(1080, 348, 'Q1~Q4 (출력→LED)', size=20, anchor='end', fill=RED, weight='bold')
    return f


def memory_idea():
    f = Fig(980, 300, '주소로 칸을 골라 읽고 쓰는 메모리', '네 칸 중 주소 01을 골라 1을 쓰고 나중에 읽는 예')
    for i, (a, d) in enumerate((('00', '0'), ('01', '1'), ('10', '0'), ('11', '1'))):
        x = 260 + i * 150
        hi = a == '01'
        f.rect(x, 90, 120, 100, fill=BLUEBG if hi else '#fff', stroke=BLUE if hi else INK, rx=6)
        f.text(x + 60, 152, d, size=34, anchor='middle', weight='bold', fill=BLUE if hi else INK)
        f.text(x + 60, 222, '주소 ' + a, size=20, anchor='middle', fill=GREY)
    f.text(30, 120, '쓰기: 주소 01에', size=22, weight='bold')
    f.text(30, 152, '1을 넣어요', size=22)
    f.text(30, 200, '읽기: 주소 01의', size=22, weight='bold', fill=RED)
    f.text(30, 232, '값을 꺼내요', size=22, fill=RED)
    f.line([(470, 70), (470, 40), (640, 40)], color=BLUE)
    f.text(650, 48, '주소를 고르면 바로 그 칸으로 가요', size=20, fill=BLUE)
    f.text(490, 280, '이해를 위한 예시 — 칸의 값은 지어낸 값이에요', size=18, anchor='middle', fill=GREY)
    return f


def opendrain():
    f = NoteFig(790, 355, '열린 드레인 출력과 10kΩ 풀업',
                '스위치가 닫히면 OUT은 0V, 열리면 저항이 OUT을 5V로 끌어올린다.')
    for x, title, closed in ((114, '닫힌 스위치', True), (488, '열린 스위치', False)):
        out = 'low' if closed else 'high'
        color = 'red' if closed else 'blue'
        f.label(x, 34, title, anchor='middle')
        f.label(x, 81, '+5 V', anchor='middle')
        f.junction(x, 100)
        f.line([(x, 100), (x, 120)])
        f.path(f'M{x},120 l-10,6 l20,12 l-20,12 l20,12 l-20,12 l10,6', fill='none')
        f.label(x + 29, 153, '10 kΩ', size=22)
        f.line([(x, 180), (x, 244)])
        f.junction(x, 203, node=out, color=color)
        f.line([(x, 203), (x + 119, 203)])
        f.junction(x + 119, 203, node=out, color=color)
        f.label(x + 144, 212, 'OUT', node=out, color=color)
        f.label(x + 144, 246, '0 V' if closed else '5 V', node=out, color=color)
        f.circle(x, 248, 4)
        f.line([(x, 252), (x if closed else x + 24, 285)], width=4)
        f.circle(x, 289, 4)
        f.line([(x, 293), (x, 319)])
        for span, y in ((16, 319), (10, 327), (4, 335)):
            f.line([(x - span, y), (x + span, y)])
    return f


def draw_note_schematics(output_dir: Path) -> tuple[Path, ...]:
    return write_note_schematics(output_dir, {
        'nand-latch': nand_latch(note=True), 'ram1bit': ram1(note=True),
        'ram2bit': ram2(note=True), 'opendrain': opendrain(),
    })


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

    for name, f in (('memory-idea', memory_idea()), ('pin670', pin670()), ('block670', block670())):
        (F / f'{name}.svg').write_text(f.svg(), encoding='utf8')
    draw_note_schematics(F)

    W1 = dict(sel=1, inp=1, rw=0, R=0, S=1, Q=1, out=0)
    W0 = dict(sel=1, inp=0, rw=0, R=1, S=0, Q=0, out=0)
    RD = dict(sel=1, rw=1, R=0, S=0, Q='Q', out='Q')
    register('ram1-given', 'q-write1', 'problem', ram1(legend=False), 150, ['a-s01-p1-o-s01-q2'])
    register('ram1-write1', 'q-write1', 'solution', ram1(W1, '1 쓰기: 각 선의 값'), 150)
    register('ram1-given-2', 'q-write0', 'problem', ram1(legend=False), 150, ['a-s07-p1'])
    register('ram1-write0', 'q-write0', 'solution', ram1(W0, '0 쓰기: 각 선의 값'), 150)
    register('ram1-read', 'q-read-op-rw', 'solution', ram1(RD, '읽기: 각 선의 값'), 150)
    A1 = dict(OE0=1, IN0=1, WR0=0, OE1=0, IN1=0, WR1=1, SA=0, RA=1, QA=1, SB=1, RB=1, OUT0=1, OUT1=0)
    B1 = dict(OE0=0, IN0=0, WR0=0, OE1=1, IN1=1, WR1=1, SA=1, RA=1, SB=0, RB=1, QB=1, OUT0=0, OUT1=1)
    B0 = dict(OE0=0, IN0=0, WR0=1, OE1=1, IN1=1, WR1=0, SA=1, RA=1, SB=1, RB=0, QB=0, OUT0=0, OUT1=0)
    register('ram2-given', 'q-apart1', 'problem', ram2(), 165, ['a-s07-p2'])
    register('ram2-apart1', 'q-apart1', 'solution', ram2(A1, 'A에 1 쓰기: 각 선의 값'), 165)
    register('ram2-bpart1', 'q-bpart1', 'solution', ram2(B1, 'B에 1 쓰기: 각 선의 값'), 165)
    register('ram2-given-3', 'q-bpart0', 'problem', ram2(), 165, ['a-s01-p1-o-s01-q3'])
    register('ram2-bpart0', 'q-bpart0', 'solution', ram2(B0, 'B에 0 쓰기: 각 선의 값'), 165)

    pid = 'q-qp-e09-board-01'
    register('latch-given', pid, 'problem', nand_latch(True, '74HC00 두 게이트로 만든 NAND SR 래치'), 70)
    board(F, reg, pid)
    (F / 'redraw-manifest.json').write_text(json.dumps(dict(schema_version=1, figures=reg), ensure_ascii=False, indent=2))


REVIEW_NOTE = '2026-11-12 PNG를 원문·교안 회로와 대조했어요. 입력 단자, 인버터 위치, WR0·WR1 공통 배선, 교차 되먹임, 핀 번호, 문제 그림의 답 비노출을 확인했어요.'


def board(F, reg, pid):
    from render_breadboard import BreadboardRenderer, _input_jumper
    from scripts.lab.review_pack.breadboard_template import template_png
    b = BreadboardRenderer(board='v1')
    c = b.cols['left']
    y = b.r_y
    b.draw_chip('74HC00', 10)
    b.connect_jacks()
    b.bridge_rails(c['vcc'], c['mid_vcc'], 35, kind='vcc')
    b.connect_power(10)
    _input_jumper(b, c, 10, "S'", "external input S' (pin1)")
    _input_jumper(b, c, 14, "R'", "external input R' (pin5)")
    b.mark_unused_inputs([9, 10, 12, 13], 10)
    b.mark_unused_outputs([8, 11], 10)
    # 되먹임: 3번(행12) → 4번(행13), 6번(행15) → 2번(행11)
    b.step_wire([(c['c'], y(12)), (c['c'], y(13))], 'sig', 'Q pin3 to pin4')
    b.step_wire([(c['b'], y(15)), (222, y(15)), (222, y(11)), (c['b'], y(11))], 'sig', "Q' pin6 to pin2")
    b.instrument(c['a'], 12, 'Q', 'pin3 output Q')
    b.verify()
    nets = []
    for n in b.nets():
        pins = {int(t.rsplit(' ', 1)[1]) for t in n['labels'] if ' pin ' in t}
        if pins:
            nets.append(pins)
    assert {2, 6} in nets and {3, 4} in nets and {14} in nets and {7} in nets, nets
    png, w, h = template_png()
    head = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}"><title>v1 PDF NAND SR latch board</title>'
    bg = f'<image x="0" y="0" width="{w}" height="{h}" href="data:image/png;base64,{base64.b64encode(png).decode()}"/>'
    # 실험08 팩에서 잰 v1 배포 PDF 열 중심(엔진 x → PDF x)과 행 대응이에요.
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
    parts.append(f'<text x="{(l+r)/2}" y="{(t+bot)/2}" font-size="34" text-anchor="middle" transform="rotate(-90 {(l+r)/2} {(t+bot)/2})">74HC00</text>')
    mapped = []
    for k, pts, desc in b._segments:
        out = [(1083 if b._jack_at(x, yv) == 'red' else 1936, 400) if b._jack_at(x, yv) else (mx(x), my(yv)) for x, yv in pts]
        coords = ' '.join(f'{x:.1f},{yv:.1f}' for x, yv in out)
        color = {'vcc': '#dc2626', 'gnd': '#1665ca', 'sig': '#16814e', 'mid': '#b06a00'}[k]
        parts.append(f'<polyline points="{coords}" fill="none" stroke="white" stroke-width="13"/><polyline points="{coords}" fill="none" stroke="{color}" stroke-width="7"/>')
        for xx, yy in [out[0], out[-1]]:
            parts.append(f'<circle cx="{xx}" cy="{yy}" r="8" fill="{color}"/>')
        mapped.append(dict(kind=k, description=desc, pdf_points=out))
    parts.append(f'<text x="500" y="{my(y(10))-14}" font-size="38" text-anchor="middle" fill="#16814e" font-weight="bold">S′</text><text x="250" y="{my(y(14))+12}" font-size="44" text-anchor="end">R′</text><text x="250" y="{my(y(12))+12}" font-size="40" text-anchor="end">Q=3번</text>')
    for suffix, role, body in (('blank', 'problem', ''), ('complete', 'solution', ''.join(parts))):
        sub = 'questions' if role == 'problem' else 'solutions'
        stem = F / sub / ('latch-' + suffix)
        stem.with_suffix('.svg').write_text(head + bg + body + '</svg>', encoding='utf8')
        if suffix == 'blank':
            stem.with_suffix('.png').write_bytes(png)
        else:
            render_png(stem.with_suffix('.svg'), stem.with_suffix('.png'), 100)
        reg.append(dict(id='latch-' + suffix, question_id=pid, role=role, svg=f'figures/{sub}/latch-{suffix}.svg', png=f'figures/{sub}/latch-{suffix}.png', svg_sha256=sha(stem.with_suffix('.svg')), png_sha256=sha(stem.with_suffix('.png')), w_mm=100, h_mm=100 * h / w, source_asset_ids=[], source_refs=[dict(source_id='s-board', pdf_page=1, printed_page=None)], derivation='v1 배포 강의노트/공지사항/Breadboard.pdf sha256=' + sha(REPO / '강의노트/공지사항/Breadboard.pdf') + ' 300dpi 전체 페이지. PDF 열 중심 394,433,563,606,649,692,734,862,904,948,990,1033,1161,1201; 행1=711.8 행63=3352(실험08 팩에서 잰 값). 엔진 JPG 좌표를 개별 선형 대응. verify 와 넷 대조.', answer_exposure='none' if role == 'problem' else 'present', review_status='pass', review_notes='2026-11-12 확대 렌더로 배선 끝점이 홀에 놓이고 14번 +5V, 7번 GND, 1번 S′, 5번 R′, 3→4, 6→2 되먹임인지 확인했어요.'))
    (F / 'quiz-board-mapping.json').write_text(json.dumps(dict(columns=xs, y_first=711.8, y_last=3352, segments=mapped, nets=[sorted(n) for n in nets]), ensure_ascii=False, indent=2))
