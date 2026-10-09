"""Vertex Express adapter. Never persist credentials or raw exception bodies."""
from pathlib import Path
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor
import base64,io,json,os,re,threading,time,uuid,wave,urllib.request,urllib.error
from .cache import digest,file_hash,cache_valid,atomic_json

class VertexError(RuntimeError):
    def __init__(self,status=None,reason='request failed'):
        self.status=status
        super().__init__('Vertex '+(str(status) if status else reason))

def load_key(env_file=None):
    values={}
    if env_file:
        for line in Path(env_file).read_text(encoding='utf-8-sig').splitlines():
            if '=' in line and not line.lstrip().startswith('#'):
                k,v=line.split('=',1); values[k.strip()]=v.strip().strip('"').strip("'")
    key=os.environ.get('GOOGLE_API_KEY') or os.environ.get('GEMINI_API_KEY') or values.get('GOOGLE_API_KEY') or values.get('GEMINI_API_KEY')
    if not key: raise VertexError(reason='missing API key')
    return key

def make_payload(text,config,direction):
    return {'contents':[{'role':'user','parts':[{'text':direction+'\n\n원고:\n'+text}]}],
      'generationConfig':{'responseModalities':['AUDIO'],'maxOutputTokens':config['max_output_tokens'],
       'speechConfig':{'languageCode':'ko-KR','voiceConfig':{'prebuiltVoiceConfig':{'voiceName':config['voice']}}}}}

def live_transport(key,model):
    if not re.fullmatch(r'[A-Za-z0-9._-]+',model): raise ValueError('invalid model')
    def request(payload):
        req=urllib.request.Request('https://aiplatform.googleapis.com/v1/publishers/google/models/'+model+':generateContent',
            data=json.dumps(payload,ensure_ascii=False).encode(),headers={'Content-Type':'application/json','x-goog-api-key':key},method='POST')
        try:
            with urllib.request.urlopen(req,timeout=150) as response: return json.load(response)
        except urllib.error.HTTPError as ex: raise VertexError(ex.code) from None
        except (TimeoutError,urllib.error.URLError): raise VertexError(None,'timeout/network') from None
        except Exception: raise VertexError(None,'invalid response') from None
    return request

def _pricing(config,payload):
    p=config.get('price',{})
    if not p: return None,None
    try:
        rates=[Decimal(p[k]) for k in ('input_per_million','output_per_million')]
        if any(not r.is_finite() or r<0 for r in rates): raise ValueError()
    except (KeyError,ValueError,ArithmeticError): raise VertexError(reason='invalid pricing') from None
    # UTF-8 payload bytes provide a deliberately conservative input-token allowance.
    upper=(len(json.dumps(payload,ensure_ascii=False).encode())*rates[0]+int(config['max_output_tokens'])*rates[1])/Decimal(1000000)
    return rates,max(upper,Decimal('0.000001'))

def _decode(response):
    candidates=response.get('candidates',[])
    if len(candidates)!=1 or candidates[0].get('finishReason')!='STOP': raise ValueError('truncated')
    chunks=[]; wavdata=False
    for part in candidates[0].get('content',{}).get('parts',[]):
        blob=part.get('inlineData')
        if not blob: continue
        mime=blob.get('mimeType','')
        if not (mime.startswith('audio/L16') or mime.startswith('audio/pcm') or mime in ('audio/wav','audio/x-wav')):
            raise ValueError('MIME')
        raw=base64.b64decode(blob['data'],validate=True)
        if raw.startswith(b'RIFF'):
            if chunks: raise ValueError('multiple WAV chunks')
            with wave.open(io.BytesIO(raw),'rb') as f:
                if (f.getnchannels(),f.getsampwidth(),f.getframerate())!=(1,2,24000): raise ValueError('format')
                raw=f.readframes(f.getnframes())
            wavdata=True
        else:
            if wavdata or not re.search(r'rate=24000(?:;|$)',mime): raise ValueError('rate')
        chunks.append(raw)
    raw=b''.join(chunks)
    if not raw or len(raw)%2: raise ValueError('PCM length')
    return raw

def synthesize(items,run,config,budget,transport,sleep=time.sleep):
    run=Path(run); dest=run/'assets/voice'; dest.mkdir(parents=True,exist_ok=True)
    throttled=threading.Event()
    def one(item):
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*',item['id']): raise ValueError('invalid segment ID')
        text=item['text']
        for a,b in config.get('pronunciation',{}).items(): text=text.replace(a,b)
        payload=make_payload(text,config,config['direction'])
        key=digest({'text':item['text'],'pronunciation':config.get('pronunciation',{}),'model':config['model'],'payload':payload})
        wav=dest/(item['id']+'-'+key[:16]+'.wav'); receipt=wav.with_suffix('.json')
        if receipt.exists():
            try:
                rec=json.loads(receipt.read_text(encoding='utf-8'))
                if cache_valid(wav,rec,key):
                    with wave.open(str(wav),'rb') as f:
                        if (f.getnchannels(),f.getsampwidth(),f.getframerate(),f.getnframes())==(1,2,24000,rec['samples']):
                            return rec
            except (ValueError,OSError,KeyError,wave.Error): pass
        rates,upper=_pricing(config,payload)
        for attempt in range(min(4,int(config.get('max_attempts',4)))):
            request_id=str(uuid.uuid4())
            if not budget.reserve(request_id,upper): raise VertexError(reason='budget exhausted')
            try:
                r=transport(payload)
            except Exception as ex:
                budget.settle(request_id,None)
                status=ex.status if isinstance(ex,VertexError) else None
                retry=isinstance(ex,VertexError) and (status in (429,500,502,503,504) or status is None)
                if status==429: throttled.set()
                if not retry or attempt+1>=min(4,int(config.get('max_attempts',4))):
                    raise VertexError(status,'transport failure') from None
                sleep(min(45,5*2**attempt)); continue
            usage=r.get('usageMetadata',{})
            if rates is not None and all(type(usage.get(k)) is int and usage[k]>=0 for k in ('promptTokenCount','candidatesTokenCount')):
                cost=(usage['promptTokenCount']*rates[0]+usage['candidatesTokenCount']*rates[1])/Decimal(1000000)
                budget.settle(request_id,cost,usage)
            else: budget.settle(request_id,None,usage)
            try: raw=_decode(r)
            except Exception: raise VertexError(reason='invalid or incomplete audio') from None
            pending=wav.with_suffix('.pending.wav')
            with wave.open(str(pending),'wb') as f:
                f.setparams((1,2,24000,0,'NONE','not compressed')); f.writeframes(raw)
            os.replace(pending,wav)
            rec={'id':item['id'],'path':wav.relative_to(run).as_posix(),'samples':len(raw)//2,'rate':24000,
                 'key':key,'sha256':file_hash(wav),'output_sha256':file_hash(wav),
                 'usage':{k:v for k,v in usage.items() if type(v) is int}}
            atomic_json(receipt,rec); return rec
        raise VertexError(reason='attempts exhausted')
    out=[]; index=0
    while index<len(items):
        workers=1 if throttled.is_set() else max(1,min(4,int(config.get('tts_concurrency',2))))
        batch=items[index:index+workers]
        with ThreadPoolExecutor(max_workers=workers) as pool:
            out.extend(pool.map(one,batch))
        index+=len(batch)
    atomic_json(run/'source/audio.json',{'voices':out})
    return out
