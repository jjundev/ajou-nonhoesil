"""Regressions for fixed LED search: feasibility, measured tradeoffs and budget."""
import copy
import pytest
from scripts.lab.place_search import load
from scripts.lab import fixed_search as s
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_length_band_uses_shortest_valid_not_baseline():
    rows = [dict(key='short', valid=True, metrics=dict(length=100, density=8, crossings=1, bends=2), stage_density=8),
            dict(key='clear', valid=True, metrics=dict(length=110, density=1, crossings=4, bends=3), stage_density=2),
            dict(key='too-long', valid=True, metrics=dict(length=111, density=0, crossings=0, bends=0), stage_density=0),
            dict(key='invalid-short', valid=False, metrics=dict(length=10, density=0, crossings=0, bends=0), stage_density=0)]
    chosen, shortest, band = s.select(rows, 1.10)
    assert (chosen['key'], shortest['key']) == ('clear', 'short')
    assert band == pytest.approx(110)


def test_geometric_crossings_include_diagonals_and_deduplicate_vertices():
    paths = [[(0, 0), (2, 2), (4, 4)], [(0, 4), (4, 0)], [(2, -1), (2, 5)]]
    assert s.crossings(paths) == 1
    assert s.crossings([[(0, 0), (2, 0)], [(2, 0), (2, 2)]]) == 0
    assert s.crossings([[(0, 0), (4, 0)], [(2, 0), (6, 0)]]) == 0


def test_fixed_leds_do_not_follow_chip_rows_and_reject_reversed_order():
    e, b = load(ROOT / '보고서/실험07/결선도/배치.py')
    anchors = copy.deepcopy(b.LAYOUT['leds'])
    spec = s.SearchSpec(anchors, budget=4)
    candidates = s.candidates(e, b, spec)
    assert len(candidates) > 8
    assert all(c['layout']['leds'] == anchors for c in candidates)
    anchors['shift']['BIT1'], anchors['shift']['BIT2'] = 18, 14
    with pytest.raises(ValueError, match='order'):
        s.candidates(e, b, s.SearchSpec(anchors))


def test_budget_continues_after_improvement_and_rejects_zero():
    with pytest.raises(ValueError):
        s.SearchSpec({}, budget=0)
    todo = [dict(key=str(i)) for i in range(12)]
    seen = []
    def evaluate(task):
        seen.append(task['key'])
        return dict(task, valid=True)
    results = s.evaluate_batch(todo, 5, evaluate)
    assert len(results) == 5
    assert seen == ['0', '1', '2', '3', '4']


def test_route_priority_returns_paths_in_canonical_wire_order():
    e, b = load(ROOT / 'tests/fixtures/board_v2_e4/배치.py')
    c = b.PLACE[0]
    n = len(c.wires)
    # Incorrectly assigning routing priority to student wire IDs breaks endpoint identity.
    order = s.wire_order(e, c, b.LAYOUT, 'long')
    assert sorted(order) == list(range(n))
    originals = [(i, 'marker') for i in order]
    assert s.canonical_paths(originals, order) == [(i, 'marker') for i in range(n)]


def test_opening_budget_spreads_over_layouts_and_assignments():
    e, b = load(ROOT / '보고서/실험07/결선도/배치.py')
    cs = s.candidates(e, b, s.SearchSpec(b.LAYOUT['leds']))[:128]
    assert len({s.key(c['layout']) for c in cs}) >= 32
    assert len({s.key(c['variant']) for c in cs}) == 16


def test_original_input_rail_row_does_not_prune_alternative_gate():
    e, b = load(ROOT / '보고서/실험07/결선도/배치.py')
    wanted = {'S1': 16, 'S2': 4, 'S3': 27, 'S4': 39}
    # NAND3 D(pin9) shares row21 with BIT2's GND landing. NAND4 D(pin12)
    # sits at row18; in either case a rail jumper may choose a free rail hole
    # without moving the LED. This is not a sound whole-layout rejection.
    cs = s.candidates(e, b, s.SearchSpec(b.LAYOUT['leds']))
    assert any(c['layout']['slots'] == wanted and c['variant']['nand'] == 4 for c in cs)


def test_noncorner_power_package_is_not_pruned_by_corner_row_assumption():
    e, b = load(ROOT / '보고서/실험07/결선도/배치.py')
    # HC76 VCC is pin5, not pin16. A pin1 row of38 (empty rail row)
    # is therefore not a physically impossible chip placement.
    wanted = {'S1': 16, 'S2': 4, 'S3': 27, 'S4': 38}
    cs = s.candidates(e, b, s.SearchSpec(b.LAYOUT['leds']))
    assert any(c['layout']['slots'] == wanted for c in cs)


def test_policy_budget_covers_all_weights_and_orders_instead_of_truncating_high_weights():
    seeds = [dict(candidate=dict(layout={'slots': {'S1': i}}, variant={'id': i})) for i in range(8)]
    tasks = s.policy_tasks(seeds, 64)
    first_budget = tasks[:64]
    assert {t['weight'] for t in first_budget} == {0., .5, 2., 4.}
    assert {t['order'] for t in first_budget} == {'original', 'long', 'led', 'fanout'}
    for c in {s.key(t['candidate']) for t in first_budget}:
        settings = {(t['weight'], t['order']) for t in first_budget if s.key(t['candidate']) == c}
        assert len(settings) == 16
