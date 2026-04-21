import os
import sqlite3

db_path = r"/chess_project/backend/chess_base.db"
print("Exists:", os.path.exists(db_path))

c = sqlite3.connect(db_path)
tables = c.execute("select name from sqlite_master where type='table'").fetchall()
with open("../../../tables.txt", "w") as f:
    for t in tables:
        f.write(t[0] + "\n")
