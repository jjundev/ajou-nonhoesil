# Logic Lab STT Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 프로젝트 로컬 logic-lab-stt를 만들고 전사본 없는 실험영상의 자동 전사를 연결한다.

**Architecture:** 독립 Python 실행기가 음성 추출, Vertex Express 전사, 청크 캐시 및 MD/JSON 출력을 담당한다. 영상 근거 도구의 inspect CLI는 누락된 전사본을 자동 생성하고 manifest에 등록한다. 기존 inspect_run 함수의 기본은 네트워크 없는 조사로 유지해 기존 API 호출자를 보호한다.

**Tech Stack:** Python 3 표준 라이브러리, FFmpeg/ffprobe, unittest. 새 패키지 설치 없음.

**Spec:** 아래 확정 명세는 이 채팅의 사용자 승인 설계와 2026-10-17 실호출 검증을 보존한다.

## Global Constraints

- 공용 audio-stt는 수정하지 않는다. 원본·기록.md·보고서는 수정하지 않는다. 커밋·푸시는 하지 않는다.
- Vertex Express `https://aiplatform.googleapis.com/v1/publishers/google/models/gemini-3.5-transcribe:generateContent`, x-goog-api-key. 다른 모델/공급자로 자동 전환하지 않는다.
- GOOGLE_API_KEY / GEMINI_API_KEY 환경변수 우선, 명시 --env-file 또는 프로젝트 .env. 키·헤더·원시 오류 본문은 저장/출력하지 않는다.
- VERBATIM, languageCodes=[ko-KR]. 일반 전사는 timestamps=false, 근거 추출은 wordTimestamp=true. 자동 전사는 직접 청취가 아니다.
- 청크는 최대 600초, PCM mono 16kHz WAV. 요청 본문 제한 20 MiB를 넘기지 않는다. 음성만 전송하고 검은 화면 MP4는 만들지 않는다.
- 시간 기준은 첫 표시 프레임 0초, 오디오 첫 PTS 차이를 보존한다. 출력 JSON 단어 시각은 근사값이다.
- 성공 청크는 원본 SHA256+전처리/모델/옵션으로 식별하고 해시 검증 뒤 재사용. 실패 시 MD를 완성본으로 등록하지 않고 재개 가능 상태를 남긴다.
- inspect CLI는 기본 자동 전사. --no-transcribe로 명시 생략, --mode video 압축만 요청은 이 옵션 사용(모드만으로 압축/해석 의도를 구별하지 않는다).

## Review Focus

1. 늦게 시작하는 음성과 0이 아닌 컨테이너 PTS: 단어 시각에 정렬 오프셋을 정확히 한 번 반영(Task 1).
2. 429/5xx·인증 오류·빈/잘린 응답: 제한 재시도, 안전한 오류, 청크 누락을 성공으로 취급하지 않음(Task 1).
3. 중단/재실행·변경된 캐시: 성공 청크 재사용과 해시 불일치 거부, 설정 변경 시 별도 실행(Task 1).
4. 수동 전사와 자동 전사 혼합·오디오 스트림 없음: 수동 우선, 불필요 API 호출 없음(Task 2).
5. 자동 전사 실패 후 프레임 분석: manifest 유지, 명시 failed 상태·unknowns, audio review 미승인(Task 2).

---

## 확정 명세

새 스킬 `.claude/skills/logic-lab-stt/`와 `.agents/skills/logic-lab-stt` 상대 심볼릭 링크를 만든다. `scripts/transcribe.py`는 CLI와 import 가능한 `transcribe(source, output_dir, *, timestamps=False, env_file=None, transport=None, chunk_seconds=600) -> dict`를 제공한다. 출력은 콘텐츠 지문별 하위 폴더의 transcript.md, transcript.json, state.json, chunks/*.json이다. JSON 상태는 complete/no_audio/failed, 원본/시간기준/정책/해시/사용량을 기록한다. 미디어 임시물은 성공 여부와 무관하게 임시 디렉터리에서 정리한다. 기존 완성 출력은 해시 확인 후 재사용하고 훼손 시 덮어쓰지 않는다.

`video_evidence.py`는 `transcribe_run(manifest, env_file=None, transcriber=None) -> dict`를 제공하고, CLI inspect의 새 --env-file/--no-transcribe 및 재개용 transcribe MANIFEST 명령에서 호출한다. 자동 등록은 완성 MD/JSON만 sources에 추가하고 둘 다 기존 입력 무결성 검증에 포함한다. 실패 상태는 manifest.transcription[sid] 및 unknowns에 기록하고 조사/미리보기는 허용한다. 실패 전사의 종료 코드는 transcribe 명령 1, inspect는 manifest 경로를 유지하며 stderr로 알린다.

## Task 1: 독립 전사 실행기

**Files:** Create `.claude/skills/logic-lab-stt/scripts/transcribe.py`, `tests/test_transcribe.py`.

**Interfaces:** Produces 위 transcribe 함수, `make_transport(key, sleep=time.sleep)`, `load_key(env_file)`; transport는 JSON payload를 받아 JSON response 반환. 호출자에게는 status/path/sha256와 안전한 error만 노출.

- [x] Step 1: 실패 테스트 작성: 테스트 응답을 이용해 3청크 병합 시 원본 오프셋 유지, STOP 아닌 응답 거부, 성공 청크 재사용, source/options 변경 분리, 캐시 훼손 거부, 키 미노출, 429만 제한 재시도, 오디오 없음 호출 0회를 검증한다.
- [x] Step 2: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s .claude/skills/logic-lab-stt/tests -v`로 기능 부재 실패 확인.
- [x] Step 3: 위 인터페이스 구현. ffprobe 프레임 첫 PTS와 오디오 추출 PCM의 시작 기준을 계산하며 shell=False 인자 배열 사용. 원자적 JSON 저장, 응답 구조·시각 유효성 검사, 429/500/502/503/504에 최대 3회 시도.
- [x] Step 4: 같은 명령으로 통과 확인.

## Task 2: 영상 근거 추출 연결

**Files:** Modify `.claude/skills/extract-lab-video-evidence/scripts/video_evidence.py`; Create `tests/test_transcription.py`.

**Interfaces:** Consumes Task 1 transcribe; Produces 위 transcribe_run, CLI inspect 기본 자동 및 transcribe 재개 명령. 직접 Python inspect_run은 기존 시그니처 유지.

- [x] Step 1: 실패 테스트 작성: 혼합 수동/자동, 무음, 부분 실패와 재개, 원본/등록본 변조 거부, review.audio pending 유지, CLI --no-transcribe와 기본 자동을 검증한다.
- [x] Step 2: 새 테스트를 실행해 기능 부재 실패 확인.
- [x] Step 3: 연결 함수와 CLI 구현. source 항목을 순회하며 등록 전후 해시 대조, 자동 JSON도 transcript_metadata kind로 무결성 검증에 포함.
- [x] Step 4: 새 테스트와 기존 video_evidence 테스트 전체 통과 확인.

## Task 3: 스킬 문서·실호출·최종 검증

**Files:** Create 새 SKILL.md, agents/openai.yaml, references/transcription-schema.md 및 상대 링크. Modify 기존 SKILL.md와 references/evidence-schema.md.

**Interfaces:** Consumes CLI 및 결과 스키마. Produces 사용 가능한 스킬, 자동 전사 기본 및 압축 생략/실패 처리 설명.

- [x] Step 1: 새 스킬 문서와 기존 스킬 예제를 갱신한다. 기존 전사 MD 직접 제공은 선택 사항임을 명시한다.
- [x] Step 2: 두 스킬 quick_validate 및 CLI --help, git diff --check 실행.
- [x] Step 3: 임시 한국어 음성/영상으로 실제 새 실행기의 전사, timestamp 응답, CLI 자동 등록 및 캐시 재사용을 확인한다. 사용자의 실제 촬영본은 전송하지 않는다.
- [x] Step 4: 관련 테스트 전체 실행 및 변경 범위를 검토한다. 계획 체크박스를 갱신하고 결과를 전달한다.

## 실행 기록

- 사용자 요청에 구현까지 명시되어 있으므로 계획 승인 질문을 반복하지 않고 직접 실행한다.
- 모델·키·엔드포인트는 이전 턴의 실제 HTTP 200 전사/시간정보 응답으로 검증됨.

- Task 1: complete — 11개 전사 테스트 통과. PTS 공백 보존과 MD 원자적 발행은 리뷰에서 발견 후 RED→GREEN 회귀 테스트로 수정했다.
- Task 2: complete — 연결/기존 영상 추출 22개 테스트 통과. Python 조사 함수는 오프라인 유지, CLI는 자동 전사한다.
- Task 3: 기능/문서 완료 — 두 스킬 quick_validate 통과, 합성 한국어 영상으로 실제 CLI 자동 전사·manifest 등록·캐시 재사용·원본 해시·audio review 미승인 확인. 전체 저장소 테스트 최종 결과는 아래에 추가한다.
- Ruling: PCM 600초는 Base64 변환 후 20 MiB 요청 제한을 넘으므로 실제 최대 450초로 제한한다. 시각은 샘플 수와 PTS로 보존한다.
- Review: 독립 읽기 전용 검토에서 지적된 내부 오디오 PTS 공백과 중단된 MD 저장을 수정했다. 최종 전처리 정책은 lab-verbatim-pcm16-v2다.

- 최종 전체 테스트: 3404 passed, 1252 subtests passed, 9 skipped, 2 failed. 실패는 기존 breadboard-diagram 문서 40390B > 40000B 검사와 실험05 결선도 JSON 12개 재생성 불일치다. 해당 스킬/결선도/테스트는 이번 작업에서 수정하지 않았다. 전체 브라우저 테스트가 다시 쓴 추적 PNG 2개는 작업 시작의 HEAD 바이트로 복원했다.
- 최종 리뷰: 두 지적 사항 모두 해결됐으며 추가 지적 없음. 최종 v2 정책의 새 CLI 실제 호출에서도 한국어 전사/시간정보 및 재개 검증 통과.
