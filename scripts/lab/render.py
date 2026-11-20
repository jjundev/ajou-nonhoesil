"""kind 별 인쇄 레이아웃. 실험실 조건이 설계 제약이다.

확인 칸은 세로로 정렬되어야 한다 — 세로줄 하나로 관통해 "전항 일치"를 표기하는
방식이 태블릿 필기에서 가장 빠르기 때문이다. 칸과 숫자 사이에는 vision 전사가
체크와 숫자를 구분할 여백이 있어야 한다.

`role: reference` 표는 인쇄본에서 제외한다. 실험실에서 채우는 물건이 아니라
예비보고서 이론 절의 재료다.
"""

import ast
import html
import json
import re
from dataclasses import replace
from pathlib import Path

from . import md, observations
from .comparison import comparison_rows
from . import nodes as node_calc
from .leds import (board_leds, circled, feeds_by_stage, feeds_by_circuit, is_sequential, lit, record_leds,
                   record_row_leds, watched)
from .netlist_parser import IC_DECL
from .notation import normalize_cell, bit_of
from .spec_parser import split_indices
from .photo_names import item_token, photo_name
from . import config
from .fit_pages import FIT_PLAIN
from .io_locations import input_columns, location_name, location_order, locations_html

MAX_BREADBOARD_ROWS = 30
# Breadboard.jpg(998×1345px) 상단에 아주대학교 로고 + 범례 원 3개가 있다.
# 인쇄 폭 190mm(prep-lab-checklist 의 @page 여백 기준: 210 - 10*2) 로 렌더링한
# 뒤 실측(픽셀 경계 대조 + 리뷰 재현)하면 실제 격자는 위에서 약 51.4mm
# 아래에서 시작한다. object-position: top 크롭이 이 띠를 예산에 안 넣으면,
# IC 가 적은 주차는 격자가 한 줄도 없이 로고만 인쇄된다 (B1).
_BREADBOARD_HEADER_MM = 51.4


# 결선도가 없는 회로 자리에 까는 빈 판형 — 판형 버전 -> (루트 기준 경로, 격자 머리띠 mm).
# 머리띠는 인쇄 폭 190mm 로 그렸을 때 1행 홀 위끝까지의 높이다. v1 은 위 실측값, v2 는
# geometry.json 에서 셈한다: (row1_center_y 336 − hole_size/2 4) / 폭 1200 × 190 = 52.6
# (`test_lab_render` 가 geometry 와 맞댄다 — 판형을 다시 뽑으면 거기서 걸린다)
BLANK_BOARDS = {
    "v1": (".claude/assets/Breadboard.jpg", _BREADBOARD_HEADER_MM),
    "v2": (".claude/assets/breadboard_v2/Breadboard_v2.png", 52.6),
}


def board_version_of(board_file: Path, experiment: int = 1) -> str:
    """주차 `배치.py` 의 `BOARD` — 엔진을 import 하지 않고 ast 로 읽는다.

    파일이 없으면 그 실험의 기본 판형(`config.default_board`)이다 — 체크리스트는 결선도보다
    먼저 나올 수 있다. 파일이 있는데 상수가 없으면 v1 이되, 판형이 v2 로 바뀐 실험부터는
    엔진 `require_board()` 처럼 거절한다. 상수는 문자열 리터럴이어야 한다 — 인쇄가
    PIL·렌더러에 묶이면 안 된다(`_diagram_html`).
    """
    if not board_file.exists():
        return config.default_board(experiment)
    for node in ast.parse(board_file.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "BOARD" for t in node.targets):
            try:
                value = ast.literal_eval(node.value)
            except ValueError:
                raise ValueError(f"{board_file}: BOARD 는 문자열 리터럴로 적는다 — "
                                 f"BOARD = 'v2' 꼴 ({ast.unparse(node.value)!r})") from None
            if value not in BLANK_BOARDS:
                raise ValueError(f"{board_file}: BOARD 는 {tuple(BLANK_BOARDS)} 중 하나다: {value!r}")
            return value
    want = config.default_board(experiment)
    if want != "v1":
        raise ValueError(f"{board_file}: 실험{experiment} 부터 판형은 {want} 다 — "
                         f"머리에 BOARD = '{want}' 를 둔다")
    return "v1"


def crop_rows(netlist_text: str) -> int:
    """netlist 가 실제로 쓰는 행 수. 브레드보드 템플릿을 여기에 맞춰 자른다.

    회로 본문을 넘긴다 — 결선도가 없는 회로의 fallback 격자 크기를 정한다.
    """
    ic_count = len(IC_DECL.findall(netlist_text))
    rows = max(6, ic_count * 8)
    return min(rows, MAX_BREADBOARD_ROWS)


_EMPHASIS = re.compile(r"\*{1,2}([^*]+)\*{1,2}")
_CODE = re.compile(r"`([^`]+)`")
_STRIKE = re.compile(r"~{2}([^~]+)~{2}")


def _esc(text) -> str:
    return html.escape(str(text), quote=False)


def _plain(text: str) -> str:
    """netlist 의 마크다운 표기를 벗긴다. 안 벗기면 인쇄본에 `**` 와 백틱이
    그대로 찍힌다.

    짝이 맞는 것을 먼저 벗기고, 남은 낱개 기호도 지운다 — 여러 줄에 걸친
    코드 스팬은 줄을 합친 뒤에도 짝이 안 맞을 수 있다. 이 도메인에서 `*` 와
    백틱은 내용이 아니라 항상 표기다.

    `~~` 취소선도 짝이 맞을 때만 벗긴다 — 실험05 미확정 표가 닫힌 항목을
    취소선으로 표시하는데, 안 벗기면 물결표째 인쇄본에 찍힌다. 낱개 `~` 는
    `*`·백틱과 달리 지우지 않는다 — 실험10 이 `p15~p16` 처럼 쪽 범위
    구분자로 흔히 쓴다. 짝 없는 `~` 를 지우면 그 범위 표기가 붙어 버린다.
    """
    text = _STRIKE.sub(r"\1", _CODE.sub(r"\1", _EMPHASIS.sub(r"\1", text)))
    return text.replace("`", "").replace("*", "")


_ORDER_NOTE = ("순서 열 번호대로 입력을 넣어요. 이 회로는 직전 상태를 기억해서, 같은 입력이라도 "
               "앞에 넣은 행에 따라 LED 가 달라요")


def _truth_table_html(table, token=None, badges=None, order=(), leds=(), png=None) -> str:
    """진리표 — 입력은 주어지고, 출력에 `예상` 을 병기한 뒤 확인 칸을 붙인다.

    `_plain` 으로 마크다운 표기를 먼저 벗기고 나서 `normalize_cell` 로 논리값을
    정규화한다 — 순서가 반대면 `**1**` 같은 굵게 표기 셀이 정규화를 통과하지
    못하고 별표째 인쇄본에 남는다.

    `token`(항목 토큰, 예 `1-2`)이 있으면 행마다 찍을 사진 파일명 열을 붙인다 —
    `contact_sheet` 가 그대로 읽는 `<항목> <입력비트>.jpg` 다. 비트는 입력 **자리**
    순서다. 입력 셀이 0/1 이 아니면(don't-care 등) 한 장으로 찍을 조합이 아니라 `—`.
    `.check` 가 아니라 `.photo-name` 이다 — `.check` 개수는 행 수 불변식이다.

    `badges`(출력 이름 → `LED⑦`)가 있으면 그 출력 머리 아래에 보드 LED 번호를 단다 — 출력 열
    순서는 명세 그대로 두고, 어느 불을 볼지만 알린다(v2 주차, 2026-10-11).

    `png`(결선도)가 있으면 **입력 열**만 표 위 위치도와 같은 묶음·위→아래 순서로 다시 세운다
    (2026-11-14 사용자). 행 순서·사진 파일명 비트는 명세 자리 그대로다 — `기록.md`·
    `contact_sheet` 가 그 순서로 읽는다.

    순차 회로 표(래치·플립플롭 — 출력 셀에 `Q(t-1)`)는 둘을 더 단다(2026-10-11 사용자, 실험06).
    `order`(netlist 회로의 `order`, 넣는 순서대로 적은 행 번호)가 있으면 맨 앞에 `순서` 열(①②…)을
    두고 — 행은 교안 순서 그대로다, 사진 파일명·`기록.md` 와 맞아야 한다 — 보드 `leds` 중 출력을
    보는 LED(`Q`, 그 반대 `Q'`)가 있으면 출력 뒤에 `켜지는 LED`·`꺼지는 LED` 두 열을 둔다. 유지·반전
    행은 두 칸을 합쳐 `직전 그대로` 다. 그때 LED 배지는 두 열이 대신하므로 달지 않는다. 조합 회로
    표(실험05)는 단계 LED 표와 배지가 맡아 두 열을 달지 않는다 — 출력 열이 많아 쪽 폭을 넘는다.
    """
    # 셀은 이름이 아니라 자리로 찾는다 — 입력과 출력이 같은 글자인 표가 있다
    # (실험3 반감산기 `A B D B`). `record._truth_table` 과 같은 규약이다.
    spec_inputs, outputs = split_indices(table)
    inputs = [spec_inputs[k] for k in
              location_order(png, [_plain(table.header[i]) for i in spec_inputs])]
    badges = badges or {}
    rank = {k: n for n, k in enumerate(order, start=1)} if len(order) == len(table.rows) else {}
    seen = record_leds(leds, table.header, outputs) if is_sequential(table, outputs) else []
    if seen:
        badges = {}
    names = {led.tag: f"{circled(led.index)}{_esc(led.tag)}" for led, _, _ in seen}
    head = ((["순서"] if rank else [])
            + [_esc(table.header[i]) for i in inputs]
            + [f"{_esc(table.header[i])}예상"
               + (f"<br><small>{_esc(badges[table.header[i]])}</small>"
                  if table.header[i] in badges else "")
               for i in outputs])
    body = [[normalize_cell(_plain(row[i])) for i in inputs]
            + [normalize_cell(_plain(row[i])) for i in outputs]
            for row in table.rows]

    # thead/tbody 로 나눈다 — 표가 쪽을 넘어가도 헤더가 따라가야 한다.
    # 헤더 없는 진리표 조각은 실험실에서 읽을 수 없다.
    out = []
    if rank:
        out.append(f"<p class='src order-note'>{_esc(_ORDER_NOTE)}</p>")
    if seen:
        legend = " ".join(names[led.tag] + (f" = {_esc(table.header[i])}"
                                              + ("의 반대" if inv else ""))
                          for led, i, inv in seen)
        polarity = {led.active_low for led, _, _ in seen}
        tail = ("" if len(polarity) > 1
                else " — 모두 0이면 켜짐" if polarity.pop() else " — 모두 1이면 켜짐")
        out.append(f'<p class="led-legend"><b>보는 LED:</b> {legend}{tail}</p>')
    out += ['<table class="led-table">' if seen else "<table>", "<thead>", "<tr>"]
    out += [f"<th>{h}</th>" for h in head]
    if seen:
        out.append("<th>켜지는 LED</th><th>꺼지는 LED</th>")
    out.append("<th>확인</th>" + ("<th>사진 파일명</th>" if token else "") + "</tr>")
    out += ["</thead>", "<tbody>"]
    for k, (raw, row) in enumerate(zip(table.rows, body), start=1):
        cells = (f'<td class="order">{circled(rank[k])}</td>' if rank else "")
        cells += "".join(f"<td>{_esc(c)}</td>" for c in row)
        if seen:
            got = record_row_leds([_plain(c) for c in raw], seen)
            if isinstance(got, str):
                cells += f'<td class="led hold" colspan="2">{_esc(got)}</td>'
            else:
                on, off = got
                cells += (f'<td class="led on">{" ".join(names[l.tag] for l in on) or "없음"}</td>'
                          '<td class="led off">'
                          + (" ".join(names[l.tag] + (" 미정" if unknown else "")
                                      for l, unknown in off) or "없음") + "</td>")
        cells += '<td class="check"></td>'
        if token:
            bits = [normalize_cell(_plain(raw[i])) for i in spec_inputs]
            name = (photo_name(token, "".join(bits))
                    if all(b in ("0", "1") for b in bits) else "—")
            cells += f'<td class="photo-name">{_esc(name)}</td>'
        out.append(f"<tr>{cells}</tr>")
    out += ["</tbody>", "</table>"]
    return "\n".join(out)


def _input_settings_html(names, rows, *, spaced=True, columns=None):
    """Highlight physical input work; each call starts an independent timeline.

    Explicit edges are events even when repeated. Static levels compare against
    the preceding ending level, not the preceding token. Unknown tokens remain
    visible but do not establish an inferred physical level.

    `columns` 는 `io_locations.input_columns` 의 결과다. 주어지면 칸을 표 위 위치도와
    같은 묶음·위→아래 순서로 쌓는다(위치 미러 칸). None 이면 명세 순서의 한 줄 목록.
    """
    levels = {}
    result = []
    bits = {'0': '0', '1': '1', 'L': '0', 'H': '1'}
    equal = ' = ' if spaced else '='
    for index, cells in enumerate(rows):
        settings = []
        for name, cell in zip(names, cells):
            parts = re.split(r'\s*(?:->|→)\s*', cell.strip())
            edge = len(parts) > 1 and all(p in bits for p in parts)
            end = bits.get(parts[-1]) if edge else ('RUN' if cell.strip() == 'RUN' else bits.get(cell.strip()))
            changed = index > 0 and (edge or (
                end is not None and levels.get(name) is not None and end != levels[name]))
            label = '반복 클록' if cell == 'RUN' else cell
            text = f'{_esc(name)}{equal}{_esc(label)}'
            settings.append(f'<span class="input-change">{text}</span>' if changed else text)
            levels[name] = end
        if columns is None:
            result.append('<br>'.join(settings))
            continue
        by_name = dict(zip(names, settings))
        cols = ''.join('<div class="col">' + ''.join(
                           f'<span class="slot">{by_name[n]}</span>' for n in picked) + '</div>'
                       for _, picked in columns)
        result.append(f'<div class="mirror" style="--g:{len(columns)}">{cols}</div>')
    return result


def _mirror_head(columns):
    """'입력 설정' 머리 밑의 묶음 이름 줄 — 칸 안 열과 같은 격자라 세로선이 맞는다."""
    if not columns:
        return ''
    return (f'<div class="mirror-head" style="--g:{len(columns)}">'
            + ''.join(f'<span>{_esc(side)}</span>' for side, _ in columns) + '</div>')


def _mirror(png, names):
    columns = input_columns(png, list(names))
    return columns, _mirror_head(columns)


def _comparison_table_html(header, rows, *, input_settings=None, input_column=1, input_head=''):
    # 6·7열은 입력 칸이 위치 미러로 두세 열을 품는다 — 조작·LED 칸에서 폭을 가져온다.
    out = ['<table class="comparison-table"><colgroup>' + ''.join(
               f'<col style="width:{w}%;">' for w in ({4:[7,43,32,18],5:[7,35,22,22,14],
                   6:[7,19,24,18,18,14], 7:[6,17,27,13,13,13,11],
                   # 8열 = LED 판독 + 유지·반전·미정 + 프로브 측정 핀
                   8:[5,14,18,11,11,11,18,12]}
                   .get(len(header),[100/len(header)]*len(header))
                   # LED 판독 + 프로브 측정 핀 7열(실험10 V1~V3) — 측정 핀 칸에 폭을 준다
                   if not (len(header) == 7 and '측정 핀·예상값' in header)
                   else [6,14,20,15,15,18,12]))
               + '</colgroup><thead><tr>',
           *[f'<th>{_esc(h)}{input_head if i == input_column and input_settings is not None else ""}</th>'
             for i, h in enumerate(header)], '</tr></thead><tbody>']
    for row_index, row in enumerate(rows):
        out.append('<tr>')
        for i, value in enumerate(row):
            if i == len(row)-1:
                out.append('<td class="actual"></td>')
            elif input_settings is not None and i == input_column:
                # Only renderer-built input markup, with source text already escaped.
                out.append('<td>' + input_settings[row_index] + '</td>')
            else:
                out.append('<td>' + _esc(value).replace('; ', '<br>') + '</td>')
        out.append('</tr>')
    out.append('</tbody></table>')
    return '\n'.join(out)


def _stepped_html(table, *, wide=False, leds=(), png=None) -> str:
    """스텝표 — **명세가 저작해 둔 빈 셀**이 실험실에서 채울 칸이다.

    `확인` 열을 붙이지 않는다. `확인` 은 "✓ 일치 / 값 = 불일치" 규약이라
    **예상값이 있어야** 뜻이 있는데 스텝표에는 없다. 붙이면 비교 대상 없는 빈
    칸이 하나 더 생기고, 실험02 T3~T5·T7 처럼 이미 `기록` 열을 저작한 표에서는
    같은 뜻의 칸이 둘이 된다.

    빈 셀이 하나도 없는 표에만 `기록` 열을 만든다 — 그런 표는 채울 곳이 없다.

    `.check` 가 아니라 `.fill` 을 쓴다. `.check` 개수는 명세의 `truth-table`
    행 수와 대조되는 불변식이라 다른 뜻의 칸을 섞으면 그 검사가 죽는다.

    셀에 `normalize_cell` 을 씌우지 않는다 — 스텝표 셀은 don't-care 축이 아니라
    스텝·조작·측정 지시가 드는 자리다. 씌우면 실험02 T4 의 `-` 나 `x` 가 논리
    don't-care `X` 로 둔갑한다. 마크다운 표기만 `_plain` 으로 벗긴다.
    """
    if getattr(table, 'comparison', None):
        header, rows = comparison_rows(table, leds)
        indices = [i for i, name in enumerate(table.header)
                   if name not in (*table.outputs, '스텝', '조작')]
        names = [table.header[i] for i in indices]
        columns, head = _mirror(png, names)
        settings = _input_settings_html(names, [[row[i] for i in indices] for row in table.rows],
                                       spaced=False, columns=columns)
        return _comparison_table_html(header, rows, input_settings=settings, input_column=2,
                                      input_head=head)
    header = list(table.header)
    rows = [[_plain('반복 클록' if c == 'RUN' else c) for c in row] for row in table.rows]
    if not any(not c.strip() for row in rows for c in row):
        header.append("기록")
        rows = [row + [""] for row in rows]

    # v3의 넓은 스텝표는 조작 문장을 읽을 폭을 확보한다. 값·열 순서·기록 칸은 그대로다.
    wide = wide and len(header) >= 10 and "조작" in header
    if wide:
        weights = [9 if h == "조작" else 3 if len(h) > 6 else 2 for h in header]
        cols = "".join(f'<col style="width:{w / sum(weights) * 100:.4f}%;">' for w in weights)
        out = ['<table class="record-stepped-wide">', f'<colgroup>{cols}</colgroup>', "<thead>", "<tr>"]
    else:
        out = ["<table>", "<thead>", "<tr>"]
    out += [f"<th>{_esc(h)}</th>" for h in header]
    out += ["</tr>", "</thead>", "<tbody>"]
    for row in rows:
        out.append("<tr>" + "".join(
            '<td class="fill"></td>' if not c.strip() else
            f'<td class="record-action">{_esc(c)}</td>' if wide and header[i] == "조작" else f"<td>{_esc(c)}</td>"
            for i, c in enumerate(row)) + "</tr>")
    out += ["</tbody>", "</table>"]
    return "\n".join(out)


_READOUT = ("판독 조건 — CH1 ______ V/div · CH2 ______ V/div · "
            "time/div ______ · 프로브 ______× · 모드  [ ] Y-T   [ ] X-Y")
_CAPTION = "캡션: ____________________     사진 파일: ____________________"


def _capture_html(table, spec_dir=None) -> str:
    """파형은 셀 표가 아니다 — 스케치 격자와 판정 기준을 낸다.

    `expected` 를 통째로 싣고 마크다운 표기를 벗긴다. 안 벗기면 실험02 T2 의
    `**두 갈래로 갈라져**` 가 별 두 개째로 인쇄된다 — 옛 `_capture_html` 은
    `_plain` 을 안 씌웠다. 그리고 이 산문이 이 표의 판정 기준 **전부**다.
    진리표처럼 대조할 셀이 없으므로 한 줄로 줄이면 남는 게 없다.

    **판독 조건**을 함께 적는다. V/div 를 모르면 결과보고서에서 화면의 칸을
    볼트로 환산할 수 없고, X-Y 인지 Y-T 인지 모르면 실험02 T1·T2 의 곡선이
    무엇을 뜻하는지 알 수 없다 — 두 표는 같은 배선에서 모드만 다르다.

    파형에는 행별 불일치 표를 붙이지 않는다.
    파형에는 "불일치 행"도 "이상 스텝"도 없다 — `예상과 다른 점` 상자가 맡는다.

    `figure` 가 있으면 예상 개형 그림을 산문과 스케치 사이에 싣는다. 경로는
    명세 파일 위치(`spec_dir`) 기준이고, 인쇄본 HTML 도 같은 `체크리스트/` 에
    놓이므로 `src` 에 그대로 쓴다. 파일이 없으면 `<img>` 를 내지 않는다 —
    깨진 그림이 PDF 로 굳는다(`check_embedded_images` 가 잡는 결함).
    """
    expected = _plain(table.expected or "").strip()
    out = []
    if expected:
        out.append(f'<div class="expected"><b>예상</b> — {_esc(expected)}</div>')
    if table.figure:
        name = Path(table.figure).name
        if spec_dir is not None and (Path(spec_dir) / table.figure).exists():
            out.append(f'<img class="expected-fig" src="{_esc(table.figure)}">')
        else:
            out.append(f"<p class='src'>예상 그림이 아직 없어요: {_esc(name)}</p>")
    out.append('<div class="sketch"></div>')
    out.append(f"<p class='readout'>{_esc(_READOUT)}</p>")
    out.append(f"<p class='readout'>{_esc(_CAPTION)}</p>")
    out.append('<div class="differs"><b>예상과 다른 점</b></div>')
    return "\n".join(out)


_BULLET = re.compile(r"^([ \t]*)-[ \t]+(.*)$")


def _blocks(body: str) -> str:
    """`- ` 불릿·열 0 산문·`##` 헤딩·**마크다운 표**를 HTML 로.

    들여쓴 이어지는 줄을 앞 항목에 붙인다 — 버리면 여러 줄로 쓴 경고가 중간에서
    잘린다. 74HC02 핀 순서 경고가 실제로 세 줄짜리 불릿이고, 그 경고를 netlist
    스스로 "이 실험에서 가장 흔한 배선 실수"라고 표시한다.

    빈 줄 없이 이어지는 열 0 산문 줄은 한 문단으로 합친다 — netlist 의
    "다르면 배선 오류다" 경고가 실제로 두 줄이다.

    표는 **원문 위치에** 인쇄한다. 옛 렌더러는 `|` 로 시작하는 줄을 전부 버렸고,
    그래서 실험10 공통 규칙의 전원 레일 표(그 주차 최대 사고 지점)와 실험02·03·05
    회로 절의 소자 배치·팬아웃 표가 인쇄본에서 통째로 사라졌다. 여섯 주차에서
    169줄이다. 여기 실린 표는 참조용이라 체크박스를 받지 않는다 — 체크박스는
    칩 상자 안의 배선표만 받는다.
    """
    out, items, para = [], [], []

    def flush_items():
        if items:
            out.append("<ul>" + "".join(f"<li>{_esc(i)}</li>" for i in items)
                       + "</ul>")
            items.clear()

    def flush_para():
        if para:
            out.append(f"<p>{_esc(' '.join(para))}</p>")
            para.clear()

    lines = body.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        stripped = line.strip()
        if not stripped:
            flush_para()
            i += 1
            continue
        if stripped.startswith("|"):
            table, nxt = md.parse_table_at(lines, i)
            if table is None:
                i += 1                    # 구분선 없는 `|` 줄 — 표가 아니다
                continue
            flush_items()
            flush_para()
            out.append(_md_table_html(table))
            i = nxt
            continue
        if stripped.startswith("#"):
            flush_items()
            flush_para()
            out.append(f"<h4>{_esc(_plain(stripped.lstrip('# ')))}</h4>")
            i += 1
            continue
        m = _BULLET.match(line)
        if m and not m.group(1):
            flush_para()
            items.append(_plain(m.group(2)))
            i += 1
            continue
        if line.startswith((" ", "\t")) and items:
            items[-1] += " " + _plain(stripped)
            i += 1
            continue
        flush_items()
        para.append(_plain(stripped))
        i += 1
    flush_items()
    flush_para()
    return "\n".join(out)


def _md_table_html(table, lead_checkbox: bool = False) -> str:
    """마크다운 표를 인쇄용 HTML 로. 체크박스 열은 `.box` 다 — `.check` 는
    명세의 기록 대상 표 행 전용이고 개수를 테스트가 명세에서 세어 대조한다."""
    out = ["<table><thead><tr>"]
    if lead_checkbox:
        out.append("<th>확인</th>")
    out += [f"<th>{_esc(_plain(h))}</th>" for h in table.header]
    out.append("</tr></thead><tbody>")
    for row in table.rows:
        out.append("<tr>")
        if lead_checkbox:
            out.append('<td class="box"></td>')
        out += [f"<td>{_esc(_plain(c))}</td>" for c in row]
        out.append("</tr>")
    out.append("</tbody></table>")
    return "".join(out)


# 미확정 표(`M1`~) 참조. 표를 인쇄하지 않으므로(2026-09-28) 산문의 참조는 가리킬 곳이
# 없다 — netlist 원문은 저작·검토용이라 그대로 두고 인쇄할 때만 벗긴다. 순서가 중요하다:
# 괄호 전체가 참조인 것 → 괄호 안 끝 항목 → 괄호 안 첫 항목 → 문장 속 "— … M8" 꼬리.
_ISSUE_REF = r"M\d{1,2}"
_ISSUE_REF_RULES = (
    (re.compile(rf"\s*\((?:{_ISSUE_REF})(?:\s*[,·]\s*{_ISSUE_REF})*(?:\s+에서[^)]*)?\)"), ""),
    (re.compile(rf"\s*,\s*{_ISSUE_REF}(?=\s*\))"), ""),
    (re.compile(rf"\((?:{_ISSUE_REF})\s*,\s*"), "("),
    (re.compile(rf"\s*—\s*[^()—]*?\b{_ISSUE_REF}(?=\))"), ""),
)


def _drop_issue_refs(text: str) -> str:
    for rule, repl in _ISSUE_REF_RULES:
        text = rule.sub(repl, text)
    return text


def common_page(spec, netlist) -> str:
    """첫 장에 칩별 포트 역할 표만 싣는다."""
    return "\n".join(
        f'<div class="tblock"><h2>{_esc(_plain(section.title))}</h2>'
        + _blocks(section.body) + '</div>'
        for section in netlist.of_kind("lookup"))


_CHIP_LINE = re.compile(r"^-[ \t]+(U\d+[ \t]*=[ \t]*.+)$")
# ``## U1 = `7490` (decade counter)`` — 실험02·10 의 배선 표기. `IC_DECL` 은
# 이미 이 형식을 읽는다(netlist_parser.py). 렌더러만 못 읽어서 실험10 P1 의
# 배선 80줄이 통째로 사라졌다.
_CHIP_HEAD = re.compile(r"^#{2,}[ \t]+(U\d+[ \t]*=[ \t]*.+?)[ \t]*$")
_ANY_HEAD = re.compile(r"^#{1,}[ \t]+\S")

def _new_chip(head: str) -> dict:
    """칩 상자 하나.

    `blocks` 가 상자 **안**의 원문 순서다 — `("table", MdTable)` 은 체크박스를
    붙일 배선표, `("note", 원문 조각)` 은 그 밖의 산문·불릿이다. 고정 순서로
    찍으면 실험02 U1 의 `핀 번호 순서로 흐르지 않는다` 경고(표를 **읽기 전에**
    읽어야 한다)가 배선표 아래로 밀리고, U2 의 `…판독한 결과:` 도입문은 상자
    끝에 콜론만 남긴 채 끊긴다. 실험10 은 반대로 표가 먼저다 — 주차마다
    다르므로 원문을 따른다.

    `wires` 는 불릿형 전용이다 (`- U<n> =` 아래 들여쓴 `- ` 배선).
    """
    return {"type": "chip", "head": _plain(head), "wires": [], "unused": [],
            "blocks": []}


def _chip_tables(chip) -> list:
    """이 칩의 배선표. `blocks` 가 정본이라 따로 담지 않는다 — 두 벌을 두면
    표류한다."""
    return [payload for kind, payload in chip["blocks"] if kind == "table"]


def _absorb_wiring(chip, table) -> None:
    """헤딩형 칩 상자 아래의 마크다운 표를 배선표로 흡수한다.

    표를 **표인 채로** 남긴다 — 불릿으로 펴면 실험10 의 `핀 | 연결 | 왜` 가
    정렬을 잃고, 정렬이야말로 표로 적은 이유다. 행마다 앞에 체크박스 열이 붙는다.

    어느 셀에든 `미사용` 이 있으면 미사용 목록으로 뺀다. 열 위치를 못 박을 수
    없다 — 실험10 U2 표는 1열(`미사용 입력핀 11, 13`)이고 실험02 P4 U2 표는
    3열(`미사용 입력`)이다. 미사용은 배선 순서와 무관하게 **배선을 끝낸 뒤**
    칩마다 따로 확인하는 물건이라 목록이 갈려야 한다.
    """
    kept = []
    for row in table.rows:
        cells = [_plain(c).strip() for c in row]
        if not any(cells):
            continue
        if any("미사용" in c for c in cells):
            chip["unused"].append(" · ".join(c for c in cells if c))
        else:
            kept.append(row)
    if kept:
        chip["blocks"].append(("table", replace(table, rows=kept)))


def _chip_boxes(nodes) -> list:
    """노드 목록에서 칩 상자만. 미사용핀 상자와 테스트가 쓴다."""
    return [n for n in nodes if n["type"] == "chip"]


def _circuit_body(section):
    """회로 본문을 `(노드 목록, 첫 칩 앞 산문, 마지막 칩 뒤 산문)` 으로 가른다.

    `- U<n> = <칩>` 이 상자의 제목이고 그 아래 들여쓴 `- ` 가 배선이다. 옛
    렌더러는 들여쓰기를 무시하고 전부 형제 번호로 만들어 **칩의 경계가 사라졌다**.

    미사용핀 줄은 배선 목록에서 빼내되 **칩 안에 남긴다**. 회로 단위로 한데
    모으면 다칩 회로에서 같은 핀 번호가 정반대 지시를 동시에 받는다 — C4 의
    pin 4 는 U5 기준 GND, U6 기준 개방이다. 어느 칩 것인지 인쇄본에 단서가
    없으면 "출력을 GND 로 내려 칩을 죽이는" 바로 그 사고가 된다.

    칩과 칩 **사이**의 산문·표는 노드로 남겨 원문 순서를 지킨다 — 옛 3버킷
    분해로는 실험10 P1 의 `U3 → 가중 저항망 표 → U4` 를 표현할 수 없어 표가
    마지막 칩 뒤로 밀렸다.

    앞뒤 산문을 따로 돌려주는 이유는 원문이 그렇게 쓰여 있기 때문이다 — 앞은
    회로 소개와 배선 경고(`74HC02 의 핀 순서에 주의`)이고, 뒤는 배선을 마친 뒤
    하는 검산(`LED_X 와 LED_Z 가 같이 켜져야 한다`)이다. 한 덩어리로 합치면
    검산 지시가 배선 앞에 놓여 preamble 로 읽힌다.

    칩 선언이 하나도 없으면 상자를 만들지 않고 본문 전체를 앞쪽 산문으로
    흘린다. 조용히 버리는 것보다 낫다.
    """
    lines = section.body.split("\n")
    nodes, prose = [], []
    chip, last_key, form = None, None, None
    note = []                     # 헤딩형 상자 안에서 모으는 산문 조각

    def close_chip():
        nonlocal chip, last_key, form
        if chip is not None:
            flush_note()
            nodes.append(chip)
            chip, last_key, form = None, None, None

    def flush_prose():
        if any(p.strip() for p in prose):
            nodes.append({"type": "prose", "text": "\n".join(prose)})
        prose.clear()

    def flush_note():
        if any(n.strip() for n in note):
            chip["blocks"].append(("note", "\n".join(note)))
        note.clear()

    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        stripped = line.strip()

        head = _CHIP_HEAD.match(line) or _CHIP_LINE.match(line)
        if head:
            close_chip()
            flush_prose()
            chip = _new_chip(head.group(1))
            form = "heading" if stripped.startswith("#") else "bullet"
            i += 1
            continue

        if _ANY_HEAD.match(line):
            # 칩이 아닌 헤딩은 칩 상자를 닫는다. 상자는 `break-inside: avoid`
            # 라서 긴 해설(실험02 P4 의 `### 왜 pin 4 와 pin 8 인가`)을 품으면
            # 쪽 나눔이 무너진다.
            close_chip()
            prose.append(line)
            i += 1
            continue

        if stripped.startswith("|"):
            indented = line.startswith((" ", "\t"))
            table, nxt = md.parse_table_at(lines, i)
            if table is None:
                # 들여쓴 `|` 줄은 그 칩에 속한다 — 상자를 닫으면 뒤따르는
                # 배선과 미사용핀 지시가 통째로 상자 밖 산문으로 샌다.
                # 체크박스도 칩 라벨도 없이 `- ` 마커째 찍히고, 미사용핀
                # 상자가 사라진다. 플로팅 핀 지시를 잃는 바로 그 사고다.
                if form == "bullet" and not indented:
                    close_chip()          # 열 0 의 구분선 없는 `|` 줄만 닫는다
                i += 1
                continue
            if chip is not None and (form == "heading" or indented):
                flush_note()
                _absorb_wiring(chip, table)
            else:
                close_chip()
                prose.extend(lines[i:nxt])
            i = nxt
            continue

        if chip is not None and form == "bullet":
            if stripped.startswith("- ") and line.startswith((" ", "\t")):
                text = _plain(stripped[2:])
                last_key = "unused" if text.startswith("미사용") else "wires"
                chip[last_key].append(text)
                i += 1
                continue
            if line.startswith((" ", "\t")) and stripped and last_key:
                # **마지막으로 담은 목록**에 잇는다. `wires` 로 고정하면 미사용
                # 줄을 잇는 줄이 엉뚱한 배선 줄에 붙는다 — 플로팅 핀 지시를
                # 다른 항목에 조용히 재부착하는 것이라, 칩 라벨을 잃던 결함과
                # 같은 부류다.
                chip[last_key][-1] += " " + _plain(stripped)
                i += 1
                continue
            if stripped:
                close_chip()          # 열 0 줄이 불릿형 칩 상자를 닫는다

        if chip is not None and form == "heading":
            note.append(line)
            i += 1
            continue

        prose.append(line)
        i += 1

    close_chip()
    flush_prose()

    chip_at = [n for n, x in enumerate(nodes) if x["type"] == "chip"]
    if not chip_at:
        return [], "\n".join(x["text"] for x in nodes), ""
    first, last = chip_at[0], chip_at[-1]
    before = "\n".join(x["text"] for x in nodes[:first])
    after = "\n".join(x["text"] for x in nodes[last + 1:])
    return nodes[first:last + 1], before, after


def _has_walk(section) -> bool:
    """`## 단계` 표에 걷기 행(`<k>걷기`)이 **하나라도** 있는가 — 공통면 주의 상자가
    쓴다. 2026-09-20 걷기 보드 뒤로는 회로 **안**에서도 걷으므로 이쪽이 넓다.
    회로 경계 판정은 `_has_entry_walk` 다. 판정 자체는 파서가 `walk` 키로 냈다."""
    return any(st.get("walk") for st in section.stages or ())


def _has_entry_walk(section) -> bool:
    """`## 단계` 표의 **첫 행**이 걷기인가 — 앞 회로를 고쳐 이 회로를 만든다는 뜻이다.
    칩 교체 배너는 회로 경계 판정이라 이것만 본다. 회로 안 걷기(실험03 C2)는
    배너가 아니라 그 단계 블록이 지시한다."""
    stages = section.stages or ()
    return bool(stages) and bool(stages[0].get("walk"))


def _chip_swap(previous, current) -> str:
    """칩 교체 배너. 준비물이 종류당 하나라 순차 배선이 강제된다 (netlist M10).

    같은 칩이 다음 회로에도 쓰이면 패키지는 남지만 **점퍼선은 다르다** —
    netlist 가 "항목마다 재배선해 쓰는 것"이라고 적는다. `그대로 둔다` 로만
    적으면 배선까지 그대로 둬도 되는 것으로 읽힌다.

    `continues` 가 있는 회로는 예외다. 실험10 E10.P2 는 다 만든 DAC 에 `741`
    비교기를 하나 더 붙이는 회로라, 기본 문구(`점퍼선을 모두 걷는다`)를 그대로
    따르면 직전 회로를 뜯는다.

    `current.stages`(`## 단계` 표)가 있는 회로도 예외다 — 그 회로는 슬롯
    고정·기준선 비교로 그려져 앞 회로의 배선을 걷지 않는다. `모두 걷는다`
    문구를 그대로 두면 학생이 실제로 점퍼선을 다 뽑아 단계 그림의 회색(=
    그대로 둔다) 전제를 깬다. 대신 그림이 무엇을 걷고 새로 꽂을지
    지시한다고 말하는데, **어느 그림인지는 첫 행이 걷기냐가 가른다**: 첫 행이
    걷기(`<k>걷기`)면 걷을 선은 걷기 그림(빨간 점선)이, 아니면 (실험01 처럼
    걷기 보드로 들어가지 않는 회로) 단계 그림의 회색·번호·`걷는다` 표가
    지시한다. 걷기 행이 없는데 걷기 그림을 가리키면 없는 그림을 찾게 된다.
    """
    if previous is None:
        return "준비 — 꽂을 칩: " + ", ".join(current.ics)
    if current.continues:
        # 이어 붙이는 회로가 선언한 칩은 **전부** 새로 꽂는 것이다. 앞 회로를
        # 그대로 두므로 이름이 겹쳐도 그것은 재배선이 아니라 **두 번째 패키지**다
        # — 실험10 C1 의 `U4 = 741 OP amp` 와 C2 의 `U5 = 741 OP amp` 가 그렇다.
        # 741 한 패키지에 op-amp 는 하나뿐이고 결선도가 "비교기를 하나 더
        # 붙인다"라고 적는다. `not in previous.ics` 로 거르면 이 기능의 존재
        # 이유인 그 지시가 배너에서 사라진다.
        # `continues` 는 언제나 직전 회로다(validate 가 강제한다). 회로 번호는
        # 머리글과 길잡이 줄에 찍혀 있어 제목 전체를 되풀이하지 않는다.
        # 단, **같은 번호로 다시 적은 칩**(실험10 C3 의 `U2 = 74HC04`)은 바뀐 핀을
        # 적으려는 같은 패키지다 — 번호까지 같은 선언은 뺀다.
        added = []
        for ref, chip in current.ic_decls:
            if (ref, chip) not in previous.ic_decls and chip not in added:
                added.append(chip)
        tail = " · 더 꽂을 칩: " + ", ".join(added) if added else ""
        return (f"앞 회로({previous.id})를 그대로 두고 이어 붙여요. "
                f"점퍼선은 뽑지 않아요{tail}")
    remove = [c for c in previous.ics if c not in current.ics]
    add = [c for c in current.ics if c not in previous.ics]
    keep = [c for c in current.ics if c in previous.ics]
    if current.rebuild_all:
        # 기반까지 걷는 경계(2026-10-05, 실험05 C2). 앞 회로와 LED 방향이 반대라(Negative Logic
        # → 보통) 사슬을 남길 수 없고, 칩 자리가 겹쳐 전원선도 다시 꽂는다(netlist M16)
        parts = ["앞 회로의 선과 LED 사슬까지 전부 뽑아요. 레일 브리지만 그대로 둬요"
                 "(새 선·부품은 단계 그림을 따라 꽂아요)"]
    elif current.rebuild:
        # 앞 회로를 통째로 걷는 경계(2026-09-27, 실험04 C2). 단계 표가 있어도 `그대로 둔다`
        # 가 아니다. 기반(전원·브리지·LED 사슬)은 남긴다 — 다음 회로 1단계의 기반과 같은
        # 자리라 뽑으면 다시 꽂게 된다.
        parts = ["앞 회로의 신호선을 전부 뽑아요. 전원선·레일 브리지·LED 사슬은 그대로 "
                 "둬요(새 선은 단계 그림을 따라 꽂아요)"]
    elif current.stages:
        if _has_entry_walk(current):
            parts = ["앞 회로 배선은 그대로 둬요. 걷을 선은 걷기 그림(빨간 점선), "
                     "새 선은 단계 그림(회색·번호)을 따라가요"]
        else:
            parts = ["앞 회로 배선은 그대로 둬요. 걷을 선·새 선은 단계 그림"
                     "(회색·번호·'걷는다' 표)을 따라가요"]
    else:
        parts = ["앞 회로의 점퍼선을 모두 뽑아요"]
    if remove:
        parts.append("뺄 칩: " + ", ".join(remove))
    if add:
        parts.append("꽂을 칩: " + ", ".join(add))
    if keep:
        parts.append("칩은 그대로 두고 선만 다시 꽂을 칩: " + ", ".join(keep))
    return " · ".join(parts)


def _schematic_html(item, spec_dir) -> str:
    """강의노트 게이트 회로도 — 항목의 첫 회로 페이지, 칩 교체 배너 바로 뒤.

    결선도를 보다가 "원래 회로가 뭐였지" 를 교안을 따로 열지 않고 확인하게 한다.
    `src` 는 명세 기준 상대경로 그대로다 — 인쇄본 HTML 이 명세와 같은 `체크리스트/`
    에 놓인다(`_capture_html` 의 `figure` 와 같은 논리). 파일이 없으면 `<img>` 를
    내지 않는다 — 깨진 그림이 PDF 로 굳는다. 필드가 없으면 빈 문자열이다.

    파일명·출처 캡션은 생략한다. 그림이 없으면 안내 한 줄을 낸다.
    """
    if item is None or not item.schematic:
        return ""
    out = []
    for rel in item.schematic:
        if (Path(spec_dir) / rel).exists():
            out.append(f'<img class="schematic" src="{_esc(rel)}">')
        else:
            out.append(f"<p class='src'>회로도가 아직 없어요: {_esc(rel)}</p>")
    return "".join(out)


# 결선도 PNG 옆 JSON 의 스키마. 렌더러(`render_breadboard.SIDECAR_SCHEMA`)와 같은 문자열 —
# 인쇄가 PIL 에 묶이지 않게 import 하지 않고 따로 든다
SIDECAR_SCHEMA = "breadboard-sidecar/v1"


def _sidecar(png: Path, board: str = "v1") -> dict:
    """PNG 옆 사이드카. PNG 만 있고 이것이 없으면 옛 렌더러 산출물이다 — 결선 순서가
    조용히 빠진 채 인쇄되지 않게 멈춘다.

    `board` 는 그 주차 `배치.py` 의 판형이다. 사이드카의 `board`(없으면 v1)와 다르면 멈춘다 —
    빌더가 `board=BOARD` 를 빠뜨리면 `build_all` 이 멈추기 전에 v1 그림을 이미 써 두므로,
    v2 주차 체크리스트에 v1 판형 그림이 조용히 실리지 않게 여기서 막는다."""
    side = png.with_suffix(".json")
    if not side.exists():
        raise FileNotFoundError(
            f"{side.name} 가 없다 — 결선도를 다시 뽑는다: python3 "
            ".claude/skills/breadboard-diagram/scripts/render_breadboard.py --experiment <N>")
    data = json.loads(side.read_text(encoding="utf-8"))
    if data.get("schema") != SIDECAR_SCHEMA:
        raise ValueError(f"{side.name} 의 schema 가 {data.get('schema')!r} 다 — "
                         f"{SIDECAR_SCHEMA} 로 다시 뽑는다")
    got = data.get("board", "v1")
    if got != board:
        raise ValueError(f"{side.name} 는 {got} 판형 그림인데 주차 배치.py 의 BOARD 는 {board} 다 — "
                         "빌더가 BreadboardRenderer(..., board=BOARD) 로 넘기는지 보고 다시 뽑는다")
    return data


def _step_n(s) -> str:
    """결선 순서 번호 원 — 단계 그림 팔레트 색(`color`)이 있으면 바탕을 그 색으로(그림 위 번호 원과 같게)."""
    style = f' style="background:{_esc(s["color"])}"' if s.get("color") else ""
    return f'<span class="n"{style}>{s["n"]}</span>'


def _board_text_html(data) -> str:
    """그림 옆 글자 — 걷기 · 결선 순서 · 계측 · 회색 개수. 순서가 곧 실험실 순서다:
    먼저 뽑고, 새로 꽂고, 문다. 클래스 이름은 디자인 템플릿과의 계약이다."""
    out = []
    if data["removals"]:
        items = "".join(
            '<li class="removal"><span class="box"></span>'
            + (f'<span class="n">{r["n"]}</span>' if r["n"] is not None else "")
            + f'<span class="text">{_esc(r["text"])}</span></li>'
            for r in data["removals"])
        out.append(f'<p class="list-head">먼저 뽑아요</p><ul class="removals">{items}</ul>')
    if data["steps"]:
        items = "".join(
            f'<li class="step" data-kind="{_esc(s["kind"])}"><span class="box"></span>'
            + _step_n(s)
            + f'<span class="route">{_esc(s["from"])} → {_esc(s["to"])}'
            + (f' ×{s["count"]}' if s["count"] > 1 else "")
            + f'</span><span class="desc">{_esc(s["desc"])}</span></li>'
            for s in data["steps"])
        out.append(f'<ol class="steps">{items}</ol>')
    if data["probes"]:
        items = "".join(
            f'<li class="probe"><span class="box"></span><span class="n">{p["n"]}</span>'
            f'<span class="route">{_esc(p["label"])} → {_esc(p["at"])}</span>'
            f'<span class="desc">{_esc(p["desc"])}</span></li>'
            for p in data["probes"])
        out.append(f'<p class="list-head">계측 — 꽂지 않고 물어요</p><ol class="probes">{items}</ol>')
    return "".join(out)


def _task_note(todo, data) -> str:
    """목록의 연결 설명과 정확히 겹치는 절만 덜고 나머지 조작은 보존한다."""
    def normalise(text):
        return re.sub(r'\s+', '', _plain(text).replace('->', '→')).rstrip('.。')

    descriptions = [normalise(row['desc']) for row in data.get('steps', [])]
    kept = []
    for part in re.split(r';\s*|(?<=[요다])\.\s*', _plain(todo)):
        part = part.strip()
        if not part:
            continue
        route = normalise(part).removeprefix('신호선:').removesuffix('급전')
        duplicate = '→' in route and any(
            route == desc or desc.endswith('=' + route) for desc in descriptions)
        if not duplicate:
            kept.append(part)
    return f'<p class="operation">{_esc(" · ".join(kept))}</p>' if kept else ''


def _diagram_html(section, netlist) -> str:
    """결선도가 있으면 싣고, 없으면 그 자리에 빈 브레드보드를 넣는다.

    **렌더러를 호출하지 않는다.** 인쇄가 PIL·시스템 폰트·미추적 스크립트에
    묶이면 안 된다. 부재는 `validate.check_netlist_circuits` 가 warn 으로 알린다.

    그림은 전체 폭을 요구한다 — 998px 를 절반(95mm)으로 줄이면 12px 핀 라벨이
    약 3.2pt 가 되어 읽을 수 없다.
    """
    if section.diagram:
        png = netlist.path.parent / section.diagram
        if png.exists():
            src = f"../{netlist.path.parent.name}/{section.diagram}"
            data = _sidecar(png, board_version_of(netlist.path.parent / "배치.py", netlist.experiment))
            return (f'<figure class="board"><img src="{_esc(src)}" style="width:100%"></figure>'
                    + ("" if getattr(section, "stages", ()) else _board_text_html(data)))
    rows = crop_rows(section.body)
    # 빈 판형은 그 주차 판형이다 — v2 주차에 v1 격자를 깔면 열이 둘 더 있는 판에 그리게 된다
    asset, header_mm = BLANK_BOARDS[board_version_of(netlist.path.parent / "배치.py", netlist.experiment)]
    visible_mm = header_mm + rows * 6
    return (f"<h3>브레드보드 작도 ({rows}행)</h3>"
            "<p class='src'>이 회로의 결선도가 아직 없어요 — 격자에 직접 그려요</p>"
            f'<img src="{config.root_relative_prefix()}{asset}" '
            f'style="width:100%;max-height:{visible_mm:.1f}mm;object-fit:cover;'
            'object-position:top">')


def _assembly_html(step, netlist) -> str:
    """A power-off assembly page, without an observation or measurement table."""
    png = netlist.path.parent / step.diagram
    data = _sidecar(png, board_version_of(netlist.path.parent / "배치.py", netlist.experiment))
    src = f"../{netlist.path.parent.name}/{step.diagram}"
    return (f'<div class="stage"><h3>단계 {step.stage_no} 준비 {circled(step.order)} · {_esc(step.title)}</h3>'
            '<p class="banner">전원·신호발생기 OFF</p>'
            f'<figure class="board"><img src="{_esc(src)}" style="width:100%"></figure>'
            + _task_note(step.todo, data)
            + _board_text_html(data)
            + f'<p><span class="box"></span><b>완료 확인:</b> {_esc(_plain(step.check))}</p></div>')


def _stage_html(stage, netlist, section, spec=None, last=False, leds=(), feed=None) -> str:
    """단계 블록 하나 — 그림, 이 단계에서 할 것, 확인 노드, 확인 칸, 단계 진리표.

    그림이 없으면 빈 브레드보드를 넣지 않는다 — 단계 그림은 회색 기준선이 요점이라
    격자로 대신할 수 없다. 부재는 validate 가 warn 으로 알렸다.

    `확인 노드` 줄은 그 단계에서 볼 노드의 이름과 **핀**이다. 핀은 `## 노드` 표에서
    조회한다 — 단계 표에 핀을 적게 하면 두 자리가 표류한다.

    단계 진리표는 그 노드의 기대값을 **이 블록 안에** 싣는다 — 2026-09-28 전에는 회로 끝의
    중간 노드 표에만 있어 학생이 단계마다 뒤로 넘겨 보고 돌아와야 했다. `spec` 이 없으면
    (단위 테스트의 세 인자 호출) 싣지 않는다. `last` 인 단계는 싣지 않는다 — 바로 뒤에
    기록표가 오고 그것이 그 단계의 표다.

    걷기 행(`<k>걷기`)에는 `확인 노드` 줄도 단계 진리표도 없다 — 걷기만 하는 장이라 관측할
    출력이 없고, 파서가 `node` 를 `None` 으로 낸다.

    `leds`(보드 LED, v2 사이드카)와 `feed`(이 단계 뒤 누적 급전 지도)에서 이 단계 관측 노드를 보는
    LED 가 있으면 노드 열 대신 LED 점등 표를 싣는다 — `last` 여도 싣는다(2026-10-11 사용자). 앞
    단계 LED 만 있고 관측 노드는 프로브로 보는 단계는 옛 표다 — LED 표에 그 노드가 없다.
    """
    png = netlist.path.parent / stage["diagram"] if stage["diagram"] else None
    data = {}
    if png is not None and png.exists():
        src = f"../{netlist.path.parent.name}/{stage['diagram']}"
        img = f'<figure class="board"><img src="{_esc(src)}" style="width:100%"></figure>'
        data = _sidecar(png, board_version_of(netlist.path.parent / "배치.py", netlist.experiment))
        text = _board_text_html(data)
    else:
        img = f"<p class='src'>단계 그림이 아직 없어요: {_esc(stage['diagram'] or '(없음)')}</p>"
        text = ""
    try:
        procedure = observations.procedure_for_stage(section, stage) if stage.get("procedure") else None
    except ValueError:
        procedure = None  # 아래의 기존 오류 표시 경로에서 처리한다.
    diagnostic = bool(stage.get("diagnostic")) or (procedure is not None and procedure.checklist == "diagnostic")
    if diagnostic and data.get("probes"):
        data = {**data, "probes": []}
        text = _board_text_html(data)
    node = ""
    if stage.get("node") and not diagnostic:
        pin = next((n["pin"] for n in section.nodes if n["name"] == stage["node"]), "")
        tail = f" <small>({_esc(pin)})</small>" if pin else ""
        node = f"<p><b>확인 노드:</b> {_esc(_plain(stage['node']))}{tail}</p>"
    table = ""
    seen_nodes = {feed[led.tag] for led in watched(leds, feed or {}, section)}
    if stage.get("procedure") and not diagnostic:
        try:
            procedure = observations.procedure_for_stage(section, stage)
            names = list(dict.fromkeys([*procedure.observe, *[feed[led.tag] for led in leds
                                                            if led.tag in (feed or {})
                                                            and feed[led.tag] in {n['name'] for n in section.nodes}]]))
            authored = observations.stage_observations(section, spec, stage, names)
            table = (f'<h4>{_esc(procedure.id)} · {_esc(procedure.title)}</h4>'
                     + _observation_procedure_html(authored, leds, feed, png=png))
        except ValueError as exc:
            table = f"<p class='src'>확인 절차를 인쇄할 수 없어요: {_esc(exc)}</p>"
    elif not diagnostic and spec is not None and stage.get("node") and stage["node"] in seen_nodes:
        table = _led_table_html(spec, section, leds, feed, png=png)
    elif not diagnostic and spec is not None and stage.get("node") and not last:
        table = _stage_table_html(spec, section, stage["node"], _stage_led(stage["todo"]), png=png)
    # 걷기 행은 `단계 2걷기` 가 아니라 `2단계 전 · 걷기` 로 찍는다 — 인쇄본에서
    # "2단계 앞에 하는 정리" 로 읽혀야 한다. `단계 2 · 걷기` 는 바로 뒤 `단계 2`
    # 와 번호가 겹쳐 같은 단계를 두 번 하는 것처럼 보였다(2026-09-29 실험04).
    # 판정은 파서의 `walk` 키다.
    head = (f"{_esc(str(stage['walk_of']))}단계 전 · 걷기" if stage.get("walk")
            else f"단계 {_esc(stage['n'])}")
    # 블록 하나가 PDF 한 쪽이다 — 쪽 높이는 `fit_pages` 가 블록 실측값으로 준다.
    operation = ('<p class="operation"><b>전원 OFF</b></p>' if stage.get('walk')
                 else _task_note(stage['todo'], data))
    # 명시 관측표와 걷기 목록이 확인 대상·핀·결과를 이미 담는다.
    check = ('' if diagnostic or stage.get('procedure') or stage.get('walk') else
             f'<p><span class="box"></span><b>확인:</b> {_esc(_plain(stage["check"]))}</p>')
    if table:
        node = ''
    return (f'<div class="stage"><h3>{head}</h3>{operation}{img}{text}{node}'
            f'{check}'
            f"{table}</div>")


# 단계의 관측 LED — `이 단계에서` 칸의 `…→LED<n> 급전` 표기. 실험03·04 결선도가 관측
# 단계마다 정확히 하나씩 쓴다(2026-09-28 실측). 표기가 없거나 둘 이상이면 짐작하지 않는다.
_STAGE_LED = re.compile(r"→\s*LED\s*(\d+)\s*급전")


def _stage_led(todo) -> str:
    """`LED<n>` 또는 빈 문자열."""
    found = _STAGE_LED.findall(_plain(todo or ""))
    return f"LED{found[0]}" if len(found) == 1 else ""


_JUMPER = {"H/L": "H=+5V · L=GND"}


def _inline_observation_html(table, leds, feed, png=None):
    # 받는 신호를 아는 LED가 하나도 없으면 LED로 판독할 근거가 없다 — 프로브 표로 그린다
    lamps = [l for l in leds if l.tag in feed]
    if not any(feed[l.tag] is not None for l in lamps):
        lamps = []
    rows = []

    def all_unknown(r):
        # 전원 직후처럼 모든 LED가 미정인 행은 켜짐·꺼짐 칸에 `미정`을 적는다 — 별도 열을 만들지 않는다
        v = dict(zip((n for n,_ in table.points), r.expected))
        return bool(lamps) and all(v.get(feed[l.tag]) == '미정' for l in lamps)
    has_other = any(dict(zip((n for n,_ in table.points), r.expected)).get(feed[l.tag], '관측 안 함')
                    not in ('0','1','H','L') for r in table.rows if not all_unknown(r) for l in lamps)
    probe_points = [(n,p) for n,p in table.points if n not in {feed[l.tag] for l in lamps}]
    for row in table.rows:
        values = dict(zip((n for n, _ in table.points), row.expected))
        inputs = '; '.join(f'{n} = {c}' for n, c in zip(table.inputs, row.inputs))
        if lamps and all_unknown(row):
            rows.append([f'S{row.order}', row.action, inputs, '미정', '미정',
                         *(['없음'] if has_other else []),
                         *(['; '.join(f'{n} ({p}): {values[n]}' for n,p in probe_points)] if probe_points else []), ''])
        elif lamps:
            on, off, other = [], [], []
            for led in lamps:
                token = values.get(feed[led.tag], '관측 안 함')
                label = f'{circled(led.index)}{led.tag}'
                bit = bit_of(token, table.encoding) if token in ('0', '1', 'H', 'L') else None
                if bit is None:
                    other.append(label + ': ' + {'유지':'직전 그대로', '반전':'직전과 반대',
                        '미정':'미정', '관측 안 함':'이번 절차 관측 안 함'}[token])
                else:
                    (on if lit(bit, led.active_low) else off).append(label)
            rows.append([f'S{row.order}', row.action, inputs, ' · '.join(on) or '없음',
                         ' · '.join(off) or '없음', *(['; '.join(other) or '없음'] if has_other else []),
                         *(['; '.join(f'{n} ({p}): {values[n]}' for n,p in probe_points)] if probe_points else []), ''])
        else:
            expected = '; '.join(f'{n} ({pin}): {v}' for (n,pin),v in zip(table.points,row.expected))
            rows.append([str(row.order), row.action, inputs, expected, ''])
    if lamps:
        # LED 판독 표는 기록표(T1 등)와 같은 서식 — `스텝`·`S<n>`·`CLK=값`
        header = ['스텝','조작','입력 설정','예상 켜지는 LED','예상 꺼지는 LED']
        if has_other:
            header.append('유지·반전·미정')
        if probe_points:
            header.append('측정 핀·예상값')
        header.append('실제 결과')
        pins = ' · '.join(f'{circled(l.index)}{l.tag} = {feed[l.tag]}'
                          for l in lamps if l.tag != feed[l.tag])
        detail = '<p>보는 LED: ' + _esc(pins) + '</p>' if pins else ''
    else:
        header = ['순서','조작','입력 설정','측정 핀·예상 논리값','실제 결과']
        detail = ''
    columns, head = _mirror(png, table.inputs)
    settings = _input_settings_html(table.inputs, [row.inputs for row in table.rows], columns=columns,
                                    spaced=not lamps)
    h = _comparison_table_html(header, rows, input_settings=settings, input_column=2, input_head=head)
    # One timeline, one stable authored order per row.
    for row in table.rows:
        label = f'S{row.order}' if lamps else str(row.order)
        h = h.replace('<tr><td>' + label + '</td>',
                      f'<tr data-observation-order="{row.order}"><td>{label}</td>', 1)
    return detail + h


def _observation_procedure_html(table, leds=(), feed=None, png=None) -> str:
    """Two matched timelines, with per-LED status. Never writes measured cells."""
    feed = feed or {}
    if not any(feed.get(l.tag) is not None for l in leds):
        feed = {}
    out = ['<section class="observation-procedure">']
    if getattr(table, 'purpose', ''):
        out.append(f'<p class="observation-purpose">{_esc(table.purpose)}</p>')
    out.append(f'<p><b>준비·초기화:</b> {_esc(table.setup)}</p>')
    if png is not None:
        out.append(locations_html(png, table.inputs,
                                  feed={tag: name for tag, name in feed.items() if name is not None}))
    if table.layout == 'inline':
        return '\n'.join(out) + _inline_observation_html(table, leds, feed, png) + '</section>'
    columns, head = _mirror(png, table.inputs)
    out.append('<p><b>조작·입력</b></p>')
    out.append(f'<table><thead><tr><th>순서</th><th>조작</th><th>입력 설정{head}</th></tr></thead><tbody>')
    settings = _input_settings_html(table.inputs, [row.inputs for row in table.rows], columns=columns)
    for row, inputs in zip(table.rows, settings):
        out.append(f'<tr data-observation-order="{row.order}"><td>{row.order}</td>'
                   f'<td>{_esc(row.action)}</td><td>{inputs}</td></tr>')
    out.append('</tbody></table>')
    out.append('<p><b>관측 예상</b></p>')
    out.append('<table><thead><tr><th>순서</th><th>관측점 · 핀 · 예상</th><th>LED 상태</th><th>확인</th></tr></thead><tbody>')
    for row in table.rows:
        by_name = {n: token for (n, _), token in zip(table.points, row.expected)}
        expected = '<br>'.join(f'{_esc(n)} ({_esc(pin)}): {_esc(token)}'
                              for (n, pin), token in zip(table.points, row.expected))
        statuses = []
        for led in leds:
            if led.tag not in feed:
                continue
            token = by_name.get(feed[led.tag], '관측 안 함')
            bit = bit_of(token, table.encoding) if token in ('0','1','H','L') else None
            if bit is not None:
                status = '켜짐' if lit(bit, led.active_low) else '소등'
            else:
                status = {'유지':'직전 그대로', '반전':'직전과 반대',
                          '미정':'미정', '관측 안 함':'이번 절차 관측 안 함'}[token]
            polarity = '0이면 켜짐' if led.active_low else '1이면 켜짐'
            statuses.append(f'{circled(led.index)}{_esc(led.tag)}: {status} <small>({polarity})</small>')
        out.append(f'<tr data-observation-order="{row.order}"><td>{row.order}</td><td>{expected}</td>'
                   f'<td>{"<br>".join(statuses) if statuses else "프로브 관측"}</td><td class="box"></td></tr>')
    out.append('</tbody></table></section>')
    return '\n'.join(out)


def _reorder_inputs(table, png):
    """계산된 표(단계·LED·노드 표)의 입력 열을 위치도 순서로 — 행 순서는 기록표 그대로다."""
    order = location_order(png, table.inputs)
    if order == list(range(len(table.inputs))):
        return table
    return replace(table, inputs=[table.inputs[k] for k in order],
                   rows=[([cells[k] for k in order], rest) for cells, rest in table.rows])


def _stage_table_html(spec, section, node_name, led="", png=None) -> str:
    """단계 진리표 — 입력은 그 노드 식에 나오는 것만, 열 머리 둘째 줄은 노드 핀.

    머리는 두 줄이다. 입력 열 위에 `입력 — 점퍼 1=+5V · 0=GND` 묶음 머리를 단다 — 입력
    열을 LED 로 읽는 학생이 있었다(2026-09-28 사용자 질문). 노드 열은 `led` 가 있으면
    `LED4 = E'` 처럼 볼 LED 를 먼저 쓴다 — 표만 보고 어느 불을 볼지 알아야 한다.

    확인 칸은 `td.box` 다 — `.check` 개수는 명세 기록표 행 수와 대조되는 불변식이다
    (`test_check_cells_exist_for_every_truth_table_row`). 표를 div 로 감싸지 않는다 —
    단계 블록의 `</div>` 가 블록 끝이어야 테스트와 인쇄 묶음(`break-inside`)이 맞는다.

    계산 실패는 validate 가 먼저 error 로 막지만, 렌더는 죽지 않고 안내 한 줄을 낸다.
    """
    try:
        st = node_calc.stage_table(section, spec, node_name)
    except ValueError as exc:
        return f"<p class='src'>단계 진리표를 계산할 수 없어요: {_esc(exc)}</p>"
    st = _reorder_inputs(st, png)
    name, pin = st.node
    label = (f"{_esc(led)} = {_esc(_plain(name))}<br><small>예상 · {_esc(pin)}</small>" if led
             else f"{_esc(_plain(name))}예상<br><small>{_esc(pin)}</small>")
    jumper = _JUMPER.get(st.encoding, "1=+5V · 0=GND")
    inputs = "".join(f"<th>{_esc(n)}</th>" for n in st.inputs)
    if st.inputs:
        head = (f'<tr><th colspan="{len(st.inputs)}">입력 — 점퍼 {_esc(jumper)}</th>'
                f'<th rowspan="2">{label}</th><th rowspan="2">확인</th></tr>'
                f"<tr>{inputs}</tr>")
    else:                         # 상수 노드 — 입력 열이 없다
        head = f"<tr><th>{label}</th><th>확인</th></tr>"
    body = ["<tr>" + "".join(f"<td>{_esc(c)}</td>" for c in cells)
            + f"<td>{_esc(node_calc.format_bit(bit, st.encoding))}</td>"
            + '<td class="box"></td></tr>'
            for cells, bit in st.rows]
    return "\n".join(([locations_html(png, st.inputs, feed={})] if png is not None else [])
                     + ['<table class="stage-table">', "<thead>", head, "</thead>",
                      "<tbody>", *body, "</tbody>", "</table>"])


def _led_table_html(spec, section, leds, feed, png=None) -> str:
    """단계 LED 점등 표 — 그 단계까지 급전된 보드 LED 를 행마다 `켜지는 LED`·`꺼지는 LED` 두 열에
    보드 순서(①②…)로 나눠 적는다.

    극성은 이미 적용했다 — Negative Logic LED(실험05 C1)는 출력 0 에서 켜져 논리값만 보면
    헷갈렸다. 열마다 LED 하나를 두면 LED 열 개(실험05 C1)에서 쪽 폭을 넘어 두 열로 접었다
    (2026-10-11 사용자). 표 위 `보는 LED:` 줄이 번호·급전 핀·극성을 한 번 알린다 — 임시 급전은
    `②A2 = D0'` 처럼 노드를 밝힌다. 값이 안 정해지는 LED 는 꺼지는 칸에 보드 순서대로 `①P 미정` 으로 적는다.
    확인 칸은 옛 단계 표처럼 `td.box` 다(`.check` 불변식).
    """
    shown = watched(leds, feed, section)
    try:
        st = node_calc.stage_nodes_table(section, spec, [feed[led.tag] for led in shown])
    except ValueError as exc:
        return f"<p class='src'>단계 진리표를 계산할 수 없어요: {_esc(exc)}</p>"
    st = _reorder_inputs(st, png)
    names = {led.tag: f"{circled(led.index)}{_esc(led.tag)}" for led in shown}
    seen = []
    for led, (node, pin) in zip(shown, st.nodes):
        name = names[led.tag] + (f" = {_esc(_plain(node))}" if node != led.tag else "")
        seen.append(f"{name}({_esc(pin)})")
    polarity = {led.active_low for led in shown}
    if len(polarity) == 1:
        tail = " — 모두 0이면 켜짐" if polarity.pop() else " — 모두 1이면 켜짐"
    else:                         # 섞이면 LED 마다 적는다
        seen = [f"{s} {'0' if led.active_low else '1'}이면 켜짐" for s, led in zip(seen, shown)]
        tail = ""
    legend = f'<p class="led-legend"><b>보는 LED:</b> {" ".join(seen)}{tail}</p>'
    jumper = _JUMPER.get(st.encoding, "1=+5V · 0=GND")
    if st.inputs:
        head = (f'<tr><th colspan="{len(st.inputs)}">입력 — 점퍼 {_esc(jumper)}</th>'
                '<th rowspan="2">켜지는 LED</th><th rowspan="2">꺼지는 LED</th>'
                '<th rowspan="2">확인</th></tr><tr>'
                + "".join(f"<th>{_esc(n)}</th>" for n in st.inputs) + "</tr>")
    else:                         # 상수 노드뿐 — 입력 열이 없다
        head = "<tr><th>켜지는 LED</th><th>꺼지는 LED</th><th>확인</th></tr>"
    body = []
    for cells, bits in st.rows:
        on = [names[led.tag] for led, bit in zip(shown, bits)
              if bit is not None and lit(bit, led.active_low)]
        # 미정 LED 도 꺼지는 칸에 보드 순서 그대로 끼운다 — 칸 안 순서가 `보는 LED:` 줄과 같아야 한다
        off = [names[led.tag] + (" 미정" if bit is None else "") for led, bit in zip(shown, bits)
               if bit is None or not lit(bit, led.active_low)]
        off_text = " ".join(off) or "없음"
        body.append("<tr>" + "".join(f"<td>{_esc(c)}</td>" for c in cells)
                    + f'<td class="led on">{" ".join(on) or "없음"}</td>'
                    + f'<td class="led off">{off_text}</td><td class="box"></td></tr>')
    return "\n".join(([locations_html(png, st.inputs,
                                     feed={tag: name for tag, name in feed.items() if name is not None})] if png is not None else [])
                     + [legend, '<table class="stage-table led-table">', "<thead>", head, "</thead>",
                      "<tbody>", *body, "</tbody>", "</table>"])


_INSTRUMENT = "계측기 설정 — 모드·레인지·단위: ________________________________"


def _record_outputs(spec, section) -> set:
    """기록표 출력 열 이름. 기록표가 없거나 입력 열이 어긋나면(validate 가 막는다) 빈 집합."""
    try:
        table = node_calc.record_table(section, spec)
    except ValueError:
        return set()
    if table is None:
        return set()
    return {table.header[i] for i in split_indices(table)[1]}


def _unstaged_nodes_html(spec, section, png=None) -> str:
    """단계에서 안 본 노드 — 어느 단계도 가리키지 않는 노드의 핀과 기대값. 기록표 뒤에 온다.

    2026-09-28 최종 리뷰: 옛 중간 노드 표를 통째로 없애면 한 단계 안에서 함께 세운 노드
    (실험04 C2 `S0'`·`S1'`)와 단계 없는 회로의 노드가 인쇄본에서 사라진다. 단계 진리표와
    겹치는 열은 찍지 않는다 — N1(겹치는 표 제거)의 취지는 그대로다. 읽는 표라 `.check` 가 없다.
    """
    staged = {s["node"] for s in section.stages if s.get("node")}
    expressions = [n for n in section.nodes if observations.point_kind(n) == "expression"]
    keep = [k for k, n in enumerate(expressions) if n["name"] not in staged]
    if not keep:
        return ""
    try:
        nt = node_calc.compute(section, spec)
    except ValueError as exc:
        return f"<p class='src'>노드 표를 계산할 수 없어요: {_esc(exc)}</p>"
    nt = _reorder_inputs(nt, png)
    out = ['<div class="tblock nodes">',
           "<h3>단계에서 안 본 노드 — 프로브로 찍을 핀</h3>",
           locations_html(png, nt.inputs, feed={}) if png is not None else "",
           "<table>", "<thead>", "<tr>"]
    out += [f"<th>{_esc(name)}</th>" for name in nt.inputs]
    out += [f"<th>{_esc(_plain(nt.nodes[k][0]))}<br><small>{_esc(nt.nodes[k][1])}</small></th>"
            for k in keep]
    out += ["</tr>", "</thead>", "<tbody>"]
    for cells, bits in nt.rows:
        vals = ([node_calc.format_bit(bits[k], nt.encoding) for k in keep] if bits is not None
                else ["—"] * len(keep))
        out.append("<tr>" + "".join(f"<td>{_esc(c)}</td>" for c in cells)
                   + "".join(f"<td>{_esc(v)}</td>" for v in vals) + "</tr>")
    out += ["</tbody>", "</table>", "</div>"]
    return "\n".join(out)


def _circuit_tables(spec, section, badges=None, leds=(), netlist=None) -> str:
    out = []
    circuit_item = next((i for i in spec.items if i.id == section.item), None)
    for table_id in section.tables:
        table = spec.table(table_id)
        if table is None or table.role == "reference":
            continue
        # 토큰은 표를 가진 항목에서 딴다 — `contact_sheet` 는 기록.md 의 항목
        # 헤딩으로 사진을 묶는다. 소유 항목이 없으면 회로의 `item` 으로 물러선다.
        item = next((i for i in spec.items if table_id in i.tables), circuit_item)
        token = item_token(item.title) if item else None
        out.append('<div class="tblock">')
        out.append(f"<h3>{_esc(table.id)} · {_esc(table.title)}</h3>")
        if getattr(table, "purpose", None):
            out.append(f'<p class="table-purpose">{_esc(table.purpose)}</p>')
        # `_plain` 을 씌운다 — 옛 `_tables()` 는 안 씌웠다. 지금 어느 명세의
        # `source` 에도 마크다운이 없지만, 들어오는 순간 백틱이 인쇄본에 찍히고
        # 그것을 잡는 검사는 본문만 본다.
        if table.kind == "capture":
            out.append(_capture_html(table, spec.path.parent))
        elif table.kind == "stepped":
            if getattr(table, 'comparison', None):
                if netlist is not None and section.diagram:
                    out.append(locations_html(netlist.path.parent / section.diagram,
                               [location_name(n) for n in table.header
                                if n not in [*(table.outputs or []), '스텝', '조작']]))
            png = (netlist.path.parent / section.diagram
                   if netlist is not None and section.diagram and getattr(table, 'comparison', None) else None)
            out.append(_stepped_html(table, wide=netlist is not None and netlist.schema == "lab-netlist/v3",
                                     leds=leds, png=png))
            if not getattr(table, 'comparison', None):
                out.append(f"<p class='readout'>{_esc(_INSTRUMENT)}</p>")
        else:
            png = None            # 위 스텝표 갈래의 png 가 다음 표로 새지 않게
            if netlist is not None:
                png = netlist.path.parent / section.diagram if section.diagram else None
                inputs = [_plain(table.header[i]) for i in split_indices(table)[0]]
                out.append(locations_html(png, inputs))
            out.append(_truth_table_html(table, token, badges, section.order, leds, png=png))
        out.append("</div>")
    for table_id in section.refs:
        table = spec.table(table_id)
        if table is None:
            continue                  # validate 가 error 로 잡는다
        out.append('<div class="tblock">')
        out.append(f"<h3>{_esc(table.id)} · {_esc(table.title)} — 참조</h3>")
        # 기록 칸·미니표·사진 지시를 붙이지 않는다. 교안·데이터시트에서 옮긴
        # 이론표라 실험실에서 채우는 물건이 아니다 — 옆 표(실험02 T7)가 대조할
        # 기준값일 뿐이다.
        out.append(_md_table_html(table))
        out.append("</div>")
    return "\n".join(out)


def _unused_html(chips) -> str:
    """할 일이 있는 미사용 핀 지시만 칩별로 한 번 표시한다."""
    out = []
    for chip in chips:
        instructions = [re.sub(r'\s*·\s*공통 운영(?:,\s*M\d+)?', '', u)
                        for u in chip["unused"] if not re.search(r"(?:[:：]|핀)\s*없음", u)]
        if instructions:
            out.append(f'<div class="chipunused"><b>{_esc(chip["head"])}</b><ul>')
            out.extend(f'<li><span class="box"></span>{_esc(u)}</li>' for u in instructions)
            out.append('</ul></div>')
    return '<div class="unused"><b>미사용 핀</b>' + ''.join(out) + '</div>' if out else ''


def _item_label(item) -> str:
    """`실험 3) BCD 카운터` → `실험 3`. 번호가 없는 제목은 항목 ID 로 대신한다."""
    token = item_token(item.title)
    return f"실험 {token}" if token else item.id


def _circuit_trail(spec, netlist, current) -> str:
    """실험별 회로 길잡이 줄. 회로를 통틀어 `회로 2/5` 로 세면 실험이 다섯으로 읽힌다."""
    groups = {}
    for section in netlist.circuits:
        groups.setdefault(section.item, []).append(section)
    parts = []
    for item_id, sections in groups.items():
        item = next((i for i in spec.items if i.id == item_id), None)
        ids = ' › '.join(f'<b>{_esc(s.id)}</b>' if s is current else _esc(s.id)
                         for s in sections)
        parts.append(f'{_esc(_item_label(item))}: {ids}' if item is not None else ids)
    return '<div class="trail">' + ' <span class="sep">|</span> '.join(parts) + '</div>'


def _circuit_heading(section, item, first: bool) -> str:
    """긴 실험 제목은 그 실험의 첫 회로에만 적고, 뒤 회로는 실험 번호로 줄인다."""
    title = _plain(section.title)
    if item is not None and not first:
        title = title.replace(item.title, _item_label(item), 1)
    return title


def circuit_pages(spec, netlist) -> str:
    """작업 그림·조작표·기록표. 원본의 저작 설명과 중복 핀 배선표는 싣지 않는다."""
    out, previous = [], None
    feed_after = {}
    shown = set()
    v3_feeds = feeds_by_circuit(netlist) if netlist.schema == "lab-netlist/v3" else None
    for section in netlist.circuits:
        nodes, prose_before, prose_after = _circuit_body(section)
        chips = _chip_boxes(nodes)
        item = next((i for i in spec.items if i.id == section.item), None)
        first = item is not None and item.id not in shown
        header = _circuit_trail(spec, netlist, section)
        header += (f'<h2>{_esc(_circuit_heading(section, item, first))}'
                   f' · 기록: {_esc(", ".join(section.tables))}</h2>')
        header += f'<div class="banner">{_esc(_chip_swap(previous, section))}</div>'
        if first:
            shown.add(item.id)
            header += _schematic_html(item, spec.path.parent)
        out.append('<section class="circuit">')
        png = netlist.path.parent / section.diagram if section.diagram else None
        leds = board_leds(png) if png is not None and png.exists() else []
        observed = [s for s in section.stages if s.get("node")]
        last = observed[-1] if observed else None
        if last is not None and last["node"] not in _record_outputs(spec, section):
            last = None
        feeds = (v3_feeds[section.id] if v3_feeds is not None else
                 feeds_by_stage(section, start=feed_after if section.continues else None))
        stages = []
        for stage, feed in zip(section.stages, feeds):
            if not stage.get('walk'):
                from .assembly import steps_for_stage
                stages.extend(_assembly_html(step, netlist)
                              for step in steps_for_stage(section, stage.get('stage_no')))
            stages.append(_stage_html(stage, netlist, section, spec, last=stage is last,
                                      leds=leds, feed=feed))
        if stages:
            # 회로 개요와 실제 작업을 분리한다. 준비 1은 다음 쪽에서 시작한다.
            out.append(FIT_PLAIN + header + '</div>')
            out.extend(stages)
        feed_after = feeds[-1] if feeds else (feed_after if section.continues else {})
        out.append(FIT_PLAIN)
        if not stages:
            out.append(header)
            # 단계 없는 계측 회로의 유일한 장비 설정·저항망 표는 보존한다.
            if prose_before.strip():
                out.append(_blocks(prose_before))
        out.append('<div class="wirebox"><h3>완성본</h3>')
        out.append(_diagram_html(section, netlist))
        if not stages:
            for node in nodes:
                if node['type'] == 'prose':
                    out.append(_blocks(node['text']))
                elif png is None or not png.exists():
                    # 그림도 단계도 없는 회로에는 유일한 연결 정보를 남긴다.
                    out.append(f'<div class="chip"><h4>{_esc(node["head"])}</h4>')
                    out.extend(f'<p>{_esc(w)}</p>' for w in node['wires'])
                    out.extend(_md_table_html(p, lead_checkbox=True) if k == 'table' else _blocks(p)
                               for k, p in node['blocks'])
                    out.append('</div>')
        out.append('</div></div>')
        out.append(FIT_PLAIN)
        out.append(_unused_html(chips))
        if not stages and prose_after.strip():
            out.append(_blocks(prose_after))
        outputs = _record_outputs(spec, section)
        badges = {led.tag: f"LED{circled(led.index)}" for led in leds if led.tag in outputs}
        out.append(_circuit_tables(spec, section, badges, leds, netlist=netlist))
        out.append(_unstaged_nodes_html(spec, section, png=png))
        out.append('<div class="circuit-notes"><b>메모</b></div>')
        out.append('</div></section>')
        previous = section
    return _drop_issue_refs("\n".join(out))


CLOSING = ()


def closing_page() -> str:
    """반복 종료 안내는 현장판에서 제외한다."""
    return ""


def render_checklist(spec, netlist, template) -> str:
    """`netlist` 는 `netlist_parser.LabNetlist` 다 — 날 문자열이 아니다.

    회로 메타 없이는 인쇄본을 낼 수 없다. 옛 결선도를 "옛 방식으로 대충" 렌더하는
    관용을 두지 않는다 — 렌더러가 두 벌이 되고 어느 주차가 어느 레이아웃인지
    조용히 갈린다. 파서가 백필 방법을 담아 거절한다.
    """
    from .assembly import check_structure, check_assets
    errors = check_structure(netlist) + check_assets(netlist)
    if errors:
        raise ValueError("\n".join(str(f) for f in errors))
    title = config.document_title(spec.experiment, spec.title, "체크리스트")
    circuits = circuit_pages(spec, netlist)
    circuits = re.sub(r'<div class="(?:stage|fit)">',
                      lambda m: m[0] + f'<h1>{_esc(title)}</h1>' + common_page(spec, netlist),
                      circuits, count=1)
    if netlist.schema != "lab-netlist/v3":
        template = re.sub(r'<!-- OBSERVATION_STYLE_BEGIN -->.*?<!-- OBSERVATION_STYLE_END -->\n',
                          '', template, flags=re.S)
    return (template
            .replace("{{TITLE}}", _esc(title))
            .replace("{{COMMON}}", "")
            .replace("{{CIRCUITS}}", circuits)
            .replace("{{CLOSING}}", ""))
