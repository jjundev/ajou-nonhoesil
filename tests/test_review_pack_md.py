from pathlib import Path
import pytest
from scripts.lab.review_pack.html2md import convert_pack, check_md

def pages(tmp_path, body):
    a=tmp_path/'실험04_실험설명.html';b=tmp_path/'실험04_기출풀이.html'
    a.write_text('<body><main><article id="t">'+body+'</article></main></body>',encoding='utf-8')
    b.write_text('<body><main><article id="q"><details><summary>풀이</summary><p>저항과 전류를 곱합니다.</p></details></article></main></body>',encoding='utf-8')
    return a,b

def test_hidden_solution_math_links(tmp_path):
    a,b=pages(tmp_path,'<math data-tex="V=IR"><mi>V</mi><mo>=</mo><mi>I</mi><mi>R</mi></math><a href="실험04_기출풀이.html#q">문제</a>')
    outputs,_=convert_pack(a,b)
    assert '저항과 전류를 곱합니다.' in outputs[1].read_text(encoding='utf-8')
    text=outputs[0].read_text(encoding='utf-8')
    from urllib.parse import unquote
    assert '$V=IR$' in text and '실험04_기출풀이.md#q' in unquote(text)
    assert check_md(a,outputs[0])==[]

def test_complement_table_and_static_widget(tmp_path):
    a,b=pages(tmp_path,'<p><span class="ov"><span class="ov">A</span>·B</span></p><table><tr><th>A | B</th></tr><tr><td>0</td></tr></table><div class="controls">조작</div><div class="static-equivalent"><p>대표 출력 0</p></div>')
    outputs,_=convert_pack(a,b);text=outputs[0].read_text(encoding='utf-8')
    assert "((A)'·B)'" in text and 'A \\| B' in text
    assert '조작' not in text and '대표 출력 0' in text

def test_svg_and_spaced_image(tmp_path):
    (tmp_path/'한 글 (1).png').write_bytes(b'png')
    a,b=pages(tmp_path,'<img src="한%20글%20%281%29.png" alt="그림"><svg viewBox="0 0 10 10"><title>상태</title><circle cx="5" cy="5" r="2"/></svg>')
    outputs,n=convert_pack(a,b)
    assert n==1 and check_md(a,outputs[0])==[]
    assert list((tmp_path/'자료/figures').glob('md-*.svg'))

def test_missing_math_fails(tmp_path):
    a,b=pages(tmp_path,'<math><mi>A</mi></math>')
    with pytest.raises(ValueError):convert_pack(a,b)

def test_removed_solution_detected(tmp_path):
    a,b=pages(tmp_path,'<p>필수 내용</p>')
    outputs,_=convert_pack(a,b)
    outputs[1].write_text('',encoding='utf-8')
    assert check_md(b,outputs[1])
def test_held_question_list_item_keeps_anchor(tmp_path):
    from scripts.lab.review_pack.html2md import export_document, check_md
    source = tmp_path / 'held.html'
    source.write_text('<main><ul><li id="q-held">조건이 없어 보류</li></ul></main>', encoding='utf-8')
    markdown, _ = export_document(source)
    source.with_suffix('.md').write_text(markdown, encoding='utf-8')
    assert '<a id="q-held"></a>' in markdown
    assert check_md(source, source.with_suffix('.md')) == []
