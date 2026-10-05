"""`breadboard-diagram` CLI 의 회로 ID 계약.

2026-09-06 에 발견: `dispatch` 가 `e1_or → build_e1_and`, `e1_nor → build_e1_nand`
로 매핑해 OR·NOR 을 요청하면 AND·NAND 그림이 나왔다. SKILL.md 는 `e1_nor` 가
`74HC02` 의 출력 핀 1번 배치를 반영한다고 광고했지만 소스에 `74HC02` 가 없다.
결선도가 없는 것보다 **틀린 결선도가 나오는 것**이 훨씬 나쁘다 — 그 지점이
netlist 스스로 "가장 흔한 배선 실수"라고 표시한 곳이기 때문이다.

임포트하지 않고 소스를 `ast` 로 읽는다. 이 스크립트는 패키지가 아니고 PIL 을
끌어온다. 정본은 `.claude/skills/breadboard-diagram/` 이다 — 2026-09-06 에
`.agents/skills/` 사본과 갈라진 것을 발견해 일원화했다. 다른 스킬 아홉 개가
모두 `.claude/skills/` 아래 있고 슬래시 커맨드 런타임도 여기서 로드한다.

2026-09-15: 엔진과 주차 결선을 나눴다. 회로 ID 분기표(`dispatch`·`--circuit`)는 없고,
빌더는 `보고서/실험NN/결선도/배치.py` 에 있다. 아래 `_tree()` 는 엔진과 주차 파일을 한
모듈처럼 이어 읽는다.
"""

import ast
import unittest
from pathlib import Path

from tests._boards import board_files, engine_files

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / ".claude/skills/breadboard-diagram/scripts/render_breadboard.py"
SKILL = ROOT / ".claude/skills/breadboard-diagram/SKILL.md"


def _tree():
    """엔진과 주차 `배치.py` 전부를 한 모듈처럼 이어 읽는다 — 상수·빌더가 어느
    파일에 있든 아래 도우미가 그대로 찾는다."""
    body = []
    for p in [*engine_files(), *board_files()]:
        body += ast.parse(p.read_text(encoding="utf-8")).body
    return ast.Module(body=body, type_ignores=[])


def _cli_options():
    """엔진 `main()` 의 `add_argument` 첫 인자들."""
    tree = ast.parse(SRC.read_text(encoding="utf-8"))
    return [c.args[0].value for c in ast.walk(tree)
            if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
            and c.func.attr == "add_argument" and c.args
            and isinstance(c.args[0], ast.Constant)]


def _finals(path):
    """`배치.py` 의 `FINALS = [(파일명, 빌더), …]` → [(파일명, 빌더 이름)]."""
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "FINALS" for t in node.targets):
            return [(e.elts[0].value, e.elts[1].id) for e in node.value.elts]
    raise AssertionError(f"{path}: FINALS 가 없다")


def _module_const(name):
    """모듈 최상위의 리터럴 상수. 빌더가 핀 목록을 상수로 빼 쓰면
    `ast.literal_eval` 이 Name 에서 죽는다."""
    for node in _tree().body:
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == name for t in node.targets):
            v = node.value
            # `frozenset({...})` 처럼 감싼 것은 벗겨서 읽는다
            if (isinstance(v, ast.Call) and isinstance(v.func, ast.Name)
                    and v.func.id in {"frozenset", "set", "tuple", "list"} and v.args):
                return ast.literal_eval(v.args[0])
            return ast.literal_eval(v)
    raise AssertionError(f"모듈 상수 {name} 을 못 찾았다")


def _literal(node):
    """리터럴이면 그대로, 모듈 상수 이름이면 풀어서."""
    if isinstance(node, ast.Name):
        return _module_const(node.id)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return list(_literal(node.left)) + list(_literal(node.right))
    return ast.literal_eval(node)


# 레일에 홀이 없는 행. **하드코딩하지 않는다** — 2026-09-07 까지 이 파일은
# `{2,3,4,9,15,21,32}` 를 들고 있었는데, 그건 눈대중 좌표 시절의 목록이라
# 실측값(`{1,2,63} + 8·14·20…62`)과 겹치는 데가 하나도 없었다. 검사가 엉뚱한
# 행을 막고 진짜 빈 행은 통과시키고 있었다. 렌더러가 들고 있는 값을 읽는다.
NO_HOLE_ROWS = set(_module_const("RAIL_GAP_ROWS"))


def _builder_names():
    """파일 안 `build_*` 함수 이름."""
    return [n.name for n in _tree().body
            if isinstance(n, ast.FunctionDef) and n.name.startswith("build_")]


def _calls_in(fn_name, method):
    """`build_*` 함수 안의 `bb.<method>(...)` 호출 노드."""
    for node in _tree().body:
        if isinstance(node, ast.FunctionDef) and node.name == fn_name:
            return [c for c in ast.walk(node)
                    if isinstance(c, ast.Call)
                    and isinstance(c.func, ast.Attribute)
                    and c.func.attr == method]
    raise AssertionError(f"{fn_name} 를 못 찾았다")


def _bridge_rows(fn_name):
    """그 빌더가 브리지를 그리는 행 번호."""
    rows = []
    for call in _calls_in(fn_name, "connect_unused_inputs"):
        for kw in call.keywords:
            if kw.arg == "bridge_row":
                rows.append(_literal(kw.value))
    for call in _calls_in(fn_name, "bridge_rails"):
        if len(call.args) >= 3:
            rows.append(_literal(call.args[2]))
    return rows


class BreadboardCli(unittest.TestCase):
    def test_CLI_는_실험_번호로만_부른다(self):
        """회로 ID 분기표가 있으면 엔진이 주차 이름을 알아야 한다 — 2026-09-15 에 없앴다."""
        opts = _cli_options()
        self.assertIn("--experiment", opts)
        self.assertNotIn("--circuit", opts)

    def test_완성본끼리_빌더를_공유하지_않는다(self):
        """두 완성본이 한 빌더를 쓰면 둘 중 하나는 반드시 틀린 그림이다."""
        files = board_files()
        self.assertTrue(files, "주차 결선 파일이 하나도 없다")
        for p in files:
            with self.subTest(p.parent.parent.name):
                names = [b for _f, b in _finals(p)]
                self.assertEqual(len(names), len(set(names)), names)

    def test_지원하지_않는_회로를_SKILL_문서가_광고하지_않는다(self):
        doc = SKILL.read_text(encoding="utf-8")
        supported = {n.removeprefix("build_") for n in _builder_names()}
        for gone in ("e1_or", "e1_nor", "e2_rn", "e2_rp", "e2_tpd_s1", "e2_tpd_s2",
                     "e3_ha_s1", "e3_ha_s2", "e3_hs_s1", "e3_hs_s2"):
            if gone not in supported:
                with self.subTest(circuit=gone):
                    self.assertNotIn(f"`{gone}`", doc)


class RailBridge(unittest.TestCase):
    """전원 레일쌍 넷은 물리적으로 분리된 스트립이다.

    칩 7번 핀을 좌측 GND 레일에 내리고 미사용 입력을 중앙 GND 레일에 내리면,
    두 레일이 이어져 있지 않아 그 미사용 입력들이 그대로 뜬다. 배선표로는
    보이지 않고 그림을 열어야 보인다.
    """

    def test_중앙_GND_레일로_내리면_bridge_row_를_넘긴다(self):
        missing = []
        for fn in _builder_names():
            bridged = bool(_calls_in(fn, "bridge_rails"))
            for call in _calls_in(fn, "connect_unused_inputs"):
                kw = {k.arg: k.value for k in call.keywords}
                if _literal(kw["rail"]) != "gnd" if "rail" in kw else False:
                    continue        # VCC 풀업은 14번 핀과 같은 레일로 간다
                pins = _literal(call.args[0])
                if not any(8 <= p <= 14 for p in pins):
                    continue        # 1~7번은 7번 핀과 같은 레일로 간다
                if "bridge_row" not in kw and not bridged:
                    missing.append(f"{fn}: 핀 {pins} 이 중앙 GND 레일에서 끝난다")
        self.assertEqual(missing, [], "\n".join(missing))

    def test_bridge_row_는_레일_홀이_있는_행이다(self):
        bad = []
        for fn in _builder_names():
            for row in _bridge_rows(fn):
                if row in NO_HOLE_ROWS:
                    bad.append(f"{fn}: {row}행에는 레일 홀이 없다")
        self.assertEqual(bad, [], "\n".join(bad))


def _helper_call(fn_name, callee):
    """`build_*` 함수 안의 `callee(...)` (모듈 함수) 호출 노드 하나."""
    for node in _tree().body:
        if isinstance(node, ast.FunctionDef) and node.name == fn_name:
            for c in ast.walk(node):
                if (isinstance(c, ast.Call) and isinstance(c.func, ast.Name)
                        and c.func.id == callee):
                    return c
    raise AssertionError(f"{fn_name} 안에 {callee}() 호출이 없다")


class ChipPinout(unittest.TestCase):
    """빌더가 그리는 칩이 netlist 가 지정한 칩과 같은지 본다. 실험01 빌더는 칩과
    미사용핀을 `_e1_single`·`_e1_two_chip` 에 인자로 넘기므로 그 호출을 읽는다."""

    def test_e1_or_은_74HC32_를_그린다(self):
        call = _helper_call("build_e1_or", "_e1_single")
        self.assertEqual(ast.literal_eval(call.args[1]), "74HC32",
                         "netlist C2 는 74HC32 단일 칩이다")

    def test_e1_nor_은_74HC32_와_74HC02_를_그린다(self):
        call = _helper_call("build_e1_nor", "_e1_two_chip")
        self.assertEqual([ast.literal_eval(call.args[1]), ast.literal_eval(call.args[2])],
                         ["74HC32", "74HC02"], "netlist C4 는 OR 앞단 + NOR 뒷단이다")

    def test_74HC02_의_미사용_출력을_4_10_13_으로_잡는다(self):
        """74HC00·74HC08·74HC32 는 출력이 3·6·8·11 이지만 74HC02 는
        1·4·10·13 이다. netlist 가 '이 실험에서 가장 흔한 배선 실수'로
        표시한 지점이고, 옛 `e1_nor` 별칭이 정확히 여기서 틀렸다."""
        call = _helper_call("build_e1_nor", "_e1_two_chip")
        kw = {k.arg: ast.literal_eval(k.value) for k in call.keywords}
        self.assertEqual(set(kw["back_unused_out"]), {4, 10, 13},
                         "74HC02 의 미사용 출력은 4·10·13 이다")
        self.assertEqual(set(kw["back_unused_in"]), {5, 6, 8, 9, 11, 12},
                         "74HC02 의 미사용 입력은 5·6·8·9·11·12 이다")

    def test_실험01_빌더는_미사용_입력을_접지하지_않는다(self):
        """실험01 실측(2026-09-11) 규칙. 접지는 교안이 지시한 실험02 만 한다."""
        for fn in ("build_e1_and", "build_e1_or", "build_e1_nand", "build_e1_nor",
                   "build_e1_comb", "_e1_single", "_e1_two_chip", "_e1_front"):
            with self.subTest(fn=fn):
                self.assertEqual(_calls_in(fn, "connect_unused_inputs"), [])


if __name__ == "__main__":
    unittest.main()
