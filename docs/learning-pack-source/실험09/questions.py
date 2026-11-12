"""은행 문항의 풀이·문제설명 원고. 답안 상태는 독립 풀이(check_values.py)와 제공 답안을 대조한 결과예요."""
from h import p, table


def img(name, alt, width=500):
    return f'<p><img src="figures/solutions/{name}.png" width="{width}" style="max-width:100%;height:auto" alt="{alt}"></p>'


RAM1_COND = p('회로는 원문 그림을 다시 그린 그림이에요. 교안 p4의 1 bit RAM과 연결이 같아요. 가운데 RS 플립플롭은 S=1이면 Set, R=1이면 Reset, 둘 다 0이면 유지예요.')
RAM2_COND = (p('회로는 교안 p6(원문 그림과 같은 회로)을 다시 그린 그림이에요. 입력 스위치는 단자로 줄였고 핀 번호는 원문 그대로예요.') +
             p('교안 범례: OE는 Read Select(0: Off, 1: On), IN은 Write Select(0: Off, 1: On), WR은 Write Value(0 or 1)예요. 범례는 OE0, IN0, WR0을 A part, OE1, IN1, WR1을 B part라고 적어요.'))

SIX = ['OE0', 'OE1', 'IN0', 'IN1', 'WR0', 'WR1']


def six(vals):
    return table(SIX, [[str(v) for v in vals]], 'ccccnn')


ORDER = ['q-ram-role', 'q-sram-def', 'q-sram-cell', 'q-read-op-rw', 'q-write1', 'q-write0', 'q-apart1', 'q-bpart1', 'q-bpart0']

# 수록하지 않는 은행 문항: (상태, 색인 상태, 이유)
NOT_INCLUDED = {
 'q-write-op-rw': ('held', 'not_selected', '예상문항이에요. Write 때 Read/Write=0은 기출 q-write1(1 쓰기 입력값)과 q-write0에서 이미 답해요. 새 개념 공백이 없어 미선별했고 원문·제공 답안은 보존해요.'),
 'q-apart0': ('held', 'not_selected', '예상문항이에요. A part 선택(IN0)은 q-apart1, 0 쓰기(WR0=1, WR1=0)는 기출 q-bpart0에서 다뤄요. 새 개념 공백이 없어 미선별했고 원문·제공 답안은 보존해요.'),
 'q-74670': ('held', 'reading_hold', '대표 등장(채점본_1 3번)이 부분 판독이에요. 74670 그림 위에 수기 답안이 겹쳐 Data Output 단자 이름 등 일부 라벨이 가려졌어요. 문제 조건을 추측해 채우지 않고 은행에서 판독을 해결한 뒤 다시 가져와요. 74670의 주소·입력·출력·레지스터 수는 실험설명 t-74670과 자체 연습(빈칸 2, 서술 2)에서 다뤄요.'),
 'q-online-74670': ('held', 'reading_hold', '온라인 개별과제 슬라이드의 축소 이미지라 수기 서술 일부를 판독하지 못했어요(부분 판독). 퀴즈 시행 근거도 없어요. 단자 의미(GWN·GRN·D·Q·W·R)는 실험설명 t-74670에서 다뤄요.'),
}

Q = {
'q-ram-role': dict(ask='RAM의 역할 서술', title='RAM의 역할', topic='t-ram', status='verified', scope='current',
 answer='기억된 정보를 읽거나 새로운 정보를 기억시킬 수 있는 메모리예요. 위치에 관계없이 거의 같은 시간에 원하는 위치에 접근해 데이터를 읽고 써요(Random Access). 기억장치, 응용 프로그램의 일시적 로딩, 데이터의 일시적 저장에 쓰여요.',
 hint='무엇을 하는 장치인지(읽기·쓰기), 어떻게 접근하는지, 어디에 쓰이는지 세 가지를 차례로 써요.',
 understand='RAM이 컴퓨터에서 무슨 일을 하는지 짧게 쓰는 서술 문제예요. 정의와 쓰임을 함께 써요.',
 cue='읽기·쓰기 + 임의 접근 + 일시적 저장',
 recall=['“RAM의 역할”이라는 말이 단서예요. RAM(Random Access Memory)의 이름 세 단어를 풀어 쓰면 답의 뼈대가 돼요.',
  '교안 p3 정의는 “기억된 정보를 읽거나 새로운 정보를 기억시킬 수 있는 메모리”예요. 읽기와 쓰기를 둘 다 할 수 있다는 것이 핵심이에요.',
  'Random Access는 위치와 관계없이 거의 같은 시간에 접근한다는 뜻이에요. 교안은 쓰임으로 “기억장치, 응용 프로그램의 일시적 로딩, 데이터의 일시적 저장”을 적어요.'],
 start='“RAM은 정보를 읽고 쓸 수 있는 메모리예요”로 시작해요.',
 steps=[('정의', p('교안 p3: 기억된 정보를 읽거나 새로운 정보를 기억시킬 수 있는 메모리예요.')), ('접근 방식', p('메모리 안 물리적 위치에 관계없이 거의 같은 시간에 원하는 위치를 읽거나 써요. 이것이 Random Access예요.')), ('쓰임', p('기억장치, 응용 프로그램의 일시적 로딩, 데이터의 일시적 저장에 써요.'))],
 verify='제공 답안 일곱 개 모두 “정보를 읽거나 기억”과 “일시적 로딩·저장”을 담고 있어 이 풀이와 같은 내용이에요.',
 pitfall='Random을 “무작위 값”으로 쓰지 않아요. 읽기만 쓰고 쓰기(기억시키기)를 빠뜨리면 정의가 모자라요.',
 retry=['읽기와 쓰기를 둘 다 적어요.', 'Random Access의 뜻을 한 문장으로 적어요.', '쓰임 세 가지를 적어요.'],
 sum_key='읽고 쓸 수 있고, 어느 위치든 거의 같은 시간에 접근해요.'),

'q-sram-def': dict(ask='SRAM이 무엇인지 간단한 서술', title='Static RAM(SRAM)이란', topic='t-ram', status='verified', scope='supplement',
 answer='SRAM은 플립플롭(래치)으로 한 비트씩 저장하는 RAM이에요. 전원이 있는 동안에는 다시 써 주지(리프레시) 않아도 값이 유지되고, 주소로 어느 위치든 거의 같은 시간에 읽고 써요. 전원을 끄면 값이 사라지는 휘발성 메모리예요.',
 hint='Static이 무엇을 가리키는지, 무엇으로 저장하는지, 전원과의 관계를 차례로 써요.',
 understand='Static RAM의 뜻을 몇 문장으로 쓰는 문제예요. 교안은 SRAM을 따로 정의하지 않아서 RAM 정의에 저장 방식과 성질을 보태요.',
 cue='래치로 저장 + 리프레시 없음 + 휘발성',
 recall=['“Static”이 단서예요. 보충(교안 밖 일반 지식): 정적이라는 말은 다시 써 주지 않아도 값이 그대로 있다는 뜻이에요. 그 반대가 주기적으로 다시 써야 하는 DRAM(Dynamic)이에요.',
  '값을 그대로 붙잡는 회로는 플립플롭(래치)이에요. 이번 실험의 칸도 NAND SR 래치라서 SRAM 방식이에요.',
  'Static이어도 전원이 있어야 래치가 동작해요. 그래서 SRAM도 전원을 끄면 값이 사라지는 휘발성이에요. 교안 실험 2의 휘발성 실험이 이것과 이어져요.'],
 start='“SRAM은 플립플롭(래치)으로 비트를 저장하는 RAM이에요”로 시작해요.',
 steps=[('저장 방식', p('플립플롭(래치)이 비트 하나를 붙잡아요. 이번 실험의 NAND SR 래치가 그 예예요.')), ('Static의 뜻', p('전원이 있는 동안 리프레시 없이 값이 유지돼요. DRAM은 전하가 새서 주기적으로 다시 써야 해요(보충).')), ('RAM의 성질', p('주소로 어느 위치든 거의 같은 시간에 읽고 쓰고, 전원을 끄면 값이 사라져요(휘발성).'))],
 verify='채점본의 수기 답안(부분 판독)도 “접근속도가 같고, 휘발성”을 적었어요. 이 풀이와 겹치는 핵심이에요.',
 pitfall='Static을 “전원 없이도 유지”로 쓰면 틀려요. 비휘발성은 ROM·플래시 같은 다른 메모리의 성질이에요(보충).',
 retry=['저장 소자(래치)를 적어요.', 'Static의 뜻(리프레시 없음)을 적어요.', '휘발성을 덧붙여요.'],
 sum_key='래치로 저장하고 리프레시가 필요 없지만 휘발성이에요.'),

'q-sram-cell': dict(ask='SRAM에서 정보를 저장하는 회로 이름', title='SRAM의 저장 회로', topic='t-latch', status='verified', scope='current',
 answer='플립플롭(래치)이에요. 이번 실험에서는 NAND 게이트 두 개로 만든 NAND SR 래치가 한 비트를 저장해요.',
 hint='이번 실험에서 A, B 한 칸이 무엇으로 만들어졌는지 떠올려요.',
 understand='SRAM의 한 칸이 어떤 회로로 값을 붙잡는지 이름을 쓰는 문제예요.',
 cue='값을 붙잡는 회로 = 래치(플립플롭)',
 recall=['“정보를 저장하는 회로”가 단서예요. 입력을 쉬게 해도 값이 남는 회로, 즉 되먹임이 있는 래치(플립플롭)를 떠올려요.',
  '교안 목표가 “NAND SR Latch 기반의 회로 구성”이에요. 2bit RAM의 칸 A, B가 각각 NAND SR 래치예요.',
  '보충: 반도체 SRAM 셀은 인버터 두 개를 엇갈려 이은 래치로 흔히 설명해요. 그래서 제공 답안에 “인버터”가 함께 적힌 자료도 있어요.'],
 start='“A, B 칸은 NAND 두 개를 엇갈려 이은 래치예요”라고 적어요.',
 steps=[('저장 회로', p('되먹임으로 Q를 붙잡는 플립플롭(래치)이에요.')), ('이번 실험', p('74HC00 NAND 두 개로 만든 NAND SR 래치가 비트 하나예요. S′=R′=1이면 앞의 값을 유지해요.'))],
 verify='제공 답안은 “플립플롭, 인버터”, “플립플롭이 사용되며…”, “R-S F/F” 세 가지예요. 셋 다 플립플롭(래치) 계열이라 이 풀이와 맞아요.',
 pitfall='레지스터는 플립플롭 여러 개를 묶은 것이에요. 한 비트를 붙잡는 회로의 이름은 플립플롭(래치)이에요.',
 retry=['되먹임이 있는 회로를 떠올려요.', '이번 실험 칸의 이름을 적어요.', '제공 답안의 표현과 비교해요.'],
 sum_key='한 비트는 래치(플립플롭)가 붙잡아요.'),

'q-read-op-rw': dict(ask='Read operation 때의 Read/Write 입력 값', title='읽기 때 Read/Write 값', topic='t-1bit', status='verified', scope='current',
 answer='1',
 conditions=p('원문 그림은 은행에 답 표시 없는 사본이 없어 다시 싣지 않았어요. 회로는 다음 문항(1 bit RAM에 1 쓰기)의 그림과 같은 교안 p4 1 bit RAM이에요. Selection input은 세 AND에 모두 들어가요. Input은 그대로 S 쪽 AND에, 인버터를 거쳐 R 쪽 AND에 들어가요. Read/Write는 인버터를 거쳐 S·R 쪽 AND에, 그대로 출력 AND에 들어가요. 출력 AND의 나머지 입력은 Q예요.'), figs=[],
 hint='Read/Write가 어느 AND에 그대로, 어느 AND에 뒤집혀 들어가는지 따라가요.',
 understand='1 bit RAM에서 저장된 값을 Output으로 꺼낼 때 Read/Write 입력을 0과 1 중 무엇으로 둘지 묻는 문제예요.',
 cue='출력 AND에 그대로 들어가는 선은 1이어야',
 recall=['“Read operation”이 단서예요. 읽기는 Q를 Output으로 꺼내는 일이니 출력 AND의 문이 열려야 해요.',
  '출력 AND는 Output = Sel·(R/W)·Q예요. Read/Write가 그대로 들어가니 1이어야 Q가 나가요.',
  'Read/Write는 인버터를 거쳐 S, R 쪽 AND에도 들어가요. 1이면 그 문이 닫혀 읽는 동안 값이 바뀌지 않아요.'],
 start='Output = Sel·(R/W)·Q를 적고 R/W 자리에 1을 넣어 봐요.',
 steps=[('출력 문', p('Output = Sel·(R/W)·Q예요. R/W=1, Sel=1이면 Output=Q예요.')), ('쓰기 문 닫힘', p('(R/W)′=0이라 S=R=0이에요. 래치는 유지돼요. 교안 표의 Read 줄(1, 1, X → Q(t-1), Q(t-1))과 같아요.') + img('ram1-read', '읽기 때 각 선의 값', 520))],
 verify='R/W=0이면 출력 AND가 0을 내서 Q를 볼 수 없어요. 그래서 읽기는 1뿐이에요.',
 pitfall='제공 답안 일부는 “Read = 1, Write = 1”처럼 적혀 있어 값인지 규약인지 모호해요. 이 문제의 답은 입력 값 1이에요.',
 wb_pitfall='읽기는 1, 쓰기는 0이에요. 제공 답안 일부의 “Read = 1, Write = 1” 표기는 모호해요.',
 retry=['출력 AND 식을 적어요.', 'R/W에 1을 넣어 Output=Q를 확인해요.', '쓰기 문이 닫히는지 확인해요.'],
 sum_key='읽기는 R/W=1이고 Output=Q예요.'),

'q-write1': dict(ask='1을 쓸 때의 Selection input, Input, Read/Write 값', title='1 bit RAM에 1 쓰기', topic='t-1bit', status='verified', scope='current',
 answer='Selection input=1, Input=1, Read/Write=0',
 conditions=RAM1_COND, figs=['ram1-given'],
 hint='Q=1이 되려면 S와 R 중 어느 쪽이 1이어야 하는지부터 정해요.',
 understand='1 bit RAM의 Q에 1을 넣으려면 세 입력을 어떻게 둘지 찾는 문제예요.',
 cue='Q=1 → S=1 → S 쪽 AND 세 입력 모두 1',
 recall=['“1의 데이터를 쓰려고”가 단서예요. RS 플립플롭 표에서 Q=1은 Set 줄(S=1, R=0)이에요.',
  'S 쪽 AND는 S = Sel·(R/W)′·Input이에요. 세 입력이 모두 1이어야 S=1이에요. (R/W)′=1이려면 Read/Write=0이에요.',
  'R 쪽 AND는 Input′를 받아요. Input=1이면 R=0이라 Set과 Reset이 부딪치지 않아요.'],
 start='S = Sel·(R/W)′·Input = 1을 적고 각 항을 1로 맞춰요.',
 steps=[('목표', p('Q=1이려면 S=1, R=0이에요.')), ('S 쪽 AND', p('Sel=1, (R/W)′=1, Input=1이라야 S=1이에요. 그래서 Read/Write=0이에요.')), ('R 쪽 확인', p('R = Sel·(R/W)′·Input′ = 1·1·0 = 0이에요.') + img('ram1-write1', '1 쓰기 때 각 선의 값', 520))],
 verify='p4 표 셋째 줄(1, 0, 1 → Q=1, Output=0)과 같아요. 쓰는 동안 Output은 0이에요. 처음 Q가 0이든 1이든 Q=1이 돼요.',
 pitfall='Read/Write를 1로 두면 읽기라 써지지 않아요. 교안 p4 식은 S·R이 그림과 바뀌어 적혀 있으니 회로도로 판단해요. 수기 메모 한 장은 input을 0으로 적었지만 덧칠로 판독이 불확실해요.',
 wb_pitfall='Read/Write=0이 쓰기예요. 교안 p4 식은 S·R이 그림과 바뀌어 있으니 회로도로 판단해요.',
 retry=['Q=1에 필요한 S, R을 적어요.', 'S 쪽 AND 세 입력을 1로 맞춰요.', 'R=0인지 확인해요.'],
 sum_key='Sel=1, Input=1, R/W=0이면 S=1이라 Q=1이에요.'),

'q-write0': dict(ask='0을 쓸 때의 Selection input, Input, Read/Write 값', title='1 bit RAM에 0 쓰기', topic='t-1bit', status='verified', scope='current',
 answer='Selection input=1, Input=0, Read/Write=0',
 conditions=RAM1_COND, figs=['ram1-given-2'],
 hint='Q=0이 되려면 R=1이어야 해요. R 쪽 AND에는 Input이 어떻게 들어가나요?',
 understand='앞 문제와 반대로 Q에 0을 넣는 세 입력을 찾는 문제예요.',
 cue='Q=0 → R=1 → R 쪽 AND는 Input′를 받음',
 recall=['“0의 데이터를 쓰려고”가 단서예요. RS 표의 Reset 줄(S=0, R=1)을 떠올려요.',
  'R 쪽 AND는 R = Sel·(R/W)′·Input′예요. Input이 인버터를 거쳐 들어가니 Input=0이어야 그 항이 1이에요.',
  'Selection=1, Read/Write=0은 1 쓰기와 같아요. 쓸 값만 Input으로 바뀌어요.'],
 start='R = Sel·(R/W)′·Input′ = 1을 적어요.',
 steps=[('목표', p('Q=0이려면 R=1, S=0이에요.')), ('R 쪽 AND', p('Sel=1, (R/W)′=1, Input′=1이라야 R=1이에요. 그래서 Input=0, Read/Write=0이에요.')), ('S 쪽 확인', p('S = 1·1·0 = 0이에요.') + img('ram1-write0', '0 쓰기 때 각 선의 값', 520))],
 verify='p4 표 둘째 줄(1, 0, 0 → Q=0, Output=0)과 같아요. 제공 답안 일곱 개도 1, 0, 0이에요(덧쓴 수기 한 장은 판독 보류).',
 pitfall='Selection을 0으로 두면 아무것도 써지지 않아요. p4 표 첫 줄은 그때 Q=0이라 적었지만 회로대로면 Q는 유지예요.',
 retry=['Q=0에 필요한 S, R을 적어요.', 'R 쪽 AND의 Input′를 1로 맞춰요.', 'S=0인지 확인해요.'],
 sum_key='Sel=1, Input=0, R/W=0이면 R=1이라 Q=0이에요.'),

'q-apart1': dict(wb_noimg=True, ask='A part에 1을 쓰기 위한 OE0, OE1, IN0, IN1, WR0, WR1 값', title='2bit RAM의 A에 1 쓰기', topic='t-2bit', status='verified', scope='current',
 answer='OE0=1, OE1=0, IN0=1, IN1=0, WR0=0, WR1=1 (쓰기에 필요한 것은 IN0=1, IN1=0, WR1=1, WR0=0이고 OE는 저장에 영향을 주지 않아요)',
 conditions=RAM2_COND, figs=['ram2-given'],
 hint='A의 Set 쪽 NAND 두 입력이 무엇인지 회로도에서 찾아요. 범례 이름만 믿지 말아요.',
 understand='2bit RAM의 칸 A에만 1을 넣으려면 여섯 입력을 어떻게 둘지 찾는 문제예요.',
 cue='A의 Set 쪽 NAND = IN0과 WR1',
 recall=['“A part에 1”이 단서예요. A의 래치를 Set(Q=1)하려면 S′_A=0, R′_A=1이어야 해요.',
  '회로도에서 A의 Set 쪽 NAND(1·2번)는 IN0과 WR1을, Reset 쪽 NAND(4·5번)는 IN0과 WR0을 받아요. S′_A=(IN0·WR1)′이 0이려면 IN0=1, WR1=1이에요.',
  'WR0, WR1은 B에도 함께 들어가요. B가 바뀌지 않으려면 IN1=0이어야 해요. OE는 출력 문이라 저장에는 영향이 없어요. 제공 답안은 OE0=1로 두어 쓰는 값이 OUT0에 바로 보이게 했어요.'],
 start='S′_A = (IN0·WR1)′ = 0을 적어요.',
 steps=[('A의 래치', p('Set하려면 S′_A=0, R′_A=1이에요. IN0=1, WR1=1, WR0=0이면 S′_A=(1·1)′=0, R′_A=(1·0)′=1이에요.')), ('B 지키기', p('IN1=0이면 S′_B=R′_B=1이라 B는 유지돼요.')), ('OE', p('OE0=1이면 OUT0=OE0·Q로 쓰는 값 1이 바로 보이고, OE1=0이면 OUT1=0이에요. OE를 바꿔도 저장값은 같아요.') + six([1, 0, 1, 0, 0, 1]) + img('ram2-apart1', 'A에 1 쓰기 때 각 선의 값', 560))],
 verify='처음 A, B가 0이든 1이든, OE를 어떻게 두든 S′_A=0, R′_A=1, S′_B=R′_B=1이라 A=1이 되고 B는 그대로예요. 제공 답안 일곱 개도 같은 값이에요.',
 pitfall='범례만 보고 “A의 값 = WR0”이라 여겨 WR0=1로 쓰면 A에 0이 써져요. 회로도대로 저장값은 WR1과 같아요. IN1까지 1로 두면 B에도 1이 써져요.',
 wb_pitfall='범례만 보면 WR0=1로 착각해요. 회로도대로 저장값은 WR1과 같아요. IN1=1이면 B도 바뀌어요.',
 retry=['A의 Set 쪽 NAND 입력을 회로도에서 찾아요.', 'S′=0, R′=1이 되게 IN0, WR1, WR0을 정해요.', 'IN1=0으로 B를 지켜요.'],
 sum_key='IN0=1, WR1=1, WR0=0, IN1=0이고 OE는 저장에 영향이 없어요.'),

'q-bpart1': dict(wb_noimg=True, ask='B part에 1을 쓰기 위한 OE0, OE1, IN0, IN1, WR0, WR1 값', title='2bit RAM의 B에 1 쓰기', topic='t-2bit', status='verified', scope='current',
 answer='OE0=0, OE1=1, IN0=0, IN1=1, WR0=0, WR1=1',
 conditions=RAM2_COND + p('원문 그림은 은행에 답 표시 없는 사본이 없어 다시 싣지 않았어요. 회로는 앞 문항(A part에 1 쓰기)의 그림과 같은 교안 p6 2bit RAM이에요. B의 Set 쪽 NAND(1·2번)는 IN1과 WR1, Reset 쪽 NAND(4·5번)는 IN1과 WR0을 받아요.'), figs=[],
 hint='B의 Set 쪽 NAND 두 입력을 찾고, A를 지키려면 무엇을 0으로 둘지 생각해요.',
 understand='2bit RAM의 칸 B에만 1을 넣는 여섯 입력을 찾는 문제예요.',
 cue='B의 Set 쪽 NAND = IN1과 WR1',
 recall=['“B part에 1”이 단서예요. B를 Set하려면 S′_B=0, R′_B=1이에요.',
  'B의 Set 쪽 NAND(1·2번)는 IN1과 WR1, Reset 쪽(4·5번)은 IN1과 WR0을 받아요. WR 두 선은 A와 같이 써요.',
  'A를 지키려면 IN0=0이에요. OE1=1이면 OUT1이 B를 바로 보여 주고, OE0=0이면 OUT0=0이에요.'],
 start='S′_B = (IN1·WR1)′ = 0을 적어요.',
 steps=[('B의 래치', p('IN1=1, WR1=1, WR0=0이면 S′_B=0, R′_B=1이라 B가 Set돼요.')), ('A 지키기', p('IN0=0이면 A의 두 NAND가 1을 내서 A는 유지돼요.') + six([0, 1, 0, 1, 0, 1]) + img('ram2-bpart1', 'B에 1 쓰기 때 각 선의 값', 560))],
 verify='처음 값과 OE에 관계없이 S′_B=0, R′_B=1, S′_A=R′_A=1이라 B=1, A 유지예요. 제공 답안 두 개도 같은 값이에요(덧쓴 수기 두 장은 WR 값 판독 보류).',
 pitfall='WR은 A와 B가 같이 써요. 칸을 고르는 것은 IN뿐이에요. 범례대로 WR1만 B의 값이라고 생각해도 이 문항의 값은 같지만, B에 0을 쓸 때는 WR0=1도 필요해요.',
 retry=['B의 Set 쪽 NAND 입력을 찾아요.', 'IN1, WR1, WR0을 정해요.', 'IN0=0으로 A를 지켜요.'],
 sum_key='IN1=1, WR1=1, WR0=0, IN0=0이에요.'),

'q-bpart0': dict(wb_noimg=True, ask='B part에 0을 쓰기 위한 OE0, OE1, IN0, IN1, WR0, WR1 값', title='2bit RAM의 B에 0 쓰기', topic='t-2bit', status='verified', scope='current',
 answer='OE0=0, OE1=1, IN0=0, IN1=1, WR0=1, WR1=0',
 conditions=RAM2_COND, figs=['ram2-given-3'],
 hint='0을 쓰려면 B의 Reset 쪽 NAND 출력이 0이 돼야 해요. 그 NAND의 두 입력을 찾아요.',
 understand='2bit RAM의 칸 B에 0을 넣는 여섯 입력을 찾는 문제예요.',
 cue='B의 Reset 쪽 NAND = IN1과 WR0',
 recall=['“B part에 0”이 단서예요. B를 Reset하려면 R′_B=0, S′_B=1이에요.',
  'B의 Reset 쪽 NAND(4·5번)는 IN1과 WR0을 받아요. R′_B=(IN1·WR0)′=0이려면 IN1=1, WR0=1이에요. S′_B가 1로 남으려면 WR1=0이에요.',
  '교안 주의 2대로 WR0과 WR1은 반대예요. A를 지키려면 IN0=0이에요.'],
 start='R′_B = (IN1·WR0)′ = 0을 적어요.',
 steps=[('B의 래치', p('IN1=1, WR0=1, WR1=0이면 R′_B=0, S′_B=1이라 B가 Reset(Q=0)돼요.')), ('A 지키기와 OE', p('IN0=0이라 A는 유지돼요. OE1=1이면 OUT1이 0을 보여 줘요.') + six([0, 1, 0, 1, 1, 0]) + img('ram2-bpart0', 'B에 0 쓰기 때 각 선의 값', 560))],
 verify='처음 값과 OE에 관계없이 R′_B=0, S′_B=1, S′_A=R′_A=1이라 B=0, A 유지예요. 제공 답안 여섯 개(덧쓴 수기 두 장 제외)도 같은 값이에요.',
 pitfall='범례를 그대로 읽어 “B의 값 WR1=0”만 두고 WR0을 0으로 두면 R′_B=1이라 아무것도 써지지 않아요. WR0=1이 필요해요.',
 retry=['B의 Reset 쪽 NAND 입력을 찾아요.', 'R′=0, S′=1이 되게 WR0, WR1을 정해요.', 'IN0=0으로 A를 지켜요.'],
 sum_key='IN1=1, WR0=1, WR1=0, IN0=0이에요.'),
}
