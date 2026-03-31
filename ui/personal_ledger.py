import tkinter as tk
from tkinter import ttk,messagebox,simpledialog
from tkcalendar import DateEntry
from database import db


def open_personal_ledgers():

    win = tk.Toplevel()
    win.title("Personal Ledgers")
    win.state("zoomed")

    listbox = tk.Listbox(win,font=("Arial",12))
    listbox.pack(fill="both",expand=True,padx=10,pady=10)


# ---------- LOAD ----------

    def load():

        listbox.delete(0,"end")

        conn=db()
        c=conn.cursor()

        c.execute("SELECT id,name FROM personal_ledgers")

        rows=c.fetchall()

        for r in rows:
            listbox.insert("end",f"{r[0]} - {r[1]}")

        conn.close()


# ---------- ADD PERSON ----------

    def add_person():

        name = simpledialog.askstring("Name","Enter Person Name")

        if not name:
            return

        conn=db()
        c=conn.cursor()

        c.execute("INSERT INTO personal_ledgers(name) VALUES(?)",(name,))

        conn.commit()
        conn.close()

        load()


# ---------- OPEN LEDGER ----------

    def open_ledger(event):

        item=listbox.get(listbox.curselection())

        ledger_id=int(item.split("-")[0])
        name=item.split("-")[1].strip()

        open_person_ledger_window(ledger_id,name)


    listbox.bind("<Double-1>",open_ledger)


    tk.Button(win,text="Add Person",
              bg="green",fg="white",
              command=add_person).pack(pady=5)


    load()


# ---------- LEDGER WINDOW ----------

def open_person_ledger_window(ledger_id,name):

    win=tk.Toplevel()
    win.title(f"{name} Ledger")
    win.state("zoomed")


# ENTRY

    top=tk.Frame(win)
    top.pack(pady=10)

    date=DateEntry(top,date_pattern="yyyy-mm-dd")
    date.grid(row=0,column=0,padx=5)

    debit=tk.Entry(top,width=10)
    debit.grid(row=0,column=1,padx=5)

    credit=tk.Entry(top,width=10)
    credit.grid(row=0,column=2,padx=5)

    mode=ttk.Combobox(top,values=["Cash","Bank"],width=8)
    mode.grid(row=0,column=3,padx=5)

    narration=tk.Entry(top,width=25)
    narration.grid(row=0,column=4,padx=5)


# SAVE

    def save():

        conn=db()
        c=conn.cursor()

        c.execute("""
        INSERT INTO personal_transactions
        (ledger_id,date,debit,credit,mode,narration)
        VALUES(?,?,?,?,?,?)
        """,(
        ledger_id,
        date.get(),
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

        load()


    tk.Button(top,text="Save",bg="green",fg="white",
              command=save).grid(row=0,column=5,padx=5)


# TABLE

    cols=("Date","Debit","Credit","Mode","Narration","Balance")

    tree=ttk.Treeview(win,columns=cols,show="headings")

    for c in cols:
        tree.heading(c,text=c)
        tree.column(c,width=110)

    tree.pack(fill="both",expand=True)


# LOAD

    def load():

        for i in tree.get_children():
            tree.delete(i)

        conn=db()
        c=conn.cursor()

        c.execute("""
        SELECT date,debit,credit,mode,narration
        FROM personal_transactions
        WHERE ledger_id=?
        """,(ledger_id,))

        rows=c.fetchall()

        balance=0

        for r in rows:

            balance=balance+(r[1] or 0)-(r[2] or 0)

            tree.insert("",tk.END,values=(
            r[0],r[1],r[2],r[3],r[4],balance
            ))

        conn.close()


    load()