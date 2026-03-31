from database import init_db,update_db

init_db()
update_db()

import tkinter as tk
from tkinter import ttk,messagebox
from database import db
from datetime import datetime,timedelta
from ui.ledger import open_ledger


def fast_collection():

    win=tk.Toplevel()
    win.title("Fast Collection PRO V8")
    win.state("zoomed")

    today=datetime.now()
    today_str = today.strftime("%Y-%m-%d")

    last_days=[(today-timedelta(days=i)).strftime("%Y-%m-%d") for i in range(5,0,-1)]

    # ---------------- TOP ----------------

    top=tk.Frame(win)
    top.pack(fill="x",pady=5)

    tk.Label(top,text="Payment Mode").pack(side="left",padx=5)

    mode_var=tk.StringVar(value="Cash")

    ttk.Combobox(
        top,
        textvariable=mode_var,
        values=["Cash","Bank"],
        width=10
    ).pack(side="left")

    tk.Label(top,text="Search").pack(side="left",padx=20)

    search=tk.Entry(top,width=25)
    search.pack(side="left")

    # ---------------- TREE ----------------

    cols=("id","Name","Mobile","Account","Loan","Inst",
          "d1","d2","d3","d4","d5",
          "Today","Total","Pending")

    frame=tk.Frame(win)
    frame.pack(fill="both",expand=True)

    tree=ttk.Treeview(frame,columns=cols,show="headings")

    heads=[
        "LoanID","Name","Mobile","Account","Loan","Inst",
        last_days[0],last_days[1],last_days[2],last_days[3],last_days[4],
        "Today","Total","Pending"
    ]

    for c,h in zip(cols,heads):
        tree.heading(c,text=h)
        tree.column(c,width=90,anchor="center")

    tree.pack(fill="both",expand=True)

    tree.tag_configure("pending",background="#ffe5e5")
    tree.tag_configure("paid",background="#d4ffd4")
    tree.tag_configure("today",background="#d9f0ff")

    # ---------------- TOTAL PANEL ----------------

    total_var=tk.StringVar()
    cash_var=tk.StringVar()
    bank_var=tk.StringVar()

    bottom=tk.Frame(win)
    bottom.pack(fill="x")

    tk.Label(bottom,textvariable=total_var,font=("Arial",14,"bold")).pack()
    tk.Label(bottom,textvariable=cash_var).pack()
    tk.Label(bottom,textvariable=bank_var).pack()

    # ---------------- SAVE COLLECTION ----------------

    undo_stack=[]


    def save_collection(loan_id,amt,date):

        mode=mode_var.get()

        conn=db()
        c=conn.cursor()

        c.execute(
        "SELECT id FROM transactions WHERE loan_id=? AND date=?",
        (loan_id,date)
        )

        row=c.fetchone()

        if row:

            c.execute(
            """
            UPDATE transactions
            SET credit=?,mode=?
            WHERE id=?
            """,
            (amt,mode,row[0])
            )

        else:

            c.execute(
            """
            INSERT INTO transactions
            (loan_id,date,debit,credit,narration,mode)
            VALUES (?,?,?,?,?,?)
            """,
            (loan_id,date,0,amt,"Collection",mode)
            )

        undo_stack.append((loan_id,date))
        conn.commit()
        conn.close()

    # ---------------- UNDO COLLECTION ----------------
    def undo_last(e=None):
        if not undo_stack:
            return
        loan_id,date = undo_stack.pop()
        conn=db()
        c=conn.cursor()
        c.execute('DELETE FROM transactions WHERE loan_id=? AND date=?',(loan_id,date))
        conn.commit()
        conn.close()
        load_members()

    win.bind('<Control-z>',undo_last)

# ---------------- TOTALS ----------------

    def load_totals():

        conn=db()
        c=conn.cursor()

        total = today_amt + sum(last5)

        c.execute("SELECT SUM(credit) FROM transactions WHERE date=? AND mode='Cash'",(today_str,))
        cash=c.fetchone()[0] or 0

        c.execute("SELECT SUM(credit) FROM transactions WHERE date=? AND mode='Bank'",(today_str,))
        bank=c.fetchone()[0] or 0

        conn.close()

        total_var.set(f"Today Total : {total}")
        cash_var.set(f"Cash : {cash}")
        bank_var.set(f"Bank : {bank}")

    # ---------------- LOAD MEMBERS ----------------

    def load_members():

        tree.delete(*tree.get_children())

        conn=db()
        c=conn.cursor()

        c.execute("""
        SELECT loans.id,
        members.name,
        members.mobile,
        loans.account_no,
        loans.loan_amount,
        loans.installment
        FROM loans
        JOIN members ON loans.member_id=members.id
        WHERE loans.status='Running'
        """)

        rows=c.fetchall()

        for r in rows:

            loan_id=r[0]

            c.execute("SELECT SUM(credit) FROM transactions WHERE loan_id=?",(loan_id,))
            total=c.fetchone()[0] or 0

            c.execute("SELECT SUM(credit) FROM transactions WHERE loan_id=? AND date=?",(loan_id,today_str))
            today_amt=c.fetchone()[0] or 0

            last5=[]
            for d in last_days:
                c.execute(
                    "SELECT SUM(credit) FROM transactions WHERE loan_id=? AND date=?",
                    (loan_id,d)
                )
                amt=c.fetchone()[0]
                last5.append(amt if amt else 0)

            c.execute(
            "SELECT SUM(credit) FROM transactions WHERE loan_id=? AND date=?",
            (loan_id,today_str)
            )
            today_amt=c.fetchone()[0] or 0

            total = today_amt + sum(last5)

            pending = max(r[4] - total,0)
            
            tag=""

            if total > r[4]:
                tag="paid"
            elif pending > 0:
                tag="pending"

            tree.insert("",tk.END,values=(
                loan_id,r[1],r[2],r[3],
                r[4],r[5],
                last5[0],last5[1],last5[2],last5[3],last5[4],
                today_amt,total,pending
            ),tags=(tag,))

        conn.close()

        load_totals()

    
    # ---------------- FAST COLLECTION ----------------

    def quick_collect(e=None):

        selected=tree.focus()

        if not selected:
            return

        data=tree.item(selected)["values"]

        loan_id=data[0]
        inst=data[5]

        save_collection(loan_id,inst,today_str)

        load_members()

    tree.bind("<space>",quick_collect)

    def next_member(e=None):
        selected=tree.focus()
        items=tree.get_children()
        if selected in items:
            idx=items.index(selected)
            if idx+1 < len(items):
                nxt=items[idx+1]
                tree.selection_set(nxt)
                tree.focus(nxt)
                tree.see(nxt)

    tree.bind("<Return>",next_member)

    # ---------------- SEARCH ----------------

    def do_search(e=None):

        q=search.get().lower()

        for item in tree.get_children(''):

            data=tree.item(item)["values"]

            if (
                q in str(data[1]).lower() or
                q in str(data[2]) or
                q in str(data[3]) or
                q in str(data[0])
            ):
                tree.selection_set(item)
                tree.focus(item)
                tree.see(item)
                break

    search.bind("<KeyRelease>",do_search)

    load_members()

    def open_member_ledger(event=None):

        selected = tree.focus()

        if not selected:
            return

        data = tree.item(selected)["values"]

        loan_id = data[0]

        open_ledger(loan_id)
