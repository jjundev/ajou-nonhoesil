# 실험04 기출 문제지·해설지 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

이번 사용자의 기존 실행 선택은 **Native**다. `executing-plans`로 직접 구현하고 마지막에 독립 리뷰 1회를 수행한다. 계획 작성은 구현 승인이 아니며 사용자 계획 검토 후 시작한다.

**Goal:** 실험04 기출을 전자회로2 원본 템플릿의 문제지·해설지 HTML/MD로 분리하고 학습용 회로 그림을 별도 SVG/PNG로 재작성한다.

**Architecture:** 기존 문제은행 import·학습 manifest·stage/publish 흐름을 유지한다. 선택적인 review_presentation_version=2와 문항별 작성 JSON을 도입하고, 원본 템플릿 데이터 변환·그림 검증·MD 출력을 별도 모듈로 구성한다. 기존 팩과 실험설명은 기존 경로를 유지한다.

**Tech Stack:** Python 표준 라이브러리, pytest, 기존 Pretendard/KaTeX 0.16.11 번들, 직접 작성 SVG, 기존 PyMuPDF/Pillow 검증 도구, 설치된 Chrome. 브라우저 자동 검증에서 사용 가능한 Playwright를 선택적으로 사용하며 생성기의 런타임 의존성은 추가하지 않는다.

**Spec:** `docs/superpowers/specs/2026-10-01-question-workbook-design.md`.

## Global Constraints

- 적용 범위는 실험04의 현재 선별된 12문항이며 held 3문항은 계속 감사 기록에 남긴다.
- Native로 구현하고 Python 표준 라이브러리 기반 생성기를 유지한다. 그림 래스터화·브라우저 검증에 기존 검증 도구를 사용할 수 있다.
- 전자회로2 `workbook/templates/problem.html`과 `answer.html`을 바이트 그대로 복사한다. 생성 결과에서 데이터 삽입과 외부 자원 URL의 로컬 번들 치환만 허용한다.
- 실험설명의 생명과학 템플릿·본문·새 SVG·문체·MD 메타데이터를 유지한다.
- 문제은행·원자료·증거 자산·수입 고정 필드는 수정하지 않는다.
- 새 회로·블록도는 별도 SVG와 300dpi PNG로 저장하고 진리표·문장·수식은 텍스트로 작성한다.
- 문제지의 삽입 JSON·DOM·인쇄에는 해설·최종 답·풀이용 그림·답 노출 증거를 포함하지 않는다.
- 문제지·해설지의 ID·번호·순서·문제 조건은 동일하다. 기존 `기출풀이` 파일명과 문항 ID를 유지한다.
- 원문의 활성 극성·게이트 수·접속·반전·부품명·핀 이름을 보존한다. 판독 불확실성을 추측으로 해소하거나 그림 재제작만으로 verified로 승격하지 않는다.
- 템플릿의 A4 가로형(297mm × 210mm), 배치, 힌트 영역, 서체, 색, 축소·인쇄 동작을 유지한다.
- 브라우저에서 내용 넘침·잘림·깨진 그림·수식 오류가 있으면 발행하지 않는다. 수정은 내용 정리와 그림 크기 조정으로 하며 풀이 삭제나 임의 템플릿 변경을 하지 않는다.
- 새 파일은 별도 stage에서 검증하고 기존 publish의 백업·복구 절차로 발행한다. push·merge·원래 체크아웃 통합은 포함하지 않는다.

## Review Focus

1. 해설·notes·답 노출 증거가 문제 JSON의 새 필드나 이미지로 섞이는 입력: 문제지는 허용 필드만 직렬화하고 role/exposure 검증을 통과해야 한다. Task 2, 3, 4.
2. 한글·공백·퍼센트 인코딩 상대 경로와 JS 생성 문항 anchor: 문제·해설·노트·MD 링크가 실제 대상을 찾아야 한다. Task 3, 4, 6.
3. 긴 한국어 원문·넓은 진리표·여러 풀이 이미지·마지막 답이 있는 문항: A4에서 모두 보이고 넘침이면 발행되지 않아야 한다. Task 5, 6.
4. copied template 또는 SVG/PNG가 바뀌거나 검토 상태만 옛 pass인 입력: 해시와 검토 기록이 최종 파일에 결합되고 새 저작은 검증 상태를 재설정해야 한다. Task 1, 2, 7.
5. presentation version 없는 기존 팩 및 0문항·held-only 데이터: legacy 검사/MD가 유지되고 새로운 빈 데이터도 오류 없이 생성되며 실험04의 실발행에는 12문항이 있어야 한다. Task 1, 3, 4, 7.

---

## 실행 환경과 파일 구조

모든 명령의 작업 디렉터리는 `C:/Users/Hyunjun/.codex/worktrees/logic-lab-review-pack/논회실`이다. 계획 작성 시 HEAD는 `175a6f8`이고 백업 폴더 두 개만 untracked였다. 실행 시 다시 확인하고 다른 세션 변경을 덮어쓰지 않는다. 기존 linked worktree를 사용하며 새 worktree를 만들지 않는다. 현재 채팅 cwd `864c`에서 아래 명령을 실행하지 않는다.

```powershell
git status --short
git branch --show-current
git log -1 --oneline
python --version
python -m pytest tests -k review_pack -n 0 -q
```

pytest.ini의 병렬 실행 기본값을 `-n 0`으로 비활성화해 Chrome·출력 파일 경쟁을 피한다. 테스트 실패를 기준선으로 기록하고 이 기능 때문에 생긴 실패와 분리한다.

| 파일 | 책임 |
|---|---|
| `.claude/skills/logic-lab-review-pack/assets/workbook/problem.html`, `answer.html`, `provenance.json` | 전자회로2 원본 스냅샷과 해시 |
| `scripts/lab/review_pack/manifest.py` | 표시 버전·새 파일명·작성 JSON 경로 계약 |
| `scripts/lab/review_pack/workbook_content.py` | 작성 JSON 로드·검증과 템플릿 payload 변환 |
| `scripts/lab/review_pack/workbook_figures.py` | 재작성 그림 기록·출처·용도·해시 검사 |
| `scripts/lab/review_pack/workbook_render.py` | 원본 템플릿 주입·로컬 자원 치환·payload 읽기 |
| `scripts/lab/review_pack/workbook_md.py` | payload의 교육 내용을 MD로 출력하고 독립적으로 보존 검사 |
| `scripts/lab/review_pack/workbook_checks.py` | 두 payload와 manifest·그림·MD의 일치 검사 |
| `scripts/lab/review_pack/render.py`, `html2md.py`, `checks.py`, `bank_asset_checks.py`, `__main__.py`, `publish.py` | version=2 분기와 기존 stage/publish 통합 |
| `docs/learning-pack-source/실험04/workbook/<id>.json` | 현재 included 12문항의 문제·힌트·단계별 풀이 |
| `docs/learning-pack-source/실험04/redraw_questions.py`, `figures/questions/`, `figures/solutions/`, `figures/redraw-manifest.json` | 재현 가능한 직접 그림 작성과 기록 |
| `.claude/skills/logic-lab-review-pack/references/workbook.md` | 새 작성 계약과 실사용 예 |
| `tests/_workbook_fixture.py`, `tests/test_review_pack_workbook_*.py` | 새 계약·출력·보존·실제 인쇄 회귀 |
| `docs/verify/logic-lab-review-pack-question-workbook.md` | 최종 검증 명령·대상 해시·화면·인쇄·미해결 |

저작 원본과 문제은행을 분리한다. `docs/learning-pack-source/실험04/evidence/`, `authoring-index.json`의 고정 필드와 은행 JSON은 수정하지 않는다.

## 확정 인터페이스

함수·필드 이름은 아래를 기준으로 모든 task에 동일하게 사용한다.

```python
# manifest.py: 기존 호출은 output_names(experiment) 그대로 유지
def output_names(experiment: int, *, review_presentation_version: int | None = None) -> dict[str, str]:
    # legacy: note_html/note_md/review_html/review_md
    # v2: legacy 키 + question_html/question_md
    base = config.experiment_folder_name(experiment)
    names = {f'{kind}_{ext}': f'{base}_{label}.{ext}'
             for kind, label in [('note', '실험설명'), ('review', '기출풀이')]
             for ext in ('html', 'md')}
    if review_presentation_version == 2:
        names.update({f'question_{ext}': f'{base}_기출문제.{ext}' for ext in ('html', 'md')})
    return names

# workbook_content.py
# canonical row = 작성 JSON + manifest에서 가져온 id/title/number/kind/section/topics/sources
def load_workbook_content(manifest: dict, run: Path) -> list[dict]:
    """included 순서로 로드; 계약·자원 오류면 ValueError; 입력을 변경하지 않는다."""

def build_workbook_data(manifest: dict, content: list[dict], mode: str) -> dict:
    """mode='problems'|'answers'; {meta, problems}; 문제지에는 solution/notes가 없다."""

# workbook_figures.py
def check_redrawn_figures(folder: Path, manifest: dict, *, require_review: bool = False) -> list[str]:
    """figure_manifest의 경로·파일·해시·원문 연결·role/exposure·검토 상태 검사."""

# workbook_render.py
def render_workbook_html(data: dict, assets: Path) -> str:
    """mode에 맞는 원본 템플릿을 선택; 해시 검사; 데이터 주입과 URL 치환."""

def read_workbook_payload(path: Path) -> dict:
    """id=workbook-data인 application/json script 하나를 엄격하게 읽는다."""

# workbook_md.py
def write_workbook_md(data: dict, manifest: dict, path: Path) -> Path:
    """같은 data에서 MD 출력; answers에는 문항별 출처·개념 링크·held 기록."""

def check_workbook_md(data: dict, manifest: dict, path: Path) -> list[str]:
    """교육 텍스트 leaf·원래 TeX·표 셀·ID·이미지·상대 링크를 독립 검사."""

# workbook_checks.py
def check_workbook_pack(folder: Path, manifest: dict) -> list[str]:
    """HTML payload 쌍·manifest·그림·MD 검사. browser pass를 대신하지 않는다."""
```

위 인터페이스 블록은 문서용 서명이다. 실제 구현은 아래 task의 행동·검증 계약을 모두 충족한다. 함수는 stub 상태로 커밋하지 않는다.

### Task 1: 원본 템플릿 스냅샷과 호환 가능한 작성 계약

**Files:**
- Create: `.claude/skills/logic-lab-review-pack/assets/workbook/problem.html`, `answer.html`, `provenance.json`.
- Modify: `scripts/lab/review_pack/manifest.py:12`, `validate_manifest`의 version·included fragment 분기.
- Create: `tests/_workbook_fixture.py`, `tests/test_review_pack_workbook_contract.py`.
- Modify: `tests/test_review_pack_manifest.py`.

**Interfaces:** Consumes 기존 `validate_manifest(data)`와 legacy fixture. Produces 위 `output_names` 확장, `review_presentation_version=2`, `figure_manifest`, `problems[].workbook_fragment` 계약 및 `create_workbook_run(tmp_path) -> tuple[dict, Path]` 테스트 helper.

- [x] **Step 1: 계약 실패 테스트 작성.** 기존 fixture 기반 새 helper를 아래처럼 만든다. 실제 결과 파일을 만들지 않고 테스트 RUN만 생성한다.

```python
# tests/_workbook_fixture.py
import json
import shutil
from pathlib import Path
from tests.test_review_pack_manifest import fixture

def create_workbook_run(tmp_path):
    run = tmp_path/'run'
    shutil.copytree(Path('tests/fixtures/review_pack'), run)
    m = fixture()
    m['review_presentation_version'] = 2
    m['figure_manifest'] = 'figures/redraw-manifest.json'
    m['checks'] = dict.fromkeys(('source_visual', 'content', 'independent', 'browser'), 'not_run')
    p = m['problems'][0]
    p['workbook_fragment'] = f'workbook/{p["id"]}.json'
    p['title'] = '문항 제목'
    authored = dict(original='<p>문제를 풀어 보시오.</p>', conditions='<p>S=0</p>',
        ask='<p>Y를 구하시오.</p>', problem_figures=[], hints=[dict(label='경로', html='<p>선택 경로를 보세요.</p>')],
        solution=dict(steps=[dict(label='선택', html='<p>정답 전용 문구</p>')], answer='<p>Y=I0</p>'),
        notes=['해설 전용 대조 기록'])
    (run/'workbook').mkdir()
    (run/p['workbook_fragment']).write_text(json.dumps(authored, ensure_ascii=False), encoding='utf-8')
    (run/'figures').mkdir(exist_ok=True)
    (run/m['figure_manifest']).write_text('{"schema_version":1,"figures":[]}', encoding='utf-8')
    (run/'manifest.json').write_text(json.dumps(m, ensure_ascii=False), encoding='utf-8')
    return m, run
```

```python
# tests/test_review_pack_workbook_contract.py
from pathlib import Path
import hashlib
import json
import pytest
from tests._workbook_fixture import create_workbook_run
from tests.test_review_pack_manifest import fixture
from scripts.lab.review_pack.manifest import output_names, validate_manifest

def test_v2_names_and_legacy():
    assert set(output_names(4)) == {'note_html','note_md','review_html','review_md'}
    names = output_names(4, review_presentation_version=2)
    assert names['question_html'] == '실험04_기출문제.html'
    assert names['review_html'] == '실험04_기출풀이.html'
    assert validate_manifest(fixture()) == []

@pytest.mark.parametrize('version', [True, '2', 1, 3])
def test_reject_invalid_version(tmp_path, version):
    m, run = create_workbook_run(tmp_path)
    m['review_presentation_version'] = version
    assert validate_manifest(m)

def test_modern_requires_workbook_path(tmp_path):
    m, run = create_workbook_run(tmp_path)
    del m['problems'][0]['workbook_fragment']
    assert validate_manifest(m)
    m['problems'][0]['workbook_fragment'] = '../escape.json'
    assert validate_manifest(m)

def test_snapshot_matches_provenance():
    root = Path('.claude/skills/logic-lab-review-pack/assets/workbook')
    provenance = json.loads((root/'provenance.json').read_text(encoding='utf-8'))
    for name, digest in provenance['sha256'].items():
        assert hashlib.sha256((root/name).read_bytes()).hexdigest() == digest
```

- [x] **Step 2: 실패 확인.** `python -m pytest tests/test_review_pack_workbook_contract.py -n 0 -q`. 새 인자 및 snapshot 부재 때문에 FAIL이어야 한다.
- [x] **Step 3: 원본 두 파일을 복사하고 provenance 저장.** 아래 스냅샷 코드는 프로젝트 runtime 파일이 아니라 이번 구현에서 실행할 준비 명령이다. 원본이 계획 당시 hash와 달라졌으면 먼저 diff를 읽고 provenance의 실제 값으로 문서를 갱신한다.

```python
from pathlib import Path
import hashlib
import json
import shutil
src = Path('C:/Users/Hyunjun/Desktop/현준대학/26-2/ajou-electronic-circuits-2/workbook/templates')
dst = Path('.claude/skills/logic-lab-review-pack/assets/workbook')
dst.mkdir(parents=True, exist_ok=True)
for name in ('problem.html', 'answer.html'):
    shutil.copyfile(src/name, dst/name)
record = dict(source=str(src), sha256={n: hashlib.sha256((dst/n).read_bytes()).hexdigest()
              for n in ('problem.html','answer.html')})
(dst/'provenance.json').write_text(json.dumps(record, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
```

- [x] **Step 4: version·file 계약 구현.** `output_names`는 인터페이스 블록의 코드로 확장한다. 아래 조건을 validate_manifest의 included 검사에 반영한다. figure_manifest는 v2에 반드시 필요하며 legacy에는 요구하지 않는다. 모든 version 검사는 bool을 int로 허용하지 않는다.

```python
modern = data.get('review_presentation_version') == 2
if 'review_presentation_version' in data and (type(data['review_presentation_version']) is not int or not modern):
    errors.append('review_presentation_version must be 2 or absent')
if modern and not safe_relative(data.get('figure_manifest')):
    errors.append('unsafe/missing figure_manifest')
# 기존 included 문항 검사 중 fragment 부분을 아래로 교체
field = 'workbook_fragment' if modern else 'fragment'
if p.get('status') == 'included' and not safe_relative(p.get(field)):
    errors.append(ident + ': unsafe/missing ' + field)
```

- [x] **Step 5: PASS 확인 및 commit.** `python -m pytest tests/test_review_pack_workbook_contract.py tests/test_review_pack_manifest.py -n 0 -q`. 선택한 위 파일만 stage하고 `git commit -m "feat: add workbook presentation contract and template snapshots"`.

### Task 2: 작성 JSON과 재작성 그림을 검증하고 payload로 변환

**Files:**
- Create: `scripts/lab/review_pack/workbook_content.py`, `workbook_figures.py`.
- Create: `tests/test_review_pack_workbook_content.py`, `tests/test_review_pack_workbook_figures.py`.
- Modify: `tests/_workbook_fixture.py`에 아래 그림 helper 추가.

**Interfaces:** Consumes Task 1 manifest와 작성 JSON. Produces `load_workbook_content`, `build_workbook_data`, `check_redrawn_figures`; 테스트 helper `add_redrawn_figure(m, run, *, role='problem', exposure='none') -> dict`.

- [ ] **Step 1: 누출·입력·변조 실패 테스트 작성.** 다음 실제 helper와 테스트를 추가한다.

```python
def add_redrawn_figure(m, run, *, role='problem', exposure='none'):
    import hashlib
    p = m['problems'][0]
    folder = 'questions' if role == 'problem' else 'solutions'
    svg = f'figures/{folder}/diagram.svg'
    png = f'figures/{folder}/diagram.png'
    (run/svg).parent.mkdir(parents=True, exist_ok=True)
    (run/svg).write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 100"><title>S入力</title><path d="M0 50 H200"/></svg>', encoding='utf-8')
    # 표준 라이브러리만으로 유효한 2×1 RGB PNG 테스트 파일 작성
    import struct, zlib
    def chunk(kind, body):
        return struct.pack('!I', len(body))+kind+body+struct.pack('!I', zlib.crc32(kind+body)&0xffffffff)
    raw = b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR', struct.pack('!2I5B',2,1,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(b'\x00'+b'\xff'*6))+chunk(b'IEND',b'')
    (run/png).write_bytes(raw)
    row = dict(id='f1', question_id=p['id'], role=role, svg=svg, png=png,
        svg_sha256=hashlib.sha256((run/svg).read_bytes()).hexdigest(),
        png_sha256=hashlib.sha256(raw).hexdigest(), w_mm=100.0, h_mm=50.0,
        source_asset_ids=[], source_refs=p['sources'], derivation='입력 조건에서 직접 작성',
        answer_exposure=exposure, review_status='not_run', review_notes='검토 전')
    (run/m['figure_manifest']).write_text(json.dumps(dict(schema_version=1,figures=[row]),ensure_ascii=False),encoding='utf-8')
    return row
```

2×1 fixture는 파일 계약 테스트에만 사용하고 실제 PNG 해상도 검증은 Task 5에서 한다.

```python
import copy
import json
import pytest
from scripts.lab.review_pack.workbook_content import load_workbook_content, build_workbook_data
from scripts.lab.review_pack.workbook_figures import check_redrawn_figures
from tests._workbook_fixture import create_workbook_run, add_redrawn_figure

def test_problem_projection_excludes_answers_and_notes(tmp_path):
    m, run = create_workbook_run(tmp_path)
    before = copy.deepcopy(m)
    content = load_workbook_content(m, run)
    problem = build_workbook_data(m, content, 'problems')
    answer = build_workbook_data(m, content, 'answers')
    assert m == before
    assert 'solution' not in problem['problems'][0]
    assert 'notes' not in problem['problems'][0]
    assert '정답 전용 문구' not in json.dumps(problem, ensure_ascii=False)
    assert '해설 전용 대조 기록' not in json.dumps(problem, ensure_ascii=False)
    assert problem['problems'][0]['html'] == answer['problems'][0]['html']
    assert answer['problems'][0]['solution']['answer'] == '<p>Y=I0</p>'

@pytest.mark.parametrize('html', ['<script>1</script>', '<img onerror="alert(1)" src="x">',
    '<a href="javascript:alert(1)">x</a>', '<svg><script>1</script></svg>',
    '<div style="background:url(evidence/assets/answer.png)">x</div>'])
def test_active_or_hidden_resource_refused(tmp_path, html):
    m, run = create_workbook_run(tmp_path)
    path = run/m['problems'][0]['workbook_fragment']
    obj = json.loads(path.read_text(encoding='utf-8'))
    obj['original'] = html
    path.write_text(json.dumps(obj), encoding='utf-8')
    with pytest.raises(ValueError): load_workbook_content(m, run)

def test_duplicate_json_keys_fail(tmp_path):
    m, run = create_workbook_run(tmp_path)
    (run/m['problems'][0]['workbook_fragment']).write_text('{"original":"x","original":"y"}', encoding='utf-8')
    with pytest.raises(ValueError): load_workbook_content(m, run)

def test_solution_figure_cannot_be_used_as_problem(tmp_path):
    m, run = create_workbook_run(tmp_path)
    add_redrawn_figure(m, run, role='solution', exposure='present')
    path = run/m['problems'][0]['workbook_fragment']
    obj = json.loads(path.read_text(encoding='utf-8')); obj['problem_figures'] = ['f1']
    path.write_text(json.dumps(obj), encoding='utf-8')
    with pytest.raises(ValueError): load_workbook_content(m, run)

def test_changed_svg_or_unreviewed_figure_fails(tmp_path):
    m, run = create_workbook_run(tmp_path)
    row = add_redrawn_figure(m, run)
    assert check_redrawn_figures(run, m) == []
    assert check_redrawn_figures(run, m, require_review=True)
    (run/row['svg']).write_text('<svg/>', encoding='utf-8')
    assert check_redrawn_figures(run, m)
```

- [ ] **Step 2: FAIL 확인.** `python -m pytest tests/test_review_pack_workbook_content.py tests/test_review_pack_workbook_figures.py -n 0 -q`; 새 모듈이 없어 collection FAIL.
- [ ] **Step 3: 엄격 로드와 그림 기록 검사 구현.** JSON은 `_unique_json_object`로 읽는다. 새 authored JSON은 지정된 7키만 허용한다. original/conditions/ask는 str, hints는 label/html 및 선택 formula(str|list[str]), solution은 steps/answer, notes는 list[str], problem_figures는 list[str]. steps는 label/html dict 목록이며 included 문항은 steps와 answer 중 하나 이상 있어야 한다. 허용되지 않은 키·unknown figure·중복 figure ID·잘못된 번호형·NaN/무한대·음수 크기·경로 탈출은 ValueError로 실패시킨다.

```python
# workbook_content.py의 안전한 JSON 로드에 사용
import json
from pathlib import Path
from .question_bank import _unique_json_object

def _strict_json(path):
    def bad_constant(value):
        raise ValueError('Nonfinite JSON value: ' + value)
    return json.loads(Path(path).read_text(encoding='utf-8-sig'),
                      object_pairs_hook=_unique_json_object, parse_constant=bad_constant)

def _within(folder, relative):
    from .manifest import safe_relative
    if not safe_relative(relative): raise ValueError('Unsafe authored path: ' + str(relative))
    base = Path(folder).resolve(); path = base/relative
    if path.is_symlink() or any(p.is_symlink() for p in path.parents if p != base):
        raise ValueError('Symlink authored path')
    if not path.resolve().is_relative_to(base): raise ValueError('Path outside run')
    return path
```

workbook_figures는 workbook_content의 `_within`/`_strict_json` helper를 사용한다. workbook_content에서 workbook_figures를 필요로 하는 import는 load_workbook_content 함수 안에서 수행해 순환 import를 피한다. 파일 크기/숫자 검사는 bool과 유한하지 않은 값을 제외한다. SVG는 ElementTree로 파싱해 script/image/foreignObject 및 이벤트 속성·외부 href·CSS url/import를 금지한다. 원문 비트맵을 SVG 안에 감싼 그림은 허용하지 않는다. PNG 시그니처와 SVG/PNG/인쇄 크기의 가로세로 비율이 일치하는지 확인한다. source_refs는 manifest에 있는 source_id/페이지를 사용한다. bank_import가 있으면 source_asset_ids의 소속 문항과 원문 asset hash를 index/evidence로 대조하고 problem 그림은 safe_problem_asset_ids만 참조한다. 은행 수입 문항의 독립 도출 solution은 source_refs와 derivation이 필수다. 은행이 없는 practice fixture는 source_refs=[]를 허용하되 derivation은 필수다. JSON 필드 검사는 구체적인 위치를 오류에 포함한다.

- [ ] **Step 4: HTML 조각 검사와 payload 허용 목록 구현.** Parser로 교육 마크업을 읽는다. script/style/iframe/object/embed/svg, on* 이벤트, javascript URL을 거부한다. 조각 style은 해설 img의 `max-width:100%;height:auto`만 허용하며 CSS 배경 자원은 금지한다. img는 registry의 해당 문항 그림만 허용한다. 문제 텍스트 영역에는 solution role 그림이나 evidence 원문을 허용하지 않는다. 링크는 같은 팩의 개념/대조 링크만 생성기가 추가하고 사용자 조각의 링크는 로컬 상대 경로로 제한한다.

```python
# workbook_content.py의 projection 핵심: 원본 dict를 통째로 복사하지 않는다
def _project_row(row, mode):
    entry = dict(id=row['id'], kind=row['kind'], number=row['number'],
        title=row['title'], section=row['section'], book_page=None,
        difficulty=None, sol=None, original_lang='ko', depends_on=[],
        html=dict(original=row['original'],conditions=row['conditions'],ask=row['ask']),
        figures=row['figures'], hints=row['hints'])
    if mode == 'answers':
        entry['solution'] = dict(steps=[dict(s) for s in row['solution']['steps']],
                                 answer=row['solution']['answer'])
    return entry
```

canonical row의 figures는 registry에서 `{src: png, w_mm, h_mm}`로 만들고 solution 단계의 img는 SVG/PNG 실제 경로를 갖는다. build_workbook_data는 mode를 먼저 검증하고 번호를 included 순서의 1부터 부여한다. notes·분류·답안 상태·개념 링크를 해설 단계로 조립한다. 본문과 최종 답을 임의로 계산·변경하지 않는다. 0문항에는 meta.total=0과 빈 problems를 반환한다.

- [ ] **Step 5: PASS 확인 및 commit.** `python -m pytest tests/test_review_pack_workbook_contract.py tests/test_review_pack_workbook_content.py tests/test_review_pack_workbook_figures.py -n 0 -q`; 모두 PASS. 위 소스/테스트만 stage하고 `git commit -m "feat: validate authored workbook content and redrawn figures"`.

### Task 3: 원본 템플릿으로 HTML을 생성하고 동일 데이터로 MD 작성

**Files:**
- Create: `scripts/lab/review_pack/workbook_render.py`, `workbook_md.py`.
- Create: `tests/test_review_pack_workbook_render.py`, `tests/test_review_pack_workbook_md.py`.

**Interfaces:** Consumes Task 2 payload. Produces `render_workbook_html`, `read_workbook_payload`, `write_workbook_md`, `check_workbook_md`. html2md.export_document는 교육 조각의 MD 렌더링에만 사용하고 dynamic workbook HTML 전체에는 사용하지 않는다.

- [ ] **Step 1: 주입·이스케이프·MD 보존 실패 테스트 작성.**

```python
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

def test_md_retains_table_math_and_all_solution_steps(tmp_path):
    m, run = create_workbook_run(tmp_path)
    data = build_workbook_data(m, load_workbook_content(m,run), 'answers')
    p = data['problems'][0]
    p['solution']['steps'].append(dict(label='검산',html='<p>$$Y=I_0$$</p><table><tr><th>S</th><th>Y</th></tr><tr><td>0</td><td>I0</td></tr></table>'))
    path = write_workbook_md(data,m,tmp_path/'실험04_기출풀이.md')
    text = path.read_text(encoding='utf-8')
    assert '$$Y=I_0$$' in text and '| 0 | I0 |' in text
    assert '정답 전용 문구' in text
    assert f'<a id="{p["id"]}"></a>' in text
    assert check_workbook_md(data,m,path) == []
    path.write_text(text.replace('정답 전용 문구',''),encoding='utf-8')
    assert check_workbook_md(data,m,path)

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
```

- [ ] **Step 2: FAIL 확인.** `python -m pytest tests/test_review_pack_workbook_render.py tests/test_review_pack_workbook_md.py -n 0 -q`.
- [ ] **Step 3: 주입 구현.** 원본 snapshot hash를 provenance로 검사한 뒤 아래 핵심을 적용한다. generated HTML을 read_workbook_payload로 읽을 때 script id/mime 중복과 JSON 중복 키도 거부한다. 원본 외부 URL이 예상 목록 밖이면 로컬화 실패로 오류를 낸다.

```python
import json
TOKEN = '__WORKBOOK_DATA__'
URL_MAP = {
 'https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css': 'assets/vendor/pretendard/pretendard.css',
 'https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css': 'assets/vendor/katex/katex.min.css',
 'https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js': 'assets/vendor/katex/katex.min.js',
 'https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js': 'assets/vendor/katex/auto-render.min.js',
}
def _inject(template, data):
    if template.count(TOKEN) != 1: raise ValueError('Expected exactly one workbook data slot')
    text = template.replace(TOKEN, json.dumps(data,ensure_ascii=False,allow_nan=False).replace('<','\\u003c'))
    for remote, local in URL_MAP.items(): text = text.replace(remote,local)
    return text
```

- [ ] **Step 4: MD를 작성 데이터에서 생성하고 독립 검사 구현.** 교육 HTML 조각은 아래 helper로 기존 변환기를 재사용한다. 출력 본문의 문항 anchor는 원래 ID이며 HTML 링크의 학습 파일 suffix만 .md로 변경한다. problem payload의 original/conditions/ask/문제 그림/힌트만 출력하고 answers는 추가 steps/answer·출처·개념 링크·notes·held 기록을 출력한다. 표는 모든 셀 순서와 빈 출력 셀을 유지한다.

```python
from pathlib import Path
from tempfile import TemporaryDirectory
from .html2md import export_document

def _fragment_md(text):
    with TemporaryDirectory(prefix='logic-workbook-md-') as directory:
        path = Path(directory)/'fragment.html'
        path.write_text('<main>'+text+'</main>',encoding='utf-8')
        return export_document(path,export=False)[0].strip()
```

check_workbook_md는 작성 함수를 다시 호출해 전체 문자열만 비교하지 않는다. payload HTML의 text leaf·수식 문자열·표 셀을 Parser로 독립 순회하고 MD에서 보존을 검사한다. figure.src와 단계 img의 상대 URL을 확인하고 이미지 파일이 존재해야 한다. notes와 감사 필드는 answers에서만 검사한다. 파일명에 공백/한글/퍼센트가 있으면 quote/unquote로 처리하고 로컬 anchor를 MD의 `<a id>`로 검사한다. source PDF는 기존 규칙대로 stage 외부 링크로 예외 처리한다.

- [ ] **Step 5: PASS 확인 및 commit.** `python -m pytest tests/test_review_pack_workbook_render.py tests/test_review_pack_workbook_md.py -n 0 -q`; `git commit -m "feat: render workbook sheets and preserve markdown from shared data"`.

### Task 4: 기존 build/check/publish에 새 표시 방식 연결

**Files:**
- Modify: `scripts/lab/review_pack/render.py`, `html2md.py`, `checks.py`, `bank_asset_checks.py`, `__main__.py`, `publish.py`.
- Create: `scripts/lab/review_pack/workbook_checks.py`, `tests/test_review_pack_workbook_flow.py`.
- Modify: `tests/test_review_pack_bank_assets.py`, `tests/test_review_pack_publish.py`.

**Interfaces:** Consumes Task 1~3 functions. Produces `check_workbook_pack(folder,manifest)`와 확장된 assemble 반환값(question_html/question_md 추가). 기존 CLI 인자와 publish destination은 동일하다.

- [ ] **Step 1: 생성·legacy·누출·실제 payload anchor 테스트 작성.**

```python
import json
from pathlib import Path
from scripts.lab.review_pack.render import assemble
from scripts.lab.review_pack.html2md import convert_pack
from scripts.lab.review_pack.checks import check_pack
from scripts.lab.review_pack.workbook_render import read_workbook_payload
from tests._workbook_fixture import create_workbook_run

ASSETS = Path('.claude/skills/logic-lab-review-pack/assets')

def test_modern_build_checks_dynamic_ids_and_three_md(tmp_path):
    m, run = create_workbook_run(tmp_path)
    stage = tmp_path/'stage'; paths = assemble(m,run,stage,ASSETS)
    convert_pack(paths['note_html'],paths['review_html'],manifest=m)
    assert paths['question_html'].is_file()
    for label in ('실험설명','기출문제','기출풀이'):
        assert (stage/f'실험04_{label}.md').is_file()
    a = read_workbook_payload(paths['review_html'])
    q = read_workbook_payload(paths['question_html'])
    assert [p['id'] for p in a['problems']] == [p['id'] for p in q['problems']]
    assert check_pack(stage) == []
    # canonical JSON 본문은 스크립트 내부이므로 정적 article 검사를 적용하지 않는다
    assert '<article class="card"' not in paths['review_html'].read_text(encoding='utf-8')

def test_tampered_question_payload_rejected(tmp_path):
    from scripts.lab.review_pack.workbook_render import render_workbook_html
    m, run = create_workbook_run(tmp_path)
    stage = tmp_path/'stage'; paths = assemble(m,run,stage,ASSETS)
    convert_pack(paths['note_html'],paths['review_html'],manifest=m)
    data = read_workbook_payload(paths['question_html'])
    data['problems'][0]['solution'] = {'answer':'exposed'}
    paths['question_html'].write_text(render_workbook_html(data,ASSETS),encoding='utf-8')
    assert check_pack(stage)
```

아래 변형 테스트로 실제 payload 순서·ID·조건·그림의 불일치를 검사한다. 각 경우 동일한 작성 데이터를 사용해 문제와 해설을 구성한 후 생성물을 변조하므로 표시 계약을 검사한다.

```python
import copy
import pytest
from scripts.lab.review_pack.workbook_render import render_workbook_html

@pytest.mark.parametrize('change', ['order','duplicate','conditions','encoded_path','solution_image','foreign'])
def test_payload_mutations_rejected(tmp_path,change):
    m, run = create_workbook_run(tmp_path)
    p2 = copy.deepcopy(m['problems'][0]); p2['id'] += '-second'
    p2['workbook_fragment'] = f'workbook/{p2["id"]}.json'
    (run/p2['workbook_fragment']).write_bytes((run/m['problems'][0]['workbook_fragment']).read_bytes())
    m['problems'].append(p2)
    paths = assemble(m,run,tmp_path/'stage',ASSETS)
    convert_pack(paths['note_html'],paths['review_html'],manifest=m)
    key = 'review_html' if change == 'conditions' else 'question_html'
    data = read_workbook_payload(paths[key])
    if change == 'order': data['problems'].reverse()
    if change == 'duplicate': data['problems'][1]['id'] = data['problems'][0]['id']
    if change == 'conditions': data['problems'][0]['html']['conditions'] = '<p>S=1</p>'
    if change == 'encoded_path':
        data['problems'][0]['figures'] = [dict(src='%2e%2e/outside.png',w_mm=10,h_mm=10)]
    if change == 'solution_image':
        data['problems'][0]['figures'] = [dict(src='figures/solutions/fake.png',w_mm=10,h_mm=10)]
    if change == 'foreign':
        data['problems'].append(dict(data['problems'][0],id='q-held'))
    paths[key].write_text(render_workbook_html(data,ASSETS),encoding='utf-8')
    assert check_pack(tmp_path/'stage')
```

은행 fixture는 `tests/test_review_pack_bank_assets.py:asset_pack`을 사용해 기존 exposed 이미지의 이름/hash를 바꿔 문제 그림으로 쓰는 경우와 source_asset_ids를 다른 문항에 결합하는 경우를 아래 테스트로 거부한다. add_redrawn_figure와 create_workbook_run을 쓴 일반 RUN에 bank_import를 임의 복사하지 말고 asset_pack이 만든 실제 은행 수입 manifest를 v2로 전환한 뒤 기록을 추가한다.

```python
def test_exposed_bank_asset_cannot_author_problem_diagram(tmp_path):
    from tests.test_review_pack_bank_assets import asset_pack
    from tests._workbook_fixture import add_redrawn_figure
    from scripts.lab.review_pack.workbook_figures import check_redrawn_figures
    run, m = asset_pack(tmp_path,exposure='present')
    m['review_presentation_version'] = 2
    m['figure_manifest'] = 'figures/redraw-manifest.json'
    row = add_redrawn_figure(m,run)
    bank = json.loads((run/m['bank_import']['snapshot_path']).read_text(encoding='utf-8'))
    row['source_asset_ids'] = [bank['assets'][0]['id']]
    (run/m['figure_manifest']).write_text(json.dumps(dict(schema_version=1,figures=[row])),encoding='utf-8')
    assert check_redrawn_figures(run,m)
```

- [ ] **Step 2: FAIL 확인.** `python -m pytest tests/test_review_pack_workbook_flow.py -n 0 -q`; question_html 반환·새 분기 부재로 FAIL.
- [ ] **Step 3: assemble를 분기한다.** v2 작성 데이터/그림 검사를 출력 디렉터리 생성보다 먼저 실행한다. 기존 note 렌더링과 audit 생성은 유지하고 legacy review 생성만 v2에서 건너뛴다. assets/evidence/figures 복사 이후 아래 동작을 넣는다. paths['question_md']/['review_md']도 반환한다.

```python
if manifest.get('review_presentation_version') == 2:
    names = output_names(manifest['experiment'],review_presentation_version=2)
    content = load_workbook_content(manifest,run)
    for mode, key in [('problems','question'),('answers','review')]:
        data = build_workbook_data(manifest,content,mode)
        path = out/names[key+'_html']
        path.write_text(render_workbook_html(data,assets),encoding='utf-8')
        paths[key+'_html'] = path
        paths[key+'_md'] = write_workbook_md(data,manifest,out/names[key+'_md'])
```

실제로 preflight content 로드는 함수 앞에서 한 번만 하고 여기서 재사용한다. read_fragment의 NOTE_HREF/REVIEW_HREF와 note navigation을 유지하고 v2 note navigation에 기출문제 링크를 추가한다. footer/메타데이터 분리는 note_presentation_version의 기존 동작을 유지한다.

- [ ] **Step 4: 검사·변환 분기 구현.** convert_pack은 v2에서 note만 정적 변환하고 workbook MD 파일이 이미 있음을 확인하며 빈 review MD로 덮어쓰지 않는다. check_pack은 note의 기존 검사·note_metadata를 그대로 수행하고 v2 review/question 검사만 check_workbook_pack에 위임한다. bank_asset_checks도 v2에 정적 card/details 요구를 적용하지 않고 새 payload 자산 검사 경로로 간다. 모든 output_names 호출에서 표시 버전을 전달하고 note→dynamic 문항 anchor 검사는 payload ID로 확인한다.

check_workbook_pack은 포함 문항 ID·번호·kind/answer status·problem html/figures/hints의 두 payload 일치, 문제 payload 허용 키, 해설 steps/answer 존재, registry role/exposure·hash·evidence 소속, MD 보존·link를 검사한다. HTML payload를 읽는 것으로 끝내지 말고 삽입 script 외의 HTML img/CSS 외부 자원도 기존 검사로 확인한다. 두 HTML이 읽은 payload를 원본 snapshot에 재주입한 결과와 동일한지 대조해 script 밖에 추가한 답안 img/DOM을 거부한다. browser 검증은 별도이며 자동 구조 PASS를 browser PASS로 기록하지 않는다.

- [ ] **Step 5: 발행 사전 조건 확장.** 기존 publish의 checks 조건 전후에 v2만 `check_redrawn_figures(stage,data,require_review=True)`를 요구한다. 시각 검토 not_run인 도식을 발행하지 않는다. checks.browser/source_visual/content는 기존에 요구되던 검토와 함께 새 두 파일을 대상으로 한다. 사용자 파일 충돌·generated_files·원문 해시·backup/rollback 기존 검사는 유지한다. tests/test_review_pack_publish.py에 not_run 그림 기록 및 새 기출문제 파일과 사용자 파일 충돌 실패를 추가한다.

- [ ] **Step 6: 전체 관련 회귀 및 commit.** `python -m pytest tests -k review_pack -n 0 -q`; legacy, note metadata/figures/print, bank import tests 포함. 모두 새 회귀 없이 PASS 후 위 파일만 stage하고 `git commit -m "feat: integrate workbook sheets with review pack validation and publishing"`.

### Task 5: 실제 12문항을 새로 저작하고 회로를 직접 제작

**Files:**
- Create: `docs/learning-pack-source/실험04/workbook/q-mux2.json`, `q-mux4.json`, `q-demux2.json`, `q-design4.json`, `q-decoder.json`, `q-tri.json`, `q-muxdef.json`, `q-demuxdef.json`, `q-difference.json`, `q-demux4.json`, `q-mux2-graded.json`, `q-active-general.json`.
- Create: `docs/learning-pack-source/실험04/redraw_questions.py`, `figures/questions/`, `figures/solutions/`, `figures/redraw-manifest.json`.
- Modify: `docs/learning-pack-source/실험04/manifest.json`, `검증결과.md`.
- Create: `tests/test_review_pack_workbook_experiment04.py`.
- Modify: `.claude/skills/logic-lab-review-pack/SKILL.md`, `references/authoring.md`, `references/verification.md`; Create `references/workbook.md`.

**Interfaces:** Consumes 기존 committed 저작 HTML·manifest·은행 증거. Produces 위 새 작성 JSON·registry·그림, schema_version=1/review_presentation_version=2 저작 manifest. 기존 note source 파일과 고정 bank fields는 바꾸지 않는다.

- [ ] **Step 1: 실제 콘텐츠 보존 실패 테스트 작성.**

```python
import json
from pathlib import Path
from itertools import product
from scripts.lab.review_pack.workbook_content import load_workbook_content, build_workbook_data
from scripts.lab.review_pack.workbook_figures import check_redrawn_figures

ROOT = Path('docs/learning-pack-source/실험04')
EXPECTED = ['q-mux2','q-mux4','q-demux2','q-design4','q-decoder','q-tri',
            'q-muxdef','q-demuxdef','q-difference','q-demux4','q-mux2-graded','q-active-general']

def test_all_selected_questions_preserve_identity_and_holds():
    m = json.loads((ROOT/'manifest.json').read_text(encoding='utf-8'))
    assert m['review_presentation_version'] == 2
    rows = load_workbook_content(m, ROOT)
    assert [q['id'] for q in rows] == EXPECTED
    assert [p['id'] for p in m['problems'] if p['status']=='held'] == ['q-active','q-switch','q-empty-six']
    assert check_redrawn_figures(ROOT,m,require_review=True) == []
    a = build_workbook_data(m,rows,'answers'); q = build_workbook_data(m,rows,'problems')
    by_id = {p['id']:p for p in a['problems']}
    assert '답안 충돌' in by_id['q-tri']['section']
    assert '답안 충돌' in by_id['q-demux4']['section']
    assert all('evidence/' not in json.dumps(p,ensure_ascii=False) for p in q['problems'])

def test_mux_and_tristate_models_match_selected_output():
    for s,i0,i1 in product((0,1),repeat=3):
        assert int(((not s) and i0) or (s and i1)) == (i1 if s else i0)
        oe0,oe1 = s,1-s
        active = [v for v,oe in [(i0,oe0),(i1,oe1)] if oe == 0]
        assert active == [i1 if s else i0]
    for s1,s0,d0,d1,d2,d3 in product((0,1),repeat=6):
        terms = [(not s1) and (not s0) and d0,(not s1) and s0 and d1,
                 s1 and (not s0) and d2,s1 and s0 and d3]
        assert int(any(terms)) == [d0,d1,d2,d3][2*s1+s0]
```

이 식 검산만으로 새 SVG가 정확하다고 주장하지 않는다. 도식 연결은 원문 대조와 실제 SVG 접속 확인을 별도로 수행한다. 실제 입력표·서술형 조건·disputed 표기는 이 테스트와 함께 확인한다.

- [ ] **Step 2: FAIL 확인.** `python -m pytest tests/test_review_pack_workbook_experiment04.py -n 0 -q`; 새 버전/작성 파일 부재로 FAIL.
- [ ] **Step 3: 12문항을 아래 배치로 저작한다.** 각 문항별로 기존 div.problem의 원문 문장·조건·표를 읽고 original/conditions/ask로 분리한다. 제공 답안/채점 수기와 인쇄 조건을 구분한다. 기존 풀이와 검산·흔한 실수를 단계로 모두 옮기며 원문 조건에 없는 enable·부품명·회로를 추가하지 않는다.

| 문항 | 문제지 그림/표 | 해설지 그림·핵심 |
|---|---|---|
| q-mux2 | 주어진 게이트 수를 텍스트로 제시 | NOT 1+AND 2+OR 1 완성 회로·8행 |
| q-mux4 | given-01: 원문의 E/S0/S1/D0~D3 회로와 빈 출력표 | E 활성 Low·원문 게이트/부품/반전·0,1,0,0 |
| q-demux2 | AND 2+NOT 1 조건 | 독립 Y0/Y1 출력 회로·4행 |
| q-design4 | given-01: 원문 미완성 블록과 기능표 | NOT 2+3입력 AND 4+4입력 OR 1, enable 추가 금지 |
| q-decoder | 원문 정의·구할 것 | Ck로 MUX/DMUX 연결을 보여 주는 풀이 도식 |
| q-tri | given-01: 원문의 미결선 버퍼·인버터·nOE 기능표 | nOE0=S/nOE1=S′·공통 Y, active High 답안 충돌 유지 |
| q-muxdef | 원문 서술 조건 | 선택 신호/데이터/출력 정의·I1=0 검산 |
| q-demuxdef | 출처 미확인 표기 | 분배 정의·데이터 입력과 선택선 구분 |
| q-difference | 출처 미확인 표기 | N→1/1→N, 단순 역함수로 쓰지 않음 |
| q-demux4 | 원래 입력표 유지, 출력만 빈칸, 전사 표임을 표시 | 원문 X/이상 모델 0 구분, 실제 부품 출력 확정 금지 |
| q-mux2-graded | Sel/X0/X1의 지정 네 행·빈 출력 | 원문의 입력 이름을 쓴 완성 회로·0,1,1,1 |
| q-active-general | 인쇄 배점·수기 배점의 차이는 notes에 보존 | 활성 극성은 출력값과 다름을 예로 검산 |

기본 그림 파일은 questions의 q-mux4/q-design4/q-tri 각 given-01, solutions의 q-mux2/q-demux2/q-design4/q-decoder/q-tri/q-mux2-graded 각 solution-01로 9쌍이다. 원문 시각 확인으로 추가 도식이 실제 필요하면 같은 규칙의 -02 파일을 추가하고 registry·검증 목록도 갱신한다. 정의 문항에 장식용 회로를 만들거나 증거 페이지 전체를 새 이미지로 재인쇄하지 않는다.

Step 3은 한 번에 12문항을 작성하는 작업이 아니다. 아래 체크 한 개마다 해당 문항의 원문·조건·표·풀이를 읽고 위 7키 JSON으로 작성한 뒤 `load_workbook_content`의 해당 문항 오류를 확인한다. 그림 ID 연결은 Step 4~5의 기록이 생긴 뒤 검증한다.

- [ ] **Step 3a:** `workbook/q-mux2.json` 작성·8행과 게이트 수 확인.
- [ ] **Step 3b:** `workbook/q-mux4.json` 작성·D3→D0 열 순서와 빈 출력 4칸 확인.
- [ ] **Step 3c:** `workbook/q-demux2.json` 작성·독립 출력 2개와 4행 확인.
- [ ] **Step 3d:** `workbook/q-design4.json` 작성·enable 없는 기능표와 지정 게이트 수 확인.
- [ ] **Step 3e:** `workbook/q-decoder.json` 작성·Ck와 데이터 경로 관계 확인.
- [ ] **Step 3f:** `workbook/q-tri.json` 작성·nOE 기능표·High-Z·충돌 조건 확인.
- [ ] **Step 3g:** `workbook/q-muxdef.json` 작성·선택 데이터가 0일 때의 출력 확인.
- [ ] **Step 3h:** `workbook/q-demuxdef.json` 작성·기출 여부 미확인 분류 유지.
- [ ] **Step 3i:** `workbook/q-difference.json` 작성·N→1/1→N과 입력 정보 손실 설명 확인.
- [ ] **Step 3j:** `workbook/q-demux4.json` 작성·+5/0 입력, 전사 빈칸, 원문 X와 계산 0 구분.
- [ ] **Step 3k:** `workbook/q-mux2-graded.json` 작성·원문 지정 4행을 8행 일반표로 대체하지 않음.
- [ ] **Step 3l:** `workbook/q-active-general.json` 작성·기능 활성과 출력 논리값을 구분.

문항 힌트는 접근 순서만 제공하고 완성 배선·최종 출력열·정답 회로식을 그대로 노출하지 않는다. 두 판의 original/conditions/ask는 동일한 JSON을 사용한다.

- [ ] **Step 4: 새 도식을 직접 SVG로 제작하고 PNG를 만든다.** 기존 `redraw_figures.py`는 노트 전용이므로 수정 없이 도형 작성을 참고한다. `redraw_questions.py`는 이 실험의 직접 도식 함수와 등록 목록만 가진다. 회로는 직교 배선·접속점·명확한 비접속 교차·반전 bubble·이름 있는 단자를 쓰고 원문 NAND를 AND/OR로 조용히 치환하지 않는다. q-tri 미결선 그림에 해답 배선을 그리지 않는다. SVG는 아래 저장 형태를 사용하고 PNG 래스터화는 기존 fitz로 수행한다.

```python
from pathlib import Path
from html import escape
import fitz

def save_drawing(destination, title, body, width_mm=120, height_mm=72):
    destination = Path(destination)
    destination.parent.mkdir(parents=True,exist_ok=True)
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width_mm}mm" height="{height_mm}mm" '
           f'viewBox="0 0 1000 600" role="img"><title>{escape(title)}</title>'
           '<rect width="1000" height="600" fill="white"/>'+body+'</svg>')
    destination.write_text(svg,encoding='utf-8')
    with fitz.open(stream=svg.encode('utf-8'),filetype='svg') as image:
        with fitz.open(stream=image.convert_to_pdf(),filetype='pdf') as pdf:
            pdf[0].get_pixmap(matrix=fitz.Matrix(300/72,300/72),alpha=False).save(destination.with_suffix('.png'))
    return destination, destination.with_suffix('.png')
```

라벨은 ASCII 신호명 또는 한국어로 적고 font-size를 viewBox 배율에 맞춰 A4 최종 표시에서 읽을 수 있도록 정한다. 실행 명령은 `python docs/learning-pack-source/실험04/redraw_questions.py`다. SVG/PDF 변환이 라벨을 잘못 처리하면 Chrome에서 SVG를 렌더링해 PNG로 저장하고 변환 방법을 기록한다. PNG는 명시한 mm 크기×300/25.4 픽셀과 ±2px 이내인지 Pillow로 검증한다.

Step 4는 도식별로 나누어 수행한다. 복잡한 회로는 먼저 신호/게이트 위치를 작성하고 다음 체크에서 배선·교차·접속을 연결한다. 저장·래스터화 함수는 위 save_drawing을 공통으로 쓴다.

- [ ] **Step 4a:** q-mux4 given-01의 원문 부품·핀·입력 극성을 읽고 게이트 위치를 작성.
- [ ] **Step 4b:** q-mux4 given-01의 배선·반전·접속점을 연결하고 PNG 저장.
- [ ] **Step 4c:** q-design4 given-01의 원문 블록·신호 단자만 작성하고 PNG 저장.
- [ ] **Step 4d:** q-tri given-01의 미결선 버퍼·인버터·활성 Low 단자를 작성하고 PNG 저장.
- [ ] **Step 4e:** q-mux2 solution-01의 NOT/AND/OR와 배선을 작성하고 PNG 저장.
- [ ] **Step 4f:** q-demux2 solution-01의 NOT/AND와 독립 출력 배선을 작성하고 PNG 저장.
- [ ] **Step 4g:** q-design4 solution-01의 게이트 위치와 S1/S0 반전선을 작성.
- [ ] **Step 4h:** q-design4 solution-01의 네 AND 입력과 OR 합성 배선을 연결하고 PNG 저장.
- [ ] **Step 4i:** q-decoder solution-01의 Ck·MUX·DMUX 흐름을 작성하고 PNG 저장.
- [ ] **Step 4j:** q-tri solution-01의 nOE0/nOE1·공통 버스·I0/I1를 연결하고 PNG 저장.
- [ ] **Step 4k:** q-mux2-graded solution-01을 Sel/X0/X1 원문 신호명으로 작성하고 PNG 저장.

- [ ] **Step 5: 출처·대조·해시를 기록한다.** 새 그림마다 source_refs/asset IDs·role/exposure·svg/png hash·인쇄 크기·도출 설명을 registry에 기록한다. source_asset_ids는 실제 index에서 확인한 ID만 사용한다. 그림의 wire 끝점·게이트 입력 개수·pin/극성·교차/접속점·기능표를 원문 PNG와 함께 읽고 review_notes에 확인 내용을 적은 뒤에만 review_status=pass로 한다. 정답 도식은 조건에서 도출한 설계임을 표시한다. 모든 새 JSON에는 문항별 힌트를 작성하고 generic 동일 힌트를 반복하지 않는다.

- [ ] **Step 6: manifest·검증 상태와 스킬 지침 갱신.** p.workbook_fragment와 figure_manifest/version만 추가하고 은행 고정필드를 보존한다. 새 콘텐츠 검토 상태는 아래처럼 초기화하며 최종 단계의 검증 뒤에만 변경한다.

```python
m['review_presentation_version'] = 2
m['figure_manifest'] = 'figures/redraw-manifest.json'
m['checks'] = dict.fromkeys(('source_visual','content','independent','browser'),'not_run')
for p in m['problems']:
    if p['status'] == 'included': p['workbook_fragment'] = f'workbook/{p["id"]}.json'
```

SKILL.md의 출력 수를 HTML 3/MD 3으로 바꾸고 생명과학 템플릿은 실험설명, 전자회로2 템플릿은 문제/풀이에 적용한다고 명시한다. authoring에 새 JSON 예시, SVG/PNG registry, 문제/해설 역할을 적고 verification에 workbook의 A4 가로·확대·Hint·인쇄 검사를 추가한다. 기존 독립 검토/증거 보존 규칙을 유지한다.

- [ ] **Step 7: PASS·보존 확인 및 commit.** `python -m pytest tests/test_review_pack_workbook_experiment04.py tests/test_review_pack_note_figures.py tests/test_review_pack_bank_provenance.py -n 0 -q`. `git diff -- docs/learning-pack-source/실험04/sections docs/learning-pack-source/실험04/evidence 문제은행`은 변경이 없어야 한다. 위 작성/그림/지침/테스트만 stage하고 `git commit -m "docs: redraw experiment 4 question and solution diagrams"`.

### Task 6: 실제 브라우저·A4 인쇄로 오류와 내용 잘림 검사

**Files:**
- Create: `tests/test_review_pack_workbook_browser.py`.
- Create: `docs/verify/logic-lab-review-pack-question-workbook.md` 및 이 문서에서 연결할 검증 스크린샷.
- Modify: 실제 작성 JSON·그림의 검증된 결함만 수정. 원본 템플릿은 수정하지 않는다.

**Interfaces:** Consumes Task 5 source와 build CLI. Produces 최종 stage에 대한 실제 browser/print 결과와 파일 해시 기록. 검증용 PDF는 학습팩의 공식 출력에 추가하지 않는다.

- [ ] **Step 1: 브라우저 검증 test를 작성한다.** 기존 Chrome을 사용하는 선택 테스트이며 도구 부재로 skip이면 브라우저 검증 완료로 간주하지 않는다. 실행 시 Native 브라우저 도구로 같은 조건을 검사할 수 있다.

```python
import json
from pathlib import Path
import pytest
from scripts.lab.review_pack.render import assemble
from scripts.lab.review_pack.html2md import convert_pack

@pytest.mark.parametrize('viewport',[{'width':1280,'height':900},{'width':375,'height':812}])
def test_real_workbook_decode_ready_and_no_overflow(tmp_path,viewport):
    pw = pytest.importorskip('playwright.sync_api')
    run = Path('docs/learning-pack-source/실험04')
    m = json.loads((run/'manifest.json').read_text(encoding='utf-8'))
    paths = assemble(m,run,tmp_path/'stage',Path('.claude/skills/logic-lab-review-pack/assets'))
    convert_pack(paths['note_html'],paths['review_html'],manifest=m)
    expected = [p['id'] for p in m['problems'] if p['status']=='included']
    with pw.sync_playwright() as driver:
        with driver.chromium.launch(channel='chrome') as browser:
            page = browser.new_page(viewport=viewport)
            errors = []; page.on('pageerror',lambda e:errors.append(str(e)))
            for key in ('question_html','review_html'):
                page.goto(paths[key].resolve().as_uri())
                page.wait_for_function('document.documentElement.dataset.ready',timeout=60000)
                assert page.locator('html').get_attribute('data-ready') == 'true'
                assert page.locator('body').get_attribute('data-overflow') == ''
                assert page.locator('.page--problem').evaluate_all('(nodes)=>nodes.map(n=>n.id)') == expected
                assert page.locator('.katex-error').count() == 0
                assert page.locator('img').evaluate_all('(imgs)=>imgs.every(i=>i.complete && i.naturalWidth>0)')
            assert errors == []
```

브라우저 테스트에 아래 함수와 검사를 추가한다. 작은 화면에는 원본 템플릿의 고정 페이지 축소 동작을 적용한다. 넓은 표와 마지막 답의 경계도 확인해 원본 data-overflow 검사가 놓치는 위치를 보완한다.

```python
def assert_workbook_bounds_and_links(page):
    assert page.locator('.sol-step img').evaluate_all('''imgs => imgs.every(img => {
      const p=img.closest('.sol-step-body').getBoundingClientRect(),r=img.getBoundingClientRect();
      return r.left>=p.left-1 && r.right<=p.right+1;
    })''')
    assert page.locator('.sol-answer').evaluate_all('''nodes => nodes.every(node => {
      const p=node.closest('.work').getBoundingClientRect(),r=node.getBoundingClientRect();
      return r.bottom<=p.bottom+1;
    })''')
    assert page.locator('table').evaluate_all('''tables => tables.every(table => {
      const p=table.parentElement.getBoundingClientRect(),r=table.getBoundingClientRect();
      return r.left>=p.left-1 && r.right<=p.right+1;
    })''')
    assert page.locator('a.hint-strip').evaluate_all('''links => links.every(a =>
      document.getElementById(decodeURIComponent(a.hash.slice(1))))''')

def assert_offline_reload(page):
    page.context.set_offline(True)
    try:
        page.reload()
        page.wait_for_function('document.documentElement.dataset.ready',timeout=60000)
        assert page.locator('html').get_attribute('data-ready') == 'true'
        assert page.locator('.katex-error').count() == 0
        assert page.locator('img').evaluate_all('(imgs)=>imgs.every(i=>i.complete && i.naturalWidth>0)')
    finally:
        page.context.set_offline(False)
```

Step 1의 key 루프 안에서 두 함수를 호출한다. 문제지 q-mux4의 빈 출력은 `page.locator('#q-mux4 tbody tr td:last-child').all_text_contents()`가 `['','','','']`인지 검사한다. blank table/그림이 브라우저에서 식으로 채워지지 않아야 한다.

- [ ] **Step 2: 첫 실제 stage를 생성하고 브라우저 테스트 실행.**

```powershell
python -m scripts.lab.review_pack build --root . --run docs/learning-pack-source/실험04 --stage tmp/review-pack/실험04-workbook-20261001-a
python -m scripts.lab.review_pack check --folder tmp/review-pack/실험04-workbook-20261001-a
python -m pytest tests/test_review_pack_workbook_browser.py -n 0 -q
```

stage가 이미 있으면 새 접미사를 사용한다. 처음 검사에서 내용 넘침 FAIL이면 test를 약하게 만들지 않고 JSON의 문장 배치·그림 폭을 수정해 새 stage에서 다시 검사한다. 실패 이유와 수정 내용을 기록한다.

- [ ] **Step 3: 두 HTML을 실제로 읽고 스크린샷을 확인한다.** 12문항을 모두 넘겨 문제와 해설 조건·빈 표·완성 회로·일반 정의를 읽는다. 1280px 화면에서는 모든 칸의 라벨·신호명이 읽혀야 한다. 375px에서는 원본 screenZoom 동작과 링크가 작동해야 한다. 실험설명 목차·이전/다음·요약·MUX 조작은 유지되어야 한다. 두 파일을 offline로 reload해 폰트·수식·이미지가 모두 로컬로 로드되는지 확인한다. console error 및 이미지 실패는 0이어야 한다.

- [ ] **Step 4: 검증 PDF를 생성하고 모든 쪽을 렌더링해 확인한다.** 자동 브라우저가 가능하면 data-ready=true와 이미지 완료 이후 `page.pdf(path=...,prefer_css_page_size=True,print_background=True)`로 저장한다. 아래 물리 크기 검사를 실행하고 그림·진리표·마지막 답이 있는 모든 쪽을 PNG로 렌더링해 시각 점검한다. Hint 추가 쪽 수가 있어서 PDF 쪽 수를 12로 고정하지 않는다.

```python
from pathlib import Path
from pypdf import PdfReader
import fitz

def verify_print(pdf_path, output_dir):
    target = Path(output_dir); target.mkdir(parents=True,exist_ok=True)
    reader = PdfReader(pdf_path)
    assert len(reader.pages) >= 12
    for page in reader.pages:
        assert abs(float(page.mediabox.width)*25.4/72-297) < 0.5
        assert abs(float(page.mediabox.height)*25.4/72-210) < 0.5
    with fitz.open(pdf_path) as pdf:
        for i,page in enumerate(pdf):
            page.get_pixmap(matrix=fitz.Matrix(1.5,1.5),alpha=False).save(target/f'page-{i+1:02}.png')
```

- [ ] **Step 5: 검증 기록을 작성한다.** 정확한 명령·결과·stage·template hash·HTML/그림 hash·12문항 체크 목록·인쇄 쪽 목록·원문 극성 대조·모바일 화면·offline 결과를 `docs/verify/logic-lab-review-pack-question-workbook.md`에 남긴다. 실제 수행되지 않은 테스트는 not_run/skip으로 적는다. 수정은 최대 두 차례로 하고 남은 오류가 있으면 초안으로 보고하며 기존 팩을 발행하지 않는다.
- [ ] **Step 6: 관련 테스트 PASS 후 commit.** `python -m pytest tests -k review_pack -n 0 -q`; browser test, 검증 문서와 실제 필요했던 작성 수정만 stage하고 `git commit -m "test: verify workbook rendering and landscape print layout"`.

### Task 7: 독립 리뷰·최종 발행·원래 체크아웃용 핸드오프

**Files:**
- Modify: `docs/learning-pack-source/실험04/manifest.json`, `검증결과.md`.
- Generate: `복습노트/실험04/`의 HTML 3/MD 3, 그림, 감사·증거·로컬 번들.
- Modify: `docs/verify/logic-lab-review-pack-question-workbook.md`.

**Interfaces:** Consumes Task 6의 실제 검증 및 `publish(stage,destination,root)` 기존 API. Produces 검증된 최종 학습팩과 backup 경로. merger는 이 task에 포함하지 않는다.

- [ ] **Step 1: 현재 diff와 test baseline을 기록한다.** `git status --short`, `git diff --stat`, `python -m pytest tests -k review_pack -n 0 -q`, `python -m pytest tests -n 0 -q`를 실행한다. 전체 실패가 있으면 위치·이 변경과의 관계·재현 명령을 검증 문서에 적고 새 회귀는 고친다. 기존 실패를 통과한 것으로 보고하지 않는다.
- [ ] **Step 2: Native 작업의 최종 독립 리뷰 1회.** requesting-code-review 스킬을 읽고 실행 시작 기준 SHA부터 현재 변경·설계·계획·실제 12문항·새 그림·검증 결과를 독립 리뷰어에게 전달한다. 계획 작성 시에는 subagent를 띄우지 않는다. reviewer는 template 동일성, 문제 JSON 답 노출, active Low/Z/X, 그림 접속, MD 보존, version 분기, stage/backup을 확인한다. 실제 독립 검토가 안 되면 independent=pass를 기록하지 않는다. 리뷰 수정은 관련 자동/시각 검증을 다시 수행한다.
- [ ] **Step 3: 검증 상태를 실제 결과로 갱신하고 최종 stage를 새로 생성한다.** 이전 학습팩의 pass를 복사하지 않는다. source_visual은 모든 새 그림 대조 완료, content는 실제 본문/풀이/검산 확인, independent는 리뷰 결과, browser는 두 HTML와 기존 note의 실제 화면/인쇄 결과다. source authoring 검증 문서와 최종 파일 해시를 함께 기록한다.

```powershell
python -m scripts.lab.review_pack build --root . --run docs/learning-pack-source/실험04 --stage tmp/review-pack/실험04-workbook-20261001-final
python -m scripts.lab.review_pack check --folder tmp/review-pack/실험04-workbook-20261001-final
```

최종 stage의 HTML/그림 콘텐츠가 검토한 stage와 동일한지 확인한다. 생성본 내용이 달라졌으면 해당 화면·내용·인쇄 검증을 다시 한다. build/check 통과만으로 최종 browser=pass를 추정하지 않는다. 실제 included ID 목록이 Task 5 EXPECTED와 정확히 같아야 한다.

- [ ] **Step 4: 최종 stage를 발행한다.**

```powershell
python -m scripts.lab.review_pack publish --root . --stage tmp/review-pack/실험04-workbook-20261001-final --experiment 4
python -m scripts.lab.review_pack check --folder 복습노트/실험04
```

publish가 만든 backup 경로를 기록하고 삭제하지 않는다. 최종 위치에서 note→question/review, answer→note concept, MD→MD 및 evidence 원문 링크를 실제 확인한다. 이전 팩의 사용자 파일 충돌이면 오류를 해결하기 전까지 덮어쓰지 않는다.
- [ ] **Step 5: 선택적으로 stage하고 commit.**

```powershell
git add docs/learning-pack-source/실험04/manifest.json docs/learning-pack-source/실험04/검증결과.md docs/verify/logic-lab-review-pack-question-workbook.md 복습노트/실험04
git diff --cached --stat
git commit -m "docs: publish experiment 4 question and solution workbook sheets"
git status --short
```

백업 폴더·tmp stage·검증 PDF는 학습팩 출력으로 commit하지 않는다. 범위 밖 사용자 변경을 묶지 않는다.
- [ ] **Step 6: 사용자에게 결과와 후속 통합 정보를 전달한다.** 새 문제지/해설지와 MD 링크, 작업 worktree/branch/최종 commit, included 12/held 3, 그림 수, 실제 테스트/브라우저/인쇄 결과, 답안 충돌 두 문항, 미해결, backup 경로를 전달한다. 원래 체크아웃에는 미통합임을 명시한다.

## 계획 자체 검토

- 템플릿 원본/byte 보존/로컬 번들: Task 1, 3.
- source bank와 authored JSON 분리/12문항 및 3 held/기존 링크: Task 1, 2, 4, 5.
- 문제지 답 노출 차단/그림 role·출처·해시/검증 상태 결합: Task 2, 3, 4, 5, 7.
- JS 템플릿의 빈 MD 문제/표·수식·그림·anchor 보존: Task 3, 4.
- 직접 그림 제작/원문 반전·게이트·극성/독립 도출: Task 5, 6, 7.
- A4 가로/작은 화면/긴 문항/이미지 decode/Hint/offline: Task 6.
- note 리프레시와 legacy 유지/0문항/backup·원문 hash: Task 1, 4, 7.
- 모든 인터페이스는 이 문서의 확정 인터페이스와 일치한다. 그림 helper는 Task 2에서, 실제 저작·검증 함수를 Task 5~6에서 정의한다.
- Review Focus 다섯 조건을 해당 task의 입력 변형 테스트 및 실제 화면 검증에 연결했다.
- 실행 시작 전 사용자에게 계획 검토를 요청한다. 기존 Native 선택을 다시 묻지 않는다.
