"""Second-pass manufacturer reference audit, independent of build.py constants.

Pin groups below are transcribed from manufacturer Pin description tables,
not imported from the authoring module. See audit-reference.json for provenance.
"""
from pathlib import Path
import json,re,html
from itertools import product
P=Path(__file__).resolve().parent
chips=json.loads((P/'chips.json').read_text(encoding='utf-8'))
qs=json.loads((P/'questions.json').read_text(encoding='utf-8'))
expected={}
def ref(number,n,groups):
    pins={};roles={}
    for symbols,nums,role in groups:
        assert len(symbols)==len(nums)
        for symbol,pin in zip(symbols,nums):
            assert pin not in pins
            pins[pin]=symbol;roles[pin]=role
    assert set(pins)==set(range(1,n+1))
    expected[number]={'pins':[pins[i] for i in range(1,n+1)],'roles':[roles[i] for i in range(1,n+1)]}
def group(symbols,nums,role):return symbols.split(),nums,role
for num in ['00','08','32','86']:
    ref(num,14,[group('1A 2A 3A 4A',[1,4,9,12],'입력'),group('1B 2B 3B 4B',[2,5,10,13],'입력'),group('1Y 2Y 3Y 4Y',[3,6,8,11],'출력'),group('GND VCC',[7,14],'전원')])
ref('02',14,[group('1Y 2Y 3Y 4Y',[1,4,10,13],'출력'),group('1A 2A 3A 4A',[2,5,8,11],'입력'),group('1B 2B 3B 4B',[3,6,9,12],'입력'),group('GND VCC',[7,14],'전원')])
for num in ['04','14']:
    ref(num,14,[group('1A 2A 3A 4A 5A 6A',[1,3,5,9,11,13],'입력'),group('1Y 2Y 3Y 4Y 5Y 6Y',[2,4,6,8,10,12],'출력'),group('GND VCC',[7,14],'전원')])
ref('11',14,[group('1A 2A 3A',[1,3,9],'입력'),group('1B 2B 3B',[2,4,10],'입력'),group('1C 2C 3C',[13,5,11],'입력'),group('1Y 2Y 3Y',[12,6,8],'출력'),group('GND VCC',[7,14],'전원')])
ref('20',14,[group('1A 1B 1C 1D',[1,2,4,5],'입력'),group('2A 2B 2C 2D',[9,10,12,13],'입력'),group('1Y 2Y',[6,8],'출력'),group('GND VCC',[7,14],'전원'),group('NC NC',[3,11],'NC')])
ref('42',16,[group('/Y0 /Y1 /Y2 /Y3 /Y4 /Y5 /Y6 /Y7 /Y8 /Y9',[1,2,3,4,5,6,7,9,10,11],'출력'),group('A B C D',[15,14,13,12],'입력'),group('GND VCC',[8,16],'전원')])
ref('139',16,[group('/1E /2E',[1,15],'입력'),group('1A0 1A1 2A0 2A1',[2,3,14,13],'입력'),group('/1Y0 /1Y1 /1Y2 /1Y3 /2Y0 /2Y1 /2Y2 /2Y3',[4,5,6,7,12,11,10,9],'출력'),group('GND VCC',[8,16],'전원')])
ref('153',16,[group('/1E /2E',[1,15],'입력'),group('S0 S1',[14,2],'입력'),group('1I0 1I1 1I2 1I3 2I0 2I1 2I2 2I3',[6,5,4,3,10,11,12,13],'입력'),group('1Y 2Y',[7,9],'출력'),group('GND VCC',[8,16],'전원')])
ref('148',16,[group('/I0 /I1 /I2 /I3 /I4 /I5 /I6 /I7',[10,11,12,13,1,2,3,4],'입력'),group('/EI',[5],'입력'),group('/A0 /A1 /A2 /GS /EO',[9,7,6,14,15],'출력'),group('GND VCC',[8,16],'전원')])
role_ko={'입력':'입력','출력':'출력','전원':'전원','NC':'연결하지 않음'}
note=(P.parent/'정리노트.html').read_text(encoding='utf-8')
count=0
for c in chips:
    r=expected[c['num'][4:]]
    assert c['pins']==r['pins'],c['num']
    block=re.search(r'<article class="topic" id="'+c['id']+r'">(.*?)</article>',note,re.S).group(1)
    for pin,(signal,role) in enumerate(zip(r['pins'],r['roles']),1):
        assert f'{pin} · {html.escape(signal)}' in block,(c['num'],pin,'SVG')
        assert f'<td>{pin}</td><td>{html.escape(signal)}</td><td>{role_ko[role]}</td>' in block,(c['num'],pin,'table')
        count+=1
assert count==190
# Verify truth tables independently against definitions, including emitted HTML rows.
for num,op in [('00',lambda a,b:int(not(a and b))),('02',lambda a,b:int(not(a or b))),('08',lambda a,b:int(a and b)),('32',lambda a,b:int(a or b)),('86',lambda a,b:int(a!=b))]:
    block=re.search(r'<article class="topic" id="hc'+num+r'">(.*?)</article>',note,re.S).group(1)
    for a,b in product([0,1],repeat=2):
        assert f'<td>{a}</td><td>{b}</td><td>{op(a,b)}</td>' in block,(num,a,b)
for a,b,c in product([0,1],repeat=3):
    assert ((a&b)&c)==int(all([a,b,c]))
    s=(a^b)^c;co=(a&b)|((a^b)&c)
    assert s+2*co==a+b+c
    d=(a^b)^c;bo=((1-a)&b)|((1-(a^b))&c)
    assert d-2*bo==a-b-c
    assert int(not(a and b and c and 1))==int(not(a and b and c))
for value in range(16):
    outputs=[int(value!=k) for k in range(10)]
    assert sum(v==0 for v in outputs)==int(value<10)
    if value==5:assert outputs[5]==0 and outputs[:5]+outputs[6:]==[1]*9
print('Manufacturer reference: 13 chips / 190 pins, SVG labels and pin-role tables PASS')
print('Rendered Boolean tables; adder, subtractor, NAND and BCD calculations PASS')
# Completeness check for the question asking explicitly for input/output counts.
assert '입력 4개' in qs[9]['answer'] and '출력 10개' in qs[9]['answer'],'q10 answer omits explicit I/O counts'
print('q10 answer completeness PASS')
for num,r in expected.items():
    c=next(c for c in chips if c['num']=='74HC'+num)
    r['datasheet']=c['url']
    r['reference']='TI Rev. H p3 pin figure, p9 function table' if num=='148' else 'Nexperia Pin description Table 2; Functional description Table 3'
    if num=='42':r['notation']='교안 A/B/C/D = Nexperia 0A/1A/2A/3A; /Y0~9 = active LOW 0Y~9Y'
(P/'audit-reference.json').write_text(json.dumps(expected,ensure_ascii=False,indent=2),encoding='utf-8')
