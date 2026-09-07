import os
import sys
import argparse
from PIL import Image, ImageDraw, ImageFont

# 저장소 루트. 이 파일은 `<루트>/.claude/skills/breadboard-diagram/scripts/`
# 에 있다. **cwd 로 찾지 않는다** — 예전 후보 목록이 상대 경로여서 저장소
# 루트 밖에서 부르면 조용히 못 찾았고, 그 자리를 메우려고 남의 계정에서는
# 그냥 죽는 절대 경로가 하드코딩돼 있었다.
REPO_ROOT = os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..'))

# 브레드보드 템플릿 정본. **`.claude/assets/` 가 이긴다.**
#
# 이 클래스의 `cols`·`r_y()` 픽셀 좌표는 이 한 장의 그림에 맞춰져 있다.
# 그래서 "같은 브레드보드 그림"이면 아무거나 써도 되는 게 아니다 —
# 2026-2 배포본 `강의노트/공지사항/Breadboard.pdf` 는 도면도 세로 좌표도
# 같지만(보드 상하단이 y=242·1317 로 일치) **가로가 중앙 기준 약 5% 넓다**.
# 좌우 끝 레일이 최대 19px 밀리는데 홀 간격이 17px 이라, 갈아끼우면 결선이
# 옆 홀에 그려진다. 그림 자체는 그럴듯하게 나오므로 눈으로는 안 잡힌다.
# 배포본으로 옮기려면 좌표표를 같이 다시 떠야 한다.
#
# 아카이브 사본은 지금 정본과 바이트가 같지만(md5 ae44279586294fc5…) 과거
# 학기 자료라 정리 대상이다. 최후 대체물로만 남긴다.
TEMPLATE_CANDIDATES = (
    '.claude/assets/Breadboard.jpg',
    'from_the_past/정리/강의노트/Breadboard.jpg',
    'from_the_past/정리/아카이브/강의노트/Breadboard.jpg',
)

# 좌표표가 묶여 있는 판본의 크기.
TEMPLATE_SIZE = (998, 1345)


def _default_template():
    """정본 템플릿 경로. 저장소 루트를 먼저 보고, 없으면 cwd 도 본다."""
    tried = []
    for rel in TEMPLATE_CANDIDATES:
        for base in (REPO_ROOT, os.getcwd()):
            path = os.path.join(base, rel)
            if path in tried:
                continue
            tried.append(path)
            if os.path.exists(path):
                return path
    raise FileNotFoundError(
        '브레드보드 템플릿을 찾지 못했습니다. 찾아본 곳:\n  ' + '\n  '.join(tried))


# ---------------------------------------------------------------------------
# 물리 좌표계 — `.claude/assets/Breadboard.jpg` 를 직접 측정한 값이다.
#
# 이전 판은 `r_y = 243 + (r-1)*17.15`, 좌측 GND 레일 x=163 처럼 **눈대중 값**을
# 썼다. 그림은 그럴듯했지만 배선 끝점이 홀 안에 들어가지 않았다 — 1행이 29px,
# 우측 f~j 열이 한 칸(16.5px) 통째로 어긋나 있었다. 홀을 세어가며 손으로 따라
# 그리라고 만든 그림에서 이건 치명적이다.
#
# 아래 값은 템플릿의 어두운 픽셀 군집 중심을 떠서 얻었다. 다시 뜨려면
# `tools/measure_template.py` 를 보라.
ROW0 = 272.0        # 1행 홀 중심 y
ROW_PITCH = 16.345  # 행 간격
ROW_MAX = 63        # 이 보드는 63행이다 (라벨은 1·10·20…60 만 찍혀 있다)

# 전원 레일은 5홀씩 묶여 있고 그 사이가 비어 있다. **그 빈 행에 배선을 끝내면
# 갈 데가 없다.** 위아래 끝(1·2·62·63)과 6행 주기의 빈 행이 여기 해당한다.
RAIL_GAP_ROWS = frozenset(
    {1, 2, 8, 14, 20, 26, 32, 38, 44, 50, 56, 62, 63})  # 실측값. 풀어 쓴다 —
# 검사 코드가 소스를 ast 로 읽어 이 목록을 그대로 가져다 쓴다

# 배선 색은 **넷뿐이다.** 이전 판은 한 장에 16색을 썼는데 그중 (0,110,170) 과
# (0,120,180), (200,0,0) 과 (220,20,20) 처럼 눈으로 구분되지 않는 쌍이 여럿이라
# 색이 정보를 나르지 않으면서 눈만 어지럽혔다. 손으로 그리는 사람 손에 있는
# 펜도 네 자루다.
WIRE = {
    'vcc': (200, 30, 30, 255),    # 빨강 — +5V
    'gnd': (30, 60, 200, 255),    # 파랑 — 0V(GND)
    'sig': (25, 25, 25, 255),     # 검정 — 입력·출력 신호
    'mid': (20, 130, 60, 255),    # 초록 — 칩과 칩 사이 중간 노드
}
KIND_KR = {'vcc': '+5V', 'gnd': '0V', 'sig': '신호', 'mid': '중간'}

# 계측기 리드는 **배선이 아니다.** 점퍼선으로 꽂는 게 아니라 프로브 팁과 집게로
# 문다. 그래서 위 네 색에 끼워 넣지 않고 회색 점선으로 따로 그리고, 순서표도
# '결선' 이 아니라 '계측' 표에 따로 쌓는다
PROBE = (105, 105, 110, 255)

# 전원 잭 세 개의 중심 x (템플릿 상단). y 는 원 아래끝 근처.
JACKS = {'red': 439, 'yellow': 603, 'gray': 766}
JACK_BOTTOM = 160


class BreadboardRenderer:
    def __init__(self, template_path=None):
        if template_path is None:
            template_path = _default_template()
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"Breadboard template not found: {template_path}")

        self.base_im = Image.open(template_path).convert('RGBA')
        # 좌표표가 이 크기에 묶여 있다. 다른 판본이 들어오면 여기서 걸린다 —
        # 갈아끼운 그림은 결과가 그럴듯해서 눈으로는 안 잡히기 때문이다.
        if self.base_im.size != TEMPLATE_SIZE:
            raise ValueError(
                f'템플릿 크기가 {TEMPLATE_SIZE[0]}x{TEMPLATE_SIZE[1]} 가 아닙니다: '
                f'{self.base_im.size} ({template_path}).\n'
                'cols·r_y() 좌표는 정본 한 장에 맞춰져 있습니다. '
                '다른 판본을 쓰려면 좌표표를 다시 떠야 합니다.')
        self.im = self.base_im.copy()
        self.overlay = Image.new('RGBA', self.im.size, (0, 0, 0, 0))
        self.draw = ImageDraw.Draw(self.overlay)
        # 이미 그린 레일 브리지. 칩마다 connect_unused_inputs 를 부르면 같은
        # 레일쌍을 여러 번 잇게 되므로 한 번만 그린다
        self._bridged = set()
        # 어느 레일 스트립에 무엇이 닿았는지. 레일쌍 넷은 서로 **별개
        # 스트립**이라, +5V 를 한 레일에 넣고 칩 14번 핀을 다른 레일에 물리면
        # 그림은 멀쩡한데 전원이 안 간다. verify() 가 이걸로 잡는다
        self._touched = {'vcc': set(), 'gnd': set()}
        self._rail_uf = {}
        # 결선 순서표. 손으로 그리는 사람은 그림 전체를 한 번에 볼 필요 없이
        # 이 표를 위에서 아래로 지워가며 한 줄씩 그린다
        self.steps = []
        # 번호 매기기는 e1 계열(손스케치용 원도)만 켠다. e2 빌더들은 아직
        # 옛 API(draw_wire) 를 쓰므로 순서표가 반쪽이 된다 — 반쪽 표는 없는
        # 것보다 나쁘다
        self.numbered = False
        # 보드 밖으로 뺀 규칙 문구. 배선이 아니라 배선의 *이유* 라서 손으로
        # 옮겨 그릴 대상이 아니다 — 보드 위에 두면 그릴 홀만 가린다
        self.notes = []
        # 계측기·신호원 접점. 결선표와 섞지 않는다
        self.probes = []
        self.title = ""
        self.subtitle = ""

        self.font_title = ImageFont.truetype('/System/Library/Fonts/AppleSDGothicNeo.ttc', 21)
        self.font_subtitle = ImageFont.truetype('/System/Library/Fonts/AppleSDGothicNeo.ttc', 14)
        self.font_kr_bold = ImageFont.truetype('/System/Library/Fonts/AppleSDGothicNeo.ttc', 12)
        self.font_kr_sm = ImageFont.truetype('/System/Library/Fonts/AppleSDGothicNeo.ttc', 11)
        self.font_en_bold = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 12)
        self.font_en_sm = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 10)
        self.font_chip = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 11)
        self.font_num = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 9)
        self.font_step = ImageFont.truetype('/System/Library/Fonts/AppleSDGothicNeo.ttc', 11)

        self.cols = {
            'left': {
                'gnd': 174, 'vcc': 190,
                'a': 239, 'b': 256, 'c': 272, 'd': 288, 'e': 305,
                'chip_x1': 310, 'chip_x2': 349,
                'f': 354, 'g': 370, 'h': 386, 'i': 403, 'j': 419,
                'mid_gnd': 468, 'mid_vcc': 484,
            },
            'right': {
                'mid_gnd': 542, 'mid_vcc': 558,
                'a': 607, 'b': 623, 'c': 640, 'd': 656, 'e': 672,
                'chip_x1': 677, 'chip_x2': 716,
                'f': 721, 'g': 738, 'h': 754, 'i': 770, 'j': 786,
                'gnd': 836, 'vcc': 852,
            },
        }
        self._addr_map = self._build_addr_map()

    # ---------------- 좌표 ----------------

    def r_y(self, r):
        return int(round(ROW0 + (r - 1) * ROW_PITCH))

    @staticmethod
    def is_rail_row(r):
        return 1 <= r <= ROW_MAX and r not in RAIL_GAP_ROWS

    def snap_rail_row(self, r):
        """레일에 홀이 실제로 있는 가장 가까운 행."""
        if self.is_rail_row(r):
            return r
        for d in range(1, 8):
            for cand in (r - d, r + d):
                if self.is_rail_row(cand):
                    return cand
        raise ValueError(f'레일 홀이 있는 행을 못 찾았다: r={r}')

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

    def touch_rail(self, kind, x):
        """이 배선이 어느 전원 레일에 닿았는지 적어 둔다."""
        if kind in self._touched and x in self._rail_xs():
            self._touched[kind].add(x)

    def _build_addr_map(self):
        """x 좌표 -> 사람이 읽는 이름. 결선 순서표의 주소를 자동으로 만든다."""
        out = {}
        names = {'gnd': 'GND레일', 'vcc': 'VCC레일',
                 'mid_gnd': '중앙GND레일', 'mid_vcc': '중앙VCC레일'}
        for block, blabel in (('left', '좌'), ('right', '우')):
            for key, x in self.cols[block].items():
                if key.startswith('chip'):
                    continue
                out[x] = f'{blabel} {names.get(key, key)}'
        return out

    def addr(self, x, y):
        """(x, y) 를 '좌 e7' 처럼 읽히는 주소로. 표에 그대로 들어간다."""
        if y < 240:
            return '전원잭'
        if x < 149:
            return '보드밖(입력)'
        if x > 880:
            return '보드밖'
        r = int(round((y - ROW0) / ROW_PITCH)) + 1
        best = min(self._addr_map, key=lambda k: abs(k - x))
        if abs(best - x) > 9:
            # 홀이 아니라 배선 통로다. 분기점(T 접속)일 때만 여기 온다
            return '분기점'
        name = self._addr_map[best]
        return f'{name}{r}행' if '레일' in name else f'{name}{r}'

    # ---------------- 머리글 ----------------

    def set_header(self, title, subtitle):
        """제목은 **잭 아래 빈 띠(y 165~238)** 에 넣는다.

        이전 판은 `[370,30,850,160]` 을 흰색으로 덮고 그 자리에 제목을 썼는데,
        하필 그 사각형 안에 **전원 잭 세 개가 들어 있었다.** 과거 예비보고서의
        결선도는 예외 없이 그 잭에서 보드까지 전원선을 그린다 — 실험대 전원이
        그 잭이기 때문이다. 덮어버리면 "5V 를 어디서 따오지"에서 막힌다.
        """
        self.title, self.subtitle = title, subtitle
        self.draw.text((28, 170), title, fill=(20, 40, 90, 255), font=self.font_title)
        self.draw.text((30, 200), subtitle, fill=(80, 90, 100, 255), font=self.font_subtitle)
        self.draw.text((30, 220), "※ 이 그림을 손으로 따라 그린 뒤 학번/이름/날짜를 자필로 적어 제출한다",
                       fill=(180, 50, 50, 255), font=self.font_kr_sm)

    def connect_jacks(self, block='left'):
        """전원 잭 -> 보드 레일. 과거 결선도가 모두 그리던 선이다."""
        c = self.cols[block]
        r_v, r_g = self.snap_rail_row(3), self.snap_rail_row(4)
        self.step_wire([(JACKS['red'], JACK_BOTTOM), (JACKS['red'], 250),
                        (c['vcc'], 250), (c['vcc'], self.r_y(r_v))],
                       'vcc', '전원장치 +5V 잭', marker_at=(JACKS['red'] + 46, 118))
        self.step_wire([(JACKS['gray'], JACK_BOTTOM), (JACKS['gray'], 258),
                        (c['gnd'], 258), (c['gnd'], self.r_y(r_g))],
                       'gnd', '전원장치 0V 잭', marker_at=(JACKS['gray'] + 46, 118))
        self.note('잭 색과 전압 표기는 실험대 전원장치에서 직접 확인할 것 '
                  '(교안에 잭 색 규정이 없다). 가운데 노란 잭은 쓰지 않는다.')

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

    def draw_wire(self, points, color, width=3):
        """번호 없는 생짜 배선. e2 빌더들이 아직 이걸 쓴다."""
        self.draw.line(points, fill=color, width=width, joint='curve')
        for p in (points[0], points[-1]):
            self.draw.ellipse([p[0]-3, p[1]-3, p[0]+3, p[1]+3], fill=color)

    def _dashed(self, points, color, width=2, dash=7, gap=5):
        for (x0, y0), (x1, y1) in zip(points, points[1:]):
            span = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
            if span == 0:
                continue
            ux, uy, t = (x1 - x0) / span, (y1 - y0) / span, 0.0
            while t < span:
                e = min(t + dash, span)
                self.draw.line([(x0 + ux * t, y0 + uy * t), (x0 + ux * e, y0 + uy * e)],
                               fill=color, width=width)
                t = e + gap

    def instrument(self, x, row, label, desc, block='left', lane_row=None):
        """계측기·신호원 접점. **배선이 아니다** — 점퍼로 꽂는 게 아니라
        프로브 팁이나 집게로 문다. 회색 점선으로 그리고 계측표에 따로 쌓는다.

        보드 왼쪽 여백으로 뺀다. `lane_row` 를 주면 여백 안(x=140)에서 꺾어
        그 행으로 옮긴다 — 접점 두 개가 이웃한 행이면 꼬리표가 겹치기 때문이다.
        """
        y = self.r_y(row)
        lane_y = self.r_y(lane_row) if lane_row else y
        pts = [(x, y), (140, y)] + ([(140, lane_y)] if lane_row else []) + [(100, lane_y)]
        self._dashed(pts, PROBE)
        self.draw.ellipse([x - 5, y - 5, x + 5, y + 5], outline=PROBE, width=2)
        n = len(self.probes) + 1
        self.draw_badge(12, lane_y - 8, f'{n}. {label}', (248, 248, 250, 240), PROBE,
                        font=self.font_kr_sm, pad=2)
        self.probes.append({'n': n, 'label': label, 'at': self.addr(x, y), 'desc': desc})

    def instrument_note(self, label, at, desc):
        """그림에 그릴 자리가 없는 접점(회로에 꽂기 전 저항 측정 등)."""
        self.probes.append({'n': len(self.probes) + 1, 'label': label,
                            'at': at, 'desc': desc})

    def _marker(self, x, y, n, color):
        """배선 번호. 결선 순서표의 몇 번인지 가리킨다."""
        self.draw.ellipse([x-8, y-8, x+8, y+8], fill=(255, 255, 255, 245), outline=color, width=2)
        t = str(n)
        bbox = self.draw.textbbox((0, 0), t, font=self.font_num)
        self.draw.text((x - (bbox[2]-bbox[0])/2 - bbox[0], y - (bbox[3]-bbox[1])/2 - bbox[1]),
                       t, fill=color, font=self.font_num)

    def enable_steps(self):
        self.numbered = True

    def step_wire(self, points, kind, desc, width=3, marker_at=None, count=1,
                  frm=None, to=None):
        """배선 하나 + 결선 순서표 한 줄.

        `desc` 는 짧은 뜻풀이만 준다 — 어디서 어디로 가는지는 좌표에서
        자동으로 뽑는다 ('좌 b7 -> 좌 GND레일7행').
        """
        color = WIRE[kind]
        self.draw.line(points, fill=color, width=width, joint='curve')
        for p in (points[0], points[-1]):
            self.draw.ellipse([p[0]-3, p[1]-3, p[0]+3, p[1]+3], fill=color)
        if not self.numbered:
            return None

        n = len(self.steps) + 1
        if marker_at is None:
            (x0, y0), (x1, y1) = points[0], points[1] if len(points) > 1 else points[0]
            marker_at = ((x0 + x1) // 2, (y0 + y1) // 2)
        self._marker(marker_at[0], marker_at[1], n, color)

        for p in (points[0], points[-1]):
            self.touch_rail(kind, p[0])
        frm = frm or self.addr(*points[0])
        to = to or self.addr(*points[-1])
        self.steps.append({'n': n, 'kind': kind, 'frm': frm, 'to': to,
                           'desc': desc, 'count': count})
        return n

    def step_note(self, kind, frm, to, desc, count=1, marker_at=None):
        """그림에 이미 그려진 것을 표에 한 줄로 묶는다.

        `marker_at` 을 주면 보드 위에도 번호 원을 찍는다. **부품을 꽂는
        단계에는 반드시 준다** — 안 주면 표에는 번호가 있는데 그림에는 없어서,
        따라 그리는 사람이 그 차례에서 그림을 뒤지다 막힌다.
        """
        if not self.numbered:
            return None
        n = len(self.steps) + 1
        if marker_at is not None:
            self._marker(marker_at[0], marker_at[1], n, WIRE[kind])
        self.steps.append({'n': n, 'kind': kind, 'frm': frm, 'to': to,
                           'desc': desc, 'count': count})
        return n

    def draw_resistor(self, x, y1, y2, label="330Ω", bands=None):
        wire_col = (100, 100, 100, 255)
        body_col = (225, 195, 145, 255)
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
        ymid = (y_anode + y_cathode) // 2
        self.draw.line([(x, y_anode), (x, ymid - 8)], fill=(130, 130, 130, 255), width=2)
        self.draw.line([(x, ymid + 8), (x, y_cathode)], fill=(130, 130, 130, 255), width=2)
        self.draw.ellipse([x - 8, ymid - 8, x + 8, ymid + 8], fill=(*color_rgb, 240), outline=(255, 255, 255, 255), width=2)
        if label:
            self.draw_badge(x + 12, ymid - 7, label, (255, 255, 255, 235), color_rgb, font=self.font_kr_sm, pad=2)

    def led_chain(self, x, top_row, tag, desc, block='left', color_rgb=(220, 20, 20),
                  marker_dx=-21):
        """LED + 330Ω + GND 한 벌.

        보드 위에는 **짧은 꼬리표만** 붙인다 (L1, X, Z…). 'L2 최종 LED
        (Y=A·B·C)' 같은 긴 문구는 결선 순서표로 내려보낸다 — 손으로 옮겨
        그릴 것이 아니면서 정작 그릴 홀을 가리기 때문이다.
        """
        c = self.cols[block]
        y_a, y_k = self.r_y(top_row), self.r_y(top_row + 1)
        self.draw_led(x, y_a, y_k, color_rgb, tag)
        self.draw_resistor(x, y_k, self.r_y(top_row + 3), label="330Ω")
        self.step_note('sig', self.addr(x, y_a), self.addr(x, self.r_y(top_row + 3)),
                       f'{tag}: LED + 330Ω 직렬 · {desc}',
                       marker_at=(x + marker_dx, (y_a + y_k) // 2))
        r_gnd = self.snap_rail_row(top_row + 3)
        x_gnd = self.nearest_gnd_rail(x, block)
        self.step_wire([(x, self.r_y(top_row + 3)), (x_gnd, self.r_y(r_gnd))],
                       'gnd', f'{tag} 저항 아래 -> GND',
                       width=2, marker_at=(x - 22, self.r_y(top_row + 3) + 2))

    # ---------------- 칩 ----------------

    def _vtext(self, xy, text, fill, font):
        """세로쓰기. 과거 결선도가 칩 이름을 이렇게 적었다 — 몸통 안에 넣으면
        핀 번호를 d·g 열 홀 위에 얹지 않아도 된다."""
        bbox = font.getbbox(text)
        w, h = bbox[2] - bbox[0] + 4, bbox[3] - bbox[1] + 4
        tmp = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(tmp).text((2 - bbox[0], 2 - bbox[1]), text, fill=fill, font=font)
        rot = tmp.rotate(-90, expand=True)
        self.overlay.alpha_composite(rot, (int(xy[0] - rot.width / 2), int(xy[1] - rot.height / 2)))

    def draw_chip(self, name, start_row, block='left'):
        c = self.cols[block]
        x1, x2 = c['chip_x1'], c['chip_x2']
        y_top = self.r_y(start_row) - 8
        y_bot = self.r_y(start_row + 6) + 8

        self.draw.rectangle([x1, y_top, x2, y_bot], fill=(30, 33, 36, 255), outline=(130, 140, 150, 255), width=2)
        notch_w = (x2 - x1) // 3
        self.draw.arc([x1 + notch_w, y_top - 6, x2 - notch_w, y_top + 6], 0, 180, fill=(200, 200, 200, 255), width=2)
        self._vtext(((x1 + x2) / 2, (y_top + y_bot) / 2), name, (255, 255, 255, 255), self.font_chip)

        # 핀 번호는 **몸통 안쪽**에 흰 글씨로. 이전 판은 e-15 / f+6 에 찍어서
        # d 열과 g 열 홀을 가렸다 — 정작 배선을 꽂는 자리다
        for i in range(7):
            y = self.r_y(start_row + i)
            self.draw.line([(c['e'], y), (x1, y)], fill=(170, 170, 170, 255), width=3)
            self.draw.line([(x2, y), (c['f'], y)], fill=(170, 170, 170, 255), width=3)
            self.draw.text((x1 + 3, y - 6), str(i + 1), fill=(215, 215, 215, 255), font=self.font_num)
            rt = str(14 - i)
            w = self.draw.textbbox((0, 0), rt, font=self.font_num)[2]
            self.draw.text((x2 - 3 - w, y - 6), rt, fill=(215, 215, 215, 255), font=self.font_num)

    def bridge_rails(self, x_a, x_b, row, kind='gnd', label=None):
        """물리적으로 분리된 전원 레일 모듈 둘을 잇는 점퍼.

        이 템플릿의 레일쌍(좌 174/190, 중앙좌 468/484, 중앙우 542/558,
        우 836/852)은 각각 **별개 스트립**이다. 칩 7번 핀을 좌측 GND 레일에
        내리고 미사용 입력을 중앙 GND 레일에 내리면 두 레일이 이어져 있지
        않아 미사용 입력이 뜬다. 그 점퍼를 명시적으로 그린다.
        """
        key = (kind, min(x_a, x_b), max(x_a, x_b))
        if key in self._bridged:
            return
        self._bridged.add(key)
        row = self.snap_rail_row(row)
        self._uf_union(x_a, x_b)
        y = self.r_y(row)
        self.step_wire([(x_a, y), (x_b, y)], kind,
                       '레일 브리지',
                       marker_at=((x_a + x_b) // 2, y - 12))

    def connect_power(self, start_row, block='left'):
        """pin 14 -> +5V, pin 7 -> GND.

        어느 레일로 가는지는 블록마다 다르다. 좌측 보드는 f~j 쪽(pin 8~14)이
        중앙 레일에, a~e 쪽(pin 1~7)이 바깥 왼쪽 레일에 붙는다. 우측 보드는
        좌우가 뒤집힌다 — 이전 판은 좌측 기준 배선을 우측에도 그대로 써서
        복합회로 빌더가 전원 배선을 손으로 다시 썼다.
        """
        c = self.cols[block]
        x_vcc = c['mid_vcc'] if block == 'left' else c['vcc']
        x_gnd = c['gnd'] if block == 'left' else c['mid_gnd']
        r14 = self.snap_rail_row(start_row)
        self.step_wire([(c['f'], self.r_y(start_row)), (x_vcc, self.r_y(r14))],
                       'vcc', 'pin 14 -> +5V 레일',
                       marker_at=((c['f'] + x_vcc) // 2, self.r_y(start_row) - 11))
        r7 = self.snap_rail_row(start_row + 6)
        self.step_wire([(c['e'], self.r_y(start_row + 6)), (x_gnd, self.r_y(r7))],
                       'gnd', 'pin 7 -> GND 레일',
                       marker_at=((c['e'] + x_gnd) // 2, self.r_y(start_row + 6) - 11))

    def nearest_gnd_rail(self, x, block='left'):
        """그 자리에서 제일 가까운 GND 레일. 좌우 블록은 a~e 쪽과 f~j 쪽에
        붙는 레일이 서로 뒤집혀 있어서 블록 이름만으로는 못 고른다."""
        c = self.cols[block]
        return min((c['gnd'], c['mid_gnd']), key=lambda xr: abs(xr - x))

    def nearest_vcc_rail(self, x, block='left'):
        c = self.cols[block]
        return min((c['vcc'], c['mid_vcc']), key=lambda xr: abs(xr - x))

    def connect_unused_inputs(self, pins, start_row, block='left', bridge_row=None,
                              chip='', rail='gnd'):
        """미사용 입력핀을 전원 레일로. 여러 가닥이지만 표에는 **한 줄**로 묶는다.

        `rail='vcc'` 면 GND 가 아니라 +5V 로 올린다. 실험02 교안 p8 도면이
        미사용 입력 일부를 VCC 로 묶으라고 지정한다 — CMOS 입력은 뜨면 안 될
        뿐이지 어느 쪽으로 묶든 상관없고, 도면을 그대로 따르는 편이 대조하기 쉽다.
        """
        c = self.cols[block]
        for p in pins:
            if 1 <= p <= 7:
                row, x_pin = start_row + (p - 1), c['d']
            elif 8 <= p <= 14:
                row, x_pin = start_row + (14 - p), c['g']
            else:
                continue
            pick = self.nearest_vcc_rail if rail == 'vcc' else self.nearest_gnd_rail
            x_rail, r_rail = pick(x_pin, block), self.snap_rail_row(row)
            col = WIRE[rail]
            self.draw.line([(x_pin, self.r_y(row)), (x_rail, self.r_y(r_rail))], fill=col, width=2)
            self.draw.ellipse([x_pin-3, self.r_y(row)-3, x_pin+3, self.r_y(row)+3], fill=col)
            self.draw.ellipse([x_rail-3, self.r_y(r_rail)-3, x_rail+3, self.r_y(r_rail)+3], fill=col)
            self.touch_rail(rail, x_rail)

        pin_str = ", ".join(str(p) for p in pins)
        self.step_note(rail, f'{chip} pin {pin_str}',
                       '가까운 +5V 레일' if rail == 'vcc' else '가까운 GND 레일',
                       '미사용 입력 풀업' if rail == 'vcc' else '미사용 입력 접지',
                       count=len(pins))

        if rail == 'gnd' and any(8 <= p <= 14 for p in pins):
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
        pin_str = ", ".join(str(p) for p in pins)
        self.note(f'{chip} 미사용 출력 pin {pin_str} 은 **아무 데도 연결하지 않는다** '
                  f'— 개방(NC). GND 로 내리거나 출력끼리 묶으면 칩이 상한다.')

    # ---------------- 내보내기 ----------------

    def _wrap(self, text, font, max_w):
        out, line = [], ''
        for ch in text:
            if self.draw.textlength(line + ch, font=font) > max_w and line:
                out.append(line)
                line = ch
            else:
                line += ch
        if line:
            out.append(line)
        return out

    def _draw_footer(self, im, y0):
        """보드 아래 흰 띠에 **범례 + 결선 순서표**.

        보드 위에서 걷어낸 규칙 문구가 여기로 내려온다. 손으로 그리는 사람은
        그림 전체를 한 번에 볼 필요 없이 이 표를 위에서 아래로 지워가며
        한 줄씩 그린다 — 30가닥을 동시에 보는 문제가 사라진다.
        """
        d = ImageDraw.Draw(im)
        x_pad = 28
        d.line([(x_pad, y0), (998 - x_pad, y0)], fill=(190, 195, 200, 255), width=1)
        y = y0 + 14

        # 색 규칙 범례는 넷으로 고정된 그림에만. e2 빌더들은 아직 옛 팔레트를
        # 쓰므로 범례를 붙이면 거짓말이 된다
        if self.numbered:
            d.text((x_pad, y), "배선 색 규칙", fill=(20, 40, 90, 255), font=self.font_kr_bold)
            x = x_pad + 84
            for kind in ('vcc', 'gnd', 'sig', 'mid'):
                d.line([(x, y + 7), (x + 24, y + 7)], fill=WIRE[kind], width=4)
                d.text((x + 30, y), KIND_KR[kind], fill=(60, 60, 60, 255), font=self.font_step)
                x += 96
            if self.probes:
                for k in range(0, 24, 12):
                    d.line([(x + k, y + 7), (x + k + 7, y + 7)], fill=PROBE, width=3)
                d.text((x + 30, y), '계측기(점선 — 꽂는 게 아니라 문다)',
                       fill=(60, 60, 60, 255), font=self.font_step)
            y += 24

        for n in self.notes:
            for ln in self._wrap('· ' + n.replace('**', ''), self.font_step, 998 - 2 * x_pad):
                d.text((x_pad, y), ln, fill=(90, 70, 70, 255), font=self.font_step)
                y += 15
        y += 8

        if not (self.numbered and self.steps):
            return self._draw_probe_table(d, y, x_pad) if self.probes else y

        d.line([(x_pad, y), (998 - x_pad, y)], fill=(225, 228, 232, 255), width=1)
        y += 12
        d.text((x_pad, y), "결선 순서 — 위에서 아래로 한 줄씩 그리고 ☐ 를 채운다",
               fill=(20, 40, 90, 255), font=self.font_kr_bold)
        y += 22

        col_w = (998 - 2 * x_pad) // 2
        text_w = col_w - 58
        blocks = []
        for st in self.steps:
            mult = f" x{st['count']}" if st['count'] > 1 else ""
            blocks.append((st, self._wrap(f"{st['frm']} → {st['to']}{mult} · {st['desc']}",
                                          self.font_step, text_w)[:2]))

        # 두 단으로 나눈다. 줄 수 기준으로 갈라야 단 높이가 맞는다
        total = sum(len(b[1]) for b in blocks)
        half, acc, cut = (total + 1) // 2, 0, len(blocks)
        for i, b in enumerate(blocks):
            if acc >= half:
                cut = i
                break
            acc += len(b[1])

        bottom = y
        for ci, chunk in enumerate((blocks[:cut], blocks[cut:])):
            cx, cy = x_pad + ci * col_w, y
            for st, lines in chunk:
                d.rectangle([cx, cy + 2, cx + 11, cy + 13], outline=(120, 125, 130, 255), width=1)
                self._marker_on(d, cx + 28, cy + 8, st['n'], WIRE[st['kind']])
                for k, ln in enumerate(lines):
                    d.text((cx + 42, cy + k * 14), ln, fill=(45, 45, 45, 255), font=self.font_step)
                cy += max(18, len(lines) * 14 + 4)
            bottom = max(bottom, cy)
        y = bottom + 14
        return self._draw_probe_table(d, y, x_pad) if self.probes else y + 10

    def _draw_probe_table(self, d, y, x_pad):
        """계측표. 결선표와 **따로** 쌓는다 — 프로브는 꽂는 게 아니라 무는 것이라
        결선 순서에 섞으면 조원이 점퍼선을 찾게 된다."""
        d.line([(x_pad, y), (998 - x_pad, y)], fill=(225, 228, 232, 255), width=1)
        y += 12
        d.text((x_pad, y), "계측 · 신호원 — 어디에 무는가 (배선이 아니다)",
               fill=(20, 40, 90, 255), font=self.font_kr_bold)
        y += 22
        for pr in self.probes:
            d.rectangle([x_pad, y + 2, x_pad + 11, y + 13], outline=(120, 125, 130, 255), width=1)
            d.text((x_pad + 20, y), f"{pr['n']}.", fill=PROBE, font=self.font_step)
            lines = self._wrap(f"{pr['label']} → {pr['at']} · {pr['desc']}",
                               self.font_step, 998 - 2 * x_pad - 60)[:2]
            for k, ln in enumerate(lines):
                d.text((x_pad + 42, y + k * 14), ln, fill=(45, 45, 45, 255), font=self.font_step)
            y += max(18, len(lines) * 14 + 4)
        return y + 10

    def _marker_on(self, d, x, y, n, color):
        d.ellipse([x-8, y-8, x+8, y+8], fill=(255, 255, 255, 245), outline=color, width=2)
        t = str(n)
        bbox = d.textbbox((0, 0), t, font=self.font_num)
        d.text((x - (bbox[2]-bbox[0])/2 - bbox[0], y - (bbox[3]-bbox[1])/2 - bbox[1]),
               t, fill=color, font=self.font_num)

    def verify(self):
        """배선 끝점이 실제 홀 위에 있는지 검사한다.

        좌표표가 어긋나도 그림은 그럴듯하게 나오기 때문에 눈으로는 안 잡힌다.
        템플릿 크기 검사(TEMPLATE_SIZE)는 판본 교체만 잡지 좌표 자체의
        회귀는 못 잡는다 — 이전 판이 정확히 그 틈으로 빠져나갔다.
        """
        bad = []
        for s in self.steps:
            for a in (s['frm'], s['to']):
                if '레일' in a:
                    try:
                        r = int(a.split('레일')[1].replace('행', ''))
                    except ValueError:
                        continue
                    if not self.is_rail_row(r):
                        bad.append(f"{a} — 그 행의 레일에는 홀이 없다")
        if bad:
            raise AssertionError('결선 끝점이 홀 밖이다:\n  ' + '\n  '.join(bad))

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

    def export(self, output_path, max_row=35):
        self.verify()
        final_im = Image.alpha_composite(self.im, self.overlay)
        board_h = self.r_y(max_row) + 20
        board = final_im.crop((0, 0, 998, board_h)).convert('RGB')

        canvas = Image.new('RGB', (998, board_h + 1400), (255, 255, 255))
        canvas.paste(board, (0, 0))
        used = self._draw_footer(canvas, board_h)
        out = canvas.crop((0, 0, 998, min(used, canvas.height)))
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        out.save(output_path)
        print(f"[SUCCESS] Exported: {output_path} "
              f"({out.size[0]}x{out.size[1]}, 결선 {len(self.steps)}단계)")


def _tag(bb, x, y, text, col=(60, 60, 60, 255)):
    """보드 위 꼬리표. **두 글자 안팎으로만** 쓴다 — 뜻은 결선 순서표에 있다."""
    bb.draw_badge(x, y, text, (255, 255, 255, 235), col, font=bb.font_kr_sm, pad=2)


def _input_jumper(bb, c, row, name, target, rail_row=None, marker=(130, 0)):
    """입력 한 줄: **좌 GND 레일 홀 → 같은 행 b열**. GND(=0) 자리를 그린 것이다.

    이전 판은 보드 밖 x=95 허공에서 선을 끌어왔다. 브레드보드 그림에서 홀이
    아닌 데서 나오는 선은 꽂을 데가 없다 — 따라 그리는 사람이 왼쪽 끝을 어디에
    꽂아야 하는지 알 수 없었다. netlist 공통 규칙(입력은 +5V 나 GND 에 직접
    물린다)대로 레일 홀에서 출발시키고, 1 을 줄 때는 레일 쪽 끝만 빨간 VCC
    레일로 옮겨 꽂는다고 범례에 적는다.

    레일에 홀이 없는 행(8·14·20행 따위)은 `snap_rail_row()` 로 가까운 홀 행에서
    출발해 한 행 비스듬히 들어간다 — `connect_unused_inputs()` 와 같은 관례다.
    **`rail_row` 는 그 자동 선택이 이웃 입력과 같은 홀을 고를 때 준다.** 7행·8행에
    나란히 들어가는 A·B 는 8행이 7행 홀로 스냅돼 A 와 한 홀을 두고 다투므로
    B 에 9 를 넘긴다. 한 홀에 점퍼 둘은 못 꽂는다.

    번호 원은 기본으로 **레일 왼쪽 x=130, 행 높이 그대로** 둔다. 선이 레일에서
    시작하니 그 자리는 비어 있고, 선과 같은 높이라 어느 줄 번호인지 바로 읽힌다.
    단 템플릿에 행 번호가 인쇄된 10·20·30행은 거기가 막혀 있으니 레일과 a열
    사이 여백 `(215, ±13)` 으로 피한다. 꼬리표에는 꽂을 자리(b10)를 그대로
    적는다 — 왼쪽 눈금이 10·20·30 뿐이라 이름만 있으면 홀을 세어야 한다.
    """
    r_rail = rail_row if rail_row is not None else bb.snap_rail_row(row)
    bb.step_wire([(c['gnd'], bb.r_y(r_rail)), (c['b'], bb.r_y(row))], 'sig',
                 f'입력 {name} -> {target} · 1 이면 레일 쪽 끝을 +5V 레일로 옮긴다',
                 marker_at=(marker[0], bb.r_y(row) + marker[1]))
    _tag(bb, 12, bb.r_y(row) - 8, f"입력 {name} → b{row}")


def build_e1_and(output_path, template_path=None):
    """실험 1-1 · 3입력 AND (74HC08 2단 캐스케이드). netlist C1."""
    bb = BreadboardRenderer(template_path)
    bb.enable_steps()
    bb.set_header("실험 1-1: 3-Input AND Gate 결선도",
                  "74HC08 (Quad 2-Input AND) 한 개를 2단으로 · LED 마다 330Ω 직렬")
    c = bb.cols['left']
    r = 10

    bb.draw_chip("74HC08", r)
    bb.connect_jacks()
    # 잭이 들어간 바깥 레일과 칩이 물리는 중앙 레일은 **별개 스트립**이다.
    # 이어주지 않으면 그림대로 꽂아도 전원이 안 간다
    bb.bridge_rails(c['gnd'], c['mid_gnd'], 29, kind='gnd')
    bb.bridge_rails(c['vcc'], c['mid_vcc'], 30, kind='vcc')
    bb.connect_power(r)

    # 입력 세 줄은 보드 밖에서 목표 행으로 **수평 직행**한다. 예전엔 5·6·7행으로
    # 들어와 a열을 타고 내려갔는데, A(5→10)·C(7→14)·중간단 갈래(12→19) 가 전부
    # x=c['a'] 한 줄에 겹쳐 있었다. 그려 놓고 보면 C 가 12행부터 초록 중간단
    # 선에 삼켜져, 따라 그리면 pin 3 이 pin 5 로 들어가는 다른 회로가 된다.
    # 세로 경유 자체를 없애면 겹침도 홀 가림도 한꺼번에 닫힌다
    # 입력 세 줄은 좌 GND 레일 홀에서 같은 행 b열로 들어간다. 사연은 _input_jumper
    _input_jumper(bb, c, 10, 'A', 'pin 1', marker=(215, -13))
    _input_jumper(bb, c, 11, 'B', 'pin 2', marker=(215, +13))
    _input_jumper(bb, c, 14, 'C', 'pin 5', marker=(215, +13))

    bb.step_wire([(c['c'], bb.r_y(12)), (c['c'], bb.r_y(13))], 'mid',
                 '1단 출력 A·B -> 2단 입력 (pin 3 -> pin 4)', width=4,
                 marker_at=(c['c'] - 20, bb.r_y(12) + 8))

    bb.step_wire([(c['c'], bb.r_y(12)), (c['a'], bb.r_y(12)), (c['a'], bb.r_y(19))], 'mid',
                 '중간단 확인용 갈래', width=2, marker_at=(c['a'] + 18, bb.r_y(16)))
    bb.led_chain(c['a'], 19, "L1", "중간단 A·B — 켜지는지 눈으로만 본다", color_rgb=(210, 140, 0))

    bb.step_wire([(c['c'], bb.r_y(15)), (c['c'], bb.r_y(24))], 'sig',
                 '최종 출력 pin 6 -> L2', marker_at=(c['c'] + 18, bb.r_y(20)))
    bb.led_chain(c['c'], 24, "L2", "최종 출력 Y = A·B·C — 진리표 검증 대상")

    bb.connect_unused_inputs([9, 10, 12, 13], r, bridge_row=29, chip='74HC08')
    bb.mark_unused_outputs([8, 11], r, chip='74HC08')
    bb.note('입력 A·B·C 는 GND(=0) 에 꽂힌 자리로 그렸다. 1 을 줄 때는 그 점퍼의 레일 쪽 끝만 빨간 +5V 레일로 옮겨 꽂는다. 띄워두지 않는다.')
    bb.export(output_path, max_row=31)


def build_e1_or(output_path, template_path=None):
    """실험 1-2 · 3입력 OR (74HC32). netlist C2.

    C1(AND) 과 위상이 같다 — 74HC32 는 74HC00·74HC08 과 같은 표준 DIP-14 쿼드
    2입력 배치(1,2->3 / 4,5->6)를 쓴다. **Nexperia 74HC32 Rev. 10 (2025-04-30)
    §5.2 로 확인됐다** — `1A~4A = 1,4,9,12` / `1B~4B = 2,5,10,13` /
    `1Y~4Y = 3,6,8,11` / GND 7 / VCC 14.
    """
    bb = BreadboardRenderer(template_path)
    bb.enable_steps()
    bb.set_header("실험 1-2: 3-Input OR Gate 결선도",
                  "74HC32 (Quad 2-Input OR) 한 개를 2단으로 · LED 마다 330Ω 직렬")
    c = bb.cols['left']
    r = 10

    bb.draw_chip("74HC32", r)
    bb.connect_jacks()
    # 잭이 들어간 바깥 레일과 칩이 물리는 중앙 레일은 **별개 스트립**이다.
    # 이어주지 않으면 그림대로 꽂아도 전원이 안 간다
    bb.bridge_rails(c['gnd'], c['mid_gnd'], 29, kind='gnd')
    bb.bridge_rails(c['vcc'], c['mid_vcc'], 30, kind='vcc')
    bb.connect_power(r)

    # 입력 세 줄은 보드 밖에서 목표 행으로 **수평 직행**한다. 예전엔 5·6·7행으로
    # 들어와 a열을 타고 내려갔는데, A(5→10)·C(7→14)·중간단 갈래(12→19) 가 전부
    # x=c['a'] 한 줄에 겹쳐 있었다. 그려 놓고 보면 C 가 12행부터 초록 중간단
    # 선에 삼켜져, 따라 그리면 pin 3 이 pin 5 로 들어가는 다른 회로가 된다.
    # 세로 경유 자체를 없애면 겹침도 홀 가림도 한꺼번에 닫힌다
    # 입력 세 줄은 좌 GND 레일 홀에서 같은 행 b열로 들어간다. 사연은 _input_jumper
    _input_jumper(bb, c, 10, 'A', 'pin 1', marker=(215, -13))
    _input_jumper(bb, c, 11, 'B', 'pin 2', marker=(215, +13))
    _input_jumper(bb, c, 14, 'C', 'pin 5', marker=(215, +13))

    bb.step_wire([(c['c'], bb.r_y(12)), (c['c'], bb.r_y(13))], 'mid',
                 '1단 출력 A+B -> 2단 입력 (pin 3 -> pin 4)', width=4,
                 marker_at=(c['c'] - 20, bb.r_y(12) + 8))

    bb.step_wire([(c['c'], bb.r_y(12)), (c['a'], bb.r_y(12)), (c['a'], bb.r_y(19))], 'mid',
                 '중간단 확인용 갈래', width=2, marker_at=(c['a'] + 18, bb.r_y(16)))
    bb.led_chain(c['a'], 19, "L1", "중간단 A+B — 켜지는지 눈으로만 본다", color_rgb=(210, 140, 0))

    bb.step_wire([(c['c'], bb.r_y(15)), (c['c'], bb.r_y(24))], 'sig',
                 '최종 출력 pin 6 -> L2', marker_at=(c['c'] + 18, bb.r_y(20)))
    bb.led_chain(c['c'], 24, "L2", "최종 출력 Y = A+B+C — 진리표 검증 대상")

    bb.connect_unused_inputs([9, 10, 12, 13], r, bridge_row=29, chip='74HC32')
    bb.mark_unused_outputs([8, 11], r, chip='74HC32')
    bb.note('입력 A·B·C 는 GND(=0) 에 꽂힌 자리로 그렸다. 1 을 줄 때는 그 점퍼의 레일 쪽 끝만 빨간 +5V 레일로 옮겨 꽂는다. 띄워두지 않는다.')
    bb.export(output_path, max_row=31)


def build_e1_nand(output_path, template_path=None):
    """실험 2-1 · 3입력 NAND (74HC08 앞단 + 74HC00 뒷단). netlist C3."""
    bb = BreadboardRenderer(template_path)
    bb.enable_steps()
    bb.set_header("실험 2-1: 3-Input NAND Gate 결선도",
                  "74HC08 (AND 앞단) + 74HC00 (NAND 뒷단) · LED 마다 330Ω 직렬")
    c = bb.cols['left']
    r_and, r_nand = 7, 18

    bb.draw_chip("74HC08", r_and)
    bb.draw_chip("74HC00", r_nand)
    bb.connect_jacks()
    bb.bridge_rails(c['gnd'], c['mid_gnd'], 29, kind='gnd')
    bb.bridge_rails(c['vcc'], c['mid_vcc'], 30, kind='vcc')
    bb.connect_power(r_and)
    bb.connect_power(r_nand)

    # 8행 레일에는 홀이 없다. 자동 스냅은 7행을 고르는데 그건 A 의 홀이다 — B 는 9행
    _input_jumper(bb, c, 7, 'A', '74HC08 pin 1')
    _input_jumper(bb, c, 8, 'B', '74HC08 pin 2', rail_row=9)

    bb.step_wire([(c['c'], bb.r_y(9)), (c['c'], bb.r_y(18))], 'mid',
                 'A·B -> 74HC00 pin 1 (칩 사이 연결)', marker_at=(c['c'] + 18, bb.r_y(13)))

    bb.step_wire([(c['b'], bb.r_y(9)), (c['b'], bb.r_y(13))], 'mid',
                 '중간단 확인용 갈래', width=2, marker_at=(c['b'] - 20, bb.r_y(11)))
    bb.led_chain(c['b'], 13, "L1", "중간단 A·B — 켜지는지 눈으로만 본다", color_rgb=(210, 140, 0))

    _input_jumper(bb, c, 19, 'C', '74HC00 pin 2')

    bb.step_wire([(c['c'], bb.r_y(20)), (c['c'], bb.r_y(25))], 'sig',
                 '최종 출력 74HC00 pin 3 -> L2', marker_at=(c['c'] + 18, bb.r_y(22)))
    bb.led_chain(c['c'], 25, "L2", "최종 출력 Y = (A·B·C)' — 진리표 검증 대상")

    bb.connect_unused_inputs([4, 5, 9, 10, 12, 13], r_and, bridge_row=29, chip='74HC08')
    bb.mark_unused_outputs([6, 8, 11], r_and, chip='74HC08')
    bb.connect_unused_inputs([4, 5, 9, 10, 12, 13], r_nand, bridge_row=29, chip='74HC00')
    bb.mark_unused_outputs([6, 8, 11], r_nand, chip='74HC00')
    bb.note('입력 A·B·C 는 GND(=0) 에 꽂힌 자리로 그렸다. 1 을 줄 때는 그 점퍼의 레일 쪽 끝만 빨간 +5V 레일로 옮겨 꽂는다. 띄워두지 않는다.')
    bb.export(output_path, max_row=31)


def build_e1_nor(output_path, template_path=None):
    """실험 2-2 · 3입력 NOR (74HC32 앞단 + 74HC02 뒷단). netlist C4.

    **74HC02 는 출력이 1번 핀이다.** 74HC00/08/32 가 (1,2 -> 3) 인 데 반해
    74HC02 는 (2,3 -> 1) 이다 — netlist 가 "이 실험에서 가장 흔한 배선
    실수"로 표시한 지점이다. 2026-2 배포본 교안 p14 가 이 구성(74HC32 앞단 +
    74HC02 뒷단)을 회로도에 직접 라벨해 파생과 일치함이 확인됐다.
    """
    bb = BreadboardRenderer(template_path)
    bb.enable_steps()
    bb.set_header("실험 2-2: 3-Input NOR Gate 결선도",
                  "74HC32 (OR 앞단) + 74HC02 (NOR 뒷단) · 74HC02 는 출력이 1번 핀")
    c = bb.cols['left']
    r_or, r_nor = 7, 18

    bb.draw_chip("74HC32", r_or)
    bb.draw_chip("74HC02", r_nor)
    bb.connect_jacks()
    bb.bridge_rails(c['gnd'], c['mid_gnd'], 29, kind='gnd')
    bb.bridge_rails(c['vcc'], c['mid_vcc'], 30, kind='vcc')
    bb.connect_power(r_or)
    bb.connect_power(r_nor)

    # 8행 레일에는 홀이 없다. 자동 스냅은 7행을 고르는데 그건 A 의 홀이다 — B 는 9행
    _input_jumper(bb, c, 7, 'A', '74HC32 pin 1')
    _input_jumper(bb, c, 8, 'B', '74HC32 pin 2', rail_row=9)

    # A+B 는 74HC02 의 **2번 핀**으로 간다. 1번 핀은 출력이다
    bb.step_wire([(c['c'], bb.r_y(9)), (c['c'], bb.r_y(19))], 'mid',
                 "A+B -> 74HC02 pin 2 (1번 아님!)", marker_at=(c['c'] + 18, bb.r_y(14)))

    bb.step_wire([(c['b'], bb.r_y(9)), (c['b'], bb.r_y(13))], 'mid',
                 '중간단 확인용 갈래', width=2, marker_at=(c['b'] - 20, bb.r_y(11)))
    bb.led_chain(c['b'], 13, "L1", "중간단 A+B — 켜지는지 눈으로만 본다", color_rgb=(210, 140, 0))

    # 20행은 레일 홀도 없고("20 →" 가 인쇄돼) 왼쪽 여백도 막혀 있다 — 19행 홀에서
    # 비스듬히 들어가고 번호 원은 여백 아래쪽으로
    _input_jumper(bb, c, 20, 'C', '74HC02 pin 3', marker=(215, +13))

    # 최종 출력은 74HC02 의 1번 핀 — 칩 맨 윗핀이다
    bb.step_wire([(c['a'], bb.r_y(18)), (c['a'], bb.r_y(25))], 'sig',
                 "최종 출력 74HC02 pin 1 -> L2 (출력이 맨 윗핀)",
                 marker_at=(c['a'] + 18, bb.r_y(22)))
    bb.led_chain(c['a'], 25, "L2", "최종 출력 Y = (A+B+C)' — 진리표 검증 대상")

    bb.connect_unused_inputs([4, 5, 9, 10, 12, 13], r_or, bridge_row=29, chip='74HC32')
    bb.mark_unused_outputs([6, 8, 11], r_or, chip='74HC32')
    bb.connect_unused_inputs([5, 6, 8, 9, 11, 12], r_nor, bridge_row=29, chip='74HC02')
    bb.mark_unused_outputs([4, 10, 13], r_nor, chip='74HC02')
    bb.note('74HC02 는 핀 배치가 다르다 — 입력이 2·3 / 5·6 / 8·9 / 11·12, 출력이 1·4·10·13. '
            '나머지 넷과 반대다.')
    bb.note('입력 A·B·C 는 GND(=0) 에 꽂힌 자리로 그렸다. 1 을 줄 때는 그 점퍼의 레일 쪽 끝만 빨간 +5V 레일로 옮겨 꽂는다. 띄워두지 않는다.')
    bb.export(output_path, max_row=31)


def build_e1_comb(output_path, template_path=None, stage=None):
    """실험 3 · 복합 논리회로 (74HC04 + 74HC08 + 74HC32). netlist C5.

    칩이 셋이라 한 장에 다 그리면 손으로 따라 그리기 버겁다. `stage` 로
    **누적 3단계**를 뽑을 수 있다 — 회로 자체는 하나뿐이라 그림을 쪼갤 수는
    없지만 그리는 순서는 쪼갤 수 있다.

      stage=1  칩 안착 + 전원 (잭·pin14/7·레일 브리지)
      stage=2  1단계 + 신호 배선 (A, B, A', A'·B, Z, X, Y)
      stage=3  2단계 + LED 3벌 + 미사용 핀 처리 = 최종본
    """
    bb = BreadboardRenderer(template_path)
    bb.enable_steps()
    st = 3 if stage is None else stage
    title = {1: "실험 3: 복합 논리회로 — 1단계 (칩과 전원)",
             2: "실험 3: 복합 논리회로 — 2단계 (신호 배선까지)",
             3: "실험 3: 복합 논리회로 결선도 (X, Y, Z 동시 관찰)" if stage is None
                else "실험 3: 복합 논리회로 — 3단계 (완성)"}[st]
    bb.set_header(title,
                  "74HC04 (NOT) + 74HC08 (AND) + 74HC32 (OR) · LED 3개 · 330Ω 3개")

    c_l, c_r = bb.cols['left'], bb.cols['right']
    r_not, r_and, r_or = 7, 18, 10

    # --- 1단계: 칩 안착과 전원 ---
    bb.draw_chip("74HC04", r_not, block='left')
    bb.draw_chip("74HC08", r_and, block='left')
    bb.draw_chip("74HC32", r_or, block='right')
    bb.connect_jacks()
    # 이 그림은 분리된 레일 스트립을 여섯 개 쓴다. 하나라도 안 이으면 그쪽에
    # 물린 핀이 전원을 못 받는다 — 그림은 멀쩡해 보인다
    bb.bridge_rails(c_l['gnd'], c_l['mid_gnd'], 31, kind='gnd')
    bb.bridge_rails(c_l['mid_gnd'], c_r['mid_gnd'], 31, kind='gnd')
    bb.bridge_rails(c_r['mid_gnd'], c_r['gnd'], 31, kind='gnd')
    bb.bridge_rails(c_l['vcc'], c_l['mid_vcc'], 33, kind='vcc')
    bb.bridge_rails(c_l['mid_vcc'], c_r['vcc'], 33, kind='vcc')
    bb.connect_power(r_not, block='left')
    bb.connect_power(r_and, block='left')
    bb.connect_power(r_or, block='right')

    if st >= 2:
        # --- 2단계: 신호 ---
        _input_jumper(bb, c_l, 7, 'A', '74HC04 pin 1')
        # 오른쪽 블록으로 가는 갈래는 **같은 스트립의 다른 홀(a7)** 에 두 번째 점퍼를
        # 꽂는 것이다. 점퍼는 이어 붙일 수 없으니 허공 줄기에서 분기하면 안 된다.
        # 레일과 a열 사이 여백(x=228)으로 빠져 5행까지 올라간 뒤 판 위를 가로지른다
        # — a열을 타고 올라가면 a5·a6 홀을 덮는다
        bb.step_wire([(c_l['a'], bb.r_y(7)), (228, bb.r_y(7)), (228, bb.r_y(5)),
                      (c_r['a'], bb.r_y(5)), (c_r['a'], bb.r_y(13)), (c_r['b'], bb.r_y(13))],
                     'sig', '입력 A 갈래 -> 74HC32 pin 4', width=2, marker_at=(c_r['a'] - 40, bb.r_y(5) - 12))
        bb.step_wire([(c_r['a'], bb.r_y(10)), (c_r['b'], bb.r_y(10))],
                     'sig', '입력 A 갈래 -> 74HC32 pin 1', width=2, marker_at=(c_r['a'] - 18, bb.r_y(10)))

        _input_jumper(bb, c_l, 19, 'B', '74HC08 pin 2')
        # B 갈래도 a19 에 두 번째 점퍼. 여백 x=212 로 6행까지 올라간다 — A 갈래(228)와
        # 다른 세로줄이라 겹치지 않고, 7행에서 입력 A 선과 한 번 교차만 한다
        bb.step_wire([(c_l['a'], bb.r_y(19)), (212, bb.r_y(19)), (212, bb.r_y(6)),
                      (c_r['b'] + 8, bb.r_y(6)), (c_r['b'] + 8, bb.r_y(14)), (c_r['b'], bb.r_y(14))],
                     'sig', '입력 B 갈래 -> 74HC32 pin 5', width=2,
                     marker_at=(c_r['b'] - 60, bb.r_y(6) + 10))

        bb.step_wire([(c_l['c'], bb.r_y(8)), (c_l['c'], bb.r_y(18))], 'mid',
                     "A' (74HC04 pin 2) -> 74HC08 pin 1", marker_at=(c_l['c'] - 20, bb.r_y(15)))
        _tag(bb, c_l['c'] - 46, bb.r_y(12) - 8, "A'")

        bb.step_wire([(c_l['d'], bb.r_y(20)), (c_l['d'], bb.r_y(9))], 'mid',
                     "A'·B (74HC08 pin 3) -> 74HC04 pin 3", marker_at=(c_l['d'] + 18, bb.r_y(16)))
        _tag(bb, c_l['d'] + 12, bb.r_y(21) - 8, "A'·B")

        bb.step_wire([(c_l['b'], bb.r_y(10)), (c_r['c'], bb.r_y(10)), (c_r['c'], bb.r_y(11)), (c_r['b'], bb.r_y(11))],
                     'mid', "Z (74HC04 pin 4) -> 74HC32 pin 2", width=2,
                     marker_at=(c_l['b'] + 60, bb.r_y(10) - 12))

    if st >= 3:
        # --- 3단계: 출력 LED 와 마감 ---
        bb.step_wire([(c_l['b'], bb.r_y(10)), (c_l['b'], bb.r_y(26))], 'sig',
                     'Z 노드 -> Z LED', marker_at=(c_l['b'] - 20, bb.r_y(22)))
        bb.led_chain(c_l['b'], 26, "Z", "Z = (A'·B)' — X 와 항상 같아야 한다",
                     color_rgb=(210, 20, 80))

        bb.step_wire([(c_r['d'], bb.r_y(12)), (c_r['d'], bb.r_y(22))], 'sig',
                     '74HC32 pin 3 -> X LED', marker_at=(c_r['d'] + 18, bb.r_y(18)))
        bb.led_chain(c_r['d'], 22, "X", "X = A + Z — Z 와 다르면 배선 오류",
                     block='right', color_rgb=(220, 120, 0), marker_dx=40)

        bb.step_wire([(c_r['c'], bb.r_y(15)), (c_r['c'], bb.r_y(27))], 'sig',
                     '74HC32 pin 6 -> Y LED', marker_at=(c_r['c'] - 20, bb.r_y(21)))
        bb.led_chain(c_r['c'], 27, "Y", "Y = A + B", block='right', color_rgb=(20, 150, 50))

        bb.connect_unused_inputs([5, 9, 11, 13], r_not, block='left', bridge_row=31, chip='74HC04')
        bb.mark_unused_outputs([6, 8, 10, 12], r_not, block='left', chip='74HC04')
        bb.connect_unused_inputs([4, 5, 9, 10, 12, 13], r_and, block='left', bridge_row=31, chip='74HC08')
        bb.mark_unused_outputs([6, 8, 11], r_and, block='left', chip='74HC08')
        bb.connect_unused_inputs([9, 10, 12, 13], r_or, block='right', bridge_row=31, chip='74HC32')
        bb.mark_unused_outputs([8, 11], r_or, block='right', chip='74HC32')

        bb.note("Z 와 X 는 부울대수로 항등이다 (X = A + (A'·B)' = A + B' = Z). "
                "두 LED 가 서로 다르게 켜지면 배선이 틀린 것이다 — 공짜 자체 검산.")

    bb.note('입력 A·B 두 개뿐이다. 교안 p15 회로도에 C 입력은 없다.')
    bb.note('입력 A·B 는 GND(=0) 에 꽂힌 자리로 그렸다. 1 을 줄 때는 그 점퍼의 레일 쪽 끝만 빨간 +5V 레일로 옮겨 꽂는다. 오른쪽 블록으로 가는 갈래는 같은 행의 a열에 꽂는 두 번째 점퍼다.')
    bb.export(output_path, max_row=34)


# ---------------------------------------------------------------------------
# 실험 2 · CMOS 회로의 전기적 특성
#
# 실험 1 과 성격이 다르다. **정답표가 없다** — LED 가 켜지는지 보는 게 아니라
# 함수발생기로 흔들고 오실로스코프·DMM 으로 읽는다. 그래서 그림에 두 층이 더
# 필요하다.
#
#   · 배선(점퍼선으로 꽂는 것)   -> `step_wire`, 결선 순서표
#   · 계측(프로브·집게로 무는 것) -> `instrument`, 계측표, 회색 점선
#
# 둘을 한 표에 섞으면 조원이 프로브 자리에 점퍼선을 찾는다.
#
# 미사용 입력 처리도 실험 1 과 다르다. 교안 p8 도면이 **일부는 GND, 일부는
# VCC** 로 묶으라고 지정한다 (pin 3·5 -> GND / pin 9·11·13 -> VCC). CMOS 입력은
# 뜨지만 않으면 어느 쪽이든 되지만, 도면대로 따라야 실험실에서 대조가 된다.
#
# 근거: `보고서/실험02/결선도/netlist.md` (C1~C5), `체크리스트/명세.md`.

_E2_UNUSED_GND = [3, 5]        # 교안 p8: 미사용 입력 중 GND 로 내리는 것
_E2_UNUSED_VCC = [9, 11, 13]   # 교안 p8: VCC 로 올리는 것
_E2_UNUSED_OUT = [4, 6, 8, 10, 12]


def _e2_power(bb, block='left'):
    """잭 -> 바깥 레일 -> 중앙 레일. 레일쌍은 별개 스트립이라 브리지가 필수다."""
    c = bb.cols[block]
    bb.connect_jacks()
    bb.bridge_rails(c['gnd'], c['mid_gnd'], 29, kind='gnd')
    bb.bridge_rails(c['vcc'], c['mid_vcc'], 30, kind='vcc')


def _e2_unused(bb, start_row, chip, block='left'):
    """교안 p8 의 미사용핀 처리 한 벌."""
    bb.connect_unused_inputs(_E2_UNUSED_GND, start_row, block=block, chip=chip, rail='gnd')
    bb.connect_unused_inputs(_E2_UNUSED_VCC, start_row, block=block, chip=chip, rail='vcc')
    bb.mark_unused_outputs(_E2_UNUSED_OUT, start_row, block=block, chip=chip)


def _build_e2_vtc(output_path, template_path, chip, title, subtitle, extra_notes=()):
    """E2.P1 / E2.P2 공통. **배선이 글자 그대로 같고 칩만 바뀐다** — 통제
    실험이라 함수발생기 설정·프로브 위치·미사용핀 처리를 하나도 안 바꾼다.
    바꾸면 그림 차이가 칩 때문인지 설정 때문인지 갈리지 않는다."""
    bb = BreadboardRenderer(template_path)
    bb.enable_steps()
    bb.set_header(title, subtitle)
    c = bb.cols['left']
    r = 10

    bb.draw_chip(chip, r)
    _e2_power(bb)
    bb.connect_power(r)
    _e2_unused(bb, r, chip)

    # pin 1 은 함수발생기가 물고, pin 2 는 아무 부하 없이 프로브만 문다.
    # 점퍼선으로 꽂을 배선이 전원과 미사용핀뿐이다
    bb.instrument(c['a'], r, '함수발생기 + CH1 (X축)',
                  f'사인파 Vpp 5V · 오프셋 2.5V · {chip} pin 1 (= V_IN)', lane_row=5)
    bb.instrument(c['a'], r + 1, 'CH2 (Y축)',
                  f'{chip} pin 2 (= V_OUT). 부하 없음 — 프로브만 문다', lane_row=7)
    bb.instrument_note('두 프로브 접지 클립', '공통 GND 레일', '보드 GND 와 같은 노드')

    bb.note('오프셋 2.5V 를 빼먹으면 입력이 -2.5V 까지 내려간다. 데이터시트 LIMITING '
            'VALUES 가 V_I < -0.5V 에서 입력 보호 다이오드에 전류가 흐른다고 못박는다 — '
            '함수발생기가 전류를 제한하지 않으면 입력단이 상한다.')
    bb.note('오실로스코프를 X-Y 로 둔다: [Horiz] → 시간 모드 → XY (매뉴얼 p46~p47). '
            'CH1/CH2 를 바꿔 물면 곡선이 90도 돈다 — 오프셋을 잠깐 올렸다 내려서 '
            '곡선이 **좌우로** 움직이면 제대로 문 것이다.')
    for t in extra_notes:
        bb.note(t)
    bb.export(output_path, max_row=31)


def build_e2_inv(output_path, template_path=None):
    """실험 2-1 · Inverter 입출력 특성 (74HC04 VTC). netlist C1."""
    return _build_e2_vtc(
        output_path, template_path, '74HC04',
        "실험 2-1: Inverter 입출력 특성 (VTC)",
        "74HC04 (Hex Inverter) · 오실로스코프 X-Y 모드 (CH1=V_IN, CH2=V_OUT)")


def build_e2_schmitt(output_path, template_path=None):
    """실험 2-2 · Schmitt-trigger 입출력 특성 (74HC14). netlist C2."""
    return _build_e2_vtc(
        output_path, template_path, '74HC14',
        "실험 2-2: Schmitt-trigger 입출력 특성 (히스테리시스)",
        "74HC14 (Schmitt-trigger Hex Inverter) · 실험 2-1 과 배선이 같고 칩만 바뀐다",
        extra_notes=(
            '실험 2-1 의 통제 실험이다. 배선·함수발생기 설정·프로브 위치를 하나도 '
            '바꾸지 않는다. 바꾸면 그림 차이가 칩 때문인지 설정 때문인지 갈리지 않는다.',
            '칩을 바꿔 꽂을 때 전원을 내린다. 전원이 살아 있는 채로 DIP 를 뽑으면 '
            '핀이 순서대로 빠지면서 입력에만 전원이 걸린 순간이 생긴다.',
            '74HC14 는 74HC04 와 핀 배치가 같다 (Nexperia Rev. 10 §6.2 확인).'))


def _build_e2_dc(output_path, template_path, mode):
    """E2.P3-1(Rn) / E2.P3-2(Rp). **부하 저항의 위치가 이 항목의 전부다.**

    Rn: pin 1 -> VCC (입력 HIGH -> 출력 LOW). R1 이 VCC 와 출력 사이 -> 출력이
        전류를 빨아들이는 sinking. NMOS 도통 저항에 걸린 전압이 V_OL.
    Rp: pin 1 -> GND (입력 LOW -> 출력 HIGH). R1 이 출력과 GND 사이 -> sourcing.
        PMOS 도통 저항에서 잃은 만큼 V_OH 가 VCC 보다 낮아진다.

    위아래를 뒤집은 것뿐이고 **바뀌는 곳은 두 군데다** (pin 1 이 붙는 레일,
    R1 의 반대쪽이 붙는 레일).
    """
    rn = (mode == 'Rn')
    rail = 'vcc' if rn else 'gnd'
    bb = BreadboardRenderer(template_path)
    bb.enable_steps()
    bb.set_header(
        f"실험 2-3{'(1)' if rn else '(2)'}: CMOS DC 특성 — {mode}",
        f"74HC04 · {'NMOS' if rn else 'PMOS'} 온저항 · 1kΩ 부하를 "
        f"{'VCC 와 출력 사이' if rn else '출력과 GND 사이'} 에 둔다 "
        f"· 출력이 {'sinking (V_OL)' if rn else 'sourcing (V_OH)'}")
    c = bb.cols['left']
    r = 10

    bb.draw_chip('74HC04', r)
    _e2_power(bb)
    bb.connect_power(r)

    # pin 1 을 레일에 직결한다. CMOS 입력은 전류를 거의 안 먹으므로 저항이 필요없다
    x_rail = (bb.nearest_vcc_rail if rn else bb.nearest_gnd_rail)(c['b'], 'left')
    bb.step_wire([(c['b'], bb.r_y(r)), (x_rail, bb.r_y(bb.snap_rail_row(r)))], rail,
                 f"pin 1 -> {'+5V' if rn else 'GND'} 직결 "
                 f"(입력 {'HIGH' if rn else 'LOW'} -> 출력 {'LOW' if rn else 'HIGH'} 고정)",
                 marker_at=(c['b'] - 30, bb.r_y(r) - 12))

    # R1 = 1kΩ. pin 2 가 있는 행(a~e 는 한 줄이 한 노드다)에서 아래로 내린다
    bb.draw_resistor(c['a'], bb.r_y(r + 1), bb.r_y(r + 4), label="1kΩ")
    bb.step_note('sig', bb.addr(c['a'], bb.r_y(r + 1)), bb.addr(c['a'], bb.r_y(r + 4)),
                 'R1 = 1kΩ 꽂기 (pin 2 와 같은 행에서 시작)',
                 marker_at=(c['a'] - 22, (bb.r_y(r + 1) + bb.r_y(r + 4)) // 2))
    x_far = (bb.nearest_vcc_rail if rn else bb.nearest_gnd_rail)(c['a'], 'left')
    bb.step_wire([(c['a'], bb.r_y(r + 4)), (x_far, bb.r_y(bb.snap_rail_row(r + 4)))], rail,
                 f"R1 반대쪽 -> {'+5V' if rn else 'GND'} 레일",
                 marker_at=(c['a'] - 30, bb.r_y(r + 4) + 10))

    _e2_unused(bb, r, '74HC04')

    bb.instrument_note('S1 · DMM 저항(Ω) 모드', 'R1 양끝',
                       '**회로에 꽂기 전에** R1 실저항을 잰다. 꽂은 채로 재면 IC 를 '
                       '통한 우회 경로가 병렬로 붙어 값이 틀린다')
    bb.instrument(c['c'], r + 1, 'S2 · DMM DCV (+)',
                  f"74HC04 pin 2 = V_out (= {'V_OL' if rn else 'V_OH'}). (-) 는 공통 GND",
                  lane_row=6)
    if rn:
        bb.instrument(c['d'], r + 1, 'S3 · DMM DCV — R1 양단',
                      '(+) VCC 레일, (-) pin 2. R1 양단 전압에서 I_OL 을 낸다', lane_row=20)
    else:
        bb.instrument_note('S3 · DMM DCV', 'VCC 레일 ↔ 공통 GND',
                           'VCC 실측. Rp 의 분자가 (VCC - V_OH) 라 공칭 5.00V 를 쓰면 '
                           '두 큰 수의 차에서 오차가 커진다')

    if rn:
        bb.note('pin 2(출력)를 VCC 에 **직결하면 안 된다.** 반드시 R1 을 거친다 — '
                '직결하면 도통한 NMOS 를 통해 VCC 가 GND 로 단락된다.')
        bb.note('R1 양단 전압 / R1 = I_OL. V_OL / I_OL = Rn.')
    else:
        bb.note('R1 이 pin 2 와 GND 사이에 있으므로 **R1 양단 전압 = V_out** 이다. '
                '따라서 I_OH = V_out / R1 이고 DMM 접점이 Rn 쪽보다 하나 줄어든다.')
        bb.note('(VCC - V_OH) / I_OH = Rp. 보통 Rp > Rn 이고, 그것이 상승 천이가 '
                '하강 천이보다 느린 원인이다 — 실험 2-4 의 지연 비대칭이 여기서 나온다.')
    bb.note('전류계를 쓸 거면 **반드시 직렬로** 넣는다. 저항이나 전원에 병렬로 대면 '
            '전류계가 VCC 를 단락시켜 퓨즈가 나간다.')
    bb.export(output_path, max_row=31)


def build_e2_rn(output_path, template_path=None):
    """실험 2-3 (1) · CMOS DC 특성 — Rn. netlist C3."""
    return _build_e2_dc(output_path, template_path, 'Rn')


def build_e2_rp(output_path, template_path=None):
    """실험 2-3 (2) · CMOS DC 특성 — Rp. netlist C4."""
    return _build_e2_dc(output_path, template_path, 'Rp')


def build_e2_tpd(output_path, template_path=None):
    """실험 2-4 · 전파지연 tpd (74HC04 두 개). netlist C5.

    **체인이 핀 번호 순서로 흐르지 않는다.** `pin 6` 에서 `pin 13` 으로 건너뛴 뒤
    번호를 거슬러 내려온다 (교안 p13 회로도를 900dpi 로 렌더해 확정).

        1 →2 · 3 →4 · 5 →6 · 13→12 · 11→10 · 9 →8

    CH1(pin 4) 과 CH2(pin 8) 사이에 인버터가 **4단** 있다. 핀 번호만 보고
    `1→2, 3→4, 5→6, 9→8` 로 짐작하면 2단으로 세게 되고 게이트당 t_pd 가 정확히
    2배로 나온다 — 이 주차에서 가장 비싼 실수다. 배선이 아니라 계산에서 틀리므로
    실험실에서는 아무 이상이 없어 보인다.
    """
    bb = BreadboardRenderer(template_path)
    bb.enable_steps()
    bb.set_header("실험 2-4: CMOS AC 특성 — 전파지연 t_pd",
                  "74HC04 두 개 · U1 은 인버터 6개 직렬 체인, U2 는 최종단 부하 · CH1=pin 4, CH2=pin 8")
    c_l, c_r = bb.cols['left'], bb.cols['right']
    r1, r2 = 7, 10   # U1 좌측 7행, U2 우측 10행

    bb.draw_chip('74HC04', r1, block='left')
    bb.draw_chip('74HC04', r2, block='right')

    bb.connect_jacks()
    bb.bridge_rails(c_l['gnd'], c_l['mid_gnd'], 31, kind='gnd')
    bb.bridge_rails(c_l['mid_gnd'], c_r['mid_gnd'], 31, kind='gnd')
    bb.bridge_rails(c_r['mid_gnd'], c_r['gnd'], 31, kind='gnd')
    bb.bridge_rails(c_l['vcc'], c_l['mid_vcc'], 33, kind='vcc')
    bb.bridge_rails(c_l['mid_vcc'], c_r['vcc'], 33, kind='vcc')
    bb.connect_power(r1, block='left')
    bb.connect_power(r2, block='right')

    # U1 체인. 인접 핀끼리는 짧은 점퍼 넷, 6->13 하나만 칩을 가로지른다
    bb.step_wire([(c_l['b'], bb.r_y(8)), (c_l['b'], bb.r_y(9))], 'mid',
                 '1단 출력 pin 2 -> 2단 입력 pin 3', width=4,
                 marker_at=(c_l['b'] - 20, bb.r_y(8) + 8))
    bb.step_wire([(c_l['b'], bb.r_y(10)), (c_l['b'], bb.r_y(11))], 'mid',
                 '2단 출력 pin 4 -> 3단 입력 pin 5', width=4,
                 marker_at=(c_l['b'] - 20, bb.r_y(10) + 8))
    # 3단 출력 pin 6 (12행, a~e 쪽) -> 4단 입력 pin 13 (8행, f~j 쪽). 칩 위로 넘긴다
    bb.step_wire([(c_l['c'], bb.r_y(12)), (c_l['c'], bb.r_y(5)),
                  (c_l['h'], bb.r_y(5)), (c_l['h'], bb.r_y(8))], 'mid',
                 '3단 출력 pin 6 -> 4단 입력 pin 13 (칩을 가로지르는 유일한 긴 점퍼)',
                 marker_at=(c_l['e'] + 6, bb.r_y(5) - 12))
    bb.step_wire([(c_l['g'], bb.r_y(9)), (c_l['g'], bb.r_y(10))], 'mid',
                 '4단 출력 pin 12 -> 5단 입력 pin 11', width=4,
                 marker_at=(c_l['g'] + 20, bb.r_y(9) + 8))
    bb.step_wire([(c_l['g'], bb.r_y(11)), (c_l['g'], bb.r_y(12))], 'mid',
                 '5단 출력 pin 10 -> 6단 입력 pin 9', width=4,
                 marker_at=(c_l['g'] + 20, bb.r_y(11) + 8))

    # U1 pin 8 (6단 출력, 13행 f~j 쪽) -> U2 pin 1 (우측 10행 a~e 쪽)
    bb.step_wire([(c_l['i'], bb.r_y(13)), (c_l['i'], bb.r_y(4)),
                  (c_r['a'], bb.r_y(4)), (c_r['a'], bb.r_y(10))], 'sig',
                 'U1 최종단 pin 8 -> U2 pin 1 (게이트 입력 부하)',
                 marker_at=(c_r['a'] - 70, bb.r_y(4) - 12))

    # U2 는 논리에 관여하지 않는다. pin 1 만 받고 나머지는 도면대로 묶는다
    bb.connect_unused_inputs(_E2_UNUSED_GND, r2, block='right', chip='U2', rail='gnd')
    bb.connect_unused_inputs(_E2_UNUSED_VCC, r2, block='right', chip='U2', rail='vcc')
    bb.mark_unused_outputs([2] + _E2_UNUSED_OUT, r2, block='right', chip='U2')

    bb.instrument(c_l['a'], r1, '함수발생기', 'U1 pin 1 (체인 입력)', lane_row=17)
    bb.instrument(c_l['d'], 10, 'CH1', 'U1 pin 4 = 2단 출력. 여기가 지연 측정 시작점',
                  lane_row=19)
    bb.instrument(c_l['h'], 13, 'CH2', 'U1 pin 8 = 6단 출력. CH1 과 사이에 인버터 4단',
                  lane_row=21)
    bb.instrument_note('두 프로브 접지 클립', '공통 GND 레일', '보드 GND 와 같은 노드')

    bb.note('U1 에는 **미사용 입력핀이 없다.** 인버터 6개를 전부 쓰므로 14핀이 모두 '
            '물린다. 다른 항목의 습관대로 pin 3·5 를 GND 로 내리면 체인이 끊긴다.')
    bb.note('긴 점퍼(pin 6 -> pin 13)가 빠지면 뒤 4단이 전부 죽고 pin 8 이 뜬다. '
            '화면에는 CH2 가 노이즈처럼 흔들리는 모습으로 나타나지, 지연이 이상한 '
            '모습으로 나타나지 않는다.')
    bb.note('CH1 과 CH2 사이는 **4단**이다 (5→6, 13→12, 11→10, 9→8). 핀 번호만 보고 '
            '2단으로 세면 게이트당 t_pd 가 정확히 2배로 나온다. 짝수 단이라 두 파형은 '
            '동상이고, Δt = 2·t_PHL + 2·t_PLH 이므로 둘을 분리할 수 없다 — 평균만 얻는다.')
    bb.note('U2 는 논리에 관여하지 않는다. U1 최종단에 게이트 입력 부하 하나를 '
            '더하는 것이 전부이고, U2 pin 2 는 개방이다.')
    bb.export(output_path, max_row=34)


def build_e2_all(output_dir, template_path=None):
    """실험 2의 모든 결선도 5종을 지정된 디렉토리에 일괄 렌더링"""
    os.makedirs(output_dir, exist_ok=True)
    targets = [
        ("실험02_결선도_인버터_입출력특성.png", build_e2_inv),
        ("실험02_결선도_슈미트트리거_입출력특성.png", build_e2_schmitt),
        ("실험02_결선도_DC특성_Rn.png", build_e2_rn),
        ("실험02_결선도_DC특성_Rp.png", build_e2_rp),
        ("실험02_결선도_전파지연_tpd.png", build_e2_tpd),
    ]
    for filename, func in targets:
        p = os.path.join(output_dir, filename)
        func(p, template_path)
    print(f"[SUCCESS] All 5 diagrams for 실험02 generated in: {output_dir}")


# 단계별 빌더는 **이름 있는 함수**로 둔다. 람다로 두면
# `tests/test_breadboard_diagram_cli.py` 가 dispatch 를 AST 로 읽어 "두 회로가
# 한 빌더를 공유하지 않는지" 보는 가드가 깨진다 — OR·NOR 이 AND·NAND 빌더의
# 별칭이던 시절을 잡아낸 바로 그 검사다.
def build_e1_comb_s1(output_path, template_path=None):
    """복합회로 1단계 — 칩 안착과 전원만."""
    build_e1_comb(output_path, template_path, stage=1)


def build_e1_comb_s2(output_path, template_path=None):
    """복합회로 2단계 — 1단계 + 신호 배선."""
    build_e1_comb(output_path, template_path, stage=2)


def build_e1_comb_s3(output_path, template_path=None):
    """복합회로 3단계 — 2단계 + LED 3벌과 미사용 핀 처리."""
    build_e1_comb(output_path, template_path, stage=3)


def build_e1_all(output_dir, template_path=None):
    """실험 1 결선도 일괄 렌더. 복합회로는 **누적 3단계만** 낸다 — 칩 셋을
    한 장으로 따라 그리는 건 무리라서 그리는 순서를 쪼개 준다."""
    os.makedirs(output_dir, exist_ok=True)
    targets = [
        ("실험01_결선도_3입력_AND.png", build_e1_and),
        ("실험01_결선도_3입력_OR.png", build_e1_or),
        ("실험01_결선도_3입력_NAND.png", build_e1_nand),
        ("실험01_결선도_3입력_NOR.png", build_e1_nor),
        # 복합회로는 **누적 3단계만** 낸다. 통짜 한 장(`e1_comb`)은 3단계
        # 완성본과 그림이 같으면서 순서를 안 주므로, 손으로 따라 그릴 사람에게
        # 줄 것이 못 된다. CLI 로는 여전히 뽑을 수 있다
        ("실험01_결선도_복합논리회로_1단계_전원.png", build_e1_comb_s1),
        ("실험01_결선도_복합논리회로_2단계_신호.png", build_e1_comb_s2),
        ("실험01_결선도_복합논리회로_3단계_완성.png", build_e1_comb_s3),
    ]
    for filename, func in targets:
        func(os.path.join(output_dir, filename), template_path)
    print(f"[SUCCESS] 실험01 결선도 {len(targets)}장 생성: {output_dir}")


def main():
    parser = argparse.ArgumentParser(description="Breadboard Diagram Generator")
    parser.add_argument("--circuit", required=True, choices=[
        "e1_and", "e1_or", "e1_nand", "e1_nor", "e1_comb",
        "e1_comb_s1", "e1_comb_s2", "e1_comb_s3", "e1_all",
        "e2_inv", "e2_schmitt", "e2_rn", "e2_rp", "e2_tpd", "e2_all"
    ], help="Circuit ID to render")
    parser.add_argument("--output", required=True, help="Output PNG path (or directory path for e2_all)")
    parser.add_argument("--template", default=None, help="Path to Breadboard.jpg")
    args = parser.parse_args()
    
    dispatch = {
        "e1_and": build_e1_and,
        "e1_or": build_e1_or,
        "e1_nand": build_e1_nand,
        "e1_nor": build_e1_nor,
        "e1_comb": build_e1_comb,
        "e1_comb_s1": build_e1_comb_s1,
        "e1_comb_s2": build_e1_comb_s2,
        "e1_comb_s3": build_e1_comb_s3,
        "e1_all": build_e1_all,
        "e2_inv": build_e2_inv,
        "e2_schmitt": build_e2_schmitt,
        "e2_rn": build_e2_rn,
        "e2_rp": build_e2_rp,
        "e2_tpd": build_e2_tpd,
        "e2_all": build_e2_all,
    }
    dispatch[args.circuit](args.output, args.template)

if __name__ == "__main__":
    main()
