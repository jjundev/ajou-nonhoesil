from fixtures import *
from solution_video.review_adapter import generate_voice,default_config
import base64
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
