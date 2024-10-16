import sys
from sherpa_api_client_20240722 import annotate_file, annotate_text, get_token, get_annotators, ask_question

import json
import re
import streamlit as st
st.set_page_config(layout="wide")

import os
import random


DOCPROJECT = "chatexperiment"
PIPELINE   = "myanswergenerator"
MAXLINESINHISTORY = 30

st.logo(
    "1000-Blockmark_1_B.png",
    size="large",
    link="https://www.kairntech.com",
    icon_image="1000-Blockmark_1_B.png"
)

st.sidebar.title("Settings:")
# show text fields where user can enter a server, a username and a password
st.sidebar.write("Enter your server, username and password")
SHERPA   = st.sidebar.text_input("Server", value="https://sherpa-sandbox.kairntech.com")
USER     = st.sidebar.text_input("Username")
PASSWORD = st.sidebar.text_input("Password", type="password")
# title of the streamlit app
st.title("Chat with my documents")
st.write("(a Kairntech demo: using the Kairntech Server '%s' and project '%s')" % (SHERPA, DOCPROJECT))
st.write("Hi, I am your chat assistant. Ask me questions on your documents. The corpus in '%s' projects contains ~100 scientific documents on Animal Health." % DOCPROJECT)
# get the list of document from the folder "docs"
if USER is not None and PASSWORD is not None:
    print("tyring to get a token with server %s, user %s, password ******" % (SHERPA, USER))
    TOKEN = get_token(SHERPA, USER, PASSWORD)
if TOKEN is None:
    st.write("You are not (yet) authenticated.")
    st.stop()
else:
    print("Authentication successful")


def get_references(resultjson):
    try:
        answer = resultjson["answer"]
    except Exception as e:
        return []
    # get all regex '[\d+]' from the answer
    refs = re.findall(r'\[(\d+)\]', answer)
    print("refs = %s" % refs)
    references = []
    for ref in refs:
        # first reference is 1, not 0, second is 2, etc, so we need to substract 1 ...
        references.append("%s: %s" % (ref, resultjson['hits'][int(ref)-1]['segment']['metadata']['original']))
    return references

if 'history' not in st.session_state:
    st.session_state.history = ""

if len(st.session_state.history) > 0:
    st.divider()
    st.write("Conversation history: ")
    st.html(st.session_state.history)
    st.divider()
# create a text input window where user can enter a message
message    = st.text_input("Enter your question")
# arrange the next two buttons in two columns, # make this col quite small to make the buttons appear side by side
col1, col2 = st.columns([1, 4])
with col1:
    submit     = st.button("Submit")
with col2:
    freshstart = st.button("New conversation")

# wait until the user has entered a message

if freshstart:
    st.session_state.history = ""
    st.rerun()

if submit:

    query    = "HISTORY: " + st.session_state.history + "  \n\nQUESTION:" + message
    print("=====================================================================")
    print("query = %s" % query)
    # delete any html markup in the query
    query = re.sub(r'<[^>]*>', '', query)
    result   = ask_question(str(query), DOCPROJECT, PIPELINE, TOKEN, SHERPA)
    # print result whjich is a json object in nicely indented form
    print("result = ", json.dumps(result, indent=4))
    try:
        response = result["answer"]
        print("response = %s" % response)
    except Exception as e:
        response = "Could not get an answer: %s" % e
        print("Exception when asking '%s: %s" % (query, e))
        response = "Sorry, I cannot answer this question"
    print("=====================================================================")

    st.write(response)
    try:
        references = get_references(result)
    except Exception as e:
        print("error trying to get references: %s" % e)
        references = []
    # replace square brackets by parentheses in response
    response = response.replace("[", "(")
    response = response.replace("]", ")")
    response = response.replace(":", ";") # HACK, seems colon breaks the color coding
    response = response + "<br>\n" + "<br>".join(references)
    # trim the st.session_state.history to the last 10 lines: HACK! Check options to summarize etc
    lines = st.session_state.history.split("\n")
    if len(lines) > MAXLINESINHISTORY:
        st.session_state.history = "\n".join(lines[-MAXLINESINHISTORY:])

    st.session_state.history = st.session_state.history + "  \n\n<p style='color: green;'>QUERY: " + message + "</p><p style='color: red;'>AI RESPONSE: " + response + "</p>\n"
    st.rerun()
