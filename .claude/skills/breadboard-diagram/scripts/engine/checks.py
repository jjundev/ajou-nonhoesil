# 결선도 엔진 조각 — 검사(R5~R17·넷 모형·verify).
# 단독으로 import 하지 않는다. `../render_breadboard.py` 가 조각들을 `_PARTS` 순서대로 자기
# 이름공간에서 실행한다 — 앞 조각의 이름(import·상수·함수)을 import 없이 그대로 쓴다.

class _RuleChecks:
    """`BreadboardRenderer` 의 검사 쪽 — R5~R17 와 넷 모형. `export()` 직전에 `verify()` 가 돈다.
    그리기 상태(`_leads`·`_segments`·`chips` …)는 `BreadboardRenderer.__init__` 이 만든다."""

    def side_leads(self):
        """칩마다 양쪽(a~d / g~j) 핀 행에 꽂힌 리드 수 — R7 의 지표. 점유표(`_leads`)만 읽는다.
        `wiring()` 에 넣지 않는다 — `content()` 가 통째로 해시해 지난 주차 도장이 전부 깨진다.
        """
        out = []
        for ch in self.chips:
            c = self.cols[ch['block']]
            rows = range(ch['pin1_row'], ch['pin1_row'] + len(ch['pins']) // 2)
            for side, names in SIDE_COLS.items():
                xs = {c[k] for k in names}
                holes = sorted((h for h in self._leads if h[0] in xs and h[1] in rows),
                               key=lambda h: (h[1], h[0]))
                out.append({'chip': ch['label'], 'block': ch['block'],
                            'pin1_row': ch['pin1_row'], 'side': side, 'count': len(holes),
                            'addrs': [self.addr(x, self.r_y(r)) for x, r in holes]})
        return out

    def chip_side_of(self, end):
        """`_endpoint()` 결과가 어느 칩의 어느 쪽 핀 스트립인가 — 칩 행 안 a~d 는 'a', g~j 는 'f'.
        e·f·칩 행 밖·레일·잭은 None. 같은 이름의 칩이 둘일 수 있어(실험02 t_pd) `pin1_row` 로 가른다.
        """
        if end[0] != 'hole' or end[1] is None:
            return None
        blk, col, row = end[1]
        for ch in self.chips:
            if ch['block'] == blk and ch['pin1_row'] <= row <= ch['pin1_row'] + len(ch['pins']) // 2 - 1:
                for side, names in SIDE_COLS.items():
                    if col in names:
                        return {'chip': ch['label'], 'block': blk, 'pin1_row': ch['pin1_row'], 'side': side}
                return None
        return None

    def cross_side_wires(self):
        """R8 의 지표 — 같은 블록의 **서로 다른 두 칩** 핀 스트립을 잇는 배선 중 양 끝 쪽이 다른 것
        (2026-09-20 격리 시험판의 X자). 예외는 `test_breadboard_physical.py` `KNOWN_CROSS_SIDE`.
        같은 칩 안 사슬·다른 블록 사이는 안 본다. 가닥 단위라 중계 스트립을 거친 두 가닥은 못 본다.
        `wiring()` 에 넣지 않는다 — 도장.
        """
        out = []
        for _kind, pts, desc in self._segments:
            a = self.chip_side_of(self._endpoint(pts[0]))
            b = self.chip_side_of(self._endpoint(pts[-1]))
            if not a or not b or a['block'] != b['block']:
                continue
            if (a['chip'], a['pin1_row']) == (b['chip'], b['pin1_row']) or a['side'] == b['side']:
                continue
            out.append({'frm': self.addr(*pts[0]), 'to': self.addr(*pts[-1]), 'desc': desc,
                        'from_side': a, 'to_side': b})
        return out

    # ---------------- 읽기 규칙 R11~R14 (spec.readability, v2) ----------------
    # R1~R10 을 통과하고도 따라 그릴 수 없던 그림을 잡는다 — `docs/plans/2026-10-03-실험04-v2-시험판-결과.md`.
    # v1 승인본은 소급하지 않는다.

    def _chip_bodies(self):
        """칩마다 (몸통 상자, 칩 기둥 가운데 x, 칩) — 몸통은 e·f 핀 열 안쪽, pin 1 행 위 ~ 마지막 a쪽 핀 행 아래."""
        out = []
        for ch in self.chips:
            c = self.cols[ch['block']]
            box = (c['chip_x1'] - 1, self.r_y(ch['pin1_row']) - 10,
                   c['chip_x2'] + 1, self.r_y(ch['pin1_row'] + len(ch['pins']) // 2 - 1) + 10)
            out.append((box, (c['e'] + c['f']) / 2, ch))
        return out

    @staticmethod
    def _seg_in_box(a, b, box):
        """구간 ab 가 상자 **안쪽**을 지나가는가 — 2px 간격으로 훑는다(대각선도 잡는다)."""
        x0, y0, x1, y1 = box
        # 범위가 상자와 안 겹치면 훑지 않는다. 여유 1 — 훑기 점은 반올림으로 끝점을 ulp 만큼 넘는다
        # (0.7000000000000001 → 1.8 의 끝 점은 1.8000000000000003). 2026-10-05 배선기 속도.
        if max(a[0], b[0]) < x0 - 1 or min(a[0], b[0]) > x1 + 1 or max(a[1], b[1]) < y0 - 1 or min(a[1], b[1]) > y1 + 1:
            return False
        n = int(max(abs(b[0] - a[0]), abs(b[1] - a[1])) / 2) + 1
        return any(x0 < a[0] + (b[0] - a[0]) * t / n < x1 and y0 < a[1] + (b[1] - a[1]) * t / n < y1
                   for t in range(n + 1))

    def marker_problems(self):
        """R11 — 번호 원이 가리는 것: 꽂힌 홀(끝점·부품 다리), 다른 번호 원, 칩 몸통(칩 이름·핀
        번호), 그리고 **둘 이상의** 배선(원은 자기 배선 위에 앉으니 둘째부터는 남의 것이다)."""
        out = []
        boxes = self.marker_boxes
        for i, (x0, y0, x1, y1) in enumerate(boxes):
            at = f'번호 원({x0 + 8},{y0 + 8})'
            for (hx, hr), what in self._leads.items():
                if x0 - 1 <= hx <= x1 + 1 and y0 - 1 <= self.r_y(hr) <= y1 + 1:
                    out.append(f'{at} 이 꽂힌 홀 {self.addr(hx, self.r_y(hr))} 을 가린다')
            for b in boxes[i + 1:]:
                if not (x1 <= b[0] or b[2] <= x0 or y1 <= b[1] or b[3] <= y0):
                    out.append(f'{at} 과 번호 원({b[0] + 8},{b[1] + 8}) 이 겹친다')
            for b, _cx, ch in self._chip_bodies():
                if not (x1 <= b[0] or b[2] <= x0 or y1 <= b[1] or b[3] <= y0):
                    out.append(f"{at} 이 칩 {ch['label']}({ch['pin1_row']}행) 몸통을 가린다")
            under = [d for _k, pts, d in self._segments
                     if any(self._seg_in_box(a, b, (x0, y0, x1, y1)) for a, b in zip(pts, pts[1:]))]
            if len(under) > 1:
                out.append(f'{at} 아래 배선 {len(under)}가닥: {", ".join(under)}')
        return out

    def wires_over_holes(self):
        """R12 — 신호선(`sig`·`mid`)이 끝점 말고 지나가는 홀 — 꽂힌 것인지 지나가는 것인지 안 보인다.
        전원·브리지·잭 선과 입력 점퍼는 안 본다."""
        input_segs = {inp['seg'] for inp in self.inputs}
        out = []
        for i, (kind, pts, desc) in enumerate(self._segments):
            if kind not in ('sig', 'mid') or i in input_segs:
                continue
            ends = {self.hole_at(*pts[0]), self.hole_at(*pts[-1])}
            seen = []
            for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
                n = max(1, int(max(abs(x1 - x0), abs(y1 - y0)) / 2))
                for t in range(n + 1):
                    h = self.hole_at(x0 + (x1 - x0) * t / n, y0 + (y1 - y0) * t / n)
                    if h is not None and h not in ends and h not in seen:
                        seen.append(h)
            if seen:
                out.append(f"{desc}: {', '.join(self.addr(x, self.r_y(r)) for x, r in seen[:4])}"
                           + (f' 외 {len(seen) - 4}' if len(seen) > 4 else ''))
        return out

    def needless_body_crossings(self):
        """R13 — 양 끝이 칩 기둥의 같은 쪽인데 그 칩 몸통에 들어가는 신호선. 양 끝이 다른 쪽이면 한 번은
        건너야 해서 안 본다. 들어가기만 해도 본다 — e·f 사이 골을 세로로 타는 선은 R12 가 못 본다."""
        out = []
        for kind, pts, desc in self._segments:
            if kind not in ('sig', 'mid'):
                continue
            for box, cx, ch in self._chip_bodies():
                if (pts[0][0] < cx) != (pts[-1][0] < cx):
                    continue
                if any(self._seg_in_box(a, b, box) for a, b in zip(pts, pts[1:])):
                    out.append(f"{desc} — 칩 {ch['label']}({ch['pin1_row']}행)")
        return out

    def assembly_signals(self):
        """준비 그림에 있으면 안 되는 새 신호선. 입력 점퍼의 0 자리는 임시 고정이라 뺀다(`references/assembly.md`)."""
        held = {('sig', self._endpoint(self._segments[i['seg']][1][0]), self._endpoint(self._segments[i['seg']][1][-1]))
                for i in self.inputs}
        return [k for k in self.new_signal if k not in held]

    def _display_boxes(self):
        """표시기 몸통과 그 저항 몸통 상자, 눕힌 풀업 저항(`pull_up`)의 다리~다리 상자 — 없으면 빈 목록이다."""
        return [b for d in self.displays for b in d['boxes']] + list(getattr(self, 'part_boxes', ()))

    def wires_over_display(self):
        """R15 — 표시기·표시기 저항 몸통 위를 지나는 배선. 숫자를 가리거나 다리가 안 보인다."""
        out = []
        for _kind, pts, desc in self._segments:
            if any(self._seg_in_box(a, b, box) for box in self._display_boxes()
                   for a, b in zip(pts, pts[1:])):
                out.append(desc)
        return out

    @staticmethod
    def _segs_cross(p, q, r, s):
        """구간 pq 와 rs 가 **서로의 안쪽에서** 엇갈리는가 — 끝점 맞닿음·한 직선 위 포개짐은 아니다
        (포개짐은 R4 몫이다). 방향 부호가 양쪽 다 엄격히 갈려야 참이다."""
        def turn(a, b, c):
            v = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
            return (v > 1e-9) - (v < -1e-9)
        return (turn(p, q, r) * turn(p, q, s) < 0) and (turn(r, s, p) * turn(r, s, q) < 0)

    def input_crossings(self):
        """R16 — 입력 점퍼끼리 X자로 엇갈림. 레일 빈 행 때문에 `free_rail_row` 가 레일 끝을 다른 행으로
        밀면 점퍼가 사선이 되고, 이웃 입력과 엇갈리면 어느 끝이 어느 입력인지 안 읽힌다(2026-11-09 실험09 C2)."""
        segs = [(inp['name'], self._segments[inp['seg']][1]) for inp in self.inputs]
        out = []
        for i, (n1, p) in enumerate(segs):
            for n2, q in segs[i + 1:]:
                if any(self._segs_cross(a, b, c, d) for a, b in zip(p, p[1:]) for c, d in zip(q, q[1:])):
                    out.append(f'{n1}({self.addr(*p[0])} → {self.addr(*p[-1])}) 과 '
                               f'{n2}({self.addr(*q[0])} → {self.addr(*q[-1])}) 이 엇갈린다')
        return out

    def badge_hits(self, box, seg):
        """신호 이름 배지 상자 하나가 가리는 것 — 번호 원, 꽂힌 홀, 자기 것(`seg`)이 아닌 배선, 다른 배지."""
        def inter(a, b):
            return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])
        hits = [f'번호 원 {m}' for m in self.marker_boxes if inter(box, m)]
        for (hx, hr), what in self._leads.items():
            if box[0] <= hx <= box[2] and box[1] <= self.r_y(hr) <= box[3]:
                hits.append(f'홀 {what}')
        for j, (_kind, pts, desc) in enumerate(self._segments):
            if j == seg:
                continue
            for (ax, ay), (bx, by) in zip(pts, pts[1:]):
                n = int(max(abs(bx - ax), abs(by - ay)) / 2) + 1
                if any(box[0] < ax + (bx - ax) * k / n < box[2]
                       and box[1] < ay + (by - ay) * k / n < box[3] for k in range(n + 1)):
                    hits.append(f'배선 {desc}')
                    break
        hits += [f'배지 {n}' for n, b, _s in self.tag_boxes if b is not box and inter(box, b)]
        return hits

    def badge_problems(self):
        """R17 — 신호 이름 배지가 가리는 것. 그리는 순서와 무관하게 다 그린 뒤에 본다 — 번호 원은 이미 그린
        배지만 비켜 가서, 아직 안 그린 이웃 입력의 배지 위에 앉을 수 있었다(2026-11-09 실험09 C2)."""
        return [f"{name}: {', '.join(hits)}" for name, box, seg in self.tag_boxes
                for hits in [self.badge_hits(box, seg)] if hits]

    def wires_over_chip_labels(self):
        """R14 — 칩 이름 글자 위를 지나는 배선(전원선 포함). R13 이 허용한 칩 안 이어 가기도 이름
        위아래 반 행으로 건넌다 — 한복판을 건너면 어느 칩인지 안 읽힌다(2026-10-04)."""
        out = []
        for _kind, pts, desc in self._segments:
            for box, ch in self.chip_label_boxes:
                if any(self._seg_in_box(a, b, box) for a, b in zip(pts, pts[1:])):
                    out.append(f"{desc} — 칩 {ch['label']}({ch['pin1_row']}행)")
        return out

    def _zone(self, end, shared):
        """끝점이 어느 블록 편인가 — 단자대·바깥 레일은 그 블록, 두 블록이 같이 쓰는 레일
        (`shared`, v2 가운데)과 잭·여백은 None."""
        if end[0] != 'hole' or end[1] is None:
            return None
        block, col, _row = end[1]
        return None if self.cols[block][col] in shared else block

    def block_crossings(self):
        """R10 의 지표 — 양 끝이 서로 다른 블록인 배선. 레일↔레일 전원 브리지는 뺀다.
        `wiring()` 에 넣지 않는다 — 도장."""
        shared, out = self._shared_xs(), []
        for _kind, pts, desc in self._segments:
            a, b = self._endpoint(pts[0]), self._endpoint(pts[-1])
            za, zb = self._zone(a, shared), self._zone(b, shared)
            if {za, zb} != {'left', 'right'}:
                continue
            if self._strip(a[1])[0] == 'rail' and self._strip(b[1])[0] == 'rail':
                continue
            out.append({'ends': {za: a[1], zb: b[1]}, 'desc': desc,
                        'frm': self.addr(*pts[0]), 'to': self.addr(*pts[-1])})
        return out

    def _block_role_violations(self):
        """R10 — LED 전용 블록으로 건너는 선은 칩 핀 스트립 → LED 사슬 신호 스트립뿐이고, 건너는
        선끼리 위아래 순서가 LED 순서와 같다. '출력' 인지는 안 본다(2026-10-03). v1 은 빈 목록.
        """
        led_blocks = self.spec.led_only_blocks
        if not led_blocks:
            return []
        chip_strips = {self._strip(sym) for ch in self.chips
                       if ch['block'] in self.spec.chip_blocks for sym in ch['pins'].values()}
        led_strips = {self._strip(ch['signal']) for ch in self.led_chains
                      if ch['signal'] is not None and ch['signal'][0] in led_blocks}
        led_strips |= {self._strip(sym) for d in self.displays for sym in d['seg_strips'].values()}
        if getattr(self, 'led_block_parts', None):
            # 주차 예외(`LED_BLOCK_PARTS_REASON`) — 그 블록의 저항·가변저항 스트립과 바깥 레일도 받는다(실험10)
            led_strips |= {self._strip(r[k]) for r in self.lying for k in ('top', 'bottom')
                           if r[k] is not None and r[k][0] in led_blocks}
            led_strips |= {self._strip(sym) for p in self.pots for sym in (*p['ends'], p['wiper'])
                           if sym[0] in led_blocks}
            led_strips |= {('rail', self.cols[b][k]) for b in led_blocks for k in ('gnd', 'vcc')}
        bad, ok = [], []
        for w in self.block_crossings():
            led_end = next((s for z, s in w['ends'].items() if z in led_blocks), None)
            chip_end = next((s for z, s in w['ends'].items() if z not in led_blocks), None)
            if (led_end is None or chip_end is None
                    or self._strip(chip_end) not in chip_strips
                    or self._strip(led_end) not in led_strips):
                bad.append(f"R10 블록 건너기 위반: {w['frm']} → {w['to']} · {w['desc']} — "
                           "블록을 건너는 선은 칩 핀 스트립에서 LED 사슬 스트립으로만 간다")
            else:
                ok.append((led_end[2], chip_end[2], w))
        if getattr(self, 'led_order_policy', 'pin') == 'fixed':
            return bad
        ok.sort(key=lambda t: t[0])
        for (_l1, c1, w1), (_l2, c2, w2) in zip(ok, ok[1:]):
            if c1 > c2:
                bad.append(f"R10 건너는 선 엇갈림: {w1['frm']} → {w1['to']} / "
                           f"{w2['frm']} → {w2['to']} — 칩 쪽 행 순서를 LED 순서와 맞춘다")
        return bad

    def wiring(self):
        """이 그림이 무엇을 어디에 꽂았는지 **기호 좌표**(블록, 열, 행)로 낸다 — 손그림 검토
        (`review-hand-diagram`)의 정답이고, 손그림 전사와 같은 주소 말을 쓴다. `content()` 가 해시한다.
        `overlaps` 는 `verify()` 가 채운다 — 잘 안 보이는 선을 판정문에 달려고.
        """
        wires = [{'kind': kind, 'desc': desc,
                  'frm': self._endpoint(pts[0]), 'to': self._endpoint(pts[-1])}
                 for kind, pts, desc in self._segments]
        out = {
            'chips': list(self.chips),
            'wires': wires,
            'inputs': [dict(i) for i in self.inputs],
            # 이름 붙은 계측 지점 — 입력 점퍼도 LED 도 없는 주차(실험02)의 H15 대상
            'probes': [{'name': p['name'], 'at': p['at']}
                       for p in self.probes if p.get('name')],
            'leds': list(self.leds),
            'resistors': list(self.resistors),
            'chains': list(self.led_chains),
            'unused_inputs': list(self.unused_inputs),
            'unused_outputs': list(self.unused_outputs),
            'bridges': list(self.bridges),
            'overlaps': list(self.overlap_warnings),
        }
        if self.displays:
            out['displays'] = list(self.displays)    # 표시기 없는 주차는 키가 없다 — 옛 도장이 그대로다
        if getattr(self, 'pots', None):
            out['pots'] = list(self.pots)            # 가변저항 없는 주차는 키가 없다(실험10)
        return out

    def input_node(self, name, x, row):
        """**방금 그린 배선**을 입력 점퍼로 적어 둔다(`_input_jumper` 가 부른다). 넷 검사는 그 레일 끝을
        가상 입력 노드로 센다 — 안 그러면 입력이 전부 GND 와 한 넷이다.

        `x`·`row` 는 좌표가 아니라 **직전 세그먼트가 그 홀에서 끝났는지 보는 단언**이다 — 사이에 배선이
        끼면 엉뚱한 세그먼트가 입력이 되고 그림은 멀쩡하게 나온다.
        """
        seg = len(self._segments) - 1
        assert seg >= 0, f'input_node({name}) 앞에 step_wire() 가 없다'
        ex, ey = self._segments[seg][1][-1]
        end, here = self.sym(ex, self._row_of(ey)), self.sym(x, row)
        assert end == here, (
            f'input_node({name}) 이 가리키는 홀 {here} 이 직전 배선의 끝점 {end} 과 '
            f'다르다 — input_node() 는 그 입력 점퍼를 그린 step_wire() 바로 뒤에 와야 한다')
        self.inputs.append({'name': name, 'at': here, 'seg': seg})

    _AE = ('a', 'b', 'c', 'd', 'e')
    _FJ = ('f', 'g', 'h', 'i', 'j')

    def _strip(self, sym):
        """기호 좌표 -> 스트립 키. **홀이 아니라 스트립이 넷의 단위다** — 한 행의 a~e·f~j 가 각각 한
        스트립, 전원 레일은 열 하나가 통째로 한 스트립(행 없음).
        """
        if sym is None:
            return None
        block, col, row = sym
        if col in self._AE:
            return (block, 'ae', row)
        if col in self._FJ:
            return (block, 'fj', row)
        return ('rail', self.cols[block][col])

    def _pin_label(self, ch, p):
        """칩 핀의 넷 라벨. 한 그림에 같은 칩이 둘이면(`e2_tpd`) 행으로 갈린다."""
        return f"{ch['label']}#{ch['pin1_row']} pin {p}"

    def _lead_labels(self):
        """부품 다리의 (넷 라벨, 기호 좌표) 목록. `nets()` 와 R5ⓒ 가 같은 라벨을 쓰도록 한 자리에 둔다 —
        어긋나면 뜬 다리 판정이 조용히 넘어간다.
        """
        out = []
        for led in self.leds:
            out.append((f"LED {led['tag']} 애노드", led['anode']))
            out.append((f"LED {led['tag']} 캐소드", led['cathode']))
        for i, r in enumerate(self.resistors, 1):
            out.append((f"저항{i}({r['label']}) 윗다리", r['top']))
            out.append((f"저항{i}({r['label']}) 아랫다리", r['bottom']))
        for d in self.displays:
            out += [(f"{d['label']} pin {p}", sym) for p, sym in d['pins'].items()
                    if p not in d.get('open', ())]  # 일부러 비운 핀(FND 507 DP)은 뜬 다리가 아니다
        for i, pot in enumerate(getattr(self, 'pots', ()), 1):
            out.append((f"가변저항{i}({pot['label']}) 끝 다리 1", pot['ends'][0]))
            out.append((f"가변저항{i}({pot['label']}) 끝 다리 2", pot['ends'][1]))
            if not pot.get('wiper_open'):
                out.append((f"가변저항{i}({pot['label']}) 와이퍼", pot['wiper']))
        return out

    def nets(self, substitute_inputs=True):
        """그린 것을 **전기적 넷**으로 묶어 낸다.

        -> `[{'labels': {'74HC32#10 pin 1', '입력 A', ...}, 'rails': {'vcc'}}, ...]`

        구조(`chips`·`leds`·`resistors`·`_segments`·`inputs`)만 읽고 `desc` 는 안 읽는다.
        `substitute_inputs=False` 면 입력 점퍼의 레일 끝을 치환하지 않는다 — 그림 그대로의 단락
        (R5ⓑ)은 그 넷에서만 보인다. 라벨·뜬 핀 판정은 치환한 넷을 쓴다.
        """
        uf = {}

        def find(k):
            uf.setdefault(k, k)
            while uf[k] != k:
                uf[k] = uf[uf[k]]
                k = uf[k]
            return k

        def union(a, b):
            ra, rb = find(a), find(b)
            if ra != rb:
                uf[rb] = ra

        members = {}

        def put(strip, label):
            if strip is not None:
                members.setdefault(strip, set()).add(label)
                find(strip)

        for ch in self.chips:
            for p, sym in ch['pins'].items():
                put(self._strip(sym), self._pin_label(ch, p))
        for label, sym in self._lead_labels():
            put(self._strip(sym), label)
        for x, name in self._addr_map.items():
            if x in self._rail_xs():
                put(('rail', x), name)

        # 입력 점퍼는 레일 쪽 끝을 가상 노드로 바꾼다 (`input_node()` 참조).
        # 끄면 그린 그대로 — 레일 끝이 레일로 남는다
        sub = {}
        if substitute_inputs:
            for inp in self.inputs:
                sub[inp['seg']] = ('input', inp['name'])
                put(('input', inp['name']), f"입력 {inp['name']}")

        for i, (kind, pts, desc) in enumerate(self._segments):
            ends = []
            for p in (pts[0], pts[-1]):
                color = self._jack_at(*p)
                if color is not None:
                    ends.append(('jack', color))
                    put(('jack', color), f'{JACK_KR[color]} 잭')
                else:
                    ends.append(self._strip(self.sym(p[0], self._row_of(p[1]))))
            if i in sub:
                ends = [sub[i] if e is not None and e[0] == 'rail' else e for e in ends]
            if ends[0] is None or ends[1] is None:
                continue   # 홀이 아닌 끝점은 R1 이 따로 잡는다
            union(ends[0], ends[1])

        groups = {}
        for strip in list(uf):
            groups.setdefault(find(strip), []).append(strip)
        out = []
        for strips in groups.values():
            labels = set()
            rails = set()
            for st in strips:
                labels |= members.get(st, set())
                if st[0] == 'rail':
                    rails.add(self._rail_kind.get(st[1]))
            out.append({'labels': labels, 'rails': rails - {None}})
        return out

    def verify(self):
        """그림대로 꽂을 수 있는지 검사한다 — 내보내기 직전에 돈다. 규칙 표는 SKILL.md §5, 회귀 사례는 연혁.md 가 정본.

        R1  끝점은 실제 홀(잭만 예외)       R2  한 홀에 리드 하나
        R3  끝점·다리 위를 다른 배선이 안 지남  R4  배선이 같은 축에 포개지지 않음(`overlap_policy`)
        R5  넷이 말이 됨 — 같은 스트립 점퍼·단락·뜬 핀/다리 없음
        R6  자기 스트립 안을 달리는 구간 없음
        R7  칩 한쪽 리드 ≤ SIDE_LEAD_MAX     R8  같은 블록 두 칩 사이 쪽 안 바꿈 (둘 다 `density_policy`)
        R9  칩은 `spec.chip_blocks` 에만     R10 LED 전용 블록으로는 칩 핀 → LED 사슬만, 순서대로
        R11~R17 읽기 규칙 — 번호 원·홀 위 신호선·몸통 건너기·칩 이름·표시기·입력 점퍼 엇갈림·배지(`spec.readability`)
        그리고 레일 연결성(브리지).
        """
        bad = [f'홀이 아니다: {s}' for s in self._not_holes]
        bad += [f'한 홀에 리드 둘: {s}' for s in self._double]
        bad += [f'끝점이 다른 배선 아래 깔린다: {s}' for s in self._endpoints_under_wires()]

        # R4. 포개진 배선은 한 선으로 보인다. overlap_warnings 는 이번 verify() 의 결과다.
        # 경고 모드는 R4 문구만 낮춘다 — 같은 포개짐은 R3 에도 걸려 그래도 던진다
        overlaps = self._overlaps()
        self.overlap_warnings = overlaps
        if overlaps:
            msg = '배선이 포개졌다:\n  ' + '\n  '.join(overlaps)
            if self.overlap_policy == 'strict':
                bad.append(msg)
            else:
                print(f'[WARN] {msg}', file=sys.stderr)

        # R7. 칩 한쪽 밀집
        if self.density_policy not in ('strict', 'legacy'):
            raise ValueError(f"density_policy 는 'strict' 또는 'legacy' 다: {self.density_policy!r}")
        if self.density_policy == 'strict':
            for s in self.side_leads():
                if s['count'] > self.side_lead_max:
                    blk = '좌' if s['block'] == 'left' else '우'
                    side_kr = '왼쪽' if s['side'] == 'a' else '오른쪽'
                    bad.append(f"R7 칩 한쪽 밀집: {s['chip']}({blk} {s['pin1_row']}행) {side_kr} "
                               f"{s['count']}리드 > {self.side_lead_max}: {', '.join(s['addrs'])}")

        # R8. 같은 블록 두 칩 사이 엇갈림
        if self.density_policy == 'strict':
            for w in self.cross_side_wires():
                bad.append(f"R8 칩 사이 엇갈림: {w['frm']} → {w['to']} · {w['desc']} — "
                           f"{w['from_side']['chip']} {w['from_side']['side']}쪽 → "
                           f"{w['to_side']['chip']} {w['to_side']['side']}쪽")
        # R9·R10. 블록 역할 — 판형이 정한다(`spec.chip_blocks`·`led_only_blocks`)
        allowed = '·'.join('좌' if b == 'left' else '우' for b in self.spec.chip_blocks)
        for ch in self.chips:
            if ch['block'] not in self.spec.chip_blocks:
                blk = '좌' if ch['block'] == 'left' else '우'
                bad.append(f"R9 칩 블록 위반: {ch['label']}({blk} {ch['pin1_row']}행) — "
                           f"{self.board} 판형은 칩을 {allowed} 블록에만 둔다")
        bad += self._block_role_violations()
        if bad:
            raise AssertionError('그림대로 꽂을 수 없다:\n  ' + '\n  '.join(bad))

        # R5. 넷 검사 — 꽂을 수는 있지만 회로가 아닌 그림
        r5 = []
        input_segs = {inp['seg'] for inp in self.inputs}
        for i, (kind, pts, desc) in enumerate(self._segments):
            if i in input_segs:
                continue   # 입력 점퍼의 레일 끝은 가상 노드다 (`input_node()`)
            a = self._strip(self.sym(pts[0][0], self._row_of(pts[0][1])))
            b = self._strip(self.sym(pts[-1][0], self._row_of(pts[-1][1])))
            if a is not None and a == b:
                r5.append(f'같은 스트립 안에서 끝나는 점퍼(전기적으로 무의미): {desc}')

        # R6. 꺾임점 둘이 같은 스트립인 구간 — R5ⓐ 는 양 끝점만 봐서 놓친다(2026-09-10)
        for kind, pts, desc in self._segments:
            for (ax, ay), (bx, by) in zip(pts, pts[1:]):
                if self.hole_at(ax, ay) is None or self.hole_at(bx, by) is None:
                    continue   # 잭(보드 밖)이나 여백을 지나는 구간은 볼 것이 없다
                sa = self._strip(self.sym(ax, self._row_of(ay)))
                sb = self._strip(self.sym(bx, self._row_of(by)))
                if sa is not None and sa == sb:
                    r5.append(f'자기 스트립 안을 달리는 구간(없어도 되는 우회): '
                              f'{self.addr(ax, ay)} -> {self.addr(bx, by)} · {desc}')

        nets = self.nets()
        # 단락만은 치환하지 않은 넷에서 본다 — 입력 점퍼의 레일 끝은 실재 배선이다
        for net in self.nets(substitute_inputs=False):
            if {'vcc', 'gnd'} == net['rails'] or {'vcc', 'gnd'} < net['rails']:
                r5.append('+5V 와 GND 가 한 넷이다 — 단락: '
                          + ', '.join(sorted(net['labels'])))
            elif len(net['rails']) > 1:
                names = ' 와 '.join(KIND_KR[k] for k in sorted(net['rails']))
                r5.append(f'{names} 가 한 넷이다 — 단락: ' + ', '.join(sorted(net['labels'])))
        # 둘째 전원(+15V) — 그 레일 넷에는 `DIP_SUPPLY` 가 허락한 칩 핀만 닿고, 그 핀은 그 레일에 닿는다
        # (실험10: +15V 가 로직 칩에 닿으면 칩이 망가진다 — 74HC05 절대 최대 7V)
        extra = {k for k in self._touched if k not in ('vcc', 'gnd')}
        if extra:
            for ch in self.chips:
                allowed = DIP_SUPPLY.get(ch['label'], {})
                for p in ch['pins']:
                    lab = self._pin_label(ch, p)
                    net = next((n for n in nets if lab in n['labels']), None)
                    rails = net['rails'] if net else set()
                    for k in extra & rails:
                        if allowed.get(p) != k:
                            r5.append(f'{lab} 가 {KIND_KR[k]} 레일 넷에 닿는다 — 이 핀은 {KIND_KR[k]} 를 받지 않는다')
                    want = allowed.get(p)
                    if want and want not in rails and not self.partial:
                        r5.append(f'{lab} 는 {KIND_KR[want]} 레일에 닿아야 한다 — 지금 넷의 레일: '
                                  + ('·'.join(KIND_KR[k] for k in sorted(rails)) or '없음'))

        # 아무 데도 안 물린 것 — 넷에 자기 라벨 하나뿐. 개방 미사용 핀·계측 자리(실험02)·덜 그린
        # 그림(`partial`)은 뺀다
        probe_strips = {self._strip(p['sym']) for p in self.probes if p.get('sym')}
        # 면제 키에 칩 라벨을 넣지 않는다 — `build_e2_tpd` 는 칩 라벨과 `mark_unused_outputs(chip=)` 가
        # 달라 오탐이 난다. (블록, pin1_row) 가 칩 하나로 정해지는 것은 R2 가 강제한다
        open_pins = {(u['block'], u['pin1_row'], u['pin']) for u in self.unused_outputs}
        # 개방으로 등록한 미사용 입력(rail None)도 뜬 핀이 아니다
        open_pins |= {(u['block'], u['pin1_row'], u['pin'])
                      for u in self.unused_inputs if u.get('rail') is None}
        # (라벨, 스트립, 조사, 무엇이라 부를지) — 칩 핀과 부품 다리. 뜬 저항은 실험실에서 이상 없어 보인다
        checked = []
        if not self.partial:
            for ch in self.chips:
                for p, sym in ch['pins'].items():
                    if (ch['block'], ch['pin1_row'], p) in open_pins:
                        continue
                    checked.append((self._pin_label(ch, p), self._strip(sym), '이', '뜬 핀'))
            for label, sym in self._lead_labels():
                checked.append((label, self._strip(sym), '가', '뜬 다리'))
        for lab, strip, josa, what in checked:
            if strip in probe_strips:
                continue
            for net in nets:
                if lab in net['labels']:
                    if len(net['labels']) == 1:
                        r5.append(f'{lab} {josa} 아무 데도 안 물렸다 — {what}')
                    break

        if r5:
            raise AssertionError('넷이 틀렸다:\n  ' + '\n  '.join(r5))

        # 레일 연결성 — 같은 전원 레일들이 브리지로 이어져 있지 않으면 전원이 안 간다
        for kind in self._touched:
            rails = self._touched[kind]
            if len(rails) <= 1:
                continue
            groups = {}
            for x in rails:
                groups.setdefault(self._uf_find(x), []).append(x)
            if len(groups) > 1:
                desc = ' / '.join(
                    '+'.join(sorted(self._addr_map.get(x, str(x)) for x in g))
                    for g in groups.values())
                raise AssertionError(
                    f'{KIND_KR[kind]} 레일이 끊겨 있다 — 브리지가 없다: {desc}\n'
                    '  레일쌍 넷은 별개 스트립이다. bridge_rails() 로 이어라.')

        # R11~R17. 읽기 규칙 — 기하·넷·레일이 맞은 뒤에 본다. v2(`spec.readability`)만
        if self.spec.readability:
            rd = [f'R11 번호 원 가림: {p}' for p in self.marker_problems()]
            rd += [f'R12 신호선이 홀 위를 지난다: {p}' for p in self.wires_over_holes()]
            rd += [f'R13 칩 몸통을 쓸데없이 건넌다: {p}' for p in self.needless_body_crossings()]
            rd += [f'R14 배선이 칩 이름을 가린다: {p}' for p in self.wires_over_chip_labels()]
            rd += [f'R15 배선이 표시기·풀업 저항을 가린다: {p}' for p in self.wires_over_display()]
            rd += [f'R16 입력 점퍼끼리 엇갈린다: {p}' for p in self.input_crossings()]
            rd += [f'R17 신호 이름 배지가 가린다: {p}' for p in self.badge_problems()]
            rd += self.bridge_clearance_problems()
            if rd:
                raise AssertionError('따라 그릴 수 없다:\n  ' + '\n  '.join(rd))
