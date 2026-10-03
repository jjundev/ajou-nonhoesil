# 기존 export-hand-diagram --crop baseline

- 일자: 2026-10-01
- 작업 디렉터리: `/Users/hyunjun_macbook_pro/Documents/Univ/논회실`
- 입력: `/Users/hyunjun_macbook_pro/Downloads/논회실 mux_261001_152503.pdf`
- 원본: 2쪽, 각 1210 × 834 PDF pt.
- 코드와 스킬 변경 없이 기존 명령을 실행했다.
- `docs/superpowers`, 수동 JPEG, 이전 검증 결과는 읽지 않았다.

## 직접 읽은 파일

1. `.agents/skills/export-hand-diagram/SKILL.md`
2. `scripts/lab/export_hand_diagrams.py` (실행 후 크롭 동작 및 파일명 해석 확인)
3. 위 입력 PDF (PyMuPDF로 열고, 전체 페이지를 렌더링하여 눈으로 확인)
4. 아래 이번 실행 생성 PNG 4개 (view_image로 직접 열어 비교)

스크립트는 실행 과정에서 config/hand_grid/netlist_parser 모듈을 import하고 실험04 netlist를 파일명 결정에 이용한다. 명시한 입력 경로는 Downloads 아래이므로 기존 round 전사 파일을 연결하지 않는다. 이 실행에서 이전 검증 결과나 수동 JPEG를 별도로 조회하지 않았다.

## 실행 명령

```bash
cat .agents/skills/export-hand-diagram/SKILL.md
python3 -m scripts.lab.export_hand_diagrams 4 '/Users/hyunjun_macbook_pro/Downloads/논회실 mux_261001_152503.pdf' --crop --out output/validation/hand-diagram-crop/round00/baseline/
sed -n '1,260p' scripts/lab/export_hand_diagrams.py
sed -n '260,450p' scripts/lab/export_hand_diagrams.py
```

전체 원본 확인용 렌더링 및 크기/용량 조회:

```python
import fitz
from pathlib import Path
from PIL import Image
out=Path('output/validation/hand-diagram-crop/round00/baseline')
doc=fitz.open('/Users/hyunjun_macbook_pro/Downloads/논회실 mux_261001_152503.pdf')
for i,p in enumerate(doc):
    path=out/f'source-page-{i+1}.png'
    p.get_pixmap(dpi=110).save(str(path))
    print(path, p.rect)
for f in out.glob('*.png'):
    with Image.open(f) as im: print(f.name, im.size, f.stat().st_size)
```

view_image 도구로 아래 순서대로 4장을 직접 열었다: source-page-1.png, 실험04_1-1_손그림_4x1MUX.png, source-page-2.png, 실험04_2-1_손그림_1x4DMUX.png.

## 결과

명령은 exit code 0과 `[SUCCESS] 2개의 손그림 PNG 생성 완료`를 반환했다.

| 파일 | 픽셀 크기 | 바이트 | 용도 |
|---|---:|---:|---|
| 실험04_1-1_손그림_4x1MUX.png | 1817 × 2368 | 1958045 | 기존 --crop 결과 p1, 기본 300 DPI |
| 실험04_2-1_손그림_1x4DMUX.png | 1817 × 2368 | 1929099 | 기존 --crop 결과 p2, 기본 300 DPI |
| source-page-1.png | 1849 × 1275 | 586463 | 원본 전체 페이지 확인용 110 DPI |
| source-page-2.png | 1849 × 1275 | 582445 | 원본 전체 페이지 확인용 110 DPI |

## 육안 판정

**FAIL — 두 쪽 모두 브레드보드 하단이 잘린다.**

- p1 원본에는 60행 아래 최하단 홀 행들과 브레드보드 사각 외곽선의 바닥이 보인다. 크롭 결과에서는 하단 홀/외곽선이 이미지 아래 경계에서 잘려, 완전한 보드 본체를 보존하지 못한다. 빨강 하단 전원 배선은 보이지만 그 아래 보드 끝 여백과 최하단 행이 보존되지 않는다.
- p2 역시 원본의 브레드보드 최하단 홀들과 바닥 외곽선이 크롭 결과 아래 경계에서 잘린다.
- p2 오른쪽 상단 자필 제목은 완전히 제외되지 않고 `1x` 단편만 남는다. 원본 제목은 `1x4 DMUX 결선도`이다.
- 상단 전원 잭과 연결 배선, 주요 IC, 본체 내 배선, p1의 D0/D2/E 및 p2의 D 외부 주석은 보인다. p1 상단 + 표기는 위쪽 경계에 매우 가깝다.
- 따라서 파일 생성 성공/예상 픽셀 크기 일치만으로 크롭 성공을 판단할 수 없다.

코드 확인상 고정 템플릿 영역 X=[20,565], Y=[30,740]을 PDF 내 이미지 사각형으로 변환하여 크롭한다. 위 실패 판정은 이 코드 추론만으로 내리지 않고 원본 전체 페이지와 산출 PNG를 직접 비교한 결과다.
