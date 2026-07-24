import sqlite3

DB_PATH = "nana_scheduler.db"
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
HOURS = list(range(11, 21))

def seed():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM employees")
    if cur.fetchone()[0] > 0:
        print("Database already has data — aborting seed to avoid overwriting.")
        conn.close()
        return
    
    conn.execute("PRAGMA foreign_keys = ON")

    # Clear existing data so this script is safely re-runnable
    cur.execute("DELETE FROM availability")
    cur.execute("DELETE FROM employees")
    cur.execute("DELETE FROM staffing_requirements")

    # --- Employees + availability ---
    employee_availability = {
        "Alice":  {(d, h) for d in DAYS for h in HOURS},
        "Ben":    {(d, h) for d in ["Mon","Tue","Wed","Thu","Fri"] for h in HOURS},
        "Carla":  {(d, h) for d in DAYS for h in HOURS},
        "Dan":    {(d, h) for d in DAYS for h in HOURS},
        "Elena":  {(d, h) for d in DAYS for h in HOURS} - {("Fri", h) for h in range(17, 21)} - {("Sat", h) for h in range(17, 21)},
        "Frank":  {(d, h) for d in DAYS for h in HOURS},
        "Gina":   {(d, h) for d in DAYS for h in range(11, 17)},
        "Hank":   {(d, h) for d in DAYS for h in HOURS},
        "Ivy":    {(d, h) for d in DAYS for h in range(17, 21)},
        "Jack":   {(d, h) for d in DAYS for h in HOURS},
        "Kim":    {(d, h) for d in ["Sat","Sun"] for h in HOURS},
        "Leo":    {(d, h) for d in ["Sat","Sun"] for h in HOURS},
        "Mia":    {(d, h) for d in DAYS for h in HOURS},
        "Noah":   {(d, h) for d in DAYS for h in HOURS},
        "Oscar":  {(d, h) for d in DAYS for h in HOURS},
        "Peter":  {(d, h) for d in DAYS for h in HOURS},
        "Quinn":  {(d, h) for d in DAYS for h in HOURS},
        "Ruby":   {(d, h) for d in DAYS for h in HOURS},
        "Sam":    {(d, h) for d in DAYS for h in HOURS},
        "Tom":    {(d, h) for d in DAYS for h in HOURS}
    }

    for name, avail in employee_availability.items():
        cur.execute(
            "INSERT INTO employees (name, max_hours_per_week) VALUES (?, ?)",
            (name, 40)
        )
        employee_id = cur.lastrowid
        for (day, hour) in avail:
            cur.execute(
                "INSERT INTO availability (employee_id, day, hour) VALUES (?, ?, ?)",
                (employee_id, day, hour)
            )

    # --- Location preferences ---
    # Simple placeholder pattern: a few employees have real preferences, rest are neutral
    location_preferences = {
        "Alice":  {"Big Stand": 2, "Marina": 0},   # strongly prefers Big Stand
        "Carla":  {"Big Stand": 0, "Marina": 2},   # strongly prefers Marina
        "Dan":    {"Big Stand": 1, "Marina": 0},   # slightly prefers Big Stand
        "Gina":   {"Big Stand": -1, "Marina": 1},  # dislikes Big Stand, prefers Marina
        # everyone else defaults to neutral (0) for both locations
    }

    for name in employee_availability:  # ensures every employee gets a row for every location
        cur.execute("SELECT id FROM employees WHERE name = ?", (name,))
        employee_id = cur.fetchone()[0]
        prefs = location_preferences.get(name, {})
        for loc in ["Big Stand", "Marina"]:
            score = prefs.get(loc, 0)
            cur.execute(
                "INSERT INTO location_preferences (employee_id, location, preference_score) VALUES (?, ?, ?)",
                (employee_id, loc, score)
            )

    # --- Staffing requirements ---
    for d in DAYS:
        is_weekend = d in ("Sat", "Sun")
        big_stand_min, big_stand_max = (8, 10) if is_weekend else (5, 5)
        cur.execute(
            "INSERT INTO staffing_requirements (location, day, min_needed, max_needed) VALUES (?, ?, ?, ?)",
            ("Big Stand", d, big_stand_min, big_stand_max)
        )
        cur.execute(
            "INSERT INTO staffing_requirements (location, day, min_needed, max_needed) VALUES (?, ?, ?, ?)",
            ("Marina", d, 3, 3)
        )

    conn.commit()
    conn.close()
    print("Database seeded successfully.")

if __name__ == "__main__":
    seed()