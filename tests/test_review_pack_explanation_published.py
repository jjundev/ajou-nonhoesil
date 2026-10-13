from pathlib import Path
import json,re
import pytest
from scripts.lab.review_pack.workbook_render import read_workbook_payload
from scripts.lab.review_pack.html2md import Parser
from scripts.lab.review_pack.explanation_content import text
ROOT=Path(__file__).resolve().parents[1]

def audit_experiment(number):
    folder=ROOT/'복습노트'/f'실험{number:02d}'
    m=json.loads((folder/'.pack/manifest.json').read_text())
    selected=[p for p in m['problems'] if p['status']=='included']
    q=read_workbook_payload(folder/f'실험{number:02d}_기출문제.html')['problems']
    tree=Parser();tree.feed((folder/f'실험{number:02d}_문제설명.html').read_text())
    articles=[n for n in tree.root.walk() if n.tag=='article' and 'topic' in n.attrs.get('class','').split()]
    report=(folder/'.pack/problem-explanations/검증결과.md').read_text()
    return dict(counts=(len(selected),len(q),len(articles)),
        ids=([p['id'] for p in selected],[p['id'] for p in q],[n.attrs['id'] for n in articles]),
        numbers=([str(i) for i in range(1,len(selected)+1)],[p['number'] for p in q],[re.search(r'문제 (\d+)',text(n)).group(1) for n in articles]),
        subparts_complete=all('| '+p['id']+' |' in report for p in selected),answer_status={p['id']:p['answer_status'] for p in selected},articles=articles)

@pytest.mark.parametrize('number,expected',[(1,12),(2,14),(3,15),(4,12),(5,19)])
def test_experiment_coverage(number,expected):
    result=audit_experiment(number)
    assert result['counts']==(expected,expected,expected)
    assert result['ids'][0]==result['ids'][1]==result['ids'][2]
    assert result['numbers'][0]==result['numbers'][1]==result['numbers'][2]
    assert result['subparts_complete']
    for article in result['articles']:
        for key in ('recall','understand','start','solve','verify','pitfall','retry'):
            assert sum(n.attrs.get('data-explanation')==key for n in article.walk())==1

@pytest.mark.parametrize('number,states',[(1,{'q-deq':'disputed'}),(2,{'q-region':'disputed','q-delay-transition':'unresolved','q-transition':'unresolved','q-speed':'unresolved'}),(3,{'q-fa-design':'disputed','q-fs-roles':'disputed','q-cs-roles-sub':'unresolved'}),(4,{'q-tri':'disputed','q-demux4':'disputed'})])
def test_experiment_answer_states(number,states):
    result=audit_experiment(number)
    for ident,state in states.items():
        assert result['answer_status'][ident]==state
        assert ('답안 충돌' if state=='disputed' else '정답 미확정') in text(next(n for n in result['articles'] if n.attrs['id']==ident))

@pytest.mark.parametrize('number',range(1,7))
def test_published_recall(number):
    folder=ROOT/'복습노트'/f'실험{number:02d}'
    tree=Parser();tree.feed((folder/f'실험{number:02d}_문제설명.html').read_text())
    articles=[n for n in tree.root.walk() if n.tag=='article' and 'topic' in n.attrs.get('class','').split()]
    assert articles
    for article in articles:
        regions=[n.attrs['data-explanation'] for n in article.walk() if n.attrs.get('data-explanation')]
        assert regions[0]=='recall'
        assert '이 문제를 보면 떠올려요' in text(article)
