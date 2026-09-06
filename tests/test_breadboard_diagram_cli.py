"""`breadboard-diagram` CLI 의 회로 ID 계약.

2026-09-06 에 발견: `dispatch` 가 `e1_or → build_e1_and`, `e1_nor → build_e1_nand`
로 매핑해 OR·NOR 을 요청하면 AND·NAND 그림이 나왔다. SKILL.md 는 `e1_nor` 가
`74HC02` 의 출력 핀 1번 배치를 반영한다고 광고했지만 소스에 `74HC02` 가 없다.
결선도가 없는 것보다 **틀린 결선도가 나오는 것**이 훨씬 나쁘다 — 그 지점이
netlist 스스로 "가장 흔한 배선 실수"라고 표시한 곳이기 때문이다.

임포트하지 않고 소스를 `ast` 로 읽는다. 이 스크립트는 패키지가 아니고 PIL 을
끌어온다.
"""

import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / ".agents/skills/breadboard-diagram/scripts/render_breadboard.py"
SKILL = ROOT / ".agents/skills/breadboard-diagram/SKILL.md"


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


if __name__ == "__main__":
    unittest.main()
