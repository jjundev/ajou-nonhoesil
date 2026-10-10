"""Explicit speech/caption chunk pairs (caption_timing pcm-chunks-v1).

A chunked segment keeps its parent text/caption_text; each chunk is one spoken clip and exactly one caption cue.
"""
import re
from .contracts import InputError

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
