"""Lower rail bridges: real geometry, exact holes and legacy compatibility."""
import copy
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def engine():
    spec = importlib.util.spec_from_file_location(
        'render_breadboard', ROOT / '.claude/skills/breadboard-diagram/scripts/render_breadboard.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def circuit(e, signal_row=13):
    def fixed(bb, stage, superset=False, layout=None):
        bb.connect_jacks()
        bb.connect_rail_bridges(layout)
        L = bb.cols['left']
        bb.step_wire([(L['a'], bb.r_y(signal_row)), (L['j'], bb.r_y(signal_row))],
                     'sig', 'fixed signal')
    return e.PlaceCircuit('toy', {'U1': 'K1'}, {'U1': '74HC04'}, (), (), fixed)


def test_selects_nearest_clear_lower_pair_without_mutating_layout(engine):
    lay = {'slots': {'K1': 3}, 'leds': {'toy': {}}, 'bridge': [12, 13]}
    before = copy.deepcopy(lay)
    got = engine.place_lower_bridges([circuit(engine)], lay)
    # Chip ends at row 9; 12/13 collide with signal row 13; 14 has no rail holes.
    assert got['bridge'] == [15, 16]
    assert lay == before
    assert got['bridge_policy'] == 'lower-clearance-v1'
    for stage in (1, None):
        bb = engine.BreadboardRenderer(board='v2')
        circuit(engine).fixed(bb, stage, layout=got)
        assert not bb.bridge_clearance_problems()
        assert [b[1][-1] for b in bb.bridges] == [15, 16]


def test_exact_pair_rejects_occupied_hole_instead_of_snapping(engine):
    bb = engine.BreadboardRenderer(board='v2')
    L = bb.cols['left']
    bb.step_wire([(L['gnd'], bb.r_y(15)), (L['a'], bb.r_y(15))], 'gnd', 'occupied')
    old = copy.deepcopy(bb.bridges)
    with pytest.raises(ValueError, match='브리지'):
        bb.connect_rail_bridges({'bridge': [15, 16], 'bridge_policy': 'lower-clearance-v1'})
    assert bb.bridges == old


def test_clearance_rejects_crossing_and_near_parallel_but_not_remote_wire(engine):
    for shape, want_bad in [('cross', True), ('parallel', True), ('remote', False)]:
        bb = engine.BreadboardRenderer(board='v2')
        bb.connect_rail_bridges({'bridge': [15, 16], 'bridge_policy': 'lower-clearance-v1'})
        L, R = bb.cols['left'], bb.cols['right']
        y = bb.r_y(15)
        paths = {
            'cross': [(L['b'], bb.r_y(13)), (L['b'], bb.r_y(17))],
            'parallel': [(L['a'], y - bb.spec.row_pitch / 2),
                         (L['j'], y - bb.spec.row_pitch / 2)],
            'remote': [(R['b'], y), (R['j'], y)],
        }
        bb.step_wire(paths[shape], 'sig', shape)
        assert bool(bb.bridge_clearance_problems()) is want_bad


def test_legacy_bridges_keep_existing_snap_behavior(engine):
    bb = engine.BreadboardRenderer(board='v2')
    L = bb.cols['left']
    bb.step_wire([(L['gnd'], bb.r_y(15)), (L['a'], bb.r_y(15))], 'gnd', 'occupied')
    bb.bridge_rails(L['gnd'], L['mid_gnd'], 15)
    assert bb.bridges[0][1][-1] == 16


def test_no_clear_space_fails_instead_of_picking_crowded_pair(engine):
    # Last chip ends at 57; only legal candidate is 60/61; signal occupies row 60.
    lay = {'slots': {'K1': 51}, 'leds': {'toy': {}}, 'bridge': [60, 61]}
    with pytest.raises(AssertionError, match='브리지'):
        engine.place_lower_bridges([circuit(engine, 60)], lay)


def test_one_pitch_clearance_is_enough_and_does_not_force_bottom(engine):
    lay = {'slots': {'K1': 3}, 'leds': {'toy': {}}, 'bridge': [12, 13]}
    assert engine.place_lower_bridges([circuit(engine, 11)], lay)['bridge'] == [12, 13]


def test_fixed_search_opt_in_expands_lower_pairs_and_preserves_leds(engine):
    from scripts.lab import fixed_search as fs
    from types import SimpleNamespace
    c = engine.PlaceCircuit('toy', {'U1': 'K1'}, {'U1': '74HC04'}, (), (), lambda *a: None)
    lay = {'slots': {'K1': 3}, 'leds': {'toy': {}}, 'bridge': [12, 13]}
    board = SimpleNamespace(PLACE=[c], SLOTS=('K1',), LAYOUT=lay,
                            search_variants=lambda: ['original'])
    before = copy.deepcopy(lay)
    spec = fs.SearchSpec(lay['leds'], budget=16, lower_bridges=True)
    candidates = fs.candidates(engine, board, spec)
    assert candidates[0]['layout']['bridge'] == [12, 13]
    assert candidates[1]['layout']['bridge'] == [15, 16]
    assert all(x['layout']['bridge_policy'] == 'lower-clearance-v1' for x in candidates)
    assert all(x['layout']['leds'] == lay['leds'] for x in candidates)
    assert board.LAYOUT == before


def test_exact_second_hole_failure_leaves_both_bridges_unwritten(engine):
    bb = engine.BreadboardRenderer(board='v2')
    L = bb.cols['left']
    bb.step_wire([(L['vcc'], bb.r_y(16)), (L['a'], bb.r_y(16))], 'vcc', 'occupied')
    with pytest.raises(ValueError, match='브리지'):
        bb.connect_rail_bridges({'bridge': [15, 16], 'bridge_policy': 'lower-clearance-v1'})
    assert not bb.bridges


def test_candidate_rejected_by_stage_validation_tries_next_pair(engine):
    lay = {'slots': {'K1': 3}, 'leds': {'toy': {}}, 'bridge': [12, 13]}
    visited = []
    def verify(candidate):
        visited.append(candidate['bridge'])
        return 'temporary stage crosses bridge' if candidate['bridge'] == [12, 13] else None
    assert engine.place_lower_bridges([circuit(engine, 5)], lay, verify=verify)['bridge'] == [15, 16]
    assert visited == [[12, 13], [15, 16]]


def test_wrong_actual_holes_and_missing_bridges_are_rejected(engine):
    bb = engine.BreadboardRenderer(board='v2')
    bb.connect_rail_bridges({'bridge': [15, 16]})
    with pytest.raises(AssertionError, match='브리지'):
        engine.check_lower_bridges(bb, {'bridge': [16, 17], 'bridge_policy': 'lower-clearance-v1'})


@pytest.mark.parametrize('a,b,c,d,want', [
    ((0, 0), (10, 0), (5, -1), (5, 1), 0),
    ((0, 0), (10, 0), (5, 0), (20, 0), 0),
    ((0, 0), (10, 0), (12, 0), (20, 0), 2),
    ((0, 0), (10, 0), (2, 4), (8, 4), 4),
    ((0, 0), (10, 0), (2, 4), (8, 10), 4),
])
def test_distance_handles_crossings_overlap_parallel_and_diagonal(engine, a, b, c, d, want):
    assert engine._segment_distance(a, b, c, d) == pytest.approx(want)


def test_fixed_selection_does_not_push_already_clear_pair_further_down():
    from scripts.lab import fixed_search as fs
    def row(name, pair, density):
        return dict(key=name, valid=True, stage_density=density, weight=.5, order='original',
                    candidate=dict(layout={'slots': {'K1': 3}, 'leds': {}, 'bridge': pair,
                                           'bridge_policy': 'lower-clearance-v1'}, variant='original'),
                    metrics=dict(length=10, density=density, crossings=0, bends=2))
    near, far = row('near', [15, 16], 2), row('far', [60, 61], 0)
    assert fs.select([far, near])[0]['key'] == 'near'


def test_real_fixed_adapter_checks_lower_policy_on_all_preparation_and_stage_boards():
    from scripts.lab.place_search import load
    from scripts.lab import fixed_search as fs
    e, board = load(ROOT / '보고서/실험07/결선도/배치.py')
    original = copy.deepcopy(board.LAYOUT)
    baseline = board.search_baseline()
    baseline['candidate']['layout']['bridge_policy'] = 'lower-clearance-v1'
    result = fs.validate_plan(e, board, baseline['candidate'], baseline['plans'], baseline['temporaries'])
    assert result['board_count'] == 36
    assert board.LAYOUT == original


def test_cli_rejects_lower_policy_when_legacy_mode_would_ignore_it():
    from scripts.lab import place_search
    with pytest.raises(SystemExit) as exc:
        place_search.main(['/nonexistent/배치.py', '--lower-bridges'])
    assert exc.value.code == 2
