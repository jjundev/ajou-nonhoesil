"""원본 PDF 도형 하나에 가로 공개 예산 하나를 잡고 clip 조각에 폭 비례로 나눈다.

조각 수가 늘어도 도형 전체 draw 시간은 같다. 풀이 그림(kind=='figure')은 reveal.FIGURE_DRAW_FRAMES 로
그림 단위 wipe 를 따로 받으므로 여기서 다루지 않는다.
"""
import math
from .contracts import InputError

MIN_SHAPE_FRAMES=18
MAX_SHAPE_FRAMES=90


def shape_budget(width:float,height:float,interval:int)->int:
    return min(MAX_SHAPE_FRAMES,max(MIN_SHAPE_FRAMES,math.ceil(width/height*interval)))


def allocate_shape_frames(units:list[dict],layers:dict,step_id:str,height:float,interval:int)->dict[tuple[str,int],int]:
    if type(height) not in (int,float) or not math.isfinite(height) or height<=0 or type(interval) is not int or interval<=0:
        raise InputError('invalid shape timing height/interval')
    shapes={s['id']:s for s in layers.get('shapes',[])};groups={};result={}
    for u in units:
        if u['step_id']!=step_id:continue
        for i,p in enumerate(u['pieces']):
            if p['kind']!='shape':continue
            if p['id'] in shapes and shapes[p['id']].get('kind')=='figure':continue
            groups.setdefault(p['id'],[]).append(((u['id'],i),p['clip_bbox'][2]-p['clip_bbox'][0]))
    for sid,parts in groups.items():
        if sid not in shapes:raise InputError('missing shape '+sid)
        width=shapes[sid]['bbox'][2]-shapes[sid]['bbox'][0]
        if not math.isfinite(width) or width<0 or any(not math.isfinite(w) or w<0 for _,w in parts):raise InputError('invalid shape width '+sid)
        budget=shape_budget(width,height,interval)
        if len(parts)>budget:raise InputError(f'shape {sid}: {len(parts)} pieces exceed {budget} frames; author fewer clips')
        if width==0:
            if len(parts)!=1:raise InputError('vertical shape must have one piece '+sid)
            result[parts[0][0]]=MIN_SHAPE_FRAMES;continue
        if any(w<=0 for _,w in parts):raise InputError('empty shape clip '+sid)
        # 1프레임 미만 몫은 1로 묶어 두고 남은 예산을 나머지에 다시 비례 배분한다.
        pending=list(range(len(parts)));quotas=[0.]*len(parts);remaining=budget
        while pending:
            scale=remaining/sum(parts[i][1] for i in pending)
            small=[i for i in pending if parts[i][1]*scale<1]
            if not small:
                for i in pending:quotas[i]=parts[i][1]*scale
                break
            for i in small:quotas[i]=1.;remaining-=1;pending.remove(i)
        frames=[math.floor(q) for q in quotas]
        # 최대 나머지 순, 동률은 저작 순서.
        for i in sorted(range(len(parts)),key=lambda i:(-(quotas[i]-frames[i]),i))[:budget-sum(frames)]:frames[i]+=1
        for (key,_),n in zip(parts,frames):result[key]=n
    return result
