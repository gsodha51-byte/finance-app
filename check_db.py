import sqlite3

conn = sqlite3.connect("finance.db")
c = conn.cursor()

for row in c.execute("SELECT account_no,installment_type FROM loans"):
    print(row)

conn.close()