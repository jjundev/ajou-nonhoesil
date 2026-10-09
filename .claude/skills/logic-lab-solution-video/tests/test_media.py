from fixtures import *
from solution_video.subtitles import write_srt,burn_subtitles
from solution_video.util import checked
class MediaTests(Sandbox):
    def test_white_pdf_renders_and_captions_stay_outside(self):
        self.check_caption_strip('원본 풀이를 확인합니다.')
    def test_two_line_caption_strip(self):
        self.check_caption_strip('따라서 Q₁은 이미터가 접지된 공통 이미터 증폭기로 볼 수 있습니다.',True)
    def check_caption_strip(self,text,two_lines=False):
        timeline=dict(rate=24000,segments=[dict(text=text,start_sample=0,end_sample=24000,voice_samples=24000)])
        srt=write_srt(timeline,self.run/'caption.srt'); self.assertIn(text.split()[0],srt.read_text())
        if two_lines:self.assertEqual(len(srt.read_text().strip().splitlines()[2:]),2)
        master=self.run/'master.mp4'
        checked(['ffmpeg','-y','-v','error','-f','lavfi','-i','color=white:s=1920x1080:r=30','-t','1','-c:v','libx264','-pix_fmt','yuv420p',master])
        font=S/'assets/fonts/Pretendard-Bold.ttf'
        final=burn_subtitles(master,srt,self.run/'최종.mp4',font)
        raw=checked(['ffmpeg','-v','error','-i',final,'-frames:v','1','-f','image2',self.run/'frame.png'])
        from PIL import Image,ImageChops
        image=Image.open(self.run/'frame.png').convert('RGB'); bbox=ImageChops.difference(image,Image.new('RGB',image.size,'white')).getbbox()
        self.assertIsNotNone(bbox); self.assertGreaterEqual(bbox[1],900)
    def test_two_line_background_is_one_uniform_rectangle(self):
        # Unequal lines must share one box; stacked per-line boxes create steps and overlaps.
        from PIL import Image
        from solution_video.media import ffmpeg
        master=self.run/'white.mp4'
        checked([ffmpeg(),'-y','-v','error','-f','lavfi','-i','color=white:s=1920x1080:r=30','-t','0.1','-c:v','libx264','-pix_fmt','yuv420p',master])
        srt=self.run/'two.srt';srt.write_text('1\n00:00:00,000 --> 00:00:00,100\nQ₁과 Q₃의 출력 저항까지 같은\n두 노드에 연결되므로 병렬입니다.\n')
        final=burn_subtitles(master,srt,self.run/'two.mp4',S/'assets/fonts/Pretendard-Bold.ttf')
        png=self.run/'two.png';checked([ffmpeg(),'-v','error','-i',final,'-frames:v','1',png])
        mask=Image.open(png).convert('L').crop((0,900,1920,1080)).point(lambda p:255 if p<200 else 0)
        box=mask.getbbox();self.assertIsNotNone(box)
        bounds=[mask.crop((0,y,1920,y+1)).getbbox() for y in range(box[1]+5,box[3]-5)]
        self.assertTrue(all(bounds),'one shared background has no horizontal gap')
        self.assertLessEqual(max(b[0] for b in bounds)-min(b[0] for b in bounds),4,'left box edge must be straight')
        self.assertLessEqual(max(b[2] for b in bounds)-min(b[2] for b in bounds),4,'right box edge must be straight')
        # Background beside the shorter line must not double-darken where line boxes overlap.
        gray=Image.open(png).convert('L');x=box[0]+8
        shades=[gray.getpixel((x,y+900)) for y in range(box[1]+5,box[3]-5)]
        self.assertLessEqual(max(shades)-min(shades),5,'background opacity is uniform between lines')
    def test_padded_segments_place_pcm_at_shifted_start(self):
        from solution_video.media import render_master
        from solution_video.util import file_hash
        from unittest.mock import patch
        from test_annotations import teaching_fixture,make_teaching_plan
        from solution_video.teaching import build_teaching_timeline
        from solution_video.review_adapter import default_config
        _,_,m,l=teaching_fixture();audio=[]
        for index,seg in enumerate(m['segments']):
            a=make_audio(seg['id'],800,self.run)
            with wave.open(str(self.run/a['path']),'wb') as f:f.setparams((1,2,24000,0,'NONE',''));f.writeframes((index+1).to_bytes(2,'little')*800)
            a['sha256']=file_hash(self.run/a['path']);audio.append(a)
        t=build_teaching_timeline(m,l,audio,default_config(),None,make_teaching_plan())
        entry=self.run/'cli.js';entry.write_text('');html=self.run/'composition/index.html';html.parent.mkdir();html.write_text('')
        def command(args,**kwargs):
            Path(args[args.index('--output')+1]).write_bytes(b'video');return __import__('types').SimpleNamespace(returncode=0,stdout='',stderr='')
        def checked(args,**kwargs):(self.run/'renders/master.pending.mp4').write_bytes(b'video')
        with patch('solution_video.media.source_checks'),patch('solution_video.media.command',side_effect=command),patch('solution_video.media.probe',return_value={'streams':[{'codec_type':'video','nb_frames':t['total_frames']}]}),patch('solution_video.media.checked',side_effect=checked),patch('solution_video.media.ffmpeg',return_value='ffmpeg'):
            render_master([dict(entry='composition/index.html',key='solution',first_frame=0,last_frame=t['total_frames'])],t,audio,self.run,entry)
        with wave.open(str(self.run/'renders/narration.wav'),'rb') as f:raw=f.readframes(f.getnframes())
        self.assertEqual(raw[800*2:1600*2],b'\x02\x00'*800)
        self.assertEqual(raw[1600*2:64800*2],b'\x00\x00'*(64800-1600))
        self.assertEqual(raw[64800*2:65600*2],b'\x03\x00'*800)
