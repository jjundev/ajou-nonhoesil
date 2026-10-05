# 결선도 엔진 조각 — BreadboardRenderer 그리기·번호 원·도장.
# 단독으로 import 하지 않는다. `../render_breadboard.py` 가 조각들을 `_PARTS` 순서대로 자기
# 이름공간에서 실행한다 — 앞 조각의 이름(import·상수·함수)을 import 없이 그대로 쓴다.

class BreadboardRenderer(_RuleChecks):
    def __init__(self, template_path=None, baseline=None, layer=None, board=DEFAULT_BOARD):
        # 판형 버전. 주차 `배치.py` 의 `BOARD` 를 빌더가 그대로 넘긴다 — `build_all` 이 대조한다
        self.board = board
        self.spec = board_spec(board)
        if template_path is None:
            template_path = _default_template(self.spec)
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"Breadboard template not found: {template_path}")

        self.base_im = Image.open(template_path).convert('RGBA')
        # 좌표표가 이 크기에 묶여 있다. 다른 판본이 들어오면 여기서 걸린다 —
        # 갈아끼운 그림은 결과가 그럴듯해서 눈으로는 안 잡히기 때문이다.
        w, h = self.spec.size
        if self.base_im.size != self.spec.size:
            raise ValueError(
                f'템플릿 크기가 {w}x{h} 가 아닙니다: '
                f'{self.base_im.size} ({template_path}).\n'
                'cols·r_y() 좌표는 정본 한 장에 맞춰져 있습니다. '
                '다른 판본을 쓰려면 좌표표를 다시 떠야 합니다.')
        if self.spec.sha256 is not None:
            with open(template_path, 'rb') as f:
                digest = hashlib.sha256(f.read()).hexdigest()
            if digest != self.spec.sha256:
                raise ValueError(
                    f'{self.board} 양식 PNG 의 해시가 geometry.json 의 png_sha256 과 다르다: '
                    f'{template_path}.\n판형을 다시 뽑았으면 1배(1200x1600)인지, '
                    'hand_grid.detect_grid 가 0px 로 맞는지 확인하고 png_sha256 을 같이 고친다')
        # 정본은 998px 한 장뿐이다 — 격자·로고는 확대해 깐다(`SCALE` 주석). NEAREST 는 픽셀을
        # 그대로 늘려 원본과 같은 모양이다. LANCZOS 는 JPEG 잡티까지 매끈하게 늘려 PNG 가
        # 장당 2.3MB 로 커졌다(NEAREST 는 1.1MB 안팎, 2026-09-28 실측)
        self.im = self.base_im.resize((w * SCALE, h * SCALE), Image.NEAREST)
        self.overlay = Image.new('RGBA', self.im.size, (0, 0, 0, 0))
        self.draw = _ScaledDraw(self.overlay)
        # 이미 그린 레일 브리지. 칩마다 connect_unused_inputs 를 부르면 같은
        # 레일쌍을 여러 번 잇게 되므로 한 번만 그린다
        self._bridged = set()
        # 실제로 꽂힌 브리지. `_bridged` 는 중복 방지 키(kind, x, x)라 **행이 없다**.
        # 행을 안 담으면 `wiring()` 이 1행을 주는데 1행은 레일 빈 행이라,
        # 손그림 검토가 참조 브리지마다 H1 치명을 헛낸다
        self.bridges = []
        # 어느 레일 스트립에 무엇이 닿았는지. 레일쌍 넷은 서로 **별개
        # 스트립**이라, +5V 를 한 레일에 넣고 칩 14번 핀을 다른 레일에 물리면
        # 그림은 멀쩡한데 전원이 안 간다. verify() 가 이걸로 잡는다
        self._touched = {'vcc': set(), 'gnd': set()}
        self._rail_uf = {}
        # 결선 순서표. 손으로 그리는 사람은 그림 전체를 한 번에 볼 필요 없이
        # 이 표를 위에서 아래로 지워가며 한 줄씩 그린다
        self.steps = []
        # 기준선 대비 **새로 꽂는 신호선**의 key. 예산(`STAGE_WIRE_BUDGET`)의 지표다.
        # `content()` 에는 넣지 않는다 — 넣으면 기존 PNG 스물두 장의 도장이 바뀐다.
        self.new_signal = []
        # R7·R8 정책. 'strict' 가 기본 — 칩 한쪽 리드가 SIDE_LEAD_MAX 를 넘거나(R7) 같은
        # 블록 두 칩 사이 배선이 쪽을 바꾸면(R8) verify() 가 막는다. 'legacy' 는 R7(2026-09-20)
        # 이전에 승인·제출된 실험01~03 빌더만 쓴다 — 승인본을 다시 그리지 않으려는
        # 것이지 면허가 아니다. tests/test_breadboard_physical.py 가 실험 4 이상은 전부
        # strict 인지 본다. content() 에 들지 않아 도장은 그대로다.
        self.density_policy = 'strict'
        # 홀 점유표. (열 x, 행) -> 무엇이 꽂혀 있는가. 배선 끝점·부품 다리·칩 핀이
        # 전부 여기 등록되고 verify() 가 본다 — 끝점은 홀이어야 하고(R1), 한 홀에는
        # 리드 하나만 들어간다(R2). 2026-09-07 까지 verify() 는 주소 문자열을 파싱해
        # 레일 끝점의 빈 행만 봤고, 허공(x=95)에서 출발한 입력선이 그 틈으로 지나갔다
        self._leads = {}
        # 배선이 **지나가는** 홀. 비어 있지만 여기에 끝점을 두면 점이 선 아래
        # 깔린다 — free_rail_row() 가 피하고 verify() R3 가 끝점과 대조한다
        self._passed = set()
        self._not_holes = []
        self._double = []
        # 배선 구간 목록. (색, 꼭짓점들, 뜻). 서로 다른 배선이 같은 축 위에
        # 포개지면 그림에서 한 선으로 보인다 — 2026-09-07 실험 1-1 에서 입력 C 가
        # 초록 중간단 선에 삼켜져 다른 회로로 읽혔다. 'strict' 면 verify() 가
        # 던지고, 'warn' 이면 stderr 에 적고 overlap_warnings 에 남긴다
        self._segments = []
        self.overlap_policy = 'strict'
        self.overlap_warnings = []
        # 결선 순서표와 번호 원을 켜는 스위치. **지금은 13장 빌더가 전부 켠다** —
        # e1 계열도 e2 계열도 `enable_steps()` + `step_wire()` 에 네 색 팔레트(`WIRE`)를
        # 쓴다. 옛 `draw_wire()` 를 쓰는 빌더는 하나도 없다 (2026-09-10 확인)
        self.numbered = False
        # 보드 밖으로 뺀 규칙 문구. 배선이 아니라 배선의 *이유* 라서 손으로
        # 옮겨 그릴 대상이 아니다 — 보드 위에 두면 그릴 홀만 가린다
        self.notes = []
        # 계측기·신호원 접점. 결선표와 섞지 않는다
        self.probes = []
        # 입력 점퍼가 꽂힌 자리. 넷 검사가 레일 쪽 끝을 **가상 입력 노드**로
        # 바꿔 세는 데 쓴다 — `input_node()` 주석 참조
        self.inputs = []
        # 보드 안에 찍은 신호 이름 배지. (이름, 상자 (x0, y0, x1, y1), 가리키는 배선 번호 | None).
        # 가독성 테스트가 번호 원·배선·꽂힌 홀을 가리는지 본다
        self.tag_boxes = []
        # 엔진 고정 부품(`marker_near`) 번호 원 — 비킨 자리를 적어 두고(`settled_markers`), 힌트가 있으면
        # 그 자리를 쓴다(`marker_hints`, 보통 `place_marker_hints` 가 superset 판에서 뽑은 것). 그림마다
        # 있는 부품이 달라도 같은 선의 원이 같은 자리다(2026-10-05 최종 검토)
        self.marker_hints = {}
        self.settled_markers = {}
        # 번호 원의 상자. 같은 검사가 쓴다
        self.marker_boxes = []
        # 번호 원의 **자리** — 그렸든 안 그렸든(층 그림의 흐린·숨긴 번호, 기준선 회색 선). v2 자동
        # 자리(`_auto_marker`)는 이것을 피한다. 그려진 원만 피하면 층 그림과 완성본의 자리가
        # 갈라져, 완성본은 통과하는데 층 그림이 R11 로 멈춘다(2026-10-04 검토). `readability` 만
        self._marker_slots = []
        # 보드 밖 입력 꼬리표(`_tag`) 상자 — (글, (x0, y0, x1, y1)). 같은 행 입력이 둘이면
        # 꼬리표가 포개진다(2026-09-28 실험04 C2 S1·D) — `_input_jumper` 가 이걸 보고 비킨다
        self.margin_tag_boxes = []
        # 일부러 덜 그린 그림인가 (복합 회로 누적 1·2단계). '아무 데도 안 물렸다'
        # 갈래만 건너뛴다 — 칩 핀도 부품 다리도 아직 안 붙었을 수 있다. 같은
        # 스트립 점퍼도 전원 단락도 덜 그렸다고 봐줄 것이 아니다.
        # 걷기 보드에서는 프로퍼티(`partial` setter)가 False 를 받아도 True 로 남긴다 —
        # 아래 `self.ghost` 를 먼저 정해 두어야 setter 가 그것을 볼 수 있다
        self._partial = False
        # 앞 보드의 `snapshot()`. 같은 홀 쌍의 배선·같은 홀의 LED 사슬은 회색으로
        # 그리고 번호를 주지 않는다 — 실험실에서는 그 선을 손대지 않는다.
        # 기준선에 있었는데 이번에 안 그린 것은 `removed()` 가 "걷는다" 로 낸다.
        # 실험01 실험실 기록(2026-09-11): 1-1→1-2 는 칩만 갈아끼우면 됐다
        self.baseline = baseline
        self.kept = []          # 그대로 두는 배선·부품의 desc
        self.swaps = []         # (앞 칩, 새 칩, block, pin1_row)
        self._keep_parts = False  # led_chain 이 기준선 사슬을 그리는 동안 참
        self._pull_parts = False  # led_chain 이 걷기 보드가 뽑는 사슬을 그리는 동안 참
        # 걷기 보드 — 기준선 dict 의 `ghost` 키 `{'wires': {key: n}, 'title', 'subtitle'}`.
        # 사슬째 뽑는 LED 사슬이 있으면 `'chains': {사슬 key: tag}` 도 든다.
        # `step_wire()` 가 그 key 를 만나면 점유표·구간에 안 남기고 `ghost_layer` 에 빨간
        # 점선으로 그린다. 뽑은 선의 핀이 뜨는 것이 정상이라 `partial` 이다.
        # 기준선 dict 에 키를 얹는 이유: `set_header()` 가 제목을 즉시 그려 사후에 못 바꾸고,
        # 빌더 시그니처를 늘리면 세 주차 스물세 빌더를 고쳐야 한다. `removal_board()` 가 만든다
        self.ghost = (baseline or {}).get('ghost')
        self.ghost_layer = Image.new('RGBA', self.im.size, (0, 0, 0, 0))
        self.ghost_drawn = {}     # key -> n. export() 가 빌더가 안 그린 key 를 잡는다
        self.ghost_chains_drawn = set()   # 사슬 key. export() 가 안 그린 사슬을 잡는다
        if self.ghost is not None:
            self.partial = True
        # 따라 그리기 층 — (lo, hi). 완성본 빌더를 그대로 돌리되 번호 lo 앞 배선은 회색·번호
        # 없이, lo~hi 는 색·완성본 번호로, hi 뒤는 버리는 판(`_hidden_draw`)에 그린다.
        # 안 보이는 배선도 점유표·구간·결선 순서표에는 남긴다 — 빼면 뒤 배선의
        # `free_rail_row()` 가 다른 행을 골라 완성본과 다른 그림이 된다(2026-09-28 팀원 전달용).
        # 기준선 사슬과 섞지 않는다 — 기준선의 회색은 "실험실에서 손대지 않는다" 는 다른 뜻이다
        if layer is not None:
            if baseline is not None:
                raise ValueError('layer 는 기준선 없는 완성본에만 준다 — baseline 과 함께 못 준다')
            ok = (isinstance(layer, tuple) and len(layer) == 2
                  and all(type(v) is int for v in layer) and 1 <= layer[0] <= layer[1])
            if not ok:
                raise ValueError(f'layer 는 1 <= lo <= hi 인 정수 쌍이어야 한다: {layer!r}')
        self.layer = layer
        self._hidden_draw = (_ScaledDraw(Image.new('RGBA', self.im.size, (0, 0, 0, 0)))
                             if layer is not None else None)
        self.submit = True
        self.title = ""
        self.subtitle = ""

        self.font_title = _font('kr', 21)
        self.font_subtitle = _font('kr', 14)
        self.font_kr_bold = _font('kr', 12)
        self.font_kr_sm = _font('kr', 11)
        self.font_en_bold = _font('en', 12)
        self.font_en_sm = _font('en', 10)
        self.font_chip = _font('en', 11)
        self.font_num = _font('en', 9)
        self.font_step = _font('kr', 11)

        self._init_cols()
        # 그린 것을 **사실 그대로** 적어 둔다. 손그림 검토가 이걸 정답으로
        # 읽는다. `_leads` 의 뜻풀이 문자열을 파싱하게 두면 말이 바뀔 때마다
        # 검사기가 조용히 깨진다 — 검사기는 코드를 읽어야지 산문을 읽으면 안 된다
        self.chips = []
        # 칩마다 이름 글자 상자(논리 좌표) — R14. 글꼴 따라 달라지는 픽셀이라 `chips`(도장에 든다)와 따로 둔다
        self.chip_label_boxes = []
        self.leds = []
        self.resistors = []
        self.led_chains = []
        self.unused_inputs = []
        self.unused_outputs = []

        self._addr_map = self._build_addr_map()
        self._sym_map = self._build_sym_map()

    def _layer_view(self, n):
        """따라 그리기 층에서 번호 n 배선의 모양 — 'shown'(색·번호) · 'faded'(회색) · 'hidden'."""
        if self.layer is None:
            return 'shown'
        lo, hi = self.layer
        if n < lo:
            return 'faded'
        if n > hi:
            return 'hidden'
        return 'shown'

    @property
    def partial(self):
        return self._partial

    @partial.setter
    def partial(self, value):
        """걷기 보드는 정의상 `partial` 이다 — 내려도 다시 올린다.

        걷어낸 가닥의 핀은 아무 데도 안 물린다(74HC08 pin 1·4). 그게 이 그림의 요점인데
        `verify()` R5 는 뜬 핀을 오류로 잡는다. 주차 파일들은 `bb.partial = st < 3`
        처럼 단계로 값을 정하므로, 생성자가 켜 둔 것을 빌더가 뒤에서 도로 내린다
        (2026-09-19 실험03 걷기 보드가 이걸로 PNG 재생성에서 죽었다). 세 주차 스물세
        빌더에 `or bb.ghost` 를 덧대는 대신 여기서 한 번 막는다.
        """
        self._partial = bool(value) or getattr(self, 'ghost', None) is not None

    # ---------------- 좌표 ----------------

    def _init_cols(self):
        """열 좌표표 — 판형 사양(`self.spec.cols`)의 사본. 렌더러 안에서는 이 표가 열 좌표의
        **유일한 권위**다. 손그림 검토는 같은 사양을 `column_table()` 로 읽는다."""
        self.cols = copy.deepcopy(self.spec.cols)
        # 레일 x -> 어느 전원인가. 넷 검사가 +5V 와 GND 가 한 넷이 됐는지 볼 때
        # 쓴다. 열 **이름**에서 뽑으므로 이 표가 유일한 권위라는 규칙을 지킨다
        self._rail_kind = {}
        for blk in self.cols.values():
            for key, x in blk.items():
                if 'gnd' in key:
                    self._rail_kind[x] = 'gnd'
                elif 'vcc' in key:
                    self._rail_kind[x] = 'vcc'

    def r_y(self, r):
        return int(round(self.spec.row0 + (r - 1) * self.spec.row_pitch))

    @staticmethod
    def is_rail_row(r):
        return 1 <= r <= ROW_MAX and r not in RAIL_GAP_ROWS

    def _row_of(self, y):
        """y 좌표에 제일 가까운 행 번호. addr() 과 hole_at() 이 같은 식을 쓴다 — 한쪽만 고치면 갈린다."""
        return int(round((y - self.spec.row0) / self.spec.row_pitch)) + 1

    def hole_at(self, x, y):
        """(x, y) 가 실제 홀이면 그 홀의 키 (열 x, 행), 아니면 None.

        레일은 5홀씩 묶여 빈 행이 있고, 단자대는 63행 전부 홀이다. 열·행 모두
        홀 중심에서 5px 안이어야 한다 — 열 피치가 16px 라 9px 로는 인접 열
        사이에 거부 구간이 없었다. 그 밖은 배선 통로거나 밀린 좌표다.
        v2 는 열 24px·행 19px 라 5px 허용치가 더 넉넉하다.
        """
        r = self._row_of(y)
        if not 1 <= r <= ROW_MAX:
            return None
        best = min(self._addr_map, key=lambda k: abs(k - x))
        if abs(best - x) > 5:
            return None
        if abs(y - self.r_y(r)) > 5:
            return None
        if '레일' in self._addr_map[best] and not self.is_rail_row(r):
            return None
        return (best, r)

    def _register_pass(self, points):
        """폴리라인이 지나가는 홀을 `_passed` 에 적는다 (양 끝점은 뺀다).

        2px 간격으로 훑어 `hole_at()` 에 걸리는 홀을 모은다 — 대각선도 같은
        식으로 잡힌다. 꺾이는 점이 홀 위에 있으면 그것도 '지나간 홀' 이다.
        """
        ends = {self.hole_at(*points[0]), self.hole_at(*points[-1])}
        for (x0, y0), (x1, y1) in zip(points, points[1:]):
            length = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** .5
            n = max(1, int(length / 2))
            for i in range(n + 1):
                t = i / n
                key = self.hole_at(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t)
                if key is not None and key not in ends:
                    self._passed.add(key)

    def _endpoints_under_wires(self, margin=6):
        """R3. 배선 끝점이나 부품 다리가 다른 배선 구간의 **중간**에 놓인 곳.

        점이 선 아래 깔리면 그 선에서 갈라지는 T 접속으로 읽힌다. 점퍼는 이어
        붙일 수 없으니 그런 접속은 없다 — **같은 넷이라도 봐주지 않는다.**
        2026-09-08 복합 회로 a7·a19 가 같은 넷이었고, 그래서 더 헷갈렸다.
        R4 가 같은 색 30px 이하를 밑동으로 봐주더라도 그 밑동의 끝점은 여기서
        걸린다 — 갈래는 옆 홀에서 세로로 뺀다.

        칩 핀 홀은 뺀다. 칩을 가로지르는 선은 핀 행을 지날 수밖에 없고 핀
        스텁은 회색이라 구분된다. 구간 양끝 `margin` px 안은 그 배선 자신의
        끝이라 뺀다 — 옆 홀(16px)에 나란히 끝나는 두 점퍼는 걸리지 않는다.
        """
        pts = []
        for i, (kind, points, desc) in enumerate(self._segments):
            for q in (points[0], points[-1]):
                pts.append((i, q, f'[{KIND_KR[kind]}] {desc}'))
        for (x, r), what in self._leads.items():
            if '다리' in what or '애노드' in what or '캐소드' in what:
                pts.append((None, (x, self.r_y(r)), f'[부품] {what}'))
        out = []
        for owner, (px, py), what in pts:
            for j, (kj, pj, dj) in enumerate(self._segments):
                if owner == j:
                    continue
                for (ax, ay), (bx, by) in zip(pj, pj[1:]):
                    dx, dy = bx - ax, by - ay
                    length = (dx * dx + dy * dy) ** .5
                    if length < 1:
                        continue
                    along = ((px - ax) * dx + (py - ay) * dy) / length
                    if along <= margin or length - along <= margin:
                        continue
                    if abs((px - ax) * dy - (py - ay) * dx) / length < 1.5:
                        out.append(f'{self.addr(px, py)} {what} ← 그 위를 지나는 [{KIND_KR[kj]}] {dj}')
        return sorted(set(out))

    def _jack_at(self, x, y):
        """(x, y) 가 전원 잭이면 그 잭 키('red'·'yellow'·'gray'), 아니면 None.

        잭은 보드 밖의 유일한 합법 끝점이다. `lead`·`_endpoint`·`nets` 가 같은 규칙을 써야 해서
        한 자리에 둔다 — 판형마다 잭 자리와 보드 위 테두리가 다르다(`self.spec`).
        """
        s = self.spec
        if y < s.jack_y_max and any(abs(x - jx) < 30 for jx in s.jacks.values()):
            return min(s.jacks, key=lambda k: abs(s.jacks[k] - x))
        return None

    def lead(self, x, y, what):
        """홀 (x, y) 에 리드 하나를 꽂는다.

        전원잭(`_jack_at`)은 보드 밖의 유일한 합법 끝점이라 건너뛴다. 홀이 아니면
        R1 위반, 이미 차 있으면 R2 위반으로 적어 두고 verify() 가 한꺼번에 낸다
        — 그리는 도중에 던지면 어디까지 그렸는지 알 수 없다.
        """
        if self._jack_at(x, y) is not None:
            return   # 전원잭 — 보드 밖의 유일한 합법 끝점
        key = self.hole_at(x, y)
        if key is None:
            self._not_holes.append(f'{what} — ({x:.0f}, {y:.0f}) = {self.addr(x, y)}')
            return
        prev = self._leads.get(key)
        if prev is not None:
            self._double.append(f'{self.addr(x, y)}: {prev} + {what}')
        else:
            self._leads[key] = what

    def free_rail_row(self, row, *xs):
        """`row` 에서 가장 가까운, `xs` 열의 홀이 전부 비어 있는 레일 행.

        `snap_rail_row()` 는 홀이 있는 행만 찾았다. 그래서 7행·8행에 나란히
        들어가는 입력 A·B 가 둘 다 7행 홀로 스냅돼 한 홀을 두고 다퉜고, 레일
        브리지 셋을 31행에 이으면 가운데 레일 31행에 점퍼 둘이 꽂혔다. 한 홀에
        리드 둘은 못 꽂는다 — 점유표를 보고 비어 있는 이웃으로 간다. 가까운
        순(같은 행, 위, 아래, 두 칸 위, …)이라 결과가 결정적이다.

        다른 배선이 **지나가는** 홀(`_passed`)도 찬 것으로 본다. pin 14 전원선이
        같은 행 중앙 GND 레일 홀 위를 지나는데 거기에 미사용 핀 접지선이 착지하면
        파란 점이 빨간 선 아래 깔린다 (R3). 먼저 그린 선이 지나간 자리는 비켜 간다.
        """
        for d in range(0, 8):
            for cand in ((row,) if d == 0 else (row - d, row + d)):
                if self.is_rail_row(cand) and all(
                        (x, cand) not in self._leads and (x, cand) not in self._passed for x in xs):
                    return cand
        raise ValueError(f'{row}행 근처에 빈 레일 홀이 없다: x={xs}')

    def _overlaps(self):
        """서로 다른 배선의 구간이 같은 축 위에 포개진 곳. 축 방향 구간만 본다.

        다른 색이면 8px 만 포개져도 잡는다. 같은 색은 30px(두 홀 폭 안)까지
        봐준다 — 같은 스트립의 옆 홀에 꽂은 두 번째 점퍼가 첫 점퍼 위를 되짚어
        여백으로 나가는 갈래 밑동이 그렇다. 다만 그 밑동은 굵은 선 아래 깔려
        "선 중간에서 얇은 선이 솟는" 그림이 되므로(2026-09-08 복합 회로 a7·a19
        지적) 봐준다고 해서 써도 되는 건 아니다 — 갈래는 옆 홀에서 세로로 뺀다.
        그 이상 같은 색으로 포개지면 두 넷이 한 선으로 보인다 (검정은 모든
        신호선의 색이다).
        """
        segs = []
        for i, (kind, pts, desc) in enumerate(self._segments):
            for a, b in zip(pts, pts[1:]):
                segs.append((i, kind, desc, a, b))
        out = []
        for i, ki, di, a, b in segs:
            for j, kj, dj, c, d in segs:
                if j <= i:
                    continue
                lim = 8 if ki != kj else 30
                where = None
                if abs(a[0] - b[0]) < .5 and abs(c[0] - d[0]) < .5 and abs(a[0] - c[0]) < 1.5:
                    lo = max(min(a[1], b[1]), min(c[1], d[1]))
                    hi = min(max(a[1], b[1]), max(c[1], d[1]))
                    if hi - lo > lim:
                        where = f'세로 {self.addr(a[0], lo)}~{self.addr(a[0], hi)}'
                elif abs(a[1] - b[1]) < .5 and abs(c[1] - d[1]) < .5 and abs(a[1] - c[1]) < 1.5:
                    lo = max(min(a[0], b[0]), min(c[0], d[0]))
                    hi = min(max(a[0], b[0]), max(c[0], d[0]))
                    if hi - lo > lim:
                        where = f'가로 {self.addr(lo, a[1])}~{self.addr(hi, a[1])}'
                if where:
                    out.append(f'{where} — [{KIND_KR[ki]}] {di} / [{KIND_KR[kj]}] {dj}')
        return out

    def _rail_xs(self):
        out = set()
        for block in self.cols.values():
            for key, x in block.items():
                if 'gnd' in key or 'vcc' in key:
                    out.add(x)
        return out

    def _uf_find(self, key):
        self._rail_uf.setdefault(key, key)
        while self._rail_uf[key] != key:
            self._rail_uf[key] = self._rail_uf[self._rail_uf[key]]
            key = self._rail_uf[key]
        return key

    def _uf_union(self, a, b):
        ra, rb = self._uf_find(a), self._uf_find(b)
        if ra != rb:
            self._rail_uf[rb] = ra

    def _shared_xs(self):
        """두 블록이 같은 x 로 부르는 열(v2 가운데 레일). v1 은 빈 집합이다."""
        return _shared_of(self.cols)

    def touch_rail(self, kind, x):
        """이 배선이 어느 전원 레일에 닿았는지 적어 둔다."""
        if kind in self._touched and x in self._rail_xs():
            self._touched[kind].add(x)

    def _build_addr_map(self):
        """x 좌표 -> 사람이 읽는 이름. 결선 순서표의 주소를 자동으로 만든다.

        두 블록이 같은 x 로 부르는 열(v2 가운데 레일)은 좌·우 접두어 없이 한 번만 적는다 —
        한 레일이다(설계 §3). v1 은 그런 열이 없어 이름이 그대로다.
        """
        names = {'gnd': 'GND레일', 'vcc': 'VCC레일',
                 'mid_gnd': '중앙GND레일', 'mid_vcc': '중앙VCC레일'}
        shared = self._shared_xs()
        out = {}
        for x, (block, key) in _hole_columns(self.cols).items():
            name = names.get(key, key)
            out[x] = name if x in shared else f"{'좌' if block == 'left' else '우'} {name}"
        return out

    def _build_sym_map(self):
        """x 좌표 -> (블록, 열 이름). `_addr_map` 의 기계용 짝이다. 두 블록이 같은 x 를 부르면
        (v2 가운데 레일) `left` 다."""
        return _hole_columns(self.cols)

    def sym(self, x, row):
        """(x, 행) -> (블록, 열 이름, 행). 홀이 아니면 None.

        `addr()` 이 사람이 읽는 '좌 b10' 을 만든다면 이쪽은 기계가 비교하는
        ('left', 'b', 10) 을 만든다. 허용치는 `hole_at()` 과 같은 5px 다 —
        열 피치가 16px 라 그보다 넓으면 인접 열 사이에 거부 구간이 없다.
        """
        best = min(self._sym_map, key=lambda k: abs(k - x))
        if abs(best - x) > 5:
            return None
        block, col = self._sym_map[best]
        return (block, col, row)

    def addr(self, x, y):
        """(x, y) 를 '좌 e7' 처럼 읽히는 주소로. 표에 그대로 들어간다."""
        s = self.spec
        if y < s.jack_y_max:
            return '전원잭'
        if x < s.board_left:
            return '보드밖(입력)'
        if x > s.board_right:
            return '보드밖'
        r = self._row_of(y)
        best = min(self._addr_map, key=lambda k: abs(k - x))
        # 9px 는 v1 열 피치(16)의 절반 남짓이고 v2(24)에서도 절반보다 작다
        if abs(best - x) > 9:
            # 홀이 아니라 배선 통로다. 분기점(T 접속)일 때만 여기 온다
            return '분기점'
        name = self._addr_map[best]
        return f'{name}{r}행' if '레일' in name else f'{name}{r}'

    # ---------------- 머리글 ----------------

    def set_header(self, title, subtitle, submit=True):
        """제목·부제는 **그리지 않는다** — 사이드카 JSON 으로 가고 체크리스트가 싣는다
        (2026-09-28 읽기면 개편: 그림에 구운 글자는 태블릿에서 작고 체크할 수 없었다).

        걷기 보드(ghost 모드)는 앞 회로 빌더가 부르는 제목 대신 `ghost` 의 제목을 쓴다 —
        빌더는 자기가 걷기 보드로 렌더되는지 모른다.
        """
        if self.ghost is not None:
            title, subtitle, submit = self.ghost['title'], self.ghost['subtitle'], False
        self.title, self.subtitle = title, subtitle
        self.submit = submit

    def connect_jacks(self, block='left'):
        """전원 잭 -> 보드 레일. 과거 결선도가 모두 그리던 선이다.

        잭 아래 끝에서 내려와 보드 위 테두리 바로 안쪽(`spec.jack_route_y`)을 가로질러 레일로
        간다. v1 은 테두리 242 + 8·16 = 250·258, v2 는 304 + 8·16 = 312·320 — 같은 식이다.
        """
        c, s = self.cols[block], self.spec
        y_v, y_g = s.jack_route_y
        r_v, r_g = self.free_rail_row(3, c['vcc']), self.free_rail_row(4, c['gnd'])
        self.step_wire([(s.jacks['red'], s.jack_bottom), (s.jacks['red'], y_v),
                        (c['vcc'], y_v), (c['vcc'], self.r_y(r_v))],
                       'vcc', '전원장치 +5V 잭', marker_at=(s.jacks['red'] + 46, s.jack_marker_y))
        self.step_wire([(s.jacks['gray'], s.jack_bottom), (s.jacks['gray'], y_g),
                        (c['gnd'], y_g), (c['gnd'], self.r_y(r_g))],
                       'gnd', '전원장치 0V 잭', marker_at=(s.jacks['gray'] + 46, s.jack_marker_y))

    # ---------------- 낱개 그리기 ----------------

    def note(self, text):
        if text not in self.notes:
            self.notes.append(text)

    def draw_badge(self, x, y, text, bg_col=(255, 255, 255, 235), text_col=(20, 20, 20, 255), font=None, pad=3):
        if font is None:
            font = self.font_kr_bold
        bbox = self.draw.textbbox((x, y), text, font=font)
        self.draw.rectangle([bbox[0]-pad, bbox[1]-pad, bbox[2]+pad, bbox[3]+pad], fill=bg_col, outline=text_col, width=1)
        self.draw.text((x, y), text, fill=text_col, font=font)

    def signal_tag(self, name, x, y, align='center', col=(20, 20, 20, 255), seg=None,
                   arrow=None):
        """보드 안 **신호 이름** 배지 — 입력 A·B·C, 출력 L1·L2·X·Y·Z.

        2026-09 실험01 예보 조교 감점(-1): 손그림 결선도에 입력 A·B·C 위치 표기가
        없었다. 원도는 입력 이름을 보드 밖(x=12) 꼬리표에만 적었고, 학생은 보드
        판형 위만 따라 그려 그 글자가 옮겨지지 않았다. 신호 이름은 그림의 일부라
        이 함수로 보드 안에 둔다. 규칙 문구는 여전히 `note()` 로 보드 밖이다.

        `align='center'` 면 (x, y) 가 배지 중심, `'left'` 면 x 가 배지 상자의 왼쪽
        끝이다. `seg` 는 이 이름이 가리키는 배선의 `_segments` 번호 — 겹침 검사가
        그 선만 봐준다.

        `arrow='left'|'right'` 는 입력 표지다 — `col` 로 채운 상자에 흰 화살촉과 흰 글자.
        화살촉은 점퍼선이 뻗는 쪽 끝에서 그쪽을 가리킨다(`D0▶`·`◀E`) — 중앙 여백의
        배지는 이것으로 좌·우 어느 블록으로 들어가는지 갈린다. 좌우 여백을 1 로 줄여
        화살촉 자리를 낸다(`INPUT_TRI`). 상자(겹침 검사 대상)는 화살촉까지 덮는다.
        """
        assert arrow in (None, 'left', 'right'), f"arrow 는 None·'left'·'right' 다: {arrow!r}"
        font, pad = self.font_en_bold, 2
        b = self.draw.textbbox((0, 0), name, font=font)
        w, h = b[2] - b[0], b[3] - b[1]
        hpad = 1 if arrow else pad
        tri, gap = (INPUT_TRI, 1) if arrow else (0, 0)
        full = tri + gap + w
        left = x - full / 2 if align == 'center' else x + hpad
        lead = tri + gap if arrow == 'left' else 0     # 글자 앞에 오는 화살촉 몫
        tx, ty = left + lead - b[0], y - h / 2 - b[1]
        box = self.draw.textbbox((tx, ty), name, font=font)
        box = (box[0] - lead - hpad, box[1] - pad,
               box[2] + (tri + gap - lead) + hpad, box[3] + pad)
        if arrow:
            self.draw.rectangle(box, fill=col, outline=col, width=1)
            cy = (box[1] + box[3]) / 2
            if arrow == 'right':
                x0 = box[2] - hpad - tri
                tip = [(x0, cy - h * 0.4), (x0 + tri, cy), (x0, cy + h * 0.4)]
            else:
                x0 = box[0] + hpad
                tip = [(x0 + tri, cy - h * 0.4), (x0, cy), (x0 + tri, cy + h * 0.4)]
            self.draw.polygon(tip, fill=(255, 255, 255, 255))
            self.draw.text((tx, ty), name, fill=(255, 255, 255, 255), font=font)
        else:
            self.draw_badge(tx, ty, name, (255, 255, 255, 235), col, font=font, pad=pad)
        self.tag_boxes.append((name, box, seg))

    def draw_wire(self, points, color, width=3):
        """번호 없는 생짜 배선. **지금 이 함수를 부르는 빌더는 하나도 없다.**

        `_segments` 에도 `_leads` 에도 아무것도 남기지 않는다 — 그래서 이걸로 그린
        선은 `verify()` 를 통째로 우회한다. 끝점이 홀인지(R1), 한 홀에 리드가
        둘인지(R2), 다른 배선 아래 깔리는지(R3·R4), 무엇과 무엇을 잇는지(R5)
        아무도 보지 않는다. 순서표에도 안 오른다. `step_wire()` 를 써라.
        """
        self.draw.line(points, fill=color, width=width, joint='curve')
        for p in (points[0], points[-1]):
            self.draw.ellipse([p[0]-3, p[1]-3, p[0]+3, p[1]+3], fill=color)

    def _dashed(self, points, color, width=2, dash=7, gap=5, draw=None):
        d = draw or self.draw
        for (x0, y0), (x1, y1) in zip(points, points[1:]):
            span = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
            if span == 0:
                continue
            ux, uy, t = (x1 - x0) / span, (y1 - y0) / span, 0.0
            while t < span:
                e = min(t + dash, span)
                d.line([(x0 + ux * t, y0 + uy * t), (x0 + ux * e, y0 + uy * e)],
                       fill=color, width=width)
                t = e + gap

    def instrument(self, x, row, label, desc, block='left', lane_row=None, name=None):
        """계측기·신호원 접점. **배선이 아니다** — 점퍼로 꽂는 게 아니라
        프로브 팁이나 집게로 문다. 회색 점선으로 그리고 계측표에 따로 쌓는다.

        보드 왼쪽 여백으로 뺀다. `lane_row` 를 주면 여백 안(x=140)에서 꺾어
        그 행으로 옮긴다 — 접점 두 개가 이웃한 행이면 꼬리표가 겹치기 때문이다.

        `name` 은 교안 회로도가 그 접점에 붙인 신호 이름이다(실험02 `VIN`·`VOUT`·
        `CH1`·`CH2`). 주면 **보드 안에도** 배지로 적는다 — 꼬리표만 보드 밖에 두면
        판형 위만 따라 그리는 손그림에서 이름이 빠진다(2026-09 실험01 조교 감점과
        같은 꼴, 2026-09-14 실험02 pre_review_round3). 자리는 그 접점과 같은
        스트립의 끝 여백이다: 칩 왼쪽 스트립(a~e)이면 레일과 a 열 사이, 오른쪽
        스트립(f~j)이면 j 열 바깥. 한 행의 다섯 홀은 한 노드라 스트립 끝에 적어도
        같은 핀을 가리킨다.
        """
        y = self.r_y(row)
        lane_y = self.r_y(lane_row) if lane_row else y
        # x=140·100·12 는 좌 여백 안이다 — v1 테두리 149, v2 144 둘 다 그 오른쪽이라 판형과 무관하다
        pts = [(x, y), (140, y)] + ([(140, lane_y)] if lane_row else []) + [(100, lane_y)]
        self._dashed(pts, PROBE)
        self.draw.ellipse([x - 5, y - 5, x + 5, y + 5], outline=PROBE, width=2)
        n = len(self.probes) + 1
        self.draw_badge(12, lane_y - 8, f'{n}. {label}', (248, 248, 250, 240), PROBE,
                        font=self.font_kr_sm, pad=2)
        entry = {'n': n, 'label': label, 'at': self.addr(x, y), 'desc': desc,
                 'sym': self.sym(x, row)}
        if name:
            entry['name'] = name
            c = self.cols[block]
            if x < c['chip_x1']:
                rail = max(v for k, v in c.items()
                           if ('gnd' in k or 'vcc' in k) and v < c['a'])
                # 가운데서 1.5px 왼쪽 — 3~4행 사이 번호 원(b 열 - 20)과 붙지 않게
                self.signal_tag(name, (rail + c['a']) / 2 - 1.5, y, col=PROBE)
            else:
                self.signal_tag(name, c['j'] + 6, y, align='left', col=PROBE)
        self.probes.append(entry)

    def instrument_note(self, label, at, desc):
        """그림에 그릴 자리가 없는 접점(회로에 꽂기 전 저항 측정 등)."""
        self.probes.append({'n': len(self.probes) + 1, 'label': label,
                            'at': at, 'desc': desc})

    def _marker(self, x, y, n, color):
        """배선 번호. 결선 순서표의 몇 번인지 가리킨다."""
        self.marker_boxes.append((x - 8, y - 8, x + 8, y + 8))
        self.draw.ellipse([x-8, y-8, x+8, y+8], fill=(255, 255, 255, 245), outline=color, width=2)
        t = str(n)
        bbox = self.draw.textbbox((0, 0), t, font=self.font_num)
        self.draw.text((x - (bbox[2]-bbox[0])/2 - bbox[0], y - (bbox[3]-bbox[1])/2 - bbox[1]),
                       t, fill=color, font=self.font_num)

    def enable_steps(self):
        self.numbered = True

    def _marker_removed(self, x, y, n):
        """걷기 번호 — 빨간 채움·흰 숫자. 순서표 원(흰 바탕·색 테두리)과 구분된다."""
        self.marker_boxes.append((x - 8, y - 8, x + 8, y + 8))
        self._marker_on(self.draw, x, y, n, REMOVE, filled=True)

    def _ghost_wire(self, points, n):
        """걷기 보드의 뽑을 배선. 유령 레이어에 빨간 점선, overlay 에 걷기 번호 원.

        점유표·구간·레일 접촉에 아무것도 안 남긴다 — 이 선은 이제 없는 것이고, 그 홀에
        다음 회로의 새 선이 앉을 수 있다(실험03 좌 d7·a9). 끝점 원도 안 찍는다.
        번호 원은 가장 긴 구간의 중점에, 기존 원과 겹치면 그 구간을 따라 옮긴다.
        """
        self._dashed(points, REMOVE, width=4, dash=9, gap=6,
                     draw=_ScaledDraw(self.ghost_layer))
        if len(points) < 2:
            self._marker_removed(points[0][0], points[0][1], n)
            return
        (x0, y0), (x1, y1) = max(zip(points, points[1:]),
                                 key=lambda s: abs(s[1][0] - s[0][0]) + abs(s[1][1] - s[0][1]))
        span = max(1.0, ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5)
        ux, uy = (x1 - x0) / span, (y1 - y0) / span
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        x, y = mx, my
        if self.spec.readability:
            # v2: 다른 번호 원만이 아니라 꽂힌 홀·칩 몸통도 피한다(R11). 2026-10-05 배치 탐색 8걷기 —
            # 유령선 번호 원이 중앙 GND 레일 홀을 덮었다. 구간을 따라 4px 씩 가운데부터 훑는다
            for k in sorted(range(-int(span / 2) + 8, int(span / 2) - 7, 4), key=lambda k: (abs(k), k)):
                cx, cy = int(mx + ux * k), int(my + uy * k)    # 찍는 자리(정수)로 잰다 — 반 행 선은 .5 다
                box = (cx - 8, cy - 8, cx + 8, cy + 8)
                if (not any(_boxes_touch(box, b) for b in self.marker_boxes)
                        and not any(box[0] - 1 <= hx <= box[2] + 1 and box[1] - 1 <= self.r_y(hr) <= box[3] + 1
                                    for hx, hr in self._leads)
                        and not any(_boxes_touch(box, b) for b, _cx, _ch in self._chip_bodies())):
                    self._marker_removed(cx, cy, n)
                    return
        for k in (0, 24, -24, 48):
            x, y = mx + ux * k, my + uy * k
            box = (x - 8, y - 8, x + 8, y + 8)
            if not any(_boxes_touch(box, b) for b in self.marker_boxes):
                break
        self._marker_removed(int(x), int(y), n)

    def step_wire(self, points, kind, desc, width=3, marker_at=None, count=1,
                  frm=None, to=None, marker_near=None):
        """배선 하나 + 결선 순서표 한 줄.

        `desc` 는 짧은 뜻풀이만 준다 — 어디서 어디로 가는지는 좌표에서
        자동으로 뽑는다 ('좌 b7 -> 좌 GND레일7행').

        기준선(`baseline`)에 같은 (색, 끝점, 끝점) 이 있으면 **회색으로 그리고
        번호를 주지 않는다** — 앞 단계에서 꽂아 둔 그대로다. 점유표·구간·레일
        접촉은 똑같이 남긴다: 회색이어도 그림대로 꽂히는지는 verify() 가 본다.

        따라 그리기 층(`layer`)이면 번호로 모양을 정한다(`_layer_view`). 어느 모양이든
        점유표·구간·결선 순서표에는 남는다 — 번호와 뒤 배선 자리가 완성본과 같아야 한다.

        `marker_near` 는 엔진 고정 부품(전원선·LED 사슬·입력 점퍼)의 기본 자리다 — v2 는 그 자리가
        R11 에 걸리면 가까운 빈 자리로 비킨다(`_settle_marker`). `marker_at` 은 빌더가 고른 자리라
        그대로 찍는다.
        """
        if marker_near is not None and not self.spec.readability and marker_at is None:
            marker_at = marker_near
        key = (kind, self._endpoint(points[0]), self._endpoint(points[-1]))
        if self.ghost is not None and key in self.ghost['wires']:
            n = self.ghost['wires'][key]
            self._ghost_wire(points, n)
            self.ghost_drawn[key] = n
            return None
        kept = self.baseline is not None and key in self.baseline['wires']
        view = self._layer_view(len(self.steps) + 1) if self.numbered and not kept else 'shown'
        draw = self._hidden_draw if view == 'hidden' else self.draw
        color = KEEP if kept or view == 'faded' else WIRE[kind]
        draw.line(points, fill=color, width=width, joint='curve')
        for p in (points[0], points[-1]):
            draw.ellipse([p[0]-3, p[1]-3, p[0]+3, p[1]+3], fill=color)
        for p in (points[0], points[-1]):
            self.lead(p[0], p[1], f'{KIND_KR[kind]} 배선 · {desc}')
            self.touch_rail(kind, p[0])
        self._segments.append((kind, [tuple(p) for p in points], desc))
        self._register_pass(points)
        if not kept and kind in ('sig', 'mid'):
            self.new_signal.append(key)
        if self.spec.readability:
            # 자리는 보이든 말든 늘 정한다 — 같은 선 순서면 완성본·층 그림·단계 그림이 같은 자리다
            if marker_at is None and marker_near is not None:
                marker_at = (self.marker_hints.get(key)
                             or self._settle_marker(*marker_near, own=len(self._segments) - 1))
                self.settled_markers[key] = marker_at
            if marker_at is None:
                marker_at = self._auto_marker(len(self._segments) - 1)
                if marker_at is None:
                    print(f'[WARN] 번호 원 자동 자리 없음 — {desc}: 옛 자리(첫 구간 가운데)에 찍는다. '
                          'R11 에 걸리면 marker_at 을 직접 주거나 경로를 바꾼다', file=sys.stderr)
            if marker_at is not None:
                self._marker_slots.append((marker_at[0] - 8, marker_at[1] - 8,
                                           marker_at[0] + 8, marker_at[1] + 8))
        if kept:
            self.kept.append(desc)
            return None
        if not self.numbered:
            return None

        n = len(self.steps) + 1
        if view == 'shown':
            if marker_at is None:
                (x0, y0), (x1, y1) = points[0], points[1] if len(points) > 1 else points[0]
                marker_at = ((x0 + x1) // 2, (y0 + y1) // 2)
            self._marker(marker_at[0], marker_at[1], n, color)

        frm = frm or self.addr(*points[0])
        to = to or self.addr(*points[-1])
        self.steps.append({'n': n, 'kind': kind, 'frm': frm, 'to': to,
                           'desc': desc, 'count': count})
        return n

    def step_note(self, kind, frm, to, desc, count=1, marker_at=None, marker_near=None):
        """그림에 이미 그려진 것을 표에 한 줄로 묶는다.

        `marker_at` 을 주면 보드 위에도 번호 원을 찍는다. **부품을 꽂는
        단계에는 반드시 준다** — 안 주면 표에는 번호가 있는데 그림에는 없어서,
        따라 그리는 사람이 그 차례에서 그림을 뒤지다 막힌다. `marker_near` 는 `step_wire` 와 같다.
        """
        if marker_near is not None and marker_at is None:
            if self.spec.readability and not self._pull_parts:
                nkey = ('note', kind, frm, to)
                marker_at = self.marker_hints.get(nkey) or self._settle_marker(*marker_near)
                self.settled_markers[nkey] = marker_at
            else:
                marker_at = marker_near
        if self.spec.readability and marker_at is not None and not self._pull_parts:
            self._marker_slots.append((marker_at[0] - 8, marker_at[1] - 8,
                                       marker_at[0] + 8, marker_at[1] + 8))
        if self._keep_parts:
            self.kept.append(desc)      # 기준선 사슬의 부품 줄 — 번호 없이 회색
            return None
        if self._pull_parts:
            return None                 # 걷기 보드가 뽑는 사슬 — 새로 꽂는 것이 아니다
        if not self.numbered:
            return None
        n = len(self.steps) + 1
        if marker_at is not None and self._layer_view(n) == 'shown':
            self._marker(marker_at[0], marker_at[1], n, WIRE[kind])
        self.steps.append({'n': n, 'kind': kind, 'frm': frm, 'to': to,
                           'desc': desc, 'count': count})
        return n

    def draw_resistor(self, x, y1, y2, label="330Ω", bands=None):
        self.lead(x, y1, f'{label} 윗다리')
        self.lead(x, y2, f'{label} 아랫다리')
        self.resistors.append({'label': label,
                               'top': self.sym(x, self._row_of(y1)),
                               'bottom': self.sym(x, self._row_of(y2))})
        wire_col = KEEP if self._keep_parts else (100, 100, 100, 255)
        body_col = (215, 215, 215, 255) if self._keep_parts else (225, 195, 145, 255)
        if self._keep_parts:
            bands = [KEEP] * 4
        if self._pull_parts:
            wire_col, body_col, bands = REMOVE, (240, 200, 200, 255), [REMOVE] * 4
        ymid = (y1 + y2) // 2
        self.draw.line([(x, y1), (x, ymid - 12)], fill=wire_col, width=2)
        self.draw.line([(x, ymid + 12), (x, y2)], fill=wire_col, width=2)
        self.draw.rectangle([x - 5, ymid - 12, x + 5, ymid + 12], fill=body_col, outline=(90, 70, 40, 255), width=1)
        if bands is None:
            if "1k" in label:
                bands = [(139, 69, 19, 255), (30, 30, 30, 255), (200, 20, 20, 255), (218, 165, 32, 255)]
            else:
                bands = [(204, 85, 0, 255), (204, 85, 0, 255), (139, 69, 19, 255), (218, 165, 32, 255)]
        for col, off in zip(bands, [-7, -2, 3, 8]):
            self.draw.line([(x - 4, ymid + off), (x + 4, ymid + off)], fill=col, width=2)

    def draw_led(self, x, y_anode, y_cathode, color_rgb=(230, 30, 30), label="LED"):
        self.lead(x, y_anode, f'{label} LED 애노드')
        self.lead(x, y_cathode, f'{label} LED 캐소드')
        self.leds.append({'tag': label,
                          'anode': self.sym(x, self._row_of(y_anode)),
                          'cathode': self.sym(x, self._row_of(y_cathode))})
        if self._keep_parts:
            color_rgb = KEEP[:3]
        lead_col = (130, 130, 130, 255)
        if self._pull_parts:
            color_rgb, lead_col = REMOVE[:3], REMOVE
        ymid = (y_anode + y_cathode) // 2
        self.draw.line([(x, y_anode), (x, ymid - 8)], fill=lead_col, width=2)
        self.draw.line([(x, ymid + 8), (x, y_cathode)], fill=lead_col, width=2)
        self.draw.ellipse([x - 8, ymid - 8, x + 8, ymid + 8], fill=(*color_rgb, 240), outline=(255, 255, 255, 255), width=2)
        if label:
            self.signal_tag(label, x + 10, ymid, align='left', col=color_rgb)

    def led_chain(self, x, top_row, tag, desc, block='left', color_rgb=(220, 20, 20),
                  marker_dx=-21, active_low=False):
        """LED + 330Ω + GND 한 벌. `x` 는 **신호가 도착하는 열**이다.

        LED 는 그 옆 열, 저항은 그 다음 열에 꽂는다. 같은 행 a~e(또는 f~j)는
        한 노드라 어느 홀이든 이어지지만, **한 홀에는 다리 하나만** 들어간다.
        이전 판은 배선 끝·LED 애노드·LED 캐소드·저항 윗다리를 전부 한 열에
        포개 그렸다 — 그림대로면 한 홀에 둘씩 꽂아야 했다. 사슬은 빈 열 쪽으로
        자란다: 오른쪽에 두 열이 없으면(d 열) 왼쪽으로 간다.

        저항 아래 GND 점퍼는 저항 행에서 **레일에 가장 가까운 빈 홀**에서 뽑는다.
        LED 열에서 뽑으면 왼쪽으로 자란 사슬(도착 d → LED c → 저항 b)의 가로선이
        저항 아랫다리 b 위를 지나간다 — 검정 선 아래 다리가 깔리는 그림이다.

        보드 위에는 **신호 이름만** 붙인다 (L1, X, Z…) — `draw_led()` 가
        `signal_tag()` 로 찍는다. 'L2 최종 LED (L2=A·B·C)' 같은 긴 문구는 결선
        순서표로 내려보낸다 — 손으로 옮겨 그릴 것이 아니면서 정작 그릴 홀을
        가리기 때문이다.

        `active_low` 면 **Negative Logic** 사슬이다(실험05 1-2, 교안 p9 "Output 을 Negative Logic
        으로 구축") — 출력이 0 일 때 켜진다. 신호 → 330Ω(옆 열, 윗행~윗행+2) → LED(그다음 열, 캐소드
        윗행+2 → 애노드 윗행+3) → +5V. 저항과 LED 의 열 쓰임이 보통 사슬과 뒤집힌다. 레일 점퍼는 보통
        사슬과 같은 윗행+3 에서 나가 배치기 `led_rows` 가 극성을 몰라도 된다. 레코드에는
        `'active_low': True` 를 더한다 — 보통 사슬에는 키를 넣지 않는다(`wiring()` → 도장).
        """
        c = self.cols[block]
        group = [c[k] for k in 'abcde'] if x <= c['e'] else [c[k] for k in 'fghij']
        i = group.index(x)
        step = 1 if i + 2 < len(group) else -1
        x_led, x_res = group[i + step], group[i + 2 * step]
        if active_low:
            x_l, a_row, k_row = x_res, top_row + 3, top_row + 2      # LED: 캐소드 위, 애노드 아래
            x_r, rt_row, rb_row = x_led, top_row, top_row + 2        # 330Ω: 신호 스트립 → 캐소드 스트립
        else:
            x_l, a_row, k_row = x_led, top_row, top_row + 1
            x_r, rt_row, rb_row = x_res, top_row + 1, top_row + 3
        key = (self.sym(x_l, a_row), self.sym(x_l, k_row),
               self.sym(x_r, rt_row), self.sym(x_r, rb_row))
        # 기준선에 같은 네 홀의 사슬이 있으면 LED·저항·GND 점퍼 전부 회색이고
        # 번호가 없다 — 앞 단계에서 꽂아 둔 그대로다. 플래그는 사슬을 그리는 동안만 선다
        # 걷기 보드가 사슬째 뽑는 사슬(`ghost['chains']`)은 LED·저항을 걷기 빨강으로 칠하고
        # 점선 상자로 두른다 — 번호는 GND 점퍼(유령선)가 받는다. 선만 빨갛고 부품이 회색이면
        # 그림이 "부품은 둔다" 로 읽힌다(2026-09-29 실험04 8걷기, 사용자)
        self._pull_parts = self.ghost is not None and key in self.ghost.get('chains', {})
        self._keep_parts = (self.baseline is not None and key in self.baseline['chains']
                            and not self._pull_parts)
        try:
            y_a, y_k = self.r_y(a_row), self.r_y(k_row)
            y_rt, y_rb = self.r_y(rt_row), self.r_y(rb_row)
            y_top, y_end = self.r_y(top_row), self.r_y(top_row + 3)
            self.draw_led(x_l, y_a, y_k, color_rgb, tag)
            self.draw_resistor(x_r, y_rt, y_rb, label="330Ω")
            if self._pull_parts:
                x0, x1 = min(x_l, x_r) - 12, max(x_l, x_r) + 12
                self._dashed([(x0, y_top - 12), (x1, y_top - 12), (x1, y_end + 12), (x0, y_end + 12),
                              (x0, y_top - 12)], REMOVE, width=3, dash=7, gap=5,
                             draw=_ScaledDraw(self.ghost_layer))
                self.ghost_chains_drawn.add(key)
            rec = {'tag': tag,
                   'signal': self.sym(x, top_row),
                   'anode': self.sym(x_l, a_row),
                   'cathode': self.sym(x_l, k_row),
                   'res_top': self.sym(x_r, rt_row),
                   'res_bottom': self.sym(x_r, rb_row)}
            if active_low:
                rec['active_low'] = True
            self.led_chains.append(rec)
            if active_low:
                self.step_note('sig', self.addr(x_r, y_rt), self.addr(x_l, y_a),
                               f'{tag}: 330Ω({self.addr(x_r, y_rt)}→{self.addr(x_r, y_rb)}) + '
                               f'LED(캐소드 {self.addr(x_l, y_k)}→애노드 {self.addr(x_l, y_a)}) 직렬 · '
                               f'0 이면 켜짐 · {desc}',
                               marker_near=(x + marker_dx, self.r_y(top_row + 1)))
                x_rail, kind, what = self.nearest_vcc_rail(x_led, block), 'vcc', f'{tag} LED 애노드 -> +5V'
            else:
                self.step_note('sig', self.addr(x_l, y_a), self.addr(x_r, y_rb),
                               f'{tag}: LED({self.addr(x_l, y_a)}→{self.addr(x_l, y_k)}) + '
                               f'330Ω({self.addr(x_r, y_k)}→{self.addr(x_r, y_rb)}) 직렬 · {desc}',
                               marker_near=(x + marker_dx, y_k))
                x_rail, kind, what = self.nearest_gnd_rail(x_led, block), 'gnd', f'{tag} 저항 아래 -> GND'
            # 레일 점퍼는 윗행+3 에서 레일에 가장 가까운 빈 홀로 — 그 행에서 비어 있는 열은 두 극성 모두
            # 신호 열과 `x_led` 다(보통 사슬은 LED 가 윗행~+1, Negative 는 저항이 윗행~+2)
            free = [x, x_led] + ([group[i + 3 * step]] if 0 <= i + 3 * step < len(group) else [])
            x_from = min(free, key=lambda h: abs(h - x_rail))
            r_rail = self.free_rail_row(top_row + 3, x_rail)
            self.step_wire([(x_from, y_end), (x_rail, self.r_y(r_rail))],
                           kind, what, width=2, marker_near=(x_from - 22, y_end + 2))
        finally:
            self._keep_parts = False
            self._pull_parts = False

    # ---------------- 칩 ----------------

    def _vtext(self, xy, text, fill, font):
        """세로쓰기. 과거 결선도가 칩 이름을 이렇게 적었다 — 몸통 안에 넣으면
        핀 번호를 d·g 열 홀 위에 얹지 않아도 된다."""
        real = font.real if isinstance(font, _ScaledFont) else font
        bbox = real.getbbox(text)
        pad = 2 * SCALE
        w, h = bbox[2] - bbox[0] + 2 * pad, bbox[3] - bbox[1] + 2 * pad
        tmp = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(tmp).text((pad - bbox[0], pad - bbox[1]), text, fill=fill, font=real)
        rot = tmp.rotate(-90, expand=True)
        self.overlay.alpha_composite(rot, (int(xy[0] * SCALE - rot.width / 2),
                                           int(xy[1] * SCALE - rot.height / 2)))

    def _chip_font(self, name, rows):
        """칩 이름 글꼴. DIP-14 는 늘 `font_chip`(11pt). DIP-16 은 세로 글자 상자가 `2·pitch − 4` 이하인
        가장 큰 크기다 — 몸통 가운데 반 행(k+3.5) 하나만 막아 a쪽 pin 1~7 이 그 위·아래 반 행 일곱으로
        건넌다. 74HC42 는 출력 일곱이 a쪽이다. 11pt(44px)면 반 행 셋을 막아 Y3·Y4 가 못 건넌다(2026-10-05 설계 #5)."""
        if rows == 7:
            return self.font_chip
        limit = 2 * self.spec.row_pitch - 4
        for size in range(11, 5, -1):
            f = _font('en', size)
            b = f.getbbox(name)
            if b[2] - b[0] + 4 <= limit:
                return f
        return _font('en', 6)

    def draw_chip(self, name, start_row, block='left'):
        c = self.cols[block]
        n = dip_pins(name)
        rows = n // 2
        x1, x2 = c['chip_x1'], c['chip_x2']
        y_top = self.r_y(start_row) - 8
        y_bot = self.r_y(start_row + rows - 1) + 8

        # 기준선의 같은 자리에 같은 칩이 있으면 몸통을 회색으로 그린다 — 앞
        # 단계에서 꽂아 둔 그대로라는 뜻이다(footer 범례 "회색 = 앞 단계에서
        # 그대로 둔다"). 배선·LED 사슬과 같은 규칙을 칩에도 적용한다.
        prev = (self.baseline['chips'].get((block, start_row))
                if self.baseline is not None else None)
        kept_chip = self.baseline is not None and prev == name
        body_fill = (200, 200, 200, 255) if kept_chip else (30, 33, 36, 255)
        body_outline = KEEP if kept_chip else (130, 140, 150, 255)
        # 몸통이 밝아지면 흰 글씨는 안 보인다 — 진한 회색으로 바꿔 pin 번호·
        # 이름을 계속 읽을 수 있게 한다
        text_fill = (55, 55, 55, 255) if kept_chip else (255, 255, 255, 255)
        num_fill = (90, 90, 90, 255) if kept_chip else (215, 215, 215, 255)

        self.draw.rectangle([x1, y_top, x2, y_bot], fill=body_fill, outline=body_outline, width=2)
        notch_w = (x2 - x1) // 3
        self.draw.arc([x1 + notch_w, y_top - 6, x2 - notch_w, y_top + 6], 0, 180, fill=(200, 200, 200, 255), width=2)
        label_at = ((x1 + x2) / 2, (y_top + y_bot) / 2)
        font = self._chip_font(name, rows)
        self._vtext(label_at, name, text_fill, font)
        # 세로로 돌린 이름 글자가 차지하는 상자(논리 좌표, `_vtext` 의 여백 2 포함) — R14
        lb = font.getbbox(name)
        half_w, half_h = (lb[3] - lb[1]) / 2 + 2, (lb[2] - lb[0]) / 2 + 2
        label_box = (label_at[0] - half_w, label_at[1] - half_h,
                     label_at[0] + half_w, label_at[1] + half_h)

        # 핀 번호는 **몸통 안쪽**에 찍는다. 이전 판은 e-15 / f+6 에 찍어서
        # d 열과 g 열 홀을 가렸다 — 정작 배선을 꽂는 자리다
        for i in range(rows):
            y = self.r_y(start_row + i)
            self.draw.line([(c['e'], y), (x1, y)], fill=(170, 170, 170, 255), width=3)
            self.draw.line([(x2, y), (c['f'], y)], fill=(170, 170, 170, 255), width=3)
            self.draw.text((x1 + 3, y - 6), str(i + 1), fill=num_fill, font=self.font_num)
            rt = str(n - i)
            w = self.draw.textbbox((0, 0), rt, font=self.font_num)[2]
            self.draw.text((x2 - 3 - w, y - 6), rt, fill=num_fill, font=self.font_num)
            self.lead(c['e'], y, f'{name} pin {i + 1}')
            self.lead(c['f'], y, f'{name} pin {n - i}')

        pins = {}
        for i in range(rows):
            pins[i + 1] = self.sym(c['e'], start_row + i)
            pins[n - i] = self.sym(c['f'], start_row + i)
        self.chips.append({'label': name, 'block': block,
                           'pin1_row': start_row, 'pins': pins})
        self.chip_label_boxes.append((label_box, self.chips[-1]))
        if self.baseline is not None:
            if kept_chip:
                self.kept.append(f'{name} 칩 그대로')
            elif prev is None:
                # 빈 자리에 새로 꽂는다 — 뽑을 것이 없으니 "교체"라고 하지 않는다
                self.swaps.append((prev, name, block, start_row))
                self.step_note('sig', '(빈 자리)', f'꽂는다: {name}',
                               f'{"좌" if block == "left" else "우"} {start_row}행에 새로 꽂는다',
                               marker_at=((x1 + x2) // 2, y_top + 12))
            else:
                # 같은 자리의 칩이 다르다 — 실험실에서 첫 번째로 할 일이다
                self.swaps.append((prev, name, block, start_row))
                # 번호 원은 칩 몸통 안, 위쪽 가장자리 근처에 찍는다 — 몸통 위 행은
                # 홀이 있고(복합회로에서는 가로 배선도 지나가) 원이 겹쳐 가린다
                self.step_note('sig', f'뽑는다: {prev}', f'꽂는다: {name}',
                               f'{"좌" if block == "left" else "우"} {start_row}행 칩 교체',
                               marker_at=((x1 + x2) // 2, y_top + 12))

    def bridge_rails(self, x_a, x_b, row, kind='gnd', label=None):
        """물리적으로 분리된 전원 레일 모듈 둘을 잇는 점퍼.

        v1 기준 — 이 템플릿의 레일쌍(좌 174/190, 중앙좌 468/484, 중앙우 542/558,
        우 836/852)은 각각 **별개 스트립**이다. 칩 7번 핀을 좌측 GND 레일에
        내리고 미사용 입력을 중앙 GND 레일에 내리면 두 레일이 이어져 있지
        않아 미사용 입력이 뜬다. 그 점퍼를 명시적으로 그린다.
        v2 는 가운데 레일이 하나라 좌 바깥 ↔ 가운데 두 가닥이면 된다. 같은 열을 이으면 오류다.
        """
        if x_a == x_b:
            raise ValueError(f'같은 레일 열을 잇는 브리지다(x={x_a}, {self._addr_map.get(x_a)}) — '
                             '두 블록이 이름만 다르게 부르는 한 레일이다. 브리지할 것이 없다')
        key = (kind, min(x_a, x_b), max(x_a, x_b))
        if key in self._bridged:
            return
        self._bridged.add(key)
        row = self.free_rail_row(row, x_a, x_b)
        self._uf_union(x_a, x_b)
        self.bridges.append((kind, self.sym(x_a, row), self.sym(x_b, row)))
        y = self.r_y(row)
        self.step_wire([(x_a, y), (x_b, y)], kind,
                       '레일 브리지',
                       marker_at=((x_a + x_b) // 2, y - 12))

    def connect_power(self, start_row, block='left', gnd_marker_at=None, gnd_col='d'):
        """pin 14(DIP-16 은 16) -> +5V, pin 7(DIP-16 은 8) -> GND. `gnd_marker_at` 은 pin 7 번호 원 자리를
        빌더가 지정할 때만 준다 — 기본 자리(레일과 d열 사이, 한 행 위)에 다른
        배선의 모서리가 오는 경우다. `gnd_col` 은 pin 7 접지선이 출발하는 열로,
        `connect_unused_inputs(col=)` 과 같은 이유로 바꾼다.

        어느 레일로 가는지는 블록마다 다르다. 좌측 보드는 f~j 쪽(pin 8~14)이
        중앙 레일에, a~e 쪽(pin 1~7)이 바깥 왼쪽 레일에 붙는다. 우측 보드는
        좌우가 뒤집힌다 — 이전 판은 좌측 기준 배선을 우측에도 그대로 써서
        복합회로 빌더가 전원 배선을 손으로 다시 썼다.

        점퍼는 핀 홀 바로 옆(d·g 열)에서 출발한다 — e·f 열 홀에는 칩 다리가
        꽂혀 있다. `connect_unused_inputs()` 가 처음부터 그렇게 했다.
        """
        c = self.cols[block]
        n = self._pins_at(block, start_row)
        g = start_row + n // 2 - 1          # GND 핀 행 — DIP-14 pin 7 은 k+6, DIP-16 pin 8 은 k+7
        x_vcc = c['mid_vcc'] if block == 'left' else c['vcc']
        x_gnd = c['gnd'] if block == 'left' else c['mid_gnd']
        r14 = self.free_rail_row(start_row, x_vcc)
        # DIP-16 은 번호 원을 선 위에 바로 얹는다 — 기본 자리(11px 위)는 반 행 k−0.5 를 덮는데, 그 반 행이
        # a쪽 pin 1 이 가운데 여백으로 건널 유일한 통로다(74HC42 는 a쪽 출력 일곱이 다 LED 로 간다, 설계 #5).
        # DIP-14 는 그대로(v1 도장·e4 스냅숏)
        dy_vcc = 0 if n == 16 else -11
        self.step_wire([(c['g'], self.r_y(start_row)), (x_vcc, self.r_y(r14))],
                       'vcc', f'pin {n} -> +5V 레일',
                       marker_near=((c['g'] + x_vcc) // 2, self.r_y(start_row) + dy_vcc))
        r7 = self.free_rail_row(g, x_gnd)
        self.step_wire([(c[gnd_col], self.r_y(g)), (x_gnd, self.r_y(r7))],
                       'gnd', f'pin {n // 2} -> GND 레일', marker_at=gnd_marker_at,
                       marker_near=((c['d'] + x_gnd) // 2, self.r_y(g) - 11))

    def nearest_gnd_rail(self, x, block='left'):
        """그 자리에서 제일 가까운 GND 레일. 좌우 블록은 a~e 쪽과 f~j 쪽에
        붙는 레일이 서로 뒤집혀 있어서 블록 이름만으로는 못 고른다."""
        c = self.cols[block]
        return min((c['gnd'], c['mid_gnd']), key=lambda xr: abs(xr - x))

    def nearest_vcc_rail(self, x, block='left'):
        c = self.cols[block]
        return min((c['vcc'], c['mid_vcc']), key=lambda xr: abs(xr - x))

    def _pins_at(self, block, start_row):
        """그 자리에 그린 칩의 핀 수. 칩 레코드에 키를 더하지 않고 `pins` 개수로 읽는다 — 레코드는
        `wiring()` 으로 도장에 든다. 아직 안 그렸으면 14 로 보고 경고한다(16핀 칩을 그리기 전에 전원을
        부르면 pin 7 출력을 GND 에 묶는 그림이 조용히 나간다). v1 은 경고하지 않는다 — 승인 빌더(실험01~03)는
        뒤 단계에 꽂을 칩의 빈 소켓 전원을 먼저 깔고, 전부 14핀이다."""
        for ch in self.chips:
            if ch['block'] == block and ch['pin1_row'] == start_row:
                return len(ch['pins'])
        if self.board == 'v1':
            return 14
        print(f'[WARN] {block} {start_row}행에 그린 칩이 없다 — 14핀으로 본다. draw_chip 을 먼저 부른다',
              file=sys.stderr)
        return 14

    def connect_unused_inputs(self, pins, start_row, block='left', bridge_row=None,
                              chip='', rail='gnd', col='d'):
        """미사용 입력핀을 전원 레일로. 여러 가닥이지만 표에는 **한 줄**로 묶는다.

        `rail='vcc'` 면 GND 가 아니라 +5V 로 올린다. 실험02 교안 p8 도면이
        미사용 입력 일부를 VCC 로 묶으라고 지정한다 — CMOS 입력은 뜨면 안 될
        뿐이지 어느 쪽으로 묶든 상관없고, 도면을 그대로 따르는 편이 대조하기 쉽다.

        `col` 은 pin 1~7 쪽 접지선이 출발하는 열이다 (기본 d — 핀 홀 e 바로 옆).
        그 열 위로 다른 세로선이 지나가면(복합 회로의 초록 A'·B 선이 d열을 탄다)
        접지선 끝점이 그 선 아래 깔리므로 빈 열로 옮긴다.

        착지는 **자기 행에 레일 홀이 있는 핀부터** 한다. 빈 행(8·14·20행)의 핀은
        이웃 행으로 밀리는데, 그 핀이 먼저 착지하면 정작 그 행의 주인 핀이 밀린다.
        """
        c = self.cols[block]
        n = self._pins_at(block, start_row)
        h = n // 2
        placed = []
        for p in pins:
            if 1 <= p <= h:
                placed.append((start_row + (p - 1), c[col], p))
            elif h < p <= n:
                placed.append((start_row + (n - p), c['g'], p))
        order = sorted(range(len(placed)), key=lambda i: (not self.is_rail_row(placed[i][0]), i))
        # 기준선에 같은 (색, 끝점, 끝점) 이 있으면 `step_wire` 와 같은 규칙으로 회색이다
        # — 실험02 C1→C2 는 칩만 갈아 끼우므로 pull 선 다섯 가닥이 전부 그대로다.
        # 전부 회색이면 순서표에 번호 대신 "그대로 둔다" 로 남긴다
        kept_lines = 0
        # 따라 그리기 층 — 가닥이 여럿이어도 번호는 뒤의 `step_note` 하나라 그 번호로 정한다
        view = self._layer_view(len(self.steps) + 1) if self.numbered else 'shown'
        draw = self._hidden_draw if view == 'hidden' else self.draw
        for row, x_pin, p in (placed[i] for i in order):
            pick = self.nearest_vcc_rail if rail == 'vcc' else self.nearest_gnd_rail
            x_rail = pick(x_pin, block)
            r_rail = self.free_rail_row(row, x_rail)
            key = (rail, self._endpoint((x_pin, self.r_y(row))),
                   self._endpoint((x_rail, self.r_y(r_rail))))
            kept = self.baseline is not None and key in self.baseline['wires']
            kept_lines += kept
            col = KEEP if kept or view == 'faded' else WIRE[rail]
            draw.line([(x_pin, self.r_y(row)), (x_rail, self.r_y(r_rail))], fill=col, width=2)
            self._segments.append((rail, [(x_pin, self.r_y(row)), (x_rail, self.r_y(r_rail))],
                                   f'{chip} pin {p} 미사용 입력'))
            self._register_pass([(x_pin, self.r_y(row)), (x_rail, self.r_y(r_rail))])
            draw.ellipse([x_pin-3, self.r_y(row)-3, x_pin+3, self.r_y(row)+3], fill=col)
            draw.ellipse([x_rail-3, self.r_y(r_rail)-3, x_rail+3, self.r_y(r_rail)+3], fill=col)
            self.lead(x_pin, self.r_y(row), f'{chip} pin {p} 미사용 입력 접지선')
            self.lead(x_rail, self.r_y(r_rail), f'{chip} pin {p} 미사용 입력 접지선')
            self.touch_rail(rail, x_rail)
            self.unused_inputs.append({'chip': chip, 'pin': p, 'rail': rail,
                                       'block': block, 'pin1_row': start_row})

        pin_str = ", ".join(str(p) for p in pins)
        desc = '미사용 입력 풀업' if rail == 'vcc' else '미사용 입력 접지'
        if placed and kept_lines == len(placed):
            self.kept.append(f'{chip} pin {pin_str} {desc}')
        else:
            self.step_note(rail, f'{chip} pin {pin_str}',
                           '가까운 +5V 레일' if rail == 'vcc' else '가까운 GND 레일',
                           desc, count=len(pins))

        if rail == 'gnd' and any(h < p <= n for p in pins):
            if bridge_row is None:
                print(f"[WARN] {block} 블록 미사용 입력 {pin_str} 이 중앙 GND 레일에 "
                      f"내려갔는데 bridge_row 가 없다 — 7번 핀 레일과 이어지지 않아 "
                      f"뜬다. 빌더에서 bridge_row 를 넘겨라", file=sys.stderr)
            else:
                self.bridge_rails(c['mid_gnd'], c['gnd'], bridge_row, kind='gnd')

    def mark_unused_outputs(self, pins, start_row, block='left', chip=''):
        """미사용 출력은 **아무것도 그리지 않는다.** 개방이 곧 배선 없음이다.

        이전 판은 핀마다 'Pin 8: NC (개방)' 배지를 보드 위에 찍었다. 손으로
        옮겨 그릴 것이 하나도 없는 문구가 정작 그릴 홀을 덮었다.
        """
        for p in pins:
            self.unused_outputs.append({'chip': chip, 'pin': p,
                                        'block': block, 'pin1_row': start_row})

    def mark_unused_inputs(self, pins, start_row, block='left', chip=''):
        """미사용 게이트 입력을 **개방**으로 등록한다. 아무것도 그리지 않는다.

        2026-09-11 실험01 실측: 미사용 입력을 접지하지 않아도 진리표가 같았고,
        접지선은 NAND 순서표 20줄 중 12줄이었다. 학교 규정도 아니다(운영계획서
        3.2 6) 은 손그림·학번·이름·날짜만 요구한다). 그래서 뺀다 — 교안이
        미사용 핀 처리를 지시한 주차(실험02 p9)만 `connect_unused_inputs` 로
        그린다. **사용하는 게이트의 입력은 여전히 반드시 물린다** — 그쪽이
        R5ⓒ 가 잡는 진짜 결함이다.
        """
        for p in pins:
            self.unused_inputs.append({'chip': chip, 'pin': p, 'rail': None,
                                       'block': block, 'pin1_row': start_row})

    # ---------------- 내보내기 ----------------

    def _marker_on(self, d, x, y, n, color, filled=False):
        """번호 원. `filled` 면 색 채움·흰 숫자 — 걷기 번호가 순서표 번호와 헷갈리지 않게."""
        fill, text = ((color, (255, 255, 255, 255)) if filled
                      else ((255, 255, 255, 245), color))
        d.ellipse([x-8, y-8, x+8, y+8], fill=fill, outline=color, width=2)
        t = str(n)
        bbox = d.textbbox((0, 0), t, font=self.font_num)
        d.text((x - (bbox[2]-bbox[0])/2 - bbox[0], y - (bbox[3]-bbox[1])/2 - bbox[1]),
               t, fill=text, font=self.font_num)

    def _endpoint(self, p):
        """배선 끝점 -> `('jack', 색)` 또는 `('hole', (블록, 열, 행))`. `wiring()`
        과 기준선 비교가 **같은 규칙**을 써야 해서 한 자리에 둔다."""
        x, y = p
        color = self._jack_at(x, y)
        if color is not None:
            return ('jack', color)
        return ('hole', self.sym(x, self._row_of(y)))

    def _sym_addr(self, end):
        """`_endpoint()` 출력 -> '좌 b10' 처럼 읽히는 주소. `addr()` 과 같은 말이다."""
        if end[0] == 'jack':
            return '전원잭'
        block, col, row = end[1]
        name = self._addr_map[self.cols[block][col]]
        return f'{name}{row}행' if '레일' in name else f'{name}{row}'

    def snapshot(self):
        """이 보드의 배선·사슬·칩을 **다음 보드의 기준선**으로 쓸 수 있게 낸다.

        끝점 기호만 담는다 — 꼭짓점은 여기 없다. 걷기 보드(`removal_board`)는 앞 회로
        빌더를 **다시 돌려** 그리므로 살아 있는 빌더의 꼭짓점을 쓴다(`_ghost_wire`).
        """
        w = self.wiring()
        return {
            'wires': {(x['kind'], x['frm'], x['to']): x['desc'] for x in w['wires']},
            'chains': {(ch['anode'], ch['cathode'], ch['res_top'], ch['res_bottom']): ch['tag']
                       for ch in w['chains']},
            'chips': {(ch['block'], ch['pin1_row']): ch['label'] for ch in w['chips']},
        }

    def removals(self):
        """기준선에 있었는데 이번 보드에 없는 **배선** — 걷기 번호를 매겨 낸다.

        순서는 기준선(앞 보드)의 그리기 순서라 결정적이다. netlist 단계 표가 이
        번호(걷기 ①·②)를 인용한다. 칩·사슬은 여기 없고 `removed()` 에만 있다 —
        칩 교체는 순서표에 이미 번호 원이 있다.

        꼭짓점은 내지 않는다 — 걷기 보드는 앞 회로 빌더를 다시 돌려 그리므로 그림은
        살아 있는 빌더의 꼭짓점으로 그려진다(`_ghost_wire`).
        """
        if self.baseline is None:
            return []
        drawn = {(k, self._endpoint(pts[0]), self._endpoint(pts[-1]))
                 for k, pts, _ in self._segments}
        out = []
        for key, desc in self.baseline['wires'].items():
            if key in drawn:
                continue
            out.append({'n': len(out) + 1, 'key': key,
                        'addr': f'{self._sym_addr(key[1])} → {self._sym_addr(key[2])}',
                        'desc': desc})
        return out

    def removed(self):
        """기준선에 있었는데 이번 보드에 없는 것 — 실험실에서 **걷을** 것. 배선 → 칩 →
        사슬 순의 문자열. 배선 줄은 `removals()` 와 같은 순서·같은 수다."""
        if self.baseline is None:
            return []
        out = [f"{r['addr']} · {r['desc']}" for r in self.removals()]
        here = {(c['block'], c['pin1_row']) for c in self.chips}
        for key, label in self.baseline['chips'].items():
            if key not in here:
                out.append(f'칩 {label} ({"좌" if key[0] == "left" else "우"} {key[1]}행) 뽑는다')
        chains = {(ch['anode'], ch['cathode'], ch['res_top'], ch['res_bottom'])
                  for ch in self.led_chains}
        for key, tag in self.baseline['chains'].items():
            if key not in chains:
                out.append(f'LED {tag} 사슬 ({self._chain_span(key)}) 뽑는다')
        return out

    def _marker_clear(self, x, y, own=None, pad=2):
        """(x, y) 에 번호 원을 찍으면 아무것도 안 가리는가 — 꽂힌 홀, 다른 번호 원, 칩 몸통,
        `own` 번째가 아닌 배선."""
        box = (x - 8 - pad, y - 8 - pad, x + 8 + pad, y + 8 + pad)
        if any(box[0] <= hx <= box[2] and box[1] <= self.r_y(hr) <= box[3] for hx, hr in self._leads):
            return False
        # 그려진 원이 아니라 정해진 **자리**를 피한다 — 층 그림에서 흐리게 둔 앞 번호도 완성본에선 있다
        if any(not (box[2] <= m[0] or m[2] <= box[0] or box[3] <= m[1] or m[3] <= box[1])
               for m in self._marker_slots + self.marker_boxes):
            return False
        if any(not (box[2] <= b[0] or b[2] <= box[0] or box[3] <= b[1] or b[3] <= box[1])
               for b, _cx, _ch in self._chip_bodies()):
            return False
        return not any(i != own and self._seg_in_box(a, b, box)
                       for i, (_k, pts, _d) in enumerate(self._segments)
                       for a, b in zip(pts, pts[1:]))

    def _auto_marker(self, idx):
        """`_segments[idx]` 의 번호 원 자리 — R11 을 지키는 첫 점. 가로 구간을 먼저, 그다음 긴
        구간 순으로 가운데부터 4px 씩 밖으로 훑는다. 세로 차선 한복판에 앉은 원은 이웃 차선을
        막는다(시험판 MUX U1 pin 8 임시선). 자리가 없으면 None — 호출자가 옛 자리에 찍고
        verify() 의 R11 이 멈춘다."""
        pts = self._segments[idx][1]
        segs = sorted(zip(pts, pts[1:]), key=lambda s: (abs(s[0][1] - s[1][1]) > .5,
                                                        -(abs(s[0][0] - s[1][0]) + abs(s[0][1] - s[1][1]))))
        for a, b in segs:
            length = ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** .5
            if length < 24:
                continue
            mid = length / 2
            for off in range(0, int(mid - 12) + 1, 4):     # +1: 길이 24~25 구간도 가운데 한 점은 본다
                for t in sorted({mid - off, mid + off}):
                    x = round(a[0] + (b[0] - a[0]) * t / length)
                    y = round(a[1] + (b[1] - a[1]) * t / length)
                    if self._marker_clear(x, y, own=idx):
                        return (x, y)
        return None

    # 엔진 고정 부품 번호 원이 비킬 때 훑는 자리 — 4px 격자, 32px 안, 가까운 순(동률은 가로 먼저)
    _SETTLE_OFFSETS = sorted(((dx, dy) for dx in range(-32, 33, 4) for dy in range(-32, 33, 4)
                              if (dx, dy) != (0, 0)),
                             key=lambda d: (d[0] ** 2 + d[1] ** 2, abs(d[1]), d[0], d[1]))

    def _marker_fits(self, x, y, own=None):
        """(x, y) 번호 원이 `marker_problems()` 에 안 걸리는가 — 꽂힌 홀, 다른 번호 원(자리), 칩 몸통,
        배선 둘 이상(자기 배선 포함), 그리고 이미 그린 신호 이름 배지."""
        box = (x - 8, y - 8, x + 8, y + 8)
        if any(box[0] - 1 <= hx <= box[2] + 1 and box[1] - 1 <= self.r_y(hr) <= box[3] + 1
               for hx, hr in self._leads):
            return False
        if any(not (box[2] <= m[0] or m[2] <= box[0] or box[3] <= m[1] or m[3] <= box[1])
               for m in self._marker_slots + self.marker_boxes):
            return False
        if any(not (box[2] <= b[0] or b[2] <= box[0] or box[3] <= b[1] or b[3] <= box[1])
               for b, _cx, _ch in self._chip_bodies()):
            return False
        if any(_boxes_touch(box, b) for _n, b, _seg in self.tag_boxes):
            return False
        under = sum(1 for _k, pts, _d in self._segments
                    if any(self._seg_in_box(a, b, box) for a, b in zip(pts, pts[1:])))
        return under <= 1

    def _settle_marker(self, x, y, own=None):
        """엔진 고정 부품의 번호 원 자리 — 기본 자리 (x, y) 가 R11 을 지키면 그대로(지금 그림이 안
        바뀐다), 아니면 가까운 순으로 아무것도 안 가리는 자리. 없으면 기본 자리 — verify() 가 멈춘다.
        2026-10-05 배치 탐색: 입력 행이 LED 행 바로 아래면 입력 점퍼 원이 LED 사슬 원과 겹쳤다."""
        if self._marker_fits(x, y, own):
            return (x, y)
        for dx, dy in self._SETTLE_OFFSETS:
            cx, cy = x + dx, y + dy
            if self._marker_clear(cx, cy, own=own) and self._marker_fits(cx, cy, own):
                return (cx, cy)
        return (x, y)

    def content(self):
        """도장에 드는 것 — 이 그림이 **무엇을** 싣는가. 주차 파일이 넘긴 문자열과 홀
        주소뿐이다. 픽셀·글꼴·줄바꿈 결과·엔진 범례 문구는 넣지 않는다 — 기계마다
        글꼴이 달라도 같은 결선이면 같은 도장이 나와야 한다.

        `verify()` 뒤에 불러야 `wiring()['overlaps']` 가 찬다 — `export()` 가 그렇게 한다.
        """
        out = {
            'title': self.title, 'subtitle': self.subtitle, 'submit': self.submit,
            'notes': list(self.notes),
            'steps': list(self.steps),
            'probes': list(self.probes),
            'kept': len(self.kept) if self.baseline is not None else None,
            'removed': self.removed(),
            'wiring': self.wiring(),
        }
        if self.board != 'v1':
            # v2 부터만 든다 — v1 도장은 그대로이고, 결선이 같아도 판형을 바꾸면 도장이 바뀐다
            out['board'] = self.board
        if self.layer is not None:
            # 층 보드에서만 든다 — 완성본 도장은 그대로다
            out['layer'] = list(self.layer)
        if self.ghost is not None:
            # 걷기 보드에서만 든다 — 다른 보드의 도장은 그대로라 재생성 범위가 안 번진다
            out['ghost'] = [(r['n'], r['addr']) for r in self.removals()]
            if self.ghost.get('chains'):
                # 사슬째 뽑는 걷기 보드에서만 든다 — 옛 걷기 보드 도장은 그대로다
                out['ghost_chains'] = self._ghost_chain_lines()
        return out

    def _ghost_chain_lines(self):
        """걷기 보드가 사슬째 뽑는 LED 사슬 — 번호 없는 한 줄씩. 그리기 순서대로."""
        chains = self.ghost.get('chains', {}) if self.ghost is not None else {}
        return [f'LED {chains[k]} 사슬 ({self._chain_span(k)}) 의 LED·330Ω 을 뽑는다 (빨간 점선 상자)'
                for k in chains]

    def _chain_span(self, key):
        """사슬 열쇠(애노드, 캐소드, 저항 윗다리, 저항 아랫다리) → '맨 위 홀~맨 아래 홀'. 보통 사슬은 애노드~
        저항 아랫다리 그대로(도장 불변). Negative 사슬은 저항 윗다리(윗행)~애노드(윗행+3)다."""
        top = min((key[0], key[2]), key=lambda h: h[2])
        bottom = max((key[0], key[3]), key=lambda h: h[2])
        return f'{self._sym_addr(("hole", top))}~{self._sym_addr(("hole", bottom))}'

    def sidecar(self):
        """그림 옆에 실을 글자 — 체크리스트가 읽는다. PNG 에는 보드만 있다(2026-09-28).

        걷기 번호는 걷기 보드에서만 준다 — 그 보드만 그림에 빨간 번호 원이 있다. 칩·사슬
        걷기(`removed()` 의 배선 뒤쪽)는 번호가 없다.
        """
        ghost = self.ghost is not None
        wires = self.removals()
        removals = [{'n': r['n'] if ghost else None, 'text': f"{r['addr']} · {r['desc']}"}
                    for r in wires]
        removals += [{'n': None, 'text': g} for g in self.removed()[len(wires):]]
        removals += [{'n': None, 'text': g} for g in self._ghost_chain_lines()]
        side = {
            'schema': SIDECAR_SCHEMA,
            'title': self.title,
            'subtitle': self.subtitle,
            'kept': len(self.kept) if self.baseline is not None else None,
            'steps': [{'n': s['n'], 'kind': s['kind'], 'from': s['frm'], 'to': s['to'],
                       'desc': s['desc'], 'count': s['count']} for s in self.steps],
            'removals': removals,
            'probes': [{'n': p['n'], 'label': p['label'], 'at': p['at'], 'desc': p['desc']}
                       for p in self.probes],
        }
        if self.board != 'v1':
            # v2 부터만 든다. 커밋된 v1 사이드카는 바이트로 대조된다(`CommittedPngs`) — 없으면 v1 이다
            side['board'] = self.board
        return side

    def stamp(self):
        # v2 = 보드만 담은 PNG(2026-09-28). 접두어가 바뀌어 옛 PNG 는 전부 stale 로 잡힌다
        blob = json.dumps(self.content(), ensure_ascii=False, sort_keys=True, default=_jsonable)
        return 'v2:' + hashlib.sha256(blob.encode('utf-8')).hexdigest()

    def export(self, output_path, max_row=35):
        self.verify()
        if self.ghost is not None:
            missing = [f'{self._sym_addr(k[1])} → {self._sym_addr(k[2])}'
                       for k in self.ghost['wires'] if k not in self.ghost_drawn]
            assert not missing, (
                f'걷기 대상 배선을 앞 빌더가 그리지 않았다: {missing} — '
                'removal_board 의 prev 빌더·stage 가 기준선을 만든 것과 같아야 한다')
            # 반대쪽도 본다 — 유령 목록이 실제로 걷히는 배선의 부분집합이어도 안 된다.
            # 번호 없는 가닥이 조용히 사라지면 그림이 무엇을 뽑는지 말해 주지 않는다.
            listed = set(self.ghost['wires'])
            actual = {r['key'] for r in self.removals()}
            extra = [self._sym_addr(k[1]) + ' → ' + self._sym_addr(k[2])
                     for k in actual - listed]
            gone = [self._sym_addr(k[1]) + ' → ' + self._sym_addr(k[2])
                    for k in listed - actual]
            assert not (extra or gone), (
                f'걷기 목록과 실제로 걷히는 배선이 다르다 — 목록에 없는데 걷히는 것: '
                f'{extra}, 목록에 있는데 안 걷히는 것: {gone} — '
                'removal_board 의 nxt 빌더가 기준선을 만든 prev 와 짝이 맞아야 한다')
            undrawn = [self.ghost['chains'][k] for k in self.ghost.get('chains', {})
                       if k not in self.ghost_chains_drawn]
            assert not undrawn, (
                f'걷기 대상 LED 사슬을 앞 빌더가 그리지 않았다: {undrawn} — '
                'removal_board 의 prev 빌더·stage 가 기준선을 만든 것과 같아야 한다')
        # 유령선은 템플릿과 overlay 사이 — 회색 선·칩·새 선이 유령선을 덮는다
        final_im = Image.alpha_composite(Image.alpha_composite(self.im, self.ghost_layer),
                                         self.overlay)
        board_h = self.r_y(max_row) + 20
        out = final_im.crop((0, 0, self.spec.size[0] * SCALE, board_h * SCALE)).convert('RGB')
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        info = PngInfo()
        info.add_text(STAMP_KEY, self.stamp())
        out.save(output_path, pnginfo=info)
        with open(os.path.splitext(output_path)[0] + '.json', 'w', encoding='utf-8') as f:
            json.dump(self.sidecar(), f, ensure_ascii=False, indent=1)
            f.write('\n')
        staged = self.partial or self.baseline is not None
        print(f"[SUCCESS] Exported: {output_path} "
              f"({out.size[0]}x{out.size[1]}, 결선 {len(self.steps)}단계, "
              f"새 신호선 {len(self.new_signal)} · 걷는 선 {len(self.removals())})")
        if staged and len(self.new_signal) > STAGE_WIRE_BUDGET:
            # 막지 않는다 — 저작 중에는 넘는 보드를 그려 봐야 어디서 쪼갤지 보인다.
            # 주차 보드 테스트(`tests/test_breadboard_boards.py`)가 승인을 막는다.
            print(f"[WARN] 새 신호선이 {len(self.new_signal)} 가닥이다 "
                  f"(예산 {STAGE_WIRE_BUDGET}) — 관측 노드 하나로 단계를 더 쪼갠다")
