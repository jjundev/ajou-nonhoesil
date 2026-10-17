"""Opt-in layout patches. Keep unversioned workbook bytes unchanged."""

CSS='''/* 퀴즈 작도: 고정된 인쇄 크기, 넘치면 검사 실패 */
#book .work-board-block { flex: none; }
#book .work-board img { display: block; width: 100mm; min-width: 90mm; height: auto; margin: 0 auto; }
.page-center > .work-board-block ~ .work { min-height: 25mm; }
'''
MOVE='''  const boards = [...panel.querySelectorAll('.work-board')];
  if (boards.length) {
    const area = el('div', 'work-board-block');
    for (const board of boards) {
      const owner = board.closest('.block');
      area.append(board);
      if (owner && !owner.querySelector('.prose').textContent.trim() && !owner.querySelector('img, table, .katex')) owner.remove();
    }
    center.append(area);
  }
'''
REMOVE='''  for (const board of panel.querySelectorAll('.work-board')) {
    const owner = board.closest('.block');
    board.remove();
    if (owner && !owner.querySelector('.prose').textContent.trim() && !owner.querySelector('img, table, .katex')) owner.remove();
  }
'''
SCAN='''    for (const page of book.querySelectorAll('.page--problem')) {
      const center = page.querySelector('.page-center');
      const bad = [...page.querySelectorAll('.work-board img')].some(img => {
        const r=img.getBoundingClientRect(), c=center.getBoundingClientRect();
        return img.offsetWidth < 90*96/25.4-1 || r.left<c.left-1 || r.right>c.right+1 || r.bottom>c.bottom+1;
      });
      if ((bad || (center.querySelector('.work-board-block') && (center.scrollHeight>center.clientHeight+1 || center.scrollWidth>center.clientWidth+1))) && !overflow.includes(page.id)) {
        page.dataset.overflow=''; overflow.push(page.id);
      }
    }
'''


def apply_quiz_patches(text: str, template_name: str) -> str:
    if template_name not in ('problem.html','answer.html'):raise ValueError('Unknown quiz template')
    center="  const center = el('div', 'page-center');"
    start="  const quizBoardPage = !!panel.querySelector('.work-board');\n"
    start+=(REMOVE if template_name=='answer.html' else '')+center
    patches=[('/* 수식 */',CSS+'/* 수식 */'),(center,start)]
    if template_name=='problem.html':
        anchor="  center.append(el('div', 'work'));"
        patches.append((anchor,MOVE+anchor))
    row='  row.append(panel, center);'
    patches.append((row,"  if (quizBoardPage) {\n    const schematic = center.querySelector('.fig-band');\n    if (schematic) panel.insertBefore(schematic, panel.querySelector('.conditions')?.closest('.block') || null);\n  }\n"+row))
    patches.append(
                    ("    document.body.dataset.overflow = overflow.join(',');",SCAN+"    document.body.dataset.overflow = overflow.join(',');")
    )
    for old,new in patches:
        if text.count(old)!=1:raise ValueError('Quiz patch anchor not unique in '+template_name+': '+old[:30])
        text=text.replace(old,new)
    return text
