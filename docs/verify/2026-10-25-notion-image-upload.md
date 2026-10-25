# Notion 이미지 자동 첨부 실측 검증

- 검증 일시(KST): 2026-10-25T18:26:45.477902+09:00 ~ 2026-10-25T18:36:03.645746+09:00
- 코드 커밋: `105b58cf8ea9fa390c73addbe4818824da3231b3`
- 작업 브랜치: `codex/notion-image-upload`
- 실제 서비스: Notion API `2026-03-11`, 과목정보에 설정된 부모 페이지 아래 시험 전용 페이지.
- 로컬 시험 자료·진행 기록: `/tmp/notion-image-acceptance-20261025-01` (실제 보고서 output 이력과 분리).

## 실행과 결과

```bash
NOTION_IMAGE_LIVE=1 NOTION_IMAGE_LIVE_WORKDIR=/tmp/notion-image-acceptance-20261025-01 .venv/bin/python -m pytest -n0 tests/test_notion_image_live.py -q -s
```

- 장애 주입 인수 실행: 2 passed / 131.11s.
- 최종 코드로 실제 6개 페이지 재검증 및 구체적 오류 원인 확인 후 변조 재시험: 2 passed / 37.40s.
- 관련 단위 회귀: 379 passed, 1 live skipped, 39 subtests (마지막 독립 리뷰 후 최종 전체 결과는 아래 추가).
- 중간 전체 저장소 회귀: 3712 passed, 10 skipped, 1224 subtests; 기존 Pillow 등의 경고 52건.
- 기본 테스트에서는 라이브 테스트가 skip된다. 실제 Notion에 쓰는 테스트는 두 환경변수를 모두 지정한 경우만 실행한다.

## 실제 시험 페이지

| 시나리오 | 페이지 | 이미지 수 | 버전 | 복구 전 상태 | 판정 |
|---|---|---:|---:|---|---|
| happy_path | [시험 페이지](https://app.notion.com/p/happy_path-notion-image-acceptance-20261025-01-v1-sync-5c90443f40eb41079fa5017f2fdbe1e5-404b06d263bc81cea6d5c9f6e45be462) | 4 | 1 | 정상/기존 journal 재개 | pass |
| insert_response_lost | [시험 페이지](https://app.notion.com/p/insert_response_lost-notion-image-acceptance-20261025-01-v1-sync-5a328e60e57b4e9685e1e7c7a59699fe-404b06d263bc81fca4a6f2c6c9ebf3b2) | 3 | 1 | inserting | pass |
| archive_response_lost | [시험 페이지](https://app.notion.com/p/archive_response_lost-notion-image-acceptance-20261025-01-v1-sync-10989ea2f1954c3693808104d2f9b24d-404b06d263bc81c396e4ced0f8288193) | 3 | 1 | inserting | pass |
| process_crash | [시험 페이지](https://app.notion.com/p/process_crash-notion-image-acceptance-20261025-01-v1-sync-97fd48ae26d346fbaf4ff35195f1c4e4-404b06d263bc8119a21add55c6d80483) | 3 | 1 | inserting | pass |
| baseline_failure | [시험 페이지](https://app.notion.com/p/baseline_failure-notion-image-acceptance-20261025-01-v1-sync-324afc34e8834cb486b667a91c35c733-404b06d263bc81169b3bca7df6114989) | 3 | 1 | verified | pass |
| page_create_response_lost | [시험 페이지](https://www.notion.so/404b06d263bc81b1a50fcc025ed3a9f5) | 3 | 1 | planned | pass |

모든 페이지는 보존했다. 페이지 제목은 검증 완료이며 URL의 예전 sync 슬러그는 제목 갱신 뒤에도 유지될 수 있다.
정상 페이지는 110개 최상위 블록과 표의 하위 행을 포함한다. 첫 이미지·끝 이미지·연속 이미지·동일 파일/캡션 반복·PNG/JPEG·2,400자 한글 캡션·표·수식을 시험했다.

## 검증과 실패 복구 증거

| 항목 | 기대 및 실측 |
|---|---|
| 정확한 위치 | 같은 부모와 앞뒤 비이미지 본문 경계, 구간 내 이미지 ID 순서를 대조했다. 개수와 캡션이 맞아도 다른 절로 옮긴 이미지를 거절했다. |
| 캡션 | rich_text를 합친 문자열을 공백까지 정확히 비교했다. 캡션 불일치 오류를 실제 확인하고 원래 캡션으로 복구했다. |
| 내용 | 인증 헤더 없이 원격 파일을 다운로드해 SHA-256 비교했다. 다른 JPEG로 교체하자 원본 내용 불일치 오류가 발생했고 원래 파일로 복구했다. |
| 삽입 응답 유실 | 실제 API 성공 응답을 받은 직후 호출자에게 URLError를 주입했다. resume이 표식 뒤 후보의 내용과 캡션을 확인해 기존 블록을 채택했다. |
| 표식 삭제 응답 유실 | 실제 삭제 성공 뒤 응답을 잃게 했다. resume은 이미 사라진 표식을 재삽입하지 않고 진행했다. |
| 프로세스 중단 | 별도 worker에서 실제 이미지 삽입 응답을 받은 직후 os._exit(73)으로 종료했다. 블록 ID 저장·정상 잠금 정리 없이 종료했으며, 새 프로세스가 같은 페이지/버전에서 재개했다. |
| baseline 저장 실패 | 이미지/본문 검증 뒤 로컬 저장만 OSError로 실패시켰다. 완료 이력이 없는 상태에서 같은 페이지와 버전으로 재개해 baseline 하나·레코드 하나를 확정했다. |
| 페이지 생성 응답 유실 | 실제 새 페이지 생성 직후 응답을 잃게 했다. 임시 제목의 작업 ID와 본문 소유권 표식으로 부모 아래 고유한 페이지를 재발견했다. 두 번째 페이지를 만들지 않았다. |
| 중복 없음 | 각 시나리오에서 계획된 이미지 수, baseline 1개, 완료 레코드 1개, 정상/임시 제목 후보 페이지 총 1개를 원격·로컬에서 확인했다. |
| 비밀 비저장 | 시험 산출물 JSON/MD와 진행 기록에서 실제 토큰·X-Amz-Signature·X-Amz-Security-Token이 없음을 검사했다. 원격 응답 전체와 다운로드 URL은 저장하지 않았다. |

시험 변조의 실패는 단순한 네트워크 오류를 성공으로 세지 않는다. 각각 `캡션 불일치`, `원본 내용과 다릅니다`, `본문 경계/순서` 오류인지 확인했다.
시험 소유 이미지 복원 후 전체 위치·캡션·내용을 다시 검증했다. API unarchive는 원래 자리에 복원하지 않아 시험 도구에서 첫 이미지를 position:start로 재생성했고, 아래에는 최종 블록 ID를 기록했다. 운영 sync는 사용자 편집을 자동 보정하지 않는다.

### 복구 전후 식별자

| 시나리오 | 복구 전 page_id | 완료 page_id | 버전 전→후 |
|---|---|---|---|
| happy_path | 응답 유실/정상 경로 | 404b06d2-63bc-81ce-a6d5-c9f6e45be462 | 1→1 |
| insert_response_lost | 404b06d2-63bc-81fc-a4a6-f2c6c9ebf3b2 | 404b06d2-63bc-81fc-a4a6-f2c6c9ebf3b2 | 1→1 |
| archive_response_lost | 404b06d2-63bc-81c3-96e4-ced0f8288193 | 404b06d2-63bc-81c3-96e4-ced0f8288193 | 1→1 |
| process_crash | 404b06d2-63bc-8119-a21a-dd55c6d80483 | 404b06d2-63bc-8119-a21a-dd55c6d80483 | 1→1 |
| baseline_failure | 404b06d2-63bc-8116-9b3b-ca7df6114989 | 404b06d2-63bc-8116-9b3b-ca7df6114989 | 1→1 |
| page_create_response_lost | 응답 유실/정상 경로 | 404b06d2-63bc-81b1-a50f-cc025ed3a9f5 | 1→1 |

## 최종 이미지 식별자와 검증값

긴 캡션은 길이와 SHA-256으로 기록하고, 짧은 캡션은 원문을 함께 남긴다. 문서 경계는 ∅로 표시한다. 다운로드 URL은 제외했다.

### happy_path

- 등장 0: 캡션 ''
  - caption SHA-256: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
  - upload ID: `404b06d2-63bc-815b-88a3-00b2134b4dce`; image block ID: `404b06d2-63bc-8142-a062-fb9f691eaec1`
  - parent: `404b06d2-63bc-81ce-a6d5-c9f6e45be462`; before: `∅`; after: `c77235c6-fc6f-415a-a717-e786dc95049e`
  - source SHA-256: `b820cfc6ecef814bb38bbe4511f871ad44c2535fcd832029dd270a7b381ec154`
  - remote SHA-256: `b820cfc6ecef814bb38bbe4511f871ad44c2535fcd832029dd270a7b381ec154`; comparison: sha256; ok: True
- 등장 1: 캡션 2400자 (아래 해시)
  - caption SHA-256: `f553b3d33834d30ed7735be424f0e3bd5920eed0677923beedd1d049ec3ed2a2`
  - upload ID: `404b06d2-63bc-814c-bf8a-00b21d139c60`; image block ID: `404b06d2-63bc-8164-8479-fd268301d470`
  - parent: `404b06d2-63bc-81ce-a6d5-c9f6e45be462`; before: `41ff5aab-f95b-41e3-92ac-3435b5ef81d4`; after: `a4de4ada-96cf-4f20-978b-9b031c605565`
  - source SHA-256: `3fab87d6c4e6e4d6f80c7678a8f59aab8fc03af67fa90c1f4a8591f266e2760c`
  - remote SHA-256: `3fab87d6c4e6e4d6f80c7678a8f59aab8fc03af67fa90c1f4a8591f266e2760c`; comparison: sha256; ok: True
- 등장 2: 캡션 '반복 캡션'
  - caption SHA-256: `894180c928eff6027b16ab45c74c7f2c5997b9efa078d6555831daa6b1de2e6e`
  - upload ID: `404b06d2-63bc-81f8-af49-00b2e5745a88`; image block ID: `404b06d2-63bc-814f-837f-fb6d5efd50c4`
  - parent: `404b06d2-63bc-81ce-a6d5-c9f6e45be462`; before: `a4de4ada-96cf-4f20-978b-9b031c605565`; after: `∅`
  - source SHA-256: `b820cfc6ecef814bb38bbe4511f871ad44c2535fcd832029dd270a7b381ec154`
  - remote SHA-256: `b820cfc6ecef814bb38bbe4511f871ad44c2535fcd832029dd270a7b381ec154`; comparison: sha256; ok: True
- 등장 3: 캡션 '반복 캡션'
  - caption SHA-256: `894180c928eff6027b16ab45c74c7f2c5997b9efa078d6555831daa6b1de2e6e`
  - upload ID: `404b06d2-63bc-810d-b3a7-00b21e77b429`; image block ID: `404b06d2-63bc-81d2-89a0-c897cff4b637`
  - parent: `404b06d2-63bc-81ce-a6d5-c9f6e45be462`; before: `a4de4ada-96cf-4f20-978b-9b031c605565`; after: `∅`
  - source SHA-256: `b820cfc6ecef814bb38bbe4511f871ad44c2535fcd832029dd270a7b381ec154`
  - remote SHA-256: `b820cfc6ecef814bb38bbe4511f871ad44c2535fcd832029dd270a7b381ec154`; comparison: sha256; ok: True

### insert_response_lost

- 등장 0: 캡션 ''
  - caption SHA-256: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
  - upload ID: `404b06d2-63bc-81f8-931b-00b23c4b2bb6`; image block ID: `404b06d2-63bc-81f6-a830-f1b1e03a742d`
  - parent: `404b06d2-63bc-81fc-a4a6-f2c6c9ebf3b2`; before: `∅`; after: `f3ebf0b5-554d-4331-9a2b-d7e7aa3cbd90`
  - source SHA-256: `b820cfc6ecef814bb38bbe4511f871ad44c2535fcd832029dd270a7b381ec154`
  - remote SHA-256: `b820cfc6ecef814bb38bbe4511f871ad44c2535fcd832029dd270a7b381ec154`; comparison: sha256; ok: True
- 등장 1: 캡션 '반복 캡션'
  - caption SHA-256: `894180c928eff6027b16ab45c74c7f2c5997b9efa078d6555831daa6b1de2e6e`
  - upload ID: `404b06d2-63bc-8166-adf4-00b24088e569`; image block ID: `404b06d2-63bc-814a-bd60-de30c0108050`
  - parent: `404b06d2-63bc-81fc-a4a6-f2c6c9ebf3b2`; before: `81837487-148d-46b5-804b-e19f0ee5d424`; after: `∅`
  - source SHA-256: `b820cfc6ecef814bb38bbe4511f871ad44c2535fcd832029dd270a7b381ec154`
  - remote SHA-256: `b820cfc6ecef814bb38bbe4511f871ad44c2535fcd832029dd270a7b381ec154`; comparison: sha256; ok: True
- 등장 2: 캡션 '반복 캡션'
  - caption SHA-256: `894180c928eff6027b16ab45c74c7f2c5997b9efa078d6555831daa6b1de2e6e`
  - upload ID: `404b06d2-63bc-81ba-ae03-00b291bf33d9`; image block ID: `404b06d2-63bc-8141-9262-c50a31943561`
  - parent: `404b06d2-63bc-81fc-a4a6-f2c6c9ebf3b2`; before: `81837487-148d-46b5-804b-e19f0ee5d424`; after: `∅`
  - source SHA-256: `b820cfc6ecef814bb38bbe4511f871ad44c2535fcd832029dd270a7b381ec154`
  - remote SHA-256: `b820cfc6ecef814bb38bbe4511f871ad44c2535fcd832029dd270a7b381ec154`; comparison: sha256; ok: True

### archive_response_lost

- 등장 0: 캡션 ''
  - caption SHA-256: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
  - upload ID: `404b06d2-63bc-81e7-a0b7-00b2b247c87e`; image block ID: `404b06d2-63bc-819c-9bad-d302849dbec7`
  - parent: `404b06d2-63bc-81c3-96e4-ced0f8288193`; before: `∅`; after: `22e760a5-bc41-462d-afbf-6e46efb04e30`
  - source SHA-256: `b820cfc6ecef814bb38bbe4511f871ad44c2535fcd832029dd270a7b381ec154`
  - remote SHA-256: `b820cfc6ecef814bb38bbe4511f871ad44c2535fcd832029dd270a7b381ec154`; comparison: sha256; ok: True
- 등장 1: 캡션 '반복 캡션'
  - caption SHA-256: `894180c928eff6027b16ab45c74c7f2c5997b9efa078d6555831daa6b1de2e6e`
  - upload ID: `404b06d2-63bc-81b2-bc91-00b26aa6025a`; image block ID: `404b06d2-63bc-81b0-bd8a-f3809d54426a`
  - parent: `404b06d2-63bc-81c3-96e4-ced0f8288193`; before: `9d93b954-8daa-4c89-9b24-bd7eb0e4fd53`; after: `∅`
  - source SHA-256: `b820cfc6ecef814bb38bbe4511f871ad44c2535fcd832029dd270a7b381ec154`
  - remote SHA-256: `b820cfc6ecef814bb38bbe4511f871ad44c2535fcd832029dd270a7b381ec154`; comparison: sha256; ok: True
- 등장 2: 캡션 '반복 캡션'
  - caption SHA-256: `894180c928eff6027b16ab45c74c7f2c5997b9efa078d6555831daa6b1de2e6e`
  - upload ID: `404b06d2-63bc-81f7-9603-00b2b8c0d9c3`; image block ID: `404b06d2-63bc-816d-9a9b-ff3acadc5cd1`
  - parent: `404b06d2-63bc-81c3-96e4-ced0f8288193`; before: `9d93b954-8daa-4c89-9b24-bd7eb0e4fd53`; after: `∅`
  - source SHA-256: `b820cfc6ecef814bb38bbe4511f871ad44c2535fcd832029dd270a7b381ec154`
  - remote SHA-256: `b820cfc6ecef814bb38bbe4511f871ad44c2535fcd832029dd270a7b381ec154`; comparison: sha256; ok: True

### process_crash

- 등장 0: 캡션 ''
  - caption SHA-256: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
  - upload ID: `404b06d2-63bc-81c4-be92-00b29cbdfb13`; image block ID: `404b06d2-63bc-814c-a3b6-d1028449c17a`
  - parent: `404b06d2-63bc-8119-a21a-dd55c6d80483`; before: `∅`; after: `51cbc6d2-666e-4f54-bbe6-54e60d4c9078`
  - source SHA-256: `b820cfc6ecef814bb38bbe4511f871ad44c2535fcd832029dd270a7b381ec154`
  - remote SHA-256: `b820cfc6ecef814bb38bbe4511f871ad44c2535fcd832029dd270a7b381ec154`; comparison: sha256; ok: True
- 등장 1: 캡션 '반복 캡션'
  - caption SHA-256: `894180c928eff6027b16ab45c74c7f2c5997b9efa078d6555831daa6b1de2e6e`
  - upload ID: `404b06d2-63bc-81ed-99dd-00b2d40e9034`; image block ID: `404b06d2-63bc-8195-965e-d5622cedfce5`
  - parent: `404b06d2-63bc-8119-a21a-dd55c6d80483`; before: `f648e19a-2213-4f9e-90f6-d74e46d9106f`; after: `∅`
  - source SHA-256: `b820cfc6ecef814bb38bbe4511f871ad44c2535fcd832029dd270a7b381ec154`
  - remote SHA-256: `b820cfc6ecef814bb38bbe4511f871ad44c2535fcd832029dd270a7b381ec154`; comparison: sha256; ok: True
- 등장 2: 캡션 '반복 캡션'
  - caption SHA-256: `894180c928eff6027b16ab45c74c7f2c5997b9efa078d6555831daa6b1de2e6e`
  - upload ID: `404b06d2-63bc-8172-a7b4-00b24b8224d9`; image block ID: `404b06d2-63bc-8141-a674-c4b6cb06ceef`
  - parent: `404b06d2-63bc-8119-a21a-dd55c6d80483`; before: `f648e19a-2213-4f9e-90f6-d74e46d9106f`; after: `∅`
  - source SHA-256: `b820cfc6ecef814bb38bbe4511f871ad44c2535fcd832029dd270a7b381ec154`
  - remote SHA-256: `b820cfc6ecef814bb38bbe4511f871ad44c2535fcd832029dd270a7b381ec154`; comparison: sha256; ok: True

### baseline_failure

- 등장 0: 캡션 ''
  - caption SHA-256: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
  - upload ID: `404b06d2-63bc-81b3-9dd9-00b2bfd4a4af`; image block ID: `404b06d2-63bc-819b-86e2-de005fa90441`
  - parent: `404b06d2-63bc-8116-9b3b-ca7df6114989`; before: `∅`; after: `c3d98a23-5340-4439-8821-d77465e8d4ef`
  - source SHA-256: `b820cfc6ecef814bb38bbe4511f871ad44c2535fcd832029dd270a7b381ec154`
  - remote SHA-256: `b820cfc6ecef814bb38bbe4511f871ad44c2535fcd832029dd270a7b381ec154`; comparison: sha256; ok: True
- 등장 1: 캡션 '반복 캡션'
  - caption SHA-256: `894180c928eff6027b16ab45c74c7f2c5997b9efa078d6555831daa6b1de2e6e`
  - upload ID: `404b06d2-63bc-8191-95e2-00b2f6a9b29c`; image block ID: `404b06d2-63bc-81e6-acdb-ea74027978b0`
  - parent: `404b06d2-63bc-8116-9b3b-ca7df6114989`; before: `75840903-1806-4979-b408-4d8048aeae9e`; after: `∅`
  - source SHA-256: `b820cfc6ecef814bb38bbe4511f871ad44c2535fcd832029dd270a7b381ec154`
  - remote SHA-256: `b820cfc6ecef814bb38bbe4511f871ad44c2535fcd832029dd270a7b381ec154`; comparison: sha256; ok: True
- 등장 2: 캡션 '반복 캡션'
  - caption SHA-256: `894180c928eff6027b16ab45c74c7f2c5997b9efa078d6555831daa6b1de2e6e`
  - upload ID: `404b06d2-63bc-8171-a539-00b27b15985a`; image block ID: `404b06d2-63bc-8140-9744-c362fd731192`
  - parent: `404b06d2-63bc-8116-9b3b-ca7df6114989`; before: `75840903-1806-4979-b408-4d8048aeae9e`; after: `∅`
  - source SHA-256: `b820cfc6ecef814bb38bbe4511f871ad44c2535fcd832029dd270a7b381ec154`
  - remote SHA-256: `b820cfc6ecef814bb38bbe4511f871ad44c2535fcd832029dd270a7b381ec154`; comparison: sha256; ok: True

### page_create_response_lost

- 등장 0: 캡션 ''
  - caption SHA-256: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
  - upload ID: `404b06d2-63bc-81ec-8314-00b29aea3c99`; image block ID: `404b06d2-63bc-811a-9856-d6b577785903`
  - parent: `404b06d2-63bc-81b1-a50f-cc025ed3a9f5`; before: `∅`; after: `8c1c1f77-833a-40f5-ae9e-742c4bf4dc7d`
  - source SHA-256: `b820cfc6ecef814bb38bbe4511f871ad44c2535fcd832029dd270a7b381ec154`
  - remote SHA-256: `b820cfc6ecef814bb38bbe4511f871ad44c2535fcd832029dd270a7b381ec154`; comparison: sha256; ok: True
- 등장 1: 캡션 '반복 캡션'
  - caption SHA-256: `894180c928eff6027b16ab45c74c7f2c5997b9efa078d6555831daa6b1de2e6e`
  - upload ID: `404b06d2-63bc-8139-8848-00b278b13e2a`; image block ID: `404b06d2-63bc-814e-8a03-fd33fb7e0653`
  - parent: `404b06d2-63bc-81b1-a50f-cc025ed3a9f5`; before: `9bbc3e24-3534-4a88-8284-7ab0299723c5`; after: `∅`
  - source SHA-256: `b820cfc6ecef814bb38bbe4511f871ad44c2535fcd832029dd270a7b381ec154`
  - remote SHA-256: `b820cfc6ecef814bb38bbe4511f871ad44c2535fcd832029dd270a7b381ec154`; comparison: sha256; ok: True
- 등장 2: 캡션 '반복 캡션'
  - caption SHA-256: `894180c928eff6027b16ab45c74c7f2c5997b9efa078d6555831daa6b1de2e6e`
  - upload ID: `404b06d2-63bc-812b-bf2b-00b26b8c2c9f`; image block ID: `404b06d2-63bc-8128-a3dd-fd58ac5a4ee6`
  - parent: `404b06d2-63bc-81b1-a50f-cc025ed3a9f5`; before: `9bbc3e24-3534-4a88-8284-7ab0299723c5`; after: `∅`
  - source SHA-256: `b820cfc6ecef814bb38bbe4511f871ad44c2535fcd832029dd270a7b381ec154`
  - remote SHA-256: `b820cfc6ecef814bb38bbe4511f871ad44c2535fcd832029dd270a7b381ec154`; comparison: sha256; ok: True

## 별도 관문과 제한

- 최초 API 관문은 /tmp/notion-image-probe-20261025-01/probe.json에 보존했다. 독립 표식·표·수식·삽입 위치·캡션·내용·표식 제거 7항목 통과.
- [최초 API 시험 페이지](https://app.notion.com/p/API-f2b43652df3f462e92317a27f3a8af5f-404b06d263bc819fa23ed487a3cc6bd0)
- 실제 시험 중 100개 초과 블록의 삽입 응답이 단일 항목이라는 가정이 깨졌다. 성공 후에도 원격 표식 구간으로 다시 식별하도록 수정했고 회귀 테스트와 같은 페이지 재개로 확인했다.
- 미첨부 upload 만료, 다운로드 URL 만료 후 재조회, Pillow 없는 경우, 재인코딩 픽셀 비교, 원본/원격 편집 충돌 및 동시 실행 거절은 단위 테스트로 확인했다. 한 시간 대기 만료를 실제 서비스에서 실측한 것은 아니다.
- PNG/JPEG의 최상위 독립 로컬 이미지 줄이 지원 범위다. 표/목록/인라인 로컬 이미지는 사전 거절하며 외부 HTTPS 이미지는 유지한다.
- PDF 크기·정렬·쪽 나눔과 하드웨어 실험 결과의 정확성은 이 시험 범위에 없다.
- 기존 보고서 notion.json·baseline·원본 이미지는 수정하지 않았다. 전체 테스트가 재생성한 navigation PNG 두 개는 원래 상태로 돌렸다.
- API 근거: [파일 업로드](https://developers.notion.com/guides/data-apis/uploading-small-files), [위치 지정 삽입](https://developers.notion.com/reference/patch-block-children).

## 독립 리뷰와 최종 회귀

독립 리뷰 후 이 절에 판정·수정·최종 전체 회귀 결과를 추가한다.
