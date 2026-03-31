import tkinter as tk
from tkinter import ttk
from tkcalendar import DateEntry
from database import db


def open_daybook():

    win=tk.Toplevel()
    win.title("Day Book")
    win.state("zoomed")

    tk.Label(win,text="DAY BOOK",font=("Arial",18,"bold")).pack(pady=10)

    # ---------- DATE FRAME ----------

    date_frame=tk.Frame(win)
    date_frame.pack()

    tk.Label(date_frame,text="Select Date").pack(side="left")

    cal=DateEntry(date_frame,date_pattern="yyyy-mm-dd")
    cal.pack(side="left",padx=10)

    # ---------- MAIN FRAME ----------

    main=tk.Frame(win)
    main.pack(fill="both",expand=True,padx=10,pady=10)

    # ---------- CREDIT SIDE ----------

    left=tk.Frame(main)
    left.pack(side="left",fill="both",expand=True)

    tk.Label(left,text="CREDIT (Receipts)",font=("Arial",12,"bold")).pack()

    cols=("Date","Particular","Cash","Bank")

    tree_credit=ttk.Treeview(left,columns=cols,show="headings")

    for c in cols:
        tree_credit.heading(c,text=c)
        tree_credit.column(c,width=130,anchor="center")

    tree_credit.pack(fill="both",expand=True)

    # ---------- DEBIT SIDE ----------

    right=tk.Frame(main)
    right.pack(side="right",fill="both",expand=True)

    tk.Label(right,text="DEBIT (Payments)",font=("Arial",12,"bold")).pack()

    tree_debit=ttk.Treeview(right,columns=cols,show="headings")

    for c in cols:
        tree_debit.heading(c,text=c)
        tree_debit.column(c,width=130,anchor="center")

    tree_debit.pack(fill="both",expand=True)

    # ---------- TAG COLORS ----------

    tree_credit.tag_configure("head",font=("Arial",11,"bold"),foreground="green")
    tree_debit.tag_configure("head",font=("Arial",11,"bold"),foreground="red")

    # ---------- SUMMARY ----------

    summary=tk.Frame(win)
    summary.pack(fill="x")

    opening_label=tk.Label(summary,font=("Arial",11,"bold"))
    opening_label.pack(side="left",padx=20)

    cash_label=tk.Label(summary,font=("Arial",11,"bold"))
    cash_label.pack(side="left",padx=20)

    bank_label=tk.Label(summary,font=("Arial",11,"bold"))
    bank_label.pack(side="left",padx=20)

    closing_label=tk.Label(summary,font=("Arial",11,"bold"))
    closing_label.pack(side="right",padx=20)

    # ---------- LOAD DAYBOOK ----------

    def load_daybook():

        date=cal.get()

        tree_credit.delete(*tree_credit.get_children())
        tree_debit.delete(*tree_debit.get_children())

        conn=db()
        c=conn.cursor()

        # ---------- OPENING BALANCE ----------

        c.execute("SELECT SUM(credit)-SUM(debit) FROM transactions WHERE date < ?",(date,))
        loan_open=c.fetchone()[0] or 0

        c.execute("SELECT SUM(credit)-SUM(debit) FROM general_ledger WHERE date < ?",(date,))
        gl_open=c.fetchone()[0] or 0

        c.execute("SELECT SUM(credit)-SUM(debit) FROM personal_transactions WHERE date < ?",(date,))
        personal_open=c.fetchone()[0] or 0

        opening=loan_open+gl_open+personal_open

        opening_label.config(text=f"Opening Balance : {opening}")

        cash_in=0
        bank_in=0
        cash_out=0
        bank_out=0

        # ---------- LOAN COLLECTION ----------

        tree_credit.insert("",tk.END,values=("","LOAN","",""),tags=("head",))

        c.execute("""
        SELECT l.installment_type,SUM(t.credit),t.mode
        FROM transactions t
        LEFT JOIN loans l ON t.loan_id=l.id
        WHERE t.date=? AND t.credit>0
        GROUP BY l.installment_type,t.mode
        """,(date,))

        for loan_type,amt,mode in c.fetchall():

            cash=""
            bank=""

            if mode=="Cash":
                cash=amt
                cash_in+=amt
            else:
                bank=amt
                bank_in+=amt

            tree_credit.insert("",tk.END,values=(date,loan_type,cash,bank))

        # ---------- PERSONAL LEDGER CREDIT ----------

        tree_credit.insert("",tk.END,values=("","PERSONAL LEDGER","",""),tags=("head",))

        c.execute("""
        SELECT pt.date,pl.name,pt.credit,pt.mode
        FROM personal_transactions pt
        LEFT JOIN personal_ledgers pl
        ON pt.ledger_id=pl.id
        WHERE pt.date=? AND pt.credit>0
        """,(date,))

        for d,name,amt,mode in c.fetchall():

            cash=""
            bank=""

            if mode=="Cash":
                cash=amt
                cash_in+=amt
            else:
                bank=amt
                bank_in+=amt

            tree_credit.insert("",tk.END,values=(d,name,cash,bank))

        # ---------- LOAN DISBURSEMENT ----------

        tree_debit.insert("",tk.END,values=("","LOAN","",""),tags=("head",))

        c.execute("""
        SELECT t.date,m.name,l.installment_type,t.debit,t.mode
        FROM transactions t
        LEFT JOIN loans l ON t.loan_id=l.id
        LEFT JOIN members m ON l.member_id=m.id
        WHERE t.date=? AND t.debit>0
        """,(date,))

        for d,name,loan_type,amt,mode in c.fetchall():

            cash=""
            bank=""

            if mode=="Cash":
                cash=amt
                cash_out+=amt
            else:
                bank=amt
                bank_out+=amt

            tree_debit.insert("",tk.END,values=(d,loan_type+" - "+name,cash,bank))

        # ---------- SALARY ----------

        tree_debit.insert("",tk.END,values=("","SALARY","",""),tags=("head",))

        c.execute("""
        SELECT date,narration,debit,mode
        FROM general_ledger
        WHERE date=? AND ledger='Salary'
        """,(date,))

        for d,narr,amt,mode in c.fetchall():

            cash=""
            bank=""

            if mode=="Cash":
                cash=amt
                cash_out+=amt
            else:
                bank=amt
                bank_out+=amt

            tree_debit.insert("",tk.END,values=(d,narr,cash,bank))

        # ---------- EXPENSE ----------

        tree_debit.insert("",tk.END,values=("","EXPENSE","",""),tags=("head",))

        c.execute("""
        SELECT date,narration,debit,mode
        FROM general_ledger
        WHERE date=? AND ledger='Expense'
        """,(date,))

        for d,narr,amt,mode in c.fetchall():

            cash=""
            bank=""

            if mode=="Cash":
                cash=amt
                cash_out+=amt
            else:
                bank=amt
                bank_out+=amt

            tree_debit.insert("",tk.END,values=(d,narr,cash,bank))

        # ---------- PERSONAL LEDGER DEBIT ----------

        tree_debit.insert("",tk.END,values=("","PERSONAL LEDGER","",""),tags=("head",))

        c.execute("""
        SELECT pt.date,pl.name,pt.debit,pt.mode
        FROM personal_transactions pt
        LEFT JOIN personal_ledgers pl
        ON pt.ledger_id=pl.id
        WHERE pt.date=? AND pt.debit>0
        """,(date,))

        for d,name,amt,mode in c.fetchall():

            cash=""
            bank=""

            if mode=="Cash":
                cash=amt
                cash_out+=amt
            else:
                bank=amt
                bank_out+=amt

            tree_debit.insert("",tk.END,values=(d,name,cash,bank))

        closing=opening+cash_in+bank_in-cash_out-bank_out

        cash_label.config(text=f"Cash In : {cash_in}   Cash Out : {cash_out}")
        bank_label.config(text=f"Bank In : {bank_in}   Bank Out : {bank_out}")
        closing_label.config(text=f"Closing Balance : {closing}")

        conn.close()

    tk.Button(date_frame,text="Load",command=load_daybook).pack(side="left",padx=10)