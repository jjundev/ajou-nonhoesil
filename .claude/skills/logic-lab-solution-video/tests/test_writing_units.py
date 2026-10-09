from fixtures import *
import copy
import importlib
from solution_video.contracts import InputError


def unit(uid, band, glyphs=(), shapes=(), line='line1', chunk='chunk1', column='col1', camera_break=False):
    return dict(id=uid, line_id=line, chunk_id=chunk, column_id=column, band=band,
                glyph_ids=list(glyphs), shape_ids=list(shapes), camera_break_before=camera_break)


def spatial_layers():
    return dict(glyphs=[dict(id='right',text='x',bbox=[20,10,30,20],paint_order=0),
                        dict(id='left',text='a',bbox=[0,10,10,20],paint_order=1),
                        dict(id='sub',text='1',bbox=[5,21,9,25],paint_order=2)],
                shapes=[dict(id='bar',bbox=[0,26,30,27],paint_order=3)],
                map=dict(steps=[dict(id='step',glyph_ids=['right','left','sub'],shape_ids=['bar'],
                         writing_units=[unit('u1',[0,10],['left','sub'],['bar']),
                                        unit('u2',[10,30],['right'],['bar'])])]))


class WritingUnitTests(Sandbox):
    def compile(self, layers):
        try: compiler=importlib.import_module('solution_video.writing_units').compile_writing_units
        except ModuleNotFoundError: self.fail('spatial writing compiler is missing')
        return compiler(layers)

    def test_subscripts_do_not_change_source_order(self):
        layers=spatial_layers(); original=copy.deepcopy(layers)
        units=self.compile(layers)
        self.assertEqual(layers,original)
        self.assertEqual([p['id'] for p in units[0]['pieces']],['left','bar','sub'])
        self.assertEqual(units[0]['bbox'],[0,10,10,27])
        self.assertEqual(units[1]['step_id'],'step')

    def test_fraction_and_radical_pieces_cover_original(self):
        units=self.compile(spatial_layers())
        clips=[p['clip_bbox'] for u in units for p in u['pieces'] if p['id']=='bar']
        self.assertEqual(clips,[[0,26,10,27],[10,26,30,27]])
        self.assertEqual(sum((b[2]-b[0])*(b[3]-b[1]) for b in clips),30)

    def test_columns_and_invalid_units(self):
        base=spatial_layers()
        mutations=[lambda us:us[1].update(band=[5,30]),lambda us:us[1].update(id='u1'),
                   lambda us:us[1].update(glyph_ids=['unknown']),lambda us:us[0].update(glyph_ids=['left']),
                   lambda us:us[1].update(shape_ids=[]),lambda us:us[1].update(column_id='col2'),
                   lambda us:us[1].update(chunk_id='chunk2'),lambda us:us[1].update(band=[10,float('nan')])]
        for mutate in mutations:
            layers=copy.deepcopy(base); mutate(layers['map']['steps'][0]['writing_units'])
            with self.subTest(layers=layers),self.assertRaises(InputError):self.compile(layers)
        layers=copy.deepcopy(base)
        layers['map']['steps'][0]['writing_units'][1].update(line_id='line2',column_id='col2')
        self.assertEqual(len(self.compile(layers)),2)

    def test_missing_units_requires_authoring(self):
        layers=spatial_layers(); del layers['map']['steps'][0]['writing_units']
        with self.assertRaisesRegex(InputError,'writing_units.*author'):self.compile(layers)
    def test_zero_height_native_fraction_line_splits_by_length(self):
        l=spatial_layers();l['shapes'][0]['bbox']=[0,26,30,26]
        clips=[p['clip_bbox'] for u in self.compile(l) for p in u['pieces'] if p['id']=='bar']
        self.assertEqual(clips,[[0,26,10,26],[10,26,30,26]])
    def test_reopening_chunk_requires_new_chunk_identity(self):
        l=spatial_layers();us=l['map']['steps'][0]['writing_units']
        us[1].update(chunk_id='chunk2',camera_break_before=True)
        l['glyphs'].append(dict(id='last',text='z',bbox=[40,10,50,20],paint_order=5));l['map']['steps'][0]['glyph_ids'].append('last')
        us.append(unit('u3',[40,50],['last'],chunk='chunk1',camera_break=True))
        with self.assertRaisesRegex(InputError,'chunk'):self.compile(l)
