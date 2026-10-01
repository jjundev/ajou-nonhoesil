"""Strict static export, inspired by bio-review-pack's DOM/anchor approach.

The learning HTML vocabulary is converted directly; controls/scripts are omitted,
solutions and static widget equivalents are retained. No biology runtime dependency.
"""
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
import hashlib
import html
import re
from urllib.parse import quote, unquote, urlsplit

@dataclass
class Node:
    tag: str
    attrs: dict = field(default_factory=dict)
    children: list = field(default_factory=list)
    def walk(self):
        yield self
        for child in self.children:
            if isinstance(child,Node): yield from child.walk()

class Parser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root=Node('root');self.stack=[self.root]
    def handle_starttag(self,tag,attrs):
        node=Node(tag,dict(attrs));self.stack[-1].children.append(node)
        if tag not in {'img','br','hr','input','meta','link','source','wbr'}:self.stack.append(node)
    def handle_startendtag(self,tag,attrs):
        self.handle_starttag(tag,attrs)
        if self.stack[-1].tag==tag:self.stack.pop()
    def handle_endtag(self,tag):
        for i in range(len(self.stack)-1,0,-1):
            if self.stack[i].tag==tag:
                del self.stack[i:];break
    def handle_data(self,data):self.stack[-1].children.append(data)

def parse(path):
    parser=Parser();parser.feed(Path(path).read_text(encoding='utf-8'))
    return next((n for n in parser.root.walk() if n.tag=='main'),parser.root)

def omitted(node):
    return node.tag in {'script','style','nav','button','input','select','output'} or 'controls' in node.attrs.get('class','').split()

def serialize(node):
    if isinstance(node,str):return html.escape(node)
    attrs=''.join(f' {k}="{html.escape(str(v or ""),quote=True)}"' for k,v in node.attrs.items())
    return '<'+node.tag+attrs+'>'+''.join(serialize(c) for c in node.children)+'</'+node.tag+'>'

def export_document(path, export=True):
    path=Path(path);tree=parse(path);figures=set()
    def render(n):
        if isinstance(n,str):return n.replace('|',r'\|')
        if omitted(n):return ''
        tag=n.tag
        if tag=='math':
            tex=n.attrs.get('data-tex')
            if not tex:raise ValueError('MathML missing data-tex')
            mark='$$' if n.attrs.get('display')=='block' else '$'
            return mark+tex+mark
        if tag=='svg':
            text=serialize(n)
            if 'xmlns=' not in text:text=text.replace('<svg','<svg xmlns="http://www.w3.org/2000/svg"',1)
            filename='md-'+hashlib.sha256(text.encode()).hexdigest()[:16]+'.svg'
            dest=path.parent/'figures'/filename
            if export:
                dest.parent.mkdir(exist_ok=True);dest.write_text(text,encoding='utf-8')
            figures.add(filename)
            title=next((''.join(c for c in x.children if isinstance(c,str)) for x in n.walk() if x.tag=='title'),'회로 그림')
            return f'![{title}](figures/{filename})\n\n'
        body=''.join(render(c) for c in n.children)
        anchor=f'<a id="{n.attrs["id"]}"></a>\n' if n.attrs.get('id') else ''
        if tag in {'h1','h2','h3','h4','h5','h6'}:return '\n'+anchor+'#'*int(tag[1])+' '+body.strip()+'\n\n'
        if tag=='a':
            href=n.attrs.get('href','')
            href=re.sub(r'(실험\d{2}_(?:실험설명|기출풀이))\.html',r'\1.md',unquote(href))
            href=quote(href,safe='/#:.?=&%_-')
            return f'[{body}]({href})' if href else body
        if tag=='img':
            src=quote(unquote(n.attrs.get('src','')),safe='/#:.?=&%_-')
            return f'![{n.attrs.get("alt","그림")}]({src})'
        if tag=='span' and 'ov' in n.attrs.get('class','').split():return '('+body+")'"
        if tag in {'strong','b'}:return '**'+body+'**'
        if tag in {'em','i'}:return '*'+body+'*'
        if tag=='code':return '`'+body+'`'
        if tag=='pre':return '\n\n```\n'+body.replace('`','')+'\n```\n\n'
        if tag=='br':return '<br>'
        if tag=='hr':return '\n---\n'
        if tag=='summary':return '\n#### '+body.strip()+'\n\n'
        if tag=='li':return anchor+'- '+body.strip()+'\n'
        if tag=='table':
            rows=[]
            for tr in n.walk():
                if tr.tag=='tr':
                    cells=[render(c).strip().replace('\n','<br>') for c in tr.children if isinstance(c,Node) and c.tag in {'td','th'}]
                    rows.append('| '+' | '.join(cells)+' |')
            if rows:
                cols=len([c for tr in n.walk() if tr.tag=='tr' for c in tr.children if isinstance(c,Node) and c.tag in {'td','th'}])
                first=next(x for x in n.walk() if x.tag=='tr')
                count=sum(isinstance(c,Node) and c.tag in {'td','th'} for c in first.children)
                rows.insert(1,'| '+' | '.join(['---']*count)+' |')
            return '\n'+anchor+'\n'.join(rows)+'\n\n'
        if tag in {'p','div','section','article','main','aside','blockquote','figure','figcaption','details','ul','ol','dl','dt','dd','header'}:return '\n'+anchor+body.strip()+'\n\n'
        if tag in {'root','body','span','td','th','thead','tbody','tr','label','small','sup','sub'}:return anchor+body
        raise ValueError('Unsupported learning markup: '+tag)
    return re.sub(r'\n{3,}','\n\n',render(tree)).strip()+'\n',len(figures)

def convert_pack(note_path,review_path):
    paths=[Path(note_path),Path(review_path)]
    names=[re.fullmatch(r'(실험\d{2})_(실험설명|기출풀이)\.html',p.name) for p in paths]
    if not all(names) or names[0][1]!=names[1][1] or [m[2] for m in names]!=['실험설명','기출풀이'] or paths[0].parent!=paths[1].parent:
        raise ValueError('Mismatched learning pack names')
    outputs=[];count=0
    for path in paths:
        text,n=export_document(path);out=path.with_suffix('.md')
        out.write_text(text,encoding='utf-8');outputs.append(out);count+=n
    return outputs,count

def check_md(html_path,md_path):
    path=Path(md_path)
    if not path.is_file():return ['Missing MD: '+str(path)]
    text=path.read_text(encoding='utf-8');errors=[]
    # Check every educational text leaf independently of the rendering algorithm.
    def norm(s):return re.sub(r'[\s\\*_\x60|]','',html.unescape(s))
    normalized=norm(text)
    def visit(n,article='document'):
        if isinstance(n,str):
            if norm(n) and norm(n) not in normalized:errors.append(article+': missing text '+n.strip()[:60])
            return
        if omitted(n):return
        article=n.attrs.get('id',article)
        if n.attrs.get('id') and f'<a id="{n.attrs["id"]}"></a>' not in text:errors.append(article+': missing anchor')
        if n.tag=='math':
            if n.attrs.get('data-tex','!missing!') not in text:errors.append(article+': missing math')
            return
        if n.tag=='svg':return
        for c in n.children:visit(c,article)
    visit(parse(html_path))
    for target in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',text):
        if urlsplit(target).scheme:continue
        part,_,frag=unquote(target).partition('#')
        dest=path.parent/part if part else path
        # Source evidence lives outside stage; checked after publication.
        if part.startswith('../../'):continue
        if not dest.is_file():errors.append('Missing link/image: '+target)
        elif frag and dest.suffix=='.md' and f'<a id="{frag}"></a>' not in dest.read_text(encoding='utf-8'):errors.append('Missing target anchor: '+target)
    expected,_=export_document(html_path,export=False)
    expected_imgs=re.findall(r'!\[[^\]]*\]\(([^)]+)\)',expected)
    for image in expected_imgs:
        if image not in text:errors.append('Missing figure: '+image)
    return errors
