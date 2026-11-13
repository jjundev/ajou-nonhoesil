"""Regenerate the three chip study documents; original experiment packs are untouched."""
from pathlib import Path
import html, json, re, shutil
from mcq import merge_mcq, render_choices

PACK=Path(__file__).resolve().parent
OUT=PACK.parent
ROOT=OUT.parents[1]
ASSETS=ROOT/'.claude/skills/logic-lab-review-pack/assets'
E=html.escape
CHIPS=[]
def chip(num,name,kind,pins,gates,experiments,use,trap,extra=False):
    c=dict(id='hc'+num,num='74HC'+num,name=name,kind=kind,pins=pins.split(),gates=gates,experiments=experiments,use=use,trap=trap,extra=extra)
    stem='74HC'+num if num in ['20','42'] else '74HC_HCT'+num
    c['url']='https://assets.nexperia.com/documents/data-sheet/'+stem+'.pdf'
    if num=='148':c['url']='https://www.ti.com/lit/ds/symlink/sn74hc148.pdf'
    CHIPS.append(c)
    return c
quad='1A 1B 1Y 2A 2B 2Y GND 3Y 3A 3B 4Y 4A 4B VCC'
inv='1A 1Y 2A 2Y 3A 3Y GND 4Y 4A 5Y 5A 6Y 6A VCC'
g4=[([1,2],3),([4,5],6),([9,10],8),([12,13],11)]
gi=[([1],2),([3],4),([5],6),([9],8),([11],10),([13],12)]
chip('00','NAND · 2입력 4개','NAND',quad,g4,'01','두 입력이 모두 1일 때만 출력이 0이에요. NAND만으로도 다른 논리를 구성할 수 있어요.','00은 AND가 아니라 AND의 결과를 뒤집는 NAND예요.')
chip('02','NOR · 2입력 4개','NOR','1Y 1A 1B 2Y 2A 2B GND 3A 3B 3Y 4A 4B 4Y VCC',[([2,3],1),([5,6],4),([8,9],10),([11,12],13)],'01','두 입력이 모두 0일 때만 출력이 1이에요. 실험01에서는 OR 다음 NOR를 연결하는 회로에도 쓰여요.','첫 게이트는 2·3번 입력 → 1번 출력이에요. 00·08·32와 같은 배선으로 바꾸면 안 돼요.')
chip('04','NOT · 인버터 6개','NOT',inv,gi,'01·02·03·04·05','입력 한 개를 반전해요. 실험02에서는 입력 전압과 출력 전압의 관계를 측정하고, 다른 실험에서는 보수 신호를 만들어요.','1번 입력 → 2번 출력이에요. 2입력 게이트처럼 1·2번을 두 입력으로 쓰지 않아요.')
chip('08','AND · 2입력 4개','AND',quad,g4,'01·03·05 교안','입력이 모두 1이어야 출력이 1이에요. 실험01의 3입력 AND는 2입력 AND 두 개를 이어 만들어요. 실험03에서는 carry와 borrow의 곱 항을 만들어요.','08 자체가 3입력 AND 칩은 아니에요. 칩 수와 사용 게이트 수를 구별해요.')
chip('32','OR · 2입력 4개','OR',quad,g4,'01·03','입력 중 하나라도 1이면 출력이 1이에요. 전가산기와 전감산기에서 두 조건을 합쳐 최종 carry·borrow를 만들어요.','32는 OR, 86은 XOR예요. 두 입력이 모두 1일 때 결과가 달라요.')
chip('86','XOR · 2입력 4개','XOR',quad,g4,'03 · 01 준비물','두 입력이 다르면 1이에요. 전가산기의 합과 전감산기의 차를 계산하는 데 쓰여요.','두 입력이 모두 1이면 XOR는 0이에요. 외형이나 핀 배치가 같아도 OR와 기능은 달라요.')
chip('14','Schmitt NOT · 6개','SCHMITT',inv,gi,'02','반전 기능에 히스테리시스가 더해져요. 입력이 올라갈 때와 내려갈 때 전환되는 문턱이 달라, 느리거나 잡음이 있는 입력을 정리할 수 있어요.','04와 핀 배치는 같지만 아날로그 입출력 특성이 같지는 않아요. 문턱 사이 출력은 이전 상태에 따라 달라요.')
chip('11','AND · 3입력 3개','AND3','1A 1B 2A 2B 2C 2Y GND 3Y 3A 3B 3C 1Y 1C VCC',[([1,2,13],12),([3,4,5],6),([9,10,11],8)],'04','1×4 DMUX의 데이터와 선택 조건을 곱하는 3입력 AND로 쓰여요. 한 출력 경로의 세 조건이 모두 1일 때만 1이에요.','첫 게이트의 세 번째 입력은 13번이고 출력은 12번이에요. 1·2·3번이 한 게이트의 입력이 아니에요.')
chip('20','NAND · 4입력 2개','NAND4','1A 1B NC 1C 1D 1Y GND 2Y 2A 2B NC 2C 2D VCC',[([1,2,4,5],6),([9,10,12,13],8)],'04·05','실험04에서는 선택 조건과 데이터를 NAND로 묶고 마지막 NAND에서 합쳐요. 실험05의 Excess-3 인코더도 NOT와 NAND의 조합으로 구현해요.','3·11번은 NC예요. 연결되지 않은 핀을 입력으로 세거나, 4입력 NAND의 입력 하나를 띄워 두면 안 돼요.')
chip('42','BCD → Decimal · 1-of-10','BCD','/Y0 /Y1 /Y2 /Y3 /Y4 /Y5 /Y6 GND /Y7 /Y8 /Y9 D C B A VCC',[],'05','4비트 BCD를 받아 해당 십진 출력 하나만 0으로 내려요. A가 1의 자리 비트, D가 8의 자리 비트예요. 교안의 LED 연결은 출력이 0일 때 켜지는 방식이에요.','16핀으로 VCC=16, GND=8이에요. 출력 10개이며 4→16 전체 디코더가 아니에요. BCD 10~15에서는 모든 출력이 1이에요.')
chip('139','Dual 2→4 Decoder / DMUX','DECODER','/1E 1A0 1A1 /1Y0 /1Y1 /1Y2 /1Y3 GND /2Y3 /2Y2 /2Y1 /2Y0 2A1 2A0 /2E VCC',[],'04 교안 보충','각 절반에 선택 입력 두 개와 Active Low enable이 있어요. 활성 상태에서 선택된 출력 하나만 0이에요.','이번 수행 항목은 게이트 구현이에요. 전용 칩의 활성 극성을 게이트 회로에 그대로 옮기지 않아요.',True)
chip('153','Dual 4→1 MUX','MUX','/1E S1 1I3 1I2 1I1 1I0 1Y GND 2Y 2I0 2I1 2I2 2I3 S0 /2E VCC',[],'04 교안 보충','두 개의 4→1 MUX가 선택선 S1·S0를 공유해요. 각 enable이 0일 때 해당 데이터가 출력되고 1이면 출력은 0이에요.','153은 입력 여러 개 중 하나를 출력으로 골라요. 139와 데이터 흐름이 달라요.',True)
chip('148','8→3 Priority Encoder','ENCODER','/I4 /I5 /I6 /I7 /EI /A2 /A1 GND /A0 /I0 /I1 /I2 /I3 /GS /EO VCC',[],'05 교안 보충','입력과 코드 출력이 Active Low예요. enable이 활성일 때 여러 입력이 동시에 활성이라면 번호가 높은 입력을 우선해요.','이번 Excess-3 인코더의 실제 사용 칩은 04·20이에요. 148 자체를 Excess-3 변환 칩으로 외우지 않아요.',True)

def table(head,rows):
    return '<div class="table-wrap"><table><thead><tr>'+''.join('<th>'+str(x)+'</th>' for x in head)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(x)+'</td>' for x in row)+'</tr>' for row in rows)+'</tbody></table></div>'
def svg(c,blank=False):
    n=len(c['pins']);half=n//2;h=86+half*35
    s=f'<svg class="pinmap" role="img" aria-label="{c["num"]} {n}핀 위에서 본 핀 배치" viewBox="0 0 520 {h}"><rect x="180" y="34" width="160" height="{h-62}" rx="8" fill="var(--surface)" stroke="currentColor"/><path d="M245 34 a15 15 0 0 0 30 0" fill="none" stroke="currentColor"/><circle cx="194" cy="58" r="4" fill="currentColor"/><text x="260" y="18" text-anchor="middle">노치 ↑ · 위에서 봄</text><text x="260" y="{h/2}" text-anchor="middle" font-weight="700">{c["num"]}</text>'
    for i in range(half):
        for pin,x1,x2,tx,anchor in [(i+1,156,180,147,'end'),(n-i,340,364,373,'start')]:
            label=c['pins'][pin-1];y=72+i*35
            s+=f'<path d="M{x1} {y} H{x2}" stroke="currentColor" stroke-width="2"/><text x="{tx}" y="{y+5}" text-anchor="{anchor}">{pin} · {E(label) if not blank else "?"}</text>'
    return s+'</svg>'

def truth(c):
    k=c['kind']
    if k in ['AND','OR','NAND','NOR','XOR']:
        fn={'AND':lambda a,b:a&b,'OR':lambda a,b:a|b,'NAND':lambda a,b:1-(a&b),'NOR':lambda a,b:1-(a|b),'XOR':lambda a,b:a^b}[k]
        return table(['A','B','Y'],[(a,b,fn(a,b)) for a in range(2) for b in range(2)])
    if k=='NOT':return table(['A','Y'],[(0,1),(1,0)])
    if k=='SCHMITT':return table(['입력 상태','출력 판단'],[('충분히 낮음','1'),('상승하며 V_T+ 통과','1 → 0'),('하강하며 V_T− 통과','0 → 1'),('두 문턱 사이','이전 상태에 따라 달라짐')])
    if k=='AND3':return table(['조건','Y'],[('입력 3개 모두 1',1),('하나라도 0',0)])
    if k=='NAND4':return table(['조건','Y'],[('입력 4개 모두 1',0),('하나라도 0',1)])
    if k=='BCD':return table(['D C B A','십진수','0인 출력','그 밖의 출력'],[(f'{i:04b}',i,'Y'+str(i),'모두 1') for i in range(10)]+[('1010~1111','무효 BCD','없음','모두 1')])
    return ''

Q=[]
def q(title,topic,prompt,answer,steps,wrong,hint=None,draw=False):
    Q.append(dict(id=f'q{len(Q)+1:02}',title=title,topic=topic,prompt=prompt,answer=answer,steps=steps,wrong=wrong,hint=hint or '칩의 기능과 입력·출력 핀을 따로 확인해 보세요.',draw=draw))
for c in CHIPS[:10]:
    answer=c['name'] if c['kind']!='BCD' else 'BCD → Decimal 디코더 · 입력 4개 · Active Low 출력 10개'
    q(c['num']+'의 정체',c['id'],f'{c["num"]}의 기능과 내부 구성(게이트 개수·게이트당 입력 수 또는 입출력 수)을 적으세요.',answer,['부품 번호의 뒤 숫자를 기능과 연결해요.',c['use']],c['trap'])
q('AND 칩 고르기','hc08','2입력 AND와 3입력 AND를 각각 한 게이트로 구현하려 해요. 칩 번호를 고르세요.','2입력: 74HC08 / 3입력: 74HC11',['08은 2입력 AND 네 개, 11은 3입력 AND 세 개예요.','3입력 AND는 08 두 게이트로도 구현하지만, 질문은 한 게이트로 구현하는 조건이에요.'],'08을 3입력 AND 전용 칩으로 외우지 않아요.')
q('전원 핀 비교','common','74HC08과 74HC42의 VCC·GND 핀 번호를 각각 적으세요.','08: VCC 14·GND 7 / 42: VCC 16·GND 8',['08은 14핀, 42는 16핀이에요.','핀 수와 정확한 칩을 확인한 뒤 전원 핀을 찾아요.'],'모든 74HC 칩에 14·7을 적용하지 않아요.')
q('노치 기준으로 방향 읽기','common','14핀 칩의 노치를 위로 놓고 위에서 봐요. 왼쪽 위·왼쪽 아래·오른쪽 아래·오른쪽 위의 번호는?','차례로 1·7·8·14',['노치 왼쪽 위에서 1번을 찾아요.','왼쪽을 아래로 내려가 7번, 오른쪽 아래가 8번이고 오른쪽 위로 올라가며 14번이 돼요.'],'바닥에서 본 그림은 좌우가 뒤집혀요.')
q('08 첫 게이트 배선','hc08','74HC08의 첫 게이트에 입력 A·B를 넣고 Y를 읽으려 해요. 입력·출력·전원 핀을 지정하세요.','A=1, B=2, Y=3, VCC=14, GND=7',['입력은 첫 게이트의 1A·1B인 1·2번이에요.','출력은 1Y인 3번이며, 칩 공통 전원도 연결해야 해요.'],'3번은 세 번째 입력이 아니라 출력이에요.',draw=True)
q('02로 교체할 때','hc02','08의 1·2번에 입력, 3번에 출력을 연결한 배선을 그대로 02에 사용해도 될까요? 올바른 첫 게이트 배선을 적으세요.','안 돼요. 02는 입력 2·3 → 출력 1이에요.',['02의 1번은 1Y, 2·3번은 1A·1B예요.','전원 핀은 14·7로 같지만 신호 핀의 역할이 달라요.'],'핀 수가 같다고 신호 배치까지 같지는 않아요.',draw=True)
q('04는 입력이 하나','hc04','74HC04의 1번 핀에 0을 넣었어요. 어느 핀에서 어떤 논리값을 읽나요?','2번에서 1',['첫 인버터는 1 → 2로 연결돼요.','NOT는 0을 1로 뒤집어요.'],'1·2번을 서로 다른 입력으로 보지 않아요.')
q('OR와 XOR 구별','hc86','32와 86의 첫 게이트 입력을 모두 1로 했어요. 각각 3번 출력은?','32: 1 / 86: 0',['OR는 하나 이상이 1이면 1이에요.','XOR는 두 입력이 다를 때만 1이에요.'],'핀 배치가 같아도 기능은 다를 수 있어요.')
q('11의 첫 게이트','hc11','74HC11의 첫 AND 게이트 입력 세 개와 출력 핀을 적으세요.','입력 1·2·13 → 출력 12',['1A·1B·1C를 같은 게이트 번호로 묶어요.','13번의 1C도 첫 게이트 입력이고 12번의 1Y가 출력이에요.'],'1·2·3 → 4처럼 연속 번호로 추측하지 않아요.',draw=True)
q('20의 NC 구별','hc20','74HC20의 첫 게이트를 써요. 입력 네 개, 출력, NC 두 개를 적으세요.','입력 1·2·4·5 / 출력 6 / NC 3·11',['핀 3을 건너뛰고 입력 1·2·4·5를 찾아요.','NC는 내부 회로에 연결되지 않은 핀이에요.'],'NC와 사용하지 않는 실제 입력은 달라요.',draw=True)
q('NAND 출력 계산','hc20','74HC20의 1·2·4·5번을 순서대로 1·1·0·1로 했어요. 6번의 값은?','1',['네 입력의 AND 결과는 0이에요.','NAND가 그 결과를 뒤집으므로 1이에요.'],'모든 입력이 1일 때만 NAND 출력이 0이에요.')
q('한 칩으로 3입력 AND','hc08','74HC08 하나로 Y=A·B·C를 만들어요. 첫째·둘째 게이트를 쓰는 신호 연결을 완성하세요.','A→1, B→2, 3→4, C→5, Y=6',['첫 게이트 1·2 → 3에서 A·B를 만들어요.','3번을 둘째 게이트의 4번에 연결하고 5번에 C를 넣으면 6번이 A·B·C예요.'],'게이트 두 개를 쓴다고 칩도 두 개 필요한 것은 아니에요.')
q('전가산기에서 고를 칩','hc86','전가산기 S=(A XOR B) XOR Ci, Co=A·B+(A XOR B)·Ci를 만들 때 필요한 기능별 칩 번호를 적으세요.','XOR=86, AND=08, OR=32',['합은 XOR 두 게이트로 만들어요.','carry의 두 곱 항은 AND, 두 항의 결합은 OR예요.'],'전가산기를 만든다고 반드시 전용 가산기 IC가 필요한 것은 아니에요.')
q('14로 교체한 이유','hc14','실험02에서 04를 14로 교체했어요. 핀 배치와 전환 문턱은 각각 어떻게 달라지나요?','핀 배치는 같고, 14는 상승·하강 전환 문턱이 달라요.',['둘 다 여섯 인버터이고 첫 경로는 1 → 2예요.','14는 Schmitt 입력이므로 V_T+와 V_T−를 구분해요.'],'두 칩이 같은 반전 기능이라고 전달 특성도 같다고 판단하지 않아요.')
q('입력·출력·NC 처리','common','사용하지 않는 CMOS 입력, 사용하지 않는 출력, NC 핀은 각각 어떻게 처리하나요?','입력은 회로에 맞는 확정 논리값으로 고정 / 출력은 미연결 / NC는 미연결',['실제 입력을 띄우면 논리값이 불안정해질 수 있어요.','출력은 값을 내보내는 핀이므로 전원이나 다른 출력에 직접 묶지 않아요.','NC는 실제 입력이 아니에요.'],'입력과 출력 모두 GND에 연결한다는 규칙은 틀려요.')
q('NAND의 남는 입력','hc20','4입력 NAND를 3입력 NAND처럼 쓰려 해요. 남는 실제 입력 하나를 0·1 중 어디에 고정해야 하나요?','1(VCC)',['NAND의 AND 부분에서 항등원은 1이에요.','NOT(A·B·C·1)=NOT(A·B·C)가 돼요. 0에 묶으면 출력이 항상 1이에요.'],'이 문제는 사용 중인 게이트의 남는 입력이에요. NC와 구별해요.')
q('BCD 입력 핀 찾기','hc42','74HC42에 십진수 5를 넣어요. D C B A 비트열과 핀 12·13·14·15의 값을 적으세요.','D C B A=0101 / 12=0, 13=1, 14=0, 15=1',['5=4+1이므로 D C B A는 0101이에요.','A는 15, B는 14, C는 13, D는 12번이에요.'],'A가 최하위 비트예요. 핀 번호 순서와 비트의 자릿수를 구별해요.',draw=True)
q('선택 출력과 LED','hc42','42의 입력이 0101(D C B A)이에요. 0이 되는 출력 이름·핀 번호와, 교안처럼 +5V→LED→저항→출력으로 연결한 LED 상태는?','Y5·6번이 0, 해당 LED가 켜져요.',['5를 선택하면 Y5만 0이에요.','Y5는 6번이고 출력으로 전류가 흘러들어가도록 LED를 연결해요.'],'출력 0이 항상 LED 꺼짐을 뜻하지 않아요.')
q('무효 BCD','hc42','74HC42에 1010(D C B A)을 넣었어요. Y10이 활성화되나요?','아니요. Y10은 없고 Y0~Y9 모두 1이에요.',['1010은 십진수 10으로 한 자리 BCD 유효 범위 밖이에요.','42는 1-of-10 디코더라서 이런 입력에서는 모든 출력을 비활성으로 해요.'],'교안의 4×16 표기만 보고 16개 출력이 있다고 외우지 않아요.')
q('MUX 실제 구현 칩','hc20','이번 실험04의 4×1 MUX 게이트 구현에 쓰는 칩 두 종류는?','74HC04와 74HC20',['04로 선택선·enable의 보수 신호를 만들어요.','20의 NAND 게이트들로 경로 조건과 최종 출력을 구성해요.'],'교안에 있는 전용 MUX 153은 이번 수행의 게이트 구현과 구분해요.')
q('DMUX와 인코더 실제 칩','hc11','이번 실험04의 1×4 DMUX와 실험05의 Excess-3 인코더에 쓰는 칩 조합을 각각 적으세요.','DMUX: 04·11 / Excess-3: 04·20',['DMUX는 보수 신호와 3입력 AND로 경로를 만들어요.','Excess-3 회로는 보수 신호와 4입력 NAND 조합이에요.'],'148을 이번 Excess-3 회로의 사용 칩으로 바꾸어 외우지 않아요.')

COMMON='''<p>실험실에서는 “AND가 무엇인가”에 더해 <b>어느 칩을 골라 어느 다리에 연결하는가</b>까지 판단해야 해요. 먼저 번호와 기능을 연결하고, 방향·전원·게이트 묶음을 확인해 보세요.</p><p>범위는 실험01~05예요. 실제 수행 중심 칩 10종을 먼저 익히고, 교안에만 등장하는 전용 칩 3종은 보충에서 구별해요. 새로 만든 연습문제이며 실제 기출이나 출제 예고는 아니에요.</p><div class="sum">번호 → 기능 → 방향 → 전원 → 신호 핀 순서로 확인해요.</div>'''
def article(ident,title,body):return f'<article class="topic" id="{ident}"><h3>{title}</h3>{body}</article>'
def core_note(c):
    n=len(c['pins']);g=c['gates']
    b=f'<p><b>{c["name"]}</b> · 관련 실험 {c["experiments"]}'+(' · 보충' if c['extra'] else ' · 핵심')+'</p><p>'+c['use']+'</p>'
    b+=svg(c)+f'<p class="caption">{n}핀의 번호·신호 대응을 위에서 본 학습용 그림이에요. 실물 제조사·접미사와 패키지는 사용 전 확인해요. /는 Active Low를 표시하며, 칩 몸체 크기와 다리 간격은 축척이 아니에요.</p>'
    b+=table(['핀','신호','역할'],[(i,p,'전원' if p in ['VCC','GND'] else '연결하지 않음' if p=='NC' else '출력' if 'Y' in p or (c['kind']=='ENCODER' and p in ['/A0','/A1','/A2','/GS','/EO']) else '입력') for i,p in enumerate(c['pins'],1)])
    if g:
        b+='<h4>같은 게이트끼리 묶어 읽어요</h4>'+table(['게이트','입력 핀 → 출력 핀'],[(i,'·'.join(map(str,ins))+' → '+str(y)) for i,(ins,y) in enumerate(g,1)])
        b+=f'<p>첫 게이트를 사용하는 예: 입력 {"·".join(map(str,g[0][0]))}번에서 신호를 넣고 {g[0][1]}번에서 출력을 읽어요. VCC는 {n}번, GND는 {n//2}번에 연결해요.</p>'
    b+=truth(c)+f'<div class="warn"><b>여기서 자주 헷갈려요</b><p>{c["trap"]}</p></div><div class="sum">{c["num"]}: {c["name"]}. {c["trap"]}</div>'
    return b

def build():
    questions=merge_mcq(Q,json.loads((PACK/'mcq.json').read_text(encoding='utf-8')))
    PACK.mkdir(parents=True,exist_ok=True)
    shared_vendor=OUT.parent/'.vendor'
    if not (shared_vendor/'pretendard').is_dir():
        shutil.copytree(ASSETS/'vendor',shared_vendor,dirs_exist_ok=True)
    notes=[('start','칩 공부를 시작해요',COMMON)]
    common='''<h4>노치부터 확인해요</h4><p>칩을 위에서 보고 노치를 위로 놓아요. 왼쪽 위가 1번이고 왼쪽을 따라 아래로 센 다음, 오른쪽 아래에서 위로 올라가요. 14핀은 왼쪽 아래 7·오른쪽 아래 8·오른쪽 위 14번이에요. 16핀은 각각 8·9·16번이에요.</p><h4>글자의 역할을 구분해요</h4><p>74HC08에서 HC는 논리 계열, 08은 기능을 구별하는 번호예요. 제조사 접두사나 끝의 패키지 표기는 따로 확인해요. HC·HCT·LS를 전기적으로 같은 칩이라고 가정하지 않아요.</p><h4>입력, 출력, NC는 서로 달라요</h4><p>사용하지 않는 CMOS 입력은 VCC 또는 GND 등 회로에 맞는 확정값으로 고정해요. 사용 중인 게이트의 남는 입력은 원하는 논리를 보존하도록 고정해요. 미사용 출력과 NC는 연결하지 않아요. 여러 출력끼리 직접 묶지 않아요.</p><p>전원은 이 실험 교안의 +5V를 기준으로 해요. 신호원·측정기와 회로는 기준 접지를 공유해야 해요. LED는 극성과 직렬 저항을 확인해요. “LED 켜짐=논리 1”은 연결 방식에 따라 달라요.</p><div class="sum">노치 기준 위에서 보기. /는 Active Low. 실제 입력 고정·출력 미연결·NC 미연결을 구분해요.</div>'''
    notes.append(('common','방향·전원·입출력을 읽어요',common))
    rows=[(f'<a href="#{c["id"]}">{c["num"]}</a>',c['name'],c['experiments'],'보충' if c['extra'] else '핵심') for c in CHIPS]
    notes.append(('index','번호와 기능을 한눈에 봐요',table(['칩','기능·구성','관련 실험','범위'],rows)+'<p>00 NAND / 02 NOR / 04 NOT / 08 AND / 32 OR / 86 XOR를 먼저 짝지어요. 이어서 14 Schmitt, 11 3입력 AND, 20 4입력 NAND, 42 BCD 디코더를 익혀요.</p>'))
    notes.extend((c['id'],c['num']+' · '+c['name'],core_note(c)) for c in CHIPS)
    notes.append(('lab-map','실험별로 다시 연결해요',table(['실험','이번 수행에서의 칩·역할'],[('01','00·02·04·08·32: 기본 게이트 조합 (86은 준비물에도 등장)'),('02','04 전달 특성·저항·지연 / 14 Schmitt 비교'),('03','86 합·차 / 08 곱 항 / 32 합 항 / 04 보수'),('04','MUX: 04·20 / DMUX: 04·11'),('05','BCD 디코더: 42 / Excess-3 인코더: 04·20')])+'<p>139·153·148은 교안 준비물·수행 제외 항목의 보충이에요. 실제 배선은 이번 학기 수행 항목으로 구분해 공부해요.</p>'))
    filenames=['정리노트.html','문제풀이.html','문제설명.html']
    pages=[notes,[],[]]
    for x in questions:
        c=next((c for c in CHIPS if c['id']==x['topic']),None)
        visual=svg(c,blank=True) if c and x['draw'] else ''
        prompt=f'<p>{x["prompt"]}</p>'+visual
        links=f'<p class="study-links"><a href="정리노트.html#{x["topic"]}">관련 정리</a> · <a href="문제설명.html#{x["id"]}">자세한 설명</a></p>'
        short=prompt+'<p class="mcq-guidance">보기 하나를 고르면 바로 채점해요. 채점 후 보기를 누르면 이유를 확인할 수 있어요.</p>'+render_choices(x)+f'<details class="practice-hint"><summary>힌트 보기</summary><p>{x["hint"]}</p></details>'+links
        long=prompt+render_choices(x,explain=True)+f'<h4>정답</h4><p><b>{x["answer"]}</b></p><h4>이렇게 판단해요</h4><ol>'+''.join('<li>'+s+'</li>' for s in x['steps'])+'</ol>'+f'<div class="warn"><b>오답을 피하려면</b><p>{x["wrong"]}</p></div><p><a href="정리노트.html#{x["topic"]}">관련 정리</a> · <a href="문제풀이.html#{x["id"]}">문제로 돌아가기</a></p><div class="sum">{x["answer"]}</div>'
        pages[1].append((x['id'],x['id'][1:]+'. '+x['title'],short))
        pages[2].append((x['id'],x['id'][1:]+'. '+x['title'],long))
    css='''<style>.pinmap{display:block;width:100%;max-width:520px;margin:24px auto;color:var(--ink);font:16px system-ui,sans-serif}.caption{font-size:.88em;color:var(--ink-2)}.table-wrap{max-width:100%;overflow-x:auto}table{width:100%;border-collapse:collapse}th,td{padding:10px 12px;border:1px solid var(--line);text-align:left}th{background:var(--surface)}.pack-links{display:flex;gap:16px;flex-wrap:wrap;margin:18px 0 28px}.pack-links a{font-weight:650;text-underline-offset:4px}.work-space{min-height:95px;padding:18px;border:1px dashed var(--line);margin:24px 0;color:var(--ink-2)}.practice-hint,.practice-answer{border:1px solid var(--line);padding:14px;margin:14px 0}.practice-answer summary,.practice-hint summary{cursor:pointer;font-weight:650}.study-links{margin-top:26px}h4{margin-top:30px}li{margin-block:9px}:focus-visible{outline:2px solid var(--accent);outline-offset:4px}@media(max-width:500px){th,td{padding:8px 6px;font-size:.9em}.pinmap{font-size:17px}}@media print{.pack-links,.work-space{display:none}.practice-answer>*,.practice-hint>*{display:block!important}.pinmap{max-width:400px;break-inside:avoid}table{font-size:10pt}tr{break-inside:avoid}.topic{break-before:page}.topic:first-child{break-before:auto}}</style>'''
    script='''<script>let chipDetails=[];addEventListener('beforeprint',()=>{chipDetails=[...document.querySelectorAll('details')].map(d=>[d,d.open]);chipDetails.forEach(([d])=>d.open=true)});addEventListener('afterprint',()=>chipDetails.forEach(([d,o])=>d.open=o));</script>'''
    template=(ASSETS/'note-template.html').read_text(encoding='utf-8')
    # Existing notebook visual authority; static math uses Unicode, so KaTeX is unnecessary.
    template=re.sub(r'\s*<link[^>]+href="https://cdn.jsdelivr.net/npm/katex[^>]+>','',template)
    template=re.sub(r'\s*<script defer src="https://cdn.jsdelivr.net/npm/katex.*?</script>','',template,flags=re.S)
    template=template.replace('https://cdn.jsdelivr.net/npm/pretendard@1.3.9/dist/web/static/pretendard.css','../.vendor/pretendard/pretendard.css')
    for i,items in enumerate(pages):
        nav='<nav class="pack-links" aria-label="학습 자료">'+''.join(f'<a href="{f}"'+(' aria-current="page"' if j==i else '')+'>'+f[:-5]+'</a>' for j,f in enumerate(filenames))+'</nav>'
        sections=nav+'<section id="learning"><h2 class="sr-only">학습 내용</h2>'+''.join(article(*a) for a in items)+'</section>'
        toc='<ol class="toc-list">'+''.join(f'<li><a href="#{a[0]}">{a[1]}</a></li>' for a in items)+'</ol>'
        values=dict(PAGE_TITLE='칩 정리 · '+filenames[i][:-5],DESCRIPTION='실험01~05 칩 학습',BRAND='칩 정리',TITLE=filenames[i][:-5],SUBTITLE=f'실험01~05 · 핵심 10종과 보충 3종 · '+('전체 핀맵과 실제 사용법' if i==0 else f'직접 만든 연습 {len(Q)}문항'),RANGE='logic-lab-chips-01-05-'+str(i),SECTIONS=sections,TOC=toc,FOOTER='실험01~05 교안 및 제조사 핀 자료 대조 · 2026-10-15 · 상세 근거: .pack/sources.json',SCRIPTS=script)
        t=template
        for key,value in values.items():t=t.replace('{{'+key+'}}',value)
        fixes='<style>.pinmap text{fill:currentColor}.btn-ghost{background:var(--surface);color:var(--ink)}.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip-path:inset(50%);white-space:nowrap;border:0}@media(max-width:500px){.pinmap text{font-size:22px}}</style>'
        t=t.replace('</head>',css+fixes+'</head>')
        if i>0:
            t=t.replace('</head>','<style>'+ (PACK/'mcq.css').read_text(encoding='utf-8')+'</style></head>')
            t=t.replace('</body>','<script>'+(PACK/'mcq.js').read_text(encoding='utf-8')+'</script></body>')
        assert '{{' not in t
        (OUT/filenames[i]).write_text(t,encoding='utf-8')
    (PACK/'chips.json').write_text(json.dumps(CHIPS,ensure_ascii=False,indent=2),encoding='utf-8')
    (PACK/'questions.json').write_text(json.dumps(questions,ensure_ascii=False,indent=2),encoding='utf-8')
    sources=dict(date='2026-10-15',scope=[1,2,3,4,5],manuals=[str(p.relative_to(ROOT)) for p in (ROOT/'강의노트').glob('실험[1-5]*.pdf')],scope_evidence=[f'보고서/실험{i:02}/체크리스트/명세.md' for i in range(1,6)],datasheets=[dict(chip=c['num'],url=c['url'],sections='Pinning information / Pin description / Functional description') for c in CHIPS],limitations=['실물 제조사·패키지 접미사는 미확인. 교안의 두 줄 핀 번호와 제조사 표준 핀 설명을 대조한 학습 그림.','직접 PDF 다운로드는 403이므로 웹 문서 열람으로 확인. 제조사 PDF를 로컬에 보관했다고 주장하지 않음.','과거 실험01 체크리스트의 미사용 입력 방치 문구는 채택하지 않음. 실험02 교안 p9의 입력 고정을 따름.','04·05 교안 표지는 과거 학기 표기이나 현재 배포 경로의 파일을 기준으로 함.'])
    (PACK/'sources.json').write_text(json.dumps(sources,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'Built 3 HTML documents, {len(CHIPS)} chips, {len(Q)} questions')

if __name__=='__main__':build()
