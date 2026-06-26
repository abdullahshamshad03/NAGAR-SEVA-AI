import sqlite3
from datetime import datetime

def get_connection():
    conn = sqlite3.connect("nagarseva.db")
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
            created_at TEXT
        )
    ''')
    
    conn.commit()
    conn.close()
    print("Database ready!")

def save_issue(data: dict):
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO issues 
        (issue_title, category, severity, severity_score, 
         department, description, location, affected_people, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data.get("issue_title", "Unknown"),
        data.get("category", "Other"),
        data.get("severity", "Medium"),
        data.get("severity_score", 5),
        data.get("department", "Unknown"),
        data.get("description", ""),
        data.get("location", "Not specified"),
        data.get("affected_people", 0),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    
    conn.commit()
    issue_id = cursor.lastrowid
    conn.close()
    return issue_id

def get_all_issues():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM issues ORDER BY created_at DESC")
    issues = cursor.fetchall()
    conn.close()
    return issues

def get_stats():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) as total FROM issues")
    total = cursor.fetchone()["total"]
    
    cursor.execute("SELECT COUNT(*) as pending FROM issues WHERE status='Pending'")
    pending = cursor.fetchone()["pending"]
    
    cursor.execute("SELECT COUNT(*) as resolved FROM issues WHERE status='Resolved'")
    resolved = cursor.fetchone()["resolved"]
    
    cursor.execute("SELECT category, COUNT(*) as count FROM issues GROUP BY category")
    by_category = cursor.fetchall()
    
    conn.close()
    
    return {
        "total": total,
        "pending": pending,
        "resolved": resolved,
        "by_category": [dict(row) for row in by_category]
    }

# Pehli baar run karo toh DB ban jaaye
if __name__ == "__main__":
    init_db()