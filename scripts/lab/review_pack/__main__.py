"""python -m scripts.lab.review_pack: sources, import-bank, build, check, publish."""
import argparse
import json
from pathlib import Path
from .sources import inventory
from .manifest import load_manifest, DATA
from .render import assemble
from .html2md import convert_pack
from .checks import check_pack
from .publish import publish
from scripts.lab import config
from .bank_import import import_bank
from .bank_provenance import check_bank_import

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    for cmd in ('sources','import-bank','build','check','publish','rerender','explain-stage'):
        p=sub.add_parser(cmd)
        if cmd not in {'check','rerender','explain-stage'}:p.add_argument('--root',type=Path,required=True)
        if cmd in {'sources','publish'}:p.add_argument('--experiment',type=int,required=True)
        if cmd in {'build','publish'}:p.add_argument('--stage',type=Path,required=True)
        if cmd=='build':p.add_argument('--run',type=Path,required=True)
        if cmd=='import-bank':
            p.add_argument('--bank',type=Path,required=True)
            p.add_argument('--run',type=Path,required=True)
        if cmd in {'check','rerender','explain-stage'}:p.add_argument('--folder',type=Path,required=True)
        if cmd=='explain-stage':
            p.add_argument('--author-root',type=Path,required=True)
            p.add_argument('--stage',type=Path,required=True)
    args=parser.parse_args(argv)
    try:
        if args.command=='sources':
            print(json.dumps(inventory(args.root,args.experiment),ensure_ascii=False,indent=2))
        elif args.command=='import-bank':
            run=import_bank(args.root,args.bank,args.run)
            imported=load_manifest(run/'manifest.json')
            print(json.dumps({'run':str(run),'items':len(imported['problems']),
                              'status':'authoring_pending'},ensure_ascii=False))
        elif args.command=='build':
            data=load_manifest(args.run/'manifest.json')
            errors=check_bank_import(args.run,data,root=args.root)
            if errors:raise ValueError('\n'.join(errors))
            assets=args.root/'.claude/skills/logic-lab-review-pack/assets'
            paths=assemble(data,args.run,args.stage,assets)
            convert_pack(paths['note_html'],paths['review_html'],manifest=data)
            evidence=args.run/'검증결과.md'
            if evidence.exists():(args.stage/'검증결과.md').write_bytes(evidence.read_bytes())
            data['generated_files']=sorted(p.relative_to(args.stage).as_posix() for p in args.stage.rglob('*') if p.is_file())
            paths['manifest'].write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
            errors=check_pack(args.stage)
            if errors:raise ValueError('\n'.join(errors))
            print(args.stage)
        elif args.command=='explain-stage':
            from .explanation_stage import prepare_explanation_stage
            print(prepare_explanation_stage(args.folder,args.author_root,args.stage))
        elif args.command=='check':
            errors=check_pack(args.folder)
            if errors:raise ValueError('\n'.join(errors))
            print('OK (mechanical checks only)')
        elif args.command=='rerender':
            from .workbook_rerender import rerender_workbook
            errors=rerender_workbook(args.folder)
            if errors:raise ValueError(chr(10).join(errors))
            print('OK '+str(args.folder))
        else:
            stage_data=load_manifest(args.stage/DATA/'manifest.json')
            if stage_data['experiment']!=args.experiment:raise ValueError('Experiment mismatch')
            target=args.root/'복습노트'/config.experiment_folder_name(args.experiment)
            backup=publish(args.stage,target,args.root)
            print(json.dumps({'output':str(target),'backup':str(backup) if backup else None},ensure_ascii=False))
        return 0
    except (ValueError,OSError) as exc:
        print('FAIL: '+str(exc));return 1

if __name__=='__main__':
    raise SystemExit(main())
