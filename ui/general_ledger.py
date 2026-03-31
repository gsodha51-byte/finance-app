import tkinter as tk
from tkinter import ttk,messagebox
from tkcalendar import DateEntry
from database import db


def open_general_ledger():

    win = tk.Toplevel()
    win.title("General Ledger")
    win.state("zoomed")


# ---------- LEDGER TYPE BUTTONS ----------

    top = tk.Frame(win)
    top.pack(pady=10)

    ledger_var = tk.StringVar()

    def set_ledger(name):
        ledger_var.set(name)

    tk.Button(top,text="Expense",width=15,
              command=lambda:set_ledger("Expense")).grid(row=0,column=0,padx=5)

    tk.Button(top,text="Salary",width=15,
              command=lambda:set_ledger("Salary")).grid(row=0,column=1,padx=5)

    tk.Button(top,text="Office Expense",width=15,
              command=lambda:set_ledger("Office Expense")).grid(row=0,column=2,padx=5)

    tk.Button(top,text="Personal Ledger",width=15,
              command=lambda:set_ledger("Personal Ledger")).grid(row=0,column=3,padx=5)

    tk.Button(top,text="Other Expense",width=15,
              command=lambda:set_ledger("Other Expense")).grid(row=0,column=4,padx=5)


# ---------- ENTRY ROW ----------

    entry = tk.Frame(win)
    entry.pack(pady=10)

    date_entry = DateEntry(entry,width=12,date_pattern="yyyy-mm-dd")
    date_entry.grid(row=0,column=0,padx=5)

    ledger = tk.Entry(entry,textvariable=ledger_var,width=18)
    ledger.grid(row=0,column=1,padx=5)

    debit = tk.Entry(entry,width=10)
    debit.grid(row=0,column=2,padx=5)

    credit = tk.Entry(entry,width=10)
    credit.grid(row=0,column=3,padx=5)

    mode = ttk.Combobox(entry,values=["Cash","Bank"],width=8)
    mode.grid(row=0,column=4,padx=5)

    narration = tk.Entry(entry,width=25)
    narration.grid(row=0,column=5,padx=5)


# ---------- SAVE ----------

    def save():

        conn=db()
        c=conn.cursor()

        c.execute("""
        INSERT INTO general_ledger
        (date,ledger,debit,credit,mode,narration)
        VALUES(?,?,?,?,?,?)
        """,(
        date_entry.get(),
        ledger_var.get(),
        float(debit.get() or 0),
        float(credit.get() or 0),
        mode.get(),
        narration.get()
        ))

        conn.commit()
        conn.close()

        debit.delete(0,"end")
        credit.delete(0,"end")
        narration.delete(0,"end")

        load_data()


    tk.Button(entry,text="Save",bg="green",fg="white",
              command=save).grid(row=0,column=6,padx=5)


# ---------- TABLE ----------

    cols=("Date","Ledger","Debit","Credit","Mode","Narration")

    tree = ttk.Treeview(win,columns=cols,show="headings")

    for c in cols:
        tree.heading(c,text=c)
        tree.column(c,width=120)

    tree.pack(fill="both",expand=True)


# ---------- LOAD DATA ----------

    def load_data():

        for i in tree.get_children():
            tree.delete(i)

        conn=db()
        c=conn.cursor()

        c.execute("""
        SELECT date,ledger,debit,credit,mode,narration
        FROM general_ledger
        ORDER BY id DESC
        """)

        rows=c.fetchall()

        for r in rows:
            tree.insert("",tk.END,values=r)

        conn.close()

    load_data()


# ---------- CLOSE ----------

    tk.Button(win,text="Close",
              bg="red",fg="white",
              command=win.destroy).pack(pady=5)