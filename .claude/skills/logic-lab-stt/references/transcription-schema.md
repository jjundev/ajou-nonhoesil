# 전사 결과 스키마

`--output-dir` 아래 `<지문24자리>/`에 기록한다. 지문은 원본 실제 경로·SHA-256, 정책, 모델·엔드포인트, 옵션, 청크 샘플 수, 오디오 시각 차이에 따라 달라진다.

| 파일 | 내용 |
|---|---|
| state.json | identity, running/failed/complete, 안전한 오류 코드 또는 완성본 경로·해시 |
| chunks/00000.json 등 | 청크 샘플 시작·개수, 승인된 text/words/usage와 무결성 지문 |
| transcript.md | 단일 전사. 시간 옵션 지정 시 MM:SS.mmm와 발언, 없으면 단락 |
| transcript.json | 완성 전사와 시간 정보·청크 사용량·출처 |

transcript.json은 schema_version=1, status=complete다. source_sha256/source_path/policy/model/endpoint/config/chunk_frames를 보관한다. text는 API 전사문, words는 시간 옵션이 있을 때 반환 단어 목록이다. chunks는 index/start_s/end_s/text/words/usage를 가진다. duration_s는 추출 음성 샘플 수 기준이다. 사용량은 각 청크 usage를 합산한다. 캐시 사용량은 이번에 새로 발생한 과금이 아니며 비용 총액은 추측하지 않는다.

words는 word/start_s/end_s를 가진다. API startOffset/endOffset 초 문자열에 청크 시작 샘플/16000과 audio_offset_s를 더한다. audio_offset_s는 첫 디코딩 오디오 PTS에서 첫 표시 영상 프레임 PTS를 뺀 값이다. 영상이 없으면 첫 오디오 샘플을 0초로 한다. time_basis는 first_display_frame 또는 first_audio_sample이다. 영상보다 앞선 음성은 음수일 수 있다. 근거 manifest에는 영상 범위 안의 발언만 선택한다.

timing_accuracy=approximate, audio_review=not_listened는 전사 한계를 명시한다. 시간 옵션 MD는 반환 단어 순서대로 단락을 묶고 text에는 API 원래 전사 문자열을 보존한다. 숫자·띄어쓰기 등 모델 자체 정규화가 있을 수 있다.

오디오 스트림이 없으면 `{status: no_audio, source_sha256: ...}`를 반환하며 MD를 만들지 않는다. 명시적인 빈 전사 객체는 MD에 `[인식된 발화 없음]`으로 표시한다. 후보 부재·차단·STOP 아닌 종료·발언은 있으나 시간정보 없음은 완료로 인정하지 않는다.

동일 실행은 `.lock`으로 겹치지 않게 한다. 파일·캐시 해시 불일치는 덮어쓰지 않는다. 해시는 우발적 훼손 탐지이며 서명된 진위 인증은 아니다.
