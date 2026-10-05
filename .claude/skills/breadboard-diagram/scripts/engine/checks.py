# 결선도 엔진 조각 — 검사(R5~R14·넷 모형·verify).
# 단독으로 import 하지 않는다. `../render_breadboard.py` 가 조각들을 `_PARTS` 순서대로 자기
# 이름공간에서 실행한다 — 앞 조각의 이름(import·상수·함수)을 import 없이 그대로 쓴다.

class _RuleChecks:
    """`BreadboardRenderer` 의 검사 쪽 — R5~R14 와 넷 모형. `export()` 직전에 `verify()` 가 돈다.
    그리기 상태(`_leads`·`_segments`·`chips` …)는 `BreadboardRenderer.__init__` 이 만든다."""

    def side_leads(self):
        """칩마다 양쪽(a~d / g~j) 핀 행 7개에 꽂힌 리드 수 — R7 의 지표.

        점유표(`_leads`)만 읽는다. 칩 핀(e·f 열)은 그 칩 자신이라 빼고, 지나가는
        선(`_passed`)은 꽂는 것이 아니라 뺀다. `wiring()` 에 넣지 않는다 — `content()`
        가 `wiring()` 을 통째로 해시하므로 필드 하나만 더해도 지난 주차 도장이 전부
        깨진다.
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
        """`_endpoint()` 결과가 어느 칩의 어느 쪽 핀 스트립인가.

        칩 행 범위(pin1_row ~ pin1_row+행수−1) 안의 a~d 열이면 그 칩의 'a' 쪽, g~j 열이면 'f' 쪽 — 같은 행
        a~e / f~j 는 한 스트립이라 그 홀에 꽂은 것은 그 핀에 꽂은 것이다. e·f(칩 다리)·칩 행
        밖·레일·잭은 None. 같은 이름의 칩이 두 자리에 앉을 수 있어(실험02 t_pd) `pin1_row` 로
        구분한다.
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
        """R8 의 지표 — 같은 블록의 **서로 다른 두 칩** 핀 스트립을 잇는 배선 중 양 끝 쪽이 다른 것.

        2026-09-20 격리 시험판(게이트를 무조건 1·4 로 나눈 판)에서 `좌 a9 → 좌 h19`(A⊕B → NOT2),
        `우 g13 → 우 b21`(AND2 → OR) 같은 X자가 생겼다 — 승인본 실험01~03 완성본 7장은 0건,
        시험 전용 `build_e2_tpd` 한 가닥만 예외(`tests/test_breadboard_physical.py`
        `KNOWN_CROSS_SIDE`). 같은 칩 안의 사슬(XOR1→XOR2)은 나누기의 대가라 보지 않고, 다른
        블록 사이는 차선으로 건너므로 보지 않는다. 가닥 단위로 본다 — 중계 스트립을 거친 두
        가닥은 못 본다. 넷 단위 검사는 별건. `wiring()` 에 넣지 않는다 — 도장.
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
    #
    # 2026-10-03 실험04 v2 시험판(`docs/plans/2026-10-03-실험04-v2-시험판-결과.md`)은 R1~R10 을
    # 다 통과했는데 **따라 그릴 수 없었다**(사용자). 번호 원이 끝점 홀을 덮었고 — 기본 자리가
    # 첫 구간 가운데인데 첫 구간이 반 행(9.5px) 토막이었다 — 검정 선이 검정 홀 열 위를 지나가
    # 꽂힌 것인지 지나가는 것인지 안 보였다. 칩 넷이 한 블록에 몰리는 v2 에서 처음 드러났다.
    # v1 승인본(실험01~04)은 소급하지 않는다.

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
        """R12 — 신호선(`sig`·`mid`)이 끝점 말고 지나가는 홀. 검정 선이 검정 홀 위를 지나가면 거기
        꽂힌 것인지 지나가는 것인지 안 보인다. 전원·GND·레일 브리지·잭 선과 입력 점퍼(레일에서
        같은 행으로 곧게 들어온다)는 안 본다."""
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
        """R13 — 양 끝이 칩 기둥의 같은 쪽인데 그 칩 몸통을 가로지르는 신호선. 칩 이름·핀 번호를
        덮고 쓸데없이 돌아간다. 양 끝이 다른 쪽(칩 안 a↔f 이어 가기, a쪽 출력 → LED)이면 한 번은
        건너야 하므로 안 본다. 가로로 건너는 것만이 아니라 몸통 상자에 **들어가기만** 해도 본다 —
        e·f 사이 골을 세로로 타는 선은 홀이 없어 R12 가 못 보고 칩 이름·핀 번호를 길게 덮는다
        (2026-10-04 검토)."""
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

    def wires_over_chip_labels(self):
        """R14 — 칩 이름 글자 위를 지나는 배선. R13 이 허용한 칩 안 a↔f 이어 가기도 이름
        한복판을 건너면 '7⁴HC20' 처럼 읽혀 어느 칩인지 안 보인다(2026-10-04 실험04 v2 시험판
        검토). 이름은 몸통 가운데(pin 4 행 둘레)에 세로로 적히므로 이어 가기는 그 위아래 반 행
        — pin 1~3 이나 pin 5~7 사이 — 으로 건넌다. 전원선도 본다 — 가리는 것은 색과 무관하다."""
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
        """R10 의 지표 — 양 끝이 서로 다른 블록인 배선. 레일↔레일 전원 브리지는 안 든다(설계 §5)
        — 가운데 레일은 어느 블록도 아니고, 좌 바깥 ↔ 우 바깥 브리지는 양 끝이 레일이라 뺀다.
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
        선끼리 위아래 순서가 LED 순서와 같다(설계 §5).

        핀 방향표가 없어 '출력' 인지는 보지 않는다(2026-10-03 결정) — LED 에 무엇이 물렸는지는
        R5 와 netlist 대조가 본다. `spec.led_only_blocks` 가 비면(v1) 아무것도 안 낸다.
        """
        led_blocks = self.spec.led_only_blocks
        if not led_blocks:
            return []
        chip_strips = {self._strip(sym) for ch in self.chips
                       if ch['block'] in self.spec.chip_blocks for sym in ch['pins'].values()}
        led_strips = {self._strip(ch['signal']) for ch in self.led_chains
                      if ch['signal'] is not None and ch['signal'][0] in led_blocks}
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
        ok.sort(key=lambda t: t[0])
        for (_l1, c1, w1), (_l2, c2, w2) in zip(ok, ok[1:]):
            if c1 > c2:
                bad.append(f"R10 건너는 선 엇갈림: {w1['frm']} → {w1['to']} / "
                           f"{w2['frm']} → {w2['to']} — 칩 쪽 행 순서를 LED 순서와 맞춘다")
        return bad

    def wiring(self):
        """이 그림이 무엇을 어디에 꽂았는지 **기호 좌표**로 낸다.

        손그림 검토(`review-hand-diagram`)가 정답으로 쓴다. 픽셀이 아니라
        (블록, 열, 행) 으로 내는 이유는 손그림 전사가 '좌 b10' 같은 주소로
        적히기 때문이다 — 양쪽을 같은 말로 맞춰야 비교가 된다.

        `overlaps` 는 `verify()` 가 채운다. `export()` 를 거친 렌더러면 차 있고,
        아니면 비어 있다. 참조 그림에서 **잘 안 보이는 선**을 판정문에 주석으로
        달기 위한 것이다 — 복합회로의 A 갈래가 초록 Z 선 아래 깔려 있어서
        따라 그린 사람이 통째로 빠뜨렸다.
        """
        wires = [{'kind': kind, 'desc': desc,
                  'frm': self._endpoint(pts[0]), 'to': self._endpoint(pts[-1])}
                 for kind, pts, desc in self._segments]
        return {
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

    def input_node(self, name, x, row):
        """**방금 그린 배선**을 입력 점퍼로 적어 둔다 (`_input_jumper` 가 부른다).

        입력 점퍼는 지금 GND 레일에 꽂혀 있다 — 0 을 준 자리를 그린 것이고,
        1 을 줄 때는 레일 쪽 끝만 VCC 레일로 옮긴다. 넷 검사가 이걸 레일
        연결로 세면 입력 A·B·C 가 GND 와 한 넷이 되어 "pin 1 이 입력 A 에
        물렸는가" 를 물을 수 없다. 그래서 그 끝을 가상 입력 노드로 바꿔 센다.

        넷을 정하는 것은 `seg` 하나다. `x`·`row` 는 좌표를 뜻하는 인자가 아니라
        **직전 세그먼트가 정말 그 홀에서 끝났는지 확인하는 단언**이다 — "이
        함수는 `step_wire()` 바로 뒤에 온다" 는 관례를 여기서 강제한다. 관례로
        두면 사이에 배선 한 줄이 끼는 순간 엉뚱한 세그먼트의 끝이 가상 노드로
        바뀌고, 그림은 멀쩡하게 나온다.
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
        """기호 좌표 -> 스트립 키. **홀이 아니라 스트립이 넷의 단위다.**

        단자대는 한 행의 a~e 가 한 스트립, f~j 가 또 한 스트립이다 (가운데
        골이 갈라 놓는다). 전원 레일은 열 하나가 통째로 한 스트립이라 행이
        없다 — 레일쌍 넷이 서로 별개 스트립인 것은 x 가 다르기 때문이다.
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
        """부품 다리의 (넷 라벨, 기호 좌표) 목록. LED 두 다리, 저항 두 다리.

        `nets()` 와 R5ⓒ 가 **같은 말**을 써야 해서 한 자리에 둔다 — 한쪽만
        고치면 "뜬 다리" 판정이 자기 라벨을 넷에서 못 찾고 조용히 넘어간다.
        """
        out = []
        for led in self.leds:
            out.append((f"LED {led['tag']} 애노드", led['anode']))
            out.append((f"LED {led['tag']} 캐소드", led['cathode']))
        for i, r in enumerate(self.resistors, 1):
            out.append((f"저항{i}({r['label']}) 윗다리", r['top']))
            out.append((f"저항{i}({r['label']}) 아랫다리", r['bottom']))
        return out

    def nets(self, substitute_inputs=True):
        """그린 것을 **전기적 넷**으로 묶어 낸다.

        -> `[{'labels': {'74HC32#10 pin 1', '입력 A', ...}, 'rails': {'vcc'}}, ...]`

        `_leads` 는 홀 단위라 이 층위를 못 본다 — 같은 스트립의 다른 홀에 꽂은
        두 점퍼는 홀이 다르지만 **전기적으로 한 점**이다. 2026-09-09 의 결함
        둘이 정확히 그 틈으로 지나갔다.

        `desc` 문자열은 읽지 않는다. `chips`·`leds`·`resistors`·`_segments`·
        `inputs` 라는 **구조**만 읽는다 — 말이 바뀔 때 조용히 깨지지 않도록.

        `substitute_inputs=False` 면 입력 점퍼의 레일 끝을 **치환하지 않는다.**
        치환된 넷은 "무엇이 무엇에 물렸는가" 를 묻기 위한 것이라 그 배선이 실재로
        잇고 있는 레일을 지운다 — 그림 그대로 꽂았을 때의 단락(R5ⓑ)은 지우지
        않은 넷에서만 보인다. 라벨·뜬 핀 판정은 치환한 넷을 쓴다.
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
        """그림대로 꽂을 수 있는지 검사한다. 내보내기 직전에 돈다.

        좌표표가 어긋나도, 선이 허공에서 출발해도 그림은 그럴듯하게 나온다 —
        눈으로는 안 잡힌다. 2026-09-07 까지는 주소 문자열에 '레일' 이 든 끝점의
        빈 행만 봤고, 허공(x=95)에서 온 입력선은 '보드밖(입력)' 이라는 이름을
        달고 그 틈으로 지나갔다. 지금은 점유표(`_leads`)를 본다.

        R1  모든 끝점은 실제 홀이다 (전원잭만 예외).
        R2  한 홀에는 리드 하나만 들어간다 — 점퍼·부품 다리·칩 핀 전부.
        R3  배선 끝점·부품 다리 위를 다른 배선이 지나가지 않는다 — 넷 무관.
        R4  서로 다른 배선이 같은 축 위에 포개지지 않는다 (`overlap_policy`).
        R5  넷이 말이 된다 — 같은 스트립 안에서 끝나는 점퍼가 없고, +5V 와
            GND 가 한 넷이 아니며(치환하지 않은 넷에서 본다), 아무 데도 안 물린
            칩 핀도 부품 다리도 없다.
        R6  배선이 자기 스트립 안을 달리는 구간이 없다 — 뒤쪽 홀에서 출발하면
            되는 우회다. R5ⓐ 가 양 끝점만 보는 틈으로 지나간 부류다.
        R7  칩 한쪽(핀 행 7 × 자유 열 4)에 꽂힌 리드가 SIDE_LEAD_MAX 를 넘지 않는다
            (`density_policy`). 실험01~03 승인본만 'legacy' 로 끈다.
        R8  같은 블록의 두 칩을 잇는 배선은 쪽(a~d / g~j)을 바꾸지 않는다 — 게이트는 신호가
            오는 쪽으로 배정한다(SKILL §4a). `density_policy` 가 함께 끈다.
        R9  칩은 판형이 허용한 블록에만 둔다(`spec.chip_blocks`) — v2 는 좌 블록만.
        R10 LED 전용 블록(`spec.led_only_blocks`, v2 는 우)으로 건너는 선은 칩 핀 스트립 →
            LED 사슬 신호 스트립뿐이고, 건너는 선끼리 위아래 순서가 LED 순서와 같다. 핀
            방향표가 없어 '출력' 인지는 안 본다. v1 은 R9 가 두 블록을 다 허용하고 R10 이
            비어 있어 실험01~04 가 그대로다.
        R11 번호 원이 꽂힌 홀·다른 번호 원·칩 몸통·남의 배선을 가리지 않는다.
        R12 신호선은 끝점 말고 홀 위를 지나지 않는다 — 닿은 홀은 전부 꽂는 홀이다.
        R13 양 끝이 칩의 같은 쪽인 신호선은 그 칩 몸통을 건너지 않는다.
        R14 어떤 배선도 칩 이름 글자 위를 지나지 않는다 — 칩 안 이어 가기도 이름 위아래로 건넌다.
            R11~R14 는 `spec.readability`(v2)만 돈다 — 2026-10-03 실험04 v2 시험판.
        그리고 레일 연결성 — 같은 전원을 나르는 레일이 브리지로 이어져 있는가.

        R1~R4 는 전부 **기하**다. 2026-09-09 까지 "이 배선이 무엇을 잇는가" 는
        아무도 안 봤고, 그 틈으로 결함 둘이 지나갔다 — 복합 회로의 `우 a10 →
        우 b10` 은 같은 스트립 안이라 아무 일도 안 하면서 74HC32 pin 1 을 뜬
        채로 뒀고, 실험02 Rn 은 1kΩ 아랫다리가 pin 5 행에 앉아 +5V 를 GND 로
        직결시켰다. 더 나쁜 것은 R3 를 통과시키려는 재배치가 첫 결함을 만들었고
        검사는 오히려 통과로 바뀌었다는 점이다. 그래서 R5 를 넣었다.
        """
        bad = [f'홀이 아니다: {s}' for s in self._not_holes]
        bad += [f'한 홀에 리드 둘: {s}' for s in self._double]
        bad += [f'끝점이 다른 배선 아래 깔린다: {s}' for s in self._endpoints_under_wires()]

        # R4. 다른 배선끼리 같은 축 위에 포개지면 그림에서 한 선으로 보인다.
        # overlap_warnings 는 **이번 verify() 의 결과**다 — 포개짐이 없으면 비운다.
        # 축 위 포개짐은 한쪽 끝점이 상대 구간 안에 있다는 뜻이라 R3 에도 걸린다 —
        # R4 는 "두 넷이 한 선으로 보인다" 는 진단을 덧붙이는 역할이고, 경고 모드는
        # R4 문구만 낮춘다 (R3 는 그래도 던진다)
        overlaps = self._overlaps()
        self.overlap_warnings = overlaps
        if overlaps:
            msg = '배선이 포개졌다:\n  ' + '\n  '.join(overlaps)
            if self.overlap_policy == 'strict':
                bad.append(msg)
            else:
                print(f'[WARN] {msg}', file=sys.stderr)

        # R7. 칩 한쪽에 리드가 몰리지 않는다 — 2026-09-18 실험03 에서 네 칩이 게이트 1·2 만
        # 써서 74HC86 왼쪽에 11리드가 몰렸다. 게이트를 좌·우로 나눠 배정하면 풀린다(SKILL §4a).
        if self.density_policy not in ('strict', 'legacy'):
            raise ValueError(f"density_policy 는 'strict' 또는 'legacy' 다: {self.density_policy!r}")
        if self.density_policy == 'strict':
            for s in self.side_leads():
                if s['count'] > SIDE_LEAD_MAX:
                    blk = '좌' if s['block'] == 'left' else '우'
                    side_kr = '왼쪽' if s['side'] == 'a' else '오른쪽'
                    bad.append(f"R7 칩 한쪽 밀집: {s['chip']}({blk} {s['pin1_row']}행) {side_kr} "
                               f"{s['count']}리드 > {SIDE_LEAD_MAX}: {', '.join(s['addrs'])}")

        # R8. 같은 블록 두 칩 사이 배선이 반대쪽으로 건너지 않는다 — 2026-09-20 격리 시험판의
        # X자. 게이트를 신호가 오는 쪽으로 배정하면 생기지 않는다(SKILL §4a).
        if self.density_policy == 'strict':
            for w in self.cross_side_wires():
                bad.append(f"R8 칩 사이 엇갈림: {w['frm']} → {w['to']} · {w['desc']} — "
                           f"{w['from_side']['chip']} {w['from_side']['side']}쪽 → "
                           f"{w['to_side']['chip']} {w['to_side']['side']}쪽")
        # R9·R10. 블록 역할 — 판형이 정한다(`spec.chip_blocks`·`led_only_blocks`). v2 는 칩을
        # 좌 블록에만 두고 우 블록에는 LED 사슬만 둔다(설계 §5)
        allowed = '·'.join('좌' if b == 'left' else '우' for b in self.spec.chip_blocks)
        for ch in self.chips:
            if ch['block'] not in self.spec.chip_blocks:
                blk = '좌' if ch['block'] == 'left' else '우'
                bad.append(f"R9 칩 블록 위반: {ch['label']}({blk} {ch['pin1_row']}행) — "
                           f"{self.board} 판형은 칩을 {allowed} 블록에만 둔다")
        bad += self._block_role_violations()
        if bad:
            raise AssertionError('그림대로 꽂을 수 없다:\n  ' + '\n  '.join(bad))

        # R5. 넷 검사. 여기까지는 전부 기하였다 — 그림대로 꽂을 수는 있지만
        # 꽂아 봐야 회로가 아닌 그림을 여기서 잡는다
        r5 = []
        input_segs = {inp['seg'] for inp in self.inputs}
        for i, (kind, pts, desc) in enumerate(self._segments):
            if i in input_segs:
                continue   # 입력 점퍼의 레일 끝은 가상 노드다 (`input_node()`)
            a = self._strip(self.sym(pts[0][0], self._row_of(pts[0][1])))
            b = self._strip(self.sym(pts[-1][0], self._row_of(pts[-1][1])))
            if a is not None and a == b:
                r5.append(f'같은 스트립 안에서 끝나는 점퍼(전기적으로 무의미): {desc}')

        # R6. 자기 스트립 안을 달리는 구간. 꺾임점 둘이 같은 스트립이면 그
        # 구간은 전기적으로 없는 것과 같다 — 뒤쪽 홀에서 출발하면 그만이다.
        # R5ⓐ 는 배선의 **양 끝점**만 봐서, 자기 스트립 안을 지나다 밖으로
        # 나가는 배선은 끝점이 서로 달라 통과했다. 2026-09-10 OR 의 ⑪ 갈래
        # (`좌 c12 → 좌 a12 → 좌 a24`)가 그 틈으로 이틀을 살아남았다.
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
        # 단락만은 **치환하지 않은 넷**에서 본다. 입력 점퍼가 지금 꽂혀 있는
        # 레일은 가상 노드가 아니라 실재 배선이다 — 그 점퍼가 꽂힌 스트립이
        # 이미 VCC 에 물려 있으면 그림 그대로가 GND↔VCC 직결인데, 치환한 넷에서는
        # 그 레일이 지워져 아무 일도 없어 보인다
        for net in self.nets(substitute_inputs=False):
            if {'vcc', 'gnd'} <= net['rails']:
                r5.append('+5V 와 GND 가 한 넷이다 — 단락: '
                          + ', '.join(sorted(net['labels'])))

        # 아무 데도 안 물린 것. 넷에 자기 라벨 하나뿐이면 그림에는 있으되
        # 회로에는 없다. 미사용 출력(개방 NC)과 계측기가 무는 자리는 뺀다 —
        # 실험02 는 점퍼가 아니라 프로브로 신호를 넣고 뺀다. 덜 그린
        # 그림(`partial`)도 통째로 뺀다: 칩 핀도 부품 다리도 아직 안 붙었을 수 있다
        probe_strips = {self._strip(p['sym']) for p in self.probes if p.get('sym')}
        # 면제 키에 **칩 라벨이 없다.** 넣으면 `build_e2_tpd` 가 깨진다 — 거기서
        # `draw_chip` 라벨은 '74HC04' 인데 `mark_unused_outputs(chip='U2')` 라
        # 키가 어긋나고, U2 의 미사용 출력 6개가 전부 뜬 핀 오탐이 된다.
        # 그리고 "같은 블록·같은 pin1_row 에 칩 둘은 없다" 는 것은 관례가 아니라
        # **R2 가 강제한다** — 그렇게 두면 `draw_chip` 이 e·f 열 홀에 리드를 둘씩
        # 꽂아 `_double` 에 걸리고, 그건 R5 보다 먼저 던진다
        open_pins = {(u['block'], u['pin1_row'], u['pin']) for u in self.unused_outputs}
        # 개방으로 등록한 미사용 입력(`mark_unused_inputs`, rail None)도 뜬 핀이
        # 아니다. 접지한 것(rail 'gnd'/'vcc')은 배선이 있으므로 여기 올 일이 없다
        open_pins |= {(u['block'], u['pin1_row'], u['pin'])
                      for u in self.unused_inputs if u.get('rail') is None}
        # (라벨, 스트립, 조사, 무엇이라 부를지). 칩 핀만 보던 것을 부품 다리까지 넓혔다 —
        # 양끝이 다 빈 스트립에 걸친 저항은 아무 규칙도 안 보고 지나갔고, 그림대로
        # 꽂으면 무부하 V_OL 을 재게 되는데 **실험실에서는 아무 이상이 없어 보인다.**
        # 짝이 있는 다리는 넷에 라벨이 둘 이상이라(예: {저항1(1kΩ) 윗다리, 좌
        # VCC레일}) 오탐이 나지 않는다
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

        # 레일 연결성. 같은 전원을 나르는 레일들이 브리지로 이어져 있지
        # 않으면, 그림대로 꽂았을 때 전원이 안 간다. 눈으로는 절대 안 잡힌다 —
        # 레일마다 배선이 얌전히 꽂혀 있고 색도 맞기 때문이다
        for kind in ('vcc', 'gnd'):
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

        # R11~R14. 읽기 규칙 — 꽂을 수 있고 회로도 맞는데 **따라 그릴 수 없는** 그림
        # (2026-10-03 실험04 v2 시험판, 사용자). 기하·넷·레일보다 뒤에 본다 — 그것들이
        # 틀린 그림의 읽기는 따질 필요가 없다. v2(`spec.readability`)만
        if self.spec.readability:
            rd = [f'R11 번호 원 가림: {p}' for p in self.marker_problems()]
            rd += [f'R12 신호선이 홀 위를 지난다: {p}' for p in self.wires_over_holes()]
            rd += [f'R13 칩 몸통을 쓸데없이 건넌다: {p}' for p in self.needless_body_crossings()]
            rd += [f'R14 배선이 칩 이름을 가린다: {p}' for p in self.wires_over_chip_labels()]
            if rd:
                raise AssertionError('따라 그릴 수 없다:\n  ' + '\n  '.join(rd))
