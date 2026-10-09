from fixtures import *
from unittest.mock import patch
from solution_video.publication import publish_batch
from solution_video.util import write,file_hash
class PublicationTests(Sandbox):
    def setUp(self):
        super().setUp(); self.root=self.run/'output'; self.batch=self.root/'1002_제작자료/실행/batch'; self.batch.mkdir(parents=True)
        items=[]
        for i in range(2):
            run=self.batch/f'videos/p{i}'; (run/'renders').mkdir(parents=True); f=run/'renders/final.mp4';f.write_bytes(b'final'+bytes([i]));write(run/'verification/report.json',{'complete':True,'final_sha256':file_hash(f),'input_hash':'x'})
            items.append({'id':str(i),'run':f'videos/p{i}','filename':str(i)+'.mp4'})
        write(self.batch/'batch.json',{'items':items,'selector':'1002'}); self.latest=self.root/'1002_제작자료/latest.json'; write(self.latest,{'previous':'old'})
    def test_final_tamper_and_publish_rollback(self):
        before=self.latest.read_bytes(); (self.batch/'videos/p0/renders/final.mp4').write_bytes(b'tampered')
        with patch('solution_video.publication.report_current',return_value=True): result=publish_batch(self.batch)
        self.assertFalse(result['complete']); self.assertEqual(self.latest.read_bytes(),before); self.assertEqual(result['published'],['1.mp4'])
    def test_move_failure_restores_previous(self):
        for i in range(2): (self.root/f'{i}.mp4').write_bytes(b'previous'+bytes([i]))
        before=self.latest.read_bytes(); import os
        original=os.replace; triggered=[False]
        def replace(a,b):
            if Path(b).resolve()==(self.root/'1.mp4').resolve() and '.staging' in str(a) and not triggered[0]: triggered[0]=True; raise OSError('injected move failure')
            return original(a,b)
        with patch('solution_video.publication.report_current',return_value=True),patch('solution_video.publication.os.replace',side_effect=replace): result=publish_batch(self.batch)
        self.assertFalse(result['complete']); self.assertEqual(self.latest.read_bytes(),before)
        for i in range(2): self.assertEqual((self.root/f'{i}.mp4').read_bytes(),b'previous'+bytes([i]))
    def test_same_title_collision(self):
        data=json.loads((self.batch/'batch.json').read_text()); data['items'][1]['filename']=data['items'][0]['filename'];write(self.batch/'batch.json',data)
        with patch('solution_video.publication.report_current',return_value=True): result=publish_batch(self.batch)
        self.assertFalse(result['complete']); self.assertEqual(result['published'],[])
    def test_published_receipt_completes_and_tracks_real_file(self):
        from solution_video.state import STAGES,finish_stage,recover_run
        for item in json.loads((self.batch/'batch.json').read_text())['items']:
            run=self.batch/item['run']
            for stage in STAGES[:-1]:
                out=run/(stage+'.txt');out.write_text(stage);finish_stage(run,stage,[out])
        with patch('solution_video.publication.report_current',return_value=True):result=publish_batch(self.batch)
        self.assertTrue(result['complete'])
        run=self.batch/'videos/p0';self.assertIsNone(recover_run(run))
        (self.root/'0.mp4').write_bytes(b'changed');self.assertEqual(recover_run(run),'publish')
    def test_authored_title_becomes_sanitized_filename(self):
        for i in range(2):
            run=self.batch/f'videos/p{i}';write(run/'source/manifest.json',{'problem_id':str(i),'title':'전압/이득: 확인'})
        with patch('solution_video.publication.report_current',return_value=True):result=publish_batch(self.batch)
        self.assertEqual(result['published'],['0 — 전압 이득 확인.mp4','1 — 전압 이득 확인.mp4'])
