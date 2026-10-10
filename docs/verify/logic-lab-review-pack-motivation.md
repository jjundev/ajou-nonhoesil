# 실험01~05 회로 사용 동기 도입부 검증 — 2026-10-10

## 변경과 범위

첫 토픽 `t-start`의 제목을 ‘왜 이 회로를 쓰는지 먼저 알아봐요’로 통일했다. 해결할 문제 → 회로가 필요한 이유 → 작은 입력·출력 예 → 이번 실험과 연결 순서로 각 실험에 맞는 네 문단을 작성했다. 수행 범위·판본·예상/측정 구분과 기존 상세 설명을 보존했다. 첫 토픽 요약에도 회로가 해결하는 문제를 반영했다.

향후 생성에 적용하도록 SKILL·authoring·verification 규칙을 갱신했다. 실험01~03의 첫 fragment를 보존했으며 실험04·05 생성 코드가 해당 fragment를 직접 읽게 해 본문 중복과 재생성 시 되돌아감을 막았다. 원본 manifest와 첫 제목·근거도 동기화했다. 실험05 TOPICS의 페이지 목록·md_notes까지 일치하는 회귀 검사를 RED→GREEN으로 확인해 전체 build_run 재생성 시 새 근거가 사라지지 않게 했다.

## 내용 대조와 검산

| 실험 | 확인한 근거와 예 | 판정 |
|---|---|---|
| 01 | 교안 p3·p5·p6: AND(1,0)=0, AND(1,1)=1. OR의 ‘하나라도 만족’과 구분. 문/버튼은 이해용 상황이며 실제 구동 실험으로 설명하지 않음 | self_review |
| 02 | 교안 p4 히스테리시스 그림, p10·p11 입력 설정: 낮은 입력에서 출력 1, 상승 문턱을 넘으면 0, 하강 문턱을 넘기 전까지 0 유지. 두 문턱 사이 상태는 이력에 의존. AC 수행 제외 유지 | self_review |
| 03 | 교안 p3: 1+1=10의 합 0/올림 1. 0−1은 윗자리에서 2를 빌리는 한 자리 감산 예로 차 1/내림 1. 여러 자리 계산의 전달과 연결 | self_review |
| 04 | 교안 p3·p5·p8·p11: I0=0,I1=1이면 S=0에서 Y=0, S=1에서 Y=1. 활성 High DMUX에서 D=0이면 선택된 출력도 0. 실제 MUX enable 조건은 상세 토픽에 유지. 출력 직접 연결의 충돌은 보충으로 표시 | self_review |
| 05 | 교안 p3·p5·p9·p11·p12: 활성 High 이상 디코더 101→D5=1, one-hot 인코더 D5→101. 일반 인코더의 단일 활성 입력 조건, 우선순위 필요, 74HC42·74HC148의 활성 Low 구분. Excess-3는 특정 코드이며 모든 인코더의 출력으로 일반화하지 않음 | self_review |

텍스트 추출과 관련 PDF 페이지 렌더를 함께 확인했다. 변경한 도입부에는 새 측정값이나 임의의 문턱 전압을 넣지 않았다. 원문 교안·보고서·문제은행은 수정하지 않았다.

실험02의 기존 netlist 출처 해시는 CRLF 바이트 기준이었다. 현재 파일의 LF를 CRLF로 바꾼 바이트의 SHA256이 기존 해시와 정확히 같고, git `09090ea` 파일과 현재 내용도 같음을 확인했다. 따라서 본문 변경 없이 stage의 해당 source SHA256만 현재 LF 바이트로 갱신했다. 모든 source의 실제 해시를 다시 검사했고 기존 publish 검사를 통과했다. 다른 토픽의 설명·MD 메타데이터는 바꾸지 않았다.

## 테스트와 보존

- 사전 검사: 현재 5개 팩 check 오류 0; publish·metadata·navigation 테스트 21개 통과.
- 최초 RED: 미구현 stage 함수와 옛 재생성 제목에 대해 12개 실패.
- 초기 GREEN: 관련 27개 통과. 추가 보호: 동시 생성 stage를 삭제하는 회귀와 사용자 파일 소유권을 잘못 가져오는 회귀를 각각 RED→GREEN으로 검증했다.
- 최종 관련 단위 테스트: motivation·metadata·navigation·publish 35개 통과.
- 전체 학습팩 회귀: `python -m pytest -o addopts='' tests -k review_pack -q` → 369 passed. PyMuPDF/Swig 관련 기존 deprecation warning 5개, 실패 없음.
- 첫 토픽 밖 HTML article와 MD 본문, 모든 토픽 ID와 storage KEY를 바이트/문자열로 비교했다.
- 기출 HTML·MD·PDF, 그림·원문 증거·기타 파일의 SHA256 보존을 확인했다. 사용자 파일은 stage가 소유하지 않고 기존 publish가 보존한다.
- 최종 5개 팩은 각각 실험설명 HTML·MD·자료/manifest.json 세 파일만 바뀌었다. 파일 목록이 동일하고 기존 기출 PDF 10개가 모두 그대로 남았다.
- 모든 생성 파일은 최종 검사 stage와 byte-identical이고 발행 후 5개 check 오류 0.

## 브라우저

Chrome + Playwright로 실험01~05 × 375px/1280px × light/dark, 총 20조합을 확인했다. 첫 토픽·목차 제목·현재 토픽 표시·우측 요약·이전/다음·hash 이동·모바일 목차 닫힘·읽음 상태 복구가 통과했다. 문서 가로 넘침, 깨진 이미지, KaTeX 오류, pageerror는 모두 0.

최종 stage b의 HTML·MD·assets가 브라우저에서 확인한 stage a와 바이트 단위로 같음을 확인했다. b에서는 기존 사용자 PDF를 stage에서 제외해 소유권만 바로잡았다. 새 stage를 확인하지 않고 기존 증거를 인용한 것이 아니라 표시 내용·실행 자원의 동일성을 비교했다.

- [20조합 결과](motivation-assets/results.json)
- [실험03 데스크톱 다크 화면](motivation-assets/exp03-1280-dark.png)
- [실험04 모바일 밝은 화면](motivation-assets/exp04-375-light.png)

## 발행과 복구

원자료 해시·검증 상태·사용자 파일 충돌 보호를 유지한 기존 publish로 5개 팩을 발행했다. 중간 실패 시 이미 발행된 팩을 백업에서 되돌리는 절차를 사용했다. 작업 중 사전 충돌 검사가 한 번 중단됐지만 어떤 기존 팩도 교체되지 않은 상태에서 소유권 오류를 수정했다.

기존 팩 백업은 실행 workspace의 backups/에 보관했다. 기존 생성 파일은 git 기준선 `2dca1db`에서도 복구할 수 있다. 사용자 추가 PDF는 삭제·재생성하지 않았다. 새 내용의 source_visual/browser는 실제 검토로 pass, content는 self_review, independent는 not_run으로 기록했다. 이는 전체 기출의 새 블라인드 검토를 주장하지 않기 위한 구분이다.
