from fixtures import *
import os
class LabAcceptanceTests(Sandbox):
    """Opt-in: inspects a real Aoede batch made by the skill (실험05 기출3·기출4)."""
    def batch(self):
        target=os.environ.get('LOGIC_LAB_ACCEPTANCE_BATCH')
        if not target: self.skipTest('set LOGIC_LAB_ACCEPTANCE_BATCH to a published 실험05 batch')
        return Path(target)
    def test_live_batch_complete(self):
        batch=self.batch(); data=json.loads((batch/'batch.json').read_text(encoding='utf-8'))
        items={i['id']:i for i in data['items']}
        self.assertEqual(set(items),{'q-prio-exam','q-dec2x4-design'})
        for item in items.values():
            report=json.loads((batch/item['run']/'verification/report.json').read_text(encoding='utf-8'))
            self.assertTrue(report['complete'],item['id']); self.assertEqual(report['live_audio'],'verified')
        catalog=json.loads((batch/'catalog.json').read_text(encoding='utf-8')); self.assertTrue(catalog['complete'])
        root=batch.parents[2]
        for entry in catalog['files']:
            self.assertEqual(entry['sha256'],hashlib.sha256((root/entry['path']).read_bytes()).hexdigest())
        self.assertEqual(sorted(e['path'][:3] for e in catalog['files']),['기출3','기출4'])
    def test_figure_problem_uses_figure_unit(self):
        batch=self.batch(); data=json.loads((batch/'batch.json').read_text(encoding='utf-8'))
        run=batch/next(i['run'] for i in data['items'] if i['id']=='q-dec2x4-design')
        layers=json.loads((run/'layers/layers.json').read_text(encoding='utf-8'))
        self.assertTrue(any(s['kind']=='figure' for s in layers['shapes']))
