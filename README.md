# Description

This is a tool to generate SPARQL queries from requests made by the user using natural language.
The idea is to use those queries to select documents from the LiLa Knowledge Base (available here[https://lila-erc.eu/#page-top]).

SPARQL is known for its difficult and cumbersome syntax and this tool aims at making it more usable for researchers in the field working with this specific database.

# Areas of Improvement

1. missing config.yaml file -> guided setup (?)
2. setting up hashed passwords using the correct method of the streamlit_authenticator library `stauth.Hasher().hash_list()`
