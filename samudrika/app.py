import os
import json
import base64
import uuid
import logging
import io
from datetime import datetime
from typing import Optional

env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            if line.strip() and not line.startswith("#"):
                try:
                    key, val = line.strip().split("=", 1)
                    os.environ[key] = val
                except ValueError:
                    pass

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Request, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from pydantic import BaseModel
from PIL import Image
from mistralai import Mistral

from sqlalchemy import create_engine, Column, String
from sqlalchemy.orm import declarative_base, sessionmaker

# -------------------------------------------------------------------
# Configuration & Placeholders
# -------------------------------------------------------------------
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "YOUR_WHATSAPP_VERIFY_TOKEN")
WHATSAPP_API_TOKEN = os.getenv("WHATSAPP_API_TOKEN", "YOUR_WHATSAPP_BEARER_TOKEN")
SYSTEM_PROMPT = "Analyze this palm image based on Vedic palmistry. Focus on major lines: life line, heart line, head line, and fate line."

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "frontend")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Samudrika API", description="API Middleware for Palm Reading MVP")

# -------------------------------------------------------------------
# Database Setup
# -------------------------------------------------------------------
DATABASE_URL = os.getenv("POSTGRES_URL")
if not DATABASE_URL:
    # Use /tmp for SQLite on Vercel as root is read-only
    if os.getenv("VERCEL"):
        DATABASE_URL = "sqlite:////tmp/samudrika.db"
    else:
        DATABASE_URL = "sqlite:///samudrika.db"

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class RequestLog(Base):
    __tablename__ = "request_logs"
    id = Column(String, primary_key=True, index=True)
    timestamp = Column(String)
    user_phone_number = Column(String)
    status = Column(String)
    llm_response_text = Column(String)

class ChatSession(Base):
    __tablename__ = "chat_sessions"
    session_id = Column(String, primary_key=True, index=True)
    timestamp = Column(String)
    name = Column(String)
    email = Column(String)
    phone = Column(String)
    dob = Column(String)
    tob = Column(String)
    pob = Column(String)
    referral_code = Column(String, nullable=True)
    palm_reading = Column(String)
    chat_history = Column(String)

def init_db():
    """Initializes the SQLAlchemy database with the required tables."""
    Base.metadata.create_all(bind=engine)

def log_request(req_id: str, phone: str, status: str, response: str):
    """Logs the request metadata and response into the SQLite database."""
    try:
        db = SessionLocal()
        new_log = RequestLog(
            id=req_id,
            timestamp=datetime.utcnow().isoformat(),
            user_phone_number=phone,
            status=status,
            llm_response_text=response
        )
        db.add(new_log)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to log to DB: {e}")
    finally:
        db.close()

# Run init on startup
@app.on_event("startup")
def on_startup():
    init_db()

# -------------------------------------------------------------------
# Frontend & Static Files
# -------------------------------------------------------------------
assets_dir = os.path.join(FRONTEND_DIR, "assets")
if os.path.isdir(assets_dir):
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

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

def get_mistral_client():
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        return None
    try:
        return Mistral(api_key=api_key)
    except Exception as e:
        logger.error(f"Failed to initialize Mistral Client: {e}")
        return None

@retry(
    stop=stop_after_attempt(3), 
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((requests.exceptions.Timeout, requests.exceptions.ConnectionError, Exception))
)
async def call_mistral_llm(image_bytes: bytes, astrology_context: str = "") -> str:
    """
    Calls Mistral Pixtral with the image bytes, system prompt, and astrology context.
    Implements retry logic.
    """
    client = get_mistral_client()
    if not client:
        logger.warning("MISTRAL_API_KEY not found. Returning mock response.")
        return "✨ **Cosmic Reading Successful! (Mock Demo)** ✨\n\nYour life line shows immense vitality and a strong connection to nature. The deep groove in your fate line suggests a major career breakthrough is approaching in the next 6 months.\n\nYour heart line reveals a deeply empathetic soul. The small cross near your Jupiter mount indicates spiritual protection.\n\n*(Note: To get live readings, please configure MISTRAL_API_KEY in your environment!)*"

    base64_image = base64.b64encode(image_bytes).decode('utf-8')
    image_url = f"data:image/jpeg;base64,{base64_image}"

    prompt = SYSTEM_PROMPT
    if astrology_context:
        prompt += f"\n\nAstrology Context of the User:\n{astrology_context}\n\nPlease explicitly mention their name and birth details in a welcoming, mystical opening sentence so they know the reading is highly personalized based on their birth chart!"

    response = await client.chat.complete_async(
        model='pixtral-12b-2409',
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": image_url}
                ]
            }
        ],
        temperature=0.1,
        max_tokens=1000
    )
    return response.choices[0].message.content.strip()

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

class SessionStartRequest(BaseModel):
    name: str
    email: str
    phone: str
    dob: str
    tob: str
    pob: str
    referral_code: Optional[str] = None

@app.post("/start_session")
def start_session(req: SessionStartRequest):
    session_id = str(uuid.uuid4())
    try:
        db = SessionLocal()
        new_session = ChatSession(
            session_id=session_id,
            timestamp=datetime.utcnow().isoformat(),
            name=req.name,
            email=req.email,
            phone=req.phone,
            dob=req.dob,
            tob=req.tob,
            pob=req.pob,
            referral_code=req.referral_code,
            palm_reading="",
            chat_history="[]"
        )
        db.add(new_session)
        db.commit()
        return {"session_id": session_id}
    except Exception as e:
        logger.error(f"Failed to create session: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    finally:
        db.close()

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
            
        # 1.5. Fetch Astrology Context
        astrology_context = ""
        if session_id:
            try:
                db = SessionLocal()
                session = db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
                if session and session.name:
                    astrology_context = f"Name: {session.name}\nDate of Birth: {session.dob}\nTime of Birth: {session.tob}\nPlace of Birth: {session.pob}"
                db.close()
            except Exception as e:
                logger.error(f"Failed to fetch session {session_id} for astrology context: {e}")
            
        # 2. Call Mistral LLM with retry logic
        try:
            llm_response = await call_mistral_llm(image_bytes, astrology_context)
        except Exception as e:
            logger.warning(f"Mistral call failed, using mock response. Error: {e}")
            import time
            time.sleep(2)
            llm_response = "✨ **Cosmic Reading (Testing Phase)** ✨\n\nOops! We are currently in our testing phase. We will fix this issue shortly and get back to you.\n\nIf you have paid, please be assured that your refund will be processed in 3-5 working days."
            
        # 4. Update session data if session_id is provided
        if session_id:
            try:
                db = SessionLocal()
                session = db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
                if session:
                    session.palm_reading = llm_response
                    db.commit()
                db.close()
            except Exception as e:
                logger.error(f"Failed to save palm reading to session {session_id}: {e}")

        # 5. Log Success
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
        
        # Step 3: Call LLM
        # llm_response = await call_mistral_llm(image_bytes)
        
        # Step 5: Log & Reply
        # log_request(req_id, phone_number, "SUCCESS", llm_response)
        # TODO: Implement a function to send `llm_response` back to the user via WhatsApp Graph API
        
        pass # Remove this pass when implementing the above
        
    except Exception as e:
        logger.error(f"Failed to process WhatsApp image {media_id}: {e}")
        log_request(req_id, phone_number, "FAILED", str(e))

class ChatRequest(BaseModel):
    session_id: str
    message: str

@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    # 1. Fetch current history and details from DB
    try:
        db = SessionLocal()
        session = db.query(ChatSession).filter(ChatSession.session_id == req.session_id).first()
    except Exception as e:
        logger.error(f"Failed to fetch session {req.session_id}: {e}")
        raise HTTPException(status_code=500, detail="Database access error")
       
    if not session:
        if 'db' in locals(): db.close()
        raise HTTPException(status_code=404, detail="Session not found")
        
    name = session.name
    dob = session.dob
    tob = session.tob
    pob = session.pob
    palm_reading = session.palm_reading
    history_str = session.chat_history
    
    import json
    try:
        history = json.loads(history_str) if history_str else []
    except Exception:
        history = []
        
    # 2. Call Mistral
    client = get_mistral_client()
    if not client:
        logger.warning("MISTRAL_API_KEY not configured. Returning fallback response.")
        response_text = f"✨ **Pandit Ji (Mock Response)** ✨\n\nI can see in your lines that you are seeking answers, {name}. (Set MISTRAL_API_KEY in your environment for active AI responses!)"
    else:
        system_prompt = (
            f"You are Pandit Ji, a premium Vedic Astrologer and Palmist. "
            f"You are currently chatting with {name}. "
            f"Their birth details are: Date of Birth: {dob}, Time of Birth: {tob}, Place of Birth: {pob}. "
            f"If they have scanned their palm, this is their reading:\n\"{palm_reading}\"\n"
            f"Answer the user's questions about their life, career, marriage, or wealth in a wise, mystic, and reassuring tone. "
            f"IMPORTANT: You MUST give ALL your responses entirely in Hindi (using Devanagari script). Start your responses with a greeting like 'हरि ओम' or 'प्रणाम'. "
            f"Keep your answers concise, around 2-3 sentences, so it feels like a live chat conversation."
        )
        
        messages = [{"role": "system", "content": system_prompt}]
        for h in history:
            role = "user" if h.get("role") == "user" else "assistant"
            messages.append({"role": role, "content": h.get("text")})
        
        messages.append({"role": "user", "content": req.message})
        
        try:
            response = await client.chat.complete_async(
                model='mistral-small-latest',
                messages=messages,
                temperature=0.3,
                max_tokens=250
            )
            response_text = response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Chat error: {e}")
            error_msg = str(e)
            if "503" in error_msg or "UNAVAILABLE" in error_msg:
                response_text = "The cosmic energies are currently overwhelming and Pandit Ji is meditating deeply. Please ask your question again in a few moments."
            else:
                response_text = "The stars are temporarily clouded. Please try again."
            
    # 3. Update DB with new history
    history.append({"role": "user", "text": req.message})
    history.append({"role": "model", "text": response_text})
    
    try:
        session.chat_history = json.dumps(history)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to update chat history for session {req.session_id}: {e}")
    finally:
        db.close()
        
    return {"response": response_text}

@app.get("/session/{session_id}")
async def get_session(session_id: str):
    db = SessionLocal()
    try:
        session = db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
            
        import json
        history = []
        if session.chat_history:
            try:
                history = json.loads(session.chat_history)
            except:
                pass
                
        return {
            "name": session.name,
            "palm_reading": session.palm_reading,
            "chat_history": history
        }
    finally:
        db.close()


