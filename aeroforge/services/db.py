import sqlite3
from config import DB_PATH

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cur = conn.cursor()
cur.execute('''
CREATE TABLE IF NOT EXISTS scores (
    id INTEGER PRIMARY KEY,
    user TEXT,
    score REAL
)
''')
conn.commit()
