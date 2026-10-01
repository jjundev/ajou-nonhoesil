import copy
import json
import pytest
from scripts.lab.review_pack.workbook_content import load_workbook_content, build_workbook_data
from scripts.lab.review_pack.workbook_figures import check_redrawn_figures
from tests._workbook_fixture import create_workbook_run, add_redrawn_figure

def test_changed_svg_or_unreviewed_figure_fails(tmp_path):
    m, run = create_workbook_run(tmp_path)
    row = add_redrawn_figure(m, run)
    assert check_redrawn_figures(run, m) == []
    assert check_redrawn_figures(run, m, require_review=True)
    (run/row['svg']).write_text('<svg/>', encoding='utf-8')
    assert check_redrawn_figures(run, m)
