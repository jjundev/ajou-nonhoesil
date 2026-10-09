from fixtures import *
import json,hashlib,re
class ForkTests(Sandbox):
    def test_no_sibling_skill_references(self):
        bad=re.compile(r'ec2-review-video|_ec2_review_video_lib|EC2_[A-Z]')
        hits=[str(p.relative_to(S)) for p in S.rglob('*') if p.is_file() and p.suffix in {'.py','.js','.mjs','.cjs','.json'}
              and '__pycache__' not in p.parts and p.name not in {'upstream.json','test_fork.py'} and bad.search(p.read_text(encoding='utf-8'))]
        self.assertEqual(hits,[])
    def test_upstream_manifest_accounts_for_every_file(self):
        u=json.loads((S/'upstream.json').read_text(encoding='utf-8'))
        self.assertEqual(u['source_commit'],'af86ffbc1004ca1e1f08c0c9125f3dc8272a8409')
        files={p.relative_to(S).as_posix() for p in S.rglob('*') if p.is_file() and '__pycache__' not in p.parts}-{'upstream.json'}
        self.assertEqual(files-set(u['files'])-set(u['local_changes']),set())
        for rel,meta in u['files'].items():
            if rel not in u['local_changes']:
                self.assertEqual(hashlib.sha256((S/rel).read_bytes()).hexdigest(),meta['sha256'],rel)
    def test_vendored_runtime_present(self):
        for rel in ['scripts/tts_lib/vertex_tts.py','assets/fonts/Pretendard-Bold.ttf','assets/runtime/gsap.min.js']:
            self.assertTrue((S/rel).is_file(),rel)
