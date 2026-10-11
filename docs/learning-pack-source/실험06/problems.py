"""Workbook entries for 실험06. Every table answer is checked against a gate-level model."""
from h import *

# ---------------------------------------------------------------- gate-level models (unit delay)
def nand(*x):
    return 0 if all(x) else 1


def run(step, state, inputs, limit=60):
    """Iterate a synchronous unit-delay netlist until it stops changing. Returns final state or None (oscillates)."""
    seen = []
    for _ in range(limit):
        new = step(state, inputs)
        if new == state:
            return state
        if new in seen:
            return None
        seen.append(state)
        state = new
    return None


def sr_step(st, i):
    a, b, q, qb = st
    return (nand(i['S'], i['E']), nand(i['R'], i['E']), nand(a, qb), nand(b, q))


def jk_step(st, i):
    a, b, q, qb = st
    return (nand(i['J'], i['E'], qb), nand(i['K'], i['E'], q), nand(a, qb), nand(b, q))


def basic_step(st, i):
    q, qb = st
    return (nand(i['S'], qb), nand(i['R'], q))


def gated(step, q, inputs, hold):
    """Start from a settled hold state with output q, then apply inputs."""
    st = run(step, (1, 1, q, 1 - q), hold)
    assert st is not None
    out = run(step, st, inputs)
    return None if out is None else out[2:]


SR_HOLD = dict(S=0, R=0, E=0)
for q0 in (0, 1):
    for s, r in ((0, 0), (0, 1), (1, 0), (1, 1)):
        assert gated(sr_step, q0, dict(S=s, R=r, E=0), SR_HOLD) == (q0, 1 - q0)
    assert gated(sr_step, q0, dict(S=0, R=0, E=1), SR_HOLD) == (q0, 1 - q0)
    assert gated(sr_step, q0, dict(S=0, R=1, E=1), SR_HOLD) == (0, 1)
    assert gated(sr_step, q0, dict(S=1, R=0, E=1), SR_HOLD) == (1, 0)
    assert gated(sr_step, q0, dict(S=1, R=1, E=1), SR_HOLD) == (1, 1)
# after S=R=1, dropping both to 0 at once: the symmetric ideal model never settles (예측 불가)
st11 = run(sr_step, run(sr_step, (1, 1, 0, 1), SR_HOLD), dict(S=1, R=1, E=1))
assert run(sr_step, st11, dict(S=0, R=0, E=1)) is None

# D latch: S=D, R=D′
for q0 in (0, 1):
    for d in (0, 1):
        assert gated(sr_step, q0, dict(S=d, R=1 - d, E=0), SR_HOLD) == (q0, 1 - q0)
        assert gated(sr_step, q0, dict(S=d, R=1 - d, E=1), SR_HOLD) == (d, 1 - d)

# JK latch
JK_HOLD = dict(J=0, K=0, E=0)
for q0 in (0, 1):
    assert gated(jk_step, q0, dict(J=1, K=1, E=0), JK_HOLD) == (q0, 1 - q0)
    assert gated(jk_step, q0, dict(J=0, K=0, E=1), JK_HOLD) == (q0, 1 - q0)
    assert gated(jk_step, q0, dict(J=0, K=1, E=1), JK_HOLD) == (0, 1)
    assert gated(jk_step, q0, dict(J=1, K=0, E=1), JK_HOLD) == (1, 0)
    assert gated(jk_step, q0, dict(J=1, K=1, E=1), JK_HOLD) is None      # race-around while E stays 1


def jk_pulse(q0, width):
    st = run(jk_step, (1, 1, q0, 1 - q0), JK_HOLD)
    for _ in range(width):
        st = jk_step(st, dict(J=1, K=1, E=1))
    st = run(jk_step, st, dict(J=1, K=1, E=0))
    return st[2:]


assert all(jk_pulse(q0, 2) == (1 - q0, q0) for q0 in (0, 1))         # 짧은 펄스: 한 번만 뒤집힘

# basic NAND latch (inputs active low)
for q0 in (0, 1):
    assert run(basic_step, (q0, 1 - q0), dict(S=1, R=1)) == (q0, 1 - q0)
assert run(basic_step, (0, 1), dict(S=0, R=1)) == (1, 0)
assert run(basic_step, (1, 0), dict(S=1, R=0)) == (0, 1)
assert run(basic_step, (0, 1), dict(S=0, R=0)) == (1, 1) == run(basic_step, (1, 0), dict(S=0, R=0))


# 74HC76 behaviour (교안 p11): async PR/CLR active low, falling edge J/K
def hc76(q, pr, clr, edge, j, k):
    if pr == 0 and clr == 1:
        return 1
    if clr == 0 and pr == 1:
        return 0
    assert pr == 1 and clr == 1
    if edge != 'fall':
        return q
    return {(0, 0): q, (0, 1): 0, (1, 0): 1, (1, 1): 1 - q}[(j, k)]


TRACE = [  # step, PR, CLR, CLK, J, K
    (1, 0, 1, 'none1', 0, 0), (2, 1, 1, 'fall', 0, 0), (3, 1, 1, 'rise', 0, 1), (4, 1, 1, 'fall', 0, 1),
    (5, 1, 1, 'fall', 1, 1), (6, 1, 1, 'fall', 1, 1), (7, 1, 1, 'fall', 1, 0), (8, 1, 0, 'none0', 1, 1)]
q = None
TRACE_Q = []
for n, pr, clr, e, j, k in TRACE:
    q = hc76(q, pr, clr, e, j, k)
    TRACE_Q.append(q)
assert TRACE_Q == [1, 1, 1, 0, 1, 0, 1, 0]
CLK_TXT = {'none1': '1 (변화 없음)', 'none0': '0 (변화 없음)', 'fall': '↓', 'rise': '↑'}


# ---------------------------------------------------------------- html helpers
def img_sol(pid, alt, width=400):
    return f'<p><img src="figures/solutions/{pid}-solution-01.png" width="{width}" style="max-width:100%;height:auto" alt="{esc(alt)}"></p>'


def step(label, html):
    return dict(label=label, html=html)


def chk(t):
    return f'<p><strong>검산:</strong> {t}</p>'


def mist(t):
    return f'<p><strong>흔한 실수:</strong> {t}</p>'


P = {}

# ------------------------------------------------------------ 서술형
P['q-diff'] = dict(
    original=p('Latch와 Flip-Flop의 차이점에 대해서 설명하시오.'),
    conditions='', ask=p('입력이 출력에 반영되는 때를 기준으로 두 소자를 비교하세요.'), problem_figures=[],
    hints=[dict(label='비교 기준', html=p('제어 입력이 1인 “동안”과 제어 입력이 바뀌는 “순간” 중 무엇에 반응하는지 생각해요.'))],
    solution=dict(steps=[
        step('공통점', p('둘 다 1비트(Q와 Q′)를 저장하는 기억소자예요. 출력을 되먹여 이전 상태를 유지해요.')),
        step('차이', table(['구분', 'Latch', 'Flip-Flop'],
                         [['트리거', '레벨(Level-triggered)', '엣지(Edge-triggered)'],
                          ['입력 반영', 'Enable이 1인 동안 입력이 바뀔 때마다 출력이 바로 따라 바뀜', '클록의 상승 또는 하강 엣지 순간에만 입력을 받아 출력이 바뀜'],
                          ['교안의 분류', '비동기 기억소자', '동기 기억소자(Clock에 맞춰 동작)']])),
        step('검산', chk('같은 입력 파형(Enable/Clock=1 구간 안에서 D가 두 번 바뀜)을 넣으면 래치는 두 번 다 따라가고, 플립플롭은 엣지에서 한 번만 바뀌는지 그려 보면 차이가 맞아요.')),
        step('흔한 실수', mist('“래치는 클록이 전혀 없다”라고만 쓰면 Enable 래치를 설명하지 못해요. 레벨과 엣지의 차이를 함께 써요.')),
    ], answer=p('Latch는 Enable이 활성인 동안 입력 변화가 바로 출력에 반영되는 레벨 트리거(비동기) 기억소자이고, Flip-Flop은 클록의 엣지 순간에만 입력이 출력에 반영되는 엣지 트리거(동기) 기억소자예요.')),
    notes=['제공 답안들(“latch는 clock과 무관한 비동기식, f/f은 clock에 따라 동작하는 동기식”, 에지/레벨 트리거 구분)과 같은 요지예요. 교안 p4·p5의 분류를 따랐어요.'])

P['q-latch'] = dict(
    original=p('Latch에 대해서 설명하시오.'), conditions='', ask=p('Latch가 무엇을 저장하고 언제 입력을 받아들이는지 설명하세요.'), problem_figures=[],
    hints=[dict(label='세 가지', html=p('무엇을 저장하나, 어떻게 기억하나(되먹임), 언제 입력이 반영되나를 차례로 써요.'))],
    solution=dict(steps=[
        step('풀이', ul(['2진 정보 1비트를 저장하는 기억소자예요. 출력 Q와 Q′은 서로 반대인 두 안정 상태 중 하나를 유지해요.',
                       '출력을 입력으로 되먹이는 구조라서 입력이 사라진 뒤에도 마지막 상태를 지켜요.',
                       '레벨 트리거예요. Enable이 활성(1)인 동안 입력이 바뀌면 출력이 바로 따라 바뀌고, Enable이 0이면 유지해요. 교안은 비동기 기억소자로 분류해요.',
                       '예: SR 래치, D 래치, JK 래치'])),
        step('검산', chk('D 래치에서 E=1, D=1 → Q=1, 이어서 E=0, D=0 → Q=1 유지로 “저장”과 “레벨 반영”을 모두 확인할 수 있어요.')),
        step('흔한 실수', mist('“입력이 변할 때마다 출력이 바뀐다”만 쓰면 Enable=0일 때의 유지를 빠뜨려요.')),
    ], answer=p('Latch는 되먹임으로 1비트를 기억하는 레벨 트리거(비동기) 기억소자예요. Enable이 활성인 동안 입력에 따라 출력이 바로 바뀌고, 비활성이면 마지막 상태를 유지해요.')),
    notes=['제공 답안(비동기 기억소자, 1비트 저장, 상반된 두 상태 유지, Level sensitive device)과 같은 요지예요.'])

P['q-ff'] = dict(
    original=p('Flip-Flop에 대해서 설명하시오.'), conditions='', ask=p('Flip-Flop이 무엇을 저장하고 언제 입력을 받아들이는지 설명하세요.'), problem_figures=[],
    hints=[dict(label='래치와 비교', html=p('저장하는 것은 래치와 같아요. 입력이 반영되는 순간이 달라요.'))],
    solution=dict(steps=[
        step('풀이', ul(['2진 정보 1비트를 저장하는 기억소자이고 Q와 Q′은 서로 반대인 두 안정 상태 중 하나를 유지해요.',
                       '클록을 입력받는 동기 기억소자예요. 클록의 상승 엣지 또는 하강 엣지 순간에만 입력이 출력에 반영되고, 그 사이에는 입력이 바뀌어도 출력이 그대로예요(Edge-triggered).',
                       '예: SR F/F, D F/F(74HC74, 상승 엣지), JK F/F(74HC76, 하강 엣지)'])),
        step('검산', chk('74HC76에서 J=K=1로 두고 클록을 한 번 내리면 Q가 정확히 한 번 뒤집히고, 클록이 0으로 머무는 동안은 그대로예요.')),
        step('흔한 실수', mist('“클록이 1인 동안 입력을 받는다”라고 쓰면 래치(레벨) 설명이 돼요.')),
    ], answer=p('Flip-Flop은 1비트를 기억하는 동기 기억소자로, 클록의 엣지(상승 또는 하강) 순간에만 입력이 출력에 반영되고 그 밖에는 상태를 유지해요.')),
    notes=['제공 답안(동기식 기억소자, Edge sensitive memory element)과 같은 요지예요.'])

# ------------------------------------------------------------ 기본 SR 래치 S=R=0
P['q-sr-nand-00'] = dict(
    original=p('아래의 회로는 기본 S-R latch 회로이다. S와 R이 동시에 0이 입력되면 Q와 Q′의 출력은 무엇인가? Q′ = not Q 등식이 성립하는가?'),
    conditions=p('NAND(74HC00) 두 개의 출력이 서로의 입력에 연결돼 있어요. S는 Q를 내는 NAND, R은 Q′을 내는 NAND에 들어가요. Enable 입력은 없어요.'),
    ask=p('S=R=0일 때 Q와 Q′을 구하고, Q′=not Q가 성립하는지 답하세요.'),
    problem_figures=['q-sr-nand-00-given-01'],
    hints=[dict(label='NAND 성질', html=p('NAND는 입력에 0이 하나라도 있으면 출력이 1이에요. 각 NAND에 0이 들어가는지만 보면 돼요.'))],
    solution=dict(steps=[
        step('풀이', p('S=0이 들어간 위 NAND는 다른 입력과 상관없이 1을 내요. 그래서 Q=1이에요. R=0이 들어간 아래 NAND도 1을 내서 Q′=1이에요.')),
        step('판단', p('Q=1, Q′=1이라 Q′이 Q의 반대가 아니에요. 따라서 Q′=not Q는 성립하지 않아요.')),
        step('검산', chk('되먹임 값을 넣어 다시 계산해도 Q=(0·1)′=1, Q′=(0·1)′=1로 변하지 않아요. 이 상태에서 S·R을 동시에 1로 되돌리면 어느 상태로 남을지 예측할 수 없어서 이 입력을 쓰지 않아요.')),
        step('흔한 실수', mist('Active High SR 래치의 “S=R=0은 유지”를 그대로 적용하면 틀려요. NAND 기본 래치는 S=R=1이 유지이고 S=R=0이 금지 상태예요.')),
    ], answer=p('Q=1, Q′=1이에요. 두 출력이 같아서 Q′=not Q는 성립하지 않아요.')),
    notes=['제공 답안(“Q=1, Q′=1이 출력이 되어서 성립하지 않는다”)과 같아요. NAND 모델 계산으로 확인했어요.'])

# ------------------------------------------------------------ Enable SR 래치 진리표
SR_ROWS_Q = [['0', '0', '1', ''], ['0', '1', '1', ''], ['1', '0', '1', ''], ['1', '1', '1', ''], ['x', 'x', '0', '']]
SR_ROWS_A = [['0', '0', '1', 'Q(t−1)'], ['0', '1', '1', '0 : Reset'], ['1', '0', '1', '1 : Set'], ['1', '1', '1', '1 (Q′도 1, 부정·사용 안 함)'], ['x', 'x', '0', 'Q(t−1)']]
P['q-rs-latch'] = dict(
    original=p('R-S Latch의 Truth table을 완성하시오.'),
    conditions=p('회로는 아래 그림과 같아요. S·C가 첫 NAND, R·C가 둘째 NAND에 들어가고 그 출력이 서로 되먹임된 NAND 두 개로 가요(74HC00 네 개 게이트). C는 Enable 역할이에요. 원문에는 빈 표가 없어요. 풀이하기 쉽게 입력 행만 정리했어요.'),
    ask=p('표의 Q(t)를 채우세요. 부정 행은 회로가 내는 값과 쓰지 않는 이유를 함께 써요.') + table(['S', 'R', 'C', 'Q(t)'], SR_ROWS_Q),
    problem_figures=['q-rs-latch-given-01'],
    hints=[dict(label='C부터', html=p('C=0이면 앞단 NAND 두 개의 출력이 어떻게 되는지 먼저 봐요. 그다음 C=1에서 S·R마다 앞단 출력 → Q 순서로 따라가요.'))],
    solution=dict(steps=[
        step('C=0', p('앞단 NAND에 0이 들어가서 두 출력이 모두 1이에요. 교차 NAND는 1을 받아 서로를 붙잡으니 이전 값 Q(t−1)이 유지돼요.')),
        step('C=1', p('앞단 NAND는 S·R을 뒤집어 전달해요. S=1이면 위 앞단 출력이 0이라 Q=1(Set), R=1이면 아래 앞단 출력이 0이라 Q′=1, Q=0(Reset)이에요. S=R=0이면 앞단 출력이 모두 1이라 유지예요. S=R=1이면 앞단 출력이 모두 0이라 Q=1, Q′=1이에요.')),
        step('완성한 표', table(['S', 'R', 'C', 'Q(t)'], SR_ROWS_A)),
        step('검산', chk('Set 행에서 Q=1을 넣고 다시 계산하면 Q′=(1·1)′=0으로 Q′=Q̄가 맞아요. S=R=1 행만 Q=Q′=1이라 사용하지 않아요.')),
        step('흔한 실수', mist('S=R=1 행을 “X”로만 쓰고 끝내면 회로가 실제로 내는 값(Q=Q′=1)을 놓쳐요. 값과 금지 이유를 함께 써요.')),
    ], answer=p('00(C=1)→Q(t−1), 01→0(Reset), 10→1(Set), 11→1(Q′도 1, 금지), C=0→Q(t−1)')),
    notes=['제공 답안(예상 v1·v2·DOCX)은 S=R=1 행을 “1”로 적었어요. 같은 회로를 쓴 다른 자료는 “1 (Invalid)”, “−”로 적었어요. 회로 계산으로는 Q=Q′=1이고 사용하지 않는 상태예요.'])

# ------------------------------------------------------------ R-S → toggle (퀴즈 해설)
P['q-rs-quiz'] = dict(
    original=p('1) R-S Latch 회로로부터 (R,S가 1 일때), Q의 값이 Toggle 되게 하려면 회로를 어떻게 변형해야 하는가?') +
             p('2) R-S Latch 회로에서 (R,S 가 1일 때) 갖는 문제점이 무엇인가?') + p('(1)의 결과와 같이 변형된 회로를 무슨 회로라고 부르는가?'),
    conditions=p('주어진 회로는 S·C, R·C를 받는 NAND 두 개와 서로 되먹임된 NAND 두 개로 된 R-S Latch예요.'),
    ask=p('세 소문항, 1) 변형 방법, 2) 문제점, 3) 변형된 회로의 이름(원문의 “(1)의 결과와 같이…” 문장)에 모두 답하세요.'),
    problem_figures=['q-rs-quiz-given-01'],
    hints=[dict(label='Toggle 조건', html=p('Toggle은 “지금 Q가 0이면 Set, 1이면 Reset”이에요. S 쪽 NAND가 Q가 0일 때만, R 쪽 NAND가 Q가 1일 때만 열리게 하려면 각 NAND에 무엇을 하나 더 넣으면 될지 생각해요.'))],
    solution=dict(steps=[
        step('1) 변형', p('S 쪽 앞단 NAND를 3입력으로 바꿔 Q′을 되먹이고, R 쪽 앞단 NAND도 3입력으로 바꿔 Q를 되먹여요. Q=0이면 Q′=1이라 S 쪽만 열려 Set, Q=1이면 R 쪽만 열려 Reset이 되어 S=R=1(C=1)에서 Q가 뒤집혀요.') +
             img_sol('q-rs-quiz', 'S 쪽 3입력 NAND에 Q′, R 쪽 3입력 NAND에 Q를 되먹인 변형 회로')),
        step('2) 문제점', p('C=1, S=R=1이면 앞단 NAND 출력이 모두 0이라 Q=1, Q′=1이 돼요. Q와 Q′이 서로 보수여야 한다는 관계가 깨지고, 이 상태에서 S·R을 동시에 0으로 되돌리면 다음 상태를 예측할 수 없어요. 그래서 이 입력을 금지(부정, Not Allowed)해요.')),
        step('3) 이름', p('J-K Latch(JK 래치)예요. S 자리가 J, R 자리가 K가 돼요.')),
        step('검산', chk('Q=0에서 J=K=C=1: J 쪽 NAND=(1·1·1)′=0 → Q=1. Q=1에서: K 쪽 NAND=(1·1·1)′=0 → Q=0. 매번 반대로 바뀌어요.')),
        step('흔한 실수', mist('되먹임 선을 반대로 연결(S 쪽에 Q)하면 Q가 이미 1일 때 다시 Set을 시도해 Toggle이 되지 않아요. 또 C=1이 길게 유지되면 계속 뒤집히는 race-around가 생겨요.')),
    ], answer=p('1) S 쪽 NAND에 Q′, R 쪽 NAND에 Q를 되먹여 3입력으로 바꿔요. 2) Q=Q′=1이 되어 보수 관계가 깨지고 다음 상태를 예측할 수 없어 사용 금지예요. 3) JK Latch예요.')),
    notes=['퀴즈 해설.pdf의 해설과 같은 결론이에요. 해설의 “정확히는 출력값이 0과 1을 반복한다”는 문장은 S=R=1 동안이 아니라 동시에 0으로 되돌릴 때의 이상 모델에 해당해요(게이트 모델 계산: S=R=1 동안은 Q=Q′=1로 고정).'])

# ------------------------------------------------------------ D 회로 진리표
D_Q = [['0', '1', '', ''], ['1', '1', '', ''], ['X', '0', '', '']]
D_A = [['0', '1', '0', '1'], ['1', '1', '1', '0'], ['X', '0', 'Q(t−1)', 'Q′(t−1)']]
P['q-dff-table'] = dict(
    original=p('D F/F의 Truth table을 완성하시오(회로설계로 대체될 수 있음)'),
    conditions=p('회로는 아래 그림과 같아요. 원문 그림의 입력 단자 이름은 S와 C예요. S는 첫 NAND로 바로, 또 NOT(74HC04)을 거쳐 둘째 NAND로 들어가요. C는 두 NAND에 함께 들어가요. 원문에는 빈 표가 없어요. 풀이하기 쉽게 입력 행만 정리했어요.'),
    ask=p('표의 Q와 Q′을 채우세요.') + table(['S', 'C', 'Q', 'Q′'], D_Q),
    problem_figures=['q-dff-table-given-01'],
    hints=[dict(label='SR로 바꿔 읽기', html=p('NOT 때문에 아래 NAND로 가는 값은 항상 S의 반대예요. 그러면 위 NAND와 아래 NAND 중 어느 쪽에 1이 들어가는지 C=1에서 따져요.'))],
    solution=dict(steps=[
        step('회로 읽기', p('위 앞단 NAND는 S·C, 아래 앞단 NAND는 S′·C를 받아요. SR 래치의 S 자리에 S, R 자리에 S′이 들어간 D 래치예요. 그래서 두 입력이 동시에 1이 될 수 없어요.')),
        step('행마다', p('C=1, S=0: 아래 앞단만 0 → Reset, Q=0, Q′=1. C=1, S=1: 위 앞단만 0 → Set, Q=1, Q′=0. C=0: 앞단 출력이 모두 1 → 유지.')),
        step('완성한 표', table(['S', 'C', 'Q', 'Q′'], D_A)),
        step('검산', chk('C=1에서 Q가 항상 S와 같고 Q′은 그 반대예요. 금지 상태가 없어요.')),
        step('흔한 실수', mist('입력 이름이 S라서 SR 래치 표(유지·Reset·Set·부정 네 행)를 그대로 쓰면 안 돼요. NOT 때문에 입력 조합이 두 가지뿐이에요.')),
    ], answer=p('S=0, C=1 → Q=0, Q′=1; S=1, C=1 → Q=1, Q′=0; C=0 → Q(t−1), Q′(t−1) 유지')),
    notes=['제공 답안(종합본)과 같아요. 원문 문제는 “D F/F”라고 부르지만 회로와 표는 C가 1인 동안 동작하는 D 래치예요. 기출_단답형 5번 답안의 둘째 행 “0 1 1”은 입력이 첫 행과 같아서 오기로 보여요(회로 계산은 S=1일 때 1).'])

P['q-dff-design'] = dict(
    original=p('D F/F의 Truth table을 만족하는 회로를 설계하시오.') + table(['D', 'C', 'Q(t)'], [['0', '1', '0'], ['1', '1', '1'], ['x', '0', 'Q(t-1)']]),
    conditions=p('표는 원문 그대로이고 이미 채워져 있어요. C는 제어 입력이에요. 원문은 F/F라고 부르지만 표에는 C가 1인 동안의 동작이 적혀 있어요.'),
    ask=p('이 표를 만족하는 게이트 회로를 그리세요.'), problem_figures=[],
    hints=[dict(label='출발점', html=p('C=1이면 Q=D, C=0이면 유지예요. Enable이 있는 SR 래치에서 S와 R을 무엇으로 정하면 이 표가 되는지 생각해요.'))],
    solution=dict(steps=[
        step('생각', p('Enable SR 래치는 C=0이면 유지하고, C=1이면 S=1→Q=1, R=1→Q=0이에요. S=D, R=D′으로 정하면 C=1에서 Q=D가 되고 S=R=1도 생기지 않아요.')),
        step('완성 회로', p('NOT 1개(74HC04)로 D′을 만들고, NAND 4개(74HC00)로 앞단 (D·C)′, (D′·C)′과 교차 래치를 만들어요.') +
             img_sol('q-dff-design', 'D와 NOT을 거친 D′이 C와 함께 앞단 NAND 두 개로 들어가고 교차된 NAND 두 개가 Q와 Q′을 내는 D 래치')),
        step('검산', chk('C=1, D=0: 아래 앞단 (1·1)′=0 → Q′=1, Q=0. C=1, D=1: 위 앞단 0 → Q=1. C=0: 앞단 모두 1 → 유지. 표 세 행과 같아요.')),
        step('흔한 실수', mist('NOT 없이 D를 두 NAND에 그대로 넣으면 D=1, C=1에서 S=R=1 금지 상태가 돼요.')),
    ], answer=p('D와 D′(NOT)을 S·R 자리에 넣은 Enable SR 래치(NOT 1개 + NAND 4개)예요.')),
    notes=['표가 C=1인 “동안” Q=D인 레벨 동작이라서, 이름은 F/F이지만 D 래치 회로가 이 표를 만족해요. 예상문제 자료의 “D Latch” 설계 답안 회로(입력 이름은 S·C)와 같은 구조예요. 엣지형 D F/F(마스터-슬레이브 등)도 다른 유효한 설계로 인정될 수 있어요.'])

# ------------------------------------------------------------ JK 회로 진리표
JK_Q = [['0', '0', '1', ''], ['0', '1', '1', ''], ['1', '0', '1', ''], ['1', '1', '1', ''], ['X', 'X', '0', '']]
JK_A = [['0', '0', '1', 'Q(t−1)'], ['0', '1', '1', '0 : Reset'], ['1', '0', '1', '1 : Set'], ['1', '1', '1', 'Q(t−1)′ : Toggle'], ['X', 'X', '0', 'Q(t−1)']]
P['q-jkff-short'] = dict(
    original=p('J-K F/F의 Truth table을 완성하시오.'),
    conditions=p('회로는 아래 그림과 같아요. J·C와 Q′을 받는 3입력 NAND, K·C와 Q를 받는 3입력 NAND(74HC10)가 서로 되먹임된 NAND 두 개(74HC00)로 가요. Toggle 행은 C를 짧게 1로 하는 이상적인 경우로 읽어요. 원문에는 빈 표가 없어요. 풀이하기 쉽게 입력 행만 정리했어요.'),
    ask=p('표의 Q(t)를 채우세요.') + table(['J', 'K', 'C', 'Q(t)'], JK_Q),
    problem_figures=['q-jkff-short-given-01'],
    hints=[dict(label='되먹임 선', html=p('J 쪽 NAND에는 Q′, K 쪽 NAND에는 Q가 들어가요. J=K=1일 때 Q=0인 경우와 Q=1인 경우를 따로 계산해요.'))],
    solution=dict(steps=[
        step('C=0과 J=K=0', p('앞단 NAND에 0이 있어 출력이 모두 1이라 유지예요.')),
        step('J=0,K=1과 J=1,K=0', p('K=1이면 Q=1일 때 K 쪽이 열려 Q=0이 되고, Q가 이미 0이면 그대로 0이에요. 그래서 Reset. J=1이면 같은 방식으로 Set이에요.')),
        step('J=K=1', p('Q=0이면 Q′=1이라 J 쪽 NAND만 0 → Q=1. Q=1이면 K 쪽 NAND만 0 → Q=0. 결과는 이전 값의 반대(Toggle)예요.')),
        step('완성한 표', table(['J', 'K', 'C', 'Q(t)'], JK_A)),
        step('검산', chk('J=1, K=0에서 Q=1이었다면 J 쪽 NAND는 Q′=0 때문에 1, K 쪽은 K=0 때문에 1이라 Q=1 유지예요. Set 결과와 같아요.')),
        step('흔한 실수', mist('이 회로는 C가 1인 동안 동작하는 래치예요. J=K=1에서 C를 오래 1로 두면 Q가 계속 뒤집혀요(race-around). 표의 Toggle은 C를 Q가 한 번 뒤집힐 만큼은 길고 되먹임이 다시 돌아오기 전에 끝날 만큼 짧게 1로 하는 이상적인 조건의 결과예요.')),
    ], answer=p('00→Q(t−1), 01→0(Reset), 10→1(Set), 11→Q(t−1)′(Toggle), C=0→Q(t−1)')),
    notes=['제공 답안과 같아요. 원문은 “J-K F/F”라고 부르지만 회로는 C에 대한 레벨 동작인 JK 래치예요. 게이트 지연 모델로 계산하면 C=1을 유지할 때 J=K=1에서 상태가 계속 바뀌고, 짧은 펄스에서는 한 번만 뒤집혀요.'])

P['q-jkff-design'] = dict(
    original=p('J-K F/F의 Truth table을 만족하는 회로를 설계하시오.') +
             table(['J', 'K', 'C', 'Q(t)'], [['0', '0', '1', 'Q(t-1)'], ['0', '1', '1', '0 : Reset'], ['1', '0', '1', '1 : Set'], ['1', '1', '1', 'Q(t-1)′ : Toggle'], ['x', 'x', '0', 'Q(t-1)']]),
    conditions=p('표는 원문 그대로이고 이미 채워져 있어요. 원문은 F/F라고 부르지만 표에는 C가 1인 동안의 동작이 적혀 있어요. Toggle 행은 C를 짧게 1로 하는 이상적인 경우로 읽어요.'), ask=p('이 표를 만족하는 게이트 회로를 그리세요.'), problem_figures=[],
    hints=[dict(label='SR에서 출발', html=p('J=S, K=R로 두면 1·1 행만 다르게 만들면 돼요. 그 행에서 지금 Q에 따라 S 쪽과 R 쪽 중 한쪽만 열리게 하려면 무엇을 되먹일지 생각해요.'))],
    solution=dict(steps=[
        step('생각', p('Enable SR 래치의 앞단 NAND를 3입력으로 바꿔요. J 쪽에는 J·C·Q′, K 쪽에는 K·C·Q를 넣어요. 지금 Q가 0이면 J 쪽만, 1이면 K 쪽만 열려서 1·1 행이 Toggle이 돼요.')),
        step('완성 회로', p('3입력 NAND 2개(74HC10)와 2입력 NAND 2개(74HC00)로 만들어요.') +
             img_sol('q-jkff-design', 'J와 C와 Q′이 첫 3입력 NAND, K와 C와 Q가 둘째 3입력 NAND로 들어가고 교차된 NAND 두 개가 Q와 Q′을 내는 JK 래치')),
        step('특성식', tex(r'Q(t)=J\,\overline{Q(t-1)}+\overline{K}\,Q(t-1)') + p('C=1일 때의 식이에요.')),
        step('검산', chk('네 J·K 조합과 Q=0, 1 두 경우를 모두 계산하면 표와 같아요. 예: J=K=1, Q=1 → K 쪽 (1·1·1)′=0 → Q=0.')),
        step('흔한 실수', mist('Q와 Q′의 되먹임을 바꾸어 연결하면 1·1 행에서 Toggle이 되지 않고 같은 값을 다시 Set해요. 또 C=1이 길면 race-around가 생긴다는 한계도 함께 알아 둬요.')),
    ], answer=p('J·C·Q′, K·C·Q를 받는 3입력 NAND 두 개 + 교차 NAND 두 개로 된 JK 래치예요.')),
    notes=['예상문제 자료의 “J-K Latch” 설계 답안 회로(74HC10 2개, 74HC00 2개)와 같은 구조예요. 표는 C=1에서 동작하는 레벨 표이고 Toggle 행은 C가 짧은 펄스라는 조건이 필요해요. 하강 엣지 JK F/F(74HC76)를 쓰는 답도 다른 유효한 구현이에요.'])

# ------------------------------------------------------------ T F/F
P['q-tff'] = dict(
    original=p('J-K F/F을 이용해서 T F/F(toggle)을 만드는 방법을 설명하시오.'), conditions='',
    ask=p('연결 방법과 T=0, T=1일 때의 동작을 설명하세요.'), problem_figures=[],
    hints=[dict(label='JK 표에서', html=p('JK 표의 네 행 중 “유지”와 “Toggle”만 남기려면 J와 K가 항상 같아야 해요.'))],
    solution=dict(steps=[
        step('연결', p('J와 K를 한 선으로 묶어 입력 T로 써요. 클록은 그대로 CLK에 연결해요.') + img_sol('q-tff', 'T 입력을 J와 K에 함께 연결한 J-K 플립플롭')),
        step('동작', table(['T', 'J', 'K', '클록 엣지 후 Q'], [['0', '0', '0', 'Q(t−1) 유지'], ['1', '1', '1', 'Q(t−1)′ Toggle']])),
        step('특성식', tex(r'Q(t)=T\oplus Q(t-1)')),
        step('검산', chk('T=1로 두고 74HC76의 클록을 세 번 내리면 Q가 0→1→0→1로 바뀌어요(시작 Q=0일 때).')),
        step('흔한 실수', mist('J=K=1을 “인식하지 못한다”고 쓰면 안 돼요. JK에서 1·1은 정상 입력인 Toggle이에요. 금지 상태는 SR의 1·1이에요.')),
    ], answer=p('J와 K를 묶어 T로 쓰면 T=0일 때 유지, T=1일 때 클록 엣지마다 Q가 반전돼요.')),
    notes=['제공 답안(v1·v2·DOCX의 “T=0→유지, T=1→Toggle”, 기출_단답형 7번 그림)과 같아요. 종합본 답안의 “J와 K에 모두 1이 들어오면 인식하지 못하는데”는 SR의 금지 상태와 혼동한 표현이에요.'])

# ------------------------------------------------------------ 74HC76 CLR/PR
P['q-74hc76'] = dict(
    original=p('74HC76은 J-K F/F이다. CLR 핀과 PR핀의 기능에 대해 설명하시오.'), conditions='',
    ask=p('CLR와 PR가 어떤 값일 때 Q가 어떻게 되는지, 클록과의 관계를 함께 설명하세요.'), problem_figures=[],
    hints=[dict(label='이름 풀기', html=p('PR은 Preset, CLR은 Clear의 줄임말이에요. 기호의 원(bubble)이 무엇을 뜻하는지도 떠올려요.'))],
    solution=dict(steps=[
        step('기능', ul(['PR(Preset, 교안의 SET): 0을 넣으면 클록·J·K와 상관없이 즉시 Q=1(Q′=0)이 돼요.',
                       'CLR(Clear, 교안의 RESET): 0을 넣으면 클록·J·K와 상관없이 즉시 Q=0(Q′=1)이 돼요.',
                       '둘 다 0일 때 동작하는 Active Low 비동기 입력이고 클록보다 우선해요. J·K로 동작시킬 때는 둘 다 1(HIGH)로 둬요.',
                       '그래서 플립플롭을 원하는 초기 상태(0 또는 1)로 맞출 때 써요.'])),
        step('표', table(['PR', 'CLR', 'Q'], [['0', '1', '1 (Preset)'], ['1', '0', '0 (Clear)'], ['1', '1', '클록·J·K에 따라 동작'], ['0', '0', '사용하지 않음']])),
        step('검산', chk('교안 p11 표(Set=0, Reset=1 → 1: Set / Set=1, Reset=0 → 0: Reset)와 74HC76 데이터시트 그림의 표(Set=L → Q=H)가 모두 같은 방향이에요.')),
        step('흔한 실수', mist('PR을 “출력을 0으로” 만든다고 쓰면 반대예요. Preset은 1로, Clear는 0으로 만들어요. “1을 넣으면 동작”이라고 쓰는 것도 Active Low를 놓친 거예요.')),
    ], answer=p('PR은 0일 때 Q를 1로, CLR은 0일 때 Q를 0으로 만드는 Active Low 비동기 입력이에요. 클록과 상관없이 우선 적용되어 초기화에 쓰이고, 평소 J·K 동작 때는 둘 다 HIGH로 둬요.')),
    notes=['제공 답안이 자료마다 달라요. 예상 v1·v2·DOCX는 CLR=clear, PR=set으로 이 풀이와 같아요. 종합본은 PR=출력 0, CLR=출력 1로 반대이고, 기출_단답형은 clr·pr 모두 “0이 입력되면 출력 0”이라고 적었어요. 교안 p11과 데이터시트 그림 기준으로 CLR→0, PR→1이에요.'])

# ------------------------------------------------------------ 74HC574
P['q-74hc574'] = dict(
    original=p('74HC574는 D F/F이다. 어느 시점에서 입력이 출력에 반영되는지 설명하시오.'), conditions='',
    ask=p('입력 D가 출력 Q에 반영되는 순간을 쓰세요.'), problem_figures=[],
    hints=[dict(label='F/F이면', html=p('플립플롭은 클록의 “순간”에 동작해요. 클록 단자 기호에 원이 있는지 없는지로 엣지 방향을 떠올려요.'))],
    solution=dict(steps=[
        step('풀이', p('74HC574는 상승 엣지에서 동작하는 8비트 D 플립플롭이에요. 클록이 Low에서 High로 오르는 순간의 D 값이 저장되어 Q에 나타나고(출력 enable OE′가 Low일 때), 그 밖의 시간(클록이 High나 Low로 머무는 동안)에는 D가 바뀌어도 Q가 그대로예요.')),
        step('검산', chk('교안 p9의 74HC74 표에서 CLK가 ↑일 때만 Q=D이고 CLK=0이면 Q(t−1)인 것과 같은 원리예요.')),
        step('흔한 실수', mist('“클록이 High인 동안 반영된다”라고 쓰면 레벨 동작(래치) 설명이 돼요. 엣지 순간만 반영돼요.')),
    ], answer=p('클록이 Low에서 High로 상승하는 순간(Rising Edge)에 입력 D가 출력에 반영돼요.')),
    notes=['제공 답안(“한clock 발생 지속기간 동안에만 입력이 출력에 반영된다(clock이 low에서 high로 상승할때)”)은 레벨과 엣지를 함께 적었어요. 괄호 안의 상승 시점이 맞는 부분이에요. 이 저장소에는 74HC574 데이터시트가 없어 일반적인 74HC574 사양(상승 엣지, 3상태 출력의 8비트 D F/F) 기준이에요.'])

# ------------------------------------------------------------ 연습: 74HC76 추적
TR_H = ['단계', 'PR', 'CLR', 'CLK', 'J', 'K', 'Q']
TR_Q = [[str(n), str(pr), str(clr), CLK_TXT[e], str(j), str(k), ''] for n, pr, clr, e, j, k in TRACE]
TR_A = [[str(n), str(pr), str(clr), CLK_TXT[e], str(j), str(k), str(q)] for (n, pr, clr, e, j, k), q in zip(TRACE, TRACE_Q)]
P['q-p-76-trace'] = dict(
    original=p('새 연습: 74HC76 한 개의 플립플롭에 아래 순서로 입력을 넣었어요. 각 단계가 끝난 뒤의 Q를 구하세요.'),
    conditions=p('↓는 클록이 1에서 0으로 떨어지는 순간, ↑는 0에서 1로 오르는 순간이에요. “변화 없음”은 그 단계에서 클록 엣지가 없다는 뜻이에요. ↓가 이어지는 단계 사이에는 클록이 다시 1로 오르는 ↑가 있지만, 74HC76은 ↑에 반응하지 않아 표에서 생략했어요. 처음 Q는 정해져 있지 않아요.'),
    ask=p('표의 Q를 채우세요.') + table(TR_H, TR_Q), problem_figures=[],
    hints=[dict(label='순서', html=p('각 단계에서 PR·CLR을 먼저 보고, 둘 다 1일 때만 클록이 ↓인지 확인한 뒤 J·K를 적용해요.'))],
    solution=dict(steps=[
        step('1단계', p('PR=0, CLR=1이라 클록과 상관없이 Q=1이에요. 처음 Q가 무엇이었든 여기서 정해져요.')),
        step('2~4단계', p('2단계: ↓, J=K=0 → 유지 1. 3단계: ↑라서 74HC76은 반응하지 않아요 → 1. 4단계: ↓, J=0, K=1 → Reset 0.')),
        step('5~7단계', p('5단계: ↓, J=K=1 → Toggle 1. 6단계: 다시 Toggle 0. 7단계: ↓, J=1, K=0 → Set 1.')),
        step('8단계', p('CLR=0이라 클록이 없어도, J=K=1이어도 즉시 Q=0이에요.')),
        step('완성한 표', table(TR_H, TR_A)),
        step('검산', chk('하강 엣지는 2·4·5·6·7단계의 다섯 번뿐이고, Q가 바뀐 단계는 1(Preset)·4·5·6·7·8(Clear)이에요. 3단계(↑)는 바뀌지 않았어요.')),
        step('흔한 실수', mist('3단계의 상승 엣지에서 K=1을 적용해 0으로 바꾸면 틀려요. 8단계에서 J=K=1을 보고 Toggle하면 CLR 우선을 놓친 거예요.')),
    ], answer=p('Q = 1, 1, 1, 0, 1, 0, 1, 0 (단계 1~8)')),
    notes=['이 문제는 기출에 없는 74HC76 엣지 추적을 보충하려고 만든 새 연습이에요. 교안 p11 표의 규칙으로 계산했어요.'])

ORDER = ['q-diff', 'q-latch', 'q-ff', 'q-sr-nand-00', 'q-rs-latch', 'q-rs-quiz', 'q-dff-table', 'q-dff-design',
         'q-jkff-short', 'q-jkff-design', 'q-tff', 'q-74hc76', 'q-74hc574', 'q-p-76-trace']
assert set(ORDER) == set(P)

PROBLEM_TOPICS = {
    'q-diff': ['t-edge'], 'q-latch': ['t-basics', 't-sr-enable'], 'q-ff': ['t-edge'], 'q-sr-nand-00': ['t-sr-basic'],
    'q-rs-latch': ['t-sr-enable'], 'q-rs-quiz': ['t-sr-enable', 't-jk-latch'], 'q-dff-table': ['t-d-latch'],
    'q-dff-design': ['t-d-latch'], 'q-jkff-short': ['t-jk-latch'], 'q-jkff-design': ['t-jk-latch'],
    'q-tff': ['t-74hc76'], 'q-74hc76': ['t-74hc76'], 'q-74hc574': ['t-edge'], 'q-p-76-trace': ['t-74hc76'],
}
TITLES = {
    'q-diff': 'Latch와 Flip-Flop의 차이', 'q-latch': 'Latch를 설명', 'q-ff': 'Flip-Flop을 설명',
    'q-sr-nand-00': '기본 S-R latch에 S=R=0을 넣으면', 'q-rs-latch': 'Enable이 있는 R-S Latch의 진리표',
    'q-rs-quiz': 'R-S Latch를 Toggle 되게 바꾸기', 'q-dff-table': '회로가 주어진 D F/F 진리표',
    'q-dff-design': 'D F/F 진리표를 만족하는 회로 설계', 'q-jkff-short': '회로가 주어진 J-K F/F 진리표',
    'q-jkff-design': 'J-K F/F 진리표를 만족하는 회로 설계', 'q-tff': 'J-K F/F로 T F/F 만들기',
    'q-74hc76': '74HC76의 CLR·PR 핀 기능', 'q-74hc574': '74HC574에서 입력이 반영되는 시점', 'q-p-76-trace': '74HC76 하강 엣지 따라가기',
}
DERIVED = {
    'q-diff': 'Latch=레벨 트리거(Enable 동안 반영, 비동기), F/F=엣지 트리거(클록 엣지 순간 반영, 동기)',
    'q-latch': '1비트 레벨 트리거 기억소자: Enable 동안 입력 반영, 아니면 유지',
    'q-ff': '1비트 엣지 트리거 동기 기억소자: 클록 엣지 순간에만 반영',
    'q-sr-nand-00': 'Q=1, Q′=1, Q′=not Q 성립 안 함',
    'q-rs-latch': '00→Q(t−1), 01→0, 10→1, 11→1(Q′=1, 금지), C=0→Q(t−1)',
    'q-rs-quiz': 'S쪽 NAND에 Q′, R쪽 NAND에 Q 되먹임(3입력); Q=Q′=1·다음 상태 예측 불가로 금지; JK Latch',
    'q-dff-table': 'S=0,C=1→Q=0,Q′=1; S=1,C=1→Q=1,Q′=0; C=0→유지',
    'q-dff-design': 'S=D, R=D′인 Enable SR 래치(NOT 1 + NAND 4)',
    'q-jkff-short': '00→Q(t−1), 01→0, 10→1, 11→Q(t−1)′, C=0→Q(t−1)',
    'q-jkff-design': 'J·C·Q′, K·C·Q 3입력 NAND 2 + 교차 NAND 2 (JK 래치)',
    'q-tff': 'J와 K를 묶어 T: T=0 유지, T=1 Toggle',
    'q-74hc76': 'PR=0→Q=1, CLR=0→Q=0, Active Low 비동기 우선, 평소 HIGH',
    'q-74hc574': '클록 상승 엣지(Low→High) 순간',
    'q-p-76-trace': 'Q=1,1,1,0,1,0,1,0',
}
SCOPE_SUPP = {'q-sr-nand-00', 'q-rs-quiz', 'q-jkff-short', 'q-jkff-design', 'q-74hc574'}
