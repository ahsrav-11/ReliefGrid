from . import db
from .models import Notification, User


def notify(user_id, msg):
    db.session.add(Notification(user_id=user_id, message=msg))


def notify_admins(msg):
    for u in User.query.filter_by(role="admin"):
        notify(u.id, msg)


def intval(v, lo, hi, label):
    try:
        n = int(v)
    except (TypeError, ValueError):
        n = None
    if n is None or not lo <= n <= hi:
        raise ValueError(f"{label} must be a whole number between {lo} and {hi}.")
    return n


def field(name, label, type="text", options=None, value="", **kw):
    opts = [(str(v), l) for v, l in options] if options is not None else None
    return {"name": name, "label": label, "type": type, "options": opts, "value": value, **kw}
