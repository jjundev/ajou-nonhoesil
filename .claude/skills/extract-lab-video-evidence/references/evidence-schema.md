# 근거 파일과 CLI

`manifest.json`의 원본 정보·프레임 출처는 도구가 기록한다. 모델은 장면 해석과 선택, 직접 확인한 범위를 채운다. 원본 경로나 해시·미디어 정보를 바꾸지 않는다.

## 필드

| 필드 | 작성 주체 | 내용 |
|---|---|---|
| `schema_version`, `run_dir`, `run_label`, `mode`, `outputs` | inspect | 실행 식별·모드·예약한 저장 위치 |
| `sources` | inspect/verify | `p1`, `p2` 영상 및 `transcript_p1` 전사본. 원본 경로·해시·길이·미디어 정보 |
| `scenes` | 모델 | 원본 구간, 교안 항목(`item_id`, 미확정 null), 화면 관찰, 발언, 미확인 사항 |
| `captures` | 모델 → build | 사진 선택 시각·장면 id. 생성 시 실제 프레임 번호·PTS·경로 추가 |
| `pairs` | 모델 → build | 두 사진 id·제목·근거 주석·연속성. 같은 사진을 여러 비교에 재사용 가능 |
| `cuts` | 모델 | 원본 보존 구간·이유·앞에 넣을 중단 안내 |
| `render` | 선택 지정 | `fps`, `size: [가로, 세로]`. 생략하면 첫 보존 영상의 실제 평균 fps와 표시 크기 |
| `unknowns` | 모델 | 전반적인 미확인 사항 문자열 목록 |
| `review` | 직접 확인한 모델 | `photos`, `boundaries`, `audio`: 기본 pending, 확인 후 verified, 청취 불가 시 audio만 unavailable |
| `rendered`, `checks` | build/verify | 실제 편집 시간선·패딩 길이·기술 검사·완료 여부 |

모든 `start_s`·`end_s`·`at_s`는 **해당 영상의 첫 표시 프레임을 0초로 한 경과 시각**이다. `frame_pts_s`는 원본 컨테이너의 절대 PTS라 시작값이 0이 아닐 수 있다. `source_time_s`는 선택된 실제 프레임의 경과 시각이다. 전사 시각은 근사값이며 사진 시각을 덮어쓰지 않는다.

구간은 `[start_s, end_s)`다. 요청 시각 이상의 첫 실제 프레임을 선택하며, 해당 시각에 프레임이 없으면 오류다. 프레임에 맞춘 편집 구간과 출력 fps에 맞춘 1프레임 미만의 끝 패딩은 `rendered.timeline`에 별도 기록한다. 속도를 바꾸지 않는다. 서로 다른 표시 크기는 첫 영상 크기에 맞춰 여백을 추가하며 자르지 않는다.

## 선택 예시

아래는 입력 조작 설명과 LED 관찰을 분리한 **형식 예시**다. 시각·관찰·조건은 매번 원본에서 새로 판단한다. 원본·실험 항목·장수·해상도를 예시대로 고정하지 않는다.

```json
{
  "scenes": [{
    "id": "set_condition",
    "source_id": "p1",
    "start_s": 11,
    "end_s": 16,
    "item_id": "E6.P3-2/T3/1",
    "speech": [{
      "source_id": "transcript_p1",
      "at_s": 11,
      "text": "Reset=1이라는 발언"
    }],
    "observation": "위 LED 점등, 아래 LED 소등",
    "unknowns": ["Set 입력 전압과 실물 핀 대응은 독립 확인 못함"]
  }],
  "captures": [{
    "id": "photo1",
    "source_id": "p1",
    "at_s": 12.5,
    "scene_id": "set_condition",
    "title": "Set조건_설명구간",
    "observation": "위 LED 점등"
  }],
  "pairs": [],
  "cuts": [{
    "source_id": "p1",
    "start_s": 10,
    "end_s": 116.9,
    "reason": "초기 전원 미인가와 마지막 실패 시도를 제외"
  }, {
    "source_id": "p2",
    "start_s": 0,
    "end_s": 7,
    "reason": "배선 수정 후 최종 상태, 전원 차단 전 종료",
    "break_before": {
      "text": "배선 조정 후 재촬영\n수정 후 최종 상태",
      "duration_s": 2
    }
  }]
}
```

`pairs` 요소는 다음 형식이다. `capture_ids`에 존재하는 사진 id 2개를 순서대로 넣는다. 다른 촬영본이면 `continuity`는 `interrupted`다. 단일 촬영본에서도 중간 조정으로 연속성이 끊겼다면 `interrupted`로 지정한다.

```json
{
  "id": "repair_compare",
  "title": "배선 수정 전후 상태",
  "capture_ids": ["photo_before", "photo_after"],
  "continuity": "interrupted",
  "note": "입력 조건은 전사 기준, 수정 중 상태 변화 미확인"
}
```

출력은 같지만 입력은 여러 조합일 수 있다. 캡션에 입력을 넣을 때 전사·직접 관찰·사용자 설명 중 어느 근거인지 명시한다. `item_id` 연결은 해당 행을 완전히 검증했다는 판정이 아니다.

## 실행과 복구

- `inspect --experiment N`은 저장소의 `scripts.lab.config.experiment_dir`를 사용한다. 경로 정규화는 실제 디렉터리 이름으로 해결한다.
- `--source`를 지정한 순서로 `p1`, `p2`…가 된다. `--transcript p1=경로`는 생략 가능하다. 전사본이 없으면 `speech`를 비운다.
- 모드는 `photos`(기본), `video`, `both`다. 선택 자료는 이번 요청에 필요한 것만 채운다.
- `preview`는 기본 1초 간격, 조작 부근은 `--step 0.1` 등으로 좁힌다. 같은 미리보기 이름은 덮어쓰지 않는다. 필요하면 기존 미리보기를 다시 연다.
- 프레임 목록은 원본별 한 번 조사해 `frames/`에 캐시한다. 여러 사진 추출은 원본별 한 번의 디코딩으로 묶는다.
- `build`는 이미 존재하는 사진 폴더·영상·ZIP을 덮어쓰지 않는다. 중간 실패 시 `재현명령.txt`와 오류를 확인하고, 잘못된 선택을 고쳐 새 `inspect` 실행에 옮긴다. 생성물을 지우는 대신 공통 `_v2` 버전을 사용한다.
- `verify`의 `technical_pass: true`만으로 전달 완료는 아니다. 사진/연결점의 직접 확인을 기록하고 다시 실행해 `complete: true`를 확인한다. 영상이 없거나 도구 오류면 완료로 보고하지 않는다.
- `verify` 종료 코드: 완료 0, 기술 검사 실패 또는 직접 확인 대기 1, 잘못된 입력·실행 오류 2.
- `검증결과.json`·미확인 문서·사진 안내·재현 명령을 실행 폴더에 보관한다. PNG 원본은 변형하지 않고 비교 시트만 별도 축소·주석 처리한다.

## 개발 검증

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s .claude/skills/extract-lab-video-evidence/tests -v
```

합성 미디어는 임시 폴더에서만 만든다. 실제 촬영본으로 재검증할 때에도 기존 결과 폴더를 재사용하지 않고 별도의 임시 실험 폴더·전달 폴더를 지정한다.
