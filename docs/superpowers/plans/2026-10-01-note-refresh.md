# 실험설명 문체·정보·그림 수정 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 실험설명 HTML을 생명과학의 다정한 말투와 새 그림으로 개선하고, 출처·연결 문제는 MD에 보존한다.

**Architecture:** 공통 학습 본문은 유지하고 manifest에서 MD 전용 토픽 메타데이터를 생성한다. 버전 2 출력에만 분리 규칙을 적용하여 기존 팩 검사를 유지한다. SVG 설명 그림과 설명 조각을 지속 가능한 저작 원본으로 저장하고 실험04를 다시 생성한다.

**Tech Stack:** 기존 Python 표준 라이브러리, pytest, HTML/CSS, SVG, KaTeX, Chrome.

**Spec:** `docs/superpowers/specs/2026-10-01-note-refresh-design.md`

## Global Constraints
- 본문·요약·힌트·그림 설명은 짧고 다정한 ‘~해요’체로 쓴다. 수식·신호 이름·직접 인용은 유지한다.
- HTML에는 ‘이 개념으로 풀 문제’와 출처가 나타나지 않는다. DOM·요약 패널·인쇄에도 포함하지 않는다.
- MD에는 토픽별 출처와 연결 문제를 보존한다.
- 설명용 회로·블록도는 SVG, 진리표는 텍스트 표로 만든다. HTML과 MD에서 같은 그림을 사용한다.
- 목차, 페이지 이동, 요약 패널과 MUX 조작 기능은 유지한다.
- 생명과학의 레이아웃·조작을 유지한다. 생명과학 원본 템플릿을 그대로 보존하고 조립 시 슬롯 값만 수정한다.
- 원자료·측정값·도출값의 차이와 논리 조건은 유지한다. 원문의 모순은 새 그림으로 조용히 덮지 않는다.
- 작업 경로: 기존 managed worktree `C:/Users/Hyunjun/.codex/worktrees/logic-lab-review-pack/논회실`의 `codex/logic-lab-review-pack` 브랜치. 원래 checkout으로 통합하지 않는다.
- 실행은 native. 현재 백업 폴더와 문제은행 증거는 수정·삭제·커밋하지 않는다.

## Review Focus
1. 기존 manifest에 출력 버전이 없음: 기존 팩을 새 규칙으로 잘못 거부하지 않는다. Task 1에서 legacy fixture 검사.
2. 출처/연결 문제가 없는 토픽: 빈 제목·구분자를 만들지 않는다. Task 1에서 빈 metadata 검사.
3. 보류·중복 문제: MD 연결 목록에 포함하지 않는다. Task 1에서 status filtering 검사.
4. 원문과 이상 회로의 극성·X 표기 불일치: 새 그림이 원문 정답인 것처럼 보이지 않는다. Task 2에서 DMUX·tri-state 대조.
5. 다크 모드·모바일·인쇄: 선·라벨·접속점과 회로 끝부분이 읽힌다. Task 3에서 화면 및 PDF 확인.

---

## 파일 구조
| 파일 | 역할 |
|---|---|
| `scripts/lab/review_pack/note_metadata.py` (신규) | manifest 기반 MD 메타데이터 생성·독립 검사 |
| `scripts/lab/review_pack/render.py` | v2 설명 HTML에서 출처·footer 안내 제외 |
| `scripts/lab/review_pack/html2md.py` | 토픽별 metadata 추가 변환 |
| `scripts/lab/review_pack/__main__.py` | build에서 manifest를 converter에 전달 |
| `scripts/lab/review_pack/checks.py`, `manifest.py` | v2 값과 메타데이터 검사, legacy 지원 |
| `.claude/skills/logic-lab-review-pack/SKILL.md`, `references/authoring.md` | 말투·그림·출력 분리 계약 |
| `docs/learning-pack-source/실험04/` (신규) | manifest, sections, problems, figures, evidence 및 저작안내 원본 |
| `tests/test_review_pack_note_metadata.py` (신규) | 출력 분리·누락·legacy 회귀 테스트 |
| `복습노트/실험04/` | 검증 후 재발행한 결과물 |
| `docs/verify/logic-lab-review-pack-note-refresh.md` (신규) | 내용·브라우저·그림 검증 결과 |

템플릿 HTML의 디자인 코드와 provenance hash는 바꾸지 않는다. FOOTER 슬롯을 note v2에서 빈 값으로 채운다. 출처 URL은 현재 refs와 같은 상대 경로·PDF page anchor를 유지한다.

### Task 1: HTML·MD 분리 출력과 검사

**Files:** 위 Python 6개 파일과 신규 metadata 테스트, 스킬 문서 2개.

**Interfaces:**
- `topic_metadata(manifest: dict) -> dict[str, str]`: 토픽 id별 MD 문자열. 출처와 포함 문제 링크를 manifest 순서로 생성한다.
- `check_note_metadata(manifest: dict, html_text: str, md_text: str) -> list[str]`: v2 HTML에서 금지 metadata 존재 및 MD 누락을 검사한다. legacy는 빈 오류 목록을 반환한다.
- `export_document(path, export=True, note_metadata=None) -> tuple[str, int]`: 기존 인자를 유지하고 article.topic 끝에 해당 metadata를 추가한다.
- `convert_pack(note_path, review_path, manifest=None)`: 기존 반환값 유지. manifest가 없으면 같은 폴더 manifest.json을 읽고, 없는 경우 기존 변환을 유지한다.

- [ ] **Step 1: 실패 테스트 작성.** 신규 테스트의 최소 핵심:

```python
from pathlib import Path
from tests.test_review_pack_manifest import fixture
from scripts.lab.review_pack.render import assemble
from scripts.lab.review_pack.html2md import convert_pack
from scripts.lab.review_pack.checks import check_pack

def test_note_metadata_only_in_md(tmp_path):
    m = fixture(); m['note_presentation_version'] = 2
    paths = assemble(m, Path('tests/fixtures/review_pack'), tmp_path/'stage',
                     Path('.claude/skills/logic-lab-review-pack/assets'))
    convert_pack(paths['note_html'], paths['review_html'], manifest=m)
    h = paths['note_html'].read_text(encoding='utf-8')
    d = paths['note_html'].with_suffix('.md').read_text(encoding='utf-8')
    assert 'class="sources"' not in h
    assert '출처와 문항목록.md에서' not in h
    assert '이 개념으로 풀 문제' not in h
    assert '출처:' in d and '#q-mux-001' in d
    assert check_pack(tmp_path/'stage') == []
    paths['note_html'].with_suffix('.md').write_text(
        d.replace('이 개념으로 풀 문제', '누락'), encoding='utf-8')
    assert check_pack(tmp_path/'stage')
```

추가 독립 사례는 같은 fixture의 topics[0].sources=[] / problems=[]에서 metadata 결과가 빈 문자열인 것, 문제 status='held'에서 링크가 없는 것, legacy fixture에서 기존 출처 HTML과 check_pack 성공이다. HTML의 sources 클래스뿐 아니라 main 안 ‘출처:’와 연결 문제 문구를 검사한다. fixture의 refs 없는 practice 문제에는 기존 review 출력 유지.

- [ ] **Step 2:** `python -m pytest tests/test_review_pack_note_metadata.py -v` 실행. 새 manifest 인자 또는 분리 출력 assertion에서 실패해야 한다.
- [ ] **Step 3: 최소 구현.** metadata의 생성 규칙:

```python
from urllib.parse import quote

def topic_metadata(manifest):
    sources = {s['id']: s for s in manifest['sources']}
    result = {}
    for t in manifest['topics']:
        rows = []
        links = []
        for p in manifest['problems']:
            if p['status'] == 'included' and t['id'] in p['topics']:
                title = str(p.get('title', p['id'])).replace('[', r'\[').replace(']', r'\]')
                target = quote(f"실험{manifest['experiment']:02d}_기출풀이.md", safe='')
                links.append(f"[{title}]({target}#{p['id']})")
        if links:
            rows.append('이 개념으로 풀 문제: ' + ' · '.join(links))
        refs = []
        for r in t['sources']:
            source = sources[r['source_id']]
            url = '../../' + quote(source['path'], safe='/')
            label = source['path'].replace('[', r'\[').replace(']', r'\]')
            if r.get('pdf_page'):
                url += f"#page={r['pdf_page']}"
                label += f" · PDF p{r['pdf_page']}"
            refs.append(f'[{label}]({url})')
        if refs:
            rows.append('출처: ' + ' · '.join(refs))
        result[t['id']] = '\n\n'.join(rows)
    return result
```

`manifest.py`는 필드 없음 또는 정수 2만 허용한다(bool 제외). render는 v2 note에서 refs(t)를 붙이지 않고 FOOTER=''로 한다. v2 fragment 안 metadata 문구/출처 클래스가 있으면 해당 토픽 id를 담은 ValueError로 거부한다. 저작자는 Task 2에서 본문 metadata를 제거한다. converter는 v2에만 topic_metadata를 전달하고 article 렌더 종료 직전에 삽입한다. checks는 manifest 기반으로 각 토픽 MD 구간에서 metadata 문자열을 확인하고 HTML main의 텍스트·sources 요소를 별도 검사한다. 기존 check_md의 학습 내용 보존 검사는 유지한다. 문서에 v2의 분리 규칙과 build 예시를 추가한다.
- [ ] **Step 4:** `python -m pytest tests/test_review_pack_note_metadata.py tests/test_review_pack_render.py tests/test_review_pack_md.py tests/test_review_pack_manifest.py -v` 실행. 모든 선택 테스트 PASS.
- [ ] **Step 5:** 수정 파일만 git add하고 `git commit -m "feat: separate note metadata from learning HTML"`.

### Task 2: 실험04 말투와 설명 그림 교체

**Files:** 신규 `docs/learning-pack-source/실험04/`, 스킬 문서 2개, 신규 `tests/test_review_pack_note_figures.py`.

**Interfaces:** 원본 run의 manifest/sections/problems/figures/evidence 파일 계약은 그대로 유지. 기존 `tmp/review-pack/실험04-learning-20261001`에서 시작하여 원본을 새 경로에 보존한다. manifest에 `note_presentation_version: 2`를 추가한다. bank snapshot·import index·34개 자산은 바이트 그대로 유지한다.

- [ ] **Step 1:** 기존 run과 최종 팩의 manifest 및 HTML을 대조하여 최종 수정 내용이 포함된 저작 원본을 확정한다. 새 폴더로 복사하고 과거 stage·임시 PDF·검증 pass 상태는 가져오지 않는다. checks는 전부 not_run으로 초기화한다. 최종에서 고친 한국어 문장과 template provenance를 복사본에 동기화한다.
- [ ] **Step 2: 그림 교체 실패 테스트 작성.**

```python
from pathlib import Path
from xml.etree import ElementTree as ET

def test_experiment4_has_redrawn_note_figures():
    root = Path('docs/learning-pack-source/실험04')
    names = ['mux2-gates', 'mux4-enable', 'demux4-gates',
             'decoder-routing', 'tristate-bus', 'lab-signal-flow']
    for name in names:
        path = root/'figures'/f'{name}.svg'
        tree = ET.parse(path)
        assert tree.getroot().get('viewBox')
        assert not any(n.tag.endswith('image') for n in tree.iter())
        assert any(n.tag.endswith('title') for n in tree.iter())
```

- [ ] **Step 3:** `python -m pytest tests/test_review_pack_note_figures.py -v` 실행. SVG 파일이 없어서 FAIL.
- [ ] **Step 4:** 8개 토픽의 본문·제목·요약·힌트를 한국어 ‘~해요’체로 다시 쓴다. 규칙의 예:

```html
<div class="layer eli5"><span class="layer-title">두 입력 중 하나를 골라요</span>
<p>S가 0이면 I0를, 1이면 I1을 골라요. 선택된 입력이 0이면 출력도 0이에요.</p></div>
<figure class="figure"><img src="figures/mux2-gates.svg"
alt="선택선 S와 그 반전 신호가 두 AND 경로를 열고 OR로 출력 Y를 만드는 회로">
<figcaption>선택선은 경로를 고르고, 데이터 입력은 출력값을 정해요.</figcaption></figure>
```

본문의 연결 문제 p와 출처 메타데이터는 제거한다. 원문 쪽수·판본 파일명 등 근거 안내는 MD로 옮기되 ‘이상값과 원문 답안이 달라요’ 같은 학습상 필요한 경고는 HTML에 남긴다. 모든 새 문장은 한국어로 작성한다.
- [ ] **Step 5:** 여섯 SVG를 직접 제작한다. mux2는 NOT+AND 2+OR, mux4는 네 주소 항과 enable 극성, demux4는 NOT 2+AND 4와 별도 출력, decoder는 00~11 one-hot 주소 신호, tri-state는 nOE=0 통과/nOE=1 Z와 공통 버스, lab은 실험1-1·2-1의 조작·관찰 신호 흐름이다. 각 그림은 `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 460" role="img"><title>…</title>…</svg>` 형식을 사용한다. 배경과 선의 대비를 보장하고 text는 최소 18px, 접속점은 circle, 비접속 교차는 분리/bridge, 출력 반전은 bubble로 표현한다. SVG마다 읽을 수 있는 설명과 원자료 대조 기록을 MD 원본에 남긴다.
- [ ] **Step 6:** 원문 설명 그림을 목록화하여 새 그림/텍스트 표 대응을 기록한다. 기존 note의 img가 PNG/JPG 또는 evidence 은행 이미지를 참조하지 않음을 검사한다. widget은 정적 표를 유지한다. 새 그림의 모든 출력을 `itertools.product((0,1), repeat=n)`으로 계산하여 본문 표와 대조한다. DMUX D=0의 0000과 원문 X, nOE=1의 Z와 active-High 제공 그림 차이를 명시한다.
- [ ] **Step 7:** 그림 테스트 PASS 후 SKILL.md와 authoring.md에 생명과학 content-rules.md:75–78 문체 및 설명 그림 재제작 규칙을 추가한다. 한국어 문체·표기·조건을 문장 단위로 자체 검토한다. 문체는 어미 regex로 통과 판정하지 않는다.
- [ ] **Step 8:** 원본·그림·문서·테스트만 git add하고 `git commit -m "docs: redraw experiment 4 learning explanations"`.

### Task 3: 실제 팩 생성·브라우저·인쇄 검증과 재발행

**Files:** `복습노트/실험04/`, `docs/verify/logic-lab-review-pack-note-refresh.md` 및 검증 스크린샷.

**Interfaces:** 기존 build/check/publish CLI를 사용한다. publish는 check_pack 및 원자료 hash, 브라우저/내용/원문 검토 상태와 generated_files 일치를 요구한다. 검토를 수행한 뒤에만 상태를 pass/self_review로 기록한다.

- [ ] **Step 1:** `python -m pytest tests -k review_pack -q` 실행. 실패 시 원인을 확인하고 관련 변경 회귀와 기존 기준선 실패를 구분한다.
- [ ] **Step 2:** PowerShell에서 새 stage로 빌드:

```powershell
python -m scripts.lab.review_pack build --root . --run docs/learning-pack-source/실험04 --stage tmp/review-pack/실험04-note-refresh-20261001-a
python -m scripts.lab.review_pack check --folder tmp/review-pack/실험04-note-refresh-20261001-a
```

stage 존재 오류이면 덮어쓰지 않고 다음 접미사를 쓴다. 실패한 build의 부분 stage를 publish하지 않는다.
- [ ] **Step 3:** 생성 HTML의 학습 main·요약·footer에서 metadata 부재, MD의 8토픽별 metadata 보존과 링크를 검사한다. 6 SVG와 해당 MD 참조가 같은 파일인지 확인한다. 기출풀이 원문·답안·증거 이미지가 이전 팩과 동일함을 대조한다.
- [ ] **Step 4:** native browser로 1280×900 및 375×812, 밝은/어두운 테마에서 8개 토픽과 모든 새 그림을 확인한다. 목차·이전/다음·요약·개념 링크·MUX 8조합을 조작한다. console 오류/깨진 그림/가로 넘침을 확인한다. 캡션과 문체를 화면에서 읽고 수정 사항이 있으면 새 stage로 다시 생성한다.
- [ ] **Step 5:** Chrome 인쇄 PDF를 생성해 페이지별 렌더로 그림의 선·라벨·오른쪽 경계·페이지 분할을 확인한다. 실험설명 인쇄에도 metadata가 없고, 기출풀이 인쇄에는 기존 풀이가 모두 남는지 확인한다. PDF는 검증 산출물로만 관리한다.
- [ ] **Step 6:** `docs/verify/logic-lab-review-pack-note-refresh.md`에 명령·결과·SVG 대조·화면·인쇄 검증과 제한을 기록한다. 실행 방식 native의 마지막 독립 리뷰는 requesting-code-review 절차에 따라 수행한다. 검토하지 않은 내용을 pass라고 기록하지 않는다.
- [ ] **Step 7:** 검토 결과를 저작 원본 checks에 반영하고 새로운 stage로 재생성한다. `check` 통과 후 publish:

```powershell
python -m scripts.lab.review_pack publish --root . --experiment 4 --stage tmp/review-pack/실험04-note-refresh-20261001-b
python -m scripts.lab.review_pack check --folder 복습노트/실험04
```

위 b는 최종 검토 stage를 가리키도록 맞춘다. 기존 팩은 publish가 백업한다. 실제 최종 위치의 상대 링크를 확인하고 user_files/백업은 보존한다.
- [ ] **Step 8:** 생성 팩·검증 문서와 최종 저작 원본만 선택해 커밋한다. `git status --short`를 확인하고 `git commit -m "docs: publish refreshed experiment 4 learning pack"`. 사용자에게 HTML/MD 링크, 검증 결과, commit을 전달한다. push·merge·원래 checkout 통합은 이 작업 범위에 포함하지 않는다.

## 계획 자체 검토
- spec의 문체: Task 2; HTML/MD 분리와 legacy: Task 1; 직접 그림 제작: Task 2; 화면 유지·검증·저장: Task 3.
- 메타데이터 생성과 검사 입력은 동일 manifest; HTML 학습 내용 보존 검사는 기존 check_md로 독립 유지한다.
- Review Focus 다섯 항목을 해당 task의 자동/수동 검증에 연결했다.
- 실행 시작 전 사용자의 계획 확인을 기다린다. 기존 native 방식을 재선택하도록 요구하지 않는다.
