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
    write(run/'source/adapter.json',{'sha256':adapter_hash(),'files':{str(p):file_hash(p) for p in adapter_files()}})
    write(run/'source/config.json',config)
    # Credentials stay in memory inside live_transport; its errors are sanitized.
    transport=transport or tts.live_transport(tts.load_key(env_file),config['model'])
    b=budget.Budget(Path(ledger),limit_usd=config.get('budget_usd'))
    return tts.synthesize(segments,run,config,b,transport)
