import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__)) 
project_root = os.path.dirname(current_dir)             

if project_root not in sys.path:
    sys.path.append(project_root)

import streamlit as st
from dotenv import load_dotenv
from streamlit_authenticator import Authenticate
import logfire
import yaml
from yaml.loader import SafeLoader
from pathlib import Path
from src.response.agents import intent_extractor, main_agent
from src.mongo.storage import run_vector_search, save_agent_queries
from src.programs.tools import gen
from src.response.dataclasses import QuestionType

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
    
    question_language = intent.language
    question_category = intent.category

    if intent.question_type != QuestionType.LILA_RELATED:
        pass
    else:
        examples = run_vector_search(question=user_query, category=question_category)
        semantic_structure = intent.triples
        
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):

                try:
                    history = {}
                    response = main_agent(
                        user_question=user_query, 
                        sparql_queries=examples,
                        semantic_structure=semantic_structure,
                        message_history=history
                        )
                        
                    if response.content: 
                        st.write_stream(gen(response.content))

                        if response.sparql_query:
                            save_agent_queries(
                                user_query=user_query,
                                sparql_query=response.sparql_query,
                                query_results=response.query_results,
                                agent_response=response.content
                            )
                    else:
                        st.warning("Response is None")
                    st.session_state.messages.append({"role": "assistant", "content": response.content})
                    history.update(
                        {
                            "User": user_query,
                            "Your answer": response.content
                        }
                    )

                except Exception as e:
                    logfire.error(f"An error occurred during the chat: {e}")
                    st.error(f"An error occurred during the chat: {e}")


  
