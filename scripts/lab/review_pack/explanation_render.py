"""Reuse the learning-note shell for the complete problem walkthroughs."""
from pathlib import Path
from collections import Counter
from urllib.parse import quote
import html
import shutil
from .explanation_content import load_explanations, within
from .equation_cards import separate_equations
from .table_cards import separate_tables
from .table_layout import load_layouts, layout_problem_tables, TableLayoutError
from .manifest import output_names, DATA
from .navigation import render_navigation
from .html2md import export_document, Parser

VENDOR = {
 'https://cdn.jsdelivr.net/npm/pretendard@1.3.9/dist/web/static/pretendard.css': 'pretendard/pretendard.css',
 'https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css': 'katex/katex.min.css',
 'https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js': 'katex/katex.min.js',
 'https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js': 'katex/auto-render.min.js',
}

def explanation_metadata(manifest: dict) -> dict[str,str]:
    sources={s['id']:s for s in manifest['sources']};metadata={}
    for p in manifest['problems']:
        if p['status']!='included':continue
        refs=[]
        for ref in p['sources']:
            source=sources[ref['source_id']]
            label=source['path'].replace('[',r'\[').replace(']',r'\]')
            url='../../'+quote(source['path'],safe='/')
            if ref.get('pdf_page'):
                url+=f"#page={ref['pdf_page']}";label+=f" · PDF p{ref['pdf_page']}"
            refs.append(f'[{label}]({url})')
        metadata[p['id']]='출처: '+' · '.join(refs) if refs else '새로 구성한 연습문제예요.'
    return metadata

def write_explanations(manifest: dict, question_data: dict, author_root: Path, folder: Path, assets: Path) -> dict[str,Path]:
    rows=load_explanations(manifest,question_data,author_root)
    author_root,folder,assets=map(Path,(author_root,folder,assets))
    names=output_names(manifest['experiment'],review_presentation_version=2,problem_explanation_version=1)
    esc=lambda value:html.escape(str(value),quote=True)
    layouts=load_layouts(author_root)
    if layouts:
        ids={r.problem["id"] for r in rows}
        for e in layouts["tables"]:
            if e["key"].split("/")[0] not in ids:raise TableLayoutError(e["key"]+": unknown problem")
    bodies=[]
    for row in rows:
        p=row.problem
        parts=layout_problem_tables(p['id'],dict(p['html'],explanation=row.fragment),layouts)
        problem='<div class="layer formal"><span class="layer-title">문제 읽기</span>'
        for key,label in [('original','문제'),('conditions','주어진 조건'),('ask','구할 것')]:
            if parts[key].strip():problem+=f'<h4>{label}</h4>'+parts[key]
        for f in p['figures']:
            problem+=f'<figure class="figure"><img src="{esc(f["src"])}" alt="{esc(p["title"])} · 주어진 그림"></figure>'
        problem+='</div>'
        fragment=parts['explanation'].replace('{{NOTE_HREF}}',names['note_html']).replace('{{REVIEW_HREF}}',names['review_html'])
        # Fragment paths are document-relative; preserve both authoring and published form.
        bodies.append(f'<article class="topic" id="{esc(p["id"])}"><h3>문제 {esc(p["number"])} · {esc(p["title"])}</h3>'+separate_tables(separate_equations(problem))+separate_tables(separate_equations(fragment))+'</article>')
        target=folder/DATA/manifest['problems'][next(i for i,x in enumerate(manifest['problems']) if x['id']==p['id'])]['explanation_fragment']
        target.parent.mkdir(parents=True,exist_ok=True)
        if target.resolve()!=within(author_root,'problem-explanations/'+p['id']+'.html').resolve():
            target.write_text(row.fragment,encoding='utf-8')
    layout_path=author_root/'problem-explanations/table-layout.json'
    if layout_path.is_file():
        target=folder/DATA/'problem-explanations/table-layout.json'
        target.parent.mkdir(parents=True,exist_ok=True)
        if target.resolve()!=layout_path.resolve():shutil.copy2(layout_path,target)
    extra=author_root/'problem-explanations/figures'
    if extra.is_dir():
        for f in extra.rglob('*'):
            if f.is_symlink():raise ValueError('Symlink explanation figure')
            if f.is_file():
                target=folder/DATA/'problem-explanations/figures'/f.relative_to(extra)
                target.parent.mkdir(parents=True,exist_ok=True)
                if f.resolve()!=target.resolve():shutil.copy2(f,target)
    title=f"실험 {manifest['experiment']} · 문제 설명"
    content='<section id="learning"><h2>문제를 함께 풀어요</h2>'+''.join(bodies)+'</section>'
    toc=render_navigation(names,'note',[dict(id=r.problem['id'],title=f"문제 {r.problem['number']} · {r.problem['title']}") for r in rows])
    values=dict(PAGE_TITLE=title,DESCRIPTION='이론을 문제풀이에 연결해요',BRAND='문제 설명',TITLE=title,SUBTITLE='첫 줄부터 완성 답과 검산까지 함께 풀어요.',INTRO='문제지와 같은 번호로 읽어요. 설명을 읽은 뒤 문제지에서 다시 풀어 보세요.',SECTIONS=content,PARTS=content,FOOTER='',SCRIPTS=f'<script src="{DATA}/assets/widgets.js"></script>',RANGE=f"logic-lab-{manifest['experiment']:02d}-problem-explanation",NOTE_HREF=names['note_html'],**toc)
    document=(assets/'note-template.html').read_text(encoding='utf-8')
    document=document.replace('<body', '<body data-problem-explanation="true"',1)
    for key,value in values.items():document=document.replace('{{'+key+'}}',value)
    for url,local in VENDOR.items():document=document.replace(url,DATA+'/assets/vendor/'+local)
    if '{{' in document:raise ValueError('Unreplaced explanation placeholder')
    parser=Parser();parser.feed(document)
    counts=Counter(n.attrs['id'] for n in parser.root.walk() if n.attrs.get('id'))
    duplicates=[ident for ident,count in counts.items() if count>1]
    if duplicates:raise ValueError('duplicate ID: '+', '.join(duplicates))
    path=folder/names['explanation_html'];path.write_text(document,encoding='utf-8')
    md,_=export_document(path,note_metadata=explanation_metadata(manifest))
    from .pack_md import write_pack_md
    mdpath=write_pack_md(folder,names['explanation_md'],md)
    return dict(explanation_html=path,explanation_md=mdpath)
