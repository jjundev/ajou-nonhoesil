# 단계·준비 그림 계약

**단계는 그리기 순서의 앞부분 자르기다.** 주차 빌더는 완성 경로를 한 번 쓰고 배선마다
"처음 꽂히는 단계" 를 달아 `stage` 로 자른다 — **완성 경로의 호출 순서를 바꾸지
않는다.** 레일 착지 행이 점유 순서로 정해지므로 순서가 바뀌면 완성본 도장이 바뀌고
손그림 원도·예비보고서 그림이 어긋난다. 실물은 `보고서/실험03/결선도/배치.py` 의
`_e3_draw` 다.


## 선택 조립 그림 사슬

계약 정본은 `docs/schema/lab-netlist-v3.md`다. 주차 `배치.py`의 선택
`ASSEMBLY_BOARDS = {부모_일반단계_PNG: [(준비_PNG, builder), ...]}`는 조립 표와
부모·파일명·순서가 정확히 같아야 한다. builder는 `(output_path, template_path=None,
baseline=None)`을 받고 렌더러를 반환한다. BOARDS·FINALS 계약을 바꾸지 않는다.

`iter_procedure_boards(board)`가 준비→부모 순서로 snapshot을 전달한다. 준비도 물리 충돌·
레일·제거 검사를 받는다. 전원이 꺼져 미완성이라는 이유로 이 검사를 면제하지 않는다.
준비는 전원·임시 고정·수동 LED 사슬 추가만 허용한다. sig/mid·출력 급전은 기능 단계,
제거는 걷기에 둔다. 준비 중 모든 F/F가 통전 구동된다는 전제는 적용하지 않는다.
기존 전체 배치의 레일 예약과 경로를 재사용해 나중 준비에서 기존 홀을 옮기지 않는다.
완성본에는 준비 기준선을 주지 않는다. 실험07의 준비6개는 사례이며 공통 고정 개수가 아니다.

생성 전 `assembly.check_structure(netlist)`, 생성 후
`assembly.check_registry(netlist, board.ASSEMBLY_BOARDS)`와 `assembly.check_assets(netlist)`를
실행해 error 0을 확인한다. 표 없는 주차는 빈 registry로 기존 사슬을 그대로 따른다.
