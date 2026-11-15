"""Assemble authored fragments; never publish or overwrite an existing pack."""
from pathlib import Path
import html
import json
import re
import shutil
from urllib.parse import quote
from .manifest import validate_manifest, output_names, DATA, link_data, VENDOR_DIR, replace_vendor_urls, sync_shared_vendor, workbook_links
from .bank_import import copy_import_material
from .bank_provenance import check_bank_import
from .note_metadata import forbidden_note_metadata, summary_structure_errors
from .note_reading import reading_structure_errors
from .navigation import render_navigation
from .pack_md import write_pack_md
from .equation_cards import separate_equations
from .table_cards import separate_tables
from .table_layout import load_note_layouts, layout_note_tables, TableLayoutError
from .note_summary import SUMMARY_FILE, load_note_summaries, check_topic_ids, replace_summary

KINDS={'past':'실제 기출','unknown':'출처 미확인','predicted':'기존 예상문제','practice':'새 연습'}
ANSWERS={'verified':'풀이 검토됨','disputed':'답안 충돌','unresolved':'정답 미확정'}

def read_fragment(run,relative,names,manifest):
    candidate=(run/relative).resolve()
    if not candidate.is_relative_to(run.resolve()): raise ValueError('fragment outside run')
    text=candidate.read_text(encoding='utf-8')
    if re.search(r'<script\b|\son\w+\s*=|javascript:',text,re.I): raise ValueError('Active fragment code is forbidden')
    text = link_data(text).replace('{{NOTE_HREF}}', names['note_html'])
    return workbook_links(text, manifest)

def assemble(manifest,run,out,assets):
    errors=validate_manifest(manifest)
    if errors: raise ValueError('\n'.join(errors))
    run,out,assets=map(Path,(run,out,assets))
    if out.exists(): raise ValueError('Stage already exists; choose a new directory')
    errors=check_bank_import(run,manifest)
    if errors:raise ValueError('\n'.join(errors))
    workbook=manifest.get('review_presentation_version')==2
    names=output_names(manifest['experiment'],review_presentation_version=manifest.get('review_presentation_version')); sources={s['id']:s for s in manifest['sources']}
    if workbook:
        from .workbook_content import load_workbook_content,build_workbook_data
        from .workbook_render import render_workbook_html, workbook_source_path, write_workbook_payload
        from .workbook_md import write_workbook_md
        authored=load_workbook_content(manifest,run)
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
    layouts=load_note_layouts(run)
    if layouts:
        ids={t['id'] for t in manifest['topics']}
        for e in layouts['tables']:
            if e['key'].split('/')[0] not in ids:raise TableLayoutError(e['key']+': unknown topic')
    summaries=load_note_summaries(run)
    if summaries is not None:check_topic_ids(summaries,[t['id'] for t in manifest['topics']])
    for t in manifest['topics']:
        fragment=read_fragment(run,t['fragment'],names,manifest)
        modern=manifest.get('note_presentation_version')==2
        if modern and forbidden_note_metadata(fragment):
            raise ValueError(t['id']+': note metadata belongs in manifest, not HTML')
        if summaries is not None:fragment=replace_summary(t['id'],fragment,summaries[t['id']])
        if manifest.get('note_summary_version')==2 and (errors:=summary_structure_errors(t['id'],fragment)):
            raise ValueError(errors[0])
        if manifest.get('note_reading_version')==1 and (errors:=reading_structure_errors(t['id'],fragment)):
            raise ValueError(errors[0])
        fragment=layout_note_tables(t['id'],fragment,layouts)
        note.append(f'<article class="topic" id="{t["id"]}"><h3>{esc(t["title"])}</h3>'+separate_tables(separate_equations(fragment))+('' if modern else refs(t))+'</article>')
    for p in manifest['problems']:
        if workbook: break
        if p['status']!='included': continue
        head=f'<p class="eyebrow">{KINDS[p["kind"]]} · {ANSWERS[p["answer_status"]]} · {esc(p["scope"])}</p>'
        conflict=(f'<aside>제공 답안: {esc(p.get("given_answer"))} / 도출 답안: {esc(p.get("derived_answer"))}. 충돌·불확실성을 확인하세요.</aside>' if p['answer_status']!='verified' else '')
        body=read_fragment(run,p['fragment'],names,manifest)
        guide=''
        if 'bank_question_id' in p:
            guide=f'<p><a href="{DATA}/원문과_저작안내.md#{p["id"]}">원문·제공 답안 연결·보류 기록</a></p>'
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
    data_out=out/DATA
    shutil.copytree(assets,data_out/'assets',ignore=shutil.ignore_patterns('vendor'))
    if (assets/'vendor').is_dir():
        sync_shared_vendor(assets/'vendor',out.parent/VENDOR_DIR)
    if (run/'figures').exists():
        for p in (run/'figures').rglob('*'):
            if p.is_symlink(): raise ValueError('No symlink figures')
        shutil.copytree(run/'figures',data_out/'figures')
    else: (data_out/'figures').mkdir()
    for name in ('sections/table-layout.json',SUMMARY_FILE):
        if (run/name).exists():
            (data_out/'sections').mkdir(exist_ok=True)
            shutil.copy2(run/name,data_out/name)
    status={'current':'이번 학기 교안 기준','archive':'과거 교안 기준 · 이번 학기 미확인','unknown':'판본 미확인','general':'교안 없음 · 일반 이론'}[manifest['edition_status']]
    paths={}
    for kind,body in ([('note',note)] if workbook else [('note',note),('review',review)]):
        navigation=render_navigation(names,kind,manifest['topics'] if kind=='note' else [p for p in manifest['problems'] if p['status']=='included'])
        text=(assets/f'{kind}-template.html').read_text(encoding='utf-8')
        title=f'실험 {manifest["experiment"]} · {esc(manifest["title"])} · '+('실험 설명' if kind=='note' else '기출 풀이')
        content='<section id="learning"><h2>'+('실험 이해' if kind=='note' else '문제와 풀이')+'</h2>'+'\n'.join(body)+'</section>'
        values=dict(PAGE_TITLE=title,DESCRIPTION=status,BRAND='실험 설명',TITLE=title,**navigation,SUBTITLE=status,INTRO=status,SECTIONS=content,PARTS=content,FOOTER='출처와 문항목록.md에서 판본·분류·미해결 사항을 확인하세요.',SCRIPTS=f'<script src="{DATA}/assets/widgets.js"></script>',RANGE=f'logic-lab-{manifest["experiment"]:02d}',NOTE_HREF=names['note_html'])
        if kind=='note' and manifest.get('note_presentation_version')==2:
            values['FOOTER']=''
        for key,val in values.items():
            text=text.replace('{{'+key+'}}',val)
        text=replace_vendor_urls(text)
        if '{{' in text: raise ValueError('Unreplaced placeholder')
        path=out/names[kind+'_html'];path.write_text(text,encoding='utf-8');paths[kind+'_html']=path
    if workbook:
        for mode,key in [('problems','question'),('answers','review')]:
            data=build_workbook_data(manifest,authored,mode)
            path=workbook_source_path(out,manifest,key)
            if manifest.get('workbook_delivery')=='pdf':
                paths[key+'_source']=write_workbook_payload(path,data)
            else:
                path.write_text(render_workbook_html(data,assets),encoding='utf-8')
                paths[key+'_html']=path
            paths[key+'_md']=write_workbook_md(data,manifest,out/DATA/names[key+'_md'])
    if manifest.get('problem_explanation_version') in (1,2):
        from .explanation_render import PROBLEM_PANEL_FIRST_EXPERIMENT, copy_problem_panel_assets, write_explanations
        from .workbook_render import read_workbook_payload
        explanation_assets = data_out / 'assets'
        if manifest['experiment'] >= PROBLEM_PANEL_FIRST_EXPERIMENT:
            copy_problem_panel_assets(explanation_assets)
        question=read_workbook_payload(workbook_source_path(out,manifest,'question'))
        paths.update(write_explanations(manifest,question,run,out,explanation_assets))
    audit=['# 출처와 문항목록','',f'판본 상태: {status}','']
    for p in manifest['problems']:
        audit.extend([f'## {p["id"]} · {KINDS[p["kind"]]}',f'- 분류: {p["status"]} / 범위: {p["scope"]}',f'- 사유: {p["reason"]}',f'- 대표 문항: {p.get("duplicate_of")}',f'- 제공 답안: {p.get("given_answer")}',f'- 도출 답안: {p.get("derived_answer")} / {ANSWERS[p["answer_status"]]}'])
        for ref in p['sources']:
            audit.append(f'- 출처: {sources[ref["source_id"]]["path"]} / PDF {ref.get("pdf_page")} / 인쇄 {ref.get("printed_page")} / 문항 {ref.get("question","미표기")}')
        audit.append('')
    paths['audit']=write_pack_md(out,'출처와_문항목록.md','\n'.join(audit))
    paths['manifest']=data_out/'manifest.json';paths['manifest'].write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    return paths
