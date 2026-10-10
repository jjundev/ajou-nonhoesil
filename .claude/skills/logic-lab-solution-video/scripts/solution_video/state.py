from pathlib import Path
from .util import S,digest,file_hash,read,write,local
from .review_adapter import adapter_hash
from .contracts import InputError
from .writing import timing_settings
STAGES=['inputs','layers','script','voice','timing','composition','render','captions','verify','publish']
FACTORS={
 'inputs':['source/inputs.json','source/pair.json','source/snapshots/**/*'],  # 동결한 그림은 snapshots/figures/<sha>/ 아래라 재귀 글롭이어야 한다
 'layers':['source/map.json','layers/candidates.json','layers/original.svg'],
 'script':['source/manifest.json','source/coverage.json','source/circuit-review.json','source/lesson.json','verification/gate.json'],
 'voice':['source/config.json','source/chunk-trims.json'], 'timing':['source/audio.json','source/chunk-audio.json','assets/voice/*.wav'],  # 사람이 정한 청크 절단은 tts 가 연결본에 적용한다
 'composition':['source/timeline.json'], 'render':['source/parts.json','composition/**/*'],
 'captions':['renders/master.mp4'], 'verify':['renders/final.mp4','renders/captions.srt','verification/audio-review.json','verification/visual-review.json','verification/pacing-review.json'], 'publish':['verification/report.json']}
MODULES={'inputs':['sources'],'layers':['pdf_pages','writing_units'],'script':['manifest','lesson','subtitles','speech_chunks'],'voice':['review_adapter','speech_chunks'],'timing':['reveal','writing','speech_chunks','shape_timing'],'composition':['composition','writing_camera'],'render':['media'],'captions':['subtitles'],'verify':['verify','narration_pacing'],'publish':['publication']}
def stage_fingerprint(run,stage):
    run=Path(run); n=STAGES.index(stage); files={}
    for s in STAGES[:n+1]:
        for pattern in FACTORS[s]:
            for p in run.glob(pattern):
                if p.is_file(): files[p.relative_to(run).as_posix()]=file_hash(p)
        for module in MODULES[s]:
            p=S/'scripts/solution_video'/(module+'.py')
            if p.exists(): files['tool:'+module]=file_hash(p)
    for module in ['util','contracts','page_layout']:
        p=S/'scripts/solution_video'/(module+'.py'); files['tool:'+module]=file_hash(p)
    if n>=1: files['tool:browser_check']=file_hash(S/'tests/browser_check.mjs')
    if n>=8:files['tool:writing_flow_check']=file_hash(S/'tests/writing_flow_check.mjs')
    if n>=8:files['tool:teaching_check']=file_hash(S/'tests/teaching_check.mjs')
    if n>=3: files['tool:adapter']=adapter_hash()
    writing_path=run/'source/writing.json'
    writing=read(writing_path) if writing_path.is_file() else None
    pencil=writing is not None and writing.get('mode')=='pencil'
    if n>=4:
        from .annotations import load_teaching
        from .teaching import teaching_timing_settings
        present={name:(run/('source/'+name+'.json')).is_file() for name in ['focus','annotations']}
        files['teaching:presence']=digest(present)
        if any(present.values()):
            plan=load_teaching(run,read(run/'source/manifest.json'),read(run/'layers/layers.json'))
            files['teaching:timing']=digest(teaching_timing_settings(plan))
        files['tool:teaching']=file_hash(S/'scripts/solution_video/teaching.py')
    if n>=5:
        for name in ['focus','annotations']:
            p=run/('source/'+name+'.json')
            if p.is_file():files['teaching:'+name]=file_hash(p)
        for name in ['annotations','focus']:
            files['tool:'+name]=file_hash(S/'scripts/solution_video'/(name+'.py'))
        if (run/'source/annotations.json').is_file():
            font=S/'assets/fonts/Pretendard-Bold.ttf'
            files['teaching:font']=file_hash(font) if font.is_file() else 'missing'
            pencil=True
    if n>=4 and writing is not None:
        files['writing:timing']=digest(timing_settings(writing))
    if n>=5:
        if writing is not None:files['writing:composition']=digest(writing)
        if pencil:
            for name in ['pencil-yellow-v1.png','pencil-yellow-v1.json']:
                path=S/'assets/pencil'/name;files['asset:pencil/'+name]=file_hash(path) if path.is_file() else 'missing'
        for p in (S/'assets').glob('*'):
            if p.suffix in ('.js','.css') and (p.name!='writing.js' or pencil): files['asset:'+p.name]=file_hash(p)
    return digest(files)
def recover_run(run):
    run=Path(run); path=run/'state.json'; state=read(path) if path.is_file() else {'stages':{}}
    for s in STAGES:
        record=state['stages'].get(s)
        if not record or record['fingerprint']!=stage_fingerprint(run,s): return s
        if any(not local(run,p).is_file() or file_hash(local(run,p))!=sha for p,sha in record['outputs'].items()): return s
        if s=='publish':
            try:
                receipt=read(run/'verification/publication.json')
                for path,sha in receipt['published'].items():
                    if not Path(path).is_file() or file_hash(path)!=sha:return s
            except (OSError,KeyError,ValueError):return s
    return None
def finish_stage(run,stage,outputs):
    run=Path(run).resolve(); state=read(run/'state.json') if (run/'state.json').exists() else {'schema_version':1,'stages':{}}
    hashes={}
    for p in outputs:
        p=Path(p).resolve()
        if not p.is_relative_to(run) or not p.is_file(): raise InputError('stage output missing or outside run')
        hashes[p.relative_to(run).as_posix()]=file_hash(p)
    state['stages'][stage]={'fingerprint':stage_fingerprint(run,stage),'outputs':hashes}; write(run/'state.json',state)
