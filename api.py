from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
import agent

app = FastAPI(
    title="YouTube & Video Agent API", 
    description="Test all agent features visually using Swagger UI!"
)

class YoutubeURLRequest(BaseModel):
    url: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://www.youtube.com/watch?v=..."
            }
        }

class LocalVideoQueryRequest(BaseModel):
    query: str
    video_path: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "What is being shown?",
                "video_path": "/Users/yamansaraswat/Downloads/video.mp4"
            }
        }

class QARequest(BaseModel):
    query: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "Summarize the key points about astrology."
            }
        }

from typing import List

class LocalVideoBatchQueryRequest(BaseModel):
    query: str
    video_paths: List[str]
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "What is being shown?",
                "video_paths": [
                    "/Users/yamansaraswat/Downloads/video1.mp4",
                    "/Users/yamansaraswat/Downloads/video2.mp4"
                ]
            }
        }

@app.post("/process_youtube", tags=["Option 1"])
def process_youtube_endpoint(req: YoutubeURLRequest):
    """
    Extracts the transcript from a YouTube URL and saves it to the CSV database.
    (Does not download the video).
    """
    result = agent.process_youtube(req.url)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@app.post("/query_local_video", tags=["Option 2"])
def query_local_video_endpoint(req: LocalVideoQueryRequest):
    """
    Searches the chunks for a matching timestamp, extracts a GIF from the local video path, 
    and gets an answer from Gemini Multimodal AI.
    """
    result = agent.query_local_video(req.query, req.video_path)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@app.post("/qa_local_ai", tags=["Option 3"])
def qa_local_ai_endpoint(req: QARequest):
    """
    Searches the saved transcript data and generates an answer using local Llama 3 via Ollama.
    """
    result = agent.qa_open_source(req.query)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@app.post("/upload_document_qa", tags=["Option 4"])
async def upload_document_qa_endpoint(
    query: str = Form(...), 
    file: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None)
):
    """
    Upload a .txt, .pdf, or .csv file, OR provide raw text directly, and ask a question. 
    The local Llama 3 model will answer based strictly on the provided text or document.
    """
    if file:
        file_bytes = await file.read()
        result = agent.qa_document(file_bytes, file.filename, query)
    elif text:
        result = agent.qa_text(text, query)
    else:
        raise HTTPException(status_code=400, detail="Must provide either a file or raw text.")
        
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@app.post("/query_local_videos_batch", tags=["Option 5"])
def query_local_videos_batch_endpoint(req: LocalVideoBatchQueryRequest):
    """
    Provide a list of up to 50 video paths and run a single query across all of them.
    Returns a list of answers for each video.
    """
    if len(req.video_paths) > 50:
        raise HTTPException(status_code=400, detail="Maximum of 50 video paths allowed.")
        
    result = agent.query_local_videos_batch(req.query, req.video_paths)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

class VisualPalmRequest(BaseModel):
    image_paths: List[str]
    
    class Config:
        json_schema_extra = {
            "example": {
                "image_paths": [
                    "/Users/yamansaraswat/Desktop/youtube_agent/test_palm1.jpg",
                    "/Users/yamansaraswat/Desktop/youtube_agent/test_palm2.jpg"
                ]
            }
        }

@app.post("/qa_palm_images", tags=["Option 6"])
def qa_palm_images_endpoint(req: VisualPalmRequest):
    """
    Provide a list of absolute paths to the user's hand images.
    The system will visually compare them to the local reference database and generate a palm reading using Gemini.
    """
    result = agent.qa_palm_images(req.image_paths)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

from typing import List, Dict

class AstrologyChatRequest(BaseModel):
    name: str
    dob: str
    time: str
    place: str
    query: str
    history: List[Dict[str, str]] = []

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Yaman",
                "dob": "1995-06-15",
                "time": "14:30",
                "place": "Delhi, India",
                "query": "What does my career look like?",
                "history": [
                    {"role": "user", "content": "Hello!"},
                    {"role": "model", "content": "Hello Yaman! How can I help you today?"}
                ]
            }
        }

@app.post("/astrology_chat", tags=["Option 7"])
def astrology_chat_endpoint(req: AstrologyChatRequest):
    """
    Takes user birth profile details, current question, and chat history.
    Uses Gemini to extract relevant reference details from local PDFs and answers user queries.
    """
    user_info = {
        "name": req.name,
        "dob": req.dob,
        "time": req.time,
        "place": req.place
    }
    result = agent.qa_astrology(user_info, req.query, req.history)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
