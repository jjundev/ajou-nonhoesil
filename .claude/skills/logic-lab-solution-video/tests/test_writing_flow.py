from fixtures import *
from solution_video.util import write,read,file_hash
from solution_video.verify import verify_run

class WritingFlowTests(Sandbox):
    def test_missing_pencil_units_blocks_verify(self):
        write(self.run/'source/timeline.json',dict(writing=dict(mode='pencil')))
        r=verify_run(self.run,Path('/missing'))
        self.assertEqual(r['checks']['writing_flow']['status'],'unverified')
        self.assertEqual(r['checks']['narration_pacing']['status'],'unverified')
    def test_typing_kept(self):
        write(self.run/'source/timeline.json',dict(writing=dict(mode='typing')))
        r=verify_run(self.run,Path('/missing'))
        self.assertEqual(r['checks']['writing_flow']['status'],'passed')
        self.assertEqual(r['checks']['narration_pacing']['status'],'passed')
    def test_pacing_review_invalidates_verify_stage(self):
        from solution_video.state import stage_fingerprint
        a=stage_fingerprint(self.run,'verify')
        write(self.run/'verification/pacing-review.json',dict(input_hash='stale',gaps=[]))
        self.assertNotEqual(a,stage_fingerprint(self.run,'verify'))
    def spatial_fixture(self):
        from test_composition import CompositionTests
        from test_writing_units import unit
        from solution_video.reveal import build_timeline
        from solution_video.review_adapter import default_config
        from solution_video.writing import default_writing
        from solution_video.composition import assemble
        fixture=CompositionTests();fixture.run=self.run;fixture.pencil_fixture(check_browser=False)
        l=read(self.run/'layers/layers.json');m=read(self.run/'source/manifest.json');gs=l['glyphs'];sh=l['shapes']
        # Explicit rows of the synthetic native page: text/subscript, fraction line, answer box.
        rows=[(gs,[s for s in sh if s['kind']=='fraction_bar']),( [],[s for s in sh if s['kind']=='answer_box'])]
        us=[]
        for n,(glyphs,shapes) in enumerate(rows):
            if not glyphs and not shapes:continue
            cuts=sorted(set([v for o in glyphs+shapes for v in (o['bbox'][0],o['bbox'][2])]))
            for j,(lo,hi) in enumerate(zip(cuts,cuts[1:])):
                gids=[g['id'] for g in glyphs if (g['bbox'][0]<hi and g['bbox'][2]>lo) or g['bbox'][0]==g['bbox'][2] and lo<=g['bbox'][0]<hi]
                sids=[s['id'] for s in shapes if s['bbox'][0]<hi and s['bbox'][2]>lo]
                if gids or sids:us.append(unit('u'+str(n)+'_'+str(j),[lo,hi],gids,sids,line='line'+str(n)))
        l['map']['steps'][0]['writing_units']=us;write(self.run/'layers/layers.json',l)
        t=build_timeline(m,l,read(self.run/'source/audio.json')['voices'],default_config(),default_writing());write(self.run/'source/timeline.json',t)
        assemble({'problem':{'snapshot':'pencil.pdf','page_index':0}},l,m,t,self.run,S/'assets/runtime/gsap.min.js')
        return l,t
    def test_native_piece_pixels_order_camera_and_mutations(self):
        from solution_video.util import browser
        l,t=self.spatial_fixture()
        args=['--entry',str(self.run/'composition/index.html'),'--layers',str(self.run/'layers/layers.json'),'--dest',str(self.run/'verification/flow')]
        flow=browser(['--mode','writing-flow',*args]);self.assertTrue(all(flow[k] for k in ['order_ok','fit_ok','transitions_ok','stable_camera','seek_equal']),flow)
        w=browser(['--mode','timeline',*args])['writing'];self.assertEqual(w['hidden_leaks'],0,w);self.assertEqual(w['complete_diff'],0,w);self.assertTrue(w['bounds_ok'],w)
        entry=self.run/'composition/index.html';original=entry.read_text()
        for mutation,key in [("window.solutionTimeline.writing_spans.find(s=>s.kind==='draw').unit_id='wrong'",'order_ok'),("document.querySelector('#answer-page>svg').setAttribute('viewBox','0 0 10 10')",'fit_ok')]:
            entry.write_text(original.replace('</body>',"<script>const prior=window.renderSolutionFrame;window.renderSolutionFrame=f=>{prior(f);"+mutation+";};</script></body>"))
            self.assertFalse(browser(['--mode','writing-flow',*args])[key],key)
    def test_native_radical_outline_accumulates_without_future_leak(self):
        import fitz
        from solution_video.pdf_pages import export_page,extract_layers
        from solution_video.reveal import build_timeline
        from solution_video.writing import default_writing
        from solution_video.review_adapter import default_config
        from solution_video.composition import assemble
        from solution_video.util import browser
        from test_writing_units import unit
        p=self.run/'radical.pdf';d=fitz.open();pg=d.new_page(width=400,height=300)
        pg.insert_text((10,30),'Problem');pg.insert_text((120,120),'ab',fontsize=14)
        pg.draw_polyline([(110,117),(113,121),(117,106),(145,106)]);d.save(p)
        c=export_page(p,0,self.run/'layers');gids=[g['id'] for g in c['glyphs'] if g['bbox'][0]>100];sids=[s['id'] for s in c['shapes'] if s['bbox'][0]>100]
        for s in c['shapes']:
            if s['id'] in sids:s['kind']='radical_bar'
        gs=[g for g in c['glyphs'] if g['id'] in gids]
        us=[unit('left',[110,130],[g['id'] for g in gs if g['bbox'][0]<130],sids),unit('right',[130,145],[g['id'] for g in gs if g['bbox'][2]>130],sids)]
        mp=dict(work_bbox=[100,90,155,130],steps=[dict(id='solution',glyph_ids=gids,shape_ids=sids,writing_units=us)],answer_step_id='solution')
        l=extract_layers(c,mp);write(self.run/'layers/layers.json',l)
        m=dict(segments=[dict(id='intro',kind='problem'),dict(id='w',kind='write',step_id='solution')],shape_anchors={sid:gids[-1] for sid in sids},cameras=[])
        audio=[make_audio(s['id'],2400,self.run) for s in m['segments']];t=build_timeline(m,l,audio,default_config(),default_writing())
        assemble({'problem':{'snapshot':'radical.pdf','page_index':0}},l,m,t,self.run,S/'assets/runtime/gsap.min.js')
        w=browser(['--mode','timeline','--entry',str(self.run/'composition/index.html'),'--layers',str(self.run/'layers/layers.json'),'--dest',str(self.run/'verification/radical')])['writing']
        self.assertEqual(w['hidden_leaks'],0,w);self.assertEqual(w['complete_diff'],0,w);self.assertTrue(w['seek_equal'],w)
    def test_native_vertical_stroke_is_visible_before_completion(self):
        import fitz
        from PIL import Image,ImageChops
        from solution_video.pdf_pages import export_page,extract_layers
        from solution_video.reveal import build_timeline
        from solution_video.writing import default_writing
        from solution_video.review_adapter import default_config
        from solution_video.composition import assemble
        from solution_video.util import browser
        from test_writing_units import unit
        p=self.run/'vertical.pdf';d=fitz.open();pg=d.new_page(width=400,height=300)
        pg.insert_text((10,30),'Problem');pg.insert_text((130,125),'a',fontsize=14);pg.draw_line((120,105),(120,145));d.save(p)
        c=export_page(p,0,self.run/'layers');gids=[g['id'] for g in c['glyphs'] if g['bbox'][0]>100];sids=[s['id'] for s in c['shapes'] if s['bbox'][0]>100]
        mp=dict(work_bbox=[110,90,155,150],steps=[dict(id='solution',glyph_ids=gids,shape_ids=sids,writing_units=[unit('u',[110,155],gids,sids)])],answer_step_id='solution')
        l=extract_layers(c,mp);write(self.run/'layers/layers.json',l)
        m=dict(segments=[dict(id='intro',kind='problem'),dict(id='w',kind='write',step_id='solution')],shape_anchors={sid:gids[-1] for sid in sids},cameras=[])
        t=build_timeline(m,l,[make_audio(s['id'],2400,self.run) for s in m['segments']],default_config(),default_writing())
        assemble({'problem':{'snapshot':'vertical.pdf','page_index':0}},l,m,t,self.run,S/'assets/runtime/gsap.min.js')
        dest=self.run/'verification/vertical';r=browser(['--mode','timeline','--entry',str(self.run/'composition/index.html'),'--layers',str(self.run/'layers/layers.json'),'--dest',str(dest)])['writing']
        draw=next(s for s in t['writing_spans'] if s['kind']=='draw' and s['target_kind']=='shape');start=draw['start_frame'];middle=(start+draw['end_frame']-1)//2
        a=Image.open(dest/f'writing-{start}.png').convert('RGB');b=Image.open(dest/f'writing-{middle}.png').convert('RGB')
        pixels=sum(p!=(0,0,0) for p in ImageChops.difference(a,b).get_flattened_data())
        self.assertGreater(pixels,50,'native vertical line must visibly grow before completion')
        self.assertEqual(r['hidden_leaks'],0,r);self.assertTrue(r['bounds_ok'],r)
