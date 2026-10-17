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


def create_quiz_run(tmp_path):
    import json, hashlib
    from PIL import Image, ImageDraw
    from tests._workbook_fixture import create_workbook_run
    from tests._explanation_recall_fixture import FRAGMENT_V2
    _, run=create_workbook_run(tmp_path)
    m=quiz_manifest(); registry=[]
    (run/'problem-explanations').mkdir()
    labels={'true_false':['판정 근거','문장 확인'], 'fill_blank':['빈칸별 근거'],
            'breadboard':['연결 기준','완성 결선도'], 'short_answer':['채점 핵심','허용 표현']}
    for p in m['problems']:
        kind=p.get('question_type'); answer=p['derived_answer']
        p['title']=kind or '선택선 적용'
        obj=dict(original='<p>합성 계약 검증 문항입니다.</p>',conditions='<p>S=0, Enable 활성.</p>',
                 ask='<p>주어진 조건으로 답하시오.</p>',problem_figures=[],hints=[dict(label='단서',html='<p>조건을 읽으세요.</p>')],
                 solution=dict(steps=[dict(label=l,html='<p>조건을 적용합니다. QUIZ_SOLUTION_ONLY_SENTINEL</p>') for l in labels.get(kind,['선택'])],answer=f'<p>{answer}</p>'),notes=[])
        if kind=='breadboard':
            for name,role,exposure,w,h in [('circuit','problem','none',45,20),('blank','problem','none',100,133.33),('complete','solution','present',75,100)]:
                ident='f-'+name; folder='questions' if role=='problem' else 'solutions'
                stem=f'figures/{folder}/{name}'; (run/stem).parent.mkdir(parents=True,exist_ok=True)
                width,height=round(w*6),round(h*6)
                svg=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}"><title>{name}</title><rect x="1" y="1" width="{width-2}" height="{height-2}" fill="white" stroke="black"/></svg>'
                (run/(stem+'.svg')).write_text(svg,encoding='utf-8')
                if name=='blank':
                    import base64
                    from scripts.lab.review_pack.breadboard_template import template_png
                    png_bytes,width,height=template_png()
                    h=w*height/width
                    svg=(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}"><title>v1 PDF</title>'
                         f'<image x="0" y="0" width="{width}" height="{height}" href="data:image/png;base64,{base64.b64encode(png_bytes).decode()}"/></svg>')
                    (run/(stem+'.svg')).write_text(svg,encoding='utf-8')
                img=Image.new('RGB',(width,height),'white');draw=ImageDraw.Draw(img);draw.rectangle((1,1,width-2,height-2),outline='black',width=2)
                for y in range(20,height-15,15):
                    for x in range(20,width-15,15):draw.ellipse((x-2,y-2,x+2,y+2),fill='gray')
                if name=='complete':draw.line((30,40,width-30,height-40),fill='blue',width=4)
                img.save(run/(stem+'.png'))
                if name=='blank':
                    (run/(stem+'.png')).write_bytes(png_bytes)
                registry.append(dict(id=ident,question_id=p['id'],role=role,answer_exposure=exposure,
                    svg=stem+'.svg',png=stem+'.png',svg_sha256=hashlib.sha256((run/(stem+'.svg')).read_bytes()).hexdigest(),
                    png_sha256=hashlib.sha256((run/(stem+'.png')).read_bytes()).hexdigest(),w_mm=w,h_mm=h,
                    source_asset_ids=[],source_refs=p['sources'],derivation='합성 레이아웃 테스트',review_status='not_run',review_notes='테스트용, 실제 내용 검토 아님'))
            obj['problem_figures']=['f-circuit']
            obj['conditions']='<div class="table-wrap"><table class="chip-spec"><thead><tr><th>핀</th><th>이름</th><th>역할</th></tr></thead><tbody><tr><td>1</td><td>A</td><td>입력</td></tr></tbody></table></div><div class="work-board"><img src="figures/questions/blank.png" alt="작도용 빈 브레드보드"></div>'
            obj['solution']['steps'][-1]['html']+='<img src="figures/solutions/complete.png" width="260" style="max-width:100%;height:auto" alt="완성 결선도">'
        (run/p['workbook_fragment']).write_text(json.dumps(obj,ensure_ascii=False),encoding='utf-8')
        explanation=FRAGMENT_V2.replace('Y=I0예요.',f'{answer}입니다.').replace('선택선이 고른 입력을 찾아요.',p['title']+'의 조건을 읽어요.')
        (run/p['explanation_fragment']).write_text(explanation,encoding='utf-8')
    (run/m['figure_manifest']).write_text(json.dumps(dict(schema_version=1,figures=registry),ensure_ascii=False),encoding='utf-8')
    (run/'manifest.json').write_text(json.dumps(m,ensure_ascii=False),encoding='utf-8')
    return m,run
