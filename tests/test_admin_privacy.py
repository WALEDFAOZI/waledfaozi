from otaku_bot import config
from tests.harness import Harness


def test_admin_never_in_public_boards(tmp_path):
    h = Harness(tmp_path)
    db = h.db
    db.upsert_user(1, "OwnerName"); db.upsert_user(2, "Sara")
    db.add_admin(1) if hasattr(db, "add_admin") else None
    with db.conn:
        db.conn.execute("UPDATE users SET best_score=9.9, best_sudden=50 WHERE tg_id=1")
        db.conn.execute("UPDATE users SET best_score=5.0, best_sudden=3 WHERE tg_id=2")
    assert db.is_admin(1)
    names = [r["name"] for r in db.leaderboard(10)] + [r["name"] for r in db.sudden_leaderboard(10)]
    assert "OwnerName" not in names and "Sara" in names
