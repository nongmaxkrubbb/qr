import io
import base64
import qrcode
from datetime import datetime

def next_queue_number(db, queue_type_id, prefix):
    today = datetime.now().strftime("%Y-%m-%d")
    cur = db.execute(
        """SELECT COUNT(*) as cnt FROM tickets
           WHERE queue_type_id = ? AND date(created_at) = ?""",
        (queue_type_id, today),
    )
    count = cur.fetchone()["cnt"] + 1
    return f"{prefix}{count:03d}"

def avg_service_seconds(db, queue_type_id):
    cur = db.execute(
        """SELECT called_at, completed_at FROM tickets
           WHERE queue_type_id = ? AND completed_at IS NOT NULL AND called_at IS NOT NULL
           ORDER BY completed_at DESC LIMIT 20""",
        (queue_type_id,),
    )
    rows = cur.fetchall()
    if not rows:
        return 600  # default guess: 10 minutes
    total = 0
    n = 0
    for row in rows:
        try:
            called = datetime.fromisoformat(row["called_at"])
            completed = datetime.fromisoformat(row["completed_at"])
            diff = (completed - called).total_seconds()
            if diff > 0:
                total += diff
                n += 1
        except (ValueError, TypeError):
            continue
    return int(total / n) if n else 600

def people_ahead(db, ticket):
    cur = db.execute(
        """SELECT COUNT(*) as cnt FROM tickets
           WHERE queue_type_id = ? AND status = 'waiting' AND id < ?""",
        (ticket["queue_type_id"], ticket["id"]),
    )
    return cur.fetchone()["cnt"]

def make_qr_base64(url):
    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")
