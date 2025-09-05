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
from frontend.quiz_page import quiz

APP_TITLE = "Vocabulary Improvement"
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
            st.session_state["redirect_to_quiz"] = True
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
    """
    Prepares a new quiz session for the currently authenticated user by creating or resuming a session,
    building a batch of quiz items, and initializing session state variables.
    """
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

from frontend.quiz_page import quiz

def main():
    ensure_init()
    if st.session_state.auth_user:
        st.sidebar.title("Navigation")
        if st.session_state.auth_user.get("is_admin"):
            pages = ["Dashboard", "Quiz", "Admin · Words"]
        else:
            pages = ["Dashboard", "Quiz"]
        # Redirect to Quiz if just signed in
        if st.session_state.pop("redirect_to_quiz", False):
            page = "Quiz"
        else:
            page = st.sidebar.radio("Go to", pages)
    else:
        page = "Sign in / Sign up"

    header()

    # If signed in, prevent access to sign in/sign up page
    if st.session_state.auth_user and page == "Sign in / Sign up":
        st.warning("You are already signed in.")
        page = "Dashboard"

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
