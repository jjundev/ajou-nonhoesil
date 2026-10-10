"""pcm-chunks-v1 수용: 가짜 transport → 청크 WAV → segment 연결 → timeline 의 절대 cue → SRT (유료 호출 없음)."""
from fixtures import *
from solution_video.contracts import InputError
from solution_video.util import read,write
from solution_video.speech_chunks import MODE
from test_speech_chunks import FakeTTS
from test_manifest import example
import copy,re

def chunked_example():
    m,l,c,r=example();m['caption_timing']=MODE
    one=lambda t:dict(text=t,caption_text=t,chunks=[dict(id='c1',text=t,caption_text=t)])
    m['segments'][0].update(one('문제를 읽어요.'))
    m['segments'][1].update(text='에스원 바 에스제로 바 디를 써요. 와이영이 켜져요.',caption_text='S1′S0′D를 써요. Y0이 켜져요.',
                            chunks=[dict(id='c1',text='에스원 바 에스제로 바 디를 써요.',caption_text='S1′S0′D를 써요.'),
                                    dict(id='c2',text='와이영이 켜져요.',caption_text='Y0이 켜져요.')])
    m['segments'][2].update(one('답을 확인해요.'))
    return m,l,c,r
LENGTHS={'문제를 읽어요.':24000,'에스원 바 에스제로 바 디를 써요.':2400,'와이영이 켜져요.':7200,'답을 확인해요.':4800}
def srt_rows(text):
    def s(h,m,sec,ms):return int(h)*3600+int(m)*60+int(sec)+int(ms)/1000
    return [(s(*a[:4]),s(*a[4:8]),a[8]) for a in re.findall(r'(\d\d):(\d\d):(\d\d),(\d{3}) --> (\d\d):(\d\d):(\d\d),(\d{3})\n(.+?)\n(?:\n|$)',text,re.S)]

class ChunkSyncTests(Sandbox):
    def build(self,m=None,lengths=LENGTHS,cfg=None):
        from solution_video.review_adapter import generate_voice,default_config
        from solution_video.teaching import build_teaching_timeline
        m=m or chunked_example()[0];l=chunked_example()[1];cfg=cfg or dict(default_config(),max_attempts=1,tts_concurrency=1)
        self.fake=getattr(self,'fake',None) or FakeTTS(lengths)
        audio=generate_voice(m['segments'],self.run,cfg,self.run/'ledger.json',self.fake)
        return m,l,audio,build_teaching_timeline(m,l,audio,cfg,None,None)
    def test_srt_uses_pcm_not_character_weights(self):
        from solution_video.subtitles import write_srt
        m,l,audio,t=self.build()
        self.assertEqual(t['caption_timing'],MODE)
        w=next(s for s in t['segments'] if s['id']=='write');self.assertEqual(w['start_sample'],24000)
        cues=[c for c in t['caption_cues'] if c['segment_id']=='write']
        self.assertEqual([(c['start_sample'],c['end_sample']) for c in cues],[(24000,26400),(26400,33600)])
        rows=srt_rows(write_srt(t,self.run/'a.srt').read_text(encoding='utf-8'))
        self.assertEqual([r[2] for r in rows],['문제를 읽어요.','S1′S0′D를 써요.','Y0이 켜져요.','답을 확인해요.'])
        self.assertEqual(rows[1][:2],(1.0,1.1));self.assertEqual(rows[2][:2],(1.1,1.4))
        # 같은 음성에서 자막만 줄여도 시간은 그대로이고 재합성하지 않는다.
        m2=copy.deepcopy(m);m2['segments'][1]['chunks'][0]['caption_text']='S1′S0′D.';m2['segments'][1]['caption_text']='S1′S0′D. Y0이 켜져요.'
        _,_,_,t2=self.build(m2)
        self.assertEqual(len(self.fake.calls),4)
        self.assertEqual([(c['start_sample'],c['end_sample']) for c in t2['caption_cues']],[(c['start_sample'],c['end_sample']) for c in t['caption_cues']])
    def test_hold_and_frame_padding_have_no_caption(self):
        m,l,audio,t=self.build()
        for seg in t['segments']:
            last=[c for c in t['caption_cues'] if c['segment_id']==seg['id']][-1]
            self.assertEqual(last['end_sample'],seg['start_sample']+seg['voice_samples'])
            self.assertLess(last['end_sample'],seg['end_sample']+1)
            self.assertEqual(seg['start_sample']%800,0)  # 다음 segment 는 프레임 경계에서 시작
        end=next(s for s in t['segments'] if s['id']=='end');w=next(s for s in t['segments'] if s['id']=='write')
        self.assertGreater(end['start_sample'],w['start_sample']+w['voice_samples'])  # write hold 구간은 자막 없음
        self.assertEqual(next(c for c in t['caption_cues'] if c['segment_id']=='end')['start_sample'],end['start_sample'])
    def test_missing_or_reordered_chunk_boundaries_fail(self):
        from solution_video.reveal import build_timeline
        from solution_video.subtitles import write_srt
        from solution_video.review_adapter import default_config
        m,l,audio,t=self.build()
        bad=copy.deepcopy(audio);next(a for a in bad if a['id']=='write').pop('chunks')
        with self.assertRaisesRegex(InputError,'boundaries missing'):build_timeline(m,l,bad,default_config())
        bad=copy.deepcopy(audio);w=next(a for a in bad if a['id']=='write');w['chunks']=w['chunks'][::-1]
        with self.assertRaisesRegex(InputError,'boundaries missing/mismatched'):build_timeline(m,l,bad,default_config())
        bad=copy.deepcopy(audio);w=next(a for a in bad if a['id']=='write');w['chunks'][1]['end_sample']-=800
        with self.assertRaisesRegex(InputError,'coverage mismatch'):build_timeline(m,l,bad,default_config())
        for mutate in [lambda c:c.pop(),lambda c:c.insert(0,c.pop()),lambda c:c[1].update(start_sample=c[1]['start_sample']+1)]:
            tt=copy.deepcopy(t);mutate(tt['caption_cues'])
            with self.assertRaises(InputError):write_srt(tt,self.run/'bad.srt')
        legacy=copy.deepcopy(m);legacy.pop('caption_timing')
        with self.assertRaisesRegex(InputError,'speech chunks|caption'):build_timeline(dict(legacy,caption_timing='chars'),l,audio,default_config())
    def test_legacy_srt_unchanged(self):
        from solution_video.reveal import build_timeline
        from solution_video.subtitles import write_srt
        from solution_video.review_adapter import default_config
        m,l,_,_=example();audio=[make_audio(s['id'],24000,self.run) for s in m['segments']]
        t=build_timeline(m,l,audio,default_config())
        self.assertNotIn('caption_timing',t);self.assertNotIn('caption_cues',t)
        rows=srt_rows(write_srt(t,self.run/'legacy.srt').read_text(encoding='utf-8'))
        self.assertEqual(len(rows),3);self.assertEqual(rows[0][:2],(0.0,1.0))
    def test_cli_tts_and_retime_validate_chunk_audio(self):
        from unittest.mock import patch
        from types import SimpleNamespace
        import importlib.util
        from solution_video.state import finish_stage,STAGES
        from solution_video.review_adapter import default_config
        spec=importlib.util.spec_from_file_location('solution_cli_chunks',S/'scripts/video.py');cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)
        m,l,c,r=chunked_example();h=cli.content_fingerprint(m,l,c);c['input_hash']=r['input_hash']=h
        for name,data in [('source/manifest.json',m),('layers/layers.json',l),('source/coverage.json',c),('source/circuit-review.json',r),('source/config.json',dict(default_config(),max_attempts=1,tts_concurrency=1))]:write(self.run/name,data)
        write(self.run/'run.json',dict(batch=str(self.run/'batch'),review=False));write(self.run/'batch/batch.json',dict(items=[]))
        for stage in STAGES[:3]:
            out=self.run/(stage+'.txt');out.write_text(stage);finish_stage(self.run,stage,[out])
        fake=FakeTTS(LENGTHS)
        with patch.object(cli,'_gate'):
            result=cli.run_stage('tts',self.run,SimpleNamespace(config=None,env_file=None,approve_review=False),transport=fake)
            self.assertEqual((result['status'],result['paid_requests'],len(fake.calls)),('passed',0,4))
            state=read(self.run/'state.json');self.assertIn('source/chunk-audio.json',state['stages']['voice']['outputs'])
            self.assertEqual(len(read(self.run/'source/timeline.json')['caption_cues']),4)
            result=cli.run_stage('retime',self.run,SimpleNamespace(writing_config=None));self.assertEqual(result['status'],'passed')
            raw=self.run/read(self.run/'source/chunk-audio.json')['voices'][1]['path'];raw.write_bytes(raw.read_bytes()[:-2]+b'\1\0')
            with self.assertRaisesRegex(InputError,'provenance mismatch: write__c1'):cli.run_stage('retime',self.run,SimpleNamespace(writing_config=None))

class ChunkGateTests(Sandbox):
    def make_run(self):
        from solution_video.subtitles import write_srt
        b=ChunkSyncTests('test_legacy_srt_unchanged');b.run=self.run
        m,l,audio,t=b.build()
        write(self.run/'source/manifest.json',m);write(self.run/'layers/layers.json',l);write(self.run/'source/timeline.json',t)
        write_srt(t,self.run/'renders/captions.srt');return m,t
    def review(self,m,**over):
        rows=[dict(segment_id=s['id'],chunk_id=c['id'],transcript_match=True,no_instruction_speech=True,natural_join=True,sync_passed=True,notes='대본대로, 지침 발화 없음')
              for s in m['segments'] for c in s['chunks']]
        return dict(dict(status='passed',mode='live-listened',notes='전체 청취',chunk_checks=rows),**over)
    def test_structural_sync_passes_and_tampering_fails(self):
        from solution_video.speech_chunks import verify_chunk_sync
        m,t=self.make_run();r=verify_chunk_sync(self.run)
        self.assertEqual(r['status'],'passed',r['issues']);self.assertEqual(r['live_listening'],'not-evidence')
        self.assertTrue((self.run/'verification/chunk-sync.json').is_file());self.assertIn('source/chunk-audio.json',r['evidence_hashes'])
        srt=self.run/'renders/captions.srt';good=srt.read_text(encoding='utf-8')
        srt.write_text(good.replace('00:00:01,100','00:00:01,200',1),encoding='utf-8')
        self.assertEqual(verify_chunk_sync(self.run)['status'],'unverified');srt.write_text(good,encoding='utf-8')
        tt=copy.deepcopy(t);tt['caption_cues'][1]['end_sample']+=800;tt['caption_cues'][2]['start_sample']+=800;write(self.run/'source/timeline.json',tt)
        self.assertEqual(verify_chunk_sync(self.run)['status'],'unverified');write(self.run/'source/timeline.json',t)
        raw=self.run/read(self.run/'source/chunk-audio.json')['voices'][2]['path'];rgood=raw.read_bytes();raw.write_bytes(rgood[:-2]+b'\1\0')
        r=verify_chunk_sync(self.run);self.assertEqual(r['status'],'unverified');self.assertTrue(r['issues'])
        raw.write_bytes(rgood);self.assertEqual(verify_chunk_sync(self.run)['status'],'passed')
    def test_no_listening_or_incomplete_chunk_review_blocks(self):
        from solution_video.speech_chunks import chunk_review_passed
        m,_=self.make_run();self.assertTrue(chunk_review_passed(self.review(m),m))
        rows=self.review(m)['chunk_checks']
        for bad in [self.review(m,mode='not-listened'),self.review(m,chunk_checks=rows[:-1]),self.review(m,chunk_checks=rows+rows[-1:]),
                    self.review(m,chunk_checks=rows[::-1]),self.review(m,chunk_checks=None)]+[
                    self.review(m,chunk_checks=[dict(rows[0],**{k:v}),*rows[1:]]) for k in ['transcript_match','no_instruction_speech','natural_join','sync_passed'] for v in [False,'true',None]]+[
                    self.review(m,chunk_checks=[dict(rows[0],notes=' '),*rows[1:]])]:
            with self.subTest(bad=str(bad)[:80]):self.assertFalse(chunk_review_passed(bad,m))
        legacy=example()[0];self.assertTrue(chunk_review_passed({'mode':'live-listened'},legacy))
    def test_verify_run_gates_chunk_mode_and_synthetic_pcm_is_not_live_audio(self):
        from solution_video.verify import verify_run,verification_fingerprint
        from solution_video.publication import report_current
        m,_=self.make_run()
        report=verify_run(self.run,self.run/'missing-hyperframes')
        self.assertEqual(report['checks']['chunk_sync']['status'],'passed')  # 합성 PCM 구조는 맞아도
        self.assertEqual(report['live_audio'],'unverified');self.assertFalse(report['complete'])  # 청취 없이는 승인 없음
        h=verification_fingerprint(self.run);ev={'renders/captions.srt':cli_hash(self.run/'renders/captions.srt')}
        write(self.run/'verification/audio-review.json',dict(self.review(m,chunk_checks=self.review(m)['chunk_checks'][:-1]),input_hash=h,evidence=ev))
        self.assertEqual(verify_run(self.run,self.run/'x')['checks']['audio_meaning']['status'],'unverified')
        write(self.run/'verification/audio-review.json',dict(self.review(m),input_hash=h,evidence=ev))
        report=verify_run(self.run,self.run/'x');self.assertEqual(report['checks']['audio_meaning']['status'],'passed');self.assertEqual(report['live_audio'],'verified')
        # 게시 판정은 청크 모드에서 chunk_sync 를 요구한다.
        write(self.run/'verification/visual-review.json',{'status':'passed'})
        reviews={p:cli_hash(self.run/p) for p in ['verification/audio-review.json','verification/visual-review.json']}
        base={k:{'status':'passed'} for k in ['content','original_svg','hyperframes','final_media','captions','audio_meaning','visual_meaning']}
        fake=dict(input_hash=verification_fingerprint(self.run),live_audio='verified',review_hashes=reviews,checks=base)
        self.assertFalse(report_current(self.run,fake))
        self.assertFalse(report_current(self.run,dict(fake,checks=dict(base,chunk_sync={'status':'unverified'}))))
        self.assertTrue(report_current(self.run,dict(fake,checks=dict(base,chunk_sync={'status':'passed'}))))
def cli_hash(p):
    from solution_video.util import file_hash
    return file_hash(p)
