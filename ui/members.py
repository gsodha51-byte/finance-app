import tkinter as tk
from tkinter import messagebox, ttk
from database import db
from utils.account import generate_account_no
from datetime import datetime, timedelta
from ui.ledger import open_ledger
from tkinter import filedialog
import shutil
import os


# ---------------- DAILY COLLECTION WINDOW ----------------

def daily_collection():

    win = tk.Toplevel()
    win.title("Daily Collection")
    win.state("zoomed")

    cols=("Member","Amount","Mode")

    tree=ttk.Treeview(win,columns=cols,show="headings",selectmode="browse")

    for c in cols:
        tree.heading(c,text=c)
        tree.column(c,width=150)

    tree.pack(fill="both",expand=True)

    today=datetime.now().strftime("%Y-%m-%d")

    conn=db()
    c=conn.cursor()

    c.execute("""
    SELECT members.name,transactions.credit,transactions.mode
    FROM transactions
    JOIN loans ON transactions.loan_id=loans.id
    JOIN members ON loans.member_id=members.id
    WHERE transactions.date=? AND transactions.credit>0
    """,(today,))

    rows=c.fetchall()

    total=0
    cash_total = 0
    bank_total = 0

    for r in rows:
        tree.insert("",tk.END,values=r)
        total+=r[1]

        if r[2] == "Cash":
            cash_total += r[1]

        if r[2] == "Bank":
            bank_total += r[1]

    conn.close()

    tk.Label(win,text=f"Total Collection : {total}",
             font=("Arial",11,"bold")).pack(pady=5)

    summary = tk.Frame(win)
    summary.pack()

    tk.Label(summary,text=f"Cash : {cash_total}",
             font=("Arial",11,"bold")).pack()

    tk.Label(summary,text=f"Bank : {bank_total}",
             font=("Arial",11,"bold")).pack()

    tk.Label(summary,text=f"Total Collection : {total}",
             font=("Arial",12,"bold")).pack()


# ---------------- ADD MEMBER ----------------

def add_member_dds():

    win = tk.Toplevel()
    win.title("Add DDS Member")

    name = tk.Entry(win)
    father = tk.Entry(win)
    village = tk.Entry(win)
    mobile1 = tk.Entry(win)
    mobile2 = tk.Entry(win)

    labels = [
        ("Name*", name),
        ("Father*", father),
        ("Village*", village),
        ("Mobile No. 1*", mobile1),
        ("Mobile No. 2", mobile2)
    ]

    for i,(t,e) in enumerate(labels):
        tk.Label(win,text=t).grid(row=i,column=0,padx=5,pady=5,sticky="w")
        e.grid(row=i,column=1,padx=5,pady=5)

    def save():

        if name.get()=="":
            messagebox.showerror("Error","Name required")
            return

        conn=db()
        c=conn.cursor()

        # save member
        c.execute("""
        INSERT INTO members(name,father,village,mobile,guarantor1,guarantor2,document)
        VALUES(?,?,?,?,?,?,?)
        """,(
        name.get(),
        father.get(),
        village.get(),
        mobile1.get()+","+mobile2.get(),
        "",
        "",
        ""
        ))

        member_id=c.lastrowid

        # generate account
        c.execute("SELECT COUNT(*) FROM loans")
        n=c.fetchone()[0]+1

        acc=generate_account_no(n)

        # create DDS loan account
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
        """,(
        acc,
        member_id,
        0,
        0,
        "DDS",
        "",
        "Running"
        ))

        conn.commit()
        conn.close()

        messagebox.showinfo("Success","DDS Member Saved")
        win.destroy()

    tk.Button(
        win,
        text="Save Member",
        command=save,
        width=20,
        bg="#28a745",
        fg="white",
        font=("Arial",10,"bold"),
        activebackground="#218838",
        activeforeground="white"
    ).grid(row=6,column=1,pady=10)

def add_member_daily():
    add_member("Daily")

def add_member_monthly():
    add_member("Monthly")

# ---------------- DAILY / MONTHLY MEMBER ----------------

def add_member(loan_type=None):

    win = tk.Toplevel()
    win.title("Add Member")

    name = tk.Entry(win)
    father = tk.Entry(win)
    village = tk.Entry(win)

    mobile = tk.Entry(win)
    mobile2 = tk.Entry(win)

    g1 = tk.Entry(win)
    g1_mobile = tk.Entry(win)

    g2 = tk.Entry(win)
    g2_mobile = tk.Entry(win)

    principal = tk.Entry(win)
    interest = tk.Entry(win)
    total_amount = tk.Entry(win,state="readonly")

    installment = tk.Entry(win)

    duration = tk.Entry(win,state="readonly")

    installment_type = tk.StringVar()

    installment_box = ttk.Combobox(
        win,
        textvariable=installment_type,
        values=["DDS","Daily","Monthly"],
        state="readonly",
        width=20
    )

    if loan_type:
        installment_type.set(loan_type)

    installment_box.grid(row=12,column=1)

    labels = [
        ("Name*", name),
        ("Father*", father),
        ("Village*", village),
        ("Mobile 1*", mobile),
        ("Mobile 2", mobile2),
        ("Guarantor1*", g1),
        ("Guarantor1 Mobile", g1_mobile),
        ("Guarantor2", g2),
        ("Guarantor2 Mobile", g2_mobile)
    ]

    for i,(t,e) in enumerate(labels):
        tk.Label(win,text=t).grid(row=i,column=0,padx=5,pady=5,sticky="w")
        e.grid(row=i,column=1,padx=5,pady=5)

    start=len(labels)

    tk.Label(win,text="Principal Amount").grid(row=start,column=0)
    principal.grid(row=start,column=1)

    tk.Label(win,text="Interest").grid(row=start+1,column=0)
    interest.grid(row=start+1,column=1)

    tk.Label(win,text="Total Loan").grid(row=start+2,column=0)
    total_amount.grid(row=start+2,column=1)

    tk.Label(win,text="Installment").grid(row=start+3,column=0)
    installment.grid(row=start+3,column=1)

    tk.Label(win,text="Loan Duration (Months)").grid(row=start+4,column=0)
    duration.grid(row=start+4,column=1)

    tk.Label(win,text="Installment Type").grid(row=start+5,column=0)
    installment_box.grid(row=start+5,column=1)

    doc_path = tk.StringVar()

    tk.Label(win,text="Document").grid(row=start+6,column=0)

    doc_entry = tk.Entry(win,textvariable=doc_path,width=25,state="readonly")
    doc_entry.grid(row=start+6,column=1)

    def upload_doc():
        file = filedialog.askopenfilename(filetypes=[("All Files","*.*")])
        if file:
            doc_path.set(file)

    tk.Button(win,text="Upload",command=upload_doc).grid(row=start+6,column=2)

    # -------- AUTO TOTAL --------

    def calculate_total(event=None):

        try:
            p=float(principal.get() or 0)
            i=float(interest.get() or 0)

            total=p+i

            total_amount.config(state="normal")
            total_amount.delete(0,"end")
            total_amount.insert(0,str(total))
            total_amount.config(state="readonly")

        except:
            pass

        try:
            loan=float(total_amount.get() or 0)
            inst=float(installment.get() or 0)

            if inst>0:
                d=loan/inst

                duration.config(state="normal")
                duration.delete(0,"end")
                duration.insert(0,str(int(d)))
                duration.config(state="readonly")

        except:
            pass

    principal.bind("<KeyRelease>",calculate_total)
    interest.bind("<KeyRelease>",calculate_total)
    installment.bind("<KeyRelease>",calculate_total)

    def save():

        if name.get()=="":
            messagebox.showerror("Error","Name required")
            return

        conn=db()
        c=conn.cursor()

        c.execute("""
        INSERT INTO members(name,father,village,mobile,guarantor1,guarantor2,document)
        VALUES(?,?,?,?,?,?,?)
        """,(
        name.get(),
        father.get(),
        village.get(),
        mobile.get()+","+mobile2.get(),
        g1.get(),
        g2.get(),
        doc_path.get()
        ))

        member_id=c.lastrowid

        c.execute("SELECT COUNT(*) FROM loans")
        n=c.fetchone()[0]+1

        acc=generate_account_no(n)

        loan_amount=float(total_amount.get() or 0)
        installment_amount=float(installment.get() or 0)

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
        """,(
        acc,
        member_id,
        loan_amount,
        installment_amount,
        installment_type.get(),
        "",
        "Running"
        ))

        loan_id=c.lastrowid

        today=datetime.now()

        
        conn.commit()
        conn.close()

        messagebox.showinfo("Success","Member Saved")
        win.destroy()

    tk.Button(
        win,
        text="Save Member",
        command=save,
        width=20,
        bg="#28a745",
        fg="white",
        font=("Arial",10,"bold"),
        activebackground="#218838",
        activeforeground="white"
    ).grid(row=start+8,column=1,pady=10)



# ---------------- SEARCH + COLLECTION ----------------

def search_member(loan_type=None):

    win = tk.Toplevel()

    if loan_type:
        win.title(f"{loan_type}")
    else:
        win.title("Member Search + Collection")
    win.state("zoomed")

    search=tk.Entry(win,width=30)
    search.pack(pady=5)

    cols = ("LoanID","Name","Mobile","Start Date","Loan","Inst",
      "d1","d2","d3","d4","d5","d6","d7","d8","d9","d10",
      "Today","Total","Pending","Due")

    tree=ttk.Treeview(win,columns=cols,show="headings",selectmode="browse")

    today=datetime.now()
    today_str=today.strftime("%Y-%m-%d")

    from dateutil.relativedelta import relativedelta

    if loan_type == "Daily":

        last_days=[(today-timedelta(days=i)).strftime("%Y-%m-%d") for i in range(10,0,-1)]

    elif loan_type == "Monthly":

        # -------- LAST 10 PERIODS --------

        if loan_type == "Monthly":

            last_days = [
            (today - relativedelta(months=i)).strftime("%Y-%m")
            for i in range(0,10)
            ]

            last_days.reverse()

        else:   # Daily / DDS

            last_days = [
                (today - timedelta(days=i)).strftime("%Y-%m-%d")
                for i in range(9,-1,-1)
            ]

    else:   # DDS

        last_days=[(today-timedelta(days=i)).strftime("%Y-%m-%d") for i in range(10,0,-1)]

    heads=["LoanID","Name","Mobile","Start Date","Loan","Inst"] + last_days + ["Today","Total","Pending","Due"]

    for c,h in zip(cols,heads):
        tree.heading(c,text=h)
        tree.column(c,width=70,anchor="center")

    tree.pack(fill="both",expand=True)

    btn_frame = tk.Frame(win)
    btn_frame.pack(pady=10)

    tk.Button(btn_frame,text="Daily Collection",
              bg="orange",
              command=daily_collection).pack(side="left",padx=5)


    def delete_member():

        selected = tree.selection()

        if not selected:
            messagebox.showwarning("Warning","Select a member first")
            return

        item = selected[0]
        data = tree.item(item,"values")

        loan_id = data[0]

        confirm = messagebox.askyesno(
            "Confirm Delete",
            "Are you sure you want to delete this member?"
        )

        if not confirm:
            return

        conn = db()
        c = conn.cursor()

        c.execute("DELETE FROM transactions WHERE loan_id=?", (loan_id,))
        c.execute("DELETE FROM loans WHERE id=?", (loan_id,))

        conn.commit()
        conn.close()

        do()

        messagebox.showinfo("Deleted","Member deleted successfully")

    tk.Button(btn_frame,text="Delete Member",
              bg="red",
              fg="white",
              width=15,
              command=delete_member).pack(side="left",padx=5)


    scroll_x = tk.Scrollbar(win, orient="horizontal", command=tree.xview)
    tree.configure(xscrollcommand=scroll_x.set)
    scroll_x.pack(fill="x")

    def edit_loan_type():

        selected = tree.selection()

        if not selected:
            messagebox.showwarning("Warning","Select a row first")
            return

        item = selected[0]
        data = tree.item(item,"values")

        loan_id = data[0]

        # ---- New Window ----
        edit_win = tk.Toplevel()
        edit_win.title("Edit Loan Type")
        edit_win.state("zoomed")

        tk.Label(edit_win,text="Select Loan Type").pack(pady=5)

        loan_type_var = tk.StringVar()

        type_box = ttk.Combobox(
            edit_win,
            textvariable=loan_type_var,
            values=["DDS","Daily","Monthly"],
            state="readonly",
            width=20
        )

        type_box.pack(pady=5)
        type_box.current(0)

        def update():

            new_type = loan_type_var.get()

            conn=db()
            c=conn.cursor()

            c.execute(
                "UPDATE loans SET installment_type=? WHERE id=?",
                (new_type,loan_id)
            )

            conn.commit()
            conn.close()

            edit_win.destroy()

            do()

            messagebox.showinfo("Updated","Loan type updated successfully")

        tk.Button(edit_win,text="Update",command=update,width=15).pack(pady=5)

    def open_selected(event):

        item = tree.identify_row(event.y)

        if not item:
            return

        data = tree.item(item,"values")

        loan_id = data[0]

        open_ledger(loan_id)

    
    def open_selected_enter(event=None):

        selected = tree.selection()

        if not selected:
            return

        item = selected[0]
        data = tree.item(item,"values")

        loan_id = data[0]

        open_ledger(loan_id)

    def open_collection(event=None):

        selected = tree.selection()
        
        if not selected:
            return

        item = selected[0]
        data = tree.item(item,"values")

        loan_id = data[0]

        # collection window
        open_ledger(loan_id)

    def do():

        conn=db()
        c=conn.cursor()

        q="%"+search.get()+"%"

        if loan_type:

            c.execute("""
            SELECT loans.id,
            members.name,
            members.mobile,
            loans.loan_amount,
            loans.installment
            FROM members
            JOIN loans ON members.id=loans.member_id
            WHERE loans.installment_type=?
            AND loans.status='Running'
            AND (
                members.name LIKE ?
                OR members.mobile LIKE ?
                OR loans.account_no LIKE ?
            )
            """,(loan_type,q,q,q))

        else:

            c.execute("""
            SELECT loans.id,
            members.name,
            members.mobile,
            loans.loan_amount,
            loans.installment
            FROM members
            JOIN loans ON members.id=loans.member_id
            WHERE loans.status='Running'
            AND (
            members.name LIKE ?
            OR members.mobile LIKE ?
            OR loans.account_no LIKE ?
            )
            """,(q,q,q))

        rows=c.fetchall()

        tree.delete(*tree.get_children())

        for r in rows:

            loan_id=r[0]

            last10=[]
            for d in last_days:

                if loan_type == "Monthly":

                    c.execute("""
                    SELECT SUM(credit)
                    FROM transactions
                    WHERE loan_id=? AND strftime('%Y-%m',date)=?
                    """,(loan_id,d))

                else:

                    c.execute("""
                    SELECT SUM(credit)
                    FROM transactions
                    WHERE loan_id=? AND date=?
                    """,(loan_id,d))

                last10.append(c.fetchone()[0] or 0)

            c.execute(
            "SELECT SUM(credit) FROM transactions WHERE loan_id=? AND date=?",
            (loan_id,today_str))

            today_amt=c.fetchone()[0] or 0

            total = today_amt + sum(last10)

            pending=max(r[3]-total,0)

            # ---- DUE CALCULATION ----

            # loan start date
            c.execute(
                "SELECT date FROM transactions WHERE loan_id=? AND debit>0 LIMIT 1",
                (loan_id,)
            )
            row = c.fetchone()

            if row:
                start_date = row[0]
                days = (today - datetime.strptime(row[0], "%Y-%m-%d")).days
            else:
                start_date = ""
                days = 0

            expected = r[4] * max(days,0)

            due = max(expected - total,0)

            item = tree.insert("",tk.END,values=(
                loan_id,
                r[1],
                r[2],
                start_date,
                r[3],
                r[4],
                *last10,
                today_amt,
                total,
                pending,
                due
            ))

            if due > 0:
                tree.item(item,tags=("due",))    
        tree.tag_configure("due",foreground="red")            

        conn.close()

    tk.Button(btn_frame,text="Search",command=do,width=12).pack(side="left",padx=5)
    tk.Button(btn_frame,
          text="Edit Loan Type",
          bg="blue",
          fg="white",
          width=15,
          command=edit_loan_type).pack(side="left",padx=5)

    search.bind("<KeyRelease>", lambda e: do())

    tree.bind("<Double-Button-1>", open_selected)
    tree.bind("<Return>", open_selected_enter)
    tree.bind("<space>", open_collection)

    do()