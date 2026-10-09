"""Validate authored spatial reveal bands without changing PDF paint order."""
import copy
import math
import re
from typing import Literal, TypedDict
from .contracts import InputError

TOL = .01

class WritingPiece(TypedDict):
    kind: Literal['glyph', 'shape']
    id: str
    clip_bbox: list[float]

class WritingUnit(TypedDict):
    id: str
    line_id: str
    chunk_id: str
    column_id: str
    band: list[float]
    glyph_ids: list[str]
    shape_ids: list[str]
    camera_break_before: bool
    step_id: str
    bbox: list[float]
    pieces: list[WritingPiece]


def compile_writing_units(layers: dict) -> list[WritingUnit]:
    def require(ok, message):
        if not ok: raise InputError(message)
    objects={kind:{o['id']:o for o in layers.get(kind+'s',[])} for kind in ('glyph','shape')}
    result=[]; seen=set(); closed_lines=set(); previous=None
    line_columns={}; closed_chunks=set()
    for step in layers['map']['steps']:
        authored=step.get('writing_units')
        require(isinstance(authored,list) and bool(authored),'writing_units required; author line/column/band boundaries')
        clips={kind:{oid:[] for oid in step[kind+'_ids']} for kind in objects}
        for raw in authored:
            require(isinstance(raw,dict),'invalid writing unit')
            for field in ('id','line_id','chunk_id','column_id'):
                require(isinstance(raw.get(field),str) and re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*',raw[field]),'writing unit IDs must be safe ASCII')
            require(raw['id'] not in seen,'duplicate writing unit ID'); seen.add(raw['id'])
            band=raw.get('band')
            require(isinstance(band,list) and len(band)==2 and all(type(x) in (float,int) and math.isfinite(x) for x in band) and band[1]>band[0],'invalid writing band')
            require(type(raw.get('camera_break_before')) is bool,'camera_break_before must be boolean')
            line,chunk,column=raw['line_id'],raw['chunk_id'],raw['column_id']
            require(line_columns.get(line,column)==column,'column change requires new line'); line_columns[line]=column
            if previous:
                if line==previous['line_id']:
                    require(band[0]>=previous['band'][1]-TOL,'writing bands overlap or move backwards')
                    if chunk!=previous['chunk_id']:
                        closed_chunks.add((line,previous['chunk_id']))
                        require((line,chunk) not in closed_chunks,'cannot reopen completed chunk')
                        require(raw['camera_break_before'],'chunk change requires camera_break_before')
                else:
                    closed_lines.add(previous['line_id'])
                    require(line not in closed_lines,'cannot return to a completed line')
            pieces=[]
            for kind in objects:
                ids=raw.get(kind+'_ids')
                require(isinstance(ids,list) and all(isinstance(i,str) for i in ids) and len(set(ids))==len(ids),'invalid/duplicate writing target IDs')
                for oid in ids:
                    require(oid in clips[kind] and oid in objects[kind],'unknown or external writing target ID')
                    b=objects[kind][oid]['bbox']
                    require(len(b)==4 and all(type(x) in (int,float) and math.isfinite(x) for x in b) and b[2]>=b[0] and b[3]>=b[1],'invalid target bbox')
                    lo,hi=max(b[0],band[0]),min(b[2],band[1])
                    zero=b[2]==b[0] or kind=='glyph' and objects[kind][oid]['text'].isspace()
                    require(hi>lo or zero and band[0]-TOL<=b[0]<=band[1]+TOL,'target does not intersect writing band')
                    clip=[lo,b[1],hi,b[3]] if not zero else list(b)
                    clips[kind][oid].append(clip)
                    pieces.append(dict(kind=kind,id=oid,clip_bbox=clip))
            require(bool(pieces),'empty writing unit')
            pieces.sort(key=lambda p:(p['clip_bbox'][0],p['clip_bbox'][1],objects[p['kind']][p['id']].get('paint_order',0)))
            bbox=[min(p['clip_bbox'][0] for p in pieces),min(p['clip_bbox'][1] for p in pieces),max(p['clip_bbox'][2] for p in pieces),max(p['clip_bbox'][3] for p in pieces)]
            normalized=copy.deepcopy(raw); normalized.update(step_id=step['id'],bbox=bbox,pieces=pieces)
            result.append(normalized); previous=normalized
        for kind,targets in clips.items():
            for oid,parts in targets.items():
                require(bool(parts),'missing writing target '+oid)
                b=objects[kind][oid]['bbox']
                if b[2]==b[0] or kind=='glyph' and objects[kind][oid]['text'].isspace():require(len(parts)==1,'zero-area target must belong to one unit');continue
                parts.sort(key=lambda p:p[0]); edge=b[0]
                for part in parts:
                    require(abs(part[0]-edge)<=TOL,'incomplete or overlapping clip coverage '+oid)
                    edge=part[2]
                require(abs(edge-b[2])<=TOL,'incomplete clip coverage '+oid)
    return result
