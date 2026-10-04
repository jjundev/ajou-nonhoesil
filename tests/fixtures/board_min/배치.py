# 로더 테스트용 최소 주차 결선 파일 — 전원 잭 두 가닥만 그린다.
from render_breadboard import BreadboardRenderer

BOARD = 'v1'


def build_min(output_path, template_path=None, stage=None, baseline=None):
    bb = BreadboardRenderer(template_path, baseline=baseline, board=BOARD)
    bb.enable_steps()
    bb.set_header('최소 보드', '로더 테스트')
    bb.connect_jacks()
    bb.export(output_path)
    return bb


BOARDS = [("min_1단계_잭.png", build_min, None)]
FINALS = [("min.png", build_min)]
