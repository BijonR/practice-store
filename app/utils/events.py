from flask import request, session
from flask_login import current_user
from app import db
from app.models import Event
import uuid


def _get_session_id():
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
    return session["session_id"]


def log_event(event_type, page_url=None, metadata=None):
    """Writes one row to the events table. Call this anywhere in a route
    to record something for the analytics dashboard."""
    try:
        user_id = current_user.id if current_user.is_authenticated else None
    except Exception:
        user_id = None

    event = Event(
        user_id=user_id,
        session_id=_get_session_id(),
        event_type=event_type,
        page_url=page_url or request.path,
        event_metadata=metadata or {},
    )
    db.session.add(event)
    db.session.commit()
