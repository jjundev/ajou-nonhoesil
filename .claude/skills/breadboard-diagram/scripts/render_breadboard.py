import os
import sys
import argparse
from PIL import Image, ImageDraw, ImageFont

class BreadboardRenderer:
    def __init__(self, template_path=None):
        if template_path is None:
            candidate_paths = [
                'from_the_past/정리/강의노트/Breadboard.jpg',
                'from_the_past/정리/아카이브/강의노트/Breadboard.jpg',
                '/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/강의노트/Breadboard.jpg'
            ]
            for p in candidate_paths:
                if os.path.exists(p):
                    template_path = p
                    break
        if not template_path or not os.path.exists(template_path):
            raise FileNotFoundError(f"Breadboard template not found: {template_path}")
            
        self.base_im = Image.open(template_path).convert('RGBA')
        self.im = self.base_im.copy()
        self.overlay = Image.new('RGBA', self.im.size, (0, 0, 0, 0))
        self.draw = ImageDraw.Draw(self.overlay)
        # 이미 그린 레일 브리지. 칩마다 connect_unused_inputs 를 부르면 같은
        # 레일쌍을 여러 번 잇게 되므로 한 번만 그린다
        self._bridged = set()
        
        # Typography
        self.font_title = ImageFont.truetype('/System/Library/Fonts/AppleSDGothicNeo.ttc', 21)
        self.font_subtitle = ImageFont.truetype('/System/Library/Fonts/AppleSDGothicNeo.ttc', 14)
        self.font_kr_bold = ImageFont.truetype('/System/Library/Fonts/AppleSDGothicNeo.ttc', 12)
        self.font_kr_sm = ImageFont.truetype('/System/Library/Fonts/AppleSDGothicNeo.ttc', 11)
        self.font_en_bold = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 12)
        self.font_en_sm = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 10)
        self.font_chip = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 11)
        
        self.cols = {
            'left': {
                'gnd': 163, 'vcc': 193,
                'a': 236, 'b': 252, 'c': 269, 'd': 286, 'e': 302,
                'chip_x1': 308, 'chip_x2': 352,
                'f': 358, 'g': 375, 'h': 392, 'i': 408, 'j': 425,
                'mid_gnd': 458, 'mid_vcc': 488
            },
            'right': {
                'mid_gnd': 529, 'mid_vcc': 559,
                'a': 614, 'b': 631, 'c': 648, 'd': 665, 'e': 681,
                'chip_x1': 686, 'chip_x2': 730,
                'f': 738, 'g': 755, 'h': 772, 'i': 789, 'j': 806,
                'gnd': 837, 'vcc': 867
            }
        }
        
    def r_y(self, r):
        return int(243 + (r - 1) * 17.15)
        
    def set_header(self, title, subtitle):
        self.draw.rectangle([370, 30, 850, 160], fill=(255, 255, 255, 255))
        self.draw.text((380, 50), title, fill=(20, 40, 90, 255), font=self.font_title)
        self.draw.text((382, 85), subtitle, fill=(80, 90, 100, 255), font=self.font_subtitle)
        self.draw.text((382, 110), "※ 손스케치 시 이 결선도를 바탕으로 따라 그리고 학번/이름/날짜 자필 서명 필수", fill=(180, 50, 50, 255), font=self.font_kr_sm)

    def draw_badge(self, x, y, text, bg_col=(255, 255, 255, 235), text_col=(20, 20, 20, 255), font=None, pad=3):
        if font is None:
            font = self.font_kr_bold
        bbox = self.draw.textbbox((x, y), text, font=font)
        self.draw.rectangle([bbox[0]-pad, bbox[1]-pad, bbox[2]+pad, bbox[3]+pad], fill=bg_col, outline=text_col, width=1)
        self.draw.text((x, y), text, fill=text_col, font=font)

    def draw_wire(self, points, color, width=3):
        self.draw.line(points, fill=color, width=width, joint='curve')
        p_start, p_end = points[0], points[-1]
        self.draw.ellipse([p_start[0]-3, p_start[1]-3, p_start[0]+3, p_start[1]+3], fill=color)
        self.draw.ellipse([p_end[0]-3, p_end[1]-3, p_end[0]+3, p_end[1]+3], fill=color)

    def draw_resistor(self, x, y1, y2, label="330Ω", bands=None):
        wire_col = (100, 100, 100, 255)
        body_col = (225, 195, 145, 255)
        ymid = (y1 + y2) // 2
        self.draw.line([(x, y1), (x, ymid - 12)], fill=wire_col, width=2)
        self.draw.line([(x, ymid + 12), (x, y2)], fill=wire_col, width=2)
        self.draw.rectangle([x - 5, ymid - 12, x + 5, ymid + 12], fill=body_col, outline=(90, 70, 40, 255), width=1)
        
        if bands is None:
            if "1k" in label:
                # 1kΩ: Brown (1), Black (0), Red (x100), Gold (±5%)
                bands = [
                    (139, 69, 19, 255),  # Brown
                    (30, 30, 30, 255),    # Black
                    (200, 20, 20, 255),   # Red
                    (218, 165, 32, 255)   # Gold
                ]
            else:
                # 330Ω: Orange (3), Orange (3), Brown (x10), Gold (±5%)
                bands = [
                    (204, 85, 0, 255),   # Orange
                    (204, 85, 0, 255),   # Orange
                    (139, 69, 19, 255),  # Brown
                    (218, 165, 32, 255)  # Gold
                ]
        
        offsets = [-7, -2, 3, 8]
        for col, off in zip(bands, offsets):
            self.draw.line([(x - 4, ymid + off), (x + 4, ymid + off)], fill=col, width=2)
            
        self.draw_badge(x + 10, ymid - 7, label, (255, 255, 255, 230), (100, 60, 20, 255), font=self.font_en_sm, pad=2)

    def draw_led(self, x, y_anode, y_cathode, color_rgb=(230, 30, 30), label="LED"):
        ymid = (y_anode + y_cathode) // 2
        self.draw.line([(x, y_anode), (x, ymid - 8)], fill=(130, 130, 130, 255), width=2)
        self.draw.line([(x, ymid + 8), (x, y_cathode)], fill=(130, 130, 130, 255), width=2)
        self.draw.ellipse([x - 8, ymid - 8, x + 8, ymid + 8], fill=(*color_rgb, 240), outline=(255, 255, 255, 255), width=2)
        self.draw_badge(x + 12, ymid - 7, label, (255, 255, 255, 230), color_rgb, font=self.font_kr_bold, pad=2)

    def draw_chip(self, name, start_row, block='left'):
        c = self.cols[block]
        x1, x2 = c['chip_x1'], c['chip_x2']
        y_top = self.r_y(start_row) - 8
        y_bot = self.r_y(start_row + 6) + 8
        
        self.draw.rectangle([x1, y_top, x2, y_bot], fill=(30, 33, 36, 255), outline=(130, 140, 150, 255), width=2)
        notch_w = (x2 - x1) // 3
        self.draw.arc([x1 + notch_w, y_top - 6, x2 - notch_w, y_top + 6], 0, 180, fill=(200, 200, 200, 255), width=2)
        
        bbox = self.draw.textbbox((0, 0), name, font=self.font_chip)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        ymid = (y_top + y_bot) // 2
        self.draw.text(((x1 + x2 - tw) // 2, ymid - th // 2), name, fill=(255, 255, 255, 255), font=self.font_chip)
        
        for i in range(7):
            curr_r = start_row + i
            y = self.r_y(curr_r)
            pin_l = i + 1
            pin_r = 14 - i
            self.draw.line([(c['e'], y), (x1, y)], fill=(170, 170, 170, 255), width=3)
            self.draw.line([(x2, y), (c['f'], y)], fill=(170, 170, 170, 255), width=3)
            self.draw.text((c['e'] - 15, y - 6), str(pin_l), fill=(80, 80, 80, 255), font=self.font_en_sm)
            self.draw.text((c['f'] + 6, y - 6), str(pin_r), fill=(80, 80, 80, 255), font=self.font_en_sm)

    def bridge_rails(self, x_a, x_b, row, kind='gnd', label=None):
        """물리적으로 분리된 전원 레일 모듈 둘을 잇는 점퍼.

        이 템플릿의 레일쌍(좌 163/193, 중앙좌 458/488, 중앙우 529/559,
        우 837/867)은 각각 **별개 스트립**이다. 칩 7번 핀을 좌측 GND 레일에
        내리고 미사용 입력을 중앙 GND 레일에 내리면 두 레일이 이어져 있지
        않아 미사용 입력이 뜬다. 그 점퍼를 명시적으로 그린다.

        `row` 는 레일에 실제 홀이 있는 행이어야 한다. 이 템플릿에서 홀이
        없는 행은 2, 3, 4, 9, 15, 21, 32 다.
        """
        key = (kind, min(x_a, x_b), max(x_a, x_b))
        if key in self._bridged:
            return
        self._bridged.add(key)

        color = (20, 60, 220, 255) if kind == 'gnd' else (220, 20, 20, 255)
        y = self.r_y(row)
        self.draw_wire([(x_a, y), (x_b, y)], color, width=3)

        if label is None:
            label = "레일 브리지 ──> GND 공통" if kind == 'gnd' else "레일 브리지 ──> +5V 공통"
        if label:
            bg = (240, 245, 255, 240) if kind == 'gnd' else (255, 240, 240, 240)
            self.draw_badge(min(x_a, x_b) + 12, y + 7, label, bg, color, font=self.font_kr_sm)

    def connect_power(self, start_row, block='left'):
        c = self.cols[block]
        self.draw_wire([(c['f'], self.r_y(start_row)), (c['mid_vcc'], self.r_y(start_row))], (220, 20, 20, 255), width=3)
        self.draw_badge(c['mid_vcc'] + 10, self.r_y(start_row) - 8, "VCC (+5V)", (255, 240, 240, 240), (200, 0, 0, 255), font=self.font_en_bold)
        
        self.draw_wire([(c['e'], self.r_y(start_row + 6)), (c['gnd'], self.r_y(start_row + 6))], (20, 60, 220, 255), width=3)
        self.draw_badge(c['gnd'] - 55, self.r_y(start_row + 6) - 8, "GND (0V)", (240, 240, 255, 240), (20, 60, 220, 255), font=self.font_en_bold)

    def connect_unused_inputs(self, pins, start_row, block='left', bridge_row=None):
        c = self.cols[block]
        for p in pins:
            if 1 <= p <= 7:
                row = start_row + (p - 1)
                self.draw_wire([(c['d'], self.r_y(row)), (c['gnd'], self.r_y(row))], (20, 60, 220, 255), width=2)
            elif 8 <= p <= 14:
                row = start_row + (14 - p)
                self.draw_wire([(c['g'], self.r_y(row)), (c['mid_gnd'], self.r_y(row))], (20, 60, 220, 255), width=2)
                
        pin_str = ", ".join(str(p) for p in pins)
        mid_r = start_row + 2
        self.draw_badge(c['mid_gnd'] + 15, self.r_y(mid_r) - 8, f"미사용 입력 ({pin_str}) ──> GND 접지", (240, 245, 255, 240), (20, 60, 200, 255))

        # 8~14번 핀은 중앙 GND 레일로 내려가는데, 7번 핀이 물린 레일과 별개
        # 스트립이다. 브리지를 그리지 않으면 그 미사용 입력들이 그대로 뜬다
        if any(8 <= p <= 14 for p in pins):
            if bridge_row is None:
                print(f"[WARN] {block} 블록 미사용 입력 {pin_str} 이 중앙 GND 레일에 "
                      f"내려갔는데 bridge_row 가 없다 — 7번 핀 레일과 이어지지 않아 "
                      f"뜬다. 빌더에서 bridge_row 를 넘겨라", file=sys.stderr)
            else:
                self.bridge_rails(c['mid_gnd'], c['gnd'], bridge_row, kind='gnd')

    def mark_unused_outputs(self, pins, start_row, block='left'):
        c = self.cols[block]
        for p in pins:
            if 1 <= p <= 7:
                row = start_row + (p - 1)
                self.draw_badge(c['d'] - 45, self.r_y(row) - 8, f"Pin {p}: NC", (250, 250, 250, 240), (130, 60, 60, 255), font=self.font_kr_sm)
            elif 8 <= p <= 14:
                row = start_row + (14 - p)
                self.draw_badge(c['f'] + 20, self.r_y(row) - 8, f"Pin {p}: NC (개방)", (250, 250, 250, 240), (130, 60, 60, 255), font=self.font_kr_sm)
                
        pin_str = ", ".join(str(p) for p in pins)
        mid_r = start_row + 4
        self.draw_badge(c['mid_gnd'] + 15, self.r_y(mid_r) - 8, f"미사용 출력 ({pin_str}) ──> 개방(NC) 필수", (255, 240, 240, 240), (180, 40, 40, 255))

    def export(self, output_path, max_row=35):
        final_im = Image.alpha_composite(self.im, self.overlay)
        crop_box = (0, 0, 998, self.r_y(max_row) + 20)
        cropped = final_im.crop(crop_box)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        cropped.save(output_path)
        print(f"[SUCCESS] Exported: {output_path} ({cropped.size[0]}x{cropped.size[1]})")


def build_e1_and(output_path, template_path=None):
    bb = BreadboardRenderer(template_path)
    bb.set_header("실험 1-1: 3-Input AND Gate 회로 결선도", "IC: 74HC08 (Quad 2-Input AND) · 다이오드 보호 330Ω 저항 필수")
    bb.draw_chip("74HC08", 10)
    bb.connect_power(10)
    c = bb.cols['left']
    
    bb.draw_wire([(c['b'], bb.r_y(10)), (c['a'], bb.r_y(10)), (c['a'], bb.r_y(5)), (95, bb.r_y(5))], (230, 90, 0, 255), width=3)
    bb.draw_badge(12, bb.r_y(5) - 9, "입력 A (1A)", (255, 245, 235, 240), (210, 80, 0, 255))
    
    bb.draw_wire([(c['b'], bb.r_y(11)), (c['a'] - 16, bb.r_y(11)), (c['a'] - 16, bb.r_y(6)), (95, bb.r_y(6))], (0, 120, 180, 255), width=3)
    bb.draw_badge(12, bb.r_y(6) - 9, "입력 B (1B)", (235, 245, 255, 240), (0, 110, 170, 255))
    
    bb.draw_wire([(c['b'], bb.r_y(14)), (c['a'], bb.r_y(14)), (c['a'], bb.r_y(7)), (95, bb.r_y(7))], (20, 150, 40, 255), width=3)
    bb.draw_badge(12, bb.r_y(7) - 9, "입력 C (2B)", (235, 255, 235, 240), (20, 130, 30, 255))
    
    bb.draw_wire([(c['c'], bb.r_y(12)), (c['c'], bb.r_y(13))], (140, 40, 200, 255), width=4)
    bb.draw_badge(c['c'] - 75, bb.r_y(12) + 1, "1단->2단 연결", (255, 245, 255, 230), (130, 30, 190, 255), font=bb.font_kr_sm)
    
    bb.draw_wire([(c['a'], bb.r_y(12)), (c['a'], bb.r_y(19))], (180, 40, 180, 255), width=2)
    bb.draw_led(c['a'], bb.r_y(19), bb.r_y(20), color_rgb=(210, 140, 0), label="L1 중간 LED (A·B)")
    bb.draw_resistor(c['a'], bb.r_y(20), bb.r_y(22), label="330Ω")
    bb.draw_wire([(c['a'], bb.r_y(22)), (c['gnd'], bb.r_y(22))], (20, 60, 220, 255), width=2)
    
    bb.draw_wire([(c['c'], bb.r_y(15)), (c['c'], bb.r_y(24))], (220, 20, 70, 255), width=3)
    bb.draw_led(c['c'], bb.r_y(24), bb.r_y(25), color_rgb=(220, 20, 20), label="L2 최종 LED (Y=A·B·C)")
    bb.draw_resistor(c['c'], bb.r_y(25), bb.r_y(27), label="330Ω")
    bb.draw_wire([(c['c'], bb.r_y(27)), (c['gnd'], bb.r_y(27))], (20, 60, 220, 255), width=2)
    
    bb.connect_unused_inputs([9, 10, 12, 13], 10, bridge_row=29)
    bb.mark_unused_outputs([8, 11], 10)
    bb.export(output_path, max_row=30)


def build_e1_or(output_path, template_path=None):
    """실험 1-1 (2) · 3입력 OR (74HC32). netlist C2.

    C1(AND) 과 위상이 같다 — 74HC32 는 74HC00·74HC08 과 같은 표준 DIP-14 쿼드
    2입력 배치(1,2→3 / 4,5→6)를 쓴다. **그 핀아웃은 저장소 데이터시트로도
    저장소 회로도로도 확인되지 않았다(netlist M1).** 실물 칩 각인을 벤더
    데이터시트와 대조할 것.
    """
    bb = BreadboardRenderer(template_path)
    bb.set_header("실험 1-1: 3-Input OR Gate 회로 결선도",
                  "IC: 74HC32 (Quad 2-Input OR) · 다이오드 보호 330Ω 저항 필수")
    bb.draw_chip("74HC32", 10)
    bb.connect_power(10)
    c = bb.cols['left']

    bb.draw_wire([(c['b'], bb.r_y(10)), (c['a'], bb.r_y(10)), (c['a'], bb.r_y(5)), (95, bb.r_y(5))], (230, 90, 0, 255), width=3)
    bb.draw_badge(12, bb.r_y(5) - 9, "입력 A (1A)", (255, 245, 235, 240), (210, 80, 0, 255))

    bb.draw_wire([(c['b'], bb.r_y(11)), (c['a'] - 16, bb.r_y(11)), (c['a'] - 16, bb.r_y(6)), (95, bb.r_y(6))], (0, 120, 180, 255), width=3)
    bb.draw_badge(12, bb.r_y(6) - 9, "입력 B (1B)", (235, 245, 255, 240), (0, 110, 170, 255))

    bb.draw_wire([(c['b'], bb.r_y(14)), (c['a'], bb.r_y(14)), (c['a'], bb.r_y(7)), (95, bb.r_y(7))], (20, 150, 40, 255), width=3)
    bb.draw_badge(12, bb.r_y(7) - 9, "입력 C (2B)", (235, 255, 235, 240), (20, 130, 30, 255))

    bb.draw_wire([(c['c'], bb.r_y(12)), (c['c'], bb.r_y(13))], (140, 40, 200, 255), width=4)
    bb.draw_badge(c['c'] - 75, bb.r_y(12) + 1, "1단->2단 연결", (255, 245, 255, 230), (130, 30, 190, 255), font=bb.font_kr_sm)

    bb.draw_wire([(c['a'], bb.r_y(12)), (c['a'], bb.r_y(19))], (180, 40, 180, 255), width=2)
    bb.draw_led(c['a'], bb.r_y(19), bb.r_y(20), color_rgb=(210, 140, 0), label="L1 중간 LED (A+B)")
    bb.draw_resistor(c['a'], bb.r_y(20), bb.r_y(22), label="330Ω")
    bb.draw_wire([(c['a'], bb.r_y(22)), (c['gnd'], bb.r_y(22))], (20, 60, 220, 255), width=2)

    bb.draw_wire([(c['c'], bb.r_y(15)), (c['c'], bb.r_y(24))], (220, 20, 70, 255), width=3)
    bb.draw_led(c['c'], bb.r_y(24), bb.r_y(25), color_rgb=(220, 20, 20), label="L2 최종 LED (Y=A+B+C)")
    bb.draw_resistor(c['c'], bb.r_y(25), bb.r_y(27), label="330Ω")
    bb.draw_wire([(c['c'], bb.r_y(27)), (c['gnd'], bb.r_y(27))], (20, 60, 220, 255), width=2)

    bb.connect_unused_inputs([9, 10, 12, 13], 10, bridge_row=29)
    bb.mark_unused_outputs([8, 11], 10)
    bb.export(output_path, max_row=30)


def build_e1_nand(output_path, template_path=None):
    bb = BreadboardRenderer(template_path)
    bb.set_header("실험 1-2: 3-Input NAND Gate 회로 결선도", "IC: 74HC08 (AND 앞단) + 74HC00 (NAND 뒷단) · 330Ω 저항 필수")
    
    c = bb.cols['left']
    r_and = 7
    r_nand = 18
    
    bb.draw_chip("74HC08", r_and)
    bb.connect_power(r_and)
    
    bb.draw_chip("74HC00", r_nand)
    bb.connect_power(r_nand)
    
    bb.draw_wire([(c['b'], bb.r_y(7)), (c['a'], bb.r_y(7)), (c['a'], bb.r_y(4)), (95, bb.r_y(4))], (230, 90, 0, 255), width=3)
    bb.draw_badge(12, bb.r_y(4) - 9, "입력 A (AND 1A)", (255, 245, 235, 240), (210, 80, 0, 255))
    
    bb.draw_wire([(c['b'], bb.r_y(8)), (c['a'] - 16, bb.r_y(8)), (c['a'] - 16, bb.r_y(5)), (95, bb.r_y(5))], (0, 120, 180, 255), width=3)
    bb.draw_badge(12, bb.r_y(5) - 9, "입력 B (AND 1B)", (235, 245, 255, 240), (0, 110, 170, 255))
    
    bb.draw_wire([(c['c'], bb.r_y(9)), (c['c'], bb.r_y(18))], (140, 40, 200, 255), width=3)
    bb.draw_badge(c['c'] - 95, bb.r_y(14) - 8, "A·B 신호 ──>", (255, 245, 255, 230), (130, 30, 190, 255), font=bb.font_kr_sm)
    
    bb.draw_wire([(c['b'], bb.r_y(9)), (c['b'], bb.r_y(14))], (180, 40, 180, 255), width=2)
    bb.draw_led(c['b'], bb.r_y(14), bb.r_y(15), color_rgb=(210, 140, 0), label="L1 중간 LED (A·B)")
    bb.draw_resistor(c['b'], bb.r_y(15), bb.r_y(16), label="330Ω")
    bb.draw_wire([(c['b'], bb.r_y(16)), (c['gnd'], bb.r_y(16))], (20, 60, 220, 255), width=2)
    
    bb.draw_wire([(c['b'], bb.r_y(19)), (c['a'], bb.r_y(19)), (c['a'], bb.r_y(17)), (95, bb.r_y(17))], (20, 150, 40, 255), width=3)
    bb.draw_badge(12, bb.r_y(17) - 9, "입력 C (NAND 1B)", (235, 255, 235, 240), (20, 130, 30, 255))
    
    bb.draw_wire([(c['c'], bb.r_y(20)), (c['c'], bb.r_y(27))], (220, 20, 70, 255), width=3)
    bb.draw_led(c['c'], bb.r_y(27), bb.r_y(28), color_rgb=(220, 20, 20), label="L2 최종 LED (Y=(A·B·C)')")
    bb.draw_resistor(c['c'], bb.r_y(28), bb.r_y(30), label="330Ω")
    bb.draw_wire([(c['c'], bb.r_y(30)), (c['gnd'], bb.r_y(30))], (20, 60, 220, 255), width=2)
    
    bb.connect_unused_inputs([4, 5, 9, 10, 12, 13], r_and, bridge_row=31)
    bb.mark_unused_outputs([6, 8, 11], r_and)
    
    bb.connect_unused_inputs([4, 5, 9, 10, 12, 13], r_nand, bridge_row=31)
    bb.mark_unused_outputs([6, 8, 11], r_nand)
    
    bb.export(output_path, max_row=33)


def build_e1_comb(output_path, template_path=None):
    """실험 2: 복합 논리회로 (74HC04 + 74HC08 + 74HC32) 결선도.
    좌측: 74HC04 (row 7), 74HC08 (row 18)
    우측: 74HC32 (row 10)
    """
    bb = BreadboardRenderer(template_path)
    bb.set_header("실험 2: 복합 논리회로 결선도 (X, Y, Z 동시 관찰)", "IC: 74HC04 (NOT) + 74HC08 (AND) + 74HC32 (OR) · 330Ω 저항 3개 필수")
    
    c_l = bb.cols['left']
    c_r = bb.cols['right']
    r_not = 7
    r_and = 18
    r_or = 10
    
    # 1. 칩 안착 & 전원 결선
    # 74HC04 (NOT) at row 7 (left)
    bb.draw_chip("74HC04", r_not, block='left')
    bb.connect_power(r_not, block='left')
    
    # 74HC08 (AND) at row 18 (left)
    bb.draw_chip("74HC08", r_and, block='left')
    bb.connect_power(r_and, block='left')
    
    # 74HC32 (OR) at row 10 (right)
    bb.draw_chip("74HC32", r_or, block='right')
    # 74HC32 Pin 14 -> right VCC rail (col 'vcc': x=867)
    bb.draw_wire([(c_r['f'], bb.r_y(r_or)), (c_r['vcc'], bb.r_y(r_or))], (220, 20, 20, 255), width=3)
    bb.draw_badge(c_r['vcc'] - 75, bb.r_y(r_or - 2) - 8, "VCC (+5V)", (255, 240, 240, 240), (200, 0, 0, 255), font=bb.font_en_bold)
    
    # 74HC32 Pin 7 -> middle GND rail (col 'mid_gnd': x=529)
    bb.draw_wire([(c_r['e'], bb.r_y(r_or + 6)), (c_r['mid_gnd'], bb.r_y(r_or + 6))], (20, 60, 220, 255), width=3)
    bb.draw_badge(c_r['mid_gnd'] - 55, bb.r_y(r_or + 6) - 8, "GND (0V)", (240, 240, 255, 240), (20, 60, 220, 255), font=bb.font_en_bold)

    # 2. 신호 입력 A, B
    # Input A enters 74HC04 Pin 1 (1A, row 7)
    bb.draw_wire([(c_l['b'], bb.r_y(7)), (c_l['a'], bb.r_y(7)), (c_l['a'], bb.r_y(4)), (95, bb.r_y(4))], (230, 90, 0, 255), width=3)
    bb.draw_badge(12, bb.r_y(4) - 9, "입력 A", (255, 245, 235, 240), (210, 80, 0, 255))
    
    # Input A fans out across header to 74HC32 Pin 1 (row 10) & Pin 4 (row 13) on right
    bb.draw_wire([(c_l['a'], bb.r_y(4)), (c_r['a'], bb.r_y(4)), (c_r['a'], bb.r_y(10))], (230, 90, 0, 255), width=2)
    bb.draw_wire([(c_r['a'], bb.r_y(10)), (c_r['a'], bb.r_y(13))], (230, 90, 0, 255), width=2)
    
    # Input B enters 74HC08 Pin 2 (1B, row 19) & 74HC32 Pin 5 (2B, row 14)
    bb.draw_wire([(c_l['b'], bb.r_y(19)), (c_l['a'] - 16, bb.r_y(19)), (c_l['a'] - 16, bb.r_y(5)), (95, bb.r_y(5))], (0, 120, 180, 255), width=3)
    bb.draw_badge(12, bb.r_y(5) - 9, "입력 B", (235, 245, 255, 240), (0, 110, 170, 255))
    bb.draw_wire([(c_l['a'] - 16, bb.r_y(5)), (c_r['b'], bb.r_y(5)), (c_r['b'], bb.r_y(14))], (0, 120, 180, 255), width=2)
    
    # 3. 신호 체인:
    # A' = 74HC04 Pin 2 (row 8) -> 74HC08 Pin 1 (row 18)
    bb.draw_wire([(c_l['c'], bb.r_y(8)), (c_l['c'], bb.r_y(18))], (180, 50, 20, 255), width=3)
    bb.draw_badge(c_l['c'] - 75, bb.r_y(12) - 8, "A' 신호", (255, 240, 235, 230), (180, 50, 20, 255), font=bb.font_kr_sm)
    
    # A'·B = 74HC08 Pin 3 (row 20) -> 74HC04 Pin 3 (row 9)
    bb.draw_wire([(c_l['d'], bb.r_y(20)), (c_l['d'], bb.r_y(9))], (140, 40, 200, 255), width=3)
    bb.draw_badge(c_l['d'] - 80, bb.r_y(15) - 8, "A'·B 신호", (255, 245, 255, 230), (130, 30, 190, 255), font=bb.font_kr_sm)
    
    # Z = (A'·B)' = 74HC04 Pin 4 (row 10) -> Output Z LED & to 74HC32 Pin 2 (row 11)
    bb.draw_wire([(c_l['b'], bb.r_y(10)), (c_l['b'], bb.r_y(26))], (200, 30, 100, 255), width=3)
    bb.draw_wire([(c_l['b'], bb.r_y(10)), (c_r['c'], bb.r_y(10)), (c_r['c'], bb.r_y(11))], (200, 30, 100, 255), width=2)
    
    # Z LED at row 26 (left)
    bb.draw_led(c_l['b'], bb.r_y(26), bb.r_y(27), color_rgb=(210, 20, 80), label="Z 출력 LED (Z=(A'·B)')")
    bb.draw_resistor(c_l['b'], bb.r_y(27), bb.r_y(29), label="330Ω")
    bb.draw_wire([(c_l['b'], bb.r_y(29)), (c_l['gnd'], bb.r_y(29))], (20, 60, 220, 255), width=2)
    
    # X = A + Z: 74HC32 Pin 3 (row 12) -> X LED
    bb.draw_wire([(c_r['d'], bb.r_y(12)), (c_r['d'], bb.r_y(22))], (220, 120, 0, 255), width=3)
    bb.draw_led(c_r['d'], bb.r_y(22), bb.r_y(23), color_rgb=(220, 120, 0), label="X 출력 LED (X=A+Z)")
    bb.draw_resistor(c_r['d'], bb.r_y(23), bb.r_y(25), label="330Ω")
    bb.draw_wire([(c_r['d'], bb.r_y(25)), (c_r['gnd'], bb.r_y(25))], (20, 60, 220, 255), width=2)
    
    # Y = A + B: 74HC32 Pin 6 (row 15) -> Y LED
    bb.draw_wire([(c_r['c'], bb.r_y(15)), (c_r['c'], bb.r_y(27))], (20, 150, 50, 255), width=3)
    bb.draw_led(c_r['c'], bb.r_y(27), bb.r_y(28), color_rgb=(20, 150, 50), label="Y 출력 LED (Y=A+B)")
    bb.draw_resistor(c_r['c'], bb.r_y(28), bb.r_y(30), label="330Ω")
    bb.draw_wire([(c_r['c'], bb.r_y(30)), (c_r['gnd'], bb.r_y(30))], (20, 60, 220, 255), width=2)
    
    # 4. 미사용 핀 안전 처리 (동선 정리)
    # 74HC04: 미사용 입력 (5, 9, 11, 13) -> GND, 미사용 출력 (6, 8, 10, 12) -> NC
    bb.connect_unused_inputs([5, 9, 11, 13], r_not, block='left', bridge_row=31)
    bb.mark_unused_outputs([6, 8, 10, 12], r_not, block='left')
    
    # 74HC08: 미사용 입력 (4, 5, 9, 10, 12, 13) -> GND, 미사용 출력 (6, 8, 11) -> NC
    bb.connect_unused_inputs([4, 5, 9, 10, 12, 13], r_and, block='left', bridge_row=31)
    bb.mark_unused_outputs([6, 8, 11], r_and, block='left')
    
    # 74HC32 (우측 칩): 미사용 입력 (9, 10, 12, 13) -> 우측 GND 레일(gnd: x=837)
    for p in [9, 10, 12, 13]:
        r = r_or + (14 - p)
        bb.draw_wire([(c_r['g'], bb.r_y(r)), (c_r['gnd'], bb.r_y(r))], (20, 60, 220, 255), width=2)
    bb.draw_badge(c_r['f'] + 20, bb.r_y(r_or + 1) - 8, "미사용 입력 (9,10,12,13) ──> GND", (240, 245, 255, 240), (20, 60, 200, 255))
    
    # 74HC32 미사용 출력 (8, 11) -> 개방(NC)
    bb.draw_badge(c_r['f'] + 20, bb.r_y(r_or + 3) - 8, "Pin 11: NC", (250, 250, 250, 240), (130, 60, 60, 255), font=bb.font_kr_sm)
    bb.draw_badge(c_r['f'] + 20, bb.r_y(r_or + 6) - 8, "Pin 8: NC", (250, 250, 250, 240), (130, 60, 60, 255), font=bb.font_kr_sm)
    bb.draw_badge(c_r['f'] + 20, bb.r_y(r_or + 5) - 8, "미사용 출력 (8, 11) ──> 개방(NC)", (255, 240, 240, 240), (180, 40, 40, 255))

    # 5. 레일 브리지 — 이 그림은 분리된 레일 모듈 넷을 쓴다
    #    GND: 좌(163) · 중앙좌(458) · 중앙우(529) · 우(837) 를 31행에서 잇는다.
    #         잇지 않으면 우측 74HC32 의 7번 핀(중앙우)과 좌측 칩들의 7번 핀(좌)이
    #         서로 다른 스트립에 있어 한쪽이 접지되지 않는다
    #    VCC: 좌측 칩들은 중앙좌(488), 74HC32 는 우(867) 에서 받으므로 33행에서 잇는다
    bb.bridge_rails(c_l['mid_gnd'], c_r['mid_gnd'], 31, kind='gnd', label="")
    bb.bridge_rails(c_r['mid_gnd'], c_r['gnd'], 31, kind='gnd')
    bb.bridge_rails(c_l['mid_vcc'], c_r['vcc'], 33, kind='vcc')

    bb.export(output_path, max_row=34)


def build_e2_inv(output_path, template_path=None):
    """실험 2-1: Inverter 입출력 특성 회로 (VTC 곡선) 결선도"""
    bb = BreadboardRenderer(template_path)
    bb.set_header("실험 2-1: Inverter 입출력 특성 회로 (VTC 곡선)", "IC: 74HC04 (Hex Inverter) · 오실로스코프 X-Y 모드 (CH1=VIN, CH2=VOUT)")
    
    r_chip = 10
    c = bb.cols['left']
    
    # 1. 칩 안착 & 전원 결선
    bb.draw_chip("74HC04", r_chip, block='left')
    bb.connect_power(r_chip, block='left')
    
    # 2. 신호 입력: Pin 1 (1A, row 10)
    # 함수발생기 입력 (0~5V 사인파, 5Vpp, Offset 2.5V)
    bb.draw_wire([(c['b'], bb.r_y(10)), (c['a'], bb.r_y(10)), (c['a'], bb.r_y(5)), (95, bb.r_y(5))], (230, 90, 0, 255), width=3)
    bb.draw_badge(12, bb.r_y(5) - 9, "함수발생기 VIN (5Vpp, Offset 2.5V)", (255, 245, 235, 240), (210, 80, 0, 255))
    
    # CH1 프로브 팁 (가로축 VIN 관측)
    bb.draw_wire([(c['a'], bb.r_y(7)), (95, bb.r_y(7))], (230, 90, 0, 255), width=2)
    bb.draw_badge(12, bb.r_y(7) - 9, "CH1 프로브 팁 (X축 = VIN)", (255, 240, 225, 245), (190, 70, 0, 255), font=bb.font_kr_bold)
    
    # 3. 신호 출력: Pin 2 (1Y, row 11)
    # CH2 프로브 팁 (세로축 VOUT 관측, 부하 없음)
    bb.draw_wire([(c['b'], bb.r_y(11)), (c['a'] - 16, bb.r_y(11)), (c['a'] - 16, bb.r_y(19)), (95, bb.r_y(19))], (0, 120, 180, 255), width=3)
    bb.draw_badge(12, bb.r_y(19) - 9, "CH2 프로브 팁 (Y축 = VOUT)", (235, 245, 255, 245), (0, 110, 170, 255), font=bb.font_kr_bold)
    
    # 공통 접지 안내 배지
    bb.draw_badge(c['gnd'] - 100, bb.r_y(22) - 9, "★ 공통 GND: 함수발생기 접지 + 프로브 접지 클립 결선", (240, 240, 255, 245), (20, 60, 220, 255))
    bb.draw_wire([(c['gnd'], bb.r_y(22)), (c['gnd'] - 10, bb.r_y(22))], (20, 60, 220, 255), width=2)

    # 4. 미사용 입력핀 처리 (교안 p8 엄격 준수)
    # Pin 3 (row 12), Pin 5 (row 14) -> GND
    bb.draw_wire([(c['d'], bb.r_y(12)), (c['gnd'], bb.r_y(12))], (20, 60, 220, 255), width=2)
    bb.draw_wire([(c['d'], bb.r_y(14)), (c['gnd'], bb.r_y(14))], (20, 60, 220, 255), width=2)
    bb.draw_badge(c['gnd'] - 85, bb.r_y(13) - 9, "미사용 입력 (3, 5) ──> GND", (240, 245, 255, 240), (20, 60, 200, 255))
    
    # Pin 9 (row 15), Pin 11 (row 13), Pin 13 (row 11) -> VCC (mid_vcc)
    bb.draw_wire([(c['g'], bb.r_y(15)), (c['mid_vcc'], bb.r_y(15))], (220, 20, 20, 255), width=2)
    bb.draw_wire([(c['g'], bb.r_y(13)), (c['mid_vcc'], bb.r_y(13))], (220, 20, 20, 255), width=2)
    bb.draw_wire([(c['g'], bb.r_y(11)), (c['mid_vcc'], bb.r_y(11))], (220, 20, 20, 255), width=2)
    bb.draw_badge(530, bb.r_y(11) - 9, "미사용 입력 (9, 11, 13) ──> VCC 풀업", (255, 240, 240, 240), (200, 20, 20, 255))
    
    # 5. 미사용 출력핀 처리: 4, 6, 8, 10, 12 -> 개방(NC)
    bb.draw_badge(c['d'] - 38, bb.r_y(13) - 7, "Pin 4: NC", (250, 250, 250, 240), (130, 60, 60, 255), font=bb.font_kr_sm)
    bb.draw_badge(c['d'] - 38, bb.r_y(15) - 7, "Pin 6: NC", (250, 250, 250, 240), (130, 60, 60, 255), font=bb.font_kr_sm)
    bb.draw_badge(c['f'] + 18, bb.r_y(16) - 7, "Pin 8: NC", (250, 250, 250, 240), (130, 60, 60, 255), font=bb.font_kr_sm)
    bb.draw_badge(c['f'] + 18, bb.r_y(14) - 7, "Pin 10: NC", (250, 250, 250, 240), (130, 60, 60, 255), font=bb.font_kr_sm)
    bb.draw_badge(c['f'] + 18, bb.r_y(12) - 7, "Pin 12: NC", (250, 250, 250, 240), (130, 60, 60, 255), font=bb.font_kr_sm)
    bb.draw_badge(530, bb.r_y(15) - 9, "미사용 출력 (4, 6, 8, 10, 12) ──> 개방(NC) 필수", (255, 245, 245, 240), (180, 40, 40, 255))
    
    # 요약 노트
    bb.draw_badge(12, bb.r_y(25) - 9, "※ X-Y 모드 주의: CH1 = 가로축(VIN), CH2 = 세로축(VOUT) 배정 필수 (반대 연결 시 전치 그래프)", (255, 255, 235, 250), (140, 90, 10, 255), font=bb.font_kr_sm)

    bb.export(output_path, max_row=27)


def build_e2_schmitt(output_path, template_path=None):
    """실험 2-2: Schmitt-trigger 입출력 특성 회로 (Hysteresis) 결선도"""
    bb = BreadboardRenderer(template_path)
    bb.set_header("실험 2-2: Schmitt-trigger 입출력 특성 회로 (Hysteresis)", "IC: 74HC14 (Schmitt Inverter) · X-Y 모드 히스테리시스 루프(VT+, VT-) 관찰")
    
    r_chip = 10
    c = bb.cols['left']
    
    # 1. 칩 안착 & 전원 결선
    bb.draw_chip("74HC14", r_chip, block='left')
    bb.connect_power(r_chip, block='left')
    
    # 2. 신호 입력: Pin 1 (1A, row 10)
    # 함수발생기 입력 (0~5V 사인파, 5Vpp, Offset 2.5V)
    bb.draw_wire([(c['b'], bb.r_y(10)), (c['a'], bb.r_y(10)), (c['a'], bb.r_y(5)), (95, bb.r_y(5))], (230, 90, 0, 255), width=3)
    bb.draw_badge(12, bb.r_y(5) - 9, "함수발생기 VIN (5Vpp, Offset 2.5V)", (255, 245, 235, 240), (210, 80, 0, 255))
    
    # CH1 프로브 팁 (가로축 VIN 관측)
    bb.draw_wire([(c['a'], bb.r_y(7)), (95, bb.r_y(7))], (230, 90, 0, 255), width=2)
    bb.draw_badge(12, bb.r_y(7) - 9, "CH1 프로브 팁 (X축 = VIN)", (255, 240, 225, 245), (190, 70, 0, 255), font=bb.font_kr_bold)
    
    # 3. 신호 출력: Pin 2 (1Y, row 11)
    # CH2 프로브 팁 (세로축 VOUT 관측)
    bb.draw_wire([(c['b'], bb.r_y(11)), (c['a'] - 16, bb.r_y(11)), (c['a'] - 16, bb.r_y(19)), (95, bb.r_y(19))], (0, 120, 180, 255), width=3)
    bb.draw_badge(12, bb.r_y(19) - 9, "CH2 프로브 팁 (Y축 = VOUT)", (235, 245, 255, 245), (0, 110, 170, 255), font=bb.font_kr_bold)
    
    # 공통 접지 안내 배지
    bb.draw_badge(c['gnd'] - 100, bb.r_y(22) - 9, "★ 공통 GND: 함수발생기 접지 + 프로브 접지 클립 결선", (240, 240, 255, 245), (20, 60, 220, 255))
    bb.draw_wire([(c['gnd'], bb.r_y(22)), (c['gnd'] - 10, bb.r_y(22))], (20, 60, 220, 255), width=2)

    # 4. 미사용 입력핀 처리
    bb.draw_wire([(c['d'], bb.r_y(12)), (c['gnd'], bb.r_y(12))], (20, 60, 220, 255), width=2)
    bb.draw_wire([(c['d'], bb.r_y(14)), (c['gnd'], bb.r_y(14))], (20, 60, 220, 255), width=2)
    bb.draw_badge(c['gnd'] - 85, bb.r_y(13) - 9, "미사용 입력 (3, 5) ──> GND", (240, 245, 255, 240), (20, 60, 200, 255))
    
    bb.draw_wire([(c['g'], bb.r_y(15)), (c['mid_vcc'], bb.r_y(15))], (220, 20, 20, 255), width=2)
    bb.draw_wire([(c['g'], bb.r_y(13)), (c['mid_vcc'], bb.r_y(13))], (220, 20, 20, 255), width=2)
    bb.draw_wire([(c['g'], bb.r_y(11)), (c['mid_vcc'], bb.r_y(11))], (220, 20, 20, 255), width=2)
    bb.draw_badge(530, bb.r_y(11) - 9, "미사용 입력 (9, 11, 13) ──> VCC 풀업", (255, 240, 240, 240), (200, 20, 20, 255))
    
    # 5. 미사용 출력핀 처리
    bb.draw_badge(c['d'] - 38, bb.r_y(13) - 7, "Pin 4: NC", (250, 250, 250, 240), (130, 60, 60, 255), font=bb.font_kr_sm)
    bb.draw_badge(c['d'] - 38, bb.r_y(15) - 7, "Pin 6: NC", (250, 250, 250, 240), (130, 60, 60, 255), font=bb.font_kr_sm)
    bb.draw_badge(c['f'] + 18, bb.r_y(16) - 7, "Pin 8: NC", (250, 250, 250, 240), (130, 60, 60, 255), font=bb.font_kr_sm)
    bb.draw_badge(c['f'] + 18, bb.r_y(14) - 7, "Pin 10: NC", (250, 250, 250, 240), (130, 60, 60, 255), font=bb.font_kr_sm)
    bb.draw_badge(c['f'] + 18, bb.r_y(12) - 7, "Pin 12: NC", (250, 250, 250, 240), (130, 60, 60, 255), font=bb.font_kr_sm)
    bb.draw_badge(530, bb.r_y(15) - 9, "미사용 출력 (4, 6, 8, 10, 12) ──> 개방(NC) 필수", (255, 245, 245, 240), (180, 40, 40, 255))
    
    # 슈미트 트리거 안내 노트
    bb.draw_badge(12, bb.r_y(25) - 9, "※ 74HC04와 결선 동일 / IC만 74HC14로 교체 (전원 OFF 상태에서 교체 필수)", (255, 240, 240, 250), (190, 30, 30, 255), font=bb.font_kr_bold)
    bb.draw_badge(12, bb.r_y(27) - 9, "측정 목표: 상향 임계전압 VT+(~2.9V), 하향 임계전압 VT-(~2.1V), 히스테리시스 루프 폭 ΔVT 실측", (245, 250, 255, 250), (20, 70, 160, 255), font=bb.font_kr_sm)

    bb.export(output_path, max_row=29)


def build_e2_rn(output_path, template_path=None):
    """실험 2-3 (1): CMOS DC 특성 측정 — Rn (NMOS 온저항) 결선도"""
    bb = BreadboardRenderer(template_path)
    bb.set_header("실험 2-3 (1): CMOS DC 특성 측정 — Rn (NMOS 온저항)", "IC: 74HC04 · 부하저항 R1=1kΩ (VCC 풀업) · NMOS 도통/Sinking 상태 (출력 LOW)")
    
    r_chip = 10
    c = bb.cols['left']
    
    # 1. 칩 안착 & 전원 결선
    bb.draw_chip("74HC04", r_chip, block='left')
    bb.connect_power(r_chip, block='left')
    
    # 2. 입력 Pin 1 -> VCC 직결 (입력 HIGH 고정 -> NMOS ON, 출력 LOW)
    bb.draw_wire([(c['b'], bb.r_y(10)), (c['a'], bb.r_y(10)), (c['a'], bb.r_y(7)), (c['vcc'], bb.r_y(7))], (220, 20, 20, 255), width=3)
    bb.draw_badge(12, bb.r_y(7) - 9, "입력 Pin 1 ──> VCC 직결 (HIGH 고정)", (255, 240, 240, 245), (200, 20, 20, 255), font=bb.font_kr_bold)
    
    # 3. 부하 저항 R1 (1kΩ) 결선: VCC 풀업 (VCC ──> R1 ──> Pin 2)
    # 안전 설계: 칩 핀(row 10~16)과 간섭이 없는 빈 행 row 19~23에 R1 배치
    r_res_top = 19
    r_res_bot = 23
    bb.draw_resistor(c['b'], bb.r_y(r_res_top), bb.r_y(r_res_bot), label="R1 1kΩ")
    
    # Pin 2 (row 11, col b) -> R1 상단(row 19, col b) 연결 점퍼선
    bb.draw_wire([(c['b'], bb.r_y(11)), (c['b'] - 10, bb.r_y(11)), (c['b'] - 10, bb.r_y(r_res_top)), (c['b'], bb.r_y(r_res_top))], (180, 50, 180, 255), width=3)
    bb.draw_badge(12, bb.r_y(11) - 9, "출력 Pin 2 (전류 Sinking)", (255, 245, 255, 240), (140, 30, 160, 255), font=bb.font_kr_bold)
    
    # R1 하단(row 23, col b) -> VCC 레일 연결 (풀업)
    bb.draw_wire([(c['b'], bb.r_y(r_res_bot)), (c['vcc'], bb.r_y(r_res_bot))], (220, 20, 20, 255), width=3)
    bb.draw_badge(c['vcc'] - 75, bb.r_y(r_res_bot) - 8, "VCC 풀업", (255, 240, 240, 240), (200, 20, 20, 255), font=bb.font_kr_sm)

    # 4. DMM 계측 접점 가이드
    # S1: 실저항 측정 안내
    bb.draw_badge(12, bb.r_y(4) - 9, "[S1] R1 실저항: 회로에 꽂기 전 DMM 저항(Ω) 모드로 단독 실측", (255, 255, 240, 245), (140, 100, 10, 255), font=bb.font_kr_sm)
    # S2: VOL 측정 (Pin 2 vs GND)
    bb.draw_wire([(c['a'], bb.r_y(r_res_top)), (95, bb.r_y(r_res_top))], (0, 120, 180, 255), width=2)
    bb.draw_badge(12, bb.r_y(r_res_top) - 9, "[S2] DMM(+) ──> Pin 2 (VOL = Vout 실측)", (235, 245, 255, 245), (0, 100, 180, 255), font=bb.font_kr_bold)
    # S3: VR1 양단 전압 측정 (VCC vs Pin 2)
    bb.draw_badge(12, bb.r_y(26) - 9, "[S3] DMM 양단을 R1 양단에 연결 ──> VR1 전압 실측 (I_OL 계산용)", (240, 255, 240, 245), (20, 130, 40, 255), font=bb.font_kr_sm)
    
    # 계산식 공식 배지
    bb.draw_badge(12, bb.r_y(28) - 9, "★ Rn 계산식: I_OL = VR1 / R1 = (VCC - VOL) / R1,   Rn = VOL / I_OL  (NMOS 온저항 규격: 80~130Ω)", (255, 250, 235, 250), (160, 80, 0, 255), font=bb.font_kr_bold)

    # 5. 미사용 입력/출력 처리
    bb.draw_wire([(c['d'], bb.r_y(12)), (c['gnd'], bb.r_y(12))], (20, 60, 220, 255), width=2)
    bb.draw_wire([(c['d'], bb.r_y(14)), (c['gnd'], bb.r_y(14))], (20, 60, 220, 255), width=2)
    bb.draw_badge(c['gnd'] - 85, bb.r_y(13) - 9, "미사용 입력 (3, 5) ──> GND", (240, 245, 255, 240), (20, 60, 200, 255))
    
    bb.draw_wire([(c['g'], bb.r_y(15)), (c['mid_vcc'], bb.r_y(15))], (220, 20, 20, 255), width=2)
    bb.draw_wire([(c['g'], bb.r_y(13)), (c['mid_vcc'], bb.r_y(13))], (220, 20, 20, 255), width=2)
    bb.draw_wire([(c['g'], bb.r_y(11)), (c['mid_vcc'], bb.r_y(11))], (220, 20, 20, 255), width=2)
    bb.draw_badge(530, bb.r_y(11) - 9, "미사용 입력 (9, 11, 13) ──> VCC", (255, 240, 240, 240), (200, 20, 20, 255))
    
    bb.draw_badge(c['d'] - 38, bb.r_y(13) - 7, "Pin 4: NC", (250, 250, 250, 240), (130, 60, 60, 255), font=bb.font_kr_sm)
    bb.draw_badge(c['d'] - 38, bb.r_y(15) - 7, "Pin 6: NC", (250, 250, 250, 240), (130, 60, 60, 255), font=bb.font_kr_sm)
    bb.draw_badge(c['f'] + 18, bb.r_y(16) - 7, "Pin 8: NC", (250, 250, 250, 240), (130, 60, 60, 255), font=bb.font_kr_sm)
    bb.draw_badge(c['f'] + 18, bb.r_y(14) - 7, "Pin 10: NC", (250, 250, 250, 240), (130, 60, 60, 255), font=bb.font_kr_sm)
    bb.draw_badge(c['f'] + 18, bb.r_y(12) - 7, "Pin 12: NC", (250, 250, 250, 240), (130, 60, 60, 255), font=bb.font_kr_sm)
    bb.draw_badge(530, bb.r_y(15) - 9, "미사용 출력 (4, 6, 8, 10, 12) ──> NC (개방)", (255, 245, 245, 240), (180, 40, 40, 255))

    bb.export(output_path, max_row=30)


def build_e2_rp(output_path, template_path=None):
    """실험 2-3 (2): CMOS DC 특성 측정 — Rp (PMOS 온저항) 결선도"""
    bb = BreadboardRenderer(template_path)
    bb.set_header("실험 2-3 (2): CMOS DC 특성 측정 — Rp (PMOS 온저항)", "IC: 74HC04 · 부하저항 R1=1kΩ (GND 풀다운) · PMOS 도통/Sourcing 상태 (출력 HIGH)")
    
    r_chip = 10
    c = bb.cols['left']
    
    # 1. 칩 안착 & 전원 결선
    bb.draw_chip("74HC04", r_chip, block='left')
    bb.connect_power(r_chip, block='left')
    
    # 2. 입력 Pin 1 -> GND 직결 (입력 LOW 고정 -> PMOS ON, 출력 HIGH)
    bb.draw_wire([(c['b'], bb.r_y(10)), (c['a'], bb.r_y(10)), (c['a'], bb.r_y(8)), (c['gnd'], bb.r_y(8))], (20, 60, 220, 255), width=3)
    bb.draw_badge(12, bb.r_y(8) - 9, "입력 Pin 1 ──> GND 직결 (LOW 고정)", (240, 240, 255, 245), (20, 60, 220, 255), font=bb.font_kr_bold)
    
    # 3. 부하 저항 R1 (1kΩ) 결선: GND 풀다운 (Pin 2 ──> R1 ──> GND)
    # 안전 설계: 칩 핀(row 10~16)과 간섭이 없는 빈 행 row 19~23에 R1 배치
    r_res_top = 19
    r_res_bot = 23
    bb.draw_resistor(c['b'], bb.r_y(r_res_top), bb.r_y(r_res_bot), label="R1 1kΩ")
    
    # Pin 2 (row 11, col b) -> R1 상단(row 19, col b) 연결 점퍼선
    bb.draw_wire([(c['b'], bb.r_y(11)), (c['b'] - 10, bb.r_y(11)), (c['b'] - 10, bb.r_y(r_res_top)), (c['b'], bb.r_y(r_res_top))], (180, 50, 180, 255), width=3)
    bb.draw_badge(12, bb.r_y(11) - 9, "출력 Pin 2 (전류 Sourcing)", (255, 245, 255, 240), (140, 30, 160, 255), font=bb.font_kr_bold)
    
    # R1 하단(row 23, col b) -> GND 레일 연결 (풀다운)
    bb.draw_wire([(c['b'], bb.r_y(r_res_bot)), (c['gnd'], bb.r_y(r_res_bot))], (20, 60, 220, 255), width=3)
    bb.draw_badge(c['gnd'] - 75, bb.r_y(r_res_bot) - 8, "GND 풀다운", (240, 240, 255, 240), (20, 60, 220, 255), font=bb.font_kr_sm)

    # 4. DMM 계측 접점 가이드
    # S1: 실저항 측정 안내
    bb.draw_badge(12, bb.r_y(4) - 9, "[S1] R1 실저항: 회로에 꽂기 전 DMM 저항(Ω) 모드로 단독 실측", (255, 255, 240, 245), (140, 100, 10, 255), font=bb.font_kr_sm)
    # S2: VOH 측정 (Pin 2 vs GND)
    bb.draw_wire([(c['a'], bb.r_y(r_res_top)), (95, bb.r_y(r_res_top))], (0, 120, 180, 255), width=2)
    bb.draw_badge(12, bb.r_y(r_res_top) - 9, "[S2] DMM(+) ──> Pin 2 (VOH = VR1 실측)", (235, 245, 255, 245), (0, 100, 180, 255), font=bb.font_kr_bold)
    # S3: VCC 정밀 실측 (VCC vs GND)
    bb.draw_badge(12, bb.r_y(26) - 9, "[S3] DMM으로 전원 전압 VCC 정밀 실측 ──> 분자 (VCC - VOH) 정밀 계산용", (255, 240, 240, 245), (200, 30, 30, 255), font=bb.font_kr_sm)
    
    # 계산식 공식 배지
    bb.draw_badge(12, bb.r_y(28) - 9, "★ Rp 계산식: I_OH = VOH / R1,   Rp = (VCC - VOH) / I_OH  (PMOS 온저항 규격: 150~250Ω)", (255, 250, 235, 250), (160, 80, 0, 255), font=bb.font_kr_bold)

    # 5. 미사용 입력/출력 처리
    bb.draw_wire([(c['d'], bb.r_y(12)), (c['gnd'], bb.r_y(12))], (20, 60, 220, 255), width=2)
    bb.draw_wire([(c['d'], bb.r_y(14)), (c['gnd'], bb.r_y(14))], (20, 60, 220, 255), width=2)
    bb.draw_badge(c['gnd'] - 85, bb.r_y(13) - 9, "미사용 입력 (3, 5) ──> GND", (240, 245, 255, 240), (20, 60, 200, 255))
    
    bb.draw_wire([(c['g'], bb.r_y(15)), (c['mid_vcc'], bb.r_y(15))], (220, 20, 20, 255), width=2)
    bb.draw_wire([(c['g'], bb.r_y(13)), (c['mid_vcc'], bb.r_y(13))], (220, 20, 20, 255), width=2)
    bb.draw_wire([(c['g'], bb.r_y(11)), (c['mid_vcc'], bb.r_y(11))], (220, 20, 20, 255), width=2)
    bb.draw_badge(530, bb.r_y(11) - 9, "미사용 입력 (9, 11, 13) ──> VCC", (255, 240, 240, 240), (200, 20, 20, 255))
    
    bb.draw_badge(c['d'] - 38, bb.r_y(13) - 7, "Pin 4: NC", (250, 250, 250, 240), (130, 60, 60, 255), font=bb.font_kr_sm)
    bb.draw_badge(c['d'] - 38, bb.r_y(15) - 7, "Pin 6: NC", (250, 250, 250, 240), (130, 60, 60, 255), font=bb.font_kr_sm)
    bb.draw_badge(c['f'] + 18, bb.r_y(16) - 7, "Pin 8: NC", (250, 250, 250, 240), (130, 60, 60, 255), font=bb.font_kr_sm)
    bb.draw_badge(c['f'] + 18, bb.r_y(14) - 7, "Pin 10: NC", (250, 250, 250, 240), (130, 60, 60, 255), font=bb.font_kr_sm)
    bb.draw_badge(c['f'] + 18, bb.r_y(12) - 7, "Pin 12: NC", (250, 250, 250, 240), (130, 60, 60, 255), font=bb.font_kr_sm)
    bb.draw_badge(530, bb.r_y(15) - 9, "미사용 출력 (4, 6, 8, 10, 12) ──> NC (개방)", (255, 245, 245, 240), (180, 40, 40, 255))

    bb.export(output_path, max_row=30)


def build_e2_tpd(output_path, template_path=None):
    """실험 2-4: CMOS AC 특성 측정 — 전파지연(tpd) 체인 결선도 (U1 6단계 체인 + U2 부하 칩)"""
    bb = BreadboardRenderer(template_path)
    bb.set_header("실험 2-4: CMOS AC 특성 측정 — 전파지연(tpd) 체인", "IC: 74HC04 x 2개 · U1 (6단 직렬 지연 체인) + U2 (부하 인버터) · 4단 지연(Δt) 측정")
    
    r_u1 = 8
    r_u2 = 8
    c_l = bb.cols['left']
    c_r = bb.cols['right']
    
    # 1. 칩 안착 & 전원 결선
    # U1 (좌측)
    bb.draw_chip("74HC04", r_u1, block='left')
    bb.connect_power(r_u1, block='left')
    bb.draw_badge(c_l['chip_x1'] - 5, bb.r_y(r_u1 - 1) - 8, "U1: 6단 지연 체인", (245, 245, 255, 240), (30, 50, 150, 255), font=bb.font_kr_bold)
    
    # U2 (우측)
    bb.draw_chip("74HC04", r_u2, block='right')
    # U2 전원: Pin 14 -> right VCC rail (col 'vcc': 867), Pin 7 -> middle GND rail (col 'mid_gnd': 529)
    bb.draw_wire([(c_r['f'], bb.r_y(r_u2)), (c_r['vcc'], bb.r_y(r_u2))], (220, 20, 20, 255), width=3)
    bb.draw_badge(c_r['vcc'] - 75, bb.r_y(r_u2 - 2) - 8, "VCC (+5V)", (255, 240, 240, 240), (200, 0, 0, 255), font=bb.font_en_bold)
    
    bb.draw_wire([(c_r['e'], bb.r_y(r_u2 + 6)), (c_r['mid_gnd'], bb.r_y(r_u2 + 6))], (20, 60, 220, 255), width=3)
    bb.draw_badge(c_r['mid_gnd'] - 55, bb.r_y(r_u2 + 6) - 8, "GND (0V)", (240, 240, 255, 240), (20, 60, 220, 255), font=bb.font_en_bold)
    bb.draw_badge(c_r['chip_x1'] - 5, bb.r_y(r_u2 - 1) - 8, "U2: 부하 인버터", (255, 245, 245, 240), (160, 40, 40, 255), font=bb.font_kr_bold)

    # 2. 함수발생기 입력: U1 Pin 1 (row 8, col b)
    bb.draw_wire([(c_l['b'], bb.r_y(8)), (c_l['a'], bb.r_y(8)), (c_l['a'], bb.r_y(4)), (95, bb.r_y(4))], (230, 90, 0, 255), width=3)
    bb.draw_badge(12, bb.r_y(4) - 9, "함수발생기: 1MHz 구형파 (5Vpp, Offset 2.5V)", (255, 245, 235, 240), (210, 80, 0, 255), font=bb.font_kr_bold)

    # 3. U1 지연 체인 결선 (1단 -> 2단 -> 3단 -> 4단 -> 5단 -> 6단)
    # 단 1->2: Pin 2 (row 9, col c) -> Pin 3 (row 10, col c)
    bb.draw_wire([(c_l['c'], bb.r_y(9)), (c_l['c'], bb.r_y(10))], (140, 40, 200, 255), width=4)
    bb.draw_badge(c_l['c'] - 60, bb.r_y(9) + 2, "단1->2", (255, 245, 255, 230), (130, 30, 190, 255), font=bb.font_kr_sm)
    
    # 단 2->3: Pin 4 (row 11, col c) -> Pin 5 (row 12, col c)
    bb.draw_wire([(c_l['c'], bb.r_y(11)), (c_l['c'], bb.r_y(12))], (140, 40, 200, 255), width=4)
    bb.draw_badge(c_l['c'] - 60, bb.r_y(11) + 2, "단2->3", (255, 245, 255, 230), (130, 30, 190, 255), font=bb.font_kr_sm)
    
    # CH1 프로브: U1 Pin 4 (row 11, col b) -> 기준 신호 (2단 출력!)
    bb.draw_wire([(c_l['b'], bb.r_y(11)), (c_l['a'] - 16, bb.r_y(11)), (c_l['a'] - 16, bb.r_y(18)), (95, bb.r_y(18))], (0, 120, 180, 255), width=3)
    bb.draw_badge(12, bb.r_y(18) - 9, "CH1 프로브 팁: U1 Pin 4 (기준 파형, 2단 출력)", (235, 245, 255, 245), (0, 110, 170, 255), font=bb.font_kr_bold)

    # ★ 단 3->4: Pin 6 (row 13, col d) -> Pin 13 (row 9, col g) [대각선 크로스 점퍼!]
    bb.draw_wire([
        (c_l['d'], bb.r_y(13)),
        (c_l['d'], bb.r_y(16)),
        (c_l['g'], bb.r_y(16)),
        (c_l['g'], bb.r_y(9))
    ], (220, 100, 0, 255), width=3)
    bb.draw_badge(c_l['chip_x1'] - 15, bb.r_y(16) - 9, "★ 크로스 점퍼 (Pin 6 ──> Pin 13, 단 3->4)", (255, 245, 235, 245), (200, 80, 0, 255), font=bb.font_kr_bold)

    # 단 4->5: Pin 12 (row 10, col h) -> Pin 11 (row 11, col h)
    bb.draw_wire([(c_l['h'], bb.r_y(10)), (c_l['h'], bb.r_y(11))], (140, 40, 200, 255), width=4)
    bb.draw_badge(c_l['h'] + 8, bb.r_y(10) + 2, "단4->5", (255, 245, 255, 230), (130, 30, 190, 255), font=bb.font_kr_sm)
    
    # 단 5->6: Pin 10 (row 12, col h) -> Pin 9 (row 13, col h)
    bb.draw_wire([(c_l['h'], bb.r_y(12)), (c_l['h'], bb.r_y(13))], (140, 40, 200, 255), width=4)
    bb.draw_badge(c_l['h'] + 8, bb.r_y(12) + 2, "단5->6", (255, 245, 255, 230), (130, 30, 190, 255), font=bb.font_kr_sm)

    # 4. 체인 최종 출력: U1 Pin 8 (row 14, col g)
    # -> CH2 프로브 팁 (지연 파형, 6단 출력!)
    bb.draw_wire([(c_l['g'], bb.r_y(14)), (c_l['g'], bb.r_y(20)), (95, bb.r_y(20))], (20, 150, 40, 255), width=3)
    bb.draw_badge(12, bb.r_y(20) - 9, "CH2 프로브 팁: U1 Pin 8 (4단 지연 파형, 6단 출력)", (235, 255, 235, 245), (10, 130, 30, 255), font=bb.font_kr_bold)
    
    # -> U2 Pin 1 (row 8, col b on right block) [부하 연결!]
    bb.draw_wire([
        (c_l['g'], bb.r_y(14)),
        (c_l['j'], bb.r_y(14)),
        (c_l['j'], bb.r_y(5)),
        (c_r['a'], bb.r_y(5)),
        (c_r['a'], bb.r_y(8)),
        (c_r['b'], bb.r_y(8))
    ], (20, 150, 40, 255), width=2)
    bb.draw_badge(490, bb.r_y(5) - 9, "U1 Pin 8 ──> U2 Pin 1 (부하 입력)", (235, 255, 235, 240), (10, 130, 30, 255), font=bb.font_kr_sm)

    # 5. U2 부하 인버터 결선
    # Pin 2 (row 9, col b): 개방(NC! 교안 도면 X표)
    bb.draw_badge(c_r['a'] - 65, bb.r_y(9) - 7, "Pin 2: NC (개방)", (250, 250, 250, 240), (130, 60, 60, 255), font=bb.font_kr_sm)
    
    # U2 미사용 입력: 3, 5 -> GND (mid_gnd: 529)
    bb.draw_wire([(c_r['d'], bb.r_y(10)), (c_r['mid_gnd'], bb.r_y(10))], (20, 60, 220, 255), width=2)
    bb.draw_wire([(c_r['d'], bb.r_y(12)), (c_r['mid_gnd'], bb.r_y(12))], (20, 60, 220, 255), width=2)
    bb.draw_badge(c_r['mid_gnd'] - 30, bb.r_y(15) - 9, "U2 미사용 입력 (3, 5) ──> GND", (240, 245, 255, 240), (20, 60, 200, 255), font=bb.font_kr_sm)
    
    # U2 미사용 입력: 9, 11, 13 -> VCC (right vcc: 867)
    bb.draw_wire([(c_r['g'], bb.r_y(13)), (c_r['vcc'], bb.r_y(13))], (220, 20, 20, 255), width=2)
    bb.draw_wire([(c_r['g'], bb.r_y(11)), (c_r['vcc'], bb.r_y(11))], (220, 20, 20, 255), width=2)
    bb.draw_wire([(c_r['g'], bb.r_y(9)), (c_r['vcc'], bb.r_y(9))], (220, 20, 20, 255), width=2)
    bb.draw_badge(c_r['chip_x2'] + 10, bb.r_y(16) - 9, "U2 미사용 입력 (9, 11, 13) ──> VCC 풀업", (255, 240, 240, 240), (200, 20, 20, 255), font=bb.font_kr_sm)
    
    # U2 미사용 출력: 4, 6, 8, 10, 12 -> NC
    bb.draw_badge(c_r['d'] - 38, bb.r_y(11) - 7, "Pin 4: NC", (250, 250, 250, 240), (130, 60, 60, 255), font=bb.font_kr_sm)
    bb.draw_badge(c_r['d'] - 38, bb.r_y(13) - 7, "Pin 6: NC", (250, 250, 250, 240), (130, 60, 60, 255), font=bb.font_kr_sm)
    bb.draw_badge(c_r['f'] + 18, bb.r_y(14) - 7, "Pin 8: NC", (250, 250, 250, 240), (130, 60, 60, 255), font=bb.font_kr_sm)
    bb.draw_badge(c_r['f'] + 18, bb.r_y(12) - 7, "Pin 10: NC", (250, 250, 250, 240), (130, 60, 60, 255), font=bb.font_kr_sm)
    bb.draw_badge(c_r['f'] + 18, bb.r_y(10) - 7, "Pin 12: NC", (250, 250, 250, 240), (130, 60, 60, 255), font=bb.font_kr_sm)

    # 6. 중요 판독 및 단 수 공식 안내 배지
    bb.draw_badge(12, bb.r_y(23) - 9, "★ [가장 비싼 실수 방지] CH1(Pin 4)과 CH2(Pin 8) 사이 인버터 단 수는 '정확히 4단' (3단, 4단, 5단, 6단)!", (255, 235, 235, 250), (190, 20, 20, 255), font=bb.font_kr_bold)
    bb.draw_badge(12, bb.r_y(25) - 9, "단수 오산 경고: 핀 번호만 보고 2단으로 착각하면 tpd가 2배로 계산됨.  게이트당 tpd = Δt / 4 (typ ~9ns, 실측 ~7~10ns)", (235, 245, 255, 250), (20, 60, 180, 255), font=bb.font_kr_sm)

    bb.export(output_path, max_row=27)


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


def main():
    parser = argparse.ArgumentParser(description="Breadboard Diagram Generator")
    parser.add_argument("--circuit", required=True, choices=[
        "e1_and", "e1_or", "e1_nand", "e1_comb",
        "e2_inv", "e2_schmitt", "e2_rn", "e2_rp", "e2_tpd", "e2_all"
    ], help="Circuit ID to render")
    parser.add_argument("--output", required=True, help="Output PNG path (or directory path for e2_all)")
    parser.add_argument("--template", default=None, help="Path to Breadboard.jpg")
    args = parser.parse_args()
    
    dispatch = {
        "e1_and": build_e1_and,
        "e1_or": build_e1_or,
        "e1_nand": build_e1_nand,
        "e1_comb": build_e1_comb,
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
