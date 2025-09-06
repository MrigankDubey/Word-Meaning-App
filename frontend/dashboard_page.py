import streamlit as st
from backend.logic import get_user_stats

def dashboard():
    st.subheader("Dashboard")
    stats = get_user_stats(st.session_state.auth_user["id"])
    col1, col2, col3 = st.columns(3)
    col1.metric("Accuracy", f"{stats['accuracy']}%")
    col2.metric("Attempts", f"{stats['attempts']}")
    col3.metric("Mastered (Box≥4)", f"{stats['mastered']}")
    st.write("---")
    st.write("Use the **Quiz** tab in the sidebar to start or resume today's session(s).")