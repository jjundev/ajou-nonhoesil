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


def _assigns_engine_attr(node):
    """`mod.x = …`·`self.mod.x = …`·`cls.mod.x = …` 가 있나 — 엔진 전역을 바꿔 끼우는 꼴."""
    for a in ast.walk(node):
        targets = a.targets if isinstance(a, ast.Assign) else [a.target] if isinstance(a, (ast.AugAssign, ast.AnnAssign)) else []
        for t in targets:
            if isinstance(t, ast.Attribute):
                v = t.value
                if (isinstance(v, ast.Name) and v.id == 'mod') or (isinstance(v, ast.Attribute) and v.attr == 'mod'):
                    return True
    return False


class Grouping(unittest.TestCase):
    def test_대상_클래스는_한_그룹이다(self):
        import importlib
        for stem, names in SHARED.items():
            m = importlib.import_module(f'tests.{stem}')
            for name in names:
                self.assertEqual(getattr(getattr(m, name), 'render_group', None), GROUP, f'{stem}::{name}')

    def test_대상_클래스는_공용_사본을_쓴다(self):
        for stem, names in SHARED.items():
            classes = _classes(stem)
            for name in names:
                nodes = _with_bases(classes, name)
                self.assertTrue(_calls(nodes, 'engine'), f'{stem}::{name} 가 _renders.engine() 을 안 부른다')
                self.assertFalse(_calls(nodes, '_load'), f'{stem}::{name} 가 아직 _load() 로 새 사본을 만든다')

    def test_공용_사본을_쓰는_클래스는_엔진_전역을_바꾸지_않는다(self):
        for stem in SHARED:
            classes = _classes(stem)
            for name in classes:
                nodes = _with_bases(classes, name)
                if _calls(nodes, 'engine'):
                    self.assertFalse(any(_assigns_engine_attr(n) for n in nodes),
                                     f'{stem}::{name} 는 공용 엔진의 전역을 바꾼다 — 각자 _load() 하라')


class CacheKey(unittest.TestCase):
    render_group = GROUP     # 같은 워커의 공용 캐시를 쓰므로 이 시험 자체는 거의 공짜다

    def test_기본_λ_와_엔진_λ_가_같은_경로를_쓴다(self):
        mod = _renders.engine()
        b = mod.load_board_file(TRIAL, 'board_v2_e4')
        self.assertIs(b._dmux_paths(None), b._dmux_paths(mod.DENSITY_WEIGHT))


if __name__ == '__main__':
    unittest.main()
