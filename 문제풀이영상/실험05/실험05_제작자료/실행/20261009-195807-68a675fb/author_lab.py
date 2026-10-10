"""실험05 실측 저작 도구. 쪽마다 사람이 native.png·PDF 줄 좌표를 보고 정한 step·줄 경계·띠를 받아 map/manifest/검토 파일을 쓴다.

사용: .venv/bin/python <batch>/author_lab.py <problem_id>
문항별 값(SPECS)은 이 파일 아래쪽에 있다. 자동 읽기 순서 추정은 하지 않는다 — 줄 경계와 띠는 직접 검토한 값이다.
"""
import re,sys,pathlib
root=pathlib.Path.cwd();skill=root/'.claude/skills/logic-lab-solution-video';sys.path[:0]=[str(skill/'scripts')]
import importlib.util
spec=importlib.util.spec_from_file_location('solution_cli',skill/'scripts/video.py');video=importlib.util.module_from_spec(spec);spec.loader.exec_module(video)
from types import SimpleNamespace
from solution_video.util import read,write
from solution_video.pdf_pages import inside
from solution_video.manifest import content_fingerprint
from solution_video.writing_units import compile_writing_units
BATCH=pathlib.Path(__file__).resolve().parent

def center_y(o):return (o['bbox'][1]+o['bbox'][3])/2

def units_for(step_id,glyphs,shapes,breaks,table_cuts):
    """breaks: 줄 경계(y). table_cuts: {줄 번호: [x 경계...]} — 표 줄은 열 경계로 띠를 자르고, 나머지 줄은 띠 하나."""
    bins=[[] for _ in range(len(breaks)+1)]
    for kind,o in [('glyph',g) for g in glyphs]+[('shape',s) for s in shapes]:
        # A tall answer-card background/bar opens with its '답' label line instead of being sliced by the text bands.
        tall=kind=='shape' and o.get('kind')=='answer_box' and o['bbox'][3]-o['bbox'][1]>30
        bins[0 if tall else sum(center_y(o)>=e for e in breaks)].append((kind,o))
    units=[]
    for ri,targets in enumerate(bins):
        if not targets:continue
        left=min(o['bbox'][0] for _,o in targets);right=max(o['bbox'][2] for _,o in targets)
        cuts=table_cuts.get(ri)
        if not cuts:
            # Word-cluster bands as upstream authored_writing does: only the first unit of a new line is a lifted move.
            spans=sorted((o['bbox'][0],o['bbox'][2]) for kind,o in targets if o['bbox'][2]-o['bbox'][0]>.5 and (kind=='glyph' and not o['text'].isspace() or kind=='shape' and o['bbox'][2]-o['bbox'][0]<30))
            merged=[]
            for lo,hi in spans:
                if merged and lo<merged[-1][1]:merged[-1][1]=max(hi,merged[-1][1])
                else:merged.append([lo,hi])
            cuts=sorted(set([left,right]+[(a[1]+b[0])/2 for a,b in zip(merged,merged[1:])]))
        if right-left<1:cuts=[left,left+1]
        line=f'line_{step_id}_{ri}'
        for bi,(lo,hi) in enumerate(zip(cuts,cuts[1:])):
            sel={'glyph':[],'shape':[]}
            for kind,o in targets:
                b=o['bbox'];zero=b[2]==b[0] or kind=='glyph' and o['text'].isspace()
                last=bi==len(cuts)-2
                if zero and (lo<=b[0]<hi or last and b[0]==hi) or not zero and b[0]<hi and b[2]>lo:sel[kind].append(o['id'])
            if sel['glyph'] or sel['shape']:
                units.append(dict(id=f'u_{step_id}_{ri}_{bi}',line_id=line,chunk_id=f'c_{step_id}_{ri}',column_id='main',band=[lo,hi],glyph_ids=sel['glyph'],shape_ids=sel['shape'],camera_break_before=False))
    return units

def md_section(md,pid):
    body=md.split(f'<a id="{pid}"></a>',1)[1]
    body=re.split(r'\n<a id="',body,maxsplit=1)[0]
    return {m[1]:m[2].strip() for m in re.finditer(r'### (풀이 \d+ · [^\n]+|최종 답)\n(.*?)(?=\n### |\Z)',body,re.S)}

def author(pid):
    spec=SPECS[pid];data=read(BATCH/'batch.json');item=next(i for i in data['items'] if i['id']==pid)
    run=BATCH/item['run'];pair=read(run/'source/pair.json');c=read(run/'layers/candidates.json')
    work=spec['work_bbox'];gs=[g for g in c['glyphs'] if inside(g['bbox'],work)];ss=[s for s in c['shapes'] if inside(s['bbox'],work)]
    steps=[]
    for st in spec['steps']:
        lo,hi=st['y']
        sg=[g for g in gs if lo<=center_y(g)<hi];sh=[s for s in ss if lo<=center_y(s)<hi]
        units=units_for(st['id'],sg,sh,st['breaks'],st.get('table_cuts',{}))
        order=[gid for u in units for gid in u['glyph_ids']];sorder=[sid for u in units for sid in u['shape_ids']]
        steps.append(dict(id=st['id'],glyph_ids=list(dict.fromkeys(order)),shape_ids=list(dict.fromkeys(sorder)),writing_units=units))
    assert sum(len(s['glyph_ids']) for s in steps)==len(gs),'glyph not assigned to a step'
    assert sum(len(s['shape_ids']) for s in steps)==len(ss),'shape not assigned to a step'
    mp=dict(work_bbox=work,steps=steps,answer_step_id=steps[-1]['id']);write(run/'source/map.json',mp)
    compile_writing_units(dict(glyphs=c['glyphs'],shapes=c['shapes'],map=mp))
    print('extract',video.run_stage('extract',run,SimpleNamespace())['gate'])
    l=read(run/'layers/layers.json');gid={g['id']:g for g in l['glyphs']};sid={s['id']:s for s in l['shapes']}
    ans='answer:'+str(pair['answer']['page_index']+1);prob='problem:'+str(pair['problem']['page_index']+1)
    segs=[dict(id='intro',kind='problem',step_id='',text=spec['intro'][0],caption_text=spec['intro'][1],source_refs=[prob])]
    for st in spec['steps']:
        for kind,(text,cap) in st.get('before',[]):segs.append(dict(id=f'{kind}_{st["id"]}',kind=kind,step_id=st['id'],text=text,caption_text=cap,source_refs=[ans,'md:'+st['md']]))
        segs.append(dict(id='write_'+st['id'],kind='write',step_id=st['id'],text=st['say'][0],caption_text=st['say'][1],source_refs=[ans,'md:'+st['md']]))
    cameras=[]
    if (run/'source/timeline.json').is_file():
        t=read(run/'source/timeline.json');done=max(x['end_frame'] for x in t['writing_spans'] if x['step_id']==steps[-1]['id'])
        last=max(x['end_frame'] for x in t['writing_spans'])
        if done==last and done+30<t['segments'][-1]['end_sample']//800:
            cameras=[dict(at_frame=done+15,viewbox=[0,0,l['metadata']['width_pt'],l['metadata']['height_pt']],transition_frames=12)]
    m=dict(schema_version=1,problem_id=pid,title=pair['title'],segments=segs,reveal_order=[g for s in steps for g in s['glyph_ids']],
           shape_anchors={s_:(st['glyph_ids'][0] if sid[s_]['kind']=='step_badge' else st['glyph_ids'][-1]) for st in steps for s_ in st['shape_ids']},cameras=cameras)
    md=md_section((run/pair['md_snapshot']).read_text(encoding='utf-8'),pid)
    cov=dict(status='passed',pdf_md_agree=True,rows=[dict(step_id=s['id'],source_refs=[ans,'md:'+st['md']],pdf_text=''.join(gid[g]['text'] for g in s['glyph_ids']),md_text=md[st['md']],meaning_review=st['review']+(' 그림 내용: '+st['figure_text'] if st.get('figure_text') else '')) for s,st in zip(steps,spec['steps'])])
    rev=dict(status='passed',steps=[dict(step_id=s['id'],assumptions=spec['assumptions'],equations=md[st['md']],units='없음(논리값 0·1)',evidence=st['evidence']) for s,st in zip(steps,spec['steps'])])
    h=content_fingerprint(m,l,cov);cov['input_hash']=rev['input_hash']=h
    for name,d in [('manifest',m),('coverage',cov),('circuit-review',rev)]:write(run/'source'/(name+'.json'),d)
    print('check',video.run_stage('check',run,SimpleNamespace()))

TABLE=[322.5,525.0,600.0,669.0,745.5]
SPECS={
'q-prio-exam':dict(
  work_bbox=[300,62,751,573],
  assumptions='번호가 큰 입력이 우선(원문 자료의 74HC148 해석). 출력 A2A1A0 는 선택된 입력 번호의 3비트 이진수. 원문 첫 행 0000 0001→000 유지.',
  intro=('기출 삼번이에요. 팔 대 삼 우선순위 인코더의 진리표에서 빈칸을 채우는 문제예요. 입력 디는 디 세븐부터 디 제로까지 여덟 비트이고, 번호가 큰 입력이 우선이라고 읽어요. 첫 행은 이미 채워져 있고, 나머지 다섯 행의 에이 투, 에이 원, 에이 제로를 구해요.',
         '기출 3번이에요. 8×3 우선순위 인코더의 진리표에서 빈칸을 채우는 문제예요. 입력 D는 D7부터 D0까지 여덟 비트이고, 번호가 큰 입력이 우선이라고 읽어요. 첫 행은 이미 채워져 있고, 나머지 다섯 행의 A2, A1, A0를 구해요.'),
  steps=[
   dict(id='sol',y=(62,150),breaks=[86,105,120],md='풀이 1 · 풀이',
        say=('번호가 큰 입력이 우선이니까, 각 행에서 가장 왼쪽에 있는 일을 찾고 그 번호를 이진수로 쓰면 돼요. 영영일일 일영일영에서 가장 왼쪽 일은 디 파이브라서 일영일이에요. 나머지도 같은 방법으로 디 식스는 일일영, 디 포는 일영영, 디 세븐은 일일일이에요.',
             '번호가 큰 입력이 우선이니까, 각 행에서 가장 왼쪽에 있는 1을 찾고 그 번호를 이진수로 쓰면 돼요. 0011 1010에서 가장 왼쪽 1은 D5라서 101이에요. 나머지도 같은 방법으로 D6은 110, D4는 100, D7은 111이에요.'),
        review='답안 3쪽 풀이 1 의 세 줄을 MD 풀이 1 과 대조: D5→101, D6→110, D4→100, D6→110, D7→111 일치.',evidence='각 입력에서 최상위 1 의 위치: 0011 1010→D5, 0101 1110→D6, 0001 1101→D4, 0110 0100→D6, 1111 1111→D7. 이진수 변환 5=101, 6=110, 4=100, 7=111.'),
   dict(id='table_head',y=(150,209.5),breaks=[185],table_cuts={1:TABLE},md='풀이 2 · 완성한 표',
        say=('이제 이 결과를 표로 정리해요. 맨 왼쪽 열은 입력 디의 여덟 비트이고, 오른쪽 세 열은 출력 에이 투, 에이 원, 에이 제로예요. 에이 투가 가장 높은 자리라서, 세 열을 이어 읽으면 선택된 입력의 번호가 이진수로 나와요.','이제 이 결과를 표로 정리해요. 맨 왼쪽 열은 입력 D의 여덟 비트이고, 오른쪽 세 열은 출력 A2, A1, A0예요. A2가 가장 높은 자리라서, 세 열을 이어 읽으면 선택된 입력의 번호가 이진수로 나와요.'),
        review='표 머리글 D·A2·A1·A0 를 MD 표 머리글과 대조.',evidence='표 열 구성은 원문 문제 표와 같다.'),
   dict(id='rows_a',y=(209.5,271.0),breaks=[229.8,250.8],table_cuts={0:TABLE,1:TABLE,2:TABLE},md='풀이 2 · 완성한 표',
        say=('첫 행 영영영영 영영영일은 켜진 비트가 디 제로 하나뿐이라서, 원문 그대로 영영영이에요. 두 번째 행 영영일일 일영일영은 켜진 비트가 여러 개지만, 그중 번호가 가장 큰 것이 디 파이브예요. 그래서 오를 이진수로 쓴 일영일이에요. 세 번째 행 영일영일 일일일영은 가장 큰 번호가 디 식스라서, 육을 이진수로 쓴 일일영이에요.','첫 행 0000 0001은 켜진 비트가 D0 하나뿐이라서, 원문 그대로 000이에요. 두 번째 행 0011 1010은 켜진 비트가 여러 개지만, 그중 번호가 가장 큰 것이 D5예요. 그래서 5를 이진수로 쓴 101이에요. 세 번째 행 0101 1110은 가장 큰 번호가 D6이라서, 6을 이진수로 쓴 110이에요.'),
        review='표 1~3행 값 000, 101, 110 을 MD 표와 대조.',evidence='0000 0001: 최상위 1=D0→000. 0011 1010: D5→101. 0101 1110: D6→110.'),
   dict(id='rows_b',y=(271.0,345),breaks=[292.0,312.3],table_cuts={0:TABLE,1:TABLE,2:TABLE},md='풀이 2 · 완성한 표',
        say=('네 번째 행 영영영일 일일영일은 위쪽 네 비트 중 디 포만 켜져 있어서, 사를 이진수로 쓴 일영영이에요. 다섯 번째 행 영일일영 영일영영은 디 식스와 디 파이브가 함께 켜져 있지만, 더 큰 디 식스가 이겨서 일일영이에요. 마지막 행은 여덟 비트가 모두 일이에요. 이때도 가장 큰 디 세븐만 보면 되니까, 칠을 이진수로 쓴 일일일이에요.','네 번째 행 0001 1101은 위쪽 네 비트 중 D4만 켜져 있어서, 4를 이진수로 쓴 100이에요. 다섯 번째 행 0110 0100은 D6과 D5가 함께 켜져 있지만, 더 큰 D6이 이겨서 110이에요. 마지막 행은 여덟 비트가 모두 1이에요. 이때도 가장 큰 D7만 보면 되니까, 7을 이진수로 쓴 111이에요.'),
        review='표 4~6행 값 100, 110, 111 을 MD 표와 대조.',evidence='0001 1101: D4→100. 0110 0100: D6→110. 1111 1111: D7→111.'),
   dict(id='check',y=(345,425),breaks=[381,399],md='풀이 3 · 검산',
        say=('검산해 볼게요. 각 행에서 선택한 자리보다 왼쪽은 모두 영이에요. 첫 행 영영영영 영영영일은 디 제로라서 영영영이고, 원문과 같아요.','검산해 볼게요. 각 행에서 선택한 자리보다 왼쪽은 모두 0이에요. 첫 행 0000 0001은 D0이라서 000이고, 원문과 같아요.'),
        review='검산 두 줄을 MD 풀이 3 과 대조.',evidence='선택한 자리 왼쪽이 모두 0 인지 다섯 행에서 확인. 첫 행 D0→000 이 원문 첫 행과 일치.'),
   dict(id='mistake',y=(425,505),breaks=[461,479],md='풀이 4 · 흔한 실수',
        say=('흔한 실수도 짚어 볼게요. 일이 여러 개일 때 모든 자리를 오어로 합치면 일반 인코더의 결과가 돼요. 예를 들어 영영일일 일영일영을 오어로 합치면 다른 코드가 나와요.','흔한 실수도 짚어 볼게요. 1이 여러 개일 때 모든 자리를 OR로 합치면 일반 인코더의 결과가 돼요. 예를 들어 0011 1010을 OR로 합치면 다른 코드가 나와요.'),
        review='흔한 실수 두 줄을 MD 풀이 4 와 대조.',evidence='0011 1010 의 켜진 자리 D5·D4·D3·D1 을 OR 하면 101|100|011|001=111 로 우선순위 결과 101 과 다르다.'),
   dict(id='answer',y=(505,573),breaks=[525,552],md='최종 답',
        say=('답을 정리하면, 영영일일 일영일영은 일영일, 영일영일 일일일영은 일일영, 영영영일 일일영일은 일영영, 영일일영 영일영영은 일일영, 일일일일 일일일일은 일일일이에요. 번호가 큰 입력이 우선이에요.','답을 정리하면, 0011 1010은 101, 0101 1110은 110, 0001 1101은 100, 0110 0100은 110, 1111 1111은 111이에요. 번호가 큰 입력이 우선이에요.'),
        review='답 상자 두 줄을 MD 최종 답과 대조.',evidence='표 2~6행과 같은 다섯 값.'),
  ]),
}

SPECS['q-demux-from-dec-graded']=dict(
  work_bbox=[300,62,751,573],
  assumptions='원문 디코더는 선택 입력 S1·S0, NOT 2개, 2입력 AND 4개(위에서부터 S1S0=00,01,10,11). 디멀티플렉서는 데이터 입력 D 를 네 AND 에 더한다.',
  intro=('기출 십이번이에요. 투 투 포 디코더의 게이트 회로를 활용해서 원 투 포 디멀티플렉서 회로를 만들고, 두 회로의 차이를 설명하는 문제예요. 원문 회로 그림은 채점 표시가 섞여 있어서 문제지에는 싣지 않았어요. 선택 입력 에스 원, 에스 제로와 낫 두 개, 이입력 앤드 네 개로 된 디코더라고 읽어요.',
         '기출 12번이에요. 2 to 4 디코더의 게이트 회로를 활용해서 1 to 4 디멀티플렉서 회로를 만들고, 두 회로의 차이를 설명하는 문제예요. 원문 회로 그림은 채점 표시가 섞여 있어서 문제지에는 싣지 않았어요. 선택 입력 S1, S0과 NOT 2개, 2입력 AND 4개로 된 디코더라고 읽어요.'),
  steps=[
   dict(id='sol',y=(62,135),breaks=[86,105],md='풀이 1 · 풀이',
        say=('디코더의 앤드 네 개는 위에서부터 에스 원 에스 제로가 영영, 영일, 일영, 일일인 경우를 골라내요. 각 앤드에 데이터 디를 하나 더 넣으면, 디를 통과시키는 건 선택된 앤드뿐이에요. 그래서 앤드를 삼입력으로 바꾸고, 디를 네 앤드 모두에 연결해요.',
             '디코더의 AND 네 개는 위에서부터 S1S0가 00, 01, 10, 11인 경우를 골라내요. 각 AND에 데이터 D를 하나 더 넣으면, D를 통과시키는 건 선택된 AND뿐이에요. 그래서 AND를 3입력으로 바꾸고, D를 네 AND 모두에 연결해요.'),
        review='답안 12쪽 풀이 1 두 줄을 MD 풀이 1 과 대조. PDF 는 "입력으로" 없이 "D를 더 넣으면" 으로 같은 뜻.',evidence='2입력 AND 의 선택 조합(S1′S0′, S1′S0, S1S0′, S1S0)에 D 를 세 번째 입력으로 더하면 선택된 출력만 D 를 따른다.'),
   dict(id='circuit',y=(135,335),breaks=[166],md='풀이 2 · 완성 회로',
        figure_text='D·S0·S1 입력, S1·S0 각각 NOT, 3입력 AND 네 개의 출력 Y0=S1′S0′D, Y1=S1′S0·D, Y2=S1·S0′D, Y3=S1·S0·D',
        say=('완성 회로를 그려 볼게요. 에스 원과 에스 제로는 각각 낫을 거쳐 반전 신호도 만들어요. 위에서부터 와이 제로는 에스 원 바, 에스 제로 바와 디를 받고, 와이 원은 에스 원 바, 에스 제로와 디를 받아요. 와이 투는 에스 원, 에스 제로 바와 디를, 와이 쓰리는 에스 원, 에스 제로와 디를 삼입력 앤드로 받아요.',
             '완성 회로를 그려 볼게요. S1과 S0은 각각 NOT을 거쳐 반전 신호도 만들어요. 위에서부터 Y0은 S1′, S0′과 D를 받고, Y1은 S1′, S0과 D를 받아요. Y2는 S1, S0′과 D를, Y3은 S1, S0과 D를 3입력 AND로 받아요.'),
        review='완성 회로 그림은 figures/solutions/q-demux-from-dec-graded-solution-01.png 와 픽셀이 같은 figure 도형. 같은 이름 SVG 의 라벨(Y0 = S1′S0′D … Y3 = S1·S0·D)과 연결을 MD 풀이 2 그림과 대조.',evidence='SVG 라벨과 배선: 각 AND 가 선택 조합 두 신호와 D 를 받는다. q-demux-from-dec-solution-01 과 픽셀이 같지만 이 문항 ID 의 PNG 로만 대응.'),
   dict(id='formula',y=(335,460),breaks=[370,391,407,424],md='풀이 3 · 논리식',
        say=('논리식으로 쓰면 와이 제로는 에스 원 바 에스 제로 바 디, 와이 원은 에스 원 바 에스 제로 디예요. 와이 투는 에스 원 에스 제로 바 디, 와이 쓰리는 에스 원 에스 제로 디예요.',
             '논리식으로 쓰면 Y0=S1′S0′D, Y1=S1′S0D예요. Y2=S1S0′D, Y3=S1S0D예요.'),
        review='KaTeX 논리식 네 개를 MD 풀이 3 과 대조. PDF 조판은 줄바꿈이 등호 앞에서 일어나 "D, Y1" 이 한 줄에 놓이지만 식 내용은 같다(복습팩 조판 결함, 원문 그대로 공개).',evidence='Y_k 는 선택 조합 곱에 D 를 곱한 것: 00→S1′S0′D, 01→S1′S0D, 10→S1S0′D, 11→S1S0D.'),
   dict(id='diff',y=(460,508),breaks=[490],md='풀이 4 · 두 회로의 차이',
        say=('두 회로의 차이를 정리해요. 디멀티플렉서에는 데이터 입력 디가 하나 더 있고, 앤드가 이입력에서 삼입력이 돼요.','두 회로의 차이를 정리해요. 디멀티플렉서에는 데이터 입력 D가 하나 더 있고, AND가 2입력에서 3입력이 돼요.'),
        review='PDF 에 보이는 첫 항목을 MD 풀이 4 첫 항목과 대조. MD 의 두 번째 항목(D=0 이면 모두 0)과 풀이 5 흔한 실수는 PDF 에서 넘쳐 보이지 않는다 — 복습팩 조판 결함으로 기록하고, 영상은 PDF 기준으로 보이는 내용만 공개한다.',evidence='데이터 입력 D 추가, AND 2입력→3입력.'),
   dict(id='answer',y=(508,573),breaks=[525,552],md='최종 답',
        say=('답을 정리하면, 첫째, 앤드를 삼입력으로 바꾸고 디를 연결해서, 와이 케이는 에스 원 에스 제로가 케이인 조건과 디를 곱한 거예요. 둘째, 디멀티플렉서에는 데이터 입력 디가 있고 선택된 출력이 디를 따르며, 디가 일이면 디코더와 같아요.',
             '답을 정리하면, (1) AND를 3입력으로 바꾸고 D를 연결해서, Yk는 S1S0가 k인 조건과 D를 곱한 거예요. (2) 디멀티플렉서에는 데이터 입력 D가 있고 선택된 출력이 D를 따르며, D=1이면 디코더와 같아요.'),
        review='답 상자 두 줄을 MD 최종 답과 대조.',evidence='Yk=(S1S0=k)·D. D=1 이면 디코더 출력과 같다.'),
  ])
if __name__=='__main__':author(sys.argv[1])
