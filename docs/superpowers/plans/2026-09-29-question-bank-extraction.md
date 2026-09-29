# Question Bank Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 학습팩과 독립된 기출 문제은행 계약·읽기 전용 검증 CLI·실험4 새 세션 추출 절차를 제공한다.

**Architecture:** 원문 등장(occurrence)과 고유 문항(question)을 분리한 JSON 및 근거 이미지를 보존한다. 스키마는 형식을, Python은 참조·감사·파일 무결성을 검증한다. 기존 manifest/build/publish는 변경하지 않으며 실제 추출은 도구 완성 후 별도 새 세션에서 수행한다.

**Tech Stack:** 기존 Python 환경, 표준 라이브러리 json/pathlib/hashlib/argparse/re, pytest. 외부 런타임 의존성 없음. JSON Schema는 문서화된 제한 키워드만 사용하고 범용 스키마 엔진을 만들지 않는다.

**Spec:** [승인된 추출 설계](../specs/2026-09-29-question-bank-extraction-design.md). 실행자는 이 문서와 설계를 모두 읽는다.

## Global Constraints

- 기존 워크트리 C:/Users/Hyunjun/.codex/worktrees/logic-lab-review-pack/논회실 및 브랜치 codex/logic-lab-review-pack을 사용한다.
- Python 런타임은 표준 라이브러리만 사용한다. PDF 시각 판독 도구는 기존 검증 환경과 pdf 스킬을 사용한다.
- 원자료·보고서·측정 기록·결선도·기존 학습팩은 수정하지 않는다.
- tmp/review-pack-work/experiment04의 임시 분석은 추출 근거로 사용하지 않는다.
- 첫 실제 추출은 실험4 전체 자료이며, 기출·예상·해설·이미지·원본 문서를 모두 감사한다.
- 문제은행 JSON에는 HTML 조각·독립 풀이·정답 검증 완료 상태를 넣지 않는다.
- 파일 경로는 기준 디렉터리 상대 POSIX 경로이며 Windows와 macOS에서 사용할 수 있어야 한다.
- 형식 검사 통과, 원문 시각 판독 완료, 독립 풀이 검증을 서로 대신하지 않는다.
- 새 세션 생성이나 Task 8 실행을 자동으로 시작하지 않는다.

확정된 실행 방식은 **Native**다. executing-plans로 Task 1~5를 직접 구현하고 최종 독립 코드 리뷰를 수행한다. 구현 중 모델 변경이나 task별 서브에이전트 분할을 추가하지 않는다. 이 계획 저장 자체는 구현 시작이나 실제 기출 추출을 뜻하지 않는다.

## Review Focus

1. 오버바/극성/수치 한 개만 다른 문항: 유사 문항 관계만 남기고 자동 병합하지 않는다 — Task 2의 variant 보존 테스트.
2. 같은 번호의 서로 다른 분반 답안 및 여러 충돌 답안: 후보 연결과 원문을 유지하고 정답 검증으로 승격하지 않는다 — Task 2의 답안 테스트.
3. .doc/미지원 파일/빈 폴더/페이지 수를 못 읽은 PDF: 목록에서 사라지지 않고 명시적 오류 또는 보류로 남는다 — Task 3의 목록·감사 테스트.
4. 경로 탈출·링크·원문 또는 그림 변경: 구조가 정상이어도 입력을 거부하고 원문을 수정하지 않는다 — Task 3의 파일 무결성 테스트.
5. 형식 정상이나 시각 판독 미완료/답 노출 이미지: CLI가 완전 추출 또는 안전한 문제 그림으로 오인시키지 않는다 — Task 2와 Task 4의 상태·출력 테스트.

---

## 작업 환경과 파일 지도

모든 명령의 cwd는 Global Constraints의 워크트리다. 현재 시작 커밋은 0d56b13f3bfe04e0483e142eb6ad698695e91752. 다른 변경이 있으면 보존하고 이 계획 파일만 stage한다. 원래 Desktop 체크아웃에서 실행하지 않는다.

| 파일 | 변경 | 책임 |
|---|---|---|
| .claude/skills/logic-lab-review-pack/references/question-bank.schema.json | 생성 | 형식 정본 |
| .claude/skills/logic-lab-review-pack/references/question-bank.md | 생성 | 계약 의미·검증·후속 연결 경계 |
| .claude/skills/logic-lab-review-pack/references/question-bank-extraction-session.md | 생성 | 새 세션용 실험4 추출 요청·완료 조건 |
| .claude/skills/logic-lab-review-pack/SKILL.md | 자료 확인 절만 수정 | 별도 추출 선행과 미구현 import 경계 안내 |
| scripts/lab/review_pack/question_bank.py | 생성 | 스키마·관계·감사·파일 검사 및 집계 |
| scripts/lab/review_pack/question_bank_sources.py | 생성 | 확장자 무관 원자료 목록화 |
| scripts/lab/review_pack/question_bank_cli.py | 생성 | inventory/check CLI |
| tests/test_review_pack_question_bank.py | 생성 | 계약·의미·파일 검사 |
| tests/test_review_pack_question_bank_sources.py | 생성 | 목록화 검사 |
| tests/test_review_pack_question_bank_cli.py | 생성 | CLI 입출력·실패 코드 |
| tests/fixtures/review_pack/question_bank/minimal.json | 생성 | 실제 기출과 무관한 작은 유효 fixture |
| 문제은행/실험04/ | 별도 추출 세션에서 생성 | 실제 JSON·근거 이미지·검증결과 |

기존 sources.py는 학습팩 자료 탐색기이므로 확장자 필터를 이번 변경에서 고치지 않는다. question_bank_sources.py는 퀴즈 하위 전체 파일만 담당한다. 기존 manifest/render/html2md/checks/publish 및 템플릿은 수정 대상이 아니다.

## Task 1: 형식 계약과 비변이 로더

**Files:** Create schema JSON, question_bank.py, minimal.json, tests/test_review_pack_question_bank.py.

**Interfaces:**
- `validate_question_bank(data: object) -> list[str]`: 형식·의미 오류, JSON 경로를 포함한 문자열. 데이터 변경 없음.
- `load_question_bank(path: Path) -> dict`: UTF-8(JSON BOM도 허용) 로드 후 validate, 오류는 ValueError. 파일 읽기 실패는 OSError.
- `_shape_errors(value: object, rule: dict, at: str = '$') -> list[str]`: 이 스키마에서 사용한 키워드만 처리하는 비공개 함수.
- `SCHEMA_PATH: Path`: `Path(__file__).resolve().parents[3] / '.claude/skills/logic-lab-review-pack/references/question-bank.schema.json'`.

- [ ] **1. 실행 환경과 기준 상태를 확인한다.**

```powershell
git status --short
git branch --show-current
python --version
python -m pytest -n0 tests/test_review_pack_manifest.py tests/test_review_pack_sources.py -q
```

예상: 지정 브랜치, 기존 관련 테스트 통과. 환경 문제는 먼저 구분한다. 인계된 전체 관련 검사 416개 통과와 기존 config 14개 실패는 과거 결과이지 이번 실행 증거가 아니다.

- [ ] **2. 최소 fixture를 아래 내용으로 작성한다.** 이 fixture는 문항이 없는 draft의 형식 예제이며 실제 원문 hash 검사용이 아니다.

```json
{
  "schema": "logic-lab-question-bank", "schema_version": 1,
  "bank_id": "bank-exp04", "experiment": 4,
  "sources": [], "assets": [], "occurrences": [], "questions": [], "relations": [],
  "audit": {"status": "draft", "checks": {"structure": "not_run", "source_visual": "not_run"}, "units": [], "unresolved": []}
}
```

- [ ] **3. 형식 실패 테스트를 쓴다.** 다음 helper는 이 테스트 파일의 후속 task에서도 사용한다.

```python
import copy
import json
from pathlib import Path
import pytest
from scripts.lab.review_pack.question_bank import validate_question_bank, load_question_bank

def bank():
    return json.loads(Path('tests/fixtures/review_pack/question_bank/minimal.json').read_text(encoding='utf-8'))

def test_minimal_draft_is_valid_and_unchanged():
    data = bank(); before = copy.deepcopy(data)
    assert validate_question_bank(data) == []
    assert data == before

@pytest.mark.parametrize('key,value', [('schema_version', 2), ('schema_version', True), ('experiment', True), ('experiment', 11), ('questions', {}), ('schema', 'learning-pack')])
def test_wrong_shape(key, value):
    data = bank(); data[key] = value
    assert validate_question_bank(data)

def test_unknown_authoring_field_rejected():
    data = bank(); data['derived_answer'] = '1'
    assert any('derived_answer' in e for e in validate_question_bank(data))

def test_loader_reports_invalid_json(tmp_path):
    path = tmp_path / 'bank.json'; path.write_text('{', encoding='utf-8')
    with pytest.raises(ValueError): load_question_bank(path)
```

- [ ] **4. 실패를 확인한다.** `python -m pytest -n0 tests/test_review_pack_question_bank.py -q`. 예상: 아직 모듈이 없어 collection 오류. 다른 오류와 혼동하지 않는다.

- [ ] **5. 다음 생성 코드를 일회성 Python으로 실행해 schema JSON을 쓴다.** 코드는 생성 스크립트로 별도 추적하지 않는다. `obj()`는 모든 필드를 required로 만들므로 nullable 필드도 명시적으로 null을 기록한다.

```python
import json
from pathlib import Path
S = {'type': 'string'}
N = {'type': ['string', 'null']}
I = {'type': 'integer', 'minimum': 1}
ID = {'type': 'string', 'pattern': r'^[A-Za-z][A-Za-z0-9_-]*$'}
H = {'type': 'string', 'pattern': r'^[a-f0-9]{64}$'}
def enum(*values): return {'enum': list(values)}
def arr(item): return {'type': 'array', 'items': item}
def obj(**props): return {'type': 'object', 'properties': props, 'required': list(props), 'additionalProperties': False}
def nullable(rule): return dict(rule, type=[rule['type'], 'null'])
LOC = obj(source_id=ID, pdf_page=nullable(I), printed_page=N, locator=S,
          bbox=dict(nullable(arr({'type':'number','minimum':0,'maximum':1})), minItems=4, maxItems=4),
          image_size=dict(nullable(arr(I)), minItems=2, maxItems=2))
META = obj(year=N, term=N)
SOURCE = obj(id=ID, path=S, sha256=H, format=enum('pdf','docx','doc','image','text','other'),
    filename_metadata=META, observed_metadata=META,
    conflicts=arr(obj(field=enum('year','term'), filename_value=S, observed_value=S, location=LOC)),
    processing=enum('pending','complete','held'), reason=S, unit_kind=enum('page','document','image'), unit_count=nullable(I))
ASSET = obj(id=ID, path=S, sha256=H, location=LOC, role=enum('problem','answer','mixed'), answer_exposure=enum('none','present','unknown'))
BLOCK = obj(id=ID, type=enum('text','math','table','figure'), text=S, tex=N, cells=nullable(arr(arr(S))), asset_id=nullable(ID))
OCC = obj(id=ID, role=enum('question','answer','explanation','mixed'), location=LOC, original_number=N,
    blocks=arr(BLOCK), reading=enum('readable','partial','unreadable'),
    uncertainties=arr(obj(block_id=nullable(ID), symbol=S, candidates=arr(S), reason=S, location=LOC)))
Q = obj(id=ID, occurrence_ids=dict(arr(ID), minItems=1), representative_occurrence_id=ID,
    kind=enum('past','predicted','unknown'), classification_reason=S, evidence=dict(arr(LOC), minItems=1),
    subparts=arr(obj(id=ID, label=S, occurrence_id=ID, block_ids=dict(arr(ID), minItems=1))),
    answers=arr(obj(occurrence_id=ID, target_id=ID, status=enum('confirmed','candidate'), reason=S)))
REL = obj(from_id=ID, to_id=ID, type=enum('duplicate_candidate','variant_of','answer_candidate'), reason=S, evidence=dict(arr(LOC), minItems=1))
AUDIT = obj(status=enum('draft','complete','complete_with_holds'),
    checks=obj(structure=enum('not_run','pass','fail'), source_visual=enum('not_run','partial','pass')),
    units=arr(obj(source_id=ID, index=I, outcome=enum('questions','reference','blank','held'), occurrence_ids=arr(ID), reason=S)),
    unresolved=arr(obj(target_id=ID, reason=S)))
schema = obj(schema=enum('logic-lab-question-bank'), schema_version={'type':'integer','enum':[1]}, bank_id=ID,
    experiment={'type':'integer','minimum':1,'maximum':10}, sources=arr(SOURCE), assets=arr(ASSET),
    occurrences=arr(OCC), questions=arr(Q), relations=arr(REL), audit=AUDIT)
schema['$schema'] = 'https://json-schema.org/draft/2020-12/schema'
path = Path('.claude/skills/logic-lab-review-pack/references/question-bank.schema.json')
path.write_text(json.dumps(schema, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
```

- [ ] **6. 입력을 변경하지 않는 형식 검사와 로더를 구현한다.** 아래 구현에서 시작해 Task 2에서 의미 검사를 추가한다. 네트워크에서 schema를 가져오지 않는다.

```python
import json
import math
import re
from pathlib import Path

SCHEMA_PATH = Path(__file__).resolve().parents[3] / '.claude/skills/logic-lab-review-pack/references/question-bank.schema.json'

def _shape_errors(value, rule, at='$'):
    kinds = {'object': lambda v: isinstance(v, dict), 'array': lambda v: isinstance(v, list),
             'string': lambda v: isinstance(v, str), 'integer': lambda v: type(v) is int,
             'number': lambda v: type(v) in (int, float) and math.isfinite(v), 'null': lambda v: v is None}
    errors = []
    expected = rule.get('type')
    if expected is not None:
        names = expected if isinstance(expected, list) else [expected]
        if not any(kinds[n](value) for n in names): return [f'{at}: invalid type']
    if 'enum' in rule and not any(type(value) is type(v) and value == v for v in rule['enum']):
        errors.append(f'{at}: invalid value')
    if value is None: return errors
    if isinstance(value, dict):
        props = rule.get('properties', {})
        for key in rule.get('required', []):
            if key not in value: errors.append(f'{at}.{key}: required')
        for key, item in value.items():
            if key in props: errors.extend(_shape_errors(item, props[key], f'{at}.{key}'))
            elif rule.get('additionalProperties') is False: errors.append(f'{at}.{key}: unknown field')
    if isinstance(value, list):
        if len(value) < rule.get('minItems', 0) or len(value) > rule.get('maxItems', len(value)):
            errors.append(f'{at}: invalid length')
        for i, item in enumerate(value): errors.extend(_shape_errors(item, rule['items'], f'{at}[{i}]'))
    if isinstance(value, str) and 'pattern' in rule and not re.fullmatch(rule['pattern'], value):
        errors.append(f'{at}: invalid pattern')
    if type(value) in (int, float):
        if value < rule.get('minimum', value) or value > rule.get('maximum', value): errors.append(f'{at}: out of range')
    return errors

def validate_question_bank(data):
    schema = json.loads(SCHEMA_PATH.read_text(encoding='utf-8'))
    return _shape_errors(data, schema)

def load_question_bank(path):
    data = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    errors = validate_question_bank(data)
    if errors: raise ValueError('\n'.join(errors))
    return data
```

- [ ] **7. 형식 검사 테스트를 통과시키고 커밋한다.** `python -m pytest -n0 tests/test_review_pack_question_bank.py -q` → PASS. JSON Schema 생성 코드를 실행한 결과를 눈으로 확인한다.

```powershell
git add .claude/skills/logic-lab-review-pack/references/question-bank.schema.json scripts/lab/review_pack/question_bank.py tests/test_review_pack_question_bank.py tests/fixtures/review_pack/question_bank/minimal.json
git commit -m "feat: define question bank extraction contract"
```

## Task 2: 관계·판독·감사 의미 검사

**Files:** Modify question_bank.py and tests/test_review_pack_question_bank.py.

**Interfaces:** `validate_question_bank(data: object) -> list[str]`를 확장한다. `summarize_question_bank(data: dict) -> dict`를 추가한다. 반환 키는 sources, occurrences, unique_questions, past, predicted, unknown, unreadable, partial, candidate_relations, unresolved이며 값은 정수다. 형식 검사를 통과한 입력만 집계한다. 검사기는 병합·정렬·상태 갱신을 하지 않는다.

- [ ] **1. 테스트에 실제 형태의 작은 문제 fixture helper를 추가한다.**

```python
def location():
    return dict(source_id='s1', pdf_page=None, printed_page=None, locator='document:1', bbox=None, image_size=None)

def populated():
    data = bank()
    data['sources'] = [dict(id='s1', path='quiz.txt', sha256='0'*64, format='text',
        filename_metadata={'year':None,'term':None}, observed_metadata={'year':None,'term':None},
        conflicts=[], processing='complete', reason='', unit_kind='document', unit_count=1)]
    data['occurrences'] = [dict(id='o1', role='question', location=location(), original_number='1',
        blocks=[dict(id='b1',type='text',text='입력이 0일 때 출력은?',tex=None,cells=None,asset_id=None)], reading='readable', uncertainties=[])]
    data['questions'] = [dict(id='q1',occurrence_ids=['o1'],representative_occurrence_id='o1',kind='unknown',
        classification_reason='실제 시험 여부 미확인',evidence=[location()],subparts=[],answers=[])]
    data['audit']['units'] = [dict(source_id='s1',index=1,outcome='questions',occurrence_ids=['o1'],reason='')]
    return data

@pytest.mark.parametrize('change', [
    lambda d: d['questions'][0].update(representative_occurrence_id='missing'),
    lambda d: d['occurrences'][0].update(reading='partial'),
    lambda d: d['occurrences'][0]['blocks'][0].update(id='q1'),
    lambda d: d['audit'].update(status='complete'),
    lambda d: d['questions'][0]['answers'].append(dict(occurrence_id='o1',target_id='q1',status='confirmed',reason='번호만 같음')),
])
def test_semantic_errors(change):
    data = populated(); change(data)
    assert validate_question_bank(data)

def test_variant_is_not_merged_or_mutated():
    data = populated()
    occ = copy.deepcopy(data['occurrences'][0]); occ['id']='o2'; occ['blocks'][0].update(id='b2',text='입력이 1일 때 출력은?')
    data['occurrences'].append(occ)
    q = copy.deepcopy(data['questions'][0]); q.update(id='q2',occurrence_ids=['o2'],representative_occurrence_id='o2')
    data['questions'].append(q)
    data['audit']['units'][0]['occurrence_ids'].append('o2')
    data['relations'].append(dict(from_id='q1',to_id='q2',type='variant_of',reason='입력값이 다름',evidence=[location()]))
    before=copy.deepcopy(data)
    assert validate_question_bank(data)==[]
    assert len(data['questions'])==2 and data==before

def test_conflicting_provided_answers_remain_candidates():
    data=populated()
    for number, value in [(2,'0'),(3,'1')]:
        occ=copy.deepcopy(data['occurrences'][0]); occ.update(id=f'o{number}',role='answer')
        occ['blocks'][0].update(id=f'b{number}',text=value)
        data['occurrences'].append(occ)
        data['questions'][0]['answers'].append(dict(occurrence_id=occ['id'],target_id='q1',status='candidate',reason='분반 미확인'))
        data['audit']['units'][0]['occurrence_ids'].append(occ['id'])
    before=copy.deepcopy(data)
    assert validate_question_bank(data)==[]
    assert data==before
```

- [ ] **2. 위 의미 검사가 실패하는지 확인한다.** `python -m pytest -n0 tests/test_review_pack_question_bank.py -q`. 예상: 현재는 형식만 검사하므로 의미 오류 테스트 실패.

- [ ] **3. validate에 의미 검사를 추가한다.** 형식 오류가 있으면 즉시 반환해 malformed 입력에서 KeyError를 막는다. 아래 코드 패턴으로 인덱스와 JSON 경로를 유지한다.

```python
# validate_question_bank의 기존 즉시 반환을 다음 흐름으로 바꾼다.
schema = json.loads(SCHEMA_PATH.read_text(encoding='utf-8'))
errors = _shape_errors(data, schema)
if errors: return errors
indexes = {}
seen = set()
for collection in ('sources','assets','occurrences','questions'):
    indexes[collection] = {}
    for i, row in enumerate(data[collection]):
        at = f'$.{collection}[{i}]'
        if row['id'] in seen: errors.append(f'{at}.id: duplicate id')
        seen.add(row['id']); indexes[collection][row['id']] = row
for i, occurrence in enumerate(data['occurrences']):
    for j, block in enumerate(occurrence['blocks']):
        if block['id'] in seen: errors.append(f'$.occurrences[{i}].blocks[{j}].id: duplicate id')
        seen.add(block['id'])
for i, question in enumerate(data['questions']):
    for j, part in enumerate(question['subparts']):
        if part['id'] in seen: errors.append(f'$.questions[{i}].subparts[{j}].id: duplicate id')
        seen.add(part['id'])
```

다음 표의 조건을 각각 반복문으로 검사한다. 참조가 없으면 오류를 기록한 뒤 해당 분기를 continue한다. 의미 검사 private helper를 분리할 때에는 동일 모듈에 두고 public API를 늘리지 않는다.

| 대상 | 정확한 검사 |
|---|---|
| 모든 Location | source 존재, PDF page 및 unit_count 범위, 비PDF null/locator 필수, bbox 정렬과 image_size 동반 |
| source | format↔unit_kind 일치, image/document는 count=1, PDF count=null은 held만 허용, held 이유 필수, 메타데이터 값 차이에 정확히 대응하는 conflict 필요 |
| block | math tex, table 직사각 cells, figure asset 참조 필수; 관련 없는 nullable 값은 null; readable occurrence는 blocks 비어 있으면 오류 |
| uncertainty | partial/unreadable에서 최소 한 개, block_id가 있으면 같은 occurrence의 block, reason 필수 |
| asset | problem은 exposure=none; 모든 asset에 원문 Location |
| question | representative 소속, occurrence_ids 중복 금지, question/mixed 역할만 소속 가능, 각 question/mixed 등장 정확히 한 소속, classification_reason 및 evidence 필수 |
| subpart/answer | 소문항의 occurrence/block 소속 일치, 답안 역할 및 target 소속 검사, reason 필수 |
| relation | 타입별 대상 종류, 자기 관계 금지, 동일 타입·무방향 question 쌍 중복 금지, 이유·근거 필수 |
| audit unit | source 존재, (source_id,index) 유일, 범위/역할 일치, occurrence 존재 및 같은 source, 대표 페이지/문서 단위에 등장 포함; questions outcome은 최소 한 등장, reference/blank는 등장 없음, held는 reason |
| unresolved | 대상은 실제 레코드/소문항/block ID, reason 필수; held unit은 해당 source ID를 대상으로 이유를 기록 |
| 완료 상태 | draft만 pending/누락 unit 허용; complete/complete_with_holds는 비어 있지 않은 source 목록 및 모든 알려진 unit 감사, pending 없음; unknown count held source는 1개 held unit; complete는 미해결/held/partial/unreadable 없음 및 source_visual=pass; complete_with_holds는 미해결 최소 1개 및 source_visual=partial/pass; 모든 partial/unreadable occurrence와 held source는 각각 unresolved 대상에 포함 |
| 미연결 답안 | question.answers 또는 answer_candidate로 연결되지 않은 answer/explanation은 unresolved에 이유 필수 |

위 표의 검사를 마치면 `return errors`로 종료한다. 이때 검사 함수가 audit.checks.structure를 수정하지 않는다. 후속 단계로 연결되는 집계 코드는 다음 형태로 구현한다.

```python
def summarize_question_bank(data):
    result={k:len(data[k]) for k in ('sources','occurrences')}
    result['unique_questions']=len(data['questions'])
    for kind in ('past','predicted','unknown'):
        result[kind]=sum(q['kind']==kind for q in data['questions'])
    for state in ('unreadable','partial'):
        result[state]=sum(o['reading']==state for o in data['occurrences'])
    result['candidate_relations']=sum(r['type']!='variant_of' for r in data['relations'])
    result['unresolved']=len(data['audit']['unresolved'])
    return result
```

- [ ] **4. 페이지·그림·보류와 재정렬 회귀 테스트를 추가한다.**

```python
def test_exposed_image_cannot_be_problem_asset():
    data=populated()
    data['assets']=[dict(id='a1',path='assets/a.png',sha256='0'*64,location=location(),role='problem',answer_exposure='present')]
    assert validate_question_bank(data)

def test_complete_with_holds_is_valid_but_not_complete():
    data=populated(); data['occurrences'][0]['reading']='partial'
    data['occurrences'][0]['uncertainties']=[dict(block_id='b1',symbol='오버바',candidates=[],reason='흐림',location=location())]
    data['audit'].update(status='complete_with_holds',unresolved=[dict(target_id='o1',reason='오버바 판독 보류')])
    data['audit']['checks']['source_visual']='partial'
    assert validate_question_bank(data)==[]
    data['audit']['status']='complete'
    assert validate_question_bank(data)

@pytest.mark.parametrize('page', [0, 3, True])
def test_invalid_pdf_page(page):
    data=populated(); data['sources'][0].update(format='pdf',path='quiz.pdf',unit_kind='page',unit_count=2)
    data['occurrences'][0]['location']['pdf_page']=page
    data['questions'][0]['evidence'][0]['pdf_page']=1
    assert validate_question_bank(data)

def test_order_does_not_reissue_ids():
    data=populated()
    occurrence=copy.deepcopy(data['occurrences'][0]); occurrence['id']='o2'; occurrence['blocks'][0].update(id='b2',text='다른 조건')
    data['occurrences'].append(occurrence)
    question=copy.deepcopy(data['questions'][0]); question.update(id='q2',occurrence_ids=['o2'],representative_occurrence_id='o2')
    data['questions'].append(question)
    data['audit']['units'][0]['occurrence_ids'].append('o2')
    before=copy.deepcopy(data)
    for key in ('sources','assets','occurrences','questions','relations'): data[key].reverse()
    assert validate_question_bank(data)==[]
    assert {q['id'] for q in data['questions']}=={q['id'] for q in before['questions']}

def test_filename_header_conflict_requires_evidence():
    data=populated(); source=data['sources'][0]
    source['filename_metadata']['year']='2016'; source['observed_metadata']['year']='2017'
    assert validate_question_bank(data)
    source['conflicts']=[dict(field='year',filename_value='2016',observed_value='2017',location=location())]
    assert validate_question_bank(data)==[]

def test_shared_stem_subpart_references_existing_blocks():
    data=populated()
    data['questions'][0]['subparts']=[dict(id='part1',label='가',occurrence_id='o1',block_ids=['b1'])]
    assert validate_question_bank(data)==[]
    data['questions'][0]['subparts'][0]['block_ids']=['missing']
    assert validate_question_bank(data)

def test_duplicate_candidate_does_not_require_merge():
    data=populated()
    occurrence=copy.deepcopy(data['occurrences'][0]); occurrence['id']='o2'; occurrence['blocks'][0]['id']='b2'
    data['occurrences'].append(occurrence)
    question=copy.deepcopy(data['questions'][0]); question.update(id='q2',occurrence_ids=['o2'],representative_occurrence_id='o2')
    data['questions'].append(question); data['audit']['units'][0]['occurrence_ids'].append('o2')
    data['relations']=[dict(from_id='q1',to_id='q2',type='duplicate_candidate',reason='극성 재확인 필요',evidence=[location()])]
    assert validate_question_bank(data)==[]
    assert len(data['questions'])==2

def test_complete_pdf_must_account_for_every_page():
    data=populated(); data['sources'][0].update(format='pdf',path='quiz.pdf',unit_kind='page',unit_count=2)
    data['occurrences'][0]['location']['pdf_page']=1; data['questions'][0]['evidence'][0]['pdf_page']=1
    data['audit']['status']='complete'; data['audit']['checks']['source_visual']='pass'
    assert validate_question_bank(data)
    data['audit']['units'].append(dict(source_id='s1',index=2,outcome='blank',occurrence_ids=[],reason='빈 뒷면'))
    assert validate_question_bank(data)==[]
```

- [ ] **5. 해당 파일 테스트를 통과시키고 커밋한다.** `python -m pytest -n0 tests/test_review_pack_question_bank.py -q` → PASS.

```powershell
git add scripts/lab/review_pack/question_bank.py tests/test_review_pack_question_bank.py
git commit -m "feat: validate question provenance and audit states"
```

## Task 3: 빠짐없는 목록과 파일 무결성

**Files:** Create question_bank_sources.py, tests/test_review_pack_question_bank_sources.py; Modify question_bank.py and its test.

**Interfaces:**
- `inventory_quiz_sources(root: Path, experiment: int) -> list[dict]`: 설계의 source 행, filename/observed metadata는 우선 null, conflicts=[]; processing=pending. PDF unit_count=null, image/document는 1. 지원 여부 판정은 추출자가 한다.
- `check_question_bank_files(data: dict, *, root: Path, bank_dir: Path) -> list[str]`: 유효한 JSON의 source/asset 경로와 해시 검사; write 없음.
- source ID는 `s-` + NFC 정규화 POSIX 상대 경로 SHA256 앞 16자. 실제 path는 파일시스템 원형을 보존한다. 정규화 경로 충돌과 ID 충돌은 ValueError. 빈/없는 폴더도 ValueError.

- [ ] **1. 확장자 누락 및 원문 변경 테스트를 쓴다.**

```python
# tests/test_review_pack_question_bank_sources.py
from pathlib import Path
import pytest
from scripts.lab.review_pack.question_bank_sources import inventory_quiz_sources

def test_all_extensions_are_in_inventory(tmp_path):
    folder=tmp_path/'from_the_past/정리/퀴즈/실험4/원본_docx'; folder.mkdir(parents=True)
    for name in ('원본.doc','unknown.bin','문제.pdf','note.jpg','복사.docx'): (folder/name).write_bytes(b'evidence')
    rows=inventory_quiz_sources(tmp_path,4)
    assert len(rows)==5
    assert {r['format'] for r in rows}=={'doc','other','pdf','image','docx'}
    assert all(r['processing']=='pending' for r in rows)

def test_empty_source_folder_is_not_success(tmp_path):
    with pytest.raises(ValueError): inventory_quiz_sources(tmp_path,4)

def test_source_id_survives_content_change(tmp_path):
    folder=tmp_path/'from_the_past/정리/퀴즈/실험4'; folder.mkdir(parents=True)
    path=folder/'문제.txt'; path.write_bytes(b'one'); first=inventory_quiz_sources(tmp_path,4)[0]
    path.write_bytes(b'two'); second=inventory_quiz_sources(tmp_path,4)[0]
    assert first['id']==second['id'] and first['sha256']!=second['sha256']
```

- [ ] **2. 파일 검사 테스트를 question_bank 테스트 파일에 추가한다.**

```python
from hashlib import sha256
from scripts.lab.review_pack.question_bank import check_question_bank_files

def test_changed_source_and_missing_asset(tmp_path):
    data=populated(); (tmp_path/'quiz.txt').write_bytes(b'original')
    data['sources'][0]['sha256']=sha256(b'original').hexdigest()
    assert check_question_bank_files(data,root=tmp_path,bank_dir=tmp_path)==[]
    (tmp_path/'quiz.txt').write_bytes(b'changed')
    assert check_question_bank_files(data,root=tmp_path,bank_dir=tmp_path)
    data['sources'][0]['sha256']=sha256(b'changed').hexdigest()
    data['assets']=[dict(id='a1',path='assets/missing.png',sha256='0'*64,location=location(),role='mixed',answer_exposure='unknown')]
    assert check_question_bank_files(data,root=tmp_path,bank_dir=tmp_path)

@pytest.mark.parametrize('path',['../outside.txt','C:/outside.txt','/absolute.txt','a\\b.txt','.'])
def test_unsafe_source_path(tmp_path,path):
    data=populated(); data['sources'][0]['path']=path
    assert check_question_bank_files(data,root=tmp_path,bank_dir=tmp_path)
```

- [ ] **3. 두 테스트 파일을 실행해 새 함수가 없어 실패하는지 확인한다.** `python -m pytest -n0 tests/test_review_pack_question_bank.py tests/test_review_pack_question_bank_sources.py -q`.

- [ ] **4. 전체 파일 목록화와 containment 검사를 구현한다.** 기존 `config.experiment_folder_name`으로 실험 번호를 검사하고 `sources.file_sha256`을 재사용한다. 아래가 경로·형식 처리의 핵심 코드다.

```python
# inventory_quiz_sources에서 사용하는 형식 표
formats={'.pdf':'pdf','.docx':'docx','.doc':'doc','.png':'image','.jpg':'image','.jpeg':'image','.webp':'image','.tif':'image','.tiff':'image','.txt':'text','.md':'text'}
# 모든 파일을 수집하며 알 수 없는 확장자도 other로 반환한다.
files=sorted(p for p in folder.rglob('*') if p.is_file())
if not files: raise ValueError('No quiz source files: '+str(folder))
```

폴더가 없으면 먼저 동일한 ValueError를 낸다. 탐색 중 symlink/junction은 확인해 root 밖이면 실패한다. 심볼릭 디렉터리 내부를 탐색하지 못해 누락시키는 대신 링크 디렉터리 자체를 명시적 오류로 보고한다. 이 처리를 위해 rglob만 단독 사용하지 말고 os.walk(followlinks=False)의 dirs/files에서 is_symlink 및 사용 가능한 is_junction을 검사한다. 원문 파일 symlink도 거부하면 root 안/밖 여부와 관계없이 정책이 명확하다.

```python
# check_question_bank_files 내부 source/asset 각 행의 처리 패턴
from pathlib import PurePosixPath
from scripts.lab.review_pack.sources import file_sha256

relative=PurePosixPath(row['path'])
if relative.is_absolute() or row['path'] in ('','.') or '..' in relative.parts or '\\' in row['path'] or ':' in row['path']:
    errors.append(f'{at}.path: unsafe relative path')
else:
    target=(base/row['path']).resolve()
    if not target.is_relative_to(base.resolve()): errors.append(f'{at}.path: outside base')
    elif not target.is_file(): errors.append(f'{at}.path: missing file')
    elif file_sha256(target)!=row['sha256']: errors.append(f'{at}.sha256: changed file')
```

source의 base=root, asset의 base=bank_dir. asset은 relative.parts[0]=='assets'도 검사한다. OSError는 해당 JSON 경로 오류로 변환한다. 각 경로 segment의 symlink/junction도 검사한다. NFC 경로 충돌은 다른 원문으로 자동 합치지 않는다.

- [ ] **5. 링크·유니코드·미지원 PDF 보류 테스트를 추가한다.**

```python
# question_bank_sources 테스트 파일
def test_source_symlink_is_rejected(tmp_path):
    folder=tmp_path/'from_the_past/정리/퀴즈/실험4'; folder.mkdir(parents=True)
    target=tmp_path/'outside.txt'; target.write_text('x',encoding='utf-8')
    try: (folder/'link.txt').symlink_to(target)
    except OSError: pytest.skip('host cannot create symlink; record this validation limit')
    with pytest.raises(ValueError): inventory_quiz_sources(tmp_path,4)

def test_nfd_filename_keeps_resolvable_path(tmp_path):
    import unicodedata
    folder=tmp_path/'from_the_past/정리/퀴즈/실험4'; folder.mkdir(parents=True)
    path=folder/unicodedata.normalize('NFD','기출.txt'); path.write_bytes(b'x')
    row=inventory_quiz_sources(tmp_path,4)[0]
    assert (tmp_path/row['path']).is_file()

# question_bank 테스트 파일
def test_unknown_page_count_is_explicit_hold():
    data=bank()
    source=populated()['sources'][0]
    source.update(path='locked.pdf',format='pdf',unit_kind='page',unit_count=None,processing='held',reason='암호화')
    data['sources']=[source]
    data['audit'].update(status='complete_with_holds',units=[dict(source_id='s1',index=1,outcome='held',occurrence_ids=[],reason='암호화')],unresolved=[dict(target_id='s1',reason='페이지 수 확인 불가')])
    data['audit']['checks']['source_visual']='partial'
    assert validate_question_bank(data)==[]
```

- [ ] **6. 두 테스트 파일을 통과시키고 커밋한다.** skip은 통과로 숨기지 않고 검증 기록에 남긴다.

```powershell
python -m pytest -n0 tests/test_review_pack_question_bank.py tests/test_review_pack_question_bank_sources.py -q
git add scripts/lab/review_pack/question_bank.py scripts/lab/review_pack/question_bank_sources.py tests/test_review_pack_question_bank.py tests/test_review_pack_question_bank_sources.py
git commit -m "feat: inventory and verify question bank evidence"
```

## Task 4: 읽기 전용 CLI

**Files:** Create question_bank_cli.py, tests/test_review_pack_question_bank_cli.py.

**Interfaces:** `main(argv: list[str] | None = None) -> int`. 명령:

```powershell
python -m scripts.lab.review_pack.question_bank_cli inventory --root . --experiment 4
python -m scripts.lab.review_pack.question_bank_cli check --root . --bank 문제은행/실험04/question-bank.json
```

inventory는 `{experiment,sources}` JSON, check는 `{mechanical_check,audit_status,recorded_source_visual,counts}` JSON. 성공 0, JSON/검사/파일/빈 자료 오류 1, argparse 사용 오류 2. 실패는 stderr에 FAIL 및 이유. stdout은 UTF-8 JSON, ensure_ascii=False. 두 명령 모두 파일을 쓰지 않는다. checks.structure 값을 자동 수정하지 않는다.

- [ ] **1. CLI 통합 테스트를 쓴다.**

```python
import json
from scripts.lab.review_pack.question_bank_cli import main

def test_check_reports_draft_not_verified(tmp_path,capsys):
    source='tests/fixtures/review_pack/question_bank/minimal.json'
    assert main(['check','--root',str(tmp_path),'--bank',source])==0
    output=json.loads(capsys.readouterr().out)
    assert output['mechanical_check']=='pass'
    assert output['audit_status']=='draft'
    assert output['recorded_source_visual']=='not_run'

def test_invalid_json_has_nonzero_status(tmp_path,capsys):
    path=tmp_path/'bad.json'; path.write_text('{',encoding='utf-8')
    assert main(['check','--root',str(tmp_path),'--bank',str(path)])==1
    assert 'FAIL' in capsys.readouterr().err

def test_inventory_missing_is_failure(tmp_path,capsys):
    assert main(['inventory','--root',str(tmp_path),'--experiment','4'])==1
    assert 'FAIL' in capsys.readouterr().err
```

- [ ] **2. 모듈 부재로 테스트 실패를 확인한다.** `python -m pytest -n0 tests/test_review_pack_question_bank_cli.py -q`.

- [ ] **3. CLI를 아래 형태로 구현한다.** 모듈 import에 부작용이 없어야 한다.

```python
import argparse
import json
import sys
from pathlib import Path
from .question_bank import load_question_bank, check_question_bank_files, summarize_question_bank
from .question_bank_sources import inventory_quiz_sources

def main(argv=None):
    parser=argparse.ArgumentParser(description='Read-only question bank evidence checks')
    commands=parser.add_subparsers(dest='command',required=True)
    inv=commands.add_parser('inventory'); inv.add_argument('--root',type=Path,required=True); inv.add_argument('--experiment',type=int,required=True)
    check=commands.add_parser('check'); check.add_argument('--root',type=Path,required=True); check.add_argument('--bank',type=Path,required=True)
    args=parser.parse_args(argv)
    try:
        if args.command=='inventory':
            result={'experiment':args.experiment,'sources':inventory_quiz_sources(args.root,args.experiment)}
        else:
            data=load_question_bank(args.bank)
            errors=check_question_bank_files(data,root=args.root,bank_dir=args.bank.parent)
            if errors: raise ValueError('\n'.join(errors))
            result={'mechanical_check':'pass','audit_status':data['audit']['status'],
                    'recorded_source_visual':data['audit']['checks']['source_visual'],'counts':summarize_question_bank(data)}
        print(json.dumps(result,ensure_ascii=False,indent=2)); return 0
    except (ValueError,OSError) as exc:
        print('FAIL: '+str(exc),file=sys.stderr); return 1

if __name__=='__main__':
    if hasattr(sys.stdout,'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr,'reconfigure'): sys.stderr.reconfigure(encoding='utf-8')
    raise SystemExit(main())
```

- [ ] **4. CLI 테스트와 실험4 목록화만 실행한다.** 실제 판독이나 학습팩 생성은 하지 않는다.

```powershell
python -m pytest -n0 tests/test_review_pack_question_bank_cli.py -q
python -m scripts.lab.review_pack.question_bank_cli inventory --root . --experiment 4
```

2026-09-29 탐색 시 실험4에는 PDF/JPG/PNG/DOCX를 합쳐 11개 파일이 있었다. 변경 가능한 숫자이므로 테스트에 11을 고정하지 않는다. 현재 Get-ChildItem -Recurse -File 목록과 CLI의 path 집합을 대조한다.

- [ ] **5. 커밋한다.**

```powershell
git add scripts/lab/review_pack/question_bank_cli.py tests/test_review_pack_question_bank_cli.py
git commit -m "feat: expose read-only question bank checks"
```

## Task 5: 추출 인계 문서와 최종 수용 검토

**Files:** Create references/question-bank.md, references/question-bank-extraction-session.md; Modify SKILL.md: 자료 확인 절. 위 file map의 전체 경로가 기준이다.

**Interfaces:** 새 세션은 실제 source와 계약/CLI만 입력으로 받는다. 출력은 문제은행/실험04/question-bank.json, assets/, 검증결과.md. 이 task의 완료물은 도구와 인계 문서이며 실제 문제은행을 만들었다고 보고하지 않는다.

- [ ] **1. question-bank.md에 설계의 각 객체·enum·위치 규칙·상태 전이를 문서화한다.** schema JSON이 형식 정본, 설계와 question_bank.py가 의미 규칙임을 명시한다. 위 두 CLI 명령과 출력 키를 그대로 싣는다. 예제는 minimal.json을 가리키며 실제 기출로 오해시키지 않는다. import 경계에는 bank_id/schema_version/JSON SHA256 추적, 제공 답안 다중 보존, 독립 풀이 단계 분리, checks 전이 금지를 쓴다.

- [ ] **2. SKILL.md 자료 확인 절 앞에 다음 안내를 넣는다.** 기존 생성 절을 지우거나 아직 없는 import 명령을 안내하지 않는다.

```markdown
### 별도 세션에서 추출한 문제은행

기출 원문 추출은 [문제은행 계약](references/question-bank.md)과
[새 추출 세션 절차](references/question-bank-extraction-session.md)를 따른다.
문제은행 JSON은 manifest.json과 다른 계약이다. 현재 전용 import는 미구현이다.
문제은행 추출 요청에서는 여기의 학습팩 build/publish 절을 실행하지 않는다.
기존 임시 분석을 검증된 문제은행으로 사용하지 않는다.
```

- [ ] **3. 새 세션 인계 문서에 아래 요청과 순서를 기록한다.** 새 chat을 자동 생성하지 않는다. 사용자가 새 세션에 이 문서를 전달하면 그 세션에서 실행한다.

```text
기존 codex/logic-lab-review-pack 워크트리에서 실험4의 원자료 전체를 새로 판독하여
문제은행/실험04/question-bank.json 및 assets/, 검증결과.md를 만들어라.
question-bank.md, question-bank.schema.json, 추출 설계를 먼저 읽어라.
pdf 스킬로 회로·표·기호를 시각 대조하고 DOCX는 documents 스킬의 읽기 절차를 사용하라.
임시 분석 tmp/review-pack-work/experiment04는 열람·전재하지 마라.
제공 답안을 보존하되 독립 풀이·학습팩 생성·Task 8·원래 체크아웃 통합은 하지 마라.
```

1. `git status --short` 및 CLI inventory로 원자료 집합을 확인한다. 대상 폴더 밖의 인터넷 자료나 보고서 답안을 정답 근거로 섞지 않는다.
2. `tmp/question-bank/실험04-<고유실행ID>`를 새로 만들고 원문을 렌더한다. pdf/documents 스킬의 사용 가능한 도구를 확인한다. 변환 결과는 원본을 덮어쓰지 않는다.
3. 파일별 unit_count와 원문 메타데이터를 기록한다. `2016-1` 파일명/헤더 차이, 종합본의 예상문제 혼합, 해설의 선 수·X 표기·부품명은 확인할 단서이며 사실로 미리 입력하지 않는다.
4. 파일 하나씩 모든 페이지/문서 단위를 감사한다. occurrence/blocks/그림을 먼저 기록하고 판독 불가도 남긴다. 반복 전사가 끝난 뒤 question 묶기와 답안 연결을 한다.
5. 검증 CLI를 실행해 오류를 수정한다. 구조 통과만으로 source_visual=pass를 쓰지 않는다. 근거 그림을 실제로 원문과 대조하고 metadata conflict·불확실성·보류 수를 검증결과.md에 기록한다.
6. 원문 해시를 다시 확인한다. 새로 만든 은행의 상태가 complete 또는 complete_with_holds인지 확인한다. draft는 tmp에 보존하고 정본으로 내보내지 않는다.
7. 최종 폴더가 없을 때만 JSON/근거 이미지/검증결과.md를 복사하고 최종 경로에서 CLI check를 다시 실행한다. 기존 폴더가 있으면 새 작업본과 차이를 보고하고 덮어쓰지 않는다.
8. 보고는 경로·기계 검사·시각 판독 범위·고유 기출/예상/미확인 수·보류·미연결 답안을 포함한다. 독립 풀이 검증이나 학습팩 완성을 주장하지 않는다. 원래 계획 Task 8을 재개하지 않는다.

- [ ] **4. 문서·스키마와 코드를 자체 대조한다.** 모든 키/enum/API/CLI 옵션이 일치하는지 확인한다. schema가 사용하는 키워드는 type/enum/properties/required/additionalProperties/items/minItems/maxItems/pattern/minimum/maximum 및 $schema 메타데이터뿐이어야 한다. 다른 키워드를 추가하면 _shape_errors가 무시하지 않도록 지원을 먼저 구현하거나 사용을 철회한다.

- [ ] **5. 관련 회귀 검사와 diff 검토를 한다.** 테스트 대상은 신규 세 파일과 기존 review_pack 여섯 파일이다.

```powershell
python -m pytest -n0 tests/test_review_pack_question_bank.py tests/test_review_pack_question_bank_sources.py tests/test_review_pack_question_bank_cli.py tests/test_review_pack_sources.py tests/test_review_pack_manifest.py tests/test_review_pack_render.py tests/test_review_pack_md.py tests/test_review_pack_checks.py tests/test_review_pack_publish.py -q
git diff --check
git diff --stat
git status --short
```

원자료·템플릿·보고서 및 기존 manifest 계약 변경이 없는지 확인한다. 이 범위 밖 전체 테스트는 실행한 경우에만 보고하며 config의 알려진 Windows 실패를 새 기능 실패와 구분한다. 생명과학 화면이나 브라우저 검증을 이번 CLI 검증으로 대체하지 않는다.

- [ ] **6. Native 실행의 최종 독립 코드 리뷰를 요청한다.** 전체 이번 변경과 설계·테스트 결과를 리뷰어에게 전달한다. 누락·잘못된 완료 상태·원문 변조 가능성·예외 누출을 검토한다. 실제 기출 해석에 대한 독립 리뷰가 아니며 그렇게 표기하지 않는다. 발견 사항 수정 후 해당 검사만 재실행한다. 리뷰 도구를 사용할 수 없으면 독립 리뷰 미실시를 명시한다.

- [ ] **7. 문서를 커밋하고 도구 단계 완료를 보고한다.**

```powershell
git add .claude/skills/logic-lab-review-pack/references/question-bank.md .claude/skills/logic-lab-review-pack/references/question-bank-extraction-session.md .claude/skills/logic-lab-review-pack/SKILL.md
git commit -m "docs: document independent question bank extraction"
```

완료 보고에는 CLI, 계약 문서, 새 세션용 요청 링크, 실제 테스트 결과와 미실시 검증을 포함한다. 실제 실험4 추출은 별도 새 세션에서 시작할 다음 작업으로 남긴다. import와 Task 8은 이번 계획의 완료 조건이 아니다.

## 계획 자체 검토

- 승인된 결정 #0/B, #1 추출 우선, #2 실험4 우선, #3~9 증거·답안·감사 경계는 설계와 각 task에 반영했다.
- 계약 객체/저장 단위는 Task 1, 관계·답안·판독·완료 상태는 Task 2, 모든 파일·hash·안전 경로는 Task 3, 관찰 가능한 CLI는 Task 4, 실제 새 세션 절차 및 import 경계는 Task 5가 담당한다.
- Review Focus 다섯 항목은 Task 2~4의 구체 테스트에 연결했다. source link 테스트의 호스트 권한 skip은 검증 한계로 남긴다.
- 공개 함수명 및 반환 키는 Interfaces가 정본이다. 기존 학습팩 manifest와 import를 혼동하지 않는다.
- 문서-only 계획 작성 단계에서 구현·테스트·독립 리뷰·실제 기출 추출을 완료했다고 주장하지 않는다.
- 이 계획의 Task 1~5를 실행한 뒤 새 세션 추출, 이후 별도 import 계획과 Task 8 순서로 진행한다.
