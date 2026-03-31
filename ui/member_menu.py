import tkinter as tk
from ui.member_types.dds import open_dds
from ui.member_types.daily_loan import open_daily
from ui.member_types.monthly import open_monthly

def member_menu():

    win = tk.Toplevel()
    win.title("Search Member - Select Loan Type")
    win.state("zoomed")

    tk.Label(
        win,
        text="Search Member - Select Loan Type",
        font=("Arial",12,"bold")
    ).pack(pady=15)

    tk.Button(
        win,
        text="DDS",
        width=20,
        command=open_dds
    ).pack(pady=5)

    tk.Button(
        win,
        text="Daily Loan",
        width=20,
        command=open_daily
    ).pack(pady=5)

    tk.Button(
        win,
        text="Monthly",
        width=20,
        command=open_monthly
    ).pack(pady=5)
    return win