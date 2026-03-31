import pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox
from database import db


# ---------------- ACCOUNT GENERATOR ----------------

def generate_account_no(c):

    c.execute("SELECT COUNT(*) FROM loans")

    n = c.fetchone()[0] + 1

    return f"ACC{str(n).zfill(3)}"


# ---------------- SELECT FILE ----------------

def import_excel_data():

    file = filedialog.askopenfilename(
        filetypes=[("Excel Files", "*.xlsx")]
    )

    if not file:
        return

    df = pd.read_excel(file)

    total_rows = len(df)

    members = set(df["name"])

    transactions = len(df)

    errors = 0

    for i, row in df.iterrows():

        if pd.isna(row["name"]):
            errors += 1

    show_preview(df, total_rows, len(members), transactions, errors)


# ---------------- PREVIEW WINDOW ----------------

def show_preview(df, total_rows, members, transactions, errors):

    win = tk.Toplevel()
    win.title("Excel Import Preview")
    win.geometry("350x250")

    tk.Label(
        win,
        text="Excel Import Preview",
        font=("Arial", 14, "bold")
    ).pack(pady=10)

    tk.Label(win, text=f"Total Rows : {total_rows}").pack(pady=5)
    tk.Label(win, text=f"Members : {members}").pack(pady=5)
    tk.Label(win, text=f"Transactions : {transactions}").pack(pady=5)
    tk.Label(win, text=f"Errors : {errors}").pack(pady=5)

    tk.Button(
        win,
        text="Import Data",
        bg="green",
        fg="white",
        command=lambda: confirm_import(df, win)
    ).pack(pady=10)

    tk.Button(
        win,
        text="Cancel",
        bg="red",
        fg="white",
        command=win.destroy
    ).pack()


# ---------------- IMPORT DATA ----------------

def confirm_import(df, win):

    conn = db()
    c = conn.cursor()

    for i, row in df.iterrows():

        if pd.isna(row["name"]):
            continue

        # ---------- MEMBER ----------

        c.execute("""
        INSERT OR IGNORE INTO members
        (name,father,village,mobile,guarantor1,guarantor2)
        VALUES(?,?,?,?,?,?)
        """, (
            row["name"],
            row["father"],
            row["village"],
            str(row["mobile"]),
            row["guarantor1"],
            row["guarantor2"]
        ))

        c.execute(
            "SELECT id FROM members WHERE name=?",
            (row["name"],)
        )

        member_id = c.fetchone()[0]


        # ---------- ACCOUNT NUMBER ----------

        account_no = row["account_no"]

        if pd.isna(account_no):
            account_no = generate_account_no(c)


        # ---------- LOAN ----------

        c.execute("""
        INSERT OR IGNORE INTO loans
        (account_no,member_id,loan_amount,installment,installment_type,status)
        VALUES(?,?,?,?,?,?)
        """, (
            account_no,
            member_id,
            row["loan_amount"],
            row["installment"],
            row["installment_type"],
            row["status"]
        ))

        c.execute(
            "SELECT id FROM loans WHERE account_no=?",
            (account_no,)
        )

        loan_id = c.fetchone()[0]


        # ---------- TRANSACTION ----------

        c.execute("""
        INSERT INTO transactions
        (loan_id,date,debit,credit,mode,narration)
        VALUES(?,?,?,?,?,?)
        """, (
            loan_id,
            str(row["txn_date"]),
            row["debit"],
            row["credit"],
            row["mode"],
            row["narration"]
        ))


    conn.commit()
    conn.close()

    win.destroy()

    messagebox.showinfo(
        "Success",
        "Excel Data Imported Successfully"
    )