from pathlib import Path
from decimal import Decimal
import json,threading
from .cache import atomic_json,file_lock

_locks={}; _guard=threading.Lock()

class Budget:
    def __init__(self,path,limit_usd=None):
        self.path=Path(path); self.limit=None if limit_usd is None else Decimal(str(limit_usd))
        if self.limit is not None and (not self.limit.is_finite() or self.limit<0): raise ValueError('invalid budget')
        with _guard: self.lock=_locks.setdefault(str(self.path.resolve()),threading.RLock())
    def _load(self):
        return json.loads(self.path.read_text(encoding='utf-8')) if self.path.exists() else {'requests':{}}
    def _used(self,data):
        amounts=[r['actual'] if r.get('actual') is not None else r.get('reserved') for r in data['requests'].values()]
        if any(a is None for a in amounts): raise ValueError('earlier unpriced usage cannot be checked against a USD limit; use a new run or remove the limit')
        return sum((Decimal(a) for a in amounts),Decimal(0))
    def remaining(self):
        with self.lock: return None if self.limit is None else max(Decimal(0),self.limit-self._used(self._load()))
    def reserve(self,request_id,upper_usd=None):
        value=None if upper_usd is None else Decimal(str(upper_usd))
        if value is not None and (not value.is_finite() or value<=0): raise ValueError('invalid request bound')
        with self.lock, file_lock(self.path.with_suffix('.lock')):
            data=self._load()
            if request_id in data['requests']: raise ValueError('duplicate request ID')
            if self.limit is not None:
                if value is None: raise ValueError('explicit USD limit needs configured rates')
                if self._used(data)+value>self.limit: return False
            data['requests'][request_id]={'reserved':None if value is None else str(value),'actual':None,'status':'reserved','usage':{}}
            atomic_json(self.path,data); return True
    def settle(self,request_id,actual_usd,usage=None):
        with self.lock, file_lock(self.path.with_suffix('.lock')):
            data=self._load(); row=data['requests'][request_id]
            if actual_usd is not None:
                cost=Decimal(str(actual_usd))
                if not cost.is_finite() or cost<0: raise ValueError('invalid actual cost')
                row['actual']=str(cost)
            row['usage']={k:v for k,v in (usage or {}).items() if type(v) is int and v>=0}
            row['status']=('usage-recorded' if row['usage'] else 'unknown') if actual_usd is None else 'settled'
            atomic_json(self.path,data)
