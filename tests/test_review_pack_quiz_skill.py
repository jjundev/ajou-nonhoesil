"""Executable examples and reference reachability; prose is application-reviewed."""
import json,re
from pathlib import Path
from scripts.lab.review_pack.quiz_practice import QUIZ_COUNTS

SKILL=Path('.claude/skills/logic-lab-review-pack')


def test_full_authoring_requires_quiz_reference():
    target=SKILL/'references/quiz-practice.md'
    assert target.is_file()
    links=re.findall(r'\]\(([^)]+)\)',(SKILL/'SKILL.md').read_text(encoding='utf-8'))
    assert any((SKILL/link).resolve()==target.resolve() for link in links)


def test_documented_policy_matches_code():
    text=(SKILL/'references/quiz-practice.md').read_text(encoding='utf-8')
    contract=json.loads(re.search(r'```json\s*(.*?)```',text,re.S)[1])
    assert contract['quiz_practice_version']==1
    assert contract['counts']==QUIZ_COUNTS
    assert contract['apply_to']==['new','full_regeneration']
    assert contract['preserve_on']==['rerender','pdf_export','navigation_only','explanation_only']
