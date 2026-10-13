---
name: export-standalone-note
description: 복습노트 HTML(실험설명·문제설명·기출문제·기출풀이)을 파일 하나로 합쳐 다운로드 폴더에 내보낸다. 실험이 여럿이면 실험별 폴더가 든 zip 하나로 낸다. 사용자가 "standalone", "한 파일로", "HTML만 복사해도 열리게", "다른 PC·태블릿에서 열 수 있게", "다운로드 폴더에 만들어줘" 등을 요청하거나 /export-standalone-note 를 호출할 때 사용한다.
---

# export-standalone-note

실험설명의 탐색 구조를 수정한 경우 먼저 원본 팩과 동봉 템플릿을 갱신·검사한 뒤 이 스킬로 기존 standalone을 다시 내보낸다. `aria-current` 등 속성이 붙은 sibling HTML 링크도 비링크 표시로 변환하고 내부 토픽 hash 링크는 보존한다. 남은 상대경로 참조(leftovers)는 0이어야 한다. 최신 실험설명 패널은 내부 목차만 표시하며, 자료 이동 영역을 내보내기 과정에서 다시 추가하지 않는다.

`복습노트/<실험NN>/` 의 HTML 은 숨김 폴더 `.pack/assets/`(KaTeX·Pretendard·widgets.js)와
`.pack/figures/` 를 상대경로로 부른다. 이 스킬은 그것들을 전부 인라인한 단일 파일을 만든다.
원본 `복습노트/` 는 건드리지 않는다.

## 실행

REPO 루트(scripts/lab/config.py 가 있는 곳)에서:

```bash
python3 -m scripts.lab.standalone_note 실험05                # 실험설명 1종
python3 -m scripts.lab.standalone_note 실험05 --kind all      # 4종(실험설명·기출문제·기출풀이·문제설명)
python3 -m scripts.lab.standalone_note 실험05 --kind 문제설명 # 문제설명 1종
python3 -m scripts.lab.standalone_note 실험01 실험05 --kind all   # 실험 2개 이상 → zip
python3 -m scripts.lab.standalone_note 실험01~05 --kind all  # 범위도 된다(실험01~실험05 도 같다)
python3 -m scripts.lab.standalone_note all --kind all         # 실험 폴더 전부 → zip
python3 -m scripts.lab.standalone_note 실험05 --out <폴더>    # 기본 ~/Downloads
```

- 주차로 말하면 실험 번호로 옮긴다. 종류를 말하지 않으면 실험설명, "전부·기출까지"면 `--kind all`.
  "테스트"·"다 확인"처럼 새 기능을 훑어보려는 말도 `--kind all` 로 읽고, 그렇게 했다고 보고한다.
- `python` 은 맥에 없을 수 있다. `python3` 를 쓴다(표준 라이브러리만 쓴다).
- 파일이 1개(실험 1개·종류 1개): `<출력폴더>/실험NN_<종류>.html`. 접미사는 없고 원본 노트와 이름이 같다. 같은 이름은 덮어쓴다.
- 파일이 2개 이상(실험 여러 개, 또는 한 실험의 `--kind all`): `<출력폴더>/논회실_복습노트_실험01~05.zip`,
  안은 `실험NN/실험NN_<종류>.html`. 실험이 하나면 `…_실험05.zip`, 연속이 아니면 `…_실험01_실험03.zip`.
  `--zip 이름.zip` 으로 이름을 바꾼다.
- 출력 폴더에 같은 이름의 낱개 HTML 이 이미 있으면 도구가 경고만 하고 지우지 않는다.
  남은 낱개는 사용자에게 알리고, 지우겠다고 하면 `rm` 대신 휴지통(`~/.Trash`)으로 옮긴다.
  옛 이름(`*_standalone.html`, `복습노트_standalone.zip`)도 같다.
- `--kind all` 은 없는 종류를 건너뛰고 이름을 출력한다. 종류를 하나 지정했는데 파일이 없으면 오류다.
- Windows 에서는 **압축을 푼 뒤** 연다. zip 미리보기에서 하나만 열면 형제 링크가 끊긴다.
- 같은 묶음에 있는 형제(예: 문제설명 → 실험설명#토픽)는 같은 폴더의 `실험NN_<종류>.html#토픽` 으로 이어진다. 묶음에 없으면 `<span>`.

## 확인과 보고

1. 출력 줄에 `남은 참조` 가 붙었거나 종료 코드가 1 이면 실패다. 목록을 그대로 보고하고 성공이라 하지 않는다.
2. zip 이면 마지막의 `zip 검사 통과 (파일 N개, 형제 링크 M개)` 줄을 확인한다.
   `zip 검사 실패` 가 나오면 목록(끊긴 링크·NFC·UTF-8 플래그·금지 문자)을 그대로 보고한다.
3. 렌더는 브라우저로 열어 수식·그림·글꼴을 본다. 한 편이면 충분하다(문제설명이 링크가 많아 좋다).
   - 브라우저 pane 이 `file://` 을 거부하면 zip 을 **scratchpad 에 풀어** 로컬 http 로 연다:
     `cd <풀린 폴더> && python3 -m http.server 8765 --bind 127.0.0.1` 후
     `http://127.0.0.1:8765/<퍼센트 인코딩한 경로>` 로 이동한다.
   - 열면 `.katex` 개수·`.katex-error` 0·깨진 `img` 0·`document.fonts.check('16px Pretendard')`·
     형제 링크 `fetch` 가 200 인지 본다. 끝나면 서버를 내리고 풀어 둔 폴더를 지운다.
   - http 확인은 `file://` 더블클릭과 Windows 실기를 **대신하지 못한다.** 보고에 "더블클릭·Windows 미확인" 이라고 쓰고 사용자에게 부탁한다.
4. 보고는 경로·크기·남은 참조 수·zip 검사·낱개 경고 유무·렌더 확인 여부(어느 방법으로, 몇 편) 한 줄씩.

## 알아둘 것

- 같은 묶음에 없는 형제 노트로 가던 링크는 `<span>` 이 된다(단일 파일에서는 열 수 없다).
- zip 이름은 NFC·UTF-8 플래그로 쓴다(맥 NFD 이름이 Windows 에서 깨지는 것을 막는다). Windows 실기 확인은 못 했다 — 구조 검사로 대신한다.
- `defer` 스크립트(KaTeX)는 `</body>` 앞으로 옮겨 순서를 지킨다. 헤더에 그대로 인라인하면 수식이 렌더되지 않는다.
- 글꼴은 Pretendard 400~800 의 woff2 만 넣는다. 결과는 약 6MB.
