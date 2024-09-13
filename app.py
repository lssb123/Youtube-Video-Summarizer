import streamlit as st
import requests
import time

API_URL = "http://localhost:8000/summarize"
QUESTION_API_URL = "http://localhost:8000/ask"

st.title("YouTube Video Summarizer with Embeddings")
if "summary" not in st.session_state:
    st.session_state.summary = None
if "video_id" not in st.session_state:
    st.session_state.video_id = None


video_url = st.text_input("Enter YouTube Video URL")


def writing(welcome):
    for word in welcome.split(" "):
        yield word + " "
        time.sleep(0.2)


if st.button("Generate Summary and Store in Qdrant"):
    if video_url:
        with st.spinner("Generating summary and storing in Qdrant..."):
            try:
                response = requests.post(API_URL, json={"youtube_url": video_url})
                if response.status_code == 200:
                    data = response.json()
                    st.session_state.summary = data['summary']
                    st.session_state.video_id = data['video_id']
                    st.subheader("Summary")
                    st.write_stream(writing(st.session_state.summary))
                    st.success("Summary successfully stored in Qdrant!")
                else:
                    st.error(f"Error: {response.json()['detail']}")
            except Exception as e:
                st.error(f"Error connecting to API: {str(e)}")
    else:
        st.error("Please enter a valid YouTube URL.")

if st.session_state.summary:
    question = st.text_input("Ask a question about the summary")
    if st.button("Get Answer"):
        if question:
            with st.spinner("Getting answer..."):
                try:
                    question_response = requests.post(
                        QUESTION_API_URL, 
                        json={"question": question, "video_id": st.session_state.video_id}
                    )
                    if question_response.status_code == 200:
                        answer = question_response.json().get("answer")
                        st.subheader("Answer")
                        st.write_stream(writing(answer))
                    else:
                        st.error(f"Error: {question_response.json()['detail']}")
                except Exception as e:
                    st.error(f"Error connecting to API: {str(e)}")
        else:
            st.error("Please enter a question.")
