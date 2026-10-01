"""Preserve the committed problem/solution text in the new workbook contract."""
from pathlib import Path
import json
import sys
import html

ROOT=Path(__file__).parent
sys.path.insert(0,str(ROOT.parents[2]))
from scripts.lab.review_pack.html2md import Parser,Node,serialize

ASK={
 'q-mux2':'회로, 논리식, 진리표를 작성하세요.',
 'q-mux4':'표의 빈 출력 Y 네 칸을 채우세요.',
 'q-demux2':'회로, 각 출력의 논리식, 진리표를 작성하세요.',
 'q-design4':'지정한 게이트 수로 블록 내부 회로를 설계하세요.',
 'q-decoder':'디코더와 연관 지어 MUX와 DMUX의 특징을 설명하세요.',
 'q-tri':'Tri-state 버퍼와 인버터를 결선하여 2×1 MUX를 설계하세요.',
 'q-muxdef':'멀티플렉서를 간단히 서술하세요.',
 'q-demuxdef':'디멀티플렉서를 간단히 서술하세요.',
 'q-difference':'MUX와 DMUX의 차이를 설명하세요.',
 'q-demux4':'주어진 입력 조건의 출력란을 채우세요.',
 'q-mux2-graded':'회로와 논리식을 쓰고 지정된 네 행의 출력을 구하세요.',
 'q-active-general':'Active High와 Active Low를 각각 서술하세요.',
}
HINT={
 'q-mux2':'S가 0일 때와 1일 때 전달할 입력을 따로 정한 뒤 두 경로를 합쳐 보세요.',
 'q-mux4':'주소는 S1S0예요. 데이터 열은 D3부터 D0까지 역순이며 E가 활성인 조건도 확인하세요.',
 'q-demux2':'데이터를 두 AND 경로에 나누고 선택선과 그 보수로 한 경로씩 열어 보세요.',
 'q-design4':'기능표의 주소마다 데이터 하나를 통과시킬 AND 경로가 필요해요.',
 'q-decoder':'주소를 출력 선택 신호로 바꾼 다음, 데이터를 어디서 곱하고 어디서 합치는지 비교하세요.',
 'q-tri':'nOE=0에서 버퍼가 구동해요. 두 출력이 공통선에서 동시에 구동하지 않도록 제어하세요.',
 'q-muxdef':'데이터 입력 수, 선택 신호, 데이터 출력 수를 나누어 설명하세요.',
 'q-demuxdef':'데이터가 들어오는 곳과 선택 신호가 지정하는 출력 경로를 구분하세요.',
 'q-difference':'데이터 경로가 모이는지 흩어지는지, 선택되지 않은 데이터가 남는지 비교하세요.',
 'q-demux4':'High/Low를 먼저 읽고 주소마다 선택되는 출력 하나를 찾으세요. 원문 X와 계산값은 구분해요.',
 'q-mux2-graded':'일반 8행 표를 다시 쓰기보다 인쇄된 네 행의 Sel 값을 먼저 확인하세요.',
 'q-active-general':'전압이 높은 것과 기능이 유효한 것은 같지 않아요. enable을 예로 생각해 보세요.',
}
GIVEN={'q-mux4','q-design4','q-tri'}
SOLUTIONS={'q-mux2','q-demux2','q-design4','q-decoder','q-tri','q-mux2-graded'}
HINT_LABEL={
 'q-mux2':'선택선별 경로', 'q-mux4':'주소·열 순서', 'q-demux2':'선택된 출력',
 'q-design4':'주소별 AND', 'q-decoder':'선택 신호·데이터', 'q-tri':'nOE·Z·공통선',
 'q-muxdef':'데이터·선택·출력', 'q-demuxdef':'입력·분배 경로', 'q-difference':'데이터 흐름 방향',
 'q-demux4':'논리값·출력 순서', 'q-mux2-graded':'지정된 네 행', 'q-active-general':'전압·기능 구분',
}

def plain(node):
    return ''.join(c if isinstance(c,str) else plain(c) for c in node.children)

def main():
    path=ROOT/'manifest.json';m=json.loads(path.read_text(encoding='utf-8'))
    (ROOT/'workbook').mkdir(exist_ok=True)
    for p in m['problems']:
        if p['status']!='included': continue
        ident=p['id'];parser=Parser();parser.feed((ROOT/p['fragment']).read_text(encoding='utf-8'))
        problem=next(n for n in parser.root.walk() if n.tag=='div' and 'problem' in n.attrs.get('class','').split())
        children=[n for n in problem.children if isinstance(n,Node)]
        original=serialize(children[0])
        conditions=''.join(serialize(n) for n in children[1:] if 'figure' not in n.attrs.get('class','').split())
        sol=next(n for n in parser.root.walk() if n.tag=='details' and 'solution' in n.attrs.get('class','').split())
        steps=[]
        for n in sol.children:
            if not isinstance(n,Node) or n.tag=='summary': continue
            text=plain(n)
            label='풀이'
            if '검산:' in text: label='검산'
            elif '흔한 실수:' in text: label='흔한 실수'
            elif n.tag=='div' and 'table-wrap' in n.attrs.get('class',''): label='표로 확인'
            elif '$$' in text: label='논리식'
            elif '최종' in text: label='결과'
            steps.append(dict(label=label,html=serialize(n)))
        if ident in SOLUTIONS:
            image=f'figures/solutions/{ident}-solution-01.png'
            steps.insert(1,dict(label='완성 회로',html=f'<p><img src="{image}" width="400" style="max-width:100%;height:auto" alt="{html.escape(p["title"],quote=True)} 완성 회로"></p>'))
        if ident=='q-tri':
            # Keep both paragraphs, with a single step heading/gap in the A4
            # template. Separate headings left too little room for review links.
            steps[-2:]=[dict(label='검산 · 주의',html=steps[-2]['html']+steps[-1]['html'])]
        notes=[]
        if ident=='q-tri': notes.append('원문 버퍼 표는 nOE가 Low일 때 동작해요. 제공 답안의 Active High 캡션과 다르므로 이 해설은 활성 Low 표를 기준으로 설계했어요.')
        if ident=='q-demux4': notes.append('원자료는 출력이 채워진 표예요. 문제지는 같은 입력 조건으로 출력란만 비웠어요. 원문 D=0의 X 표기와 이상 AND형 DMUX의 계산값 0을 구분해요.')
        if ident in {'q-demuxdef','q-difference','q-demux4'}: notes.append('기출 여부를 확인하지 못한 자료의 문항이에요. 실제 기출로 단정하지 않아요.')
        obj=dict(original=original,conditions=conditions,ask='<p>'+ASK[ident]+'</p>',
            problem_figures=[ident+'-given-01'] if ident in GIVEN else [],
            hints=[dict(label=HINT_LABEL[ident],html='<p>'+HINT[ident]+'</p>')],
            solution=dict(steps=steps,answer='<p>'+html.escape(p.get('derived_answer') or '해설의 조건과 검산 결과를 확인하세요.')+'</p>'),notes=notes)
        p['workbook_fragment']='workbook/'+ident+'.json'
        (ROOT/p['workbook_fragment']).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    m['review_presentation_version']=2;m['figure_manifest']='figures/redraw-manifest.json'
    m['checks']=dict.fromkeys(('source_visual','content','independent','browser'),'not_run')
    path.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Workbook authored: 12 included / 3 held; immutable bank fields unchanged.')

if __name__=='__main__': main()
