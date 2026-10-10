"""Measure speech energy and narration gaps; never generate or modify audio."""
from pathlib import Path
import array,math,sys,wave
from .contracts import InputError
from .util import digest,file_hash,local,read


def speech_intervals(pcm_path:Path)->list[tuple[int,int]]:
    try:
        with wave.open(str(pcm_path),'rb') as wav:
            if (wav.getnchannels(),wav.getsampwidth(),wav.getframerate(),wav.getcomptype())!=(1,2,24000,'NONE'):raise InputError('expected 24kHz mono PCM16')
            samples=array.array('h',wav.readframes(wav.getnframes()))
            if sys.byteorder!='little':samples.byteswap()
    except (OSError,wave.Error) as ex:raise InputError('invalid PCM') from ex
    intervals=[]
    for start in range(0,len(samples),480):
        block=samples[start:start+480]
        if math.sqrt(sum(x*x for x in block)/len(block))/32768>=.01:
            end=min(start+480,len(samples))
            if intervals and start-intervals[-1][1]<=2400:intervals[-1]=(intervals[-1][0],end)
            else:intervals.append((start,end))
    return intervals


def analyze_narration_pacing(timeline:dict,audio:list[dict],run:Path)->dict:
    run=Path(run); voices={a['id']:a for a in audio};speech={};hashes={}
    if len(voices)!=len(audio):raise InputError('duplicate audio record')
    for a in audio:
        p=local(run,a['path'])
        try:
            if file_hash(p)!=a['sha256']:raise InputError('PCM hash changed')
            with wave.open(str(p),'rb') as w:
                if (w.getnchannels(),w.getsampwidth(),w.getframerate(),w.getnframes())!=(1,2,24000,a['samples']) or a['rate']!=24000:raise InputError('PCM provenance mismatch')
        except (OSError,wave.Error,KeyError) as ex:raise InputError('invalid measured PCM') from ex
        hashes[a['path']]=a['sha256'];speech[a['id']]=speech_intervals(p)
    input_hash=digest(dict(timeline=timeline,audio=audio));reviews=[]
    review_path=run/'verification/pacing-review.json'
    if review_path.is_file():
        review=read(review_path)
        if review.get('input_hash')==input_hash:reviews=review.get('gaps',[])
    rows=[];unreviewed=[]
    for seg in timeline['segments']:
        if seg['kind']!='write':continue
        if seg['id'] not in voices:raise InputError('missing writing voice')
        start,end=seg['start_sample']//800,seg['end_sample']//800
        spans=[s for s in timeline.get('writing_spans',[]) if start<=s['start_frame']<end]
        if not spans:continue
        first,last=min(s['start_frame'] for s in spans),max(s['end_frame'] for s in spans)
        active=set(f for s in spans for f in range(s['start_frame'],s['end_frame']))
        voiced=set()
        for lo,hi in speech[seg['id']]:
            for f in range(start+math.floor(lo/800),start+math.ceil(hi/800)):
                # A frame's sample midpoint classifies energy without rounding a 60fr gap to 61.
                if lo<=((f-start)*800+400)<hi:voiced.add(f)
        gaps=[];cursor=first
        while cursor<last:
            if cursor in voiced:cursor+=1;continue
            lo=cursor
            while cursor<last and cursor not in voiced:cursor+=1
            gaps.append(dict(start_frame=lo,end_frame=cursor))
        long=[g for g in gaps if g['end_frame']-g['start_frame']>60]
        for gap in long:
            if not any(r.get('segment_id')==seg['id'] and r.get('start_frame')==gap['start_frame'] and r.get('end_frame')==gap['end_frame'] and isinstance(r.get('reason'),str) and r['reason'].strip() for r in reviews):unreviewed.append(dict(segment_id=seg['id'],**gap))
        ratio=len(active&voiced)/len(active) if active else 0
        rows.append(dict(segment_id=seg['id'],voiced_ratio=ratio,longest_gap_frames=max((g['end_frame']-g['start_frame'] for g in gaps),default=0),gaps=gaps,density_guidance=None if .7<=ratio<=.85 else 'author speech for approximately 70–85% of active writing',writing_frames=len(active)))
    return dict(input_hash=input_hash,segments=rows,status='review-required' if unreviewed else 'passed',unreviewed_gaps=unreviewed,evidence_hashes=hashes)
