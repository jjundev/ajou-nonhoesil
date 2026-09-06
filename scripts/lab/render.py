"""kind 별 인쇄 레이아웃. 실험실 조건이 설계 제약이다.

확인 칸은 세로로 정렬되어야 한다 — 세로줄 하나로 관통해 "전항 일치"를 표기하는
방식이 태블릿 필기에서 가장 빠르기 때문이다. 칸과 숫자 사이에는 vision 전사가
체크와 숫자를 구분할 여백이 있어야 한다.

`role: reference` 표는 인쇄본에서 제외한다. 실험실에서 채우는 물건이 아니라
예비보고서 이론 절의 재료다.
"""

import html
import re

from . import md
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
# IC 선언(`U<n> = <칩>`) 을 센다. `" = 74"` 로 좁히면 40xx·555 계열 IC 를
# 쓰는 주차는 0개로 세어 위 degenerate 크롭(머리띠보다 작은 상자)에 빠진다.
_IC_DECL = re.compile(r"\bU\d+\s*=\s*\S")


def crop_rows(netlist_text: str) -> int:
    """netlist 가 실제로 쓰는 행 수. 브레드보드 템플릿을 여기에 맞춰 자른다.

    소스가 하나이므로 크롭이 자동 계산된다 (R7).
    """
    ic_count = len(_IC_DECL.findall(netlist_text))
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


def _procedure(spec, netlist_text) -> str:
    """결선 절차. VCC/GND/미사용핀을 최상단 박스에 둔다.

    netlist 본문의 **모든 불릿과 산문 줄**을 싣는다. 영문 `pin` 이 든 줄만
    고르면 한글로 쓴 경고가 통째로 사라진다 — 실제로 "입력을 띄워두지
    않는다"(이 과목의 대표 실패 원인)와 "74HC02 는 핀 배치가 다르다"(netlist
    가 스스로 가장 흔한 배선 실수라고 표시한 것)가 인쇄본에서 빠져 있었다.

    불릿·헤딩과 별개로 **열 0 의 산문 줄**(절 도입문·꼬리 경고 등)도 그 절의
    `<p>` 로 내보낸다 — 안 그러면 "복합회로 X≡Z 항등이 깨지면 배선 오류"
    처럼 불릿이 아닌 형태로 쓰인 경고가 조용히 사라진다. 표 줄(`|` 로 시작)은
    여전히 건너뛴다 — `role: reference` 표와 같은 이유로 이 인쇄본의 대상이
    아니다(§섹션별 재료). `참조 핀아웃`·`미확정 사항`처럼 표만 딸린 절은
    지금도 산문이 없으면 여전히 빈 제목을 인쇄하지 않는다.
    """
    power = " · ".join(f"{k} = {v}" for k, v in spec.power.items())
    out = [f'<div class="power">전원: {_esc(power)} · '
           "미사용 입력핀은 전부 GND (플로팅 금지)</div>"]
    _, body = md.split_frontmatter(netlist_text)
    step, open_list, pending_heading, blank_before = 0, False, None, False
    for line in body.split("\n"):
        stripped = line.strip()
        if not stripped:
            blank_before = True
            continue
        if stripped.startswith("#"):
            if open_list:
                out.append("</ol>")
                open_list = False
            # 바로 내보내지 않는다. 표만 딸린 절(`참조 핀아웃`, `미확정 사항`)은
            # 항목이 하나도 없어서 빈 제목만 인쇄된다.
            pending_heading = stripped.lstrip("# ")
        elif stripped.startswith("- "):
            if pending_heading is not None:
                out.append(f"<h3>{_esc(pending_heading)}</h3>")
                pending_heading = None
            if not open_list:
                out.append(f'<ol start="{step + 1}">')
                open_list = True
            step += 1
            out.append(f"<li>{_esc(_plain(stripped[2:]))}</li>")
        elif open_list and line.startswith(" ") and out[-1].endswith("</li>"):
            # 들여쓴 이어지는 줄은 앞 항목에 붙인다. 버리면 여러 줄로 쓴 경고가
            # 중간에서 잘린다 — 74HC02 핀 배치 경고가 실제로 그렇게 잘렸다.
            out[-1] = out[-1][: -len("</li>")] + " " + _esc(_plain(stripped)) + "</li>"
        elif not stripped.startswith("|") and not line.startswith(" "):
            # 헤딩도 불릿도 아닌 열 0 산문 — 절 도입문이거나 목록 뒤에 남는
            # 마무리 경고다. 표 줄(`|`)과 불릿의 들여쓴 이어짐은 위에서 이미
            # 처리했으므로 여기 남는 건 진짜 산문뿐이다.
            if open_list:
                out.append("</ol>")
                open_list = False
            if pending_heading is not None:
                out.append(f"<h3>{_esc(pending_heading)}</h3>")
                pending_heading = None
            text = _esc(_plain(stripped))
            if not blank_before and out and out[-1].startswith("<p>") and out[-1].endswith("</p>"):
                # 빈 줄 없이 이어지는 산문 줄은 같은 문단이다 — 줄바꿈만 있고
                # 빈 줄이 없는 마크다운 문단은 한 덩어리로 합쳐야 한다
                # (netlist.md 의 "다르면 배선 오류다" 경고가 실제로 두 줄이다).
                out[-1] = out[-1][: -len("</p>")] + " " + text + "</p>"
            else:
                out.append(f"<p>{text}</p>")
        blank_before = False
    if open_list:
        out.append("</ol>")
    return "\n".join(out)


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
    """`- ` 불릿·열 0 산문·`##` 헤딩을 HTML 로. 표 줄(`|`)은 건너뛴다.

    들여쓴 이어지는 줄을 앞 항목에 붙인다 — 버리면 여러 줄로 쓴 경고가 중간에서
    잘린다. 74HC02 핀 순서 경고가 실제로 세 줄짜리 불릿이고, 그 경고를 netlist
    스스로 "이 실험에서 가장 흔한 배선 실수"라고 표시한다.

    빈 줄 없이 이어지는 열 0 산문 줄은 한 문단으로 합친다 — netlist 의
    "다르면 배선 오류다" 경고가 실제로 두 줄이다.
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

    for raw in body.split("\n"):
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped:
            flush_para()
            continue
        if stripped.startswith("|"):
            continue                      # 표는 부르는 쪽이 따로 렌더한다
        if stripped.startswith("#"):
            flush_items()
            flush_para()
            out.append(f"<h4>{_esc(_plain(stripped.lstrip('# ')))}</h4>")
            continue
        m = _BULLET.match(line)
        if m and not m.group(1):
            flush_para()
            items.append(_plain(m.group(2)))
            continue
        if line.startswith((" ", "\t")) and items:
            items[-1] += " " + _plain(stripped)
            continue
        flush_items()
        para.append(_plain(stripped))
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
        out.append(f'<div class="tblock"><h2>{_esc(_plain(section.title))}</h2>')
        out.append(_blocks(section.body))
        for table in md.parse_tables(section.body):
            out.append(_md_table_html(table))
        out.append("</div>")

    for section in netlist.of_kind("open-issues"):
        out.append(f"<h2>{_esc(_plain(section.title))} — 실험실에서 확인할 것</h2>")
        out.append(_blocks(section.body))
        for table in md.parse_tables(section.body):
            out.append(_md_table_html(table, lead_checkbox=True))

    return "\n".join(out)


_CHIP_LINE = re.compile(r"^-[ \t]+(U\d+[ \t]*=[ \t]*.+)$")

_PHOTO = {
    "truth-table": "사진: 완성 회로 1장 + 불일치 행마다 1장. 파일명 {tid} row3.jpg 형식",
    "stepped": "사진: 스텝마다 1장. 파일명 {tid} row3.jpg 형식",
    "capture": "사진: 파형 자체가 결과물이다. 파일명 {tid} row1.jpg 형식",
}


def _split_circuit_body(section):
    """회로 본문을 (칩 상자, 미사용핀 줄, 산문) 으로 가른다.

    `- U<n> = <칩>` 이 상자의 제목이고 그 아래 들여쓴 `- ` 가 배선이다. 옛
    렌더러는 들여쓰기를 무시하고 전부 형제 번호로 만들어 **칩의 경계가 사라졌다**.

    미사용핀 줄은 상자에서 빼내 별도 강조 박스로 보낸다 — 플로팅 입력이 이
    과목의 대표 실패 원인인데 긴 목록의 마지막 두 줄로 묻혀 있었다.

    `- U<n> =` 형태의 칩 선언이 하나도 없으면(실험10 처럼 `## U1 = ...` 헤딩을
    쓰는 결선도) 상자를 만들지 않고 본문 전체를 산문으로 흘린다. 조용히 버리는
    것보다 낫다.
    """
    chips, unused, prose = [], [], []
    current = None
    for raw in section.body.split("\n"):
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("|"):
            continue
        m = _CHIP_LINE.match(line)
        if m:
            current = {"head": _plain(m.group(1)), "wires": []}
            chips.append(current)
            continue
        if stripped.startswith("- ") and line.startswith((" ", "\t")) and current:
            text = _plain(stripped[2:])
            (unused if text.startswith("미사용") else current["wires"]).append(text)
            continue
        if line.startswith((" ", "\t")) and current and current["wires"]:
            current["wires"][-1] += " " + _plain(stripped)
            continue
        prose.append(line)
    return chips, unused, "\n".join(prose)


def _chip_swap(previous, current) -> str:
    """칩 교체 배너. 준비물이 종류당 하나라 순차 배선이 강제된다 (netlist M10)."""
    if previous is None:
        return "준비: " + ", ".join(current.ics) + " 를 꽂는다"
    remove = [c for c in previous.ics if c not in current.ics]
    add = [c for c in current.ics if c not in previous.ics]
    keep = [c for c in current.ics if c in previous.ics]
    parts = []
    if remove:
        parts.append("뺀다: " + ", ".join(remove))
    if add:
        parts.append("꽂는다: " + ", ".join(add))
    if keep:
        parts.append("그대로 둔다: " + ", ".join(keep))
    return " · ".join(parts) or "칩 교체 없음"


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

    면 안의 순서는 작업 순서다 — 칩 교체 → 결선도 → 배선 → 미사용핀 → 유의사항
    → 측정표. `[결선도+배선]` 과 `[표]` 만 통짜로 유지하므로, 넘칠 때 갈리는
    지점이 "다 꽂았다"는 순간과 일치한다.
    """
    out, previous = [], None
    total = len(netlist.circuits)
    for n, section in enumerate(netlist.circuits, start=1):
        chips, unused, prose = _split_circuit_body(section)
        tables = ", ".join(section.tables)
        out.append('<section class="circuit">')
        out.append(f"<h2>회로 {n}/{total} · {_esc(_plain(section.title))} "
                   f"· 기록: {_esc(tables)}</h2>")
        out.append(f'<div class="banner">{_esc(_chip_swap(previous, section))}</div>')
        out.append('<div class="wirebox">')
        out.append(_diagram_html(section, netlist))
        for chip in chips:
            out.append(f'<div class="chip"><h4>{_esc(chip["head"])}</h4><ol start="1">')
            out += [f'<li><span class="box"></span>{_esc(w)}</li>'
                    for w in chip["wires"]]
            out.append("</ol></div>")
        out.append("</div>")
        if unused:
            out.append('<div class="unused"><b>배선을 끝내고 반드시 확인한다</b><ul>')
            out += [f'<li><span class="box"></span>{_esc(u)}</li>' for u in unused]
            out.append("</ul></div>")
        if prose.strip():
            out.append(_blocks(prose))
        out.append(_circuit_tables(spec, section))
        out.append("</section>")
        previous = section
    return "\n".join(out)


def _tables(spec) -> str:
    out = []
    for item in spec.items:
        out.append(f"<h2>{_esc(item.id)} · {_esc(item.title)}</h2>")
        out.append(f"<p>IC: {_esc(', '.join(item.ics))} · "
                   f"판독: {_esc(', '.join(item.device))}</p>")
        for table_id in item.tables:
            table = spec.table(table_id)
            if table.role == "reference":
                continue          # 참조표는 인쇄본에 넣지 않는다 (③ 이론 절의 재료다)
            # 제목·출처·표를 한 덩어리로 묶는다 — 캡션만 앞 쪽에 남으면
            # 어느 표의 출처인지 실험실에서 알 수 없다.
            out.append('<div class="tblock">')
            out.append(f"<h3>{_esc(table.id)} · {_esc(table.title)}</h3>")
            out.append(f"<p class='src'>출처: {_esc(table.source)}</p>")
            out.append(_capture_html(table) if table.kind == "capture"
                       else _truth_or_stepped_html(table))
            out.append("</div>")
        out.append('<div class="pair">'
                   "<div><b>결선도</b><br>(사진 부착)</div>"
                   "<div><b>구성한 회로</b><br>(사진 부착)</div></div>")
    return "\n".join(out)


def _breadboard(spec, netlist_text) -> str:
    rows = crop_rows(netlist_text)
    labels = " · ".join(f"{k}={v}" for k, v in spec.power.items())
    # 머리띠(_BREADBOARD_HEADER_MM)를 예산에 더해야 캡션이 약속하는 `rows`행이
    # 실제로 보인다 — 안 더하면 머리띠가 예산을 깎아먹어 IC 가 적은 주차는
    # 격자가 한 줄도 없이 로고만 인쇄된다 (B1).
    visible_mm = _BREADBOARD_HEADER_MM + rows * 6
    # 제목만 앞 쪽에 남고 그림이 다음 쪽으로 넘어가는 것을 막는다 — 표와 같은 이유다.
    return (f'<div class="tblock"><h2>브레드보드 작도 ({rows}행)</h2>'
            f"<p>단자: {_esc(labels)}</p>"
            f'<img src="{config.root_relative_prefix()}.claude/assets/Breadboard.jpg" '
            f'style="width:100%;max-height:{visible_mm:.1f}mm;object-fit:cover;'
            'object-position:top"></div>')


def render_checklist(spec, netlist_text, template) -> str:
    title = config.document_title(spec.experiment, spec.title, "체크리스트")
    return (template
            .replace("{{TITLE}}", _esc(title))
            .replace("{{PROCEDURE}}", _procedure(spec, netlist_text))
            .replace("{{TABLES}}", _tables(spec))
            .replace("{{BREADBOARD}}", _breadboard(spec, netlist_text)))
