import copy
import json
import pytest
from scripts.lab.review_pack import table_layout as layout
from scripts.lab.review_pack.html2md import Parser, export_document

def table(headers=('A','Q'), values=('0','')):
    return '<table><thead><tr>'+''.join(f'<th>{v}</th>' for v in headers)+'</tr></thead><tbody><tr>'+''.join(f'<td>{v}</td>' for v in values)+'</tr></tbody></table>'

def schema(pair=False):
    entry=dict(key='q/original/0', expected_headers=['A','Q'], columns=[dict(role='input',kind='signal',group='입력'),dict(role='output',kind='expression',group='출력')],boundaries=[dict(left=0,kind='major')])
    if pair:entry['pair']='q-pair'
    entries=[entry]
    if pair:
        other=copy.deepcopy(entry);other['key']='q/explanation/0';entries.append(other)
    return dict(version=1,tables=entries)

def nodes(source,tag):
    p=Parser();p.feed(source);return [n for n in p.root.walk() if n.tag==tag]

def test_explicit_roles_override_header_names():
    s=schema();s['tables'][0]['columns'][0].update(role='output',group='출력')
    result=layout.layout_problem_tables('q',dict(original=table()),s)['original']
    assert nodes(result,'th')[-2].attrs['data-layout-role']=='output'

def test_paired_blank_and_state_tables_share_widths():
    result=layout.layout_problem_tables('q',dict(original=table(),explanation=table(values=('1','Q(t−1) ⊕ T'))),schema(True))
    a=[c.attrs['style'] for c in nodes(result['original'],'col')]
    b=[c.attrs['style'] for c in nodes(result['explanation'],'col')]
    assert a==b
    assert float(a[1].split(':')[1][:-3])>6

def test_group_boundaries_do_not_add_data_columns():
    result=layout.layout_problem_tables('q',dict(original=table()),schema())['original']
    assert len(nodes(result,'td'))==2
    assert [n.children for n in nodes(result,'td')]==[['0'],[]]
    assert [n.children for n in nodes(result,'th')[:2]]==[['입력'],['출력']]
    assert nodes(result,'th')[-2].attrs['data-layout-boundary']=='major-right'

@pytest.mark.parametrize('change',['header','columns','missing','extra','duplicate','pair'])
def test_layout_rejects_drift(change):
    s=schema(True);parts=dict(original=table(),explanation=table())
    if change=='header':s['tables'][0]['expected_headers'][0]='X'
    if change=='columns':s['tables'][0]['columns'].pop()
    if change=='missing':s['tables'].pop()
    if change=='extra':s['tables'].append(dict(s['tables'][0],key='q/ask/0'))
    if change=='duplicate':s['tables'].append(copy.deepcopy(s['tables'][0]))
    if change=='pair':s['tables'][1]['columns'][0]['role']='output'
    with pytest.raises(layout.TableLayoutError,match='q/'):
        layout.layout_problem_tables('q',parts,s)

def test_spanning_headers_preserved_or_explicitly_rejected():
    source='<table><thead><tr><th colspan="2">원래 묶음</th></tr><tr><th>A</th><th>Q</th></tr></thead><tbody><tr><td rowspan="2">0</td><td>1</td></tr><tr><td>0</td></tr></tbody></table>'
    # Existing spanning heading conflicts with a new input/output boundary.
    with pytest.raises(layout.TableLayoutError,match='q/'):
        layout.layout_problem_tables('q',dict(original=source),schema())
    s=schema();s['tables'][0]['boundaries']=[]
    for c in s['tables'][0]['columns']:c['group']='신호';c['role']='input'
    out=layout.layout_problem_tables('q',dict(original=source),s)['original']
    assert nodes(out,'td')[0].attrs['rowspan']=='2'
    assert any(n.attrs.get('colspan')=='2' and n.children==['원래 묶음'] for n in nodes(out,'th'))

def test_no_metadata_keeps_legacy_markup():
    parts=dict(original=table())
    assert layout.layout_problem_tables('q',parts,None)==parts

def test_second_render_is_identical():
    once=layout.layout_problem_tables('q',dict(original=table()),schema())
    assert layout.layout_problem_tables('q',once,schema())==once

def test_md_omits_only_generated_group_row(tmp_path):
    source=layout.layout_problem_tables('q',dict(original=table()),schema())['original']
    path=tmp_path/'note.html';path.write_text('<main>'+source+'</main>')
    md,_=export_document(path)
    assert '입력' not in md and '출력' not in md
    assert '| A | Q |' in md

def test_load_rejects_version_and_duplicates(tmp_path):
    directory=tmp_path/'problem-explanations';directory.mkdir()
    path=directory/'table-layout.json'
    assert layout.load_layouts(tmp_path) is None
    path.write_text(json.dumps(dict(version=9,tables=[])))
    with pytest.raises(layout.TableLayoutError):layout.load_layouts(tmp_path)

def test_paired_buses_equalize_from_shared_values_not_blank_cells():
    s=schema(True)
    for entry in s['tables']:
        for c in entry['columns']:c['kind']='bus'
    result=layout.layout_problem_tables('q',dict(original=table(values=('','')),explanation=table(values=('11111111','1111'))),s)
    widths=[[c.attrs['style'] for c in nodes(result[part],'col')] for part in ['original','explanation']]
    assert widths[0]==widths[1]
    # Different bit lengths keep independent widths; blank cells have no bit length.
    assert widths[0]==['width:6.700rem','width:4.500rem']

def test_semantic_group_headers_have_matching_column_groups():
    result=layout.layout_problem_tables('q',dict(original=table()),schema())['original']
    groups=nodes(result,'colgroup')
    assert len(groups)==2
    assert [len([n for n in g.children if getattr(n,'tag',None)=='col']) for g in groups]==[1,1]

def note_schema():
    s=schema();s['tables'][0]['key']='t-mux/0'
    return s

def test_note_tables_use_topic_keys():
    out=layout.layout_note_tables('t-mux',table(),note_schema())
    assert nodes(out,'table')[0].attrs['data-layout-table']=='t-mux/0'
    assert [n.children for n in nodes(out,'th')[:2]]==[['입력'],['출력']]

def test_note_layout_is_idempotent():
    once=layout.layout_note_tables('t-mux',table(),note_schema())
    assert layout.layout_note_tables('t-mux',once,note_schema())==once

def test_note_layout_none_keeps_fragment():
    assert layout.layout_note_tables('t-mux',table(),None)==table()

@pytest.mark.parametrize('change',['missing','extra','header'])
def test_note_layout_rejects_drift(change):
    s=note_schema();source=table()
    if change=='missing':source+=table()
    if change=='extra':s['tables'].append(dict(s['tables'][0],key='t-mux/1'))
    if change=='header':s['tables'][0]['expected_headers'][0]='X'
    with pytest.raises(layout.TableLayoutError,match='t-mux/'):
        layout.layout_note_tables('t-mux',source,s)

def test_note_and_problem_keys_are_not_interchangeable():
    with pytest.raises(layout.TableLayoutError,match='invalid key'):
        layout.layout_note_tables('t-mux',table(),schema())
    with pytest.raises(layout.TableLayoutError,match='invalid key'):
        layout.layout_problem_tables('q',dict(original=table()),note_schema())

def test_template_layout_rules_apply_to_note_pages():
    from pathlib import Path
    text=Path('.claude/skills/logic-lab-review-pack/assets/note-template.html').read_text(encoding='utf-8')
    block=text[text.index('/* explanation-table-layout:start */'):text.index('/* explanation-table-layout:end */')]
    assert '    .table-card:has(> table[data-layout-table]) { container-type: inline-size; position: relative; }' in block
    assert '    [data-layout-table] td { white-space: nowrap; }' in block
    assert [l.strip() for l in block.splitlines() if '[data-problem-explanation]' in l]==['[data-problem-explanation] .work-board img { display: block; max-width: 100%; height: auto; }']

def test_relayout_with_changed_metadata_matches_fresh_layout():
    old=note_schema()
    new=note_schema();new['tables'][0]['boundaries']=[];new['tables'][0]['columns'][1].update(role='input',group='입력')
    once=layout.layout_note_tables('t-mux',table(),old)
    assert layout.layout_note_tables('t-mux',once,new)==layout.layout_note_tables('t-mux',table(),new)
