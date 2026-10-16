# Task8 완료 보고

실험05 19문항 recall/summary v2 저작·검토·로컬 발행 완료.

- RED: test_recall_published[5-19]가 v1==2 assertion으로 실패. GREEN: 같은 케이스 1 passed. 발행본 coverage+recall 필터 2 passed,14 deselected.
- Final stage/published check 각각 OK. source hash 포함 기존 검사 유지.
- 원문: manifest 참조 23 PDF pages 렌더링 및 view_image 실제 검사. output/validation/problem-recall/sources-05.json과 source-05/ PNG에 기록.
- 내용: decoder minterm 8/4행, encoder8 onehot/NAND encoder4, priority 지정6행·256 masks, Excess3 0…9 complement·SW6 회로식/시험4행, DMUX8행/quiz4행 실제 계산. computations-05.json 증거. content=self_review; independent=not_run.
- 브라우저: 19×375/1280×light/dark=76 cases, 152 screenshots, 20 실제 픽셀 contact sheets 전부 view_image 확인. noJS19 readable; pageerror/KaTeX/broken image/document overflow 0. drawer/current/navigation/Enter focus/read-state separation/reload 수행. 20 긴 카드 scroll/touch hash유지. gap24+24+1와 card16/1/auto 확인. browser-05.json/touch-05.json 증거. 재사용 harness print는 낡은 48/12 숫자, 실제 JSON76/DOM19로 검증함.
- 74HC143 원문 이름/ID/status/old six sections 그대로. 단답형 p2에는 그림/기능표 없음. 교안 p10 그림은 74HC148. 새 recall/summary가 이름 차이·148 조건부 해석·GS/EO 상세 상태의 제공 자료 검증 한계 명시. 실제143 datasheet 검증 주장 없음.
- 19 fragment에서 새 recall/summary 제거 시 old 문자열 정확 일치. 모든 기존 소문항/풀이/경고 보존.
- 보존: {
  "files_unchanged": 172,
  "new_outside_mutable": 0,
  "metadata_equal": true,
  "source_hashes": "stage and published check OK",
  "fragments_exact": 19,
  "browser_cases": 76,
  "touch_cases": 20,
  "backup": "C:\\Users\\Hyunjun\\.codex\\worktrees\\logic-lab-problem-recall\\논회실\\복습노트\\실험05.backup-f026b24748e2"
}

저작 원본/발행 검증결과.md 및 docs/verify/logic-lab-problem-recall.md에 각 19 ID의 단서·개념/기호·적용조건/이유·소문항·원문/page·경고·요약·실제검토 기록.
저작 manifest에는 없던 problem_explanation_version 키만 2로 추가. 초기 author script가 기존 literal v1 assert에서만 실패했으나 19 fragments/original snapshot은 이미 성공 저장됐고 manifest 단계 별도로 수정. 미완성 stage 발행 없음.
백업은 유지했고 PNG 대용량 증거는 커밋하지 않은 로컬 output에 유지. scope 밖 engine/spec/navigation/netlist는 커밋하지 않음.
