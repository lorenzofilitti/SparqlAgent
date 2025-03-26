import streamlit as st
from dotenv import load_dotenv
from streamlit_authenticator import Authenticate
from programs.tools import gen
from pydantic_ai import Agent
import logfire
import os
import yaml
from yaml.loader import SafeLoader
from pathlib import Path

load_dotenv()
logfire.configure(token=os.getenv("LOGFIRE-TOKEN"))




def configure_page():
    try:
        st.set_page_config(page_title="Lila database chatbot", 
                        layout="centered")
        
        with open(Path.cwd()/"config.yaml", "r") as f:
            config = yaml.load(f, Loader=SafeLoader)

        if "authenticator" not in st.session_state:
            st.session_state.authenticator = Authenticate(
                credentials= config["credentials"],
                cookie_name= config["cookie"]["name"],
                cookie_key= config["cookie"]["key"],
                cookie_expiry_days= config["cookie"]["expiry_days"],
            
        )
        if "messages" not in st.session_state:
            st.session_state.messages = []
        if "Ai_mex_to_markdown" not in st.session_state:
            st.session_state.Ai_mex_to_markdown = {}

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
        # with open(Path.cwd()/"config.yaml", 'w') as file:
        #     yaml.dump(config, file, default_flow_style=False, allow_unicode=True)
        
        st.markdown("# Lila Database Chatbot 💬", unsafe_allow_html=True)  
    
        message_container = st.container()

        for message in st.session_state.messages:
            with message_container:
                if message["role"] == "user":
                    with st.chat_message("user"):
                        st.markdown(message["content"], unsafe_allow_html=True)
                elif st.session_state.Ai_mex_to_markdown["content"]:
                    with st.chat_message("assistant"):    
                        st.markdown(st.session_state.Ai_mex_to_markdown["content"], unsafe_allow_html=True)
            


        if user_query := st.chat_input("Ask something"):
            with message_container:
                st.chat_message("user").markdown(user_query)
                st.session_state.messages.append({"role": "user", "content": user_query})

                
                with st.chat_message("assistant"):
                    with st.spinner("Thinking..."):

                        try:
                            history = [msg["content"] for msg in st.session_state.messages if msg["role"] == "assistant"]
                            logfire.info(f"Chat history length: {len(history)}")
                            if not history:
                                response = agent.run_sync(user_query)
                            else:
                                response = agent.run_sync(user_query, message_history=history[-1]) 

                            st.write_stream(gen(response.data))
                            st.session_state.Ai_mex_to_markdown.update({"content": response.data})
                            st.session_state.messages[0].update({"role": "assistant", "content": response.new_messages()})

                            
            
                        except Exception as e:
                            logfire.error(f"An error occurred during the chat: {e}")
                            st.error(f"An error occurred during the chat: {e}")


  
                        