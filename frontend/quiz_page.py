import time
import streamlit as st
from backend.logic import (
    session_summary, mark_session_completed, save_attempt
)


def quiz():
    st.subheader("Word Meanings")
    if st.session_state.current_session_id is None or not st.session_state.current_items:
        if st.button("Start today's session"):
            from app import prepare_new_session  # Import here to avoid circular import
            prepare_new_session()
            st.experimental_rerun()
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
            from app import prepare_new_session
            prepare_new_session()
        return

    item = items[idx]
    st.markdown(f"**Q{idx+1}.** {item['question']}")

    # Make options appear as clickable boxes using columns and buttons
    choice_key = f"choice_{idx}"
    if choice_key not in st.session_state:
        st.session_state[choice_key] = None

    option_cols = st.columns(len(item["options"]))
    answered_key = f"answered_{idx}"
    for i, option in enumerate(item["options"]):
        if option_cols[i].button(option, key=f"{choice_key}_btn_{i}", disabled=st.session_state.get(answered_key, False)):
            st.session_state[choice_key] = option
            # Immediately process answer
            elapsed = int((time.time() - st.session_state.start_time) * 1000) if st.session_state.start_time else None
            correct = (option == item["answer"])
            save_attempt(st.session_state.auth_user["id"],
                         st.session_state.current_session_id,
                         item["word_id"], option, correct, response_time_ms=elapsed)
            if correct:
                st.success("Correct!")
            else:
                st.error(f"Incorrect. Correct answer: **{item['answer']}**")
            st.session_state[answered_key] = True
            st.session_state.start_time = time.time()
            st.experimental_rerun()
            return

    # If already answered, show feedback and move to next after a delay
    if st.session_state.get(answered_key, False):
        time.sleep(1.0)
        st.session_state.current_index += 1
        st.session_state.pop(choice_key, None)
        st.session_state.pop(answered_key, None)
        st.experimental_rerun()