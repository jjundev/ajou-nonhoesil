from tests.test_review_pack_explanation_content import setup, FRAGMENT


RECALL = ('<div class="layer formal" data-explanation="recall">'
          '<span class="layer-title">이 문제를 봤을 때 떠올릴 개념과 공식</span>'
          '<p>선택선이라는 단서에서 MUX를 떠올려요. MUX는 선택선으로 입력 하나를 골라요.</p>'
          '<p>Y=SI1+S′I0에서 S는 선택선, I0와 I1은 데이터, Y는 출력이에요. '
          'Enable이 활성인 2×1 MUX라서 이 식을 적용해요.</p></div>')
SUMMARY = '<p data-summary="recall"><strong>핵심 개념:</strong> MUX는 선택선으로 입력 하나를 골라요.</p>'
LEGACY_RECALL = FRAGMENT.split('\n',1)[0]
V1_WITHOUT_RECALL = FRAGMENT.replace(LEGACY_RECALL+'\n','',1)
FRAGMENT_V2 = V1_WITHOUT_RECALL.replace(
    '<div class="layer formal" data-explanation="start">',
    RECALL + '<div class="layer formal" data-explanation="start">',
).replace('<div class="sum" hidden>', '<div class="sum" hidden>' + SUMMARY)


def setup_v2(tmp_path):
    m, root, data = setup(tmp_path)
    m['problem_explanation_version'] = 2
    (root / m['problems'][0]['explanation_fragment']).write_text(FRAGMENT_V2, encoding='utf-8')
    return m, root, data
