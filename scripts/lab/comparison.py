"""Explicit stepped comparisons; authored logical expectations never become actual data."""
from .notation import bit_of
from .leds import lit, circled

ACTUAL = "실제 결과"
BIT_GUIDE = "불일치 시 실제 BIT1~BIT6을 이름 순서로 적어요. 예: 001101. 1=켜짐, 0=소등이에요."
GUIDE = "실제 결과 — 맞으면 ✓, 다르면 실제 값을 적어요. 안 본 행은 비워 둬요."

def comparison_error(table):
    mode = getattr(table, 'comparison', None)
    if mode is None:
        return None
    if mode != 'led' or table.kind != 'stepped':
        return 'comparison: led 는 stepped 표에만 쓴다'
    outputs = table.outputs or []
    if not outputs or len(set(outputs)) != len(outputs) or any(table.header.count(n) != 1 for n in outputs):
        return '비교 표 outputs 는 중복 없이 존재하는 출력 열을 선언해야 한다'
    if table.encoding not in ('0/1', 'H/L') or not table.rows:
        return '비교 표의 encoding 또는 행이 없다'
    for row in table.rows:
        if len(row) != len(table.header) or any(not c.strip() for c in row):
            return '비교 표의 입력·예상값은 빈칸 없이 작성해야 한다'
        if any(bit_of(row[table.header.index(n)], table.encoding) is None for n in outputs):
            return '비교 표 예상 출력은 encoding 에 맞는 비트여야 한다'
    return None

def comparison_rows(table, leds=()):
    error = comparison_error(table)
    if error:
        raise ValueError(f'{table.id}: {error}')
    indices = [table.header.index(n) for n in table.outputs]
    ins = [i for i in range(len(table.header)) if i not in indices]
    if leds and any(not any(l.tag == n for l in leds) for n in table.outputs):
        raise ValueError(f'{table.id}: 예상 출력의 LED 위치·극성 정보가 없다')
    lamps = [(n, next((l for l in leds if l.tag == n), None)) for n in table.outputs]
    result = []
    for row in table.rows:
        on, off = [], []
        for n, led in lamps:
            bit = bit_of(row[table.header.index(n)], table.encoding)
            label = f'{circled(led.index)}{n}' if led else n
            (on if lit(bit, led.active_low if led else False) else off).append(label)
        # Keep every authored input, including clock edges and initialization controls.
        inputs = '; '.join(f'{table.header[i]}={"반복 클록" if row[i] == "RUN" else row[i]}' for i in ins if table.header[i] not in ('스텝', '조작'))
        step = row[table.header.index('스텝')] if '스텝' in table.header else str(len(result)+1)
        action = row[table.header.index('조작')] if '조작' in table.header else ''
        result.append([step, action, inputs, ' · '.join(on) or '없음', ' · '.join(off) or '없음', ''])
    return ['스텝', '조작', '입력 설정', '예상 켜지는 LED', '예상 꺼지는 LED', ACTUAL], result
