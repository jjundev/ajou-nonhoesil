# v2 판형 연기 시험 — 새 v2 주차 `배치.py` 의 본보기다.
#
# 칩은 좌 블록에만, LED 사슬은 우 블록에만 둔다(R9·R10). 전원은 잭 → 좌 바깥 레일 → 가운데
# 레일 브리지 두 가닥. 우 바깥 레일은 쓰지 않는다. LED 를 구동하는 게이트는 f~j 쪽(pin 8~14)이라
# 건너는 선이 칩 몸통 위를 지나지 않고, 사슬은 우 a 열에서 받아 GND 를 가운데 레일로 내린다.
#
#   U1 좌 5행  : 74HC08 — 게이트 3 (pin 10·9 → 8) = A·B → L1
#   U2 좌 23행 : 74HC32 — 게이트 3 (pin 10·9 → 8) = C+D → L2
#
# 입력은 가운데 GND 레일에서 i 열로 넣는다(`_input_jumper(side='f')`). 번호 원은 그 선 위
# x=562 에 둔다 — 기본 자리(배지 위 18px)는 이웃 행 배지와 겹친다.
from render_breadboard import BreadboardRenderer, _input_jumper

BOARD = 'v2'

U1, U2 = 5, 23          # 74HC08 · 74HC32 의 pin 1 행 (좌 블록)


def build_v2_smoke(output_path, template_path=None, stage=None, baseline=None, layer=None):
    bb = BreadboardRenderer(template_path, baseline=baseline, layer=layer, board=BOARD)
    bb.enable_steps()
    bb.set_header('v2 연기 시험', '74HC08 · 74HC32 → LED 두 개')
    L, R = bb.cols['left'], bb.cols['right']
    bb.draw_chip('74HC08', U1)
    bb.draw_chip('74HC32', U2)
    bb.connect_jacks()                                   # ① ② 잭 → 좌 바깥 레일
    bb.bridge_rails(L['gnd'], L['mid_gnd'], 33, kind='gnd')   # ③ 좌 바깥 → 가운데 GND
    bb.bridge_rails(L['vcc'], L['mid_vcc'], 34, kind='vcc')   # ④ 좌 바깥 → 가운데 VCC
    for row in (U1, U2):
        bb.connect_power(row)                            # ⑤~⑧ pin 14 → 가운데 VCC, pin 7 → 좌 GND
    for row, chip, (a, b) in ((U1, '74HC08', ('A', 'B')), (U2, '74HC32', ('C', 'D'))):
        _input_jumper(bb, L, row + 4, a, f'{chip} pin 10', marker=(562, 0), side='f')   # ⑨~⑫
        _input_jumper(bb, L, row + 5, b, f'{chip} pin 9', marker=(562, 0), side='f')
        bb.mark_unused_inputs([1, 2, 4, 5, 12, 13], row, chip=chip)
        bb.mark_unused_outputs([3, 6, 11], row, chip=chip)
    for row, tag in ((U1, 'L1'), (U2, 'L2')):
        out = row + 6                                    # pin 8 행
        # ⑬ ⑯ 가운데를 건너는 선 — 반 행 아래로 건넌다. 같은 행으로 곧게 건너면 가운데 레일
        # 홀 위를 지나 GND 레일에 꽂힌 것으로 읽힌다(R12, 2026-10-03)
        y, h = bb.r_y(out), bb.spec.row_pitch / 2
        bb.step_wire([(L['j'], y), (L['j'], y + h), (R['a'], y + h), (R['a'], y)], 'sig',
                     f'{tag} 급전 (pin 8)')
        bb.led_chain(R['a'], out, tag, f'{tag} = pin 8', block='right')   # ⑭⑮ ⑰⑱
    bb.export(output_path)
    return bb


BOARDS = []
FINALS = [('v2_smoke.png', build_v2_smoke)]
LAYERS = {'v2_smoke.png': [(1, 4, '전원 잭·브리지'), (5, 8, '칩 전원'),
                           (9, 12, '입력'), (13, 18, '출력·LED')]}
