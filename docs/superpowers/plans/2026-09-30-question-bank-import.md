# Question Bank Import Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 완료된 문제은행을 출처·답안·보류 증거가 유지되는 학습팩 저작 초안으로 가져오고 기존 build/check/publish에 연결한다.

**Architecture:** import는 은행의 바이트 동일 사본과 자산, 파생 저작 인덱스, 모든 문항을 held로 둔 유효 manifest를 생성한다. 고정 추출 정보와 저작자가 바꿀 상태를 구분하고 build/check/publish에서 연결·해시를 검증한다. 기존 학습팩과 생명과학 템플릿은 유지한다.

**Tech Stack:** 기존 Python + 표준 라이브러리, pytest/pytest-xdist, 기존 question_bank 검증기와 HTMLParser. 새 런타임 의존성 없음.

**Spec:** [승인된 import 연결 설계](../specs/2026-09-30-question-bank-import-design.md). 실행자는 이 문서와 명세를 함께 읽는다. 사용자의 writing-plans 호출은 파일 명세 승인으로 반영하며 실행 방식은 기존 Native를 유지한다. 이 계획의 검토 전 구현을 시작하지 않는다.

## Global Constraints

- Python 표준 라이브러리만 사용한다.
- 기존 실험4 문제은행·원문 자료·원문 자산은 수정하지 않는다.
- 문항 ID와 분류를 임의로 변경하거나 variant_of 문항을 자동 병합하지 않는다.
- 제공 답안의 confirmed/candidate는 연결 상태이며 정답 검증 상태가 아니다.
- 추출 검사 결과를 학습팩 content/independent/browser의 pass로 복사하지 않는다.
- 생명과학 note-template.html/review-template.html과 기존 출력 네 파일을 유지한다.
- 답 노출 present/unknown 자산을 답 없는 문제 본문에 자동 삽입하지 않는다.
- 기존 run/stage/최종 팩을 import에서 덮어쓰지 않는다.
- 문제은행 JSON의 정확한 바이트와 SHA256을 보존한다.
- JSON에 없는 풀이·개념·문제 조건을 import가 생성하지 않는다.

## Review Focus

1. 원문 파일명의 NFD 한글·공백·괄호: 실제 디스크 경로를 보존하고 파일을 찾는다. Task 2 경로 테스트.
2. 같은 문항에 여러 답안·후보 연결·소문항이 있음: 추출 순서와 모든 연결을 유지하고 정답으로 승격하지 않는다. Task 1 복합 fixture.
3. present/unknown 원문 이미지를 이름만 바꿔 figures에 복사함: 같은 바이트 해시도 인식해 문제 영역 사용을 거절한다. Task 4 자산 테스트.
4. snapshot·인덱스가 일치하지만 원래 은행/원자료가 변경됨: 로컬 check와 현재 입력 대조를 구분하고 build/publish는 실패한다. Task 3 및 Task 5 테스트.
5. 대표 원문은 partial이고 다른 등장 또는 답안은 readable: 판독 문제를 자동 해결하거나 included로 승격하지 않는다. Task 3 보류 테스트.

---

## 작업 위치·현재 코드·파일 책임

작업 위치: `C:/Users/Hyunjun/.codex/worktrees/logic-lab-review-pack/논회실`, 브랜치 `codex/logic-lab-review-pack`. 새 worktree를 만들지 않는다. 기준 커밋은 명세를 추가한 `50a5e41`; 실제 실행 전에 git 상태를 다시 확인한다.

현재 `question_bank.load_question_bank(path)`는 중복 JSON 키를 거절한다. `check_question_bank_files(data, root=..., bank_dir=...)`는 source/asset 해시를 읽기 전용으로 확인한다. `question_bank_sources._evidence_path(base, relative)`는 POSIX 상대 경로와 Windows junction/symlink를 검사한다.

`manifest.validate_manifest(data)`의 held 문항은 topics=[]·fragment 없음으로 유효하다. 기존 source ID와 problem ID는 전역 유일하다. 기존 CLI의 build는 assemble→convert_pack→check_pack 순서이며 import는 없다. publish는 check_pack 다음 원자료·검증 상태·generated_files를 검사한다.

명세의 bank_import.py 책임을 작은 파일로 나눈다. 동작과 공개 CLI 계약은 바꾸지 않는다.

| 파일 | 책임 |
|---|---|
| `scripts/lab/review_pack/bank_index.py` | 인덱스·초기 manifest 파생, optional 필드 형식 검사 |
| `scripts/lab/review_pack/bank_import.py` | 입력 검증 후 새 run에 snapshot·증거·인덱스·안내 생성/복사 |
| `scripts/lab/review_pack/bank_provenance.py` | 로컬 증거·문항 연결·현재 입력의 일치 검사 |
| `scripts/lab/review_pack/bank_asset_checks.py` | 문제 화면의 은행 자산 답 노출 검사 |
| `manifest.py` | legacy 계약에 optional bank_import와 bank_question_id 연결 |
| `__main__.py` | import-bank와 build 사전 검사 |
| `render.py` | 증거 복사와 원문·저작 안내 탐색 링크 |
| `checks.py` | 새 증거·자산 검사를 기존 검사에 연결 |
| `publish.py` | 현재 은행·원자료 대조 |
| `tests/_bank_import_fixture.py` | 파일을 가진 최소 은행 테스트 입력 |
| `tests/test_review_pack_bank_index.py` | 파생·형식 계약 |
| `tests/test_review_pack_bank_import.py` | 새 run 생성 및 입력 보존 |
| `tests/test_review_pack_bank_provenance.py` | 증거·연결 변조와 현재 입력 변경 |
| `tests/test_review_pack_bank_assets.py` | 답 노출·우회 경로 |
| `tests/test_review_pack_bank_import_flow.py` | CLI→build→check→publish, legacy 회귀 |
| `.claude/skills/logic-lab-review-pack/SKILL.md` | JSON이 있으면 import를 사용하는 실행 흐름 |
| 같은 스킬의 `references/question-bank.md`, `format.md`, `verification.md` | 명령·계약·검증 설명 |
| `docs/verify/2026-09-30-question-bank-import.md` | 실제 은행 수용 결과·한계 |

실행 전 관련 baseline은 아래 PowerShell 명령으로 실행한다. PowerShell은 외부 명령의 wildcard를 자동 확장하지 않으므로 파일 목록을 명시적으로 전달한다.

```powershell
$reviewPackTests = @(Get-ChildItem tests -Filter 'test_review_pack*.py' | ForEach-Object FullName)
python -m pytest -n0 @reviewPackTests -q
```

전체 저장소의 이전 실패 목록은 `docs/verify/2026-09-29-question-bank-extraction.md`에 있다. 명령 출력을 작업 ledger에 기록하고 기존 실패를 이번 수정으로 인한 실패와 구분한다.

## Task 1: 파생 인덱스와 manifest 계약

**Files:** Create `bank_index.py`, `tests/_bank_import_fixture.py`, `tests/test_review_pack_bank_index.py`; Modify `manifest.py:14-97`.

**Interfaces:**
- Consumes: shape·semantic 검사를 통과한 문제은행 dict; 은행 bytes의 SHA256 문자열.
- Produces: `build_authoring_index(bank: dict, bank_sha256: str) -> dict`; `initial_manifest(bank: dict, source_path: str, bank_sha256: str) -> dict`; `validate_bank_import_fields(manifest: dict) -> list[str]`.
- 인덱스의 고정 정보는 spec의 필드 전체이며 가변 필드는 authoring_status·selection_reason뿐이다.
- authoring_status enum은 pending/reading_hold/ready/not_selected/held로 정한다. ready는 독립 검토 완료를 뜻하지 않는다. not_selected/held는 비어 있지 않은 selection_reason을 요구한다.
- bank_import는 bank_id/schema_version/source_path/sha256/snapshot_path/index_path 6개 필드만 허용한다. 경로는 import 생성값 evidence/question-bank.json, authoring-index.json을 사용한다.

- [ ] **Step 1: 파일이 있는 최소 은행 fixture를 작성한다.** 테스트 전용 코드이며 생산 모듈은 아직 만들지 않는다.

```python
# tests/_bank_import_fixture.py
import copy
import hashlib
import json
from pathlib import Path

def create_bank(root: Path, *, relative='문제은행/실험04/question-bank.json'):
    from tests.test_review_pack_question_bank import populated
    bank = populated()  # 이미 유효한 1 source/1 question의 기존 테스트 입력
    source = root / 'quiz.txt'
    source.write_bytes(b'original quiz evidence')
    bank['sources'][0]['sha256'] = hashlib.sha256(source.read_bytes()).hexdigest()
    bank['audit'].update(status='complete')
    bank['audit']['checks'].update(structure='pass', source_visual='pass')
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(bank, ensure_ascii=False, indent=2), encoding='utf-8')
    return path, bank

def save_bank(path: Path, bank: dict):
    path.write_text(json.dumps(bank, ensure_ascii=False, indent=2), encoding='utf-8')

def add_answer(bank: dict, ident: str, value: str, status: str):
    occurrence = copy.deepcopy(bank['occurrences'][0])
    occurrence.update(id=ident, role='answer')
    occurrence['blocks'] = [dict(id='b-' + ident, type='text',
        text=value, tex=None, cells=None, asset_id=None)]
    bank['occurrences'].append(occurrence)
    bank['audit']['units'][0]['occurrence_ids'].append(ident)
    bank['questions'][0]['answers'].append(dict(
        occurrence_id=ident, target_id='q1', status=status, reason='provided association'))
    return occurrence

def add_asset(path: Path, bank: dict, ident: str, role: str, exposure: str, content: bytes):
    import copy
    asset_file = path.parent / 'assets' / (ident + '.png')
    asset_file.parent.mkdir(exist_ok=True)
    asset_file.write_bytes(content)
    row = dict(id=ident, path='assets/' + ident + '.png',
        sha256=hashlib.sha256(content).hexdigest(),
        location=copy.deepcopy(bank['occurrences'][0]['location']),
        role=role, answer_exposure=exposure)
    bank['assets'].append(row)
    return row

def mark_partial(bank: dict):
    occurrence = bank['occurrences'][0]
    occurrence.update(reading='partial', uncertainties=[dict(
        block_id='b1', symbol='overbar', candidates=['present','absent'],
        reason='blurred', location=copy.deepcopy(occurrence['location']))])
    bank['audit'].update(status='complete_with_holds',
        unresolved=[dict(target_id='o1', reason='blurred')])
    bank['audit']['checks']['source_visual'] = 'partial'
```

현재 test module의 populated가 fixture 제공 함수다. import 방향은 테스트→테스트만이며 생산 코드에서 import하지 않는다. 이후 기존 함수 변경이 필요해지면 테스트 공용 helper로 함께 옮긴다.

- [ ] **Step 2: 상태 승격·연결 누락을 잡는 테스트를 먼저 작성한다.**

```python
from scripts.lab.review_pack.bank_index import build_authoring_index, initial_manifest
from scripts.lab.review_pack.manifest import validate_manifest
from tests._bank_import_fixture import create_bank, add_answer, mark_partial

def test_import_does_not_promote_provided_answers(tmp_path):
    path, bank = create_bank(tmp_path)
    add_answer(bank, 'a-confirmed', '0', 'confirmed')
    add_answer(bank, 'a-candidate', '1', 'candidate')
    index = build_authoring_index(bank, '0' * 64)
    assert index['questions'][0]['provided_answers'] == bank['questions'][0]['answers']
    manifest = initial_manifest(bank, path.relative_to(tmp_path).as_posix(), '0' * 64)
    assert validate_manifest(manifest) == []
    assert manifest['checks'] == dict(source_visual='not_run', content='not_run',
                                     independent='not_run', browser='not_run')
    assert manifest['problems'][0]['status'] == 'held'
    assert manifest['problems'][0]['derived_answer'] is None
    assert manifest['problems'][0]['given_answer'] is None

def test_partial_stays_reading_hold(tmp_path):
    _, bank = create_bank(tmp_path)
    mark_partial(bank)
    row = build_authoring_index(bank, '0' * 64)['questions'][0]
    assert row['authoring_status'] == 'reading_hold'
    assert row['unresolved'] == [dict(target_id='o1', reason='blurred')]
```

- [ ] **Step 3: RED를 확인한다.** Run `python -m pytest -n0 tests/test_review_pack_bank_index.py -q`. Expected: 새 bank_index import 부재. 문법·fixture 실패이면 먼저 고친다.
- [ ] **Step 4: 결정적 파생과 형식 검사를 구현한다.**

```python
def question_sources(bank, question):
    occurrences = {row['id']: row for row in bank['occurrences']}
    return [
        dict(occurrences[ident]['location'],
             question=occurrences[ident]['original_number'])
        for ident in question['occurrence_ids']
    ]
```

build_authoring_index는 deepcopy로 question 필드를 보존한다. 각 question의 대상 집합은 question ID, subpart IDs, question occurrence IDs, 그 block IDs, answers 및 answer_candidate relation이 가리키는 해당 문항/소문항의 답안 occurrence IDs와 blocks, 그 위치의 source IDs 및 연결 asset IDs다. audit.unresolved에서 이 집합에 속한 항목을 원래 순서대로 가져온다. variant_of 관계를 따라 다른 question의 모든 답안까지 가져오지 않는다. 해당 문항과 직접 관련된 relation 자체는 모두 보존한다.

safe_problem_asset_ids는 해당 question occurrence의 figure block이 참조한 자산 중 role=problem/exposure=none만 담는다. 답안 occurrence 자산과 나머지는 evidence_only_asset_ids로 분류한다. ID 목록은 원문 등장 순서에서 중복만 제거한다. 선언된 다른 자산도 전체 snapshot에서는 유지한다.

initial_manifest는 spec 초기값을 사용한다. problems의 id=bank_question_id=은행 question ID이며 sources에 모든 원문 위치를 넣는다. checks 모두 not_run, topics=[]다. 은행 snapshot은 아직 파일로 쓰지 않는다.

validate_bank_import_fields는 bank_import 객체의 정확한 키·문자열 bank ID·정수 버전 1·SHA256·엄격한 경로를 검사한다. bank_question_id가 있는데 bank_import가 없으면 오류다. 은행 수입 행은 id와 bank_question_id가 같아야 한다. legacy manifest는 이 필드가 없으면 빈 오류 목록이다. bool/list/dict를 enum/hash 검사에 넣어도 예외가 아니라 finding을 반환한다. 기존 validate_manifest 끝에서 이 함수의 오류를 합친다.

- [ ] **Step 5: 추가 행동 테스트를 작성·실행한다.**

```python
def test_reordering_preserves_question_id(tmp_path):
    import copy
    _, bank = create_bank(tmp_path)
    second = copy.deepcopy(bank['occurrences'][0])
    second['id'] = 'o2'; second['blocks'][0].update(id='b2', text='different condition')
    bank['occurrences'].append(second)
    bank['audit']['units'][0]['occurrence_ids'].append('o2')
    q = copy.deepcopy(bank['questions'][0])
    q.update(id='q2', occurrence_ids=['o2'], representative_occurrence_id='o2')
    bank['questions'].append(q)
    bank['relations'].append(dict(from_id='q1',to_id='q2',type='variant_of',
        reason='different condition',evidence=[copy.deepcopy(second['location'])]))
    first = initial_manifest(bank, 'bank.json', '0'*64)
    bank['questions'].reverse()
    second_manifest = initial_manifest(bank, 'bank.json', '0'*64)
    assert {p['id'] for p in first['problems']} == {'q1','q2'}
    assert {p['id'] for p in second_manifest['problems']} == {'q1','q2'}
```

다음 테스트로 subpart ID·candidate 관계·source 보류를 검증한다.

```python
def test_subpart_candidate_and_source_hold_are_preserved(tmp_path):
    import copy
    _, bank = create_bank(tmp_path)
    question = bank['questions'][0]
    question['subparts'] = [dict(id='part1',label='가',occurrence_id='o1',block_ids=['b1'])]
    answer = add_answer(bank,'a-part','provided value','candidate')
    question['answers'][0]['target_id']='part1'
    relation=dict(from_id='a-part',to_id='part1',type='answer_candidate',
        reason='subpart association',evidence=[copy.deepcopy(answer['location'])])
    bank['relations']=[relation]
    hold=dict(target_id='s1',reason='edition uncertain')
    bank['audit'].update(status='complete_with_holds',unresolved=[hold])
    index=build_authoring_index(bank,'0'*64)['questions'][0]
    assert index['subparts']==question['subparts']
    assert index['provided_answers']==question['answers']
    assert index['relations']==[relation]
    assert hold in index['unresolved']
```

잘못된 bank_import 경로 `../bank.json`, 배열 schema_version, 알 수 없는 필드, 다른 bank_question_id도 오류로 검사한다. Run `python -m pytest -n0 tests/test_review_pack_bank_index.py tests/test_review_pack_manifest.py -q`. Expected: PASS.
- [ ] **Step 6: 커밋한다.** `git add scripts/lab/review_pack/bank_index.py scripts/lab/review_pack/manifest.py tests/_bank_import_fixture.py tests/test_review_pack_bank_index.py`; `git commit -m "feat: define question bank authoring bridge"`.

## Task 2: 검증 후 증거가 보존되는 import 명령

**Files:** Create `bank_import.py`, `tests/test_review_pack_bank_import.py`; Modify `__main__.py:1-48`.

**Interfaces:**
- Consumes: Task 1 `build_authoring_index`, `initial_manifest`; 기존 load_question_bank, check_question_bank_files, _evidence_path, file_sha256.
- Produces: `import_bank(root: Path, bank_path: Path, run: Path) -> Path`; `copy_import_material(run: Path, out: Path, manifest: dict) -> None`.
- CLI import-bank는 --root/--bank/--run 필수, --experiment 불필요(은행 값 사용). 성공은 새 run 경로와 import된 항목 수, 실패는 기존 CLI의 FAIL과 exit 1.

- [ ] **Step 1: 새 run 생성과 원문 보존 테스트를 작성한다.**

```python
import json
import pytest
from scripts.lab.review_pack.bank_import import import_bank
from tests._bank_import_fixture import create_bank, add_asset, save_bank

def test_snapshot_and_all_assets_are_byte_identical(tmp_path):
    path, bank = create_bank(tmp_path)
    add_asset(path, bank, 'img-answer', 'answer', 'present', b'answer evidence')
    save_bank(path, bank)
    original = path.read_bytes()
    run = tmp_path / 'tmp' / 'authoring'
    assert import_bank(tmp_path, path, run) == run
    assert (run/'evidence/question-bank.json').read_bytes() == original
    assert (run/'evidence/assets/img-answer.png').read_bytes() == b'answer evidence'
    assert path.read_bytes() == original
    assert (tmp_path/'quiz.txt').read_bytes() == b'original quiz evidence'
    assert json.loads((run/'manifest.json').read_text(encoding='utf-8'))['checks']['browser']=='not_run'

def test_invalid_asset_does_not_create_run(tmp_path):
    path, bank = create_bank(tmp_path)
    asset = add_asset(path, bank, 'broken', 'mixed', 'unknown', b'original')
    save_bank(path, bank)
    (path.parent/asset['path']).write_bytes(b'changed')
    run = tmp_path/'not-created'
    with pytest.raises(ValueError):
        import_bank(tmp_path,path,run)
    assert not run.exists()
```

- [ ] **Step 2: RED를 확인한다.** `python -m pytest -n0 tests/test_review_pack_bank_import.py -q`. Expected: bank_import import 부재.
- [ ] **Step 3: 읽기 전용 사전 검사와 배타적 출력 생성을 구현한다.**

```python
bank = load_question_bank(bank_path)
errors = check_question_bank_files(bank, root=root, bank_dir=bank_path.parent)
if bank['audit']['status'] not in ('complete','complete_with_holds'):
    errors.append('Import requires a finished question bank')
if errors:
    raise ValueError('\n'.join(errors))
raw = bank_path.read_bytes()
digest = hashlib.sha256(raw).hexdigest()
```

파일을 여러 번 읽으며 다른 버전을 섞지 않게, 사전 검사한 파일 해시와 마지막 raw bytes를 대조한다. 작업 중 은행·원문·자산이 변경되면 성공 처리하지 않는다. bank_path의 실제 root 상대 철자를 보존하고 _evidence_path로 링크·탈출을 검사한다.

run은 root 내부의 새 경로로 제한한다. bank_dir와 서로 조상·자손 관계면 거절한다. 기존 run·깨진 링크도 거절한다. 기존 파일을 지우거나 recursive overwrite하지 않는다. 검증 후 임시 sibling에 모든 파일을 완성하고 마지막에 run.mkdir(exist_ok=False)로 경로를 배타적으로 확보해 새로 만든 파일만 이동한다. 출력 경합이나 I/O 실패에서는 불완전 출력 경로를 보고하고 성공 메시지를 쓰지 않는다.

snapshot은 raw를 write_bytes한다. 선언된 asset만 _evidence_path로 찾아 동일 상대 경로에 copy2하고 해시를 재검사한다. authoring-index와 manifest는 UTF-8 JSON. 안내 MD는 분류·모든 제공 답안 ID/status/target/reason·보류·원문 위치·snapshot/asset 링크를 포함한다. 원문 전사 전체는 snapshot으로 접근하며 scalar 정답으로 축소하지 않는다.

copy_import_material은 manifest.bank_import가 없으면 아무것도 하지 않는다. 있으면 snapshot·선언 자산·index·안내만 out에 복사한다. 내부 검사 실패 또는 대상 파일 충돌은 ValueError이며 임의 다른 run 파일을 복사하지 않는다.

- [ ] **Step 4: CLI를 연결하고 draft·경로·overwrite를 검사한다.**

```python
def test_existing_run_is_preserved(tmp_path):
    path, bank = create_bank(tmp_path)
    run=tmp_path/'run'; run.mkdir(); (run/'memo').write_text('keep')
    with pytest.raises(ValueError):
        import_bank(tmp_path,path,run)
    assert (run/'memo').read_text()=='keep'

def test_draft_is_not_imported(tmp_path):
    path, bank = create_bank(tmp_path)
    bank['audit']['status']='draft'; save_bank(path,bank)
    with pytest.raises(ValueError):
        import_bank(tmp_path,path,tmp_path/'run')
    assert not (tmp_path/'run').exists()

def test_nfd_filename_survives(tmp_path):
    import unicodedata
    filename=unicodedata.normalize('NFD','문제은행/실험04/은행 (1).json')
    path, _=create_bank(tmp_path,relative=filename)
    run=tmp_path/'run'
    import_bank(tmp_path,path,run)
    data=json.loads((run/'manifest.json').read_text(encoding='utf-8'))
    assert data['bank_import']['source_path']==path.relative_to(tmp_path).as_posix()
```

추가 테스트: 외부 bank 경로, run=bank_dir, 잘못된 은행 버전·실험 번호, symlink/junction, 출력 생성 도중 OSError. 링크 권한이 없는 Windows는 테스트를 skip하고 가능한 플랫폼에서 실행한다. CLI 테스트는 main을 실제 argument 배열로 호출해 exit code와 파일 효과를 확인한다. Run `python -m pytest -n0 tests/test_review_pack_bank_import.py tests/test_review_pack_question_bank_cli.py -q`. Expected: PASS.
- [ ] **Step 5: 커밋한다.** `git add scripts/lab/review_pack/bank_import.py scripts/lab/review_pack/__main__.py tests/test_review_pack_bank_import.py`; `git commit -m "feat: import question banks without changing evidence"`.

## Task 3: 로컬 snapshot·인덱스·현재 은행의 검증

**Files:** Create `bank_provenance.py`, `tests/test_review_pack_bank_provenance.py`.

**Interfaces:**
- Consumes: Task 1 파생 함수, Task 2 run·snapshot.
- Produces: `check_bank_import(folder: Path, manifest: dict, *, root: Path | None = None) -> list[str]`.
- root=None은 로컬 snapshot/assets/index/manifest 연결만 확인한다. root가 있으면 원래 bank_path bytes와 원자료·원래 자산도 확인한다. legacy manifest는 [].

- [ ] **Step 1: 인덱스 변조·현재 은행 변경 테스트를 작성한다.**

```python
import json
from scripts.lab.review_pack.bank_import import import_bank
from scripts.lab.review_pack.bank_provenance import check_bank_import
from tests._bank_import_fixture import create_bank

def imported(tmp_path):
    path, _=create_bank(tmp_path)
    run=tmp_path/'run'; import_bank(tmp_path,path,run)
    manifest=json.loads((run/'manifest.json').read_text(encoding='utf-8'))
    return path,run,manifest

def test_origin_change_is_not_a_local_snapshot_failure(tmp_path):
    path,run,manifest=imported(tmp_path)
    path.write_bytes(path.read_bytes()+b'\n')
    assert check_bank_import(run,manifest)==[]
    assert check_bank_import(run,manifest,root=tmp_path)

def test_fixed_index_data_cannot_be_rewritten(tmp_path):
    _,run,manifest=imported(tmp_path)
    p=run/'authoring-index.json'
    index=json.loads(p.read_text(encoding='utf-8'))
    index['questions'][0]['kind']='past'
    p.write_text(json.dumps(index),encoding='utf-8')
    assert check_bank_import(run,manifest)
```

- [ ] **Step 2: RED를 확인한다.** `python -m pytest -n0 tests/test_review_pack_bank_provenance.py -q`. Expected: bank_provenance import 부재.
- [ ] **Step 3: 추출 정보의 일치 검사를 구현한다.**

```python
snapshot = _evidence_path(folder, manifest['bank_import']['snapshot_path'])
if file_sha256(snapshot) != manifest['bank_import']['sha256']:
    return ['$.bank_import.sha256: snapshot changed']
bank = load_question_bank(snapshot)
expected = build_authoring_index(bank, manifest['bank_import']['sha256'])
```

snapshot bank_id/version/experiment를 metadata·manifest와 대조한다. asset path/hash를 snapshot.parent 기준으로 검사하되 root=None이면 source 파일 확인을 시도하지 않는다. check_question_bank_files를 root=None로 호출하면 원문 경로 기준이 틀리므로 asset subset을 별도로 검사한다.

authoring-index를 중복 JSON 키 거절 방식으로 읽는다. exact shape를 검사하고 허용된 가변 필드 외의 최상위·question 필드를 expected와 대조한다. question 배열 순서는 변경 가능하지만 question ID 집합은 같아야 하고 중복 ID는 거절한다. provided_answers, occurrence_ids, relations, unresolved의 원래 순서는 보존한다. index selection_reason은 문자열이고 not_selected/held이면 비어 있지 않아야 한다.

manifest에서 bank_question_id를 가진 행의 집합은 bank questions 집합과 정확히 같아야 한다. id/kind/source 위치·질문 번호를 initial_manifest의 행과 대조한다. source ID/path/hash는 은행과 같아야 한다. topics/독립 풀이/상태/선별 이유는 저작자가 수정할 수 있으며 새로운 practice 문항과 교안 source 추가를 허용한다.

은행 representative reading이 partial/unreadable이면 included를 거절한다. 답안 관련 hold만 있는 readable 문제는 disputed/unresolved로 저작 가능하다. root가 있으면 original JSON bytes 해시와 check_question_bank_files도 재확인한다. 오류 문자열에는 문제 ID 또는 JSON 경로와 source/asset ID를 넣는다.

- [ ] **Step 4: 누락·관계·보류·가변 필드 테스트를 추가한다.**

```python
def test_question_cannot_disappear(tmp_path):
    _,run,manifest=imported(tmp_path)
    manifest['problems']=[]
    assert check_bank_import(run,manifest)

def test_partial_representative_cannot_be_included(tmp_path):
    from tests._bank_import_fixture import mark_partial, save_bank
    path,bank=create_bank(tmp_path);mark_partial(bank);save_bank(path,bank)
    run=tmp_path/'run';import_bank(tmp_path,path,run)
    manifest=json.loads((run/'manifest.json').read_text(encoding='utf-8'))
    manifest['problems'][0].update(status='included')
    assert any('q1' in error for error in check_bank_import(run,manifest))

def test_selection_reason_is_editable(tmp_path):
    _,run,manifest=imported(tmp_path)
    p=run/'authoring-index.json'; index=json.loads(p.read_text(encoding='utf-8'))
    index['questions'][0].update(authoring_status='not_selected',selection_reason='concept already covered')
    p.write_text(json.dumps(index),encoding='utf-8')
    assert check_bank_import(run,manifest)==[]
```

추가 테스트: snapshot 파일 bytes 변경, snapshot 자산 누락/해시 변경, 원자료 해시 변경, bank_question_id 탈락, ID/분류/소문항 답안 대상 변조, 새로운 practice 문항 허용, 배열 버전·알 수 없는 metadata key가 오류로 반환됨. Run `python -m pytest -n0 tests/test_review_pack_bank_provenance.py -q`. Expected: PASS.
- [ ] **Step 5: 커밋한다.** `git add scripts/lab/review_pack/bank_provenance.py tests/test_review_pack_bank_provenance.py`; `git commit -m "feat: validate imported bank provenance"`.

## Task 4: 답 노출 원문이 문제 화면에 들어가는 것 차단

**Files:** Create `bank_asset_checks.py`, `tests/test_review_pack_bank_assets.py`; Modify `checks.py:17-72`, `render.py:20-80`.

**Interfaces:**
- Consumes: 로컬 증거 검증을 통과한 manifest/snapshot, 기존 html2md.Parser.
- Produces: `check_bank_problem_assets(folder: Path, manifest: dict) -> list[str]`. root 없이 작동한다. 은행이 없는 legacy면 [].
- 이미지는 경로와 SHA256으로 은행 자산에 대응시킨다. 같은 bytes에 안전·비안전 선언이 함께 있으면 보수적으로 문제 사용을 거절한다.

- [ ] **Step 1: 합성 카드로 자산 재명명 우회 테스트를 작성한다.**

```python
import json, shutil
from scripts.lab.review_pack.bank_import import import_bank
from scripts.lab.review_pack.bank_asset_checks import check_bank_problem_assets
from tests._bank_import_fixture import create_bank, add_asset, save_bank

def asset_pack(tmp_path, exposure):
    path,bank=create_bank(tmp_path)
    role='problem' if exposure=='none' else 'mixed'
    add_asset(path,bank,'scan',role,exposure,b'original image '+exposure.encode())
    bank['occurrences'][0]['blocks'].append(dict(
        id='b-scan',type='figure',text='source image',tex=None,cells=None,asset_id='scan'))
    save_bank(path,bank)
    run=tmp_path/'run';import_bank(tmp_path,path,run)
    (run/'figures/renamed.png').write_bytes((run/'evidence/assets/scan.png').read_bytes())
    manifest=json.loads((run/'manifest.json').read_text(encoding='utf-8'))
    manifest['problems'][0].update(status='included')
    (run/'실험04_기출풀이.html').write_text(
        '<main><article class="card" id="q1"><div class="problem">'
        '<img src="figures/renamed.png"></div></article></main>',encoding='utf-8')
    return run,manifest

def test_answer_image_renamed_is_still_blocked(tmp_path):
    run,manifest=asset_pack(tmp_path,'present')
    assert check_bank_problem_assets(run,manifest)

def test_unknown_exposure_is_not_safe(tmp_path):
    run,manifest=asset_pack(tmp_path,'unknown')
    assert check_bank_problem_assets(run,manifest)
```

- [ ] **Step 2: RED를 확인한다.** `python -m pytest -n0 tests/test_review_pack_bank_assets.py -q`. Expected: bank_asset_checks import 부재.
- [ ] **Step 3: 카드의 문제 영역과 답안 증거 영역을 검사한다.**

```python
unsafe_hashes = {
    a['sha256'] for a in bank['assets']
    if a['role'] != 'problem' or a['answer_exposure'] != 'none'
}
# file이 어떤 이름으로 복사됐든 hash가 unsafe_hashes에 있으면 문제 영역에서 거절.
```

은행 imported included article에는 div.problem이 정확히 한 개 있어야 한다. img/src, source/src, SVG image href/xlink:href, object/data, embed/src, inline CSS url()의 로컬 파일을 찾는다. Parser에는 parent가 없으므로 재귀 순회 시 조상 tag/class를 전달한다. URL decode 후 폴더 내부 경로로 검사하고 symlink/junction 및 경로 탈출은 거절한다. remote/data URI는 문제 원문 자산으로 허용하지 않으며 기존 remote resource 검사와 함께 오류로 처리한다.

알려진 은행 자산은 role/exposure 판정을 따른다. 문제 영역 밖이라도 즉시 보이는 article 형제 이미지에는 같은 기준을 적용한다. 원문·답안 노출 자산은 details.original 또는 details.solution 안에서만 허용한다. details.hint는 정답 원문 표시를 허용하지 않는다. 포함 카드에 div.problem이 없거나 여러 개면 오류로 처리해 마크업 변경으로 검사 범위를 우회하지 못하게 한다.

새 교육용 그림은 은행 hash와 매칭되지 않으면 이 검사의 role 판정 대상이 아니지만 경로·외부 자원 검사는 적용한다. 의미상 답 노출 검토는 후속 내용 검토가 담당한다.

render는 bank 수입 행의 scalar provided/derived answer 안내를 문제 앞에 노출하지 않는다. 기존 legacy conflict 표시 방식은 유지하고 imported 문제에는 안내를 details.original에 두며 “원문과_저작안내.md” 링크를 제공한다. 노트·기출 HTML 목차의 템플릿 CSS·스크립트 파일은 수정하지 않는다.

- [ ] **Step 4: 허용 위치·우회 마크업과 기존 검사 연결을 검증한다.**

```python
def test_exposed_evidence_allowed_only_in_solution(tmp_path):
    run,manifest=asset_pack(tmp_path,'present')
    (run/'실험04_기출풀이.html').write_text(
        '<main><article class="card" id="q1"><div class="problem"><p>문제</p></div>'
        '<details class="solution"><summary>풀이</summary>'
        '<img src="figures/renamed.png"></details></article></main>',encoding='utf-8')
    assert check_bank_problem_assets(run,manifest)==[]

def test_safe_image_allowed(tmp_path):
    run,manifest=asset_pack(tmp_path,'none')
    assert check_bank_problem_assets(run,manifest)==[]
```

fixture는 원문 이미지를 question figure block에 연결하므로 authoring-index의 허용 목록과 대응한다. 이미지 percent-encoded 한글 경로, inline SVG image, inline CSS 배경, div.problem 누락, 안전/비안전의 동일 hash, unknown 이미지 outside problem을 각각 재현한다.

check_pack는 manifest 로딩 다음 check_bank_import를 호출하고, 증거 검증이 통과한 경우 bank asset 검사를 수행한다. 잘못된 증거에 대한 traceback 대신 finding을 반환한다. Run `python -m pytest -n0 tests/test_review_pack_bank_assets.py tests/test_review_pack_checks.py tests/test_review_pack_render.py -q`. Expected: PASS.
- [ ] **Step 5: 커밋한다.** Task 4 파일만 stage하고 `git commit -m "feat: keep exposed source answers out of questions"`.

## Task 5: build/check/publish에서 연결 계약 적용

**Files:** Modify `__main__.py:25-48`, `render.py:20-80`, `publish.py:12-40`; Create `tests/test_review_pack_bank_import_flow.py`.

**Interfaces:**
- Consumes: `copy_import_material(run,out,manifest)`, `check_bank_import(folder,manifest,root=None)`, 기존 main/assemble/check_pack/publish.
- Produces: 기존 build/check/publish CLI 계약 유지. bank_import 없는 호출은 기존 행동 그대로.
- build는 out 생성 전 current evidence 검사; render는 로컬 import 증거를 stage에 복사; publish는 filesystem 변경 전 current evidence 검사.

- [ ] **Step 1: 가짜 학습 fixture로 end-to-end 테스트를 작성한다. 실제 실험4 내용을 저작하지 않는다.**

```python
# tests/test_review_pack_bank_import_flow.py
import json
from pathlib import Path
from scripts.lab.review_pack.__main__ import main
from tests._bank_import_fixture import create_bank

def author_fixture(root, run):
    assets=Path('.claude/skills/logic-lab-review-pack/assets')
    import shutil
    target=root/'.claude/skills/logic-lab-review-pack/assets'
    target.parent.mkdir(parents=True);shutil.copytree(assets,target)
    p=run/'manifest.json';m=json.loads(p.read_text(encoding='utf-8'))
    m['topics']=[dict(id='t-example',title='개념 예',requires=[],
        sources=[],fragment='sections/t-example.html')]
    (run/'sections/t-example.html').write_text('<p>검증 fixture 개념입니다.</p>',encoding='utf-8')
    m['problems'][0].update(status='included',topics=['t-example'],
        reason='fixture authored',derived_answer='fixture answer',answer_status='unresolved',
        fragment='problems/q1.html')
    (run/'problems/q1.html').write_text(
        '<div class="problem"><p>입력이 0일 때 출력은?</p></div>'
        '<a href="{{NOTE_HREF}}#t-example">개념</a>'
        '<details class="hint"><summary>힌트</summary>fixture hint</details>'
        '<details class="solution"><summary>풀이</summary>fixture answer</details>',
        encoding='utf-8')
    p.write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8')
    return m

def test_cli_preserves_evidence_through_build_and_check(tmp_path):
    path,_=create_bank(tmp_path)
    run=tmp_path/'run'
    assert main(['import-bank','--root',str(tmp_path),'--bank',str(path),'--run',str(run)])==0
    author_fixture(tmp_path,run)
    stage=tmp_path/'stage'
    assert main(['build','--root',str(tmp_path),'--run',str(run),'--stage',str(stage)])==0
    assert (stage/'evidence/question-bank.json').read_bytes()==path.read_bytes()
    assert (stage/'authoring-index.json').is_file()
    assert main(['check','--folder',str(stage)])==0
    m=json.loads((stage/'manifest.json').read_text(encoding='utf-8'))
    assert 'evidence/question-bank.json' in m['generated_files']
    assert 'authoring-index.json' in m['generated_files']
```

- [ ] **Step 2: RED를 확인한다.** `python -m pytest -n0 tests/test_review_pack_bank_import_flow.py -q`. Expected: build가 증거를 복사하지 않거나 imported 안내 링크 누락으로 실패. import-bank의 parser 통과 여부는 Task 2에서 이미 검증되어 있어야 한다.
- [ ] **Step 3: 기존 흐름에 최소 호출을 연결한다.**

```python
# __main__.py, build에서 assemble 전에
errors = check_bank_import(args.run, data, root=args.root)
if errors:
    raise ValueError('\n'.join(errors))

# render.assemble, out을 만든 뒤 HTML 링크·안내·검증보다 먼저
copy_import_material(run, out, manifest)

# publish, destination 이동/복사 전에
errors = check_bank_import(stage, data, root=root)
if errors:
    raise ValueError('\n'.join(errors))
```

copy 작업은 한 곳(render)에만 둔다. build는 generated_files를 증거 복사·MD 변환·검증결과 복사 후 작성한다. pack의 안내 MD에는 raw 정답 증거의 확인 경로를 제공하고, 제공 답안 status와 학습팩 answer_status를 구분한다.

manifest 로더는 imported provenance가 포함될 때 중복 JSON 키를 거절하도록 기존 question_bank의 strict JSON object 로더 패턴을 재사용한다. 일반 manifest도 중복 키 손실을 방지하되 기존 정상 fixture는 바꾸지 않는다.

- [ ] **Step 4: 현재 입력 변경·발행 gate·legacy 회귀를 검사한다.**

```python
def test_changed_bank_blocks_build_without_creating_stage(tmp_path):
    path,_=create_bank(tmp_path);run=tmp_path/'run'
    assert main(['import-bank','--root',str(tmp_path),'--bank',str(path),'--run',str(run)])==0
    author_fixture(tmp_path,run)
    path.write_bytes(path.read_bytes()+b'\n')
    stage=tmp_path/'stage'
    assert main(['build','--root',str(tmp_path),'--run',str(run),'--stage',str(stage)])==1
    assert not stage.exists()
```

별도 test에서는 정상 build 후 은행·원자료·원래 자산을 각각 바꾸고 publish가 기존 destination/memo를 보존하는지 검사한다. unchanged origin에서는 기존 검증 gate가 not_run으로 발행을 거절한다. 테스트 fixture만 source_visual/content/browser를 수동 pass/self_review로 설정해 backup/사용자 memo/증거 파일 유지·rollback을 확인한다. 이 fixture 상태를 실제 은행 검증 기록으로 사용하지 않는다.

Run `python -m pytest -n0 tests/test_review_pack_bank_import_flow.py tests/test_review_pack_publish.py tests/test_review_pack_manifest.py tests/test_review_pack_md.py -q`. Expected: PASS.
- [ ] **Step 5: 커밋한다.** Task 5 수정 코드·테스트만 stage하고 `git commit -m "feat: preserve bank provenance through pack generation"`.

## Task 6: 스킬 연결·실제 은행 import 수용 검증

**Files:** Modify `.claude/skills/logic-lab-review-pack/SKILL.md`, `references/question-bank.md`, `references/format.md`, `references/verification.md`; Create `docs/verify/2026-09-30-question-bank-import.md`.

**Interfaces:** 기존 스킬의 자료·문항 저작 전에 완성 은행 존재 확인→import-bank. 이후 기존 설명·독립 풀이 저작 절차를 사용하며 추출을 다시 수행하지 않는다.

- [ ] **Step 1: 스킬과 references를 갱신한다.** 다음 명령과 의미를 문서에 넣는다.

```powershell
python -m scripts.lab.review_pack.question_bank_cli check --root . --bank 문제은행/실험04/question-bank.json
python -m scripts.lab.review_pack import-bank --root . --bank 문제은행/실험04/question-bank.json --run tmp/review-pack/실험04-import-20260930
```

새 bank가 이미 있으면 raw 퀴즈 재추출 대신 은행을 입력으로 사용한다. run manifest의 topics·fragment·독립 풀이를 저작하고 bank snapshot/index 고정 필드를 편집하지 않는다. 부분 판독 문제는 원래 은행에서 해결한 뒤 새 import를 한다. 예상문제 선별 이유는 index/manifest에 남긴다. question-bank.md의 “import 없음” 설명은 실제 제공 기능과 명령으로 교체한다. format/verification에 optional 계약·current input 대조·답 노출 이미지 규칙을 적는다.

- [ ] **Step 2: 실제 은행을 읽기 전용으로 검증하고 새 tmp run으로 import한다.** 위 명령을 실제로 실행하며 run이 이미 있으면 다른 고유 이름을 사용한다. 다음 수용 검사를 실행한다.

```python
from pathlib import Path
import hashlib,json
root=Path('.')
source=root/'문제은행/실험04/question-bank.json'
run=root/'tmp/review-pack/실험04-import-20260930'
before=source.read_bytes()
snapshot=run/'evidence/question-bank.json'
assert snapshot.read_bytes()==before
m=json.loads((run/'manifest.json').read_text(encoding='utf-8'))
bank=json.loads(snapshot.read_text(encoding='utf-8'))
index=json.loads((run/'authoring-index.json').read_text(encoding='utf-8'))
assert len(m['problems'])==15 and len(bank['occurrences'])==93
assert len(bank['assets'])==34 and len(bank['audit']['unresolved'])==20
assert sum(len(q['provided_answers']) for q in index['questions'])==38
assert all(p['status']=='held' and p['derived_answer'] is None for p in m['problems'])
assert set(m['checks'].values())=={'not_run'}
assert source.read_bytes()==before
print('Import acceptance passed; no learning pack authored or published')
```

source/asset bytes의 before/after 해시도 전체 11/34개 대조한다. 통계는 검증 기록에만 쓰며 코드에는 하드코딩하지 않는다. 실제 은행의 confirmed 30/candidate 8, 판독 보류 q-empty-six, 답 노출 자산의 안전 목록 제외를 확인한다. 실제 학습팩 HTML/MD·독립 풀이·browser pass를 만들지 않는다.

- [ ] **Step 3: 검증 기록을 작성한다.** 시작/종료 커밋, 실제 명령·종료 코드, 대상 run, 보존된 항목 수, 기존 실패, 검사 범위·미수행(실제 내용·브라우저·Task 8·통합)을 기록한다.
- [ ] **Step 4: 관련 회귀와 전체 저장소 검사를 수행한다.**

```powershell
$reviewPackTests = @(Get-ChildItem tests -Filter 'test_review_pack*.py' | ForEach-Object FullName)
python -m pytest -n0 @reviewPackTests -q
python -m pytest tests -q
git diff --check
```

전체 검사는 이전 알려진 실패가 있을 수 있으므로 실제 이름과 결과를 기록한다. 신규 변경과 연관된 실패는 수정하고 관련 검사를 다시 수행한다. 같은 오류를 반복해 보기 위해 전체 검사를 재실행하지 않는다. 단독 실행으로만 확인 가능한 경합은 해당 테스트 하나를 확인하고 전체 통과로 표현하지 않는다.

- [ ] **Step 5: Native 최종 독립 리뷰를 수행한다.** requesting-code-review/verification-before-completion을 사용한다. 리뷰어에게 spec/plan·이번 import 변경 범위·Review Focus·실제 수용 기록·ledger ruling만 전달하며 실험4의 답안 도출을 요청하지 않는다. Major/Critical은 재현 테스트 RED→GREEN 후 수정한다. 템플릿 bytes와 실제 은행·원문이 변경되지 않았는지 확인한다.
- [ ] **Step 6: 커밋하고 사용자에게 결과를 전달한다.** 스킬 문서와 수용 기록만 stage 후 `git commit -m "docs: document question bank import workflow"`. Native 리뷰 수정이 있으면 별도 fix commit. 최종 보고는 import 명령·검사 결과·남은 전체 실패·다음 저작 단계만 포함한다. 실제 학습팩 생성/Task 8/merge/push를 자동 시작하지 않는다.

## 계획 자체 검토

- 명세 대응: import/입력 보존 Task 2; index·manifest 계약 Task 1; snapshot/원본 변경·문항 연결 Task 3; 답 노출 Task 4; 기존 생성/검사/발행 Task 5; 문서·실제 은행·Native 리뷰 Task 6.
- Review Focus는 Task 1~5의 fixture와 실행 경로에 모두 대응한다.
- 모든 public 함수의 정의·소비 위치가 Interfaces에 연결되어 있다. CLI signature는 import-bank에 --root/--bank/--run만 추가한다.
- 구현 전 spec과 계획을 모두 읽고, 실행 중 필요한 수정은 ledger에 근거·영향을 남긴다.
- 계획 문서의 코드는 앞으로 작성·실행할 단계이며 현재 구현·통과 결과가 아니다.
