# Fresh 실행 기록

격리 지시 준수: 지정 원본 PDF, 스킬/참조, 추출 코드/크롭 코드, netlist만 직접 읽었다. 금지된 대화 기록, docs/superpowers, 수동 crop JPEG, 이전 validation, 평가 결과는 읽지 않았다. netlist 전체 cat 출력은 도구 출력 한도로 일부 잘렸으나 C1/C2 파일명과 회로명은 확인했다. 코드 및 스킬 수정 없음.

## 명령과 시각 판독

1. `cat .claude/skills/export-hand-diagram/SKILL.md`
2. `cat .claude/skills/export-hand-diagram/references/crop-plan.md`; `rg --files scripts/lab | rg 'export_hand|crop'`; `rg --files 보고서/실험04 | rg netlist`
3. `cat scripts/lab/export_hand_diagrams.py`; `cat 보고서/실험04/결선도/netlist.md`
4. Python fitz로 원본 모든 페이지를 Matrix(1.5,1.5) PNG 렌더. page.rect=(0,0,1210,834), PNG 1815×1251. full-p001/full-p002 모두 view_image로 열었다.
5. 각 페이지 top=(350,0,1100,190), bottom=(350,600,900,720), left=(350,125,475,630), right=(750,125,1100,630) PDF pt clip을 Matrix(2,2)로 렌더. 8장 모두 view_image로 직접 열었다.
6. full-p001/full-p002를 다시 view_image로 열어 외부 표기 누락 대조.
7. `sed -n '1,260p' scripts/lab/hand_crop.py`
8. 시각 판독 좌표로 crop-plan.json 작성. pt=pixel/1.5 (전체 렌더) 또는 clip 시작점+pixel/2 (확대 렌더). 보드 외곽 x440.5..779, y127..626. 모든 외곽과 하단 끝을 보고 정했으며 자동색상/고정 템플릿 판독 없음. 좌표는 시각 측정 약 1 pt 정밀도. 미리 여백을 넣지 않았으며 코드가 본체 너비 338.5 pt의 2%=6.77 pt를 적용한다.
9. `python3 -m scripts.lab.export_hand_diagrams 4 '/Users/hyunjun_macbook_pro/Downloads/논회실 mux_261001_152503.pdf' --crop --crop-plan output/validation/hand-diagram-crop/round02/fresh/crop-plan.json --out output/validation/hand-diagram-crop/round02/fresh`
10. CLI 종료 0, 두 장 saved. 보고서 box를 원본 전체 렌더에 PIL ImageDraw.rectangle로 겹쳐 boundaries-p001/p002 생성.
11. 최종 PNG 두 장 및 경계 미리보기 두 장 모두 view_image로 확인. 단자 3개, 극성, 급전선, 외부 D0/D2/E 및 D, 양측 1~60 행 번호/화살표, 마지막 홀, 하단 외곽선 보존. 바깥에 남은 직접 결선 표기 없음. 2쪽 오른쪽 위 제목 '1x4' 일부는 crop 영역에 걸쳐 남음: 스킬에서 허용하므로 덧칠하거나 crop을 넓히지 않았다.

## 외부 필기 누락 확인 표

|페이지|위치|필기|판정|이유|
|---|---|---|---|---|
|1|위|빨강 +, 파랑 − 및 단자 급전선|keep|전원 극성과 실제 배선|
|1|위/오른쪽|1-1, 4x1 MUX 결선도|excluded|회로 제목으로 명확하게 읽힘|
|1|왼쪽|D0와 화살표, D2와 화살표|keep|보드 입력선 시작점 지시|
|1|오른쪽|E와 화살표|keep|입력선 시작점 지시|
|1|아래|외부 손필기 없음|없음|확대 이미지 확인|
|1|양측|행 번호 1/10/20/30/40/50/60와 화살표|keep|판형 행 번호 보존 규칙|
|1|위/아래|구분선, [브레드보드 실제도 1]|excluded|인쇄 판형 캡션|
|2|위|빨강 (+), 파랑 (−) 및 단자 급전선|keep|전원 극성과 실제 배선|
|2|위/오른쪽|2-1, 1x4 DMUX 결선도|excluded|회로 제목으로 명확하게 읽힘|
|2|왼쪽|외부 손필기 없음|없음|확대 이미지 확인|
|2|오른쪽|D와 화살표|keep|보드 입력선 시작점 지시|
|2|아래|외부 손필기 없음|없음|확대 이미지 확인|
|2|양측|행 번호 1/10/20/30/40/50/60와 화살표|keep|판형 행 번호 보존 규칙|
|2|위/아래|구분선, [브레드보드 실제도 1]|excluded|인쇄 판형 캡션|

ambiguous: 두 페이지 모두 없음. pending 없음. margin_clipped: 두 페이지 모두 false.

## 직접 읽은 파일

- .claude/skills/export-hand-diagram/SKILL.md
- .claude/skills/export-hand-diagram/references/crop-plan.md
- scripts/lab/export_hand_diagrams.py
- scripts/lab/hand_crop.py
- 보고서/실험04/결선도/netlist.md
- /Users/hyunjun_macbook_pro/Downloads/논회실 mux_261001_152503.pdf
