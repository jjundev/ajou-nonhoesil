import base64
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import urllib.error
import wave

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/transcribe.py'


def response(text='입력은 일입니다.', start='0.1s', end='0.3s'):
    return {'candidates': [{'finishReason': 'STOP', 'content': {'parts': [
        {'text': text, 'audioTranscription': {'text': text, 'words': [
            {'word': text, 'startOffset': start, 'endOffset': end}]}}]}}],
        'usageMetadata': {'totalTokenCount': 10}}


class TranscribeTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.audio = self.root / '한글 $`음성`.wav'
        with wave.open(str(self.audio), 'wb') as f:
            f.setparams((1, 2, 16000, 0, 'NONE', 'not compressed'))
            f.writeframes(b'\x01\x00' * 16000 * 3)
        self.assertTrue(SCRIPT.is_file(), 'logic-lab-stt 실행기가 필요합니다')
        spec = importlib.util.spec_from_file_location('lab_stt', SCRIPT)
        self.stt = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.stt)

    def run_stt(self, transport, **kwargs):
        return self.stt.transcribe(self.audio, self.root / 'output',
                                   transport=transport, **kwargs)

    def test_chunk_merge_and_cache_reuse(self):
        calls = []
        def transport(payload):
            calls.append(payload)
            return response()
        result = self.run_stt(transport, timestamps=True, chunk_seconds=1)
        self.assertEqual(result['status'], 'complete')
        data = json.loads(Path(result['json']).read_text())
        self.assertEqual([round(w['start_s'], 2) for w in data['words']], [.1, 1.1, 2.1])
        self.assertIn('00:02.100', Path(result['md']).read_text())
        self.assertEqual(len(calls), 3)
        self.run_stt(transport, timestamps=True, chunk_seconds=1)
        self.assertEqual(len(calls), 3)
        config = calls[0]['generationConfig']['audioTranscriptionConfig']
        self.assertEqual(config, {'mode': 'VERBATIM', 'languageCodes': ['ko-KR'], 'wordTimestamp': True})
        raw = base64.b64decode(calls[0]['contents'][0]['parts'][0]['inlineData']['data'])
        with wave.open(io.BytesIO(raw)) as f:
            self.assertEqual((f.getframerate(), f.getnchannels()), (16000, 1))

    def test_failed_chunk_resume_without_partial_md(self):
        calls = []
        def fail_second(payload):
            calls.append(payload)
            if len(calls) == 2:
                return {'candidates': [{'finishReason': 'MAX_TOKENS'}]}
            return response()
        with self.assertRaises(self.stt.SttError):
            self.run_stt(fail_second, timestamps=True, chunk_seconds=1)
        self.assertFalse(list((self.root / 'output').rglob('transcript.md')))
        states = list((self.root / 'output').rglob('state.json'))
        self.assertEqual(json.loads(states[0].read_text())['status'], 'failed')
        resumed = []
        self.run_stt(lambda p: resumed.append(p) or response(), timestamps=True, chunk_seconds=1)
        self.assertEqual(len(resumed), 2)

    def test_corrupt_completed_output_is_not_overwritten(self):
        result = self.run_stt(lambda p: response())
        md = Path(result['md'])
        md.write_text('사용자 수정')
        with self.assertRaises(self.stt.SttError):
            self.run_stt(lambda p: self.fail('corrupt cache must not call API'))
        self.assertEqual(md.read_text(), '사용자 수정')

    def test_interrupted_markdown_publish_can_resume(self):
        with patch.object(self.stt.os, 'link', side_effect=OSError('disk failure')):
            with self.assertRaises(self.stt.SttError):
                self.run_stt(lambda p: response())
        self.assertFalse(list((self.root / 'output').rglob('transcript.md')))
        result = self.run_stt(lambda p: self.fail('reuse complete cached chunk'))
        self.assertEqual(result['status'], 'complete')

    def test_changed_options_use_separate_run(self):
        a = self.run_stt(lambda p: response())
        b = self.run_stt(lambda p: response(), timestamps=True)
        self.assertNotEqual(a['md'], b['md'])

    def test_invalid_timing_or_empty_response_rejected(self):
        for value in (response(start='NaNs'), response(end='99s'),
                      {'candidates': []}, response(text='')):
            with self.subTest(value=value), self.assertRaises(self.stt.SttError):
                self.run_stt(lambda p: value, timestamps=True)

    def test_audio_video_start_offset_preserved(self):
        video = self.root / 'offset.mp4'
        subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i',
                        'color=s=64x64:r=10:d=4', '-itsoffset', '1', '-i', str(self.audio),
                        '-c:v', 'libx264', '-c:a', 'pcm_s16le', '-f', 'mov', str(video)], check=True)
        result = self.stt.transcribe(video, self.root / 'video-output',
                                     transport=lambda p: response(), timestamps=True)
        data = json.loads(Path(result['json']).read_text())
        self.assertAlmostEqual(data['words'][0]['start_s'], 1.1, places=2)
        self.assertAlmostEqual(data['audio_offset_s'], 1, places=2)

    def test_no_audio_does_not_require_credentials(self):
        video = self.root / 'silent.mp4'
        subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i',
                        'color=s=64x64:r=10:d=1', '-c:v', 'libx264', str(video)], check=True)
        result = self.stt.transcribe(video, self.root / 'silent-output',
                                     transport=lambda p: self.fail('no audio'))
        self.assertEqual(result['status'], 'no_audio')
        self.assertNotIn('md', result)

    def test_internal_audio_pts_gap_is_preserved(self):
        gap = self.root / 'gap.mkv'
        # Remove packets from [1,2), retaining their original positions in the container.
        subprocess.run(['ffmpeg', '-v', 'error', '-i', str(self.audio), '-af',
                        "aselect='not(between(t,1,2))'", '-c:a', 'pcm_s16le', str(gap)], check=True)
        durations = []
        def transport(payload):
            raw = base64.b64decode(payload['contents'][0]['parts'][0]['inlineData']['data'])
            with wave.open(io.BytesIO(raw)) as f:
                durations.append(f.getnframes() / f.getframerate())
            return response(start='2.5s', end='2.8s')
        result = self.stt.transcribe(gap, self.root / 'gap-output',
                                     transport=transport, timestamps=True)
        self.assertAlmostEqual(durations[0], 3, delta=.1)
        data = json.loads(Path(result['json']).read_text())
        self.assertEqual(data['words'][0]['start_s'], 2.5)

    def test_key_loading_and_transport_error_redaction(self):
        env = self.root / '.env'
        env.write_text('GOOGLE_API_KEY=file-secret\n')
        with patch.dict(os.environ, {'GOOGLE_API_KEY': 'env-secret'}):
            self.assertEqual(self.stt.load_key(env), 'env-secret')
        sleeps = []
        error = urllib.error.HTTPError('https://example.test', 429, 'secret', {}, io.BytesIO(b'file-secret'))
        with patch.object(self.stt.urllib.request, 'urlopen', side_effect=error) as urlopen:
            with self.assertRaises(self.stt.SttError) as caught:
                self.stt.make_transport('file-secret', sleep=sleeps.append)({})
        self.assertEqual(urlopen.call_count, 3)
        self.assertNotIn('secret', str(caught.exception))
        self.assertEqual(len(sleeps), 2)
        with patch.object(self.stt.urllib.request, 'urlopen', side_effect=
                          urllib.error.HTTPError('url', 403, 'file-secret', {}, None)) as urlopen:
            with self.assertRaises(self.stt.SttError):
                self.stt.make_transport('file-secret')({})
        self.assertEqual(urlopen.call_count, 1)

    def test_unexpected_exception_not_persisted(self):
        def failing(payload):
            raise RuntimeError('credential-secret')
        with self.assertRaises(self.stt.SttError) as caught:
            self.run_stt(failing)
        self.assertNotIn('credential-secret', str(caught.exception))
        for path in (self.root / 'output').rglob('*.json'):
            self.assertNotIn('credential-secret', path.read_text())


if __name__ == '__main__':
    unittest.main()
