"""Provenance and integrity for separately authored schematic assets."""
from pathlib import Path
from xml.etree import ElementTree as ET
import hashlib
import math
import re
import struct
from .workbook_content import _strict_json, _within
from .bank_index import build_authoring_index
from .manifest import data_dir

KEYS={'id','question_id','role','svg','png','svg_sha256','png_sha256','w_mm','h_mm',
      'source_asset_ids','source_refs','derivation','answer_exposure','review_status','review_notes'}

def check_redrawn_figures(folder, manifest, *, require_review=False):
    errors=[];folder=data_dir(folder)
    try:
        obj=_strict_json(_within(folder,manifest['figure_manifest']))
        if not isinstance(obj,dict) or set(obj)!={'schema_version','figures'} or type(obj['schema_version']) is not int or obj['schema_version']!=1 or not isinstance(obj['figures'],list):
            raise ValueError('Invalid figure manifest')
        questions={p['id']:p for p in manifest['problems']}
        seen=set();paths=set();assets={};safe={}
        if 'bank_import' in manifest:
            binding=manifest['bank_import']; bank=_strict_json(_within(folder,binding['snapshot_path']))
            assets={a['id']:a for a in bank['assets']}
            safe={q['question_id']:set(q['safe_problem_asset_ids']) for q in build_authoring_index(bank,binding['sha256'])['questions']}
        for f in obj['figures']:
            if not isinstance(f,dict) or set(f)!=KEYS: raise ValueError('Invalid figure fields')
            ident=f['id']
            if not isinstance(ident,str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*',ident) or ident in seen:
                raise ValueError('Invalid/duplicate figure id')
            seen.add(ident);p=questions.get(f['question_id'])
            if p is None: raise ValueError(ident+': unknown question')
            if f['role'] not in {'problem','solution'} or f['answer_exposure'] not in {'none','present'}:
                raise ValueError(ident+': invalid figure role/exposure')
            if f['role']=='problem' and f['answer_exposure']!='none': raise ValueError(ident+': exposed question diagram')
            if f['review_status'] not in {'not_run','pass','held'}: raise ValueError(ident+': invalid review status')
            if require_review and f['review_status']!='pass': errors.append(ident+': diagram not visually reviewed')
            if not isinstance(f['review_notes'],str) or not f['review_notes'].strip(): raise ValueError(ident+': missing review notes')
            if not isinstance(f['derivation'],str) or not f['derivation'].strip(): raise ValueError(ident+': missing derivation')
            for key in ('w_mm','h_mm'):
                if type(f[key]) not in (int,float) or not math.isfinite(f[key]) or f[key]<=0: raise ValueError(ident+': invalid physical dimensions')
            blobs={}
            for suffix in ('svg','png'):
                value=f[suffix]
                if not isinstance(value,str) or not value.endswith('.'+suffix) or value in paths:
                    raise ValueError(ident+': invalid/duplicate figure path')
                expected='figures/questions/' if f['role']=='problem' else 'figures/solutions/'
                if not value.startswith(expected): raise ValueError(ident+': role/path mismatch')
                paths.add(value);blob=_within(folder,value).read_bytes();blobs[suffix]=blob
                if hashlib.sha256(blob).hexdigest()!=f[suffix+'_sha256']: raise ValueError(ident+': '+suffix+' hash changed')
            svg=ET.fromstring(blobs['svg']); box=svg.get('viewBox','').split()
            if len(box)!=4 or svg.tag!='{http://www.w3.org/2000/svg}svg': raise ValueError(ident+': invalid SVG viewBox')
            dims=[float(x) for x in box]
            if any(not math.isfinite(x) for x in dims) or dims[2]<=0 or dims[3]<=0: raise ValueError(ident+': invalid SVG bounds')
            if not any(n.tag=='{http://www.w3.org/2000/svg}title' and (n.text or '').strip() for n in svg.iter()): raise ValueError(ident+': missing SVG title')
            for n in svg.iter():
                tag=n.tag.rsplit('}',1)[-1]
                if tag in {'script','image','foreignObject'} or any(k.lower().startswith('on') for k in n.attrib):
                    raise ValueError(ident+': active or raster SVG')
                if any(k.rsplit('}',1)[-1]=='href' and not v.startswith('#') for k,v in n.attrib.items()): raise ValueError(ident+': external SVG resource')
                if re.search(r'url\s*\(|@import', ' '.join(n.attrib.values())+' '+(n.text or ''),re.I): raise ValueError(ident+': CSS SVG resource')
            blob=blobs['png']
            if len(blob)<24 or not blob.startswith(b'\x89PNG\r\n\x1a\n'): raise ValueError(ident+': invalid PNG')
            width,height=struct.unpack('!II',blob[16:24])
            ratio=f['w_mm']/f['h_mm']
            if width<=0 or height<=0 or abs(dims[2]/dims[3]/ratio-1)>0.02 or abs(width/height/ratio-1)>0.02:
                raise ValueError(ident+': diagram aspect ratio mismatch')
            refs=f['source_refs']
            if not isinstance(refs,list) or any(not isinstance(r,dict) or r.get('source_id') not in {s['id'] for s in manifest['sources']} for r in refs):
                raise ValueError(ident+': invalid source references')
            if p.get('bank_question_id') and (not refs or any(not any(r.get('source_id')==pr.get('source_id') and r.get('pdf_page')==pr.get('pdf_page') for pr in p['sources']) for r in refs)):
                raise ValueError(ident+': diagram sources do not belong to question')
            ids=f['source_asset_ids']
            if not isinstance(ids,list) or any(not isinstance(a,str) for a in ids) or len(set(ids))!=len(ids): raise ValueError(ident+': invalid source asset ids')
            for asset_id in ids:
                if asset_id not in assets: raise ValueError(ident+': unknown original asset')
                if f['role']=='problem' and asset_id not in safe.get(p.get('bank_question_id'),set()): raise ValueError(ident+': exposed/foreign source asset')
            if p.get('bank_question_id') and f['role']=='problem' and not ids:
                raise ValueError(ident+': question diagram needs safe original asset')
    except (ValueError,OSError,KeyError,TypeError,ET.ParseError,struct.error) as exc:
        errors.append('Redrawn diagrams: '+str(exc))
    return errors
