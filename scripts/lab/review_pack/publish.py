"""Validated local publication with preserved backups and rollback."""
from pathlib import Path
import os
import shutil
import tempfile
import uuid
from .checks import check_pack
from .manifest import load_manifest,DATA
from .sources import file_sha256
from scripts.lab import config
from .bank_provenance import check_bank_import

def publish(stage,destination,root):
    root=Path(root).resolve();stage=Path(stage).resolve();dest=Path(destination).resolve()
    errors=check_pack(stage)
    if errors:raise ValueError('\n'.join(errors))
    data=load_manifest(stage/DATA/'manifest.json')
    if data.get('problem_explanation_version')==1:
        checks=data['explanation_checks']
        if checks['source_visual']!='pass' or checks['content'] not in {'pass','self_review'} or checks['browser']!='pass':
            raise ValueError('문제설명 검토: 원문·내용·브라우저 확인이 필요합니다')
    if data.get('review_presentation_version')==2:
        from .workbook_figures import check_redrawn_figures
        errors=check_redrawn_figures(stage,data,require_review=True)
        if errors: raise ValueError('\n'.join(errors))
    errors=check_bank_import(stage,data,root=root)
    if errors:raise ValueError('\n'.join(errors))
    expected=root/'복습노트'/config.experiment_folder_name(data['experiment'])
    if dest!=expected or stage==dest or stage.is_relative_to(dest) or dest.is_relative_to(stage):
        raise ValueError('Invalid/overlapping destination')
    for tree in (stage,dest):
        if tree.exists() and any(p.is_symlink() for p in tree.rglob('*')):raise ValueError('Symlink in pack')
    for source in data['sources']:
        path=(root/source['path']).resolve()
        if not path.is_relative_to(root):raise ValueError('Source outside root')
        if file_sha256(path)!=source['sha256']:raise ValueError('원문 변경: '+source['path'])
    if data['checks']['browser']!='pass' or data['checks']['content'] not in {'pass','self_review'} or data['checks']['source_visual']!='pass':
        raise ValueError('브라우저·원문·내용 검토 기록이 필요합니다')
    new_owned=set(data.get('generated_files',[]))
    actual={p.relative_to(stage).as_posix() for p in stage.rglob('*') if p.is_file()}
    if new_owned!=actual:raise ValueError('generated_files must match stage')
    old_owned=set()
    if (dest/DATA/'manifest.json').exists():
        old_owned=set(load_manifest(dest/DATA/'manifest.json').get('generated_files',[]))
    user_files=[p for p in dest.rglob('*') if p.is_file() and p.relative_to(dest).as_posix() not in old_owned] if dest.exists() else []
    if any(p.relative_to(dest).as_posix() in new_owned for p in user_files):raise ValueError('User file collision')
    dest.parent.mkdir(parents=True,exist_ok=True)
    prepared=Path(tempfile.mkdtemp(prefix='.review-pack-',dir=dest.parent))
    shutil.copytree(stage,prepared,dirs_exist_ok=True)
    for p in user_files:
        target=prepared/p.relative_to(dest);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
    backup=None
    if dest.exists():
        backup=dest.with_name(dest.name+'.backup-'+uuid.uuid4().hex[:12])
        os.replace(dest,backup)
    try:
        os.replace(prepared,dest)
    except OSError:
        if backup is not None:os.replace(backup,dest)
        raise
    return backup
