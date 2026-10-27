"""Explicit, build-time column sizing for problem explanations and note topics.

The workbook and authored fragments remain the source of educational content.
Metadata identifies roles; header spelling never determines an input/output role.
"""
from pathlib import Path
import html
import json
import re
import unicodedata
from .html2md import Node, Parser

class TableLayoutError(ValueError):
    pass

ROLES={'index','control','input','intermediate','output','description'}
KINDS={'signal','bus','expression','text','connector','index'}
TABLE=re.compile(r'<table\b[^>]*>.*?</table\s*>',re.S|re.I)
PROBLEM_KEY=r'[^/]+/(original|conditions|ask|explanation)/\d+'
NOTE_KEY=r't-[a-z0-9-]+/\d+'

def text(node):
    return ''.join(text(c) if isinstance(c,Node) else c for c in node.children)

def normalized(node):
    return ' '.join(text(node).split())

def markup(node):
    if isinstance(node,str):return html.escape(node,quote=False)
    attrs=''.join(f' {k}="{html.escape(str(v or ""),quote=True)}"' for k,v in node.attrs.items())
    start='<'+node.tag+attrs+'>'
    if node.tag in {'br','img','hr','wbr','col','input','meta','link','source'}:return start
    return start+''.join(markup(c) for c in node.children)+'</'+node.tag+'>'

def validate(layouts,pattern=PROBLEM_KEY):
    if layouts.get('version')!=1 or not isinstance(layouts.get('tables'),list):
        raise TableLayoutError('table-layout: expected version 1 and tables list')
    seen=set()
    pairs={}
    for entry in layouts['tables']:
        key=entry.get('key','table-layout')
        if key in seen:raise TableLayoutError(key+': duplicate entry')
        seen.add(key)
        if not re.fullmatch(pattern,key):raise TableLayoutError(key+': invalid key')
        columns=entry.get('columns',[])
        if not columns or len(columns)!=len(entry.get('expected_headers',[])):raise TableLayoutError(key+': column/header count')
        for col in columns:
            if col.get('role') not in ROLES or col.get('kind') not in KINDS or not isinstance(col.get('group'),str):raise TableLayoutError(key+': invalid column')
            if 'min_rem' in col and (not isinstance(col['min_rem'],(int,float)) or not 0<col['min_rem']<1000):raise TableLayoutError(key+': invalid min_rem')
        seen_edges=set()
        for edge in entry.get('boundaries',[]):
            left=edge.get('left')
            if not isinstance(left,int) or not 0<=left<len(columns)-1 or left in seen_edges or edge.get('kind') not in {'major','minor'}:raise TableLayoutError(key+': invalid boundary')
            seen_edges.add(left)
        if pair:=entry.get('pair'):
            # Pair identity is explicit and must use exactly the same layout contract.
            signature={k:entry.get(k) for k in ('expected_headers','columns','boundaries')}
            if pair in pairs and pairs[pair]!=signature:raise TableLayoutError(key+': incompatible pair schema')
            pairs[pair]=signature
    return layouts

def load_layouts(author_root:Path):
    path=Path(author_root)/'problem-explanations/table-layout.json'
    if not path.is_file():return None
    try:return validate(json.loads(path.read_text(encoding='utf-8')))
    except (TypeError,KeyError,json.JSONDecodeError) as exc:raise TableLayoutError(str(path)+': '+str(exc)) from exc

def grid(table,key):
    rows=[n for n in table.walk() if n.tag=='tr' and 'data-layout-group-row' not in n.attrs]
    active={};result=[];width=0
    for row in rows:
        line={i:cell for i,(cell,left) in active.items() if left>0}
        newactive={i:(cell,left-1) for i,(cell,left) in active.items() if left>1}
        positions=[];i=0
        for cell in row.children:
            if not isinstance(cell,Node) or cell.tag not in {'th','td'}:continue
            while i in line:i+=1
            try:span=int(cell.attrs.get('colspan',1));height=int(cell.attrs.get('rowspan',1))
            except ValueError as exc:raise TableLayoutError(key+': invalid span') from exc
            if span<1 or height<1:raise TableLayoutError(key+': invalid span')
            if any(j in line for j in range(i,i+span)):raise TableLayoutError(key+': overlapping span')
            positions.append((cell,i,span))
            for j in range(i,i+span):
                line[j]=cell
                if height>1:newactive[j]=(cell,height-1)
            i+=span
        active=newactive;width=max(width,len(line));result.append((row,line,positions))
    if not result or active or any(len(line)!=width for _,line,_ in result):raise TableLayoutError(key+': irregular grid')
    headers=[]
    for i in range(width):
        candidates=[line[i] for _,line,_ in result if line[i].tag=='th']
        if not candidates:raise TableLayoutError(key+': missing column header')
        headers.append(normalized(candidates[-1]))
    return result,headers

def units(value):
    return sum(2 if unicodedata.east_asian_width(c) in 'WF' else 1 for c in value)

def layout_problem_tables(problem_id,parts,layouts):
    return _layout_parts(problem_id,parts,layouts,PROBLEM_KEY,lambda part,ordinal:f'{problem_id}/{part}/{ordinal}')

def load_note_layouts(run:Path):
    path=Path(run)/'sections/table-layout.json'
    if not path.is_file():return None
    try:return validate(json.loads(path.read_text(encoding='utf-8')),NOTE_KEY)
    except (TypeError,KeyError,json.JSONDecodeError) as exc:raise TableLayoutError(str(path)+': '+str(exc)) from exc

def layout_note_tables(topic_id:str,fragment:str,layouts:dict|None)->str:
    # Note keys are <topic-id>/<ordinal>; the whole topic fragment is one part.
    return _layout_parts(topic_id,dict(body=fragment),layouts,NOTE_KEY,lambda part,ordinal:f'{topic_id}/{ordinal}')['body']

def _layout_parts(owner,parts,layouts,pattern,keyof):
    if layouts is None:return parts.copy()
    validate(layouts,pattern)
    entries={e['key']:e for e in layouts['tables'] if e['key'].split('/')[0]==owner}
    found={};parsed={}
    for part,source in parts.items():
        for ordinal,match in enumerate(TABLE.finditer(source)):
            key=keyof(part,ordinal)
            if key not in entries:raise TableLayoutError(key+': missing metadata')
            parser=Parser();parser.feed(match.group());tables=[n for n in parser.root.walk() if n.tag=='table']
            if len(tables)!=1:raise TableLayoutError(key+': nested tables unsupported')
            table=tables[0]
            # Remove only generated decorations, so a second render is identical.
            for parent in list(table.walk()):
                parent.children=[c for c in parent.children if not (isinstance(c,Node) and ('data-layout-group-row' in c.attrs or 'data-layout-cols' in c.attrs))]
            rows,headers=grid(table,key);entry=entries[key]
            if headers!=entry['expected_headers']:raise TableLayoutError(key+': header drift '+repr(headers))
            for _,_,positions in rows:
                for cell,start,span in positions:
                    if any(start<=e['left']<start+span-1 for e in entry.get('boundaries',[])):raise TableLayoutError(key+': spanning cell crosses group boundary')
            found[key]=match;parsed[key]=(table,rows)
    if set(entries)!=set(found):raise TableLayoutError(next(iter(set(entries)-set(found)))+': extra metadata')
    widths={}
    for key,(table,rows) in parsed.items():
        cols=entries[key]['columns'];sizes=[]
        for i,col in enumerate(cols):
            kind=col['kind'];values=[]
            for _,line,_ in rows:
                cell=line[i]
                if int(cell.attrs.get('colspan',1))>1:continue
                value=normalized(cell)
                values.extend(value.split() if cell.tag=='th' and kind in {'signal','index'} else [value])
            minimum={'signal':3,'index':3,'bus':4,'expression':6,'text':7.8,'connector':2}[kind]
            content=0 if kind=='text' else max((units(v) for v in values),default=0)*.65+1
            sizes.append(max(minimum,content,col.get('min_rem',0)))
        widths[key]=sizes
    profiles={}
    for key,sizes in widths.items():
        profile=entries[key].get('pair',key)
        profiles[profile]=[max(a,b) for a,b in zip(profiles.get(profile,sizes),sizes)]
    # Normalize the complete profile, including bit lengths from both partners.
    # Blank cells carry no length and must not accidentally couple bus columns.
    for profile,sizes in profiles.items():
        members=[k for k in parsed if entries[k].get('pair',k)==profile]
        cols=entries[members[0]]['columns']
        signal=max((sizes[i] for i,c in enumerate(cols) if c['kind']=='signal'),default=3)
        lengths={}
        for i,c in enumerate(cols):
            if c['kind']=='signal':sizes[i]=signal
            if c['kind']=='bus':
                lengths[i]=max((len(normalized(line[i]).replace(' ',''))
                    for k in members for _,line,_ in parsed[k][1]
                    if line[i].tag=='td' and normalized(line[i])),default=0)
        buses={}
        for i,length in lengths.items():
            if length:buses[length]=max(buses.get(length,0),sizes[i])
        for i,length in lengths.items():
            if length:sizes[i]=buses[length]
    for key,(table,rows) in parsed.items():
        entry=entries[key];cols=entry['columns'];sizes=profiles[entry.get('pair',key)].copy()
        pads=[{'left':0.,'right':0.} for _ in cols];labels=[[] for _ in cols]
        for e in entry.get('boundaries',[]):
            left=e['left'];amount=.5 if e['kind']=='major' else .25
            pads[left]['right']=amount;pads[left+1]['left']=amount
            labels[left].append(e['kind']+'-right');labels[left+1].append(e['kind']+'-left')
        totals=[round(s+p['left']+p['right'],3) for s,p in zip(sizes,pads)]
        table.attrs.update({'data-layout-table':key,'data-layout-mode':'text' if any(c['kind']=='text' for c in cols) else 'compact','style':f'--layout-min:{sum(totals):.3f}rem'})
        groups=[]
        for i,c in enumerate(cols):
            if groups and groups[-1][0]==c['group']:groups[-1][2]+=1
            else:groups.append([c['group'],i,1])
        text_count=sum(c['kind']=='text' for c in cols)
        column_groups=[]
        for name,start,span in groups:
            column_nodes=[]
            for i in range(start,start+span):
                width=f'{totals[i]:.3f}rem'
                if cols[i]['kind']=='text':
                    width=f'calc({width} + max(0px, 100cqw - var(--layout-min)) / {text_count})'
                column_nodes.append(Node('col',{'style':'width:'+width}))
            column_groups.append(Node('colgroup',{'data-layout-cols':''},column_nodes))
        table.children[0:0]=column_groups
        for _,_,positions in rows:
            for cell,start,span in positions:
                cell.attrs.update({'data-layout-kind':cols[start]['kind'],'data-layout-role':cols[start]['role']})
                boundary=labels[start] if span==1 else [v for v in labels[start] if v.endswith('left')]+[v for v in labels[start+span-1] if v.endswith('right')]
                # A re-layout must not keep boundaries the metadata no longer has.
                if boundary:cell.attrs['data-layout-boundary']=' '.join(boundary)
                else:cell.attrs.pop('data-layout-boundary',None)
                if cell.tag=='th':cell.attrs.setdefault('scope','colgroup' if span>1 else 'col')
        existing=any([normalized(cell) for cell,_,_ in positions]==[g[0] for g in groups] for _,_,positions in rows)
        if len(groups)>1 and any(c['role'] in {'input','output','control','intermediate'} for c in cols) and not existing:
            group_row=Node('tr',{'data-layout-group-row':''},[Node('th',{'scope':'colgroup','colspan':str(span)},[name]) for name,start,span in groups])
            thead=next((n for n in table.children if isinstance(n,Node) and n.tag=='thead'),None)
            if thead:thead.children.insert(0,group_row)
            else:
                # Keep all header rows in one thead; inserting a lone implicit tbody is invalid HTML.
                header_rows=[row for row,_,positions in rows if positions and all(c.tag=='th' for c,_,_ in positions)]
                for parent in list(table.walk()):parent.children=[c for c in parent.children if not any(c is r for r in header_rows)]
                table.children.insert(len(column_groups),Node('thead',{},[group_row]+header_rows))
    output={}
    for part,source in parts.items():
        ordinal=iter(range(1000000))
        output[part]=TABLE.sub(lambda m:markup(parsed[keyof(part,next(ordinal))][0]),source)
    return output
