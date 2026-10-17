"""The course PDF is preserved; arbitrary raster figures remain rejected."""
import base64
import hashlib
import json

from tests._workbook_fixture import create_workbook_run, add_redrawn_figure
from scripts.lab.review_pack.workbook_figures import check_redrawn_figures


def test_original_v1_pdf_background_is_allowed_only_for_quiz_breadboard(tmp_path):
    from scripts.lab.review_pack.breadboard_template import template_png
    png, width, height = template_png()
    m, run = create_workbook_run(tmp_path)
    m['quiz_practice_version'] = 1
    m['problems'][0]['question_type'] = 'breadboard'
    row = add_redrawn_figure(m, run)
    row.update(w_mm=100, h_mm=100*height/width)
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">'
           f'<title>원본 v1 양식</title><image x="0" y="0" width="{width}" height="{height}" '
           f'href="data:image/png;base64,{base64.b64encode(png).decode()}"/></svg>')
    (run/row['svg']).write_text(svg, encoding='utf-8')
    (run/row['png']).write_bytes(png)
    for key in ('svg', 'png'):
        row[key+'_sha256'] = hashlib.sha256((run/row[key]).read_bytes()).hexdigest()
    def save():
        (run/m['figure_manifest']).write_text(json.dumps({'schema_version':1,'figures':[row]}), encoding='utf-8')
    save()
    assert check_redrawn_figures(run, m) == []
    del m['quiz_practice_version']
    assert check_redrawn_figures(run, m)
    m['quiz_practice_version'] = 1
    m['problems'][0]['question_type'] = 'true_false'
    assert check_redrawn_figures(run, m)
    m['problems'][0]['question_type'] = 'breadboard'
    svg = svg.replace(base64.b64encode(png).decode(), base64.b64encode(b'foreign raster').decode())
    (run/row['svg']).write_text(svg, encoding='utf-8')
    row['svg_sha256'] = hashlib.sha256((run/row['svg']).read_bytes()).hexdigest()
    save()
    assert check_redrawn_figures(run, m)
