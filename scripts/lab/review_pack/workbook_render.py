"""Use unmodified EC2 template snapshots with local resources."""
from pathlib import Path
import hashlib
import json
from .html2md import Parser
from .workbook_content import _strict_json
from .question_bank import _unique_json_object

TOKEN='__WORKBOOK_DATA__'
URL_MAP={
    'https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css':'assets/vendor/pretendard/pretendard.css',
    'https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css':'assets/vendor/katex/katex.min.css',
    'https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js':'assets/vendor/katex/katex.min.js',
    'https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js':'assets/vendor/katex/auto-render.min.js',
}

def render_workbook_html(data, assets):
    mode=data.get('meta',{}).get('mode')
    if mode not in {'problems','answers'}: raise ValueError('Invalid workbook mode')
    folder=Path(assets)/'workbook'
    name='problem.html' if mode=='problems' else 'answer.html'
    provenance=_strict_json(folder/'provenance.json')
    blob=(folder/name).read_bytes()
    if hashlib.sha256(blob).hexdigest()!=provenance['sha256'][name]: raise ValueError('Template snapshot changed: '+name)
    template=blob.decode('utf-8')
    if template.count(TOKEN)!=1: raise ValueError('Expected one workbook data slot')
    text=template.replace(TOKEN,json.dumps(data,ensure_ascii=False,allow_nan=False).replace('<','\\u003c'))
    for remote,local in URL_MAP.items(): text=text.replace(remote,local)
    parser=Parser();parser.feed(text)
    for n in parser.root.walk():
        if n.tag in {'link','script'}:
            url=n.attrs.get('href' if n.tag=='link' else 'src','')
            if url and not url.startswith('assets/vendor/'): raise ValueError('Unmapped template resource: '+url)
    return text

def read_workbook_payload(path):
    parser=Parser();parser.feed(Path(path).read_text(encoding='utf-8'))
    nodes=[n for n in parser.root.walk() if n.attrs.get('id')=='workbook-data']
    if len(nodes)!=1 or nodes[0].tag!='script' or nodes[0].attrs.get('type')!='application/json':
        raise ValueError('Missing/duplicate workbook JSON script')
    def bad(value): raise ValueError('Nonfinite workbook value: '+value)
    text=''.join(c for c in nodes[0].children if isinstance(c,str))
    return json.loads(text,object_pairs_hook=_unique_json_object,parse_constant=bad)
