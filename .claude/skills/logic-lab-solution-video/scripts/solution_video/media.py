from pathlib import Path
import functools,json,os,shutil,wave
from .util import checked,command,write,file_hash,local
from .contracts import InputError
@functools.lru_cache
def ffmpeg():
    candidates=[os.environ.get('LOGIC_LAB_FFMPEG'),shutil.which('ffmpeg'),'/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg']
    for p in candidates:
        if p and Path(p).is_file() and ' subtitles ' in command([p,'-filters']).stdout: return p
    raise InputError('FFmpeg with libass subtitles missing; supply LOGIC_LAB_FFMPEG')
def probe(path): return json.loads(checked(['ffprobe','-v','error','-show_streams','-show_format','-of','json',path]).stdout)
def source_checks(parts,run,entry):
    result=[]
    for p in parts:
        html=local(run,p['entry']); args=['node',entry,'check',html.parent,'--json','--samples','3']
        r=command(args,timeout=180)
        dest=Path(run)/'verification'/('check-'+p['key']+'.json'); write(dest,{'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'entry_sha256':file_hash(entry),'html_sha256':file_hash(html)})
        if r.returncode: raise InputError('HyperFrames check failed; inspect '+str(dest))
        result.append(dest)
    return result

def render_master(parts,timeline,audio,run,hyperframes_entry):
    run=Path(run).resolve(); entry=Path(hyperframes_entry).resolve(); source_checks(parts,run,entry)
    outputs=[]; work=run/'renders'; work.mkdir(parents=True,exist_ok=True)
    for part in parts:
        html=local(run,part['entry']); out=work/(part['key']+'.mp4')
        r=command(['node',entry,'render','--composition',html.name,'--quality','delivery','--workers','2','--output',out],cwd=html.parent,timeout=7200)
        (work/(part['key']+'.log')).write_text(r.stdout+'\n'+r.stderr,encoding='utf-8')
        if r.returncode or not out.is_file(): raise InputError('HyperFrames render failed; inspect renders/'+part['key']+'.log')
        v=next(s for s in probe(out)['streams'] if s['codec_type']=='video')
        if int(v.get('nb_frames',0))!=part['last_frame']-part['first_frame']: raise InputError('render frame count mismatch')
        outputs.append(out)
    mixed=bytearray(timeline['total_samples']*2); voices={a['id']:a for a in audio}
    for s in timeline['segments']:
        a=voices[s['id']]; p=local(run,a['path'])
        if file_hash(p)!=a['sha256']: raise InputError('PCM hash changed')
        with wave.open(str(p),'rb') as f:
            if (f.getnchannels(),f.getsampwidth(),f.getframerate(),f.getnframes())!=(1,2,24000,a['samples']): raise InputError('PCM provenance mismatch')
            raw=f.readframes(f.getnframes())
        start=s['start_sample']*2
        if start+len(raw)>s['end_sample']*2: raise InputError('voice exceeds measured slot')
        mixed[start:start+len(raw)]=raw
    with wave.open(str(work/'narration.wav'),'wb') as f: f.setparams((1,2,24000,0,'NONE','')); f.writeframes(mixed)
    for i,p in enumerate(outputs): shutil.copyfile(p,work/f'part-{i}.mp4')
    (work/'concat.txt').write_text('\n'.join("file 'part-"+str(i)+".mp4'" for i in range(len(outputs))),encoding='utf-8')
    master=work/'master.mp4'; pending=work/'master.pending.mp4'
    checked([ffmpeg(),'-y','-v','error','-f','concat','-safe','1','-i','concat.txt','-i','narration.wav','-c:v','copy','-c:a','aac','-b:a','128k','-movflags','+faststart',pending],cwd=work,timeout=300)
    os.replace(pending,master); return master
