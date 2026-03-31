import os
import shutil
import tkinter as tk
from tkinter import ttk, messagebox
from database import db
from tkcalendar import DateEntry
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from tkinter import filedialog
import shutil
import os


# ---------- AUTO BACKUP ----------
def auto_backup():

    if not os.path.exists("backup"):
        os.makedirs("backup")

    today=datetime.now().strftime("%Y%m%d")

    source="finance.db"
    dest=f"backup/finance_{today}.db"

    if os.path.exists(source) and not os.path.exists(dest):
        shutil.copy(source,dest)


# ---------- MAIN LEDGER ----------
def open_ledger(loan_id=None):

    if loan_id is None:
        return

    auto_backup()

    win=tk.Toplevel()
    win.title("Member Ledger")
    win.state("zoomed")
    
    conn=db()
    c=conn.cursor()

    c.execute("""
    SELECT members.name,
    members.mobile,
    members.guarantor1,
    members.document,
    loans.account_no,
    loans.loan_amount,
    loans.installment
    FROM loans
    JOIN members ON loans.member_id=members.id
    WHERE loans.id=?
    """,(loan_id,))

    info=c.fetchone()


# ---------- MEMBER INFO ----------
    top=tk.Frame(win)
    top.pack(fill="x", pady=5)

    top.grid_columnconfigure(3, weight=1)

    tk.Label(top,text=f"Name : {info[0]}",font=("Arial",18,"bold")).grid(row=0,column=0,padx=20)

    mobile = str(info[1]).replace(",", "")
    
    tk.Label(top,text=f"Mobile : {mobile}").grid(row=0,column=1,padx=20)

    tk.Label(top,text=f"Guarantor : {info[2]}",font=("Arial",10,"bold")).grid(row=0,column=2,padx=20)

    tk.Button(
        top,
        text="Documents",
        bg="purple",
        fg="white",
        width=12,
        command=lambda: open_document_manager(info[4])
    ).grid(row=0,column=3,padx=20)

    tk.Label(top,text=f"Account : {info[4]}").grid(row=1,column=0,padx=20)

    tk.Label(top,text=f"Loan : {info[5]}").grid(row=1,column=1,padx=20)

    tk.Label(top,text=f"Installment : {info[6]}").grid(row=1,column=2,padx=20)


# ---------- SEARCH ----------
    search_frame = tk.Frame(win)
    search_frame.pack(pady=5)

    tk.Label(search_frame,text="Search").grid(row=0,column=0)

    search_var = tk.StringVar()
    search_entry = tk.Entry(search_frame,textvariable=search_var,width=20)
    search_entry.grid(row=0,column=1,padx=5)
    def focus_search(event=None):
        search_entry.focus_set()

    win.bind("<Control-f>",focus_search)

    tk.Label(search_frame,text="From").grid(row=0,column=2)
    tk.Label(search_frame,text="Amount").grid(row=0,column=6)

    amount_var = tk.StringVar()
    amount_entry = tk.Entry(search_frame,textvariable=amount_var,width=10)
    amount_entry.grid(row=0,column=7,padx=5)

    from_date = DateEntry(search_frame,width=12,date_pattern="yyyy-mm-dd")
    from_date.grid(row=0,column=3,padx=5)

    tk.Label(search_frame,text="To").grid(row=0,column=4)

    to_date = DateEntry(search_frame,width=12,date_pattern="yyyy-mm-dd")
    to_date.grid(row=0,column=5,padx=5)

    from_date.set_date("2000-01-01")
    to_date.set_date(datetime.now().strftime("%Y-%m-%d"))




    # ---------- TABLE ----------
    cols=("Date","Debit","Credit","Mode","Narration","Balance")

    tree=ttk.Treeview(win,columns=cols,show="headings")

    for col in cols:
        tree.heading(col,text=col)
        tree.column(col,width=150,anchor="center")

    tree.pack(fill="both",expand=True)

    tree.tag_configure("collection",background="#e8ffe8")
    tree.tag_configure("today",background="#fff2a8")
    tree.tag_configure("overdue",background="#ffd6d6")


# ---------- LOAD LEDGER ----------
    def load_ledger():

        for i in tree.get_children():
            tree.delete(i)

        balance = 0
        total_credit = 0

        conn=db()
        c=conn.cursor()

        c.execute("""
        SELECT id,date,debit,credit,mode,narration
        FROM transactions
        WHERE loan_id=?
        ORDER BY rowid
        """,(loan_id,))

        rows=c.fetchall()

        balance=0
        total_credit=0

        keyword=search_var.get().lower()
        amt_filter = amount_var.get()
        from_d = None
        to_d = None

        if from_date.get():
            from_d = datetime.strptime(from_date.get(), "%Y-%m-%d").date()

        if to_date.get():
            to_d = datetime.strptime(to_date.get(), "%Y-%m-%d").date()

                
        today = datetime.now().date()

        for r in rows:

            debit = "" if r[2] == 0 else r[2]
            credit = "" if r[3] == 0 else r[3]
            mode = r[4] or ""
            narration = r[5] or ""

            try:
                row_date = datetime.strptime(r[1], "%Y-%m-%d").date()
            except:
                row_date = today

            # search keyword filter
            if keyword and keyword not in str(r).lower():
                continue

            # amount filter
            if amt_filter:
                if amt_filter not in str(r[2]) and amt_filter not in str(r[3]):
                    continue

            # from date filter
            if from_d is not None and row_date < from_d:
                continue

            # to date filter
            if to_d is not None and row_date > to_d:
                continue

            balance = balance + (r[2] or 0) - (r[3] or 0)
            total_credit += (r[3] or 0)

            if row_date == today and r[3] > 0:
                tag = "today"
            elif r[3] > 0:
                tag = "collection"
            else:
                tag = ""

            tree.insert(
                "",
                tk.END,
                iid=r[0],
                values=(r[1], debit, credit, mode, narration, balance),
                tags=(tag,)
            )

        conn.close()

        # Pending / Penalty calculation
        if balance < 0:
            pending = 0
            penalty = abs(balance)
        else:
            pending = balance
            penalty = 0


        # Close button logic
        if pending == 0:
            close_btn.config(state="normal")
        else:
            close_btn.config(state="disabled")


        # Labels update
        total_label.config(text=f"Total Collection : {total_credit}")
        pending_label.config(text=f"Pending : {pending}")
        penalty_label.config(text=f"Penalty : {penalty}")

    search_var.trace("w",lambda *args:load_ledger())

    amount_var.trace("w", lambda *args: load_ledger())

    from_date.bind("<<DateEntrySelected>>", lambda e: load_ledger())

    to_date.bind("<<DateEntrySelected>>", lambda e: load_ledger())


# ---------- RIGHT CLICK MENU ----------
    menu=tk.Menu(win,tearoff=0)

    def show_menu(event):

        item=tree.identify_row(event.y)

        if item:
            tree.selection_set(item)
            tree.focus(item)
            menu.post(event.x_root,event.y_root)

    tree.bind("<Button-3>",show_menu)


# ---------- EDIT ENTRY ----------
    def edit_entry():

        selected = tree.selection()

        if not selected:
            return

        item = selected[0]
        txn_id = item
        
        data=tree.item(item)["values"]

        date=data[0]
        debit=data[1] or 0
        credit=data[2] or 0
        mode=data[3] or ""

        edit=tk.Toplevel(win)
        edit.title("Edit Entry")

        tk.Label(edit,text="Date").pack()
        date_var=tk.StringVar(value=date)
        tk.Entry(edit,textvariable=date_var).pack()

        tk.Label(edit,text="Debit").pack()
        debit_var=tk.StringVar(value=debit)
        tk.Entry(edit,textvariable=debit_var).pack()

        tk.Label(edit,text="Credit").pack()
        credit_var=tk.StringVar(value=credit)
        tk.Entry(edit,textvariable=credit_var).pack()

        tk.Label(edit,text="Mode").pack()

        mode_var=tk.StringVar(value=mode)

        ttk.Combobox(
            edit,
            textvariable=mode_var,
            values=["Cash","Bank"]
        ).pack()

        def save_edit():

            conn=db()
            c=conn.cursor()

            c.execute("""
            UPDATE transactions
            SET date=?,debit=?,credit=?,mode=?
            WHERE id=?
            """,(
                date_var.get(),
                float(debit_var.get()),
                float(credit_var.get()),
                mode_var.get(),
                txn_id
            ))

            conn.commit()
            conn.close()

            edit.destroy()
            load_ledger()

            amt_entry.delete(0,tk.END)
            narr_entry.delete(0,tk.END)
       
        tk.Button(edit,text="Save",command=save_edit).pack(pady=10)


# ---------- DELETE ENTRY ----------
    def delete_entry():

        selected = tree.selection()

        if not selected:
            return

        item = selected[0]
        txn_id = item

        confirm = messagebox.askyesno("Delete","Delete this entry?",parent=win)

        if not confirm:
            return

        conn=db()
        c=conn.cursor()

        c.execute(
            "DELETE FROM transactions WHERE id=?",
            (txn_id,)
        )

        conn.commit()
        conn.close()

        load_ledger()

    menu.add_command(label="Edit Entry",command=edit_entry)
    menu.add_command(label="Delete Entry",command=delete_entry)


# ---------- INSTALLMENT ENTRY ----------
    entry_frame=tk.Frame(win)
    entry_frame.pack(pady=10)

    tk.Label(entry_frame,text="Date").grid(row=0,column=0)
    tk.Label(entry_frame,text="Install Amount").grid(row=0,column=2)

    def add_debit():

        amt=amt_entry.get()

        if amt=="":
            messagebox.showerror("Error","Enter amount",parent=win)
            return

        conn=db()
        c=conn.cursor()

        c.execute("""
        INSERT INTO transactions(date,debit,credit,loan_id,mode,narration)
        VALUES(?,?,?,?,?,?)
        """,(date_entry.get(),float(amt),0,loan_id,mode_var.get(),narr_entry.get()))

        conn.commit()
        conn.close()

        load_ledger()

    date_entry=DateEntry(entry_frame,width=12,date_pattern="yyyy-mm-dd")
    date_entry.grid(row=0,column=1)

    tk.Label(entry_frame,text="Narration").grid(row=0,column=6)

    narr_entry=tk.Entry(entry_frame,width=20)
    narr_entry.grid(row=0,column=7)

    amt_entry=tk.Entry(entry_frame,width=12)
    amt_entry.grid(row=0,column=3)

    mode_var=tk.StringVar(value="Cash")

    mode_box=ttk.Combobox(
        entry_frame,
        textvariable=mode_var,
        values=["Cash","Bank"],
        width=10
    )
    mode_box.grid(row=0,column=4)

    def save_installment():

        amt=amt_entry.get()

        if amt=="":
            messagebox.showerror("Error","Enter amount",parent=win)
            return

        conn=db()
        c=conn.cursor()

        c.execute("""
        INSERT INTO transactions(date,debit,credit,loan_id,mode,narration)
        VALUES(?,?,?,?,?,?)
        """,(date_entry.get(),0,float(amt),loan_id,mode_var.get(),narr_entry.get()))

        conn.commit()
        conn.close()

        load_ledger()

        amt_entry.delete(0,tk.END)
        narr_entry.delete(0,tk.END)

    tk.Button(entry_frame,text="Save Installment",
              bg="green",fg="white",
              command=save_installment)\
        .grid(row=0,column=5,padx=10)

    tk.Button(
        entry_frame,
        text="Add Debit",
        bg="orange",
        fg="white",
        command=add_debit
    ).grid(row=0,column=8,padx=10)


# ---------- PRINT LEDGER ----------
    import tempfile
    import webbrowser
    
    def print_ledger():

        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")

        filename = temp_file.name

        pdf=canvas.Canvas(filename,pagesize=letter)

        width,height=letter

        pdf.setFont("Helvetica-Bold",16)
        pdf.drawString(200,height-60,"Member Ledger")

        pdf.setFont("Helvetica",10)

        pdf.drawString(40,height-100,f"Name : {info[0]}")
        pdf.drawString(40,height-120,f"Account : {info[4]}")
        pdf.drawString(40,height-140,f"Loan Amount : {info[5]}")
        
        y = height - 220

        for row in tree.get_children():

            data = tree.item(row)["values"]
            
            pdf.drawString(40, y, str(data[0]))   # Date
            pdf.drawString(110, y, str(data[1]))  # Debit
            pdf.drawString(170, y, str(data[2]))  # Credit
            pdf.drawString(240, y, str(data[3]))  # Mode
            pdf.drawString(310, y, str(data[4]))  # Narration
            pdf.drawString(470, y, str(data[5]))  # Balance
            
            y -= 18

        pdf.drawString(40,60,total_label.cget("text"))
        pdf.drawString(40,40,pending_label.cget("text"))

        pdf.save()

        webbrowser.open(filename)

    
    def close_account():

        confirm = messagebox.askyesno(
            "Confirm",
            "Are you sure you want to close this account?"
        )

        if not confirm:
            return

        conn=db()
        c=conn.cursor()

        c.execute(
            "UPDATE loans SET status='Closed' WHERE id=?",
            (loan_id,)
        )

        conn.commit()
        conn.close()

        messagebox.showinfo("Closed","Account Closed Successfully")

        win.destroy()

    def edit_loan():

        edit_win = tk.Toplevel()
        edit_win.title("Edit Loan")
        edit_win.state("zoomed")

        tk.Label(edit_win,text="Loan Amount").pack(pady=5)
        loan_entry = tk.Entry(edit_win)
        loan_entry.pack()

        tk.Label(edit_win,text="Installment").pack(pady=5)
        inst_entry = tk.Entry(edit_win)
        inst_entry.pack()

        loan_entry.insert(0,str(info[5]))
        inst_entry.insert(0,str(info[6]))

        def update():

            new_loan=float(loan_entry.get())
            new_inst=float(inst_entry.get())

            conn=db()
            c=conn.cursor()

            c.execute("""
            UPDATE loans
            SET loan_amount=?,installment=?
            WHERE id=?
            """,(new_loan,new_inst,loan_id))

            conn.commit()
            conn.close()

            messagebox.showinfo("Updated","Loan updated successfully")

            edit_win.destroy()

        tk.Button(edit_win,text="Update",command=update,width=15).pack(pady=10)

# ---------- BUTTONS ----------
     
    tk.Button(win,
        text="Print Ledger",
        bg="blue",
        fg="white",
        command=print_ledger).pack(pady=5)

    tk.Button(
        win,
        text="Edit Loan",
        bg="orange",
        fg="black",
        width=15,
        command=edit_loan
    ).pack(pady=5)    

    close_btn = tk.Button(
        win,
        text="Close Account",
        bg="red",
        fg="white",
        state="disabled",
        command=close_account
    )
    
    close_btn.pack(pady=5)


# ---------- SUMMARY ----------
    bottom=tk.Frame(win)
    bottom.pack(pady=5)

    total_label=tk.Label(bottom,font=("Arial",10,"bold"))
    total_label.pack()

    pending_label=tk.Label(bottom,font=("Arial",10,"bold"))
    pending_label.pack()

    penalty_label=tk.Label(bottom,font=("Arial",10,"bold"),fg="red")
    penalty_label.pack()

    tk.Button(win,text="Close",
              bg="red",fg="white",
              command=win.destroy).pack(pady=10)

    load_ledger()

        

def open_document_manager(account):

    folder = os.path.join("documents", account)

    os.makedirs(folder, exist_ok=True)

    doc_win = tk.Toplevel()
    doc_win.title("Document Manager")
    doc_win.state("zoomed")

    listbox = tk.Listbox(doc_win, width=60, height=15)
    listbox.pack(pady=10)

    def load_docs():

        listbox.delete(0, tk.END)

        files = os.listdir(folder)

        for f in files:
            listbox.insert(tk.END, f)

    load_docs()

    # ---------- Upload ----------
    def upload_doc():

        file = filedialog.askopenfilename()

        if not file:
            return

        name = os.path.basename(file)

        shutil.copy(file, os.path.join(folder, name))

        load_docs()

    # ---------- Open ----------
    def open_doc():

        selected = listbox.curselection()

        if not selected:
            return

        file = listbox.get(selected[0])

        os.startfile(os.path.join(folder, file))

    # ---------- Delete ----------
    def delete_doc():

        selected = listbox.curselection()

        if not selected:
            return

        file = listbox.get(selected[0])

        os.remove(os.path.join(folder, file))

        load_docs()

    tk.Button(doc_win, text="Upload", width=15, command=upload_doc).pack(pady=5)
    tk.Button(doc_win, text="Open", width=15, command=open_doc).pack(pady=5)
    tk.Button(doc_win, text="Delete", width=15, command=delete_doc).pack(pady=5)
