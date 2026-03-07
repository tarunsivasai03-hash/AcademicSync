"""
Common routes — /api/*
Available to all authenticated users (any role).

  GET  /health               — no auth, uptime check
  GET  /uploads/<filename>   — serve uploaded files
  GET  /tasks                — user's personal tasks
  POST /tasks                — create task
  PUT  /tasks/<id>           — update / complete task
  DELETE /tasks/<id>         — delete task
  GET  /notifications        — user's notifications
  GET  /notifications/stream — SSE stream for real-time push
  POST /notifications/<id>/read    — mark one read
  POST /notifications/read-all     — mark all read
"""
import os
import time
import json
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify, send_from_directory, current_app, Response, stream_with_context
from flask_jwt_extended import jwt_required, decode_token

from app.extensions import db
from app.utils.decorators import any_authenticated, get_current_user
from app.models.task import Task
from app.models.notification import Notification

common_bp = Blueprint("common", __name__)


# ── GET /api/health ───────────────────────────────────────────────────────────
@common_bp.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status":    "ok",
        "service":   "AcademicSync API",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }), 200


# ── GET /uploads/<filename> ───────────────────────────────────────────────────
@common_bp.route("/uploads/<path:filename>", methods=["GET"])
@any_authenticated
def serve_upload(filename):
    """Serve files from the uploads folder. JWT required to prevent public access."""
    upload_dir = current_app.config["UPLOAD_FOLDER"]
    if not os.path.exists(os.path.join(upload_dir, filename)):
        return jsonify({"error": "File not found"}), 404
    return send_from_directory(upload_dir, filename)


# ── GET /api/tasks ────────────────────────────────────────────────────────────
@common_bp.route("/tasks", methods=["GET"])
@any_authenticated
def get_tasks():
    user  = get_current_user()
    tasks = user.tasks.order_by(Task.created_at.desc()).all()
    return jsonify([t.to_dict() for t in tasks]), 200


# ── POST /api/tasks ───────────────────────────────────────────────────────────
@common_bp.route("/tasks", methods=["POST"])
@any_authenticated
def create_task():
    user = get_current_user()
    data = request.get_json(silent=True) or {}

    title = data.get("title", "").strip()
    if not title:
        return jsonify({"error": "'title' is required"}), 400

    due_date = None
    if data.get("due_date"):
        try:
            due_date = datetime.fromisoformat(data["due_date"].replace("Z", "+00:00"))
        except ValueError:
            return jsonify({"error": "Invalid due_date format"}), 400

    task = Task(
        user_id     = user.id,
        title       = title,
        description = data.get("description", ""),
        due_date    = due_date,
        priority    = data.get("priority", "medium"),
        is_completed= bool(data.get("completed", False)),
    )
    db.session.add(task)
    db.session.commit()
    return jsonify({"message": "Task created", "task": task.to_dict()}), 201


# ── PUT /api/tasks/<id> ───────────────────────────────────────────────────────
@common_bp.route("/tasks/<int:task_id>", methods=["PUT"])
@any_authenticated
def update_task(task_id):
    user = get_current_user()
    task = Task.query.filter_by(id=task_id, user_id=user.id).first()
    if not task:
        return jsonify({"error": "Task not found"}), 404

    data = request.get_json(silent=True) or {}
    if "title" in data:
        task.title = data["title"].strip()
    if "description" in data:
        task.description = data["description"]
    if "priority" in data:
        task.priority = data["priority"]
    if "completed" in data:
        task.is_completed = bool(data["completed"])
    if "due_date" in data and data["due_date"]:
        try:
            task.due_date = datetime.fromisoformat(data["due_date"].replace("Z", "+00:00"))
        except ValueError:
            return jsonify({"error": "Invalid due_date format"}), 400

    db.session.commit()
    return jsonify({"message": "Task updated", "task": task.to_dict()}), 200


# ── DELETE /api/tasks/<id> ────────────────────────────────────────────────────
@common_bp.route("/tasks/<int:task_id>", methods=["DELETE"])
@any_authenticated
def delete_task(task_id):
    user = get_current_user()
    task = Task.query.filter_by(id=task_id, user_id=user.id).first()
    if not task:
        return jsonify({"error": "Task not found"}), 404

    db.session.delete(task)
    db.session.commit()
    return jsonify({"message": "Task deleted"}), 200


# ── GET /api/notifications ────────────────────────────────────────────────────
@common_bp.route("/notifications", methods=["GET"])
@any_authenticated
def get_notifications():
    user          = get_current_user()
    unread_only   = request.args.get("unread", "false").lower() == "true"
    limit         = min(int(request.args.get("limit", 30)), 100)

    query = user.notifications.order_by(Notification.created_at.desc())
    if unread_only:
        query = query.filter_by(is_read=False)

    notifications = query.limit(limit).all()
    unread_count  = user.notifications.filter_by(is_read=False).count()

    return jsonify({
        "notifications": [n.to_dict() for n in notifications],
        "unread_count":  unread_count,
    }), 200


# ── POST /api/notifications/<id>/read ─────────────────────────────────────────
@common_bp.route("/notifications/<int:notif_id>/read", methods=["POST"])
@any_authenticated
def mark_notification_read(notif_id):
    user  = get_current_user()
    notif = Notification.query.filter_by(id=notif_id, user_id=user.id).first()
    if not notif:
        return jsonify({"error": "Notification not found"}), 404

    notif.is_read = True
    db.session.commit()
    return jsonify({"message": "Marked as read"}), 200


# ── POST /api/notifications/read-all ─────────────────────────────────────────
@common_bp.route("/notifications/read-all", methods=["POST"])
@any_authenticated
def mark_all_read():
    user = get_current_user()
    user.notifications.filter_by(is_read=False).update({"is_read": True})
    db.session.commit()
    return jsonify({"message": "All notifications marked as read"}), 200


# ── GET /api/notifications/stream (SSE) ───────────────────────────────────────
@common_bp.route("/notifications/stream", methods=["GET"])
def notification_stream():
    """Server-Sent Events stream — pushes unread count + latest notifications
    to the browser every 15 s without polling from the client.

    EventSource cannot set custom headers, so the JWT is passed as ?token=
    """
    raw_token = request.args.get("token", "")
    if not raw_token:
        return jsonify({"error": "token parameter required"}), 401

    try:
        decoded = decode_token(raw_token)
        user_id = int(decoded["sub"])
    except Exception:
        return jsonify({"error": "Invalid or expired token"}), 401

    def generate():
        last_unread     = -1
        last_newest_id  = -1

        # Initial handshake so the browser knows the connection is live
        yield "event: connected\ndata: {}\n\n"

        while True:
            try:
                unread_count = Notification.query.filter_by(
                    user_id=user_id, is_read=False
                ).count()

                newest = (Notification.query
                          .filter_by(user_id=user_id)
                          .order_by(Notification.id.desc())
                          .first())
                newest_id = newest.id if newest else 0

                if unread_count != last_unread or newest_id != last_newest_id:
                    last_unread    = unread_count
                    last_newest_id = newest_id

                    recent = (Notification.query
                              .filter_by(user_id=user_id, is_read=False)
                              .order_by(Notification.created_at.desc())
                              .limit(5).all())

                    payload = json.dumps({
                        "unread_count":  unread_count,
                        "notifications": [n.to_dict() for n in recent],
                    })
                    yield f"data: {payload}\n\n"
                else:
                    # Keep-alive comment — prevents proxies/browsers timing out
                    yield ": ping\n\n"

            except GeneratorExit:
                break
            except Exception:
                break

            time.sleep(15)

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control":     "no-cache",
            "X-Accel-Buffering": "no",      # disable nginx buffering
            "Connection":        "keep-alive",
        },
    )
