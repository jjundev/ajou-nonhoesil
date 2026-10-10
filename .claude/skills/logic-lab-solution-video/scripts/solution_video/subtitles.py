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
     '수치 서술 문맥의 한글 수사입니다. 원본과 대조하여 숫자인지 확인하세요.'),
    ('warning','logic_bar_word',r'(?<![A-Za-z0-9_])[A-Z][A-Za-z0-9_]*\s*(바|낫)(?:(?![가-힣])|(?=[이가은는을를와과의도만로에]))',
     '논리 부정은 자막에 ′ 로 씁니다 (예: S1′)')]
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
    warnings=[]
    for segment in segments:
        if not isinstance(segment,dict):continue
        # pcm-chunks-v1: 경고는 cue 하나인 청크 자막 기준(span 도 청크 안), 어느 청크인지 chunk_id 로 알린다.
        chunked=isinstance(segment.get('chunks'),list)
        for item in segment['chunks'] if chunked else [segment]:
            if not isinstance(item,dict) or not isinstance(item.get('caption_text'),str):continue
            for issue in inspect_caption_notation(item['caption_text'],segment.get('id','unknown')):
                if issue['severity']!='warning':continue
                if chunked:issue['chunk_id']=item.get('id','unknown')
                warnings.append(issue)
    return warnings

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

# Caption math for the logic lab is intentionally conservative: this is not a Korean parser.
# One atom is a signal name or product term with its complements (Bo, S1′S0′D, A'B, A\u0305B),
# a number, a hyphen-joined name (1-to-4) or a nibble-grouped binary word (0011 1010).
_TERM=r"[0-9]*[A-Za-zΔλμΩ][A-Za-z0-9_₀-₉\u0305]*(?:[′'\u0305]+[A-Za-z0-9_₀-₉\u0305]*)*"
_NUMBER=r"[0-9]+(?:[.,][0-9]+)*[′']*"
_CAPTION_ATOM=re.compile(r"(?<![0-9A-Za-z_])[01]{4}(?: [01]{4})+(?![0-9A-Za-z_])"
                         r"|(?:"+_TERM+"|"+_NUMBER+")(?:-(?:"+_TERM+"|"+_NUMBER+"))*")
_LAYOUT_OPERATORS=_OPERATORS+'⊕⊙·'
_GROUPS={'(':')','[':']','{':'}'}

def _protected_ranges(text:str)->list[tuple[int,int]]:
    """Protect outer bracket groups, atoms, signed atoms and slash-joined pairs (end exclusive)."""
    _caption_units(text,False)  # Keep the existing delimiter/punctuation contract.
    ranges=[];stack=[]
    for i,ch in enumerate(text):
        if stack and ch==stack[-1][0]:
            closer,start=stack.pop()
            if not stack and closer in _GROUPS.values():ranges.append((start,i+1))
        elif stack and stack[-1][0] in _QUOTES:
            continue
        elif ch in _PAIRS:
            stack.append((_PAIRS[ch],i))
    for match in _CAPTION_ATOM.finditer(text):
        start,end=match.span()
        if not any(a<=start and end<=b for a,b in ranges):ranges.append((start,end))
    signed=[]
    for start,end in ranges:
        at=start
        while at>0 and text[at-1].isspace():at-=1
        if at>0 and text[at-1] in '+−-':
            sign=at-1;prev=text[:sign].rstrip()
            if not prev or prev[-1] in _LAYOUT_OPERATORS+'([{,' or re.search(r'[가-힣]$',prev):start=sign
        signed.append((start,end))
    result=[]
    for start,end in sorted(signed):
        if result and re.fullmatch(r'\s*/\s*',text[result[-1][1]:start]):result[-1]=(result[-1][0],end)
        else:result.append((start,end))
    return result

def _math_spans(text:str,protected:list[tuple[int,int]])->list[tuple[int,int,bool]]:
    """Maximal runs of math joined by spaces or operators; the flag marks a formula (has an operator)."""
    spans=[]
    for start,end in protected:
        if not _CAPTION_ATOM.search(text[start:end]):continue
        gap=text[spans[-1][1]:start] if spans else None
        if gap is not None and re.fullmatch(r'(?:\s+|\s*['+re.escape(_LAYOUT_OPERATORS)+r']\s*)',gap):
            spans[-1]=(spans[-1][0],end)
        else:spans.append((start,end))
    return [(a,b,any(c in _LAYOUT_OPERATORS for c in text[a:b])) for a,b in spans]

def _wrap_candidates(text:str,max_chars:int)->list[tuple[int,int,int,str,str]]:
    """(priority, balance, split_index, left, right): 0 prose/formula boundary, 1 prose space, 2 operator."""
    protected=_protected_ranges(text);spans=_math_spans(text,protected)
    points={m.start() for m in re.finditer(r'\s+',text)}
    points.update(i for i,ch in enumerate(text) if ch in _LAYOUT_OPERATORS)
    choices=[]
    for at in sorted(points):
        if any(a<at<b for a,b in protected):continue
        left,right=text[:at].rstrip(),text[at:].lstrip()
        if (not left or not right or right[0] in '.,)]}”’′\''
            or left[-1] in _LAYOUT_OPERATORS+'([{'
            or len(left)>max_chars or len(right)>max_chars):continue
        right_start=len(text)-len(right)
        operator=right[0] in _LAYOUT_OPERATORS
        # Inside a math run only an operator may start the next line, and it keeps its right-hand term.
        if any(a<at<b for a,b,_ in spans) and not operator:continue
        before=any(a==right_start and formula for a,b,formula in spans) and bool(re.search(r'[가-힣]$',left))
        after=any(b==len(left) and formula for a,b,formula in spans) and bool(re.match(r'[가-힣]',right))
        priority=0 if before or after else 2 if operator else 1
        choices.append((priority,abs(len(left)-len(right)),at,left,right))
    return choices

def wrap_caption(text:str,max_chars:int=34,max_lines:int=2)->str:
    """Fit one cue at semantic boundaries without splitting terms, groups or formulas that fit a line."""
    if max_chars<1 or max_lines not in (1,2):raise InputError('caption limits require positive width and one or two lines')
    text=' '.join(text.split())
    if any(b-a>max_chars for a,b in _protected_ranges(text)):
        raise InputError('caption protected expression exceeds '+str(max_chars)+' characters: '+text)
    if len(text)<=max_chars:return text
    choices=_wrap_candidates(text,max_chars)
    if max_lines==1 or not choices:raise InputError('caption clause exceeds '+str(max_lines)+' lines of '+str(max_chars)+' characters; author shorter captions: '+text)
    _,_,_,left,right=min(choices)
    return left+'\n'+right

def split_caption(text:str,max_chars:int=34)->list[str]:
    return [wrap_caption(unit,max_chars) for unit in caption_units(text)]

def chunk_caption(text:str)->str:
    """One authored speech chunk = exactly one cue (same sentence/comma rules as split_caption); a comma-ending clause keeps its comma."""
    units=_caption_units(text,not text.rstrip().endswith(','))
    if len(units)!=1:raise InputError('speech chunk must contain exactly one caption cue (split it at the sentence/comma boundary): '+text)
    return wrap_caption(units[0])

def write_srt(timeline,dest):
    lines=[]; num=0
    from .speech_chunks import MODE,validate_caption_cues
    if timeline.get('caption_timing') not in (None,MODE):raise InputError('unsupported caption timing mode')
    chunk_mode=timeline.get('caption_timing')==MODE
    # pcm-chunks-v1: cue 시간은 실측 청크 샘플 경계 그대로(글자 수 비례 배분 없음). legacy 는 아래 기존 방식.
    for num,cue in enumerate(validate_caption_cues(timeline) if chunk_mode else [],1):
        lines.append(f'{num}\n{_stamp(cue["start_sample"],timeline["rate"])} --> {_stamp(cue["end_sample"],timeline["rate"])}\n{chunk_caption(caption_text(cue))}\n')
    for seg in [] if chunk_mode else timeline['segments']:
        text=caption_text(seg); chunks=split_caption(text)
        lengths=[len(unit) for unit in _caption_units(text,False)]
        duration=seg.get('voice_samples',seg['end_sample']-seg['start_sample']); weights=sum(lengths); start=seg['start_sample']; offset=0
        for c,length in zip(chunks,lengths):
            end=start+round(duration*(offset+length)/weights); begin=start+round(duration*offset/weights); offset+=length
            if end-begin<24: raise InputError('caption too short for millisecond resolution')
            num+=1; lines.append(f'{num}\n{_stamp(begin,timeline["rate"])} --> {_stamp(end,timeline["rate"])}\n{c}\n')
    dest=Path(dest); dest.parent.mkdir(parents=True,exist_ok=True); dest.write_text('\n'.join(lines),encoding='utf-8'); return dest

def caption_srt_matches(timeline:dict,srt)->bool:
    """True when srt holds exactly what write_srt makes now: cue numbers, wrapped text, line breaks and times."""
    srt=Path(srt)
    if not srt.is_file():return False
    with tempfile.TemporaryDirectory(prefix='logic-lab-expected-captions-') as td:
        expected=write_srt(timeline,Path(td)/'expected.srt').read_text(encoding='utf-8')
    return srt.read_text(encoding='utf-8')==expected

def burn_subtitles(master,srt,dest,font):
    master,srt,dest,font=map(lambda p:Path(p).resolve(),[master,srt,dest,font])
    if dest==master: raise InputError('cannot overwrite master with captions')
    dest.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='ec2-captions-') as td:
        work=Path(td); (work/'fonts').mkdir(); shutil.copyfile(font,work/'fonts/Pretendard-Bold.ttf'); shutil.copyfile(srt,work/'subs.srt')
        style='WrapStyle=2,FontName=Pretendard,FontSize=14,Bold=1,Alignment=2,MarginV=14,Outline=0,Shadow=4,BorderStyle=4,PrimaryColour=&HFFFFFF&,OutlineColour=&H4D0E0B0B,BackColour=&H4D0E0B0B'
        pending=dest.with_name(dest.stem+'.pending.mp4')
        checked([ffmpeg(),'-y','-v','error','-i',master,'-vf',"subtitles=subs.srt:fontsdir=fonts:force_style='"+style+"'",'-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-c:a','copy',pending],cwd=work,timeout=1800)
        os.replace(pending,dest)
    return dest
