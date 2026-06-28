"""
Database module for NagarSeva AI.
SQLite operations: save, duplicate support, upvotes, resolve, citizen
verification (confirm/reopen), department performance, and gamification.
"""

import sqlite3
from datetime import datetime

DB_PATH = "nagarseva.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS issues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            issue_title TEXT NOT NULL,
            category TEXT,
            severity TEXT,
            severity_score INTEGER,
            department TEXT,
            description TEXT,
            location TEXT,
            reporter TEXT DEFAULT 'Anonymous',
            mobile TEXT DEFAULT '',
            status TEXT DEFAULT 'Pending',
            affected_people INTEGER DEFAULT 0,
            report_count INTEGER DEFAULT 1,
            upvotes INTEGER DEFAULT 0,
            impact_score INTEGER DEFAULT 0,
            verification TEXT DEFAULT 'NA',
            lat REAL,
            lon REAL,
            image_path TEXT,
            created_at TEXT,
            resolved_at TEXT
        )
    ''')
    conn.commit()
    conn.close()


def save_issue(data: dict) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO issues
        (issue_title, category, severity, severity_score, department,
         description, location, reporter, mobile, affected_people, impact_score,
         lat, lon, image_path, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data.get("issue_title", "Unknown"),
        data.get("category", "Other"),
        data.get("severity", "Medium"),
        data.get("severity_score", 5),
        data.get("department", "MCD"),
        data.get("description", ""),
        data.get("location", "Not specified"),
        data.get("reporter", "Anonymous"),
        data.get("mobile", ""),
        data.get("affected_people", 0),
        data.get("impact_score", 0),
        data.get("lat"),
        data.get("lon"),
        data.get("image_path"),
        _now(),
    ))
    conn.commit()
    issue_id = cursor.lastrowid
    conn.close()
    return issue_id


def get_issues_by_mobile(mobile: str):
    """Return all issues reported from a given mobile number (for tracking)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM issues WHERE mobile = ? ORDER BY created_at DESC",
                   (mobile,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def get_geolocated_issues():
    """Return issues that have coordinates, for the map view."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM issues WHERE lat IS NOT NULL AND lon IS NOT NULL")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def get_all_issues():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM issues ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_pending_issues():
    """For duplicate detection — compare against open issues only."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM issues WHERE status='Pending' ORDER BY created_at DESC")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def get_issues_by_department(department: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM issues WHERE department = ? ORDER BY created_at DESC",
        (department,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def merge_duplicate(issue_id: int, extra_people: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE issues
        SET report_count = report_count + 1,
            affected_people = affected_people + ?
        WHERE id = ?
    ''', (extra_people, issue_id))
    conn.commit()
    conn.close()


def upvote_issue(issue_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE issues SET upvotes = upvotes + 1 WHERE id = ?", (issue_id,))
    conn.commit()
    conn.close()


def resolve_issue(issue_id: int):
    """Officer marks resolved → status Resolved, awaiting citizen verification."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE issues SET status='Resolved', verification='Pending', resolved_at=? WHERE id=?",
        (_now(), issue_id))
    conn.commit()
    conn.close()


def confirm_resolution(issue_id: int):
    """Citizen confirms the fix is real."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE issues SET verification='Confirmed' WHERE id=?", (issue_id,))
    conn.commit()
    conn.close()


def reopen_issue(issue_id: int):
    """Citizen says it's NOT actually fixed → reopen + flag."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE issues SET status='Pending', verification='Reopened', resolved_at=NULL WHERE id=?",
        (issue_id,))
    conn.commit()
    conn.close()


def get_stats() -> dict:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) AS c FROM issues")
    total = cursor.fetchone()["c"]
    cursor.execute("SELECT COUNT(*) AS c FROM issues WHERE status='Pending'")
    pending = cursor.fetchone()["c"]
    cursor.execute("SELECT COUNT(*) AS c FROM issues WHERE status='Resolved'")
    resolved = cursor.fetchone()["c"]
    cursor.execute("SELECT COUNT(*) AS c FROM issues WHERE verification='Confirmed'")
    confirmed = cursor.fetchone()["c"]
    cursor.execute("SELECT COUNT(*) AS c FROM issues WHERE verification='Reopened'")
    reopened = cursor.fetchone()["c"]
    cursor.execute("SELECT COALESCE(SUM(affected_people),0) AS p FROM issues")
    total_affected = cursor.fetchone()["p"]

    cursor.execute("SELECT category, COUNT(*) AS count FROM issues GROUP BY category ORDER BY count DESC")
    by_category = [dict(r) for r in cursor.fetchall()]
    cursor.execute("SELECT department, COUNT(*) AS count FROM issues GROUP BY department ORDER BY count DESC")
    by_department = [dict(r) for r in cursor.fetchall()]

    conn.close()
    return {
        "total": total, "pending": pending, "resolved": resolved,
        "confirmed": confirmed, "reopened": reopened,
        "total_affected": total_affected,
        "by_category": by_category, "by_department": by_department,
    }


def get_department_stats(department: str) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) AS c FROM issues WHERE department=?", (department,))
    total = cursor.fetchone()["c"]
    cursor.execute("SELECT COUNT(*) AS c FROM issues WHERE department=? AND status='Pending'", (department,))
    pending = cursor.fetchone()["c"]
    cursor.execute("SELECT COUNT(*) AS c FROM issues WHERE department=? AND status='Resolved'", (department,))
    resolved = cursor.fetchone()["c"]
    cursor.execute("SELECT COALESCE(SUM(affected_people),0) AS p FROM issues WHERE department=?", (department,))
    people = cursor.fetchone()["p"]
    conn.close()
    return {"total": total, "pending": pending, "resolved": resolved, "total_affected": people}


def get_area_stats():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT location, COUNT(*) AS issue_count,
               COALESCE(SUM(affected_people),0) AS people,
               COALESCE(SUM(upvotes),0) AS upvotes
        FROM issues GROUP BY location ORDER BY issue_count DESC LIMIT 10
    ''')
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def get_priority_queue():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT *,
               (severity_score * 10 + upvotes * 5 + report_count * 3
                + affected_people / 20) AS priority
        FROM issues WHERE status='Pending'
        ORDER BY priority DESC LIMIT 10
    ''')
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def get_department_performance():
    """
    Avg resolution time (hours) per department, computed from
    resolved_at - created_at for confirmed/resolved issues.
    Returns list of dicts: department, resolved_count, avg_hours.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT department,
               COUNT(*) AS resolved_count,
               AVG((julianday(resolved_at) - julianday(created_at)) * 24) AS avg_hours
        FROM issues
        WHERE resolved_at IS NOT NULL
        GROUP BY department
        ORDER BY avg_hours ASC
    ''')
    rows = []
    for r in cursor.fetchall():
        d = dict(r)
        d["avg_hours"] = round(d["avg_hours"], 1) if d["avg_hours"] else 0
        rows.append(d)
    conn.close()
    return rows


def get_citizen_points(reporter: str) -> dict:
    """
    Gamification: points for a citizen.
    Report = 10, each upvote received = 2, confirmed resolution = 50 bonus.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT COUNT(*) AS reports,
               COALESCE(SUM(upvotes),0) AS upvotes,
               COALESCE(SUM(CASE WHEN verification='Confirmed' THEN 1 ELSE 0 END),0) AS confirmed
        FROM issues WHERE reporter = ?
    ''', (reporter,))
    row = dict(cursor.fetchone())
    conn.close()

    points = row["reports"] * 10 + row["upvotes"] * 2 + row["confirmed"] * 50

    if points >= 200:
        badge, title = "🏆", "Civic Champion"
    elif points >= 100:
        badge, title = "🥇", "Community Hero"
    elif points >= 50:
        badge, title = "🥈", "Active Citizen"
    elif points >= 10:
        badge, title = "🥉", "Rising Reporter"
    else:
        badge, title = "🌱", "New Citizen"

    return {
        "points": points, "reports": row["reports"],
        "upvotes": row["upvotes"], "confirmed": row["confirmed"],
        "badge": badge, "title": title,
    }


def get_leaderboard(limit=5):
    """Top citizens by points (computed in SQL)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT reporter,
               COUNT(*) * 10
               + COALESCE(SUM(upvotes),0) * 2
               + COALESCE(SUM(CASE WHEN verification='Confirmed' THEN 1 ELSE 0 END),0) * 50 AS points,
               COUNT(*) AS reports
        FROM issues
        WHERE reporter IS NOT NULL AND reporter != 'Anonymous'
        GROUP BY reporter
        ORDER BY points DESC
        LIMIT ?
    ''', (limit,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


if __name__ == "__main__":
    init_db()
    print("Database ready!")