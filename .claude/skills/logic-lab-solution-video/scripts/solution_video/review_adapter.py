"""Use only existing cache/budget/Vertex modules with a private package name."""
from pathlib import Path
import importlib.util,importlib,sys,types
from .util import S,read,write,file_hash,digest
from .contracts import InputError
NAME='_logic_lab_tts_lib'
def default_config(): return read(S/'assets/defaults.json')
def adapter_files():
    folder=S/'scripts/tts_lib'
    files=[folder/(n+'.py') for n in ['__init__','cache','budget','vertex_tts']]
    if not all(p.is_file() for p in files): raise InputError('tts_lib TTS adapter dependency missing')
    return files
def adapter_hash(): return digest({p.name:file_hash(p) for p in adapter_files()})
def _modules():
    folder=adapter_files()[0].parent
    if NAME not in sys.modules:
        spec=importlib.util.spec_from_file_location(NAME,folder/'__init__.py',submodule_search_locations=[str(folder)])
        mod=importlib.util.module_from_spec(spec); sys.modules[NAME]=mod; spec.loader.exec_module(mod)
    return importlib.import_module(NAME+'.vertex_tts'),importlib.import_module(NAME+'.budget')
def validate_config(config):
    def scrub(v):
        if isinstance(v,dict):
            for k,x in v.items():
                if any(s in k.lower() for s in ['api_key','apikey','credential','secret','authorization','access_token']): raise InputError('credentials must come from environment, never config')
                scrub(x)
        elif isinstance(v,list):
            for x in v: scrub(x)
    scrub(config)
    expected={'provider':'vertex-ai-express','language':'ko-KR','sample_rate':24000,'width':1920,'height':1080,'fps':30}
    if any(config.get(k)!=v for k,v in expected.items()): raise InputError('unsupported provider/media contract; no automatic substitute')
    if not config.get('model') or not config.get('voice'): raise InputError('model/voice must be explicit')
    if not 0<float(config.get('chars_per_second',7))<=8: raise InputError('invalid writing speed')
def generate_voice(segments,run,config,ledger,transport=None,env_file=None):
    validate_config(config); tts,budget=_modules(); run=Path(run)
    from .speech_chunks import speech_items,validate_speech_chunks,check_trims_before_tts,join_segment_audio,CHUNK_AUDIO
    # pcm-chunks-v1: 청크가 하나라도 있으면 전부 있어야 한다(일부 누락을 글자 수 방식으로 메우지 않는다). 절단표는 유료 요청 전에 검사한다.
    chunk_mode=any('chunks' in s for s in segments)
    validate_speech_chunks(segments,required=chunk_mode); items=speech_items(segments)
    # spoken-text-only-v1: 옛 config 의 direction 은 요청에 들어가지 않는다. 동결 config 에도 남기지 않아 보낸 것과 맞춘다.
    config={k:v for k,v in config.items() if k!='direction'}
    trims=check_trims_before_tts(segments,run,config)
    write(run/'source/adapter.json',{'sha256':adapter_hash(),'files':{str(p):file_hash(p) for p in adapter_files()}})
    write(run/'source/config.json',config)
    # Credentials stay in memory inside live_transport; its errors are sanitized.
    transport=transport or tts.live_transport(tts.load_key(env_file),config['model'])
    b=budget.Budget(Path(ledger),limit_usd=config.get('budget_usd'))
    if not chunk_mode: return tts.synthesize(items,run,config,b,transport)
    # 청크 WAV 는 지우지 않는다: 실패하면 성공한 청크는 캐시로 다음 실행에 재사용된다. audio.json 은 연결이 끝난 뒤에만 갱신한다.
    chunks=tts.synthesize(items,run,config,b,transport,audio_index=None)
    write(run/CHUNK_AUDIO,{'policy':tts.POLICY,'voices':chunks})
    audio=join_segment_audio(segments,chunks,run,trims)
    write(run/'source/audio.json',{'voices':audio})
    return audio
