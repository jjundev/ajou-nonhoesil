import json
from pathlib import Path
from itertools import product
from scripts.lab.review_pack.workbook_content import load_workbook_content, build_workbook_data
from scripts.lab.review_pack.workbook_figures import check_redrawn_figures

ROOT = Path('docs/learning-pack-source/실험04')
EXPECTED = ['q-mux2','q-mux4','q-demux2','q-design4','q-decoder','q-tri',
            'q-muxdef','q-demuxdef','q-difference','q-demux4','q-mux2-graded','q-active-general']

def test_raster_keeps_white_gate_and_connected_wire():
    from PIL import Image
    image=Image.open(ROOT/'figures/solutions/q-mux2-solution-01.png').convert('RGB')
    w,h=image.size
    assert min(image.getpixel((round(350*w/1000),round(145*h/600)))) > 240
    assert min(image.getpixel((round(460*w/1000),round(165*h/600)))) < 80

def test_all_selected_questions_preserve_identity_and_holds():
    m = json.loads((ROOT/'manifest.json').read_text(encoding='utf-8'))
    assert m['review_presentation_version'] == 2
    rows = load_workbook_content(m, ROOT)
    assert [q['id'] for q in rows] == EXPECTED
    assert [p['id'] for p in m['problems'] if p['status']=='held'] == ['q-active','q-switch','q-empty-six']
    assert check_redrawn_figures(ROOT,m,require_review=True) == []
    a = build_workbook_data(m,rows,'answers'); q = build_workbook_data(m,rows,'problems')
    by_id = {p['id']:p for p in a['problems']}
    assert '답안 충돌' in by_id['q-tri']['section']
    assert '답안 충돌' in by_id['q-demux4']['section']
    assert all('evidence/' not in json.dumps(p,ensure_ascii=False) for p in q['problems'])

def test_mux_and_tristate_models_match_selected_output():
    for s,i0,i1 in product((0,1),repeat=3):
        assert int(((not s) and i0) or (s and i1)) == (i1 if s else i0)
        oe0,oe1 = s,1-s
        active = [v for v,oe in [(i0,oe0),(i1,oe1)] if oe == 0]
        assert active == [i1 if s else i0]
    for s1,s0,d0,d1,d2,d3 in product((0,1),repeat=6):
        terms = [(not s1) and (not s0) and d0,(not s1) and s0 and d1,
                 s1 and (not s0) and d2,s1 and s0 and d3]
        assert int(any(terms)) == [d0,d1,d2,d3][2*s1+s0]
