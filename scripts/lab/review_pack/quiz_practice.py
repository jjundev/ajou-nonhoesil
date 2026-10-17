"""Optional quiz practice policy; structural validation is not content review."""
from collections import Counter

QUIZ_COUNTS = {'true_false': 4, 'fill_blank': 3, 'breadboard': 1, 'short_answer': 2}
QUIZ_LABELS = {'true_false':'T/F', 'fill_blank':'빈칸', 'breadboard':'브레드보드 작도', 'short_answer':'짧은 서술형'}


def validate_quiz_practice(manifest: dict) -> list[str]:
    rows=manifest.get('problems',[])
    rows=[p for p in rows if isinstance(p,dict)] if isinstance(rows,list) else []
    errors=[]
    if 'quiz_practice_version' not in manifest:
        return [str(p.get('id'))+': question_type requires quiz_practice_version' for p in rows if 'question_type' in p]
    if type(manifest['quiz_practice_version']) is not int or manifest['quiz_practice_version']!=1:
        errors.append('quiz_practice_version must be 1 or absent')
    if manifest.get('review_presentation_version')!=2 or manifest.get('problem_explanation_version')!=2:
        errors.append('quiz_practice_version requires workbook 2 and explanation 2')
    counts=Counter(); started=False
    for p in rows:
        ident=str(p.get('id')); kind=p.get('question_type')
        if 'question_type' in p and (not isinstance(kind,str) or kind not in QUIZ_COUNTS):
            errors.append(ident+': invalid question_type'); continue
        if p.get('status')!='included': continue
        if 'question_type' not in p:
            if started: errors.append(ident+': existing questions must precede quiz practice')
            continue
        started=True
        if p.get('kind')=='practice': counts[kind]+=1
        else: errors.append(ident+': quiz question must be practice')
        if (p.get('given_answer') is not None or 'bank_question_id' in p
                or p.get('answer_status')!='verified' or p.get('scope')!='current'
                or not p.get('sources') or not p.get('topics')):
            errors.append(ident+': quiz practice requires verified/current, sources/topics, no bank/given answer')
        answer=p.get('derived_answer')
        if not isinstance(answer,str) or not answer.strip() or (kind=='true_false' and answer not in ('T','F')):
            errors.append(ident+': invalid quiz derived_answer')
    for kind,expected in QUIZ_COUNTS.items():
        if counts[kind]!=expected: errors.append(f'quiz {kind}: expected {expected}, included {counts[kind]}')
    return errors
