"""결선도의 **두 층 계약**을 강제한다.

이 그림은 제출물이 아니다. 운영계획서 3.2 6) 이 "직접 손으로 작성한 회로
결선도"를 요구하므로, 렌더 결과물은 조원이 **따라 그릴 원도**다. 그래서
무엇이 그림 위에 있어야 하고 무엇이 있으면 안 되는지가 갈린다.

  · 보드 위  — 손으로 옮겨 그릴 것 (배선, 칩, 핀 번호, 두 글자 꼬리표)
  · 보드 밖  — 옮겨 그릴 수 없는 것 (미사용핀을 접지하는 *이유*, 계측 지시)

2026-09 이전 판은 이 둘을 섞어 보드 위에 라벨 박스를 30개 넘게 얹었다. 그중
절반은 손으로 옮길 것이 하나도 없는 문구인데 하필 **따라 그릴 홀을 덮었다.**
같은 내용이 예비보고서 본문에 이미 문장으로 있었다.

문서로만 적어 두면 다음 주차 빌더가 조용히 옛 방식으로 돌아간다 — 옛 함수
(`draw_wire`, `draw_badge`)가 그대로 살아 있고 더 짧기 때문이다. 그래서 센다.
"""
import ast
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / ".claude/skills/breadboard-diagram/scripts/render_breadboard.py"

# 보드 안쪽 x 범위. 이 밖에 앉는 배지는 여백이라 홀을 가리지 않는다
BOARD_L, BOARD_R = 149, 877

# 보드 위에 허용하는 꼬리표 개수. `L1`·`A'`·`Z` 처럼 두 글자짜리만 남긴
# 결과가 회로당 0~5 개다. 문구를 다시 얹기 시작하면 여기서 걸린다
MAX_ON_BOARD_LABELS = 8

# `_tag()` 만 보드 위 배지를 그린다. 빌더가 직접 부르면 옛 방식으로 돌아간 것
SANCTIONED_BADGE_HELPER = "_tag"


def _module():
    spec = importlib.util.spec_from_file_location("render_breadboard", SRC)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _circuit_builders(mod):
    """`--circuit` 이 부르는 빌더. `*_all` 은 이들을 묶기만 한다."""
    import inspect
    out = {}
    for name, fn in vars(mod).items():
        if (name.startswith("build_") and not name.endswith("_all")
                and inspect.isfunction(fn)):
            out[name] = fn
    return out


class BuilderApiContract(unittest.TestCase):
    """소스를 ast 로 읽어 옛 API 로 새는지 본다."""

    @staticmethod
    def _builder_like(tree):
        for n in tree.body:
            if isinstance(n, ast.FunctionDef) and (
                    n.name.startswith("build_") or n.name.startswith("_build_")
                    or n.name.startswith("_e1_") or n.name.startswith("_e2_")):
                yield n

    def _calls(self, node, attr):
        return [c for c in ast.walk(node)
                if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
                and c.func.attr == attr]

    def test_빌더가_번호_없는_배선을_그리지_않는다(self):
        tree = ast.parse(SRC.read_text(encoding="utf-8"))
        bad = [n.name for n in self._builder_like(tree) if self._calls(n, "draw_wire")]
        self.assertEqual(bad, [], f"{bad}: draw_wire 는 번호도 순서표도 남기지 않는다. "
                                  "step_wire 를 쓴다")

    def test_빌더가_보드_위에_배지를_직접_그리지_않는다(self):
        tree = ast.parse(SRC.read_text(encoding="utf-8"))
        bad = [n.name for n in self._builder_like(tree) if self._calls(n, "draw_badge")]
        self.assertEqual(bad, [], f"{bad}: 보드 위 꼬리표는 {SANCTIONED_BADGE_HELPER}() 로, "
                                  "설명은 note() 로 보드 밖에 낸다")


class RenderedContract(unittest.TestCase):
    """실제로 그려 보고 센다. ast 로는 위임을 못 따라간다."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _module()

    def _render(self, fn):
        counted = {'labels': 0}
        mod = self.mod
        orig_badge = mod.BreadboardRenderer.draw_badge
        captured = {}

        def spy_badge(self_, x, y, text, *a, **k):
            if BOARD_L < x < BOARD_R:
                counted['labels'] += 1
            return orig_badge(self_, x, y, text, *a, **k)

        orig_export = mod.BreadboardRenderer.export

        def spy_export(self_, *a, **k):
            captured['bb'] = self_
            return orig_export(self_, *a, **k)

        mod.BreadboardRenderer.draw_badge = spy_badge
        mod.BreadboardRenderer.export = spy_export
        try:
            with tempfile.TemporaryDirectory() as d:
                fn(os.path.join(d, 'x.png'))
        finally:
            mod.BreadboardRenderer.draw_badge = orig_badge
            mod.BreadboardRenderer.export = orig_export
        return captured['bb'], counted['labels']

    def test_모든_회로가_결선_순서표를_낸다(self):
        """번호와 순서표가 없으면 조원은 30가닥을 동시에 봐야 한다."""
        for name, fn in _circuit_builders(self.mod).items():
            with self.subTest(회로=name):
                bb, _ = self._render(fn)
                self.assertTrue(bb.numbered, f"{name}: enable_steps() 를 안 불렀다")
                self.assertGreater(len(bb.steps), 0, f"{name}: 결선 순서표가 비었다")

    def test_보드_위_꼬리표가_적다(self):
        for name, fn in _circuit_builders(self.mod).items():
            with self.subTest(회로=name):
                _, labels = self._render(fn)
                self.assertLessEqual(
                    labels, MAX_ON_BOARD_LABELS,
                    f"{name}: 보드 위 라벨 {labels}개. 손으로 옮겨 그릴 것이 아니면 "
                    "note() 로 보드 밖에 낸다")

    def test_배선_색이_넷을_넘지_않는다(self):
        """이전 판은 한 장에 16색을 썼고 그중 눈으로 구분 안 되는 쌍이 여럿이었다.
        따라 그리는 사람 손에 있는 펜도 네 자루다."""
        self.assertEqual(set(self.mod.WIRE), {'vcc', 'gnd', 'sig', 'mid'})
        self.assertEqual(len(set(self.mod.WIRE.values())), 4, '색이 겹친다')

    def test_계측기는_배선_색을_쓰지_않는다(self):
        """프로브는 점퍼로 꽂는 게 아니라 문다. 색을 섞으면 조원이 프로브 자리에
        점퍼선을 찾는다."""
        self.assertNotIn(self.mod.PROBE, set(self.mod.WIRE.values()))


if __name__ == '__main__':
    unittest.main()
