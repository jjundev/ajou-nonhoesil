from pathlib import Path
import math,os,re,shutil,tempfile
from .util import checked
from .media import ffmpeg
from .contracts import InputError

def _stamp(samples,rate):
    ms=round(samples*1000/rate); sec,ms=divmod(ms,1000); minutes,sec=divmod(sec,60); hr,minutes=divmod(minutes,60)
    return f'{hr:02d}:{minutes:02d}:{sec:02d},{ms:03d}'
def caption_text(segment:dict)->str:
    value=segment.get('caption_text') if 'caption_text' in segment else segment.get('text')
    if not isinstance(value,str) or not value.strip():raise InputError('nonempty caption_text required')
    if 'caption_text' in segment:
        validate_caption_notation(value,segment.get('id','unknown'))
    return ' '.join(value.split())

_KOREAN_NUMBER=r'(?:영|일|이|삼|사|오|육|칠|팔|구|십|백|천|만)+'
_MATH_ATOM=r'(?:[A-Za-zΔλμΩ][A-Za-z0-9_₀-₉]*|[0-9]+)'
_NOTATION_RULES=[
    ('error','spoken_operator',r'(?<![가-힣])(?:더하기|빼기|곱하기|나누기|마이너스)(?![가-힣])',
     '명시적 연산을 기호로 표기하세요.'),
    ('error','spoken_fraction',r'(?<![가-힣])'+_KOREAN_NUMBER+r'\s*분의\s*'+_KOREAN_NUMBER,
     '분수를 숫자와 /로 표기하세요.'),
    ('error','spoken_decimal',r'(?<![가-힣])'+_KOREAN_NUMBER+r'\s+점\s+'+_KOREAN_NUMBER,
     '소수를 숫자로 표기하세요.'),
    ('warning','number_before_symbol',r'(?<![가-힣])'+_KOREAN_NUMBER+r'\s+(?='+_MATH_ATOM+r')',
     '숫자 또는 지시어일 수 있습니다. 원본 수식과 문맥을 대조하세요.'),
    ('warning','spoken_divisor',r'(?<![가-힣])'+_KOREAN_NUMBER+r'(?:으로|로)\s+나눈',
     '나누는 수를 뜻하는지 문맥으로 확인하세요.'),
    ('warning','numeric_predicate',r'(?:값|계수|답|전류|전압)(?:은|는)\s+(?P<number>'+_KOREAN_NUMBER+r')(?=입니다|이다)',
     '수치 서술 문맥의 한글 수사입니다. 원본과 대조하여 숫자인지 확인하세요.')]
_NOTATION_RULES=[(severity,code,re.compile(pattern),reason)
                 for severity,code,pattern,reason in _NOTATION_RULES]

def inspect_caption_notation(text:str,segment_id:str)->list[dict]:
    """Return diagnostics without guessing or changing Korean meaning."""
    issues={}
    for severity,code,pattern,reason in _NOTATION_RULES:
        for match in pattern.finditer(text):
            span=match.span('number') if 'number' in pattern.groupindex else match.span()
            issue=dict(severity=severity,code=code,segment_id=segment_id,span=list(span),
                       matched_text=text[slice(*span)],reason=reason)
            if span not in issues or severity=='error':issues[span]=issue
    return [issues[span] for span in sorted(issues)]

def caption_notation_warnings(segments:list[dict])->list[dict]:
    return [issue for segment in segments if isinstance(segment,dict)
            and isinstance(segment.get('caption_text'),str)
            for issue in inspect_caption_notation(segment['caption_text'],segment.get('id','unknown'))
            if issue['severity']=='warning']

def validate_caption_notation(text:str,segment_id:str)->None:
    errors=[i for i in inspect_caption_notation(text,segment_id) if i['severity']=='error']
    if errors:
        details='; '.join(i['matched_text'].strip()+': '+i['reason'] for i in errors)
        raise InputError('segment '+segment_id+': caption requires numeric/symbol notation: '
                         +details+'; author caption_text: '+text)

_PAIRS={'(':')','[':']','{':'}','“':'”','‘':'’','"':'"'}
_QUOTES={'”','’','"'}
_OPERATORS='+−=∥×÷'

def _caption_units(text:str,terminal_period:bool)->list[str]:
    text=' '.join(text.split())
    if not text:raise InputError('nonempty caption required')
    if '$' in text or '\\(' in text or '\\)' in text:raise InputError('LaTeX caption unsupported: '+text)
    if text.rstrip('”’"').endswith(('?','!','…')):raise InputError('caption must end with period: '+text)
    stack=[];units=[];start=0
    for i,ch in enumerate(text):
        boundary=False
        if stack and ch==stack[-1]:
            stack.pop()
            if ch in _QUOTES and not stack and text[start:i].rstrip('”’"').endswith(('?','!','…')) and (i+1==len(text) or text[i+1].isspace()):
                raise InputError('caption sentence must end with period: '+text)
            # A complete quoted sentence owns its closing quote.
            boundary=ch in _QUOTES and not stack and text[start:i].rstrip('”’"').endswith('.') and (i+1==len(text) or text[i+1].isspace())
        elif stack and stack[-1] in _QUOTES:
            continue
        elif ch in _PAIRS:
            stack.append(_PAIRS[ch])
        elif ch in ')]}”’':
            raise InputError('unbalanced caption delimiters: '+text)
        elif not stack:
            if ch in '?!…' and (i+1==len(text) or text[i+1].isspace()):raise InputError('caption sentence must end with period: '+text)
            if ch==',':
                boundary=not (i>0 and i+1<len(text) and text[i-1].isdigit() and text[i+1].isdigit())
            elif ch=='.':
                boundary=i+1==len(text) or text[i+1].isspace()
        if boundary:
            unit=text[start:i+1].strip()
            if unit:units.append(unit)
            start=i+1
    if stack:raise InputError('unbalanced caption delimiters: '+text)
    tail=text[start:].strip()
    if tail:units.append(tail)
    if terminal_period and not units[-1].rstrip('”’"').endswith('.'):
        if units[-1].endswith(','):raise InputError('caption cannot end with comma: '+text)
        units[-1]+='.'
    return units

def caption_units(text:str)->list[str]:
    """Split prose at sentence/clause boundaries without changing stored text."""
    return _caption_units(text,True)

def wrap_caption(text:str,max_chars:int=34,max_lines:int=2)->str:
    """Fit one semantic unit, preserving identifiers and punctuation."""
    if max_chars<1 or max_lines not in (1,2):raise InputError('caption limits require positive width and one or two lines')
    text=' '.join(text.split())
    tokens=re.findall(r'[^\s+−=∥×÷(),]+|[+−=∥×÷(),]',text)
    if any(len(t)>max_chars for t in tokens):raise InputError('caption token exceeds '+str(max_chars)+' characters: '+text)
    if len(text)<=max_chars:return text
    def candidates(points):
        valid=[]
        for at in points:
            left,right=text[:at].rstrip(),text[at:].lstrip()
            if not left or not right or right[0] in '.,)]}”’' or len(left)>max_chars or len(right)>max_chars:continue
            valid.append((abs(len(left)-len(right)),at,left,right))
        return valid
    choices=candidates([m.start() for m in re.finditer(r'\s+',text)])
    if not choices:choices=candidates([i+1 for i,c in enumerate(text) if c in _OPERATORS])
    if max_lines==1 or not choices:raise InputError('caption clause exceeds '+str(max_lines)+' lines of '+str(max_chars)+' characters; author shorter captions: '+text)
    _,_,left,right=min(choices)
    return left+'\n'+right

def split_caption(text:str,max_chars:int=34)->list[str]:
    return [wrap_caption(unit,max_chars) for unit in caption_units(text)]

def write_srt(timeline,dest):
    lines=[]; num=0
    for seg in timeline['segments']:
        text=caption_text(seg); chunks=split_caption(text)
        lengths=[len(unit) for unit in _caption_units(text,False)]
        duration=seg.get('voice_samples',seg['end_sample']-seg['start_sample']); weights=sum(lengths); start=seg['start_sample']; offset=0
        for c,length in zip(chunks,lengths):
            end=start+round(duration*(offset+length)/weights); begin=start+round(duration*offset/weights); offset+=length
            if end-begin<24: raise InputError('caption too short for millisecond resolution')
            num+=1; lines.append(f'{num}\n{_stamp(begin,timeline["rate"])} --> {_stamp(end,timeline["rate"])}\n{c}\n')
    dest=Path(dest); dest.parent.mkdir(parents=True,exist_ok=True); dest.write_text('\n'.join(lines),encoding='utf-8'); return dest

def burn_subtitles(master,srt,dest,font):
    master,srt,dest,font=map(lambda p:Path(p).resolve(),[master,srt,dest,font])
    if dest==master: raise InputError('cannot overwrite master with captions')
    dest.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='ec2-captions-') as td:
        work=Path(td); (work/'fonts').mkdir(); shutil.copyfile(font,work/'fonts/Pretendard-Bold.ttf'); shutil.copyfile(srt,work/'subs.srt')
        style='FontName=Pretendard,FontSize=14,Bold=1,Alignment=2,MarginV=14,Outline=0,Shadow=4,BorderStyle=4,PrimaryColour=&HFFFFFF&,OutlineColour=&H4D0E0B0B,BackColour=&H4D0E0B0B'
        pending=dest.with_name(dest.stem+'.pending.mp4')
        checked([ffmpeg(),'-y','-v','error','-i',master,'-vf',"subtitles=subs.srt:fontsdir=fonts:force_style='"+style+"'",'-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-c:a','copy',pending],cwd=work,timeout=1800)
        os.replace(pending,dest)
    return dest
