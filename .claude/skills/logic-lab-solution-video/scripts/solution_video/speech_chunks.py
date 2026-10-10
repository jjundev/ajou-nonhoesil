"""Explicit speech/caption chunk pairs (caption_timing pcm-chunks-v1).

A chunked segment keeps its parent text/caption_text; each chunk is one spoken clip and exactly one caption cue.
"""
from pathlib import Path
import os,re,wave
from .contracts import InputError
from .util import digest,file_hash,read,write

MODE='pcm-chunks-v1'
_ID=r'[A-Za-z][A-Za-z0-9_-]*'

def _normalized(value):
    if not isinstance(value,str) or not value.strip():raise InputError('nonempty chunk text required')
    return ' '.join(value.split())

def validate_speech_chunks(segments:list[dict],*,required:bool)->None:
    """Every chunk is {id,text,caption_text}; joined chunk text/caption equal the parent's; each caption is one cue.
    required=True (pcm-chunks-v1) refuses any segment without chunks: never fall back to character weights."""
    from .subtitles import caption_text,chunk_caption
    identities=set()
    for segment in segments:
        sid=segment.get('id','unknown');chunks=segment.get('chunks')
        def fail(why):raise InputError('segment '+str(sid)+': '+why)
        if not isinstance(sid,str) or not re.fullmatch(_ID,sid):fail('invalid segment ID')
        if chunks is None:
            if required:fail('speech chunks required in '+MODE+' (no character-weight fallback)')
            if sid in identities:fail('duplicate speech identity')
            identities.add(sid);continue
        if not isinstance(chunks,list) or not chunks:fail('nonempty speech chunks required')
        ids=set()
        for chunk in chunks:
            if not isinstance(chunk,dict):fail('chunk must be an object')
            cid=chunk.get('id')
            if not isinstance(cid,str) or not re.fullmatch(_ID,cid):fail('invalid chunk ID')
            ident=sid+'__'+cid
            if cid in ids or ident in identities:fail('duplicate speech identity '+ident)
            ids.add(cid);identities.add(ident)
            try:
                _normalized(chunk.get('text'))
                if not isinstance(chunk.get('caption_text'),str):fail('chunk '+cid+' caption_text required')
                chunk_caption(caption_text(dict(chunk,id=ident)))
            except InputError as ex:
                if str(ex).startswith('segment '+str(sid)+':'):raise
                fail('chunk '+cid+': '+str(ex))
        for key in ['text','caption_text']:
            if key not in segment:fail(key+' required with speech chunks')
            if _normalized(segment.get(key))!=_normalized(' '.join(chunk[key] for chunk in chunks)):
                fail(key+' differs from joined speech chunks')

def speech_items(segments:list[dict])->list[dict]:
    """TTS requests: one per chunk (id segment__chunk) or, for a legacy segment, one per segment."""
    validate_speech_chunks(segments,required=False)
    items=[]
    for segment in segments:
        if 'chunks' not in segment:items.append(dict(id=segment['id'],text=segment['text']));continue
        for chunk in segment['chunks']:
            items.append(dict(id=segment['id']+'__'+chunk['id'],segment_id=segment['id'],chunk_id=chunk['id'],text=chunk['text']))
    return items

# --- measured PCM: chunk clips -> segment WAV, segment-relative sample boundaries ---------------------------------
RATE=24000
CHUNK_AUDIO='source/chunk-audio.json'
CHUNK_TRIMS='source/chunk-trims.json'

def _pcm(record,run):
    """Raw PCM16 bytes of a receipt's WAV after checking hash, format and length."""
    from .util import local,file_hash
    try:
        path=local(run,record['path'])
        if type(record['samples']) is not int or record['samples']<=0 or record['rate']!=RATE or file_hash(path)!=record['sha256']:
            raise InputError('PCM provenance mismatch: '+str(record.get('id')))
        with wave.open(str(path),'rb') as w:
            if (w.getnchannels(),w.getsampwidth(),w.getframerate(),w.getnframes(),w.getcomptype())!=(1,2,RATE,record['samples'],'NONE'):
                raise InputError('PCM format mismatch: '+str(record.get('id')))
            raw=w.readframes(w.getnframes())
        if len(raw)!=record['samples']*2:raise InputError('PCM truncated: '+str(record.get('id')))
        return raw
    except (OSError,KeyError,TypeError,wave.Error) as ex:raise InputError('invalid chunk PCM: '+str(record.get('id') if isinstance(record,dict) else record)) from ex

def _trim_rows(trims,items):
    """Human-reviewed integer sample cuts only; never inferred from audio energy."""
    if trims is None:return {}
    if not isinstance(trims,dict) or trims.get('schema_version')!=1 or not isinstance(trims.get('rows'),list):raise InputError('invalid chunk trims: schema_version 1 with rows required')
    allowed={(i['segment_id'],i['chunk_id']) for i in items if 'chunk_id' in i};rows={}
    for row in trims['rows']:
        if not isinstance(row,dict):raise InputError('invalid chunk trim row')
        pair=(row.get('segment_id'),row.get('chunk_id'))
        if pair not in allowed:raise InputError('chunk trim for unknown chunk: '+str(pair))
        if pair in rows:raise InputError('duplicate chunk trim: '+str(pair))
        if not isinstance(row.get('reason'),str) or not row['reason'].strip():raise InputError('chunk trim reason required: '+str(pair))
        rows[pair]=row
    return rows

def _segment_plans(segments,chunk_audio,run,trims):
    validate_speech_chunks(segments,required=True)
    items=speech_items(segments);records={a.get('id'):a for a in chunk_audio}
    if len(records)!=len(chunk_audio) or set(records)!={i['id'] for i in items}:raise InputError('chunk audio/manifest mismatch')
    rows=_trim_rows(trims,items);plans=[]
    for segment in segments:
        chunks=[];parts=[];offset=0
        for chunk in segment['chunks']:
            ident=segment['id']+'__'+chunk['id'];a=records[ident];raw=_pcm(a,run)
            lo,hi=0,a['samples'];trim=rows.get((segment['id'],chunk['id']))
            if trim:
                lo,hi=trim.get('start_sample'),trim.get('end_sample')
                if type(lo) is not int or type(hi) is not int or not 0<=lo<hi<=a['samples']:raise InputError('invalid chunk trim range '+ident)
                if trim.get('raw_sha256')!=a['sha256']:raise InputError('stale chunk trim (raw WAV changed) '+ident)
            chunks.append(dict(id=chunk['id'],source_id=ident,raw_sha256=a['sha256'],trim_start_sample=lo,trim_end_sample=hi,start_sample=offset,end_sample=offset+hi-lo))
            parts.append(raw[lo*2:hi*2]);offset+=hi-lo  # no inserted silence between chunks
        key=digest(dict(policy=MODE,segment_id=segment['id'],chunks=chunks))
        plans.append(dict(id=segment['id'],raw=b''.join(parts),samples=offset,rate=RATE,key=key,chunks=chunks))
    return plans

def join_segment_audio(segments:list[dict],chunk_audio:list[dict],run:Path,trims:dict|None=None)->list[dict]:
    """Concatenate raw chunk PCM (no re-encoding, no silence) into one segment WAV; raw chunk WAVs stay untouched."""
    run=Path(run);dest=run/'assets/voice';dest.mkdir(parents=True,exist_ok=True);out=[]
    for plan in _segment_plans(segments,chunk_audio,run,trims):
        path=dest/(plan['id']+'-joined-'+plan['key'][:16]+'.wav');pending=path.with_suffix('.pending.wav')
        with wave.open(str(pending),'wb') as w:w.setparams((1,2,RATE,0,'NONE','not compressed'));w.writeframes(plan['raw'])
        os.replace(pending,path)
        rec={k:v for k,v in plan.items() if k!='raw'}
        rec.update(path=path.relative_to(run).as_posix(),sha256=file_hash(path),output_sha256=file_hash(path),policy=MODE)
        write(path.with_suffix('.json'),rec);out.append(rec)
    return out

def _current_key_check(records,items,config):
    """Receipts must come from the current spoken-text-only request for the current chunk text."""
    from .review_adapter import _modules
    tts,_=_modules();by_item={i['id']:i for i in items}
    for rec in records:
        item=by_item.get(rec.get('id'))
        if item is None:raise InputError('unknown chunk receipt: '+str(rec.get('id')))
        if rec.get('policy')!=tts.POLICY or rec.get('key')!=tts.speech_key(item['text'],config):raise InputError('stale speech chunk receipt: '+rec['id'])

def check_trims_before_tts(segments,run,config)->dict|None:
    """Before any paid request: a trims file needs chunk speech and must still refer to the saved raw clips of the current text."""
    run=Path(run);path=run/CHUNK_TRIMS
    if not path.is_file():return None
    trims=read(path)
    if not any('chunks' in s for s in segments):raise InputError('chunk trims require chunk speech')
    items=speech_items(segments);rows=_trim_rows(trims,items)
    if not rows:return trims
    try:previous={a['id']:a for a in read(run/CHUNK_AUDIO)['voices']}
    except (OSError,KeyError,ValueError,TypeError) as ex:raise InputError('chunk trims need saved chunk audio; remove '+CHUNK_TRIMS+' first') from ex
    by_item={i['id']:i for i in items}
    for sid,cid in rows:
        ident=sid+'__'+cid
        if ident not in previous:raise InputError('trimmed chunk has no saved raw clip: '+ident)
        try:_current_key_check([previous[ident]],[by_item[ident]],config)
        except InputError as ex:raise InputError('trimmed speech input changed; remove or reauthor the trim for '+ident) from ex
        if rows[(sid,cid)].get('raw_sha256')!=previous[ident].get('sha256'):raise InputError('stale chunk trim (raw WAV changed) '+ident)
        lo,hi=rows[(sid,cid)].get('start_sample'),rows[(sid,cid)].get('end_sample')
        if type(lo) is not int or type(hi) is not int or not 0<=lo<hi<=previous[ident].get('samples',0):raise InputError('invalid chunk trim range '+ident)
    return trims

def validate_chunk_audio(segments:list[dict],voices:list[dict],run:Path,config:dict)->None:
    """Chunk mode: receipts current, raw clips intact, joined segment WAVs exactly equal to raw PCM + trims. Legacy: no-op."""
    if not any('chunks' in s for s in segments):return
    run=Path(run)
    try:data=read(run/CHUNK_AUDIO)
    except (OSError,ValueError) as ex:raise InputError('chunk audio receipts missing: '+CHUNK_AUDIO) from ex
    from .review_adapter import _modules
    if not isinstance(data,dict) or data.get('policy')!=_modules()[0].POLICY or not isinstance(data.get('voices'),list):raise InputError('invalid chunk audio receipts')
    records=data['voices'];_current_key_check(records,speech_items(segments),config)
    trims=read(run/CHUNK_TRIMS) if (run/CHUNK_TRIMS).is_file() else None
    plans=_segment_plans(segments,records,run,trims);actual={v.get('id'):v for v in voices}
    if len(actual)!=len(voices) or set(actual)!={s['id'] for s in segments}:raise InputError('joined segment mismatch')
    for expected in plans:
        record=actual[expected['id']]
        if any(record.get(k)!=expected[k] for k in ['samples','rate','key','chunks']) or _pcm(record,run)!=expected['raw']:
            raise InputError('joined PCM/chunk boundaries changed: '+expected['id'])

# --- timeline cues (absolute samples) ------------------------------------------------------------------------------
def caption_cues_for(segment,voice,start_sample)->list[dict]:
    """Absolute cue samples = segment start + measured relative chunk boundaries. Hold/padding after the voice gets no cue."""
    boundaries=voice.get('chunks')
    if not isinstance(boundaries,list) or [c.get('id') for c in boundaries]!=[c['id'] for c in segment['chunks']]:
        raise InputError('audio chunk boundaries missing/mismatched: '+segment['id'])
    cues=[]
    for chunk,boundary in zip(segment['chunks'],boundaries):
        lo,hi=boundary.get('start_sample'),boundary.get('end_sample')
        if type(lo) is not int or type(hi) is not int:raise InputError('invalid sample boundaries: '+segment['id']+'__'+chunk['id'])
        cues.append(dict(segment_id=segment['id'],chunk_id=chunk['id'],caption_text=chunk['caption_text'],start_sample=start_sample+lo,end_sample=start_sample+hi))
    return cues

def validate_caption_cues(timeline:dict)->list[dict]:
    """Cues tile each segment's measured voice exactly, in manifest chunk order, never into the hold."""
    from .subtitles import caption_text,chunk_caption
    cues=timeline.get('caption_cues')
    if timeline.get('caption_timing')!=MODE or not isinstance(cues,list) or not cues:raise InputError('measured caption cues required')
    index=0
    for seg in timeline['segments']:
        chunks=seg.get('chunks');cursor=seg['start_sample']
        if not isinstance(chunks,list) or not chunks:raise InputError('missing timeline speech chunks: '+str(seg.get('id')))
        for chunk in chunks:
            if index>=len(cues):raise InputError('missing caption cue: '+seg['id']+'__'+chunk['id'])
            cue=cues[index];index+=1;lo,hi=cue.get('start_sample'),cue.get('end_sample')
            chunk_caption(caption_text(dict(cue,id=seg['id']+'__'+chunk['id'])))
            if (cue.get('segment_id')!=seg['id'] or cue.get('chunk_id')!=chunk['id'] or cue.get('caption_text')!=chunk['caption_text']
                or type(lo) is not int or type(hi) is not int or lo!=cursor or hi-lo<24
                or hi>seg['start_sample']+seg['voice_samples']):raise InputError('invalid measured caption cue: '+seg['id']+'__'+chunk['id'])
            cursor=hi
        if cursor!=seg['start_sample']+seg['voice_samples'] or cursor>seg['end_sample']:raise InputError('caption/voice coverage mismatch: '+seg['id'])
    if index!=len(cues):raise InputError('extra caption cue')
    return cues

# --- verification -------------------------------------------------------------------------------------------------
REVIEW_FLAGS=('transcript_match','no_instruction_speech','natural_join','sync_passed')

def chunk_review_passed(review:dict,manifest:dict)->bool:
    """Chunk mode audio-review: a live listener checked every chunk in order. Structure checks never stand in for it."""
    if manifest.get('caption_timing')!=MODE:return True
    if review.get('mode')!='live-listened':return False
    expected=[(s['id'],c['id']) for s in manifest['segments'] for c in s.get('chunks',[])]
    rows=review.get('chunk_checks')
    if not isinstance(rows,list) or any(not isinstance(r,dict) for r in rows):return False
    if [(r.get('segment_id'),r.get('chunk_id')) for r in rows]!=expected:return False
    return all(all(r.get(k) is True for k in REVIEW_FLAGS) and isinstance(r.get('notes'),str) and r['notes'].strip() for r in rows)

def verify_chunk_sync(run:Path)->dict:
    """Structural sync evidence (verification/chunk-sync.json): receipts, raw/joined PCM, timeline cues and SRT all
    rebuild from the measured samples. It is not evidence that anyone listened."""
    import tempfile
    from .subtitles import write_srt
    from .teaching import build_teaching_timeline
    from .annotations import load_teaching
    from .writing import load_writing
    from .util import local
    run=Path(run).resolve();issues=[];hashes={}
    try:
        m=read(run/'source/manifest.json');t=read(run/'source/timeline.json')
        if m.get('caption_timing')!=MODE or t.get('caption_timing')!=MODE:raise InputError('chunk timing mode required')
        cfg=read(run/'source/config.json');voices=read(run/'source/audio.json')['voices']
        validate_chunk_audio(m['segments'],voices,run,cfg);validate_caption_cues(t)
        l=read(run/'layers/layers.json')
        writing=load_writing(run,cfg) if (run/'source/writing.json').is_file() else None
        expected=build_teaching_timeline(m,l,voices,cfg,writing,load_teaching(run,m,l))
        if t['caption_cues']!=expected['caption_cues']:raise InputError('timeline cues differ from measured chunk PCM')
        with tempfile.TemporaryDirectory(prefix='logic-lab-chunk-sync-') as td:
            if write_srt(expected,Path(td)/'expected.srt').read_bytes()!=(run/'renders/captions.srt').read_bytes():raise InputError('SRT differs from measured chunk boundaries')
        paths=[run/'source/manifest.json',run/'source/audio.json',run/CHUNK_AUDIO,run/'source/timeline.json',run/'renders/captions.srt']
        paths+=[local(run,a['path']) for a in voices]+[local(run,a['path']) for a in read(run/CHUNK_AUDIO)['voices']]
        if (run/CHUNK_TRIMS).is_file():paths.append(run/CHUNK_TRIMS)
        hashes={p.relative_to(run).as_posix():file_hash(p) for p in paths}
    except (InputError,OSError,KeyError,TypeError,ValueError) as ex:issues.append(str(ex)[:500])
    result=dict(status='passed' if not issues else 'unverified',caption_timing=MODE,live_listening='not-evidence',
                input_hash=digest(hashes),evidence_hashes=hashes,issues=issues)
    write(run/'verification/chunk-sync.json',result);return result
