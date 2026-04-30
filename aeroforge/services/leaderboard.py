from services.db import cur, conn

def add_score(user, score):
    cur.execute('INSERT INTO scores (user, score) VALUES (?, ?)', (user, score))
    conn.commit()

def get_top():
    rows = cur.execute('SELECT user, score FROM scores ORDER BY score DESC LIMIT 10').fetchall()
    return [{'user': r[0], 'score': r[1]} for r in rows]
