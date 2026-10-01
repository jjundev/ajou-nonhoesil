"""Static study documents from workbook payloads, without running JavaScript."""
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import quote, unquote, urlsplit
import html
import re
from .html2md import Parser,Node,export_document
from .manifest import output_names

def _fragment_md(text):
    with TemporaryDirectory(prefix='logic-workbook-md-') as directory:
        path=Path(directory)/'fragment.html'
        path.write_text('<main>'+text+'</main>',encoding='utf-8')
        return export_document(path,export=False)[0].strip()

def _html_fields(p):
    yield from p['html'].values()
    for hint in p['hints']:
        yield hint['label'];yield hint['html']
        if 'formula' in hint:
            values=hint['formula'] if isinstance(hint['formula'],list) else [hint['formula']]
            yield from values
    if 'solution' in p:
        for step in p['solution']['steps']: yield step['label'];yield step['html']
        yield p['solution']['answer']

def write_workbook_md(data, manifest, path):
    parts=['# '+data['meta']['title'],'']
    names=output_names(manifest['experiment'],review_presentation_version=2)
    other='review_md' if data['meta']['mode']=='problems' else 'question_md'
    parts.append(f'[실험 설명]({names["note_md"]}) · [문제/해설]({names[other]})\n')
    if not data['problems']: parts.append('수록할 문항이 없습니다. 감사 기록에서 보류 상태를 확인하세요.\n')
    source_rows={s['id']:s for s in manifest['sources']}
    by_id={p['id']:p for p in manifest['problems']}
    for p in data['problems']:
        parts += [f'<a id="{p["id"]}"></a>',f'## {p["number"]}. {p["title"]}',p['kind']+' · '+p['section'],'']
        for key,label in [('original','문제 원문'),('conditions','조건'),('ask','구할 것')]:
            if p['html'][key]: parts += ['### '+label,_fragment_md(p['html'][key]),'']
        for f in p['figures']: parts += [f'![{p["title"]} — 주어진 회로]({quote(f["src"],safe="/")})','']
        for h in p['hints']:
            parts += ['### 힌트 · '+_fragment_md(h['label']),_fragment_md(h['html']),'']
            if 'formula' in h:
                values=h['formula'] if isinstance(h['formula'],list) else [h['formula']]
                parts.extend('$$'+v+'$$\n' for v in values)
        if 'solution' in p:
            for i,step in enumerate(p['solution']['steps'],1):
                parts += [f'### 풀이 {i} · '+_fragment_md(step['label']),_fragment_md(step['html']),'']
            parts += ['### 최종 답',_fragment_md(p['solution']['answer']),'','### 출처']
            for ref in by_id[p['id']]['sources']:
                src=source_rows[ref['source_id']]['path']
                url='../../'+quote(src,safe='/')+(f'#page={ref["pdf_page"]}' if ref.get('pdf_page') else '')
                parts.append(f'- [{src}]({url})')
            parts.append('')
    if data['meta']['mode']=='answers':
        held=[p for p in manifest['problems'] if p['status']!='included']
        if held: parts += ['## 중복·보류·다른 실험 문항','']
        for p in held: parts += [f'<a id="{p["id"]}"></a>',f'- {p["id"]} · {p["status"]}: {p["reason"]}']
    path=Path(path);path.write_text('\n'.join(parts).rstrip()+'\n',encoding='utf-8')
    return path

def check_workbook_md(data, manifest, path):
    path=Path(path)
    if not path.is_file(): return ['Missing workbook MD: '+str(path)]
    text=path.read_text(encoding='utf-8'); errors=[]
    def norm(value): return re.sub(r'[\s\\*_`|]','',html.unescape(value))
    normalized=norm(text)
    for p in data['problems']:
        if f'<a id="{p["id"]}"></a>' not in text: errors.append(p['id']+': missing MD anchor')
        for fragment in _html_fields(p):
            parser=Parser();parser.feed(fragment)
            for n in parser.root.walk():
                for child in n.children:
                    if isinstance(child,str) and norm(child) and norm(child) not in normalized:
                        errors.append(p['id']+': missing MD text '+child.strip()[:60])
                if n.tag=='img' and quote(unquote(n.attrs.get('src','')),safe='/#:.?=&%_-') not in text:
                    errors.append(p['id']+': missing MD solution diagram')
        for f in p['figures']:
            if quote(f['src'],safe='/') not in text: errors.append(p['id']+': missing MD question diagram')
    for target in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',text):
        parts=urlsplit(target)
        if parts.scheme or parts.netloc: continue
        rel=unquote(parts.path)
        if rel.startswith('../../'): continue
        dest=path.parent/rel if rel else path
        if not dest.is_file(): errors.append('Missing MD resource: '+target)
        elif parts.fragment and dest.suffix=='.md':
            if '<a id="'+unquote(parts.fragment)+'"></a>' not in dest.read_text(encoding='utf-8'):
                errors.append('Missing MD anchor: '+target)
    if data['meta']['mode']=='answers':
        for p in manifest['problems']:
            if p['status']!='included' and (p['id'] not in text or p['reason'] not in text):
                errors.append(p['id']+': missing held record')
    return errors
