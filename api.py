from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
import os
import uuid
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
async def process_youtube_endpoint(req: YoutubeURLRequest):
    """
    Extracts the transcript from a YouTube URL and saves it to the CSV database.
    (Does not download the video).
    """
    result = await agent.process_youtube(req.url)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@app.post("/query_local_video", tags=["Option 2"])
async def query_local_video_endpoint(req: LocalVideoQueryRequest):
    """
    Searches the chunks for a matching timestamp, extracts a GIF from the local video path, 
    and gets an answer from Gemini Multimodal AI.
    """
    result = await agent.query_local_video(req.query, req.video_path)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@app.post("/qa_local_ai", tags=["Option 3"])
async def qa_local_ai_endpoint(req: QARequest):
    """
    Searches the saved transcript data and generates an answer using local Llama 3 via Ollama.
    """
    result = await agent.qa_open_source(req.query)
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
        result = await agent.qa_document(file_bytes, file.filename, query)
    elif text:
        result = await agent.qa_text(text, query)
    else:
        raise HTTPException(status_code=400, detail="Must provide either a file or raw text.")
        
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@app.post("/query_local_videos_batch", tags=["Option 5"])
async def query_local_videos_batch_endpoint(req: LocalVideoBatchQueryRequest):
    """
    Provide a list of up to 50 video paths and run a single query across all of them.
    Returns a list of answers for each video.
    """
    if len(req.video_paths) > 50:
        raise HTTPException(status_code=400, detail="Maximum of 50 video paths allowed.")
        
    result = await agent.query_local_videos_batch(req.query, req.video_paths)
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
async def qa_palm_images_endpoint(req: VisualPalmRequest):
    """
    Provide a list of absolute paths to the user's hand images.
    The system will visually compare them to the local reference database and generate a palm reading using Gemini.
    """
    result = await agent.qa_palm_images(req.image_paths)
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
async def astrology_chat_endpoint(req: AstrologyChatRequest):
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
    result = await agent.qa_astrology(user_info, req.query, req.history)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

class DocumentChatRequest(BaseModel):
    document_ids: List[str]
    query: str
    history: List[Dict[str, str]] = []

    class Config:
        json_schema_extra = {
            "example": {
                "document_ids": ["uuid-1", "uuid-2"],
                "query": "Summarize this document",
                "history": []
            }
        }

UPLOAD_DOCS_DIR = os.path.join(agent.DATA_DIR, "uploaded_documents")
os.makedirs(UPLOAD_DOCS_DIR, exist_ok=True)

@app.post("/upload_document", tags=["Option 8"])
async def upload_document_endpoint(file: UploadFile = File(...)):
    """
    Upload a PDF document, extract its text content, and save it under a unique document ID.
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
        
    try:
        file_bytes = await file.read()
        doc_id = str(uuid.uuid4())
        
        # Parse text from bytes
        text_content = agent.extract_text_from_bytes(file_bytes)
        if not text_content.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from the PDF. Make sure it's not scanned or empty.")
            
        dest_path = os.path.join(UPLOAD_DOCS_DIR, f"{doc_id}.txt")
        with open(dest_path, "w", encoding="utf-8") as f:
            f.write(text_content)
            
        # Log to SQLite DB
        agent.add_document_to_db(doc_id, file.filename)
            
        return {"document_id": doc_id, "filename": file.filename}
        
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process PDF: {str(e)}")

@app.get("/list_documents", tags=["Option 8"])
def list_documents_endpoint():
    """
    List all previously uploaded documents.
    """
    return agent.get_all_documents()

@app.post("/document_chat", tags=["Option 8"])
async def document_chat_endpoint(req: DocumentChatRequest):
    """
    Interact with multiple uploaded PDF documents simultaneously using your Gemini API key and RAG.
    """
    result = await agent.qa_uploaded_documents(req.document_ids, req.query, req.history)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
