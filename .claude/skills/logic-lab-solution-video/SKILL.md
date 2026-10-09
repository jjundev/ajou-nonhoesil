---
name: logic-lab-solution-video
description: 논리회로실험 복습팩의 기출문제·기출풀이 PDF 원본 화면을 사용하고 중앙 풀이를 한 글자씩 공개하는 한국어 문제풀이 영상을 만든다. 실험 번호·문항 ID·라벨·재개·대본 검토 요청 또는 /logic-lab-solution-video 에 사용한다. 복습팩 자체 생성은 logic-lab-review-pack 을 사용한다.
---

# PDF 문제풀이 영상

문제지로 조건과 구할 것을 확인한 뒤, 중앙 풀이를 숨긴 답안 페이지의 **원래 위치**에서 풀이를 한 글자씩 공개한다. 답안의 문장·기호·수치·줄바꿈·순서를 그대로 유지한다. PDF 원본의 글자 윤곽을 사용하며 HTML/KaTeX로 다시 쓰지 않는다. 완성 화면은 원본 답안과 같아야 한다.

## 호출과 기본값

- `/ec2-solution-video 1002`: 해당 날짜 모든 문항, 문제별 MP4.
- `/ec2-solution-video 1002 --problems E10.11,P10.62`: 선택한 문항.
- `/ec2-solution-video 0923-1002 --review`: 범위 문항의 대본을 묶어 한 번 사용자 검토.
- `/ec2-solution-video 1002 --writing-mode typing`: 기존 타이핑 방식 선택. 신규 실행은 pencil이 기본이다.
- 재개 요청: 이전 batch의 `resume-set`으로 처음 무효인 단계를 확인한다.

한국어 Aoede / Vertex AI Express / gemini-2.5-flash-tts, 1920×1080/30fps, mono PCM 24kHz. 연필 작성 기본 초당 7.5글자(사용자 요청으로 기존 5글자에서 1.5배), 음성이 짧으면 작성 시간을 늘린다. 배경음·필기·타이핑 소리는 없음. 예산 상한 없음이며 요청 전체 사용량을 공용 ledger에 기록한다. 공급자·모델을 자동 대체하지 않는다.

연필 PNG 한 장을 촉 중심으로 움직이며 원본 윤곽을 왼쪽에서 오른쪽으로 공개한다. 실제 한글·수식 획순을 복원하는 연출은 아니다. 연필 길이는 촉부터 지우개 끝까지 화면상 160px이며 확대와 무관하다. 줄바꿈에서는 들어 옮기고 작성 완료·설명·최종 hold에서는 숨긴다. pencil은 PageMap의 writing_units에 저작한 줄·가로 영역 순서로 공개한다. 첨자·위첨자는 같은 영역 안에서 위아래로 처리하고 긴 분수선·근호선은 clip을 누적한다. 원문 glyph_ids 순서는 보존한다. typing은 기존 anchor 공개를 유지한다.

PDF 흰 화면과 회로·격자·조건·Hint를 보존한다. 기본 복습문제는 하단 180px를 비운 16:9 PDF다. PDF 전체를 1920×1080에 맞춘 뒤 예약 영역만 자막으로 덮는다. 1920×900에 다시 축소하지 않는다. 기존 A4 입력은 원본 비율을 유지해 호환한다. 새 PDF는 약 11.34pt 본문과 같은 비율로 조정한 제목·수식·힌트를 사용해 기존 A4 전체 화면의 텍스트 표시 크기를 유지한다. 영상에서 추가 글꼴 재조판 없이 그 PDF의 글자를 그대로 공개한다. 작성 중 작은 글자는 원래 배치 그대로 확대한다. 회로에서 돌아올 때 다음 줄 전체와 실제 연필 여백을 fit하고, 해당 구간 작성 중 구도를 고정한다. 26px에서도 안 들어오는 줄은 의미 경계의 chunk를 명시하며 12프레임 카메라 이동을 마친 뒤 작성한다. 입력 문제지와 답안의 회로도 크기/페이지 번호를 독립적으로 확인한다. 긴 2단 풀이의 단계 순서를 사람이 검토한다.

## 실행

이 프로젝트에서 PyMuPDF와 Pillow가 있는 Python, Node, 로컬 GSAP/HyperFrames/puppeteer-core/Chrome, libass 포함 FFmpeg를 사용한다. 없는 패키지를 자동 전역 설치하지 않는다. `EC2_PUPPETEER_CORE_PACKAGE`는 package.json 절대 경로, `EC2_CHROME`, `EC2_FFMPEG`는 실행 파일 절대 경로로 지정할 수 있다. 현재 환경의 설치 경로는 매 실행 확인한다. Node CLI가 없으면 렌더를 검증 완료로 보고하지 않는다.

1. `python3 .agents/skills/ec2-solution-video/scripts/video.py prepare 1002 --repo "$PWD" [--problems ID,ID] [--review] [--writing-mode pencil|typing]`. 반환된 batch와 문항별 run을 사용한다. 원자료를 동결하며 비용은 0이다.
2. [PDF와 내용 대응](references/pdf-and-coverage.md)을 읽는다. 실제 문제/답안 PDF, 동결 workbook MD, 후보 SVG와 native PNG를 읽고 `source/map.json`을 작성한다. `extract --run RUN`으로 빈/부분/완성 프레임 게이트를 실행한다. native PDF와 원본 SVG도 직접 대조한다. 픽셀 비교 0만으로 의미 검토를 승인하지 않는다.
3. 원문과 일치하는 `manifest.json`, `coverage.json`, `circuit-review.json`을 작성하고 `check --run RUN`으로 검증한다. 상단 회로·표를 설명할 때 이 대본 저작 단계에서 선택적으로 focus.json과 annotations.json도 작성한다([PDF와 내용 대응](references/pdf-and-coverage.md)). 의미에 맞는 reason/check cue에 회로 확대·화살표/타원/밑줄/짧은 label을 연결하고, TTS 전에 check로 검증한다. 원본 풀이와 한 연필을 공유하고 최종 전체 화면에서 주석을 숨긴다. 한글 음절/조판 기호를 공개하며 첨자·분수선·근호선·답 상자를 누락하지 않는다. PDF/MD 충돌, 풀이 이미지, 해석할 수 없는 클립/도형은 해당 문항을 중단한다. 새 풀이·계산을 창작하거나 오류를 조용히 수정하지 않는다.
4. [음성과 실측 타이밍](references/narration-and-timing.md)을 읽는다. `tts --run RUN [--config JSON] [--env-file ENV]`를 실행한다. 최초 SVG 게이트와 현재 내용 검토 전에는 유료 요청을 하지 않는다. `--review`이면 전체 대본을 사용자에게 보여 주고 승인 후 한 번 `--approve-review`를 사용한다. 기본 모드에는 사용자 승인 단계를 추가하지 않는다.
5. `assemble --run RUN --runtime /ABS/gsap.min.js`, `render --run RUN --hyperframes-entry /ABS/hyperframes/dist/cli.js`, `captions --run RUN`을 차례로 실행한다. 모든 공개 상태가 임의 seek에도 같아야 하며 끝난 후 연필·커서를 숨긴다. 완성 오류를 마지막 원본 이미지 교체로 감추지 않는다.
6. [최종 검증과 게시](references/verification.md)를 읽는다. 최종 하드 자막 MP4의 재생·음성·가독성을 직접 검토하고 현재 증거 해시를 가진 audio/visual review를 작성한다. `verify --run RUN --hyperframes-entry /ABS/.../cli.js`를 통과한 문항만 `publish-set --batch BATCH`로 게시한다. 일부 실패 시 성공 결과/음성은 보존하고 전체 latest를 바꾸지 않는다.

작성 속도만 바꾸려면 `retime --run RUN [--writing-config JSON]`을 사용한다. 새 pencil의 check/tts/retime은 writing_units 누락을 거부한다. 현재 내용 검증과 저장 WAV의 형식·해시를 확인하고 유료 음성 호출 없이 timeline을 다시 만든다. 이후 assemble/render/captions/verify를 재실행한다. `source/writing.json`이 없는 이전 실행은 기존 타이핑 설정으로 읽는다. PNG·metadata·촉 좌표가 누락되거나 손상되면 실패하며 타이핑으로 자동 전환하지 않는다.

모든 단계 명령은 위 `scripts/video.py`에 붙인다. JSON status가 author-required이면 필요한 원문 검토 파일을 작성한다. awaiting-review는 사용자 대본 승인 대기다. failed이면 명시된 단계의 증거를 읽고 원인을 수정한다. `resume-set --batch BATCH`는 캐시 파일을 삭제하지 않는다. 단계를 건너뛰어 오래된 음성/영상과 새 대본을 섞지 않는다.

## 출력

`문제풀이영상/<날짜 또는 범위>/<문항 ID — 자연스러운 한국어 제목>.mp4`에 최종 하드 자막본만 둔다. `_자막` 접미사를 쓰지 않는다. 소스·대본·SVG·HTML·WAV·마스터·자막·검증·사용량은 같은 날짜의 `<범위>_제작자료/실행/<실행ID>/videos/<안전한 키>/`에 둔다. 같은 제목의 이전 결과는 제작자료 안에 보존한다. catalog/README는 실제 최종 파일 SHA256을 기록하고 latest는 전체 성공일 때만 갱신한다.

기존 ec2-review-video·노트·PDF·영상을 수정하지 않는다. 그 스킬의 TTS/cache/budget만 이름이 격리된 adapter로 사용한다. 다크 전용 렌더/자막 검사는 사용하지 않는다. 스캔 완전 자동 처리, 손글씨, 실제 키보드 녹화, 음성만 교체하는 별도 기능은 제공하지 않는다. 전달 시 검증한 범위와 실제 음성 미검증 여부를 구분한다.

## 회로 근거와 필기 음성 저작

신규 교육 흐름은 `source/lesson.json`(schema_version=1)에 PageMap 순서의 steps를 작성한다. 각 row는 step_id, mode, reason_segment_ids, check_segment_ids, region_ids, annotation_ids, meaning_notes, source_refs를 가진다. circuit 단계는 관련 회로 reason과 표시가 각각 필요하며 식을 쓰기 전에 회로 연결/가정을 설명한다. calculation 단계는 회로 목록을 비우고 exemption_reason에 제목·기존 근거의 후속 정리 등 이유를 명시한다. 단순 제목이나 계산마다 왕복하지 않는다. 기존 lesson 없는 run은 재개 가능하다.

핵심 논리마다 회로 근거 → 해당 내용 필기를 배치하고 필요한 경우 check로 돌아온다. 필기 text에는 지금 쓰는 문장/식의 읽기와 기호·항의 의미를 넣는다. 긴 원고 하나를 붙이지 말고 PageMap을 의미 단위로 분할하며 glyph/shape 중복·누락을 막는다. 필기 기본 7.5 chars/sec를 유지하고 영상 길이는 이해 우선으로 늘린다.

guided manifest의 모든 segment에 음성 `text`와 표시 `caption_text`를 별도로 작성한다. ‘알 오 원’은 음성으로 읽고 자막에는 `r_O1`을 쓴다. `r_O3`, `g_m1`, `V_BE`, `R₁`, `Q₁`, `∥` 등의 기호와 원문 대소문자를 보존하며 LaTeX 원문을 자막에 출력하지 않는다. caption_text가 없는 기존 run만 text로 fallback한다. 기호 토큰을 줄 중간에서 자르지 않으며 34자를 넘는 단일 토큰은 저작 오류다. 자막만 변경해도 후속 결과를 갱신하되 동일 text의 WAV는 TTS cache로 재사용한다.

현재 입력에 대한 lesson_flow는 회로 근거의 순서/안정 화면/표시 가시성을 검사한다. 의미 검토에서는 원문 회로, 실제 표시, 음성, 기호 자막을 함께 대조한다. 필기 음성의 2초 초과 무음은 narration_pacing 검토 대상이고 70–85% 밀도는 저작 가이드다. 카메라/픽셀 검사 통과나 synthetic PCM으로 교육 품질과 실제 음성을 승인하지 않는다.

### 문장·쉼표 자막 경계
문장 종료 온점에서 자막을 교체하고 서로 다른 문장을 한 cue에 합치지 않는다. 수식·괄호 밖 쉼표에서도 교체하며 쉼표는 앞 cue에 남긴다. 화면 내 줄바꿈은 교체와 별개이며 cue당 최대 두 줄, 줄당 34자다. 공백을 우선해 줄을 나누고 기호·첨자는 보존한다. 숫자 내부 점/쉼표, 식별자 점, 괄호/인용 내부 구두점은 보호하고 완결된 인용 문장의 닫는 따옴표는 문장과 함께 표시한다.
마지막 온점이 없는 기존 text는 표시용 온점만 추가하며 저장 원고와 음성은 바꾸지 않는다. ?, !, … 종결 및 불균형 괄호/LaTeX 원문은 저작 오류다. 두 줄에 들어가지 않는 구절과 34자 초과 원자 토큰은 check/tts 전에 segment id와 문제 구절로 알린다. 작성자가 의미상 쉼표 경계 또는 간결한 표기를 지정한다.
SRT 시간은 실측 voice_samples 안에서 원문 의미 단위의 글자 수 비율로 배분한다. 줄바꿈과 표시용 추가 온점은 시간 가중치에 넣지 않는다. cue 사이 임의 공백은 추가하지 않으며 실제 문장·쉼표 발화 시점과의 정밀 정렬은 제공하지 않는다. 자막만 바꾸어도 기존 final/SRT 검증은 다시 수행하고 같은 음성 WAV는 cache로 재사용한다. 두 줄 자막은 실제 libass 화면에서 하단 900..1080 영역과 기호 보존을 확인한다.

두 줄 자막 배경은 libass BorderStyle4/Outline0/Shadow4로 cue 전체에 하나의 균일한 박스를 그린다. 줄별 박스를 겹치는 BorderStyle3은 사용하지 않는다. 실제 두 줄·서로 다른 줄 길이에서 박스 가장자리와 불투명도 균일성 및 기호·글자 가독성을 확인한다.

### 숫자·연산의 자막 표기
음성 `text`는 자연스러운 한국어 발음을 쓰고, `caption_text`는 수학적 수치·연산을 숫자와 기호로 직접 저작한다. 예: `더하기 → +`, `빼기/음수 → −`, `곱하기 → ×`, `나누기 → /`, `이 ΔI → 2ΔI`, `이분의 삼 → 3/2`, `일 점 오 → 1.5`, `영 → 0`, 문항 `에이/비 → (a)/(b)`. 분수의 괄호와 부호를 원본에 맞춰 `R_L × ((I₀ + ΔI)/2 − (I₀ − ΔI))`처럼 보존한다. 기호를 단순 연결해 연산 우선순위를 바꾸지 않는다.
`이 두 항`, `이 회로`, `더해집니다` 등 설명 문장은 문맥대로 유지한다. 한글 숫자 전체 치환은 금지한다. 자연어 문맥만으로 불명확한 숫자는 원본 PDF/MD와 대조하고 표시용 문장 전체를 저작한다. `caption_text`의 명시적 연산어와 한글 분수·소수는 error로 차단한다. 기호 앞 한글 수사(`이 ΔI`, `이 R_L`), 한글 수사로 나눈 표현, `값은/계수는/답은/전류는/전압은 이입니다` 같은 수치 서술은 warning으로 알리고 진행한다. `I₀이` 같은 조사와 `이 회로`, `이 두 항` 같은 일반 지시어는 유지한다. 경고는 숫자 판정이 아니며 원본과 문맥 대조가 필요하다. 자동 치환하지 않는다. 모든 발견을 severity/code/segment_id/span/matched_text/reason으로 수집하고 check/tts/captions 결과와 verify 보고서에 warnings로 전달한다. TTS 경고는 유료 요청 전에 stderr로 출력한다. 경고 자체로 완료를 막거나 사용자 승인 단계를 추가하지 않으며 기존 최종 의미 검토에서 경고도 대조한다. 이 검사는 완전한 한국어 해석기가 아니므로 미탐 가능 표현은 내용 검토에서 확인한다. `caption_text` 없는 legacy fallback은 유지한다.
자막을 수정하면 WAV와 음성 `text` 해시를 보존하고, 현재 검토 지문·타임라인·자막·최종 MP4·검증을 갱신한다. 동일 음성은 캐시를 재사용하며 유료 재합성을 하지 않는다. 기호·첨자·분수·괄호, 문장/쉼표 경계, 두 줄 제한 및 실제 하단 박스를 확인한다.
