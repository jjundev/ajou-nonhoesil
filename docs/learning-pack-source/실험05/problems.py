"""Workbook entries for 실험05. Truth tables are computed from the logic, not typed."""
from h import *
from itertools import product

# ---------------------------------------------------------------- logic models
def nand(*x):
    return 0 if all(x) else 1


def excess3_circuit(sw):
    """sw = dict d0..d5 -> 0/1 (switch to VCC = 1). Returns (bit3, bit2, bit1, bit0) per redrawn netlist."""
    n = {i: 1 - sw[i] for i in range(6)}
    b3 = nand(n[5], 1, 1, 1)
    b2 = nand(n[4], n[3], n[2], n[1])
    b1 = nand(n[4], n[3], n[0], 1)
    b0 = nand(n[4], n[2], n[0], 1)
    return b3, b2, b1, b0


def sw_word(word):
    """'000001' -> SW5..SW0 left to right."""
    return {5 - i: int(c) for i, c in enumerate(word)}


def fmt(bits):
    return ''.join(str(b) for b in bits)


# self checks of the circuit model against Excess-3 (BCD + 3)
for d in range(6):
    sw = {i: int(i == d) for i in range(6)}
    assert excess3_circuit(sw) == tuple(int(c) for c in format(d + 3, '04b')), d
assert excess3_circuit({i: 0 for i in range(6)}) == (0, 0, 0, 0)
assert excess3_circuit({0: 0, 1: 1, 2: 1, 3: 0, 4: 0, 5: 0}) == (0, 1, 0, 1)

# 4x2 NAND encoder model
def enc4x2(d):
    n = [1 - x for x in d]
    t1 = nand(d[1], n[0], n[2], n[3])
    t2 = nand(d[2], n[0], n[1], n[3])
    t3 = nand(d[3], n[0], n[1], n[2])
    return nand(t2, t3), nand(t1, t3)  # A (high), B (low)

for k in range(4):
    d = [int(i == k) for i in range(4)]
    a, b = enc4x2(d)
    assert (a << 1 | b) == k, k

# 2x4 decoder / 1x4 demux
for a1, a0 in product((0, 1), repeat=2):
    k = a1 * 2 + a0
    for dd in (0, 1):
        ys = [int((1 - a1 if not (j >> 1) else a1) and (1 - a0 if not (j & 1) else a0) and dd) for j in range(4)]
        assert ys == [int(j == k and dd == 1) for j in range(4)]

# 74HC148 (active low): highest-numbered low input wins
def hc148(ins, ei=0):
    """ins: list of 8 levels (0=L,1=H) for IN0..IN7. returns (A2,A1,A0) levels."""
    if ei == 1:
        return (1, 1, 1)
    low = [i for i in range(8) if ins[i] == 0]
    if not low:
        return (1, 1, 1)
    k = max(low)
    code = [(k >> 2) & 1, (k >> 1) & 1, k & 1]
    return tuple(1 - c for c in code)

row2 = [0, 1, 0, 1, 0, 1, 0, 1]
row3 = [1, 0, 1, 0, 1, 0, 1, 0]
assert hc148(row2) == (0, 0, 1) and hc148(row3) == (0, 0, 0) and hc148([1] * 8) == (1, 1, 1)


def prio8(word):
    bits = [int(c) for c in word.replace(' ', '')]  # D7..D0
    for i, b in enumerate(bits):
        if b:
            return 7 - i
    return None


assert [prio8(w) for w in ['0011 1010', '0101 1110', '0001 1101', '0110 0100', '1111 1111']] == [5, 6, 4, 6, 7]


# ---------------------------------------------------------------- html helpers
def blank_table(headers, rows):
    return table(headers, rows)


def img_sol(pid, alt, width=400):
    return f'<p><img src="figures/solutions/{pid}-solution-01.png" width="{width}" style="max-width:100%;height:auto" alt="{esc(alt)}"></p>'


def step(label, html):
    return dict(label=label, html=html)


def chk(t):
    return f'<p><strong>검산:</strong> {t}</p>'


def mist(t):
    return f'<p><strong>흔한 실수:</strong> {t}</p>'


P = {}

# ------------------------------------------------------------ q-dec3x8
H8 = ['A', 'D7', 'D6', 'D5', 'D4', 'D3', 'D2', 'D1', 'D0']
rows_q = [['000', '0', '0', '0', '0', '0', '0', '0', '1']] + [[format(k, '03b')] + [''] * 8 for k in range(1, 8)]
rows_a = [[format(k, '03b')] + [str(int(j == k)) for j in (7, 6, 5, 4, 3, 2, 1, 0)] for k in range(8)]
P['q-dec3x8'] = dict(
    original=p('3X8 Decoder의 Truth table을 완성하시오.') + blank_table(H8, rows_q) + p('(원문 표의 첫 행 A=000은 이미 채워져 있어요.)'),
    conditions=p('A는 세 비트 A2A1A0이고 출력은 D7~D0 여덟 줄이에요.'),
    ask=p('A=001부터 111까지 일곱 행의 D7~D0을 채우세요.'),
    problem_figures=[],
    hints=[dict(label='읽는 법', html=p('A를 이진수에서 십진수로 바꿔 보세요. 그 번호의 출력 하나만 1이에요.'))],
    solution=dict(steps=[
        step('풀이', p('3×8 디코더는 입력 A2A1A0가 가리키는 번호의 출력 Dk만 1이고 나머지는 0이에요. 001은 1이라서 D1, 010은 2라서 D2, … 111은 7이라서 D7만 1이에요.')),
        step('완성한 표', blank_table(H8, rows_a)),
        step('검산', chk('각 행에서 1이 정확히 하나이고, 그 자리 번호가 A의 십진수와 같아요. 예: 101=5 → D5.')),
        step('흔한 실수', mist('출력의 열 순서(D7이 왼쪽)를 잘못 읽어 1이 반대쪽에 오는 경우예요. 000 행의 1이 D0(맨 오른쪽)인 것을 기준으로 맞춰요.')),
    ], answer=p('A=k(십진수)이면 Dk만 1이에요. 000→D0, 001→D1, …, 111→D7.')),
    notes=['제공 답안(예상문제 자료의 답안 표)과 같은 표예요.'])

# ------------------------------------------------------------ q-prio-onehot
HP = ['D', 'A2', 'A1', 'A0']
oh = [format(1 << k, '08b') for k in range(8)]
oh_s = [w[:4] + ' ' + w[4:] for w in oh]
rows_q = [[oh_s[0], '0', '0', '0']] + [[w, '', '', ''] for w in oh_s[1:]]
rows_a = [[w, *format(k, '03b')] for k, w in enumerate(oh_s)]
P['q-prio-onehot'] = dict(
    original=p('8X3 Priority Encoder의 Truth table을 완성하시오') + blank_table(HP, rows_q) + p('(원문 표의 첫 행은 이미 채워져 있어요.)'),
    conditions=p('D는 D7…D0 여덟 비트이고, 각 행에서 한 비트만 1이에요. 출력은 A2A1A0예요.'),
    ask=p('나머지 일곱 행의 A2A1A0를 채우세요.'),
    problem_figures=[],
    hints=[dict(label='1의 위치', html=p('각 행에서 1이 있는 자리의 번호를 먼저 찾아요. 오른쪽 끝이 D0이에요.'))],
    solution=dict(steps=[
        step('풀이', p('한 비트만 1이면 우선순위를 가릴 일이 없어요. 1이 있는 자리 번호를 이진수로 쓴 값이 A2A1A0예요. 0000 0010은 D1이라서 001, 0000 0100은 D2라서 010, … 1000 0000은 D7이라서 111이에요.')),
        step('완성한 표', blank_table(HP, rows_a)),
        step('검산', chk('첫 행(D0 → 000)과 마지막 행(D7 → 111)이 일치하고, 여덟 행이 000부터 111까지 한 번씩 나와요.')),
        step('흔한 실수', mist('왼쪽 끝을 D0으로 읽으면 코드가 거꾸로 나와요.')),
    ], answer=p('D0→000, D1→001, D2→010, D3→011, D4→100, D5→101, D6→110, D7→111')),
    notes=['제공 답안과 같아요. 한 비트만 1인 행에서는 우선순위 방향이 결과를 바꾸지 않아요.'])

# ------------------------------------------------------------ q-prio-exam
ws = ['0011 1010', '0101 1110', '0001 1101', '0110 0100', '1111 1111']
rows_q = [['0000 0001', '0', '0', '0']] + [[w, '', '', ''] for w in ws]
rows_a = [['0000 0001', '0', '0', '0']] + [[w, *format(prio8(w), '03b')] for w in ws]
P['q-prio-exam'] = dict(
    original=p('8X3 Priority Encoder의 Truth table을 완성하시오') + p('Fill in the blanks of the 3x8 priority decoder.') + blank_table(HP, rows_q) + p('(원문 표의 첫 행은 이미 채워져 있어요.)'),
    conditions=p('D는 D7…D0 여덟 비트예요. 원문에는 우선순위 방향이 적혀 있지 않아요. 이 자료는 교안의 74HC148 표처럼 번호가 큰 입력이 우선이라고 읽어요. 영어 문장은 3x8 priority decoder라고 쓰여 있지만 한국어 문장과 표는 8×3 우선순위 인코더예요.'),
    ask=p('나머지 다섯 행의 A2A1A0를 채우세요.'),
    problem_figures=[],
    hints=[dict(label='먼저 볼 비트', html=p('여러 비트가 1이에요. 왼쪽(D7 쪽)부터 처음으로 1이 나오는 자리를 찾아요.'))],
    solution=dict(steps=[
        step('풀이', p('번호가 큰 입력이 우선이므로 각 행에서 가장 왼쪽의 1이 몇 번인지 찾고, 그 번호를 이진수로 써요. 0011 1010의 가장 왼쪽 1은 D5라서 101이에요. 0101 1110은 D6 → 110, 0001 1101은 D4 → 100, 0110 0100은 D6 → 110, 1111 1111은 D7 → 111이에요.')),
        step('완성한 표', blank_table(HP, rows_a)),
        step('검산', chk('각 행에서 선택한 자리보다 왼쪽은 모두 0이에요. 첫 행 0000 0001은 D0 → 000이라서 원문과 같아요.')),
        step('흔한 실수', mist('1이 여러 개일 때 모든 자리를 OR로 합치면 일반 인코더의 결과가 돼요. 예를 들어 0011 1010을 OR하면 다른 코드가 나와요.')),
    ], answer=p('0011 1010→101, 0101 1110→110, 0001 1101→100, 0110 0100→110, 1111 1111→111 (번호가 큰 입력 우선)')),
    notes=['원문은 우선순위 방향을 적지 않았어요. 교안 p11의 74HC148 표(IN7 우선)에 맞춰 풀었어요. 퀴즈 해설 자료의 “IN0가 가장 높은 우선순위” 문장은 같은 해설의 예와 맞지 않아 쓰지 않았어요. 방향이 반대(D0 우선)라면 답이 달라져요.'])

# ------------------------------------------------------------ q-dec2x4-design
P['q-dec2x4-design'] = dict(
    original=p('2x4 Decoder의 회로를 설계하시오.(Not gate 2개, 2-input And gate 4개)') + p('Design a circuit diagram of 2x4 decoder. (2 NOT gates, 4 2-input AND gates)'),
    conditions=p('입력은 I1, I0 두 개, 출력은 O0~O3 네 개예요. 출력 Ok는 I1I0가 k를 이진수로 쓴 값일 때만 1이에요.'),
    ask=p('NOT 2개와 2입력 AND 4개로 회로를 그리고 논리식을 쓰세요.'),
    problem_figures=[],
    hints=[dict(label='출력마다 한 조합', html=p('네 출력이 각각 입력 조합 하나만 1로 만들어야 해요. 조합마다 I1과 I0 중 어느 쪽에 NOT을 붙일지 정해 보세요.'))],
    solution=dict(steps=[
        step('풀이', p('I1과 I0를 각각 NOT에 넣어 I1′, I0′를 만들어요. 각 AND에는 그 출력이 선택하는 조합의 값(원래 신호 또는 반전 신호)을 하나씩 넣어요. O0=I1′I0′, O1=I1′I0, O2=I1I0′, O3=I1I0예요.')),
        step('완성 회로', img_sol('q-dec2x4-design', '2×4 디코더 완성 회로')),
        step('논리식', tex(r'O_0=\overline{I_1}\,\overline{I_0},\ O_1=\overline{I_1}I_0,\ O_2=I_1\overline{I_0},\ O_3=I_1I_0')),
        step('표로 확인', blank_table(['I1', 'I0', 'O3', 'O2', 'O1', 'O0'], [['0', '0', '0', '0', '0', '1'], ['0', '1', '0', '0', '1', '0'], ['1', '0', '0', '1', '0', '0'], ['1', '1', '1', '0', '0', '0']])),
        step('검산', chk('게이트 수는 NOT 2개, 2입력 AND 4개로 요구와 같아요. 네 입력 조합에서 켜진 출력이 정확히 하나씩이에요.')),
        step('흔한 실수', mist('두 NOT 출력을 서로 바꾸어 연결하면 O1과 O2가 뒤바뀌어요. I1이 상위 비트라는 점을 기준으로 맞춰요.')),
    ], answer=p('O0=I1′I0′, O1=I1′I0, O2=I1I0′, O3=I1I0 (NOT 2개, AND 4개)')),
    notes=['제공 답안 그림(입력 I0·I1, NOT 2개, AND 4개, 출력 O0~O3)과 같은 구조예요.'])

# ------------------------------------------------------------ q-enc4x2-design
rows_e = []
for k in range(4):
    d = [int(i == k) for i in range(4)]
    a, b = enc4x2(d)
    rows_e.append([str(d[3]), str(d[2]), str(d[1]), str(d[0]), str(a), str(b)])
P['q-enc4x2-design'] = dict(
    original=p('4x2 Encoder의 회로를 설계하시오.(Not gate 4개, 4-input nand gate 3개, 2-input nand gate 2개)') + p('Design a circuit diagram of 2x4 Encoder. (4 NOT gates, 3 4-input NAND gates, 2 2-input NAND gates)'),
    conditions=p('입력 D0~D3 중 한 줄만 1이라고 가정하고, 출력은 상위 비트 A와 하위 비트 B로 두어요. 영어 문장은 2x4라고 쓰였지만 한국어 문장과 게이트 수에 맞춰 4×2 인코더로 읽어요.'),
    ask=p('주어진 게이트 수로 회로를 그리고 A, B의 논리식을 쓰세요.'),
    problem_figures=[],
    hints=[dict(label='식부터', html=p('D0~D3의 번호 0~3을 이진수로 쓰고, A와 B가 1이 되는 번호를 찾으세요. 그다음 NAND 두 단계가 OR을 만든다는 점을 떠올려요.'))],
    solution=dict(steps=[
        step('식 세우기', p('번호 0~3의 이진수는 00, 01, 10, 11이에요. 그래서 A=D2+D3, B=D1+D3이에요. D0은 코드가 00이라 더할 항이 없어요.')),
        step('NAND로 바꾸기', p('D1, D2, D3 각각 “자기만 켜진 항”을 4입력 NAND로 만들어요(그래서 NOT이 D0~D3에 하나씩 4개). 두 번째 단계의 2입력 NAND가 A(D2항, D3항)와 B(D1항, D3항)를 합쳐요. 드모르간 법칙으로 NAND(X′, Y′)=X+Y예요.')),
        step('완성 회로', img_sol('q-enc4x2-design', '4×2 인코더 NAND 구성 회로', 280)),
        step('표와 검산', blank_table(['D3', 'D2', 'D1', 'D0', 'A', 'B'], rows_e) + p('<strong>검산:</strong> NOT 4개, 4입력 NAND 3개, 2입력 NAND 2개이고 AB가 번호와 같아요. <strong>흔한 실수:</strong> 두 번째 NAND를 AND로 읽지 않아요.')),
    ], answer=p('A=D2+D3, B=D1+D3 (NOT 4개, 4입력 NAND 3개, 2입력 NAND 2개의 NAND-NAND 회로)')),
    notes=['제공 답안은 교재식 4×2 인코더 그림(NOT 4개, AND 3개, OR 2개)으로, NAND 구성과 게이트 종류가 달라서 후보 연결로만 두었어요. AND-OR 구조를 드모르간 법칙으로 NAND-NAND로 바꾼 것과 같은 동작이에요.'])

# ------------------------------------------------------------ q-excess3-why
P['q-excess3-why'] = dict(
    original=p('Excess-3 코드의 특징과 사용이유에 대해서 설명하시오.') + p('Describe the characteristics of Excess-3 code. And explain the reason why the Excess-3 code is used.'),
    conditions='',
    ask=p('Excess-3 코드가 무엇인지, 어떤 특징이 있어 왜 쓰는지 설명하세요.'),
    problem_figures=[],
    hints=[dict(label='비교할 것', html=p('BCD와 비교하세요. 각 코드에 더해진 값이 무엇이고, 비트를 뒤집으면 어떤 수가 되는지 몇 개만 계산해 보세요.'))],
    solution=dict(steps=[
        step('풀이', p('Excess-3 코드는 십진수 한 자리를 BCD로 쓴 값에 3(0011)을 더한 코드예요. 0→0011, 1→0100, …, 9→1100이에요.')),
        step('특징', ul(['어떤 숫자의 코드를 비트마다 뒤집으면 9의 보수의 코드가 돼요. 예: 2→0101, 뒤집으면 1010=7의 코드이고 9−2=7이에요.',
                       '어느 숫자도 0000으로 쓰지 않아요. 최소 코드가 0011이에요.'])),
        step('사용 이유', p('비트 반전만으로 9의 보수를 얻어서 십진 감산 회로가 쉬워져요. 0000이 숫자 코드로 쓰이지 않아서 모든 비트가 0인 상태를 데이터 없음·신호 끊김과 구별할 수 있어요.')),
        step('검산', chk('9의 보수 짝 (0,9), (1,8), (2,7), (3,6), (4,5)에서 코드를 비트 반전하면 서로 짝의 코드가 나와요. 예: 3→0110, 뒤집으면 1001=6의 코드.')),
        step('흔한 실수', mist('Excess-3를 “BCD에 3을 곱한 것”이나 “이진수에 3을 더한 일반 이진수”로 설명하지 않도록 해요. 십진 한 자리 BCD에 3을 더하는 코드예요.')),
    ], answer=p('십진 한 자리의 BCD에 3을 더한 코드예요. 비트 반전이 9의 보수라서 감산에 유리하고, 0000이 숫자 코드가 아니라서 신호 없음과 구별돼요.')),
    notes=['제공 답안은 “감산에 유리, 신호두절 구별, 반올림에도 유용, 비트 반전으로 9의 보수”라고 써요. 이 중 “반올림에도 유용”은 여기서 확인하지 않았어요.'])

# ------------------------------------------------------------ q-excess3-enc-exam / 6row
EX_H = ['SW', 'Bit3', 'Bit2', 'Bit1', 'Bit0']


def ex_rows(words, answer):
    out = []
    for w in words:
        row = [w]
        if answer:
            row += [str(b) for b in excess3_circuit(sw_word(w))]
        else:
            row += [''] * 4
        out.append(row)
    return out


def ex_problem(pid, words, orig_extra, note_extra, figure_id):
    ans = ex_rows(words, True)
    return dict(
        original=p('10진 Excess 3코드 Encoder의 회로를 보고 Truth table을 완성하시오.()') + orig_extra + blank_table(EX_H, ex_rows(words, False)),
        conditions=p('회로는 아래 그림과 같아요. SW5~SW0은 십진수 5~0을 나타내는 스위치이고 NOT 6개와 4입력 NAND 4개(74HC20)로 되어 있어요. 스위치를 VCC에 연결하면 그 입력은 1, 아니면 0이에요. 표의 SW 열은 왼쪽부터 SW5, SW4, …, SW0의 값이에요. NAND의 남는 입력은 VCC에 연결돼 있어요.'),
        ask=p('표의 Bit3~Bit0 값을 채우세요.'),
        problem_figures=[figure_id],
        hints=[dict(label='식으로 바꾸기', html=p('NAND 앞의 NOT과 드모르간 법칙을 이용하면 각 Bit가 어떤 스위치들의 OR인지 알 수 있어요. 한 스위치만 1인 행에서는 그 스위치가 들어간 Bit만 1이에요.'))],
        solution=dict(steps=[
            step('회로 읽기', p('Bit3 NAND에는 SW5의 반전이, Bit2에는 SW4·SW3·SW2·SW1의 반전이, Bit1에는 SW4·SW3·SW0의 반전이, Bit0에는 SW4·SW2·SW0의 반전이 들어가요(남는 입력은 VCC). NAND(X′, Y′, …)=X+Y+…이므로 각 Bit는 연결된 스위치들의 OR예요.')),
            step('식', tex(r'\mathrm{Bit3}=SW5,\ \mathrm{Bit2}=SW1+SW2+SW3+SW4,\ \mathrm{Bit1}=SW0+SW3+SW4,\ \mathrm{Bit0}=SW0+SW2+SW4')),
            step('완성한 표', blank_table(EX_H, ans)),
            step('검산·주의', p('<strong>검산:</strong> 각 행이 십진수+3의 4비트와 같아요(SW5만 켜면 5+3=8=1000). <strong>흔한 실수:</strong> SW 열을 오른쪽부터 SW5로 읽으면 행이 뒤바뀌어요. 표 열은 왼쪽이 SW5예요.' + note_extra)),
        ], answer=p('; '.join(f'{r[0]} → {"".join(r[1:])}' for r in ans))),
        notes=[])


P['q-excess3-enc-exam'] = ex_problem(
    'q-excess3-enc-exam', ['000001', '000100', '010000', '100000'],
    p('Referring to the circuit diagram below (decimal excess-3 code encoder), fill in the blanks of the truth table.'),
    '', 'q-excess3-enc-exam-given-01')
P['q-excess3-enc-exam']['notes'] = ['원문은 SW 열의 비트 순서를 적지 않았어요. 회로 그림의 SW5가 위, SW0이 아래라서 왼쪽이 SW5라고 읽었어요. 반대로 읽으면 행 순서만 바뀌어요.']
P['q-excess3-enc-6row'] = ex_problem(
    'q-excess3-enc-6row', ['000001', '000010', '000100', '001000', '010000', '100000'],
    '', '', 'q-excess3-enc-6row-given-01')
P['q-excess3-enc-6row']['notes'] = ['예상문제 원문에는 어느 판에도 답이 없어요. 회로 계산으로 구했어요. SW 열 읽기는 기출 4행판과 같아요.']

# ------------------------------------------------------------ q-1of4-excess3
rows_q = [['1000', '->', ''], ['0100', '->', ''], ['0010', '->', '']]
rows_a = [['1000', '->', '0011'], ['0100', '->', '0100'], ['0010', '->', '0101']]
P['q-1of4-excess3'] = dict(
    original=p('다음 1-out-of-4 코드를 Excess-3 코드로 변환 하시오.') + blank_table(['D0D1D2D3', '', 'Excess-3'], rows_q),
    conditions=p('1-out-of-4 코드는 네 비트 중 한 비트만 1인 코드(one-hot)예요. D0D1D2D3에서 왼쪽이 D0이고, 1이 있는 자리의 번호가 십진수 0~3을 뜻해요.'),
    ask=p('세 행을 Excess-3 코드(4비트)로 바꾸세요.'),
    problem_figures=[],
    hints=[dict(label='번호 먼저', html=p('각 행에서 1이 몇 번째 자리(D0부터)인지 십진수로 바꾼 다음, Excess-3 코드의 정의를 적용하세요.'))],
    solution=dict(steps=[
        step('풀이', p('1000은 D0 자리가 1이라서 숫자 0, 0100은 D1 자리라서 숫자 1, 0010은 D2 자리라서 숫자 2예요. Excess-3 코드는 숫자+3의 4비트라서 0→0011, 1→0100, 2→0101이에요.')),
        step('완성한 표', blank_table(['D0D1D2D3', '', 'Excess-3'], rows_a)),
        step('검산', chk('0+3=3=0011, 1+3=4=0100, 2+3=5=0101.')),
        step('흔한 실수', mist('1000을 이진수 8로 읽어 1011을 쓰면 안 돼요. 이 문제의 입력은 이진수가 아니라 1의 위치를 나타내는 one-hot 코드예요.')),
    ], answer=p('1000 → 0011, 0100 → 0100, 0010 → 0101')),
    notes=['같은 틀의 채점본에서는 입력 이름이 BCD로 수기 수정되고 세 번째 행이 0001로 인쇄되어 있어 읽기 불확실로 보류했어요. 그 판을 BCD로 읽으면 1000→1011, 0100→0111, 0001→0100이에요.'])

# ------------------------------------------------------------ q-prio-vs-binary
P['q-prio-vs-binary'] = dict(
    original=p('Priority encoder의 특징을 Binary encoder와 비교하여 설명하시오.'),
    conditions='',
    ask=p('여러 입력이 동시에 1일 때 두 인코더의 출력이 어떻게 다른지 설명하세요.'),
    problem_figures=[],
    hints=[dict(label='동시 입력', html=p('입력 두 개가 동시에 1인 경우를 하나 정해 두 인코더에 각각 넣어 보세요.'))],
    solution=dict(steps=[
        step('풀이', p('Binary(일반) 인코더는 한 줄만 켜진다고 가정해서 출력 비트를 “그 비트가 1인 번호들의 OR”로 만들어요. 8×3에서 D1과 D2가 동시에 1이면 A1=1, A0=1이라서 011이 나오고, 이는 1도 2도 아닌 3의 코드예요.')),
        step('우선순위 인코더', p('Priority 인코더는 동시에 켜진 입력 중 우선순위가 가장 높은 입력만 코드로 내요. 번호가 큰 쪽이 우선이면 D1과 D2가 동시에 1일 때 D2의 코드 010이 나와요.')),
        step('검산', chk('8×3 일반 인코더 식 A1=D2+D3+D6+D7, A0=D1+D3+D5+D7에 D1=D2=1을 넣으면 A2A1A0=011이에요.')),
        step('흔한 실수', mist('우선순위 인코더가 모든 입력을 합쳐 계산한다고 쓰면 반대예요. 하나만 골라요.')),
    ], answer=p('동시에 여러 입력이 1이면 Binary 인코더는 엉뚱한 코드를 내고, Priority 인코더는 우선순위가 높은 입력의 코드만 내요.')),
    notes=['제공 답안(“다수의 H가 동시에 입력되었을 때 Binary encoder는 undesirable한 결과, Priority encoder는 우선순위에 따라 출력이 정해짐”)과 같은 요지예요. 채점본의 응시자 손글씨 답안은 일부 판독이 불확실해 쓰지 않았어요.'])

# ------------------------------------------------------------ q-demux-from-dec (+ graded)
DEMUX_TABLE = blank_table(['S1', 'S0', 'D', 'Y3', 'Y2', 'Y1', 'Y0'],
                          [['0', '0', '1', '0', '0', '0', '1'], ['0', '1', '1', '0', '0', '1', '0'], ['1', '0', '1', '0', '1', '0', '0'], ['1', '1', '1', '1', '0', '0', '0'], ['x', 'x', '0', '0', '0', '0', '0']])


def demux_steps(pid):
    return [
        step('풀이', p('디코더의 AND 네 개는 위에서부터 S1S0=00, 01, 10, 11을 골라내요. 각 AND에 데이터 D를 입력으로 하나 더 넣으면 선택된 AND만 D를 통과시켜요. AND를 3입력으로 바꾸고 D를 네 AND 모두에 연결해요.')),
        step('완성 회로', img_sol(pid, '디코더를 활용한 1×4 디멀티플렉서 회로', 260)),
        step('논리식', tex(r'Y_0=\overline{S_1}\,\overline{S_0}D,\ Y_1=\overline{S_1}S_0D,\ Y_2=S_1\overline{S_0}D,\ Y_3=S_1S_0D')),
    ]


P['q-demux-from-dec'] = dict(
    original=p('아래의 2 to 4 Decoder의 Gate 회로를 활용하여 1 to 4 Demultiplexer의 Gate회로를 작성하시오.'),
    conditions=p('그림은 선택 입력 S0, S1과 NOT 2개, 2입력 AND 4개로 이루어진 2 to 4 디코더 게이트 회로예요. 출력 네 줄에는 이름이 없어요.'),
    ask=p('데이터 입력 D를 추가해 1 to 4 디멀티플렉서의 게이트 회로를 그리고 출력 식을 쓰세요.'),
    problem_figures=['q-demux-from-dec-given-01'],
    hints=[dict(label='바꿀 곳', html=p('디코더의 출력은 선택된 한 줄만 1이에요. 그 1 대신 데이터 D가 나오게 하려면 각 AND에 무엇을 더해야 할지 생각하세요.'))],
    solution=dict(steps=demux_steps('q-demux-from-dec') + [
        step('검산·주의', p('<strong>검산:</strong> S1S0=10, D=1이면 Y2만 1이고 D=0이면 모두 0이에요. <strong>흔한 실수:</strong> D를 일부 AND에만 연결하거나 NOT에 넣지 않아요.')),
    ], answer=p('AND를 3입력으로 바꾸고 D를 모두에 연결해요. Y0=S1′S0′D, Y1=S1′S0D, Y2=S1S0′D, Y3=S1S0D')),
    notes=['제공 답안 회로(+5V 스위치 S0·S1·D, 74HC04 2개, 74HC11 3입력 AND 4개, 출력 Y0~Y3)와 같은 구조예요.'])

P['q-demux-from-dec-graded'] = dict(
    original=p('2. 아래의 2 to 4 Decoder의 Gate 회로를 활용하여 1 to 4 Demultiplexer의 Gate회로를 작성하시오.(2점.)') + p('두 회로 간에 어떠한 차이가 있는가?(2점.) (총 4점)'),
    conditions=p('원문의 회로 그림은 채점 표시가 섞여 있어 이 문제지에는 싣지 않았어요. 그림은 선택 입력 S0, S1과 NOT 2개, 2입력 AND 4개로 이루어진 2 to 4 디코더 게이트 회로예요.'),
    ask=p('(1) 디코더 회로를 활용해 1 to 4 디멀티플렉서 회로를 작성하세요. (2) 두 회로 사이의 차이를 설명하세요.'),
    problem_figures=[],
    hints=[dict(label='차이를 볼 곳', html=p('두 회로의 입력 신호 종류와 개수, AND 게이트의 입력 수, 출력이 켜지는 조건을 각각 비교해 보세요.'))],
    solution=dict(steps=demux_steps('q-demux-from-dec-graded') + [
        step('두 회로의 차이', ul(['디멀티플렉서에는 데이터 입력 D가 하나 더 있고 AND가 2입력에서 3입력이 돼요.',
                              '디코더는 코드만으로 항상 한 출력이 1이지만, 디멀티플렉서의 선택된 출력은 D를 따라가서 D=0이면 모두 0이에요. D=1이면 디코더와 같아요.'])),
        step('주의', p('<strong>흔한 실수:</strong> 입력 개수만 비교하면 부족해요. 선택선과 데이터선의 역할 차이를 함께 써요.')),
    ], answer=p('(1) AND를 3입력으로 바꾸고 D를 연결: Yk=(S1S0가 k인 조건)·D. (2) 디멀티플렉서에는 데이터 입력 D가 있고 선택된 출력이 D를 따르며, D=1이면 디코더와 같아요.')),
    notes=['채점본 응시자 손글씨 답안(블록도와 “Decoder vs DMUX” 비교표)은 부분 판독이라 정답으로 쓰지 않았어요. 개념 메모 자료의 “디코더는 입력에 따라 하나의 출력, 디멀티플렉서는 선택선에 따라 하나의 출력 활성화”는 후보로만 연결해 두었어요.'])

# ------------------------------------------------------------ q-74hc148-table
rows_q = [['L', 'H', 'H', 'H', 'H', 'H', 'H', 'H', 'H', 'H', 'H', 'H'],
          ['L', 'L', 'H', 'L', 'H', 'L', 'H', 'L', 'H', '', '', ''],
          ['L', 'H', 'L', 'H', 'L', 'H', 'L', 'H', 'L', '', '', '']]


def lh(t):
    return ''.join('L' if b == 0 else 'H' for b in t)


rows_a = [rows_q[0],
          rows_q[1][:9] + list(lh(hc148(row2))),
          rows_q[2][:9] + list(lh(hc148(row3)))]
H148 = ['E1', '0', '1', '2', '3', '4', '5', '6', '7', 'A2', 'A1', 'A0']
P['q-74hc148-table'] = dict(
    original=p('아래 회로는 74HC148을 활용하여 설계한 8x3 Priority Encoder 이다. 아래의 Table을 완성하시오.') + blank_table(H148, rows_q) + p('(원문 표의 첫 행은 출력까지 이미 채워져 있어요. 표 머리 input은 E1, 0~7, output은 A2 A1 A0예요.)'),
    conditions=p('스위치 두 개가 IN0~IN7을 짝수 번호끼리, 홀수 번호끼리 묶어 구동하고, EI(표의 E1)는 GND에 연결돼 있어요. 74HC148은 입력, EI, 출력이 모두 Low가 활성인 칩이에요. 번호가 큰 입력이 우선이에요(교안 p11).'),
    ask=p('둘째 행과 셋째 행의 A2 A1 A0를 H 또는 L로 채우세요.'),
    problem_figures=['q-74hc148-table-given-01'],
    hints=[dict(label='세 단계', html=p('Low인 입력을 모두 찾고, 그중 번호가 가장 큰 입력을 고른 다음, 그 번호를 이진수로 쓴 뒤 비트를 뒤집어 H/L로 바꿔요.'))],
    solution=dict(steps=[
        step('풀이', p('둘째 행은 IN0, IN2, IN4, IN6이 L이에요. 가장 큰 번호는 6이고 110이에요. Active Low 출력은 비트를 뒤집어 001, 즉 A2 A1 A0=L L H예요. 셋째 행은 IN1, IN3, IN5, IN7이 L이고 가장 큰 번호가 7이에요. 111을 뒤집으면 000, 즉 L L L이에요.')),
        step('완성한 표', blank_table(H148, rows_a)),
        step('검산', chk('첫 행처럼 모든 입력이 H이면 A2 A1 A0=H H H예요. 교안 p11의 표에서 IN7=L이면 L L L이고, IN7=H, IN6=L이면 L L H라서 같은 규칙이에요.')),
        step('흔한 실수', mist('H를 1, L을 0으로 읽은 다음 비트를 뒤집지 않으면 반대 코드가 나와요. 또 가장 작은 번호(IN0)를 우선으로 읽으면 안 돼요.')),
    ], answer=p('둘째 행 L L H, 셋째 행 L L L')),
    notes=['제공 답안과 같아요. 퀴즈 해설 자료의 “IN0가 가장 높은 우선순위”라는 문장은 같은 해설의 둘째 행 설명(6번 L, 7번 H일 때 LLH)과 맞지 않아 쓰지 않았어요.'])

# ------------------------------------------------------------ q-quiz-dec2x4-table
rows_q = [['0', '0', '', '', '', ''], ['1', '0', '', '', '', ''], ['0', '1', '', '', '', ''], ['1', '1', '', '', '', '']]
rows_a = []
for b0, b1 in [(0, 0), (1, 0), (0, 1), (1, 1)]:
    d1 = b0 & b1
    d2 = (1 - b0) & b1
    d3 = b0 & (1 - b1)
    d4 = (1 - b0) & (1 - b1)
    rows_a.append([str(b0), str(b1), str(d1), str(d2), str(d3), str(d4)])
assert rows_a == [['0', '0', '0', '0', '0', '1'], ['1', '0', '0', '0', '1', '0'], ['0', '1', '0', '1', '0', '0'], ['1', '1', '1', '0', '0', '0']]
CON = table(['게이트', '입력 1', '입력 2', '출력'],
            [['U2A (74HC08)', 'SW1', 'SW2', 'D1'], ['U2B', 'U1A 출력 (SW1 반전)', 'SW2', 'D2'],
             ['U2C', 'SW1', 'U1B 출력 (SW2 반전)', 'D3'], ['U2D', 'U1A 출력', 'U1B 출력', 'D4']])
P['q-quiz-dec2x4-table'] = dict(
    original=p('1. 2X4 Decoder의 회로를 보고 Truth table을 완성하시오.'),
    conditions=p('원문 회로 그림은 해설이 같은 쪽에 섞여 있어 이 문제지에는 싣지 않고 글로 옮겼어요. 스위치 SW1(= bit0)과 SW2(= bit1)가 입력이고, 스위치를 VCC에 연결하면 1이에요. U1A(74HC04)는 SW1을, U1B는 SW2를 반전해요. 네 AND(74HC08)의 출력은 저항 330Ω을 거쳐 LED D1~D4에 연결돼 있고, 출력이 1이면 해당 LED가 켜져요.') + CON,
    ask=p('bit0, bit1의 네 가지 조합마다 D1~D4의 값을 채우세요. (표의 입력은 bit0, bit1 순서로 00, 10, 01, 11이에요.)'),
    problem_figures=[],
    hints=[dict(label='출력별 식', html=p('먼저 D1~D4 각각이 bit0와 bit1의 어떤 AND인지 식으로 쓰세요. 그다음 입력 조합을 하나씩 넣어요.'))],
    solution=dict(steps=[
        step('식 세우기', tex(r'D_1=b_0b_1,\ D_2=\overline{b_0}\,b_1,\ D_3=b_0\overline{b_1},\ D_4=\overline{b_0}\,\overline{b_1}')),
        step('완성한 표', blank_table(['bit0', 'bit1', 'D1', 'D2', 'D3', 'D4'], rows_a)),
        step('검산', chk('각 행에서 1이 정확히 하나이고, 그 출력은 입력 조합과 맞는 AND예요. 예: bit0=1, bit1=0이면 D3만 켜져요.')),
        step('흔한 실수', mist('D1~D4의 번호를 입력 번호와 같다고 읽으면 안 돼요. 이 회로에서 D1이 입력 11, D4가 입력 00에 대응해요. bit0와 bit1이 표에서 bit0가 먼저 나오는 점도 확인해요.')),
    ], answer=p('00 → D4만 1, 10 → D3만 1, 01 → D2만 1, 11 → D1만 1 (bit0 bit1 순서)')),
    notes=['제공 답안 표(bit0 bit1 D1 D2 D3 D4: 00→0001, 10→0010, 01→0100, 11→1000)와 같아요. 회로 배선은 저해상도 원문 그림을 확대해 읽었어요. 원문 그림에는 정답 표가 같은 쪽에 있어 문제지에는 글로만 옮겼어요.'])

# ------------------------------------------------------------ definitions / short answers
P['q-sa-decoder-def'] = dict(
    original=p('Decoder에 대해서 설명하시오.'),
    conditions='',
    ask=p('디코더가 무엇인지 입력과 출력을 포함해 설명하세요.'),
    problem_figures=[],
    hints=[dict(label='담을 내용', html=p('입력 비트 수와 출력 개수의 관계, 그리고 출력 중 몇 개가 활성화되는지를 써요.'))],
    solution=dict(steps=[
        step('풀이', p('디코더는 n비트 이진 코드를 입력받아 2ⁿ개의 서로 다른 출력 중 그 코드에 해당하는 하나만 활성화하는 조합 논리회로예요. 입력 n개, 출력 m개이면 n×m 디코더라고 불러요.')),
        step('예', p('2×4 디코더는 A1A0=10이면 D2만 1이에요. 메모리나 I/O 장치 중 하나를 고르는 데 써요.')),
        step('검산', chk('3비트 입력이면 출력은 2³=8개이고 한 번에 하나만 활성화돼요.')),
        step('흔한 실수', mist('출력이 여러 개 동시에 켜진다고 쓰면 안 돼요. 일반 디코더는 입력 코드 하나에 출력 한 줄이에요.')),
    ], answer=p('n비트 이진 코드를 2ⁿ개의 서로 다른 정보(한 줄 활성화)로 바꾸는 조합 논리회로예요.')),
    notes=['제공 답안과 교안 p3의 정의가 같아요.'])

P['q-sa-encoder-def'] = dict(
    original=p('Encoder에 대해서 설명하시오.'),
    conditions='',
    ask=p('인코더가 무엇인지 입력과 출력을 포함해 설명하세요.'),
    problem_figures=[],
    hints=[dict(label='담을 내용', html=p('디코더와 반대 방향이라는 점과 입력 개수와 출력 비트 수의 관계를 써요.'))],
    solution=dict(steps=[
        step('풀이', p('인코더는 2ⁿ개의 입력 중 하나가 활성화되면 그 위치 정보를 n비트 이진 코드로 바꾸는 조합 논리회로예요. 입력 m개, 출력 n개이면 m×n 인코더라고 불러요.')),
        step('예', p('8×3 인코더는 D5만 1이면 A2A1A0=101을 출력해요. 키보드 입력 처리나 인터럽트 식별에 써요.')),
        step('검산', chk('8개 입력이면 출력은 3비트(2³=8)예요.')),
        step('흔한 실수', mist('여러 입력이 동시에 켜지는 경우를 처리하지 못한다는 한계도 함께 알아 둬요. 그때는 우선순위 인코더가 필요해요.')),
    ], answer=p('2ⁿ개 입력 중 활성화된 하나의 위치를 n비트 이진 코드로 바꾸는 조합 논리회로예요.')),
    notes=['제공 답안은 “10진수나 8진수를 입력으로 받아 2진수나 BCD 같은 코드로 변환”이라고 써요. 교안 p5의 정의(활성 입력의 위치를 n비트 코드로 변환)와 같은 뜻의 설명이에요.'])

enc8 = []
for k in range(8):
    enc8.append([str(int(j == k)) for j in (7, 6, 5, 4, 3, 2, 1, 0)] + list(format(k, '03b')))
P['q-sa-enc8x3'] = dict(
    original=p('8X3 Encoder 진리표작성'),
    conditions=p('입력 D7~D0 중 한 줄만 1이라고 가정해요. 출력은 A2A1A0예요.'),
    ask=p('입력 여덟 가지에 대한 진리표를 작성하세요.'),
    problem_figures=[],
    hints=[dict(label='행 만들기', html=p('행마다 D0부터 D7까지 한 줄씩 1로 두고, 그 번호를 이진수로 바꿔 출력에 써요.'))],
    solution=dict(steps=[
        step('풀이', p('D0이 1이면 000, D1이 1이면 001, … D7이 1이면 111이에요.')),
        step('완성한 표', blank_table(['D7', 'D6', 'D5', 'D4', 'D3', 'D2', 'D1', 'D0', 'A2', 'A1', 'A0'], enc8[::1])),
        step('식', tex(r'A_2=D_4+D_5+D_6+D_7,\ A_1=D_2+D_3+D_6+D_7,\ A_0=D_1+D_3+D_5+D_7')),
        step('검산', chk('각 출력 비트가 1인 행의 입력 번호들이 위 OR 식에 들어 있어요.')),
        step('흔한 실수', mist('한 줄만 켜진 여덟 행만 정해진 표예요. 두 줄 이상이 켜진 입력은 이 표가 정하지 않아요.')),
    ], answer=p('Dk만 1이면 A2A1A0는 k의 3비트 이진수예요 (D0→000, …, D7→111).')),
    notes=['제공 답안 표와 같아요. 원문에는 표 틀이 없어 진리표 전체를 새로 작성하는 문제로 읽었어요.'])

P['q-sa-prio-why'] = dict(
    original=p('Priority Encoder에 대해서 설명하시오(사용이유)'),
    conditions='',
    ask=p('우선순위 인코더를 왜 쓰는지 설명하세요.'),
    problem_figures=[],
    hints=[dict(label='문제 상황', html=p('일반 인코더에 입력 두 개가 동시에 들어오면 어떤 코드가 나오는지 하나만 계산해 보세요.'))],
    solution=dict(steps=[
        step('풀이', p('일반 인코더는 한 번에 하나의 입력만 켜진다고 가정해요. 8×3 일반 인코더에서 D1과 D2가 동시에 켜지면 출력이 011(=3)이 되어 1도 2도 아닌 값이 나와요. 우선순위 인코더는 동시에 켜진 입력 중 우선순위가 높은 입력의 코드만 내보내서 이 문제를 없애요.')),
        step('검산', chk('A1=D2+D3+D6+D7=1, A0=D1+D3+D5+D7=1, A2=0이라서 011이에요.')),
        step('흔한 실수', mist('우선순위 인코더가 입력 개수를 줄여 주는 회로라고 쓰면 안 돼요. 동시 입력의 충돌을 해결해요.')),
    ], answer=p('여러 입력이 동시에 활성일 때 우선순위가 높은 입력 하나를 선택해 올바른 코드를 내기 위해 써요.')),
    notes=['제공 답안(“우선순위가 가장 높은 것을 먼저 실행하기 위해서”)과 같은 요지예요.'])

P['q-sa-74hc143'] = dict(
    original=p('74HC143은 Priority Encoder이다. 각 Output port A0, A1, A2, GS, EO에 대해서 설명하시오.'),
    conditions=p('원문은 칩 이름을 74HC143으로 적었어요. 교안에서 쓰는 우선순위 인코더 IC는 74HC148이고, 핀 이름 A0~A2, GS, EO가 같아서 74HC148의 핀으로 읽어요.'),
    ask=p('다섯 출력 핀의 역할을 각각 설명하세요.'),
    problem_figures=[],
    hints=[dict(label='나눠 보기', html=p('A0~A2는 하나의 묶음이에요. GS와 EO는 각각 “입력이 있나”와 “다음 칩에 넘길 enable”과 관련이 있어요.'))],
    solution=dict(steps=[
        step('풀이', ul(['A0, A1, A2: 우선순위가 가장 높은 활성 입력의 번호를 나타내는 3비트 데이터 출력이에요. Active Low라서 이진수를 비트마다 뒤집은 값이 나와요.',
                       'GS: Priority Flag 출력이에요. EI가 Low이고 하나 이상의 입력이 활성(Low)일 때 Low가 되어 “입력이 있다”를 알려요.',
                       'EO: Enable 출력이에요. EI가 Low이고 모든 입력이 High일 때 Low가 되어 다음 칩의 EI에 연결해 칩을 이어 붙일 때 써요.'])),
        step('검산', chk('IN0만 Low일 때와 모두 High일 때 A2A1A0는 같은 HHH예요. 두 경우는 GS(Low/High)로 구분할 수 있어요.')),
        step('흔한 실수', mist('GS를 번호를 나타내는 네 번째 비트로 쓰면 안 돼요. 코드는 A2A1A0 세 핀이에요.')),
    ], answer=p('A0~A2는 데이터 출력, GS는 Priority Flag 출력, EO는 Enable 출력이에요.')),
    notes=['제공 답안(A0~A2 Data Output, GS Priority Flag Output, EO Enable Output)과 같아요. GS와 EO의 Low 조건은 이 저장소에 74HC148 데이터시트가 없어 일반적인 74HC148 설명 기준이에요.'])

PROBLEM_TOPICS = {
    'q-dec3x8': ['t-decoder'], 'q-prio-onehot': ['t-priority'], 'q-prio-exam': ['t-priority'],
    'q-dec2x4-design': ['t-decoder'], 'q-enc4x2-design': ['t-encoder'], 'q-excess3-why': ['t-excess3'],
    'q-excess3-enc-exam': ['t-excess3'], 'q-excess3-enc-6row': ['t-excess3'], 'q-1of4-excess3': ['t-excess3'],
    'q-prio-vs-binary': ['t-priority', 't-encoder'], 'q-demux-from-dec': ['t-demux'], 'q-demux-from-dec-graded': ['t-demux'],
    'q-74hc148-table': ['t-priority'], 'q-quiz-dec2x4-table': ['t-decoder'], 'q-sa-decoder-def': ['t-decoder'],
    'q-sa-encoder-def': ['t-encoder'], 'q-sa-enc8x3': ['t-encoder'], 'q-sa-prio-why': ['t-priority', 't-encoder'],
    'q-sa-74hc143': ['t-priority'],
}
TITLES = {
    'q-dec3x8': '3×8 디코더의 진리표', 'q-prio-onehot': '8×3 우선순위 인코더 — 한 줄만 켜진 입력', 'q-prio-exam': '8×3 우선순위 인코더 — 여러 비트가 켜진 입력',
    'q-dec2x4-design': '2×4 디코더의 게이트 설계', 'q-enc4x2-design': '4×2 인코더의 NAND 설계', 'q-excess3-why': 'Excess-3 코드의 특징과 사용 이유',
    'q-excess3-enc-exam': 'Excess-3 인코더 회로의 진리표(네 행)', 'q-excess3-enc-6row': 'Excess-3 인코더 회로의 진리표(여섯 행)',
    'q-1of4-excess3': '1-out-of-4 코드를 Excess-3로 변환', 'q-prio-vs-binary': '우선순위 인코더와 Binary 인코더의 비교',
    'q-demux-from-dec': '디코더 회로로 1 to 4 디멀티플렉서 만들기', 'q-demux-from-dec-graded': '디코더로 DMUX 만들기와 두 회로의 차이',
    'q-74hc148-table': '74HC148 우선순위 인코더의 진리표', 'q-quiz-dec2x4-table': '2×4 디코더 회로의 진리표',
    'q-sa-decoder-def': 'Decoder를 설명', 'q-sa-encoder-def': 'Encoder를 설명', 'q-sa-enc8x3': '8×3 인코더 진리표',
    'q-sa-prio-why': 'Priority Encoder의 사용 이유', 'q-sa-74hc143': '우선순위 인코더 IC의 출력 핀',
}
DERIVED = {
    'q-dec3x8': 'A=k이면 Dk만 1 (000→D0, …, 111→D7)',
    'q-prio-onehot': 'Dk→k의 3비트 이진수 (D0→000, …, D7→111)',
    'q-prio-exam': '0011 1010→101, 0101 1110→110, 0001 1101→100, 0110 0100→110, 1111 1111→111 (번호가 큰 입력 우선)',
    'q-dec2x4-design': 'O0=I1′I0′, O1=I1′I0, O2=I1I0′, O3=I1I0',
    'q-enc4x2-design': 'A=D2+D3, B=D1+D3 (NOT 4, 4입력 NAND 3, 2입력 NAND 2)',
    'q-excess3-why': '십진 한 자리 BCD+3; 비트 반전=9의 보수; 0000 미사용',
    'q-excess3-enc-exam': '000001→0011, 000100→0101, 010000→0111, 100000→1000',
    'q-excess3-enc-6row': '000001→0011, 000010→0100, 000100→0101, 001000→0110, 010000→0111, 100000→1000',
    'q-1of4-excess3': '1000→0011, 0100→0100, 0010→0101',
    'q-prio-vs-binary': '동시 입력 시 Binary는 잘못된 코드, Priority는 우선순위가 높은 입력의 코드',
    'q-demux-from-dec': 'AND를 3입력으로 바꾸고 D 연결: Y0=S1′S0′D, Y1=S1′S0D, Y2=S1S0′D, Y3=S1S0D',
    'q-demux-from-dec-graded': 'AND 3입력+D 연결; 차이: 데이터 입력 D의 유무, D=1이면 디코더와 같음',
    'q-74hc148-table': '둘째 행 LLH, 셋째 행 LLL',
    'q-quiz-dec2x4-table': '00→D4, 10→D3, 01→D2, 11→D1만 1',
    'q-sa-decoder-def': 'n비트 코드를 2ⁿ개 중 한 줄 활성화',
    'q-sa-encoder-def': '2ⁿ개 입력 중 활성 입력 위치를 n비트 코드로',
    'q-sa-enc8x3': 'Dk→k의 3비트 이진수',
    'q-sa-prio-why': '동시 입력 충돌 해결: 우선순위가 높은 입력 선택',
    'q-sa-74hc143': 'A0~A2 데이터 출력, GS Priority Flag, EO Enable 출력',
}
