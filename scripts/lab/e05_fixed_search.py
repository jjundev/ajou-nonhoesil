"""Isolated E05 fixed-LED search adapters; approved builders/assets are never edited.

The two E05 circuits use disjoint slots and C2 explicitly rebuilds the board.
Each adapter therefore searches only its own occupied slots. Logical signatures
are normalized to chip IDs, logical pins, and LED-associated resistor IDs.
"""
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
import copy
import hashlib
import itertools
import json
import re

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / '보고서/실험05/결선도/배치.py'


def configure(ns, name, e):
    src = e.load_board_file(SOURCE, 'e05_original_' + name)
    original_layout = copy.deepcopy(src.LAYOUT)
    original_circuit = src.BCD if name == 'bcd' else src.XS3
    original_inputs = copy.deepcopy(src._BCD_INPUTS if name == 'bcd' else src._XS3_INPUTS)
    original_ties = copy.deepcopy(src._XS3_TIES)
    original_mark_nc = src._mark_nc
    original_paths = src.place_paths
    original_hints = src.place_marker_hints
    tags = tuple(sorted(original_circuit.leds, key=lambda t: int(t[1:])))
    slots = tuple(original_circuit.chips.values())
    layout = dict(slots={s: original_layout['slots'][s] for s in slots},
                  leds={name: dict(zip(tags, sorted(original_layout['leds'][name].values())))},
                  bridge=copy.deepcopy(original_layout['bridge']))
    state = dict(candidate=None, plans=None, validation_only=True)
    cache = {}
    variant0 = dict(u1=False, u2=False, u3=False)

    class SearchRenderer(e.BreadboardRenderer):
        def __init__(self, *a, **kw):
            super().__init__(*a, **kw)
            self.led_order_policy = 'fixed'
            self.route_avoid_bodies = True
            self.validation_only = state['validation_only']

    def map_pin(u, pin, variant):
        if not variant.get(u.lower(), False):
            return pin
        if u == 'U1':
            return {1: 13, 13: 1, 2: 12, 12: 2, 3: 11, 11: 3,
                    4: 10, 10: 4, 5: 9, 9: 5, 6: 8, 8: 6}.get(pin, pin)
        return {1: 9, 9: 1, 2: 10, 10: 2, 4: 12, 12: 4, 5: 13, 13: 5,
                6: 8, 8: 6, 3: 11, 11: 3}.get(pin, pin)

    def variants():
        return [variant0.copy()] if name == 'bcd' else [dict(zip(('u1', 'u2', 'u3'), v))
                      for v in itertools.product((False, True), repeat=3)]

    def circuit(variant):
        def end(p):
            return p if p[0] == 'LED' else (p[0], map_pin(*p, variant))
        def desc(d):
            return re.sub(r'(U[1-4]) pin (\d+)',
                          lambda m: f'{m[1]} pin {map_pin(m[1], int(m[2]), variant)}', d)
        return replace(original_circuit, leds=tags,
                       wires=tuple((s, en, k, end(a), end(b), desc(d))
                                   for s, en, k, a, b, d in original_circuit.wires),
                       inputs=tuple((u, map_pin(u, p, variant)) for _, _, u, p in original_inputs))

    def normalized(bb, lay, variant):
        locations = {(original_circuit.models[u], lay['slots'][slot]): u
                     for u, slot in original_circuit.chips.items()}
        resistors = {str(i + 1): led['tag'] for i, led in enumerate(bb.leds)}
        groups = []
        for net in bb.nets():
            labels = []
            for label in net['labels']:
                m = re.fullmatch(r'(74HC\d+)#(\d+) pin (\d+)', label)
                if m:
                    u = locations[m[1], int(m[2])]
                    label = f'{u} pin {map_pin(u, int(m[3]), variant)}'
                label = re.sub(r'저항(\d+)\(', lambda m: '저항' + resistors[m[1]] + '(', label)
                labels.append(label)
            groups.append((tuple(sorted(labels)), tuple(sorted(net['rails']))))
        return tuple(sorted(groups))

    # Capture original logical connections lazily, without rendering PNGs or
    # changing original module files. Baseline labels are independent of route geometry.
    old_renderer = src.BreadboardRenderer
    def expected():
        if cache:
            return cache
        saved = (src.LAYOUT, src.BCD, src.XS3, src._BCD_LEDS, src._XS3_LEDS,
                 src._BCD_INPUTS, src._XS3_INPUTS, src._XS3_TIES, src.BreadboardRenderer,
                 src.place_paths, src.place_marker_hints, src._mark_nc)
        class ReferenceRenderer(e.BreadboardRenderer):
            def __init__(self, *a, **kw):
                super().__init__(*a, **kw)
                self.validation_only = True
        try:
            src.LAYOUT = original_layout
            if name == 'bcd':
                src.BCD = original_circuit
                src._BCD_LEDS = original_circuit.leds
                src._BCD_INPUTS = original_inputs
            else:
                src.XS3 = original_circuit
                src._XS3_LEDS = original_circuit.leds
                src._XS3_INPUTS = original_inputs
            src._XS3_TIES = original_ties
            src.BreadboardRenderer = ReferenceRenderer
            src.place_paths, src.place_marker_hints = original_paths, original_hints
            src._mark_nc = original_mark_nc
            base = None
            for filename, fn, stage in boards:
                bb = fn('/unused.png', stage=stage, baseline=base)
                cache[filename] = normalized(bb, original_layout, variant0)
                base = bb.snapshot()
            for filename, fn in finals:
                bb = fn('/unused.png')
                cache[filename] = normalized(bb, original_layout, variant0)
        finally:
            (src.LAYOUT, src.BCD, src.XS3, src._BCD_LEDS, src._XS3_LEDS,
             src._BCD_INPUTS, src._XS3_INPUTS, src._XS3_TIES, src.BreadboardRenderer,
             src.place_paths, src.place_marker_hints, src._mark_nc) = saved
        return cache

    def paths(c, lay):
        if state['plans'] is not None and c.name == name:
            return state['plans']
        return original_paths(c, lay)

    def hints(c, lay):
        # Fixed-part markers use the renderer's normal collision settling.
        # Signal markers are settled on the complete routed foundation.
        return {} if state['plans'] is not None else original_hints(c, lay)

    def mark_nc(bb, k, chip, pins):
        u = re.search(r'\((U\d)\)', chip)[1]
        v = state['candidate']['variant'] if state['candidate'] else variant0
        return original_mark_nc(bb, k, chip, tuple(map_pin(u, p, v) for p in pins))

    def apply(lay, variant):
        c = circuit(variant)
        src.LAYOUT = copy.deepcopy(lay)
        if name == 'bcd':
            src.BCD, src._BCD_LEDS = c, tags
            src._BCD_INPUTS = [(s, n, u, map_pin(u, p, variant)) for s, n, u, p in original_inputs]
        else:
            src.XS3, src._XS3_LEDS = c, tags
            src._XS3_INPUTS = [(s, n, u, map_pin(u, p, variant)) for s, n, u, p in original_inputs]
            src._XS3_TIES = {u: tuple(map_pin(u, p, variant) for p in pins) for u, pins in original_ties.items()}
        src.BreadboardRenderer = SearchRenderer
        src.place_paths, src.place_marker_hints, src._mark_nc = paths, hints, mark_nc

    @contextmanager
    def context(candidate, plans, temporaries, validation_only=False):
        saved = (src.LAYOUT, src.BCD, src.XS3, src._BCD_LEDS, src._XS3_LEDS, src._BCD_INPUTS,
                 src._XS3_INPUTS, src._XS3_TIES, src.BreadboardRenderer, src.place_paths,
                 src.place_marker_hints, src._mark_nc, state.copy())
        try:
            state.update(candidate=candidate, plans=plans, validation_only=validation_only)
            apply(candidate['layout'], candidate['variant'])
            yield
        finally:
            (src.LAYOUT, src.BCD, src.XS3, src._BCD_LEDS, src._XS3_LEDS, src._BCD_INPUTS,
             src._XS3_INPUTS, src._XS3_TIES, src.BreadboardRenderer, src.place_paths,
             src.place_marker_hints, src._mark_nc, restored) = saved
            state.clear()
            state.update(restored)

    def fixed(bb, lay, variant):
        with context(dict(layout=lay, variant=variant), [], [], validation_only=True):
            (src._bcd_fixed if name == 'bcd' else src._xs3_fixed)(bb, None, True, lay)

    def equivalent(bb, filename):
        actual = normalized(bb, state['candidate']['layout'], state['candidate']['variant'])
        if actual != expected()[filename]:
            raise AssertionError(f'Logical nets differ: {name} {filename}')

    def drivers(bb, stage):
        if stage is None:  # Removal is performed with power off.
            return
        v = state['candidate']['variant']
        lay = state['candidate']['layout']
        c = circuit(v)
        # Check every gate whose output has been connected in this stage.
        active = set()
        for s, en, _, a, b, _ in c.wires:
            if s <= stage and (en is None or stage <= en):
                active.update(x for x in (a, b) if x[0] != 'LED')
        roles = {'U1': {2: (1,), 4: (3,), 6: (5,), 8: (9,), 10: (11,), 12: (13,)},
                 'U2': {6: (1, 2, 4, 5), 8: (9, 10, 12, 13)},
                 'U3': {6: (1, 2, 4, 5), 8: (9, 10, 12, 13)},
                 'U4': {p: (12, 13, 14, 15) for p in src._BCD_OUT.values()}}
        k = e.place_chips(c, lay)
        def label(u, p):
            return f'{c.models[u]}#{k[u]} pin {p}'
        output_labels = {label(u, p) for u in c.chips for p in roles[u]}
        nets = bb.nets()
        for u in c.chips:
            for out, inputs in roles[u].items():
                if (u, out) not in active:
                    continue
                for pin in inputs:
                    n = next(n for n in nets if label(u, pin) in n['labels'])
                    if not (n['rails'] or output_labels.intersection(n['labels'])
                            or any(x.startswith('입력 ') for x in n['labels'])):
                        raise AssertionError(f'Undriven active input: stage {stage}, {u} pin {pin}')

    def baseline():
        path = Path(ns['__file__']).with_suffix('.json')
        row = json.loads(path.read_text())
        row['provenance'] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                             for p in (SOURCE, Path(__file__), SOURCE.with_name('netlist.md'))}
        return row

    # E05 C1 and C2 share no occupied slot, and transition into C2 rebuilds.
    boards = [r for r in src.BOARDS if ('BCD디코더' if name == 'bcd' else 'Excess3인코더') in r[0]]
    finals = [r for r in src.FINALS if ('BCD디코더' if name == 'bcd' else 'Excess3인코더') in r[0]]
    src._ORDER_NOTE = 'LED 위→아래: Y0→Y9 (숫자순 고정 탐색 후보).'
    apply(layout, variant0)
    ns.update(BOARD='v2', SLOTS=slots, LAYOUT=layout, PLACE=[circuit(variant0)],
              START_ROWS=tuple(range(3, 55)) if name == 'bcd' else e.PLACE_STARTS,
              BOARDS=boards, FINALS=finals, ASSEMBLY_BOARDS={},
              search_variants=variants, search_circuit=circuit, search_temporaries=lambda v: [],
              search_context=context, search_fixed=fixed, search_baseline=baseline,
              search_assert_equivalent=equivalent, search_assert_drivers=drivers,
              map_pin=map_pin, original_circuit=original_circuit, _source=src,
              original_layout=original_layout, normalize=normalized, expected=expected)
