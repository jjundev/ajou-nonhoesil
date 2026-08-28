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

MAX_BREADBOARD_ROWS = 30
_PIN_ROW = re.compile(r"pin\s+(\d+)")


def crop_rows(netlist_text: str) -> int:
    """netlist 가 실제로 쓰는 행 수. 브레드보드 템플릿을 여기에 맞춰 자른다.

    소스가 하나이므로 크롭이 자동 계산된다 (R7).
    """
    ic_count = netlist_text.count(" = 74")
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

    netlist 본문의 **모든 불릿**을 싣는다. 영문 `pin` 이 든 줄만 고르면
    한글로 쓴 경고가 통째로 사라진다 — 실제로 "입력을 띄워두지 않는다"(이 과목의
    대표 실패 원인)와 "74HC02 는 핀 배치가 다르다"(netlist 가 스스로 가장 흔한
    배선 실수라고 표시한 것)가 인쇄본에서 빠져 있었다.
    """
    power = " · ".join(f"{k} = {v}" for k, v in spec.power.items())
    out = [f'<div class="power">전원: {_esc(power)} · '
           "미사용 입력핀은 전부 GND (플로팅 금지)</div>"]
    _, body = md.split_frontmatter(netlist_text)
    step, open_list, pending_heading = 0, False, None
    for line in body.split("\n"):
        stripped = line.strip()
        if stripped.startswith("#"):
            if open_list:
                out.append("</ol>")
                open_list = False
            # 바로 내보내지 않는다. 표나 산문만 딸린 절(`참조 핀아웃`,
            # `미확정 사항`)은 항목이 하나도 없어서 빈 제목만 인쇄된다.
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
        elif open_list and stripped and line.startswith(" ") and out[-1].endswith("</li>"):
            # 들여쓴 이어지는 줄은 앞 항목에 붙인다. 버리면 여러 줄로 쓴 경고가
            # 중간에서 잘린다 — 74HC02 핀 배치 경고가 실제로 그렇게 잘렸다.
            out[-1] = out[-1][: -len("</li>")] + " " + _esc(_plain(stripped)) + "</li>"
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
    # 제목만 앞 쪽에 남고 그림이 다음 쪽으로 넘어가는 것을 막는다 — 표와 같은 이유다.
    return (f'<div class="tblock"><h2>브레드보드 작도 ({rows}행)</h2>'
            f"<p>단자: {_esc(labels)}</p>"
            f'<img src="../../.claude/assets/Breadboard.jpg" '
            f'style="width:100%;max-height:{rows * 6}mm;object-fit:cover;'
            'object-position:top"></div>')


def render_checklist(spec, netlist_text, template) -> str:
    title = f"{spec.week}주차 · 실험{spec.experiment} {spec.title} 체크리스트"
    return (template
            .replace("{{TITLE}}", _esc(title))
            .replace("{{PROCEDURE}}", _procedure(spec, netlist_text))
            .replace("{{TABLES}}", _tables(spec))
            .replace("{{BREADBOARD}}", _breadboard(spec, netlist_text)))
