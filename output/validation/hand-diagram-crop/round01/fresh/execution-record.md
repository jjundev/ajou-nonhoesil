# Fresh crop 실행 기록

작업 루트: `/Users/hyunjun_macbook_pro/.codex/worktrees/hand-diagram-crop/논회실`
원본: `/Users/hyunjun_macbook_pro/Downloads/논회실 mux_261001_152503.pdf`
원본 SHA-256: `c6139e2a6ba5852b290b2c4e2aad3e64baa8b355b27326d082f803044ebbe4e7`

## 직접 읽은 파일

- `.claude/skills/export-hand-diagram/SKILL.md`
- `.claude/skills/export-hand-diagram/references/crop-plan.md`
- `scripts/lab/export_hand_diagrams.py`
- `scripts/lab/hand_crop.py`
- `보고서/실험04/결선도/netlist.md` (출력 길이 제한으로 일부 생략된 본문 및 회로 메타데이터 rg 결과)
- 지정 원본 PDF 2쪽
- 이번 실행에서 생성한 full/detail/final PNG와 crop-report.json

과거 대화, docs/superpowers, 수동 crop JPEG, 다른 validation 출력, 평가 보고서는 읽지 않았다. 코드·스킬은 수정하지 않았다. 실행 모듈이 config/hand_grid/hand_crop/netlist_parser를 import하고 해당 설정을 읽는 것은 실행 의존성이다.

## 실행

1. `cat .claude/skills/export-hand-diagram/SKILL.md`
2. `cat .claude/skills/export-hand-diagram/references/crop-plan.md`
3. `rg --files scripts/lab | rg 'export_hand|config'` 및 `rg --files | rg '실험04/.*/netlist.md$'`
4. `cat scripts/lab/export_hand_diagrams.py` 및 `cat 보고서/실험04/결선도/netlist.md`
5. 출력 폴더를 만들고 PyMuPDF `page.get_pixmap(matrix=fitz.Matrix(1.5,1.5))`로 2쪽 전체를 `full-p001.png`, `full-p002.png`로 렌더했다.
6. 원본 확대: 각 쪽 `fitz.Matrix(3,3)`와 clip pt 좌표 top=(395,25,835,230), bottom=(395,560,820,675), signal=(390,180,830,410)로 detail PNG 6개를 생성했다.
7. `sed -n '1,240p' scripts/lab/hand_crop.py` 및 `rg -n '^# C|^- (item|diagram):' 보고서/실험04/결선도/netlist.md`
8. 전체 렌더에서 측정한 픽셀 경계를 1.5로 나눠 pt로 기록한 `crop-plan.json`을 작성했다. 원본 전체 렌더 크기는 1815×1251, PDF page.rect는 [0,0,1210,834]다. x_pt=x_px×1210/1815, y_pt=y_px×834/1251. plan에는 2% 여백을 넣지 않았다.
9. 아래 명령을 실행했다(종료 코드 0).

```bash
python3 -m scripts.lab.export_hand_diagrams 4 '/Users/hyunjun_macbook_pro/Downloads/논회실 mux_261001_152503.pdf' --crop --crop-plan output/validation/hand-diagram-crop/round01/fresh/crop-plan.json --out output/validation/hand-diagram-crop/round01/fresh
```

10. 최종 PNG 2개를 view_image로 직접 열어 원본과 비교하고, crop-report.json과 PIL 크기·파일 바이트를 확인했다.

## 판단 및 직접 이미지 확인

전체 페이지 2개, 확대 detail 6개, 최종 PNG 2개를 view_image로 열었다. 보드의 마지막 홀 아래 외곽선까지 보드 본체로 잡았다. 외곽은 전체 렌더 픽셀 기준 [661,190,1169,940]이며, 사용하지 않은 하단 영역도 유지했다. 보드 너비 338.6667 pt의 2%=6.7733 pt를 코드가 각 방향에 한 번씩 붙였다.

1쪽: 전원 단자 세 개, 위쪽 +/−와 전원선, 양쪽 행 번호·화살표, 보드 바깥 D0·D2·E와 연결 화살표를 보존했다. S0·S1·D1·D3 및 IC 핀 번호는 보드 내부에 있어 그대로 남는다. 오른쪽 1-1/4×1 MUX 결선도는 제목으로 제외했다.

2쪽: 전원 단자 세 개, 단자 아래 (+)/(−)와 전원선, 양쪽 행 번호·화살표, 오른쪽 D와 연결 화살표를 보존했다. 내부 S0·S1·Y0~Y3·IC 핀 번호도 남는다. 오른쪽 2-1/1×4 DMUX 결선도는 제목이므로 경계를 넓히지 않았다. 크롭 범위 안에 걸친 제목 조각은 스킬 규칙대로 지우지 않았다.

두 쪽 모두 상하 판형 구분선과 하단 브레드보드 실제도 캡션을 제외했다. 직접 결선 표기와 제목 구분이 명확하여 ambiguous는 비었다. pending은 없으며, 페이지 경계로 제한된 여백도 없다. 이 작업은 크롭 검증이며 회로 정확성을 검토한 것은 아니다.

## 생성 파일

- `실험04_1-1_손그림_4x1MUX.png`: 1758×2524 px, 1,995,909 bytes, 300 DPI 렌더 후 크롭
- `실험04_2-1_손그림_1x4DMUX.png`: 1696×2444 px, 1,958,979 bytes, 300 DPI 렌더 후 크롭
- `crop-plan.json`, `crop-report.json`, `execution-record.md`
- `full-p001.png`, `full-p002.png`
- `detail-p001-top.png`, `detail-p001-bottom.png`, `detail-p001-signal.png`
- `detail-p002-top.png`, `detail-p002-bottom.png`, `detail-p002-signal.png`

보고서 삽입 상대 경로(보고서/실험04/예비보고서.md 기준):
`../../output/validation/hand-diagram-crop/round01/fresh/실험04_1-1_손그림_4x1MUX.png`
`../../output/validation/hand-diagram-crop/round01/fresh/실험04_2-1_손그림_1x4DMUX.png`

## 현재 코드 최종 재실행

부모 에이전트가 부분 페이지 파일명/다중 실험 보고서 처리만 수정했다고 알린 후 위와 동일한 CLI를 다시 실행했다. 종료 코드 0. 전체 2쪽 파일명·크기는 유지되었다. `final-hashes.json`에 최종 PNG SHA-256·크기·용량을 기록했다. 소스 파일을 추가로 읽지는 않았다.
