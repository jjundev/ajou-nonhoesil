from fixtures import *
import json,shutil,unicodedata
from solution_video.sources import discover,freeze_sources,parse_selector,KINDS,DATA_DIR
from solution_video.contracts import InputError
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
    def test_missing_pack_and_freeze(self):
        failures=[]; discover(REPO,'실험09',None,failures)
        self.assertIn('experiment pack missing: 실험09',[f['reason'] for f in failures])
        frozen=freeze_sources(discover(REPO,'실험05',['q-dec2x4-design']),self.run)
        self.assertFalse(Path(frozen[0]['figure_refs'][0]).is_absolute())
        self.assertTrue((self.run/frozen[0]['figure_refs'][0]).is_file())
        self.assertEqual(Path(frozen[0]['figure_refs'][0]).name,'q-dec2x4-design-solution-01.png')
