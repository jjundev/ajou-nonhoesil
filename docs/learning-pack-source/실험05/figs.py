"""All 실험05 schematics, drawn from scratch (not copies of the originals)."""
from figlib import *


def decoder_core(f, ox, oy, a1='A1', a0='A0', outs=('D0', 'D1', 'D2', 'D3'), out_eq=None,
                 data=None, out_labels=True, gate_names=None, ghost_note=None, pitch=100):
    """2x4 decoder with vertical signal buses. Optional data input D (3-input ANDs).
    ox,oy: top-left of the drawing area. Returns bottom y."""
    bx = dict(a1=ox + 70, n1=ox + 160, a0=ox + 230, n0=ox + 320)
    if data:
        bx['d'] = ox + 390
    top0, top1 = oy + 10, oy + 56
    # inputs
    f.text(ox, top0 + 7, a0, anchor='start', weight='bold')
    f.line([(ox + 42, top0), (bx['a0'], top0)])
    f.text(ox, top1 + 7, a1, anchor='start', weight='bold')
    f.line([(ox + 42, top1), (bx['a1'], top1)])
    if data:
        dy = oy - 34
        f.text(ox, dy + 7, data, anchor='start', weight='bold')
        f.line([(ox + 42, dy), (bx['d'], dy)])
    ny = oy + 120
    n1 = f.not_(bx['a1'] + 8, ny - 22)
    f.line([n1['out'], (bx['n1'], ny)])
    f.dot(bx['a1'], ny)
    n0 = f.not_(bx['a0'] + 8, ny - 22)
    f.line([n0['out'], (bx['n0'], ny)])
    f.dot(bx['a0'], ny)
    gx = ox + 480
    gy0 = oy + 190
    buses = {k: [] for k in bx}
    taps = []
    n = 3 if data else 2
    for k in range(4):
        hi = (k >> 1) & 1
        lo = k & 1
        g = f.and_(gx, gy0 + pitch * k, n)
        pins = g['ins']
        wires = [('a1' if hi else 'n1'), ('a0' if lo else 'n0')] + (['d'] if data else [])
        for (px, py), key in zip(pins, wires):
            taps.append((key, py))
            f.line([(bx[key], py), (px, py)])
            f.dot(bx[key], py)
        ex = g['out'][0] + 70
        f.line([g['out'], (ex, g['out'][1])])
        if out_labels:
            f.text(ex + 10, g['out'][1] + 8, outs[k], weight='bold')
            if out_eq:
                f.text(ex + 10, g['out'][1] + 34, out_eq[k], size=20, fill=GREY)
    # vertical buses
    start = dict(a1=top1, n1=ny, a0=top0, n0=ny)
    if data:
        start['d'] = dy
    for key, x in bx.items():
        ys = [y for k2, y in taps if k2 == key]
        f.line([(x, start[key]), (x, max(ys))])
    f.text(bx['a1'], oy + 190 - 100 + 0, '', size=18)
    return gy0 + pitch * 3 + 70


def dec2x4_fig(title, a1='A1', a0='A0', outs=('D0', 'D1', 'D2', 'D3'), eq=True):
    f = Fig(860, 680, title, '입력 두 개와 반전 신호를 AND 네 개에 연결한 2×4 디코더')
    ox, oy = 30, 60
    out_eq = [f'= {a1}′·{a0}′', f'= {a1}′·{a0}', f'= {a1}·{a0}′', f'= {a1}·{a0}'] if eq else None
    decoder_core(f, ox, oy, a1, a0, outs, out_eq)
    f.text(30, 655, '선 교차에 점이 없으면 이어지지 않아요', size=20, fill=GREY)
    return f


def demux_fig(title, solution=True):
    f = Fig(940, 720, title, '디코더의 AND 게이트를 3입력으로 바꿔 데이터 D를 함께 곱한 1×4 디멀티플렉서')
    ox, oy = 30, 90
    decoder_core(f, ox, oy, 'S1', 'S0', ('Y0', 'Y1', 'Y2', 'Y3'),
                 ['= S1′S0′D', '= S1′S0·D', '= S1·S0′D', '= S1·S0·D'], data='D')
    f.text(30, 698, '선 교차에 점이 없으면 이어지지 않아요', size=20, fill=GREY)
    return f


def given_decoder_fig(title):
    """Problem figure: plain 2-to-4 decoder gate circuit, outputs unlabeled."""
    f = Fig(860, 600, title, '입력 S0, S1과 NOT 두 개, 2입력 AND 네 개로 이루어진 2 to 4 디코더 게이트 회로')
    ox, oy = 30, 60
    decoder_core(f, ox, oy, 'S1', 'S0', ('', '', '', ''), None, out_labels=False, pitch=82)
    f.text(30, 585, '출력 네 줄은 아래 AND 네 개의 출력이에요', size=20, fill=GREY)
    return f


def enc4x2_nand_fig(title='4×2 인코더 (NAND 구성)', labels=True):
    W, H = 1180, 820
    f = Fig(W, H, title, 'NOT 4개, 4입력 NAND 3개, 2입력 NAND 2개로 만든 4×2 인코더')
    ys = [70, 135, 200, 265]
    names = ['D0', 'D1', 'D2', 'D3']
    R = [150 + 28 * i for i in range(4)]
    N = [400 + 28 * i for i in range(4)]
    last_tap = {}
    taps = []
    for i in range(4):
        f.text(30, ys[i] + 8, names[i], weight='bold')
        f.line([(80, ys[i]), (R[i], ys[i]), (300, ys[i])])
        f.dot(R[i], ys[i])
        g = f.not_(300, ys[i] - 22)
        f.line([g['out'], (N[i], ys[i])])
    gx = 620
    gates = [  # (label, y, pins)
        ('t1', 350, [('R', 1), ('N', 0), ('N', 2), ('N', 3)]),
        ('t3', 490, [('R', 3), ('N', 0), ('N', 1), ('N', 2)]),
        ('t2', 630, [('R', 2), ('N', 0), ('N', 1), ('N', 3)]),
    ]
    outs = {}
    for lab, gy, pins in gates:
        g = f.and_(gx, gy, 4, bubble=True, H=122)
        outs[lab] = g['out']
        for (kind, idx), (px, py) in zip(pins, g['ins']):
            x = R[idx] if kind == 'R' else N[idx]
            taps.append(((kind, idx), py))
            f.line([(x, py), (px, py)])
            f.dot(x, py)
    for i in range(4):
        ysr = [y for (k, j), y in taps if k == 'R' and j == i]
        ysn = [y for (k, j), y in taps if k == 'N' and j == i]
        f.line([(R[i], ys[i]), (R[i], max([ys[i]] + ysr))])
        f.line([(N[i], ys[i]), (N[i], max([ys[i]] + ysn))])
    # second-level NAND2: B uses t1,t3 ; A uses t3,t2
    nx = 850
    gb = f.and_(nx, 395, 2, bubble=True)
    ga = f.and_(nx, 575, 2, bubble=True)
    t1, t3, t2 = outs['t1'], outs['t3'], outs['t2']
    f.line([t1, (770, t1[1]), (770, gb['ins'][0][1]), gb['ins'][0]])
    fx = 745
    f.line([t3, (fx, t3[1])])
    f.dot(fx, t3[1])
    f.line([(fx, t3[1]), (fx, gb['ins'][1][1]), gb['ins'][1]])
    f.line([(fx, t3[1]), (fx, ga['ins'][0][1]), ga['ins'][0]])
    f.line([t2, (770, t2[1]), (770, ga['ins'][1][1]), ga['ins'][1]])
    for g, nm, sub in ((gb, 'B', '(하위 비트)'), (ga, 'A', '(상위 비트)')):
        ex = g['out'][0] + 50
        f.line([g['out'], (ex, g['out'][1])])
        if labels:
            f.text(ex + 8, g['out'][1] + 8, nm, weight='bold')
            f.text(ex + 8, g['out'][1] + 34, sub, size=20, fill=GREY)
    f.text(30, 800, '동그라미(○)는 반전이에요. 선 교차에 점이 없으면 이어지지 않아요', size=20, fill=GREY)
    return f


def excess3_fig(title, answer_free=True, names=True, compact=False):
    """Decimal(0-5) to Excess-3 encoder: switches D5..D0, six NOT, four NAND4."""
    W, H = (1120, 610) if compact else (1120, 820)
    f = Fig(W, H, title, '스위치 D5부터 D0까지 여섯 개와 NOT 여섯 개, 4입력 NAND 네 개로 이루어진 십진수 Excess-3 인코더')
    rows = ({5: 60, 4: 136, 3: 212, 2: 288, 1: 364, 0: 440} if compact else {5: 90, 4: 190, 3: 290, 2: 390, 1: 490, 0: 590})
    GH = 96 if compact else 122
    bus_x = {5: 600, 4: 565, 3: 530, 2: 495, 1: 460, 0: 425}  # top row = rightmost bus
    sw_label = {5: 'D5 · SW5 (십진 5)', 4: 'D4', 3: 'D3', 2: 'D2', 1: 'D1', 0: 'D0 · SW0 (십진 0)'}
    for d, y in rows.items():
        x_end, _ = f.switch(70, y, '')
        f.text((x_end + 300) / 2, y - 27, sw_label[d] if names else f'D{d}', size=20, anchor='middle', weight='bold')
        f.line([(x_end, y), (300, y)])
        g = f.not_(300, y - 22)
        f.line([g['out'], (bus_x[d], y)])
    gx = 780
    specs = [
        ('Bit3', 'U2A', 40 if not compact else 36, [('N', 5), ('V', 0), ('V', 0), ('V', 0)]),
        ('Bit2', 'U2B', 220 if not compact else 160, [('N', 4), ('N', 3), ('N', 2), ('N', 1)]),
        ('Bit1', 'U3A', 400 if not compact else 282, [('N', 4), ('N', 3), ('N', 0), ('V', 0)]),
        ('Bit0', 'U3B', 580 if not compact else 426, [('N', 4), ('N', 2), ('N', 0), ('V', 0)]),
    ]
    taps = {d: [rows[d]] for d in rows}
    for bit, uname, gy, pins in specs:
        g = f.and_(gx, gy, 4, bubble=True, H=GH)
        f.text(gx + 4, gy - 8, f'{uname} 74HC20', size=18, fill=GREY)
        for (kind, d), (px, py) in zip(pins, g['ins']):
            if kind == 'N':
                f.line([(bus_x[d], py), (px, py)])
                f.dot(bus_x[d], py)
                taps[d].append(py)
            else:
                f.line([(px - 40, py), (px, py)])
                f.text(px - 46, py + 7, 'VCC', size=18, anchor='end', fill=GREY)
        ex = g['out'][0] + 60
        f.line([g['out'], (ex, g['out'][1])])
        f.text(ex + 10, g['out'][1] + 8, bit, weight='bold')
    for d in rows:
        f.line([(bus_x[d], min(taps[d])), (bus_x[d], max(taps[d]))])
    f.text(300, 515 if compact else 700, '74HC04 ×6 (NOT)', size=18, fill=GREY)
    f.text(30, 595 if compact else 800, '○ 는 반전이에요. NAND 의 남는 입력은 VCC(1)에 묶어 둬요. 선 교차에 점이 없으면 이어지지 않아요', size=19, fill=GREY)
    return f


def hc148_fig(title, labeled_switches=True):
    f = Fig(940, 560, title, '74HC148 우선순위 인코더: 입력 IN0~IN7과 EI는 Low 가 활성이고, 출력은 A2 A1 A0, GS, EO')
    bx, by, bw, bh = 400, 60, 190, 400
    f.rect(bx, by, bw, bh, fill=BLUEBG, stroke=BLUE)
    f.text(bx + bw / 2, by - 14, '74HC148', anchor='middle', size=24, fill=BLUE, weight='bold')
    pins_in = [('IN0', 10), ('IN1', 11), ('IN2', 12), ('IN3', 13), ('IN4', 1), ('IN5', 2), ('IN6', 3), ('IN7', 4)]
    for i, (n, p) in enumerate(pins_in):
        y = by + 34 + i * 40
        f.line([(bx - 60, y), (bx, y)])
        f.text(bx + 10, y + 7, n, size=20)
        f.text(bx - 66, y - 6, str(p), size=18, anchor='end', fill=GREY)
        f.text(bx - 70, y + 26, '', size=1)
    ei = by + 34 + 8 * 40 + 6
    f.line([(bx - 60, ei), (bx, ei)])
    f.text(bx + 10, ei + 7, 'EI', size=20)
    f.text(bx - 66, ei - 6, '5', size=18, anchor='end', fill=GREY)
    outs = [('A0', 9), ('A1', 7), ('A2', 6), ('GS', 14), ('EO', 15)]
    for i, (n, p) in enumerate(outs):
        y = by + 70 + i * 60
        f.line([(bx + bw, y), (bx + bw + 80, y)])
        f.text(bx + bw - 12, y + 7, n, size=20, anchor='end')
        f.text(bx + bw + 14, y - 6, str(p), size=18, fill=GREY)
        f.text(bx + bw + 96, y + 7, n, size=22, weight='bold')
    f.text(30, 40, '입력(왼쪽)과 EI 는 Low(0)일 때 활성', size=20, fill=GREY)
    f.text(bx + bw + 96, 36, '출력(오른쪽)', size=20, fill=GREY)
    f.text(30, 535, '숫자는 칩의 핀 번호예요', size=20, fill=GREY)
    return f


def given_148_fig(title):
    f = Fig(960, 580, title, 'U1=74HC148, 스위치 두 개로 짝수 입력과 홀수 입력을 각각 묶어 구동하고 EI는 GND에 연결')
    bx, by, bw, bh = 480, 70, 170, 380
    f.rect(bx, by, bw, bh, fill=BLUEBG, stroke=BLUE)
    f.text(bx + bw / 2, by - 14, '74HC148 (U1)', anchor='middle', size=22, fill=BLUE, weight='bold')
    pin_y = {}
    for i in range(8):
        y = by + 34 + i * 38
        pin_y[i] = y
        f.line([(bx - 70, y), (bx, y)])
        f.text(bx + 8, y + 7, f'IN{i}', size=20)
    ei = by + 34 + 8 * 38 + 6
    f.line([(bx - 70, ei), (bx, ei)])
    f.text(bx + 8, ei + 7, 'EI', size=20)
    f.line([(bx - 40, ei), (bx - 40, ei + 34)])
    f.line([(bx - 60, ei + 34), (bx - 20, ei + 34)])
    f.line([(bx - 52, ei + 42), (bx - 28, ei + 42)])
    f.text(bx - 12, ei + 50, 'GND', size=18, anchor='start', fill=GREY)
    ev, od = bx - 130, bx - 100
    sa = f.switch(60, 90, '')
    f.text(60, 40, 'SWa', size=22, weight='bold')
    sb = f.switch(60, 510, '')
    f.text(60, 462, 'SWb', size=22, weight='bold')
    f.line([sa, (ev, sa[1])])
    f.line([(ev, sa[1]), (ev, pin_y[6])])
    f.line([sb, (od, sb[1])])
    f.line([(od, pin_y[1]), (od, sb[1])])
    for i in (0, 2, 4, 6):
        f.line([(ev, pin_y[i]), (bx - 70, pin_y[i]), (bx, pin_y[i])])
        f.dot(ev, pin_y[i])
    for i in (1, 3, 5, 7):
        f.line([(od, pin_y[i]), (bx, pin_y[i])])
        f.dot(od, pin_y[i])
    f.text(140, 40, '→ IN0 IN2 IN4 IN6', size=20, fill=GREY)
    f.text(140, 462, '→ IN1 IN3 IN5 IN7', size=20, fill=GREY)
    outs = [('A0', 0), ('A1', 1), ('A2', 2), ('GS', 3), ('EO', 4)]
    for n, i in outs:
        y = by + 60 + i * 60
        f.line([(bx + bw, y), (bx + bw + 90, y)])
        f.text(bx + bw - 10, y + 7, n, size=20, anchor='end')
        f.text(bx + bw + 100, y + 7, n, size=22, weight='bold')
    return f


def bcd_decoder_fig(title='BCD → 십진 디코더 (74HC42) + 출력 LED'):
    f = Fig(980, 640, title, '스위치 네 개가 74HC42의 A B C D 입력을 정하고, Low 가 활성인 출력 Y0~Y9에 LED를 VCC 쪽으로 달아요')
    bx, by, bw, bh = 330, 50, 190, 520
    f.rect(bx, by, bw, bh, fill=BLUEBG, stroke=BLUE)
    f.text(bx + bw / 2, by + bh / 2 + 8, '74HC42', anchor='middle', size=26, fill=BLUE, weight='bold')
    for i, (n, bit) in enumerate([('A', 'Bit0'), ('B', 'Bit1'), ('C', 'Bit2'), ('D', 'Bit3')]):
        y = by + 70 + i * 100
        f.line([(bx - 90, y), (bx, y)])
        f.text(bx + 12, y + 8, n, size=22)
        f.text(bx - 100, y + 8, bit, size=22, anchor='end', weight='bold')
    for k in range(10):
        y = by + 34 + k * 49
        f.line([(bx + bw, y), (bx + bw + 60, y)])
        f.text(bx + bw - 12, y + 7, f'Y{k}', size=20, anchor='end')
        f.circle(bx + bw + 6, y, 6, fill='#fff')
    f.text(30, 40, '입력 (BCD 4비트)', size=20, fill=GREY)
    f.text(bx + bw + 20, 36, '출력 (Low 가 활성)', size=20, fill=GREY)
    # LED branch example
    ex = bx + bw + 100
    f.text(ex, 100, '출력 한 줄의 LED 연결', size=20, fill=GREY)
    yy = 180
    f.line([(ex, yy), (ex + 40, yy)])
    f.text(ex, yy - 14, 'Yk', size=20, fill=INK)
    f.path(f'M{ex+40:g},{yy:g} l8,-12 l12,24 l12,-24 l12,24 l8,-12', fill='none')
    f.text(ex + 62, yy + 40, '330Ω', size=20, anchor='middle', fill=GREY)
    f.line([(ex + 92, yy), (ex + 130, yy)])
    f.path(f'M{ex+156:g},{yy-16:g} L{ex+156:g},{yy+16:g} L{ex+130:g},{yy:g} Z', fill=BLUEBG, stroke=BLUE)
    f.line([(ex + 130, yy - 16), (ex + 130, yy + 16)], color=BLUE)
    f.line([(ex + 156, yy), (ex + 190, yy)])
    f.text(ex + 190, yy - 14, 'VCC', size=20, fill=INK)
    f.text(ex, yy + 90, 'Yk 가 Low(0)이면 전류가', size=20, fill=INK)
    f.text(ex, yy + 118, 'VCC → LED → 저항 → Yk 로 흘러', size=20, fill=INK)
    f.text(ex, yy + 146, 'LED 가 켜져요', size=20, fill=INK)
    return f


def pair_fig(title='디코더와 인코더는 서로 반대 방향이에요'):
    f = Fig(1000, 440, title, '디코더는 2진 코드를 한 줄만 켜진 신호로, 인코더는 한 줄만 켜진 신호를 2진 코드로 바꿔요')
    # decoder
    f.text(30, 40, '디코더 (Decoder)', size=26, weight='bold', fill=BLUE)
    f.rect(40, 70, 200, 70, fill=BLUEBG, stroke=BLUE)
    f.text(140, 114, '2진 코드  101', size=22, anchor='middle')
    f.line([(240, 105), (330, 105)])
    f.path('M330,85 l30,20 l-30,20 z', fill=BLUE, stroke=BLUE)
    f.rect(370, 62, 560, 86, fill='#fff')
    lab = ['D7', 'D6', 'D5', 'D4', 'D3', 'D2', 'D1', 'D0']
    val = [0, 0, 1, 0, 0, 0, 0, 0]
    for i, (l, v) in enumerate(zip(lab, val)):
        x = 395 + i * 66
        f.circle(x, 94, 20, fill=(BLUE if v else '#fff'), stroke=BLUE)
        f.text(x, 100, str(v), size=22, anchor='middle', fill=('#fff' if v else INK), weight='bold')
        f.text(x, 138, l, size=18, anchor='middle', fill=GREY)
    f.text(650, 172, '한 줄만 켜져요 (one-hot)', size=20, anchor='middle', fill=GREY)
    # encoder
    f.text(30, 250, '인코더 (Encoder)', size=26, weight='bold', fill=GRN)
    f.rect(40, 280, 560, 86, fill='#fff')
    for i, (l, v) in enumerate(zip(lab, val)):
        x = 65 + i * 66
        f.circle(x, 312, 20, fill=(GRN if v else '#fff'), stroke=GRN)
        f.text(x, 318, str(v), size=22, anchor='middle', fill=('#fff' if v else INK), weight='bold')
        f.text(x, 356, l, size=18, anchor='middle', fill=GREY)
    f.line([(610, 323), (700, 323)])
    f.path('M700,303 l30,20 l-30,20 z', fill=GRN, stroke=GRN)
    f.rect(740, 288, 200, 70, fill='#e9f7ef', stroke=GRN)
    f.text(840, 332, '2진 코드  101', size=22, anchor='middle')
    f.text(300, 410, '켜진 줄의 위치(5번)를 2진수 101로 알려 줘요', size=20, anchor='middle', fill=GREY)
    return f


def save(fig, out_svg, physical=None):
    Path(out_svg).parent.mkdir(parents=True, exist_ok=True)
    Path(out_svg).write_text(fig.svg(physical), encoding='utf-8')


if __name__ == '__main__':
    import sys
    out = Path('tmp/p5/preview')
    out.mkdir(parents=True, exist_ok=True)
    jobs = {
        'dec2x4': dec2x4_fig('2×4 디코더'),
        'demux': demux_fig('1×4 디멀티플렉서'),
        'given_dec': given_decoder_fig('2 to 4 디코더 게이트 회로'),
        'enc4x2': enc4x2_nand_fig(),
        'excess3': excess3_fig('Excess-3 인코더'),
        'hc148': hc148_fig('74HC148'),
        'given148': given_148_fig('74HC148 문제 회로'),
        'bcd': bcd_decoder_fig(),
        'pair': pair_fig(),
    }
    for k, fg in jobs.items():
        p = out / (k + '.svg')
        save(fg, p, physical=(fg.w * 0.14, fg.h * 0.14))
        render_png(p, out / (k + '.png'), fg.w * 0.14, dpi=160)
        print(k, fg.w, fg.h)
