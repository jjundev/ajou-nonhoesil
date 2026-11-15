"""실험06 자체 출제 10문항과 풀이 원고. 교안 쪽수는 실제 PDF 기준."""
import json
from pathlib import Path
from h import p, table
from recall import QUIZ_RECALL

MAN = 's-a9792f60486135b0'
BOARD = 's-df4e3850c9b9d3a3'

# type, id suffix, title, topic, page, condition, ask, answer, reason, check, pitfall
ITEMS = [
 ('true_false','tf-01','Enable이 꺼진 SR 래치','t-sr-enable',7,
  '이상적인 Enable SR 래치가 정상 상태로 초기화되어 있어요. E=0을 유지해요.',
  'S와 R이 바뀌어도 Q는 직전 값을 유지한다. T/F를 고르세요.', 'T',
  'E=0이면 앞단 NAND 두 출력은 S·R과 무관하게 모두 1이에요. 뒤의 교차 NAND는 마지막 안정 상태를 유지해요.',
  'Q=0과 Q=1 각각에서 S·R 네 조합을 넣어도 같은 상태인지 확인해요.',
  '유지는 Q=0이라는 뜻이 아니에요. 초기 Q가 1이면 1을 지켜요.'),
 ('true_false','tf-02','D 래치의 투명 구간','t-d-latch',8,
  '이상적인 D 래치에서 E=1이고 전파 지연 뒤의 안정 출력만 봐요.',
  'D가 0에서 1로 바뀌면 클록 엣지가 없어도 Q는 1로 바뀐다. T/F를 고르세요.', 'T',
  'D 래치는 레벨 트리거예요. E=1인 동안 S=D, R=D′이므로 D=1이면 Set되어 Q=1이에요.',
  'E=1에서 D=0일 때 Q=0, D=1일 때 Q=1을 각각 대입해요.',
  'D라는 이름만 보고 엣지 트리거 D 플립플롭과 혼동하지 않아요.'),
 ('true_false','tf-03','74HC76의 동작 엣지','t-74hc76',11,
  '교안의 74HC76에서 비동기 SET·RESET은 모두 비활성(High)이고 J=K=1이에요. 입력의 setup/hold 조건을 만족해요.',
  'CLK가 0에서 1로 올라가는 순간에 Q가 반전된다. T/F를 고르세요.', 'F',
  '교안의 74HC76은 하강 엣지에서 동작해요. J=K=1이면 CLK가 1→0으로 떨어질 때 Q가 반전돼요.',
  'Q=0에서 상승 엣지만 주면 0을 유지하고, 다음 하강 엣지에서 1이 되는지 확인해요.',
  'JK의 Toggle 조건과 소자의 유효 클록 엣지를 따로 확인해요.'),
 ('true_false','tf-04','SR 부정 상태의 두 출력','t-sr-enable',7,
  '교안의 NAND 4개로 만든 Enable SR 래치에서 E=S=R=1을 유지하고 전파 지연이 지난 상태예요.',
  '이때도 Q′은 반드시 Q의 보수이다. T/F를 고르세요.', 'F',
  '앞단 NAND가 모두 0을 내므로 뒤의 NAND 두 출력은 Q=Q′=1이에요. 보수 관계가 깨지는 부정 상태라 사용하지 않아요.',
  '앞단: NAND(1,1)=0, 뒤단: NAND(0,어떤 값)=1을 양쪽에 적용해요.',
  '진리표의 부정 X를 입력 don’t-care나 Q=0으로 해석하지 않아요. 동시에 해제한 뒤의 상태도 보장하지 않아요.'),
 ('fill_blank','blank-01','SR 래치의 세 명령','t-sr-enable',7,
  '정상 초기화된 Enable SR 래치에서 E=1이에요. S·R은 Active High 명령이에요.',
  '(S,R)=(1,0)이면 ① (Set/Reset), (0,1)이면 ② (Set/Reset), (0,0)이면 직전 값을 ③ (유지/반전)해요.',
  '① Set, ② Reset, ③ 유지',
  'S=1,R=0은 Q를 1로 정하는 Set, S=0,R=1은 Q를 0으로 정하는 Reset이에요. S=R=0이면 앞단이 모두 1이 되어 기억 상태를 지켜요.',
  '직전 Q를 0과 1로 바꾸어도 ①의 Q는 1, ②의 Q는 0이고, ③은 각각 0·1인지 확인해요.',
  'Enable 없는 기본 NAND 래치의 Active Low 입력표를 그대로 옮기지 않아요.'),
 ('fill_blank','blank-02','D 래치의 입력과 기억','t-d-latch',8,
  '이상적인 D 래치에 안정된 입력을 넣어요. Q이전은 E를 0으로 바꾸기 직전의 출력이에요.',
  'SR 래치의 S=D, R=① (D/D′)로 묶어요. E=1이면 Q=② (D/Q이전), E=0이면 Q=③ (D/Q이전)이에요.',
  '① D′, ② D, ③ Q이전',
  'R은 D의 보수 D′이어야 S와 R이 동시에 1이 되지 않아요. E=1이면 D가 Q에 반영되고 E=0이면 마지막 상태를 유지해요.',
  'D=0이면 (S,R)=(0,1), D=1이면 (1,0)이에요. 그 뒤 E=0에서 D를 바꿔도 Q는 그대로인지 확인해요.',
  '①은 D의 보수·NOT D·D̄도 인정해요. ③은 현재 D가 아니라 직전 출력이에요.'),
 ('fill_blank','blank-03','74HC76의 비동기 우선순위','t-74hc76',11,
  '교안의 74HC76이고 입력은 안정되어 있어요. SET·RESET은 Active Low예요. 두 제어를 동시에 0으로 넣지 않아요.',
  'J·K의 클록 동작을 보려면 SET=RESET=① (Low/High)로 둬요. SET=1, RESET=0이면 CLK·J·K와 무관하게 Q=② (0/1)이에요. 둘 다 1이고 J=K=1이면 유효 하강 엣지에서 Q는 직전 값의 ③ (보수/동일값)가 돼요.',
  '① High, ② 0, ③ 보수',
  'Active Low 제어는 0에서 활성이라 정상 클록 동작에는 둘 다 1이 필요해요. RESET만 0이면 비동기 리셋이 우선하여 Q=0이에요. 정상 모드에서 J=K=1이면 하강 엣지마다 Toggle해요.',
  '클록이 정지해도 RESET=0이면 Q=0이에요. RESET 해제 후 정상 엣지에서 Q가 반전되는지 따로 확인해요.',
  '①은 1·H, ③은 반전값·NOT Q도 인정해요. RESET=0일 때 Toggle 공식을 먼저 적용하지 않아요.'),
 ('breadboard','board-01','Enable SR 래치 작도','t-sr-enable',7,
  '74HC00(DIP-14) 한 개, +5V/GND와 S·E·R 입력을 사용해요. 출력은 고입력 임피던스 계측기로 Q·Q′을 관찰해요(LED·저항 추가 없음). 전원을 끄고 배선해요. 입력은 항상 0V 또는 +5V에 연결하며 띄우지 않아요. 모든 게이트를 사용하므로 미사용 핀은 없어요. 빨강 잭=+5V, 회색 잭=GND, 노랑 잭은 사용하지 않아요.',
  '주어진 논리 회로와 핀 명세를 보고 v1 양식에 칩 방향, 전원, S·E·R, 게이트 사이 배선과 Q·Q′ 관측점을 작도하세요. 칩 위치는 자유예요.',
  '14→+5V, 7→GND; S→1, E→2·4, R→5; 3→9, 6→13, 8→12, 11→10; Q=8, Q′=11',
  '먼저 NOT bubble이 있는 NAND 네 개를 찾아요. S·E를 첫 게이트, R·E를 둘째 게이트에 넣고, 두 출력을 교차 NAND 입력으로 보내요. Q와 Q′은 반대쪽 게이트 입력으로 되먹여요.',
  'E=0 유지, E=1에서 (S,R)=10 Set·01 Reset·00 유지·11 부정을 확인해요. 핀 넷은 완성 연결표와 같아야 해요.',
  '같은 행의 a~e와 f~j는 각각 연결되지만 중앙 홈을 건너서는 연결되지 않아요. 선이 그림에서 교차해도 연결점이 없으면 도통하지 않아요. 출력끼리 묶거나 전원 레일을 단락하지 않아요.'),
 ('short_answer','short-01','SR 래치는 어떻게 기억할까요','t-sr-enable',7,
  '교안의 Enable SR 래치예요. 먼저 E=1,S=1,R=0으로 Set한 다음 S=R=0으로 바꿔요. 전파 지연 뒤의 안정 상태를 설명해요.',
  '출력 Q의 변화, 입력 명령이 사라진 뒤 값을 유지하는 원리와 E=0의 역할을 3~4문장으로 설명하세요.',
  'Set으로 Q=1이 돼요. S=R=0으로 돌아와도 교차 되먹임이 Q=1,Q′=0을 유지해요. E=0이면 S·R의 변화가 저장부에 전달되지 않아 직전 상태를 지켜요.',
  '앞단은 명령을 전달하거나 차단하고, 뒤의 교차 NAND는 출력을 서로 입력으로 돌려보내요. 유지 명령에서 두 NAND가 서로의 현재 값을 지지하므로 새 명령 전까지 기억해요.',
  'Set 뒤 (Q,Q′)=(1,0)을 두 교차 NAND에 다시 넣어도 같은 출력이 나오는지 확인해요.',
  '“전기가 남아 있어서”만으로는 되먹임 원리를 설명하지 못해요. 전원이 차단되어도 영구 보존된다고 쓰지 않아요.'),
 ('short_answer','short-02','74HC76에서 비동기 제어를 High로 두는 이유','t-74hc76',11,
  '교안의 74HC76 JK 플립플롭에서 J·K에 따른 정상 클록 동작을 관찰하려고 해요.',
  'SET·RESET을 High로 두는 이유, 둘 중 하나만 Low일 때의 Q, 정상 모드에서 출력이 갱신되는 클록 순간을 3~4문장으로 설명하세요.',
  'SET·RESET은 Active Low 비동기 제어이므로 둘 다 High로 두어 비활성화해요. SET만 Low이면 Q=1, RESET만 Low이면 Q=0이며 클록보다 우선해요. 둘 다 High일 때 교안의 74HC76은 하강 엣지에서 J·K에 따라 Q를 갱신해요.',
  '비동기는 클록을 기다리지 않는다는 뜻이에요. 한 제어라도 활성이라면 J·K의 기능표보다 그 명령이 먼저 출력에 반영돼요. 제어를 해제한 정상 모드에서만 유효 클록 엣지를 따져요.',
  'CLK를 고정한 채 SET만 0/RESET만 0인 두 경우와, 두 제어를 1로 둔 하강 엣지 경우를 구분해요.',
  'High가 Set 명령이라는 뜻이 아니에요. 두 제어의 동시 Low는 정상 사용 조건에서 제외해요.'),
]

def ref(page):
    return dict(source_id=MAN,pdf_page=page,printed_page=None)

def workbook(item):
    typ,suffix,title,topic,page,condition,ask,answer,reason,check,pitfall=item
    labels={'true_false':['판정 근거','문장 확인'],'fill_blank':['빈칸별 근거'],
            'breadboard':['연결 기준','완성 결선도'],'short_answer':['채점 핵심','허용 표현']}[typ]
    steps=[dict(label=labels[0],html=p(reason))]
    if typ=='true_false':steps.append(dict(label=labels[1],html=p(('바른 문장: '+ ('74HC76은 하강 엣지에서 반전돼요.' if suffix=='tf-03' else '이 조건에서는 Q=Q′=1이라 보수 관계가 깨져요.')) if answer=='F' else '주어진 초기화·활성 조건에서 성립해요. '+check)))
    if typ=='short_answer':
        steps[0]['html']+=p('채점 요소: '+answer)
        steps.append(dict(label=labels[1],html=p('되먹임/피드백, 유지/저장, High/1, 하강 엣지/1→0처럼 의미가 같은 표현을 인정해요. '+pitfall)))
    if typ=='breadboard':
        steps[0]['html']+=table(['넷','연결'],[['전원','14: +5V / 7: GND'],['입력','S:1 / E:2·4 / R:5'],['앞단','3–9 / 6–13'],['되먹임','8–12 / 11–10'],['관측','Q:8 / Q′:11']])
        steps.append(dict(label=labels[1],html='<img src="figures/solutions/q-qp-e06-board-01-complete.png" width="270" style="max-width:100%;height:auto" alt="v1 PDF 위 Enable SR 래치 완성 결선도">'+p('예시는 초기 입력을 0으로 그렸어요. 점퍼의 레일 쪽 끝만 옮겨 입력을 바꿔요. 위치가 달라도 동일 넷이면 인정해요.')))
    obj=dict(original=p('자체 출제 · '+title),conditions=p(condition),ask=p(ask),problem_figures=[],
             hints=[dict(label='접근 순서',html=p('활성 조건을 먼저 표시하고 현재 입력과 직전 상태를 구분해요.' if typ!='breadboard' else '전원 핀과 NAND 게이트 묶음을 먼저 찾고, 회로도의 연결점을 넷 단위로 따라가요.'))],
             solution=dict(steps=steps,answer=p(answer)),notes=[check,pitfall])
    if typ=='breadboard':
        pins=[['1·2→3','1A·1B→1Y','NAND 입력→출력'],['4·5→6','2A·2B→2Y','NAND 입력→출력'],['9·10→8','3A·3B→3Y','NAND 입력→출력'],['12·13→11','4A·4B→4Y','NAND 입력→출력'],['7','GND','0V'],['14','VCC','+5V']]
        obj['conditions']+=table(['핀','이름','역할'],pins).replace('<table>','<table class="chip-spec">')+'<div class="work-board"><img src="figures/questions/q-qp-e06-board-01-blank.png" alt="v1 PDF 원본 전체 작도 양식"></div>'
        obj['problem_figures']=['q-qp-e06-board-01-circuit']
    return obj

# Summary-only conditions; question, recall body and workbook data stay independent.
SUMMARY_NOTES = {'q-qp-e06-tf-01': '정상 상태로 초기화된 이상 래치의 E=0·전파 지연 뒤 안정 상태 조건이에요. 유지는 Q=0을 뜻하지 않아요.',
 'q-qp-e06-tf-02': '이상적인 D 래치에서 전파 지연 뒤의 안정 출력을 보는 조건이며, 엣지형 D 플립플롭과 구분해요.',
 'q-qp-e06-tf-03': 'SET·RESET 둘 다 High로 비동기 제어를 해제하고 입력 setup/hold 조건을 만족할 때의 판단이에요.',
 'q-qp-e06-tf-04': 'E=S=R=1을 유지한 전파 지연 뒤 조건이에요. 부정 X는 입력 don’t-care나 Q=0이 아니며 동시 해제 뒤 상태도 보장 못 해요.',
 'q-qp-e06-blank-01': '정상 초기화·E=1인 Enable SR의 High 활성 명령 조건이에요. Enable 없는 기본 NAND의 Low 활성 표와 섞지 않아요.',
 'q-qp-e06-blank-03': '안정 입력의 교안 74HC76 조건이고 SET·RESET을 동시에 0으로 넣지 않아요.',
 'q-qp-e06-board-01': '전원을 끄고 결선하고 입력은 0V/+5V에 고정해 띄우지 않아요. 출력은 고입력 임피던스 계측기로 관찰하며 LED·저항은 추가하지 않아요. 중앙 홈 '
                      '양쪽은 분리되고 교차선은 접속점 없으면 연결되지 않아요. 출력끼리 결합·전원 레일 단락을 피해요.',
 'q-qp-e06-short-01': '먼저 E=1·S=1·R=0으로 Set한 뒤 S=R=0인 안정 상태를 설명해요. 전원이 차단되어도 영구 보존된다는 뜻은 아니에요.',
 'q-qp-e06-short-02': 'High는 Set 명령이 아니라 비동기 제어 비활성이며 두 제어의 동시 Low는 정상 사용에서 제외해요.'}


def explanation(item):
    typ,suffix,title,topic,page,condition,ask,answer,reason,check,pitfall=item
    cue, concept, first_step = QUIZ_RECALL[suffix]
    recall = p(concept)
    start = p(first_step) + f'<p>개념으로 돌아가기: <a href="{{{{NOTE_HREF}}}}#{topic}">해당 동작 원리</a></p>'
    obj=workbook(item)
    solve=''.join(p(s['label'])+s['html'].replace('src="figures/','src=".pack/figures/').replace(' style="max-width:100%;height:auto"','') for s in obj['solution']['steps'])
    if typ=='breadboard':solve=solve.replace('<img ','<figure class="figure"><img ').replace('alt="v1 PDF 위 Enable SR 래치 완성 결선도">','alt="v1 PDF 위 Enable SR 래치 완성 결선도"></figure>')
    def layer(key,cls,label,html):return f'<div class="layer {cls}" data-explanation="{key}"><span class="layer-title">{label}</span>{html}</div>'
    pid = 'q-qp-e06-' + suffix
    summary_note = p(SUMMARY_NOTES[pid]) if pid in SUMMARY_NOTES else ''
    return (layer('understand','eli5','이 문제에서 할 일',p(ask)+p('입력의 이름만 외우지 않고 활성 조건에서 출력이 왜 그렇게 되는지 확인해요.'))+
      layer('recall','formal','이 문제를 봤을 때 떠올릴 개념과 공식',f'<p class="lead cue">{cue}</p>'+recall)+
      layer('start','formal','첫 줄을 이렇게 시작해요',start)+layer('solve','formal','이유를 따라 완성해요',solve)+
      layer('verify','formal','완성 답과 검산',p(answer)+p(check))+layer('pitfall','warn','이 실수를 피하세요',p(pitfall))+
      layer('retry','formal','설명을 닫고 다시 풀어요','<ol><li>문제의 활성 조건을 표시해요.</li><li>첫 판단에서 정답까지 이유를 써요.</li><li>반대 상태나 경계 조건으로 검산해요.</li></ol>')+
      f'<div class="sum" hidden><p><strong>떠올릴 것:</strong> {cue}</p><p data-summary="recall">{reason}</p><p>답: {answer}</p><p>검산: {check}</p>{summary_note}</div>')

E={'q-qp-e06-'+i[1]:explanation(i) for i in ITEMS}

def apply(run,manifest):
    from quiz_figures import create
    create(run,manifest)
    manifest['quiz_practice_version']=1
    for item in ITEMS:
        typ,suffix,title,topic,page,condition,ask,answer,reason,check,pitfall=item
        pid='q-qp-e06-'+suffix
        refs=[ref(page)]
        if typ=='breadboard':refs.append(dict(source_id=BOARD,pdf_page=1,printed_page=None))
        manifest['problems'].append(dict(id=pid,title=title,kind='practice',question_type=typ,status='included',reason='새 퀴즈 유형 연습: 교안 조건에서 자체 출제하고 안정 상태·전이로 검산',topics=[topic],sources=refs,duplicate_of=None,scope='current',given_answer=None,derived_answer=answer,answer_status='verified',workbook_fragment=f'workbook/{pid}.json',explanation_fragment=f'problem-explanations/{pid}.html'))
        (run/'workbook'/f'{pid}.json').write_text(json.dumps(workbook(item),ensure_ascii=False,indent=2),encoding='utf-8')
        (run/'problem-explanations'/f'{pid}.html').write_text(E[pid],encoding='utf-8')
