from app.models.database.webhooks import Webhooks
from requests import post
from json import loads, dumps

def run_webhook(event: str, data: dict):
    webhooks = Webhooks.select()
    for webhook in webhooks:
        try:
            post(webhook.url, json={"event": event, "data": loads(dumps(data, indent=4, sort_keys=True, default=str))}, verify=False, timeout=10)
        except Exception:
            pass
