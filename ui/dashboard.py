import tkinter as tk
from ui.member_menu import member_menu
from ui.daybook import open_daybook
from ui.summary import open_summary
from database import db
from tkinter import ttk, messagebox
from ui.members import add_member
from ui.general_ledger import open_general_ledger
from ui.personal_ledger import open_personal_ledgers
from ui.excel_import import import_excel_data
from ui.members import add_member_dds
from ui.members import add_member_daily
from ui.members import add_member_monthly


def dashboard(role):
    
    win=tk.Tk()
    win.title("GS Finance Dashboard")

    current_window = None

    def open_window(func):

        nonlocal current_window

        if current_window is not None:
            try:
                current_window.destroy()
            except:
                pass

        current_window = func()

    tk.Label(win,text=f"Dashboard ({role})",font=("Arial",18)).pack(pady=20)

    tk.Button(
        win,
        text="Add Member",
        width=30,
        command=lambda:open_window(add_member_menu)
    ).pack(pady=6)

    tk.Button(
        win,
        text="Search Member",
        width=30,
        command=lambda:open_window(member_menu)
    ).pack(pady=6)

    tk.Button(
        win,
        text="Daybook",
        width=30,
        command=lambda:open_window(open_daybook)
    ).pack(pady=6)

    tk.Button(
        win,
        text="Loan Summary",
        width=30,
        command=lambda:open_window(open_summary)
    ).pack(pady=6)

    tk.Button(
        win,
        text="General Ledger",
        width=30,
        bg="#6c757d",
        fg="white",
        command=open_general_ledger
    ).pack(pady=6)

    tk.Button(
        win,
        text="Personal Ledger",
        width=30,
        command=open_personal_ledgers
    ).pack(pady=6)

    tk.Button(
        win,
        text="Import Excel Data",
        width=30,
        command=import_excel_data
    ).pack(pady=6)
    # ---- NEW BUTTON ----

    tk.Button(
        win,
        text="Close Account",
        width=30,
        bg="red",
        fg="white",
        command=lambda:open_window(close_account_menu)
    ).pack(pady=6)

    win.mainloop()

def add_member_menu():

    win = tk.Toplevel()
    win.title("Add Member - Select Loan Typ")
    win.state("zoomed")

    tk.Label(win,text="Add Member - Select Loan Typ",
             font=("Arial",12,"bold")).pack(pady=15)

    tk.Button(win,text="DDS",
              width=20,
              command=lambda:[win.destroy(), add_member_dds()]).pack(pady=5)

    tk.Button(win,text="Daily Loan",
              width=20,
              command=lambda:[win.destroy(), add_member_daily()]).pack(pady=5)

    tk.Button(win,text="Monthly",
              width=20,
              command=lambda:[win.destroy(), add_member_monthly()]).pack(pady=5)
    
    return win
# ---------------- CLOSE ACCOUNT MENU ----------------

def close_account_menu():

    win = tk.Toplevel()
    win.title("Close Account")
    win.state("zoomed")

    tk.Label(win,text="Select Loan Type",
             font=("Arial",12,"bold")).pack(pady=10)

    tk.Button(win,text="DDS",
              width=20,
              command=lambda:close_account_window("DDS")).pack(pady=5)

    tk.Button(win,text="Daily",
              width=20,
              command=lambda:close_account_window("Daily")).pack(pady=5)

    tk.Button(win,text="Monthly",
              width=20,
              command=lambda:close_account_window("Monthly")).pack(pady=5)

    return win
# ---------------- CLOSE ACCOUNT WINDOW ----------------

def close_account_window(loan_type):

    win = tk.Toplevel()
    win.title(f"Closed {loan_type} Accounts")
    win.state("zoomed")

    cols=("LoanID","Name","Mobile","Loan")

    tree=ttk.Treeview(win,columns=cols,show="headings")

    for c in cols:
        tree.heading(c,text=c)
        tree.column(c,width=120)

    tree.pack(fill="both",expand=True)
    
    conn=db()
    c=conn.cursor()

    c.execute("""
    SELECT loans.id,
    members.name,
    members.mobile,
    loans.loan_amount
    FROM loans
    JOIN members ON members.id=loans.member_id
    WHERE loans.installment_type=? AND loans.status='Closed'
    """,(loan_type,))

    rows=c.fetchall()

    for r in rows:
        tree.insert("",tk.END,values=r)

    conn.close()

    # -------- OPEN LEDGER ON DOUBLE CLICK --------

    def open_selected(event=None):

        item = tree.focus()

        if not item:
            return

        data = tree.item(item)["values"]

        loan_id = data[0]

        from ui.ledger import open_ledger
        open_ledger(loan_id)

    tree.bind("<Double-1>", open_selected)


    # -------- REOPEN ACCOUNT --------

    def reopen_account():

        item = tree.focus()

        if not item:
            messagebox.showwarning("Warning","Select account first")
            return

        data = tree.item(item)["values"]

        loan_id = data[0]

        confirm = messagebox.askyesno(
            "Confirm",
            "Reopen this account?"
        )

        if not confirm:
            return

        conn=db()
        c=conn.cursor()

        c.execute(
            "UPDATE loans SET status='Running' WHERE id=?",
            (loan_id,)
        )

        conn.commit()
        conn.close()

        tree.delete(item)

        messagebox.showinfo("Success","Account Reopened")


    # -------- CLOSE ACCOUNT (OLD CODE KE LIYE SAFE) --------

    def close_selected():

        item = tree.focus()

        if not item:
            messagebox.showwarning("Warning","Select account first")
            return

        data = tree.item(item)["values"]

        loan_id = data[0]

        conn=db()
        c=conn.cursor()

        c.execute(
            "UPDATE loans SET status='Closed' WHERE id=?",
            (loan_id,)
        )

        conn.commit()
        conn.close()

        tree.delete(item)

        messagebox.showinfo("Closed","Account Closed")


    # -------- BUTTONS --------

    tk.Button(win,text="Reopen Account",
              bg="green",
              fg="white",
              command=reopen_account).pack(pady=5)

    tk.Button(win,text="Close Account",
              bg="red",
              fg="white",
              command=close_selected).pack(pady=5)

    return win
    