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
