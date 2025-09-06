import streamlit as st

def sidebar_nav(auth_user):
    """
    Renders the sidebar navigation and returns the selected page.
    """
    st.sidebar.markdown("## Navigation")

    nav_options = {
        "Dashboard": "🏠 Dashboard",
        "Vocabulary Builder": "📝 Vocabulary Builder"
    }
    if auth_user.get("is_admin"):
        nav_options["Admin · Words"] = "🛠️ Admin · Words"

    # Track current page in session state
    if "page" not in st.session_state:
        st.session_state.page = "Dashboard"

    # Render each nav option as a button
    for key, label in nav_options.items():
        if st.sidebar.button(label, key=f"nav-{key}"):
            st.session_state.page = key
            st.experimental_rerun()

    st.sidebar.markdown("---")
    st.sidebar.write(f"Signed in as **{auth_user['username']}**")
    if st.sidebar.button("Sign out", key="sidebar-signout"):
        st.session_state.update({'auth_user': None, 'current_session_id': None, 'current_index': 0, 'current_items': [], 'review_after': False})
        st.experimental_rerun()

    return st.session_state.page
