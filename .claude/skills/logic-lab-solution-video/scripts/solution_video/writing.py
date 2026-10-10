"""Writing settings are independent of voice configuration and billing."""
import math
from pathlib import Path
from .contracts import InputError
from .util import S, read, file_hash

def default_writing(mode='pencil'):
    value=read(S/'assets/writing-defaults.json');value['mode']=mode
    if mode=='typing':value['chars_per_second']=7
    validate_writing(value);return value

def validate_writing(value):
    if not isinstance(value,dict):raise InputError('writing settings must be an object')
    keys={'schema_version','mode','chars_per_second','pencil_length_px','adjacent_move_frames','lifted_move_frames','tilt_degrees','read_hold_seconds','asset_id'}
    if set(value)!=keys:raise InputError('writing settings keys mismatch')
    if type(value['schema_version']) is not int or value['schema_version']!=1:raise InputError('unknown writing schema')
    if value['mode'] not in ('pencil','typing') or value['asset_id']!='pencil-yellow-v1':raise InputError('unknown writing mode/asset')
    for key,low,high,strict in [('chars_per_second',0,7.5 if value['mode']=='pencil' else 7,True),('pencil_length_px',0,float('inf'),True),('tilt_degrees',0,2,False),('read_hold_seconds',0,float('inf'),False)]:
        n=value[key]
        if type(n) not in (float,int) or not math.isfinite(n) or n>high or (n<=low if strict else n<low):raise InputError('invalid writing '+key)
    for key in ('adjacent_move_frames','lifted_move_frames'):
        if type(value[key]) is not int or value[key]<1:raise InputError('invalid writing '+key)

def timing_settings(value):
    """Only these settings change measured writing slots and completion events."""
    return {key:value.get(key) for key in ('mode','chars_per_second','adjacent_move_frames','lifted_move_frames','read_hold_seconds')}

def load_writing(run,config):
    path=Path(run)/'source/writing.json'
    if not path.exists():
        value=default_writing('typing');value.update(chars_per_second=config['chars_per_second'],read_hold_seconds=config['read_hold_seconds']);return value
    try:value=read(path)
    except (ValueError,OSError) as e:raise InputError('invalid writing file') from e
    validate_writing(value);return value

def load_pencil_asset(asset_dir):
    from PIL import Image
    root=Path(asset_dir)
    try:
        meta=read(root/'pencil-yellow-v1.json')
        if meta['file']!='pencil-yellow-v1.png':raise ValueError('file')
        path=root/meta['file']
        with Image.open(path) as im:
            if im.format!='PNG' or im.mode!='RGBA' or im.size!=(meta['width'],meta['height']):raise ValueError('format/size')
            im.load()
            if im.getchannel('A').getextrema()!=(0,255):raise ValueError('transparency')
            if list(im.getchannel('A').getbbox())!=meta['visible_bounds_px']:raise ValueError('visible bounds')
        if file_hash(path)!=meta['sha256']:raise ValueError('hash')
        for key in ('tip_px','end_px'):
            pt=meta[key]
            if not isinstance(pt,list) or len(pt)!=2 or any(type(n) not in (int,float) or not math.isfinite(n) for n in pt) or not (0<=pt[0]<meta['width'] and 0<=pt[1]<meta['height']):raise ValueError(key)
        if math.dist(meta['tip_px'],meta['end_px'])<1:raise ValueError('endpoint length')
    except (OSError,ValueError,KeyError,TypeError) as e:raise InputError('invalid pencil asset: '+str(e)) from e
    return meta

def representative_height(glyphs):
    heights=sorted(g['bbox'][3]-g['bbox'][1] for g in glyphs if not g['text'].isspace() and g['bbox'][3]-g['bbox'][1]>=2)
    if not heights:raise InputError('writing step has no measurable letter')
    return heights[int((len(heights)-1)*.75)]
