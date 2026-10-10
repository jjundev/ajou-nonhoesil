from fixtures import *
import copy, shutil
from solution_video.contracts import InputError
from solution_video.review_adapter import default_config

class WritingTests(Sandbox):
    def test_new_defaults_and_legacy_fallback(self):
        from solution_video.writing import default_writing, load_writing
        self.assertEqual(default_writing()['chars_per_second'],7.5)
        self.assertEqual(default_writing()['pencil_length_px'],160)
        self.assertEqual(default_writing('typing')['chars_per_second'],7)
        self.assertEqual(load_writing(self.run,default_config())['mode'],'typing')
        c=default_config();c['chars_per_second']=8
        self.assertEqual(load_writing(self.run,c)['chars_per_second'],8)
    def test_invalid_writing_values(self):
        from solution_video.writing import default_writing, validate_writing
        for k,v in [('mode','other'),('asset_id','../bad'),('chars_per_second',float('nan')),('chars_per_second',float('inf')),('chars_per_second',8),('chars_per_second',0),('pencil_length_px',0),('adjacent_move_frames',True),('lifted_move_frames',0),('tilt_degrees',3),('read_hold_seconds',-1)]:
            with self.subTest(key=k,value=v),self.assertRaises(InputError):
                c=default_writing();c[k]=v;validate_writing(c)
        with self.assertRaises(InputError): validate_writing({'mode':'pencil'})
    def test_pencil_asset_contract(self):
        from solution_video.writing import load_pencil_asset
        from solution_video.util import write
        meta=load_pencil_asset(S/'assets/pencil')
        self.assertEqual(meta['sha256'],'8f09ff6af2689c9cb50bab4382c4d18a46639312ea8d2edf42ad82c774d20269')
        dst=self.run/'asset';shutil.copytree(S/'assets/pencil',dst)
        bad=copy.deepcopy(meta);bad['tip_px']=[-1,5];write(dst/'pencil-yellow-v1.json',bad)
        with self.assertRaises(InputError):load_pencil_asset(dst)
        write(dst/'pencil-yellow-v1.json',meta)
        (dst/meta['file']).write_bytes(b'broken')
        with self.assertRaises(InputError):load_pencil_asset(dst)
        (dst/meta['file']).unlink()
        with self.assertRaises(InputError):load_pencil_asset(dst)
    def test_asset_rejects_false_bounds_and_opaque_png(self):
        from solution_video.writing import load_pencil_asset
        from solution_video.util import write,file_hash
        from PIL import Image
        dst=self.run/'asset';shutil.copytree(S/'assets/pencil',dst);meta=json.loads((dst/'pencil-yellow-v1.json').read_text())
        bad=copy.deepcopy(meta);bad['visible_bounds_px']=[0,0,1254,1254];write(dst/'pencil-yellow-v1.json',bad)
        with self.assertRaises(InputError):load_pencil_asset(dst)
        Image.new('RGBA',(1254,1254),(255,255,255,255)).save(dst/meta['file']);meta['sha256']=file_hash(dst/meta['file']);write(dst/'pencil-yellow-v1.json',meta)
        with self.assertRaises(InputError):load_pencil_asset(dst)
