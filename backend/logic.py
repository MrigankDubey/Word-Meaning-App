import random
import time
from datetime import datetime
from collections import defaultdict
from .db import get_conn
import pytz

IST = pytz.timezone("Asia/Kolkata")

def today_local_str():
    return datetime.now(IST).strftime("%Y-%m-%d")

def count_words():
    with get_conn() as con:
        cur = con.cursor()
        cur.execute("SELECT COUNT(*) FROM words")
        return cur.fetchone()[0]

def add_word_rows(rows):
    with get_conn() as con:
        cur = con.cursor()
        cur.executemany(
            "INSERT INTO words(text, definition, part_of_speech, language) VALUES(?,?,?,?)",
            rows
        )
        con.commit()

def get_random_distractors(correct_id, k=4, pos=None):
    with get_conn() as con:
        cur = con.cursor()
        if pos:
            cur.execute("SELECT id, text FROM words WHERE id<>? AND part_of_speech=? ORDER BY RANDOM() LIMIT ?",
                        (correct_id, pos, k))
            rows = cur.fetchall()
            if len(rows) < k:  # fallback to any
                need = k - len(rows)
                cur.execute("SELECT id, text FROM words WHERE id<>? ORDER BY RANDOM() LIMIT ?",
                            (correct_id, need))
                rows += cur.fetchall()
        else:
            cur.execute("SELECT id, text FROM words WHERE id<>? ORDER BY RANDOM() LIMIT ?",
                        (correct_id, k))
            rows = cur.fetchall()
        return [r[1] for r in rows]

def start_or_resume_session(user_id, date_local=None):
    date_local = date_local or today_local_str()
    with get_conn() as con:
        cur = con.cursor()
        cur.execute("SELECT id FROM sessions WHERE user_id=? AND date_local=? AND completed=0 ORDER BY id DESC LIMIT 1",
                    (user_id, date_local))
        row = cur.fetchone()
        if row:
            return row[0]
        # create fresh session
        cur.execute("INSERT INTO sessions(user_id, date_local) VALUES(?,?)", (user_id, date_local))
        con.commit()
        return cur.lastrowid

def mark_session_completed(session_id):
    with get_conn() as con:
        cur = con.cursor()
        cur.execute("UPDATE sessions SET completed=1 WHERE id=?", (session_id,))
        con.commit()

def words_already_served_today(user_id, date_local=None):
    date_local = date_local or today_local_str()
    with get_conn() as con:
        cur = con.cursor()
        cur.execute("SELECT word_id FROM user_day_words WHERE user_id=? AND date_local=?", (user_id, date_local))
        return {row[0] for row in cur.fetchall()}

def _next_candidates(user_id, how_many, date_local):
    """Pick words never shown today for this user."""
    used = words_already_served_today(user_id, date_local)
    with get_conn() as con:
        cur = con.cursor()
        if used:
            placeholders = ",".join("?" for _ in used)
            cur.execute(f"SELECT id, text, definition, part_of_speech FROM words WHERE id NOT IN ({placeholders}) ORDER BY RANDOM() LIMIT ?",
                        (*used, how_many))
        else:
            cur.execute("SELECT id, text, definition, part_of_speech FROM words ORDER BY RANDOM() LIMIT ?",
                        (how_many,))
        return cur.fetchall()

def build_quiz_batch(user_id, date_local=None, size=20):
    date_local = date_local or today_local_str()
    # just choose fresh words not used today (no repeats) — review happens after a session
    rows = _next_candidates(user_id, size, date_local)
    items = []
    for idx, (wid, text, definition, pos) in enumerate(rows, start=1):
        distractors = get_random_distractors(wid, 4, pos)
        options = distractors + [text]
        random.shuffle(options)
        items.append({
            "word_id": wid, "question": definition, "answer": text, "options": options, "pos": pos
        })
    return items

def record_served_words(user_id, word_ids, date_local=None):
    date_local = date_local or today_local_str()
    with get_conn() as con:
        cur = con.cursor()
        cur.executemany("INSERT OR IGNORE INTO user_day_words(user_id, date_local, word_id) VALUES(?,?,?)",
                        [(user_id, date_local, wid) for wid in word_ids])
        con.commit()

def create_session_items(session_id, items):
    with get_conn() as con:
        cur = con.cursor()
        for i, it in enumerate(items, start=1):
            cur.execute("INSERT INTO session_items(session_id, word_id, position) VALUES(?,?,?)",
                        (session_id, it["word_id"], i))
        con.commit()

def save_attempt(user_id, session_id, word_id, user_answer, correct, response_time_ms=None):
    with get_conn() as con:
        cur = con.cursor()
        cur.execute("UPDATE session_items SET user_answer=?, correct=? WHERE session_id=? AND word_id=?",
                    (user_answer, 1 if correct else 0, session_id, word_id))
        # fetch current Leitner box for this user/word (latest)
        cur.execute("SELECT box FROM user_attempts WHERE user_id=? AND word_id=? ORDER BY id DESC LIMIT 1",
                    (user_id, word_id))
        row = cur.fetchone()
        box = row[0] if row else 1
        if correct:
            box = min(5, box + 1)
        else:
            box = 1
        cur.execute("""
            INSERT INTO user_attempts(user_id, word_id, date_local, correct, response_time_ms, box)
            VALUES(?,?,?,?,?,?)
        """, (user_id, word_id, today_local_str(), 1 if correct else 0, response_time_ms, box))
        con.commit()

def session_summary(session_id):
    with get_conn() as con:
        cur = con.cursor()
        cur.execute("""
        SELECT si.word_id, w.text, w.definition, si.correct, si.user_answer
        FROM session_items si JOIN words w ON w.id = si.word_id
        WHERE si.session_id=? ORDER BY si.position ASC
        """, (session_id,))
        rows = cur.fetchall()
        total = len(rows)
        correct = sum(1 for r in rows if r[3]==1)
        wrong_items = [{"word_id": r[0], "word": r[1], "definition": r[2], "user_answer": r[4]} for r in rows if r[3]==0]
        return {"total": total, "correct": correct, "wrong": wrong_items}

def get_user_stats(user_id):
    with get_conn() as con:
        cur = con.cursor()
        cur.execute("""
            SELECT COUNT(*), SUM(correct) FROM user_attempts WHERE user_id=?
        """, (user_id,))
        a = cur.fetchone()
        attempts = a[0] or 0
        correct = a[1] or 0
        accuracy = round((correct/attempts)*100, 1) if attempts else 0.0
        # mastered = words with last box>=4
        cur.execute("""
            SELECT COUNT(DISTINCT word_id) FROM (
                SELECT word_id, MAX(box) as maxbox FROM user_attempts WHERE user_id=? GROUP BY word_id
            ) WHERE maxbox>=4
        """, (user_id,))
        mastered = cur.fetchone()[0] or 0
        return {"attempts": attempts, "accuracy": accuracy, "mastered": mastered}
