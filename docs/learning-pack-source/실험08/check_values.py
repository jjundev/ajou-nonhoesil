"""실험08 추적표·답을 회로 동작 규칙에서 다시 계산해 원고 값과 대조해요. 실제 측정이 아니에요."""
from pathlib import Path
import itertools, json, sys
sys.path.insert(0, str(Path(__file__).parent))
from content import SEG


def jk(q, j, k):
    return (j and not q) or ((not k) and q)


def ripple(n, a=0, b=0):
    out = [(a, b)]
    for _ in range(n):
        fall = a == 1
        a = 1 - a
        if fall:
            b = 1 - b
        out.append((a, b))
    return out


def sync_next(a, b):
    return int(jk(a, 1 - b, 1)), int(jk(b, a, 1))


def sync(n, a=0, b=0):
    out = [(a, b)]
    for _ in range(n):
        a, b = sync_next(a, b)
        out.append((a, b))
    return out


def mod6(n):
    a = b = c = 0
    out = [(a, b, c)]
    for _ in range(n):
        na, nb = sync_next(a, b)
        if b == 1 and nb == 0:
            c = 1 - c
        a, b = na, nb
        out.append((a, b, c))
    return out


def seven490(n):
    """교안 p6 내부: QA 는 T, QB J=QD′ K=1, QC 는 QB 하강에 T, QD J=QB·QC K=1. QB·QD 클럭은 INPUT B(=QA)."""
    qa = qb = qc = qd = 0
    out = [(qd, qc, qb, qa)]
    for _ in range(n):
        fall = qa == 1
        qa = 1 - qa
        if fall:
            nb = int(jk(qb, 1 - qd, 1))
            nd = int(jk(qd, qb & qc, 1))
            if qb == 1 and nb == 0:
                qc = 1 - qc
            qb, qd = nb, nd
        out.append((qd, qc, qb, qa))
    return out


r = ripple(6)
assert [f'{a}{b}' for a, b in r] == ['00', '10', '01', '11', '00', '10', '01']
s = sync(6)
assert [f'{a}{b}' for a, b in s] == ['00', '10', '01', '00', '10', '01', '00']
assert sync_next(1, 1) == (0, 0)
m = mod6(6)
assert len(set(m[:6])) == 6 and m[6] == m[0]
assert [f'{a}{b}{c}' for a, b, c in m] == ['000', '100', '010', '001', '101', '011', '000']
c = seven490(10)
assert [d * 8 + cc * 4 + b * 2 + a for d, cc, b, a in c] == [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 0]
# 3단 비동기: A, B, C 차례 반전
a = b = cc = 0
seq = [0]
for _ in range(8):
    fa = a
    a = 1 - a
    if fa:
        fb = b
        b = 1 - b
        if fb:
            cc = 1 - cc
    seq.append(cc * 4 + b * 2 + a)
assert seq == [0, 1, 2, 3, 4, 5, 6, 7, 0]
# 디코더: 상태마다 출력 하나
for A, B in itertools.product((0, 1), repeat=2):
    y = [(1 - A) & (1 - B), A & (1 - B), (1 - A) & B, A & B]
    assert sum(y) == 1 and y.index(1) == A + 2 * B
# 7447 숫자 5
PIN = dict(a=13, b=12, c=11, d=10, e=9, f=15, g=14)
out = {PIN[s]: 'L' if s in SEG[5] else 'H' for s in 'abcdefg'}
assert out == {13: 'L', 12: 'H', 11: 'L', 10: 'L', 9: 'H', 14: 'L', 15: 'L'}
assert SEG[3] == 'abcdg' and SEG[4] == 'bcfg'
# 5상태 최소 비트, Toggle
assert next(k for k in range(9) if 2 ** k >= 5) == 3
assert all(int(jk(q, 1, 1)) == 1 - q for q in (0, 1))
print(json.dumps(dict(status='pass', ripple=[f'{a}{b}' for a, b in r], sync=[f'{a}{b}' for a, b in s], mod6=[f'{a}{b}{x}' for a, b, x in m], bcd=[d * 8 + cc * 4 + b * 2 + a for d, cc, b, a in c]), ensure_ascii=False))
