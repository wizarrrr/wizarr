from app.models.database import Requests
from playhouse.shortcuts import model_to_dict
from json import loads, dumps

def get_requests(disallowed: list[str] = None):
    # Get all requests from the database
    requests = list(Requests.select().dicts())

    # Remove disallowed requests keys
    if disallowed is not None:
        for request in requests:
            for key in disallowed:
                del request[key]

    # Return the requests
    return loads(dumps(requests, indent=4, sort_keys=True, default=str))
