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
"""

import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / ".claude/skills/breadboard-diagram/scripts/render_breadboard.py"
SKILL = ROOT / ".claude/skills/breadboard-diagram/SKILL.md"


def _tree():
    return ast.parse(SRC.read_text(encoding="utf-8"))


def _dispatch_pairs():
    """`dispatch = {...}` 의 (회로 ID, 빌더 함수 이름) 목록."""
    for node in ast.walk(_tree()):
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "dispatch" for t in node.targets):
            return [(ast.literal_eval(k), v.id)
                    for k, v in zip(node.value.keys, node.value.values)]
    raise AssertionError("dispatch 딕셔너리를 못 찾았다")


def _choices():
    """`--circuit` 인자의 choices 리스트."""
    for node in ast.walk(_tree()):
        if (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "add_argument"
                and node.args and getattr(node.args[0], "value", "") == "--circuit"):
            for kw in node.keywords:
                if kw.arg == "choices":
                    return ast.literal_eval(kw.value)
    raise AssertionError("--circuit 의 choices 를 못 찾았다")


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


class BreadboardDispatch(unittest.TestCase):
    def test_회로_ID_가_빌더를_공유하지_않는다(self):
        """두 회로가 한 빌더를 쓰면 둘 중 하나는 반드시 틀린 그림이다."""
        pairs = _dispatch_pairs()
        seen = {}
        shared = []
        for circuit, builder in pairs:
            if builder in seen:
                shared.append(f"{seen[builder]} 와 {circuit} 가 {builder} 를 공유한다")
            seen[builder] = circuit
        self.assertEqual(shared, [], "\n".join(shared))

    def test_choices_와_dispatch_가_같은_집합이다(self):
        self.assertEqual(sorted(_choices()),
                         sorted(c for c, _ in _dispatch_pairs()))

    def test_지원하지_않는_회로를_SKILL_문서가_광고하지_않는다(self):
        doc = SKILL.read_text(encoding="utf-8")
        supported = {c for c, _ in _dispatch_pairs()}
        for gone in ("e1_or", "e1_nor"):
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


class ChipPinout(unittest.TestCase):
    """빌더가 그리는 칩이 netlist 가 지정한 칩과 같은지 본다."""

    def test_e1_or_은_74HC32_를_그린다(self):
        chips = [ast.literal_eval(c.args[0])
                 for c in _calls_in("build_e1_or", "draw_chip")]
        self.assertEqual(chips, ["74HC32"],
                         "netlist C2 는 74HC32 단일 칩이다")

    def test_e1_nor_은_74HC32_와_74HC02_를_그린다(self):
        chips = [ast.literal_eval(c.args[0])
                 for c in _calls_in("build_e1_nor", "draw_chip")]
        self.assertEqual(chips, ["74HC32", "74HC02"],
                         "netlist C4 는 OR 앞단 + NOR 뒷단이다")

    def test_74HC02_의_미사용_출력을_4_10_13_으로_잡는다(self):
        """74HC00·74HC08·74HC32 는 출력이 3·6·8·11 이지만 74HC02 는
        1·4·10·13 이다. netlist 가 '이 실험에서 가장 흔한 배선 실수'로
        표시한 지점이고, 옛 `e1_nor` 별칭이 정확히 여기서 틀렸다."""
        out_sets = [set(ast.literal_eval(c.args[0]))
                    for c in _calls_in("build_e1_nor", "mark_unused_outputs")]
        self.assertIn({4, 10, 13}, out_sets,
                      "74HC02 의 미사용 출력은 4·10·13 이다")
        in_sets = [set(ast.literal_eval(c.args[0]))
                   for c in _calls_in("build_e1_nor", "connect_unused_inputs")]
        self.assertIn({5, 6, 8, 9, 11, 12}, in_sets,
                      "74HC02 의 미사용 입력은 5·6·8·9·11·12 이다")


if __name__ == "__main__":
    unittest.main()
