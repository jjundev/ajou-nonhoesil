# 발화에 맞춘 회로 필기(주석 굵기·청크 타이밍) 이식 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 전자회로2 `eeec3d5` 의 주석 엔진 개선(도형별 `stroke_width_px`, 음성 청크에 묶는 `chunk_id`, 실측 청크 window 해석)을 `logic-lab-solution-video` 에 재구현하고 논리회로용 색 역할을 문서로 정한다.

**Architecture:** 이미 있는 주석 흐름(`annotations.py` 검증·컴파일 → `teaching.py` 타이밍 → `focus.py` 카메라 → `lesson.py` 검증점 → `teaching_check.mjs` 화면 오라클)을 그대로 두고 각 단계에 굵기와 청크 모드를 더한다. 청크 cue 는 main 에 이미 있는 `timeline['caption_cues']`(`speech_chunks.py:175` `caption_cues_for`, 필드 `segment_id/chunk_id/start_sample/end_sample`)를 읽는다. 청크 없는 항목(legacy)은 동작이 바이트까지 같아야 한다.

**Tech Stack:** Python 3(.venv, unittest), PyMuPDF(label 글리프), Node(`test_teaching_runtime.cjs`, `teaching_check.mjs` puppeteer), git worktree.

**Spec:** 이 문서의 「확정 결정」 절. 2026-10-11 대화(`/grill-yourself 이어서 진행해`)에서 확정. 상류 근거: `../전자회로2` 커밋 `eeec3d5`, 설계 `docs/superpowers/specs/2026-10-09-ec2-circuit-ink-design.md`, 코드 diff `git -C ../전자회로2 diff a017c9d eeec3d5 -- .agents/skills/ec2-solution-video`.

## 확정 결정

| # | 결정 | 값 |
|---|---|---|
| 1 | 범위 | 엔진 이식만. 기출3·기출12 재저작·재합성 없음(유료 호출 0) |
| 2 | `chunk_id` 전제 | manifest `caption_timing=='pcm-chunks-v1'` 이고 그 segment 의 `chunks[].id` 중 하나일 때만 |
| 3 | legacy | `chunk_id` 없는 항목은 오프셋 하한 12·기본 순차 배치·`minimum_segment_frames` 덧대기 그대로 |
| 4 | 시간 부족 | 무음을 늘리지 않고 `<id> segment <sid> chunk <cid>` 를 담은 InputError |
| 5 | 굵기 | 유한 숫자 2~12, 생략 3. label 은 금지(글자 크기로). 권장 보조 4·경로 6·강조 8 |
| 6 | 풀이 칸 | `work_bbox` 겹침 금지 유지(`annotations.py:31`). 중앙 풀이 그림 위 주석은 다음 라운드 |
| 7 | 재개 | `chunk_id` 변경 → timing 부터, 굵기·색 변경 → composition 부터(WAV 보존) |
| 8 | teaching 화면 검사 | 그 검사만 timeout 600초 |
| N1 | 색 역할 | 파랑 `#1565C0` 선택 조건(S1S0 값·선택된 행) / 주황 `#C45100` 데이터·켜진 입력(D 경로·가장 왼쪽 1) / 초록 `#237A43` 출력·결과(Yk·A2A1A0) / 자주 `#8E348E` 대조·흔한 실수 |
| N2 | 풀이 칸 그림 위 주석 | 이번엔 안 함 |
| N3 | 적용 | 엔진만, 적용은 다음 실험 영상부터 |

## Global Constraints

- 작업 위치: worktree `/Users/hyunjun_macbook_pro/Documents/Univ/논회실-annotation-ink`(브랜치 `feat/video-annotation-ink`, main `1fe4c3c` 에서 분기, `.venv` 는 main 의 심볼릭 링크). 원 트리와 `.claude/worktrees/*` 는 건드리지 않는다.
- 스킬 경로 접두 `S=.claude/skills/logic-lab-solution-video`. 아래 경로는 모두 `S/` 기준.
- 스킬 파일을 바꾸거나 만들면 **같은 커밋에서** `upstream.json` 의 `local_changes` 에 사유를 적는다(기존 항목이면 `; ` 로 덧붙임). 안 하면 `tests/test_fork.py::test_upstream_manifest_accounts_for_every_file` 가 깨진다. `source_commit` 은 af86ffb 그대로.
- 상류 테스트를 옮길 때 형제 스킬 경로(`ec2-review-video`, `S.parent/'ec2-review-video/...'`)는 쓰지 않는다 — `test_fork.py::test_no_sibling_skill_references`. GSAP 는 `S/'assets/runtime/gsap.min.js'`, 폰트는 `S/'assets/fonts/Pretendard-Bold.ttf'`.
- 테스트 명령(worktree 루트): `.venv/bin/python -m unittest discover -s .claude/skills/logic-lab-solution-video/tests` (기준선: 303 OK, skip 2). 단일 클래스는 `... -k <ClassName>` 대신 `cd S/tests && ../../../../.venv/bin/python -m unittest test_annotations.InkWidthTests -v`.
- 유료 호출·실제 run 재생성·게시·push 금지.
- 문서·커밋 메시지 한국어, 식별자·경로만 원문. 커밋 스타일 `feat(solution-video): …`, 끝에 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. 한 manifest 에서 segment A 는 청크 항목, segment B 는 legacy 항목 — 허용되어야 한다(섞임 금지는 같은 segment 안만). → Task 1 테스트.
2. 논리식 label(`S1′S0′`, 결합 오버바 `Y̅`)이 MuPDF 글리프 별칭 때문에 거부되거나 저작 글자가 바뀌면 안 된다. Pretendard 에 없는 `⊕`(2026-10-11 확인: `has_glyph`=0)는 조용히 빠지지 않고 `unsupported font glyph` 로 막혀야 한다. → Task 2 테스트.
3. 청크 항목의 `hide_at` 이 같은 segment 를 가리키며 완성보다 이르면 window 단계에서 막혀야 한다(검증 단계에서는 청크 모드라 통과). → Task 3 테스트.
4. 기존 run(teaching 사이드카 없음)·legacy 계획의 timeline·span 이 이전과 바이트까지 같아야 한다. → Task 3 테스트.
5. 굵기 12 화살표가 region 가장자리에 있을 때 카메라가 연필 여백 + 선 반경을 확보해야 한다. → Task 4 테스트.

---

### Task 1: 주석 계약 — 굵기와 청크 모드 검증

**Files:**
- Modify: `scripts/solution_video/annotations.py` (`_validate`, 67-115행 부근)
- Modify: `upstream.json`
- Test: `tests/test_annotations.py` (클래스 추가)

**Interfaces:**
- Produces: `validate_teaching(...)` 의 정규화된 항목에 `stroke_width_px: int|float`(비-label 만, 기본 3), `chunk_id: str`(지정했을 때만), 청크 항목의 `offset_frames` 기본 0. 상류 `eeec3d5` 의 `annotations.py` `_validate` 와 같은 규칙.

- [x] **Step 1: 실패하는 테스트 작성** — `tests/test_annotations.py` 끝에 상류 `git -C ../전자회로2 show eeec3d5:.agents/skills/ec2-solution-video/tests/test_annotations.py` 의 `InkWidthTests.test_stroke_width_contract`, `InkWidthTests.test_label_rejects_stroke_width`, `ChunkAnnotationTests`(fixture 포함)를 옮긴다. 핵심 단언:
  - 기본 `make_teaching_plan()['items'][0]['stroke_width_px']==3`; `[2,4,6,8,12,4.5]` 통과; `[1.9,12.1,True,'6',nan,inf]` InputError.
  - label 에 `stroke_width_px=6` → InputError.
  - 청크 fixture(`caption_timing='pcm-chunks-v1'`, segment `r` 의 chunks `c1,c2`, `intro` 의 chunk `other`)에서 `c1`·`c2` 두 항목 오프셋 `[0,0]`; 변형 7가지(`missing`, 다른 segment 의 `other`, 모드 키 제거, `offset_frames=-1`, `True`, 같은 청크 겹침 `offset_frames=25`, 같은 segment 에 legacy 항목 혼합) 모두 InputError.
  - 추가(Review Focus 1) `test_chunk_and_legacy_in_different_segments`: 청크 fixture 의 manifest 에 reason segment `r2`(`chunks=[dict(id='k1')]`)를 `w` 앞에 넣고 focus cue `dict(segment_id='r2',target='circuit')` 를 더한다. `r` 에는 `chunk_id='c1'` 항목, `r2` 에는 `chunk_id` 없는 항목(`id='b'`, `segment_id='r2'`) → 통과하고 `b` 의 `offset_frames==12`.
- [x] **Step 2: 실패 확인** — `cd .claude/skills/logic-lab-solution-video/tests && ../../../../.venv/bin/python -m unittest test_annotations -v` → 새 테스트 FAIL(`stroke_width_px` KeyError/AssertionError).
- [x] **Step 3: 구현** — `_validate` 에 `modes={}` 를 두고 항목마다 `chunk_mode='chunk_id' in i`, `offset_key=(sid,chunk) if chunk_mode else sid`, `minimum=0 if chunk_mode else 12` 로 오프셋 검사를 한다. 같은 segment 안 hide 비교는 청크 모드에서 건너뛴다(Task 3 가 맡음). 굵기 검사 `type(width) in (int,float) and math.isfinite(width) and 2<=width<=12`(bool 은 `type` 으로 걸러짐). 오류 문구: `unknown chunk for segment <sid>`, `mixed segment/chunk timing for <sid>`, `stroke_width_px must be finite number in 2..12`, `label uses font size, not stroke_width_px`.
- [x] **Step 4: 통과 확인** — 같은 명령 → 전부 PASS. 이어 전체 테스트 → 기준선 대비 새 실패 없음.
- [x] **Step 5: `upstream.json`** — `scripts/solution_video/annotations.py`, `tests/test_annotations.py` 사유에 "stroke_width_px 2..12·label 금지; pcm-chunks-v1 의 chunk_id(청크 시작 기준 오프셋, 같은 segment 혼합 금지)" 덧붙임.
- [x] **Step 6: 커밋** — `feat(solution-video): 주석에 선 굵기와 음성 청크 지정을 받는다`

### Task 2: 굵기를 그림에 반영 — SVG·런타임·논리식 label 글리프

**Files:**
- Modify: `scripts/solution_video/annotations.py` (`compile_annotations` 의 path `stroke-width`, label 글리프 대조)
- Modify: `assets/annotations.js:31` (화면 굵기)
- Modify: `upstream.json`
- Test: `tests/test_annotations.py`, `tests/test_teaching_runtime.cjs`

**Interfaces:**
- Consumes: Task 1 의 `stroke_width_px`.
- Produces: `compiled.json` 항목에 `stroke_width_px` 가 실리고(비-label), `annotations.svg` path 의 `stroke-width` 가 그 값. 런타임 화면 굵기 = `(item.stroke_width_px??3)/scale`.

- [x] **Step 1: 실패하는 테스트** — 상류 `InkWidthTests.test_compiled_stroke_and_color`(굵기 6·색 `#C45100` → path `stroke-width==6`, `stroke=='#C45100'`, compiled 항목 6)를 옮긴다. 상류 `MathLabelAliasTests` 대신 논리식 판 `LogicLabelGlyphTests.test_logic_label_keeps_authored_unicode`: runs `[dict(text="S1′S0′",origin=[40,60],font_size_pt=12)]` 컴파일 → `[g['text'] for g in glyphs]==['S','1','′','S','0','′']`, `annotations.svg` 에 `data-text="′"` 포함. 별도 케이스 `test_xor_symbol_rejected`: `"A⊕B"` label 은 `validate_teaching` 에서 InputError(`unsupported font glyph`). `tests/test_teaching_runtime.cjs` 에 상류 `renderer preserves mixed screen widths across camera scales and backward seeks` 테스트(굵기 6·4·8·생략 3, 뷰 3개 왕복)를 옮긴다.
- [x] **Step 2: 실패 확인** — `../../../../.venv/bin/python -m unittest test_annotations -v` 와 `node --test test_teaching_runtime.cjs` → 새 테스트 FAIL.
- [x] **Step 3: 구현** — path 속성 `'stroke-width':str(i['stroke_width_px'])`. label 대조에서 `e['text']!=u['text']` 이면 `len(e['text'])==1 and font.has_glyph(ord(u['text'])) and font.has_glyph(ord(e['text']))==font.has_glyph(ord(u['text']))` 일 때만 허용하고 `n.set('data-text',u['text'])` 로 저작 글자를 남긴다(상류와 같음). `annotations.js` 는 `3` 상수를 `(entry.item.stroke_width_px??3)` 로.
- [x] **Step 4: 통과 확인** — 두 명령 PASS, 전체 테스트 새 실패 없음.
- [x] **Step 5: `upstream.json`** — `assets/annotations.js`, `tests/test_teaching_runtime.cjs` 와 annotations.py 사유 갱신.
- [x] **Step 6: 커밋** — `feat(solution-video): 주석 굵기를 SVG 와 화면에 반영하고 논리식 label 글자를 보존한다`

### Task 3: 청크 window 타이밍

**Files:**
- Modify: `scripts/solution_video/teaching.py`
- Modify: `upstream.json`
- Test: `tests/test_teaching.py`, `tests/test_state.py`

**Interfaces:**
- Consumes: Task 1 항목(`chunk_id`, `offset_frames`), timeline 의 `caption_cues`.
- Produces: `resolve_annotation_windows(plan:dict, timeline:dict) -> list[dict]` — 항목마다 `{id,start_frame,end_frame,hide_frame}`. `teaching_timing_settings` 항목에 `chunk_id` 추가. `build_teaching_timeline` 이 이 window 로 span 을 만들고 `start_frame` 순으로 정렬.

- [x] **Step 1: 실패하는 테스트** — 상류 `eeec3d5` `tests/test_teaching.py` 의 `ChunkWindowTests`(fixture·`test_chunk_absolute_windows`·`test_overlap_deadline_hide_and_long_label`·`test_chunk_marks_do_not_extend_segment_and_projection`)를 숫자 그대로 옮긴다(예: window `[(112,138),(138,164)]`, 단독 두 번째 항목 시작 131, 겹침 오류 정규식 `'b.*r.*c2'`, 마감 초과 `'a.*r.*c1'`, `minimum_segment_frames(p)=={'r':54}`, `chunk_id` 변경은 설정 해시를 바꾸고 굵기·색은 안 바꿈). Review Focus 3: 같은 클래스 `test_same_segment_early_hide`: 청크 항목 `hide_at=dict(segment_id='r',offset_frames=20)` → `resolve_annotation_windows` InputError(정규식 `'a'`). Review Focus 4: `test_legacy_plan_spans_unchanged` — `make_teaching_plan()` 의 `build_teaching_timeline` span 이 기존 `test_short_voice_appends_silence` 의 `[('move',13,21),('draw',21,39)]` 와 같음을 다시 단언(정렬 추가 뒤에도). `tests/test_state.py` 에 상류 `test_chunk_and_style_invalidation`(chunk 변경 → `recover_run=='timing'`, 굵기·색 변경 → `'composition'`, voice 지문·WAV 해시 불변)을 옮긴다.
- [x] **Step 2: 실패 확인** — `../../../../.venv/bin/python -m unittest test_teaching test_state -v` → 새 테스트 FAIL(`chunk resolver missing`).
- [x] **Step 3: 구현** — 청크 항목: `start=max(ceil(cue.start_sample/800)+offset, seg.start_sample//800+12)`, `deadline=min(cue.end_sample//800, seg.end_sample//800-13)`. legacy: `start=seg.start_sample//800+offset`, `deadline=` 마지막 segment 끝 프레임. `end=start+annotation_duration(i)`; `end>deadline` → `annotation completes at <end>, beyond speech/camera deadline <deadline>`; hide 규칙은 기존 `build_teaching_timeline` 의 것을 옮김; 시작 순 정렬 뒤 인접 겹침 → `annotation windows overlap`. 모든 오류 이름은 `f'{id} segment {sid} chunk {chunk}'`. `minimum_segment_frames` 는 `'chunk_id' in i` 항목을 건너뜀. `build_teaching_timeline` 은 window 의 `start_frame/hide_frame` 으로 기존 move/draw span 을 만들고 마지막에 `spans.sort(key=lambda s:s['start_frame'])`.
- [x] **Step 4: 통과 확인** — 같은 명령 PASS, 전체 테스트 새 실패 없음(특히 `test_teaching`·`test_focus`·`test_composition` 의 legacy 숫자).
- [x] **Step 5: `upstream.json`** — `scripts/solution_video/teaching.py`, `tests/test_teaching.py`, `tests/test_state.py` 사유 갱신.
- [x] **Step 6: 커밋** — `feat(solution-video): 청크 주석을 실측 청크 발화 안에서 그리고 무음을 덧대지 않는다`

### Task 4: 카메라 여백·청크 검증점·화면 오라클

**Files:**
- Modify: `scripts/solution_video/focus.py` (`compile_focus_keys` 여백)
- Modify: `scripts/solution_video/lesson.py` (`lesson_expectations` 끝)
- Modify: `tests/teaching_check.mjs` (bounds·굵기 오라클, 회귀 수평 밑줄)
- Modify: `upstream.json`
- Test: `tests/test_focus.py`, `tests/test_lesson.py`, `tests/test_lesson_runtime.py`

**Interfaces:**
- Consumes: Task 2 의 compiled `stroke_width_px`, Task 3 의 window·`caption_cues`.
- Produces: `lesson_expectations(...)['probes']` 에 `chunk_id` 가 있는 검증점 `{step_id,segment_id,chunk_id,frame,region_bbox,annotation_ids}` 추가.

- [x] **Step 1: 실패하는 테스트** — 상류 `eeec3d5` 에서 옮긴다: `test_focus.py` 의 `test_thick_arrow_screen_bounds`(굵기 12, bbox `[5,30,190,90]`, 화면 여백 180/200/30 에 반경 6 을 더해 단언), `test_lesson.py` 의 `test_chunk_evidence_probes`(`[('c1',138,['a']),('c2',174,['b'])]`, 청크 cue 를 지운 뒤 `'c1'` InputError — 상류 파일에서 fixture 의 `caption_cues` 구성까지 그대로), `test_lesson_runtime.py` 의 `test_horizontal_underline_counts_as_painted_lesson_evidence`(굵기 8 수평 밑줄이 `lesson_flow` true). 이 마지막 테스트의 `assemble` GSAP 인자는 `S/'assets/runtime/gsap.min.js'` 로 바꾼다.
- [x] **Step 2: 실패 확인** — `../../../../.venv/bin/python -m unittest test_focus test_lesson test_lesson_runtime -v` → 새 테스트 FAIL.
- [x] **Step 3: 구현** — `focus.py`: `radius=max(stroke_width_px/2 for 보이는 비-label 항목, default=0)` 를 `margin_x/top/bottom` 에 더해 scale·view 계산. `lesson.py`: 상류 9줄 블록(청크별 마지막 draw 끝을 검증점으로, `probe<=chunk.end_sample//800`, `probe<cue.end_frame-12`, hide 이전). `teaching_check.mjs`: lesson probe 가시성 검사에 stroke 반경을 포함하고(수평선은 기하 높이 0), 포커스 구간에서 각 주석 bbox±반경이 1920×900 안인지와 화면 굵기가 `stroke_width_px??3` 와 1e-3 안에서 같은지 `bounds_ok` 에 넣고 실패 시 `bounds_debug` 를 남긴다(상류 diff 그대로).
- [x] **Step 4: 통과 확인** — 같은 명령 PASS, 전체 테스트 새 실패 없음.
- [x] **Step 5: `upstream.json`** — `focus.py`, `lesson.py`, `tests/teaching_check.mjs`, 세 테스트 파일 사유 갱신.
- [x] **Step 6: 커밋** — `feat(solution-video): 굵은 주석의 반경을 카메라 여백에 넣고 청크마다 완성 화면을 검증한다`

### Task 5: teaching 화면 검사 예산과 문서

**Files:**
- Modify: `scripts/solution_video/verify.py` (`teaching_browser` 추가, teaching 게이트 호출부)
- Modify: `SKILL.md`, `references/narration-and-timing.md`, `references/verification.md`
- Modify: `upstream.json`
- Test: `tests/test_verify.py`

**Interfaces:**
- Produces: `teaching_browser(args:list[str]) -> dict` — `node tests/browser_check.mjs *args *browser_config()` 를 timeout 600 으로 실행해 JSON 을 돌려준다. 다른 `browser()` 호출의 timeout 은 그대로.

- [x] **Step 1: 실패하는 테스트** — 상류 `DenseTeachingScreenTests.test_dense_teaching_screen_has_budget_for_complete_frame_oracles` 를 옮긴다(`subprocess.run` patch, timeout<300 이면 TimeoutExpired → `teaching_browser(['--mode','teaching'])=={'bounds_ok':True,'seek_equal':True}`).
- [x] **Step 2: 실패 확인** — `../../../../.venv/bin/python -m unittest test_verify.DenseTeachingScreenTests -v` → FAIL(`dense teaching runner missing`).
- [x] **Step 3: 구현** — `verify.py` 에 `teaching_browser` 를 두고 teaching 게이트의 `browser([... '--mode','teaching' ...])` 를 이것으로 바꾼다. import 는 `S, browser_config, checked` — 셋 다 `scripts/solution_video/util.py`(5·17·33행)에 있다.
- [x] **Step 4: 문서** — `references/narration-and-timing.md` 와 `references/verification.md` 의 청크 동기화 절 뒤, `SKILL.md` 의 focus/annotations 문단(38행 부근) 뒤에 「발화에 맞춘 회로 필기」 절을 쓴다. 담을 것: 같은 타원 반복으로 근거를 대신하지 않음; `stroke_width_px` 2~12(생략 3), 권장 보조 4·경로 6·강조 8, label 은 `font_size_pt`; 색 역할 N1 표(파랑 선택 조건·주황 데이터/켜진 입력·초록 출력/결과·자주 대조/흔한 실수, 색과 함께 위치·기호로도 구분); `chunk_id` 는 pcm-chunks-v1 에서만, 오프셋은 청크 시작 기준, 같은 segment 혼합 금지, 넘치면 표시를 간소화하고 무음을 늘리지 않음; 0/1 값 label 은 선 옆에 쓰고 선을 덮지 않음; label 폰트(Pretendard)에 `⊕` 가 없으니 XOR 은 글자로 쓴다; 교차점 점 없는 선을 연결처럼 잇지 않음; 원본 신호 이름 그대로; 주석은 `work_bbox` 밖(왼쪽 패널)만 — 중앙 풀이 그림 위는 아직 불가; 기술 검사가 청취를 대신하지 않음. verification.md 에는 teaching 검사 600초와 `bounds_debug` 를 적는다.
- [x] **Step 5: 전체 확인** — 전체 테스트 PASS(기준선 303 + 새 테스트), `git diff --check main` 깨끗.
- [x] **Step 6: `upstream.json`** — `verify.py`, `tests/test_verify.py`, `SKILL.md`, 두 references 사유 갱신.
- [x] **Step 7: 커밋** — `docs(solution-video): 논리회로 주석 색 역할과 청크 필기 규칙을 적고 teaching 검사에 600초를 준다`

## 완료 후

- main 병합·push 는 하지 않는다. 브랜치·커밋 목록·테스트 결과를 보고한다.
