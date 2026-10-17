"""Synthetic quiz inputs; these are contract fixtures, not reviewed course material."""
from copy import deepcopy
from tests.test_review_pack_manifest import fixture


def quiz_manifest():
    m = deepcopy(fixture())
    m.update(quiz_practice_version=1, review_presentation_version=2,
             problem_explanation_version=2, figure_manifest='figures/redraw-manifest.json',
             explanation_checks=dict.fromkeys(('source_visual','content','independent','browser'),'not_run'))
    for kind, short, count in [('true_false','tf',4),('fill_blank','blank',3),('breadboard','board',1),('short_answer','short',2)]:
        for n in range(1,count+1):
            p = deepcopy(m['problems'][0])
            p.update(id=f'q-qp-e04-{short}-{n:02}', question_type=kind,
                     sources=[dict(source_id='s1',pdf_page=1,printed_page=None)],
                     derived_answer=('T' if n<=2 else 'F') if kind=='true_false' else '합성 정답')
            m['problems'].append(p)
    for p in m['problems']:
        p.update(workbook_fragment=f'workbook/{p["id"]}.json',
                 explanation_fragment=f'problem-explanations/{p["id"]}.html')
    return m
