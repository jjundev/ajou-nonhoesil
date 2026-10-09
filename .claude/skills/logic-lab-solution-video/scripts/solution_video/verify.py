from pathlib import Path
import json,wave
from .util import digest,file_hash,read,write,command,local,browser
from .media import probe,ffmpeg,source_checks
from .subtitles import caption_notation_warnings
from .manifest import validate_manifest

def verification_fingerprint(run):
    run=Path(run)
    roots=['source','layers','composition','renders']
    files={p.relative_to(run).as_posix():file_hash(p) for root in roots for p in (run/root).rglob('*') if p.is_file() and p.suffix not in ('.log','.pending') and p.name!='config.env'}
    files['tool']=digest({p.name:file_hash(p) for p in (Path(__file__).parent).glob('*.py')})
    return digest(files)

def gate_valid(run,layers,g):
    try:
        return (g['input_hash']==digest(layers) and all(g[k]==0 for k in ['pixel_diff','non_target_diff','hidden_leaks'])
          and bool(g.get('evidence_hashes')) and set(g['evidence'])==set(g['evidence_hashes'])
          and all(local(run,p).is_file() and file_hash(local(run,p))==sha for p,sha in g['evidence_hashes'].items())
          and all(file_hash(Path(layers[k]))==g['source_hashes'][k] for k in ['original_svg','animated_svg','reference_png']))
    except (OSError,KeyError,ValueError): return False

def verify_run(run,hyperframes_entry):
    run=Path(run).resolve(); checks={}; evidence=[]; final=run/'renders/final.mp4'; h=verification_fingerprint(run)
    def check(name,fn):
        try:
            ok=fn(); checks[name]={'status':'passed' if ok else 'unverified'}
        except Exception as ex: checks[name]={'status':'unverified','reason':str(ex)[:500]}
    def content():
        validate_manifest(read(run/'source/manifest.json'),read(run/'layers/layers.json'),read(run/'source/coverage.json'),read(run/'source/circuit-review.json')); return True
    check('content',content)
    def gate():
        return gate_valid(run,read(run/'layers/layers.json'),read(run/'verification/gate.json'))
    check('original_svg',gate)
    def writing_gate():
        t=read(run/'source/timeline.json')
        if t.get('writing',{}).get('mode')!='pencil':return True
        from .writing import load_pencil_asset,load_writing,timing_settings
        load_pencil_asset(run/'composition')
        from .teaching import build_teaching_timeline
        from .annotations import load_teaching
        cfg=read(run/'source/config.json');writing=load_writing(run,cfg)
        if timing_settings(t['writing'])!=timing_settings(writing):return False
        m,l=read(run/'source/manifest.json'),read(run/'layers/layers.json')
        expected=build_teaching_timeline(m,l,read(run/'source/audio.json')['voices'],cfg,writing,load_teaching(run,m,l))
        if dict(t,cameras=[],writing=timing_settings(t['writing']))!=dict(expected,cameras=[],writing=timing_settings(writing)):return False
        expected_path=run/'verification/writing-timeline.json';write(expected_path,expected)
        result=browser(['--mode','timeline','--entry',str((run/'composition/index.html').resolve()),'--layers',str((run/'layers/layers.json').resolve()),'--timeline',str(expected_path.resolve()),'--dest',str((run/'verification/writing-frames').resolve())])
        w=result['writing'];w['input_hash']=h
        w['evidence_hashes']={str(Path(p).relative_to(run)):file_hash(p) for p in w['evidence']}
        evidence.extend(w['evidence_hashes']);write(run/'verification/writing.json',w)
        return (w['timeline_equal'] and w['order_ok'] and w['seek_equal'] and w['gsap_seek_equal'] and w['bounds_ok'] and w['inactive_hidden'] and not w['final_visible'] and w['tip_error_px']<=1 and all(w[k]==0 for k in ['precomplete_diff','complete_diff','hidden_leaks']))
    check('writing_animation',writing_gate)
    def teaching_gate():
        from .annotations import load_teaching,compile_annotations
        from .teaching import build_teaching_timeline
        from .writing import load_writing,load_pencil_asset,timing_settings
        from .composition import camera_keys
        from .focus import compile_focus_keys
        t=read(run/'source/timeline.json')
        if not t.get('teaching') and not any((run/('source/'+n+'.json')).exists() for n in ['focus','annotations']):return True
        m,l,cfg=read(run/'source/manifest.json'),read(run/'layers/layers.json'),read(run/'source/config.json')
        plan=load_teaching(run,m,l);writing=load_writing(run,cfg) if (run/'source/writing.json').is_file() else None
        from .lesson import load_lesson,lesson_expectations,lesson_screen_passed
        lesson=load_lesson(run,m,l,plan)
        expected=build_teaching_timeline(m,l,read(run/'source/audio.json')['voices'],cfg,writing,plan)
        if dict(t,cameras=[],writing=timing_settings(t['writing']) if t.get('writing') else {})!=dict(expected,cameras=[],writing=timing_settings(expected['writing']) if expected.get('writing') else {}):return False
        if not plan:return True
        compiled=compile_annotations(plan,l,run/'verification/teaching-oracle') if plan['items'] else None
        if compiled:load_pencil_asset(run/'composition')
        expected['cameras']=compile_focus_keys(m,l,expected,plan,compiled,camera_keys(m,l,expected))
        path=run/'verification/teaching-expected.json';write(path,dict(timeline=expected,compiled=compiled,lesson=lesson_expectations(lesson,m,expected,plan) if lesson else None))
        r=browser(['--mode','teaching','--entry',str(run/'composition/index.html'),'--layers',str(run/'layers/layers.json'),'--timeline',str(path),'--dest',str(run/'verification/teaching-frames')])
        r['input_hash']=h;r['evidence_hashes']={str(Path(p).relative_to(run)):file_hash(p) for p in r['evidence']};evidence.extend(r['evidence_hashes']);write(run/'verification/teaching.json',r)
        return all(r[k] for k in ['timeline_equal','cameras_equal','geometry_equal','seek_equal','gsap_seek_equal','bounds_ok','inactive_hidden']) and not r['final_visible'] and r['tip_error_px']<=1 and all(r[k]==0 for k in ['original_pixel_diff','annotation_pixel_diff','future_leaks'])
    check('teaching_animation',teaching_gate)
    def lesson_gate():
        if not (run/'source/lesson.json').is_file():return True
        from .lesson import load_lesson,lesson_expectations,lesson_screen_passed
        from .annotations import load_teaching
        m,l=read(run/'source/manifest.json'),read(run/'layers/layers.json')
        p=load_teaching(run,m,l);lesson=load_lesson(run,m,l,p)
        expected=lesson_expectations(lesson,m,read(run/'source/timeline.json'),p or {'regions':[],'items':[]})
        screen=read(run/'verification/teaching.json') if expected['probes'] else None
        return checks['teaching_animation']['status']=='passed' and lesson_screen_passed(expected,screen)
    check('lesson_flow',lesson_gate)
    def flow_gate():
        t=read(run/'source/timeline.json')
        if t.get('writing',{}).get('mode')!='pencil':return True
        from .writing_units import compile_writing_units
        compile_writing_units(read(run/'layers/layers.json'))
        r=browser(['--mode','writing-flow','--entry',str(run/'composition/index.html'),'--layers',str(run/'layers/layers.json'),'--dest',str(run/'verification/flow-frames')])
        r['input_hash']=h;r['evidence_hashes']={str(Path(p).relative_to(run)):file_hash(p) for p in r['evidence']}
        write(run/'verification/writing-flow.json',r);evidence.extend(r['evidence_hashes'])
        return all(r[k] for k in ['order_ok','fit_ok','transitions_ok','stable_camera','seek_equal'])
    check('writing_flow',flow_gate)
    def pacing_gate():
        t=read(run/'source/timeline.json')
        if t.get('writing',{}).get('mode')!='pencil':return True
        from .narration_pacing import analyze_narration_pacing
        r=analyze_narration_pacing(t,read(run/'source/audio.json')['voices'],run)
        write(run/'verification/narration-pacing.json',r);evidence.extend(r['evidence_hashes'])
        return r['status']=='passed'
    check('narration_pacing',pacing_gate)
    check('hyperframes',lambda:bool(source_checks(read(run/'source/parts.json'),run,hyperframes_entry)))
    def media():
        t=read(run/'source/timeline.json'); data=probe(final); streams=data['streams']; v=next(s for s in streams if s['codec_type']=='video'); a=next(s for s in streams if s['codec_type']=='audio')
        if (v['width'],v['height'],v['avg_frame_rate'],int(v['nb_frames']),int(a['sample_rate']))!=(1920,1080,'30/1',t['total_frames'],24000): return False
        if abs(float(v['duration'])-float(a['duration']))>1/30: return False
        if command([ffmpeg(),'-v','error','-i',final,'-f','null','-'],timeout=1800).returncode: return False
        for rec in read(run/'source/audio.json')['voices']:
            p=local(run,rec['path'])
            if file_hash(p)!=rec['sha256']: return False
            with wave.open(str(p),'rb') as f:
                if (f.getnchannels(),f.getsampwidth(),f.getframerate(),f.getnframes())!=(1,2,24000,rec['samples']): return False
        return True
    check('final_media',media)
    def captions():
        from PIL import Image,ImageChops
        import io
        t=read(run/'source/timeline.json'); srt=run/'renders/captions.srt'
        if not srt.is_file() or not (run/'renders/master.mp4').is_file(): return False
        # Compare captioned/master at each caption midpoint; lossy compression tolerance.
        import re,subprocess
        ranges=re.findall(r'(\d\d):(\d\d):(\d\d),(\d{3}) --> (\d\d):(\d\d):(\d\d),(\d{3})',srt.read_text())
        if not ranges: return False
        def sec(parts): return int(parts[0])*3600+int(parts[1])*60+int(parts[2])+int(parts[3])/1000
        for row in ranges:
            at=(sec(row[:4])+sec(row[4:]))/2; pics=[]
            for p in [run/'renders/master.mp4',final]:
                r=subprocess.run([ffmpeg(),'-v','error','-ss',str(at),'-i',str(p),'-frames:v','1','-f','image2pipe','-vcodec','png','-'],capture_output=True,timeout=60)
                if r.returncode: return False
                pics.append(Image.open(io.BytesIO(r.stdout)).convert('RGB'))
            diff=ImageChops.difference(*pics); bbox=diff.crop((0,900,1920,1080)).getbbox()
            if not bbox: return False
            # PDF pixels may differ slightly after CRF encoding; reject caption-sized dark blocks above strip.
            from PIL import ImageStat
            if max(ImageStat.Stat(diff.crop((0,0,1920,900))).mean)>3: return False
        return True
    check('captions',captions)
    for kind in ['audio','visual']:
        def review(k=kind):
            r=read(run/'verification'/f'{k}-review.json')
            if r.get('status')!='passed' or r.get('input_hash')!=h or not r.get('notes') or not r.get('evidence'): return False
            if k=='audio' and r.get('mode')!='live-listened': return False
            return all(local(run,p).is_file() and file_hash(local(run,p))==sha for p,sha in r['evidence'].items())
        check(kind+'_meaning',review)
    complete=all(v['status']=='passed' for v in checks.values())
    report=dict(complete=complete,input_hash=h,checks=checks,evidence=evidence,final_sha256=file_hash(final) if final.is_file() else None,review_hashes={p.relative_to(run).as_posix():file_hash(p) for p in (run/'verification').glob('*-review.json')},live_audio='verified' if checks['audio_meaning']['status']=='passed' else 'unverified')
    path=run/'source/manifest.json'
    report['warnings']=caption_notation_warnings(read(path).get('segments',[])) if path.is_file() else []
    write(run/'verification/report.json',report); return report
