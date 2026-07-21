-- employees.sql

CREATE TABLE employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    max_hours_per_week INTEGER DEFAULT 40
);

CREATE TABLE availability (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL,
    day TEXT NOT NULL,       -- 'Mon', 'Tue', etc.
    hour INTEGER NOT NULL,   -- 11 through 20 (start of each 1-hr slot)
    FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
);

CREATE TABLE staffing_requirements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    location TEXT NOT NULL,
    day TEXT NOT NULL,
    min_needed INTEGER NOT NULL,
    max_needed INTEGER NOT NULL
);