"""결선도가 **그림대로 꽂히는가**를 렌더러가 내보내기 전에 증명하는지 검사한다.

2026-09-07 에 발견: 입력 A·B·C 가 보드 밖 x=95 허공에서 출발하고 있었다.
`addr()` 이 그 자리에 '보드밖(입력)' 이라는 이름을 붙여 주었고, `verify()` 는
docstring 과 달리 레일 끝점의 빈 행만 봤다. 그림도 순서표도 멀쩡해 보였다 —
따라 그리던 사람이 왼쪽 끝을 어디에 꽂아야 할지 몰라서 걸렸다.

합성 보드에 배선 한두 줄을 그리고 `verify()` 만 부른다. 파일을 쓰지 않아
빠르고, 어느 규칙이 잡았는지 메시지로 확인한다.
"""
import importlib.util
import os
import tempfile
import unittest

from tests._boards import all_builders

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO_ROOT, '.claude', 'skills', 'breadboard-diagram',
                      'scripts', 'render_breadboard.py')


def _load():
    spec = importlib.util.spec_from_file_location('render_breadboard', SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class PhysicalRules(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    def board(self):
        bb = self.mod.BreadboardRenderer()
        bb.enable_steps()
        return bb

    # ---- R1. 모든 끝점은 홀이다 ----

    def test_허공에서_출발한_배선은_막힌다(self):
        bb = self.board()
        c = bb.cols['left']
        bb.step_wire([(95, bb.r_y(10)), (c['b'], bb.r_y(10))], 'sig', '입력 A')
        with self.assertRaisesRegex(AssertionError, '홀이 아니다.*보드밖'):
            bb.verify()

    def test_레일_빈_행에_꽂은_끝점은_막힌다(self):
        bb = self.board()
        c = bb.cols['left']
        bb.step_wire([(c['gnd'], bb.r_y(14)), (c['b'], bb.r_y(14))], 'sig', '입력 C')
        with self.assertRaisesRegex(AssertionError, '홀이 아니다.*GND레일14행'):
            bb.verify()

    def test_전원잭은_보드_밖이어도_된다(self):
        bb = self.board()
        bb.connect_jacks()
        bb.verify()

    def test_홀_사이_골에_앉은_끝점은_홀이_아니다(self):
        # 열 피치가 16px 인데 허용치가 9px 였다 — 인접 열 사이에 '홀 아님' 이 없었다
        bb = self.board()
        c = bb.cols['left']
        self.assertEqual(bb.hole_at(c['c'], bb.r_y(10)), (c['c'], 10))
        self.assertIsNone(bb.hole_at(c['c'] + 8, bb.r_y(10)))
        self.assertIsNone(bb.hole_at(c['c'], bb.r_y(10) + 8))

    def test_잭이_아닌_보드_위쪽_허공은_면제되지_않는다(self):
        bb = self.board()
        c = bb.cols['left']
        bb.step_wire([(c['c'], 239), (c['c'], bb.r_y(10))], 'sig', '위에서 내려온 선')
        with self.assertRaisesRegex(AssertionError, '홀이 아니다'):
            bb.verify()

    # ---- R2. 한 홀에 리드 하나 ----

    def test_한_홀에_배선_둘은_막힌다(self):
        bb = self.board()
        c = bb.cols['left']
        bb.step_wire([(c['c'], bb.r_y(12)), (c['c'], bb.r_y(13))], 'mid', '1단 -> 2단')
        bb.step_wire([(c['c'], bb.r_y(12)), (c['a'], bb.r_y(12))], 'mid', '갈래')
        with self.assertRaisesRegex(AssertionError, '한 홀에 리드 둘.*좌 c12'):
            bb.verify()

    def test_레일_홀이_차면_가까운_빈_홀로_옮긴다(self):
        bb = self.board()
        c = bb.cols['left']
        bb.lead(c['gnd'], bb.r_y(7), '먼저 꽂힌 것')
        # 8행은 빈 행이고 7행은 찼다 -> 9행
        self.assertEqual(bb.free_rail_row(8, c['gnd']), 9)
        self.assertEqual(bb.free_rail_row(10, c['gnd']), 10)
        # 두 열을 같이 주면 둘 다 비어야 한다
        bb.lead(c['mid_gnd'], bb.r_y(31), '브리지 끝')
        self.assertEqual(bb.free_rail_row(31, c['mid_gnd'], c['mid_vcc']), 30)

    # ---- R4. 서로 다른 배선이 같은 축 위에 포개지지 않는다 ----

    def test_다른_색_배선이_한_줄에_포개지면_막힌다(self):
        # 2026-09-07 실험 1-1 의 원형: 입력 C 의 세로 구간이 초록 중간단 선에 덮여
        # pin 3 이 pin 5 로 들어가는 다른 회로로 읽혔다
        bb = self.board()
        c = bb.cols['left']
        bb.step_wire([(c['a'], bb.r_y(7)), (c['a'], bb.r_y(14))], 'sig', '입력 C')
        bb.step_wire([(c['a'], bb.r_y(12)), (c['a'], bb.r_y(19))], 'mid', '중간단 갈래')
        # `.` 은 줄바꿈을 못 넘는다 — 메시지가 '포개졌다:\n  세로 …' 꼴이라 \s+ 로 잇는다
        with self.assertRaisesRegex(AssertionError, '포개졌다:\\s+세로'):
            bb.verify()

    def test_같은_색_밑동은_R4_가_봐주지만_R3_가_잡는다(self):
        # 옛 복합 회로의 B 갈래: a19 에 꽂은 두 번째 점퍼가 입력선(레일→b19) 위를
        # 27px 되짚어 여백(x=212)으로 나갔다. R4 는 두 홀 폭 안의 같은 색 포개짐을
        # 밑동으로 봐주지만, 그 밑동의 끝점 a19 는 입력선 **중간**에 놓인다 —
        # 그림에서는 얇은 선이 굵은 선 중간에서 솟는 것으로 보였다 (2026-09-08).
        bb = self.board()
        c = bb.cols['left']
        bb.step_wire([(c['gnd'], bb.r_y(19)), (c['b'], bb.r_y(19))], 'sig', '입력 B')
        bb.step_wire([(c['a'], bb.r_y(19)), (212, bb.r_y(19)), (212, bb.r_y(5)), (c['a'], bb.r_y(5))],
                     'sig', '갈래')
        self.assertEqual(bb._overlaps(), [])
        with self.assertRaisesRegex(AssertionError, '끝점이 다른 배선 아래.*좌 a19'):
            bb.verify()

    # ---- R3. 끝점 위를 다른 배선이 지나가지 않는다 ----

    def test_옆_홀에_나란히_끝나는_두_점퍼는_괜찮다(self):
        # 고친 뒤의 모양: 입력선은 a19 에서 멈추고 갈래는 b19 에서 세로로 나간다
        bb = self.board()
        c = bb.cols['left']
        bb.step_wire([(c['gnd'], bb.r_y(19)), (c['a'], bb.r_y(19))], 'sig', '입력 B')
        bb.step_wire([(c['b'], bb.r_y(19)), (c['b'], bb.r_y(12)), (228, bb.r_y(12)), (228, bb.r_y(6)),
                      (c['c'], bb.r_y(6))], 'sig', '갈래')
        bb.verify()

    def test_같은_넷이라도_끝점_위를_지나면_막힌다(self):
        # 옛 AND 회로: pin 3→4 점퍼가 c12 에서 끝나는데 같은 넷의 갈래가 d12 에서
        # a12 로 가며 c12 위를 지났다. T 접속으로 읽히지만 점퍼는 이어 붙일 수 없다
        bb = self.board()
        c = bb.cols['left']
        bb.step_wire([(c['c'], bb.r_y(12)), (c['c'], bb.r_y(13))], 'mid', 'pin 3 -> pin 4')
        bb.step_wire([(c['d'], bb.r_y(12)), (c['a'], bb.r_y(12))], 'mid', '갈래')
        with self.assertRaisesRegex(AssertionError, '끝점이 다른 배선 아래.*좌 c12'):
            bb.verify()

    def test_대각선_아래_깔린_끝점도_잡는다(self):
        bb = self.board()
        c = bb.cols['left']
        # g8 → 중앙GND 6행 대각선이 j7 근처를 지난다. 그 선 위의 한 점에 끝점을 둔다
        x0, y0, x1, y1 = c['g'], bb.r_y(8), c['mid_gnd'], bb.r_y(6)
        bb.step_wire([(x0, y0), (x1, y1)], 'gnd', '대각 접지선')
        t = (c['j'] - x0) / (x1 - x0)
        y_on = y0 + (y1 - y0) * t
        self.assertLess(abs(y_on - bb.r_y(7)), 5, '픽스처: j7 홀이 대각선 위에 있어야 한다')
        bb.step_wire([(c['j'], bb.r_y(7)), (c['j'], bb.r_y(9))], 'sig', 'j7 에서 출발')
        with self.assertRaisesRegex(AssertionError, '끝점이 다른 배선 아래.*좌 j7'):
            bb.verify()

    def test_칩_핀_홀_위를_지나는_것은_봐준다(self):
        # 칩을 가로지르는 선은 핀 행을 지날 수밖에 없다. e10·f10 은 핀 홀이다
        bb = self.board()
        c = bb.cols['left']
        bb.draw_chip('74HC04', 7)
        # R3 만 보는 조각 보드다 — 핀을 하나도 안 물렸으니 R5 의 뜬 핀 검사는 끈다
        bb.partial = True
        bb.step_wire([(c['b'], bb.r_y(10)), (c['mid_gnd'], bb.r_y(10))], 'mid', '칩 가로지르기')
        bb.verify()

    def test_부품_다리_위를_지나면_막힌다(self):
        bb = self.board()
        c = bb.cols['left']
        bb.draw_resistor(c['c'], bb.r_y(20), bb.r_y(22))
        bb.step_wire([(c['c'], bb.r_y(15)), (c['c'], bb.r_y(24))], 'sig', '저항 위를 지나는 선')
        with self.assertRaisesRegex(AssertionError, '끝점이 다른 배선 아래.*윗다리'):
            bb.verify()

    def test_레일_홀_위를_지나간_선이_있으면_착지를_비킨다(self):
        # pin 14 전원선(g7 → 중앙VCC 7행)은 중앙GND 7행 홀 위를 지난다.
        # 8행(빈 행)의 핀 접지선은 7행이 아니라 9행에 착지해야 한다
        bb = self.board()
        c = bb.cols['left']
        bb.step_wire([(c['g'], bb.r_y(7)), (c['mid_vcc'], bb.r_y(7))], 'vcc', 'pin 14')
        self.assertIn((c['mid_gnd'], 7), bb._passed)
        self.assertEqual(bb.free_rail_row(8, c['mid_gnd']), 9)

    def test_경고_모드는_R4_를_기록만_하고_R3_는_그래도_던진다(self):
        # 축 위 포개짐은 언제나 한쪽 끝점이 상대 구간 안에 있다 — R3 가 잡는다.
        # 경고 모드는 R4 문구만 낮추고, 그래도 overlap_warnings 는 채워진다
        bb = self.board()
        bb.overlap_policy = 'warn'
        c = bb.cols['left']
        bb.step_wire([(c['a'], bb.r_y(7)), (c['a'], bb.r_y(14))], 'sig', '입력 C')
        bb.step_wire([(c['a'], bb.r_y(12)), (c['a'], bb.r_y(19))], 'mid', '중간단 갈래')
        with self.assertRaisesRegex(AssertionError, '끝점이 다른 배선 아래.*좌 a12'):
            bb.verify()
        self.assertEqual(len(bb.overlap_warnings), 1)

    def test_경고_목록은_이번_verify_의_결과로_덮인다(self):
        # ad06489 가 고친 시나리오: 포개짐이 사라진 뒤에도 옛 경고가 남았다
        bb = self.board()
        bb.overlap_policy = 'warn'
        bb.overlap_warnings = ['옛 경고']
        bb.connect_jacks()
        bb.verify()
        self.assertEqual(bb.overlap_warnings, [])

    # ---- R2. 부품 다리와 칩 핀도 홀을 차지한다 ----

    def test_칩_핀_홀에_배선을_꽂으면_막힌다(self):
        bb = self.board()
        c = bb.cols['left']
        bb.draw_chip('74HC08', 10)
        bb.step_wire([(c['f'], bb.r_y(10)), (c['mid_vcc'], bb.r_y(10))], 'vcc', 'pin 14')
        with self.assertRaisesRegex(AssertionError, '한 홀에 리드 둘.*74HC08 pin 14'):
            bb.verify()

    def test_LED_사슬은_다리마다_다른_홀을_쓴다(self):
        bb = self.board()
        c = bb.cols['left']
        # 이 판은 **일부러 덜 그린 조각**이다 — c15 에 칩이 없어 신호선 반대쪽이
        # 빈 스트립이다. R5 의 '아무 데도 안 물렸다' 갈래만 뺀다 (R1~R4 는 다 돈다)
        bb.partial = True
        bb.step_wire([(c['c'], bb.r_y(15)), (c['c'], bb.r_y(24))], 'sig', '출력 -> L2')
        bb.led_chain(c['c'], 24, 'L2', '최종 출력')
        bb.verify()
        self.assertEqual(bb._leads[(c['c'], 24)], '신호 배선 · 출력 -> L2')
        self.assertEqual(bb._leads[(c['d'], 24)], 'L2 LED 애노드')
        self.assertEqual(bb._leads[(c['d'], 25)], 'L2 LED 캐소드')
        self.assertEqual(bb._leads[(c['e'], 25)], '330Ω 윗다리')
        self.assertEqual(bb._leads[(c['e'], 27)], '330Ω 아랫다리')
        # GND 점퍼는 레일 쪽 끝 홀(c27)에서. LED 열(d27)에서 뽑으면 레일로 가는 길에
        # 다른 다리 위를 지나진 않지만, 레일 쪽 끝이 항상 아무것도 안 넘는 자리다
        self.assertIn((c['c'], 27), bb._leads)
        self.assertNotIn((c['d'], 27), bb._leads)

    def test_오른쪽_끝_열의_LED_사슬은_왼쪽으로_자란다(self):
        bb = self.board()
        c = bb.cols['right']
        bb.partial = True   # 위와 같은 조각 판이다 — d12 에 칩이 없다
        bb.step_wire([(c['d'], bb.r_y(12)), (c['d'], bb.r_y(22))], 'sig', 'pin 3 -> X')
        bb.led_chain(c['d'], 22, 'X', 'X 출력', block='right')
        bb.verify()
        self.assertEqual(bb._leads[(c['c'], 22)], 'X LED 애노드')
        self.assertEqual(bb._leads[(c['b'], 23)], '330Ω 윗다리')
        # 왼쪽으로 자란 사슬의 GND 점퍼는 저항 너머(a25)에서 — c25 나 d25 에서 뽑으면
        # 레일(542, 왼쪽)로 가는 가로선이 저항 아랫다리 b25 위를 지난다
        self.assertIn((c['a'], 25), bb._leads)
        self.assertNotIn((c['c'], 25), bb._leads)

    # ---- R7. 칩 한쪽에 리드가 몰리지 않는다 ----

    def _chip_with_side_leads(self, n, side='a'):
        """좌 7행 74HC08 의 한쪽 자유 열에 리드 n 개를 점유표로 직접 꽂는다.
        배선 기하는 R1~R6 몫이라 여기서는 `lead()` 만 쓴다. 핀은 안 물렸으니 partial."""
        bb = self.board()
        bb.draw_chip('74HC08', 7)
        bb.partial = True
        c = bb.cols['left']
        cols = self.mod.SIDE_COLS[side]
        for k in range(n):
            bb.lead(c[cols[k % 4]], bb.r_y(7 + k // 4), f'점퍼 {k}')
        return bb

    def test_칩_한쪽_8리드는_통과한다(self):
        self._chip_with_side_leads(8).verify()

    def test_칩_한쪽_9리드는_R7_로_막힌다(self):
        bb = self._chip_with_side_leads(9)
        with self.assertRaisesRegex(AssertionError, r'R7 칩 한쪽 밀집: 74HC08\(좌 7행\) 왼쪽 9리드 > 8: 좌 a7'):
            bb.verify()

    def test_오른쪽도_같은_한도다(self):
        bb = self._chip_with_side_leads(9, side='f')
        with self.assertRaisesRegex(AssertionError, r'오른쪽 9리드 > 8: 좌 g7'):
            bb.verify()

    def test_칩_핀과_지나가는_선은_R7_에_안_센다(self):
        """칩 핀 홀(e·f)은 칩 자신이고, 위를 지나는 선은 꽂는 것이 아니다."""
        bb = self._chip_with_side_leads(8)
        c = bb.cols['left']
        # d 열을 세로로 지나는 선 — d7~d8 은 꽂혀 있으니 옆 a~d 밖인 여백 x 로 우회하지 않고
        # 칩 아래 행에서 출발해 칩 위 행으로 간다(d9~d13 은 비어 있어 `_passed` 에만 든다)
        bb.step_wire([(c['d'], bb.r_y(16)), (c['d'], bb.r_y(9))], 'sig', '지나가는 선')
        self.assertEqual([s['count'] for s in bb.side_leads()], [9, 0])
        # d9 는 이 선의 **끝점**이라 리드다 — 9 가 됐으니 막힌다. 끝점을 d16→d15 로 바꾸면 통과
        with self.assertRaisesRegex(AssertionError, 'R7'):
            bb.verify()

    def test_legacy_정책은_R7_을_끈다(self):
        bb = self._chip_with_side_leads(11)
        bb.density_policy = 'legacy'
        bb.verify()

    def test_모르는_밀도_정책은_거절한다(self):
        bb = self._chip_with_side_leads(1)
        bb.density_policy = 'warn'
        with self.assertRaisesRegex(ValueError, 'density_policy'):
            bb.verify()

    # ---- 칩 오른쪽 게이트의 입력 점퍼 (R7 을 풀기 위한 헬퍼 분기) ----

    def _badge_covers_lead(self, bb, name):
        box = next(b for n, b, _s in bb.tag_boxes if n == name)
        return [what for (hx, hr), what in bb._leads.items()
                if box[0] <= hx <= box[2] and box[1] <= bb.r_y(hr) <= box[3]]

    def test_좌_블록_f쪽_입력은_중앙_GND_레일에서_i열로_들어간다(self):
        bb = self.board()
        c = bb.cols['left']
        bb.draw_chip('74HC08', 7)
        bb.partial = True
        # 11행 = pin1_row+4 = f 쪽 pin 10. (8행은 레일 빈 행이라 free_rail_row 가 7행으로
        # 옮긴다 — 레일 행 판정을 섞지 않으려고 홀이 있는 11행을 쓴다)
        self.mod._input_jumper(bb, c, 11, 'B', '74HC08 pin 10', side='f')
        bb.verify()
        kind, pts, desc = bb._segments[-1]
        self.assertEqual(bb.addr(*pts[0]), '좌 중앙GND레일11행')
        self.assertEqual(bb.addr(*pts[-1]), '좌 i11')
        self.assertEqual(bb.inputs[-1], {'name': 'B', 'at': ('left', 'i', 11), 'seg': len(bb._segments) - 1})
        self.assertEqual(self._badge_covers_lead(bb, 'B'), [])
        # 배지는 중앙 레일쌍 사이 여백(좌 중앙 VCC 484 ~ 우 중앙 GND 542)에 있다
        box = next(b for n, b, _s in bb.tag_boxes if n == 'B')
        self.assertGreater(box[0], c['mid_vcc'])
        self.assertLess(box[2], bb.cols['right']['mid_gnd'])
        # 순서표 문구는 a 쪽과 같은 틀이다 — 도장 규약을 f 쪽에서도 지킨다
        self.assertEqual(desc, '입력 B -> 74HC08 pin 10 · 1 이면 레일 쪽 끝을 +5V 레일로 옮긴다')

    def test_우_블록_f쪽_입력은_우_바깥_GND_레일에서_i열로_들어간다(self):
        bb = self.board()
        c = bb.cols['right']
        bb.draw_chip('74HC08', 10, block='right')
        bb.partial = True
        self.mod._input_jumper(bb, c, 11, 'A', '74HC08 pin 13', side='f')
        bb.verify()
        kind, pts, desc = bb._segments[-1]
        self.assertEqual(bb.addr(*pts[0]), '우 GND레일11행')
        self.assertEqual(bb.addr(*pts[-1]), '우 i11')
        box = next(b for n, b, _s in bb.tag_boxes if n == 'A')
        self.assertGreater(box[0], c['vcc'])
        self.assertLess(box[2], self.mod.BOARD_RIGHT)
        self.assertEqual(self._badge_covers_lead(bb, 'A'), [])

    def test_우_블록_a쪽_입력은_우_중앙_GND_레일에서_b열로_들어간다(self):
        bb = self.board()
        c = bb.cols['right']
        bb.draw_chip('74HC08', 10, block='right')
        bb.partial = True
        self.mod._input_jumper(bb, c, 10, 'A', '74HC08 pin 1')
        bb.verify()
        kind, pts, desc = bb._segments[-1]
        self.assertEqual(bb.addr(*pts[0]), '우 중앙GND레일10행')
        self.assertEqual(bb.addr(*pts[-1]), '우 b10')

    def test_좌_블록_a쪽_입력은_지금과_같다(self):
        """기존 주차의 호출 형태(`marker=(215, 13)`)가 그대로 도는지 — 도장 불변의 근거."""
        bb = self.board()
        c = bb.cols['left']
        bb.draw_chip('74HC08', 7)
        bb.partial = True
        self.mod._input_jumper(bb, c, 10, 'C', '74HC08 pin 4', marker=(215, 13))
        bb.verify()
        kind, pts, desc = bb._segments[-1]
        self.assertEqual(bb.addr(*pts[0]), '좌 GND레일10행')
        self.assertEqual(bb.addr(*pts[-1]), '좌 b10')
        self.assertEqual(desc, '입력 C -> 74HC08 pin 4 · 1 이면 레일 쪽 끝을 +5V 레일로 옮긴다')

    def test_f쪽_입력_레일도_레일_연결성_검사에_든다(self):
        """`kind='sig'` 라 `step_wire` 가 `touch_rail` 을 안 부른다 — 입력이 매달린
        레일이 접지 레일과 안 이어져 있어도 통과하던 자리(2026-09-20 최종리뷰)."""
        bb = self.board()
        bb.draw_chip('74HC08', 10, block='right')
        bb.partial = True
        bb.connect_jacks()  # 잭은 좌 바깥 레일에 꽂힌다
        self.mod._input_jumper(bb, bb.cols['right'], 11, 'A', '74HC08 pin 13', side='f')
        with self.assertRaisesRegex(AssertionError, '레일이 끊겨 있다'):
            bb.verify()

    def test_f쪽_입력_레일을_브리지로_이으면_통과한다(self):
        bb = self.board()
        bb.draw_chip('74HC08', 10, block='right')
        bb.partial = True
        bb.connect_jacks()
        self.mod._input_jumper(bb, bb.cols['right'], 11, 'A', '74HC08 pin 13', side='f')
        bb.bridge_rails(bb.cols['left']['gnd'], bb.cols['right']['gnd'], 30, kind='gnd')
        bb.verify()

    def test_side_는_a_또는_f_다(self):
        bb = self.board()
        with self.assertRaisesRegex(AssertionError, "side"):
            self.mod._input_jumper(bb, bb.cols['left'], 7, 'A', 'x', side='g')

    def test_걷을_입력_점퍼는_그쪽_GND_레일을_건드리지_않는다(self):
        """걷기 보드(`removal_board`)에서 이 점퍼는 `step_wire` 가 유령선으로만 그리고
        점유표·구간·레일 접촉을 하나도 안 남긴다 — 꽂혀 있지 않은 선이다. 그런데
        `touch_rail` 을 먼저 부르면 우 바깥 GND 836 이 검사에 들어가 브리지를 내놓으라고
        한다(2026-09-20)."""
        bb = self.board()
        bb.draw_chip('74HC08', 10, block='right')
        bb.partial = True
        bb.connect_jacks()
        self.mod._input_jumper(bb, bb.cols['right'], 11, 'A', '74HC08 pin 13', side='f')
        snap = bb.snapshot()

        # 그 점퍼만 빼고 다시 그린 보드의 removals() 가 걷기 key 를 준다
        probe = self.mod.BreadboardRenderer(baseline=snap)
        probe.enable_steps()
        probe.draw_chip('74HC08', 10, block='right')
        probe.partial = True
        probe.connect_jacks()
        keys = [r['key'] for r in probe.removals()]
        self.assertEqual(len(keys), 1, f'입력 점퍼 하나만 걷어야 한다: {keys}')

        ghost = self.mod.BreadboardRenderer(baseline=dict(
            snap, ghost={'wires': {keys[0]: 1}, 'title': 't', 'subtitle': 's'}))
        ghost.enable_steps()
        ghost.draw_chip('74HC08', 10, block='right')
        ghost.connect_jacks()
        self.mod._input_jumper(ghost, ghost.cols['right'], 11, 'A', '74HC08 pin 13', side='f')
        self.assertNotIn(ghost.cols['right']['gnd'], ghost._touched['gnd'])
        ghost.verify()

    # ---- R8. 같은 블록 두 칩 사이 배선은 쪽을 바꾸지 않는다 ----

    def _two_chips(self):
        """좌 7행 74HC86 + 좌 18행 74HC04. 핀은 안 물렸으니 partial."""
        bb = self.board()
        bb.draw_chip('74HC86', 7)
        bb.draw_chip('74HC04', 18)
        bb.partial = True
        return bb

    def test_같은_쪽으로_잇는_칩_사이_배선은_통과한다(self):
        bb = self._two_chips()
        c = bb.cols['left']
        bb.step_wire([(c['a'], bb.r_y(9)), (c['a'], bb.r_y(20))], 'mid', 'A⊕B -> NOT2 pin 3')
        self.assertEqual(bb.cross_side_wires(), [])
        bb.verify()

    def test_반대_쪽으로_건너는_칩_사이_배선은_R8_로_막힌다(self):
        bb = self._two_chips()
        c = bb.cols['left']
        bb.step_wire([(c['a'], bb.r_y(9)), (c['a'], bb.r_y(16)), (c['h'], bb.r_y(16)), (c['h'], bb.r_y(19))],
                     'mid', 'A⊕B -> NOT2 pin 13')
        w = bb.cross_side_wires()
        self.assertEqual([(x['frm'], x['to']) for x in w], [('좌 a9', '좌 h19')])
        self.assertEqual((w[0]['from_side']['chip'], w[0]['from_side']['side']), ('74HC86', 'a'))
        self.assertEqual((w[0]['to_side']['chip'], w[0]['to_side']['side']), ('74HC04', 'f'))
        with self.assertRaisesRegex(AssertionError, r'R8 칩 사이 엇갈림: 좌 a9 → 좌 h19 · A⊕B -> NOT2 pin 13 — 74HC86 a쪽 → 74HC04 f쪽'):
            bb.verify()

    def test_같은_칩_안에서_건너는_사슬은_R8_대상이_아니다(self):
        """게이트를 나눈 칩 안의 XOR1→XOR2 사슬 — 나누기의 대가라 허용한다."""
        bb = self._two_chips()
        c = bb.cols['left']
        bb.step_wire([(c['c'], bb.r_y(9)), (c['c'], bb.r_y(14)), (c['h'], bb.r_y(14)), (c['h'], bb.r_y(9))],
                     'mid', 'XOR1 -> XOR2 (pin 3 -> pin 12)')
        self.assertEqual(bb.cross_side_wires(), [])
        bb.verify()

    def test_다른_블록으로_건너는_배선은_R8_대상이_아니다(self):
        bb = self._two_chips()
        c, r = bb.cols['left'], bb.cols['right']
        bb.draw_chip('74HC08', 10, block='right')
        bb.step_wire([(c['a'], bb.r_y(9)), (c['a'], bb.r_y(6)), (r['h'], bb.r_y(6)), (r['h'], bb.r_y(12))],
                     'mid', 'A⊕B -> 우 AND2 pin 12')
        self.assertEqual(bb.cross_side_wires(), [])
        bb.verify()

    def test_LED_레일_끝점은_R8_대상이_아니다(self):
        """칩 f쪽 출력 → LED 사슬(칩 행 밖) 은 칩 사이 배선이 아니다."""
        bb = self._two_chips()
        c = bb.cols['left']
        bb.step_wire([(c['i'], bb.r_y(10)), (c['i'], bb.r_y(15)), (212, bb.r_y(15)), (212, bb.r_y(30)), (c['a'], bb.r_y(30))],
                     'sig', 'S -> LED1')
        self.assertEqual(bb.cross_side_wires(), [])

    def test_legacy_정책은_R8_도_끈다(self):
        bb = self._two_chips()
        c = bb.cols['left']
        bb.step_wire([(c['a'], bb.r_y(9)), (c['a'], bb.r_y(16)), (c['h'], bb.r_y(16)), (c['h'], bb.r_y(19))],
                     'mid', 'A⊕B -> NOT2 pin 13')
        bb.density_policy = 'legacy'
        bb.verify()


# R8 의 승인본 예외 — 2026-09-20 실측. 실험02 t_pd 2단계(`build_e2_tpd`, legacy)는 **같은
# 부품번호 74HC04 두 개**(좌 7행 U1, 좌 18행 U2)를 U1 pin 8(f쪽) → U2 pin 1(a쪽) 으로 잇는다.
# 74HC04 의 핀배치상 목적지 pin 1 은 a쪽에만 있어 쪽을 바꿀 수밖에 없고, 승인·제출된 그림이라
# 다시 그리지 않는다. R8 자체는 legacy 로 면제되므로 verify() 동작에는 영향이 없다 — 이 표는
# 회귀선일 뿐이고, 주소까지 못 박아 두어 한 건이라도 늘면 테스트가 깨진다.
KNOWN_CROSS_SIDE = {'build_e2_tpd': [('좌 i13', '좌 b18')]}


def _render(mod, fn):
    """빌더를 임시 파일로 렌더하고 렌더러 객체를 돌려준다. export() 안에서 verify() 가 돈다."""
    captured = {}
    orig = mod.BreadboardRenderer.export

    def spy(self_, *a, **k):
        captured['bb'] = self_
        return orig(self_, *a, **k)

    mod.BreadboardRenderer.export = spy
    try:
        with tempfile.TemporaryDirectory() as d:
            fn(os.path.join(d, 'x.png'))
    finally:
        mod.BreadboardRenderer.export = orig
    return captured['bb']


class AllCircuits(unittest.TestCase):
    """12장 전부가 그림대로 꽂힌다. 2026-09-08 까지 복합 회로만 포개짐 경고 둘을
    안고 경고 모드였다 — 초록 Z 선을 11행으로 옮겨 0 이 됐고 엄격 모드다."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    def builders(self):
        return all_builders(self.mod)

    def test_모든_회로가_그림대로_꽂힌다(self):
        for name, fn in sorted(self.builders().items()):
            with self.subTest(회로=name):
                bb = _render(self.mod, fn)
                self.assertEqual(bb._not_holes, [])
                self.assertEqual(bb._double, [])

    def test_모든_회로가_엄격_모드로_포개짐_없이_통과한다(self):
        for name, fn in sorted(self.builders().items()):
            with self.subTest(회로=name):
                bb = _render(self.mod, fn)
                self.assertEqual(bb.overlap_policy, 'strict', f'{name}: 경고 모드로 도는 회로가 없어야 한다')
                self.assertEqual(bb.overlap_warnings, [])

    def test_R7_legacy_는_실험_1_2_3_뿐이고_그_뒤는_엄격_모드다(self):
        """실험01~03 은 R7(2026-09-20) 이전 승인본이라 legacy 로 고정한다. 실험04부터
        새 빌더가 legacy 를 붙이면 여기서 걸린다 — 밀집은 게이트 배정으로 풀지 정책으로
        끄지 않는다."""
        for name, fn in sorted(self.builders().items()):
            with self.subTest(회로=name):
                exp = int(fn.__module__.rsplit('board_e', 1)[1])
                bb = _render(self.mod, fn)
                want = 'legacy' if exp <= 3 else 'strict'
                self.assertEqual(bb.density_policy, want,
                                 f'{name}: 실험{exp:02d} 의 density_policy 는 {want} 여야 한다')
                if want == 'strict':
                    self.assertTrue(all(s['count'] <= self.mod.SIDE_LEAD_MAX for s in bb.side_leads()))

    def test_R8_모든_회로에_칩_사이_엇갈림이_없다(self):
        """2026-09-20 실측: 실험01~03 완성본 7장 0건, 시험 전용 build_e2_tpd 1건 —
        legacy 라도 회귀선으로 건다. 알려진 1건까지 주소로 못 박으므로 어디서든 새 엇갈림이
        생기거나 e2_tpd 에 하나 더 붙으면 여기서 걸린다."""
        for name, fn in sorted(self.builders().items()):
            with self.subTest(회로=name):
                bb = _render(self.mod, fn)
                self.assertEqual([(w['frm'], w['to']) for w in bb.cross_side_wires()],
                                 KNOWN_CROSS_SIDE.get(name, []), name)


if __name__ == '__main__':
    unittest.main()
