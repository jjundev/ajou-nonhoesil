from fixtures import *
import importlib
from solution_video.contracts import InputError

class ShapeTimingTests(Sandbox):
    def api(self):
        try:return importlib.import_module('solution_video.shape_timing').allocate_shape_frames
        except ModuleNotFoundError:self.fail('shape budget allocator missing')
    def allocate(self,widths,width=None,height=10,interval=4,kind=None):
        edge=0;units=[]
        for i,w in enumerate(widths):
            units.append(dict(id='u'+str(i),step_id='s',pieces=[dict(kind='shape',id='box',clip_bbox=[edge,0,edge+w,0])]))
            edge+=w
        shape=dict(id='box',bbox=[0,0,edge if width is None else width,0])
        if kind:shape['kind']=kind
        return self.api()(units,dict(shapes=[shape]),'s',height,interval)
    def test_split_invariance(self):
        self.assertEqual(sum(self.allocate([120]).values()),48)
        self.assertEqual(sum(self.allocate([5]*24).values()),48)
    def test_unequal_widths(self):self.assertEqual(list(self.allocate([10,30]).values()),[5,13])
    def test_tie_goes_to_authored_order(self):
        # 18 을 같은 폭 넷으로: 몫 4.5 의 나머지는 저작 순서상 앞 조각부터 받는다.
        self.assertEqual(list(self.allocate([10,10,10,10]).values()),[5,5,4,4])
    def test_minimum_and_overfragmentation(self):
        a=self.allocate([.1,39.9]);self.assertEqual(sum(a.values()),18);self.assertGreaterEqual(min(a.values()),1)
        with self.assertRaisesRegex(InputError,'box.*19.*18'):self.allocate([1]*19)
    def test_vertical_and_zero_height(self):
        self.assertEqual(list(self.allocate([0]).values()),[18])
        self.assertEqual(sum(self.allocate([60,60]).values()),48)
    def test_invalid_height_interval(self):
        for h,i in [(0,4),(float('nan'),4),(10,True),(10,0)]:
            with self.assertRaises(InputError):self.allocate([120],height=h,interval=i)
    def test_identity_scope(self):
        units=[dict(id='u',step_id='other',pieces=[dict(kind='shape',id='box',clip_bbox=[0,0,10,0])])]
        self.assertEqual(self.api()(units,dict(shapes=[]),'s',10,4),{})
    def test_wide_answer_box_is_bounded(self):
        self.assertEqual(sum(self.allocate([900/24]*24,height=7).values()),90)
    def test_figure_is_left_to_figure_wipe(self):
        # 풀이 그림은 그림 단위 wipe(FIGURE_DRAW_FRAMES) 몫이라 도형 예산을 받지 않는다.
        self.assertEqual(self.allocate([300,300],kind='figure'),{})
