"""결선도 엔진은 진입점 `render_breadboard.py` 와 `engine/` 조각들이다.

진입점이 조각을 `_PARTS` 순서대로 **자기 이름공간에서** 실행한다 — 엔진을 부를 때마다 독립 사본이어야 하는
계약(`test_breadboard_boards.py` `test_주차_파일은_불러온_엔진의_클래스를_쓴다`)을 지키려고 패키지로 나누지
않았다(`docs/plans/2026-10-05-결선도-엔진-나누기-설계.md`).
"""
import unittest

from tests._boards import ENGINE, engine_files


class EngineFiles(unittest.TestCase):
    def test_진입점이_맨_앞이고_다_있다(self):
        files = engine_files()
        self.assertEqual(files[0], ENGINE)
        self.assertTrue(all(p.exists() for p in files), files)


if __name__ == '__main__':
    unittest.main()
