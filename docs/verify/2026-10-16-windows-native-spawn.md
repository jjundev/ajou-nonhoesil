# Windows 네이티브 spawn 검사 원인과 수정

대상: `tests/test_affected_trace.py`의 `os.spawnve` 검사 두 건. 병합 검증 당시 Python 3.14와 3.11에서 접근 위반으로 실패했다.

## 재현과 원인

- 추적기·pytest 없이 `os.spawnve(os.P_WAIT, sys.executable, [sys.executable, '-c', 'pass'], {})`만 실행해도 부모 Python이 `0xC0000005`로 종료했다.
- Windows Application 이벤트 1000의 오류 모듈은 `C:\Windows\System32\ucrtbase.dll` 10.0.22621.3593, 오프셋은 `0x54fe2`였다. 진단용 vectored exception handler에서도 같은 DLL과 오프셋을 확인했다.
- `spawnv`는 성공했다. `spawnve`는 빈 환경·변수 하나·상속 환경과 P_WAIT/P_NOWAIT 모두에서 충돌했다. 따라서 자식에게 추적 변수를 전달했는지는 충돌의 원인이 아니다.
- 같은 Python과 재현 코드를 `cmd.exe /d /c`를 거쳐 실행하면 성공했다. 직접 실행한 부모의 원시 Windows 환경 블록에는 `=C:` 같은 숨은 드라이브 현재 경로 항목이 없었다.
- 새 부모를 시작할 때 그 환경에 `=C:` 현재 경로 항목만 추가하면, 빈 환경·변수 하나·상속 환경을 받는 네이티브 자식이 각각 5회 연속 성공했다. 일반 환경 변수 하나를 추가하는 대조군은 계속 실패했다.
- 이는 [CPython 이슈 137934](https://github.com/python/cpython/issues/137934)에 보고된 Windows UCRT의 `construct_environment_block` 접근 위반과 일치한다. 해당 보고도 cmd를 거친 실행과 직접 실행의 차이를 기록한다. 이 호스트에서 숨은 드라이브 항목이 충돌을 가르는 조건인 것은 위 대조 실험으로 확인했다.

## 변경 범위

`_trace_run`이 테스트용 pytest 부모 프로세스를 만들 때 Windows 로컬 드라이브의 숨은 현재 경로 항목을 `setdefault`로 보충한다. 이 항목은 `os.environ` 대입이나 `os.putenv`가 거부하므로 `subprocess.run(env=...)`으로 부모 생성 시 전달한다.

실제 `os.spawnve` 호출, 자식에게 넘기는 빈 환경/상속 환경, 종료 코드 및 opaque 판정은 유지한다. 추적 환경을 상속하는 경우에는 JSON 기록 개수도 2개 이상인지 확인해 실제 자식의 기록 생성까지 검증한다. 추적기 구현·시스템 DLL·Python 설치는 수정하지 않는다. 기존 POSIX 전용 두 검사의 플랫폼 skip 조건도 유지한다.

## 검증

- 수정 전 Python 3.14 단독 파일: 1 failed, 21 passed, 2 skipped. 이전 실행에서는 같은 네이티브 두 검사 모두 실패했으며 발생 여부는 실행마다 달랐다.
- 수정 후 Python 3.14 단독 파일: **22 passed, 2 skipped**. JUnit: `tmp/windows-native-trace-fixed.xml`.
- 수정 후 Python 3.11 단독 파일: **22 passed, 2 skipped**. JUnit: `tmp/windows-native-trace-py311.xml`.
- 별도 read-only 코드 리뷰: 수정이 네이티브 API·빈 자식 환경·기존 assert를 유지하며 자식 기록 확인을 강화한 것을 확인했다. 이 보정은 드라이브 문자가 있는 로컬 임시 경로에 적용되며 UNC 임시 경로는 범위 밖이다.
- Python 3.14 전체 스위트 `python -m pytest tests/ -q --junitxml=tmp/windows-native-full-suite.xml`: **3395 passed, 7 skipped, 2 warnings, 1250 subtests passed**, 종료 코드 0, 505.57초. `--ignore` 없이 원래 네이티브 두 검사를 포함했다. 경고 두 건은 기존 Pillow `getdata` 사용의 deprecation 경고다.
- 전체 실행 중 다시 생성된 기존 navigation PNG 두 장은 실행 전 HEAD로 복원했다. 변경은 테스트 파일과 검증 문서 두 개뿐이다.
