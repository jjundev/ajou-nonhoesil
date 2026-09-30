"""Create a new authoring run from finished, unchanged extraction evidence."""
import hashlib
import html
import json
import os
from pathlib import Path
import shutil
import tempfile
from urllib.parse import quote
from .bank_index import build_authoring_index,initial_manifest
from .question_bank import load_question_bank,validate_question_bank,check_question_bank_files,_unique_json_object
from .question_bank_sources import _evidence_path
from .sources import file_sha256

GUIDE_NAME='원문과_저작안내.md'

def _json_write(path,data):
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def _project_path(root,path):
    root=Path(root).absolute();path=Path(path).absolute()
    try:relative=path.relative_to(root).as_posix()
    except ValueError as exc:raise ValueError('Path must be inside project root') from exc
    return _evidence_path(root,relative)

def _guide(bank,index):
    occurrences={o['id']:o for o in bank['occurrences']}
    lines=['# 원문과 저작 안내','',
        '문제은행은 추출 증거입니다. confirmed/candidate는 답안 연결 상태이며 정답 검증 상태가 아닙니다.',
        '모든 문제는 저작 대기로 시작합니다. 설명·개념 연결·독립 풀이 후 수록 여부를 결정하세요.',
        '[은행 JSON 사본](evidence/question-bank.json)','']
    for q in index['questions']:
        lines += [f'<a id="{q["question_id"]}"></a>',f'## {q["question_id"]} · {q["kind"]}','',
            f'- 판독: {q["representative_reading"]} / 저작: {q["authoring_status"]}']
        for ident in q['occurrence_ids']:
            o=occurrences[ident]
            lines.append(f'- 등장 {ident}, 번호 {o["original_number"]}: '+json.dumps(o['location'],ensure_ascii=False))
        for answer in q['provided_answers']:
            lines.append(f'- 제공 답안 {answer["occurrence_id"]} → {answer["target_id"]}: {answer["status"]} / {html.escape(answer["reason"])}')
            for block in occurrences[answer['occurrence_id']]['blocks']:
                lines.append('  - '+html.escape(block['text']))
                if block['type']=='math':lines.append('  - LaTeX: '+html.escape(block['tex']))
                if block['type']=='table':lines.append('  - 표: '+json.dumps(block['cells'],ensure_ascii=False))
                if block['type']=='figure':lines.append('  - 자산 ID: '+block['asset_id'])
        for r in q['relations']:
            lines.append(f'- 관계 {r["type"]}: {r["from_id"]} → {r["to_id"]} / {html.escape(r["reason"])}')
        for u in q['unresolved']:lines.append(f'- 보류 {u["target_id"]}: {html.escape(u["reason"])}')
        lines += ['- 답 없는 문제용 자산: '+', '.join(q['safe_problem_asset_ids']),
                  '- 증거용 자산: '+', '.join(q['evidence_only_asset_ids']),'']
    lines += ['## 원문 자산','']
    for a in bank['assets']:
        lines.append(f'- [{a["id"]}](evidence/{quote(a["path"],safe="/")}) · {a["role"]} · 답 노출 {a["answer_exposure"]}')
    return '\n'.join(lines)+'\n'

def import_bank(root,bank_path,run):
    root=Path(root).absolute()
    bank_path=_project_path(root,bank_path);run=_project_path(root,run)
    if run.exists() or os.path.lexists(run):raise ValueError('Run already exists')
    if run.is_relative_to(bank_path.parent) or bank_path.parent.is_relative_to(run):
        raise ValueError('Run overlaps input bank directory')
    raw=bank_path.read_bytes()
    bank=json.loads(raw.decode('utf-8-sig'),object_pairs_hook=_unique_json_object)
    errors=validate_question_bank(bank)
    if errors:raise ValueError('\n'.join(errors))
    if bank['audit']['status'] not in ('complete','complete_with_holds'):
        raise ValueError('Import requires a finished question bank')
    errors=check_question_bank_files(bank,root=root,bank_dir=bank_path.parent)
    if errors:raise ValueError('\n'.join(errors))
    digest=hashlib.sha256(raw).hexdigest()
    index=build_authoring_index(bank,digest)
    manifest=initial_manifest(bank,bank_path.relative_to(root).as_posix(),digest)
    run.parent.mkdir(parents=True,exist_ok=True)
    prepared=Path(tempfile.mkdtemp(prefix='.bank-import-',dir=run.parent))
    try:
        (prepared/'evidence').mkdir()
        (prepared/'evidence/question-bank.json').write_bytes(raw)
        for asset in bank['assets']:
            source=_evidence_path(bank_path.parent,asset['path'])
            target=_evidence_path(prepared/'evidence',asset['path'])
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(source,target)
            if file_sha256(target)!=asset['sha256']:raise ValueError('Asset changed while importing: '+asset['id'])
        _json_write(prepared/'authoring-index.json',index)
        _json_write(prepared/'manifest.json',manifest)
        (prepared/GUIDE_NAME).write_text(_guide(bank,index),encoding='utf-8')
        for name in ('sections','problems','figures'):(prepared/name).mkdir()
        if file_sha256(bank_path)!=digest:raise ValueError('Bank changed while importing')
        errors=check_question_bank_files(bank,root=root,bank_dir=bank_path.parent)
        if errors:raise ValueError('\n'.join(errors))
        # Exclusive reservation prevents a concurrent author from being overwritten.
        run.mkdir(exist_ok=False)
        try:
            for entry in prepared.iterdir():entry.rename(run/entry.name)
        except OSError as exc:
            raise OSError(f'Incomplete import at {run}: {exc}') from exc
    finally:
        # Only the tempfile we created, under the already checked output parent.
        if prepared.parent==run.parent and prepared.name.startswith('.bank-import-'):
            shutil.rmtree(prepared)
    return run

def copy_import_material(run,out,manifest):
    if 'bank_import' not in manifest:return
    from .bank_provenance import check_bank_import
    run,out=Path(run),Path(out)
    errors=check_bank_import(run,manifest)
    if errors:raise ValueError('\n'.join(errors))
    binding=manifest['bank_import']
    snapshot=_evidence_path(run,binding['snapshot_path'])
    bank=load_question_bank(snapshot)
    paths=[binding['snapshot_path'],binding['index_path'],GUIDE_NAME]
    paths += ['evidence/'+a['path'] for a in bank['assets']]
    for relative in paths:
        target=_evidence_path(out,relative)
        if target.exists():raise ValueError('Stage evidence collision: '+relative)
    for relative in paths:
        source=_evidence_path(run,relative);target=_evidence_path(out,relative)
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
