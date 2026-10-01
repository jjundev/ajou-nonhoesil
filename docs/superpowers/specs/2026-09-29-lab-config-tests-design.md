# 논리회로실험 교안 후보 테스트 수정 설계

## 목표

Windows에서 실패하는 `tests/test_lab_config.py`의 테스트 가정만 최소 수정한다. 배포본 → 보고서 폴더 사본 → 과거 교안의 기존 후보 우선순위는 유지한다.

## 확인된 원인

- `archive_candidate()`가 `str(Path)`를 POSIX 슬래시 상수와 비교해 Windows에서 후보를 찾지 못한다.
- `ExperimentBaseTest.test_기반이_두_입구_전부에_적용된다`도 같은 방식으로 사본 후보를 놓친다.
- `TestManualCandidates.test_파일_이름은_0_을_채우지_않는다`는 배포본이 없는 목록을 가정하지만, 실제 배포본이 있으면 `manual_candidates(4)`가 그것을 맨 앞에 둔다.
- 재현: `python -m pytest -p no:cacheprovider -n0 tests/test_lab_config.py -q` → 14 failed, 99 passed. 아카이브 PDF 10개는 모두 존재한다.

## 결정된 동작

- 아카이브와 보고서 사본은 문자열 접두사가 아니라 `Path`의 부모 경로로 식별한다.
- 파일명과 폴더명 규칙 테스트는 배포본 없는 임시 루트를 전달해 입력을 통제하고, 두 후보의 정확한 경로와 순서를 확인한다.
- 배포본이 존재하는 경우의 우선순위는 기존 `TestDistributedManual.test_배포본이_주차_폴더_사본보다_먼저다`로 검증한다.
- `scripts/lab/config.py`, 원본 자료, 학습팩 브랜치는 수정하지 않는다.
- macOS에서 직접 실행하지 않았다면 macOS 검증 완료라고 주장하지 않는다.

## 범위와 검증

수정 파일은 `tests/test_lab_config.py` 하나다. 변경 뒤 다음을 실행하고 남은 실패가 있으면 이름과 원인을 보고한다.

```powershell
python -m pytest -n0 tests/test_lab_config.py -q
python -m pytest -n0 tests/test_lab_config.py tests/test_lab_validate.py tests/test_skill_docs.py -q
```
