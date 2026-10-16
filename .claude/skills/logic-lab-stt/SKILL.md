---
name: logic-lab-stt
description: 논리회로실험 영상·음성을 Gemini API로 원문 전사하거나 전사 MD와 타임스탬프를 생성할 때 사용한다. extract-lab-video-evidence의 누락 전사본 자동 생성에도 사용한다. 사진 판독·영상 편집·결과보고서 작성은 해당 전용 스킬을 사용한다.
---

# 실험영상 음성 전사

프로젝트 로컬 Gemini API 전사 실행기다. 실행 에이전트가 GPT여도 사용한다. 공용 audio-stt의 네이티브 view_file 경로와 달리 실제 음성은 Gemini API가 처리한다. 원본을 수정하지 않고 발언을 전사하며 회로 상태·실험 성공을 판정하지 않는다. API 전사는 직접 청취가 아니다.

## 실행

`TOOL`은 이 파일 옆 `scripts/transcribe.py`의 실제 경로다. Python 3, FFmpeg, ffprobe가 필요하며 새 패키지나 Whisper를 설치하지 않는다. 공용 audio-stt와 TTS 실행기에 의존하지 않는다.

```bash
python3 "$TOOL" '/실제/영상.mp4' \
  --output-dir '/실제/실행폴더/transcripts/p1' \
  --env-file '/실제/프로젝트/.env' --timestamps
```

일반 전사는 `--timestamps`를 생략해 단락 MD를 만든다. 영상 근거 추출에서는 시간 정보를 지정한다. 화자 라벨은 생성하지 않는다. 이름별 화자 구분 요청은 현재 미지원임을 알린다. 안 들리는 부분을 예상 정답·교안으로 채우거나 문장을 요약·정정하지 않는다. 중요한 입력 조건은 원본 화면·제공 발언과 대조한다.

원본에서 추출한 mono 16kHz PCM WAV만 전송한다. 검은 화면 MP4·원본 영상·교안은 업로드하지 않는다. `--chunk-seconds`는 0 초과 600 이하이며 기본 600이다. PCM/Base64 요청 크기를 제한하기 위해 실제 청크는 최대 450초다. 중간 무음과 원래 속도를 유지한다.

## 인증과 모델

- 모델은 `gemini-3.5-transcribe`로 고정하고 자동 대체하지 않는다.
- Vertex Express `https://aiplatform.googleapis.com/v1/publishers/google/models/gemini-3.5-transcribe:generateContent`와 `x-goog-api-key` 헤더를 사용한다.
- `generationConfig.audioTranscriptionConfig`는 `mode: VERBATIM`, `languageCodes: [ko-KR]`, `wordTimestamp: true|false`다. SMART 모드는 사용하지 않는다.
- 키는 `GOOGLE_API_KEY`, `GEMINI_API_KEY` 환경변수 우선, 이후 `--env-file`의 같은 이름 순으로 읽는다. CLI에서 파일을 생략하면 프로젝트 루트 `.env`를 찾는다. 캐시 재사용과 오디오 없는 영상은 키 없이 처리한다.
- 키·전체 환경·헤더·원시 HTTP 오류 본문을 출력하거나 영수증에 넣지 않는다. 키를 CLI 인자로 전달하지 않는다.

이 경로는 2026-10-17 기존 프로젝트 키로 한국어 VERBATIM과 단어별 시간 정보 HTTP 200을 확인했다. [Google 모델 문서](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/gemini/3-5-transcribe)는 기능 참고 자료이며 실제 접근 여부는 호출 결과로 판단한다.

## 결과와 복구

반환값의 `status`는 complete 또는 no_audio다. 완성본의 `md`, `json` 절대 경로와 해시를 사용한다. 파일·시간 기준은 [전사 스키마](references/transcription-schema.md)를 읽는다.

- 오디오 스트림이 없으면 no_audio를 반환하고 API를 호출하지 않는다. 조용하지만 오디오 스트림이 있는 파일과 구별한다.
- 완료 전사와 청크는 해시 검증 후 재사용한다. 원본·옵션 변경은 별도 지문 폴더로 처리한다. 훼손된 기존 결과를 덮어쓰지 않는다.
- 실패는 state.json에 안전한 코드로 기록한다. 같은 명령으로 성공한 청크를 재사용해 재개한다. 모든 청크 완료 전에는 MD를 전달하지 않는다.
- HTTP 429/500/502/503/504만 최대 3회 시도한다. 인증 오류·차단·잘린 응답·잘못된 시각은 실패한다. 타임아웃은 과금 여부가 불명확하므로 자동 재시도하지 않는다. 수동 재실행 시 중복 과금 가능성이 있다.
- 강제 종료로 `.lock`이 남으면 활성 프로세스가 없는지 확인한 뒤 그 실행의 잠금 파일만 제거한다. 정상/예외 종료는 자동 정리한다.
- 미디어 임시물은 실행 폴더 안에서 처리하고 예외 종료에도 정리한다. 청크 JSON·전사·state는 근거와 재개용으로 남긴다.

단어 시각은 근사값이며 시간 기능이 전사 정확도를 떨어뜨릴 수 있다. 실제 클럭 에지·프레임·배선 상태를 확정하거나 review.audio를 자동 승인하지 않는다. 반환문에는 숫자·띄어쓰기 정규화나 오인이 있을 수 있다.

전달 시 MD/JSON 링크, 전사·재사용·미확인 범위와 실패 여부를 알린다. 원본·기록.md·보고서는 수정하지 않으며 커밋·푸시는 별도 요청이 있을 때만 한다.

## 개발 검증

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s .claude/skills/logic-lab-stt/tests -v
```

실제 API 검증은 임시 합성 음성으로 최소한 수행한다. 사용자 촬영본 전체를 개발 테스트에 보내지 않는다.
