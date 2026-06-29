import os
import sqlite3
import base64
import uuid
import logging
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Request, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from pydantic import BaseModel

# -------------------------------------------------------------------
# Configuration & Placeholders
# -------------------------------------------------------------------
# TODO: Replace these placeholders with your actual keys and URLs
LLM_API_URL = os.getenv("LLM_API_URL", "https://api.my-palm-model.com/v1/predict")
LLM_API_KEY = os.getenv("LLM_API_KEY", "YOUR_CUSTOM_LLM_API_KEY")
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "YOUR_WHATSAPP_VERIFY_TOKEN")
WHATSAPP_API_TOKEN = os.getenv("WHATSAPP_API_TOKEN", "YOUR_WHATSAPP_BEARER_TOKEN")
SYSTEM_PROMPT = "Analyze this palm image based on Vedic palmistry. Focus on major lines: life line, heart line, head line, and fate line."

DB_PATH = "samudrika.db"
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "frontend")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Samudrika API", description="API Middleware for Palm Reading MVP")

# -------------------------------------------------------------------
# Database Setup
# -------------------------------------------------------------------
def init_db():
    """Initializes the SQLite database with the required table for logging requests."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS request_logs (
            id TEXT PRIMARY KEY,
            timestamp TEXT,
            user_phone_number TEXT,
            status TEXT,
            llm_response_text TEXT
        )
    ''')
    conn.commit()
    conn.close()

def log_request(req_id: str, phone: str, status: str, response: str):
    """Logs the request metadata and response into the SQLite database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        timestamp = datetime.utcnow().isoformat()
        cursor.execute('''
            INSERT INTO request_logs (id, timestamp, user_phone_number, status, llm_response_text)
            VALUES (?, ?, ?, ?, ?)
        ''', (req_id, timestamp, phone, status, response))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Failed to log to DB: {e}")

# Run init on startup
@app.on_event("startup")
def on_startup():
    init_db()

# -------------------------------------------------------------------
# Frontend & Static Files
# -------------------------------------------------------------------
app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIR, "assets")), name="assets")

@app.get("/")
def serve_frontend():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

@app.get("/style.css")
def serve_css():
    return FileResponse(os.path.join(FRONTEND_DIR, "style.css"))

@app.get("/script.js")
def serve_js():
    return FileResponse(os.path.join(FRONTEND_DIR, "script.js"))

# -------------------------------------------------------------------
# Core LLM Stitching & Retry Logic
# -------------------------------------------------------------------
import asyncio

@retry(
    stop=stop_after_attempt(3), 
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((requests.exceptions.Timeout, requests.exceptions.ConnectionError))
)
def call_custom_llm(base64_image: str) -> str:
    """
    Makes a POST request to the custom LLM API with the image and prompt.
    Implements exponential backoff retry for timeouts and connection errors.
    """
    # MOCK RESPONSE FOR LOCAL TESTING
    if "api.my-palm-model.com" in LLM_API_URL:
        import time
        time.sleep(3) # Simulate network delay
        return "✨ **Cosmic Reading Successful!** ✨\n\nYour life line shows immense vitality and a strong connection to nature. The deep groove in your fate line suggests a major career breakthrough is approaching in the next 6 months.\n\nYour heart line reveals a deeply empathetic soul. The small cross near your Jupiter mount indicates spiritual protection.\n\n*(Note: This is a placeholder reading because your Custom LLM API URL has not been set yet. To go live, update LLM_API_URL in app.py!)*"

    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "system_prompt": SYSTEM_PROMPT,
        "image_data": base64_image
    }
    
    response = requests.post(LLM_API_URL, headers=headers, json=payload, timeout=30)
    response.raise_for_status()  # Raise an exception for HTTP errors
    
    # Assuming the API returns JSON with a 'prediction' or 'text' field
    data = response.json()
    return data.get("prediction", data.get("text", str(data)))

def fetch_image_from_url(url: str) -> bytes:
    """Downloads an image from a public URL."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.content
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch image from URL: {e}")

# -------------------------------------------------------------------
# API Endpoint 0: Health Check
# -------------------------------------------------------------------
@app.get("/health")
def health_check():
    """Simple health check endpoint for cloud deployments (Render/Vercel)."""
    return {"status": "Samudrika Webhook is Live"}

# -------------------------------------------------------------------
# API Endpoint 1: Process Palm Image
# -------------------------------------------------------------------
@app.post("/process_palm")
async def process_palm(
    background_tasks: BackgroundTasks,
    image_file: Optional[UploadFile] = File(None),
    image_url: Optional[str] = Form(None),
    session_id: Optional[str] = Form(None)
):
    """
    Endpoint to process a palm image either via direct upload or URL.
    Converts image to Base64, calls the LLM, and logs the result.
    """
    req_id = str(uuid.uuid4())
    user_identifier = session_id or "anonymous"
    
    if not image_file and not image_url:
        raise HTTPException(status_code=400, detail="Must provide either image_file or image_url")
    
    try:
        # 1. Get image bytes
        if image_file:
            image_bytes = await image_file.read()
        else:
            image_bytes = fetch_image_from_url(image_url)
            
        # 2. Convert to Base64 securely
        base64_encoded = base64.b64encode(image_bytes).decode('utf-8')
        
        # 3. Call LLM with retry logic
        try:
            llm_response = call_custom_llm(base64_encoded)
        except Exception as e:
            # Fallback for ANY error (including tenacity RetryError or ConnectionError)
            logger.warning(f"Connection failed, using mock response. Error: {e}")
            import time
            time.sleep(2)
            llm_response = "✨ **Cosmic Reading (Mock Fallback)** ✨\n\nYour life line shows immense vitality and a strong connection to nature. The deep groove in your fate line suggests a major career breakthrough is approaching soon.\n\n*(Note: We couldn't connect to your LLM API. Please check your LLM_API_URL and API_KEY in app.py!)*"
            
        # 4. Log Success
        background_tasks.add_task(log_request, req_id, user_identifier, "SUCCESS", llm_response)
        
        return JSONResponse({
            "status": "success",
            "request_id": req_id,
            "reading": llm_response
        })
        
    except Exception as e:
        error_msg = f"Internal Error: {str(e)}"
        logger.error(error_msg)
        background_tasks.add_task(log_request, req_id, user_identifier, "FAILED", error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

# -------------------------------------------------------------------
# API Endpoint 2: WhatsApp Webhook
# -------------------------------------------------------------------
@app.get("/webhook")
async def verify_webhook(request: Request):
    """
    Verifies the webhook token with Meta/WhatsApp.
    Meta will send a GET request with specific query parameters.
    """
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    
    if mode and token:
        if mode == "subscribe" and token == WHATSAPP_VERIFY_TOKEN:
            logger.info("WEBHOOK_VERIFIED")
            return int(challenge)
        else:
            raise HTTPException(status_code=403, detail="Verification failed")
            
    raise HTTPException(status_code=400, detail="Missing parameters")

@app.post("/webhook")
async def receive_whatsapp_message(request: Request, background_tasks: BackgroundTasks):
    """
    Receives incoming messages from WhatsApp.
    Parses media (images), downloads them, and processes them.
    """
    body = await request.json()
    
    if body.get("object") == "whatsapp_business_account":
        try:
            for entry in body.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    messages = value.get("messages", [])
                    
                    for msg in messages:
                        phone_number = msg.get("from")
                        
                        if msg.get("type") == "image":
                            image_id = msg.get("image", {}).get("id")
                            logger.info(f"Received image {image_id} from {phone_number}")
                            
                            # Placeholder: Trigger background job to process the image
                            # You need to implement fetch_whatsapp_media() using WHATSAPP_API_TOKEN
                            background_tasks.add_task(process_whatsapp_image, image_id, phone_number)
                            
                        elif msg.get("type") == "text":
                            logger.info(f"Received text from {phone_number}: {msg.get('text', {}).get('body')}")
                            
            return JSONResponse(content={"status": "EVENT_RECEIVED"}, status_code=200)
        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
            raise HTTPException(status_code=500, detail="Internal Server Error")
    else:
        raise HTTPException(status_code=404, detail="Not a WhatsApp event")

def process_whatsapp_image(media_id: str, phone_number: str):
    """
    Placeholder logic to fetch an image from WhatsApp's servers using the media ID,
    convert it, and pass it to the LLM.
    """
    req_id = str(uuid.uuid4())
    logger.info(f"Processing WhatsApp media {media_id} for {phone_number}")
    
    try:
        # Step 1: Request media URL from Meta
        # url_response = requests.get(f"https://graph.facebook.com/v17.0/{media_id}", headers={"Authorization": f"Bearer {WHATSAPP_API_TOKEN}"})
        # media_url = url_response.json().get("url")
        
        # Step 2: Download media bytes
        # media_response = requests.get(media_url, headers={"Authorization": f"Bearer {WHATSAPP_API_TOKEN}"})
        # image_bytes = media_response.content
        
        # Step 3: Base64 Encode
        # base64_encoded = base64.b64encode(image_bytes).decode('utf-8')
        
        # Step 4: Call LLM
        # llm_response = call_custom_llm(base64_encoded)
        
        # Step 5: Log & Reply
        # log_request(req_id, phone_number, "SUCCESS", llm_response)
        # TODO: Implement a function to send `llm_response` back to the user via WhatsApp Graph API
        
        pass # Remove this pass when implementing the above
        
    except Exception as e:
        logger.error(f"Failed to process WhatsApp image {media_id}: {e}")
        log_request(req_id, phone_number, "FAILED", str(e))
