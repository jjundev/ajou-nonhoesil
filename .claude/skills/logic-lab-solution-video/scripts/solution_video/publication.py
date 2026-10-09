from pathlib import Path
import os,shutil,uuid,re,unicodedata
from .util import read,write,file_hash,local,digest as digest_key
from .verify import verification_fingerprint
from .contracts import InputError

def report_current(run,report):
    required={'content','original_svg','hyperframes','final_media','captions','audio_meaning','visual_meaning'}
    reviews=report.get('review_hashes',{})
    return (report.get('input_hash')==verification_fingerprint(run) and report.get('live_audio')=='verified'
        and required<=report.get('checks',{}).keys() and all(report['checks'][k]['status']=='passed' for k in required)
        and len(reviews)==2 and all(local(run,p).is_file() and file_hash(local(run,p))==sha for p,sha in reviews.items()))

def output_filename(item,run):
    manifest=run/'source/manifest.json'
    if not manifest.is_file():return item['filename']
    m=read(manifest)
    if m['problem_id']!=item['id']:raise InputError('manifest/item identity mismatch')
    title=unicodedata.normalize('NFC',m['title'])
    title=re.sub(r'[\\/:*?"<>|\x00-\x1f]+',' ',title)
    title=' '.join(title.split()).strip(' .')
    if not title:raise InputError('empty sanitized title')
    result=item['id']+' — '+title
    while len((result+'.mp4').encode('utf-8'))>240:result=result[:-1]
    return result.rstrip(' .')+'.mp4'

def publication_current(run,filename,root):
    try:
        r=read(run/'verification/publication.json')
        target=str(root/filename)
        return target in r['published'] and all(Path(p).is_file() and file_hash(p)==sha for p,sha in r['published'].items())
    except (OSError,ValueError,KeyError):return False

def _rollback(journal):
    for op in reversed(journal['operations']):
        target,backup=Path(op['target']),Path(op['backup'])
        if backup.is_file():
            if target.exists(): target.unlink()
            os.replace(backup,target)
        elif not op['had_previous'] and target.exists() and file_hash(target)==op['new_sha256']: target.unlink()

def publish_batch(batch):
    from .review_adapter import _modules
    _,budget=_modules(); from importlib import import_module
    lock=import_module('_logic_lab_tts_lib.cache').file_lock
    batch=Path(batch).resolve(); production=batch.parent.parent; root=production.parent
    with lock(production/'publish.lock'): return _publish(batch,production,root)

def _publish(batch,production,root):
    data=read(batch/'batch.json'); errors=[]; ready=[]; names=set()
    for original in data['items']:
        item=dict(original)
        try:
            run=local(batch,item['run']);filename=output_filename(item,run);item['filename']=filename
            if Path(filename).name!=filename or not filename.endswith('.mp4') or filename in names:
                return {'complete':False,'published':[],'errors':[{'reason':'unsafe or duplicate output title'}]}
            names.add(filename)
            report=read(run/'verification/report.json');final=run/'renders/final.mp4'
            if not report['complete'] or file_hash(final)!=report['final_sha256'] or not report_current(run,report):raise InputError('final changed or not currently verified')
            ready.append((item,run,final,report))
        except Exception as ex:errors.append({'id':item['id'],'reason':str(ex)[:300]})
    journal_path=batch/'publication-journal.json'
    if journal_path.exists():
        old=read(journal_path)
        if old['status']=='pending': _rollback(old); old['status']='rolled-back';write(journal_path,old)
    if not ready: return {'complete':False,'published':[],'errors':errors}
    latest=read(production/'latest.json') if (production/'latest.json').is_file() else {}
    complete_catalog=read(batch/'catalog.json').get('complete') if (batch/'catalog.json').is_file() else False
    already_complete=complete_catalog and latest.get('batch')==batch.relative_to(production).as_posix()
    if (errors or already_complete) and all(publication_current(run,item['filename'],root) for item,run,_,_ in ready):
        return {'complete':not errors,'published':[i['filename'] for i,_,_,_ in ready],'errors':errors}
    staging=production/'.staging'/uuid.uuid4().hex; staging.mkdir(parents=True)
    backups=production/'이전버전'/uuid.uuid4().hex; backups.mkdir(parents=True)
    journal={'status':'pending','operations':[]}; write(journal_path,journal)
    published=[]; catalog=[]
    def install(src,target):
        slot=staging/('new-'+str(len(journal['operations']))); shutil.copyfile(src,slot)
        op={'target':str(target),'backup':str(backups/str(len(journal['operations']))),'had_previous':target.exists(),'new_sha256':file_hash(slot)}
        journal['operations'].append(op); write(journal_path,journal)
        if target.exists(): os.replace(target,op['backup'])
        os.replace(slot,target)
    try:
        for item,run,final,report in ready:
            target=root/item['filename']
            if not publication_current(run,item['filename'],root):install(final,target)
            published.append(item['filename'])
            catalog.append({'problem_id':item['id'],'path':item['filename'],'size':target.stat().st_size,'sha256':file_hash(target),'run':item['run']})
        write(staging/'catalog.json',{'batch':str(batch),'complete':not errors,'files':catalog})
        install(staging/'catalog.json',batch/'catalog.json')
        (staging/'README.md').write_text('\n'.join(f"- {c['problem_id']}: {c['path']} ({c['sha256']})" for c in catalog)+'\n',encoding='utf-8')
        install(staging/'README.md',batch/'README.md')
        if not errors:
            write(staging/'latest.json',{'batch':batch.relative_to(production).as_posix(),'files':catalog})
            install(staging/'latest.json',production/'latest.json')
        from .state import stage_fingerprint
        for item,run,final,report in ready:
            receipt=staging/('receipt-'+digest_key(item['id'])+'.json')
            write(receipt,{'problem_id':item['id'],'published':{str(root/item['filename']):file_hash(root/item['filename']),str(batch/'catalog.json'):file_hash(batch/'catalog.json')}})
            target=run/'verification/publication.json';install(receipt,target)
            state=read(run/'state.json') if (run/'state.json').exists() else {'schema_version':1,'stages':{}}
            state['stages']['publish']={'fingerprint':stage_fingerprint(run,'publish'),'outputs':{'verification/publication.json':file_hash(target)}}
            statefile=staging/('state-'+digest_key(item['id'])+'.json');write(statefile,state);install(statefile,run/'state.json')
        journal['status']='committed';write(journal_path,journal)
    except Exception as ex:
        _rollback(journal); journal['status']='rolled-back';write(journal_path,journal)
        return {'complete':False,'published':[],'errors':errors+[{'reason':'publication rolled back: '+str(ex)[:200]}]}
    finally: shutil.rmtree(staging,ignore_errors=True)
    return {'complete':not errors,'published':published,'errors':errors}
