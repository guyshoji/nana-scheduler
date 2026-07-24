import sqlite3
import os

DB_PATH = "nana_scheduler.db"
SCHEMA_PATH = os.path.join("src", "db", "schema.sql")

if os.path.exists(DB_PATH):
    print("Database already exists, skipping.")
else:
    with open(SCHEMA_PATH, "r") as f:
        schema = f.read()
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(schema)
    conn.commit()
    conn.close()
    print("Database created successfully.")
