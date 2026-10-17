import pymupdf
from tests.test_review_pack_quiz_flow import publish_quiz_fixture
from scripts.lab.workbook_pdf import export,check_pdf,check_pdf_content


def test_quiz_pdf_counts_and_content(tmp_path):
    dest=publish_quiz_fixture(tmp_path)
    question,_=export(dest,'기출문제',dest);answer,_=export(dest,'기출풀이',dest)
    assert check_pdf(question,11)==[]
    assert check_pdf(answer,11,exact=False)==[]
    assert check_pdf_content(question)==check_pdf_content(answer)==[]
    with pymupdf.open(question) as doc:
        text=''.join(p.get_text() for p in doc)
        assert 'QUIZ_SOLUTION_ONLY_SENTINEL' not in text
        for p in list(doc)[1:]:assert '자체 출제' in p.get_text()
        board=doc[8]
        # One 3:4 blank board, apart from the separate schematic.
        boards=[i for i in board.get_image_info() if abs((i['bbox'][2]-i['bbox'][0])/(i['bbox'][3]-i['bbox'][1])-.75)<.02]
        assert len(boards)==1
    with pymupdf.open(answer) as doc:
        assert 'QUIZ_SOLUTION_ONLY_SENTINEL' in ''.join(p.get_text() for p in doc)
