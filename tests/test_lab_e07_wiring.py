"""실험07의 실제 넷과 단계 관측 준비를 검증한다. 상태 시뮬레이터는 아니다."""
from pathlib import Path
import pytest
from scripts.lab.place_search import load

ROOT = Path(__file__).resolve().parents[1]

@pytest.fixture(scope='module')
def board(tmp_path_factory):
    mod, week = load(ROOT / '보고서/실험07/결선도/배치.py')
    bb = week.build_e7_shift(tmp_path_factory.mktemp('e07') / 'final.png')
    return mod, week, bb


def net(bb, label):
    return next(n for n in bb.nets() if label in n['labels'])


def pin(week, u, p):
    return f"{week.SHIFT.models[u]}#{week.LAYOUT['slots'][week.SHIFT.chips[u]]} pin {p}"


def test_six_bits_follow_previous_q_and_complement(board):
    _, week, bb = board
    # BIT1/3/5 are the second FF; BIT2/4/6 are the first FF in each package.
    bits = [('U2', 9, 12, 11, 10), ('U2', 4, 16, 15, 14),
            ('U3', 9, 12, 11, 10), ('U3', 4, 16, 15, 14),
            ('U4', 9, 12, 11, 10), ('U4', 4, 16, 15, 14)]
    assert pin(week, 'U2', 9) in net(bb, '입력 D')['labels']
    assert pin(week, 'U2', 12) in net(bb, pin(week, 'U1', 8))['labels']
    for prev, curr in zip(bits, bits[1:]):
        assert pin(week, curr[0], curr[1]) in net(bb, pin(week, prev[0], prev[3]))['labels']
        assert pin(week, curr[0], curr[2]) in net(bb, pin(week, prev[0], prev[4]))['labels']
    for i, (u, _, _, q, _) in enumerate(bits, 1):
        # Engine normal LED has signal on anode and resistor after cathode.
        assert f'LED BIT{i} 애노드' in net(bb, pin(week, u, q))['labels']
        assert not net(bb, pin(week, u, q))['rails']


def test_all_control_and_power_pins(board):
    _, week, bb = board
    for u in ('U2', 'U3', 'U4'):
        for p in (1, 6):
            assert pin(week, u, p) in net(bb, '입력 CLK')['labels']
        for p in (3, 8):
            assert pin(week, u, p) in net(bb, '입력 CLR')['labels']
        assert net(bb, pin(week, u, 5))['rails'] == {'vcc'}
        assert net(bb, pin(week, u, 13))['rails'] == {'gnd'}
    assert pin(week, 'U2', 7) in net(bb, '입력 PR1')['labels']
    assert pin(week, 'U2', 2) in net(bb, '입력 PR2')['labels']
    for u in ('U3', 'U4'):
        for p in (2, 7):
            assert net(bb, pin(week, u, p))['rails'] == {'vcc'}
    assert not bb.cross_side_wires()
    assert max(x['count'] for x in bb.side_leads()) <= week.SIDE_LEAD_MAX


def test_every_powered_ff_input_has_a_driver_in_each_stage(tmp_path):
    _, week = load(ROOT / '보고서/실험07/결선도/배치.py')
    base = None
    for name, fn, st in week.BOARDS:
        bb = fn(tmp_path / name, stage=st, baseline=base)
        base = bb.snapshot()
        if st is None:  # 걷기 중에는 전원이 꺼져 있다.
            continue
        for u in ('U2', 'U3', 'U4'):
            for p in (1, 2, 3, 4, 6, 7, 8, 9, 12, 16):
                labels = net(bb, pin(week, u, p))['labels']
                # A rail, an external input, or an actual FF/NAND output drives the net.
                driven = bool(net(bb, pin(week, u, p))['rails']) or any(x.startswith('입력 ') for x in labels)
                driven |= any(pin(week, v, q) in labels for v in ('U2', 'U3', 'U4') for q in (10, 11, 14, 15))
                driven |= pin(week, 'U1', 8) in labels
                assert driven, (st, u, p, labels)


def test_approved_numeric_order_and_final_routing(board):
    mod, week, bb = board
    assert [v['tag'] for v in sorted(bb.leds, key=lambda v: v['anode'][2])] == [f'BIT{i}' for i in range(1, 7)]
    assert {pin(week, 'U1', p) for p in (9, 10)} <= net(bb, '입력 D')['labels']
    metrics = mod.wire_metrics(bb)
    assert metrics['length'] == pytest.approx(305.3157894736842)
    assert metrics['bends'] == 69
    assert metrics['density'] == pytest.approx(3.4736842105263164)
