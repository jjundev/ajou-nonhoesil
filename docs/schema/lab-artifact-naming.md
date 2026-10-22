# 실험 산출물 파일명

실험07부터 배포·열람용 문서는 `실험NN_실험_제목_산출물종류.확장자`로 만든다.
번호는 두 자리, 제목은 `체크리스트/명세.md`의 `title`이며 공백은 `_`로 바꾼다.
문서 안에 표시하는 제목은 기존 `config.document_title`을 유지한다.

생성과 조회 모두 `scripts.lab.config.artifact_path`를 사용한다. 실험01~06은
기존 이름과 폴더를 그대로 반환하므로 새 이름을 직접 조립하거나 옛 이름으로 fallback하지 않는다.

```python
from pathlib import Path
from scripts.lab import config

exp = Path(config.experiment_dir(7))
html = config.artifact_path(exp, '체크리스트', '.html')
pdf = config.artifact_path(exp, '체크리스트')
record = config.artifact_path(exp, '기록', '.md')
report = config.artifact_path(exp, '예비보고서', '.md')
cover = config.artifact_path(exp, '예비보고서표지')
handout = config.artifact_path(exp, '손그림모사')
```

| 종류 | 폴더 | 실험07 예시 |
|---|---|---|
| 체크리스트 | 체크리스트/ | 실험07_Shift_Register_체크리스트.html · .pdf |
| 기록 | 체크리스트/ | 실험07_Shift_Register_기록.md |
| 예비보고서·결과보고서 MD | output/ | 실험07_Shift_Register_예비보고서.md |
| 최종 제출본 PDF | 실험 폴더 바로 아래 | 실험07_Shift_Register_예비보고서.pdf |
| 예비보고서표지·결과보고서표지 | output/ | 실험07_Shift_Register_예비보고서표지.html · .pdf |
| 손그림모사·부품그리기·따라그리기 | 결선도/팀원전달용/ | 실험07_Shift_Register_손그림모사.pdf |
| 예상결과 HTML | output/ | 실험07_Shift_Register_예상결과.html |

`명세.md`, `netlist.md`, 배치 코드, 회로/단계 PNG와 JSON, 사진, 검토 라운드,
노션 baseline 및 되읽기 이력은 내부 자료이므로 이름을 유지한다. 이력의 원본 파일 참조는
바뀐 이름으로 갱신한다. `기록_최적화결선도.md` 같은 내부 검토 메모도 이름을 유지한다.

이름을 옮길 때 목적지가 이미 있으면 덮어쓰지 않는다. 기존 산출물은 재생성하지 않고
이름만 바꾸며, 본문 안에 실제로 변경된 파일을 가리키는 링크가 있을 때만 해당 링크를 고친다.
작성된 기록의 실측값·메모 및 PDF 스트림은 보존한다.

노션 업로드 이력의 `source`는 새 보고서 파일명을 가리킨다. 기존 baseline·되읽기 파일은
이름을 유지하고, 이름 변경 전 원본 파일명을 해당 레코드의 `history_source`에 보존한다.
조회·복구·비교는 `notion.history_path(output_dir, record)` 및 `baseline=False`를 사용한다.
새 업로드는 `history_source`가 없으므로 현재 `source`를 기준으로 별도 버전 이력을 만든다.
