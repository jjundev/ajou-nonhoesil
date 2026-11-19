"""교안·기출 회로를 직접 그린 벡터 원고와 300dpi 워크북 그림."""
from figlib import Fig, render_png, sha, BLUE, BLUEBG, GREY, INK, RED
from pathlib import Path
import json, base64, sys
REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / '.claude/skills/breadboard-diagram/scripts'))
from render_breadboard import BreadboardRenderer, _input_jumper
from scripts.lab.review_pack.breadboard_template import template_png
from scripts.lab.review_pack.note_schematic import SchematicSymbols, write_note_schematics


class NoteFig(SchematicSymbols, Fig):
    pass


def wave(f, x0, y, step, vals, h=44, color=INK, width=3):
    """vals 는 반주기(또는 칸)마다의 0/1 값이에요."""
    pts = [(x0, y + h * (1 - vals[0]))]
    for i, v in enumerate(vals):
        yy = y + h * (1 - v)
        pts.append((x0 + i * step, yy))
        pts.append((x0 + (i + 1) * step, yy))
    f.line(pts, color=color, width=width)


def clock_vals(n):
    return [0] + [1, 0] * n


def ripple_states(n):
    a = b = 0
    out = [(a, b)]
    for _ in range(n):
        a2 = 1 - a
        if a == 1:
            b = 1 - b
        a = a2
        out.append((a, b))
    return out


def sync_states(n):
    a = b = 0
    out = [(a, b)]
    for _ in range(n):
        ja, jb = 1 - b, a
        a, b = (1 - a if ja else 0), (1 - b if jb else 0)
        out.append((a, b))
    return out


def timing(title, states, extra=None):
    """Clock·A·B 완성 파형. states[i] 는 i번째 하강 엣지 뒤의 값이에요."""
    n = len(states) - 1
    step = 42
    f = Fig(190 + step * (2 * n + 1), 330 if not extra else 400, title)
    x0 = 130
    rows = [('Clock', 40, clock_vals(n)), ('A', 130, None), ('B', 220, None)]
    for name, y, vals in rows:
        f.text(100, y + 34, name, size=26, anchor='end', weight='bold')
        if vals is None:
            idx = 0 if name == 'A' else 1
            vals = [states[i // 2][idx] for i in range(2 * n + 1)]
            wave(f, x0, y, step, vals, color=BLUE, width=4)
        else:
            wave(f, x0, y, step, vals)
    for i in range(1, n + 1):
        x = x0 + step * 2 * i
        f.line([(x, 30), (x, 285)], color=GREY, width=1.5, dash='6 6')
        f.text(x, 305, f'↓{i}', size=20, anchor='middle', fill=GREY)
    if extra:
        f.text(100, 355, 'AB', size=24, anchor='end', weight='bold')
        for i in range(n + 1):
            x = x0 + step * (2 * i + 1) if i < n else x0 + step * (2 * n + 0.5)
            f.text(x, 360, f'{states[i][0]}{states[i][1]}', size=20, anchor='middle', fill=BLUE)
    return f


def blank_wave(title):
    """원문 답란: A·B 행 시작·끝 막대와 6주기 Clock."""
    step = 56
    f = Fig(150 + step * 13 + 30, 300, title)
    x0 = 120
    for name, y in (('A', 50), ('B', 130)):
        f.text(90, y + 12, name, size=28, anchor='end', weight='bold')
        f.line([(x0, y + 6), (x0 + 36, y + 6)], width=6)
        f.line([(x0 + step * 13 - 36, y + 6), (x0 + step * 13, y + 6)], width=6)
    f.text(90, 248, 'Clock', size=28, anchor='end', weight='bold')
    wave(f, x0, 205, step, clock_vals(6), h=50)
    return f


def jk(f, x, y, pins, name='74HC76'):
    """74HC76 F/F 한 개. pins 는 J, CLK, K, Q, Qbar, PR, CL 번호 묶음이에요."""
    w, h = 170, 170
    f.rect(x, y, w, h, fill='#fff', stroke=BLUE)
    pj, pc, pk, pq, pb, ppr, pcl = pins
    f.text(x + 14, y + 44, 'J', size=24, fill=BLUE)
    f.text(x + 34, y + 94, 'CLK', size=20, fill=BLUE)
    f.text(x + 14, y + 146, 'K', size=24, fill=BLUE)
    f.text(x + w - 16, y + 44, 'Q', size=24, anchor='end', fill=BLUE)
    f.text(x + w - 16, y + 146, "Q'", size=24, anchor='end', fill=BLUE)
    f.text(x + w / 2, y + 30, 'PR', size=18, anchor='middle', fill=BLUE)
    f.text(x + w / 2, y + h - 12, 'CL', size=18, anchor='middle', fill=BLUE)
    f.circle(x - 8, y + 88, 7, stroke=BLUE)
    f.circle(x + w / 2, y - 8, 7, stroke=BLUE)
    f.circle(x + w / 2, y + h + 8, 7, stroke=BLUE)
    f.line([(x, y + 78), (x + 22, y + 88), (x, y + 98)], color=BLUE)
    f.text(x + w - 4, y + h + 32, name, size=18, anchor='middle', fill=BLUE)
    for t, xx, yy, an in ((pj, x - 8, y + 30, 'end'), (pc, x - 20, y + 76, 'end'), (pk, x - 8, y + 134, 'end'), (pq, x + w + 8, y + 30, 'start'), (pb, x + w + 8, y + 134, 'start')):
        f.text(xx, yy, str(t), size=18, anchor=an, fill=GREY)
    f.text(x + w / 2 + 12, y - 16, str(ppr), size=18, fill=GREY)
    f.text(x + w / 2 + 12, y + h + 28, str(pcl), size=18, fill=GREY)
    return dict(j=(x, y + 38), clk=(x - 15, y + 88), k=(x, y + 140), q=(x + w, y + 38), qb=(x + w, y + 140), pr=(x + w / 2, y - 15), cl=(x + w / 2, y + h + 15))


def clockgen(f, x, y):
    f.rect(x, y, 170, 120, rx=4)
    f.text(x + 18, y + 38, 'Clock', size=22)
    f.text(x + 18, y + 70, 'Generator', size=22)
    f.text(x + 18, y + 102, '+5V, 1Hz', size=22)


def schem(sync):
    title = '74HC76 두 개의 동기 카운터 회로' if sync else '74HC76 두 개의 비동기 카운터 회로'
    desc = '두 CLK가 Clock Generator에 공통, J1은 B′, J2는 A, K는 VCC' if sync else '첫 단 CLK는 Clock Generator, 둘째 단 CLK는 A, J·K는 VCC'
    f = Fig(1120, 560, title, desc)
    a = jk(f, 340, 170, (4, 1, 16, 15, 14, 2, 3))
    b = jk(f, 740, 170, (9, 6, 12, 11, 10, 7, 8))
    clockgen(f, 20, 230 if not sync else 390)
    vcc_y, cl_y = 90, 440
    f.text(630, 40, 'VCC', size=22, anchor='middle', fill=RED)
    f.circle(630, 52, 6, stroke=RED)
    f.line([(630, 58), (630, vcc_y)], color=RED)
    f.line([(a['pr'][0], vcc_y), (b['pr'][0], vcc_y)], color=RED)
    f.line([(a['pr'][0], vcc_y), a['pr']], color=RED)
    f.line([(b['pr'][0], vcc_y), b['pr']], color=RED)
    f.dot(630, vcc_y, color=RED)
    # CL 두 개는 아래쪽 VCC 줄이에요.
    f.line([a['cl'], (a['cl'][0], cl_y), (b['cl'][0], cl_y), b['cl']], color=RED)
    f.text(1000, cl_y + 7, 'VCC', size=22, anchor='start', fill=RED)
    f.circle(985, cl_y, 6, stroke=RED)
    f.line([(b['cl'][0], cl_y), (979, cl_y)], color=RED)
    # 출력 이름
    f.text(a['q'][0] + 72, a['q'][1] - 12, 'A', size=26, fill=RED, weight='bold')
    f.text(a['qb'][0] + 72, a['qb'][1] - 12, "A'", size=26, fill=RED, weight='bold')
    f.text(b['q'][0] + 72, b['q'][1] - 12, 'B', size=26, fill=RED, weight='bold')
    f.text(b['qb'][0] + 72, b['qb'][1] - 12, "B'", size=26, fill=RED, weight='bold')
    f.line([a['qb'], (a['qb'][0] + 60, a['qb'][1])])
    f.line([b['q'], (b['q'][0] + 60, b['q'][1])])
    if sync:
        # K 두 개는 VCC 줄, J1 은 B', J2 는 A 에서 와요.
        f.line([a['k'], (a['k'][0] - 60, a['k'][1]), (a['k'][0] - 60, vcc_y), (a['pr'][0], vcc_y)], color=RED)
        f.line([b['k'], (b['k'][0] - 60, b['k'][1]), (b['k'][0] - 60, vcc_y)], color=RED)
        f.dot(b['k'][0] - 60, vcc_y, color=RED)
        f.line([a['q'], (a['q'][0] + 60, a['q'][1]), (b['j'][0], b['j'][1])])
        f.line([b['qb'], (b['qb'][0] + 110, b['qb'][1]), (b['qb'][0] + 110, 130), (a['j'][0] - 30, 130), (a['j'][0] - 30, a['j'][1]), a['j']])
        f.line([(190, 450), (240, 450), (240, a['clk'][1]), a['clk']])
        f.line([(240, 470), (640, 470), (640, b['clk'][1]), b['clk']])
        f.line([(240, 450), (240, 470)])
        f.dot(240, 450)
        f.line([(105, 510), (105, 540)])
        f.line([(85, 540), (125, 540)])
    else:
        # 네 J·K 모두 VCC 줄이에요.
        f.line([a['j'], (a['j'][0] - 60, a['j'][1]), (a['j'][0] - 60, vcc_y), (a['pr'][0], vcc_y)], color=RED)
        f.line([a['k'], (a['k'][0] - 60, a['k'][1]), (a['k'][0] - 60, a['j'][1])], color=RED)
        f.dot(a['j'][0] - 60, a['j'][1], color=RED)
        f.line([b['j'], (b['j'][0] - 40, b['j'][1]), (b['j'][0] - 40, vcc_y)], color=RED)
        f.line([b['k'], (b['k'][0] - 40, b['k'][1]), (b['k'][0] - 40, b['j'][1])], color=RED)
        f.dot(b['j'][0] - 40, b['j'][1], color=RED)
        f.dot(b['j'][0] - 40, vcc_y, color=RED)
        f.line([(190, a['clk'][1]), a['clk']])
        f.line([a['q'], (a['q'][0] + 60, a['q'][1]), (a['q'][0] + 60, b['clk'][1]), b['clk']])
        f.line([b['qb'], (b['qb'][0] + 60, b['qb'][1])])
        f.line([(105, 350), (105, 400)])
        f.line([(85, 400), (125, 400)])
    f.line([(b['q'][0] + 60, b['q'][1]), b['q']])
    return f


def tchain():
    f = Fig(860, 340, 'T 플립플롭 세 단을 이은 블록도', '원문처럼 블록 C 안 출력 라벨도 B, B′로 인쇄했어요')
    xs = [130, 370, 610]
    for x, name, q in zip(xs, 'ABC', ('A', 'B', 'B')):
        f.rect(x, 110, 150, 130, fill=BLUEBG, rx=2)
        f.text(x + 12, 170, 'T', size=26)
        f.text(x + 62, 186, name, size=34)
        f.text(x + 120, 150, q, size=24)
        f.text(x + 120, 214, q + "'", size=24)
    f.text(30, 170, 'CLK', size=28, weight='bold')
    f.line([(95, 162), (130, 162)])
    for x, name in zip(xs, 'ABC'):
        f.line([(x + 150, 140), (x + 180, 140)])
        f.line([(x + 180, 140), (x + 180, 50)])
        f.text(x + 180, 36, name, size=30, anchor='middle', weight='bold')
    for x in xs[:2]:
        f.dot(x + 180, 140)
        f.line([(x + 180, 140), (x + 180, 162), (x + 240, 162)])
    f.text(30, 306, 'Reset', size=28, weight='bold')
    f.line([(115, 298), (685, 298)])
    for x in xs:
        f.line([(x + 75, 240), (x + 75, 298)])
    for x in xs[:2]:
        f.dot(x + 75, 298)
    return f


def pin7447():
    f = Fig(860, 470, 'BCD-to-7-Segment 디코더 핀 배치와 세그먼트 이름')
    f.rect(170, 30, 210, 400, rx=4)
    f.path('M250,30 a25,25 0 0 0 50,0', fill='#fff')
    left = ['B', 'C', 'LT', 'BI/RBO', 'RBI', 'D', 'A', 'GND']
    right = ['VCC', 'f', 'g', 'a', 'b', 'c', 'd', 'e']
    for i in range(8):
        y = 70 + i * 48
        f.text(190, y + 8, str(i + 1), size=20)
        f.text(360, y + 8, str(16 - i), size=20, anchor='end')
        f.text(155, y + 8, left[i], size=24, anchor='end')
        f.text(395, y + 8, right[i], size=24)
    for i, w in ((2, 34), (3, 120), (4, 52)):
        y = 70 + i * 48 - 20
        f.line([(155 - w, y), (155, y)], width=2.5)
    seg(f, 560, 110, set())
    return f


SEGS = {'a': (0, 0, 1), 'b': (1, 0, 0), 'c': (1, 1, 0), 'd': (0, 2, 1), 'e': (0, 1, 0), 'f': (0, 0, 0), 'g': (0, 1, 1)}


def seg(f, x, y, on, L=130, T=20):
    """세그먼트 일곱 개. on 에 든 세그먼트를 칠해요."""
    for name, (cx, cy, horiz) in SEGS.items():
        fill = BLUE if name in on else '#e8ebf0'
        if horiz:
            f.rect(x + T / 2, y + cy * L - T / 2, L - T, T, fill=fill, stroke=GREY, rx=4, sw=1.5)
            f.text(x + L / 2, y + cy * L + 7, name, size=20, anchor='middle', fill='#fff' if name in on else INK, weight='bold')
        else:
            f.rect(x + cx * L - T / 2, y + cy * L + T / 2, T, L - T, fill=fill, stroke=GREY, rx=4, sw=1.5)
            f.text(x + cx * L, y + cy * L + L / 2 + 7, name, size=20, anchor='middle', fill='#fff' if name in on else INK, weight='bold')


def ripple_block():
    f = NoteFig(742, 230, '비동기 2단 카운터 블록도')
    for x, name, output in ((152, 'A', 'A'), (440, 'B', 'B')):
        f.rect(x, 52, 166, 145, fill=BLUEBG)
        f.label(x + 83, 33, 'FF', sub=name, anchor='middle')
        f.label(x + 31, 127, 'CLK')
        f.label(x + 24, 173, 'T = 1')
        f.label(x + 146, 85, output, anchor='end', node=output)
        f.label(x + 146, 173, output + '′', anchor='end')
        f.path(f'M{x},108 l14,10 l-14,10', fill='none')
        f.circle(x - 6, 118, 6)
    f.label(78, 126, 'CLK', anchor='end')
    f.line([(100, 118), (140, 118)])
    f.junction(100, 118)
    f.line([(318, 77), (382, 77), (382, 118), (428, 118)])
    f.line([(606, 77), (677, 77)])
    f.junction(677, 77, node='B')
    f.label(700, 85, 'B', node='B')
    return f


def ripple_delay():
    f = Fig(760, 330, '11에서 00으로 갈 때의 지연 확대')
    x0, s = 110, 80
    f.text(90, 72, 'CLK', size=22, anchor='end', weight='bold')
    wave(f, x0, 40, s, [1, 1, 0, 0, 0, 0, 0], h=40)
    f.text(90, 152, 'A', size=22, anchor='end', weight='bold')
    wave(f, x0, 120, s, [1, 1, 1, 0, 0, 0, 0], h=40, color=BLUE)
    f.text(90, 232, 'B', size=22, anchor='end', weight='bold')
    wave(f, x0, 200, s, [1, 1, 1, 1, 0, 0, 0], h=40, color=BLUE)
    f.text(90, 300, 'AB', size=22, anchor='end', weight='bold')
    for x, t, c in ((x0 + 1.5 * s, '11', INK), (x0 + 3.5 * s, '01', RED), (x0 + 5.5 * s, '00', INK)):
        f.text(x, 300, t, size=24, anchor='middle', fill=c, weight='bold')
    for x in (x0 + 2 * s, x0 + 3 * s, x0 + 4 * s):
        f.line([(x, 30), (x, 270)], color=GREY, width=1.5, dash='6 6')
    return f


def sync_block():
    f = NoteFig(805, 319, '동기 3진 카운터 블록도')
    for x, n, q in ((185, 'A', 'A'), (475, 'B', 'B')):
        f.rect(x, 85, 176, 152, fill=BLUEBG)
        f.label(x + 20, 126, 'J')
        f.label(x + 31, 175, 'CLK', size=22)
        f.label(x + 20, 216, 'K = 1', size=22)
        f.label(x + 155, 126, q, anchor='end', node=q)
        f.label(x + 155, 216, q + '′', anchor='end', node=f'{q}-bar', color='red')
        f.label(x + 128, 175, 'FF', sub=n, anchor='middle', size=22)
        f.path(f'M{x},156 l14,10 l-14,10', fill='none')
        f.circle(x - 6, 166, 6)
    f.label(81, 291, 'CLK', anchor='end', node='clock')
    f.junction(104, 283, node='clock')
    f.line([(104, 283), (428, 283), (428, 166), (463, 166)])
    f.line([(151, 283), (151, 166), (173, 166)])
    f.junction(151, 283, node='clock')
    f.line([(361, 118), (475, 118)])
    f.label(417, 100, 'A', anchor='middle', node='A')
    f.line([(651, 118), (727, 118)])
    f.junction(727, 118, node='B')
    f.label(750, 126, 'B', node='B')
    f.line([(651, 208), (702, 208), (702, 53), (123, 53), (123, 118), (185, 118)])
    f.crossing(702, 118)
    f.label(405, 34, 'B′', anchor='middle', node='B-bar', color='red')
    return f


def sync_states_fig():
    f = Fig(700, 300, '동기 3진 카운터 상태도')
    pts = {'00': (130, 110), '10': (350, 110), '01': (570, 110), '11': (350, 240)}
    for k, (x, y) in pts.items():
        dash = k == '11'
        f.circle(x, y, 44, fill='#fff' if dash else BLUEBG, stroke=GREY if dash else INK)
        f.text(x, y + 9, k, size=26, anchor='middle', fill=GREY if dash else INK, weight='bold')
    f.line([(174, 110), (306, 110)])
    f.path('M306,110 l-14,-8 v16 z', fill=INK)
    f.line([(394, 110), (526, 110)])
    f.path('M526,110 l-14,-8 v16 z', fill=INK)
    f.line([(570, 66), (570, 30), (130, 30), (130, 66)])
    f.path('M130,66 l-8,-14 h16 z', fill=INK)
    f.line([(310, 222), (165, 142)], color=GREY)
    f.path('M165,142 l16,1 l-8,14 z', fill=GREY)
    f.text(410, 248, '쓰지 않는 상태', size=20, fill=GREY)
    return f


def decoder():
    f = NoteFig(550, 470, '네 AND 게이트로 만든 상태 디코더')
    terms = (('A′', 'B′'), ('A', 'B′'), ('A′', 'B'), ('A', 'B'))
    for i, names in enumerate(terms):
        g = f.and_(190, 20 + i * 112, H=80)
        for name, (x, y) in zip(names, g['ins']):
            node = name[0] + ('-bar' if name.endswith('′') else '')
            color = 'red' if name.endswith('′') else 'blue'
            f.label(99, y + 8, name, anchor='end', node=node, color=color)
            f.line([(123, y), (x, y)])
            f.junction(123, y, node=node, color=color)
        x, y = g['out']
        f.line([(x, y), (368, y)])
        f.junction(368, y)
        f.label(391, y + 8, f'출력 {i}')
    return f


def block7490():
    f = NoteFig(845, 383, '7490의 QA를 CLKB에 연결한 BCD 카운터')
    f.rect(178, 54, 474, 286, fill='#fff', rx=4)
    f.rect(210, 117, 150, 120, fill=BLUEBG)
    f.label(285, 145, '2진 단', anchor='middle')
    f.label(335, 201, 'Q', sub='A', anchor='end', node='qa')
    f.rect(465, 142, 158, 171, fill=BLUEBG)
    f.label(544, 128, '5진 단', anchor='middle')
    f.label(487, 269, 'CLKB', size=22)
    f.label(134, 202, 'CLK', anchor='end', node='clka', color='red')
    f.line([(156, 194), (210, 194)])
    f.junction(156, 194, node='clka', color='red')
    f.label(161, 172, '14', anchor='middle', size=22, node='clka', color='red')
    # QA branches to the external A terminal and the 5-divider clock input.
    f.line([(360, 194), (397, 194), (397, 89), (718, 89)])
    f.line([(397, 194), (397, 260), (465, 260)])
    f.junction(397, 194, node='qa')
    f.junction(718, 89, node='qa')
    f.label(745, 97, 'A', node='qa')
    f.label(677, 70, '12', size=22, node='qa')
    f.label(442, 242, '1', size=22, node='qa')
    for y, bit, pin in ((170, 'B', 9), (219, 'C', 8), (268, 'D', 11)):
        f.label(601, y + 8, 'Q', sub=bit, anchor='end', size=22)
        f.line([(623, y), (718, y)])
        f.junction(718, y)
        f.label(745, y + 8, bit)
        f.label(677, y - 18, str(pin), size=22)
    f.label(432, 376, '7490', anchor='middle')
    return f


def fullchain():
    f = Fig(1000, 230, '클럭부터 FND까지의 전체 흐름')
    boxes = [(20, '1Hz', '클럭', False), (190, '7490', '세기', True), (390, '7447', '번역', True), (590, '330Ω', '7개', False), (770, 'FND', '표시', True)]
    for x, t, s, on in boxes:
        f.rect(x, 50, 130, 110, fill=BLUEBG if on else '#fff')
        f.text(x + 65, 98, t, size=26, anchor='middle', weight='bold')
        f.text(x + 65, 134, s, size=22, anchor='middle')
    for x1, x2, t in ((150, 190, ''), (320, 390, 'ABCD'), (520, 590, 'a~g'), (720, 770, '')):
        f.line([(x1, 105), (x2, 105)])
        f.path(f'M{x2},105 l-12,-7 v14 z', fill=INK)
        if t:
            f.text((x1 + x2) / 2, 92, t, size=20, anchor='middle', fill=BLUE, weight='bold')
    f.text(835, 200, '공통 핀 +5V', size=20, anchor='middle', fill=RED)
    f.line([(835, 160), (835, 180)], color=RED)
    return f


def seven5():
    f = Fig(300, 360, '숫자 5에서 켜지는 세그먼트')
    seg(f, 85, 50, set('acdfg'))
    return f


def and_given():
    f = Fig(620, 220, '74HC08 AND 게이트 한 개로 만든 출력 3')
    g = f.and_(250, 60, H=90)
    f.text(60, g['ins'][0][1] + 8, 'A', size=28)
    f.text(60, g['ins'][1][1] + 8, 'B', size=28)
    f.line([(100, g['ins'][0][1]), g['ins'][0]])
    f.line([(100, g['ins'][1][1]), g['ins'][1]])
    f.line([g['out'], (470, g['out'][1])])
    f.text(490, g['out'][1] + 9, 'Y', size=28, weight='bold')
    f.text(220, g['ins'][0][1] - 8, '1', size=20, fill=GREY)
    f.text(220, g['ins'][1][1] + 24, '2', size=20, fill=GREY)
    f.text(420, g['out'][1] - 10, '3', size=20, fill=GREY)
    f.text(20, 200, '74HC08: VCC 14번=+5V, GND 7번=0V', size=22)
    return f


def mod6():
    f = Fig(860, 280, '3진 회로 뒤에 T F/F 하나를 붙여 6상태로 만드는 그림')
    f.rect(190, 70, 260, 130, fill=BLUEBG)
    f.text(320, 128, '문제의 3진 회로', size=24, anchor='middle', weight='bold')
    f.text(320, 164, '(그대로 둠)', size=22, anchor='middle')
    f.rect(590, 70, 170, 130, fill='#fff', stroke=BLUE)
    f.text(675, 128, 'T F/F', size=24, anchor='middle', weight='bold', fill=BLUE)
    f.text(675, 164, '새로 추가', size=20, anchor='middle', fill=BLUE)
    f.text(40, 142, 'Clock', size=24)
    f.line([(115, 135), (190, 135)])
    f.line([(450, 135), (590, 135)], color=BLUE)
    f.text(520, 120, 'B 하강', size=22, anchor='middle', fill=BLUE, weight='bold')
    f.line([(760, 135), (820, 135)], color=BLUE)
    f.text(835, 143, 'C', size=24, anchor='middle', fill=BLUE, weight='bold')
    f.text(430, 250, '상태 수 3 × 2 = 6, 플립플롭 3개', size=24, anchor='middle')
    return f


def draw_note_schematics(output_dir: Path) -> tuple[Path, ...]:
    return write_note_schematics(output_dir, {
        'ripple-block': ripple_block(), 'sync-block': sync_block(),
        'decoder-and': decoder(), '7490-block': block7490(),
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
        reg.append(dict(id=fid, question_id=pid, role=role, svg=f'figures/{sub}/{fid}.svg', png=f'figures/{sub}/{fid}.png', svg_sha256=sha(stem.with_suffix('.svg')), png_sha256=sha(stem.with_suffix('.png')), w_mm=ww, h_mm=ww * f.h / f.w, source_asset_ids=list(ids), source_refs=q['sources'][:1], derivation=how, answer_exposure='none' if role == 'problem' else 'present', review_status='pass', review_notes='2026-11-02 PNG·A4 PDF를 원문·교안 회로와 대조했어요. 핀, 공통 클럭, 되먹임, 하강 엣지 위치, 문제 그림의 답 비노출을 확인했어요.'))

    for name, f in (('ripple-wave', timing('비동기 2단 카운터 파형', ripple_states(4), extra=True)), ('ripple-delay', ripple_delay()), ('sync-states', sync_states_fig()), ('seven-seg-5', seven5()), ('full-chain', fullchain())):
        (F / f'{name}.svg').write_text(f.svg(), encoding='utf8')
    draw_note_schematics(F)

    register('xbit-given', 'q-xbit-ymod', 'problem', tchain(), 120, ['a-s02-p1-o-s02-q2'])
    register('sync-given', 'q-sync-wave', 'problem', schem(True), 150, ['a-s02-p1-o-s02-q3'])
    register('sync-blank', 'q-sync-wave', 'problem', blank_wave('동기 회로 파형 답란'), 150, ['a-s02-p1-o-s02-q3'])
    register('sync-wave', 'q-sync-wave', 'solution', timing('동기 3진 회로 완성 파형', sync_states(6), extra=True), 150)
    register('sync-given-2', 'q-mod-and-double', 'problem', schem(True), 150, ['a-s02-p1'])
    register('mod6', 'q-mod-and-double', 'solution', mod6(), 130)
    register('ripple-given', 'q-ripple-wave', 'problem', schem(False), 150, ['a-s07-p2-o-s07-q7'])
    register('ripple-blank', 'q-ripple-wave', 'problem', blank_wave('비동기 회로 파형 답란'), 150, ['a-s07-p2-o-s07-q7'])
    register('ripple-solution', 'q-ripple-wave', 'solution', timing('비동기 2단 회로 완성 파형', ripple_states(6), extra=True), 150)
    register('pin7447-given', 'q-7447', 'problem', pin7447(), 120, ['a-s07-p4-o-s07-q10'])
    register('seven5-solution', 'q-7447', 'solution', seven5(), 45)

    pid = 'q-qp-e08-board-01'
    register('and-given', pid, 'problem', and_given(), 75)
    # engine validation is separate from the PDF coordinate projection
    b = BreadboardRenderer(board='v1')
    c = b.cols['left']
    y = b.r_y
    b.draw_chip('74HC08', 10)
    b.connect_jacks()
    b.bridge_rails(c['vcc'], c['mid_vcc'], 35, kind='vcc')
    b.connect_power(10)
    _input_jumper(b, c, 10, 'A', 'external input A')
    _input_jumper(b, c, 11, 'B', 'external input B')
    b.mark_unused_inputs([4, 5, 9, 10, 12, 13], 10)
    b.mark_unused_outputs([6, 8, 11], 10)
    b.step_wire([(c['b'], y(12)), (220, y(12)), (220, y(20)), (c['b'], y(20))], 'sig', 'Y pin3 measurement point at b20')
    b.instrument(c['a'], 12, 'Y', 'pin3 output measurement')
    b.verify()
    nets = []
    for n in b.nets():
        pins = {int(t.rsplit(' ', 1)[1]) for t in n['labels'] if ' pin ' in t}
        if pins:
            nets.append(pins)
    assert {14} in nets and {7} in nets
    png, w, h = template_png()
    head = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}"><title>v1 PDF AND gate board</title>'
    bg = f'<image x="0" y="0" width="{w}" height="{h}" href="data:image/png;base64,{base64.b64encode(png).decode()}"/>'
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
    parts.append(f'<text x="{(l+r)/2}" y="{(t+bot)/2}" font-size="34" text-anchor="middle" transform="rotate(-90 {(l+r)/2} {(t+bot)/2})">74HC08</text>')
    mapped = []
    for k, pts, desc in b._segments:
        out = [(1083 if b._jack_at(x, yv) == 'red' else 1936, 400) if b._jack_at(x, yv) else (mx(x), my(yv)) for x, yv in pts]
        coords = ' '.join(f'{x:.1f},{yv:.1f}' for x, yv in out)
        color = {'vcc': '#dc2626', 'gnd': '#1665ca', 'sig': '#16814e', 'mid': '#b06a00'}[k]
        parts.append(f'<polyline points="{coords}" fill="none" stroke="white" stroke-width="13"/><polyline points="{coords}" fill="none" stroke="{color}" stroke-width="7"/>')
        for xx, yy in [out[0], out[-1]]:
            parts.append(f'<circle cx="{xx}" cy="{yy}" r="8" fill="{color}"/>')
        mapped.append(dict(kind=k, description=desc, pdf_points=out))
    parts.append(f'<text x="470" y="{my(y(9))-15}" font-size="48">A</text><text x="335" y="{my(y(12))+12}" font-size="48">B</text><text x="480" y="{my(y(20))+65}" font-size="48">Y (pin3)</text>')
    for suffix, role, body in (('blank', 'problem', ''), ('complete', 'solution', ''.join(parts))):
        sub = 'questions' if role == 'problem' else 'solutions'
        stem = F / sub / ('and-' + suffix)
        stem.with_suffix('.svg').write_text(head + bg + body + '</svg>', encoding='utf8')
        if suffix == 'blank':
            stem.with_suffix('.png').write_bytes(png)
        else:
            render_png(stem.with_suffix('.svg'), stem.with_suffix('.png'), 100)
        reg.append(dict(id='and-' + suffix, question_id=pid, role=role, svg=f'figures/{sub}/and-{suffix}.svg', png=f'figures/{sub}/and-{suffix}.png', svg_sha256=sha(stem.with_suffix('.svg')), png_sha256=sha(stem.with_suffix('.png')), w_mm=100, h_mm=100 * h / w, source_asset_ids=[], source_refs=[dict(source_id='s-board', pdf_page=1, printed_page=None)], derivation='v1 배포 강의노트/공지사항/Breadboard.pdf sha256=' + sha(REPO / '강의노트/공지사항/Breadboard.pdf') + ' 300dpi 전체 페이지. PDF 열 중심 394,433,563,606,649,692,734,862,904,948,990,1033,1161,1201; 행1=711.8 행63=3352. 엔진 JPG 좌표를 개별 선형 대응. verify 와 넷 대조.', answer_exposure='none' if role == 'problem' else 'present', review_status='pass', review_notes='2026-11-02 확대 렌더로 배선 끝점이 홀에 놓이고 14번 +5V, 7번 GND, 1·2번 입력, 3번 측정점인지 확인했어요.'))
    (F / 'quiz-board-mapping.json').write_text(json.dumps(dict(columns=xs, y_first=711.8, y_last=3352, segments=mapped, nets=[sorted(n) for n in nets]), ensure_ascii=False, indent=2))
    (F / 'redraw-manifest.json').write_text(json.dumps(dict(schema_version=1, figures=reg), ensure_ascii=False, indent=2))
