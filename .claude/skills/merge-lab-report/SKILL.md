---
name: merge-lab-report
description: MUST USE when user wants to merge lab report body PDF with cover PDF (e.g. "보고서랑 표지랑 합쳐줘", "표지 붙여줘", "제출본 만들어줘", "노션 PDF 표지 병합", "/merge-lab-report"). Automatically generates the cover via make-lab-report-cover if missing.
---

# merge-lab-report

## 산출물 이름 (실험07부터)

파일 경로는 `scripts.lab.config.artifact_path(실험폴더, 종류, 확장자)`로 정한다.
실험07 이상은 `실험NN_실험_제목_산출물종류.확장자`이고, 실험01~06은 기존 이름 그대로다.
실험 제목은 명세의 `title`에서 읽는다. 문서 안의 제목·내부 그림 이름은 바꾸지 않는다.
이 문서의 `기록.md`·`체크리스트.pdf` 같은 짧은 이름은 종류를 뜻하는 별칭이며,
실제 생성·존재 확인·전사·검증·결과 링크에는 반드시 공통 함수가 반환한 경로를 쓴다.
종류는 `체크리스트`, `기록`, `예비보고서`, `결과보고서`, `예비보고서표지`,
`결과보고서표지`, `손그림모사`, `부품그리기`, `따라그리기`, `예상결과`다.
저장 위치·예외·이력 보존 규칙은 `docs/schema/lab-artifact-naming.md`를 따른다.

보고서 본문 PDF(노션 내보내기 등)의 맨 앞에 IEEE 윤리 강령 표지 1쪽을 붙여 **최종 제출본 PDF**를 무손실 조립한다. 표지가 없거나 제출일이 달라졌으면 `make-lab-report-cover` 파이프라인으로 자동 생성한다.

## 절대 규칙

1. **표준 파일명은 공통 함수로 정한다.** `config.artifact_path('<실험NN>', '<예비보고서|결과보고서>')` (실험07 예: `실험07_Shift_Register_예비보고서.pdf`; 실험01~06은 기존 이름 유지). 공백 변형 파일이나 심볼릭 링크를 만들지 않는다.
2. **무손실 보존.** 본문에 포함된 손그림 결선도 등의 고해상도 이미지를 재인코딩하거나 압축하지 않고 `pypdf` 로 원본 스트림을 그대로 유지한다.
3. **단일 소스 원칙.** 학번·성명·교수명·제출일 형식은 하드코딩하지 않고 `.claude/과목정보.md` 에서만 읽는다.
4. **표지 누락 시 자동 생성 게이트.** 표지가 없으면 거절하지 않고 `make-lab-report-cover` 로직을 실행해 즉시 A4 1장 표지를 만든 뒤 병합으로 진행한다.
5. **입력 원본 자동 정리 (rm).** 병합 및 실측 검증이 완료되면 노션 내보내기 본문 PDF(UUID 접두사 파일 등)를 삭제(`rm`)하여 폴더를 깨끗하게 유지한다. 단, 출력 대상 파일과 동일하거나 검증에 실패한 경우에는 삭제하지 않는다. 삭제 자체가 실패하면(예: Windows 에서 파일이 열려 있음) 병합은 성공으로 두고 stderr 에 `경고: 본문 원본을 지우지 못했습니다` 를 남긴다 — 이 경고를 보면 사용자에게 원본이 남았다고 알린다.

## 실행 절차

0. **실험 번호와 보고서 종류 확정.**
   - 사용자가 "실험1 예비보고서 표지랑 합쳐줘" 처럼 부르면 실험 번호 1, 종류 `예비보고서` 로 확정.
   - 무엇을 만들지(예비보고서/결과보고서) 불명확하면 되묻고 멈춘다.

1. **본문 PDF 탐색.**
   - 사용자가 파일 경로(@...)를 직접 주었으면 그 파일을 쓴다.
   - 경로가 없으면 `<실험NN>/` 및 `<실험NN>/output/` 에서 본문 PDF를 탐색한다:
     ```bash
     python3 -c "
     from pathlib import Path
     from scripts.lab.merge_report import find_body_pdf
     print(find_body_pdf(Path('<실험NN>'), kind='<예비보고서|결과보고서>'))
     "
     ```
   - **완료 기준:** 본문 PDF 경로 1개가 확정되어야 한다. 후보가 0개거나 2개 이상이면 에러 메시지를 사용자에게 알리고 멈춘다.

2. **표지 PDF 확인 및 조건부 자동 생성.**
   - `config.artifact_path('<실험NN>', '<예비보고서표지|결과보고서표지>')` 가 존재하는지, 제출일이 일치하는지 확인.
   - 없거나 갱신이 필요하면 자동 생성:
     ```bash
     python3 -c "
     from pathlib import Path
     from scripts.lab.spec_parser import parse_spec
     from scripts.lab.merge_report import ensure_cover_pdf
     exp_dir = Path('<실험NN>')
     spec = parse_spec(exp_dir / '체크리스트/명세.md')
     print(ensure_cover_pdf(exp_dir, spec, '<예비보고서|결과보고서>'))
     "
     ```
   - **완료 기준:** 정확히 1쪽짜리 A4 표지 PDF 가 디스크에 실재해야 한다.

3. **무손실 병합 및 입력 원본 자동 정리.**
   - `scripts/lab/merge_report.py` 모듈 호출:
     ```bash
     python3 -m scripts.lab.merge_report --dir <실험NN> --kind <예비보고서|결과보고서>
     ```
   - 사용자가 본문 파일 경로를 직접 지정한 경우 `--body <파일경로>` 를 함께 넘긴다.
   - 병합 및 검증 성공 시 입력 원본 본문 PDF는 자동 삭제(`rm`)된다 (보존 필요 시 `--keep-body` 사용).
   - **완료 기준:** `config.artifact_path('<실험NN>', '<예비보고서|결과보고서>')` 가 디스크에 생성되고 입력 원본 PDF가 정리된다.

4. **실측 무결성 검증.**
   - 총 쪽수가 `표지(1) + 본문(N) = N + 1` 쪽인지, 1쪽 치수가 A4(210×297mm)인지 확인:
     ```bash
     python3 -c "
     from scripts.lab import config
     from pathlib import Path
     from scripts.lab.merge_report import verify_merged_pdf
     print(verify_merged_pdf(Path(config.artifact_path('<실험NN>', '<예비보고서|결과보고서>'))))
     "
     ```
   - **완료 기준:** 쪽수 불일치나 치수 오차 에러 없이 `valid: True` 가 반환되어야 한다.

5. **결과 안내.**
   - 생성된 최종 제출용 PDF 마크다운 링크와 총 쪽수, 포함된 표지/본문 요약을 출력한다.

## 비-목표

- 심볼릭 링크를 생성하지 않는다.
- 노션 API 로 PDF 를 직접 다운로드하지 않는다 (노션 PDF 는 사용자가 수동 내보내기).
- 본문 텍스트나 이미지를 임의로 변형·재압축하지 않는다.
