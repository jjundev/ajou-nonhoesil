# verify-write-result-report Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 실험01 결과보고서 승인본(v5)을 통제군으로, ④ `write-result-report` 와 ⑤ `review-lab-report` 를 답안 없는 격리 트리에서 다시 실행시키고 재생성물을 자동 대조해 규칙·검사가 없는 자리를 찾는 스킬 `verify-write-result-report` 를 만들고 첫 회차를 돌린다.

**Architecture:** `verify-draft-lab-spec` 과 같은 골격의 형제 스킬이다. `scripts/lab/isolate.py` 를 일반화해(비울 폴더·되살릴 파일·글롭 키) 결과보고서 입력물(기록·명세·결선도·사진 시트·예비보고서)은 남기고 답안(결과보고서 md·baseline·리뷰·계획·피드백 로그)만 뺀다. 새 모듈 `scripts/lab/report_compare.py` 가 재생성물과 승인본을 6갈래(구조·표 셀·참고문헌·문체·사실 토큰·산문)로 대조하고 판정 초안을 낸다. 스킬은 아무것도 고치지 않는다 — 갈린 자리마다 ⑦ 분류 표 형식으로 제안만 하고 사용자 승인 뒤 재실행한다. 선행 작업으로 v5 되읽기에서 나온 규칙(조사·단위 붙여쓰기)을 ③④ 에 넣고 `validate.check_body_style` 을 warn 으로 신설한다.

**Tech Stack:** Python 3.11 표준 라이브러리만(`scripts/lab/*` 관례 — `requests`·PyYAML 없음), `git archive`, unittest 스타일 테스트를 `pytest` 로 실행. **이 PC 에서 `python3` 는 Microsoft Store 스텁이라 실행되지 않는다 — 항상 Git Bash 에서 `PYTHONPATH=. python` 으로 돌린다.** 스킬 문서 안의 `python3 -c` 는 관례상 그대로 두되 실행할 때 `python` 으로 바꾼다. `pdftoppm`·`pdftotext`·`pdfinfo` 는 `C:\Users\Hyunjun\AppData\Local\Microsoft\WinGet\Packages\oschwartz10612.Poppler_Microsoft.Winget.Source_8wekyb3d8bbwe\poppler-25.07.0\Library\bin\` 에 있다.

**Spec:** 이 대화의 `/grill-yourself` 설계(2026-09-12, 결정 #0~#17 전부 추천값으로 확정). 요약은 아래 §설계 요약.

## Global Constraints

- 격리 트리는 `git archive HEAD` 로 푼다(`scripts/lab/isolate.py:37`) — **커밋 안 한 변경은 재지지 않는다.** Task 1 이 먼저다.
- 스킬 문서는 `tests/test_skill_docs.py` 의 불변식을 지킨다: `## 절대 규칙`·`## 실행 절차` 안 항목 번호는 연속, 헤딩은 `#`·`##` 두 단계, 다른 문서의 단계는 `④ §실행 절차 12` 형식으로만 가리킨다(`④ 12단계` 라고 쓰면 자기 문서의 12단계를 찾다 실패한다), `§3` 같은 맨 번호 참조 금지, 본문에 `Task` 라는 단어를 쓰지 않는다.
- 새 검사·새 규칙은 **테스트부터** 쓴다(⑤ 비-목표). 검사 규칙은 `validate.py` 에, 대조 규칙은 `report_compare.py` 에 두고 스킬 문서는 부르기만 한다.
- 스킬 `verify-write-result-report` 는 **④·⑤·승인본·규칙 어느 것도 고치지 않고 커밋하지 않는다.** 에이전트 프롬프트에 "합격"·"채점" 이라는 말과 이력 명령(`git log`·`show`·`diff`)을 넣지 않는다.
- 노션 페이지를 만들거나 지우지 않는다. 이 계획은 노션 API 를 호출하지 않는다.
- 커밋 메시지 끝에 `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` 를 붙인다.
- `.vscode/` 는 이 작업과 무관하다 — 스테이지하지 않는다.

---

## 설계 요약 (spec)

**통제군.** `보고서/실험01/output/실험01_결과보고서.md` 가 노션 v5 와 동기화된 상태다(2026-09-12 확인: `1-1부터` 3회, `330Ω` 2회, `뒷단이 NAND라` 1회, 백틱 0). `실험01_결과보고서_notion_baseline_v5.md` 는 대조 도구의 자기대조(HTML 표 파서 검증)용이다.

**v5 되읽기 분류(사용자 확정).** ⑴ 숫자·영문·기호 뒤 조사와 숫자 뒤 단위를 붙여 쓴다(`1-1 부터`→`1-1부터`, `L1 이`→`L1이`, `330 Ω`→`330Ω`, `5 V`→`5V`) — 체계적, ④ §절대 규칙 18 신설 + ③ §절대 규칙 21 거울, `validate.check_body_style` warn. ⑵ 추가 공부의 2-1 벡터 문장을 뒷단이 NAND 임을 반영해 다시 따짐 — 체계적, ④ §섹션별 재료 추가 공부 행에 한 문장.

**격리.** `build_isolated_tree(root, dest, experiment, answer_keys, clear_subdirs=("output",), keep=[<예비보고서 md>])`. 남기는 것: `체크리스트/{명세,기록}.md`, `결선도/`, `실험사진/`(시트 포함), `실험중있었던일.md`, `강의노트/`, `.claude/{데이터시트_출처,과목정보,보고서양식}.md`, ④·⑤·`export-photo-sheet` 스킬. 구조적 누출: ④ SKILL.md 자체가 실험01 사례(핀 1 고착-1·2-1 의 011)를 규칙 예시로 싣는다 — 판정에 적고 그 자리 일치는 합격 근거로 세지 않는다.

**대조 6갈래.** `structure`(헤딩 수열·표 수·행 수·그림 자리·여백 블록), `cell`(표 셀), `references`(참고문헌 항목), `style`(`check_body_style`), `fact`(문장의 사실 토큰: 수치+단위·IC·벡터 집합·`A=B=1`·`핀 N`·`고착-N`·`(미확인)`), `wording`(절별 문장 일치율 — 보고만, 세지 않음). 합격: 앞 다섯이 0 이고 `fact` 는 사람이 `규칙 없음/검사 없음/환경` 으로 가른 뒤 앞 둘이 0.

**에이전트.** ④ 절차대로 쓰고 ⑤ 로 error 0 까지 검토. 사용자에게 묻는 자리는 묻지도 지어내지도 말고 비운 채 보고 5항에 적는다. `기록.md` 의 사용자 확인 문장은 확인된 것으로 본다. 네트워크는 `.claude/데이터시트_출처.md` 의 URL 만. 환경 줄(파이썬 명령·poppler 경로)은 컨트롤러가 실행 시 채운다.

**루프.** 세션당 최대 3회. `규칙 없음`·`검사 없음` 으로 분류된 차이가 남을 때만 사용자 승인 → 규칙 반영 커밋 → 재실행. `wording` 만 다른 것은 재실행 사유가 아니다.

---

### Task 1: 미커밋 변경(v5 동기화·규칙 반영)을 커밋한다

**Files:**
- Modify(스테이지만): `.claude/skills/verify-draft-lab-spec/SKILL.md`, `.claude/skills/write-pre-report/SKILL.md`, `.claude/skills/write-result-report/SKILL.md`, `scripts/lab/validate.py`, `보고서/실험01/output/notion.json`, `보고서/실험01/output/실험01_결과보고서.md`, `보고서/실험01/output/실험1 Basic Gates 결과보고서 표지.pdf`, `보고서/실험01/체크리스트/기록.md`
- Add(스테이지만): `docs/plans/2026-09-12-실험01-결과보고서-v4.md`, `docs/plans/2026-09-12-verify-write-result-report.md`, `보고서/실험01/output/실험01_결과보고서_notion_baseline_v4.md`, `보고서/실험01/output/실험01_결과보고서_notion_baseline_v5.md`, `보고서/실험01/실험1_Basic_Gates_결과보고서.pdf`

**Interfaces:**
- Consumes: 없음
- Produces: HEAD 에 승인본·baseline v5·④ 규칙 8/7단계 보강이 들어 있다. 이후 모든 Task 의 테스트가 `output/실험01_결과보고서_notion_baseline_v5.md` 를 읽는다.

- [ ] **Step 1: 원본 md 가 v5 와 동기화돼 있는지 센다**

Run:
```bash
F="보고서/실험01/output/실험01_결과보고서.md"
echo "$(grep -c '1-1부터' "$F") $(grep -c '330Ω' "$F") $(grep -c '뒷단이 NAND라' "$F") $(grep -c '`' "$F")"
```
Expected: `3 2 1 0`. 다르면 멈추고 사용자에게 보고한다 — 통제군이 v5 가 아니다.

- [ ] **Step 2: 기존 테스트가 통과하는 상태인지 본다**

Run:
```bash
PYTHONPATH=. python -m pytest tests -q -x 2>&1 | tail -3
```
Expected: 마지막 줄이 `… passed` 이고 `failed` 가 없다. 실패하면 어느 테스트인지 그대로 사용자에게 보고하고 멈춘다(이 Task 는 코드를 바꾸지 않으므로 기존 실패다).

- [ ] **Step 3: 대상만 스테이지한다**

Run:
```bash
git add ".claude/skills/verify-draft-lab-spec/SKILL.md" \
        ".claude/skills/write-pre-report/SKILL.md" \
        ".claude/skills/write-result-report/SKILL.md" \
        scripts/lab/validate.py \
        "보고서/실험01/output/notion.json" \
        "보고서/실험01/output/실험01_결과보고서.md" \
        "보고서/실험01/output/실험01_결과보고서_notion_baseline_v4.md" \
        "보고서/실험01/output/실험01_결과보고서_notion_baseline_v5.md" \
        "보고서/실험01/output/실험1 Basic Gates 결과보고서 표지.pdf" \
        "보고서/실험01/체크리스트/기록.md" \
        "보고서/실험01/실험1_Basic_Gates_결과보고서.pdf" \
        "docs/plans/2026-09-12-실험01-결과보고서-v4.md" \
        "docs/plans/2026-09-12-verify-write-result-report.md"
git status --short | grep -v "^??"
```
Expected: 위 13개만 `A`/`M` 로 나오고 `.vscode/` 는 `??` 로 남는다.

- [ ] **Step 4: 커밋한다**

Run:
```bash
git commit -m "$(cat <<'EOF'
fix(실험01): 결과보고서 v4·v5 동기화 — 칩 불량 논증·LED 전류 정정·조사/단위 붙여쓰기 및 ③④ 규칙 반영

- 결과 분석: 핀 1 고착-1 은 2-1 의 011 에서 드러났어야 함 → 모델 밖 불량으로 논증
- 본문 백틱·결론 장식문·em dash 제거, LED 전류 (5.0−1.9)/330 ≈ 9.4mA
- v5: 숫자·영문 뒤 조사와 단위 붙여쓰기, 2-1 벡터 문장을 NAND 뒷단 기준으로 정정
- ④ 절대 규칙 8·7단계, ③ 절대 규칙 11, validate docstring 갱신
- 제출 PDF·baseline v4/v5·계획 문서 추가

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
EOF
)"
git log --oneline -1
```
Expected: 새 커밋 해시 한 줄.

---

### Task 2: round2 피드백 로그와 붙여쓰기 규칙(④ 18·③ 21)을 넣는다

**Files:**
- Create: `docs/notion-feedback/round2-실험01-결과보고서.md`
- Modify: `.claude/skills/write-result-report/SKILL.md` (§절대 규칙 17 끝, §섹션별 재료 "추가 공부" 행)
- Modify: `.claude/skills/write-pre-report/SKILL.md` (§절대 규칙 20 끝)
- Test: `tests/test_skill_docs.py` (`SkillDocInvariants` 에 메서드 추가)

**Interfaces:**
- Consumes: 없음
- Produces: ④ §절대 규칙 18 과 ③ §절대 규칙 21 이 존재한다(Task 3 의 검사 docstring 과 Task 7 의 스킬 문서가 `④ §절대 규칙 18` 로 가리킨다).

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_skill_docs.py` 의 `class SkillDocInvariants` 안, `test_rule_5b_cites_a_result_report_sample` 메서드 바로 앞에 추가:

```python
    def test_particle_spacing_rule_lives_in_both_report_skills(self):
        # 2026-09-12 실험01 결보 v5 되읽기: 사용자가 본문 전체에서 `L1 이`→`L1이`,
        # `330 Ω`→`330Ω` 로 고쳤다. 표기 규약이라 ③④ 둘 다 규칙으로 갖는다.
        for name in REPORT_DOCS:
            with self.subTest(name):
                self.assertIn("조사와 숫자 뒤 단위는 붙여 쓴다", self.flat[name])
```

- [ ] **Step 2: 실패를 확인한다**

Run: `PYTHONPATH=. python -m pytest tests/test_skill_docs.py -q -k particle_spacing`
Expected: FAIL (AssertionError, 두 subTest 모두).

- [ ] **Step 3: ④ 에 절대 규칙 18 을 붙인다**

`.claude/skills/write-result-report/SKILL.md` 에서 찾을 문장:
```
    2개 — 인버터가 한 칩에 6개라 두 단 모두 한 칩으로 잡힌다.

## 실행 절차
```
바꿀 문장:
```
    2개 — 인버터가 한 칩에 6개라 두 단 모두 한 칩으로 잡힌다.
18. **숫자·영문·기호 뒤 조사와 숫자 뒤 단위는 붙여 쓴다.** `L1이 A·B`, `A=B=1에서만`,
    `330Ω`, `5V`, `9.4mA`, `(미확인)은` 으로 쓴다 — `L1 이`, `330 Ω` 처럼 띄우지
    않는다. 2026-09-12 실험01 결보 v5 되읽기에서 사용자가 본문 전체를 이 규약으로
    고쳤다(`docs/notion-feedback/round2-실험01-결과보고서.md`). 한글 낱말 사이의
    띄어쓰기는 그대로다 — 이 규칙은 라틴 문자·숫자·닫는 괄호 바로 뒤에만 해당한다.
    ⑤ 의 `validate.check_body_style` 이 warn 으로 잡는다.

## 실행 절차
```

- [ ] **Step 4: ④ §섹션별 재료의 추가 공부 행에 한 문장을 더한다**

찾을 문장(같은 파일, 표 행 안 — 한 줄이다):
```
인용한 문헌은 이 절 안이 아니라 맨 뒤 "출처 및 참고문헌" 절로 보낸다(§절대 규칙 10) |
```
바꿀 문장:
```
인용한 문헌은 이 절 안이 아니라 맨 뒤 "출처 및 참고문헌" 절로 보낸다(§절대 규칙 10). **앞 항목에서 세운 계산을 회로 구조가 다른 항목에 그대로 옮기지 않는다** — 실험01 v5 에서 3입력 AND 의 고착 검출표를 뒷단이 NAND 인 2-1 에 그대로 적용한 문장을 사용자가 "뒷단이 NAND 라 위 계산을 그대로 쓸 수는 없지만 같은 방법으로 따지면" 으로 고쳤다. 항목마다 그 항목의 게이트로 다시 따진다 |
```

- [ ] **Step 5: ③ 에 절대 규칙 21 을 붙인다**

`.claude/skills/write-pre-report/SKILL.md` 에서 찾을 문장:
```
    끼운다. 빈 채로 나가면 ⑦ 의 `check_pulled_images` 가 error 로 잡는다.

## 실행 절차
```
바꿀 문장:
```
    끼운다. 빈 채로 나가면 ⑦ 의 `check_pulled_images` 가 error 로 잡는다.
21. **숫자·영문·기호 뒤 조사와 숫자 뒤 단위는 붙여 쓴다.** `74HC08의`, `L1이`,
    `330Ω`, `5V` 로 쓴다 — `74HC08 의`, `330 Ω` 처럼 띄우지 않는다. ④ §절대 규칙
    18 과 같은 규칙이다(2026-09-12 실험01 결보 v5 되읽기). 이미 올린 예비보고서는
    소급하지 않는다. `validate.check_body_style` 이 warn 으로 잡는다.

## 실행 절차
```

- [ ] **Step 6: 피드백 로그 round2 를 쓴다**

`docs/notion-feedback/round2-실험01-결과보고서.md` 를 아래 내용 그대로 만든다.

```markdown
# 라운드 2 · 실험01 결과보고서

- 올린 것: `보고서/실험01/output/실험01_결과보고서.md`
- 노션 v3: https://app.notion.com/p/1-Basic-Gates-v3-3d8b06d263bc81fd9552eea4da7c4b19 (사용자 미편집)
- 노션 v4: https://app.notion.com/p/1-Basic-Gates-v4-3d8b06d263bc815fa6d6dd3f033953a5 (평가 수정본, 사용자가 노션에서 편집)
- 노션 v5: https://app.notion.com/p/1-Basic-Gates-v5-3d9b06d263bc81ffaa13f3b3c282127c (최종 승인본)
- baseline: `실험01_결과보고서_notion_baseline_v4.md`, `실험01_결과보고서_notion_baseline_v5.md`
- 되읽음: v4 편집분은 baseline v4 ↔ baseline v5 diff 로 잰다 (2026-09-12)

## 특이사항 — 두 종류의 수정

v3 는 사용자가 노션에서 손대지 않았다. 대신 "모순·대학생 수준·AI 흔적" 세 관점의 평가를
요청했고 그 결과를 `/grill-yourself` 설계(`docs/plans/2026-09-12-실험01-결과보고서-v4.md`)로
확정해 원본 md 에서 고쳐 v4 로 올렸다(1~7번). 사용자는 v4 를 노션에서 다시 고쳤고, 그
편집분이 v5 로 올라가 최종 승인됐다(8~9번).

## 분류

| # | 무엇이 바뀌었나 | 분류 | 반영 대상 | 반영함? |
|---|---|---|---|---|
| 1 | 같은 원인 서사가 네 절에 거의 같은 문장으로 반복 → 결과 분석 한 곳에만 상세, 나머지는 가리키기 | 체계적 | ④ §절대 규칙 8 | 예 |
| 2 | 본문 수식·신호 이름의 백틱 코드 서식 제거 | 체계적 | ④ §절대 규칙 8, ③ §절대 규칙 11, `validate.check_heading_backticks` docstring | 예 |
| 3 | 인과 주장을 결선표(어느 게이트·어느 핀)와 앞 실험 결과까지 대조해 논증 | 체계적 | ④ §실행 절차 7 "메모의 인과 주장" 문단 | 예 |
| 4 | LED 전류를 실제 전원 5V 로 계산(예비보고서 9mA 와 일치) | 일회성 | 이번 md | 예 |
| 5 | 절 끝 장식 결론문·em dash·"첫째/둘째" 제거 | 일회성(④ 규칙 8 의 판별 기준으로 이미 덮임) | 이번 md | 예 |
| 6 | 추가 공부 두 소절 축소 제안 | 반영 안 함 | — | 아니오 — 라운드1 #2 에서 사용자가 "3학년 수준, 매주" 로 정했다 |
| 7 | 참고문헌 형식 간소화 제안 | 반영 안 함 | — | 아니오 — `check_report_references` 가 개정·발행일·URL 을 요구한다 |
| 8 | 본문 전체에서 숫자·영문·기호 뒤 조사와 숫자 뒤 단위를 붙여 씀(`1-1 부터`→`1-1부터`, `L1 이`→`L1이`, `330 Ω`→`330Ω`, `5 V`→`5V`, 헤딩 `A=B=1 에서만`→`A=B=1에서만`) | 체계적 | ④ §절대 규칙 18, ③ §절대 규칙 21, `validate.check_body_style`(warn), ④ §실행 절차 12·⑤ §실행 절차 4 호출 | 예 |
| 9 | 추가 공부의 2-1 벡터 문장을 "뒷단이 NAND 라 위 계산을 그대로 쓸 수는 없지만 같은 방법으로 따지면, A 고착-1 은 011 에서 잡는 대신 B 고착-1 과 C 고착-0 을 못 잡고, 네 행 모두 최종 출력이 1 이어야 하는 행이라 Y 고착-1 도 잡지 못한다" 로 정정 | 체계적 | ④ §섹션별 재료 "추가 공부" 행 | 예 |

## 재생성 대조

이번 라운드부터 결과보고서용 격리 재생성 도구가 있다 — `verify-write-result-report`
(`docs/verify/write-result-report.md`). 8·9번을 반영한 판본으로 실험01 을 재생성해 승인본과
대조한 결과는 그 런북의 기록 표에 남긴다.

## 남은 것

- `check_body_style` 은 warn 이다. 다음 실험에서 같은 수정이 또 나오면 error 로 올린다.
```

- [ ] **Step 7: 테스트가 통과하는지, 상호참조가 깨지지 않았는지 본다**

Run: `PYTHONPATH=. python -m pytest tests/test_skill_docs.py -q`
Expected: 전부 PASS (번호 연속성·상호참조 테스트 포함).

- [ ] **Step 8: 커밋한다**

```bash
git add tests/test_skill_docs.py \
        ".claude/skills/write-result-report/SKILL.md" \
        ".claude/skills/write-pre-report/SKILL.md" \
        "docs/notion-feedback/round2-실험01-결과보고서.md"
git commit -m "$(cat <<'EOF'
feat(skills): 실험01 결보 v5 되읽기 반영 — 조사·단위 붙여쓰기 규칙(④18·③21)과 round2 피드백 로그

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: `validate.check_body_style` 을 만들고 ④⑤ 가 부르게 한다

**Files:**
- Modify: `scripts/lab/validate.py` (`check_heading_backticks` 바로 뒤에 함수 추가, 그 docstring 마지막 문단 수정)
- Modify: `.claude/skills/write-result-report/SKILL.md` (§실행 절차 12 코드 블록)
- Modify: `.claude/skills/review-lab-report/SKILL.md` (§실행 절차 4 코드 블록)
- Test: `tests/test_lab_validate.py`, `tests/test_skill_docs.py`

**Interfaces:**
- Consumes: 없음
- Produces: `validate.check_body_style(md_text: str) -> list[Finding]` — level 은 전부 `"warn"`, `where` 는 `"본문 문체"`, 갈래마다 Finding 하나(백틱·em dash·첫째/둘째·조사 띄어쓰기·단위 띄어쓰기), 참고문헌 절과 표 줄·펜스 코드 블록은 보지 않는다. Task 5 의 `report_compare` 가 `style` 갈래로 그대로 쓴다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_lab_validate.py` 맨 끝에 추가:

```python
class BodyStyle(unittest.TestCase):
    """2026-09-12 실험01 결보 v5 회차에서 승격한 본문 문체 검사.

    v3 평가에서 백틱·em dash·"첫째" 가, v5 되읽기에서 조사·단위 띄어쓰기가
    사용자 손으로 지워졌다. 전부 기계로 셀 수 있는 것이라 warn 으로 잡는다.
    """

    CANON = ROOT / config.experiment_dir(1) / "output/실험01_결과보고서.md"

    def _msgs(self, text):
        return [f.message for f in validate.check_body_style(text)]

    def test_승인본은_0건이다(self):
        # 이 검사의 폭은 승인본 v5 로 맞춘다 — 승인본에서 하나라도 잡히면 정규식이
        # 넓은 것이지 승인본이 틀린 것이 아니다.
        got = validate.check_body_style(self.CANON.read_text(encoding="utf-8"))
        self.assertEqual(got, [], [str(f) for f in got])

    def test_조사_띄어쓰기를_잡는다(self):
        msgs = self._msgs("# 실험 결과\n앞단 출력 L1 이 A·B 다.\n")
        self.assertEqual(len(msgs), 1, msgs)
        self.assertIn("조사", msgs[0])

    def test_붙여_쓴_조사는_잡지_않는다(self):
        self.assertEqual(self._msgs("# 실험 결과\n앞단 출력 L1이 A·B다. C 하나만 1이어도 켜진다.\n"), [])

    def test_단위_띄어쓰기를_잡는다(self):
        msgs = self._msgs("# 결과 분석\n전류는 (5.0 − 1.9) / 330 ≈ 9.4 mA 다.\n")
        self.assertEqual(len(msgs), 1, msgs)   # `9.4 mA` 하나. `330 ≈` 는 조사가 아니다
        self.assertIn("단위", msgs[0])

    def test_백틱과_em_dash와_첫째를_잡는다(self):
        msgs = self._msgs("# 고찰\n`L1` 이 켜졌다 — 첫째, 배선이 맞았다.\n")
        self.assertTrue(any("백틱" in m for m in msgs), msgs)
        self.assertTrue(any("em dash" in m for m in msgs), msgs)
        self.assertTrue(any("첫째" in m for m in msgs), msgs)

    def test_참고문헌_절과_표_줄은_보지_않는다(self):
        text = ("# 실험 결과\n\t| A | L1 |\n\t|---|---|\n\t| 1 | 1 |\n"
                "# 출처 및 참고문헌\n- Nexperia, 74HC_HCT08 — Rev. 9 — 2021-12-13, 5 V 조건\n")
        self.assertEqual(self._msgs(text), [])

    def test_각_갈래는_한_건으로_요약하고_첫_줄을_적는다(self):
        msgs = self._msgs("# 고찰\nL1 이 켜졌다.\nL2 가 꺼졌다.\n")
        self.assertEqual(len(msgs), 1, msgs)
        self.assertIn("2곳", msgs[0])
        self.assertIn("2행", msgs[0])
```

- [ ] **Step 2: 실패를 확인한다**

Run: `PYTHONPATH=. python -m pytest tests/test_lab_validate.py -q -k BodyStyle`
Expected: FAIL — `AttributeError: module 'scripts.lab.validate' has no attribute 'check_body_style'`.

- [ ] **Step 3: 검사를 구현한다**

`scripts/lab/validate.py` 의 `check_heading_backticks` 함수 바로 다음(주석 `# A4 한 장에 들어가는 표의 최대 열 수.` 앞)에 추가:

```python
# 본문 문체. 전부 2026-09-12 실험01 결보에서 사용자가 손으로 지운 것들이다 —
# v3 평가에서 백틱·em dash·"첫째", v5 되읽기에서 조사·단위 띄어쓰기.
# 라틴 문자·숫자·닫는 괄호·작은따옴표(보수 `'`) 바로 뒤에 공백 하나 + 조사 + 경계.
_STYLE_PARTICLE = re.compile(
    r"[A-Za-z0-9)\]'}] (은|는|이|가|을|를|의|와|과|로|으로|에|에서|도|만|부터|까지|뿐)"
    r"(?=[\s,.)]|$)")
_STYLE_UNIT = re.compile(r"\d (?:V|mA|μA|µA|Ω|kΩ|ns/V|ns|°C)(?![A-Za-z])")
_STYLE_FENCE = re.compile(r"^\s*```")


def check_body_style(md_text) -> list:
    """본문 문체 다섯 갈래를 warn 으로 잡는다. 갈래마다 Finding 하나.

    참고문헌 절(`#` 헤딩에 `참고문헌`)과 표 줄, 펜스 코드 블록은 보지 않는다 —
    서지에는 `Rev. 9 — 2021` 같은 em dash 와 영문·숫자가 정상이고, 표 셀은
    `check_notion_markdown` 의 몫이다. ③ §절대 규칙 21·④ §절대 규칙 18(붙여쓰기),
    ④ §절대 규칙 8(백틱·em dash·첫째) 의 기계 검사판이다. 폭은 실험01 결보
    v5 승인본에서 0건이 나오도록 맞췄다(`tests/test_lab_validate.py::BodyStyle`).
    """
    hits = {"백틱": [], "em dash": [], "첫째": [], "조사": [], "단위": []}
    in_refs, in_fence = False, False
    for n, line in enumerate(md_text.splitlines(), 1):
        if _STYLE_FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if line.startswith("#"):
            in_refs = "참고문헌" in line
        if in_refs or line.lstrip().startswith("|"):
            continue
        if "`" in line:
            hits["백틱"].append(n)
        if "—" in line:
            hits["em dash"].append(n)
        if "첫째" in line:
            hits["첫째"].append(n)
        if _STYLE_PARTICLE.search(line):
            hits["조사"].append(n)
        if _STYLE_UNIT.search(line):
            hits["단위"].append(n)
    why = {
        "백틱": "본문 백틱 코드 서식 — 노션에서 붉은 고정폭 배경으로 렌더된다 (④ §절대 규칙 8)",
        "em dash": "본문 em dash — 학생이 손으로 쓰지 않는 문장 부호다 (④ §절대 규칙 8)",
        "첫째": "\"첫째 … 둘째 …\" 열거 — 산문 두 문단으로 푼다 (④ §절대 규칙 8)",
        "조사": "숫자·영문 뒤 조사를 띄어 썼다 — `L1이`, `A=B=1에서` 처럼 붙인다 (④ §절대 규칙 18)",
        "단위": "숫자와 단위를 띄어 썼다 — `330Ω`, `9.4mA` 처럼 붙인다 (④ §절대 규칙 18)",
    }
    return [Finding("warn", "본문 문체", f"{why[k]}: {len(v)}곳 (첫 자리 {v[0]}행)")
            for k, v in hits.items() if v]
```

그리고 `check_heading_backticks` docstring 의 마지막 문단을 바꾼다. 찾을 문장:
```
    2026-09-12 부터는 본문의 백틱도 쓰지 않는다(③ §절대 규칙 11, ④ §절대
    규칙 8). 다만 이 검사는 아직 **헤딩 줄만** 본다 — 본문 검사는 같은
    수정이 다음 실험에서 또 나오면 승격한다.
```
바꿀 문장:
```
    2026-09-12 부터는 본문의 백틱도 쓰지 않는다(③ §절대 규칙 11, ④ §절대
    규칙 8). 이 검사는 **헤딩 줄만** 본다(error) — 본문은 `check_body_style`
    이 warn 으로 본다(같은 날 결보 v5 회차에서 승격).
```

- [ ] **Step 4: 테스트를 돌린다**

Run: `PYTHONPATH=. python -m pytest tests/test_lab_validate.py -q -k BodyStyle`
Expected: 7개 PASS. `test_승인본은_0건이다` 가 실패하면 실패 메시지의 `첫 자리 N행` 을 승인본에서 열어 본다 — 그 줄이 규약 위반이면 승인본이 아니라 정규식을 좁힌다(예: 그 낱말을 `_STYLE_PARTICLE` 의 대안 목록에서 뺀다). 승인본은 고치지 않는다.

- [ ] **Step 5: ④⑤ 가 부르도록 스킬 문서 테스트를 먼저 쓴다**

`tests/test_skill_docs.py` 의 `class SkillDocInvariants` 에 추가(`test_every_skill_passes_item_count_to_the_section_check` 바로 뒤):

```python
    def test_body_style_check_is_called_by_writer_and_reviewer(self):
        # warn 검사라도 ④ 가 안 부르면 md 를 낸 세션 안에서 못 고치고, ⑤ 가
        # 안 부르면 같은 보고서를 두 기준으로 잰다.
        for name in ("결과", "리뷰"):
            with self.subTest(name):
                self.assertIn("check_body_style(", self.docs[name])
```

Run: `PYTHONPATH=. python -m pytest tests/test_skill_docs.py -q -k body_style`
Expected: FAIL (두 subTest).

- [ ] **Step 6: ④ §실행 절차 12 의 코드 블록에 검사를 더한다**

`.claude/skills/write-result-report/SKILL.md` 찾을 문장:
```
    for f in (validate.check_report_sections(rep, fmt.result, item_count=len(spec.items))
              + validate.check_report_references(rep, spec, root=root)
              + validate.check_notion_markdown(rep)):
        print(f)
    "
    ```

    **세 검사를 한꺼번에 돌린다.**
```
바꿀 문장:
```
    for f in (validate.check_report_sections(rep, fmt.result, item_count=len(spec.items))
              + validate.check_report_references(rep, spec, root=root)
              + validate.check_notion_markdown(rep)
              + validate.check_body_style(Path(rep).read_text(encoding='utf-8'))):
        print(f)
    "
    ```

    **네 검사를 한꺼번에 돌린다.** `check_body_style` 은 warn 이지만 여기서
    고친다 — §절대 규칙 8·18 의 기계 검사판이라 남기면 그대로 노션에 올라간다.
```

- [ ] **Step 7: ⑤ §실행 절차 4 의 코드 블록에 검사를 더한다**

`.claude/skills/review-lab-report/SKILL.md` 찾을 문장:
```
   for f in validate.check_report_references('<보고서 경로>', spec, root=root):
       print(f)
   "
   ```
```
바꿀 문장:
```
   for f in validate.check_report_references('<보고서 경로>', spec, root=root):
       print(f)
   for f in validate.check_body_style(Path('<보고서 경로>').read_text(encoding='utf-8')):
       print(f)
   "
   ```

   `check_body_style` 은 본문 문체(백틱·em dash·"첫째"·조사/단위 띄어쓰기)를
   warn 으로 잡는다 — ③ §절대 규칙 21·④ §절대 규칙 8·18 의 기계 검사판이다.
   warn 이라도 라운드 문서에 그대로 적는다.
```

- [ ] **Step 8: 전체 테스트를 돌린다**

Run: `PYTHONPATH=. python -m pytest tests/test_skill_docs.py tests/test_lab_validate.py -q`
Expected: 전부 PASS.

- [ ] **Step 9: 커밋한다**

```bash
git add scripts/lab/validate.py tests/test_lab_validate.py tests/test_skill_docs.py \
        ".claude/skills/write-result-report/SKILL.md" ".claude/skills/review-lab-report/SKILL.md"
git commit -m "$(cat <<'EOF'
feat(lab): validate.check_body_style — 본문 백틱·em dash·첫째·조사/단위 띄어쓰기를 warn 으로 잡고 ④⑤ 가 부른다

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: `isolate.build_isolated_tree` 를 일반화하고 `leak_sentences` 를 더한다

**Files:**
- Modify: `scripts/lab/isolate.py`
- Test: `tests/test_lab_isolate.py`

**Interfaces:**
- Consumes: `regen_compare._sentences(path, min_len) -> set[str]` (기존)
- Produces:
  - `build_isolated_tree(root, dest, experiment, answer_keys, clear_subdirs=_CLEARED, keep=()) -> Path` — `answer_keys` 에 `*`·`?`·`[` 가 있으면 `dest.glob` 로 편다; `clear_subdirs` 는 실험 폴더 아래에서 비울 하위 폴더 이름들; `keep` 은 비운 뒤 아카이브에서 되살릴 저장소 상대 경로들.
  - `leak_sentences(approved_md, tree, min_len=25, exts=(".md", ".py", ".txt")) -> list[str]` — `"<트리 상대경로>: <문장>"` 한 건에 한 줄.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_lab_isolate.py` 의 `_fake_repo()` 를 아래처럼 바꾼다(기존 파일들에 결보 관련 파일을 더한다):

```python
def _fake_repo():
    root = Path(tempfile.mkdtemp())
    (root / "docs/verify").mkdir(parents=True)
    (root / "docs/verify/answer.md").write_text("합격 조건\n", encoding="utf-8")
    exp = root / config.experiment_dir(1)
    (exp / "체크리스트").mkdir(parents=True)
    (exp / "결선도").mkdir()
    (exp / "output").mkdir()
    (exp / "실험사진/시트").mkdir(parents=True)
    (exp / "체크리스트/명세.md").write_text("정답\n", encoding="utf-8")
    (exp / "체크리스트/기록.md").write_text("기록\n", encoding="utf-8")
    (exp / "결선도/netlist.md").write_text("정답\n", encoding="utf-8")
    (exp / "output/실험01_예비보고서.md").write_text("예보 본문\n", encoding="utf-8")
    (exp / "output/실험01_결과보고서.md").write_text(
        "시험한 네 행은 모두 예상과 일치했다는 승인본 문장이다.\n", encoding="utf-8")
    (exp / "output/실험01_결과보고서_notion_baseline_v5.md").write_text("답\n", encoding="utf-8")
    (exp / "output/result_review_round1.md").write_text("리뷰\n", encoding="utf-8")
    (exp / "실험사진/시트/실험01_1-1_사진_3입력_AND.jpg").write_bytes(b"jpg")
    (root / "keep.md").write_text("남는 파일 E1.P1-1 언급\n", encoding="utf-8")
    _git(root, "init", "-q")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "seed")
    return root
```

그리고 파일 끝에 클래스 두 개를 추가한다:

```python
class ResultReportMode(unittest.TestCase):
    """결과보고서 검증용 격리 — output 만 비우고 예비보고서 md 를 되살린다.

    명세·기록·결선도·사진 시트는 ④ 의 **입력**이라 남아야 한다. 답안은
    output/ 의 결과보고서 계열과 리뷰 문서뿐이다.
    """

    def setUp(self):
        self.root = _fake_repo()
        self.dest = Path(tempfile.mkdtemp()) / "iso"
        exp = config.experiment_dir(1)
        build_isolated_tree(self.root, self.dest, 1, ["docs/verify"],
                            clear_subdirs=("output",),
                            keep=[f"{exp}/output/실험01_예비보고서.md"])
        self.exp = self.dest / exp

    def test_입력물은_남는다(self):
        self.assertTrue((self.exp / "체크리스트/명세.md").exists())
        self.assertTrue((self.exp / "체크리스트/기록.md").exists())
        self.assertTrue((self.exp / "결선도/netlist.md").exists())
        self.assertTrue((self.exp / "실험사진/시트/실험01_1-1_사진_3입력_AND.jpg").exists())

    def test_output_은_예비보고서만_남는다(self):
        self.assertEqual(sorted(p.name for p in (self.exp / "output").iterdir()),
                         ["실험01_예비보고서.md"])
        self.assertEqual((self.exp / "output/실험01_예비보고서.md").read_text(encoding="utf-8"),
                         "예보 본문\n")

    def test_status_는_비어_있다(self):
        self.assertEqual(_git(self.dest, "status", "--porcelain"), "")

    def test_글롭_키를_편다(self):
        dest = Path(tempfile.mkdtemp()) / "iso"
        exp = config.experiment_dir(1)
        build_isolated_tree(self.root, dest, 1, [f"{exp}/output/*결과보고서*"], clear_subdirs=())
        names = sorted(p.name for p in (dest / exp / "output").iterdir())
        self.assertEqual(names, ["result_review_round1.md", "실험01_예비보고서.md"])

    def test_없는_keep_경로는_예외다(self):
        dest = Path(tempfile.mkdtemp()) / "iso"
        with self.assertRaises(KeyError):
            build_isolated_tree(self.root, dest, 1, [], clear_subdirs=("output",),
                                keep=["없는/파일.md"])

    def test_기본_인자는_세_폴더를_비운다(self):
        dest = Path(tempfile.mkdtemp()) / "iso"
        build_isolated_tree(self.root, dest, 1, [])
        exp = dest / config.experiment_dir(1)
        self.assertFalse((exp / "체크리스트/기록.md").exists())
        self.assertEqual(list((exp / "output").iterdir()), [])


class LeakSentences(unittest.TestCase):
    def test_승인본_문장이_남은_파일을_짚는다(self):
        root = _fake_repo()
        approved = root / config.experiment_dir(1) / "output/실험01_결과보고서.md"
        tree = Path(tempfile.mkdtemp())
        (tree / "a.md").write_text("서론. 시험한 네 행은 모두 예상과 일치했다는 승인본 문장이다. 끝.\n",
                                   encoding="utf-8")
        (tree / "b.md").write_text("이 문장은 스물다섯 자를 넘기려고 일부러 길게 쓴 문장이다.\n",
                                   encoding="utf-8")
        hits = leak_sentences(approved, tree)
        self.assertEqual(len(hits), 1, hits)
        self.assertTrue(hits[0].startswith("a.md: "), hits[0])

    def test_git_폴더와_다른_확장자는_건너뛴다(self):
        root = _fake_repo()
        approved = root / config.experiment_dir(1) / "output/실험01_결과보고서.md"
        tree = Path(tempfile.mkdtemp())
        (tree / ".git").mkdir()
        (tree / ".git/x.md").write_text(approved.read_text(encoding="utf-8"), encoding="utf-8")
        (tree / "x.jpg").write_text(approved.read_text(encoding="utf-8"), encoding="utf-8")
        self.assertEqual(leak_sentences(approved, tree), [])
```

파일 상단 import 를 바꾼다:
```python
from scripts.lab.isolate import (_DERIVED, build_isolated_tree, leak_scan, leak_sentences,
                                 leak_tokens)
```

- [ ] **Step 2: 실패를 확인한다**

Run: `PYTHONPATH=. python -m pytest tests/test_lab_isolate.py -q`
Expected: ImportError (`leak_sentences`) 로 수집 단계에서 실패.

- [ ] **Step 3: 구현한다**

`scripts/lab/isolate.py` 를 아래로 바꾼다(모듈 docstring 은 그대로 두고 그 아래 전부 교체):

```python
import io
import re
import shutil
import subprocess
import tarfile
from pathlib import Path

from . import config
from .regen_compare import _sentences
from .spec_parser import parse_spec

# 기본값 — `draft-lab-spec` 검증용. 명세·결선도·output 을 통째로 비운다.
# 결과보고서 검증은 `clear_subdirs=("output",)` 에 `keep` 으로 예비보고서 md 를
# 되살린다 — 명세·기록·결선도·사진은 ④ 의 입력이지 답안이 아니다.
_CLEARED = ("체크리스트", "결선도", "output")
_GLOB_CHARS = ("*", "?", "[")


def _git(cwd, *args) -> str:
    return subprocess.run(["git", "-c", "user.name=ws", "-c", "user.email=ws@local", *args],
                          cwd=cwd, check=True, capture_output=True, text=True).stdout


def _guard(dest_real: Path, p: Path, key: str) -> Path:
    """`dest / key` 가 격리 트리 밖을 가리키면 예외. 절대경로 키·`..` 키가 그렇다."""
    p_real = p.resolve()
    if p_real == dest_real or not p_real.is_relative_to(dest_real):
        # `dest / key` 는 key 가 절대경로처럼 보이면 dest 를 버리고 key 그대로가
        # 된다(Path.__truediv__ 의 규칙) — 답안지 키에 실수로든 스킬 문서 오염으로든
        # 앞에 `/` 가 붙으면 격리 임시 폴더 밖 임의 경로를 rmtree/unlink 하게 된다.
        raise ValueError(f"답안지 키가 격리 트리 밖을 가리킨다: {key!r}")
    return p


def _expand_keys(dest: Path, dest_real: Path, answer_keys) -> list:
    out = []
    for key in answer_keys:
        if any(ch in key for ch in _GLOB_CHARS):
            if key.startswith(("/", "\\")) or ".." in Path(key).parts:
                raise ValueError(f"답안지 키가 격리 트리 밖을 가리킨다: {key!r}")
            out += [_guard(dest_real, p, key) for p in sorted(dest.glob(key))]
        else:
            out.append(_guard(dest_real, dest / key, key))
    return out


def _restore(archive: bytes, dest: Path, rel: str) -> None:
    """아카이브에서 `rel` 하나를 다시 꺼낸다. 없으면 KeyError — 조용히 넘기면
    '예비보고서 없이 돌았다' 가 판정에서 '④ 가 예보를 안 읽었다' 로 보인다."""
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as tf:
        member = tf.getmember(rel)
        tf.extract(member, dest, filter="data")


def build_isolated_tree(root, dest, experiment: int, answer_keys,
                        clear_subdirs=_CLEARED, keep=()) -> Path:
    root, dest = Path(root), Path(dest)
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    archive = subprocess.run(["git", "archive", "--format=tar", "HEAD"], cwd=root,
                             check=True, capture_output=True).stdout
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as tf:
        tf.extractall(dest, filter="data")

    dest_real = dest.resolve()
    for p in _expand_keys(dest, dest_real, answer_keys):
        if p.is_dir():
            shutil.rmtree(p)
        elif p.exists():
            p.unlink()

    exp = dest / config.experiment_dir(experiment)
    for sub in clear_subdirs:
        d = exp / sub
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)
    for rel in keep:
        _restore(archive, dest, rel)

    _git(dest, "init", "-q")
    _git(dest, "add", "-A")
    _git(dest, "commit", "-qm", "workspace")
    return dest


_DERIVED = re.compile(r"derived\s*\((.*)\)\s*$", re.S)


def leak_tokens(spec_path) -> list:
    """승인본 명세에서 트리에 남아 있으면 안 되는 문자열을 뽑는다."""
    spec = parse_spec(Path(spec_path))
    toks = []
    for it in spec.items:
        toks += [it.id, it.title]
    for t in spec.tables:
        m = _DERIVED.search(t.source or "")
        if m:
            toks += [part.strip() for part in m.group(1).split(";") if part.strip()]
    return toks


def leak_scan(dest, tokens, exts=(".md", ".py", ".html", ".txt", ".json")) -> list:
    dest = Path(dest)
    hits = []
    for p in sorted(dest.rglob("*")):
        if ".git" in p.parts or not p.is_file() or p.suffix not in exts:
            continue
        try:
            lines = p.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for n, line in enumerate(lines, 1):
            for tok in tokens:
                if tok in line:
                    hits.append(f"{p.relative_to(dest)}:{n}: {tok}")
    return hits


def leak_sentences(approved_md, tree, min_len=25, exts=(".md", ".py", ".txt")) -> list:
    """승인본 보고서의 문장(25자 이상)이 트리 어딘가에 그대로 남아 있는지 본다.

    명세 토큰(`leak_tokens`)은 결과보고서에 맞지 않는다 — 결보의 답은 항목 id 가
    아니라 문장이다. `regen_compare.shared_sentences` 와 같은 자름 규칙을 쓴다.
    """
    tree = Path(tree)
    wanted = _sentences(Path(approved_md), min_len)
    hits = []
    for p in sorted(tree.rglob("*")):
        if ".git" in p.parts or not p.is_file() or p.suffix not in exts:
            continue
        try:
            found = _sentences(p, min_len)
        except UnicodeDecodeError:
            continue
        for s in sorted(wanted & found, key=len, reverse=True):
            hits.append(f"{p.relative_to(tree)}: {s[:120]}")
    return hits
```

- [ ] **Step 4: 테스트를 돌린다**

Run: `PYTHONPATH=. python -m pytest tests/test_lab_isolate.py tests/test_lab_regen_compare.py -q`
Expected: 전부 PASS (기존 `BuildIsolatedTree` 5개 포함). `_fake_repo` 에 `output/` 을 추가했으므로 `test_실험_폴더는_비어_있되_남아_있다` 는 그대로 통과한다.

- [ ] **Step 5: 순환 import 가 없는지 확인한다**

Run: `PYTHONPATH=. python -c "from scripts.lab import isolate, regen_compare, specdiff; print('ok')"`
Expected: `ok`.

- [ ] **Step 6: 커밋한다**

```bash
git add scripts/lab/isolate.py tests/test_lab_isolate.py
git commit -m "$(cat <<'EOF'
feat(lab): isolate — 비울 폴더·되살릴 파일·글롭 키를 받고 승인본 문장 누출 검사를 더한다

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: `report_compare.py` — 보고서 구조 추출과 5갈래 대조

**Files:**
- Create: `scripts/lab/report_compare.py`
- Test: `tests/test_lab_report_compare.py`

**Interfaces:**
- Consumes: `md.parse_tables(body) -> list[MdTable(header, rows, line)]`, `md.split_frontmatter(text) -> (dict, body)`, `validate._HTML_TABLE`, `validate._HTML_TABLE_HEADER_ROW`, `validate._IMAGE_ANY`, `validate._reference_block(text) -> (lines, found)`, `validate._reference_entries(lines) -> list[str]`, `validate.check_body_style(md_text)` (Task 3)
- Produces:
  - `@dataclass Section(heading: str, level: int, tables: list[tuple[list, list]], images: list[str], sentences: list[str], empty_blocks: int)`
  - `@dataclass ReportShape(title: str, sections: list[Section], references: list[str])`
  - `report_shape(text: str) -> ReportShape`
  - `compare_reports(approved_text: str, regen_text: str) -> dict[str, list[str]]` — 키는 항상 `structure`·`cell`·`references`·`style`·`fact`·`wording` 여섯(`fact` 는 Task 6 이 채운다; 여기서는 빈 리스트)
  - `counted(diffs: dict) -> int` — `wording` 을 뺀 다섯 갈래의 합

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_lab_report_compare.py` 를 만든다:

```python
"""결과보고서 재생성물 ↔ 승인본 대조.

승인본은 실험01 결보(노션 v5 동기화본)이고, baseline v5 는 같은 내용을 노션이
HTML 표로 돌려준 것이다. 둘을 같게 읽지 못하면 이 도구는 형태 차이를 결함으로
센다 — 그래서 자기대조와 승인본↔baseline 대조가 첫 테스트다.
"""

import tempfile
import unittest
from pathlib import Path

from scripts.lab import config
from scripts.lab.report_compare import compare_reports, counted, report_shape

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / config.experiment_dir(1) / "output"
APPROVED = OUT / "실험01_결과보고서.md"
BASELINE_V5 = OUT / "실험01_결과보고서_notion_baseline_v5.md"


def _text(p):
    return p.read_text(encoding="utf-8")


def _variant(replacements):
    """승인본의 **첫 출현만** 바꾼 문자열."""
    text = _text(APPROVED)
    for old, new in replacements:
        assert text.count(old) >= 1, old
        text = text.replace(old, new, 1)
    return text


class Shape(unittest.TestCase):
    def test_승인본의_헤딩은_두_단계이고_제목은_따로_둔다(self):
        s = report_shape(_text(APPROVED))
        self.assertTrue(s.title.startswith("실험1 Basic Gates"))
        self.assertTrue(all(sec.level in (1, 2) for sec in s.sections))
        self.assertEqual(s.sections[0].heading, "실험 결과")

    def test_HTML_표와_파이프_표를_같은_셀로_읽는다(self):
        a = report_shape(_text(APPROVED))
        b = report_shape(_text(BASELINE_V5))
        self.assertEqual([sec.heading for sec in a.sections], [sec.heading for sec in b.sections])
        for x, y in zip(a.sections, b.sections):
            with self.subTest(x.heading):
                self.assertEqual(x.tables, y.tables)

    def test_여백_블록은_헤딩_앞_개수로_센다(self):
        s = report_shape("# 제목\n<table_of_contents color=\"gray\"/>\n<empty-block/>\n# 실험 결과\n본문.\n"
                         "<empty-block/>\n<empty-block/>\n# 고찰\n본문.\n")
        self.assertEqual([sec.empty_blocks for sec in s.sections], [1, 2])

    def test_참고문헌은_항목_단위다(self):
        s = report_shape("# 출처 및 참고문헌\n- 논리회로실험 강의노트\n- Nexperia, 74HC_HCT08 Rev. 9\n  https://x\n")
        self.assertEqual(len(s.references), 2)
        self.assertIn("https://x", s.references[1])


class Compare(unittest.TestCase):
    def test_자기대조는_0건이다(self):
        d = compare_reports(_text(APPROVED), _text(APPROVED))
        self.assertEqual(counted(d), 0, d)
        self.assertEqual(sorted(d), ["cell", "fact", "references", "structure", "style", "wording"])

    def test_승인본과_baseline_v5는_wording_밖_0건이다(self):
        d = compare_reports(_text(APPROVED), _text(BASELINE_V5))
        self.assertEqual(counted(d), 0, {k: v for k, v in d.items() if k != "wording"})

    def test_셀_하나가_다르면_cell_1건(self):
        d = compare_reports(_text(APPROVED), _variant([("\t| 1 | 1 | 1 | 1 | 1 |", "\t| 1 | 1 | 1 | 1 | 0 |")]))
        self.assertEqual(len(d["cell"]), 1, d["cell"])
        self.assertIn("'1'", d["cell"][0])
        self.assertIn("'0'", d["cell"][0])

    def test_소절이_빠지면_structure(self):
        d = compare_reports(_text(APPROVED), _variant([("## 실험 1-2) 3-input OR gate\n", "")]))
        self.assertTrue(any("실험 1-2) 3-input OR gate" in x for x in d["structure"]), d["structure"])

    def test_참고문헌_한_줄이_빠지면_references(self):
        d = compare_reports(_text(APPROVED), _variant([("- 논리회로실험 강의노트\n", "")]))
        self.assertEqual(len(d["references"]), 1, d["references"])

    def test_문체는_재생성_쪽만_본다(self):
        d = compare_reports(_text(APPROVED), _variant([("L1이 A·B", "L1 이 A·B")]))
        self.assertEqual(len(d["style"]), 1, d["style"])

    def test_wording_은_절마다_일치율_한_줄이다(self):
        d = compare_reports(_text(APPROVED), _text(APPROVED))
        self.assertTrue(all("1.00" in x for x in d["wording"]), d["wording"])
```

- [ ] **Step 2: 실패를 확인한다**

Run: `PYTHONPATH=. python -m pytest tests/test_lab_report_compare.py -q`
Expected: ModuleNotFoundError (`scripts.lab.report_compare`).

- [ ] **Step 3: 구현한다**

`scripts/lab/report_compare.py` 를 만든다:

```python
"""결과보고서 재생성물을 승인본과 대조한다.

`specdiff` 가 명세의 계약 필드를, `regen_compare` 가 결선도의 간선 집합을 보는
것과 짝이다 — 여기는 **보고서 md** 를 본다. 문장 동일성은 요구하지 않는다(요구하면
승인본 문장을 규칙에 베끼는 과적합으로 간다). 보는 것은 여섯 갈래다.

- `structure` — 헤딩 수열(레벨·이름), 절마다 표 수·행 수·그림 자리·앞 여백 블록 수
- `cell`      — 표 셀(헤더 포함). `**` 굵게 표시는 벗기고 본다
- `references`— 참고문헌 항목의 다중집합
- `style`     — `validate.check_body_style` 이 재생성물에서 잡은 것(승인본은 0건)
- `fact`      — 절마다 문장에서 뽑은 사실 토큰의 다중집합 차
- `wording`   — 절마다 문장 집합 일치율. **보고만 하고 세지 않는다**

표는 파이프 표와 노션이 되돌려주는 HTML `<table>` 을 같은 셀 목록으로 읽는다 —
승인본(파이프)과 baseline(HTML)을 대조해 0건이 나와야 이 도구를 믿을 수 있다
(`tests/test_lab_report_compare.py`).
"""

import difflib
import html
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from . import config, md, validate

_HEADING = re.compile(r"^(#{1,2})\s+(.*)$")
_EMPTY = re.compile(r"^\s*<empty-block\s*/>\s*$")
_TOC = re.compile(r"^\s*<table_of_contents\b")
_TR = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.IGNORECASE | re.DOTALL)
_TD = re.compile(r"<t[dh]\b[^>]*>(.*?)</t[dh]>", re.IGNORECASE | re.DOTALL)
_BOLD = re.compile(r"\*\*(.*?)\*\*")
_ESCAPED = re.compile(r"\\([{}_*\[\]])")
_SENT_SPLIT = re.compile(r"(?<=[.。!?])\s+")


@dataclass
class Section:
    heading: str
    level: int
    tables: list = field(default_factory=list)     # [(header, rows)]
    images: list = field(default_factory=list)     # alt 텍스트
    sentences: list = field(default_factory=list)
    empty_blocks: int = 0


@dataclass
class ReportShape:
    title: str
    sections: list
    references: list


def _norm(s: str) -> str:
    s = _BOLD.sub(r"\1", s)
    s = _ESCAPED.sub(r"\1", s)
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def _html_to_pipe(m) -> str:
    """HTML 표 하나를 파이프 표 문자열로. 첫 `<tr>` 을 헤더로 본다 — 노션 되읽기는
    항상 `header-row="true"` 를 붙이고, 안 붙은 표는 이 저장소에 없다."""
    indent = re.match(r"\s*", m.group(0)).group(0).replace("\n", "")
    rows = [[_norm(c) for c in _TD.findall(tr)] for tr in _TR.findall(m.group(2))]
    if not rows:
        return ""
    width = len(rows[0])
    lines = [indent + "| " + " | ".join(rows[0]) + " |",
             indent + "|" + "---|" * width]
    lines += [indent + "| " + " | ".join(r) + " |" for r in rows[1:]]
    return "\n".join(lines)


def _pipe_tables_only(text: str) -> str:
    return validate._HTML_TABLE.sub(_html_to_pipe, text)


def report_shape(text: str) -> ReportShape:
    """구조를 뽑는다. 첫 `# ` 헤딩은 문서 제목이라 절이 아니다 — 노션이 페이지
    제목으로 흡수해 되읽기에는 없다. 절은 그 다음부터, `#`·`##` 두 단계다."""
    _, body = md.split_frontmatter(_pipe_tables_only(text))
    lines = body.split("\n")
    title, sections, pending_empty = "", [], 0
    cur = None
    i = 0
    while i < len(lines):
        line = lines[i]
        table, nxt = md.parse_table_at(lines, i)
        if table is not None:
            if cur is not None:
                cur.tables.append(([_norm(c) for c in table.header],
                                   [[_norm(c) for c in r] for r in table.rows]))
            i = nxt
            continue
        hm = _HEADING.match(line)
        if hm:
            level, name = len(hm.group(1)), _norm(hm.group(2))
            # 문서 제목은 "바로 다음 비어 있지 않은 줄이 목차 블록" 인 `#` 헤딩뿐이다.
            # 되읽기(baseline)는 제목이 흡수돼 `<table_of_contents>` 로 시작하므로
            # 그 첫 `# 실험 결과` 를 제목으로 먹으면 절 수열이 승인본과 어긋난다.
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if level == 1 and cur is None and not title and j < len(lines) and _TOC.match(lines[j]):
                title = name
            else:
                cur = Section(heading=name, level=level, empty_blocks=pending_empty)
                sections.append(cur)
            pending_empty = 0
            i += 1
            continue
        if _EMPTY.match(line):
            pending_empty += 1
            i += 1
            continue
        if _TOC.match(line) or not line.strip():
            i += 1
            continue
        if cur is not None:
            imgs = validate._IMAGE_ANY.findall(line)
            if imgs:
                cur.images += [_norm(alt) for alt, _ in imgs]
                line = validate._IMAGE_ANY.sub("", line)
            prose = _norm(re.sub(r"^\s*[-*+]\s+", "", line))
            cur.sentences += [s for s in _SENT_SPLIT.split(prose) if len(s) >= 5]
        i += 1
    ref_lines, _ = validate._reference_block(body)
    refs = [_norm(re.sub(r"^\s*(?:[-*+]|\d+[.)])\s+", "", e))
            for e in validate._reference_entries(ref_lines)]
    return ReportShape(title=title, sections=sections, references=refs)


def _pair_sections(a, b):
    """이름으로 짝짓는다(첫 출현). 순서·누락은 structure 가 따로 알린다."""
    by_name = {}
    for s in b:
        by_name.setdefault(s.heading, s)
    return [(s, by_name.get(s.heading)) for s in a]


def _structure(a: ReportShape, b: ReportShape) -> list:
    out = []
    ha, hb = [f"{'#' * s.level} {s.heading}" for s in a.sections], \
             [f"{'#' * s.level} {s.heading}" for s in b.sections]
    if ha != hb:
        for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(a=ha, b=hb).get_opcodes():
            if tag == "equal":
                continue
            out.append(f"헤딩 {tag}: 원본 {ha[i1:i2]} / 재생성 {hb[j1:j2]}")
    for x, y in _pair_sections(a.sections, b.sections):
        if y is None:
            continue
        if len(x.tables) != len(y.tables):
            out.append(f"절 '{x.heading}': 표 {len(x.tables)}개 / 재생성 {len(y.tables)}개")
        for k, (tx, ty) in enumerate(zip(x.tables, y.tables), 1):
            if len(tx[1]) != len(ty[1]):
                out.append(f"절 '{x.heading}' 표 {k}: 행 {len(tx[1])} / 재생성 {len(ty[1])}")
        if x.images != y.images:
            out.append(f"절 '{x.heading}': 그림 {x.images} / 재생성 {y.images}")
        if x.empty_blocks != y.empty_blocks:
            out.append(f"절 '{x.heading}': 앞 여백 블록 {x.empty_blocks} / 재생성 {y.empty_blocks}")
    return out


def _cells(a: ReportShape, b: ReportShape) -> list:
    out = []
    for x, y in _pair_sections(a.sections, b.sections):
        if y is None:
            continue
        for k, (tx, ty) in enumerate(zip(x.tables, y.tables), 1):
            grid_x = [tx[0]] + tx[1]
            grid_y = [ty[0]] + ty[1]
            for r, (rx, ry) in enumerate(zip(grid_x, grid_y)):
                for c, (cx, cy) in enumerate(zip(rx, ry), 1):
                    if cx != cy:
                        where = "헤더" if r == 0 else f"행{r}"
                        out.append(f"절 '{x.heading}' 표 {k} {where} 열{c}: 원본 '{cx}' / 재생성 '{cy}'")
                if len(rx) != len(ry):
                    out.append(f"절 '{x.heading}' 표 {k} 행{r}: 셀 {len(rx)}개 / 재생성 {len(ry)}개")
    return out


def _references(a: ReportShape, b: ReportShape) -> list:
    ca, cb = Counter(a.references), Counter(b.references)
    out = [f"원본에만 — {r}" for r in (ca - cb).elements()]
    out += [f"재생성에만 — {r}" for r in (cb - ca).elements()]
    return out


def _wording(a: ReportShape, b: ReportShape) -> list:
    out = []
    for x, y in _pair_sections(a.sections, b.sections):
        if y is None:
            continue
        sx, sy = set(x.sentences), set(y.sentences)
        union = sx | sy
        j = (len(sx & sy) / len(union)) if union else 1.0
        out.append(f"절 '{x.heading}': 문장 일치율 {j:.2f} (원본 {len(sx)} / 재생성 {len(sy)} / 공통 {len(sx & sy)})")
    return out


def compare_reports(approved_text: str, regen_text: str) -> dict:
    a, b = report_shape(approved_text), report_shape(regen_text)
    return {
        "structure": _structure(a, b),
        "cell": _cells(a, b),
        "references": _references(a, b),
        "style": [f.message for f in validate.check_body_style(regen_text)],
        "fact": [],
        "wording": _wording(a, b),
    }


def counted(diffs: dict) -> int:
    return sum(len(v) for k, v in diffs.items() if k != "wording")
```

- [ ] **Step 4: 테스트를 돌린다**

Run: `PYTHONPATH=. python -m pytest tests/test_lab_report_compare.py -q`
Expected: 전부 PASS. `_variant` 의 `assert text.count(old) >= 1` 이 죽으면 승인본의 그 문장이 다른 것이니 `grep -n` 으로 실제 줄을 찾아 `old` 를 그 원문으로 바꾼다(테스트 뜻은 그대로다). `test_승인본과_baseline_v5는_wording_밖_0건이다` 가 실패하면 실패 메시지의 갈래를 본다 — `references` 면 두 목록을 나란히 출력해(`print(report_shape(_text(APPROVED)).references)`, baseline 도 같이) 노션이 바꾼 서식(불릿 마커·공백·이스케이프)을 `_norm` 에 더한다; `structure` 의 여백 블록이면 baseline 의 `<empty-block/>` 줄 수를 세어 승인본과 같은지 확인하고, 다르면 노션 왕복 노이즈이므로 `empty_blocks` 비교를 `structure` 에서 빼고 docstring 에 그 이유를 적는다. 항목 수·헤딩·셀이 다르면 진짜 손실이라 사용자에게 보고한다.

- [ ] **Step 5: 커밋한다**

```bash
git add scripts/lab/report_compare.py tests/test_lab_report_compare.py
git commit -m "$(cat <<'EOF'
feat(lab): report_compare — 결과보고서 재생성물을 승인본과 구조·셀·참고문헌·문체·산문으로 대조한다

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: `report_compare` 에 사실 토큰 갈래와 판정 초안을 더한다

**Files:**
- Modify: `scripts/lab/report_compare.py`
- Test: `tests/test_lab_report_compare.py`

**Interfaces:**
- Consumes: Task 5 의 `ReportShape`, `compare_reports`, `counted`; `config.experiment_dir(n) -> str`, `config.experiment_folder_name(n) -> str`
- Produces:
  - `fact_tokens(sentences: list[str]) -> Counter`
  - `compare_reports(...)["fact"]` 가 채워진다
  - `judgment_markdown(experiment: int, regen_md, leak_hits=(), agent_report: str = "") -> str` — `## 1.`~`## 7.` 일곱 절, 첫 줄에 세션 메모리 주입 명시

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_lab_report_compare.py` 끝에 추가:

```python
from scripts.lab.report_compare import fact_tokens, judgment_markdown


class Facts(unittest.TestCase):
    def test_사실_토큰을_뽑는다(self):
        c = fact_tokens(["전류는 9.4mA 이고 74HC08 의 1번 핀이 고착-1 이면 A=B=1 에서 {01, 10, 11} 가 (미확인)"])
        self.assertEqual(c["9.4mA"], 1)
        self.assertEqual(c["74HC08"], 1)
        self.assertEqual(c["핀 1"], 1)
        self.assertEqual(c["고착-1"], 1)
        self.assertEqual(c["A=B=1"], 1)
        self.assertEqual(c["{01, 10, 11}"], 1)
        self.assertEqual(c["(미확인)"], 1)

    def test_수치가_바뀌면_fact_에_양쪽_값이_적힌다(self):
        d = compare_reports(_text(APPROVED), _variant([("9.4mA", "7.9mA")]))
        self.assertEqual(len(d["fact"]), 1, d["fact"])
        self.assertIn("9.4mA", d["fact"][0])
        self.assertIn("7.9mA", d["fact"][0])

    def test_자기대조는_fact_도_0(self):
        self.assertEqual(compare_reports(_text(APPROVED), _text(APPROVED))["fact"], [])


class Judgment(unittest.TestCase):
    def test_일곱_절과_메모리_주입_문장이_있다(self):
        d = Path(tempfile.mkdtemp())
        regen = d / "실험01_결과보고서.md"
        regen.write_text(_variant([("9.4mA", "7.9mA")]), encoding="utf-8")
        text = judgment_markdown(1, regen, leak_hits=["a.md: 문장"], agent_report="보고 본문")
        for n in range(1, 8):
            self.assertIn(f"## {n}.", text)
        self.assertIn("세션 메모리 주입", text)
        self.assertIn("7.9mA", text)
        self.assertIn("a.md: 문장", text)
        self.assertIn("보고 본문", text)
        self.assertIn("[ ] 규칙 없음", text)
```

- [ ] **Step 2: 실패를 확인한다**

Run: `PYTHONPATH=. python -m pytest tests/test_lab_report_compare.py -q -k "Facts or Judgment"`
Expected: ImportError (`fact_tokens`).

- [ ] **Step 3: 구현한다**

`scripts/lab/report_compare.py` 의 `_wording` 함수 앞에 추가:

```python
# 문장이 달라도 사실이 같으면 같은 보고서다 — 그래서 문장이 아니라 토큰을 센다.
# 수치+단위, IC 이름, 벡터 집합, 입력 조건, 핀 번호, 고착 표기, (미확인).
_FACT = re.compile(
    r"\d+(?:\.\d+)?(?:V|mA|μA|µA|Ω|kΩ|ns/V|ns|°C)"
    r"|74[A-Z]*\d{2,3}"
    r"|\{[01,\s]+\}"
    r"|[A-Z]=(?:[A-Z]=)*[01]"          # A=1, A=B=1, C=0
    r"|\d+번 핀|핀\s?\d+"
    r"|고착-[01]"
    r"|\(미확인\)")
_PIN_KO = re.compile(r"^(\d+)번 핀$")


def fact_tokens(sentences) -> Counter:
    """`1번 핀` 과 `핀 1` 은 같은 사실이라 `핀 1` 로 모은다."""
    c = Counter()
    for s in sentences:
        for tok in _FACT.findall(s):
            tok = re.sub(r"\s+", " ", tok).strip()
            m = _PIN_KO.match(tok)
            if m:
                tok = f"핀 {m.group(1)}"
            c[tok] += 1
    return c


def _facts(a: ReportShape, b: ReportShape) -> list:
    out = []
    for x, y in _pair_sections(a.sections, b.sections):
        if y is None:
            continue
        cx, cy = fact_tokens(x.sentences), fact_tokens(y.sentences)
        only_x = sorted((cx - cy).items())
        only_y = sorted((cy - cx).items())
        if only_x or only_y:
            fmt = lambda items: ", ".join(f"{t}×{n}" if n > 1 else t for t, n in items) or "—"
            out.append(f"절 '{x.heading}': 원본에만 {fmt(only_x)} / 재생성에만 {fmt(only_y)}")
    return out
```

`compare_reports` 의 `"fact": [],` 를 `"fact": _facts(a, b),` 로 바꾼다.

파일 끝에 추가:

```python
_ROOT = Path(__file__).resolve().parents[2]   # scripts/lab/report_compare.py → 저장소 루트


def approved_report_path(experiment: int) -> Path:
    """승인본 경로. 저장소 루트 기준 절대경로라 어느 CWD 에서 불러도 같다."""
    return (_ROOT / config.experiment_dir(experiment) / "output"
            / f"{config.experiment_folder_name(experiment)}_결과보고서.md")


def judgment_markdown(experiment: int, regen_md, leak_hits=(), agent_report: str = "") -> str:
    """판정 초안. 도구가 셀 수 있는 것만 센다 — `fact` 의 세 갈래 분류(규칙 없음 /
    검사 없음 / 환경)와 산문은 사람이 원본과 나란히 읽고 표시한다."""
    approved = approved_report_path(experiment).read_text(encoding="utf-8")
    regen = Path(regen_md).read_text(encoding="utf-8")
    d = compare_reports(approved, regen)
    L = [f"# 실험{experiment} 결과보고서 격리 재생성 판정 초안", "",
         "이 회차는 세션 메모리 주입 아래서 돌았다.", "",
         f"## 1. 구조 {len(d['structure'])}건"] + [f"- {x}" for x in d["structure"]]
    L += ["", f"## 2. 표 셀 {len(d['cell'])}건"] + [f"- {x}" for x in d["cell"]]
    L += ["", f"## 3. 참고문헌 {len(d['references'])}건"] + [f"- {x}" for x in d["references"]]
    L += ["", f"## 4. 문체 {len(d['style'])}건 (재생성물, `check_body_style`)"] + [f"- {x}" for x in d["style"]]
    L += ["", f"## 5. 사실 토큰 {len(d['fact'])}건 — 한 줄마다 하나에 표시한다"]
    L += [f"- {x}\n    - [ ] 규칙 없음  [ ] 검사 없음  [ ] 환경(데이터시트 못 열음 등)" for x in d["fact"]]
    L += ["", "## 6. 산문 일치율 (기준 밖 — 나란히 읽는다)"] + [f"- {x}" for x in d["wording"]]
    L += ["", "사람이 볼 것:",
          "- 사실 토큰 차이마다 위 세 칸 중 하나에 표시한다. `규칙 없음`·`검사 없음` 만 규칙 제안의 재료다.",
          "- 산문은 절마다 원본과 나란히 읽는다 — 사실이 같고 문장만 다른 것은 결함이 아니다.",
          "- 에이전트 보고 3항(⑤ 첫 실행 error/warn/info)으로 **규칙이 막았나 / 검사가 잡았나** 를 가른다.",
          "", f"## 7. 구조적 누출 {len(list(leak_hits))}건"] + [f"- {x}" for x in leak_hits]
    L += ["", "> 구조 대조가 0건이라는 것은 같은 틀이라는 뜻이고, 같은 보고서라는 뜻이 아니다.", ""]
    if agent_report:
        L += ["## 에이전트 보고 (원문)", "", agent_report, ""]
    return "\n".join(L)
```

- [ ] **Step 4: 테스트를 돌린다**

Run: `PYTHONPATH=. python -m pytest tests/test_lab_report_compare.py -q`
Expected: 전부 PASS. `test_자기대조는_0건이다` 와 baseline 대조가 `fact` 때문에 깨지면 baseline 의 `\{01, 10, 11\}` 이스케이프가 `_norm` 에서 풀리는지 본다(`_ESCAPED` 가 `\{`·`\}` 를 벗긴다).

- [ ] **Step 5: 커밋한다**

```bash
git add scripts/lab/report_compare.py tests/test_lab_report_compare.py
git commit -m "$(cat <<'EOF'
feat(lab): report_compare — 사실 토큰 갈래와 판정 초안(judgment_markdown)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
EOF
)"
```

---

### Task 7: 스킬 문서·런북을 쓰고 형제 문서·테스트를 맞춘다

**Files:**
- Create: `.claude/skills/verify-write-result-report/SKILL.md`
- Create: `docs/verify/write-result-report.md`
- Modify: `.claude/skills/verify-draft-lab-spec/SKILL.md` (KEYS, §답안지 목록)
- Modify: `.claude/skills/sync-report-to-notion/SKILL.md` (pull 14단계)
- Test: `tests/test_skill_docs.py`

**Interfaces:**
- Consumes: `isolate.build_isolated_tree(..., clear_subdirs, keep)`, `isolate.leak_scan`, `isolate.leak_sentences`, `report_compare.compare_reports`, `report_compare.counted`, `report_compare.judgment_markdown`, `report_compare.approved_report_path`
- Produces: `/verify-write-result-report <실험N>` 절차 문서. Task 8 이 이 문서를 글자 그대로 따른다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_skill_docs.py` 상단 상수에 추가(`VERIFY = ...` 다음 줄):
```python
VERIFY_RESULT = ROOT / ".claude/skills/verify-write-result-report/SKILL.md"
```
`DOCS` 에 항목 추가:
```python
    "결보검증": (VERIFY_RESULT, ("절대 규칙", "실행 절차")),
```

`SkillDocInvariants` 의 기존 `test_the_verifier_answer_keys_agree_in_all_three_places` 안에서 아래 한 줄을 바꾼다. 찾을 줄:
```python
        other_skills = {k for k in keys if k.startswith(".claude/skills/")} - {
            ".claude/skills/verify-draft-lab-spec", ".claude/skills/breadboard-diagram"}
```
바꿀 줄:
```python
        other_skills = {k for k in keys if k.startswith(".claude/skills/")
                        and "/verify-" not in k} - {".claude/skills/breadboard-diagram"}
```

그리고 `test_the_verifier_does_not_fix_anything` 바로 뒤에 메서드 세 개를 추가:

```python
    def test_the_result_verifier_answer_keys_agree_with_its_prose(self):
        # `verify-write-result-report` 판. "스킬 여덟" 예외는 없고, `{exp}` 로
        # 실험 폴더를 끼우는 f-string 키는 `<실험NN>` 불릿이 맡는다.
        text = self.docs["결보검증"]
        proc = sections(text)["실행 절차"]
        start = proc.index("KEYS = [") + len("KEYS = [")
        end = proc.index("]", start)
        keys = {m.rstrip("/") for m in re.findall(r"'([^']+)'", proc[start:end])}
        literal_keys = {k for k in keys if "{exp}" not in k}

        sec = sections(text)["답안지 목록"]
        before, marker, after = sec.partition("남기는 것:")
        self.assertNotEqual(marker, "")
        prose, placeholder = set(), set()
        for b in re.split(r"(?m)^- ", before)[1:]:
            toks = {m.rstrip("/") for m in re.findall(r"`([^`]+)`", b)}
            (placeholder if "<실험NN>" in b else prose).update(toks)
        self.assertEqual(prose - literal_keys, set(), prose - literal_keys)
        self.assertEqual(literal_keys - prose, set(), literal_keys - prose)
        for k in literal_keys:
            with self.subTest(k):
                self.assertNotIn(k, after)

    def test_the_result_verifier_lists_itself_and_its_tools_as_answer_keys(self):
        sec = sections(self.docs["결보검증"])["답안지 목록"]
        for key in ("`.claude/skills/verify-write-result-report/`", "`docs/verify/`",
                    "`docs/plans/`", "`docs/notion-feedback/`", "`tests/`",
                    "`scripts/lab/report_compare.py`", "`scripts/lab/isolate.py`"):
            with self.subTest(key):
                self.assertIn(key, sec)

    def test_the_result_verifier_prompt_and_non_goals_match_the_sibling(self):
        sec = sections(self.docs["결보검증"])["에이전트 프롬프트"]
        self.assertNotIn("합격", sec)
        self.assertNotIn("채점", sec)
        self.assertIn("`git log`", sec)
        self.assertIn("한 번에 통과했으면 그렇다고 명시", sec)
        self.assertIn("`review-lab-report`", sec)
        non = sections(self.docs["결보검증"])["비-목표"]
        self.assertIn("`write-result-report` 를 고치지 않는다", non)
        self.assertIn("커밋하지 않는다", non)

    def test_both_verifiers_keep_each_other_out_of_the_tree(self):
        # 두 검증 스킬은 서로의 프롬프트·답안지 목록을 싣는다 — 한쪽 격리 트리에
        # 다른 쪽이 남으면 에이전트가 거기서 시험 형식을 읽는다.
        self.assertIn("'.claude/skills/verify-write-result-report'", self.docs["검증"])
        self.assertIn("'.claude/skills/verify-draft-lab-spec'", self.docs["결보검증"])
```

Run: `PYTHONPATH=. python -m pytest tests/test_skill_docs.py -q`
Expected: `FileNotFoundError` (setUp 이 새 문서를 읽는다) — 새 문서를 만들면 다음 단계에서 나머지가 실패한다.

- [ ] **Step 2: 스킬 문서를 만든다**

`.claude/skills/verify-write-result-report/SKILL.md` 를 아래 내용 그대로 만든다.

````markdown
---
name: verify-write-result-report
description: write-result-report 와 review-lab-report 를 답안 없는 격리 트리에서 다시 실행시키고 승인된 결과보고서와 자동 대조해 판정 초안과 런북 기록 행을 낸다. 사용자가 "결보 격리 재생성 돌려", "실험1 결과보고서로 스킬 검증", "write-result-report 고쳤으니 검증해" 등을 요청하거나 /verify-write-result-report 를 호출할 때 쓴다. 승인된 결과보고서가 노션에 올라간 실험(통제군)만 잰다. 아무것도 고치지 않는다 — 갈린 자리는 규칙 제안 표로 사용자에게 묻는 데서 끝난다.
---

# verify-write-result-report

`verify-draft-lab-spec` 의 결과보고서 판이다. ④ `write-result-report` 문서는
컴파일도 실행도 되지 않으므로 결함은 규칙만 주고 격리 에이전트에게 실행시켜야
나온다. 이 스킬은 그 실행을 `/` 한 번으로 만들고, 재생성물을 승인본과 여섯
갈래(구조·표 셀·참고문헌·문체·사실 토큰·산문)로 대조한다. 대조 도구는
`scripts/lab/report_compare.py` 이고 갈래의 뜻은 그 docstring 이 정본이다.

## 인자

`<실험N>`

- 번호 토큰이 없으면 한 줄로 되묻고 중단한다.
- 통제군 조건: `<실험NN>/output/<실험NN>_결과보고서.md` 가 있고, 같은 폴더
  `notion.json` 에 `결과보고서` 레코드가 있으며, 그 최신 판본의
  `_notion_baseline_v<N>.md` 와 원본이 `report_compare` 로 산문 밖 0건이어야
  한다(0단계가 잰다). 하나라도 아니면 "통제군이 없다" 로 거절한다.
  2026-09-12 기준 자격이 있는 것은 실험01(v5) 뿐이다.

## 절대 규칙

1. **답안지를 전부 뺀 트리에서만 돈다.** 목록은 §답안지 목록이고 첫 줄이 이
   스킬 자신이다. 목록을 줄이지 않는다.
2. **못 빼는 누출은 적는다.** ④ `write-result-report/SKILL.md` 자체가 실험01
   사례(핀 1 고착-1, 2-1 의 011, 칩 불량 경위)를 규칙 예시로 싣는다. 시험
   대상이라 못 뺀다. 2단계의 누출 결과를 판정.md 7절에 "구조적 누출" 로
   적고, **그 자리의 일치는 합격 근거로 세지 않는다.**
3. **프롬프트에 사유와 합격 조건을 쓰지 않는다.** 이력 명령(`git log`·`show`·
   `diff`)도 금지한다. §에이전트 프롬프트를 글자 그대로 쓰고 자리표시자만
   채운다.
4. **규칙이 막았는지 검사가 잡았는지를 가른다.** 에이전트 보고 3항(⑤ 첫 실행의
   error/warn/info 원문)이 근거다. 검사가 잡은 항목은 ④ 문서의 빈 자리로
   취급한다. 첫 실행 error 0 인데 승인본과 갈렸으면 **규칙도 검사도 없는
   자리**다 — 통제군 대조만이 그것을 본다.
5. **자동 합격은 없다.** 도구는 갈래별로 세기만 한다. 사실 토큰 차이의 세
   갈래(`규칙 없음`·`검사 없음`·`환경`)와 산문은 사람이 원본과 나란히 읽고
   표시한다. **산문 일치율은 기준 밖이다** — 문장이 같기를 요구하면 승인본
   문장을 규칙에 베끼는 과적합으로 간다.
6. **아무것도 고치지 않는다.** ④ 도 ⑤ 도 승인본도 규칙도. 갈린 자리는 ⑦
   `sync-report-to-notion` 의 분류 표 형식(무엇 / 분류 / 반영 대상 파일·절)으로
   **제안**하고 멈춘다. 커밋하지 않는다.
7. **세션 메모리 주입을 명시한다.** 하네스가 컨트롤러의 세션 메모리를
   서브에이전트에 주입한다. 막을 수 없으니 판정.md 첫 줄에 적는다 —
   `judgment_markdown` 이 자동으로 넣는다.
8. **회차 상한은 세션당 3회다.** 재실행 사유는 판정에서 `규칙 없음`·`검사
   없음` 으로 표시된 차이가 남아 있고 사용자가 그 규칙 제안을 승인해 ④·⑤ 를
   고쳐 커밋한 경우뿐이다. 산문만 다른 것은 재실행 사유가 아니다.

## 실행 절차

0. **실험 번호를 폴더로 옮기고 통제군을 확인한다.**

   ```bash
   python3 -c "
   from pathlib import Path
   from scripts.lab import config, notion
   from scripts.lab.report_compare import approved_report_path, compare_reports, counted
   d = Path(config.experiment_dir(<실험번호>))
   ap = approved_report_path(<실험번호>)
   recs = [r for r in notion.load_records(d / 'output') if r['kind'] == '결과보고서']
   print('O' if ap.exists() else 'X', ap)
   print('O' if recs else 'X', '노션 결과보고서 레코드', len(recs), '건')
   base = d / 'output' / f\"{ap.stem}_notion_baseline_v{recs[-1]['version']}.md\" if recs else None
   print('O' if base and base.exists() else 'X', base)
   if ap.exists() and base and base.exists():
       diff = compare_reports(ap.read_text(encoding='utf-8'), base.read_text(encoding='utf-8'))
       print('원본↔baseline 산문 밖 차이', counted(diff), '건')
   "
   ```

   `X` 가 하나라도 있거나 차이가 0 이 아니면 거절한다 — 원본이 승인본이 아니다.

   ```bash
   git status --porcelain .claude/skills scripts/lab 보고서/<실험NN>
   ```

   출력이 비어 있지 않으면 멈추고 사용자에게 묻는다 — 격리 트리는
   `git archive HEAD` 로 **HEAD** 를 푸므로 커밋 안 한 수정은 재지지 않는다.

1. **격리 트리를 만든다.** 시스템 임시 폴더 아래에 둔다. 답안지 목록은
   §답안지 목록을 **그대로** 옮긴다. `output/` 은 통째로 비운 뒤 예비보고서 md
   만 되살린다 — "예비보고서와의 비교" 절의 입력이다.

   ```bash
   python3 -c "
   import tempfile
   from pathlib import Path
   from scripts.lab import config
   from scripts.lab.isolate import build_isolated_tree
   exp = config.experiment_dir(<실험번호>)
   name = config.experiment_folder_name(<실험번호>)
   KEYS = [
       '.claude/skills/verify-write-result-report', '.claude/skills/verify-draft-lab-spec',
       'docs/verify', 'docs/plans', 'docs/notion-feedback', 'docs/rule-friction',
       'docs/corpus-audit', 'docs/study', 'docs/강의노트_이론_실험_매핑_정리.md',
       'scripts/lab/report_compare.py', 'scripts/lab/specdiff.py',
       'scripts/lab/regen_compare.py', 'scripts/lab/isolate.py', 'tests',
       f'{exp}/*결과보고서*.pdf',
   ]
   dest = Path(tempfile.gettempdir()) / f'iso-{name}'
   build_isolated_tree(Path('.'), dest, <실험번호>, KEYS,
                       clear_subdirs=('output',),
                       keep=[f'{exp}/output/{name}_예비보고서.md'])
   print(dest)
   "
   ```

   `체크리스트/`·`결선도/`·`실험사진/`(시트 포함)·`실험중있었던일.md` 는 남는다
   — ④ 의 입력이다. 이 트리는 `HEAD` 의 사본이다.

2. **누출을 훑는다.** 승인본 문장(25자 이상)과 사례 토큰으로 트리를 훑는다.

   ```bash
   python3 -c "
   import tempfile
   from pathlib import Path
   from scripts.lab import config
   from scripts.lab.isolate import leak_scan, leak_sentences
   from scripts.lab.report_compare import approved_report_path
   dest = Path(tempfile.gettempdir()) / f'iso-{config.experiment_folder_name(<실험번호>)}'
   for h in leak_sentences(approved_report_path(<실험번호>), dest): print('문장', h)
   for h in leak_scan(dest, ['고착-1', 'A=B=1', '칩 불량']): print('토큰', h)
   "
   ```

   남는 자리가 `.claude/skills/write-result-report/SKILL.md` 와
   `보고서/<실험NN>/체크리스트/기록.md`(종료 메모의 사실)뿐이면 정상이다(§절대
   규칙 2). 다른 파일이 나오면 §답안지 목록에 더하고 1단계부터 다시 한다.
   결과는 6단계의 판정.md 7절에 넣는다.

3. **대조 도구를 자기대조로 점검한다.** 승인본을 승인본과 대조해 0건, 승인본을
   최신 baseline 과 대조해 산문 밖 0건이어야 다음 단계의 숫자를 믿을 수 있다.

   ```bash
   python3 -c "
   from scripts.lab.report_compare import approved_report_path, compare_reports, counted
   t = approved_report_path(<실험번호>).read_text(encoding='utf-8')
   print('self', counted(compare_reports(t, t)))
   "
   ```

   `self 0` 이어야 한다. baseline 대조는 0단계가 이미 찍었다.

4. **에이전트를 띄운다.** Agent 도구, 기본 모델, 백그라운드. §에이전트 프롬프트를
   글자 그대로 쓰고 `<작업 디렉토리>`·`<실험번호>`·`<파이썬 명령>`·`<poppler 경로>`
   만 채운다. 파이썬 명령과 poppler 경로는 이 PC 에서 `where python`·`where
   pdftoppm` 으로 확인한 값을 쓴다(macOS 면 `which`). 기다리는 동안 **격리
   트리와 승인본은 건드리지 않는다.** 형제 스킬의 실측은 305k 토큰·21분이다.

5. **산출물을 보존한다.** 끝나면 격리 트리의 `보고서/<실험NN>/output/` 과
   `tmp/격리보고.md` 를 저장소 `tmp/verify-artifacts/<실험NN>-결보격리-<YYYY-MM-DD>/`
   로 복사한다(`tmp/` 는 gitignore). 격리 트리를 지우기 전에 한다.

6. **판정 초안을 낸다.**

   ```bash
   python3 -c "
   from pathlib import Path
   from scripts.lab import config
   from scripts.lab.report_compare import judgment_markdown
   name = config.experiment_folder_name(<실험번호>)
   art = Path('tmp/verify-artifacts/<실험NN>-결보격리-<YYYY-MM-DD>')
   report = (art / '격리보고.md').read_text(encoding='utf-8') if (art / '격리보고.md').exists() else ''
   leaks = <2단계 출력 줄 목록>
   out = art / '판정.md'
   out.write_text(judgment_markdown(<실험번호>, art / 'output' / f'{name}_결과보고서.md',
                                    leak_hits=leaks, agent_report=report), encoding='utf-8')
   print(out.read_text(encoding='utf-8'))
   "
   ```

7. **사람이 본다.** 판정.md 5절의 사실 토큰 차이마다 세 칸 중 하나에 표시하고,
   6절의 산문은 절마다 원본과 나란히 읽는다. 에이전트 보고 3항으로 §절대 규칙
   4 의 갈림을 가른다. 결과를 판정.md 끝에 "## 8. 판정" 으로 적는다: 구조·셀·
   참고문헌·문체의 일치 여부, `규칙 없음`·`검사 없음` 으로 표시한 자리와 그
   근거, 원본 쪽 결함.

8. **런북 기록 표에 행을 붙인다.** `docs/verify/write-result-report.md` 의
   `## 기록` 표 마지막 행 뒤에 한 줄:

   `| <YYYY-MM-DD> | \`<git rev-parse --short HEAD>\` | V1 — 실험NN 무인자 재생성 + ⑤ | <한 줄 요약>. 판정: tmp/verify-artifacts/<실험NN>-결보격리-<날짜>/판정.md |`

9. **보고한다.** 네 가지를 낸다 — 일치한 갈래, `규칙 없음`·`검사 없음` 자리와
   그 근거, `환경` 으로 뺀 자리, 원본 쪽 결함. `규칙 없음`·`검사 없음` 자리마다
   ⑦ 분류 표 형식으로 **제안**한다(무엇 / 분류 / 반영 대상 파일·절). 규칙 신설과
   승인본 수정은 이 스킬 밖이다. 격리 트리를 지운다. 사용자가 제안을 승인해
   ④·⑤ 를 고치고 커밋하면 같은 명령을 다시 돈다(§절대 규칙 8).

## 답안지 목록

격리 트리에서 지우는 것. 정본은 이 절이고 코드는 받기만 한다. 첫 줄이 이 스킬
자신이다.

- `.claude/skills/verify-write-result-report/` — 이 문서. 합격 조건과 프롬프트가
  있다
- `.claude/skills/verify-draft-lab-spec/` — 형제 스킬. 같은 시험 형식과 답안지
  목록을 싣는다
- `docs/verify/` — 런북. 시나리오와 회차 기록
- `docs/plans/` — 결보 v4 계획에 논증 원문 전부가 있다
- `docs/notion-feedback/` — 되읽기 분류 로그. 규칙이 왜 생겼는지를 문장으로 적는다
- `docs/rule-friction/`·`docs/study/`·`docs/corpus-audit/`·
  `docs/강의노트_이론_실험_매핑_정리.md` — 실험 내용의 파생 서술과 과거 제출본 감사
- `scripts/lab/report_compare.py`·`scripts/lab/specdiff.py`·
  `scripts/lab/regen_compare.py`·`scripts/lab/isolate.py` — docstring 이 대조
  기준을 적는다
- `tests/` — 승인본 결보 문장을 픽스처로 읽는 테스트가 있다
- `보고서/<실험NN>/output/` **내용물 전부** — 결과보고서 md·baseline·되읽기·
  리뷰 라운드·`notion.json`. 예비보고서 md 한 파일만 함수가 되살린다
- `보고서/<실험NN>/*결과보고서*.pdf` — 제출본 PDF. grep 은 PDF 를 못 보므로
  목록으로 막는다

남기는 것: `체크리스트/{명세,기록}.md`·`결선도/`·`실험사진/`(시트 포함)·
`실험중있었던일.md`·`강의노트/`·`.claude/데이터시트_출처.md`·
`.claude/과목정보.md`·`.claude/보고서양식.md`·`docs/schema/`·`scripts/lab/`
나머지·④ ⑤ `export-photo-sheet` 를 비롯한 다른 스킬·다른 실험 폴더. ④·⑤ 가
참조하거나 그 절차가 실물로 드는 것들이다.

## 에이전트 프롬프트

```
작업 디렉토리: <작업 디렉토리>

이 저장소에 `write-result-report` 스킬과 `review-lab-report` 스킬이 있다.
`.claude/skills/write-result-report/SKILL.md` 를 읽고 **그 문서의 절차 그대로** 다음 요청을 수행하라:

> 실험<실험번호> 결과보고서를 써라

md 를 낸 뒤 `.claude/skills/review-lab-report/SKILL.md` 를 읽고 **그 문서의 절차 그대로** `실험<실험번호> result round1` 로 검토하라. error 가 남으면 `write-result-report` 의 규칙대로 md 를 고치고 다음 라운드로 다시 검토한다. error 0 이 될 때까지 반복한다.

너에게 주어진 것은 두 스킬 문서와 이 저장소뿐이다. 다른 맥락은 없다. 한국어로 작업하고 보고한다.

금지:
- 위 작업 디렉토리 밖의 파일을 읽지도 쓰지도 마라. 예외는 `.claude/데이터시트_출처.md` 에 적힌 URL 의 데이터시트를 내려받는 것뿐이다 — 그 파일은 작업 디렉토리 안 `tmp/` 아래에 둔다.
- `python3 -m unittest discover` 나 `pytest` 를 돌리지 마라. 스킬 절차가 지정하는 표적 검증 명령만 쓴다.
- `git commit` / `git add` / `git log` / `git show` / `git diff` / `git stash` / `git checkout` / 브랜치 조작을 하지 마라. 이 작업과 무관하다. 트리 상태 확인이 필요하면 `git status --porcelain` 만 쓴다.
- 스킬 문서와 이 저장소 밖의 지식으로 관찰값·수치를 채우지 마라. 근거가 저장소 안 파일이면 그 경로를 적는다.
- 스킬 절차가 사용자에게 묻도록 한 자리에 이르면 묻지도 지어내지도 마라 — 그 절차가 정한 대로 그 자리를 비우고 아래 5항에 적는다. 단 `기록.md` 에 이미 "사용자 확인" 으로 적힌 사실은 확인된 것으로 본다.

환경: 파이썬은 작업 디렉토리에서 `<파이썬 명령> ...` 로 돌린다 — 스킬 문서의 `python3 -c` 는 `<파이썬 명령> -c` 로 읽는다. `pdftotext`·`pdftoppm`·`pdfinfo` 는 `<poppler 경로>` 에 있다. 판독 노트·렌더 PNG·내려받은 데이터시트 같은 스크래치는 작업 디렉토리 안 `tmp/` 아래에 둔다.

끝나면 아래 형식으로 보고하라. 같은 내용을 작업 디렉토리 안 `tmp/격리보고.md` 에도 저장하라.

1. 만든 파일 경로 전부 (없으면 "없음"). 어느 강의노트 판본(경로·쪽수)을 열었는지.
2. 두 스킬 문서의 마지막 절차 단계가 요구하는 안내 전부.
3. 검증 단계마다(`write-result-report` 의 검증 단계와 `review-lab-report` 의 각 라운드): **첫 실행**에서 error / warn / info 가 각각 무엇이 나왔는지 원문 그대로, 그것을 어떻게 처리했는지, 몇 번 반복했는지. **첫 실행에서 error 0 으로 한 번에 통과했으면 그렇다고 명시하라.**
4. `review-lab-report` 의 "사람이 확인할 것" 항목 각각과 처리.
5. 막혔거나 규칙이 안 맞아 스스로 판단으로 메운 자리, 사용자에게 물어야 했으나 묻지 못한 자리 (없으면 "없음"). 어느 규칙·단계였는지 번호로.
6. 두 스킬 문서에서 모호하거나 서로 어긋난다고 느낀 문장 (없으면 "없음"). 원문 인용과 함께.
7. 이번 작업에서 읽은 저장소 파일 전부. 다른 실험 폴더의 파일을 참고했으면 무엇을 어디에 썼는지.
8. 실제로 연 데이터시트 (경로·URL). 열지 못한 것과 그 이유.
```

## 비-목표

- **`write-result-report` 를 고치지 않는다. `review-lab-report` 도.** 갈린
  자리는 제안하고 멈춘다.
- **승인본을 고치지 않는다. 커밋하지 않는다.**
- **노션에 올리지 않는다.** 재생성물은 `tmp/` 에만 남는다.
- **`write-pre-report` 를 재지 않는다.** 예비보고서 검증은 별개다.
- **기록.md 비어 있음·필기 PDF 전사 같은 다른 시나리오를 돌리지 않는다.**
  무인자 재생성(V1)만이다.
````

- [ ] **Step 3: 런북을 만든다**

`docs/verify/write-result-report.md` 를 아래 내용 그대로 만든다.

```markdown
# `write-result-report` 실행 검증 런북

`write-result-report`·`review-lab-report` 는 산문 규칙 문서라 컴파일도 실행도
되지 않는다. `tests/test_skill_docs.py` 가 보는 것은 상호참조·번호 같은
**구조**뿐이고, 그 문서가 좋은 결과보고서를 만드는지는 검사하지 않는다. 그것을
보는 유일한 방법은 승인본이 있는 실험을 답안 없는 트리에서 다시 쓰게 하고
승인본과 대조하는 것이다.

**스킬 문서(`SKILL.md`)를 고치면 이 런북을 다시 돌린다.** 어느 판본으로 무엇을
돌렸는지 아래 기록 표에 남긴다.

## 시나리오

### V1 — 재생성 (무인자) + ⑤ 검토

**스킬 `verify-write-result-report` 를 돌린다** (`/verify-write-result-report <실험N>`).
격리 트리 만들기·답안지 목록·에이전트 프롬프트·판정 초안·기록 행까지 그 스킬
문서가 정본이다. 여기서는 되풀이하지 않는다 — 둘을 두면 표류한다.

스킬이 안 하는 것만 여기 적는다. **판정 기준**: 구조·표 셀·참고문헌·문체 네
갈래가 0건이고, 사실 토큰 차이를 사람이 `규칙 없음 / 검사 없음 / 환경` 으로
가른 뒤 앞 둘이 0 이면 합격이다. 산문 일치율은 기준 밖이다 — 문장이 같기를
요구하면 승인본 문장을 규칙에 베끼는 과적합으로 간다. `환경` 은 데이터시트를
못 열어 수치가 "확인 필요" 로 남은 것처럼 스킬 밖 사정이다.

**루프**: `규칙 없음`·`검사 없음` 자리마다 스킬이 ⑦ 분류 표 형식으로 규칙을
제안한다. 사용자가 승인하면 ④·⑤ 를 고쳐 커밋하고 같은 명령을 다시 돈다.
세션당 3회가 상한이다.

통제군은 승인된 결과보고서가 노션에 올라간 실험뿐이다. 2026-09-12 기준
실험01(v5).

## 기록

| 날짜 | SKILL.md 판본 | 돌린 시나리오 | 결과 |
|---|---|---|---|
```

- [ ] **Step 4: 형제 스킬의 KEYS 와 §답안지 목록에 새 스킬을 더한다**

`.claude/skills/verify-draft-lab-spec/SKILL.md` 찾을 문장:
```
       'scripts/lab/isolate.py', 'scripts/lab/contact_sheet.py',
       'scripts/lab/export_hand_diagrams.py', 'tests',
```
바꿀 문장:
```
       'scripts/lab/isolate.py', 'scripts/lab/contact_sheet.py',
       'scripts/lab/export_hand_diagrams.py', 'scripts/lab/report_compare.py',
       '.claude/skills/verify-write-result-report', 'tests',
```

같은 파일 §답안지 목록에서 찾을 문장:
```
- `tests/` — 실험01 값을 픽스처로 읽는 테스트가 열 개 넘는다
```
바꿀 문장:
```
- `scripts/lab/report_compare.py`·`.claude/skills/verify-write-result-report/` —
  결과보고서 검증 도구와 형제 스킬. 같은 시험 형식과 답안지 목록을 싣는다
- `tests/` — 실험01 값을 픽스처로 읽는 테스트가 열 개 넘는다
```

- [ ] **Step 5: ⑦ 의 재생성 대조 단계에 결보용 스킬을 가리킨다**

`.claude/skills/sync-report-to-notion/SKILL.md` 찾을 문장:
```
    일회성 수정만 있었던 라운드는 재생성하지 않는다.
```
바꿀 문장:
```
    일회성 수정만 있었던 라운드는 재생성하지 않는다. **결과보고서는
    `verify-write-result-report` 가 이 대조를 맡는다** — 답안 없는 격리 트리에서
    ④·⑤ 를 다시 돌리고 승인본과 여섯 갈래로 대조한다(2026-09-12 신설). 예비보고서는
    아직 손으로 한다.
```

- [ ] **Step 6: 테스트를 돌린다**

Run: `PYTHONPATH=. python -m pytest tests/test_skill_docs.py -q`
Expected: 전부 PASS. 자주 나는 실패와 처방: `§절대 규칙 N 없음` → 새 문서 안 참조 번호가 1~8 안인지 본다; `N단계 없음` → 다른 문서의 단계를 `④ 12단계` 처럼 썼는지 찾아 `④ §실행 절차 12` 로 고친다; `test_the_verifier_answer_keys_agree_in_all_three_places` 의 `other_skills` 개수 → Step 1 의 `"/verify-" not in k` 수정이 들어갔는지 본다.

- [ ] **Step 7: 커밋한다**

```bash
git add ".claude/skills/verify-write-result-report/SKILL.md" \
        ".claude/skills/verify-draft-lab-spec/SKILL.md" \
        ".claude/skills/sync-report-to-notion/SKILL.md" \
        docs/verify/write-result-report.md tests/test_skill_docs.py
git commit -m "$(cat <<'EOF'
feat(skills): verify-write-result-report — 결과보고서 스킬 격리 재생성 검증 스킬과 런북 신설

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
EOF
)"
```

---

### Task 8: 첫 회차를 돌린다 (`/verify-write-result-report 실험1`)

**Files:**
- Create(gitignore): `tmp/verify-artifacts/실험01-결보격리-<YYYY-MM-DD>/` (재생성 md·리뷰 라운드·격리보고.md·판정.md)
- Modify: `docs/verify/write-result-report.md` (`## 기록` 표 한 행)

**Interfaces:**
- Consumes: Task 7 의 스킬 문서 전부. 이 Task 는 그 문서를 글자 그대로 따르는 것이 전부다 — 아래는 이 PC 에서 채울 값과 확인 지점만 적는다.
- Produces: 판정.md, 런북 기록 행, 사용자에게 보낼 규칙 제안 표.

- [ ] **Step 1: 환경 값을 확인한다**

Run:
```bash
where python | head -1
where pdftoppm | head -1
PYTHONPATH=. python -c "import pypdf; print('pypdf', pypdf.__version__)"
git status --porcelain .claude/skills scripts/lab 보고서/실험01
```
Expected: `E:\Python\python.exe`, WinGet poppler 경로, pypdf 판본 한 줄, 그리고 `git status` 출력이 비어 있다. `pypdf` 가 없으면 ⑤ 3단계가 죽으므로 사용자에게 알리고 멈춘다.

- [ ] **Step 2: 스킬 0~3단계를 돌린다**

스킬 문서 §실행 절차 0~3 의 명령을 `<실험번호>`=`1`, `<실험NN>`=`실험01` 로 채워 순서대로 돌린다(`python3` 는 `PYTHONPATH=. python` 으로). 0단계 기대: 세 줄 `O`, `원본↔baseline 산문 밖 차이 0 건`. 1단계 기대: `C:\Users\Hyunjun\AppData\Local\Temp\iso-실험01`. 2단계 기대: 출력 줄의 파일이 `.claude/skills/write-result-report/SKILL.md` 와 `보고서/실험01/체크리스트/기록.md` 뿐이다 — 다른 파일이 나오면 그 경로를 §답안지 목록과 KEYS 에 더하고(Task 7 Step 2 의 두 곳 + `test_the_result_verifier_lists_itself...` 가 요구하는 표기) 커밋한 뒤 1단계부터 다시 한다. 3단계 기대: `self 0`.

- [ ] **Step 3: 격리 트리에 입력물이 남았는지 눈으로 확인한다**

Run:
```bash
ISO="/c/Users/Hyunjun/AppData/Local/Temp/iso-실험01/보고서/실험01"
ls "$ISO/체크리스트" "$ISO/output" "$ISO/실험사진/시트"; ls "$ISO" | grep -c 결과보고서
```
Expected: 체크리스트에 `기록.md 명세.md 체크리스트.html 체크리스트.pdf`, output 에 `실험01_예비보고서.md` 하나, 시트 5장, 마지막 줄 `0`.

- [ ] **Step 4: 에이전트를 띄운다**

Agent 도구로 `subagent_type: general-purpose`, `run_in_background: true`. 프롬프트는 스킬 §에이전트 프롬프트를 글자 그대로 복사하고 다음만 채운다: `<작업 디렉토리>` = `C:\Users\Hyunjun\AppData\Local\Temp\iso-실험01`, `<실험번호>` = `1`, `<파이썬 명령>` = `PYTHONPATH=. python`(Git Bash) 또는 `$env:PYTHONPATH='.'; python`(PowerShell) 중 에이전트가 쓰는 셸에 맞는 것 — 둘 다 적어 준다, `<poppler 경로>` = Step 1 의 WinGet 경로. 기다리는 동안 격리 트리와 승인본은 건드리지 않는다.

- [ ] **Step 5: 산출물을 보존하고 판정 초안을 낸다**

Run(에이전트가 끝난 뒤, 날짜는 실제 값):
```bash
D="tmp/verify-artifacts/실험01-결보격리-$(date +%F)"
mkdir -p "$D"
cp -r "/c/Users/Hyunjun/AppData/Local/Temp/iso-실험01/보고서/실험01/output" "$D/"
cp "/c/Users/Hyunjun/AppData/Local/Temp/iso-실험01/tmp/격리보고.md" "$D/" 2>/dev/null || echo "격리보고.md 없음 — 에이전트 보고 원문을 $D/격리보고.md 로 직접 저장한다"
ls "$D/output"
```
Expected: `실험01_결과보고서.md` 와 `result_review_round1.md`(이상)가 있다. 없으면 에이전트 보고 1항을 보고 어디서 멈췄는지 판정.md 8절에 적는다 — 그것도 결과다.

그 다음 스킬 6단계 명령을 돌린다(`<2단계 출력 줄 목록>` 은 Step 2 의 2단계 출력을 파이썬 리스트 리터럴로).

- [ ] **Step 6: 사람이 보고 판정을 적는다**

판정.md 5절의 사실 토큰 줄마다 세 칸 중 하나에 `x` 를 넣는다. 기준: 에이전트 보고 8항에서 데이터시트를 못 열었다고 했고 그 수치가 갈렸으면 `환경`; 에이전트 보고 3항의 ⑤ 첫 실행 warn/error 에 그 자리가 잡혀 있으면 `검사 없음` 이 아니라 규칙 자리를 본다(잡았는데도 남았으면 ④ 규칙 문장이 약한 것 = `규칙 없음`); 어디에도 안 잡혔으면 `검사 없음` 과 `규칙 없음` 둘 다 후보이고, ④ 문서에 그 자리를 다루는 문장이 있는지 grep 해 있으면 `검사 없음`, 없으면 `규칙 없음`. 6절 산문은 절마다 원본과 나란히 읽어 사실이 다른 문장만 5절 형식으로 8절에 옮긴다. 8절 "## 8. 판정" 을 스킬 7단계 형식으로 적는다.

- [ ] **Step 7: 런북 기록 행을 붙이고 커밋한다**

`docs/verify/write-result-report.md` 의 `## 기록` 표 헤더 구분선 아래에 스킬 8단계 형식의 행 한 줄을 붙인다(판본은 `git rev-parse --short HEAD`, 요약은 8절 판정의 첫 문장).

```bash
git add docs/verify/write-result-report.md
git commit -m "$(cat <<'EOF'
docs(verify): write-result-report 런북 — 실험01 결보 격리 재생성 1회차 기록

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 8: 사용자에게 보고하고 멈춘다**

스킬 9단계 형식으로 네 가지를 낸다. `규칙 없음`·`검사 없음` 자리마다 아래 표 형식으로 제안한다.

```markdown
| # | 무엇이 갈렸나 | 분류 | 제안 반영 대상 |
|---|---|---|---|
| 1 | … | 규칙 없음 | ④ §절대 규칙 N 에 "…" 한 문장 |
```

여기서 이 계획은 끝난다. 사용자가 제안을 승인하면 ④·⑤ 수정 → `tests/test_skill_docs.py` 통과 확인 → 커밋 → `/verify-write-result-report 실험1` 재실행(2회차)이며, 세션당 3회가 상한이다. 격리 트리는 `rm -rf /c/Users/Hyunjun/AppData/Local/Temp/iso-실험01` 로 지운다.

---

## Self-Review

- **Spec coverage:** 결정 #1(통제군=원본 md, baseline 은 자기대조) → Task 5 테스트 + 스킬 0·3단계; #2·#3(격리 일반화·입력물 보존) → Task 4 + 스킬 1단계 `clear_subdirs`/`keep`; #4(문장 누출) → Task 4 `leak_sentences` + 스킬 2단계; #5(6갈래·합격 기준) → Task 5·6 + 런북 판정 기준; #6(④ 뒤 ⑤) → 프롬프트 둘째 문단; #7(질문 자리·기록.md 확인) → 프롬프트 금지 마지막 줄; #8(환경 줄 자리표시자) → 프롬프트 환경 줄 + Task 8 Step 4; #9(고치지 않고 제안) → 절대 규칙 6·9단계·비-목표; #10(④18·③21) → Task 2; #11(런북) → Task 7 Step 3; #12(round2 로그) → Task 2 Step 6; #13(선행 커밋) → Task 1; #14(check_body_style warn) → Task 3; #15(NAND 문장 체계적) → Task 2 Step 4; #16(3회 상한) → 절대 규칙 8 + 런북; #17(데이터시트 URL 만) → 프롬프트 금지 첫 줄. 구조적 누출 → 절대 규칙 2 + 판정 7절.
- **Placeholder scan:** 코드 단계는 전부 본문이 있다. 스킬 문서의 `<실험번호>`·`<작업 디렉토리>`·`<파이썬 명령>`·`<poppler 경로>`·`<2단계 출력 줄 목록>` 은 실행 시 채우는 자리표시자이고 Task 8 이 이 PC 의 값을 적었다. Task 5 Step 4 와 Task 7 Step 6 의 "실패하면" 처방은 구체 조치다.
- **Type consistency:** `build_isolated_tree(root, dest, experiment, answer_keys, clear_subdirs, keep)` 이 Task 4·7(스킬 1단계) 에서 같다. `leak_sentences(approved_md, tree)`·`leak_scan(dest, tokens)` 가 Task 4·7(2단계) 에서 같다. `compare_reports`·`counted`·`judgment_markdown(experiment, regen_md, leak_hits, agent_report)`·`approved_report_path` 가 Task 5·6·7 에서 같다. `validate.check_body_style(md_text)` 가 Task 3·5·7 에서 같다. 새 문서 키 `"결보검증"` 이 Task 7 Step 1 의 세 테스트에서 같다. ④ 규칙 번호 18, ③ 규칙 번호 21 이 Task 2·3·7 에서 같다.
