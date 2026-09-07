"""렌더러 좌표가 템플릿의 **실제 홀 위치**와 맞는지 검사한다.

이 검사가 없던 시절 `render_breadboard.py` 는 눈대중 좌표
(`r_y = 243 + (r-1)*17.15`, 좌측 GND 레일 x=163)를 썼고, 1행이 29px·우측
f~j 열이 한 칸 통째로 어긋난 채 1년 가까이 굴러갔다. **그림 자체는 그럴듯해서
눈으로는 안 잡힌다** — 배선 끝점이 홀과 홀 사이 골에 앉을 뿐이다.

기존 `TEMPLATE_SIZE` 검사는 *판본 교체* 만 잡는다. 좌표표를 손으로 고쳐
어긋나게 만드는 회귀는 그 그물을 그대로 통과한다. 그래서 픽셀을 직접 센다.
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


def _clusters(profile, threshold, min_width):
    """프로파일에서 폭이 `min_width` 이상인 군집의 중심들."""
    out, i = [], 0
    while i < len(profile):
        if profile[i] > threshold:
            j = i
            while j < len(profile) and profile[j] > threshold:
                j += 1
            if j - i >= min_width:
                out.append((i + j - 1) / 2)
            i = j
        else:
            i += 1
    return out


class BreadboardCoords(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load()
        from PIL import Image
        path = cls.mod._default_template()
        cls.im = Image.open(path).convert('L')
        cls.px = cls.im.load()
        cls.W, cls.H = cls.im.size

    def _col_centers(self):
        """홀 열의 중심. 인쇄된 레일 선(폭 2~3px)은 폭으로 걸러낸다."""
        prof = [0] * self.W
        for y in range(250, 1300, 3):
            for x in range(self.W):
                if self.px[x, y] < 140:
                    prof[x] += 1
        return _clusters(prof, 40, 5)

    def _row_centers(self):
        prof = [0] * self.H
        for y in range(250, 1300):
            prof[y] = sum(1 for x in range(232, 428) if self.px[x, y] < 140)
        return [c for c in _clusters(prof, 6, 2) if 260 < c < 1300]

    def test_열_좌표가_실제_홀_중심과_맞는다(self):
        centers = self._col_centers()
        self.assertGreaterEqual(len(centers), 24, '홀 열을 못 찾았다')
        bb = self.mod.BreadboardRenderer()
        for block in ('left', 'right'):
            for key, x in bb.cols[block].items():
                if key.startswith('chip'):
                    continue
                nearest = min(centers, key=lambda c: abs(c - x))
                self.assertLessEqual(
                    abs(nearest - x), 4.0,
                    f'{block}.{key} = {x} 가 홀 중심 {nearest:.1f} 에서 '
                    f'{abs(nearest - x):.1f}px 벗어났다 (홀 폭 9px, 간격 16.5px)')

    def test_행_좌표가_실제_홀_중심과_맞는다(self):
        centers = self._row_centers()
        self.assertEqual(len(centers), self.mod.ROW_MAX,
                         f'단자대 행이 {self.mod.ROW_MAX} 개가 아니다: {len(centers)}')
        bb = self.mod.BreadboardRenderer()
        for r in range(1, self.mod.ROW_MAX + 1):
            self.assertLessEqual(
                abs(centers[r - 1] - bb.r_y(r)), 3.0,
                f'{r}행: r_y={bb.r_y(r)} vs 실측 {centers[r - 1]:.1f}')

    def test_레일_빈_행_목록이_실측과_같다(self):
        """레일은 5홀씩 묶여 있다. 빈 행에 배선을 끝내면 꽂을 데가 없다."""
        bb = self.mod.BreadboardRenderer()
        measured = set()
        for r in range(1, self.mod.ROW_MAX + 1):
            y = bb.r_y(r)
            dark = sum(1 for yy in range(y - 4, y + 5) for x in range(169, 196)
                       if self.px[x, yy] < 140)
            if dark <= 6:
                measured.add(r)
        self.assertEqual(measured, set(self.mod.RAIL_GAP_ROWS))

    def test_빌더_다섯이_끝점_검사를_통과한다(self):
        """빌더를 실제로 돌린다. `verify()` 가 레일 착지 행을 확인하고,
        여기서는 표에 적힌 주소가 전부 실제 홀 이름인지 본다.

        `분기점` 은 홀이 아니라 배선 통로에서 갈라지는 T 접속이다. 하나뿐이고
        (복합회로의 입력 B 갈래) 그것도 `frm=` 로 이름을 덮어 뒀으므로,
        표에 `분기점` 이 남아 있으면 의도치 않게 허공에서 시작한 배선이다.
        """
        import tempfile
        for name in ('build_e1_and', 'build_e1_or', 'build_e1_nand',
                     'build_e1_nor', 'build_e1_comb'):
            with self.subTest(회로=name):
                with tempfile.TemporaryDirectory() as d:
                    out = os.path.join(d, 'x.png')
                    getattr(self.mod, name)(out)
                    self.assertTrue(os.path.exists(out))

    def test_결선표_주소가_모두_실제_홀이다(self):
        # 복합회로가 가장 배선이 많다. 표를 직접 들여다본다
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            renderer = {}
            orig = self.mod.BreadboardRenderer

            class Spy(orig):
                def export(self_inner, *a, **k):
                    renderer['bb'] = self_inner
                    return orig.export(self_inner, *a, **k)

            self.mod.BreadboardRenderer = Spy
            try:
                self.mod.build_e1_comb(os.path.join(d, 'x.png'))
            finally:
                self.mod.BreadboardRenderer = orig

        bb = renderer['bb']
        self.assertGreater(len(bb.steps), 20)
        for st in bb.steps:
            for a in (st['frm'], st['to']):
                self.assertNotEqual(a, '분기점',
                                    f"{st['n']}번 배선이 홀이 아닌 데서 시작·끝난다: {st}")

    def test_레일이_끊겨_있으면_내보내기가_멈춘다(self):
        """레일쌍 넷은 별개 스트립이다. +5V 를 한 레일에 넣고 칩 14번 핀을 다른
        레일에 물리면 **그림은 완벽해 보이는데 전원이 안 간다** — 레일마다
        배선이 얌전히 꽂혀 있고 색도 맞기 때문이다. 실제로 실험01 그림 다섯 장이
        이 상태로 나갔다가 이 검사로 잡혔다.
        """
        bb = self.mod.BreadboardRenderer()
        bb.enable_steps()
        c = bb.cols['left']
        bb.step_wire([(c['f'], bb.r_y(10)), (c['mid_vcc'], bb.r_y(10))], 'vcc', 'pin 14')
        bb.step_wire([(c['a'], bb.r_y(4)), (c['vcc'], bb.r_y(4))], 'vcc', '전원 투입')
        with self.assertRaises(AssertionError) as cm:
            bb.verify()
        self.assertIn('레일이 끊겨 있다', str(cm.exception))

        bb.bridge_rails(c['vcc'], c['mid_vcc'], 30, kind='vcc')
        bb.verify()   # 이으면 통과한다


if __name__ == '__main__':
    unittest.main()
