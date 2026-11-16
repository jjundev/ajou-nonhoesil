"""실험10 노트·문항 표의 값을 원리에서 다시 계산해요. 결과를 JSON으로 내요.

사용: python check_values.py [out.json]
"""
import json, sys, itertools
from fractions import Fraction as Fr

R = {}


def ok(name, cond, detail=''):
    R[name] = dict(pass_=bool(cond), detail=detail)
    if not cond:
        print('FAIL', name, detail)


def close(a, b, tol=1e-6):
    return abs(a - b) <= tol

# t-start: 1V/LSB 4비트
ok('start-dac', [int('0101', 2), int('1010', 2)] == [5, 10])
ok('start-adc', [int(5.0 // 1), int(5.4 // 1)] == [5, 5], '내림 규칙에서 5.0V, 5.4V 모두 0101')

# t-opamp: 이상 반전 증폭기, 공급 ±15V
def inv(vin, r1, rf, vs=15):
    v = -rf / r1 * vin
    return max(-vs, min(vs, v)), v
ok('opamp-rows', [inv(1, 1.5, 4.5)[0], inv(2, 1.5, 4.5)[0], inv(1, 1.5, 2.7)[0]] == [-3, -6, -1.8000000000000003] or
   all(close(a, b) for a, b in zip([inv(1, 1.5, 4.5)[0], inv(2, 1.5, 4.5)[0], inv(1, 1.5, 2.7)[0]], [-3, -6, -1.8])))
ok('opamp-sat', inv(6, 1.5, 4.5) == (-15, -18.0))
ok('opamp-supp', close(inv(0.5, 1, 4.5)[0], -2.25))
ok('tf-02', close(inv(1, 1.5, 9)[0] / inv(1, 1.5, 4.5)[0], 2))
ok('blank-02', close(-4.5 / 1.5, -3))

# t-summing: 24k/12k/6k/3k, Rf 4.5k, 5V
Ri = {'QA': 24, 'QB': 12, 'QC': 6, 'QD': 3}
def summ(n, rf=4.5, vh=5):
    bits = {'QA': n & 1, 'QB': n >> 1 & 1, 'QC': n >> 2 & 1, 'QD': n >> 3 & 1}
    return -rf * sum(vh * b / Ri[k] for k, b in bits.items())
want = {1: -0.9375, 2: -1.875, 7: -6.5625, 8: -7.5, 9: -8.4375, 5: -4.6875}
ok('summing-rows', all(close(summ(n), v) for n, v in want.items()), {n: summ(n) for n in want})
ok('summing-linear', all(close(summ(n), n * summ(1)) for n in range(16)))

# t-network: 3비트, VR=8. 공식과 노드 해석(가중: 밀만 RL→∞, 래더: 테브난 사다리)
def weighted(bits, vr=8):
    n = len(bits)
    rs = [2 ** k for k in range(n)]  # D1 → R, D2 → 2R ...
    return sum(Fr(vr * b, r) for b, r in zip(bits, rs)) / sum(Fr(1, r) for r in rs)
def ladder(bits, vr=8):
    # 끝 2R 접지에서 시작해 Dn → D1 쪽으로 테브난 등가를 쌓아요. D1 노드가 출력(개방)이에요.
    vth, rth = Fr(0), Fr(2)  # 2R 접지 (R=1)
    for i, b in enumerate(reversed(bits)):
        if i > 0:
            rth += 1  # 사이 R
        # 노드에 2R로 D 연결: 두 소스 병렬 합성
        v2, r2 = Fr(vr * b), Fr(2)
        vth = (vth / rth + v2 / r2) / (1 / rth + 1 / r2)
        rth = 1 / (1 / rth + 1 / r2)
    return vth
def formula(bits, den, vr=8):
    n = len(bits)
    return Fr(vr * sum(2 ** (n - 1 - i) * b for i, b in enumerate(bits)), den)
rows = {'001': (Fr(8, 7), Fr(1)), '100': (Fr(32, 7), Fr(4)), '111': (Fr(8), Fr(7))}
good = True
for code, (w, l) in rows.items():
    bits = [int(c) for c in code]
    good &= weighted(bits) == w == formula(bits, 7) and ladder(bits) == l == formula(bits, 8)
for bits in itertools.product([0, 1], repeat=4):
    good &= weighted(list(bits)) == formula(list(bits), 15) and ladder(list(bits)) == formula(list(bits), 16)
ok('network-rows-and-4bit-exhaustive', good)
ok('network-supp', 2 ** 3 * 1 == 8)

# t-7490: BCD 순환
seq = [n % 10 for n in range(11)]
ok('7490-cycle', seq[9] == 9 and seq[10] == 0 and format(6 + 2, '04b') == '1000')

# t-oc: 두 번 반전 + 오픈 컬렉터
def chain(q, pullup=True):
    n1 = 1 - q
    pulls = n1 == 1
    return 0 if pulls else (5 if pullup else None)
ok('oc-rows', chain(0) == 0 and chain(1) == 5 and chain(1, False) is None)
ok('oc-path', [round(1.5 + r, 1) for r in (22.6, 10.5, 4.5, 1.5)] == [24.1, 12.0, 6.0, 3.0])
ok('oc-supp', (0 if 1 == 1 else 5) == 0, 'QA=1 바로 7405 → 당김 0V')

# t-dac
ok('dac-desc', all(summ(n + 1) < summ(n) for n in range(9)) and summ(0) > summ(9), '반전이라 내림차순, 9→0에서 위로')
ok('dac-time', close(1 / 1000 * 1000, 1) and close(10 / 1000 * 1000, 10), '1kHz: 1ms/단, 10ms/주기')
ok('dac-rf', close(2.7 / 4.5, 0.6) and close(0.5 * 2.7 / 4.5, 0.3))
par = 10.5 * 68 / (10.5 + 68)
ok('dac-parallel', close(round(par, 1), 9.1), par)
# 출력 식 V+ + Rf Σ(V+−Vi)/Ri 는 V+=0에서 반전 가산기와 같아요
ok('dac-formula', all(close(0 + 4.5 * sum((0 - 5 * b) / r for b, r in zip(bits, (24, 12, 6, 3))), summ(sum(b << i for i, b in enumerate(bits)))) for bits in itertools.product([0, 1], repeat=4)))

# t-comparator: Vout = Vs+ if V+ > V− else Vs−
def cmp(vp, vm):
    return 15 if vp > vm else 0
ok('cmp-rows', [cmp(8.5, v) for v in (10, 9, 8, 7)] == [0, 0, 15, 15])
ok('cmp-supp', next(n for n, v in zip(range(2, 6), (10, 9, 8, 7)) if cmp(9.5, v) == 15) == 3)

# t-adc
ok('flash', [2 ** n - 1 for n in (2, 3, 4, 8)] == [3, 7, 15, 255])
def sar(vin, n=4):
    code, log = 0, []
    for k in reversed(range(n)):
        t = code | 1 << k
        keep = vin >= t
        log.append((format(t, f'0{n}b'), keep))
        if keep:
            code = t
    return code, log
code, log = sar(6.3)
ok('sar', code == 6 and log == [('1000', False), ('0100', True), ('0110', True), ('0111', False)], log)
ok('counter-steps', next(n for n in range(1, 16) if n > 6.3) == 7)
ok('sar-8bit', len(sar(100.2, 8)[1]) == 8)

# 문항
ok('q-summing-equal', close(-(1 + 2 + 3), -4.5 * (1 / 4.5 + 2 / 4.5 + 3 / 4.5)))
ok('q-comparator-dir', cmp(8.5, 9) == 0 and cmp(8.5, 8) == 15, 'DAC가 반전 입력: DAC > 기준이면 0V (제공 답안과 반대)')

out = {k: dict(pass_=v['pass_'], detail=str(v['detail'])) for k, v in R.items()}
fails = [k for k, v in R.items() if not v['pass_']]
print(f'{len(R) - len(fails)}/{len(R)} pass')
if len(sys.argv) > 1:
    json.dump(dict(checks=out, failed=fails), open(sys.argv[1], 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
sys.exit(1 if fails else 0)
