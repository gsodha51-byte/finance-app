import sqlite3

DB="finance.db"

def db():
    return sqlite3.connect(DB)

def init_db():

    conn=db()
    c=conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        password TEXT,
        role TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS members(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        father TEXT,
        village TEXT,
        mobile TEXT,
        guarantor1 TEXT,
        guarantor2 TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS loans(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account_no TEXT,
        member_id INTEGER,
        loan_amount REAL,
        installment REAL,
        installment_type TEXT,
        disbursement_detail TEXT,
        status TEXT
    )
    """)

    # UPDATED TRANSACTIONS TABLE
    c.execute("""
    CREATE TABLE IF NOT EXISTS transactions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        loan_id INTEGER,
        date TEXT,
        debit REAL,
        credit REAL,
        narration TEXT,
        mode TEXT
    )
    """)

    # GENERAL LEDGER TABLE
    c.execute("""
    CREATE TABLE IF NOT EXISTS general_ledger(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        ledger TEXT,
        debit REAL,
        credit REAL,
        mode TEXT,
        narration TEXT
    )
    """)

    # PERSONAL LEDGER MASTER
    c.execute("""
    CREATE TABLE IF NOT EXISTS personal_ledgers(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT
    )
    """)

    # PERSONAL LEDGER TRANSACTIONS
    c.execute("""
    CREATE TABLE IF NOT EXISTS personal_transactions(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ledger_id INTEGER,
    date TEXT,
    debit REAL,
    credit REAL,
    mode TEXT,
    narration TEXT
    )
    """)
    
    conn.commit()
    conn.close()

def update_db():

    conn=db()
    c=conn.cursor()

    try:
        c.execute("ALTER TABLE transactions ADD COLUMN narration TEXT")
    except:
        pass

    try:
        c.execute("ALTER TABLE members ADD COLUMN document TEXT")
    except:
        pass

    conn.commit()
    conn.close()