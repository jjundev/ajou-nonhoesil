"""주차 결선 파일(`보고서/실험NN/결선도/배치.py`)의 로더·일괄 렌더.

설계: docs/plans/2026-09-15-결선도-엔진-주차분리-설계.md
"""
import importlib.util
import os
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


if __name__ == "__main__":
    unittest.main()
