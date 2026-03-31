from fastapi import FastAPI
from database import init_db, update_db
from backup_system import backup_database
from ui.login import login_screen

app = FastAPI()

@app.get("/")
def home():
    return {"message": "API chal rahi hai 🚀"}

if __name__ == "__main__":
    init_db()
    update_db()
    backup_database()   
    login_screen()