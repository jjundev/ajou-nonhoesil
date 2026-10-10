# 논회실 기출 풀이영상 스킬 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 전자회로2 `ec2-solution-video` 를 포크해 `복습노트/실험NN` 기출문제·기출풀이 PDF 로 문항별 한국어 풀이영상 MP4 를 만드는 `logic-lab-solution-video` 스킬을 만든다.

**Architecture:** 상류 엔진을 스킬 폴더로 통째로 복사하고(`upstream.json` 에 출처 기록), 형제 스킬 의존을 스킬 안으로 들여온 뒤, 소스 탐색·입력 게이트·그림 단위·논리식 자막·출력 이름 다섯 군데만 논회실용으로 바꾼다. 단계(prepare→extract→check→tts→assemble→render→captions→verify→publish-set)와 검증·게시 계약은 상류 그대로다.

**Tech Stack:** Python 3(.venv — PyMuPDF, Pillow), unittest, Node + puppeteer-core + Chrome, HyperFrames CLI, GSAP, libass FFmpeg, Vertex AI Express TTS.

**Spec:** `docs/superpowers/specs/2026-10-09-logic-lab-solution-video-design.md`

## Global Constraints

- 상류 기준: `../전자회로2` 커밋 `af86ffbc1004ca1e1f08c0c9125f3dc8272a8409`. 작업 트리가 아니라 이 커밋에서 `git archive`/`git show` 로 꺼낸다.
- 스킬 경로: `.claude/skills/logic-lab-solution-video/`, `.agents/skills/logic-lab-solution-video` 는 `../../.claude/skills/logic-lab-solution-video` 심볼릭 링크.
- 상류 구조와 파일 이름을 유지한다. 상류 파일을 바꾸거나 새 파일(테스트 포함)을 만들면 그 태스크 안에서 `upstream.json.local_changes` 에 이유 한 줄을 적는다 — 안 그러면 Task 1 의 `test_upstream_manifest_accounts_for_every_file` 가 깨진다.
- 매체 계약 불변: vertex-ai-express / gemini-2.5-flash-tts / Aoede / ko-KR / 1920×1080 / 30fps / mono PCM 24kHz. 공급자·모델 자동 대체 금지. 키는 환경변수 또는 `--env-file` 로만.
- 연필 7.5 chars/sec, 연필 길이 160px, 확대 기준 글자 26px — 상류 값 유지.
- 유료 TTS 는 `tts` 단계에서만. prepare/extract/check 는 `paid_requests: 0`.
- 환경변수 접두사 `LOGIC_LAB_` (`LOGIC_LAB_CHROME`, `LOGIC_LAB_FFMPEG`, `LOGIC_LAB_PUPPETEER_CORE_PACKAGE`).
- 출력 루트 `문제풀이영상/<실험NN>/`, 제작자료 `문제풀이영상/<실험NN>/<실험NN>_제작자료/실행/<YYYYMMDD-HHMMSS-8hex>/`, 최종 파일 `<라벨> — <제목>.mp4`.
- 복습노트·문제은행·보고서·전자회로2 의 파일을 수정하지 않는다.
- 테스트 실행: `.venv/bin/python -m unittest discover -s .claude/skills/logic-lab-solution-video/tests` (저장소 루트에서). 루트 pytest 는 점 폴더를 수집하지 않으므로 이 명령이 기준이다.
- 응답·문서·커밋 메시지는 한국어, 코드 식별자·경로만 원문.

## Review Focus

1. **팩을 다시 만들어 문항 순서가 바뀐 뒤 라벨로 고르기** — 라벨은 매번 현재 manifest 순서에서 계산해야 한다(Task 2 `test_labels_follow_current_manifest_order`).
2. **macOS NFD 이름의 폴더·파일** — `복습노트`·`실험05`·PDF 이름이 NFD 여도 찾아야 한다(Task 2 `test_nfd_folder_names`).
3. **픽셀이 같은 그림이 두 문항에 있을 때**(`q-demux-from-dec-solution-01` 과 `q-demux-from-dec-graded-solution-01` 실측 동일) — 그림 대조는 그 문항의 `<id>-solution-NN.png` 로만 한다(Task 2 `test_figure_refs_are_exact_per_problem`).
4. **한 실험의 모든 문항이 게이트에서 떨어질 때**(실험02) — prepare 는 비용 0 으로 끝나고 batch 에 전부 failed 가 남아야 한다(Task 6 `test_prepare_all_failed_experiment`).
5. **26px 로도 최소 배율로도 화면에 안 들어오는 그림** — 조용히 잘리지 말고 chunk ID 를 담은 InputError 여야 한다(Task 4 `test_oversized_figure_rejected`).

---

### Task 1: 상류 포크와 의존성 내재화

**Files:**
- Create: `.claude/skills/logic-lab-solution-video/**` (상류 `.agents/skills/ec2-solution-video/` @af86ffb 전체)
- Create: `.claude/skills/logic-lab-solution-video/scripts/tts_lib/{__init__,cache,budget,vertex_tts}.py` (상류 `.agents/skills/ec2-review-video/scripts/lib/` @af86ffb)
- Create: `.claude/skills/logic-lab-solution-video/assets/fonts/{Pretendard-Bold.ttf,SOURCE.md}` (상류 `ec2-review-video/assets/fonts/`)
- Create: `.claude/skills/logic-lab-solution-video/assets/runtime/{gsap.min.js,GSAP-README.md}` (상류 `ec2-review-video/assets/runtime/vendor/`)
- Create: `.claude/skills/logic-lab-solution-video/upstream.json`
- Create: `.agents/skills/logic-lab-solution-video` (심볼릭 링크)
- Modify: `scripts/solution_video/review_adapter.py`, `publication.py`, `annotations.py`, `state.py`, `util.py`, `media.py`, `scripts/video.py`, `agents/openai.yaml`, `SKILL.md`(frontmatter 만)
- Modify: 상류 테스트 중 gsap/폰트 경로를 쓰는 파일들
- Delete: `tests/test_sources.py`, `tests/acceptance.py`, `tests/test_acceptance.py`, `tests/teaching_acceptance.py`, `tests/test_teaching_acceptance.py`, `tests/guided_acceptance.py`, `tests/test_guided_acceptance.py`; `tests/test_cli.py` 의 `test_review_gate_and_zero_paid_prepare`, `test_export_failure_preserves_other_prepared_items` (전자회로2 `복습노트/1002` 데이터에 묶여 있다. Task 2·6·7 이 대체한다)
- Test: `.claude/skills/logic-lab-solution-video/tests/test_fork.py`

**Interfaces:**
- Produces: `review_adapter.adapter_files() -> list[Path]` 가 `S/'scripts/tts_lib'` 의 4개 파일을 돌려준다. 비공개 모듈 이름 `NAME='_logic_lab_tts_lib'`. `publication.publish_batch` 의 lock 은 `import_module('_logic_lab_tts_lib.cache').file_lock`.
- Produces: 폰트 경로 상수는 모두 `S/'assets/fonts/Pretendard-Bold.ttf'`, GSAP 는 `S/'assets/runtime/gsap.min.js'`.
- Produces: `upstream.json` = `{"source_repo": "../전자회로2", "source_commit": "af86ffbc1004ca1e1f08c0c9125f3dc8272a8409", "files": {"<스킬 상대경로>": {"upstream_path": "<전자회로2 상대경로>", "sha256": "<상류 바이트 sha256>"}}, "local_changes": {"<스킬 상대경로>": "<이유>"}, "removed": {"<상류 경로>": "<이유>"}}`.

- [ ] **Step 1: 실패하는 테스트 작성** — `tests/test_fork.py`

```python
from fixtures import *
import json,hashlib,re
class ForkTests(Sandbox):
    def test_no_sibling_skill_references(self):
        bad=re.compile(r'ec2-review-video|_ec2_review_video_lib|EC2_[A-Z]')
        hits=[str(p.relative_to(S)) for p in S.rglob('*') if p.is_file() and p.suffix in {'.py','.js','.mjs','.cjs','.json'}
              and '__pycache__' not in p.parts and p.name!='upstream.json' and bad.search(p.read_text(encoding='utf-8'))]
        self.assertEqual(hits,[])
    def test_upstream_manifest_accounts_for_every_file(self):
        u=json.loads((S/'upstream.json').read_text(encoding='utf-8'))
        self.assertEqual(u['source_commit'],'af86ffbc1004ca1e1f08c0c9125f3dc8272a8409')
        files={p.relative_to(S).as_posix() for p in S.rglob('*') if p.is_file() and '__pycache__' not in p.parts}-{'upstream.json'}
        self.assertEqual(files-set(u['files'])-set(u['local_changes']),set())
        for rel,meta in u['files'].items():
            if rel not in u['local_changes']:
                self.assertEqual(hashlib.sha256((S/rel).read_bytes()).hexdigest(),meta['sha256'],rel)
    def test_vendored_runtime_present(self):
        for rel in ['scripts/tts_lib/vertex_tts.py','assets/fonts/Pretendard-Bold.ttf','assets/runtime/gsap.min.js']:
            self.assertTrue((S/rel).is_file(),rel)
        self.assertTrue((REPO/'.agents/skills/logic-lab-solution-video').is_symlink())
```

`fixtures.py` 는 상류 것을 그대로 쓴다(`S`=스킬 폴더, `REPO=S.parents[2]`=논회실 루트).

- [ ] **Step 2: 실패 확인**

Run: `.venv/bin/python -m unittest discover -s .claude/skills/logic-lab-solution-video/tests -p test_fork.py -v`
Expected: 스킬 폴더가 없어 import/discovery 실패.

- [ ] **Step 3: 복사·내재화·경로 교체**

- `git -C ../전자회로2 archive af86ffbc1004ca1e1f08c0c9125f3dc8272a8409 .agents/skills/ec2-solution-video | tar -x --strip-components=3 -C .claude/skills/logic-lab-solution-video` 로 꺼낸다(작업 트리 복사 금지). 같은 방식으로 tts lib·폰트·GSAP 를 위 경로에 놓는다.
- `upstream.json.files` 는 복사 직후 바이트 sha256 으로 채운다. 이후 바꾼 파일은 `local_changes` 에 이유를 적는다. 지운 테스트는 `removed` 에 적는다.
- `util.py`/`media.py` 의 `EC2_` → `LOGIC_LAB_`, 오류 문구도 같이.
- `SKILL.md` frontmatter: `name: logic-lab-solution-video`, `description: 논리회로실험 복습팩의 기출문제·기출풀이 PDF 원본 화면을 사용하고 중앙 풀이를 한 글자씩 공개하는 한국어 문제풀이 영상을 만든다. 실험 번호·문항 ID·라벨·재개·대본 검토 요청 또는 /logic-lab-solution-video 에 사용한다. 복습팩 자체 생성은 logic-lab-review-pack 을 사용한다.` 본문은 Task 6 에서 다시 쓴다.
- `agents/openai.yaml`: display_name `논리회로실험 문제풀이 영상`, default_prompt 의 `$ec2-solution-video` → `$logic-lab-solution-video`.
- 심볼릭 링크: `ln -s ../../.claude/skills/logic-lab-solution-video .agents/skills/logic-lab-solution-video`.

- [ ] **Step 4: 전체 스위트 통과 확인**

Run: `.venv/bin/python -m unittest discover -s .claude/skills/logic-lab-solution-video/tests -v`
Expected: OK (브라우저 테스트는 `~/.npm/_npx/*/node_modules/puppeteer-core` 와 Chrome 을 쓴다. 못 찾으면 `LOGIC_LAB_PUPPETEER_CORE_PACKAGE` 를 지정해 다시 실행하고, 그래도 실패하면 멈추고 보고한다).

- [ ] **Step 5: 커밋**

```bash
git add .claude/skills/logic-lab-solution-video .agents/skills/logic-lab-solution-video
git commit -m "feat(solution-video): 전자회로2 풀이영상 엔진을 af86ffb 기준으로 포크하고 TTS·폰트·GSAP 를 내재화한다"
```

---

### Task 2: 실험 단위 소스 탐색

**Files:**
- Modify: `.claude/skills/logic-lab-solution-video/scripts/solution_video/sources.py` (전면 재작성. `validate_pairs`·`_conditions`·`_answer_hash`·`freeze_sources` 골격은 유지)
- Modify: `scripts/solution_video/contracts.py` (`PagePair` 필드 추가)
- Test: `tests/test_sources_lab.py`

**Interfaces:**
- Consumes: Task 1 의 스킬 골격.
- Produces:
  - `KINDS: dict[str,str] = {'past':'기출','predicted':'예상문제','unknown':'출처 미확인','practice':'연습문제'}`
  - `parse_selector(selector: str) -> list[str]` → `['실험03','실험04','실험05']` 형태. 받는 꼴: `실험05`, `05`, `5`, `03-05`, `실험03-05`. 범위 1–10, 역순·형식 오류는 `InputError('invalid experiment selector: '+selector)`.
  - `discover(repo: Path, selector: str, problem_ids: list[str]|None=None, failures: list|None=None) -> list[PagePair]`
  - `PagePair` 추가 필드: `label: str`(예 `'기출3'`), `title: str`, `experiments: list[str]`(상류 `dates` 대체), `figure_refs: list[str]`(절대경로, 정렬). `md_snapshot` 은 `복습노트/실험NN/실험NN_기출풀이.md`.
  - `freeze_sources(pairs, batch)` 는 `figure_refs` 도 동결해 batch 상대경로로 바꾼다.
  - 실패 사유 문자열: 팩 없음 `'experiment pack missing: 실험NN'`, PDF 쌍 `'missing or ambiguous PDF pair'`, 머리말 불일치 `'header/list mismatch: <id>'`, 선택 밖 `'problem IDs outside range: ...'`.

- [ ] **Step 1: 실패하는 테스트 작성** — `tests/test_sources_lab.py` (실데이터 `REPO/'복습노트/실험05'` 사용)

```python
from fixtures import *
import json,shutil,unicodedata
from solution_video.sources import discover,freeze_sources,parse_selector,KINDS
from solution_video.contracts import InputError
class LabSourceTests(Sandbox):
    def test_kinds_match_review_pack(self):
        sys.path.insert(0,str(REPO))
        from scripts.lab.review_pack.workbook_content import KINDS as PACK
        self.assertEqual(KINDS,PACK)
    def test_selector_forms(self):
        self.assertEqual(parse_selector('실험05'),['실험05']); self.assertEqual(parse_selector('5'),['실험05'])
        self.assertEqual(parse_selector('실험03-05'),['실험03','실험04','실험05'])
        for bad in ['실험00','실험11','05-03','abc','']:
            with self.assertRaises(InputError): parse_selector(bad)
    def test_experiment05_pairs_and_labels(self):
        pairs={p['problem_id']:p for p in discover(REPO,'실험05')}
        self.assertEqual(pairs['q-dec3x8']['label'],'예상문제1')
        self.assertEqual((pairs['q-dec3x8']['problem']['page_index'],pairs['q-dec3x8']['answer']['page_index']),(0,0))
        self.assertEqual(pairs['q-prio-exam']['label'],'기출3')
        self.assertTrue(pairs['q-prio-exam']['md_snapshot'].endswith('실험05_기출풀이.md'))
    def test_select_by_label_or_id(self):
        self.assertEqual([p['problem_id'] for p in discover(REPO,'실험05',['기출3'])],['q-prio-exam'])
        self.assertEqual([p['label'] for p in discover(REPO,'실험05',['q-dec2x4-design'])],['기출4'])
        with self.assertRaisesRegex(InputError,'outside range'): discover(REPO,'실험05',['기출99'])
    def test_figure_refs_are_exact_per_problem(self):
        p=discover(REPO,'실험05',['q-dec2x4-design'])[0]
        self.assertEqual([Path(f).name for f in p['figure_refs']],['q-dec2x4-design-solution-01.png'])
    def test_labels_follow_current_manifest_order(self):
        repo=self.run/'repo'; pack=repo/'복습노트/실험05'; shutil.copytree(REPO/'복습노트/실험05',pack)
        m=json.loads((pack/'manifest.json').read_text(encoding='utf-8')); inc=[p for p in m['problems'] if p['status']=='included']
        a,b=m['problems'].index(inc[0]),m['problems'].index(inc[1]); m['problems'][a],m['problems'][b]=m['problems'][b],m['problems'][a]
        (pack/'manifest.json').write_text(json.dumps(m,ensure_ascii=False),encoding='utf-8')
        failures=[]; discover(repo,'실험05',None,failures)
        self.assertIn('header/list mismatch',' '.join(f['reason'] for f in failures))
    def test_nfd_folder_names(self):
        repo=self.run/'repo'; root=repo/unicodedata.normalize('NFD','복습노트'); root.mkdir(parents=True)
        shutil.copytree(REPO/'복습노트/실험05',root/unicodedata.normalize('NFD','실험05'))
        self.assertEqual(len(discover(repo,'실험05')),len(discover(REPO,'실험05')))
    def test_missing_pack_and_freeze(self):
        failures=[]; discover(REPO,'실험09',None,failures)
        self.assertIn('experiment pack missing: 실험09',[f['reason'] for f in failures])
        frozen=freeze_sources(discover(REPO,'실험05',['q-dec2x4-design']),self.run)
        self.assertFalse(Path(frozen[0]['figure_refs'][0]).is_absolute())
        self.assertTrue((self.run/frozen[0]['figure_refs'][0]).is_file())
```

라벨 기대값은 2026-10-09 실측이다: 1 `q-dec3x8` 예상문제, 3 `q-prio-exam` 기출, 4 `q-dec2x4-design` 기출(쪽 인덱스 3), 11 `q-demux-from-dec` 출처 미확인, 12 `q-demux-from-dec-graded` 기출. 팩이 그 사이 다시 만들어졌으면 manifest 의 included 순서로 다시 확인하고 테스트 값을 실측에 맞춘다. `q-demux-from-dec-graded-solution-01.png` 는 `q-demux-from-dec-solution-01.png` 와 픽셀이 같다(Review Focus 3).

- [ ] **Step 2: 실패 확인**

Run: `.venv/bin/python -m unittest discover -s .claude/skills/logic-lab-solution-video/tests -p test_sources_lab.py -v`
Expected: `ImportError: cannot import name 'parse_selector'`.

- [ ] **Step 3: `sources.py` 재작성**

- 라벨: `KINDS[kind]+str(n)`, n 은 `status=='included'` 문항 중 1부터 센 순번.
- 쪽 짝짓기: 배지 = `page.get_text(clip=Rect(0,0,140,header_bottom))` 의 NFC 첫 줄, 이것이 라벨과 같고 머리말 전체(NFC)에 `title` 이 들어 있으면 그 문항 쪽이다. 같은 라벨 두 쪽이면 `'duplicate page for '+id`.
- PDF 이름: 팩 폴더의 `*_기출문제.pdf`·`*_기출풀이.pdf` 각각 정확히 하나(NFC 비교).
- `figure_refs`: `figures/solutions/` 에서 `re.fullmatch(re.escape(id)+r'-solution-\d{2}\.png', name)`.
- 상류의 날짜 범위 중복 제거(같은 ID 다른 답 → 충돌)는 `experiments` 로 이름만 바꿔 유지.

- [ ] **Step 4: 통과 확인**

Run: 위 명령 → `OK`. 이어서 전체 스위트도 OK.

- [ ] **Step 5: 커밋**

```bash
git add .claude/skills/logic-lab-solution-video
git commit -m "feat(solution-video): 복습노트/실험NN manifest 순서로 라벨을 만들고 문제지·풀이 쪽을 짝짓는다"
```

---

### Task 3: 입력 게이트

**Files:**
- Create: `.claude/skills/logic-lab-solution-video/scripts/solution_video/input_gate.py`
- Modify: `scripts/solution_video/sources.py` (짝짓기 직후 게이트 호출)
- Test: `tests/test_input_gate.py`

**Interfaces:**
- Consumes: Task 2 `discover`, `page_layout`.
- Produces: `input_defects(pdf: Path, page_index: int) -> list[dict]`. 각 원소 `{'code': 'raw_latex'|'clipped_figure', 'detail': str}`.
  - `raw_latex`: 쪽 텍스트에 `re.search(r'\$[^$\n]*\\[A-Za-z]|\$[A-Za-z]+_\{', text)`.
  - `clipped_figure`: `page.get_image_info()` 중 x0 ≥ 조건 패널 오른쪽 끝(패널 못 찾으면 286)인 이미지의 y1 이 '답' 블록 상단(텍스트 블록 첫 줄이 정확히 `답` 이고 x0 ≥ 패널 끝인 것들의 최소 y0)보다 0.5pt 넘게 아래. '답' 블록이 없으면 `page_layout(...)['body_bottom']` 와 비교.
- Produces: `discover` 는 문제·답안 두 쪽의 결함을 모아 `'input defect: '+';'.join(code+' p.'+str(page_index+1))` 로 그 문항만 실패 처리.

- [ ] **Step 1: 실패하는 테스트 작성**

```python
from fixtures import *
from solution_video.input_gate import input_defects
from solution_video.sources import discover
class InputGateTests(Sandbox):
    def pdf(self,text=None,image_bottom=None):
        import fitz,io; from PIL import Image
        d=fitz.open(); p=d.new_page(width=841.9,height=595)
        p.draw_rect((22,59,286,572),fill=(246/255,246/255,243/255),color=None)
        if text: p.insert_text((330,120),text)
        p.insert_text((330,500),'답')
        if image_bottom:
            buf=io.BytesIO(); Image.new('RGB',(40,40),'black').save(buf,'PNG'); p.insert_image((330,380,500,image_bottom),stream=buf.getvalue())
        out=self.run/'g.pdf'; d.save(out); return out
    def codes(self,pdf): return [d['code'] for d in input_defects(pdf,0)]
    def test_raw_latex(self):
        self.assertEqual(self.codes(self.pdf(text=r'$V_{CC}=5\,\mathrm{V}$')),['raw_latex'])
        self.assertEqual(self.codes(self.pdf(text='V_CC = 5 V, 가격 $5')),[])
    def test_clipped_figure(self):
        self.assertEqual(self.codes(self.pdf(image_bottom=540)),['clipped_figure'])
        self.assertEqual(self.codes(self.pdf(image_bottom=470)),[])
    def test_real_packs(self):
        failures=[]; ok=discover(REPO,'실험05',None,failures)
        bad={f['problem_id']:f['reason'] for f in failures}
        self.assertIn('clipped_figure',bad['q-demux-from-dec']); self.assertIn('q-prio-exam',[p['problem_id'] for p in ok])
        failures=[]; self.assertEqual(discover(REPO,'실험02',None,failures),[])
        self.assertTrue(all('raw_latex' in f['reason'] for f in failures))
```

`insert_text` 의 `'답'` 은 기본 글꼴에서 한글이 빠질 수 있다. 그러면 `fontname='korea'`(PyMuPDF CJK 내장)로 넣는다.

- [ ] **Step 2: 실패 확인** — `-p test_input_gate.py` → `ModuleNotFoundError: solution_video.input_gate`.
- [ ] **Step 3: `input_gate.py` 구현과 `discover` 연결.**
- [ ] **Step 4: 통과 확인** — `test_input_gate.py`, 이어서 전체 스위트 OK. `test_sources_lab.py` 의 `q-demux-from-dec` 관련 기대가 있으면 이 시점의 동작(실패 목록으로 이동)에 맞는지 확인.
- [ ] **Step 5: 커밋**

```bash
git add .claude/skills/logic-lab-solution-video
git commit -m "feat(solution-video): 원문 LaTeX·잘린 풀이 그림 쪽을 유료 호출 전에 문항 단위로 거른다"
```

---

### Task 4: 풀이 그림 단위 (연필 wipe)

**Files:**
- Modify: `scripts/solution_video/pdf_pages.py` (`export_page` 그림 승격, `ALLOWED` 에 `'figure'`)
- Modify: `scripts/solution_video/reveal.py` (figure 조각 draw 프레임)
- Modify: `scripts/solution_video/writing_camera.py` (figure 묶음 배율 대체)
- Modify: `scripts/video.py` (`export_page` 호출 2곳에 `figure_refs` 전달)
- Test: `tests/test_figure_unit.py`

**Interfaces:**
- Consumes: Task 2 `PagePair.figure_refs`(run 상대경로).
- Produces:
  - `figure_pixel_hash(data: bytes) -> str` — 이미지 바이트를 Pillow 로 열어 RGB 변환, `sha256(f'{w}x{h}'.encode()+rgb_bytes)`.
  - `export_page(pdf, page_index, dest, figure_refs: list[Path]|None=None)` — PDF 이미지(`page.get_image_info(xrefs=True)` + `doc.extract_image(xref)`)의 해시가 `figure_refs` 중 하나와 같고 SVG 인벤토리의 image 항목과 bbox 가 각 변 0.5pt 안에서 맞으면, 그 항목을 `shapes` 에 `dict(id=f's{i:05d}', bbox, svg_ids, kind='figure', paint_order=i, figure_source=<PNG 파일명>)` 로 넣는다. 아니면 상류대로 `images`.
  - `reveal.FIGURE_DRAW_FRAMES = 60` — 조각의 대상이 `kind=='figure'` 도형이면 draw 길이 60프레임. 나머지는 상류 값.
  - `writing_camera`: 묶음에 figure 조각이 있고 28/27/26 어느 것도 안 맞으면, 1900×880 에 들어가는 최대 scale 로 한 번 더 시도한다. 그래도 안 되면 상류 오류 `'writing chunk cannot fit at 26px; author smaller chunks: '+chunk_id`.
- 규칙(references 에 적는다, Task 6): figure 는 글자가 있는 step 에 둔다. 글자 없는 step 은 상류가 `'empty writing step'` 으로 거부한다.

- [ ] **Step 1: 실패하는 테스트 작성**

```python
from fixtures import *
from solution_video.pdf_pages import export_page,extract_layers,compare_completed,figure_pixel_hash
from solution_video.contracts import ExtractionError
PACK=REPO/'복습노트/실험05'
class FigureUnitTests(Sandbox):
    def page(self,refs):
        return export_page(PACK/'실험05_기출풀이.pdf',3,self.run/'layers',refs)  # 기출4 q-dec2x4-design (쪽 인덱스 3, 실측)
    def test_matching_image_becomes_figure_shape(self):
        p=self.page([PACK/'figures/solutions/q-dec2x4-design-solution-01.png'])
        figs=[s for s in p['shapes'] if s['kind']=='figure']
        self.assertEqual([f['figure_source'] for f in figs],['q-dec2x4-design-solution-01.png'])
    def test_unmatched_solution_image_still_stops(self):
        p=self.page([])
        self.assertFalse(any(s['kind']=='figure' for s in p['shapes']))
        from solution_video.pdf_pages import inside
        work=[300,59,760,560]  # 쪽 폭 841.9pt, Hint 단(x≈757) 왼쪽까지
        ids=lambda kind:[o['id'] for o in p[kind] if inside(o['bbox'],work)]
        with self.assertRaisesRegex(ExtractionError,'solution region contains image'):
            extract_layers(p,{'work_bbox':work,'steps':[{'id':'s','glyph_ids':ids('glyphs'),'shape_ids':ids('shapes')}],'answer_step_id':'s'})
    def test_gate_zero_with_figure_target(self): ...   # 실측 work_bbox 로 figure+glyph 를 모두 매핑해 compare_completed 의 pixel_diff/non_target_diff/hidden_leaks 가 모두 0
    def test_figure_draw_frames(self): ...             # writing_units 에 figure 조각 하나 + 제목 글자; build_timeline 의 그 조각 draw span 길이 == 60
    def test_figure_camera_fallback(self): ...         # base 글자 9pt, figure 300×237pt 묶음 → 키 생성 성공, viewbox 폭 ≥ figure 폭
    def test_oversized_figure_rejected(self): ...      # figure 1000×700pt → InputError, 메시지에 chunk_id 포함
    def test_pixel_hash_ignores_encoding(self):
        import io; from PIL import Image
        im=Image.new('RGB',(3,2),(1,2,3)); a=io.BytesIO(); b=io.BytesIO(); im.save(a,'PNG'); im.save(b,'PNG',compress_level=0)
        self.assertEqual(figure_pixel_hash(a.getvalue()),figure_pixel_hash(b.getvalue()))
```

`...` 로 적은 네 테스트는 상류 `test_writing_units.py`·`test_writing_camera.py`·`test_pdf_pages.py` 의 fixture 생성 방식을 그대로 따르고 주석에 적은 단언 하나씩을 가진다. `test_gate_zero_with_figure_target` 의 work_bbox·step 매핑은 `layers/native.png` 를 보고 정한다.

- [ ] **Step 2: 실패 확인** — `-p test_figure_unit.py` → `ImportError: figure_pixel_hash`.
- [ ] **Step 3: 구현** — 위 Interfaces 대로. `writing.js`·`player.js` 는 바꾸지 않는다(도형 clip 경로가 `<image>` 에도 그대로 적용된다). 바꿔야 한다면 멈추고 이유를 보고한다.
- [ ] **Step 4: 통과 확인** — `test_figure_unit.py`, 전체 스위트 OK.
- [ ] **Step 5: 커밋**

```bash
git add .claude/skills/logic-lab-solution-video
git commit -m "feat(solution-video): 문항 풀이 PNG 와 픽셀이 같은 그림을 figure 도형으로 올려 연필로 wipe 한다"
```

---

### Task 5: 논리식 음성·자막 규칙

**Files:**
- Modify: `assets/defaults.json` (`pronunciation`, `direction`)
- Modify: `scripts/solution_video/subtitles.py` (`_NOTATION_RULES` 에 한 항목)
- Modify: `references/narration-and-timing.md` (논리식 읽기 절)
- Test: `tests/test_caption_notation.py` (상류 파일에 테스트 추가)

**Interfaces:**
- Produces: `defaults.json.pronunciation = {"V_CC": "브이 씨씨", "V_IH": "브이 아이 에이치", "V_IL": "브이 아이 엘", "GND": "그라운드", "′": " 바"}`. `direction = "한국어로 차분하게 논리회로 실험 기출을 함께 푸는 느낌으로 읽으세요. 부울식은 신호 이름과 바를 또박또박 읽습니다. 과장하지 않습니다."` 나머지 키는 상류 값.
- Produces: 경고 규칙 `('warning','logic_bar_word', re.compile(r'(?<![A-Za-z0-9_])[A-Z][A-Za-z0-9_]*\s*(바|낫)(?![가-힣])'), '논리 부정은 자막에 ′ 로 씁니다 (예: S1′)')`.

- [ ] **Step 1: 실패하는 테스트 작성**

```python
    def test_logic_bar_word_warns(self):
        w=caption_notation_warnings([{'id':'a','caption_text':'Y0는 S1 바 S0 바 D예요.'}])
        self.assertEqual({i['code'] for i in w},{'logic_bar_word'})
    def test_logic_prime_and_korean_ba_are_quiet(self):
        for text in ['Y0=S1′S0′D예요.','이 바를 보면 출력이 정해져요.','A+B는 OR예요.']:
            self.assertEqual(caption_notation_warnings([{'id':'a','caption_text':text}]),[])
    def test_defaults_are_logic_lab(self):
        d=default_config(); self.assertEqual(d['pronunciation']['′'],' 바'); self.assertEqual(d['voice'],'Aoede')
        self.assertNotIn('g_m',d['pronunciation'])
```

(`default_config` 는 `solution_video.review_adapter` 에서 import.)

- [ ] **Step 2: 실패 확인** — `-p test_caption_notation.py`, 새 세 테스트 FAIL.
- [ ] **Step 3: 구현** — 규칙 추가·defaults 교체. references 에는 "자막=원문 기호(`S1′S0′D`, `+`, `V_CC`, `74HC138`), 음성=읽는 소리(‘에스원 바 에스제로 바 디’, ‘칠사 에이치씨 일삼팔’), OR 의 `+` 를 ‘더하기’로 읽지 않는다, 음성 원고는 복습팩 풀이와 같은 ~해요체" 를 상류 문체로 적는다.
- [ ] **Step 4: 통과 확인** — 전체 스위트 OK.
- [ ] **Step 5: 커밋**

```bash
git add .claude/skills/logic-lab-solution-video
git commit -m "feat(solution-video): 논리식 발음 사전과 바/낫 자막 경고를 넣는다"
```

---

### Task 6: CLI·출력 이름·문서·gitignore

**Files:**
- Modify: `scripts/video.py` (`prepare_batch`)
- Modify: `scripts/solution_video/publication.py` (`output_filename`)
- Modify: `SKILL.md` (본문 전체), `references/pdf-and-coverage.md`, `references/verification.md`
- Modify: `/.gitignore` (논회실 루트)
- Test: `tests/test_cli.py` (테스트 추가), `tests/test_publication.py` (테스트 추가)

**Interfaces:**
- Consumes: Task 2 `discover`/`parse_selector`, Task 4 `export_page(..., figure_refs)`.
- Produces:
  - `prepare_batch(repo, selector, problem_ids=None, review=False, writing_mode='pencil') -> Path` — 폴더 이름은 `parse_selector` 결과가 하나면 그 이름(`실험05`), 여럿이면 `실험03-05`. 루트 `repo/'문제풀이영상'/name`, 제작자료 `name+'_제작자료'`. batch item 에 `label` 추가, 기본 `filename = label+' — 풀이.mp4'`.
  - `output_filename(item, run)` 은 접두어로 `item.get('label') or item['id']` 를 쓴다.
  - `.gitignore` 추가 줄(Spec #11):
    ```
    # 풀이영상 제작자료 중 유료 호출 없이 다시 만들 수 있는 것
    문제풀이영상/**/실행/**/renders/
    문제풀이영상/**/실행/**/verification/
    문제풀이영상/**/실행/**/composition/
    문제풀이영상/**/실행/**/caption-original/
    ```

- [ ] **Step 1: 실패하는 테스트 작성**

```python
    def sandbox_repo(self):
        repo=self.run/'repo'; (repo/'복습노트').mkdir(parents=True)
        for n in ['실험02','실험05']: (repo/'복습노트'/n).symlink_to(REPO/'복습노트'/n)
        return repo
    def test_prepare_labels_and_paths(self):
        repo=self.sandbox_repo()
        self.assertEqual(cli.main(['prepare','실험05','--repo',str(repo),'--problems','기출3,q-demux-from-dec']),0)
        batch=next((repo/'문제풀이영상/실험05/실험05_제작자료/실행').iterdir())
        items={i['id']:i for i in read(batch/'batch.json')['items']}
        self.assertEqual(items['q-prio-exam']['label'],'기출3'); self.assertEqual(items['q-prio-exam']['status'],'author-required')
        self.assertEqual(items['q-demux-from-dec']['status'],'failed'); self.assertIn('clipped_figure',items['q-demux-from-dec']['reason'])
    def test_prepare_all_failed_experiment(self):
        repo=self.sandbox_repo(); out=io.StringIO()
        with contextlib.redirect_stdout(out): cli.main(['prepare','실험02','--repo',str(repo)])
        result=json.loads(out.getvalue()); self.assertEqual(result['paid_requests'],0)
        batch=Path(result['batch']); self.assertTrue(all(i['status']=='failed' for i in read(batch/'batch.json')['items']))
```

`test_publication.py` 에: label `기출3`, manifest title `8×3 우선순위 인코더 — 여러 비트가 켜진 입력` 인 item 의 `output_filename` 이 `'기출3 — 8×3 우선순위 인코더 — 여러 비트가 켜진 입력.mp4'`.

`.gitignore` 는 테스트 대신 Step 4 에서 `git check-ignore` 로 확인한다.

- [ ] **Step 2: 실패 확인** — 두 파일의 새 테스트 FAIL.
- [ ] **Step 3: 구현과 문서**
  - `prepare_batch` 가 `pair['figure_refs']` 를 run 으로 복사하고 `export_page(..., [run/r for r in pair['figure_refs']])` 로 넘긴다. `extract` 의 재시도 경로도 같게.
  - `SKILL.md` 본문: 상류 절 구조(호출과 기본값/실행/출력/회로 근거와 필기 음성 저작/자막 절)를 유지하고 날짜→실험, `/ec2-solution-video 1002` → `/logic-lab-solution-video 실험05`, `--problems E10.11,P10.62` → `--problems 기출3,q-dec2x4-design`, Razavi·전자회로 예시 → 논리회로 예시, 입력 게이트·그림 단위·라벨 이름 규칙을 넣는다. 명령은 `.venv/bin/python .claude/skills/logic-lab-solution-video/scripts/video.py ...`, `--runtime "$PWD/.claude/skills/logic-lab-solution-video/assets/runtime/gsap.min.js"`, `--hyperframes-entry` 는 `ls ~/.npm/_npx/*/node_modules/hyperframes/dist/cli.js` 로 찾은 절대경로.
  - `references/pdf-and-coverage.md`: "이미지 안에 풀이가 있으면 중단" 을 "그 문항의 `figures/solutions/<id>-solution-NN.png` 와 픽셀이 같은 그림은 `figure` 도형으로 쓰고, coverage 의 meaning_review 에 같은 이름 SVG 를 근거로 그림 의미를 적는다. 그 밖의 이미지는 중단" 으로, md_text 는 `실험NN_기출풀이.md` 의 같은 문항 절에서 가져온다고 바꾼다. figure 를 글자 있는 step 에 둔다는 규칙과, lesson 의 `circuit` 모드가 논회실에서는 문제 그림(회로도·진리표·파형) 근거 단계라는 뜻도 넣는다.
- [ ] **Step 4: 통과 확인**

Run: 전체 스위트 → OK.
Run: `git check-ignore -v '문제풀이영상/실험05/실험05_제작자료/실행/x/videos/k/renders/final.mp4' '문제풀이영상/실험05/기출3 — t.mp4'`
Expected: 첫 경로만 `.gitignore` 줄과 함께 출력, 둘째 경로는 출력 없음.

- [ ] **Step 5: 커밋**

```bash
git add .gitignore .claude/skills/logic-lab-solution-video
git commit -m "feat(solution-video): 실험 단위 prepare·라벨 파일 이름·스킬 문서를 논회실용으로 맞춘다"
```

---

### Task 7: 실험05 실측 (유료 TTS)

**Files:**
- Create: `문제풀이영상/실험05/**` (스킬 실행 산출물)
- Create: `.claude/skills/logic-lab-solution-video/tests/test_lab_acceptance.py`

**Interfaces:**
- Consumes: Task 1–6 의 CLI 전체.
- Produces: `문제풀이영상/실험05/기출3 — <제목>.mp4`, `문제풀이영상/실험05/기출4 — <제목>.mp4`(figure 문항), 각 run 의 `verification/report.json` `complete: true`, batch `catalog.json`.

- [ ] **Step 1: opt-in 실측 테스트 작성** — 상류 `test_acceptance.py` 형식. `LOGIC_LAB_ACCEPTANCE_BATCH` 가 없으면 skip. 있으면 `batch.json` 의 두 item 이 `q-prio-exam`·`q-dec2x4-design` 이고, 각 `report.json` 이 `complete` 이며 `live_audio=='verified'`, `catalog.json` 의 sha256 이 실제 MP4 와 같은지, q-dec2x4-design 의 `layers/layers.json` 에 `kind=='figure'` 도형이 하나 이상인지 단언한다.
- [ ] **Step 2: 사전 조건** — 사용자에게 Vertex 키가 든 `--env-file` 경로를 받는다(키 값은 출력·기록하지 않는다). 사용자 답을 기다린다.
- [ ] **Step 3: prepare** — `.venv/bin/python .claude/skills/logic-lab-solution-video/scripts/video.py prepare 실험05 --repo "$PWD" --problems 기출3,q-dec2x4-design` → 두 item `author-required`.
- [ ] **Step 4: 저작과 게이트** — 두 run 마다 `references/pdf-and-coverage.md` 대로 `source/map.json`(writing_units 포함, figure 는 '완성 회로' 제목 step 에), `extract`(gate 0/0/0), `manifest.json`·`coverage.json`·`circuit-review.json`·`lesson.json`(+필요 시 focus/annotations), `check` 통과.
- [ ] **Step 5: tts → assemble → render → captions → verify** — SKILL.md 실행 절 명령 그대로. `verify` 전에 최종 MP4 를 직접 보고(연필 wipe 구간 프레임 포함) audio/visual review 를 쓴다.
- [ ] **Step 6: publish-set** — `publish-set --batch <BATCH>` → `complete: true`. `LOGIC_LAB_ACCEPTANCE_BATCH=<BATCH> .venv/bin/python -m unittest discover -s .claude/skills/logic-lab-solution-video/tests -p test_lab_acceptance.py -v` → OK.
- [ ] **Step 7: 커밋** — `.gitignore` 가 중간물을 빼므로 폴더째 add 한다.

```bash
git add 문제풀이영상/실험05 .claude/skills/logic-lab-solution-video/tests/test_lab_acceptance.py
git commit -m "feat(실험05): 기출3·기출4 풀이영상을 만들고 실측 검증 테스트를 추가한다"
```

보고: 두 MP4 경로, 영상 길이, 유료 요청 수(`usage.json`), 직접 확인한 항목과 확인하지 못한 항목을 나눠서.
