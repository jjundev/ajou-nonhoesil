"""Read-only inventory and validation commands for extracted question banks."""
import argparse
import json
import sys
from pathlib import Path
from .question_bank import load_question_bank, check_question_bank_files, summarize_question_bank
from .question_bank_sources import inventory_quiz_sources

def main(argv=None):
    parser=argparse.ArgumentParser(description='Read-only question bank evidence checks')
    commands=parser.add_subparsers(dest='command',required=True)
    inv=commands.add_parser('inventory'); inv.add_argument('--root',type=Path,required=True); inv.add_argument('--experiment',type=int,required=True)
    check=commands.add_parser('check'); check.add_argument('--root',type=Path,required=True); check.add_argument('--bank',type=Path,required=True)
    args=parser.parse_args(argv)
    try:
        if args.command=='inventory':
            result={'experiment':args.experiment,'sources':inventory_quiz_sources(args.root,args.experiment)}
        else:
            data=load_question_bank(args.bank)
            errors=check_question_bank_files(data,root=args.root,bank_dir=args.bank.parent)
            if errors: raise ValueError('\n'.join(errors))
            result={'mechanical_check':'pass','audit_status':data['audit']['status'],
                    'recorded_source_visual':data['audit']['checks']['source_visual'],'counts':summarize_question_bank(data)}
        print(json.dumps(result,ensure_ascii=False,indent=2)); return 0
    except (ValueError,OSError) as exc:
        print('FAIL: '+str(exc),file=sys.stderr); return 1

if __name__=='__main__':
    if hasattr(sys.stdout,'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr,'reconfigure'): sys.stderr.reconfigure(encoding='utf-8')
    raise SystemExit(main())
