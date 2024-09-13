from fastapi import FastAPI, HTTPException
import tensorflow_hub as hub
import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, Distance, VectorParams
from youtube_transcript_api import YouTubeTranscriptApi
import google.generativeai as genai
from dotenv import load_dotenv
import os
import uuid

load_dotenv()
genai.configure(api_key=os.getenv("API_KEY"))
app = FastAPI()
client = QdrantClient(url="http://localhost:6333")
embed_model_url = "https://tfhub.dev/google/universal-sentence-encoder/4"
embed_model = hub.load(embed_model_url)
collection_name = "youtubesummary"

# try:
#     client.create_collection(
#         collection_name=collection_name,
#         vectors_config=VectorParams(size=512, distance=Distance.COSINE)
#     )
# except Exception as e:
#     print("Collection might already exist:", str(e))

@app.post("/summarize")
async def summarize_and_store(youtube_url: dict):
    video_url = youtube_url.get("youtube_url")

    if "v=" not in video_url:
        raise HTTPException(status_code=400, detail="Invalid YouTube URL")
    video_id = video_url.split("v=")[-1]

    transcript = get_transcript(video_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript could not be retrieved")

    summary = summarize_transcript(transcript)
    if not summary:
        raise HTTPException(status_code=500, detail="Summary generation failed")

    chunk_size = 1000
    chunks = split_into_chunks(summary, chunk_size)
    
    for chunk in chunks:
        embeddings = embed_model([chunk])
        embeddings = np.array(embeddings).tolist()

        point_id = str(uuid.uuid4())

        point = PointStruct(id=point_id, vector=embeddings[0], payload={"video_id": video_id, "summary_chunk": chunk})
        client.upsert(collection_name=collection_name, points=[point], wait=True)

    return {"status": "Summary successfully stored in Qdrant!", "summary": summary, "video_id": video_id}


@app.post("/ask")
async def answer_question(question_data: dict):
    question = question_data.get("question")
    video_id = question_data.get("video_id")

    question_embedding = embed_model([question])
    question_vector = np.array(question_embedding).tolist()[0] 

    try:
        search_results = client.search(
            collection_name=collection_name,
            query_vector=question_vector, 
            limit=5
            # filter={"must": [{"key": "video_id", "match": {"value": video_id}}]}  # Filter by video ID
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching for relevant summaries: {str(e)}")

    if not search_results:
        raise HTTPException(status_code=404, detail="No relevant summaries found")

    top_summaries = " ".join([result.payload["summary_chunk"] for result in search_results])

    answer = summarize_transcript(top_summaries + f" Answer the question: {question}"+ " If the question is not related to the relavant summary provided then respond the answer as 'please provide me the relavant questions'")
    
    if not answer:
        raise HTTPException(status_code=500, detail="Failed to generate answer from the retrieved summary")

    return {"answer": answer}


def get_transcript(video_id):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join([item['text'] for item in transcript])
    except Exception as e:
        print(f"Error fetching transcript: {str(e)}")
        return None


def summarize_transcript(text):
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(f"Summarize this text: {text}")
        if not response or not hasattr(response, 'text'):
            raise ValueError("Invalid response format from summarization API")
        return response.text
    except Exception as e:
        print(f"Error summarizing text: {str(e)}")
        return None


# Helper function to split text into chunks of up to chunk_size characters, ensuring no word is split
def split_into_chunks(text, chunk_size):
    chunks = []
    while len(text) > chunk_size:
        # Find the last space within chunk_size characters to avoid splitting words
        split_point = text.rfind(' ', 0, chunk_size)
        if split_point == -1:
            split_point = chunk_size
        chunks.append(text[:split_point].strip())
        text = text[split_point:].strip()
    chunks.append(text)
    return chunks
