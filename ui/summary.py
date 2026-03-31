import tkinter as tk
from database import db

def open_summary():

    win=tk.Toplevel()
    win.title("Loan Summary")
    win.state("zoomed")
    
    conn=db()
    c=conn.cursor()

    # DAILY
    c.execute("SELECT COUNT(*),SUM(loan_amount) FROM loans WHERE installment_type='Daily' AND status='Running'")
    daily=c.fetchone()

    # MONTHLY
    c.execute("SELECT COUNT(*),SUM(loan_amount) FROM loans WHERE installment_type='Monthly' AND status='Running'")
    monthly=c.fetchone()

    # DDS
    c.execute("SELECT COUNT(*),SUM(loan_amount) FROM loans WHERE installment_type='DDS' AND status='Running'")
    dds=c.fetchone()

    conn.close()

    tk.Label(win,text="DDS",font=("Arial",14,"bold")).pack(pady=10)
    tk.Label(win,text=f"Members : {dds[0]}").pack()
    tk.Label(win,text=f"Total Amount : {dds[1] or 0}").pack()

    tk.Label(win,text="Daily Loan",font=("Arial",14,"bold")).pack(pady=10)
    tk.Label(win,text=f"Members : {daily[0]}").pack()
    tk.Label(win,text=f"Total Amount : {daily[1] or 0}").pack()

    tk.Label(win,text="Monthly Loan",font=("Arial",14,"bold")).pack(pady=10)
    tk.Label(win,text=f"Members : {monthly[0]}").pack()
    tk.Label(win,text=f"Total Amount : {monthly[1] or 0}").pack()
    
    return win