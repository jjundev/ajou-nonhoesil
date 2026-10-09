from fixtures import *
import unittest
from solution_video.subtitles import caption_text,split_caption,write_srt
from solution_video.contracts import InputError

class CaptionNotationTests(unittest.TestCase):
    def test_rejects_spoken_math_with_segment_context(self):
        for text in ['I₀ 더하기 ΔI입니다.','I₀ 빼기 ΔI입니다.',
                     'R_L 곱하기 ΔI입니다.','I₀ 나누기 이입니다.',
                     '마이너스 I₀입니다.','계수는 이분의 삼입니다.',
                     '변화량은 일 점 오 ΔI입니다.']:
            with self.subTest(text=text),self.assertRaisesRegex(InputError,'write_example'):
                caption_text(dict(id='write_example',text='음성 원고',caption_text=text))

    def test_preserves_prose_and_tts_text(self):
        spoken='이 델타 아이 알 엘입니다.'
        seg=dict(id='write_example',text=spoken,caption_text='이 두 항을 비교합니다. 값은 2ΔI R_L입니다.')
        self.assertEqual(caption_text(seg),seg['caption_text'])
        self.assertEqual(seg['text'],spoken)
        caption_text(dict(id='reason',caption_text='이 회로의 이득은 같은 방향으로 더해집니다. 두 소자를 봅니다.'))

    def test_symbols_fractions_and_subscripts_survive_srt(self):
        import tempfile
        from pathlib import Path
        text='V_out = R_L × ((I₀ + ΔI)/2 − (I₀ − ΔI)). 계수는 3/2입니다.'
        seg=dict(id='write_example',text='음성은 기호를 읽습니다.',caption_text=text,
                 start_sample=0,end_sample=240000,voice_samples=240000)
        with tempfile.TemporaryDirectory() as td:
            p=write_srt(dict(rate=24000,segments=[seg]),Path(td)/'test.srt')
            s=p.read_text();self.assertIn('I₀',s);self.assertIn('3/2',s);self.assertIn('−',s)
        self.assertEqual(' '.join(c.replace('\n',' ') for c in split_caption(text)),text)

    def test_legacy_voice_fallback_still_works(self):
        self.assertEqual(caption_text(dict(text='아이 영 더하기 델타 아이입니다.')),'아이 영 더하기 델타 아이입니다.')

    def test_ambiguous_numbers_warn_without_blocking_or_rewriting(self):
        from solution_video import subtitles
        inspect=getattr(subtitles,'inspect_caption_notation',None)
        self.assertTrue(callable(inspect),'structured notation inspection required')
        for text in ['이 ΔI입니다.','이 R_L을 지납니다.','값은 이입니다.',
                     '(I₀ + ΔI)를 이로 나눈 값입니다.']:
            with self.subTest(text=text):
                issues=inspect(text,'write_example')
                self.assertTrue(issues)
                self.assertTrue(all(i['severity']=='warning' for i in issues))
                self.assertEqual(caption_text(dict(id='write_example',caption_text=text)),text)
                for i in issues:
                    self.assertEqual(i['segment_id'],'write_example')
                    self.assertEqual(text[slice(*i['span'])],i['matched_text'])
                    self.assertTrue(i['reason']);self.assertTrue(i['code'])

    def test_particle_and_demonstrative_prose_have_no_issues(self):
        from solution_video import subtitles
        inspect=getattr(subtitles,'inspect_caption_notation',None)
        self.assertTrue(callable(inspect))
        for text in ['I₀이 증가합니다.','이 두 항을 봅니다.','이 회로의 이득입니다.',
                     '이때 전압이 변합니다.','2ΔI입니다.']:
            self.assertEqual(inspect(text,'s'),[])

    def test_collects_all_issues_with_unique_spans(self):
        from solution_video import subtitles
        inspect=getattr(subtitles,'inspect_caption_notation',None)
        self.assertTrue(callable(inspect))
        text='이 ΔI에 더하기 이분의 삼을 적용합니다. 값은 이입니다.'
        issues=inspect(text,'s')
        self.assertEqual([i['severity'] for i in issues],['warning','error','error','warning'])
        self.assertEqual(len({tuple(i['span']) for i in issues}),4)
