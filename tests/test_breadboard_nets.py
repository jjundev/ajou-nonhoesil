"""결선도가 **무엇과 무엇을 잇는가**를 렌더러가 아는지 검사한다.

2026-09-09 에 발견: 복합 회로의 `우 a10 → 우 b10` 점퍼는 같은 5홀 스트립
안에서 끝나 전기적으로 아무 일도 하지 않았고, 74HC32 pin 1 은 뜬 채였다.
실험02 Rn 은 1kΩ 아랫다리가 pin 5 행에 앉아 +5V 와 GND 를 직결시켰다.
둘 다 `verify()` R1~R4 와 시험 128건을 통과한 상태로 커밋돼 있었다 — R1~R4
는 전부 기하라서, 배선이 무엇을 잇는지는 아무도 보지 않았다.

브레드보드는 홀이 아니라 **스트립** 단위로 이어진다. 단자대는 한 행의 a~e
가 한 스트립이고 f~j 가 또 한 스트립, 전원 레일은 열 하나가 통째로 한
스트립이다. 그래서 홀 점유표(`_leads`)로는 이 층위가 안 보인다.
"""
import importlib.util
import os
import unittest

from tests._boards import all_builders
from tests._renders import render

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO_ROOT, '.claude', 'skills', 'breadboard-diagram',
                      'scripts', 'render_breadboard.py')


def _load():
    spec = importlib.util.spec_from_file_location('render_breadboard', SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _render(mod, fn):
    """빌더를 그려 렌더러 객체를 돌려준다 — 프로세스에서 한 번만 그린다(`tests/_renders.py`)."""
    return render(mod, fn)[0]


def _net_of(bb, label):
    for net in bb.nets():
        if label in net['labels']:
            return net
    raise AssertionError(f'{label} 이 어느 넷에도 없다')


class NetModel(unittest.TestCase):
    """스트립을 옳게 묶는가. 합성 보드에 몇 줄만 그리고 `nets()` 만 부른다."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _load()
        cls.b1, cls.b2, cls.b3 = (cls.mod.load_board(n) for n in (1, 2, 3))

    def board(self):
        bb = self.mod.BreadboardRenderer()
        bb.enable_steps()
        return bb

    def test_같은_행_a부터_e_는_한_스트립이다(self):
        bb = self.board()
        c = bb.cols['left']
        bb.draw_chip('74HC08', 10)
        bb.step_wire([(c['d'], bb.r_y(10)), (c['d'], bb.r_y(13))], 'sig', '시험')
        self.assertIn('74HC08#10 pin 4', _net_of(bb, '74HC08#10 pin 1')['labels'])

    def test_칩_건너편_f부터_j_는_다른_스트립이다(self):
        bb = self.board()
        bb.draw_chip('74HC08', 10)
        self.assertNotIn('74HC08#10 pin 14', _net_of(bb, '74HC08#10 pin 1')['labels'])

    def test_레일쌍은_브리지_전에는_다른_넷이다(self):
        bb = self.board()
        c = bb.cols['left']
        self.assertNotIn('좌 중앙GND레일', _net_of(bb, '좌 GND레일')['labels'])
        bb.bridge_rails(c['gnd'], c['mid_gnd'], 29, kind='gnd')
        self.assertIn('좌 중앙GND레일', _net_of(bb, '좌 GND레일')['labels'])

    def test_입력_점퍼의_레일_끝은_가상_노드다(self):
        """입력은 지금 GND 레일에 꽂혀 있지만(=0 자리) 1 을 줄 때 그 끝만
        VCC 로 옮긴다. 레일 연결로 세면 입력 A·B·C 가 GND 와 한 넷이 되어
        'pin 1 이 A 에 물렸는가' 를 물을 수 없다."""
        bb = self.board()
        c = bb.cols['left']
        bb.draw_chip('74HC08', 10)
        self.mod._input_jumper(bb, c, 10, 'A', '74HC08 pin 1')
        net = _net_of(bb, '입력 A')
        self.assertIn('74HC08#10 pin 1', net['labels'])
        self.assertNotIn('좌 GND레일', net['labels'])


class CircuitNets(unittest.TestCase):
    """회로마다 넷리스트가 약속한 대로 물렸는가. 정답의 권위는
    `보고서/실험01/결선도/netlist.md` 와 실험02 넷리스트다."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _load()
        cls.b1, cls.b2, cls.b3 = (cls.mod.load_board(n) for n in (1, 2, 3))

    def test_복합_74HC32_pin_1_이_입력_A_와_한_넷이다(self):
        """2026-09-09 까지 `우 a10 → 우 b10` 은 같은 스트립 안에서 끝나 아무
        일도 하지 않았고, a10 으로 A 를 가져오는 선이 없어 pin 1 이 떴다.
        netlist C5: `U9 pin 1 ← 입력 A`."""
        bb = _render(self.mod, self.b1.build_e1_comb_s3)
        self.assertIn('입력 A', _net_of(bb, '74HC32#10 pin 1')['labels'])

    def test_복합_Z_와_X_는_각자_LED_를_달고_있다(self):
        """`X ≡ Z` 라 두 LED 가 언제나 같이 켜져야 한다 — 공짜 자체 검산이다.
        서로 다른 넷에서 각각 켜져야 의미가 있다."""
        bb = _render(self.mod, self.b1.build_e1_comb_s3)
        z = _net_of(bb, '74HC04#7 pin 4')['labels']
        self.assertIn('LED Z 애노드', z)
        self.assertIn('74HC32#10 pin 2', z)
        self.assertIn('LED X 애노드', _net_of(bb, '74HC32#10 pin 3')['labels'])
        self.assertNotIn('LED X 애노드', z)

    def test_tpd_체인은_교안_p12_순서로_흐른다(self):
        """netlist C3: 2→3, 4→5, 6→13, 12→11, 10→9, 8→U2 pin 1. 핀 번호 순서가
        아니다 — pin 6 에서 pin 13 으로 건너뛴 뒤 거슬러 내려온다. 핀 번호만 보고
        `9→8` 로 짐작하면 CH1~CH2 사이가 2단이 되고 게이트당 t_pd 가 2배로 나온다."""
        bb = _render(self.mod, self.b2.build_e2_tpd)
        for a, b in ((2, 3), (4, 5), (6, 13), (12, 11), (10, 9)):
            with self.subTest(pair=(a, b)):
                self.assertIn(f'74HC04#7 pin {b}', _net_of(bb, f'74HC04#7 pin {a}')['labels'])
        self.assertIn('74HC04#18 pin 1', _net_of(bb, '74HC04#7 pin 8')['labels'])

    def test_tpd_U1_체인은_전원_레일에_닿지_않는다(self):
        """체인 노드 하나라도 레일에 물리면 그 단 뒤가 전부 고정된다."""
        bb = _render(self.mod, self.b2.build_e2_tpd)
        for p in (2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 13):
            with self.subTest(pin=p):
                self.assertEqual(set(), _net_of(bb, f'74HC04#7 pin {p}')['rails'])

    def test_tpd_U2_pull_선은_교안_p12_회로도대로다(self):
        """netlist C3: U2 pin 3·5 → GND, pin 9·11·13 → VCC. pin 2 는 개방."""
        bb = _render(self.mod, self.b2.build_e2_tpd)
        for p in (3, 5):
            self.assertEqual({'gnd'}, _net_of(bb, f'74HC04#18 pin {p}')['rails'])
        for p in (9, 11, 13):
            self.assertEqual({'vcc'}, _net_of(bb, f'74HC04#18 pin {p}')['rails'])

    def test_실험02_회로는_전원이_단락되지_않는다(self):
        """pull-down(3·5) 과 pull-up(9·11·13) 이 한 레일 행에 착지하면 단락이다."""
        for name in ('build_e2_inv', 'build_e2_schmitt', 'build_e2_tpd'):
            with self.subTest(회로=name):
                bb = _render(self.mod, getattr(self.b2, name))
                for net in bb.nets():
                    self.assertNotEqual({'vcc', 'gnd'}, net['rails'], sorted(net['labels']))

    def test_VTC_회로의_pull_선은_교안_p9_그림대로다(self):
        """netlist C1·C2: pin 3·5 → GND, pin 9·11·13 → VCC. 74HC14 도 같다."""
        for name, chip in (('build_e2_inv', '74HC04'), ('build_e2_schmitt', '74HC14')):
            with self.subTest(회로=name):
                bb = _render(self.mod, getattr(self.b2, name))
                for p in (3, 5):
                    self.assertEqual({'gnd'}, _net_of(bb, f'{chip}#7 pin {p}')['rails'])
                for p in (9, 11, 13):
                    self.assertEqual({'vcc'}, _net_of(bb, f'{chip}#7 pin {p}')['rails'])


class R5(unittest.TestCase):
    """넷 검사 자체. 합성 보드에 몇 줄만 그리고 `verify()` 를 부른다 —
    파일을 쓰지 않아 빠르고, 어느 갈래가 잡았는지 메시지로 확인한다."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _load()
        cls.b1, cls.b2, cls.b3 = (cls.mod.load_board(n) for n in (1, 2, 3))

    def board(self):
        bb = self.mod.BreadboardRenderer()
        bb.enable_steps()
        return bb

    def test_같은_스트립_안에서_끝나는_점퍼는_막힌다(self):
        bb = self.board()
        c = bb.cols['left']
        bb.step_wire([(c['c'], bb.r_y(20)), (c['d'], bb.r_y(20))], 'sig', '갈래')
        with self.assertRaisesRegex(AssertionError, '같은 스트립'):
            bb.verify()

    def test_옆_행으로_가는_점퍼는_통과한다(self):
        bb = self.board()
        c = bb.cols['left']
        bb.step_wire([(c['c'], bb.r_y(20)), (c['c'], bb.r_y(21))], 'sig', '갈래')
        bb.verify()

    def test_전원_두_레일이_한_넷이면_막힌다(self):
        bb = self.board()
        c = bb.cols['left']
        bb.step_wire([(c['vcc'], bb.r_y(21)), (c['gnd'], bb.r_y(21))], 'vcc', '단락')
        with self.assertRaisesRegex(AssertionError, '단락'):
            bb.verify()

    def test_아무_데도_안_물린_칩_핀은_막힌다(self):
        bb = self.board()
        bb.draw_chip('74HC08', 10)
        with self.assertRaisesRegex(AssertionError, '뜬 핀'):
            bb.verify()

    def test_미사용_출력은_뜬_핀이_아니다(self):
        bb = self.board()
        bb.draw_chip('74HC08', 10)
        bb.mark_unused_outputs([8], 10, chip='74HC08')
        with self.assertRaises(AssertionError) as e:
            bb.verify()
        self.assertIn('74HC08#10 pin 1 이', str(e.exception))
        self.assertNotIn('74HC08#10 pin 8 이', str(e.exception))

    def test_개방_등록한_미사용_입력은_뜬_핀이_아니다(self):
        """실험01 실측(2026-09-11): 미사용 게이트 입력을 접지하지 않아도 결과가
        같았다. 접지선은 순서표의 절반이었다. 개방으로 등록하면 R5ⓒ 가 봐준다."""
        bb = self.board()
        bb.draw_chip('74HC08', 10)
        bb.mark_unused_inputs([9, 10, 12, 13], 10, chip='74HC08')
        bb.mark_unused_outputs([8, 11], 10, chip='74HC08')
        with self.assertRaises(AssertionError) as e:
            bb.verify()
        msg = str(e.exception)
        self.assertIn('74HC08#10 pin 1 이', msg)
        for p in (9, 10, 12, 13):
            self.assertNotIn(f'74HC08#10 pin {p} 이', msg)

    def test_개방_미사용_입력은_rail_이_None_으로_남는다(self):
        bb = self.board()
        bb.draw_chip('74HC08', 10)
        bb.mark_unused_inputs([9, 10], 10, chip='74HC08')
        self.assertEqual([(u['chip'], u['pin'], u['rail']) for u in bb.wiring()['unused_inputs']],
                         [('74HC08', 9, None), ('74HC08', 10, None)])
        self.assertEqual(bb.notes, [])  # 문구는 체크리스트 핀 점검 상자가 싣는다

    def test_계측기가_무는_핀은_뜬_핀이_아니다(self):
        """실험02 인버터는 pin 1 에 함수발생기를, pin 2 에 프로브를 문다 —
        점퍼가 없다고 뜬 것이 아니다."""
        bb = self.board()
        c = bb.cols['left']
        bb.draw_chip('74HC04', 10)
        bb.instrument(c['a'], 10, '함수발생기', '체인 입력')
        with self.assertRaises(AssertionError) as e:
            bb.verify()
        self.assertNotIn('74HC04#10 pin 1 이', str(e.exception))
        self.assertIn('74HC04#10 pin 2 이', str(e.exception))

    def test_덜_그린_그림은_뜬_핀만_봐준다(self):
        bb = self.board()
        c = bb.cols['left']
        bb.draw_chip('74HC08', 10)
        bb.partial = True
        bb.verify()
        bb.step_wire([(c['c'], bb.r_y(20)), (c['d'], bb.r_y(20))], 'sig', '갈래')
        with self.assertRaisesRegex(AssertionError, '같은 스트립'):
            bb.verify()

    def test_양끝이_빈_스트립인_부품_다리는_막힌다(self):
        """뜬 핀만 보던 시절, 허공에 걸친 저항은 어떤 규칙도 안 봤다. 그림대로
        꽂으면 부하가 안 달린 채로 V_OL 을 재게 되고 **실험실에서는 아무 이상이
        없어 보인다** — 눈으로도 계측으로도 안 잡히는 자리다."""
        bb = self.board()
        c = bb.cols['left']
        bb.draw_resistor(c['c'], bb.r_y(21), bb.r_y(24), label="1kΩ")
        with self.assertRaises(AssertionError) as e:
            bb.verify()
        self.assertIn('저항1(1kΩ) 윗다리 가 아무 데도 안 물렸다 — 뜬 다리', str(e.exception))
        self.assertIn('저항1(1kΩ) 아랫다리 가 아무 데도 안 물렸다 — 뜬 다리', str(e.exception))

        # 아랫다리를 레일에 물리면 그 다리는 더 이상 뜨지 않는다
        bb.step_wire([(c['a'], bb.r_y(24)), (c['gnd'], bb.r_y(24))], 'gnd', '아랫다리 -> GND')
        with self.assertRaises(AssertionError) as e:
            bb.verify()
        self.assertNotIn('아랫다리 가', str(e.exception))
        self.assertIn('윗다리 가', str(e.exception))

        # 윗다리까지 물리면 통과한다 — 짝이 붙은 다리는 넷에 라벨이 둘 이상이다
        bb.step_wire([(c['a'], bb.r_y(21)), (c['gnd'], bb.r_y(21))], 'gnd', '윗다리 -> GND')
        bb.verify()

    def test_입력_점퍼가_꽂힌_스트립이_VCC_에_물리면_단락이다(self):
        """입력 점퍼의 레일 끝은 라벨 판정에서만 가상 노드다. 그림에 그려진
        배선은 GND 레일에 실제로 꽂혀 있으므로, 그 스트립이 VCC 에도 물리면
        그림 그대로가 GND↔VCC 직결이다 — 치환한 넷에서는 안 보인다."""
        bb = self.board()
        c = bb.cols['left']
        self.mod._input_jumper(bb, c, 20, 'A', '어딘가')
        # 같은 스트립(좌 a~e 20행)에서 VCC 로. 가로선이 입력선 끝점 b20 위를
        # 지나지 않도록 d 열에서 세로로 빠져나간 뒤 17행에서 레일로 간다
        bb.step_wire([(c['d'], bb.r_y(20)), (c['d'], bb.r_y(17)), (c['vcc'], bb.r_y(17))],
                     'vcc', '입력 스트립 -> +5V')
        with self.assertRaisesRegex(AssertionError, '단락'):
            bb.verify()

    def test_모든_회로가_넷_검사를_통과한다(self):
        """`export()` 안에서 `verify()` 가 돈다 — 렌더가 되면 통과한 것이다."""
        builders = all_builders(self.mod)
        # 2026-09-12 슬롯 고정: 실험01 절차 CLI 래퍼 5개(e1_or_s1·e1_nand_s1/_s2·
        # e1_nor_s1/_s2)가 늘어 기존 13(실험01 8 + 실험02 5)에서 18이 됐다.
        # 2026-09-13 실험02 재저작: Rn·Rp 가 빠지고(배포본 교안에 없다) 절차 래퍼
        # 3개(e2_schmitt_s1·e2_tpd_s1/_s2)가 늘어 실험01 13 + 실험02 6 = 19 다.
        # 2026-09-14 실험03: 회로 4 + 절차 래퍼 8 = 12 가 늘어 31 이다.
        # 2026-09-14 범위 축소(조교 공지 `_350547_1`): 실험02 절차 래퍼 2개
        # (e2_tpd_s1/_s2)와 실험03 절차 래퍼 5개(e3_ha_s1/_s2·e3_hs_s1/_s2·e3_fs_s2)가
        # 빠져 24 다. 완성본 build_e2_tpd·build_e3_ha·build_e3_hs 는 남는다.
        # 2026-09-15 엔진·주차 분리: 빌더가 주차 `배치.py` 로 옮겨 갔다(`tests/_boards.py`).
        # 일괄 렌더 `build_eN_all` 은 원래 세지 않았으므로 수는 그대로 24 다.
        # 2026-09-20 단계 세분화: 실험03 절차 래퍼가 셋(e3_fa_s1/_s2·e3_fs_s1)에서
        # 일곱(e3_fa_s1~_s5·e3_fs_s1/_s2)으로 늘어 28 이다.
        # 2026-09-28 실험04: 회로 2(e4_mux·e4_dmux) + 절차 래퍼 12(e4_mux_s1~_s8·
        # e4_dmux_s1~_s4) = 14 가 늘어 42 다.
        self.assertEqual(len(builders), 42)
        for name, fn in sorted(builders.items()):
            with self.subTest(회로=name):
                _render(self.mod, fn)


class R6(unittest.TestCase):
    """자기 스트립 안을 달리는 구간. R5ⓐ 가 배선의 **양 끝점**만 보는 사이,
    자기 스트립 안을 지나다 밖으로 나가는 배선은 끝점이 서로 다른 스트립이라
    통과했다. 2026-09-10 사용자가 OR 의 ⑪ 갈래(`좌 c12 → 좌 a12 → 좌 a24`)를
    짚어 드러났다 — 12행 a~e 는 한 스트립이라 가로 구간은 없어도 되는 우회다."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _load()
        cls.b1, cls.b2, cls.b3 = (cls.mod.load_board(n) for n in (1, 2, 3))

    def board(self):
        bb = self.mod.BreadboardRenderer()
        bb.enable_steps()
        return bb

    def test_자기_스트립_안을_달리는_구간은_막힌다(self):
        bb = self.board()
        c = bb.cols['left']
        bb.step_wire([(c['c'], bb.r_y(12)), (c['a'], bb.r_y(12)), (c['a'], bb.r_y(24))],
                     'mid', '중간단 확인용 갈래')
        with self.assertRaisesRegex(AssertionError, '자기 스트립.*좌 c12 -> 좌 a12'):
            bb.verify()

    def test_옛_AND_갈래_기하를_그대로_재현하면_걸린다(self):
        # 2026-09-08~10 의 실제 좌표. 점퍼(d12→d13)와 갈래가 나란히 있던 그림이다.
        # 점퍼는 R6 에 걸리지 않고 갈래만 걸려야 한다
        bb = self.board()
        c = bb.cols['left']
        bb.step_wire([(c['d'], bb.r_y(12)), (c['d'], bb.r_y(13))], 'mid', 'pin 3 -> pin 4')
        bb.step_wire([(c['c'], bb.r_y(12)), (c['a'], bb.r_y(12)), (c['a'], bb.r_y(24))],
                     'mid', '중간단 확인용 갈래')
        with self.assertRaisesRegex(AssertionError, '자기 스트립.*중간단 확인용 갈래'):
            bb.verify()

    def test_곧게_내리는_갈래는_통과한다(self):
        bb = self.board()
        c = bb.cols['left']
        bb.step_wire([(c['a'], bb.r_y(12)), (c['a'], bb.r_y(24))], 'mid', '중간단 확인용 갈래')
        bb.verify()

    def test_잭에서_레일로_내려오는_선은_R6_가_안_본다(self):
        # 레일 스트립 키에는 행이 없다 — 같은 레일 위 두 점은 언제나 같은 스트립이다.
        # 홀 판정 없이 `sym()` 만 보면 전원잭 배선 둘이 통째로 오탐이 된다
        bb = self.board()
        bb.connect_jacks()
        bb.verify()

    def test_칩을_가로지르는_선은_스트립이_갈려_통과한다(self):
        # a~e 와 f~j 는 가운데 골이 갈라 놓는다. 한 행을 가로질러도 같은 스트립이 아니다
        bb = self.board()
        c = bb.cols['left']
        bb.step_wire([(c['b'], bb.r_y(25)), (c['i'], bb.r_y(25))], 'sig', '골 건너기')
        bb.verify()


if __name__ == '__main__':
    unittest.main()

