"""Real e07 adapter contracts: immutable anchors and identical staged netlists."""
from pathlib import Path
import copy
import pytest
from scripts.lab.place_search import load
from scripts.lab import fixed_search as s

ROOT = Path(__file__).resolve().parents[1]


def test_approved_baseline_validates_all_thirty_boards_without_writing(tmp_path):
    e, b = load(ROOT / '보고서/실험07/결선도/배치.py')
    original = copy.deepcopy(b.LAYOUT)
    row = b.search_baseline()
    result = s.validate_plan(e, b, row['candidate'], row['plans'], row['temporaries'])
    assert result['board_count'] == 30
    assert result['metrics']['crossings'] == 18
    assert result['metrics']['density'] == pytest.approx(3.4736842105263164)
    assert b.LAYOUT == original


def test_all_declared_assignments_preserve_logical_edges_and_control_identity():
    e, b = load(ROOT / '보고서/실험07/결선도/배치.py')
    # Each whole-FF swap is a pin permutation, not swapping J/K or Q/complement.
    variants = b.search_variants()
    assert len(variants) == 16
    logical = b.SHIFT
    for v in variants:
        c = b.search_circuit(v)
        for u, model in c.models.items():
            pins = [b._map_pin(u, p, v) for p in range(1, e.dip_pins(model) + 1)]
            assert sorted(pins) == list(range(1, e.dip_pins(model) + 1))
            for p in range(1, e.dip_pins(model) + 1):
                assert b._map_pin(u, b._map_pin(u, p, v), v) == p
        for old, new in zip(logical.wires, c.wires):
            assert old[:3] == new[:3]
            for old_end, new_end in zip(old[3:5], new[3:5]):
                assert new_end == (old_end if old_end[0] == 'LED' else
                                   (old_end[0], b._map_pin(*old_end, v)))
        inputs = dict((name, (u, p)) for _, name, u, p in b._ORIGINAL_INPUTS)
        with b.search_context(dict(layout=b.LAYOUT, variant=v), [], []):
            for _, name, u, p in b._INPUTS:
                old_u, old_p = inputs[name]
                assert (u, p) == (old_u, b._map_pin(old_u, old_p, v))
    assert b.SHIFT is logical


def test_candidate_context_restores_approved_plan_on_failure():
    e, b = load(ROOT / '보고서/실험07/결선도/배치.py')
    original = b.search_baseline()
    candidate = dict(layout=copy.deepcopy(b.LAYOUT), variant=b.search_variants()[-1])
    candidate['layout']['slots']['S1'] += 1
    with pytest.raises(RuntimeError):
        with b.search_context(candidate, [], [], validation_only=True):
            assert b.LAYOUT != original['candidate']['layout']
            raise RuntimeError('test exception')
    assert b.search_baseline() == original
    assert not b._SEARCH_VALIDATE_ONLY


def test_fixed_order_relaxes_only_pin_order_not_wrong_block_role():
    # Use actual committed e07 where BIT1/2 driver rows are inverted.
    e, b = load(ROOT / '보고서/실험07/결선도/배치.py')
    row = b.search_baseline()
    with b.search_context(row['candidate'], row['plans'], row['temporaries'], validation_only=True):
        bb = b.build_e7_shift('/unused.png')
        assert not bb._block_role_violations()
        bb.led_order_policy = 'pin'
        assert any('엇갈림' in x for x in bb._block_role_violations())
        bb.led_order_policy = 'fixed'
        # A left-chip to right non-LED strip is still prohibited.
        L, R = bb.cols['left'], bb.cols['right']
        bb._segments.append(('sig', [(L['a'], bb.r_y(6)), (R['a'], bb.r_y(58))], 'invalid'))
        assert any('블록 건너기 위반' in x for x in bb._block_role_violations())


def test_ff_variants_preserve_each_terminal_role():
    _, b = load(ROOT / '보고서/실험07/결선도/배치.py')
    # Independently stated package roles, not derived by the mapper under test.
    ff1 = dict(clk=1, pr=2, clr=3, j=4, k=16, q=15, qb=14)
    ff2 = dict(clk=6, pr=7, clr=8, j=9, k=12, q=11, qb=10)
    swapped = dict(nand=4, ff=[True, True, True])
    for u in ('U2', 'U3', 'U4'):
        for role in ff1:
            assert b._map_pin(u, ff1[role], swapped) == ff2[role]
            assert b._map_pin(u, ff2[role], swapped) == ff1[role]
        assert b._map_pin(u, 5, swapped) == 5
        assert b._map_pin(u, 13, swapped) == 13
    assert [b._map_pin('U1', p, swapped) for p in (9, 10, 8)] == [12, 13, 11]


def test_net_equivalence_rejects_a_physically_possible_wrong_led():
    e, b = load(ROOT / '보고서/실험07/결선도/배치.py')
    row = b.search_baseline()
    with b.search_context(row['candidate'], row['plans'], row['temporaries'], validation_only=True):
        bb = b.build_e7_shift('/unused.png')
        b.search_assert_equivalent(bb, b.FINALS[0][0])
        # A swapped pair of LED names preserves geometry but changes observations.
        original = bb.nets
        nodes = copy.deepcopy(original())
        for node in nodes:
            node['labels'] = {x.replace('LED BIT1', 'LED TEMP').replace('LED BIT2', 'LED BIT1')
                              .replace('LED TEMP', 'LED BIT2') for x in node['labels']}
        bb.nets = lambda: nodes
        with pytest.raises(AssertionError, match='equivalence'):
            b.search_assert_equivalent(bb, b.FINALS[0][0])


def test_real_search_budget_and_result_are_independent_of_process_count():
    path = ROOT / '보고서/실험07/결선도/배치.py'
    results = []
    for jobs in (1, 2):
        e, b = load(path)
        before = b.search_baseline()
        result = s.run(e, b, path, s.SearchSpec(b.LAYOUT['leds'], budget=2), jobs=jobs)
        assert result['attempts'] == 2
        assert len(result['rows']) == 2
        assert all(r['candidate']['layout']['leds'] == before['candidate']['layout']['leds']
                   for r in result['rows'])
        assert b.search_baseline() == before
        results.append(result)
    assert results[0] == results[1]
