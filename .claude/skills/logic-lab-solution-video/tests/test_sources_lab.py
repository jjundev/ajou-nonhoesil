from fixtures import *
import json,shutil,unicodedata
from solution_video.sources import discover,freeze_sources,parse_selector,KINDS,DATA_DIR
from solution_video.contracts import InputError
def draw_rows(page,x0,y0,rows,w=60,h=24):
    """rows of cells; a cell is a text or (columns spanned, text). A spanned cell has no inner line, so extract() reads None."""
    import fitz
    for r,row in enumerate(rows):
        c=0
        for cell in row:
            span,text=cell if isinstance(cell,tuple) else (1,cell)
            rect=fitz.Rect(x0+w*c,y0+h*r,x0+w*(c+span),y0+h*(r+1)); page.draw_rect(rect,color=(0,0,0),width=.8)
            if text: page.insert_text((rect.x0+4,rect.y0+16),text,fontname='korea',fontsize=10)
            c+=span
def redraw(pack,suffix,build):
    """Run build(page) on every page of the pack's PDF and save it in place."""
    import fitz
    pdf=pack/('실험06_'+suffix+'.pdf'); doc=fitz.open(pdf)
    for page in doc: build(page)
    doc.save(pack/'tmp.pdf'); doc.close(); (pack/'tmp.pdf').replace(pdf)
class LabSourceTests(Sandbox):
    def test_kinds_match_review_pack(self):
        sys.path.insert(0,str(REPO))
        from scripts.lab.review_pack.workbook_content import KINDS as PACK
        self.assertEqual(KINDS,PACK)
    def test_data_dir_matches_review_pack(self):
        sys.path.insert(0,str(REPO))
        from scripts.lab.config import PACK_DATA_DIR
        self.assertEqual(DATA_DIR,PACK_DATA_DIR)
    def test_selector_forms(self):
        self.assertEqual(parse_selector('실험05'),['실험05']); self.assertEqual(parse_selector('5'),['실험05'])
        self.assertEqual(parse_selector('05'),['실험05']); self.assertEqual(parse_selector('03-05'),['실험03','실험04','실험05'])
        self.assertEqual(parse_selector('실험03-05'),['실험03','실험04','실험05'])
        for bad in ['실험00','실험11','05-03','abc','']:
            with self.assertRaises(InputError): parse_selector(bad)
    def test_experiment05_pairs_and_labels(self):
        pairs={p['problem_id']:p for p in discover(REPO,'실험05',None,[])}
        self.assertEqual(pairs['q-dec3x8']['label'],'예상문제1')
        self.assertEqual((pairs['q-dec3x8']['problem']['page_index'],pairs['q-dec3x8']['answer']['page_index']),(0,0))
        self.assertEqual(pairs['q-prio-exam']['label'],'기출3')
        self.assertEqual(pairs['q-prio-exam']['title'],'8×3 우선순위 인코더 — 여러 비트가 켜진 입력')
        self.assertEqual(pairs['q-prio-exam']['experiments'],['실험05'])
        self.assertTrue(pairs['q-prio-exam']['md_snapshot'].endswith('실험05_기출풀이.md'))
    def test_select_by_label_or_id(self):
        self.assertEqual([p['problem_id'] for p in discover(REPO,'실험05',['기출3'])],['q-prio-exam'])
        self.assertEqual([p['label'] for p in discover(REPO,'실험05',['q-dec2x4-design'])],['기출4'])
        with self.assertRaisesRegex(InputError,'outside range'): discover(REPO,'실험05',['기출99'])
    def test_range_label_must_be_qualified(self):
        with self.assertRaisesRegex(InputError,'ambiguous label'): discover(REPO,'03-05',['기출3'],[])
        self.assertEqual([p['problem_id'] for p in discover(REPO,'03-05',['실험05:기출3'],[])],['q-prio-exam'])
        self.assertEqual([p['problem_id'] for p in discover(REPO,'03-05',['q-prio-exam'],[])],['q-prio-exam'])
    def test_figure_refs_are_exact_per_problem(self):
        p=discover(REPO,'실험05',['q-dec2x4-design'])[0]
        self.assertEqual([Path(f).name for f in p['figure_refs']],['q-dec2x4-design-solution-01.png'])
        self.assertTrue(all(Path(f).is_absolute() for f in p['figure_refs']))
    def test_labels_follow_current_manifest_order(self):
        repo=self.run/'repo'; pack=repo/'복습노트/실험05'; shutil.copytree(REPO/'복습노트/실험05',pack)
        m=json.loads((pack/'자료/manifest.json').read_text(encoding='utf-8')); inc=[p for p in m['problems'] if p['status']=='included']
        a,b=m['problems'].index(inc[0]),m['problems'].index(inc[1]); m['problems'][a],m['problems'][b]=m['problems'][b],m['problems'][a]
        (pack/'자료/manifest.json').write_text(json.dumps(m,ensure_ascii=False),encoding='utf-8')
        failures=[]; discover(repo,'실험05',None,failures)
        self.assertIn('header/list mismatch',' '.join(f['reason'] for f in failures))
    def test_nfd_folder_names(self):
        repo=self.run/'repo'; root=repo/unicodedata.normalize('NFD','복습노트'); root.mkdir(parents=True)
        shutil.copytree(REPO/'복습노트/실험05',root/unicodedata.normalize('NFD','실험05'))
        self.assertEqual(len(discover(repo,'실험05',None,[])),len(discover(REPO,'실험05',None,[])))
    def test_nfd_file_names(self):
        # 폴더 이름만 NFD 이던 test_nfd_folder_names 의 빈틈: 팩 안의 모든 파일·폴더 이름이 NFD 여도 같은 문항을 찾는다.
        nfd=lambda s:unicodedata.normalize('NFD',s)
        def copy_nfd(src,dst):
            dst.mkdir(parents=True)
            for x in src.iterdir():
                if x.is_dir(): copy_nfd(x,dst/nfd(x.name))
                else: shutil.copyfile(x,dst/nfd(x.name))
        repo=self.run/'repo'; pack=repo/nfd('복습노트')/nfd('실험05'); copy_nfd(REPO/'복습노트/실험05',pack)
        if any(x.name!=nfd(x.name) for x in pack.rglob('*')): self.skipTest('this file system does not keep NFD file names')
        def shape(root):
            failures=[]; pairs=discover(root,'실험05',None,failures)
            self.assertEqual(failures,[])
            return [(p['problem_id'],len(p['figure_refs']),bool(p['md_snapshot'])) for p in pairs]
        expected=shape(REPO)
        self.assertTrue(expected and any(n for _,n,_ in expected) and all(has for _,_,has in expected))
        self.assertEqual(shape(repo),expected)
    def test_labels_are_recomputed_when_pack_is_rebuilt(self):
        repo=self.run/'repo'; table=[['A','B','Y'],['0','1','가']]
        problems=[dict(id='q-a',kind='past',title='가산기 설계'),dict(id='q-b',kind='past',title='감산기 설계')]
        synthetic_pack(repo,'실험06',problems,table,table)
        failures=[]; pairs=discover(repo,'실험06',None,failures)
        self.assertEqual(failures,[]); self.assertEqual([(p['problem_id'],p['label']) for p in pairs],[('q-a','기출1'),('q-b','기출2')])
        self.assertEqual([p['problem_id'] for p in discover(repo,'실험06',['기출1'],[])],['q-a'])
        # 순서를 바꿔 다시 만들면 라벨이 새 순서로 다시 계산되고, 쪽 머리와도 어긋나지 않는다(성공 경로).
        synthetic_pack(repo,'실험06',problems[::-1],table,table)
        failures=[]; pairs=discover(repo,'실험06',None,failures)
        self.assertEqual(failures,[]); self.assertEqual([(p['problem_id'],p['label']) for p in pairs],[('q-b','기출1'),('q-a','기출2')])
        self.assertEqual([p['problem_id'] for p in discover(repo,'실험06',['기출1'],[])],['q-b'])
    def test_missing_pdf_pair_fails_per_problem_with_label(self):
        # 팩이 없을 때만 label 이 None 이다. PDF 짝이 없으면 manifest 는 읽혔으므로 문항마다 라벨을 단 실패가 된다.
        repo=self.run/'repo'; table=[['A','B'],['0','1']]
        problems=[dict(id='q-a',kind='past',title='가산기 설계'),dict(id='q-b',kind='past',title='감산기 설계')]
        pack=synthetic_pack(repo,'실험06',problems,table,table)
        (pack/'실험06_기출풀이.pdf').unlink()
        failures=[]; pairs=discover(repo,'실험06',None,failures)
        self.assertEqual(pairs,[])
        self.assertEqual([(f['problem_id'],f['experiment'],f['label'],f['reason']) for f in failures],
            [('q-a','실험06','기출1','missing or ambiguous PDF pair'),('q-b','실험06','기출2','missing or ambiguous PDF pair')])
    def tables_pack(self,table,answer_table,after_write=None):
        # 합성 팩 하나(문항 q-a). after_write(pack) 가 있으면 PDF 를 쓴 직후 손볼 수 있다.
        repo=self.run/'repo'; pack=synthetic_pack(repo,'실험06',[dict(id='q-a',kind='past',title='진리표 작성')],table,answer_table)
        if after_write: after_write(pack)
        failures=[]; return discover(repo,'실험06',None,failures),failures
    def test_table_row_swap_is_rejected(self):
        # 글자 multiset 은 같으므로 기존 대조는 통과한다. 행 순서가 바뀐 것은 표 대조만 잡는다.
        pairs,failures=self.tables_pack([['A','B'],['0','1'],['1','0']],[['A','B'],['1','0'],['0','1']])
        self.assertEqual(pairs,[])
        self.assertEqual([(f['problem_id'],f['label']) for f in failures],[('q-a','기출1')])
        self.assertIn('table rows differ: q-a table 1 row 2',failures[0]['reason'])
    def test_table_column_swap_is_rejected(self):
        pairs,failures=self.tables_pack([['A','B'],['0','1']],[['B','A'],['1','0']])
        self.assertEqual(pairs,[]); self.assertIn('table rows differ: q-a table 1 row 1',failures[0]['reason'])
    def test_identical_tables_pass(self):
        table=[['A','B'],['0','1'],['1','0']]
        pairs,failures=self.tables_pack(table,table)
        self.assertEqual(failures,[]); self.assertEqual([p['problem_id'] for p in pairs],['q-a'])
    def test_answer_without_table_is_skipped(self):
        # 해설지에 같은 글자가 표가 아니라 글줄로만 있다(선이 없어 find_tables 가 못 찾는다). 표 때문에 실패하면 안 된다.
        def flatten(pack):
            import fitz
            pdf=pack/'실험06_기출풀이.pdf'; doc=fitz.open(pdf)
            for page in doc: page.insert_text((34,200),'A B 0 1 1 0',fontname='korea',fontsize=10)
            doc.save(pack/'tmp.pdf'); doc.close(); (pack/'tmp.pdf').replace(pdf)
        pairs,failures=self.tables_pack([['A','B'],['0','1'],['1','0']],None,flatten)
        self.assertEqual(failures,[]); self.assertEqual([p['problem_id'] for p in pairs],['q-a'])
        from solution_video.sources import _table_mismatch
        self.assertIsNone(_table_mismatch(pairs[0]['problem'],pairs[0]['answer']))
    def test_table_of_another_shape_is_skipped(self):
        # 글자는 같지만 모양이 다르면(3x2 대 2x3) 같은 표로 볼 근거가 없어 건너뛴다.
        pairs,failures=self.tables_pack([['A','B'],['0','1'],['1','0']],[['A','B','0'],['1','1','0']])
        self.assertEqual(failures,[]); self.assertEqual([p['problem_id'] for p in pairs],['q-a'])
    def test_table_check_survives_find_tables_error(self):
        # 표를 읽다 예외가 나면 그 쪽은 표가 없는 것으로 보고 건너뛴다: 글자 대조를 이미 통과한 입력을 새로 막지 않는다.
        import fitz
        from unittest.mock import patch
        swapped=([['A','B'],['0','1'],['1','0']],[['A','B'],['1','0'],['0','1']])
        pairs,failures=self.tables_pack(*swapped)
        self.assertEqual(pairs,[]); self.assertIn('table rows differ',failures[0]['reason'])
        with patch.object(fitz.Page,'find_tables',side_effect=RuntimeError('boom')):
            pairs,failures=self.tables_pack(*swapped)
        self.assertEqual(failures,[]); self.assertEqual([p['problem_id'] for p in pairs],['q-a'])
    def test_merged_cell_table_row_swap_is_rejected(self):
        # 병합 칸은 extract() 가 None 으로 준다. None 을 '' 로 바꾸지 않으면 TypeError 가 삼켜져 검사가 조용히 꺼진다.
        head=[(2,'H'),'C']
        def tables(problem_body,answer_body):
            def hook(pack):
                redraw(pack,'기출문제',lambda pg:draw_rows(pg,300,200,[head]+problem_body))
                redraw(pack,'기출풀이',lambda pg:draw_rows(pg,34,200,[head]+answer_body))
            return self.tables_pack(None,None,hook)
        pairs,failures=tables([['0','1','2'],['3','4','5']],[['3','4','5'],['0','1','2']])
        self.assertEqual(pairs,[]); self.assertIn('table rows differ: q-a table 1 row 2',failures[0]['reason'])
        pairs,failures=tables([['0','1','2'],['3','4','5']],[['0','1','2'],['3','4','5']])
        self.assertEqual(failures,[]); self.assertEqual(len(pairs),1)
        from solution_video.sources import _tables
        read=_tables(pairs[0]['problem'])  # 빈 목록이면 읽기가 조용히 실패한 것이다
        self.assertEqual(read,[[['H','','C'],['0','1','2'],['3','4','5']]])
    def test_wrapped_header_cell_matches_unwrapped(self):
        # 해설지 헤더 칸이 두 줄로 접혀 extract() 가 'AND\n출력' 을 주어도 줄 바꿈·공백은 값이 아니다.
        import fitz
        pairs,failures=self.tables_pack([['AND출력','B'],['0','1']],[['AND\n출력','B'],['0','1']])
        self.assertEqual(failures,[]); self.assertEqual(len(pairs),1)
        with fitz.open(pairs[0]['answer']['snapshot']) as d:
            self.assertEqual(d[0].find_tables().tables[0].extract()[0][0],'AND\n출력')  # 접힌 칸이 실제로 만들어졌다
    def test_solution_table_cannot_vouch_for_a_swapped_panel_copy(self):
        # 후보는 해설지 조건 패널 안의 표뿐이다: 풀이 단계에 문제지와 같은 표가 있어도 패널 복사본이 바뀌면 거부한다.
        import fitz
        problem=[['A','B'],['0','1'],['1','0']]; swapped=[['A','B'],['1','0'],['0','1']]
        def answer_page(panel_rows,step_rows):
            def hook(pack):
                def build(pg):
                    pg.draw_rect((22,59,286,572),fill=(246/255,246/255,243/255),color=None)
                    draw_rows(pg,34,200,panel_rows); draw_rows(pg,330,200,step_rows)
                redraw(pack,'기출풀이',build)
            return self.tables_pack(problem,None,hook)
        pairs,failures=answer_page(swapped,problem)
        self.assertEqual(pairs,[]); self.assertIn('table rows differ: q-a table 1 row 2',failures[0]['reason'])
        # 반대로 풀이 단계 표가 달라도 패널 복사본이 같으면 통과한다.
        pairs,failures=answer_page(problem,swapped)
        self.assertEqual(failures,[]); self.assertEqual(len(pairs),1)
    def test_real_packs_have_no_table_false_positive(self):
        from solution_video.sources import _tables
        expected={'실험01':3,'실험02':0,'실험03':5,'실험04':5,'실험05':8}  # 문제지 표 개수
        for n,count in expected.items():
            failures=[]; pairs=discover(REPO,n,None,failures)
            self.assertEqual([f['reason'] for f in failures if 'table rows differ' in f['reason']],[],n)
            # 오탐이 없다는 말은 표가 실제로 비교됐을 때만 뜻이 있다: 문제지 표마다 해설지 패널에 같은 모양이 있고 하나와 일치한다.
            total=checked=matched=0
            for p in pairs:
                panel=_tables(p['answer'],panel=True)
                for table in _tables(p['problem']):
                    same=[a for a in panel if [len(r) for r in a]==[len(r) for r in table]]
                    total+=1; checked+=bool(same); matched+=table in same
            self.assertEqual((total,checked,matched),(count,count,count),n)
    def test_svg_refs_are_exact_per_problem(self):
        p=discover(REPO,'실험05',['q-dec2x4-design'])[0]
        self.assertEqual([Path(f).name for f in p['figure_svg_refs']],['q-dec2x4-design-solution-01.svg'])
        self.assertTrue(all(Path(f).is_absolute() for f in p['figure_svg_refs'])); self.assertEqual(p['figure_svg_missing'],[])
        # 접두가 겹치는 다른 문항(q-demux-from-dec / q-demux-from-dec-graded)의 SVG 는 섞이지 않는다.
        pairs={x['problem_id']:x for x in discover(REPO,'실험05',['q-demux-from-dec','q-demux-from-dec-graded'])}
        self.assertEqual([Path(f).name for f in pairs['q-demux-from-dec']['figure_svg_refs']],['q-demux-from-dec-solution-01.svg'])
        self.assertEqual([Path(f).name for f in pairs['q-demux-from-dec-graded']['figure_svg_refs']],['q-demux-from-dec-graded-solution-01.svg'])
    def test_svg_is_frozen_with_provenance(self):
        frozen=freeze_sources(discover(REPO,'실험05',['q-dec2x4-design']),self.run)
        rel=frozen[0]['figure_svg_refs'][0]
        self.assertFalse(Path(rel).is_absolute()); self.assertTrue((self.run/rel).is_file())
        self.assertEqual(Path(rel).name,'q-dec2x4-design-solution-01.svg')
        files=json.loads((self.run/'source/inputs.json').read_text(encoding='utf-8'))['files']
        self.assertIn(rel,files); self.assertTrue(files[rel]['original'].endswith('q-dec2x4-design-solution-01.svg'))
        # PNG 와 같은 규칙(source/snapshots/figures/<파일 sha>/<이름>)으로 동결된다. 픽셀 대조는 PNG 만 쓴다.
        self.assertEqual(Path(rel).parent.parent,Path('source/snapshots/figures'))
        self.assertEqual(Path(rel).parent.name,files[rel]['sha256'])
        self.assertEqual(Path(rel).parent.parent,Path(frozen[0]['figure_refs'][0]).parent.parent)
    def solutions_copy(self):
        repo=self.run/'repo'; shutil.copytree(REPO/'복습노트/실험05',repo/'복습노트/실험05')
        return repo,repo/'복습노트/실험05/자료/figures/solutions'
    def test_missing_svg_warns_without_failing(self):
        repo,solutions=self.solutions_copy(); (solutions/'q-dec2x4-design-solution-01.svg').unlink()
        failures=[]; pairs={p['problem_id']:p for p in discover(repo,'실험05',['q-dec2x4-design'],failures)}
        self.assertEqual(failures,[])
        self.assertEqual(pairs['q-dec2x4-design']['figure_svg_refs'],[]); self.assertEqual(pairs['q-dec2x4-design']['figure_svg_missing'],['q-dec2x4-design-solution-01.png'])
        self.assertEqual([Path(f).name for f in pairs['q-dec2x4-design']['figure_refs']],['q-dec2x4-design-solution-01.png'])
    def test_svg_without_png_and_extra_svg(self):
        # SVG 는 근거 보존용이라 PNG 와 짝이 맞지 않아도 모은다. 누락 경고는 PNG 기준이다.
        repo,solutions=self.solutions_copy(); shutil.copyfile(solutions/'q-dec2x4-design-solution-01.svg',solutions/'q-dec2x4-design-solution-02.svg')
        (solutions/'q-enc4x2-design-solution-01.png').unlink()
        pairs={p['problem_id']:p for p in discover(repo,'실험05',['q-dec2x4-design','q-enc4x2-design'],[])}
        a,b=pairs['q-dec2x4-design'],pairs['q-enc4x2-design']
        self.assertEqual([Path(f).name for f in a['figure_svg_refs']],['q-dec2x4-design-solution-01.svg','q-dec2x4-design-solution-02.svg'])
        self.assertEqual(a['figure_svg_missing'],[])
        self.assertEqual((b['figure_refs'],[Path(f).name for f in b['figure_svg_refs']],b['figure_svg_missing']),([],['q-enc4x2-design-solution-01.svg'],[]))
    def test_freeze_accepts_pair_without_svg_keys(self):
        # 옛 pair 에는 두 키가 없다. 읽는 쪽은 .get 으로 받는다.
        pair=discover(REPO,'실험05',['q-dec2x4-design'])[0]; del pair['figure_svg_refs'],pair['figure_svg_missing']
        frozen=freeze_sources([pair],self.run)
        self.assertEqual(frozen[0].get('figure_svg_refs',[]),[]); self.assertEqual(len(frozen[0]['figure_refs']),1)
    def test_missing_pack_and_freeze(self):
        failures=[]; discover(REPO,'실험09',None,failures)
        self.assertIn('experiment pack missing: 실험09',[f['reason'] for f in failures])
        self.assertEqual([f['label'] for f in failures],[None])  # experiment-level: no problem, so no label
        frozen=freeze_sources(discover(REPO,'실험05',['q-dec2x4-design']),self.run)
        self.assertFalse(Path(frozen[0]['figure_refs'][0]).is_absolute())
        self.assertTrue((self.run/frozen[0]['figure_refs'][0]).is_file())
        self.assertEqual(Path(frozen[0]['figure_refs'][0]).name,'q-dec2x4-design-solution-01.png')
