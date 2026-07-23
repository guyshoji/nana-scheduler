import sqlite3

DB_PATH = "nana_scheduler.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def load_employees():
    conn = get_connection()
    cur = conn.execute("SELECT id, name, max_hours_per_week, is_mopper FROM employees")
    employees = cur.fetchall()
    conn.close()
    return employees

def load_availability():
    conn = get_connection()
    cur = conn.execute("SELECT name FROM employees")
    all_names = [row[0] for row in cur.fetchall()]

    availability = {name: set() for name in all_names}

    cur = conn.execute("""
        SELECT e.name, a.day, a.hour
        FROM availability a
        JOIN employees e ON a.employee_id = e.id
    """)
    rows = cur.fetchall()
    conn.close()

    for name, day, hour in rows:
        availability[name].add((day, hour))

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
    """Returns {(location, day, hour): (min_needed, max_needed)} for the solver."""
    conn = get_connection()
    cur = conn.execute("SELECT location, day, hour, min_needed FROM staffing_requirements")
    rows = cur.fetchall()
    conn.close()

    requirements = {}
    for location, day, hour, min_needed in rows:
        requirements[(location, day, hour)] = min_needed
    return requirements

def add_employee(name, max_hours=40):
    conn = get_connection()
    conn.execute(
        "INSERT INTO employees (name, max_hours_per_week) VALUES (?, ?)",
        (name, max_hours)
    )
    conn.commit()
    conn.close()

def delete_employee(employee_id):
    conn = get_connection()
    conn.execute("DELETE FROM employees WHERE id = ?", (employee_id,))
    conn.commit()
    conn.close()

def update_employee(employee_id, name, max_hours):
    conn = get_connection()
    conn.execute(
        "UPDATE employees SET name = ?, max_hours_per_week = ? WHERE id = ?",
        (name, max_hours, employee_id)
    )
    conn.commit()
    conn.close()

def get_employee_by_id(employee_id):
    conn = get_connection()
    cur = conn.execute(
        "SELECT id, name, max_hours_per_week, is_mopper FROM employees WHERE id = ?",
        (employee_id,)
    )
    row = cur.fetchone()
    conn.close()
    return row

def set_availability(employee_id, availability_set):
    """Replaces an employee's entire availability with the given set of (day, hour) tuples."""
    conn = get_connection()
    conn.execute("DELETE FROM availability WHERE employee_id = ?", (employee_id,))
    for (day, hour) in availability_set:
        conn.execute(
            "INSERT INTO availability (employee_id, day, hour) VALUES (?, ?, ?)",
            (employee_id, day, hour)
        )
    conn.commit()
    conn.close()

def get_availability_for_employee(employee_id):
    conn = get_connection()
    cur = conn.execute(
        "SELECT day, hour FROM availability WHERE employee_id = ?",
        (employee_id,)
    )
    rows = cur.fetchall()
    conn.close()
    return set(rows)

def set_location_preferences(employee_id, preferences_dict):
    """preferences_dict = {location: score}"""
    conn = get_connection()
    for location, score in preferences_dict.items():
        conn.execute("""
            INSERT INTO location_preferences (employee_id, location, preference_score)
            VALUES (?, ?, ?)
            ON CONFLICT(employee_id, location) DO UPDATE SET preference_score = excluded.preference_score
        """, (employee_id, location, score))
    conn.commit()
    conn.close()

def get_preferences_for_employee(employee_id):
    conn = get_connection()
    cur = conn.execute(
        "SELECT location, preference_score FROM location_preferences WHERE employee_id = ?",
        (employee_id,)
    )
    rows = cur.fetchall()
    conn.close()
    return dict(rows)

def set_mopper_status(employee_id, is_mopper):
    conn = get_connection()
    conn.execute(
        "UPDATE employees SET is_mopper = ? WHERE id = ?",
        (1 if is_mopper else 0, employee_id)
    )
    conn.commit()
    conn.close()

def load_moppers():
    """Returns a set of employee names designated as moppers."""
    conn = get_connection()
    cur = conn.execute(
        "SELECT name FROM employees WHERE is_mopper = 1"
    )
    names = {row[0] for row in cur.fetchall()}
    conn.close()
    return names

def load_staffing_requirements_grid():
    """Returns {(location, day, hour): (min_needed, max_needed)} for UI display."""
    conn = get_connection()
    cur = conn.execute("SELECT location, day, hour, min_needed FROM staffing_requirements")
    rows = cur.fetchall()
    conn.close()
    return {(loc, day, hour): mn for loc, day, hour, mn in rows}

def set_staffing_requirement(location, day, hour, min_needed):
    conn = get_connection()
    conn.execute("""
        INSERT INTO staffing_requirements (location, day, hour, min_needed)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(location, day, hour) DO UPDATE SET
            min_needed = excluded.min_needed
    """, (location, day, hour, min_needed))
    conn.commit()
    conn.close()
