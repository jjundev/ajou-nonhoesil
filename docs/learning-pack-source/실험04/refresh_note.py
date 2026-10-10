"""Author the version 2 learning note; preserve reviewed tables and problem evidence."""
from pathlib import Path
import json
import re

ROOT=Path(__file__).parent

def layer(kind,title,*paragraphs):
    return f'<div class="layer {kind}"><span class="layer-title">{title}</span>'+''.join(
        p if p.startswith('<') else '<p>'+p+'</p>' for p in paragraphs)+'</div>'

def figure(name,alt,caption):
    return f'<figure class="figure"><img src="figures/{name}.svg" alt="{alt}"><figcaption>{caption}</figcaption></figure>'

def summary(text):return '<div class="sum" hidden><p>'+text+'</p></div>'

def tables(ident):
    return re.findall(r'<div class="table-wrap">.*?</table></div>',(ROOT/'sections'/f'{ident}.html').read_text(encoding='utf-8'),re.S)

def author():
    basic=tables('t-basics');mux2=tables('t-mux2');mux4=tables('t-mux4')
    demux=tables('t-demux');decoder=tables('t-decoder');tri=tables('t-tristate')
    text={}
    text['t-start']=(ROOT/'sections/t-start.html').read_text(encoding='utf-8').strip()
    text['t-basics']=layer('eli5','전압을 0과 1로 읽어요',
        '디지털 회로는 입력 전압을 Low(0)와 High(1)로 나눠 읽어요. 이번 5V 전원 실험에서는 GND와 +5V를 입력으로 써요. 중간 전압까지 모두 유효한 0이나 1인 건 아니에요.')+layer('formal','기호부터 같이 읽어 봐요',
        'A·B는 AND예요. 두 입력이 모두 1일 때만 출력이 1이에요. A+B는 OR예요. 하나라도 1이면 출력이 1이에요. A′나 윗줄은 NOT으로, 0과 1을 뒤집어요.',
        '여기의 +는 숫자를 더하는 기호가 아니에요. 그래서 부울식에서는 1+1=1이에요. NAND는 AND의 결과를 한 번 뒤집어요.',*basic,
        '진리표의 한 행은 입력을 동시에 정했을 때의 출력을 보여 줘요. 입력이 3개면 2³=8가지 조합을 확인해요. S1S0는 두 비트 주소예요. 00, 01, 10, 11은 각각 0, 1, 2, 3을 뜻하고 S1이 큰 자리예요.')+layer('warn','X와 Z는 다른 뜻이에요',
        '입력 X를 don’t-care로 썼다면, 그 입력이 0이든 1이든 해당 행의 결론이 같다는 뜻이에요. 알 수 없는 값을 뜻하는 X와 구분해요.',
        'Z는 high impedance예요. 출력이 선을 적극적으로 구동하지 않는 상태라서 논리 0과 달라요. 출력칸에 X가 있다고 곧바로 Z라고 판단하지 않아요.',
        '출력 1은 신호의 논리값이에요. LED가 켜지는지는 결선 방향에도 달려 있어요.')+summary('AND는 둘 다 1일 때, OR는 하나라도 1일 때 1이에요. NOT은 반전해요. X와 Z는 구분해서 읽어요.')
    text['t-mux2']=layer('eli5','두 문 중 하나만 열어요',
        'S가 0이면 I0 쪽 문을, 1이면 I1 쪽 문을 열어요. 선택된 입력이 0이면 출력도 0이에요. 경로를 골랐다고 출력이 항상 1이 되는 건 아니에요.')+layer('formal','식과 회로를 함께 만들어요',
        '$$Y=\\overline{S}I_0+SI_1$$',
        'S를 NOT에 넣어 S′를 만들어요. 첫 AND에는 S′와 I0, 둘째 AND에는 S와 I1을 연결해요. 두 AND의 출력을 OR로 합치면 Y가 돼요.',
        figure('mux2-gates','S′와 I0, S와 I1을 각각 AND에 넣고 두 출력을 OR로 합치는 2×1 MUX','선택선은 경로를 고르고, 데이터 입력은 출력값을 정해요.'),
        'S=0이면 S′=1이라서 첫 항은 I0, 둘째 항은 0이에요. S=1이면 반대로 둘째 항의 I1만 남아요.',*mux2,
        'S=1, I0=1, I1=0을 넣어 볼게요. 첫 항은 0·1=0, 둘째 항은 1·0=0이라서 Y=0이에요. 선택되지 않은 I0의 값은 출력에 영향을 주지 않아요.')+layer('supp','직접 바꿔 봐요',
        '<div data-widget="mux2"><div class="controls"><label>선택선 S <select name="S"><option value="0">0</option><option value="1">1</option></select></label> <label><input type="checkbox" name="I0">I0=1</label> <label><input type="checkbox" name="I1">I1=1</label> <label>출력 Y <output>0</output></label></div><div class="static-equivalent"><p>S=0이면 Y=I0, S=1이면 Y=I1이에요. 위 진리표에서 모든 입력 조합을 확인할 수 있어요.</p></div></div>')+layer('warn','한 단계만 풀어 봐요',
        'S=0, I0=1, I1=0일 때 두 AND의 출력을 먼저 구해 봐요.',
        '<details class="hint"><summary>힌트</summary><p>S′=1부터 넣어 봐요.</p></details>',
        '<details class="solution"><summary>연습 답</summary><p>첫 AND는 1, 둘째 AND는 0이에요. 두 값을 OR로 합치면 Y=1이에요. Y=I0와도 일치해요.</p></details>')+summary('Y=S′I0+SI1이에요. NOT 1개, AND 2개, OR 1개를 써요. 선택하지 않은 데이터는 출력에 영향을 주지 않아요.')
    text['t-mux4']=layer('eli5','두 비트로 네 경로를 골라요',
        '주소 S1S0가 10이면 세 번째 입력 I2를 골라요. 네 데이터를 모두 더하는 게 아니라 한 경로만 열어요. E는 회로 전체의 동작을 허가하는 제어 신호예요.')+layer('formal','네 경로의 조건을 써 봐요',
        '$$F=\\overline{S_1}\\overline{S_0}I_0+\\overline{S_1}S_0I_1+S_1\\overline{S_0}I_2+S_1S_0I_3$$',mux4[0],
        'enable이 없는 기본 회로는 NOT 2개, 3입력 AND 4개, 4입력 OR 1개로 만들어요. 각 AND는 주소가 맞을 때만 해당 데이터를 보내요. 주소가 10이고 I0,I1,I2,I3=1,1,0,1이면 F=I2=0이에요.',
        '$$Y=\\overline{E}F$$',
        '실험 1-1에서는 E=0일 때 동작하고, E=1이면 회로 계산상 Y=0이에요. 각 경로에 E′를 함께 곱해요.',
        figure('mux4-enable','각 데이터와 E′ 및 두 주소 조건을 NAND에 넣고 마지막 NAND로 합치는 4×1 MUX','작은 원은 출력 반전을 뜻해요. 네 경로를 NAND 두 단계로 합쳐요.'),
        '앞의 4입력 NAND 네 개가 각 항을 반전하고 마지막 NAND가 다시 합쳐요. 드모르간 법칙 (A′B′C′D′)′=A+B+C+D를 적용하면 OR로 합친 것과 같아요. 각 항에는 E′가 포함돼 있어요.',mux4[1])+layer('warn','활성 조건과 데이터값은 별개예요',
        'Active Low는 제어 입력이 0일 때 기능이 켜진다는 뜻이에요. Active High는 1일 때 기능이 켜진다는 뜻이에요. 활성 상태의 데이터나 출력까지 항상 Low 또는 High라는 뜻은 아니에요.',
        '선택된 데이터가 0이면 0을, 1이면 1을 보내요. 원문 표에는 E=1의 출력이 X로 적혀 있지만, NAND 회로에서 계산하면 0이에요. 이 X를 실제 미정 출력이나 Z로 해석하지 않아요.')+summary('주소 00/01/10/11은 I0/I1/I2/I3를 골라요. 실험 회로는 E=0에서 동작하고 E=1이면 Y=0이에요.')
    text['t-demux']=layer('eli5','한 입력을 네 곳 중 한 곳으로 보내요',
        'D는 보낼 값이고 S1S0는 목적지예요. D=1이고 주소가 10이면 Y2만 1이고 나머지는 0이에요. D=0이면 선택된 곳도 0이에요.')+layer('formal','각 출력의 조건을 따로 써요',
        '$$Y_0=D\\overline{S_1}\\overline{S_0},\\quad Y_1=D\\overline{S_1}S_0$$',
        '$$Y_2=DS_1\\overline{S_0},\\quad Y_3=DS_1S_0$$',
        'NOT 2개로 주소의 보수를 만들어요. 3입력 AND 네 개에는 D와 해당 주소 조건을 연결해요. MUX와 달리 출력들을 OR로 합치지 않아요. 실험 2-1에서는 D가 데이터와 enable 역할을 함께 해요.',
        figure('demux4-gates','각 AND에 D와 두 주소 조건을 넣어 별도 출력 Y0부터 Y3까지 만드는 회로','네 출력은 서로 다른 목적지예요. 각 출력을 따로 관찰해요.'),*demux,
        '1×2 DMUX도 같은 원리예요. Y0=DS′, Y1=DS라서 NOT 1개와 AND 2개로 만들 수 있어요.')+layer('warn','이 표는 게이트에서 계산한 값이에요',
        '원문 표와 제공 답안에는 D=0인 출력칸이 X로 적혀 있어요. 하지만 AND 회로에서는 D=0이면 모든 출력이 0으로 결정돼요. 출력이 떠 있는 상태가 아니에요. 위 표와 새 그림은 이 이상적인 AND 회로를 설명해요.')+summary('D=1이면 주소가 고른 출력만 1이에요. D=0이면 모두 0이에요. MUX처럼 출력을 합치지 않아요.')
    text['t-decoder']=layer('eli5','주소를 선택 신호로 바꿔요',
        '디코더는 주소 10을 “2번만 선택”이라는 네 신호로 바꿔요. 이 신호를 데이터와 어떻게 묶느냐에 따라 MUX나 DMUX를 만들 수 있어요.')+layer('formal','같은 선택 신호를 다르게 써요',
        '활성 High 출력인 2→4 디코더에서는 C0=S1′S0′, C1=S1′S0, C2=S1S0′, C3=S1S0예요. MUX는 Y=C0I0+C1I1+C2I2+C3I3로 데이터를 골라 합쳐요. DMUX는 Yk=D·Ck로 데이터를 각각의 출력에 보내요.',
        figure('decoder-routing','두 비트 주소가 C0부터 C3까지 네 선택 신호로 바뀌고 MUX 또는 DMUX에 쓰이는 관계','주소가 10이면 C2만 1이에요. 이 그림은 활성 High 출력 모델이에요.'),
        'DMUX의 D를 1로 고정하면 디코더처럼 동작해요. 디코더에 적절한 enable 입력이 있다면 그 입력에 데이터를 넣어 DMUX처럼 사용할 수도 있어요.',*decoder,
        'n개 선택선은 최대 2ⁿ개 경로를 구분해요. 데이터선만 세면 MUX는 N→1, DMUX는 1→N이에요. 선택선까지 세면 전체 신호선 수는 달라져요. 그래서 “출력이 입력의 2배”라는 규칙으로 외우면 틀릴 수 있어요.')+layer('warn','출력 극성을 확인해요',
        '활성 Low 출력 디코더는 선택된 출력이 0이고 나머지가 1이에요. 위 식은 활성 High 출력 기준이에요. 데이터와 enable도 극성을 확인한 뒤 연결해요.')+summary('디코더는 주소를 선택 신호로 바꿔요. MUX는 데이터를 골라 합치고, DMUX는 목적지별로 나눠 보내요.')
    text['t-tristate']=layer('eli5','꺼진 출력은 선에서 손을 떼요',
        '일반 버퍼는 입력을 그대로 출력해요. Tri-state 버퍼는 켜졌을 때만 값을 보내고, 꺼지면 Z 상태로 선에서 손을 떼요. 두 출력선을 함께 쓸 때는 한 버퍼만 값을 보내야 해요.')+layer('formal','활성 Low 조건에 맞춰 연결해요',*tri[:1],
        '이 문제의 74HC125 조건은 nOE=0일 때 활성 상태예요. S=0이면 I0를, S=1이면 I1을 보내려면 nOE0=S, nOE1=S′로 연결해요. 각 데이터는 버퍼의 A 입력에, 두 B 출력은 공통 Y에 연결해요.',
        figure('tristate-bus','nOE0=S와 nOE1=S′인 활성 Low 버퍼 두 개의 출력을 공통 Y에 연결한 회로','제어 입력의 작은 원은 활성 Low를 나타내요. 검은 점은 연결된 접속점이에요.'),*tri[1:],
        '둘 다 Z이면 Y는 유효한 0이나 1로 결정되지 않아요. 둘 다 켜져서 서로 다른 값을 보내면 충돌해요. 이 표는 선택값이 안정된 뒤의 이상 동작이에요. 선택이 바뀌는 순간의 지연까지 보장하려면 별도 검토가 필요해요.')+layer('warn','활성 High 답안을 그대로 쓰지 않아요',
        '제공된 답안 그림은 활성 High enable 기준이에요. 그 연결을 활성 Low nOE 문제에 그대로 쓰면 선택 입력의 의미가 뒤집혀요. 활성 High 버퍼라면 OE0=S′, OE1=S로 연결해요. 여기서는 IC 핀 번호나 정격을 추가로 단정하지 않아요.')+summary('nOE는 0에서 켜져요. nOE0=S, nOE1=S′로 연결해요. Z는 0이 아니고, 두 버퍼를 동시에 켜면 충돌할 수 있어요.')
    text['t-lab']=layer('eli5','식대로 동작하는지 확인해요',
        '실험에서는 선택된 데이터가 지정된 출력까지 도착하는지 확인해요. 전원을 끈 상태에서 결선하고, 공급 전원과 공통 GND를 확인해요.',
        figure('lab-signal-flow','MUX와 DMUX에서 제어 조건을 정하고 주소와 데이터를 바꾸어 출력을 관찰하는 순서','먼저 조건을 정하고 입력을 바꿔요. 예상값과 실제 관찰값은 따로 기록해요.'))+layer('formal','1-1 MUX는 이렇게 확인해요',
        '준비물은 5V 전원과 74HC04·74HC20 등이에요. 회로는 NOT 3개와 4입력 NAND 5개를 써요. 74HC20 한 패키지에는 해당 NAND가 2개 들어 있으므로 3패키지가 필요해요.',
        'S1, S0, E를 각각 반전해요. 각 주소 조건과 데이터, E′를 앞 NAND에 넣고 마지막 NAND로 Y를 만들어요. <a href="#t-mux4">4×1 MUX 설명</a>의 회로와 식을 함께 확인해요.',
        'E=0을 유지하고 주소를 00, 01, 10, 11로 바꿔요. 선택된 입력을 0과 1로 바꾸면 Y도 따라와야 해요. 선택하지 않은 입력만 바꾸면 Y는 그대로여야 해요.',
        '마지막으로 E=1로 바꿔요. 회로 계산상 Y=0이에요. 원문 표의 X와 구분해서 실제 관찰값을 기록해요.')+layer('formal','2-1 DMUX는 이렇게 확인해요',
        'NOT 2개와 3입력 AND 4개를 써요. 74HC11 한 패키지에는 3입력 AND가 3개 들어 있으므로 2패키지가 필요해요. <a href="#t-demux">DMUX 설명</a>의 회로처럼 네 출력을 따로 연결해요.',
        'D=1에서 주소를 순서대로 바꾸면 Y0, Y1, Y2, Y3가 하나씩 1이 돼야 해요. D=0으로 바꾸면 모두 0이에요. 원문 표의 X는 실제로 관찰한 값과 구분해요.',
        '예상과 다르면 주소 두 비트가 바뀌었는지, 반전 신호와 원래 입력을 혼동했는지, E나 D의 활성 조건이 맞는지 확인해요. LED가 켜졌다고 항상 논리 1인 건 아니에요. 실제 결선에 맞춰 확인해요.')+layer('supp','IC 활용은 보충으로 살펴봐요',
        '1-2는 74HC153, 2-2는 74HC139를 활용해요. 이번 수행에서는 제외되지만 이론이나 시험에서도 제외된다는 뜻은 아니에요.',
        '74HC139의 표는 선택된 출력이 Low인 모델이에요. 활성 High 출력인 2-1 AND 회로의 표와 섞지 않아요. 실제 IC 결선이나 핀 번호는 해당 교안과 정확한 데이터시트를 확인해요.')+summary('MUX는 선택 입력을 바꾸며 Y를 확인해요. DMUX는 D=1에서 출력 하나씩, D=0에서 모두 0인지 확인해요.')
    for ident,body in text.items():(ROOT/'sections'/f'{ident}.html').write_text(body+'\n',encoding='utf-8')
    m=json.loads((ROOT/'manifest.json').read_text(encoding='utf-8'))
    m['note_presentation_version']=2;m.pop('generated_files',None)
    m['checks']={k:'not_run' for k in m['checks']}
    m['title']='Multiplexer & Demultiplexer — 경로를 고르는 회로를 배워요'
    titles=['왜 이 회로를 쓰는지 먼저 알아봐요','0·1, 게이트와 진리표를 다시 읽어요',
            '2×1 MUX의 경로를 골라 봐요','4×1 MUX와 활성 Low enable을 배워요',
            'DMUX로 데이터를 나눠 보내요','디코더와 MUX·DMUX를 연결해 봐요',
            'Tri-state로 출력선을 함께 써요','실험에서 바꾸고 관찰할 것을 정리해요']
    notes={
        't-start':'판본 기록: 2026-2 배포 교안의 표지에는 25-1로 적혀 있어요. 수행 범위는 9월 14일 공지의 1-1·2-1이에요. 기출 파일명 2016-1의 시험지 헤더는 2017-1이에요. 빈 예상문제 6번은 보류했어요.',
        't-mux2':'그림 재제작: 정의와 교안 PDF p3–4를 바탕으로 NOT 1개, AND 2개, OR 1개를 새로 그렸어요. 8가지 입력 조합을 식과 대조했어요.',
        't-mux4':'그림 재제작: 교안 PDF p8의 NAND 회로를 신호 이름으로 다시 그렸어요. S1·S0·E의 NOT 보수 신호는 아래 줄에 정의했어요. p9의 E=1 출력 X와 달리 이 회로의 이상 출력은 0이에요. 원문 스캔은 설명 화면에 첨부하지 않아요.',
        't-demux':'그림 재제작: 교안 PDF p11의 NOT 2개·AND 4개 회로를 새로 그렸어요. p12 원문 및 제공 퀴즈의 D=0 출력 X는 유지된 증거에서 확인할 수 있어요. 새 표는 AND 회로의 도출값 0000이에요.',
        't-decoder':'그림 재제작: 주소 10의 one-hot 선택과 Ck·Ik 합산/Ck·D 분배 관계를 직접 블록도로 그렸어요. 활성 High 출력에 한정한 이상 모델이에요.',
        't-tristate':'그림 재제작: 기출의 74HC125 제공 조건 nOE=0 활성에 맞춰 nOE0=S, nOE1=S′로 새로 그렸어요. 예상문제의 active high enables 답안 그림과 극성이 달라요. 기존 답안 충돌 상태를 유지했어요.',
        't-lab':'그림 재제작: 교안 PDF p8·p11의 회로는 앞 개념 토픽의 SVG로 대체하고 p9·p12 스캔 표는 텍스트 표 및 불일치 설명으로 대체했어요. 실험 조작은 별도 흐름도로 새로 그렸어요. 그림은 핀 배치도가 아니에요.'}
    for t,title in zip(m['topics'],titles):
        t['title']=title
        if t['id'] in notes and t['id'] != 't-start':t['md_notes']=notes[t['id']]
    (ROOT/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

if __name__=='__main__':author()
