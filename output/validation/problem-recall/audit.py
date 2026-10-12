from pathlib import Path
import json,hashlib,subprocess,itertools,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
from scripts.lab.review_pack.checks import check_pack
out=Path('output/validation/problem-recall'); result=[]
for number in range(1,7):
 nn=f'{number:02d}';folder=Path('복습노트')/f'실험{nn}'
 errors=check_pack(folder);assert not errors,(nn,errors)
 baseline=json.loads((out/f'baseline-{nn}.json').read_text(encoding='utf-8'))
 m=json.loads((folder/'자료/manifest.json').read_text(encoding='utf-8'))
 assert m['problem_explanation_version']==2
 for key in ('experiment','sources','topics','problems','checks','review_presentation_version','note_presentation_version'):
  assert m.get(key)==baseline['manifest'].get(key),(nn,key)
 for rel,digest in baseline['files'].items():
  p=folder/rel;assert p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==digest,(nn,rel)
 mutable={f'실험{nn}_문제설명.html',f'실험{nn}_문제설명.md','자료/manifest.json'}
 unexpected=[f.relative_to(folder).as_posix() for f in folder.rglob('*') if f.is_file() and f.relative_to(folder).as_posix() not in baseline['files'] and f.relative_to(folder).as_posix() not in mutable and not f.relative_to(folder).as_posix().startswith('자료/problem-explanations/')]
 assert not unexpected,(nn,unexpected)
 sources=[]
 for src in m['sources']:
  actual=hashlib.sha256(Path(src['path']).read_bytes()).hexdigest();assert actual==src['sha256'],(nn,src['path'])
  sources.append(dict(path=src['path'],expected=src['sha256'],actual=actual))
 backups=[]
 for backup in sorted(Path('복습노트').glob(f'실험{nn}.backup-*')):
  matches=all((backup/rel).is_file() and hashlib.sha256((backup/rel).read_bytes()).hexdigest()==digest for rel,digest in baseline['files'].items())
  if matches:backups.append(backup.as_posix())
 assert backups,nn
 result.append(dict(experiment=nn,count=sum(p['status']=='included' for p in m['problems']),preserved_files=len(baseline['files']),sources=sources,matching_backups=backups,check='pass',metadata='equal',unexpected_files=unexpected))
assert [r['count'] for r in result]==[12,14,15,12,19,14]
net=Path('보고서/실험02/결선도/netlist.md')
committed=subprocess.check_output(['git','show','HEAD:'+net.as_posix()])
assert committed==net.read_bytes()
evidence=dict(packs=result,total=86,netlist=dict(path=net.as_posix(),committed=hashlib.sha256(committed).hexdigest(),current=hashlib.sha256(net.read_bytes()).hexdigest()))
(out/'final-audit.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
p=out/'calculation-06.json';d=json.loads(p.read_text(encoding='utf-8'))
d['jk_actual_cases']=[dict(J=j,K=k,Q=q,Qnext=(j and not q) or (not k and q)) for j,k,q in itertools.product([0,1],repeat=3)]
d['t_actual_cases']=[dict(T=t,Q=q,Qnext=t^q) for t,q in itertools.product([0,1],repeat=2)]
for row in d['jk_actual_cases']:row['Qnext']=int(row['Qnext'])
assert [row['Qnext'] for row in d['jk_actual_cases']]==[0,1,0,0,1,1,1,0]
assert [row['Qnext'] for row in d['t_actual_cases']]==[0,1,1,0]
d['tuple_columns']={'jk':['J','K','Q','Qnext'],'t':['T','Q','Qnext']}
d['tuple_assumptions']='One permitted update; complementary prior state; asynchronous preset/clear inactive; specified triggering edge. JK truth-table order hold/reset/set/toggle; T hold/toggle.'
d['source_digest_evidence']=result[-1]['sources'];d['final_audit_note']='Actual tuple and digest evidence added in Task10; original labels/path-only evidence retained.'
p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('6 packs, 86 explanations, all non-explanation files preserved')
print([(r['experiment'],r['preserved_files'],len(r['sources']),r['matching_backups']) for r in result])
print('netlist committed/current SHA:',evidence['netlist']['current'])

from scripts.lab.review_pack.html2md import Parser

def canon(n):
    if isinstance(n,str): return n
    return (n.tag,n.attrs,[canon(c) for c in n.children])

def sections(fragment):
    parser=Parser(); parser.feed(fragment)
    return {n.attrs['data-explanation']:canon(n) for n in parser.root.walk() if 'data-explanation' in n.attrs}

counts=[]
for item in result:
    nn=item['experiment']; folder=Path(f'복습노트/실험{nn}/자료/problem-explanations')
    backup=Path(item['matching_backups'][0])/'자료/problem-explanations'
    manifest=json.loads(Path(f'복습노트/실험{nn}/자료/manifest.json').read_text(encoding='utf-8'))
    count=0
    for problem in manifest['problems']:
        if problem['status']!='included': continue
        ident=problem['id']; current=(folder/f'{ident}.html').read_bytes()
        old=sections((backup/f'{ident}.html').read_text(encoding='utf-8')); new=sections(current.decode('utf-8'))
        for key in ('understand','start','solve','verify','pitfall','retry'):
            assert old[key]==new[key],(nn,ident,key)
        assert Path(f'docs/learning-pack-source/실험{nn}/problem-explanations/{ident}.html').read_bytes()==current,(nn,ident)
        count+=1
    counts.append(count)
evidence['six_old_sections_identical']=counts
(out/'final-audit.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('86 authored/published fragments exact; original six sections identical:',counts)

from scripts.lab.review_pack.manifest import validate_manifest
from scripts.lab.review_pack.explanation_content import load_explanations
from scripts.lab.review_pack.workbook_render import read_workbook_payload
source_contract=[]
for number in (4,5):
    author=Path(f'docs/learning-pack-source/실험{number:02d}')
    manifest=json.loads((author/'manifest.json').read_text(encoding='utf-8'))
    assert validate_manifest(manifest)==[]
    question=read_workbook_payload(Path(f'복습노트/실험{number:02d}/실험{number:02d}_기출문제.html'))
    loaded=load_explanations(manifest,question,author)
    assert len(loaded)=={4:12,5:19}[number]
    source_contract.append(dict(experiment=number,validation='pass',loaded=len(loaded),checks=manifest['explanation_checks']))
evidence['original_source_v2_contract']=source_contract
(out/'final-audit.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Original source04/05 manifest and v2 fragments validate/load:',source_contract)
