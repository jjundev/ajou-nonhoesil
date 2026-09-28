"""kind 별 인쇄 레이아웃. 실험실 조건이 설계 제약이다.

확인 칸은 세로로 정렬되어야 한다 — 세로줄 하나로 관통해 "전항 일치"를 표기하는
방식이 태블릿 필기에서 가장 빠르기 때문이다. 칸과 숫자 사이에는 vision 전사가
체크와 숫자를 구분할 여백이 있어야 한다.

`role: reference` 표는 인쇄본에서 제외한다. 실험실에서 채우는 물건이 아니라
예비보고서 이론 절의 재료다.
"""

import html
import json
import re
from dataclasses import replace
from pathlib import Path

from . import md
from . import nodes as node_calc
from .netlist_parser import IC_DECL
from .notation import normalize_cell
from .spec_parser import split_indices
from .photo_names import item_token, photo_name
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


def _truth_table_html(table, token=None) -> str:
    """진리표 — 입력은 주어지고, 출력에 `예상` 을 병기한 뒤 확인 칸을 붙인다.

    `_plain` 으로 마크다운 표기를 먼저 벗기고 나서 `normalize_cell` 로 논리값을
    정규화한다 — 순서가 반대면 `**1**` 같은 굵게 표기 셀이 정규화를 통과하지
    못하고 별표째 인쇄본에 남는다.

    `token`(항목 토큰, 예 `1-2`)이 있으면 행마다 찍을 사진 파일명 열을 붙인다 —
    `contact_sheet` 가 그대로 읽는 `<항목> <입력비트>.jpg` 다. 비트는 입력 **자리**
    순서다. 입력 셀이 0/1 이 아니면(don't-care 등) 한 장으로 찍을 조합이 아니라 `—`.
    `.check` 가 아니라 `.photo-name` 이다 — `.check` 개수는 행 수 불변식이다.
    """
    # 셀은 이름이 아니라 자리로 찾는다 — 입력과 출력이 같은 글자인 표가 있다
    # (실험3 반감산기 `A B D B`). `record._truth_table` 과 같은 규약이다.
    inputs, outputs = split_indices(table)
    head = [table.header[i] for i in inputs] + [f"{table.header[i]}예상" for i in outputs]
    body = [[normalize_cell(_plain(row[i])) for i in inputs]
            + [normalize_cell(_plain(row[i])) for i in outputs]
            for row in table.rows]

    # thead/tbody 로 나눈다 — 표가 쪽을 넘어가도 헤더가 따라가야 한다.
    # 헤더 없는 진리표 조각은 실험실에서 읽을 수 없다.
    out = ["<table>", "<thead>", "<tr>"]
    out += [f"<th>{_esc(h)}</th>" for h in head]
    out.append("<th>확인</th>" + ("<th>사진 파일명</th>" if token else "") + "</tr>")
    out += ["</thead>", "<tbody>"]
    for row in body:
        cells = "".join(f"<td>{_esc(c)}</td>" for c in row) + '<td class="check"></td>'
        if token:
            bits = row[:len(inputs)]
            name = (photo_name(token, "".join(bits))
                    if all(b in ("0", "1") for b in bits) else "—")
            cells += f'<td class="photo-name">{_esc(name)}</td>'
        out.append(f"<tr>{cells}</tr>")
    out += ["</tbody>", "</table>"]
    return "\n".join(out)


def _stepped_html(table) -> str:
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
    header = list(table.header)
    rows = [[_plain(c) for c in row] for row in table.rows]
    if not any(not c.strip() for row in rows for c in row):
        header.append("기록")
        rows = [row + [""] for row in rows]

    out = ["<table>", "<thead>", "<tr>"]
    out += [f"<th>{_esc(h)}</th>" for h in header]
    out += ["</tr>", "</thead>", "<tbody>"]
    for row in rows:
        out.append("<tr>" + "".join(
            '<td class="fill"></td>' if not c.strip() else f"<td>{_esc(c)}</td>"
            for c in row) + "</tr>")
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

    미니표는 붙이지 않는다(`_mismatch_html` 이 `capture` 에 `""` 를 준다).
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
            out.append(f'<img class="expected-fig" src="{_esc(table.figure)}">'
                       f"<p class='src'>예상 그림: {_esc(name)}</p>")
        else:
            out.append(f"<p class='src'>예상 그림이 아직 없다: {_esc(name)}</p>")
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


LEGEND = (
    "진리표 — 확인 칸: ✓ 일치 / 값 = 불일치 시 실제로 관찰한 값 / 공란 = 미확인. "
    "표를 통째로 진행하지 않았으면 그 표 아래에 진행하지 않았음 이라고 적는다.",
    "스텝표 — 회색 칸에 읽은 값을 단위와 함께 적는다 (예: 3.2 V, 47 Ω). "
    "확인 칸이 없다: 대조할 예상값이 없는 표다.",
    "파형 — 격자에 직접 그리고 판독 조건 줄(V/div·time/div·프로브·모드)을 채운다. "
    "조건이 없으면 결과보고서에서 화면의 칸을 볼트로 환산할 수 없다.",
)


# 공통면 물리 주의. 셋째 줄만 주차에 따라 갈린다 — 배너 원칙("모든 주차에서 참인
# 것만")대로 걷기 보드가 없는 주차에서 걷기 그림을 가리키지 않는다.
_CAUTION = (
    "선은 클립에 물릴 깊이까지만 꽂는다 — 끝까지 밀어 넣으면 접촉이 끊길 수 있다 (실험03 GND 선)",
    "칩을 꽂고 뽑을 때는 전원을 끈다",
)
_CAUTION_SWAP = {
    True: "선을 뽑을 때는 걷기 그림(빨간 점선)의 선부터 먼저 뽑고 새 선을 꽂는다 — "
          "회로를 바꿀 때도, 회로 안에서도 같다",
    False: "회로를 바꿀 때는 걷을 선부터 먼저 뽑고 새 선을 꽂는다",
}

# 선 색 — 결선도 PNG 아래 범례가 사라져(2026-09-28) 공통면에 한 번 싣는다. 색은
# 렌더러의 `WIRE`·`KEEP`·`REMOVE`·`PROBE` 와 같다(렌더러를 import 하지 않는다)
WIRE_LEGEND = ("선 색 — 빨강 +5V · 파랑 0V · 검정 신호 · 초록 칩 사이 중간 노드 · "
               "회색 = 앞 단계에서 그대로 둔다 · 빨간 점선 = 뽑는다 · "
               "회색 점선 = 계측기(꽂지 않고 문다)")


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
    """회로 페이지들 앞에 한 번만 오는 면.

    `kind` 가 목적지를 정한다. **`common`·`open-issues` 는 싣지 않는다**(2026-09-28) —
    공통 규칙과 미확정 표가 실험04 공통면 4쪽을 차지했는데 실험실에서 읽히지 않았다.
    둘 다 netlist 에 저작·검토용으로 남는다. 실험실에서 손으로 해야 하는 것은
    저작자가 `must-read` 절(불릿 다섯)로 올리고 그것만 전원 박스 바로 아래 싣는다.
    `sources`(핀아웃 출처)는 ③ 예비보고서의 참고문헌 재료라 여기 없다.
    """
    power = " · ".join(f"{k} = {v}" for k, v in spec.power.items())
    # 배너는 **모든 주차에서 참인 것**만 말한다. 옛 문구 "미사용 입력핀은 전부 GND" 는
    # 주차의 절반에서 거짓이었다(실험02 는 VCC 로도 올린다). 칩별 미사용 핀 지시는 회로
    # 쪽 핀 점검 상자에 있다.
    out = [f'<div class="power">전원: {_esc(power)} · '
           "사용하는 게이트의 입력은 반드시 물린다 (플로팅 금지) — "
           "미사용 핀은 회로마다 핀 점검 상자를 본다</div>"]
    for section in netlist.of_kind("must-read"):
        out.append(f'<div class="must-read"><h2>{_esc(_plain(section.title))}</h2>'
                   f"{_blocks(section.body)}</div>")
    walk = any(_has_walk(c) for c in netlist.circuits)
    lines = _CAUTION + (_CAUTION_SWAP[walk],)
    out.append('<div class="caution"><b>손으로 할 때 주의</b><ul>'
               + "".join(f"<li>{_esc(line)}</li>" for line in lines)
               + "</ul></div>")
    out.append(f'<p class="wire-legend">{_esc(WIRE_LEGEND)}</p>')
    out += [f'<p class="legend">{_esc(line)}</p>' for line in LEGEND]
    out += ["<h2>오늘의 흐름</h2>", _flow_table(spec, netlist)]

    for section in netlist.of_kind("lookup"):
        # `_blocks` 가 본문의 표를 제자리에 싣는다 — 여기서 또 렌더하면 두 번 찍힌다
        out.append(f'<div class="tblock"><h2>{_esc(_plain(section.title))}</h2>')
        out.append(_blocks(section.body))
        out.append("</div>")

    for section in netlist.of_kind("layout"):
        # 칩 자리표. 다섯 회로가 같은 자리를 쓴다는 선언이라 한 번만 보면 된다
        out.append(f'<div class="tblock"><h2>{_esc(_plain(section.title))}</h2>')
        out.append(_blocks(section.body))
        out.append("</div>")

    return _drop_issue_refs("\n".join(out))


_CHIP_LINE = re.compile(r"^-[ \t]+(U\d+[ \t]*=[ \t]*.+)$")
# ``## U1 = `7490` (decade counter)`` — 실험02·10 의 배선 표기. `IC_DECL` 은
# 이미 이 형식을 읽는다(netlist_parser.py). 렌더러만 못 읽어서 실험10 P1 의
# 배선 80줄이 통째로 사라졌다.
_CHIP_HEAD = re.compile(r"^#{2,}[ \t]+(U\d+[ \t]*=[ \t]*.+?)[ \t]*$")
_ANY_HEAD = re.compile(r"^#{1,}[ \t]+\S")

# 사진 파일명은 `photo_names` 규칙이다. 실험02 는 `실험02 1-1 …` 처럼 접두어를 붙여
# 시트 엔진이 전부 규칙 밖으로 거절했다 — 그래서 접두어 금지를 줄마다 적는다.
_NO_PREFIX = "앞에 실험 번호(예: 실험03)를 붙이지 않는다"
_PHOTO = {
    "truth-table": "사진: 시험한 행마다 1장(불일치 행 필수). 파일명은 표의 '사진 파일명' 열 그대로 — " + _NO_PREFIX,
    "stepped": "사진: 스텝마다 1장. 파일명 '{tok} {tid} s<스텝>.jpg' — " + _NO_PREFIX,
    "capture": "사진: 파형 자체가 결과물이다. 파일명 '{tok} {tid} <설명>.jpg' — " + _NO_PREFIX,
}
# 항목 제목에 `실험 N)` 이 없으면 파일명 열이 없다 — 가리킬 열이 없으니 규칙을 적는다.
_PHOTO_NO_TOKEN = ("사진: 시험한 행마다 1장(불일치 행 필수). 파일명 '<항목> <입력비트>.jpg' — "
                   + _NO_PREFIX)


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
        return "준비 — 꽂는다: " + ", ".join(current.ics)
    if current.continues:
        # 이어 붙이는 회로가 선언한 칩은 **전부** 새로 꽂는 것이다. 앞 회로를
        # 그대로 두므로 이름이 겹쳐도 그것은 재배선이 아니라 **두 번째 패키지**다
        # — 실험10 C1 의 `U4 = 741 OP amp` 와 C2 의 `U5 = 741 OP amp` 가 그렇다.
        # 741 한 패키지에 op-amp 는 하나뿐이고 결선도가 "비교기를 하나 더
        # 붙인다"라고 적는다. `not in previous.ics` 로 거르면 이 기능의 존재
        # 이유인 그 지시가 배너에서 사라진다.
        # `continues` 는 언제나 직전 회로다(validate 가 강제한다). 인쇄본에
        # 없는 내부 ID(`C1`) 대신 학생이 앞 쪽에서 실제로 읽은 제목을 말한다.
        tail = " · 추가로 꽂는다: " + ", ".join(current.ics) if current.ics else ""
        return (f"앞 회로({_plain(previous.title)})를 그대로 두고 이어 붙인다 — "
                f"점퍼선을 걷지 않는다{tail}")
    remove = [c for c in previous.ics if c not in current.ics]
    add = [c for c in current.ics if c not in previous.ics]
    keep = [c for c in current.ics if c in previous.ics]
    if current.rebuild:
        # 앞 회로를 통째로 걷는 경계(2026-09-27, 실험04 C2). 단계 표가 있어도 `그대로 둔다`
        # 가 아니다. 기반(전원·브리지·LED 사슬)은 남긴다 — 다음 회로 1단계의 기반과 같은
        # 자리라 뽑으면 다시 꽂게 된다.
        parts = ["앞 회로의 신호선을 전부 뽑는다 — 전원선·레일 브리지·LED 사슬은 그대로 "
                 "둔다(새 선은 단계 그림이 지시한다)"]
    elif current.stages:
        if _has_entry_walk(current):
            parts = ["앞 회로 배선은 그대로 둔다 — 걷을 선은 걷기 그림(빨간 점선), "
                     "새 선은 단계 그림(회색·번호)이 지시한다"]
        else:
            parts = ["앞 회로 배선은 그대로 둔다 — 걷을 선·새 선은 단계 그림"
                     "(회색·번호·'걷는다' 표)이 지시한다"]
    else:
        parts = ["앞 회로의 점퍼선을 모두 걷는다"]
    if remove:
        parts.append("뺀다: " + ", ".join(remove))
    if add:
        parts.append("꽂는다: " + ", ".join(add))
    if keep:
        parts.append("패키지는 두고 재배선한다: " + ", ".join(keep))
    return " · ".join(parts)


def _schematic_html(item, spec_dir) -> str:
    """강의노트 게이트 회로도 — 항목의 첫 회로 페이지, 칩 교체 배너 바로 뒤.

    결선도를 보다가 "원래 회로가 뭐였지" 를 교안을 따로 열지 않고 확인하게 한다.
    `src` 는 명세 기준 상대경로 그대로다 — 인쇄본 HTML 이 명세와 같은 `체크리스트/`
    에 놓인다(`_capture_html` 의 `figure` 와 같은 논리). 파일이 없으면 `<img>` 를
    내지 않는다 — 깨진 그림이 PDF 로 굳는다. 필드가 없으면 빈 문자열이다.

    캡션은 `pages` 의 첫 쪽만 적는다 — `schematic.py` 는 `--page` 가 없으면
    `pages[0]` 을 자른다. 캡션은 `<img>` 를 하나라도 냈을 때만 붙인다 — 그림이
    없는데 캡션만 남으면 없는 그림을 가리킨다(파일이 없으면 안내 한 줄뿐이다).
    """
    if item is None or not item.schematic:
        return ""
    caption = (f"강의노트 p{item.pages[0]} · 회로 구성" if item.pages
               else "강의노트 · 회로 구성")
    out = []
    for rel in item.schematic:
        if (Path(spec_dir) / rel).exists():
            out.append(f'<img class="schematic" src="{_esc(rel)}">')
        else:
            out.append(f"<p class='src'>회로도가 아직 없다: {_esc(rel)}</p>")
    if any(o.startswith("<img") for o in out):
        out.append(f"<p class='src'>{_esc(caption)}</p>")
    return "".join(out)


# 결선도 PNG 옆 JSON 의 스키마. 렌더러(`render_breadboard.SIDECAR_SCHEMA`)와 같은 문자열 —
# 인쇄가 PIL 에 묶이지 않게 import 하지 않고 따로 든다
SIDECAR_SCHEMA = "breadboard-sidecar/v1"


def _sidecar(png: Path) -> dict:
    """PNG 옆 사이드카. PNG 만 있고 이것이 없으면 옛 렌더러 산출물이다 — 결선 순서가
    조용히 빠진 채 인쇄되지 않게 멈춘다."""
    side = png.with_suffix(".json")
    if not side.exists():
        raise FileNotFoundError(
            f"{side.name} 가 없다 — 결선도를 다시 뽑는다: python3 "
            ".claude/skills/breadboard-diagram/scripts/render_breadboard.py --experiment <N>")
    data = json.loads(side.read_text(encoding="utf-8"))
    if data.get("schema") != SIDECAR_SCHEMA:
        raise ValueError(f"{side.name} 의 schema 가 {data.get('schema')!r} 다 — "
                         f"{SIDECAR_SCHEMA} 로 다시 뽑는다")
    return data


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
        out.append(f'<p class="list-head">먼저 뽑는다</p><ul class="removals">{items}</ul>')
    if data["steps"]:
        items = "".join(
            f'<li class="step" data-kind="{_esc(s["kind"])}"><span class="box"></span>'
            f'<span class="n">{s["n"]}</span>'
            f'<span class="route">{_esc(s["from"])} → {_esc(s["to"])}'
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
        out.append(f'<p class="list-head">계측 — 꽂지 않고 문다</p><ol class="probes">{items}</ol>')
    if data["kept"]:
        out.append(f'<p class="kept">회색 = 앞 단계에서 그대로 둔 것 {data["kept"]}개</p>')
    return "".join(out)


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
            return (f'<figure class="board"><img src="{_esc(src)}" style="width:100%"></figure>'
                    f'<p class="src">결선도: {_esc(section.diagram)}</p>'
                    + _board_text_html(_sidecar(png)))
    rows = crop_rows(section.body)
    visible_mm = _BREADBOARD_HEADER_MM + rows * 6
    return (f"<h3>브레드보드 작도 ({rows}행)</h3>"
            "<p class='src'>이 회로의 결선도가 아직 없다 — 격자에 직접 그린다</p>"
            f'<img src="{config.root_relative_prefix()}.claude/assets/Breadboard.jpg" '
            f'style="width:100%;max-height:{visible_mm:.1f}mm;object-fit:cover;'
            'object-position:top">')


def _stage_html(stage, netlist, section, spec=None, last=False) -> str:
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
    """
    png = netlist.path.parent / stage["diagram"] if stage["diagram"] else None
    if png is not None and png.exists():
        src = f"../{netlist.path.parent.name}/{stage['diagram']}"
        img = f'<figure class="board"><img src="{_esc(src)}" style="width:100%"></figure>'
        text = _board_text_html(_sidecar(png))
    else:
        img = f"<p class='src'>단계 그림이 아직 없다: {_esc(stage['diagram'] or '(없음)')}</p>"
        text = ""
    node = ""
    if stage.get("node"):
        pin = next((n["pin"] for n in section.nodes if n["name"] == stage["node"]), "")
        tail = f" <small>({_esc(pin)})</small>" if pin else ""
        node = f"<p><b>확인 노드:</b> {_esc(_plain(stage['node']))}{tail}</p>"
    table = ""
    if spec is not None and stage.get("node") and not last:
        table = _stage_table_html(spec, section, stage["node"], _stage_led(stage["todo"]))
    # 걷기 행은 `단계 2걷기` 가 아니라 `단계 2 · 걷기` 로 찍는다 — 인쇄본에서
    # "2단계 머리의 걷기" 로 읽혀야 한다. 판정은 파서의 `walk` 키다.
    head = (f"단계 {_esc(str(stage['walk_of']))} · 걷기" if stage.get("walk")
            else f"단계 {_esc(stage['n'])}")
    # 블록 하나가 PDF 한 쪽이다 — 쪽 높이는 `fit_pages` 가 블록 실측값으로 준다.
    return (f'<div class="stage"><h3>{head}</h3>{img}'
            f"<p><b>이 단계에서:</b> {_esc(_plain(stage['todo']))}</p>{text}{node}"
            f'<p><span class="box"></span><b>확인:</b> {_esc(_plain(stage["check"]))}</p>'
            f"{table}</div>")


# 단계의 관측 LED — `이 단계에서` 칸의 `…→LED<n> 급전` 표기. 실험03·04 결선도가 관측
# 단계마다 정확히 하나씩 쓴다(2026-09-28 실측). 표기가 없거나 둘 이상이면 짐작하지 않는다.
_STAGE_LED = re.compile(r"→\s*LED\s*(\d+)\s*급전")


def _stage_led(todo) -> str:
    """`LED<n>` 또는 빈 문자열."""
    found = _STAGE_LED.findall(_plain(todo or ""))
    return f"LED{found[0]}" if len(found) == 1 else ""


_JUMPER = {"H/L": "H=+5V · L=GND"}


def _stage_table_html(spec, section, node_name, led="") -> str:
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
        return f"<p class='src'>단계 진리표를 계산할 수 없다: {_esc(exc)}</p>"
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
    return "\n".join(['<table class="stage-table">', "<thead>", head, "</thead>",
                      "<tbody>", *body, "</tbody>", "</table>"])


_MISMATCH = {
    "truth-table": ("불일치 행", "예상", "실제", "사진 파일", "짐작된 원인"),
    "stepped": ("이상 스텝", "관찰한 것", "짐작된 원인"),
}

_INSTRUMENT = "계측기 설정 — 모드·레인지·단위: ________________________________"


_MISMATCH_TITLE = {"truth-table": "불일치 기록", "stepped": "이상 스텝 기록"}


_NODE_HINT = ("틀린 행에서 입력 쪽 노드부터 프로브로 찍는다. 기대값과 처음 갈라지는 노드가 "
              "고장 자리다 — 그 게이트의 입력 핀이 틀리면 선, 맞으면 게이트")


def _record_outputs(spec, section) -> set:
    """기록표 출력 열 이름. 기록표가 없거나 입력 열이 어긋나면(validate 가 막는다) 빈 집합."""
    try:
        table = node_calc.record_table(section, spec)
    except ValueError:
        return set()
    if table is None:
        return set()
    return {table.header[i] for i in split_indices(table)[1]}


def _unstaged_nodes_html(spec, section) -> str:
    """단계에서 안 본 노드 — 어느 단계도 가리키지 않는 노드의 핀과 기대값. 기록표 뒤에 온다.

    2026-09-28 최종 리뷰: 옛 중간 노드 표를 통째로 없애면 한 단계 안에서 함께 세운 노드
    (실험04 C2 `S0'`·`S1'`)와 단계 없는 회로의 노드가 인쇄본에서 사라진다. 단계 진리표와
    겹치는 열은 찍지 않는다 — N1(겹치는 표 제거)의 취지는 그대로다. 읽는 표라 `.check` 가 없다.
    """
    staged = {s["node"] for s in section.stages if s.get("node")}
    keep = [k for k, n in enumerate(section.nodes) if n["name"] not in staged]
    if not keep:
        return ""
    try:
        nt = node_calc.compute(section, spec)
    except ValueError as exc:
        return f"<p class='src'>노드 표를 계산할 수 없다: {_esc(exc)}</p>"
    out = ['<div class="tblock nodes">',
           "<h3>단계에서 안 본 노드 — 프로브로 찍을 핀</h3>",
           f"<p class='src'>{_esc(_NODE_HINT)}</p>",
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


def _mismatch_html(kind: str, table_id: str) -> str:
    """결과보고서의 `예상과의 비교`가 여기서 나온다. 확인 칸 하나로는 좁다.

    kind 마다 열이 다르다. 스텝표에는 예상값이 없으므로 `예상`·`불일치 행` 열이
    설 자리가 없고, `capture` 는 아예 미니표를 갖지 않는다 — 파형에는 행도
    스텝도 없다. 그 자리는 `_capture_html` 의 `예상과 다른 점` 상자가 맡는다.

    표 앞에 `<h4>표ID · 종류</h4>` 를 붙여 자기 제목을 준다 — 표 제목은 앞
    쪽에 있어 쪽을 넘어가면(실험10 PDF 17쪽) `이상 스텝 | 관찰한 것 |
    짐작된 원인` 만 홀로 남는, 문맥 없는 3열 표가 된다.
    """
    head = _MISMATCH.get(kind)
    if head is None:
        return ""
    title = _MISMATCH_TITLE[kind]
    cells = "".join(f"<th>{_esc(h)}</th>" for h in head)
    body = "".join("<tr>" + "<td></td>" * len(head) + "</tr>" for _ in range(3))
    return (f"<h4>{_esc(table_id)} · {title}</h4>"
            f'<table class="mismatch"><thead><tr>{cells}</tr></thead>'
            f"<tbody>{body}</tbody></table>")


def _circuit_tables(spec, section) -> str:
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
        # `_plain` 을 씌운다 — 옛 `_tables()` 는 안 씌웠다. 지금 어느 명세의
        # `source` 에도 마크다운이 없지만, 들어오는 순간 백틱이 인쇄본에 찍히고
        # 그것을 잡는 검사는 본문만 본다.
        out.append(f"<p class='src'>출처: {_esc(_plain(table.source or ''))}</p>")
        if table.kind == "capture":
            out.append(_capture_html(table, spec.path.parent))
        elif table.kind == "stepped":
            out.append(_stepped_html(table))
            out.append(f"<p class='readout'>{_esc(_INSTRUMENT)}</p>")
        else:
            out.append(_truth_table_html(table, token))
        photo = (_PHOTO_NO_TOKEN if table.kind == "truth-table" and not token
                 else _PHOTO[table.kind].format(tid=table.id, tok=token or "<항목>"))
        out.append(f"<p class='photo'>{_esc(photo)}</p>")
        out.append(_mismatch_html(table.kind, table.id))
        out.append("</div>")
    for table_id in section.refs:
        table = spec.table(table_id)
        if table is None:
            continue                  # validate 가 error 로 잡는다
        out.append('<div class="tblock">')
        out.append(f"<h3>{_esc(table.id)} · {_esc(table.title)} — 참조</h3>")
        out.append(f"<p class='src'>출처: {_esc(_plain(table.source or ''))}</p>")
        # 기록 칸·미니표·사진 지시를 붙이지 않는다. 교안·데이터시트에서 옮긴
        # 이론표라 실험실에서 채우는 물건이 아니다 — 옆 표(실험02 T7)가 대조할
        # 기준값일 뿐이다.
        out.append(_md_table_html(table))
        out.append("</div>")
    return "\n".join(out)


def circuit_pages(spec, netlist) -> str:
    """회로마다 한 면. 강제 개쪽이라 회로 둘이 한 쪽을 나눠 쓰지 않는다.
    강의노트 회로도는 한 항목을 가리키는 회로가 여럿이어도 첫 회로에만 싣는다.

    면 안의 순서는 작업 순서다 — 칩 교체 → 강의노트 회로도 → 유의사항 → 결선도
    → 배선 → 미사용핀 → 단계(단계 진리표) → 측정표. 유의사항(예: `74HC02 는 핀 순서에 주의`)을
    배선 앞으로 옮겼다 — 그것을 실행하며 봐야 할 배선 뒤에 두면 이미 다 꽂은 뒤에야 읽게 된다.
    단계는 완성본·배선 **뒤**다(2026-09-28) — 전체 모습을 먼저 보고 단계를 밟는다. 측정표는
    마지막 단계 바로 뒤라, 마지막 관측 단계는 자기 단계 진리표 대신 기록표를 본다.
    미사용핀 상자는 칩별로 낸다 — 회로 단위로 합치면 C4 처럼 같은 핀 번호가
    칩마다 정반대 지시를 받을 때 어느 칩 것인지 사라진다.
    """
    out, previous = [], None
    shown = set()                 # 강의노트 회로도를 이미 실은 항목
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
        banner = _chip_swap(previous, section)
        out.append(f'<div class="banner">{_esc(banner)}</div>')
        if item is not None and item.id not in shown:
            shown.add(item.id)
            schematic = _schematic_html(item, spec.path.parent)
            if schematic:         # 빈 문자열을 넣으면 필드 없는 주차의 HTML 에 빈 줄이 는다
                out.append(schematic)
        if prose_before.strip():
            out.append(_blocks(prose_before))
        out.append('<div class="wirebox">')
        if section.stages:
            out.append("<p class='src'><b>완성본 — 손그림 원도</b> (회색 없음)</p>")
        out.append(_diagram_html(section, netlist))
        # 옛 PNG 머리에 있던 제출 안내 — 그림에 글자를 굽지 않게 되어(2026-09-28) 여기로 온다.
        # 단계 유무와 상관없이 회로마다 한 번: 손그림은 완성본마다 한 장이다
        out.append("<p class='src submit'>손그림은 이 그림을 따라 그리고 학번·이름·날짜를 자필로 적는다</p>")
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
                       "<b>핀 점검 — 사용 핀은 다 물렸는가 · 미사용 핀은 지시대로인가 (칩마다 따로)</b>")
            for chip in unused_chips:
                out.append(f'<div class="chipunused"><b>{_esc(chip["head"])}</b><ul>')
                out += [f'<li><span class="box"></span>{_esc(u)}</li>'
                        for u in chip["unused"]]
                out.append("</ul></div>")
            out.append("</div>")
        if prose_after.strip():
            # 배선을 마친 뒤 하는 검산이다. 앞으로 올리면 preamble 로 읽힌다.
            out.append(_blocks(prose_after))
        # 마지막 관측 단계는 단계 진리표를 싣지 않는다 — 바로 뒤 기록표가 그 표다. 단 그 노드가
        # 기록표 출력 열일 때만이다 — 중간 노드면 기록표에 그 값이 없다.
        observed = [s for s in section.stages if s.get("node")]
        last = observed[-1] if observed else None
        if last is not None and last["node"] not in _record_outputs(spec, section):
            last = None
        for stage in section.stages:
            out.append(_stage_html(stage, netlist, section, spec, last=stage is last))
        out.append(_circuit_tables(spec, section))
        unstaged = _unstaged_nodes_html(spec, section)
        if unstaged:              # 빈 문자열을 넣으면 노드 없는 주차의 HTML 에 빈 줄이 는다
            out.append(unstaged)
        out.append("</section>")
        previous = section
    return _drop_issue_refs("\n".join(out))


CLOSING = (
    "표마다 확인 칸이 다 찼는가 — 사진만 찍었으면 시험한 행마다 사진이 있는가 "
    "(진행하지 않은 표에는 진행하지 않았음 을 적는다)",
    "표마다 사진 지시대로 찍었는가 — 진리표는 시험한 행마다(불일치 행 필수), "
    "스텝표는 스텝마다, 파형은 화면마다",
    "사진 파일명이 표에 인쇄된 이름 그대로인가 (실험 번호 접두어 없이)",
    "공통면의 실험실 확인 목록을 다 처리했는가",
    "조교에게 물어볼 것을 다 물었는가",
    "종료 메모 거리(막힌 것·예상과 다른 것·해결·새로 안 것)를 적어 두었는가 — 실험 폴더에 .md 로 둔 자유 메모 파일도 된다",
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
