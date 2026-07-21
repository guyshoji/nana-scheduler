import sqlite3

DB_PATH = "nana_scheduler.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def load_employees():
    conn = get_connection()
    cur = conn.execute("SELECT id, name, max_hours_per_week FROM employees")
    employees = cur.fetchall()
    conn.close()
    return employees

def load_availability():
    conn = get_connection()
    cur = conn.execute("""
        SELECT e.name, a.day, a.hour
        FROM availability a
        JOIN employees e ON a.employee_id = e.id
    """)
    rows = cur.fetchall()
    conn.close()

    availability = {}
    for name, day, hour in rows:
        availability.setdefault(name, set()).add((day, hour))
    return availability

def load_location_preferences():
    conn = get_connection()
    cur = conn.execute("SELECT e.name, lp.location, lp.preference_score FROM location_preferences lp JOIN employees e ON lp.employee_id = e.id")
    rows = cur.fetchall()
    conn.close()

    preferences = {}
    for name, location, score in rows:
        preferences[(name, location)] = score
    return preferences

def load_staffing_requirements():
    conn = get_connection()
    cur = conn.execute("SELECT location, day, min_needed, max_needed FROM staffing_requirements")
    rows = cur.fetchall()
    conn.close()

    requirements = {}
    for location, day, min_needed, max_needed in rows:
        requirements[(location, day)] = (min_needed, max_needed)
    return requirements