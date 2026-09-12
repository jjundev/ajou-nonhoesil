"""렌더러가 이 머신의 폰트로 뜨는지 본다.

2026-09-12 까지 `BreadboardRenderer.__init__` 은 macOS 경로
(`/System/Library/Fonts/AppleSDGothicNeo.ttc`)를 박아 두어 Windows 에서는
`OSError: cannot open resource` 로 렌더러 테스트 165건이 통째로 죽었다.
"""
import importlib.util
import os
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO_ROOT, '.claude', 'skills', 'breadboard-diagram',
                      'scripts', 'render_breadboard.py')


def _load():
    spec = importlib.util.spec_from_file_location('render_breadboard', SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Fonts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    def test_한글_영문_후보가_있다(self):
        self.assertEqual(set(self.mod.FONT_CANDIDATES), {'kr', 'en'})

    def test_font_path_는_실재하는_파일을_준다(self):
        for kind in ('kr', 'en'):
            with self.subTest(kind=kind):
                self.assertTrue(os.path.exists(self.mod.font_path(kind)))

    def test_모르는_kind_는_거절한다(self):
        with self.assertRaises(KeyError):
            self.mod.font_path('emoji')

    def test_렌더러가_이_머신에서_뜬다(self):
        bb = self.mod.BreadboardRenderer()
        self.assertIsNotNone(bb.font_title)


if __name__ == '__main__':
    unittest.main()
