#!/usr/bin/env python3
"""Stage CLI. Preparing/extracting/checking never invokes a paid service."""
from pathlib import Path
import argparse,copy,json,os,shutil,sys,uuid,wave
from datetime import datetime
from solution_video.util import S,read,write,digest,file_hash,local
from solution_video.contracts import InputError,ReviewError
from solution_video.sources import discover,freeze_sources
from solution_video.pdf_pages import export_page,extract_layers,compare_completed
from solution_video.manifest import validate_manifest,content_fingerprint
from solution_video.review_adapter import default_config,generate_voice,validate_config
from solution_video.teaching import build_teaching_timeline
from solution_video.annotations import load_teaching
from solution_video.lesson import load_lesson
from solution_video.writing import default_writing,load_writing,validate_writing
from solution_video.composition import assemble
from solution_video.media import render_master
from solution_video.subtitles import write_srt,burn_subtitles,caption_notation_warnings
from solution_video.verify import verify_run
from solution_video.state import STAGES,recover_run,finish_stage,stage_fingerprint
from solution_video.publication import publish_batch

def prepare_batch(repo,selector,problem_ids=None,review=False,writing_mode="pencil"):
    writing=default_writing(writing_mode)
    repo=Path(repo).resolve(); failures=[];pairs=discover(repo,selector,problem_ids,failures=failures)
    root=repo/'문제풀이영상'/selector; production=root/(selector+'_제작자료'); ident=datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8]; batch=production/'실행'/ident;batch.mkdir(parents=True)
    frozen=freeze_sources(pairs,batch); items=[]
    data={'schema_version':1,'selector':selector,'review':review,'items':items};write(batch/'batch.json',data)
    for p in frozen:
        key='problem-'+digest(p['problem_id'])[:12]; run=batch/'videos'/key; run.mkdir(parents=True)
        pair=copy.deepcopy(p)
        for source in [pair,*pair.get('sources',[])]:
            for ref in [source['problem'],source['answer']]:
                target=run/ref['snapshot'];target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(batch/ref['snapshot'],target)
            if source['md_snapshot']:
                target=run/source['md_snapshot'];target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(batch/source['md_snapshot'],target)
        write(run/'source/inputs.json',read(batch/'source/inputs.json')); write(run/'source/pair.json',pair);write(run/'source/config.json',default_config())
        write(run/'source/writing.json',writing)
        write(run/'run.json',{'batch':str(batch),'review':review,'problem_id':p['problem_id']})
        item={'id':p['problem_id'],'run':'videos/'+key,'filename':p['problem_id']+' — 풀이.mp4','status':'author-required'}
        items.append(item);write(batch/'batch.json',data)
        try:
            export_page(local(run,pair['answer']['snapshot']),pair['answer']['page_index'],run/'layers')
            finish_stage(run,'inputs',[run/'source/inputs.json',run/'source/pair.json'])
        except Exception as ex:
            item.update(status='failed',reason=str(ex)[:500]);write(run/'source/prepare-error.json',{'reason':item['reason']})
        write(batch/'batch.json',data)
    grouped={}
    for failure in failures:
        pid=failure['problem_id'] or 'date-'+failure['date'];grouped.setdefault(pid,dict(failure,correspondences=[]))['correspondences'].append(failure)
    for failure in grouped.values():
        pid=failure['problem_id'] or 'date-'+failure['date'];key='failed-'+digest(failure)[:12];run=batch/'videos'/key
        write(run/'source/prepare-error.json',failure)
        items.append({'id':pid,'run':'videos/'+key,'filename':pid+' — 풀이.mp4','status':'failed','reason':failure['reason']})
    write(batch/'batch.json',data);return batch

def resume_batch(batch):
    batch=Path(batch);data=read(batch/'batch.json');items=[]
    for item in data['items']:
        run=local(batch,item['run']);next_stage=recover_run(run)
        failed=(run/'source/prepare-error.json').is_file() and not (run/'layers/candidates.json').is_file()
        items.append(dict(item,next=next_stage,status='failed' if failed else 'passed' if next_stage is None else 'pending'))
    return {'items':items}

def _load(run): return tuple(read(run/p) for p in ['source/manifest.json','layers/layers.json','source/coverage.json','source/circuit-review.json'])
def _gate(run,layers):
    g=read(run/'verification/gate.json')
    if g.get('input_hash')!=digest(layers) or any(g[k]!=0 for k in ['pixel_diff','non_target_diff','hidden_leaks']): raise ReviewError('PDF reveal gate missing/stale/failed')
    if any(file_hash(local(run,p))!=sha for p,sha in g.get('evidence_hashes',{}).items()) or not g.get('evidence_hashes'): raise ReviewError('PDF gate evidence changed')
    for key in ['original_svg','animated_svg','reference_png']:
        if file_hash(Path(layers[key]))!=g['source_hashes'][key]: raise ReviewError('PDF layer changed since gate')

def run_stage(action,run,args,transport=None):
    path=Path(run)/'source/manifest.json'
    warnings=caption_notation_warnings(read(path).get('segments',[])) if path.is_file() else []
    if action=='tts' and warnings:
        print(json.dumps({'stage':'tts','warnings':warnings},ensure_ascii=False),file=sys.stderr,flush=True)
    result=_run_stage(action,run,args,transport)
    if action in ('check','tts','captions'):result['warnings']=warnings
    return result

def _run_stage(action,run,args,transport=None):
    run=Path(run).resolve()
    if action=='extract' and not (run/'layers/candidates.json').is_file() and (run/'source/pair.json').is_file():
        pair=read(run/'source/pair.json');export_page(local(run,pair['answer']['snapshot']),pair['answer']['page_index'],run/'layers')
        finish_stage(run,'inputs',[run/'source/inputs.json',run/'source/pair.json'])
        (run/'source/prepare-error.json').unlink(missing_ok=True)
    needed=['source/map.json'] if action=='extract' else ['source/manifest.json','layers/layers.json','source/coverage.json','source/circuit-review.json']
    if any(not (run/p).is_file() for p in needed): return {'status':'author-required','run':str(run),'missing':[p for p in needed if not (run/p).is_file()],'paid_requests':0}
    stage={'extract':'layers','check':'script','tts':'voice','retime':'timing','assemble':'composition','render':'render','captions':'captions','verify':'verify'}[action]
    if (run/'state.json').is_file():
        next_stage=recover_run(run)
        if next_stage and STAGES.index(next_stage)<STAGES.index(stage): raise InputError('complete or refresh prerequisite stage: '+next_stage)
    if action=='extract':
        layers=extract_layers(read(run/'layers/candidates.json'),read(run/'source/map.json'));write(run/'layers/layers.json',layers)
        g=compare_completed(layers,run/'verification/gate-frames');g['input_hash']=digest(layers)
        g['evidence']=[Path(p).relative_to(run).as_posix() for p in g['evidence']];g['evidence_hashes']={p:file_hash(local(run,p)) for p in g['evidence']};g['source_hashes']={k:file_hash(layers[k]) for k in ['original_svg','animated_svg','reference_png']}
        write(run/'verification/gate.json',g)
        if any(g[k] for k in ['pixel_diff','non_target_diff','hidden_leaks']): raise ReviewError('original SVG gate failed')
        finish_stage(run,'layers',[run/'layers/layers.json',run/'layers/animated.svg',run/'verification/gate.json']); return {'status':'passed','paid_requests':0,'gate':g}
    if action=='retime' and not (run/'state.json').is_file():raise InputError('complete prerequisite stage: voice')
    m,l,c,r=_load(run)
    if (run/'source/pair.json').exists() and m['problem_id']!=read(run/'source/pair.json')['problem_id']:raise ReviewError('manifest/source identity mismatch')
    validate_manifest(m,l,c,r);_gate(run,l)
    teaching=load_teaching(run,m,l)
    load_lesson(run,m,l,teaching)
    if action in ('check','tts','retime'):
        cfg=read(run/'source/config.json')
        proposed=read(args.writing_config) if action=='retime' and args.writing_config else None
        current=proposed or load_writing(run,cfg)
        validate_writing(current)
        if current['mode']=='pencil':
            from solution_video.writing_units import compile_writing_units
            compile_writing_units(l)
    if action=='check': finish_stage(run,stage,[run/'source/manifest.json',run/'source/coverage.json',run/'source/circuit-review.json']);return {'status':'passed','paid_requests':0,'input_hash':content_fingerprint(m,l,c)}
    if action=='tts':
        cfg=read(args.config) if args.config else read(run/'source/config.json');validate_config(cfg);write(run/'source/config.json',cfg)
        writing=load_writing(run,cfg) if (run/'source/writing.json').is_file() else None
        meta=read(run/'run.json'); batch=Path(meta['batch']); bd=read(batch/'batch.json')
        if meta['review']:
            scope=[i for i in bd['items'] if not ((local(batch,i['run'])/'source/prepare-error.json').is_file() and not (local(batch,i['run'])/'layers/candidates.json').is_file())]
            if any(not (local(batch,i['run'])/'source/manifest.json').is_file() for i in scope):return {'status':'author-required','paid_requests':0,'reason':'finish remaining batch scripts before review'}
            review_hash=digest({i['id']:content_fingerprint(*_load(local(batch,i['run']))[:3]) for i in scope})
            approval=batch/'script-approval.json'
            if args.approve_review: write(approval,{'input_hash':review_hash,'approved':True})
            if not approval.exists() or read(approval).get('input_hash')!=review_hash: return {'status':'awaiting-review','paid_requests':0,'input_hash':review_hash}
        ledger=batch/'usage.json'; count=lambda:len(read(ledger)['requests']) if ledger.is_file() else 0
        before=count()
        try: audio=generate_voice(m['segments'],run,cfg,ledger,transport,env_file=args.env_file)
        except Exception as ex:
            ex.paid_requests=0 if transport else count()-before
            raise
        paid=0 if transport else count()-before
        finish_stage(run,'voice',[run/'source/audio.json']);t=build_teaching_timeline(m,l,audio,cfg,writing,teaching);write(run/'source/timeline.json',t);finish_stage(run,'timing',[run/'source/timeline.json'])
        return {'status':'passed','segments':len(audio),'paid_requests':paid}
    if action=='retime':
        cfg=read(run/'source/config.json');validate_config(cfg)
        proposed=read(args.writing_config) if args.writing_config else None
        if proposed is not None:validate_writing(proposed)
        writing=proposed or (load_writing(run,cfg) if (run/'source/writing.json').is_file() else None)
        audio=read(run/'source/audio.json')['voices']
        try:
            for a in audio:
                path=local(run,a['path'])
                if file_hash(path)!=a['sha256']:raise InputError('PCM hash changed')
                with wave.open(str(path),'rb') as wav:
                    if (wav.getnchannels(),wav.getsampwidth(),wav.getframerate(),wav.getnframes())!=(1,2,24000,a['samples']):raise InputError('PCM provenance mismatch')
        except (OSError,wave.Error,KeyError) as ex:raise InputError('invalid saved PCM') from ex
        t=build_teaching_timeline(m,l,audio,cfg,writing,teaching)
        if proposed is not None:write(run/'source/writing.json',proposed)
        write(run/'source/timeline.json',t);finish_stage(run,'timing',[run/'source/timeline.json'])
        return {'status':'passed','paid_requests':0,'total_frames':t['total_frames']}
    if action=='assemble':
        if not (run/'source/audio.json').exists(): return {'status':'author-required','paid_requests':0,'missing':['source/audio.json']}
        parts=assemble(read(run/'source/pair.json'),l,m,read(run/'source/timeline.json'),run,Path(args.runtime));finish_stage(run,stage,[run/'source/parts.json',*[p for p in (run/'composition').rglob('*') if p.is_file()]]);return {'status':'passed','parts':parts,'paid_requests':0}
    if action=='render':
        p=render_master(read(run/'source/parts.json'),read(run/'source/timeline.json'),read(run/'source/audio.json')['voices'],run,Path(args.hyperframes_entry));finish_stage(run,stage,[p]);return {'status':'passed','master':str(p),'paid_requests':0}
    if action=='captions':
        srt=write_srt(read(run/'source/timeline.json'),run/'renders/captions.srt');final=burn_subtitles(run/'renders/master.mp4',srt,run/'renders/final.mp4',S/'assets/fonts/Pretendard-Bold.ttf');finish_stage(run,stage,[srt,final]);return {'status':'passed','final':str(final),'paid_requests':0}
    report=verify_run(run,Path(args.hyperframes_entry))
    if report['complete']: finish_stage(run,stage,[run/'verification/report.json'])
    return dict(report,status='passed' if report['complete'] else 'failed',paid_requests=0)

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);subs=parser.add_subparsers(dest='action',required=True)
    p=subs.add_parser('prepare');p.add_argument('selector');p.add_argument('--repo',type=Path,default=Path.cwd());p.add_argument('--problems');p.add_argument('--review',action='store_true');p.add_argument('--writing-mode',choices=['pencil','typing'],default='pencil')
    for name in ['extract','check','tts','retime','assemble','render','captions','verify']:
        p=subs.add_parser(name);p.add_argument('--run',required=True,type=Path)
        if name=='tts':
            p.add_argument('--config',type=Path);p.add_argument('--env-file',type=Path);p.add_argument('--approve-review',action='store_true')
        if name=='retime':p.add_argument('--writing-config',type=Path)
        if name=='assemble': p.add_argument('--runtime',required=True)
        if name in ['render','verify']: p.add_argument('--hyperframes-entry',required=True)
    for name in ['resume-set','publish-set']:
        p=subs.add_parser(name);p.add_argument('--batch',required=True,type=Path)
    args=parser.parse_args(argv)
    try:
        if args.action=='prepare': result={'status':'author-required','batch':str(prepare_batch(args.repo,args.selector,args.problems.split(',') if args.problems else None,args.review,args.writing_mode)),'paid_requests':0}
        elif args.action=='resume-set': result=dict(resume_batch(args.batch),paid_requests=0)
        elif args.action=='publish-set':
            result=publish_batch(args.batch);result.update(status='passed' if result['complete'] else 'failed',paid_requests=0)
        else: result=run_stage(args.action,args.run,args)
    except Exception as ex: result={'status':'failed','reason':str(ex)[:600],'paid_requests':getattr(ex,'paid_requests',0)}
    print(json.dumps(result,ensure_ascii=False,indent=2));return 1 if result.get('status')=='failed' else 0
if __name__=='__main__': sys.exit(main())
