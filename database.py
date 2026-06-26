"""
Database module for NagarSeva AI.
Handles all SQLite operations: save, duplicate detection support,
upvotes, resolve, stats, and area-based insights.
"""

import sqlite3
from datetime import datetime

DB_PATH = "nagarseva.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


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
            status TEXT DEFAULT 'Pending',
            affected_people INTEGER DEFAULT 0,
            report_count INTEGER DEFAULT 1,
            upvotes INTEGER DEFAULT 0,
            impact_score INTEGER DEFAULT 0,
            created_at TEXT
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
         description, location, affected_people, impact_score, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data.get("issue_title", "Unknown"),
        data.get("category", "Other"),
        data.get("severity", "Medium"),
        data.get("severity_score", 5),
        data.get("department", "MCD"),
        data.get("description", ""),
        data.get("location", "Not specified"),
        data.get("affected_people", 0),
        data.get("impact_score", 0),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    ))
    conn.commit()
    issue_id = cursor.lastrowid
    conn.close()
    return issue_id


def get_all_issues():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM issues ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_pending_issues():
    """Used for duplicate detection — only compare against open issues."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM issues WHERE status='Pending' ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def merge_duplicate(issue_id: int, extra_people: int):
    """When a duplicate is detected, bump report_count + affected_people."""
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
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE issues SET status = 'Resolved' WHERE id = ?", (issue_id,))
    conn.commit()
    conn.close()


def get_stats() -> dict:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) AS total FROM issues")
    total = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) AS pending FROM issues WHERE status='Pending'")
    pending = cursor.fetchone()["pending"]

    cursor.execute("SELECT COUNT(*) AS resolved FROM issues WHERE status='Resolved'")
    resolved = cursor.fetchone()["resolved"]

    cursor.execute("SELECT COALESCE(SUM(affected_people),0) AS people FROM issues")
    total_affected = cursor.fetchone()["people"]

    cursor.execute("SELECT category, COUNT(*) AS count FROM issues GROUP BY category ORDER BY count DESC")
    by_category = [dict(r) for r in cursor.fetchall()]

    cursor.execute("SELECT department, COUNT(*) AS count FROM issues GROUP BY department ORDER BY count DESC")
    by_department = [dict(r) for r in cursor.fetchall()]

    conn.close()
    return {
        "total": total,
        "pending": pending,
        "resolved": resolved,
        "total_affected": total_affected,
        "by_category": by_category,
        "by_department": by_department,
    }


def get_area_stats():
    """Group issues by location for the heatmap / most-affected-areas view."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT location,
               COUNT(*) AS issue_count,
               COALESCE(SUM(affected_people),0) AS people,
               COALESCE(SUM(upvotes),0) AS upvotes
        FROM issues
        GROUP BY location
        ORDER BY issue_count DESC
        LIMIT 10
    ''')
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def get_priority_queue():
    """
    Smart priority sorting: combines severity_score, upvotes, and affected_people.
    Returns pending issues sorted by a computed priority score.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT *,
               (severity_score * 10 + upvotes * 5 + report_count * 3
                + affected_people / 20) AS priority
        FROM issues
        WHERE status = 'Pending'
        ORDER BY priority DESC
        LIMIT 10
    ''')
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


if __name__ == "__main__":
    init_db()
    print("Database ready!")