"""Assemble authored fragments; never publish or overwrite an existing pack."""
from pathlib import Path
import html
import json
import re
import shutil
from urllib.parse import quote
from .manifest import validate_manifest, output_names
from .bank_import import copy_import_material
from .bank_provenance import check_bank_import

KINDS={'past':'실제 기출','unknown':'출처 미확인','predicted':'기존 예상문제','practice':'새 연습'}
ANSWERS={'verified':'풀이 검토됨','disputed':'답안 충돌','unresolved':'정답 미확정'}

def read_fragment(run,relative,names):
    candidate=(run/relative).resolve()
    if not candidate.is_relative_to(run.resolve()): raise ValueError('fragment outside run')
    text=candidate.read_text(encoding='utf-8')
    if re.search(r'<script\b|\son\w+\s*=|javascript:',text,re.I): raise ValueError('Active fragment code is forbidden')
    return text.replace('{{NOTE_HREF}}',names['note_html']).replace('{{REVIEW_HREF}}',names['review_html'])

def assemble(manifest,run,out,assets):
    errors=validate_manifest(manifest)
    if errors: raise ValueError('\n'.join(errors))
    run,out,assets=map(Path,(run,out,assets))
    if out.exists(): raise ValueError('Stage already exists; choose a new directory')
    errors=check_bank_import(run,manifest)
    if errors:raise ValueError('\n'.join(errors))
    names=output_names(manifest['experiment']); sources={s['id']:s for s in manifest['sources']}
    esc=lambda v:html.escape(str(v),quote=True)
    def refs(row):
        links=[]
        for ref in row['sources']:
            s=sources[ref['source_id']]
            url='../../'+quote(s['path'],safe='/')+(f"#page={ref['pdf_page']}" if ref.get('pdf_page') else '')
            label=f"{s['path']}"+(f" · PDF p{ref['pdf_page']}" if ref.get('pdf_page') else '')
            links.append(f'<a href="{esc(url)}">{esc(label)}</a>')
        return '<p class="sources">출처: '+(' · '.join(links) or '새로 구성한 설명·연습')+'</p>'
    note=[];review=[]
    for t in manifest['topics']:
        note.append(f'<article class="topic" id="{t["id"]}"><h3>{esc(t["title"])}</h3>'+read_fragment(run,t['fragment'],names)+refs(t)+'</article>')
    for p in manifest['problems']:
        if p['status']!='included': continue
        head=f'<p class="eyebrow">{KINDS[p["kind"]]} · {ANSWERS[p["answer_status"]]} · {esc(p["scope"])}</p>'
        conflict=(f'<aside>제공 답안: {esc(p.get("given_answer"))} / 도출 답안: {esc(p.get("derived_answer"))}. 충돌·불확실성을 확인하세요.</aside>' if p['answer_status']!='verified' else '')
        body=read_fragment(run,p['fragment'],names)
        guide=''
        if 'bank_question_id' in p:
            guide=f'<p><a href="원문과_저작안내.md#{p["id"]}">원문·제공 답안 연결·보류 기록</a></p>'
            if conflict:
                body+='<details class="original"><summary>답안 대조 기록</summary>'+conflict+'</details>'
                conflict=''
        review.append(f'<article class="card" id="{p["id"]}" data-source="{esc(KINDS[p["kind"]])}"><h3>{esc(p.get("title",p["id"]))}</h3>'+head+refs(p)+guide+conflict+body+'</article>')
    if not review: review=['<p>수록할 문항이 없습니다. 출처와 문항목록에서 자료·보류 상태를 확인하세요.</p>']
    held=[p for p in manifest['problems'] if p['status']!='included']
    if held:
        review.append('<section><h2>중복·보류·다른 실험 문항</h2><ul>'+''.join(f'<li id="{p["id"]}">{esc(p["id"])} · {esc(p["status"])}: {esc(p["reason"])}</li>' for p in held)+'</ul></section>')
    out.mkdir(parents=True)
    copy_import_material(run,out,manifest)
    shutil.copytree(assets,out/'assets')
    if (run/'figures').exists():
        for p in (run/'figures').rglob('*'):
            if p.is_symlink(): raise ValueError('No symlink figures')
        shutil.copytree(run/'figures',out/'figures')
    else: (out/'figures').mkdir()
    status={'current':'이번 학기 교안 기준','archive':'과거 교안 기준 · 이번 학기 미확인','unknown':'판본 미확인','general':'교안 없음 · 일반 이론'}[manifest['edition_status']]
    paths={}
    for kind,body in [('note',note),('review',review)]:
        rows=manifest['topics'] if kind=='note' else [p for p in manifest['problems'] if p['status']=='included']
        nav=f'<a href="{names["note_html"]}">실험 설명</a><a href="{names["review_html"]}">기출 풀이</a>'
        nav+=''.join(f'<a href="#{r["id"]}">{esc(r.get("title",r["id"]))}</a>' for r in rows)
        text=(assets/f'{kind}-template.html').read_text(encoding='utf-8')
        title=f'실험 {manifest["experiment"]} · {esc(manifest["title"])} · '+('실험 설명' if kind=='note' else '기출 풀이')
        content='<section id="learning"><h2>'+('실험 이해' if kind=='note' else '문제와 풀이')+'</h2>'+'\n'.join(body)+'</section>'
        values=dict(PAGE_TITLE=title,DESCRIPTION=status,BRAND='실험 설명',TITLE=title,TOC=nav,SUBTITLE=status,INTRO=status,SECTIONS=content,PARTS=content,FOOTER='출처와 문항목록.md에서 판본·분류·미해결 사항을 확인하세요.',SCRIPTS='<script src="assets/widgets.js"></script>',RANGE=f'logic-lab-{manifest["experiment"]:02d}',NOTE_HREF=names['note_html'])
        for key,val in values.items():
            text=text.replace('{{'+key+'}}',val)
        for url,local in {
            'https://cdn.jsdelivr.net/npm/pretendard@1.3.9/dist/web/static/pretendard.css':'assets/vendor/pretendard/pretendard.css',
            'https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css':'assets/vendor/katex/katex.min.css',
            'https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js':'assets/vendor/katex/katex.min.js',
            'https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js':'assets/vendor/katex/auto-render.min.js',
        }.items(): text=text.replace(url,local)
        if '{{' in text: raise ValueError('Unreplaced placeholder')
        path=out/names[kind+'_html'];path.write_text(text,encoding='utf-8');paths[kind+'_html']=path
    audit=['# 출처와 문항목록','',f'판본 상태: {status}','']
    for p in manifest['problems']:
        audit.extend([f'## {p["id"]} · {KINDS[p["kind"]]}',f'- 분류: {p["status"]} / 범위: {p["scope"]}',f'- 사유: {p["reason"]}',f'- 대표 문항: {p.get("duplicate_of")}',f'- 제공 답안: {p.get("given_answer")}',f'- 도출 답안: {p.get("derived_answer")} / {ANSWERS[p["answer_status"]]}'])
        for ref in p['sources']:
            audit.append(f'- 출처: {sources[ref["source_id"]]["path"]} / PDF {ref.get("pdf_page")} / 인쇄 {ref.get("printed_page")} / 문항 {ref.get("question","미표기")}')
        audit.append('')
    paths['audit']=out/'출처와_문항목록.md';paths['audit'].write_text('\n'.join(audit),encoding='utf-8')
    paths['manifest']=out/'manifest.json';paths['manifest'].write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    return paths
