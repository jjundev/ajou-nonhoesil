# 원본 화면과 작성 계약

`prepare`는 입력 PDF와 workbook MD를 SHA256으로 동결하고 각 페이지의 `layers/candidates.json`, `candidate.svg`, `native.png`를 만든다. 후보 목록은 전체 페이지의 원본 그림이고 작성 영역은 아직 없다. `source/pair.json`과 동결 MD를 읽고 PDF 화면을 직접 확인한다.

`source/map.json`에 중앙 풀이만 들어가는 `work_bbox: [x0,y0,x1,y1]`를 PDF point 좌표로 작성한다. `steps: [{id,glyph_ids,shape_ids}]`는 원본 단계 순서, 각 glyph_ids는 사람이 읽는 순서다. 두 단에서는 왼쪽 위→왼쪽 아래→오른쪽 위→오른쪽 아래 순서를 원문과 대조한다. 분수의 분자/분모, 첨자와 병렬 기호의 순서를 개별 검토한다. 좌표 정렬만으로 읽기 순서를 승인하지 않는다. 마지막 단계의 id를 `answer_step_id`로 적는다. 짧은 발화와 작성 단위를 원하면 원본 단계를 작은 연속 단위로 나눈다.

범위 안의 모든 글자와 풀이 도형을 한 번씩 포함한다. 회로, 조건, Hint, 격자 이미지는 지정하지 않는다. 도형 후보의 `unclassified`는 직접 확인 후 `fraction_bar|radical_bar|step_badge|answer_box|bullet` 중 해당 값을 지정한다. 근호와 장식 선은 실제 의미를 보고 분류한다. 이미지 안에 풀이가 있으면 중단한다. 이미지 배경 전체에 걸치는 격자는 그대로 둔다. 기존 SVG의 path, transform, clipPath, defs와 data-text를 편집하지 않는다.

`extract` 후 `layers/layers.json`이 확정되며 gate는 원본/빈 화면/삭제 대조/일부 공개/완성 PNG를 만든다. 완성 픽셀 차이, 숨김 대조 차이, 비대상 변경이 모두 0이어야 한다. `native.png`와 원본 SVG PNG는 서로 다른 렌더러이므로 직접 시각 검토한다. 그림 교체로 완성 오류를 감추지 않는다.

`source/manifest.json`: schema_version=1, problem_id, 자연스러운 한국어 title, segments, reveal_order, shape_anchors, cameras. segments의 id는 영문으로 시작하는 ASCII 안전 문자열, kind는 problem/reason/write/check/summary, step_id와 text/source_refs가 있다. 첫 segment는 problem이고 각 mapped step에 write 하나씩 순서대로 둔다. reveal_order는 PageMap glyph_ids를 순서대로 합친 값이다. shape_anchors는 shape ID→같은 단계 glyph ID다. cameras는 `{at_frame,viewbox:[x0,y0,width,height]}`, 빈 배열이면 측정 타이밍과 원본 글자 크기로 기본 확대를 만든다.

`source/coverage.json`은 `{status,input_hash,pdf_md_agree,rows:[{step_id,source_refs,pdf_text,md_text,meaning_review}]}`다. PDF의 원문을 보존하고 MD와 수식/부호/단위/값을 의미로 대조한다. MD가 없으면 md_text=null, meaning_review에 PDF만으로 검토한 범위를 적는다. 충돌은 pdf_md_agree=false로 기록하고 그 문항을 중단한다. `source/circuit-review.json`은 `{status,input_hash,steps:[{step_id,assumptions,equations,units,evidence}]}`로 노드/접지/반회로/부호/계산 검산의 근거를 작성한다. 모양 검사 성공은 의미 검토가 아니다.

완성된 문서에 `content_fingerprint(manifest,layers,coverage)`를 구해 두 검토의 input_hash로 넣고 status=passed를 지정한다. coverage의 status/input_hash만 지문에서 제외한다. `check`가 현재 지문을 검증한 다음에만 TTS를 실행한다. 원문은 PDF가 기준이며 MD의 최신 풀이를 조용히 대체하지 않는다.

구현 검증에서 확대 기준을 단계 본문 글자의 대표 높이 26px로 적용했다. 등호·분수선·첨자는 본문과의 원래 비율을 유지한다. 납작한 기호 하나가 전체 문장을 과도하게 확대하지 않도록 단계별 배율을 고정하며, 필요한 경우 명시적 카메라로 작은 첨자를 확인한다.

ID의 0 padding은 문항 대응에서 숫자로 비교하되 E10.04 같은 원래 전체 ID를 보존한다. 날짜 범위의 동일 ID는 고정 제목/페이지 번호/footer를 제외한 원본 본문 그림으로 비교한다. 회로·조건·풀이·Hint·본문 배치가 다르면 충돌이다. 모든 날짜의 동결 PDF/MD 대응은 PagePair.sources에 남는다. prepare는 실패 문항을 batch에 기록하면서 다른 문항을 계속 준비한다. 실패한 export는 같은 동결 run에서 extract로 재시도할 수 있다. 선택하지 않은 문항 때문에 선택 문항을 중단하지 않는다.

## 회로 포커스와 추가 표시

`source/focus.json`은 선택적인 연출 입력이다. schema_version=1, 답안 PDF의 source_sha256, regions와 cues를 작성한다. region은 실제 PDF point의 bbox이며 페이지 안, work_bbox보다 위에 있어야 한다. 회로 이름·소자 값·전원·주요 노드를 모두 포함한다. cue의 segment_id는 reason/check, target은 region ID다. manifest.cameras와 혼용하지 않는다. 그림이 없으면 이 파일을 만들지 않는다.

`source/annotations.json`은 같은 해시와 items를 가진다. 각 item은 안전한 ASCII id, region_id, segment_id, kind, geometry, source_refs, meaning_notes를 가진다. 해당 segment/region cue가 필수다. arrow/underline은 from/to 좌표, ellipse는 bbox, label은 text/origin baseline/font_size_pt를 가진 runs를 받는다. 첨자는 작은 별도 run으로 표현한다. label은 비공백 최대 24자이며 LaTeX·줄바꿈·없는 글꼴 문자를 거부한다. 원문에 없는 계산을 추가하지 않는다.

기본 color는 #1565C0, 도형 선은 화면상 3px다. 원본 기호를 덮지 않도록 native PNG와 실제 확대 화면에서 위치·방향·단위를 확인한다. 새 주석은 원본 SVG를 수정하지 않고 조립본의 teaching-annotations 그룹으로 추가한다. 글자는 로컬 Pretendard 윤곽으로 동결한다. 주석은 최종 원본 전체 화면 직전까지 누적된다. hide_at을 {segment_id,offset_frames}로 지정하면 작성 완료 후 일찍 숨길 수 있다.

## Spatial writing units

Keep `glyph_ids`, `shape_ids`, and coverage PDF text in original source order.
For pencil mode author `writing_units` in each step: safe unique `id`, `line_id`,
`column_id`, `chunk_id`, finite increasing horizontal `band: [x0,x1]`,
`glyph_ids`, `shape_ids`, and boolean `camera_break_before`. Units are the reveal
order. Split fraction/radical targets across adjacent bands; every target bbox
must be fully covered once (0.01pt tolerance). Assign zero-area spaces once.
Change lines when switching columns; never return to a completed line. Changing
chunks within a line requires `camera_break_before: true`. Inspect original
geometry; do not infer reading order from PDF paint order. Typing stays legacy.
