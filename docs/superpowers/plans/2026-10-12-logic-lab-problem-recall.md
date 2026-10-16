# 논회실 문제설명 스킬 분리와 핵심 개념 보충 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 논회실 문제설명을 전용 스킬로 분리하면서 전체 학습팩의 네 HTML·네 MD를 유지하고 실험01~06의 86문항에 핵심 개념을 보충한다.

**Architecture:** 새 logic-lab-problem-explain 스킬이 설명 저작·검증 절차를 소유하고 기존 scripts.lab.review_pack 생성기와 로컬 템플릿을 재사용한다. problem_explanation_version=1은 기존 여섯 구역으로 읽으며 새 생성·갱신은 v2의 일곱 구역으로 처리한다. 기존 팩은 explain-stage와 publish를 통해 설명만 교체하고 다른 문서와 자산의 hash를 보존한다.

**Tech Stack:** Python 표준 라이브러리, pytest/pytest-xdist, 기존 Playwright+Chrome, HTML/CSS/KaTeX/Pretendard, Windows PowerShell. 현재 Python 3.14.7에서 pytest 9.1.1과 Playwright import를 확인했다. 스크립트가 hashlib.file_digest를 사용하므로 실행 Python은 3.11 이상이다.

**Spec:** C:/Users/Hyunjun/Desktop/현준대학/26-2/논회실/docs/superpowers/specs/2026-10-12-logic-lab-problem-recall-design.md

## Global Constraints

- 논회실 프로젝트 전용이며 다른 과목용 범용 엔진을 만들지 않는다.
- 기존 Python 표준 라이브러리 생성기를 재사용하며 런타임 의존성을 추가하지 않는다.
- Windows PowerShell에서 저장소 루트를 작업 디렉터리로 사용한다.
- 실행 Python은 3.11 이상이며 기존 hashlib.file_digest 사용 조건을 유지한다.
- 새 해설은 짧고 다정한 '~해요'체로 쓰되 정의·성립 조건·인과를 생략하지 않는다.
- 기존 문항 ID·번호·순서·출처·분류·소문항·답안 상태를 유지한다.
- 기존 실험설명·기출문제·기출풀이 HTML/MD/PDF와 기존 그림·자산·원문·사용자 파일을 보존한다.
- 설명 HTML과 MD는 실험 폴더 루트에, 설명 조각과 검증 기록은 자료/problem-explanations/에 둔다.
- 원문·내용·브라우저 검토는 실제 수행 후에만 기록하고 독립 검토 미실시는 그대로 표시한다.
- 실패한 검증으로 기존 팩을 교체하지 않으며 기존 백업·사용자 파일 충돌 검사·복구 경로를 유지한다.

## Review Focus

1. 기존 여섯 구역의 v1 또는 설명 미활성 팩: 새 v2 검사로 기존 팩을 거부하지 않는다. Task 1의 호환성/미활성 테스트와 Task 2의 v1 build 테스트가 담당한다.
2. 중첩 제목·layer-title·숨긴 문장뿐인 recall: 실제 설명으로 인정하지 않는다. Task 1의 매개변수화 본문 검사 테스트가 담당한다.
3. 구역 중복·잘못된 순서·소문항마다 다른 개념: 구조 오류는 거부하고 서로 다른 개념은 문항별 내용 검토로 확인한다. Task 1의 구역 테스트와 Tasks 4~9의 소문항 감사가 담당한다.
4. 자료가 부족하거나 disputed/unresolved인 문항: 일반 개념과 현재 조건을 구분하고 기존 경고·답안 상태를 유지한다. Task 2의 상태 보존 테스트와 Tasks 4~9의 원문 감사가 담당한다.
5. 설명 변경·발행 실패·사용자 파일이 있는 팩: 이전 설명 승인 재사용을 막고 다른 문서/사용자 파일을 보존한다. Task 2의 재stage/충돌/복구 테스트 및 Tasks 4~9의 보존 hash 검사가 담당한다.

---

## 실행 준비와 파일 구조

이번 계획 작성에서는 구현하지 않았다. 실행 시 using-git-worktrees로 격리 여부를 결정하고 작업 디렉터리를 그 저장소 루트로 둔다. 현재 작업 트리에서는 계획 작성 전 git status가 깨끗했다. 문서 생성 커밋은 이 두 문서만 선택하여 기록하며 사용자의 다른 변경을 stage하지 않는다.

```powershell
python --version
python -c "import pytest, playwright; print(pytest.__version__)"
git status --short
```

pytest.ini는 기본 -n auto이므로 아래 좁은 테스트는 모두 `-n 0`을 쓴다. 브라우저 검사는 기존 `channel='chrome'`을 재사용한다. Python import 또는 Chrome 실행 실패는 실제 원인을 기록하고 requirements-dev.txt/설치된 런타임을 확인한다. 테스트를 통과했다고 기록하지 않는다.

| 파일/영역 | 책임 |
|---|---|
| scripts/lab/review_pack/explanation_content.py | v1/v2 구역과 recall/요약 본문 계약 |
| scripts/lab/review_pack/manifest.py | 버전 수용, 출력 파일명과 필드 검증 |
| scripts/lab/review_pack/explanation_stage.py | 목표 버전 원고 검사, 소유 파일 복사, 검토 초기화 |
| scripts/lab/review_pack/explanation_render.py | 같은 문항/템플릿으로 HTML/MD 렌더 |
| scripts/lab/review_pack/explanation_checks.py | 목표 버전 재렌더 대조·링크·MD 검사 |
| scripts/lab/review_pack/render.py, html2md.py, publish.py, __main__.py | 전체 build/MD/발행/CLI의 v2 연결 |
| .claude/skills/logic-lab-problem-explain/SKILL.md, references/*.md | 설명 전용 실행·저작·형식·검증 지침 |
| .claude/skills/logic-lab-review-pack/SKILL.md, references/*.md | 전체 팩 연결, 문제설명 중복 지침 제거 |
| tests/_explanation_recall_fixture.py | 정상 v2 원고와 manifest fixture |
| tests/test_review_pack_explanation_recall.py | 신규 계약 회귀 |
| tests/test_review_pack_explanation_render.py, stage.py, browser.py, published.py | 조립·보존·화면·발행본 회귀 확장 |
| docs/learning-pack-source/실험01~05/problem-explanations/*.html | 문항별 설명의 저작 원본 |
| docs/learning-pack-source/실험06/explanations.py, recall.py, build_run.py | 실험06 원고 생성원과 신규 recall/버전 |
| docs/learning-pack-source/실험06/problem-explanations/*.html | 실험06 explain-stage 입력용 생성 조각 |
| 복습노트/실험NN/실험NN_문제설명.html/.md, 자료/problem-explanations/, 자료/manifest.json | 발행 문서·원고·검토·버전 |
| docs/verify/logic-lab-problem-recall.md | 86문항 완료 범위·근거·보존·백업 기록 |
| output/validation/problem-recall/ | 실행 시 원본 hash, stage 경로, 브라우저 증거 |

Task 1→2→3 이후 실험별 Tasks 4~9를 진행하고 Task 10에서 전체 회귀와 최종 보고를 한다. 각 실험은 검토한 stage만 발행하여 독립적으로 완성한다. 공용 코드는 한 번 구현한다. 원고에 대한 구현을 흉내 내는 문장별 테스트는 만들지 않는다.

## Task 1: v2 구역·recall·요약 계약, v1 호환성

**Files:**
- Modify: scripts/lab/review_pack/explanation_content.py:8-64, manifest.py:33-60
- Create: tests/_explanation_recall_fixture.py, tests/test_review_pack_explanation_recall.py
- Test: tests/test_review_pack_explanation_content.py

**Interfaces:**
- Consumes: 기존 `Parser`, `Node`, `text(node)`, `validate_fragment(fragment: str, ident: str, state: str) -> None`, `tests.test_review_pack_explanation_content.setup(tmp_path)`.
- Produces: `explanation_sections(version: int) -> tuple[str, ...]`; `validate_fragment(fragment: str, ident: str, state: str, *, version: int = 1) -> None`와 manifest 기반 호출; `setup_v2(tmp_path) -> tuple[dict, Path, dict]`; `FRAGMENT_V2: str`.

- [ ] **Step 1: 정상 원고 fixture와 실패 테스트를 추가한다.** fixture 원고의 실제 내용은 다음과 같다.

```python
# tests/_explanation_recall_fixture.py
from tests.test_review_pack_explanation_content import setup, FRAGMENT

RECALL = ('<div class="layer formal" data-explanation="recall">'
          '<span class="layer-title">이 문제를 봤을 때 떠올릴 개념과 공식</span>'
          '<p>선택선이라는 단서에서 MUX를 떠올려요. MUX는 선택선으로 입력 하나를 골라요.</p>'
          '<p>Y=SI1+S′I0에서 S는 선택선, I0와 I1은 데이터, Y는 출력이에요. '
          'Enable이 활성인 2×1 MUX라서 이 식을 적용해요.</p></div>')
SUMMARY = '<p data-summary="recall"><strong>핵심 개념:</strong> MUX는 선택선으로 입력 하나를 골라요.</p>'
FRAGMENT_V2 = FRAGMENT.replace(
    '<div class="layer formal" data-explanation="start">',
    RECALL+'<div class="layer formal" data-explanation="start">',
).replace('<div class="sum" hidden>', '<div class="sum" hidden>'+SUMMARY)

def setup_v2(tmp_path):
    m, root, data = setup(tmp_path)
    m['problem_explanation_version'] = 2
    (root / m['problems'][0]['explanation_fragment']).write_text(FRAGMENT_V2, encoding='utf-8')
    return m, root, data
```

```python
# tests/test_review_pack_explanation_recall.py
import pytest
from scripts.lab.review_pack.explanation_content import validate_fragment, load_explanations
from scripts.lab.review_pack.manifest import validate_manifest, output_names
from tests.test_review_pack_explanation_content import setup, FRAGMENT
from tests._explanation_recall_fixture import setup_v2, FRAGMENT_V2, RECALL, SUMMARY

def test_v1_and_inactive_manifest_remain_readable(tmp_path):
    m, root, data = setup(tmp_path)
    assert validate_manifest(m) == []
    assert len(load_explanations(m, data, root)) == 1
    del m['problem_explanation_version']; del m['explanation_checks']
    assert validate_manifest(m) == []
    assert 'explanation_html' not in output_names(4)

def test_v2_contract_and_names(tmp_path):
    m, root, data = setup_v2(tmp_path)
    assert validate_manifest(m) == []
    assert len(load_explanations(m, data, root)) == 1
    assert output_names(4, review_presentation_version=2,
                        problem_explanation_version=2)['explanation_html'] == '실험04_문제설명.html'

@pytest.mark.parametrize('body', [
    '<h4>개념</h4>', '<div><h4>개념</h4></div>',
    '<span class="layer-title">개념</span>',
    '<h4>개념</h4><p hidden>숨긴 설명</p>',
    '<h4>개념</h4><div aria-hidden="true">숨긴 설명</div>',
    '<h4>개념</h4><p>&nbsp; </p>',
])
def test_recall_requires_visible_body(body):
    replacement = '<div class="layer formal" data-explanation="recall">'+body+'</div>'
    with pytest.raises(ValueError, match='recall'):
        validate_fragment(FRAGMENT_V2.replace(RECALL, replacement), 'q', 'verified', version=2)

@pytest.mark.parametrize('fragment', [
    FRAGMENT, FRAGMENT_V2+RECALL,
    FRAGMENT_V2.replace(RECALL, '').replace(
        '<div class="layer formal" data-explanation="solve">',
        RECALL+'<div class="layer formal" data-explanation="solve">'),
    FRAGMENT_V2.replace(RECALL, '<div>'+RECALL+'</div>'),
    FRAGMENT_V2+'<div data-explanation="foreign"><p>문장</p></div>',
])
def test_v2_section_coverage_order_and_direct_children(fragment):
    with pytest.raises(ValueError):
        validate_fragment(fragment, 'q', 'verified', version=2)

def test_v2_requires_concept_summary():
    with pytest.raises(ValueError, match='summary'):
        validate_fragment(FRAGMENT_V2.replace(SUMMARY, ''), 'q', 'verified', version=2)

@pytest.mark.parametrize('replacement', [
    '<p data-summary="recall"><strong class="layer-title">개념</strong></p>',
    '<div data-summary="recall"><h4>제목</h4></div>',
    SUMMARY+SUMMARY,
])
def test_v2_concept_summary_needs_one_body(replacement):
    with pytest.raises(ValueError, match='summary'):
        validate_fragment(FRAGMENT_V2.replace(SUMMARY,replacement),'q','verified',version=2)

@pytest.mark.parametrize('version', [0, 3, True, '2'])
def test_unknown_versions_rejected(tmp_path, version):
    m, root, data = setup_v2(tmp_path)
    m['problem_explanation_version'] = version
    assert validate_manifest(m)
```

- [ ] **Step 2: 실패를 확인한다.** `python -m pytest tests/test_review_pack_explanation_recall.py -n 0 -q` → 신규 v2 API/manifest 미지원으로 FAIL. v1 실패는 예상 실패가 아니므로 원인을 조사한다.
- [ ] **Step 3: 버전별 구역과 본문 검사를 구현한다.** explanation_content에 다음 helper를 추가하고 기존 validate_fragment에 keyword version, `required = explanation_sections(version)`을 추가한다. 기존 markup·경고·retry·sum 검사를 보존하며 기존 SECTIONS 참조만 required로 바꾼다.

```python
SECTIONS_BY_VERSION = {
    1: ('understand', 'start', 'solve', 'verify', 'pitfall', 'retry'),
    2: ('understand', 'recall', 'start', 'solve', 'verify', 'pitfall', 'retry'),
}
SECTIONS = SECTIONS_BY_VERSION[1]

def explanation_sections(version: int) -> tuple[str, ...]:
    if type(version) is not int or version not in SECTIONS_BY_VERSION:
        raise ValueError('Unsupported explanation version')
    return SECTIONS_BY_VERSION[version]

def _body_text(node) -> str:
    if isinstance(node, str):
        return node
    if (node.tag in {'h1','h2','h3','h4','h5','h6'}
            or 'layer-title' in node.attrs.get('class','').split()
            or 'hidden' in node.attrs or node.attrs.get('aria-hidden') == 'true'):
        return ''
    return ''.join(_body_text(child) for child in node.children)

def _validate_v2(root, ident: str) -> None:
    all_sections = [n for n in root.walk() if 'data-explanation' in n.attrs]
    direct = [n for n in root.children if isinstance(n, Node) and 'data-explanation' in n.attrs]
    if len(all_sections) != len(direct):
        raise ValueError(ident+': nested explanation section')
    if tuple(n.attrs['data-explanation'] for n in direct) != SECTIONS_BY_VERSION[2]:
        raise ValueError(ident+': explanation section order/coverage')
    for n in direct:
        classes = n.attrs.get('class','').split()
        if 'layer' not in classes:
            raise ValueError(ident+': explanation requires layer')
        if n.attrs['data-explanation'] == 'recall':
            if 'formal' not in classes or not _body_text(n).strip():
                raise ValueError(ident+': recall needs visible concept explanation')
    sums = [n for n in root.children if isinstance(n, Node) and 'sum' in n.attrs.get('class','').split()]
    summary = [n for s in sums for n in s.walk() if n.attrs.get('data-summary') == 'recall']
    if len(summary) != 1 or not _body_text(summary[0]).strip():
        raise ValueError(ident+': summary needs recall body')
```

`Node`는 `.html2md`에서 import한다. `_validate_v2(parser.root, ident)`는 `version == 2`일 때 호출한다. load_explanations는 `version=manifest.get('problem_explanation_version', 1)`을 전달한다. manifest.output_names의 활성 조건을 `in (1,2)`로 바꾸고 validate_manifest는 `type(value) is int and value in (1,2) and modern`만 허용한다. 구조 검사가 의미 검토를 대신하지 않는다는 모듈 주석을 유지한다.

- [ ] **Step 4: 통과를 확인한다.** `python -m pytest tests/test_review_pack_explanation_recall.py tests/test_review_pack_explanation_content.py -n 0 -q` → PASS.
- [ ] **Step 5: 커밋한다.**

```powershell
git add scripts/lab/review_pack/explanation_content.py scripts/lab/review_pack/manifest.py tests/_explanation_recall_fixture.py tests/test_review_pack_explanation_recall.py
git commit -m "feat: add versioned concept recall explanation contract"
```

## Task 2: v2의 전체 build·설명 stage·검사·발행 연결

**Files:**
- Modify: scripts/lab/review_pack/explanation_stage.py, explanation_render.py, explanation_checks.py, render.py, html2md.py, publish.py, __main__.py
- Modify/Test: tests/test_review_pack_explanation_stage.py, tests/test_review_pack_explanation_render.py, tests/test_review_pack_explanation_recall.py, tests/test_review_pack_publish.py

**Interfaces:**
- Consumes: Task 1의 v1/v2 manifest와 setup_v2/FRAGMENT_V2.
- Produces: `prepare_explanation_stage(folder: Path, author_root: Path, stage: Path, *, explanation_version: int = 2) -> Path`; 기존 `write_explanations(manifest, question_data, author_root, folder, assets) -> dict[str,Path]`; 기존 build/check/publish CLI; explain-stage에 `--explanation-version {1,2}`(기본 2).

- [ ] **Step 1: v2 생성·보존·검토 초기화 회귀 테스트를 추가한다.** render 테스트에 다음을 넣는다.

```python
def test_v2_full_build_and_markdown_include_recall(tmp_path):
    from tests._explanation_recall_fixture import setup_v2
    from scripts.lab.review_pack.render import assemble
    from scripts.lab.review_pack.html2md import convert_pack
    from scripts.lab.review_pack.checks import check_pack
    m, run, data = setup_v2(tmp_path)
    stage = tmp_path/'stage'
    paths = assemble(m, run, stage, ASSETS)
    outputs, count = convert_pack(paths['note_html'], paths['review_html'], manifest=m)
    for label in ('실험설명','기출문제','기출풀이','문제설명'):
        for ext in ('html','md'):
            assert (stage/f'실험04_{label}.{ext}').is_file()
    assert paths['explanation_md'] in outputs
    assert '선택선이라는 단서' in paths['explanation_md'].read_text(encoding='utf-8')
    assert '핵심 개념:' in paths['explanation_md'].read_text(encoding='utf-8')
    assert 'data-summary="recall"' in paths['explanation_html'].read_text(encoding='utf-8')
    assert check_pack(stage) == []
```

stage 테스트는 기존 `pack(tmp_path)`, `hashes(folder)`를 사용한다.

```python
def test_v2_stage_preserves_others_and_resets_review(tmp_path):
    import json
    from tests._explanation_recall_fixture import FRAGMENT_V2
    folder, author = pack(tmp_path)
    before = hashes(folder)
    (author/'q-mux-001.html').write_text(FRAGMENT_V2, encoding='utf-8')
    first = prepare_explanation_stage(folder, author, tmp_path/'first')
    m = json.loads((first/'자료/manifest.json').read_text(encoding='utf-8'))
    assert m['problem_explanation_version'] == 2
    assert set(m['explanation_checks'].values()) == {'not_run'}
    assert hashes(folder) == before
    for name, value in before.items():
        if name not in {'자료/manifest.json','사용자메모.md'}:
            assert hashes(first)[name] == value
    m['explanation_checks'] = dict.fromkeys(m['explanation_checks'], 'pass')
    (first/'자료/manifest.json').write_text(json.dumps(m), encoding='utf-8')
    changed = FRAGMENT_V2.replace('선택선이라는 단서', '입력 선택이라는 단서')
    (author/'q-mux-001.html').write_text(changed, encoding='utf-8')
    second = prepare_explanation_stage(first, author, tmp_path/'second')
    newer = json.loads((second/'자료/manifest.json').read_text(encoding='utf-8'))
    assert set(newer['explanation_checks'].values()) == {'not_run'}

def test_v2_invalid_author_does_not_write_stage_or_source(tmp_path):
    folder, author = pack(tmp_path)
    before = hashes(folder)
    with pytest.raises(ValueError):
        prepare_explanation_stage(folder, author, tmp_path/'bad')
    assert not (tmp_path/'bad').exists()
    assert hashes(folder) == before

def test_unreviewed_v2_cannot_publish(tmp_path):
    from tests._explanation_recall_fixture import FRAGMENT_V2
    from scripts.lab.review_pack.publish import publish
    folder, author = pack(tmp_path)
    (author/'q-mux-001.html').write_text(FRAGMENT_V2, encoding='utf-8')
    stage = prepare_explanation_stage(folder, author, tmp_path/'stage')
    with pytest.raises(ValueError, match='문제설명 검토'):
        publish(stage, tmp_path/'복습노트/실험04', tmp_path)
```

기존 정상 v1 stage 테스트의 호출에는 `explanation_version=1`을 명시하여 v1 경로를 계속 검증한다. v2 상태 보존 테스트를 render 파일에 추가한다.

```python
@pytest.mark.parametrize('state,label',[('disputed','답안 충돌'),('unresolved','정답 미확정')])
def test_v2_answer_warning_and_manifest_preserved(tmp_path,state,label):
    from tests._explanation_recall_fixture import setup_v2,FRAGMENT_V2
    m,run,data=setup_v2(tmp_path)
    m['problems'][0]['answer_status']=state
    (run/m['problems'][0]['explanation_fragment']).write_text(
        FRAGMENT_V2.replace('선택선은 데이터가 아니에요.',label+' 조건을 확인해요.'),encoding='utf-8')
    before=deepcopy(m)
    folder=tmp_path/'stage'; folder.mkdir()
    paths=write_explanations(m,data,run,folder,ASSETS)
    assert label in paths['explanation_html'].read_text(encoding='utf-8')
    assert label in paths['explanation_md'].read_text(encoding='utf-8')
    assert m==before
```

CLI 테스트를 stage 파일에 추가한다.

```python
def test_explain_stage_cli_defaults_to_v2_and_allows_v1(tmp_path):
    from scripts.lab.review_pack.__main__ import main
    from tests._explanation_recall_fixture import FRAGMENT_V2
    folder,author=pack(tmp_path)
    (author/'q-mux-001.html').write_text(FRAGMENT_V2,encoding='utf-8')
    stage=tmp_path/'cli'
    assert main(['explain-stage','--folder',str(folder),'--author-root',str(author),
                 '--stage',str(stage)])==0
    assert json.loads((stage/'자료/manifest.json').read_text(encoding='utf-8'))['problem_explanation_version']==2
    variant=tmp_path/'v1'; variant.mkdir()
    folder,author=pack(variant)
    stage=variant/'cli'
    assert main(['explain-stage','--folder',str(folder),'--author-root',str(author),
                 '--stage',str(stage),'--explanation-version','1'])==0
    assert json.loads((stage/'자료/manifest.json').read_text(encoding='utf-8'))['problem_explanation_version']==1
```

- [ ] **Step 2: 실패를 확인한다.** `python -m pytest tests/test_review_pack_explanation_stage.py tests/test_review_pack_explanation_render.py -n 0 -q` → 신규 v2 생성/gate 실패. 기존 카드 테스트는 유지한다.
- [ ] **Step 3: 목표 버전을 검사 전에 지정하고 모든 활성 경로를 연결한다.**

```python
# prepare_explanation_stage 시작부와 manifest load 뒤
def prepare_explanation_stage(folder, author_root, stage, *, explanation_version=2):
    # 기존 경로 겹침·소유 파일·충돌 검사는 유지한다.
    # 아래 줄은 기존 load_manifest 이후, load_explanations 이전에 둔다.
    from .explanation_content import explanation_sections
    explanation_sections(explanation_version)
    m['problem_explanation_version'] = explanation_version
```

위 코드의 함수 선언은 기존 함수를 대체하되 본문을 삭제하지 않는다. names 호출에서 실제 manifest 버전을 전달하고 끝의 `m['problem_explanation_version']=1` 고정 대입을 제거한다. explanation_checks는 기존과 같이 not_run으로 새로 만든다. explanation_render와 explanation_checks는 다음 호출을 사용한다.

```python
names = output_names(manifest['experiment'], review_presentation_version=2,
                     problem_explanation_version=manifest['problem_explanation_version'])
```

render.py, html2md.py, publish.py의 `get('problem_explanation_version') == 1`과 explanation_checks의 역조건을 모두 `(1,2)` 활성 조건으로 바꾼다. html2md의 names 호출에도 실제 버전을 전달한다. publish의 원문·문항·소유권·백업·복구 검사와 required review 기준은 바꾸지 않는다. __main__에서 explain-stage parser와 전달만 확장한다.

```python
p.add_argument('--explanation-version', type=int, choices=(1,2), default=2)
# explain-stage 분기
print(prepare_explanation_stage(args.folder, args.author_root, args.stage,
                               explanation_version=args.explanation_version))
```

- [ ] **Step 4: v2 사용자 충돌과 복구 테스트를 추가한다.** 다음 코드를 tests/test_review_pack_publish.py에 추가한다. 원본 파일을 조작하는 fixture에서 실제 사용자 팩을 사용하지 않는다. 이 단계도 구현 전에 실행하여 FAIL을 확인하고 이후 Step 5에서 통과를 확인한다.

```python
def ready_v2(tmp_path):
    from tests._explanation_recall_fixture import setup_v2
    from scripts.lab.review_pack.render import assemble
    from scripts.lab.review_pack.html2md import convert_pack
    m, run, data = setup_v2(tmp_path)
    for s in m['sources']:
        path = tmp_path/s['path']
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'fixture source')
        s['sha256'] = file_sha256(path)
    m['checks'].update(source_visual='pass',content='self_review',browser='pass')
    m['explanation_checks'].update(source_visual='pass',content='self_review',browser='pass')
    stage = tmp_path/'stage'
    paths = assemble(m,run,stage,Path('.claude/skills/logic-lab-review-pack/assets'))
    convert_pack(paths['note_html'],paths['review_html'],manifest=m)
    m['generated_files'] = sorted(p.relative_to(stage).as_posix() for p in stage.rglob('*') if p.is_file())
    (stage/'자료/manifest.json').write_text(json.dumps(m,ensure_ascii=False),encoding='utf-8')
    dest = tmp_path/'복습노트/실험04'; dest.mkdir(parents=True)
    (dest/'사용자메모.md').write_text('보존',encoding='utf-8')
    return stage,dest

def test_v2_user_explanation_collision_refused(tmp_path):
    stage,dest = ready_v2(tmp_path)
    path = dest/'실험04_문제설명.html'
    path.write_bytes(b'user original')
    with pytest.raises(ValueError,match='User file collision'):
        publish(stage,dest,tmp_path)
    assert path.read_bytes() == b'user original'
    assert (dest/'사용자메모.md').read_text(encoding='utf-8') == '보존'

def test_v2_rename_failure_restores_original(tmp_path):
    stage,dest = ready_v2(tmp_path)
    original = os.replace; calls = []
    def fail_second(a,b):
        calls.append((a,b))
        if len(calls) == 2: raise OSError('test failure')
        return original(a,b)
    with patch('scripts.lab.review_pack.publish.os.replace',side_effect=fail_second):
        with pytest.raises(OSError): publish(stage,dest,tmp_path)
    assert (dest/'사용자메모.md').read_text(encoding='utf-8') == '보존'
    assert not (dest/'실험04_문제설명.html').exists()

def test_v2_user_file_survives_success(tmp_path):
    stage,dest = ready_v2(tmp_path)
    backup = publish(stage,dest,tmp_path)
    assert (backup/'사용자메모.md').read_text(encoding='utf-8') == '보존'
    assert (dest/'사용자메모.md').read_text(encoding='utf-8') == '보존'
    assert (dest/'실험04_문제설명.html').is_file()
```
- [ ] **Step 5: 관련 회귀 통과를 확인한다.**

```powershell
python -m pytest tests/test_review_pack_explanation_recall.py tests/test_review_pack_explanation_content.py tests/test_review_pack_explanation_render.py tests/test_review_pack_explanation_stage.py tests/test_review_pack_checks.py tests/test_review_pack_publish.py tests/test_review_pack_workbook_flow.py -n 0 -q
```

Expected: PASS. `rg -n 'problem_explanation_version' scripts/lab/review_pack`로 v1 전용 조건 잔재를 확인한다. v1을 설명하는 테스트/default는 잔재가 아니다.

- [ ] **Step 6: 해당 파일만 커밋한다.**

```powershell
git add scripts/lab/review_pack/explanation_stage.py scripts/lab/review_pack/explanation_render.py scripts/lab/review_pack/explanation_checks.py scripts/lab/review_pack/render.py scripts/lab/review_pack/html2md.py scripts/lab/review_pack/publish.py scripts/lab/review_pack/__main__.py tests/test_review_pack_explanation_stage.py tests/test_review_pack_explanation_render.py tests/test_review_pack_explanation_recall.py tests/test_review_pack_publish.py
git commit -m "feat: connect concept recall to explanation build and publication"
```

## Task 3: 전용 스킬 분리와 전체 학습팩 연결

**Files:**
- Create: .claude/skills/logic-lab-problem-explain/SKILL.md, references/authoring.md, references/format.md, references/verification.md
- Modify: .claude/skills/logic-lab-review-pack/SKILL.md:10,86,121,132-140; references/authoring.md:42-57, format.md:42-48, verification.md:38-50, workbook.md:46-48

**Interfaces:**
- Consumes: Task 2의 설명 stage CLI(기본 v2), 기존 build/check/publish, 이 설계의 대상 규칙.
- Produces: 같은 에이전트가 독립 호출 또는 전체 학습팩 흐름에서 읽을 설명 전용 스킬. 기존 네 HTML·네 MD 출력은 그대로다.

- [ ] **Step 1: skill-creator 및 writing-great-skills를 읽고 이 저장소 패턴으로 작성한다.** 원고 책임·검토·소유권은 위 설계를 따르고 범용 installer나 새 도구 서버는 만들지 않는다. 아래 frontmatter와 진입 절을 사용한다.

```markdown
---
name: logic-lab-problem-explain
description: 논리회로실험의 기존 학습팩으로 문제의 단서·떠올릴 개념과 공식·첫 줄·풀이 이유·완성 답·검산을 펼친 문제설명 HTML과 MD를 만든다. 문제해설·입문 풀이 설명·핵심 개념 보충 또는 /logic-lab-problem-explain [실험번호|범위|팩경로]에 사용한다. 전체 학습팩에서도 문제설명 저작 단계에 이 스킬을 사용한다.
---

# 논리회로실험 문제설명

이론을 읽었지만 문제풀이 경험이 부족한 학생에게 단서에서 방법을 고르는 과정까지 설명해요. 기존 워크북 v2의 included 문항을 같은 ID·번호·순서로 사용해요. 새 문제·PDF·영상·보고서는 만들지 않아요. 설명은 에이전트가 저작하고 CLI는 조립·검증·발행해요.
```

- [ ] **Step 2: 실행 절을 작성한다.** 번호/범위에는 config.experiment_folder_name 검증을 사용하고 경로는 저장소의 복습노트/실험NN만 수용한다. 인자 없음은 정규식 `실험[0-9]{2}`와 workbook v2 manifest가 있는 디렉터리의 최대 번호로 결정한다. backup suffix/legacy/자료 부족 후보는 기본 대상으로 선택하지 않는다. 없는 팩은 워크북 준비 안내를 한다. 실제 원고 내용을 작성한 뒤 Task 4~9와 같은 explain-stage/check/review/publish 명령을 안내한다. stage 성공만으로 내용 검토 pass를 기록하지 않도록 명시한다.
- [ ] **Step 3: 저작·형식·검증 문서를 작성한다.** authoring은 v2 순서, recall의 다섯 의미 기준, 정성 문항, 서로 다른 소문항 개념, start와의 구분, `<p data-summary="recall">`을 명시한다. format은 v1/v2, canonical path, 별도 explanation_checks, generated_files를 명시한다. verification은 실제 원문/독립 검산/브라우저, 경고 보존, hash 보존, 수정 후 새 stage와 검토 초기화를 명시한다. 아래 예는 문항 원문 대조 후 사용하는 형식 예이며 실제 조건을 대신하지 않는다.

```html
<div class="layer formal" data-explanation="recall">
  <span class="layer-title">이 문제를 봤을 때 떠올릴 개념과 공식</span>
  <p>'입력 하나만 켜진다'는 조건에서 one-hot 입력의 인코더를 떠올려요. 켜진 선의 번호를 이진 코드로 바꿔요.</p>
  <p>A=D2+D3, B=D1+D3에서 A는 상위 비트, B는 하위 비트예요. '+'는 논리 OR를 뜻해요.</p>
  <p>입력 둘 이상이 동시에 켜지면 이 간단한 식이 우선순위를 정해 주지는 않아요. NAND 지정 조건은 드모르간 법칙으로 연결해요.</p>
</div>
```

- [ ] **Step 4: 기존 스킬의 문제설명 전용 절을 연결 지침으로 치환한다.** 전체팩의 대상/출처/문제은행/워크북/저장 규칙은 유지한다. 원고 작성 절에서 `../logic-lab-problem-explain/SKILL.md`를 읽고 같은 실행에서 explanations를 저작하도록 한다. references의 관련 절은 각각 `../../logic-lab-problem-explain/references/authoring.md` 등으로 링크하고 독립 내용을 복제하지 않는다. 신규 manifest는 v2로 지시하며 기존 v1 읽기는 전용 format으로 연결한다. 네 HTML·네 MD와 여덟 링크 보고 규칙을 유지한다.
- [ ] **Step 5: 문서 흐름을 직접 확인한다.** '실험06 학습팩', '실험05 문제설명만', '실험01~06 핵심 개념 보충', 인자 없음, 팩 없음의 다섯 요청을 SKILL.md만 읽어 순서대로 추적한다. 문서 상대 링크의 대상 존재, 최신 팩 선택, 여덟 문서 유지, 기존 source/read-only 경계를 확인한다. 문서 문자열을 그대로 복제하는 테스트는 만들지 않는다. Task 2의 네 HTML/MD 테스트는 이미 통과해야 한다.
- [ ] **Step 6: 커밋한다.**

```powershell
git add .claude/skills/logic-lab-problem-explain .claude/skills/logic-lab-review-pack/SKILL.md .claude/skills/logic-lab-review-pack/references/authoring.md .claude/skills/logic-lab-review-pack/references/format.md .claude/skills/logic-lab-review-pack/references/verification.md .claude/skills/logic-lab-review-pack/references/workbook.md
git commit -m "feat: split logic lab problem explanation skill"
```

## 실험별 작업의 공통 테스트와 검증 도구

Tasks 4~9는 각 실험을 독립 완료한다. 다음 테스트를 Task 4에서 추가하고 Tasks 5~9는 각각 자기 실험 인자를 실패→통과로 검증한다. `audit_experiment`는 기존 tests/test_review_pack_explanation_published.py에 있다.

```python
# tests/test_review_pack_explanation_published.py
@pytest.mark.parametrize('number,expected', [(1,12),(2,14),(3,15),(4,12),(5,19),(6,14)])
def test_recall_published(number, expected):
    from scripts.lab.review_pack.explanation_content import _body_text
    folder = ROOT/'복습노트'/f'실험{number:02d}'
    m = json.loads((folder/'자료/manifest.json').read_text(encoding='utf-8'))
    assert m['problem_explanation_version'] == 2
    result = audit_experiment(number)
    assert result['counts'] == (expected,expected,expected)
    assert result['ids'][0] == result['ids'][1] == result['ids'][2]
    for article in result['articles']:
        sections = [n.attrs['data-explanation'] for n in article.children
                    if hasattr(n,'attrs') and 'data-explanation' in n.attrs]
        assert sections == ['understand','recall','start','solve','verify','pitfall','retry']
        recall = next(n for n in article.walk() if n.attrs.get('data-explanation') == 'recall')
        assert _body_text(recall).strip()
        summary = [n for n in article.walk() if n.attrs.get('data-summary') == 'recall']
        assert len(summary) == 1 and _body_text(summary[0]).strip()
    assert result['subparts_complete']
```

기존 `test_experiment_coverage`의 매개변수 목록에도 (6,14)를 추가한다. 기존 한국어 원고를 그대로 보존한다.

실행 시 docs/verify/logic-lab-problem-recall.md에 다음 열을 실험별로 기록한다: 문항 ID, 단서, 개념/기호, 적용 조건/선택 이유, 소문항 범위, 원문 path/PDF page, 경고 보존, 요약 일치, 검토 결과. 별도 원문/계산 증거와 브라우저 결과를 자료/problem-explanations/검증결과.md에 남긴다. '구조 검사를 통과했다'는 독립 계산 결과가 아니다.

아래 보존 비교 코드는 각 실험 task에 실제 번호로 확장되어 있다. mutable 범위는 설명 HTML/MD, 자료/manifest.json, 자료/problem-explanations/뿐이다. 다른 파일의 변경·삭제·신규 편입은 실패한다. original manifest의 문항/출처/토픽 데이터는 최종 비교에서 동일해야 한다. 기존 원고의 understand/start/solve/verify/pitfall/retry 문자열도 전후 비교하여 핵심 개념 보충 이외의 변경을 검토한다. 기존 경고를 줄이지 않는다.

전체 출처 hash 검사나 원문 일치가 실패하면 해당 팩을 보류한다. 이 계획에서 원문 재추출/정답 상태 변경까지 확장하지 않는다. 성공한 다른 실험은 독립 발행한다.


## Task 4: 실험01 12문항의 핵심 개념 보충과 검토 발행

**Files:**
- Modify: docs/learning-pack-source/실험01/problem-explanations/q-tt3-4row.html
- Modify: docs/learning-pack-source/실험01/problem-explanations/q-tt3-8row.html
- Modify: docs/learning-pack-source/실험01/problem-explanations/q-xor2-tt.html
- Modify: docs/learning-pack-source/실험01/problem-explanations/q-xor-graded.html
- Modify: docs/learning-pack-source/실험01/problem-explanations/q-switching.html
- Modify: docs/learning-pack-source/실험01/problem-explanations/q-demorgan.html
- Modify: docs/learning-pack-source/실험01/problem-explanations/q-deq.html
- Modify: docs/learning-pack-source/실험01/problem-explanations/q-logicdiagram.html
- Modify: docs/learning-pack-source/실험01/problem-explanations/q-nand-xor.html
- Modify: docs/learning-pack-source/실험01/problem-explanations/q-nand3.html
- Modify: docs/learning-pack-source/실험01/problem-explanations/q-nor3-or-inv.html
- Modify: docs/learning-pack-source/실험01/problem-explanations/q-cmos-nand3.html
- Modify: docs/learning-pack-source/실험01/problem-explanations/검증결과.md (실험06은 새 저작 기록을 생성)
- Modify: 복습노트/실험01/실험01_문제설명.html, 복습노트/실험01/실험01_문제설명.md, 복습노트/실험01/자료/manifest.json
- Modify: 복습노트/실험01/자료/problem-explanations/의 위 12개 원고와 검증결과.md
- Modify/Test: tests/test_review_pack_explanation_published.py
- Modify: docs/verify/logic-lab-problem-recall.md

**Interfaces:**
- Consumes: Task 2의 prepare_explanation_stage(..., explanation_version=2), check/publish CLI; Task 3의 전용 저작·검증 규칙; 기존 실험01의 manifest와 문제지 payload.
- Produces: 같은 included 12문항의 v2 원고/HTML/MD, 실제 검토 기록, 원본 보존 hash와 백업 경로. 문제/풀이 payload·답안 상태는 그대로다.

- [ ] **Step 1: 이 실험의 실패를 확인한다.** Task 4에서는 앞 절의 공통 test_recall_published 코드를 먼저 추가한다. 이후 각 실험은 아래 한 케이스를 실행한다.

```powershell
python -m pytest "tests/test_review_pack_explanation_published.py::test_recall_published[1-12]" -n 0 -q
```

Expected: 현재 발행 manifest가 v1이라 FAIL. 다른 실험의 아직 보충하지 않은 케이스는 이 단계에서 통과할 필요가 없다.

- [ ] **Step 2: 설명 밖의 모든 파일과 manifest를 snapshot한다.** 다음 코드는 원본을 수정하지 않으며 출력 폴더의 baseline이 이미 있으면 실패한다.

```powershell
@'
from pathlib import Path
import hashlib, json
folder=Path('복습노트/실험01')
out=Path('output/validation/problem-recall')
out.mkdir(parents=True,exist_ok=True)
baseline=out/'baseline-01.json'
if baseline.exists(): raise SystemExit('Baseline already exists; keep the recorded original')
mutable={'실험01_문제설명.html','실험01_문제설명.md','자료/manifest.json'}
hashes={}
for path in folder.rglob('*'):
    if not path.is_file(): continue
    rel=path.relative_to(folder).as_posix()
    if rel in mutable or rel.startswith('자료/problem-explanations/'): continue
    hashes[rel]=hashlib.sha256(path.read_bytes()).hexdigest()
m=json.loads((folder/'자료/manifest.json').read_text(encoding='utf-8'))
baseline.write_text(json.dumps({'files':hashes,'manifest':m},ensure_ascii=False,indent=2),encoding='utf-8')
'@ | python -
```

- [ ] **Step 3: 이 실험의 included ID와 표를 읽고 각 문항의 원문·토픽·기존 start/solve/verify를 대조한다.** 아래 관점은 저작 범위이며 미확인 원문 조건을 추측하는 근거가 아니다. 식·극성·임계값은 실제 원문 페이지로 확인한다.

| 문항 ID | recall에서 연결할 단서·개념·조건 |
|---|---|
| q-tt3-4row | 입력 조합과 진리표, A·B·C와 출력의 뜻; 원문에 지정된 네 행만 판독 |
| q-tt3-8row | 3입력의 2³=8 조합, 게이트별 출력 규칙과 비트 순서 |
| q-xor2-tt | XOR는 입력이 다를 때 1, 두 입력의 네 조합과 출력 |
| q-xor-graded | XOR 기호·진리표·A′B+AB′의 같은 의미와 보수 기호 |
| q-switching | 부울대수의 +/곱/보수, 항등·멱등·흡수와 적용되는 항 |
| q-demorgan | 곱의 보수와 합의 보수, 보수할 변수와 AND/OR 교환 |
| q-deq | 회로 중간 노드부터 식 세우기, 출력 버블의 보수; 답안 충돌 유지 |
| q-logicdiagram | 부울식의 연산 우선순위와 게이트 연결, 괄호별 중간 노드 |
| q-nand-xor | NAND의 보수 출력과 XOR의 서로 다른 입력 조건, NAND만 사용 |
| q-nand3 | 3입력 NAND의 출력 조건과 AND 뒤 최종 반전의 위치 |
| q-nor3-or-inv | 3입력 NOR의 출력 조건과 OR 뒤 반전 |
| q-cmos-nand3 | PMOS/NMOS 켜짐 조건, NAND의 직렬 pull-down/병렬 pull-up |

원문 참조는 아래 코드로 manifest의 문제·토픽별 출처를 출력한다. PDF 회로·표를 읽을 때 pdf 스킬을 사용하고 실제 페이지를 렌더링하여 판독한다. 텍스트 추출만으로 버블/엣지/표의 머리를 확정하지 않는다.

```powershell
@'
from pathlib import Path
import json
m=json.loads(Path('복습노트/실험01/자료/manifest.json').read_text(encoding='utf-8'))
sources={s['id']:s for s in m['sources']}; topics={t['id']:t for t in m['topics']}
for p in m['problems']:
    if p['status']!='included': continue
    refs=p['sources']+[r for tid in p['topics'] for r in topics[tid]['sources']]
    print(p['id'],[(sources[r['source_id']]['path'],r.get('pdf_page')) for r in refs])
'@ | python -
```

- [ ] **Step 4: q-tt3-4row의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: 입력 조합과 진리표, A·B·C와 출력의 뜻; 원문에 지정된 네 행만 판독. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 5: q-tt3-4row 한 문항의 recall과 요약을 저작한다.** 위 Files의 해당 HTML에서 understand 다음에 recall을 삽입하고 기존 직계 sum에 data-summary=recall 문단을 추가한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 6: q-tt3-8row의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: 3입력의 2³=8 조합, 게이트별 출력 규칙과 비트 순서. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 7: q-tt3-8row 한 문항의 recall과 요약을 저작한다.** 위 Files의 해당 HTML에서 understand 다음에 recall을 삽입하고 기존 직계 sum에 data-summary=recall 문단을 추가한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 8: q-xor2-tt의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: XOR는 입력이 다를 때 1, 두 입력의 네 조합과 출력. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 9: q-xor2-tt 한 문항의 recall과 요약을 저작한다.** 위 Files의 해당 HTML에서 understand 다음에 recall을 삽입하고 기존 직계 sum에 data-summary=recall 문단을 추가한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 10: q-xor-graded의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: XOR 기호·진리표·A′B+AB′의 같은 의미와 보수 기호. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 11: q-xor-graded 한 문항의 recall과 요약을 저작한다.** 위 Files의 해당 HTML에서 understand 다음에 recall을 삽입하고 기존 직계 sum에 data-summary=recall 문단을 추가한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 12: q-switching의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: 부울대수의 +/곱/보수, 항등·멱등·흡수와 적용되는 항. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 13: q-switching 한 문항의 recall과 요약을 저작한다.** 위 Files의 해당 HTML에서 understand 다음에 recall을 삽입하고 기존 직계 sum에 data-summary=recall 문단을 추가한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 14: q-demorgan의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: 곱의 보수와 합의 보수, 보수할 변수와 AND/OR 교환. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 15: q-demorgan 한 문항의 recall과 요약을 저작한다.** 위 Files의 해당 HTML에서 understand 다음에 recall을 삽입하고 기존 직계 sum에 data-summary=recall 문단을 추가한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 16: q-deq의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: 회로 중간 노드부터 식 세우기, 출력 버블의 보수; 답안 충돌 유지. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 17: q-deq 한 문항의 recall과 요약을 저작한다.** 위 Files의 해당 HTML에서 understand 다음에 recall을 삽입하고 기존 직계 sum에 data-summary=recall 문단을 추가한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 18: q-logicdiagram의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: 부울식의 연산 우선순위와 게이트 연결, 괄호별 중간 노드. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 19: q-logicdiagram 한 문항의 recall과 요약을 저작한다.** 위 Files의 해당 HTML에서 understand 다음에 recall을 삽입하고 기존 직계 sum에 data-summary=recall 문단을 추가한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 20: q-nand-xor의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: NAND의 보수 출력과 XOR의 서로 다른 입력 조건, NAND만 사용. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 21: q-nand-xor 한 문항의 recall과 요약을 저작한다.** 위 Files의 해당 HTML에서 understand 다음에 recall을 삽입하고 기존 직계 sum에 data-summary=recall 문단을 추가한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 22: q-nand3의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: 3입력 NAND의 출력 조건과 AND 뒤 최종 반전의 위치. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 23: q-nand3 한 문항의 recall과 요약을 저작한다.** 위 Files의 해당 HTML에서 understand 다음에 recall을 삽입하고 기존 직계 sum에 data-summary=recall 문단을 추가한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 24: q-nor3-or-inv의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: 3입력 NOR의 출력 조건과 OR 뒤 반전. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 25: q-nor3-or-inv 한 문항의 recall과 요약을 저작한다.** 위 Files의 해당 HTML에서 understand 다음에 recall을 삽입하고 기존 직계 sum에 data-summary=recall 문단을 추가한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 26: q-cmos-nand3의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: PMOS/NMOS 켜짐 조건, NAND의 직렬 pull-down/병렬 pull-up. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 27: q-cmos-nand3 한 문항의 recall과 요약을 저작한다.** 위 Files의 해당 HTML에서 understand 다음에 recall을 삽입하고 기존 직계 sum에 data-summary=recall 문단을 추가한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 28: 원고·요약을 한 문항씩 재검토하고 기록을 갱신한다.** 각 ID의 단서/개념/기호/조건/선택 이유/모든 소문항/요약 일치/원문 page/경고 보존을 기록한다. 기존 source_visual/content/browser 문구를 복사하지 않고 실제 확인한 결과를 쓴다. 검증 기록에는 실제 독립 검산·검토자와 결과를 기재한다.

- [ ] **Step 29: 새 고유 stage를 만들고 기계 검사를 수행한다.** 출력 stage 경로를 파일로 기록하여 이후 명령이 같은 stage를 사용한다.

```powershell
$recallStage01=Join-Path 'tmp/review-pack' ('recall-01-'+[guid]::NewGuid().ToString('N'))
python -m scripts.lab.review_pack explain-stage --folder '복습노트/실험01' --author-root 'docs/learning-pack-source/실험01/problem-explanations' --stage $recallStage01 --explanation-version 2
if ($LASTEXITCODE -ne 0) { throw 'explain-stage failed' }
Set-Content -LiteralPath 'output/validation/problem-recall/stage-01.txt' -Value $recallStage01 -Encoding utf8
python -m scripts.lab.review_pack check --folder $recallStage01
if ($LASTEXITCODE -ne 0) { throw 'check failed' }
```

Expected: 새 stage 경로와 OK (mechanical checks only). 실패하면 원고를 수정하고 새 stage를 만든다. 기존 stage를 덮어쓰지 않는다.

- [ ] **Step 30: stage에서 12문항의 브라우저·원문·내용을 실제 검토한다.** 375×900/1280×900 × light/dark의 각 문항 hash로 이동하여 recall을 읽고 우측 요약을 열어 본문과 대조한다. pageerror·KaTeX error·깨진 그림·문서 가로 넘침은 0, 긴 수식/표는 카드 내부 스크롤, JS 비활성에서는 전체 풀이가 읽혀야 한다. 관련 화면/측정/근거를 검증결과.md에 남긴다. 새 결과에 대한 content=pass 또는 self_review, source_visual=pass, browser=pass, independent=실제 상태만 manifest에 기록한다. 문구 수정 후에는 다시 새 stage를 만들고 관련 검토를 수행한다.

- [ ] **Step 31: 검토 기록을 stage와 저작 원본에 보존하고 소유 목록을 동기화한다.** 다음 코드는 검사 합격을 자동 부여하지 않는다. 실제 기록 작성 후 파일을 동기화한다.

```powershell
@'
from pathlib import Path
import json, shutil
stage=Path(Path('output/validation/problem-recall/stage-01.txt').read_text(encoding='utf-8-sig').strip())
report=Path('docs/learning-pack-source/실험01/problem-explanations/검증결과.md')
shutil.copy2(report,stage/'자료/problem-explanations/검증결과.md')
p=stage/'자료/manifest.json'; m=json.loads(p.read_text(encoding='utf-8'))
m['generated_files']=sorted(f.relative_to(stage).as_posix() for f in stage.rglob('*') if f.is_file())
p.write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8')
'@ | python -
```

- [ ] **Step 32: stage의 다른 파일 및 문항·출처·토픽이 원본과 같은지 확인한다.**

```powershell
@'
from pathlib import Path
import json,hashlib
stage=Path(Path('output/validation/problem-recall/stage-01.txt').read_text(encoding='utf-8-sig').strip())
baseline=json.loads(Path('output/validation/problem-recall/baseline-01.json').read_text(encoding='utf-8'))
old=baseline['manifest']; new=json.loads((stage/'자료/manifest.json').read_text(encoding='utf-8'))
for key in ('experiment','sources','topics','problems','checks','review_presentation_version','note_presentation_version'):
    assert old.get(key)==new.get(key), key
for rel,digest in baseline['files'].items():
    path=stage/rel
    # 사용자 파일은 stage에 복사하지 않고 publish가 보존한다. 원본 generated_files로 구분한다.
    if rel not in old.get('generated_files',[]): continue
    assert path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest()==digest, rel
assert new['problem_explanation_version']==2
assert new['explanation_checks']['source_visual']=='pass'
assert new['explanation_checks']['content'] in {'pass','self_review'}
assert new['explanation_checks']['browser']=='pass'
print('preservation and reviews checked')
'@ | python -
```

- [ ] **Step 33: 이 실험을 검증 후 발행한다.**

```powershell
$recallStage01=Get-Content -LiteralPath 'output/validation/problem-recall/stage-01.txt' -Raw
$recallStage01=$recallStage01.Trim()
python -m scripts.lab.review_pack check --folder $recallStage01
if ($LASTEXITCODE -ne 0) { throw 'final stage check failed' }
python -m scripts.lab.review_pack publish --root . --stage $recallStage01 --experiment 1
if ($LASTEXITCODE -ne 0) { throw 'publication failed' }
python -m scripts.lab.review_pack check --folder '복습노트/실험01'
if ($LASTEXITCODE -ne 0) { throw 'published check failed' }
python -m pytest "tests/test_review_pack_explanation_published.py::test_recall_published[1-12]" -n 0 -q
```

Expected: publish 출력에 백업 경로, pack check OK, 12문항 recall 테스트 PASS. 백업 경로를 docs/verify/logic-lab-problem-recall.md에 기록한다. 발행 후 baseline의 모든 파일(사용자 파일 포함)이 같은 hash인지 비교하고 기존 소유 목록 밖의 신규 파일은 mutable 범위 외에 없는지 확인한다.

- [ ] **Step 34: 실험01 관련 원고·발행 문서·검증 기록만 커밋한다.** 테스트에서는 전체 6실험 매개변수 목록을 한 번만 추가한다. 아직 미완성인 다른 실험은 이 커밋의 완료 대상으로 표시하지 않는다.

```powershell
git add 'docs/learning-pack-source/실험01/problem-explanations' '복습노트/실험01/실험01_문제설명.html' '복습노트/실험01/실험01_문제설명.md' '복습노트/실험01/자료/problem-explanations' '복습노트/실험01/자료/manifest.json' docs/verify/logic-lab-problem-recall.md tests/test_review_pack_explanation_published.py
git commit -m "docs: add concept recall to lab 01 explanations"
```


## Task 5: 실험02 14문항의 핵심 개념 보충과 검토 발행

**Files:**
- Modify: docs/learning-pack-source/실험02/problem-explanations/q-region.html
- Modify: docs/learning-pack-source/실험02/problem-explanations/q-params-4.html
- Modify: docs/learning-pack-source/실험02/problem-explanations/q-params-2017.html
- Modify: docs/learning-pack-source/실험02/problem-explanations/q-params-2016.html
- Modify: docs/learning-pack-source/실험02/problem-explanations/q-schmitt-noise.html
- Modify: docs/learning-pack-source/실험02/problem-explanations/q-schmitt-waveform.html
- Modify: docs/learning-pack-source/실험02/problem-explanations/q-rprn-effect.html
- Modify: docs/learning-pack-source/실험02/problem-explanations/q-rp-derive.html
- Modify: docs/learning-pack-source/실험02/problem-explanations/q-rp-derive-current.html
- Modify: docs/learning-pack-source/실험02/problem-explanations/q-rn-derive.html
- Modify: docs/learning-pack-source/실험02/problem-explanations/q-prop-delay.html
- Modify: docs/learning-pack-source/실험02/problem-explanations/q-delay-transition.html
- Modify: docs/learning-pack-source/실험02/problem-explanations/q-transition.html
- Modify: docs/learning-pack-source/실험02/problem-explanations/q-speed.html
- Modify: docs/learning-pack-source/실험02/problem-explanations/검증결과.md (실험06은 새 저작 기록을 생성)
- Modify: 복습노트/실험02/실험02_문제설명.html, 복습노트/실험02/실험02_문제설명.md, 복습노트/실험02/자료/manifest.json
- Modify: 복습노트/실험02/자료/problem-explanations/의 위 14개 원고와 검증결과.md
- Modify/Test: tests/test_review_pack_explanation_published.py
- Modify: docs/verify/logic-lab-problem-recall.md

**Interfaces:**
- Consumes: Task 2의 prepare_explanation_stage(..., explanation_version=2), check/publish CLI; Task 3의 전용 저작·검증 규칙; 기존 실험02의 manifest와 문제지 payload.
- Produces: 같은 included 14문항의 v2 원고/HTML/MD, 실제 검토 기록, 원본 보존 hash와 백업 경로. 문제/풀이 payload·답안 상태는 그대로다.

- [ ] **Step 1: 이 실험의 실패를 확인한다.** Task 4에서는 앞 절의 공통 test_recall_published 코드를 먼저 추가한다. 이후 각 실험은 아래 한 케이스를 실행한다.

```powershell
python -m pytest "tests/test_review_pack_explanation_published.py::test_recall_published[2-14]" -n 0 -q
```

Expected: 현재 발행 manifest가 v1이라 FAIL. 다른 실험의 아직 보충하지 않은 케이스는 이 단계에서 통과할 필요가 없다.

- [ ] **Step 2: 설명 밖의 모든 파일과 manifest를 snapshot한다.** 다음 코드는 원본을 수정하지 않으며 출력 폴더의 baseline이 이미 있으면 실패한다.

```powershell
@'
from pathlib import Path
import hashlib, json
folder=Path('복습노트/실험02')
out=Path('output/validation/problem-recall')
out.mkdir(parents=True,exist_ok=True)
baseline=out/'baseline-02.json'
if baseline.exists(): raise SystemExit('Baseline already exists; keep the recorded original')
mutable={'실험02_문제설명.html','실험02_문제설명.md','자료/manifest.json'}
hashes={}
for path in folder.rglob('*'):
    if not path.is_file(): continue
    rel=path.relative_to(folder).as_posix()
    if rel in mutable or rel.startswith('자료/problem-explanations/'): continue
    hashes[rel]=hashlib.sha256(path.read_bytes()).hexdigest()
m=json.loads((folder/'자료/manifest.json').read_text(encoding='utf-8'))
baseline.write_text(json.dumps({'files':hashes,'manifest':m},ensure_ascii=False,indent=2),encoding='utf-8')
'@ | python -
```

- [ ] **Step 3: 이 실험의 included ID와 표를 읽고 각 문항의 원문·토픽·기존 start/solve/verify를 대조한다.** 아래 관점은 저작 범위이며 미확인 원문 조건을 추측하는 근거가 아니다. 식·극성·임계값은 실제 원문 페이지로 확인한다.

| 문항 ID | recall에서 연결할 단서·개념·조건 |
|---|---|
| q-region | VILmax/VIHmin/VOLmax/VOHmin과 입력·출력 보증 구간; 충돌 표시 유지 |
| q-params-4 | 네 임계값의 입력/출력 구분과 min/max의 보증 의미 |
| q-params-2017 | VOHmin은 출력 High 최소값, VILmax는 입력 Low 최대값과 단위 |
| q-params-2016 | VIHmin은 입력 High 최소값, VOLmax는 출력 Low 최대값과 단위 |
| q-schmitt-noise | 상승/하강 임계값과 hysteresis, 임계 부근 잡음과 상태 기억 |
| q-schmitt-waveform | 같은 입력 파형에 상승/하강 임계값 적용, 이전 출력 상태 |
| q-rprn-effect | 등가 on 저항, 출력 부하 전류와 전압 강하의 관계 |
| q-rp-derive | High 출력의 PMOS 경로와 ΔV/|I|, 전류 부호·단위 |
| q-rp-derive-current | 입력 Low의 PMOS 도통, High 출력 전류 방향과 전압 차 |
| q-rn-derive | 입력 High의 NMOS 도통, Low 출력 VOL/IOL의 조건 |
| q-prop-delay | 부하 용량 충·방전과 입력/출력 기준점 사이의 지연 |
| q-delay-transition | tPLH/tPHL과 tr/tf의 측정 기준 차이; 정답 미확정 유지 |
| q-transition | 상승/하강의 다른 전류 경로·등가 저항·부하; 정답 미확정 유지 |
| q-speed | 지연·천이 시간을 구분하고 실제 교안 용어 대조; 정답 미확정 유지 |

원문 참조는 아래 코드로 manifest의 문제·토픽별 출처를 출력한다. PDF 회로·표를 읽을 때 pdf 스킬을 사용하고 실제 페이지를 렌더링하여 판독한다. 텍스트 추출만으로 버블/엣지/표의 머리를 확정하지 않는다.

```powershell
@'
from pathlib import Path
import json
m=json.loads(Path('복습노트/실험02/자료/manifest.json').read_text(encoding='utf-8'))
sources={s['id']:s for s in m['sources']}; topics={t['id']:t for t in m['topics']}
for p in m['problems']:
    if p['status']!='included': continue
    refs=p['sources']+[r for tid in p['topics'] for r in topics[tid]['sources']]
    print(p['id'],[(sources[r['source_id']]['path'],r.get('pdf_page')) for r in refs])
'@ | python -
```

- [ ] **Step 4: q-region의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: VILmax/VIHmin/VOLmax/VOHmin과 입력·출력 보증 구간; 충돌 표시 유지. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 5: q-region 한 문항의 recall과 요약을 저작한다.** 위 Files의 해당 HTML에서 understand 다음에 recall을 삽입하고 기존 직계 sum에 data-summary=recall 문단을 추가한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 6: q-params-4의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: 네 임계값의 입력/출력 구분과 min/max의 보증 의미. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 7: q-params-4 한 문항의 recall과 요약을 저작한다.** 위 Files의 해당 HTML에서 understand 다음에 recall을 삽입하고 기존 직계 sum에 data-summary=recall 문단을 추가한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 8: q-params-2017의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: VOHmin은 출력 High 최소값, VILmax는 입력 Low 최대값과 단위. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 9: q-params-2017 한 문항의 recall과 요약을 저작한다.** 위 Files의 해당 HTML에서 understand 다음에 recall을 삽입하고 기존 직계 sum에 data-summary=recall 문단을 추가한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 10: q-params-2016의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: VIHmin은 입력 High 최소값, VOLmax는 출력 Low 최대값과 단위. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 11: q-params-2016 한 문항의 recall과 요약을 저작한다.** 위 Files의 해당 HTML에서 understand 다음에 recall을 삽입하고 기존 직계 sum에 data-summary=recall 문단을 추가한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 12: q-schmitt-noise의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: 상승/하강 임계값과 hysteresis, 임계 부근 잡음과 상태 기억. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 13: q-schmitt-noise 한 문항의 recall과 요약을 저작한다.** 위 Files의 해당 HTML에서 understand 다음에 recall을 삽입하고 기존 직계 sum에 data-summary=recall 문단을 추가한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 14: q-schmitt-waveform의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: 같은 입력 파형에 상승/하강 임계값 적용, 이전 출력 상태. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 15: q-schmitt-waveform 한 문항의 recall과 요약을 저작한다.** 위 Files의 해당 HTML에서 understand 다음에 recall을 삽입하고 기존 직계 sum에 data-summary=recall 문단을 추가한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 16: q-rprn-effect의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: 등가 on 저항, 출력 부하 전류와 전압 강하의 관계. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 17: q-rprn-effect 한 문항의 recall과 요약을 저작한다.** 위 Files의 해당 HTML에서 understand 다음에 recall을 삽입하고 기존 직계 sum에 data-summary=recall 문단을 추가한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 18: q-rp-derive의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: High 출력의 PMOS 경로와 ΔV/|I|, 전류 부호·단위. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 19: q-rp-derive 한 문항의 recall과 요약을 저작한다.** 위 Files의 해당 HTML에서 understand 다음에 recall을 삽입하고 기존 직계 sum에 data-summary=recall 문단을 추가한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 20: q-rp-derive-current의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: 입력 Low의 PMOS 도통, High 출력 전류 방향과 전압 차. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 21: q-rp-derive-current 한 문항의 recall과 요약을 저작한다.** 위 Files의 해당 HTML에서 understand 다음에 recall을 삽입하고 기존 직계 sum에 data-summary=recall 문단을 추가한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 22: q-rn-derive의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: 입력 High의 NMOS 도통, Low 출력 VOL/IOL의 조건. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 23: q-rn-derive 한 문항의 recall과 요약을 저작한다.** 위 Files의 해당 HTML에서 understand 다음에 recall을 삽입하고 기존 직계 sum에 data-summary=recall 문단을 추가한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 24: q-prop-delay의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: 부하 용량 충·방전과 입력/출력 기준점 사이의 지연. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 25: q-prop-delay 한 문항의 recall과 요약을 저작한다.** 위 Files의 해당 HTML에서 understand 다음에 recall을 삽입하고 기존 직계 sum에 data-summary=recall 문단을 추가한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 26: q-delay-transition의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: tPLH/tPHL과 tr/tf의 측정 기준 차이; 정답 미확정 유지. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 27: q-delay-transition 한 문항의 recall과 요약을 저작한다.** 위 Files의 해당 HTML에서 understand 다음에 recall을 삽입하고 기존 직계 sum에 data-summary=recall 문단을 추가한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 28: q-transition의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: 상승/하강의 다른 전류 경로·등가 저항·부하; 정답 미확정 유지. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 29: q-transition 한 문항의 recall과 요약을 저작한다.** 위 Files의 해당 HTML에서 understand 다음에 recall을 삽입하고 기존 직계 sum에 data-summary=recall 문단을 추가한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 30: q-speed의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: 지연·천이 시간을 구분하고 실제 교안 용어 대조; 정답 미확정 유지. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 31: q-speed 한 문항의 recall과 요약을 저작한다.** 위 Files의 해당 HTML에서 understand 다음에 recall을 삽입하고 기존 직계 sum에 data-summary=recall 문단을 추가한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 32: 원고·요약을 한 문항씩 재검토하고 기록을 갱신한다.** 각 ID의 단서/개념/기호/조건/선택 이유/모든 소문항/요약 일치/원문 page/경고 보존을 기록한다. 기존 source_visual/content/browser 문구를 복사하지 않고 실제 확인한 결과를 쓴다. 검증 기록에는 실제 독립 검산·검토자와 결과를 기재한다.

- [ ] **Step 33: 새 고유 stage를 만들고 기계 검사를 수행한다.** 출력 stage 경로를 파일로 기록하여 이후 명령이 같은 stage를 사용한다.

```powershell
$recallStage02=Join-Path 'tmp/review-pack' ('recall-02-'+[guid]::NewGuid().ToString('N'))
python -m scripts.lab.review_pack explain-stage --folder '복습노트/실험02' --author-root 'docs/learning-pack-source/실험02/problem-explanations' --stage $recallStage02 --explanation-version 2
if ($LASTEXITCODE -ne 0) { throw 'explain-stage failed' }
Set-Content -LiteralPath 'output/validation/problem-recall/stage-02.txt' -Value $recallStage02 -Encoding utf8
python -m scripts.lab.review_pack check --folder $recallStage02
if ($LASTEXITCODE -ne 0) { throw 'check failed' }
```

Expected: 새 stage 경로와 OK (mechanical checks only). 실패하면 원고를 수정하고 새 stage를 만든다. 기존 stage를 덮어쓰지 않는다.

- [ ] **Step 34: stage에서 14문항의 브라우저·원문·내용을 실제 검토한다.** 375×900/1280×900 × light/dark의 각 문항 hash로 이동하여 recall을 읽고 우측 요약을 열어 본문과 대조한다. pageerror·KaTeX error·깨진 그림·문서 가로 넘침은 0, 긴 수식/표는 카드 내부 스크롤, JS 비활성에서는 전체 풀이가 읽혀야 한다. 관련 화면/측정/근거를 검증결과.md에 남긴다. 새 결과에 대한 content=pass 또는 self_review, source_visual=pass, browser=pass, independent=실제 상태만 manifest에 기록한다. 문구 수정 후에는 다시 새 stage를 만들고 관련 검토를 수행한다.

- [ ] **Step 35: 검토 기록을 stage와 저작 원본에 보존하고 소유 목록을 동기화한다.** 다음 코드는 검사 합격을 자동 부여하지 않는다. 실제 기록 작성 후 파일을 동기화한다.

```powershell
@'
from pathlib import Path
import json, shutil
stage=Path(Path('output/validation/problem-recall/stage-02.txt').read_text(encoding='utf-8-sig').strip())
report=Path('docs/learning-pack-source/실험02/problem-explanations/검증결과.md')
shutil.copy2(report,stage/'자료/problem-explanations/검증결과.md')
p=stage/'자료/manifest.json'; m=json.loads(p.read_text(encoding='utf-8'))
m['generated_files']=sorted(f.relative_to(stage).as_posix() for f in stage.rglob('*') if f.is_file())
p.write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8')
'@ | python -
```

- [ ] **Step 36: stage의 다른 파일 및 문항·출처·토픽이 원본과 같은지 확인한다.**

```powershell
@'
from pathlib import Path
import json,hashlib
stage=Path(Path('output/validation/problem-recall/stage-02.txt').read_text(encoding='utf-8-sig').strip())
baseline=json.loads(Path('output/validation/problem-recall/baseline-02.json').read_text(encoding='utf-8'))
old=baseline['manifest']; new=json.loads((stage/'자료/manifest.json').read_text(encoding='utf-8'))
for key in ('experiment','sources','topics','problems','checks','review_presentation_version','note_presentation_version'):
    assert old.get(key)==new.get(key), key
for rel,digest in baseline['files'].items():
    path=stage/rel
    # 사용자 파일은 stage에 복사하지 않고 publish가 보존한다. 원본 generated_files로 구분한다.
    if rel not in old.get('generated_files',[]): continue
    assert path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest()==digest, rel
assert new['problem_explanation_version']==2
assert new['explanation_checks']['source_visual']=='pass'
assert new['explanation_checks']['content'] in {'pass','self_review'}
assert new['explanation_checks']['browser']=='pass'
print('preservation and reviews checked')
'@ | python -
```

- [ ] **Step 37: 이 실험을 검증 후 발행한다.**

```powershell
$recallStage02=Get-Content -LiteralPath 'output/validation/problem-recall/stage-02.txt' -Raw
$recallStage02=$recallStage02.Trim()
python -m scripts.lab.review_pack check --folder $recallStage02
if ($LASTEXITCODE -ne 0) { throw 'final stage check failed' }
python -m scripts.lab.review_pack publish --root . --stage $recallStage02 --experiment 2
if ($LASTEXITCODE -ne 0) { throw 'publication failed' }
python -m scripts.lab.review_pack check --folder '복습노트/실험02'
if ($LASTEXITCODE -ne 0) { throw 'published check failed' }
python -m pytest "tests/test_review_pack_explanation_published.py::test_recall_published[2-14]" -n 0 -q
```

Expected: publish 출력에 백업 경로, pack check OK, 14문항 recall 테스트 PASS. 백업 경로를 docs/verify/logic-lab-problem-recall.md에 기록한다. 발행 후 baseline의 모든 파일(사용자 파일 포함)이 같은 hash인지 비교하고 기존 소유 목록 밖의 신규 파일은 mutable 범위 외에 없는지 확인한다.

- [ ] **Step 38: 실험02 관련 원고·발행 문서·검증 기록만 커밋한다.** 테스트에서는 전체 6실험 매개변수 목록을 한 번만 추가한다. 아직 미완성인 다른 실험은 이 커밋의 완료 대상으로 표시하지 않는다.

```powershell
git add 'docs/learning-pack-source/실험02/problem-explanations' '복습노트/실험02/실험02_문제설명.html' '복습노트/실험02/실험02_문제설명.md' '복습노트/실험02/자료/problem-explanations' '복습노트/실험02/자료/manifest.json' docs/verify/logic-lab-problem-recall.md tests/test_review_pack_explanation_published.py
git commit -m "docs: add concept recall to lab 02 explanations"
```


## Task 6: 실험03 15문항의 핵심 개념 보충과 검토 발행

**Files:**
- Modify: docs/learning-pack-source/실험03/problem-explanations/q-ha-table.html
- Modify: docs/learning-pack-source/실험03/problem-explanations/q-ha-design-eq.html
- Modify: docs/learning-pack-source/실험03/problem-explanations/q-ha-design-ic.html
- Modify: docs/learning-pack-source/실험03/problem-explanations/q-cs-roles.html
- Modify: docs/learning-pack-source/실험03/problem-explanations/q-ha-lsb.html
- Modify: docs/learning-pack-source/실험03/problem-explanations/q-adder-diff.html
- Modify: docs/learning-pack-source/실험03/problem-explanations/q-fa-table.html
- Modify: docs/learning-pack-source/실험03/problem-explanations/q-fa-design.html
- Modify: docs/learning-pack-source/실험03/problem-explanations/q-hs-bool.html
- Modify: docs/learning-pack-source/실험03/problem-explanations/q-hs-circuit.html
- Modify: docs/learning-pack-source/실험03/problem-explanations/q-sub-diff.html
- Modify: docs/learning-pack-source/실험03/problem-explanations/q-fs-table.html
- Modify: docs/learning-pack-source/실험03/problem-explanations/q-fs-equation.html
- Modify: docs/learning-pack-source/실험03/problem-explanations/q-fs-roles.html
- Modify: docs/learning-pack-source/실험03/problem-explanations/q-cs-roles-sub.html
- Modify: docs/learning-pack-source/실험03/problem-explanations/검증결과.md (실험06은 새 저작 기록을 생성)
- Modify: 복습노트/실험03/실험03_문제설명.html, 복습노트/실험03/실험03_문제설명.md, 복습노트/실험03/자료/manifest.json
- Modify: 복습노트/실험03/자료/problem-explanations/의 위 15개 원고와 검증결과.md
- Modify/Test: tests/test_review_pack_explanation_published.py
- Modify: docs/verify/logic-lab-problem-recall.md

**Interfaces:**
- Consumes: Task 2의 prepare_explanation_stage(..., explanation_version=2), check/publish CLI; Task 3의 전용 저작·검증 규칙; 기존 실험03의 manifest와 문제지 payload.
- Produces: 같은 included 15문항의 v2 원고/HTML/MD, 실제 검토 기록, 원본 보존 hash와 백업 경로. 문제/풀이 payload·답안 상태는 그대로다.

- [ ] **Step 1: 이 실험의 실패를 확인한다.** Task 4에서는 앞 절의 공통 test_recall_published 코드를 먼저 추가한다. 이후 각 실험은 아래 한 케이스를 실행한다.

```powershell
python -m pytest "tests/test_review_pack_explanation_published.py::test_recall_published[3-15]" -n 0 -q
```

Expected: 현재 발행 manifest가 v1이라 FAIL. 다른 실험의 아직 보충하지 않은 케이스는 이 단계에서 통과할 필요가 없다.

- [ ] **Step 2: 설명 밖의 모든 파일과 manifest를 snapshot한다.** 다음 코드는 원본을 수정하지 않으며 출력 폴더의 baseline이 이미 있으면 실패한다.

```powershell
@'
from pathlib import Path
import hashlib, json
folder=Path('복습노트/실험03')
out=Path('output/validation/problem-recall')
out.mkdir(parents=True,exist_ok=True)
baseline=out/'baseline-03.json'
if baseline.exists(): raise SystemExit('Baseline already exists; keep the recorded original')
mutable={'실험03_문제설명.html','실험03_문제설명.md','자료/manifest.json'}
hashes={}
for path in folder.rglob('*'):
    if not path.is_file(): continue
    rel=path.relative_to(folder).as_posix()
    if rel in mutable or rel.startswith('자료/problem-explanations/'): continue
    hashes[rel]=hashlib.sha256(path.read_bytes()).hexdigest()
m=json.loads((folder/'자료/manifest.json').read_text(encoding='utf-8'))
baseline.write_text(json.dumps({'files':hashes,'manifest':m},ensure_ascii=False,indent=2),encoding='utf-8')
'@ | python -
```

- [ ] **Step 3: 이 실험의 included ID와 표를 읽고 각 문항의 원문·토픽·기존 start/solve/verify를 대조한다.** 아래 관점은 저작 범위이며 미확인 원문 조건을 추측하는 근거가 아니다. 식·극성·임계값은 실제 원문 페이지로 확인한다.

| 문항 ID | recall에서 연결할 단서·개념·조건 |
|---|---|
| q-ha-table | 반가산기의 A+B=2C+S, S는 XOR, C는 AND |
| q-ha-design-eq | 주어진 식의 S/C 출력 의미와 XOR/AND의 대응 |
| q-ha-design-ic | 7486 XOR/7408 AND 역할, pinout은 원문 데이터시트 대조 |
| q-cs-roles | 합 비트 S와 자리올림 C, 반가산기와 전가산기의 입력 차이 |
| q-ha-lsb | 최하위 자리의 carry-in 부재와 이후 자리의 carry 전달 |
| q-adder-diff | 두 입력과 carry-in 포함 세 입력의 차이 |
| q-fa-table | A+B+Ci=2Co+S, parity 합과 두 개 이상 1일 때 carry |
| q-fa-design | S=A XOR B XOR Ci와 Co=AB+Ci(A XOR B); 원문 식 번호 충돌 유지 |
| q-hs-bool | 반감산기의 D=A XOR B와 borrow=A′B; 피감수/감수 순서 |
| q-hs-circuit | XOR와 A 반전 뒤 AND로 difference/borrow 구현 |
| q-sub-diff | borrow-in을 받는 전감산기와 두 입력 반감산기의 차이 |
| q-fs-table | A−B−Bi=D−2Bo, 이전 borrow와 두 단계 감산의 입력 순서 |
| q-fs-equation | 회로 중간 difference/borrow에서 최종 D/Bo 유도 |
| q-fs-roles | 차 D와 빌림 B의 수치 의미; 원문의 답안 충돌 유지 |
| q-cs-roles-sub | 감산기의 D/B와 가산기의 C/S 구분; 원문 표기 불일치·미확정 유지 |

원문 참조는 아래 코드로 manifest의 문제·토픽별 출처를 출력한다. PDF 회로·표를 읽을 때 pdf 스킬을 사용하고 실제 페이지를 렌더링하여 판독한다. 텍스트 추출만으로 버블/엣지/표의 머리를 확정하지 않는다.

```powershell
@'
from pathlib import Path
import json
m=json.loads(Path('복습노트/실험03/자료/manifest.json').read_text(encoding='utf-8'))
sources={s['id']:s for s in m['sources']}; topics={t['id']:t for t in m['topics']}
for p in m['problems']:
    if p['status']!='included': continue
    refs=p['sources']+[r for tid in p['topics'] for r in topics[tid]['sources']]
    print(p['id'],[(sources[r['source_id']]['path'],r.get('pdf_page')) for r in refs])
'@ | python -
```

- [ ] **Step 4: q-ha-table의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: 반가산기의 A+B=2C+S, S는 XOR, C는 AND. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 5: q-ha-table 한 문항의 recall과 요약을 저작한다.** 위 Files의 해당 HTML에서 understand 다음에 recall을 삽입하고 기존 직계 sum에 data-summary=recall 문단을 추가한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 6: q-ha-design-eq의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: 주어진 식의 S/C 출력 의미와 XOR/AND의 대응. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 7: q-ha-design-eq 한 문항의 recall과 요약을 저작한다.** 위 Files의 해당 HTML에서 understand 다음에 recall을 삽입하고 기존 직계 sum에 data-summary=recall 문단을 추가한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 8: q-ha-design-ic의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: 7486 XOR/7408 AND 역할, pinout은 원문 데이터시트 대조. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 9: q-ha-design-ic 한 문항의 recall과 요약을 저작한다.** 위 Files의 해당 HTML에서 understand 다음에 recall을 삽입하고 기존 직계 sum에 data-summary=recall 문단을 추가한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 10: q-cs-roles의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: 합 비트 S와 자리올림 C, 반가산기와 전가산기의 입력 차이. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 11: q-cs-roles 한 문항의 recall과 요약을 저작한다.** 위 Files의 해당 HTML에서 understand 다음에 recall을 삽입하고 기존 직계 sum에 data-summary=recall 문단을 추가한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 12: q-ha-lsb의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: 최하위 자리의 carry-in 부재와 이후 자리의 carry 전달. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 13: q-ha-lsb 한 문항의 recall과 요약을 저작한다.** 위 Files의 해당 HTML에서 understand 다음에 recall을 삽입하고 기존 직계 sum에 data-summary=recall 문단을 추가한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 14: q-adder-diff의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: 두 입력과 carry-in 포함 세 입력의 차이. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 15: q-adder-diff 한 문항의 recall과 요약을 저작한다.** 위 Files의 해당 HTML에서 understand 다음에 recall을 삽입하고 기존 직계 sum에 data-summary=recall 문단을 추가한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 16: q-fa-table의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: A+B+Ci=2Co+S, parity 합과 두 개 이상 1일 때 carry. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 17: q-fa-table 한 문항의 recall과 요약을 저작한다.** 위 Files의 해당 HTML에서 understand 다음에 recall을 삽입하고 기존 직계 sum에 data-summary=recall 문단을 추가한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 18: q-fa-design의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: S=A XOR B XOR Ci와 Co=AB+Ci(A XOR B); 원문 식 번호 충돌 유지. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 19: q-fa-design 한 문항의 recall과 요약을 저작한다.** 위 Files의 해당 HTML에서 understand 다음에 recall을 삽입하고 기존 직계 sum에 data-summary=recall 문단을 추가한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 20: q-hs-bool의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: 반감산기의 D=A XOR B와 borrow=A′B; 피감수/감수 순서. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 21: q-hs-bool 한 문항의 recall과 요약을 저작한다.** 위 Files의 해당 HTML에서 understand 다음에 recall을 삽입하고 기존 직계 sum에 data-summary=recall 문단을 추가한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 22: q-hs-circuit의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: XOR와 A 반전 뒤 AND로 difference/borrow 구현. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 23: q-hs-circuit 한 문항의 recall과 요약을 저작한다.** 위 Files의 해당 HTML에서 understand 다음에 recall을 삽입하고 기존 직계 sum에 data-summary=recall 문단을 추가한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 24: q-sub-diff의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: borrow-in을 받는 전감산기와 두 입력 반감산기의 차이. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 25: q-sub-diff 한 문항의 recall과 요약을 저작한다.** 위 Files의 해당 HTML에서 understand 다음에 recall을 삽입하고 기존 직계 sum에 data-summary=recall 문단을 추가한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 26: q-fs-table의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: A−B−Bi=D−2Bo, 이전 borrow와 두 단계 감산의 입력 순서. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 27: q-fs-table 한 문항의 recall과 요약을 저작한다.** 위 Files의 해당 HTML에서 understand 다음에 recall을 삽입하고 기존 직계 sum에 data-summary=recall 문단을 추가한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 28: q-fs-equation의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: 회로 중간 difference/borrow에서 최종 D/Bo 유도. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 29: q-fs-equation 한 문항의 recall과 요약을 저작한다.** 위 Files의 해당 HTML에서 understand 다음에 recall을 삽입하고 기존 직계 sum에 data-summary=recall 문단을 추가한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 30: q-fs-roles의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: 차 D와 빌림 B의 수치 의미; 원문의 답안 충돌 유지. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 31: q-fs-roles 한 문항의 recall과 요약을 저작한다.** 위 Files의 해당 HTML에서 understand 다음에 recall을 삽입하고 기존 직계 sum에 data-summary=recall 문단을 추가한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 32: q-cs-roles-sub의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: 감산기의 D/B와 가산기의 C/S 구분; 원문 표기 불일치·미확정 유지. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 33: q-cs-roles-sub 한 문항의 recall과 요약을 저작한다.** 위 Files의 해당 HTML에서 understand 다음에 recall을 삽입하고 기존 직계 sum에 data-summary=recall 문단을 추가한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 34: 원고·요약을 한 문항씩 재검토하고 기록을 갱신한다.** 각 ID의 단서/개념/기호/조건/선택 이유/모든 소문항/요약 일치/원문 page/경고 보존을 기록한다. 기존 source_visual/content/browser 문구를 복사하지 않고 실제 확인한 결과를 쓴다. 검증 기록에는 실제 독립 검산·검토자와 결과를 기재한다.

- [ ] **Step 35: 새 고유 stage를 만들고 기계 검사를 수행한다.** 출력 stage 경로를 파일로 기록하여 이후 명령이 같은 stage를 사용한다.

```powershell
$recallStage03=Join-Path 'tmp/review-pack' ('recall-03-'+[guid]::NewGuid().ToString('N'))
python -m scripts.lab.review_pack explain-stage --folder '복습노트/실험03' --author-root 'docs/learning-pack-source/실험03/problem-explanations' --stage $recallStage03 --explanation-version 2
if ($LASTEXITCODE -ne 0) { throw 'explain-stage failed' }
Set-Content -LiteralPath 'output/validation/problem-recall/stage-03.txt' -Value $recallStage03 -Encoding utf8
python -m scripts.lab.review_pack check --folder $recallStage03
if ($LASTEXITCODE -ne 0) { throw 'check failed' }
```

Expected: 새 stage 경로와 OK (mechanical checks only). 실패하면 원고를 수정하고 새 stage를 만든다. 기존 stage를 덮어쓰지 않는다.

- [ ] **Step 36: stage에서 15문항의 브라우저·원문·내용을 실제 검토한다.** 375×900/1280×900 × light/dark의 각 문항 hash로 이동하여 recall을 읽고 우측 요약을 열어 본문과 대조한다. pageerror·KaTeX error·깨진 그림·문서 가로 넘침은 0, 긴 수식/표는 카드 내부 스크롤, JS 비활성에서는 전체 풀이가 읽혀야 한다. 관련 화면/측정/근거를 검증결과.md에 남긴다. 새 결과에 대한 content=pass 또는 self_review, source_visual=pass, browser=pass, independent=실제 상태만 manifest에 기록한다. 문구 수정 후에는 다시 새 stage를 만들고 관련 검토를 수행한다.

- [ ] **Step 37: 검토 기록을 stage와 저작 원본에 보존하고 소유 목록을 동기화한다.** 다음 코드는 검사 합격을 자동 부여하지 않는다. 실제 기록 작성 후 파일을 동기화한다.

```powershell
@'
from pathlib import Path
import json, shutil
stage=Path(Path('output/validation/problem-recall/stage-03.txt').read_text(encoding='utf-8-sig').strip())
report=Path('docs/learning-pack-source/실험03/problem-explanations/검증결과.md')
shutil.copy2(report,stage/'자료/problem-explanations/검증결과.md')
p=stage/'자료/manifest.json'; m=json.loads(p.read_text(encoding='utf-8'))
m['generated_files']=sorted(f.relative_to(stage).as_posix() for f in stage.rglob('*') if f.is_file())
p.write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8')
'@ | python -
```

- [ ] **Step 38: stage의 다른 파일 및 문항·출처·토픽이 원본과 같은지 확인한다.**

```powershell
@'
from pathlib import Path
import json,hashlib
stage=Path(Path('output/validation/problem-recall/stage-03.txt').read_text(encoding='utf-8-sig').strip())
baseline=json.loads(Path('output/validation/problem-recall/baseline-03.json').read_text(encoding='utf-8'))
old=baseline['manifest']; new=json.loads((stage/'자료/manifest.json').read_text(encoding='utf-8'))
for key in ('experiment','sources','topics','problems','checks','review_presentation_version','note_presentation_version'):
    assert old.get(key)==new.get(key), key
for rel,digest in baseline['files'].items():
    path=stage/rel
    # 사용자 파일은 stage에 복사하지 않고 publish가 보존한다. 원본 generated_files로 구분한다.
    if rel not in old.get('generated_files',[]): continue
    assert path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest()==digest, rel
assert new['problem_explanation_version']==2
assert new['explanation_checks']['source_visual']=='pass'
assert new['explanation_checks']['content'] in {'pass','self_review'}
assert new['explanation_checks']['browser']=='pass'
print('preservation and reviews checked')
'@ | python -
```

- [ ] **Step 39: 이 실험을 검증 후 발행한다.**

```powershell
$recallStage03=Get-Content -LiteralPath 'output/validation/problem-recall/stage-03.txt' -Raw
$recallStage03=$recallStage03.Trim()
python -m scripts.lab.review_pack check --folder $recallStage03
if ($LASTEXITCODE -ne 0) { throw 'final stage check failed' }
python -m scripts.lab.review_pack publish --root . --stage $recallStage03 --experiment 3
if ($LASTEXITCODE -ne 0) { throw 'publication failed' }
python -m scripts.lab.review_pack check --folder '복습노트/실험03'
if ($LASTEXITCODE -ne 0) { throw 'published check failed' }
python -m pytest "tests/test_review_pack_explanation_published.py::test_recall_published[3-15]" -n 0 -q
```

Expected: publish 출력에 백업 경로, pack check OK, 15문항 recall 테스트 PASS. 백업 경로를 docs/verify/logic-lab-problem-recall.md에 기록한다. 발행 후 baseline의 모든 파일(사용자 파일 포함)이 같은 hash인지 비교하고 기존 소유 목록 밖의 신규 파일은 mutable 범위 외에 없는지 확인한다.

- [ ] **Step 40: 실험03 관련 원고·발행 문서·검증 기록만 커밋한다.** 테스트에서는 전체 6실험 매개변수 목록을 한 번만 추가한다. 아직 미완성인 다른 실험은 이 커밋의 완료 대상으로 표시하지 않는다.

```powershell
git add 'docs/learning-pack-source/실험03/problem-explanations' '복습노트/실험03/실험03_문제설명.html' '복습노트/실험03/실험03_문제설명.md' '복습노트/실험03/자료/problem-explanations' '복습노트/실험03/자료/manifest.json' docs/verify/logic-lab-problem-recall.md tests/test_review_pack_explanation_published.py
git commit -m "docs: add concept recall to lab 03 explanations"
```


## Task 7: 실험04 12문항의 핵심 개념 보충과 검토 발행

**Files:**
- Modify: docs/learning-pack-source/실험04/problem-explanations/q-mux2.html
- Modify: docs/learning-pack-source/실험04/problem-explanations/q-mux4.html
- Modify: docs/learning-pack-source/실험04/problem-explanations/q-demux2.html
- Modify: docs/learning-pack-source/실험04/problem-explanations/q-design4.html
- Modify: docs/learning-pack-source/실험04/problem-explanations/q-decoder.html
- Modify: docs/learning-pack-source/실험04/problem-explanations/q-tri.html
- Modify: docs/learning-pack-source/실험04/problem-explanations/q-muxdef.html
- Modify: docs/learning-pack-source/실험04/problem-explanations/q-demuxdef.html
- Modify: docs/learning-pack-source/실험04/problem-explanations/q-difference.html
- Modify: docs/learning-pack-source/실험04/problem-explanations/q-demux4.html
- Modify: docs/learning-pack-source/실험04/problem-explanations/q-mux2-graded.html
- Modify: docs/learning-pack-source/실험04/problem-explanations/q-active-general.html
- Modify: docs/learning-pack-source/실험04/problem-explanations/검증결과.md (실험06은 새 저작 기록을 생성)
- Modify: 복습노트/실험04/실험04_문제설명.html, 복습노트/실험04/실험04_문제설명.md, 복습노트/실험04/자료/manifest.json
- Modify: 복습노트/실험04/자료/problem-explanations/의 위 12개 원고와 검증결과.md
- Modify/Test: tests/test_review_pack_explanation_published.py
- Modify: docs/verify/logic-lab-problem-recall.md
- Modify: docs/learning-pack-source/실험04/manifest.json (기존 원고의 problem_explanation_version만 2로 변경)

**Interfaces:**
- Consumes: Task 2의 prepare_explanation_stage(..., explanation_version=2), check/publish CLI; Task 3의 전용 저작·검증 규칙; 기존 실험04의 manifest와 문제지 payload.
- Produces: 같은 included 12문항의 v2 원고/HTML/MD, 실제 검토 기록, 원본 보존 hash와 백업 경로. 문제/풀이 payload·답안 상태는 그대로다.

- [ ] **Step 1: 이 실험의 실패를 확인한다.** Task 4에서는 앞 절의 공통 test_recall_published 코드를 먼저 추가한다. 이후 각 실험은 아래 한 케이스를 실행한다.

```powershell
python -m pytest "tests/test_review_pack_explanation_published.py::test_recall_published[4-12]" -n 0 -q
```

Expected: 현재 발행 manifest가 v1이라 FAIL. 다른 실험의 아직 보충하지 않은 케이스는 이 단계에서 통과할 필요가 없다.

- [ ] **Step 2: 설명 밖의 모든 파일과 manifest를 snapshot한다.** 다음 코드는 원본을 수정하지 않으며 출력 폴더의 baseline이 이미 있으면 실패한다.

```powershell
@'
from pathlib import Path
import hashlib, json
folder=Path('복습노트/실험04')
out=Path('output/validation/problem-recall')
out.mkdir(parents=True,exist_ok=True)
baseline=out/'baseline-04.json'
if baseline.exists(): raise SystemExit('Baseline already exists; keep the recorded original')
mutable={'실험04_문제설명.html','실험04_문제설명.md','자료/manifest.json'}
hashes={}
for path in folder.rglob('*'):
    if not path.is_file(): continue
    rel=path.relative_to(folder).as_posix()
    if rel in mutable or rel.startswith('자료/problem-explanations/'): continue
    hashes[rel]=hashlib.sha256(path.read_bytes()).hexdigest()
m=json.loads((folder/'자료/manifest.json').read_text(encoding='utf-8'))
baseline.write_text(json.dumps({'files':hashes,'manifest':m},ensure_ascii=False,indent=2),encoding='utf-8')
'@ | python -
```

- [ ] **Step 3: 이 실험의 included ID와 표를 읽고 각 문항의 원문·토픽·기존 start/solve/verify를 대조한다.** 아래 관점은 저작 범위이며 미확인 원문 조건을 추측하는 근거가 아니다. 식·극성·임계값은 실제 원문 페이지로 확인한다.

| 문항 ID | recall에서 연결할 단서·개념·조건 |
|---|---|
| q-mux2 | 선택선과 데이터, Y=S′I0+SI1의 선택 조건 |
| q-mux4 | 두 선택 비트의 입력 번호와 Enable 극성, 비활성 출력 조건 |
| q-demux2 | 한 데이터 입력의 선택된 출력 분배, Y0=DS′/Y1=DS |
| q-design4 | 4×1의 네 minterm 선택 경로와 지정 게이트 제약 |
| q-decoder | binary-to-one-hot 해독, MUX는 선택/DMUX는 분배 |
| q-tri | High-Z는 논리 0과 다름, active-low enable과 버스 충돌; disputed 유지 |
| q-muxdef | 여러 입력 중 하나를 선택하는 MUX 정의와 선택선 역할 |
| q-demuxdef | 한 입력을 선택 출력으로 보내는 DMUX 정의; 기출 미확인 표시 유지 |
| q-difference | 입력→출력 개수와 선택선 역할 비교; 기출 미확인 표시 유지 |
| q-demux4 | 선택 비트→출력 번호와 출력 극성; disputed·기출 미확인 유지 |
| q-mux2-graded | 2×1 선택 식을 지정된 네 행에만 적용, 채점 행 순서 보존 |
| q-active-general | 활성은 기능 실행의 의미, High/Low와 출력값의 구분 |

원문 참조는 아래 코드로 manifest의 문제·토픽별 출처를 출력한다. PDF 회로·표를 읽을 때 pdf 스킬을 사용하고 실제 페이지를 렌더링하여 판독한다. 텍스트 추출만으로 버블/엣지/표의 머리를 확정하지 않는다.

```powershell
@'
from pathlib import Path
import json
m=json.loads(Path('복습노트/실험04/자료/manifest.json').read_text(encoding='utf-8'))
sources={s['id']:s for s in m['sources']}; topics={t['id']:t for t in m['topics']}
for p in m['problems']:
    if p['status']!='included': continue
    refs=p['sources']+[r for tid in p['topics'] for r in topics[tid]['sources']]
    print(p['id'],[(sources[r['source_id']]['path'],r.get('pdf_page')) for r in refs])
'@ | python -
```

- [ ] **Step 4: q-mux2의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: 선택선과 데이터, Y=S′I0+SI1의 선택 조건. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 5: q-mux2 한 문항의 recall과 요약을 저작한다.** 위 Files의 해당 HTML에서 understand 다음에 recall을 삽입하고 기존 직계 sum에 data-summary=recall 문단을 추가한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 6: q-mux4의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: 두 선택 비트의 입력 번호와 Enable 극성, 비활성 출력 조건. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 7: q-mux4 한 문항의 recall과 요약을 저작한다.** 위 Files의 해당 HTML에서 understand 다음에 recall을 삽입하고 기존 직계 sum에 data-summary=recall 문단을 추가한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 8: q-demux2의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: 한 데이터 입력의 선택된 출력 분배, Y0=DS′/Y1=DS. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 9: q-demux2 한 문항의 recall과 요약을 저작한다.** 위 Files의 해당 HTML에서 understand 다음에 recall을 삽입하고 기존 직계 sum에 data-summary=recall 문단을 추가한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 10: q-design4의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: 4×1의 네 minterm 선택 경로와 지정 게이트 제약. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 11: q-design4 한 문항의 recall과 요약을 저작한다.** 위 Files의 해당 HTML에서 understand 다음에 recall을 삽입하고 기존 직계 sum에 data-summary=recall 문단을 추가한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 12: q-decoder의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: binary-to-one-hot 해독, MUX는 선택/DMUX는 분배. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 13: q-decoder 한 문항의 recall과 요약을 저작한다.** 위 Files의 해당 HTML에서 understand 다음에 recall을 삽입하고 기존 직계 sum에 data-summary=recall 문단을 추가한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 14: q-tri의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: High-Z는 논리 0과 다름, active-low enable과 버스 충돌; disputed 유지. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 15: q-tri 한 문항의 recall과 요약을 저작한다.** 위 Files의 해당 HTML에서 understand 다음에 recall을 삽입하고 기존 직계 sum에 data-summary=recall 문단을 추가한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 16: q-muxdef의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: 여러 입력 중 하나를 선택하는 MUX 정의와 선택선 역할. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 17: q-muxdef 한 문항의 recall과 요약을 저작한다.** 위 Files의 해당 HTML에서 understand 다음에 recall을 삽입하고 기존 직계 sum에 data-summary=recall 문단을 추가한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 18: q-demuxdef의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: 한 입력을 선택 출력으로 보내는 DMUX 정의; 기출 미확인 표시 유지. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 19: q-demuxdef 한 문항의 recall과 요약을 저작한다.** 위 Files의 해당 HTML에서 understand 다음에 recall을 삽입하고 기존 직계 sum에 data-summary=recall 문단을 추가한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 20: q-difference의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: 입력→출력 개수와 선택선 역할 비교; 기출 미확인 표시 유지. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 21: q-difference 한 문항의 recall과 요약을 저작한다.** 위 Files의 해당 HTML에서 understand 다음에 recall을 삽입하고 기존 직계 sum에 data-summary=recall 문단을 추가한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 22: q-demux4의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: 선택 비트→출력 번호와 출력 극성; disputed·기출 미확인 유지. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 23: q-demux4 한 문항의 recall과 요약을 저작한다.** 위 Files의 해당 HTML에서 understand 다음에 recall을 삽입하고 기존 직계 sum에 data-summary=recall 문단을 추가한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 24: q-mux2-graded의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: 2×1 선택 식을 지정된 네 행에만 적용, 채점 행 순서 보존. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 25: q-mux2-graded 한 문항의 recall과 요약을 저작한다.** 위 Files의 해당 HTML에서 understand 다음에 recall을 삽입하고 기존 직계 sum에 data-summary=recall 문단을 추가한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 26: q-active-general의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: 활성은 기능 실행의 의미, High/Low와 출력값의 구분. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 27: q-active-general 한 문항의 recall과 요약을 저작한다.** 위 Files의 해당 HTML에서 understand 다음에 recall을 삽입하고 기존 직계 sum에 data-summary=recall 문단을 추가한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 28: 원고·요약을 한 문항씩 재검토하고 기록을 갱신한다.** 각 ID의 단서/개념/기호/조건/선택 이유/모든 소문항/요약 일치/원문 page/경고 보존을 기록한다. 기존 source_visual/content/browser 문구를 복사하지 않고 실제 확인한 결과를 쓴다. 검증 기록에는 실제 독립 검산·검토자와 결과를 기재한다.

- [ ] **Step 29: 새 고유 stage를 만들고 기계 검사를 수행한다.** 출력 stage 경로를 파일로 기록하여 이후 명령이 같은 stage를 사용한다.

```powershell
$recallStage04=Join-Path 'tmp/review-pack' ('recall-04-'+[guid]::NewGuid().ToString('N'))
python -m scripts.lab.review_pack explain-stage --folder '복습노트/실험04' --author-root 'docs/learning-pack-source/실험04/problem-explanations' --stage $recallStage04 --explanation-version 2
if ($LASTEXITCODE -ne 0) { throw 'explain-stage failed' }
Set-Content -LiteralPath 'output/validation/problem-recall/stage-04.txt' -Value $recallStage04 -Encoding utf8
python -m scripts.lab.review_pack check --folder $recallStage04
if ($LASTEXITCODE -ne 0) { throw 'check failed' }
```

Expected: 새 stage 경로와 OK (mechanical checks only). 실패하면 원고를 수정하고 새 stage를 만든다. 기존 stage를 덮어쓰지 않는다.

- [ ] **Step 30: stage에서 12문항의 브라우저·원문·내용을 실제 검토한다.** 375×900/1280×900 × light/dark의 각 문항 hash로 이동하여 recall을 읽고 우측 요약을 열어 본문과 대조한다. pageerror·KaTeX error·깨진 그림·문서 가로 넘침은 0, 긴 수식/표는 카드 내부 스크롤, JS 비활성에서는 전체 풀이가 읽혀야 한다. 관련 화면/측정/근거를 검증결과.md에 남긴다. 새 결과에 대한 content=pass 또는 self_review, source_visual=pass, browser=pass, independent=실제 상태만 manifest에 기록한다. 문구 수정 후에는 다시 새 stage를 만들고 관련 검토를 수행한다.

- [ ] **Step 31: 검토 기록을 stage와 저작 원본에 보존하고 소유 목록을 동기화한다.** 다음 코드는 검사 합격을 자동 부여하지 않는다. 실제 기록 작성 후 파일을 동기화한다.

```powershell
@'
from pathlib import Path
import json, shutil
stage=Path(Path('output/validation/problem-recall/stage-04.txt').read_text(encoding='utf-8-sig').strip())
report=Path('docs/learning-pack-source/실험04/problem-explanations/검증결과.md')
shutil.copy2(report,stage/'자료/problem-explanations/검증결과.md')
p=stage/'자료/manifest.json'; m=json.loads(p.read_text(encoding='utf-8'))
m['generated_files']=sorted(f.relative_to(stage).as_posix() for f in stage.rglob('*') if f.is_file())
p.write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8')
'@ | python -
```

- [ ] **Step 32: stage의 다른 파일 및 문항·출처·토픽이 원본과 같은지 확인한다.**

```powershell
@'
from pathlib import Path
import json,hashlib
stage=Path(Path('output/validation/problem-recall/stage-04.txt').read_text(encoding='utf-8-sig').strip())
baseline=json.loads(Path('output/validation/problem-recall/baseline-04.json').read_text(encoding='utf-8'))
old=baseline['manifest']; new=json.loads((stage/'자료/manifest.json').read_text(encoding='utf-8'))
for key in ('experiment','sources','topics','problems','checks','review_presentation_version','note_presentation_version'):
    assert old.get(key)==new.get(key), key
for rel,digest in baseline['files'].items():
    path=stage/rel
    # 사용자 파일은 stage에 복사하지 않고 publish가 보존한다. 원본 generated_files로 구분한다.
    if rel not in old.get('generated_files',[]): continue
    assert path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest()==digest, rel
assert new['problem_explanation_version']==2
assert new['explanation_checks']['source_visual']=='pass'
assert new['explanation_checks']['content'] in {'pass','self_review'}
assert new['explanation_checks']['browser']=='pass'
print('preservation and reviews checked')
'@ | python -
```

- [ ] **Step 33: 이 실험을 검증 후 발행한다.**

```powershell
$recallStage04=Get-Content -LiteralPath 'output/validation/problem-recall/stage-04.txt' -Raw
$recallStage04=$recallStage04.Trim()
python -m scripts.lab.review_pack check --folder $recallStage04
if ($LASTEXITCODE -ne 0) { throw 'final stage check failed' }
python -m scripts.lab.review_pack publish --root . --stage $recallStage04 --experiment 4
if ($LASTEXITCODE -ne 0) { throw 'publication failed' }
python -m scripts.lab.review_pack check --folder '복습노트/실험04'
if ($LASTEXITCODE -ne 0) { throw 'published check failed' }
python -m pytest "tests/test_review_pack_explanation_published.py::test_recall_published[4-12]" -n 0 -q
```

Expected: publish 출력에 백업 경로, pack check OK, 12문항 recall 테스트 PASS. 백업 경로를 docs/verify/logic-lab-problem-recall.md에 기록한다. 발행 후 baseline의 모든 파일(사용자 파일 포함)이 같은 hash인지 비교하고 기존 소유 목록 밖의 신규 파일은 mutable 범위 외에 없는지 확인한다.

- [ ] **Step 34: 실험04 관련 원고·발행 문서·검증 기록만 커밋한다.** 테스트에서는 전체 6실험 매개변수 목록을 한 번만 추가한다. 아직 미완성인 다른 실험은 이 커밋의 완료 대상으로 표시하지 않는다.

```powershell
git add 'docs/learning-pack-source/실험04/problem-explanations' '복습노트/실험04/실험04_문제설명.html' '복습노트/실험04/실험04_문제설명.md' '복습노트/실험04/자료/problem-explanations' '복습노트/실험04/자료/manifest.json' docs/verify/logic-lab-problem-recall.md tests/test_review_pack_explanation_published.py
git add 'docs/learning-pack-source/실험04/manifest.json'
git commit -m "docs: add concept recall to lab 04 explanations"
```


## Task 8: 실험05 19문항의 핵심 개념 보충과 검토 발행

**Files:**
- Modify: docs/learning-pack-source/실험05/problem-explanations/q-dec3x8.html
- Modify: docs/learning-pack-source/실험05/problem-explanations/q-prio-onehot.html
- Modify: docs/learning-pack-source/실험05/problem-explanations/q-prio-exam.html
- Modify: docs/learning-pack-source/실험05/problem-explanations/q-dec2x4-design.html
- Modify: docs/learning-pack-source/실험05/problem-explanations/q-enc4x2-design.html
- Modify: docs/learning-pack-source/실험05/problem-explanations/q-excess3-why.html
- Modify: docs/learning-pack-source/실험05/problem-explanations/q-excess3-enc-exam.html
- Modify: docs/learning-pack-source/실험05/problem-explanations/q-excess3-enc-6row.html
- Modify: docs/learning-pack-source/실험05/problem-explanations/q-1of4-excess3.html
- Modify: docs/learning-pack-source/실험05/problem-explanations/q-prio-vs-binary.html
- Modify: docs/learning-pack-source/실험05/problem-explanations/q-demux-from-dec.html
- Modify: docs/learning-pack-source/실험05/problem-explanations/q-demux-from-dec-graded.html
- Modify: docs/learning-pack-source/실험05/problem-explanations/q-74hc148-table.html
- Modify: docs/learning-pack-source/실험05/problem-explanations/q-quiz-dec2x4-table.html
- Modify: docs/learning-pack-source/실험05/problem-explanations/q-sa-decoder-def.html
- Modify: docs/learning-pack-source/실험05/problem-explanations/q-sa-encoder-def.html
- Modify: docs/learning-pack-source/실험05/problem-explanations/q-sa-enc8x3.html
- Modify: docs/learning-pack-source/실험05/problem-explanations/q-sa-prio-why.html
- Modify: docs/learning-pack-source/실험05/problem-explanations/q-sa-74hc143.html
- Modify: docs/learning-pack-source/실험05/problem-explanations/검증결과.md (실험06은 새 저작 기록을 생성)
- Modify: 복습노트/실험05/실험05_문제설명.html, 복습노트/실험05/실험05_문제설명.md, 복습노트/실험05/자료/manifest.json
- Modify: 복습노트/실험05/자료/problem-explanations/의 위 19개 원고와 검증결과.md
- Modify/Test: tests/test_review_pack_explanation_published.py
- Modify: docs/verify/logic-lab-problem-recall.md
- Modify: docs/learning-pack-source/실험05/manifest.json (기존 원고의 problem_explanation_version만 2로 변경)

**Interfaces:**
- Consumes: Task 2의 prepare_explanation_stage(..., explanation_version=2), check/publish CLI; Task 3의 전용 저작·검증 규칙; 기존 실험05의 manifest와 문제지 payload.
- Produces: 같은 included 19문항의 v2 원고/HTML/MD, 실제 검토 기록, 원본 보존 hash와 백업 경로. 문제/풀이 payload·답안 상태는 그대로다.

- [ ] **Step 1: 이 실험의 실패를 확인한다.** Task 4에서는 앞 절의 공통 test_recall_published 코드를 먼저 추가한다. 이후 각 실험은 아래 한 케이스를 실행한다.

```powershell
python -m pytest "tests/test_review_pack_explanation_published.py::test_recall_published[5-19]" -n 0 -q
```

Expected: 현재 발행 manifest가 v1이라 FAIL. 다른 실험의 아직 보충하지 않은 케이스는 이 단계에서 통과할 필요가 없다.

- [ ] **Step 2: 설명 밖의 모든 파일과 manifest를 snapshot한다.** 다음 코드는 원본을 수정하지 않으며 출력 폴더의 baseline이 이미 있으면 실패한다.

```powershell
@'
from pathlib import Path
import hashlib, json
folder=Path('복습노트/실험05')
out=Path('output/validation/problem-recall')
out.mkdir(parents=True,exist_ok=True)
baseline=out/'baseline-05.json'
if baseline.exists(): raise SystemExit('Baseline already exists; keep the recorded original')
mutable={'실험05_문제설명.html','실험05_문제설명.md','자료/manifest.json'}
hashes={}
for path in folder.rglob('*'):
    if not path.is_file(): continue
    rel=path.relative_to(folder).as_posix()
    if rel in mutable or rel.startswith('자료/problem-explanations/'): continue
    hashes[rel]=hashlib.sha256(path.read_bytes()).hexdigest()
m=json.loads((folder/'자료/manifest.json').read_text(encoding='utf-8'))
baseline.write_text(json.dumps({'files':hashes,'manifest':m},ensure_ascii=False,indent=2),encoding='utf-8')
'@ | python -
```

- [ ] **Step 3: 이 실험의 included ID와 표를 읽고 각 문항의 원문·토픽·기존 start/solve/verify를 대조한다.** 아래 관점은 저작 범위이며 미확인 원문 조건을 추측하는 근거가 아니다. 식·극성·임계값은 실제 원문 페이지로 확인한다.

| 문항 ID | recall에서 연결할 단서·개념·조건 |
|---|---|
| q-dec3x8 | 3비트 이진 입력의 8개 minterm 출력과 활성 극성 |
| q-prio-onehot | one-hot 입력 번호를 3비트로 인코딩, 무입력/유효 표시 구분 |
| q-prio-exam | 다중 활성 입력에서 가장 높은 우선순위 선택과 무관 입력 |
| q-dec2x4-design | S1/S0의 네 minterm과 Enable의 곱, 비트 순서 |
| q-enc4x2-design | one-hot 번호의 상위/하위 비트와 드모르간의 NAND 변환 |
| q-excess3-why | 10진 숫자+3의 4비트 코드와 자기보수 성질의 적용 범위 |
| q-excess3-enc-exam | 주어진 회로의 bit 가중치와 Excess-3 값; 네 행만 검산 |
| q-excess3-enc-6row | 10진/입력 코드/Excess-3 출력 구분과 여섯 지정 행 |
| q-1of4-excess3 | one-hot의 입력 번호를 먼저 해석한 뒤 +3 코딩 |
| q-prio-vs-binary | one-hot 전제의 binary encoder와 다중 활성 처리 priority encoder |
| q-demux-from-dec | decoder의 선택 minterm에 데이터 D를 조건으로 추가 |
| q-demux-from-dec-graded | 주소 선택과 데이터 분배의 차이, Enable/데이터 결합 |
| q-74hc148-table | 74HC148 입력·출력·EI의 active-low와 우선순위, GS/EO 원문 대조 |
| q-quiz-dec2x4-table | 회로 게이트·버블에서 실제 minterm과 출력 극성 판독 |
| q-sa-decoder-def | n비트 코드→2ⁿ개 선택 출력, Enable과 극성 |
| q-sa-encoder-def | 한 활성 입력의 번호→이진 코드, one-hot 전제 |
| q-sa-enc8x3 | 8개 입력 번호와 A2/A1/A0의 4/2/1 가중치 |
| q-sa-prio-why | 입력 여러 개가 활성일 때 출력 모호성을 우선순위로 해결 |
| q-sa-74hc143 | 문항에 적힌 IC명과 원 그림의 출력 핀 기능 대조, 148/143 혼동 금지 |

원문 참조는 아래 코드로 manifest의 문제·토픽별 출처를 출력한다. PDF 회로·표를 읽을 때 pdf 스킬을 사용하고 실제 페이지를 렌더링하여 판독한다. 텍스트 추출만으로 버블/엣지/표의 머리를 확정하지 않는다.

```powershell
@'
from pathlib import Path
import json
m=json.loads(Path('복습노트/실험05/자료/manifest.json').read_text(encoding='utf-8'))
sources={s['id']:s for s in m['sources']}; topics={t['id']:t for t in m['topics']}
for p in m['problems']:
    if p['status']!='included': continue
    refs=p['sources']+[r for tid in p['topics'] for r in topics[tid]['sources']]
    print(p['id'],[(sources[r['source_id']]['path'],r.get('pdf_page')) for r in refs])
'@ | python -
```

- [ ] **Step 4: q-dec3x8의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: 3비트 이진 입력의 8개 minterm 출력과 활성 극성. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 5: q-dec3x8 한 문항의 recall과 요약을 저작한다.** 위 Files의 해당 HTML에서 understand 다음에 recall을 삽입하고 기존 직계 sum에 data-summary=recall 문단을 추가한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 6: q-prio-onehot의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: one-hot 입력 번호를 3비트로 인코딩, 무입력/유효 표시 구분. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 7: q-prio-onehot 한 문항의 recall과 요약을 저작한다.** 위 Files의 해당 HTML에서 understand 다음에 recall을 삽입하고 기존 직계 sum에 data-summary=recall 문단을 추가한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 8: q-prio-exam의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: 다중 활성 입력에서 가장 높은 우선순위 선택과 무관 입력. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 9: q-prio-exam 한 문항의 recall과 요약을 저작한다.** 위 Files의 해당 HTML에서 understand 다음에 recall을 삽입하고 기존 직계 sum에 data-summary=recall 문단을 추가한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 10: q-dec2x4-design의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: S1/S0의 네 minterm과 Enable의 곱, 비트 순서. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 11: q-dec2x4-design 한 문항의 recall과 요약을 저작한다.** 위 Files의 해당 HTML에서 understand 다음에 recall을 삽입하고 기존 직계 sum에 data-summary=recall 문단을 추가한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 12: q-enc4x2-design의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: one-hot 번호의 상위/하위 비트와 드모르간의 NAND 변환. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 13: q-enc4x2-design 한 문항의 recall과 요약을 저작한다.** 위 Files의 해당 HTML에서 understand 다음에 recall을 삽입하고 기존 직계 sum에 data-summary=recall 문단을 추가한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 14: q-excess3-why의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: 10진 숫자+3의 4비트 코드와 자기보수 성질의 적용 범위. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 15: q-excess3-why 한 문항의 recall과 요약을 저작한다.** 위 Files의 해당 HTML에서 understand 다음에 recall을 삽입하고 기존 직계 sum에 data-summary=recall 문단을 추가한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 16: q-excess3-enc-exam의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: 주어진 회로의 bit 가중치와 Excess-3 값; 네 행만 검산. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 17: q-excess3-enc-exam 한 문항의 recall과 요약을 저작한다.** 위 Files의 해당 HTML에서 understand 다음에 recall을 삽입하고 기존 직계 sum에 data-summary=recall 문단을 추가한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 18: q-excess3-enc-6row의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: 10진/입력 코드/Excess-3 출력 구분과 여섯 지정 행. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 19: q-excess3-enc-6row 한 문항의 recall과 요약을 저작한다.** 위 Files의 해당 HTML에서 understand 다음에 recall을 삽입하고 기존 직계 sum에 data-summary=recall 문단을 추가한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 20: q-1of4-excess3의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: one-hot의 입력 번호를 먼저 해석한 뒤 +3 코딩. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 21: q-1of4-excess3 한 문항의 recall과 요약을 저작한다.** 위 Files의 해당 HTML에서 understand 다음에 recall을 삽입하고 기존 직계 sum에 data-summary=recall 문단을 추가한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 22: q-prio-vs-binary의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: one-hot 전제의 binary encoder와 다중 활성 처리 priority encoder. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 23: q-prio-vs-binary 한 문항의 recall과 요약을 저작한다.** 위 Files의 해당 HTML에서 understand 다음에 recall을 삽입하고 기존 직계 sum에 data-summary=recall 문단을 추가한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 24: q-demux-from-dec의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: decoder의 선택 minterm에 데이터 D를 조건으로 추가. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 25: q-demux-from-dec 한 문항의 recall과 요약을 저작한다.** 위 Files의 해당 HTML에서 understand 다음에 recall을 삽입하고 기존 직계 sum에 data-summary=recall 문단을 추가한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 26: q-demux-from-dec-graded의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: 주소 선택과 데이터 분배의 차이, Enable/데이터 결합. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 27: q-demux-from-dec-graded 한 문항의 recall과 요약을 저작한다.** 위 Files의 해당 HTML에서 understand 다음에 recall을 삽입하고 기존 직계 sum에 data-summary=recall 문단을 추가한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 28: q-74hc148-table의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: 74HC148 입력·출력·EI의 active-low와 우선순위, GS/EO 원문 대조. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 29: q-74hc148-table 한 문항의 recall과 요약을 저작한다.** 위 Files의 해당 HTML에서 understand 다음에 recall을 삽입하고 기존 직계 sum에 data-summary=recall 문단을 추가한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 30: q-quiz-dec2x4-table의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: 회로 게이트·버블에서 실제 minterm과 출력 극성 판독. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 31: q-quiz-dec2x4-table 한 문항의 recall과 요약을 저작한다.** 위 Files의 해당 HTML에서 understand 다음에 recall을 삽입하고 기존 직계 sum에 data-summary=recall 문단을 추가한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 32: q-sa-decoder-def의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: n비트 코드→2ⁿ개 선택 출력, Enable과 극성. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 33: q-sa-decoder-def 한 문항의 recall과 요약을 저작한다.** 위 Files의 해당 HTML에서 understand 다음에 recall을 삽입하고 기존 직계 sum에 data-summary=recall 문단을 추가한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 34: q-sa-encoder-def의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: 한 활성 입력의 번호→이진 코드, one-hot 전제. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 35: q-sa-encoder-def 한 문항의 recall과 요약을 저작한다.** 위 Files의 해당 HTML에서 understand 다음에 recall을 삽입하고 기존 직계 sum에 data-summary=recall 문단을 추가한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 36: q-sa-enc8x3의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: 8개 입력 번호와 A2/A1/A0의 4/2/1 가중치. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 37: q-sa-enc8x3 한 문항의 recall과 요약을 저작한다.** 위 Files의 해당 HTML에서 understand 다음에 recall을 삽입하고 기존 직계 sum에 data-summary=recall 문단을 추가한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 38: q-sa-prio-why의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: 입력 여러 개가 활성일 때 출력 모호성을 우선순위로 해결. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 39: q-sa-prio-why 한 문항의 recall과 요약을 저작한다.** 위 Files의 해당 HTML에서 understand 다음에 recall을 삽입하고 기존 직계 sum에 data-summary=recall 문단을 추가한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 40: q-sa-74hc143의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: 문항에 적힌 IC명과 원 그림의 출력 핀 기능 대조, 148/143 혼동 금지. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 41: q-sa-74hc143 한 문항의 recall과 요약을 저작한다.** 위 Files의 해당 HTML에서 understand 다음에 recall을 삽입하고 기존 직계 sum에 data-summary=recall 문단을 추가한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 42: 원고·요약을 한 문항씩 재검토하고 기록을 갱신한다.** 각 ID의 단서/개념/기호/조건/선택 이유/모든 소문항/요약 일치/원문 page/경고 보존을 기록한다. 기존 source_visual/content/browser 문구를 복사하지 않고 실제 확인한 결과를 쓴다. 검증 기록에는 실제 독립 검산·검토자와 결과를 기재한다.

- [ ] **Step 43: 새 고유 stage를 만들고 기계 검사를 수행한다.** 출력 stage 경로를 파일로 기록하여 이후 명령이 같은 stage를 사용한다.

```powershell
$recallStage05=Join-Path 'tmp/review-pack' ('recall-05-'+[guid]::NewGuid().ToString('N'))
python -m scripts.lab.review_pack explain-stage --folder '복습노트/실험05' --author-root 'docs/learning-pack-source/실험05/problem-explanations' --stage $recallStage05 --explanation-version 2
if ($LASTEXITCODE -ne 0) { throw 'explain-stage failed' }
Set-Content -LiteralPath 'output/validation/problem-recall/stage-05.txt' -Value $recallStage05 -Encoding utf8
python -m scripts.lab.review_pack check --folder $recallStage05
if ($LASTEXITCODE -ne 0) { throw 'check failed' }
```

Expected: 새 stage 경로와 OK (mechanical checks only). 실패하면 원고를 수정하고 새 stage를 만든다. 기존 stage를 덮어쓰지 않는다.

- [ ] **Step 44: stage에서 19문항의 브라우저·원문·내용을 실제 검토한다.** 375×900/1280×900 × light/dark의 각 문항 hash로 이동하여 recall을 읽고 우측 요약을 열어 본문과 대조한다. pageerror·KaTeX error·깨진 그림·문서 가로 넘침은 0, 긴 수식/표는 카드 내부 스크롤, JS 비활성에서는 전체 풀이가 읽혀야 한다. 관련 화면/측정/근거를 검증결과.md에 남긴다. 새 결과에 대한 content=pass 또는 self_review, source_visual=pass, browser=pass, independent=실제 상태만 manifest에 기록한다. 문구 수정 후에는 다시 새 stage를 만들고 관련 검토를 수행한다.

- [ ] **Step 45: 검토 기록을 stage와 저작 원본에 보존하고 소유 목록을 동기화한다.** 다음 코드는 검사 합격을 자동 부여하지 않는다. 실제 기록 작성 후 파일을 동기화한다.

```powershell
@'
from pathlib import Path
import json, shutil
stage=Path(Path('output/validation/problem-recall/stage-05.txt').read_text(encoding='utf-8-sig').strip())
report=Path('docs/learning-pack-source/실험05/problem-explanations/검증결과.md')
shutil.copy2(report,stage/'자료/problem-explanations/검증결과.md')
p=stage/'자료/manifest.json'; m=json.loads(p.read_text(encoding='utf-8'))
m['generated_files']=sorted(f.relative_to(stage).as_posix() for f in stage.rglob('*') if f.is_file())
p.write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8')
'@ | python -
```

- [ ] **Step 46: stage의 다른 파일 및 문항·출처·토픽이 원본과 같은지 확인한다.**

```powershell
@'
from pathlib import Path
import json,hashlib
stage=Path(Path('output/validation/problem-recall/stage-05.txt').read_text(encoding='utf-8-sig').strip())
baseline=json.loads(Path('output/validation/problem-recall/baseline-05.json').read_text(encoding='utf-8'))
old=baseline['manifest']; new=json.loads((stage/'자료/manifest.json').read_text(encoding='utf-8'))
for key in ('experiment','sources','topics','problems','checks','review_presentation_version','note_presentation_version'):
    assert old.get(key)==new.get(key), key
for rel,digest in baseline['files'].items():
    path=stage/rel
    # 사용자 파일은 stage에 복사하지 않고 publish가 보존한다. 원본 generated_files로 구분한다.
    if rel not in old.get('generated_files',[]): continue
    assert path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest()==digest, rel
assert new['problem_explanation_version']==2
assert new['explanation_checks']['source_visual']=='pass'
assert new['explanation_checks']['content'] in {'pass','self_review'}
assert new['explanation_checks']['browser']=='pass'
print('preservation and reviews checked')
'@ | python -
```

- [ ] **Step 47: 이 실험을 검증 후 발행한다.**

```powershell
$recallStage05=Get-Content -LiteralPath 'output/validation/problem-recall/stage-05.txt' -Raw
$recallStage05=$recallStage05.Trim()
python -m scripts.lab.review_pack check --folder $recallStage05
if ($LASTEXITCODE -ne 0) { throw 'final stage check failed' }
python -m scripts.lab.review_pack publish --root . --stage $recallStage05 --experiment 5
if ($LASTEXITCODE -ne 0) { throw 'publication failed' }
python -m scripts.lab.review_pack check --folder '복습노트/실험05'
if ($LASTEXITCODE -ne 0) { throw 'published check failed' }
python -m pytest "tests/test_review_pack_explanation_published.py::test_recall_published[5-19]" -n 0 -q
```

Expected: publish 출력에 백업 경로, pack check OK, 19문항 recall 테스트 PASS. 백업 경로를 docs/verify/logic-lab-problem-recall.md에 기록한다. 발행 후 baseline의 모든 파일(사용자 파일 포함)이 같은 hash인지 비교하고 기존 소유 목록 밖의 신규 파일은 mutable 범위 외에 없는지 확인한다.

- [ ] **Step 48: 실험05 관련 원고·발행 문서·검증 기록만 커밋한다.** 테스트에서는 전체 6실험 매개변수 목록을 한 번만 추가한다. 아직 미완성인 다른 실험은 이 커밋의 완료 대상으로 표시하지 않는다.

```powershell
git add 'docs/learning-pack-source/실험05/problem-explanations' '복습노트/실험05/실험05_문제설명.html' '복습노트/실험05/실험05_문제설명.md' '복습노트/실험05/자료/problem-explanations' '복습노트/실험05/자료/manifest.json' docs/verify/logic-lab-problem-recall.md tests/test_review_pack_explanation_published.py
git add 'docs/learning-pack-source/실험05/manifest.json'
git commit -m "docs: add concept recall to lab 05 explanations"
```


## Task 9: 실험06 14문항의 핵심 개념 보충과 검토 발행

**Files:**
- Create: docs/learning-pack-source/실험06/problem-explanations/q-diff.html
- Create: docs/learning-pack-source/실험06/problem-explanations/q-latch.html
- Create: docs/learning-pack-source/실험06/problem-explanations/q-ff.html
- Create: docs/learning-pack-source/실험06/problem-explanations/q-sr-nand-00.html
- Create: docs/learning-pack-source/실험06/problem-explanations/q-rs-latch.html
- Create: docs/learning-pack-source/실험06/problem-explanations/q-rs-quiz.html
- Create: docs/learning-pack-source/실험06/problem-explanations/q-dff-table.html
- Create: docs/learning-pack-source/실험06/problem-explanations/q-dff-design.html
- Create: docs/learning-pack-source/실험06/problem-explanations/q-jkff-short.html
- Create: docs/learning-pack-source/실험06/problem-explanations/q-jkff-design.html
- Create: docs/learning-pack-source/실험06/problem-explanations/q-tff.html
- Create: docs/learning-pack-source/실험06/problem-explanations/q-74hc76.html
- Create: docs/learning-pack-source/실험06/problem-explanations/q-74hc574.html
- Create: docs/learning-pack-source/실험06/problem-explanations/q-p-76-trace.html
- Modify: docs/learning-pack-source/실험06/problem-explanations/검증결과.md (실험06은 새 저작 기록을 생성)
- Modify: 복습노트/실험06/실험06_문제설명.html, 복습노트/실험06/실험06_문제설명.md, 복습노트/실험06/자료/manifest.json
- Modify: 복습노트/실험06/자료/problem-explanations/의 위 14개 원고와 검증결과.md
- Modify/Test: tests/test_review_pack_explanation_published.py
- Modify: docs/verify/logic-lab-problem-recall.md
- Create: docs/learning-pack-source/실험06/recall.py
- Modify: docs/learning-pack-source/실험06/explanations.py, build_run.py

**Interfaces:**
- Consumes: Task 2의 prepare_explanation_stage(..., explanation_version=2), check/publish CLI; Task 3의 전용 저작·검증 규칙; 기존 실험06의 manifest와 문제지 payload.
- Produces: 같은 included 14문항의 v2 원고/HTML/MD, 실제 검토 기록, 원본 보존 hash와 백업 경로. 문제/풀이 payload·답안 상태는 그대로다.

- [ ] **Step 1: 이 실험의 실패를 확인한다.** Task 4에서는 앞 절의 공통 test_recall_published 코드를 먼저 추가한다. 이후 각 실험은 아래 한 케이스를 실행한다.

```powershell
python -m pytest "tests/test_review_pack_explanation_published.py::test_recall_published[6-14]" -n 0 -q
```

Expected: 현재 발행 manifest가 v1이라 FAIL. 다른 실험의 아직 보충하지 않은 케이스는 이 단계에서 통과할 필요가 없다.

- [ ] **Step 2: 설명 밖의 모든 파일과 manifest를 snapshot한다.** 다음 코드는 원본을 수정하지 않으며 출력 폴더의 baseline이 이미 있으면 실패한다.

```powershell
@'
from pathlib import Path
import hashlib, json
folder=Path('복습노트/실험06')
out=Path('output/validation/problem-recall')
out.mkdir(parents=True,exist_ok=True)
baseline=out/'baseline-06.json'
if baseline.exists(): raise SystemExit('Baseline already exists; keep the recorded original')
mutable={'실험06_문제설명.html','실험06_문제설명.md','자료/manifest.json'}
hashes={}
for path in folder.rglob('*'):
    if not path.is_file(): continue
    rel=path.relative_to(folder).as_posix()
    if rel in mutable or rel.startswith('자료/problem-explanations/'): continue
    hashes[rel]=hashlib.sha256(path.read_bytes()).hexdigest()
m=json.loads((folder/'자료/manifest.json').read_text(encoding='utf-8'))
baseline.write_text(json.dumps({'files':hashes,'manifest':m},ensure_ascii=False,indent=2),encoding='utf-8')
'@ | python -
```

- [ ] **Step 3: 이 실험의 included ID와 표를 읽고 각 문항의 원문·토픽·기존 start/solve/verify를 대조한다.** 아래 관점은 저작 범위이며 미확인 원문 조건을 추측하는 근거가 아니다. 식·극성·임계값은 실제 원문 페이지로 확인한다.

| 문항 ID | recall에서 연결할 단서·개념·조건 |
|---|---|
| q-diff | 저장과 반영 시점: level-sensitive latch와 edge-triggered FF |
| q-latch | 되먹임의 1비트 기억과 Enable 활성 동안의 투명성 |
| q-ff | 클록 엣지 샘플링과 엣지 사이의 상태 유지 |
| q-sr-nand-00 | NAND의 0 입력 강제 1과 active-low SR; 동시 활성의 금지 상태 |
| q-rs-latch | Enable 있는 교안 회로의 실제 입력 극성과 유지/set/reset/금지 |
| q-rs-quiz | 출력 되먹임과 toggle 조건, 레벨 회로 반복 변화의 조건 |
| q-dff-table | SR 입력을 D와 보수로 묶는 의미와 회로의 level/edge 판독 |
| q-dff-design | D의 상보 입력 구성과 실제 회로 트리거 조건 |
| q-jkff-short | J/K의 유지/reset/set/toggle 조건과 이전 상태 Q |
| q-jkff-design | 출력 되먹임으로 SR 금지 입력을 피하는 JK 구성과 회로 클록 조건 |
| q-tff | JK에서 J=K=T, T=0 유지/T=1 엣지당 반전, Qnext=Q XOR T |
| q-74hc76 | 비동기 CLR/PR의 active-low, 클록과 무관한 우선 동작·동시 활성 주의 |
| q-74hc574 | 상승 엣지 저장, 8비트 D 레지스터와 OE의 High-Z 제어 구분 |
| q-p-76-trace | 74HC76 하강 엣지에서만 JK 상태 갱신, 비동기 제어 우선 |

원문 참조는 아래 코드로 manifest의 문제·토픽별 출처를 출력한다. PDF 회로·표를 읽을 때 pdf 스킬을 사용하고 실제 페이지를 렌더링하여 판독한다. 텍스트 추출만으로 버블/엣지/표의 머리를 확정하지 않는다.

```powershell
@'
from pathlib import Path
import json
m=json.loads(Path('복습노트/실험06/자료/manifest.json').read_text(encoding='utf-8'))
sources={s['id']:s for s in m['sources']}; topics={t['id']:t for t in m['topics']}
for p in m['problems']:
    if p['status']!='included': continue
    refs=p['sources']+[r for tid in p['topics'] for r in topics[tid]['sources']]
    print(p['id'],[(sources[r['source_id']]['path'],r.get('pdf_page')) for r in refs])
'@ | python -
```

- [ ] **Step 4: q-diff의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: 저장과 반영 시점: level-sensitive latch와 edge-triggered FF. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 5: q-diff 한 문항의 recall과 요약을 저작한다.** recall.py의 RECALL['q-diff']에 (본문 HTML, 짧은 요약 HTML)을 작성한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 6: q-latch의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: 되먹임의 1비트 기억과 Enable 활성 동안의 투명성. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 7: q-latch 한 문항의 recall과 요약을 저작한다.** recall.py의 RECALL['q-latch']에 (본문 HTML, 짧은 요약 HTML)을 작성한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 8: q-ff의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: 클록 엣지 샘플링과 엣지 사이의 상태 유지. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 9: q-ff 한 문항의 recall과 요약을 저작한다.** recall.py의 RECALL['q-ff']에 (본문 HTML, 짧은 요약 HTML)을 작성한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 10: q-sr-nand-00의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: NAND의 0 입력 강제 1과 active-low SR; 동시 활성의 금지 상태. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 11: q-sr-nand-00 한 문항의 recall과 요약을 저작한다.** recall.py의 RECALL['q-sr-nand-00']에 (본문 HTML, 짧은 요약 HTML)을 작성한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 12: q-rs-latch의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: Enable 있는 교안 회로의 실제 입력 극성과 유지/set/reset/금지. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 13: q-rs-latch 한 문항의 recall과 요약을 저작한다.** recall.py의 RECALL['q-rs-latch']에 (본문 HTML, 짧은 요약 HTML)을 작성한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 14: q-rs-quiz의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: 출력 되먹임과 toggle 조건, 레벨 회로 반복 변화의 조건. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 15: q-rs-quiz 한 문항의 recall과 요약을 저작한다.** recall.py의 RECALL['q-rs-quiz']에 (본문 HTML, 짧은 요약 HTML)을 작성한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 16: q-dff-table의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: SR 입력을 D와 보수로 묶는 의미와 회로의 level/edge 판독. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 17: q-dff-table 한 문항의 recall과 요약을 저작한다.** recall.py의 RECALL['q-dff-table']에 (본문 HTML, 짧은 요약 HTML)을 작성한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 18: q-dff-design의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: D의 상보 입력 구성과 실제 회로 트리거 조건. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 19: q-dff-design 한 문항의 recall과 요약을 저작한다.** recall.py의 RECALL['q-dff-design']에 (본문 HTML, 짧은 요약 HTML)을 작성한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 20: q-jkff-short의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: J/K의 유지/reset/set/toggle 조건과 이전 상태 Q. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 21: q-jkff-short 한 문항의 recall과 요약을 저작한다.** recall.py의 RECALL['q-jkff-short']에 (본문 HTML, 짧은 요약 HTML)을 작성한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 22: q-jkff-design의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: 출력 되먹임으로 SR 금지 입력을 피하는 JK 구성과 회로 클록 조건. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 23: q-jkff-design 한 문항의 recall과 요약을 저작한다.** recall.py의 RECALL['q-jkff-design']에 (본문 HTML, 짧은 요약 HTML)을 작성한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 24: q-tff의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: JK에서 J=K=T, T=0 유지/T=1 엣지당 반전, Qnext=Q XOR T. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 25: q-tff 한 문항의 recall과 요약을 저작한다.** recall.py의 RECALL['q-tff']에 (본문 HTML, 짧은 요약 HTML)을 작성한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 26: q-74hc76의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: 비동기 CLR/PR의 active-low, 클록과 무관한 우선 동작·동시 활성 주의. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 27: q-74hc76 한 문항의 recall과 요약을 저작한다.** recall.py의 RECALL['q-74hc76']에 (본문 HTML, 짧은 요약 HTML)을 작성한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 28: q-74hc574의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: 상승 엣지 저장, 8비트 D 레지스터와 OE의 High-Z 제어 구분. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 29: q-74hc574 한 문항의 recall과 요약을 저작한다.** recall.py의 RECALL['q-74hc574']에 (본문 HTML, 짧은 요약 HTML)을 작성한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 30: q-p-76-trace의 근거 페이지와 기존 답/소문항을 읽는다.** 확인할 관점: 74HC76 하강 엣지에서만 JK 상태 갱신, 비동기 제어 우선. 단서와 적용 조건을 검증 기록의 해당 ID 행에 남긴다.
- [ ] **Step 31: q-p-76-trace 한 문항의 recall과 요약을 저작한다.** recall.py의 RECALL['q-p-76-trace']에 (본문 HTML, 짧은 요약 HTML)을 작성한다. 개념의 뜻·기호·조건·선택 이유를 연결하고 기존 풀이 및 경고는 보존한다. 공통 형식은 Task 3의 실제 HTML 예를 사용하되 이 문항 내용으로 작성한다.

- [ ] **Step 32: Python 원고 생성원에 recall을 연결한다.** recall.py는 위 14 ID 전체의 RECALL: dict[str, tuple[str,str]]를 정의한다. 각 value 첫 항은 제목을 제외한 본문 HTML, 두 번째는 요약 문단의 본문 HTML이다. 기존 explanations.build의 인수/호출은 그대로 두고 아래 코드를 해당 함수에 삽입한다. 반환문에서는 understand와 start 사이에 recall 구역을, sum 시작 뒤에 요약 문단을 삽입한다.

```python
from recall import RECALL

# 기존 build 함수 내부, links/retry 계산 옆
recall_html, recall_summary = RECALL[pid]
recall_section = (
    '<div class="layer formal" data-explanation="recall">'
    '<span class="layer-title">이 문제를 봤을 때 떠올릴 개념과 공식</span>'
    + recall_html + '</div>'
)
summary_recall = '<p data-summary="recall">'+recall_summary+'</p>'
```

build_run.py는 manifest['problem_explanation_version']=2, manifest['explanation_checks']=dict.fromkeys(CHK,'not_run')로 변경한다. 기존 다른 checks/figure REVIEW는 바꾸지 않는다. build_run.py 전체를 실행하지 않는다.

- [ ] **Step 33: 생성 조각을 별도 설명 폴더에 출력하고 실제 v2 검사로 확인한다.**

```powershell
@'
from pathlib import Path
import sys
source=Path('docs/learning-pack-source/실험06').resolve()
sys.path.insert(0,str(source))
from explanations import E
from scripts.lab.review_pack.explanation_content import validate_fragment
out=source/'problem-explanations'; out.mkdir(exist_ok=True)
if len(E)!=14: raise SystemExit('Expected 14 authored explanations')
for ident, fragment in E.items():
    validate_fragment(fragment,ident,'verified',version=2)
    (out/(ident+'.html')).write_text(fragment,encoding='utf-8')
print('14 v2 fragments')
'@ | python -
```

- [ ] **Step 34: 원고·요약을 한 문항씩 재검토하고 기록을 갱신한다.** 각 ID의 단서/개념/기호/조건/선택 이유/모든 소문항/요약 일치/원문 page/경고 보존을 기록한다. 기존 source_visual/content/browser 문구를 복사하지 않고 실제 확인한 결과를 쓴다. 검증 기록에는 실제 독립 검산·검토자와 결과를 기재한다.

- [ ] **Step 35: 새 고유 stage를 만들고 기계 검사를 수행한다.** 출력 stage 경로를 파일로 기록하여 이후 명령이 같은 stage를 사용한다.

```powershell
$recallStage06=Join-Path 'tmp/review-pack' ('recall-06-'+[guid]::NewGuid().ToString('N'))
python -m scripts.lab.review_pack explain-stage --folder '복습노트/실험06' --author-root 'docs/learning-pack-source/실험06/problem-explanations' --stage $recallStage06 --explanation-version 2
if ($LASTEXITCODE -ne 0) { throw 'explain-stage failed' }
Set-Content -LiteralPath 'output/validation/problem-recall/stage-06.txt' -Value $recallStage06 -Encoding utf8
python -m scripts.lab.review_pack check --folder $recallStage06
if ($LASTEXITCODE -ne 0) { throw 'check failed' }
```

Expected: 새 stage 경로와 OK (mechanical checks only). 실패하면 원고를 수정하고 새 stage를 만든다. 기존 stage를 덮어쓰지 않는다.

- [ ] **Step 36: stage에서 14문항의 브라우저·원문·내용을 실제 검토한다.** 375×900/1280×900 × light/dark의 각 문항 hash로 이동하여 recall을 읽고 우측 요약을 열어 본문과 대조한다. pageerror·KaTeX error·깨진 그림·문서 가로 넘침은 0, 긴 수식/표는 카드 내부 스크롤, JS 비활성에서는 전체 풀이가 읽혀야 한다. 관련 화면/측정/근거를 검증결과.md에 남긴다. 새 결과에 대한 content=pass 또는 self_review, source_visual=pass, browser=pass, independent=실제 상태만 manifest에 기록한다. 문구 수정 후에는 다시 새 stage를 만들고 관련 검토를 수행한다.

- [ ] **Step 37: 검토 기록을 stage와 저작 원본에 보존하고 소유 목록을 동기화한다.** 다음 코드는 검사 합격을 자동 부여하지 않는다. 실제 기록 작성 후 파일을 동기화한다.

```powershell
@'
from pathlib import Path
import json, shutil
stage=Path(Path('output/validation/problem-recall/stage-06.txt').read_text(encoding='utf-8-sig').strip())
report=Path('docs/learning-pack-source/실험06/problem-explanations/검증결과.md')
shutil.copy2(report,stage/'자료/problem-explanations/검증결과.md')
p=stage/'자료/manifest.json'; m=json.loads(p.read_text(encoding='utf-8'))
m['generated_files']=sorted(f.relative_to(stage).as_posix() for f in stage.rglob('*') if f.is_file())
p.write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8')
'@ | python -
```

- [ ] **Step 38: stage의 다른 파일 및 문항·출처·토픽이 원본과 같은지 확인한다.**

```powershell
@'
from pathlib import Path
import json,hashlib
stage=Path(Path('output/validation/problem-recall/stage-06.txt').read_text(encoding='utf-8-sig').strip())
baseline=json.loads(Path('output/validation/problem-recall/baseline-06.json').read_text(encoding='utf-8'))
old=baseline['manifest']; new=json.loads((stage/'자료/manifest.json').read_text(encoding='utf-8'))
for key in ('experiment','sources','topics','problems','checks','review_presentation_version','note_presentation_version'):
    assert old.get(key)==new.get(key), key
for rel,digest in baseline['files'].items():
    path=stage/rel
    # 사용자 파일은 stage에 복사하지 않고 publish가 보존한다. 원본 generated_files로 구분한다.
    if rel not in old.get('generated_files',[]): continue
    assert path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest()==digest, rel
assert new['problem_explanation_version']==2
assert new['explanation_checks']['source_visual']=='pass'
assert new['explanation_checks']['content'] in {'pass','self_review'}
assert new['explanation_checks']['browser']=='pass'
print('preservation and reviews checked')
'@ | python -
```

- [ ] **Step 39: 이 실험을 검증 후 발행한다.**

```powershell
$recallStage06=Get-Content -LiteralPath 'output/validation/problem-recall/stage-06.txt' -Raw
$recallStage06=$recallStage06.Trim()
python -m scripts.lab.review_pack check --folder $recallStage06
if ($LASTEXITCODE -ne 0) { throw 'final stage check failed' }
python -m scripts.lab.review_pack publish --root . --stage $recallStage06 --experiment 6
if ($LASTEXITCODE -ne 0) { throw 'publication failed' }
python -m scripts.lab.review_pack check --folder '복습노트/실험06'
if ($LASTEXITCODE -ne 0) { throw 'published check failed' }
python -m pytest "tests/test_review_pack_explanation_published.py::test_recall_published[6-14]" -n 0 -q
```

Expected: publish 출력에 백업 경로, pack check OK, 14문항 recall 테스트 PASS. 백업 경로를 docs/verify/logic-lab-problem-recall.md에 기록한다. 발행 후 baseline의 모든 파일(사용자 파일 포함)이 같은 hash인지 비교하고 기존 소유 목록 밖의 신규 파일은 mutable 범위 외에 없는지 확인한다.

- [ ] **Step 40: 실험06 관련 원고·발행 문서·검증 기록만 커밋한다.** 테스트에서는 전체 6실험 매개변수 목록을 한 번만 추가한다. 아직 미완성인 다른 실험은 이 커밋의 완료 대상으로 표시하지 않는다.

```powershell
git add 'docs/learning-pack-source/실험06/problem-explanations' '복습노트/실험06/실험06_문제설명.html' '복습노트/실험06/실험06_문제설명.md' '복습노트/실험06/자료/problem-explanations' '복습노트/실험06/자료/manifest.json' docs/verify/logic-lab-problem-recall.md tests/test_review_pack_explanation_published.py
git add docs/learning-pack-source/실험06/recall.py docs/learning-pack-source/실험06/explanations.py docs/learning-pack-source/실험06/build_run.py
git commit -m "docs: add concept recall to lab 06 explanations"
```

## Task 10: 86문항 화면·내용·보존 회귀와 최종 인계

**Files:**
- Modify/Test: tests/test_review_pack_explanation_browser.py, tests/test_review_pack_explanation_render.py, tests/test_review_pack_explanation_published.py
- Modify: docs/verify/logic-lab-problem-recall.md
- Read: 이 계획의 Spec, 실험01~06 저작/발행 검증결과.md와 output/validation/problem-recall/ 증거

**Interfaces:**
- Consumes: Tasks 4~9의 여섯 v2 발행 팩, 각 실험 baseline-NN.json, Task 1의 setup_v2, 기존 browser fixture.
- Produces: 86문항의 실제 브라우저/내용 검증 및 보존 결과, 관련 회귀 PASS, 최종 설명 링크 여섯 쌍과 백업/보류 보고.

- [ ] **Step 1: 생성본 v2 브라우저 회귀를 추가하고 실행한다.** 기존 pages fixture는 v1 그대로 유지하고 새 v2 테스트에서 직접 setup_v2로 조립한다.

```python
@pytest.mark.parametrize('width',[375,1280])
@pytest.mark.parametrize('theme',['light','dark'])
def test_generated_v2_recall_and_summary(browser,tmp_path,width,theme):
    from tests._explanation_recall_fixture import setup_v2
    m,run,data = setup_v2(tmp_path)
    paths = assemble(m,run,tmp_path/'stage',Path('.claude/skills/logic-lab-review-pack/assets'))
    convert_pack(paths['note_html'],paths['review_html'],manifest=m)
    ctx = browser.new_context(viewport=dict(width=width,height=900),color_scheme=theme)
    page = ctx.new_page(); errors=[]
    page.on('pageerror',lambda e: errors.append(str(e)))
    page.goto(paths['explanation_html'].as_uri()+'#q-mux-001')
    recall = page.locator('main article.topic [data-explanation="recall"]')
    assert recall.is_visible()
    assert '선택선이라는 단서' in recall.inner_text()
    if page.locator('.layout').get_attribute('data-right')!='open':
        page.locator('#toggle-right').click()
    summary = page.locator('#panel-right [data-summary="recall"]')
    assert summary.count()==1 and summary.is_visible()
    assert '입력 하나' in summary.inner_text()
    assert page.locator('.katex-error').count()==0
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    assert not errors
    ctx.close()
```

Run: `python -m pytest tests/test_review_pack_explanation_browser.py -k generated_v2_recall -n 0 -q` → PASS. 이 추가 검사는 이미 구현된 생성기 검증이며 오류가 있으면 내용이 아니라 원인을 수정한다. 신규 CSS는 추가하지 않는다.

- [ ] **Step 2: 발행본의 모든 문항에서 recall과 현재 문항 요약을 검사한다.** 기존 test_all_published_explanation_articles/test_all_published_explanations_without_js의 대상 range를 range(1,7), 기대 수 목록을 [12,14,15,12,19,14]로 확장한다. 아래 테스트도 같은 파일에 추가한다.

```python
@pytest.mark.parametrize('number',range(1,7))
@pytest.mark.parametrize('width',[375,1280])
@pytest.mark.parametrize('theme',['light','dark'])
def test_published_recall_and_summary(browser,number,width,theme):
    import json
    root=Path(__file__).resolve().parents[1]
    folder=root/'복습노트'/f'실험{number:02d}'
    manifest=json.loads((folder/'자료/manifest.json').read_text(encoding='utf-8'))
    ids=[p['id'] for p in manifest['problems'] if p['status']=='included']
    ctx=browser.new_context(viewport=dict(width=width,height=900),color_scheme=theme)
    page=ctx.new_page(); errors=[]
    page.on('pageerror',lambda e: errors.append(str(e)))
    page.goto((folder/f'실험{number:02d}_문제설명.html').as_uri())
    if page.locator('.layout').get_attribute('data-right')!='open':
        page.locator('#toggle-right').click()
    for ident in ids:
        page.evaluate('(id)=>location.hash=id',ident)
        page.wait_for_function(
            '(id)=>document.querySelector(".toc a[aria-current=true]").getAttribute("href")==="#"+id',
            arg=ident,
        )
        assert page.locator('#'+ident+' [data-explanation="recall"]').is_visible()
        summary=page.locator('#panel-right [data-summary="recall"]')
        assert summary.count()==1 and summary.is_visible()
        assert summary.inner_text().strip()
        assert page.locator('.katex-error').count()==0
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    assert not errors
    ctx.close()
```

Run: `python -m pytest tests/test_review_pack_explanation_browser.py -n 0 -q` → PASS. JS 비활성 검사에서는 recall이 모든 문항에서 보이는지 기존 verify 검사와 같은 evaluate_all로 단언한다. 요약은 hidden이 정상이라 JS 비활성에서 우측 요약 표시를 강제하지 않는다.

- [ ] **Step 3: recall 내부의 수식/표 카드와 MD 보존 테스트를 추가한다.** 기존 전 문서 변환을 유지하여 새로운 구역도 자동 카드 처리되어야 한다.

```python
def test_recall_equation_and_table_survive_render_and_md(tmp_path):
    from tests._explanation_recall_fixture import setup_v2,FRAGMENT_V2,RECALL
    m,run,data=setup_v2(tmp_path)
    extra='<p>$$Y=\\overline{S}I_0+SI_1$$</p><table><tr><th>S</th><th>선택</th></tr><tr><td>0</td><td>I0</td></tr></table>'
    fragment=FRAGMENT_V2.replace(RECALL,RECALL.replace('</div>',extra+'</div>'))
    (run/m['problems'][0]['explanation_fragment']).write_text(fragment,encoding='utf-8')
    folder=tmp_path/'stage'; folder.mkdir()
    paths=write_explanations(m,data,run,folder,ASSETS)
    parser=Parser(); parser.feed(paths['explanation_html'].read_text(encoding='utf-8'))
    recall=next(n for n in parser.root.walk() if n.attrs.get('data-explanation')=='recall')
    classes=[n.attrs.get('class','').split() for n in recall.walk()]
    assert any('equation-card' in c for c in classes)
    assert any('table-card' in c for c in classes)
    md=paths['explanation_md'].read_text(encoding='utf-8')
    assert '\\overline{S}' in md and 'I0' in md and '선택' in md
```

Run: `python -m pytest tests/test_review_pack_explanation_render.py -n 0 -q` → PASS.

- [ ] **Step 4: 86문항의 내용 검토 기록을 읽고 실제 근거와 대조한다.** 단순히 record 행이 있다는 테스트로 완료하지 않는다. 일반 정의만 있는 recall, 공식에 누락된 one-hot/Enable/극성/트리거 조건, 정성 문항에 불필요하게 만든 공식, 서로 다른 소문항 개념 누락, 본문에 없는 요약, 소자 이름/핀 기능 오기를 찾는다. 특히 실험02 경계값·전류 부호, 실험03 borrow와 carry, 실험04 High-Z, 실험05 74HC148/74HC143, 실험06 74HC76/574의 엣지를 원문과 대조한다. 수정하면 해당 실험의 새 stage·내용/브라우저 검토·발행·보존 비교를 다시 수행한다.
- [ ] **Step 5: 여섯 팩의 최종 기계 검사와 다른 파일 보존을 확인한다.**

```powershell
@'
from pathlib import Path
import hashlib,json
from scripts.lab.review_pack.checks import check_pack
counts=[]
for number in range(1,7):
    nn=f'{number:02d}'; folder=Path('복습노트')/f'실험{nn}'
    errors=check_pack(folder)
    assert not errors,(number,errors)
    baseline=json.loads((Path('output/validation/problem-recall')/f'baseline-{nn}.json').read_text(encoding='utf-8'))
    m=json.loads((folder/'자료/manifest.json').read_text(encoding='utf-8'))
    assert m['problem_explanation_version']==2
    for key in ('experiment','sources','topics','problems','checks','review_presentation_version','note_presentation_version'):
        assert m.get(key)==baseline['manifest'].get(key),(number,key)
    for rel,digest in baseline['files'].items():
        path=folder/rel
        assert path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest()==digest,(number,rel)
    mutable={f'실험{nn}_문제설명.html',f'실험{nn}_문제설명.md','자료/manifest.json'}
    unexpected=[f.relative_to(folder).as_posix() for f in folder.rglob('*') if f.is_file()
                and f.relative_to(folder).as_posix() not in baseline['files']
                and f.relative_to(folder).as_posix() not in mutable
                and not f.relative_to(folder).as_posix().startswith('자료/problem-explanations/')]
    assert not unexpected,(number,unexpected)
    counts.append(sum(p['status']=='included' for p in m['problems']))
assert counts==[12,14,15,12,19,14] and sum(counts)==86
print('6 packs, 86 explanations, all non-explanation files preserved')
'@ | python -
```

Expected: 위 문항 수와 보존 확인 메시지. 검증 증거를 docs/verify에 기록한다. 원문 hash는 check/publish의 기존 경로에서 검사하므로 그 검사를 끄지 않는다.

- [ ] **Step 6: 관련 review_pack 테스트를 한 번 모아 실행한다.**

```powershell
python -m pytest tests -k review_pack -n 0 -q
git diff --check
git status --short
```

Expected: PASS, whitespace 오류 없음, 예상 변경만 표시. 원고/계약/버전 변경 뒤 실패가 있으면 의미 있는 원인을 수정하고 해당 좁은 테스트를 먼저 재실행한다. 이미 PASS인 전체 실행을 이유 없이 반복하지 않는다. 완전히 무관한 알려진 테스트 실패가 있으면 원인과 재현 명령을 분리 기록한다.

- [ ] **Step 7: 실행 방법에 맞는 최종 리뷰를 수행한다.** Subagent-driven이면 선택한 스킬의 task별 리뷰 이후 전체 변경을 리뷰한다. Native이면 모든 task를 현재 세션에서 구현하고 마지막에 독립 리뷰어 한 명이 전체 변경을 검토한다. 이 단계의 리뷰어 호출은 사용자가 실행 방법을 선택한 뒤에만 한다. 리뷰는 버전 경로 누락, 기존 문서 변경, 86문항의 조건·경고 누락, 근거 없는 승인, exp06 원고 재생성 회귀에 집중한다. 리뷰 도구의 가용 모델/기능을 확인하며 현재 환경이 제공하지 않는 모델을 지정하지 않는다.
- [ ] **Step 8: 최종 검증 기록과 테스트 변경을 커밋한다.**

```powershell
git add tests/test_review_pack_explanation_browser.py tests/test_review_pack_explanation_render.py tests/test_review_pack_explanation_published.py docs/verify/logic-lab-problem-recall.md
git commit -m "test: verify all lab explanation recall and preserved outputs"
```

- [ ] **Step 9: 사용자에게 완료 범위와 실제 검증 결과를 보고한다.** 전용 스킬 경로, 전체팩 네 HTML·네 MD 유지, 86문항의 개념 보충, 여섯 실험의 설명 HTML/MD 링크, 기존 파일 hash 보존, 테스트 결과, 백업과 보류/미해결을 전달한다. 독립 검토 미실시나 답안 충돌을 완료 보고에서 숨기지 않는다. 원문이 부족한 팩은 발행 완료에 포함하지 않는다.

## 계획 자체 검토와 구현 인계

계획 작성자는 저장 후 아래를 직접 점검한다. 이 체크는 구현 PASS를 의미하지 않는다.

- [x] 확정된 #6=논회실 전용, #7=전체팩 포함, #8=실험01~06 전부 보충이 Spec과 Tasks 3~9에 반영되어 있다.
- [x] v1 호환성·v2 계약·전체 build·전용 stage·check·MD·publish가 Tasks 1~2에 각각 포함되어 있다.
- [x] Review Focus의 다섯 위험과 소문항/정성 문항/불확실성 의미 검토가 테스트 또는 내용 검토 단계에 대응한다.
- [x] Tasks 4~9의 included ID가 현재 manifest와 정확히 같으며 기대 합계가 86이다.
- [x] 실험06 원고 생성원과 빌드 버전 갱신이 Task 9에 포함되어 있다.
- [x] 새로운 interface 이름, keyword version/explanation_version, fixture 함수명과 CLI 옵션이 서로 일치한다.
- [x] 예제 Python 블록은 구문 검사 가능하며 미정 항목과 임시 자리표시자가 없다.
- [x] 작업 트리에 계획/설계 두 문서만 추가되었고 제품 코드·원고·발행 파일은 이번 턴에서 바꾸지 않았다.

2026-10-12 계획 작성 자체 검증: Python/PowerShell 안의 Python 예제 42개 AST 구문 검사 통과, 10개 task 확인, 86개 included ID와 각 실험 task 표의 완전 일치 확인, 미정 자리표시자·의도하지 않은 문자 없음 확인. 이는 제품 테스트 실행 결과가 아니다.

구현 방식은 아직 미선택이다. 계획 링크를 제시하고 사용자에게 계획 검토와 Subagent-driven/Native 선택을 한 번 요청한다. 이 계획은 86문항의 조건 대조와 실험별 독립 리뷰가 큰 비중이므로 Subagent-driven을 추천한다. Native도 지원하며 인터페이스/작업 순서를 동일하게 사용한다. 스킬의 Execution Handoff에 따라 계획 검토 응답을 받은 뒤 구현을 시작한다.

