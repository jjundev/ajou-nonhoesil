# 음성과 작성 타이밍

음성 설정은 assets/defaults.json, 작성 설정은 assets/writing-defaults.json이며 각각 source/config.json과 source/writing.json에 동결한다. Aoede/한국어/24kHz mono PCM, 1920×1080/30fps이며 모델과 공급자를 자동 대체하지 않는다. 환경 GOOGLE_API_KEY 또는 GEMINI_API_KEY를 사용한다. --env-file은 메모리로만 읽고 config/로그에 키를 넣지 않는다. budget_usd=null은 상한 없음이며 명시 상한을 주면 price 요율과 기존 예산 규칙을 따른다. 모든 문항은 batch/usage.json 하나를 쓴다.

문제를 확인하는 발화로 시작한다. 판단 이유(reason), 원문을 쓰는 동안의 설명(write), 계산 확인(check), 답 확인(summary)을 원자료에 연결한다. PDF에 없는 새 계산이나 풀이를 만들지 않는다. 한 발화가 길면 PageMap 단계도 작은 연속 단위로 나눈다. 실패한 문항만 재개하고 성공 WAV는 내용/설정 해시로 재사용한다.

연필 기본은 7.5글자/초이며 인접 글자마다 이동 1프레임 + 작성 3프레임이다. 사용자 요청에 따라 이전 5글자/초(이동 1+작성 5프레임)보다 1.5배 빠르다. 긴 이동·줄바꿈·단계 이동은 최소 8프레임 이동을 사용하고 작성 시간을 줄이지 않는다. write 구간은 max(실제 WAV 길이, 모든 이동·작성 길이)+ceil(0.75×30)=23프레임이다. typing 선택은 기존 ceil(30/7) 프레임 간격을 사용한다. 작성 파일이 없는 legacy 실행은 기존 config의 속도/hold를 그대로 쓴다. 공백은 이동 시간만 사용하며 연필은 숨긴다. typing의 shape는 같은 단계의 anchor glyph 완료 시점에 공개한다. pencil은 writing_units의 shape piece를 최소 18프레임씩 작성하며, 폭 0인 세로 선은 위에서 아래로 공개한다. 전체 타이밍은 800샘플=1프레임이며 실제 PCM은 자르거나 늘이지 않고 남는 구간을 무음으로 채운다. 마지막은 최소 1초 전체 답안 확인이다. 단어별 실제 음성 정렬을 주장하지 않는다.

writing.json의 키: schema_version=1, mode=pencil|typing, chars_per_second=7.5(typing 기본 7), pencil_length_px=160, adjacent_move_frames=1, lifted_move_frames=8, tilt_degrees=2, read_hold_seconds=0.75, asset_id=pencil-yellow-v1. 명시 설정의 속도는 유한 수 pencil은 0<값<=7.5, typing은 0<값<=7, 길이는 양의 유한 수, 이동은 양의 정수, 기울기는 0~2°, hold는 0 이상의 유한 수다. 잘못된 값·알 수 없는 키/모드/asset은 실패한다.

`retime --run RUN --writing-config /ABS/writing.json`은 현재 내용 게이트와 voice 선행 단계, 모든 WAV의 샘플 수·mono·16-bit·24kHz·SHA256을 확인하고 저장 음성만 재배치한다. 공급자·usage ledger·음성 승인·WAV를 수정하지 않으며 paid_requests=0이다. 검증 실패 시 기존 timeline을 덮어쓰지 않는다. 성공 후 assemble부터 다시 실행한다.

연필 asset은 assets/pencil/pencil-yellow-v1.png 및 JSON이다. JSON의 tip_px/end_px로 촉 중심 회전과 화면 길이를 계산한다. PNG 형식·RGBA alpha·해시·좌표를 검사하고 composition에 복사한다. 실제 획순 데이터 없이 원본 SVG를 점진 공개하므로 획순 필기로 설명하지 않는다. 효과음은 추가하지 않는다.

개발 테스트는 fake transport와 로컬 PCM만 사용한다. 실제 Aoede 품질/발음/의미는 최종 파일을 청취하여 별도 현재 audio-review로 확인한다. fake PCM의 기술 검사로 실제 음성 의미 검토를 통과 처리하지 않는다.

## 회로 설명의 타이밍

설명 의미에 따라 focus cue를 지정한다. 회로로 12프레임 동안 이동 → 연필 진입 8프레임 → 표시 작성 → 최소 30프레임 확인 → 풀이로 12프레임 복귀한다. 도형 작성 기본 18프레임이며 더 짧은 명시는 오류다. label은 글자당 이동 1+공개 5프레임, 공백은 연필 없이 6프레임이다. offset_frames는 segment 상대 연필 이동 시작이며 기본 첫 12, 이후 앞 주석 완료 직후다. 겹치는 주석은 거부한다. 카메라 이동 중 필기하지 않는다.

음성은 segment 시작에서 재생한다. 짧은 WAV 뒤에만 무음을 추가하고 이후 WAV·원본 공개·writing spans·자막을 같은 프레임만큼 이동한다. 자막은 실측 voice_samples 길이만 사용한다. 단어별 음성 동기화는 제공하지 않는다. source/focus.json 또는 annotations.json을 바꾼 뒤 기존 `retime --run RUN`으로 다시 계산하며 유료 TTS를 호출하지 않는다. 설명 대본 자체를 바꾸면 기존 내용/음성 검토를 다시 거친다.

좌표·색·글꼴 크기만 변경하면 composition부터 재개한다. cue·길이·offset·문자 공개 단위·hide 또는 파일 추가/삭제는 timing부터다. WAV 캐시는 유지한다. assemble은 저장 timeline의 timing_hash와 현재 연출을 대조하고 오래된 타이밍이면 retime을 요구한다.

## Writing narration pacing

Explain the reason, meaning of each term, and connection to the circuit while
writing. Split PageMap steps for smaller write segments; preserve original PDF
coverage. Aim for speech during 70–85% of active writing time. Measure actual
24kHz PCM with 20ms RMS windows (-40dBFS) and join internal gaps <=100ms. This
is energy estimation, not word alignment. Count gaps from first move to last
draw, including intermediate camera travel; exclude final reading hold.
Any uninterrupted gap >60 frames needs added explanation or an intentional
`verification/pacing-review.json` entry with current `input_hash`, `gaps`
containing `segment_id`, `start_frame`, `end_frame`, and a nonempty `reason`.
Density is guidance; never stretch/cut WAV or repeatedly pay for regeneration
to satisfy a metric. Fake PCM and pacing PASS cannot approve audio meaning.

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
