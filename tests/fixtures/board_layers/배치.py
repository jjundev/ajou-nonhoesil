# 따라 그리기 생성기 테스트용 — 전원 잭 두 가닥, 층 둘.
from render_breadboard import BreadboardRenderer


def build_min(output_path, template_path=None, stage=None, baseline=None, layer=None):
    bb = BreadboardRenderer(template_path, baseline=baseline, layer=layer)
    bb.enable_steps()
    bb.set_header('최소 보드', '생성기 테스트')
    bb.connect_jacks()
    bb.note('입력 <A> & 메모')
    bb.export(output_path)
    return bb


BOARDS = [("min_1단계_잭.png", build_min, None)]
FINALS = [("최소_결선도.png", build_min)]
LAYERS = {"최소_결선도.png": [(1, 1, "+5V 잭"), (2, 2, "0V 잭")]}
