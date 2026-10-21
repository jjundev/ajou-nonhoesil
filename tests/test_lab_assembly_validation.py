import json
from PIL import Image
from scripts.lab import assembly
from tests.test_lab_assembly_parser import parsed,TEXT

def test_structure_before_assets(tmp_path):
 n=parsed(tmp_path)
 assert assembly.check_structure(n)==[]
 assert assembly.check_assets(n)
 for s in n.circuits[0].assembly_steps:
  Image.new('RGB',(2,2)).save(tmp_path/s.diagram)
  (tmp_path/s.diagram).with_suffix('.json').write_text(json.dumps({'schema':'breadboard-sidecar/v1'}))
 assert assembly.check_assets(n)==[]
 (tmp_path/'prep2.json').write_text('{bad')
 assert any(f.level=='error' for f in assembly.check_assets(n))

def test_invalid_parent_order_and_duplicate_keys(tmp_path):
 for text in [TEXT.replace('| 1 | 1 |','| 2 | 1 |'),TEXT.replace('| 1 | 2 |','| 1 | 9 |'),
              TEXT.replace('| 1 | 2 |','| 1 | 3 |').replace('| 1 | 3 | U3','| 1 | 2 | U3'),
              TEXT+'\n']:
  n=parsed(tmp_path,text)
  if text==TEXT+'\n': n.circuits[0].stages*=2
  assert any(f.level=='error' for f in assembly.check_structure(n))
