from fixtures import *
from solution_video.state import finish_stage,recover_run,STAGES
from solution_video.util import write
class StateTests(Sandbox):
    def test_lesson_edit_invalidates_script(self):
        from solution_video.state import stage_fingerprint
        before=stage_fingerprint(self.run,'script')
        write(self.run/'source/lesson.json',{'schema_version':1,'steps':[]})
        added=stage_fingerprint(self.run,'script');self.assertNotEqual(before,added)
        write(self.run/'source/lesson.json',{'schema_version':1,'steps':[{'exemption_reason':'changed'}]})
        self.assertNotEqual(added,stage_fingerprint(self.run,'script'))
        (self.run/'source/lesson.json').unlink();self.assertEqual(before,stage_fingerprint(self.run,'script'))
    def test_caption_edit_invalidates_script_preserving_pcm(self):
        from solution_video.state import stage_fingerprint
        from solution_video.util import file_hash
        a=make_audio('w',2400,self.run);sha=file_hash(self.run/a['path'])
        write(self.run/'source/manifest.json',dict(segments=[dict(id='w',text='알 오 원',caption_text='r_O1')]))
        before=stage_fingerprint(self.run,'script')
        write(self.run/'source/manifest.json',dict(segments=[dict(id='w',text='알 오 원',caption_text='저항 r_O1')]))
        self.assertNotEqual(before,stage_fingerprint(self.run,'script'));self.assertEqual(sha,file_hash(self.run/a['path']))
    def test_first_invalid_stage_and_voice_preservation(self):
        (self.run/'source').mkdir(); (self.run/'layers').mkdir(); write(self.run/'source/map.json',{'work_bbox':[1,2,3,4]}); write(self.run/'source/config.json',{'voice':'Aoede'})
        pub=self.run/'published.mp4';pub.write_bytes(b'published')
        from solution_video.util import file_hash
        write(self.run/'verification/publication.json',{'published':{str(pub):file_hash(pub)}})
        for stage in STAGES:
            out=self.run/(stage+'.txt'); out.write_text(stage); finish_stage(self.run,stage,[out])
        self.assertIsNone(recover_run(self.run))
        write(self.run/'source/config.json',{'voice':'Other'}); self.assertEqual(recover_run(self.run),'voice')
        write(self.run/'source/map.json',{'work_bbox':[1,2,30,40]}); self.assertEqual(recover_run(self.run),'layers'); self.assertEqual((self.run/'voice.txt').read_text(),'voice')
    def test_writing_and_asset_first_invalid_stage(self):
        import copy,shutil
        from unittest.mock import patch
        import solution_video.state as state
        from solution_video.writing import default_writing
        root=self.run/'tool';shutil.copytree(S,root,ignore=shutil.ignore_patterns('__pycache__'))
        c=default_writing();write(self.run/'source/writing.json',c)
        def finish():
            for stage in STAGES[:6]:
                out=self.run/(stage+'.txt');out.write_text(stage);finish_stage(self.run,stage,[out])
        with patch.object(state,'S',root):
            finish();c['chars_per_second']=4;write(self.run/'source/writing.json',c);self.assertEqual(recover_run(self.run),'timing')
            finish();c['pencil_length_px']=150;write(self.run/'source/writing.json',c);self.assertEqual(recover_run(self.run),'composition')
            finish();p=root/'assets/pencil/pencil-yellow-v1.json';meta=json.loads(p.read_text());meta['tip_px'][0]+=1;write(p,meta);self.assertEqual(recover_run(self.run),'composition')
            (self.run/'source/writing.json').unlink();finish();meta['tip_px'][0]+=1;write(p,meta);self.assertEqual(recover_run(self.run),'render')
    def test_teaching_visual_timing_add_delete(self):
        from test_annotations import teaching_fixture
        f,a,m,l=teaching_fixture();write(self.run/'source/manifest.json',m);write(self.run/'layers/layers.json',l)
        def finish():
            for stage in STAGES[:6]:
                out=self.run/(stage+'.txt');out.write_text(stage);finish_stage(self.run,stage,[out])
        finish();write(self.run/'source/focus.json',f);write(self.run/'source/annotations.json',a)
        self.assertEqual(recover_run(self.run),'timing')
        finish();a['items'][0]['color']='#FF0000';write(self.run/'source/annotations.json',a);self.assertEqual(recover_run(self.run),'composition')
        finish();a['items'][0]['offset_frames']=20;write(self.run/'source/annotations.json',a);self.assertEqual(recover_run(self.run),'timing')
        finish();(self.run/'source/annotations.json').unlink();(self.run/'source/focus.json').unlink();self.assertEqual(recover_run(self.run),'timing')
    def test_spatial_units_script_and_camera_invalidate_correct_stages(self):
        import shutil
        from unittest.mock import patch
        import solution_video.state as state
        root=self.run/'tool';shutil.copytree(S,root,ignore=shutil.ignore_patterns('__pycache__'))
        from solution_video.util import read,file_hash
        from solution_video.writing import default_writing
        write(self.run/'source/writing.json',default_writing());write(self.run/'source/map.json',dict(steps=[dict(writing_units=[])]))
        voice=make_audio('w',2400,self.run);before=file_hash(self.run/voice['path'])
        def finish():
            for stage in STAGES[:6]:
                out=self.run/(stage+'.txt');out.write_text(stage);finish_stage(self.run,stage,[out])
        with patch.object(state,'S',root):
            finish();mp=read(self.run/'source/map.json');mp['steps'][0]['writing_units']=[dict(id='changed')];write(self.run/'source/map.json',mp)
            self.assertEqual(recover_run(self.run),'layers')
            finish();write(self.run/'source/manifest.json',dict(segments=[dict(text='new explanation')]))
            self.assertEqual(recover_run(self.run),'script')
            finish();p=root/'scripts/solution_video/writing_camera.py';p.write_text(p.read_text()+'\n# camera edit\n')
            self.assertEqual(recover_run(self.run),'composition');self.assertEqual(file_hash(self.run/voice['path']),before)
