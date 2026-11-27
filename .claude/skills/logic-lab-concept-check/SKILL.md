---
name: logic-lab-concept-check
description: 논리회로실험의 확인문제·개념 퀴즈·즉시 채점 HTML을 기존 실험설명과 교안으로 만들 때 사용한다. /logic-lab-concept-check 실험09 또는 신규 논리회로실험 학습팩의 PDF 생성 직후에 실행한다.
---

# 논리회로실험 확인문제

실험 한 편에서 새로 배운 개념을 5~10분 안에 확인할 4지선다와 값 입력형 문항을 만든다. 단독 호출은 실험 번호 하나(`9`, `실험09`)를 받는다. 신규 학습팩에 연결할 때는 방금 PDF까지 생성한 실험 번호를 그대로 넘긴다.

공개 HTML은 `복습노트/실험NN/실험NN_확인문제.html`에 둔다. 근거와 검사 기록은 `.pack/자료_확인문제/`에 둔다. 한 화면에 한 문항을 표시하고, 힌트는 우측에서 기본으로 펼쳐진다. 채점 뒤 풀이에서 실험설명 토픽으로 이동한다. 같은 탭에서 풀이 링크를 따라갔다가 브라우저 뒤로 가기로 돌아오면 제출 답안·채점·푼 문제 표시를 복원한다. 마지막 응답에서 복기 창이 열리고 새로고침하면 답안이 초기화된다.

## 1. 준비와 저작

저장소 루트에서 실행한다. Playwright와 Chromium이 설치된 Python을 쓴다. 명령의 `RUN`은 아직 없는 고유 임시 실행 디렉터리 경로다. 필요하면 `--root`로 테스트용 저장소 루트를 지정한다.

```sh
S=.claude/skills/logic-lab-concept-check/scripts
python3 "$S/delivery.py" prepare 실험09 --run RUN
```

출력한 `SRC` 경로는 `RUN/복습노트/실험NN/.pack/자료_확인문제`다. 원고·브라우저 스크린샷과 풀이자에게 보일 사본을 RUN에 둔다. 학습팩이 없으면 해당 경로를 보고한다.

[문항 규칙](references/items.md)을 읽는다. 발행된 실험설명과 manifest의 토픽·교안 쪽을 대조한 뒤 `SRC/objectives.json`을 작성한다. 문항 작성자에게 그 목표와 근거를 넘겨 `SRC/items.json`을 작성하게 한다. 작성자는 메인과 별도 에이전트를 사용하거나 메인이 직접 맡을 수 있다. 교안과 노트의 상태·엣지·핀 극성이 어긋나면 원자료를 확인하고 조건이 확실한 문항만 채택한다.

```sh
python3 "$S/delivery.py" check 실험09 --run RUN
python3 "$S/delivery.py" build 실험09 --run RUN
```

템플릿은 `assets/review-template.html`의 자구알 스냅샷이다. 템플릿과 전용 CSS·JS의 출처 및 해시는 [SOURCE.md](assets/SOURCE.md)에 있다. 새로운 과목용 문구와 경로는 생성 단계에서 적용한다.

## 2. 블라인드 풀이

```sh
python3 "$S/blind.py" make SRC RUN/blind-r1.md
```

작성에 참여하지 않은 새 에이전트를 컨텍스트 상속 없이 띄운다. [풀이 지시](references/blind.md)와 블라인드 사본, 기존 실험설명 MD 경로를 준다. 원고, 기존 풀이장부, 생성된 HTML의 경로는 풀이자에게 제공하지 않는다.

```sh
python3 "$S/blind.py" record SRC RUN/blind-answers-r1.md SRC/blind-ledger.json --round 1
python3 "$S/blind.py" status SRC SRC/blind-ledger.json
```

오답·이의가 나오면 발문과 근거부터 다시 확인한다. 원고를 고치면 규칙 검사와 빌드를 다시 한다. 상태 검사에 누락·수정·답 불일치·이의·근거 누락으로 남은 모든 문항을 `make … --only q3,q7`로 뽑아 새 풀이자에게 보낸다. 세 차례까지 풀이하며, 남은 이의와 미검증 문항은 보고한다. 스스로 검산한 결과는 저작 검토로 기록한다.

## 3. 오프라인 검사와 발행

```sh
python3 "$S/browser_check.py" RUN/복습노트/실험09/실험09_확인문제.html \
  --src SRC --out SRC/browser.json --shots RUN/shots --serve-root RUN
python3 "$S/delivery.py" publish 실험09 --run RUN
```

발행 전에 1280×900·375×812의 밝은·어두운 화면을 실제로 열어 첫 문항, 힌트, 마지막 문항, 복기 창의 잘림과 겹침을 본다. 브라우저 검사는 객관식 채점·재시도, 입력형 허용답, 힌트 상태, 복기 복사, 링크와 실험설명 토픽 도착, 뒤로 가기 뒤 풀이 복원과 새로고침 뒤 초기화, 글꼴·KaTeX, 콘솔 오류와 가로 넘침을 확인한다. 원고를 고친 뒤에는 현재 HTML에 대한 검사 결과를 새로 받는다.

발행 명령은 블라인드 장부, 브라우저 네 조합, 현재 HTML과 학습팩 근거, 팩 배치를 검증한다. 실패하면 RUN에 초안을 두고 해당 실패와 보류 이유를 보고한다. 교체할 기존 확인문제가 있으면 발행 시 RUN에 백업한다. 보고에 HTML·근거 경로, 목표/문항/형식 수, 블라인드와 브라우저 결과, 보류나 백업 경로를 적는다.
