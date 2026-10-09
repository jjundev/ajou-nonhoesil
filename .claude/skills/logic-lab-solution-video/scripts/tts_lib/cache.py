from pathlib import Path
from contextlib import contextmanager
import hashlib,json,os,tempfile

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()

def file_hash(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def atomic_json(path,value):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    tmp=None
    try:
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=path.parent,delete=False) as f:
            tmp=Path(f.name)
            json.dump(value,f,ensure_ascii=False,indent=2,allow_nan=False)
            f.flush(); os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        if tmp and tmp.exists(): tmp.unlink()

def cache_valid(output,receipt,expected_key):
    try: return receipt.get('key')==expected_key and file_hash(output)==receipt['output_sha256']
    except (OSError,KeyError,TypeError): return False

@contextmanager
def file_lock(path):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a+b') as f:
        if f.tell()==0: f.write(b'0'); f.flush()
        f.seek(0)
        try:
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(f.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError: raise RuntimeError('run is locked by another process') from None
        try: yield
        finally:
            f.seek(0)
            if os.name=='nt': msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1)
            else: fcntl.flock(f.fileno(),fcntl.LOCK_UN)
