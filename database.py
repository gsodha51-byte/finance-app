import psycopg2

import os
from dotenv import load_dotenv

load_dotenv()

def db():
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
        port=5432,
        sslmode="require"
    )
    return conn
def init_db():

    conn=db()
    c=conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id SERIAL PRIMARY KEY,
        username TEXT,
        password TEXT,
        role TEXT,
        mobile TEXT,
        email TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS members(
        id SERIAL PRIMARY KEY,
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
        id SERIAL PRIMARY KEY,
        account_no TEXT,
        member_id INTEGER REFERENCES members(id) ON DELETE CASCADE,
        loan_amount REAL,
        installment REAL,
        installment_type TEXT,
        disbursement_detail TEXT,
        status TEXT,
        start_date DATE DEFAULT CURRENT_DATE
    )
    """)

    # UPDATED TRANSACTIONS TABLE
    c.execute("""
    CREATE TABLE IF NOT EXISTS transactions(
        id SERIAL PRIMARY KEY,
        loan_id INTEGER REFERENCES loans(id) ON DELETE CASCADE,
        date TIMESTAMP,
        debit REAL,
        credit REAL,
        narration TEXT,
        mode TEXT
    )
    """)

    # GENERAL LEDGER TABLE
    c.execute("""
    CREATE TABLE IF NOT EXISTS general_ledger(
        id SERIAL PRIMARY KEY,
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
        id SERIAL PRIMARY KEY,
        name TEXT
    )
    """)

    # PERSONAL LEDGER TRANSACTIONS
    c.execute("""
    CREATE TABLE IF NOT EXISTS personal_transactions(
        id SERIAL PRIMARY KEY,
    ledger_id INTEGER,
    date TEXT,
    debit REAL,
    credit REAL,
    mode TEXT,
    narration TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS ledger_master(
        id SERIAL PRIMARY KEY,
        name TEXT UNIQUE
    )
    """)

    # 🔥 LOAN DETAILS TABLE (DOCUMENT STORAGE)
    c.execute("""
    CREATE TABLE IF NOT EXISTS loan_details(
        id SERIAL PRIMARY KEY,
        account_id INTEGER REFERENCES loans(id) ON DELETE CASCADE,
        document TEXT
    )
    """)
    
    conn.commit()
    conn.close()

def update_db():

    conn = db()
    c = conn.cursor()

    try:
        c.execute("ALTER TABLE transactions ADD COLUMN narration TEXT")
    except:
        pass

    try:
        c.execute("""
        ALTER TABLE loans
        ADD CONSTRAINT fk_member
        FOREIGN KEY (member_id) REFERENCES members(id)
        """)
    except:
        pass

    conn.commit()
    conn.close()

    # 🔥 ADD FOREIGN KEY: transactions → loans
    try:
        c.execute("""
        ALTER TABLE transactions
        ADD CONSTRAINT fk_loan
        FOREIGN KEY (loan_id) REFERENCES loans(id)
        ON DELETE CASCADE
        """)
    except:
        pass

    conn.commit()
    conn.close()

def add_to_general_ledger(date, ledger, debit, credit, mode, narration):
    conn = db()
    c = conn.cursor()

    c.execute("""
    INSERT INTO general_ledger(date, ledger, debit, credit, mode, narration)
    VALUES(%s, %s, %s, %s, %s, %s)
    """, (date, ledger, debit, credit, mode, narration))

    conn.commit()
    conn.close()

def create_admin():
    conn = db()
    c = conn.cursor()

    c.execute("SELECT * FROM users WHERE username='admin'")
    if c.fetchone():
        return

    c.execute("""
    INSERT INTO users(username, password, role, mobile, email)
    VALUES(%s, %s, %s, %s, %s)
    """, ("admin", "admin123", "admin", "9468551100", "gsodha51@gmail.com"))

    conn.commit()
    conn.close()

create_admin()