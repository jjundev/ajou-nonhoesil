from fixtures import *
from solution_video.contracts import InputError,ReviewError
from solution_video.speech_chunks import validate_speech_chunks,speech_items,MODE

def chunked():
    """논회실 예: 음성은 읽는 소리, 자막은 원문 기호. 청크 하나 = 자막 cue 하나."""
    return [dict(id='intro',kind='problem',text='첫 문단이에요.',source_refs=['problem:1']),
            dict(id='w',kind='write',step_id='s',source_refs=['answer:1'],
                 text='출력은 에스원 바 에스제로 바 디예요. 그래서 와이영이 켜져요.',
                 caption_text='출력은 S1′S0′D예요. 그래서 Y0이 켜져요.',
                 chunks=[dict(id='c1',text='출력은 에스원 바 에스제로 바 디예요.',caption_text='출력은 S1′S0′D예요.'),
                         dict(id='c2',text='그래서 와이영이 켜져요.',caption_text='그래서 Y0이 켜져요.')])]

class ChunkContractTests(Sandbox):
    def test_requires_every_segment_in_chunk_mode(self):
        segs=chunked()
        with self.assertRaisesRegex(InputError,'segment intro: speech chunks required'):validate_speech_chunks(segs,required=True)
        segs[0].update(caption_text='첫 문단이에요.',chunks=[dict(id='a',text='첫 문단이에요.',caption_text='첫 문단이에요.')])
        validate_speech_chunks(segs,required=True)
    def test_legacy_unchanged(self):
        segs=[dict(id='one',text='첫 문단'),dict(id='two',text='두 번째',caption_text='두 번째.')]
        validate_speech_chunks(segs,required=False)
        self.assertEqual(speech_items(segs),[dict(id='one',text='첫 문단'),dict(id='two',text='두 번째')])
    def test_chunk_items(self):
        self.assertEqual([i['id'] for i in speech_items(chunked())],['intro','w__c1','w__c2'])
        self.assertEqual(speech_items(chunked())[1],dict(id='w__c1',segment_id='w',chunk_id='c1',text='출력은 에스원 바 에스제로 바 디예요.'))
    def test_parent_reconstruction_and_atomic_caption(self):
        def bad(mutate,pattern):
            segs=chunked();mutate(segs[1])
            with self.subTest(pattern=pattern),self.assertRaisesRegex(InputError,pattern):validate_speech_chunks(segs,required=False)
        bad(lambda s:s.update(text='출력은 에스원 바 디예요. 그래서 와이영이 켜져요.'),'text differs')
        bad(lambda s:s.update(caption_text='출력은 S1′D예요. 그래서 Y0이 켜져요.'),'caption_text differs')
        bad(lambda s:s['chunks'][1].update(id='c1'),'duplicate speech identity w__c1')
        bad(lambda s:s['chunks'][1].update(id='1bad'),'invalid chunk ID')
        bad(lambda s:s['chunks'][0].update(text='  '),'chunk c1')
        bad(lambda s:s['chunks'][0].pop('caption_text'),'chunk c1 caption_text required')
        bad(lambda s:s.update(chunks=[]),'nonempty speech chunks')
        bad(lambda s:s.pop('caption_text'),'caption_text required')
        # 두 문장을 한 청크에 넣으면 cue 가 둘이라 거부한다.
        bad(lambda s:s.update(chunks=[dict(id='c1',text=s['text'],caption_text=s['caption_text'])]),'exactly one caption cue')
        # 청크 자막의 말로 쓴 연산은 기존 규칙대로 오류.
        bad(lambda s:(s['chunks'][1].update(caption_text='그래서 A 더하기 B예요.'),s.update(caption_text='출력은 S1′S0′D예요. 그래서 A 더하기 B예요.')),'chunk c2')
    def test_comma_clause_and_formula_chunk(self):
        segs=[dict(id='w',text='에이 오어 비는, 일이에요.',caption_text='A + B는, 1이에요.',
                   chunks=[dict(id='a',text='에이 오어 비는,',caption_text='A + B는,'),dict(id='b',text='일이에요.',caption_text='1이에요.')])]
        validate_speech_chunks(segs,required=True)
    def test_cross_segment_identity_collision(self):
        segs=[dict(id='w__c1',text='가.'),*chunked()[1:]]
        with self.assertRaisesRegex(InputError,'duplicate speech identity'):validate_speech_chunks(segs,required=False)
    def test_caption_warnings_include_chunk_id(self):
        from solution_video.subtitles import caption_notation_warnings
        segs=chunked();segs[1]['chunks'][1]['caption_text']='그래서 S1 바는 0이에요.';segs[1]['caption_text']='출력은 S1′S0′D예요. 그래서 S1 바는 0이에요.'
        w=caption_notation_warnings(segs)
        self.assertEqual([(i['code'],i['segment_id'],i.get('chunk_id')) for i in w],[('logic_bar_word','w','c2')])

class ChunkManifestTests(Sandbox):
    def manifest(self,**over):
        from test_manifest import example
        from solution_video.manifest import content_fingerprint
        m,l,c,r=example();m.update(over.pop('manifest',{}))
        for s in m['segments']:s.update(over.get(s['id'],{}))
        h=content_fingerprint(m,l,c);c['input_hash']=r['input_hash']=h
        return m,l,c,r
    def chunks(self,text):return dict(caption_text=text,chunks=[dict(id='c1',text=text,caption_text=text)])
    def test_chunk_mode_requires_every_segment(self):
        from solution_video.manifest import validate_manifest
        m=self.manifest(manifest=dict(caption_timing=MODE),write=self.chunks('절반 회로를 씁니다.'))
        with self.assertRaisesRegex(InputError,'segment intro: speech chunks required'):validate_manifest(*m)
        m=self.manifest(manifest=dict(caption_timing=MODE),intro=self.chunks('문제를 읽습니다.'),write=self.chunks('절반 회로를 씁니다.'),end=self.chunks('답을 확인합니다.'))
        validate_manifest(*m)
    def test_chunks_need_explicit_mode_and_known_mode(self):
        from solution_video.manifest import validate_manifest
        with self.assertRaisesRegex(ReviewError,'require caption_timing'):validate_manifest(*self.manifest(write=self.chunks('절반 회로를 씁니다.')))
        with self.assertRaisesRegex(ReviewError,'unsupported caption timing'):validate_manifest(*self.manifest(manifest=dict(caption_timing='chars')))
        validate_manifest(*self.manifest())  # legacy manifest stays valid

import base64,struct
from solution_video.util import read,write,file_hash
def pcm(samples,amp=0,seed=0):
    return b''.join(struct.pack('<h',((i*7+seed)%13-6)*amp) for i in range(samples))
class FakeTTS:
    """가짜 transport: 대본별 길이·진폭이 다른 PCM 을 돌려주고 요청을 기록한다(유료 호출 없음)."""
    def __init__(self,lengths,amp=300):self.lengths=lengths;self.amp=amp;self.calls=[];self.fail=set()
    def __call__(self,payload):
        text=payload['contents'][0]['parts'][0]['text'];self.calls.append(text)
        if text in self.fail:raise ValueError('secret-key-should-not-leak')
        n=self.lengths.get(text,2400)
        data=base64.b64encode(pcm(n,self.amp,len(self.calls))).decode()
        return {'candidates':[{'finishReason':'STOP','content':{'parts':[{'inlineData':{'mimeType':'audio/L16;rate=24000','data':data}}]}}]}
def two_chunk_segments():
    return [dict(id='w',kind='write',step_id='s',source_refs=['answer:1'],text='첫 청크예요. 둘째 청크예요.',caption_text='첫 청크예요. 둘째 청크예요.',
                 chunks=[dict(id='a',text='첫 청크예요.',caption_text='첫 청크예요.'),dict(id='b',text='둘째 청크예요.',caption_text='둘째 청크예요.')])]
def wav_bytes(path):
    with wave.open(str(path),'rb') as w:return w.readframes(w.getnframes())

class ChunkAudioTests(Sandbox):
    def config(self):
        from solution_video.review_adapter import default_config
        c=default_config();c.update(max_attempts=1,tts_concurrency=1);return c
    def voice(self,segments,fake,cfg=None):
        from solution_video.review_adapter import generate_voice
        return generate_voice(segments,self.run,cfg or self.config(),self.run/'ledger.json',fake)
    def test_join_measured_pcm(self):
        fake=FakeTTS({'첫 청크예요.':2400,'둘째 청크예요.':7200})
        out=self.voice(two_chunk_segments(),fake)
        self.assertEqual(fake.calls,['첫 청크예요.','둘째 청크예요.'])
        self.assertEqual(len(out),1);seg=out[0]
        self.assertEqual(seg['samples'],9600);self.assertEqual([(c['start_sample'],c['end_sample']) for c in seg['chunks']],[(0,2400),(2400,9600)])
        receipts=read(self.run/'source/chunk-audio.json')
        self.assertEqual(receipts['policy'],'spoken-text-only-v1');self.assertEqual([r['id'] for r in receipts['voices']],['w__a','w__b'])
        raw=b''.join(wav_bytes(self.run/r['path']) for r in receipts['voices'])
        self.assertEqual(wav_bytes(self.run/seg['path']),raw)
        self.assertEqual(read(self.run/'source/audio.json')['voices'],out)
        from solution_video.speech_chunks import validate_chunk_audio
        validate_chunk_audio(two_chunk_segments(),out,self.run,read(self.run/'source/config.json'))
    def test_no_automatic_trim_of_quiet_speech(self):
        fake=FakeTTS({'첫 청크예요.':2400,'둘째 청크예요.':2400},amp=1)
        out=self.voice(two_chunk_segments(),fake)
        receipts=read(self.run/'source/chunk-audio.json')['voices']
        self.assertEqual(out[0]['samples'],4800)
        self.assertEqual(wav_bytes(self.run/out[0]['path']),b''.join(wav_bytes(self.run/r['path']) for r in receipts))
    def test_explicit_trim_preserves_raw_and_reuses_cache(self):
        fake=FakeTTS({'첫 청크예요.':2400,'둘째 청크예요.':7200});self.voice(two_chunk_segments(),fake)
        receipts={r['id']:r for r in read(self.run/'source/chunk-audio.json')['voices']};raw_a=(self.run/receipts['w__a']['path']).read_bytes()
        write(self.run/'source/chunk-trims.json',dict(schema_version=1,rows=[dict(segment_id='w',chunk_id='a',raw_sha256=receipts['w__a']['sha256'],start_sample=100,end_sample=2300,reason='청취: 앞뒤 무음 0.1초씩')]))
        out=self.voice(two_chunk_segments(),fake)
        self.assertEqual(len(fake.calls),2)  # 절단은 유료 재합성이 아니다
        self.assertEqual((self.run/receipts['w__a']['path']).read_bytes(),raw_a)
        c=out[0]['chunks'];self.assertEqual((c[0]['trim_start_sample'],c[0]['trim_end_sample'],c[0]['start_sample'],c[0]['end_sample']),(100,2300,0,2200))
        self.assertEqual((c[1]['start_sample'],c[1]['end_sample']),(2200,9400));self.assertEqual(out[0]['samples'],9400)
        self.assertEqual(wav_bytes(self.run/out[0]['path']),wav_bytes(self.run/receipts['w__a']['path'])[200:4600]+wav_bytes(self.run/receipts['w__b']['path']))
    def test_reject_bad_trim_and_provenance(self):
        from solution_video.speech_chunks import validate_chunk_audio
        fake=FakeTTS({});out=self.voice(two_chunk_segments(),fake)
        receipts={r['id']:r for r in read(self.run/'source/chunk-audio.json')['voices']};sha=receipts['w__a']['sha256']
        row=dict(segment_id='w',chunk_id='a',raw_sha256=sha,start_sample=0,end_sample=10,reason='r')
        for bad,pattern in [([dict(row,start_sample=-1)],'range'),([dict(row,end_sample=2401)],'range'),([dict(row,start_sample=10)],'range'),
                            ([dict(row,start_sample=True)],'range'),([dict(row,end_sample=10.0)],'range'),([row,row],'duplicate'),
                            ([dict(row,raw_sha256='0'*64)],'stale'),([dict(row,chunk_id='zz')],'unknown chunk'),([dict(row,reason=' ')],'reason')]:
            write(self.run/'source/chunk-trims.json',dict(schema_version=1,rows=bad))
            with self.subTest(pattern=pattern),self.assertRaisesRegex(InputError,pattern):self.voice(two_chunk_segments(),fake)
        self.assertEqual(len(fake.calls),2)  # 거부는 유료 요청 전
        (self.run/'source/chunk-trims.json').unlink()
        cfg=read(self.run/'source/config.json')
        # 변조한 원본 청크 WAV·연결본·영수증 누락을 잡는다.
        a=self.run/receipts['w__a']['path'];good=a.read_bytes();a.write_bytes(good[:-2]+b'\1\0')
        with self.assertRaisesRegex(InputError,'w__a'):validate_chunk_audio(two_chunk_segments(),out,self.run,cfg)
        a.write_bytes(good);validate_chunk_audio(two_chunk_segments(),out,self.run,cfg)
        j=self.run/out[0]['path'];jgood=j.read_bytes();j.write_bytes(jgood[:-2]+b'\1\0')
        with self.assertRaises(InputError):validate_chunk_audio(two_chunk_segments(),[dict(out[0],sha256=file_hash(j))],self.run,cfg)
        j.write_bytes(jgood)
        moved=[dict(out[0],chunks=[dict(out[0]['chunks'][0],end_sample=2000),out[0]['chunks'][1]])]
        with self.assertRaisesRegex(InputError,'boundaries changed'):validate_chunk_audio(two_chunk_segments(),moved,self.run,cfg)
        (self.run/'source/chunk-audio.json').unlink()
        with self.assertRaisesRegex(InputError,'chunk audio receipts missing'):validate_chunk_audio(two_chunk_segments(),out,self.run,cfg)
    def test_text_change_marks_receipt_stale_and_trim_must_be_reauthored(self):
        from solution_video.speech_chunks import validate_chunk_audio
        fake=FakeTTS({});out=self.voice(two_chunk_segments(),fake);cfg=read(self.run/'source/config.json')
        segs=two_chunk_segments();segs[0]['chunks'][0]['text']='첫 청크라요.';segs[0]['text']='첫 청크라요. 둘째 청크예요.'
        with self.assertRaisesRegex(InputError,'stale speech chunk receipt: w__a'):validate_chunk_audio(segs,out,self.run,cfg)
        receipts={r['id']:r for r in read(self.run/'source/chunk-audio.json')['voices']}
        write(self.run/'source/chunk-trims.json',dict(schema_version=1,rows=[dict(segment_id='w',chunk_id='a',raw_sha256=receipts['w__a']['sha256'],start_sample=0,end_sample=10,reason='r')]))
        with self.assertRaisesRegex(InputError,'reauthor the trim for w__a'):self.voice(segs,fake)
        self.assertEqual(len(fake.calls),2)
    def test_caption_change_reuses_chunk_voice(self):
        fake=FakeTTS({});a=self.voice(two_chunk_segments(),fake)
        segs=two_chunk_segments();segs[0]['chunks'][1]['caption_text']='둘째예요.';segs[0]['caption_text']='첫 청크예요. 둘째예요.'
        b=self.voice(segs,fake);self.assertEqual(len(fake.calls),2);self.assertEqual(a,b)
    def test_partial_failure_resumes_without_touching_audio_index(self):
        fake=FakeTTS({});fake.fail.add('둘째 청크예요.')
        with self.assertRaises(Exception) as ctx:self.voice(two_chunk_segments(),fake)
        self.assertNotIn('secret-key',str(ctx.exception))
        self.assertFalse((self.run/'source/audio.json').exists());self.assertFalse((self.run/'source/chunk-audio.json').exists())
        self.assertTrue(list((self.run/'assets/voice').glob('w__a-*.wav')))
        fake.fail.clear();out=self.voice(two_chunk_segments(),fake)
        self.assertEqual(fake.calls,['첫 청크예요.','둘째 청크예요.','둘째 청크예요.']);self.assertEqual(len(out),1)
        self.assertTrue((self.run/'ledger.json').exists())
    def test_partial_chunks_are_not_filled_with_legacy(self):
        segs=[dict(id='intro',text='문제예요.'),*two_chunk_segments()];fake=FakeTTS({})
        with self.assertRaisesRegex(InputError,'segment intro: speech chunks required'):self.voice(segs,fake)
        self.assertEqual(fake.calls,[])
    def test_legacy_voice_keeps_old_index(self):
        fake=FakeTTS({});out=self.voice([dict(id='one',text='첫 문단')],fake)
        self.assertEqual(read(self.run/'source/audio.json')['voices'],out);self.assertNotIn('chunks',out[0])
        self.assertFalse((self.run/'source/chunk-audio.json').exists())
        from solution_video.speech_chunks import validate_chunk_audio
        validate_chunk_audio([dict(id='one',text='첫 문단')],out,self.run,{})  # legacy: no-op
        write(self.run/'source/chunk-trims.json',dict(schema_version=1,rows=[]))
        with self.assertRaisesRegex(InputError,'require chunk speech'):self.voice([dict(id='one',text='첫 문단')],fake)
