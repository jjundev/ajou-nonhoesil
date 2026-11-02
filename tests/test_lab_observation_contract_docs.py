"""Execute complete schema examples so authoring docs cannot drift from the parser."""
from pathlib import Path
import re
from scripts.lab.netlist_parser import parse_netlist
from scripts.lab.observations import procedure_issues

def test_v3_document_examples_are_executable(tmp_path):
    text=Path('docs/schema/lab-netlist-v3.md').read_text()
    examples=[b for b in re.findall(r'```markdown\n(.*?)```',text,re.S) if b.startswith('---\n')]
    assert examples, 'schema must provide a complete runnable netlist example'
    for i,block in enumerate(examples):
        p=tmp_path/f'example-{i}.md'; p.write_text(block)
        n=parse_netlist(p); c=n.circuits[0]
        assert c.procedures
        assert procedure_issues(c,c.procedures[0])==[]
        assert c.stages[0]['procedure']==c.procedures[0].id

def test_clock_authoring_rules_cover_continuous_and_single_pulses():
    for skill in ('draft-lab-spec', 'prep-lab-checklist'):
        text = Path(f'.claude/skills/{skill}/SKILL.md').read_text(encoding='utf-8')
        for phrase in ('반복 클록', 'RUN', '단일 펄스', '교안 우선', 'Vpp', '기록 보존'):
            assert phrase in text, (skill, phrase)
