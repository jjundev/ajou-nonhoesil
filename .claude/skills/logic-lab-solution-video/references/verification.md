# 검증·재개·게시

`verify`는 최종 자막본 `renders/final.mp4`를 검사한다. 마스터만 있으면 완료가 아니다. HyperFrames check와 전체 디코드, 1920×1080/30fps, 실측 WAV 샘플/해시, 최종 A/V 길이 차이 ≤1프레임을 검사한다. 자막은 Pretendard Bold FontSize14/Alignment2/MarginV14/Outline0/Shadow4/BorderStyle4, 흰 글자/약70% 검정 박스다. 문장·쉼표에서 교체하고 cue당 최대 두 줄(줄당 34자)로 표시하며 자막 중간 프레임을 마스터와 비교해 상단 PDF 침범과 하단 표시를 검사한다. 화면 비교 전에 `renders/captions.srt` 가 현재 `source/timeline.json` 으로 `write_srt` 가 지금 만드는 SRT 와 바이트 단위로 같은지(cue 번호·텍스트·줄바꿈·시각) 대조한다. 자막 줄만 손으로 고치거나 시각이 1ms라도 다른 SRT 는 화면에 자막이 보여도 실패다. 현재 source_hashes와 gate 증거 해시도 확인한다.

pencil의 `writing_animation`은 현재 composition을 실제 브라우저에서 검사한다. 모든 구간의 촉/몸통 경계·길이·순서를 확인하고 단계별 시작/중간/마스크 유지 완료, 카메라 변경, 긴 이동, 최종 hold를 캡처한다. 연필 overlay를 제외한 원본 SVG와 비교해 부분 공개의 미래 글자 누출, 마지막 마스크의 윤곽 손실, 완성 차이가 없어야 한다. 임의 seek 재현, 촉 경계 오차<=1px, 연필이 1920×900 안에 존재하고 마지막에 사라지는 것도 필수다. snapshot은 verification/writing-frames, 값·증거 해시는 verification/writing.json에 기록한다. PNG decode/해시/좌표 실패는 검사 실패이며 조용한 타이핑 대체는 없다. typing·legacy는 연필 검사를 요구하지 않는다.

자동 검사는 내용·발음·회로 의미의 승인이 아니다. 동결 PDF/MD와 완성 프레임을 대조하고 최종 영상의 발음·수식·음성 동기화를 직접 검토한다. `verification/audio-review.json`, `visual-review.json`에 `{status:passed,input_hash,notes,evidence:{relative_path:sha256}}`를 작성한다. input_hash는 `verification_fingerprint(run)`으로 구한다. audio-review의 mode는 실제 청취한 경우에만 `live-listened`다. fake PCM은 live 음성 검토로 승인하지 않는다. 실제 음성 검토가 없으면 complete=false/live_audio=unverified이며 게시하지 않는다.

상태 순서: inputs → layers → script → voice → timing → composition → render → captions → verify → publish. `resume-set`은 각 단계 입력/출력 SHA256과 사용 도구 지문으로 처음 무효 단계를 돌려준다. map 변경은 layers부터, 음성 설정은 voice부터, 작성 속도·모드·이동/hold 변경은 timing부터, 연필 길이·각도·PNG·촉 metadata 변경은 composition부터, 자막본 변조는 captions부터 재개한다. 동결한 PDF·MD·그림(PNG·SVG, `source/snapshots/` 아래 모든 깊이)을 변조하거나 지우면 inputs부터 다시 시작한다. `source/manifest.json` 변경 후 검토 input_hash도 새로 작성한다. 길이·각도 변경 후 assemble은 현재 writing.json의 시각 값을 조립에 동결하며 source/timeline.json과 voice/timing 기록은 보존한다. 화면 게이트는 원문·PCM으로 재계산한 현재 설정을 기준으로 검사한다. 성공 WAV는 물리적으로 삭제하지 않는다.

새 clone 에는 `layers/` 의 svg·png 와 `verification/` 이 없어(`.gitignore`) `layers` 단계 출력(`layers/animated.svg`·`verification/gate.json`)이 비므로 `resume-set` 은 inputs 가 유효해도 `layers` 부터 무효를 돌려준다. `layers/candidates.json` 을 지우고 `extract` 를 다시 돌려 svg·png·게이트 프레임을 만든다(비용 0).

게시 직전에 최종 파일/검증 지문을 다시 확인한다. 같은 파일시스템 staging, 이전버전 backup, journal로 파일과 latest를 교체한다. 이동 실패 시 이미 교체한 파일도 복구한다. 중단된 pending journal은 다음 게시 때 복구한다. 같은 제목/문항 키 충돌은 오류다. 부분 성공은 현재 검증된 파일만 게시하되 latest를 유지한다. 기존 결과는 이전버전에 남고 마스터는 run에 남는다.

실측 수용 테스트는 실제 Aoede 음성으로 만든 batch 를 검사한다. 개발 미디어 검사 통과와 실제 Aoede 청취 통과를 분리하여 기록한다. 승인 없는 유료 테스트·가짜 audio review로 게시하지 않는다.

```sh
LOGIC_LAB_ACCEPTANCE_BATCH=/ABS/문제풀이영상/실험05/실험05_제작자료/실행/RUN_ID .venv/bin/python -m unittest discover -s .claude/skills/logic-lab-solution-video/tests -p test_lab_acceptance.py -v
```

`LOGIC_LAB_ACCEPTANCE_BATCH` 가 없으면 skip 한다. 지정하면 batch(실험05 기출3·기출12)의 각 문항 report 가 complete·live_audio verified 인지, catalog SHA256 이 실제 MP4 와 같은지, figure 문항의 layers 에 figure 도형이 있는지 검사한다.

검증된 Manifest.title을 실제 파일명에 사용하며 금지된 파일명 문자는 공백으로 정리한다. 게시 영수증은 실제 MP4와 catalog SHA256을 저장한다. 정상 게시 후 재개는 완료로 판정하며, 게시된 파일이 바뀌면 publish 단계부터 다시 확인한다. 명시적 카메라도 마지막 전체 답안 hold를 덮을 수 없다.

## 회로 주석 게이트

verify의 teaching_animation은 현재 sidecar/WAV로 schedule, geometry, camera를 독립 재생성하여 실제 composition과 대조한다. verification/teaching.json과 teaching-frames에는 카메라 전환 시작/중간/끝, 주석 작성·숨김, 최종 전체 화면, 역방향·GSAP seek 증거와 해시를 남긴다. 원본은 주석을 숨긴 상태로 별도 기준 SVG와 비교하고, 주석은 렌더러의 opacity/mask를 복사하지 않는 기준 화면과 비교한다.

촉 오차는 최대 1px, 기본 연필 길이는 160±0.5px, 전체 경계는 1920×900이다. 원본 필기와 주석은 한 연필을 공유하며 동시에 표시하지 않는다. typing 풀이에서도 주석 검증은 필수다. 누락·선공개·최종 잔류·촉 또는 카메라 변조는 실패한다. label 본문은 화면상 26px 이상이며 문제 그림/주석/연필을 동시에 맞출 수 없으면 영역 ID와 이유를 보고한다.

fake PCM 으로 만든 개발 검증은 렌더·자막·브라우저·미디어만 확인한다. fake PCM은 audio_meaning을 승인하지 않으며 production 게시를 통과하지 못한다. 실제 Aoede 최종 음성·주석 의미를 직접 검토한 증거가 별도로 필요하다.

Spatial pencil verification additionally requires `writing_flow` and
`narration_pacing`. Original geometry/authored bands independently define
expected order, whole-chunk fit, fixed camera, and no draw during transitions.
Evidence is in `writing-flow.json`, `flow-frames`, and `narration-pacing.json`.
Current gap review is hash-bound; changed PCM invalidates it. Audio meaning
still requires actual listening, independently of all technical checks.

## 회로 근거와 필기 음성 저작

신규 교육 흐름은 `source/lesson.json`(schema_version=1)에 PageMap 순서의 steps를 작성한다. 각 row는 step_id, mode, reason_segment_ids, check_segment_ids, region_ids, annotation_ids, meaning_notes, source_refs를 가진다. circuit 단계는 관련 회로 reason과 표시가 각각 필요하며 식을 쓰기 전에 회로 연결/가정을 설명한다. calculation 단계는 회로 목록을 비우고 exemption_reason에 제목·기존 근거의 후속 정리 등 이유를 명시한다. 단순 제목이나 계산마다 왕복하지 않는다. 기존 lesson 없는 run은 재개 가능하다.

핵심 논리마다 회로 근거 → 해당 내용 필기를 배치하고 필요한 경우 check로 돌아온다. 필기 text에는 지금 쓰는 문장/식의 읽기와 기호·항의 의미를 넣는다. 긴 원고 하나를 붙이지 말고 PageMap을 의미 단위로 분할하며 glyph/shape 중복·누락을 막는다. 필기 기본 7.5 chars/sec를 유지하고 영상 길이는 이해 우선으로 늘린다.

guided manifest의 모든 segment에 음성 `text`와 표시 `caption_text`를 별도로 작성한다. ‘알 오 원’은 음성으로 읽고 자막에는 `r_O1`을 쓴다. `r_O3`, `g_m1`, `V_BE`, `R₁`, `Q₁`, `∥` 등의 기호와 원문 대소문자를 보존하며 LaTeX 원문을 자막에 출력하지 않는다. caption_text가 없는 기존 run만 text로 fallback한다. 기호 토큰·곱 항·괄호 묶음을 줄 중간에서 자르지 않으며 34자를 넘는 보호 구간은 저작 오류다. 자막만 변경해도 후속 결과를 갱신하되 동일 text의 WAV는 TTS cache로 재사용한다.

현재 입력에 대한 lesson_flow는 회로 근거의 순서/안정 화면/표시 가시성을 검사한다. 의미 검토에서는 원문 회로, 실제 표시, 음성, 기호 자막을 함께 대조한다. 필기 음성의 2초 초과 무음은 narration_pacing 검토 대상이고 70–85% 밀도는 저작 가이드다. 카메라/픽셀 검사 통과나 synthetic PCM으로 교육 품질과 실제 음성을 승인하지 않는다.

### 문장·쉼표 자막 경계
문장 종료 온점에서 자막을 교체하고 서로 다른 문장을 한 cue에 합치지 않는다. 수식·괄호 밖 쉼표에서도 교체하며 쉼표는 앞 cue에 남긴다. 화면 내 줄바꿈은 교체와 별개이며 cue당 최대 두 줄, 줄당 34자다. 줄바꿈 후보는 우선순위 순으로 ① 설명과 수식(연산자가 든 식: `A′B + AB′`, `Y0=S1′S0′D+S1S0D`) 경계 ② 수식 밖 일반 공백 ③ 괄호 밖 연산자 바로 앞이고, 길이 균형은 같은 우선순위 안에서만 비교한다. 한 줄에 들어가는 수식은 통째로 한 줄에 두고, 긴 식은 연산자를 다음 항과 같은 줄에 둔다(`출력 F는 A′B′C′D + A′BC′D′` / `+ AB′CD′ + ABC′D + ABCD′입니다.`). 신호 이름·곱 항과 그 부정(`Bo`, `A′B`, `A'B`, 결합 오버바 `A̅B̅`), 괄호 묶음 내부와 맞붙은 묶음 사이(`(A + B′)(A′ + C)`), 공백으로 이은 곱(`S1′ S0′ D`), 니블 단위 이진수(`0011 1010`), `1-to-4` 는 나누지 않는다. 혼자 쓴 신호 이름·이진수는 수식이 아니라 문장으로 보고 ②의 균형을 따른다. 안전한 두 줄이 없으면 InputError 이며 자동 축약·글자 축소·cue 분할은 하지 않는다. libass 는 `WrapStyle=2` 로 SRT 에 적힌 줄바꿈만 쓴다. 기호·첨자는 보존한다. 숫자 내부 점/쉼표, 식별자 점, 괄호/인용 내부 구두점은 보호하고 완결된 인용 문장의 닫는 따옴표는 문장과 함께 표시한다.
마지막 온점이 없는 기존 text는 표시용 온점만 추가하며 저장 원고와 음성은 바꾸지 않는다. ?, !, … 종결 및 불균형 괄호/LaTeX 원문은 저작 오류다. 두 줄에 들어가지 않는 구절과 34자 초과 보호 구간(항·괄호 묶음)은 check/tts 전에 segment id와 문제 구절로 알린다. 작성자가 의미상 쉼표 경계 또는 간결한 표기를 지정한다.
청크 없는 legacy manifest 의 SRT 시간은 실측 voice_samples 안에서 원문 의미 단위의 글자 수 비율로 배분한다(`pcm-chunks-v1` 은 아래 청크 동기화 절처럼 실측 청크 경계를 쓴다). 줄바꿈과 표시용 추가 온점은 시간 가중치에 넣지 않는다. cue 사이 임의 공백은 추가하지 않으며 실제 문장·쉼표 발화 시점과의 정밀 정렬은 제공하지 않는다. 자막만 바꾸어도 기존 final/SRT 검증은 다시 수행하고 같은 음성 WAV는 cache로 재사용한다. 두 줄 자막은 실제 libass 화면에서 하단 900..1080 영역과 기호 보존을 확인한다.

두 줄 자막 배경은 libass BorderStyle4/Outline0/Shadow4로 cue 전체에 하나의 균일한 박스를 그린다. 줄별 박스를 겹치는 BorderStyle3은 사용하지 않는다. 실제 두 줄·서로 다른 줄 길이에서 박스 가장자리와 불투명도 균일성 및 기호·글자 가독성을 확인한다.

## 청크 동기화 검증 (pcm-chunks-v1)

청크 모드 manifest 이면 verify 에 `chunk_sync` 검사가 붙는다. `verification/chunk-sync.json` 에 status·input_hash·evidence_hashes(manifest·audio·chunk-audio·청크 절단·timeline·SRT·raw/연결 WAV)·issues 를 남긴다. 검사 내용: 영수증이 현재 대본의 spoken-text-only 키인지, raw 청크 WAV 해시·형식, 연결 WAV 가 raw PCM+절단과 바이트까지 같은지, timeline cue 가 저장 PCM 으로 다시 만든 cue 와 같은지, `renders/captions.srt` 가 그 cue 로 다시 쓴 SRT 와 같은지. 이것은 구조 검증이며 실제 청취 증거가 아니다(`live_listening: not-evidence`). 게시 판정(publish-set)도 청크 모드에서는 chunk_sync 통과를 요구한다.

청크 모드 audio-review 는 기존 필드(status·mode·input_hash·notes·evidence)에 더해 `chunk_checks` 를 가진다. manifest 의 모든 청크를 순서대로 한 행씩: `{segment_id, chunk_id, transcript_match, no_instruction_speech, natural_join, sync_passed, notes}`. 네 플래그는 모두 `true`(문자열·null 불가), notes 는 비우지 않는다. transcript_match 는 청크 대본대로 읽었는지(누락·추가 발화 없음), no_instruction_speech 는 지침 같은 발화가 없는지, natural_join 은 앞 청크와 이어 붙인 곳이 끊기지 않는지, sync_passed 는 최종 MP4 에서 그 cue 전환이 음성 경계와 맞는지다. 실제로 최종 파일을 들은 경우에만 mode 를 `live-listened` 로 쓴다. 청취 수단이 없으면 기술 검증 결과와 청취 미검증 상태를 함께 전달하고 complete=false/live_audio=unverified 로 두며 publish-set·latest 갱신을 하지 않는다. 합성 PCM 으로 chunk_sync 가 통과해도 live_audio 는 승인되지 않는다. 청크 없는 legacy run 의 audio-review 계약은 그대로다.
