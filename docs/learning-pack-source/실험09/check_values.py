"""실험09 추적표·답을 게이트 모델로 다시 계산해 원고 값과 대조해요. 실제 측정이 아니에요.

- 1 bit RAM: p4 회로도(Input 인버터가 R 쪽 AND, Input 그대로가 S 쪽 AND)와 Active High SR 표.
- 2 bit RAM: p6 회로도의 NAND 네트워크(WR1 은 두 비트의 세트 쪽, WR0 은 리셋 쪽 NAND 에 공통)를
  되먹임이 안정될 때까지 반복 계산해요. 74HC03 열린 드레인 + 10k 풀업은 논리상 NAND 와 같아요.
- 74670: 교안 p8 범례(WE·RE 0: On)와 4워드 × 4비트 저장으로 모델링해요.
"""
from pathlib import Path
import itertools, json, sys


def nand(*xs):
    return 0 if all(xs) else 1


# ---- NAND SR 래치 ---------------------------------------------------------
def nand_latch(s_, r_, q, qb):
    """S′·R′ 입력과 현재 Q·Q′에서 안정 상태를 찾아요."""
    for _ in range(10):
        nq, nqb = nand(s_, qb), nand(r_, q)
        if (nq, nqb) == (q, qb):
            return q, qb
        q, qb = nq, nqb
    raise RuntimeError('unstable')


def latch_rules():
    out = {}
    for s_, r_ in itertools.product((0, 1), repeat=2):
        res = set()
        for q in (0, 1):
            res.add(nand_latch(s_, r_, q, 1 - q))
        out[(s_, r_)] = res
    return out


# ---- 1 bit RAM (p4) --------------------------------------------------------
def ram1(sel, rw, inp, q):
    """S·R·Output 과 다음 Q. q 는 이전 Q예요. S=R=0 이면 유지해요."""
    s = sel & (1 - rw) & inp          # 회로도: Input 그대로가 S 쪽 AND
    r = sel & (1 - rw) & (1 - inp)    # 회로도: Input 인버터가 R 쪽 AND
    if s and r:
        raise ValueError('S=R=1')
    nq = 1 if s else 0 if r else q
    out = sel & rw & nq
    return s, r, nq, out


def ram1_manual_eq(sel, rw, inp):
    """교안 p4 식을 글자 그대로: S=Sel·RW′·Input′, R=Sel·RW′·Input."""
    return sel & (1 - rw) & (1 - inp), sel & (1 - rw) & inp


# ---- 2 bit RAM (p6) --------------------------------------------------------
class Ram2:
    def __init__(self, qa=0, qb=0):
        self.q = {'A': qa, 'B': qb}

    def apply(self, oe0, in0, wr0, oe1, in1, wr1):
        nodes = {}
        for bit, en, oe in (('A', in0, oe0), ('B', in1, oe1)):
            s_ = nand(en, wr1)          # 세트 쪽 NAND (p6 pin 1·2→3, WR1 공통)
            r_ = nand(en, wr0)          # 리셋 쪽 NAND (p6 pin 4·5→6, WR0 공통)
            q, qb = nand_latch(s_, r_, self.q[bit], 1 - self.q[bit])
            if s_ == 0 and r_ == 0:
                q = None                # 금지 입력: Q=Q′=1 이라 정해지지 않아요
            else:
                self.q[bit] = q
            rd = nand(oe, q if q is not None else 1)   # 74HC03 + 풀업
            out = nand(rd, rd)
            nodes[bit] = dict(S_=s_, R_=r_, Q=q, RD_=rd, OUT=out)
        return nodes


T1 = [  # 스텝, OE0 IN0 WR0 OE1 IN1 WR1, 기대 OUT0 OUT1 (명세 T1)
    ('S1', (0, 0, 0, 0, 0, 1), (0, 0)),
    ('W1', (0, 1, 0, 0, 0, 1), (0, 0)),
    ('R1', (1, 0, 0, 0, 0, 1), (1, 0)),
    ('W2', (0, 0, 1, 0, 1, 0), (0, 0)),
    ('R2', (1, 0, 1, 1, 0, 0), (1, 0)),
    ('W3', (0, 0, 0, 0, 1, 1), (0, 0)),
    ('R3', (1, 0, 0, 1, 0, 1), (1, 1)),
    ('W4', (0, 1, 1, 0, 0, 0), (0, 0)),
    ('R4', (1, 0, 1, 1, 0, 0), (0, 1)),
]


def run_t1():
    rows = []
    for qa0, qb0 in itertools.product((0, 1), repeat=2):
        r = Ram2(qa0, qb0)
        for name, ins, exp in T1:
            n = r.apply(*ins)
            got = (n['A']['OUT'], n['B']['OUT'])
            if name != 'S1':
                assert got == exp, (qa0, qb0, name, got, exp)
            rows.append((qa0, qb0, name, got))
    return rows


def bank_answers():
    """문제은행 2bit 문항의 독립 풀이: 쓰고 IN 을 내려 저장한 뒤 읽었을 때 값."""
    res = {}
    cases = {
        'q-apart1': ((1, 1, 0, 0, 0, 1), 'A', 1),
        'q-bpart1': ((0, 0, 0, 1, 1, 1), 'B', 1),
        'q-bpart0': ((0, 0, 1, 1, 1, 0), 'B', 0),
        'q-apart0': ((1, 1, 1, 0, 0, 0), 'A', 0),
    }
    for qid, (ins, bit, want) in cases.items():
        for qa0, qb0 in itertools.product((0, 1), repeat=2):
            for oe_a, oe_b in itertools.product((0, 1), repeat=2):
                r = Ram2(qa0, qb0)
                oe0, in0, wr0, oe1, in1, wr1 = ins
                r.apply(oe_a, in0, wr0, oe_b, in1, wr1)       # OE 값과 무관하게 써지는지
                other = 'B' if bit == 'A' else 'A'
                before_other = (qb0 if other == 'B' else qa0)
                assert r.q[bit] == want, (qid, oe_a, oe_b)
                assert r.q[other] == before_other, (qid, 'other bit changed')
            r = Ram2(0, 0)
            n = r.apply(*ins)
            r.apply(ins[0], 0, ins[2], ins[3], 0, ins[5])      # IN 내려 저장
            n2 = r.apply(1 if bit == 'A' else 0, 0, ins[2], 1 if bit == 'B' else 0, 0, ins[5])
            assert n2[bit]['OUT'] == want
        res[qid] = 'ok'
    # 범례대로(WR0 이 A 값) 읽은 오답은 반대 값을 써요.
    r = Ram2(0, 0)
    r.apply(0, 1, 1, 0, 0, 0)
    assert r.q['A'] == 0
    return res


def rules_checks():
    r = Ram2(1, 0)
    # IN=0 이면 WR 을 어떻게 바꿔도 유지
    for wr0, wr1 in itertools.product((0, 1), repeat=2):
        n = r.apply(0, 0, wr0, 0, 0, wr1)
        assert r.q == {'A': 1, 'B': 0} and n['A']['S_'] == 1 and n['A']['R_'] == 1
    # IN0=1, WR0=WR1=1 이면 S′=R′=0 (금지)
    n = Ram2().apply(0, 1, 1, 0, 0, 1)
    assert n['A']['S_'] == 0 and n['A']['R_'] == 0 and n['A']['Q'] is None
    # IN0=1, WR0=WR1=0 이면 쓰지 않음(유지)
    r = Ram2(1, 1)
    r.apply(0, 1, 0, 0, 0, 0)
    assert r.q['A'] == 1
    # IN0=IN1=1 이면 두 비트에 같은 값이 써짐
    r = Ram2(0, 1)
    r.apply(0, 1, 0, 0, 1, 1)
    assert r.q == {'A': 1, 'B': 1}
    # OE0=1, IN0=1 이면 OUT0 이 WR1 을 바로 따라감(기존 값 못 읽음)
    r = Ram2(0, 0)
    n = r.apply(1, 1, 0, 0, 0, 1)
    assert n['A']['OUT'] == 1
    n = r.apply(1, 1, 1, 0, 0, 0)
    assert n['A']['OUT'] == 0
    return 'ok'


# ---- 74670 -----------------------------------------------------------------
class R670:
    def __init__(self):
        self.mem = {a: None for a in range(4)}

    def step(self, wb, wa, we, d, rb, ra, re):
        """d 는 (D4, D3, D2, D1). we·re 는 0 일 때 켜져요. 출력 None 은 고임피던스."""
        if we == 0:
            self.mem[wb * 2 + wa] = tuple(d)
        if re == 1:
            return None
        return self.mem[rb * 2 + ra]


def run_t4():
    r = R670()
    writes = [(0, 0, (0, 0, 0, 1)), (0, 1, (0, 0, 1, 0)), (1, 0, (0, 1, 0, 0)), (1, 1, (1, 0, 0, 0))]
    for wb, wa, d in writes:
        r.step(wb, wa, 1, d, 0, 0, 1)
        assert r.step(wb, wa, 0, d, 0, 0, 1) is None
        r.step(wb, wa, 1, d, 0, 0, 1)
    reads = {}
    for rb, ra in itertools.product((0, 1), repeat=2):
        reads[f'{rb}{ra}'] = ''.join(map(str, r.step(1, 1, 1, (0, 0, 0, 0), rb, ra, 0)))
    assert reads == {'00': '0001', '01': '0010', '10': '0100', '11': '1000'}
    # 동시에: 11 에 쓰면서 00 을 읽기
    out = r.step(1, 1, 0, (1, 1, 1, 1), 0, 0, 0)
    assert out == (0, 0, 0, 1) and r.mem[3] == (1, 1, 1, 1)
    return reads


def bus_checks():
    """t-opendrain 추론 절: 3번·6번을 묶은 wired-AND 읽기 버스와 74HC00 대체 시 출력."""
    rows = {}
    for oe0, oe1, qa, qb in itertools.product((0, 1), repeat=4):
        line = nand(oe0, qa) & nand(oe1, qb)          # 열린 드레인 묶음 = AND
        out = nand(line, line)                         # 입력 묶은 NAND = 인버터
        assert out == ((oe0 & qa) | (oe1 & qb))
        if (oe0, oe1) == (1, 0):
            assert out == qa
        if (oe0, oe1) == (0, 1):
            assert out == qb
        # 74HC00(푸시풀)이면 두 출력이 반대로 구동할 때 부딪쳐요
        clash = nand(oe0, qa) != nand(oe1, qb)
        rows[f'{oe0}{oe1}{qa}{qb}'] = dict(line=line, out=out, totem_clash=clash)
    assert rows['1010']['totem_clash']                 # A 읽기(Q_A=1), OE1=0 → 단락
    # 교안 회로 그대로(묶지 않음)는 74HC00이어도 OUT0 = OE0·Q
    for oe, q in itertools.product((0, 1), repeat=2):
        a = nand(oe, q)
        assert nand(a, a) == (oe & q)
    return rows


def main():
    lr = latch_rules()
    assert lr[(0, 1)] == {(1, 0)} and lr[(1, 0)] == {(0, 1)}
    assert lr[(1, 1)] == {(0, 1), (1, 0)} and lr[(0, 0)] == {(1, 1)}
    one = {}
    for sel, rw, inp in itertools.product((0, 1), repeat=3):
        for q in (0, 1):
            one[f'{sel}{rw}{inp}{q}'] = ram1(sel, rw, inp, q)
    # 문항 답
    assert ram1(1, 0, 1, 0)[2] == 1 and ram1(1, 0, 1, 1)[2] == 1        # 1 쓰기
    assert ram1(1, 0, 0, 0)[2] == 0 and ram1(1, 0, 0, 1)[2] == 0        # 0 쓰기
    assert ram1(1, 1, 0, 1)[3] == 1 and ram1(1, 1, 1, 0)[3] == 0        # 읽기는 Q
    assert ram1(0, 0, 1, 1)[2] == 1                                     # Sel=0 은 유지(표 1행 Q=0 과 다름)
    # 교안 식을 글자대로 쓰면 Input=1 에서 R=1 → Q=0 이라 표와 반대예요.
    assert ram1_manual_eq(1, 0, 1) == (0, 1)
    t1 = run_t1()
    ans = bank_answers()
    rc = rules_checks()
    t4 = run_t4()
    bus = bus_checks()
    res = dict(latch={f'{k[0]}{k[1]}': sorted(v) for k, v in lr.items()}, ram1=one, t1=t1, bank=ans, rules=rc, t4=t4, bus=bus)
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if out:
        out.write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding='utf-8')
    print('check_values ok')


if __name__ == '__main__':
    main()
