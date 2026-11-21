from scripts.lab.svg_png import svg_size


def test_svg_size_reads_viewbox():
    assert svg_size('<svg viewBox="0 0 1200 520" xmlns="http://www.w3.org/2000/svg"></svg>') == (1200, 520)
