import sqlite3

conn = sqlite3.connect("finance.db")
c = conn.cursor()

c.execute("DELETE FROM transactions")
c.execute("DELETE FROM loans")
c.execute("DELETE FROM members")

conn.commit()
conn.close()

print("Database cleaned successfully")