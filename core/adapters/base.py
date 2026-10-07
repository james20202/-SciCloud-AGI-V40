from abc import ABC, abstractmethod

class AdapterResult:
    def __init__(self, success, message='', outputs=None, data=None):
        self.success=bool(success); self.message=message; self.outputs=outputs or []; self.data=data or {}
    def to_dict(self):
        return {'success':self.success,'message':self.message,'outputs':self.outputs,'data':self.data}

class BaseAdapter(ABC):
    key='base'
    @abstractmethod
    def test(self, model): raise NotImplementedError
    @abstractmethod
    def execute(self, model, task, context): raise NotImplementedError
