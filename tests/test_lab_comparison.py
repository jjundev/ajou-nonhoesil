"""Comparison rows must retain the input, expected result and writable actual cell."""
import re
from dataclasses import replace
from pathlib import Path
import pytest
from scripts.lab import render, record, validate, observations, md
from scripts.lab.spec_parser import parse_spec
from scripts.lab.netlist_parser import parse_netlist
from scripts.lab.leds import Led


def comparison(tmp_path):
    text=Path('tests/fixtures/spec_observation_sixbit.md').read_text()
    # Small independent timeline: reset, then D=1 on a falling edge.
    text=text[:text.index('## T1')] + '''## T1 · 비교

- kind: stepped
- encoding: 0/1
- source: manual:p10
- comparison: led
- outputs: [BIT1, BIT2]

| 스텝 | 조작 | D | CLK | BIT1 | BIT2 |
|---|---|---|---|---|---|
| R0 | 초기화 | 0 | 0 | 0 | 0 |
| S1 | 하강 관측 | 1 | 1->0 | 1 | 0 |
'''
    p=tmp_path/'spec.md';p.write_text(text)
    return parse_spec(p)


def rows(html):
    return [re.findall(r'<td[^>]*>(.*?)</td>',r,re.S) for r in re.findall(r'<tr[^>]*>(.*?)</tr>',html,re.S) if '<td' in r]


def test_comparison_has_expected_led_and_blank_actual_on_same_row(tmp_path):
    t=comparison(tmp_path).tables[0]
    leds=[Led('BIT2','a1',True,1),Led('BIT1','a2',False,2)]
    h=render._stepped_html(t,leds=leds)
    r=rows(h)
    assert len(r)==2 and r[1][-1]==''
    assert '1-&gt;0' in r[1][2]
    assert '②BIT1' in r[1][3] and '①BIT2' in r[1][3] # polarity applied
    assert len(r[1])==6
    assert h.count('class="actual"')==2


def test_record_comparison_keeps_expected_separate_from_actual(tmp_path):
    s=comparison(tmp_path); text=record.derive_record(s)
    t=record._tables_by_id(text)['T1']
    assert t.header[-1]=='실제 결과'
    assert t.rows[1][-1]=='' and 'BIT1' in t.rows[1][-3]
    p=tmp_path/'record.md';p.write_text(text.replace('| S1', '| S1'))
    filled=text.replace('filled_by: ~','filled_by: hand')
    p.write_text(filled)
    with pytest.raises(record.RecordExistsError): record.write_record(p,text)


@pytest.mark.parametrize('change', ['empty','missing_output','bad_mode','no_outputs'])
def test_malformed_comparison_is_error(tmp_path,change):
    s=comparison(tmp_path); t=s.tables[0]
    if change=='empty': t.rows[1][-1]=''
    elif change=='missing_output': t.outputs=['MISSING']
    elif change=='no_outputs': t.outputs=[]
    else: t.comparison='mystery'
    assert any(f.level=='error' for f in validate.validate_spec(s))
    with pytest.raises(ValueError): render._stepped_html(t)


def test_inline_observation_keeps_input_expected_and_actual_together():
    t=observations.ObservationTable(['D'],[('Q','U1 pin 3')],
        [observations.ObservationRow(1,'D 입력',['1'],['0'])],
        '0/1','derived','manual:p1','준비','이유',layout='inline')
    h=render._observation_procedure_html(t)
    r=rows(h)
    assert len(r)==1 and len(r[0])==4
    assert 'D = 1' in r[0][1] and 'U1 pin 3' in r[0][2] and ': 0' in r[0][2]
    assert r[0][-1]=='' and 'class="actual"' in h


def test_changed_record_headers_fail_closed(tmp_path):
    p=tmp_path/'record.md'
    old='''---
filled_by: ~
---
### T1 · 이전
| 스텝 | BIT1 |
|---|---|
| S1 | 1 |
'''
    p.write_text(old)
    new=old.replace('BIT1','실제 결과').replace('| S1 | 1 |','| S1 | |')
    with pytest.raises(record.RecordExistsError): record.write_record(p,new)
    assert p.read_text()==old


def test_explicit_old_template_allows_only_empty_migration(tmp_path):
    p=tmp_path/'record.md'
    old='''---
filled_by: ~
---
### T1 · 이전
| 스텝 | BIT1 |
|---|---|
| S1 | |
'''
    new=old.replace('BIT1','실제 결과')
    p.write_text(old)
    assert record.write_record(p,new,previous_template=old)['status']=='regenerated'
    p.write_text(old.replace('| S1 | |','| S1 | 1 |'))
    with pytest.raises(record.RecordExistsError): record.write_record(p,new,previous_template=old)


def test_e07_t1_pattern_and_all_three_timelines_are_consistent():
    s=parse_spec('보고서/실험07/체크리스트/명세.md')
    want=[['000000','000000','100000','010000','101000','110100','011010','001101'],
          ['000000','100000','100000','010000','001000','000100','000010','000001','000000'],
          ['000000','010000','010000','001000','000100','000010','000001','000000']]
    for t, expected in zip(s.tables,want):
        assert t.comparison=='led'
        ix=[t.header.index(f'BIT{i}') for i in range(1,7)]
        assert [''.join(r[i] for i in ix) for r in t.rows]==expected
        assert all(len(r)==len(t.header) for r in t.rows)
    t=s.tables[0]
    assert [r[t.header.index('D')] for r in t.rows[2:]]==list('101100')


def test_e07_all_v_procedures_are_one_comparison_timeline():
    n=parse_netlist('보고서/실험07/결선도/netlist.md')
    s=parse_spec('보고서/실험07/체크리스트/명세.md')
    c=n.circuits[0]
    assert len(c.procedures)==12
    for p,stage in zip(c.procedures,[x for x in c.stages if not x['walk']]):
        assert p.layout=='inline'
        t=observations.stage_observations(c,s,stage,p.observe)
        h=render._observation_procedure_html(t)
        assert len(rows(h))==len(p.steps)
        assert h.count('class="actual"')==len(p.steps)
        assert [r[0] for r in rows(h)]==[str(x.order) for x in p.steps]


def test_inline_led_unknown_is_not_reported_as_off():
    t=observations.ObservationTable(['D'],[('Q','U1 pin 3')],
        [observations.ObservationRow(1,'설정',['1'],['미정'])],
        '0/1','derived','manual:p1','준비','이유',layout='inline')
    h=render._observation_procedure_html(t,[Led('L','a1',False,1)],{'L':'Q'})
    r=rows(h)[0]
    assert r[2]=='없음' and r[3]=='없음' and '미정' in r[4]


@pytest.mark.parametrize('change',['extra_row','short_row','reordered_rows'])
def test_previous_template_migration_preserves_unmatched_measurements(tmp_path,change):
    old='''---
filled_by: ~
---
### T1 · 이전
| 스텝 | 조작 | BIT1 |
|---|---|---|
| S1 | 첫 클럭 | |
| S2 | 다음 클럭 | |
'''
    changed=old
    if change=='extra_row': changed += '| S3 | 추가 관측 | 1 |\n'
    elif change=='short_row': changed=changed.replace('| S2 | 다음 클럭 | |','| S2 | 1 |')
    else: changed=changed.replace('| S1 | 첫 클럭 | |\n| S2 | 다음 클럭 | |', '| S2 | 다음 클럭 | 1 |\n| S1 | 첫 클럭 | |')
    new=old.replace('BIT1','실제 결과')
    p=tmp_path/'record.md';p.write_text(changed)
    with pytest.raises(record.RecordExistsError): record.write_record(p,new,previous_template=old)
    assert p.read_text()==changed


def test_six_bit_record_explains_actual_bit_order():
    text=record.derive_record(parse_spec('보고서/실험07/체크리스트/명세.md'))
    assert 'BIT1→BIT6' in text and '1=켜짐' in text and '0=소등' in text
    assert record.record_marks(text,text)==[]
