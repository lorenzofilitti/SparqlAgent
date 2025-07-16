import streamlit as st
from dotenv import load_dotenv
from streamlit_authenticator import Authenticate
from programs.tools import gen
import logfire
import os
import yaml
from yaml.loader import SafeLoader
from pathlib import Path
from src.response.agents import intent_extractor, main_agent, QuestionCategories
from src.programs.tools import search_similarity

load_dotenv()
logfire.configure(token=os.getenv("LOGFIRE-TOKEN"))


def load_config():
    with open(Path.cwd()/"config.yaml", "r") as f:
        config = yaml.load(f, Loader=SafeLoader)
    return config


config = load_config()
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


authenticator: Authenticate = st.session_state.authenticator
authenticator.login("main")

if st.session_state.get("authentication_status") is None:
        st.warning("Please enter username and password")

elif st.session_state.get("authentication_status") is False:
    st.error("Username or password is incorrect")

elif st.session_state.get("authentication_status"):
    logfire.info("User logged in")
    authenticator.logout(location="sidebar")
    

st.markdown("# LiLa Database Chatbot 🤖", unsafe_allow_html=True)  

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if user_query := st.chat_input("Ask something"):
    st.session_state.messages.append({"role": "user", "content": user_query})
    st.chat_message("user").markdown(user_query)
    
    intent = intent_extractor(
        user_question=user_query, 
        previous_exchange=st.session_state.messages
        )

    if intent.question_type != QuestionCategories.LILA_RELATED:
        pass
    else:
        examples = search_similarity(query=user_query)
        semantic_structure = intent.triples
        
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):

                try:
                    history = st.session_state.memory.get("content")
                    if not history:
                        response = main_agent(
                            user_question=user_query, 
                            sparql_queries=examples,
                            semantic_structure=semantic_structure,
                            message_history=None
                            )
                    else:
                        response = main_agent(
                            user_question=user_query,
                            sparql_queries=examples,
                            semantic_structure=semantic_structure,
                            message_history=history
                            ) 
                    
                    if response.data is not None:
                        st.write_stream(gen(response.data))
                    else:
                        st.warning("Response is None")
                    st.session_state.memory.update({"content": response.new_messages()})
                    st.session_state.messages.append({"role": "assistant", "content": response.data})

                except Exception as e:
                    logfire.error(f"An error occurred during the chat: {e}")
                    st.error(f"An error occurred during the chat: {e}")


  
