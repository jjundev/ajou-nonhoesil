from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import json, hashlib
root=Path(__file__).resolve().parent
fresh=root.parent/'fresh'
data=[{'page':1,'auto':str(next(fresh.glob('*4x1MUX.png'))),'manual':'/Users/hyunjun_macbook_pro/Downloads/Screenshot_20261001_154344_Samsung Notes.jpg','auto_board':[190.5,416.5,1592,2489],'manual_board':[83.5,189.5,692,1087.5],'ink_margins':[37,32,45,34]}, {'page':2,'auto':str(next(fresh.glob('*1x4DMUX.png'))),'manual':'/Users/hyunjun_macbook_pro/Downloads/Screenshot_20261001_154402_Samsung Notes.jpg','auto_board':[123.5,336.5,1525,2409],'manual_board':[56,152.5,628,998],'ink_margins':[33,31,40,34]}]
font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',24)
for d in data:
 imgs={k:Image.open(d[k]).convert('RGB') for k in ['manual','auto']}
 # independent x/y scaling, mapping all 4 board corners onto same rectangle
 BW=850; BH=1257; ox=180; oy=320; pw=1150; ph=1640
 canvas=Image.new('RGB',(pw*2+30,ph+75),'#e8ecf0'); draw=ImageDraw.Draw(canvas)
 d['measurements']={}
 for i,k in enumerate(['manual','auto']):
  im=imgs[k]; x0,y0,x1,y1=d[k+'_board']; bw=x1-x0; bh=y1-y0
  sx=BW/bw; sy=BH/bh
  coeff=(1/sx,0,x0-ox/sx,0,1/sy,y0-oy/sy)
  aligned=im.transform((pw,ph),Image.Transform.AFFINE,coeff,Image.Resampling.BICUBIC,fillcolor='#d9e0e7')
  ad=ImageDraw.Draw(aligned)
  boundary=[ox-x0*sx,oy-y0*sy,ox+(im.width-x0)*sx,oy+(im.height-y0)*sy]
  ad.rectangle(boundary,outline='#2864c5',width=2)
  for x,y in [(ox,oy),(ox+BW,oy),(ox,oy+BH),(ox+BW,oy+BH)]:
   ad.line((x-8,y,x+8,y),fill='#04a49d',width=2); ad.line((x,y-8,x,y+8),fill='#04a49d',width=2)
  canvas.paste(aligned,(i*(pw+30),75))
  draw.text((i*(pw+30)+20,15),f'Page {d["page"]} | {k.upper()} | board aligned',font=font,fill='#172536')
  d['measurements'][k]={'size':im.size,'board_width_px':bw,'board_height_px':bh,'corners':[[x0,y0],[x1,y0],[x0,y1],[x1,y1]],'boundary_extension_percent_board_width':[100*x0/bw,100*y0/bw,100*(im.width-x1)/bw,100*(im.height-y1)/bw],'scale_xy':[sx,sy]}
 d['boundary_delta_auto_minus_manual_percent']=[a-m for a,m in zip(d['measurements']['auto']['boundary_extension_percent_board_width'],d['measurements']['manual']['boundary_extension_percent_board_width'])]
 d['visible_ink_margin_percent']=[100*v/d['measurements']['auto']['board_width_px'] for v in d['ink_margins']]
 canvas.save(root/f'comparison-p{d["page"]}.png')
(root/'alignment-measurements.json').write_text(json.dumps(data,indent=2,ensure_ascii=False))
print(json.dumps([{k:v for k,v in d.items() if k in ['page','boundary_delta_auto_minus_manual_percent','visible_ink_margin_percent']} for d in data],indent=2))
for v in json.loads((fresh/'final-hashes.json').read_text()):
 assert hashlib.sha256((fresh/v['file']).read_bytes()).hexdigest()==v['sha256']
print('Input hashes remain unchanged')
