# hand-crop/v1

## 좌표

PDF `page.rect`와 **회전 적용된 전체 페이지 렌더 이미지**를 기준으로 한다. 렌더 크기가 W×H라면:

- x_pt = page.rect.x0 + x_px × page.rect.width / W
- y_pt = page.rect.y0 + y_px × page.rect.height / H

box는 `[x0,y0,x1,y1]`, 유한한 수이며 페이지 안의 양수 너비·높이를 가져야 한다. 회전 전 `get_drawings()`/이미지 삽입 좌표를 쓸 경우 `page.rotation_matrix`로 같은 좌표계에 옮긴다. 원본에 배치된 판형 이미지 크기를 PDF 페이지 크기로 착각하지 않는다.

보드 본체 실제 테두리와 보존 요소 끝을 기록한다. 여백은 코드가 한 번만 적용한다. 픽셀 변환은 바깥 방향으로 반올림한다. 경계를 측정한 렌더 크기와 이유를 실행 기록에 남긴다.

## 작성 예시 (합성 좌표)

```python
import hashlib, json
from pathlib import Path
plan = {
    'schema': 'hand-crop/v1',
    'source_sha256': hashlib.sha256(Path(pdf_path).read_bytes()).hexdigest(),
    'pages': [{
        'page': 1,
        'page_rect': [0, 0, 600, 800],
        'board_box': [100, 200, 500, 700],
        'keep': [
            {'label': '전원 단자·극성·배선', 'box': [250, 80, 400, 200]},
            {'label': '좌측 외부 신호와 화살표', 'box': [40, 300, 100, 340]},
            {'label': '행 번호', 'box': [75, 200, 525, 690]},
        ],
        'excluded': [{'label': '우측 회로 제목', 'reason': '결선 표기가 아닌 제목'}],
        'ambiguous': []
    }]
}
Path(plan_path).write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding='utf-8')
```

예시 좌표는 실제 PDF에 재사용하지 않는다. 모든 선택 페이지를 기록해야 한다. 중복 페이지/없는 페이지/원본 해시 또는 크기 불일치는 오류다. `keep`, `excluded`, `ambiguous`는 빈 배열이어도 필수다.

## 애매한 필기

```json
{"label":"보드 밖 필기", "box":[530,300,560,340], "reason":"신호 이름인지 설명인지 판독 불가"}
```

위 객체를 해당 페이지 `ambiguous` 배열에 넣는다. 코드는 그 페이지 최종 PNG를 만들지 않고 다음 후보를 만든다:

- `candidates/p001-exclude.png`: ambiguous 없이 크롭
- `candidates/p001-include.png`: ambiguous 전부 포함
- `candidates/p001-boundaries.png`: 전체 페이지에 주황(제외)/파랑(포함) 경계

사용자 결정 전 ambiguous를 비우지 않는다. 기존 정본이 있어도 pending은 새 정본을 의미하지 않는다. 사용자 결정에 따라 keep 또는 excluded로 옮기고 그 페이지를 다시 실행한다.
