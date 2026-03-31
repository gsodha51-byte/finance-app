
import tkinter as tk
from ui.dashboard import dashboard

def login_screen():

    win=tk.Tk()
    win.title("GS Finance Login")

    tk.Label(win,text="Username").pack()
    user=tk.Entry(win); user.pack()

    tk.Label(win,text="Password").pack()
    pwd=tk.Entry(win,show="*"); pwd.pack()

    def login():
        role="operator"
        if user.get()=="admin":
            role="admin"
        win.destroy()
        dashboard(role)

    tk.Button(win,text="Login",command=login).pack(pady=10)
    win.mainloop()
