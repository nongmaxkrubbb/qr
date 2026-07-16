from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, jsonify

from app.database import get_db
from app.utils import next_queue_number, make_qr_base64, people_ahead, avg_service_seconds

user_bp = Blueprint('user', __name__)

@user_bp.route("/")
def index():
    db = get_db()
    queue_types = db.execute("SELECT * FROM queue_types").fetchall()
    return render_template("index.html", queue_types=queue_types)

@user_bp.route("/get_ticket", methods=["POST"])
def get_ticket():
    db = get_db()
    queue_type_id = request.form.get("queue_type_id", type=int)
    qtype = db.execute(
        "SELECT * FROM queue_types WHERE id = ?", (queue_type_id,)
    ).fetchone()
    if not qtype:
        return redirect(url_for("user.index"))

    queue_number = next_queue_number(db, queue_type_id, qtype["prefix"])
    now = datetime.now().isoformat(timespec="seconds")
    cur = db.execute(
        """INSERT INTO tickets (queue_number, queue_type_id, status, created_at)
           VALUES (?, ?, 'waiting', ?)""",
        (queue_number, queue_type_id, now),
    )
    db.commit()
    ticket_id = cur.lastrowid

    status_url = url_for("user.status_page", ticket_id=ticket_id, _external=True)
    qr_b64 = make_qr_base64(status_url)

    return render_template(
        "ticket.html",
        queue_number=queue_number,
        ticket_id=ticket_id,
        qr_b64=qr_b64,
        status_url=status_url,
    )

@user_bp.route("/status/<int:ticket_id>")
def status_page(ticket_id):
    return render_template("status.html", ticket_id=ticket_id)

@user_bp.route("/api/status/<int:ticket_id>")
def api_status(ticket_id):
    db = get_db()
    ticket = db.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    if not ticket:
        return jsonify({"error": "ไม่พบคิวนี้"}), 404

    qtype = db.execute(
        "SELECT * FROM queue_types WHERE id = ?", (ticket["queue_type_id"],)
    ).fetchone()

    now_calling = db.execute(
        """SELECT queue_number FROM tickets
           WHERE queue_type_id = ? AND status = 'in_service'
           ORDER BY called_at DESC LIMIT 1""",
        (ticket["queue_type_id"],),
    ).fetchone()

    ahead = people_ahead(db, ticket) if ticket["status"] == "waiting" else 0
    avg_secs = avg_service_seconds(db, ticket["queue_type_id"])
    eta_minutes = round((ahead * avg_secs) / 60) if ticket["status"] == "waiting" else 0

    return jsonify(
        {
            "queue_number": ticket["queue_number"],
            "queue_type": qtype["name"],
            "status": ticket["status"],
            "now_calling": now_calling["queue_number"] if now_calling else "-",
            "people_ahead": ahead,
            "eta_minutes": eta_minutes,
        }
    )
