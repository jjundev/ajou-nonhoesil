"""결선도 넷에서 74HC 게이트 논리를 돌린다 — v2 시험판의 진리표 검사용.

렌더러 `nets()` 는 "무엇과 무엇이 한 스트립 묶음인가" 까지만 안다. 회로가 교안 함수를
내는지는 아무도 보지 않았다(승인본은 netlist 핀 줄과 대조한다). 시험판은 교안 핀 번호를
일부러 바꾸므로 핀 줄 대조를 못 쓴다 — 그래서 넷을 직접 돌린다. 관측 넷의 **상류만**
평가한다: 중계로 쓴 미사용 게이트는 입력 일부만 물려 있어 출력까지 계산하면 뜬 입력이다.
"""
import re

PINMAP = {
    '74HC04': [((1,), 2), ((3,), 4), ((5,), 6), ((9,), 8), ((11,), 10), ((13,), 12)],
    '74HC20': [((1, 2, 4, 5), 6), ((9, 10, 12, 13), 8)],
    '74HC11': [((1, 2, 13), 12), ((3, 4, 5), 6), ((9, 10, 11), 8)],
}
_FUNC = {'74HC04': lambda v: 1 - v[0],
         '74HC20': lambda v: 0 if all(v) else 1,
         '74HC11': lambda v: 1 if all(v) else 0}
_PIN = re.compile(r'^(74HC\d+)#(\d+) pin (\d+)$')
_INPUT = re.compile(r'^입력 (\S+)$')


class SimError(Exception):
    pass


def _index(nets):
    where = {}
    for i, n in enumerate(nets):
        for lab in n['labels']:
            if lab in where and where[lab] != i:
                raise SimError(f'{lab} 이 두 넷에 있다')
            where[lab] = i
    return where


def _drivers(nets):
    """넷 번호 → [(칩, 행, 입력핀들)] — 그 넷에 출력핀이 앉은 게이트."""
    out = {}
    for i, n in enumerate(nets):
        for lab in n['labels']:
            m = _PIN.match(lab)
            if not m or m.group(1) not in PINMAP:
                continue
            chip, row, pin = m.group(1), m.group(2), int(m.group(3))
            for ins, o in PINMAP[chip]:
                if o == pin:
                    out.setdefault(i, []).append((chip, row, ins))
    return out


def value_of(nets, label, inputs):
    """`label` 이 든 넷의 논리값(0/1). 입력 점퍼 `입력 X` 의 값은 `inputs['X']`."""
    where = _index(nets)
    drivers = _drivers(nets)
    if label not in where:
        raise SimError(f'{label} 이 어느 넷에도 없다')
    memo, busy = {}, set()

    def ev(i):
        if i in memo:
            return memo[i]
        if i in busy:
            raise SimError(f'되먹임: {sorted(nets[i]["labels"])}')
        busy.add(i)
        n = nets[i]
        srcs = []
        if 'vcc' in n['rails']:
            srcs.append(1)
        if 'gnd' in n['rails']:
            srcs.append(0)
        for lab in n['labels']:
            m = _INPUT.match(lab)
            if m:
                if m.group(1) not in inputs:
                    raise SimError(f'{lab} 의 값이 없다')
                srcs.append(int(inputs[m.group(1)]))
        gates = drivers.get(i, [])
        if len(srcs) + len(gates) > 1:
            raise SimError(f'한 넷에 출력 둘 이상: {sorted(n["labels"])}')
        if gates:
            chip, row, ins = gates[0]
            vals = []
            for p in ins:
                lab = f'{chip}#{row} pin {p}'
                if lab not in where:
                    raise SimError(f'뜬 입력: {lab}')
                vals.append(ev(where[lab]))
            srcs.append(_FUNC[chip](vals))
        if not srcs:
            raise SimError(f'뜬 넷: {sorted(n["labels"])}')
        busy.discard(i)
        memo[i] = srcs[0]
        return srcs[0]

    return ev(where[label])
