"""브레드보드 v2 판형 — 판형 산출물·사양·가운데 레일 공유·블록 역할(R9·R10)·계약·연기 시험.

설계: docs/plans/2026-10-02-브레드보드-v2-구조-설계.md
구현계획: docs/plans/2026-10-03-브레드보드-v2-구현계획.md
v1(실험01~04)이 바이트 하나 안 바뀌는 것은 기존 테스트(`test_breadboard_boards` 의 도장·사이드카
대조)가 지킨다. 여기는 v2 와, v1·v2 가 갈리는 자리를 본다.
"""
import hashlib
import importlib.util
import json
import os
import shutil
import tempfile
import types
import unittest
from dataclasses import replace
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".claude/skills/breadboard-diagram/scripts/render_breadboard.py"
V2_DIR = ROOT / ".claude/assets/breadboard_v2"
GEOMETRY = V2_DIR / "geometry.json"
SMOKE = ROOT / "tests/fixtures/board_v2/배치.py"


def _load(name="render_breadboard"):
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class V2Template(unittest.TestCase):
    """판형 산출물 — 1배 PNG, 해시, 잭 글자 자리. 판형을 다시 뽑으면 여기서 걸린다."""

    def setUp(self):
        self.g = json.loads(GEOMETRY.read_text(encoding="utf-8"))
        self.png = V2_DIR / self.g["png"]

    def test_PNG_는_1배다(self):
        """2배로 뽑으면 레일 극성선이 4px 가 되어 손그림 검토가 레일 열을 6.5px 밀어 잡는다."""
        with Image.open(self.png) as im:
            self.assertEqual(im.size, (1200, 1600))
        self.assertEqual(self.g["export_scale"], 1)

    def test_해시가_geometry_와_같다(self):
        self.assertEqual(hashlib.sha256(self.png.read_bytes()).hexdigest(), self.g["png_sha256"])

    def test_잭_글자는_잭_왼쪽에_있고_아래는_비어_있다(self):
        """잭 전원선은 잭 아래로 곧장 내려간다 — 글자가 아래 있으면 선이 덮는다(2026-10-03 사용자)."""
        with Image.open(self.png) as im:
            im = im.convert("RGB")
            bg = im.getpixel((5, 5))
            for j in self.g["jacks"]:
                if j["name"] == "yellow":
                    continue
                cx, cy, bottom = j["center_x"], j["center_y"], j["bottom_y"]
                r = bottom - cy
                below = [im.getpixel((x, y)) for x in range(cx - 20, cx + 21)
                         for y in range(bottom + 4, bottom + 41)]
                self.assertTrue(all(p == bg for p in below), f"{j['name']} 잭 아래에 그림이 있다")
                left = [im.getpixel((x, y)) for x in range(cx - r - 60, cx - r - 3)
                        for y in range(cy - 10, cy + 11)]
                self.assertTrue(any(sum(p) < 300 for p in left), f"{j['name']} 글자가 잭 왼쪽에 없다")


if __name__ == "__main__":
    unittest.main()
