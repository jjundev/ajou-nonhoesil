"""느린 v2 시험판 시험이 엔진 사본 하나를 나눠 쓰는지 본다.

경로 캐시(`_PLACE_PATHS`)는 엔진 사본마다 있어서, 시험마다 엔진을 새로 로드하면 MUX 경로 탐색
(약 28초)을 매번 다시 한다. 설계: `docs/plans/2026-10-05-느린-배선-테스트-엔진-공유-설계.md`.
"""
import importlib.util
import unittest

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


if __name__ == '__main__':
    unittest.main()
