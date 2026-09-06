"""kind 별 인쇄 레이아웃. 실험실 조건이 설계 제약이다.

확인 칸은 세로로 정렬되어야 한다 — 세로줄 하나로 관통해 "전항 일치"를 표기하는
방식이 태블릿 필기에서 가장 빠르기 때문이다. 칸과 숫자 사이에는 vision 전사가
체크와 숫자를 구분할 여백이 있어야 한다.

`role: reference` 표는 인쇄본에서 제외한다. 실험실에서 채우는 물건이 아니라
예비보고서 이론 절의 재료다.
"""

import html
import re
from dataclasses import replace

from . import md
from .netlist_parser import IC_DECL
from .notation import normalize_cell
from .spec_parser import split_columns
from . import config

MAX_BREADBOARD_ROWS = 30
# Breadboard.jpg(998×1345px) 상단에 아주대학교 로고 + 범례 원 3개가 있다.
# 인쇄 폭 190mm(prep-lab-checklist 의 @page 여백 기준: 210 - 10*2) 로 렌더링한
# 뒤 실측(픽셀 경계 대조 + 리뷰 재현)하면 실제 격자는 위에서 약 51.4mm
# 아래에서 시작한다. object-position: top 크롭이 이 띠를 예산에 안 넣으면,
# IC 가 적은 주차는 격자가 한 줄도 없이 로고만 인쇄된다 (B1).
_BREADBOARD_HEADER_MM = 51.4


def crop_rows(netlist_text: str) -> int:
    """netlist 가 실제로 쓰는 행 수. 브레드보드 템플릿을 여기에 맞춰 자른다.

    회로 본문을 넘긴다 — 결선도가 없는 회로의 fallback 격자 크기를 정한다.
    """
    ic_count = len(IC_DECL.findall(netlist_text))
    rows = max(6, ic_count * 8)
    return min(rows, MAX_BREADBOARD_ROWS)


_EMPHASIS = re.compile(r"\*{1,2}([^*]+)\*{1,2}")
_CODE = re.compile(r"`([^`]+)`")


def _esc(text) -> str:
    return html.escape(str(text), quote=False)


def _plain(text: str) -> str:
    """netlist 의 마크다운 표기를 벗긴다. 안 벗기면 인쇄본에 `**` 와 백틱이
    그대로 찍힌다.

    짝이 맞는 것을 먼저 벗기고, 남은 낱개 기호도 지운다 — 여러 줄에 걸친
    코드 스팬은 줄을 합친 뒤에도 짝이 안 맞을 수 있다. 이 도메인에서 `*` 와
    백틱은 내용이 아니라 항상 표기다.
    """
    text = _CODE.sub(r"\1", _EMPHASIS.sub(r"\1", text))
    return text.replace("`", "").replace("*", "")


def _truth_or_stepped_html(table) -> str:
    if table.kind == "truth-table":
        inputs, outputs = split_columns(table)
        at = {c: i for i, c in enumerate(table.header)}
        head = list(inputs) + [f"{c}예상" for c in outputs]
        body = [[normalize_cell(row[at[c]]) for c in inputs]
                + [normalize_cell(row[at[c]]) for c in outputs]
                for row in table.rows]
    else:
        head = list(table.header)
        body = [[normalize_cell(c) for c in row] for row in table.rows]

    # thead/tbody 로 나눈다 — 표가 쪽을 넘어가도 헤더가 따라가야 한다.
    # 헤더 없는 진리표 조각은 실험실에서 읽을 수 없다.
    out = ["<table>", "<thead>", "<tr>"]
    out += [f"<th>{_esc(h)}</th>" for h in head]
    out.append('<th>확인</th></tr>')
    out += ["</thead>", "<tbody>"]
    for row in body:
        out.append("<tr>" + "".join(f"<td>{_esc(c)}</td>" for c in row)
                   + '<td class="check"></td></tr>')
    out += ["</tbody>", "</table>"]
    return "\n".join(out)


def _capture_html(table) -> str:
    return (f"<p>예상: {_esc(table.expected or '')}</p>"
            '<div class="sketch"></div><p>캡션: ________________</p>')


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


LEGEND = ("확인 칸: ✓ 일치 / 값 = 불일치 시 실제로 관찰한 값 / 공란 = 미확인. "
          "표를 통째로 진행하지 않았으면 그 표 아래에 진행하지 않았음 이라고 적는다.")


def _flow_table(spec, netlist) -> str:
    """오늘의 흐름. 도착 직후 오늘 뭘 몇 개 하는지 한눈에 본다.

    쪽번호는 렌더 시점에 알 수 없다(Chrome 이 조판한다). 회로 번호로 대신한다 —
    회로마다 강제 개쪽이므로 회로 번호가 곧 순서다.
    """
    total = len(netlist.circuits)
    rows = ["<table class='flow'><thead><tr><th>순서</th><th>회로</th>"
            "<th>쓰는 IC</th><th>기록할 표</th></tr></thead><tbody>"]
    for n, circuit in enumerate(netlist.circuits, start=1):
        tables = ", ".join(
            f"{t} {spec.table(t).title}" if spec.table(t) else t
            for t in circuit.tables)
        rows.append(
            f"<tr><td>{n}/{total}</td><td>{_esc(_plain(circuit.title))}</td>"
            f"<td>{_esc(' · '.join(circuit.ics))}</td><td>{_esc(tables)}</td></tr>")
    rows.append("</tbody></table>")
    return "".join(rows)


def common_page(spec, netlist) -> str:
    """회로 페이지들 앞에 한 번만 오는 면.

    `kind` 가 목적지를 정한다 — `sources`(핀아웃 출처)는 여기 없다. 그것은
    ③ 예비보고서의 참고문헌 재료지 실험실에서 근거의 등급을 읽을 일은 없다.
    옛 렌더러는 그것을 배선 단계 7~11번으로 찍었다.
    """
    power = " · ".join(f"{k} = {v}" for k, v in spec.power.items())
    out = [f'<div class="power">전원: {_esc(power)} · '
           "미사용 입력핀은 전부 GND (플로팅 금지)</div>",
           f'<p class="legend">{_esc(LEGEND)}</p>',
           "<h2>오늘의 흐름</h2>", _flow_table(spec, netlist)]

    for section in netlist.of_kind("common"):
        out.append(f"<h2>{_esc(_plain(section.title))}</h2>")
        out.append(_blocks(section.body))

    for section in netlist.of_kind("lookup"):
        # `_blocks` 가 본문의 표를 제자리에 싣는다 — 여기서 또 렌더하면 두 번
        # 찍힌다. 체크박스가 필요한 `open-issues` 만 따로 렌더한다.
        out.append(f'<div class="tblock"><h2>{_esc(_plain(section.title))}</h2>')
        out.append(_blocks(section.body))
        out.append("</div>")

    for section in netlist.of_kind("open-issues"):
        out.append(f"<h2>{_esc(_plain(section.title))} — 실험실에서 확인할 것</h2>")
        # 표 줄을 **빈 줄로 바꾼다.** 지워 버리면 표가 유일한 구분자였던 두
        # 문단이 한 문단으로 합쳐진다 — `_blocks` 는 빈 줄에서만 문단을 끊는다.
        # 표는 아래에서 체크박스를 붙여 따로 렌더한다. `_blocks` 에 그대로
        # 넘기면 체크박스 없는 사본이 앞에 한 번 더 찍힌다.
        prose = "\n".join("" if line.strip().startswith("|") else line
                          for line in section.body.split("\n"))
        out.append(_blocks(prose))
        for table in md.parse_tables(section.body):
            out.append(_md_table_html(table, lead_checkbox=True))

    return "\n".join(out)


_CHIP_LINE = re.compile(r"^-[ \t]+(U\d+[ \t]*=[ \t]*.+)$")
# ``## U1 = `7490` (decade counter)`` — 실험02·10 의 배선 표기. `IC_DECL` 은
# 이미 이 형식을 읽는다(netlist_parser.py). 렌더러만 못 읽어서 실험10 P1 의
# 배선 80줄이 통째로 사라졌다.
_CHIP_HEAD = re.compile(r"^#{2,}[ \t]+(U\d+[ \t]*=[ \t]*.+?)[ \t]*$")
_ANY_HEAD = re.compile(r"^#{1,}[ \t]+\S")

_PHOTO = {
    "truth-table": "사진: 완성 회로 1장 + 불일치 행마다 1장. 파일명 {tid} row3.jpg 형식",
    "stepped": "사진: 스텝마다 1장. 파일명 {tid} row3.jpg 형식",
    "capture": "사진: 파형 자체가 결과물이다. 파일명 {tid} row1.jpg 형식",
}


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
            table, nxt = md.parse_table_at(lines, i)
            if table is None:
                # 구분선 없는 `|` 줄은 표가 아니다. 불릿형 상자를 열어 둔 채
                # 넘기면 그 뒤 줄들이 엉뚱하게 배선으로 붙는다.
                if form == "bullet":
                    close_chip()
                i += 1
                continue
            if chip is not None and form == "heading":
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


def _chip_swap(previous, current) -> str:
    """칩 교체 배너. 준비물이 종류당 하나라 순차 배선이 강제된다 (netlist M10).

    같은 칩이 다음 회로에도 쓰이면 패키지는 남지만 **점퍼선은 다르다** —
    netlist 가 "항목마다 재배선해 쓰는 것"이라고 적는다. `그대로 둔다` 로만
    적으면 배선까지 그대로 둬도 되는 것으로 읽힌다.
    """
    if previous is None:
        return "준비 — 꽂는다: " + ", ".join(current.ics)
    remove = [c for c in previous.ics if c not in current.ics]
    add = [c for c in current.ics if c not in previous.ics]
    keep = [c for c in current.ics if c in previous.ics]
    parts = ["앞 회로의 점퍼선을 모두 걷는다"]
    if remove:
        parts.append("뺀다: " + ", ".join(remove))
    if add:
        parts.append("꽂는다: " + ", ".join(add))
    if keep:
        parts.append("패키지는 두고 재배선한다: " + ", ".join(keep))
    return " · ".join(parts)


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
            return (f'<img src="{_esc(src)}" style="width:100%">'
                    f'<p class="src">결선도: {_esc(section.diagram)}</p>')
    rows = crop_rows(section.body)
    visible_mm = _BREADBOARD_HEADER_MM + rows * 6
    return (f"<h3>브레드보드 작도 ({rows}행)</h3>"
            "<p class='src'>이 회로의 결선도가 아직 없다 — 격자에 직접 그린다</p>"
            f'<img src="{config.root_relative_prefix()}.claude/assets/Breadboard.jpg" '
            f'style="width:100%;max-height:{visible_mm:.1f}mm;object-fit:cover;'
            'object-position:top">')


def _mismatch_html() -> str:
    """결과보고서의 `예상과의 비교`가 여기서 나온다. 확인 칸 하나로는 좁다."""
    head = ('<table class="mismatch"><thead><tr><th>불일치 행</th><th>예상</th>'
            "<th>실제</th><th>사진 파일</th><th>짐작된 원인</th></tr></thead><tbody>")
    body = "".join("<tr>" + "<td></td>" * 5 + "</tr>" for _ in range(3))
    return head + body + "</tbody></table>"


def _circuit_tables(spec, section) -> str:
    out = []
    for table_id in section.tables:
        table = spec.table(table_id)
        if table is None or table.role == "reference":
            continue
        out.append('<div class="tblock">')
        out.append(f"<h3>{_esc(table.id)} · {_esc(table.title)}</h3>")
        # `_plain` 을 씌운다 — 옛 `_tables()` 는 안 씌웠다. 지금 어느 명세의
        # `source` 에도 마크다운이 없지만, 들어오는 순간 백틱이 인쇄본에 찍히고
        # 그것을 잡는 검사는 본문만 본다.
        out.append(f"<p class='src'>출처: {_esc(_plain(table.source or ''))}</p>")
        out.append(_capture_html(table) if table.kind == "capture"
                   else _truth_or_stepped_html(table))
        out.append(f"<p class='photo'>"
                   f"{_esc(_PHOTO[table.kind].format(tid=table.id))}</p>")
        out.append(_mismatch_html())
        out.append("</div>")
    return "\n".join(out)


def circuit_pages(spec, netlist) -> str:
    """회로마다 한 면. 강제 개쪽이라 회로 둘이 한 쪽을 나눠 쓰지 않는다.

    면 안의 순서는 작업 순서다 — 칩 교체 → 유의사항 → 결선도 → 배선 → 미사용핀
    → 측정표. 유의사항(예: `74HC02 는 핀 순서에 주의`)을 배선 앞으로 옮겼다 —
    그것을 실행하며 봐야 할 배선 뒤에 두면 이미 다 꽂은 뒤에야 읽게 된다.
    미사용핀 상자는 칩별로 낸다 — 회로 단위로 합치면 C4 처럼 같은 핀 번호가
    칩마다 정반대 지시를 받을 때 어느 칩 것인지 사라진다.
    """
    out, previous = [], None
    total = len(netlist.circuits)
    for n, section in enumerate(netlist.circuits, start=1):
        nodes, prose_before, prose_after = _circuit_body(section)
        chips = _chip_boxes(nodes)
        tables = ", ".join(section.tables)
        item = next((i for i in spec.items if i.id == section.item), None)
        device = f" · 판독: {', '.join(item.device)}" if item else ""
        out.append('<section class="circuit">')
        out.append(f"<h2>회로 {n}/{total} · {_esc(_plain(section.title))} "
                   f"· 기록: {_esc(tables)}{_esc(device)}</h2>")
        out.append(f'<div class="banner">{_esc(_chip_swap(previous, section))}</div>')
        if prose_before.strip():
            out.append(_blocks(prose_before))
        out.append('<div class="wirebox">')
        out.append(_diagram_html(section, netlist))
        for node in nodes:
            if node["type"] == "prose":
                out.append(_blocks(node["text"]))
                continue
            out.append(f'<div class="chip"><h4>{_esc(node["head"])}</h4>')
            if node["wires"]:
                out.append('<ol start="1">')
                out += [f'<li><span class="box"></span>{_esc(w)}</li>'
                        for w in node["wires"]]
                out.append("</ol>")
            # 상자 안은 원문 순서다. 고정 순서로 찍으면 표 앞에 있어야 할 경고가
            # 표 아래로 밀린다 (실험02 U1) — 주차마다 표와 산문의 순서가 다르다.
            for kind, payload in node["blocks"]:
                out.append(_md_table_html(payload, lead_checkbox=True)
                           if kind == "table" else _blocks(payload))
            out.append("</div>")
        out.append("</div>")
        unused_chips = [c for c in chips if c["unused"]]
        if unused_chips:
            out.append('<div class="unused">'
                       "<b>배선을 끝내고 반드시 확인한다 — 칩마다 따로 본다</b>")
            for chip in unused_chips:
                out.append(f'<div class="chipunused"><b>{_esc(chip["head"])}</b><ul>')
                out += [f'<li><span class="box"></span>{_esc(u)}</li>'
                        for u in chip["unused"]]
                out.append("</ul></div>")
            out.append("</div>")
        if prose_after.strip():
            # 배선을 마친 뒤 하는 검산이다. 앞으로 올리면 preamble 로 읽힌다.
            out.append(_blocks(prose_after))
        out.append(_circuit_tables(spec, section))
        out.append("</section>")
        previous = section
    return "\n".join(out)


CLOSING = (
    "표마다 확인 칸이 다 찼는가 (진행하지 않은 표에는 진행하지 않았음 을 적는다)",
    "회로마다 완성 회로 사진을 찍었는가",
    "진리표는 불일치 행마다 사진을 찍었는가",
    "사진 파일명이 T1 row3.jpg 형식인가",
    "공통면의 실험실 확인 목록을 다 처리했는가",
    "조교에게 물어볼 것을 다 물었는가",
    "부품을 반납했는가",
)


def closing_page() -> str:
    """실험실을 나오기 전 30초. 여기서 빠뜨린 것은 결과보고서에서 못 채운다."""
    items = "".join(f'<li><span class="box"></span>{_esc(c)}</li>'
                    for c in CLOSING)
    return f"<h2>실험실을 나오기 전에</h2><ul>{items}</ul>"


def render_checklist(spec, netlist, template) -> str:
    """`netlist` 는 `netlist_parser.LabNetlist` 다 — 날 문자열이 아니다.

    회로 메타 없이는 인쇄본을 낼 수 없다. 옛 결선도를 "옛 방식으로 대충" 렌더하는
    관용을 두지 않는다 — 렌더러가 두 벌이 되고 어느 주차가 어느 레이아웃인지
    조용히 갈린다. 파서가 백필 방법을 담아 거절한다.
    """
    title = config.document_title(spec.experiment, spec.title, "체크리스트")
    return (template
            .replace("{{TITLE}}", _esc(title))
            .replace("{{COMMON}}", common_page(spec, netlist))
            .replace("{{CIRCUITS}}", circuit_pages(spec, netlist))
            .replace("{{CLOSING}}", closing_page()))
