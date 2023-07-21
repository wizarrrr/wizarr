from datetime import datetime
from json import JSONDecoder, JSONEncoder, dumps


class DateTimeEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return JSONEncoder.default(self, obj)
    
class DateTimeDecoder(JSONDecoder):
    def __init__(self, *args, **kwargs):
        super().__init__(object_hook=self.object_hook, *args, **kwargs)

    def object_hook(self, obj):
        for key, value in obj.items():
            if isinstance(value, str):
                try:
                    obj[key] = datetime.fromisoformat(value)
                except ValueError:
                    pass
        return obj