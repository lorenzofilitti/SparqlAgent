import streamlit as st
from dotenv import load_dotenv
from streamlit_authenticator import Authenticate
from programs.tools import gen
from pydantic_ai import Agent
import logfire
import os
import json
import yaml
from yaml.loader import SafeLoader
from pathlib import Path

load_dotenv()
logfire.configure(token=os.getenv("LOGFIRE-TOKEN"))


def load_config():
    with open(Path.cwd()/"config.yaml", "r") as f:
        config = yaml.load(f, Loader=SafeLoader)
    return config


def configure_page():
    config = load_config()
    try:
        st.set_page_config(
            page_title="Lila database chatbot", 
            layout="centered",
            initial_sidebar_state="collapsed"
            )
        
        if "authenticator" not in st.session_state:
            st.session_state.authenticator = Authenticate(
                credentials= config["credentials"],
                cookie_name= config["cookie"]["name"],
                cookie_key= config["cookie"]["key"],
                cookie_expiry_days= config["cookie"]["expiry_days"],
            
        )
        if "messages" not in st.session_state:
            st.session_state.messages = []
        if "memory" not in st.session_state:
            st.session_state.memory = {}

    except Exception as e:
        logfire.error(f"Error during page configuration: {e}")


def chat_interface(agent: Agent):
    configure_page()

    authenticator: Authenticate = st.session_state.authenticator
    authenticator.login("main")

    if st.session_state.get("authentication_status") is None:
            st.warning("Please enter username and password")

    elif st.session_state.get("authentication_status") is False:
        st.error("Username or password is incorrect")

    elif st.session_state.get("authentication_status"):
        logfire.info("User logged in")
        authenticator.logout(location="sidebar")
        
        st.markdown("# Lila Database Chatbot 💬", unsafe_allow_html=True)  

        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
          
        if user_query := st.chat_input("Ask something"):
            st.session_state.messages.append({"role": "user", "content": user_query})
            st.chat_message("user").markdown(user_query)
            
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):

                    try:
                        history = st.session_state.memory.get("content")
                        logfire.info(f"Chat history length: {history}")
                        if not history:
                            response = agent.run_sync(user_query)
                        else:
                            response = agent.run_sync(user_query, message_history=history) 

                        st.write_stream(gen(response.data))
                        
                        st.session_state.memory.update({"content": response.new_messages()})
                        st.session_state.messages.append({"role": "assistant", "content": response.data})

                    except Exception as e:
                        logfire.error(f"An error occurred during the chat: {e}")
                        st.error(f"An error occurred during the chat: {e}")


  
def plot_query():
    with open(Path.cwd()/"args.json", "r") as f:
        args = json.load(f)
    with st.sidebar:
        st.markdown("## Sparql query used")
        st.code(args.get("args")[0], language="sparql", wrap_lines=True)