import copy
from pathlib import Path
from scripts.lab.review_pack.workbook_content import load_workbook_content, build_workbook_data
from scripts.lab.review_pack.workbook_render import render_workbook_html, read_workbook_payload
from scripts.lab.review_pack.workbook_md import write_workbook_md, check_workbook_md
from tests._workbook_fixture import create_workbook_run

ASSETS = Path('.claude/skills/logic-lab-review-pack/assets')

def test_safe_injection_and_relative_links(tmp_path):
    m, run = create_workbook_run(tmp_path)
    data = build_workbook_data(m, load_workbook_content(m,run), 'problems')
    data['meta']['title'] = '</script><!--한국어 제목'
    target = tmp_path/'문제지.html'
    target.write_text(render_workbook_html(data,ASSETS),encoding='utf-8')
    assert read_workbook_payload(target) == data
    text = target.read_text(encoding='utf-8')
    assert '\\u003c/script>' in text
    assert '__WORKBOOK_DATA__' not in text
    assert 'href="https://cdn.' not in text and 'src="https://cdn.' not in text
    assert '정답 전용 문구' not in text

def test_zero_questions_still_roundtrip(tmp_path):
    m, run = create_workbook_run(tmp_path)
    m['problems'] = []
    data = build_workbook_data(m, [], 'problems')
    path = tmp_path/'empty.html'; path.write_text(render_workbook_html(data,ASSETS),encoding='utf-8')
    assert read_workbook_payload(path)['problems'] == []
    md = write_workbook_md(data,m,tmp_path/'empty.md')
    assert '수록할 문항이 없습니다' in md.read_text(encoding='utf-8')

def test_changed_template_is_rejected(tmp_path):
    import shutil
    import pytest
    copied = tmp_path/'assets'; shutil.copytree(ASSETS,copied)
    path = copied/'workbook/problem.html'
    path.write_text(path.read_text(encoding='utf-8').replace('297mm','280mm'),encoding='utf-8')
    m, run = create_workbook_run(tmp_path/'input')
    data = build_workbook_data(m,load_workbook_content(m,run),'problems')
    with pytest.raises(ValueError): render_workbook_html(data,copied)

def test_git_export_keeps_the_literal_template_contract(tmp_path):
    import subprocess
    import pytest
    exported=tmp_path/'exported'; (exported/'workbook').mkdir(parents=True)
    for name in ('problem.html','answer.html','provenance.json'):
        result=subprocess.run(['git','show',':.claude/skills/logic-lab-review-pack/assets/workbook/'+name],capture_output=True)
        if result.returncode:
            pytest.skip('Git index is unavailable in this source distribution')
        (exported/'workbook'/name).write_bytes(result.stdout)
    m,run=create_workbook_run(tmp_path/'authoring')
    for mode in ('problems','answers'):
        data=build_workbook_data(m,load_workbook_content(m,run),mode)
        target=tmp_path/(mode+'.html')
        target.write_text(render_workbook_html(data,exported),encoding='utf-8')
        assert read_workbook_payload(target)==data


def test_local_patches_add_table_borders_and_optional_conditions(tmp_path):
    m, run = create_workbook_run(tmp_path)
    content = load_workbook_content(m, run)
    for mode in ('problems', 'answers'):
        text = render_workbook_html(build_workbook_data(m, content, mode), ASSETS)
        assert '#book th, #book td' in text and 'border: .3mm solid var(--ink)' in text
        assert '#book .original td { height: 7mm; }' in text
        assert "if (p.html.conditions && p.html.conditions.trim()) panel.append(block('조건'" in text
        assert "block('조건', p.html.conditions, 'conditions'), block('구할 것'" not in text

def test_local_patch_anchor_loss_is_rejected():
    import pytest
    from scripts.lab.review_pack.workbook_render import apply_local_patches
    with pytest.raises(ValueError): apply_local_patches('<style></style>', 'x.html')
