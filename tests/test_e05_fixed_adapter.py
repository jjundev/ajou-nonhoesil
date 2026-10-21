"""E05 exploration adapters preserve logical identities while fixing numeric LED order."""
from pathlib import Path
import copy
import pytest
from scripts.lab.place_search import load
from scripts.lab.fixed_search import validate_anchors

ROOT = Path(__file__).resolve().parents[1]

@pytest.mark.parametrize('name,tags', [('bcd', tuple(f'Y{i}' for i in range(10))), ('xs3', tuple(f'A{i}' for i in range(4)))])
def test_numeric_anchors_and_reversible_context(name, tags):
    e, b = load(ROOT / f'보고서/실험05/결선도/탐색/{name}.py')
    assert b.PLACE[0].leds == tags
    validate_anchors(b.PLACE, b.LAYOUT['leds'], e)
    original = copy.deepcopy(b.LAYOUT)
    candidate = dict(layout=copy.deepcopy(b.LAYOUT), variant=b.search_variants()[-1])
    candidate['layout']['slots'][b.SLOTS[0]] += 1
    with pytest.raises(RuntimeError):
        with b.search_context(candidate, [], [], validation_only=True):
            assert b._source.LAYOUT != original
            raise RuntimeError('restore')
    assert b._source.LAYOUT == original
    assert b.LAYOUT == original


def test_equivalent_gate_swaps_are_whole_bijections():
    _, b = load(ROOT / '보고서/실험05/결선도/탐색/xs3.py')
    assert len(b.search_variants()) == 8
    for v in b.search_variants():
        for u in ('U1', 'U2', 'U3'):
            pins = [b.map_pin(u, p, v) for p in range(1, 15)]
            assert sorted(pins) == list(range(1, 15))
            assert b.map_pin(u, 7, v) == 7
            assert b.map_pin(u, 14, v) == 14
            for p in range(1, 15):
                assert b.map_pin(u, b.map_pin(u, p, v), v) == p
        # HC20's four inputs and output move as a complete unit.
        if v['u2']:
            assert [b.map_pin('U2', p, v) for p in (1, 2, 4, 5, 6)] == [9, 10, 12, 13, 8]
        c = b.search_circuit(v)
        for old, new in zip(b.original_circuit.wires, c.wires):
            for a, z in zip(old[3:5], new[3:5]):
                assert z == (a if a[0] == 'LED' else (a[0], b.map_pin(*a, v)))


def test_single_decoder_search_can_move_to_middle_of_led_column():
    from scripts.lab.fixed_search import slot_candidates
    e, b = load(ROOT / '보고서/실험05/결선도/탐색/bcd.py')
    b.START_ROWS = tuple(range(3, 55))
    assert {'K1': 30} in list(slot_candidates(e, b))


@pytest.mark.parametrize('name,count', [('bcd', 5), ('xs3', 7)])
def test_numeric_baseline_preserves_every_stage_net(name, count):
    from scripts.lab.fixed_search import validate_plan
    e, b = load(ROOT / f'보고서/실험05/결선도/탐색/{name}.py')
    r = b.search_baseline()
    result = validate_plan(e, b, r['candidate'], r['plans'], r['temporaries'])
    assert result['board_count'] == count
    # Bootstrap baseline is a new numeric plan, not the original approved plan.
    assert b.original_layout['leds'][name] != r['candidate']['layout']['leds'][name]


def test_logical_validation_detects_swapped_led_identity():
    _, b = load(ROOT / '보고서/실험05/결선도/탐색/xs3.py')
    r = b.search_baseline()
    with b.search_context(r['candidate'], r['plans'], [], validation_only=True):
        filename, fn = b.FINALS[0]
        bb = fn('/unused.png')
        b.search_assert_equivalent(bb, filename)
        nodes = copy.deepcopy(bb.nets())
        for n in nodes:
            n['labels'] = {x.replace('LED A0', 'LED TMP').replace('LED A1', 'LED A0')
                           .replace('LED TMP', 'LED A1') for x in n['labels']}
        bb.nets = lambda: nodes
        with pytest.raises(AssertionError, match='Logical nets differ'):
            b.search_assert_equivalent(bb, filename)
