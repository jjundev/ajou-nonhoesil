import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/video_evidence.py'
spec = importlib.util.spec_from_file_location('video_evidence_stt_test', SCRIPT)
ve = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ve)


class TranscriptionIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.base = Path(cls.temp.name)
        cls.clip = cls.base / 'source.mp4'
        cls.silent = cls.base / 'silent.mp4'
        subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'color=s=64x64:r=10:d=1',
                        '-f', 'lavfi', '-i', 'sine=duration=1', '-c:v', 'libx264', '-c:a', 'aac',
                        str(cls.clip)], check=True)
        subprocess.run(['ffmpeg', '-v', 'error', '-i', str(cls.clip), '-an', '-c:v', 'copy',
                        str(cls.silent)], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        temp = tempfile.TemporaryDirectory(dir=self.base)
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.experiment = self.root / '실험06'
        self.experiment.mkdir()

    def inspect(self, sources=None, transcripts=None):
        return ve.inspect_run(self.experiment, '전사시험', sources or [self.clip],
                              transcripts or {}, 'both', self.root / 'delivery')

    def fake_stt(self, source, output_dir, **kwargs):
        self.assertTrue(kwargs['timestamps'])
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        md, meta = output_dir / 'transcript.md', output_dir / 'transcript.json'
        md.write_text('00:00.100\n출력은 일입니다.\n')
        meta.write_text(json.dumps({'status': 'complete', 'source_sha256': ve.sha256(source)}))
        return {'status': 'complete', 'md': str(md), 'json': str(meta),
                'md_sha256': ve.sha256(md), 'json_sha256': ve.sha256(meta),
                'source_sha256': ve.sha256(source), 'model': 'gemini-3.5-transcribe'}

    def test_manual_transcript_precedes_auto_and_review_stays_pending(self):
        manual = self.root / '수동.md'
        manual.write_text('직접 제공한 발언')
        manifest = self.inspect([self.clip, self.silent], {'p1': manual})
        with patch.object(ve, 'load_transcriber', return_value=lambda *a, **k: self.fail('no call')):
            result = ve.transcribe_run(manifest)
        m = ve.load(manifest)
        self.assertEqual(m['sources']['transcript_p1']['path'], str(manual.resolve()))
        self.assertEqual(m['transcription']['p2']['status'], 'no_audio')
        self.assertEqual(m['review']['audio'], 'pending')
        self.assertEqual(result['failed'], 0)

    def test_auto_registers_both_outputs_and_reuses(self):
        manifest = self.inspect()
        ve.transcribe_run(manifest, transcriber=self.fake_stt)
        m = ve.load(manifest)
        self.assertEqual(m['sources']['transcript_p1']['origin'], 'gemini_api')
        self.assertIn('transcript_metadata_p1', m['sources'])
        self.assertTrue(ve.inputs_unchanged(m))
        self.assertEqual(m['review']['audio'], 'pending')
        ve.transcribe_run(manifest, transcriber=lambda *a, **k: self.fail('already present'))
        Path(m['sources']['transcript_metadata_p1']['path']).write_text('changed')
        with self.assertRaises(ValueError):
            ve.transcribe_run(manifest, transcriber=self.fake_stt)

    def test_failure_is_explicit_and_resume_removes_unknown(self):
        manifest = self.inspect()
        def failure(*args, **kwargs):
            raise RuntimeError('secret-must-not-be-saved')
        result = ve.transcribe_run(manifest, transcriber=failure)
        self.assertEqual(result['failed'], 1)
        m = ve.load(manifest)
        self.assertEqual(m['transcription']['p1']['status'], 'failed')
        self.assertTrue(m['unknowns'])
        self.assertNotIn('transcript_p1', m['sources'])
        self.assertNotIn('secret-must-not-be-saved', manifest.read_text())
        self.assertEqual(ve.transcribe_run(manifest, transcriber=self.fake_stt)['failed'], 0)
        self.assertFalse(ve.load(manifest)['unknowns'])

    def test_source_changed_is_rejected_before_api(self):
        manifest = self.inspect()
        m = ve.load(manifest)
        m['sources']['p1']['sha256_before'] = 'changed'
        ve.save(manifest, m)
        with self.assertRaises(ValueError):
            ve.transcribe_run(manifest, transcriber=lambda *a, **k: self.fail('no call'))

    def test_inspect_cli_auto_and_explicit_skip(self):
        common = ['video_evidence.py', 'inspect', '--experiment-dir', str(self.experiment),
                  '--label', 'cli', '--source', str(self.clip), '--deliver-dir', str(self.root / 'd')]
        with patch('sys.argv', common), patch.object(ve, 'transcribe_run', return_value={'failed': 0}) as auto:
            self.assertEqual(ve.main(), 0)
        self.assertEqual(auto.call_count, 1)
        with patch('sys.argv', common + ['--no-transcribe']), patch.object(ve, 'transcribe_run') as auto:
            self.assertEqual(ve.main(), 0)
        self.assertEqual(auto.call_count, 0)


if __name__ == '__main__':
    unittest.main()
