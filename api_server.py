from fastapi import FastAPI
import sqlite3

app = FastAPI()

DB = "finance.db"

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


@app.get("/members")
def members():
    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT id,name,mobile FROM members")

    rows = c.fetchall()

    data = []

    for r in rows:
        data.append(dict(r))

    conn.close()

    return data