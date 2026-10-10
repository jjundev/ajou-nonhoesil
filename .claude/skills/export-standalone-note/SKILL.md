---
name: export-standalone-note
description: 복습노트 HTML(실험설명·기출문제·기출풀이)을 파일 하나로 합쳐 다운로드 폴더에 내보낸다. 사용자가 "standalone", "한 파일로", "HTML만 복사해도 열리게", "다른 PC·태블릿에서 열 수 있게", "다운로드 폴더에 만들어줘" 등을 요청하거나 /export-standalone-note 를 호출할 때 사용한다.
---

# export-standalone-note

`복습노트/<실험NN>/` 의 HTML 은 `자료/assets/`(KaTeX·Pretendard·widgets.js)와
`자료/figures/` 를 상대경로로 부른다. 이 스킬은 그것들을 전부 인라인한 단일 파일을 만든다.
원본 `복습노트/` 는 건드리지 않는다.

## 실행

REPO 루트(scripts/lab/config.py 가 있는 곳)에서:

```powershell
python -m scripts.lab.standalone_note 실험05                 # 실험설명 1종
python -m scripts.lab.standalone_note 실험05 --kind all      # 3종
python -m scripts.lab.standalone_note 실험05 --out <폴더>    # 기본 ~/Downloads
```

- 주차로 말하면 실험 번호로 옮긴다. 종류를 말하지 않으면 실험설명, "전부·기출까지"면 `--kind all`.
- 출력: `<출력폴더>/실험NN_<종류>_standalone.html`. 같은 이름은 덮어쓴다.

## 확인과 보고

1. 출력 줄에 `남은 참조` 가 붙었거나 종료 코드가 1 이면 실패다. 목록을 그대로 보고하고 성공이라 하지 않는다.
2. 렌더는 브라우저로 열어 수식·그림·글꼴을 본다. 브라우저 pane 이 file:// 을 거부하면
   **"렌더 미확인"** 이라고 쓰고, 사용자에게 더블클릭 확인을 부탁한다.
3. 보고는 경로·크기·남은 참조 수·렌더 확인 여부 한 줄씩.

## 알아둘 것

- 형제 노트로 가던 상단 링크는 `<span>` 이 된다(단일 파일에서는 열 수 없다).
- `defer` 스크립트(KaTeX)는 `</body>` 앞으로 옮겨 순서를 지킨다. 헤더에 그대로 인라인하면 수식이 렌더되지 않는다.
- 글꼴은 Pretendard 400~800 의 woff2 만 넣는다. 결과는 약 6MB.
