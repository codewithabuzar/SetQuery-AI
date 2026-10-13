"""Floating AI assistant for the SetQuery workspace."""

import streamlit as st

from ai_app_help import answer_app_question
from llm import ask_gemini_app


@st.fragment
def render_floating_ai():

    if "floating_ai_open" not in st.session_state:
        st.session_state.floating_ai_open = False

    if "floating_ai_history" not in st.session_state:
        st.session_state.floating_ai_history = []

    with st.container(key="sq_ai_launcher"):

        if st.button(
            "SetQuery-AI",
            icon=":material/auto_awesome:",
            key="sq_ai_toggle",
            help="Ask SetQuery AI",
        ):
            st.session_state.floating_ai_open = (
                not st.session_state.floating_ai_open
            )
            st.rerun(scope="fragment")

    if not st.session_state.floating_ai_open:
        return

    with st.container(key="sq_ai_panel"):

        with st.container(key="sq_ai_header"):

            left, right = st.columns([5, 1])

            with left:
                st.markdown("#### ? SetQuery AI")
                st.caption("Your geospatial assistant")

            with right:
                if st.button(
                    "?",
                    key="sq_ai_close",
                    help="Close assistant",
                ):
                    st.session_state.floating_ai_open = False
                    st.rerun(scope="fragment")

        with st.container(
            height=230,
            key="sq_ai_messages",
        ):

            history = st.session_state.floating_ai_history

            if not history:
                st.markdown(
                    "Hi! I'm SetQuery AI. "
                    "Ask me about the app, its features, "
                    "or how to analyze satellite data."
                )

            for index, message in enumerate(history):

                role = message["role"]

                bubble_key = (
                    f"sq_ai_bubble_{role}_{index}"
                )

                with st.container(key=bubble_key):

                    if role == "user":
                        st.caption("You")
                    else:
                        st.caption("? SetQuery AI")

                    st.markdown(message["content"])

        with st.form(
            "sq_ai_message_form",
            clear_on_submit=True,
        ):

            question = st.text_input(
                "Message",
                placeholder="Ask SetQuery AI...",
                label_visibility="collapsed",
            )

            submitted = st.form_submit_button(
                "Send ?",
                type="primary",
                use_container_width=True,
            )

        if submitted and question.strip():

            question = question.strip()

            st.session_state.floating_ai_history.append({
                "role": "user",
                "content": question,
            })

            with st.spinner("SetQuery AI is thinking..."):

                try:
                    answer = answer_app_question(question)

                    if answer is None:
                        answer = ask_gemini_app(question)

                except Exception:
                    answer = (
                        "I can help explain SetQuery AI, "
                        "its features and methodology. "
                        "Please try again."
                    )

            st.session_state.floating_ai_history.append({
                "role": "assistant",
                "content": answer,
            })

            st.rerun(scope="fragment")
