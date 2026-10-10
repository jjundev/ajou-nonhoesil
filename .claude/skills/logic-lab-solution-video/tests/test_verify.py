from fixtures import *
from solution_video.util import read,write
from solution_video.verify import verify_run
class VerifyTests(Sandbox):
    def test_notation_warnings_are_reported_without_new_gate(self):
        write(self.run/'source/manifest.json',dict(segments=[dict(id='s',caption_text='값은 이입니다.')]))
        report=verify_run(self.run,Path('/missing/hyperframes'))
        self.assertEqual(len(report.get('warnings',[])),1)
        self.assertEqual(report['warnings'][0]['code'],'numeric_predicate')
        self.assertNotIn('caption_notation',report['checks'])

    def test_captions_gate_rejects_srt_that_differs_from_write_srt(self):
        # A captioned screen alone is not enough: cue numbers, wrapped lines and times must equal write_srt now.
        from solution_video.subtitles import write_srt,burn_subtitles
        from solution_video.media import ffmpeg
        from solution_video.util import checked
        text='그래서 반가산기의 합 출력 S는 A′B + AB′이고 XOR와 같아요.'
        timeline=dict(rate=24000,segments=[dict(id='s',caption_text=text,start_sample=0,end_sample=24000,voice_samples=24000)])
        write(self.run/'source/timeline.json',timeline);(self.run/'renders').mkdir(exist_ok=True)
        master=self.run/'renders/master.mp4'
        checked([ffmpeg(),'-y','-v','error','-f','lavfi','-i','color=c=black:s=1920x1080:r=30:d=1','-c:v','libx264','-pix_fmt','yuv420p',master])
        srt=write_srt(timeline,self.run/'renders/captions.srt')
        burn_subtitles(master,srt,self.run/'renders/final.mp4',S/'assets/fonts/Pretendard-Bold.ttf')
        self.assertEqual(verify_run(self.run,Path('/missing/hyperframes'))['checks']['captions']['status'],'passed')
        srt.write_text(srt.read_text(encoding='utf-8').replace('S는\nA′B + AB′','S는 A′B +\nAB′'),encoding='utf-8')
        self.assertEqual(verify_run(self.run,Path('/missing/hyperframes'))['checks']['captions']['status'],'unverified')

    def test_final_media_checked_after_burn(self):
        report=verify_run(self.run,Path('/missing/hyperframes'))
        self.assertFalse(report['complete']); self.assertIsNone(report['final_sha256'])
    def test_source_timeout_and_missing_reviews(self):
        report=verify_run(self.run,Path('/missing/hyperframes'))
        self.assertFalse(report['complete']); self.assertIn('unverified',str(report['checks']))
    def test_gate_evidence_tamper_is_rejected(self):
        from solution_video.util import write,digest,file_hash
        from solution_video.verify import gate_valid
        layer=dict(original_svg=str(self.run/'a.svg'),animated_svg=str(self.run/'b.svg'),reference_png=str(self.run/'native.png'))
        for p in [self.run/'a.svg',self.run/'b.svg',self.run/'native.png',self.run/'evidence.png']:p.write_bytes(b'original')
        g=dict(input_hash=digest(layer),pixel_diff=0,non_target_diff=0,hidden_leaks=0,evidence=['evidence.png'],evidence_hashes={'evidence.png':file_hash(self.run/'evidence.png')},source_hashes={k:file_hash(v) for k,v in layer.items()})
        self.assertTrue(gate_valid(self.run,layer,g));(self.run/'evidence.png').write_bytes(b'changed')
        self.assertFalse(gate_valid(self.run,layer,g))
    def test_pencil_gate_failure_blocks_verify(self):
        from solution_video.util import write
        write(self.run/'source/timeline.json',{'writing':{'mode':'pencil'}})
        report=verify_run(self.run,Path('/missing/hyperframes'))
        self.assertFalse(report['complete']);self.assertEqual(report['checks']['writing_animation']['status'],'unverified')
    def test_typing_requires_no_pencil(self):
        from solution_video.util import write
        write(self.run/'source/timeline.json',{'writing':{'mode':'typing'}})
        report=verify_run(self.run,Path('/missing/hyperframes'))
        self.assertEqual(report['checks']['writing_animation']['status'],'passed')
    def test_actual_composition_tampering_is_rejected(self):
        from test_composition import CompositionTests
        from solution_video.util import write,read,digest,file_hash
        from solution_video.pdf_pages import compare_completed
        from solution_video.writing import default_writing
        self.run=self.run.resolve()
        fixture=CompositionTests();fixture.run=self.run;fixture.pencil_fixture()
        layers=read(self.run/'layers/layers.json');g=compare_completed(layers,self.run/'verification/gate-frames')
        g['input_hash']=digest(layers);g['evidence']=[str(Path(p).relative_to(self.run)) for p in g['evidence']];g['evidence_hashes']={p:file_hash(self.run/p) for p in g['evidence']};g['source_hashes']={k:file_hash(layers[k]) for k in ['original_svg','animated_svg','reference_png']};write(self.run/'verification/gate.json',g)
        write(self.run/'source/timeline.json',read(self.run/'composition/timeline.json'))
        entry=self.run/'composition/index.html';original=entry.read_text()
        for mutation in ["document.querySelector('#answer-page [data-reveal]').style.opacity='1'", "document.getElementById('pencil').style.transform='translate(0px,0px)'", "document.getElementById('pencil').style.opacity='1'"]:
            with self.subTest(mutation=mutation):
                entry.write_text(original.replace('</body>',"<script>const realRender=window.renderSolutionFrame;window.renderSolutionFrame=f=>{realRender(f);"+mutation+";};</script></body>"))
                r=verify_run(self.run,Path('/missing/hyperframes'))
                self.assertEqual(r['checks']['original_svg']['status'],'passed');self.assertEqual(r['checks']['writing_animation']['status'],'unverified');self.assertFalse(r['complete'])
    def test_blank_timeline_cannot_pass_original_gate(self):
        from test_composition import CompositionTests
        from solution_video.util import read,write
        self.run=self.run.resolve();fixture=CompositionTests();fixture.run=self.run;fixture.pencil_fixture()
        entry=self.run/'composition/index.html';entry.write_text(entry.read_text().replace('</body>',"<script>window.solutionTimeline.events=[];window.solutionTimeline.writing_spans=[];window.renderSolutionFrame(0);</script></body>"))
        t=read(self.run/'source/timeline.json');t['events']=[];t['writing_spans']=[];write(self.run/'source/timeline.json',t)
        r=verify_run(self.run,Path('/missing/hyperframes'))
        self.assertEqual(r['checks']['writing_animation']['status'],'unverified')
    def test_typing_teaching_is_not_exempt(self):
        from solution_video.util import write
        write(self.run/'source/timeline.json',{'writing':{'mode':'typing'},'teaching':{'spans':[]}})
        r=verify_run(self.run,Path('/missing/hyperframes'))
        self.assertIn('teaching_animation',r['checks'])
        self.assertEqual(r['checks']['teaching_animation']['status'],'unverified')
    def test_original_gate_survives_annotations(self):
        from test_composition import CompositionTests
        from solution_video.util import read,write,digest,file_hash
        from solution_video.pdf_pages import compare_completed
        self.run=self.run.resolve();fixture=CompositionTests();fixture.run=self.run;fixture.teaching_fixture('typing')
        l=read(self.run/'layers/layers.json');g=compare_completed(l,self.run/'verification/gate-frames');g.update(input_hash=digest(l),source_hashes={k:file_hash(l[k]) for k in ['original_svg','animated_svg','reference_png']})
        g['evidence']=[str(Path(p).relative_to(self.run)) for p in g['evidence']];g['evidence_hashes']={p:file_hash(self.run/p) for p in g['evidence']};write(self.run/'verification/gate.json',g)
        report=verify_run(self.run,Path('/missing/hyperframes'))
        self.assertEqual(report['checks']['original_svg']['status'],'passed');self.assertEqual(report['checks']['teaching_animation']['status'],'passed');self.assertFalse(report['complete'])
        t=read(self.run/'source/timeline.json');t['teaching']['spans'][0]['end_frame']+=1;write(self.run/'source/timeline.json',t)
        self.assertEqual(verify_run(self.run,Path('/missing/hyperframes'))['checks']['teaching_animation']['status'],'unverified')
    def test_teaching_visual_pencil_setting_does_not_require_retime(self):
        from test_composition import CompositionTests
        from solution_video.util import read,write
        from solution_video.composition import assemble
        self.run=self.run.resolve();fixture=CompositionTests();fixture.run=self.run;fixture.teaching_fixture()
        w=read(self.run/'source/writing.json');w['pencil_length_px']=120;write(self.run/'source/writing.json',w)
        assemble({'problem':{'snapshot':'pencil.pdf','page_index':0}},read(self.run/'layers/layers.json'),read(self.run/'source/manifest.json'),read(self.run/'source/timeline.json'),self.run,S/'assets/runtime/gsap.min.js')
        report=verify_run(self.run,Path('/missing/hyperframes'))
        self.assertEqual(report['checks']['teaching_animation']['status'],'passed')
