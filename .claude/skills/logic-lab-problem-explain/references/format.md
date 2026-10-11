# 문제설명 표시 계약

기계 계약은 scripts/lab/review_pack/manifest.py와 explanation_content.py예요. schema_version=1과 review_presentation_version=2를 유지해요. 새 설명 manifest는 problem_explanation_version=2로 지정해요. 기존 v1은 recall 없는 understand/start/solve/verify/pitfall/retry 여섯 구역으로 계속 읽고 build/check/publish가 지원해요. v1 형식을 명시적으로 재현할 때만 explain-stage --explanation-version 1을 써요. 버전이 없는 기존 팩에는 설명을 강제하지 않아요.

활성 시 included 문항의 explanation_fragment는 정확히 problem-explanations/<문항ID>.html이에요. 다른 status는 설명을 요구하지 않아요. 문제지 payload의 ID·번호·제목·순서를 그대로 써요. canonical 발행 경로는 복습노트/실험NN/실험NN_문제설명.html 및 .md, 자료/problem-explanations/<id>.html과 figures/, 검증결과.md예요. manifest는 자료/manifest.json이고 내부 조각 경로는 자료 기준이에요.

explanation_checks는 source_visual/content/independent/browser 네 키, 값은 pass/fail/not_run/self_review예요. 기존 checks와 별도이며 신규/내용 변경은 not_run에서 시작해요. publish에는 source_visual=pass, content=pass 또는 self_review, browser=pass가 필요해요. independent는 실제 수행 상태 그대로 기록하며 기존 답안 상태를 자동으로 바꾸지 않아요.

generated_files는 실험 폴더 루트 기준이며 새 설명 HTML/MD·조각·그림·검증 기록을 포함해 stage 실제 파일 집합과 같아야 해요. 사용자 파일을 편입하지 않아요. 검토 보고서를 stage에 새로 추가하면 이 목록도 갱신해요.

문제설명은 부모 스킬의 note-template과 article.topic·eli5/formal/warn·sum·목차·이전/다음을 재사용해요. 별도 자산을 복제하지 않아요. 읽음 RANGE는 logic-lab-NN-problem-explanation으로 실험설명과 분리해요. 자료 이동·진행 합계·학습 잠금·자동 채점은 넣지 않아요. 불확실성·성립 조건은 HTML에, 상세 출처는 MD에 남겨요. 기존 문제 projection에 정답 projection을 섞지 않아요.
