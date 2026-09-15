"""주차 결선 파일(`보고서/실험NN/결선도/배치.py`)의 로더·일괄 렌더.

설계: docs/plans/2026-09-15-결선도-엔진-주차분리-설계.md
"""
import ast
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.lab import config

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".claude/skills/breadboard-diagram/scripts/render_breadboard.py"
FIXTURE = ROOT / "tests/fixtures/board_min/배치.py"


def _load(name="render_breadboard"):
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Loader(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    def test_주차_파일은_불러온_엔진의_클래스를_쓴다(self):
        """테스트 스파이가 `mod.BreadboardRenderer` 에 걸리려면 같은 객체여야 한다."""
        board = self.mod.load_board_file(FIXTURE)
        self.assertIs(board.BreadboardRenderer, self.mod.BreadboardRenderer)
        other = _load("rb_other")
        self.assertIsNot(other.BreadboardRenderer, self.mod.BreadboardRenderer)
        self.assertIs(other.load_board_file(FIXTURE).BreadboardRenderer, other.BreadboardRenderer)

    def test_불러온_뒤_sys_modules_를_되돌린다(self):
        before = sys.modules.get("render_breadboard")
        self.mod.load_board_file(FIXTURE)
        self.assertIs(sys.modules.get("render_breadboard"), before)

    def test_바이트코드를_남기지_않는다(self):
        """보고서 폴더에 `__pycache__` 가 생기면 안 된다."""
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "배치.py"
            p.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
            self.mod.load_board_file(p)
            self.assertFalse((Path(d) / "__pycache__").exists())

    def test_board_path_는_config_의_실험_폴더를_따른다(self):
        self.assertEqual(Path(self.mod.board_path(3)),
                         ROOT / config.experiment_dir(3) / "결선도" / "배치.py")

    def test_board_numbers_는_실험_폴더_이름을_config_로_되돌려_센다(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d) / config.EXPERIMENT_BASE
            for name in (config.experiment_folder_name(4), config.experiment_folder_name(2),
                         "실험4", "메모"):
                (base / name / "결선도").mkdir(parents=True)
                (base / name / "결선도" / "배치.py").write_text("", encoding="utf-8")
            self.assertEqual(self.mod.board_numbers(root=d), [2, 4])


class BuildAll(unittest.TestCase):
    def test_사슬과_완성본을_전부_뽑는다(self):
        mod = _load()
        with tempfile.TemporaryDirectory() as d:
            made = mod.build_all(mod.load_board_file(FIXTURE), d)
            self.assertEqual(sorted(made), ["min.png", "min_1단계_잭.png"])
            self.assertEqual(sorted(os.listdir(d)), ["min.png", "min_1단계_잭.png"])


class RealBoards(unittest.TestCase):
    """세 주차의 결선이 실험 폴더로 옮겨 갔고, 엔진에는 주차 이름이 없다."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    def test_세_주차의_결선_파일이_있다(self):
        self.assertTrue({1, 2, 3} <= set(self.mod.board_numbers()), self.mod.board_numbers())

    def test_주차_파일은_BOARDS_와_FINALS_를_낸다(self):
        for n in self.mod.board_numbers():
            with self.subTest(실험=n):
                board = self.mod.load_board(n)
                self.assertTrue(all(len(t) == 3 for t in board.BOARDS), board.BOARDS)
                self.assertTrue(all(len(t) == 2 for t in board.FINALS), board.FINALS)

    def test_엔진은_주차_결선을_정의하지_않는다(self):
        tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
        names = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
        names += [t.id for n in tree.body if isinstance(n, ast.Assign)
                  for t in n.targets if isinstance(t, ast.Name)]
        bad = [n for n in names if n.startswith(("build_e", "_e1_", "_e2_", "_e3_"))
               or n[:1] == "E" and n[1:2].isdigit()]
        self.assertEqual(bad, [])


class Cli(unittest.TestCase):
    def _run(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *args],
                              capture_output=True, text=True, cwd=ROOT)

    def test_experiment_로_그_주차를_전부_뽑는다(self):
        board = _load().load_board(2)
        want = sorted([n for n, _f, _s in board.BOARDS] + [n for n, _f in board.FINALS])
        with tempfile.TemporaryDirectory() as d:
            r = self._run("--experiment", "2", "--output", d)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(sorted(os.listdir(d)), want)

    def test_circuit_는_없다(self):
        r = self._run("--circuit", "e3_all", "--output", tempfile.gettempdir())
        self.assertEqual(r.returncode, 2, r.stderr)

    def test_결선_파일이_없는_실험은_거절한다(self):
        free = sorted(set(range(1, config.EXPERIMENT_COUNT + 1)) - set(_load().board_numbers()))
        r = self._run("--experiment", str(free[-1]))
        self.assertEqual(r.returncode, 2)
        self.assertIn("주차 결선 파일이 없다", r.stderr)


if __name__ == "__main__":
    unittest.main()
