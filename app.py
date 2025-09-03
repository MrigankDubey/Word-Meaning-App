import os
import time
import random
from datetime import datetime
import streamlit as st
import pandas as pd
import pytz

from backend.db import init_db
from backend import auth
from backend.logic import (
    today_local_str, start_or_resume_session, build_quiz_batch,
    record_served_words, create_session_items, save_attempt,
    session_summary, mark_session_completed, get_user_stats, count_words, add_word_rows
)

APP_TITLE = "Word Meaning (Daily 20)"
IST = pytz.timezone("Asia/Kolkata")

def ensure_init():
    init_db()

    # Auto-seed words from CSV if empty
    try:
        if count_words() == 0:
            csv_path = os.path.join(os.path.dirname(__file__), "data", "words.csv")
            if os.path.exists(csv_path):
                df = pd.read_csv(csv_path).fillna("")
                rows = [[r["text"], r["definition"], r.get("part_of_speech",""), r.get("language","en")] for r in df.to_dict("records")]
                add_word_rows(rows)
    except Exception as e:
        st.warning(f"Could not seed words: {e}")
    if "auth_user" not in st.session_state:
        st.session_state.auth_user = None
    if "current_session_id" not in st.session_state:
        st.session_state.current_session_id = None
    if "current_items" not in st.session_state:
        st.session_state.current_items = []
    if "current_index" not in st.session_state:
        st.session_state.current_index = 0
    if "start_time" not in st.session_state:
        st.session_state.start_time = None
    if "review_after" not in st.session_state:
        st.session_state.review_after = False

def local_date():
    return datetime.now(IST).strftime("%Y-%m-%d")

def header():
    st.title(APP_TITLE)
    if st.session_state.auth_user:
        st.caption(f"Welcome, **{st.session_state.auth_user['username']}** — {local_date()} (Asia/Kolkata)")
        st.button("Sign out", on_click=lambda: st.session_state.update({'auth_user': None, 'current_session_id': None, 'current_index': 0, 'current_items': [], 'review_after': False}))

def sign_up():
    st.subheader("Create account")
    with st.form("signup"):
        username = st.text_input("Username").strip()
        email = st.text_input("Email (optional)").strip()
        pw = st.text_input("Password", type="password")
        pw2 = st.text_input("Confirm Password", type="password")
        is_admin = st.checkbox("Make this user an admin")
        submit = st.form_submit_button("Sign up")
    if submit:
        if not username or not pw or pw != pw2:
            st.error("Please provide a username, password, and ensure both passwords match.")
        else:
            try:
                uid = auth.create_user(username, pw, email=email or None, is_admin=is_admin)
                st.success("Account created. Please sign in.")
            except Exception as e:
                st.error(f"Couldn't create user: {e}")

def sign_in():
    st.subheader("Sign in")
    with st.form("signin"):
        username = st.text_input("Username").strip()
        pw = st.text_input("Password", type="password")
        submit = st.form_submit_button("Sign in")
    if submit:
        user = auth.verify_password(username, pw)
        if user:
            st.session_state.auth_user = user
            st.success("Signed in.")
        else:
            st.error("Invalid username or password.")

def admin_words_panel():
    st.subheader("Admin · Manage Words")
    uploaded = st.file_uploader("Upload CSV with columns: text,definition,part_of_speech,language", type=["csv"])
    if uploaded is not None:
        try:
            df = pd.read_csv(uploaded).fillna("")
            required = {"text", "definition"}
            if not required.issubset(df.columns):
                st.error("CSV must contain at least 'text' and 'definition' columns.")
            else:
                from backend.logic import add_word_rows, count_words
                rows = df[["text","definition","part_of_speech","language"]].fillna("").values.tolist() \
                    if {"part_of_speech","language"}.issubset(df.columns) \
                    else [[r["text"], r["definition"], r.get("part_of_speech",""), r.get("language","en")] for r in df.to_dict("records")]
                add_word_rows(rows)
                st.success(f"Imported {len(rows)} words. Total now: {count_words()}")
        except Exception as e:
            st.error(f"Import failed: {e}")

def dashboard():
    st.subheader("Dashboard")
    stats = get_user_stats(st.session_state.auth_user["id"])
    col1, col2, col3 = st.columns(3)
    col1.metric("Accuracy", f"{stats['accuracy']}%")
    col2.metric("Attempts", f"{stats['attempts']}")
    col3.metric("Mastered (Box≥4)", f"{stats['mastered']}")
    st.write("---")
    st.write("Use the **Quiz** tab in the sidebar to start or resume today's session(s).")

def prepare_new_session():
    user_id = st.session_state.auth_user["id"]
    sid = start_or_resume_session(user_id, local_date())
    # If it's truly new (no items), create 20 fresh items
    if sid != st.session_state.get("current_session_id"):
        st.session_state.current_session_id = sid
        # Build batch
        batch = build_quiz_batch(user_id, local_date(), size=20)
        st.session_state.current_items = batch
        st.session_state.current_index = 0
        st.session_state.start_time = time.time()
        # Mark the words as served for "no repeat today"
        record_served_words(user_id, [it["word_id"] for it in batch], local_date())
        # Create DB rows for items
        create_session_items(sid, batch)

def quiz():
    st.subheader("Quiz (20 per session)")
    if st.session_state.current_session_id is None or not st.session_state.current_items:
        if st.button("Start today's session"):
            prepare_new_session()
        return

    items = st.session_state.current_items
    idx = st.session_state.current_index
    if idx >= len(items):
        # summary
        sid = st.session_state.current_session_id
        summary = session_summary(sid)
        st.success(f"You answered {summary['correct']} / {summary['total']} correctly.")
        if summary["wrong"]:
            st.session_state.review_after = True
            st.write("### Review your incorrect answers")
            for w in summary["wrong"]:
                st.markdown(f"- **Definition:** {w['definition']}  \n  **Correct word:** {w['word']}")
        # complete and allow next session
        mark_session_completed(sid)
        st.session_state.current_session_id = None
        st.session_state.current_items = []
        st.session_state.current_index = 0
        if st.button("Start next set of 20"):
            prepare_new_session()
        return

    item = items[idx]
    st.markdown(f"**Q{idx+1}.** {item['question']}")
    choice = st.radio("Pick the correct word:", item["options"], index=None, key=f"q_{idx}")
    disabled = choice is None
    if st.button("Submit answer", disabled=disabled):
        elapsed = int((time.time() - st.session_state.start_time) * 1000) if st.session_state.start_time else None
        correct = (choice == item["answer"])
        save_attempt(st.session_state.auth_user["id"],
                     st.session_state.current_session_id,
                     item["word_id"], choice, correct, response_time_ms=elapsed)
        if correct:
            st.success("Correct!")
        else:
            st.error(f"Incorrect. Correct answer: **{item['answer']}**")
        st.session_state.current_index += 1
        st.session_state.start_time = time.time()
        st.rerun()

def main():
    ensure_init()
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Go to", ["Sign in / Sign up", "Dashboard", "Quiz", "Admin · Words"])

    header()
    if not st.session_state.auth_user and page != "Sign in / Sign up":
        st.info("Please sign in first.")
        page = "Sign in / Sign up"

    if page == "Sign in / Sign up":
        tab1, tab2 = st.tabs(["Sign in", "Sign up"])
        with tab1:
            sign_in()
        with tab2:
            sign_up()
    elif page == "Dashboard":
        dashboard()
    elif page == "Quiz":
        prepare_new_session()
        quiz()
    elif page == "Admin · Words":
        if not st.session_state.auth_user or not st.session_state.auth_user.get("is_admin"):
            st.error("Admins only.")
        else:
            admin_words_panel()

if __name__ == "__main__":
    main()
