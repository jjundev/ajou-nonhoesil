from fixtures import *
from test_manifest import example
from solution_video.pdf_pages import export_page,extract_layers
from solution_video.reveal import build_timeline
from solution_video.review_adapter import default_config
from solution_video.composition import assemble
from solution_video.util import browser
class CompositionTests(Sandbox):
    def test_explicit_camera_cannot_write_under_caption_after_letterboxing(self):
        from solution_video.composition import camera_keys
        from solution_video.contracts import InputError
        m,l,_,_=example();l['metadata']={'width_pt':1440,'height_pt':810}
        l['glyphs']=[dict(id='g1',text='x',bbox=[100,85,105,90],svg_ids=[],paint_order=0)]
        l['map']['steps']=[dict(id='s',glyph_ids=['g1'],shape_ids=[])]
        m['cameras']=[dict(at_frame=0,viewbox=[0,0,200,100])]
        t=dict(total_frames=130,segments=[dict(start_sample=0,end_sample=80000)],events=[dict(id='g1',frame=5,kind='glyph')])
        with self.assertRaisesRegex(InputError,'camera clips'):
            camera_keys(m,l,t)
    def test_wide_pdf_fills_frame_and_preserves_caption_clip(self):
        import fitz
        p=self.run/'wide.pdf';d=fitz.open();pg=d.new_page(width=1440,height=810)
        pg.insert_text((10,30),'P10.1');pg.insert_text((110,120),'x + y = 2',fontsize=21);d.save(p)
        candidate=export_page(p,0,self.run/'layers');mp=mapping(candidate);layers=extract_layers(candidate,mp)
        m,_,_,_=example();m['segments']=m['segments'][:2];m['segments'][1]['step_id']='solution';m['reveal_order']=mp['steps'][0]['glyph_ids'];m['shape_anchors']={}
        audio=[make_audio(s['id'],2400,self.run) for s in m['segments']];t=build_timeline(m,layers,audio,default_config())
        parts=assemble({'problem':{'snapshot':'wide.pdf','page_index':0}},layers,m,t,self.run,S/'assets/runtime/gsap.min.js')
        r=browser(['--mode','timeline','--entry',str(self.run/parts[0]['entry'])])
        self.assertEqual(r['svg']['width'],1920);self.assertEqual(r['svg']['height'],1080)
        self.assertEqual(r['svg']['x'],0);self.assertEqual(r['viewport']['height'],900)
        self.assertTrue(r['seek_equal']);self.assertEqual(r['final_cursor'],'0')
    def test_parts_have_exact_frame_coverage(self):
        p=math_pdf(self.run/'a.pdf'); candidate=export_page(p,0,self.run/'layers'); mp=mapping(candidate); layers=extract_layers(candidate,mp)
        m,_,_,_=example(); m['segments']=m['segments'][:2]; m['segments'][1]['step_id']='solution'; m['reveal_order']=mp['steps'][0]['glyph_ids']; m['shape_anchors']={s['id']:m['reveal_order'][-1] for s in layers['shapes']}
        audio=[make_audio(s['id'],2400,self.run) for s in m['segments']]; t=build_timeline(m,layers,audio,default_config()); pair={'problem':{'snapshot':'a.pdf','page_index':0}}
        parts=assemble(pair,layers,m,t,self.run,S/'assets/runtime/gsap.min.js')
        self.assertEqual(parts[0]['first_frame'],0); self.assertEqual(parts[-1]['last_frame'],t['total_frames'])
        html=(self.run/parts[0]['entry']).read_text(); self.assertNotIn('katex',html.lower()); self.assertIn('data-composition-id',html); self.assertIn("window.__timelines['solution']",html)
        r=browser(['--mode','timeline','--entry',str(self.run/parts[0]['entry'])]); self.assertTrue(r['seek_equal']); self.assertEqual(r['final_cursor'],'0'); self.assertEqual(r['viewport']['height'],900)
    def test_default_camera_keeps_readable_line_context(self):
        from solution_video.composition import camera_keys
        from test_manifest import example
        m,l,_,_=example();l['metadata']={'width_pt':842,'height_pt':595}
        l['glyphs']=[dict(id='g'+str(i),text='가' if i<8 else '=',bbox=[300+i*12,250,307+i*12,257 if i<8 else 252],svg_ids=[],paint_order=i) for i in range(10)]
        l['map']['steps']=[dict(id='s',glyph_ids=[g['id'] for g in l['glyphs']],shape_ids=[])];l['map']['answer_step_id']='s'
        t=dict(total_frames=120,segments=[dict(start_sample=0,end_sample=80000)],events=[dict(id=g['id'],frame=i*5+1,kind='glyph') for i,g in enumerate(l['glyphs'])])
        keys=camera_keys(m,l,t)
        self.assertLess(max(900/k['viewbox'][3] for k in keys),6)
    def test_explicit_final_zoom_cannot_crop_finished_answer(self):
        from solution_video.composition import camera_keys
        from test_manifest import example
        m,l,_,_=example();l['metadata']={'width_pt':842,'height_pt':595}
        m['cameras']=[dict(at_frame=0,viewbox=[50,50,200,150]),dict(at_frame=100,viewbox=[60,60,180,100]),dict(at_frame=120,viewbox=[60,60,180,100])]
        t=dict(total_frames=130,segments=[dict(start_sample=0,end_sample=80000)],events=[dict(id='g1',frame=5,kind='glyph'),dict(id='g2',frame=50,kind='glyph')])
        keys=camera_keys(m,l,t);self.assertEqual(keys[-1],dict(at_frame=100,viewbox=[0,0,842,595]))
    def pencil_fixture(self,complex_svg=False,mirrored=False,check_browser=True):
        from solution_video.writing import default_writing
        p=self.run/'pencil.pdf'
        if complex_svg:
            import fitz
            d=fitz.open();pg=d.new_page(width=400,height=300);pg.insert_text((110,120),'xx',fontsize=18);pg.insert_text((115,124),'1',fontsize=8);pg.insert_text((110,160),'한글',fontname='korea',fontsize=14)
            for xref in pg.get_contents():d.update_stream(xref,b'q\n1 0.04 0 1 0 0 cm\n100 100 120 100 re W n\n'+d.xref_stream(xref)+b'\nQ\n')
            pg.draw_line((115,133),(140,133));d.save(p)
        else: math_pdf(p)
        c=export_page(p,0,self.run/'layers')
        if complex_svg:
            a,b=c['glyphs'][:2];a['svg_ids']+=b['svg_ids'];a['text']+=b['text'];a['bbox']=[min(a['bbox'][0],b['bbox'][0]),min(a['bbox'][1],b['bbox'][1]),max(a['bbox'][2],b['bbox'][2]),max(a['bbox'][3],b['bbox'][3])];c['glyphs'].remove(b)
        mp=mapping(c);l=extract_layers(c,mp)
        from solution_video.util import write
        write(self.run/'layers/layers.json',l)
        m,_,_,_=example();m['segments']=m['segments'][:2];m['segments'][1]['step_id']='solution';m['reveal_order']=mp['steps'][0]['glyph_ids'];m['shape_anchors']={s['id']:m['reveal_order'][-1] for s in l['shapes']}
        if mirrored:
            b=l['glyphs'][0]['bbox'];sc=28/(b[3]-b[1]);m['cameras']=[dict(at_frame=0,viewbox=[b[0]-1850/sc,b[1]-450/sc,1920/sc,900/sc])]
        audio=[make_audio(s['id'],2400,self.run) for s in m['segments']]
        t=build_timeline(m,l,audio,default_config(),default_writing())
        for name,data in [('manifest',m),('timeline',t),('writing',t['writing']),('config',default_config()),('audio',{'voices':audio})]:write(self.run/'source'/(name+'.json'),data)
        assemble({'problem':{'snapshot':'pencil.pdf','page_index':0}},l,m,t,self.run,S/'assets/runtime/gsap.min.js')
        if not check_browser:return
        return browser(['--mode','timeline','--entry',str(self.run/'composition/index.html'),'--layers',str(self.run/'layers/layers.json'),'--dest',str(self.run/'verification')])
    def test_pencil_partial_and_precomplete(self):
        r=self.pencil_fixture()['writing']
        self.assertEqual(r['precomplete_diff'],0);self.assertEqual(r['complete_diff'],0);self.assertEqual(r['hidden_leaks'],0)
        self.assertLessEqual(r['tip_error_px'],1);self.assertTrue(r['bounds_ok']);self.assertTrue(r['seek_equal']);self.assertTrue(r['gsap_seek_equal'])
    def test_no_pencil_in_holds_or_whitespace(self):
        r=self.pencil_fixture()['writing'];self.assertFalse(r['final_visible']);self.assertTrue(r['inactive_hidden'])
    def test_camera_contains_pencil_at_four_edges(self):
        from solution_video.composition import camera_keys
        from solution_video.writing import default_writing
        m,l,_,_=example();m['segments']=[dict(id='w',kind='write',step_id='s')];m['cameras']=[];m['shape_anchors']={}
        l['metadata']={'width_pt':1440,'height_pt':810}
        l['glyphs']=[dict(id='g'+str(i),text='x',bbox=b,svg_ids=[],paint_order=i) for i,b in enumerate([[0,0,20,20],[1420,0,1440,20],[0,780,20,800],[1420,780,1440,800]])]
        l['map']['steps']=[dict(id='s',glyph_ids=[g['id'] for g in l['glyphs']])]
        t=build_timeline(m,l,[make_audio('w',800,self.run)],default_config(),default_writing());keys=camera_keys(m,l,t)
        for s in t['writing_spans']:
            if s['kind']!='draw':continue
            k=next(k for k in reversed(keys) if k['at_frame']<=s['start_frame']);b=l['glyphs'][int(s['id'][1:])]['bbox'];v=k['viewbox'];sc=1080/v[3]
            x=(b[0]-v[0])*sc;y=(b[1]+.8*(b[3]-b[1])-v[1])*sc
            import math
            meta=json.loads((S/'assets/pencil/pencil-yellow-v1.json').read_text());scale=160/math.dist(meta['tip_px'],meta['end_px']);px=meta['visible_bounds_px']
            for nibx in [x,(b[2]-v[0])*sc]:
                for angle in [-2,0,2]:
                    r=math.radians(angle)
                    for xx,yy in [(px[0],px[1]),(px[2],px[1]),(px[2],px[3]),(px[0],px[3])]:
                        dx=(xx-meta['tip_px'][0])*scale*(-1 if k.get('mirror') else 1);dy=(yy-meta['tip_px'][1])*scale
                        sx=nibx+dx*math.cos(r)-dy*math.sin(r);sy=y+dx*math.sin(r)+dy*math.cos(r)
                        self.assertGreaterEqual(sx,0);self.assertLessEqual(sx,1920);self.assertGreaterEqual(sy,0);self.assertLessEqual(sy,900)
    def test_existing_clip_transform_and_grouped_glyph(self):
        r=self.pencil_fixture(True)['writing']
        self.assertEqual(r['precomplete_diff'],0);self.assertEqual(r['complete_diff'],0);self.assertEqual(r['hidden_leaks'],0);self.assertTrue(r['bounds_ok'])
    def test_long_pencil_can_fit_with_measured_envelope(self):
        from solution_video.composition import camera_keys
        from solution_video.writing import default_writing
        m,l,_,_=example();m['segments']=[dict(id='w',kind='write',step_id='s')];m['shape_anchors']={};m['cameras']=[]
        l['metadata']={'width_pt':1440,'height_pt':810};l['glyphs']=[dict(id='g',text='x',bbox=[100,100,120,120],svg_ids=[],paint_order=0)];l['map']['steps']=[dict(id='s',glyph_ids=['g'])]
        w=default_writing();w['pencil_length_px']=400;t=build_timeline(m,l,[make_audio('w',800,self.run)],default_config(),w)
        keys=camera_keys(m,l,t);self.assertTrue(keys)
    def test_pencil_explicit_camera_preserves_zoom_and_readability(self):
        from solution_video.composition import camera_keys
        from solution_video.writing import default_writing
        from solution_video.contracts import InputError
        m,l,_,_=example();m['segments']=[dict(id='w',kind='write',step_id='s')];m['shape_anchors']={}
        l['metadata']={'width_pt':1440,'height_pt':810};l['glyphs']=[dict(id='g',text='x',bbox=[100,100,120,120],svg_ids=[],paint_order=0)];l['map']['steps']=[dict(id='s',glyph_ids=['g'])]
        t=build_timeline(m,l,[make_audio('w',800,self.run)],default_config(),default_writing())
        m['cameras']=[dict(at_frame=0,viewbox=[0,0,400,225])];keys=camera_keys(m,l,t);self.assertAlmostEqual(keys[1]['viewbox'][2],400);self.assertAlmostEqual(keys[1]['viewbox'][3],225)
        m['cameras']=[dict(at_frame=0,viewbox=[0,0,1920,1080])]
        with self.assertRaisesRegex(InputError,'too small'):camera_keys(m,l,t)
    def test_pencil_mirrors_before_moving_explicit_camera(self):
        from solution_video.composition import camera_keys
        from solution_video.writing import default_writing
        m,l,_,_=example();m['segments']=[dict(id='w',kind='write',step_id='s')];m['shape_anchors']={};m['cameras']=[dict(at_frame=0,viewbox=[0,0,400,225])]
        l['metadata']={'width_pt':1440,'height_pt':810};l['glyphs']=[dict(id='g',text='x',bbox=[365,100,380,120],svg_ids=[],paint_order=0)];l['map']['steps']=[dict(id='s',glyph_ids=['g'])]
        t=build_timeline(m,l,[make_audio('w',800,self.run)],default_config(),default_writing());k=camera_keys(m,l,t)[1]
        self.assertAlmostEqual(k['viewbox'][0],0);self.assertAlmostEqual(k['viewbox'][1],0);self.assertAlmostEqual(k['viewbox'][2],400);self.assertAlmostEqual(k['viewbox'][3],225);self.assertTrue(k['mirror'])
    def test_mirrored_png_stays_aligned_in_browser(self):
        r=self.pencil_fixture(mirrored=True)['writing']
        self.assertTrue(r['bounds_ok']);self.assertLessEqual(r['tip_error_px'],1);self.assertEqual(r['precomplete_diff'],0);self.assertEqual(r['hidden_leaks'],0)
    def prepared_pencil_run(self):
        from solution_video.util import read,write,digest,file_hash
        from solution_video.manifest import content_fingerprint
        from solution_video.pdf_pages import compare_completed
        from solution_video.state import finish_stage,STAGES
        self.run=self.run.resolve();self.pencil_fixture(check_browser=False)
        m=read(self.run/'source/manifest.json');l=read(self.run/'layers/layers.json');step=l['map']['steps'][0]
        c=dict(status='passed',pdf_md_agree=True,rows=[dict(step_id=step['id'],source_refs=['answer:1'],pdf_text=''.join(g['text'] for g in l['glyphs']),md_text='Synthetic math fixture',meaning_review='Controlled fixture matches original glyphs')])
        r=dict(status='passed',steps=[dict(step_id=step['id'],assumptions='fixture',equations='x+y=2',units='symbolic',evidence='original PDF')]);h=content_fingerprint(m,l,c);c['input_hash']=r['input_hash']=h
        write(self.run/'source/coverage.json',c);write(self.run/'source/circuit-review.json',r)
        write(self.run/'source/pair.json',dict(problem_id=m['problem_id'],problem=dict(snapshot='pencil.pdf',page_index=0)))
        g=compare_completed(l,self.run/'verification/gate-frames');g.update(input_hash=digest(l),source_hashes={k:file_hash(l[k]) for k in ['original_svg','animated_svg','reference_png']})
        g['evidence']=[str(Path(p).relative_to(self.run)) for p in g['evidence']];g['evidence_hashes']={p:file_hash(self.run/p) for p in g['evidence']};write(self.run/'verification/gate.json',g)
        for stage in STAGES[:6]:
            out=self.run/(stage+'.txt');out.write_text(stage)
            finish_stage(self.run,stage,[self.run/'source/timeline.json'] if stage=='timing' else [out])
    def test_visual_settings_refresh_without_retime(self):
        from test_cli import cli
        from types import SimpleNamespace
        from solution_video.util import read,write,file_hash
        from solution_video.state import recover_run
        self.prepared_pencil_run()
        before=read(self.run/'state.json');timeline_hash=file_hash(self.run/'source/timeline.json');voice_hash=file_hash(self.run/'source/audio.json')
        wav_hashes={a['path']:file_hash(self.run/a['path']) for a in read(self.run/'source/audio.json')['voices']}
        writing=read(self.run/'source/writing.json');writing.update(pencil_length_px=120,tilt_degrees=0);write(self.run/'source/writing.json',writing)
        self.assertEqual(recover_run(self.run),'composition')
        result=cli.run_stage('assemble',self.run,SimpleNamespace(runtime=S/'assets/runtime/gsap.min.js'))
        self.assertEqual(result['status'],'passed');self.assertEqual(result['paid_requests'],0)
        actual=read(self.run/'composition/timeline.json')['writing'];self.assertEqual(actual['pencil_length_px'],120);self.assertEqual(actual['tilt_degrees'],0)
        self.assertEqual(file_hash(self.run/'source/timeline.json'),timeline_hash);self.assertEqual(file_hash(self.run/'source/audio.json'),voice_hash)
        for name,sha in wav_hashes.items():self.assertEqual(file_hash(self.run/name),sha)
        after=read(self.run/'state.json')
        for stage in ['voice','timing']:self.assertEqual(after['stages'][stage],before['stages'][stage])
        self.assertFalse((self.run/'usage.json').exists())
        writing['chars_per_second']=4;write(self.run/'source/writing.json',writing)
        with self.assertRaisesRegex(ValueError,'prerequisite stage: timing'):cli.run_stage('assemble',self.run,SimpleNamespace(runtime=S/'assets/runtime/gsap.min.js'))
    def test_visual_settings_verify_against_current_composition(self):
        from solution_video.util import read,write
        from solution_video.verify import verify_run
        self.prepared_pencil_run();writing=read(self.run/'source/writing.json');writing.update(pencil_length_px=120,tilt_degrees=0);write(self.run/'source/writing.json',writing)
        t=read(self.run/'source/timeline.json');t['writing']=writing
        assemble(read(self.run/'source/pair.json'),read(self.run/'layers/layers.json'),read(self.run/'source/manifest.json'),t,self.run,S/'assets/runtime/gsap.min.js')
        report=verify_run(self.run,Path('/missing/hyperframes'))
        self.assertEqual(report['checks']['writing_animation']['status'],'passed')
    def teaching_fixture(self,mode='pencil'):
        from solution_video.annotations import load_teaching
        from solution_video.teaching import build_teaching_timeline
        from solution_video.util import read,write
        self.pencil_fixture(check_browser=False)
        m=read(self.run/'source/manifest.json');l=read(self.run/'layers/layers.json')
        m['segments'].insert(1,dict(id='r',kind='reason',step_id='solution',text='회로의 방향을 표시합니다.',source_refs=['answer:1']))
        f=dict(schema_version=1,source_sha256=l['metadata']['source_sha256'],regions=[dict(id='circuit',bbox=[30,35,190,75])],cues=[dict(segment_id='r',target='circuit')])
        a=dict(schema_version=1,source_sha256=f['source_sha256'],items=[dict(id='arrow',segment_id='r',region_id='circuit',kind='arrow',geometry={'from':[60,40],'to':[60,65]},source_refs=['answer:1'],meaning_notes='synthetic test')])
        write(self.run/'source/focus.json',f);write(self.run/'source/annotations.json',a)
        from solution_video.writing import default_writing
        w=default_writing(mode);write(self.run/'source/writing.json',w)
        audio=[make_audio(s['id'],2400,self.run) for s in m['segments']]
        t=build_teaching_timeline(m,l,audio,default_config(),w,load_teaching(self.run,m,l))
        write(self.run/'source/manifest.json',m);write(self.run/'source/audio.json',{'voices':audio});write(self.run/'source/timeline.json',t)
        assemble({'problem':{'snapshot':'pencil.pdf','page_index':0}},l,m,t,self.run,S/'assets/runtime/gsap.min.js')
        return t
    def test_typing_annotations_load_pencil_but_legacy_does_not(self):
        t=self.teaching_fixture('typing');html=(self.run/'composition/index.html').read_text()
        self.assertIn('id="pencil"',html);self.assertTrue((self.run/'composition/annotations/compiled.json').is_file())
        self.assertIn('annotations.js',html)
        self.assertEqual(html.count('id="pencil"'),1)
    def test_annotation_and_original_share_one_pen(self):
        self.teaching_fixture()
        r=browser(['--mode','teaching','--entry',str(self.run/'composition/index.html'),'--layers',str(self.run/'layers/layers.json'),'--dest',str(self.run/'verification/teaching-frames')])
        self.assertTrue(r['bounds_ok']);self.assertTrue(r['seek_equal']);self.assertTrue(r['gsap_seek_equal']);self.assertLessEqual(r['tip_error_px'],1)
        self.assertEqual(r['original_pixel_diff'],0);self.assertEqual(r['annotation_pixel_diff'],0);self.assertFalse(r['final_visible'])
    def test_teaching_mutations_block_completion(self):
        self.teaching_fixture('typing');html=self.run/'composition/index.html';base=html.read_text()
        for change in ["document.getElementById('annotation-arrow').remove();", "document.getElementById('pencil').style.transform='translate(50px,50px)';", "document.getElementById('annotation-arrow').style.opacity='1';", "document.querySelector('#answer-page>svg').setAttribute('viewBox','0 0 200 100');"]:
            html.write_text(base.replace('</body>',"<script>const renderOriginal=window.renderSolutionFrame;window.renderSolutionFrame=f=>{renderOriginal(f);"+change+"};</script></body>"))
            with self.subTest(change=change):
                from solution_video.contracts import InputError
                try:r=browser(['--mode','teaching','--entry',str(html),'--layers',str(self.run/'layers/layers.json'),'--dest',str(self.run/'verification/teaching-frames')])
                except InputError:continue
                self.assertFalse(r.get('bounds_ok',False) and r.get('seek_equal',False) and r.get('tip_error_px',2)<=1 and r.get('annotation_pixel_diff',1)==0 and r.get('cameras_equal',False) and not r.get('final_visible',True))
        html.write_text(base)

    def test_labels_whitespace_and_focus_only_in_browser(self):
        from solution_video.util import read,write
        from solution_video.annotations import load_teaching
        from solution_video.teaching import build_teaching_timeline
        self.teaching_fixture('typing');m=read(self.run/'source/manifest.json');l=read(self.run/'layers/layers.json');a=read(self.run/'source/annotations.json')
        a['items'][0].update(kind='label',geometry={'runs':[dict(text='v ',origin=[60,55],font_size_pt=12),dict(text='x',origin=[72,60],font_size_pt=8)]})
        for items in [a['items'],[]]:
            a['items']=items;write(self.run/'source/annotations.json',a)
            t=build_teaching_timeline(m,l,read(self.run/'source/audio.json')['voices'],default_config(),read(self.run/'source/writing.json'),load_teaching(self.run,m,l));write(self.run/'source/timeline.json',t)
            assemble({'problem':{'snapshot':'pencil.pdf','page_index':0}},l,m,t,self.run,S/'assets/runtime/gsap.min.js')
            r=browser(['--mode','teaching','--entry',str(self.run/'composition/index.html'),'--layers',str(self.run/'layers/layers.json'),'--dest',str(self.run/'verification/teaching-frames')])
            self.assertEqual(r['annotation_pixel_diff'],0);self.assertEqual(r['original_pixel_diff'],0);self.assertTrue(r['bounds_ok']);self.assertTrue(r['inactive_hidden'])
    def test_different_figures_do_not_drag_pen_from_hidden_camera(self):
        from solution_video.util import read,write
        from solution_video.annotations import load_teaching
        from solution_video.teaching import build_teaching_timeline
        self.teaching_fixture();m=read(self.run/'source/manifest.json');l=read(self.run/'layers/layers.json');f=read(self.run/'source/focus.json');a=read(self.run/'source/annotations.json')
        m['segments'].append(dict(id='check2',kind='check',step_id='solution',text='다른 그림을 확인합니다.',source_refs=['answer:1']))
        f['regions'].append(dict(id='other',bbox=[300,35,310,75]));f['cues'].append(dict(segment_id='check2',target='other'))
        a['items'].append(dict(a['items'][0],id='other_arrow',segment_id='check2',region_id='other',geometry={'from':[305,40],'to':[305,65]}))
        write(self.run/'source/focus.json',f);write(self.run/'source/annotations.json',a)
        audio=[make_audio(s['id'],2400,self.run) for s in m['segments']];t=build_teaching_timeline(m,l,audio,default_config(),read(self.run/'source/writing.json'),load_teaching(self.run,m,l));write(self.run/'source/timeline.json',t)
        assemble({'problem':{'snapshot':'pencil.pdf','page_index':0}},l,m,t,self.run,S/'assets/runtime/gsap.min.js')
        r=browser(['--mode','teaching','--entry',str(self.run/'composition/index.html'),'--layers',str(self.run/'layers/layers.json'),'--dest',str(self.run/'verification/teaching-frames')]);self.assertTrue(r['bounds_ok'])
    def test_annotation_glyph_definition_tampering_is_detected(self):
        from solution_video.util import read,write
        from solution_video.annotations import load_teaching
        from solution_video.teaching import build_teaching_timeline
        self.teaching_fixture('typing');m=read(self.run/'source/manifest.json');l=read(self.run/'layers/layers.json');a=read(self.run/'source/annotations.json')
        a['items'][0].update(kind='label',geometry={'runs':[dict(text='v',origin=[60,55],font_size_pt=12)]});write(self.run/'source/annotations.json',a)
        t=build_teaching_timeline(m,l,read(self.run/'source/audio.json')['voices'],default_config(),read(self.run/'source/writing.json'),load_teaching(self.run,m,l))
        assemble({'problem':{'snapshot':'pencil.pdf','page_index':0}},l,m,t,self.run,S/'assets/runtime/gsap.min.js')
        entry=self.run/'composition/index.html';entry.write_text(entry.read_text().replace('</body>',"<script>document.querySelectorAll('#teaching-annotations defs path').forEach(p=>p.setAttribute('d',''));</script></body>"))
        r=browser(['--mode','teaching','--entry',str(entry),'--layers',str(self.run/'layers/layers.json'),'--dest',str(self.run/'verification/teaching-frames')])
        self.assertGreater(r['annotation_pixel_diff'],0)
    def test_focus_return_preserves_last_draw_screen_tip(self):
        import fitz
        from solution_video.writing import default_writing
        from solution_video.annotations import load_teaching
        from solution_video.teaching import build_teaching_timeline
        from solution_video.util import write
        pdf=self.run/'wide-check.pdf';d=fitz.open();page=d.new_page(width=1440,height=810)
        for x,y,text in [(100,140,'x'),(1250,140,'y'),(100,210,'z')]:page.insert_text((x,y),text,fontsize=20)
        page.draw_rect((780,60,940,90));d.save(pdf);d.close()
        c=export_page(pdf,0,self.run/'layers');g={g['text']:g['id'] for g in c['glyphs']}
        mp=dict(work_bbox=[90,100,1350,230],steps=[dict(id='s1',glyph_ids=[g['x'],g['y']],shape_ids=[]),dict(id='s2',glyph_ids=[g['z']],shape_ids=[])],answer_step_id='s2');l=extract_layers(c,mp)
        m=dict(segments=[dict(id='intro',kind='problem',step_id='',text='intro'),dict(id='w1',kind='write',step_id='s1',text='write'),dict(id='c',kind='check',step_id='s1',text='check'),dict(id='w2',kind='write',step_id='s2',text='write')],reveal_order=[g['x'],g['y'],g['z']],shape_anchors={},cameras=[])
        f=dict(schema_version=1,source_sha256=l['metadata']['source_sha256'],regions=[dict(id='figure',bbox=[780,60,940,90])],cues=[dict(segment_id='c',target='figure')]);write(self.run/'source/focus.json',f);write(self.run/'layers/layers.json',l)
        t=build_teaching_timeline(m,l,[make_audio(s['id'],800,self.run) for s in m['segments']],default_config(),default_writing(),load_teaching(self.run,m,l))
        assemble({'problem':{'snapshot':'wide-check.pdf','page_index':0}},l,m,t,self.run,S/'assets/runtime/gsap.min.js')
        r=browser(['--mode','timeline','--entry',str(self.run/'composition/index.html'),'--layers',str(self.run/'layers/layers.json'),'--dest',str(self.run/'verification/writing')])
        self.assertTrue(r['writing']['bounds_ok'])
