"""Use EC2 template snapshots (hash-pinned) with local resources and LOCAL_PATCHES."""
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

CONDITIONS_OLD="  panel.append(block('조건', p.html.conditions, 'conditions'), block('구할 것', p.html.ask, 'ask-box'));"
CONDITIONS_NEW=("  if (p.html.conditions && p.html.conditions.trim()) panel.append(block('조건', p.html.conditions, 'conditions'));   // 조건이 없으면 라벨도 없다\n"
                "  panel.append(block('구할 것', p.html.ask, 'ask-box'));")
TABLE_ANCHOR='/* 수식 */'
TABLE_CSS='''/* 표: 격자선, 머리행 강조. 원문 표의 빈 칸은 태블릿 펜으로 쓸 높이(7mm)를 갖는다 */
#book table { border-collapse: collapse; width: 100%; margin: 1mm 0; }
#book th, #book td {
  border: .3mm solid var(--ink); padding: 1.2mm 1.2mm; text-align: center;
  overflow-wrap: break-word; word-break: keep-all; line-height: 1.3;
}
#book th { font-weight: 700; background: var(--paper); }
#book .original td { height: 7mm; }

'''
# 원본 스냅샷 위에 덧씌우는 두 건. 스냅샷이 바뀌어 anchor 가 사라지면 조용히 넘기지 않고 실패한다.
LOCAL_PATCHES=[(CONDITIONS_OLD,CONDITIONS_NEW),(TABLE_ANCHOR,TABLE_CSS+TABLE_ANCHOR)]

def apply_local_patches(text, name):
    for old,new in LOCAL_PATCHES:
        if text.count(old)!=1: raise ValueError('Local patch anchor not unique in '+name+': '+old[:30])
        text=text.replace(old,new)
    return text

def render_workbook_html(data, assets):
    mode=data.get('meta',{}).get('mode')
    if mode not in {'problems','answers'}: raise ValueError('Invalid workbook mode')
    folder=Path(assets)/'workbook'
    name='problem.html' if mode=='problems' else 'answer.html'
    provenance=_strict_json(folder/'provenance.json')
    blob=(folder/name).read_bytes()
    if hashlib.sha256(blob).hexdigest()!=provenance['sha256'][name]: raise ValueError('Template snapshot changed: '+name)
    template=apply_local_patches(blob.decode('utf-8').replace('\r\n','\n'),name)  # 데이터 슬롯을 채우기 전에 덧씌운다
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
