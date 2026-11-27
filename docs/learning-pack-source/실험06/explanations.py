"""Problem walkthroughs (문제설명) for every included 실험06 question."""
from h import p, table
from sections import TOPICS
import problems as PR
from recall import RECALL

TITLE = {t[0]: t[1] for t in TOPICS}


def figure(src, alt):
    return f'<figure class="figure"><img src=".pack/figures/{src}" alt="{alt}"></figure>'


# Conditions highlighted in the right-hand summary.
SUMMARY_NOTES = {'q-diff': '비교는 비동기 강제 입력이 없는 정상 동작이며 엣지 방향은 소자마다 지정돼요.',
 'q-latch': '초기 Q는 Set/Reset으로 정하기 전 0으로 가정하지 않으며, SR 금지 입력에서는 정상 보수 관계를 적용하지 않아요.',
 'q-ff': '입력은 지정 엣지의 setup/hold를 만족해야 해요. 74HC74는 ↑, 74HC76은 ↓예요. 비동기 PR·CLR이 활성일 때는 그 명령이 우선해요.',
 'q-sr-nand-00': '00은 금지 입력이에요. S·R을 동시에 1로 풀면 다음 상태는 미정이에요.',
 'q-rs-quiz': '한 번의 Toggle은 짧은 C 펄스 조건이에요. 원래 SR의 금지 상태에서 S·R을 동시에 해제한 뒤 값도 예측하지 못해요.',
 'q-dff-table': '제목은 F/F지만 엣지 검출 없는 D 래치로 읽어요. 기출 답안 둘째 행의 “0 1 1”은 오기로 보이며 회로 계산은 S=1일 때 Q=1이에요.',
 'q-dff-design': '원문 F/F 명칭보다 레벨 표를 기준으로 NOT 1개·NAND 4개를 설계해요. Q(t−1)은 0으로 정해진 값이 아닌 이전 저장값이에요.',
 'q-jkff-short': 'C=0은 유지이며 11의 단일 Toggle은 한 번 바뀔 만큼 길고 되먹임이 돌아오기 전 끝날 만큼 짧은 C 펄스의 이상 조건이에요.',
 'q-jkff-design': '정상 보수 상태에서 C=1일 때의 갱신이며 C=0은 유지해요. 3입력 NAND 2개·교차 NAND 2개를 쓰고, 긴 C=1의 race-around와 엣지형 '
                  '74HC76을 구분해요.',
 'q-tff': 'T는 setup/hold 조건을 만족해야 하며 초기 Q가 없으면 기호 Q로 시작해요. 이 74HC76은 ↓를 쓰고 레벨 JK의 긴 활성 구간과 구분해요.',
 'q-74hc76': '교안·데이터시트의 PR→1·CLR→0을 기준으로 반대로 적힌 제공 답안과 구별해요. 동시 0 해제 뒤의 상태도 보장하지 않아요.',
 'q-74hc574': '입력의 setup/hold 조건이 필요해요. Nexperia 데이터시트가 근거이며, 제공 답안의 “한 clock 지속기간” 레벨 표현과 '
              '구분해요.',
 'q-p-76-trace': '단계 1–8의 Q는 1·1·1·0·1·0·1·0이에요. 처음 Q는 미정이며 반복 ↓ 사이의 ↑는 동작하지 않아 표에서 생략된 것이에요.'}


def build(pid, cue, why, understand, start, solve, answer, check, pitfall, retry, judge):
    links = ', '.join(f'<a href="{{{{NOTE_HREF}}}}#{t}">{TITLE[t]}</a>' for t in PR.PROBLEM_TOPICS[pid])
    retry = retry[:3]
    recall_html, recall_summary = RECALL[pid]
    recall_section = ('<div class="layer formal" data-explanation="recall"><span class="layer-title">이 문제를 봤을 때 떠올릴 개념과 공식</span>' + f'<p class="lead cue">{cue}</p>' + why + recall_html + '</div>')
    summary_recall = '<p data-summary="recall">'+recall_summary+'</p>'
    summary_note = p(SUMMARY_NOTES[pid]) if pid in SUMMARY_NOTES else ''
    return (f'<div class="layer eli5" data-explanation="understand"><span class="layer-title">이 문제에서 할 일</span>{understand}</div>'
            + recall_section +
            f'<div class="layer formal" data-explanation="start"><span class="layer-title">첫 줄을 이렇게 시작해요</span>{start}<p>필요한 개념: {links}</p></div>'
            f'<div class="layer formal" data-explanation="solve"><span class="layer-title">왜 이렇게 푸는지 함께 따라가요</span>{solve}</div>'
            f'<div class="layer formal" data-explanation="verify"><span class="layer-title">완성 답과 검산</span>{answer}<p><strong>검산:</strong> {check}</p></div>'
            f'<div class="layer warn" data-explanation="pitfall"><span class="layer-title">여기서 헷갈리기 쉬워요</span>{pitfall}</div>'
            f'<div class="layer formal" data-explanation="retry"><span class="layer-title">이제 설명을 닫고 다시 풀어요</span><ol>' +
            ''.join(f'<li>{r}</li>' for r in retry) + '</ol></div>'
            f'<div class="sum" hidden><p><strong>떠올릴 것:</strong> {cue}</p>{summary_recall}<p><strong>시작:</strong> {strip(start)}</p><p><strong>판단:</strong> {judge}</p><p><strong>검산:</strong> {check}</p>{summary_note}</div>')


def strip(html):
    import re
    return re.sub(r'<[^>]+>', '', html)


SR_A = table(['S', 'R', 'C', 'Q(t)', 'Q′(t)'],
             [['0', '0', '1', 'Q(t−1)', 'Q′(t−1)'], ['0', '1', '1', '0', '1'], ['1', '0', '1', '1', '0'], ['1', '1', '1', '1', '1'], ['x', 'x', '0', 'Q(t−1)', 'Q′(t−1)']])
JK_A = table(['J', 'K', 'C', 'Q(t)'], [['0', '0', '1', 'Q(t−1)'], ['0', '1', '1', '0 : Reset'], ['1', '0', '1', '1 : Set'], ['1', '1', '1', 'Q(t−1)′ : Toggle'], ['X', 'X', '0', 'Q(t−1)']])

E = {}

E['q-diff'] = build('q-diff',
    '입력이 반영되는 시점을 비교해요',
    p('두 소자 모두 1비트를 기억하므로 입력을 받아들이는 시점이 구분 기준이에요.'),
    p('두 소자의 공통점과 차이를 써요.'),
    p('비교 기준을 입력 반영 시점으로 잡아요.'),
    p('교안의 래치는 Enable=1인 동안, 플립플롭은 소자에 지정된 클록 엣지에서 입력을 반영해요.') +
    table(['구분', 'Latch', 'Flip-Flop'], [['트리거', '레벨', '엣지'], ['입력 반영', 'Enable=1인 동안 계속', '클록 엣지 순간에만'], ['분류', '비동기', '동기']]) +
    figure('level-vs-edge.svg', '같은 C와 D에 대해 D 래치는 C가 1인 동안 D를 따라가고 D 플립플롭은 상승 엣지에서만 D를 저장하는 타이밍도'),
    p('래치는 레벨 트리거, 플립플롭은 엣지 트리거예요.'),
    '클록이 높은 동안 D가 0→1→0으로 바뀌면 D 래치의 Q는 따라가고, D 플립플롭은 엣지에서 저장한 값을 유지해요.',
    p('위 비교는 비동기 강제 입력을 쓰지 않을 때예요. 유효 엣지 방향은 소자마다 달라요.'),
    ['같은 파형에서 두 소자가 D를 받는 구간과 순간을 각각 표시해요.'],
    '교안의 래치는 Enable=1인 동안, 플립플롭은 소자에 지정된 클록 엣지에서 입력을 반영해요.')

E['q-latch'] = build('q-latch',
    '래치는 되먹임으로 1비트를 저장해요',
    p('출력을 되먹이면 두 안정 상태 중 하나를 유지할 수 있어요.'),
    p('무엇을 저장하고 언제 갱신하는지 써요.'),
    p('Q(t−1)을 이미 저장한 값으로 두어요.'),
    p('교안의 Enable 래치는 E=1인 동안 입력에 반응해요. E=0이면 교차 되먹임이 기존 상태를 지켜요.'),
    p('래치는 되먹임으로 1비트를 저장하는 레벨 감응 기억소자예요.'),
    'D 래치에 E=D=1을 준 뒤 E=0으로 닫고 D를 0으로 바꾸면 Q는 1이에요.',
    p('초기 Q는 Set 또는 Reset 전까지 미정이에요. SR 금지 입력에서는 Q와 Q′의 보수 관계가 깨져요.'),
    ['되먹임과 Enable의 역할을 한 문장씩 써요.'],
    '교안의 Enable 래치는 E=1인 동안 입력에 반응해요. E=0이면 교차 되먹임이 기존 상태를 지켜요.')

E['q-ff'] = build('q-ff',
    '플립플롭에서 유효 엣지를 먼저 찾아요',
    p('Clock의 레벨이 유지되는 구간과 입력을 샘플링하는 순간을 구분해요.'),
    p('저장 단위와 입력이 반영되는 때를 써요.'),
    p('클록에서 유효한 엣지 하나를 표시해요.'),
    p('74HC74는 상승 엣지, 교안의 74HC76은 하강 엣지를 써요. 엣지 사이에는 저장값을 유지해요.'),
    p('플립플롭은 지정 클록 엣지에서 입력을 받아 1비트를 저장하는 동기 기억소자예요.'),
    '74HC76에서 J=K=1로 두고 클록을 한 번 내리면 Q가 한 번 반전되고, 낮은 구간에는 유지돼요.',
    p('비동기 PR·CLR이 활성일 때는 그 명령이 우선해요. 정상 엣지 동작은 입력의 setup/hold 조건을 전제로 해요.'),
    ['지정 엣지와 엣지 사이의 동작을 나눠 써요.'],
    '74HC74는 상승 엣지, 교안의 74HC76은 하강 엣지를 써요. 엣지 사이에는 저장값을 유지해요.')

E['q-sr-nand-00'] = build('q-sr-nand-00',
    'S와 R의 0이 두 NAND에 직접 들어가요',
    p('Enable 앞단이 없는 교차 NAND라 S·R은 0에서 활성이고, 0이 들어간 NAND의 출력은 1로 정해져요.'),
    p('두 출력과 보수 관계를 답해요.'),
    p('Q=(S·Q′)′, Q′=(R·Q)′에 S=R=0을 넣어요.'),
    p('두 식 모두 되먹임 입력과 관계없이 1이에요.') +
    table(['S', 'R', 'Q', 'Q′'], [['1', '1', 'Q(t−1)', 'Q′(t−1)'], ['0', '1', '1', '0'], ['1', '0', '0', '1'], ['0', '0', '1', '1']]),
    p('Q=Q′=1이므로 Q′=NOT Q는 성립하지 않아요.'),
    '되먹임에 나온 1을 다시 넣어도 두 식이 (0·1)′=1로 유지돼요.',
    p('앞단이 붙은 Enable SR의 00은 유지예요. 이 회로의 00은 금지이며 S·R을 동시에 1로 풀면 다음 상태는 미정이에요.'),
    ['각 NAND의 강제 입력을 표시해 두 출력을 계산해요.'],
    '두 식 모두 되먹임 입력과 관계없이 1이에요.')

E['q-rs-latch'] = build('q-rs-latch',
    'C를 Enable로 읽고 앞단 NAND부터 계산해요',
    p('C가 두 앞단 NAND에 공통으로 들어가므로 C=0이면 명령을 차단해요. 바깥 S·R은 High 활성, 저장부 NAND 입력은 Low 활성이에요.'),
    p('Q(t)의 다섯 행과 금지 이유를 써요.'),
    p('C=0이면 (S·0)′=(R·0)′=1이므로 마지막 행을 Q(t−1)로 채워요.'),
    p('C=1일 때 S·R이 10이면 Q 쪽 입력만 0이라 Set이에요. 11은 두 입력을 모두 0으로 만들어 Q=Q′=1이 돼요.') +
    SR_A,
    p('완성표에서 11은 출력이 1이어도 보수 관계가 깨져 사용하지 않는 행이에요.'),
    'Set 행의 Q=1을 반대쪽에 되먹이면 Q′=(1·1)′=0으로 돌아와요.',
    p('11에 대한 자료의 1·Invalid·대시는 같은 부정 행을 가리켜요. 실제 출력값과 금지 여부를 함께 써요.'),
    ['앞단 출력을 먼저 적고, 교차 NAND 두 출력으로 표를 채워요.'],
    'C=1일 때 S·R이 10이면 Q 쪽 입력만 0이라 Set이에요. 11은 두 입력을 모두 0으로 만들어 Q=Q′=1이 돼요.')

E['q-rs-quiz'] = build('q-rs-quiz',
    '11에서 현재 Q와 반대 방향만 열어요',
    p('한 번 반전하려면 Q=0에서는 Set, Q=1에서는 Reset 요청만 열어야 해요.'),
    p('변형, 원래 회로의 금지 이유, 회로 이름을 답해요.'),
    p('정상 상태의 보수 출력 Q′을 Set 쪽에 표시해요.'),
    p('① 두 앞단을 3입력 NAND로 바꾸고 S 쪽 Q′, R 쪽 Q를 되먹여요. ② 원래 SR에서 C=1, S=R=1이면 Q=Q′=1이라 보수 관계가 깨져요. 두 명령을 함께 해제한 뒤 상태는 미정이에요. ③ 변형한 회로는 JK 래치이며 S가 J, R이 K가 돼요.') +
    figure('solutions/q-rs-quiz-solution-01.svg', 'S 쪽 3입력 NAND에 Q′, R 쪽 3입력 NAND에 Q를 되먹인 변형 회로'),
    p('완성 회로에서 J 쪽 Q′와 K 쪽 Q를 확인해요.'),
    'J=K=C=1에 Q=0과 Q=1을 각각 넣으면 활성 앞단이 바뀌어 한 번의 갱신 결과가 각각 1과 0이에요.',
    p('되먹임을 반대로 연결하면 반전되지 않아요. 표의 한 번 반전에는 짧은 C 펄스가 필요하고 C=1을 오래 유지하면 race-around가 생겨요.'),
    ['되먹임 두 선을 그린 뒤 원래 11의 문제와 변형 회로 이름을 써요.'],
    '① 두 앞단을 3입력 NAND로 바꾸고 S 쪽 Q′, R 쪽 Q를 되먹여요. ② 원래 SR에서 C=1, S=R=1이면 Q=Q′=1이라 보수 관계가 깨져요. 두 명령을 함께 해제한 뒤 상태는 미정이에요. ③ 변형한 회로는 JK 래치이며 S가 J, R이 K가 돼요.')

E['q-dff-table'] = build('q-dff-table',
    'NOT을 거친 S′이 Reset 쪽으로 가요',
    p('그림에서 S가 데이터 역할이고 아래 앞단은 S′을 받으므로, Enable D 래치의 두 행이 나와요.'),
    p('Q와 Q′의 세 행을 채워요.'),
    p('C=1, S=0이면 아래 앞단만 0이라 Q′=1부터 적어요.'),
    p('C=1에서는 두 명령이 동시에 1이 될 수 없어요. C=0이면 앞단 출력이 모두 1이라 직전 상태가 남아요.') +
    table(['S', 'C', 'Q', 'Q′'], [['0', '1', '0', '1'], ['1', '1', '1', '0'], ['X', '0', 'Q(t−1)', 'Q′(t−1)']]),
    p('C=1에서 Q=S, Q′=S′이고 C=0에서는 두 출력이 유지돼요.'),
    'C=1, S=1이면 위 앞단 NAND가 (1·1)′=0을 내므로 Q=1이에요.',
    p('제목의 F/F와 달리 그림은 레벨 래치예요. 기출 단답형의 둘째 행 “0 1 1”은 오기로 보이며 회로에서 Q=1인 행의 S는 1이에요.'),
    ['NOT이 붙은 쪽을 따라가서 두 활성 행과 유지 행을 채워요.'],
    'C=1에서는 두 명령이 동시에 1이 될 수 없어요. C=0이면 앞단 출력이 모두 1이라 직전 상태가 남아요.')

E['q-dff-design'] = build('q-dff-design',
    'C=1 구간의 Q=D는 레벨 래치 동작이에요',
    p('표가 C=1인 동안 D를 따라가라고 하므로 Enable SR 래치에서 두 명령을 한 입력으로 만들어요.'),
    p('주어진 표를 구현하는 회로를 그려요.'),
    p('S=D, R=D′으로 연결해요.'),
    p('NOT 1개와 NAND 4개를 써요. D와 D′은 동시에 1이 될 수 없어 C=1에서는 D 값이 Set 또는 Reset 하나를 골라요.') +
    figure('solutions/q-dff-design-solution-01.svg', 'D와 D′이 C와 함께 앞단 NAND 두 개로 들어가고 교차 NAND 두 개가 Q와 Q′을 내는 D 래치'),
    p('회로에서 D와 D′이 각 앞단에 하나씩 들어가고 C는 공통이에요.'),
    '활성 때 D=0·1을 각각 넣어 Q=0·1을 확인해요. C=0에서 앞단 두 출력은 1이므로 이전 Q(t−1)이 남아요.',
    p('D를 양쪽에 그대로 보내면 D=C=1에서 금지 입력이 생겨요. 엣지형 D F/F는 C=1 도중 바뀐 D를 반영하지 못해요.'),
    ['D·D′과 C를 앞단에 배선하고 표의 세 행을 확인해요.'],
    'NOT 1개와 NAND 4개를 써요. D와 D′은 동시에 1이 될 수 없어 C=1에서는 D 값이 Set 또는 Reset 하나를 골라요.')

E['q-jkff-short'] = build('q-jkff-short',
    '3입력 NAND에서 Q′과 Q의 되먹임을 따라가요',
    p('J에는 Q′, K에는 Q가 되먹여져 현재 출력에 따라 Set·Reset 중 한쪽만 열려요.'),
    p('JK 표의 다섯 행을 채워요.'),
    p('C=0이면 두 앞단 출력이 1이라 유지 행부터 적어요.'),
    p('C=1, JK=11에서 기존 Q=0이면 J 쪽, Q=1이면 K 쪽만 열려 한 번 갱신할 때 값이 뒤집혀요.') +
    JK_A,
    p('완성표의 Q(t−1)은 갱신 직전 저장값이에요.'),
    'C=1의 각 행은 한 번의 갱신식 Qnext=J·Q′+K′·Q에 이전 Q=0·1을 각각 넣어 확인해요.',
    p('그림은 레벨 래치예요. 11의 단일 반전은 한 번 갱신한 뒤 되먹임이 재반영되기 전에 C가 닫히는 조건이고, 긴 C=1에서는 race-around가 생겨요.'),
    ['활성 행마다 이전 Q를 두 값으로 바꿔 표를 채워요.'],
    'C=1, JK=11에서 기존 Q=0이면 J 쪽, Q=1이면 K 쪽만 열려 한 번 갱신할 때 값이 뒤집혀요.')

E['q-jkff-design'] = build('q-jkff-design',
    '11에서 한쪽 요청만 열리도록 앞단을 바꿔요',
    p('11→Q(t−1)′을 만들려면 현재 Q가 0일 때 Set, 1일 때 Reset만 허용해요.'),
    p('진리표를 만족하는 게이트 회로를 그려요.'),
    p('J 쪽은 J·C·Q′, K 쪽은 K·C·Q를 받게 해요.'),
    p('3입력 NAND 2개와 교차 2입력 NAND 2개로 구성해요. 정상 보수 상태에서는 C=1이어도 두 요청이 동시에 활성화되지 않아요.') +
    figure('solutions/q-jkff-design-solution-01.svg', 'J, C, Q′이 첫 3입력 NAND, K, C, Q가 둘째 3입력 NAND로 들어가는 JK 래치') +
    '<p>$$Q(t)=J\\,\\overline{Q(t-1)}+\\overline{K}\\,Q(t-1)$$</p>',
    p('식은 C=1에서 한 번 갱신한 결과예요.'),
    'J=K=C=1, Q=1을 대입하면 K 쪽 NAND=0으로 Q=0이에요. Q=0에서 반대 방향과 C=0의 유지도 확인해요.',
    p('되먹임을 바꾸면 11 반전이 깨져요. 레벨 회로의 긴 C=1에서는 race-around가 생겨요. 엣지 해석이 필요한 경우에는 하강 엣지형 74HC76을 구분해요.'),
    ['두 되먹임 선을 그린 뒤 11을 Q=0과 1에서 각각 검산해요.'],
    '3입력 NAND 2개와 교차 2입력 NAND 2개로 구성해요. 정상 보수 상태에서는 C=1이어도 두 요청이 동시에 활성화되지 않아요.')

E['q-tff'] = build('q-tff',
    'JK 표에서 유지와 반전 두 행을 골라요',
    p('T는 유지와 반전만 필요해요. JK 표에서 해당하는 입력은 00과 11이므로 두 입력에 같은 값을 주면 돼요.'),
    p('배선과 T 값별 동작을 답해요.'),
    p('J=K=T로 연결해요.'),
    p('엣지 직전 Q를 기준으로 00은 Q, 11은 Q의 보수를 내요.') +
    figure('tff-from-jk.svg', 'T 입력이 J와 K에 함께 연결되고 CLK가 원이 붙은 클록 단자에 연결된 J-K 플립플롭') +
    table(['T', 'J', 'K', '클록 엣지 후 Q'], [['0', '0', '0', 'Q(t−1) 유지'], ['1', '1', '1', 'Q(t−1)′ Toggle']]),
    '<p>$$Q(t)=T\\oplus Q(t-1)$$</p>',
    '74HC76에서 T=1, 초기 Q=0이면 세 번의 하강 엣지 뒤 Q가 차례로 1, 0, 1이에요.',
    p('JK의 11은 정상 Toggle이에요. 초기 Q가 주어지지 않으면 식에 이전 Q를 그대로 남겨요. 레벨 JK의 긴 활성 구간에서는 반복 반전할 수 있어요.'),
    ['J=K를 만족하는 두 행을 골라 배선과 출력식을 써요.'],
    '비동기 제어가 비활성이고 T가 안정된 지정 엣지에서만 갱신해요.')

E['q-74hc76'] = build('q-74hc76',
    'PR·CLR은 각각 Low에서 비동기로 작동해요',
    p('회로 기호에서 PR·CLR의 반전 표시는 0이 활성이라는 단서예요. 비동기 입력이므로 클록과 J·K보다 먼저 적용해요.'),
    p('두 제어 핀의 입력값과 Q의 관계를 답해요.'),
    p('입력 순서를 (PR, CLR)로 고정하고 한 핀만 활성인 두 행부터 써요.'),
    p('활성인 핀이 클록 변화 없이 Q를 바로 정해요.') +
    table(['PR', 'CLR', 'Q'], [['0', '1', '1 (Preset)'], ['1', '0', '0 (Clear)'], ['1', '1', '클록·J·K에 따라 동작'], ['0', '0', '사용하지 않음']]) +
    figure('hc76-pinout.svg', '74HC76 16핀 배치. 2번 1PR, 3번 1CLR, 5번 VCC, 13번 GND'),
    p('(PR, CLR)이 (0, 1)이면 Q=1, (1, 0)이면 Q=0이에요.'),
    '교안 11쪽과 데이터시트의 Set·Reset 행에서 Q의 극성을 대조해요.',
    p('두 핀에 동시에 0을 넣는 조합은 피하고, 동시에 해제한 뒤의 Q는 미정으로 둬요. 종합본은 PR·CLR 결과를 뒤집었고, 기출 단답형은 둘 다 Q=0으로 적었어요. 교안과 데이터시트의 표를 기준으로 해요.'),
    ['(0, 1), (1, 0), (1, 1)을 순서대로 보고 각 동작을 써요.'],
    'PR만 0이면 Q=1, CLR만 0이면 Q=0이에요.')

E['q-74hc574'] = build('q-74hc574',
    'CP는 저장, OE는 출력 핀을 제어해요',
    p('74HC574에서는 D를 저장하는 순간과 저장값이 핀에 보이는 조건을 구분해요.'),
    p('입력이 저장되는 시점을 써요.'),
    p('CP=0→1을 표시하고 엣지의 D를 읽어요.'),
    p('지정 엣지에서 안정된 8비트 D를 저장해요. OE=0이면 저장값이 핀에 나오고, OE=1이면 핀만 High-Z가 돼요.'),
    p('입력 저장은 CP의 상승 엣지 순간에 일어나요.'),
    'OE=1에서 D=1을 저장한 뒤 CP를 고정하고 D=0, OE=0으로 바꾸면 핀에서 이전 값 1이 나와요.',
    p('제공 답안은 “한 clock 지속기간 동안”과 “low에서 high로 상승할 때”를 함께 썼어요. 엣지 순간이 맞아요. 소자 사양은 Nexperia Rev. 10, 1–4쪽을 기준으로 해요.'),
    ['저장 엣지와 핀에 값이 보이는 OE 조건을 따로 표시해요.'],
    '지정 엣지에서 안정된 8비트 D를 저장해요. OE=0이면 저장값이 핀에 나오고, OE=1이면 핀만 High-Z가 돼요.')

TR = PR.TRACE
E['q-p-76-trace'] = build('q-p-76-trace',
    '비동기 제어부터 보고 ↓에서만 J·K를 읽어요',
    p('PR 또는 CLR 중 하나만 0이면 해당 비동기 제어가 클록 없이 Q를 정해요. 둘 다 1이면 ↓에서만 J·K를 적용해요.'),
    p('각 단계 뒤 Q를 채워요.'),
    p('1단계는 PR=0, CLR=1이어서 미정이던 Q가 1로 정해져요.'),
    p('3단계는 ↑라 Q=1을 유지해요. 5·6단계는 연속해서 반전해요. 8단계는 CLR=0이라 Q=0이에요.') +
    table(['단계', 'PR', 'CLR', 'CLK', 'J', 'K', 'Q'],
          [[str(n), str(pr), str(clr), PR.CLK_TXT[e], str(j), str(k), str(q)] for (n, pr, clr, e, j, k), q in zip(TR, PR.TRACE_Q)]),
    p('1~8단계 Q는 1·1·1·0·1·0·1·0이에요.'),
    '검산용으로 8단계 직전 Q=0과 하강 엣지를 가정해도 CLR=0이라 Q=0이에요. JK만 적용하면 1이 나와요.',
    p('연속한 ↓ 사이의 ↑는 문제 표에서 생략돼요. ↑에서는 J·K로 Q를 갱신하지 않아요.'),
    ['각 행에서 비동기 제어와 ↓를 순서대로 확인하고 Q를 다음 행에 넘겨요.'],
    '1단계 Preset이 초기 Q를 정하고 8단계 Clear가 Toggle보다 우선해요.')

assert set(E) == set(PR.P)

# 전체 갱신의 자체 출제 문항도 같은 정본 E에서 내보내요.
from quiz import E as QUIZ_E
E.update(QUIZ_E)
