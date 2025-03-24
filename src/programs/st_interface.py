import streamlit as st
from dotenv import load_dotenv

from programs.tools import gen
from pydantic_ai import Agent
import logfire
import os

load_dotenv()
logfire.configure(token=os.getenv("LOGFIRE-TOKEN"))


def configure_page():
    st.set_page_config(page_title="Lila database chatbot", 
                       layout="wide", 
                       initial_sidebar_state="expanded")
    with st.sidebar:
        st.markdown("## Useful Links 🔗")
        st.link_button("Visit the Lila website", url="https://lila-erc.eu/#page-top", icon="👉")

    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "Ai_mex_to_markdown" not in st.session_state:
        st.session_state.Ai_mex_to_markdown = ""
    logfire.info("Page setup successfully")


def chat_interface(agent: Agent):
    st.markdown("# Lila Database Chatbot 💬", unsafe_allow_html=True)
    message_container = st.container()

    for message in st.session_state.messages:
        with message_container:
            with st.chat_message(message["role"]):
                if message["role"] == "assistant":
                    st.markdown(st.session_state.Ai_mex_to_markdown, unsafe_allow_html=True)
                else:
                    st.markdown(message["content"], unsafe_allow_html=True)


    if user_query := st.chat_input("Ask something"):
        with message_container:
            st.chat_message("user").markdown(user_query)
            st.session_state.messages.append({"role": "user", "content": user_query})

            
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):

                    try:
                        history = [message["content"] for message in st.session_state.messages if message["role"] == "assistant"]
                        if not history:
                            response = agent.run_sync(user_query)
                        else:
                            response = agent.run_sync(user_query, message_history=history[-1]) 

                        st.write_stream(gen(response.data))
                        st.session_state.Ai_mex_to_markdown += response.data
                        st.session_state.messages.append({"role": "assistant", "content": response.new_messages()}) 
        
                    except Exception as e:
                        error_message = e
                        logfire.error(f"An error occurred during the chat: {error_message}")
                        st.error(f"An error occurred during the chat: {error_message}")

                        