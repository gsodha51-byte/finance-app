from fastapi import FastAPI, UploadFile, File
from database import db, add_to_general_ledger, init_db
from fastapi.staticfiles import StaticFiles
from database import db
import os
from datetime import datetime, timedelta, date
from passlib.hash import bcrypt
from backup_system import backup_database

from apscheduler.schedulers.background import BackgroundScheduler

import shutil
import random
import time
import requests
import smtplib
from email.mime.text import MIMEText

otp_store = {}

def send_email_otp(to_email, otp):

    sender_email = "gsodha51@gmail.com"
    sender_password = "moqyoiueeaugahem"

    msg = MIMEText(f"Your OTP is: {otp}")
    msg["Subject"] = "OTP Verification"
    msg["From"] = sender_email
    msg["To"] = to_email

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        print("Email sent")

    except Exception as e:
        print("Email error:", e)

def create_backup():

    try:
        folder = "backups/" + datetime.now().strftime("%Y-%m")
        os.makedirs(folder, exist_ok=True)

        filename = "backup_" + datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".db"

        src = "finance.db"   # ⚠️ apna DB naam check karo
        dst = os.path.join(folder, filename)

        shutil.copy2(src, dst)

        return {"status": "ok", "file": filename}

    except Exception as e:
        return {"status": "error", "msg": str(e)}

app = FastAPI()

# ---------------- INIT ----------------
if not os.path.exists("uploads"):
    os.mkdir("uploads")

backup_database()

init_db()

# ---------------- HOME ----------------
@app.get("/api")
def home():
    return {"message": "API chal rahi hai 🚀"}

@app.get("/backup")
def backup_now():

    result = create_backup()

    return result


# ---------------- MEMBERS ----------------
@app.get("/members")
def get_members():
    conn = db()
    c = conn.cursor()

    c.execute("SELECT id,name,mobile FROM members")
    rows = c.fetchall()

    conn.close()

    return [
        {"id": r[0], "name": r[1], "mobile": r[2]}
        for r in rows
    ]

@app.get("/loans")
def get_loans():

    conn = db()
    c = conn.cursor()

    c.execute("""
    SELECT 
        loans.id,
        members.name,
        loans.loan_amount,
        loans.installment,
        COALESCE(SUM(transactions.credit - transactions.debit),0)
    FROM loans
    JOIN members ON loans.member_id = members.id
    LEFT JOIN transactions ON transactions.loan_id = loans.id
    WHERE loans.status='Running'
    GROUP BY loans.id, members.name, loans.loan_amount, loans.installment
    """)

    rows = c.fetchall()

    data = []

    for r in rows:
        paid = r[4]
        pending = r[2] - paid

        data.append({
            "loan_id": r[0],
            "name": r[1],
            "loan": r[2],
            "installment": r[3],
            "paid": paid,
            "pending": pending
        })

    conn.close()
    return data


# ---------------- ADD MEMBER + LOAN ----------------
from fastapi import Request

@app.post("/add-full-member")
async def add_full_member(request: Request):

    data = await request.json()

    name = data.get("name")
    father = data.get("father", "")
    village = data.get("village", "")
    mobile = data.get("mobile", "")
    g1 = data.get("g1", "")
    g2 = data.get("g2", "")
    amount = float(data.get("amount", 0))
    start_date = data.get("start_date")
    inst = float(data.get("inst", 0))
    loan_type = data.get("type", "Daily")
    doc = ""

    conn = db()
    c = conn.cursor()

    # ✅ STEP 2: पहले check करो member exist है या नहीं (mobile से)

    c.execute("SELECT id FROM members WHERE mobile=%s", (mobile,))
    existing = c.fetchone()

    if existing:
        # 👉 पुराना member (CIF reuse)
        member_id = existing[0]
    else:
        # 👉 नया member create
        c.execute("""
        INSERT INTO members(name,father,village,mobile)
        VALUES (%s,%s,%s,%s)
        RETURNING id
        """, (name, father, village, mobile))

        member_id = c.fetchone()[0]

   # ✅ DDS को loan में मत डालो
    loan_type = data.get("type", "Daily")

    if loan_type != "DDS":

        c.execute("SELECT COUNT(*) FROM loans")
        n = c.fetchone()[0] + 1
        acc = f"ACC{str(n).zfill(3)}"

        c.execute("""
        INSERT INTO loans(account_no,member_id,loan_amount,installment,installment_type,status,start_date)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (
            acc, member_id, amount, inst, loan_type, "Running",
            start_date if start_date else datetime.now().date()
        ))

    conn.commit()
    conn.close()

    return {"status": "ok"}

@app.get("/find-member")
def find_member(mobile: str):

    conn = db()
    c = conn.cursor()

    c.execute("""
    SELECT id, name, father, village 
    FROM members 
    WHERE mobile=%s
    """, (mobile,))

    row = c.fetchone()
    conn.close()

    if row:
        return {
            "found": True,
            "id": row[0],
            "name": row[1],
            "father": row[2],
            "village": row[3]
        }
    else:
        return {"found": False}

# ---------------- FAST COLLECTION ----------------
@app.get("/fast-collection")
def fast_collection(type: str = "Daily"):

    conn = db()
    c = conn.cursor()

    today = datetime.now().date()

    # 🔹 last 10 days/months
    if type == "Monthly":
        last_days = []
        for i in range(10, 0, -1):
            d = today.replace(day=1) - timedelta(days=30*i)
            last_days.append(d.strftime("%Y-%m"))
    else:
        last_days = [(today - timedelta(days=i)) for i in range(10, 0, -1)]

    min_date = last_days[0]

    # 🔥 ALL TRANSACTIONS IN ONE QUERY
    if type == "Monthly":
        c.execute("""
        SELECT loan_id,
               TO_CHAR(date::date, 'YYYY-MM') as d,
               SUM(credit - debit)
        FROM transactions
        WHERE date::date >= %s
        GROUP BY loan_id, d
        """, (str(min_date) + "-01",))
    else:
        c.execute("""
        SELECT loan_id,
               DATE(date::date) as d,
               SUM(credit - debit)
        FROM transactions
        WHERE date::date >= %s
        GROUP BY loan_id, d
        """, (min_date,))

    rows = c.fetchall()

    # 🔹 DATA MAP (fast lookup)
    data_map = {}
    for r in rows:
        loan_id, d, amt = r
        if loan_id not in data_map:
            data_map[loan_id] = {}
        data_map[loan_id][str(d)] = amt or 0

    # 🔹 LOANS
    c.execute("""
        SELECT loans.id, loans.account_no, members.name, members.mobile,
        loans.loan_amount, loans.installment, loan_details.document,
        loans.start_date
    FROM loans
    JOIN members ON loans.member_id = members.id
    LEFT JOIN loan_details ON loan_details.account_id = loans.id
    WHERE loans.status='Running' AND LOWER(loans.installment_type)=LOWER(%s)
    ORDER BY loans.id ASC
    """, (type,))

    loans = c.fetchall()

    result = []

    for r in loans:
        loan_id = r[0]

        last10 = []

        for d in last_days:
            key = str(d) if type != "Monthly" else d
            last10.append(data_map.get(loan_id, {}).get(str(key), 0))

        # 🔹 TODAY
        today_key = today.strftime("%Y-%m-%d") if type != "Monthly" else today.strftime("%Y-%m")
        today_amt = data_map.get(loan_id, {}).get(today_key, 0)

        # 🔹 TOTAL
        total = today_amt + sum(last10)

        loan_amount = r[4] or 0
        pending = max((r[4] or 0) - total, 0)

        # 🔹 EXPECTED
        start_date = r[7]
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()

        diff_days = max((today - start_date).days, 0)

        if type == "Monthly":
            months = diff_days // 30
            expected = months * r[5]
        else:
            expected = diff_days * r[5]

        today_pending = max(expected - total, 0)

        result.append({
            "loan_id": loan_id,
            "account": r[1],
            "name": r[2],
            "mobile": r[3],
            "loan": r[4],
            "inst": r[5],
            "doc": r[6],
            "start_date": str(r[7]),
            "expected": expected,
            "today_pending": today_pending,
            "last10": last10,
            "today": today_amt,
            "total": total,
            "pending": pending
        })

    conn.close()
    return result

# ---------------- COLLECTION ----------------
from fastapi import Request

@app.post("/collect")
async def collect(request: Request):

    data = await request.json()

    loan_id = data.get("loan_id")
    amount = float(data.get("amount"))
    mode = data.get("mode")

    conn = db()
    c = conn.cursor()

    c.execute("""
    INSERT INTO transactions (loan_id,date,debit,credit,narration,mode)
    VALUES (%s,NOW(),%s,%s,%s,%s)
    """, (
        loan_id,
        0,
        amount,
        "Installment",
        mode
    ))

    add_to_general_ledger(
        date=datetime.now(),
        ledger="Loan Collection",
        debit=0,
        credit=amount,
        mode=mode,
        narration="Loan Collection"
    )

    conn.commit()
    conn.close()

    return {"status": "ok"}
    
import uuid

@app.post("/add-gl")
async def add_gl(data: dict):

    conn = db()
    c = conn.cursor()

    account = data["account"]
    type = data["type"]
    amount = float(data["amount"])
    mode = data["mode"]
    note = data.get("note","")

    # 🔥 same voucher_id for both entries
    voucher_id = str(uuid.uuid4())

    cash_account = "Cash" if mode == "Cash" else "Bank"

    if type == "Payment":

        # party debit
        c.execute("""
        INSERT INTO general_ledger(date, ledger, debit, credit, mode, narration, voucher_id)
        VALUES(NOW(), %s, %s, 0, %s, %s, %s)
        """, (account, amount, mode, note, voucher_id))

        # cash credit
        c.execute("""
        INSERT INTO general_ledger(date, ledger, debit, credit, mode, narration, voucher_id)
        VALUES(NOW(), %s, 0, %s, %s, %s, %s)
        """, (cash_account, amount, mode, f"By {account}", voucher_id))

    else:

        # bank/cash debit
        c.execute("""
        INSERT INTO general_ledger (date, ledger, debit, credit, mode, narration, voucher_id)
        VALUES (NOW(), %s, %s, 0, %s, %s, %s)
        """, (cash_account, amount, mode, f"From {account}", voucher_id))

        # party credit (FIX)
        c.execute("""
        INSERT INTO general_ledger (date, ledger, debit, credit, mode, narration, voucher_id)
        VALUES (NOW(), %s, 0, %s, %s, %s, %s)
        """, (account, amount, mode, f"From {account}", voucher_id))

    conn.commit()
    conn.close()

    return {"status":"ok"}

@app.post("/add-ledger")
async def add_ledger(data: dict):

    conn = db()
    c = conn.cursor()

    name = data.get("name")
    opening = float(data.get("opening", 0))
    typ = data.get("type", "dr")

    try:
        # 1️⃣ ledger create
        c.execute("""
        INSERT INTO ledger_master(name)
        VALUES(%s)
        """, (name,))

        # 2️⃣ opening balance entry
        if opening > 0:

            if typ == "dr":
                debit = opening
                credit = 0
            else:
                debit = 0
                credit = opening

            c.execute("""
            INSERT INTO general_ledger(date, ledger, debit, credit, mode, narration, voucher_id)
            VALUES(NOW(), %s, %s, %s, %s, %s, %s)
            """, (
                name,
                debit,
                credit,
                "Opening",
                "Opening Balance",
                "OPEN-"+name
            ))

        conn.commit()
        return {"status": "ok"}

    except Exception as e:
        conn.rollback()
        return {"status": "error", "msg": "Ledger already exists"}

    finally:
        conn.close()

@app.get("/ledgers")
def get_ledgers():

    conn = db()
    c = conn.cursor()

    c.execute("SELECT name FROM ledger_master")
    data = c.fetchall()

    conn.close()

    return [d[0] for d in data]

@app.get("/ledger-detail")
def ledger_detail(name: str = None, voucher_id: str = None):

    conn = db()
    c = conn.cursor()

    if voucher_id:
        c.execute("""
        SELECT id, date, ledger, debit, credit, mode, narration, voucher_id
        FROM general_ledger
        WHERE voucher_id=%s
        """, (voucher_id,))
    else:
        c.execute("""
        SELECT id, date, ledger, debit, credit, mode, narration, voucher_id
        FROM general_ledger
        WHERE LOWER(ledger)=LOWER(%s)
        ORDER BY date
        """, (name,))

    rows = c.fetchall()

    data = []

    for r in rows:
        data.append({
            "id": r[0],
            "date": str(r[1]).split(" ")[0],
            "ledger": r[2],   # 👈 सही
            "debit": r[3],
            "credit": r[4],
            "mode": r[5],
            "narration": r[6],
            "voucher_id": r[7]
        })

    conn.close()
    return data


# ---------------- FILE UPLOAD ----------------
from typing import List
from fastapi import UploadFile, File
import os, shutil

@app.post("/upload-doc")
def upload_doc(loan_id: int, files: List[UploadFile] = File(...)):

    folder = f"uploads/loan_{loan_id}"
    os.makedirs(folder, exist_ok=True)

    for file in files:
        file_path = f"{folder}/{file.filename}"
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    
    
    # 🔥 DB में filename save
    conn = db()
    c = conn.cursor()

    c.execute("""
        UPDATE loan_details
        SET document=%s
        WHERE account_id=%s
    """, (file.filename, loan_id))

    conn.commit()
    conn.close()

    return {"filename": file.filename}

# ---------------- LEDGER DATA ----------------
@app.get("/ledger-data")
def ledger_data(loan_id: int):

    conn = db()
    c = conn.cursor()

    # Member + Loan
    c.execute("""
    SELECT members.name, members.mobile,
           loans.account_no,
           loans.loan_amount, loans.installment,
           loans.start_date
    FROM loans
    JOIN members ON loans.member_id = members.id
    WHERE loans.id=%s
    """,(loan_id,))
    m = c.fetchone()

    # Transactions
    c.execute("""
    SELECT id, date, debit, credit, mode, narration
    FROM transactions
    WHERE loan_id=%s
    ORDER BY date
    """,(loan_id,))
    rows = c.fetchall()

    # 🔥 First entry (loan)
    ledger_rows = []

    # Add transactions
    for r in rows:
        ledger_rows.append({
            "id": r[0],
            "date": str(r[1]).split(" ")[0],
            "debit": r[2],
            "credit": r[3],
            "mode": r[4],
            "narration": r[5]
        })

    conn.close()

    return {
        "name": m[0],
        "mobile": m[1],
        "account_no": m[2],
        "loan": m[3],
        "inst": m[4],
        "start_date": str(m[5]),
        "rows": ledger_rows   # 🔥 ये missing था
    }


# ---------------- ADD DEBIT ----------------
@app.post("/add-debit")
def add_debit(loan_id: int, amount: float, note: str = ""):

    conn = db()
    c = conn.cursor()

    c.execute("""
    INSERT INTO transactions (loan_id,date,debit,credit,narration,mode)
    VALUES (%s,NOW(),%s,%s,%s,%s)
    """, (
        loan_id,
        amount,
        0,
        note,
        "Cash"
    ))

    conn.commit()
    conn.close()

    return {"status":"ok"}

    conn.commit()
    conn.close()

    return {"status":"ok"}

# ---------------- EDIT LOAN ----------------
@app.post("/edit-loan")
def edit_loan(loan_id: int, amount: float):

    conn = db()
    c = conn.cursor()

    c.execute(
        "UPDATE loans SET loan_amount=%s WHERE id=%s",
        (amount, loan_id)
    )

    conn.commit()
    conn.close()

    return {"status": "updated"}

# ---------------- EDIT LOAN TYPE ----------------
@app.post("/edit-loan-type")
def edit_loan_type(loan_id: int, type: str):

    conn = db()
    c = conn.cursor()

    c.execute(
        "UPDATE loans SET installment_type=%s WHERE id=%s",
        (type, loan_id)
    )

    conn.commit()
    conn.close()

    return {"status": "updated"}

# ---------------- DELETE MEMBER ----------------
@app.post("/delete-member")
def delete_member(loan_id: int):

    conn = db()
    c = conn.cursor()

    # पहले transactions delete करो
    c.execute("DELETE FROM transactions WHERE loan_id=%s", (loan_id,))

    # फिर loan delete करो
    c.execute("DELETE FROM loans WHERE id=%s", (loan_id,))

    conn.commit()
    conn.close()

    return {"status": "deleted"}

@app.post("/delete-transaction")
def delete_transaction(id: int):

    conn = db()
    c = conn.cursor()

    c.execute("DELETE FROM transactions WHERE id=%s", (id,))

    conn.commit()
    conn.close()

    return {"status": "deleted"}

@app.post("/delete-entry")
def delete_entry(id: int):

    conn = db()
    c = conn.cursor()

    # 🔥 पहले voucher_id निकालो
    c.execute("SELECT voucher_id FROM general_ledger WHERE id=%s", (id,))
    row = c.fetchone()

    if not row:
        return {"status": "not found"}

    voucher_id = row[0]

    # 🔥 उसी voucher की सारी entries delete
    c.execute("DELETE FROM general_ledger WHERE voucher_id=%s", (voucher_id,))

    conn.commit()
    conn.close()

    return {"status": "deleted"}

@app.post("/update-transaction")
def update_transaction(id: int, debit: float, credit: float, mode: str):

    conn = db()
    c = conn.cursor()

    c.execute("""
    UPDATE transactions 
    SET debit=%s, credit=%s, mode=%s
    WHERE id=%s
    """, (debit, credit, mode, id))

    conn.commit()
    conn.close()

    return {"status": "updated"}

# ---------------- DAILY COLLECTION ----------------
@app.get("/daily-collection")
def daily_collection(date: str = None):

    conn = db()
    c = conn.cursor()

    if not date:
        date = datetime.now().date()

    # 🔹 LOAN COLLECTION
    c.execute("""
    SELECT 
        loans.account_no, 
        members.name, 
        (transactions.credit - transactions.debit) AS amount, 
        transactions.mode, 
        loans.installment_type
    FROM transactions
    JOIN loans ON transactions.loan_id = loans.id
    JOIN members ON loans.member_id = members.id
    WHERE DATE(transactions.date) = %s 
    AND (transactions.credit - transactions.debit) > 0
    """, (date,))

    loan_rows = c.fetchall()

    # 🔹 DDS COLLECTION
    c.execute("""
    SELECT 
        d.id,
        m.name,
        t.amount,
        'Cash' as mode,
        'DDS'
    FROM dds_transactions t
    JOIN dds_accounts d ON t.dds_id = d.id
    JOIN members m ON d.member_id = m.id
    WHERE DATE(t.date) = %s
    """, (date,))

    dds_rows = c.fetchall()

    data = []
    total = 0

    # Loan data
    for r in loan_rows:
        data.append({
            "account": r[0],
            "name": r[1],
            "amount": r[2],
            "mode": r[3],
            "type": r[4]
        })
        total += r[2]

    # DDS data
    for r in dds_rows:
        data.append({
            "account": f"DDS-{r[0]}",
            "name": r[1],
            "amount": r[2],
            "mode": r[3],
            "type": "DDS"
        })
        total += r[2]

    conn.close()

    return {
        "data": data,
        "total": total
    }

# ---------------- TODAY SUMMARY ----------------
@app.get("/today-summary")
def today_summary():

    conn = db()
    c = conn.cursor()

    today = datetime.now().date()

    # DDS count
    c.execute("SELECT COUNT(*) FROM dds_accounts")
    dds = c.fetchone()[0]

    # Daily count
    c.execute("SELECT COUNT(*) FROM loans WHERE installment_type='Daily'")
    daily = c.fetchone()[0]

    # Monthly count
    c.execute("SELECT COUNT(*) FROM loans WHERE installment_type='Monthly'")
    monthly = c.fetchone()[0]

    total_members = dds + daily + monthly

    # 🔥 TOTAL COLLECTION (आज)
    c.execute("""
    SELECT 
        COALESCE(SUM(credit - debit),0)
    FROM transactions
    WHERE DATE(date) = %s
    """, (today,))
    total = c.fetchone()[0]

    # 🔥 CASH
    c.execute("""
    SELECT 
        COALESCE(SUM(credit - debit),0)
    FROM transactions
    WHERE DATE(date) = %s AND mode='Cash'
    """, (today,))
    cash = c.fetchone()[0]

    # 🔥 ONLINE
    c.execute("""
    SELECT 
        COALESCE(SUM(credit - debit),0)
    FROM transactions
    WHERE DATE(date) = %s AND mode!='Cash'
    """, (today,))
    online = c.fetchone()[0]

    conn.close()

    return {
        "dds": dds,
        "daily": daily,
        "monthly": monthly,
        "members": total_members,
        "total": total,
        "cash": cash,
        "online": online
    }

# ---------------- DELETE DOCUMENT ----------------
@app.post("/delete-doc")
def delete_doc(filename: str):

    import os

    print("Deleting file:", filename)   # 👈 debug

    file_path = f"uploads/{filename}"

    if os.path.exists(file_path):
        os.remove(file_path)
        print("Deleted successfully")
    else:
        print("File not found ❌")

    return {"status": "deleted"}

@app.get("/get-docs")
def get_docs(loan_id: int):

    folder = f"uploads/loan_{loan_id}"

    if not os.path.exists(folder):
        return {"files": []}

    files = os.listdir(folder)

    return {"files": files} 

@app.get("/member-details")
def member_details(loan_id: int):

    conn = db()
    c = conn.cursor()

    c.execute("""
    SELECT 
        members.name,
        members.father,
        members.village,
        members.mobile,
        loans.loan_amount,
        loans.installment,
        loans.installment_type,
        loans.start_date
    FROM loans
    JOIN members ON loans.member_id = members.id
    WHERE loans.id=%s
    """,(loan_id,))

    r = c.fetchone()
    conn.close()

    return {
        "name": r[0],
        "father": r[1],
        "village": r[2],
        "mobile": r[3],
        "amount": r[4],
        "inst": r[5],
        "type": r[6],
        "start_date": str(r[7])
    }

from fastapi import Request

@app.post("/update-member")
async def update_member(request: Request):

    data = await request.json()
    start_date = data.get("start_date")

    conn = db()
    c = conn.cursor()

    c.execute("""
    UPDATE members
    SET name=%s, father=%s, village=%s, mobile=%s, g1=%s, g2=%s
    WHERE id = (
        SELECT member_id FROM loans WHERE id=%s
    )
    """,(data["name"], data["father"], data["village"], data["mobile"], data["g1"], data["g2"], data["loan_id"]))

    c.execute("""
    UPDATE loans
    SET loan_amount=%s, installment=%s, installment_type=%s, start_date=%s
    WHERE id=%s
    """,(data["amount"], data["inst"], data["type"], start_date, data["loan_id"]))

    conn.commit()
    conn.close()

    return {"status":"updated"}

@app.post("/close-account")
def close_account(loan_id: int):

    conn = db()
    c = conn.cursor()

    c.execute("""
    UPDATE loans
    SET status='Closed'
    WHERE id=%s
    """,(loan_id,))

    conn.commit()
    conn.close()

    return {"status":"closed"}

# ================= DDS SYSTEM =================

from fastapi import Request

@app.post("/create-dds")
async def create_dds(request: Request):

    data = await request.json()

    name = data.get("name")
    father = data.get("father")
    village = data.get("village")
    mobile = data.get("mobile")

    conn = db()
    c = conn.cursor()

    # member check
    c.execute("SELECT id FROM members WHERE mobile=%s", (mobile,))
    row = c.fetchone()

    if row:
        member_id = row[0]
    else:
        c.execute("""
            INSERT INTO members(cif, name, father, mobile, aadhaar)
            VALUES(%s,%s,%s,%s,%s)
            RETURNING id
        """, (cif, name, father, mobile, aadhaar))

        member_id = c.fetchone()[0]

    # DDS account check
    c.execute("SELECT id FROM dds_accounts WHERE member_id=%s",(member_id,))
    exists = c.fetchone()

    if not exists:
        c.execute("""
        INSERT INTO dds_accounts(member_id)
        VALUES (%s)
        """, (member_id,))

    conn.commit()
    conn.close()

    return {"status":"ok"}


# ✅ DDS LIST (collection screen)
@app.get("/dds-list")
def dds_list():

    conn = db()
    c = conn.cursor()

    c.execute("""
    SELECT 
        dds_accounts.id,
        members.name,
        members.mobile,

        COALESCE(SUM(dds_transactions.amount),0) as total,

        COALESCE(SUM(
            CASE 
                WHEN DATE(dds_transactions.date) = CURRENT_DATE 
                THEN dds_transactions.amount 
                ELSE 0 
            END
        ),0) as today

    FROM dds_accounts
    JOIN members ON dds_accounts.member_id = members.id
    LEFT JOIN dds_transactions 
        ON dds_transactions.dds_id = dds_accounts.id

    WHERE dds_accounts.status='Running'

    GROUP BY dds_accounts.id, members.name, members.mobile
    """)

    rows = c.fetchall()

    data = []

    for r in rows:

        paid = r[3] or 0

        data.append({
            "id": r[0],
            "name": r[1],
            "mobile": r[2],
            "total": r[3],
            "paid": r[3],
            "today": r[4],   # 👈 ADD
            "pending": 0
        })

    conn.close()
    return data


# ✅ DDS COLLECTION
from fastapi import Request

@app.post("/dds-collect")
async def dds_collect(request: Request):

    data = await request.json()

    dds_id = data["dds_id"]
    amount = data["amount"]
    mode = data.get("mode", "Cash")

    conn = db()
    c = conn.cursor()

    c.execute("""
    INSERT INTO dds_transactions(dds_id, date, amount, mode, type)
    VALUES (%s, NOW(), %s, %s, 'CR')
    """, (dds_id, amount, mode))

    # 🔥 ADD THIS (VERY IMPORTANT)
    add_to_general_ledger(
        date=datetime.now(),
        ledger="DDS Collection",
        debit=0,
        credit=amount,
        mode=mode,
        narration="DDS Collection"
    )

    conn.commit()
    conn.close()

    return {"status": "ok"}
   
@app.get("/general-ledger")
def general_ledger():

    conn = db()
    c = conn.cursor()

    c.execute("""
    SELECT date, ledger, debit, credit, mode, narration
    FROM general_ledger
    ORDER BY date DESC
    """)

    rows = c.fetchall()

    data = []

    for r in rows:
        data.append({
            "date": str(r[0]).split(" ")[0],
            "ledger": r[1],
            "debit": r[2],
            "credit": r[3],
            "mode": r[4],
            "narration": r[5]
        })

    conn.close()
    return data

@app.post("/delete-voucher")
async def delete_voucher(data: dict):

    conn = db()
    c = conn.cursor()

    voucher_id = data["voucher_id"]

    print("DELETE ID:", voucher_id)   # 👈 DEBUG

    c.execute("DELETE FROM general_ledger WHERE voucher_id=%s", (voucher_id,))

    print("Rows deleted:", c.rowcount)   # 👈 DEBUG

    conn.commit()
    conn.close()

    return {"status":"deleted"}

@app.post("/update-entry")
async def update_entry(data: dict):

    conn = db()
    c = conn.cursor()

    voucher_id = data["voucher_id"]
    amount = float(data["amount"])
    mode = data["mode"]
    note = data["note"]
    type = data["type"]
    account = data["account"]

    # ✅ STEP 1: OLD DELETE
    c.execute("DELETE FROM general_ledger WHERE voucher_id=%s", (voucher_id,))

    cash_account = "Cash" if mode == "Cash" else "Bank"

    # ✅ STEP 2: RE-INSERT (UPDATED)
    if type == "Payment":

        c.execute("""
        INSERT INTO general_ledger(date, ledger, debit, credit, mode, narration, voucher_id)
        VALUES(NOW(), %s, %s, 0, %s, %s, %s)
        """, (account, amount, mode, note, voucher_id))

        c.execute("""
        INSERT INTO general_ledger(date, ledger, debit, credit, mode, narration, voucher_id)
        VALUES(NOW(), %s, 0, %s, %s, %s, %s)
        """, (cash_account, amount, mode, f"By {account}", voucher_id))

    else:

        c.execute("""
        INSERT INTO general_ledger(date, ledger, debit, credit, mode, narration, voucher_id)
        VALUES(NOW(), %s, %s, 0, %s, %s, %s)
        """, (cash_account, amount, mode, f"From {account}", voucher_id))

        c.execute("""
        INSERT INTO general_ledger(date, ledger, debit, credit, mode, narration, voucher_id)
        VALUES(NOW(), %s, 0, %s, %s, %s, %s)
        """, (account, amount, mode, note, voucher_id))

    conn.commit()
    conn.close()

    return {"status": "updated"}

@app.get("/daybook")
def daybook(date: str = None):

    if not date:
        date = datetime.now().date()

    # 🔥 ADD THIS
    if isinstance(date, str) and "/" in date:
        date = datetime.strptime(date, "%d/%m/%Y").strftime("%Y-%m-%d")

    conn = db()
    c = conn.cursor()

    # ---------------- OPENING ----------------

    credit = []
    total_credit_cash = 0
    total_credit_bank = 0

    c.execute("""
    SELECT 
        SUM(CASE WHEN mode='Cash' THEN debit-credit ELSE 0 END),
        SUM(CASE WHEN mode!='Cash' THEN debit-credit ELSE 0 END)
    FROM general_ledger
    WHERE DATE(date) < %s
    """, (date,))

    row = c.fetchone()
    opening_cash = row[0] or 0
    opening_bank = row[1] or 0

    # 🔹 Loan Collection
    c.execute("""
    SELECT SUM(credit - debit), mode
    FROM transactions
    WHERE DATE(date)=%s
    GROUP BY mode
    """, (date,))

    loan_rows = c.fetchall()

    loan_cash = 0
    loan_bank = 0

    for r in loan_rows:
        amt = r[0] or 0
        mode = r[1]

        if mode == "Cash":
            loan_cash += amt
        else:
            loan_bank += amt

    # 🔥 Parent (Loan Collection)
    if loan_cash > 0 or loan_bank > 0:

        # Parent row
        credit.append({
            "date": str(date),
            "particular": "Loan Collection",
            "cash": loan_cash,
            "bank": loan_bank
        })

        
        # 🔹 REAL SPLIT (Daily + Monthly)

        c.execute("""
        SELECT loans.installment_type,
            SUM(transactions.credit - transactions.debit),
            transactions.mode
        FROM transactions
        JOIN loans ON transactions.loan_id = loans.id
        WHERE DATE(transactions.date)=%s
        GROUP BY loans.installment_type, transactions.mode
        """, (date,))

        rows = c.fetchall()

        daily_cash = 0
        daily_bank = 0
        monthly_cash = 0
        monthly_bank = 0

        for r in rows:
            typ = r[0]   # Daily / Monthly
            amt = r[1] or 0
            mode = r[2]

            if typ == "Daily":
                if mode == "Cash":
                    daily_cash += amt
                else:
                    daily_bank += amt

            elif typ == "Monthly":
                if mode == "Cash":
                    monthly_cash += amt
                else:
                    monthly_bank += amt

        if daily_cash > 0 or daily_bank > 0:
            credit.append({
                "date": str(date),
                "particular": "Daily Loan Collection",
                "cash": daily_cash,
                "bank": daily_bank
            })

        if monthly_cash > 0 or monthly_bank > 0:
            credit.append({
                "date": str(date),
                "particular": "Monthly Loan Collection",
                "cash": monthly_cash,
                "bank": monthly_bank
            })
    
    # 🔹 DDS Collection
    c.execute("""
    SELECT 
        SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END),
        mode
    FROM dds_transactions
    WHERE DATE(date)=%s
    GROUP BY mode
    """, (date,))

    dds_rows = c.fetchall()

    dds_cash = 0
    dds_bank = 0

    for r in dds_rows:
        amt = r[0] or 0
        mode = r[1]

        if mode == "Cash":
            dds_cash += amt
        else:
            dds_bank += amt

    if dds_cash > 0 or dds_bank > 0:
        credit.append({
            "date": str(date),
            "particular": "DDS Collection",
            "cash": dds_cash,
            "bank": dds_bank
        })

        total_credit_cash += dds_cash
        total_credit_bank += dds_bank

    # ---------------- CREDIT ----------------
    
    print("DATE:", date)

    c.execute("""
    SELECT ledger, credit, mode
    FROM general_ledger
    WHERE DATE(date)=%s AND credit > 0
    """, (date,))

    rows = c.fetchall()

    print("CREDIT ROWS:", rows)

    for r in rows:
        ledger = r[0]
        credit_amt = r[1]
        mode = r[2]

        # ❌ system ledgers skip
        lname = ledger.strip().lower()

        if lname in ["loan collection", "dds collection", "cash", "bank"]:
            continue

        credit.append({
            "date": str(date),
            "particular": ledger,
            "cash": credit_amt if mode == "Cash" else 0,
            "bank": credit_amt if mode != "Cash" else 0
        })
    
        print("AFTER FILTER:", credit)

        if mode == "Cash":
            total_credit_cash += credit_amt
        else:
            total_credit_bank += credit_amt        
   
    # ---------------- DEBIT ----------------
    debit_list = []
    total_debit_cash = 0
    total_debit_bank = 0

    c.execute("""
    SELECT ledger, debit, mode
    FROM general_ledger
    WHERE DATE(date)=%s AND debit > 0
    """, (date,))

    debit_rows = c.fetchall()

    for r in debit_rows:
        ledger = r[0]
        debit_amt = r[1]
        mode = r[2]

        lname = ledger.lower()

        # ❌ skip system
        if "collection" in lname:
            continue

        if "bank" in lname or "cash" in lname:
            continue

        debit_list.append({
            "date": str(date),
            "particular": ledger,
            "cash": debit_amt if mode == "Cash" else 0,
            "bank": debit_amt if mode != "Cash" else 0
        })

        if mode == "Cash":
            total_debit_cash += debit_amt
        else:
            total_debit_bank += debit_amt

    # ---------------- CLOSING ----------------
    closing_cash = opening_cash + total_credit_cash - total_debit_cash
    closing_bank = opening_bank + total_credit_bank - total_debit_bank

    conn.close()

    return {
        "opening_cash": opening_cash,
        "opening_bank": opening_bank,
        "closing_cash": closing_cash,
        "closing_bank": closing_bank,
        "credit": credit,
        "debit": debit_list
    }
    
@app.get("/dds-ledger")
def dds_ledger(dds_id: int):

    conn = db()
    c = conn.cursor()

    c.execute("""
    SELECT id, date, amount, mode
    FROM dds_transactions
    WHERE dds_id=%s
    ORDER BY date
    """,(dds_id,))

    rows = c.fetchall()

    conn.close()

    return [
        {
            "id": r[0],
            "date": str(r[1]).split(" ")[0],
            "amount": r[2],
            "mode": r[3]
        }
        for r in rows
    ]

@app.post("/update-dds")
def update_dds(data: dict):

    id = data.get("id")
    amount = float(data.get("amount"))

    conn = db()
    c = conn.cursor()

    # old amount
    c.execute("SELECT amount FROM dds_transactions WHERE id=%s",(id,))
    old = c.fetchone()[0]

    diff = amount - old

    # update dds
    c.execute("""
    UPDATE dds_transactions SET amount=%s WHERE id=%s
    """,(amount,id))

    # update GL properly
    c.execute("""
    UPDATE general_ledger
    SET debit = debit + %s
    WHERE narration='DDS' AND debit > 0
    """,(diff,))

    c.execute("""
    UPDATE general_ledger
    SET credit = credit + %s
    WHERE ledger='DDS Collection'
    """,(diff,))

    conn.commit()
    conn.close()

    return {"status":"updated"}

@app.post("/delete-dds")
def delete_dds(data: dict):

    id = data.get("id")

    conn = db()
    c = conn.cursor()

    c.execute("DELETE FROM dds_transactions WHERE id=%s", (id,))

    conn.commit()
    conn.close()

    return {"status":"deleted"}

@app.get("/dds-member")
def dds_member(dds_id: int):

    conn = db()
    c = conn.cursor()

    c.execute("""
    SELECT m.name, m.mobile, d.total_amount
    FROM dds_accounts d
    JOIN members m ON d.member_id = m.id
    WHERE d.id=%s
    """,(dds_id,))

    r = c.fetchone()

    conn.close()

    return {
        "name": r[0],
        "mobile": r[1],
        "total": r[2]
    }

@app.post("/add-dds-debit")
def add_dds_debit(data: dict):

    dds_id = data.get("dds_id")
    amount = float(data.get("amount"))

    conn = db()
    c = conn.cursor()

    # debit entry (reverse entry)
    c.execute("""
    INSERT INTO dds_transactions(dds_id, date, amount)
    VALUES (%s, NOW(), %s)
    """,(dds_id, -amount))   # 👈 minus = debit

    conn.commit()
    conn.close()

    return {"status":"ok"}

@app.post("/reopen-dds")
def reopen_dds(dds_id: int):

    conn = db()
    c = conn.cursor()

    c.execute("""
    UPDATE dds_accounts 
    SET status='Running' 
    WHERE id=%s
    """, (dds_id,))

    conn.commit()
    conn.close()

    return {"status":"reopened"}

@app.post("/delete-dds-member")
def delete_dds_member(data: dict):

    id = data.get("id")

    conn = db()
    c = conn.cursor()

    c.execute("DELETE FROM dds_accounts WHERE id=%s",(id,))

    conn.commit()
    conn.close()

    return {"status":"deleted"}

@app.post("/close-loan")
def close_loan(loan_id: int):

    conn = db()
    c = conn.cursor()

    c.execute("""
    UPDATE loans 
    SET status='Closed', close_date=NOW()
    WHERE id=%s
    """, (loan_id,))

    conn.commit()
    conn.close()

    return {"status":"closed"}

@app.post("/reopen-loan")
def reopen_loan(loan_id: int):

    conn = db()
    c = conn.cursor()

    c.execute("UPDATE loans SET status='Running' WHERE id=%s", (loan_id,))

    conn.commit()
    conn.close()

    return {"status":"reopened"}

@app.get("/closed-loans")
def closed_loans():

    conn = db()
    c = conn.cursor()

    c.execute("""
    SELECT account_no, name, loan_amount, status
    FROM loans
    JOIN members ON loans.member_id = members.id
    WHERE loans.status='Closed'
    """)

    rows = c.fetchall()
    conn.close()

    return [
        {
            "loan_id": r[0],
            "name": r[1],
            "loan": r[2]
        }
        for r in rows
    ]

@app.get("/closed-dds")
def closed_dds():

    conn = db()
    c = conn.cursor()

    c.execute("""
    SELECT dds_accounts.id, members.name, members.mobile, dds_accounts.status
    FROM dds_accounts
    JOIN members ON dds_accounts.member_id = members.id
    WHERE dds_accounts.status='Closed'
    """)

    rows = c.fetchall()

    result = []
    for r in rows:
        result.append({
            "account_no": f"DDS-{r[0]}",
            "name": r[1],
            "mobile": r[2],
            "status": r[3]
        })

    return result

@app.post("/close-dds")
async def close_dds(request: Request):

    data = await request.json()
    dds_id = data.get("dds_id")

    print("Closing DDS ID:", dds_id)

    conn = db()
    c = conn.cursor()

    c.execute("""
    UPDATE dds_accounts 
    SET status='Closed' 
    WHERE id=%s
    """, (dds_id,))

    conn.commit()
    conn.close()

    return {"status":"closed"}

@app.get("/dds-today-summary")
def dds_today_summary():

    conn = db()
    c = conn.cursor()

    c.execute("""
    SELECT 
        mode,

        SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as cr,
        SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as dr

    FROM dds_transactions
    WHERE DATE(date) = CURRENT_DATE
    GROUP BY mode
    """)

    rows = c.fetchall()

    result = {
        "cash_cr": 0,
        "cash_dr": 0,
        "bank_cr": 0,
        "bank_dr": 0
    }

    for r in rows:
        mode = r[0]
        cr = r[1] or 0
        dr = r[2] or 0

        if mode == "Cash":
            result["cash_cr"] = cr
            result["cash_dr"] = dr
        else:
            result["bank_cr"] = cr
            result["bank_dr"] = dr

    conn.close()
    return result

@app.get("/loan-today-summary")
def loan_today_summary():

    conn = db()
    c = conn.cursor()

    c.execute("""
    SELECT 
        mode,
        SUM(credit) as cr,
        SUM(debit) as dr
    FROM transactions
    WHERE DATE(date) = CURRENT_DATE
    GROUP BY mode
    """)

    rows = c.fetchall()

    result = {
        "cash_cr": 0,
        "cash_dr": 0,
        "bank_cr": 0,
        "bank_dr": 0
    }

    for r in rows:
        mode = r[0]
        cr = r[1] or 0
        dr = r[2] or 0

        if mode == "Cash":
            result["cash_cr"] = cr
            result["cash_dr"] = dr
        else:
            result["bank_cr"] = cr
            result["bank_dr"] = dr

    conn.close()
    return result

@app.get("/loan-month-summary")
def loan_month_summary():

    conn = db()
    c = conn.cursor()

    c.execute("""
    SELECT 
        mode,
        SUM(credit) as cr,
        SUM(debit) as dr
    FROM transactions
    WHERE date::timestamp >= DATE_TRUNC('month', CURRENT_DATE)
    AND date::timestamp < DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '1 month'
    GROUP BY mode
    """)

    rows = c.fetchall()

    result = {
        "cash_cr": 0,
        "cash_dr": 0,
        "bank_cr": 0,
        "bank_dr": 0
    }

    for r in rows:
        mode = r[0]
        cr = r[1] or 0
        dr = r[2] or 0

        if mode == "Cash":
            result["cash_cr"] = cr
            result["cash_dr"] = dr
        else:
            result["bank_cr"] = cr
            result["bank_dr"] = dr

    conn.close()
    return result

@app.get("/summary")
def summary(date: str = None):

    conn = db()
    c = conn.cursor()

    if not date:
        date = datetime.now().date()

    # 🔥 DDS
    c.execute("""
    SELECT 
        SUM(CASE WHEN mode='Cash' AND amount > 0 THEN amount ELSE 0 END),
        SUM(CASE WHEN mode='Cash' AND amount < 0 THEN ABS(amount) ELSE 0 END),
        SUM(CASE WHEN mode!='Cash' AND amount > 0 THEN amount ELSE 0 END),
        SUM(CASE WHEN mode!='Cash' AND amount < 0 THEN ABS(amount) ELSE 0 END)
    FROM dds_transactions
    WHERE DATE(date)=%s
    """,(date,))
    dds = c.fetchone()

    # 🔥 DAILY + MONTHLY (transactions से)
    c.execute("""
    SELECT 
        loans.installment_type,
        mode,
        SUM(credit),
        SUM(debit)
    FROM transactions
    JOIN loans ON transactions.loan_id = loans.id
    WHERE DATE(transactions.date)=%s
    GROUP BY loans.installment_type, mode
    """,(date,))
    rows = c.fetchall()

    data = {
        "Daily": {"cash_cr":0,"cash_dr":0,"bank_cr":0,"bank_dr":0},
        "Monthly": {"cash_cr":0,"cash_dr":0,"bank_cr":0,"bank_dr":0}
    }

    for r in rows:
        t, mode, cr, dr = r
        cr = cr or 0
        dr = dr or 0

        if mode == "Cash":
            data[t]["cash_cr"] += cr
            data[t]["cash_dr"] += dr
        else:
            data[t]["bank_cr"] += cr
            data[t]["bank_dr"] += dr

    # 🔥 Mode total
    c.execute("""
    SELECT 
        SUM(CASE WHEN mode='Cash' THEN credit-debit ELSE 0 END),
        SUM(CASE WHEN mode!='Cash' THEN credit-debit ELSE 0 END)
    FROM transactions
    WHERE DATE(date)=%s
    """,(date,))
    cash_total, bank_total = c.fetchone()
    
    c.execute("""
    SELECT COUNT(*) FROM (
        SELECT m.id
        FROM members m
        LEFT JOIN loans l 
            ON m.id = l.member_id AND l.status='Running'
        LEFT JOIN dds_accounts d 
            ON m.id = d.member_id AND d.status='Running'
        WHERE l.id IS NOT NULL OR d.id IS NOT NULL
        GROUP BY m.id
    ) x
    """)

    total_members = c.fetchone()[0]

    # ✅ DDS Active / Closed (temporary fix)
    active_dds = 0
    closed_dds = 0

    c.execute("SELECT COUNT(*) FROM loans WHERE status='Running'")
    active_loans = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM loans WHERE status='Closed'")
    closed_loans = c.fetchone()[0]

    # ✅ Active Breakdown
    c.execute("SELECT COUNT(*) FROM loans WHERE status='Running' AND installment_type='Daily'")
    active_daily = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM loans WHERE status='Running' AND installment_type='Monthly'")
    active_monthly = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM dds_accounts WHERE status='Running'")
    active_dds = c.fetchone()[0]

    # ✅ Closed Breakdown
    c.execute("SELECT COUNT(*) FROM loans WHERE status='Closed' AND installment_type='Daily'")
    closed_daily = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM loans WHERE status='Closed' AND installment_type='Monthly'")
    closed_monthly = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM dds_accounts WHERE status='Closed'")
    closed_dds = c.fetchone()[0]

    # 🔥 Pending (Daily)
    c.execute("""
    SELECT 
        SUM(l.loan_amount - COALESCE(t.total_paid,0))
    FROM loans l
    LEFT JOIN (
        SELECT loan_id, SUM(credit - debit) as total_paid
        FROM transactions
        GROUP BY loan_id
    ) t ON l.id = t.loan_id
    WHERE l.installment_type='Daily'
    """)
    daily_pending = c.fetchone()[0] or 0

    c.execute("""
    SELECT 
        SUM(l.loan_amount - COALESCE(t.total_paid,0))
    FROM loans l
    LEFT JOIN (
        SELECT loan_id, SUM(credit - debit) as total_paid
        FROM transactions
        GROUP BY loan_id
    ) t ON l.id = t.loan_id
    WHERE l.installment_type='Monthly'
    """)
    monthly_pending = c.fetchone()[0] or 0

    # 🔥 Activity
    # ✅ temporary fix
    new_members = 0

    c.execute("SELECT COUNT(*) FROM transactions WHERE DATE(date)=%s",(date,))
    collections = c.fetchone()[0]

    closed_today = 0

    conn.close()

    return {
        "dds_cash_cr": dds[0] or 0,
        "dds_cash_dr": dds[1] or 0,
        "dds_bank_cr": dds[2] or 0,
        "dds_bank_dr": dds[3] or 0,

        "daily_cash_cr": data["Daily"]["cash_cr"],
        "daily_cash_dr": data["Daily"]["cash_dr"],
        "daily_bank_cr": data["Daily"]["bank_cr"],
        "daily_bank_dr": data["Daily"]["bank_dr"],

        "monthly_cash_cr": data["Monthly"]["cash_cr"],
        "monthly_cash_dr": data["Monthly"]["cash_dr"],
        "monthly_bank_cr": data["Monthly"]["bank_cr"],
        "monthly_bank_dr": data["Monthly"]["bank_dr"],

        "cash_total": cash_total or 0,
        "bank_total": bank_total or 0,

        "total_members": total_members,
        "active_dds": active_dds,
        "active_daily": active_daily,
        "active_monthly": active_monthly,

        "closed_dds": closed_dds,
        "closed_daily": closed_daily,
        "closed_monthly": closed_monthly,

        "daily_pending": daily_pending,
        "monthly_pending": monthly_pending,

        "new_members": new_members,
        "collections": collections,
        "closed_today": closed_today
    }

@app.get("/active-members")
def active_members():

    conn = db()
    c = conn.cursor()

    c.execute("""
    SELECT 
        m.name,
        m.mobile,

        COUNT(DISTINCT d.id) as dds,
        COUNT(DISTINCT CASE WHEN l.installment_type='Daily' THEN l.id END) as daily,
        COUNT(DISTINCT CASE WHEN l.installment_type='Monthly' THEN l.id END) as monthly

    FROM members m

    LEFT JOIN loans l 
        ON m.id = l.member_id AND l.status='Running'

    LEFT JOIN dds_accounts d 
        ON m.id = d.member_id AND d.status='Running'

    WHERE l.id IS NOT NULL OR d.id IS NOT NULL

    GROUP BY m.id
    """)

    rows = c.fetchall()

    result = []

    for r in rows:
        result.append({
            "name": r[0],
            "mobile": r[1],
            "dds": r[2],
            "daily": r[3],
            "monthly": r[4]
        })

    conn.close()

    return result

@app.get("/member-accounts")
def member_accounts(mobile: str):

    conn = db()
    c = conn.cursor()

    # member id निकालो
    c.execute("SELECT id FROM members WHERE mobile=%s", (mobile,))
    row = c.fetchone()

    if not row:
        return []

    member_id = row[0]

    result = []

    # DDS accounts
    c.execute("""
        SELECT id, id as account_no, 'DDS'
        FROM dds_accounts
        WHERE member_id=%s AND status='Running'
    """, (member_id,))
    for r in c.fetchall():
        result.append({
            "id": r[0],
            "account_no": r[1],
            "type": r[2]
        })

    # Loan accounts
    c.execute("""
        SELECT id, account_no, installment_type 
        FROM loans 
        WHERE member_id=%s AND status='Running'
    """, (member_id,))
    for r in c.fetchall():
        result.append({
            "id": r[0],
            "account_no": r[1],
            "type": r[2]
        })

    conn.close()

    return result

@app.get("/loan-details")
def loan_details(date: str, type: str):

    conn = db()
    c = conn.cursor()

    c.execute("""
    SELECT         
        loans.account_no,
        members.name,
        loans.id,

        SUM(CASE 
            WHEN transactions.mode = 'Cash' 
            THEN transactions.credit 
            ELSE 0 
        END) as cash,

        SUM(CASE 
            WHEN transactions.mode != 'Cash' 
            THEN transactions.credit 
            ELSE 0 
        END) as bank

    FROM transactions

    JOIN loans ON transactions.loan_id = loans.id
    JOIN members ON loans.member_id = members.id

    WHERE DATE(transactions.date)=%s
    AND loans.installment_type=%s
    AND transactions.credit > 0

    GROUP BY 
        loans.account_no,
        members.name,
        loans.id  

    ORDER BY members.name
    """, (date, type))

    rows = c.fetchall()
    conn.close()

    return [
        {
            "date": "",   # date अब नहीं है
            "account": r[0],
            "name": r[1],
            "loan_id": r[2],
            "cash": r[3],
            "bank": r[4]
        }
        for r in rows
    ]

@app.get("/dds-details")
def dds_details(date: str):

    conn = db()
    c = conn.cursor()

    c.execute("""
    SELECT 
        dds_transactions.date,
        dds_accounts.id, 
        members.name,
        SUM(CASE WHEN dds_transactions.mode='Cash' THEN dds_transactions.amount ELSE 0 END),
        SUM(CASE WHEN dds_transactions.mode!='Cash' THEN dds_transactions.amount ELSE 0 END)

    FROM dds_transactions
    JOIN dds_accounts ON dds_transactions.dds_id = dds_accounts.id
    JOIN members ON dds_accounts.member_id = members.id

    WHERE DATE(dds_transactions.date)=%s

    GROUP BY dds_transactions.date, dds_accounts.id, members.name
    ORDER BY members.name
    """, (date,))

    rows = c.fetchall()
    conn.close()

    return [
        {
            "date": r[0],
            "account": f"DDS-{r[1]}",
            "name": r[2],
            "cash": r[3] or 0,
            "bank": r[4] or 0
        }
        for r in rows
    ]

@app.get("/due-members")
def due_members(days: str):

    conn = db()
    cur = conn.cursor()

    # 🔥 SQL
    query = """
    SELECT 
        loans.account_no,
        members.name,
        members.mobile,
        MAX(transactions.date) as last_paid
    FROM loans
    JOIN members ON loans.member_id = members.id
    LEFT JOIN transactions ON transactions.loan_id = loans.id
    GROUP BY loans.account_no, members.name, members.mobile
    """

    cur.execute(query)

    print("QUERY RUNNING")

    rows = cur.fetchall()

    print("ROWS DATA:", rows)
    
    rows = cur.fetchall()

    from datetime import datetime

    result = []

    for r in rows:
        account = r[0]
        name = r[1]
        mobile = r[2]
        last_paid = r[3]

        from datetime import datetime

        if last_paid:
            # 🔥 direct string से date निकालो (safe तरीका)
            last_paid = str(last_paid).split(" ")[0]   # सिर्फ date
            last_paid = datetime.strptime(last_paid, "%Y-%m-%d")

            diff = (datetime.now() - last_paid).days
        else:
            diff = 999

        # 🔥 filter logic
        if days == "old":
            if diff > 15:
                result.append({
                    "account": account,
                    "name": name,
                    "mobile": mobile,
                    "last_paid": str(last_paid).split(" ")[0] if last_paid else ""
                })
        else:
            if diff >= int(days):
                result.append({
                    "account": account,
                    "name": name,
                    "mobile": mobile,
                    "last_paid": str(last_paid).split(" ")[0] if last_paid else ""
                })

    return result

@app.get("/monthly-due")
def monthly_due():

    conn = db()
    cur = conn.cursor()

    query = """
    SELECT 
        loans.id,
        loans.account_no,
        members.name,
        members.mobile,
        loans.start_date,
        loans.installment
    FROM loans
    LEFT JOIN members ON loans.member_id = members.id
    WHERE loans.installment_type = 'Monthly'
    """

    cur.execute(query)
    rows = cur.fetchall()

    from datetime import datetime

    today = datetime.now()

    due_list = []
    paid_list = []

    for r in rows:

        print("ROW:", r)

        loan_id = r[0]
        account = r[1]
        name = r[2]
        mobile = r[3]
        start_date = r[4]
        installment = r[5]

        # 🔥 start_date fix
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date.split(" ")[0], "%Y-%m-%d")

        # 🔥 months passed
        months = (today.year - start_date.year) * 12 + (today.month - start_date.month)
        if today.day < start_date.day:
            months -= 1

        months = max(months, 0)

        # 🔥 total paid amount
        cur.execute("""
            SELECT COALESCE(SUM(credit - debit),0)
            FROM transactions
            WHERE loan_id = %s
        """, (loan_id,))

        total_paid = cur.fetchone()[0] or 0

        # 🔥 paid kist
        paid_kist = int(total_paid // installment)

        # 🔥 due kist
        due_kist = months - paid_kist

        # 🔥 oldest due date
        from dateutil.relativedelta import relativedelta
        oldest_due = start_date + relativedelta(months=paid_kist)

        # 🔴 Due Members
        if due_kist > 0:
            due_list.append({
                "account": account,
                "name": name,
                "mobile": mobile,
                "due_date": oldest_due.strftime("%Y-%m-%d"),
                "due_kist": due_kist
            })

        # 🟢 Paid Members
        else:
            next_due = start_date + relativedelta(months=months+1)

            paid_list.append({
                "account": account,
                "name": name,
                "mobile": mobile,
                "next_due": next_due.strftime("%Y-%m-%d")
            })

    return {
        "due": due_list,
        "paid": paid_list
    }

@app.get("/backup-list")
def backup_list():

    files = []

    base = "backups"

    if not os.path.exists(base):
        return []

    for folder in os.listdir(base):
        path = os.path.join(base, folder)

        if os.path.isdir(path):
            for f in os.listdir(path):
                files.append(f"{folder}/{f}")

    files.sort(reverse=True)

    return files

@app.post("/restore")
async def restore(request: Request):

    data = await request.json()

    file = data.get("file")
    password = data.get("password")

    if password != "admin@123":
        return {"status": "error", "msg": "Wrong password"}

    try:
        create_backup()

        src = os.path.join("backups", file)
        dst = "finance.db"

        shutil.copy2(src, dst)

        return {"status": "ok"}

    except Exception as e:
        return {"status": "error", "msg": str(e)}

from fastapi import Form

@app.post("/restore-file")
async def restore_file(file: UploadFile = File(...), password: str = Form(...)):

    if password != "admin@123":
        return {"status": "error", "msg": "Wrong password"}

    try:
        # safety backup
        create_backup()

        # temp save
        temp_path = "temp_restore.db"

        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # replace DB
        shutil.copy2(temp_path, "finance.db")

        os.remove(temp_path)

        return {"status": "ok"}

    except Exception as e:
        return {"status": "error", "msg": str(e)}

from fastapi import Request
from passlib.hash import pbkdf2_sha256

@app.post("/login")
async def login(request: Request):

    data = await request.json()

    username = data.get("username").strip().lower()
    password = data.get("password")

    conn = db()
    c = conn.cursor()

    c.execute("SELECT * FROM users WHERE username=%s", (username,))
    user = c.fetchone()

    conn.close()

    print("INPUT USER:", username)
    print("INPUT PASS:", password)
    print("DB DATA:", user)

    if user:
        print("VERIFY RESULT:", pbkdf2_sha256.verify(password, user[2]))

    if user and pbkdf2_sha256.verify(password, user[2]):
        return {
            "status": "ok",
            "role": user[3],
            "username": user[1]
        }
    else:
        return {"status": "error"}
   
from passlib.hash import pbkdf2_sha256

from passlib.hash import pbkdf2_sha256

@app.post("/change-password")
async def change_password(request: Request):

    data = await request.json()

    username = data.get("username")
    old_password = data.get("old_password")
    otp = data.get("otp")
    new_password = data.get("new_password")

    conn = db()
    c = conn.cursor()

    # 🔍 user check
    c.execute("SELECT * FROM users WHERE username=%s", (username,))
    user = c.fetchone()

    if not user:
        return {"status": "error", "msg": "User not found"}

    # 🔐 OLD PASSWORD CHECK (optional but important)
    if old_password:
        try:
            if old_password and not bcrypt.verify(old_password, user[2]):
                return {"status": "error", "msg": "Old password incorrect"}
        except:
            # अगर old password plain text है
            if old_password != user[2]:
                return {"status": "error", "msg": "Wrong old password"}

    # 🔐 OTP VERIFY
    data_otp = otp_store.get(username)

    if not data_otp:
        return {"status": "error", "msg": "OTP not found"}

    if time.time() - data_otp["time"] > 300:
        return {"status": "error", "msg": "OTP expired"}

    if data_otp["otp"] != otp:
        return {"status": "error", "msg": "Wrong OTP"}

    # 🔐 NEW PASSWORD HASH
    new_hash = pbkdf2_sha256.hash(new_password)

    c.execute("UPDATE users SET password=%s WHERE username=%s", (new_hash, username))

    conn.commit()
    conn.close()

    # OTP delete
    if username in otp_store:
        del otp_store[username]

    return {"status": "ok", "msg": "Password updated successfully"}

@app.post("/send-otp")
async def send_otp(request: Request):

    data = await request.json()
    username = data.get("username")

    conn = db()
    c = conn.cursor()

    # 🔍 user से mobile/email लो
    c.execute("SELECT mobile, email FROM users WHERE username=%s", (username,))
    user = c.fetchone()

    if not user:
        return {"status": "error", "msg": "User not found"}

    mobile = user[0]
    email = user[1]

    if not mobile:
        return {"status": "error", "msg": "Mobile not found"}

    # 🔢 OTP generate
    otp = str(random.randint(1000, 9999))

    otp_store[username] = {
        "otp": otp,
        "time": time.time()
    }

    # 🔥 SMS भेजने का code (अभी print)
    print("OTP:", otp)

    # 📧 EMAIL भेजो
    if email:
        send_email_otp(email, otp)

    return {"status": "otp sent"}

# 🔥 SERVER START BACKUP
create_backup()

# 🔥 AUTO DAILY BACKUP
scheduler = BackgroundScheduler()

# रोज रात 11:59 backup
scheduler.add_job(create_backup, 'cron', hour=23, minute=59)

scheduler.start()

from passlib.hash import pbkdf2_sha256

@app.post("/add-user")
async def add_user(request: Request):

    data = await request.json()

    username = data.get("username").strip().lower()
    password = data.get("password")
    role = data.get("role")

    if not username or not password:
        return {"status": "error", "msg": "Missing fields"}

    # 🔐 hash password
    hashed = pbkdf2_sha256.hash(password)

    conn = db()
    c = conn.cursor()

    try:
        c.execute("""
        INSERT INTO users(username, password, role)
        VALUES(%s, %s, %s)
        """, (username, hashed, role))

        conn.commit()
        conn.close()

        return {"status": "ok"}

    except Exception as e:
        conn.close()
        return {"status": "error", "msg": str(e)}

import pandas as pd
from fastapi import UploadFile, File

@app.post("/import-members-loan")
async def import_excel(file: UploadFile = File(...)):

    df = pd.read_excel(file.file)

    conn = db()
    c = conn.cursor()

    inserted = 0
    result_data = []

    for _, row in df.iterrows():

        print("ROW:", row.to_dict())

        name = row["name"]
        father = row["father"]
        mobile = row["mobile"]
        aadhaar = str(row["aadhaar"])

        # 🔹 CIF check / create
        c.execute("""
            SELECT id, cif FROM members
            WHERE aadhaar=%s OR (name=%s AND father=%s)
        """, (aadhaar, name, father))

        r = c.fetchone()

        if r:
            member_id = r[0]
            cif = r[1]

        else:
            # ✅ last CIF निकालो
            c.execute("""
                SELECT cif FROM members
                WHERE cif IS NOT NULL
                ORDER BY id DESC LIMIT 1
            """)

            last = c.fetchone()

            if not last:
                cif = "CIF001"
            else:
                num = int(last[0].replace("CIF","")) + 1
                cif = f"CIF{num:03d}"

            # ✅ नया member insert
            c.execute("""
                INSERT INTO members(cif, name, father, mobile, aadhaar)
                VALUES(%s,%s,%s,%s,%s)
            """, (cif, name, father, mobile, aadhaar))

            member_id = c.lastrowid

        # 🔹 Account No
        c.execute("SELECT account_no FROM loans ORDER BY id DESC LIMIT 1")
        r = c.fetchone()

        if not r:
            account_no = "ACC001"
        else:
            num = int(r[0].replace("ACC","")) + 1
            account_no = f"ACC{num:03d}"

        # 🔹 Loan No
        c.execute("SELECT loan_no FROM loans WHERE loan_no IS NOT NULL ORDER BY id DESC LIMIT 1")
        r = c.fetchone()

        if not r:
            loan_no = "LN001"
        else:
            num = int(r[0].replace("LN","")) + 1
            loan_no = f"LN{num:03d}"

        # 🔹 Insert Loan
        c.execute("""
            INSERT INTO loans(
                member_id,
                cif,
                account_no,
                loan_no,
                installment_type,
                start_date,
                loan_amount,
                interest,
                total_loan,
                installment,
                duration,
                status
            )
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            member_id,
            cif,
            account_no,
            loan_no,
            row["loan_type"].capitalize(),
            row["loan_date"],
            row["principal"],
            row["interest"],
            row["total_loan"],
            row["installment"],
            row["duration"]
        ))

        # ✅ यहीं होना चाहिए
        inserted += 1

        result_data.append({
            "name": name,
            "cif": cif,
            "loan_no": loan_no,
            "account_no": account_no
        })

    conn.commit()

    result_df = pd.DataFrame(result_data)

    file_path = "uploads/result.xlsx"
    result_df.to_excel(file_path, index=False)

    conn.close()

    from fastapi.responses import FileResponse

    return FileResponse(
        path=file_path,
        filename="import_result.xlsx",
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

# ---------------- STATIC ----------------
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

app.mount("/", StaticFiles(directory="static", html=True), name="static")