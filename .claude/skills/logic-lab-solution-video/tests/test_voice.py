from fixtures import *
from solution_video.review_adapter import generate_voice,default_config
import base64,wave
def _ok(payload,samples=2400):
    return {'candidates':[{'finishReason':'STOP','content':{'parts':[{'inlineData':{'mimeType':'audio/L16;rate=24000','data':base64.b64encode(b'\0\0'*samples).decode()}}]}}]}
class SpokenTextOnlyTests(Sandbox):
    def test_payload_contains_only_spoken_text(self):
        cfg=default_config();cfg.update(max_attempts=1,tts_concurrency=1);calls=[]
        def transport(payload):calls.append(payload);return _ok(payload)
        out=generate_voice([dict(id='one',text='출력은 S1′S0′D 예요.',caption_text='출력은 S1′S0′D예요.')],self.run,cfg,self.run/'ledger.json',transport)
        self.assertEqual(len(calls),1);payload=calls[0]
        parts=payload['contents'][0]['parts'];self.assertEqual(len(parts),1)
        expected='출력은 S1′S0′D 예요.'
        for a,b in cfg['pronunciation'].items():expected=expected.replace(a,b)
        self.assertEqual(parts[0]['text'],expected)
        for bad in ['원고','읽으세요','caption','S1′S0′D예요']:self.assertNotIn(bad,json.dumps(payload,ensure_ascii=False))
        g=payload['generationConfig'];self.assertEqual(g['responseModalities'],['AUDIO'])
        self.assertEqual(g['speechConfig']['languageCode'],'ko-KR');self.assertEqual(g['speechConfig']['voiceConfig']['prebuiltVoiceConfig']['voiceName'],'Aoede')
        self.assertEqual(out[0]['policy'],'spoken-text-only-v1')
    def test_old_config_direction_is_not_sent_or_frozen(self):
        cfg=default_config();cfg.update(max_attempts=1,tts_concurrency=1,direction='차분하게 읽으세요. 과장하지 않습니다.');calls=[]
        def transport(payload):calls.append(payload);return _ok(payload)
        generate_voice([dict(id='one',text='첫 문단')],self.run,cfg,self.run/'ledger.json',transport)
        self.assertEqual(calls[0]['contents'][0]['parts'][0]['text'],'첫 문단')
        self.assertNotIn('direction',json.loads((self.run/'source/config.json').read_text(encoding='utf-8')))
    def test_policy_invalidates_old_direction_cache(self):
        from solution_video.review_adapter import _modules
        tts,_=_modules();cfg=default_config();cfg.update(max_attempts=1,tts_concurrency=1);calls=[]
        def transport(payload):calls.append(payload);return _ok(payload)
        # 옛 방식(지침 포함, 정책 없음) 키로 저장된 캐시를 흉내 낸다.
        old_payload=tts.make_payload('옛 지침\n\n원고:\n첫 문단',cfg)
        old_key=tts.digest({'text':'첫 문단','pronunciation':cfg.get('pronunciation',{}),'model':cfg['model'],'payload':old_payload})
        self.assertNotEqual(old_key,tts.speech_key('첫 문단',cfg))
        wav=self.run/'assets/voice'/('one-'+old_key[:16]+'.wav');wav.parent.mkdir(parents=True)
        with wave.open(str(wav),'wb') as w:w.setparams((1,2,24000,0,'NONE',''));w.writeframes(b'\0\0'*2400)
        (wav.with_suffix('.json')).write_text(json.dumps(dict(id='one',path=wav.relative_to(self.run).as_posix(),samples=2400,rate=24000,key=old_key,sha256=tts.file_hash(wav),output_sha256=tts.file_hash(wav))),encoding='utf-8')
        out=generate_voice([dict(id='one',text='첫 문단')],self.run,cfg,self.run/'ledger.json',transport)
        self.assertEqual(len(calls),1);self.assertNotEqual(out[0]['key'],old_key)
        # 같은 키의 영수증이라도 정책 표지가 없으면 다시 만든다.
        rec=json.loads(Path(self.run/out[0]['path']).with_suffix('.json').read_text(encoding='utf-8'));rec.pop('policy')
        Path(self.run/out[0]['path']).with_suffix('.json').write_text(json.dumps(rec),encoding='utf-8')
        generate_voice([dict(id='one',text='첫 문단')],self.run,cfg,self.run/'ledger.json',transport)
        self.assertEqual(len(calls),2)
        generate_voice([dict(id='one',text='첫 문단')],self.run,cfg,self.run/'ledger.json',transport)
        self.assertEqual(len(calls),2)
    def test_cache_key_follows_sent_script(self):
        from solution_video.review_adapter import _modules
        tts,_=_modules();cfg=default_config()
        a=tts.speech_key('S1′ 이에요.',cfg);b=tts.speech_key('S1′ 이에요.',dict(cfg,pronunciation=dict(cfg['pronunciation'],**{'′':' 프라임 '})))
        self.assertNotEqual(a,b)
class VoiceTests(Sandbox):
    def test_caption_change_reuses_voice(self):
        cfg=default_config();cfg.update(max_attempts=1,tts_concurrency=1);calls=[]
        def transport(payload):
            calls.append(payload)
            return {'candidates':[{'finishReason':'STOP','content':{'parts':[{'inlineData':{'mimeType':'audio/L16;rate=24000','data':base64.b64encode(b'\0\0'*2400).decode()}}]}}]}
        a=generate_voice([dict(id='one',text='알 오 원',caption_text='r_O1')],self.run,cfg,self.run/'ledger.json',transport)
        b=generate_voice([dict(id='one',text='알 오 원',caption_text='출력 저항 r_O1')],self.run,cfg,self.run/'ledger.json',transport)
        self.assertEqual(len(calls),1);self.assertEqual(a[0]['sha256'],b[0]['sha256'])
        self.assertIn('알 오 원',str(calls[0]));self.assertNotIn('r_O1',str(calls[0]))
    def test_partial_voice_retry(self):
        cfg=default_config(); cfg.update(max_attempts=1,tts_concurrency=1)
        items=[dict(id='one',text='첫 문단'),dict(id='two',text='두 번째')]; counts={'one':0,'two':0}; fail=[True]
        def transport(payload):
            key='one' if '첫 문단' in payload['contents'][0]['parts'][0]['text'] else 'two'; counts[key]+=1
            if key=='two' and fail[0]: raise ValueError('secret should not leak')
            return {'candidates':[{'finishReason':'STOP','content':{'parts':[{'inlineData':{'mimeType':'audio/L16;rate=24000','data':base64.b64encode(b'\0\0'*2400).decode()}}]}}]}
        with self.assertRaises(Exception): generate_voice(items,self.run,cfg,self.run/'ledger.json',transport)
        fail[0]=False; out=generate_voice(items,self.run,cfg,self.run/'ledger.json',transport)
        self.assertEqual(counts,{'one':1,'two':2}); self.assertEqual(len(out),2)
        self.assertTrue((self.run/'ledger.json').exists())
    def test_voice_defaults_and_secret_redaction(self):
        cfg=default_config(); self.assertEqual((cfg['provider'],cfg['model'],cfg['voice'],cfg['language'],cfg['sample_rate']),('vertex-ai-express','gemini-2.5-flash-tts','Aoede','ko-KR',24000))
        with self.assertRaises(ValueError): generate_voice([],self.run,dict(cfg,api_key='secret'),self.run/'ledger.json',lambda p:{})
