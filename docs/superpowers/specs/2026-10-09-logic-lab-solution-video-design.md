# 논회실 기출 풀이영상 스킬 (`logic-lab-solution-video`) 설계

2026-10-09. 전자회로2 `ec2-solution-video`(커밋 `af86ffbc1004ca1e1f08c0c9125f3dc8272a8409`)를 논회실로 포크한다.

## 의도

`복습노트/실험NN/실험NN_기출문제.pdf`·`실험NN_기출풀이.pdf` 쌍에서 문항마다 한국어 풀이영상 MP4 를 만든다.
문제지 쪽으로 조건·구할 것을 보이고, 답안 쪽에서 가려 둔 가운데 풀이를 연필이 원래 위치에 한 글자씩 공개한다(Aoede 음성 + 하드 자막).
`/logic-lab-solution-video 실험05` 로 `문제풀이영상/실험05/` 에 검증 통과 문항별 MP4 가 놓이면 완료다.

분류: 아키텍처형 — 논회실에 영상 하위 시스템(TTS·HyperFrames 렌더·자막·게시)이 없다.

## 접근: 포크 (A)

엔진 전체를 `.claude/skills/logic-lab-solution-video/` 로 복사하고 `upstream.json` 에 상류 커밋·파일 해시·논회실 변경 목록을 남긴다.
상류 구조(`scripts/video.py`, `scripts/solution_video/`, `assets/`, `references/`, `tests/`)를 유지해 diff 로 다시 맞출 수 있게 한다.
형제 스킬 `ec2-review-video` 의존은 전부 스킬 안으로 가져온다: `scripts/lib/{__init__,cache,budget,vertex_tts}.py` → `scripts/tts_lib/`, `assets/fonts/Pretendard-Bold.ttf`(+SOURCE.md), `assets/runtime/vendor/gsap.min.js`(+GSAP-README.md) → `assets/runtime/`.
`.agents/skills/logic-lab-solution-video` 는 `.claude/skills/...` 를 가리키는 심볼릭 링크(기존 관례).

## 논회실 차이 (이 다섯 가지만 상류와 다르다)

1. **소스 탐색.** 선택자 `실험NN`·`NN`·`NN-MM`·`실험NN-MM`. `복습노트/실험NN/manifest.json` 의 `problems` 중 `status=='included'` 를 순서대로 읽어 n번째 문항의 표시 라벨을 `KINDS[kind]+str(n)` 으로 만든다(`KINDS` 는 `scripts/lab/review_pack/workbook_content.py:13` 과 같은 값). 문제지·답안 PDF 에서 머리말 배지(클립 x 0–140 의 첫 줄)가 라벨과 같고 머리말 전체에 `title` 이 들어 있는 쪽을 짝짓는다. MD 스냅샷은 `실험NN_기출풀이.md`. `--problems` 는 내부 ID(`q-prio-exam`)와 라벨(`기출3`)을 모두 받는다. 문항의 풀이 그림 참조는 `figures/solutions/<id>-solution-NN.png`.
2. **입력 게이트(유료 호출 전).** 원문 LaTeX(`raw_latex`)가 찍힌 쪽, 풀이 영역 그림이 '답' 상자 상단 아래로 내려간 쪽(`clipped_figure`)은 그 문항만 failed 로 남기고 나머지를 계속한다. 2026-10-09 실측: 실험02 전 쪽 raw_latex, 실험02·03·04·05 의 13쪽 clipped_figure.
3. **그림 단위.** 답안 쪽 이미지 중 디코딩 픽셀이 그 문항의 `figures/solutions/*.png` 와 같은 것(실측: 평균 차 0)을 `kind:'figure'` 도형으로 승격한다. 그러면 상류의 writing unit band clip 이 그대로 왼→오 wipe 가 된다. figure 조각의 작성 시간은 60프레임(2초) 고정이고 음성이 길면 세그먼트가 음성을 따른다(상류 규칙). figure 는 글자가 있는 단계(예: '완성 회로' 제목)와 같은 step 에 둔다. 26px 기준으로 화면에 안 들어오는 figure 묶음은 들어가는 최대 배율로 맞춘다. 대응 PNG 가 없는 풀이 영역 이미지는 상류대로 중단한다. 문제 그림·점 격자 배경은 대상이 아니다.
4. **논리식 음성·자막.** 자막은 원문 기호(`S1′S0′D`, `+`, `V_CC`, `74HC138`), 음성은 읽는 소리("에스원 바 …"). `defaults.json` 의 `pronunciation`·`direction` 을 논리회로용으로 바꾸고, 자막에 "신호 이름 + 바/낫" 이 보이면 `logic_bar_word` 경고를 낸다.
5. **출력.** `문제풀이영상/<실험NN>/<라벨> — <제목>.mp4`, 제작자료 `문제풀이영상/<실험NN>/<실험NN>_제작자료/실행/<실행ID>/`. catalog 에 내부 ID 도 남는다. 환경변수 이름은 `LOGIC_LAB_CHROME`·`LOGIC_LAB_FFMPEG`·`LOGIC_LAB_<PKG>_PACKAGE`.

나머지(단계·상태·검증·게시 계약, lesson/focus/annotations 스키마, 자막 경계 규칙, Aoede/gemini-2.5-flash-tts/1920×1080/30fps/24kHz, 연필 7.5자/초)는 상류 그대로다. lesson 의 `circuit` 모드는 논회실에서 "문제 그림(회로도·진리표·파형) 근거 단계" 를 뜻한다.
PDF 판형은 A4 가로 그대로(상류 legacy 프로파일: 머리말 하단 59pt, 조건 패널 (22,59,286,572) 실측 일치).

## 확정 결정

| # | 결정 | 값 |
|---|---|---|
| 9 | 상류 스냅샷 | `af86ffbc1004ca1e1f08c0c9125f3dc8272a8409` (2026-10-09 clean 확인) |
| 10 | 풀이 그림 | 연필 wipe |
| 11 | git | 최종 MP4·catalog/README·`source/`·`layers/*.json`(svg·png 는 무시)·`usage.json`·WAV 커밋. `renders/`·`verification/`·`composition/`·`caption-original/` 는 무시 |
| 12 | 첫 실측 | 실험05 |

## 하지 않는 것

복습팩 PDF 결함 수정(별도 작업), 16:9 영상용 PDF, 개념 복습 영상, 전자회로2 수정·자동 상류 동기화.
