from datetime import datetime
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash

from app.database import get_db

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("staff_id"):
            return redirect(url_for("admin.admin_login", next=request.path))
        return view(*args, **kwargs)
    return wrapped

@admin_bp.route("/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        db = get_db()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        staff = db.execute(
            "SELECT * FROM staff WHERE username = ?", (username,)
        ).fetchone()
        if staff and check_password_hash(staff["password_hash"], password):
            session["staff_id"] = staff["id"]
            session["staff_username"] = staff["username"]
            next_url = request.args.get("next") or url_for("admin.admin")
            return redirect(next_url)
        flash("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
    return render_template("login.html")

@admin_bp.route("/logout", methods=["POST"])
def admin_logout():
    session.clear()
    return redirect(url_for("admin.admin_login"))

@admin_bp.route("/")
@login_required
def admin():
    db = get_db()
    queue_types = db.execute("SELECT * FROM queue_types").fetchall()
    return render_template("admin.html", queue_types=queue_types)

@admin_bp.route("/room/<int:queue_type_id>")
@login_required
def room(queue_type_id):
    db = get_db()
    qtype = db.execute("SELECT * FROM queue_types WHERE id = ?", (queue_type_id,)).fetchone()
    if not qtype:
        return redirect(url_for("admin.admin"))

    waiting = db.execute(
        """SELECT tickets.*, queue_types.name as type_name FROM tickets
           JOIN queue_types ON tickets.queue_type_id = queue_types.id
           WHERE tickets.status = 'waiting' AND queue_type_id = ?
           ORDER BY tickets.created_at ASC""", (queue_type_id,)
    ).fetchall()
    
    in_service = db.execute(
        """SELECT tickets.*, queue_types.name as type_name FROM tickets
           JOIN queue_types ON tickets.queue_type_id = queue_types.id
           WHERE tickets.status = 'in_service' AND queue_type_id = ?
           ORDER BY tickets.called_at DESC""", (queue_type_id,)
    ).fetchall()

    return render_template(
        "admin_room.html", qtype=qtype, waiting=waiting, in_service=in_service
    )

@admin_bp.route("/call_next/<int:queue_type_id>", methods=["POST"])
@login_required
def call_next(queue_type_id):
    db = get_db()
    ticket = db.execute(
        """SELECT * FROM tickets WHERE queue_type_id = ? AND status = 'waiting'
           ORDER BY created_at ASC LIMIT 1""",
        (queue_type_id,),
    ).fetchone()
    if ticket:
        now = datetime.now().isoformat(timespec="seconds")
        db.execute(
            "UPDATE tickets SET status = 'in_service', called_at = ? WHERE id = ?",
            (now, ticket["id"]),
        )
        db.commit()
    return redirect(url_for("admin.room", queue_type_id=queue_type_id))

@admin_bp.route("/complete/<int:ticket_id>", methods=["POST"])
@login_required
def complete_ticket(ticket_id):
    db = get_db()
    ticket = db.execute("SELECT queue_type_id FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    if ticket:
        now = datetime.now().isoformat(timespec="seconds")
        db.execute(
            "UPDATE tickets SET status = 'done', completed_at = ? WHERE id = ?",
            (now, ticket_id),
        )
        db.commit()
        return redirect(url_for("admin.room", queue_type_id=ticket["queue_type_id"]))
    return redirect(url_for("admin.admin"))

@admin_bp.route("/skip/<int:ticket_id>", methods=["POST"])
@login_required
def skip_ticket(ticket_id):
    db = get_db()
    ticket = db.execute("SELECT queue_type_id FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    if ticket:
        db.execute("UPDATE tickets SET status = 'skipped' WHERE id = ?", (ticket_id,))
        db.commit()
        return redirect(url_for("admin.room", queue_type_id=ticket["queue_type_id"]))
    return redirect(url_for("admin.admin"))

@admin_bp.route("/dashboard")
@login_required
def dashboard():
    db = get_db()
    today = datetime.now().strftime("%Y-%m-%d")

    total_today = db.execute(
        "SELECT COUNT(*) as cnt FROM tickets WHERE date(created_at) = ?", (today,)
    ).fetchone()["cnt"]

    done_today = db.execute(
        "SELECT COUNT(*) as cnt FROM tickets WHERE date(created_at) = ? AND status = 'done'",
        (today,),
    ).fetchone()["cnt"]

    skipped_today = db.execute(
        "SELECT COUNT(*) as cnt FROM tickets WHERE date(created_at) = ? AND status = 'skipped'",
        (today,),
    ).fetchone()["cnt"]

    waiting_now = db.execute(
        "SELECT COUNT(*) as cnt FROM tickets WHERE status = 'waiting'"
    ).fetchone()["cnt"]

    # average wait time (created_at -> called_at) today, in minutes
    rows = db.execute(
        """SELECT created_at, called_at FROM tickets
           WHERE date(created_at) = ? AND called_at IS NOT NULL""",
        (today,),
    ).fetchall()
    wait_seconds = []
    for row in rows:
        try:
            created = datetime.fromisoformat(row["created_at"])
            called = datetime.fromisoformat(row["called_at"])
            diff = (called - created).total_seconds()
            if diff >= 0:
                wait_seconds.append(diff)
        except (ValueError, TypeError):
            continue
    avg_wait_minutes = round((sum(wait_seconds) / len(wait_seconds)) / 60, 1) if wait_seconds else 0

    # busiest hour today (by ticket creation time)
    hour_rows = db.execute(
        "SELECT created_at FROM tickets WHERE date(created_at) = ?", (today,)
    ).fetchall()
    hour_counts = {}
    for row in hour_rows:
        try:
            hour = datetime.fromisoformat(row["created_at"]).strftime("%H:00")
            hour_counts[hour] = hour_counts.get(hour, 0) + 1
        except (ValueError, TypeError):
            continue
    busiest_hour = max(hour_counts, key=hour_counts.get) if hour_counts else "-"

    # breakdown per queue type today
    per_type = db.execute(
        """SELECT queue_types.name as type_name, COUNT(tickets.id) as cnt
           FROM queue_types
           LEFT JOIN tickets ON tickets.queue_type_id = queue_types.id
               AND date(tickets.created_at) = ?
           GROUP BY queue_types.id""",
        (today,),
    ).fetchall()

    return render_template(
        "dashboard.html",
        total_today=total_today,
        done_today=done_today,
        skipped_today=skipped_today,
        waiting_now=waiting_now,
        avg_wait_minutes=avg_wait_minutes,
        busiest_hour=busiest_hour,
        per_type=per_type,
    )
