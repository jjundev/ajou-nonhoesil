"""Prepare a new owned-file stage without changing existing learning materials."""
from pathlib import Path
import json,shutil
from .manifest import load_manifest,output_names,DATA
from .explanation_content import within,CHECK_KEYS
from .explanation_render import write_explanations
from .workbook_render import read_workbook_payload

def prepare_explanation_stage(folder: Path, author_root: Path, stage: Path) -> Path:
    folder,author_root,stage=map(lambda p:Path(p).resolve(),(folder,author_root,stage))
    if stage.exists() or stage.is_relative_to(folder) or folder.is_relative_to(stage):raise ValueError('Existing/overlapping explanation stage')
    m=load_manifest(folder/DATA/'manifest.json')
    if m.get('review_presentation_version')!=2:raise ValueError('Explanations require workbook version 2')
    owned=m.get('generated_files',[])
    for relative in owned:
        if not within(folder,relative).is_file():raise ValueError('Missing owned file: '+relative)
    names=output_names(m['experiment'],review_presentation_version=2,problem_explanation_version=1)
    new_paths=[names['explanation_html'],names['explanation_md']]
    for p in m['problems']:
        if p['status']=='included':
            p['explanation_fragment']=f'problem-explanations/{p["id"]}.html'
            new_paths.append(DATA+'/'+p['explanation_fragment'])
    for f in author_root.rglob('*'):
        if f.is_symlink():raise ValueError('Symlink explanation authoring file')
        if f.is_file():new_paths.append(DATA+'/problem-explanations/'+f.relative_to(author_root).as_posix())
    for relative in new_paths:
        if within(folder,relative).exists() and relative not in owned:raise ValueError('User explanation file collision: '+relative)
    question=read_workbook_payload(folder/names['question_html'])
    # Validate before any stage is written; author_root contains the per-question files.
    from .explanation_content import load_explanations
    from tempfile import TemporaryDirectory
    with TemporaryDirectory() as temp:
        wrapped=Path(temp)/'problem-explanations';shutil.copytree(author_root,wrapped)
        load_explanations(m,question,Path(temp))
        stage.mkdir(parents=True)
        for relative in owned:
            target=stage/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(folder/relative,target)
        write_explanations(m,question,Path(temp),stage,stage/DATA/'assets')
        report=author_root/'검증결과.md'
        if report.is_file():shutil.copy2(report,stage/DATA/'problem-explanations/검증결과.md')
    m['problem_explanation_version']=1;m['explanation_checks']=dict.fromkeys(CHECK_KEYS,'not_run')
    m['generated_files']=sorted(p.relative_to(stage).as_posix() for p in stage.rglob('*') if p.is_file())
    (stage/DATA/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8')
    from .checks import check_pack
    errors=check_pack(stage)
    if errors:raise ValueError('\n'.join(errors))
    return stage
