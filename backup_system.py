import os
import shutil
from datetime import datetime

def backup_database():

    db_file = "finance.db"

    if not os.path.exists("backup"):
        os.makedirs("backup")

    today = datetime.now().strftime("%Y%m%d")

    backup_file = f"backup/finance_{today}.db"

    if os.path.exists(db_file) and not os.path.exists(backup_file):
        shutil.copy(db_file, backup_file)
        print("Backup created:", backup_file)