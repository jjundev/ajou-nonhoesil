# 격리 크롭 실행 기록

- 대상: 실험04, ambiguity/source.pdf 전체 2쪽. 원본·코드 변경 없음.
- 원본 전체 렌더: PyMuPDF Matrix(1.5,1.5), 각 1815×1251 px. 두 이미지 모두 view_image로 직접 확인.
- PDF 좌표: 각 page.rect=[0,0,1210,834]. x_pt=x_px×1210/1815, y_pt=y_px×834/1251. 계획에는 왼쪽·위 내림, 오른쪽·아래 올림으로 소수 둘째 자리까지 기록.
- 보드 외곽 판독: 전체 렌더에서 x=661..1169, y=190..940 px. 마지막 홀 아래 외곽 테두리까지 포함. 전원 단자 세 개/극성/연결선, 행 번호, 외부 입력 이름/화살표 별도 keep.
- 2% 여백은 계획에 넣지 않고 코드가 적용. board width=338.67 pt, margin=6.7734 pt. 페이지 경계 제한 없음.
- 애매한 항목: 1쪽 왼쪽 40~50행 높이 보라색 물음표. 직접 결선 표기인지 설명인지 확정 불가. 확대 detail-p001.png 확인 후에도 ambiguous 유지.
- 2쪽 우측 D 표기는 detail-p002.png에서 직접 결선 화살표로 확인.
- 실행: python3 -m scripts.lab.export_hand_diagrams 4 output/validation/hand-diagram-crop/ambiguity/source.pdf --crop --crop-plan output/validation/hand-diagram-crop/ambiguity/fresh/crop-plan.json --out output/validation/hand-diagram-crop/ambiguity/fresh
- 종료 코드 2. 1쪽 pending, 2쪽 300 DPI 최종 PNG 저장.
- 후보 include/exclude/boundaries 및 2쪽 PNG 모두 view_image로 열어 검토. 보드 전체 하단 외곽선, 모든 홀, 단자/극성/행 번호/외부 신호 보존 확인. 2쪽 우상단 제목 조각은 규칙상 허용.
- exclude 후보는 보존 요소 기준 2% 여백에 물음표 우측 미세 조각이 걸침. 임의로 지우거나 필수 여백 축소하지 않음. include 후보는 물음표 전체 보존.
- 사용자 질문 초안: 1쪽 보드 왼쪽 아래의 보라색 물음표를 결선도의 일부로 포함할까요, 검토 메모로 제외할까요? 파랑 경계가 포함, 주황 경계가 제외 후보입니다.
- 승인 전 1쪽 최종 PNG를 만들지 않음. 부모에게 후보를 반환하고 판단 대기.
- 실수: 존재하지 않는 일본어 철자 경로로 netlist rg를 한 번 시도해 실패. 이후 rg --files로 실제 경로 확인. 금지된 다른 validation, docs/superpowers, 사용자 JPEG는 읽지 않음.
