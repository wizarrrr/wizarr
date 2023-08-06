from .pushover import Pushover, PushoverResource
from .smtp import SMTP, SMTPResource


__resources__ = {
    "pushover": {
        "resource": PushoverResource,
        "notification": Pushover,
    },
    "smtp": {
        "resource": SMTPResource,
        "notification": SMTP,
    }
}
