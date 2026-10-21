from pathlib import Path
import pytest
from scripts.lab.netlist_parser import parse_netlist, NetlistError
TEXT=(Path(__file__).parent/'fixtures/netlist_assembly_v3.md').read_text()
def parsed(tmp_path,text=TEXT):
 p=tmp_path/'netlist.md'; p.write_text(text); return parse_netlist(p)
def test_parse_six_assembly_rows(tmp_path):
 c=parsed(tmp_path).circuits[0]
 assert [(s.stage_no,s.order) for s in c.assembly_steps]==[(1,i) for i in range(1,7)]
 assert '조립 순서' not in c.body and 'prep1.png' not in c.body
 assert c.stages[0]['stage_no']==1
 assert all(s.line>0 for s in c.assembly_steps)
def test_no_assembly_is_empty_and_v2_rejects_new_table(tmp_path):
 plain=TEXT[:TEXT.index('## 조립 순서')]+TEXT[TEXT.index('## 단계'):]
 for version in ('v2','v3'):
  assert parsed(tmp_path,plain.replace('v3',version)).circuits[0].assembly_steps==[]
 with pytest.raises(NetlistError): parsed(tmp_path,TEXT.replace('v3','v2'))
@pytest.mark.parametrize('text',[
 TEXT.replace('소속 단계','부모'),TEXT.replace('| 1 | 1 |','| 0 | 1 |'),
 TEXT.replace('| 1 | 1 |','| 1 | -1 |'),TEXT.replace('| 전원 |','|  |'),
 TEXT.replace('| prep1.png | 레일 연결 | 극성 대조 |','| prep1.png |'),
 TEXT+TEXT[TEXT.index('## 조립 순서'):TEXT.index('## 단계')],
 TEXT.replace('| 1 | 2 |','| 1 | 1 |'),
 TEXT[:TEXT.index('| 1 | 1 |')]+TEXT[TEXT.index('## 단계'):],
])
def test_bad_headers_empty_cells_duplicate_table_and_numbers(tmp_path,text):
 with pytest.raises(NetlistError): parsed(tmp_path,text)
