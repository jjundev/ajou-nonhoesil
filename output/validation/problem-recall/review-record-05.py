from pathlib import Path
import json,re,hashlib,shutil
out=Path('output/validation/problem-recall');stage=Path((out/'stage-05.txt').read_text(encoding='utf-8-sig').strip());base=json.loads((out/'baseline-05.json').read_text(encoding='utf-8'));m=base['manifest'];ss={s['id']:s for s in m['sources']};ts={t['id']:t for t in m['topics']};data=json.loads((out/'recall-data-05.json').read_text(encoding='utf-8'));orig=json.loads((out/'original-fragments-05.json').read_text(encoding='utf-8'));r=Path('docs/learning-pack-source/실험05/problem-explanations')
rows=['| 문항 ID | 단서 | 개념/기호 | 적용 조건/선택 이유 | 소문항 범위 | 원문 path/PDF page | 경고 보존 | 요약 일치 | 검토 결과 |','|---|---|---|---|---|---|---|---|---|']
for p in m['problems']:
 if p['status']!='included':continue
 ident=p['id'];new=(r/(ident+'.html')).read_text(encoding='utf-8');stripped=re.sub(r'<div class="layer formal" data-explanation="recall">.*?</div>','',new,count=1,flags=re.S);stripped=re.sub(r'<p data-summary="recall">.*?</p>','',stripped,count=1,flags=re.S);assert stripped==orig[ident]
 refs=p['sources']+[r for t in p['topics'] for r in ts[t]['sources']];refs=list(dict.fromkeys((ss[x['source_id']]['path'],x.get('pdf_page')) for x in refs));source='; '.join(name+(f' p{pg}' if pg else '（PDF 아님; 보조자료）') for name,pg in refs)
 scope={'q-demux-from-dec-graded':'(1) 회로 변경 (2) 기능 차이','q-excess3-enc-exam':'지정 네 행·회로식','q-excess3-enc-6row':'지정 여섯 행·회로식','q-sa-74hc143':'A0·A1·A2·GS·EO 역할·IC 식별 한계'}.get(ident,'기존 원문 표/식/정의와 전체 solve/verify 보존')
 rows.append('| '+' | '.join([ident,*[v.replace('|','/') for v in data[ident]],scope,source,'old six sections exact; 기존 경고 그대로','실제 4조건 요약/본문 대조','content=self_review; source_visual=pass; browser=pass; independent=not_run'])+' |')
report='''# 실험05 핵심 개념 보충 검증

검토자: Task8 저작 에이전트 자체 검토. 독립 리뷰어 검토는 수행하지 않았어요(independent=not_run).

## 원문과 실제 계산

manifest의 19 included ID와 순서, payload/기존 solve/verify를 대조했어요. 참조 PDF 23개 페이지를 PyMuPDF 1.5배 PNG로 렌더링하고 view_image로 전부 직접 확인했어요. NOT 버블, NAND 출력 반전, VCC 잔여 입력, AND 출력 극성, SW5…SW0/Bit3…Bit0, bit0 먼저인 표, 74HC148 이름·EI 접지·핀을 확인했어요. 보조 DOCX는 새로 해석하지 않았고 같은 문항 PDF를 근거로 사용했어요. 원문 hash는 stage/published check가 확인해요.

computations-05.json에는 3×8/2×4 minterm 8/4행, one-hot 8입력 번호, 4입력 NAND encoder 4행, priority 지정 6행과 256 활성 마스크, Excess-3 10자리/비트보수, SW 6행 회로 OR식, DMUX 주소×D 8행, quiz 네 행 계산을 실제 실행해 저장했어요. SW0…SW5 결과는 0011·0100·0101·0110·0111·1000이고 시험 네 행은 0011·0101·0111·1000이에요. D1/D2 동시 일반 OR는 011, 번호 큰 쪽 priority는 010이에요. HC148 지정 표는 HHH·LLH·LLL이고 EI=H는 교안 기능표의 HHH와 대조했어요.

원문 단답형 p2의 이름은 74HC143이며 그 페이지에 칩 그림/기능표가 없어요. 교안 p10 그림은 74HC148, p11은 active-low 우선순위 코드 표예요. 원문 역할은 A0~A2 Data Output, GS Priority Flag Output, EO Enable Output예요. 두 IC가 동일하다거나 실제143 기능을 확인했다고 주장하지 않아요. 기존 상세 EI/GS/EO 상태를 그대로 보존하지만 새 recall/summary는 148 해석에 따른 조건부 설명 및 제공 자료 검증 한계를 명시해요. GS/EO 상세 기능표는 제공 교안에 없으므로 독립 계산 pass로 표시하지 않아요.

## 브라우저

최종 stage에서 실제 Chrome Playwright로 375×900/1280×900 × light/dark의 19문항 전부 hash 이동·현재 목차·recall·우측 요약을 확인했어요(76 cases, 152 개별 screenshots). 20 실제 픽셀 contact sheets를 view_image로 읽어 본문/요약 내용·줄바꿈·두 테마 대비를 직접 확인했어요. pageerror/KaTeX error/깨진 이미지/문서 가로 넘침 모두 0이에요. equation/table 카드 16px padding·1px border·overflow:auto 확인, 모바일 긴 카드 20회 실제 내부 scroll 및 touch 이벤트 후 hash 유지 확인했어요. 모바일 drawer 닫기, 이전/다음, Enter focus, 읽음 저장/새로고침 유지·실험설명 namespace 분리를 실행했어요. JS 꺼진 375px에서도 19 articles와 recall/solve/verify 57구역 및 목차가 모두 보여요. no-js 실제 screenshot도 view_image로 확인했어요. 재사용 harness 마지막 print는 이전 실험의 48/12 숫자를 남겼지만 JSON 실제 76개 case와 DOM assertion 19개가 증거예요.

문제 읽기→understand gap은 각 76 case의 metrics에서 24px margin+24px padding+1px border예요. 새 recall은 숨기거나 접지 않았어요.

## 문항별 검토

'''+ '\n'.join(rows)+'\n\n## 보존\n\n새 recall과 summary를 제거하면 19개 원고 전체 문자열이 원본과 정확히 같아요. 기존 여섯 구역·풀이·경고·소문항·요약이 동일해요. 최종 stage의 experiment/sources/topics/problems/checks/review/note presentation version과 설명 밖 generated 파일 SHA256은 baseline과 동일하게 검증했어요. 발행 후 사용자 파일까지 동일 SHA256을 재검증해요.\n'
(r/'검증결과.md').write_text(report,encoding='utf-8');shutil.copy2(r/'검증결과.md',stage/'자료/problem-explanations/검증결과.md')
p=stage/'자료/manifest.json';new=json.loads(p.read_text(encoding='utf-8'));new['explanation_checks']={'source_visual':'pass','content':'self_review','independent':'not_run','browser':'pass'};new['generated_files']=sorted(f.relative_to(stage).as_posix() for f in stage.rglob('*') if f.is_file());p.write_text(json.dumps(new,ensure_ascii=False,indent=2),encoding='utf-8')
for key in ('experiment','sources','topics','problems','checks','review_presentation_version','note_presentation_version'):assert m.get(key)==new.get(key),key
for rel,digest in base['files'].items():
 if rel in m.get('generated_files',[]):assert hashlib.sha256((stage/rel).read_bytes()).hexdigest()==digest,rel
assert new['problem_explanation_version']==2
verify=Path('docs/verify/logic-lab-problem-recall.md');s=verify.read_text(encoding='utf-8');s+='\n\n## 실험05 — 19문항\n\n'+'\n'.join(rows)+'\n\n상세 증거: docs/learning-pack-source/실험05/problem-explanations/검증결과.md; content=self_review, independent=not_run.\n';verify.write_text(s,encoding='utf-8')
print('76 browser cases and exact 19 fragment removal verified; stage preservation and real review states ready')
