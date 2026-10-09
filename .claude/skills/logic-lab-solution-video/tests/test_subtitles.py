from fixtures import *
from test_annotations import make_teaching_plan,teaching_fixture
from solution_video.teaching import build_teaching_timeline
from solution_video.review_adapter import default_config
from solution_video.subtitles import write_srt
class SubtitleTests(Sandbox):
 def caption(self,**fields):
  t={'rate':24000,'segments':[dict(id='s',text='알 오 원',start_sample=24000,end_sample=240000,voice_samples=72000,**fields)]}
  return write_srt(t,self.run/'a.srt').read_text()
 def test_caption_uses_symbols(self):
  s=self.caption(caption_text='r_O1 ∥ r_O3 ∥ R₁')
  self.assertIn('r_O1',s);self.assertNotIn('알 오 원',s)
 def test_legacy_caption_fallback(self):
  self.assertIn('알 오 원',self.caption())
 def test_empty_caption_rejected(self):
  from solution_video.contracts import InputError
  for value in ['', '  ',None,3]:
   with self.subTest(value=value),self.assertRaises(InputError):self.caption(caption_text=value)
 def test_atomic_formula_caption(self):
  from solution_video.subtitles import split_caption
  from solution_video.contracts import InputError
  formula='r_O1∥r_O3∥R₁+g_m1+V_BE+'*2+'r_O1.'
  chunks=split_caption(formula)
  self.assertEqual(len(chunks),1)
  self.assertEqual(chunks[0].replace('\n',''),formula)
  self.assertTrue(all(len(line)<=34 for line in chunks[0].splitlines()))
  self.assertTrue(all(not line.endswith(('r_', 'r_O', 'g_', 'g_m', 'V_', 'V_B')) for line in chunks[0].splitlines()))
  with self.assertRaises(InputError):split_caption('r_'+'O'*40)
 def test_caption_pcm_bounds(self):
  s=self.caption(caption_text='출력 저항은 r_O1과 r_O3과 R₁의 병렬입니다. 같은 교류 접지에 연결됩니다.')
  import re
  times=re.findall(r'(\d\d:\d\d:\d\d,\d{3}) --> (\d\d:\d\d:\d\d,\d{3})',s)
  self.assertEqual(times[0][0],'00:00:01,000');self.assertEqual(times[-1][1],'00:00:04,000')
  self.assertTrue(all('00:00:01,000'<=a<b<='00:00:04,000' for a,b in times))
 def test_post_padding_preserves_measured_caption_duration(self):
  _,_,m,l=teaching_fixture();audio=[make_audio(s['id'],800,self.run) for s in m['segments']]
  t=build_teaching_timeline(m,l,audio,default_config(),None,make_teaching_plan())
  write_srt(t,self.run/'a.srt');s=(self.run/'a.srt').read_text()
  self.assertIn('00:00:00,033 --> 00:00:00,067',s)
  self.assertIn('00:00:02,700 --> 00:00:02,733',s)
 def test_sentence_and_comma_boundaries(self):
  from solution_video.subtitles import split_caption
  self.assertEqual(split_caption('g_m1은 Q₁의 트랜스컨덕턴스이고, r_O1은 Q₁의 출력 저항입니다. 이 두 기호를 구별해 둡니다.'),['g_m1은 Q₁의 트랜스컨덕턴스이고,','r_O1은 Q₁의 출력 저항입니다.','이 두 기호를 구별해 둡니다.'])
 def test_long_sentence_wrap_is_one_cue(self):
  from solution_video.subtitles import split_caption
  text='따라서 Q₁은 이미터가 접지된 공통 이미터 증폭기로 볼 수 있습니다.'
  chunks=split_caption(text)
  self.assertEqual(len(chunks),1);self.assertEqual(len(chunks[0].splitlines()),2)
  self.assertTrue(all(len(line)<=34 for line in chunks[0].splitlines()))
  self.assertEqual(' '.join(chunks[0].split()),text)
 def test_protected_punctuation(self):
  from solution_video.subtitles import caption_units
  self.assertEqual(caption_units('E10.13에서 0.5와 1,000을 봅니다. f(X, P)는 같은 식입니다.'),['E10.13에서 0.5와 1,000을 봅니다.','f(X, P)는 같은 식입니다.'])
  for text in ['(X,P), 다음입니다.','[X,P], 다음입니다.','{X,P}, 다음입니다.','“X,P”, 다음입니다.','‘X,P’, 다음입니다.','"X,P", 다음입니다.']:
   with self.subTest(text=text):self.assertEqual(len(caption_units(text)),2)
  self.assertEqual(caption_units("f'와 module.value를 봅니다."),["f'와 module.value를 봅니다."])
 def test_legacy_terminal_period(self):
  from solution_video.subtitles import split_caption
  text='원본을 확인합니다';self.assertEqual(split_caption(text),['원본을 확인합니다.']);self.assertEqual(text,'원본을 확인합니다')
 def test_quoted_sentence_end(self):
  from solution_video.subtitles import caption_units
  self.assertEqual(caption_units('“같은 값입니다.” 다음입니다.'),['“같은 값입니다.”','다음입니다.'])
 def test_atomic_tokens_and_layout_errors(self):
  from solution_video.subtitles import split_caption,wrap_caption
  from solution_video.contracts import InputError
  for text in ['r_'+'O'*40,('긴 구절을 계속 이어서 설명합니다 '*8)+'.','(X,P입니다.','X]입니다.','맞습니까?','맞습니다!','생략…','$x$입니다.']:
   with self.subTest(text=text),self.assertRaises(InputError):split_caption(text)
  self.assertNotEqual(wrap_caption('X '*16+'끝.' ).splitlines()[-1],'.')
 def test_semantic_srt_contiguous_pcm(self):
  from solution_video.subtitles import _stamp
  first='따라서 Q₁은 이미터가 접지된 공통 이미터 증폭기로 볼 수 있습니다.'
  last='다음 값을 씁니다';s=self.caption(caption_text=first+' '+last)
  entries=s.strip().split('\n\n');self.assertEqual(len(entries),2)
  a=entries[0].splitlines();b=entries[1].splitlines()
  self.assertEqual(len(a[2:]),2)
  cut=_stamp(24000+round(72000*len(first)/(len(first)+len(last))),24000)
  self.assertEqual(a[1],'00:00:01,000 --> '+cut);self.assertEqual(b[1],cut+' --> 00:00:04,000')
  self.assertEqual(b[2],last+'.')
 def test_comma_list_reconstruction(self):
  from solution_video.subtitles import split_caption
  text='Q₁의 r_O1, 부하의 r_O3, 그리고 R₁입니다.'
  chunks=split_caption(text)
  self.assertEqual(chunks,['Q₁의 r_O1,','부하의 r_O3,','그리고 R₁입니다.'])
  self.assertEqual(' '.join(chunks),text)
 def test_unsupported_internal_sentence_endings(self):
  from solution_video.subtitles import split_caption
  from solution_video.contracts import InputError
  for text in ['맞습니까? 다음입니다.','좋습니다! 다음입니다.','생략… 다음입니다.','“맞습니까?” 다음입니다.','"좋습니다!" 다음입니다.','‘생략…’ 다음입니다.']:
   with self.subTest(text=text),self.assertRaises(InputError):split_caption(text)
  self.assertEqual(split_caption('(맞습니까?) 답을 확인합니다.'),['(맞습니까?) 답을 확인합니다.'])
  self.assertEqual(split_caption('“어째서? 설명합니다”를 읽습니다.'),['“어째서? 설명합니다”를 읽습니다.'])
