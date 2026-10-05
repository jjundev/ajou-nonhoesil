"""결선도 엔진은 진입점 `render_breadboard.py` 와 `engine/` 조각들이다.

진입점이 조각을 `_PARTS` 순서대로 **자기 이름공간에서** 실행한다 — 엔진을 부를 때마다 독립 사본이어야 하는
계약(`test_breadboard_boards.py` `test_주차_파일은_불러온_엔진의_클래스를_쓴다`)을 지키려고 패키지로 나누지
않았다(`docs/plans/2026-10-05-결선도-엔진-나누기-설계.md`).
"""
import ast
import importlib.util
import os
import subprocess
import sys
import tempfile
import traceback
import unittest

from tests._boards import ENGINE, engine_files

ENGINE_DIR = ENGINE.parent / "engine"


def _load(name="render_breadboard"):
    spec = importlib.util.spec_from_file_location(name, ENGINE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class EngineFiles(unittest.TestCase):
    def test_진입점이_맨_앞이고_다_있다(self):
        files = engine_files()
        self.assertEqual(files[0], ENGINE)
        self.assertTrue(all(p.exists() for p in files), files)


class EngineParts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    def test_조각_목록이_폴더와_같다(self):
        """조각을 만들고 `_PARTS` 에 안 넣으면 그 이름은 처음 부를 때에야 NameError 다."""
        self.assertEqual(sorted(p.name for p in ENGINE_DIR.glob("*.py")), sorted(self.mod._PARTS))
        self.assertEqual(len(engine_files()), 1 + len(self.mod._PARTS))
        self.assertFalse((ENGINE_DIR / "__init__.py").exists(), "조각 폴더는 패키지가 아니다")

    def test_진입점은_로더와_CLI_만_남는다(self):
        src = ENGINE.read_text(encoding="utf-8")
        self.assertLessEqual(len(src.splitlines()), 320)
        self.assertEqual([n.name for n in ast.parse(src).body if isinstance(n, ast.ClassDef)], [])

    def test_조각은_머리에_단독_import_금지를_적는다(self):
        for p in engine_files()[1:]:
            with self.subTest(p.name):
                head = p.read_text(encoding="utf-8").splitlines()[:3]
                self.assertTrue(head[0].startswith("# 결선도 엔진 조각"), head)
                self.assertIn("단독으로 import 하지 않는다", "\n".join(head))

    def test_사본마다_상태가_따로다(self):
        a, b = self.mod, _load("rb_other_parts")
        self.assertIsNot(a.BreadboardRenderer, b.BreadboardRenderer)
        self.assertIsNot(a._ORDERED, b._ORDERED)
        self.assertIsNot(a._PLACE_PATHS, b._PLACE_PATHS)
        self.assertIsNot(a._PLACE_HINTS, b._PLACE_HINTS)
        saved = b._routes
        b._routes = lambda *args, **kw: iter(())
        try:
            self.assertIsNot(a._routes, b._routes)
            self.assertIs(b.route_plan.__globals__["_routes"], b._routes,
                          "바꿔 끼운 전역이 조각 함수에 닿아야 한다")
        finally:
            b._routes = saved

    def test_예외는_조각_파일을_가리킨다(self):
        try:                     # assertRaises 는 traceback 을 지워 두므로 직접 잡는다
            self.mod.dip_pins("74HC999", strict=True)
        except ValueError as e:
            tb = e.__traceback__
        else:
            self.fail("모르는 칩은 ValueError")
        last = traceback.extract_tb(tb)[-1]
        self.assertTrue(last.filename.endswith(os.path.join("engine", "router.py")), last.filename)
        self.assertIn("raise ValueError", last.line)

    def test_검사_메서드는_RuleChecks_에_있다(self):
        R, C = self.mod.BreadboardRenderer, self.mod._RuleChecks
        self.assertIs(R.__mro__[1], C)
        for name in ("verify", "nets", "wiring", "marker_problems", "side_leads"):
            with self.subTest(name):
                self.assertIn(name, vars(C))
                self.assertNotIn(name, vars(R))
                self.assertTrue(callable(getattr(R, name)))
        for name in ("step_wire", "_auto_marker", "_settle_marker", "export", "content"):
            with self.subTest(name):
                self.assertIn(name, vars(R))

    def test_저장소_밖_cwd_에서도_불러온다(self):
        code = ("import importlib.util, sys\n"
                f"spec = importlib.util.spec_from_file_location('render_breadboard', {str(ENGINE)!r})\n"
                "m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)\n"
                "print(m.BreadboardRenderer.__mro__[1].__name__, callable(m.place_plan))\n")
        env = {**os.environ, "PYTHONIOENCODING": "utf-8"}   # Windows 파이프 기본은 cp949 — 한글 도움말
        with tempfile.TemporaryDirectory() as d:
            r = subprocess.run([sys.executable, "-c", code], cwd=d, capture_output=True, text=True,
                               encoding="utf-8", env=env)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(r.stdout.strip(), "_RuleChecks True")
            r = subprocess.run([sys.executable, str(ENGINE), "--help"], cwd=d, capture_output=True,
                               text=True, encoding="utf-8", env=env)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("--experiment", r.stdout)


if __name__ == '__main__':
    unittest.main()
