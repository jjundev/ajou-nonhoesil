"""렌더러가 이 머신의 폰트로 뜨는지 본다.

2026-09-12 까지 `BreadboardRenderer.__init__` 은 macOS 경로
(`/System/Library/Fonts/AppleSDGothicNeo.ttc`)를 박아 두어 Windows 에서는
`OSError: cannot open resource` 로 렌더러 테스트 165건이 통째로 죽었다.

2026-09-19 에는 더 조용한 사고가 있었다 — Windows 에서 고른 맑은 고딕에 U+2295 `⊕`
가 없어 결선도 부제가 `(A□B)·Ci` 로 나갔다. 터지지 않으니 테스트도 몰랐다. 그래서
"뜨는가" 만이 아니라 "필요한 글자를 그리는가" 까지 여기서 본다.
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

    def test_고른_한글_폰트가_필요한_글자를_다_그린다(self):
        """`⊕→·☐※` — 결선도가 실제로 찍는 기호들. 하나라도 없으면 □ 로 나간다."""
        chosen = self.mod.font_path('kr')
        for ch in self.mod.REQUIRED_GLYPHS['kr']:
            with self.subTest(ch=ch):
                self.assertTrue(self.mod._covers(chosen, ch), f'{chosen} 에 {ch} 가 없다')

    def test_맑은_고딕은_동그라미더하기가_없어_밀린다(self):
        """2026-09-19 사고의 장본인. `_covers` 가 이걸 못 잡으면 규칙이 무의미하다."""
        malgun = 'C:/Windows/Fonts/malgun.ttf'
        if not os.path.exists(malgun):
            self.skipTest('이 머신에 맑은 고딕이 없다')
        self.assertTrue(self.mod._covers(malgun, '가'), '한글은 되는 폰트여야 대조가 된다')
        self.assertFalse(self.mod._covers(malgun, '⊕'))
        self.assertNotEqual(self.mod.font_path('kr'), malgun)


if __name__ == '__main__':
    unittest.main()
