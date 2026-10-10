from fixtures import *
from solution_video.util import read,write
import importlib.util
spec=importlib.util.spec_from_file_location('solution_cli',S/'scripts/video.py'); cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)
class CLITests(Sandbox):
    def test_warning_returned_and_printed_before_voice(self):
        from unittest.mock import patch
        from test_manifest import example
        from types import SimpleNamespace
        import io,contextlib,json
        m,l,c,r=example();m['segments'][1]['caption_text']='이 R_L을 봅니다.'
        h=cli.content_fingerprint(m,l,c);c['input_hash']=r['input_hash']=h
        for name,data in [('source/manifest.json',m),('layers/layers.json',l),('source/coverage.json',c),('source/circuit-review.json',r),('source/config.json',cli.default_config())]:write(self.run/name,data)
        write(self.run/'run.json',dict(batch=str(self.run/'batch'),review=False))
        write(self.run/'batch/batch.json',dict(items=[]));stderr=io.StringIO()
        def voice(segments,run,*args,**kwargs):
            self.assertIn('number_before_symbol',stderr.getvalue())
            audio=[make_audio(s['id'],24000,run) for s in segments]
            write(run/'source/audio.json',dict(voices=audio));return audio
        with patch.object(cli,'_gate'),contextlib.redirect_stderr(stderr):
            checked=cli.run_stage('check',self.run,SimpleNamespace())
            self.assertEqual(checked['status'],'passed');self.assertEqual(len(checked.get('warnings',[])),1)
            # Synthetic content fixture has no input-stage records; state gates have separate tests.
            (self.run/'state.json').unlink()
            with patch.object(cli,'generate_voice',side_effect=voice):
                result=cli.run_stage('tts',self.run,SimpleNamespace(config=None,env_file=None,approve_review=False),transport=lambda p:{})
            self.assertEqual(result['status'],'passed');self.assertEqual(len(result.get('warnings',[])),1)
        self.assertEqual(read(self.run/'source/manifest.json')['segments'][1]['caption_text'],'이 R_L을 봅니다.')

    def test_invalid_lesson_blocks_paid_voice(self):
        from unittest.mock import patch
        from test_manifest import example
        from solution_video.util import write
        from solution_video.review_adapter import default_config
        from types import SimpleNamespace
        m,l,c,r=example()
        for name,data in [('source/manifest.json',m),('layers/layers.json',l),('source/coverage.json',c),('source/circuit-review.json',r),('source/config.json',default_config()),('source/lesson.json',dict(schema_version=1,steps=[]))]:write(self.run/name,data)
        with patch.object(cli,'_gate'),patch.object(cli,'generate_voice') as voice:
            with self.assertRaisesRegex(ValueError,'lesson'):cli.run_stage('tts',self.run,SimpleNamespace(config=None,env_file=None,approve_review=False))
            voice.assert_not_called()
    def test_invalid_caption_before_paid_voice(self):
        from unittest.mock import patch
        from test_manifest import example
        from solution_video.util import write
        from solution_video.review_adapter import default_config
        from solution_video.contracts import InputError
        from types import SimpleNamespace
        for field in ['caption_text','text']:
            m,l,c,r=example();bad='너무 긴 설명을 같은 구절로 계속 이어갑니다 '*7
            m['segments'][1][field]=bad
            h=cli.content_fingerprint(m,l,c);c['input_hash']=r['input_hash']=h
            for name,data in [('source/manifest.json',m),('layers/layers.json',l),('source/coverage.json',c),('source/circuit-review.json',r),('source/config.json',default_config())]:write(self.run/name,data)
            write(self.run/'run.json',dict(batch=str(self.run/'batch'),review=False));write(self.run/'batch/batch.json',dict(items=[]))
            with self.subTest(field=field),patch.object(cli,'_gate'),patch.object(cli,'generate_voice',side_effect=AssertionError('paid generation reached')) as voice:
                with self.assertRaises(InputError) as caught:cli.run_stage('tts',self.run,SimpleNamespace(config=None,env_file=None,approve_review=False))
                self.assertIn('segment write',str(caught.exception));self.assertIn('너무 긴 설명',str(caught.exception));voice.assert_not_called()
    def test_invalid_sentence_terminator_before_paid_voice(self):
        from unittest.mock import patch
        from test_manifest import example
        from solution_video.util import write
        from solution_video.review_adapter import default_config
        from solution_video.contracts import InputError
        from types import SimpleNamespace
        for bad in ['맞습니까? 다음입니다.','좋습니다! 다음입니다.','생략… 다음입니다.','“맞습니까?” 다음입니다.']:
            m,l,c,r=example();field='caption_text'
            m['segments'][1][field]=bad
            h=cli.content_fingerprint(m,l,c);c['input_hash']=r['input_hash']=h
            for name,data in [('source/manifest.json',m),('layers/layers.json',l),('source/coverage.json',c),('source/circuit-review.json',r),('source/config.json',default_config())]:write(self.run/name,data)
            write(self.run/'run.json',dict(batch=str(self.run/'batch'),review=False));write(self.run/'batch/batch.json',dict(items=[]))
            with self.subTest(text=bad),patch.object(cli,'_gate'),patch.object(cli,'generate_voice',side_effect=AssertionError('paid generation reached')) as voice:
                with self.assertRaises(InputError) as caught:cli.run_stage('tts',self.run,SimpleNamespace(config=None,env_file=None,approve_review=False))
                self.assertIn('segment write',str(caught.exception));self.assertIn(bad,str(caught.exception));voice.assert_not_called()
    def test_stale_prerequisite_blocks_assemble(self):
        from unittest.mock import patch
        from test_manifest import example
        from types import SimpleNamespace
        m,l,c,r=example()
        for p in ['source/manifest.json','layers/layers.json','source/coverage.json','source/circuit-review.json']:
            (self.run/p).parent.mkdir(parents=True,exist_ok=True);(self.run/p).write_text('{}')
        (self.run/'state.json').write_text('{"stages":{}}')
        with patch.object(cli,'_load',return_value=(m,l,c,r)),patch.object(cli,'_gate'),patch.object(cli,'recover_run',return_value='voice'):
            with self.assertRaises(ValueError): cli.run_stage('assemble',self.run,SimpleNamespace(runtime='missing'))
    def test_batch_review_approval_is_current_and_paid_zero_until_approved(self):
        from unittest.mock import patch
        from test_manifest import example
        from types import SimpleNamespace
        from solution_video.util import write
        from solution_video.review_adapter import default_config
        batch=self.run/'batch';run=batch/'videos/one';run.mkdir(parents=True)
        m,l,c,r=example()
        for name,data in [('source/manifest.json',m),('layers/layers.json',l),('source/coverage.json',c),('source/circuit-review.json',r),('source/config.json',default_config()),('run.json',{'batch':str(batch),'review':True})]:write(run/name,data)
        write(batch/'videos/failed/source/prepare-error.json',{'reason':'unsupported'})
        write(batch/'batch.json',{'items':[{'id':m['problem_id'],'run':'videos/one'},{'id':'bad','run':'videos/failed','status':'failed'}]})
        args=SimpleNamespace(config=None,env_file=None,approve_review=False)
        with patch.object(cli,'_gate'),patch.object(cli,'generate_voice') as voice:
            result=cli.run_stage('tts',run,args);self.assertEqual(result['status'],'awaiting-review');voice.assert_not_called();self.assertEqual(result['paid_requests'],0)
        args.approve_review=True
        audio=[make_audio(s['id'],24000,run) for s in m['segments']];write(run/'source/audio.json',{'voices':audio})
        with patch.object(cli,'_gate'),patch.object(cli,'generate_voice',return_value=audio):
            result=cli.run_stage('tts',run,args,transport=lambda p:{});self.assertEqual(result['status'],'passed')
        args.approve_review=False;m['segments'][0]['text']='새로운 문제 설명';h=cli.content_fingerprint(m,l,c);c['input_hash']=r['input_hash']=h
        for name,data in [('manifest',m),('coverage',c),('circuit-review',r)]:write(run/'source'/(name+'.json'),data)
        # This test isolates review hash; stage invalidation is tested separately.
        with patch.object(cli,'_gate'),patch.object(cli,'recover_run',return_value='voice'),patch.object(cli,'generate_voice') as voice:
            result=cli.run_stage('tts',run,args);self.assertEqual(result['status'],'awaiting-review');voice.assert_not_called()
    def retime_fixture(self):
        from test_manifest import example
        from solution_video.util import write
        from solution_video.state import finish_stage,STAGES
        from solution_video.review_adapter import default_config
        m,l,c,r=example()
        for name,data in [('source/manifest.json',m),('layers/layers.json',l),('source/coverage.json',c),('source/circuit-review.json',r),('source/config.json',default_config())]:write(self.run/name,data)
        audio=[make_audio(s['id'],2400,self.run) for s in m['segments']];write(self.run/'source/audio.json',{'voices':audio})
        for stage in STAGES[:4]:
            p=self.run/(stage+'.txt');p.write_text(stage);finish_stage(self.run,stage,[p])
        return audio
    def test_retime_uses_current_verified_pcm_without_paid_calls(self):
        from unittest.mock import patch
        from types import SimpleNamespace
        from solution_video.util import write,file_hash,read
        from solution_video.writing import default_writing
        audio=self.retime_fixture()
        from test_writing_units import unit
        l=read(self.run/'layers/layers.json');m=read(self.run/'source/manifest.json');c=read(self.run/'source/coverage.json');r=read(self.run/'source/circuit-review.json')
        for i,step in enumerate(l['map']['steps']):
            ids=step['glyph_ids'];boxes=[next(g['bbox'] for g in l['glyphs'] if g['id']==gid) for gid in ids]+[s['bbox'] for s in l['shapes'] if s['id'] in step['shape_ids']]
            step['writing_units']=[unit('u'+str(i),[min(b[0] for b in boxes),max(b[2] for b in boxes)],ids,step['shape_ids'],line='line'+str(i))]
        c['input_hash']=r['input_hash']=cli.content_fingerprint(m,l,c)
        for name,data in [('layers/layers.json',l),('source/coverage.json',c),('source/circuit-review.json',r)]:write(self.run/name,data)
        from solution_video.state import finish_stage,STAGES
        for stage in STAGES[:4]:finish_stage(self.run,stage,[self.run/(stage+'.txt')])
        cfg=default_writing();cfg['chars_per_second']=4;write(self.run/'custom.json',cfg)
        before=[file_hash(self.run/a['path']) for a in audio]
        with patch.object(cli,'_gate'),patch.object(cli,'generate_voice',side_effect=AssertionError('paid call')) as voice:
            result=cli.run_stage('retime',self.run,SimpleNamespace(writing_config=self.run/'custom.json'))
        self.assertEqual(result['paid_requests'],0);self.assertEqual(result['status'],'passed');voice.assert_not_called()
        self.assertEqual([file_hash(self.run/a['path']) for a in audio],before);self.assertEqual(read(self.run/'source/timeline.json')['writing']['chars_per_second'],4)
    def test_retime_rejects_tampered_or_stale_voice(self):
        from unittest.mock import patch
        from types import SimpleNamespace
        from solution_video.util import write
        audio=self.retime_fixture()
        with patch.object(cli,'_gate'):
            (self.run/audio[0]['path']).write_bytes(b'tampered')
            with self.assertRaises(ValueError):cli.run_stage('retime',self.run,SimpleNamespace(writing_config=None))
            write(self.run/'source/config.json',{'voice':'changed'})
            with self.assertRaisesRegex(ValueError,'prerequisite'):cli.run_stage('retime',self.run,SimpleNamespace(writing_config=None))
    def test_invalid_writing_blocks_voice_before_paid_call(self):
        from unittest.mock import patch
        from types import SimpleNamespace
        from solution_video.util import write
        self.retime_fixture();write(self.run/'source/writing.json',{'mode':'broken'})
        with patch.object(cli,'_gate'),patch.object(cli,'generate_voice',side_effect=AssertionError('paid call')) as voice:
            with self.assertRaisesRegex(ValueError,'writing'):cli.run_stage('tts',self.run,SimpleNamespace(config=None,approve_review=False,env_file=None))
            voice.assert_not_called()
    def test_teaching_retime_preserves_pcm_and_captions(self):
        from unittest.mock import patch
        from types import SimpleNamespace
        from solution_video.util import write,read,file_hash
        from solution_video.manifest import content_fingerprint
        from test_annotations import teaching_fixture
        from solution_video.subtitles import write_srt
        self.retime_fixture();m=read(self.run/'source/manifest.json');l=read(self.run/'layers/layers.json');c=read(self.run/'source/coverage.json');r=read(self.run/'source/circuit-review.json')
        l['metadata']=dict(width_pt=400,height_pt=300,source_sha256='a'*64);l['map']['work_bbox']=[100,100,300,240]
        m['segments'].insert(1,dict(id='r',kind='reason',step_id=l['map']['steps'][0]['id'],text='회로를 확인합니다.',source_refs=['answer:1']))
        c['input_hash']=r['input_hash']=content_fingerprint(m,l,c)
        f,a,_,_=teaching_fixture()
        for name,data in [('source/manifest.json',m),('layers/layers.json',l),('source/coverage.json',c),('source/circuit-review.json',r),('source/focus.json',f),('source/annotations.json',a)]:write(self.run/name,data)
        audio=[make_audio(s['id'],2400,self.run) for s in m['segments']];write(self.run/'source/audio.json',{'voices':audio});before=[file_hash(self.run/a['path']) for a in audio]
        from solution_video.state import finish_stage,STAGES
        for stage in STAGES[:4]:finish_stage(self.run,stage,[self.run/(stage+'.txt')])
        with patch.object(cli,'_gate'),patch.object(cli,'generate_voice',side_effect=AssertionError('paid call')) as voice:
            result=cli.run_stage('retime',self.run,SimpleNamespace(writing_config=None))
        self.assertEqual(result['paid_requests'],0);voice.assert_not_called();self.assertEqual(before,[file_hash(self.run/a['path']) for a in audio])
        t=read(self.run/'source/timeline.json');self.assertIn('teaching',t);write_srt(t,self.run/'captions.srt');self.assertIn('00:00:02,767', (self.run/'captions.srt').read_text())
    def test_pencil_missing_units_blocks_check_before_paid_calls(self):
        from unittest.mock import patch
        from types import SimpleNamespace
        from solution_video.util import write
        from solution_video.writing import default_writing
        self.retime_fixture();write(self.run/'source/writing.json',default_writing())
        with patch.object(cli,'_gate'),patch.object(cli,'recover_run',return_value='script'):
            with self.assertRaisesRegex(ValueError,'writing_units'):cli.run_stage('check',self.run,SimpleNamespace())

class LabPrepareTests(Sandbox):
    def sandbox_repo(self):
        repo=self.run/'repo'; (repo/'복습노트').mkdir(parents=True)
        (repo/'복습노트/실험04').symlink_to(REPO/'복습노트/실험04')
        defective_pack(repo,'실험02','all'); defective_pack(repo,'실험05',[10])  # 출처 미확인11 q-demux-from-dec
        return repo
    def test_prepare_labels_and_paths(self):
        import io,contextlib
        repo=self.sandbox_repo()
        with contextlib.redirect_stdout(io.StringIO()): code=cli.main(['prepare','실험05','--repo',str(repo),'--problems','기출4,q-demux-from-dec'])
        self.assertEqual(code,0)
        batch=next((repo/'문제풀이영상/실험05/실험05_제작자료/실행').iterdir())
        items={i['id']:i for i in read(batch/'batch.json')['items']}
        self.assertEqual(items['q-dec2x4-design']['label'],'기출4'); self.assertEqual(items['q-dec2x4-design']['status'],'author-required')
        self.assertEqual(items['q-dec2x4-design']['filename'],'기출4 — 풀이.mp4')
        self.assertEqual(items['q-demux-from-dec']['status'],'failed'); self.assertIn('raw_latex p.11',items['q-demux-from-dec']['reason'])
        # A dropped problem keeps the same display label the passing ones get; its file name no longer falls back to the ID.
        self.assertEqual(items['q-demux-from-dec']['label'],'출처 미확인11')
        self.assertEqual(items['q-demux-from-dec']['filename'],'출처 미확인11 — 풀이.mp4')
        run=batch/items['q-dec2x4-design']['run']; pair=read(run/'source/pair.json')
        self.assertTrue(all((run/f).is_file() for f in pair['figure_refs']))
        self.assertEqual([s['figure_source'] for s in read(run/'layers/candidates.json')['shapes'] if s['kind']=='figure'],['q-dec2x4-design-solution-01.png'])
    def test_prepare_copies_svg_into_run(self):
        repo=self.sandbox_repo(); batch=cli.prepare_batch(repo,'실험05',['기출4'])
        item=read(batch/'batch.json')['items'][0]; run=batch/item['run']; pair=read(run/'source/pair.json')
        self.assertEqual([Path(f).name for f in pair['figure_svg_refs']],['q-dec2x4-design-solution-01.svg'])
        self.assertTrue(pair['figure_svg_refs'] and all((run/f).is_file() for f in pair['figure_svg_refs']))
        self.assertTrue(set(pair['figure_svg_refs'])<=set(read(run/'source/inputs.json')['files']))
        # export_page 는 PNG 만 받는다: SVG 는 도형 후보(figure_source)가 되지 않는다.
        self.assertEqual([s['figure_source'] for s in read(run/'layers/candidates.json')['shapes'] if s['kind']=='figure'],['q-dec2x4-design-solution-01.png'])
    def test_prepare_reports_missing_pair_svg_as_warning(self):
        import io,contextlib,json
        repo=self.sandbox_repo(); (repo/'복습노트/실험05/자료/figures/solutions/q-dec2x4-design-solution-01.svg').unlink()  # 팩 사본이라 원본은 그대로다
        out=io.StringIO()
        with contextlib.redirect_stdout(out): code=cli.main(['prepare','실험05','--repo',str(repo),'--problems','기출4,q-demux-from-dec'])
        result=json.loads(out.getvalue()); self.assertEqual(code,0)
        want=['figure SVG missing: q-dec2x4-design-solution-01.png']
        self.assertEqual(result['warnings'],want)
        self.assertEqual((result['prepared'],result['failed'],result['status']),(1,1,'author-required'))  # 기존 키·상태는 그대로
        items={i['id']:i for i in read(Path(result['batch'])/'batch.json')['items']}
        self.assertEqual(items['q-dec2x4-design']['warnings'],want); self.assertEqual(items['q-dec2x4-design']['status'],'author-required')
        self.assertNotIn('warnings',items['q-demux-from-dec'])  # 입력 게이트에서 탈락한 항목 형식은 그대로
    def test_prepare_without_missing_svg_has_no_warnings_key(self):
        import io,contextlib,json
        repo=self.sandbox_repo(); out=io.StringIO()
        with contextlib.redirect_stdout(out): code=cli.main(['prepare','실험05','--repo',str(repo),'--problems','기출4,q-demux-from-dec'])
        result=json.loads(out.getvalue()); self.assertEqual(code,0); self.assertNotIn('warnings',result)
        self.assertTrue(all('warnings' not in i for i in read(Path(result['batch'])/'batch.json')['items']))
    def test_prepare_all_failed_experiment(self):
        import io,contextlib,json
        repo=self.sandbox_repo(); out=io.StringIO()
        with contextlib.redirect_stdout(out): code=cli.main(['prepare','실험02','--repo',str(repo)])
        result=json.loads(out.getvalue()); self.assertEqual(result['paid_requests'],0)
        # Nothing passed the input gate: the stage must not claim 'author-required' (there is nothing to author).
        self.assertEqual(code,1); self.assertEqual(result['status'],'failed')
        self.assertEqual(result['prepared'],0); self.assertGreater(result['failed'],0)
        self.assertEqual(result['reason'],'all problems failed the input gate; see batch.json')
        batch=Path(result['batch']); items=read(batch/'batch.json')['items']
        self.assertTrue(items and all(i['status']=='failed' for i in items))
        self.assertEqual(result['failed'],len(items))
        # Every dropped problem still says which one it is.
        self.assertTrue(all(i['label'] and i['filename']==i['label']+' — 풀이.mp4' for i in items),items)
        self.assertEqual(batch.parents[2],repo.resolve()/'문제풀이영상/실험02')
    def test_prepare_partial_failure_exits_zero(self):
        import io,contextlib,json
        repo=self.sandbox_repo(); out=io.StringIO()
        with contextlib.redirect_stdout(out): code=cli.main(['prepare','실험05','--repo',str(repo),'--problems','기출4,q-demux-from-dec'])
        result=json.loads(out.getvalue())
        self.assertEqual(code,0); self.assertEqual(result['status'],'author-required')
        self.assertEqual((result['prepared'],result['failed']),(1,1)); self.assertNotIn('reason',result)
        self.assertEqual(result['paid_requests'],0)
    def test_range_prefix_on_failed_label(self):
        repo=self.sandbox_repo()
        batch=cli.prepare_batch(repo,'실험04-05',['실험05:기출4','실험05:q-demux-from-dec'])
        items={i['id']:i for i in read(batch/'batch.json')['items']}
        # Same rule for both: a range prefixes the experiment, a single experiment does not.
        self.assertEqual(items['q-dec2x4-design']['label'],'실험05 기출4')
        self.assertEqual(items['q-demux-from-dec']['status'],'failed')
        self.assertEqual(items['q-demux-from-dec']['label'],'실험05 출처 미확인11')
        self.assertEqual(items['q-demux-from-dec']['filename'],'실험05 출처 미확인11 — 풀이.mp4')
        self.assertEqual(cli.summarize_batch(batch),{'prepared':1,'failed':1})
    def test_range_prefix_follows_each_items_own_experiment(self):
        # 마지막 실험(실험05)만 보면 접두를 experiments[-1] 로 고정한 구현도 통과한다: 실험04 쪽 탈락·성공 항목도 본다.
        repo=self.run/'repo'; (repo/'복습노트').mkdir(parents=True)
        defective_pack(repo,'실험04',[0]); defective_pack(repo,'실험05',[10])  # 기출1 q-mux2 / 출처 미확인11 q-demux-from-dec
        batch=cli.prepare_batch(repo,'실험04-05',['실험04:q-mux2','실험04:q-mux4','실험05:기출4','실험05:q-demux-from-dec'])
        items={i['id']:i for i in read(batch/'batch.json')['items']}
        self.assertEqual({k:(v['status'],v['label']) for k,v in items.items()},{
            'q-mux2':('failed','실험04 기출1'),'q-mux4':('author-required','실험04 기출2'),
            'q-dec2x4-design':('author-required','실험05 기출4'),'q-demux-from-dec':('failed','실험05 출처 미확인11')})
        self.assertEqual(items['q-mux2']['filename'],'실험04 기출1 — 풀이.mp4')
        self.assertEqual(items['q-mux4']['filename'],'실험04 기출2 — 풀이.mp4')
        self.assertEqual(cli.summarize_batch(batch),{'prepared':2,'failed':2})
    def test_experiment_level_failure_has_no_label(self):
        repo=self.run/'repo'; (repo/'복습노트').mkdir(parents=True)  # 실험03 pack folder absent
        batch=cli.prepare_batch(repo,'실험03')
        items=read(batch/'batch.json')['items']
        self.assertEqual([(i['id'],i['label'],i['filename'],i['status']) for i in items],
            [('experiment-실험03',None,'experiment-실험03 — 풀이.mp4','failed')])
        self.assertEqual(cli.summarize_batch(batch),{'prepared':0,'failed':1})
    def test_prepare_range_folder_name_and_writing_mode(self):
        repo=self.sandbox_repo()
        for mode in ['pencil','typing']:
            batch=cli.prepare_batch(repo,'실험05',['기출3'],False,mode)
            self.assertEqual(batch.parents[2],repo.resolve()/'문제풀이영상/실험05')
            self.assertEqual(read(batch/read(batch/'batch.json')['items'][0]['run']/'source/writing.json')['mode'],mode)
        batch=cli.prepare_batch(repo,'실험04-05',['실험05:기출3'])
        self.assertEqual(batch.parents[2],repo.resolve()/'문제풀이영상/실험04-05')
        item=read(batch/'batch.json')['items'][0]
        self.assertEqual((item['label'],item['filename']),('실험05 기출3','실험05 기출3 — 풀이.mp4'))
