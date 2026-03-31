
import tkinter as tk
from tkinter import ttk
from database import db
from utils.account import generate_account_no

def add_loan():

    win=tk.Toplevel()
    win.title("Add Loan")

    conn=db(); c=conn.cursor()
    c.execute("SELECT id,name FROM members")
    members=c.fetchall()

    c.execute("SELECT COUNT(*) FROM loans")
    n=c.fetchone()[0]+1
    conn.close()

    acc=generate_account_no(n)

    tk.Label(win,text="Account:"+acc).grid(row=0,column=0)

    member=ttk.Combobox(win,values=[f"{m[0]}|{m[1]}" for m in members])
    member.grid(row=1,column=1)

    amount=tk.Entry(win)
    inst=tk.Entry(win)

    tk.Label(win,text="Loan Amount").grid(row=2,column=0)
    amount.grid(row=2,column=1)

    tk.Label(win,text="Installment").grid(row=3,column=0)
    inst.grid(row=3,column=1)

    installment_type = ttk.Combobox(win,values=["Daily","Monthly"])
    installment_type.current(0)

    tk.Label(win,text="Installment Type").grid(row=4,column=0)
    installment_type.grid(row=4,column=1)

    detail = tk.Text(win,height=4,width=30)

    tk.Label(win,text="Payment Detail").grid(row=5,column=0)
    detail.grid(row=5,column=1,pady=5)

    # SAVE FUNCTION यहीं होना चाहिए
    def save():

        if member.get()=="":
            return

        mid=int(member.get().split("|")[0])

        conn=db()
        c=conn.cursor()

        c.execute("""
        INSERT INTO loans(
        account_no,
        member_id,
        loan_amount,
        installment,
        installment_type,
        disbursement_detail,
        status
        )
        VALUES(?,?,?,?,?,?,?)
        """,
        (
        acc,
        mid,
        amount.get(),
        inst.get(),
        installment_type.get(),
        detail.get("1.0","end"),
        "Running"
        ))

        conn.commit()
        conn.close()

        win.destroy()

    tk.Button(win,text="Save Loan",command=save,width=15).grid(row=6,column=1,pady=10)