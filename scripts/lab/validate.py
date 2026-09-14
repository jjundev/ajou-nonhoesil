"""명세·결선도·보고서 검증. 예외를 던지지 않고 `Finding` 목록을 돌려준다.

⑤ `review-lab-report` 스킬이 이 모듈을 부른다. 검토는 반쯤 망가진 문서에도
동작해야 하므로, 여기서는 절대 예외로 중단하지 않는다.
"""

import re
import subprocess
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from . import config, md
from .boolexpr import eval_boolean
from .notation import DONT_CARE, normalize_cell
from .render import _chip_boxes, _chip_tables, _circuit_body
from .spec_parser import (ENCODINGS, ROLES, column_label, derived_parts,
                          split_columns, split_indices)

_BAD_CELL = {"\\|": "escape 된 파이프", "<br>": "<br> 태그", "\t": "탭 문자"}

# 관측 결과에 **방향을 붙이는** 문장. "~하면 ~를 의심한다", "~보다 크게
# 나오면 ~다". 교안에 원본이 없어 대조할 곳이 없고, 방향이 거꾸로여도
# 문법·서식 검사는 전부 통과하며 읽는 사람에게는 오히려 친절해 보인다.
# 실험02 명세가 이 형태로 두 번 거꾸로였고 둘 다 제출본까지 갔다.
#
# 실측으로 폭을 맞췄다 — 살아 있는 문서 10개에 33건, 최대 9건. 넓히면
# 목록이 못 읽을 만큼 길어지고, 좁히면(`나온다` 를 빼면) 실험02 의 원래
# 오문 하나가 빠진다.
_DIAGNOSTIC = re.compile(r"의심|나오면|나온다|보이면|어긋나면|빠뜨리면")

_MARKS = {"error": "✗", "warn": "!", "info": "ℹ"}

# 칩 상자 밖에서 배선·미사용핀 지시처럼 보이는 줄. 상자 밖으로 새면 체크박스도
# 칩 라벨도 없이 `- ` 마커째 인쇄된다 — check_netlist_circuits 가 이 정규식으로
# 렌더러의 상자 경계 버그와 무관하게 시끄럽게 만든다.
_STRAY_WIRE = re.compile(r"^\s*-\s*(pin|미사용)")


@dataclass
class Finding:
    level: str   # "error" | "warn" | "info"
    where: str
    message: str

    def __str__(self):
        return f"{_MARKS.get(self.level, '!')} {self.where} — {self.message}"


def _bit(cell, encoding):
    """평가용 비트로 읽는다. **데이터를 바꾸지 않는다** — 검산 중에만 쓴다."""
    c = normalize_cell(cell)
    if encoding == "H/L":
        return {"L": 0, "H": 1}.get(c)
    return {"0": 0, "1": 1}.get(c)


def check_table_integrity(spec) -> list:
    out = []
    for t in spec.tables:
        width = len(t.header)
        for i, row in enumerate(t.rows, start=1):
            where = f"{spec.path.name}:{t.id} 행{i}"
            if len(row) != width:
                out.append(Finding("error", where,
                    f"셀이 {len(row)}개인데 헤더는 {width}개다"))
            for cell in row:
                for bad, label in _BAD_CELL.items():
                    if bad in cell:
                        out.append(Finding("error", where, f"셀에 {label}가 있다: {cell!r}"))
    return out


def check_metadata(spec) -> list:
    out = []
    for t in spec.tables:
        where = f"{spec.path.name}:{t.id}"
        if not t.source:
            out.append(Finding("error", where, "source 가 없다 (예상값 출처는 항상 명시한다)"))
        if (t.source or "").strip().startswith("derived") and not derived_parts(t):
            # 형식이 깨지면 derived_parts 가 빈 리스트를 주는데, 그건 "derived 가
            # 아님" 과 구별되지 않는다. split_columns 가 조용히 잘못된 입출력
            # 분할을 내놓으므로 여기서 잡아야 한다.
            out.append(Finding("error", where,
                f"source 가 derived 인데 식을 읽지 못했다: {t.source!r}. "
                "`derived (Y = 식)` 또는 `derived (X = 식 ; Y = 식)` 형태여야 한다"))
        if t.outputs is not None:
            # split_columns 는 헤더에 있는 이름만 쓰고 나머지를 조용히 버린다.
            missing = [c for c in t.outputs if c not in t.header]
            if missing:
                out.append(Finding("error", where,
                    f"outputs 가 헤더에 없는 열을 가리킨다: {missing}. "
                    f"헤더: {t.header}"))
            targets = [name for name, _ in derived_parts(t)]
            if targets and set(targets) != set(t.outputs):
                # 출력을 두 곳에 적으면 한쪽만 고쳐진다. split_columns 는
                # derived 식을 따르므로 outputs 쪽이 조용히 무시된다.
                out.append(Finding("error", where,
                    f"outputs {t.outputs} 가 derived 대입 대상 {targets} 와 "
                    "다르다. derived 표는 식이 출력을 정하므로 outputs 를 "
                    "지우거나 식에 맞춘다"))
        if t.role not in ROLES:
            out.append(Finding("error", where,
                f"role 이 {t.role!r} 이다. `record` 또는 `reference` 여야 한다"))
        if t.kind == "capture":
            if not t.expected:
                out.append(Finding("error", where,
                    "capture 표에 expected 산문이 없다 (예상값을 적을 곳이 여기다)"))
        elif t.encoding not in ENCODINGS:
            out.append(Finding("error", where,
                f"encoding 이 {t.encoding!r} 이다. `0/1` 또는 `H/L` 을 선언해야 한다"))
    return out


def check_row_count(spec) -> list:
    """진리표 행 수 ↔ 입력 비트 수. `X` 가 있으면 축약된 표이므로 건너뛴다."""
    out = []
    for t in spec.tables:
        if t.kind != "truth-table" or not t.rows:
            continue
        if any(normalize_cell(c) == DONT_CARE for row in t.rows for c in row):
            continue
        inputs, _ = split_columns(t)
        if not inputs:
            continue
        expected = 2 ** len(inputs)
        if len(t.rows) != expected:
            out.append(Finding("warn", f"{spec.path.name}:{t.id}",
                f"입력 {len(inputs)}비트({', '.join(inputs)})면 {expected}행이어야 하는데 "
                f"{len(t.rows)}행이다"))
    return out


def check_boolean(spec) -> list:
    """`derived (...)` 로 선언된 표를 식으로 되짚는다. 출력이 여럿이면 전부."""
    out = []
    for t in spec.tables:
        pairs = derived_parts(t)
        if not pairs or not t.rows:
            continue
        where = f"{spec.path.name}:{t.id}"
        inputs, _ = split_indices(t)
        # 입력 열을 나중에 채운다 — 출력이 입력과 같은 글자면(실험3 반감산기
        # `A B D B`) 출력 값이 식의 입력 자리를 덮으면 안 된다.
        order = [k for k in range(len(t.header)) if k not in inputs] + inputs
        for target, expr in pairs:
            if target not in t.header:
                out.append(Finding("error", where,
                    f"source 의 출력 {target!r} 이 표 헤더에 없다: {t.header}"))
                continue
            # 같은 글자가 입력에도 있으면 뒤의 것이 출력이다(split_indices).
            out_col = max(k for k, c in enumerate(t.header) if c == target)
            label = column_label(t.header, out_col)
            seen_eval_errors = set()
            for i, row in enumerate(t.rows, start=1):
                if len(row) != len(t.header):
                    continue
                env, dont_care, bad_cells = {}, False, []
                for k in order:
                    col, cell = t.header[k], row[k]
                    bit = _bit(cell, t.encoding)
                    if bit is not None:
                        env[col] = bit
                    elif k in inputs and normalize_cell(cell) == DONT_CARE:
                        env.pop(col, None)
                        dont_care = True
                    elif k in inputs:
                        env.pop(col, None)
                        bad_cells.append(f"{col}={cell!r}")
                if dont_care:
                    # 입력이 don't-care 인 행은 구체적 식으로 검산할 수 없다.
                    # 행 수 검사가 X 있는 표를 건너뛰는 것과 같은 이유다.
                    continue
                got = _bit(row[out_col], t.encoding)
                if got is None:
                    continue
                try:
                    want = eval_boolean(expr, env)
                except ValueError as exc:
                    # 셀 하나가 해독 불가라고 표 전체(나머지 행)를 포기하지
                    # 않는다 — 이 행만 건너뛰고 검산을 계속한다. 같은 열이
                    # 통째로 깨지면 모든 행에서 같은 메시지가 반복되므로,
                    # 한 표에서 처음 한 번만 보고한다.
                    sig = str(exc)
                    if sig not in seen_eval_errors:
                        seen_eval_errors.add(sig)
                        cells = ", ".join(bad_cells) or "(식이 참조하지 않는 열)"
                        out.append(Finding("error", f"{where} 행{i}",
                            f"{label} 의 식 {expr!r} 을 평가할 수 없다: {exc} "
                            f"— 해독 못 한 셀: {cells}"))
                    continue
                if got != want:
                    shown = ", ".join(f"{column_label(t.header, k)}={row[k]}"
                                      for k in inputs)
                    out.append(Finding("error", f"{where} 행{i}",
                        f"{shown} 일 때 {label} = {expr} = {want} 인데 "
                        f"표에는 {row[out_col]!r} 이다"))
    return out


def check_column_roles(spec) -> list:
    """같은 열 이름이 **입력과 출력으로 갈리는지** 본다. 두 층이 있다.

    - **표 사이** — 실험01 이 실물이다. `C` 가 T1~T4 에서는 세 번째 입력이고
      T6~T9 에서는 출력이다. 교안 p5·p6·p8·p9 가 `INPUT(A, B) / OUTPUT(C)` 2단
      헤더로 갈라 놓은 것을 명세가 한 줄 헤더로 누르면서 구분이 사라졌다.
    - **한 표 안** — 실험3 반감산기 `A B D B`. 교안 p6 이 내림 수를 입력과 같은
      글자 `B` 로 적는다. 파서가 입력 하나·출력 하나로 갈리는 경우만 받고 뒤의
      것을 출력으로 본다(`split_indices`). 이 표들은 표 사이 층에서 빼고 따로
      알린다 — 같이 세면 "표마다 뜻이 다르다" 는 틀린 문장이 된다.

    **`info` 다 — 표를 고치라는 뜻이 아니다.** 교안이 그렇게 쓰면 `draft-lab-spec`
    §절대 규칙 5 가 열 이름을 원문 그대로 두라고 한다. 고칠 자리는 머리말의
    `| 토큰 | 뜻 | 근거 |` 표다. `error` 로 올리면 교안 표기를 바꾸게 되어 그 규칙과
    정면으로 부딪힌다.
    """
    roles, within = {}, {}
    for t in spec.tables:
        ins, outs = split_columns(t)
        for name in dict.fromkeys(n for n in ins if n in outs):
            within.setdefault(name, []).append(t.id)
        for name in ins:
            roles.setdefault(name, {}).setdefault("입력", []).append(t.id)
        for name in outs:
            roles.setdefault(name, {}).setdefault("출력", []).append(t.id)
    out = []
    for name, ids in within.items():
        out.append(Finding(
            "info", f"{spec.path.name}:{name}",
            f"열 `{name}` 이 한 표 안에서 입력이자 출력이다 ({'·'.join(ids)}) — 뒤의 "
            f"`{name}` 이 출력이다. 머리말 `| 토큰 | 뜻 | 근거 |` 표에 두 열의 뜻을 "
            f"밝혔는지 본다(`draft-lab-spec` §절대 규칙 5)"))
    for name, seen in roles.items():
        skip = set(within.get(name, []))
        seen = {role: [i for i in ids if i not in skip] for role, ids in seen.items()}
        seen = {role: ids for role, ids in seen.items() if ids}
        if len(seen) < 2:
            continue
        where = " / ".join(f"{role} {'·'.join(ids)}" for role, ids in seen.items())
        out.append(Finding(
            "info", f"{spec.path.name}:{name}",
            f"열 `{name}` 이 표마다 뜻이 다르다 ({where}). 표를 고치지 말고 "
            f"머리말 `| 토큰 | 뜻 | 근거 |` 표에 밝혔는지 본다 — 교안 표기가 "
            f"그렇다면 그대로 두는 것이 맞다(`draft-lab-spec` §절대 규칙 5)"))
    return out


def check_orphan_tables(spec) -> list:
    """본문에 있으나 어느 항목도 가리키지 않는 표.

    파서는 반대 방향(없는 표를 가리키는 항목)만 막는다. 고아 표는 구조적으로
    표현 가능하므로 여기서 잡는다 — 대개 항목의 `tables` 에 ID 를 빠뜨린 것이다.
    """
    referenced = {tid for item in spec.items for tid in item.tables}
    return [Finding("error", f"{spec.path.name}:{t.id}",
                    "어느 항목의 tables 도 이 표를 가리키지 않는다")
            for t in spec.tables if t.id not in referenced]


def check_diagnostic_claims(text, where) -> list:
    """방향을 붙인 문장을 `info` 로 **센다. 판정하지 않는다.**

    방향이 맞는지는 그 절차의 산술을 실제로 굴려 봐야 알 수 있고 그건 코드가
    못 한다. 여기서 하는 일은 "굴려 봐야 할 문장이 여기 N개 있다" 를 보이게
    만드는 것뿐이다 — 그래서 `error` 가 아니라 `info` 다. `error` 로 올리면
    방향이 맞는 문장까지 고치게 된다.
    """
    return [Finding("info", f"{where}:{i}",
                    f"방향을 붙인 문장이다 — 절차의 산술로 굴려 봤는가: "
                    f"{line.strip()[:60]}")
            for i, line in enumerate(text.split("\n"), start=1)
            if _DIAGNOSTIC.search(line)]


# 교안을 인용한다고 주장하는 줄. `교안`·`강의노트` 가 같은 줄에 없으면
# 자기 이전 판이나 데이터시트를 인용하는 것이라 검사 대상이 아니다.
_MANUAL_WORD = re.compile(r"교안|강의노트")
# 길이는 여기서 거르지 않는다 — 짧은 인용을 건너뛰면 그 닫는 따옴표가
# 다음 인용의 여는 따옴표로 붙어 엉뚱한 조각이 인용으로 잡힌다.
_QUOTE = re.compile(r"[\u201c\u201d\"]([^\u201c\u201d\"\n`]{1,80})[\u201c\u201d\"]")
_QUOTE_MIN = 4


def _squash(s: str) -> str:
    return re.sub(r"\s+", "", s)


_HANGUL = re.compile(r"[\uac00-\ud7a3]")


def _pdftotext_text(manual_path) -> str:
    """`pdftotext -layout` 의 표준 출력을 문자열로 돌려준다. 못 돌리면 빈 문자열."""
    try:
        done = subprocess.run(["pdftotext", "-layout", str(manual_path), "-"],
                              capture_output=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return ""
    if done.returncode != 0:
        return ""
    # `text=True` 로 받으면 안 된다 — pdftotext 가 글머리표(`0xb7`) 같은
    # 비 UTF-8 바이트를 섞어 내고, Windows 기본 인코딩(cp949)에서는 그것이
    # 읽기 스레드의 UnicodeDecodeError 가 되어 함수가 None 을 돌려줬다.
    return done.stdout.decode("utf-8", errors="replace")


def _pypdf_text(manual_path) -> str:
    """`pypdf` 로 쪽마다 텍스트를 뽑아 잇는다. 라이브러리가 없거나 못 열면 빈 문자열."""
    try:
        import pypdf
    except ImportError:
        return ""
    try:
        reader = pypdf.PdfReader(str(manual_path))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    except Exception:
        return ""


def extract_manual_text(manual_path) -> str:
    """교안 PDF 의 텍스트 층을 통째로 뽑는다. 못 뽑으면 빈 문자열이다.

    빈 문자열이면 `check_manual_quotes` 가 아무것도 내지 않는다 — `pdftotext`
    가 없는 환경에서 "교안에 그 문장이 없다" 로 오진하지 않기 위해서다.

    **항상 `str` 이다** — 어떤 경로로도 None 을 돌려주지 않는다. 호출자가
    `len()` 을 바로 걸기 때문이다.

    `pdftotext` 결과에 한글이 한 글자도 없는데 `pypdf` 결과에는 있으면 `pypdf`
    쪽을 덧붙인다. 실험2 교안이 실물이다 — 내장 NanumSquare 트루타입에
    한글 ToUnicode 가 없어 `pdftotext` 는 ASCII 만 내놓고, 그 결과 명세의
    한글 인용 12건이 전부 "교안에 없다" 로 오진됐다. `pypdf` 는 같은 파일에서
    한글을 제대로 되살린다. 둘 다 한글이 없으면 `pdftotext` 결과를 그대로
    쓴다(영문 교안이거나 래스터인 경우).
    """
    text = _pdftotext_text(manual_path)
    if _HANGUL.search(text):
        return text
    fallback = _pypdf_text(manual_path)
    if not _HANGUL.search(fallback):
        return text
    return f"{text}\n{fallback}" if text else fallback


def check_manual_quotes(text, manual_text, where) -> list:
    """교안을 인용한다고 **주장하는** 큰따옴표 문장이 그 교안에 실재하는지 본다.

    판본을 갈면서 산문만 옛 판에 남는 사고를 겨냥한다. 실험01 이 실물이다 —
    `source_manual` 이 2026-2 배포본으로 바뀐 뒤에도 아카이브 2020-2 판의
    `"OR gate에 대한 IC 찾아서 수행"` 이 산문에 남았고, 기존 검사기는
    전부 통과시켰다. `source_manual` 은 파서가 필드로만 보고 내용은 아무도
    안 읽었기 때문이다.

    **`info` 만 낸다 — `error` 로 올리면 안 된다.** 교안의 회로도·기호가
    래스터면 `pdftotext` 가 그 자리에서 0 자를 내놓으므로(§절대 규칙 3),
    "추출본에 없다" 가 "교안에 없다" 를 뜻하지 않는다. 이 검사가 하는 일은
    "교안을 다시 펴서 이 줄을 확인하라" 를 보이게 만드는 것뿐이다.
    """
    if not _squash(manual_text or ""):
        return []
    hay = _squash(manual_text)
    out = []
    for i, line in enumerate(text.split("\n"), start=1):
        if not _MANUAL_WORD.search(line):
            continue
        for m in _QUOTE.finditer(line):
            quoted = m.group(1).strip()
            if len(_squash(quoted)) < _QUOTE_MIN:
                continue
            if _squash(quoted) not in hay:
                out.append(Finding(
                    "info", f"{where}:{i}",
                    f"교안 인용인데 `source_manual` 텍스트 추출본에 그 문자열이 "
                    f"없다 — 판본이 바뀐 자리인지 본다(래스터면 오탐이다): "
                    f"\u201c{quoted}\u201d"))
    return out


# 강의노트 텍스트에서 신호 이름을 뽑는 토큰. `spec_parser._NAME`(부울식 변수)과
# 같은 규칙이라 `L1과` 는 `L1` 로, `INPUT(A, B, C)` 는 `INPUT`·`A`·`B`·`C` 로 읽힌다.
# 수식 이탤릭(𝐴)과 숫자로 시작하는 셀 값(`0`)은 토큰이 아니다.
_LATIN_TOKEN = re.compile(r"[A-Za-z][A-Za-z0-9_]*")
_MANUAL_PAGE = re.compile(r"manual:p(\d+)")


def extract_manual_pages(manual_path) -> list:
    """강의노트 PDF 의 쪽별 텍스트. 1쪽이 `[0]` 이다. 못 열면 빈 리스트.

    `check_manual_names` 가 쪽 단위로 대조하려고 쓴다 — `extract_manual_text` 는 전
    쪽을 이어 붙여 어느 쪽에 있는지를 잃는다. pypdf 를 먼저 쓴다: 실험3 강의노트는
    `pdftotext` 가 한글을 떨어뜨린다(Symbol 폰트). pypdf 가 빈 문자열을 준 쪽만
    `pdftotext -f N -l N` 으로 한 번 더 본다.
    """
    try:
        import pypdf
    except ImportError:
        return []
    try:
        reader = pypdf.PdfReader(str(manual_path))
        pages = [(page.extract_text() or "") for page in reader.pages]
    except Exception:
        return []
    for n, text in enumerate(pages, start=1):
        if text.strip():
            continue
        try:
            done = subprocess.run(["pdftotext", "-layout", "-f", str(n), "-l", str(n),
                                   str(manual_path), "-"], capture_output=True, timeout=60)
        except (OSError, subprocess.SubprocessError):
            continue
        if done.returncode == 0:
            pages[n - 1] = done.stdout.decode("utf-8", errors="replace")
    return pages


def _contains_run(tokens, run) -> bool:
    """`run` 이 `tokens` 안에 끊기지 않고 그 순서로 있는가."""
    n = len(run)
    return any(tokens[k:k + n] == run for k in range(len(tokens) - n + 1))


def check_manual_names(spec, pages) -> list:
    """명세 진리표의 열 이름이 **강의노트 그 쪽에** 그대로 있는지 본다.

    다른 이름 검사는 전부 명세를 기준으로 잰다 — 예보 표는 명세 머리와, 결선도
    배지는 빌더와. 명세가 강의노트와 어긋나면 하류가 전부 통과한다. 2026-09-14
    실험03 명세가 반감산기 내림 수 `B` 를 `Bo` 로 바꿨고, 명세·예보를 둘 다 `Bo` 로
    바꾼 사본은 warn 0건이었다. 조교는 회로도 출력 이름을 표에서 바꾼 예보를
    감점했다(2026-09 실험01, -1).

    - 교안 표를 옮긴 표(`source` 가 `manual:pN` 을 인용): 머리 토큰열이 인용 쪽 중
      하나의 토큰열 안에 **끊기지 않고 그 순서로** 있어야 한다. 순서와 같은 글자
      둘까지 본다(실험3 p6 `A B D B`).
    - 파생표(`derived`): 열 이름마다 그 표를 쓰는 항목의 `pages` 쪽 텍스트에 토큰으로
      있어야 한다. 이름이 회로도 꼬리표·절차 문장에 흩어져 있어서다(실험1 p11
      "L1과 L2에 330Ω 저항", "INPUT(A, B, C)").
    - 파생표를 쓰는 항목에 `pages` 가 없으면 error, 강의노트 쪽 수를 넘는 쪽은 error.
    - 텍스트 층이 없는 쪽(래스터)은 info — 대조를 못 했다는 뜻이지 틀렸다는 뜻이
      아니다(`check_manual_quotes` 와 같은 이유). `pages` 가 빈 리스트면(PDF 를 못
      엶) info 한 줄만 낸다.
    - 머리에 라틴 토큰이 아닌 열(한글 설명 열)이 있는 표는 info 로 알리고 건너뛴다.
    """
    name = spec.path.name
    if not pages:
        return [Finding("info", name,
            "강의노트 텍스트를 뽑지 못해 열 이름 대조를 건너뛴다 — vision 으로 본다")]
    tokens = [_LATIN_TOKEN.findall(p) for p in pages]
    out, noted = [], set()

    def readable(where, nums):
        """쓸 수 있는 쪽 번호만 돌려준다. 없는 쪽은 error, 텍스트 층이 없는 쪽은 info."""
        ok = []
        for n in nums:
            if not isinstance(n, int) or not 1 <= n <= len(pages):
                if (where, n) not in noted:
                    out.append(Finding("error", where,
                        f"교안 p{n} 은 없다 — 이 강의노트는 {len(pages)}쪽이다"))
            elif not tokens[n - 1]:
                if (where, n) not in noted:
                    out.append(Finding("info", where,
                        f"교안 p{n} 에 텍스트 층이 없다(래스터) — 열 이름은 vision 으로 "
                        "대조한다"))
            else:
                ok.append(n)
            noted.add((where, n))
        return ok

    def cite(nums):
        return "·".join(f"p{n}" for n in nums)

    for t in spec.tables:
        if t.kind != "truth-table" or not t.header:
            continue
        where = f"{name}:{t.id}"
        header = [_bare_cell(c) for c in t.header]
        if not all(_LATIN_TOKEN.fullmatch(c) for c in header):
            bad = [c for c in header if not _LATIN_TOKEN.fullmatch(c)]
            out.append(Finding("info", where,
                f"머리에 라틴 토큰이 아닌 열({', '.join(bad)})이 있어 강의노트 이름 대조를 "
                "건너뛴다 — vision 으로 본다"))
            continue
        cited = [int(n) for n in _MANUAL_PAGE.findall(t.source or "")]
        if cited:
            ok = readable(where, cited)
            if ok and not any(_contains_run(tokens[n - 1], header) for n in ok):
                out.append(Finding("error", where,
                    f"머리 `{' '.join(header)}` 가 교안 {cite(ok)} 에 이 순서로 없다 — "
                    "교안 표를 옮긴 표는 머리를 글자 그대로 둔다"
                    "(`draft-lab-spec` §절대 규칙 5)"))
            continue
        for item in spec.items:
            if t.id not in item.tables:
                continue
            iwhere = f"{name}:{item.id}"
            if not item.pages:
                if (iwhere, None) not in noted:
                    out.append(Finding("error", iwhere,
                        f"pages 가 없어 {t.id} 의 열 이름을 강의노트와 대조할 수 없다 — "
                        "회로도·절차가 있는 쪽을 `pages: [N]` 으로 적는다"))
                    noted.add((iwhere, None))
                continue
            ok = readable(iwhere, item.pages)
            if not ok:
                continue
            have = set().union(*(tokens[n - 1] for n in ok))
            for c in dict.fromkeys(header):
                if c not in have:
                    out.append(Finding("error", where,
                        f"열 `{c}` 가 교안 {cite(ok)} 에 없다 — 열 이름은 강의노트 "
                        "회로도·절차의 표기를 그대로 쓴다(`draft-lab-spec` §절대 규칙 5)"))
    return out


def validate_spec(spec) -> list:
    # 진단 문장 info 는 **맨 끝**에 붙인다 — 앞에 끼우면 `findings[0]` 이
    # error 라고 단언하는 검사들이 조용히 깨진다.
    return (check_table_integrity(spec) + check_metadata(spec)
            + check_row_count(spec) + check_boolean(spec)
            + check_orphan_tables(spec)
            + check_column_roles(spec)
            + check_diagnostic_claims(
                spec.path.read_text(encoding="utf-8"), spec.path.name))


def check_folder_convention(spec_path, spec) -> list:
    """명세가 놓인 폴더의 **이름과 위치** 가 `experiment` 필드와 맞는지 본다.

    폴더는 `<보고서>/<실험NN>/체크리스트/명세.md` 구조다. 리네임을 한 번 하고
    끝내면 다음 주차에 다시 어긋나므로, ⑤ 가 매 검토마다 이것을 부른다.

    **이름과 위치를 따로 본다.** 기대값은 `config.experiment_dir`(경로)이
    아니라 `config.experiment_folder_name`(이름)이다 — 조부모 폴더의 `.name`
    과 견주는 자리라 경로를 넣으면 옳게 놓인 명세까지 전부 error 가 된다.
    위치는 그 위 한 칸(`EXPERIMENT_BASE`)을 따로 확인한다. 이름만 보던 시절엔
    실험 폴더가 통째로 루트에서 `보고서/` 로 옮겨간 것을 이 검사가 못 봤다.
    """
    path = Path(spec_path).resolve()
    parents = path.parents
    if len(parents) < 3:
        return [Finding("error", str(spec_path),
                        "명세 경로가 "
                        f"`{config.EXPERIMENT_BASE}/<실험NN>/체크리스트/명세.md` "
                        "형태가 아니다")]
    actual = parents[1].name
    actual_base = parents[2].name
    try:
        expected = config.experiment_folder_name(spec.experiment)
    except (TypeError, ValueError) as e:
        # ⑤ 는 반쯤 망가진 문서에도 돌아야 한다. 여기서 죽으면 검토가 멈춘다.
        return [Finding("error", actual,
                        f"명세의 experiment 값을 폴더 이름으로 바꿀 수 없다: {e}")]
    out = []
    if actual != expected:
        out.append(Finding("error", actual,
            f"폴더 이름이 `{actual}` 인데 명세의 `experiment: {spec.experiment}` 는 "
            f"`{expected}` 를 요구한다 — 둘 중 하나가 틀렸다"))
    # 이름이 틀렸어도 위치는 마저 본다. 한 번에 하나씩만 알려주면 고친 뒤
    # 다시 돌려야 나머지가 드러난다.
    if actual_base != config.EXPERIMENT_BASE:
        out.append(Finding("error", f"{actual_base}/{actual}",
            f"실험 폴더가 `{actual_base}/` 아래에 있다 — "
            f"`{config.EXPERIMENT_BASE}/{actual}` 이어야 한다"))
    return out


def check_netlist(netlist_path, spec) -> list:
    """플로팅 입력은 이 과목의 대표 실패 원인이다. 누락을 error 로 잡는다."""
    path = Path(netlist_path)
    if not path.exists():
        return [Finding("error", str(netlist_path), "결선도 netlist 파일이 없다")]
    text = path.read_text(encoding="utf-8")
    out = []
    for token, label in (("VCC", "VCC 연결"), ("GND", "GND 연결"),
                         ("미사용", "미사용 입력핀 처리")):
        if token not in text:
            out.append(Finding("error", path.name, f"{label} 언급이 통째로 없다"))
    for item in spec.items:
        for ic in item.ics:
            if ic not in text:
                out.append(Finding("warn", path.name,
                    f"항목 {item.id} 의 IC {ic} 가 netlist 에 없다"))
    # 결선도 쪽이 명세보다 진단 문장이 많다 (실험10: 9 대 1). 명세만
    # 검사하면 절반을 놓친다. **끝에** 붙인다 — 파일 부재 error 는 위에서
    # 이미 돌아갔고, 여기 info 가 앞에 끼면 `findings[0]` 단언이 깨진다.
    out += check_diagnostic_claims(text, path.name)
    return out


def check_netlist_circuits(netlist, spec) -> list:
    """회로 메타의 **의미** 결함. 구조 결함은 `netlist_parser` 가 예외로 던진다.

    `check_netlist` 는 건드리지 않는다 — 다섯 스킬이 그것을 부르고, 회로 메타를
    요구하는 것은 인쇄본을 내는 ① `prep-lab-checklist` 뿐이다. 요구를 필요한
    자리에만 둔다. 그것에 요구를 넣으면 아직 백필하지 않은 다섯 주차에서
    ③④⑤⑧ 이 동시에 멈춘다.

    결선도 부재는 **warn 이지 error 가 아니다.** 그림 없이도 배선 목록과 빈
    브레드보드로 실험은 된다. 다만 조용히 빈칸으로 나가면 인쇄 후에야 눈으로
    발견하므로 시끄럽게 알린다.
    """
    out = []
    layouts = netlist.of_kind("layout")
    if len(layouts) > 1:
        out.append(Finding("error", netlist.path.name,
            f"kind: layout 절이 {len(layouts)}개다 — 칩 자리표는 실험당 하나다. "
            "자리가 둘이면 어느 그림이 어느 자리인지 갈린다"))
    known_items = {i.id for i in spec.items}
    known_tables = {t.id for t in spec.tables}
    covered = set()

    for circuit in netlist.circuits:
        where = f"{netlist.path.name}:{circuit.id}"
        if circuit.item not in known_items:
            out.append(Finding("error", where,
                f"item {circuit.item!r} 이 명세에 없다. "
                f"정의된 항목: {sorted(known_items)}"))
        for table_id in circuit.tables:
            if table_id not in known_tables:
                out.append(Finding("error", where,
                    f"없는 표 {table_id} 를 가리킨다. "
                    f"정의된 표: {sorted(known_tables)}"))
            elif spec.table(table_id).role == "reference":
                # 렌더러도 걸러내지만, 그쪽 필터는 netlist 가 참조표를 말하지
                # 않는 한 발화하지 않아 회귀를 못 잡는다. 여기서 저작 단계에
                # 막는다 — 교안 이론표는 실험실에서 채우는 물건이 아니다.
                out.append(Finding("error", where,
                    f"{table_id} 는 role: reference 표다 — 교안에서 옮긴 이론표라 "
                    "실험실에서 채우지 않는다. 회로의 tables 에서 뺀다 "
                    "(예비보고서 이론 절의 재료다)"))
            else:
                covered.add(table_id)
        for st in circuit.stages:
            if not st["check"]:
                out.append(Finding("error", where,
                    f"단계 {st['n']} 의 확인 칸이 비었다 — 단계 끝에서 무엇을 보는지가 "
                    "이 표의 존재 이유다. 관측할 LED 와 입력 조합을 적는다"))
            if st["diagram"] and not (netlist.path.parent / st["diagram"]).exists():
                out.append(Finding("warn", where,
                    f"단계 {st['n']} 그림 파일이 없다: {st['diagram']}. "
                    "breadboard-diagram 의 e1_all 같은 일괄 렌더로 만든다"))
        if circuit.stages and circuit.diagram and circuit.stages[-1]["diagram"] == circuit.diagram:
            out.append(Finding("error", where,
                f"완성본(diagram = {circuit.diagram})과 마지막 단계 그림이 같은 파일이다. "
                "단계 그림은 회색 기준선을 담아 손그림 원도로 쓸 수 없다 — "
                "완성본은 기준선 없이 따로 낸다 (E1_FINALS)"))
        if circuit.continues:
            if circuit.continues == circuit.id:
                out.append(Finding("error", where,
                    "continues 가 자기 자신을 가리킨다. 이어 붙일 **앞** 회로의 "
                    "ID 를 적는다 — 배너가 '그대로 두라'고 지시하는 대상이다"))
            else:
                known_circuits = {c.id for c in netlist.circuits} - {circuit.id}
                if circuit.continues not in known_circuits:
                    out.append(Finding("error", where,
                        f"continues 가 {circuit.continues!r} 를 가리키는데 그런 회로가 "
                        f"없다. 정의된 회로: {sorted(known_circuits)}. 배너가 "
                        "'뜯지 말라'고 지시하는 대상이라 없는 회로를 가리키면 "
                        "실험실에서 무엇을 남겨야 할지 알 수 없다"))
                else:
                    order = [c.id for c in netlist.circuits]
                    at = order.index(circuit.id)
                    previous = order[at - 1] if at else None
                    if circuit.continues != previous:
                        out.append(Finding("error", where,
                            f"continues 가 {circuit.continues!r} 를 가리키는데 "
                            f"직전 회로는 {previous!r} 다. 이어 붙이기는 **바로 앞** "
                            "회로만 가능하다 — 배너가 '점퍼선을 걷지 않는다'고 "
                            "말하는 순간 그 사이 회로들의 점퍼를 어떻게 하라는 "
                            "지시가 사라진다"))
        for table_id in circuit.refs:
            if table_id not in known_tables:
                out.append(Finding("error", where,
                    f"refs 가 없는 표 {table_id} 를 가리킨다. "
                    f"정의된 표: {sorted(known_tables)}"))
            elif spec.table(table_id).role != "reference":
                out.append(Finding("error", where,
                    f"refs 가 {table_id} 를 가리키는데 그것은 기록 대상 표다 — "
                    "방향이 반대다. 실험실에서 채우는 표는 tables 로 간다. "
                    "refs 는 role: reference 표를 회로 페이지에 읽기 전용으로 "
                    "싣는 자리다 (실험02 T7 이 대조하는 T8 같은 것)"))
        if not circuit.diagram:
            out.append(Finding("warn", where,
                "diagram 이 없다 — 인쇄본에 빈 브레드보드가 대신 들어간다. "
                "breadboard-diagram 스킬로 결선도를 먼저 렌더한다"))
        elif not (netlist.path.parent / circuit.diagram).exists():
            out.append(Finding("warn", where,
                f"diagram 파일이 없다: {circuit.diagram}. breadboard-diagram "
                "스킬로 렌더하거나 diagram 줄을 지운다"))

    # 조용한 손실을 시끄럽게 만드는 것이 이 계약의 존재 이유다. 옛 판정은
    # "본문에 표 줄이 있다" 였는데, 렌더러가 표를 싣게 되면서 그 경고가
    # 거짓이 됐다. 지금 조용히 사라질 수 있는 것은 배선 그 자체다 — 칩
    # 선언이 아예 없거나(실험10 처럼 표만 있는 경우), 칩 상자에 배선 행이
    # 하나도 안 잡히는 경우(형식을 섞어 쓴 경우)다.
    for circuit in netlist.circuits:
        where = f"{netlist.path.name}:{circuit.id}"
        nodes, before, after = _circuit_body(circuit)
        chips = _chip_boxes(nodes)
        if not chips:
            out.append(Finding("warn", where,
                "칩 선언이 하나도 없다 — 배선이 인쇄본에 실리지 않는다. "
                "`- U<n> = <칩>` 불릿(아래에 들여쓴 `- ` 배선) 또는 "
                "`## U<n> = <칩>` 헤딩(아래에 배선 표) 중 하나로 적는다"))
            continue
        for chip in chips:
            if not chip["wires"] and not _chip_tables(chip):
                out.append(Finding("warn", where,
                    f"칩 {chip['head']!r} 에 배선이 하나도 없다 — 상자가 제목만 "
                    "남는다. 불릿형이면 들여쓴 `- ` 배선을, 헤딩형이면 배선 표를 "
                    "칩 아래에 둔다"))
        # 배선이 한 줄이라도 남으면 칩당 warn 은 울리지 않는다 — 조용한 손실을
        # 시끄럽게 만든다는 이 계약의 존재 이유가 거기서는 뚫린다. 렌더러가
        # 무엇을 하든(상자 경계 버그가 다시 생기든) 배선처럼 생긴 줄이 상자
        # **밖**에 있으면 그 자체로 시끄럽게 만든다.
        stray = [line.strip() for line in (before + "\n" + after).split("\n")
                 if _STRAY_WIRE.match(line)]
        if stray:
            out.append(Finding("warn", where,
                f"배선처럼 보이는 줄 {len(stray)}개가 칩 상자 **밖**에 있다: "
                f"{stray[:3]}. 체크박스도 칩 라벨도 없이 인쇄되고, 미사용핀이면 "
                "칩별 확인 상자에 안 들어간다. 칩 선언 아래로 옮긴다"))

    for table_id in sorted({t.id for t in spec.tables if t.role != "reference"}
                           - covered):
        out.append(Finding("warn", netlist.path.name,
            f"기록 대상 표 {table_id} 를 가리키는 회로가 없다 — "
            "인쇄본은 회로를 통해서만 표를 싣는다. 그대로 두면 조용히 빠진다"))
    return out


_STRAY_MARKDOWN = (("`", "백틱"), ("**", "굵게 표기"))
_TAG = re.compile(r"<[^>]+>")

# 화면·인쇄에 아무것도 찍지 않는 영역. 검사 전에 통째로 들어낸다 — CSS 주석에
# `position: fixed` 처럼 백틱을 쓰는 건 자연스러운 저작이고, 실제로 프리뷰
# 템플릿에서 두 번 반복됐다. 이걸 잡으면 매번 오탐이 떠서 검사 자체를 못 믿게
# 된다. 잡아야 할 것은 표 셀에 남은 마크다운이지 주석 속 백틱이 아니다.
_NON_RENDERING = re.compile(
    r"<!--.*?-->"
    r"|<style\b[^>]*>.*?</style>"
    r"|<script\b[^>]*>.*?</script>",
    re.DOTALL | re.IGNORECASE,
)


def check_rendered_html(html_path) -> list:
    """렌더된 HTML 본문에 마크다운 표기가 남았는지 본다.

    보고서 본문은 사람(또는 에이전트)이 마크다운에서 HTML 로 옮기는데,
    산문의 코드 스팬만 `<code>` 로 바꾸고 **표 셀을 빠뜨리는** 실수가 실제로
    일어났다 — 제출본 표 대부분에 백틱이 그대로 찍혔다. 눈으로는 잘 안 보인다.

    `<style>`·`<script>`·HTML 주석은 렌더되지 않으므로 검사에서 뺀다.
    """
    path = Path(html_path)
    if not path.exists():
        return [Finding("error", str(html_path), "렌더된 HTML 파일이 없다")]
    text = _TAG.sub(" ", _NON_RENDERING.sub(" ", path.read_text(encoding="utf-8")))
    out = []
    for token, label in _STRAY_MARKDOWN:
        count = text.count(token)
        if count:
            out.append(Finding("error", path.name,
                f"본문에 {label}({token!r})가 {count}개 남았다 — "
                "마크다운을 HTML 로 옮길 때 표 셀을 빠뜨리면 인쇄본에 그대로 찍힌다"))
    return out


def check_embedded_images(html_path) -> list:
    """`<img src=...>` 이 실제로 가리키는 파일이 있는지 본다.

    상대 경로는 **HTML 이 놓인 위치** 기준으로 풀린다. 다른 디렉토리에서
    렌더하면 그림이 깨진 채 PDF 로 굳는데, 텍스트 추출로는 안 보인다 —
    실제로 예비보고서의 브레드보드 그림이 그렇게 깨진 채 커밋됐다.
    """
    path = Path(html_path)
    if not path.exists():
        return [Finding("error", str(html_path), "렌더된 HTML 파일이 없다")]
    out = []
    for src in re.findall(r'<img[^>]+src="([^"]+)"', path.read_text(encoding="utf-8")):
        if src.startswith(("http://", "https://", "data:")):
            continue
        if not (path.parent / src).resolve().exists():
            out.append(Finding("error", path.name,
                f"이미지를 찾을 수 없다: {src!r} "
                f"(HTML 위치 {path.parent} 기준으로 푼다)"))
    return out


# NFM(Notion-flavored Markdown) 이 손실시키는 문법들. 실측 근거는
# docs/plans/2026-08-29-notion-probe-결과.md 에 있다.
# NFM 이 **입력으로도** 받는 자체 블록 태그. 원시 HTML 이 아니라 노션의 문법이다 —
# 목차 블록과 여백 블록은 학생이 노션에서 잡은 레이아웃을 소스 md 에 되돌려 넣기
# 위해 필요하고, 이것들까지 "원시 HTML" 로 잡으면 그 레이아웃을 올릴 수 없다.
# 입력 수용 여부는 실측했다 (docs/plans/2026-08-29-notion-probe-결과.md).
# 긴 이름을 먼저 둔다 — `table` 이 앞에 오면 `table_of_contents` 가 가려진다.
_NFM_BLOCK_TAGS = ("table_of_contents", "empty-block", "table", "tr", "td", "th",
                   "toggle", "callout", "columns", "column", "span")
_NFM_TAG_ALT = "|".join(_NFM_BLOCK_TAGS)

_NFM_LOSSY = (
    (re.compile(r"^#{5,}\s", re.M), "h5·h6 헤딩", "노션이 h4 로 강등한다"),
    (re.compile(r"^\[\^[^\]]+\]:", re.M), "각주 정의", "NFM 이 지원하지 않는다"),
    # 각주 정의 줄 안의 `[^n]` 을 참조로 이중 계수하지 않기 위해 `:` 로 끝나는
    # 형태(정의)는 제외한다 — 정의는 위 패턴이 이미 센다.
    (re.compile(r"(?<!\!)\[\^[^\]]+\](?!:)"), "각주 참조", "NFM 이 지원하지 않는다"),
    (re.compile(rf"^<(?!/?(?:{_NFM_TAG_ALT})\b)[a-zA-Z][^>]*>", re.M),
     "열 0 의 원시 HTML 블록", "NFM 은 일부 태그만 받는다"),
)
_IMAGE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")

# 대상이 비어도 잡고 alt 도 함께 뽑는다. `_IMAGE` 는 `[^)]+` 라 빈 링크를
# 아예 못 잡는다 — 그 함수가 세는 것이 "넣어야 할 그림" 이기 때문이다.
_IMAGE_ANY = re.compile(r"!\[([^\]]*)\]\(([^)]*)\)")

# 노션 왕복은 파이프 표를 HTML `<table>` 로 바꿔 돌려준다 — 실측 근거는
# docs/plans/2026-08-29-notion-probe-결과.md. `md.parse_tables()` 는 파이프 표만
# 인식하므로, 되읽은 문서의 표를 `markdown_shape` 가 이 패턴으로도 세지 않으면
# 왕복마다 "표가 통째로 사라졌다"는 거짓 경보가 뜬다. 속성 순서·공백·대소문자에
# 흔들리지 않게 느슨히 잡는다.
_HTML_TABLE = re.compile(r"<table\b([^>]*)>(.*?)</table>", re.IGNORECASE | re.DOTALL)
_HTML_TABLE_HEADER_ROW = re.compile(r"\bheader-row\s*=\s*[\"']true[\"']", re.IGNORECASE)
_HTML_TR = re.compile(r"<tr\b", re.IGNORECASE)


def check_pulled_images(pulled_text) -> list:
    """되읽은 본문에서 **아직 안 끼운 그림**을 잡는다.

    올릴 때 상대경로 이미지는 노션에서 반드시 깨진다 — 그래서
    `check_notion_markdown` 이 올리기 **전에** "몇 장 넣어야 한다" 를 info 로
    알린다. 그런데 사용자가 실제로 넣었는지는 여태 아무도 확인하지 않았다.
    실험01 v7 에서 브레드보드 그림이 빈 링크로 올라갔고 왕복 검사는 조용했다 —
    `check_notion_roundtrip` 은 헤딩·표·인용 **개수**만 보므로 그림은 안 센다.

    **되읽기 쪽에만 건다.** 올린 직후에는 그림이 비어 있는 것이 정상이므로
    (사용자가 노션에서 끼우기로 한 설계다) push 에 걸면 매번 거짓 경보가 된다.
    """
    out = []
    for alt, target in _IMAGE_ANY.findall(pulled_text):
        if target.strip():
            continue
        out.append(Finding("error", "노션 그림",
            f"그림 '{alt}' 이 빈 링크다 — 노션에서 아직 끼우지 않았다. "
            "이대로 PDF 를 내보내면 그 자리가 빈 채로 제출된다"))
    return out


# 문단 흐름 밖에 있는 줄머리. 표·헤딩·펜스·인용·노션 태그는 줄바꿈이 의미다.
_FLOW_OUT = ("\t", "|", "#", "<", "```", ">")
# 번호 목록도 목록이다. 이것을 산문으로 보면 연달아 오는 단계가 통째로 잡힌다
# — ⑦ 14단계 재생성이 실제로 이 오탐에 걸려 불릿으로 우회했다.
_ORDERED = re.compile(r"^\d+\.\s")
# 그림은 블록이다. 앞 산문과 붙어 있어도 "문장이 토막 났다" 가 아니다.
_IMAGE_ONLY = re.compile(r"^!\[[^\]]*\]\([^)]*\)\s*$")


# 줄 전체가 URL 하나인가. 참고문헌 인용의 링크 줄을 알아보는 데 쓴다.
_BARE_URL = re.compile(r"^<?https?://\S+>?$")


def _flow_kind(line):
    """줄이 문단 흐름의 어디에 속하는지. 흐름 밖이면 `keep`."""
    if not line.strip():
        return "blank"
    if line.startswith(_FLOW_OUT) or _IMAGE_ONLY.match(line):
        return "keep"
    if line.startswith("  "):
        return "cont"
    if line.startswith(("- ", "* ")) or _ORDERED.match(line):
        return "bullet"
    return "prose"


def check_report_wrapping(md_text) -> list:
    """본문 문단이 여러 줄로 쪼개져 있는지 본다.

    **노션은 원본의 줄바꿈을 하나하나 그대로 렌더한다.** 그래서 76열에 맞춰
    감싼 본문은 노션에서 문장 중간이 토막 난 채 보이고, 그대로 PDF 로 나간다.
    실험02 초판이 그렇게 올라갔고 **사용자가 v2 를 고치려다 눈으로 찾았다** —
    그때까지 아무 검사도 이것을 안 봤다.

    76열 규칙은 `.claude/skills/*/SKILL.md` 에만 걸린다. 보고서 본문에는 걸리지
    않는데 ③ 이 그 경계를 말해 주지 않아서, 격리 생성이 관행을 산출물에까지
    옮겨 적용했다. 판단이 아니라 기계적 서식이라 규칙을 고치지 않으면 주차마다
    재발한다.

    **폭을 재지 않는다.** 신호는 구조다 — 제대로 쓴 보고서는 문단 하나가 줄
    하나라, 산문 줄 바로 뒤에 또 산문 줄이 오는 일이 없다. 실측: 실험01
    승인본 0곳, 감싸인 실험02 초판 160곳. 임계값이 필요 없을 만큼 갈린다.

    한 줄로 요약해서 낸다. 160곳이면 160줄을 뱉는 검사는 아무도 안 읽는다.

    **올리기 전 원본에만 쓴다. 되읽은 baseline 에는 쓰지 않는다.** 원본은 빈
    줄이 문단을 가르므로 산문이 연달아 오면 반드시 쪼개진 것이다. 그런데
    노션 되읽기는 문단 사이의 빈 줄을 지워서, 각자 완결된 문단이 나란히
    붙는다 — 실험01 의 승인본은 0곳인데 그 v7 되읽기는 10곳이 잡힌다.
    `check_notion_markdown` 이 부르는 자리가 곧 그 범위다(⑦ push 2단계,
    올릴 원본). 되읽기에 이 함수를 대는 것은 범위를 벗어난 것이다.
    """
    lines = md_text.splitlines()
    hits = []
    for i in range(len(lines) - 1):
        here, nxt = lines[i], lines[i + 1]
        kind, kind_next = _flow_kind(here), _flow_kind(nxt)
        joined = ((kind_next == "prose" and kind == "prose")
                  or (kind_next == "cont" and kind in ("bullet", "cont")))
        if not joined:
            continue
        # 콜론·마침표 뒤에 수식을 따로 놓은 것은 저자의 배치다. 잡으면 거짓 경보다.
        if nxt.strip().startswith("`") and here.rstrip().endswith((":", ".")):
            continue
        # 참고문헌의 URL 줄도 저자의 배치다. 데이터시트 인용은 서지 한 줄 +
        # 링크 한 줄이 관행이라, 실험01·02 승인본이 그 모양으로 올라갔는데도
        # 이 검사가 둘 다 error 로 잡았다. **URL 만 있는 줄**로 좁힌다 —
        # 감싸인 산문의 이어진 줄이 URL 하나로만 이뤄지는 일은 없으므로
        # 진짜 감싸기(실험02 초판 160곳)를 놓치지 않는다.
        if _BARE_URL.match(nxt.strip()):
            continue
        hits.append(i + 1)
    if not hits:
        return []
    return [Finding("error", "본문 줄바꿈",
        f"문단이 {len(hits)}곳에서 줄로 쪼개져 있다 (첫 자리 {hits[0]}행) — "
        "노션은 원본의 줄바꿈을 그대로 렌더해서 문장 중간이 토막 난 채 올라간다. "
        "76열 규칙은 스킬 문서에만 걸린다 — 보고서 문단은 한 줄로 쓴다")]


_HEADING = re.compile(r"(?m)^(#{1,6})\s+(.*)$")


def check_heading_backticks(md_text) -> list:
    """헤딩 텍스트 안의 코드 스팬을 잡는다.

    **노션 목차 블록이 헤딩 텍스트를 그대로 가져간다.** 그래서 헤딩에 백틱이
    있으면 목차에까지 코드 배경이 번진다. 라운드 1 에서 학생이 실험02 의
    헤딩 두 개에서 직접 백틱을 지웠고, 남은 두 개를 어떻게 볼지 물었더니
    **체계적**이라고 확인해 주었다(실험01 승인본에는 백틱 헤딩이 0개다).

    2026-09-12 부터는 본문의 백틱도 쓰지 않는다(③ §절대 규칙 11, ④ §절대
    규칙 8). 이 검사는 **헤딩 줄만** 본다(error) — 본문은 `check_body_style`
    이 warn 으로 본다(같은 날 결보 v5 회차에서 승격).
    """
    hits = [i for i, line in enumerate(md_text.splitlines(), 1)
            if _HEADING.match(line) and "`" in _HEADING.match(line).group(2)]
    if not hits:
        return []
    return [Finding("error", "헤딩 표기",
        f"헤딩 {len(hits)}개에 백틱이 있다 (첫 자리 {hits[0]}행) — 노션 목차 "
        "블록이 헤딩 텍스트를 그대로 가져가 목차에까지 코드 배경이 번진다. "
        "기호는 본문에서만 백틱으로 감싼다")]


# 본문 문체. 전부 2026-09-12 실험01 결보에서 사용자가 손으로 지운 것들이다 —
# v3 평가에서 백틱·em dash·"첫째", v5 되읽기에서 조사·단위 띄어쓰기.
# 라틴 문자·숫자·닫는 괄호·작은따옴표(보수 `'`) 바로 뒤에 공백 하나 + 조사 + 경계.
_STYLE_PARTICLE = re.compile(
    r"[A-Za-z0-9)\]'}] (은|는|이|가|을|를|의|와|과|로|으로|에|에서|도|만|부터|까지|뿐)"
    r"(?=[\s,.)]|$)")
_STYLE_UNIT = re.compile(r"\d (?:V|mA|μA|µA|Ω|kΩ|ns/V|ns|°C)(?![A-Za-z])")
_STYLE_FENCE = re.compile(r"^\s*```")
# `\b` 로 끊어야 `<table_of_contents/>`(문서 맨 앞 목차 블록) 를 표로 오인해
# 남은 본문 전체를 "표 안" 으로 잘못 넘기지 않는다 — 닫는 태그가 영영 안 와
# `in_html_table` 이 계속 True 로 눌어붙는다.
_HTML_TABLE_OPEN = re.compile(r"<table\b", re.IGNORECASE)
_HTML_TABLE_CLOSE = re.compile(r"</table\b", re.IGNORECASE)


def check_body_style(md_text) -> list:
    """본문 문체 다섯 갈래를 warn 으로 잡는다. 갈래마다 Finding 하나.

    참고문헌 절(`#` 헤딩에 `참고문헌`)과 표 줄(파이프 표, 노션이 되돌리는 HTML
    `<table>` 표 둘 다), 펜스 코드 블록은 보지 않는다 — 서지에는 `Rev. 9 — 2021`
    같은 em dash 와 영문·숫자가 정상이고, 표 셀은 `check_notion_markdown` 의
    몫이다(`report_compare` 의 0단계가 이 함수를 되읽은 HTML baseline 에도
    돌리므로, HTML 표 줄을 걸러내지 않으면 표 안의 `5 V`·`—` 같은 정상값이
    거짓 warn 이 된다). ③ §절대 규칙 21·④ §절대 규칙 18(붙여쓰기),
    ④ §절대 규칙 8(백틱·em dash·첫째) 의 기계 검사판이다. 폭은 실험01 결보
    v5 승인본에서 0건이 나오도록 맞췄다(`tests/test_lab_validate.py::BodyStyle`).
    """
    hits = {"백틱": [], "em dash": [], "첫째": [], "조사": [], "단위": []}
    in_refs, in_fence, in_html_table = False, False, False
    for n, line in enumerate(md_text.splitlines(), 1):
        if _STYLE_FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if _HTML_TABLE_OPEN.search(line):
            in_html_table = True
        if in_html_table:
            if _HTML_TABLE_CLOSE.search(line):
                in_html_table = False
            continue
        if line.startswith("#"):
            in_refs = "참고문헌" in line
        if in_refs or line.lstrip().startswith("|"):
            continue
        if "`" in line:
            hits["백틱"].append(n)
        if "—" in line:
            hits["em dash"].append(n)
        if "첫째" in line:
            hits["첫째"].append(n)
        if _STYLE_PARTICLE.search(line):
            hits["조사"].append(n)
        if _STYLE_UNIT.search(line):
            hits["단위"].append(n)
    why = {
        "백틱": "본문 백틱 코드 서식 — 노션에서 붉은 고정폭 배경으로 렌더된다 (④ §절대 규칙 8)",
        "em dash": "본문 em dash — 학생이 손으로 쓰지 않는 문장 부호다 (④ §절대 규칙 8)",
        "첫째": "\"첫째 … 둘째 …\" 열거 — 산문 두 문단으로 푼다 (④ §절대 규칙 8)",
        "조사": "숫자·영문 뒤 조사를 띄어 썼다 — `L1이`, `A=B=1에서` 처럼 붙인다 (④ §절대 규칙 18)",
        "단위": "숫자와 단위를 띄어 썼다 — `330Ω`, `9.4mA` 처럼 붙인다 (④ §절대 규칙 18)",
    }
    return [Finding("warn", "본문 문체", f"{why[k]}: {len(v)}곳 (첫 자리 {v[0]}행)")
            for k, v in hits.items() if v]


# A4 한 장에 들어가는 표의 최대 열 수. 실측값이지 유도값이 아니다 —
# 실험05 v1 을 노션에서 A4 PDF 로 내보내 세었다(11열 셋 온전, 13·14열 잘림).
NOTION_A4_MAX_COLUMNS = 11

_SEP_ROW = re.compile(r"^\|[\s:|-]*-{2,}[\s:|-]*\|?$")


def _split_row(line):
    """`| a | b |` → `['a', 'b']`. 앞뒤 들여쓰기와 바깥 파이프를 뗀다."""
    s = line.strip()
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s[1:].split("|")]


def check_table_width(md_text) -> list:
    """A4 한 장에서 오른쪽이 잘릴 표를 잡는다.

    **노션 PDF 내보내기는 넓은 표를 경고 없이 자른다.** 노션 화면에서는 가로
    스크롤로 전부 보이므로 눈으로는 드러나지 않고, 제출본에서만 열이 사라진다.
    실험05 v1 에서 실제로 났다 — `BCD to Decimal 예상 진리표`(14열)에서 `Y7`·
    `Y8`·`Y9` 가, `8X3 우선순위 인코더 예상 진리표`(13열)에서 `GS`·`EO` 가
    빠진 채로 PDF 가 나왔다. 하필 `GS`·`EO` 는 같은 보고서의 본문이 "두 신호가
    함께 갈라 준다"고 설명하는 대상이라, 근거만 사라지고 주장이 남았다.

    **한계 11열은 실측이다.** 같은 PDF 에서 11열 표 셋(`3X8 디코더 이론표`·
    `8X3 인코더 이론표`·`Excess-3 예상 진리표`)은 온전했다. 12열은 시험하지
    않았으므로 안전한 쪽으로 11 에서 끊는다.

    **구분선이 있어야 표로 센다.** 본문에 `A|B` 같은 파이프가 섞여도 구분선이
    없으면 표가 아니다. 들여쓴 표도 센다 — §절대 규칙 13 이 불릿 아래 표를
    탭으로 들여쓰라고 시키므로, 들여쓰기를 빼면 진리표 대부분을 놓친다.
    """
    out, lines = [], md_text.splitlines()
    for i, line in enumerate(lines):
        s = line.strip()
        if not s.startswith("|") or i + 1 >= len(lines):
            continue
        if not _SEP_ROW.match(lines[i + 1].strip()):
            continue                      # 구분선이 뒤따라야 헤더다
        header = _split_row(line)
        n = len(header)
        if n <= NOTION_A4_MAX_COLUMNS:
            continue
        cut = header[NOTION_A4_MAX_COLUMNS:]
        out.append(Finding("error", "표 너비",
            f"{i + 1}행의 표가 {n}열이라 A4 PDF 에서 오른쪽 {len(cut)}열이 "
            f"잘린다 — {', '.join(cut)}. 노션 화면에서는 가로 스크롤로 다 "
            f"보이므로 내보내기 전에는 드러나지 않는다. "
            f"{NOTION_A4_MAX_COLUMNS}열 이하로 나눈다"))
    return out


def check_notion_markdown(md_path) -> list:
    """노션에 올리기 전에 md 자체를 본다.

    보고서에서 HTML 을 안 만들게 되면서 `check_rendered_html` 이 보고서 경로에서
    호출되지 않는다. 이 함수가 그 자리를 대신한다 — 대상이 렌더된 HTML 에서 md 로
    바뀌었을 뿐, "조용히 망가지고 눈으로는 안 보이는 결함"을 잡는 목적은 같다.

    **상대경로 이미지는 error 가 아니라 info 다.** 노션 API 의 마크다운은 URL 만
    받으므로 상대경로는 반드시 깨지는데, 그건 결함이 아니라 설계다 — 사진은
    사용자가 노션에서 직접 끼워 넣기로 했다(자동 첨부는 파일 업로드 후 1시간 내
    블록 삽입 + 위치 수술이 필요해 v1 의 복잡도가 아니다). 그래서 "고쳐라"가 아니라
    "무엇을 몇 장 넣어야 하는지"를 알린다.
    """
    path = Path(md_path)
    if not path.exists():
        return [Finding("error", str(md_path), "보고서 md 파일이 없다")]
    _, body = md.split_frontmatter(path.read_text(encoding="utf-8"))
    out = []
    for pattern, label, why in _NFM_LOSSY:
        hits = pattern.findall(body)
        if hits:
            out.append(Finding("error", path.name,
                f"{label} 이 {len(hits)}개 있다 — {why}"))
    for t in md.parse_tables(body):
        width = len(t.header)
        for i, row in enumerate(t.rows, start=1):
            if len(row) != width:
                out.append(Finding("error", f"{path.name}:{t.line}",
                    f"표 {i}행의 셀이 {len(row)}개인데 헤더는 {width}개다 — "
                    "노션에서 표가 통째로 뭉개진다"))
    out.extend(check_report_wrapping(body))
    out.extend(check_heading_backticks(body))
    out.extend(check_table_width(body))
    local = [s for s in _IMAGE.findall(body)
             if not s.startswith(("http://", "https://", "data:"))]
    if local:
        out.append(Finding("info", path.name,
            f"노션에서 직접 넣어야 할 그림 {len(local)}장: " + ", ".join(local)))
    return out


@dataclass
class MarkdownShape:
    headings: list
    table_count: int
    table_rows: int
    quote_blocks: int


def markdown_shape(text) -> MarkdownShape:
    """구조 불변량만 뽑는다. **텍스트 동일성은 보지 않는다.**

    노션 왕복은 문단 병합·표 정렬 마커 소실 같은 노이즈를 반드시 만든다. 그걸
    결함으로 세면 진짜 손실(표가 통째로 사라짐, 절이 안 올라감)이 파묻힌다.

    인용은 **줄이 아니라 블록**으로 센다 — 여러 줄 인용이 한 줄로 합쳐지는 것은
    노이즈지 손실이 아닌데, 줄로 세면 매번 error 로 올라온다.

    표는 **파이프 표와 HTML `<table>` 을 함께** 센다 — 노션 되읽기가 파이프 표를
    HTML 로 바꿔 돌려주기 때문이다(`_HTML_TABLE` 주석 참고). 원본(파이프)과
    되읽기(HTML)를 같은 잣대로 세지 않으면 형태만 바뀐 표가 손실로 보인다.
    """
    _, body = md.split_frontmatter(text)
    lines = body.split("\n")
    tables = md.parse_tables(body)
    html_tables = list(_HTML_TABLE.finditer(body))
    html_table_rows = 0
    for m in html_tables:
        attrs, inner = m.group(1), m.group(2)
        tr_count = len(_HTML_TR.findall(inner))
        if _HTML_TABLE_HEADER_ROW.search(attrs):
            # MdTable.rows 는 헤더 행을 빼고 세므로, HTML 표의 헤더 <tr> 도
            # 여기서 빼야 두 형태의 행 수가 같은 기준으로 비교된다.
            tr_count = max(tr_count - 1, 0)
        html_table_rows += tr_count
    quote_blocks, in_quote = 0, False
    for line in lines:
        if line.startswith(">"):
            if not in_quote:
                quote_blocks += 1
            in_quote = True
        else:
            in_quote = False
    return MarkdownShape(
        headings=[re.sub(r"^#+\s*", "", ln).strip()
                  for ln in lines if ln.startswith("#")],
        table_count=len(tables) + len(html_tables),
        table_rows=sum(len(t.rows) for t in tables) + html_table_rows,
        quote_blocks=quote_blocks,
    )


def check_notion_roundtrip(source_text, pulled_text) -> list:
    """올린 md 와 되읽은 md 의 구조를 대조한다. **손실만 본다.**

    업로드 직후 되읽어 baseline 을 저장하는 이 왕복이 곧 업로드 검증이다 — 추가
    API 호출 없이. 텍스트가 아니라 헤딩·표 개수·표 행 수·인용 블록 수만 비교하는
    이유는 `markdown_shape` 와 같다: 노션이 만드는 노이즈(문단 병합, 표 정렬
    마커 소실)를 결함으로 세면 진짜 손실이 그 안에 파묻힌다.

    늘어난 것은 보고하지 않는다 — 사용자가 노션에서 절이나 표를 더한 것은 손실이
    아니라 이 루프가 원하는 바로 그 입력이다.
    """
    src, got = markdown_shape(source_text), markdown_shape(pulled_text)
    out = []
    # 집합 포함이 아니라 **다중집합 차**로 비교한다 — 같은 이름이 두 번 나오는데
    # 하나만 남았을 때, `in` 검사는 "이름이 존재하긴 한다"만 보고 손실을 놓친다.
    # 항목반복형 프리셋(`결선도`·`구성한 회로`·`실험 결과`·`고찰`을 항목마다
    # 반복)이 이 상황을 실제로 만든다.
    missing = list((Counter(src.headings) - Counter(got.headings)).elements())
    # 첫 헤딩은 노션이 페이지 제목으로 흡수하므로 되읽기에 없을 수 있다.
    # **정확히 한 번만** 면제한다 — 같은 이름이 여러 번 나오는 양식에서 나머지
    # 누락까지 덮어 주면, 이 함수의 존재 이유인 "절이 통째로 안 올라간 것"을
    # 놓친다.
    if src.headings and src.headings[0] in missing:
        missing.remove(src.headings[0])
    for name in missing:
        out.append(Finding("error", "노션 왕복",
            f"절 '{name}' 이 되읽기에 없다 — 노션에 올라가지 않았을 수 있다"))
    if got.table_count < src.table_count:
        out.append(Finding("error", "노션 왕복",
            f"표가 {src.table_count}개에서 {got.table_count}개로 줄었다"))
    if got.table_rows < src.table_rows:
        out.append(Finding("error", "노션 왕복",
            f"표 행이 {src.table_rows}개에서 {got.table_rows}개로 줄었다"))
    if got.quote_blocks < src.quote_blocks:
        out.append(Finding("error", "노션 왕복",
            f"인용 블록이 {src.quote_blocks}개에서 {got.quote_blocks}개로 줄었다 — "
            "이 보고서의 인용은 전부 `> 출처:` 근거 표기라 하나가 사라지면 "
            "근거가 사라진 것이다"))
    return out


def check_report_sections(report_path, sections, item_count=None) -> list:
    """`.claude/보고서양식.md` 기준으로 섹션 유무·순서를 본다.

    하드코딩된 목차와 대조하지 않는다 — 양식이 연도마다 다르기 때문이다 (R1).

    `item_count` 를 주면 `repeat: per-item` 섹션이 항목 수만큼 나오는지도 본다.
    항목반복형 프리셋(결보 29편 중 14편의 실제 구조)이 이걸 요구한다.
    """
    path = Path(report_path)
    if not path.exists():
        return [Finding("error", str(report_path), "보고서 파일이 없다")]
    text = path.read_text(encoding="utf-8")
    headings = [re.sub(r"^#+\s*(?:\d+[.)]\s*)?", "", ln).strip()
                for ln in text.split("\n") if ln.startswith("#")]
    # 부분 문자열로 맞추면 `# 실험 결과 분석` 한 줄이 `실험 결과` 와 `결과 분석`
    # 두 요구 섹션을 동시에 만족시켜 버린다. 정확히 일치해야 한다.
    out, last = [], -1
    for sec in sections:
        if not sec.generate:
            continue
        hits = [i for i, h in enumerate(headings) if h == sec.name]
        pos = hits[0] if hits else None
        if pos is None:
            out.append(Finding("error", path.name, f"양식이 요구하는 섹션 '{sec.name}' 이 없다"))
            continue
        if sec.repeat == "per-item" and item_count is not None and len(hits) != item_count:
            out.append(Finding("error", path.name,
                f"섹션 '{sec.name}' 은 항목마다 반복돼야 한다 — "
                f"항목 {item_count}개인데 {len(hits)}번 나온다"))
        if pos < last:
            out.append(Finding("warn", path.name,
                f"섹션 '{sec.name}' 의 순서가 양식과 다르다"))
        last = max(last, pos)
    return out


# 참고문헌에 올라오면 안 되는 2차 미러·백과·블로그. 과거 제출본
# (`from_the_past/`) 참고문헌의 거의 전부가 여기 걸린다 — 그 형식을 따라 하면
# 검증되지 않은 출처가 그대로 제출본에 들어간다. ③ §절대 규칙 9.
_BANNED_REF_HOSTS = (
    "alldatasheet", "datasheet.co.kr", "hobbytronics", "datasheetspdf",
    "naver.", "blog.me", "tistory", "wikipedia", "namu.wiki",
    "slideshare", "electronicshub", "electronics-tutorials", "chipdocs",
)

# 데이터시트 인용 한 줄이 갖춰야 하는 것. URL 만 있고 개정·날짜가 없으면
# 어느 판을 봤는지 특정되지 않는다 — 74HC 계열은 개정마다 전기적 특성이 바뀐다.
_REF_URL = re.compile(r"https?://\S+")
_REF_DATE = re.compile(r"(?:19|20)\d{2}[-.\s년]")
_REF_EDITION = re.compile(r"Rev\.?\s*\d+|S[A-Z]{3}\d{3}[A-Z]?|SNOS[A-Z0-9]+", re.I)
# `74` 로 시작하는 것만 IC 로 본다. 바로 `\d{4}` 를 쓰면 발행연도(`2024`,
# `1974`)가 전부 IC 이름으로 잡혀 "안 쓰는 IC 를 인용했다" 오탐이 쏟아진다.
#
# 경계는 `\b` 가 아니라 **앞뒤로 숫자만 막는다.** `\b` 를 쓰면 벤더 품번
# 접두(`SN7486`·`MM74HC86`·`CD74HC20`)에서 `74…` 앞이 글자라 경계가 서지 않아
# 토큰을 통째로 놓친다 — TI 서지는 표제가 전부 `SN` 접두다. 앞의 숫자를 막으면
# `1974` 안의 `74` 는 그대로 걸러지고, 뒤의 숫자를 막으면 `74HC1480` 을
# `74HC148` 로 잘못 자르지 않는다.
_IC_TOKEN = re.compile(r"(?<![0-9])(?:74[A-Z]{0,3}\d{1,3}|LM\d{3})(?![0-9])")


def _reference_block(text: str) -> tuple:
    """`참고문헌` 절의 (본문 줄 목록, 절을 찾았는가)."""
    lines = text.split("\n")
    start = None
    for i, ln in enumerate(lines):
        if ln.startswith("#") and "참고문헌" in ln:
            start = i + 1
            break
    if start is None:
        return [], False
    out = []
    for ln in lines[start:]:
        if ln.startswith("#"):
            break
        out.append(ln)
    return out, True


_REF_BULLET = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s")

# `74HC86` · `74LS86` · `7486` 을 같은 칩으로 본다. 74 시리즈에서 가운데 글자는
# 계열(HC/HCT/LS/S/…)이고 번호가 기능을 정한다 — 핀 배치는 계열이 달라도 같다.
_IC_FAMILY = re.compile(r"^74[A-Z]*(\d{1,3})$")


def _ic_family(tok: str) -> str:
    """IC 토큰에서 계열 글자를 떼어 번호만 남긴다. 74 계열이 아니면 그대로."""
    m = _IC_FAMILY.match(tok)
    return f"74{m.group(1)}" if m else tok


def _reference_entries(body) -> list:
    """참고문헌 줄들을 **인용 한 건 단위**로 묶는다.

    불릿으로 시작하는 줄이 새 인용이고, 들여쓴 다음 줄은 그 인용의 계속이다.
    서지가 길어 URL 을 다음 줄로 내리는 것이 정상 형식이라, 줄 단위로 검사하면
    그 URL 줄에 개정·날짜가 없다고 멀쩡한 인용을 경고로 잡는다.
    """
    entries, cur = [], None
    for ln in body:
        if _REF_BULLET.match(ln):
            if cur is not None:
                entries.append(cur)
            cur = ln
        elif cur is not None and ln.strip():
            cur += " " + ln.strip()
        elif not ln.strip() and cur is not None:
            entries.append(cur)
            cur = None
    if cur is not None:
        entries.append(cur)
    return entries


def verified_datasheet_ics(root) -> set:
    """`.claude/데이터시트_출처.md` 가 확인해 둔 IC 이름 집합.

    파일이 없으면 빈 집합을 준다 — 그때는 '표에 없다' 판정을 하지 않는다.
    검증기가 자료 부재를 오류로 바꾸면 안 되기 때문이다.
    """
    path = Path(root) / ".claude" / "데이터시트_출처.md"
    if not path.exists():
        return set()
    out = set()
    for ln in path.read_text(encoding="utf-8").split("\n"):
        if ln.startswith("|"):
            out.update(_IC_TOKEN.findall(ln))
    return out


def check_report_references(report_path, spec, root=None) -> list:
    """참고문헌 절이 **실제로 쓴 IC 의 제조사 데이터시트**를 갖췄는지 본다.

    ③ `write-pre-report` §절대 규칙 9 의 기계 검사판이다. 규칙만 두면
    지시했을 뿐 보장되지 않는다 — 실제로 나오는지는 검사가 있어야 안다.

    다섯 가지를 본다:
      1. 참고문헌 절이 있는가
      2. 강의노트 줄이 있는가
      3. 명세 `ics` 의 IC 마다 인용 줄이 있는가
      4. 데이터시트 줄에 URL·개정/문서번호·발행연도가 다 있는가
      5. 금지 호스트(2차 미러·백과·블로그)가 없는가
    """
    path = Path(report_path)
    if not path.exists():
        return [Finding("error", str(report_path), "보고서 파일이 없다")]
    text = path.read_text(encoding="utf-8")
    body, found = _reference_block(text)
    if not found:
        return [Finding("error", path.name, "'출처 및 참고문헌' 절이 없다")]

    out = []
    joined = "\n".join(body)
    if not joined.strip():
        out.append(Finding("error", path.name, "참고문헌 절이 비어 있다"))
        return out

    if "강의노트" not in joined:
        out.append(Finding("error", path.name,
            "참고문헌에 강의노트가 없다 — 그 주 실습 자료는 언제나 출처다"))

    for ln in body:
        low = ln.lower()
        for host in _BANNED_REF_HOSTS:
            if host in low:
                out.append(Finding("error", path.name,
                    f"참고문헌에 금지된 2차 출처가 있다 ('{host}') — "
                    f"제조사 사이트가 1차 출처다: {ln.strip()[:60]}"))
                break

    # 명세는 `741 OP amp` 처럼 접미사를 붙여 적기도 한다. 문자열 그대로
    # 비교하면 그런 항목이 전부 "없다" 로 잡히므로 IC 토큰만 뽑아 견준다.
    used = sorted({tok for item in spec.items for ic in item.ics
                   for tok in _IC_TOKEN.findall(ic)})
    # 있는지 없는지도 **계열 글자를 뗀 번호로** 견준다. 아래 "안 쓴 IC" 검사와
    # 같은 기준이어야 한다 — 한쪽만 계열을 따지면 명세가 `7404`(TTL 표기)인데
    # 핀아웃 근거로 `74HC04` 를 인용한 보고서가 양쪽에서 동시에 걸린다
    # (없다고 error, 안 쓴다고 warn). 실험03 이 정확히 그 경우다.
    cited = {_ic_family(tok) for tok in _IC_TOKEN.findall(joined)}
    for ic in used:
        if _ic_family(ic) not in cited:
            out.append(Finding("error", path.name,
                f"'{ic}' 를 쓰는데 참고문헌에 그 데이터시트가 없다"))

    # 인용했지만 안 쓴 IC — 안 본 자료를 봤다고 적는 것이다.
    #
    # **계열 글자는 무시하고 번호로만 견준다.** 벤더 데이터시트 한 편이 계열을
    # 여럿 함께 다루고 표제도 `SN5486, SN54LS86A, …, SN7486` 이나
    # `74HC04; 74HCT04` 라, 서지를 제대로 옮겨 적으면 쓰지 않는 계열 이름이
    # 반드시 따라온다. 명세가 `7486`(TTL 표기)인데 핀아웃 근거로 `74HC86` 을
    # 인용하는 것도 정당하다 — 실험03 처럼 교안 표기와 실물 각인이 갈리는
    # 주차가 있다. 계열까지 일치를 요구하면 이런 인용이 전부 오탐이 된다.
    allowed = {_ic_family(ic) for ic in used}
    for tok in sorted(set(_IC_TOKEN.findall(joined))):
        if _ic_family(tok) in allowed:
            continue
        if any(tok in ln for ln in body if _REF_URL.search(ln)):
            out.append(Finding("warn", path.name,
                f"'{tok}' 은 이 주에 쓰지 않는데 참고문헌에 있다"))

    # 인용 한 건이 여러 줄에 걸치는 것이 정상이다 — 서지가 길어 URL 을 다음
    # 줄로 내린다. 줄 단위로 검사하면 그 URL 줄에는 개정도 날짜도 없으므로
    # 멀쩡한 인용이 전부 경고로 잡힌다. 불릿 단위로 묶어서 본다.
    for entry in _reference_entries(body):
        if not _REF_URL.search(entry) or not _IC_TOKEN.search(entry):
            continue
        if not _REF_EDITION.search(entry):
            out.append(Finding("warn", path.name,
                f"데이터시트 인용에 개정/문서번호가 없다 — "
                f"어느 판인지 특정되지 않는다: {entry.strip()[:60]}"))
        if not _REF_DATE.search(entry):
            out.append(Finding("warn", path.name,
                f"데이터시트 인용에 발행연도가 없다: {entry.strip()[:60]}"))

    verified = verified_datasheet_ics(root) if root else set()
    if verified:
        for ic in used:
            if ic not in verified:
                out.append(Finding("warn", path.name,
                    f"'{ic}' 가 `.claude/데이터시트_출처.md` 에 없다 — "
                    f"벤더 사이트에서 확인해 표에 먼저 추가한다"))
    return out


def _bare_cell(s) -> str:
    """표 머리·셀 비교용. 굵게·백틱을 벗기고 공백을 누른다."""
    return " ".join(str(s).replace("**", "").replace("`", "").split())


def _col_map(head, st_header):
    """보고서 머리의 열마다 명세 열 번호. 하나라도 못 짝지으면 None.

    같은 글자는 나온 차례대로 짝짓는다 — 실험3 반감산기 `A B D B` 에서 보고서의
    둘째 `B` 는 명세 넷째 열(출력)이다. `st_header.index()` 로 찾으면 두 `B` 가
    모두 입력 열로 가서, 교안 그대로 옮긴 표에 "셀이 틀렸다" 는 거짓 error 가 난다.
    """
    used, out = set(), []
    for c in head:
        k = next((j for j, s in enumerate(st_header) if s == c and j not in used), None)
        if k is None:
            return None
        used.add(k)
        out.append(k)
    return out


def _leftover(names, against) -> list:
    """`names` 에서 `against` 와 짝지어지지 않고 남는 이름. 같은 글자는 개수로 센다."""
    left = Counter(against)
    out = []
    for c in names:
        if left[c]:
            left[c] -= 1
        else:
            out.append(c)
    return out


def check_report_tables(report_path, spec, *, cells=True) -> list:
    """보고서 표가 명세 기록표의 **머리·열 순서**(와 `cells` 면 진리표 셀)를 옮겼는지 본다.

    ③ `write-pre-report` §절대 규칙 22 의 기계 검사판이다. 2026-09 실험01 예보가
    명세 T1~T4 의 `A B C L1 L2` 를 `A B C Y` 로 줄여 냈다 — 중간단 `L1` 을 버리고
    최종 `L2` 를 `Y` 로 바꿨다. 행 수 대조는 명세 안에서만 돌아 ⑤ 가 그대로
    통과시켰고, 조교가 감점했다(-1).

    - 대상은 명세의 `truth-table` 과 `stepped` 다. `stepped` 는 칸이 실험실에서 채워지므로
      늘 머리만 보고 행 수도 보지 않는다.
    - `cells=True`(예비보고서)면 진리표는 **정확 대응이 먼저**다 — 머리가 명세 머리에
      짝지어지고, 행 수가 같고, 셀까지 전부 같은 표. 머리와 행 수만 보면 실험01 의
      T1~T4 처럼 머리가 같은 표 넷이 서로의 짝으로 잡혀 AND 표를 OR 명세로 대조하게
      된다. §절대 규칙 19 가 넓은 표를 나누게 하므로 대응 표는 여럿일 수 있다.
    - `cells=False`(결과보고서)면 셀은 관측값이라 보지 않는다. 셀로 짝을 가를 수 없으니
      명세 순서대로, 머리가 맞는 아직 안 쓴 표 하나와 먼저 1:1 로 짝짓는다. §절대 규칙 19
      로 나뉜 넓은 표는, 아직 안 쓴 표 가운데 지금까지 짝의 열에 없는 명세 열을 새로
      덮는 표만 보고서 표 순서대로 이어 붙인다 — 머리가 완전히 같은 표는 새 열이 없어
      붙지 않으므로 "같은 머리 표 넷이 보고서 표 하나를 나눠 갖지 않는다" 는 그대로다.
      2026-09-14 전에는 결과보고서에 아예 부르지 않았다.
    - 정확 대응이 없으면, 어느 명세 표에도 대응하지 않은 표 가운데 머리가 가장 많이
      겹치는 표(진리표는 행 수도 같은 것)를 짚는다. 머리가 짝지어지면 처음 갈리는
      행을, 아니면 빠진 열과 명세에 없는 열을 알린다. 같은 글자 열은 `B(4열)` 처럼
      자리로 부른다.
    - 참조표(`role: reference`)는 §절대 규칙 16 으로 빠질 수 있어 요구하지 않는다.
      다만 셀까지 정확 대응한 표는 다른 명세 표의 짝 후보에서 뺀다. `cells=False`
      에서는 참조표를 짝으로 가져가지 않으므로, 머리와 행 수가 같은 기록표·참조표
      쌍(실험03 T5·T6)에서는 보고서의 이론표가 기록표 자리를 채워 누락을 가릴 수
      있다 — 알려진 한계.
    - 명세에 없는 표는 잡지 않는다 — §섹션별 재료 실험 이론 ⑵ 가 데이터시트
      function table 처럼 명세 밖 이론표를 싣게 한다.
    """
    path = Path(report_path)
    if not path.exists():
        return [Finding("error", str(report_path), "보고서 파일이 없다")]
    found = md.parse_tables(path.read_text(encoding="utf-8"))
    heads = [[_bare_cell(c) for c in t.header] for t in found]
    checked = [t for t in spec.tables if t.kind in ("truth-table", "stepped")]

    def bare(st):
        return [_bare_cell(c) for c in st.header]

    def fits(i, st):
        """머리가 명세 머리에 짝지어지고, 진리표면 행 수도 같다."""
        return (bool(heads[i]) and _col_map(heads[i], bare(st)) is not None
                and (st.kind != "truth-table" or len(found[i].rows) == len(st.rows)))

    def first_diff(i, st):
        """셀이 처음 갈리는 (행 번호, 보고서 값, 명세 값). 전부 같으면 None."""
        cols = _col_map(heads[i], bare(st))
        for r, (row, srow) in enumerate(zip(found[i].rows, st.rows), start=1):
            got = [str(normalize_cell(_bare_cell(v))) for v in row]
            exp = [str(normalize_cell(srow[k])) for k in cols]
            if got != exp:
                return r, got, exp
        return None

    def by_cells(st):
        return cells and st.kind == "truth-table"

    # 셀을 보는 표가 먼저 짝을 가져간다(셀까지 같은 표 전부). 나머지는 명세 순서대로 1:1.
    exact, claimed = {}, set()
    for st in checked:
        if by_cells(st):
            exact[st.id] = [i for i in range(len(found))
                            if fits(i, st) and first_diff(i, st) is None]
            claimed.update(exact[st.id])
    for st in checked:
        if not by_cells(st) and st.role == "record":
            st_header = bare(st)
            hits, covered = [], set()
            for i in range(len(found)):
                if i in claimed or not fits(i, st):
                    continue
                cols = set(_col_map(heads[i], st_header))
                if hits and cols <= covered:
                    continue  # 새 열을 보태지 않는 표(같은 머리 반복)는 짝에 더하지 않는다
                hits.append(i)
                covered |= cols
            exact[st.id] = hits
            claimed.update(hits)

    out = []
    for st in checked:
        if st.role != "record":
            continue
        st_header = bare(st)
        want = " ".join(st_header)
        hits = exact[st.id]
        if hits:
            for i in hits:
                order = _col_map(heads[i], st_header)
                if order != sorted(order):
                    out.append(Finding("error", path.name,
                        f"{found[i].line}줄 표 `{' '.join(heads[i])}` 의 열 순서가 "
                        f"명세 {st.id} `{want}` 와 다르다"))
            covered = {k for i in hits for k in _col_map(heads[i], st_header)}
            missing = [column_label(st_header, k) for k in range(len(st_header))
                       if k not in covered]
            if missing:
                out.append(Finding("error", path.name,
                    f"명세 {st.id} 의 열 {', '.join(missing)} 이 보고서 표에 없다 "
                    f"(명세: `{want}`)"))
            continue
        near = [i for i in range(len(found)) if i not in claimed
                and (st.kind != "truth-table" or len(found[i].rows) == len(st.rows))
                and set(heads[i]) & set(st_header)]
        if not near:
            out.append(Finding("error", path.name,
                f"명세 {st.id} (`{want}`) 에 대응하는 표가 보고서에 없다"))
            continue
        i = max(near, key=lambda k: (sum((Counter(heads[k]) & Counter(st_header)).values()),
                                     -k))
        claimed.add(i)
        if fits(i, st):
            r, got, exp = first_diff(i, st)
            out.append(Finding("error", path.name,
                f"{found[i].line}줄 표 {r}번째 행이 명세 {st.id} 와 다르다: "
                f"보고서 {got} · 명세 {exp}"))
        else:
            missing = _leftover(st_header, heads[i])
            extra = _leftover(heads[i], st_header)
            out.append(Finding("error", path.name,
                f"{found[i].line}줄 표 `{' '.join(heads[i])}` 가 명세 {st.id} `{want}` 와 "
                f"머리가 다르다 — 빠진 열: {', '.join(missing) or '없음'} · "
                f"명세에 없는 열: {', '.join(extra) or '없음'}. "
                "열 이름·열 수를 명세 그대로 옮긴다"))
    return out
