"""학생이 표 열 순서와 실제 점퍼 순서를 혼동하는 회귀를 검사한다."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from scripts.lab import config
from scripts.lab.netlist_parser import parse_netlist
from scripts.lab.spec_parser import parse_spec

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / '.claude/skills/breadboard-diagram/scripts/render_breadboard.py'


class Locations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        modspec = importlib.util.spec_from_file_location('render_breadboard', ENGINE)
        cls.engine = importlib.util.module_from_spec(modspec)
        modspec.loader.exec_module(cls.engine)
        cls.board = cls.engine.load_board(6)
        cls.tmp = tempfile.TemporaryDirectory()
        cls.path = Path(cls.tmp.name)
        cls.engine.build_all(cls.board, str(cls.path))
        cls.finals = [cls.path / name for name, fn in cls.board.FINALS]

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def data(self, i):
        return json.loads(self.finals[i].with_suffix('.json').read_text(encoding='utf-8'))

    def test_sidecar_captures_actual_jumper_ends(self):
        inputs = self.data(0)['inputs']
        self.assertEqual([r['name'] for r in inputs], ['S', 'E', 'R'])
        self.assertEqual([r['at'] for r in inputs], ['좌 a3', '좌 a4', '좌 a7'])
        self.assertTrue(all(r['rail'] and isinstance(r['x'], (int, float)) for r in inputs))

    def test_sr_map_uses_physical_order_even_when_table_starts_with_E(self):
        from scripts.lab.io_locations import locations_html
        out = locations_html(self.finals[0], ['E', 'S', 'R'])
        self.assertLess(out.index('첫째'), out.index('둘째'))
        self.assertLess(out.index('>S<'), out.index('>E<'))
        self.assertLess(out.index('>E<'), out.index('>R<'))
        self.assertIn('①', out)
        self.assertLess(out.index("Q&#x27;"), out.index('>Q<'))

    def test_d_map_renames_S_and_removes_R(self):
        self.assertEqual([r['name'] for r in self.data(1)['inputs']], ['D', 'E'])

    def test_jk_separates_middle_input_from_left_group(self):
        from scripts.lab.io_locations import locations_html
        out = locations_html(self.finals[2], ['J', 'K', 'CLK', 'Set', 'Reset'])
        self.assertIn('가운데 입력 점퍼', out)
        self.assertIn('왼쪽 입력 점퍼', out)
        self.assertIn('>K<', out)

    def test_subset_keeps_positions_and_marks_unused_inputs(self):
        from scripts.lab.io_locations import locations_html
        out = locations_html(self.finals[0], ['E'])
        self.assertIn('둘째', out)
        self.assertIn('io-muted', out)
        self.assertIn('>S<', out)
        self.assertIn('>R<', out)

    def test_temporary_led_feed_keeps_board_label(self):
        from scripts.lab.io_locations import locations_html
        out = locations_html(self.finals[0], ['E'], feed={"Q'": "D0'"})
        self.assertIn('Q&#x27;', out)
        self.assertIn('지금은 D0&#x27; 확인', out)

    def test_missing_metadata_is_visible(self):
        from scripts.lab.io_locations import locations_html, location_issues
        png = self.path / 'missing.png'
        self.assertIn('입력 위치를 확인할 수 없어요', locations_html(png, ['E']))
        self.assertTrue(location_issues(png, ['E']))

    def test_validator_reports_missing_positions(self):
        from scripts.lab.validate import check_io_locations
        spec = parse_spec(ROOT / config.experiment_dir(6) / '체크리스트/명세.md')
        netlist = parse_netlist(ROOT / config.experiment_dir(6) / '결선도/netlist.md')
        netlist.path = self.path / 'missing-folder' / 'netlist.md'
        findings = check_io_locations(netlist, spec)
        self.assertTrue(findings)
        self.assertTrue(all(f.level == 'warn' for f in findings))

    def test_repeated_signal_keeps_both_physical_jumpers(self):
        from scripts.lab.io_locations import locations_html
        png = self.path / 'fanout.png'
        png.with_suffix('.json').write_text(json.dumps({'inputs': [
            {'name': 'E', 'at': '좌 a3', 'rail': '좌GND레일3행', 'x': 100, 'row': 3},
            {'name': 'E', 'at': '좌 j4', 'rail': '중앙GND레일4행', 'x': 600, 'row': 4},
        ]}), encoding='utf-8')
        self.assertEqual(locations_html(png, ['E']).count('>E<'), 2)

    def test_rail_row_is_used_instead_of_fixed_pin_row(self):
        from scripts.lab.io_locations import locations_html
        png = self.path / 'shifted.png'
        png.with_suffix('.json').write_text(json.dumps({'inputs': [
            {'name': 'A', 'at': '좌 a8', 'rail': '좌GND레일9행', 'x': 100, 'row': 9},
            {'name': 'B', 'at': '좌 a9', 'rail': '좌GND레일7행', 'x': 100, 'row': 7},
        ]}), encoding='utf-8')
        out = locations_html(png, ['A', 'B'])
        self.assertLess(out.index('>B<'), out.index('>A<'))

    def test_record_table_includes_map_without_altering_cells(self):
        from scripts.lab.render import _circuit_tables
        from scripts.lab.leds import board_leds
        spec = parse_spec(ROOT / config.experiment_dir(6) / '체크리스트/명세.md')
        netlist = parse_netlist(ROOT / config.experiment_dir(6) / '결선도/netlist.md')
        section = netlist.circuits[0]
        section.diagram = self.finals[0].name
        netlist.path = self.path / 'netlist.md'
        out = _circuit_tables(spec, section, leds=board_leds(self.finals[0]), netlist=netlist)
        self.assertIn('입력·LED 위치', out)
        self.assertEqual(out.count('class="check"'), 5)
        self.assertIn('1 101.jpg', out)
        self.assertLess(out.index('io-locations'), out.index('<table'))

    def test_stage_uses_current_D_input_and_dims_unobserved_LEDs(self):
        from scripts.lab.render import _stage_html
        spec = parse_spec(ROOT / config.experiment_dir(6) / '체크리스트/명세.md')
        netlist = parse_netlist(ROOT / config.experiment_dir(6) / '결선도/netlist.md')
        section = netlist.circuits[1]
        stage = next(s for s in section.stages if s.get('node'))
        netlist.path = self.path / 'netlist.md'
        out = _stage_html(stage, netlist, section, spec)
        self.assertIn('>D<', out)
        self.assertNotIn('>S<', out)
        self.assertIn('class="io-input io-muted"', out)  # E is physically second but unused here.
        self.assertEqual(out.count('class="io-led io-muted"'), 2)

    def test_validation_includes_inputs_of_earlier_watched_LEDs(self):
        from scripts.lab.validate import check_io_locations
        folder = ROOT / config.experiment_dir(5)
        spec = parse_spec(folder / '체크리스트/명세.md')
        netlist = parse_netlist(folder / '결선도/netlist.md')
        section = netlist.circuits[1]
        final = self.path / section.diagram
        final.touch()
        data = json.loads((folder / '결선도' / section.diagram).with_suffix('.json').read_text(encoding='utf-8'))
        final.with_suffix('.json').write_text(json.dumps(data), encoding='utf-8')
        stage = next(s for s in section.stages if str(s['n']) == '2')
        # Current node D0' uses only D0, but the earlier LED A3 still observes D5.
        stage_png = self.path / stage['diagram']
        stage_png.with_suffix('.json').write_text(json.dumps({'inputs': [
            {'name': 'D0', 'at': '좌 a3', 'rail': '좌GND레일3행', 'x': 100, 'row': 3}
        ]}), encoding='utf-8')
        netlist.path = self.path / 'netlist.md'
        hits = check_io_locations(netlist, spec)
        self.assertTrue(any('C2 단계2' in f.where and 'D5' in f.message for f in hits))
