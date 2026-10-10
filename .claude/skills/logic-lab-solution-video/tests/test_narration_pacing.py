from fixtures import *
import array,importlib
from solution_video.contracts import InputError
from solution_video.util import file_hash,write,read

class NarrationPacingTests(Sandbox):
    def api(self):
        try:return importlib.import_module('solution_video.narration_pacing')
        except ModuleNotFoundError:self.fail('PCM narration gap analysis missing')
    def voice(self,frames,silent=0,rate=24000):
        p=self.run/'w.wav'
        with wave.open(str(p),'wb') as w:
            w.setparams((1,2,rate,0,'NONE',''));w.writeframes(array.array('h',[8000,-8000]*400*(frames-silent)+[0]*800*silent).tobytes())
        return dict(id='w',path='w.wav',sha256=file_hash(p),rate=rate,samples=frames*800)
    def timeline(self,end=90,hold=23):
        return dict(segments=[dict(id='w',kind='write',start_sample=0,end_sample=(end+hold)*800)],writing_spans=[dict(kind='move',step_id='s',start_frame=0,end_frame=1),dict(kind='draw',step_id='s',start_frame=1,end_frame=end)])
    def test_internal_and_tail_silence(self):
        api=self.api()
        for gap,status in [(60,'passed'),(61,'review-required')]:
            a=self.voice(90,silent=gap);r=api.analyze_narration_pacing(self.timeline(),[a],self.run)
            self.assertEqual(r['status'],status);self.assertEqual(r['segments'][0]['longest_gap_frames'],gap)
    def test_read_hold_excluded(self):
        a=self.voice(90);r=self.api().analyze_narration_pacing(self.timeline(90,100),[a],self.run)
        self.assertEqual(r['status'],'passed');self.assertEqual(r['segments'][0]['voiced_ratio'],1)
    def test_short_long_and_missing_voice(self):
        api=self.api();a=self.voice(10);r=api.analyze_narration_pacing(self.timeline(),[a],self.run)
        self.assertEqual(r['segments'][0]['longest_gap_frames'],80)
        a=self.voice(120);self.assertEqual(api.analyze_narration_pacing(self.timeline(),[a],self.run)['segments'][0]['voiced_ratio'],1)
        a['sha256']='stale'
        with self.assertRaises(InputError):api.analyze_narration_pacing(self.timeline(),[a],self.run)
        a=self.voice(90,rate=16000)
        with self.assertRaises(InputError):api.analyze_narration_pacing(self.timeline(),[a],self.run)
    def test_ratio_is_guidance_not_forced_tts(self):
        a=self.voice(90);before=(self.run/'w.wav').read_bytes();r=self.api().analyze_narration_pacing(self.timeline(),[a],self.run)
        self.assertEqual(r['status'],'passed');self.assertTrue(r['segments'][0]['density_guidance'])
        self.assertEqual(before,(self.run/'w.wav').read_bytes())
    def test_pacing_does_not_approve_audio_meaning(self):
        a=self.voice(90);r=self.api().analyze_narration_pacing(self.timeline(),[a],self.run)
        self.assertNotIn('audio_meaning',r);self.assertFalse((self.run/'verification/audio-review.json').exists())
    def test_internal_gap_and_stale_review(self):
        a=self.voice(150,silent=61);p=self.run/'w.wav'
        with wave.open(str(p),'rb') as w:data=w.readframes(w.getnframes())
        # Move tail silence into the middle; keep complete 150-frame PCM.
        pcm=data[:45*1600]+data[89*1600:]+data[45*1600:89*1600]
        with wave.open(str(p),'wb') as w:w.setparams((1,2,24000,0,'NONE',''));w.writeframes(pcm)
        a['sha256']=file_hash(p);api=self.api();r=api.analyze_narration_pacing(self.timeline(150),[a],self.run)
        gap=r['segments'][0]['gaps'][0];self.assertEqual(gap,dict(start_frame=45,end_frame=106))
        write(self.run/'verification/pacing-review.json',dict(input_hash=r['input_hash'],gaps=[dict(segment_id='w',**gap,reason='intentional thinking pause')]))
        self.assertEqual(api.analyze_narration_pacing(self.timeline(150),[a],self.run)['status'],'passed')
        a=self.voice(150,silent=61)
        self.assertEqual(api.analyze_narration_pacing(self.timeline(150),[a],self.run)['status'],'review-required')
    def test_lag_boundary_and_hold(self):
        a=self.voice(90);api=self.api()
        for end,status in [(150,'passed'),(151,'review-required')]:
            r=api.analyze_narration_pacing(self.timeline(end),[a],self.run)
            row=r['segments'][0];self.assertEqual((row['voice_end_frame'],row['writing_end_frame'],row['writing_lag_frames']),(90,end,end-90))
            self.assertEqual(bool(r['unreviewed_writing_lags']),status=='review-required')
        a=self.voice(120);r=api.analyze_narration_pacing(self.timeline(90,110),[a],self.run)
        self.assertEqual((r['segments'][0]['completed_hold_frames'],r['segments'][0]['writing_lag_frames']),(80,0))
    def test_voice_end_rounds_pcm_up_to_frame(self):
        p=self.run/'w.wav'
        with wave.open(str(p),'wb') as w:w.setparams((1,2,24000,0,'NONE',''));w.writeframes(array.array('h',[8000,-8000]*(400*89+1)).tobytes())
        a=dict(id='w',path='w.wav',sha256=file_hash(p),rate=24000,samples=89*800+2)
        self.assertEqual(self.api().analyze_narration_pacing(self.timeline(),[a],self.run)['segments'][0]['voice_end_frame'],90)
    def test_gap_review_cannot_approve_lag(self):
        a=self.voice(90);t=self.timeline(151);api=self.api();r=api.analyze_narration_pacing(t,[a],self.run)
        gap=r['segments'][0]['gaps'][0]
        write(self.run/'verification/pacing-review.json',dict(input_hash=r['input_hash'],gaps=[dict(segment_id='w',**gap,reason='연필이 마저 쓰는 무음')]))
        self.assertEqual(api.analyze_narration_pacing(t,[a],self.run)['status'],'review-required')
        review=read(self.run/'verification/pacing-review.json');review['writing_lags']=[dict(segment_id='w',voice_end_frame=90,writing_end_frame=151,reason='intentional remaining writing')];write(self.run/'verification/pacing-review.json',review)
        self.assertEqual(api.analyze_narration_pacing(t,[a],self.run)['status'],'passed')
        for change in [dict(reason=''),dict(reason='  '),dict(voice_end_frame=89),dict(writing_end_frame=150),dict(segment_id='x')]:
            bad=dict(review);bad['writing_lags']=[dict(review['writing_lags'][0],**change)]
            write(self.run/'verification/pacing-review.json',bad)
            self.assertEqual(api.analyze_narration_pacing(t,[a],self.run)['status'],'review-required')
        review['input_hash']='stale';write(self.run/'verification/pacing-review.json',review)
        self.assertEqual(api.analyze_narration_pacing(t,[a],self.run)['status'],'review-required')
    def test_lag_review_cannot_approve_gap(self):
        a=self.voice(90,silent=61);t=self.timeline();api=self.api();r=api.analyze_narration_pacing(t,[a],self.run)
        self.assertEqual(r['status'],'review-required');self.assertEqual(r['unreviewed_writing_lags'],[])
        write(self.run/'verification/pacing-review.json',dict(input_hash=r['input_hash'],writing_lags=[dict(segment_id='w',voice_end_frame=90,writing_end_frame=90,reason='x')]))
        self.assertEqual(api.analyze_narration_pacing(t,[a],self.run)['status'],'review-required')
    def test_pcm_end_separate_from_energy(self):
        a=self.voice(90,silent=61);r=self.api().analyze_narration_pacing(self.timeline(),[a],self.run)
        self.assertEqual(r['segments'][0]['voice_end_frame'],90);self.assertEqual(r['segments'][0]['writing_lag_frames'],0)
        self.assertEqual(r['segments'][0]['longest_gap_frames'],61)
    def test_old_review_without_writing_lags_still_reads(self):
        # 기출3 처럼 gaps 만 있는 옛 pacing-review.json 은 읽히고, 지연이 없으면 결과도 그대로다.
        a=self.voice(150,silent=61);t=self.timeline(150);api=self.api()
        p=self.run/'w.wav'
        with wave.open(str(p),'rb') as w:data=w.readframes(w.getnframes())
        with wave.open(str(p),'wb') as w:w.setparams((1,2,24000,0,'NONE',''));w.writeframes(data[:45*1600]+data[89*1600:]+data[45*1600:89*1600])
        a['sha256']=file_hash(p);r=api.analyze_narration_pacing(t,[a],self.run);gap=r['segments'][0]['gaps'][0]
        write(self.run/'verification/pacing-review.json',dict(input_hash=r['input_hash'],gaps=[dict(segment_id='w',**gap,reason='생각하는 쉼')]))
        r=api.analyze_narration_pacing(t,[a],self.run)
        self.assertEqual((r['status'],r['unreviewed_writing_lags']),('passed',[]))
