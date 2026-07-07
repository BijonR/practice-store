from flask import Blueprint, request, jsonify
from app.utils.events import log_event

tracking_bp = Blueprint("tracking", __name__)


@tracking_bp.route("/event", methods=["POST"])
def track_event():
    """Lets frontend JS log custom events beyond what server-side routes capture
    (e.g. a 'scroll_depth' or 'video_play' event fired from the browser)."""
    data = request.get_json(silent=True) or {}
    event_type = data.get("event_type")
    if not event_type:
        return jsonify({"error": "event_type is required"}), 400

    log_event(event_type, page_url=data.get("page_url"), metadata=data.get("metadata"))
    return jsonify({"status": "ok"}), 201
