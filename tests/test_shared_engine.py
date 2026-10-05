"""느린 v2 시험판 시험이 엔진 사본 하나를 나눠 쓰는지 본다.

경로 캐시(`_PLACE_PATHS`)는 엔진 사본마다 있어서, 시험마다 엔진을 새로 로드하면 MUX 경로 탐색
(약 28초)을 매번 다시 한다. 설계: `docs/plans/2026-10-05-느린-배선-테스트-엔진-공유-설계.md`.
"""
import ast
import importlib.util
import unittest
from pathlib import Path

from tests import _renders


class Engine(unittest.TestCase):
    def test_처음_부르면_로드한다(self):
        saved = _renders._ENGINE
        _renders._ENGINE = None
        try:
            mod = _renders.engine()
            self.assertTrue(hasattr(mod, 'place_paths'))
            self.assertIs(_renders._ENGINE, mod)
        finally:
            if saved is not None:
                _renders._ENGINE = saved

    def test_두_번_불러도_같은_사본이다(self):
        self.assertIs(_renders.engine(), _renders.engine())

    def test_따로_로드한_사본과는_다르다(self):
        spec = importlib.util.spec_from_file_location('render_breadboard', _renders.ENGINE_SCRIPT)
        fresh = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fresh)
        self.assertIsNot(fresh, _renders.engine())
        self.assertIsNot(fresh._PLACE_PATHS, _renders.engine()._PLACE_PATHS)


ROOT = Path(__file__).resolve().parents[1]
TRIAL = ROOT / 'tests/fixtures/board_v2_e4/배치.py'
GROUP = 'board_v2_e4'
SHARED = {
    'test_breadboard_v2_e4_trial': ('DmuxFinal', 'MuxFinal', 'Readability', 'StageTruth', 'Chain'),
    'test_breadboard_route': ('LambdaZero', 'ChosenWeight'),
    'test_breadboard_place': ('TrialMarkers', 'PlacedTrial'),
}


def _classes(stem):
    tree = ast.parse((ROOT / 'tests' / f'{stem}.py').read_text(encoding='utf-8'))
    return {n.name: n for n in tree.body if isinstance(n, ast.ClassDef)}


def _with_bases(classes, name):
    """클래스와 같은 파일에 정의된 기반 클래스들(`_Trial` 처럼)."""
    out, todo = [], [name]
    while todo:
        node = classes[todo.pop()]
        out.append(node)
        todo += [b.id for b in node.bases if isinstance(b, ast.Name) and b.id in classes]
    return out


def _calls(nodes, attr):
    return any(isinstance(c, ast.Call) and isinstance(c.func, (ast.Attribute, ast.Name))
               and getattr(c.func, 'attr', getattr(c.func, 'id', None)) == attr
               for n in nodes for c in ast.walk(n))


def _root(e):
    """`a.b[c].d` 의 뿌리 이름. `self.mod`·`cls.mod` 는 'mod' 로 본다."""
    while isinstance(e, (ast.Attribute, ast.Subscript)):
        if (isinstance(e, ast.Attribute) and e.attr == 'mod'
                and isinstance(e.value, ast.Name) and e.value.id in ('self', 'cls')):
            return 'mod'
        e = e.value
    return e.id if isinstance(e, ast.Name) else None


def _flat(targets):
    for t in targets:
        if isinstance(t, (ast.Tuple, ast.List)):
            yield from _flat(t.elts)
        elif isinstance(t, ast.Starred):
            yield from _flat([t.value])
        else:
            yield t


def _mutates_engine(nodes):
    """엔진 사본(`mod`·`self.mod`·`engine()` 을 받은 이름)의 속성·항목을 바꾸나 — 대입·`del`·
    `setattr`/`delattr`·`patch.object`. 엔진 전역을 바꿔 끼우는 꼴이다."""
    bound = {'mod'}
    for n in nodes:
        for a in ast.walk(n):
            if isinstance(a, ast.Assign) and _calls([a.value], 'engine'):
                bound |= {t.id for t in _flat(a.targets) if isinstance(t, ast.Name)}
    for n in nodes:
        for a in ast.walk(n):
            if isinstance(a, ast.Assign):
                targets = a.targets
            elif isinstance(a, (ast.AugAssign, ast.AnnAssign)):
                targets = [a.target]
            elif isinstance(a, ast.Delete):
                targets = a.targets
            else:
                targets = []
            for t in _flat(targets):
                if isinstance(t, (ast.Attribute, ast.Subscript)) and _root(t.value) in bound:
                    return True
            if isinstance(a, ast.Call) and a.args:
                f = a.func
                setter = isinstance(f, ast.Name) and f.id in ('setattr', 'delattr')
                patcher = (isinstance(f, ast.Attribute) and f.attr == 'object'
                           and getattr(f.value, 'id', getattr(f.value, 'attr', None)) == 'patch')
                if (setter or patcher) and _root(a.args[0]) in bound:
                    return True
    return False


def _effective_group(cls, module):
    """`tests/conftest.py` 가 이 클래스 시험에 붙일 xdist 그룹 — 가까운 명시 마크(클래스 > 모듈) >
    `xdist_per_test`(시험마다 흩음 → None) > `render_group`."""
    for m in list(getattr(cls, 'pytestmark', [])) + list(getattr(module, 'pytestmark', [])):
        if m.name == 'xdist_group':
            return m.args[0] if m.args else m.kwargs.get('name')
    if getattr(cls, 'xdist_per_test', False):
        return None
    return getattr(cls, 'render_group', None)


class EffectiveGroup(unittest.TestCase):
    """그룹 확인은 `render_group` 속성이 아니라 `tests/conftest.py` 가 실제로 붙일 그룹을 본다 —
    명시 `xdist_group` 마크와 `xdist_per_test` 가 `render_group` 을 덮는다(2026-10-05 최종 검토)."""

    def test_덮어쓰기를_conftest_순서대로_본다(self):
        import types

        import pytest
        module = types.SimpleNamespace()

        class Plain:
            render_group = GROUP

        class PerTest(Plain):
            xdist_per_test = True

        class Marked(Plain):
            pytestmark = [pytest.mark.xdist_group('other').mark]

        self.assertEqual(_effective_group(Plain, module), GROUP)
        self.assertIsNone(_effective_group(PerTest, module))
        self.assertEqual(_effective_group(Marked, module), 'other')
        module.pytestmark = [pytest.mark.xdist_group('mod').mark]
        self.assertEqual(_effective_group(Plain, module), 'mod')


class Grouping(unittest.TestCase):
    def test_대상_클래스는_한_그룹이다(self):
        import importlib
        for stem, names in SHARED.items():
            m = importlib.import_module(f'tests.{stem}')
            for name in names:
                self.assertEqual(_effective_group(getattr(m, name), m), GROUP, f'{stem}::{name}')

    def test_대상_클래스는_공용_사본을_쓴다(self):
        for stem, names in SHARED.items():
            classes = _classes(stem)
            for name in names:
                nodes = _with_bases(classes, name)
                self.assertTrue(_calls(nodes, 'engine'), f'{stem}::{name} 가 _renders.engine() 을 안 부른다')
                self.assertFalse(_calls(nodes, '_load'), f'{stem}::{name} 가 아직 _load() 로 새 사본을 만든다')

    def test_공용_사본을_쓰는_클래스는_엔진_전역을_바꾸지_않는다(self):
        for path in sorted((ROOT / 'tests').glob('test_*.py')):
            stem = path.stem
            classes = _classes(stem)
            for name in classes:
                nodes = _with_bases(classes, name)
                if _calls(nodes, 'engine'):
                    self.assertFalse(_mutates_engine(nodes),
                                     f'{stem}::{name} 는 공용 엔진의 전역을 바꾼다 — 각자 _load() 하라')


class MutationGuard(unittest.TestCase):
    """감시기가 공용 엔진을 바꿔 끼우는 흔한 꼴을 다 잡는가 — `mod.x =` 꼴만 잡던 것(2026-10-05 최종 검토)."""
    CAUGHT = (
        "mod.route_plan = f",
        "self.mod._routes = f",
        "setattr(mod, 'route_plan', f)",
        "mock.patch.object(mod, 'route_plan', f)",
        "eng = _renders.engine()\neng.route_plan = f",
        "mod.BreadboardRenderer.export = spy",
        "mod.DIP_PINS['x'] = 1",
        "mod.__dict__['x'] = 1",
        "mod.a, mod.b = 1, 2",
        "del mod.route_plan",
    )
    CLEAN = (
        "cls.mod = _renders.engine()",
        "b = mod.load_board_file(TRIAL, 'x')",
        "x = mod.DENSITY_WEIGHT",
        "self.board = b",
    )

    def test_바꿔_끼우는_꼴은_잡고_읽기는_놔둔다(self):
        for src in self.CAUGHT:
            self.assertTrue(_mutates_engine([ast.parse(src)]), src)
        for src in self.CLEAN:
            self.assertFalse(_mutates_engine([ast.parse(src)]), src)


class CacheKey(unittest.TestCase):
    render_group = GROUP     # 그룹 안에서 다른 시험 뒤에 돌면 캐시라 거의 공짜, 혼자 돌면 DMUX 탐색 약 4.5초

    def test_기본_λ_와_엔진_λ_가_같은_경로를_쓴다(self):
        mod = _renders.engine()
        b = mod.load_board_file(TRIAL, 'board_v2_e4')
        self.assertIs(b._dmux_paths(None), b._dmux_paths(mod.DENSITY_WEIGHT))


if __name__ == '__main__':
    unittest.main()
