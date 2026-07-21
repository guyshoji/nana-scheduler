import sqlite3

DB_PATH = "nana_scheduler.db"
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
HOURS = list(range(11, 21))

def seed():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()

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