# 음성과 작성 타이밍

음성 설정은 assets/defaults.json, 작성 설정은 assets/writing-defaults.json이며 각각 source/config.json과 source/writing.json에 동결한다. Aoede/한국어/24kHz mono PCM, 1920×1080/30fps이며 모델과 공급자를 자동 대체하지 않는다. 환경 GOOGLE_API_KEY 또는 GEMINI_API_KEY를 사용한다. --env-file은 메모리로만 읽고 config/로그에 키를 넣지 않는다. budget_usd=null은 상한 없음이며 명시 상한을 주면 price 요율과 기존 예산 규칙을 따른다. 모든 문항은 batch/usage.json 하나를 쓴다.

TTS 요청 정책은 `spoken-text-only-v1`이다. 텍스트 입력에는 발음 사전(`pronunciation`)을 적용한 읽을 대본만 넣고, 지침(direction)·"원고:" 같은 안내문·caption_text는 보내지 않는다. 음성(Aoede)·언어(ko-KR)·모델·오디오 형식은 설정 필드로만 정한다. 지침 문장을 함께 보내면 모델이 그 문장까지 읽어 버릴 수 있다(상류 전자회로2 영상에서 "과장하지 않습니다" 류 발화가 들렸다). 그래서 `defaults.json`에 direction이 없고, 옛 run의 config에 남은 direction은 요청에 넣지 않으며 tts가 다시 동결하는 config에서도 지운다. 말투·속도는 대본 문장(~해요체, 쉼표 위치)으로만 조절한다. 캐시 키에는 정책 버전과 실제 전송 대본이 들어가므로 지침을 포함하던 옛 캐시 WAV는 재사용되지 않고 새로 합성된다(유료). caption_text만 바꾸면 키가 같아 재합성하지 않는다. WAV 영수증(`assets/voice/*.json`)에는 policy와 payload_hash가 기록된다.

문제를 확인하는 발화로 시작한다. 판단 이유(reason), 원문을 쓰는 동안의 설명(write), 계산 확인(check), 답 확인(summary)을 원자료에 연결한다. PDF에 없는 새 계산이나 풀이를 만들지 않는다. 한 발화가 길면 PageMap 단계도 작은 연속 단위로 나눈다. 실패한 문항만 재개하고 성공 WAV는 내용/설정 해시로 재사용한다.

연필 기본은 7.5글자/초이며 인접 글자마다 이동 1프레임 + 작성 3프레임이다. 사용자 요청에 따라 이전 5글자/초(이동 1+작성 5프레임)보다 1.5배 빠르다. 긴 이동·줄바꿈·단계 이동은 최소 8프레임 이동을 사용하고 작성 시간을 줄이지 않는다. write 구간은 max(실제 WAV 길이, 모든 이동·작성 길이)+ceil(0.75×30)=23프레임이다. typing 선택은 기존 ceil(30/7) 프레임 간격을 사용한다. 작성 파일이 없는 legacy 실행은 기존 config의 속도/hold를 그대로 쓴다. 공백은 이동 시간만 사용하며 연필은 숨긴다. typing의 shape는 같은 단계의 anchor glyph 완료 시점에 공개한다. pencil은 writing_units의 shape를 원본 도형 단위 예산으로 작성한다: 같은 step_id+shape_id의 전체 폭 W, 대표 글자 높이 H, 양의 폭 조각 수 n으로 B=min(min(90, max(18, ceil(W/H×interval))), 18×n)(interval=ceil(30/chars_per_second))을 잡고 clip 폭에 비례해 나눈다. 18×n 상한 때문에 예전(조각마다 18)보다 느려지지 않는다: 한 조각 도형은 18 그대로, 잘게 쪼갠 도형만 빨라진다. 조각당 최소 1프레임, 합계는 B, 최대 나머지 순·동률은 저작 순으로 정수화하며, 조각 수가 B보다 많으면(폭 공식보다 조각이 많은 19조각 이상) 저작 오류다. 폭 0인 세로 선은 한 조각 18프레임으로 위에서 아래로 공개한다. 풀이 그림(kind=figure)은 이 예산이 아니라 그림 wipe 60프레임이다. 새 줄 들어 옮기기(최소 8프레임)는 새 줄 첫 대상(공백이어도)에만 한 번 적용하고 뒤 대상은 인접 이동이다. 전체 타이밍은 800샘플=1프레임이며 실제 PCM은 자르거나 늘이지 않고 남는 구간을 무음으로 채운다. 마지막은 최소 1초 전체 답안 확인이다. 단어별 실제 음성 정렬을 주장하지 않는다.

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

필기 지연은 무음과 따로 잰다. 구간마다 `voice_end_frame`(구간 시작+PCM 샘플 수/800 올림, 에너지가 아니라 실제 PCM 끝), `writing_end_frame`(마지막 writing span 끝), `writing_lag_frames`=max(0, 필기 끝−음성 끝), `completed_hold_frames`=구간 끝−max(음성 끝, 필기 끝)을 보고한다. 지연이 60프레임(2초)을 넘으면 review-required(`unreviewed_writing_lags`)다. 정확히 60은 통과다. 필기 중 무음을 완성 화면 읽기(hold)로 기록하지 않는다. 의도한 지연의 예외는 현재 `input_hash`의 `pacing-review.json`에 `writing_lags: [{segment_id, voice_end_frame, writing_end_frame, reason}]`로 경계가 정확히 맞고 reason이 비어 있지 않을 때만 승인된다. 기존 `gaps` 사유(예: "연필이 마저 쓰는 무음")로는 필기 지연을 승인할 수 없고, `writing_lags`로 무음 gap을 승인할 수도 없다. 먼저 대본·분할로 지연을 없애고 예외는 마지막 수단이다. 실제 청취·의미 검토를 대신하지 않는다.

## 회로 근거와 필기 음성 저작

신규 교육 흐름은 `source/lesson.json`(schema_version=1)에 PageMap 순서의 steps를 작성한다. 각 row는 step_id, mode, reason_segment_ids, check_segment_ids, region_ids, annotation_ids, meaning_notes, source_refs를 가진다. circuit 단계(논회실에서는 문제 그림 — 회로도·진리표·파형 — 을 근거로 삼는 단계)는 관련 reason과 표시가 각각 필요하며 식을 쓰기 전에 연결/가정을 설명한다. calculation 단계는 회로 목록을 비우고 exemption_reason에 제목·기존 근거의 후속 정리 등 이유를 명시한다. 단순 제목이나 계산마다 왕복하지 않는다. 기존 lesson 없는 run은 재개 가능하다.

핵심 논리마다 회로 근거 → 해당 내용 필기를 배치하고 필요한 경우 check로 돌아온다. 필기 text에는 지금 쓰는 문장/식의 읽기와 기호·항의 의미를 넣는다. 긴 원고 하나를 붙이지 말고 PageMap을 의미 단위로 분할하며 glyph/shape 중복·누락을 막는다. 필기 기본 7.5 chars/sec를 유지하고 영상 길이는 이해 우선으로 늘린다.

guided manifest의 모든 segment에 음성 `text`와 표시 `caption_text`를 별도로 작성한다. ‘에스원 바 에스제로 바 디’는 음성으로 읽고 자막에는 `S1′S0′D`를 쓴다. `+`, `V_CC`, `74HC138`, `Y0` 등의 기호와 원문 대소문자를 보존하며 LaTeX 원문을 자막에 출력하지 않는다. caption_text가 없는 기존 run만 text로 fallback한다. 기호 토큰·곱 항·괄호 묶음을 줄 중간에서 자르지 않으며 34자를 넘는 보호 구간은 저작 오류다. 자막만 변경해도 후속 결과를 갱신하되 동일 text의 WAV는 TTS cache로 재사용한다.

현재 입력에 대한 lesson_flow는 회로 근거의 순서/안정 화면/표시 가시성을 검사한다. 의미 검토에서는 원문 회로, 실제 표시, 음성, 기호 자막을 함께 대조한다. 필기 음성의 2초 초과 무음은 narration_pacing 검토 대상이고 70–85% 밀도는 저작 가이드다. 카메라/픽셀 검사 통과나 synthetic PCM으로 교육 품질과 실제 음성을 승인하지 않는다.

### 문장·쉼표 자막 경계
문장 종료 온점에서 자막을 교체하고 서로 다른 문장을 한 cue에 합치지 않는다. 수식·괄호 밖 쉼표에서도 교체하며 쉼표는 앞 cue에 남긴다. 화면 내 줄바꿈은 교체와 별개이며 cue당 최대 두 줄, 줄당 34자다. 줄바꿈 후보는 우선순위 순으로 ① 설명과 수식(연산자가 든 식: `A′B + AB′`, `Y0=S1′S0′D+S1S0D`) 경계 ② 수식 밖 일반 공백 ③ 괄호 밖 연산자 바로 앞이고, 길이 균형은 같은 우선순위 안에서만 비교한다. 한 줄에 들어가는 수식은 통째로 한 줄에 두고, 긴 식은 연산자를 다음 항과 같은 줄에 둔다(`출력 F는 A′B′C′D + A′BC′D′` / `+ AB′CD′ + ABC′D + ABCD′입니다.`). 신호 이름·곱 항과 그 부정(`Bo`, `A′B`, `A'B`, 결합 오버바 `A̅B̅`), 괄호 묶음 내부와 맞붙은 묶음 사이(`(A + B′)(A′ + C)`), 공백으로 이은 곱(`S1′ S0′ D`), 니블 단위 이진수(`0011 1010`), `1-to-4` 는 나누지 않는다. 혼자 쓴 신호 이름·이진수는 수식이 아니라 문장으로 보고 ②의 균형을 따른다. 안전한 두 줄이 없으면 InputError 이며 자동 축약·글자 축소·cue 분할은 하지 않는다. libass 는 `WrapStyle=2` 로 SRT 에 적힌 줄바꿈만 쓴다. 기호·첨자는 보존한다. 숫자 내부 점/쉼표, 식별자 점, 괄호/인용 내부 구두점은 보호하고 완결된 인용 문장의 닫는 따옴표는 문장과 함께 표시한다.
마지막 온점이 없는 기존 text는 표시용 온점만 추가하며 저장 원고와 음성은 바꾸지 않는다. ?, !, … 종결 및 불균형 괄호/LaTeX 원문은 저작 오류다. 두 줄에 들어가지 않는 구절과 34자 초과 보호 구간(항·괄호 묶음)은 check/tts 전에 segment id와 문제 구절로 알린다. 작성자가 의미상 쉼표 경계 또는 간결한 표기를 지정한다.
청크 없는 legacy manifest 의 SRT 시간은 실측 voice_samples 안에서 원문 의미 단위의 글자 수 비율로 배분한다(`pcm-chunks-v1` 은 아래 청크 동기화 절처럼 실측 청크 경계를 쓴다). 줄바꿈과 표시용 추가 온점은 시간 가중치에 넣지 않는다. cue 사이 임의 공백은 추가하지 않으며 실제 문장·쉼표 발화 시점과의 정밀 정렬은 제공하지 않는다. 자막만 바꾸어도 기존 final/SRT 검증은 다시 수행하고 같은 음성 WAV는 cache로 재사용한다. 두 줄 자막은 실제 libass 화면에서 하단 900..1080 영역과 기호 보존을 확인한다.

두 줄 자막 배경은 libass BorderStyle4/Outline0/Shadow4로 cue 전체에 하나의 균일한 박스를 그린다. 줄별 박스를 겹치는 BorderStyle3은 사용하지 않는다. 실제 두 줄·서로 다른 줄 길이에서 박스 가장자리와 불투명도 균일성 및 기호·글자 가독성을 확인한다.

### 숫자·연산의 자막 표기
음성 `text`는 자연스러운 한국어 발음을 쓰고, `caption_text`는 수학적 수치·연산을 숫자와 기호로 직접 저작한다. 예: `더하기 → +`, `빼기/음수 → −`, `곱하기 → ×`, `나누기 → /`, `이 ΔI → 2ΔI`, `이분의 삼 → 3/2`, `일 점 오 → 1.5`, `영 → 0`, 문항 `에이/비 → (a)/(b)`. 분수의 괄호와 부호를 원본에 맞춰 `R_L × ((I₀ + ΔI)/2 − (I₀ − ΔI))`처럼 보존한다. 기호를 단순 연결해 연산 우선순위를 바꾸지 않는다.
`이 두 항`, `이 회로`, `더해집니다` 등 설명 문장은 문맥대로 유지한다. 한글 숫자 전체 치환은 금지한다. 자연어 문맥만으로 불명확한 숫자는 원본 PDF/MD와 대조하고 표시용 문장 전체를 저작한다. `caption_text`의 명시적 연산어와 한글 분수·소수는 error로 차단한다. 기호 앞 한글 수사(`이 ΔI`, `이 R_L`), 한글 수사로 나눈 표현, `값은/계수는/답은/전류는/전압은 이입니다` 같은 수치 서술은 warning으로 알리고 진행한다. `I₀이` 같은 조사와 `이 회로`, `이 두 항` 같은 일반 지시어는 유지한다. 경고는 숫자 판정이 아니며 원본과 문맥 대조가 필요하다. 자동 치환하지 않는다. 모든 발견을 severity/code/segment_id/span/matched_text/reason으로 수집하고 check/tts/captions 결과와 verify 보고서에 warnings로 전달한다. TTS 경고는 유료 요청 전에 stderr로 출력한다. 경고 자체로 완료를 막거나 사용자 승인 단계를 추가하지 않으며 기존 최종 의미 검토에서 경고도 대조한다. 이 검사는 완전한 한국어 해석기가 아니므로 미탐 가능 표현은 내용 검토에서 확인한다. `caption_text` 없는 legacy fallback은 유지한다.
자막을 수정하면 WAV와 음성 `text` 해시를 보존하고, 현재 검토 지문·타임라인·자막·최종 MP4·검증을 갱신한다. 동일 음성은 캐시를 재사용하며 유료 재합성을 하지 않는다. 기호·첨자·분수·괄호, 문장/쉼표 경계, 두 줄 제한 및 실제 하단 박스를 확인한다.

### 논리식의 음성·자막 (논회실)
자막 `caption_text`는 원문 기호를 그대로 쓴다: 부정은 `′`(`S1′S0′D`), OR 는 `+`, AND 는 붙여 쓰기, 첨자 이름은 `V_CC`, 칩 이름은 `74HC138`. 음성 `text`는 읽는 소리로 쓴다: ‘에스원 바 에스제로 바 디’, ‘칠사 에이치씨 일삼팔’, ‘브이 씨씨’. OR 의 `+` 는 ‘오어’로 읽고 ‘더하기’로 읽지 않는다. `defaults.json` 의 `pronunciation` 은 `′`→‘ 바 ’(앞뒤 띄움 — ‘바디’로 붙어 읽히지 않게), `V_CC`·`V_IH`·`V_IL`·`GND` 만 TTS 직전에 치환하고, 그 밖의 신호 이름은 원고에서 직접 소리로 쓴다.
자막에 "신호 이름 + 바/낫"(`S1 바`, `B 바는`, `E 낫이면`)이 보이면 조사가 붙어도 `logic_bar_word` warning 이다. 자막에는 `S1′` 로 쓴다. 앞에 대문자 신호 이름이 없는 ‘이 바를’ 같은 일반 한국어는 경고하지 않는다.
음성 원고는 복습팩 풀이와 같은 ~해요체로 쓴다(‘~예요’, ‘~해요’). 상류 예시의 ‘~입니다’ 체를 섞지 않는다.

## 청크 동기화 (pcm-chunks-v1)

목표: 자막 cue 하나에 읽을 대본 한 청크를 명시적으로 대응시키고, 생성된 PCM 의 실측 샘플 위치로 자막 시간을 정한다. 글자 수 비례 배분은 실제 문장 발화 경계를 재지 않아 cue 가 음성보다 앞서거나 늦는다.

**저작.** manifest `schema_version` 은 1 그대로, `caption_timing: "pcm-chunks-v1"` 을 추가하고 모든 segment 에 `chunks` 를 쓴다. 각 청크는 `{id, text, caption_text}` 이고 id 는 segment 안에서 고유한 안전한 ASCII(`[A-Za-z][A-Za-z0-9_-]*`)다. 합성 ID `segment_id__chunk_id` 는 run 전체에서 겹치면 안 된다. 공백 정규화 후 청크 text 를 공백으로 이으면 부모 text, caption_text 도 같은 규칙으로 부모 caption_text 와 같아야 한다. 각 청크 caption_text 는 기존 문장·쉼표 규칙으로 cue 가 정확히 하나여야 한다(화면 두 줄 줄바꿈은 허용, 쉼표로 끝나는 청크는 쉼표를 유지). 청크 text 에는 지침 문구를 넣지 않는다 — 읽을 소리만 쓴다(‘에스원 바 에스제로 바 디예요.’). 자막 표기 규칙(‘S1′S0′D’, 논리식 경고 등)은 청크 caption_text 에 그대로 적용되고 경고에는 `chunk_id` 가 붙는다. 모드 없이 청크를 쓰거나, 모드에서 청크 없는 segment 가 있으면 check/tts 전에 오류다. 기존 run 에 적용하려면 기존 cue 경계(문장·쉼표)를 출발점으로 청크를 나누고 내용 지문이 바뀌므로 coverage/circuit-review 를 새 지문으로 갱신한다.

**합성과 연결.** 청크마다 spoken-text-only 요청을 보내 `assets/voice/<segment>__<chunk>-<key16>.wav` 와 영수증(policy·payload_hash·samples·sha256·usage, 비밀정보 없음)을 만들고 목록을 `source/chunk-audio.json`(`{policy, voices}`)에 둔다. segment WAV(`<segment>-joined-<key16>.wav`)는 청크 raw PCM 을 순서대로 이은 것이다 — 청크 사이에 무음을 넣지 않고 AAC 등 중간 인코딩도 없다. `source/audio.json` 의 segment 영수증에는 순서 있는 `chunks[{id, source_id, raw_sha256, trim_start_sample, trim_end_sample, start_sample, end_sample}]` 가 붙고 start/end 는 segment WAV 기준 상대 샘플이다. 일부 청크가 실패하면 성공한 청크 WAV 는 남고(재실행 시 캐시) `audio.json` 은 연결이 끝난 뒤에만 바뀐다. caption_text 만 바꾸면 캐시 키가 같아 재합성하지 않는다.

**명시 절단(선택).** 기본은 청크 WAV 전체를 쓴다. 청취해서 긴 앞뒤 무음을 확인한 청크만 `source/chunk-trims.json` 에 적는다: `{"schema_version":1,"rows":[{"segment_id","chunk_id","raw_sha256","start_sample","end_sample","reason"}]}`. 정수 `0 <= start_sample < end_sample <= raw samples`, raw_sha256 은 현재 원본 청크 WAV, reason 은 비우지 않는다. 자동 에너지 탐지로 자르지 않는다(약한 발음 ‘에프’·‘디’ 끝이 잘린다). 원본 WAV 는 보존된다. 절단표를 바꾸면 `resume-set` 이 voice 부터 돌려주며, `tts` 를 다시 돌리면 캐시 원본으로 연결본만 갱신한다(유료 요청 없음). 대본을 바꾼 청크의 절단 행은 유료 요청 전에 거부되므로 행을 지우거나 다시 쓴다.

**타이밍.** timeline 에 `caption_timing` 과 `caption_cues[{segment_id, chunk_id, caption_text, start_sample, end_sample}]` 가 생긴다. 절대 샘플 = segment 시작 샘플 + 상대 경계다. cue 는 segment 의 실측 voice 를 빈틈없이 덮고 필기·카메라 때문에 늘어난 segment 끝 hold 에는 자막을 늘리지 않는다. SRT 는 이 샘플을 밀리초로 반올림만 하므로 오차는 0.5ms 이하이고, 30fps 영상의 표시 전환은 1프레임 이내다. 청크 안의 단어 단위 정렬은 주장하지 않는다. `retime` 은 청크 영수증·원본·연결본·절단을 다시 대조한 뒤에만 timeline 을 만든다.

## 발화에 맞춘 회로 필기
같은 타원을 되풀이해서 설명을 대신하지 않는다. 선택 조건·데이터 경로·출력을 그 말을 하는 발화에 맞춰 표시한다. 짧은 기호·화살표·0/1 값 label 은 원본 선과 신호 이름 **옆**에 두고 선을 덮지 않는다. 교차점에 점이 없는 두 선을 연결처럼 잇지 않는다. 신호 이름은 원본 표기 그대로 쓴다.

**굵기.** 도형(arrow·ellipse·underline)마다 `stroke_width_px` 를 유한한 숫자 2~12px 로 줄 수 있고, 생략하면 3px 다. 새로 저작할 때는 보조 4px·경로 6px·강조 8px 를 쓴다. label 에는 굵기를 주지 않고(오류) runs 의 `font_size_pt` 로 크기를 정한다.

**색 역할(논리회로).** 색만으로 구분하지 않고 위치·기호로도 구분한다.

| 색 | 역할 | 예 |
|---|---|---|
| 파랑 `#1565C0`(기본) | 선택 조건 | S1S0 값, 선택된 진리표 행 |
| 주황 `#C45100` | 데이터·켜진 입력 | 선택된 D 경로, 우선순위 인코더의 가장 왼쪽 1 |
| 초록 `#237A43` | 출력·결과 | Yk, A2A1A0 |
| 자주 `#8E348E` | 대조·흔한 실수 | 고르지 않은 경로, 틀리기 쉬운 값 |

**label 글자.** label 폰트(Pretendard)에 `⊕` 글리프가 없어 `A⊕B` label 은 `unsupported font glyph` 로 막힌다. XOR 은 label 에서 글자로 쓴다(‘A XOR B’). 프라임 `′` 은 쓸 수 있다(`S1′S0′`).

**청크에 묶기.** manifest 가 `caption_timing: "pcm-chunks-v1"` 일 때만 항목에 `chunk_id`(그 reason/check segment 의 `chunks[].id`)를 줄 수 있다. 오프셋은 그 청크 발화 시작 기준 정수 ≥0(기본 0)이고, 한 segment 안에서 청크 항목과 legacy 항목을 섞지 않는다(다른 segment 끼리는 섞어도 된다). 서로 다른 청크의 항목은 같은 오프셋을 써도 된다. 그리기는 ceil(청크 start_sample/800)+오프셋과 segment 시작+12(카메라 이동) 중 늦은 프레임에 시작하고, move 8프레임과 필기 전체가 floor(청크 end_sample/800) 와 카메라 복귀 직전(segment 끝−13) 이내에 끝나야 한다. 넘치면 `<id> segment <sid> chunk <cid>` 오류가 나며, 표시나 label 을 줄이고 무음을 늘리지 않는다. `chunk_id` 없는 항목은 예전처럼 segment 기준 오프셋(하한 12)과 최소 길이 보정을 받는다.

**범위.** 주석은 `work_bbox` 밖(왼쪽 조건 패널의 회로도·진리표·파형)에만 둔다. 중앙 풀이 칸 그림 위 주석은 아직 지원하지 않는다. 설명 중 표시는 누적하고 다음 풀이로 돌아갈 때 `hide_at` 으로 정리하며 최종 전체 화면에서는 숨긴다. label 본문은 화면에서 26px 이상이어야 한다. `chunk_id` 를 바꾸면 timing 부터, 굵기·색만 바꾸면 composition 부터 다시 하고 WAV 는 그대로 쓴다. 기술 검사 통과가 음성 청취를 대신하지 않는다.
